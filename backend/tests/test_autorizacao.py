"""A dependência de papel (AD-9) — precisa do Compose no ar.

**A rota `/_teste` só existe aqui dentro.** Ela é declarada neste arquivo,
montada no `app` real por uma fixture e removida no teardown; `app/` não
importa `tests/`, então nada disso chega a produção.

Por que montar no `app` real e não num `FastAPI()` novo: os três
`exception_handler` que dão à API a forma `{"erro": {...}}` estão registrados
em `app/main.py`. Um app novo não os teria, e estes testes passariam a afirmar
sobre um `{"detail": ...}` que a API de verdade nunca devolve — o pior tipo de
teste verde.

A alternativa era criar uma rota de organizador de mentira em `app/api/`, só
para poder provar o `403`. Ela daria `curl` no navegador e custaria uma rota
que não faz nada esquecida no código de produção.
"""

from collections.abc import Callable, Generator

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.core.dependencias import exigir_papel, usuario_atual
from app.core.seguranca import criar_token_sessao
from app.main import app
from app.models.usuario import PapelUsuario, Usuario

router_de_teste = APIRouter(prefix="/_teste")


@router_de_teste.get("/so-organizador")
def _so_organizador(
    usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
) -> dict[str, str]:
    return {"papel": usuario.papel}


@router_de_teste.get("/organizador-ou-portaria")
def _organizador_ou_portaria(
    usuario: Usuario = Depends(
        exigir_papel(PapelUsuario.ORGANIZADOR, PapelUsuario.PORTARIA)
    ),
) -> dict[str, str]:
    return {"papel": usuario.papel}


@router_de_teste.get("/so-autenticado")
def _so_autenticado(usuario: Usuario = Depends(usuario_atual)) -> dict[str, str]:
    return {"papel": usuario.papel}


@pytest.fixture(scope="module", autouse=True)
def _montar_rotas_de_teste() -> Generator[None, None, None]:
    """Monta e **desmonta** as rotas de teste.

    O `app` é módulo importado, compartilhado por toda a suíte: uma rota que
    fica é uma rota que outro arquivo pode encontrar por acidente, e a ordem de
    execução do pytest passa a importar. O `openapi_schema = None` é a mesma
    ideia — o schema é cacheado na primeira geração, e um schema com rota
    fantasma é o tipo de acoplamento que aparece semanas depois.
    """
    app.include_router(router_de_teste)
    yield
    app.router.routes = [
        rota
        for rota in app.router.routes
        if not getattr(rota, "path", "").startswith("/_teste")
    ]
    app.openapi_schema = None


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    """Faz login de verdade: o cookie do teste é o mesmo que o navegador teria."""
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def test_organizador_entra_na_rota_de_organizador(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/so-organizador")

    assert resposta.status_code == 200
    assert resposta.json()["papel"] == PapelUsuario.ORGANIZADOR.value


def test_cliente_na_rota_de_organizador_recebe_403_sem_permissao(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/so-organizador")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_portaria_na_rota_de_organizador_tambem_recebe_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """A fábrica recusa todo papel fora da lista, não só o CLIENTE."""
    usuario = fabricar_usuario(PapelUsuario.PORTARIA, "portaria@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/so-organizador")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_sem_cookie_na_rota_de_papel_responde_401_e_nao_403(
    cliente: TestClient,
) -> None:
    """Autenticação antes de autorização: primeiro quem é, depois o que pode.

    Este é o teste que quebra se `exigir_papel` chamar `usuario_atual` à mão em
    vez de por `Depends` — a ordem de resolução se inverte e a resposta vira
    `403` para quem nem sessão tem.
    """
    resposta = cliente.get("/_teste/so-organizador")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


@pytest.mark.parametrize(
    "papel",
    [PapelUsuario.ORGANIZADOR, PapelUsuario.PORTARIA],
    ids=["organizador", "portaria"],
)
def test_fabrica_com_dois_papeis_aceita_os_dois(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    papel: PapelUsuario,
) -> None:
    usuario = fabricar_usuario(papel, f"{papel.value.lower()}@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/organizador-ou-portaria")

    assert resposta.status_code == 200
    assert resposta.json()["papel"] == papel.value


def test_fabrica_com_dois_papeis_recusa_o_terceiro(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "terceiro@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/organizador-ou-portaria")

    assert resposta.status_code == 403


def test_papel_forjado_no_token_nao_vale_contra_o_banco(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """O papel conferido é o do banco, nunca o escrito no token.

    Sem este teste, ler `carga["papel"]` em vez de consultar o usuário passaria
    despercebido — e um papel corrigido no banco continuaria valendo o antigo
    pelas 8 horas de vida da sessão (AD-15).
    """
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "farsante@exemplo.com")

    # Mesmo `sub`, `papel` trocado. O objeto de mentira só serve de molde para
    # `criar_token_sessao`: ele nunca vai ao banco.
    molde = Usuario(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=usuario.senha_hash,
        papel=PapelUsuario.ORGANIZADOR.value,
    )
    cliente.cookies.set("rockhub_sessao", criar_token_sessao(molde))

    resposta = cliente.get("/_teste/so-organizador")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


@pytest.mark.parametrize(
    "papel",
    [PapelUsuario.ORGANIZADOR, PapelUsuario.CLIENTE, PapelUsuario.PORTARIA],
    ids=["organizador", "cliente", "portaria"],
)
def test_rota_so_autenticada_aceita_qualquer_papel(
    cliente: TestClient,
    fabricar_usuario: Callable[..., Usuario],
    papel: PapelUsuario,
) -> None:
    usuario = fabricar_usuario(papel, f"qualquer-{papel.value.lower()}@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/_teste/so-autenticado")

    assert resposta.status_code == 200
    assert resposta.json()["papel"] == papel.value
