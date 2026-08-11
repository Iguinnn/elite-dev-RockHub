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

engine = create_engine(
    obter_settings().database_url,
    # Confere se a conexão ainda está viva antes de entregá-la, e descarta a
    # que morreu. Sem isto, o default é `False`: o pool guarda o socket para
    # sempre (`pool_recycle=-1`) e o Postgres da Railway pode ter reiniciado,
    # ou a rede interna derrubado a conexão ociosa, do outro lado. A primeira
    # requisição depois de um período parado pegaria essa conexão morta e
    # responderia `500` — que é exatamente o cenário de quem abre o link dias
    # depois do último deploy. O custo é um `SELECT 1` por checkout.
    pool_pre_ping=True,
    # Aposenta a conexão com mais de 30 minutos mesmo que ela pareça viva.
    # O `pre_ping` cobre a conexão que já morreu; este cobre a que vai morrer
    # num timeout de proxy no meio de uma requisição.
    pool_recycle=1800,
)

SessaoLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Generator[Session, None, None]:
    """Dependência do FastAPI: entrega uma `Session` e garante o fechamento."""
    sessao = SessaoLocal()
    try:
        yield sessao
    finally:
        sessao.close()
