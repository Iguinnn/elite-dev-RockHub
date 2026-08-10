"""Schemas de entrada e saída da autenticação.

`UsuarioSaida` nasce aqui porque `POST /auth/login` é o primeiro endpoint a
devolvê-lo — a Story 1.6 reaproveita o mesmo schema em `GET /auth/eu`.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.usuario import PapelUsuario


class LoginEntrada(BaseModel):
    email: str
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip().lower()
        return valor


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    email: str
    papel: PapelUsuario
