"""Rotas de autenticação: entrar e sair.

Nenhuma verificação de papel aqui — autorização por papel é dependência do
FastAPI e é assunto da Story 1.6 (AD-9).
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.db import obter_sessao
from app.core.seguranca import EXPIRACAO_SESSAO, criar_token_sessao
from app.schemas.auth import LoginEntrada, UsuarioSaida
from app.services import autenticacao

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/login", response_model=UsuarioSaida, status_code=200)
def entrar(
    dados: LoginEntrada,
    resposta: Response,
    sessao: Session = Depends(obter_sessao),
) -> UsuarioSaida:
    usuario = autenticacao.autenticar(sessao, dados.email, dados.senha)
    settings = obter_settings()
    token = criar_token_sessao(usuario)

    resposta.set_cookie(
        key=settings.cookie_sessao_nome,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=int(EXPIRACAO_SESSAO.total_seconds()),
    )

    return UsuarioSaida.model_validate(usuario)


@router.post("/logout", status_code=204)
def sair(resposta: Response) -> None:
    settings = obter_settings()
    resposta.delete_cookie(
        key=settings.cookie_sessao_nome,
        path="/",
        samesite="lax",
        secure=settings.cookie_secure,
    )
