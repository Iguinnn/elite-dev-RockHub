"""Rota `POST /organizador/eventos` (Stories 2.4 e 2.5) — a primeira rota de
escrita do domínio.

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
from app.models.usuario import PapelUsuario, Usuario


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


def _daqui_a(dias: int) -> str:
    """Data ISO-8601 com fuso, relativa ao relógio.

    ⚠️ **Relativa, e não fixa, desde que a quinta recusa entrou** (code review
    da Epic 2). O padrão do `_corpo` era `"2026-08-15T00:00:00Z"` — escrito
    quatro dias antes dessa data. Com `EVENTO_NO_PASSADO` valendo, uma constante
    no calendário é uma bomba-relógio: a suíte passaria hoje e falharia inteira
    na quinta-feira, sem ninguém ter tocado em nada.
    """
    return (
        datetime.now(timezone.utc) + timedelta(days=dias)
    ).isoformat().replace("+00:00", "Z")


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
