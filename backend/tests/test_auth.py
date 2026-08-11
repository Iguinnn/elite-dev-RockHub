"""`POST /auth/cadastro`, `/auth/login`, `/auth/logout` e `GET /auth/eu` —
precisa do Compose no ar.

A fixture `cliente`, que liga o `TestClient` (HTTP) à fixture `sessao`
(transação revertida ao fim de cada teste) por `dependency_overrides`, mora no
`conftest.py` desde a Story 1.6 — o `test_autorizacao.py` também a usa.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguranca import criar_token_sessao, gerar_hash
from app.models.usuario import PapelUsuario, Usuario


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
        # Desde a Story 2.1 a chave da Ticketmaster também é obrigatória em
        # produção — sem isto, a `Settings` nem chega a existir para este
        # teste, que não tem nada a ver com catálogo.
        ticketmaster_api_key="chave-de-teste-nao-vaze-isto",
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


# ---------------------------------------------------------------------------
# GET /auth/eu — Story 1.6
#
# ⚠️ O `TestClient` guarda cookie entre chamadas: depois de um `POST
# /auth/login` no mesmo `cliente`, o `GET /auth/eu` já vai autenticado. Os
# testes de `401` usam um `cliente` que nunca entrou, ou limpam os cookies.
# ---------------------------------------------------------------------------


def _entrar(cliente: TestClient) -> dict:
    resposta = cliente.post(
        "/auth/login", json={"email": "igor@exemplo.com", "senha": "rockhub"}
    )
    assert resposta.status_code == 200
    return resposta.json()


def test_eu_com_cookie_do_login_responde_200_sem_senha_hash(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    _entrar(cliente)

    resposta = cliente.get("/auth/eu")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(usuario_gravado.id)
    assert corpo["nome"] == "Igor Teste"
    assert corpo["email"] == "igor@exemplo.com"
    assert corpo["papel"] == PapelUsuario.CLIENTE.value
    assert "senha_hash" not in corpo
    assert "senha" not in corpo


def test_eu_devolve_exatamente_o_mesmo_corpo_do_login(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    """Três rotas, um schema. Divergência entre elas é o que quebra aqui."""
    corpo_do_login = _entrar(cliente)

    assert cliente.get("/auth/eu").json() == corpo_do_login


def test_eu_sem_cookie_responde_401_no_formato_de_erro(cliente: TestClient) -> None:
    resposta = cliente.get("/auth/eu")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_eu_com_assinatura_adulterada_responde_401(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    """O caractere trocado é o do **meio** da assinatura, nunca o último.

    A assinatura HMAC-SHA256 ocupa 43 caracteres em base64url e os 2 bits
    finais são padding: trocar o último por `A`, `B`, `C` ou `D` decodifica
    para os mesmos 32 bytes e não adultera nada. Diagnóstico no Debug Log da
    Story 1.5.
    """
    _entrar(cliente)
    cabecalho, carga, assinatura = cliente.cookies["rockhub_sessao"].split(".")

    meio = len(assinatura) // 2
    trocado = "A" if assinatura[meio] != "A" else "B"
    adulterada = assinatura[:meio] + trocado + assinatura[meio + 1 :]

    cliente.cookies.set("rockhub_sessao", f"{cabecalho}.{carga}.{adulterada}")
    resposta = cliente.get("/auth/eu")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_eu_com_cookie_que_nem_e_jwt_responde_401_e_nao_500(
    cliente: TestClient,
) -> None:
    cliente.cookies.set("rockhub_sessao", "nao-e-um-token")

    resposta = cliente.get("/auth/eu")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_eu_com_token_valido_de_usuario_apagado_responde_401(
    cliente: TestClient,
) -> None:
    """Token assinado por nós, e mesmo assim `401`: a conta não existe mais.

    É o quarto caminho da dependência, e responde igual aos outros três de
    propósito — diferenciá-lo faria a rota confirmar quais ids já existiram.
    """
    fantasma = Usuario(
        id=uuid.uuid4(),
        nome="Quem Já Foi",
        email="fantasma@exemplo.com",
        senha_hash=gerar_hash("rockhub"),
        papel=PapelUsuario.CLIENTE.value,
    )
    cliente.cookies.set("rockhub_sessao", criar_token_sessao(fantasma))

    resposta = cliente.get("/auth/eu")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_eu_depois_do_logout_responde_401(
    cliente: TestClient, usuario_gravado: Usuario
) -> None:
    _entrar(cliente)
    assert cliente.get("/auth/eu").status_code == 200

    cliente.post("/auth/logout")

    resposta = cliente.get("/auth/eu")
    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"
