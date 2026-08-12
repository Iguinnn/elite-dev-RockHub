# Code review — Epic 3: Descoberta e compra

**Data:** 2026-08-12
**Alvo:** `main...HEAD` na branch `Epic-3--Descoberta-e-compra` — 12 commits, stories 3.1 a 3.9
**Diff:** 72 arquivos, 19.169 linhas acrescentadas, 219 removidas (~12.200 de código)
**Formato:** nove subagentes — três camadas (Blind Hunter, Edge Case Hunter, Acceptance Auditor)
× três grupos (A: leitura pública 3.1–3.4 · B: reserva→pagamento→ingresso 3.5–3.9 · C: frontend)

**Triagem:** 7 decisões · 25 patches · 18 adiados · 9 descartados.
Nenhuma camada falhou. Severidade atribuída depois de ler o código em cada ponto — não pelo hunk.

## Desfecho — tudo aplicado em 2026-08-12

**As 7 decisões foram respondidas pelo Igor e os 31 patches resultantes estão no código.** A suíte
foi de **379 para 395 testes**, verde em duas rodadas seguidas; `tsc --noEmit`, `eslint` e
`next build` passam limpos.

| Decisão | Resposta do Igor |
|---|---|
| D1 · AD-5 "sem consultar o banco" | **Reescrever o critério.** O `nonce` fica; a promessa é que estava errada. A garantia real é o recálculo, não a ausência de I/O — corrigido na techspec e no docstring do `conferir_codigo` |
| D2 · `proporcao_vendida` vaza a capacidade | **Aceitar e corrigir o comentário.** Explorar exige compra real e repetida; o que não podia ficar era o schema afirmando que não há caminho de volta |
| D3 · Reserva que vence durante o gateway | **Aceitar a folga.** Coerente com a colheita preguiçosa do AD-4 — quem estava pagando quando o relógio virou não é quem o AD-4 quer punir. Registrado no docstring do `pagar` |
| D4 · Sequestro de estoque por conta | **Declarar no README.** Corte consciente, com três dias de prazo e 13 stories pela frente |
| D5 · Busca com duas palavras | **Tokenizar por espaço** — `AND` de `OR`s, uma condição por palavra |
| D6 · Cidade não normalizada | **Aceitar** — o seed controla as cidades da avaliação, e o conserto tocaria o modelo da Epic 2 |
| D7 · `GET /eventos` sem teto | **Teto fixo de 200**, sem paginação. Declarado no README, com o aviso de que apertar significa paginar, não aumentar |

**Dois achados novos apareceram durante a aplicação**, e os dois são de teste que passava sem provar:

- **A fixture `cliente` precisou de `expire_all()` por requisição.** Alinhar o `conftest` com o
  `expire_on_commit=False` de produção quebrou 10 testes, todos por leitura velha do identity map —
  nenhum era defeito real. O `dependency_overrides` entrega ao app a mesma `Session` do teste, e em
  produção cada requisição tem a sua; o `expire_all` num lugar só compensa isso sem enfraquecer
  nenhuma asserção. Antes isso acontecia **por acidente**, via a divergência que escondeu o P1.
- **Adulterar o último caractere de uma assinatura base64 não adultera nada em ~4,7% dos casos.**
  32 bytes viram 43 caracteres — 258 bits para 256 de dado —, então `A`, `B`, `C` e `D` decodificam
  igual. `test_seguranca.py` falhava de forma intermitente por isso (foi como o defeito apareceu), e
  o **teste de forja do ingresso tinha o mesmo padrão** — ali em silêncio, porque a asserção é
  `is False`: o teste que prova que o ingresso não é forjável passava sem ter forjado nada. Os dois
  passaram a trocar o **primeiro** caractere, que carrega 6 bits significativos.

O teste novo da corrida do pagamento foi **verificado contra a regressão que ele existe para pegar**:
com a transição para `PAGA` tornada incondicional, ele falha com `sum([True, True]) == 2` — as duas
conexões vencendo. O ponto de injeção é o gateway, que roda depois da guarda de leitura e antes da
transição.

O que **passou limpo**, e vale registrar porque é o que as specs marcaram como armadilha: o
`EventoNaProgramacao` sem `capacidade`/`vendidos`/`setores`/`imagem_url`; a arte só pela rota de
destaque; o esgotado continuando na capa; o `maximo_por_compra` fixo; o `404` único para rascunho,
passado e inexistente; a ordem das rotas; o `UPDATE` condicional do AD-3 no `criar()`; o `commit`
antes do `raise`; a emissão dentro do ramo que vence o `_transicionar`; o `hmac.compare_digest`;
o segredo próprio de ingresso; o `titular_nome` vindo do checkout; e, no frontend, a raiz sem
`"use client"`, o `?voltar=` sem parâmetro novo, o canhoto sem desenhar QR (isso é 4.2), e nenhum
`border-radius`/`box-shadow`/`#000`/`@keyframes` nos CSS novos.

---

## Decisões — precisam do Igor

- [x] **[Review][Decision] D1 · O "sem consultar o banco" do AD-5 é inalcançável com o `nonce` na fórmula** — `backend/app/core/seguranca.py:176`.
  O QR carrega `ID.ASSINATURA` e nada mais. `conferir_codigo(codigo, evento_id, nonce)` exige o
  `nonce`, que só existe na coluna `ingresso.nonce`: quem valida precisa buscar a linha pelo `id`
  **antes** de conseguir recalcular o HMAC. Consultar o banco é pré-requisito da verificação, não
  etapa posterior. A não-forja está real e bem feita; o que não se sustenta é a promessa de rejeitar
  sem I/O. O teste que carimba o critério passa porque fabrica o nonce localmente — prova que a
  função é pura, não que o fluxo rejeita antes de consultar.
  **Opções:** (a) tirar o `nonce` da fórmula e assinar só `id+evento_id`, recuperando a promessa ao
  custo de perder a entropia por ingresso; (b) manter o `nonce` e reescrever o critério e o AD-5 para
  "recalcula em vez de comparar com a coluna", que é a garantia que de fato existe.
  **Urgente:** a Story 5.2 bate nisso no primeiro endpoint de validação.

- [x] **[Review][Decision] D2 · `proporcao_vendida` permite reconstruir a capacidade** — `backend/app/services/evento.py:740` e `backend/app/schemas/evento.py:455`.
  Com a reserva da 3.6 no ar, reservar `N` e recarregar `/eventos/{id}` dá `Δp ≈ N/capacidade`. Num
  setor de 15, comprar 3 move a barra em exatamente `0.20` e revela a capacidade inteira — e é no
  setor pequeno que o UX-DR7 importa. O comentário do schema afirma o oposto ("não existe caminho de
  volta daqui para `capacidade` nem para `vendidos`"), o que autoriza o próximo autor a não pensar.
  **Opções:** (a) trocar o float por faixa discreta (ex.: quartis) e fechar o canal; (b) aceitar o
  vazamento como custo da barra e **corrigir o comentário**, que hoje está errado.

- [x] **[Review][Decision] D3 · Reserva que vence durante a chamada ao gateway vira `PAGA`** — `backend/app/services/reserva.py:562`.
  A checagem de prazo usa `condicao_extra=Reserva.expira_em < func.now()` na entrada; a transição
  vencedora condiciona só `de=PENDENTE`, sem nada sobre `expira_em`. Reserva com 200 ms de prazo e
  gateway levando 2 s: vira `PAGA` e emite ingresso depois de vencida, com o cronômetro em zero.
  O estoque continua coerente — o dano é de contrato.
  **Opções:** (a) condicionar a transição a `expira_em >= func.now()`, ao custo de recusar depois de
  já ter cobrado; (b) aceitar e registrar a folga, que é coerente com a colheita preguiçosa.

- [x] **[Review][Decision] D4 · Uma conta pode sequestrar o estoque de um show inteiro** — `backend/app/services/reserva.py:264`.
  O `MAXIMO_POR_COMPRA` é teto **por requisição**. Nada limita reservas `PENDENTE` por cliente, por
  evento ou por janela. Uma conta autenticada em laço prende o show por 10 minutos, renováveis — e a
  colheita preguiçosa devolve o estoque exatamente no `criar()` que o atacante está chamando.
  **Opções:** (a) limite de reservas `PENDENTE` por cliente/evento; (b) linha em
  `README.md#o-que-não-está-pronto` — é corte consciente, e o enunciado penaliza o não declarado.

- [x] **[Review][Decision] D5 · Busca com duas palavras cruzando colunas devolve vazio** — `backend/app/services/evento.py:401`.
  O padrão é `%<termo inteiro>%` contra `nome`, `local` e `cidade` com `OR`. `?q=marina sena são paulo`
  não casa nada: nenhuma coluna sozinha contém a string inteira. O "ou" do docstring é entre colunas,
  não entre tokens, e artista+cidade é o que se digita primeiro.
  **Opções:** (a) tokenizar por espaço com `AND` de `OR`s; (b) manter substring única e registrar no
  docstring, que hoje não diz nada sobre isso.

- [x] **[Review][Decision] D6 · Cidade não normalizada gera chips duplicados que dividem os eventos** — `backend/app/services/evento.py:423` e `:611`.
  `EventoEntrada.cidade` só faz `strip()`, e o organizador digita à mão. `"São Paulo"`, `"Sao Paulo"`
  e `"são paulo"` viram três chips, cada um com um subconjunto disjunto. O `?q=` é imune (passa por
  `unaccent`), o `?cidade=` não — a mesma story trata as duas metades de forma diferente.
  **Opções:** (a) normalizar na publicação; (b) comparar o chip com `unaccent(lower(...))`;
  (c) aceitar, já que o seed controla as cidades da avaliação.
  ⚠️ Toca o modelo da Epic 2.

- [x] **[Review][Decision] D7 · `GET /eventos` não tem `LIMIT` nem paginação** — `backend/app/services/evento.py:435`.
  A rota da tela mais visitada devolve toda a programação publicada e futura, com `selectinload` de
  todos os setores. O próprio docstring, 90 linhas acima, descarta filtrar no cliente porque "a
  programação inteira atravessaria a rede a cada visita" — que é o que a rota faz sem filtro, o
  estado inicial da raiz.
  **Opções:** (a) teto fixo; (b) paginação no contrato; (c) aceitar para o volume do desafio e
  declarar no README.

---

## Patches — conserto inequívoco

### Alta

- [x] **[Review][Patch] P1 · A resposta do pagamento devolve `PENDENTE` e `ingressos: []` em produção** [`backend/app/core/db.py:35`, `backend/app/services/reserva.py:609-621`]
  `SessaoLocal` usa `expire_on_commit=False`; `conftest.py:104` usa o default `True`. Como o
  `_transicionar` roda com `synchronize_session=False`, `reserva.estado` continua `'PENDENTE'` no
  objeto Python. Em teste o `commit` expira e a releitura traz `PAGA`; em produção não expira nada,
  então `_ingressos` devolve `[]` e `_para_saida` devolve `PENDENTE`. O banco fica certo, a resposta
  HTTP não. Hoje ninguém vê porque o `FormularioDePagamento` ignora o corpo e chama `router.refresh()`
  — mas o docstring da rota promete o contrário, e a Epic 4 consome esse corpo.
  **Fix:** `sessao.refresh(reserva)` depois do `commit`, e alinhar o `conftest` com o `expire_on_commit`
  de produção. *(confirmado por duas camadas independentes)*

- [x] **[Review][Patch] P2 · `ESTOQUE_INSUFICIENTE` parcial trava a tela num laço com a frase errada** [`frontend/src/components/EscolhaDeIngressos.tsx:118-163`]
  O backend levanta esse código sempre que `vendidos + quantidade > capacidade` — inclusive quando
  restam 3 e a pessoa pediu 4. Aí o setor volta como `ULTIMOS`, não `ESGOTADO`: `esgotados` sai vazio,
  nenhuma quantidade é zerada, `meuEsgotado` é `undefined` e `sobrando` é o primeiro não-esgotado, que
  é justamente o que acabou de falhar. Toast: *"Esgotou enquanto você decidia. Ainda há ingressos no
  setor Pista"* com 4 ainda no stepper, e cada novo clique repete o mesmo `409` para sempre. Como a
  tela não pode revelar estoque, a única saída é decrementar adivinhando. É o caminho mais provável do
  `409` na prática, e o único não tratado. *(confirmado por duas camadas)*

- [x] **[Review][Patch] P3 · O checkout pede ao navegador que preencha um cartão real** [`frontend/src/components/FormularioDePagamento.tsx:218,226,237,247`]
  O aviso no topo diz "use dados fictícios" e três linhas abaixo os campos declaram `cc-number`,
  `cc-name`, `cc-exp` e `cc-csc` — os tokens que fazem o navegador oferecer o cartão salvo de verdade,
  com um clique. O PAN completo então viaja no corpo JSON até um gateway simulado. O backend está
  limpo (reduz a dígitos, compara o final, descarta; nada é logado) — o problema é inteiro da tela.
  **Fix:** `autoComplete="off"` nos quatro.

### Média

- [x] **[Review][Patch] P4 · `402` respondido sem commit quando a transição para `RECUSADA` perde** [`backend/app/services/reserva.py:541-560`]
  O `raise` está fora do `if`. Perdendo o `rowcount`, nada é gravado e a resposta diz
  *"Nada foi cobrado, e os lugares voltaram para a venda"* sobre uma reserva que está `PAGA` ou
  `EXPIRADA` — falsa nas duas metades. O caminho vencedor já trata o mesmo desfecho com `409`.

- [x] **[Review][Patch] P5 · `_devolver_estoque` é a única escrita de estoque cujo `rowcount` ninguém lê** [`backend/app/services/reserva.py:147-161`]
  O comentário invoca o AD-3, mas o AD-3 é `UPDATE` condicional **provado por `rowcount`**. A guarda
  `vendidos >= quantidade` transforma inconsistência em silêncio: a reserva vira `EXPIRADA`/`RECUSADA`
  e o estoque não volta, sem log e sem erro. O `CheckConstraint` já impede negativo, então a guarda
  não protege o banco — só troca exceção visível por perda silenciosa.

- [x] **[Review][Patch] P6 · `TICKET_SIGNING_SECRET` e `JWT_SECRET` vazios passam o validador** [`backend/app/core/config.py:68,83`]
  A comparação é de igualdade com uma string. Campo apagado no painel → `""` → HMAC com chave vazia →
  ingresso forjável por qualquer um que leia o repositório, que é o risco que o validador existe para
  eliminar. O validador vizinho da Ticketmaster faz o certo (`not ...strip()`) — a assimetria está
  dentro do mesmo arquivo. **Fix:** `not .strip()` mais comprimento mínimo.

- [x] **[Review][Patch] P7 · `conferir_codigo` estoura `TypeError` → `500` com código não-ASCII** [`backend/app/core/seguranca.py:155`]
  `hmac.compare_digest` com `str` só aceita ASCII. Um QR que decodifique como `<uuid>.çç` vira `500`
  na fila da porta, para um código simplesmente inválido. O teste que promete "lixo entra, `False`
  sai" testa cinco entradas e **nenhuma** chega ao `compare_digest`. **Fix:** guarda de `isascii()`.

- [x] **[Review][Patch] P8 · Deadlock provocável: os `UPDATE` de estoque seguem a ordem do corpo** [`backend/app/services/reserva.py:336`]
  A trava Pista→Camarote, B trava Camarote→Pista, o Postgres aborta uma com `40P01`, que sobe como
  `500 ERRO_INTERNO` para o que é conflito recuperável. Mesmo problema sem controle do cliente em
  `_devolver_estoque` e `expirar_vencidas`, que não têm `ORDER BY`.
  **Fix:** ordenar por `setor_id` nos três. *(confirmado por duas camadas)*

- [x] **[Review][Patch] P9 · `unaccent` recria o curinga que o escape acabou de neutralizar** [`backend/app/services/evento.py:401`]
  A ordem é escapar em Python → `unaccent` no Postgres. `_escapar_curingas` só conhece os ASCII, e
  `unaccent('％')` (U+FF05) devolve `%`. `?q=％` vira o padrão `%%%` e devolve a programação inteira —
  a mesma armadilha que o docstring do helper diz estar fechada, por uma porta que ele não cobre.
  Reproduzido contra o Postgres do `docker-compose`. **Fix:** escapar depois do `unaccent`.

- [x] **[Review][Patch] P10 · Duplo clique em "Reservar e pagar" cria uma segunda reserva** [`frontend/src/components/EscolhaDeIngressos.tsx:208-213`]
  `router.push` não é esperado e o `finally` reabilita o botão no mesmo instante. Dois `POST /reservas`
  passam — não há dedupe nem limite. A segunda reserva consome estoque de novo e segura lugares por 10
  minutos, e a pessoa nunca a vê. O comentário reconhece a janela e trata a consequência como
  cosmética. *(confirmado por duas camadas)*

- [x] **[Review][Patch] P11 · O cronômetro zera e o checkout continua inteiro e submissível** [`frontend/src/components/Cronometro.tsx:49`, `frontend/src/app/(site)/reservas/[id]/page.tsx:184`]
  Ao chegar a zero nada relê o servidor: o texto vira "Expirada" e, logo abaixo, a nota continua
  dizendo que os lugares estão segurados e o formulário segue oferecendo pagar. A pessoa preenche CPF,
  cartão e CVV e só descobre no clique — pelo ramo silencioso do `ESTADO_MUDOU`.
  **Fix:** `router.refresh()` no zero. *(confirmado por duas camadas)*

- [x] **[Review][Patch] P12 · A corrida do pagamento não tem teste, e o ramo do AD-14 nunca executa** [`backend/tests/test_ingresso.py:272`, `backend/tests/test_pagamento.py:300`]
  `grep -rn "Barrier\|threading" backend/tests` devolve **um** teste em todo o projeto, e ele é o da
  reserva. Os dois testes de reprocessamento são barrados pela guarda de leitura da linha 525, muito
  antes do `_transicionar` — provam a guarda, não o `rowcount`. Mover a emissão para fora do ramo
  vencedor, que é a regressão que o AD-14 proíbe, deixaria os 379 testes verdes.
  **Fix:** teste com duas `Session` em conexões distintas, com `Barrier`, afirmando 2 ingressos e não 4.
  *(as três camadas do grupo B convergiram)*

- [x] **[Review][Patch] P13 · `test_migracoes.py` não menciona `ingresso`** [`backend/tests/test_migracoes.py:283`]
  A tupla de `test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz` tem seis tabelas; o schema
  tem sete. O AC12 da 3.5 avisou por escrito que sem isso *"uma migração nova com o `downgrade()`
  quebrado passaria sem ser notada"* — a 3.9 é essa migração. Não há asserção nenhuma sobre as sete
  colunas, as três FKs sem `CASCADE` nem os dois índices: um `--autogenerate` distraído reverte as
  decisões da migração sem quebrar nada.

- [x] **[Review][Patch] P14 · O teto de 6 está escrito à mão na mensagem de erro** [`frontend/src/components/EscolhaDeIngressos.tsx:385`]
  O stepper usa a prop `maximoPorCompra`; o `mensagemParaCodigo` devolve o literal *"São até 6
  ingressos por compra"*. É o desencontro que o comentário do próprio tipo `EventoPublico` existe para
  impedir — teto novo no contrato, stepper novo, frase velha.

- [x] **[Review][Patch] P15 · Cinco campos do checkout sem `max_length`** [`backend/app/schemas/pagamento.py:59,66`]
  `cpf`, `telefone`, `numero_cartao`, `validade` e `cvv` não têm teto, e o `BeforeValidator` roda
  `re.sub` sobre a string inteira antes de qualquer conferência de tamanho. Com `meio=PIX` os quatro
  campos de cartão nem chegam ao validador. `schemas/auth.py` documenta exatamente esse risco ao pôr
  `max_length` em `email` e `senha`.

- [x] **[Review][Patch] P16 · `proporcao_vendida = 1.0` junto com `ULTIMOS`** [`backend/app/services/evento.py:740`]
  Capacidade 1000 com 999 vendidos: `round(0.999, 2)` é `1.0` e a disponibilidade é `ULTIMOS`. Barra
  cheia com a palavra "últimos ingressos" e o stepper ativo — indistinguível de `ESGOTADO`, que é o
  sintoma que a ordem das condições do `_disponibilidade_do_setor` diz prevenir.
  **Fix:** `min(round(...), 0.99)` enquanto não estiver esgotado.

### Baixa

- [x] **[Review][Patch] P17 · `origem_externa_id` e `publicado_em` fora da varredura de `GET /eventos`** [`backend/tests/test_programacao.py`]
  O AC7 da 3.1 enumera nove palavras proibidas; a varredura cobre cinco. `origem_externa_id` é varrido
  nas rotas de destaque e de evento, e em nenhuma das duas varreduras de `GET /eventos` — que é a única
  rota onde os três ACs a declaram proibida. Uma palavra em duas tuplas.

- [x] **[Review][Patch] P18 · A raiz fica sem `<h1>` quando há um único evento** [`frontend/src/app/(site)/page.tsx:264`]
  Com um evento só, ele vira a capa, a fila esvazia, o bloco "Programação" some — e a página inicial
  passa a ter `<h2>` como cabeçalho de maior nível. Estado alcançável no primeiro dia de qualquer
  instalação nova.

- [x] **[Review][Patch] P19 · O filtro de cidade ativo não é marcado em neon** [`frontend/src/app/(site)/page.module.css:65`]
  O AC da 3.2 pede filtro ativo marcado em neon. O chip de período cumpre; o `<select>` só tem neon no
  `:hover`. A decisão registrada trocou o **elemento**, não descartou a marcação do estado.

- [x] **[Review][Patch] P20 · `?q=` e `?cidade=` acima de 120 acusam o backend** [`frontend/src/app/(site)/page.tsx:76`]
  O `periodo` é normalizado com um comentário longo explicando por que valor inválido não pode virar
  "não foi possível carregar a programação". `q` e `cidade` não receberam o mesmo tratamento, e o
  backend limita os dois em 120: uma URL colada devolve `422` e imprime exatamente a mentira que a
  normalização do período foi escrita para evitar, dois parâmetros ao lado.

- [x] **[Review][Patch] P21 · Cidade filtrando invisível quando só há uma cidade em cartaz** [`frontend/src/app/(site)/page.tsx:206`]
  O `<select>` só renderiza com `cidades.length > 1`, mas a `cidade` da URL é aplicada sempre. Nesse
  caso a lista sai filtrada sem nenhum controle que explique, e buscar um termo **apaga** a cidade
  (o campo não existe no form) enquanto clicar num chip de período **a preserva**.
  ⚠️ Fora desse caso o `<select>` se submete sozinho — o comentário do código está certo.

- [x] **[Review][Patch] P22 · `setoresFrescos` descarta o `maximo_por_compra` da releitura** [`frontend/src/components/EscolhaDeIngressos.tsx:78`]
  `tratarEstoqueInsuficiente` busca o `EventoPublico` inteiro e usa só `evento.setores`. O teto fica
  preso no valor da primeira renderização, contra o argumento escrito no próprio `lib/programacao.ts`.

- [x] **[Review][Patch] P23 · `PagamentoSimulado` aprova por padrão qualquer meio que não seja Pix** [`backend/app/services/pagamento.py:94`]
  `if meio is PIX: aprova`, e tudo o mais cai no ramo do cartão — com `numero_cartao=None`,
  `"".endswith("0002")` é `False` → aprovado. Acrescentar `BOLETO` ao enum faz o gateway aprovar em
  silêncio. **Fix:** `else: raise` ou `match` exaustivo.

- [x] **[Review][Patch] P24 · `test_config` depende do shell de quem roda** [`backend/tests/test_config.py`]
  `_env_file=None` desliga o `.env`, não o `os.environ`. Quem tiver `TICKET_SIGNING_SECRET` exportada
  faz o `ValueError` não acontecer e o teste falhar por motivo alheio ao que ele afirma. Falta
  `monkeypatch.delenv("TICKET_SIGNING_SECRET", raising=False)`.

- [x] **[Review][Patch] P25 · `Cronometro` renderiza `NaN:NaN` com `expira_em` inválido** [`frontend/src/components/Cronometro.tsx:32`]
  `Math.max(0, NaN)` é `NaN`, não `0` — a rede de proteção não protege, os dois ramos de guarda são
  pulados e a tela imprime `NaN:NaN`. Hoje o contrato está certo; a tela deveria absorver como
  expirada em vez de lixo tipográfico.

---

## Adiados

Ver `deferred-work.md`, seção *Deferred from: code review da Epic 3 (2026-08-12)*.

---

## Descartados como ruído

- `EventoEmDestaque` com nove chaves contra o AC5 que fala em oito — decisão do Igor com a tela
  pronta, registrada no Change Log da 3.3 e no `CHAVES_DO_DESTAQUE` do teste.
- Ramo silencioso do `ESTADO_MUDOU` no checkout — decisão documentada no código: os três códigos
  mudaram o estado no servidor e a página tem uma cara para cada um.
- Paleta âmbar → neon divergindo do `DESIGN.md` — o UX-DR1 do `epics.md` foi atualizado e instrui a
  ler "neon" onde o `DESIGN.md` disser "âmbar".
- "`<input hidden>` de cidade faltando" — falso no caso geral: o `<select>` é campo do form e se
  submete sozinho. Só vale quando ele não renderiza, e isso virou o P21.
- Cronômetro mostrando "0:00" entre 1 e 999 ms — cosmético, dura um segundo.
- `setInterval` continuando a disparar no zero — o React descarta o `setState` de valor igual, sem
  re-render. Desperdício irrelevante; o que importa virou o P11.
- `?cidade=` fora das opções exibindo "Todas as cidades" — mesma causa do P21.
- Standfirst e endereço ausentes contra o `epics.md` — cortes registrados nos ACs 12 das stories 3.3
  e 3.4.
- `Evento.cidade == cidade.strip()` divergindo do AC6, que escreve sem `strip()` — desvio trivial e
  coerente com o tratamento do `q`.
