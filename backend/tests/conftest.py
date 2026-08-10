"""Fixtures compartilhadas por mais de um arquivo de teste.

Banco: `rockhub_teste` é migrado pelo próprio Alembic antes da suíte, e cada
teste roda dentro de uma transação revertida ao fim, para um teste não sujar o
outro. HTTP: a `cliente` liga o `TestClient` a essa transação.

**Isoladas de propósito.** Os testes de `/saude`, erros e config não dependem
de nada daqui e continuam passando com o Postgres desligado — nada neste
arquivo conecta em escopo de import, só dentro de fixture. `create_engine` do
`app.core.db`, importado pela cadeia do `app.main`, também não abre conexão.
"""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_settings
from app.core.db import obter_sessao
from app.core.seguranca import gerar_hash
from app.main import app
from app.models.usuario import PapelUsuario, Usuario

RAIZ_BACKEND = Path(__file__).resolve().parent.parent


def _config_alembic() -> Config:
    """`Config` apontado explicitamente para `DATABASE_URL_TESTE`.

    A URL é definida em código, nunca por variável de ambiente — é o que
    impede um `uv run pytest` distraído de migrar o banco de desenvolvimento
    (ver Dev Notes da Story 1.3, "A fixture não pode migrar o banco de
    desenvolvimento").
    """
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", obter_settings().database_url_teste)
    return cfg


@pytest.fixture(scope="session")
def engine_teste() -> Generator[Engine, None, None]:
    """Migra `rockhub_teste` do zero (downgrade + upgrade) uma vez por sessão."""
    cfg = _config_alembic()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    engine = create_engine(obter_settings().database_url_teste)
    yield engine
    engine.dispose()


@pytest.fixture()
def sessao(engine_teste: Engine) -> Generator[Session, None, None]:
    """`Session` dentro de uma transação revertida ao final do teste.

    O flush do teste roda dentro de um SAVEPOINT (`begin_nested`), reaberto a
    cada vez que se encerra — inclusive por um `IntegrityError` esperado pelo
    próprio teste. Sem isso, um `flush()` que falha de propósito aborta a
    transação externa e o `rollback()` do teardown vira um `SAWarning`
    (`transaction already deassociated from connection`).
    """
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    savepoint = conexao.begin_nested()
    FabricaDeSessao = sessionmaker(bind=conexao)
    sessao = FabricaDeSessao()

    @event.listens_for(sessao, "after_transaction_end")
    def _reabrir_savepoint(sessao_evento: Session, transacao_evento: object) -> None:
        nonlocal savepoint
        if not savepoint.is_active:
            savepoint = conexao.begin_nested()

    yield sessao

    sessao.close()
    transacao.rollback()
    conexao.close()


@pytest.fixture()
def cliente(sessao: Session) -> Generator[TestClient, None, None]:
    """`TestClient` falando com o mesmo banco da fixture `sessao`.

    A ponte entre o HTTP e a transação revertida é `dependency_overrides`,
    substituindo `obter_sessao` (Dev Notes da Story 1.4). Veio do
    `test_auth.py` na Story 1.6, quando um segundo arquivo passou a precisar
    dela: é infraestrutura, não caso de teste.

    ⚠️ O `TestClient` guarda cookie entre chamadas. Um teste que faz login e
    depois quer provar o `401` precisa de outra instância ou de
    `cliente.cookies.clear()`.
    """
    app.dependency_overrides[obter_sessao] = lambda: sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def fabricar_usuario(sessao: Session) -> Callable[..., Usuario]:
    """Fábrica de conta gravada, com papel à escolha do teste.

    Existe porque os testes de autorização precisam dos três papéis. A
    `usuario_gravado` do `test_auth.py` **não** foi reescrita sobre ela: quinze
    testes de login e cadastro dependem daquele e-mail exato, e trocar a
    fixture por uma fábrica genérica mexeria em código já conferido para não
    ganhar nada.

    `flush` sem `commit`, como a `usuario_gravado`: o rollback do teardown da
    `sessao` é quem limpa.
    """

    def fabricar(papel: PapelUsuario, email: str = "alguem@exemplo.com") -> Usuario:
        usuario = Usuario(
            nome="Alguém",
            email=email,
            senha_hash=gerar_hash("rockhub"),
            papel=papel.value,
        )
        sessao.add(usuario)
        sessao.flush()
        sessao.refresh(usuario)
        return usuario

    return fabricar
