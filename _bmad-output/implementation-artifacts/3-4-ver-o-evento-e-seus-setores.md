---
baseline_commit: "25796a3 — `style: fio simples no lugar do duplo no masthead`, na branch `Epic-3--Descoberta-e-compra`. Migração `head`: 06c1ad5ac276 (`habilita_extensao_unaccent`). Suíte: 279 testes passando (Story 3.3). ⚠️ Não executei git — este carimbo veio do estado informado no início da sessão; confira antes de começar."
---

# Story 3.4: Ver o evento e seus setores

Status: review

Epic 3 — Descoberta e compra · **A quarta story da epic, e a que fecha a janela aberta na 3.1.**
Desde aquela story a fila da programação aponta para `/eventos/{id}`, e desde a 3.3 a capa aponta
para o mesmo lugar — um endereço que ainda não existe e cai na 404 do projeto. Esta story é quem o
cria.

São uma rota pública nova (`GET /eventos/{id}`), três schemas novos (`DisponibilidadeDoSetor`,
`SetorPublico`, `EventoPublico`), uma função de service, uma rota de tela nova
(`/eventos/[id]`) e a **primeira ilha de cliente do lado público** — o seletor de quantidade.
**Nenhuma migração, nenhuma coluna, nenhum modelo novo, nenhuma dependência nova**, e nem
`GET /eventos`, nem `/eventos/destaque`, nem `/eventos/cidades` mudam uma vírgula.

É também a primeira vez que **preço de setor** atravessa para o lado do cliente. Até aqui só saíram
derivados — `preco_minimo_centavos` e `esgotado` —, justamente para o estoque não vazar junto. Aqui
o preço de cada setor é a informação principal da tela, e continua sendo **proibido** deixar
`capacidade` e `vendidos` atravessarem (UX-DR7, AD-13). O que substitui os dois é um par de campos
derivados: uma proporção e uma palavra.

## Acceptance Criteria

1. **Given** um evento publicado e futuro
   **When** eu chamo `GET /eventos/{id}` **sem nenhum cookie de sessão**
   **Then** recebo `200` com o evento, seus setores e os campos derivados
   **And** a rota é **pública por assinatura**: nenhum `Depends(exigir_papel(...))`, nenhuma
   dependência de sessão, e nenhum parâmetro de query
   **And** chamá-la logado como cliente, organizador ou portaria devolve **exatamente** o mesmo
   corpo

2. **Given** que `/eventos/cidades` e `/eventos/destaque` são paths fixos no mesmo router
   **When** eu declaro `/eventos/{id}` no `publico.py`
   **Then** ela entra **depois** das duas, e o comentário de ordem que já está lá (escrito na 3.2
   apontando para esta story) **passa a valer de verdade**
   **And** ⚠️ é esta a story em que o aviso deixa de ser precaução: com `/eventos/{id}` declarada
   antes, uma chamada a `/eventos/cidades` tentaria ler `"cidades"` como UUID e devolveria `422`
   **And** um teste **prova as duas rotas antigas continuando de pé** depois da rota nova existir —
   sem esse teste, a regressão só apareceria na tela

3. **Given** um `id` que não é evento nenhum, **ou** um evento em rascunho
   (`publicado_em IS NULL`), **ou** um evento cuja `data_hora` já passou
   **When** eu chamo a rota
   **Then** os três recebem `404` com o **mesmo** código e a **mesma** mensagem
   **And** o recorte é **idêntico** ao da `listar_programacao` e ao do `obter_destaque`
   (`publicado_em IS NOT NULL` **e** `data_hora >= agora`), com `agora` lido **uma vez** no início
   do service (decisão do Igor)
   **And** ⚠️ distinguir os três casos transformaria a rota num oráculo — "esse UUID é o rascunho de
   alguém?" —, e é a mesma disciplina do `EVENTO_NAO_ENCONTRADO` do organizador (Story 2.6) e do
   login da 1.4, que não diz se o e-mail existe

4. **Given** um `id` que não é um UUID válido (`/eventos/banana`)
   **When** eu chamo a rota
   **Then** recebo `422` do Pydantic, porque o path param é tipado `UUID`
   **And** a tela trata `404` e `422` no **mesmo** ramo, como o `obterMeuEvento` já faz: para quem
   lê, "esse endereço está errado" e "esse show não está em cartaz" são a mesma coisa

5. **Given** o corpo da resposta
   **When** eu inspeciono suas chaves
   **Then** o evento tem **exatamente oito**: `id`, `nome`, `data_hora`, `local`, `cidade`,
   `imagem_url`, `maximo_por_compra`, `setores`
   **And** cada item de `setores` tem **exatamente cinco**: `id`, `nome`, `preco_centavos`,
   `disponibilidade`, `proporcao_vendida`
   **And** `publicado_em`, `origem_externa_id` e `organizador_id` **não entram** — não são assunto
   de quem está escolhendo um show

6. **Given** o texto inteiro da resposta desta rota
   **When** eu procuro estoque
   **Then** não aparecem `capacidade`, `vendidos`, `publicado_em`, `origem_externa_id` nem
   `organizador_id` (UX-DR7, AD-13)
   **And** ⚠️ **a lista de palavras proibidas desta rota é a terceira diferente do arquivo**:
   `setores` e `imagem_url` já eram legítimas no destaque, e agora **`preco_centavos` também é** —
   é o preço de cada setor, e é a informação principal da tela. Copiar qualquer um dos dois testes
   anteriores sem reescrever a lista o faz falhar, e "consertá-lo" apagando a asserção jogaria fora
   a proteção do UX-DR7 na rota que mais perto chega do estoque. Escreva o motivo dentro do teste
   **And** ⚠️ o campo derivado chama-se `proporcao_vendida` (feminino, concordando com "proporção"),
   e **não** `proporcao_vendidos`: o segundo casaria a palavra proibida `vendidos` na varredura e
   obrigaria a afrouxá-la

7. **Given** um setor com `capacidade = 100` e `vendidos = 39`
   **When** eu leio o item dele
   **Then** `proporcao_vendida` é `0.39` — um número entre `0.0` e `1.0`, arredondado em **duas
   casas**, que é o que a barra do medidor desenha
   **And** `capacidade` e `vendidos` **não** atravessam: proporção não é contagem, e é essa a
   diferença entre dizer "restam 61" e desenhar uma barra pela metade
   **And** a divisão nunca estoura: `capacidade > 0` é `CHECK` no banco desde a Story 2.3

8. **Given** os três estados de um setor
   **When** eu leio `disponibilidade`
   **Then** ela é um enum fechado de três valores: `DISPONIVEL`, `ULTIMOS` e `ESGOTADO`
   **And** `ESGOTADO` quando `vendidos >= capacidade`; `ULTIMOS` quando **resta 20% ou menos** da
   capacidade (decisão do Igor); `DISPONIVEL` no resto
   **And** a ordem das condições importa: **esgotado é conferido primeiro**, senão 0% restante cairia
   em `ULTIMOS`
   **And** ⚠️ a conta é feita **em inteiros** — `(capacidade - vendidos) * 5 <= capacidade` —, e não
   com `0.2` em ponto flutuante: um setor de 15 lugares com 12 vendidos dá exatamente 20%, e é
   justamente na borda que o `float` decide sozinho
   **And** o limiar é derivado de `capacidade` e `vendidos` **no backend**, e só a palavra atravessa
   (AD-13)

9. **Given** um evento com Pista, VIP e Camarote
   **When** eu leio `setores`
   **Then** os três vêm, **inclusive o esgotado**, em ordem alfabética — a ordem que o
   `order_by="Setor.nome"` do `relationship` já garante (Story 2.3), sem nenhum `sorted()` no service
   **And** evento **sem setor nenhum** (possível por `psql`, e existe no banco de desenvolvimento do
   Igor) devolve `setores: []` e **não quebra a rota**

10. **Given** o campo `maximo_por_compra`
    **When** eu o leio
    **Then** ele é `6` — um teto **fixo por compra**, e não o que resta em estoque (decisão do Igor)
    **And** ⚠️ é o que permite ao stepper ter um teto **sem que o contrato revele quantos ingressos
    restam**: `maximo_por_compra = min(disponivel, 6)` daria um stepper mais honesto e diria "restam
    2" toda vez que restassem poucos, que é exatamente o que o UX-DR7 mantém fora da tela do cliente
    **And** pedir mais do que existe é recusado na **Story 3.6**, pelo `UPDATE` condicional do AD-3 —
    e o `EXPERIENCE.md#Concorrência` já escreve a frase ("Esgotou enquanto você decidia")
    **And** ele vem **do contrato** e não é constante do frontend: o dia em que a regra mudar, a
    tela e a rota de reserva não podem discordar sobre qual é o teto

11. **Given** a rota `GET /eventos`, `GET /eventos/destaque`, `GET /eventos/cidades` e os 279 testes
    que já existem
    **When** eu rodo a suíte depois desta story
    **Then** **nenhum deles precisa mudar**: os três contratos anteriores não ganham nem perdem campo
    **And** se algum teste antigo quebrar, algo saiu do escopo — pare e diga

12. **Given** um evento publicado e futuro
    **When** eu abro `/eventos/{id}` no navegador
    **Then** vejo, em duas colunas, o cabeçalho à esquerda — kicker com a data por extenso e o dia da
    semana, nome em serifada grande, e a ficha — e a **arte à direita** (decisão do Igor)
    **And** a ficha traz **`CASA`** e, quando existe, **`CIDADE`** — rótulo em mono versalete, valor
    em serifada, no mesmo desenho da ficha da capa
    **And** ⚠️ **não há linha de `ENDEREÇO`, de `CLASSIFICAÇÃO` nem de `FONTE`**, que é o que o
    protótipo desenha: nenhum dos três existe no `Evento` (decisão do Igor — ver a tabela de
    decisões). O que a tela mostra é o que o banco tem
    **And** a página é **Server Component** nesta metade: nenhuma linha de `"use client"` no
    `page.tsx`

13. **Given** o link de volta
    **When** eu o vejo no topo
    **Then** é `← Programação`, apontando para `/`, no mesmo padrão do `← Meus eventos` da tela do
    organizador
    **And** ele é um `<Link>` de texto, não um botão

14. **Given** a lista de setores
    **When** eu vejo cada um
    **Then** vejo o nome em serifada, a **barra de proporção**, a palavra do estado em versalete, o
    preço, e o stepper de quantidade à direita
    **And** a barra é 5px de altura, fundo `var(--breu2)`, preenchimento `var(--neon)` em
    `DISPONIVEL`, `var(--brasa)` em `ULTIMOS` e `var(--fio2)` **cheio** em `ESGOTADO`
    **And** ⚠️ a informação **não é dada só por cor** (UX-DR9): `Disponível`, `Últimos ingressos` e
    `Esgotado` estão **escritos**, e a barra é `aria-hidden` — quem usa leitor de tela ouve a palavra,
    não uma porcentagem sem contexto
    **And** ⚠️ **nenhum número de estoque aparece na tela**, nem como texto, nem como `title`, nem
    como `aria-label` (UX-DR7)

15. **Given** um setor esgotado
    **When** eu o vejo
    **Then** ele aparece **esmaecido** (`opacity: .38`, a anatomia do `.setor.off` do protótipo) e
    **sem stepper**, com o selo `Esgotado` no lugar dele
    **And** os botões dele não existem no DOM — não são botões desabilitados por CSS, pelo mesmo
    motivo já escrito na fila da 3.1 e na capa da 3.3

16. **Given** o stepper de um setor disponível
    **When** eu aperto `+` e `−`
    **Then** a quantidade sobe e desce **sem confirmação**, e o rodapé recalcula na hora
    **And** não desce abaixo de **zero**, e a **soma de todos os setores** não passa de
    `maximo_por_compra`
    **And** ⚠️ o teto é da **compra**, não do setor: com 6 ingressos escolhidos entre Pista e
    Camarote, **todos** os `+` da tela ficam desabilitados (suposição declarada)
    **And** os botões no limite são `disabled` de verdade — atributo, não opacidade —, e cada um tem
    nome acessível próprio (`Mais um ingresso da Pista`), porque `+` sozinho não diz de que setor é
    **And** a quantidade é anunciada a quem usa leitor de tela sem que ele precise reler a tela

17. **Given** que escolhi 2 na Pista e 1 no Camarote
    **When** eu olho o rodapé
    **Then** ele está **fixo na base** (`position: sticky; bottom: 0`) e mostra `3 ingressos · 2
    setores` e o total `R$ 660,00`
    **And** com **um** setor escolhido ele mostra o nome dele (`2 ingressos · Pista`), como o
    protótipo escreve
    **And** ⚠️ **não há botão** no rodapé (decisão do Igor): reservar e pagar é a Story 3.6, e a rota
    que o botão chamaria não existe. Nada nesta tela promete uma ação que ainda não há
    **And** com **zero** ingressos escolhidos o rodapé **não aparece** — um total de `R$ 0,00`
    grudado na base é ruído (suposição declarada)

18. **Given** um evento com **todos** os setores esgotados
    **When** eu abro a página dele
    **Then** vejo os setores, todos esmaecidos e sem stepper, e **nenhum rodapé**
    **And** a página abre normalmente: evento esgotado é informação, não erro — a mesma regra da fila
    da 3.1 e da capa da 3.3

19. **Given** um evento sem setor nenhum
    **When** eu abro a página dele
    **Then** o cabeçalho aparece inteiro e no lugar da lista vejo uma frase — sem ilustração e sem
    botão grande (UX-DR8)
    **And** a tela **não quebra** e o rodapé não aparece

20. **Given** um `id` que não está em cartaz (inexistente, rascunho ou passado)
    **When** eu abro `/eventos/{id}`
    **Then** vejo a **404 do projeto** (`notFound()`), que já existe desde a Story 1.2 e já tem a
    casca
    **And** ⚠️ `notFound()` **levanta**, como o `redirect()`: ele não pode ficar dentro de um
    `try/catch`, e é por isso que o `try` mora no `lib/`, no molde exato do
    `organizador/eventos/[id]/page.tsx`

21. **Given** que a API está fora do ar
    **When** eu abro a página de um evento
    **Then** vejo a frase "Não foi possível carregar este evento agora. Tente de novo em instantes."
    e o link de volta — **nunca** a 404
    **And** os três estados do `lib/` são discriminados (`ok`, `nao-encontrado`, `indisponivel`),
    como no `ResultadoDoMeuEvento` e pelo mesmo motivo escrito lá: achatá-los faria um show fora de
    cartaz virar instabilidade de servidor

22. **Given** a fila da programação e a chamada principal
    **When** eu clico em qualquer uma das duas
    **Then** chego nesta página — **a janela aberta na Story 3.1 fecha aqui**
    **And** a linha do `frontend/README.md` que registra a janela é **reescrita** (ela está em
    `## A raiz: a programação`), e a entrada correspondente em `README.md#o-que-não-está-pronto`, se
    houver, sai junto

23. **Given** uma tela abaixo de 900px
    **When** abro a página do evento
    **Then** cabeçalho e arte **empilham numa coluna só** (UX-DR6), com o **cabeçalho acima**
    (suposição declarada)
    **And** cada setor empilha: nome, medidor e estado acima; preço e stepper abaixo — **sem cortar
    nenhum valor** e sem rolagem horizontal
    **And** o rodapé continua **fixo na base e legível**, sem cobrir o último setor da lista

24. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira e os **279** testes anteriores continuam verdes
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos, e `/eventos/[id]`
    aparece como rota **dinâmica** (`ƒ`) no relatório

25. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta, na seção `## Programação pública` que já existe: a rota
    de detalhe, o `404` único para os três casos, **por que a disponibilidade vira proporção e
    palavra** em vez de número, e o teto fixo por compra — além do número novo da suíte
    **And** `frontend/README.md` documenta, em `## A raiz: a programação` (ou na seção temática que
    couber): a página do evento, a **primeira ilha de cliente do lado público** e por que ela é uma
    ilha, e o **fechamento da janela** do link quebrado
    **And** os dois respeitam a régua de camada do `CLAUDE.md`: **no máximo cinco parágrafos**, na
    seção temática que já existe, sem tabela nova e sem subseção nova
    **And** `README.md` da raiz **não é tocado** nesta story — ver *Perguntas em aberto* nº 3

> **De onde vem cada critério.** O `epics.md` traz **cinco** blocos para a Story 3.4: nome, data,
> local e endereço com a lista de setores e preço; a disponibilidade em três palavras com barra de
> proporção e nunca número absoluto (UX-DR7, AD-13); o setor esgotado esmaecido e sem stepper; o
> total recalculando no rodapé sem confirmação; e o empilhamento abaixo de 900px com o rodapé
> continuando fixo. Eles viraram os ACs **12/14**, **8/14**, **15**, **16/17** e **23**.
>
> Todo o resto é decisão do Igor (tabela abaixo) ou consequência técnica dela: o endereço que não
> existe (AC12), o recorte com `404` único (ACs 3 e 4), a proporção e o teto fixo no contrato (ACs
> 7, 8 e 10), a arte ao lado do cabeçalho (AC12), vários setores somando no mesmo rodapé (ACs 16 e
> 17) e o rodapé sem botão (AC17).

## Tasks / Subtasks

- [x] **T1. `app/schemas/evento.py` — os três schemas** (AC: 5, 6, 7, 8, 10)
  - [x] `class DisponibilidadeDoSetor(str, Enum)` com `DISPONIVEL`, `ULTIMOS`, `ESGOTADO`, no molde
        do `PeriodoDaProgramacao` que já está no arquivo
    - [x] Docstring dizendo **por que é enum e não `bool` + `bool`**, e por que ele é derivado no
          backend: o limiar nasce de `capacidade` e `vendidos` (AD-13), e mandar os dois números
          para a tela decidir seria o UX-DR7 caindo pelo caminho mais curto
  - [x] `class SetorPublico(BaseModel)` com `id`, `nome`, `preco_centavos`, `disponibilidade`,
        `proporcao_vendida`
    - [x] **Sem `from_attributes`**, como o `EventoNaProgramacao` e o `EventoEmDestaque`: dois dos
          cinco campos não são atributos do `Setor`
    - [x] Docstring dizendo que ele **não é o `SetorSaida`** e por quê: aquele carrega `capacidade` e
          `vendidos` porque é o inventário do organizador, e reusá-lo aqui é o UX-DR7 caindo por
          reuso de schema — a mesma armadilha registrada na Story 3.3
    - [x] Docstring do `proporcao_vendida`: por que proporção e não contagem, e por que o nome é
          **feminino** (o teste de varredura do AC6)
  - [x] `class EventoPublico(BaseModel)` com as oito chaves do AC5
    - [x] Docstring com o que ele **recusa** e por quê: `capacidade`/`vendidos` (UX-DR7),
          `publicado_em`/`origem_externa_id`/`organizador_id` (assunto de quem publica)
    - [x] Docstring do `maximo_por_compra`: por que teto fixo e não `min(disponivel, 6)`, e por que
          ele vem do contrato em vez de ser constante da tela (AC10)
  - [x] ⚠️ `EventoNaProgramacao`, `EventoEmDestaque` e `EventoSaida` **não mudam** (AC11)

- [x] **T2. `app/services/evento.py` — o detalhe público** (AC: 1, 3, 7, 8, 9, 10)
  - [x] `MAXIMO_POR_COMPRA = 6` como constante de módulo, com comentário do porquê do número
  - [x] `_disponibilidade_do_setor(setor) -> DisponibilidadeDoSetor` — função privada, para a regra
        do limiar existir num lugar só e ser lida por um teste
    - [x] Esgotado primeiro; `ULTIMOS` por `(capacidade - vendidos) * 5 <= capacidade`, em inteiros
  - [x] `obter_publico(sessao, evento_id) -> EventoPublico`
    - [x] `agora = datetime.now(timezone.utc)` lido **uma vez**
    - [x] Uma consulta só, com as **três** condições no mesmo `where` (`id`, publicado, futuro) —
          e não um `sessao.get()` seguido de dois `if`, pelo mesmo motivo escrito no
          `obter_do_organizador`: com tudo no `where`, "só vejo o que está em cartaz" é verdade por
          construção
    - [x] `.options(selectinload(Evento.setores))`
    - [x] `None` → `raise ErroDeDominio("EVENTO_NAO_ENCONTRADO", "Esse show não está em cartaz.",
          status_http=404)` — **um** código e **uma** mensagem para os três casos (AC3)
    - [x] `proporcao_vendida=round(setor.vendidos / setor.capacidade, 2)`
    - [x] Docstring: por que o recorte é o mesmo das outras três rotas públicas, e por que os três
          casos recebem a mesma resposta
  - [x] ⚠️ `listar_programacao`, `obter_destaque` e `listar_cidades_em_cartaz` **não mudam**

- [x] **T3. `app/api/publico.py` — a quarta rota pública** (AC: 1, 2, 3, 4)
  - [x] `@router.get("/eventos/{evento_id}", response_model=EventoPublico)`, com
        `evento_id: UUID` e `sessao: Session = Depends(obter_sessao)`
  - [x] Declarada **depois** de `/eventos/cidades`, `/eventos/destaque` e `/eventos`
  - [x] Atualizar o comentário do bloco de ordem: ele foi escrito **apontando para esta story**, e
        agora descreve algo que existe. Duas linhas, não um parágrafo novo
  - [x] Docstring: pública pelo mesmo critério das outras três; o `404` único; e o que o corpo
        recusa
  - [x] `app/main.py` **não muda**: o router já está incluído

- [x] **T4. Testes do backend** (AC: 1–11, 24)
  - [x] Em `tests/test_programacao.py`, reusando `_evento_gravado` — é o módulo das rotas públicas,
        e é lá que os helpers e as fixtures moram. ✅ **Ele já serve como está**: cada setor é a tupla
        `(nome, capacidade, vendidos, preco_centavos)`, então os três estados de disponibilidade e a
        borda dos 20% se produzem sem tocar no helper. **Não mexa nele**
  - [x] Sem cookie → `200`; logado como cliente → corpo idêntico
  - [x] Rascunho → `404`; evento passado → `404`; `id` inexistente → `404`; e os três com o **mesmo
        código e a mesma mensagem** (AC3)
  - [x] `id` que não é UUID → `422`
  - [x] O evento tem **exatamente as oito chaves**, e cada setor **exatamente as cinco** (AC5)
  - [x] ⚠️ Varredura de palavras proibidas com lista **própria**: sem `setores`, sem `imagem_url` e
        **sem `preco_centavos`** — com o motivo escrito dentro do teste (AC6)
  - [x] `proporcao_vendida` de 39/100 é `0.39`; de 0/50 é `0.0`; de 50/50 é `1.0`
  - [x] Os três estados de `disponibilidade`, **com o caso de borda**: 12/15 vendidos (resta
        exatamente 20%) é `ULTIMOS`; 11/15 é `DISPONIVEL`; 15/15 é `ESGOTADO`
  - [x] Setores em ordem alfabética, incluindo o esgotado (AC9)
  - [x] Evento sem setor nenhum → `setores: []`, sem quebrar (AC9)
  - [x] `maximo_por_compra` vem `6` e **não** varia com o estoque (grave um setor com 2 restantes e
        confira que continua `6`) (AC10)
  - [x] `imagem_url = None` → `null` na resposta
  - [x] ⚠️ **A regressão de ordem de rota** (AC2): depois da rota nova existir, `GET /eventos/cidades`
        e `GET /eventos/destaque` continuam respondendo o que respondiam — **não** `422`
  - [x] OpenAPI: a rota declara **um** parâmetro de path e nenhum de query nem de segurança
  - [x] ⚠️ **Nenhum teste antigo deve precisar mudar** (AC11). Se algum quebrar, pare e diga

- [x] **T5. `src/lib/programacao.ts` — os tipos e a busca** (AC: 5, 20, 21)
  - [x] `export type DisponibilidadeDoSetor = "DISPONIVEL" | "ULTIMOS" | "ESGOTADO"`
  - [x] `export type SetorPublico` e `export type EventoPublico`, espelhando as chaves do backend
  - [x] `export type ResultadoDoEvento` com **três** estados (`ok`, `nao-encontrado`,
        `indisponivel`) — o molde é o `ResultadoDoMeuEvento` do `lib/eventos.ts`, e o docstring dele
        explica por que três e não dois
  - [x] `obterEvento(id): Promise<ResultadoDoEvento>` — `cache: "no-store"`, sem `headers` e sem
        `cabecalhoDeSessao()` (a rota é pública), com `encodeURIComponent(id)` na URL
  - [x] ⚠️ `404` **e** `422` caem no mesmo `nao-encontrado`, **antes** do `!resposta.ok` genérico —
        exatamente como o `obterMeuEvento` faz, e pelo motivo escrito lá
  - [x] ⚠️ `unstable_rethrow(erro)` como **primeira linha** do `catch` — este módulo é o único do
        `lib/` que precisa disso, e o motivo inteiro já está escrito nele desde a 3.1

- [x] **T6. `src/app/(site)/eventos/[id]/page.tsx` — a tela** (AC: 12, 13, 19, 20, 21, 23)
  - [x] Pasta e módulo de estilo novos (`page.module.css`), no mesmo padrão da raiz
  - [x] ⚠️ `params` é `Promise` nesta versão do Next: `const { id } = await params` (o gêmeo está no
        `organizador/eventos/[id]/page.tsx`)
  - [x] `nao-encontrado` → `notFound()`; `indisponivel` → frase + link de volta; `ok` → a tela
  - [x] Cabeçalho: `← Programação`, kicker com `dataDaChamada`, `<h1>` do nome, ficha `<dl>` com
        `CASA` e `CIDADE` (a de cidade some quando nula, como na capa)
  - [x] Arte à direita: `<img>` com `eslint-disable-next-line @next/next/no-img-element` e `alt=""`;
        sem `imagem_url`, o bloco `--breu2` do mesmo tamanho — **o mesmo padrão da capa da 3.3**,
        inclusive o `::after` que cobre imagem morta
  - [x] `<EscolhaDeIngressos setores={...} maximoPorCompra={...} />`
  - [x] Sem setor nenhum → a frase do AC19 no lugar do componente
  - [x] ⚠️ **Nenhum `"use client"` neste arquivo** (AC12)

- [x] **T7. `src/components/EscolhaDeIngressos.tsx` — a ilha** (AC: 14, 15, 16, 17, 18)
  - [x] `"use client"` na primeira linha. **É a primeira ilha do lado público**, e a convenção da
        espinha nomeia exatamente este caso ("seletor de quantidade")
  - [x] Em `components/`, e **não** dentro da tela como o `ChamadaPrincipal`: a diretiva é do
        **módulo**, e um `"use client"` no `page.tsx` arrastaria a página inteira para o cliente. O
        precedente é o `FormularioPublicacao`
  - [x] Props **serializáveis**: a lista de setores e o teto. Nenhuma função atravessa a fronteira
  - [x] `useState<Record<string, number>>` com a quantidade por `setor.id`
  - [x] Cada setor: nome, medidor, palavra do estado, preço, stepper
  - [x] Medidor: `<div aria-hidden>` com a largura em `%` vinda de `proporcao_vendida`
  - [x] Setor `ESGOTADO`: esmaecido, **sem stepper**, com o selo — o `.selo` da raiz é a anatomia
  - [x] Stepper: `<button type="button">` com nome acessível por setor; `disabled` no zero e no teto
        da **soma**; a quantidade num elemento com `aria-live="polite"`
  - [x] Rodapé sticky com `N ingressos · X setores` (ou o nome, com um setor só) e o total, formatado
        por `centavosParaReais`. **Sem botão** (AC17)
  - [x] Soma zero → o rodapé não é renderizado
  - [x] ⚠️ **Nada de `Intl` aqui**: dinheiro é `centavosParaReais` do `lib/formato.ts`, que é módulo
        puro e atravessa a fronteira de propósito

- [x] **T8. `page.module.css` da tela nova** (AC: 14, 15, 17, 23)
  - [x] `.pagina`, `.voltar`, `.cabecalho`, `.arte`/`.arteVazia`/`.imagemDaArte`, `.nomeDoEvento`,
        `.ficha`/`.fichaRotulo`/`.fichaValor`, `.setores`, `.setor`/`.setorEsgotado`,
        `.medidor`/`.preenchimento`, `.estado`, `.preco`, `.stepper`, `.rodape`, `.total`, `.selo`,
        `.vazio`
  - [x] **Nenhum hex novo** — só `var(--token)`. ⚠️ O protótipo escreve `#221F1C`, `#3A352F` e
        `var(--ambar)`, que são a **paleta antiga**: o fundo do medidor é `var(--breu2)`, o esgotado
        é `var(--fio2)` e o acento é `var(--neon)`
  - [x] **Sem card, sem sombra, sem raio** (UX-DR3); fio de 1px entre os setores
  - [x] O recuo lateral acompanha o da raiz, para os fios correrem de ponta a ponta
  - [x] Media query de 900px: uma coluna, cabeçalho acima da arte, setor empilhando em duas linhas

- [x] **T9. Verificação** (AC: 23, 24)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos, e `/eventos/[id]` como
        `ƒ` no relatório de rotas
  - [ ] Conferir na tela, com `next dev` e `uvicorn` no ar — ⚠️ **os sete são conferência do Igor**,
        e não minha: conferência visual é dele (regra permanente do projeto). **Não subir servidor**
    - [ ] Clicar numa fila da raiz e chegar na página — a janela da 3.1 fechada
    - [ ] Clicar na capa e chegar na mesma página
    - [ ] Um setor de cada estado na mesma tela (dá para produzir mexendo em `vendidos` por `psql`)
    - [ ] Stepper: subir, descer, o teto de 6 travando **todos** os `+`, e o rodapé acompanhando
    - [ ] Um `id` inventado na barra de endereço → a 404 do projeto
    - [ ] Derrubar o `uvicorn` e recarregar → a frase de indisponível, **não** a 404
    - [ ] Abaixo de 900px: empilhamento e rodapé continuando fixo sem cobrir o último setor
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2)
  - [x] ⚠️ Conferir que os arquivos novos **estão rastreados** — **não executo git** (regra do
        projeto); a conferência é do Igor. **Esta story cria pasta nova no frontend**, e é
        exatamente o caso em que o `.gitignore` já mordeu antes
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** se algum for iniciado

- [x] **T10. Os READMEs** (AC: 22, 25) — obrigatório, regra do projeto
  - [x] `backend/README.md`, até cinco parágrafos em `## Programação pública`
  - [x] `frontend/README.md`, até cinco parágrafos, **reescrevendo a linha da janela do link
        quebrado** (`frontend/README.md:1367-1369`)
  - [x] Conferir se `README.md#o-que-não-está-pronto` tem entrada sobre a página do evento ou sobre o
        link quebrado; se tiver, ela **sai**. Fora isso, a raiz **não é tocada**
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README
(T10) — é o "por quê" dele.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| O endereço que o AC pede | **Não existe, e a ficha mostra o que o banco tem**: `CASA` e `CIDADE`. O `Evento` não tem coluna de endereço, o formulário de publicação não pede um, e a Discovery não é consultada ao vivo (AD-1) | *Coluna `endereco` nova*: cumpriria o AC ao pé da letra — caiu porque arrastaria migração, campo no `EventoEntrada` e um `<input>` no `FormularioPublicacao`, que é tela já revisada da Epic 2, para dentro de uma story de leitura; e o dado só existiria para o que fosse publicado dali em diante. E *`local · cidade` rotulado `ENDEREÇO`*: cumpriria a palavra sem cumprir a coisa — quem lê "endereço" espera rua e número e receberia o que a linha `CASA` já dizia |
| O teto do stepper | **Fixo por compra: `maximo_por_compra = 6`**, vindo do contrato. Nenhum número de estoque atravessa: o que a tela recebe é uma proporção e uma palavra. Pedir mais do que resta é recusado na Story 3.6 pelo `UPDATE` condicional do AD-3 — que é a garantia mais pontuada do desafio, e cujo caminho de recusa passa a ser **demonstrável** | *`maximo_por_compra = min(disponivel, 6)`*: o stepper pararia no que existe de verdade e ninguém pediria o impossível — caiu porque o teto revelaria o estoque toda vez que ele fosse pequeno ("restam 2", pela tela e pelo devtools), que é exatamente o que o UX-DR7 mantém fora. E *`disponivel` cru no contrato*: a tela faria barra, palavra e teto sozinha — caiu porque é o UX-DR7 caindo no contrato, a linha que as Stories 3.1 e 3.3 defenderam com `response_model` e teste de varredura |
| O rodapé nesta story | **Só o total, sem botão.** O rodapé recalcula e mostra quantidade, setores e valor; `Reservar e pagar` entra na 3.6, junto com a rota que ele chama | *Botão apontando para o que vier*: seria a mesma janela consciente do `/eventos/{id}` entre a 3.1 e esta story — caiu porque a janela do link já custou três stories e não precisa de uma segunda, e um botão primário que cai na 404 é pior que um link de fila que cai. E *botão presente e desabilitado*: deixaria o bloco visualmente completo — caiu porque uma ação bloqueada sem motivo escrito lê como defeito, não como escopo |
| "Últimos ingressos" | **Resta 20% ou menos da capacidade.** Proporção pura, na mesma moeda do medidor: a barra e a palavra dizem a mesma coisa, e a regra vale igual para um setor de 50 e um de 5.000 lugares | *Restam 10 ingressos ou menos*: diria a verdade num setor grande — caiu porque num setor de 20 lugares metade da casa já seria "últimos". E *o que vier primeiro dos dois*: cobriria os dois tamanhos e custaria uma condição e um teste a mais, sem que nenhum caso real deste produto precise dela hoje |
| A arte | **Ao lado do cabeçalho**, como o protótipo desenha: ficha à esquerda, arte à direita. Reusa o `<img>` com `alt=""` e o `::after` da Story 3.3, e a metade de cima continua Server Component | *Sem arte*: a página seria mais rápida e mais estreita — caiu porque tiraria a única imagem da tela em que a pessoa decide comprar. E *faixa larga acima do título*: teria mais impacto e empurraria a lista de setores para baixo da dobra, que é justamente o que a tela existe para mostrar |
| O recorte da rota | **O mesmo da programação: publicado e futuro.** Rascunho, evento passado e `id` inexistente recebem o **mesmo** `404` | *Rascunho `404`, passado abre*: quem guardou o link do show de ontem ainda veria a página — caiu porque o recorte deixaria de ser um só entre as quatro rotas públicas, e custaria um estado de tela novo ("este show já aconteceu"). E *qualquer evento por id*: o rascunho de um organizador viraria público para quem adivinhasse o UUID, e a Story 3.1 gastou um AC provando que rascunho não aparece |
| Vários setores na mesma escolha | **Somam.** O rodapé diz `3 ingressos · 2 setores`, e o modelo da Story 3.5 já prevê isso — `item_reserva` é lista justamente para uma reserva ter vários itens | *Um setor por vez*, zerando o anterior: seria mais simples de reservar na 3.6 (um item, um `UPDATE`) — caiu porque zerar em silêncio a escolha que a pessoa acabou de fazer é o tipo de coisa que ninguém entende quando acontece, e porque obrigaria duas compras para levar um amigo ao camarote |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar.

- **O teto de 6 é da compra inteira, não de cada setor.** Com 4 na Pista e 2 no Camarote, todos os
  `+` travam. É o que a palavra "por compra" diz, e é o que a Story 3.6 vai cobrar do lado do
  servidor. Seis por setor daria até dezoito ingressos numa reserva.
- **A data não vira linha da ficha.** Ela já está no kicker, por extenso e com o dia da semana. Uma
  linha `DATA` repetindo o que está três centímetros acima é a ficha se contradizendo em tamanho de
  fonte. Se preferir a ficha com três linhas, é uma linha de JSX.
- **A `FONTE` do protótipo (`Ticketmaster Discovery · G5vYZ9a1kd`) fica fora.** `origem_externa_id`
  é assunto de quem publica, não de quem escolhe um show — e é o mesmo argumento com que ele já
  ficou fora dos outros três contratos públicos.
- **Abaixo de 900px o cabeçalho vem acima da arte** — o contrário da capa da 3.3. Lá a arte é o
  gancho; aqui o `<h1>` de 52px é a identidade da página, e empurrá-lo para baixo de uma imagem 4/5
  custa a primeira tela inteira no celular.
- **Com zero ingressos escolhidos o rodapé não aparece.** `R$ 0,00` grudado na base é ruído, e o
  rodapé existe para responder "quanto vou pagar" — pergunta que ainda não foi feita.
- **O rodapé nomeia o setor quando há um só, e conta setores quando há mais.** `2 ingressos · Pista`
  é o que o protótipo escreve; com três setores a linha viraria uma lista, e `3 ingressos · 2
  setores` diz a mesma coisa sem quebrar.
- **`proporcao_vendida` é arredondada em duas casas.** Duas casas desenham a barra com precisão de
  1%, que é mais do que 5px de altura conseguem mostrar — e menos dígitos é menos superfície para
  alguém tentar reconstruir a capacidade.
- **O medidor é `aria-hidden`.** A palavra ao lado dele carrega a mesma informação, e uma barra
  anunciada como "39 por cento" convidaria à leitura que o UX-DR7 evita.
- **Nenhuma paginação e nenhuma seção de "eventos parecidos".** A tela é um show e seus setores.

### O contrato da API, campo a campo

**`GET /eventos/{evento_id}`** · `200` · `response_model=EventoPublico` · **pública** ·
**um parâmetro de path, nenhum de query**

```json
{
  "id": "8f2b…",
  "nome": "Baco Exu do Blues",
  "data_hora": "2026-08-15T00:00:00Z",
  "local": "Espaço Unimed",
  "cidade": "São Paulo",
  "imagem_url": "https://s1.ticketm.net/dam/a/….jpg",
  "maximo_por_compra": 6,
  "setores": [
    { "id": "1c…", "nome": "Área VIP", "preco_centavos": 26000,
      "disponibilidade": "ULTIMOS", "proporcao_vendida": 0.8 },
    { "id": "2d…", "nome": "Camarote", "preco_centavos": 42000,
      "disponibilidade": "ESGOTADO", "proporcao_vendida": 1.0 },
    { "id": "3e…", "nome": "Pista", "preco_centavos": 12000,
      "disponibilidade": "DISPONIVEL", "proporcao_vendida": 0.39 }
  ]
}
```

| Campo | Tipo | Nota |
|---|---|---|
| `id` | `UUID` | O mesmo que a fila e a capa já usam no `href` |
| `nome` | `str` | O `<h1>` |
| `data_hora` | `datetime` | O kicker, formatado por `dataDaChamada` |
| `local` | `str` | A linha `CASA` |
| `cidade` | `str \| None` | A linha `CIDADE`; **some** quando nulo |
| `imagem_url` | `str \| None` | A arte; nulo vira bloco `--breu2` do mesmo tamanho |
| `maximo_por_compra` | `int` | **Constante `6`.** Teto do stepper — não varia com o estoque |
| `setores` | `list[SetorPublico]` | Todos, inclusive esgotados, em ordem alfabética |
| `setores[].preco_centavos` | `int` | **Chave legítima aqui**, e a primeira vez em rota de cliente |
| `setores[].disponibilidade` | `enum` | `DISPONIVEL` · `ULTIMOS` · `ESGOTADO` (AD-13) |
| `setores[].proporcao_vendida` | `float` | `0.0`–`1.0`, duas casas. A largura da barra |

**Erro:** `404` com `{"erro": {"codigo": "EVENTO_NAO_ENCONTRADO", "mensagem": "Esse show não está em
cartaz."}}` para inexistente, rascunho e passado — os três iguais. `422` do Pydantic para `id` que
não é UUID.

**As outras três rotas públicas não mudam uma vírgula**, e é o AC11 que cobra isso.

[Fonte: ARCHITECTURE-SPINE.md#AD-13, #AD-3, #Convenções · backend/app/api/publico.py ·
backend/app/schemas/evento.py:267-376]

### A tela, em texto

```
  ← PROGRAMAÇÃO
  ┌──────────────────────────────────────────┬──────────────────────────┐
  │ SEXTA, 15 DE AGOSTO DE 2026, 21H00       │  ▟▛▜▙                    │
  │                                          │   arte 4/5               │
  │ Baco Exu do Blues     ← serifada 52px    │                          │
  │ ─────────────────────────────────────    │                          │
  │ CASA      Espaço Unimed                  │                          │
  │ CIDADE    São Paulo                      │                          │
  └──────────────────────────────────────────┴──────────────────────────┘
  ═══════════════════════════════════════════════════════════════════════
  SETORES                                        ESCOLHA A QUANTIDADE
  ───────────────────────────────────────────────────────────────────────
  Pista                                       R$ 120,00   ┌───┬───┬───┐
  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  ← 39%, em neon                    │ − │ 2 │ + │
  DISPONÍVEL                                              └───┴───┴───┘
  ───────────────────────────────────────────────────────────────────────
  Área VIP                                    R$ 260,00   ┌───┬───┬───┐
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  ← 80%, em brasa                   │ − │ 0 │ + │
  ÚLTIMOS INGRESSOS                                       └───┴───┴───┘
  ───────────────────────────────────────────────────────────────────────
  Camarote                                    R$ 420,00    [ESGOTADO]
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ← 100%, em fio2       ← esmaecido, sem stepper
  ESGOTADO
  ───────────────────────────────────────────────────────────────────────
  ═══════════════════════════════════════════════════════════════════════
  2 INGRESSOS · PISTA                                          R$ 240,00
      ↑ rodapé fixo na base, sem botão nesta story
```

- Cabeçalho em duas colunas; arte com `aspect-ratio: 4/5`
- Setor em duas colunas (`1fr 230px`): nome/medidor/estado à esquerda, preço e stepper à direita
- Medidor de 5px, fundo `var(--breu2)`; stepper de três células de 38px com fio entre elas
- **Sem card, sem sombra, sem raio.** Nenhum hex novo
- Abaixo de 900px: uma coluna; o setor empilha em duas linhas; o rodapé continua na base

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `obter_destaque` | `app/services/evento.py:473` | **O molde da leitura de um evento só**, com `selectinload` e o mesmo recorte. Leia o docstring inteiro |
| `obter_do_organizador` | `app/services/evento.py:604` | **O molde do `404`**: uma consulta com todas as condições no `where`, e uma mensagem só para casos diferentes. ⚠️ Ele **não muda** |
| `listar_programacao` | `app/services/evento.py:311` | A origem do recorte `publicado + futuro` e da derivação por `setor.vendidos` (AD-13). **Não muda** |
| `EventoEmDestaque` | `app/schemas/evento.py:311` | O molde do schema derivado, sem `from_attributes`. **Não muda** |
| `SetorSaida` | `app/schemas/evento.py:169` | ⚠️ **Não reuse.** Carrega `capacidade` e `vendidos` — é o inventário do organizador, e trazê-lo para cá é o UX-DR7 caindo por reuso de schema |
| `PeriodoDaProgramacao` | `app/schemas/evento.py:239` | O molde do `str, Enum` — inclusive o docstring explicando por que enum e não string solta |
| `ErroDeDominio` | `app/core/erros.py:88` | `status_http=404`; o handler global já dá a forma `{"erro": {...}}` |
| `_evento_gravado` | `tests/test_programacao.py:56` | Grava evento com setores; cada setor é `(nome, capacidade, vendidos, preco_centavos)`. **Já serve como está — não mexa nele** |
| `test_programacao.py` | `tests/` | **É este arquivo que cresce** — é o módulo das rotas públicas, com as fixtures e os helpers |
| `obterMeuEvento` | `frontend/src/lib/eventos.ts:113` | **O molde exato da função nova**: três estados, `404`/`422` antes do `!ok`. ⚠️ A daqui **não** manda cookie |
| `obterDestaque` | `frontend/src/lib/programacao.ts:243` | O molde do `no-store` e do `unstable_rethrow` na primeira linha do `catch` |
| `organizador/eventos/[id]/page.tsx` | (arquivo inteiro) | **O molde da tela de detalhe**: `await params`, `notFound()` fora do `try`, e o ramo de indisponível |
| `ChamadaPrincipal` | `(site)/page.tsx:372` | O molde da arte (`<img>` + `eslint-disable` + `alt=""`), do bloco vazio e da ficha `<dl>` |
| `.selo` e `.arte` | `(site)/page.module.css:515, 203` | O selo `Esgotado` e o quadro da arte com o `::after` que cobre imagem morta |
| `FormularioPublicacao.tsx` | `components/` | **O precedente da ilha `"use client"`** com props serializáveis vindas de um Server Component |
| `Botao` | `components/Botao.tsx` | ⚠️ **Não use no stepper**: ele é `width: 100%` desde a 1.4 e explodiria a célula de 38px |
| `centavosParaReais`, `dataDaChamada` | `frontend/src/lib/formato.ts:52, 178` | Dinheiro e o kicker. O módulo é puro e atravessa a fronteira — **nada de `Intl` na tela** |
| `.voltar` | `organizador/eventos/page.module.css:129` | O `← Programação` do topo |
| Tokens | `frontend/src/app/globals.css` | `--neon`, `--brasa`, `--breu`, `--breu2`, `--fio`, `--fio2`, `--fumaca`, `--cal`, `--serif`, `--mono`, `.kicker` |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, as quatro migrações, `seeds/`,
`app/core/`, `app/integrations/`, `app/main.py`, `app/schemas/auth.py`, `app/schemas/catalogo.py`,
`app/api/auth.py`, `app/api/organizador.py`, `app/api/saude.py`, `app/services/autenticacao.py`,
`publicar()`, `listar_portarias()`, `listar_do_organizador()`, `obter_do_organizador()`,
`listar_programacao()`, `obter_destaque()`, `listar_cidades_em_cartaz()`, `tests/conftest.py`,
`docker-compose.yml`, `pyproject.toml`, `package.json`, `next.config.ts`, `lib/servidor.ts`,
`sessao.ts`, `api.ts`, `caminho.ts`, `eventos.ts`, `catalogo.ts`, `formato.ts`, `Masthead.tsx`,
`globals.css`, `(site)/page.tsx`, `(site)/page.module.css`, e as telas de `(entrada)/` e de
`organizador/`.

⚠️ **`lib/programacao.ts` e `api/publico.py` são as duas exceções**, e as duas são exceção por
**acréscimo**: nada do que já está neles muda de forma ou de saída.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Copiar o teste de varredura de palavras proibidas.** É a terceira lista diferente no mesmo
arquivo. Na 3.1, `setores` e `imagem_url` eram proibidas; na 3.3 as duas viraram legítimas; aqui
**`preco_centavos` também vira**. O que continua proibido é o que **conta** ingresso: `capacidade` e
`vendidos`. Escreva a lista do zero e o motivo dentro do teste — apagar a asserção "para consertar"
jogaria fora a proteção do UX-DR7 na rota que chega mais perto do estoque.

**2. Declarar `/eventos/{id}` antes das duas rotas de path fixo.** O comentário está no `publico.py`
desde a 3.2 esperando por esta story. Com ela em cima, `/eventos/cidades` vira `422` — e o sintoma é
a raiz perdendo os chips de cidade, que ninguém liga a uma rota nova de detalhe. O AC2 pede um teste
que prove as duas antigas continuando de pé.

**3. Reusar `SetorSaida` "porque já existe um schema de setor".** Ele carrega `capacidade` e
`vendidos`, que é exatamente o que esta rota não pode devolver. É a mesma armadilha da 3.3, agora com
a tentação maior: aqui a tela **precisa** de dado de setor, e o schema errado está a um import de
distância.

**4. `"use client"` no `page.tsx`.** A diretiva é do **módulo**: pô-la na página arrasta o cabeçalho,
a ficha e a arte para o cliente, e a tela deixa de ser Server Component. A ilha é um arquivo
separado, em `components/`, e recebe dados prontos por props. O `npm run build` é quem denuncia.

**5. `float` no limiar dos 20%.** `(capacidade - vendidos) <= capacidade * 0.2` decide sozinho na
borda: 12 vendidos de 15 é exatamente 20%, e o resultado depende de arredondamento binário. Em
inteiros — `(capacidade - vendidos) * 5 <= capacidade` — a regra é a mesma e não tem borda.

**6. Conferir esgotado depois do limiar.** `ESGOTADO` primeiro, sempre: 0% restante também é "20% ou
menos", e a ordem errada faz o setor esgotado aparecer como "Últimos ingressos" — com barra cheia e a
palavra errada.

**7. Nomear o campo `proporcao_vendidos`.** Ele casaria a palavra proibida `vendidos` na varredura do
AC6 e obrigaria a afrouxar o teste que existe justamente para não ser afrouxado. É `proporcao_vendida`.

**8. Deixar o teto do stepper por setor.** "Por compra" é o que o campo diz. O `+` de um setor precisa
olhar a **soma** de todos, não a própria quantidade.

**9. Botão desabilitado por CSS.** O `+` no teto e o `−` no zero são `disabled` de verdade. Opacidade
sem o atributo deixa o botão clicável e no Tab, anunciado como ativo — a mesma classe de erro que a
fila esgotada da 3.1 evitou sendo `<div>`.

**10. `sticky` que não gruda.** `position: sticky; bottom: 0` só funciona se nenhum ancestral tiver
`overflow` diferente de `visible` e se a página for mais alta que a viewport. O `.conteudo` e o
`<main>` do `(site)/layout.tsx` estão limpos hoje — se o rodapé não grudar, o culpado é uma regra
nova, não o navegador.

**11. Hex do protótipo no CSS.** O `.medidor` do protótipo é `#221F1C` com preenchimento
`var(--ambar)`, e o esgotado é `#3A352F`: são a **paleta antiga**, de antes da troca (`e5ecf30`). Os
três viram `var(--breu2)`, `var(--neon)` e `var(--fio2)`.

**12. `alt` com o nome do artista.** A arte é decorativa: o nome está escrito ao lado em 52px. Mesma
regra da capa.

**13. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest` falhar
com `os error 4551`, chame pelo módulo: `uv run python -m pytest`.

**14. O banco de desenvolvimento é do Igor.** Ele tem eventos reais de conferência, entre eles um sem
setor. **Não apague nada, e não semeie evento novo** — semear é decisão de produto dele. Para ver os
três estados de setor na tela, mexer em `vendidos` por `psql` num evento existente é o caminho, e é
conferência dele.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      publico.py                 # +GET /eventos/{id}
    schemas/
      evento.py                  # +DisponibilidadeDoSetor, +SetorPublico, +EventoPublico
    services/
      evento.py                  # +MAXIMO_POR_COMPRA, +_disponibilidade_do_setor, +obter_publico()
  tests/
    test_programacao.py          # cresce
  README.md
frontend/
  src/
    lib/
      programacao.ts             # +tipos do detalhe, +obterEvento()
    app/(site)/eventos/[id]/
      page.tsx                   # novo
      page.module.css            # novo
    components/
      EscolhaDeIngressos.tsx     # novo — a primeira ilha "use client" do lado público
  README.md
```

Não existe, e não deve passar a existir nesta story: migração, coluna nova, `app/api/cliente.py`,
rota de reserva, tabela `reserva`, `error.tsx`, `loading.tsx`, `generateMetadata`,
`images.remotePatterns` no `next.config.ts`, carrinho, sessão exigida, teste automatizado de
frontend, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| Responde sem cookie, e igual para quem está logado | `test_programacao.py` | 1 |
| Rascunho, passado e inexistente dão o **mesmo** `404` | `test_programacao.py` | 3 |
| `id` que não é UUID dá `422` | `test_programacao.py` | 4 |
| O evento tem as **oito** chaves; cada setor, **cinco** | `test_programacao.py` | 5 |
| Nenhuma palavra de contagem no texto (lista própria) | `test_programacao.py` | 6 |
| `proporcao_vendida` em `0.0`, `0.39` e `1.0` | `test_programacao.py` | 7 |
| Os três estados, **com a borda dos 20%** (11/15, 12/15, 15/15) | `test_programacao.py` | 8 |
| Setores em ordem alfabética, incluindo o esgotado | `test_programacao.py` | 9 |
| Evento sem setor nenhum devolve `[]` sem quebrar | `test_programacao.py` | 9 |
| `maximo_por_compra` é `6` e não varia com o estoque | `test_programacao.py` | 10 |
| `imagem_url` nulo volta `null` | `test_programacao.py` | 5 |
| **`/eventos/cidades` e `/eventos/destaque` continuam de pé** | `test_programacao.py` | 2 |
| OpenAPI: um parâmetro de path, nenhum de query nem de segurança | `test_programacao.py` | 1 |
| As três rotas públicas anteriores com os contratos intactos | (já existe) | 11 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são sete caminhos — os da T9.

**Baseline: 279 testes passando** (Story 3.3).

### Inteligência das stories anteriores

**Da 3.3 — a story imediatamente anterior:**

- **O `<img>` com `alt=""` e o `.imagemDaArte::after`** resolveram a imagem morta da Ticketmaster
  **sem** `"use client"`: pseudo-elemento em `<img>` só ganha caixa quando a imagem falha. A arte
  daqui tem o mesmo problema e a mesma solução — copie o padrão, não invente um `onError`.
- **A varredura de palavras proibidas mudou de lista** e o teste ganhou comentário explicando por
  quê. Aqui ela muda de novo. É a terceira, e o comentário importa mais que antes.
- **O `filtrando` subiu para antes do `Promise.all`** para a capa não ser buscada à toa. Nada
  equivalente aqui — a página tem **uma** busca só —, mas o hábito é o mesmo: não pague ida à rede
  por dado que a tela não vai usar.
- **`preco_minimo_centavos` voltou ao contrato depois da conferência visual.** Se algo desta tela
  precisar mudar depois de o Igor vê-la, é normal e é assim que a 3.3 fechou — o registro vai para o
  Dev Agent Record e o Change Log, e o AC fica como estava.
- **Nenhum teste antigo mudou na 3.3**, e nenhum deve mudar aqui: a rota é nova, e as três antigas
  estão intactas.

**Da 3.2 — a ordem de declaração das rotas.** O comentário do `publico.py` foi escrito **para esta
story**, nomeando `/eventos/{id}` com todas as letras. Esta é a story em que ele para de ser
precaução e passa a descrever o arquivo — e é a story em que o aviso, se ignorado, quebra duas rotas
que já funcionam.

**Da 3.1 — a janela do link quebrado.** A fila aponta para `/eventos/{id}` desde então, e o
`frontend/README.md:1367-1369` registra a janela por escrito, dizendo que "a 3.4 é quem a fecha". A
T10 é quem cumpre isso.

**Da 2.6 — a tela de detalhe do organizador.** Ela é o molde estrutural desta: `await params`,
`notFound()` fora do `try`, ramo de indisponível com link de volta. A diferença de fundo é o UX-DR7:
lá os números exatos aparecem porque é o inventário de quem publicou; aqui eles não podem nem sair do
banco.

**Da paleta (commit `e5ecf30`):** o acento é `--neon` (`#ff4f9a`). **O `DESIGN.md` e o protótipo
continuam escrevendo "âmbar"** e não foram tocados: onde eles disserem âmbar, leia neon. A fonte
única dos valores é `frontend/src/app/globals.css`.

[Fonte: _bmad-output/implementation-artifacts/3-3-chamada-principal-na-programacao.md ·
3-1-ver-a-programacao.md · 2-6-ver-e-gerenciar-meus-eventos.md]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | Path param tipado `UUID`, ordem de declaração de rota |
| Pydantic | 2.13.4 | Os três schemas novos, sem `from_attributes` |
| SQLAlchemy | 2.0.51 | `select().where().options(selectinload(...))`, `.first()` |
| PostgreSQL | 16 | Nenhuma mudança de schema |
| Next.js | **16.3.0** | `PageProps<"/eventos/[id]">`, `params` como `Promise`, `notFound()` |
| React | 19 | `useState` na primeira ilha de cliente do lado público |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** A documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

### Escopo — o que NÃO fazer aqui

Reserva, estoque e `UPDATE` condicional (3.5 e 3.6) · cronômetro · checkout e pagamento (3.8) ·
ingresso e QR (3.9) · exigir login para escolher quantidade · editar evento · upload de imagem ·
qualquer rota de escrita · qualquer alteração nas rotas do organizador · teste automatizado de
frontend.

Quatro tentações concretas:

- **"Já crio o `POST /reservas`, o rodapé precisa de um botão."** O botão não existe nesta story por
  decisão do Igor, e a reserva é a 3.6 inteira — com máquina de estados (AD-4) e o `UPDATE`
  condicional (AD-3)
- **"Já devolvo `disponivel` para o stepper parar no lugar certo."** É a alternativa descartada do
  teto, e é o UX-DR7 caindo no contrato
- **"Guardo a quantidade escolhida no `localStorage` para não perder ao recarregar."** É estado de
  compra sem reserva por trás: o estoque não está segurado, e o número guardado mente assim que
  alguém comprar
- **"Aproveito e mostro a `atracao` do catálogo na ficha."** Ela é campo do `ItemDoCatalogo`, existe
  só no contrato da busca da Ticketmaster e **não é gravada** — o `Evento` só tem
  `origem_externa_id`. É a entrada aberta no `deferred-work.md`, e fechá-la é decisão do Igor, não
  desta story

### Project Structure Notes

`publico.py` passa a ter **quatro** rotas, e o critério de entrada do arquivo continua o que o
docstring dele diz: nenhuma exige conta. É também o arquivo em que a ordem de declaração deixa de ser
teoria — duas rotas de path fixo e uma de path param convivendo, com o comentário que a 3.2 escreveu
finalmente descrevendo o presente.

É a primeira vez que o frontend ganha uma **rota dinâmica pública**. `/organizador/eventos/[id]` já
existe, mas atrás de duas guardas; esta responde a quem chegou pelo endereço, o que significa que o
`404` e o "indisponível" precisam ser distinguíveis por quem nunca fez login — e é por isso que o
`lib/` tem três estados e não dois.

E é a primeira **ilha de cliente do lado público**. Até aqui todo `"use client"` do projeto está em
formulário atrás de login (`FormularioLogin`, `FormularioCadastro`, `FormularioPublicacao`) ou em
navegação (`NavLink`, `BotaoSair`). O seletor de quantidade é o caso que a tabela de convenções da
espinha nomeia por extenso, e a fronteira precisa ficar visível no código: a página é servidor, o
componente é cliente, e entre os dois passam **dados**, nunca funções.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] — os cinco blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — o objetivo da epic e as stories vizinhas
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade
- [Source: ARCHITECTURE-SPINE.md#AD-3] — o `UPDATE` condicional que recusa o excesso, na Story 3.6
- [Source: ARCHITECTURE-SPINE.md#AD-12] — preço e capacidade pertencem ao setor
- [Source: ARCHITECTURE-SPINE.md#Convenções] — Server Component por padrão; `"use client"` só onde há
  interação que exige o navegador, e "seletor de quantidade" está escrito lá
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`
- [Source: DESIGN.md#Components/setor] — nome serif 25px, medidor, estado em versalete, stepper
- [Source: DESIGN.md#Components/medidor] — barra de 5px; proporção, jamais número. ⚠️ O documento
  escreve `ambar`; o token vivo é `--neon`
- [Source: DESIGN.md#Components/stepper] — três células com fio, 38px
- [Source: DESIGN.md#Typography] — título de evento serif 52px/1, `-0.035em`
- [Source: EXPERIENCE.md#setor + stepper] — não desce de zero, esgotado sem stepper, total sem
  confirmação
- [Source: EXPERIENCE.md#rodapé de compra] — fixo na base, nunca obriga a rolar de volta
- [Source: EXPERIENCE.md#Responsive & Platform] — ficha de evento empilha abaixo de 900px
- [Source: EXPERIENCE.md#Concorrência] — "Esgotou enquanto você decidia", a frase da Story 3.6
- [Source: mockups/proto-jornal-noturno.html:110-144, 338-384] — o CSS e o markup da tela do evento
- [Source: backend/app/api/publico.py:34-45] — o comentário de ordem escrito para esta story
- [Source: backend/app/services/evento.py:473-561] — `obter_destaque`, o molde da leitura de um só
- [Source: backend/app/services/evento.py:604-634] — `obter_do_organizador`, o molde do `404`
- [Source: backend/app/schemas/evento.py:169-180] — `SetorSaida`, e por que ele não serve aqui
- [Source: frontend/src/lib/eventos.ts:59-143] — os três estados e a ordem dos `if`
- [Source: frontend/src/app/(site)/organizador/eventos/[id]/page.tsx] — o molde da tela de detalhe
- [Source: frontend/src/app/(site)/page.tsx:372-493] — `ChamadaPrincipal`, o molde da arte e da ficha
- [Source: frontend/README.md:1367-1369] — a janela do link quebrado, que esta story fecha
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, régua de cinco parágrafos;
  git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. Ao
   terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída** — até cinco parágrafos por camada.
   Documentação não bloqueia o commit: aplique o código, rode a suíte, mostre o resultado, **depois**
   escreva
3. **Decisão de produto ou de modelagem é do Igor.** As sete desta story estão respondidas e as nove
   suposições estão declaradas. Se aparecer uma oitava — campo a mais, tela a mais, rota a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Conferência visual é do Igor.** Não abra a aplicação para conferir: entregue o roteiro e espere
7. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
8. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas ela **cria pasta nova no frontend**, e é exatamente o caso que já derrubou um build
   da Vercel. A conferência de rastreamento é do Igor (T9)
9. **O code review é ao fim da Epic 3**, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **O número 6 é o teto certo?** Sympla e Eventim usam entre 4 e 10 por compra, e o produto não tem
   regra de negócio que diga qual. Ele está numa constante do service e no contrato — trocá-lo é uma
   linha e um teste. **Para o dev agent: implemente `6` e não pergunte de novo.**
2. **Sem login para escolher quantidade.** A tela deixa qualquer visitante mexer no stepper e ver o
   total; o login só será exigido quando a reserva existir (3.6). É o comportamento de Sympla e
   Eventim, e é o que evita mandar a pessoa fazer conta antes de saber quanto custa — mas significa
   que a Story 3.6 vai precisar decidir **o que acontece com a escolha** quando o visitante for
   mandado ao login: ela se perde, ou volta pela URL?
3. **A raiz recebe decisão nova?** Escrevi para **não** tocar o `README.md` da raiz. A defesa do
   contrário existe e é melhor que a da 3.3: *disponibilidade atravessa como proporção e palavra,
   nunca como número* é uma escolha de contrato que vale para toda tela de cliente daqui em diante, e
   quem avalia veria um sistema diferente se `capacidade` e `vendidos` saíssem na resposta. Se você
   achar que passa na régua, é um bloco de três partes, e o material está na tabela de decisões.
4. **O `deferred-work.md` tem uma entrada esperando esta story:** *"`atracao` atravessa todo o
   contrato e ninguém usa — adiado porque a Epic 3 pode consumi-la na página do evento"*. Ela **não**
   pode: `atracao` só existe no contrato da busca do catálogo e nunca foi gravada no `Evento`. A
   entrada pode ser fechada como "não vai ser consumida", e a limpeza vira decisão sua — não fiz nada
   com ela nesta story.
5. **Nenhum evento é semeado**, e agora há uma tela a mais provando isso: numa máquina limpa o
   avaliador não tem nem em que clicar para chegar aqui. É a mesma pergunta da 3.1, da 3.2 e da 3.3,
   com um motivo a mais.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5[1m]`), via `bmad-dev-story`.

### Debug Log References

- `uv run python -m pytest tests/test_programacao.py -q` → **75 testes** (61 antes, +14 desta story).
- `uv run python -m pytest -q` → **293 testes**, todos verdes. Baseline da 3.3: 279. Nenhum teste
  antigo precisou mudar (AC11 e AC24).
- `npm run build` → limpo. `/eventos/[id]` aparece como **`ƒ`** no relatório de rotas (AC24).
- `npx tsc --noEmit` e `npm run lint` → limpos.
  ⚠️ Na primeira tentativa o `tsc` falhou com `Type '"/eventos/[id]"' does not satisfy the constraint
  'AppRoutes'`: o `PageProps<"/eventos/[id]">` depende do registro de rotas que o Next gera em
  `.next/types`, e a rota é nova. Rodar `npm run build` antes regenerou o registro e os dois passaram.
  Não é defeito do código — é a ordem certa quando a story cria rota.
- Busca por `NEXT_PUBLIC` em `frontend/src/` → **zero** ocorrências (AD-2).
- Nenhum servidor foi iniciado, então não há porta 3000/8000 para encerrar.

### Completion Notes List

**O que ficou pronto.** A rota `GET /eventos/{evento_id}` com os três schemas novos
(`DisponibilidadeDoSetor`, `SetorPublico`, `EventoPublico`), a função `obter_publico` com o helper
`_disponibilidade_do_setor`, a constante `MAXIMO_POR_COMPRA = 6`, catorze testes novos, a rota de tela
`/eventos/[id]` como Server Component, a ilha `EscolhaDeIngressos` e o módulo de estilo. Nenhuma
migração, nenhuma coluna, nenhuma dependência nova, e `GET /eventos`, `/eventos/destaque` e
`/eventos/cidades` não mudaram uma vírgula.

**A janela da Story 3.1 fechou.** `/eventos/{id}` existe, e os dois links que apontavam para o nada —
a fila da programação e a chamada principal — chegam na página. A linha do `frontend/README.md` que
registrava a janela foi reescrita (AC22). O `README.md` da raiz **não foi tocado**: conferi a tabela
`#o-que-não-está-pronto` inteira e não há entrada sobre a página do evento nem sobre o link quebrado.

**As duas armadilhas anunciadas foram as reais.** A varredura de palavras proibidas é a **terceira**
lista diferente do mesmo arquivo — escrevi do zero, com `preco_centavos` fora dela e o motivo dentro
do teste. E `/eventos/{evento_id}` está declarada **no fim** do `publico.py`, com um teste provando
`/eventos/cidades` e `/eventos/destaque` de pé depois disso; o comentário de ordem escrito na 3.2 foi
reescrito, porque ele apontava para o futuro e agora descreve o arquivo.

**Três decisões de escrita que não estavam na story, e por quê.** (1) A ficha ficou **em linha**, como
a da capa, e não nas linhas verticais do protótipo — o AC12 pede "no mesmo desenho da ficha da capa", e
com só dois pares sobrando (`CASA` e `CIDADE`) o desenho vertical do protótipo, que fazia sentido com
cinco, viraria dois rótulos soltos num vazio. (2) Os fios são **simples**, nunca `3px double`: o
protótipo fecha o cabeçalho e abre o rodapé com fio duplo, e ele saiu do masthead por decisão sua em
2026-08-12. (3) Abaixo de 900px a arte deixa de ser 4/5 e vira 16/10 — retrato na largura cheia de um
celular ocupa mais de uma tela, e o que ficaria abaixo dela é a lista de setores, que é o motivo de a
página existir. Nenhuma das três muda contrato nem comportamento; se discordar de qualquer uma, é CSS.

**Uma colisão de nome de classe que só apareceu escrevendo.** A página e a ilha compartilham o mesmo
`page.module.css` (padrão do `FormularioPublicacao`), e eu tinha `.identidade` nas duas — a coluna de
texto do cabeçalho e a coluna esquerda do setor. Viraram `.cabecalhoTexto` e `.identidadeDoSetor`.

**Duas correções vindas da conferência visual do Igor, depois da suíte passar.**

*(1) O stepper aparecia com as células quase brancas.* Defeito meu, e a causa é que **não existe reset
de `<button>` no `globals.css`** — o `*` cuida de `box-sizing`, `margin` e `padding`, e o resto fica
com o padrão do navegador (`background-color: ButtonFace`). O `−` no zero parecia cinza porque é
`disabled` e a `opacity: .35` lava o branco; clicar no `+` habilitava o `−` e revelava o branco cheio,
que foi exatamente o sintoma relatado. Nenhum botão do projeto tinha esbarrado nisso porque **todos
pintam o próprio fundo**: o `Botao` é `var(--neon)` desde a 1.4, e o `.remover` e o `.acrescentar` do
formulário de publicar já escrevem `background: none; border: none; cursor: pointer` — a convenção
existia e eu não a segui. `.passo` passou a escrever as três.

*(2) A arte virou `16/10`, e não o `4/5` do protótipo* (decisão do Igor, tomada com a tela montada).
O retrato deixava um vão de ~360px entre a ficha e a lista de setores: a coluna da arte tem ~489px de
largura, e 4/5 dá **611px de altura** contra ~250px da coluna de texto ao lado — é a arte que manda na
altura da linha do grid. O Igor levantou a hipótese de ser o container do site; **não era, e era o
contrário** — container mais largo daria arte mais alta e vão maior, então a tela pioraria sozinha no
dia em que a coluna crescesse. O agravante que decidiu: o vão empurrava a lista de setores para baixo
da dobra, que é literalmente o motivo pelo qual a "faixa larga acima do título" tinha sido descartada
nesta story — o retrato reintroduzia a alternativa recusada pela altura em vez da largura. Em 16/10 a
arte fica com ~305px, o cabeçalho equilibra, e o produto passa a ter **uma** proporção de arte só, a
mesma da capa. A regra de 16/10 da media query de 900px saiu junto, porque virou redundante. Sobra um
vão residual de ~50px; se ele incomodar, `align-items: center` no `.cabecalho` é uma linha e é o que a
capa já faz.

*(3) A data desceu do kicker para dentro da ficha, e o kicker saiu* (decisão do Igor, mesma rodada de
conferência). **Isso derruba a suposição declarada nº 2 desta story** — eu tinha escrito que a data
não viraria linha da ficha, e o motivo era não repetir o kicker com dois tamanhos de fonte a três
centímetros de distância. Movendo em vez de duplicar, o motivo continua respeitado e o objetivo do
Igor é atendido: a coluna de texto ganha altura, que é o que sobrava de vão depois da arte encolher.
Com três pares em vez de dois, a ficha trocou a versão **em linha** da capa pelas **linhas verticais
do protótipo** — o desenho vertical era o que eu tinha descartado por parecer solto com dois pares, e
com três ele volta a ser o certo e é o que preenche a coluna. O `<h1>` perdeu a margem de topo, porque
passou a ser o primeiro elemento depois do link de volta.

Nenhuma das três toca contrato, service, schema ou teste — as três são tela, e o `npm run build`,
`tsc --noEmit` e `lint` foram rodados de novo a cada uma, limpos, com `/eventos/[id]` ainda como `ƒ`.

⚠️ **O que falta é seu, e é a T9.** Os sete caminhos de conferência visual continuam desmarcados de
propósito: conferência na tela é sua (regra permanente do projeto), e não subi servidor nenhum. O
roteiro está na T9, e o caminho mais rápido para ver os três estados de setor na mesma tela é mexer em
`vendidos` por `psql` num evento que já existe — não semeei nem apaguei nada. Falta também a
conferência de que os arquivos novos **estão rastreados**: esta story cria **pasta nova no frontend**
(`src/app/(site)/eventos/`), que é exatamente o caso em que o `.gitignore` já mordeu antes, e eu não
executo git.

### File List

**Backend**

- `backend/app/schemas/evento.py` — modificado (+`DisponibilidadeDoSetor`, +`SetorPublico`,
  +`EventoPublico`; nada existente mudou)
- `backend/app/services/evento.py` — modificado (+`MAXIMO_POR_COMPRA`,
  +`_disponibilidade_do_setor`, +`obter_publico`; imports)
- `backend/app/api/publico.py` — modificado (+`GET /eventos/{evento_id}` no fim do arquivo; comentário
  de ordem reescrito; imports)
- `backend/tests/test_programacao.py` — modificado (+14 testes da Story 3.4; import de `uuid4`)
- `backend/README.md` — modificado (`## Programação pública`, três parágrafos; contagem da suíte)

**Frontend**

- `frontend/src/lib/programacao.ts` — modificado (+`DisponibilidadeDoSetor`, +`SetorPublico`,
  +`EventoPublico`, +`ResultadoDoEvento`, +`obterEvento`)
- `frontend/src/app/(site)/eventos/[id]/page.tsx` — **novo**
- `frontend/src/app/(site)/eventos/[id]/page.module.css` — **novo**
- `frontend/src/components/EscolhaDeIngressos.tsx` — **novo** (primeira ilha `"use client"` pública)
- `frontend/README.md` — modificado (`## A raiz: a programação`: a linha da janela reescrita e quatro
  parágrafos novos)

**Artefatos**

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `3-4` → `review`
- `_bmad-output/implementation-artifacts/3-4-ver-o-evento-e-seus-setores.md` — este arquivo

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-12 | Três correções vindas da conferência visual do Igor, todas de tela e nenhuma tocando contrato ou teste. **O stepper saía com as células quase brancas**: não existe reset de `<button>` no `globals.css`, e sem `background: none` o botão fica com o `ButtonFace` do navegador — o `−` no zero parecia cinza só por causa da `opacity: .35` do `disabled`, e clicar no `+` revelava o branco. Todo botão vazado do projeto já escrevia essas linhas (`.remover`, `.acrescentar`); eu não segui a convenção. **A arte virou `16/10`, a mesma da capa, e não o `4/5` do protótipo**: numa coluna de ~489px o retrato dava 611px de altura contra ~250px da coluna de texto, deixando ~360px de vão e empurrando a lista de setores para baixo da dobra — que é o motivo pelo qual a "faixa larga acima do título" já tinha sido descartada nesta story, reintroduzido pela altura em vez da largura. Não era o container do site, e era o contrário: container mais largo daria vão maior. **A data desceu do kicker para dentro da ficha e o kicker saiu**, derrubando a suposição declarada nº 2 — movida em vez de duplicada, ela enche a coluna de texto sem repetir frase; com três pares a ficha trocou o desenho em linha pelas linhas verticais do protótipo |
| 2026-08-12 | Story 3.4 implementada. Backend: `GET /eventos/{evento_id}` no fim do `publico.py`, os três schemas novos, `obter_publico` com `_disponibilidade_do_setor` e `MAXIMO_POR_COMPRA = 6`. Frontend: `obterEvento` com três estados no `lib/programacao.ts`, a rota `/eventos/[id]` como Server Component, e a **primeira ilha `"use client"` do lado público** (`EscolhaDeIngressos`). A janela do link quebrado, aberta na 3.1, **fechou** — a linha do `frontend/README.md` foi reescrita. Suíte de 279 para **293 testes**, sem nenhum teste antigo mudar; `npm run build`, `tsc --noEmit` e `lint` limpos, com `/eventos/[id]` como `ƒ`. Falta só a conferência visual da T9, que é do Igor |
| 2026-08-12 | Story 3.4 criada e contextualizada. Sete decisões do Igor incorporadas: **o endereço não existe** e a ficha mostra `CASA` e `CIDADE`, porque o `Evento` não tem a coluna e criá-la arrastaria migração e tela revisada da Epic 2 para dentro de uma story de leitura; **o teto do stepper é fixo por compra** (`maximo_por_compra: 6` no contrato), e não `min(disponivel, 6)`, para que nenhum número de estoque atravesse — quem recusa o excesso é o `UPDATE` condicional do AD-3, na 3.6; **o rodapé não tem botão**, porque reservar e pagar é a 3.6 e nada na tela deve prometer ação que não existe; **"Últimos ingressos" é 20% ou menos**, proporção pura, na mesma moeda do medidor; **a arte fica ao lado do cabeçalho**, reusando o `<img>` e o `::after` da 3.3; **o recorte é o mesmo das outras três rotas públicas**, com rascunho, passado e inexistente recebendo o mesmo `404`; e **vários setores somam na mesma escolha**, que é o que o `item_reserva` da 3.5 já prevê. Vinte e cinco ACs escritos sobre os cinco blocos do `epics.md`, entre eles o AC6, que é a armadilha menos óbvia: `preco_centavos` vira chave legítima nesta resposta, e a lista de palavras proibidas é a **terceira** diferente do mesmo arquivo de teste. Nove suposições declaradas e cinco perguntas registradas para o Igor — entre elas o fechamento da entrada de `atracao` no `deferred-work.md`, que a Epic 3 não vai consumir |
