"""Prova que a migração Alembic é a única forma de o schema nascer.

`upgrade head` num banco vazio cria as tabelas do projeto; `downgrade base` as
derruba por inteiro; `upgrade` de novo funciona sem erro. É a garantia de que
o banco pode ser reconstruído do zero.

⚠️ **Toda migração nova entra aqui.** O teste de ida e volta lista as tabelas
nominalmente: uma revisão com o `downgrade()` quebrado só é notada se alguém
acrescentar a tabela dela à lista.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from alembic import command
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.seguranca import conferir_codigo, gerar_hash, gerar_nonce
from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
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

    for coluna in ("data_hora", "data_hora_fim", "publicado_em", "criado_em"):
        assert colunas_evento[coluna]["type"].timezone is True


def test_data_hora_fim_e_obrigatoria_e_tem_o_check_do_banco(
    engine_teste: Engine,
) -> None:
    """A coluna do término (`a1c9f4d3b7e2`), lida do banco.

    ⚠️ **`NOT NULL`, e é essa palavra que faz o conserto valer para os eventos que
    já existiam.** *Descartei* deixá-la anulável na techspec
    `docs/techspec-fim-do-evento.md`: nada seria inventado, mas `porta_aberta`, a
    tela do ingresso e a do turno passariam a carregar um "e se não tem término?"
    para sempre — e os eventos de produção continuariam exatamente com o bug.
    Invariante que vale para os novos e não para os antigos é invariante pela
    metade.

    O `CHECK` é rede de segurança, não a regra: quem recusa em português é o
    `FIM_ANTES_DO_INICIO` do service. Ele é lido daqui, e não por comportamento,
    porque nenhuma rota consegue chegar até ele — a prova por `INSERT` direto mora
    em `test_evento.py`, com as outras invariantes que só o banco garante.
    """
    inspetor = inspect(engine_teste)
    colunas = {c["name"]: c for c in inspetor.get_columns("evento")}

    assert colunas["data_hora_fim"]["nullable"] is False

    # `ck_evento_` é o prefixo que a convenção de nomes do `Base.metadata` aplica,
    # e é ele que a migração e o modelo produzem — o nome curto entra nos dois
    # lugares, e quem monta o nome final é a convenção, num lugar só.
    restricoes = {c["name"] for c in inspetor.get_check_constraints("evento")}
    assert "ck_evento_fim_depois_do_inicio" in restricoes


def test_evento_gravado_antes_da_migracao_ganha_seis_horas_de_show(
    engine_teste: Engine,
) -> None:
    """⚠️ **O teste que autoriza a frase "o defeito some também no que já existe".**

    A `a1c9f4d3b7e2` não zera nada nem deixa buraco: ela calcula `data_hora + 6h`
    para toda linha que já estava no banco — inclusive as da Railway, que servem o
    roteiro de avaliação. Sem este teste, um `UPDATE` errado no meio da migração
    só apareceria como um evento encerrado no meio de um teste manual, e a
    alternativa descartada (coluna anulável) seria indistinguível da escolhida
    para quem lê a suíte.

    **As seis horas são folga deliberada, e a asserção as prende.** Com três, um
    evento antigo do banco poderia aparecer já encerrado no meio de um teste — e o
    comportamento novo seria descoberto pelo susto, e não pela leitura.

    O caminho é o de um evento de verdade gravado antes da mudança: volta-se à
    revisão anterior, grava-se a linha **sem** a coluna (por SQL cru — o modelo de
    hoje não sabe escrever `Evento` sem `data_hora_fim`), roda-se `upgrade head` e
    lê-se o resultado.

    ⚠️ **Ele comita, então ele limpa** — mesma disciplina do teste do ingresso
    logo abaixo: roda fora da transação revertida do `conftest.py`, e o `finally`
    devolve o banco ao `head` mesmo se a asserção falhar.
    """
    cfg = _config_alembic()
    Fabrica = sessionmaker(bind=engine_teste, expire_on_commit=False)

    organizador_id = uuid4()
    evento_id = uuid4()
    comeco = datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc)

    try:
        # Volta ao schema de antes: `evento` sem `data_hora_fim`.
        command.downgrade(cfg, "e5bf44a9f826")

        with Fabrica() as preparo:
            preparo.add(
                Usuario(
                    id=organizador_id,
                    nome="Organizador de antes do término",
                    email=f"org-fim-{organizador_id}@exemplo.com",
                    senha_hash=gerar_hash("rockhub"),
                    papel=PapelUsuario.ORGANIZADOR.value,
                )
            )
            preparo.flush()
            # SQL cru: o `Evento` de hoje tem `data_hora_fim`, que nesta revisão
            # do schema não existe — pelo ORM o `INSERT` sairia com a coluna.
            preparo.execute(
                text(
                    "INSERT INTO evento "
                    "(id, organizador_id, nome, data_hora, local, cidade, "
                    " origem_externa_id, publicado_em) "
                    "VALUES (:id, :organizador, :nome, :data_hora, :local, "
                    " :cidade, :origem, :publicado)"
                ),
                {
                    "id": evento_id,
                    "organizador": organizador_id,
                    "nome": "Show sem hora de acabar",
                    "data_hora": comeco,
                    "local": "Espaço Unimed",
                    "cidade": "São Paulo",
                    "origem": "G5vYZ9a1kd",
                    "publicado": datetime.now(timezone.utc),
                },
            )
            preparo.commit()

        command.upgrade(cfg, "head")

        with Fabrica() as leitura:
            fim = leitura.execute(
                text("SELECT data_hora_fim FROM evento WHERE id = :id"),
                {"id": evento_id},
            ).scalar_one()

        assert fim == comeco + timedelta(hours=6)
    finally:
        with Fabrica() as limpeza:
            limpeza.execute(text("DELETE FROM evento WHERE id = :id"), {"id": evento_id})
            limpeza.execute(
                text("DELETE FROM usuario WHERE id = :id"), {"id": organizador_id}
            )
            limpeza.commit()
        command.upgrade(cfg, "head")


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
        # ⚠️ **A oitava, e a que faltava de novo** (code review da Epic 5). A
        # `e5bf44a9f826`, da Story 5.6, é a migração nova que o comentário logo
        # acima manda registrar aqui — e ela entrou sem a linha, repetindo em uma
        # epic o que a Epic 3 já tinha corrigido uma vez. Quem acrescentar a nona
        # acrescenta a linha aqui.
        "validacao",
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


def test_upgrade_cria_a_tabela_ingresso_com_as_dez_colunas(
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
    leitura de `GET /ingressos`, não a porta. `share_token` entrou na da 4.3
    (`ed0bb0dad2a3`): é o endereço do link compartilhável, e `NULL` nele é
    "nunca compartilhado" **ou** "revogado".

    A `97672aee94c4` trocou duas das dez sem mudar a contagem: `assinatura` saiu e
    `codigo` entrou (8 símbolos de Crockford em vez dos 43 de base64), e
    `titular_nome` virou `pagador_nome` — o ingresso passou a estar no nome da
    conta, e a coluna guarda quem pagou (techspec
    `docs/techspec-codigo-curto.md`).
    """
    inspetor = inspect(engine_teste)

    colunas = {coluna["name"] for coluna in inspetor.get_columns("ingresso")}
    assert colunas == {
        "id",
        "reserva_id",
        "evento_id",
        "setor_id",
        "pagador_nome",
        "codigo",
        "nonce",
        "usado_em",
        "validado_por",
        "share_token",
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

    A tabela tem um terceiro índice desde a Story 4.3 — o único de
    `share_token` —, e ele não contradiz nada aqui: não é chave estrangeira, e
    é o `where` exato da rota pública do link. O teste dele é o próximo.
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


def test_share_token_e_anulavel_e_tem_indice_unico(engine_teste: Engine) -> None:
    """A coluna do link compartilhável (Story 4.3), lida do banco.

    **Anulável**, porque `NULL` é o estado de quem nunca compartilhou **e** o de
    quem revogou (Story 4.4) — os dois são o mesmo estado, de propósito.

    ⚠️ **Índice único, e não um índice comum.** Ele é o `where` da rota pública
    `GET /ingressos/compartilhados/{token}`, e a unicidade é o que garante que
    um token endereça um ingresso só. No Postgres `NULL` não colide com `NULL`
    num índice único, então milhares de ingressos sem link convivem sem índice
    parcial nenhum — e é justamente por isso que um `--autogenerate` distraído
    poderia trocar `unique=True` por `unique=False` sem quebrar teste nenhum de
    comportamento. Este é o teste que quebra.
    """
    inspetor = inspect(engine_teste)
    colunas = {c["name"]: c for c in inspetor.get_columns("ingresso")}

    assert colunas["share_token"]["nullable"] is True

    (indice,) = [
        i
        for i in inspetor.get_indexes("ingresso")
        if i["column_names"] == ["share_token"]
    ]
    assert indice["unique"] is True


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


def test_codigo_tem_oito_caracteres_e_indice_unico(engine_teste: Engine) -> None:
    """A coluna que a portaria usa como `where` (`97672aee94c4`).

    **`String(8)` sem folga**, ao contrário do `String(64)` que a `assinatura`
    tinha: ali a folga era para o dia em que o algoritmo mudasse; aqui o tamanho
    **é** o contrato, porque é ele que torna o campo manual usável na fila.

    ⚠️ **Índice único, e é ele que faz a colisão acontecer no lugar certo.** Com 40
    bits, dois códigos iguais deixaram de ser impossíveis; sem o único, as duas
    linhas conviveriam e a validação — que acha a linha *pelo* código — escolheria
    uma em silêncio. Com ele, a emissão recebe `IntegrityError` e sorteia outro
    `nonce`. Um `--autogenerate` distraído que trocasse `unique=True` por `False`
    não quebraria teste de comportamento nenhum; quebra este.
    """
    inspetor = inspect(engine_teste)
    colunas = {c["name"]: c for c in inspetor.get_columns("ingresso")}

    assert colunas["codigo"]["nullable"] is False
    assert colunas["codigo"]["type"].length == 8

    (indice,) = [
        i for i in inspetor.get_indexes("ingresso") if i["column_names"] == ["codigo"]
    ]
    assert indice["unique"] is True


def test_ingresso_emitido_antes_da_migracao_continua_valido(
    engine_teste: Engine,
) -> None:
    """⚠️ **O teste que autoriza a frase "nenhum ingresso foi invalidado".**

    A `97672aee94c4` não zera a tabela: o código novo é derivável das colunas que
    já existiam (`id`, `evento_id`, `nonce`), e ela **calcula** o valor de cada
    linha. Sem este teste, a alternativa descartada na techspec — apagar os
    ingressos existentes — seria indistinguível da escolhida para quem lê a suíte,
    e um `UPDATE` errado no meio da migração só apareceria na fila da porta.

    O caminho é o de um ingresso de verdade emitido antes da mudança: volta-se à
    revisão anterior, grava-se a linha **no formato antigo** (`assinatura` e
    `titular_nome`, por SQL cru — o modelo de hoje não sabe escrever essas
    colunas), roda-se `upgrade head` e confere-se o código resultante com o mesmo
    `conferir_codigo` que a portaria vai chamar.

    ⚠️ **Ele comita, então ele limpa** — mesma disciplina dos testes de corrida:
    roda fora da transação revertida do `conftest.py`, e o `finally` devolve o
    banco ao `head` mesmo se a asserção falhar.
    """
    cfg = _config_alembic()
    Fabrica = sessionmaker(bind=engine_teste, expire_on_commit=False)

    organizador_id = uuid4()
    cliente_id = uuid4()
    evento_id = uuid4()
    setor_id = uuid4()
    reserva_id = uuid4()
    ingresso_id = uuid4()
    nonce = gerar_nonce()

    try:
        # Volta ao schema de antes: `ingresso` com `assinatura` e `titular_nome`.
        command.downgrade(cfg, "ed0bb0dad2a3")

        with Fabrica() as preparo:
            preparo.add_all(
                [
                    Usuario(
                        id=organizador_id,
                        nome="Organizador da migração",
                        email=f"org-mig-{organizador_id}@exemplo.com",
                        senha_hash=gerar_hash("rockhub"),
                        papel=PapelUsuario.ORGANIZADOR.value,
                    ),
                    Usuario(
                        id=cliente_id,
                        nome="Cliente da migração",
                        email=f"cli-mig-{cliente_id}@exemplo.com",
                        senha_hash=gerar_hash("rockhub"),
                        papel=PapelUsuario.CLIENTE.value,
                    ),
                ]
            )
            preparo.flush()
            # ⚠️ **SQL cru para o evento também, e pelo motivo inverso ao do
            # ingresso logo abaixo** (14/08/2026). Lá o modelo de hoje não sabe
            # escrever colunas que já não existem; aqui ele sabe escrever uma que
            # ainda **não** existe — `data_hora_fim` nasce na `a1c9f4d3b7e2`, e
            # esta revisão é anterior a ela. Pelo ORM, o `INSERT` sairia com a
            # coluna e estouraria `UndefinedColumn`.
            preparo.execute(
                text(
                    "INSERT INTO evento "
                    "(id, organizador_id, nome, data_hora, local, cidade, "
                    " origem_externa_id, publicado_em) "
                    "VALUES (:id, :organizador, :nome, :data_hora, :local, "
                    " :cidade, :origem, :publicado)"
                ),
                {
                    "id": evento_id,
                    "organizador": organizador_id,
                    "nome": "Show de antes da migração",
                    "data_hora": datetime.now(timezone.utc) + timedelta(days=30),
                    "local": "Espaço Unimed",
                    "cidade": "São Paulo",
                    "origem": "G5vYZ9a1kd",
                    "publicado": datetime.now(timezone.utc),
                },
            )
            preparo.add(
                Setor(
                    id=setor_id,
                    evento_id=evento_id,
                    nome="Pista",
                    capacidade=10,
                    vendidos=1,
                    preco_centavos=12000,
                )
            )
            preparo.flush()
            preparo.add(
                Reserva(
                    id=reserva_id,
                    cliente_id=cliente_id,
                    evento_id=evento_id,
                    estado=EstadoReserva.PAGA.value,
                    expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
                    total_centavos=12000,
                )
            )
            preparo.flush()
            # SQL cru: o `Ingresso` de hoje tem `codigo` e `pagador_nome`, que
            # nesta revisão do schema não existem. A `assinatura` gravada aqui é
            # texto qualquer de propósito — a migração **não** a lê, ela recalcula
            # do `nonce`, e é isso que este teste está afirmando.
            preparo.execute(
                text(
                    "INSERT INTO ingresso "
                    "(id, reserva_id, evento_id, setor_id, titular_nome, "
                    " assinatura, nonce) "
                    "VALUES (:id, :reserva, :evento, :setor, :titular, "
                    " :assinatura, :nonce)"
                ),
                {
                    "id": ingresso_id,
                    "reserva": reserva_id,
                    "evento": evento_id,
                    "setor": setor_id,
                    "titular": "Nome do formato antigo",
                    "assinatura": "assinatura-do-formato-antigo",
                    "nonce": nonce,
                },
            )
            preparo.commit()

        command.upgrade(cfg, "head")

        with Fabrica() as leitura:
            codigo, pagador = leitura.execute(
                text("SELECT codigo, pagador_nome FROM ingresso WHERE id = :id"),
                {"id": ingresso_id},
            ).one()

        # O ingresso emitido antes da mudança passa na porta depois dela.
        assert conferir_codigo(codigo, ingresso_id, evento_id, nonce) is True
        # E o `RENAME COLUMN` preservou o conteúdo: quem pagou continua gravado.
        assert pagador == "Nome do formato antigo"
    finally:
        with Fabrica() as limpeza:
            limpeza.execute(
                text("DELETE FROM ingresso WHERE id = :id"), {"id": ingresso_id}
            )
            limpeza.execute(
                text("DELETE FROM reserva WHERE id = :id"), {"id": reserva_id}
            )
            limpeza.execute(text("DELETE FROM setor WHERE id = :id"), {"id": setor_id})
            limpeza.execute(text("DELETE FROM evento WHERE id = :id"), {"id": evento_id})
            limpeza.execute(
                text("DELETE FROM usuario WHERE id IN (:um, :outro)"),
                {"um": cliente_id, "outro": organizador_id},
            )
            limpeza.commit()
        # Devolve o banco ao `head` mesmo se a asserção acima falhou: os testes
        # seguintes contam com o schema atual.
        command.upgrade(cfg, "head")
