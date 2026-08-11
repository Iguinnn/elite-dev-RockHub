"""Schemas de entrada e saída da publicação de eventos.

**O que este schema recusa, e por quê.** Ele é a primeira barreira da primeira
rota de escrita do domínio, e três recusas moram aqui de propósito:

- **`origem_externa_id` é obrigatório.** É onde a regra de produto "todo evento
  nasce de uma atração do catálogo" passa a valer. A coluna do banco continua
  anulável (decisão da Story 2.3): o motivo é que a regra é de produto, e
  produto muda mais rápido que schema de banco — travá-la numa migração
  custaria outra migração para afrouxá-la.
- **`data_hora` precisa de fuso.** AD-11 pede ISO-8601 com offset. Um horário
  sem fuso é um horário sem significado: "21:00" é 21h de onde?
- **Toda string passa por `.strip()` antes do `min_length`.** `Field(min_length=1)`
  sozinho aceita `"   "` — três espaços são três caracteres válidos.

E uma coisa que ele **não** recusa, também de propósito: `setores` vazio. A
lista chega aqui sem `min_length`, porque "um evento precisa de ao menos um
setor" é regra de negócio e mora no service (`app/services/evento.py`), que
responde `EVENTO_SEM_SETOR`. Com `min_length=1`, o Pydantic responderia
`DADOS_INVALIDOS` — um código genérico para uma regra específica, e a tela não
teria como dizer o que faltou.

**`portaria_ids` chega pela mesma porta, e pelo mesmo motivo** (Story 2.5). Ele
também não tem `min_length`, também é `default_factory=list`, e a recusa
também é do service — `EVENTO_SEM_PORTARIA`. Aqui o argumento é ainda mais
forte: "publicar exige ao menos um usuário de portaria escalado" é o **AD-7**,
uma invariante da arquitetura. Invariante de arquitetura não mora num
`Field(...)`, mora no service, onde dá para lê-la em português e testá-la pelo
código do erro. São quatro recusas nesta rota agora, e a ordem delas está
escrita em `app/services/evento.py`.

**Sem `extra="forbid"`**, pelo mesmo motivo escrito no `CadastroEntrada` da
Story 1.4: campo desconhecido **ignorado** é garantia mais forte que campo
desconhecido recusado. `organizador_id`, `vendidos`, `id` e `publicado_em` não
existem para este schema, então não há caminho pelo qual o corpo da requisição
os influencie — nem para gravar, nem para provocar um `422` que diga que eles
existem.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


# Copiado de `schemas/auth.py`, não importado: lá ele é `_limpar_texto`, com o
# `_` que o declara privado do módulo. Duas linhas duplicadas custam menos que
# um import de nome privado entre schemas. No **terceiro** consumidor ele vira
# `schemas/_comum.py` — mesma convenção de `Campo` e `Botao` no frontend,
# registrada no README da raiz.
def _limpar_texto(valor: object) -> object:
    return valor.strip() if isinstance(valor, str) else valor


def _limpar_opcional(valor: object) -> object:
    """Como `_limpar_texto`, mas `""` vira `None`.

    `cidade` e `imagem_url` são anuláveis no banco. Sem isto, um campo que o
    organizador deixou em branco gravaria string vazia, e a coluna passaria a
    ter dois jeitos de dizer "não tem" — `NULL` e `""`. Toda leitura futura
    teria que conferir os dois.
    """
    if isinstance(valor, str):
        limpo = valor.strip()
        return limpo or None
    return valor


TextoLimpo = Annotated[str, BeforeValidator(_limpar_texto)]
TextoLimpoOpcional = Annotated[str | None, BeforeValidator(_limpar_opcional)]


class SetorEntrada(BaseModel):
    nome: TextoLimpo = Field(min_length=1, max_length=80)
    # `ge=1` e não `ge=0`: o `CHECK capacidade_positiva` da Story 2.3 diz
    # `> 0`, e o schema recusa antes de o banco precisar defender. Setor com
    # capacidade zero nasce esgotado e ninguém entende por que não dá comprar.
    capacidade: int = Field(ge=1)
    # Inteiro, nunca `float` (AD-11): dinheiro em ponto flutuante é erro de
    # arredondamento esperando acontecer. A conversão de reais para centavos
    # acontece no cliente, antes do envio.
    preco_centavos: int = Field(ge=0)


class EventoEntrada(BaseModel):
    origem_externa_id: TextoLimpo = Field(min_length=1, max_length=64)
    # Os três campos copiados do catálogo (AD-1). O tamanho é o da coluna: o
    # schema recusa antes de o Postgres truncar ou estourar.
    nome: TextoLimpo = Field(min_length=1, max_length=200)
    imagem_url: TextoLimpoOpcional = Field(default=None, max_length=500)
    data_hora: datetime
    # Preenchidos pelo organizador, sugeridos pelo catálogo: a mesma atração
    # vira várias datas em casas diferentes, e quem sabe onde o show dele
    # acontece é ele, não a Ticketmaster.
    local: TextoLimpo = Field(min_length=1, max_length=200)
    cidade: TextoLimpoOpcional = Field(default=None, max_length=120)
    # `default_factory=list` para que a **ausência** do campo caia na mesma
    # regra do service que a lista vazia — as duas são "publicar sem setor", e
    # merecem o mesmo `EVENTO_SEM_SETOR`. Sem o default, o campo ausente viraria
    # "field required" do Pydantic, ou seja, `DADOS_INVALIDOS`.
    #
    # `max_length=20` é teto de proteção, não regra de produto: sem ele, um
    # corpo com 10.000 setores é uma transação com 10.000 `INSERT`.
    setores: list[SetorEntrada] = Field(default_factory=list, max_length=20)
    # Quem vai validar ingresso na porta deste evento (AD-7). Mesmo
    # `default_factory=list` e mesmo teto dos setores, pelos mesmos dois
    # motivos: ausência e lista vazia são a mesma intenção, e devem receber o
    # mesmo `EVENTO_SEM_PORTARIA`; e vinte é proteção contra corpo absurdo, não
    # regra de produto.
    #
    # `list[UUID]` e não `list[str]`: id em formato inválido é erro de
    # estrutura, e estrutura é do Pydantic — vira `DADOS_INVALIDOS` antes de
    # chegar ao banco. O que o service decide é outra coisa: se o id **resolve**
    # para uma conta de portaria.
    portaria_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @field_validator("data_hora")
    @classmethod
    def _exigir_fuso(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            raise ValueError(
                "informe a data com fuso horário (ISO-8601 com offset, ex.: "
                "2026-08-15T00:00:00Z)"
            )
        return valor


class SetorSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    capacidade: int
    # `vendidos` **entra** na saída: é o inventário do organizador (UX-DR7), que
    # vê números exatos e não proporção. Recém-publicado ele é sempre zero, e é
    # lendo esse zero que o teste prova que o corpo da requisição não tem como
    # semear estoque (AD-13).
    vendidos: int
    preco_centavos: int


class PortariaSaida(BaseModel):
    """Uma conta de portaria como o organizador a vê: para escalar e conferir.

    **Não é o `UsuarioSaida` do `schemas/auth.py`, de propósito.** A forma é
    quase a mesma hoje — falta só o `papel`, que aqui seria sempre
    `"PORTARIA"`, ou seja, ruído. O significado é que não é o mesmo: um diz
    "quem está logado", este diz "quem pode ser escalado". Reusar acoplaria o
    contrato de evento ao de autenticação, e o dia em que um dos dois ganhasse
    um campo seria o dia de descobrir isso pela tela errada.

    `senha_hash` não está aqui, e é este schema — declarado como
    `response_model` nas duas rotas — que garante que ele não vaze.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    # O e-mail entra porque dois porteiros podem se chamar parecido, e é ele
    # que desempata na hora de marcar quem trabalha na porta.
    email: str


class EventoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
    imagem_url: str | None
    origem_externa_id: str | None
    publicado_em: datetime | None
    setores: list[SetorSaida]
    # A escala volta na resposta para a confirmação da tela poder dizer, por
    # nome, quem ficou responsável pela porta — sem uma segunda chamada.
    portarias: list[PortariaSaida]

    # `organizador_id` fica de fora: quem acabou de publicar já sabe quem é, e
    # devolvê-lo só daria a impressão de que é um campo que se escolhe.
