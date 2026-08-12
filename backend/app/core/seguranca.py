"""Hash de senha (Argon2id), token de sessão (JWT) e código de ingresso (HMAC).

Este módulo não sabe o que é HTTP, cookie ou rota — só hash, token e assinatura.
Quem monta o cookie é o router (`app/api/auth.py`), que é a fronteira do
`ARCHITECTURE-SPINE.md#Design Paradigm`.

**Os três primitivos moram juntos porque são a mesma categoria de coisa**: cada
um transforma um segredo do servidor em algo que o cliente carrega e não
consegue forjar. Espalhá-los deixaria a comparação de tempo constante do código
de ingresso longe da conferência de senha, que é a vizinha natural dela.
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import obter_settings
from app.models.usuario import Usuario

# Parâmetros padrão já são Argon2id no perfil de baixa memória da RFC 9106 —
# ver Dev Notes da Story 1.4, "Argon2id: o que vem de graça".
_hasher = PasswordHasher()

# As 8 horas são invariante do AD-15, não configuração. É a única fonte da
# validade da sessão: o `exp` do JWT e o `max_age` do cookie saem daqui.
EXPIRACAO_SESSAO = timedelta(hours=8)


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def conferir_senha(hash_gravado: str, senha: str) -> bool:
    """Nunca deixa a exceção subir: hash corrompido no banco vira `False`,
    não `500`."""
    try:
        return _hasher.verify(hash_gravado, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# Hash de uma senha descartável, gerado uma vez no import. Usado para nivelar
# o tempo de resposta quando o e-mail não existe — ver Dev Notes da Story 1.4,
# "A resposta não pode revelar se o e-mail existe".
HASH_FANTASMA = gerar_hash("senha-fantasma-nao-usada-por-ninguem")


class _CargaSessao(TypedDict):
    sub: str
    papel: str
    iat: int
    exp: int


def criar_token_sessao(usuario: Usuario) -> str:
    agora = datetime.now(timezone.utc)
    carga: _CargaSessao = {
        "sub": str(usuario.id),
        "papel": usuario.papel,
        "iat": int(agora.timestamp()),
        "exp": int((agora + EXPIRACAO_SESSAO).timestamp()),
    }
    return jwt.encode(carga, obter_settings().jwt_secret, algorithm="HS256")


def ler_token_sessao(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, obter_settings().jwt_secret, algorithms=["HS256"]
        )
    except jwt.PyJWTError:
        return None


# --------------------------------------------------------------------------- #
# O código do ingresso (AD-5)
# --------------------------------------------------------------------------- #

# O separador entre id e assinatura. `.` porque não aparece em UUID nem em
# base64url — os dois lados do código são recuperáveis por um `split` que não
# tem caso ambíguo.
SEPARADOR_DO_CODIGO = "."


def gerar_nonce() -> str:
    """32 caracteres de aleatoriedade por ingresso.

    É o que faz dois ingressos da mesma reserva, do mesmo setor e do mesmo
    evento terem assinaturas diferentes. Sem ele, `HMAC(segredo, id + evento)`
    já seria único por causa do id — mas o nonce é o que o AD-5 fixa, e ele dá
    margem para o dia em que o id deixar de entrar na conta.
    """
    return secrets.token_urlsafe(24)


def assinar_ingresso(ingresso_id: UUID, evento_id: UUID, nonce: str) -> str:
    """`HMAC-SHA256(TICKET_SIGNING_SECRET, id + evento + nonce)` em base64url.

    Exatamente a fórmula do AD-5, e o segredo vive só no ambiente do backend.
    Sem ele, nem adivinhar UUID nem incrementar id produz código válido.

    O `=` do padding sai fora: ele não acrescenta informação, e um código de QR
    sem caractere de preenchimento é um código mais curto — o que importa quando
    ele vira imagem lida por câmera de celular na fila da porta.
    """
    mensagem = f"{ingresso_id}{evento_id}{nonce}".encode()
    bruto = hmac.new(
        obter_settings().ticket_signing_secret.encode(),
        mensagem,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(bruto).decode().rstrip("=")


def montar_codigo(ingresso_id: UUID, assinatura: str) -> str:
    """O conteúdo do QR: `ID.ASSINATURA` (AD-5)."""
    return f"{ingresso_id}{SEPARADOR_DO_CODIGO}{assinatura}"


def conferir_codigo(codigo: str, evento_id: UUID, nonce: str) -> bool:
    """Recalcula a assinatura e compara — **sem consultar o banco** (AD-5).

    ⚠️ **`hmac.compare_digest`, nunca `==`.** A comparação byte a byte do `==`
    para no primeiro caractere diferente, e o tempo que ela leva conta quantos
    caracteres estavam certos: com paciência, isso deixa alguém descobrir a
    assinatura correta um caractere por vez. `compare_digest` gasta o mesmo
    tempo sempre.

    ⚠️ **Recalcular é o mecanismo, e a coluna `assinatura` não participa.**
    Comparar contra o que está gravado transformaria o banco em oráculo de
    assinatura e desfaria a garantia inteira — o AD-5 diz que assinatura
    divergente é recusada *antes* de qualquer consulta. A coluna existe só para
    montar o QR sem recalcular.

    O `evento_id` e o `nonce` vêm de quem chama (a portaria, na Epic 5), que os
    tem em mãos para o ingresso que está validando.
    """
    id_bruto, separador, assinatura = codigo.partition(SEPARADOR_DO_CODIGO)
    if not separador or not assinatura:
        return False

    try:
        ingresso_id = UUID(id_bruto)
    except ValueError:
        return False

    return hmac.compare_digest(
        assinar_ingresso(ingresso_id, evento_id, nonce), assinatura
    )
