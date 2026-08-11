# Code review — Epic 2 (Publicação de eventos pelo organizador)

- **Data:** 2026-08-11
- **Alvo:** branch `Epic-2---Publicação-de-eventos-pelo-organizador` vs `main`, commits `63f8e8a`..`525be1c`
- **Escopo revisado:** 39 arquivos de código, +6.105/−66 (docs, stories e `uv.lock` fora)
- **Camadas:** Blind Hunter · Edge Case Hunter · Acceptance Auditor — as três concluíram, nenhuma falhou
- **Placar:** 4 `decision-needed` (resolvidos) · 16 `patch` (**todos aplicados**) · 7 `defer` · 11 descartados
- **Verificação depois dos patches:** `uv run pytest` **218 passando** (eram 203) ·
  `npm run build` ✅ · `tsc --noEmit` ✅ · `eslint` ✅

> **Dois efeitos colaterais que não estavam na lista de achados** e apareceram ao aplicar:
>
> 1. **A suíte tinha uma bomba-relógio.** O `_corpo` de `test_organizador_eventos.py` usava
>    `data_hora: "2026-08-15T00:00:00Z"` — data fixa, escrita quatro dias antes dela. Com o
>    `EVENTO_NO_PASSADO` do P3 valendo, a suíte inteira passaria a falhar em 15/08, no meio do prazo
>    do desafio, sem ninguém ter tocado em nada. Virou `_daqui_a(30)`.
> 2. **Meus três links de "entre de novo" apontavam para `/entrar`, que não existe** — a rota é
>    `/login?voltar=…`. Quem pegou foi o `npm run build` listando as rotas; nem o `tsc` nem o ESLint
>    acusariam, porque `<Link href>` aceita qualquer string.

> **Por que este arquivo existe e não uma seção nas stories.** O workflow do
> `bmad-code-review` escreve os achados no arquivo da story. Aqui isso não vale:
> o `CLAUDE.md` congela story implementada, e o review é da epic inteira — um
> achado como o do fuso atravessa três stories. O review da Epic 1 seguiu o
> mesmo caminho e não tocou os arquivos de story.

---

## Onde as camadas erraram

Registrado porque a triagem é parte do review, e um achado descartado sem motivo
escrito volta no review seguinte.

| Achado | Camada | Veredito |
|---|---|---|
| "AD-7 deixou eventos órfãos quebrados em produção" | Blind | **Falso.** A janela está fechada em `services/evento.py:92-98`, e a branch nunca foi para produção — a Railway publica a `main`, onde a tabela `evento` não existe. Zero eventos órfãos |
| "Duplo envio desprotegido" | Blind | **Exagerado.** `setEnviando(true)` é síncrono antes do `await`; o React redesenha o botão antes do `fetch` resolver. Sobra o `Enter` mantido pressionado — virou P16, severidade baixa |
| "O crash de parsing vaza a `apikey` no log" | Blind + Edge | **Falso.** A exceção nasce fora do `try`, sem `__cause__` do `httpx`, e o `logging` não serializa variáveis locais. O `500` no lugar do `503` é real (P6); o vazamento não |
| "AC6 da 2.1 não cumprido" | Auditor | **Substituído por escrito.** O AC3 da Story 2.2 revisou a decisão antes de a story fechar, com registro no Change Log |

## Cobertura de aceite

| Story | ACs | Cumpridos | Com achado |
|---|---:|---:|---|
| 2.1 — Cliente da Ticketmaster | 10 | 9 | AC6 (substituído por escrito) |
| 2.2 — Buscar a atração no catálogo | 14 | 13 | AC7 (desvio documentado, pedido pelo Igor) |
| 2.3 — Modelo de evento e setor | 12 | 12 | — |
| 2.4 — Publicar um evento com seus setores | 18 | 18 | — |
| 2.5 — Escalar quem valida na porta | 20 | 20 | — |
| 2.6 — Ver e gerenciar meus eventos | 20 | 19 | AC14 (falta o kicker) → P15 |
| **Total** | **94** | **91** | **3** |

**Invariantes verificadas no código final, não na promessa das stories:**
AD-1 ✅ · AD-2 ✅ · AD-7 ✅ (janela fechada) · AD-9 ✅ · AD-11 ⚠️ (ver P1) · AD-12 ✅ · AD-13 ✅ · AD-15 ✅

---

## Decisões tomadas pelo Igor durante o review

- [x] **[Review][Decision] Fuso das telas de servidor** — fixar `America/Sao_Paulo`.
      Descartado: renderizar no cliente (custo de hidratação) e documentar como corte
      (é o único achado visível na tela do avaliador). → vira **P1**
- [x] **[Review][Decision] Sessão expirada no formulário** — mensagem específica
      mais link para o login em nova aba, preservando o formulário preenchido.
      Descartado: redirect automático, que descartaria tudo que foi digitado. → vira **P2**
- [x] **[Review][Decision] Evento com data no passado** — barrar no service com
      `EVENTO_NO_PASSADO`. Descartado: manter publicável só para a seção "Já
      aconteceram" ter o que mostrar. **Consequência aceita:** sem seed de eventos
      antigos, "Já aconteceram" fica invisível na avaliação — entra em
      `README.md#o-que-não-está-pronto`. → vira **P3**
- [x] **[Review][Decision] Filtro de classificação no README da raiz** — não entra:
      a régua de 2026-08-11 barra (escolher dois ids de taxonomia não faz ver "um
      sistema diferente"), e já está documentado nos READMEs de camada. A techspec
      é que precisa parar de exigir. → vira **P4**

## `patch` — fix sem ambiguidade

- [x] **[Review][Patch] P1 · Fuso do servidor formata a data do show** [`frontend/src/lib/formato.ts:38`, `:55`; `frontend/src/app/(site)/organizador/eventos/page.tsx:134-140`]
      Zero ocorrências de `timeZone` no `frontend/src`. `Intl.DateTimeFormat` sem
      `timeZone` usa o fuso do runtime — UTC na Vercel. Um show às 21h de 14/08 em
      São Paulo é gravado certo (`2026-08-15T00:00:00Z`) e lido errado: a
      confirmação (Client Component) diz "14 de agosto, 21h00"; a lista e o detalhe
      (Server Components) dizem "15 AGO" e "15 de agosto, 00h00". Não aparece em
      desenvolvimento — a máquina está em `America/Sao_Paulo`. O corte "Em cartaz" ×
      "Já aconteceram" herda o mesmo deslocamento de 3h. **Severidade: alta.**
- [x] **[Review][Patch] P2 · 401/403 achatados em "tente de novo em instantes"** [`frontend/src/components/FormularioPublicacao.tsx:59-79`]
      `mensagemParaCodigo` não conhece `NAO_AUTENTICADO` nem `SEM_PERMISSAO`. Sessão
      expirando no meio do preenchimento vira um laço sem saída, com todos os setores
      digitados na tela. Vale também para `lib/catalogo.ts:43` e `lib/portarias.ts`,
      que transformam qualquer `!resposta.ok` — inclusive 401, 403 e 422 — em
      "O catálogo da Ticketmaster não respondeu", acusando a Ticketmaster por um erro
      nosso. O `lib/eventos.ts:96-102` já faz a separação certa e serve de modelo.
- [x] **[Review][Patch] P3 · Evento com data no passado é publicável** [`backend/app/schemas/evento.py:118`, `backend/app/services/evento.py:55`]
      O único validador de `data_hora` exige fuso. Recusar com `EVENTO_NO_PASSADO`
      no service (quinta recusa), `min` no input de data, teste, e a linha da
      consequência no `README.md#o-que-não-está-pronto`.
- [x] **[Review][Patch] P4 · Techspec do filtro exige entrada de README que não vai existir** [`docs/techspec-filtro-do-catalogo.md:170-179`]
      §6 e §8 pedem uma entrada em `README.md#decisões` e outra em
      *O que não está pronto*. A régua de 2026-08-11 barra a primeira. Marcar as duas
      seções como supridas pela régua, para a techspec e o `CLAUDE.md` pararem de se
      contradizer.
- [x] **[Review][Patch] P5 · `capacidade` e `preco_centavos` sem teto** [`backend/app/schemas/evento.py:79`, `:83`; `frontend/src/components/FormularioPublicacao.tsx:87-98`]
      `Field(ge=1)` sem `le` contra uma coluna `Integer` (int4): `capacidade:
      3000000000` passa pelo Pydantic, passa pelas quatro recusas e estoura
      `DataError: integer out of range` no `commit` → `500 ERRO_INTERNO`. Alcançável
      pela interface (`<input type="number">` sem `max`). Pior no dinheiro:
      `reaisParaCentavos` faz `Math.round(Number(x) * 100)` sem checar
      `Number.isSafeInteger`, então `999999999999999,99` é gravado **arredondado
      errado, sem erro nenhum** — exatamente o que o AD-11 existe para impedir.
- [x] **[Review][Patch] P6 · Conversão da resposta da Ticketmaster fora do `try`** [`backend/app/integrations/ticketmaster.py:187-194`]
      O `try` cobre só `get`, `raise_for_status` e `json()`. As linhas 187-194,
      `_converter_evento` e `_melhor_imagem` estão fora. Corpo JSON que é lista,
      `images` com `width` string, `name` numérico → `AttributeError`/`TypeError`/
      `ValidationError` → `500`, quando o módulo inteiro existe para prometer que
      "toda falha vira o mesmo `CATALOGO_INDISPONIVEL` 503". A chave **não** vaza
      nesse caminho (verificado).
- [x] **[Review][Patch] P7 · `setores` e `portarias` sem `order_by`** [`backend/app/models/evento.py:114`, `:134`; `backend/app/services/evento.py:223`, `:274`]
      Sem `ORDER BY`, o Postgres devolve na ordem de varredura do heap. Hoje coincide
      com a inserção; a partir do `UPDATE setor SET vendidos = ...` do AD-3, na Epic
      3, a linha atualizada é reescrita no fim do heap e **o setor troca de lugar na
      tela do organizador depois da primeira venda**. `listar_do_organizador` também
      precisa de desempate (`Evento.data_hora, Evento.id`). O `listar_portarias`
      irmão já tem `.order_by(Usuario.nome)`.
- [x] **[Review][Patch] P8 · `evento.organizador_id` sem índice** [`backend/app/models/evento.py:86`]
      É a coluna do `where` de `listar_do_organizador` e metade do de
      `obter_do_organizador`. O `setor.evento_id`, doze linhas abaixo, tem
      `index=True` com o comentário "o Postgres não cria um para chave estrangeira" —
      o argumento é o mesmo. **Custo: uma migração Alembic nova.** Baixa severidade
      no volume de avaliação; entra pela consistência.
- [x] **[Review][Patch] P9 · `imagem_url` aceita qualquer string** [`backend/app/schemas/evento.py:91`]
      Sem `HttpUrl` e sem checagem de esquema. O valor vem do **corpo da
      requisição**, não da Ticketmaster — o service não confere nada contra o
      catálogo. Ele é gravado, devolvido em `EventoSaida` e a Epic 3 vai renderizá-lo
      em `<img src>` na programação pública.
- [x] **[Review][Patch] P10 · `ItemDoCatalogo` sem `max_length`** [`backend/app/schemas/catalogo.py:11`]
      `nome` sem teto no catálogo contra `max_length=200` em `EventoEntrada`. Um show
      da Discovery com nome longo (turnê + patrocinador + "presented by" é rotina lá)
      aparece na lista, é clicável, o passo 2 abre, e o `POST` volta `422` → a tela
      diz "Confira os dados do formulário" sobre um campo que ela **não mostra e
      ninguém pode editar**. Beco sem saída. Vale igual para `imagem_url` > 500.
- [x] **[Review][Patch] P11 · Campo de busca sem `maxLength`** [`frontend/src/app/(site)/organizador/publicar/page.tsx:120-126`]
      O backend tem `Query("", max_length=120)`; o campo não. Colar 200 caracteres
      devolve `422`, que o `catalogo.ts` transforma em "O catálogo da Ticketmaster
      não respondeu" — sem que a Ticketmaster tenha sido chamada.
- [x] **[Review][Patch] P12 · UI deixa passar de 20 setores e 20 escalados** [`frontend/src/components/FormularioPublicacao.tsx:137-142`]
      `max_length=20` nos dois campos do schema; nada na tela informa o teto nem
      impede a 21ª linha. O organizador digita 21 setores e recebe "Confira os dados
      do formulário".
- [x] **[Review][Patch] P13 · Cliente `httpx` do teste é reutilizado depois de fechado** [`backend/tests/test_ticketmaster.py:36-40`, `backend/tests/test_organizador_catalogo.py:26-31`]
      `lambda: cliente` devolve sempre a mesma instância, e o `with _criar_cliente()`
      do código de produção a fecha ao sair. Passa hoje porque todo teste chama
      `buscar_eventos` exatamente uma vez; o segundo `buscar_eventos` no mesmo teste
      levanta `RuntimeError: Cannot send a request, as the client has been closed` —
      uma armadilha de infraestrutura que vai parecer bug de produção para quem
      escrever o próximo caso.
- [x] **[Review][Patch] P14 · Asserção de OpenAPI que passa com qualquer coisa** [`backend/tests/test_organizador_catalogo.py:100`]
      `assert "items" in schema_200` vale para lista de qualquer tipo. Os testes
      irmãos, no mesmo diff, fazem o certo:
      `schema["items"]["$ref"].endswith("/PortariaSaida")`.
- [x] **[Review][Patch] P15 · AC14 da Story 2.6: falta o kicker** [`frontend/src/app/(site)/organizador/eventos/page.tsx:78-80`]
      O `EXPERIENCE.md#Vazio` pede "kicker em versalete, frase, fim". As duas seções
      têm kicker; o cabeçalho da página não — e é justamente ele que aparece quando a
      lista está vazia e nenhuma seção é renderizada. A tela irmã (`publicar`) tem.
- [x] **[Review][Patch] P16 · `aoEnviar` sem guarda de reentrada** [`frontend/src/components/FormularioPublicacao.tsx:156`]
      Falta `if (enviando) return;`. O `disabled={enviando}` cobre a maior parte,
      mas `Enter` mantido pressionado num campo de texto dispara envios repetidos.
      Sem chave de idempotência e sem tela de apagar evento, a duplicata é
      permanente. Uma linha.

## `defer` — real, mas não agora

Também registrados em `deferred-work.md`.

- [x] **[Review][Defer] Catálogo fora do ar impede publicar** [`frontend/src/app/(site)/organizador/publicar/page.tsx:71-82`] — `escolhido` só existe se a busca voltou `ok`, então recarregar a página com a Discovery fora derruba o formulário inteiro. Contradiz o docstring de `api/organizador.py:160` ("publicar não pode depender de a Discovery estar no ar") — que está certo sobre a **rota**; quem depende é a tela. Conserto real é persistir o item escolhido na URL, e isso é redesenho do passo 2
- [x] **[Review][Defer] O teste da chave não cobre `__cause__`** [`backend/tests/test_ticketmaster.py:197`] — `raise _catalogo_indisponivel() from erro` encadeia o `HTTPStatusError`, cujo `str()` contém a URL com `apikey=`. Hoje não vaza (o handler de `ErroDeDominio` não loga, verificado em `main.py:64-67`), mas o teste ficaria verde se alguém trocasse por `logger.exception`. Fechar exige escolher entre perder a cadeia de depuração (`from None`) e sanear a mensagem — decisão, não patch
- [x] **[Review][Defer] `test_publicar_nao_chama_a_ticketmaster` mocka a indireção, não o transporte** [`backend/tests/test_organizador_eventos.py:266`] — substitui `_criar_cliente`. Uma chamada por outro caminho (`httpx.get` direto, `requests`) passaria verde e iria à rede de verdade. A barreira forte é `MockTransport` global ou `pytest-socket`
- [x] **[Review][Defer] `GET /organizador/portarias` entrega nome e e-mail de toda a portaria do sistema** [`backend/app/services/evento.py:176`] — decisão registrada no docstring e no README, mas continua PII sem escopo, sem paginação e sem limite de taxa, varrível por qualquer organizador
- [x] **[Review][Defer] `listar_do_organizador` não filtra `publicado_em IS NOT NULL`** [`backend/app/services/evento.py:222`] — o modelo declara que `NULL` é rascunho. Nenhum caminho cria rascunho hoje; no dia em que a Epic 3 depender de "não publicado não aparece", esta tela já está do lado errado da regra
- [x] **[Review][Defer] A justificativa do `commit()` sem `try/except` está incompleta** [`backend/app/services/evento.py:170`] — o docstring diz que as violações "chegam todas do mesmo corpo, sem ninguém concorrendo". Esquece a FK `evento_portaria.usuario_id`, que aponta para outra linha de outro dono. Janela teórica hoje (não existe rota de apagar usuário), mas é a justificativa escrita que vai autorizar o próximo autor a não tratar nada
- [x] **[Review][Defer] `atracao` atravessa todo o contrato e ninguém usa** [`backend/app/schemas/catalogo.py:14`] — declarada, preenchida, tipada no frontend, com teste dedicado, e lida por nenhuma tela e nenhuma coluna. A Epic 3 pode consumi-la; até lá é um sexto do contrato do catálogo parecendo servir para alguma coisa

## Descartados (11)

`AC6 da 2.1` e `AC7 da 2.2` — desvios substituídos por escrito antes de a story
fechar · `router do catálogo pula services` — decisão registrada no README com
alternativa descartada, e o `ARCHITECTURE-SPINE.md` é artefato de planejamento
congelado, que o `CLAUDE.md` proíbe reescrever para casar com o código ·
`origem_externa_id não é verificado contra o catálogo` — o AD-1 proíbe
justamente a consulta viva · `eventos órfãos sem portaria` — nada em produção ·
`NUL em texto` — inalcançável pela interface · `voltar` fixo no detalhe ·
`momentoDaPublicacao` sem ano · comentário do `scroll-behavior` em `globals.css` ·
docstring desatualizado em `test_evento.py` · bloco "Setores" sem estado vazio no
detalhe.
