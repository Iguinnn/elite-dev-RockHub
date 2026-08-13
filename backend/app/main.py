"""Ponto de entrada da API.

O caminho `app.main:app` é fixo: é o que o uvicorn recebe no desenvolvimento e o
que o deploy da Railway vai apontar. Mudá-lo quebra os dois.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, cliente, organizador, portaria, publico, saude
from app.core.config import obter_settings
from app.core.erros import (
    MENSAGEM_PADRAO,
    ErroDeDominio,
    codigo_para_status,
    corpo_de_erro,
    descrever_erros_de_validacao,
    mensagem_para_status,
)

logger = logging.getLogger(__name__)

settings = obter_settings()

app = FastAPI(
    title=settings.app_nome,
    description="API da plataforma de eventos e ingressos RockHub.",
    version="0.1.0",
)

# `allow_credentials=True` porque a sessão será um cookie httpOnly: sem isso o
# navegador não envia o cookie nas chamadas vindas do frontend em outra origem.
# Por essa mesma razão as origens são explícitas — o curinga "*" é incompatível
# com credenciais.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Erros
#
# Os quatro handlers abaixo existem para que a API tenha **uma** forma de erro.
# Sem eles, o `{"erro": {...}}` do domínio conviveria com o `{"detail": ...}` que
# o FastAPI devolve por conta própria, e o frontend precisaria saber os dois.
#
# O quarto — o de `Exception` — é o que fecha a promessa. Com só os três
# primeiros, qualquer falha não prevista subia até o `ServerErrorMiddleware` do
# Starlette e voltava como `Internal Server Error` em **texto puro**: a única
# resposta da API fora do formato que este módulo inteiro existe para garantir.
# --------------------------------------------------------------------------- #


@app.exception_handler(ErroDeDominio)
async def tratar_erro_de_dominio(_: Request, erro: ErroDeDominio) -> JSONResponse:
    """Falha prevista pela regra de negócio."""
    return JSONResponse(status_code=erro.status_http, content=erro.como_corpo())


def _mensagem_gerada_pelo_framework(erro: StarletteHTTPException) -> bool:
    """O `detail` veio do Starlette, e não de quem levantou a exceção?

    Quando ninguém passa `detail`, o Starlette o preenche com a frase padrão do
    `HTTPStatus` — em inglês. Comparar com essa frase é o que separa "o
    framework não disse nada" de "alguém escreveu esta mensagem de propósito",
    e é o que permite traduzir a primeira sem sobrescrever a segunda.
    """
    try:
        return erro.detail == HTTPStatus(erro.status_code).phrase
    except ValueError:
        # Status fora da enumeração: então não é frase gerada pelo Starlette.
        return False


@app.exception_handler(StarletteHTTPException)
async def tratar_erro_http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
    """Rota inexistente, método errado, `HTTPException` levantado à mão.

    Captura o `HTTPException` do Starlette, do qual o do FastAPI herda — então os
    dois passam por aqui.

    A mensagem de quem levantou a exceção à mão é preservada; só a frase padrão
    do framework é trocada pela versão em português.
    """
    if not isinstance(erro.detail, str):
        mensagem = MENSAGEM_PADRAO
    elif _mensagem_gerada_pelo_framework(erro):
        mensagem = mensagem_para_status(erro.status_code)
    else:
        mensagem = erro.detail

    return JSONResponse(
        status_code=erro.status_code,
        content=corpo_de_erro(codigo_para_status(erro.status_code), mensagem),
        # Preserva cabeçalhos que fazem parte da semântica da resposta, como o
        # `WWW-Authenticate` do 401 e o `Allow` do 405.
        headers=erro.headers,
    )


@app.exception_handler(RequestValidationError)
async def tratar_erro_de_validacao(
    _: Request, erro: RequestValidationError
) -> JSONResponse:
    """Corpo, query ou path que não passaram na validação do Pydantic."""
    return JSONResponse(
        status_code=422,
        content=corpo_de_erro(
            codigo_para_status(422), descrever_erros_de_validacao(erro.errors())
        ),
    )


@app.exception_handler(Exception)
async def tratar_erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
    """Qualquer falha não prevista — o banco fora do ar, um bug meu.

    **Não expõe a causa.** O corpo é sempre o mesmo `ERRO_INTERNO` genérico:
    mensagem de exceção costuma carregar host, usuário e nome de tabela, e isso
    não volta para quem chamou. O rastro inteiro vai para o log, que é onde ele
    serve para alguma coisa.

    O `exc_info` é explícito porque o `ServerErrorMiddleware` do Starlette
    relança a exceção depois que esta resposta é enviada — o uvicorn a registra
    de qualquer jeito, mas depender disso deixaria o log dependente de quem
    hospeda. Aqui o registro é meu.
    """
    logger.error("Falha não tratada em uma requisição", exc_info=erro)
    return JSONResponse(
        status_code=500,
        content=corpo_de_erro(codigo_para_status(500), MENSAGEM_PADRAO),
    )


app.include_router(auth.router)
app.include_router(cliente.router)
app.include_router(organizador.router)
app.include_router(portaria.router)
app.include_router(publico.router)
app.include_router(saude.router)
