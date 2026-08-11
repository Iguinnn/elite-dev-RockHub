"""Invariantes de `Evento` e `Setor` que o banco garante, não o Python.

Nenhum destes testes passa por rota, service ou schema — nada disso existe
ainda. O que está sob prova é o schema: as quatro constraints do `setor`, o
`CASCADE` da chave estrangeira e o `UPDATE` condicional do AD-3, que é a
operação para a qual a tabela tem o formato que tem.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario

DATA_DO_SHOW = datetime(2026, 12, 1, 21, 0, tzinfo=timezone.utc)


def _evento(sessao: Session, organizador: Usuario, **campos: Any) -> Evento:
    """Grava um evento com os campos obrigatórios preenchidos.

    Local, e não no `conftest.py`, porque esta story é o único consumidor — a
    convenção do projeto é extrair no segundo (precedente de `Campo` e `Botao`,
    registrado no README da raiz).
    """
    valores: dict[str, Any] = {
        "organizador_id": organizador.id,
        "nome": "Noite de Rock",
        "data_hora": DATA_DO_SHOW,
        "local": "Casa de Shows",
    }
    valores.update(campos)

    evento = Evento(**valores)
    sessao.add(evento)
    sessao.flush()
    return evento


def _setor(sessao: Session, evento: Evento, **campos: Any) -> Setor:
    valores: dict[str, Any] = {
        "evento_id": evento.id,
        "nome": "Pista",
        "capacidade": 100,
        "preco_centavos": 12000,
    }
    valores.update(campos)

    setor = Setor(**valores)
    sessao.add(setor)
    sessao.flush()
    return setor


def test_evento_gera_uuid_e_criado_em_automaticamente(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)

    evento = _evento(sessao, organizador)
    sessao.refresh(evento)

    assert evento.id is not None
    assert evento.criado_em is not None
    assert evento.criado_em.tzinfo is not None


def test_evento_sem_publicado_em_existe_como_rascunho(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """`publicado_em` anulável é o que torna verificável o AC da Story 3.1."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)

    evento = _evento(sessao, organizador)
    sessao.refresh(evento)

    assert evento.publicado_em is None


def test_vendidos_maior_que_capacidade_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)

    sessao.add(
        Setor(
            evento_id=evento.id,
            nome="Pista",
            capacidade=10,
            vendidos=11,
            preco_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_vendidos_negativo_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)

    sessao.add(
        Setor(
            evento_id=evento.id,
            nome="Pista",
            capacidade=10,
            vendidos=-1,
            preco_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_capacidade_zero_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Setor com capacidade zero nasceria esgotado sem ninguém entender por quê."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)

    sessao.add(
        Setor(evento_id=evento.id, nome="Pista", capacidade=0, preco_centavos=12000)
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_preco_negativo_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)

    sessao.add(
        Setor(evento_id=evento.id, nome="Pista", capacidade=10, preco_centavos=-1)
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_dois_setores_com_mesmo_nome_no_mesmo_evento_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)
    _setor(sessao, evento, nome="Pista")

    sessao.add(
        Setor(evento_id=evento.id, nome="Pista", capacidade=50, preco_centavos=30000)
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_mesmo_nome_de_setor_em_outro_evento_e_aceito(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """A unicidade é por evento, não global: todo show pode ter uma Pista."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    primeiro = _evento(sessao, organizador, nome="Primeiro Show")
    segundo = _evento(sessao, organizador, nome="Segundo Show")

    _setor(sessao, primeiro, nome="Pista")
    setor_do_segundo = _setor(sessao, segundo, nome="Pista")

    assert setor_do_segundo.id is not None


def test_apagar_evento_leva_os_setores_junto(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """`ON DELETE CASCADE` no banco e `passive_deletes` no ORM, concordando.

    Apagar pela sessão é o ponto: com um `relationship` comum, o SQLAlchemy
    tentaria `UPDATE setor SET evento_id = NULL` antes do `DELETE` e estouraria
    no `NOT NULL` sem nunca chegar ao `CASCADE` da migração.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)
    _setor(sessao, evento, nome="Pista")
    _setor(sessao, evento, nome="Camarote", capacidade=20, preco_centavos=40000)
    evento_id = evento.id

    sessao.delete(evento)
    sessao.flush()

    restantes = sessao.execute(
        text("SELECT count(*) FROM setor WHERE evento_id = :id"), {"id": evento_id}
    ).scalar_one()
    assert restantes == 0


def test_setor_com_evento_inexistente_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    sessao.add(
        Setor(
            evento_id=uuid.uuid4(),
            nome="Pista",
            capacidade=10,
            preco_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_update_condicional_do_ad3_pedindo_mais_do_que_resta_afeta_zero_linhas(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Zero linhas afetadas é o sinal de "sem estoque" — não uma exceção.

    Este é o `UPDATE` que a Epic 3 vai usar para reservar, e é a razão de
    `capacidade` e `vendidos` serem colunas separadas. Ele é provado aqui, na
    story em que a tabela nasce, e não vira função: o service é da Epic 3.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento, capacidade=10, vendidos=8)

    sql = text(
        "UPDATE setor SET vendidos = vendidos + :q "
        " WHERE id = :id AND vendidos + :q <= capacidade"
    )

    excedente = sessao.execute(sql, {"q": 5, "id": setor.id})
    assert excedente.rowcount == 0

    cabe = sessao.execute(sql, {"q": 2, "id": setor.id})
    assert cabe.rowcount == 1
