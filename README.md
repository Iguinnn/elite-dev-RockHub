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

> **Estado atual:** em construção. Hoje está de pé o esqueleto do backend — a aplicação sobe,
> responde `GET /saude` e publica a documentação automática. Banco, autenticação e telas entram nas
> stories seguintes. A seção [O que não está pronto](#o-que-não-está-pronto) é mantida honesta a
> cada passo.

## Como executar

### Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** para o backend. Ele mesmo baixa o Python 3.12 se a máquina
  não tiver

Node e PostgreSQL entram aqui quando o frontend (Story 1.2) e o banco (Story 1.3) chegarem.

### Backend

```bash
cd backend

cp .env.example .env      # no Windows: copy .env.example .env
uv sync                   # cria a .venv/ e instala exatamente o que está no uv.lock

uv run uvicorn app.main:app --reload
```

Sobe em <http://127.0.0.1:8000>. Para conferir que está no ar:

- <http://127.0.0.1:8000/saude> → `{"status": "ok"}`
- <http://127.0.0.1:8000/docs> → documentação automática do FastAPI

Testes:

```bash
cd backend
uv run pytest
```

Detalhes de configuração, variáveis de ambiente e o contorno para o bloqueio de executáveis do
Windows estão no [README do backend](backend/README.md).

### Frontend

Ainda não existe. Entra na Story 1.2.

## Contas semeadas

Ainda não existem — o seed com os quatro usuários de avaliação (organizador, cliente e portaria)
entra na Story 1.7, junto com o modelo de usuário.

## Roteiro de avaliação

O caminho de ponta a ponta — publicar, comprar, receber o ingresso, provocar a recusa de pagamento
e validar na portaria — é escrito quando o fluxo estiver completo. Por enquanto, o que dá para
verificar é o backend subindo e respondendo, como descrito acima.

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic *(Story 1.3)* |
| Frontend | Next.js 16 · React 19 *(Story 1.2)* |
| Catálogo externo | Ticketmaster Discovery v2 *(Epic 2)* |
| Deploy | Railway (API e banco) · Vercel (frontend) *(Stories 1.8 e 1.9)* |

```text
backend/          # API FastAPI
frontend/         # Next.js
docs/             # enunciado do desafio e decisões técnicas em prosa
_bmad-output/     # artefatos de planejamento: brainstorm, arquitetura, UX, epics e stories
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
