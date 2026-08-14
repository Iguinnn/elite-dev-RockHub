"""acrescenta data_hora_fim ao evento

Revision ID: a1c9f4d3b7e2
Revises: e5bf44a9f826
Create Date: 2026-08-14 10:12:44.108927

A décima migração do projeto, e a primeira desde que as epics fecharam. Uma
coluna só: a hora em que o show acaba (techspec `docs/techspec-fim-do-evento.md`,
commit 1).

**O defeito que ela conserta.** Até aqui o `Evento` tinha `data_hora` e mais nada
sobre tempo — o sistema não sabia quando um show termina. A consequência era
visível em produção: ingresso não utilizado ficava marcado *Ativo* na conta do
cliente dias depois do show, e o turno continuava na lista da portaria, clicável
e validável. O comentário do `ABERTURA_DOS_PORTOES` já dizia isso com todas as
letras: *"não há fechamento, de propósito (…) sem contar que este projeto não tem
coluna de duração nenhuma."*

⚠️ **O `upgrade` roda em três passos, e não em um.** `add_column` com
`nullable=False` direto estoura em qualquer banco que já tenha linha de evento —
e todos têm, inclusive o da Railway que serve o roteiro de avaliação. Cria-se
anulável, preenche-se, e só então se aplica o `NOT NULL`.

**O preenchimento retroativo é `data_hora + 6 horas`, e as seis são folga
deliberada.** É ele que faz o defeito sumir **também nos eventos que já
existem** — uma correção que só valesse para os novos seria invariante pela
metade. Com três horas, um evento antigo do banco poderia aparecer já encerrado
no meio de um teste, e o comportamento novo seria descoberto pelo susto.

O `CHECK fim_depois_do_inicio` entra depois do preenchimento, pelo motivo óbvio:
antes dele a coluna está cheia de `NULL`. Ele é rede de segurança, e não a regra
— quem recusa em português é o `FIM_ANTES_DO_INICIO` do `services/evento.py`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f4d3b7e2'
down_revision: Union[str, Sequence[str], None] = 'e5bf44a9f826'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Passo 1 — anulável, porque as linhas que já existem não têm valor.
    op.add_column(
        "evento",
        sa.Column("data_hora_fim", sa.DateTime(timezone=True), nullable=True),
    )

    # Passo 2 — o término dos eventos antigos. `interval` do Postgres, e não um
    # `timedelta` calculado em Python: são as linhas do banco que se preenchem,
    # e um laço lendo e reescrevendo cada uma faria em N idas o que o servidor
    # faz numa.
    op.execute(
        "UPDATE evento SET data_hora_fim = data_hora + interval '6 hours' "
        "WHERE data_hora_fim IS NULL"
    )

    # Passo 3 — a invariante, agora que toda linha tem valor.
    op.alter_column("evento", "data_hora_fim", nullable=False)

    op.create_check_constraint(
        "fim_depois_do_inicio", "evento", "data_hora_fim > data_hora"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fim_depois_do_inicio", "evento", type_="check")
    op.drop_column("evento", "data_hora_fim")
