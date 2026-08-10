"""`POST /auth/cadastro`, `/auth/login` e `/auth/logout` — precisa do Compose no ar.

A ponte entre o `TestClient` (HTTP) e a fixture `sessao` (transação revertida
ao fim de cada teste) é `dependency_overrides`, substituindo `obter_sessao`.
Ver Dev Notes da Story 1.4, "Ligar o `TestClient` ao banco de teste".
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
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


# ---------------------------------------------------------------------------
# POST /auth/cadastro — Story 1.5
# ---------------------------------------------------------------------------

CADASTRO_VALIDO = {
    "nome": "Ana Ribeiro",
    "email": "ana@exemplo.com",
    "senha": "rockhub",
}


def test_cadastro_responde_201_com_papel_cliente_e_sem_senha(
    cliente: TestClient,
) -> None:
    resposta = cliente.post("/auth/cadastro", json=CADASTRO_VALIDO)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["papel"] == PapelUsuario.CLIENTE.value
    assert corpo["nome"] == "Ana Ribeiro"
    assert corpo["email"] == "ana@exemplo.com"
    assert "id" in corpo
    assert "senha" not in corpo
    assert "senha_hash" not in corpo


def test_cadastro_grava_hash_argon2id_e_nao_a_senha_digitada(
    cliente: TestClient, sessao: Session
) -> None:
    cliente.post("/auth/cadastro", json=CADASTRO_VALIDO)

    gravado = sessao.scalar(select(Usuario).where(Usuario.email == "ana@exemplo.com"))
    assert gravado is not None
    assert gravado.senha_hash.startswith("$argon2id$")
    assert gravado.senha_hash != "rockhub"


def test_cadastro_grava_o_mesmo_cookie_de_sessao_que_o_login(
    cliente: TestClient,
) -> None:
    """Os atributos do cadastro são comparados **contra os do login**.

    Afirmar os quatro atributos à mão nos dois lugares deixaria o teste passar
    no dia em que só um dos dois mudasse. Aqui, divergência entre as rotas é o
    que quebra — que é exatamente o que o helper compartilhado deve impedir.
    """
    resposta_cadastro = cliente.post("/auth/cadastro", json=CADASTRO_VALIDO)
    resposta_login = cliente.post(
        "/auth/login", json={"email": "ana@exemplo.com", "senha": "rockhub"}
    )

    def atributos(cabecalho: str) -> set[str]:
        # O valor do cookie é o único pedaço que difere entre as duas
        # respostas (o token carrega o instante de emissão).
        return {
            pedaco.strip()
            for pedaco in cabecalho.split(";")
            if not pedaco.strip().startswith("rockhub_sessao=")
        }

    cookie_cadastro = resposta_cadastro.headers["set-cookie"]
    assert "HttpOnly" in cookie_cadastro
    assert "SameSite=lax" in cookie_cadastro or "SameSite=Lax" in cookie_cadastro
    assert "Path=/" in cookie_cadastro
    assert "Max-Age=28800" in cookie_cadastro
    assert atributos(cookie_cadastro) == atributos(resposta_login.headers["set-cookie"])


def test_conta_criada_pelo_cadastro_consegue_entrar_pelo_login(
    cliente: TestClient,
) -> None:
    cliente.post("/auth/cadastro", json=CADASTRO_VALIDO)

    resposta = cliente.post(
        "/auth/login", json={"email": "ana@exemplo.com", "senha": "rockhub"}
    )

    assert resposta.status_code == 200


def test_email_ja_cadastrado_responde_409(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/cadastro",
        json={"nome": "Outro Igor", "email": "igor@exemplo.com", "senha": "rockhub"},
    )

    # Nada de `assert` sobre o banco depois de um 409: o `rollback()` do
    # service desfaz a transação até o savepoint e leva junto o usuário que a
    # fixture inseriu por `flush`. A resposta é o que o critério pede.
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EMAIL_JA_CADASTRADO"


def test_email_ja_cadastrado_com_outra_caixa_responde_409_e_nao_500(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    resposta = cliente.post(
        "/auth/cadastro",
        json={"nome": "Outro Igor", "email": " IGOR@Exemplo.COM ", "senha": "rockhub"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "EMAIL_JA_CADASTRADO"


def test_papel_no_corpo_e_ignorado_e_a_conta_nasce_cliente(
    cliente: TestClient,
) -> None:
    resposta = cliente.post(
        "/auth/cadastro", json={**CADASTRO_VALIDO, "papel": "ORGANIZADOR"}
    )

    assert resposta.status_code == 201
    assert resposta.json()["papel"] == PapelUsuario.CLIENTE.value


def test_senha_curta_responde_422_e_nao_cria_conta(
    cliente: TestClient, sessao: Session
) -> None:
    resposta = cliente.post("/auth/cadastro", json={**CADASTRO_VALIDO, "senha": "rock"})

    assert resposta.status_code == 422
    assert "erro" in resposta.json()
    assert sessao.scalar(select(Usuario).where(Usuario.email == "ana@exemplo.com")) is None


@pytest.mark.parametrize(
    "email",
    ["ana", "ana@exemplo", "ana exu@exemplo.com"],
    ids=["sem-arroba", "sem-ponto-no-dominio", "com-espaco-no-meio"],
)
def test_email_malformado_responde_422(cliente: TestClient, email: str) -> None:
    resposta = cliente.post("/auth/cadastro", json={**CADASTRO_VALIDO, "email": email})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_nome_so_com_espacos_responde_422(cliente: TestClient) -> None:
    resposta = cliente.post("/auth/cadastro", json={**CADASTRO_VALIDO, "nome": "   "})

    assert resposta.status_code == 422


def test_nome_longo_demais_responde_422_e_nao_500_por_truncamento(
    cliente: TestClient,
) -> None:
    resposta = cliente.post(
        "/auth/cadastro", json={**CADASTRO_VALIDO, "nome": "a" * 121}
    )

    assert resposta.status_code == 422


def test_cadastro_sem_campo_obrigatorio_responde_422_no_formato_de_erro(
    cliente: TestClient,
) -> None:
    resposta = cliente.post(
        "/auth/cadastro", json={"email": "ana@exemplo.com", "senha": "rockhub"}
    )

    assert resposta.status_code == 422
    assert "erro" in resposta.json()


def test_email_com_maiusculas_e_espacos_e_gravado_em_minusculas(
    cliente: TestClient, sessao: Session
) -> None:
    resposta = cliente.post(
        "/auth/cadastro", json={**CADASTRO_VALIDO, "email": "  Ana@Exemplo.COM "}
    )

    assert resposta.status_code == 201
    assert resposta.json()["email"] == "ana@exemplo.com"
    assert (
        sessao.scalar(select(Usuario).where(Usuario.email == "ana@exemplo.com"))
        is not None
    )
