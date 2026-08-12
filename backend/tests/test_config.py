"""Configuração vem do ambiente — inclusive a lista de origens do CORS."""

import pytest

from app.core.config import Settings

# `Settings(_env_file=None)` desliga a leitura do `.env`, mas **não** as
# variáveis do processo. Quem administra a Railway do mesmo terminal costuma
# ter `AMBIENTE` ou `JWT_SECRET` exportados na shell — e aí estes testes
# falhariam por causa do ambiente de quem roda, não do código. Esta fixture
# limpa o que cada teste vai definir por conta própria.
_VARIAVEIS_DO_AMBIENTE = (
    "AMBIENTE",
    "CORS_ORIGENS",
    "JWT_SECRET",
    "APP_NOME",
    "TICKETMASTER_API_KEY",
    # ⚠️ **Faltava aqui, e a ausência tornava um teste dependente do shell**
    # (code review da Epic 3). O `_env_file=None` desliga o `.env`, não o
    # `os.environ`: quem tivesse `TICKET_SIGNING_SECRET` exportada — ou um CI que
    # a injetasse como variável em vez de arquivo — fazia o `Settings` nascer com
    # segredo próprio, o `ValueError` não acontecer, e o teste que afirma
    # "segredo de exemplo em produção falha" quebrar por motivo alheio ao que ele
    # testa. O comentário `# fica no valor de exemplo de propósito` descrevia uma
    # condição que nada estabelecia.
    "TICKET_SIGNING_SECRET",
)


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
    # Desde a Story 2.1 a chave da Ticketmaster também é obrigatória em
    # produção — sem esta linha, este teste quebraria por um motivo que não é
    # o que ele existe para provar (ver os dois testes logo abaixo).
    monkeypatch.setenv("TICKETMASTER_API_KEY", "chave-de-teste-nao-vaze-isto")
    # E desde a Story 3.9 o segredo do ingresso, pelo mesmo motivo.
    monkeypatch.setenv("TICKET_SIGNING_SECRET", "segredo-de-ingresso-para-o-teste")

    settings = Settings(_env_file=None)

    assert settings.cookie_secure is True


def test_segredo_de_ingresso_de_exemplo_em_producao_falha_na_inicializacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A falha mais cara das três, e por isso com validador e mensagem próprios.

    Com o valor de exemplo em produção, qualquer pessoa que leia o repositório
    forja ingresso válido — o AD-5 inteiro depende de o segredo ser segredo.
    """
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("JWT_SECRET", "um-segredo-qualquer-gerado-so-para-o-teste")
    monkeypatch.setenv("TICKETMASTER_API_KEY", "chave-de-teste-nao-vaze-isto")
    # TICKET_SIGNING_SECRET fica no valor de exemplo de propósito.

    with pytest.raises(ValueError, match="TICKET_SIGNING_SECRET"):
        Settings(_env_file=None)


def test_chave_da_ticketmaster_ausente_em_producao_falha_na_inicializacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("JWT_SECRET", "um-segredo-qualquer-gerado-so-para-o-teste")
    # ⚠️ **Preenchido para este teste falhar pelo motivo certo.** O validador do
    # segredo de ingresso (Story 3.9) roda antes deste, e sem esta linha o
    # `pytest.raises` passaria a ser satisfeito pela mensagem errada — teste
    # verde provando outra coisa. É a mesma armadilha que a Story 2.1 abriu ao
    # acrescentar o segundo validador, e o `match` abaixo é o que a fecha.
    monkeypatch.setenv("TICKET_SIGNING_SECRET", "segredo-de-ingresso-para-o-teste")

    with pytest.raises(ValueError, match="TICKETMASTER_API_KEY"):
        Settings(_env_file=None)


def test_chave_da_ticketmaster_ausente_em_local_nao_falha() -> None:
    """Quem clona o repositório para avaliar não precisa de conta no portal da
    Ticketmaster (NFR1) — a busca responde `CATALOGO_INDISPONIVEL` em vez de
    impedir a aplicação de subir.
    """
    settings = Settings(_env_file=None)

    assert settings.ambiente == "local"
    assert settings.ticketmaster_api_key == ""


@pytest.mark.parametrize(
    ("variavel", "trecho_da_mensagem"),
    [
        ("TICKET_SIGNING_SECRET", "TICKET_SIGNING_SECRET"),
        ("JWT_SECRET", "JWT_SECRET"),
    ],
)
@pytest.mark.parametrize("valor", ["", "   ", "curto-demais"])
def test_segredo_vazio_ou_curto_em_producao_falha_na_inicializacao(
    monkeypatch: pytest.MonkeyPatch,
    variavel: str,
    trecho_da_mensagem: str,
    valor: str,
) -> None:
    """⚠️ **O campo apagado no painel era o buraco** (code review da Epic 3).

    Os dois validadores comparavam por igualdade contra a string de exemplo, e
    string vazia não é a string de exemplo — então `TICKET_SIGNING_SECRET=` num
    painel de deploy subia a aplicação e passava a assinar ingresso com
    `hmac.new(b"", ...)`. Chave conhecida por definição, ingresso forjável por
    qualquer um, e o aviso "conferir que não é o valor de exemplo" não pegava
    porque a variável *está* definida.

    Os três valores cobrem as três formas de o segredo não servir: vazio, só
    espaço, e curto demais para ser gerado por `token_urlsafe`.
    """
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("TICKETMASTER_API_KEY", "chave-de-teste-nao-vaze-isto")
    # A outra das duas fica válida, para o erro apontar a que está sendo testada.
    for nome in ("JWT_SECRET", "TICKET_SIGNING_SECRET"):
        monkeypatch.setenv(nome, "um-segredo-longo-o-bastante-para-passar")
    monkeypatch.setenv(variavel, valor)

    with pytest.raises(ValueError, match=trecho_da_mensagem):
        Settings(_env_file=None)
