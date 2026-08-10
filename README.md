# RockHub

Plataforma de eventos e ingressos: o organizador publica um show buscando a atração no catálogo da
Ticketmaster e define os setores à venda; o cliente descobre o evento, reserva por quantidade, paga
e recebe um ingresso com QR; a portaria valida esse QR na entrada. É a minha resposta ao **Desafio
Elite Dev** da Verzel — o enunciado completo está em
[docs/desafio-elite-dev.md](docs/desafio-elite-dev.md).

Monorepo com `backend/` (FastAPI + PostgreSQL) e `frontend/` (Next.js). Este README é o histórico
de decisões do projeto: o que eu escolhi, por que, e o que eu descartei no caminho. Os READMEs de
[backend/](backend/README.md) e [frontend/](frontend/README.md) tratam do que é específico de cada
camada.

> **Estado atual:** em construção. O backend sobe com banco: PostgreSQL migrado por Alembic e a
> tabela `usuario` já existe, com `papel` restrito a `ORGANIZADOR`/`CLIENTE`/`PORTARIA`. O frontend
> sobe com a identidade visual aplicada, o cabeçalho e as páginas de estado vazio. As duas metades
> ainda não conversam: a primeira chamada de verdade acontece no login (Story 1.4), que também é
> quando a tabela `usuario` ganha o primeiro consumidor. A seção
> [O que não está pronto](#o-que-não-está-pronto) é mantida honesta a cada passo.

## Como executar

### Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** para o backend. Ele mesmo baixa o Python 3.12 se a máquina
  não tiver
- **Docker**, com o plugin Compose (`docker compose`, com espaço — é o Compose v2, embutido em
  qualquer instalação atual), para o PostgreSQL 16
- **Node ≥ 20.9** e **npm** para o frontend. O Next 16 não roda no Node 18

### Banco de dados

```bash
docker compose up -d      # Postgres 16 em localhost:5432, com o banco de teste já criado
docker compose ps         # conferir que o serviço está saudável
```

### Backend

```bash
cd backend

cp .env.example .env      # no Windows: copy .env.example .env
uv sync                   # cria a .venv/ e instala exatamente o que está no uv.lock

uv run alembic upgrade head       # cria o schema (tabela usuario)
uv run uvicorn app.main:app --reload
```

Sobe em <http://127.0.0.1:8000>. Para conferir que está no ar:

- <http://127.0.0.1:8000/saude> → `{"status": "ok"}`
- <http://127.0.0.1:8000/docs> → documentação automática do FastAPI

Testes (exigem o Compose no ar a partir da Story 1.3 — os testes de banco migram
`rockhub_teste` pelo próprio Alembic):

```bash
cd backend
uv run pytest
```

Detalhes de configuração, variáveis de ambiente e o contorno para o bloqueio de executáveis do
Windows estão no [README do backend](backend/README.md).

### Frontend

Em outro terminal:

```bash
cd frontend

cp .env.example .env.local    # no Windows: copy .env.example .env.local
npm install

npm run dev
```

Abre em <http://localhost:3000>, com o cabeçalho e o sistema visual aplicados.

**Não mude a porta.** A 3000 é a origem que o `CORS_ORIGENS` do backend já autoriza por padrão; em
outra porta, o login da Story 1.4 falha com um erro de CORS que custa a achar.

Nesta altura o frontend ainda não chama a API — dá para abrir os dois ou só um, tanto faz.
Convenções de CSS, tokens da identidade e armadilhas do Next 16 estão no
[README do frontend](frontend/README.md).

## Contas semeadas

Ainda não existem — o seed com os quatro usuários de avaliação (organizador, cliente e portaria)
entra na Story 1.7, junto com o modelo de usuário.

## Roteiro de avaliação

O caminho de ponta a ponta — publicar, comprar, receber o ingresso, provocar a recusa de pagamento
e validar na portaria — é escrito quando o fluxo estiver completo. Por enquanto, o que dá para
verificar é o backend subindo e respondendo e o frontend abrindo com a identidade aplicada, como
descrito acima.

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript · CSS próprio, sem framework |
| Catálogo externo | Ticketmaster Discovery v2 *(Epic 2)* |
| Deploy | Railway (API e banco) · Vercel (frontend) *(Stories 1.8 e 1.9)* |

```text
docker-compose.yml   # Postgres 16 local — infraestrutura do projeto inteiro, por isso na raiz
docker/initdb/       # script que cria o banco de teste na primeira subida do Compose
backend/             # API FastAPI
frontend/            # Next.js
docs/                # enunciado do desafio e decisões técnicas em prosa
_bmad-output/        # artefatos de planejamento: brainstorm, arquitetura, UX, epics e stories
```

`_bmad-output/` é versionado de propósito: o desafio pede que os artefatos de planejamento sejam
entregues junto com o código. Lá dentro estão a sessão de brainstorming, a espinha de arquitetura
com as decisões vinculantes, o design de UX e as 38 stories.

## Decisões: por que isso e não aquilo

Esta seção cresce a cada story, enquanto o motivo ainda está fresco. As decisões de regra de
negócio que ainda não viraram código estão detalhadas em
[docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md).

### Backend separado em FastAPI, e não Next.js full-stack

**Decidi** separar a API do frontend, com FastAPI de um lado e Next.js do outro.

**Por quê:** o núcleo do desafio é concorrência — não vender o mesmo lugar duas vezes, não validar
o mesmo ingresso duas vezes. Isso se resolve com `UPDATE` condicional e transação, e eu queria a
ferramenta que deixa isso explícito. Separar também torna o contrato da API visível, o que é
justamente o que está sendo avaliado.

**O que caiu:** Next.js full-stack com Route Handlers e Prisma. Seria menos código e um deploy só,
mas empurraria a regra de concorrência para dentro do framework de tela, onde ela fica difícil de
enxergar — e apagaria a fronteira entre API e interface que o desafio pede para demonstrar.

### Sem camada de repositórios: `routers → services → models`

**Decidi** que o backend tem duas camadas antes do modelo. `app/api/` cuida do HTTP,
`app/services/` cuida da regra de negócio e das transações. Não existe `app/repositories/`.

**Por quê:** a `Session` do SQLAlchemy já é, na prática, um repositório com unidade de trabalho.
Numa aplicação deste tamanho, a camada extra viraria uma pilha de funções de repasse — `criar`,
`buscar_por_id`, `salvar` — que não separam nada de novo e só afastam a regra do lugar onde ela
acontece.

**O que caiu:** o `router → service → repository` que é padrão em projeto grande. Ele se paga
quando há mais de uma fonte de dados ou troca de ORM no horizonte. Não é o caso aqui, e adotar por
hábito seria cerimônia sem contrapartida. Deixei registrado para não parecer esquecimento.

### Erro da API tem código estável, e o frontend decide por ele

**Decidi** que **toda** resposta de erro sai como
`{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}}` — as mesmas duas chaves, venha o
erro da regra de negócio, do framework (rota inexistente, método errado) ou da validação do
Pydantic. Fixei isso na primeira story, antes de existir qualquer regra de negócio.

**Por quê:** o `codigo` é contrato; a `mensagem` é texto para humano. Com essa separação eu reescrevo
qualquer mensagem sem quebrar tela nenhuma. E o ponto de padronizar as três origens de uma vez é
que o frontend passa a ter um caminho só para tratar erro — se o `404` do router falasse
`{"detail": ...}` e o do meu service falasse `{"erro": ...}`, cada tela teria que saber os dois.

**O que caiu:** deixar cada endpoint devolver o `detail` padrão do FastAPI e o frontend interpretar
o texto. Funciona até a primeira vez que alguém corrige uma vírgula na mensagem e derruba um `if`
do outro lado.

**O que abri mão junto:** o erro de validação do Pydantic vem como uma lista de objetos aninhados,
que é mais rica para depurar. Achatei em texto (`quantidade: não é um inteiro`) para não ter uma
forma de erro diferente só nesse caso. Contrato uniforme valeu mais que detalhe estruturado num
cenário em que quem consome é a minha própria tela.

### Configuração só por variável de ambiente

**Decidi** que tudo que muda entre máquinas vem do ambiente, lido por uma classe `Settings` do
Pydantic, e que nenhum segredo entra no repositório — o que é versionado é o `.env.example`.

**Por quê:** a chave da Ticketmaster e o segredo que assina os ingressos chegam nas próximas epics.
Com o hábito já estabelecido, não existe o momento de tentação em que alguém "só comita o valor
para testar". O Pydantic ainda valida na subida: `AMBIENTE=homologacao` derruba a aplicação na hora,
em vez de causar um comportamento estranho três telas adiante.

**O que caiu:** um `config.py` com valores por ambiente versionado no repositório. É mais cômodo de
ler, mas é exatamente o arquivo em que segredo acaba caindo.

### O domínio é escrito em português

**Decidi** nomear as entidades como o enunciado as chama: `evento`, `setor`, `reserva`, `ingresso`,
`portaria`. Inclusive a rota de saúde é `/saude`.

**Por quê:** quem avalia lê o enunciado em português e depois o código. Sem tradução no meio, a
correspondência é direta e não sobra dúvida sobre qual requisito cada parte atende.

**O que caiu:** o inglês por convenção de mercado. Criaria um dicionário mental entre requisito e
código — `sector` é setor ou seção? `gate` é portaria ou portão? — em troca de nada que o projeto
aproveite.

### `uv` em vez de `pip` + `requirements.txt`

**Decidi** usar o `uv` como gerenciador do backend, com `uv.lock` versionado.

**Por quê:** o desafio vai ser rodado numa máquina que eu nunca vi. O `uv` baixa o próprio Python
3.12, cria a virtualenv e instala versões travadas — um comando, sem passo manual pelo caminho.
Cada instrução a menos no README é um jeito a menos de a avaliação travar antes de ver o produto.

**O que caiu:** `pip` + `requirements.txt`, que assume que a pessoa já tem a versão certa do Python
e sabe criar a venv. E o Poetry, que resolve o mesmo problema, mas é ele próprio mais uma
instalação a fazer antes de começar.

### A interface é um jornal noturno, e não um catálogo de e-commerce

**Decidi** que a listagem de shows não tem card: são filas separadas por fio, com a data na margem
esquerda, nome de artista em serifada e etiquetas em monoespaçada versalete. Fundo preto quente,
âmbar como acento único, raio zero e sombra zero em todo o sistema.

**Por quê:** ingresso não é produto de prateleira — é o direito de entrar num lugar, numa hora. Card
com imagem, preço e botão é vocabulário de e-commerce, e ele carrega junto a promessa errada. A
estrutura de impresso diz a coisa certa sobre o que está sendo vendido, e custa o mesmo para
construir. O desafio penaliza por escrito a interface que "parece gerada", e o que denuncia uma
interface gerada não é ser feia: é ser bonita de um jeito só. Escolher qual dos vários bonitos era
justamente o ponto.

**O que caiu:** a fileira horizontal de cards com paleta empresarial — o formato de Sympla, Eventim e
Ingresso.com. É o que o mercado faz e é o que qualquer gerador entrega por padrão, então seria a
escolha segura. Caiu junto uma lista de padrões que eu proibi de propósito e que estão anotados no
[DESIGN.md](_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md):
faixa que varre a tela, grade de 6 a 8 cards de seção, par de título gigante com textinho embaixo, e
a linha de contexto decorativa no cabeçalho ("Edição de sexta · 14 apresentações em cartaz") — essa
última eu cheguei a montar no protótipo e removi, porque soava gerada.

Duas direções visuais competiram antes: um jornal de eventos londrino, editorial e claro, e uma
parede de cartazes de casa de show, noturna. Nenhuma das duas resolvia sozinha — a primeira não tem
noite, a segunda não tem estrutura. A identidade final é a fusão: estrutura de impresso, cor de
madrugada.

### CSS escrito à mão, sem biblioteca de componentes

**Decidi** não usar shadcn, MUI, Chakra nem Tailwind. O frontend tem um `globals.css` com os nove
tokens da identidade e um `.module.css` por componente.

**Por quê:** é a mesma razão da decisão acima. Biblioteca de componentes não traz só código pronto —
traz junto um vocabulário visual, e é exatamente o vocabulário que este projeto está tentando não
ter. O card arredondado com sombra sutil vem de graça, e tirar ele depois dá mais trabalho do que
nunca tê-lo. Com CSS Modules o token fica num lugar só e o estilo de cada componente tem escopo
isolado, sem colisão de nome de classe.

**O que caiu:** Tailwind, que é o padrão do `create-next-app` e teria sido mais rápido de escrever.
Além do argumento acima, ele empurra a decisão visual para dentro do JSX, onde eu não consigo mais
ler a identidade inteira num arquivo só. Caiu também a folha global única no estilo do protótipo:
funciona hoje, mas com 30 telas pela frente vira um arquivo enorme com nomes de classe brigando.

### Fontes do sistema, nenhuma fonte externa

**Decidi** usar Georgia para a voz serifada e a monoespaçada do sistema para etiqueta e código.
Nenhuma fonte é baixada.

**Por quê:** a tensão entre as duas famílias é o que faz a identidade funcionar — serifada sozinha
vira convite de casamento, monoespaçada sozinha vira terminal —, e essa tensão eu consigo com o que
já existe em qualquer máquina. Sem requisição de rede, sem salto de layout enquanto a fonte carrega,
sem depender de um CDN de terceiro estar no ar durante a avaliação.

**O que caiu:** uma serifada de display do Google Fonts, que seria mais distinta. O `create-next-app`
inclusive já vem com a `Geist` configurada — eu arranquei. Ganhar meio grau de personalidade não
paga o custo de fazer a primeira renderização depender de rede.

### TypeScript no frontend

**Decidi** escrever o frontend em TypeScript.

**Por quê:** o que trafega entre as duas camadas é um contrato com muitos campos, em português, com
dinheiro em centavos e data em UTC — `preco_centavos`, `data_hora`, `vendidos`, `expira_em`. É
precisamente o tipo de coisa em que se erra o nome do campo e só se descobre com um `undefined`
aparecendo na tela. Como não há teste automatizado no frontend, o `tsc` é a única rede que eu tenho
ali.

**O que caiu:** JavaScript puro, que é mais rápido de escrever. Ele é mais rápido até a primeira vez
que eu renomeio um campo no backend — aí eu descubro as telas quebradas uma a uma, abrindo cada
uma, em vez de ler a lista que o compilador me dá de uma vez.

### Postgres local por `docker-compose.yml` na raiz, não instalado na máquina

**Decidi** subir o PostgreSQL 16 por Compose, num `docker-compose.yml` na raiz do repositório —
não dentro de `backend/`, porque o banco é infraestrutura do projeto inteiro (a Story 1.7 semeia
por ele, e o frontend em desenvolvimento depende do backend que depende dele).

**Por quê:** quem avalia vai clonar o repositório numa máquina que eu nunca vi. Um comando que sobe
o banco do zero, com volume nomeado e `healthcheck`, é um passo manual a menos para a avaliação
travar antes de chegar no produto.

**O que caiu:** Postgres instalado direto na máquina — obrigaria instalar, criar banco e usuário à
mão, mais passos manuais e mais formas de a avaliação travar cedo. E o banco da Railway direto
durante o desenvolvimento — zero setup local, mas passaria a depender de rede o tempo todo e todo
mundo (inclusive eu, testando) escreveria no mesmo banco de produção.

### SQLAlchemy síncrono, não `AsyncSession`

**Decidi** usar a `Session` síncrona do SQLAlchemy 2, no estilo tipado (`Mapped` / `mapped_column`).

**Por quê:** o núcleo deste desafio é concorrência — não vender o mesmo lugar duas vezes, não
validar o mesmo ingresso duas vezes — e isso se resolve com `UPDATE` condicional dentro de uma
transação. Esse código fica mais legível no síncrono. O volume de uma avaliação não cobra o preço
de I/O assíncrono, e `AsyncSession` exigiria `await` disciplinado em toda consulta e em toda
fixture de teste.

**O que caiu:** `AsyncSession` — melhor sob carga alta de I/O, mas um `await` esquecido bloqueia o
event loop de um jeito difícil de diagnosticar, e a disciplina que isso exige não se paga no
tamanho deste projeto.

### `papel` como `VARCHAR` + `CHECK`, não enum nativo do Postgres

**Decidi** que a coluna `papel` é `VARCHAR(20)` com um `CheckConstraint` nomeado
(`papel_valido`), listando os três valores (`ORGANIZADOR`, `CLIENTE`, `PORTARIA`), em vez do tipo
enum nativo do Postgres.

**Por quê:** o Alembic não cria nem derruba um tipo enum nativo sozinho no `downgrade()` — isso
quebraria a garantia de que o banco pode ser reconstruído do zero (é literalmente um critério de
aceite da Story 1.3). Alterar os valores permitidos depois também exigiria `ALTER TYPE` numa ordem
específica, mais frágil que reescrever uma migração de `CHECK`.

**O que caiu:** o enum nativo — mais idiomático no Postgres, mas o `downgrade` frágil e a evolução
mais custosa pesaram mais que o ganho de idiomatismo.

### Alembic desde a primeira tabela, nunca `create_all` — nem em teste

**Decidi** que todo schema nasce por migração Alembic versionada, sem exceção — inclusive nos
testes, que migram o banco de teste pelo Alembic em vez de criar as tabelas a partir dos modelos.

**Por quê:** `create_all` seria mais rápido de montar, mas deixaria de verificar exatamente o que
esta story entrega: a migração em si. Sem um `downgrade()` exercitado, uma migração pode estar
quebrada por meses sem que ninguém perceba — e seria a Story 1.8 (deploy na Railway) a descobrir
isso da pior forma possível, no meio de um deploy.

**O que caiu:** `Base.metadata.create_all`, cogitado especificamente para os testes por ser mais
rápido de escrever. Cai fora do projeto inteiro, não só desta story — é regra para as tabelas das
Epics 2 a 5 também.

### Testes de banco contra Postgres real, migrado pelo Alembic — não SQLite em memória

**Decidi** que a suíte roda `alembic downgrade base` seguido de `upgrade head` contra um banco de
teste real (`rockhub_teste`) antes de qualquer asserção, em vez de usar SQLite em memória.

**Por quê:** SQLite não tem UUID nativo, não tem `TIMESTAMPTZ` e trata `CHECK` de outro jeito —
passaria verde sem provar nada sobre o schema que a migração de verdade cria. O custo que eu aceitei
foi que `uv run pytest` passa a exigir o Compose no ar, e isso está documentado no
[README do backend](backend/README.md#testes).

**O que caiu:** SQLite em memória — mais rápido e sem dependência externa, mas testando um banco
que não é o de produção. `create_all` para os testes caiu pelo mesmo motivo da decisão anterior.

## O que não está pronto

Além do que ainda está por vir nas stories, estes são cortes conscientes — estão detalhados em
[docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md):

| O quê | Por quê |
|---|---|
| **Mapa de assentos** | O desafio aceita venda por quantidade em setores. A plataforma é focada em shows — pista, VIP, camarote — onde assento numerado não é o padrão |
| **Tela de editar evento** | O vínculo com a portaria só é definido na publicação. Num sistema real seria preciso escalar e remover porteiros depois |
| **Cancelamento pelo cliente** | O modelo já suporta; faltam endpoint e tela |
| **Pagamento real** | O gateway é simulado, com recusa determinística para que os dois caminhos sejam testáveis |
| **Refresh token** | Sessão de 8 horas basta para o cenário avaliado |
| **Teste automatizado no frontend** | Não há Vitest, Testing Library nem Playwright, e isso é decisão. As invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a primeira story. Em 7 dias, configurar teste de componente para cobrir markup que ainda vai mudar muito não se paga. O frontend é verificado por `npm run build`, `tsc --noEmit`, ESLint e conferência no navegador |
