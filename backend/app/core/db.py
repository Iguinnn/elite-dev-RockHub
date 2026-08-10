"""Engine e sessão do SQLAlchemy.

`create_engine` não abre conexão — só a abre o primeiro uso. Por isso ele pode
viver aqui, em tempo de import, sem exigir Postgres no ar para a aplicação
subir (os testes de `/saude` continuam passando com o banco desligado).

A dependência `obter_sessao()` só entrega e fecha a sessão. Quem abre
transação e decide `commit`/`rollback` é o service — nunca o router, nunca esta
dependência (`ARCHITECTURE-SPINE.md#Convenções`).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_settings

engine = create_engine(obter_settings().database_url)

SessaoLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Generator[Session, None, None]:
    """Dependência do FastAPI: entrega uma `Session` e garante o fechamento."""
    sessao = SessaoLocal()
    try:
        yield sessao
    finally:
        sessao.close()
