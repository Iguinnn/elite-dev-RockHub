"""Prova que a migração Alembic é a única forma de o schema nascer.

`upgrade head` num banco vazio cria as tabelas do projeto; `downgrade base` as
derruba por inteiro; `upgrade` de novo funciona sem erro. É a garantia de que
o banco pode ser reconstruído do zero.

⚠️ **Toda migração nova entra aqui.** O teste de ida e volta lista as tabelas
nominalmente: uma revisão com o `downgrade()` quebrado só é notada se alguém
acrescentar a tabela dela à lista.
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


def test_upgrade_cria_tabelas_evento_e_setor(engine_teste: Engine) -> None:
    inspetor = inspect(engine_teste)
    tabelas = inspetor.get_table_names()

    assert "evento" in tabelas
    assert "setor" in tabelas

    colunas_evento = {c["name"]: c for c in inspetor.get_columns("evento")}
    colunas_setor = {c["name"]: c for c in inspetor.get_columns("setor")}

    assert "UUID" in str(colunas_evento["id"]["type"]).upper()
    assert "UUID" in str(colunas_setor["id"]["type"]).upper()


def test_dinheiro_e_bigint_e_datas_carregam_fuso(engine_teste: Engine) -> None:
    """AD-11: dinheiro em centavos inteiros, tempo em TIMESTAMPTZ.

    Ler o tipo direto do banco é a única forma de a decisão sobreviver a um
    `--autogenerate` distraído que troque `BigInteger` por `Integer`.
    """
    inspetor = inspect(engine_teste)
    colunas_evento = {c["name"]: c for c in inspetor.get_columns("evento")}
    colunas_setor = {c["name"]: c for c in inspetor.get_columns("setor")}

    assert "BIGINT" in str(colunas_setor["preco_centavos"]["type"]).upper()

    for coluna in ("data_hora", "publicado_em", "criado_em"):
        assert colunas_evento[coluna]["type"].timezone is True


def test_publicado_em_e_anulavel_e_as_outras_datas_nao_sao(
    engine_teste: Engine,
) -> None:
    """`NULL` em `publicado_em` é o rascunho que a Story 3.1 precisa provar."""
    inspetor = inspect(engine_teste)
    colunas = {c["name"]: c for c in inspetor.get_columns("evento")}

    assert colunas["publicado_em"]["nullable"] is True
    assert colunas["data_hora"]["nullable"] is False
    assert colunas["criado_em"]["nullable"] is False


def test_chave_estrangeira_de_setor_aponta_para_evento_com_cascade(
    engine_teste: Engine,
) -> None:
    inspetor = inspect(engine_teste)
    (chave,) = inspetor.get_foreign_keys("setor")

    assert chave["referred_table"] == "evento"
    assert chave["constrained_columns"] == ["evento_id"]
    assert chave["options"]["ondelete"] == "CASCADE"


def test_upgrade_cria_a_tabela_evento_portaria(engine_teste: Engine) -> None:
    """A escala da portaria (AD-7), com chave primária composta.

    Composta, e não um `id` próprio: o par (evento, pessoa) **é** a identidade
    da linha, e é a chave que impede a mesma pessoa escalada duas vezes no
    mesmo evento.
    """
    inspetor = inspect(engine_teste)

    assert "evento_portaria" in inspetor.get_table_names()

    chave_primaria = inspetor.get_pk_constraint("evento_portaria")
    assert set(chave_primaria["constrained_columns"]) == {"evento_id", "usuario_id"}

    colunas = {c["name"]: c for c in inspetor.get_columns("evento_portaria")}
    # Nenhuma coluna própria: a tabela não tem vida sua, nem `criado_em`.
    assert set(colunas) == {"evento_id", "usuario_id"}


def test_os_dois_ondelete_de_evento_portaria_sao_diferentes(
    engine_teste: Engine,
) -> None:
    """Apagar o evento leva a escala junto; apagar quem foi escalado, não.

    Lido do banco, não do modelo: o `--autogenerate` tem histórico de emitir a
    chave estrangeira sem o `ondelete`, e são dois diferentes nesta tabela.
    """
    inspetor = inspect(engine_teste)
    chaves = {
        chave["referred_table"]: chave
        for chave in inspetor.get_foreign_keys("evento_portaria")
    }

    assert chaves["evento"]["constrained_columns"] == ["evento_id"]
    assert chaves["evento"]["options"]["ondelete"] == "CASCADE"

    assert chaves["usuario"]["constrained_columns"] == ["usuario_id"]
    # Sem `ondelete`: o Postgres recusa apagar quem já trabalhou numa porta.
    assert "ondelete" not in chaves["usuario"]["options"]


def test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz(
    engine_teste: Engine,
) -> None:
    """Vale para **todas** as tabelas, não só a primeira.

    Cada migração nova entra nesta lista: sem isso, uma revisão com o
    `downgrade()` quebrado passaria despercebida aqui.
    """
    cfg = _config_alembic()
    tabelas_do_projeto = ("usuario", "evento", "setor", "evento_portaria")

    command.downgrade(cfg, "base")
    try:
        inspetor = inspect(engine_teste)
        restantes = set(inspetor.get_table_names())
        assert restantes.isdisjoint(tabelas_do_projeto)
    finally:
        # Restaura o schema, mesmo se a asserção acima falhar, para não
        # quebrar os testes seguintes que dependem da tabela existir.
        command.upgrade(cfg, "head")

    inspetor = inspect(engine_teste)
    tabelas = inspetor.get_table_names()
    for tabela in tabelas_do_projeto:
        assert tabela in tabelas
