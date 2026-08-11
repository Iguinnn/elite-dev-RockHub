"""Configuração vem do ambiente — inclusive a lista de origens do CORS."""

import pytest

from app.core.config import Settings

# `Settings(_env_file=None)` desliga a leitura do `.env`, mas **não** as
# variáveis do processo. Quem administra a Railway do mesmo terminal costuma
# ter `AMBIENTE` ou `JWT_SECRET` exportados na shell — e aí estes testes
# falhariam por causa do ambiente de quem roda, não do código. Esta fixture
# limpa o que cada teste vai definir por conta própria.
_VARIAVEIS_DO_AMBIENTE = ("AMBIENTE", "CORS_ORIGENS", "JWT_SECRET", "APP_NOME")


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in _VARIAVEIS_DO_AMBIENTE:
        monkeypatch.delenv(nome, raising=False)


def test_valores_padrao_servem_para_desenvolvimento_local() -> None:
    settings = Settings(_env_file=None)

    assert settings.ambiente == "local"
    assert settings.cors_origens == ["http://localhost:3000"]
    assert settings.cookie_secure is False


def test_cors_origens_aceita_lista_separada_por_virgula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Formato que se digita num painel de deploy, não JSON."""
    monkeypatch.setenv(
        "CORS_ORIGENS",
        "http://localhost:3000, https://rockhub.vercel.app",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origens == [
        "http://localhost:3000",
        "https://rockhub.vercel.app",
    ]


def test_ambiente_so_aceita_valores_previstos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMBIENTE", "homologacao")

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_jwt_secret_de_exemplo_em_producao_falha_na_inicializacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMBIENTE", "producao")

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_jwt_secret_proprio_em_producao_nao_falha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("JWT_SECRET", "um-segredo-qualquer-gerado-so-para-o-teste")

    settings = Settings(_env_file=None)

    assert settings.cookie_secure is True
