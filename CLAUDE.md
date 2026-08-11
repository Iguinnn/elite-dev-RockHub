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

### Os READMEs são atualizados ao fim de toda story — obrigatório

Terminou uma story, **antes de considerá-la concluída**, atualize os três READMEs:

- `README.md` (raiz) — visão geral da aplicação
- `frontend/README.md`
- `backend/README.md`

Cada um recebe o que mudou na sua camada: o que foi implementado, o que mudou de decisão, o
histórico e **o porquê** — não só o que, sempre o motivo.

**O `README.md` da raiz é o histórico de decisões do projeto.** Não é changelog de funcionalidade:
é o registro de *por que isso e não aquilo*. Toda decisão relevante entra com três partes:

1. **O que foi decidido**
2. **Por quê** — o problema que essa escolha resolve
3. **O que foi descartado, e por quê não** — a alternativa considerada e o motivo de ter caído

A terceira parte é a que o desafio avalia e a que quase todo mundo esquece. Uma decisão sem
alternativa descartada parece que não houve escolha — que é exatamente a acusação de "AI slop".

Matéria-prima pronta para isso: os `.memlog.md` do brainstorming, da arquitetura e do UX registram,
em ordem, tudo que foi considerado e recusado ao longo do processo.

Os READMEs de `frontend/` e `backend/` ficam com o que é específico da camada: como rodar, estrutura
de pastas, convenções e decisões locais.

**Mas README não é só explicação.** A parte operacional vem primeiro, porque é o que alguém precisa
em dez segundos. Estrutura do `README.md` da raiz, nesta ordem:

1. **O que é** — dois parágrafos
2. **Como executar** — pré-requisitos, variáveis de ambiente, subir o banco, migrar, semear, rodar
   backend, rodar frontend. Comandos copiáveis, sem passo implícito
3. **Contas semeadas** — os quatro usuários e suas senhas
4. **Roteiro de avaliação** — o caminho de ponta a ponta, numerado, incluindo como provocar a
   recusa de pagamento
5. **Stack e estrutura** — o que é cada pasta
6. **Decisões: por que isso e não aquilo** — o histórico, com alternativas descartadas
7. **O que não está pronto** — limitações assumidas

**Construção incremental, revisão no fim.** As seções 1 a 5 nascem e crescem junto com o código:
a story que adiciona migração adiciona o comando de migração no mesmo commit; a que cria o seed
documenta as credenciais ali. A seção 6 ganha uma entrada sempre que uma decisão é tomada, enquanto
o motivo ainda está fresco.

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
   Versão em linguagem de gente para o README: `docs/decisoes-tecnicas.md`
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

**As duas metades estão no ar:** frontend em <https://elite-dev-rock-hub.vercel.app> (Vercel)
e API + PostgreSQL em <https://elite-dev-rockhub-production.up.railway.app> (Railway), **os dois
publicando a `main`** desde o merge da Epic 1. Da Epic 2 em diante o fluxo é: branch da epic →
code review → merge na `main` → deploy automático. Nenhum campo de painel precisa ser tocado de
novo — nem `Root Directory`, nem Production Branch, nem variável de ambiente (a
`TICKETMASTER_API_KEY` já está definida na Railway desde a 1.8, só falta a `Settings` declará-la
na Story 2.1).

O que existe hoje: backend FastAPI com migração Alembic e a tabela `usuario`; cadastro, login,
logout e `/auth/eu` com senha em Argon2id e sessão em cookie `httpOnly` de 8h; autorização por
papel como dependência de rota; seed das quatro contas de avaliação; frontend Next.js com a
identidade "jornal noturno" aplicada, telas de acesso, `/conta` protegida e masthead que reage
à sessão.

**Próximo passo: Epic 2** — publicação de eventos pelo organizador, começando pela Story 2.1
(cliente da Ticketmaster com a chave protegida). O `sprint-status.yaml` é a fonte da verdade
sobre o andamento — consulte-o antes de assumir o que está pronto.

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
