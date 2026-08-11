"""Base declarativa comum a todos os modelos.

A convenção de nomes é o que torna `CheckConstraint`, `UniqueConstraint` e
chave estrangeira determinísticas entre migração e banco. Sem ela, o Postgres
batiza cada constraint sozinho, e o `downgrade()` do Alembic tenta derrubar um
nome que pode não existir naquele banco — o tipo de coisa que só aparece no
dia do deploy.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

CONVENCAO_DE_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)
