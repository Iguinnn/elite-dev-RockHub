# Uso de IA neste projeto

O enunciado do desafio pede três coisas: **quais ferramentas** foram usadas, **em que partes**, e
**o que foi feito sem IA**. Este arquivo responde às três.

## A resposta curta

Usei IA para **quebrar o projeto em epics e stories** e para **escrever o código**.

**Todas as decisões foram minhas:** arquitetura, banco, modelagem do domínio, identidade visual e de
interface, modelo de venda, recorte de escopo, o que entra e o que fica de fora, e o que eu descarto
e por quê.

## A ferramenta

**Claude Code**, com o **BMAD Method v6.10.0** instalado e configurado em português. O BMAD é um
framework de fluxo de trabalho para agentes: ele estrutura o caminho de brainstorm → arquitetura →
UX → epics → stories → implementação → code review, com um artefato por etapa.

Dividi por modelo, de propósito: **Opus** para planejamento, specs e revisão; **Sonnet** para
implementação de código. Planejar e implementar exigem coisas diferentes, e quem acabou de decidir
dez coisas sozinho é o pior revisor delas.
Em determinados momentos, usei o **Opus** para as duas coisas.

O `_bmad/` e o `.claude/skills/` **não** estão versionados: é framework instalado, reproduzível com
`npx bmad-method install`, e commitá-los enterraria os artefatos em ~250 arquivos de ruído. O que
está versionado é o que eu produzi com ele, em [`_bmad-output/`](../_bmad-output/).

### As skills que eu usei, na ordem

O BMAD instala 45 skills. Usei **dez**, nesta sequência — e a mais importante da lista é a que eu
pulei:

| # | Skill | O que produziu | Onde está |
|---|---|---|---|
| 1 | `bmad-brainstorming` | A sessão de ideação: o produto, o público, os anti-padrões visuais que eu queria evitar | [`_bmad-output/brainstorming/`](../_bmad-output/brainstorming/) — `brainstorm-intent.md` é o destilado, o `.memlog.md` é a sessão inteira |
| 2 | ~~`bmad-prd`~~ | **Pulado de propósito.** O PDF do desafio já é a especificação; um PRD só reescreveria o enunciado com outras palavras, e eu tinha sete dias | — |
| 3 | `bmad-architecture` | A espinha de arquitetura com **14 decisões vinculantes** (AD-1 a AD-14) — código que as contraria está errado | [`ARCHITECTURE-SPINE.md`](../_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md) |
| 4 | `bmad-ux` | `DESIGN.md` (a identidade "jornal noturno") + `EXPERIENCE.md` (comportamento) + um protótipo navegável de 11 telas em HTML | [`ux-designs/`](../_bmad-output/planning-artifacts/ux-designs/) |
| 5 | `bmad-create-epics-and-stories` | **6 epics com 38 stories**, cada uma dimensionada para virar exatamente um commit | [`epics.md`](../_bmad-output/planning-artifacts/epics.md) |
| 6 | `bmad-sprint-planning` | O rastreamento de andamento, que virou a fonte da verdade sobre o que está pronto | [`sprint-status.yaml`](../_bmad-output/implementation-artifacts/sprint-status.yaml) |
| 7 | `bmad-create-story` | Os arquivos de story detalhados, da 1.1 à 3.6 | [`implementation-artifacts/`](../_bmad-output/implementation-artifacts/) |
| 8 | `bmad-dev-story` | A implementação das stories 1.1 a 3.6, uma a uma | o código |
| 9 | `bmad-spec` e `bmad-quick-dev` | Da story 3.7 em diante: as **techspecs** por grupo de stories, e a implementação a partir delas | [`docs/techspec-*.md`](.) |
| 10 | `bmad-code-review` | A revisão adversarial ao fim de cada epic | `code-review-epic-*.md` |

⚠️ **A partir da story 3.7 eu troquei o formato, no meio do projeto.** Parei de usar
`bmad-create-story` e passei a escrever **techspecs** — um documento curto cobrindo um grupo de
stories, no lugar de um arquivo por story. O motivo foi medido, não sentido: as stories da Epic 3
tinham entre 8,6 e 11,4 mil palavras e levavam ~73 minutos ponta a ponta; a primeira techspec
resolveu trabalho equivalente com 2 mil palavras. Sobravam 13 stories de código e três dias.

**O que eu não cortei junto foi a conversa das decisões**, e isso é o ponto: a techspec tem uma
seção obrigatória de *"decisões, com a alternativa descartada"*, e ela é a única do documento que
não podia encolher. O que saiu foi o que ninguém lia — contexto reexplicado, tarefas numeradas,
referências cruzadas ao planejamento.

⚠️ **As skills se adaptaram ao meu formato, não o contrário.** Está escrito no
[`CLAUDE.md`](../CLAUDE.md): *"Este formato vence o template de qualquer skill."* Se uma sessão
começasse pelo `bmad-spec` ou pelo `bmad-quick-dev`, era a skill que se dobrava às minhas seis
seções. Aceitar o template de cada ferramenta teria produzido seis formatos diferentes de
documento em sete dias.

## Onde a IA entrou

### 1 · Quebrar o projeto em epics e stories

A partir do enunciado e das decisões que eu já tinha tomado, os agentes produziram **6 epics com 38
stories**, cada uma dimensionada para virar exatamente um commit, com critérios de aceite escritos
no formato Given/When/Then. Está em
[`_bmad-output/planning-artifacts/epics.md`](../_bmad-output/planning-artifacts/epics.md).

Isso é planejamento de execução — ordem, granularidade, o que depende do quê. Não é decisão de
produto: o que cada story faz saiu do que eu já tinha decidido nas etapas anteriores.

### 2 · Escrever o código

Story a story, a partir da spec. O agente lia os critérios de aceite, o código existente e as
decisões vinculantes de arquitetura, e implementava — backend, frontend, migrações e testes.

**Eu revisei e conduzi cada uma.** Quando o agente propôs algo que eu não tinha escolhido, foi
recusado. Vários exemplos disso estão registrados nos comentários do
[`sprint-status.yaml`](../_bmad-output/implementation-artifacts/sprint-status.yaml), que é onde eu
anotei o que foi decidido em cada story e o que foi descartado.

### 3 · Code review adversarial ao fim de cada epic

Rodei revisão em camadas paralelas ao fim de cada epic, não a cada story. Os achados e a triagem
estão em `_bmad-output/implementation-artifacts/code-review-epic-*.md`, com o que foi aplicado, o
que foi adiado e o que foi descartado — e **eu decidi cada um dos três destinos**.

Foi a parte em que a IA mais rendeu, e por um motivo específico: os achados que valeram eram todos
**invisíveis para a suíte de testes**. Um deles era uma divergência de configuração entre a sessão
de teste e a de produção, que fazia o pagamento responder certo nos testes e errado em produção.

⚠️ **E uma lição no sentido contrário:** um dos achados veio com uma justificativa que estava
errada. A camada afirmou que um token sequencial passaria em todos os testes; ao provar por mutação,
ela errava. O achado era real e o argumento não era. **Achado de revisor vale o que a mutação
provar** — passei a exigir isso.

### 4 · Redação da documentação

Essa sessão (4) foi escrita inteiramente por mim, Igor Duarte, justamente para mostrar que a checagem e leitura de todos os arquivos foram feitos de forma correta.

O resto deste arquivo e o `README.md` foram redigidos com IA a partir do que eu decidi e das specs que
registraram cada decisão enquanto o motivo estava fresco. A redação foi toda assistida para bater com o meu conteúdo de fato.

**Ao final eu revisei a documentação inteira, palavra por palavra.** Não foi apenas uma leitura por cima
para ver se "parecia bom": Conferi cada frase contra o que o sistema faz de verdade, e cortar o
que não passava. Valeu a pena porque a documentação gerada erra de um jeito específico, ela descreve
o que *deveria* estar lá e muitas das vezes o código não bate com a documentação. Citando um exemplo: o README anterior afirmava, no segundo parágrafo, que comprar e validar
"são as Epics 3 a 5" e ainda não existiam; as três estavam prontas havia dias. E dizia "as **cinco**
contas" em três lugares, com seis na tabela logo abaixo. Nenhum teste pega isso, e é a primeira
coisa que vocês (avaliadores) iriam ler.

## O que foi feito sem IA

**As decisões, todas.** É a parte que o desafio avalia, e é a parte que eu não terceirizei:

- **A stack** — FastAPI + PostgreSQL + Next.js, e a razão de separar backend de frontend em vez de
  usar Next full-stack
- **A modelagem do domínio** — evento com setores por quantidade em vez de mapa de assentos; a
  reserva com máquina de estados que segura estoque desde a criação; a portaria como escala de
  trabalho por evento, e não como nível de permissão
- **A identidade visual e toda a UI/UX** — o conceito de "jornal noturno", a paleta de duas tintas,
  a recusa de biblioteca de componentes, a lista de anti-padrões visuais que eu proibi, e o layout
  de cada tela. Inclusive as correções feitas com a tela na frente: o contador da portaria levou
  três formas até achar o lugar certo, e a casca da portaria nasceu com três saídas e nenhuma
  entrada — coisas que nenhuma suíte pega e que só a conferência visual acha
- **O recorte de escopo** — o que entra, o que fica de fora, e o que vai declarado em
  *O que não está pronto*
- **As alternativas descartadas** — cada decisão do README tem uma, e a escolha de qual caminho
  descartar foi minha

**O versionamento também.** Todo commit foi escrito e feito por mim, à mão, um por story. Nenhum
agente rodou comando `git` neste repositório em momento nenhum — é regra escrita no
[`CLAUDE.md`](../CLAUDE.md), porque o histórico faz parte da avaliação e precisa refletir o meu
processo.

## Como eu conduzi a ferramenta

Duas regras minhas moldaram o resultado, e as duas estão escritas no
[`CLAUDE.md`](../CLAUDE.md) do repositório, que é o arquivo de contexto que todo agente lê antes de
começar:

**1. "As decisões são do Igor — não decida por ele."** Quando faltava uma definição, o agente
tinha que **perguntar**, não escolher. Apresentar trade-offs e consequências era bem-vindo; escolher
no meu lugar, não. O motivo é direto: o desafio avalia justamente as decisões e o raciocínio por
trás delas, e decisão tomada pela IA sem eu escolher é exatamente o *AI slop* que o enunciado
penaliza.

**2. Spec antes do código, e em duas sessões diferentes.** A sessão que escrevia a techspec
entregava o arquivo e **parava**; outra sessão implementava a partir dele. São duas regras numa só.
A primeira: spec escrita depois de implementar é memória com outro nome, e o porquê fresco era
justamente o que eu queria preservar. A segunda: quem acabou de decidir dez coisas sozinho é o pior
revisor delas — separar as sessões é o que mantém a spec sendo lida com olhos de quem não a
escreveu.

## O que isso me custou e o que me rendeu

Rendeu velocidade de execução, e é honesto dizer que sem IA eu não teria entregado este escopo em
sete dias.

Custou vigilância. O padrão de um agente é preencher lacuna com a resposta mais comum, e a resposta
mais comum é justamente a que faz todo projeto gerado ter a mesma cara. As duas regras acima
existem porque eu tropecei nisso: o primeiro acento da paleta que saiu de uma sessão de UX foi um
âmbar quase idêntico ao `amber-500` do Tailwind — a receita exata do tema escuro gerado que eu tinha
acabado de listar como anti-padrão, três parágrafos antes, no mesmo documento.
