"""Prova que a migração Alembic é a única forma de o schema nascer.

`upgrade head` num banco vazio cria a tabela `usuario`; `downgrade base` a
derruba por inteiro; `upgrade` de novo funciona sem erro. É a garantia de que
o banco pode ser reconstruído do zero (AC1 e AC3).
"""

from alembic import command
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from tests.conftest import _config_alembic


def test_banco_de_teste_e_o_rockhub_teste(sessao: Session) -> None:
    """Trava contra migrar o banco de desenvolvimento por acidente."""
    resultado = sessao.execute(text("SELECT current_database()"))
    assert resultado.scalar_one() == "rockhub_teste"


def test_upgrade_cria_tabela_usuario_com_colunas_esperadas(
    engine_teste: Engine,
) -> None:
    inspetor = inspect(engine_teste)

    assert "usuario" in inspetor.get_table_names()

    colunas = {c["name"]: c for c in inspetor.get_columns("usuario")}
    assert "UUID" in str(colunas["id"]["type"]).upper()
    assert colunas["criado_em"]["type"].timezone is True

    constraints_unicas = inspetor.get_unique_constraints("usuario")
    assert any(
        "email" in constraint["column_names"] for constraint in constraints_unicas
    )


def test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz(
    engine_teste: Engine,
) -> None:
    cfg = _config_alembic()

    command.downgrade(cfg, "base")
    try:
        inspetor = inspect(engine_teste)
        assert "usuario" not in inspetor.get_table_names()
    finally:
        # Restaura o schema, mesmo se a asserção acima falhar, para não
        # quebrar os testes seguintes que dependem da tabela existir.
        command.upgrade(cfg, "head")

    inspetor = inspect(engine_teste)
    assert "usuario" in inspetor.get_table_names()
