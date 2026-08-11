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

### Os READMEs — só a camada que a story tocou, e só o que passa na régua

Terminou uma story, **antes de considerá-la concluída**, atualize **o README da camada que a story
tocou**. Story que só mexe no backend não encosta no `frontend/README.md`. Se nenhum arquivo daquela
camada mudou, não há o que escrever ali.

O `README.md` da raiz só é tocado quando a story produz uma **decisão que muda o produto ou a
arquitetura** — o que é raro, e deve continuar raro.

**A régua da raiz, aplicada em 2026-08-11:** entra na seção *Decisões* se, tivesse eu escolhido a
alternativa, quem avalia veria **um sistema diferente**. Não entra: detalhe de UI, nome de
componente, ordem de campo, escolha de biblioteca menor, bug corrigido, decisão de processo. Essas
moram no README da camada, ao lado do código que elas afetam — ou em lugar nenhum.

**Por que a régua existe:** os três READMEs chegaram a 5.093 linhas e 54 mil palavras, com a mesma
decisão escrita três e quatro vezes (raiz + seção temática da camada + histórico da camada + notas
da story). Ninguém lê 1.900 linhas de README, e 66 subseções de decisão enterram as 20 que importam
— inclusive *O que não está pronto*, que é o único requisito do enunciado com penalidade escrita.
Um README que não é lido não pontua, por melhor que seja.

Cada decisão que passa na régua entra com três partes:

1. **O que foi decidido**
2. **Por quê** — o problema que essa escolha resolve
3. **O que foi descartado, e por quê não** — a alternativa considerada e o motivo de ter caído

A terceira parte é a que o desafio avalia e a que quase todo mundo esquece. Uma decisão sem
alternativa descartada parece que não houve escolha — que é exatamente a acusação de "AI slop".

Matéria-prima pronta para isso: os `.memlog.md` do brainstorming, da arquitetura e do UX registram,
em ordem, tudo que foi considerado e recusado ao longo do processo.

**Não existe mais seção `## Histórico desta camada`.** Ela foi removida dos dois READMEs de camada
em 2026-08-11: era duplicata literal das seções temáticas do mesmo arquivo. O que a story mudou vai
para a seção temática do assunto (`## Publicar evento`, `## O sistema visual`), não para uma linha
do tempo paralela. Não recrie a seção.

**Mas README não é só explicação.** A parte operacional vem primeiro, porque é o que alguém precisa
em dez segundos. Estrutura do `README.md` da raiz, nesta ordem:

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

**Construção incremental, revisão no fim.** As seções 1 a 6 nascem e crescem junto com o código:
a story que adiciona migração adiciona o comando de migração no mesmo commit; a que cria o seed
documenta as credenciais ali. A seção 7 ganha uma entrada quando — e só quando — uma decisão passa
na régua, enquanto o motivo ainda está fresco.

As stories da Epic 6 **não escrevem o README do zero** — elas fazem a passagem final: conferir se o
passo a passo realmente funciona numa máquina limpa, ordenar o histórico, fechar as lacunas.

Nunca deixe documentação acumulada para o fim: motivo escrito de memória, três dias depois, perde
exatamente a parte que está sendo avaliada.

**Escreva em primeira pessoa, como se fosse o Igor escrevendo.** "Usei o X porque…", "fiz assim
para…", "decidi trocar Y por Z quando percebi que…". Nunca terceira pessoa, nunca voz de
documentação gerada.

**Por quê:** o desafio avalia documentação clara e o raciocínio por trás das escolhas, e o README
é lido antes do código. Documentação escrita no fim, de memória, perde exatamente o "porquê" —
que é a parte avaliada.

Isto é uma regra permanente, não um pedido pontual. Vale para toda sessão, sem precisar ser
relembrada.

### Ritmo de trabalho: branch por epic, review por epic

- **Uma branch por epic** — o Igor cria, faz merge e gerencia. Você nunca roda comando git
- **Um commit por story** — as stories foram dimensionadas exatamente para isso
- **Code review ao fim de cada epic**, não a cada story. Rodar `bmad-code-review` 38 vezes não
  cabe no prazo; ao fim de cada epic o retorno é melhor, porque o revisor vê o conjunto

Ao terminar uma story, atualize os READMEs (regra acima) e avise que a story está pronta para
commit. Não emende a próxima story sem o Igor mandar.

### Divisão de modelos
- **Opus** — planejamento, brainstorm, PRD, arquitetura, specs, epics e stories
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
   Saiu junto `docs/decisoes-tecnicas.md`, hoje **congelado** (ver *Documentos congelados* abaixo)
3b. ~~`bmad-ux`~~ ✅ **concluído** — `_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/`
   `DESIGN.md` (identidade "jornal noturno") + `EXPERIENCE.md` (comportamento) +
   `mockups/proto-jornal-noturno.html` (protótipo navegável de 11 telas).
   **Leia a seção "Como usar este documento" antes de mexer em tela** — separa o que é duradouro
   do que o Igor vai ajustar livremente durante a codificação
4. ~~`bmad-create-epics-and-stories`~~ ✅ **concluído** — `_bmad-output/planning-artifacts/epics.md`
   com 6 epics e 38 stories, uma por commit. Cobertura validada: 16/16 FRs e 11/11 UX-DRs
5. ~~`bmad-sprint-planning`~~ ✅ **concluído** — `_bmad-output/implementation-artifacts/sprint-status.yaml`
6. `bmad-dev-story` — implementar story a story ← **em andamento**

## Estado atual

**Epic 1 concluída e revisada.** As nove stories (1.1 a 1.9) estão implementadas, e o
`bmad-code-review` da epic inteira rodou em 2026-08-11 — sem nenhum achado bloqueante.
As correções do review já estão aplicadas; a mais relevante está registrada como decisão
no README da raiz.

**Epic 2 com o código fechado.** As seis stories (2.1 a 2.6) estão implementadas — cliente da
Ticketmaster, busca no catálogo, modelo de evento e setor, publicação com setores, escala da
portaria e `Meus eventos`. Fora da numeração, um commit `feat` avulso acrescentou o filtro de
classificação do catálogo (spec em `docs/techspec-filtro-do-catalogo.md`). **Falta o
`bmad-code-review` da epic**, e é o próximo passo.

**As duas metades estão no ar:** frontend em <https://elite-dev-rock-hub.vercel.app> (Vercel)
e API + PostgreSQL em <https://elite-dev-rockhub-production.up.railway.app> (Railway), **os dois
publicando a `main`** desde o merge da Epic 1. Da Epic 2 em diante o fluxo é: branch da epic →
code review → merge na `main` → deploy automático. Nenhum campo de painel precisa ser tocado de
novo — nem `Root Directory`, nem Production Branch, nem variável de ambiente (a
`TICKETMASTER_API_KEY` já está definida na Railway desde a 1.8, só falta a `Settings` declará-la
na Story 2.1).

O que existe hoje: backend FastAPI com Alembic e as tabelas `usuario`, `evento`, `setor` e
`evento_portaria`; cadastro, login, logout e `/auth/eu` com senha em Argon2id e sessão em cookie
`httpOnly` de 8h; autorização por papel como dependência de rota; integração com a Ticketmaster
Discovery; publicação de evento com setores e escala de portaria na mesma transação; leitura de
`Meus eventos` com lista e detalhe; seed das cinco contas de avaliação; frontend Next.js com a
identidade "jornal noturno" aplicada, telas de acesso, `/conta` protegida, `/organizador/publicar`
e `/organizador/eventos`, e masthead que reage à sessão e ao papel.

**Próximo passo: code review da Epic 2**, e depois a Epic 3 (descoberta e compra). O
`sprint-status.yaml` é a fonte da verdade sobre o andamento — consulte-o antes de assumir o que
está pronto.

### Documentos congelados — não atualize

Estes existem, continuam versionados e **não recebem mais manutenção**. Não os edite ao terminar
uma story, e não os cite como se estivessem em dia:

- **`docs/decisoes-tecnicas.md`** — rascunho da fase de arquitetura. Descreve em tempo presente
  coisas que ainda não existem (reserva de 10 min, HMAC do QR, link de compartilhamento, cartão de
  teste). Congelado em 2026-08-11, com aviso no topo do próprio arquivo. As decisões vivas moram no
  `README.md` da raiz
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
_bmad-output/
  planning-artifacts/       # PRD, arquitetura, epics
  implementation-artifacts/ # stories
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
- `uv` instalado em `C:\Users\Asus\.local\bin` (necessário para os scripts Python do BMAD)
- **Docker Desktop precisa estar no ar** para `uv run pytest`: a suíte roda contra o Postgres
  real desde a Story 1.3. Sem ele, só os testes de `/saude`, erros, config e segurança passam.
