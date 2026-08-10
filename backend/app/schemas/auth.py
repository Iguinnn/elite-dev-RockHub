"""Schemas de entrada e saída da autenticação.

`UsuarioSaida` nasce aqui porque `POST /auth/login` é o primeiro endpoint a
devolvê-lo — `POST /auth/cadastro` devolve o mesmo, e a Story 1.6 reaproveita
em `GET /auth/eu`. Três rotas, um schema.
"""

import re
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.models.usuario import PapelUsuario

# Uma arroba, algo antes, algo depois, um ponto no que vem depois, espaço em
# lugar nenhum. **Não é RFC 5322 e não pretende ser**: a RFC aceita aspas,
# comentários e domínios literais em IP, e escrever isso à mão é a receita
# clássica de recusar o e-mail de alguém real. Esta regra existe para pegar o
# erro de digitação óbvio — `igor`, `igor@`, `igor@exemplo` —, e a decisão de
# não instalar `email-validator` por causa disso está no README da raiz.
_FORMATO_DE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar_email(valor: object) -> object:
    return valor.strip().lower() if isinstance(valor, str) else valor


def _limpar_texto(valor: object) -> object:
    return valor.strip() if isinstance(valor, str) else valor


# A convenção de e-mail em minúsculas nasceu na Story 1.3, no banco. Aqui ela
# vira um tipo só, usado pelos dois schemas: se o login normalizasse de um
# jeito e o cadastro de outro, a conta gravada por uma rota não seria
# encontrada pela outra.
EmailNormalizado = Annotated[str, BeforeValidator(_normalizar_email)]

# `Field(min_length=1)` sozinho não segura `"   "` — três espaços são três
# caracteres válidos. O `.strip()` antes é o que faz o mínimo significar algo.
NomeLimpo = Annotated[str, BeforeValidator(_limpar_texto)]


class LoginEntrada(BaseModel):
    email: EmailNormalizado
    senha: str


class CadastroEntrada(BaseModel):
    # Sem `extra="forbid"` de propósito. Parece a escolha rigorosa e quebraria
    # a garantia do papel: `{"papel": "ORGANIZADOR"}` no corpo passaria a
    # responder `422` em vez de criar uma conta CLIENTE. Campo desconhecido
    # **ignorado** é a garantia mais forte que existe — ele não tem como
    # influenciar nada.
    nome: NomeLimpo = Field(min_length=1, max_length=120)
    email: EmailNormalizado = Field(max_length=255)
    # `max_length=128` não é enfeite: Argon2id não tem o limite de 72 bytes do
    # bcrypt, e uma senha de 10 MB seria hasheada inteira, com 64 MB de
    # memória, por requisição.
    senha: str = Field(min_length=6, max_length=128)

    # Só o cadastro confere o formato. `LoginEntrada` continua sem isso, e é
    # decisão da Story 1.4: um `422` de formato antes do `401` de credencial
    # recriaria a distinção entre "e-mail não existe" e "senha errada" que
    # aquela story existe para eliminar.
    @field_validator("email")
    @classmethod
    def _conferir_formato_do_email(cls, valor: str) -> str:
        if not _FORMATO_DE_EMAIL.match(valor):
            raise ValueError("e-mail inválido")
        return valor


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    email: str
    papel: PapelUsuario
