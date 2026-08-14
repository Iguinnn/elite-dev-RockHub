# elite-dev-RockHub

Plataforma de Eventos e Ingressos — resposta ao **Desafio Elite Dev** da Verzel.
Requisitos completos em [docs/desafio-elite-dev.md](docs/desafio-elite-dev.md). Prazo: 7 dias corridos.

## Como trabalhamos neste projeto

### Git é responsabilidade do Igor
**Nunca execute comandos git.** Nada de `git add`, `commit`, `branch`, `merge`, `push` — nem
`git status` ou `git diff`. O Igor conduz todo o versionamento manualmente, de propósito: o
histórico de commits é parte da avaliação e precisa refletir o processo dele.

Se precisar saber o estado dos arquivos, use ferramentas de leitura (Read, Glob, Grep) ou pergunte.

### As decisões são do Igor — não decida por ele
Agentes existem aqui para **produzir specs e escrever código**, ganhando tempo de execução.
Não para escolher o rumo do produto.

Não decida por conta própria: stack, bibliotecas, modelagem de domínio, escopo, identidade
visual, o que entra ou sai. Quando faltar uma definição, **pergunte** — a menos que o Igor peça
explicitamente uma recomendação, e aí opine de forma direta.

**Por quê:** o desafio avalia justamente as decisões dele e o raciocínio por trás delas
("por que a tela é assim e não de outro jeito"). Decisão tomada pela IA sem ele escolher é
exatamente o "AI slop" que o enunciado penaliza.

Apresentar trade-offs, alternativas e consequências é bem-vindo. Escolher no lugar dele, não.

### Techspec no lugar de story — decidido em 2026-08-12

Da Story 3.7 em diante eu não escrevo mais arquivo de story. Escrevo uma **techspec que cobre um
grupo de stories**, no formato de [docs/techspec-filtro-do-catalogo.md](docs/techspec-filtro-do-catalogo.md),
e implemento a partir dela, **em outra sessão**. As specs moram em `docs/techspec-<assunto>.md`.

**Por quê:** medi o ritmo pelos arquivos da Epic 3 — ~73 min por story, ponta a ponta. As stories
tinham entre 8,6 e 11,4 mil palavras; a techspec do filtro do catálogo resolveu trabalho equivalente
com 2 mil. Sobram 13 stories de código e cerca de três dias de prazo. Cortando o arquivo de 10 mil
palavras e a redação de README a cada commit, o ciclo cai para ~45 min. O que isso **não** corta é a
conversa das decisões — ela é exatamente o que está sendo avaliado, e continua acontecendo inteira.

**O que descartei:** fechar a Epic 3 no formato antigo e trocar só na Epic 4. Caiu porque 3.7, 3.8 e
3.9 são as mais pesadas que sobraram — esperar seria abrir mão da economia justo onde ela é maior.

**Agrupe por transação ou invariante compartilhada, não "de três em três".** 3.7+3.8+3.9 são uma
techspec só porque os próprios ACs do `epics.md` as costuram na mesma função `pagar_reserva`: a
expiração da 3.7 dispara dentro da rota que a 3.8 cria, e a emissão da 3.9 acontece na mesma
transação da transição para `PAGA`. Especificar isso em três documentos deixaria as decisões de
fronteira caindo no vão entre eles. Os outros grupos naturais: 4.1+4.2 (leitura), 4.3+4.4 (o link
revogável), 5.2+5.3+5.5 (um endpoint de validação, três formas de entrada).

**A spec agrupa; o commit continua um por story.** Cada bloco de critérios de pronto da spec é o
gate de um commit, e o `sprint-status.yaml` continua marcando story a story. O histórico do git é
parte da avaliação e não muda de granularidade.

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para o Igor commitar** — sem escrever README, sem tocar no próximo. Só emende
o seguinte depois que ele mandar. **Uma spec cobrir três stories não autoriza implementá-las de uma
vez**: a tentação é exatamente essa, porque o documento é um só, e ceder a ela custa o commit por
story — a única coisa que a spec agrupada não pode custar. Esta regra vale para toda techspec, e
cada spec nova a repete logo abaixo da tabela de commits.

**Seis seções, teto de ~2.500 palavras por spec:**

1. **Escopo e commits** — quais commits saem daqui
2. **O que existe hoje** — curto, só o que a spec assume pronto
3. **Decisões, com a alternativa descartada** — a parte avaliada, a única que não pode encolher
4. **Contrato** — rotas, schemas, códigos de erro, migrações
5. **Critérios de pronto, por commit** — é o que o `bmad-code-review` lê no lugar dos ACs
6. **Armadilhas** — os ⚠️ que antes moravam nos comentários do `sprint-status.yaml`

Fica de fora o que a story tinha e ninguém lia: contexto reexplicado, tarefas numeradas, Dev Agent
Record, referências cruzadas ao planejamento, seção de testes narrada.

**Sempre em dois passos, e o segundo termina na spec.** Passo 1: leia os ACs do `epics.md`, os ADs
vinculantes e o código que já existe, e volte **só com a lista de decisões em aberto** — cada uma com
as opções, a consequência de cada lado e sua leitura. Nada de spec ainda. Passo 2, depois que eu
responder: a spec com as respostas dentro — **e para aí**. Despejar dez decisões no fim de um
documento pronto é como se perde a qualidade que o formato longo garantia.

⚠️ **Escrever a spec não é autorização para implementar.** A sessão que produz a techspec entrega o
arquivo e para; quem codifica é **outra sessão**, que recebe a spec pronta como entrada. É a divisão
de modelos logo abaixo (Opus especifica, Sonnet implementa) e é o que mantém o passo 1 valendo
alguma coisa — quem acabou de decidir dez coisas sozinho é o pior revisor delas. Se eu quiser que a
mesma sessão emende o código, eu mando; sem isso, entregue a spec e pergunte.

**Este formato vence o template de qualquer skill.** Se a sessão começar por `bmad-spec`,
`bmad-quick-dev` ou outra, é a skill que se adapta a estas seis seções — nunca o contrário.

**A spec é escrita antes do código.** Spec redigida depois de implementar é memória com outro nome,
e aí a economia vira prejuízo: o porquê fresco era o único motivo de o formato antigo existir.

### Os READMEs — escrita adiada, com uma exceção

**Desde 2026-08-12 eu não escrevo README a cada commit.** Quem registra a decisão e o porquê
enquanto estão frescos é a techspec do grupo (seção acima); a passagem final da Epic 6 transcreve
dali para os READMEs. Não pare no meio de um grupo de stories para escrever README.

**A exceção, e é só uma:** `README.md#o-que-não-está-pronto` continua sendo escrito **na hora**.
É o único requisito do enunciado com penalidade escrita, e o jeito de falhar nele é esquecer — corte
consciente que ninguém anotou vira lacuna não declarada, que é justamente o caso penalizado. Uma
linha custa trinta segundos.

O resto desta seção é **material da Epic 6** — não abra durante a implementação. Está aqui só para
a passagem final não precisar redescobrir as réguas.

**A régua da raiz:** entra na seção *Decisões* se, tivesse eu escolhido a alternativa, quem avalia
veria **um sistema diferente**. Não entra: detalhe de UI, nome de componente, ordem de campo,
biblioteca menor, bug corrigido, decisão de processo. Cada decisão que entra tem três partes — **o
que foi decidido**, **por quê**, e **o que foi descartado e por quê não**. A terceira é a que o
desafio avalia: decisão sem alternativa descartada parece que não houve escolha, que é exatamente a
acusação de "AI slop". Matéria-prima pronta: as techspecs em `docs/` e os `.memlog.md` do
brainstorming, da arquitetura e do UX.

**A régua da camada: no máximo cinco parágrafos por assunto**, na seção temática que já existe
(`## Publicar evento`, `## O sistema visual`). Sem tabela nova, sem subseção nova, sem "a lição que
fica", e **sem recriar `## Histórico desta camada`** — ela foi removida em 2026-08-11 por ser
duplicata literal das seções temáticas do mesmo arquivo.

**Por que as duas réguas existem:** os três READMEs chegaram a 5.093 linhas e 54 mil palavras, com
a mesma decisão escrita quatro vezes. Ninguém lê 1.900 linhas, e 66 subseções de decisão enterram as
20 que importam — inclusive *O que não está pronto*. Um README que não é lido não pontua.

Estrutura do `README.md` da raiz, nesta ordem:

1. **O que é** — dois parágrafos
2. **No ar** — as URLs publicadas (vale +1 ponto no enunciado)
3. **Como executar** — pré-requisitos, variáveis de ambiente, subir o banco, migrar, semear, rodar
   backend, rodar frontend. Comandos copiáveis, sem passo implícito
4. **Contas semeadas** — os cinco usuários e suas senhas
5. **Roteiro de avaliação** — o caminho de ponta a ponta, numerado, incluindo como provocar a
   recusa de pagamento
6. **Stack e estrutura** — o que é cada pasta
7. **Decisões: por que isso e não aquilo** — só as que passam na régua, com alternativas descartadas
8. **O que não está pronto** — cortes conscientes. **Obrigatória**, e não some no fim do projeto: o
   enunciado exige que o que não estiver pronto seja dito, e mapa de assentos, TMDb, editar evento,
   cancelamento e teste de frontend continuam fora por escolha
9. **Uso de IA** — ferramentas, onde entraram, e o que foi feito sem IA. O enunciado pede

Estrutura dos READMEs de camada: como rodar, variáveis, estrutura de pastas, convenções, seções
temáticas por assunto, armadilhas reais e deploy. Sem linha do tempo.

**De onde sai cada parte na passagem final:** as seções 1 a 6 saem de rodar o projeto numa máquina
limpa — comandos, variáveis, contas e roteiro se conferem, não se lembram. A seção 7 sai das
techspecs, que já registraram cada decisão com a alternativa descartada enquanto o motivo estava
fresco. **É essa transferência que sustenta o corte de tempo:** se uma spec não registrar a decisão
na hora, a passagem final vira redação de memória e perde exatamente a parte avaliada.

**Escreva em primeira pessoa, como se fosse o Igor escrevendo.** "Usei o X porque…", "decidi trocar
Y por Z quando percebi que…". Nunca terceira pessoa, nunca voz de documentação gerada. Vale também
para as techspecs.

### Ritmo de trabalho: branch por epic, review por epic

- **Uma branch por epic** — o Igor cria, faz merge e gerencia. Você nunca roda comando git
- **Um commit por story** — as stories foram dimensionadas exatamente para isso, e isso não muda
  com a techspec: uma spec de três stories produz três commits
- **Code review ao fim de cada epic**, não a cada story. Rodar `bmad-code-review` 38 vezes não
  cabe no prazo; ao fim de cada epic o retorno é melhor, porque o revisor vê o conjunto

Ao terminar cada story, rode a suíte, mostre o resultado e avise que está pronta para commit —
sem escrever README (ver *Techspec no lugar de story*). Não emende a próxima sem o Igor mandar.

### Divisão de modelos
- **Opus** — planejamento, brainstorm, PRD, arquitetura, techspecs, epics e stories
- **Sonnet** — implementação de código

### Fluxo BMAD
BMAD Method v6.10.0 instalado, configurado em português (`_bmad/core/config.yaml`).
Artefatos saem em `_bmad-output/`.

Sequência (comprimida por causa do prazo — PRD foi cortado de propósito):
1. ~~`bmad-brainstorming`~~ ✅ **concluído** — resultado em
   `_bmad-output/brainstorming/brainstorm-plataforma-eventos-ingressos-2026-08-08/`
   (`brainstorm-intent.md` é o destilado; `.memlog.md` é a sessão completa)
2. ~~`bmad-prd`~~ — **pulado**. O PDF do desafio já é a especificação; um PRD só reescreveria
   `docs/desafio-elite-dev.md` com outras palavras
3. ~~`bmad-architecture`~~ ✅ **concluído** — `_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md`
   contém 14 decisões (AD-1 a AD-14). **São vinculantes** — código que as contraria está errado.
   Saiu junto um `docs/decisoes-tecnicas.md`, **apagado em 2026-08-14** (ver *Documentos congelados*
   abaixo)
3b. ~~`bmad-ux`~~ ✅ **concluído** — `_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/`
   `DESIGN.md` (identidade "jornal noturno") + `EXPERIENCE.md` (comportamento) +
   `mockups/proto-jornal-noturno.html` (protótipo navegável de 11 telas).
   **Leia a seção "Como usar este documento" antes de mexer em tela** — separa o que é duradouro
   do que o Igor vai ajustar livremente durante a codificação
4. ~~`bmad-create-epics-and-stories`~~ ✅ **concluído** — `_bmad-output/planning-artifacts/epics.md`
   com 6 epics e 38 stories, uma por commit. Cobertura validada: 16/16 FRs e 11/11 UX-DRs
5. ~~`bmad-sprint-planning`~~ ✅ **concluído** — `_bmad-output/implementation-artifacts/sprint-status.yaml`
6. `bmad-dev-story` — implementou as stories 1.1 a 3.6, uma a uma. **Encerrado em 2026-08-12**
7. **Techspec por grupo de stories** ← **em andamento** desde a 3.7. Ver *Techspec no lugar de
   story*. As specs saem em `docs/`, fora do `_bmad-output/`, seguindo o precedente do filtro do
   catálogo

## Estado atual

**Epic 1 concluída e revisada.** As nove stories (1.1 a 1.9) estão implementadas, e o
`bmad-code-review` da epic inteira rodou em 2026-08-11 — sem nenhum achado bloqueante.
As correções do review já estão aplicadas; a mais relevante está registrada como decisão
no README da raiz.

**Epic 2 concluída e revisada.** As seis stories (2.1 a 2.6) — cliente da Ticketmaster, busca no
catálogo, modelo de evento e setor, publicação com setores, escala da portaria e `Meus eventos`.
Fora da numeração, um commit `feat` avulso acrescentou o filtro de classificação do catálogo
(spec em `docs/techspec-filtro-do-catalogo.md`). O `bmad-code-review` rodou em 2026-08-11: 16
patches aplicados, 7 adiados (`deferred-work.md`), 11 descartados; a suíte foi de 203 para 218.

**Epic 3 concluída, revisada e no ar.** As nove stories (3.1 a 3.9) — programação pública, busca e
filtros, chamada principal, página do evento com setores, modelo de reserva, a reserva com `UPDATE`
condicional do AD-3, e as três últimas pela primeira techspec agrupada do projeto (expiração
preguiçosa, pagamento com recusa e emissão de ingresso, todas convergindo na função `pagar`).

O `bmad-code-review` da epic rodou em 2026-08-12, no primeiro formato de **três camadas × três
grupos** — nove subagentes, com o diff recortado por fronteira de transação em vez de por tamanho.
Saldo: 7 decisões, 31 patches aplicados, 18 adiados, 9 descartados; a suíte foi de 379 para 395.
Achados em `code-review-epic-3.md`, adiados em `deferred-work.md`.

⚠️ **A lição que vale para as próximas epics:** os três achados de alta eram **invisíveis para a
suíte**, e o pior deles porque a fixture de teste divergia da sessão de produção
(`expire_on_commit`). Teste que não imita produção esconde exatamente a classe de bug que ele
deveria pegar — a regra ficou escrita no docstring da fixture `sessao` do `conftest.py`.

Fora da numeração das stories, dois ajustes entraram depois do review: a marca virou o lettering
próprio (`public/logotipo-rockhub.png` e `src/app/icon.png`, que substituiu o `icon.svg`), e o
checkout ganhou uma tela de espera de 6s com pontinhos — **a única animação do produto**, exceção
pedida pelo Igor contra o `EXPERIENCE.md#Carregando` e registrada nos dois arquivos que a
implementam.

⚠️ **A `TICKET_SIGNING_SECRET` na Railway derruba o deploy se estiver errada.** A Story 3.9 passou a
lê-la e a validá-la, e o code review **endureceu o validador**: além do valor de exemplo, ele agora
recusa a variável vazia, só com espaço, ou com menos de 32 caracteres. O campo apagado num painel de
deploy era o buraco mais fácil de acontecer e passava batido, porque string vazia não é a string de
exemplo. Em qualquer um dos casos a aplicação **recusa subir**, e o mesmo vale para o `JWT_SECRET`.
Se o deploy da `main` falhar na inicialização, é o primeiro lugar a olhar. O `CREATE EXTENSION
unaccent` da 3.2 **já foi conferido** em 2026-08-11 (usuário `postgres`, `usesuper = true`, extensão
criada à mão pelo painel); o registro está no docstring da própria migração, e não há o que refazer.

**As duas metades estão no ar:** frontend em <https://elite-dev-rock-hub.vercel.app> (Vercel)
e API + PostgreSQL em <https://elite-dev-rockhub-production.up.railway.app> (Railway), **os dois
publicando a `main`** desde o merge da Epic 1. Da Epic 2 em diante o fluxo é: branch da epic →
code review → merge na `main` → deploy automático. Nenhum campo de painel precisa ser tocado de
novo — nem `Root Directory`, nem Production Branch, nem variável de ambiente (a
`TICKETMASTER_API_KEY` já está definida na Railway desde a 1.8, só falta a `Settings` declará-la
na Story 2.1).

O que existe hoje: backend FastAPI com Alembic e as tabelas `usuario`, `evento`, `setor`,
`evento_portaria`, `reserva` e `item_reserva`; cadastro, login, logout e `/auth/eu` com senha em
Argon2id e sessão em cookie `httpOnly` de 8h; autorização por papel como dependência de rota;
integração com a Ticketmaster Discovery; publicação de evento com setores e escala de portaria na
mesma transação; `Meus eventos` com lista e detalhe; as quatro rotas públicas de `publico.py`
(`GET /eventos`, `/eventos/cidades`, `/eventos/destaque`, `/eventos/{id}`); `POST /reservas` e
`GET /reservas/{id}` em `cliente.py`; seed das cinco contas de avaliação; frontend Next.js com a
identidade "jornal noturno" aplicada, telas de acesso, `/conta` protegida, `/organizador/publicar`,
`/organizador/eventos`, a programação na raiz com busca e filtros, `/eventos/{id}` e `/reservas/{id}`
com o cronômetro, e masthead que reage à sessão e ao papel.

**Próximo passo: a techspec de 4.1+4.2** — `Meus ingressos` e o canhoto com o QR, que são o grupo de
leitura previsto na seção *Techspec no lugar de story*. Depois dela, 4.3+4.4 (o link revogável).
Sobram **14 stories**: 4 na Epic 4, 6 na Epic 5 e 4 na Epic 6, sendo estas últimas de documentação.

Duas coisas da Epic 3 que a Epic 5 vai encontrar, e que já estão resolvidas para não custarem
descoberta: **o AD-5 foi reescrito** — a promessa de recusar assinatura divergente "sem consultar o
banco" não se sustenta com o `nonce` na fórmula, porque o QR carrega só `ID.ASSINATURA` e o `nonce`
mora na coluna; a garantia real, e a que a Story 5.2 pode invocar, é o **recálculo**. E o
`conferir_codigo` **já tem a guarda de não-ASCII** que a portaria precisa: sem ela, um QR que
decodifique com acento virava `500` na fila da porta.

O `sprint-status.yaml` é a fonte da verdade sobre o andamento — consulte-o antes de assumir o que
está pronto.

### Documentos congelados — não atualize

Estes existem, continuam versionados e **não recebem mais manutenção**. Não os edite ao terminar
uma story, e não os cite como se estivessem em dia:

- ~~**`docs/decisoes-tecnicas.md`**~~ — **apagado em 2026-08-14, na Epic 6.** Era rascunho da fase de
  arquitetura e descrevia em tempo presente coisas que só existiram depois; congelá-lo em 2026-08-11
  não bastou, porque documento congelado ainda é documento que alguém abre e acredita. O raciocínio
  do dia do planejamento continua inteiro em `ARCHITECTURE-SPINE.md` e nos `.memlog.md`, e as
  decisões vivas — com a alternativa descartada de cada uma — moram no `README.md` da raiz. O git
  guarda o arquivo se ele fizer falta
- **`_bmad-output/planning-artifacts/`** — brainstorm, arquitetura, UX e `epics.md` são artefatos de
  **planejamento**, escritos antes da implementação. Eles registram o plano como ele foi feito; não
  os reescreva para casar com o que o código virou
- **Arquivos de story já implementados** — o `Dev Agent Record` é preenchido pela story em
  andamento e não se volta nela depois

## Decisões já travadas

Ticketmaster Discovery (só ela) · setores por quantidade, sem mapa de assentos ·
FastAPI + PostgreSQL · Next.js · Vercel (front) + Railway (back e banco).

**Diferenciação é estrutural, não visual** — detalhes e anti-padrões visuais em
`brainstorm-intent.md`. Leia esse arquivo antes de propor qualquer tela.

### Versionamento de artefatos
- `_bmad-output/` **é versionado** — PRD, epics, stories e brainstorm são artefatos produzidos
  pelo Igor, e o desafio pede explicitamente que sejam commitados
- `_bmad/` e `.claude/skills/` são **ignorados** — framework instalado, reproduzível com
  `npx bmad-method install`. Commitá-los enterraria o PRD em ~250 arquivos de ruído

## Decisões em aberto

Nenhuma das grandes. Stack, banco, modelo de venda, API externa e identidade visual foram
todas decididas no brainstorm e na arquitetura, e estão implementadas — o histórico de cada
uma, **com a alternativa descartada**, está em `README.md#decisões-por-que-isso-e-não-aquilo`.

O que continua em aberto são escolhas das epics que ainda não começaram, e elas se decidem
quando a story chegar. O que **não** está pronto e é corte consciente está na tabela
`README.md#o-que-não-está-pronto`, com o motivo de cada um.

## Estrutura

```
backend/    # API
frontend/   # React
docs/       # documentação do projeto
docs/techspec-*.md          # as specs da 3.7 em diante
_bmad-output/
  planning-artifacts/       # PRD, arquitetura, epics
  implementation-artifacts/ # stories 1.1 a 3.6, sprint-status, code reviews
```

## Pendências técnicas

- **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** O arquivo nasceu do
  template Python do GitHub, que assume que a raiz do repositório é o projeto Python. Aqui ela
  não é, e padrão sem barra inicial casa em qualquer profundidade — foi assim que `lib/` engoliu
  `frontend/src/lib/` desde a Story 1.2 e derrubou o primeiro build da Vercel na 1.9. Todos os
  padrões de empacotamento e build já foram ancorados no code review da Epic 1; **mantenha a
  regra** ao acrescentar qualquer um novo. Ficaram sem âncora de propósito os de cache e
  virtualenv (`__pycache__/`, `.venv`, `node_modules/`, `env/`, `venv/`): eles nascem em
  profundidade e nenhum é nome plausível de pasta de código.
- **Nenhuma verificação local pega arquivo que nunca entrou no repositório.** `npm run build`,
  `tsc --noEmit` e a suíte do backend leem o disco, não o índice do git. Só um clone limpo
  revela — e o primeiro clone limpo deste projeto foi o da Vercel.
- **Story que cria migração precisa de `uv run alembic upgrade head` no banco de desenvolvimento,
  e a suíte não avisa que faltou.** O `conftest.py` migra o `rockhub_teste` sozinho (`downgrade
  base` + `upgrade head`) a cada sessão, então 379 testes passam com o `rockhub` — o banco que o
  `uvicorn` usa — uma revisão atrás. O sintoma não parece migração: a tela mostra a frase genérica
  de erro, porque um `INSERT` em tabela inexistente vira `500` → `ERRO_INTERNO`, que nenhuma tela
  traduz. Aconteceu na Story 3.9, com a tabela `ingresso`. **Rode o `upgrade head` no mesmo passo
  em que a migração é criada**, e confira com `uv run alembic current` contra `alembic heads`. A
  causa real aparece inteira no log do `uvicorn` — é o primeiro lugar a olhar quando a tela diz
  "tente de novo em instantes".
- `uv` instalado em `C:\Users\Asus\.local\bin` (necessário para os scripts Python do BMAD)
- **Docker Desktop precisa estar no ar** para `uv run pytest`: a suíte roda contra o Postgres
  real desde a Story 1.3. Sem ele, só os testes de `/saude`, erros, config e segurança passam.
