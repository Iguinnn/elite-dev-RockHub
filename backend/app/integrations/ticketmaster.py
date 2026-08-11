"""Cliente da Ticketmaster Discovery — a única peça do backend que fala com um
serviço externo (Story 2.1).

Três responsabilidades, e cada uma existe por um motivo que já mordeu alguém:

- **A chave nunca sai do processo do backend** (AD-2). Ela viaja como query
  param, porque é o que a Discovery exige — e é exatamente por isso que uma
  falha HTTP não pode virar log ou mensagem de erro sem antes passar por aqui:
  a exceção do `httpx` carrega a URL completa, e a URL carrega `apikey=`.
- **A Ticketmaster fora do ar não derruba a aplicação.** Toda falha — timeout,
  conexão recusada, `401`, `429`, `500`, JSON malformado — vira o mesmo
  `ErroDeDominio("CATALOGO_INDISPONIVEL", ..., status_http=503)`. Quem chama
  não precisa saber qual dos cinco aconteceu; o log sabe.
- **O formato deles morre aqui.** `_embedded`, `_links`, `dates`,
  `classifications` não atravessam esta fronteira — quem lê `ItemDoCatalogo`
  não faz ideia de que existe uma Ticketmaster do outro lado (AD-1).
"""

import logging

import httpx

from app.core.config import obter_settings
from app.core.erros import ErroDeDominio
from app.schemas.catalogo import ItemDoCatalogo

logger = logging.getLogger(__name__)

_URL_EVENTOS = "https://app.ticketmaster.com/discovery/v2/events.json"

# 5s de inatividade é generoso para uma chamada que o organizador faz olhando a
# tela — nem tão curto que uma rede um pouco lenta vire falso negativo, nem tão
# longo que segure um worker do uvicorn por uma Ticketmaster travada (mesmo
# raciocínio do `pool_pre_ping` do code review da Epic 1).
_TIMEOUT = httpx.Timeout(5.0)


def _criar_cliente() -> httpx.Client:
    """Ponto de indireção único: é isto que o teste substitui por um cliente
    com `MockTransport`, sem acrescentar parâmetro à assinatura pública de
    `buscar_eventos`.
    """
    return httpx.Client(timeout=_TIMEOUT)


def _catalogo_indisponivel() -> ErroDeDominio:
    return ErroDeDominio(
        "CATALOGO_INDISPONIVEL",
        "O catálogo da Ticketmaster não respondeu. Tente de novo em instantes.",
        status_http=503,
    )


def _registrar_falha(erro: httpx.HTTPError) -> None:
    """Registra o suficiente para depurar — nunca a URL, que carrega a chave
    (ver o docstring do módulo).

    `401` é erro nosso (chave errada ou revogada) e merece `logger.error`; os
    demais são instabilidade do lado de lá e ficam em `logger.warning`.
    """
    status = getattr(getattr(erro, "response", None), "status_code", None)
    nivel = logger.error if status == 401 else logger.warning
    nivel(
        "Catálogo indisponível: %s (status %s)",
        type(erro).__name__,
        status if status is not None else "sem resposta",
    )


def _melhor_imagem(imagens: list[dict]) -> str | None:
    """A mais larga com `ratio == "16_9"` e sem `fallback`; senão a mais larga
    não-`fallback` qualquer; senão `None`.

    `16_9` é a proporção que a chamada principal da Story 3.3 consome
    (UX-DR4) — resolvida aqui para a Epic 3 não ter que escolher de novo no
    meio de um componente. As imagens `fallback: true` são as genéricas da
    Ticketmaster e não têm nada a ver com o show — melhor nenhuma imagem do
    que uma dessas.
    """
    candidatas = [imagem for imagem in imagens if not imagem.get("fallback")]
    preferidas = [imagem for imagem in candidatas if imagem.get("ratio") == "16_9"]

    grupo = preferidas or candidatas
    if not grupo:
        return None

    mais_larga = max(grupo, key=lambda imagem: imagem.get("width") or 0)
    return mais_larga.get("url")


def _converter_evento(evento: dict) -> ItemDoCatalogo | None:
    """Um evento da Discovery em `ItemDoCatalogo` — tolerante a tudo, menos à
    falta de `id` ou `name`: sem os dois não dá para publicar nada (Story 2.4).

    `_embedded` aninhado tem o mesmo nome nos dois níveis da resposta (o de
    fora tem `events`, o de dentro de cada evento tem `venues` e `attractions`)
    — por isso é lido daqui, do evento, e não do envelope.
    """
    id_externo = evento.get("id")
    nome = evento.get("name")
    if not id_externo or not nome:
        return None

    embutido = evento.get("_embedded") or {}
    venues = embutido.get("venues") or []
    attractions = embutido.get("attractions") or []
    venue = venues[0] if venues else {}
    attraction = attractions[0] if attractions else {}

    return ItemDoCatalogo(
        id_externo=id_externo,
        nome=nome,
        atracao=attraction.get("name"),
        imagem_url=_melhor_imagem(evento.get("images") or []),
        local=venue.get("name"),
        cidade=(venue.get("city") or {}).get("name"),
    )


def buscar_eventos(termo: str, *, limite: int = 20) -> list[ItemDoCatalogo]:
    """Busca eventos na Discovery por nome de show, atração ou casa.

    Termo em branco não gera requisição: a cota é de 5 000 chamadas por dia e
    um campo de busca vazio não vale uma delas. Lista vazia (busca sem
    resultado) e catálogo indisponível (Ticketmaster fora do ar, ou resposta
    ilegível) são situações diferentes — a primeira devolve `[]`, a segunda
    levanta `ErroDeDominio`.
    """
    termo = termo.strip()
    if not termo:
        return []

    settings = obter_settings()

    try:
        with _criar_cliente() as cliente:
            resposta = cliente.get(
                _URL_EVENTOS,
                params={
                    "apikey": settings.ticketmaster_api_key,
                    "keyword": termo,
                    "size": limite,
                    "locale": "*",
                },
            )
            resposta.raise_for_status()
            dados = resposta.json()
    except httpx.HTTPError as erro:
        _registrar_falha(erro)
        raise _catalogo_indisponivel() from erro
    except ValueError as erro:
        # `resposta.json()` levanta isto (via `json.JSONDecodeError`, que
        # herda de `ValueError`) para corpo que não é JSON válido — mesmo
        # tratamento de "a Ticketmaster não respondeu direito".
        logger.warning("Catálogo indisponível: resposta não é JSON válido")
        raise _catalogo_indisponivel() from erro

    eventos = (dados.get("_embedded") or {}).get("events") or []

    itens = []
    for evento in eventos:
        item = _converter_evento(evento)
        if item is not None:
            itens.append(item)
    return itens
