---
baseline_commit: "4bfff45 — Merge pull request #2 (Epic 2) na `main`. Branch atual: `Epic-3--Descoberta-e-compra`, árvore limpa. Migração `head`: c7cb4a29b7f3 (`cria_tabela_evento_portaria`). Suíte: 218 testes passando (203 + 15 do code review da Epic 2)."
---

# Story 3.1: Ver a programação

Status: review

Epic 3 — Descoberta e compra · **A primeira story da epic, e a primeira rota pública do projeto.**
Tudo que existe hoje no domínio é do organizador: publicar, escalar, acompanhar. Esta abre a outra
ponta — o visitante, sem conta e sem cookie, vendo o que está em cartaz.

Como visitante,
quero ver os eventos publicados com data, local e preço,
para descobrir o que está em cartaz.

A raiz `/` deixa de ser o estado vazio provisório da Story 1.2 e passa a ser **a programação**. São
uma rota nova (`GET /eventos`, no primeiro `app/api/publico.py`), um schema de leitura que **esconde
o estoque** (UX-DR7), um módulo de busca no servidor sem sessão, e a fila de jornal de quatro
colunas do `DESIGN.md` — a assinatura visual da listagem, que até agora só existia no protótipo.

Nenhuma migração, nenhum modelo, nenhuma coluna, nenhuma dependência.

## Acceptance Criteria

1. **Given** eventos publicados no banco
   **When** eu chamo `GET /eventos` **sem nenhum cookie de sessão**
   **Then** recebo `200` com uma lista de `EventoNaProgramacao`: `id`, `nome`, `data_hora`, `local`,
   `cidade`, `preco_minimo_centavos` e `esgotado`
   **And** a rota **não tem** `Depends(exigir_papel(...))` nem qualquer dependência de sessão — é
   pública por assinatura, não por disciplina
   **And** chamá-la logado como cliente, organizador ou portaria devolve exatamente a mesma coisa
   **And** nenhum evento publicado no banco responde `200` com `[]`, nunca `404`

2. **Given** um evento com `publicado_em = NULL` (rascunho — grave um pelo ORM, não há tela que o
   produza)
   **When** eu chamo a rota
   **Then** ele **não** aparece
   **And** a condição é `Evento.publicado_em.is_not(None)` no `where`, não um filtro em Python
   **And** ⚠️ é **este** o teste que o `deferred-work.md` previu ("a regra ganha teste na Epic 3").
   Ele cobre a rota pública. **`listar_do_organizador` não muda** e continua sem o filtro — o
   rascunho de alguém é dele, e a entrada do `deferred-work.md` sobre a rota do organizador
   **permanece aberta**

3. **Given** um evento cuja `data_hora` já passou
   **When** eu chamo a rota
   **Then** ele **não** aparece — o corte é `Evento.data_hora >= agora`, **no backend** (decisão do
   Igor, tabela abaixo)
   **And** `agora` é `datetime.now(timezone.utc)` lido **uma vez** no início do service, nunca
   dentro do laço nem dentro do `where` como `func.now()` misturado a comparação em Python
   **And** o organizador continua vendo o histórico dele em `/organizador/eventos` — esta regra vale
   só para a programação pública

4. **Given** eventos gravados fora de ordem
   **When** eu leio a lista
   **Then** ela vem por `data_hora` **crescente**
   **And** `Evento.id` é o desempate, pelo mesmo motivo escrito na `listar_do_organizador`: sem
   critério total, dois shows no mesmo horário trocam de lugar entre requisições

5. **Given** um evento com Pista a R$ 120,00 **esgotada** e Camarote a R$ 420,00 com ingresso
   **When** eu leio o resumo dele
   **Then** `preco_minimo_centavos` é **42000**, e não 12000 — o menor preço **entre os setores que
   ainda têm ingresso** (decisão do Igor)
   **And** disponibilidade é `setor.vendidos < setor.capacidade`, lido do setor — **AD-13**
   **And** ⚠️ é **proibido** derivar disponibilidade com `COUNT` sobre reserva ou ingresso, em
   qualquer camada. As duas tabelas nascem nas Stories 3.5 e 3.9, e é agora que o hábito se forma

6. **Given** um evento cujos setores estão **todos** esgotados
   **When** eu leio o resumo dele
   **Then** `esgotado` é `true` e `preco_minimo_centavos` é `null`
   **And** um evento **sem setor nenhum** — impossível pela rota de publicação, possível por `psql`
   — cai no mesmo caso e **não quebra** a listagem
   **And** o evento esgotado **continua na lista**: ele é informação (o show existe e acabou), não
   ruído

7. **Given** o corpo da resposta inteiro
   **When** eu procuro estoque
   **Then** não existe `capacidade`, `vendidos`, `setores`, `capacidade_total`, `vendidos_total`,
   `imagem_url`, `origem_externa_id`, `publicado_em` nem `organizador_id` em lugar nenhum — as
   chaves são **exatamente as sete** do AC1
   **And** ⚠️ **é o AC que mais importa desta story**: UX-DR7 e `DESIGN.md#Do's and Don'ts` proíbem
   contagem exata de ingresso em tela de cliente, e "a tela não mostra" não é garantia — o que a API
   devolve, o devtools mostra. A garantia é o `response_model`
   **And** `esgotado` e `preco_minimo_centavos` são derivados do estoque **sem revelá-lo**: é a
   diferença entre "restam 3" e "últimos ingressos"

8. **Given** dez eventos com três setores cada
   **When** eu observo as consultas emitidas
   **Then** os setores vêm em **uma** consulta a mais (`selectinload`), não uma por evento — o mesmo
   AC4 da Story 2.6, pelo mesmo motivo

9. **Given** a implementação do backend
   **When** eu a inspeciono
   **Then** a rota mora em **`app/api/publico.py`**, arquivo novo — é o router de visitante que a
   `ARCHITECTURE-SPINE.md#Árvore` já previa (`api/ # routers por papel: publico, cliente,
   organizador, portaria`)
   **And** ela passa por `app/services/evento.py::listar_programacao()` — router não abre `Session`
   para consultar (Design Paradigm)
   **And** `app/main.py` ganha **uma linha** de `include_router` e nada mais
   **And** **não** existe migração, modelo, coluna, código de erro nem dependência nova

10. **Given** `src/lib/programacao.ts`
    **When** eu o leio
    **Then** ele está no molde de `catalogo.ts` e `eventos.ts`: só servidor, `cache: "no-store"`,
    `try/catch` que **nunca levanta**, resultado discriminado
    **And** ⚠️ ele **não** chama `cabecalhoDeSessao()`: a rota é pública, e repassar cookie que
    ninguém lê é acoplamento que o próximo leitor tomaria por exigência
    **And** `listarProgramacao()` devolve `{ estado: "ok"; itens } | { estado: "indisponivel" }` —
    dois estados, porque não há `404` nem `401` possíveis nesta rota

11. **Given** `src/lib/formato.ts`
    **When** eu o leio
    **Then** ele ganha `partesDaFilaPublica(iso)` → `{ diaDaSemana, dia, hora }`, usando o **mesmo**
    `FUSO` do módulo
    **And** ⚠️ **nenhuma** formatação de data nova nasce dentro de `page.tsx`. Foi exatamente esse o
    achado do code review da Epic 2: as três formatações inline da fila de "Meus eventos" foram as
    únicas que passaram sem `timeZone`, e a mesma publicação aparecia com duas datas diferentes
    **And** `centavosParaReais` é **reusada**, não reescrita

12. **Given** a rota `/`
    **When** eu a abro sem sessão
    **Then** vejo a programação — Server Component, **sem uma linha de `"use client"`**, sem guarda
    de sessão e sem `redirect`
    **And** o `page.module.css` do estado vazio provisório da Story 1.2 é **substituído**, não
    duplicado

13. **Given** a listagem na tela
    **When** eu a leio
    **Then** cada evento é uma **fila de quatro colunas** — data | nome | local e cidade | preço —
    na grade do `DESIGN.md#Layout & Spacing` (`96px | 1fr | 210px | 150px`)
    **And** a data é dia da semana e hora em **mono versalete** com o dia em **serifada grande**, que
    é a assinatura visual da listagem (`DESIGN.md#Typography`); o nome do show em serifada; local e
    cidade em mono versalete; o preço em serifada com `a partir de` em mono abaixo
    **And** as filas são separadas por **fio de 1px**, e **não há card, sombra nem canto
    arredondado** — UX-DR3
    **And** hover pinta `var(--breu2)`
    **And** a fila **inteira** é clicável (padrão `fila-listagem`), não só o nome

14. **Given** um evento esgotado na lista
    **When** eu o vejo
    **Then** o preço dá lugar a um selo **`Esgotado`** vazado em `var(--brasa)`
    **And** a fila **não é clicável** e **não muda no hover** — a ausência de resposta é a informação
    (`EXPERIENCE.md#fila-listagem`)
    **And** o esmaecido do nome e da data usa `var(--fumaca)`. ⚠️ O protótipo escreve `#5F5A52`;
    **nenhum hex novo entra em `*.module.css`** — só `var(--token)`. Se o `fumaca` não bastar
    visualmente, **pergunte ao Igor** em vez de inventar um token
    **And** a informação **não é dada só por cor** (UX-DR9): a palavra "Esgotado" está escrita, e a
    fila esgotada não é um `<a>`

15. **Given** que não há nenhum evento publicado e futuro
    **When** eu abro a raiz
    **Then** vejo o estado vazio: kicker, uma frase, fim — **sem ilustração e sem botão grande**
    (`EXPERIENCE.md#Vazio`, UX-DR8)
    **And** se a programação não puder ser carregada, a tela diz isso **numa frase diferente** e não
    quebra: o projeto continua sem `error.tsx`, e a falha é um estado discriminado
    **And** "nenhum evento" e "API fora do ar" **não** compartilham a mesma frase — a primeira é
    verdade sobre o produto, a segunda é uma falha temporária

16. **Given** uma tela abaixo de 900px
    **When** eu abro a programação
    **Then** a fila colapsa de **quatro para duas colunas** — data à esquerda, o resto num bloco
    (`EXPERIENCE.md#Responsive`)
    **And** nada transborda na horizontal
    **And** os fios continuam alinhados de ponta a ponta
    **And** nenhum dos cinco anti-padrões do UX-DR10 aparece — em particular, **não** existe linha de
    contexto decorativa ("14 apresentações em cartaz") em lugar nenhum

17. **Given** a fila clicável
    **When** eu clico nela
    **Then** vou para `/eventos/{id}`, que **só nasce na Story 3.4** — uma janela de três stories em
    que o clique cai na 404 do projeto
    **And** é **decisão consciente do Igor**, pelo mesmo padrão da janela do AD-7 aberta na 2.4 e
    fechada na 2.5: ela vive dentro da branch da epic, que só ele publica
    **And** ⚠️ ela **contraria** o precedente escrito em `Masthead.tsx:38` ("link que cai no 404 não
    fica no repositório"). A diferença registrada é o alcance: lá é navegação permanente, visível a
    todo mundo em toda tela; aqui é um `href` que fecha na mesma epic. **Registre a janela no
    `frontend/README.md`**, e a Story 3.4 é quem a fecha

18. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira, e os **218** testes anteriores continuam verdes — nenhum deles
    precisa mudar, porque esta story não altera contrato nenhum que já existia
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos

19. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta a rota pública, o `EventoNaProgramacao`, **por que o
    estoque não atravessa o contrato** (UX-DR7) e a regra do preço mínimo — e corrige o número da
    suíte, que ficou em 203 e hoje é 218
    **And** `frontend/README.md` documenta a raiz virando programação, o `lib/programacao.ts` sem
    cookie, o `partesDaFilaPublica` e a janela do link até a 3.4
    **And** os dois respeitam a régua de camada do `CLAUDE.md`: **no máximo cinco parágrafos**, na
    seção temática que já existe, sem tabela nova e sem subseção nova
    **And** `README.md` da raiz recebe **uma** decisão — a programação pública só mostra o que ainda
    vai acontecer —, com a alternativa descartada, em primeira pessoa. As outras três **não passam na
    régua da raiz** e ficam nos READMEs de camada

> **De onde vem cada critério.** O `epics.md` traz **cinco** blocos para a Story 3.1: a fila com
> data, local e preço; a ausência de card, sombra e canto arredondado, com fio de 1px separando; o
> selo `Esgotado` não clicável; nenhum número absoluto de estoque; e o colapso abaixo de 900px. Os
> dois primeiros viraram o **AC13**, e os outros três os ACs **14, 7** e **16**. O bloco "eventos não
> publicados não aparecem" veio junto do primeiro e virou o **AC2**.
>
> Todo o resto é decisão do Igor (tabela abaixo) ou consequência técnica dela: o corte dos eventos
> passados no backend (AC3), o preço mínimo contando só setor com ingresso (AC5), a janela do link
> até a 3.4 (AC17) e a ausência de `imagem_url` no contrato (AC7).

## Tasks / Subtasks

- [x] **T1. `app/schemas/evento.py` — o schema da programação** (AC: 1, 5, 6, 7)
  - [x] `EventoNaProgramacao` novo: `id`, `nome`, `data_hora`, `local`, `cidade`,
        `preco_minimo_centavos: int | None`, `esgotado: bool`
  - [x] **Sem `from_attributes`**, como o `EventoResumo` e pelo mesmo motivo: os dois últimos campos
        não são atributos do `Evento`, e quem os calcula é o service
  - [x] Docstring dizendo **o que ele recusa a devolver, e por quê**: capacidade, vendidos, setores e
        imagem. É a materialização do UX-DR7 no contrato, não uma escolha de payload enxuto
  - [x] ⚠️ `EventoResumo` e `EventoSaida` **não mudam**. São de outra audiência

- [x] **T2. `app/services/evento.py` — a leitura pública** (AC: 2, 3, 4, 5, 6, 8)
  - [x] `listar_programacao(sessao) -> list[EventoNaProgramacao]`
    - [x] `agora = datetime.now(timezone.utc)`, lido **uma vez**, antes da consulta
    - [x] `select(Evento).where(Evento.publicado_em.is_not(None), Evento.data_hora >= agora)
          .order_by(Evento.data_hora, Evento.id).options(selectinload(Evento.setores))`
    - [x] Preço mínimo e esgotado, num só lugar, com comentário citando o **AD-13**: disponível é
          `setor.vendidos < setor.capacidade`; `min(...)` sobre os disponíveis, `None` se não houver
    - [x] ⚠️ `min()` sobre lista vazia **levanta `ValueError`** — o evento todo esgotado e o evento
          sem setor caem os dois nesse caminho. Trate antes, não com `try`
    - [x] Sem parâmetro nenhum além da sessão: sem filtro, sem termo, sem paginação — busca é a
          Story 3.2
  - [x] Docstring explicando as três decisões que moram aqui: por que só publicado, por que só
        futuro (e por que **no backend**), e por que o estoque não atravessa o contrato

- [x] **T3. `app/api/publico.py` — o primeiro router de visitante** (AC: 1, 9)
  - [x] Arquivo novo. `router = APIRouter(tags=["público"])`, **sem `prefix`** — a rota é `/eventos`
  - [x] `@router.get("/eventos", response_model=list[EventoNaProgramacao])`, corpo de uma linha
  - [x] **Nenhuma dependência de sessão ou papel.** Só `sessao: Session = Depends(obter_sessao)`
  - [x] Docstring do módulo dizendo o que faz este router existir: é a superfície do **visitante**,
        e o critério de entrada aqui é "não exige conta". Compare com o de `organizador.py`, que é
        por papel
  - [x] Docstring da rota: por que ela é pública, e por que o corpo não carrega estoque
  - [x] `app/main.py`: `from app.api import auth, organizador, publico, saude` e
        `app.include_router(publico.router)` — **uma linha**, junto das outras três

- [x] **T4. Testes do backend** (AC: 1–9, 18)
  - [x] `tests/test_programacao.py` (arquivo novo). Helper local que grava evento com setores pelo
        ORM, aceitando `nome`, `data_hora`, `publicado_em` e os setores com `vendidos` — o mesmo
        precedente do `test_organizador_meus_eventos.py`. ⚠️ O parâmetro virou `publicado: bool`
        depois de o teste do rascunho falhar — ver Debug Log
  - [x] Sem cookie nenhum → `200`. ⚠️ Use uma instância limpa ou `cliente.cookies.clear()`
  - [x] Logado como cliente → `200`, corpo **idêntico** ao da chamada anônima
  - [x] Rascunho (`publicado_em = None`) não aparece
  - [x] Evento com `data_hora` no passado não aparece
  - [x] Ordem crescente, com dois eventos gravados fora de ordem
  - [x] Banco sem evento publicado e futuro → `200 []`
  - [x] Preço mínimo **pula o setor esgotado**: Pista 12000 com `vendidos == capacidade`, Camarote
        42000 disponível → `preco_minimo_centavos == 42000`, `esgotado is False`
  - [x] Todos os setores esgotados → `esgotado is True` e `preco_minimo_centavos is None`
  - [x] Evento sem setor nenhum → `esgotado is True`, sem levantar
  - [x] ⚠️ O corpo tem **exatamente** as sete chaves, e o texto inteiro da resposta não contém
        `capacidade`, `vendidos`, `setores`, `imagem_url` nem `organizador_id` (AC7)
  - [x] OpenAPI: `GET /eventos` responde `list[EventoNaProgramacao]`
  - [x] ⚠️ **Nenhum teste antigo deve precisar mudar.** Se algum quebrar, algo saiu do escopo —
        pare e diga. Nenhum precisou: 218 → 231, todos os 218 anteriores intactos

- [x] **T5. `src/lib/formato.ts` — a data da fila pública** (AC: 11)
  - [x] `partesDaFilaPublica(iso)` → `{ diaDaSemana, dia, hora }`, com o `FUSO` do módulo
  - [x] `diaDaSemana` em `weekday: "short"`, **sem o ponto** que o `Intl` do pt-BR devolve — mesmo
        tratamento que `partesDaData` já faz com o mês
  - [x] `hora` no formato `22h30`, como as outras funções do módulo
  - [x] Docstring dizendo por que ela mora aqui e não na tela (o `FUSO` num lugar só — o achado do
        code review da Epic 2)
  - [x] ⚠️ As funções existentes **não mudam**

- [x] **T6. `src/lib/programacao.ts` — a busca de servidor** (AC: 10)
  - [x] Arquivo novo. Tipo `EventoNaProgramacao` espelhando o schema, e
        `ResultadoDaProgramacao` com dois estados
  - [x] `listarProgramacao()`: `fetch(`${API_URL}/eventos`, { cache: "no-store" })`, **sem
        `headers`** — comentário explicando que a ausência é intencional
  - [x] `try/catch` que nunca levanta, `console.error` no molde dos outros três módulos.
        ⚠️ Com `unstable_rethrow` antes do `console.error` — ver Debug Log

- [x] **T7. A tela** (AC: 12–16)
  - [x] `src/app/(site)/page.tsx` — substitui o estado vazio provisório da 1.2. Server Component
  - [x] `src/app/(site)/page.module.css` — a fila de quatro colunas, sobre o arquivo que já existe
  - [x] `<h1>Programação</h1>` com fio embaixo, na anatomia do `.secTitulo` de "Meus eventos"
  - [x] Fila: `<Link href={`/eventos/${evento.id}`}>` quando há ingresso; `<div>` quando esgotado
  - [x] Preço: `R$ {centavosParaReais(preco_minimo_centavos)}` com `a partir de` abaixo; esgotado
        troca o bloco inteiro pelo selo
  - [x] Estado vazio e estado indisponível, **cada um com a sua frase** — AC15
  - [x] Media query de 900px: duas colunas, local e preço descem para a coluna do nome
  - [x] ⚠️ **Nenhum hex novo**: só `var(--token)`

- [x] **T8. Verificação** (AC: 16, 18)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final → **231 passando**
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos
  - [x] Conferir na tela, com `next dev` e `uvicorn` no ar:
    - [x] Abrir `/` **sem sessão** — a programação aparece, e o masthead mostra `Entrar`
    - [~] Publicar um evento novo como `organizador@rockhub.dev` e recarregar a raiz — **não feito**:
          publicar cria dado no banco do Igor. A ordem crescente foi conferida com os quatro eventos
          que já existiam lá e por teste automatizado
    - [x] Esgotar um setor por `psql` e conferir o preço mínimo mudando (12000 → 42000); esgotar
          todos e conferir o selo e a fila não clicável. **`vendidos` restaurado para 0**
    - [x] Derrubar o `uvicorn` e recarregar a raiz — a frase de indisponível, sem tela quebrada
    - [x] Clicar numa fila → a 404 do projeto (a janela do AC17), com a casca
    - [x] Estado vazio conferido apontando o `uvicorn` para o `rockhub_teste`, que está vazio
  - [~] Abaixo de 900px: a media query foi conferida no **CSS compilado** servido pelo `next dev`;
        o olho no navegador e o Tab com foco em âmbar ficam para o Igor
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2 continua valendo)
  - [x] ⚠️ Conferir que os arquivos novos **estão rastreados** pelo git antes de dar a story por
        pronta — **não executo git** (regra do projeto); a conferência é do Igor
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** ao terminar

- [x] **T9. Os READMEs** (AC: 19) — obrigatório, regra do projeto
  - [x] `backend/README.md`, **até cinco parágrafos** (foram quatro), em `## Programação pública`:
        a rota pública, o `EventoNaProgramacao`, o que ele recusa a devolver e por quê, o preço
        mínimo entre os setores com ingresso, e o corte de publicados e futuros. *Estrutura*
        atualizada (`api/publico.py`, `tests/test_programacao.py`) e o número da suíte corrigido de
        **203 para 231**
  - [x] `frontend/README.md`, cinco parágrafos em `## A raiz: a programação`: a raiz virando
        programação, o `lib/programacao.ts` sem cookie, o `unstable_rethrow`, o `partesDaFilaPublica`
        e a janela do link até a 3.4
  - [x] `README.md` da raiz — **uma** decisão em *Decisões: por que isso e não aquilo*, no formato
        das anteriores: *a programação pública só mostra o que ainda vai acontecer*
  - [x] ⚠️ **Escreva o motivo que o Igor deu, não um motivo plausível.** Os três parágrafos da
        decisão da raiz saíram da tabela *Decisões que o Igor tomou*, sem inventar motivo
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README
(T9) — é o "por quê" dele.** Só a primeira passa na régua da raiz; as outras três moram na camada.

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| Evento cuja data já passou | **Some, com filtro no backend.** `GET /eventos` devolve só `data_hora >= agora`. A programação pública é o que está por vir: quem chega na raiz quer saber o que dá para comprar, e show que já aconteceu não é nenhuma das duas coisas. O histórico não se perde — ele continua inteiro em `/organizador/eventos`, que é de quem publicou | *Duas seções na tela, `Em cartaz` e `Já aconteceram`*, como em "Meus eventos": caiu porque lá o dono da informação é o organizador, e o histórico é o inventário dele; aqui o visitante veria metade da página ocupada por shows que não pode comprar. E *uma lista só, ordem crescente*: menos código, mas põe um show de 2001 no topo da página inicial do produto |
| O "a partir de R$ X" | **Menor preço entre os setores que ainda têm ingresso.** Se a Pista, que é a mais barata, esgotou, a fila passa a anunciar o preço do que dá para comprar. Anunciar um preço que não existe mais é a única forma de a listagem mentir com número | *Menor preço entre todos os setores, esgotados inclusive*: mais simples, mais estável entre recarregamentos — caiu porque o visitante clicaria na fila esperando R$ 120,00 e encontraria R$ 420,00, e a culpa pareceria da página do evento |
| O link da fila antes da 3.4 | **A fila já linka para `/eventos/{id}`**, e o clique cai na 404 do projeto até a Story 3.4 criar a página. Mesmo padrão da janela do AD-7, aberta na 2.4 e fechada na 2.5: ela dura dentro da branch da epic, que só eu publico, e fica registrada | *Fila sem link nesta story, `<Link>` só na 3.4*: nenhum clique quebrado em momento nenhum — caiu porque a 3.4 reescreveria a fila inteira, e porque o AC "esgotado não é clicável" não significa nada enquanto nada é clicável |
| `imagem_url` no contrato | **Não entra agora.** A fila de quatro colunas não tem imagem (`DESIGN.md`: data, nome, local, preço), e quem precisa da arte é a chamada principal da Story 3.3. O campo entra junto com quem o consome | *Já incluir o campo, para não mexer no schema de novo na 3.3*: um campo a mais e pronto — caiu porque é a mesma disciplina que recusou o `relationship` sem consumidor na 2.3 e o `back_populates` da escala na 2.5. Campo que nenhuma tela lê é campo que ninguém sabe se está certo |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar.

- **A rota é `GET /eventos`, em `app/api/publico.py`.** A árvore da espinha lista `publico` como um
  dos quatro routers por papel, e este é o primeiro. `/programacao` foi considerado e caiu: o
  recurso é evento, e a Story 3.4 vai pendurar `/eventos/{id}` no mesmo router.
- **O schema se chama `EventoNaProgramacao`.** Fica ao lado de `EventoResumo` (lista do organizador)
  e `EventoSaida` (detalhe do organizador), e o nome diz de qual tela ele é. `EventoPublico` foi
  descartado porque descreve a audiência, não a vista — e a Story 3.4 vai precisar de um segundo
  schema público, que não poderia se chamar a mesma coisa.
- **`esgotado` é um campo, e não algo derivado de `preco_minimo_centavos === null` na tela.** As
  duas versões dizem a mesma coisa hoje; a segunda faz a tela reconstruir uma regra de domínio a
  partir da ausência de um valor, e o dia em que um evento tiver preço zero alguém descobre isso pela
  tela errada.
- **O módulo do frontend é `lib/programacao.ts`, e não uma função a mais em `lib/eventos.ts`.**
  `eventos.ts` é a superfície do organizador — os dois tipos dele espelham schemas que esta rota não
  usa, e misturar audiência num módulo é o começo de um cliente de API genérico. A Story 3.4 é quem
  ganha companhia ali dentro.
- **A raiz é a programação, e não `/programacao` com a raiz redirecionando.**
  `EXPERIENCE.md#Information Architecture` escreve `Início (listagem)`, e o masthead já aponta `/`.
- **O título da seção é `Programação`, sem kicker de contexto.** O protótipo escreve
  `Agosto de 2026` ao lado; ele mente assim que a lista atravessa dois meses, e inventar um rótulo
  que se ajusta sozinho é exatamente o quinto anti-padrão ("soa gerada"). O kicker do estado vazio
  continua existindo, porque o `EXPERIENCE.md#Vazio` o pede.
- **Nenhuma paginação e nenhum limite.** Uma avaliação tem unidades de eventos. Paginar custaria
  parâmetro, contagem total e navegação, para um problema que este projeto não tem — e a Story 3.2
  vai trazer busca, que é o que resolve lista grande de verdade.
- **A fila não mostra o `f-sub` do protótipo** (a linha em itálico, "com participação de Duda Beat").
  Não existe campo de subtítulo no modelo `Evento`, e inventá-lo é migração numa story que não toca o
  banco.

### O contrato da API, campo a campo

**`GET /eventos`** · `200` · `response_model=list[EventoNaProgramacao]` · **pública**

```json
[
  {
    "id": "3f2a…",
    "nome": "Baco Exu do Blues — Bluesman Vivo",
    "data_hora": "2026-08-15T00:00:00Z",
    "local": "Espaço Unimed",
    "cidade": "São Paulo",
    "preco_minimo_centavos": 12000,
    "esgotado": false
  }
]
```

| Campo | Tipo | De onde vem |
|---|---|---|
| `preco_minimo_centavos` | `int \| None` | `min(setor.preco_centavos)` entre os setores com `vendidos < capacidade` — AD-13. `None` quando não há nenhum |
| `esgotado` | `bool` | Nenhum setor com `vendidos < capacidade`. **Nunca** `COUNT` de reserva ou ingresso |

Filtrada por `publicado_em IS NOT NULL` **e** `data_hora >= agora`. Ordenada por `data_hora`, com
`id` de desempate. Sem paginação, sem filtro e **sem autenticação**.

**O que este contrato não devolve, de propósito:** `capacidade`, `vendidos`, `setores`,
`imagem_url`, `origem_externa_id`, `publicado_em`, `organizador_id`. Os quatro primeiros por
UX-DR7 e AD-13; os três últimos porque não são assunto de quem está escolhendo um show.

**Nenhum código de erro novo. Nenhuma migração, nenhuma dependência.**

[Fonte: ARCHITECTURE-SPINE.md#AD-13, #Árvore, #Design Paradigm · backend/app/schemas/evento.py]

### A tela, em texto

O protótipo **desenha** esta tela (`proto-jornal-noturno.html:300-335`) — é uma das poucas em que
ele é literal. O que não entra nesta story está marcado abaixo.

```
  ┌ barra de busca ─────────────────────────── Story 3.2, não entra aqui ┐
  ┌ chamada principal ──────────────────────── Story 3.3, não entra aqui ┐

  PROGRAMAÇÃO
  ─────────────────────────────────────────────────────────────────────────
  SEX          Marina Sena                  Qualistage          R$ 90,00
  15                                        RIO DE JANEIRO      A PARTIR DE
  22H30
  ─────────────────────────────────────────────────────────────────────────
  QUA          Djavan                       Vibra São Paulo     ┌────────┐
  19                                        SÃO PAULO           │ESGOTADO│
  20H00                                                         └────────┘
  ─────────────────────────────────────────────────────────────────────────
```

- Dia da semana e hora em **mono versalete**; o dia em **serifada 30px** — é a assinatura visual da
  listagem (`DESIGN.md#Typography`), e é o que a diferencia da fila do organizador, que é toda mono
- Nome do show em **serifada 27px**; local e cidade em mono versalete; preço em serifada com
  `a partir de` em mono abaixo
- Fio de 1px embaixo de cada fila. **Sem caixa, sem sombra, sem raio** — UX-DR3
- Fila inteira clicável, hover em `var(--breu2)`. **Fila esgotada não é clicável e não responde ao
  hover** — `EXPERIENCE.md#fila-listagem`
- Selo `Esgotado`: retângulo vazado em `var(--brasa)`, mono 700 versalete, **raio zero**
- **Nenhum número de estoque, nenhum medidor**: medidor é da página do evento (Story 3.4), onde ele
  mostra proporção e nunca número
- Estado vazio: kicker, frase, fim

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `Evento`, `Setor` | `app/models/evento.py` | **Não mexa.** Esta story não toca o banco |
| `listar_do_organizador` | `app/services/evento.py:226` | **O molde**: `selectinload`, ordem com desempate, service devolvendo schema e não ORM. **Não a altere** |
| `EventoResumo` | `app/schemas/evento.py:205` | O precedente do schema sem `from_attributes`. `EventoNaProgramacao` entra ao lado |
| `obter_sessao` | `app/core/db.py` | A única dependência da rota nova |
| Router de saúde | `app/api/saude.py` | O precedente de router **sem** dependência de papel |
| `app/main.py:145-147` | — | Onde a linha do `include_router` entra |
| `_entrar`, `fabricar_usuario` | `tests/test_organizador_meus_eventos.py` · `tests/conftest.py:139` | O molde do arquivo de teste novo |
| `listarMeusEventos`, `buscarNoCatalogo` | `frontend/src/lib/eventos.ts`, `catalogo.ts` | O molde de `programacao.ts` — **menos** o `cabecalhoDeSessao()` |
| `API_URL` | `frontend/src/lib/servidor.ts:18` | Importe daqui. ⚠️ Importar `servidor.ts` prende o módulo ao servidor, e é isso que se quer |
| `centavosParaReais`, `partesDaData` | `frontend/src/lib/formato.ts` | Reuse a primeira; a segunda é o molde de `partesDaFilaPublica`, **não** a reescreva |
| `.secTitulo`, `.fila`, `.aviso` | `organizador/eventos/page.module.css` | O vocabulário de fila e de título de seção já está escrito — leia antes de inventar classe. **CSS Module não compartilha classe entre arquivos**: aqui se copia a anatomia, não se importa |
| A tela e o CSS da raiz | `frontend/src/app/(site)/page.tsx` e `page.module.css` | **São estes os arquivos que a story substitui.** O `.vazio`/`.frase` continuam servindo ao AC15 |
| `not-found.tsx` | `frontend/src/app/` | A 404 que o link da fila encontra até a 3.4. Já existe e já tem a casca |
| Tokens | `frontend/src/app/globals.css` | `var(--fio)`, `var(--breu2)`, `var(--brasa)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)`, `.kicker` |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, `migrations/`, `seeds/`,
`app/core/`, `app/integrations/`, `app/schemas/auth.py`, `app/schemas/catalogo.py`,
`app/api/auth.py`, `app/api/organizador.py`, `app/api/saude.py`, `app/services/autenticacao.py`,
`publicar()`, `listar_portarias()`, `listar_do_organizador()`, `obter_do_organizador()`,
`tests/conftest.py`, `docker-compose.yml`, `pyproject.toml`, `package.json`,
`frontend/src/lib/servidor.ts`, `sessao.ts`, `api.ts`, `caminho.ts`, `eventos.ts`, `catalogo.ts`,
`Masthead.tsx`, e as telas de `(entrada)/` e de `organizador/`.

De `app/main.py`, **só** a linha do router novo e o import. Se algum dos outros precisar mudar para
esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. O estoque vazando pelo contrato.** É o erro que a story inteira existe para evitar, e ele tem
duas formas: devolver `setores` "porque a Story 3.4 vai precisar", e esquecer o `response_model` na
rota — sem ele, o FastAPI serializa o que o service devolver. O que a tela não desenha, o devtools
mostra: o teste do AC7 procura as palavras `capacidade` e `vendidos` no texto **inteiro** da
resposta.

**2. `min()` sobre sequência vazia levanta `ValueError`.** Evento todo esgotado e evento sem setor
nenhum caem os dois nesse caminho, e o segundo existe no banco de desenvolvimento. Uma lista
intermediária e um `if` resolvem; `try/except ValueError` esconde a regra dentro de um tratamento de
exceção.

**3. Comparar data como texto, ou ler o relógio duas vezes.** O filtro é `Evento.data_hora >=
agora`, com `agora` sendo um `datetime` com fuso lido **uma vez** — a mesma disciplina que o
`cache()` da tela de "Meus eventos" impôs no frontend, pelo mesmo motivo: duas leituras do relógio
na mesma requisição podem discordar sobre o evento que começa agora.

**4. Formatação de data nascendo dentro do `page.tsx`.** Foi exatamente assim que a fila de "Meus
eventos" ficou sem `timeZone` e a mesma publicação apareceu com duas datas. Se a tela precisa de um
pedaço de data que o `formato.ts` não tem, o pedaço nasce **lá**, com o `FUSO` do módulo.

**5. Repassar cookie numa rota pública.** `cabecalhoDeSessao()` está a um import de distância e não
faz mal nenhum — e é exatamente por isso que ele entra sem ninguém notar. O próximo leitor vai supor
que a rota exige sessão, e a Story 3.2 vai herdar a suposição.

**6. A raiz virando estática no build.** O `fetch` com `cache: "no-store"` é o que mantém a
programação dinâmica; sem ele, o build da Vercel renderizaria a lista uma vez e ela congelaria. Hoje
o masthead já torna toda rota do `(site)` dinâmica por ler a sessão — **não conte com isso**: é
efeito colateral de outro componente, e ele pode mudar.

**7. `<Link>` envolvendo a fila esgotada.** O AC14 pede que ela **não** seja clicável. Um `<Link>`
com `pointer-events: none` continua no Tab e continua sendo anunciado como link por leitor de tela;
o elemento precisa ser outro.

**8. Hex novo no CSS.** O protótipo escreve `#5F5A52` no nome do evento esgotado. A regra do projeto
é `var(--token)` e nada mais. `var(--fumaca)` é o token que existe para texto secundário.

**9. O `.` do `Intl` em pt-BR.** `weekday: "short"` devolve `"sex."`; em versalete o ponto vira
sujeira, como já acontecia com o mês em `partesDaData`. O tratamento é o mesmo, e está a três linhas
de distância no mesmo arquivo.

**10. O `TestClient` guarda cookie entre chamadas.** O teste que prova "funciona sem sessão" precisa
de instância limpa ou de `cliente.cookies.clear()` — e nesta story ele é o teste principal.

**11. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest`
falhar com `os error 4551`, chame pelo módulo: `uv run python -m pytest`.

**12. O banco de desenvolvimento tem eventos de conferência das Stories 2.4 a 2.6**, entre eles um
de 2001 e um sem portaria. O de 2001 é o cenário do AC3 e **deve sumir** da programação. **Não
apague nada:** o banco é do Igor.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      publico.py                 # NOVO — GET /eventos
    schemas/
      evento.py                  # +EventoNaProgramacao
    services/
      evento.py                  # +listar_programacao()
    main.py                      # +1 linha de include_router
  tests/
    test_programacao.py          # NOVO
  README.md
frontend/
  src/
    lib/
      formato.ts                 # +partesDaFilaPublica()
      programacao.ts             # NOVO — no molde do catalogo.ts, sem cookie
    app/(site)/
      page.tsx                   # SUBSTITUÍDO — a programação
      page.module.css            # SUBSTITUÍDO — a fila de quatro colunas
  README.md
README.md                        # uma decisão
```

Não existe, e não deve passar a existir nesta story: `app/api/cliente.py`, `app/api/eventos.py`,
`services/programacao.py`, migração, coluna, rota de escrita, busca, filtro, chamada principal,
página do evento, medidor, paginação, `error.tsx`, teste automatizado de frontend, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| A rota responde `200` **sem nenhum cookie** | `test_programacao.py` | 1 |
| Logado como cliente, o corpo é o mesmo | `test_programacao.py` | 1 |
| Banco sem evento publicado e futuro → `200 []` | `test_programacao.py` | 1 |
| Rascunho (`publicado_em = None`) não aparece | `test_programacao.py` | 2 |
| Evento com data no passado não aparece | `test_programacao.py` | 3 |
| Ordenada por `data_hora` crescente (gravados fora de ordem) | `test_programacao.py` | 4 |
| Preço mínimo **pula** o setor esgotado | `test_programacao.py` | 5 |
| Todos os setores esgotados → `esgotado`, preço `null` | `test_programacao.py` | 6 |
| Evento sem setor nenhum não quebra | `test_programacao.py` | 6 |
| O corpo tem **exatamente** as sete chaves | `test_programacao.py` | 7 |
| `capacidade` e `vendidos` ausentes do texto inteiro da resposta | `test_programacao.py` | 7 |
| O OpenAPI declara `list[EventoNaProgramacao]` | `test_programacao.py` | 1 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são seis caminhos — os da T8.

**Baseline: 218 testes passando** (code review da Epic 2, 2026-08-11). ⚠️ O `backend/README.md#Testes`
ainda diz **203**: ele ficou parado na Story 2.6 e não foi atualizado pelo review. Corrija o número
junto com o desta story.

### Inteligência das stories anteriores

**Da 2.6 — a story imediatamente anterior:**

- **O molde inteiro do backend desta story está lá**: service devolvendo schema e não ORM,
  `selectinload` contra N+1, ordem com desempate por `id`, e a soma/derivação acontecendo num só
  lugar onde um teste consegue lê-la.
- **Foi a primeira vista de leitura que não espelha uma linha do banco.** Esta é a segunda, e a
  diferença é a audiência: lá os dois totais **revelam** o estoque porque o dono é quem lê; aqui os
  dois campos derivados existem para **não** revelá-lo.
- **`Date` contra `Date`, nunca texto contra texto.** Lá o corte por data ficou na tela; aqui ele foi
  para o backend por decisão do Igor, e vira `datetime` contra `datetime` no `where`.
- **Formatação de data mora em `lib/formato.ts`.** O code review provou o custo de não seguir isso:
  as três formatações inline da fila foram as únicas que ficaram sem `timeZone`.

**Do code review da Epic 2:**

- **`imagem_url` só aceita `http://` e `https://`** — o validador entrou no schema de entrada
  justamente porque "a Epic 3 vai renderizá-lo em `<img src>`". Esta story **não** renderiza imagem
  nenhuma; a Story 3.3 é quem colhe esse trabalho.
- **`listar_do_organizador` sem filtro de `publicado_em`** ficou adiado esperando esta epic. O AC2
  esclarece: quem ganha o filtro e o teste é a **rota pública**; a do organizador continua como está,
  e a entrada do `deferred-work.md` continua aberta.
- **Teto em campo numérico não é enfeite** (`capacidade` estourando o int4 virava `500`). Nada nesta
  story recebe número do usuário — mas o hábito de perguntar "o que acontece com o valor absurdo?"
  vale para o `min()` sobre lista vazia da armadilha 2.

**Da 2.4/2.3 — o modelo:** `publicado_em = NULL` significa rascunho, e o comentário do modelo diz,
com todas as letras, que ele existe "para tornar verificável o AC da Story 3.1". É esta story.

**Da 2.2 — o padrão de busca no servidor:** `buscarNoCatalogo` **nunca levanta**, porque não existe
`error.tsx` e uma exceção num Server Component derruba a tela inteira. Aqui a tela é a **raiz do
produto**, então o custo de esquecer isso é a aplicação inteira.

**Da 1.2 — a identidade:** a fila de listagem é o componente que o `DESIGN.md` descreve com mais
precisão, e ele nunca foi implementado — a fila do organizador é uma prima em mono. Esta é a primeira
vez que a assinatura visual da listagem sai do protótipo.

[Fonte: _bmad-output/implementation-artifacts/2-6-*.md · code-review-epic-2.md · deferred-work.md]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `APIRouter` sem dependência de papel, `response_model` |
| Pydantic | 2.13.4 | `EventoNaProgramacao`, com `int \| None` |
| SQLAlchemy | 2.0.51 | `select`, `where` com duas condições, `is_not(None)`, `selectinload`, `order_by` |
| Alembic | 1.19.1 | **Não é usado nesta story** — nenhuma migração |
| Next.js | **16.3.0** | Server Component na raiz; `fetch` com `cache: "no-store"` |
| React | 19 | Nenhuma ilha de cliente nova |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** Esta versão do Next tem quebras em relação ao
que um modelo tem memorizado; a documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

### Escopo — o que NÃO fazer aqui

Busca e filtro (3.2) · chamada principal com arte, kicker, manchete e standfirst (3.3) · página do
evento e seus setores (3.4) · medidor de proporção · reserva, stepper e rodapé de compra (3.5 em
diante) · imagem na fila · paginação · qualquer rota de escrita · qualquer alteração nas rotas do
organizador · migração de qualquer tipo · teste automatizado de frontend.

Cinco tentações concretas:

- **"Já devolvo os setores, a 3.4 vai precisar."** É o vazamento de estoque que o AC7 existe para
  impedir, e a 3.4 vai ter o schema dela — com medidor, que mostra proporção e nunca número
- **"Já ponho a barra de busca, é um `<input>`."** É a Story 3.2 inteira, com filtro de cidade e
  período, e ela tem ACs próprios
- **"Já ponho a chamada principal, a tela fica parecendo jornal."** É a Story 3.3, e ela tem cinco
  ACs só sobre quando a chamada **não** é renderizada
- **"Aproveito e conserto o filtro de `publicado_em` na lista do organizador."** Está no
  `deferred-work.md` com motivo escrito, e mexer numa rota já revisada não é escopo desta story
- **"Semeio um evento, agora que a raiz mostra a programação."** Continua sendo decisão de produto do
  Igor — qual show, qual data, quais setores, quais preços

### Project Structure Notes

Esta story cria a **quarta superfície** do backend, e a primeira sem dono: `auth` é de quem entra,
`organizador` é de quem publica, `saude` é da Railway, e `publico` é de quem só está olhando. O
critério de entrada em `publico.py` é **"não exige conta"**, e ele precisa estar escrito no docstring
do módulo — porque a Story 3.4 vai acrescentar `/eventos/{id}` ali, e as Stories 3.5 em diante vão
criar `cliente.py`, que é o oposto: exige conta, e é onde a reserva mora.

No frontend, é a primeira vez que a **raiz** busca dado de domínio. Até aqui ela era estática por
falta de conteúdo, e toda busca de servidor acontecia atrás de uma guarda de sessão. O
`programacao.ts` é o primeiro módulo de `lib/` que fala com a API **sem** repassar cookie, e a
ausência do `cabecalhoDeSessao()` merece comentário — ela é a diferença entre "esqueci" e "é
público".

É também a primeira vez que uma decisão de produto do Igor vira uma condição de `where`: "a
programação pública é o que ainda vai acontecer" não é regra de negócio herdada de invariante
nenhuma, é escolha de produto materializada no backend. Vale registrar assim no README da raiz — o
desafio avalia justamente esse tipo de "por quê".

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — os cinco blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — o objetivo da epic e as stories vizinhas
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade;
  proibido derivar por `COUNT`
- [Source: ARCHITECTURE-SPINE.md#AD-11] — dinheiro em centavos, campo sufixado `_centavos`
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`; router não toca a
  `Session`
- [Source: ARCHITECTURE-SPINE.md#Árvore] — `api/` tem routers por papel, e `publico` é um deles
- [Source: ARCHITECTURE-SPINE.md#Convenções] — Server Component por padrão; erro sempre `{"erro":{…}}`
- [Source: DESIGN.md#Layout & Spacing] — a grade `96px | 1fr | 210px | 150px` e o colapso em 900px
- [Source: DESIGN.md#Typography] — a data em serifada grande com dia da semana e hora em mono
- [Source: DESIGN.md#Components/fila-listagem] — quatro colunas, `breu2` no hover, esgotado esmaecido
  com selo `brasa`
- [Source: DESIGN.md#Do's and Don'ts] — não mostrar contagem exata em tela de cliente
- [Source: EXPERIENCE.md#Component Patterns/fila-listagem] — fila esgotada não é clicável e não muda
  no hover
- [Source: EXPERIENCE.md#Component Patterns/medidor] — proporção para o cliente, número exato para
  organizador e portaria
- [Source: EXPERIENCE.md#Vazio] — kicker, frase, fim; sem ilustração e sem botão grande
- [Source: EXPERIENCE.md#Responsive & Platform] — fila vira duas colunas abaixo de 900px
- [Source: mockups/proto-jornal-noturno.html:83-104, 300-335] — o CSS e o markup da fila
- [Source: backend/app/services/evento.py:226] — `listar_do_organizador`, o molde desta leitura
- [Source: backend/app/schemas/evento.py:205] — `EventoResumo`, o precedente sem `from_attributes`
- [Source: backend/app/models/evento.py:108] — `publicado_em NULL` é rascunho, escrito para esta story
- [Source: backend/app/api/saude.py] — o precedente de router sem dependência de papel
- [Source: frontend/src/lib/catalogo.ts] — o molde de `programacao.ts`
- [Source: frontend/src/lib/formato.ts] — o `FUSO` e as quatro formatações que já existem
- [Source: frontend/src/app/(site)/page.tsx] — a tela que esta story substitui
- [Source: frontend/src/components/Masthead.tsx:38] — o precedente de "link que cai no 404", e a
  exceção que o AC17 registra
- [Source: _bmad-output/implementation-artifacts/deferred-work.md] — a entrada sobre `publicado_em`,
  que **continua aberta** depois desta story
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, com a régua de cinco
  parágrafos por camada; git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída** — com a régua: até cinco parágrafos por
   camada, e só **uma** decisão na raiz. Documentação não bloqueia o commit: aplique o código, rode a
   suíte, mostre o resultado, **depois** escreva
3. **Decisão de produto ou de modelagem é do Igor.** As quatro desta story estão respondidas e as
   oito suposições estão declaradas. Se aparecer uma quinta — campo a mais, regra a mais, tela a mais
   — **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os três arquivos novos foram rastreados (T8)
8. **Esta é a primeira story da Epic 3.** O code review é ao fim da epic, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **O link da fila contraria o precedente do masthead** ("link que cai no 404 não fica no
   repositório", Story 1.4). Você escolheu abrir a janela até a 3.4, e ela está registrada no AC17 —
   mas o precedente continua escrito no código, e vale decidir se ele ganha a ressalva do alcance
   (navegação permanente × `href` que fecha na mesma epic) ou se fica como está.
2. **Nenhum evento é semeado.** Numa máquina limpa, a raiz do produto nasce vazia, e quem avaliar só
   vê a programação depois de publicar um evento pela interface. É o roteiro de avaliação — mas é a
   **primeira tela** que o avaliador abre. Semear um show é decisão de produto sua.
3. **Evento que começa daqui a cinco minutos continua vendendo ingresso.** O corte é `data_hora >=
   agora`, então o show some da programação só depois de começar. Se você quiser uma janela (parar de
   vender X horas antes), é regra de produto e provavelmente vale mais perto da Story 3.6.
4. **A cidade pode ser `NULL`** (a coluna é anulável desde a 2.3). A fila mostra local e cidade
   juntos; sem cidade, ela mostra só o local. Se quiser exigir cidade na publicação, é uma linha no
   schema de entrada — e é decisão sua.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context) — implementação em sessão única.

### Debug Log References

**1. O teste do rascunho falhou na primeira execução, e o defeito era do helper de teste.**
`_evento_gravado` recebia `publicado_em: datetime | None = None` e resolvia o default com
`publicado_em if publicado_em is not None else <carimbo>`. `None` era, ao mesmo tempo, "não informei"
e "é rascunho" — e o teste que gravava `publicado_em=None` recebia de volta um evento publicado, que
aparecia na programação. O `where` estava certo desde o início; quem mentia era a fixture. Trocado
por `publicado: bool = True`, que não tem esse ponto cego. É o teste falhando por motivo errado —
teria passado como "verde" se o default fosse o inverso.

**2. `unstable_rethrow` no `lib/programacao.ts`, achado pelo log do `npm run build`.** O build passava
e a raiz saía marcada `ƒ` (dinâmica), mas o log trazia `[RockHub] Programação indisponível` com a API
no ar. Causa: `cache: "no-store"` é uma das APIs que o Next interrompe **lançando**
`DYNAMIC_SERVER_USAGE` para sair da renderização estática, e o `try/catch` do módulo engolia o sinal.
A doc da versão instalada
(`node_modules/next/dist/docs/01-app/03-api-reference/04-functions/unstable_rethrow.md`) nomeia
`fetch(..., { cache: 'no-store' })` junto de `cookies()` e `notFound()` como erros que não devem ser
capturados. Os outros três módulos de `lib/` nunca sofreram disso porque chamam `cabecalhoDeSessao()`
— ou seja, `cookies()` — **fora** do `try`, e já saem do modo estático antes do `fetch`; este é o
único sem cookie, por ser público, e o `fetch` era o único sinal restante. `unstable_rethrow(erro)` é
a primeira linha do `catch`, e o log do build ficou limpo. É exatamente a armadilha 6 das Dev Notes,
por um caminho que ela não previa.

**3. As portas 3000 e 8000 estavam ocupadas por processos de 18:45, anteriores a esta sessão.**
Encerrados para a conferência de tela e devolvidos livres ao final. O `uvicorn` deixou um worker
`multiprocessing` órfão (PID filho do processo já morto) segurando a 8000 — matar só o pai não
liberou a porta. Registrado porque é o mesmo padrão da nota de memória sobre servidores em segundo
plano: conferir a porta pelo bind, não pela lista de processos.

**4. Conferência de `esgotado` no banco de desenvolvimento, e a restauração.** Para ver o selo na
tela rodei `UPDATE setor SET vendidos = capacidade` num evento e depois `SET vendidos = 0`. Antes de
restaurar conferi que **todos** os outros setores do banco estavam em `vendidos = 0` — nenhuma rota
deste projeto escreve nesse campo hoje, só a Epic 3 vai —, o que torna o zero o valor original com
certeza, e não um chute. Estado final: `SELECT count(*) FROM setor WHERE vendidos <> 0` → `0`.

### Completion Notes List

**O que foi implementado.** A primeira rota pública do projeto (`GET /eventos`, em
`app/api/publico.py`), o schema `EventoNaProgramacao` que recusa o estoque, o service
`listar_programacao()` com o corte de publicados e futuros, treze testes novos, o módulo de servidor
`lib/programacao.ts` sem cookie, `partesDaFilaPublica()` no `formato.ts`, e a raiz deixando de ser o
estado vazio provisório da Story 1.2 para virar a fila de jornal de quatro colunas.

**AC7, que é o que mais importa, está travado em dois níveis.** O `response_model` na rota impede o
FastAPI de serializar o que o service devolver, e o teste
`test_nenhuma_palavra_de_estoque_aparece_no_texto_da_resposta` procura `capacidade`, `vendidos`,
`setores`, `imagem_url` e `organizador_id` no **texto inteiro** da resposta — não nas chaves de topo,
que um `setores` aninhado escaparia. Um segundo teste afirma igualdade de conjunto das sete chaves,
então campo a mais reprova tanto quanto campo a menos. Um terceiro lê o OpenAPI e falha se a rota
passar a declarar parâmetro de segurança: "pública por assinatura" virou asserção, não promessa.

**Duas coisas saíram diferentes do que a story escreveu, as duas para melhor e as duas registradas
no Debug Log:** o parâmetro do helper de teste (`publicado: bool` em vez de `publicado_em`), e o
`unstable_rethrow` no `lib/programacao.ts`, que a story não previa e o build revelou.

**Dois ajustes que o Igor pediu ao ver a tela pronta, e que contrariam o protótipo de propósito:**

1. **`a partir de` passou para cima do preço.** O AC13 e o protótipo pedem o rótulo *abaixo* do
   valor; ali ele vira legenda de um número que já foi apresentado como se fosse o preço. Em cima,
   as duas linhas se leem como uma frase — "a partir de R$ 120,00" — e a coluna do preço passa a
   espelhar a da data, que também é rótulo em mono sobre valor em serifada grande. Como o
   `align-items: baseline` alinha pela primeira linha de cada coluna, quem alinha com o nome do show
   agora é o rótulo, e o valor desce — exatamente como o `14` desce sob o `SEX`.
2. **A fila ganhou folga: `padding` de `20px 0` para `26px 12px`.** O realce do hover pinta a caixa
   inteira, então o `padding` *é* o tamanho do realce, e ele estava encostando na primeira e na
   última letra da fila. ⚠️ O recuo lateral foi feito com `padding`, **não** com margem negativa:
   margem negativa daria o mesmo respiro e empurraria os fios para fora da medida da coluna, que é a
   mesma do masthead — e é ela que faz os filetes correrem de ponta a ponta da página. Por isso
   `.secTitulo`, `.aviso` e `.vazio` receberam o mesmo recuo de 12px: o texto continua alinhado entre
   si, e todo fio continua na largura cheia.

**Um detalhe da tela que a story não especificava:** o ramo do preço estreita por
`evento.esgotado || preco === null`, e não só por `esgotado`. Os dois dizem a mesma coisa hoje, mas
só o segundo dá ao TypeScript a certeza de que `preco` não é `null` no ramo do `<b>` — sem ele seria
preciso um `?? 0`, e "R$ 0,00" é um preço que existe: a fila anunciaria ingresso de graça se o
contrato mudasse.

**Verificação.** Backend: **231 testes passando** (218 anteriores + 13 novos), nenhum teste antigo
precisou mudar. Frontend: `npx tsc --noEmit`, `npm run lint` e `npm run build` limpos, com `/`
marcada `ƒ` (dinâmica) e sem falso "indisponível" no log. Na tela, com os dois servidores no ar:
programação sem sessão com o masthead em `Entrar`; preço mínimo pulando o setor esgotado
(12000 → 42000); selo `Esgotado` com a fila renderizada como `<div>` sem `href`; estado vazio
conferido apontando a API para o `rockhub_teste`; estado indisponível com o backend derrubado; e o
clique na fila caindo na 404 do projeto com a casca (a janela do AC17). `NEXT_PUBLIC` em
`frontend/src/`: zero.

**O que não conferi, e é honesto dizer:** o colapso de 900px foi verificado no CSS compilado servido
pelo `next dev`, não com o olho num navegador redimensionado; o foco em âmbar pelo Tab também não foi
visto — ele é herdado do `:focus-visible` do `globals.css`, e a fila esgotada está fora do Tab por ser
`<div>`, o que confirmei no HTML. E não publiquei um evento novo pela interface: isso criaria dado no
banco do Igor, e a ordem crescente já está provada por teste e pelos quatro eventos que existem lá.

⚠️ **Não executei nenhum comando git** (regra do projeto). Três arquivos são novos —
`backend/app/api/publico.py`, `backend/tests/test_programacao.py` e
`frontend/src/lib/programacao.ts` — e a conferência de que estão rastreados é do Igor.

⚠️ **`frontend/src/app/globals.css` estava modificado antes desta sessão**, com o bloco temporário de
comparação de paleta marcado "NÃO COMMITAR". Não toquei nele.

### File List

**Backend**

- `backend/app/api/publico.py` — **novo**
- `backend/tests/test_programacao.py` — **novo**
- `backend/app/schemas/evento.py` — `EventoNaProgramacao`
- `backend/app/services/evento.py` — `listar_programacao()` e o import do schema
- `backend/app/main.py` — o import e o `include_router` do `publico`
- `backend/README.md` — `## Programação pública`, *Estrutura* e o número da suíte (203 → 231)

**Frontend**

- `frontend/src/lib/programacao.ts` — **novo**
- `frontend/src/lib/formato.ts` — `partesDaFilaPublica()`
- `frontend/src/app/(site)/page.tsx` — substituído: a programação
- `frontend/src/app/(site)/page.module.css` — substituído: a fila de quatro colunas
- `frontend/README.md` — `## A raiz: a programação` e *Estrutura*

**Raiz**

- `README.md` — uma decisão em *Decisões: por que isso e não aquilo*
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 3.1 em `review`
- `_bmad-output/implementation-artifacts/3-1-ver-a-programacao.md` — esta story

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Ajustes de tela pedidos pelo Igor depois de ver a programação renderizada, os dois contrariando o protótipo e o AC13 de propósito. **`a partir de` subiu para cima do preço:** embaixo ele vira legenda de um número já apresentado como se fosse o preço; em cima, as duas linhas se leem como uma frase, e a coluna do preço passa a espelhar a da data — rótulo em mono sobre valor em serifada grande. **A fila ganhou folga** (`padding` de `20px 0` para `26px 12px`): o realce do hover pinta a caixa inteira, então o `padding` é o tamanho do realce, e ele encostava na primeira e na última letra da fila. O recuo lateral foi feito com `padding` e **não** com margem negativa — margem negativa empurraria os fios para fora da medida da coluna, que é a mesma do masthead e é o que faz os filetes correrem de ponta a ponta. `.secTitulo`, `.aviso` e `.vazio` receberam o mesmo recuo de 12px para o texto continuar alinhado entre si |
| 2026-08-11 | Story 3.1 implementada. `GET /eventos` no primeiro `app/api/publico.py`, o router cujo critério de entrada é "não exige conta" — e não um papel, como o do organizador. `EventoNaProgramacao` devolve sete campos e recusa `capacidade`, `vendidos`, `setores` e `imagem_url`: o UX-DR7 passou a valer no `response_model`, e três testes o cobram — igualdade de conjunto das chaves, busca das palavras de estoque no texto inteiro da resposta, e o OpenAPI sem parâmetro de segurança. `listar_programacao()` filtra por `publicado_em IS NOT NULL` e `data_hora >= agora` no mesmo `where`, com o relógio lido uma vez, ordem `data_hora` + `id` e `selectinload`; `preco_minimo_centavos` é o menor preço **entre os setores com ingresso**, e `min()` sobre lista vazia é tratado por `if`, não por `try`. No frontend, a raiz virou a fila de jornal de quatro colunas, `lib/programacao.ts` é o primeiro módulo a falar com a API **sem** repassar cookie, e a fila esgotada é um `<div>` — não um `<Link>` desativado por CSS, que continuaria no Tab. Duas descobertas na execução: o helper de teste precisou trocar `publicado_em: datetime \| None` por `publicado: bool`, porque `None` significava "não informei" e "é rascunho" ao mesmo tempo; e o `try/catch` do módulo novo engolia o `DYNAMIC_SERVER_USAGE` que o `cache: "no-store"` lança, o que exigiu `unstable_rethrow` — a armadilha 6 das Dev Notes, por um caminho que ela não previa. Suíte de 218 para **231**, sem nenhum teste antigo precisando mudar; `tsc`, `lint` e `build` limpos, com `/` marcada dinâmica. Os três READMEs atualizados, e o número da suíte no `backend/README.md` corrigido de 203 para 231 |
| 2026-08-11 | Story 3.1 criada e contextualizada. Quatro decisões do Igor incorporadas: a programação pública **só mostra o que ainda vai acontecer**, com o corte no backend (`data_hora >= agora`), em vez de duas seções na tela ou de uma lista única com um show de 2001 no topo; o **"a partir de"** conta só os setores que ainda têm ingresso, para a listagem não anunciar um preço que ninguém consegue mais pagar; a **fila já linka para `/eventos/{id}`**, abrindo uma janela de três stories até a 3.4 — mesmo padrão da janela do AD-7 da 2.4, e uma exceção consciente ao precedente escrito no `Masthead.tsx`; e **`imagem_url` fica fora do contrato** até a Story 3.3, que é quem consome a arte. Dezenove ACs escritos sobre os cinco blocos do `epics.md`, entre eles o AC7 — o contrato **não devolve** `capacidade`, `vendidos` nem `setores`, porque UX-DR7 se garante no `response_model` e não na tela. Oito suposições declaradas (a rota `GET /eventos` no primeiro `app/api/publico.py`, o nome `EventoNaProgramacao`, `esgotado` como campo e não como ausência de preço, `lib/programacao.ts` separado do `eventos.ts` do organizador, a raiz sendo a programação, o título sem kicker de contexto, nenhuma paginação e nenhum subtítulo na fila) e quatro perguntas registradas para o Igor |
