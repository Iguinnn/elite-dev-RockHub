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

    @field_validator("cors_origens", mode="before")
    @classmethod
    def _separar_por_virgula(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_settings() -> Settings:
    """Instância única de `Settings`, pronta para virar dependência do FastAPI.

    O cache existe para não reler o ambiente a cada requisição e para que os
    testes possam substituir a configuração por `dependency_overrides`.
    """
    return Settings()
