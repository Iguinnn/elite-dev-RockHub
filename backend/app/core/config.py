"""Configuração da aplicação, lida exclusivamente de variáveis de ambiente.

Segredo nenhum mora no repositório: o que é versionado é o `.env.example`, com as
chaves e valores de exemplo. O `.env` real fica fora do controle de versão.
"""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_JWT_SECRET_EXEMPLO = "troque-este-valor-em-producao"
_TICKET_SECRET_EXEMPLO = "troque-este-valor-em-producao-tambem"

# `token_urlsafe(48)` devolve 64 caracteres; 32 é folga confortável abaixo disso
# e ainda muito acima de qualquer coisa digitada à mão num painel.
_TAMANHO_MINIMO_DE_SEGREDO = 32

_SEGREDOS_DE_EXEMPLO = frozenset({_JWT_SECRET_EXEMPLO, _TICKET_SECRET_EXEMPLO})


def _segredo_forte(valor: str) -> bool:
    """Um segredo serve em produção se não é de exemplo, não é vazio e é longo.

    ⚠️ **Os três casos juntos, e não só o de exemplo** (code review da Epic 3).
    Os dois validadores abaixo comparavam por igualdade contra a string de
    exemplo, o que deixava passar o caso mais fácil de acontecer num painel de
    deploy: o campo **apagado**. `TICKET_SIGNING_SECRET=` vira `""`, que não é o
    valor de exemplo, então a aplicação subia e passava a assinar ingresso com
    `hmac.new(b"", ...)` — chave conhecida por definição, e ingresso forjável por
    qualquer um. O aviso escrito no CLAUDE.md ("conferir que não é o valor de
    exemplo") também não pegava esse caso, porque a variável *está* definida.

    O validador da `TICKETMASTER_API_KEY`, no mesmo arquivo, já fazia o certo com
    `not ...strip()`. A assimetria era o defeito.
    """
    limpo = valor.strip()
    return (
        limpo not in _SEGREDOS_DE_EXEMPLO and len(limpo) >= _TAMANHO_MINIMO_DE_SEGREDO
    )


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

    jwt_secret: str = _JWT_SECRET_EXEMPLO
    cookie_sessao_nome: str = "rockhub_sessao"

    # ⚠️ **Segredo próprio, e não o `jwt_secret` reaproveitado** (decisão do
    # Igor). Segredo com dois usos é o que impede girar um sem derrubar o outro:
    # trocar a chave de sessão passaria a invalidar **todo ingresso já
    # emitido**, porque a assinatura do AD-5 sai dela. São dois ciclos de vida
    # diferentes — sessão dura 8 horas, ingresso dura até o show — e eles não
    # cabem na mesma chave.
    ticket_signing_secret: str = _TICKET_SECRET_EXEMPLO

    # Padrão `""`, não um valor de exemplo como o `JWT_SECRET`: não existe chave
    # de exemplo que a Ticketmaster aceite, então "ausente" e "de exemplo" são a
    # mesma situação aqui — o validador abaixo trata só a ausência.
    ticketmaster_api_key: str = ""

    @property
    def cookie_secure(self) -> bool:
        """`Secure` só em produção — `localhost` roda em HTTP (ver Dev Notes da Story 1.4).

        Não é campo configurável de propósito: ninguém desliga em produção por
        engano num painel de deploy.
        """
        return self.ambiente == "producao"

    @model_validator(mode="after")
    def _recusar_segredo_de_exemplo_em_producao(self) -> Self:
        if self.ambiente == "producao" and not _segredo_forte(self.jwt_secret):
            raise ValueError(
                "JWT_SECRET ausente, fraco ou ainda no valor de exemplo em produção. "
                f"Ele precisa ter ao menos {_TAMANHO_MINIMO_DE_SEGREDO} caracteres. "
                "Gere um novo com: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self

    @model_validator(mode="after")
    def _recusar_segredo_de_ingresso_de_exemplo_em_producao(self) -> Self:
        """Motivo separado do validador do `JWT_SECRET`, como o da Ticketmaster.

        Uma mensagem só faria quem depura procurar a chave errada — e esta falha
        é a mais cara das três: com o segredo de exemplo em produção, qualquer
        pessoa que leia o repositório forja ingresso válido.
        """
        if self.ambiente == "producao" and not _segredo_forte(
            self.ticket_signing_secret
        ):
            raise ValueError(
                "TICKET_SIGNING_SECRET ausente, fraca ou ainda no valor de exemplo "
                "em produção — com qualquer um dos três, alguém forja ingresso. Ela "
                f"precisa ter ao menos {_TAMANHO_MINIMO_DE_SEGREDO} caracteres. "
                "Gere uma nova com: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self

    @model_validator(mode="after")
    def _recusar_chave_da_ticketmaster_ausente_em_producao(self) -> Self:
        """Motivo separado do validador do `JWT_SECRET` de propósito.

        São duas causas diferentes de "não sobe em produção" — segredo de
        exemplo esquecido versus variável nunca definida — e uma mensagem só
        faria quem depura procurar a causa errada. Em `local` a chave pode
        faltar: quem clona o repositório para avaliar não precisa de conta no
        portal da Ticketmaster (NFR1); a busca responde `CATALOGO_INDISPONIVEL`.
        """
        if self.ambiente == "producao" and not self.ticketmaster_api_key.strip():
            raise ValueError(
                "TICKETMASTER_API_KEY ausente em produção. Defina a variável no "
                "painel da Railway com a chave do portal da Ticketmaster."
            )
        return self

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
