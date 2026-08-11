"""Reexporta os modelos — é o import que `migrations/env.py` usa para o
Alembic enxergar o metadata. Sem ele, `--autogenerate` produz migração vazia.
"""

from app.models.base import Base
from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario

__all__ = ["Base", "Evento", "PapelUsuario", "Setor", "Usuario"]
