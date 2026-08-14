"""As duas rotas de **escrita** de evento do organizador: `POST
/organizador/eventos` (Stories 2.4 e 2.5) e `PUT /organizador/eventos/{id}`
(techspec `docs/techspec-editar-evento.md`, commit 1).

As duas moram no mesmo arquivo porque compartilham as cinco recusas — a edição
copia todas, com as mesmas frases —, e é aqui que uma divergência entre elas
aparece na mesma tela de resultado. O bloco do `PUT` começa no fim do arquivo,
com helpers próprios: ele grava evento e reserva pelo ORM, porque nenhum estado
de que ele precisa (setor com histórico, reserva vencida, show que já
aconteceu) é produzível pelas rotas.

Precisa do Compose no ar (faz login de verdade, como o `test_organizador_
catalogo.py`) e roda com **zero rede**: publicar não chama a Ticketmaster, e
um dos testes prova isso instalando um transporte que falha se for tocado.

Todo teste que afirma gravação lê do **banco**, não só do corpo da resposta. A
resposta prova o schema de saída; só o `sessao.get(Evento, id)` prova que a
linha existe do jeito que deveria.

⚠️ **Desde a Story 2.5, publicar exige portaria escalada** (AD-7). Todo teste
de caminho feliz passa `portaria_ids` pelo `_corpo`, com a fixture `porteiro`.
Os testes de recusa **não** passam — e continuam recebendo o código que
esperavam porque a ordem das cinco recusas põe as de setor na frente.

⚠️ **A quinta recusa (`EVENTO_NO_PASSADO`) entrou no code review da Epic 2**, e
com ela o `data_hora` padrão do `_corpo` deixou de ser uma constante: ver
`_daqui_a`.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, time, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations import ticketmaster
from app.models.evento import Evento, Setor, evento_portaria
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.models.validacao import Validacao, Veredito


@pytest.fixture()
def porteiro(fabricar_usuario: Callable[..., Usuario]) -> Usuario:
    """A conta de portaria que os testes de caminho feliz escalam.

    Fixture local, não do `conftest.py`: só este arquivo precisa dela, e a
    `fabricar_usuario` que ela usa já é a compartilhada.
    """
    return fabricar_usuario(PapelUsuario.PORTARIA, "porteiro@exemplo.com")


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    """Login de verdade: o cookie do teste é o mesmo que o navegador teria."""
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _instalar_transporte(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Igual ao do `test_organizador_catalogo.py`: substitui `_criar_cliente`
    do módulo da integração. Aqui ele existe por um motivo oposto — não para
    simular a Ticketmaster, mas para provar que ninguém a chama.
    """
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ticketmaster, "_criar_cliente", lambda: cliente_http)


def _instante(dias: int) -> datetime:
    """O mesmo relógio do `_daqui_a`, em objeto — para gravar pelo ORM."""
    return datetime.now(timezone.utc) + timedelta(days=dias)


def _daqui_a(dias: int) -> str:
    """Data ISO-8601 com fuso, relativa ao relógio.

    ⚠️ **Relativa, e não fixa, desde que a quinta recusa entrou** (code review
    da Epic 2). O padrão do `_corpo` era `"2026-08-15T00:00:00Z"` — escrito
    quatro dias antes dessa data. Com `EVENTO_NO_PASSADO` valendo, uma constante
    no calendário é uma bomba-relógio: a suíte passaria hoje e falharia inteira
    na quinta-feira, sem ninguém ter tocado em nada.
    """
    return _instante(dias).isoformat().replace("+00:00", "Z")


def _corpo(**ajustes: Any) -> dict[str, Any]:
    """Corpo válido **menos a escala**, com ajuste por parâmetro.

    Existe para que cada teste mostre **só** o que ele muda: quinze
    dicionários quase iguais escondem exatamente a linha que importa.

    ⚠️ `portaria_ids` **não** tem valor padrão aqui, e isso é intencional: o id
    da conta só existe depois da fixture, e um corpo que já viesse escalado
    apagaria da vista justamente o que a Story 2.5 acrescentou. Quem publica de
    verdade passa `_corpo(portaria_ids=[str(porteiro.id)])`.
    """
    corpo: dict[str, Any] = {
        "origem_externa_id": "G5vYZ9a1kd",
        "nome": "Baco Exu do Blues — Bluesman Vivo",
        "imagem_url": "https://s1.ticketm.net/dam/a/bluesman.jpg",
        "data_hora": _daqui_a(30),
        "local": "Espaço Unimed",
        "cidade": "São Paulo",
        "setores": [
            {"nome": "Pista", "capacidade": 800, "preco_centavos": 12000},
            {"nome": "Camarote", "capacidade": 60, "preco_centavos": 42000},
        ],
    }
    corpo.update(ajustes)
    return corpo


def _quantos_eventos(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(Evento)) or 0


def _quantos_setores(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(Setor)) or 0


def _quantas_escalas(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(evento_portaria)) or 0


def _escalados_no_banco(sessao: Session, evento_id: str) -> set[uuid.UUID]:
    """Os ids escalados lidos da **tabela de associação**.

    Ler `evento.portarias` pelo ORM provaria só que o objeto em memória tem a
    coleção certa. O que importa é a linha em `evento_portaria`.
    """
    return set(
        sessao.scalars(
            select(evento_portaria.c.usuario_id).where(
                evento_portaria.c.evento_id == uuid.UUID(evento_id)
            )
        )
    )


# --------------------------------------------------------------------------- #
# AC1 — o evento existe no banco com os campos do catálogo copiados
# --------------------------------------------------------------------------- #


def test_organizador_publica_e_o_evento_esta_no_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador1@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    corpo = resposta.json()

    gravado = sessao.get(Evento, corpo["id"])
    assert gravado is not None
    # AD-1: os três campos do catálogo foram **copiados**, não referenciados.
    assert gravado.nome == "Baco Exu do Blues — Bluesman Vivo"
    assert gravado.imagem_url == "https://s1.ticketm.net/dam/a/bluesman.jpg"
    assert gravado.origem_externa_id == "G5vYZ9a1kd"
    # E o que o organizador preencheu, do jeito que ele preencheu.
    assert gravado.local == "Espaço Unimed"
    assert gravado.cidade == "São Paulo"


def test_cada_setor_nasce_com_vendidos_zero_e_o_preco_que_foi_mandado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador2@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None

    por_nome = {setor.nome: setor for setor in gravado.setores}
    assert set(por_nome) == {"Pista", "Camarote"}
    assert por_nome["Pista"].capacidade == 800
    assert por_nome["Pista"].preco_centavos == 12000
    assert por_nome["Camarote"].preco_centavos == 42000
    # AD-13: o estoque nasce zero, e é o `server_default` da 2.3 quem responde.
    assert all(setor.vendidos == 0 for setor in gravado.setores)


def test_publicado_em_vem_preenchido_e_com_fuso(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador3@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    assert resposta.json()["publicado_em"] is not None

    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    # Publicar é o ato desta rota, não um passo posterior.
    assert gravado.publicado_em is not None
    assert gravado.publicado_em.tzinfo is not None


def test_rota_aparece_no_openapi_com_201_e_o_schema_de_saida(
    cliente: TestClient,
) -> None:
    especificacao = cliente.get("/openapi.json").json()
    operacao = especificacao["paths"]["/organizador/eventos"]["post"]
    schema = operacao["responses"]["201"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/EventoSaida")


# --------------------------------------------------------------------------- #
# AC2 — o dono é a sessão, nunca o corpo
# --------------------------------------------------------------------------- #


def test_com_dois_organizadores_o_dono_e_quem_publicou(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    # ⚠️ O e-mail padrão da fixture é fixo: dois usuários no mesmo teste
    # precisam de e-mails distintos, senão o segundo bate no UNIQUE da 1.3.
    publicador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "quem-publica@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "o-outro@exemplo.com")
    _entrar(cliente, publicador)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    assert gravado.organizador_id == publicador.id
    assert gravado.organizador_id != outro.id


def test_organizador_id_mandado_no_corpo_e_ignorado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    publicador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "dono@exemplo.com")
    vitima = fabricar_usuario(PapelUsuario.ORGANIZADOR, "vitima@exemplo.com")
    _entrar(cliente, publicador)

    # O campo não existe no schema de entrada, e o schema não tem
    # `extra="forbid"`: o corpo não é recusado, ele é **ignorado**.
    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(
            organizador_id=str(vitima.id), portaria_ids=[str(porteiro.id)]
        ),
    )

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    assert gravado.organizador_id == publicador.id


# --------------------------------------------------------------------------- #
# AC3 — publicar não fala com a Ticketmaster
# --------------------------------------------------------------------------- #


def test_publicar_nao_chama_a_ticketmaster(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_transporte(
        monkeypatch,
        lambda requisicao: pytest.fail("a publicação chamou a Ticketmaster"),
    )

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador4@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201


# --------------------------------------------------------------------------- #
# AC4 — evento sem setor tem código próprio, e não deixa órfão
# --------------------------------------------------------------------------- #


def test_lista_de_setores_vazia_e_422_evento_sem_setor(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador5@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo(setores=[]))

    assert resposta.status_code == 422
    # O `codigo`, não o status: com `min_length=1` no schema o status seria o
    # mesmo e o código viraria `DADOS_INVALIDOS`. É este assert que separa a
    # regra de negócio da validação de estrutura.
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"
    assert _quantos_eventos(sessao) == 0


def test_setores_ausente_cai_na_mesma_regra(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador6@exemplo.com")
    _entrar(cliente, usuario)

    corpo = _corpo()
    del corpo["setores"]

    resposta = cliente.post("/organizador/eventos", json=corpo)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"
    assert _quantos_eventos(sessao) == 0


# --------------------------------------------------------------------------- #
# AC5 — nome repetido é 422 legível, nunca o 500 da uq_setor_evento_id_nome
# --------------------------------------------------------------------------- #


def test_dois_setores_com_o_mesmo_nome_e_422_setor_duplicado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador7@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(
            setores=[
                {"nome": "Pista", "capacidade": 800, "preco_centavos": 12000},
                {"nome": "Pista", "capacidade": 100, "preco_centavos": 20000},
            ]
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DUPLICADO"
    # Nada gravado — nem o evento. A recusa acontece antes de qualquer `add`.
    assert _quantos_eventos(sessao) == 0
    assert _quantos_setores(sessao) == 0


def test_pista_e_pista_com_espacos_tambem_colidem(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador8@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(
            setores=[
                {"nome": "Pista", "capacidade": 800, "preco_centavos": 12000},
                {"nome": " pista ", "capacidade": 100, "preco_centavos": 20000},
            ]
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DUPLICADO"
    assert _quantos_eventos(sessao) == 0


# --------------------------------------------------------------------------- #
# AC6 — publicação exige atração do catálogo, e a regra mora no schema
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "ajuste",
    [
        pytest.param({"origem_externa_id": ""}, id="vazio"),
        pytest.param({"origem_externa_id": "   "}, id="so-espacos"),
    ],
)
def test_origem_externa_id_vazio_e_422(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    ajuste: dict[str, Any],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador9@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo(**ajuste))

    assert resposta.status_code == 422


def test_origem_externa_id_ausente_e_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador10@exemplo.com")
    _entrar(cliente, usuario)

    corpo = _corpo()
    del corpo["origem_externa_id"]

    resposta = cliente.post("/organizador/eventos", json=corpo)

    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# AC7 — só o organizador publica; autenticação antes de autorização
# --------------------------------------------------------------------------- #


def test_cliente_recebe_403_sem_permissao(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_portaria_tambem_recebe_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.PORTARIA, "portaria@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_sem_cookie_recebe_401_e_nao_403(cliente: TestClient) -> None:
    resposta = cliente.post("/organizador/eventos", json=_corpo())

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


# --------------------------------------------------------------------------- #
# AC8 — o domínio recusa antes do banco, e o estoque não vem do corpo
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "setor",
    [
        pytest.param(
            {"nome": "Pista", "capacidade": 0, "preco_centavos": 12000},
            id="capacidade-zero",
        ),
        pytest.param(
            {"nome": "Pista", "capacidade": 800, "preco_centavos": -1},
            id="preco-negativo",
        ),
        pytest.param(
            {"nome": "   ", "capacidade": 800, "preco_centavos": 12000},
            id="nome-de-setor-em-branco",
        ),
    ],
)
def test_valores_fora_do_dominio_sao_422_antes_do_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    setor: dict[str, Any],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador11@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo(setores=[setor]))

    assert resposta.status_code == 422
    assert _quantos_eventos(sessao) == 0


def test_nome_de_evento_em_branco_e_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador12@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo(nome="   "))

    assert resposta.status_code == 422


def test_vendidos_no_corpo_e_ignorado_e_o_setor_nasce_com_zero(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador13@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(
            setores=[
                {
                    "nome": "Pista",
                    "capacidade": 800,
                    "preco_centavos": 12000,
                    "vendidos": 99,
                }
            ],
            portaria_ids=[str(porteiro.id)],
        ),
    )

    assert resposta.status_code == 201
    assert resposta.json()["setores"][0]["vendidos"] == 0

    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    assert gravado.setores[0].vendidos == 0


# --------------------------------------------------------------------------- #
# AC9 — data sem fuso é data sem significado (AD-11)
# --------------------------------------------------------------------------- #


def test_data_hora_sem_fuso_e_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador14@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(data_hora="2026-08-15T00:00:00")
    )

    assert resposta.status_code == 422


def test_data_hora_com_offset_e_gravada_em_utc(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador15@exemplo.com")
    _entrar(cliente, usuario)

    # 21h em São Paulo (-03:00) é 00h do dia seguinte em UTC — é exatamente a
    # conversão que o navegador faz antes de enviar. O dia é relativo pelo mesmo
    # motivo do `_daqui_a`: com `EVENTO_NO_PASSADO` valendo, uma data fixa faz o
    # teste apodrecer no calendário.
    dia = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    fuso_de_brasilia = timezone(timedelta(hours=-3))

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(
            data_hora=f"{dia.isoformat()}T21:00:00-03:00",
            portaria_ids=[str(porteiro.id)],
        ),
    )

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    esperado = datetime.combine(dia, time(21, 0), tzinfo=fuso_de_brasilia)
    assert gravado.data_hora == esperado.astimezone(timezone.utc)
    # A prova de que a conversão aconteceu, e não de que os dois lados são
    # iguais por acaso: em UTC o show cai no **dia seguinte**, à meia-noite.
    assert gravado.data_hora.astimezone(timezone.utc).hour == 0
    assert gravado.data_hora.astimezone(timezone.utc).date() == dia + timedelta(days=1)


# --------------------------------------------------------------------------- #
# Story 2.5 · AC3 — publicar sem escalar ninguém é recusado (AD-7)
# --------------------------------------------------------------------------- #


def test_portaria_ids_ausente_e_422_evento_sem_portaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador16@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

    assert resposta.status_code == 422
    # O `codigo`, não o status: com `min_length=1` no schema o status seria o
    # mesmo e o código viraria `DADOS_INVALIDOS`. O AD-7 é invariante de
    # arquitetura, e é este assert que prova que ele mora no service.
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_PORTARIA"
    # Nada gravado: a recusa acontece antes de qualquer `add`.
    assert _quantos_eventos(sessao) == 0
    assert _quantos_setores(sessao) == 0
    assert _quantas_escalas(sessao) == 0


def test_portaria_ids_vazio_cai_na_mesma_regra(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador17@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo(portaria_ids=[]))

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_PORTARIA"
    assert _quantos_eventos(sessao) == 0


# --------------------------------------------------------------------------- #
# Story 2.5 · AC4 — a ordem das recusas é contrato
# --------------------------------------------------------------------------- #


def test_sem_setor_e_sem_portaria_a_recusa_e_a_do_setor(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Setor primeiro, e não é estética.

    Todo teste de recusa da Story 2.4 manda corpo sem `portaria_ids`, porque o
    campo não existia. Inverter a ordem os faria receber `EVENTO_SEM_PORTARIA`
    e pararem de provar o que se propuseram a provar — sem nenhum ganho.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador18@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(setores=[], portaria_ids=[])
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"


# --------------------------------------------------------------------------- #
# Story 2.5 · AC5 — escalar quem não pode é 422, e a rota não é oráculo
# --------------------------------------------------------------------------- #


def test_escalar_conta_que_nao_e_portaria_e_422_portaria_invalida(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador19@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "nao-e-porteiro@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(comprador.id)])
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "PORTARIA_INVALIDA"
    assert _quantos_eventos(sessao) == 0
    assert _quantas_escalas(sessao) == 0


def test_escalar_id_inexistente_devolve_o_mesmo_codigo_e_a_mesma_mensagem(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A rota não vira oráculo de "essa conta existe?".

    Mesma disciplina do login da Story 1.4: a resposta para "não existe" e para
    "existe, mas não serve" é indistinguível — inclusive na mensagem, não só no
    código.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador20@exemplo.com")
    cliente_comum = fabricar_usuario(PapelUsuario.CLIENTE, "outro-cliente@exemplo.com")
    _entrar(cliente, usuario)

    inexistente = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(uuid.uuid4())])
    )
    papel_errado = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(cliente_comum.id)])
    )

    assert inexistente.status_code == papel_errado.status_code == 422
    assert inexistente.json()["erro"] == papel_errado.json()["erro"]
    assert inexistente.json()["erro"]["codigo"] == "PORTARIA_INVALIDA"


def test_id_em_formato_invalido_e_dados_invalidos_do_pydantic(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Estrutura é do Pydantic; "o id resolve?" é do service."""
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador21@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=["nem-parece-um-uuid"])
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# Story 2.5 · AC6 — vários escalados, e id repetido não duplica linha
# --------------------------------------------------------------------------- #


def test_escalar_dois_grava_duas_linhas_em_evento_portaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador22@exemplo.com")
    segunda = fabricar_usuario(PapelUsuario.PORTARIA, "porteiro2@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(portaria_ids=[str(porteiro.id), str(segunda.id)]),
    )

    assert resposta.status_code == 201
    # Lido do banco, não do corpo da resposta: é a tabela de associação que
    # prova que o `relationship` gravou de verdade.
    assert _escalados_no_banco(sessao, resposta.json()["id"]) == {
        porteiro.id,
        segunda.id,
    }


def test_o_mesmo_id_duas_vezes_e_201_com_uma_linha_so(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Deduplicado em silêncio, ao contrário do `SETOR_DUPLICADO`.

    Dois setores com o mesmo nome são duas intenções em conflito; a mesma
    pessoa marcada duas vezes é uma intenção só.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador23@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(portaria_ids=[str(porteiro.id), str(porteiro.id)]),
    )

    assert resposta.status_code == 201
    assert len(resposta.json()["portarias"]) == 1
    assert _quantas_escalas(sessao) == 1


def test_mais_de_vinte_escalados_e_recusado_pelo_teto_do_schema(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """`max_length=20`: teto de proteção, não regra de produto."""
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador24@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(portaria_ids=[str(uuid.uuid4()) for _ in range(21)]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# Story 2.5 · AC7 — a resposta traz a escala, e nunca o hash da senha
# --------------------------------------------------------------------------- #


def test_a_resposta_traz_nome_e_email_de_quem_foi_escalado(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador25@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    (escalado,) = resposta.json()["portarias"]
    assert escalado["id"] == str(porteiro.id)
    assert escalado["nome"] == porteiro.nome
    assert escalado["email"] == "porteiro@exemplo.com"


def test_senha_hash_nao_aparece_em_lugar_nenhum_da_resposta(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Quem filtra é o `response_model`, e só se ele estiver declarado."""
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador26@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(portaria_ids=[str(porteiro.id)])
    )

    assert resposta.status_code == 201
    assert "senha_hash" not in resposta.text


# --------------------------------------------------------------------------- #
# Code review da Epic 2 — a quinta recusa e os tetos que faltavam
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("rotulo", "quando"),
    [
        ("ontem", -1),
        ("ano-passado", -365),
    ],
)
def test_publicar_show_no_passado_e_422_evento_no_passado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    rotulo: str,
    quando: int,
) -> None:
    """AD-7 não cobre isto, e nada cobria: erro de digitação na data é
    **permanente**, porque não existe tela de editar nem de apagar evento.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, f"passado-{rotulo}@ex.com")
    _entrar(cliente, usuario)
    antes = _quantos_eventos(sessao)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(data_hora=_daqui_a(quando), portaria_ids=[str(porteiro.id)]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NO_PASSADO"
    # A recusa acontece antes de qualquer `add`: nada chegou a existir.
    assert _quantos_eventos(sessao) == antes


def test_a_recusa_do_setor_vem_antes_da_recusa_da_data(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """A quinta recusa entrou **por último** de propósito.

    Um corpo que erra a data *e* não tem setor recebe `EVENTO_SEM_SETOR`, que é
    o que os testes das Stories 2.4 e 2.5 já provavam — a ordem documentada no
    topo de `services/evento.py` continua valendo.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "ordem-recusa@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(setores=[], data_hora=_daqui_a(-1))
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"


@pytest.mark.parametrize(
    ("rotulo", "setor"),
    [
        # `Integer` do Postgres é int4: sem o `le` do schema, isto passava por
        # todas as recusas e estourava no `commit` como `DataError`, virando
        # `500 ERRO_INTERNO` — erro de digitação vestido de bug do servidor.
        ("capacidade-acima-do-int4", {"capacidade": 2_147_483_648}),
        ("preco-absurdo", {"preco_centavos": 100_000_000_001}),
    ],
)
def test_valor_acima_do_teto_e_422_e_nao_500(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    rotulo: str,
    setor: dict[str, Any],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, f"teto-{rotulo}@exemplo.com")
    _entrar(cliente, usuario)
    antes = _quantos_eventos(sessao)

    base = {"nome": "Pista", "capacidade": 800, "preco_centavos": 12000}
    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(setores=[base | setor], portaria_ids=[str(porteiro.id)]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"
    assert _quantos_eventos(sessao) == antes


@pytest.mark.parametrize(
    "imagem",
    ["javascript:alert(1)", "data:text/html;base64,PHNjcmlwdD4=", "//evil.example"],
)
def test_imagem_url_fora_de_http_e_recusada(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    imagem: str,
) -> None:
    """O campo chega pelo **corpo**, não da Ticketmaster — o service não confere
    nada contra o catálogo. A Epic 3 vai renderizá-lo em `<img src>` público.
    """
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, f"img{len(imagem)}@ex.com")
    _entrar(cliente, usuario)

    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(imagem_url=imagem, portaria_ids=[str(porteiro.id)]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# =========================================================================== #
# `PUT /organizador/eventos/{id}` — editar evento que ainda não vendeu
# (techspec `docs/techspec-editar-evento.md`, commit 1)
# =========================================================================== #


def _evento_gravado(
    sessao: Session,
    organizador: Usuario,
    porteiro: Usuario,
    *,
    setores: list[tuple[str, int, int, int]] | None = None,
    data_hora: datetime | None = None,
) -> Evento:
    """Evento publicado com setores e escala, gravado direto pelo ORM.

    Cada setor é `(nome, capacidade, vendidos, preco_centavos)`.

    ⚠️ **Não passa pelo `POST`** de propósito, e por dois motivos que a rota não
    tem como atender: `vendidos` diferente de zero não é semeável pelo corpo
    (AD-13, e há teste da 2.4 provando isso), e `data_hora` no passado é
    justamente o que o `EVENTO_NO_PASSADO` recusa. Mesmo precedente do helper de
    evento em rascunho da 3.1 e do de reserva vencida da 3.7.
    """
    if setores is None:
        setores = [("Camarote", 60, 0, 42000), ("Pista", 800, 0, 12000)]

    evento = Evento(
        organizador_id=organizador.id,
        nome="Baco Exu do Blues — Bluesman Vivo",
        imagem_url="https://s1.ticketm.net/dam/a/bluesman.jpg",
        origem_externa_id="G5vYZ9a1kd",
        data_hora=data_hora if data_hora is not None else _instante(30),
        local="Espaço Unimed",
        cidade="São Paulo",
        publicado_em=_instante(-1),
        setores=[
            Setor(
                nome=nome,
                capacidade=capacidade,
                vendidos=vendidos,
                preco_centavos=preco,
            )
            for nome, capacidade, vendidos, preco in setores
        ],
        portarias=[porteiro],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


def _reserva_gravada(
    sessao: Session,
    dono: Usuario,
    evento: Evento,
    *itens: tuple[Setor, int],
    estado: EstadoReserva = EstadoReserva.PENDENTE,
    vencida: bool = False,
) -> Reserva:
    """Uma reserva pelo ORM, com prazo já vencido ou não — helper da 3.7."""
    reserva = Reserva(
        cliente_id=dono.id,
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
    return reserva


def _setor_por_nome(evento: Evento) -> dict[str, Setor]:
    return {setor.nome: setor for setor in evento.setores}


def _edicao(evento: Evento, porteiro: Usuario, **ajustes: Any) -> dict[str, Any]:
    """O corpo que **não muda nada** — o estado atual, reenviado.

    É o ponto de partida de quase todo teste daqui: cada um mostra só o campo
    que altera, e o resto do corpo prova de quebra que reenviar o que já está lá
    é uma edição válida (o `PUT` manda o estado final, não um diff).
    """
    corpo: dict[str, Any] = {
        "data_hora": evento.data_hora.isoformat().replace("+00:00", "Z"),
        "setores": [
            {
                "id": str(setor.id),
                "nome": setor.nome,
                "capacidade": setor.capacidade,
                "preco_centavos": setor.preco_centavos,
            }
            for setor in sorted(evento.setores, key=lambda setor: setor.nome)
        ],
        "portaria_ids": [str(porteiro.id)],
    }
    corpo.update(ajustes)
    return corpo


def _organizador(fabricar_usuario: Callable[..., Usuario], sufixo: str) -> Usuario:
    return fabricar_usuario(PapelUsuario.ORGANIZADOR, f"editar-{sufixo}@exemplo.com")


# --------------------------------------------------------------------------- #
# Editar evento sem venda troca data, setores e escala
# --------------------------------------------------------------------------- #


def test_editar_troca_data_setores_e_escala_e_o_get_seguinte_confirma(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O caminho feliz inteiro, conferido pela rota de leitura.

    O `GET` seguinte é a asserção que importa: a resposta do `PUT` prova o
    schema de saída, e só uma segunda ida ao banco prova que o que voltou é o
    que ficou gravado.
    """
    dono = _organizador(fabricar_usuario, "feliz")
    outro_porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "porteiro2@exemplo.com")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    nova_data = _daqui_a(45)
    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            data_hora=nova_data,
            setores=[
                {"nome": "Arquibancada", "capacidade": 300, "preco_centavos": 9000}
            ],
            portaria_ids=[str(outro_porteiro.id)],
        ),
    )

    assert resposta.status_code == 200

    depois = cliente.get(f"/organizador/eventos/{evento.id}").json()
    assert depois["data_hora"].replace("+00:00", "Z") == nova_data
    assert [setor["nome"] for setor in depois["setores"]] == ["Arquibancada"]
    assert depois["setores"][0]["capacidade"] == 300
    assert depois["setores"][0]["preco_centavos"] == 9000
    assert [portaria["id"] for portaria in depois["portarias"]] == [
        str(outro_porteiro.id)
    ]
    # E a resposta do `PUT` diz exatamente a mesma coisa que o `GET`.
    assert resposta.json() == depois


def test_setor_com_id_e_alterado_sem_id_e_criado_e_ausente_e_removido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """As três operações que cabem numa lista só, numa chamada só."""
    dono = _organizador(fabricar_usuario, "tres-operacoes")
    evento = _evento_gravado(sessao, dono, porteiro)
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                # Alterado: mesmo `id`, outro nome, outra capacidade, outro preço.
                {
                    "id": str(pista.id),
                    "nome": "Pista Premium",
                    "capacidade": 900,
                    "preco_centavos": 15000,
                },
                # Novo: sem `id`.
                {"nome": "Mezanino", "capacidade": 120, "preco_centavos": 25000},
                # E o "Camarote" simplesmente não veio — é remoção.
            ],
        ),
    )

    assert resposta.status_code == 200

    gravados = {
        setor.nome: setor
        for setor in sessao.scalars(
            select(Setor).where(Setor.evento_id == evento.id)
        )
    }
    assert sorted(gravados) == ["Mezanino", "Pista Premium"]
    # O alterado continua sendo a **mesma linha**: renomear não é apagar e criar.
    assert gravados["Pista Premium"].id == pista.id
    assert gravados["Pista Premium"].capacidade == 900
    assert gravados["Pista Premium"].preco_centavos == 15000
    assert gravados["Mezanino"].vendidos == 0


def test_os_cinco_campos_do_catalogo_no_corpo_sao_ignorados(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O `EventoEdicao` não tem os cinco campos do catálogo, e sem
    `extra="forbid"` eles são **ignorados** — não recusados.

    É a garantia de que a tela de editar não é mais poderosa que a de publicar:
    não existe corpo que faça este evento virar outro show sem trocar de
    `origem_externa_id`.
    """
    dono = _organizador(fabricar_usuario, "catalogo")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            nome="Outro show completamente diferente",
            imagem_url="https://exemplo.com/outra.jpg",
            local="Outro lugar",
            cidade="Outra cidade",
            origem_externa_id="ZZZZZZZZ",
        ),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Baco Exu do Blues — Bluesman Vivo"
    assert corpo["local"] == "Espaço Unimed"
    assert corpo["cidade"] == "São Paulo"
    assert corpo["origem_externa_id"] == "G5vYZ9a1kd"
    assert corpo["imagem_url"] == "https://s1.ticketm.net/dam/a/bluesman.jpg"


def test_editar_nao_mexe_no_publicado_em(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Editar não é republicar."""
    dono = _organizador(fabricar_usuario, "publicado-em")
    evento = _evento_gravado(sessao, dono, porteiro)
    antes = evento.publicado_em
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(60)),
    )

    assert resposta.status_code == 200
    gravado = sessao.get(Evento, evento.id)
    assert gravado is not None
    assert gravado.publicado_em == antes


# --------------------------------------------------------------------------- #
# A trava: `vendidos == 0` em todos os setores, depois da colheita
# --------------------------------------------------------------------------- #


def test_evento_com_reserva_paga_e_409_evento_com_venda(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "vendido")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador1@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 2, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(sessao, comprador, evento, (pista, 2), estado=EstadoReserva.PAGA)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(60)),
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EVENTO_COM_VENDA"
    # Nada mudou: a recusa acontece antes de a primeira linha ser escrita.
    gravado = sessao.get(Evento, evento.id)
    assert gravado is not None
    assert gravado.data_hora == evento.data_hora


def test_reserva_pendente_ainda_viva_tambem_trava_a_edicao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Descartei travar só com reserva `PAGA`.

    O preço vai congelado na reserva, então não haveria prejuízo contábil — mas
    quem está digitando o cartão veria o preço mudar na tela no meio da compra.
    """
    dono = _organizador(fabricar_usuario, "pendente-viva")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador2@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 3, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(sessao, comprador, evento, (pista, 3), vencida=False)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(60)),
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EVENTO_COM_VENDA"


def test_reserva_vencida_e_colhida_na_mesma_chamada_e_a_edicao_passa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O teste que justifica a colheita dentro da transação.

    Sem o `expirar_vencidas` do passo 3, um checkout abandonado seguraria a
    edição por até dez minutos — e a tela diria "esse evento já vendeu" sobre um
    evento que não vendeu nada. Mentira temporária que o organizador não tem
    como distinguir da verdadeira.
    """
    dono = _organizador(fabricar_usuario, "vencida")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador3@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 4, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    reserva = _reserva_gravada(sessao, comprador, evento, (pista, 4), vencida=True)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(60)),
    )

    assert resposta.status_code == 200
    # O estoque voltou **nesta mesma chamada**, e a reserva foi marcada.
    gravado = sessao.get(Setor, pista.id)
    assert gravado is not None
    assert gravado.vendidos == 0
    colhida = sessao.get(Reserva, reserva.id)
    assert colhida is not None
    assert colhida.estado == EstadoReserva.EXPIRADA.value
    # ⚠️ E o corpo da resposta diz o mesmo que o banco. Com
    # `synchronize_session=False` na colheita e `expire_on_commit=False` na
    # sessão, é aqui que sairia o `vendidos` de antes da expiração.
    assert resposta.json()["setores"][0]["vendidos"] == 0


# --------------------------------------------------------------------------- #
# A armadilha central: FK sem `ondelete` em `item_reserva` e `ingresso`
# --------------------------------------------------------------------------- #


def test_remover_setor_com_reserva_expirada_e_422_e_nao_500(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O teste que justifica a spec inteira.

    A reserva `EXPIRADA` devolveu o estoque, então o setor **passa** na trava do
    passo 4 — e a linha de `item_reserva` continua apontando para ele. Sem o
    passo 7, o `DELETE` estoura `IntegrityError` no `commit`, sobe ao handler
    genérico e vira `500 ERRO_INTERNO`.
    """
    dono = _organizador(fabricar_usuario, "historico")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador4@exemplo.com")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(
        sessao,
        comprador,
        evento,
        (camarote, 1),
        estado=EstadoReserva.EXPIRADA,
    )
    _entrar(cliente, dono)

    # O Camarote sai da lista — ou seja, seria removido.
    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(pista.id),
                    "nome": pista.nome,
                    "capacidade": pista.capacidade,
                    "preco_centavos": pista.preco_centavos,
                }
            ],
        ),
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["erro"]["codigo"] == "SETOR_COM_HISTORICO"
    # O nome do setor na mensagem: sem ele, o organizador com quatro setores não
    # sabe qual deles é o impedido.
    assert "Camarote" in corpo["erro"]["mensagem"]
    # E os dois continuam lá.
    assert sessao.get(Setor, camarote.id) is not None
    assert sessao.get(Setor, pista.id) is not None


def test_setor_sem_historico_nenhum_e_removido_normalmente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O caso legítimo mais comum: criou "Camarote" por engano e ninguém encostou.

    Descartei proibir remoção de qualquer setor justamente por causa dele.
    """
    dono = _organizador(fabricar_usuario, "remocao-limpa")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(pista.id),
                    "nome": pista.nome,
                    "capacidade": pista.capacidade,
                    "preco_centavos": pista.preco_centavos,
                }
            ],
        ),
    )

    assert resposta.status_code == 200
    assert sessao.get(Setor, camarote.id) is None


# --------------------------------------------------------------------------- #
# `uq_setor_evento_id_nome`: as duas ordens de escrita que virariam 500
# --------------------------------------------------------------------------- #


def test_trocar_os_nomes_de_dois_setores_entre_si_nao_e_500(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """A restrição é conferida a cada statement, não no fim da transação.

    Sem a fase do nome temporário, o `UPDATE` do primeiro setor colide com o
    nome que o segundo ainda tem — `IntegrityError` no meio de um corpo
    perfeitamente válido.
    """
    dono = _organizador(fabricar_usuario, "troca-de-nomes")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(camarote.id),
                    "nome": "Pista",
                    "capacidade": camarote.capacidade,
                    "preco_centavos": camarote.preco_centavos,
                },
                {
                    "id": str(pista.id),
                    "nome": "Camarote",
                    "capacidade": pista.capacidade,
                    "preco_centavos": pista.preco_centavos,
                },
            ],
        ),
    )

    assert resposta.status_code == 200
    trocados = {
        setor.id: setor.nome
        for setor in sessao.scalars(select(Setor).where(Setor.evento_id == evento.id))
    }
    assert trocados[camarote.id] == "Pista"
    assert trocados[pista.id] == "Camarote"


def test_remover_um_setor_e_criar_outro_com_o_mesmo_nome_nao_e_500(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """A ordem padrão do unit of work emite os `INSERT` **antes** dos `DELETE`.

    Sem a fase B antes da D, o setor novo nasce enquanto o antigo ainda existe,
    com o mesmo nome e o mesmo evento.
    """
    dono = _organizador(fabricar_usuario, "recriar-nome")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(pista.id),
                    "nome": pista.nome,
                    "capacidade": pista.capacidade,
                    "preco_centavos": pista.preco_centavos,
                },
                # Sem `id`: é um Camarote **novo**, e o antigo sai da lista.
                {"nome": "Camarote", "capacidade": 40, "preco_centavos": 50000},
            ],
        ),
    )

    assert resposta.status_code == 200
    gravados = {
        setor.nome: setor
        for setor in sessao.scalars(select(Setor).where(Setor.evento_id == evento.id))
    }
    assert sorted(gravados) == ["Camarote", "Pista"]
    assert gravados["Camarote"].id != camarote.id
    assert gravados["Camarote"].capacidade == 40


# --------------------------------------------------------------------------- #
# O `404` do dono, byte a byte igual ao de evento inexistente
# --------------------------------------------------------------------------- #


def test_editar_evento_de_outro_organizador_e_404_igual_ao_de_id_inexistente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Distinguir os dois faria desta rota um oráculo sobre os eventos alheios."""
    dono = _organizador(fabricar_usuario, "dono")
    intruso = _organizador(fabricar_usuario, "intruso")
    evento = _evento_gravado(sessao, dono, porteiro)
    corpo_enviado = _edicao(evento, porteiro)
    _entrar(cliente, intruso)

    do_outro = cliente.put(f"/organizador/eventos/{evento.id}", json=corpo_enviado)
    inexistente = cliente.put(
        f"/organizador/eventos/{uuid.uuid4()}", json=corpo_enviado
    )

    assert do_outro.status_code == 404
    assert do_outro.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"
    assert do_outro.json() == inexistente.json()
    # E nada do evento alheio mudou.
    gravado = sessao.get(Evento, evento.id)
    assert gravado is not None
    assert gravado.data_hora == evento.data_hora


# --------------------------------------------------------------------------- #
# As cinco recusas copiadas do `publicar`, uma asserção cada
# --------------------------------------------------------------------------- #


def test_editar_sem_nenhum_setor_e_422_evento_sem_setor(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "sem-setor")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}", json=_edicao(evento, porteiro, setores=[])
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"


def test_dois_setores_com_o_mesmo_nome_na_edicao_e_422_setor_duplicado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "nome-repetido")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(pista.id),
                    "nome": "Pista",
                    "capacidade": 800,
                    "preco_centavos": 12000,
                },
                # ` pista ` com espaços e caixa diferente é a mesma intenção — e
                # o `uq_setor_evento_id_nome` recusaria os dois com um `500`.
                {
                    "id": str(camarote.id),
                    "nome": " pista ",
                    "capacidade": 60,
                    "preco_centavos": 42000,
                },
            ],
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DUPLICADO"


def test_editar_sem_escalar_ninguem_e_422_evento_sem_portaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """AD-7 vale igual na edição: evento sem escala é ingresso que ninguém
    valida na porta. Não dá para publicar assim, e não dá para *ficar* assim.
    """
    dono = _organizador(fabricar_usuario, "sem-portaria")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, portaria_ids=[]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_SEM_PORTARIA"


def test_escalar_conta_que_nao_e_portaria_na_edicao_e_422_portaria_invalida(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "portaria-invalida")
    intruso = fabricar_usuario(PapelUsuario.CLIENTE, "cliente-escalado@exemplo.com")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, portaria_ids=[str(intruso.id)]),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "PORTARIA_INVALIDA"


def test_nova_data_no_passado_e_422_evento_no_passado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Consertar a data para trás só faria o show reaparecer na programação."""
    dono = _organizador(fabricar_usuario, "data-passada")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(-1)),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NO_PASSADO"


def test_editar_show_que_ja_aconteceu_e_422_evento_no_passado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O mesmo código nas duas pontas: a data que está lá e a data que veio."""
    dono = _organizador(fabricar_usuario, "show-passado")
    evento = _evento_gravado(sessao, dono, porteiro, data_hora=_instante(-2))
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora=_daqui_a(30)),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NO_PASSADO"


def test_data_hora_sem_fuso_na_edicao_e_422(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """AD-11 vale nos dois schemas — é o `DataComFuso` compartilhado."""
    dono = _organizador(fabricar_usuario, "sem-fuso")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(evento, porteiro, data_hora="2027-08-15T00:00:00"),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# `id` de setor: o que não é deste evento, e o que veio duas vezes
# --------------------------------------------------------------------------- #


def test_setor_de_outro_evento_e_422_setor_desconhecido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Um código só para "não é setor nenhum" e para "é de outro evento"."""
    dono = _organizador(fabricar_usuario, "setor-alheio")
    evento = _evento_gravado(sessao, dono, porteiro)
    outro = _evento_gravado(
        sessao, dono, porteiro, setores=[("Geral", 100, 0, 5000)]
    )
    alheio = _setor_por_nome(outro)["Geral"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(alheio.id),
                    "nome": "Geral",
                    "capacidade": 100,
                    "preco_centavos": 5000,
                }
            ],
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DESCONHECIDO"
    # O setor do outro evento continua intacto — a recusa vem antes de escrever.
    ainda_la = sessao.get(Setor, alheio.id)
    assert ainda_la is not None
    assert ainda_la.evento_id == outro.id


def test_id_inexistente_recebe_o_mesmo_setor_desconhecido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "setor-fantasma")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(uuid.uuid4()),
                    "nome": "Pista",
                    "capacidade": 800,
                    "preco_centavos": 12000,
                }
            ],
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DESCONHECIDO"


def test_o_mesmo_setor_duas_vezes_e_422_e_nao_perda_silenciosa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Sem esta recusa o estrago é silencioso.

    Dois nomes diferentes para o mesmo `id` passam pelo `SETOR_DUPLICADO`, a
    segunda entrada sobrescreve a primeira, e o setor que ficou de fora da lista
    é **removido**: o organizador mandou dois setores e recebeu um, com `200`.
    """
    dono = _organizador(fabricar_usuario, "id-repetido")
    evento = _evento_gravado(sessao, dono, porteiro)
    pista = _setor_por_nome(evento)["Pista"]
    _entrar(cliente, dono)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}",
        json=_edicao(
            evento,
            porteiro,
            setores=[
                {
                    "id": str(pista.id),
                    "nome": "Pista A",
                    "capacidade": 400,
                    "preco_centavos": 12000,
                },
                {
                    "id": str(pista.id),
                    "nome": "Pista B",
                    "capacidade": 400,
                    "preco_centavos": 12000,
                },
            ],
        ),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SETOR_DUPLICADO"
    assert len(sessao.get(Evento, evento.id).setores) == 2  # type: ignore[union-attr]


# --------------------------------------------------------------------------- #
# Autorização: a mesma das irmãs
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "papel,email",
    [
        (PapelUsuario.CLIENTE, "cliente-editar@exemplo.com"),
        (PapelUsuario.PORTARIA, "portaria-editar@exemplo.com"),
    ],
)
def test_editar_sem_papel_de_organizador_e_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    papel: PapelUsuario,
    email: str,
) -> None:
    dono = _organizador(fabricar_usuario, f"papel-{papel.value.lower()}")
    evento = _evento_gravado(sessao, dono, porteiro)
    corpo_enviado = _edicao(evento, porteiro)
    intruso = fabricar_usuario(papel, email)
    _entrar(cliente, intruso)

    resposta = cliente.put(f"/organizador/eventos/{evento.id}", json=corpo_enviado)

    assert resposta.status_code == 403


def test_editar_sem_cookie_e_401_e_nao_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "sem-cookie")
    evento = _evento_gravado(sessao, dono, porteiro)

    resposta = cliente.put(
        f"/organizador/eventos/{evento.id}", json=_edicao(evento, porteiro)
    )

    assert resposta.status_code == 401


def test_a_rota_aparece_no_openapi_com_200_e_o_schema_de_saida(
    cliente: TestClient,
) -> None:
    esquema = cliente.get("/openapi.json").json()
    put = esquema["paths"]["/organizador/eventos/{evento_id}"]["put"]

    assert "200" in put["responses"]
    referencia = put["responses"]["200"]["content"]["application/json"]["schema"]
    assert referencia["$ref"].endswith("/EventoSaida")
    corpo = put["requestBody"]["content"]["application/json"]["schema"]
    assert corpo["$ref"].endswith("/EventoEdicao")
    # Os cinco campos do catálogo não existem no contrato de entrada.
    propriedades = esquema["components"]["schemas"]["EventoEdicao"]["properties"]
    assert sorted(propriedades) == ["data_hora", "portaria_ids", "setores"]


# =========================================================================== #
# `DELETE /organizador/eventos/{id}` — excluir evento que ainda não vendeu
# (techspec `docs/techspec-editar-evento.md`, commit 3)
# =========================================================================== #


def _validacao_gravada(
    sessao: Session,
    evento: Evento,
    porteiro: Usuario,
    *,
    resultado: Veredito = Veredito.INVALIDO,
) -> Validacao:
    """A tentativa frustrada na porta — `ingresso_id` nulo, de propósito.

    ⚠️ **É a linha que passa batido**, e o helper existe para ela ter teste. A
    `validacao` nasce na porta e ninguém associa "portaria" a "excluir evento" —
    mas ela é gravada **mesmo quando o código não resolve para ingresso nenhum**,
    ou seja, existe em evento que nunca vendeu nada. Que é exatamente o único
    evento que o `DELETE` consegue apagar.
    """
    validacao = Validacao(
        evento_id=evento.id,
        portaria_id=porteiro.id,
        ingresso_id=None,
        resultado=resultado.value,
        criado_em=datetime.now(timezone.utc),
    )
    sessao.add(validacao)
    sessao.flush()
    return validacao


def _quantas_reservas(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(Reserva)) or 0


def _quantos_itens(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(ItemReserva)) or 0


# --------------------------------------------------------------------------- #
# O caminho feliz, e o que precisa sumir junto
# --------------------------------------------------------------------------- #


def test_excluir_evento_sem_venda_e_204_e_o_get_seguinte_e_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "excluir-feliz")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    # `204` é sem corpo, e é o `Response` explícito da rota que garante isso.
    assert resposta.content == b""
    assert cliente.get(f"/organizador/eventos/{evento.id}").status_code == 404


def test_excluir_leva_setores_e_escala_junto_sem_deixar_linha_orfa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """Os dois caem pelo `ondelete="CASCADE"` que declaram desde a Story 2.3."""
    dono = _organizador(fabricar_usuario, "excluir-cascata")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    assert _quantos_setores(sessao) == 2
    assert _quantas_escalas(sessao) == 1

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    assert _quantos_eventos(sessao) == 0
    assert _quantos_setores(sessao) == 0
    assert _quantas_escalas(sessao) == 0


def test_evento_excluido_some_de_meus_eventos_e_da_programacao_publica(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "excluir-listagens")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    assert len(cliente.get("/organizador/eventos").json()) == 1

    assert cliente.delete(f"/organizador/eventos/{evento.id}").status_code == 204

    assert cliente.get("/organizador/eventos").json() == []
    # A rota pública é aberta, e o cookie do organizador não muda o que ela vê.
    cliente.cookies.clear()
    assert cliente.get("/eventos").json() == []
    assert cliente.get(f"/eventos/{evento.id}").status_code == 404


# --------------------------------------------------------------------------- #
# O rastro morto: reserva não paga, itens e validação
# --------------------------------------------------------------------------- #


def test_evento_com_reserva_expirada_e_excluido_e_a_reserva_some_junto(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """O teste que justifica o commit inteiro.

    É a armadilha do `SETOR_COM_HISTORICO` um nível acima: a reserva `EXPIRADA`
    devolveu o estoque, então o evento **passa** na trava — e `reserva.evento_id`
    é FK sem `ondelete`. Sem o passo 6, o `DELETE` do evento estoura
    `IntegrityError` no `commit` e vira `500`. A única forma de errar aqui é
    testar só com evento limpo.
    """
    dono = _organizador(fabricar_usuario, "excluir-expirada")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador5@exemplo.com")
    evento = _evento_gravado(sessao, dono, porteiro)
    camarote = _setor_por_nome(evento)["Camarote"]
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(
        sessao,
        comprador,
        evento,
        (camarote, 1),
        (pista, 2),
        estado=EstadoReserva.EXPIRADA,
    )
    _entrar(cliente, dono)

    assert _quantas_reservas(sessao) == 1
    assert _quantos_itens(sessao) == 2

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    assert _quantas_reservas(sessao) == 0
    # Os itens caem pelo `ondelete="CASCADE"` do `reserva_id`, no banco.
    assert _quantos_itens(sessao) == 0
    assert _quantos_eventos(sessao) == 0


def test_evento_com_validacao_de_tentativa_frustrada_e_excluido_normalmente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """A FK que ninguém lembra: `validacao.evento_id`, também sem `ondelete`.

    Ela nasce na porta, e um `INVALIDO` é gravado com `ingresso_id` nulo — ou
    seja, existe em evento que nunca vendeu nada. Esquecer o passo 5 dá um `500`
    que só aparece depois de alguém ter apontado a câmera para um QR errado.
    """
    dono = _organizador(fabricar_usuario, "excluir-validacao")
    evento = _evento_gravado(sessao, dono, porteiro)
    _validacao_gravada(sessao, evento, porteiro)
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    assert sessao.scalar(select(func.count()).select_from(Validacao)) == 0
    assert _quantos_eventos(sessao) == 0


def test_evento_com_reserva_recusada_e_validacao_juntas_tambem_sai(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """As duas FKs no mesmo evento — é assim que um evento de verdade fica.

    `RECUSADA` também devolveu o estoque, então ela passa na trava exatamente
    como a `EXPIRADA`.
    """
    dono = _organizador(fabricar_usuario, "excluir-rastro-duplo")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador6@exemplo.com")
    evento = _evento_gravado(sessao, dono, porteiro)
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(
        sessao, comprador, evento, (pista, 1), estado=EstadoReserva.RECUSADA
    )
    _validacao_gravada(sessao, evento, porteiro, resultado=Veredito.EVENTO_ERRADO)
    _entrar(cliente, dono)

    assert cliente.delete(f"/organizador/eventos/{evento.id}").status_code == 204
    assert _quantos_eventos(sessao) == 0
    assert _quantas_reservas(sessao) == 0


# --------------------------------------------------------------------------- #
# A trava, e a prova de que a recusa não destrói nada
# --------------------------------------------------------------------------- #


def test_excluir_evento_com_reserva_paga_e_409_e_a_reserva_continua_no_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """A recusa acontece **antes** de qualquer `DELETE` — nada é destruído.

    O `estado != 'PAGA'` do passo 6 é a segunda barreira, e existe para o dia em
    que a primeira falhar: sem ele, o bug viraria "a exclusão apagou uma venda".
    """
    dono = _organizador(fabricar_usuario, "excluir-paga")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador7@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 2, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    reserva = _reserva_gravada(
        sessao, comprador, evento, (pista, 2), estado=EstadoReserva.PAGA
    )
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EVENTO_COM_VENDA"
    # A frase está no verbo certo: uma recusa de exclusão que diz "editado"
    # seria a tela mentindo sobre o que o organizador acabou de tentar.
    assert "excluído" in resposta.json()["erro"]["mensagem"]
    # E nada foi destruído: o evento, a reserva paga e os setores continuam lá.
    assert sessao.get(Evento, evento.id) is not None
    assert sessao.get(Reserva, reserva.id) is not None
    assert _quantos_setores(sessao) == 1


def test_excluir_evento_com_reserva_pendente_viva_e_409(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "excluir-pendente-viva")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador8@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 3, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(sessao, comprador, evento, (pista, 3), vencida=False)
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EVENTO_COM_VENDA"
    assert sessao.get(Evento, evento.id) is not None


def test_reserva_vencida_e_colhida_e_o_evento_e_excluido_na_mesma_chamada(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """A colheita do passo 3, na exclusão.

    Sem ela, um checkout abandonado seguraria a exclusão por até dez minutos, e
    a tela diria "esse evento já vendeu" sobre um evento que não vendeu nada.
    """
    dono = _organizador(fabricar_usuario, "excluir-vencida")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador9@exemplo.com")
    evento = _evento_gravado(
        sessao, dono, porteiro, setores=[("Pista", 800, 4, 12000)]
    )
    pista = _setor_por_nome(evento)["Pista"]
    _reserva_gravada(sessao, comprador, evento, (pista, 4), vencida=True)
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    assert _quantos_eventos(sessao) == 0
    # A reserva foi colhida **e** apagada na mesma transação: ela virou
    # `EXPIRADA` no passo 3 e caiu no passo 6.
    assert _quantas_reservas(sessao) == 0


# --------------------------------------------------------------------------- #
# A assimetria com o `PUT`: show que já aconteceu **pode** ser excluído
# --------------------------------------------------------------------------- #


def test_show_que_ja_aconteceu_e_excluido_normalmente_ao_contrario_do_put(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """**Intencional, e diferente do `PUT`** — decisão da seção 3 da techspec.

    O motivo da recusa na edição é específico do verbo: editar a data de um show
    passado o faria reaparecer na programação pública. Excluí-lo não faz nada
    reaparecer, e é justamente o caso em que a exclusão é faxina. Recusar
    prenderia todo evento antigo em `Meus eventos` para sempre.

    O par deste teste é o `test_editar_show_que_ja_aconteceu_e_422_evento_no_passado`
    lá em cima: os dois provam a assimetria, um de cada lado.
    """
    dono = _organizador(fabricar_usuario, "excluir-passado")
    evento = _evento_gravado(sessao, dono, porteiro, data_hora=_instante(-2))
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 204
    assert _quantos_eventos(sessao) == 0


# --------------------------------------------------------------------------- #
# O `404`, e a não-idempotência que o separa do `DELETE` da Story 4.4
# --------------------------------------------------------------------------- #


def test_excluir_evento_de_outro_organizador_e_404_igual_ao_de_id_inexistente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "excluir-dono")
    intruso = _organizador(fabricar_usuario, "excluir-intruso")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, intruso)

    do_outro = cliente.delete(f"/organizador/eventos/{evento.id}")
    inexistente = cliente.delete(f"/organizador/eventos/{uuid.uuid4()}")

    assert do_outro.status_code == 404
    assert do_outro.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"
    assert do_outro.json() == inexistente.json()
    # E o evento alheio continua inteiro.
    assert sessao.get(Evento, evento.id) is not None


def test_excluir_duas_vezes_devolve_404_na_segunda(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    """⚠️ **Não é idempotente, e a diferença com o `DELETE` da Story 4.4 é real.**

    Revogar um link duas vezes responde `204` nas duas, porque "o link não vale
    mais" continua verdade. Aqui o recurso do caminho deixou de existir: dizer
    `204` fingiria que a segunda chamada apagou alguma coisa.
    """
    dono = _organizador(fabricar_usuario, "excluir-duas-vezes")
    evento = _evento_gravado(sessao, dono, porteiro)
    _entrar(cliente, dono)

    assert cliente.delete(f"/organizador/eventos/{evento.id}").status_code == 204

    segunda = cliente.delete(f"/organizador/eventos/{evento.id}")
    assert segunda.status_code == 404
    assert segunda.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"


@pytest.mark.parametrize(
    "papel,email",
    [
        (PapelUsuario.CLIENTE, "cliente-excluir@exemplo.com"),
        (PapelUsuario.PORTARIA, "portaria-excluir@exemplo.com"),
    ],
)
def test_excluir_sem_papel_de_organizador_e_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
    papel: PapelUsuario,
    email: str,
) -> None:
    dono = _organizador(fabricar_usuario, f"excluir-papel-{papel.value.lower()}")
    evento = _evento_gravado(sessao, dono, porteiro)
    intruso = fabricar_usuario(papel, email)
    _entrar(cliente, intruso)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 403
    assert sessao.get(Evento, evento.id) is not None


def test_excluir_sem_cookie_e_401_e_nao_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    porteiro: Usuario,
) -> None:
    dono = _organizador(fabricar_usuario, "excluir-sem-cookie")
    evento = _evento_gravado(sessao, dono, porteiro)

    resposta = cliente.delete(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 401
    assert sessao.get(Evento, evento.id) is not None


def test_o_delete_aparece_no_openapi_com_204_e_sem_corpo_de_entrada(
    cliente: TestClient,
) -> None:
    esquema = cliente.get("/openapi.json").json()
    rota = esquema["paths"]["/organizador/eventos/{evento_id}"]["delete"]

    assert "204" in rota["responses"]
    # Sem schema de entrada: o caminho é o pedido inteiro.
    assert "requestBody" not in rota
