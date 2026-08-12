---
baseline_commit: "d7469af — `docs: confirma a extensao unaccent no Postgres da Railway`, na branch `Epic-3--Descoberta-e-compra`. Migração `head`: 06c1ad5ac276 (`habilita_extensao_unaccent`). Suíte: 263 testes passando (Story 3.2). ⚠️ Não executei git — este carimbo veio do estado informado no início da sessão; confira antes de começar."
---

# Story 3.3: Chamada principal na programação

Status: review

Epic 3 — Descoberta e compra · **A terceira story da epic, e a que faz a raiz virar capa.** A 3.1
desenhou a fila, a 3.2 deu a peneira; esta acrescenta o bloco grande no topo — o elemento que o
`DESIGN.md` chama de `chamada-principal` e que, nas palavras dele, **é o que faz a tela parecer
jornal: sem ela, a listagem vira só uma tabela**.

São uma rota pública nova (`GET /eventos/destaque`), um schema novo (`EventoEmDestaque`), uma
função de service e um bloco de duas colunas na raiz. **Nenhuma migração, nenhuma coluna, nenhum
modelo novo, nenhuma dependência nova** — e `GET /eventos` não muda uma vírgula.

É também a primeira vez que a **arte** do evento atravessa para o lado público. Ela já está gravada
em `evento.imagem_url` desde a Story 2.4, copiada da Ticketmaster no ato da publicação, e ficou
deliberadamente fora do contrato da programação até aqui (`EventoNaProgramacao`, Story 3.1) — a
fila de quatro colunas não tem imagem, e campo que nenhuma tela lê é campo que ninguém sabe se
está certo.

## Acceptance Criteria

1. **Given** eventos publicados e futuros no banco
   **When** eu chamo `GET /eventos/destaque` **sem nenhum cookie de sessão**
   **Then** recebo `200` com **um** objeto: o evento de **menor `data_hora`** entre os que estão
   publicados e ainda vão acontecer
   **And** a rota é **pública por assinatura**: nenhum `Depends(exigir_papel(...))`, nenhuma
   dependência de sessão, e **nenhum parâmetro** — nem `q`, nem `cidade`, nem `periodo`
   **And** o desempate é `Evento.id`, o mesmo de `listar_programacao`: dois shows no mesmo horário
   não podem trocar de lugar entre requisições

2. **Given** que a rota tem um path fixo e a Story 3.4 vai pendurar `/eventos/{id}` no mesmo router
   **When** eu leio o `publico.py`
   **Then** `/eventos/destaque` está declarada **antes** de qualquer rota com path param, ao lado da
   `/eventos/cidades`, e há comentário dizendo por quê
   **And** ⚠️ com `/eventos/{id}` em cima, uma chamada a `/eventos/destaque` tentaria ler
   `"destaque"` como UUID e devolveria `422` — erro de validação para um endereço que existe

3. **Given** um banco sem nenhum evento publicado e futuro
   **When** eu chamo a rota
   **Then** recebo `200` com o corpo `null` — **nunca `404`**, e nunca `204`
   **And** é a mesma decisão da 3.1: "não há show em cartaz" é resposta sobre o produto, não
   endereço inexistente. `204` está fora porque ele **não tem corpo**, e `resposta.json()` do lado
   da tela estouraria num `catch` que existe para falha de rede

4. **Given** um evento em rascunho (`publicado_em IS NULL`) marcado para amanhã, e um publicado
   marcado para daqui a um mês
   **When** eu chamo a rota
   **Then** recebo o **publicado**
   **And** o mesmo vale para evento no passado: o recorte é **idêntico** ao da `listar_programacao`
   (`publicado_em IS NOT NULL` **e** `data_hora >= agora`), e `agora` é lido **uma vez** no início do
   service

5. **Given** o próximo evento da programação
   **When** eu inspeciono o corpo da resposta
   **Then** ele tem **exatamente oito chaves**: `id`, `nome`, `data_hora`, `local`, `cidade`,
   `imagem_url`, `setores`, `esgotado`
   **And** `setores` é uma **lista de nomes** (`list[str]`) — nunca objetos, nunca `capacidade`,
   `vendidos` ou `preco_centavos`
   **And** `preco_minimo_centavos` **não entra**: a ficha que o Igor escolheu não mostra preço, e
   campo sem tela que o leia é o que a 3.1 recusou (ver *Perguntas em aberto* nº 1)
   **And** `publicado_em`, `origem_externa_id` e `organizador_id` também não entram

6. **Given** o texto inteiro da resposta desta rota
   **When** eu procuro estoque
   **Then** não aparecem `capacidade`, `vendidos`, `preco_centavos`, `publicado_em`,
   `origem_externa_id` nem `organizador_id` (UX-DR7, AD-13)
   **And** ⚠️ **a palavra `setores` agora é uma chave legítima aqui** — o teste que varre o texto
   atrás de palavras proibidas **não pode** ser copiado da 3.1 sem tirar `setores` da lista. Nome de
   setor não é estoque; contagem é

7. **Given** um evento cujos setores são `VIP`, `Pista` e `Camarote`
   **When** eu leio `setores` na resposta
   **Then** recebo `["Camarote", "Pista", "VIP"]` — em ordem alfabética, que é a ordem que o
   `relationship` já garante (`order_by="Setor.nome"`, Story 2.3)
   **And** **todos** os setores entram, inclusive os esgotados: a ficha diz o que o show **tem**,
   não o que sobrou (suposição declarada)

8. **Given** um evento cujos setores estão todos esgotados
   **When** ele é o próximo da programação
   **Then** ele **continua sendo o destaque**, com `esgotado: true` (decisão do Igor)
   **And** a derivação é `setor.vendidos < setor.capacidade`, lida do próprio setor — **é proibido**
   derivar disponibilidade com `COUNT` sobre reserva ou ingresso, em qualquer camada (AD-13)
   **And** evento **sem setor nenhum** (possível por `psql`, e existe no banco de desenvolvimento do
   Igor) também é `esgotado: true`, e não quebra a rota

9. **Given** a rota `GET /eventos` e os 263 testes que já existem
   **When** eu rodo a suíte depois desta story
   **Then** **nenhum deles precisa mudar**: `EventoNaProgramacao` não ganha nem perde campo, o
   `response_model` da programação é o mesmo, e `imagem_url` **continua fora** dela
   **And** se algum teste antigo quebrar, algo saiu do escopo — pare e diga

10. **Given** a raiz `/` sem nenhum filtro
    **When** eu a abro com eventos publicados
    **Then** vejo a chamada principal **acima** do título `Programação`, em duas colunas: arte à
    esquerda, e à direita kicker com a data por extenso, manchete em serifada e a ficha
    **And** o kicker leva **o dia da semana junto** — `SEXTA, 15 DE AGOSTO DE 2026, 22H30` —, como o
    protótipo o escreve: numa capa de show, "sexta" é a informação que situa antes do número
    **And** ⚠️ isso **não** é a `dataPorExtenso`, que não devolve o dia da semana. É uma função nova,
    e ela nasce em `lib/formato.ts` ao lado das outras — nunca inline na tela, porque é lá que o
    `FUSO` fixo mora (achado do code review da Epic 2: a mesma publicação apareceu com duas datas)
    **And** existe **uma só por tela** (UX-DR4)
    **And** a página continua **Server Component, sem uma linha de `"use client"`**

11. **Given** a chamada principal
    **When** eu leio a ficha de três dados
    **Then** ela traz **`CASA`**, **`CIDADE`** e **`SETORES`** — nesta ordem, rótulo em mono
    versalete e valor em serifada (decisão do Igor)
    **And** os setores aparecem como frase: `Pista, VIP e Camarote` — vírgulas e um `e` antes do
    último, e não uma lista com marcador
    **And** a linha `CIDADE` **some** quando `cidade` é `null` (anulável desde a 2.3) — a ficha fica
    com dois dados em vez de mostrar um rótulo sobre o vazio
    **And** ⚠️ **não há contagem de ingressos em lugar nenhum da ficha** (UX-DR7)

12. **Given** a chamada principal
    **When** eu comparo com o protótipo
    **Then** **não existe standfirst** — a linha em itálico entre a manchete e a ficha não é
    renderizada (decisão do Igor)
    **And** o motivo é que o `Evento` não tem campo de texto livre: nem coluna, nem entrada no
    formulário de publicação, nem nada que a Ticketmaster devolva. Uma frase montada com os mesmos
    dados que o kicker e a ficha já mostram é o anti-padrão nº 5 do `DESIGN.md` ("soa gerada")
    **And** ⚠️ **isto não vai para README nenhum** (instrução do Igor): a diferença é pequena e o
    registro fica aqui

13. **Given** o evento em destaque
    **When** eu olho a fila de `Programação` logo abaixo
    **Then** ele **não aparece de novo** — a lista começa no segundo evento (decisão do Igor)
    **And** o corte é por `id`, comparando o destaque com os itens da programação, e não por
    "pular o primeiro": as duas rotas são consultas independentes, e assumir que o primeiro item da
    lista é o destaque é uma coincidência que um filtro futuro desfaz

14. **Given** um banco com **um único** evento publicado e futuro
    **When** eu abro a raiz
    **Then** vejo a chamada e **nada** abaixo dela: nem o título `Programação`, nem a frase de vazio
    **And** ⚠️ "Nenhum show em cartaz por enquanto" embaixo de uma capa que mostra um show seria a
    tela se contradizendo em duas linhas

15. **Given** o evento em destaque com ingresso disponível
    **When** eu clico nele
    **Then** o bloco **inteiro** é um `<Link>` para `/eventos/{id}` — o mesmo padrão da fila
    (`fila-listagem`: a fila inteira é o alvo), e o mesmo destino que só nasce na Story 3.4
    **And** **não há botão "Ver setores"** como no protótipo: dois alvos para o mesmo destino no
    mesmo bloco (suposição declarada)
    **And** quando `esgotado` é `true`, o bloco é um `<div>` e **não** um `<Link>` — nunca um link
    desativado por CSS, pelo mesmo motivo escrito na 3.1: `pointer-events: none` tira o clique do
    mouse e deixa o elemento no Tab

16. **Given** o evento em destaque esgotado
    **When** eu o vejo
    **Then** há um selo **`ESGOTADO`** vazado em `var(--brasa)` sobre a arte, no canto superior
    esquerdo (a anatomia do `.lead-selo` do protótipo)
    **And** a informação **não é dada só por cor** (UX-DR9): a palavra está escrita, e o bloco não
    responde ao hover porque não é link
    **And** **nenhum outro selo existe**: `Destaque da semana` do protótipo fica fora — o destaque é
    o próximo show, não uma curadoria, e o rótulo mentiria num show marcado para daqui a três meses

17. **Given** um evento com `imagem_url = null` (a coluna é anulável desde a 2.3)
    **When** ele é o destaque
    **Then** o lugar da arte fica com um bloco em `var(--breu2)` **do mesmo tamanho**, e o resto do
    bloco não se move — a grade não pode dançar conforme o evento tem ou não tem foto
    **And** é a mesma solução da miniatura do catálogo (`FormularioPublicacao.tsx:382-387`)

18. **Given** a arte do evento
    **When** eu inspeciono o HTML
    **Then** ela é um `<img>` comum com `alt=""`, e **não** o `next/image`
    **And** ⚠️ o motivo é concreto: não existe `images.remotePatterns` no `next.config.ts`, e o
    `next/image` **estoura em tempo de execução** com host não declarado. O host vem de uma API
    externa e não é nosso para prometer — declarar `s1.ticketm.net` hoje é uma configuração que
    quebra calada no dia em que a Discovery servir de outro domínio. O precedente é a miniatura do
    catálogo, com o mesmo `eslint-disable-next-line @next/next/no-img-element`
    **And** `alt=""` porque a arte é **decorativa**: o nome do artista está escrito ao lado dela, em
    serifada 46px — um `alt` com o mesmo nome faria o leitor de tela anunciar o show duas vezes

19. **Given** uma busca ou um filtro ativo (`?q=`, `?cidade=` ou `?periodo=`)
    **When** eu abro a raiz
    **Then** a chamada **não é renderizada** — a tela vira lista pura (decisão do Igor)
    **And** ⚠️ a chamada nem sequer é **buscada**: com filtro ativo, `obterDestaque()` não é chamada.
    Pagar uma ida à rede por um resultado que a tela vai jogar fora é o tipo de desperdício que
    ninguém percebe depois de escrito
    **And** os três estados de lista vazia da 3.2 continuam **exatamente** como estão

20. **Given** que `GET /eventos/destaque` está fora do ar (ou devolveu erro)
    **When** eu abro a raiz
    **Then** a tela mostra a programação normalmente, **sem** a chamada — sem frase de erro e sem
    espaço reservado
    **And** `obterDestaque()` devolve `null` em qualquer falha e **nunca levanta**, com
    `unstable_rethrow(erro)` como **primeira linha do `catch`** — o motivo inteiro já está escrito
    no módulo desde a 3.1, e vale igual aqui
    **And** as duas buscas da tela continuam em `Promise.all` — agora três, e nenhuma depende da
    outra

21. **Given** uma tela abaixo de 900px
    **When** eu vejo a chamada
    **Then** arte e texto **empilham numa coluna só, a arte acima** (UX-DR6)
    **And** a ficha de três dados quebra em linha **sem cortar nenhum valor**
    **And** nada rola na horizontal, e os fios continuam de ponta a ponta

22. **Given** a chamada principal inteira
    **When** eu a inspeciono
    **Then** **sem card, sem sombra, sem raio** (UX-DR3), fio de 1px fechando o bloco embaixo
    **And** **nenhum hex novo** entra no `page.module.css` — só `var(--token)`. O degradê da arte é
    `linear-gradient(to top, var(--breu), transparent 65%)`, e não os `rgba(14,13,12,…)` do
    protótipo
    **And** o recuo lateral de **12px** é o mesmo de `.barraBusca`, `.secTitulo`, `.fila`, `.aviso` e
    `.vazio` — os seis andam juntos, e é isso que mantém os fios correndo de ponta a ponta

23. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira e os **263** testes anteriores continuam verdes
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos, e `/` continua
    marcada `ƒ` no relatório de rotas

24. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta, na seção `## Programação pública` que já existe: a rota
    de destaque, **por que ela é uma rota própria** em vez de um campo na lista, o `null` com `200`, e
    o que `setores` carrega (nomes, não estoque) — além do número novo da suíte
    **And** `frontend/README.md` documenta, em `## A raiz: a programação`: a chamada como bloco
    único, o corte do destaque na fila, e por que a arte é `<img>` e não `next/image`
    **And** os dois respeitam a régua de camada do `CLAUDE.md`: **no máximo cinco parágrafos**, na
    seção temática que já existe, sem tabela nova e sem subseção nova
    **And** `README.md` da **raiz não é tocado** nesta story — ver *Perguntas em aberto* nº 3

> **De onde vem cada critério.** O `epics.md` traz **quatro** blocos para a Story 3.3: a chamada com
> arte, kicker, manchete, standfirst e ficha de três dados (UX-DR4); uma só por tela e sem contagem
> de ingressos; nenhuma chamada quando não há evento publicado; e o empilhamento abaixo de 900px
> (UX-DR6). Eles viraram os ACs **10/11**, **11**, **14** e **21**.
>
> Todo o resto é decisão do Igor (tabela abaixo) ou consequência técnica dela: a rota própria em vez
> do campo na lista (ACs 1–9), o standfirst que não existe (AC12), o destaque saindo da fila (ACs 13
> e 14), a chamada sumindo com filtro (AC19) e o esgotado continuando na capa (ACs 8, 15 e 16).

## Tasks / Subtasks

- [x] **T1. `app/schemas/evento.py` — o schema da chamada** (AC: 5, 6, 7)
  - [x] `class EventoEmDestaque(BaseModel)` com `id`, `nome`, `data_hora`, `local`, `cidade`,
        `imagem_url`, `setores: list[str]`, `esgotado: bool`
  - [x] **Sem `from_attributes`**, como o `EventoNaProgramacao` e pelo mesmo motivo: `setores` de
        nomes e `esgotado` não são atributos do `Evento`, e declarar a conversão prometeria uma
        leitura que não acontece
  - [x] Docstring com as três coisas que ele **recusa** e por quê: nada de `capacidade`/`vendidos`
        (UX-DR7), nada de `preco_minimo_centavos` (a ficha escolhida não mostra preço), nada de
        `publicado_em`/`origem_externa_id`/`organizador_id`
  - [x] Docstring dizendo por que `setores` é `list[str]` e não `list[SetorSaida]`: a ficha quer os
        nomes, e `SetorSaida` carrega `capacidade`, `vendidos` e `preco_centavos` — devolvê-lo aqui
        seria o UX-DR7 caindo por reuso de schema
  - [x] ⚠️ `EventoNaProgramacao` **não muda**: nem ganha, nem perde campo (AC9)

- [x] **T2. `app/services/evento.py` — o destaque** (AC: 1, 3, 4, 7, 8)
  - [x] `obter_destaque(sessao) -> EventoEmDestaque | None`
    - [x] `agora = datetime.now(timezone.utc)` lido **uma vez**
    - [x] Mesmo recorte da `listar_programacao`: `publicado_em IS NOT NULL` **e**
          `data_hora >= agora`
    - [x] `.order_by(Evento.data_hora, Evento.id).limit(1)` e
          `.options(selectinload(Evento.setores))`
    - [x] `sessao.scalars(...).first()`; `None` → devolve `None`
    - [x] `esgotado` derivado como na `listar_programacao`: `not [s for s in evento.setores if
          s.vendidos < s.capacidade]` (AD-13). Evento sem setor nenhum cai em `True`
    - [x] `setores=[s.nome for s in evento.setores]` — a ordem alfabética já vem do `relationship`
    - [x] Docstring: **por que uma consulta própria e não `listar_programacao()[0]`** — a de cima
          carrega três filtros e um laço de derivação de preço sobre a programação inteira, e o
          destaque quer uma linha. `LIMIT 1` no banco é a diferença entre ler um evento e ler todos
          para descartar todos menos um
    - [x] Docstring: **por que o esgotado continua sendo destaque** (decisão do Igor) — mesma regra
          da fila da 3.1: show esgotado é informação, não ruído

- [x] **T3. `app/api/publico.py` — a terceira rota pública** (AC: 1, 2, 3)
  - [x] `@router.get("/eventos/destaque", response_model=EventoEmDestaque | None)`, **sem parâmetro
        nenhum** além de `sessao: Session = Depends(obter_sessao)`
  - [x] Declarada **ao lado da `/eventos/cidades`**, antes de qualquer rota com path param, com
        comentário no mesmo espírito do que já está lá (a Story 3.4 é quem vai exercitar isso)
  - [x] Docstring: por que `null` com `200` e não `404`, e por que não `204` (o corpo vazio quebraria
        o `resposta.json()` da tela)
  - [x] `app/main.py` **não muda**: o router já está incluído

- [x] **T4. Testes do backend** (AC: 1–9, 23)
  - [x] Em `tests/test_programacao.py`, reusando `_evento_gravado` — ⚠️ ele **precisa ganhar
        `imagem_url`** com default (`None`), sem trocar a assinatura de quem já chama
  - [x] Sem cookie → `200`; logado como cliente → corpo idêntico
  - [x] O destaque é o de **menor `data_hora`**, e não o primeiro inserido (grave o mais distante
        primeiro, de propósito)
  - [x] Rascunho não vira destaque, mesmo sendo o mais próximo
  - [x] Evento passado não vira destaque, mesmo sendo o mais próximo
  - [x] Banco sem evento publicado e futuro → `200` com corpo `null` (**e não `404`**)
  - [x] O corpo tem **exatamente as oito chaves** (AC5)
  - [x] ⚠️ Varredura de palavras proibidas no texto da resposta **sem `setores` na lista** — e com um
        comentário dizendo por quê, ou a próxima pessoa "conserta" o teste (AC6)
  - [x] `setores` vem em ordem alfabética, só com nomes, e inclui o esgotado (AC7)
  - [x] Todos os setores esgotados → `esgotado: true`, e ele **continua** sendo o destaque
  - [x] Evento sem setor nenhum → `esgotado: true`, sem quebrar
  - [x] `imagem_url = None` → `null` na resposta
  - [x] Empate de `data_hora` → desempate estável por `id` (grave dois no mesmo instante e chame
        duas vezes)
  - [x] OpenAPI: a rota **não declara parâmetro nenhum** — nem de query, nem de segurança
  - [x] ⚠️ **Nenhum teste antigo deve precisar mudar** (AC9). Se algum quebrar, pare e diga

- [x] **T5. `src/lib/programacao.ts` — o tipo e a busca** (AC: 20)
  - [x] `export type EventoEmDestaque` espelhando as oito chaves, com `imagem_url: string | null`,
        `cidade: string | null` e `setores: string[]`
  - [x] `obterDestaque(): Promise<EventoEmDestaque | null>` — `cache: "no-store"`, `null` em qualquer
        falha, sem `headers` e sem `cabecalhoDeSessao()`
  - [x] ⚠️ `unstable_rethrow(erro)` como **primeira linha** do `catch`
  - [x] ⚠️ `resposta.json()` pode devolver `null` legitimamente (AC3) — e isso **não** é falha: o tipo
        de retorno já cobre, e não pode haver nenhum `?? { estado: "indisponivel" }` transformando
        "não há show em cartaz" em erro
  - [x] Comentário dizendo por que ela devolve `null` em vez de resultado discriminado, no mesmo
        argumento da `listarCidadesEmCartaz`: sem a chamada a tela continua inteira, e um estado que
        a tela renderiza igual ao caso feliz é um ramo morto

- [x] **T6. A tela** (AC: 10–22)
  - [x] `src/app/(site)/page.tsx`: mover o cálculo de `filtrando` para **antes** do `Promise.all` —
        ele só depende dos parâmetros, e é ele que decide se a chamada é buscada (AC19)
  - [x] `Promise.all([listarProgramacao(filtros), listarCidadesEmCartaz(), filtrando ? null :
        obterDestaque()])`
  - [x] Cortar o destaque da lista **por `id`** (AC13), e não por `slice(1)`
  - [x] Renderizar `<ChamadaPrincipal>` só quando há destaque
  - [x] O título `Programação` e a lista só quando **sobra** pelo menos um evento (AC14)
  - [x] Os três estados de vazio da 3.2 **intactos** — e o de "nenhum show em cartaz" só quando não
        há destaque **nem** itens
  - [x] `ChamadaPrincipal` é um componente **desta tela**, ao lado do `Chip` e da `Fila` no mesmo
        arquivo — não vai para `components/`, pelo mesmo motivo que a barra de busca não foi
  - [x] Arte: `<img>` com `eslint-disable-next-line @next/next/no-img-element` e `alt=""`; sem
        `imagem_url`, um `<div>` do mesmo tamanho (AC17, AC18)
  - [x] Kicker: a data por extenso **com o dia da semana**, em versalete. `lib/formato.ts` ganha
        `dataDaChamada(iso)` → `"sexta, 15 de agosto de 2026, 22h30"`, ao lado da `dataPorExtenso`
        (que continua como está, sem dia da semana, servindo às telas do organizador)
    - [x] Docstring dizendo por que ela **não** é a `dataPorExtenso` com um parâmetro a mais: um
          `comDiaDaSemana?: boolean` faria a função ter duas saídas e obrigaria toda chamada a
          declarar qual delas quer. Duas funções nomeadas dizem o que devolvem
    - [x] ⚠️ Reusar o `.replace(".", "")` do dia da semana (`"sex."` → `"sex"`), como a
          `partesDaFilaPublica` já faz: em versalete o ponto vira sujeira
    - [x] ⚠️ **Nada de `Intl` inline na tela.** O `FUSO` fixo mora no módulo, e as formatações
          inline foram exatamente as que passaram despercebidas quando o `timeZone` entrou (code
          review da Epic 2)
  - [x] Ficha: três linhas `rótulo/valor`; a de `CIDADE` some com `cidade` nulo (AC11)
  - [x] Setores como frase, com `e` antes do último (AC11) — helper local de duas linhas nesta tela
  - [x] `<Link>` quando há ingresso, `<div>` quando esgotado (AC15), com o selo sobre a arte (AC16)
  - [x] `page.module.css`: `.chamada`, `.arte`, `.arteVazia`, `.imagemDaArte`, `.textoDaChamada`,
        `.manchete`, `.ficha`, `.fichaRotulo`, `.fichaValor`, `.seloDaArte`. **Nenhum hex novo**
  - [x] Media query de 900px: uma coluna, arte acima, ficha quebrando em linha (AC21)
  - [x] ⚠️ **Nenhum `"use client"` entra em nada** desta tela

- [x] **T7. Verificação** (AC: 21, 23)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos, e `/` continua `ƒ`
  - [x] Conferir na tela, com `next dev` e `uvicorn` no ar — ⚠️ **os seis são conferência do Igor**,
        e não minha: conferência visual é dele (regra permanente do projeto). Não subi servidor.
        **Conferidos por ele em 2026-08-12, os seis corretos**, depois dos dois ajustes que ele
        pediu com a tela montada (o preço na capa e a remoção do fio de baixo)
    - [x] A raiz limpa mostra a capa, e o show dela **não** aparece na fila abaixo
    - [x] Buscar qualquer coisa → a capa some, a lista continua
    - [x] Um evento com `imagem_url` nulo no destaque → o bloco cinza no lugar da arte, e nada se move
    - [x] Derrubar o `uvicorn` e recarregar → sem capa, sem espaço reservado, com a frase de
          indisponível
    - [x] Abaixo de 900px: arte acima do texto, ficha quebrando — **conferência do Igor**
    - [x] Tab pela tela: a capa é um alvo só quando é link — **conferência do Igor**
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2)
  - [ ] ⚠️ Conferir que os arquivos novos **estão rastreados** — **não executo git** (regra do
        projeto); a conferência é do Igor
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** ao terminar — não se
        aplica: nenhum servidor foi iniciado nesta sessão (só o Postgres do Compose, que fica no ar)

- [x] **T8. Os READMEs** (AC: 24) — obrigatório, regra do projeto
  - [x] `backend/README.md`, até cinco parágrafos em `## Programação pública`
  - [x] `frontend/README.md`, até cinco parágrafos em `## A raiz: a programação`
  - [x] `README.md` da raiz: **não tocar**
  - [x] ⚠️ **O standfirst ausente não vai para README nenhum** (instrução do Igor) — o registro dele é
        o AC12 e o Dev Agent Record
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README
(T8) — é o "por quê" dele.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| De onde vem a arte | **Rota própria: `GET /eventos/destaque`.** Ela devolve um objeto com os campos que a capa precisa — arte e nomes de setor inclusive — e `EventoNaProgramacao` fica exatamente como está. A fila continua enxuta, e o contrato da capa é dela | *`imagem_url` no `EventoNaProgramacao`*, com a tela usando `itens[0]` como capa: uma linha no schema e zero rota nova — caiu porque todo item da fila passaria a carregar uma URL que só um deles usa, e a 3.1 recusou exatamente isso ("campo que nenhuma tela lê é campo que ninguém sabe se está certo"). Pior: os nomes de setor da ficha exigiriam **também** `setores` na lista, que é o campo que o UX-DR7 mantém fora |
| O standfirst | **Não existe.** A capa é kicker, manchete e ficha. O `Evento` não tem texto livre — nem coluna, nem campo no formulário de publicação, nem nada vindo da Ticketmaster | *Coluna `descricao` nova*, com `<textarea>` na tela de publicar: é o único caminho em que a linha diz algo verdadeiro — caiu por custo, porque arrastaria migração, schema de entrada e uma tela já revisada da Epic 2 para dentro de uma story de leitura. E a *frase montada com os dados* ("No Qualistage, no Rio de Janeiro, nesta sexta"): cumpriria o UX-DR4 ao pé da letra e repetiria o que o kicker e a ficha já dizem — é o anti-padrão nº 5 do `DESIGN.md`, a linha de contexto que "soa gerada" |
| Quando a capa aparece | **Só na raiz limpa.** Com `?q=`, `?cidade=` ou `?periodo=`, a tela vira lista pura | *A capa refletindo o resultado filtrado* (primeiro item vira capa): manteria a identidade de jornal em qualquer estado — caiu porque a capa mudaria de show a cada busca, e com um resultado só a tela mostraria o mesmo evento em cima e embaixo. E *a capa fixa ignorando o filtro*: mostraria um show de São Paulo em cima da lista filtrada por Rio, e — pior — logo acima de "nenhum show encontrado para essa busca" |
| O destaque na fila | **Sai.** A lista começa no segundo evento; nenhum show aparece duas vezes na mesma tela | *Manter na fila também*, tratando a capa como realce do primeiro item: a lista continuaria sendo a programação inteira e o caso de um evento só não teria tratamento — caiu porque o mesmo show duas vezes numa tela de quatro é a leitura errada de "uma só por tela" |
| A ficha de três dados | **`CASA` · `CIDADE` · `SETORES`.** Os nomes dos setores entram (Pista, VIP e Camarote) — nome não é estoque, e é o que o protótipo desenha | *`CASA` · `CIDADE` · `A PARTIR DE`*: os três já existiam no contrato da programação e não exigiriam campo novo — caiu porque a data já está no kicker e o preço, sozinho, diz menos sobre o show do que a lista de setores. O preço da capa fica em aberto (*Perguntas em aberto* nº 1) |
| Destaque esgotado | **Continua na capa**, com selo `ESGOTADO` e sem link. Mesma regra da fila da 3.1: show esgotado é informação, não ruído | *Pular para o próximo com ingresso*: a capa é o bloco grande da tela e destacar o que não dá para comprar desperdiça o espaço — caiu porque "o próximo show" deixaria de ser verdade, e a capa passaria a esconder do visitante justamente o show mais próximo |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar.

- **Sem botão "Ver setores".** O protótipo põe um; aqui o **bloco inteiro** é o link, como a fila da
  3.1. Dois alvos para o mesmo destino no mesmo bloco é uma escolha falsa, e o botão seria o único
  primário da tela apontando para uma rota que só nasce na 3.4.
- **Sem selo "Destaque da semana".** O selo do protótipo vira exclusivamente o `ESGOTADO`. "Destaque
  da semana" é curadoria, e o que a rota devolve é o próximo show — a frase mentiria num show
  marcado para daqui a três meses.
- **Todos os setores entram na ficha, inclusive o esgotado.** A ficha diz o que o show tem, não o
  que sobrou. Filtrar por disponibilidade ali faria a lista mudar sozinha conforme as vendas, sem
  nenhuma pista do porquê.
- **O `null` da rota é `200` com corpo `null`.** `204` está fora porque não tem corpo, e o
  `resposta.json()` da tela estouraria num `catch` que existe para falha de rede — o "não há show"
  viraria "não foi possível carregar".
- **A capa não é buscada quando há filtro.** Não é só não renderizar: a chamada de rede também não
  acontece.
- **`obterDestaque` engole a falha e devolve `null`**, no mesmo argumento da `listarCidadesEmCartaz`:
  sem a capa a tela continua inteira, e um resultado discriminado criaria um ramo que a tela
  renderiza igual ao caso feliz.
- **Sem `preco_minimo_centavos` no contrato do destaque.** A ficha escolhida não mostra preço, e a
  disciplina da 3.1 é não devolver campo que nenhuma tela lê. Se o preço voltar para a ficha
  (*Perguntas em aberto* nº 1), é uma linha no schema e uma no service.
- **A arte é 16/10 com degradê para o breu na base**, como o `DESIGN.md` pede, mas o degradê é
  escrito com `var(--breu)` e `transparent` — nenhum `rgba()` com hex literal entra no módulo.
- **Nenhuma paginação, nenhum carrossel de destaques, nenhuma rotação.** Uma só por tela, e é a
  próxima da lista.

### O contrato da API, campo a campo

**`GET /eventos/destaque`** · `200` · `response_model=EventoEmDestaque | None` · **pública** ·
**sem parâmetro nenhum**

```json
{
  "id": "8f2b…",
  "nome": "Marina Sena",
  "data_hora": "2026-08-15T01:30:00Z",
  "local": "Qualistage",
  "cidade": "Rio de Janeiro",
  "imagem_url": "https://s1.ticketm.net/dam/a/….jpg",
  "setores": ["Camarote", "Pista", "VIP"],
  "esgotado": false
}
```

Sem evento publicado e futuro, o corpo é `null` — com `200`.

| Campo | Tipo | Nota |
|---|---|---|
| `id` | `UUID` | O destino do `<Link>`, que só existe a partir da Story 3.4 |
| `nome` | `str` | A manchete |
| `data_hora` | `datetime` | O kicker, formatado por `dataPorExtenso` |
| `local` | `str` | A linha `CASA` da ficha |
| `cidade` | `str \| None` | A linha `CIDADE`; **some** quando nulo |
| `imagem_url` | `str \| None` | A arte; nulo vira bloco `--breu2` do mesmo tamanho |
| `setores` | `list[str]` | **Só os nomes**, em ordem alfabética. A linha `SETORES` |
| `esgotado` | `bool` | Selo e ausência de link. Derivado de `setor.vendidos < setor.capacidade` (AD-13) |

**`GET /eventos` não muda uma vírgula**, e é o AC9 que cobra isso: as mesmas sete chaves, sem
`imagem_url`, sem `setores`.

**Nenhum código de erro novo.**

[Fonte: ARCHITECTURE-SPINE.md#AD-13, #Convenções · backend/app/api/publico.py · backend/app/schemas/evento.py:267-308]

### A tela, em texto

```
  ┌ BUSCAR ARTISTA, CASA DE SHOW OU CIDADE ────────────┬───────┬──────────┐
  │                                                    │ TODAS │  BUSCAR  │
  └────────────────────────────────────────────────────┴───────┴──────────┘
  QUANDO  [TODOS] 7 DIAS  30 DIAS
  ┌──────────────────────────────┬────────────────────────────────────────┐
  │ ▟▛▜▙ arte 16/10 com degradê  │  SEXTA, 15 DE AGOSTO DE 2026, 22H30    │
  │      para o breu na base     │                                        │
  │                              │  Marina Sena         ← serifada 46px   │
  │  [ESGOTADO] ← só se for      │  ──────────────────────────────────    │
  │                              │  CASA       Qualistage                 │
  │                              │  CIDADE     Rio de Janeiro             │
  │                              │  SETORES    Pista, VIP e Camarote      │
  └──────────────────────────────┴────────────────────────────────────────┘
  ─────────────────────────────────────────────────────────────────────────
  PROGRAMAÇÃO
  ─────────────────────────────────────────────────────────────────────────
  QUA          Djavan                       Vibra São Paulo     ESGOTADO
  19           ← a Marina Sena NÃO aparece aqui de novo
  AGO 2026
  20H00
  ─────────────────────────────────────────────────────────────────────────
```

- Duas colunas `1.15fr .85fr` com `gap: 34px`, fio de 1px fechando embaixo
- Kicker em mono versalete `fumaca`; manchete em serifada 46px, `-0.03em`
- Ficha: rótulo em mono versalete de 104px, valor em serifada 16px, fio entre as linhas
- **Sem card, sem sombra, sem raio.** Nenhum hex novo
- Abaixo de 900px: uma coluna, arte acima, manchete menor, ficha quebrando em linha

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `listar_programacao` | `app/services/evento.py:310` | **O molde da consulta e da derivação de `esgotado`.** Leia o docstring inteiro: as quatro decisões que moram lá valem para o destaque também. **Ela não muda nesta story** |
| `listar_cidades_em_cartaz` | `app/services/evento.py:472` | O molde da função de leitura curta, e o precedente do "mesmo recorte de publicado e futuro" |
| `EventoNaProgramacao` | `app/schemas/evento.py:267` | **Não muda.** O schema novo entra ao lado, e o docstring dele explica o que recusa |
| `EventoSaida` | `app/schemas/evento.py:311` | ⚠️ **Não reuse.** Ele traz `setores: list[SetorSaida]`, e `SetorSaida` carrega `capacidade`, `vendidos` e `preco_centavos` — é o UX-DR7 caindo por reuso de schema |
| `/eventos/cidades` (rota) | `app/api/publico.py:36` | **O molde da rota nova**, inclusive o comentário sobre ordem de declaração |
| `_evento_gravado` | `tests/test_programacao.py:56` | Ganha `imagem_url` com default `None`, sem mexer na assinatura de quem já chama |
| `test_programacao.py` | `tests/` | **É este arquivo que cresce.** Mesmo módulo, mesmos helpers |
| `listarCidadesEmCartaz` | `frontend/src/lib/programacao.ts:163` | **O molde da função nova**: `no-store`, `unstable_rethrow` na primeira linha do `catch`, falha engolida |
| `dataPorExtenso` | `frontend/src/lib/formato.ts:60` | **O molde** da função nova do kicker (`dataDaChamada`), que precisa do dia da semana. Ela **não muda**: as telas do organizador dependem dela. ⚠️ O `FUSO` fixo mora nesse módulo — formatar data inline na tela é o defeito que o code review da Epic 2 achou |
| `partesDaFilaPublica` | `frontend/src/lib/formato.ts:131` | O precedente do `.replace(".", "")` no dia da semana e no mês, para o versalete não carregar ponto |
| `Fila` e `Chip` | `(site)/page.tsx:293, 333` | Os moldes de componente-desta-tela. `Fila` é também o precedente de `<Link>`/`<div>` conforme `esgotado` |
| `.selo` | `(site)/page.module.css:324` | O selo vazado em `brasa`, raio zero — a mesma anatomia do selo da arte |
| Miniatura do catálogo | `components/FormularioPublicacao.tsx:382-387` | **O precedente do `<img>` com `eslint-disable` e do bloco vazio do mesmo tamanho** |
| Tokens | `frontend/src/app/globals.css` | `var(--neon)`, `var(--brasa)`, `var(--breu)`, `var(--breu2)`, `var(--fio)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)`, `.kicker`, `:focus-visible` |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, as quatro migrações, `seeds/`,
`app/core/`, `app/integrations/`, `app/main.py`, `app/schemas/auth.py`, `app/schemas/catalogo.py`,
`app/api/auth.py`, `app/api/organizador.py`, `app/api/saude.py`, `app/services/autenticacao.py`,
`publicar()`, `listar_portarias()`, `listar_do_organizador()`, `obter_do_organizador()`,
`listar_programacao()`, `listar_cidades_em_cartaz()`, `tests/conftest.py`, `docker-compose.yml`,
`pyproject.toml`, `package.json`, `next.config.ts`, `frontend/src/lib/servidor.ts`, `sessao.ts`,
`api.ts`, `caminho.ts`, `eventos.ts`, `catalogo.ts`, `Masthead.tsx`, `globals.css`, e as telas de
`(entrada)/` e de `organizador/`.

⚠️ **`lib/formato.ts` é a única exceção**, e é uma exceção por acréscimo: ele **ganha**
`dataDaChamada`, e nenhuma das cinco funções que já existem lá pode mudar de assinatura ou de saída
— quatro telas dependem delas.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Copiar o teste de varredura de palavras proibidas sem tirar `setores` da lista.** O teste da 3.1
varre o texto inteiro da resposta atrás de `capacidade`, `vendidos`, `setores`, `imagem_url` e
`organizador_id`. Nesta rota, **`setores` e `imagem_url` são chaves legítimas** — copiar o teste
tal como está o faz falhar, e "consertá-lo" apagando a asserção inteira jogaria fora a proteção do
UX-DR7. Tire só as duas palavras, e escreva o motivo no teste.

**2. Reusar `SetorSaida` "porque já existe um schema de setor".** Ele carrega `capacidade`,
`vendidos` e `preco_centavos`. A ficha quer três nomes; `list[str]` é o contrato, e a economia de
uma classe custaria o estoque inteiro atravessando a rede.

**3. `next/image` na arte.** Não há `images.remotePatterns` no `next.config.ts`, e o componente
estoura em tempo de execução com host não configurado — em produção, não em build. É `<img>`, com o
mesmo `eslint-disable` da miniatura do catálogo.

**4. Cortar o destaque da fila com `slice(1)`.** Funciona hoje por coincidência: as duas rotas são
consultas independentes, e o dia em que a ordenação da lista mudar, a tela passa a esconder o
segundo show e a mostrar o primeiro duas vezes. É `filter(e => e.id !== destaque.id)`.

**5. Deixar "Nenhum show em cartaz" embaixo da capa.** Com um evento só no banco, a lista fica vazia
depois do corte — e o estado vazio da 3.2 dispararia. A tela se contradiria em duas linhas. O AC14
é o que fecha isso.

**6. Buscar o destaque mesmo com filtro ativo.** Renderizar condicionalmente é a metade fácil; a
outra é não pagar a ida à rede. `filtrando` precisa ser calculado **antes** do `Promise.all` —
hoje ele é calculado depois, e mover a linha é parte da T6.

**7. Tratar o `null` do corpo como falha.** `200` com `null` é a resposta certa para banco vazio.
Um `if (!dados) return { estado: "indisponivel" }` transformaria "não há show em cartaz" em "não foi
possível carregar" — que é a mesma classe de mentira que o AC8 da 3.2 evitou na normalização do
período.

**8. Formatar a data inline na tela.** O `FUSO` fixo do `lib/formato.ts` existe porque a mesma
publicação apareceu com duas datas diferentes (achado do code review da Epic 2). O kicker precisa do
dia da semana, que a `dataPorExtenso` não devolve — e a saída **não** é um `Intl` na tela nem um
parâmetro booleano na função existente: é uma função nova, nomeada, no mesmo módulo.

**9. `alt` com o nome do artista.** A arte é decorativa: o nome está escrito ao lado em 46px. Um
`alt` repetido faz o leitor de tela anunciar o show duas vezes.

**10. Hex do protótipo no CSS.** O degradê do `.lead-arte` é `rgba(14,13,12,.92)` — o breu **antigo**,
de antes da troca de paleta. Copiá-lo pinta o degradê com a cor errada e viola a regra de só
`var(--token)` no módulo.

**11. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest` falhar
com `os error 4551`, chame pelo módulo: `uv run python -m pytest`.

**12. O banco de desenvolvimento é do Igor.** Ele tem quatro eventos reais de conferência, entre eles
um sem setor. **Não apague nada, e não semeie evento novo** — semear é decisão de produto dele.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      publico.py                 # +GET /eventos/destaque
    schemas/
      evento.py                  # +EventoEmDestaque
    services/
      evento.py                  # +obter_destaque()
  tests/
    test_programacao.py          # cresce
  README.md
frontend/
  src/
    lib/
      programacao.ts             # +EventoEmDestaque, +obterDestaque()
      formato.ts                 # +dataDaChamada() — só acréscimo
    app/(site)/
      page.tsx                   # +ChamadaPrincipal, corte do destaque na fila
      page.module.css            # +.chamada, .arte, .ficha, .manchete, .seloDaArte
  README.md
```

Não existe, e não deve passar a existir nesta story: migração, coluna nova, `components/
ChamadaPrincipal.tsx`, `app/api/cliente.py`, `services/destaque.py`, `imagem_url` no
`EventoNaProgramacao`, `images.remotePatterns` no `next.config.ts`, carrossel, rotação de destaques,
`error.tsx`, teste automatizado de frontend, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| Responde sem cookie, e igual para quem está logado | `test_programacao.py` | 1 |
| O destaque é o de **menor `data_hora`**, não o primeiro inserido | `test_programacao.py` | 1 |
| Empate de horário desempata por `id`, de forma estável | `test_programacao.py` | 1 |
| Rascunho não vira destaque, mesmo sendo o mais próximo | `test_programacao.py` | 4 |
| Evento passado não vira destaque, mesmo sendo o mais próximo | `test_programacao.py` | 4 |
| Banco vazio → `200` com corpo `null`, **e não `404`** | `test_programacao.py` | 3 |
| O corpo tem **exatamente as oito chaves** | `test_programacao.py` | 5 |
| Nenhuma palavra de estoque no texto (**sem `setores` na lista**) | `test_programacao.py` | 6 |
| `setores` traz só nomes, em ordem alfabética, incluindo o esgotado | `test_programacao.py` | 7 |
| Todos os setores esgotados → `esgotado: true`, e continua sendo destaque | `test_programacao.py` | 8 |
| Evento sem setor nenhum → `esgotado: true`, sem quebrar | `test_programacao.py` | 8 |
| `imagem_url` nulo volta `null` | `test_programacao.py` | 5 |
| OpenAPI: a rota não declara parâmetro nenhum | `test_programacao.py` | 1 |
| `GET /eventos` continua com as sete chaves e sem `imagem_url` | (já existe) | 9 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são seis caminhos — os da T7.

**Baseline: 263 testes passando** (Story 3.2).

### Inteligência das stories anteriores

**Da 3.2 — a story imediatamente anterior:**

- **A ordem de declaração das rotas** já tem comentário no `publico.py`, escrito para a Story 3.4.
  A rota nova entra no mesmo bloco, e não depois de `listar_programacao`.
- **O `<select>` de cidade e os chips de período** mostraram que a decisão do elemento vem do
  conjunto, não do estilo. Aqui vale igual: a capa é um `<Link>` quando dá para comprar e um `<div>`
  quando não dá — nunca um link desativado por CSS.
- **O `Botao` é `width: 100%` desde a 1.4**, e solto num flex ele espreme o vizinho a zero. Se a
  capa ganhar qualquer botão (ela não deve, AC15), o invólucro de largura fixa é obrigatório.
- **O `unstable_rethrow` na primeira linha do `catch`** foi descoberto pelo log do `npm run build`,
  não por teste. A função nova tem exatamente o mesmo risco.
- **Um teste da 3.1 precisou mudar uma linha na 3.2** porque afirmava `parameters == []` numa rota que
  passou a ter filtros. Nesta story **nenhum teste antigo muda** — a rota nova é rota nova, e
  `GET /eventos` está intacta. Se algum quebrar, é sinal de escopo vazando.

**Da 3.1 — a base do contrato público:** `response_model` é a garantia, não a tela; banco vazio
responde `200`, nunca `404`; e `imagem_url` ficou fora da programação **apontando para esta story**
— o docstring do `EventoNaProgramacao` diz isso com todas as letras, e agora ele está cumprido sem
que o schema mude.

**Da 2.4/2.6 — a arte:** `imagem_url` é copiada da Ticketmaster no ato da publicação e validada
para `http://` e `https://` no schema de entrada (achado P9 do code review da Epic 2). O que chega
na capa já passou por essa peneira — mas ela é **anulável**, e o AC17 é quem trata isso.

**Da paleta (commit `e5ecf30`):** o acento é `--neon` (`#ff4f9a`). **O `DESIGN.md` e o protótipo
continuam escrevendo "âmbar"** e não foram tocados: onde eles disserem âmbar, leia neon. A fonte
única dos valores é `frontend/src/app/globals.css`.

[Fonte: _bmad-output/implementation-artifacts/3-2-buscar-e-filtrar-a-programacao.md · 3-1-ver-a-programacao.md · code-review-epic-2.md]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `response_model=EventoEmDestaque \| None` devolvendo `null` com `200` |
| Pydantic | 2.13.4 | O schema novo, sem `from_attributes` |
| SQLAlchemy | 2.0.51 | `.limit(1)`, `.first()`, `selectinload` |
| PostgreSQL | 16 | Nenhuma mudança de schema |
| Next.js | **16.3.0** | Server Component, `PageProps<"/">`, `<img>` em vez de `next/image` |
| React | 19 | Nenhuma ilha de cliente nova |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** A documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

### Escopo — o que NÃO fazer aqui

Página do evento e seus setores (3.4) · medidor · reserva e stepper (3.5 em diante) · coluna de
descrição · edição de evento · upload de imagem · paginação · carrossel · rotação de destaque ·
qualquer rota de escrita · qualquer alteração nas rotas do organizador · teste automatizado de
frontend.

Quatro tentações concretas:

- **"Já ponho `imagem_url` na lista também, a 3.4 vai precisar."** A 3.4 tem contrato próprio, e o
  AC9 cobra que `EventoNaProgramacao` não mude
- **"Já devolvo os setores com preço, dá para mostrar 'a partir de' na capa."** É o UX-DR7 e a
  *Pergunta em aberto* nº 1 — se o preço voltar, ele volta como um campo, não como a lista de setores
- **"Já crio `/eventos/{id}`, a capa aponta para lá."** É a Story 3.4. A janela do link quebrado está
  aberta desde a 3.1 e registrada no `frontend/README.md`
- **"Aproveito e ponho `images.remotePatterns` para usar `next/image`."** É configuração de build que
  quebra calada quando o host da Discovery mudar, e não é decisão desta story

### Project Structure Notes

`publico.py` passa a ter **três** rotas, e as três são de leitura sem conta — o critério de entrada
do arquivo continua exatamente o que o docstring dele diz. Duas delas (`/eventos/cidades` e
`/eventos/destaque`) são paths fixos que precisam vir antes do `/eventos/{id}` da Story 3.4, e agora
são duas as linhas que dependem disso: vale um comentário só, cobrindo as duas, em vez de repetir o
aviso.

É a primeira vez que um schema deste projeto devolve uma **projeção de um relacionamento** — os
nomes dos setores como `list[str]`, e não os setores. A tentação de reusar `SetorSaida` é grande e é
exatamente o que o UX-DR7 não permite; o schema novo é a fronteira que impede isso, e o docstring
dele precisa dizer por que a lista é de strings.

No frontend, a raiz ganha o **terceiro** dado de servidor e a primeira condição sobre buscar ou não
buscar. O `Promise.all` deixa de ser "duas coisas independentes" e passa a ser "duas coisas mais uma
que depende do estado da URL" — é a linha que o AC19 protege.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] — os quatro blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — o objetivo da epic e as stories vizinhas
- [Source: ARCHITECTURE-SPINE.md#Convenções] — Server Component por padrão
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade
- [Source: ARCHITECTURE-SPINE.md#AD-2] — nada de `NEXT_PUBLIC`
- [Source: DESIGN.md#Components/chamada-principal] — duas colunas, arte 16/10 com degradê, uma só por
  tela. ⚠️ O documento escreve `ambar`; o token vivo é `--neon`
- [Source: DESIGN.md#Typography] — manchete serif 46px/1.02, `-0.03em`; kicker mono 600 10px
- [Source: DESIGN.md#Do's and Don'ts] — anti-padrão nº 5, a linha de contexto que "soa gerada"
- [Source: EXPERIENCE.md#Responsive & Platform] — chamada e ficha empilham abaixo de 900px
- [Source: EXPERIENCE.md#Vazio] — estado vazio sem ilustração e sem botão grande
- [Source: mockups/proto-jornal-noturno.html:67-81, 284-298] — o CSS e o markup do `.lead`
- [Source: backend/app/api/publico.py:30-51] — o molde da rota pública e o comentário de ordem
- [Source: backend/app/services/evento.py:310-469] — `listar_programacao`, o molde do recorte
- [Source: backend/app/schemas/evento.py:267-308] — `EventoNaProgramacao` e o motivo de `imagem_url`
  estar fora dela
- [Source: backend/tests/test_programacao.py:56-129] — o helper `_evento_gravado`
- [Source: frontend/src/lib/programacao.ts:145-186] — `listarCidadesEmCartaz`, o molde da função nova
- [Source: frontend/src/app/(site)/page.tsx] — a raiz, com `Chip` e `Fila` como moldes
- [Source: frontend/src/components/FormularioPublicacao.tsx:382-387] — o `<img>` com `eslint-disable`
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, régua de cinco parágrafos;
  git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. Ao
   terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída** — até cinco parágrafos por camada, e a
   raiz **não é tocada**. Documentação não bloqueia o commit: aplique o código, rode a suíte, mostre
   o resultado, **depois** escreva
3. **Decisão de produto ou de modelagem é do Igor.** As seis desta story estão respondidas e as nove
   suposições estão declaradas. Se aparecer uma sétima — campo a mais, tela a mais, rota a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os arquivos novos foram rastreados (T7)
8. **O code review é ao fim da Epic 3**, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **O preço sumiu da capa** — ⚠️ **decisão adiada por escolha do Igor: ele decide depois de ver a
   tela pronta.** Você escolheu `CASA · CIDADE · SETORES`, e como o destaque **sai da fila**
   (AC13), o show em capa passa a ser o único da programação sem "a partir de" em lugar nenhum da
   raiz. **Para o dev agent: implemente como está escrito nos ACs e não pergunte de novo** — o
   ajuste, se vier, é depois da conferência visual e custa duas linhas: `preco_minimo_centavos`
   volta ao schema do destaque e a ficha ganha uma quarta linha (ou `SETORES` sai).
2. **A capa some quando a pessoa busca.** É a sua decisão e está escrita, mas vale saber a
   consequência para quem avalia: o avaliador que abrir a raiz e imediatamente buscar um show nunca
   vê o elemento que "faz a tela parecer jornal". O roteiro de avaliação da Epic 6 deveria começar
   pela raiz limpa.
3. **A raiz recebe decisão nova?** Escrevi para **não** tocar o `README.md` da raiz: a régua diz que
   entra ali só o que faria quem avalia ver *um sistema diferente*, e uma capa na home é UI. A defesa
   do contrário existe — *o destaque tem contrato próprio em vez de campo na lista* é uma escolha de
   arquitetura de API que se repete na 3.4. Se você achar que passa na régua, é um bloco de três
   partes, e o material está na tabela de decisões.
4. **Nenhum evento é semeado, e agora existe uma capa vazia para provar.** Numa máquina limpa o
   avaliador abre a raiz e não vê nem capa, nem lista, nem cidade nos filtros — só a frase de "nenhum
   show em cartaz". É a mesma pergunta da 3.1 e da 3.2, com um motivo a mais.
5. **A arte vem da Ticketmaster e é servida direto do domínio deles.** Sem `next/image`, sem cache
   nosso e sem fallback se eles removerem a imagem: aí o `<img>` quebra e o navegador mostra o
   ícone de imagem faltando, no lugar do bloco cinza. Se isso incomodar, o conserto é uma linha de
   `onError` — que custa `"use client"` na capa, e é decisão sua.

## Dev Agent Record

### Agent Model Used

`claude-opus-5[1m]` (Claude Opus 5, 1M de contexto), via `bmad-dev-story`.

### Debug Log References

- **Fase vermelha, antes de qualquer implementação:** `uv run python -m pytest
  tests/test_programacao.py -k "destaque or empate or arte"` → **14 falhando, 1 passando**. O que
  passou foi a varredura de palavras proibidas: com a rota ainda inexistente, o corpo do `404` não
  contém nenhuma delas, e o teste passa por vacuidade. Ele só passa a provar alguma coisa depois que
  a rota existe — registrado aqui para não parecer que ele nasceu verde.
- **Depois de schema, service e rota:** o módulo inteiro fechou em **60 testes**.
- **Suíte completa:** `uv run python -m pytest` → **278 testes passando** em 33s, partindo dos 263
  da Story 3.2. Nenhum teste antigo precisou mudar (AC9), e nenhum quebrou.
- **Depois do preço e da remoção do fio** (pedidos do Igor com a tela pronta): **279 testes**, com
  `tsc`, `lint` e `build` limpos de novo e `/` ainda `ƒ`.
- `npx tsc --noEmit`, `npm run lint` e `npm run build` limpos; `/` continua marcada `ƒ` no relatório
  de rotas. Busca por `NEXT_PUBLIC` em `frontend/src/` → **zero** (AD-2).
- Docker Desktop estava fora do ar no início da sessão; subi ele e o `docker compose up -d` antes da
  primeira execução da suíte.

### Completion Notes List

**O que entrou.** Uma rota pública nova (`GET /eventos/destaque`), o schema `EventoEmDestaque` de
oito campos, `obter_destaque()` no service com consulta própria e `LIMIT 1`, `obterDestaque()` e o
tipo espelho no `lib/programacao.ts`, `dataDaChamada()` no `lib/formato.ts`, e o componente
`ChamadaPrincipal` dentro da própria raiz. Nenhuma migração, nenhuma coluna, nenhum modelo novo,
nenhuma dependência nova — e `GET /eventos` não mudou uma vírgula, como o AC9 exige.

**As seis decisões do Igor foram implementadas como escritas**, sem uma sétima. O standfirst não
existe (AC12) e o registro dele ficou **só aqui e no comentário do `ChamadaPrincipal`**, sem ir a
README nenhum, por instrução dele. O preço fora da ficha (*Pergunta em aberto* nº 1) foi
implementado como está e não foi perguntado de novo.

**Duas leituras que precisei fixar, e o motivo de cada uma:**

1. **O título `Programação` some junto com a lista, mas só quando há capa.** A T6 diz "o título e a
   lista só quando sobra pelo menos um evento", o que ao pé da letra tiraria o título também dos
   estados de vazio da 3.2 — e o AC19 manda que os três continuem **exatamente** como estão. A
   condição que satisfaz os dois é `destaque && itensDaFila.length === 0` (a variável
   `aFilaSobrouVazia` no `page.tsx`): com filtro ativo nunca há capa, então a tela filtrada é
   idêntica à da 3.2, e o AC14 continua valendo no caso que ele descreve — um evento só no banco.
2. **A linha `SETORES` da ficha some quando a lista vem vazia**, pela mesma regra já decidida para a
   `CIDADE` nula. Só acontece com evento sem setor nenhum (possível por `psql`, e existe no banco de
   desenvolvimento). Não é decisão nova: é a regra da cidade aplicada ao único outro campo que pode
   vir vazio.

**Três escolhas de UI pequenas que não estavam nos ACs**, e que são baratas de trocar se o Igor
discordar depois de ver a tela: o hover do bloco troca a cor da **manchete** para `var(--neon)` em
vez de pintar o fundo inteiro como a fila faz (um bloco desta altura piscando inteiro é agressivo);
o selo `ESGOTADO` ganhou `background: var(--breu)` além do contorno em `--brasa`, porque um vazado
sem fundo fica ilegível sobre arte clara; e a ficha é um `<dl>` com `<dt>`/`<dd>` em vez do `<div>`
com `<b>` do protótipo — desenha igual e diz a quem usa leitor de tela que aquilo são pares
rótulo/valor.

**Três mudanças pedidas pelo Igor depois de ver a tela pronta, e as três estão implementadas.**

1. **O preço voltou** — é a *Pergunta em aberto* nº 1, respondida com a capa montada, como estava
   previsto. `preco_minimo_centavos` voltou ao `EventoEmDestaque` (agora **nove** chaves, não oito
   como diz o AC5) e ao service, com a mesma regra da fila: o menor preço **entre os setores que
   ainda têm ingresso**, `null` quando não há nenhum. Na tela ele é uma linha própria **abaixo** da
   ficha, e não um quarto par dentro dela — os três de cima descrevem o show, e o preço é a única
   linha que fala de comprar. Dois testes novos cobrem isso: o que pula o setor esgotado (Pista a
   R$ 120,00 esgotada, Camarote a R$ 420,00 → 42000) e as asserções de `null` nos dois casos de
   `min()` sobre lista vazia. ⚠️ `preco_minimo_centavos` **não** casa a palavra proibida
   `preco_centavos` na varredura do AC6 — conferido, e é por isso que aquele teste continua verde
   sem mudar de lista.
2. **O fio de 1px embaixo da capa saiu** — o AC22 pedia "fio de 1px fechando o bloco embaixo", e na
   tela montada ele ficava solto: um filete a meia altura entre a base da arte e o `.secTitulo`, que
   já traz o próprio fio logo abaixo de "Programação". Dois filetes quase paralelos, sem nada entre
   eles, leem como sobra de grade. O que separa a capa da lista agora é o intervalo, e quem fecha o
   bloco é o fio do título.

3. **A arte quebrada foi consertada** — é a *Pergunta em aberto* nº 5, que ele mandou fechar depois
   da conferência. Um dos eventos do banco de desenvolvimento apareceu com o ícone de imagem
   faltando no meio da capa: a URL é da Ticketmaster, servida direto do domínio deles, e morreu.
   ⚠️ **A story dizia que o conserto custaria `"use client"` na capa, e não custou.** O caminho
   óbvio é um `onError`, que obriga a tela a virar ilha de cliente — hidratação e `useState` na tela
   mais visitada do produto, para tratar uma imagem. Em vez dele, `.imagemDaArte::after` cobre o
   quadro com o mesmo `--breu2` do estado vazio: **pseudo-elemento em `<img>` só ganha caixa quando
   a imagem falha**, porque a imagem que carrega é um elemento substituído e não gera a caixa. A
   regra é invisível no caso feliz, e a raiz continua Server Component da primeira à última linha —
   o AC10 e o `npm run build` marcando `/` como `ƒ` continuam valendo. No Safari, que não gera
   pseudo-elemento em imagem nenhuma, o resultado é o mesmo por outro caminho: ele não desenha
   placeholder para `alt` vazio, e o `background` que o `.arte` agora carrega **sempre** aparece
   sozinho. Esse fundo permanente é o outro meio do conserto, e serve de placeholder de carregamento
   de brinde.
   ⚠️ **A miniatura do catálogo (`FormularioPublicacao.tsx`) tem o mesmo defeito e ficou como
   está**: é tela revisada da Epic 2, o Igor não pediu, e mexer nela seria escopo vazando de uma
   story de leitura. Se valer a pena, é uma linha de CSS lá também.

Os ACs 5 e 22 ficaram, por isso, **desatualizados em relação ao código** — e de propósito: o
workflow só me deixa escrever no Dev Agent Record, no File List, no Change Log e no Status, e
reescrever AC depois do fato apagaria o registro de que a decisão veio da tela pronta, que é
justamente o que a *Pergunta em aberto* nº 1 previu.

**A armadilha nº 1 da story foi tratada de frente.** O teste de varredura de palavras proibidas
desta rota tem lista **própria**, sem `setores` e sem `imagem_url`, com o motivo escrito dentro dele
e repetido no `backend/README.md`: as duas são chaves legítimas aqui, e apagar a asserção inteira
"para consertar" jogaria fora a proteção do UX-DR7 justamente na rota que devolve um relacionamento.

**A conferência visual é do Igor, e ele a fez.** Os seis caminhos da T7 (capa na raiz limpa, capa
sumindo com filtro, `imagem_url` nulo, `uvicorn` fora do ar, abaixo de 900px e o Tab pela tela)
foram conferidos por ele em 2026-08-12, depois dos dois ajustes que ele pediu ao ver a tela montada
— e os seis estão corretos. **Não subi `next dev` nem `uvicorn`** em nenhum momento, regra
permanente do projeto, e por isso nenhum servidor ficou em segundo plano; o Postgres do Compose
continua no ar, como sempre. **Não executei git** em nenhum momento, inclusive para o
`baseline_commit`, que preservei como já estava no frontmatter — conferir que os arquivos novos
foram rastreados é dele, no commit.

### File List

**Backend**

- `backend/app/schemas/evento.py` — modificado (+`EventoEmDestaque`)
- `backend/app/services/evento.py` — modificado (+`obter_destaque()`, +import)
- `backend/app/api/publico.py` — modificado (+rota `/eventos/destaque`, +import, comentário de ordem
  de declaração reescrito para cobrir as duas rotas de path fixo)
- `backend/tests/test_programacao.py` — modificado (+15 testes; `_evento_gravado` ganhou
  `imagem_url` com default `None`)
- `backend/README.md` — modificado (`## Programação pública`, três parágrafos)

**Frontend**

- `frontend/src/lib/programacao.ts` — modificado (+tipo `EventoEmDestaque`, +`obterDestaque()`)
- `frontend/src/lib/formato.ts` — modificado (+`dataDaChamada()`; nenhuma função existente mudou)
- `frontend/src/app/(site)/page.tsx` — modificado (+`ChamadaPrincipal`, +`comoFrase`, `filtrando`
  movido para antes do `Promise.all`, corte do destaque por `id`)
- `frontend/src/app/(site)/page.module.css` — modificado (+`.chamada`, `.arte`, `.arteVazia`,
  `.imagemDaArte`, `.seloDaArte`, `.textoDaChamada`, `.manchete`, `.ficha`, `.fichaRotulo`,
  `.fichaValor` e o bloco de 900px)
- `frontend/README.md` — modificado (`## A raiz: a programação`, três parágrafos)

**Artefatos**

- `_bmad-output/implementation-artifacts/3-3-chamada-principal-na-programacao.md` — modificado
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modificado

**Nenhum arquivo novo, e nenhum apagado.** `README.md` da raiz não foi tocado (AC24).

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-12 | **A arte quebrada, consertada por CSS** — *Pergunta em aberto* nº 5 fechada por decisão do Igor. Um evento do banco de desenvolvimento apareceu com o ícone de imagem faltando no meio da capa, porque a URL da Ticketmaster morreu. A story previa que o conserto custaria `"use client"` (um `onError`), e **não custou**: `.imagemDaArte::after` cobre o quadro com o mesmo `--breu2` do estado vazio, e pseudo-elemento em `<img>` só ganha caixa quando a imagem falha — invisível no caso feliz, sem uma linha de JavaScript, com a raiz continuando Server Component e `/` ainda `ƒ`. O `.arte` passou a carregar o fundo cinza **sempre**, e não só no `.arteVazia`: é o piso do quadro, e vira placeholder de carregamento de brinde. No Safari, que não gera pseudo-elemento em imagem, o resultado é o mesmo por outro caminho — sem placeholder para `alt` vazio, o fundo aparece sozinho. A miniatura do catálogo tem o mesmo defeito e ficou como está: tela revisada da Epic 2, e mexer nela seria escopo vazando |
| 2026-08-12 | **Ajustes do Igor com a tela pronta.** O preço voltou à capa: `preco_minimo_centavos` de volta ao `EventoEmDestaque` (nove chaves, não as oito do AC5), ao service e ao tipo do frontend, com a regra da fila — menor preço entre os setores com ingresso, `null` quando não há nenhum. Na tela ele é linha própria **abaixo** da ficha, e não um quarto par dentro dela: os três de cima descrevem o show, e o preço é a única linha que fala de comprar. É a resposta da *Pergunta em aberto* nº 1, que estava escrita para ser decidida exatamente assim, depois da conferência visual — e o motivo é o destaque **sair** da fila, o que fazia dele o único show da raiz sem "a partir de". E o fio de 1px que fechava a capa embaixo (AC22) saiu: com o `.secTitulo` trazendo o próprio fio logo abaixo de "Programação", os dois ficavam quase paralelos e sem nada entre eles — sobra de grade, não separação. Suíte de 278 → **279**, com dois testes novos de preço; `tsc`, `lint` e `build` limpos, `/` ainda `ƒ`. Os ACs 5 e 22 ficaram desatualizados em relação ao código de propósito: o workflow não me deixa reescrevê-los, e reescrever apagaria o registro de que a decisão veio da tela pronta |
| 2026-08-12 | Story 3.3 implementada. Rota pública `GET /eventos/destaque` com o schema `EventoEmDestaque` de oito chaves (`preco_minimo_centavos` fora, `imagem_url` e `setores` de nomes dentro), `obter_destaque()` com consulta própria e `LIMIT 1` no mesmo recorte da programação, e `null` com `200` para banco vazio. No frontend, `obterDestaque()` com `unstable_rethrow` na primeira linha do `catch`, `dataDaChamada()` nova no `formato.ts` (a `dataPorExtenso` intacta), e o `ChamadaPrincipal` dentro da própria raiz — arte em `<img>` com `alt=""`, ficha `CASA · CIDADE · SETORES` como `<dl>`, sem standfirst e sem botão. O `filtrando` subiu para antes do `Promise.all`, que é o que faz a capa não ser **buscada** com filtro ativo, e o destaque sai da fila por `id`. Quinze testes novos, entre eles o de varredura de palavras proibidas com lista própria (sem `setores` e sem `imagem_url`, que são chaves legítimas nesta rota) e o de desempate estável por `id`. Suíte de 263 → **278**; `tsc`, `lint` e `build` limpos, com `/` ainda `ƒ`. Duas leituras fixadas e registradas nas notas: o título `Programação` some junto com a lista **só quando há capa** (o AC19 exige os três estados de vazio da 3.2 intactos), e a linha `SETORES` some com lista vazia pela mesma regra já decidida para a `CIDADE` nula. Os seis caminhos visuais da T7 e a conferência de rastreamento no git ficaram para o Igor |
| 2026-08-12 | Story 3.3 criada e contextualizada. Seis decisões do Igor incorporadas: **a arte chega por rota própria** (`GET /eventos/destaque`, com schema `EventoEmDestaque`) em vez de `imagem_url` entrar no `EventoNaProgramacao` — a fila continua sem carregar campo que ela não lê, e os nomes de setor da ficha não obrigam a lista a devolver setores; **o standfirst não existe**, porque o `Evento` não tem texto livre e uma frase montada com os mesmos dados do kicker e da ficha é o anti-padrão nº 5 do `DESIGN.md` (registrado só aqui, sem ir a README, por instrução dele); **a capa some com filtro ativo**, e nem é buscada; **o destaque sai da fila**, cortado por `id`; **a ficha é `CASA · CIDADE · SETORES`**, com os nomes dos setores em frase; e **o destaque esgotado continua na capa**, com selo e sem link, na mesma regra da fila da 3.1. Vinte e quatro ACs escritos sobre os quatro blocos do `epics.md`, entre eles o AC6, que é a armadilha menos óbvia desta story: `setores` e `imagem_url` viram chaves legítimas na resposta nova, e o teste de varredura de palavras proibidas da 3.1 não pode ser copiado sem tirar as duas. Nove suposições declaradas (sem botão "Ver setores", sem selo "Destaque da semana", todos os setores na ficha, `200` com `null` em vez de `204`, a capa não buscada com filtro, falha engolida, sem `preco_minimo_centavos`, degradê em `var(--token)` e nenhuma rotação de destaque) e cinco perguntas registradas para o Igor — a primeira delas sobre o preço, que sumiu da raiz para o show em capa |
