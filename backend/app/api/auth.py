"""Rotas de autenticação: criar conta, entrar, sair e saber quem está logado.

Nenhuma verificação de papel aqui, e nem poderia haver: autorização por papel é
dependência declarada na assinatura do endpoint e mora em
`app/core/dependencias.py` (AD-9). Estas quatro rotas são justamente as que
qualquer papel pode chamar.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.db import obter_sessao
from app.core.dependencias import usuario_atual
from app.core.seguranca import EXPIRACAO_SESSAO, criar_token_sessao
from app.models.usuario import Usuario
from app.schemas.auth import CadastroEntrada, LoginEntrada, UsuarioSaida
from app.services import autenticacao

router = APIRouter(prefix="/auth", tags=["autenticação"])


# Os dois helpers ficam adjacentes de propósito: atributo que diverge entre
# gravar e apagar produz cookie que o navegador não apaga, e a única defesa
# contra isso é os dois estarem sempre à vista um do outro.
#
# `obter_settings()` é chamado aqui dentro, e não recebido por parâmetro: o
# teste `test_cookie_e_secure_apenas_em_producao` substitui o nome no módulo
# por monkeypatch. Um helper que receba a `Settings` de fora faz aquele teste
# passar sem testar nada.
def _gravar_cookie_de_sessao(resposta: Response, usuario: Usuario) -> None:
    settings = obter_settings()
    resposta.set_cookie(
        key=settings.cookie_sessao_nome,
        value=criar_token_sessao(usuario),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=int(EXPIRACAO_SESSAO.total_seconds()),
    )


def _limpar_cookie_de_sessao(resposta: Response) -> None:
    settings = obter_settings()
    resposta.delete_cookie(
        key=settings.cookie_sessao_nome,
        path="/",
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.post("/cadastro", response_model=UsuarioSaida, status_code=201)
def cadastrar_cliente(
    dados: CadastroEntrada,
    resposta: Response,
    sessao: Session = Depends(obter_sessao),
) -> UsuarioSaida:
    """Cria a conta e **já entra**: mesma sessão que o login abriria.

    Obrigar a pessoa a digitar de novo o e-mail e a senha que acabou de
    escolher é atrito sem contrapartida — a credencial já foi provada no ato
    de criar a conta.
    """
    usuario = autenticacao.cadastrar(sessao, dados.nome, dados.email, dados.senha)
    _gravar_cookie_de_sessao(resposta, usuario)
    return UsuarioSaida.model_validate(usuario)


@router.post("/login", response_model=UsuarioSaida, status_code=200)
def entrar(
    dados: LoginEntrada,
    resposta: Response,
    sessao: Session = Depends(obter_sessao),
) -> UsuarioSaida:
    usuario = autenticacao.autenticar(sessao, dados.email, dados.senha)
    _gravar_cookie_de_sessao(resposta, usuario)
    return UsuarioSaida.model_validate(usuario)


@router.post("/logout", status_code=204)
def sair(resposta: Response) -> None:
    _limpar_cookie_de_sessao(resposta)


@router.get("/eu", response_model=UsuarioSaida)
def quem_sou_eu(usuario: Usuario = Depends(usuario_atual)) -> UsuarioSaida:
    """Quem está do outro lado do cookie. Responde `401` quando não há ninguém.

    Nenhuma `Session` na assinatura: `usuario_atual` já recebeu a dela, e pedir
    uma segunda aqui abriria uma sessão que este handler não usa.
    """
    return UsuarioSaida.model_validate(usuario)
