"""Ponto de entrada da API.

O caminho `app.main:app` é fixo: é o que o uvicorn recebe no desenvolvimento e o
que o deploy da Railway vai apontar. Mudá-lo quebra os dois.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, saude
from app.core.config import obter_settings
from app.core.erros import (
    MENSAGEM_PADRAO,
    ErroDeDominio,
    codigo_para_status,
    corpo_de_erro,
    descrever_erros_de_validacao,
)

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
# Os três handlers abaixo existem para que a API tenha **uma** forma de erro. Sem
# eles, o `{"erro": {...}}` do domínio conviveria com o `{"detail": ...}` que o
# FastAPI devolve por conta própria, e o frontend precisaria saber os dois.
# --------------------------------------------------------------------------- #


@app.exception_handler(ErroDeDominio)
async def tratar_erro_de_dominio(_: Request, erro: ErroDeDominio) -> JSONResponse:
    """Falha prevista pela regra de negócio."""
    return JSONResponse(status_code=erro.status_http, content=erro.como_corpo())


@app.exception_handler(StarletteHTTPException)
async def tratar_erro_http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
    """Rota inexistente, método errado, `HTTPException` levantado à mão.

    Captura o `HTTPException` do Starlette, do qual o do FastAPI herda — então os
    dois passam por aqui.
    """
    mensagem = erro.detail if isinstance(erro.detail, str) else MENSAGEM_PADRAO
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


app.include_router(saude.router)
app.include_router(auth.router)
