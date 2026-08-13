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
from enum import Enum
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

# Maior valor que cabe num `Integer` do Postgres (int4), que é o tipo da coluna
# `setor.capacidade`. O schema recusa antes de o banco estourar — ver o comentário
# em `SetorEntrada.capacidade`.
_MAXIMO_INT4 = 2_147_483_647

# R$ 1.000.000.000,00 em centavos. A coluna é `BigInteger` e aguentaria muito
# mais; o teto real é o do JavaScript do formulário, não o do banco.
_MAXIMO_PRECO_CENTAVOS = 100_000_000_000


class SetorEntrada(BaseModel):
    nome: TextoLimpo = Field(min_length=1, max_length=80)
    # `ge=1` e não `ge=0`: o `CHECK capacidade_positiva` da Story 2.3 diz
    # `> 0`, e o schema recusa antes de o banco precisar defender. Setor com
    # capacidade zero nasce esgotado e ninguém entende por que não dá comprar.
    #
    # ⚠️ O `le` é tão obrigatório quanto o `ge`, e por um motivo que só apareceu
    # no code review da Epic 2: a coluna é `Integer` (int4). Sem teto,
    # `capacidade: 3000000000` passava aqui, passava por todas as recusas do
    # service e só estourava no `commit`, como `DataError: integer out of
    # range` — que não é `IntegrityError`, não era previsto por ninguém e caía
    # no handler genérico. Erro de digitação virando `500 ERRO_INTERNO` é a
    # mesma "pior resposta possível" que o `SETOR_DUPLICADO` existe para evitar.
    capacidade: int = Field(ge=1, le=_MAXIMO_INT4)
    # Inteiro, nunca `float` (AD-11): dinheiro em ponto flutuante é erro de
    # arredondamento esperando acontecer. A conversão de reais para centavos
    # acontece no cliente, antes do envio.
    #
    # O teto é R$ 1 bilhão por ingresso — proteção contra corpo absurdo, não
    # regra de produto, como o `max_length=20` dos setores. Ele fica **abaixo**
    # de `Number.MAX_SAFE_INTEGER`, e é isso que importa: acima disso o próprio
    # JavaScript do formulário já perde precisão antes de enviar, e o valor
    # gravado não seria o digitado.
    preco_centavos: int = Field(ge=0, le=_MAXIMO_PRECO_CENTAVOS)


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

    @field_validator("imagem_url")
    @classmethod
    def _exigir_esquema_http(cls, valor: str | None) -> str | None:
        """Só `http://` e `https://`.

        Acrescentado no code review da Epic 2. O campo **chega pelo corpo da
        requisição**, não da Ticketmaster — o service não confere nada contra o
        catálogo, então "veio do fornecedor" nunca foi garantia. Ele é gravado,
        devolvido em `EventoSaida` e a Epic 3 vai renderizá-lo em `<img src>` na
        programação pública, onde `javascript:`, `data:` e o pixel de rastreio de
        terceiro não têm o que fazer.
        """
        if valor is not None and not valor.startswith(("http://", "https://")):
            raise ValueError("a imagem precisa ser uma URL http:// ou https://")
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


class EventoResumo(BaseModel):
    """Um evento como ele aparece na **lista** do organizador (Story 2.6).

    É a primeira vista de leitura deste projeto que não espelha uma linha do
    banco: `capacidade_total` e `vendidos_total` não existem em coluna nenhuma
    — são a soma dos setores, feita pelo service (AD-13). Por isso ele é o
    único dos quatro schemas deste módulo **sem `from_attributes`**: não há
    `Evento` do ORM de onde ler esses dois atributos, e declarar
    `from_attributes` prometeria uma conversão que não acontece.

    **Os setores não vêm, e a imagem também não.** O detalhe
    (`GET /organizador/eventos/{id}`, com `EventoSaida`) é quem abre setor a
    setor; aqui a fila precisa ser escaneável — data, nome, local e um par de
    números. Com três setores por evento e dez eventos, devolver a lista
    inteira transformaria a listagem num paredão onde não se acha o show de
    sexta.
    """

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
    publicado_em: datetime | None
    # ⚠️ Soma de `setor.capacidade` e `setor.vendidos` — AD-13. É **proibido**
    # derivar qualquer um dos dois com `COUNT` sobre reserva ou ingresso, em
    # qualquer camada. As duas tabelas nem existem ainda, e é agora que o
    # hábito se forma: `setor.vendidos` é a única fonte de verdade da
    # disponibilidade, e o `UPDATE` condicional da Epic 3 é quem vai mexer nela.
    capacidade_total: int
    vendidos_total: int


class PeriodoDaProgramacao(str, Enum):
    """O recorte de tempo do filtro `?periodo=` da programação (Story 3.2).

    **`str, Enum`, no molde do `PapelUsuario`.** Declarado como tipo do `Query`,
    ele faz três coisas de uma vez: documenta os três valores no OpenAPI,
    devolve `422` para qualquer outro **antes** de a consulta ser montada, e dá
    ao service um valor de que ele pode comparar sem `if` de string solta.
    Aceitar `str` cru e comparar dentro do service faria `?periodo=ontem` cair
    silenciosamente no ramo "sem filtro" — a pessoa veria a programação inteira
    achando que filtrou.

    **As janelas são corridas** — 7 e 30 dias **a partir de agora** —, e não a
    semana e o mês do calendário (decisão do Igor). "Esta semana" numa
    sexta-feira significaria dois dias, e "este mês" no dia 29 significaria
    quase nada: o filtro pareceria quebrado justamente nos dias em que mais
    gente procura show. Os rótulos da tela dizem exatamente isso — `7 DIAS` e
    `30 DIAS` —, para o chip não prometer calendário e entregar outra coisa.

    `TODOS` é o padrão e **não acrescenta condição nenhuma** ao `where`: ele
    existe para o chip "Todos" ter um valor a apontar, não para virar um teto
    infinito escrito em SQL.
    """

    TODOS = "todos"
    SEMANA = "semana"
    MES = "mes"


class EventoNaProgramacao(BaseModel):
    """Um evento como o **visitante** o vê na programação pública (Story 3.1).

    **O que ele recusa a devolver, e por quê.** `capacidade`, `vendidos`,
    `setores` e `imagem_url` não estão aqui, e a ausência dos três primeiros é
    a materialização do **UX-DR7** no contrato — não uma escolha de payload
    enxuto. `DESIGN.md#Do's and Don'ts` proíbe contagem exata de ingresso em
    tela de cliente, e "a tela não mostra" nunca foi garantia: o que a API
    devolve, o devtools mostra. A garantia é este `response_model`, declarado
    na rota — sem ele o FastAPI serializaria o que o service devolvesse.

    `imagem_url` fica de fora por outro motivo (decisão do Igor): a fila de
    quatro colunas não tem imagem, e quem precisa da arte é a chamada principal
    da Story 3.3. Campo que nenhuma tela lê é campo que ninguém sabe se está
    certo — a mesma disciplina que recusou o `relationship` sem consumidor na
    2.3. `publicado_em`, `origem_externa_id` e `organizador_id` também não
    entram: não são assunto de quem está escolhendo um show.

    **Os dois campos derivados existem para não revelar o estoque.**
    `preco_minimo_centavos` e `esgotado` nascem de `setor.vendidos` e
    `setor.capacidade` (AD-13) e não deixam nenhum dos dois atravessar: é a
    diferença entre dizer "restam 3" e dizer "últimos ingressos".

    **Sem `from_attributes`**, como o `EventoResumo` e pelo mesmo motivo: os
    dois últimos campos não são atributos do `Evento`, e declarar a conversão
    prometeria uma leitura que não acontece. Quem os calcula é o service.
    """

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
    # `None` quando não há nenhum setor com ingresso — evento esgotado ou
    # evento sem setor nenhum. Ver `services/evento.py::listar_programacao`.
    preco_minimo_centavos: int | None
    # Campo próprio, e não algo que a tela deriva de `preco_minimo_centavos ==
    # null`: as duas versões dizem a mesma coisa hoje, e a segunda faria a tela
    # reconstruir uma regra de domínio a partir da ausência de um valor. O dia
    # em que um evento tiver ingresso a preço zero, alguém descobriria isso
    # pela tela errada.
    esgotado: bool


class EventoEmDestaque(BaseModel):
    """O próximo show da programação, como a **chamada principal** o mostra
    (Story 3.3).

    **Por que ele existe em vez de dois campos no `EventoNaProgramacao`**
    (decisão do Igor). A capa precisa de duas coisas que a fila não desenha: a
    arte e os nomes dos setores. Acrescentá-las à lista custaria uma linha de
    schema e faria **todo** item da programação carregar uma URL e uma lista que
    só um deles usa — exatamente o que a Story 3.1 recusou ao deixar
    `imagem_url` de fora ("campo que nenhuma tela lê é campo que ninguém sabe se
    está certo"). Pior no caso dos setores: eles são o campo que o UX-DR7
    mantém fora da listagem, e devolvê-los ali por causa da capa abriria a porta
    pelo motivo errado. Dois contratos independentes custam uma classe; um
    contrato que serve às duas telas custa a disciplina de todas as próximas.

    **As três coisas que ele recusa, e por quê:**

    - **`capacidade` e `vendidos`** — UX-DR7 e AD-13. `esgotado` nasce dos dois
      e não deixa nenhum atravessar: é a diferença entre dizer "restam 3" e
      dizer "esgotado". A ficha da capa não tem contagem em lugar nenhum
    - **`publicado_em`, `origem_externa_id` e `organizador_id`** — assunto de
      quem publica, não de quem está escolhendo um show

    **`preco_minimo_centavos` entrou depois de a tela ficar pronta**, e a ordem
    importa: a ficha nasceu como `CASA · CIDADE · SETORES`, sem preço, e o Igor
    decidiu acrescentá-lo ao ver a capa montada — o show em destaque **sai da
    fila** (Story 3.3), então ele era o único da programação sem "a partir de"
    em lugar nenhum da raiz. Ele voltou como **um campo derivado**, e não como a
    lista de setores com preço dentro: é a diferença entre devolver um número e
    devolver o estoque que o produziu.

    **Por que `setores` é `list[str]` e não `list[SetorSaida]`.** A ficha quer
    três nomes — `Pista, VIP e Camarote` —, e `SetorSaida` carrega `capacidade`,
    `vendidos` e `preco_centavos`. Reusá-lo "porque já existe um schema de
    setor" seria o UX-DR7 caindo por reuso de schema, com o estoque inteiro
    atravessando a rede para a tela desenhar três palavras. A economia de uma
    classe não paga isso. É a primeira vez que um schema deste projeto devolve
    uma **projeção** de um relacionamento, e é esta a fronteira que a segura.

    **Sem `from_attributes`**, como o `EventoNaProgramacao` e pelo mesmo motivo:
    `setores` (de nomes) e `esgotado` não são atributos do `Evento`, e declarar
    a conversão prometeria uma leitura que não acontece. Quem os monta é o
    service.
    """

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
    # Anulável desde a Story 2.3, e a chave **continua no corpo** quando é nula:
    # a tela distingue "sem arte" (bloco do mesmo tamanho no lugar) de "campo
    # que não veio". Nada de `exclude_none` aqui.
    imagem_url: str | None
    # **Só os nomes**, em ordem alfabética — a ordem já vem do
    # `order_by="Setor.nome"` do `relationship` (Story 2.3), e não de um
    # `sorted()` no service. Todos entram, inclusive o esgotado: a ficha diz o
    # que o show **tem**, não o que sobrou.
    setores: list[str]
    # O menor preço **entre os setores que ainda têm ingresso**, como no
    # `EventoNaProgramacao` e pelo mesmo motivo: se a Pista esgotou, a capa
    # anuncia o preço do que dá para comprar. `None` quando não há nenhum — ou
    # seja, sempre que `esgotado` for verdadeiro.
    preco_minimo_centavos: int | None
    esgotado: bool


class DisponibilidadeDoSetor(str, Enum):
    """Quanto resta de um setor, **em palavra** — nunca em número (Story 3.4).

    **`str, Enum`, no molde do `PeriodoDaProgramacao`**: os três valores entram
    no OpenAPI, e quem consome o contrato sabe que a lista é fechada. A tela lê a
    palavra e escolhe a cor da barra; ela não tem como inventar um quarto estado
    porque não é ela quem decide qual é o estado.

    **Por que um enum de três valores e não `esgotado: bool` + `ultimos: bool`.**
    Dois booleanos permitem quatro combinações e uma delas é impossível
    (`esgotado=True, ultimos=True`) — a tela precisaria de um `if` para tratar um
    estado que o backend jamais manda, ou pior, esqueceria e desenharia a barra
    cheia com a palavra errada. Um enum fechado não tem estado inválido para
    esquecer. É também mais barato de crescer: se um dia houver `EM_BREVE`, ele é
    um valor a mais aqui, e não um terceiro booleano multiplicando o número de
    combinações por dois.

    **O estado é derivado no backend, e é isso que protege o UX-DR7.** O limiar
    nasce de `capacidade` e `vendidos` (AD-13), os dois números que esta rota não
    pode devolver. Mandar os dois para a tela decidir seria o caminho mais curto
    para o estoque atravessar: a regra viraria uma linha de TSX e os números
    ficariam no devtools de qualquer visitante. Aqui só a palavra atravessa —
    `ULTIMOS` diz "corre" sem dizer "restam 3".

    `ULTIMOS` é **20% ou menos da capacidade** (decisão do Igor), na mesma moeda
    do medidor: a barra e a palavra dizem a mesma coisa, e a regra vale igual
    para um setor de 50 e um de 5.000 lugares. A alternativa — "10 ingressos ou
    menos" — faria metade da casa ser "últimos" num setor de 20 lugares.
    """

    DISPONIVEL = "DISPONIVEL"
    ULTIMOS = "ULTIMOS"
    ESGOTADO = "ESGOTADO"


class SetorPublico(BaseModel):
    """Um setor como **quem vai comprar** o vê (Story 3.4).

    ⚠️ **Ele não é o `SetorSaida`, e reusar aquele aqui seria o UX-DR7 caindo por
    reuso de schema.** `SetorSaida` carrega `capacidade` e `vendidos` porque é o
    inventário do organizador — quem publicou vê números exatos, e vê por
    direito. Esta rota é a que chega **mais perto** do estoque em todo o lado
    público (é a tela em que a pessoa escolhe quantos ingressos quer), e é
    justamente por isso que ela não pode carregá-lo. A tentação é maior do que na
    Story 3.3, onde a ficha da capa só precisava de nomes: aqui a tela precisa
    **de dado de setor de verdade**, e o schema errado está a um import de
    distância.

    **`preco_centavos` entra, e é a primeira vez em rota de cliente.** Até aqui
    só saíram derivados (`preco_minimo_centavos`), para o estoque não vazar junto
    com o preço. Aqui o preço de cada setor é a informação principal da tela —
    ninguém escolhe entre Pista e Camarote sem saber quanto custa cada um —, e
    preço não é contagem: ele não diz nada sobre quantos ingressos restam.

    **`proporcao_vendida` é proporção, não contagem, e a diferença é a story
    inteira.** Ela é `vendidos / capacidade` arredondada em duas casas, e é a
    largura da barra do medidor. Devolver os dois números daria à tela a mesma
    barra e mais a frase "restam 61" — que é exatamente o que o
    `DESIGN.md#Do's and Don'ts` proíbe em tela de cliente. Duas casas desenham a
    barra com precisão de 1%, mais do que 5px de altura conseguem mostrar, e
    menos dígitos é menos superfície para alguém tentar reconstruir a capacidade.

    ⚠️ **O nome é feminino — `proporcao_vendida`, concordando com "proporção".**
    Não é preciosismo: `proporcao_vendidos` casaria a palavra proibida
    `vendidos` na varredura de texto do teste desta rota, e obrigaria a afrouxar
    a asserção que existe justamente para não ser afrouxada.

    **Sem `from_attributes`**, como o `EventoNaProgramacao` e o
    `EventoEmDestaque`: dois dos cinco campos não são atributos do `Setor` — eles
    nascem no service, de `capacidade` e `vendidos`. Declarar a conversão
    prometeria uma leitura que não acontece.
    """

    id: UUID
    nome: str
    preco_centavos: int
    disponibilidade: DisponibilidadeDoSetor
    # `0.0`–`1.0`, duas casas — a largura da barra. Teto de `0.99` enquanto o
    # setor não esgotou (ver `services/evento.py`).
    #
    # ⚠️ **Este campo VAZA a capacidade, e o comentário antigo dizia o contrário**
    # (code review da Epic 3, decisão do Igor de manter). Uma única leitura não
    # entrega nada, mas a diferença entre duas, sim: reservar `N` ingressos e
    # recarregar dá `Δp ≈ N/capacidade`, logo `capacidade ≈ N/Δp`. Num setor de
    # 15 lugares, comprar 3 move a proporção em exatamente `0.20` e revela a
    # capacidade inteira — e é justamente no setor pequeno, o que fica `ULTIMOS`,
    # que o UX-DR7 importa.
    #
    # **Fica assim de propósito.** Explorar isso exige compra real e repetida
    # (cada leitura custa uma reserva, com teto de 6 por compra), e a barra é a
    # informação que a tela usa para dar urgência sem números. A alternativa
    # descartada foi trocar o float por faixa discreta — quartis fechariam o
    # canal e granulariam a barra. O que **não** podia ficar era o comentário
    # anterior afirmando que "não existe caminho de volta daqui para
    # `capacidade` nem para `vendidos`": ele autorizava quem viesse depois a não
    # pensar no assunto.
    proporcao_vendida: float


class EventoPublico(BaseModel):
    """Um evento com seus setores, como **quem vai comprar** o vê (Story 3.4).

    A quarta e última vista pública da Epic 3, e a única que abre o evento setor
    a setor. As outras três — programação, capa e cidades — são listagem; esta é
    a tela da decisão.

    **O que ele recusa, e por quê:**

    - **`capacidade` e `vendidos`** — UX-DR7 e AD-13, garantidos por este
      `response_model` e não pela tela. O que substitui os dois é o par de campos
      derivados do `SetorPublico`: uma proporção e uma palavra. É a diferença
      entre desenhar uma barra pela metade e dizer "restam 61"
    - **`publicado_em`, `origem_externa_id` e `organizador_id`** — assunto de
      quem publica, não de quem está escolhendo um show. Mesma recusa dos outros
      três contratos públicos
    - **Endereço, classificação e fonte**, que o protótipo desenha — nenhum dos
      três existe no `Evento` (decisão do Igor). A ficha mostra `CASA` e
      `CIDADE`: o que a tela mostra é o que o banco tem

    **`maximo_por_compra` é teto fixo, e não `min(disponivel, 6)`** (decisão do
    Igor). É ele que permite ao stepper ter um teto **sem que o contrato revele
    quantos ingressos restam**: um teto que acompanhasse o estoque diria "restam
    2" toda vez que restassem poucos — pela tela e pelo devtools —, que é
    exatamente o que o UX-DR7 mantém fora. Pedir mais do que existe é recusado na
    Story 3.6, pelo `UPDATE` condicional do AD-3, e o
    `EXPERIENCE.md#Concorrência` já tem a frase escrita.

    **E ele vem do contrato em vez de ser constante da tela** porque a Story 3.6
    vai cobrar o mesmo teto do lado do servidor: com o número em dois lugares, o
    dia em que a regra mudar é o dia em que o stepper e a rota de reserva passam
    a discordar sobre qual é o teto — e quem descobre isso é a pessoa que
    escolheu 8 ingressos e recebeu uma recusa.

    **Sem `from_attributes`**, como os outros dois schemas públicos: `setores` é
    uma lista de `SetorPublico` (não de `Setor`) e `maximo_por_compra` não é
    coluna de nada. Quem monta os dois é o service.
    """

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
    # Anulável desde a Story 2.3, e a chave **continua no corpo** quando é nula:
    # a tela distingue "sem arte" (bloco do mesmo tamanho no lugar) de "campo que
    # não veio", como na capa da 3.3. Nada de `exclude_none` aqui.
    imagem_url: str | None
    # Constante do service (`MAXIMO_POR_COMPRA`), igual para todo evento hoje.
    # Está no contrato, e não na tela, pelo motivo escrito acima.
    maximo_por_compra: int
    # Todos, **inclusive o esgotado**, em ordem alfabética — a ordem já vem do
    # `order_by="Setor.nome"` do `relationship` (Story 2.3), não de um `sorted()`
    # no service. A tela esmaece o esgotado e tira o stepper dele; sumir com ele
    # faria a pessoa procurar o Camarote que o amigo comprou na semana passada.
    setores: list[SetorPublico]


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


class TurnoDaPortaria(BaseModel):
    """Um evento em que **quem está na porta** foi escalado (Story 5.1).

    A primeira leitura da `evento_portaria` desde que a Story 2.5 passou a
    gravá-la. É a lista de "onde eu trabalho" — não um inventário e não uma
    vitrine.

    **O que ele não devolve, e por quê.** Nem `capacidade`, nem `vendidos`, nem
    `setores`: quantas pessoas já entraram no turno é a Story 5.6, e ela vai
    contar `ingresso.usado_em`, não estoque. Devolver o inventário aqui daria à
    tela um número que ela não usa e que, no dia em que a 5.6 chegar, seria o
    número **errado** — vendidos não é entrou. O corte quem garante é o
    `response_model` da rota, e não a tela: a mesma disciplina que a Story 3.1
    inaugurou.

    **Nenhum campo derivado, nem mesmo `aberto: bool`** (decisão do Igor). O
    portão que libera a tela do evento duas horas antes do show é regra **da
    tela**, comparada com o relógio de quem lê — o precedente literal do
    `MeusEventos` da 2.6: "a API responde quais são os meus eventos; o que
    interessa agora é leitura". Mandar o booleano no contrato pareceria mais
    seguro e não é: o portão é conveniência operacional, não invariante. A
    invariante desta epic é o vínculo do AD-7, e ela se cumpre no `403` da rota,
    não num campo. Se a Story 5.2 decidir barrar validação fora da janela, ela
    calcula a própria regra no servidor.

    **Com `from_attributes`**, ao contrário do `EventoResumo` e dos três
    schemas públicos: os cinco campos são colunas do `Evento`, sem uma soma nem
    uma projeção no meio. O critério deste módulo é sempre o mesmo — declarar a
    conversão só quando ela de fato acontece —, e aqui ela acontece.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    data_hora: datetime
    local: str
    # Anulável desde a Story 2.3, e a chave **continua no corpo** quando é nula:
    # a ficha da tela precisa distinguir "sem cidade" de "campo que não veio"
    # para não imprimir um separador solto. Nada de `exclude_none` aqui.
    cidade: str | None
