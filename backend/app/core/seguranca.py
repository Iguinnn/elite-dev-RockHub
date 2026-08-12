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

    ⚠️ **Este valor nunca sai do servidor.** Ele é ingrediente do HMAC, e o
    `gerar_share_token()` do fim deste arquivo sai do **mesmo gerador** com a
    exposição exatamente oposta — aquele é feito para viajar por WhatsApp.
    Trocar um pelo outro, ou logar o nonce "porque o outro a gente mostra",
    entrega a entropia da assinatura. Os dois docstrings dizem isto em espelho.
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
    """Recalcula a assinatura e compara com a do código (AD-5).

    ⚠️ **`hmac.compare_digest`, nunca `==`.** A comparação byte a byte do `==`
    para no primeiro caractere diferente, e o tempo que ela leva conta quantos
    caracteres estavam certos: com paciência, isso deixa alguém descobrir a
    assinatura correta um caractere por vez. `compare_digest` gasta o mesmo
    tempo sempre.

    ⚠️ **Recalcular é o mecanismo, e a coluna `assinatura` não participa.**
    Comparar contra o que está gravado transformaria o banco em oráculo de
    assinatura e desfaria a garantia inteira: bastaria a alguém conseguir
    escrever na coluna. A coluna existe só para montar o QR sem recalcular. É
    **este** recálculo — e não a ausência de I/O — que torna o código não
    forjável, e é a garantia que o AD-5 realmente entrega.

    ⚠️ **A redação antiga dizia "sem consultar o banco", e isso não se sustenta**
    (code review da Epic 3, decisão do Igor). O QR carrega `ID.ASSINATURA` e nada
    mais, enquanto esta função exige o `nonce`, que só existe na coluna
    `ingresso.nonce`: quem valida tem de buscar a linha pelo `id` **antes** de
    conseguir recalcular. Consultar o banco é pré-requisito da verificação, não
    uma etapa posterior a ela. A alternativa considerada — tirar o `nonce` da
    fórmula para recuperar a promessa literal — foi descartada: ela custaria a
    entropia por ingresso, que é o que impede dois ingressos do mesmo evento de
    compartilharem assinatura. O `nonce` fica; a promessa é que foi corrigida.

    O `evento_id` e o `nonce` vêm de quem chama — a portaria, na Epic 5, depois
    de carregar o ingresso pelo id lido no QR.
    """
    id_bruto, separador, assinatura = codigo.partition(SEPARADOR_DO_CODIGO)
    if not separador or not assinatura:
        return False

    # ⚠️ **`compare_digest` com `str` só aceita ASCII** — fora dele ele levanta
    # `TypeError`, não devolve `False` (code review da Epic 3). Sem esta linha, um
    # QR que decodifique como `<uuid>.çç` sobe até o handler genérico e vira
    # `500 ERRO_INTERNO` na fila da porta, para um código simplesmente inválido.
    # A assinatura legítima é base64 urlsafe, que é ASCII por construção: nada
    # que passe aqui deixa de passar por ser válido.
    if not assinatura.isascii():
        return False

    try:
        ingresso_id = UUID(id_bruto)
    except ValueError:
        return False

    return hmac.compare_digest(
        assinar_ingresso(ingresso_id, evento_id, nonce), assinatura
    )


# --------------------------------------------------------------------------- #
# O link compartilhável do ingresso (Story 4.3)
#
# ⚠️ **Fora do bloco do AD-5 de propósito, e não por descuido de organização.**
# Os três primitivos de cima transformam um segredo do servidor em algo que o
# cliente carrega e não consegue forjar — é o que o docstring do módulo diz. O
# `share_token` não faz isso: ele é um identificador opaco e aleatório, sem
# segredo nenhum na conta, e **não autentica coisa alguma**. Escrevê-lo dentro
# da seção do código do ingresso faria a próxima pessoa supor que ele participa
# da assinatura, que é exatamente o que a techspec do link proíbe supor.
# --------------------------------------------------------------------------- #


def gerar_share_token() -> str:
    """32 caracteres de aleatoriedade para o link público de um ingresso.

    **Mesmo gerador do `gerar_nonce()`**, e por engenharia igual: 192 bits não
    se adivinham, então o endereço só chega a quem recebeu o link.

    ⚠️ **A exposição é o oposto da do nonce, e é a única diferença que
    importa.** O nonce é ingrediente secreto do HMAC e nunca sai do servidor;
    este valor é feito para viajar por WhatsApp, e ele aparece na URL, no
    histórico do navegador e em qualquer print que alguém tire. Confundir os
    dois — usar este na assinatura, ou logar o nonce "porque o outro a gente
    mostra" — entrega a entropia do AD-5 inteira.

    **Ele também não substitui o código do QR.** Quem valida na porta recalcula
    a assinatura (AD-5); o `share_token` só endereça uma visualização (AD-8).
    """
    return secrets.token_urlsafe(24)
