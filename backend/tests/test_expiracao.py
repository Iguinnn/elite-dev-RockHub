"""Colheita preguiçosa das reservas vencidas (Story 3.7) — a devolução do estoque.

Precisa do Compose no ar: grava reservas vencidas de verdade e prova a devolução
lendo `setor.vendidos` do banco.

⚠️ **Terceiro arquivo sobre a mesma dupla de tabelas, e cada um prova outra
coisa.** `test_reserva.py` é o *schema* da 3.5; `test_reservar.py` é o
*comportamento* de reservar, com a corrida do AD-3; este é a *expiração* — o
único caminho do projeto em que `setor.vendidos` **desce**.

**Quatro coisas que estes testes existem para travar:**

- **A colheita acontece antes da tentativa** (AC2). O último lugar de um setor
  esgotado por uma reserva abandonada volta a ser vendável, e quem prova isso é
  um `201` onde antes havia `409`.
- **A reserva expira inteira.** Uma reserva com dois setores devolve os dois,
  mesmo que só um deles tenha sido pedido pela pessoa que disparou a colheita.
  Se este teste cair, existe estoque preso para sempre: a reserva já está
  `EXPIRADA` e nada volta a colhê-la.
- **O alcance é o setor pedido** (decisão do Igor), não o evento nem o banco.
- **Não existe worker nem cron** (AC3), e isso é uma varredura do código-fonte,
  não uma afirmação de README.

**Helpers locais**, como manda a convenção real da suíte — helper por módulo, e
não `conftest.py` inchado.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario

RAIZ_BACKEND = Path(__file__).resolve().parent.parent


def _daqui_a(dias: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=dias)


def _evento_publicado(
    sessao: Session,
    organizador: Usuario,
    *,
    setores: list[tuple[str, int, int, int]] | None = None,
) -> Evento:
    """Evento com setores, gravado direto pelo ORM — mesmo helper da 3.6.

    Cada setor é `(nome, capacidade, vendidos, preco_centavos)`. Aqui `vendidos`
    quase nunca é zero: todo teste deste arquivo parte de estoque **já
    consumido** por uma reserva que vai vencer.
    """
    if setores is None:
        setores = [("Pista", 1, 1, 12000)]

    evento = Evento(
        organizador_id=organizador.id,
        nome="Baco Exu do Blues",
        data_hora=_daqui_a(30),
        # Quatro horas de show — nada neste arquivo depende do término, e o valor
        # existe só para satisfazer a coluna obrigatória e o `CHECK`.
        data_hora_fim=_daqui_a(30) + timedelta(hours=4),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc),
        setores=[
            Setor(
                nome=nome,
                capacidade=capacidade,
                vendidos=vendidos,
                preco_centavos=preco,
            )
            for nome, capacidade, vendidos, preco in setores
        ],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


def _reserva(
    sessao: Session,
    cliente_dono: Usuario,
    evento: Evento,
    *itens: tuple[Setor, int],
    vencida: bool,
    estado: EstadoReserva = EstadoReserva.PENDENTE,
) -> Reserva:
    """Uma reserva gravada com o prazo já vencido (ou não), pelo ORM.

    ⚠️ **Não passa pelo `POST /reservas`** de propósito: a rota sempre cria com
    dez minutos à frente, e o estado de que estes testes precisam — uma reserva
    cujo prazo já passou — não é produzível por tela nenhuma. Mesmo precedente do
    helper de evento em rascunho da 3.1.
    """
    reserva = Reserva(
        cliente_id=cliente_dono.id,
        evento_id=evento.id,
        estado=estado.value,
        expira_em=(
            datetime.now(timezone.utc)
            + (timedelta(minutes=-1) if vencida else timedelta(minutes=10))
        ),
        total_centavos=sum(
            setor.preco_centavos * quantidade for setor, quantidade in itens
        ),
        itens=[
            ItemReserva(
                setor_id=setor.id,
                quantidade=quantidade,
                preco_unitario_centavos=setor.preco_centavos,
            )
            for setor, quantidade in itens
        ],
    )
    sessao.add(reserva)
    sessao.flush()
    sessao.refresh(reserva)
    return reserva


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _por_nome(evento: Evento) -> dict[str, Setor]:
    return {setor.nome: setor for setor in evento.setores}


def _corpo(evento: Evento, *itens: tuple[Setor, int]) -> dict:
    return {
        "evento_id": str(evento.id),
        "itens": [
            {"setor_id": str(setor.id), "quantidade": quantidade}
            for setor, quantidade in itens
        ],
    }


# --------------------------------------------------------------------------- #
# AC2 — as vencidas são liberadas antes da tentativa
# --------------------------------------------------------------------------- #


def test_reserva_vencida_libera_o_ultimo_lugar_para_outra_pessoa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O teste que a story inteira existe para fazer passar.

    Um setor de um lugar só, esgotado por quem abandonou o checkout. Sem a
    colheita esta chamada é `409 ESTOQUE_INSUFICIENTE`; com ela, é `201`.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e1@exemplo.com")
    desistente = fabricar_usuario(PapelUsuario.CLIENTE, "desistente1@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador1@exemplo.com")

    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    _reserva(sessao, desistente, evento, (pista, 1), vencida=True)
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))

    assert resposta.status_code == 201
    # O lugar não foi vendido duas vezes: um saiu, um entrou.
    assert sessao.get(Setor, pista.id).vendidos == 1


def test_a_reserva_colhida_fica_expirada_no_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e2@exemplo.com")
    desistente = fabricar_usuario(PapelUsuario.CLIENTE, "desistente2@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador2@exemplo.com")

    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    abandonada = _reserva(sessao, desistente, evento, (pista, 1), vencida=True)
    _entrar(cliente, comprador)

    assert cliente.post("/reservas", json=_corpo(evento, (pista, 1))).status_code == 201

    sessao.expire(abandonada)
    assert abandonada.estado == EstadoReserva.EXPIRADA.value
    # O prazo **não** é apagado ao expirar: ele é o prazo que valeu, e quem diz
    # se ainda importa é o estado.
    assert abandonada.expira_em is not None


def test_a_reserva_expira_inteira_e_devolve_setor_que_ninguem_pediu(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Se este cair, existe estoque preso para sempre.

    A colheita é disparada por quem pediu **Pista**, mas a reserva vencida
    segurava Pista *e* Camarote. Devolver só a Pista deixaria a reserva
    `EXPIRADA` com o Camarote consumido — e nada voltaria a colher aquilo,
    porque a transição já teria acontecido.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e3@exemplo.com")
    desistente = fabricar_usuario(PapelUsuario.CLIENTE, "desistente3@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador3@exemplo.com")

    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Pista", 10, 2, 12000), ("Camarote", 10, 3, 30000)],
    )
    setores = _por_nome(evento)
    pista, camarote = setores["Pista"], setores["Camarote"]
    _reserva(
        sessao, desistente, evento, (pista, 2), (camarote, 3), vencida=True
    )
    _entrar(cliente, comprador)

    assert cliente.post("/reservas", json=_corpo(evento, (pista, 1))).status_code == 201

    # Pista: 2 devolvidos, 1 consumido pela reserva nova.
    assert sessao.get(Setor, pista.id).vendidos == 1
    # Camarote: devolvido inteiro, apesar de ninguém tê-lo pedido.
    assert sessao.get(Setor, camarote.id).vendidos == 0


# --------------------------------------------------------------------------- #
# O que a colheita NÃO faz
# --------------------------------------------------------------------------- #


def test_reserva_dentro_do_prazo_nao_e_colhida(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O contraponto do primeiro teste: sem vencimento, o `409` continua de pé."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e4@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono4@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador4@exemplo.com")

    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    em_dia = _reserva(sessao, dono, evento, (pista, 1), vencida=False)
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"
    sessao.expire(em_dia)
    assert em_dia.estado == EstadoReserva.PENDENTE.value
    assert sessao.get(Setor, pista.id).vendidos == 1


def test_a_colheita_so_alcanca_os_setores_pedidos(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O alcance é o setor do pedido, não o evento inteiro (decisão do Igor)."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e5@exemplo.com")
    desistente = fabricar_usuario(PapelUsuario.CLIENTE, "desistente5@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador5@exemplo.com")

    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Pista", 10, 0, 12000), ("Camarote", 10, 4, 30000)],
    )
    setores = _por_nome(evento)
    pista, camarote = setores["Pista"], setores["Camarote"]
    # Vencida, mas num setor que o comprador não vai pedir.
    intocada = _reserva(sessao, desistente, evento, (camarote, 4), vencida=True)
    _entrar(cliente, comprador)

    assert cliente.post("/reservas", json=_corpo(evento, (pista, 1))).status_code == 201

    sessao.expire(intocada)
    assert intocada.estado == EstadoReserva.PENDENTE.value
    assert sessao.get(Setor, camarote.id).vendidos == 4


def test_reserva_ja_paga_nao_devolve_estoque_ao_vencer_o_prazo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A transição é condicionada a `PENDENTE` (AD-4), e é isso que protege a venda.

    Uma reserva paga cujo `expira_em` já passou é o caso normal do dia seguinte:
    o prazo é o de segurar o lugar, e ele não volta a importar depois de pago.
    Sem a condição de estado, a colheita devolveria ao estoque um lugar que já
    tem dono.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e6@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono6@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador6@exemplo.com")

    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    paga = _reserva(
        sessao,
        dono,
        evento,
        (pista, 1),
        vencida=True,
        estado=EstadoReserva.PAGA,
    )
    _entrar(cliente, comprador)

    resposta = cliente.post("/reservas", json=_corpo(evento, (pista, 1)))

    assert resposta.status_code == 409
    sessao.expire(paga)
    assert paga.estado == EstadoReserva.PAGA.value
    assert sessao.get(Setor, pista.id).vendidos == 1


def test_rota_de_leitura_nao_colhe(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Decisão do Igor: só escrita colhe.

    A consequência é aceita e visível — a página pode dizer "Esgotado" com
    reservas já vencidas —, e a alternativa era transformar as quatro rotas
    públicas em escrita, na tela mais visitada do site.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-e7@exemplo.com")
    desistente = fabricar_usuario(PapelUsuario.CLIENTE, "desistente7@exemplo.com")

    evento = _evento_publicado(sessao, organizador)
    pista = _por_nome(evento)["Pista"]
    abandonada = _reserva(sessao, desistente, evento, (pista, 1), vencida=True)

    assert cliente.get(f"/eventos/{evento.id}").status_code == 200

    sessao.expire(abandonada)
    assert abandonada.estado == EstadoReserva.PENDENTE.value
    assert sessao.get(Setor, pista.id).vendidos == 1


# --------------------------------------------------------------------------- #
# AC3 — a expiração é preguiçosa: não existe worker nem cron
# --------------------------------------------------------------------------- #


def test_o_projeto_nao_tem_tarefa_agendada(cliente: TestClient) -> None:
    """Varredura do código-fonte, e não uma afirmação de README (AC3).

    O AD-4 escolhe a colheita preguiçosa em vez de agendamento, e a forma de essa
    decisão continuar verdadeira daqui a três stories é um teste que quebra
    quando alguém instalar um agendador para "resolver de uma vez".

    `BackgroundTasks` do FastAPI entra na lista: ele não é cron, mas expirar
    reserva por trás da resposta seria o mesmo desvio com outro nome — a
    devolução deixaria de acontecer no instante em que o estoque importa.
    """
    proibidos = (
        "apscheduler",
        "celery",
        "BackgroundTasks",
        "add_periodic_task",
        "crontab",
        "schedule.every",
    )

    fontes = [
        *(RAIZ_BACKEND / "app").rglob("*.py"),
        RAIZ_BACKEND / "pyproject.toml",
    ]

    for arquivo in fontes:
        conteudo = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in conteudo, (
                f"{arquivo.relative_to(RAIZ_BACKEND)} menciona '{termo}'. "
                f"A expiração é preguiçosa por decisão de arquitetura (AD-4): "
                f"quem colhe é quem precisa do estoque."
            )
