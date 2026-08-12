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


def test_as_duas_chaves_estrangeiras_lidas_tem_indice(engine_teste: Engine) -> None:
    """O Postgres cria índice para chave **primária** e para `UNIQUE`, nunca
    para chave estrangeira — quem quiser tem que declarar.

    `setor.evento_id` já tinha o dele desde a Story 2.3. O de
    `evento.organizador_id` entrou no code review da Epic 2: é a coluna do
    `where` das duas leituras de "Meus eventos", e estava sem, sozinha, contra
    o argumento que a irmã doze linhas abaixo já usava.
    """
    inspetor = inspect(engine_teste)

    indices_de_evento = {i["name"] for i in inspetor.get_indexes("evento")}
    indices_de_setor = {i["name"] for i in inspetor.get_indexes("setor")}

    assert "ix_evento_organizador_id" in indices_de_evento
    assert "ix_setor_evento_id" in indices_de_setor


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


def test_upgrade_cria_tabelas_reserva_e_item_reserva(engine_teste: Engine) -> None:
    """As duas tabelas da Story 3.5, criadas juntas por uma revisão só.

    Nada na aplicação as lê ou escreve ainda — o critério de pronto daquela
    story é o schema, como foi o da 2.3 com `evento` e `setor`.
    """
    inspetor = inspect(engine_teste)
    tabelas = inspetor.get_table_names()

    assert "reserva" in tabelas
    assert "item_reserva" in tabelas

    colunas_reserva = {c["name"]: c for c in inspetor.get_columns("reserva")}
    colunas_item = {c["name"]: c for c in inspetor.get_columns("item_reserva")}

    assert set(colunas_reserva) == {
        "id",
        "cliente_id",
        "evento_id",
        "estado",
        "expira_em",
        "total_centavos",
        "criado_em",
    }
    assert set(colunas_item) == {
        "id",
        "reserva_id",
        "setor_id",
        "quantidade",
        "preco_unitario_centavos",
    }

    assert "UUID" in str(colunas_reserva["id"]["type"]).upper()
    assert "UUID" in str(colunas_item["id"]["type"]).upper()


def test_dinheiro_da_reserva_e_bigint_e_datas_carregam_fuso(
    engine_teste: Engine,
) -> None:
    """AD-11 de novo, agora nas duas tabelas da compra.

    `expira_em` com fuso é o que permite compará-lo com o `now()` do Postgres
    na colheita preguiçosa da Story 3.7 sem conversão pelo caminho.
    """
    inspetor = inspect(engine_teste)
    colunas_reserva = {c["name"]: c for c in inspetor.get_columns("reserva")}
    colunas_item = {c["name"]: c for c in inspetor.get_columns("item_reserva")}

    assert "BIGINT" in str(colunas_reserva["total_centavos"]["type"]).upper()
    assert "BIGINT" in str(colunas_item["preco_unitario_centavos"]["type"]).upper()

    for coluna in ("expira_em", "criado_em"):
        assert colunas_reserva[coluna]["type"].timezone is True

    assert colunas_reserva["expira_em"]["nullable"] is False


def test_das_quatro_chaves_estrangeiras_da_compra_so_uma_tem_cascade(
    engine_teste: Engine,
) -> None:
    """Item some junto com a reserva; show, setor e conta vendidos, não.

    Lido do banco, não do modelo, pelo mesmo motivo do
    `test_os_dois_ondelete_de_evento_portaria_sao_diferentes`: o
    `--autogenerate` tem histórico de emitir chave estrangeira sem `ondelete`,
    e aqui são três que **devem** sair sem e uma que **deve** sair com.
    """
    inspetor = inspect(engine_teste)
    da_reserva = {
        chave["referred_table"]: chave
        for chave in inspetor.get_foreign_keys("reserva")
    }
    do_item = {
        chave["referred_table"]: chave
        for chave in inspetor.get_foreign_keys("item_reserva")
    }

    # A única com CASCADE: item de reserva apagada não significa nada.
    assert do_item["reserva"]["constrained_columns"] == ["reserva_id"]
    assert do_item["reserva"]["options"]["ondelete"] == "CASCADE"

    # As três que o Postgres recusa apagar — apagar venda tem que doer.
    assert do_item["setor"]["constrained_columns"] == ["setor_id"]
    assert "ondelete" not in do_item["setor"]["options"]

    assert da_reserva["usuario"]["constrained_columns"] == ["cliente_id"]
    assert "ondelete" not in da_reserva["usuario"]["options"]

    assert da_reserva["evento"]["constrained_columns"] == ["evento_id"]
    assert "ondelete" not in da_reserva["evento"]["options"]


def test_so_as_chaves_estrangeiras_lidas_da_compra_tem_indice(
    engine_teste: Engine,
) -> None:
    """Três com índice, uma sem — e a que fica sem é decisão, não esquecimento.

    `reserva.cliente_id` é o `where` de "minhas compras" (Epic 4),
    `item_reserva.reserva_id` é lido em todo carregamento de reserva e varrido
    a cada DELETE em cascata, e `item_reserva.setor_id` é o `where` da colheita
    da Story 3.7. `reserva.evento_id` não é lido por nenhuma story planejada:
    índice preventivo é peso sem gargalo demonstrado.
    """
    inspetor = inspect(engine_teste)

    indices_de_reserva = {i["name"] for i in inspetor.get_indexes("reserva")}
    indices_do_item = {i["name"] for i in inspetor.get_indexes("item_reserva")}

    assert "ix_reserva_cliente_id" in indices_de_reserva
    assert "ix_item_reserva_reserva_id" in indices_do_item
    assert "ix_item_reserva_setor_id" in indices_do_item

    colunas_indexadas = {
        coluna
        for indice in inspetor.get_indexes("reserva")
        for coluna in indice["column_names"]
    }
    assert "evento_id" not in colunas_indexadas


def test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz(
    engine_teste: Engine,
) -> None:
    """Vale para **todas** as tabelas, não só a primeira.

    Cada migração nova entra nesta lista: sem isso, uma revisão com o
    `downgrade()` quebrado passaria despercebida aqui.
    """
    cfg = _config_alembic()
    tabelas_do_projeto = (
        "usuario",
        "evento",
        "setor",
        "evento_portaria",
        "reserva",
        "item_reserva",
        # ⚠️ **A sétima, e a que faltava** (code review da Epic 3). O AC12 da
        # Story 3.5 avisou por escrito que sem manter esta tupla em dia "uma
        # migração nova com o `downgrade()` quebrado passaria por ele sem ser
        # notada" — e a `e43874e0cf3a`, da 3.9, foi exatamente essa migração
        # nova. Quem acrescentar a oitava tabela acrescenta a linha aqui.
        "ingresso",
    )

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


def test_upgrade_cria_a_tabela_ingresso_com_as_nove_colunas(
    engine_teste: Engine,
) -> None:
    """A sétima tabela do schema, e o AC1 da Story 3.9 lido do banco.

    ⚠️ **Não existia asserção nenhuma sobre `ingresso`** (code review da Epic 3):
    `test_ingresso.py` exercita comportamento pela rota e nunca chama
    `inspect()`. As três decisões que a migração declara no docstring — as sete
    colunas, as FKs sem `CASCADE` e o `setor_id` deliberadamente sem índice —
    eram reversíveis por um `--autogenerate` distraído sem quebrar nada.

    Mesmo formato dos quatro testes de schema que a Story 3.5 ganhou para as
    tabelas dela, e pelo mesmo motivo.

    `usado_em` e `validado_por` entraram na migração da Story 4.1
    (`8b97ae6bae09`), antes de existir validação nenhuma — o consumidor é a
    leitura de `GET /ingressos`, não a porta.
    """
    inspetor = inspect(engine_teste)

    colunas = {coluna["name"] for coluna in inspetor.get_columns("ingresso")}
    assert colunas == {
        "id",
        "reserva_id",
        "evento_id",
        "setor_id",
        "titular_nome",
        "assinatura",
        "nonce",
        "usado_em",
        "validado_por",
    }


def test_nenhuma_chave_estrangeira_do_ingresso_tem_cascade(
    engine_teste: Engine,
) -> None:
    """Apagar show, setor, reserva ou quem validou é recusado pelo banco.

    As quatro **sem** `ondelete`, e as quatro de propósito: um ingresso emitido é
    o passe de entrada de alguém que pagou, e nenhuma remoção de linha vizinha
    pode fazê-lo desaparecer em silêncio. É o mesmo argumento das três FKs da
    compra, um degrau acima — lá o que se perde é a intenção de comprar, aqui é
    a compra. `usuario` (via `validado_por`) entrou na migração da Story 4.1,
    pelo mesmo raciocínio de `reserva.cliente_id`: apagar quem já validou um
    ingresso na porta tem que doer, não sumir a validação em cascata.
    """
    inspetor = inspect(engine_teste)
    do_ingresso = {
        chave["referred_table"]: chave
        for chave in inspetor.get_foreign_keys("ingresso")
    }

    assert set(do_ingresso) == {"reserva", "evento", "setor", "usuario"}
    for tabela in ("reserva", "evento", "setor", "usuario"):
        assert "ondelete" not in do_ingresso[tabela]["options"], (
            f"a FK de ingresso para {tabela} ganhou ondelete — "
            "apagar venda tem que doer"
        )


def test_so_as_chaves_estrangeiras_lidas_do_ingresso_tem_indice(
    engine_teste: Engine,
) -> None:
    """Duas com índice, uma sem — e a que fica sem é decisão, não esquecimento.

    `reserva_id` é o `where` de "os canhotos desta reserva" e `evento_id` é o da
    portaria na Epic 5. `setor_id` não é lido por nenhuma story planejada:
    índice preventivo é peso sem gargalo demonstrado, como em `reserva.evento_id`.
    """
    inspetor = inspect(engine_teste)

    indices = {i["name"] for i in inspetor.get_indexes("ingresso")}
    assert "ix_ingresso_reserva_id" in indices
    assert "ix_ingresso_evento_id" in indices

    colunas_indexadas = {
        coluna
        for indice in inspetor.get_indexes("ingresso")
        for coluna in indice["column_names"]
    }
    assert "setor_id" not in colunas_indexadas


def test_usado_em_e_validado_por_sao_anulaveis_e_usado_em_carrega_fuso(
    engine_teste: Engine,
) -> None:
    """As duas colunas do AD-6 (Story 4.1) — `NULL` é "nunca validado".

    `usado_em` com TIMESTAMPTZ (AD-11): é contra ele que `GET /ingressos`
    decide *Ativos* de *Utilizados*, e é o que permite comparar com o `now()`
    do Postgres na Story 5.2 sem conversão de fuso pelo caminho.
    """
    inspetor = inspect(engine_teste)
    colunas = {c["name"]: c for c in inspetor.get_columns("ingresso")}

    assert colunas["usado_em"]["nullable"] is True
    assert colunas["usado_em"]["type"].timezone is True
    assert colunas["validado_por"]["nullable"] is True


def test_validado_por_referencia_usuario_sem_cascade_e_sem_indice(
    engine_teste: Engine,
) -> None:
    """Apagar uma conta de portaria que já validou um ingresso é recusado.

    Sem índice, de propósito: nenhuma story planejada filtra ingresso por quem
    validou — a coluna existe para o painel dizer *quem* validou, não para ser
    o `where` de uma consulta.
    """
    inspetor = inspect(engine_teste)
    chaves = {
        chave["referred_table"]: chave
        for chave in inspetor.get_foreign_keys("ingresso")
    }

    assert chaves["usuario"]["constrained_columns"] == ["validado_por"]
    assert "ondelete" not in chaves["usuario"]["options"]

    colunas_indexadas = {
        coluna
        for indice in inspetor.get_indexes("ingresso")
        for coluna in indice["column_names"]
    }
    assert "validado_por" not in colunas_indexadas
