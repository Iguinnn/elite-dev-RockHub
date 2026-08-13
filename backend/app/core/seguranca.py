"""Hash de senha (Argon2id), token de sessão (JWT) e código de ingresso (HMAC).

Este módulo não sabe o que é HTTP, cookie ou rota — só hash, token e assinatura.
Quem monta o cookie é o router (`app/api/auth.py`), que é a fronteira do
`ARCHITECTURE-SPINE.md#Design Paradigm`.

**Os três primitivos moram juntos porque são a mesma categoria de coisa**: cada
um transforma um segredo do servidor em algo que o cliente carrega e não
consegue forjar. Espalhá-los deixaria a comparação de tempo constante do código
de ingresso longe da conferência de senha, que é a vizinha natural dela.
"""

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

# Base32 de Crockford: 32 símbolos **sem `I`, `L`, `O` e `U`**. Os três
# primeiros saem porque `1`/`I` e `0`/`O` se confundem quando alguém lê o código
# em voz alta na fila da porta; o `U` sai para o gerador não produzir palavrão
# por acaso.
#
# ⚠️ **É a escolha do alfabeto que resolve o AC de "não diferencia maiúsculas de
# minúsculas"**, e com base64url ele era fisicamente impossível: `aB` e `Ab` são
# bytes diferentes, e um `.upper()` na entrada destruiria toda assinatura
# legítima. Aqui não existe minúscula no alfabeto, então normalizar a entrada é
# o comportamento correto, e não um risco.
_ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# 8 símbolos de 5 bits — 40 bits —, e o número é decisão de produto (techspec
# `docs/techspec-codigo-curto.md`). O campo manual da portaria existe para
# quando a câmera falha, e com os 80 caracteres do formato antigo ninguém
# conseguia usá-lo na fila: um fallback que não se usa é um fallback que não
# existe. Sobre os 40 bits: adivinhar um código exige **já estar logado como uma
# conta de portaria escalada naquele evento** (AD-7), e quem tem essa credencial
# não precisa forjar código nenhum — está autorizado a validar.
TAMANHO_DO_CODIGO = 8

# Os símbolos que a leitura em voz alta confunde, na direção que o alfabeto
# aceita. `L` → `1` é convenção da própria base32 de Crockford, não invenção
# daqui.
_CONFUSOS = str.maketrans({"I": "1", "L": "1", "O": "0"})


def gerar_nonce() -> str:
    """32 caracteres de aleatoriedade por ingresso.

    É o que faz dois ingressos da mesma reserva, do mesmo setor e do mesmo
    evento terem códigos diferentes. Ele é o que o AD-5 fixa, e ele dá margem
    para o dia em que o id deixar de entrar na conta.

    ⚠️ **Ele passou a valer mais desde que o código encolheu para 40 bits.** Com
    os 43 caracteres de base64 do formato antigo, o id já bastava para nenhum par
    de ingressos colidir; com o HMAC truncado, colisão de código é possível — é
    o `nonce` que a emissão sorteia de novo para sair dela (techspec
    `docs/techspec-codigo-curto.md`).

    ⚠️ **Este valor nunca sai do servidor.** Ele é ingrediente do HMAC, e o
    `gerar_share_token()` do fim deste arquivo sai do **mesmo gerador** com a
    exposição exatamente oposta — aquele é feito para viajar por WhatsApp.
    Trocar um pelo outro, ou logar o nonce "porque o outro a gente mostra",
    entrega a entropia da assinatura. Os dois docstrings dizem isto em espelho.
    """
    return secrets.token_urlsafe(24)


def _hmac_do_ingresso(ingresso_id: UUID, evento_id: UUID, nonce: str) -> bytes:
    """`HMAC-SHA256(TICKET_SIGNING_SECRET, id + evento + nonce)`, em bytes.

    Exatamente a fórmula do AD-5, e o segredo vive só no ambiente do backend.
    Sem ele, nem adivinhar UUID nem incrementar id produz código válido.

    **Extraído para que a geração e a conferência partam do mesmo cálculo por
    construção.** Com a fórmula escrita duas vezes, uma das duas montando a
    mensagem em outra ordem produz divergência que nenhum caso feliz revela — ela
    aparece na fila da porta, num ingresso legítimo recusado.
    """
    mensagem = f"{ingresso_id}{evento_id}{nonce}".encode()
    return hmac.new(
        obter_settings().ticket_signing_secret.encode(),
        mensagem,
        hashlib.sha256,
    ).digest()


def gerar_codigo(ingresso_id: UUID, evento_id: UUID, nonce: str) -> str:
    """O código do ingresso: o HMAC truncado a 40 bits, em base32 de Crockford.

    **Truncado, não sorteado**, e é essa palavra que mantém o AD-5 de pé — *o
    código do ingresso é um token assinado, **não** um identificador*. É o mesmo
    que o TOTP faz há vinte anos: HMAC truncado a poucos dígitos (RFC 4226). Um
    valor aleatório à moda do `gerar_share_token()` seria mais simples e, no
    mesmo tamanho, indistinguível em segurança; ele foi **descartado** porque
    custaria justamente essa frase — com o truncamento eu reescrevo a
    representação do AD-5, com o sorteio eu o revogo.

    ⚠️ **Os 5 primeiros bytes do digest, e não os 5 últimos nem uma soma dos
    32.** A escolha é arbitrária e precisa continuar exatamente esta: mudá-la
    invalida todo ingresso já emitido, do mesmo jeito que girar o
    `TICKET_SIGNING_SECRET` invalida.
    """
    valor = int.from_bytes(
        _hmac_do_ingresso(ingresso_id, evento_id, nonce)[:5], "big"
    )
    # Do símbolo mais significativo para o menos: 8 fatias de 5 bits, sempre 8
    # caracteres — `int.from_bytes` de 5 bytes nunca passa de 40 bits.
    return "".join(
        _ALFABETO[(valor >> (5 * posicao)) & 0b11111]
        for posicao in reversed(range(TAMANHO_DO_CODIGO))
    )


def normalizar_codigo(bruto: str) -> str | None:
    """O que a câmera leu ou a portaria digitou, reduzido ao código — ou `None`.

    Aceita `9k4m 7qx2`, `9K4M-7QX2` e `9K4M7QX2` como o mesmo valor: sobem as
    letras, caem espaços e hífens, e os símbolos que a leitura em voz alta
    confunde viram os do alfabeto (`I` e `L` → `1`, `O` → `0`).

    `None` é "isto não é um código deste sistema", e é a resposta para tamanho
    errado, símbolo fora do alfabeto e entrada não-ASCII. **Quem chama decide o
    que fazer com o `None`**, e é por isso que ela existe separada da
    conferência: a portaria recusa o código malformado **sem tocar no banco**,
    que é uma consulta economizada no caminho mais sensível a tempo do produto.

    ⚠️ **É aqui que a guarda de não-ASCII passou a morar** (code review da Epic
    3). `hmac.compare_digest` com `str` só aceita ASCII: fora dele ele levanta
    `TypeError` em vez de devolver `False`, e um QR que decodificasse com acento
    virava `500 ERRO_INTERNO` na fila da porta, para um código simplesmente
    inválido. Nada legítimo é barrado — o alfabeto de Crockford é ASCII por
    construção.
    """
    if not bruto.isascii():
        return None

    limpo = bruto.replace(" ", "").replace("-", "").upper().translate(_CONFUSOS)

    if len(limpo) != TAMANHO_DO_CODIGO:
        return None

    if any(simbolo not in _ALFABETO for simbolo in limpo):
        return None

    return limpo


def conferir_codigo(
    codigo: str, ingresso_id: UUID, evento_id: UUID, nonce: str
) -> bool:
    """Recalcula o código do ingresso e compara com o que chegou (AD-5).

    ⚠️ **Recalcular é o mecanismo, e a coluna `codigo` não participa da
    comparação.** Quem valida acha a linha **pelo** código e então recalcula o
    HMAC a partir das colunas (`id`, `evento_id`, `nonce`); divergência é
    `INVALIDO`. Comparar contra o valor gravado transformaria o banco em oráculo
    de assinatura e desfaria a garantia inteira: bastaria a alguém conseguir
    escrever na coluna. É **este** recálculo que torna o código não forjável, e é
    a garantia que o AD-5 realmente entrega.

    ⚠️ **`hmac.compare_digest`, nunca `==`.** A comparação do `==` para no
    primeiro caractere diferente, e o tempo que ela leva conta quantos estavam
    certos: com paciência, isso deixa alguém descobrir o código correto um
    caractere por vez. `compare_digest` gasta o mesmo tempo sempre.

    ⚠️ **A promessa do AD-5 é o recálculo, e não "sem consultar o banco"** (code
    review da Epic 3, decisão do Igor). O `nonce` só existe na coluna
    `ingresso.nonce` e entra na fórmula: quem valida tem de carregar a linha
    **antes** de conseguir recalcular. Consultar o banco é pré-requisito da
    verificação, não uma etapa posterior a ela. A alternativa considerada — tirar
    o `nonce` da fórmula para recuperar a promessa literal — foi descartada:
    custaria a entropia por ingresso. O `nonce` fica; a promessa é que foi
    corrigida.

    Lixo que a câmera leu sai `False`, nunca exceção: quem barra é o
    `normalizar_codigo` acima, antes de chegar ao `compare_digest`.
    """
    normalizado = normalizar_codigo(codigo)
    if normalizado is None:
        return False

    return hmac.compare_digest(
        gerar_codigo(ingresso_id, evento_id, nonce), normalizado
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
