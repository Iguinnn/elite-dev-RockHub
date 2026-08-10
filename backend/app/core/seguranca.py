"""Hash de senha (Argon2id) e token de sessão (JWT).

Este módulo não sabe o que é HTTP, cookie ou rota — só hash e token. Quem monta
o cookie é o router (`app/api/auth.py`), que é a fronteira do
`ARCHITECTURE-SPINE.md#Design Paradigm`.
"""

from datetime import datetime, timedelta, timezone
from typing import TypedDict

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
