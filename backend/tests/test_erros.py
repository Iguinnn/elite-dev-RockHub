"""Contrato do formato de erro — o que todas as stories seguintes vão devolver.

Se estes testes quebrarem, o frontend inteiro quebra junto: ele decide o texto
pelo `codigo`, não pela mensagem.

A API tem **uma** forma de erro, `{"erro": {"codigo": ..., "mensagem": ...}}`,
venha ela da regra de negócio, do framework ou da validação do Pydantic.
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.erros import ErroDeDominio, descrever_erros_de_validacao
from app.main import app as app_real
from app.main import (
    tratar_erro_de_dominio,
    tratar_erro_de_validacao,
    tratar_erro_http,
    tratar_erro_inesperado,
)

cliente_real = TestClient(app_real)


# --------------------------------------------------------------------------- #
# Erro de domínio
# --------------------------------------------------------------------------- #


def _app_de_dominio() -> FastAPI:
    """App mínima com o handler real e uma rota que só serve para falhar."""
    app = FastAPI()
    app.add_exception_handler(ErroDeDominio, tratar_erro_de_dominio)

    @app.get("/estoura")
    def estoura() -> None:
        raise ErroDeDominio(
            codigo="ESTOQUE_INSUFICIENTE",
            mensagem="Não há ingressos suficientes neste setor.",
            status_http=409,
        )

    return app


def test_erro_de_dominio_vira_o_corpo_padrao() -> None:
    cliente = TestClient(_app_de_dominio(), raise_server_exceptions=False)

    resposta = cliente.get("/estoura")

    assert resposta.status_code == 409
    assert resposta.json() == {
        "erro": {
            "codigo": "ESTOQUE_INSUFICIENTE",
            "mensagem": "Não há ingressos suficientes neste setor.",
        }
    }


def test_status_padrao_do_erro_de_dominio_e_400() -> None:
    erro = ErroDeDominio(codigo="DADOS_INVALIDOS", mensagem="Faltou o setor.")

    assert erro.status_http == 400
    assert erro.como_corpo() == {
        "erro": {"codigo": "DADOS_INVALIDOS", "mensagem": "Faltou o setor."}
    }


# --------------------------------------------------------------------------- #
# Erros levantados pelo próprio framework — testados na aplicação real
# --------------------------------------------------------------------------- #


def test_rota_inexistente_usa_o_mesmo_formato() -> None:
    resposta = cliente_real.get("/rota-que-nao-existe")

    assert resposta.status_code == 404
    assert resposta.json() == {
        "erro": {
            "codigo": "NAO_ENCONTRADO",
            "mensagem": "Esse endereço não existe nesta API.",
        }
    }


def test_mensagem_do_framework_vem_em_portugues() -> None:
    """A API é escrita em português inteira — inclusive quando o Starlette fala.

    Sem a tradução, o `detail` que o Starlette gera sozinho ("Not Found",
    "Method Not Allowed") seria a única string em inglês do sistema, e ela
    apareceria justamente no primeiro erro de quem explora o `/docs`.
    """
    assert "Not Found" not in cliente_real.get("/nao-existe").text
    assert "Method Not Allowed" not in cliente_real.post("/saude").text


def test_metodo_errado_usa_o_mesmo_formato_e_preserva_o_allow() -> None:
    resposta = cliente_real.post("/saude")

    assert resposta.status_code == 405
    assert resposta.json()["erro"]["codigo"] == "METODO_NAO_PERMITIDO"
    # O cabeçalho `Allow` é semântica da resposta 405 e não pode se perder no
    # caminho até o nosso formato de erro.
    assert "GET" in resposta.headers.get("allow", "")


def test_http_exception_levantado_a_mao_preserva_a_mensagem() -> None:
    app = FastAPI()
    app.add_exception_handler(StarletteHTTPException, tratar_erro_http)

    @app.get("/restrito")
    def restrito() -> None:
        raise HTTPException(status_code=403, detail="Este evento não é seu.")

    cliente = TestClient(app, raise_server_exceptions=False)

    resposta = cliente.get("/restrito")

    assert resposta.status_code == 403
    assert resposta.json() == {
        "erro": {"codigo": "SEM_PERMISSAO", "mensagem": "Este evento não é seu."}
    }


# --------------------------------------------------------------------------- #
# Validação do Pydantic
# --------------------------------------------------------------------------- #


class _Reserva(BaseModel):
    setor_id: str
    quantidade: int


def _app_de_validacao() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, tratar_erro_de_validacao)

    @app.post("/reservas")
    def reservar(reserva: _Reserva) -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_corpo_invalido_usa_o_mesmo_formato() -> None:
    cliente = TestClient(_app_de_validacao(), raise_server_exceptions=False)

    resposta = cliente.post("/reservas", json={"quantidade": "duas"})

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["erro"]["codigo"] == "DADOS_INVALIDOS"
    # A mensagem diz quais campos reprovaram — sem isso o 422 é indepurável.
    assert "setor_id" in corpo["erro"]["mensagem"]
    assert "quantidade" in corpo["erro"]["mensagem"]
    assert set(corpo["erro"].keys()) == {"codigo", "mensagem"}


def test_descricao_de_validacao_ignora_a_origem_do_campo() -> None:
    """`loc` começa com "body"/"query" — ruído para quem lê a mensagem."""
    descricao = descrever_erros_de_validacao(
        [{"loc": ("body", "quantidade"), "msg": "campo obrigatório"}]
    )

    assert descricao == "quantidade: campo obrigatório"


def test_descricao_de_validacao_junta_varios_campos() -> None:
    descricao = descrever_erros_de_validacao(
        [
            {"loc": ("body", "setor_id"), "msg": "campo obrigatório"},
            {"loc": ("body", "quantidade"), "msg": "não é um inteiro"},
        ]
    )

    assert descricao == "setor_id: campo obrigatório; quantidade: não é um inteiro"


# --------------------------------------------------------------------------- #
# Fiação
# --------------------------------------------------------------------------- #


def test_aplicacao_registra_os_quatro_handlers() -> None:
    """Garante que a padronização vale na app real, não só nas de teste."""
    registrados = app_real.exception_handlers

    assert registrados[ErroDeDominio] is tratar_erro_de_dominio
    assert registrados[StarletteHTTPException] is tratar_erro_http
    assert registrados[RequestValidationError] is tratar_erro_de_validacao
    assert registrados[Exception] is tratar_erro_inesperado


# --------------------------------------------------------------------------- #
# Falha não prevista
# --------------------------------------------------------------------------- #


def test_excecao_inesperada_tambem_usa_o_formato_padrao() -> None:
    """O 500 era a única resposta da API fora do `{"erro": {...}}`.

    `raise_server_exceptions=False` para o `TestClient` devolver a resposta em
    vez de relançar a exceção — é o comportamento do servidor de verdade que
    interessa aqui, não o do cliente de teste.
    """
    app = FastAPI()
    app.add_exception_handler(Exception, tratar_erro_inesperado)

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError("connection to server at 10.0.0.4 failed: senha=hunter2")

    cliente = TestClient(app, raise_server_exceptions=False)

    resposta = cliente.get("/explode")

    assert resposta.status_code == 500
    assert resposta.json() == {
        "erro": {
            "codigo": "ERRO_INTERNO",
            "mensagem": "Não foi possível completar a requisição.",
        }
    }
    # A causa fica no log, nunca no corpo: mensagem de exceção carrega host,
    # usuário e credencial com frequência demais para virar resposta HTTP.
    assert "10.0.0.4" not in resposta.text
    assert "hunter2" not in resposta.text
