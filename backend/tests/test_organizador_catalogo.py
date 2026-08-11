"""Rota `GET /organizador/catalogo` (Story 2.2) — precisa do Compose no ar
(faz login de verdade) e roda com a rede desligada: a Ticketmaster é
`httpx.MockTransport`, como na 2.1 (`tests/test_ticketmaster.py`).
"""

from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.integrations import ticketmaster
from app.models.usuario import PapelUsuario, Usuario

_CHAVE_DE_TESTE = "chave-de-teste-nao-vaze-isto"


@pytest.fixture(autouse=True)
def _settings_com_chave(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, ticketmaster_api_key=_CHAVE_DE_TESTE)
    monkeypatch.setattr(ticketmaster, "obter_settings", lambda: settings)


def _instalar_transporte(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Substitui `_criar_cliente` do módulo da integração — a rota chama
    `ticketmaster.buscar_eventos`, que chama `_criar_cliente` do próprio
    módulo. Apontar para `app.api.organizador` não substituiria nada e o
    teste tentaria ir à rede de verdade.
    """
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ticketmaster, "_criar_cliente", lambda: cliente_http)


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    """Login de verdade: o cookie do teste é o mesmo que o navegador teria."""
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _evento(id_externo: str = "G5vYZ9j1kdXyR") -> dict:
    return {
        "name": "Metallica: M72 World Tour",
        "id": id_externo,
        "images": [],
        "_embedded": {
            "venues": [{"name": "Allianz Parque", "city": {"name": "São Paulo"}}],
            "attractions": [{"name": "Metallica", "id": "K8vZ9171C-7"}],
        },
    }


def _resposta_com_eventos(*eventos: dict) -> httpx.Response:
    return httpx.Response(200, json={"_embedded": {"events": list(eventos)}})


# --------------------------------------------------------------------------- #
# AC1 — organizador autenticado recebe a lista convertida
# --------------------------------------------------------------------------- #


def test_organizador_recebe_200_com_os_seis_campos(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(_evento())

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "metallica"})

    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 1
    item = itens[0]
    assert set(item.keys()) == {
        "id_externo",
        "nome",
        "atracao",
        "imagem_url",
        "local",
        "cidade",
    }
    assert item["id_externo"] == "G5vYZ9j1kdXyR"
    assert item["nome"] == "Metallica: M72 World Tour"
    assert item["local"] == "Allianz Parque"
    assert item["cidade"] == "São Paulo"


def test_rota_aparece_no_openapi_com_schema_de_saida(cliente: TestClient) -> None:
    especificacao = cliente.get("/openapi.json").json()
    operacao = especificacao["paths"]["/organizador/catalogo"]["get"]
    schema_200 = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert "items" in schema_200


# --------------------------------------------------------------------------- #
# AC2 — só o organizador toca o catálogo; autenticação antes de autorização
# --------------------------------------------------------------------------- #


def test_cliente_recebe_403_sem_permissao(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "metallica"})

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_portaria_tambem_recebe_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.PORTARIA, "portaria@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "metallica"})

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_sem_cookie_recebe_401_e_nao_403(cliente: TestClient) -> None:
    resposta = cliente.get("/organizador/catalogo", params={"q": "metallica"})

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_termo_acima_de_120_caracteres_e_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador2@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "a" * 121})

    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# `q` ausente ou só espaços lista exemplos — sem `keyword`, ordenado por data
# (revisado depois do corte original desta story: termo vazio deixou de
# significar "sem requisição" — ver Change Log da Story 2.2)
# --------------------------------------------------------------------------- #


def test_sem_q_lista_exemplos_sem_keyword_ordenados_por_data(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return _resposta_com_eventos(_evento())

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador3@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert "keyword" not in capturado["url"].params
    assert capturado["url"].params["sort"] == "date,asc"


def test_q_so_com_espacos_lista_exemplos_do_mesmo_jeito(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return _resposta_com_eventos(_evento())

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador4@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "   "})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert "keyword" not in capturado["url"].params


# --------------------------------------------------------------------------- #
# Armadilha 2 dos Dev Notes — termo com `&` chega inteiro na Discovery
# --------------------------------------------------------------------------- #


def test_termo_com_e_comercial_chega_inteiro_na_keyword(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador5@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "AC/DC & Guns"})

    assert resposta.status_code == 200
    assert capturado["url"].params["keyword"] == "AC/DC & Guns"


# --------------------------------------------------------------------------- #
# AC5 — Ticketmaster fora do ar vira 503, busca sem resultado continua 200
# --------------------------------------------------------------------------- #


def test_ticketmaster_fora_do_ar_responde_503_catalogo_indisponivel(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"fault": {"faultstring": "erro qualquer"}})

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador6@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/catalogo", params={"q": "metallica"})

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "CATALOGO_INDISPONIVEL"


def test_busca_sem_resultado_e_200_com_lista_vazia_nao_503(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"page": {"size": 20, "totalElements": 0}, "_links": {}}
        )

    _instalar_transporte(monkeypatch, handler)

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador7@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get(
        "/organizador/catalogo", params={"q": "banda-que-nao-existe"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == []
