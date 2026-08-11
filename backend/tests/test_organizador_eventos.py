"""Rota `POST /organizador/eventos` (Story 2.4) — a primeira rota de escrita
do domínio.

Precisa do Compose no ar (faz login de verdade, como o `test_organizador_
catalogo.py`) e roda com **zero rede**: publicar não chama a Ticketmaster, e
um dos testes prova isso instalando um transporte que falha se for tocado.

Todo teste que afirma gravação lê do **banco**, não só do corpo da resposta. A
resposta prova o schema de saída; só o `sessao.get(Evento, id)` prova que a
linha existe do jeito que deveria.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations import ticketmaster
from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario


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


def _corpo(**ajustes: Any) -> dict[str, Any]:
    """Corpo válido, com ajuste por parâmetro.

    Existe para que cada teste mostre **só** o que ele muda: quinze
    dicionários quase iguais escondem exatamente a linha que importa.
    """
    corpo: dict[str, Any] = {
        "origem_externa_id": "G5vYZ9a1kd",
        "nome": "Baco Exu do Blues — Bluesman Vivo",
        "imagem_url": "https://s1.ticketm.net/dam/a/bluesman.jpg",
        "data_hora": "2026-08-15T00:00:00Z",
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


# --------------------------------------------------------------------------- #
# AC1 — o evento existe no banco com os campos do catálogo copiados
# --------------------------------------------------------------------------- #


def test_organizador_publica_e_o_evento_esta_no_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador1@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

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
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador2@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

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
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador3@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

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
) -> None:
    # ⚠️ O e-mail padrão da fixture é fixo: dois usuários no mesmo teste
    # precisam de e-mails distintos, senão o segundo bate no UNIQUE da 1.3.
    publicador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "quem-publica@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "o-outro@exemplo.com")
    _entrar(cliente, publicador)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    assert gravado.organizador_id == publicador.id
    assert gravado.organizador_id != outro.id


def test_organizador_id_mandado_no_corpo_e_ignorado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    publicador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "dono@exemplo.com")
    vitima = fabricar_usuario(PapelUsuario.ORGANIZADOR, "vitima@exemplo.com")
    _entrar(cliente, publicador)

    # O campo não existe no schema de entrada, e o schema não tem
    # `extra="forbid"`: o corpo não é recusado, ele é **ignorado**.
    resposta = cliente.post(
        "/organizador/eventos",
        json=_corpo(organizador_id=str(vitima.id)),
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_transporte(
        monkeypatch,
        lambda requisicao: pytest.fail("a publicação chamou a Ticketmaster"),
    )

    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador4@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.post("/organizador/eventos", json=_corpo())

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
            ]
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
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador15@exemplo.com")
    _entrar(cliente, usuario)

    # 21h de 14/08 em São Paulo (-03:00) é 00h de 15/08 em UTC — é exatamente
    # a conversão que o navegador faz antes de enviar.
    resposta = cliente.post(
        "/organizador/eventos", json=_corpo(data_hora="2026-08-14T21:00:00-03:00")
    )

    assert resposta.status_code == 201
    gravado = sessao.get(Evento, resposta.json()["id"])
    assert gravado is not None
    assert gravado.data_hora == datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc)
