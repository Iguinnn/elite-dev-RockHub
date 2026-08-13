"""encolhe o codigo do ingresso e renomeia titular_nome

Revision ID: 97672aee94c4
Revises: ed0bb0dad2a3
Create Date: 2026-08-12 21:56:18.203554

A nona migração do projeto, e a primeira que **migra dados** em vez de só mexer
no schema. Ela é consequência de uma decisão de produto, não de uma story
(techspec `docs/techspec-codigo-curto.md`): o código de 80 caracteres tornava
inutilizável o campo manual da portaria — o fallback de quando a câmera falha —,
e um fallback que ninguém consegue usar na fila é um fallback que não existe.

**Nenhum ingresso emitido é invalidado, e é por isso que existem as dez linhas
de `_preencher_codigos`.** O código novo é derivável das colunas que já estão na
tabela (`id`, `evento_id`, `nonce`), então a migração o **calcula** linha por
linha. **Descartei** apagar os ingressos existentes — o Igor disse que não
haveria problema, mas essas dez linhas evitam a frase "invalidei ingressos" no
README, e o mesmo código serve de prova de que a derivação funciona.

⚠️ **Ela precisa do `TICKET_SIGNING_SECRET`, e falhar sem ele é o comportamento
certo** — o app já se recusa a subir sem ele (`app/core/config.py`). Na Railway
isso significa que o deploy roda a migração com o segredo de produção; girar o
segredo **depois** dela invalida os códigos calculados aqui, como girar sempre
invalidou.

⚠️ **O `upgrade` importa `gerar_codigo` do app; o `downgrade` carrega a fórmula
antiga escrita à mão.** Não é inconsistência: a derivação nova tem de ser a
**mesma** que a validação da porta recalcula — duplicá-la aqui seria plantar duas
fontes da verdade para o valor que decide entrada de gente. A fórmula de base64
da revisão anterior, ao contrário, deixou de existir no código quando
`assinar_ingresso` saiu, e o único lugar que ainda precisa dela é este
`downgrade`.

⚠️ **`titular_nome` → `pagador_nome` é renomear, não recriar.** `ALTER ... RENAME
COLUMN` preserva o conteúdo: o nome digitado no checkout continua gravado, e o
que mudou é o que ele significa. O `titular_nome` das respostas passa a vir de
`usuario.nome`, pelo join com `reserva` — o ingresso é da conta, e o cartão pode
ser de outra pessoa.
"""
import base64
import hashlib
import hmac
from collections.abc import Callable
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa

from app.core.config import obter_settings
from app.core.seguranca import gerar_codigo


# revision identifiers, used by Alembic.
revision: str = '97672aee94c4'
down_revision: Union[str, Sequence[str], None] = 'ed0bb0dad2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LER_INGRESSOS = sa.text("SELECT id, evento_id, nonce FROM ingresso")


def _assinatura_antiga(ingresso_id: UUID, evento_id: UUID, nonce: str) -> str:
    """`HMAC-SHA256` em base64url sem padding — a fórmula da revisão anterior.

    Escrita aqui porque **saiu do código do app** junto com `assinar_ingresso`, e
    o `downgrade` é o único lugar que ainda a precisa: voltar para a
    `ed0bb0dad2a3` significa devolver a coluna `assinatura` com valores que o
    app daquela revisão saberia conferir.
    """
    mensagem = f"{ingresso_id}{evento_id}{nonce}".encode()
    bruto = hmac.new(
        obter_settings().ticket_signing_secret.encode(),
        mensagem,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(bruto).decode().rstrip("=")


def _preencher(coluna: str, calcular: Callable[[UUID, UUID, str], str]) -> None:
    """Recalcula `coluna` para toda linha de `ingresso`, uma UPDATE por linha.

    Sem `executemany` e sem CTE de propósito: o cálculo é HMAC em Python, então
    as linhas têm de subir para cá de todo jeito, e o volume desta tabela é o de
    um desafio de sete dias. Clareza vale mais que a viagem economizada.
    """
    conexao = op.get_bind()
    linhas = conexao.execute(_LER_INGRESSOS).all()

    atualizar = sa.text(f"UPDATE ingresso SET {coluna} = :valor WHERE id = :id")
    for ingresso_id, evento_id, nonce in linhas:
        conexao.execute(
            atualizar,
            {"valor": calcular(ingresso_id, evento_id, nonce), "id": ingresso_id},
        )


def upgrade() -> None:
    """Upgrade schema."""
    # Nasce anulável porque a linha antiga não tem valor nenhum ainda. O `SET NOT
    # NULL` vem depois do preenchimento, três passos abaixo — é essa ordem que
    # deixa a migração rodar contra uma tabela cheia.
    op.add_column('ingresso', sa.Column('codigo', sa.String(length=8), nullable=True))
    # Único **antes** do preenchimento: se dois códigos calculados colidissem, a
    # migração falha aqui em vez de deixar a tabela com duas linhas respondendo à
    # mesma leitura de QR. Com 40 bits e o punhado de ingressos que este banco
    # tem, a chance é da ordem de 10⁻¹⁰ — e o desfecho de ignorá-la seria pior
    # que o de uma migração recusada.
    op.create_index(op.f('ix_ingresso_codigo'), 'ingresso', ['codigo'], unique=True)

    _preencher('codigo', gerar_codigo)

    op.alter_column('ingresso', 'codigo', nullable=False)

    # Sai depois de o `codigo` já estar gravado: até esta linha, a coluna antiga
    # ainda é a fonte do QR, e uma migração interrompida no meio deixa o banco
    # com as duas em vez de com nenhuma.
    op.drop_column('ingresso', 'assinatura')

    op.alter_column('ingresso', 'titular_nome', new_column_name='pagador_nome')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('ingresso', 'pagador_nome', new_column_name='titular_nome')

    op.add_column('ingresso', sa.Column('assinatura', sa.String(length=64), nullable=True))
    _preencher('assinatura', _assinatura_antiga)
    op.alter_column('ingresso', 'assinatura', nullable=False)

    op.drop_index(op.f('ix_ingresso_codigo'), table_name='ingresso')
    op.drop_column('ingresso', 'codigo')
