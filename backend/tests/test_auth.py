"""`POST /auth/login` e `POST /auth/logout` — precisa do Compose no ar.

A ponte entre o `TestClient` (HTTP) e a fixture `sessao` (transação revertida
ao fim de cada teste) é `dependency_overrides`, substituindo `obter_sessao`.
Ver Dev Notes da Story 1.4, "Ligar o `TestClient` ao banco de teste".
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.seguranca import gerar_hash
from app.main import app
from app.models.usuario import PapelUsuario, Usuario


@pytest.fixture()
def cliente(sessao: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obter_sessao] = lambda: sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def usuario_gravado(sessao: Session) -> Usuario:
    usuario = Usuario(
        nome="Igor Teste",
        email="igor@exemplo.com",
        senha_hash=gerar_hash("rockhub"),
        papel=PapelUsuario.CLIENTE.value,
    )
    sessao.add(usuario)
    sessao.flush()
    sessao.refresh(usuario)
    return usuario


def test_login_correto_responde_200_com_papel_e_sem_senha_hash(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "rockhub"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["papel"] == PapelUsuario.CLIENTE.value
    assert "senha_hash" not in corpo
    assert "senha" not in corpo


def test_senha_gravada_no_banco_e_hash_argon2id_diferente_da_senha_digitada(
    sessao: Session, usuario_gravado: Usuario
) -> None:
    sessao.refresh(usuario_gravado)

    assert usuario_gravado.senha_hash.startswith("$argon2id$")
    assert usuario_gravado.senha_hash != "rockhub"


def test_login_correto_grava_cookie_httponly_lax_path_e_max_age(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "rockhub"}
    )

    cookie_bruto = resposta.headers["set-cookie"]
    assert "HttpOnly" in cookie_bruto
    assert "SameSite=lax" in cookie_bruto or "SameSite=Lax" in cookie_bruto
    assert "Path=/" in cookie_bruto
    assert "Max-Age=28800" in cookie_bruto


def test_cookie_e_secure_apenas_em_producao(
    cliente: TestClient, usuario_gravado: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    resposta_local = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "rockhub"}
    )
    assert "Secure" not in resposta_local.headers["set-cookie"]

    from app.api import auth as auth_router
    from app.core.config import Settings

    settings_producao = Settings(
        _env_file=None,
        ambiente="producao",
        jwt_secret="um-segredo-de-teste-com-trinta-e-dois-bytes",
    )
    monkeypatch.setattr(auth_router, "obter_settings", lambda: settings_producao)

    resposta_producao = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "rockhub"}
    )
    assert "Secure" in resposta_producao.headers["set-cookie"]


def test_senha_errada_responde_401_credenciais_invalidas(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "senha-errada"}
    )

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_email_inexistente_responde_exatamente_igual_a_senha_errada(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta_email_errado = cliente.post(
        "/auth/login",
        json={"email": "nao-existe@exemplo.com", "senha": "qualquer"},
    )
    resposta_senha_errada = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "senha-errada"}
    )

    assert resposta_email_errado.status_code == resposta_senha_errada.status_code
    assert resposta_email_errado.json() == resposta_senha_errada.json()


def test_email_com_maiusculas_e_espaco_entra_na_conta_gravada_em_minusculas(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": "Igor@Exemplo.COM ", "senha": "rockhub"}
    )

    assert resposta.status_code == 200


def test_login_sem_senha_responde_422_no_formato_de_erro(cliente: TestClient) -> None:
    resposta = cliente.post("/auth/login", json={"email": "igor@exemplo.com"})

    assert resposta.status_code == 422
    assert "erro" in resposta.json()


def test_logout_responde_204_e_esvazia_o_cookie(cliente: TestClient) -> None:
    resposta = cliente.post("/auth/logout")

    assert resposta.status_code == 204
    cookie_bruto = resposta.headers["set-cookie"]
    assert 'rockhub_sessao=""' in cookie_bruto
    assert "Max-Age=0" in cookie_bruto
    assert "Path=/" in cookie_bruto


def test_logout_sem_cookie_nenhum_tambem_responde_204(cliente: TestClient) -> None:
    resposta = cliente.post("/auth/logout")

    assert resposta.status_code == 204
