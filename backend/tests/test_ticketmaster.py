"""Cliente da Ticketmaster (`app/integrations/ticketmaster.py`) — Story 2.1.

Zero rede: toda substituição é `httpx.MockTransport`, que recebe a
`httpx.Request` de verdade — construída pelo código de produção, com a query
string montada por ele — e devolve a `httpx.Response` que o teste escolhe.
Isso é o que torna verificável o AC1: o teste lê `request.url.params["apikey"]`
em vez de acreditar que a chave foi enviada.

A suíte inteira roda com a rede desligada (AC9) — nenhum teste aqui faz
requisição de verdade.
"""

import logging
from collections.abc import Callable

import httpx
import pytest

from app.core.config import Settings
from app.core.erros import ErroDeDominio
from app.integrations import ticketmaster

_CHAVE_DE_TESTE = "chave-de-teste-nao-vaze-isto"


@pytest.fixture(autouse=True)
def _settings_com_chave(monkeypatch: pytest.MonkeyPatch) -> None:
    """A maioria dos testes quer uma chave presente. `Settings` não lê o
    `.env` (`_env_file=None`), então nenhum valor real de máquina alguma
    interfere aqui.
    """
    settings = Settings(_env_file=None, ticketmaster_api_key=_CHAVE_DE_TESTE)
    monkeypatch.setattr(ticketmaster, "obter_settings", lambda: settings)


def _instalar_transporte(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Substitui `_criar_cliente` por um cliente com `MockTransport` — o único
    ponto de indireção que o módulo de produção expõe para isto.
    """
    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ticketmaster, "_criar_cliente", lambda: cliente)


def _evento_completo() -> dict:
    """Forma real de um evento da Discovery — a do Dev Notes da story, com
    `_embedded` aninhado, `dates` (que este projeto não lê) e duas imagens.
    """
    return {
        "name": "Metallica: M72 World Tour",
        "id": "G5vYZ9j1kdXyR",
        "images": [
            {
                "ratio": "16_9",
                "width": 1136,
                "height": 639,
                "url": "https://s1.ticketm.net/grande",
            },
            {
                "ratio": "3_2",
                "width": 305,
                "height": 203,
                "url": "https://s1.ticketm.net/pequena",
            },
        ],
        "dates": {"start": {"dateTime": "2026-11-14T23:00:00Z"}},
        "_embedded": {
            "venues": [{"name": "Allianz Parque", "city": {"name": "São Paulo"}}],
            "attractions": [{"name": "Metallica", "id": "K8vZ9171C-7"}],
        },
    }


def _resposta_com_eventos(*eventos: dict) -> httpx.Response:
    return httpx.Response(200, json={"_embedded": {"events": list(eventos)}})


# --------------------------------------------------------------------------- #
# AC1 — a chave viaja na query string, a partir do backend
# --------------------------------------------------------------------------- #


def test_chave_sai_em_apikey_e_termo_em_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("metallica")

    assert capturado["url"].params["apikey"] == _CHAVE_DE_TESTE
    assert capturado["url"].params["keyword"] == "metallica"


def test_country_code_e_br(monkeypatch: pytest.MonkeyPatch) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("metallica")

    assert capturado["url"].params["countryCode"] == "BR"


def test_url_e_o_endpoint_de_eventos_da_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("metallica")

    assert str(capturado["url"]).startswith(
        "https://app.ticketmaster.com/discovery/v2/events.json"
    )


# --------------------------------------------------------------------------- #
# AC2 — Ticketmaster fora do ar não derruba a aplicação
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status_http", [401, 429, 500])
def test_erro_de_status_vira_catalogo_indisponivel(
    monkeypatch: pytest.MonkeyPatch, status_http: int
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_http, json={"fault": {"faultstring": "erro qualquer"}}
        )

    _instalar_transporte(monkeypatch, handler)

    with pytest.raises(ErroDeDominio) as exc_info:
        ticketmaster.buscar_eventos("metallica")

    assert exc_info.value.codigo == "CATALOGO_INDISPONIVEL"
    assert exc_info.value.status_http == 503


def test_timeout_vira_catalogo_indisponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("tempo esgotado", request=request)

    _instalar_transporte(monkeypatch, handler)

    with pytest.raises(ErroDeDominio) as exc_info:
        ticketmaster.buscar_eventos("metallica")

    assert exc_info.value.codigo == "CATALOGO_INDISPONIVEL"
    assert exc_info.value.status_http == 503


def test_falha_de_conexao_vira_catalogo_indisponivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    _instalar_transporte(monkeypatch, handler)

    with pytest.raises(ErroDeDominio) as exc_info:
        ticketmaster.buscar_eventos("metallica")

    assert exc_info.value.codigo == "CATALOGO_INDISPONIVEL"
    assert exc_info.value.status_http == 503


def test_json_malformado_vira_catalogo_indisponivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"isto nao e um json valido {")

    _instalar_transporte(monkeypatch, handler)

    with pytest.raises(ErroDeDominio) as exc_info:
        ticketmaster.buscar_eventos("metallica")

    assert exc_info.value.codigo == "CATALOGO_INDISPONIVEL"


def test_chave_nao_aparece_no_log_nem_na_mensagem_do_erro(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A chave está na URL da requisição de verdade — é o que faria um
    `logger.exception` por reflexo vazá-la. A regra desta story é registrar o
    que aconteceu sem a URL.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        # A chave passou pela URL de verdade, montada pelo código de
        # produção — se algum caminho de log a repassasse, ela apareceria
        # nesta mesma forma no `caplog`.
        assert _CHAVE_DE_TESTE in str(request.url)
        return httpx.Response(401, json={"fault": {"faultstring": "Invalid ApiKey"}})

    _instalar_transporte(monkeypatch, handler)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ErroDeDominio) as exc_info:
            ticketmaster.buscar_eventos("metallica")

    assert _CHAVE_DE_TESTE not in caplog.text
    assert _CHAVE_DE_TESTE not in exc_info.value.mensagem
    assert _CHAVE_DE_TESTE not in str(exc_info.value)


# --------------------------------------------------------------------------- #
# AC3 e AC4 — conversão para `ItemDoCatalogo`, tolerante a resposta incompleta
# --------------------------------------------------------------------------- #


def test_resposta_completa_vira_item_do_catalogo_com_os_seis_campos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(_evento_completo())

    _instalar_transporte(monkeypatch, handler)

    itens = ticketmaster.buscar_eventos("metallica")

    assert len(itens) == 1
    item = itens[0]
    assert item.id_externo == "G5vYZ9j1kdXyR"
    assert item.nome == "Metallica: M72 World Tour"
    assert item.atracao == "Metallica"
    assert item.imagem_url == "https://s1.ticketm.net/grande"
    assert item.local == "Allianz Parque"
    assert item.cidade == "São Paulo"


def test_evento_sem_venues_tem_local_e_cidade_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evento = _evento_completo()
    del evento["_embedded"]["venues"]

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(evento)

    _instalar_transporte(monkeypatch, handler)

    item = ticketmaster.buscar_eventos("metallica")[0]

    assert item.local is None
    assert item.cidade is None


def test_evento_sem_attractions_tem_atracao_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evento = _evento_completo()
    del evento["_embedded"]["attractions"]

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(evento)

    _instalar_transporte(monkeypatch, handler)

    item = ticketmaster.buscar_eventos("metallica")[0]

    assert item.atracao is None


def test_evento_sem_embedded_algum_nao_estoura(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evento online, ou registro incompleto: `_embedded` pode faltar inteiro."""
    evento = _evento_completo()
    del evento["_embedded"]

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(evento)

    _instalar_transporte(monkeypatch, handler)

    item = ticketmaster.buscar_eventos("metallica")[0]

    assert item.local is None
    assert item.cidade is None
    assert item.atracao is None


def test_evento_sem_images_tem_imagem_none(monkeypatch: pytest.MonkeyPatch) -> None:
    evento = _evento_completo()
    evento["images"] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(evento)

    _instalar_transporte(monkeypatch, handler)

    item = ticketmaster.buscar_eventos("metallica")[0]

    assert item.imagem_url is None


def test_evento_com_varias_imagens_escolhe_a_mais_larga_16_9(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evento = _evento_completo()
    evento["images"] = [
        {"ratio": "3_2", "width": 999, "height": 666, "url": "https://.../larga-3-2"},
        {
            "ratio": "16_9",
            "width": 500,
            "height": 281,
            "url": "https://.../pequena-16-9",
        },
        {
            "ratio": "16_9",
            "width": 1136,
            "height": 639,
            "url": "https://.../grande-16-9",
        },
        {
            "ratio": "16_9",
            "width": 2000,
            "height": 1125,
            "url": "https://.../fallback-generica",
            "fallback": True,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(evento)

    _instalar_transporte(monkeypatch, handler)

    item = ticketmaster.buscar_eventos("metallica")[0]

    assert item.imagem_url == "https://.../grande-16-9"


def test_evento_sem_id_ou_sem_name_e_descartado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sem_id = _evento_completo()
    del sem_id["id"]
    sem_nome = _evento_completo()
    del sem_nome["name"]
    valido = _evento_completo()
    valido["id"] = "outro-id-valido"

    def handler(request: httpx.Request) -> httpx.Response:
        return _resposta_com_eventos(sem_id, sem_nome, valido)

    _instalar_transporte(monkeypatch, handler)

    itens = ticketmaster.buscar_eventos("metallica")

    assert len(itens) == 1
    assert itens[0].id_externo == "outro-id-valido"


# --------------------------------------------------------------------------- #
# AC5 — busca sem resultado é `[]`, não erro
# --------------------------------------------------------------------------- #


def test_resposta_sem_embedded_devolve_lista_vazia_sem_estourar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forma real de "não achou nada": o corpo não tem `_embedded`, só
    `page` e `_links` — `dados["_embedded"]["events"]` estouraria `KeyError`.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"page": {"size": 20, "totalElements": 0}, "_links": {}}
        )

    _instalar_transporte(monkeypatch, handler)

    assert ticketmaster.buscar_eventos("banda-que-nao-existe") == []


# --------------------------------------------------------------------------- #
# Termo em branco lista exemplos, sem `keyword`, ordenado por data
# (revisado depois do corte original: termo vazio deixou de significar
# "sem requisição" — ver Change Log da Story 2.2)
# --------------------------------------------------------------------------- #


def test_termo_vazio_chama_sem_keyword_e_ordena_por_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    assert ticketmaster.buscar_eventos("") == []

    assert "keyword" not in capturado["url"].params
    assert capturado["url"].params["sort"] == "date,asc"


def test_termo_so_com_espacos_chama_sem_keyword_tambem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    assert ticketmaster.buscar_eventos("   ") == []

    assert "keyword" not in capturado["url"].params
    assert capturado["url"].params["sort"] == "date,asc"


def test_termo_com_conteudo_chama_com_keyword_e_sem_sort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("metallica")

    assert capturado["url"].params["keyword"] == "metallica"
    assert "sort" not in capturado["url"].params


# --------------------------------------------------------------------------- #
# Filtro de classificação híbrido — segmentId sempre, genreId só na vitrine
# (docs/techspec-filtro-do-catalogo.md)
# --------------------------------------------------------------------------- #


def test_segment_id_presente_na_busca_com_termo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("metallica")

    assert capturado["url"].params["segmentId"] == "KZFzniwnSyZfZ7v7nJ"


def test_segment_id_presente_na_busca_sem_termo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("")

    assert capturado["url"].params["segmentId"] == "KZFzniwnSyZfZ7v7nJ"


def test_genre_id_presente_na_vitrine_sem_termo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("")

    assert capturado["url"].params["genreId"] == "KnvZfZ7vAeA"


def test_genre_id_ausente_na_busca_com_termo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """É este que prova o híbrido: sem ele, mover `genreId` para fora do
    `else` não seria acusado por nenhum outro teste.
    """
    capturado: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = request.url
        return httpx.Response(200, json={"page": {"totalElements": 0}})

    _instalar_transporte(monkeypatch, handler)

    ticketmaster.buscar_eventos("rosalia")

    assert "genreId" not in capturado["url"].params
