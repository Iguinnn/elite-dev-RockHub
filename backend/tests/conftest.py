"""Fixtures de banco: migram `rockhub_teste` pelo próprio Alembic antes da
suíte, e cada teste roda dentro de uma transação revertida ao fim, para um
teste não sujar o outro.

**Isoladas de propósito.** Os testes de `/saude`, erros e config não dependem
de nada daqui e continuam passando com o Postgres desligado — nada neste
arquivo conecta em escopo de import, só dentro de fixture.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_settings

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
