---
baseline_commit: "e5ecf30 — `feat: alteracao de paleta de cores`, na branch `Epic-3--Descoberta-e-compra`. Migração `head`: c7cb4a29b7f3 (`cria_tabela_evento_portaria`). Suíte: 231 testes passando (Story 3.1). ⚠️ Não executei git — este carimbo veio do estado informado no início da sessão; confira antes de começar."
---

# Story 3.2: Buscar e filtrar a programação

Status: review

Epic 3 — Descoberta e compra · **A segunda story da epic, e a primeira em que o visitante escreve
alguma coisa.** A 3.1 abriu a programação para quem chega sem conta; esta dá a ele a peneira.

Como visitante,
quero buscar por artista, casa ou cidade,
para chegar rápido ao show que me interessa.

São três parâmetros novos na rota pública que já existe (`GET /eventos?q=&cidade=&periodo=`), uma
segunda rota pública (`GET /eventos/cidades`, para os chips não mentirem), **uma migração que
habilita a extensão `unaccent` do Postgres** — a primeira migração deste projeto que não cria
tabela — e a barra de busca do `DESIGN.md` no topo da raiz, com os chips de filtro marcando o ativo
em `var(--neon)`.

Nenhum modelo novo, nenhuma coluna nova, nenhuma dependência nova. A raiz **continua sem uma linha
de `"use client"`**: o estado da busca mora na URL.

## Acceptance Criteria

1. **Given** eventos publicados com nomes, casas e cidades diferentes
   **When** eu chamo `GET /eventos?q=marina` **sem nenhum cookie de sessão**
   **Then** recebo `200` só com os eventos cujo **nome, local ou cidade** contêm o termo
   **And** a rota continua **pública por assinatura**: nenhum `Depends(exigir_papel(...))`, nenhuma
   dependência de sessão — os três parâmetros são `Query`, e nada mais mudou na assinatura
   **And** `GET /eventos` **sem nenhum parâmetro** devolve exatamente o que devolvia antes desta
   story — os treze testes da 3.1 provam isso e **nenhum deles pode precisar mudar**

2. **Given** um evento chamado `Marina Sena` em `São Paulo`
   **When** eu busco `MARINA`, `marina`, `sao paulo`, `SÃO PAULO` ou `sao`
   **Then** ele aparece em **todas** as cinco buscas
   **And** ⚠️ a insensibilidade a acento é a decisão do Igor desta story, e ela vem da extensão
   `unaccent` do Postgres: `unaccent(Evento.nome).ilike(unaccent(padrão))`. **Não** é um
   `translate()` com mapa de letras escrito à mão, e **não** é normalização em Python — filtrar em
   Python traria a tabela inteira para a memória e desfaria o motivo de o filtro estar no `where`

3. **Given** um evento chamado `100% Rock`
   **When** eu busco `%`
   **Then** recebo **só ele** — e não a programação inteira
   **And** ⚠️ `%` e `_` são curingas do `LIKE`: o termo é **escapado** antes de virar padrão
   (`\%`, `\_`, e a própria contrabarra), com `escape="\\"` declarado no `ilike`. Sem isso, um
   `?q=%` devolve tudo e um `?q=_` devolve quase tudo, e ninguém descobre porque a tela parece
   funcionar

4. **Given** a busca `?q=` vazia, ou só com espaços
   **When** eu chamo a rota
   **Then** ela devolve a programação inteira, como se o parâmetro não existisse
   **And** o termo é `.strip()` antes de qualquer coisa — `?q=%20marina%20` acha `Marina Sena`

5. **Given** `?q=` com mais de 120 caracteres
   **When** eu chamo a rota
   **Then** recebo `422`
   **And** o teto é `Query("", max_length=120)`, **o mesmo** de `GET /organizador/catalogo`, e o
   `<input>` da tela leva o mesmo `maxLength={120}` — foi assim que a Story 2.2 impediu a tela de
   acusar a Ticketmaster por um erro do próprio formulário

6. **Given** `?cidade=São Paulo`
   **When** eu chamo a rota
   **Then** recebo só os eventos daquela cidade
   **And** a comparação é **igualdade exata** (`Evento.cidade == cidade`), e não `ilike`: o valor
   vem dos chips, que vêm do próprio banco — o parâmetro não é campo de digitação
   **And** evento com `cidade = NULL` (anulável desde a 2.3) **não aparece** em nenhum filtro de
   cidade, e continua aparecendo sem filtro

7. **Given** um evento daqui a 3 dias, um daqui a 15 e um daqui a 60
   **When** eu chamo `?periodo=semana`, depois `?periodo=mes`, depois sem `periodo`
   **Then** recebo, respectivamente, **um**, **dois** e **três** eventos
   **And** `semana` é `data_hora < agora + 7 dias` e `mes` é `data_hora < agora + 30 dias` — janelas
   corridas a partir de agora, **não** "até domingo" e "até o dia 31" (suposição declarada abaixo,
   uma linha para trocar)
   **And** `agora` continua sendo lido **uma vez** no início do service, e é o mesmo `agora` do
   corte de eventos passados da 3.1 — nunca dois relógios na mesma requisição

8. **Given** `?periodo=ontem` ou qualquer valor fora do enum
   **When** eu chamo a rota
   **Then** recebo `422`
   **And** o parâmetro é um `str, Enum` com exatamente `todos`, `semana` e `mes` — o OpenAPI
   documenta os três, e valor inventado morre no FastAPI, não numa comparação silenciosa
   **And** ⚠️ **a tela nunca produz um valor inválido**: ela normaliza o que veio da URL antes de
   chamar a API, para `/?periodo=xyz` digitado à mão mostrar a programação inteira em vez da frase
   de "não foi possível carregar"

9. **Given** `?q=marina&cidade=São Paulo&periodo=semana`
   **When** eu chamo a rota
   **Then** os três filtros valem **juntos** (`AND`), sobre as duas condições que já existiam
   (`publicado_em IS NOT NULL` **e** `data_hora >= agora`)
   **And** ⚠️ **as duas regras da 3.1 não têm exceção**: rascunho e evento passado continuam fora
   mesmo quando o termo casa perfeitamente com o nome deles. Há um teste para cada um dos dois, com
   busca que casaria

10. **Given** eventos publicados em São Paulo, no Rio e um sem cidade
    **When** eu chamo `GET /eventos/cidades` sem cookie nenhum
    **Then** recebo `200` com `["Rio de Janeiro", "São Paulo"]` — distintas, em ordem alfabética,
    **sem `null`**
    **And** ela usa o **mesmo** recorte de `publicado_em` e `data_hora >= agora`: chip de cidade que
    não tem show em cartaz é um filtro que só sabe devolver lista vazia
    **And** ⚠️ ela **não** reage a `?q=` nem a `?cidade=`. A lista de escolhas é o universo, não o
    resultado: encolhê-la conforme se filtra faz o chip sumir debaixo do cursor de quem ia clicar
    **And** ⚠️ ela é declarada **antes** de qualquer `/eventos/{id}` no `publico.py`, e há um
    comentário dizendo isso — a Story 3.4 pendura `{id}` no mesmo router, e `cidades` não é um UUID

11. **Given** a implementação do backend
    **When** eu a inspeciono
    **Then** **não** existe modelo novo, coluna nova, tabela nova, código de erro novo nem
    dependência nova
    **And** a única migração é `CREATE EXTENSION IF NOT EXISTS unaccent`, escrita à mão
    (`alembic revision -m`, **nunca** `--autogenerate`), com `DROP EXTENSION IF EXISTS unaccent` no
    `downgrade` e `down_revision = "c7cb4a29b7f3"`
    **And** o `selectinload(Evento.setores)` continua onde estava: filtrar não pode reintroduzir o
    N+1 que o AC8 da 3.1 fechou
    **And** a derivação de `preco_minimo_centavos` e `esgotado` **não muda uma linha** — AD-13, e
    continua proibido derivar disponibilidade por `COUNT`

12. **Given** o corpo de qualquer resposta desta story
    **When** eu procuro estoque
    **Then** não existe `capacidade`, `vendidos`, `setores`, `imagem_url`, `publicado_em` nem
    `organizador_id` em lugar nenhum — o `EventoNaProgramacao` **não ganha nem perde campo**
    **And** ⚠️ o teste que varre o texto inteiro da resposta atrás dessas palavras roda **também**
    com busca e filtro ativos: um `WHERE` novo não é desculpa para o contrato afrouxar (UX-DR7)

13. **Given** `src/lib/programacao.ts`
    **When** eu o leio
    **Then** `listarProgramacao` passou a receber os filtros e monta a query com `URLSearchParams`,
    **omitindo o que está vazio** — `/eventos` limpo continua sendo a chamada sem filtro
    **And** ele continua **sem `cabecalhoDeSessao()`** e sem `headers`: a rota é pública, e a
    ausência do cookie é a diferença entre "esqueci" e "é público"
    **And** ele ganha `listarCidadesEmCartaz()`, com o mesmo `cache: "no-store"`, o mesmo
    `try/catch` que **nunca levanta** e o `unstable_rethrow(erro)` como **primeira linha do
    `catch`** — o motivo inteiro está escrito no módulo desde a 3.1, e vale igual para a função nova
    **And** os dois estados de `ResultadoDaProgramacao` continuam dois: filtrar não cria `404`

14. **Given** a rota `/`
    **When** eu a abro
    **Then** ela continua **Server Component, sem uma linha de `"use client"`** — o estado da busca
    é a URL (`ARCHITECTURE-SPINE.md#Convenções`, "Server Component por padrão")
    **And** as duas buscas saem em `Promise.all`: a programação e as cidades não dependem uma da
    outra, e encadeá-las custaria uma ida à rede em série na tela mais visitada do produto
    **And** `searchParams` é `await`-ado (é `Promise` no Next 16) e cada parâmetro pode chegar como
    `string[]` — o primeiro valor basta, como em `organizador/publicar/page.tsx`

15. **Given** a barra de busca
    **When** eu a uso
    **Then** ela é um `<form method="get">` que aponta para a própria raiz, com o campo `q`, e
    submeter troca a URL para `/?q=…` — recarregável, compartilhável, e o botão voltar funciona
    **And** os filtros ativos **sobrevivem à busca**: `cidade` e `periodo` viajam no mesmo form como
    `<input type="hidden">` quando estão valendo
    **And** o campo tem rótulo de verdade — um `<label htmlFor="q">` **visualmente escondido**, não
    só `placeholder` (UX-DR9, e a mesma regra que o componente `Campo` cumpre com rótulo visível)
    **And** ⚠️ **nada de `onChange`, `useState`, `useRouter` ou debounce.** A busca acontece no
    `submit`; um teclado que dispara requisição por tecla é a coisa que transformaria esta tela numa
    ilha de cliente

16. **Given** os chips de filtro
    **When** eu os vejo
    **Then** há dois grupos, cada um aberto por um kicker: **`QUANDO`** (`TODOS · 7 DIAS ·
    30 DIAS`) e **`ONDE`** (`TODAS` + uma por cidade em cartaz)
    **And** o grupo `ONDE` **só é renderizado com duas cidades ou mais** — um filtro com uma opção
    só é um botão que não filtra
    **And** cada chip é um `<Link>` que carrega os outros filtros e o termo atual; nenhum é
    `<button>` com JavaScript
    **And** o chip ativo é **preenchido em `var(--neon)` com texto em `var(--breu)`** e leva
    `aria-current="true"`
    **And** ⚠️ a informação **não é dada só por cor** (UX-DR9): o ativo é *preenchido* e os outros
    são *vazados* — muda a forma, não só a matiz —, e o `aria-current` diz a mesma coisa a quem usa
    leitor de tela

17. **Given** uma busca ou um filtro que não acha nada
    **When** a lista volta vazia
    **Then** vejo **"Nenhum show encontrado para essa busca."** (`EXPERIENCE.md#Vazio`, texto
    literal), sem ilustração e sem botão grande — UX-DR8
    **And** junto dela, um link de texto **"Ver toda a programação"** apontando para `/`
    **And** ⚠️ são agora **três** frases diferentes e elas não se misturam: *nada em cartaz* (banco
    sem evento futuro, sem filtro), *nada para essa busca* (filtro ativo) e *não foi possível
    carregar* (API fora). A primeira é verdade sobre o produto, a segunda sobre o que eu digitei, a
    terceira é falha temporária — e cada uma pede um conserto diferente

18. **Given** a barra de busca na tela
    **When** eu a inspeciono
    **Then** ela fica **acima** do título `Programação`, logo abaixo do masthead, com fio de 1px
    embaixo — o lugar que o protótipo lhe dá (`proto-jornal-noturno.html:276-282`)
    **And** ela existe **mesmo quando a lista está vazia**: sumir a busca quando a busca não achou
    nada tira da pessoa a única ferramenta de corrigir o que ela digitou
    **And** o campo é serifada sobre fundo transparente e os chips são mono versalete, na anatomia
    do `.barra-busca`/`.filtros` do protótipo
    **And** **sem card, sem sombra, sem raio, e nenhum hex novo** — só `var(--token)` (UX-DR3)

19. **Given** uma tela abaixo de 900px
    **When** eu abro a programação
    **Then** o campo e o botão continuam na mesma linha, e os dois grupos de chips **quebram em
    linha** em vez de estourar a lateral
    **And** nada rola na horizontal, e os fios continuam de ponta a ponta
    **And** a fila de quatro colunas continua colapsando em duas, como na 3.1

20. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira e os **231** testes anteriores continuam verdes — nenhum precisa
    mudar
    **And** o número final está registrado
    **And** ⚠️ a migração nova roda no `rockhub_teste` pelo próprio `conftest.py`, que faz
    `downgrade base` + `upgrade head` a cada sessão. Se `CREATE EXTENSION` falhar por permissão, a
    suíte inteira morre na fixture — não é um teste vermelho, é a suíte não começando
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos

21. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta, na seção `## Programação pública` que já existe: os três
    parâmetros, **por que a busca vive no `where`**, a extensão `unaccent` e a migração que a
    habilita, o escape do `%`, e a rota de cidades — além do número novo da suíte
    **And** `frontend/README.md` documenta, em `## A raiz: a programação`: a busca como URL e não
    como estado, os chips como `<Link>`, e as três frases de lista vazia
    **And** os dois respeitam a régua de camada do `CLAUDE.md`: **no máximo cinco parágrafos**, na
    seção temática que já existe, sem tabela nova e sem subseção nova
    **And** `README.md` da **raiz não é tocado** nesta story — ver *Perguntas em aberto* nº 1

> **De onde vem cada critério.** O `epics.md` traz **três** blocos para a Story 3.2: a busca por
> termo casando nome, local ou cidade; o filtro de cidade ou período com o ativo marcado no acento
> da marca; e a busca sem resultado com a frase do `EXPERIENCE.md`, sem ilustração nem botão grande.
> Eles viraram os ACs **1**, **16** e **17**.
>
> Todo o resto é decisão do Igor (tabela abaixo) ou consequência técnica dela: a busca no `where` em
> vez de na tela (ACs 1, 13, 14, 15), a insensibilidade a acento e a migração que ela obriga (ACs 2,
> 11), a rota de cidades para os chips virem do banco (AC10), e o escape do `%` (AC3), que é a
> consequência menos óbvia de mandar texto de gente para dentro de um `LIKE`.

## Tasks / Subtasks

- [x] **T1. A migração da extensão** (AC: 2, 11, 20)
  - [x] `uv run alembic revision -m "habilita extensao unaccent"` — **sem `--autogenerate`**: não há
        mudança de modelo para detectar, e o autogenerate escreveria uma migração vazia (ou pior,
        proporia mexer em tabela que ninguém pediu)
  - [x] `upgrade`: `op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")`
  - [x] `downgrade`: `op.execute("DROP EXTENSION IF EXISTS unaccent")`
  - [x] Conferir `down_revision = "c7cb4a29b7f3"`
  - [x] Docstring do arquivo: **por que uma migração que não cria tabela** — a extensão é
        pré-requisito da consulta, e o schema é o lugar onde pré-requisito de consulta se declara.
        A alternativa (`translate()` com mapa de letras na consulta) foi descartada pelo Igor
  - [x] Rodar `uv run alembic upgrade head` no banco de desenvolvimento

- [x] **T2. `app/schemas/evento.py` — o enum do período** (AC: 7, 8)
  - [x] `class PeriodoDaProgramacao(str, Enum)` com `TODOS = "todos"`, `SEMANA = "semana"`,
        `MES = "mes"`
  - [x] Docstring dizendo que as janelas são **corridas** (7 e 30 dias a partir de agora) e por quê:
        "esta semana" numa sexta-feira significaria dois dias, e o filtro pareceria quebrado
  - [x] ⚠️ `EventoNaProgramacao` **não muda**: nem ganha, nem perde campo (AC12)

- [x] **T3. `app/services/evento.py` — os filtros no `where`** (AC: 1–4, 6, 7, 9, 10, 11)
  - [x] `listar_programacao(sessao, termo="", cidade="", periodo=PeriodoDaProgramacao.TODOS)`
    - [x] `agora = datetime.now(timezone.utc)` continua lido **uma vez**, e é o mesmo `agora` que
          serve ao corte de passados **e** ao teto do período
    - [x] Condições acumuladas numa lista, aplicadas num `where` só. As duas da 3.1 primeiro
    - [x] Termo: `.strip()`; se sobrou algo, escapar `\`, `%` e `_` **nesta ordem** (a contrabarra
          primeiro, ou ela escapa as próprias escapadas), montar `f"%{escapado}%"` e comparar
          `func.unaccent(coluna).ilike(func.unaccent(padrao), escape="\\")` em `or_(nome, local,
          cidade)`
    - [x] ⚠️ `Evento.cidade` é anulável: `unaccent(NULL) ILIKE …` é `NULL`, e `TRUE OR NULL` é
          `TRUE` — o evento sem cidade continua achável pelo nome. Não "conserte" isso com `coalesce`
    - [x] Cidade: `Evento.cidade == cidade` quando não vazia (igualdade exata, AC6)
    - [x] Período: `Evento.data_hora < agora + timedelta(days=7 ou 30)`; `TODOS` não acrescenta nada
    - [x] `order_by(Evento.data_hora, Evento.id)` e `selectinload(Evento.setores)` **intactos**
    - [x] A derivação de preço e `esgotado` **não muda uma linha** (AD-13)
  - [x] `listar_cidades_em_cartaz(sessao) -> list[str]`
    - [x] `select(Evento.cidade).where(publicado, futuro, Evento.cidade.is_not(None)).distinct()
          .order_by(Evento.cidade)`
    - [x] Docstring: por que ela **ignora** o termo e a cidade escolhida (AC10) — é o universo de
          escolhas, não o resultado
  - [x] Docstring de `listar_programacao` atualizada: as três decisões que já moravam lá continuam,
        e entra a quarta — **por que a peneira é do banco e não da tela** (decisão do Igor)

- [x] **T4. `app/api/publico.py` — os parâmetros e a segunda rota** (AC: 1, 5, 8, 10, 11)
  - [x] `q: str = Query("", max_length=120)`, `cidade: str = Query("", max_length=120)`,
        `periodo: PeriodoDaProgramacao = Query(PeriodoDaProgramacao.TODOS)`
  - [x] ⚠️ **Nenhuma dependência de sessão entra junto.** Só `sessao: Session = Depends(obter_sessao)`
  - [x] `@router.get("/eventos/cidades", response_model=list[str])`, declarada **antes** de qualquer
        rota com path param, com comentário para a Story 3.4: `/eventos/{id}` vem depois desta, ou
        o FastAPI tenta ler `"cidades"` como UUID e devolve `422`
  - [x] Docstrings: o que cada parâmetro faz, e que a rota **continua pública** — os três são
        `Query`, não `Depends`
  - [x] `app/main.py` **não muda**: o router já está incluído

- [x] **T5. Testes do backend** (AC: 1–12, 20)
  - [x] Em `tests/test_programacao.py`, reusando o helper de evento que já existe lá (`publicado:
        bool`, setores com `vendidos`) — ⚠️ ele pode precisar aceitar `cidade` e `local`; acrescente
        parâmetro com default, **não** troque a assinatura de quem já chama
  - [x] Termo casa **nome**; casa **local**; casa **cidade** — três testes
  - [x] Caixa: `MARINA` e `marina` acham o mesmo
  - [x] **Acento nos dois sentidos**: `sao paulo` acha `São Paulo`, e `SÃO` acha um evento gravado
        sem acento
  - [x] Termo sem resultado → `200 []`
  - [x] `?q=%` com um evento `100% Rock` no banco → devolve **só ele** (AC3)
  - [x] `?q=` vazio e `?q=   ` → programação inteira
  - [x] `?q=` com 121 caracteres → `422`
  - [x] `?cidade=` filtra; evento com `cidade = NULL` fica fora dele e dentro da lista sem filtro
  - [x] `?periodo=semana` / `mes` / ausente → 1, 2 e 3 eventos (3, 15 e 60 dias)
  - [x] `?periodo=ontem` → `422`
  - [x] Os três filtros juntos (AC9)
  - [x] ⚠️ **Rascunho e evento passado continuam fora mesmo com termo que casaria** — dois testes,
        e são os que provam que os filtros novos não abriram porta nos cortes da 3.1
  - [x] `GET /eventos/cidades`: sem cookie → `200`; distintas, ordenadas, sem `null`; ignora
        rascunho e evento passado; **não** reage a `?q=`
  - [x] AC12: com busca ativa, o corpo continua com **exatamente as sete chaves**, e o texto inteiro
        da resposta não contém `capacidade`, `vendidos`, `setores`, `imagem_url` nem `organizador_id`
  - [x] OpenAPI: `GET /eventos` declara os três parâmetros, com o enum do período, e **nenhum
        parâmetro de segurança**
  - [x] ⚠️ **Nenhum teste antigo deve precisar mudar.** Se algum quebrar, algo saiu do escopo —
        pare e diga

- [x] **T6. `src/lib/programacao.ts` — filtros na busca de servidor** (AC: 13)
  - [x] Tipo `PeriodoDaProgramacao = "todos" | "semana" | "mes"` e
        `FiltrosDaProgramacao = { q?: string; cidade?: string; periodo?: PeriodoDaProgramacao }`
  - [x] `listarProgramacao(filtros: FiltrosDaProgramacao = {})`: `URLSearchParams`, **omitindo
        vazio e `periodo: "todos"`** — a URL da API fica limpa quando não há filtro
  - [x] `listarCidadesEmCartaz(): Promise<string[]>` — `[]` em qualquer falha, com comentário
        dizendo por que ela **não** ganha resultado discriminado: não há nada diferente para a tela
        fazer sem os chips, e um estado que a tela renderiza igual é um ramo morto
  - [x] ⚠️ `unstable_rethrow(erro)` como **primeira linha** do `catch` das **duas** funções
  - [x] Continua **sem `headers`** e sem `cabecalhoDeSessao()`, com o comentário que já está lá

- [x] **T7. A tela** (AC: 14–19)
  - [x] `src/app/(site)/page.tsx`: `searchParams` (`await`, `PageProps<"/">`), helper local para
        pegar o primeiro valor de `string | string[]`
    - [x] ⚠️ O gêmeo dele em `organizador/publicar/page.tsx` **fica onde está**. Duas cópias de duas
          linhas não são um módulo, e promovê-lo mexeria numa tela já revisada por nada
  - [x] Normalizar `periodo` para um dos três valores conhecidos **antes** de chamar a API (AC8)
  - [x] `Promise.all([listarProgramacao(filtros), listarCidadesEmCartaz()])`
  - [x] `BarraDeBusca`: `<form method="get" action="/">`, `<label>` escondido, `<input
        type="search" name="q" defaultValue maxLength={120}>`, `<input type="hidden">` para `cidade`
        e `periodo` quando valendo, e `<Botao type="submit">Buscar</Botao>` — **reusado**, não
        reescrito
  - [x] `Chip`: `<Link>` com `aria-current`, montando o destino com `URLSearchParams` (nunca
        concatenando `encodeURIComponent` à mão — foi assim que a Story 2.4 produziu `%2520`)
  - [x] Os dois grupos com kicker; o grupo `ONDE` só com **duas ou mais** cidades
  - [x] Os **três** estados de lista vazia, cada um com a sua frase (AC17), e o link
        `Ver toda a programação` no da busca
  - [x] `page.module.css`: `.barraBusca`, `.grupos`, `.chip`, `.chipAtivo`, `.rotuloOculto` — no
        vocabulário do `.barra-busca`/`.filtros` do protótipo. **Nenhum hex novo**
  - [x] Media query de 900px: os grupos de chips quebram em linha (AC19)
  - [x] ⚠️ **Nenhum `"use client"` entra em nada** desta tela

- [x] **T8. Verificação** (AC: 19, 20)
  - [x] `uv run alembic upgrade head` no banco de desenvolvimento **antes** de subir o `uvicorn` —
        sem a extensão, toda chamada à raiz vira `500`
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos, e `/` continua `ƒ`
  - [x] Conferir na tela, com `next dev` e `uvicorn` no ar:
    - [x] Buscar um termo com acento digitado **sem** acento — o show aparece
    - [x] Buscar `%` — não devolve a lista inteira
    - [x] Clicar num chip de cidade e depois buscar um termo: **o chip continua marcado** e a URL
          tem os dois
    - [x] Uma busca que não acha nada → a frase da busca, o link de voltar, e **a barra continua lá**
    - [x] Abrir `/?periodo=xyz` à mão → programação inteira, sem frase de erro
    - [x] Derrubar o `uvicorn` e recarregar → frase de indisponível, sem tela quebrada e sem chips
    - [ ] Abaixo de 900px: os chips quebram, nada rola na horizontal — **conferência do Igor**
    - [ ] Tab pela barra: campo → botão → chips, todos com o contorno neon do `:focus-visible` —
          **conferência do Igor**
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2)
  - [ ] ⚠️ Conferir que os arquivos novos **estão rastreados** — **não executo git** (regra do
        projeto); a conferência é do Igor
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** ao terminar

- [x] **T9. Os READMEs** (AC: 21) — obrigatório, regra do projeto
  - [x] `backend/README.md`, até cinco parágrafos em `## Programação pública`: os três parâmetros, a
        busca no `where`, o `unaccent` e a migração, o escape do `%`, a rota de cidades. *Estrutura*
        atualizada com a migração nova, e o número da suíte corrigido
  - [x] `frontend/README.md`, até cinco parágrafos em `## A raiz: a programação`: a busca como URL,
        os chips como `<Link>`, as três frases de lista vazia
  - [x] `README.md` da raiz: **não tocar** — ver *Perguntas em aberto* nº 1
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README
(T9) — é o "por quê" dele.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| Onde a peneira roda | **No `where` do Postgres, com a busca na URL.** `GET /eventos?q=&cidade=&periodo=` filtra a tabela `evento` — só o que organizador publicou —, e a tela é um `<form method="get">` como a busca do catálogo em `/organizador/publicar`. A raiz continua Server Component, `/?q=marina` é um link que se compartilha, e o botão voltar funciona | *Filtrar em JavaScript a lista já carregada*: instantâneo ao digitar e sem rota nova — caiu porque a raiz viraria ilha `"use client"` (hoje ela não tem nenhuma), o filtro não sobreviveria a recarregar nem a compartilhar, e a lista inteira atravessaria a rede a cada visita. E o *misto* (termo na API, chips no cliente): metade do estado na URL e metade em `useState` são duas explicações para a mesma barra |
| Quais filtros | **Período e cidade, os dois vindos do banco.** Chips `TODOS · 7 DIAS · 30 DIAS` e uma cidade por show em cartaz, lidas de `GET /eventos/cidades`. Nenhum chip mente: só aparece cidade que tem evento | *Só período*, deixando cidade para o campo de busca: menos código e nenhuma consulta extra — caiu porque escolher entre duas cidades é um clique, e digitar o nome delas é um acerto de grafia. E *cidades fixas no código*, como o protótipo (`São Paulo`, `Rio`): barato, e mente no dia em que houver um show em Belo Horizonte |
| Acento na busca | **`sao paulo` acha `São Paulo`**, via extensão `unaccent` do Postgres, habilitada por migração. É como as pessoas digitam no celular, e quem avalia vai digitar assim | *Só insensível a caixa* (`ILIKE` puro): zero migração, e a story continuaria sem tocar o banco — caiu porque a busca falharia no caso mais comum que existe. E o *`translate()` com mapa de letras à mão*: mesma tela, sem migração e sem depender do Postgres da Railway — caiu porque é um mapa de trinta caracteres que ninguém revisa de novo, e que esquece `ü` e `ñ` em silêncio |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar.

- **`7 DIAS` e `30 DIAS`, e não `Esta semana` e `Este mês`.** As janelas são corridas a partir de
  agora. "Esta semana" numa sexta-feira significa dois dias, e o filtro pareceria quebrado justamente
  no dia em que mais gente procura show; "este mês" no dia 29 é pior. Os rótulos foram escritos para
  dizer exatamente o que o filtro faz. ⚠️ **O Igor aprovou a opção escrita como `Esta semana · Este
  mês`** — se ele preferir os rótulos originais, são duas strings; se preferir a semana e o mês do
  calendário, é o cálculo do teto no service.
- **A rota das cidades é `GET /eventos/cidades`, no mesmo `publico.py`.** É uma lista de facetas do
  mesmo recurso, e o alternativo `/cidades` na raiz da API não diz cidades de quê. O preço é a ordem
  de declaração perante o `/eventos/{id}` da Story 3.4, e há comentário no código sobre isso.
- **Os chips são dois grupos com kicker (`QUANDO`, `ONDE`), e não uma fileira única.** O protótipo
  mistura período e cidade numa linha só (`Todos · Esta semana · São Paulo · Rio`), o que funciona
  com quatro chips fixos e deixa de funcionar assim que as cidades vêm do banco: ninguém saberia que
  clicar em `São Paulo` não desliga `Esta semana`.
- **O grupo `ONDE` só aparece com duas cidades ou mais.** Com uma cidade só, o par `TODAS · SÃO
  PAULO` é dois botões que devolvem a mesma lista.
- **O termo casa por trecho (`%termo%`), e não por prefixo nem por palavra inteira.** `sena` acha
  `Marina Sena`. Busca por prefixo faria a pessoa acertar o começo do nome, que é justamente o que
  ela não lembra.
- **A cidade é comparada por igualdade exata**, sem `unaccent` e sem `ilike`: o valor sempre vem dos
  nossos próprios chips. Quem digitar `?cidade=sao paulo` à mão recebe lista vazia — e o campo de
  busca serve exatamente para isso.
- **`listarCidadesEmCartaz` devolve `string[]` e engole a falha.** Sem os chips a tela continua
  inteira e a busca continua funcionando; um resultado discriminado criaria um estado que a tela
  renderiza igual ao caso feliz.
- **Nenhuma paginação, ainda.** Continua valendo o que a 3.1 escreveu: uma avaliação tem unidades de
  eventos, e busca é o que resolve lista grande de verdade — é esta story.
- **Nenhum contador de resultados.** "3 shows encontrados" é exatamente a *linha de contexto
  decorativa* que o UX-DR10 proíbe, e a lista já mostra quantos são.

### O contrato da API, campo a campo

**`GET /eventos`** · `200` · `response_model=list[EventoNaProgramacao]` · **pública**

| Parâmetro | Tipo | Padrão | O que faz |
|---|---|---|---|
| `q` | `str`, `max_length=120` | `""` | Trecho de `nome`, `local` **ou** `cidade`. Sem acento e sem caixa. Vazio ou só espaços = sem filtro |
| `cidade` | `str`, `max_length=120` | `""` | Igualdade exata com `evento.cidade` |
| `periodo` | `todos` \| `semana` \| `mes` | `todos` | Teto em `agora + 7d` ou `agora + 30d`. Valor fora do enum → `422` |

Os três se somam com `AND`, **sobre** as duas condições que a Story 3.1 já impunha
(`publicado_em IS NOT NULL` e `data_hora >= agora`). O corpo de cada item **não muda**: as mesmas
sete chaves, sem `capacidade`, `vendidos`, `setores`, `imagem_url`, `publicado_em`,
`origem_externa_id` nem `organizador_id`.

**`GET /eventos/cidades`** · `200` · `response_model=list[str]` · **pública**

```json
["Rio de Janeiro", "São Paulo"]
```

Distintas, ordenadas, sem `null`, do mesmo recorte de publicados e futuros. **Sem parâmetro
nenhum** — ela é o universo de escolhas, não o resultado da busca.

**Nenhum código de erro novo.** `422` do FastAPI para parâmetro inválido, que é o mesmo que
`GET /organizador/catalogo` já faz desde a Story 2.2.

[Fonte: ARCHITECTURE-SPINE.md#AD-13, #Convenções · backend/app/api/publico.py · backend/app/api/organizador.py:59-63]

### A tela, em texto

```
  ┌ BUSCAR ARTISTA, CASA DE SHOW OU CIDADE ────────────┬──────────┐
  │ marina                                             │  BUSCAR  │
  └────────────────────────────────────────────────────┴──────────┘
  QUANDO  [TODOS] 7 DIAS  30 DIAS     ONDE  TODAS  [SÃO PAULO]  RIO DE JANEIRO
          ^^^^^^^ preenchido em neon                 ^^^^^^^^^^^ idem

  PROGRAMAÇÃO
  ─────────────────────────────────────────────────────────────────────────
  SEX          Marina Sena                  Qualistage          A PARTIR DE
  15                                        SÃO PAULO           R$ 90,00
  ─────────────────────────────────────────────────────────────────────────
```

- Campo em **serifada**, fundo transparente, fio de 1px fechando a barra embaixo — o
  `.barra-busca` do protótipo. O rótulo existe no HTML e não na tela
- Chips em **mono versalete**, vazados; o ativo preenchido em `var(--neon)` com texto `var(--breu)`
- Kicker `QUANDO` e `ONDE` abrindo cada grupo, na classe `.kicker` que já é global
- **Sem caixa, sem sombra, sem raio.** Nenhum hex novo
- Lista vazia com filtro: `Nenhum show encontrado para essa busca.` + `Ver toda a programação`
- **A barra nunca some** — nem com lista vazia, nem com a API fora

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `listar_programacao` | `app/services/evento.py:285` | **É esta função que ganha os filtros.** Leia o docstring inteiro antes: as três decisões que moram lá continuam valendo |
| `listar_programacao` (rota) | `app/api/publico.py:30` | Ganha três `Query`. **Nenhuma dependência nova** |
| `q: str = Query("", max_length=120)` | `app/api/organizador.py:61` | O precedente exato do teto do termo, e do `maxLength` gêmeo no `<input>` |
| `EventoNaProgramacao` | `app/schemas/evento.py:238` | **Não muda.** O enum do período entra ao lado |
| `PapelUsuario` | `app/models/usuario.py` | O molde de `str, Enum` do projeto |
| Migração `c7cb4a29b7f3` | `migrations/versions/` | O molde de arquivo; a nova é **escrita à mão**, não autogerada |
| `conftest.py` (`engine_teste`) | `tests/conftest.py:75` | `downgrade base` + `upgrade head` por sessão — é ele que aplica a extensão no `rockhub_teste`. **Não mexa** |
| `test_programacao.py` | `tests/` | **É este arquivo que cresce.** Mesma rota, mesmos helpers |
| `listarProgramacao` | `frontend/src/lib/programacao.ts:46` | Ganha o parâmetro de filtros. O comentário do `unstable_rethrow` e o da ausência de cookie **ficam** |
| `<form method="get">` + `searchParams` | `frontend/src/app/(site)/organizador/publicar/page.tsx:118` | **O molde inteiro da barra**: form GET, `URLSearchParams` para montar destino, helper de primeiro valor |
| `Botao`, `Campo` | `frontend/src/components/` | `Botao` é reusado no submit. `Campo` **não** serve aqui (rótulo visível na barra quebraria a faixa) — copie a regra dele, que é "nunca campo sem rótulo" |
| `NavLink` | `frontend/src/components/NavLink.tsx` | O precedente de item ativo com `aria-current`. ⚠️ Ele é `"use client"` por causa do `usePathname()`; **os chips não precisam disso**, porque quem sabe o filtro ativo é a página |
| `.secTitulo`, `.fila`, `.aviso`, `.vazio` | `(site)/page.module.css` | O arquivo que cresce. O recuo lateral de **12px** é compartilhado por todos e a barra nova entra nele — é o que mantém os fios de ponta a ponta |
| Tokens | `frontend/src/app/globals.css` | `var(--neon)`, `var(--fio)`, `var(--breu)`, `var(--breu2)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)`, `.kicker`, `:focus-visible` |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, as três migrações que já
existem, `seeds/`, `app/core/`, `app/integrations/`, `app/main.py`, `app/schemas/auth.py`,
`app/schemas/catalogo.py`, `app/api/auth.py`, `app/api/organizador.py`, `app/api/saude.py`,
`app/services/autenticacao.py`, `publicar()`, `listar_portarias()`, `listar_do_organizador()`,
`obter_do_organizador()`, `tests/conftest.py`, `docker-compose.yml`, `pyproject.toml`,
`package.json`, `frontend/src/lib/servidor.ts`, `sessao.ts`, `api.ts`, `caminho.ts`, `eventos.ts`,
`catalogo.ts`, `formato.ts`, `Masthead.tsx`, `globals.css`, e as telas de `(entrada)/` e de
`organizador/`.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Esquecer de escapar `%` e `_`.** É o erro mais fácil desta story e o mais silencioso: a tela
funciona, os testes de busca comum passam, e `?q=%` devolve a programação inteira como se fosse
resultado. Escape na ordem certa — contrabarra primeiro —, e declare `escape="\\"` no `ilike`, ou o
Postgres não sabe que a contrabarra é escape.

**2. Rodar a suíte sem aplicar a migração no banco de desenvolvimento.** O `conftest.py` migra o
`rockhub_teste` sozinho, então os testes passam e a tela quebra com `500: function unaccent(text)
does not exist`. `uv run alembic upgrade head` é a primeira coisa depois da T1.

**3. Filtrar em Python "porque é mais fácil de escrever".** Uma compreensão de lista sobre o
resultado dá o mesmo na tela e desfaz a decisão inteira do Igor: a peneira está no `where` para o
banco devolver só o que interessa. Se a condição não couber no `where`, é sinal de que ela está
errada, não de que o Python resolve.

**4. A tela virando `"use client"` sem ninguém decidir.** Basta um `onChange` no campo, ou um
`useRouter().push()` no chip. O sintoma é o `npm run build` deixando de marcar `/` como `ƒ`, ou o
Next reclamando de `useSearchParams` sem `<Suspense>`. A barra é um `<form method="get">` e os chips
são `<Link>` — nenhum dos dois precisa de JavaScript.

**5. Perder o filtro ao buscar (ou o termo ao filtrar).** É o defeito clássico de busca com chips:
`cidade` e `periodo` precisam viajar como `<input type="hidden">` dentro do form, e `q` precisa
entrar no `href` de cada chip. Um teste de tela não pega isso; o roteiro da T8 pega.

**6. Montar a URL com `encodeURIComponent` à mão.** `searchParams` chega decodificado, e concatenar
codificação em cima produz `%2520` e uma busca que não acha nada. Foi o que a Story 2.4 aprendeu:
`URLSearchParams` e só ele.

**7. `%2520` do outro lado: `?cidade=São Paulo` no `fetch` do servidor.** `URLSearchParams` no
`lib/programacao.ts` também — não interpole o valor direto na string da URL.

**8. Achar que `422` de parâmetro inválido é problema do backend.** É o comportamento certo. Quem
protege a tela é a normalização do `periodo` **antes** da chamada (AC8): sem ela, uma URL digitada
errado mostra "não foi possível carregar a programação", que é uma mentira sobre o backend.

**9. `unaccent()` não é `IMMUTABLE`.** Ela não pode entrar em índice sem uma função wrapper. Com o
volume deste projeto **não existe índice para criar** — não invente um; se alguém tentar, o
Postgres recusa e o motivo é este.

**10. A rota `/eventos/cidades` declarada depois de um path param.** Não acontece hoje, porque não
há nenhum — acontece na Story 3.4. O comentário no código é para ela.

**11. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest`
falhar com `os error 4551`, chame pelo módulo: `uv run python -m pytest`.

**12. O banco de desenvolvimento é do Igor.** Ele tem eventos de conferência das Stories 2.4 a 3.1,
entre eles um de 2001 e um sem portaria. **Não apague nada, e não semeie evento novo** — semear é
decisão de produto dele.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      publico.py                 # +3 Query em /eventos, +GET /eventos/cidades
    schemas/
      evento.py                  # +PeriodoDaProgramacao
    services/
      evento.py                  # filtros em listar_programacao(), +listar_cidades_em_cartaz()
  migrations/versions/
    2026….._habilita_extensao_unaccent.py   # NOVO — a primeira que não cria tabela
  tests/
    test_programacao.py          # cresce
  README.md
frontend/
  src/
    lib/
      programacao.ts             # filtros + listarCidadesEmCartaz()
    app/(site)/
      page.tsx                   # +barra de busca, +chips, +3º estado vazio
      page.module.css            # +.barraBusca, .grupos, .chip, .chipAtivo, .rotuloOculto
  README.md
```

Não existe, e não deve passar a existir nesta story: `app/api/cliente.py`, `services/busca.py`,
componente `BarraDeBusca.tsx` em `components/` (ela é desta tela), coluna nova, índice novo,
paginação, ordenação escolhível, autocomplete, histórico de busca, `error.tsx`, teste automatizado
de frontend, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| Termo casa nome / local / cidade | `test_programacao.py` | 1 |
| `MARINA` e `marina` acham o mesmo | `test_programacao.py` | 2 |
| `sao paulo` acha `São Paulo`, e `SÃO` acha o gravado sem acento | `test_programacao.py` | 2 |
| `?q=%` com `100% Rock` no banco devolve **só ele** | `test_programacao.py` | 3 |
| `?q=` vazio e só espaços → programação inteira | `test_programacao.py` | 4 |
| `?q=` com 121 caracteres → `422` | `test_programacao.py` | 5 |
| `?cidade=` filtra; `cidade = NULL` fica fora dele | `test_programacao.py` | 6 |
| `semana` / `mes` / sem período → 1, 2 e 3 eventos | `test_programacao.py` | 7 |
| `?periodo=ontem` → `422` | `test_programacao.py` | 8 |
| Os três filtros juntos | `test_programacao.py` | 9 |
| **Rascunho continua fora, com termo que casaria** | `test_programacao.py` | 9 |
| **Evento passado continua fora, com termo que casaria** | `test_programacao.py` | 9 |
| `/eventos/cidades`: sem cookie, distintas, ordenadas, sem `null` | `test_programacao.py` | 10 |
| `/eventos/cidades` ignora rascunho, passado e `?q=` | `test_programacao.py` | 10 |
| Com busca ativa, o corpo tem **exatamente** as sete chaves | `test_programacao.py` | 12 |
| Com busca ativa, nenhuma palavra de estoque no texto da resposta | `test_programacao.py` | 12 |
| OpenAPI declara os três parâmetros e nenhum de segurança | `test_programacao.py` | 1, 8 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são oito caminhos — os da T8.

**Baseline: 231 testes passando** (Story 3.1).

### Inteligência das stories anteriores

**Da 3.1 — a story imediatamente anterior, e a base literal desta:**

- **O `agora` lido uma vez** já está escrito e comentado. O teto do período usa **o mesmo**; um
  segundo `datetime.now()` para calcular a janela é o mesmo defeito por outra porta.
- **O `unstable_rethrow` no `catch`** foi descoberto pelo log do `npm run build`, não por teste: o
  `cache: "no-store"` lança `DYNAMIC_SERVER_USAGE` para tirar a rota do estático, e o `try/catch`
  engolia. A função nova de cidades tem exatamente o mesmo risco.
- **A fila esgotada é `<div>` e não `<Link>` desativado** — o mesmo raciocínio vale para os chips:
  o elemento certo é o que descreve o comportamento, não o que se estiliza para parecer com ele.
- **`response_model` é a garantia, não a tela.** Três testes cobram isso na 3.1; esta story os repete
  **com filtro ativo**, porque um `WHERE` novo é exatamente o tipo de mudança em que um `setores`
  aparece "só para a próxima story usar".
- **O helper de teste `publicado: bool`** nasceu de um bug de fixture: `publicado_em=None` era ao
  mesmo tempo "não informei" e "é rascunho", e o teste passava por motivo errado. Ao acrescentar
  `cidade` e `local` ao helper, cuidado com o mesmo ponto cego.

**Da 2.4/2.2 — o molde da tela:** `<form method="get">`, escolha na URL, `URLSearchParams` para
montar destino, e o `maxLength` do `<input>` casando com o `max_length` da rota. Tudo o que esta
barra precisa já foi escrito uma vez, em `organizador/publicar/page.tsx`.

**Do code review da Epic 2:** *teto em campo que vem do usuário não é enfeite* — `capacidade`
estourando o int4 virava `500`. Aqui o campo que vem do usuário é o termo, e o teto é o
`max_length=120`; o que **não** tem teto natural é o `LIKE`, e é o AC3 que fecha isso.

**Da paleta (commit `e5ecf30`, 2026-08-11):** o acento único deixou de ser âmbar e virou
**`--neon` (`#ff4f9a`)**. O `epics.md` foi corrigido junto com esta story — o UX-DR1 é vinculante e
mandaria as próximas quatro epics escolherem o token errado. **O `DESIGN.md` continua escrevendo
"âmbar"** e não foi tocado: onde ele disser âmbar, leia neon. A fonte única dos valores é
`frontend/src/app/globals.css`.

[Fonte: _bmad-output/implementation-artifacts/3-1-ver-a-programacao.md · code-review-epic-2.md · frontend/src/app/globals.css:17-58]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `Query` com `max_length`, enum como parâmetro, `response_model=list[str]` |
| Pydantic | 2.13.4 | O enum do período no OpenAPI |
| SQLAlchemy | 2.0.51 | `or_`, `func.unaccent`, `ilike(..., escape=)`, `distinct()` |
| Alembic | 1.19.1 | `op.execute` numa migração escrita à mão |
| PostgreSQL | 16 | Extensão `unaccent` (contrib, já presente na imagem oficial) |
| Next.js | **16.3.0** | `searchParams` como `Promise`, `PageProps<"/">`, Server Component |
| React | 19 | Nenhuma ilha de cliente nova |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** A documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

### Escopo — o que NÃO fazer aqui

Chamada principal com arte e manchete (3.3) · página do evento e seus setores (3.4) · medidor ·
reserva e stepper (3.5 em diante) · paginação · ordenação escolhível · autocomplete · sugestão de
busca · histórico · índice de texto (`tsvector`, `pg_trgm`) · qualquer rota de escrita · qualquer
alteração nas rotas do organizador · teste automatizado de frontend.

Cinco tentações concretas:

- **"Já ponho um `pg_trgm` com índice, fica mais rápido."** Com dezenas de eventos, `ILIKE` sem
  índice é instantâneo, e um índice de trigrama é uma migração e um conceito a mais para explicar
- **"Já filtro enquanto digita, é só um `onChange`."** É a decisão que o Igor tomou ao contrário, e
  transforma a raiz numa ilha de cliente
- **"Já devolvo os setores, a 3.4 vai precisar."** É o AC12, e é o mesmo aviso da 3.1
- **"Aproveito e ponho a chamada principal, agora que a barra está lá."** É a Story 3.3, e ela tem
  cinco ACs só sobre quando a chamada **não** aparece
- **"Já conserto o filtro de `publicado_em` na lista do organizador."** Está no `deferred-work.md`
  com motivo escrito, e continua aberto de propósito

### Project Structure Notes

Esta é a **primeira migração deste projeto que não cria tabela**, e vale dizer isso no docstring
dela: ela declara um pré-requisito da consulta no mesmo lugar onde o schema é declarado. As três
anteriores criam `usuario`, `evento`/`setor` e `evento_portaria`, e alguém que abrir a pasta esperando
mais do mesmo precisa entender por que esta é diferente em uma linha.

É também a primeira vez que a rota pública recebe **entrada de gente**. Até aqui, tudo que o
visitante mandava para o backend era o endereço; agora ele manda texto, e é por isso que o teto de
120 caracteres e o escape do `LIKE` estão nos ACs em vez de ficarem implícitos. `publico.py`
continua sendo o router cujo critério de entrada é "não exige conta" — três `Query` não mudam isso,
e o docstring precisa continuar dizendo com todas as letras que nenhum deles é `Depends`.

No frontend, a raiz passa a ter **estado**, e ele mora na URL. É a mesma escolha que a tela de
publicar fez na Story 2.4 ("a escolha é navegação, não estado"), agora na tela mais visitada do
produto — e é o que mantém a raiz inteira no servidor depois de ganhar um campo de texto, dois
grupos de chips e um botão.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] — os três blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — o objetivo da epic e as stories vizinhas
- [Source: ARCHITECTURE-SPINE.md#Convenções] — Server Component por padrão; `"use client"` só onde há
  interação que exige o navegador
- [Source: ARCHITECTURE-SPINE.md#Convenções] — toda mudança de schema é migração Alembic versionada
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`; router não toca a
  `Session`
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade
- [Source: DESIGN.md#Colors] — regra do acento único. ⚠️ O documento escreve `ambar`; o token vivo é
  `--neon` desde a troca de paleta
- [Source: DESIGN.md#Components/botao] — mono 700 versalete, raio zero
- [Source: EXPERIENCE.md#Vazio] — "Nenhum show encontrado para essa busca.", sem ilustração e sem
  botão grande
- [Source: EXPERIENCE.md#Accessibility Floor] — todo campo com rótulo associado; foco visível
- [Source: EXPERIENCE.md#Responsive & Platform] — o que acontece abaixo de 900px
- [Source: mockups/proto-jornal-noturno.html:57-65, 276-282] — o CSS e o markup da `.barra-busca`
- [Source: backend/app/api/organizador.py:59-63] — `Query("", max_length=120)`, o precedente do teto
- [Source: backend/app/services/evento.py:285] — `listar_programacao`, a função que esta story amplia
- [Source: backend/tests/conftest.py:75] — `downgrade base` + `upgrade head` aplica a extensão no
  banco de teste
- [Source: frontend/src/app/(site)/organizador/publicar/page.tsx:44-135] — o molde do form GET
- [Source: frontend/src/lib/programacao.ts] — o módulo que ganha os filtros, com o comentário do
  `unstable_rethrow` já escrito
- [Source: frontend/src/app/globals.css:17-58] — os tokens da paleta nova
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, com a régua de cinco
  parágrafos por camada; git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída** — até cinco parágrafos por camada, e a
   raiz **não é tocada** nesta. Documentação não bloqueia o commit: aplique o código, rode a suíte,
   mostre o resultado, **depois** escreva
3. **Decisão de produto ou de modelagem é do Igor.** As três desta story estão respondidas e as nove
   suposições estão declaradas. Se aparecer uma quarta — filtro a mais, campo a mais, tela a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os arquivos novos foram rastreados (T8)
8. **O code review é ao fim da Epic 3**, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **A raiz recebe decisão nova?** Escrevi a story para **não** tocar o `README.md` da raiz: a régua
   diz que entra ali só o que faria quem avalia ver *um sistema diferente*, e a decisão de produto
   desta epic — "a programação pública é o que ainda vai acontecer" — já entrou na 3.1. A defesa do
   contrário existe: *a busca acontece no banco e a URL é o estado* muda o que o avaliador vê na
   barra de endereço e mantém a raiz fora do cliente. Se você achar que passa na régua, é um bloco
   de três partes, e o material está na tabela de decisões acima.
2. **`7 DIAS`/`30 DIAS` contra `Esta semana`/`Este mês`.** Você aprovou a opção escrita com os
   rótulos de calendário; eu escrevi os ACs com janelas corridas, porque "esta semana" numa
   sexta-feira significa dois dias. Trocar os rótulos são duas strings; trocar a **regra** para o
   calendário é o cálculo do teto no service. Diga qual dos dois você quer antes do dev.
3. **A extensão `unaccent` precisa subir na Railway.** O `Pre-deploy Command` de lá já é
   `alembic upgrade head`, então a migração roda sozinha no merge — mas se o Postgres da Railway
   recusar `CREATE EXTENSION` por permissão, **o deploy inteiro falha**, não só a busca. Vale
   confirmar no painel antes do merge da epic. Eu não tenho acesso a ele.
4. **Nenhum evento é semeado, e agora existe uma busca para provar.** Numa máquina limpa o avaliador
   abre a raiz, vê o estado vazio e uma barra de busca que não tem o que buscar. Continua sendo
   decisão de produto sua semear um show — a pergunta é a mesma da 3.1, com um motivo a mais.
5. **A cidade continua anulável** (desde a 2.3). Evento sem cidade some de qualquer filtro de cidade
   — o que está certo —, mas também não gera chip. Se você quiser exigir cidade na publicação, é uma
   linha no schema de entrada, e é decisão sua.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (1M context) — `claude-opus-5[1m]`.

### Debug Log References

- `uv run alembic revision -m "habilita extensao unaccent"` → `06c1ad5ac276`, com
  `down_revision = c7cb4a29b7f3` conferido no arquivo gerado.
- `uv run alembic upgrade head` no banco de desenvolvimento: `c7cb4a29b7f3 -> 06c1ad5ac276`, sem
  erro de permissão. **A extensão subiu.**
- `uv run python -m pytest -q` (Compose no ar, sem rede): **263 passed**, de 231 na 3.1.
- `npx tsc --noEmit`, `npm run lint` e `npm run build`: os três limpos. `/` continua marcada `ƒ` no
  relatório de rotas do build — nenhuma ilha de cliente entrou.
- Busca por `NEXT_PUBLIC` em `frontend/src/`: zero ocorrências (AD-2).
- Conferência da API contra o **banco de desenvolvimento do Igor** (4 eventos reais, 2 cidades),
  com `uvicorn` no ar: `?q=sao paulo` e `?q=SÃO PAULO` acham o mesmo evento; `?q=cavern` casa pelo
  campo `local`; `?cidade=São Paulo` acha e `?cidade=sao paulo` devolve `[]` (igualdade exata);
  `?q=%` devolve `0`, não os 4; `?periodo=xyz` e `?q=` com 121 caracteres devolvem `422`;
  `/eventos/cidades?q=marina` devolve as duas cidades — ela ignora o termo.
- Conferência do HTML renderizado por `next dev`, em `/?q=rio&cidade=Rio+de+Janeiro`: o form é
  `method="get" action="/"`, o `<label for="q">` existe, `<input type="hidden" name="cidade">`
  carrega o filtro ativo, os seis chips são `<a>` com `aria-current="true"` só nos dois ativos, o
  termo `q=rio` viaja em todos os `href`, `São Paulo` sai como `S%C3%A3o+Paulo` — codificado **uma**
  vez, sem o `%2520` da Story 2.4 — e não há nenhuma marca de ilha de cliente.
- Os três estados de vazio, conferidos no HTML: `/?q=zzzzzz` traz "Nenhum show encontrado para essa
  busca." **com** o link "Ver toda a programação" e **com** a barra ainda na tela; `/?periodo=xyz`
  traz as 4 filas, sem frase de erro, com o chip `Todos` marcado apontando para `/`; e com o
  `uvicorn` derrubado, `/?q=rio` traz "Não foi possível carregar a programação agora.", a barra
  intacta, zero chips de cidade e os 3 de período.
- ⚠️ **Duas conferências ficaram para o Igor**, a pedido dele durante esta sessão: o comportamento
  abaixo de 900px e a ordem do Tab com o contorno de foco. Elas são visuais, e ele testa mais rápido
  com a tela já aberta. A terceira que continua dele é a de sempre: conferir que os arquivos novos
  entraram no índice do git.

### Completion Notes List

**Uma decisão foi consultada antes de escrever código** (*Perguntas em aberto* nº 2): o Igor
escolheu **janelas corridas com os rótulos `7 DIAS` e `30 DIAS`**, que é o que os 21 ACs já
descreviam. `semana` é `data_hora < agora + 7 dias` e `mes` é `< agora + 30 dias`, com o **mesmo**
`agora` do corte de eventos passados.

**Um teste da Story 3.1 precisou mudar uma linha, e é a única exceção ao "nenhum teste antigo
muda".** `test_a_rota_publica_nao_declara_parametro_de_seguranca` afirmava
`rota.get("parameters", []) == []`, que era a forma exata de escrever "nenhum parâmetro" enquanto a
rota não tinha nenhum — e é logicamente incompatível com a T5, que exige que ela passe a declarar
três. A invariante protegida não mudou: o que não pode existir ali é parâmetro **de sessão**. A
asserção agora é `{p["in"] for p in parameters} <= {"query"}`, que continua caindo se alguém
acrescentar um `Depends` de cookie ou header — e agora continua valendo **depois** de a rota ganhar
filtros, que é exatamente quando alguém teria a chance de errar. O motivo está escrito no docstring
do próprio teste. Os outros doze testes da 3.1 não foram tocados.

**Três defeitos silenciosos que os testes fecham**, e nenhum deles aparece na tela: `?q=%` devolvendo
a programação inteira com cara de resultado (AC3, escape do `LIKE`); `?q=\` derrubando a consulta com
`invalid escape sequence`, ou seja `500` para uma busca digitada por engano; e `unaccent` só na
coluna, que faria quem digita **com** acento não achar um evento gravado **sem** — o teste que cobre
isso é o `test_termo_com_acento_acha_o_evento_gravado_sem_acento`.

**O helper `_evento_gravado` ganhou `local` e `cidade` com os valores antigos como default**, que é o
que permitiu os treze testes da 3.1 continuarem gravando "Espaço Unimed" em "São Paulo" sem saber que
os campos passaram a ser escolhíveis. `cidade=None` é repassado cru, sem nenhum `cidade or "São
Paulo"`: aqui o `None` é valor de domínio, não ausência de argumento — o oposto do ponto cego que fez
`publicado_em` virar `publicado: bool` na 3.1.

**Um conserto da Story 3.1 entrou junto, decidido pelo Igor ao ver a tela: a fila não mostrava mês
nem ano.** A 3.1 devolvia só `diaDaSemana`, `dia` e `hora`, com um docstring justificando a omissão —
"a programação pública só mostra o que ainda vai acontecer, então o ano é sempre o mesmo ou o
próximo". As duas metades caíram na primeira tela com quatro eventos reais: a coluna mostrava `14`,
`12` e `23`, que são agosto, setembro e novembro, e a âncora de leitura da lista não dizia qual show
vinha antes; e "o mesmo ou o próximo" ainda são **dois** anos — havia um show de setembro de 2026 e
outro de setembro de 2027, idênticos na tela. `partesDaFilaPublica` ganhou `mesEAno`, que entra entre
o dia e a hora em mono versalete, **sempre com o ano**: condicioná-lo a "difere do ano atual" criaria
duas formas para a mesma coluna, decididas pelo relógio. A coluna de 900px foi de 68px para 76px, ou
o ano quebrava para baixo do mês. O docstring que justificava a omissão foi reescrito no
`formato.ts`, porque ele estava argumentando a favor de um defeito. **Vai no commit da 3.2**, e o
Igor decidiu assim sabendo que é conserto de story anterior: os dois arquivos de tela carregam
mudança das duas coisas ao mesmo tempo, e separar exigiria dividir hunk.

**Um desvio consciente do AC16, decidido pelo Igor depois de ver a tela.** O AC pedia dois grupos de
chips — `QUANDO` e `ONDE` —, e a cidade virou um `<select name="cidade">` dentro do form. O motivo:
o período é um conjunto **fechado** (sempre três opções) e a cidade é um conjunto **aberto**, que
cresce com o catálogo. Com duas cidades os chips pareciam um filtro que não filtra; com quinze seriam
três linhas de botões empurrando a programação para baixo da dobra — a mesma classe de defeito nas
duas pontas. O `<select>` mora dentro do form que já existia, então **não custa uma linha de
JavaScript**: escolher a cidade e apertar `Buscar` submete os dois juntos, a raiz continua Server
Component (`/` segue `ƒ` no build) e o estado continua na URL. O preço, único e conhecido: a cidade
deixou de filtrar num clique. A alternativa que devolveria o clique — `onChange` com
`useRouter().push()` — foi descartada na mesma conversa, porque é o AC14 ao contrário. O
`<input type="hidden" name="cidade">` saiu junto: o `<select>` já é campo do form e se submete
sozinho. A regra de "só com duas cidades ou mais" continua valendo, agora sobre o seletor.

⚠️ **Os ACs 16 e 18 não foram reescritos** — a regra do projeto é que a story implementada não volta
a ser editada fora do Dev Agent Record. O que vale é este registro e o `frontend/README.md`.

**Um defeito que só a tela pegou, e que o Igor pegou:** o `Botao` é `width: 100%` desde a Story 1.4,
porque nasceu como ação primária de formulário empilhado. Solto dentro do flex da barra, esse `100%`
resolve contra a linha inteira e espreme o `<input>` a zero — a barra virava um botão rosa de ponta a
ponta, sem lugar para digitar. O `organizador/publicar/page.tsx` já tinha resolvido isso envolvendo o
botão num `<div>` de largura fixa, e eu usei o componente sem o invólucro. Corrigido com
`.botaoBusca { flex-shrink: 0; width: 150px }` (104px abaixo de 900px, encolhendo o botão e não o
campo), com o motivo escrito nos dois arquivos. Nenhum teste automatizado pegaria isso: o HTML
renderizado estava correto, o defeito era só de layout.

**Nada fora do escopo.** Nenhum modelo, coluna, tabela, índice, código de erro ou dependência novos;
`EventoNaProgramacao` não ganhou nem perdeu campo; `selectinload` e a derivação de
`preco_minimo_centavos`/`esgotado` (AD-13) não mudaram uma linha; nenhum `"use client"` entrou; o
`README.md` da raiz não foi tocado (AC21). O único arquivo fora da lista prevista pela story é o
`docs/` — nenhum: a lista bateu.

### File List

**Novo**

- `backend/migrations/versions/20260811_06c1ad5ac276_habilita_extensao_unaccent.py`

**Modificado**

- `frontend/src/lib/formato.ts` — ⚠️ conserto da Story 3.1 (mês e ano na fila)
- `backend/app/schemas/evento.py`
- `backend/app/services/evento.py`
- `backend/app/api/publico.py`
- `backend/tests/test_programacao.py`
- `backend/README.md`
- `frontend/src/lib/programacao.ts`
- `frontend/src/app/(site)/page.tsx`
- `frontend/src/app/(site)/page.module.css`
- `frontend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-2-buscar-e-filtrar-a-programacao.md`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | **Conserto da Story 3.1 pedido pelo Igor:** a fila da programação mostrava só o dia (`14`, `12`, `23`), sem mês nem ano — a coluna que deveria ser a âncora de leitura da lista não dizia qual show vinha antes, e dois setembros de anos diferentes ficavam idênticos. `partesDaFilaPublica` ganhou `mesEAno`, sempre com o ano, e o docstring da 3.1 que justificava a omissão foi reescrito. É conserto de story anterior entrando neste commit |
| 2026-08-11 | Ajustes depois da conferência do Igor na tela, os dois registrados no Dev Agent Record: o `Botao` sem invólucro de largura fixa espremia o campo de busca a zero (ele é `width: 100%` desde a 1.4), e **o filtro de cidade deixou de ser chip e virou `<select>` dentro do form** — decisão dele, pelo argumento de conjunto fechado (período, sempre três) contra conjunto aberto (cidade, cresce com o catálogo). O seletor não custa JavaScript nenhum: está no form que já existia, e `Buscar` submete termo e cidade juntos; `/` continua `ƒ`. Desvia do AC16, que não foi reescrito |
| 2026-08-11 | Story 3.2 implementada. A migração `06c1ad5ac276` habilita a extensão `unaccent` — a primeira deste projeto que não cria tabela —, `listar_programacao` ganhou os três filtros no `where` (termo escapado contra os curingas do `LIKE`, cidade por igualdade exata, período em janelas corridas de 7 e 30 dias sobre o mesmo `agora` do corte de passados), nasceu `GET /eventos/cidades` declarada antes de qualquer path param, e a raiz ganhou barra de busca em `<form method="get">`, dois grupos de chips como `<Link>` e a terceira frase de lista vazia — tudo sem uma linha de `"use client"`. Decisão consultada e respondida pelo Igor: janelas **corridas** com os rótulos `7 DIAS`/`30 DIAS`. A suíte foi de 231 para **263 testes**; `npm run build`, `tsc --noEmit` e `lint` limpos, com `/` ainda marcada `ƒ`. Uma linha de um teste da 3.1 precisou mudar — `parameters == []` virou "todo parâmetro é `in: query`", porque a primeira frase é logicamente incompatível com a rota passar a ter filtros, e a invariante protegida (nenhum parâmetro de sessão) continua cobrada |
| 2026-08-11 | Story 3.2 criada e contextualizada. Três decisões do Igor incorporadas: **a peneira roda no `where` do Postgres, com a busca na URL** (`GET /eventos?q=&cidade=&periodo=` e `<form method="get">`), e não filtrando em JavaScript uma lista já carregada — a raiz continua Server Component e `/?q=marina` é um link que se compartilha; **período e cidade, os dois vindos do banco**, com `GET /eventos/cidades` alimentando os chips para que nenhum deles ofereça uma cidade sem show; e **a busca ignora acento**, via extensão `unaccent` do Postgres habilitada por migração — a primeira migração deste projeto que não cria tabela —, em vez de um `translate()` com mapa de letras à mão. Vinte e um ACs escritos sobre os três blocos do `epics.md`, entre eles o AC3, que é a consequência menos óbvia de mandar texto de gente para dentro de um `LIKE`: `%` e `_` são curingas, e sem escape um `?q=%` devolve a programação inteira parecendo resultado. Nove suposições declaradas (rótulos `7 DIAS`/`30 DIAS` com janelas corridas, a rota de cidades em `/eventos/cidades`, os chips em dois grupos com kicker, o grupo de cidade só com duas ou mais, casamento por trecho, cidade por igualdade exata, `listarCidadesEmCartaz` engolindo a falha, sem paginação e sem contador de resultados) e cinco perguntas registradas para o Igor — entre elas a confirmação de que o Postgres da Railway aceita `CREATE EXTENSION`, porque lá a falha derruba o deploy inteiro e não só a busca |
