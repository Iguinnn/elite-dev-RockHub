---
baseline_commit: "614e931 — feat: Story 2.5 - Escalar quem valida na portaria (branch Epic-2---Publicação-de-eventos-pelo-organizador). Árvore limpa: as Stories 2.1 a 2.5 estão commitadas. Migração `head`: c7cb4a29b7f3. Suíte: 187 testes passando."
---

# Story 2.6: Ver e gerenciar meus eventos

Status: review

Epic 2 — Publicação de eventos pelo organizador · **A última story da epic, e a primeira que só
lê.** As cinco anteriores construíram o caminho de escrita: a integração, a busca, o schema, a
publicação e a escala. Esta fecha o ciclo pelo outro lado — o organizador publicou, e agora
precisa poder olhar o que publicou.

Como organizador,
quero ver os eventos que publiquei,
para acompanhar o que está em cartaz.

**"Gerenciar" aqui é acompanhar, não editar** — decisão do Igor, registrada na tabela de decisões
abaixo. Nenhuma rota de escrita nova, nenhuma migração, nenhum modelo novo. São duas rotas de
leitura (`GET /organizador/eventos` e `GET /organizador/eventos/{id}`), duas telas (a lista e o
detalhe), o link que finalmente entra no masthead, e uma extração de duas funções de formatação que
o servidor não consegue importar de onde elas estão hoje.

## Acceptance Criteria

1. **Given** que sou organizador com eventos publicados
   **When** eu chamo `GET /organizador/eventos`
   **Then** recebo `200` com uma lista de `EventoResumo`: `id`, `nome`, `data_hora`, `local`,
   `cidade`, `publicado_em`, `capacidade_total` e `vendidos_total`
   **And** a lista vem ordenada por `data_hora` **crescente**
   **And** um organizador sem nenhum evento recebe `200` com `[]` — lista vazia é `200`, não `404`,
   pela mesma disciplina de `GET /organizador/portarias` (a pergunta foi respondida)

2. **Given** eventos publicados por outro organizador
   **When** eu chamo a rota
   **Then** eles **não** aparecem
   **And** o escopo vem do `organizador.id` da **sessão**, e não existe parâmetro de query, de
   caminho nem de corpo por onde um `organizador_id` pudesse entrar — a mesma disciplina do
   `publicar()` da Story 2.4: "ver os eventos de outra pessoa" não é uma chamada que o service
   recusa, é uma chamada que não existe

3. **Given** um evento com dois setores, um com `vendidos = 12` e outro com `vendidos = 0`
   **When** eu leio o resumo dele
   **Then** `capacidade_total` e `vendidos_total` são a **soma de `setor.capacidade` e
   `setor.vendidos`** — AD-13
   **And** ⚠️ é **proibido** derivar qualquer um dos dois com `COUNT` sobre reserva ou ingresso, em
   qualquer camada (as duas tabelas nem existem ainda, e é agora que o hábito se forma)
   **And** um evento sem setor nenhum — impossível pela rota, possível por `psql` — soma `0` e não
   quebra a listagem

4. **Given** cinco eventos meus na lista
   **When** eu observo as consultas emitidas
   **Then** os setores vêm em **uma** consulta a mais (`selectinload`), não uma por evento
   **And** a soma acontece no service, num lugar só, onde um teste consegue lê-la

5. **Given** um evento meu
   **When** eu chamo `GET /organizador/eventos/{evento_id}`
   **Then** recebo `200` com `EventoSaida` — **o mesmo schema da publicação**, reusado, com
   `setores` (nome, capacidade, vendidos, preço) e `portarias` (id, nome, e-mail)
   **And** `senha_hash` não aparece em lugar nenhum da resposta
   **And** `organizador_id` também não — quem chama já sabe quem é

6. **Given** o id de um evento de **outro** organizador
   **When** eu peço o detalhe
   **Then** recebo `404` com código `EVENTO_NAO_ENCONTRADO`
   **And** a resposta é **idêntica, byte a byte**, à de um UUID que nunca existiu — a rota não vira
   oráculo de "esse evento existe?", pela mesma disciplina do `PORTARIA_INVALIDA` da 2.5 e do login
   da 1.4
   **And** um id em formato inválido é `422 DADOS_INVALIDOS`, do Pydantic, porque o parâmetro de
   caminho é `UUID`

7. **Given** as duas rotas novas
   **When** um cliente ou a portaria as chama
   **Then** recebo `403` com `SEM_PERMISSAO`
   **And** sem cookie de sessão recebo `401` com `NAO_AUTENTICADO`, **não** `403`
   **And** a proteção é `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` na assinatura — AD-9,
   nunca um `if` no corpo

8. **Given** a implementação inteira do backend
   **When** eu a inspeciono
   **Then** as duas rotas moram em `app/api/organizador.py` e passam por `app/services/evento.py`
   — router não abre `Session` para consultar, é o paradigma da espinha
   **And** **não** existe migração nova, modelo novo, coluna nova nem dependência nova: esta story
   não toca o banco

9. **Given** `src/lib/formato.ts`
   **When** eu o leio
   **Then** `dataPorExtenso`, `momentoDaPublicacao` e `centavosParaReais` moram lá, e
   `FormularioPublicacao.tsx` passa a **importá-las** em vez de declará-las
   **And** ⚠️ a extração não é faxina: um Server Component **não pode chamar** função exportada de
   um módulo `"use client"` — o Next transforma cada export num *client reference*, e a chamada
   estoura em tempo de execução. Duplicar as três nas telas novas seria a segunda fonte do mesmo
   formato de data, e o dia em que uma mudasse ninguém saberia qual está certa
   **And** o comportamento não muda em nada: mesmos textos, mesmos formatos, mesma confirmação

10. **Given** `src/lib/eventos.ts`
    **When** eu o leio
    **Then** ele está no molde **exato** de `catalogo.ts` e `portarias.ts`: só servidor,
    `cache: "no-store"`, `cabecalhoDeSessao()` repassado à mão, `try/catch` que **nunca levanta**
    **And** `listarMeusEventos()` devolve `{ estado: "ok"; itens } | { estado: "indisponivel" }`
    **And** `obterMeuEvento(id)` devolve **três** estados — `ok`, `nao-encontrado` e `indisponivel`
    —, porque a tela precisa distinguir "não é seu" de "a API não respondeu", e só o `404` separa
    os dois

11. **Given** a rota `/organizador/eventos`
    **When** eu a abro
    **Then** é Server Component, **sem uma linha de `"use client"`**
    **And** tem as **duas** guardas de `/organizador/publicar`, no mesmo par: sem sessão,
    `redirect("/login?voltar=%2Forganizador%2Feventos")`; com papel diferente de `ORGANIZADOR`,
    `redirect("/")`

12. **Given** a lista na tela
    **When** eu a leio
    **Then** cada evento é uma **fila com fio**, com a data à esquerda, o nome em serifada, o local
    e a cidade abaixo, e `vendidos/capacidade` em mono versalete à direita — **números exatos**,
    porque é o inventário de quem é dono da informação (UX-DR7)
    **And** a fila **inteira** é clicável e leva ao detalhe, não só o nome (padrão `fila-listagem`)
    **And** o par de números não fica sem nome: ou há um rótulo visível (`vendidos`) ou um
    `aria-label` que o diga — `12/860` sozinho é ambíguo para quem chega de leitor de tela
    **And** não há medidor nem proporção: proporção é para quem compra

13. **Given** que tenho evento futuro e evento cuja data já passou
    **When** eu abro a lista
    **Then** vejo **duas seções** com kicker: `Em cartaz` (data futura, ordem crescente) e
    `Já aconteceram` (data passada, ordem **decrescente**)
    **And** seção sem nenhum evento simplesmente **não é renderizada** — bloco vazio com título é
    pior que ausência
    **And** o corte é feito na tela comparando `new Date(data_hora)` com o instante atual, nunca
    comparando texto

14. **Given** que ainda não publiquei nada
    **When** eu abro "Meus eventos"
    **Then** vejo *"Você ainda não publicou nenhum evento. Quando publicar, ele aparece aqui com o
    inventário de cada setor."* — kicker, frase, fim, **sem ilustração e sem botão grande**
    (EXPERIENCE.md#Vazio, UX-DR8)
    **And** se a lista não puder ser carregada, a tela diz isso numa frase e **não** quebra — o
    projeto continua sem `error.tsx`, e a falha é um estado discriminado

15. **Given** a rota `/organizador/eventos/[id]`
    **When** eu abro o detalhe de um evento meu
    **Then** vejo o nome em serifada, a data por extenso, `local · cidade`, o kicker
    `Publicado em …`, o inventário **setor a setor** com `vendidos/capacidade` e preço, e o bloco
    `Na porta` com quem foi escalado (nome e e-mail)
    **And** as mesmas duas guardas do AC11, e `estado === "nao-encontrado"` chama `notFound()` — a
    404 do projeto, que já existe
    **And** ⚠️ evento **sem ninguém escalado** (existem dois assim no banco de desenvolvimento,
    publicados na janela do AD-7 da 2.4) mostra uma frase no lugar da lista, e **não** quebra
    **And** há um caminho de volta para a lista

16. **Given** o masthead com sessão de organizador
    **When** eu o inspeciono
    **Then** a navegação é `Início · Meus eventos · Publicar evento · Minha conta`, nessa ordem
    **And** o comentário que hoje diz *"`Meus ingressos` e `Meus eventos` saem daqui até as Stories
    4.1 e 2.6"* é reescrito: a 2.6 chegou, e sobra só `Meus ingressos`
    **And** `Meus eventos` **não** aparece para cliente, portaria nem visitante

17. **Given** a confirmação de publicação da 2.4/2.5
    **When** um evento é publicado
    **Then** ela ganha `Ver meus eventos →` ao lado de `Publicar outro →`
    **And** **continua sem `redirect`**: a confirmação com o inventário e os escalados é o recibo da
    publicação, e trocá-la por um salto para a lista apagaria a única vez em que o organizador vê
    quem ficou com a porta

18. **Given** uma tela abaixo de 900px, nas duas páginas
    **When** eu as uso
    **Then** cada bloco ocupa a largura inteira, um por linha
    **And** nada transborda na horizontal
    **And** não há card, sombra nem canto arredondado (UX-DR3), nenhum dos cinco anti-padrões do
    UX-DR10 aparece, nenhuma informação é dada **só** por cor (UX-DR9) e nenhum hex novo entra em
    `*.module.css` — só `var(--token)`

19. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira, e os **187** testes anteriores continuam verdes — nenhum deles
    precisa mudar, porque esta story não altera contrato nenhum que já existia
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos

20. **Given** os três READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta as duas rotas, o `EventoResumo`, a soma pelo AD-13, o
    `EVENTO_NAO_ENCONTRADO` e por que o 404 não distingue "não é seu" de "não existe"
    **And** `frontend/README.md` documenta as duas telas, o `lib/formato.ts` e **por que ele
    precisou existir**, o corte em duas seções e o link novo no masthead
    **And** `README.md` da raiz ganha as decisões desta story **com a alternativa descartada** de
    cada uma, em primeira pessoa
    **And** *O que não está pronto* passa a dizer que **não há como editar evento nem trocar a
    escala depois de publicar** — a tela de "Meus eventos" existe, e é nela que alguém procuraria

> **De onde vem cada critério.** O `epics.md` traz **dois** blocos para a Story 2.6: ver cada evento
> com data, local, setores e números exatos de vendidos e capacidade; e não ver os eventos de outro
> organizador. Eles viraram os ACs **1, 3, 5, 12, 15** e **2**.
>
> Todo o resto é decisão do Igor, tomada antes de a story ser escrita (a tabela abaixo): a story é
> **só leitura**; a tela é **lista enxuta + detalhe**; a lista se parte em **em cartaz** e **já
> aconteceram**; e o masthead ganha o link, com a confirmação de publicação apontando para lá.
> O AC9 existe por uma restrição técnica, não por gosto — está explicado nele e na armadilha 1.

## Tasks / Subtasks

- [x] **T1. `app/schemas/evento.py` — o resumo** (AC: 1, 3)
  - [x] `EventoResumo` novo: `id`, `nome`, `data_hora`, `local`, `cidade`, `publicado_em`,
        `capacidade_total: int`, `vendidos_total: int`
  - [x] **Sem `from_attributes`**, ao contrário dos outros três: os dois totais não são atributos do
        `Evento`, e quem os calcula é o service (ver *Suposições declaradas*)
  - [x] **Sem `imagem_url` e sem `setores`**: a lista é enxuta de propósito, e o detalhe já tem os
        setores. Ver *Suposições declaradas*
  - [x] Docstring dizendo o que ele é — a vista de lista — e por que os totais vêm somados e não
        como lista de setores
  - [x] ⚠️ **`EventoSaida` não muda.** O detalhe reusa o schema da publicação inteiro

- [x] **T2. `app/services/evento.py` — as duas leituras** (AC: 1, 2, 3, 4, 6)
  - [x] `listar_do_organizador(sessao, organizador) -> list[EventoResumo]`
    - [x] `select(Evento).where(Evento.organizador_id == organizador.id)
          .order_by(Evento.data_hora).options(selectinload(Evento.setores))`
    - [x] ⚠️ **`selectinload` não é otimização prematura, é o AC4**: sem ele são N+1 consultas, uma
          por evento, e o custo cresce com o sucesso do organizador
    - [x] Somar `capacidade` e `vendidos` dos setores em Python, num só lugar, com comentário
          citando o **AD-13** — e dizendo que derivar por `COUNT` de reserva ou ingresso é proibido
    - [x] O parâmetro é o `Usuario` da sessão, **nunca** um `organizador_id` solto: é o que torna o
          AC2 uma questão de assinatura, não de disciplina de quem chama
  - [x] `obter_do_organizador(sessao, organizador, evento_id) -> Evento`
    - [x] Uma consulta com **as duas** condições (`id` e `organizador_id`) — não busque por id e
          confira o dono depois: são dois caminhos para a mesma decisão, e o segundo é o que alguém
          esquece
    - [x] `None` → `ErroDeDominio("EVENTO_NAO_ENCONTRADO", ..., 404)`. ⚠️ **Uma mensagem só** para
          "não existe" e "não é seu" — AC6
    - [x] `options(selectinload(Evento.setores), selectinload(Evento.portarias))`
  - [x] Docstring das duas explicando por que elas moram aqui (o mesmo argumento do
        `listar_portarias` da 2.5) e por que a rota não distingue os dois 404

- [x] **T3. `app/api/organizador.py` — as duas rotas** (AC: 5, 6, 7, 8)
  - [x] `@router.get("/eventos", response_model=list[EventoResumo])` e
        `@router.get("/eventos/{evento_id}", response_model=EventoSaida)`
  - [x] `organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` — aqui o objeto
        **é usado** (é o escopo), então **não** se chama `_`, ao contrário do `GET /portarias`
  - [x] `evento_id: UUID` como parâmetro de caminho — é o que dá o `422` do AC6 de graça
  - [x] Corpo de uma linha cada, chamando o service
  - [x] Docstring curta em cada uma: a de lista diz que o escopo é a sessão; a de detalhe diz por
        que o 404 é o mesmo para "não existe" e "não é seu"
  - [x] `app/main.py` **não muda**, e **não** nasce `app/api/eventos.py`

- [x] **T4. Testes do backend** (AC: 1–8, 19)
  - [x] `tests/test_organizador_meus_eventos.py` (arquivo novo), no molde do
        `test_organizador_portarias.py`: `_entrar` local, `fabricar_usuario` do `conftest.py`
  - [x] Um helper local que **grava um evento com setores** direto pelo ORM (a fixture de teste não
        precisa passar pela rota `POST`, e passar por ela acoplaria estes testes às quatro recusas
        da 2.4/2.5). Ele aceita `organizador`, `nome`, `data_hora` e os setores
  - [x] Lista: só os meus · ordenada por `data_hora` crescente · organizador sem evento → `200 []`
  - [x] Lista: `capacidade_total` e `vendidos_total` somam **dois** setores, com `vendidos`
        gravado diferente de zero na mão — um total que só é lido corretamente quando é soma
  - [x] Lista: evento de outro organizador não aparece (dois organizadores, um evento cada)
  - [x] Lista: o corpo tem **exatamente** as chaves do `EventoResumo` — nada de `setores`,
        `organizador_id` ou `imagem_url` vazando
  - [x] Detalhe: `200` com setores e portarias, com nome e e-mail; `senha_hash` ausente do texto
        inteiro da resposta
  - [x] Detalhe: id de outro organizador → `404 EVENTO_NAO_ENCONTRADO`, e o corpo **idêntico** ao
        de um `uuid4()` que não existe (compare os dois corpos, como a 2.5 fez com
        `PORTARIA_INVALIDA`)
  - [x] Detalhe: `/organizador/eventos/nao-e-uuid` → `422 DADOS_INVALIDOS`
  - [x] Detalhe: evento **sem portaria** (o resíduo da janela do AD-7) → `200` com
        `"portarias": []`, não erro
  - [x] Autorização, nas **duas** rotas: cliente → `403`; portaria → `403`; sem cookie → `401
        NAO_AUTENTICADO`
  - [x] OpenAPI: `GET /organizador/eventos` responde `list[EventoResumo]` e
        `GET /organizador/eventos/{evento_id}` responde `EventoSaida`
  - [x] ⚠️ **Nenhum teste antigo deve precisar mudar.** Se algum quebrar, algo saiu do escopo —
        pare e diga

- [x] **T5. `src/lib/formato.ts` — a extração** (AC: 9)
  - [x] Arquivo novo com `dataPorExtenso`, `momentoDaPublicacao` e `centavosParaReais`, **copiadas
        sem alterar uma linha** de `FormularioPublicacao.tsx`
  - [x] Módulo puro: **nenhum** import de `next/headers`, nenhum `"use client"` — ele é usado dos
        dois lados da fronteira, e é isso que o torna possível
  - [x] Docstring explicando o motivo real da extração (armadilha 1), não "para reusar"
  - [x] `FormularioPublicacao.tsx`: apagar as três declarações e importar de `@/lib/formato`.
        ⚠️ `reaisParaCentavos` **fica onde está** — ela é do formulário, não tem consumidor de
        servidor, e mover tudo "já que estou aqui" é escopo que ninguém pediu

- [x] **T6. `src/lib/eventos.ts` — as duas buscas de servidor** (AC: 10)
  - [x] Tipos `MeuEventoResumo` e `MeuEventoDetalhe` espelhando `EventoResumo` e `EventoSaida`
        (o segundo pode reusar os tipos que hoje moram em `FormularioPublicacao.tsx` — se reusar,
        **exporte-os de `lib/eventos.ts`** e importe lá, nunca o contrário)
  - [x] `listarMeusEventos()` → dois estados; `obterMeuEvento(id)` → **três**, com `404` virando
        `nao-encontrado` **antes** do `!resposta.ok` genérico
  - [x] `try/catch` que nunca levanta, `console.error` no molde dos outros dois módulos

- [x] **T7. A tela de lista** (AC: 11–14, 18)
  - [x] `src/app/(site)/organizador/eventos/page.tsx` — Server Component, as duas guardas
  - [x] `src/app/(site)/organizador/eventos/page.module.css` — **um módulo para as duas telas**
        (ver *Suposições declaradas*)
  - [x] `h1` "Meus eventos"; kicker por seção
  - [x] Partir a lista em duas com uma comparação de `Date`, futuro crescente e passado decrescente
  - [x] Fila: data à esquerda (dia + mês em mono), nome em serifada, `local · cidade`, e
        `{vendidos}/{capacidade}` à direita. `<Link>` envolvendo a fila inteira
  - [x] Estado vazio e estado indisponível, cada um com a sua frase — AC14
  - [x] Fio de 1px separando as filas; hover em `var(--breu2)`; **sem card, sem sombra, sem raio**
  - [x] Media query de 900px

- [x] **T8. A tela de detalhe** (AC: 15, 18)
  - [x] `src/app/(site)/organizador/eventos/[id]/page.tsx` — Server Component, as mesmas guardas
  - [x] ⚠️ `PageProps<"/organizador/eventos/[id]">`, e **`params` é `Promise`** no Next 16:
        `const { id } = await params`
  - [x] `nao-encontrado` → `notFound()`. ⚠️ Como o `redirect`, ele **levanta** e não pode ficar
        dentro de `try/catch` — o `try` mora dentro do `lib/eventos.ts`
  - [x] `indisponivel` → a frase, **não** `notFound()`: a API fora do ar não é evento inexistente
  - [x] Nome, `dataPorExtenso(data_hora)`, `local · cidade`, kicker `momentoDaPublicacao(...)`
  - [x] Inventário: uma linha por setor, com `{vendidos}/{capacidade}` e
        `R$ {centavosParaReais(preco_centavos)}` — números exatos, sem medidor (UX-DR7)
  - [x] `Na porta`: nome em serifada e e-mail em mono; lista vazia → frase, sem quebrar
  - [x] `← Meus eventos` de volta

- [x] **T9. Masthead e confirmação** (AC: 16, 17)
  - [x] `Masthead.tsx`: `<NavLink href="/organizador/eventos">Meus eventos</NavLink>` dentro do
        mesmo `usuario?.papel === "ORGANIZADOR" &&`, **antes** de `Publicar evento`
  - [x] Reescrever o comentário das Stories 4.1/2.6 — sobra só `Meus ingressos`
  - [x] `FormularioPublicacao.tsx`, bloco da confirmação: `Ver meus eventos →` ao lado de
        `Publicar outro →`, e o comentário que hoje diz *"não há para onde ir — 'Meus eventos' é a
        Story 2.6"* passa a explicar por que **continua** sem `redirect` (AC17)
  - [x] Uma classe nova no `publicar/page.module.css` se os dois links precisarem ficar lado a lado

- [x] **T10. Verificação** (AC: 18, 19)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos
  - [x] Conferir na tela, com `next dev` e `uvicorn` no ar, entrando como `organizador@rockhub.dev`:
    - [x] Publicar um evento com data **futura** e outro com data **passada** — a lista mostra as
          duas seções (o banco de desenvolvimento já tem dois eventos da 2.4/2.5)
    - [x] Abrir o detalhe de um evento publicado na janela do AD-7 (sem portaria) — a frase aparece
          e a tela não quebra
    - [x] Entrar como `cliente@rockhub.dev` e abrir `/organizador/eventos` → cai na raiz
    - [x] Abrir `/organizador/eventos/<uuid-que-não-existe>` → a 404 do projeto
  - [x] Abaixo de 900px: um bloco por linha, nada rolando na horizontal
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2 continua valendo)
  - [x] ⚠️ Conferir que os arquivos novos **estão rastreados** pelo git antes de dar a story por
        pronta — **não executo git** (regra do projeto); a conferência é do Igor, no `git status`
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** ao terminar

- [x] **T11. Os três READMEs** (AC: 20) — obrigatório, regra do projeto
  - [x] `backend/README.md`:
    - [x] Seção **Meus eventos** (depois de *Escalar a portaria*): as duas rotas, o `EventoResumo`,
          a soma pelo AD-13, o `EVENTO_NAO_ENCONTRADO` e por que o 404 é um só
    - [x] *Estrutura* e *Testes*: arquivo novo e número novo
    - [x] *Histórico desta camada*: entrada **Story 2.6**
  - [x] `frontend/README.md`:
    - [x] Seção nova para `/organizador/eventos` e `/organizador/eventos/[id]`
    - [x] **`src/lib/formato.ts` e por que ele existe** — a fronteira servidor/cliente, não faxina
    - [x] O corte em duas seções, e por que ele mora na tela e não na API
    - [x] *Estrutura*: os quatro arquivos novos; *Histórico desta camada*: entrada **Story 2.6**
  - [x] `README.md` da raiz — **a parte que o desafio avalia**:
    - [x] As quatro decisões desta story em *Decisões: por que isso e não aquilo*, **uma seção
          cada**, no formato das anteriores: o que decidi · por quê · o que caiu e por que não
    - [x] ⚠️ **Escreva o motivo que o Igor deu, não um motivo plausível.** A matéria-prima está em
          *Decisões que o Igor tomou*. Se faltar o porquê de alguma, **pergunte a ele**
    - [x] *O que não está pronto*: a linha sobre não haver como editar evento nem trocar a escala
          passa a ser explícita — agora existe a tela onde alguém procuraria por isso
    - [x] *Roteiro de avaliação*: o passo de publicar ganha o "e confira em Meus eventos"
    - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README da
raiz (T11) — é o "por quê" dele, e é isso que precisa aparecer lá, em primeira pessoa.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| O que "gerenciar" entrega | **Só ver.** A 2.6 é leitura pura: nenhuma rota de escrita, nenhuma migração. É o que os dois blocos de AC do `epics.md` pedem, e mantém a story do tamanho de um commit, que é a régua desta epic inteira. O "gerenciar" do título vira **acompanhar** | *Ver + trocar a escala da portaria depois de publicar*: fecharia a pergunta que ficou aberta na 2.5 (evento publicado na janela do AD-7 fica sem portaria para sempre) — caiu porque custa rota de escrita, invariante nova ("não deixar chegar a zero escalados"), tela e uma dúzia de testes, numa story que deveria ser um commit. E *ver + editar o evento inteiro*, que é a tela de editar evento já registrada como corte consciente na espinha: a regra difícil ali é capacidade não poder cair abaixo de `vendidos`, e isso é história para duas stories, não meia |
| Lista enxuta + detalhe, ou lista única | **Lista enxuta + página de detalhe.** A lista mostra data, nome, local e o total `vendidos/capacidade`; o detalhe abre os setores um a um e mostra quem está escalado na porta. É o desenho mais próximo do que uma plataforma real teria, e é **onde a edição moraria** se ela vier numa story futura — a rota `/organizador/eventos/[id]` já existiria | *Uma tela só, com os setores embutidos em cada fila*: é literalmente o que o AC do `epics.md` descreve, uma rota e uma chamada — caiu porque a fila deixa de ser fila. Com três setores por evento e dez eventos, a lista vira um paredão de números onde não dá para achar o show de sexta, e o UX-DR3 existe justamente para que a listagem seja escaneável |
| Evento cuja data já passou | **Duas seções na mesma tela**: `Em cartaz` (futuros, crescente) e `Já aconteceram` (passados, decrescente). O organizador continua com o histórico dele à mão, sem que ele ocupe o topo da operação de hoje. Custa uma comparação de data na tela e nenhum campo novo | *Uma lista só por data crescente*: menos código e menos texto — caiu porque um show de 2024 apareceria no meio da operação de hoje. E *filtrar no backend, devolvendo só os futuros*: tela mais limpa, ao custo de o organizador **perder** o histórico e de um evento sumir da conta dele sem explicação — além de pôr no backend uma regra de "o que interessa agora" que a Epic 5 vai querer diferente |
| O link no masthead | **Sim, e a confirmação de publicação aponta para lá.** A navegação do organizador passa a ser `Início · Meus eventos · Publicar evento · Minha conta` — a tela existe, então o link deixa de cair em 404, que era o único motivo de ele estar fora desde a 2.2. E a confirmação ganha `Ver meus eventos →` ao lado de `Publicar outro →` | *Redirect para a lista depois de publicar*, com o evento recém-criado no topo: é o que a maioria dos sistemas faz — caiu porque apagaria a tela de confirmação que a 2.4 e a 2.5 construíram, e é ali que o organizador vê o inventário e **quem ficou com a porta**, uma vez só, sem tela de editar para conferir depois. E *só o masthead, sem tocar na confirmação*: menos mudança em código já revisado, mas deixaria quem acabou de publicar sem caminho para o que acabou de criar |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **A rota da lista é `/organizador/eventos`, e a do detalhe `/organizador/eventos/[id]`.** O README
  da raiz já registra por que `/meus-eventos` caiu (fica perto demais de `/meus-ingressos` da Epic 4)
  e por que a tela do organizador mora dentro da casca `(site)`. Esta é a continuação literal
  daquela decisão.
- **`EVENTO_NAO_ENCONTRADO` é o nome do código, e ele é `404`.** Poderia ser o `NAO_ENCONTRADO`
  genérico que o `CODIGO_POR_STATUS` já dá de graça para qualquer `404` do framework; um código
  próprio deixa a tela distinguir "esse evento não é seu" de "esse endereço não existe nesta API",
  que é a diferença entre `notFound()` e um bug de URL.
- **O service devolve `list[EventoResumo]`, e não `Evento` do ORM.** Os dois totais não são
  atributos da entidade — são uma vista de leitura. A alternativa era `@computed_field` no schema ou
  uma `@property` no modelo; as duas escondem a soma do AD-13 na camada de serialização, onde o
  teste que a prova fica um passo mais longe. Precedente: `ticketmaster.buscar_eventos` também
  devolve schema, não ORM.
- **A lista não traz `imagem_url`.** A miniatura serve no passo 1 da publicação, para reconhecer a
  atração entre duas parecidas; aqui o organizador já sabe o que publicou, e a fila de jornal é
  data, nome e local. Se o Igor quiser a imagem, é um campo no schema e uma linha na tela.
- **Um `page.module.css` para as duas telas**, em `eventos/`, importado pelo detalhe como
  `../page.module.css`. Elas compartilham o vocabulário de fila e de inventário, e dois arquivos
  quase iguais divergiriam na primeira mudança. Precedente: `FormularioPublicacao` já importa o
  módulo da página que o hospeda.
- **O corte "em cartaz / já aconteceram" acontece na tela, não na API.** A API responde "quais são
  os meus eventos"; "o que interessa agora" é leitura, e o relógio que decide é o de quem lê. Pôr o
  corte no backend criaria dois endpoints ou um parâmetro que a Epic 5 vai querer diferente.
- **`momentoDaPublicacao` vai junto para o `lib/formato.ts`**, mesmo tendo hoje um consumidor só —
  o detalhe é o segundo, e deixar duas das três funções num lugar e a terceira no outro é a pior das
  duas opções.
- **Nenhuma paginação.** Um organizador de avaliação tem unidades de eventos. Paginar agora custaria
  parâmetro, contagem total e navegação na tela, para resolver um problema que este projeto não tem.

### O contrato da API, campo a campo

**`GET /organizador/eventos`** · `200` · `response_model=list[EventoResumo]`

```json
[
  {
    "id": "3f2a…",
    "nome": "Baco Exu do Blues — Bluesman Vivo",
    "data_hora": "2026-08-15T00:00:00Z",
    "local": "Espaço Unimed",
    "cidade": "São Paulo",
    "publicado_em": "2026-08-11T17:22:04Z",
    "capacidade_total": 860,
    "vendidos_total": 12
  }
]
```

| Campo | Tipo | De onde vem |
|---|---|---|
| `capacidade_total` | `int` | Soma de `setor.capacidade` — AD-13 |
| `vendidos_total` | `int` | Soma de `setor.vendidos` — AD-13, **nunca** `COUNT` de reserva ou ingresso |

Ordenada por `data_hora` crescente. Escopo pelo `organizador_id` da **sessão**. Sem paginação e sem
filtro.

**`GET /organizador/eventos/{evento_id}`** · `200` · `response_model=EventoSaida` — **o mesmo schema
da publicação**, sem um campo novo:

```json
{
  "id": "3f2a…", "nome": "…", "data_hora": "…", "local": "…", "cidade": "…",
  "imagem_url": "…", "origem_externa_id": "G5vYZ9a1kd", "publicado_em": "…",
  "setores": [{ "id": "9c1b…", "nome": "Pista", "capacidade": 800, "vendidos": 12,
               "preco_centavos": 12000 }],
  "portarias": [{ "id": "7c2f…", "nome": "Ana Sampaio", "email": "portaria2@rockhub.dev" }]
}
```

**Código de erro novo:**

| Código | Status | Quando |
|---|---|---|
| `EVENTO_NAO_ENCONTRADO` | `404` | O id não existe **ou** o evento é de outro organizador |

É `ErroDeDominio`, e o handler de `app/main.py` já o traduz para o formato único. **Nenhum handler
novo, nenhuma migração, nenhuma dependência.**

[Fonte: ARCHITECTURE-SPINE.md#AD-9, #AD-13 · backend/app/core/erros.py · backend/app/schemas/evento.py]

### As telas, em texto

O protótipo **não desenha** a tela de "Meus eventos" — ele só tem o link no masthead
(`proto-jornal-noturno.html:550`). O vocabulário abaixo é o da fila de listagem que o projeto já
usa em `/organizador/publicar` e o do inventário da confirmação. Grade e espaçamento continuam
sendo o que se ajusta livremente (`DESIGN.md#Como usar este documento`).

**Lista** — `/organizador/eventos`

```
  MEUS EVENTOS

  EM CARTAZ
  ─────────────────────────────────────────────────────────────────
  15 AGO   Baco Exu do Blues — Bluesman Vivo          12/860
  2026     Espaço Unimed · São Paulo
  ─────────────────────────────────────────────────────────────────
  22 AGO   Sepultura — Celebrating Life                0/1200
  2026     Circo Voador · Rio de Janeiro
  ─────────────────────────────────────────────────────────────────

  JÁ ACONTECERAM
  ─────────────────────────────────────────────────────────────────
  02 MAI   Sticky Fingers                            340/400
  2026     Fundição Progresso · Rio de Janeiro
  ─────────────────────────────────────────────────────────────────
```

**Detalhe** — `/organizador/eventos/[id]`

```
  ← MEUS EVENTOS

  PUBLICADO EM 11 DE AGOSTO, 17H22
  Baco Exu do Blues — Bluesman Vivo
  15 de agosto de 2026, 21h00 · Espaço Unimed · São Paulo

  SETORES
  ─────────────────────────────────────────────────────────────────
  PISTA         12/800 vendidos          R$ 120,00
  CAMAROTE       0/60  vendidos          R$ 420,00
  ─────────────────────────────────────────────────────────────────

  NA PORTA
  Ana Sampaio      PORTARIA2@ROCKHUB.DEV
  Jonas Ribeiro    PORTARIA@ROCKHUB.DEV
```

- Nome do show e data por extenso em **serifada**; data da fila, números, rótulos e e-mail em
  **mono versalete** — UX-DR2
- Fio embaixo de cada fila. **Sem caixa, sem sombra, sem raio** — UX-DR3
- Fila inteira clicável, hover em `var(--breu2)`, como o catálogo do passo 1
- **Números exatos, sem medidor e sem proporção**: é o inventário de quem é dono da informação
  (UX-DR7). Medidor é da tela do cliente, na Epic 3
- Estado vazio: kicker, frase, fim. Sem ilustração, sem botão grande (EXPERIENCE.md#Vazio)

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `EventoSaida`, `SetorSaida`, `PortariaSaida` | `app/schemas/evento.py` | **Reuse inteiro** no detalhe. Só `EventoResumo` é novo |
| `publicar()`, `listar_portarias()` | `app/services/evento.py` | **Não mexa.** As duas funções novas entram ao lado |
| `Evento`, `Setor`, `evento_portaria` | `app/models/evento.py` | **Não mexa.** Esta story não toca o banco |
| `exigir_papel` | `app/core/dependencias.py:81` | As duas rotas. Já garante `401` antes de `403` |
| `ErroDeDominio` | `app/core/erros.py:88` | O código novo, com `status_http=404` |
| Router do organizador | `app/api/organizador.py` | **Estenda.** Não crie `app/api/eventos.py` |
| `_entrar`, `fabricar_usuario` | `tests/test_organizador_portarias.py:22` · `tests/conftest.py:139` | O molde do arquivo de teste novo |
| `_portaria_chamada` | `tests/test_organizador_portarias.py:29` | O precedente de helper local quando a fixture compartilhada não basta — aqui o caso é o mesmo: `fabricar_usuario` grava todo mundo como "Alguém" |
| `buscarNoCatalogo`, `listarPortarias` | `frontend/src/lib/catalogo.ts`, `portarias.ts` | O **molde exato** de `eventos.ts`: resultado discriminado, nunca levanta |
| `cabecalhoDeSessao` | `frontend/src/lib/servidor.ts:51` | O cookie repassado à mão no `fetch` de servidor |
| `dataPorExtenso`, `momentoDaPublicacao`, `centavosParaReais` | `frontend/src/components/FormularioPublicacao.tsx:115-151` | **Mova para `lib/formato.ts`** — armadilha 1 |
| Guardas de página | `frontend/src/app/(site)/organizador/publicar/page.tsx:47-54` | Copie o par exato, trocando o `?voltar=` |
| `notFound()` e a 404 do projeto | `frontend/src/app/not-found.tsx` | Já existe e já tem a casca. Não crie outra |
| `NavLink`, `Masthead` | `frontend/src/components/` | Um `<NavLink>` a mais, dentro da condição de papel que já existe |
| `.item`, `.itemEscolhido`, `.inventario`, `.linhaInventario` | `publicar/page.module.css` | O vocabulário visual de fila e de inventário já está escrito — leia antes de inventar classe |
| Tokens | `frontend/src/app/globals.css` | `var(--fio)`, `var(--breu2)`, `var(--ambar)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)` |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, `migrations/`, `seeds/`,
`app/core/`, `app/main.py`, `app/integrations/`, `app/schemas/auth.py`,
`app/services/autenticacao.py`, `tests/conftest.py`, `docker-compose.yml`, `pyproject.toml`,
`package.json`, `frontend/src/lib/servidor.ts`, `sessao.ts`, `api.ts`, `caminho.ts`, e as telas de
`(entrada)/`.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Server Component não consegue chamar função de módulo `"use client"`.** É a armadilha central
desta story, e ela tem duas camadas: `dataPorExtenso`, `momentoDaPublicacao` e `centavosParaReais`
**não são exportadas** hoje (são privadas do módulo), e mesmo que fossem, o Next transforma cada
export de um arquivo `"use client"` numa referência de cliente — chamá-la do servidor estoura em
tempo de execução, não em build. As duas saídas erradas são copiar as funções para as telas novas
(duas fontes para o mesmo formato de data) e marcar as telas novas como `"use client"` (jogar fora
o Server Component por causa de um `Intl.DateTimeFormat`). A saída certa é o `lib/formato.ts` do
AC9.

**2. N+1 na lista.** `select(Evento)` seguido de `evento.setores` dentro de um laço emite uma
consulta por evento, e o sintoma só aparece com volume — ou seja, nunca, na avaliação. É o AC4, e o
conserto é uma linha: `.options(selectinload(Evento.setores))`.

**3. `params` é `Promise` no Next 16.** `const { id } = await params`, com
`PageProps<"/organizador/eventos/[id]">`. Um modelo com Next 14 na memória escreve
`{ params }: { params: { id: string } }` e o `tsc` reclama — ou pior, não reclama e o `id` vira
`undefined` em tempo de execução. **Leia `frontend/AGENTS.md` antes de escrever TSX.**

**4. `notFound()` levanta, como o `redirect()`.** Ele não pode ficar dentro de `try/catch` — o
`try` mora dentro do `lib/eventos.ts`, e o que sobra na página é um `if`. É exatamente o que o
docstring da `/conta` já registra sobre o `redirect`.

**5. Um `404` da API não é "indisponível".** Se o `obterMeuEvento` tratar todo `!resposta.ok` do
mesmo jeito, o evento de outro organizador vira "a API não respondeu" e a tela mente. Confira o
`resposta.status === 404` **antes** do caso genérico — é o AC10.

**6. `response_model` esquecido vaza o modelo inteiro.** Sem `response_model=list[EventoResumo]`, o
FastAPI serializa o que o service devolver; sem `response_model=EventoSaida` no detalhe, um
`Usuario` cru dentro de `portarias` traria `senha_hash`. Os testes que afirmam a ausência da chave
existem por isso.

**7. Conferir o dono depois de buscar por id.** `sessao.get(Evento, id)` seguido de
`if evento.organizador_id != organizador.id` funciona e cria dois caminhos para a mesma decisão. Uma
consulta com as duas condições não tem como esquecer a segunda — e é ela que torna o AC2 verdadeiro
por construção.

**8. Comparar data como texto.** `"2026-08-15T00:00:00Z" > new Date().toISOString()` funciona por
acidente enquanto todos os offsets forem `Z`, e para de funcionar no primeiro `-03:00`. Compare
`Date` com `Date`.

**9. O `TestClient` guarda cookie entre chamadas.** Um teste que faz login e depois quer provar o
`401` precisa de outra instância ou de `cliente.cookies.clear()` — está no docstring da fixture.

**10. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest`
falhar com `os error 4551`, chame pelo módulo: `uv run python -m pytest`. Documentado desde a 1.1.

**11. O banco de desenvolvimento tem dois eventos de conferência**, `Sticky Fingers - Rio de
Janeiro` (2.4, **sem portaria** — resíduo da janela do AD-7) e `Rock in Rio 2026 (conferencia 2.5)`.
Eles são exatamente o cenário do AC15 e da seção "já aconteceram", dependendo da data que têm.
**Não apague nada:** o banco é do Igor.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      organizador.py             # +GET /eventos, +GET /eventos/{evento_id}
    schemas/
      evento.py                  # +EventoResumo
    services/
      evento.py                  # +listar_do_organizador(), +obter_do_organizador()
  tests/
    test_organizador_meus_eventos.py   # NOVO
  README.md
frontend/
  src/
    lib/
      formato.ts                 # NOVO — as três funções que saíram da ilha
      eventos.ts                 # NOVO — no molde do catalogo.ts
    app/(site)/organizador/eventos/
      page.tsx                   # NOVO — a lista
      page.module.css            # NOVO — compartilhado com o detalhe
      [id]/
        page.tsx                 # NOVO — o detalhe
    components/
      Masthead.tsx               # +Meus eventos
      FormularioPublicacao.tsx   # -3 funções, +import, +link na confirmação
  README.md
README.md                        # decisões + o que não está pronto + roteiro
```

Não existe, e não deve passar a existir nesta story: `app/api/eventos.py`, migração, coluna,
`services/relatorio.py`, rota de escrita, tela de editar evento, edição da escala, paginação,
filtro por termo, `error.tsx`, teste automatizado de frontend, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar (login de verdade) e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| A lista traz só os eventos do organizador da sessão | `test_organizador_meus_eventos.py` | 1, 2 |
| Evento de outro organizador não aparece | `test_organizador_meus_eventos.py` | 2 |
| Ordenada por `data_hora` crescente (gravados fora de ordem) | `test_organizador_meus_eventos.py` | 1 |
| Organizador sem evento → `200 []` | `test_organizador_meus_eventos.py` | 1 |
| `capacidade_total`/`vendidos_total` somam dois setores, com `vendidos` ≠ 0 | `test_organizador_meus_eventos.py` | 3 |
| O corpo tem exatamente as chaves de `EventoResumo` | `test_organizador_meus_eventos.py` | 1 |
| Detalhe traz setores e portarias, com nome e e-mail | `test_organizador_meus_eventos.py` | 5 |
| Nenhuma chave `senha_hash` na resposta do detalhe | `test_organizador_meus_eventos.py` | 5 |
| Detalhe de evento alheio → `404 EVENTO_NAO_ENCONTRADO` | `test_organizador_meus_eventos.py` | 6 |
| O corpo desse `404` é **idêntico** ao de um id inexistente | `test_organizador_meus_eventos.py` | 6 |
| Id em formato inválido → `422 DADOS_INVALIDOS` | `test_organizador_meus_eventos.py` | 6 |
| Evento sem portaria → `200` com `"portarias": []` | `test_organizador_meus_eventos.py` | 15 |
| Cliente → `403`; portaria → `403`; sem cookie → `401`, nas **duas** rotas | `test_organizador_meus_eventos.py` | 7 |
| O OpenAPI declara `EventoResumo` na lista e `EventoSaida` no detalhe | `test_organizador_meus_eventos.py` | 5 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são sete caminhos:

1. Entrar como `organizador@rockhub.dev` → `Meus eventos` aparece no masthead, antes de
   `Publicar evento`
2. Abrir a lista → os eventos publicados nas 2.4/2.5 aparecem, com o total `vendidos/capacidade`
3. Clicar numa fila (em qualquer ponto dela, não só no nome) → o detalhe abre
4. O detalhe do evento publicado na janela do AD-7 → `Na porta` mostra a frase de "ninguém
   escalado", sem quebrar
5. Publicar um evento novo → a confirmação mostra `Ver meus eventos →`, e ele aparece na lista
6. Entrar como `cliente@rockhub.dev` e digitar `/organizador/eventos` → vai para a raiz, e
   `Meus eventos` não está no masthead
7. Abaixo de 900px: um bloco por linha, nada rolando na horizontal; e navegar por Tab com foco
   visível em âmbar

**Baseline: 187 testes passando** (`backend/README.md#Testes`, conferido em 2026-08-11, ao fim da
Story 2.5). Registre o número final no `backend/README.md` e nas notas de conclusão.

### Inteligência das stories anteriores

**Da 2.5 — a story imediatamente anterior:**

- **A rota de leitura do organizador passa por service**, mesmo sem invariante nenhuma, porque toca
  o banco. O critério inteiro está no docstring de `app/api/organizador.py`, e as duas rotas desta
  story caem no mesmo caso.
- **Um código de erro, uma mensagem, para casos que o cliente não precisa distinguir.** Foi assim
  com `PORTARIA_INVALIDA` ("não existe" × "não é portaria"), e é assim com o `404` daqui ("não
  existe" × "não é seu").
- **`PortariaSaida` não reusou `UsuarioSaida`** porque significado não é forma. Aqui o caminho é o
  oposto e por isso mesmo consistente: `EventoSaida` **é** o mesmo significado nas duas rotas — "o
  evento inteiro, como o organizador o vê" — então reusar é o certo.
- **A `fabricar_usuario` do `conftest.py` grava todo mundo como "Alguém"**, e por isso não serve
  para teste de ordenação. O helper local resolveu lá e o precedente vale aqui, para os eventos.
- **`preventDefault` no Enter de campo de busca dentro de `<form>`**: não há formulário nas telas
  desta story, mas a lição geral vale — leia o que a tela faz com teclado antes de dar por pronta.

**Da 2.4 — a publicação:**

- **A confirmação não redireciona, e o motivo mudou de dono.** Naquela story era "não há para onde
  ir"; agora existe para onde ir, e a decisão de **continuar** sem `redirect` é do Igor, com motivo
  próprio (AC17). Atualize o comentário do código junto — comentário que explica um motivo que
  deixou de valer é pior que nenhum.
- **A tela ganhou `#passo-2` depois que o Igor a usou**, porque o conteúdo nascia abaixo da dobra.
  Confira as telas novas no navegador, não só no código.

**Da 2.3 — o schema:** `setor.vendidos` é a única fonte de verdade da disponibilidade (AD-13), e o
`UPDATE` condicional da Epic 3 é quem vai mexer nele. Esta story só **lê** — e é a primeira que lê.

**Da 2.2 — o padrão de busca no servidor:** `buscarNoCatalogo` **nunca levanta**, porque não existe
`error.tsx` e uma exceção num Server Component derruba a tela inteira. `eventos.ts` nasce com a
mesma disciplina.

**Da 1.6 — autorização:** papel se declara na assinatura. `401` antes de `403` é garantido pelo
`Depends` encadeado, não por ordem de `if`.

**Da 1.4 — a disciplina do oráculo:** o login não diz se o e-mail existe. É a mesma regra que faz o
`404` desta story ser um só.

[Fonte: _bmad-output/implementation-artifacts/2-5-*.md · 2-4-*.md · 2-2-*.md · 1-6-*.md ·
sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `@router.get` com parâmetro de caminho `UUID` e `response_model` |
| Pydantic | 2.13.4 | `EventoResumo`, e o `422` de UUID malformado |
| SQLAlchemy | 2.0.51 | `select`, `where` com duas condições, `selectinload`, `order_by` |
| Alembic | 1.19.1 | **Não é usado nesta story** — nenhuma migração |
| Next.js | **16.3.0** | `params` é **Promise**; `PageProps<"/rota/[id]">` é global e gerado; `notFound()` de `next/navigation` |
| React | 19 | Server Component em tudo que é novo; a única ilha continua sendo o formulário |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** Esta versão do Next tem quebras em relação ao
que um modelo tem memorizado; a documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

[Fonte: ARCHITECTURE-SPINE.md#Stack · backend/pyproject.toml · frontend/package.json]

### Escopo — o que NÃO fazer aqui

Editar evento · trocar a escala depois de publicar · cancelar ou despublicar · duplicar evento ·
paginação, busca ou filtro na lista · gráfico, painel ou métrica de vendas · listagem pública (3.1) ·
página pública do evento (3.4) · qualquer rota de portaria (Epic 5) · `Meus ingressos` no masthead
(4.1) · teste automatizado de frontend · migração de qualquer tipo.

Cinco tentações concretas:

- **"Já ponho um botão de editar, a tela é essa."** É — e editar é decisão do Igor, que ele já tomou:
  esta story é só leitura. Botão que não faz nada é pior que botão ausente
- **"Copio as três funções de formatação para a tela nova, é mais rápido."** É, e cria a segunda
  fonte do mesmo formato de data. O AC9 pede a extração, e a armadilha 1 explica por que ela nem é
  opcional
- **"Marco as telas como `use client`, aí posso importar do `FormularioPublicacao`."** Isso é jogar
  fora o Server Component por causa de um `Intl.DateTimeFormat`, e contraria a convenção do projeto
  desde a 1.2
- **"Aproveito e semeio um evento, agora que existe tela para vê-lo."** Continua sendo decisão de
  produto do Igor — qual show, qual data, quais setores, quais preços —, e está registrada em *O que
  não está pronto*
- **"Faço a lista devolver só os futuros, é mais limpo."** É a opção que o Igor descartou, com
  motivo escrito na tabela de decisões

### Project Structure Notes

Esta é a **primeira tela de leitura de domínio** do projeto — todas as anteriores ou eram formulário
(login, cadastro, publicar) ou eram vista de um dado externo (o catálogo). É também a primeira vez
que uma rota do backend devolve um schema que **não** espelha uma linha do banco: `EventoResumo`
carrega dois totais que não existem em coluna nenhuma, e é o service quem os produz. As Epics 3 e 5
vão repetir esse desenho — a programação pública e o painel de entradas do turno são o mesmo tipo
de vista.

É também o momento em que o `app/api/organizador.py` fica com **cinco** rotas e o critério do seu
docstring passa a ter dois exemplos de cada lado: duas leituras que passam por service porque tocam
o banco (`/portarias` e as duas novas), uma leitura que não passa porque não toca (`/catalogo`), e
uma escrita que passa por transação e invariante (`POST /eventos`). Se ele crescer mais na Epic 3,
partir por assunto passa a valer a discussão — hoje não vale, e o docstring é o que segura a
coerência.

No frontend, o `lib/formato.ts` é a terceira vez que uma função sai de onde nasceu para virar módulo
compartilhado, e a primeira em que o motivo é **físico** e não estético: a fronteira
servidor/cliente do React Server Components não é convenção, é limite de execução. Vale registrar
assim no README — é o tipo de "por quê" que o desafio avalia, e é diferente do "extraí porque
apareceu o terceiro consumidor" que já está escrito lá para `Campo` e `Botao`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] — os dois blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR2, FR8, FR16 e o objetivo da epic
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel declarado na assinatura, nunca `if` no corpo
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade;
  proibido derivar por `COUNT`, **inclusive em tela do organizador**
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`; router não toca a
  `Session`
- [Source: ARCHITECTURE-SPINE.md#Convenções] — erro sempre `{"erro": {...}}`; Server Component por
  padrão
- [Source: ARCHITECTURE-SPINE.md#Adiado] — tela de editar evento e teste de frontend, os dois cortes
  que esta story não reabre
- [Source: EXPERIENCE.md#Information Architecture] — a navegação do organizador: `Meus eventos ·
  Publicar evento · Minha conta`
- [Source: EXPERIENCE.md#Component Patterns/medidor] — "organizador e portaria veem números exatos —
  é o inventário deles"
- [Source: EXPERIENCE.md#Component Patterns/fila-listagem] — a fila inteira é clicável, hover em
  `breu2`
- [Source: EXPERIENCE.md#Vazio] — kicker, frase, fim; sem ilustração e sem botão grande
- [Source: DESIGN.md#Como usar este documento] — grade e espaçamento são provisórios; a ausência de
  card, sombra e raio é duradoura
- [Source: mockups/proto-jornal-noturno.html:550] — o link no masthead do organizador; **não há
  protótipo da tela em si**
- [Source: backend/app/api/organizador.py] — o router a estender e o critério "existe transação ou
  invariante?"
- [Source: backend/app/services/evento.py:175] — `listar_portarias`, o precedente de leitura com
  service
- [Source: backend/app/schemas/evento.py:166] — `EventoSaida`, reusado inteiro no detalhe
- [Source: backend/app/core/erros.py:17] — `CODIGO_POR_STATUS`, e por que o código próprio ganha do
  `NAO_ENCONTRADO` genérico
- [Source: backend/tests/test_organizador_portarias.py] — o molde do arquivo de teste novo
- [Source: frontend/src/lib/catalogo.ts] — o molde de `eventos.ts`
- [Source: frontend/src/lib/servidor.ts:51] — o cookie repassado à mão no `fetch` de servidor
- [Source: frontend/src/components/FormularioPublicacao.tsx:122-151] — as três funções que mudam de
  casa
- [Source: frontend/src/app/(site)/organizador/publicar/page.tsx:47-54] — o par de guardas a copiar
- [Source: frontend/src/components/Masthead.tsx:38] — o comentário que esta story reescreve
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: README.md#a-tela-do-organizador-mora-em-organizadorpublicar] — por que `/meus-eventos`
  caiu e a rota desta tela é `/organizador/eventos`
- [Source: README.md#o-que-não-está-pronto] — a linha sobre editar evento, que esta story torna
  explícita
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do
  Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os três READMEs antes de dar a story por concluída.** As decisões da T11 são a parte
   que o desafio avalia — e **o "por quê" precisa ser o do Igor**, em primeira pessoa. Se faltar o
   motivo de alguma, pergunte a ele em vez de escrever um plausível
3. **Decisão de produto ou de modelagem é do Igor.** As quatro desta story estão respondidas e as
   oito suposições estão declaradas. Se aparecer uma quinta — campo a mais, regra a mais, tela a
   mais — **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente — vale para o `npm run dev` desta story
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os cinco arquivos novos foram rastreados (T10)
8. **Esta é a última story da Epic 2.** Depois dela vem o `bmad-code-review` da epic inteira, e só
   quando o Igor mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **Evento com data no passado continua aceito na publicação** (pergunta herdada da 2.4 e da 2.5).
   Com a tela de "Meus eventos" existindo, agora dá para **ver** o efeito: um show de 2024 publicado
   hoje aparece direto em "Já aconteceram". Vale decidir antes da Epic 3, que vai listar isso para o
   público.
2. **A escala e os dados do evento continuam sem como mudar depois de publicados.** Esta story
   decidiu que não é aqui; a tela onde isso moraria agora existe. Se virar story, é decisão sua e
   provavelmente vale mais no fim do prazo, com o fluxo obrigatório de pé.
3. **Nenhum evento é semeado.** A tela de "Meus eventos" nasce vazia numa máquina limpa, e quem
   avaliar só a vê preenchida depois de publicar um evento pela interface — o que é justamente o
   roteiro de avaliação. Se quiser um evento semeado, é decisão de produto sua (qual show, qual
   data, quais setores, quais preços) e uma alteração no `seeds/semear.py`.
4. **A lista não mostra imagem.** Suposição declarada, uma linha para trocar se você quiser a
   miniatura do catálogo na fila.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context) — via `bmad-dev-story`

### Debug Log References

Três tropeços, todos corrigidos dentro da story:

1. **`setores or [("Pista", 800, 0)]` no helper de teste.** Lista vazia é falsy, então o teste que
   existe para provar que "evento sem setor nenhum soma zero" recebia um setor de brinde e falhava
   com `assert 800 == 0`. Trocado por `if setores is None:`. O helper era novo — nenhum teste antigo
   foi afetado.
2. **`PageProps<"/organizador/eventos/[id]">` não existia no primeiro `tsc --noEmit`.** Os tipos de
   rota do Next são **gerados** em `.next/types`, e a rota tinha acabado de nascer. `npm run build`
   antes do `tsc` resolve; não é erro de código.
3. **`Date.now()` no corpo do Server Component foi reprovado pelo ESLint** (`react-hooks/purity`),
   e com razão: ler o relógio na renderização é impuro, e um evento que começa exatamente agora
   poderia cair numa seção no primeiro filtro e na outra no segundo. Corrigido com `cache()` do
   React — o valor nasce uma vez por requisição —, que é a mesma mecânica do `obterUsuarioDaSessao`.
   Correção de regra, não supressão de aviso.

### Completion Notes List

**Backend.** `EventoResumo` novo em `schemas/evento.py`, sem `from_attributes` — os dois totais não
são atributos do ORM. `listar_do_organizador()` e `obter_do_organizador()` em `services/evento.py`,
com `selectinload` na lista (AC4) e a consulta de duas condições no detalhe (AC2/AC6). As duas rotas
em `api/organizador.py`, com `Depends(exigir_papel(...))` na assinatura e `evento_id: UUID` no
caminho. `EVENTO_NAO_ENCONTRADO` é `404`, com **uma mensagem só** para "não existe" e "não é seu".
Nenhuma migração, modelo, coluna ou dependência.

**Frontend.** `lib/formato.ts` (as três funções que saíram da ilha `"use client"`, com o motivo
físico no docstring), `lib/eventos.ts` (dois estados na lista, **três** no detalhe), a tela de lista
com o corte em `Em cartaz`/`Já aconteceram` feito com `Date` contra `Date`, a tela de detalhe com
`notFound()` fora de qualquer `try`, e um `page.module.css` para as duas. `Meus eventos` entrou no
masthead antes de `Publicar evento`; a confirmação de publicação ganhou `Ver meus eventos →` e
**continua sem `redirect`**.

⚠️ **Reuso de tipo que a story previa:** `FormularioPublicacao.tsx` deixou de declarar
`EventoPublicado`/`SetorPublicado`/`PortariaPublicada` e passou a importar `MeuEventoDetalhe` de
`lib/eventos.ts`, via `import type` — que o compilador apaga, então nada daquele módulo (que fala com
`next/headers`) atravessa para o bundle do navegador. O sentido é o que a T6 mandou: exportado de
`lib/`, importado pelo componente, nunca o contrário.

**Verificação.** `uv run python -m pytest` → **203 testes passando** (187 anteriores + 16 novos), e
**nenhum teste antigo precisou mudar**. `npm run build`, `npx tsc --noEmit` e `npm run lint`, os três
limpos. `NEXT_PUBLIC` em `frontend/src/` → zero.

**Conferência na tela**, com `next dev` e `uvicorn` no ar, como `organizador@rockhub.dev`: masthead
na ordem certa; lista com as duas seções (o banco de desenvolvimento tem um evento de 2001, que caiu
em `Já aconteceram`) e os totais somados; detalhe do `Sticky Fingers` — o resíduo da janela do AD-7 —
mostrando a frase de "ninguém escalado" sem quebrar; `cliente@rockhub.dev` em `/organizador/eventos`
→ raiz, e sem `Meus eventos` no masthead; sem sessão → `/login?voltar=%2Forganizador%2Feventos`;
UUID inexistente → a 404 do projeto, com a casca.

**Ajuste depois de ver a tela:** o Igor apontou que o `← Meus eventos` do detalhe estava pequeno
demais. Ele nasceu com os 10px dos kickers, que é tamanho de etiqueta, não de navegação — subiu para
14px com `padding` de alvo, mantendo o mono versalete do UX-DR2.

⚠️ **Dois pontos para o Igor, nenhum bloqueante:**

- **Não executei git** (regra do projeto). Os **cinco arquivos novos** — `lib/formato.ts`,
  `lib/eventos.ts`, as duas `page.tsx` de `organizador/eventos/`, o `page.module.css` e o
  `tests/test_organizador_meus_eventos.py` — precisam de conferência no `git status` antes do commit:
  arquivo que nunca entrou no índice não é pego por `npm run build` nem pela suíte, e o primeiro
  clone limpo é o da Vercel.
- **Os servidores das portas 3000 e 8000 já estavam no ar antes desta sessão** (PIDs 22704 `node` e
  8840 `python`) e **não foram encerrados** — eles não são meus, e derrubá-los interromperia o que
  você estivesse usando. Os dois processos que **eu** subi morreram sozinhos, sem conseguir ligar
  nas portas.

### File List

**Backend**

- `backend/app/schemas/evento.py` — modificado: `EventoResumo`
- `backend/app/services/evento.py` — modificado: `listar_do_organizador()`, `obter_do_organizador()`
- `backend/app/api/organizador.py` — modificado: as duas rotas de `GET` e o docstring do módulo
- `backend/tests/test_organizador_meus_eventos.py` — **novo**, 16 testes
- `backend/README.md` — modificado: seção *Meus eventos*, *Estrutura*, *Testes*, *Histórico*

**Frontend**

- `frontend/src/lib/formato.ts` — **novo**
- `frontend/src/lib/eventos.ts` — **novo**
- `frontend/src/app/(site)/organizador/eventos/page.tsx` — **novo**
- `frontend/src/app/(site)/organizador/eventos/page.module.css` — **novo**, compartilhado com o detalhe
- `frontend/src/app/(site)/organizador/eventos/[id]/page.tsx` — **novo**
- `frontend/src/components/FormularioPublicacao.tsx` — modificado: −3 funções, −3 tipos, +imports,
  +`Ver meus eventos →`, comentário do `redirect` reescrito
- `frontend/src/components/Masthead.tsx` — modificado: `Meus eventos` e o comentário das Stories 4.1/2.6
- `frontend/src/app/(site)/organizador/publicar/page.module.css` — modificado: `.saidas`/`.saida`
- `frontend/README.md` — modificado: seção *Meus eventos*, *Estrutura*, lista de conferência manual,
  *Histórico*

**Raiz**

- `README.md` — modificado: quatro decisões novas, *O que não está pronto*, *Roteiro de avaliação*,
  estado atual
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modificado: status da story
- `_bmad-output/implementation-artifacts/2-6-ver-e-gerenciar-meus-eventos.md` — este arquivo

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Story 2.6 implementada. Backend: `EventoResumo` (o primeiro schema deste projeto que não espelha uma linha do banco — `capacidade_total` e `vendidos_total` são soma de setor, AD-13), `listar_do_organizador()` com `selectinload`, `obter_do_organizador()` com as duas condições numa consulta só, e as rotas `GET /organizador/eventos` e `GET /organizador/eventos/{evento_id}` em `api/organizador.py`, que ficou com cinco rotas e dois exemplos de cada lado do critério de service. `EVENTO_NAO_ENCONTRADO` responde `404` **idêntico** para "não existe" e "não é seu", provado comparando os dois corpos. Nenhuma migração, coluna ou dependência. Frontend: `lib/formato.ts` — extração que não foi faxina, porque Server Component não consegue chamar export de módulo `"use client"` —, `lib/eventos.ts` com **três** estados no detalhe (`404` conferido antes do `!ok` genérico), a lista partida em `Em cartaz`/`Já aconteceram` com `Date` contra `Date`, o detalhe com `notFound()` fora de qualquer `try`, um `page.module.css` para as duas telas, `Meus eventos` no masthead antes de `Publicar evento`, e `Ver meus eventos →` na confirmação — que continua **sem `redirect`**, agora por decisão e não por falta de destino. Dezesseis testes novos, suíte de 187 para **203**, nenhum teste antigo alterado; `build`, `tsc --noEmit` e `lint` limpos. Dois ajustes durante a implementação: `Date.now()` no render virou `cache()` do React depois de o ESLint reprovar a impureza, e o `← Meus eventos` do detalhe subiu de 10px para 14px a pedido do Igor, que viu a tela. Os três READMEs atualizados, com as quatro decisões da story e suas alternativas descartadas no da raiz |
| 2026-08-11 | Story 2.6 criada e contextualizada. Quatro decisões do Igor incorporadas: a story é **só leitura** — "gerenciar" é acompanhar, e nem a escala nem os dados do evento mudam depois de publicados, porque editar custaria rota de escrita, invariante nova e uma dúzia de testes numa story dimensionada como um commit; a tela é **lista enxuta + página de detalhe**, e não uma lista única com os setores embutidos, que transformaria a fila de jornal num paredão de números onde não se acha o show de sexta; a lista se parte em **"Em cartaz" e "Já aconteceram"**, em vez de uma ordem só (um show de 2024 no meio da operação de hoje) ou de filtrar os passados no backend (o organizador perderia o histórico e o evento sumiria sem explicação); e **`Meus eventos` entra no masthead** com a confirmação de publicação ganhando `Ver meus eventos →`, em vez de um `redirect` que apagaria o único momento em que o organizador vê quem ficou com a porta. Vinte ACs escritos sobre os dois blocos do `epics.md`, entre eles o AC9 — a extração de `dataPorExtenso`, `momentoDaPublicacao` e `centavosParaReais` para `src/lib/formato.ts`, que não é faxina: um Server Component não consegue chamar função exportada de um módulo `"use client"`, e as telas novas são Server Components. Oito suposições declaradas (a rota `/organizador/eventos`, o código `EVENTO_NAO_ENCONTRADO` com `404` único para "não existe" e "não é seu", o service devolvendo `EventoResumo` em vez de ORM, a lista sem `imagem_url`, um `page.module.css` para as duas telas, o corte por data na tela e não na API, `momentoDaPublicacao` indo junto na extração, e nenhuma paginação) e quatro perguntas registradas para as epics seguintes |
