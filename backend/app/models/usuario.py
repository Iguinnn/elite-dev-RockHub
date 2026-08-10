"""Modelo `Usuario` e o enum de papel — único enum de papel do projeto.

A dependência de papel da Story 1.6 e os schemas Pydantic das Stories 1.4/1.5
importam `PapelUsuario` daqui. Não redeclare o enum em outro lugar.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PapelUsuario(str, Enum):
    ORGANIZADOR = "ORGANIZADOR"
    CLIENTE = "CLIENTE"
    PORTARIA = "PORTARIA"


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "papel IN ('ORGANIZADOR', 'CLIENTE', 'PORTARIA')",
            name="papel_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Só a coluna: nada é hasheado nesta story — Argon2id entra na 1.4.
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
