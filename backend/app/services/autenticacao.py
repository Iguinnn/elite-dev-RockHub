"""Autenticação por e-mail e senha.

Este service só lê: nenhum `commit`, nenhum `flush`. E não sabe o que é
cookie, HTTP ou token — devolve o `Usuario` ou levanta `ErroDeDominio`. Quem
monta o token e grava o cookie é o router (`app/api/auth.py`).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import ErroDeDominio
from app.core.seguranca import HASH_FANTASMA, conferir_senha
from app.models.usuario import Usuario


def _credenciais_invalidas() -> ErroDeDominio:
    return ErroDeDominio(
        "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.", status_http=401
    )


def autenticar(sessao: Session, email: str, senha: str) -> Usuario:
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))

    if usuario is None:
        # Nivela o tempo de resposta com o caminho de usuário existente, para
        # a resposta não virar um oráculo de "esse e-mail está cadastrado?".
        conferir_senha(HASH_FANTASMA, senha)
        raise _credenciais_invalidas()

    if not conferir_senha(usuario.senha_hash, senha):
        raise _credenciais_invalidas()

    return usuario
