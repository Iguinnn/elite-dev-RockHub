"""Configuração da aplicação, lida exclusivamente de variáveis de ambiente.

Segredo nenhum mora no repositório: o que é versionado é o `.env.example`, com as
chaves e valores de exemplo. O `.env` real fica fora do controle de versão.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração do backend.

    Cada campo vira uma variável de ambiente de mesmo nome, em maiúsculas
    (`APP_NOME`, `AMBIENTE`, `CORS_ORIGENS`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_nome: str = "RockHub API"
    ambiente: Literal["local", "producao"] = "local"

    # `NoDecode` desliga a interpretação como JSON que o pydantic-settings faz por
    # padrão em campos de lista. Assim a variável de ambiente aceita a forma que
    # de fato se digita num painel de deploy: origens separadas por vírgula.
    cors_origens: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://rockhub:rockhub@localhost:5432/rockhub"
    database_url_teste: str = "postgresql+psycopg://rockhub:rockhub@localhost:5432/rockhub_teste"

    @field_validator("cors_origens", mode="before")
    @classmethod
    def _separar_por_virgula(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor

    @field_validator("database_url", "database_url_teste", mode="before")
    @classmethod
    def _normalizar_esquema_postgres(cls, valor: object) -> object:
        """Troca `postgres://`/`postgresql://` por `postgresql+psycopg://`.

        A Railway injeta `DATABASE_URL` num dos dois primeiros esquemas, que o
        SQLAlchemy resolve para o driver psycopg2 — não instalado aqui. Sem esta
        normalização, o erro na Story 1.8 seria um `ModuleNotFoundError` que não
        aponta para a URL como causa.
        """
        if isinstance(valor, str):
            if valor.startswith("postgresql+psycopg://"):
                return valor
            if valor.startswith("postgresql://"):
                return valor.replace("postgresql://", "postgresql+psycopg://", 1)
            if valor.startswith("postgres://"):
                return valor.replace("postgres://", "postgresql+psycopg://", 1)
        return valor


@lru_cache
def obter_settings() -> Settings:
    """Instância única de `Settings`, pronta para virar dependência do FastAPI.

    O cache existe para não reler o ambiente a cada requisição e para que os
    testes possam substituir a configuração por `dependency_overrides`.
    """
    return Settings()
