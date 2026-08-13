"""Reexporta os modelos — é o import que `migrations/env.py` usa para o
Alembic enxergar o metadata. Sem ele, `--autogenerate` produz migração vazia.
"""

from app.models.base import Base
from app.models.evento import Evento, Setor, evento_portaria
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.models.validacao import Validacao, Veredito

__all__ = [
    "Base",
    "EstadoReserva",
    "Evento",
    "Ingresso",
    "ItemReserva",
    "PapelUsuario",
    "Reserva",
    "Setor",
    "Usuario",
    "Validacao",
    "Veredito",
    "evento_portaria",
]
