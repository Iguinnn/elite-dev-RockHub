"""habilita extensao unaccent

Revision ID: 06c1ad5ac276
Revises: c7cb4a29b7f3
Create Date: 2026-08-11 20:15:57.908468

**A primeira migração deste projeto que não cria tabela**, e vale dizer por quê.
As três anteriores criam `usuario`, `evento`/`setor` e `evento_portaria`; esta
não acrescenta nem coluna nem índice — ela liga a extensão `unaccent` do
Postgres, que é o que faz `?q=sao paulo` achar `São Paulo` na programação
pública (Story 3.2).

Ela mora aqui, e não num passo de infraestrutura, porque **a extensão é
pré-requisito da consulta**: sem ela, `func.unaccent(...)` em
`services/evento.py::listar_programacao` estoura com `function unaccent(text)
does not exist`, e a raiz do produto vira `500`. Pré-requisito de consulta se
declara no mesmo lugar onde o schema é declarado — assim ele viaja com o código
que depende dele, roda sozinho no `Pre-deploy Command` da Railway e é aplicado
no `rockhub_teste` pelo `downgrade base` + `upgrade head` do `conftest.py`.

**A alternativa foi descartada pelo Igor:** um `translate()` com mapa de letras
escrito à mão na própria consulta resolveria a mesma tela sem tocar o banco —
e é um mapa de trinta caracteres que ninguém revisa de novo, que esquece `ü` e
`ñ` em silêncio, e cujo defeito aparece como "a busca não acha", não como erro.

⚠️ `unaccent()` **não é `IMMUTABLE`**, então ela não entra em índice sem uma
função wrapper. Com o volume deste projeto não existe índice para criar — se
alguém tentar, o Postgres recusa, e o motivo é este.

⚠️ `CREATE EXTENSION` exige superusuário ou o papel `rds_superuser`/equivalente.
Num Postgres gerenciado que recuse, **o deploy inteiro falha** aqui, não só a
busca — o `Pre-deploy Command` roda `alembic upgrade head` antes de subir a API.
**Conferido na Railway em 2026-08-11**, antes do merge da Epic 3: lá o usuário
da conexão é `postgres` com `usesuper = true`, a extensão está disponível na
versão 1.1, e ela já foi criada à mão pelo painel — então aqui ela é no-op.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '06c1ad5ac276'
down_revision: Union[str, Sequence[str], None] = 'c7cb4a29b7f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Escrita à mão (`alembic revision`, sem `--autogenerate`): não há mudança
    # de modelo para detectar, e o autogenerate produziria um arquivo vazio.
    #
    # `IF NOT EXISTS` porque a extensão é do banco, não do schema da aplicação:
    # ela pode já estar ligada por outro motivo, e nesse caso não há nada a
    # fazer — não é um erro.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    """Downgrade schema."""
    # `IF EXISTS` pelo mesmo motivo simétrico: o `downgrade base` do
    # `conftest.py` roda a cada sessão de teste, e ele não pode falhar num banco
    # onde a extensão nunca chegou a existir.
    op.execute("DROP EXTENSION IF EXISTS unaccent")
