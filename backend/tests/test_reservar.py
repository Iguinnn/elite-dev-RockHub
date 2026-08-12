"""Rotas `POST /reservas` e `GET /reservas/{id}` (Story 3.6) — reservar sem
vender o mesmo lugar duas vezes.

Precisa do Compose no ar: grava eventos e reservas de verdade e lê pelas rotas.

⚠️ **Nome diferente de `test_reserva.py`**, que é da Story 3.5 e prova o
*schema* das duas tabelas. Este prova o **comportamento**: a regra, a transação
e o `UPDATE` condicional do AD-3.

**Quatro coisas que estes testes existem para travar:**

- **A corrida do AD-3.** Duas conexões disputando o último ingresso e exatamente
  uma vencendo — o único teste do arquivo que **não** passa pelo `TestClient`, e
  o motivo está escrito no docstring dele.
- **O "tudo ou nada".** Um pedido com dois setores faz dois `UPDATE`; se o
  segundo não couber, o primeiro tem que desaparecer. Nenhuma reserva pela
  metade, nenhum estoque consumido por um pedido recusado.
- **A ordem das quatro recusas**, que é o que mantém um corpo malformado sem
  rastro no banco.
- **O estoque fora do contrato** (UX-DR7, AD-13). A varredura de palavras
  proibidas é a **quarta** lista diferente do projeto, e a mais fácil de errar:
  `quantidade`, `total_centavos` e `preco_unitario_centavos` são chaves
  **legítimas** aqui. Quantidade que a pessoa pediu não é estoque; quantidade que
  resta é.

**Helpers locais, e não no `conftest.py`** — a convenção real da suíte é helper
por módulo (`test_programacao.py`, `test_organizador_eventos.py`).
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.seguranca import gerar_hash
from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.services.evento import MAXIMO_POR_COMPRA
from app.services.reserva import PRAZO_DE_RESERVA_MINUTOS

# As oito chaves do `ReservaSaida`, e nenhuma a mais (AC9).
CHAVES_DA_RESERVA = {
    "id",
    "evento_id",
    "evento_nome",
    "evento_data_hora",
    "estado",
    "expira_em",
    "total_centavos",
    "itens",
}

# As quatro do `ItemDaReservaSaida`.
CHAVES_DO_ITEM = {
    "setor_id",
    "setor_nome",
    "quantidade",
    "preco_unitario_centavos",
}

# ⚠️ **A quarta lista de palavras proibidas do projeto**, e a que mais difere
# das anteriores. `preco_unitario_centavos`, `quantidade` e `total_centavos` são
# chaves legítimas desta resposta — o que continua proibido é o inventário:
# quanto cabe e quanto já saiu.
PALAVRAS_DE_ESTOQUE = ("capacidade", "vendidos", "proporcao", "disponibilidade", "esgotado")


def _daqui_a(dias: int) -> datetime:
    """Data relativa ao relógio: o recorte destas rotas é `data_hora >= agora`."""
    return datetime.now(timezone.utc) + timedelta(days=dias)


def _evento_publicado(
    sessao: Session,
    organizador: Usuario,
    *,
    nome: str = "Baco Exu do Blues",
    data_hora: datetime | None = None,
    publicado: bool = True,
    setores: list[tuple[str, int, int, int]] | None = None,
) -> Evento:
    """Um evento com setores, gravado direto pelo ORM.

    Mesmo precedente do `test_programacao.py`: não passa pela rota de publicação
    de propósito, porque a fixture é o **estado** de que estas rotas precisam, e
    não o caminho que o produz — e dois dos estados exercitados aqui (rascunho e
    data passada) não são produzíveis por tela nenhuma.

    Cada setor é `(nome, capacidade, vendidos, preco_centavos)`. `vendidos` entra
    na tupla porque quase todo teste daqui parte de um estoque já mexido: setor
    esgotado, setor com um lugar só, setor cheio menos dois.

    ⚠️ **`publicado: bool`, e não `publicado_em: datetime | None`** — mesmo ponto
    cego do helper da 3.1: `None` seria ao mesmo tempo "não informei" e "é
    rascunho".
    """
    if setores is None:
        setores = [("Pista", 800, 0, 12000)]

    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or _daqui_a(30),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=(
            datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc) if publicado else None
        ),
        setores=[
            Setor(
                nome=nome_do_setor,
                capacidade=capacidade,
                vendidos=vendidos,
                preco_centavos=preco,
            )
            for nome_do_setor, capacidade, vendidos, preco in setores
        ],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    """Login de verdade: o cookie do teste é o mesmo que o navegador teria."""
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _por_nome(evento: Evento) -> dict[str, Setor]:
    return {setor.nome: setor for setor in evento.setores}


def _corpo(evento: Evento, *itens: tuple[Setor, int]) -> dict:
    """`{evento_id, itens}` a partir de objetos — o que quase todo teste manda."""
    return {
        "evento_id": str(evento.id),
        "itens": [
            {"setor_id": str(setor.id), "quantidade": quantidade}
            for setor, quantidade in itens
        ],
    }


# --------------------------------------------------------------------------- #
# AC1 — a reserva nasce PENDENTE, com prazo, total e estoque consumido
# --------------------------------------------------------------------------- #


def test_a_reserva_nasce_pendente_com_prazo_de_dez_minutos(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org1@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente1@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    antes = datetime.now(timezone.utc)
    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 2)))

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["estado"] == EstadoReserva.PENDENTE.value

    expira_em = datetime.fromisoformat(corpo["expira_em"])
    prazo = expira_em - antes
    # Uma janela, e não igualdade: entre ler o relógio aqui e o service ler o
    # dele passam alguns milissegundos. O que o AC afirma é "dez minutos", não
    # "dez minutos e zero microssegundos".
    assert timedelta(minutes=PRAZO_DE_RESERVA_MINUTOS) - timedelta(seconds=10) <= prazo
    assert prazo <= timedelta(minutes=PRAZO_DE_RESERVA_MINUTOS) + timedelta(seconds=10)

    gravada = sessao.get(Reserva, UUID(corpo["id"]))
    assert gravada is not None
    assert gravada.cliente_id == comprador.id
    assert gravada.evento_id == evento.id
    assert gravada.estado == EstadoReserva.PENDENTE.value
    # TIMESTAMPTZ (AD-11): o que volta do Postgres tem fuso.
    assert gravada.expira_em.tzinfo is not None


def test_o_estoque_do_setor_sobe_exatamente_a_quantidade_pedida(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`setor.vendidos` sai de zero pela primeira vez na vida do projeto."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org2@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente2@exemplo.com")
    evento = _evento_publicado(
        sessao, organizador, setores=[("Pista", 800, 40, 12000)]
    )
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 3)))

    assert resposta.status_code == 201
    # Lido do banco, e não do corpo da resposta: o corpo prova o schema, só o
    # `SELECT` prova a escrita.
    assert sessao.get(Setor, pista.id).vendidos == 43


def test_um_item_por_setor_pedido_com_o_preco_congelado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org3@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente3@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 2)))

    assert resposta.status_code == 201
    itens = sessao.scalars(
        select(ItemReserva).where(ItemReserva.reserva_id == UUID(resposta.json()["id"]))
    ).all()
    assert len(itens) == 1
    assert itens[0].setor_id == pista.id
    assert itens[0].quantidade == 2
    assert itens[0].preco_unitario_centavos == 12000


def test_dois_setores_no_mesmo_pedido_somam_no_total_e_geram_dois_itens(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org4@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente4@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Pista", 800, 0, 12000), ("Camarote", 60, 0, 42000)],
    )
    setores = _por_nome(evento)
    _entrar(cliente, comprador)

    resposta = cliente.post(
        "/reservas",
        json=_corpo(evento, (setores["Pista"], 2), (setores["Camarote"], 1)),
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["total_centavos"] == 2 * 12000 + 42000
    assert len(corpo["itens"]) == 2
    assert sessao.get(Setor, setores["Pista"].id).vendidos == 2
    assert sessao.get(Setor, setores["Camarote"].id).vendidos == 1


# --------------------------------------------------------------------------- #
# AC3 — a corrida do AD-3
# --------------------------------------------------------------------------- #


def test_duas_conexoes_disputando_o_ultimo_ingresso_e_so_uma_vence(
    engine_teste: Engine,
) -> None:
    """**O teste mais importante da story, e o único fora do `TestClient`.**

    A fixture `cliente` do `conftest.py` amarra o app a **uma** sessão revertida
    (`dependency_overrides`): duas chamadas HTTP "concorrentes" ali dentro
    compartilhariam a mesma transação, e a corrida nunca aconteceria. O teste
    passaria sem ter provado nada — que é o pior tipo de teste verde.

    Aqui são duas `Session` em **conexões distintas** do `engine_teste`, soltas
    juntas por um `threading.Barrier(2)`, com **commit de verdade**. O Postgres
    bloqueia a linha para a segunda transação e, ao liberá-la, **reavalia o
    `WHERE` contra a versão nova** (READ COMMITTED) — é exatamente isso que faz o
    AD-3 funcionar.

    ⚠️ **A asserção é `sum(...) == 1`, e não "a primeira venceu".** Qual das duas
    chega antes é do escalonador do sistema operacional; que só uma vença é do
    banco. Assertar a ordem seria testar o escalonador, e o teste ficaria flaky
    sem nenhum ganho.

    ⚠️ **Este teste comita, então ele limpa.** Ele não está dentro da transação
    revertida do `conftest.py`; sem o `finally`, as linhas ficariam no
    `rockhub_teste` e o próximo `pytest` começaria sujo — o `downgrade base` da
    fixture de sessão limpa uma vez por suíte, não entre testes.
    """
    Fabrica = sessionmaker(bind=engine_teste)

    organizador_id = uuid4()
    evento_id = uuid4()
    setor_id = uuid4()

    with Fabrica() as preparo:
        preparo.add(
            Usuario(
                id=organizador_id,
                nome="Organizador da corrida",
                email=f"corrida-{organizador_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.ORGANIZADOR.value,
            )
        )
        # ⚠️ `flush` entre os dois: não há `relationship` entre `Evento` e
        # `Usuario` (decisão da Story 2.3), e sem relação declarada o
        # SQLAlchemy não tem como ordenar os dois `INSERT` — o do evento saía
        # primeiro e batia na FK `fk_evento_organizador_id_usuario`.
        preparo.flush()
        preparo.add(
            Evento(
                id=evento_id,
                organizador_id=organizador_id,
                nome="Show da corrida",
                data_hora=_daqui_a(30),
                local="Espaço Unimed",
                cidade="São Paulo",
                origem_externa_id="G5vYZ9a1kd",
                publicado_em=datetime.now(timezone.utc),
                # Um lugar, e um só: é o "último ingresso" que as duas disputam.
                setores=[
                    Setor(
                        id=setor_id,
                        nome="Pista",
                        capacidade=1,
                        vendidos=0,
                        preco_centavos=12000,
                    )
                ],
            )
        )
        preparo.commit()

    try:
        inicio = threading.Barrier(2)
        resultados: list[int] = []
        trava = threading.Lock()

        def tentar() -> None:
            with Fabrica() as s:
                # As duas soltam juntas, cada uma na sua conexão.
                inicio.wait()
                r = s.execute(
                    update(Setor)
                    .where(
                        Setor.id == setor_id,
                        Setor.vendidos + 1 <= Setor.capacidade,
                    )
                    .values(vendidos=Setor.vendidos + 1)
                    .execution_options(synchronize_session=False)
                )
                s.commit()
                with trava:
                    resultados.append(r.rowcount)

        threads = [threading.Thread(target=tentar) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert len(resultados) == 2
        # Exatamente uma afetou uma linha; a outra, nenhuma.
        assert sum(resultados) == 1

        with Fabrica() as leitura:
            setor = leitura.get(Setor, setor_id)
            assert setor is not None
            # Nunca `capacidade + 1`. É esta linha que o desafio pontua.
            assert setor.vendidos == setor.capacidade
    finally:
        with Fabrica() as limpeza:
            limpeza.execute(delete(Setor).where(Setor.id == setor_id))
            limpeza.execute(delete(Evento).where(Evento.id == evento_id))
            limpeza.execute(delete(Usuario).where(Usuario.id == organizador_id))
            limpeza.commit()


def test_segunda_reserva_num_setor_esgotado_recebe_409(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A versão sequencial e determinística da corrida, pela rota."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org5@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente5@exemplo.com")
    evento = _evento_publicado(sessao, organizador, setores=[("Pista", 1, 0, 12000)])
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    primeira = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))
    segunda = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))

    assert primeira.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"
    assert sessao.get(Setor, pista.id).vendidos == 1


# --------------------------------------------------------------------------- #
# AC4 — o "tudo ou nada"
# --------------------------------------------------------------------------- #


def test_pedido_maior_que_o_estoque_nao_deixa_rastro_nenhum(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """2 na Pista (que tem) e 3 no Camarote (que não tem): nada é gravado.

    ⚠️ **Cinco ingressos, e não sete**: acima de `MAXIMO_POR_COMPRA` a recusa
    seria o `422` do teto, que acontece antes de o estoque ser tocado — e o teste
    do "tudo ou nada" precisa justamente do caminho em que o primeiro `UPDATE`
    já aconteceu.

    ⚠️ **Os dois `sessao.commit()`/`sessao.rollback()` ao redor da chamada não
    são cerimônia — eles reproduzem no teste o que `obter_sessao` faz em
    produção.** Lá, a exceção atravessa o gerador e o `finally: sessao.close()`
    descarta o trabalho não confirmado. Aqui, `dependency_overrides` entrega a
    mesma `Session` do teste e **não a fecha**, então o `UPDATE` da Pista fica
    pendente na sessão depois do `409`.

    O `commit` antes sela o evento e os setores (senão o `rollback` os levaria
    junto); o `rollback` depois é o `close()` de produção. **É justamente isso
    que dá valor à asserção**: se o service tivesse confirmado alguma coisa antes
    de recusar, o `rollback` não desfaria, e a Pista apareceria com 2 vendidos.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org6@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente6@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Pista", 800, 0, 12000), ("Camarote", 60, 58, 42000)],
    )
    setores = _por_nome(evento)
    _entrar(cliente, comprador)
    sessao.commit()

    resposta = cliente.post(
        "/reservas",
        json=_corpo(evento, (setores["Pista"], 2), (setores["Camarote"], 3)),
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"

    sessao.rollback()

    # O `UPDATE` da Pista, que chegou a acontecer, desapareceu junto.
    assert sessao.get(Setor, setores["Pista"].id).vendidos == 0
    assert sessao.get(Setor, setores["Camarote"].id).vendidos == 58
    assert sessao.scalar(select(func.count()).select_from(Reserva)) == 0
    assert sessao.scalar(select(func.count()).select_from(ItemReserva)) == 0


# --------------------------------------------------------------------------- #
# AC5 — as quatro recusas, antes de qualquer escrita
# --------------------------------------------------------------------------- #


def test_itens_vazio_e_itens_ausente_recebem_o_mesmo_reserva_sem_item(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`default_factory=list` é o que faz os dois caírem na mesma regra."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org7@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente7@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    _entrar(cliente, comprador)

    vazio = cliente.post(
        "/reservas", json={"evento_id": str(evento.id), "itens": []}
    )
    ausente = cliente.post("/reservas", json={"evento_id": str(evento.id)})

    for resposta in (vazio, ausente):
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["codigo"] == "RESERVA_SEM_ITEM"


def test_o_mesmo_setor_duas_vezes_recebe_422_e_nunca_500(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem esta recusa, o `UNIQUE` da 3.5 viraria `IntegrityError` → `500`."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org8@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente8@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 1), (pista, 1)))

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ITEM_DUPLICADO"
    # E a recusa aconteceu antes de qualquer escrita.
    assert sessao.get(Setor, pista.id).vendidos == 0


def test_setor_de_outro_evento_e_setor_inexistente_recebem_o_mesmo_codigo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Um código só: distinguir transformaria a rota num oráculo."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org9@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente9@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    outro = _evento_publicado(sessao, organizador, nome="Outro show")
    setor_do_outro = _por_nome(outro)["Pista"]
    _entrar(cliente, comprador)

    de_outro_evento = cliente.post(
        "/reservas", json=_corpo(evento, (setor_do_outro, 1))
    )
    inexistente = cliente.post(
        "/reservas",
        json={
            "evento_id": str(evento.id),
            "itens": [{"setor_id": str(uuid4()), "quantidade": 1}],
        },
    )

    for resposta in (de_outro_evento, inexistente):
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["codigo"] == "SETOR_INVALIDO"

    # O setor do outro evento não foi tocado: a recusa vem antes do `UPDATE`.
    assert sessao.get(Setor, setor_do_outro.id).vendidos == 0


def test_quantidade_zero_e_negativa_sao_recusadas_pelo_pydantic(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`Field(ge=1)`: item de quantidade zero nem chega ao service."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org10@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente10@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    for quantidade in (0, -1):
        resposta = cliente.post(
            "/reservas",
            json={
                "evento_id": str(evento.id),
                "itens": [{"setor_id": str(pista.id), "quantidade": quantidade}],
            },
        )
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# AC6 — o mesmo recorte de "em cartaz" das quatro rotas públicas
# --------------------------------------------------------------------------- #


def test_os_tres_casos_fora_de_cartaz_recebem_o_mesmo_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Id inexistente, rascunho e data passada — um código e uma mensagem só.

    A mensagem é literalmente a do `GET /eventos/{id}`: para quem chama, os três
    significam a mesma coisa, e distinguir diria o que ainda não foi publicado.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org11@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente11@exemplo.com")
    rascunho = _evento_publicado(sessao, organizador, publicado=False)
    passado = _evento_publicado(
        sessao, organizador, nome="Show de ontem", data_hora=_daqui_a(-1)
    )
    _entrar(cliente, comprador)

    respostas = [
        cliente.post(
            "/reservas",
            json={
                "evento_id": str(uuid4()),
                "itens": [{"setor_id": str(uuid4()), "quantidade": 1}],
            },
        ),
        cliente.post(
            "/reservas", json=_corpo(rascunho, (_por_nome(rascunho)["Pista"], 1))
        ),
        cliente.post(
            "/reservas", json=_corpo(passado, (_por_nome(passado)["Pista"], 1))
        ),
    ]

    for resposta in respostas:
        assert resposta.status_code == 404
        assert resposta.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"
        assert resposta.json()["erro"]["mensagem"] == "Esse show não está em cartaz."

    # E o setor do rascunho continua intocado: sem o recorte, um link guardado
    # venderia ingresso para um show que ninguém publicou.
    assert sessao.get(Setor, _por_nome(rascunho)["Pista"].id).vendidos == 0


# --------------------------------------------------------------------------- #
# AC7 — papel na assinatura, e o id vindo da sessão
# --------------------------------------------------------------------------- #


def test_sem_cookie_as_duas_rotas_respondem_401(cliente: TestClient) -> None:
    """⚠️ `cookies.clear()`: o `TestClient` guarda cookie entre chamadas."""
    cliente.cookies.clear()

    post = cliente.post(
        "/reservas",
        json={
            "evento_id": str(uuid4()),
            "itens": [{"setor_id": str(uuid4()), "quantidade": 1}],
        },
    )
    get = cliente.get(f"/reservas/{uuid4()}")

    for resposta in (post, get):
        assert resposta.status_code == 401
        assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_organizador_e_portaria_recebem_403_nas_duas_rotas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Autenticação antes de autorização: com sessão e papel errado é `403`."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org12@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "porteiro12@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]

    for usuario in (organizador, porteiro):
        cliente.cookies.clear()
        _entrar(cliente, usuario)

        post = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))
        get = cliente.get(f"/reservas/{uuid4()}")

        for resposta in (post, get):
            assert resposta.status_code == 403
            assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"

    assert sessao.get(Setor, pista.id).vendidos == 0


def test_o_corpo_nao_tem_como_influenciar_o_dono_nem_o_prazo_nem_o_total(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem `extra="forbid"`, mas também sem caminho: os campos são ignorados.

    O corpo manda `cliente_id`, `estado`, `expira_em` e `total_centavos`. Nenhum
    deles existe no `ReservaEntrada`, então nenhum chega ao service — e a reserva
    nasce do dono da sessão, com o prazo e o total que a regra calculou.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org13@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente13@exemplo.com")
    outra_pessoa = fabricar_usuario(PapelUsuario.CLIENTE, "outra13@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    corpo = _corpo(evento, (pista, 1))
    corpo["cliente_id"] = str(outra_pessoa.id)
    corpo["estado"] = EstadoReserva.PAGA.value
    corpo["total_centavos"] = 1
    corpo["expira_em"] = "2030-01-01T00:00:00Z"

    resposta = cliente.post("/reservas", json=corpo)

    assert resposta.status_code == 201
    assert resposta.json()["total_centavos"] == 12000
    assert resposta.json()["estado"] == EstadoReserva.PENDENTE.value

    gravada = sessao.get(Reserva, UUID(resposta.json()["id"]))
    assert gravada is not None
    assert gravada.cliente_id == comprador.id


# --------------------------------------------------------------------------- #
# AC8 — GET /reservas/{id}: só vejo o que é meu
# --------------------------------------------------------------------------- #


def test_o_dono_le_a_reserva_com_os_itens_em_ordem_de_nome_de_setor(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org14@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente14@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[
            ("Pista", 800, 0, 12000),
            ("Área VIP", 40, 0, 60000),
            ("Camarote", 60, 0, 42000),
        ],
    )
    setores = _por_nome(evento)
    _entrar(cliente, comprador)

    criada = cliente.post(
        "/reservas",
        json=_corpo(
            evento,
            (setores["Pista"], 1),
            (setores["Área VIP"], 1),
            (setores["Camarote"], 1),
        ),
    )
    assert criada.status_code == 201

    resposta = cliente.get(f"/reservas/{criada.json()['id']}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == criada.json()["id"]
    assert corpo["evento_nome"] == "Baco Exu do Blues"
    assert corpo["total_centavos"] == 12000 + 60000 + 42000

    # ⚠️ **A ordem é comparada com a da página do evento, e não com uma lista
    # escrita à mão.** É literalmente o que o AC pede — "a mesma ordem da página
    # do evento" —, e uma lista fixa aqui afirmaria outra coisa: a minha ideia de
    # ordem alfabética. As duas discordam no primeiro nome com acento, porque o
    # `sorted()` do Python compara pontos de código e o `order_by` do
    # `relationship` é ordenado pelo Postgres, na collation do banco. "Área VIP"
    # está na lista justamente por isso.
    do_evento = cliente.get(f"/eventos/{evento.id}").json()
    ordem_da_pagina = [setor["nome"] for setor in do_evento["setores"]]

    assert [item["setor_nome"] for item in corpo["itens"]] == ordem_da_pagina
    assert [item["setor_nome"] for item in criada.json()["itens"]] == ordem_da_pagina
    # E a lista não é trivial: os três setores estão lá, em alguma ordem.
    assert sorted(ordem_da_pagina) == sorted(["Área VIP", "Camarote", "Pista"])


def test_reserva_de_outra_pessoa_e_id_inexistente_recebem_o_mesmo_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Nunca `403`: os dois casos significam a mesma coisa para quem chama."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org15@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono15@exemplo.com")
    intruso = fabricar_usuario(PapelUsuario.CLIENTE, "intruso15@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]

    _entrar(cliente, dono)
    criada = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))
    assert criada.status_code == 201

    cliente.cookies.clear()
    _entrar(cliente, intruso)

    alheia = cliente.get(f"/reservas/{criada.json()['id']}")
    inexistente = cliente.get(f"/reservas/{uuid4()}")

    for resposta in (alheia, inexistente):
        assert resposta.status_code == 404
        assert resposta.json()["erro"]["codigo"] == "RESERVA_NAO_ENCONTRADA"


def test_id_que_nao_e_uuid_recebe_422_do_pydantic(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente16@exemplo.com")
    _entrar(cliente, comprador)

    resposta = cliente.get("/reservas/banana")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# AC9 — o estoque não atravessa o contrato
# --------------------------------------------------------------------------- #


def test_o_corpo_tem_exatamente_as_chaves_do_contrato(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org17@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente17@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    criada = cliente.post("/reservas", json=_corpo(evento, (pista, 2)))
    lida = cliente.get(f"/reservas/{criada.json()['id']}")

    for resposta in (criada, lida):
        corpo = resposta.json()
        assert set(corpo) == CHAVES_DA_RESERVA
        for item in corpo["itens"]:
            assert set(item) == CHAVES_DO_ITEM


def test_nenhuma_palavra_de_estoque_aparece_no_texto_das_duas_respostas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A varredura é no **texto inteiro**, não nas chaves de topo.

    ⚠️ Se esta asserção reprovar, o defeito é o contrato — não a asserção. Um
    setor esgotado e outro quase cheio entram no evento de propósito: é o estado
    em que uma palavra de estoque teria motivo para vazar.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org18@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente18@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[
            ("Pista", 800, 799, 12000),
            ("Camarote", 60, 60, 42000),
        ],
    )
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    criada = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))
    lida = cliente.get(f"/reservas/{criada.json()['id']}")

    for resposta in (criada, lida):
        texto = resposta.text.casefold()
        for palavra in PALAVRAS_DE_ESTOQUE:
            assert palavra not in texto


# --------------------------------------------------------------------------- #
# AC10 — o preço é congelado no ato da reserva
# --------------------------------------------------------------------------- #


def test_o_preco_da_reserva_nao_muda_quando_o_setor_muda_de_preco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Ler `preco_centavos` para congelá-lo **não** viola o AC2: preço não é estoque."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org19@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente19@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    criada = cliente.post("/reservas", json=_corpo(evento, (pista, 2)))
    assert criada.status_code == 201

    # O organizador dobra o preço depois da reserva (por `psql`, hoje — não há
    # tela de editar evento).
    sessao.execute(
        update(Setor).where(Setor.id == pista.id).values(preco_centavos=24000)
    )
    sessao.flush()

    lida = cliente.get(f"/reservas/{criada.json()['id']}")

    assert lida.status_code == 200
    assert lida.json()["itens"][0]["preco_unitario_centavos"] == 12000
    assert lida.json()["total_centavos"] == 24000  # 2 × 12000, e não 2 × 24000


# --------------------------------------------------------------------------- #
# AC11 — o teto é da compra, e vem da mesma constante que a tela lê
# --------------------------------------------------------------------------- #


def test_a_soma_das_quantidades_e_o_que_estoura_o_teto(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """4 na Pista e 3 no Camarote são sete ingressos numa compra só."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org20@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente20@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Pista", 800, 0, 12000), ("Camarote", 60, 0, 42000)],
    )
    setores = _por_nome(evento)
    _entrar(cliente, comprador)

    resposta = cliente.post(
        "/reservas",
        json=_corpo(evento, (setores["Pista"], 4), (setores["Camarote"], 3)),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ACIMA_DO_MAXIMO_POR_COMPRA"
    # A recusa aconteceu antes de qualquer escrita.
    assert sessao.get(Setor, setores["Pista"].id).vendidos == 0


def test_exatamente_seis_passa_e_sete_nao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O teto é o `MAXIMO_POR_COMPRA` do `services/evento.py`, importado."""
    assert MAXIMO_POR_COMPRA == 6

    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org21@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente21@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _entrar(cliente, comprador)

    sete = cliente.post(
        "/reservas", json=_corpo(evento, (pista, MAXIMO_POR_COMPRA + 1))
    )
    seis = cliente.post("/reservas", json=_corpo(evento, (pista, MAXIMO_POR_COMPRA)))

    assert sete.status_code == 422
    assert sete.json()["erro"]["codigo"] == "ACIMA_DO_MAXIMO_POR_COMPRA"
    assert seis.status_code == 201
    assert sessao.get(Setor, pista.id).vendidos == MAXIMO_POR_COMPRA


# --------------------------------------------------------------------------- #
# O contrato publicado
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_as_duas_rotas_com_o_schema_da_reserva(
    cliente: TestClient,
) -> None:
    """O contrato publicado é o mesmo que o código promete.

    ⚠️ **Não há asserção sobre `security` aqui, e a ausência tem motivo.** O
    `usuario_atual` lê o cookie do `Request` à mão, e não por uma dependência
    `SecurityBase` do FastAPI — então **nenhuma** rota protegida deste projeto
    declara esquema de segurança no OpenAPI, nem as do organizador desde a Epic
    2. Assertar o contrário aqui exigiria mexer em `core/dependencias.py` e
    mudaria o contrato publicado de todas elas. O que garante a proteção destas
    duas são os testes de `401` e `403` acima, que exercitam a rota de verdade.
    """
    esquema = cliente.get("/openapi.json").json()

    criacao = esquema["paths"]["/reservas"]["post"]
    assert (
        criacao["responses"]["201"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/ReservaSaida")
    )
    # Nenhum parâmetro: o corpo é a entrada inteira, e o dono vem da sessão.
    assert criacao.get("parameters", []) == []

    leitura = esquema["paths"]["/reservas/{reserva_id}"]["get"]
    assert (
        leitura["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/ReservaSaida")
    )
    # Um parâmetro de caminho, e nenhum de query.
    assert {p["in"] for p in leitura["parameters"]} == {"path"}

    propriedades = esquema["components"]["schemas"]["ReservaSaida"]["properties"]
    assert set(propriedades) == CHAVES_DA_RESERVA
    item = esquema["components"]["schemas"]["ItemDaReservaSaida"]["properties"]
    assert set(item) == CHAVES_DO_ITEM
