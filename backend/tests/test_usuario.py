"""Invariantes do modelo `Usuario` que o banco garante, não o Python."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.usuario import PapelUsuario, Usuario


def test_dois_usuarios_com_mesmo_email_levanta_integrity_error(
    sessao: Session,
) -> None:
    sessao.add(
        Usuario(
            nome="Primeiro",
            email="duplicado@rockhub.com",
            senha_hash="hash-1",
            papel=PapelUsuario.CLIENTE.value,
        )
    )
    sessao.flush()

    sessao.add(
        Usuario(
            nome="Segundo",
            email="duplicado@rockhub.com",
            senha_hash="hash-2",
            papel=PapelUsuario.CLIENTE.value,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_papel_fora_dos_tres_valores_levanta_integrity_error(
    sessao: Session,
) -> None:
    sessao.add(
        Usuario(
            nome="Sem papel válido",
            email="admin@rockhub.com",
            senha_hash="hash",
            papel="ADMIN",
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_usuario_gera_uuid_e_criado_em_automaticamente(sessao: Session) -> None:
    usuario = Usuario(
        nome="Nova Conta",
        email="nova-conta@rockhub.com",
        senha_hash="hash",
        papel=PapelUsuario.ORGANIZADOR.value,
    )
    sessao.add(usuario)
    sessao.flush()
    sessao.refresh(usuario)

    assert usuario.id is not None
    assert usuario.criado_em is not None
    assert usuario.criado_em.tzinfo is not None
