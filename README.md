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

> **Estado atual:** em construção, e **as duas metades estão no ar** —
> <https://elite-dev-rock-hub.vercel.app> é a aplicação, com o PostgreSQL da Railway migrado e
> semeado por trás. Dá para abrir num navegador, entrar com uma conta de avaliação e ver a `/conta`
> sem clonar nada. **O acesso está fechado pelos dois lados:** dá para criar conta em
> `/cadastro` e entrar em `/login` — senha em Argon2id, sessão em cookie `httpOnly` de 8 horas, e o
> navegador falando só com o domínio do frontend. Rota protegida já tem guarda por papel, e um
> comando semeia as quatro contas de avaliação (abaixo, em
> [Contas semeadas](#contas-semeadas)). O backend sobe com PostgreSQL migrado por Alembic e a tabela
> `usuario`; o frontend sobe com a identidade visual aplicada, o cabeçalho e as páginas de estado
> vazio. Ainda não há evento nenhum para descobrir ou comprar — isso começa na Epic 2. A seção
> [O que não está pronto](#o-que-não-está-pronto) é mantida honesta a cada passo.

## No ar

A aplicação está publicada na Vercel — **é esta URL que abre a interface**:

**<https://elite-dev-rock-hub.vercel.app>**

Entre com qualquer uma das credenciais de [Contas semeadas](#contas-semeadas). O caminho completo,
passo a passo, está em [Roteiro de avaliação](#roteiro-de-avaliação).

A API vive à parte, na Railway, com o banco no mesmo projeto:

**<https://elite-dev-rockhub-production.up.railway.app>**

Você não precisa dela para usar a aplicação — o navegador nunca fala com esse endereço, e é de
propósito ([por quê](#proxy-api-no-next-não-samesitenone-em-produção)). Ela está aqui para quem
quiser ver o contrato da API. Dá para conferir sem instalar nada:

- **[`/saude`](https://elite-dev-rockhub-production.up.railway.app/saude)** → `{"status": "ok"}`
- **[`/docs`](https://elite-dev-rockhub-production.up.railway.app/docs)** → a documentação
  automática, com as quatro rotas de autenticação. Dá para entrar por ali mesmo, com qualquer uma
  das credenciais de [Contas semeadas](#contas-semeadas)

```bash
curl -X POST https://elite-dev-rockhub-production.up.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

Essa chamada é a verificação que mais paga num comando só: ela só devolve `200` se as migrações
rodaram, **e** o seed gravou as contas, **e** o banco em uso é o da Railway.

E a mesma chamada **pelo domínio da Vercel** prova o sistema inteiro de uma vez:

```bash
curl -i -X POST https://elite-dev-rock-hub.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

Ela só responde `200` se o build da Vercel leu o endereço da API, **e** o proxy `/api/*` reescreveu
para a Railway a partir do servidor, **e** o banco de lá respondeu. Repare no `Set-Cookie`: ele volta
pelo domínio da Vercel, com `HttpOnly`, `Secure` e `SameSite=lax` — é o cookie de sessão
atravessando dois fornecedores, que é a coisa que este deploy existe para provar.

Como cada plataforma foi configurada, campo por campo e refazível numa conta vazia, está nos READMEs
de cada camada: [Deploy na Vercel](frontend/README.md#deploy-na-vercel) e
[Deploy na Railway](backend/README.md#deploy-na-railway). Não há `vercel.json` nem `railway.json`
neste repositório, e isso é decisão — o motivo está
[abaixo](#a-configuração-de-deploy-mora-no-painel-nas-duas-plataformas).

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

# gere o segredo que assina a sessão e cole no .env, em JWT_SECRET
# (opcional em desenvolvimento — o valor de exemplo funciona; veja abaixo)
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"

uv run alembic upgrade head       # cria o schema (tabela usuario)
uv run python -m seeds.semear     # cria as 4 contas de avaliação (organizador, 2 clientes, portaria)
uv run uvicorn app.main:app --reload
```

O seed pode rodar quantas vezes você quiser: ele não duplica conta e **não apaga nem sobrescreve
nada** que já esteja no banco. Rode-o de dentro de `backend/` e **com o `-m`** — os dois detalhes
estão explicados em [Contas semeadas](#contas-semeadas).

Em desenvolvimento o valor de exemplo do `JWT_SECRET` funciona e você pode pular esse passo. Com
`AMBIENTE=producao` ele **derruba a aplicação na subida**, de propósito — o motivo está no
[README do backend](backend/README.md#configuração).

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

**Suba o backend antes.** Desde o login, o frontend chama a API — e ele a alcança por um proxy
próprio: o navegador só conhece `/api/...`, e o Next reescreve para `http://localhost:8000` do lado
do servidor. Convenções de CSS, tokens da identidade, o proxy e as armadilhas do Next 16 estão no
[README do frontend](frontend/README.md).

## Contas semeadas

Um comando cria as quatro contas de avaliação, com o Compose no ar e a migração aplicada:

```bash
cd backend
uv run python -m seeds.semear
```

| Papel | Nome | E-mail | Senha |
|---|---|---|---|
| `ORGANIZADOR` | Helena Marques | `organizador@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Bruno Tavares | `cliente@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Marina Aoki | `cliente2@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Jonas Ribeiro | `portaria@rockhub.dev` | `rockhub123` |

**São dois clientes de propósito.** O segundo existe para dar como demonstrar duas garantias que um
cliente só deixaria no ar: que o ingresso de um não aparece na conta do outro (Epic 4) e que duas
pessoas disputando o último ingresso de um setor produzem uma venda e uma recusa (Epic 3).

**As mesmas quatro contas existem no banco da Railway**, criadas por este mesmo comando: ele roda a
cada deploy, logo depois das migrações. Então dá para entrar com elas em três lugares, com as mesmas
senhas: no seu ambiente local, na [aplicação publicada](https://elite-dev-rock-hub.vercel.app) e
direto no `/docs` da [API](#no-ar). As quatro foram conferidas na URL pública — cada uma responde
`200` com o papel certo.

O comando imprime uma linha por conta — `criada` na primeira execução, `mantida` nas seguintes — e
**rodar de novo é seguro**: ele não duplica conta, não apaga nem sobrescreve nada. Se você já tinha
criado contas pela interface, elas continuam exatamente onde estão.

Dois detalhes que valem os dez segundos de leitura:

- **Com o `-m`.** `uv run seeds/semear.py` falha com `ModuleNotFoundError: No module named 'app'` —
  executar o arquivo direto põe `backend/seeds/` no caminho de import em vez de `backend/`
- **A partir de `backend/`**, porque é de lá que o `.env` é lido

**Conta criada por `/cadastro` nasce sempre `CLIENTE`**, de propósito: não há seletor de papel na
tela, e enviar `papel` na requisição não muda nada. Se você quiser uma conta de cliente sua, abra
<https://elite-dev-rock-hub.vercel.app/cadastro> (ou `http://localhost:3000/cadastro`, se estiver
rodando local) — nome, e-mail e senha, e já entra logado.

## Roteiro de avaliação

O caminho de ponta a ponta — publicar, comprar, receber o ingresso, provocar a recusa de pagamento
e validar na portaria — é escrito quando o fluxo estiver completo.

### Sem instalar nada

Abra <https://elite-dev-rock-hub.vercel.app>. São cinco minutos, sem clonar, sem Docker, sem `uv`:

1. A raiz abre com a identidade aplicada — fundo escuro, masthead com o fio duplo, serifada nos
   títulos. O masthead mostra `Início` · `Entrar`, porque você ainda não tem sessão
2. Abra `/conta` direto na barra de endereço → você é levado para `/login?voltar=%2Fconta`. A guarda
   de rota está valendo em produção
3. Entre com `organizador@rockhub.dev` / `rockhub123` → você **volta para a `/conta`**, não para a
   raiz, e ela mostra **Helena Marques** e o papel `ORGANIZADOR`. Essa conta não poderia ter nascido
   pela interface: `/cadastro` só cria `CLIENTE`
4. O masthead virou `Início` · `Minha conta`. Clique em `Sair` → ele volta para `Entrar`
   **imediatamente, sem recarregar a página**
5. Abra `/cadastro` e crie uma conta sua, com nome, e-mail e senha de no mínimo 6 caracteres → cai na
   raiz já logado. Senhas diferentes nos dois campos mostram o erro **sem nenhuma requisição**
6. No DevTools, aba Application: o cookie `rockhub_sessao` está no domínio da **Vercel**, com
   `HttpOnly` marcado — e `document.cookie` no console não o mostra. Na aba Network, toda chamada saiu
   para `/api/...` no domínio da Vercel, **nunca** para `up.railway.app`

O passo 6 é o que eu pediria para olhar com atenção: a interface está na Vercel, a API na Railway, e
mesmo assim não existe requisição entre domínios nem cookie de terceiro. O motivo está em
[Proxy `/api/*` no Next](#proxy-api-no-next-não-samesitenone-em-produção).

**O que ainda não dá para fazer por lá:** descobrir evento, comprar ingresso, receber o QR ou validar
na portaria. Nada disso existe ainda — a Epic 2 começa a publicação de eventos. O que está pronto é o
acesso, e é ele que este roteiro percorre.

### Na sua máquina

Rodando local pelos passos de [Como executar](#como-executar), e começando pelas contas semeadas
(rode `uv run python -m seeds.semear` se ainda não rodou):

1. Entrar em `http://localhost:3000/login` como `organizador@rockhub.dev` / `rockhub123` → a
   `/conta` mostra **Helena Marques** e o papel `ORGANIZADOR`. É a conta que vai publicar eventos na
   Epic 2, e ela não poderia ter nascido pela interface: `/cadastro` só cria `CLIENTE`
2. Sair e entrar como `cliente@rockhub.dev` → a mesma tela mostra **Bruno Tavares**, papel `CLIENTE`.
   O segundo cliente, `cliente2@rockhub.dev`, ainda não tem o que fazer aqui: ele existe para as
   Epics 3 e 4, onde prova que o ingresso de um não aparece na conta do outro e que dois clientes
   disputando o último lugar de um setor produzem uma venda e uma recusa
3. Rodar `uv run python -m seeds.semear` **de novo** → as quatro linhas dizem `mantida`, o comando
   sai em `0` e nenhuma conta sua desaparece. É a garantia que faz esse mesmo comando poder rodar a
   cada deploy
4. `http://127.0.0.1:8000/saude` responde `{"status": "ok"}`, e `/docs` lista `/auth/cadastro`,
   `/auth/login`, `/auth/logout` e `/auth/eu`
5. E, para ver o contrato da API sem passar pela interface: abrir
   <https://elite-dev-rockhub-production.up.railway.app/docs> e entrar pelo `POST /auth/login`
   com `organizador@rockhub.dev` / `rockhub123` → `200`, com `"papel": "ORGANIZADOR"`. É a mesma
   aplicação que a interface publicada consome, contra o mesmo PostgreSQL da Railway
6. Abrir `http://localhost:3000/cadastro` e criar uma conta com nome, e-mail e senha (mínimo de 6
   caracteres) → **cai na raiz já logado**, sem precisar entrar de novo. Rodar o seed mais uma vez
   depois disso **não mexe nessa conta**: ela continua lá e continua entrando
7. No DevTools, aba Application: o cookie `rockhub_sessao` está no domínio `localhost:3000` — o do
   frontend — com `HttpOnly` marcado. E `document.cookie` no console não o mostra
8. Na aba Network, a chamada foi para `/api/auth/cadastro`, nunca para `localhost:8000`
9. Tentar cadastrar **o mesmo e-mail de novo** (inclusive com outra caixa: `IGOR@Exemplo.COM`) mostra
   "Esse e-mail já tem conta. Entre com ele ou use outro." e responde `409` — nunca um `500`
10. No cadastro, digitar senha e confirmação diferentes mostra "As senhas não conferem." **sem
    nenhuma requisição no Network** — a confirmação nunca sai do navegador
11. Apagar o cookie e entrar em `/login` com a conta que você acabou de criar → cai na raiz. É a
    prova de que hash e normalização de e-mail batem entre as duas rotas
12. Errar a senha mostra "E-mail ou senha incorretos." numa região anunciada por leitor de tela; a
    resposta é `401` com `CREDENCIAIS_INVALIDAS`. Um e-mail que não existe devolve **exatamente** a
    mesma coisa
13. Ir e voltar entre `/login` e `/cadastro` pelos links no pé de cada tela, sem digitar URL. E o
    logotipo, no alto das duas, leva de volta para a raiz
14. `Tab` percorre os campos → botão → link, com o contorno âmbar visível em todos

E o ciclo da sessão, que fecha na Story 1.6:

15. **Sem sessão**, a raiz `http://localhost:3000/` abre normalmente e o masthead mostra
    `Início` · `Entrar` — a raiz é pública
16. Ainda sem sessão, abrir `http://localhost:3000/conta` → você é levado para
    `/login?voltar=%2Fconta`. Entrar ali **devolve você a `/conta`**, não à raiz
17. Com sessão, o masthead vira `Início` · `Minha conta`, e a `/conta` mostra nome, e-mail e papel
18. Clicar em `Sair` leva de volta para `/` **e o masthead vira `Entrar` na hora**, sem recarregar
19. `curl -i http://127.0.0.1:8000/auth/eu` sem cookie responde
    `401 {"erro":{"codigo":"NAO_AUTENTICADO", ...}}`
20. Abrir `/login?voltar=//exemplo.com` (ou `?voltar=https://exemplo.com`, ou
    `?voltar=javascript:alert(1)`) e entrar → você cai em `/`. **Nunca fora do site**
21. `curl -i http://127.0.0.1:8000/rota-que-nao-existe` responde `404` no mesmo formato
    `{"erro": {...}}` das rotas de verdade, e com a mensagem em português

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Sessão | Argon2id (`argon2-cffi`) para a senha · JWT HS256 (`PyJWT`) em cookie `httpOnly` |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript · CSS próprio, sem framework |
| Catálogo externo | Ticketmaster Discovery v2 *(Epic 2)* |
| Deploy | Vercel (frontend) e Railway (API e banco) — **as duas no ar** |

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

### Senha em Argon2id, não bcrypt nem SHA com sal

**Decidi** gravar senha como hash **Argon2id**, pelo `argon2-cffi`, com os parâmetros padrão da
biblioteca — que já são o perfil de baixa memória da RFC 9106.

**Por quê:** Argon2id é o vencedor da Password Hashing Competition e a recomendação atual do OWASP,
e é o único dos candidatos que resiste tanto a ataque por GPU quanto a ataque por hardware dedicado,
porque custa **memória** além de tempo. Na prática ele me dá de graça três coisas que eu teria que
construir e defender sozinho: sal aleatório por hash (por isso a mesma senha hasheada duas vezes dá
strings diferentes, e por isso não existe coluna de sal no banco — ele viaja dentro da própria
string), todos os parâmetros embutidos no hash (posso endurecê-los depois sem invalidar o que já
está gravado), e um custo deliberado de ~50ms por verificação.

**O que caiu:** **bcrypt**, que ainda é perfeitamente aceitável, mas trunca a senha em 72 bytes
silenciosamente e não impõe custo de memória. E **SHA-256 com sal**, que é o erro clássico: parece
seguro porque é criptografia de verdade, mas é rápido *por projeto* — e velocidade é exatamente a
propriedade errada aqui, porque quem tem o banco vazado testa bilhões de palpites por segundo.
Descartei junto o `passlib`, que é o wrapper que a documentação antiga do FastAPI usa: está sem
lançamento desde 2020, quebrou com o bcrypt 4, e não acrescenta nada sobre a API direta do
`argon2-cffi`.

**O custo que aceitei:** ~50ms e ~64 MB por verificação de senha. É o objetivo do algoritmo, não um
problema a otimizar, mas aparece de duas formas concretas — a suíte de testes de login é
perceptivelmente mais lenta que o resto, e isso pesa na escolha do tamanho da instância na Railway.

### Sessão em cookie `httpOnly`, não token no `localStorage`

**Decidi** que o JWT viaja num cookie `httpOnly`, `SameSite=Lax`, `Path=/`, com 8 horas de validade
e `Secure` quando `AMBIENTE=producao`. JavaScript nunca lê o token.

**Por quê:** token em `localStorage` é legível por qualquer script que rode na página — uma única
falha de XSS, em qualquer dependência, entrega a sessão inteira. Com `httpOnly` o navegador envia o
cookie e o JavaScript não o enxerga, então o mesmo XSS não consegue exfiltrar a credencial. E como o
frontend é Next com Server Components, cookie é também a única forma que funciona nos dois lados:
`localStorage` não existe no servidor, então eu acabaria com dois jeitos de autenticar — um no
cliente, outro no servidor — que é precisamente o que o AD-15 existe para impedir.

As 8 horas cobrem um turno de portaria, que é o cenário mais longo do sistema. Elas não são
configuráveis de propósito: invariante de arquitetura com justificativa de domínio não vira knob,
senão o valor em produção passa a divergir do documentado e ninguém descobre até alguém ser
deslogado no meio do turno.

**O que caiu:** `Authorization: Bearer` com o token no `localStorage`, que é o padrão que quase todo
tutorial de SPA ensina. É mais simples de depurar (dá para ver o token) e imune a CSRF por
construção — mas troca uma classe de ataque difícil por uma fácil, e quebraria os Server Components.
Caiu junto o **refresh token**: resolveria a sessão expirar no meio de um uso longo, ao custo de
mais um endpoint, mais uma tabela e uma regra de rotação para escrever e testar. Para 8 horas de
validade num sistema avaliado em dias, expirou e faz login de novo.

### PyJWT, não `python-jose` nem HMAC na mão

**Decidi** usar **PyJWT 2.13.0** para assinar e ler o token, sempre em HS256 com a lista de
algoritmos fixa no código.

**Por quê:** é a biblioteca de JWT mantida e minimalista do ecossistema Python — para HMAC ela não
traz dependência nenhuma a mais. E ela me protege de um erro específico: `jwt.decode` recusa rodar
sem `algorithms=[...]` explícito. Isso não é burocracia. Aceitar o algoritmo que vem escrito *dentro
do próprio token* é a vulnerabilidade clássica de JWT — um token forjado com `"alg": "none"` passaria
a valer. A biblioteca me obriga a fechar essa porta.

**O que caiu:** **`python-jose`**, que era a recomendação antiga da documentação do FastAPI. Último
lançamento em maio de 2025, e implementa o JOSE inteiro (JWE, JWK) — trazendo `pyasn1`, `rsa` e
`ecdsa` para o lockfile — quando eu uso exatamente uma primitiva. E **`hmac` + `hashlib` da
biblioteca padrão**, que teria zero dependência nova e é o mesmo mecanismo que eu vou usar na
assinatura do QR (AD-5): caiu porque me obrigaria a escrever à mão expiração, `base64url` e
comparação em tempo constante. Código de segurança escrito à mão, quando existe versão testada por
muita gente, é risco sem contrapartida.

### Proxy `/api/*` no Next, não `SameSite=None` em produção

**Decidi** que o navegador **nunca fala com o backend diretamente**. Ele chama `/api/auth/login` no
domínio do próprio frontend, e o Next reescreve para a API do lado do servidor.

**Por quê:** o deploy separa as duas metades em `rockhub.vercel.app` e `rockhub.up.railway.app`, e
para o navegador esses são *sites diferentes* — `vercel.app` e `up.railway.app` estão os dois na
Public Suffix List, então não existe domínio registrável em comum. Um cookie `SameSite=Lax` não é
aceito nem reenviado nesse cruzamento. O detalhe cruel é que isso passa despercebido: em
`localhost`, `:3000` e `:8000` são o mesmo site (porta não conta), então a suíte inteira ficaria
verde e o login só falharia em produção. Com o proxy, o `Set-Cookie` volta pelo domínio da Vercel, o
cookie é de origem própria, e o `SameSite=Lax` do AD-15 vale literalmente — sem exceção por
ambiente e sem depender da política de cookie de terceiro de cada navegador, que muda por decisão de
fornecedor.

**O que caiu:** **`SameSite=None; Secure` em produção**, que é menos código e a saída óbvia. Ela
transforma a sessão em cookie de terceiro — o Safari bloqueia isso por padrão, então o login
simplesmente não entraria naquele navegador — e exigiria emendar o AD-15 com uma exceção por
ambiente. Caiu também **deixar `Lax` cru e resolver no dia do deploy**: empurraria para a Story 1.9
uma correção que mexe no frontend, descoberta no pior momento possível.

**O que veio junto:** como as chamadas passaram a ser de mesma origem, CORS deixou de participar do
caminho do navegador — mas eu **não** removi o `CORSMiddleware` do backend, que continua sendo a
rede de proteção de qualquer chamada direta. E a variável `NEXT_PUBLIC_API_URL` virou `API_URL`,
lida no servidor: com o proxy, o navegador não precisa mais saber o endereço da API, e manter as
duas seria manter dois caminhos para alcançar a mesma coisa.

### Credencial inválida tem uma resposta só — inclusive no tempo

**Decidi** que e-mail inexistente e senha errada devolvem exatamente a mesma resposta: mesmo `401`,
mesmo `CREDENCIAIS_INVALIDAS`, mesma mensagem. E que as duas custam o mesmo tempo.

**Por quê:** a metade fácil é a mensagem — "esse e-mail não está cadastrado" entrega, para quem
perguntar, quem tem conta no sistema. Eu garanto isso usando literalmente a *mesma construção* de
erro nos dois caminhos, não duas strings iguais que alguém pode divergir depois; e o teste compara
as duas respostas **entre si**, em vez de comparar cada uma com um literal.

A metade que quase todo mundo esquece é o tempo. O caminho natural — não achou o usuário, levanta o
erro na hora — responde em ~1ms para e-mail desconhecido e em ~50ms para e-mail existente com senha
errada, porque só o segundo paga o custo do Argon2. Cinquenta vezes de diferença é medível de fora
com um `for` e um cronômetro, e transforma o endpoint num oráculo de cadastro sem precisar de senha
nenhuma. A correção é uma linha: quando o usuário não existe, eu confiro a senha contra um hash
descartável e jogo o resultado fora.

**O que caiu:** a resposta específica ("e-mail não cadastrado", com link para criar conta), que é
mais gentil e é o que muito site grande faz. Ela ajuda o usuário legítimo que errou o e-mail e
entrega a base de cadastro para qualquer um que perguntar — e num sistema com dados de compra, a
lista de quem tem conta já é informação. Caiu também **limitar tentativas de login** por IP ou por
conta, que seria a defesa mais direta contra força bruta: está declarado em
[O que não está pronto](#o-que-não-está-pronto), porque é infraestrutura (contador com expiração,
armazenamento compartilhado entre instâncias) que não se paga no prazo deste desafio.

### A tela de acesso não tem a navegação do site

**Decidi** partir o frontend em duas cascas: `(site)`, com o masthead completo, e `(entrada)`, que
mostra só o logotipo. `/login` e `/cadastro` ficam na segunda.

**Por quê:** a primeira versão da tela de login herdava o masthead do layout raiz, e o resultado era
oferecer "Meus ingressos" e "Minha conta" para quem ainda não tinha entrado. São dois links que essa
pessoa não consegue abrir, e que hoje caem no 404 — a tela pedia credencial com uma mão e apontava
para portas trancadas com a outra. Uma tela de acesso mostra a marca e o formulário; o resto é
ruído, e ruído numa tela de duas entradas é o que faz parecer template.

**O que caiu:** dois **layouts raiz** separados, que é o outro jeito de fazer isso no App Router.
Caiu por dois motivos concretos: a documentação do Next avisa que navegar entre layouts raiz
diferentes força recarga completa da página, e layout raiz múltiplo exige abrir mão do
`app/layout.tsx` — o que deixaria o `not-found.tsx` sem layout de onde herdar e obrigaria a adotar
`global-not-found`, que ainda é experimental. Caiu também esconder o masthead com `usePathname()`:
funcionaria em três linhas, mas transformaria o masthead inteiro num componente de cliente para
resolver o que é uma questão de estrutura de rota.

**O que eu aprendi tentando:** cheguei a mover o `not-found.tsx` para dentro de `(site)` para ele
herdar o masthead de graça. Não funciona — só o `not-found` na raiz de `app/` atende URL que não
casa com rota nenhuma, e o efeito foi o visitante cair no 404 padrão do Next, sem identidade. Ele
voltou para a raiz montando a própria casca, e isso está escrito no arquivo para ninguém repetir a
tentativa.

### Só cliente cria a própria conta; organizador e portaria nascem por fora

**Decidi** que o cadastro pela interface produz **sempre** uma conta `CLIENTE`. Não existe seletor de
papel na tela, não existe campo `papel` no schema de entrada, e o papel é literal dentro do service —
enviar `{"papel": "ORGANIZADOR"}` na requisição cria uma conta cliente do mesmo jeito, calada.

**Por quê:** um seletor de papel numa tela pública é uma escalada de privilégio com aparência de
formulário — qualquer visitante viraria organizador e passaria a publicar eventos. E o AD-7 é ainda
mais direto sobre a portaria: ela só valida onde foi *escalada* por um organizador, então uma conta
de portaria autocriada não faria sentido nenhum, porque não estaria ligada a evento algum. O papel é
uma afirmação sobre confiança, e afirmação de confiança não pode vir de quem está pedindo o acesso.

Fiz questão de que o campo desconhecido seja **ignorado** em vez de recusado com `422`: um `422`
provaria que o servidor viu o campo, enquanto ignorá-lo prova que ele não tem como influenciar nada.
A garantia mais forte é a que não depende de validação.

**O que caiu:** um seletor "sou cliente / sou organizador" no cadastro, que é o que várias
plataformas de evento fazem — elas resolvem o problema com aprovação manual ou verificação de CNPJ,
que é exatamente a etapa que este projeto não tem. Caiu também **um cadastro de organizador separado,
em rota própria**: é o caminho certo, e está *adiado, não descartado* — sem uma forma de decidir quem
merece o papel, a rota seria o mesmo buraco com um endereço diferente. Até a Story 1.7, organizador e
portaria nascem pelo script documentado em [Contas semeadas](#contas-semeadas).

### Validação de e-mail escrita à mão, não `EmailStr` do Pydantic

**Decidi** conferir o formato do e-mail com uma expressão regular de uma linha —
`^[^@\s]+@[^@\s]+\.[^@\s]+$` — em vez de instalar `email-validator` para usar o `EmailStr`.

**Por quê:** essa regra pega o que ela precisa pegar: `igor`, `igor@`, `igor@exemplo` sem ponto no
domínio, e-mail com espaço no meio. Ou seja, o erro de digitação, que é o único caso realista aqui.
`EmailStr` seria a escolha de um sistema em produção, e o custo é uma dependência a mais no lockfile
— e este sistema não vai para produção real: ele existe para o avaliador ver que o cadastro funciona,
e três linhas provam isso igual. **Não é RFC 5322 e não pretende ser**, e essa decisão está escrita
como corte consciente no código, ao lado da regex, e não deixada para quem ler adivinhar.

**O que caiu:** `EmailStr` + `email-validator`, mais correto e mais caro. E, do outro lado,
**nenhuma validação no backend**, que deixaria o `type="email"` do navegador como única barreira — e
ele desaparece num `curl`. Ficar sem validação nenhuma é o tipo de ausência que quem avalia nota em
dez segundos.

**O efeito colateral que eu gostei:** esta foi a primeira story desde a 1.1 a não acrescentar
nenhuma dependência, em nenhuma das duas camadas.

### Confirmação de senha, porque não existe recuperação de senha

**Decidi** que o cadastro tem quatro campos, e o quarto é "repetir senha". A senha mínima é de **6
caracteres**, sem exigir maiúscula, número ou símbolo.

**Por quê:** as duas metades desta decisão vêm do mesmo lugar — **não há recuperação de senha neste
projeto**, e isso não vai mudar. Uma letra digitada errada seria conta perdida para sempre: sem
suporte, sem e-mail de redefinição, sem saída. O campo de confirmação custa uma comparação em memória
e elimina a falha inteira. Já o piso de 6 caracteres é o que basta para um sistema que existe para
ser avaliado, sem travar as senhas curtas que as contas semeadas da Story 1.7 vão usar.

A confirmação **não chega ao backend**, e isso é parte da decisão: o formulário tem os dois valores em
mãos, compara antes do `fetch` e nem faz a requisição. Mandá-la para a API acrescentaria um campo ao
contrato, um validador cruzado, uma mensagem e um teste — tudo para verificar algo que nenhum outro
cliente da API teria por que enviar. A regra de negócio é "senha com pelo menos 6 caracteres"; "duas
caixas de texto iguais" é ergonomia de tela.

**O que caiu:** **8 caracteres**, que é o piso do NIST SP 800-63B e teria sido o padrão defensável —
6 ganhou por ser suficiente no contexto real deste sistema. **Nenhuma regra de senha**, que aceitaria
senha de um caractere. E, no lugar da confirmação, um **botão "mostrar senha"**: menos atrito e uma
interação a menos, mas expõe a senha na tela de quem se cadastra em público, e exigiria um componente
novo para resolver o mesmo problema com menos garantia.

### `Campo` e `Botao` extraídos no segundo formulário, não no primeiro

**Decidi** que componente compartilhado nasce no **segundo uso**, nunca no primeiro. Na Story 1.4, com
só a tela de login, o campo e o botão ficaram dentro do próprio formulário. Nesta story, com o
cadastro, eles viraram `Campo.tsx` e `Botao.tsx` — e o login foi reescrito sobre eles.

**Por quê:** dois campos num único formulário não dão evidência nenhuma sobre qual é a abstração
certa; seis campos e dois botões entre duas telas dão. Componente extraído cedo é componente com
`props` inventadas para casos que nunca chegam, e que a próxima story reescreve inteiro. Extrair
depois custa reescrever código que já funciona — que é um custo real e conhecido — mas em troca a
forma do componente sai dos usos de verdade.

**O que caiu:** **repetir o CSS nas duas telas**, que é o precedente que eu mesmo abri na 1.2 com o
404. Cairia bem aqui também, e não tocaria em arquivo já entregue — mas ao custo de duas cópias do
mesmo campo que divergem na primeira vez que alguém ajustar uma só. O 404 e o formulário são casos
diferentes: uma tela isolada pode divergir sem consequência; um campo de formulário que diverge entre
o login e o cadastro racha a identidade em duas.

**O risco que eu assumi, e como cobri:** reescrever o `FormularioLogin` foi o ponto mais perigoso da
story — um `htmlFor` que perde o par com o `id`, um `autoComplete` que some, e a tela continua
*parecendo* certa, sem nenhum teste de frontend para acusar. A cobertura foi conferir o login inteiro
no navegador depois da extração, campo por campo, e os 40 testes anteriores do backend passarem sem
uma linha alterada.

**Um terceiro componente que eu não tinha planejado:** o `AvisoDeErro`, extraído por um critério
diferente. `Campo` e `Botao` saíram porque se repetem; ele saiu porque a regra que o faz funcionar é
*invisível* — a região `role="alert"` precisa existir no DOM desde o primeiro render, vazia, para que
o leitor de tela anuncie o erro quando o texto chegar. Escrita como comentário dentro de um
formulário, essa regra é a primeira coisa que alguém apaga por parecer óbvia ao copiar para o
segundo. **Regra que protege acessibilidade vira componente mesmo com poucos usos**, porque é onde
ela se protege sozinha.

### Autorização é dependência na assinatura do endpoint, não `if` no corpo do handler

**Decidi** que papel se declara, não se confere:

```python
@router.get("/organizador/eventos")
def meus_eventos(usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))): ...
```

Não existe um `if usuario.papel == ...` dentro do corpo de handler nenhum, no projeto inteiro.

**Por quê:** a proteção passa a fazer parte da *assinatura* da rota. Ela aparece na documentação
gerada — o `/docs` sabe que a rota é restrita —, e esquecê-la vira uma linha ausente que se vê à
distância, em vez de uma verificação que alguém precisava lembrar de escrever. É o AD-9, e a razão
de ele existir é que autorização espalhada por handler é o tipo de coisa que funciona em 19 rotas e
falha na vigésima, sem nada acusando.

**O que caiu:** **conferir o papel dentro do handler**, que é o caminho de menos código e o que
qualquer tutorial mostra. Ele não custa nada na primeira rota; custa na décima, quando a proteção
depende de disciplina de quem escreve, e não da estrutura. Considerei também um **middleware que
inspeciona o caminho da URL** (`/organizador/*` exige `ORGANIZADOR`): resolveria de um lugar só, ao
preço de manter uma tabela caminho→papel paralela às rotas — duas listas que divergem, e a
desatualizada é sempre a que ninguém olha.

### O papel vem do banco, não do que está escrito no token

**Decidi** que `exigir_papel` consulta o usuário no banco a cada requisição, mesmo com o `papel`
gravado dentro do JWT desde a Story 1.4.

**Por quê:** a sessão dura 8 horas (AD-15). Um papel corrigido no banco continuaria valendo o antigo
por todo esse tempo, e a única forma de derrubar o token seria trocar o `JWT_SECRET` — deslogando
todo mundo. Além disso, a consulta acontece de qualquer jeito: a dependência precisa do usuário
inteiro para responder o `GET /auth/eu`. Ler o papel do banco não custa uma consulta a mais, custa
zero.

**O que caiu:** **ler `carga["papel"]` do token**, que é o caminho curto e é o que a maior parte dos
exemplos de JWT faz. A economia é real (uma consulta por requisição) e paga-se com uma janela de 8
horas em que a autorização está errada e ninguém consegue corrigir. Um teste guarda essa decisão: um
usuário gravado como `CLIENTE`, com um token forjado dizendo `ORGANIZADOR`, recebe `403`.

Isso vale também para o vínculo portaria ↔ evento do AD-7, que vai ser lido do banco a cada
validação em vez de carregado na sessão.

### A guarda de rota mora na página, não em `middleware` do Next

**Decidi** que cada página protegida do frontend lê a sessão e redireciona por conta própria — três
linhas repetidas por página.

**Por quê:** o middleware só consegue ver que **existe** um cookie, não que ele vale. Validar o JWT
ali exigiria o `JWT_SECRET` no ambiente do frontend, e o AD-2 diz o contrário: o segredo que assina
a sessão não tem por que existir na Vercel. A guarda na página pergunta ao backend, que é quem tem o
segredo.

**O que caiu:** **o `middleware.ts` conferindo o cookie**, que é o caminho que todo tutorial de Next
mostra e centraliza a regra num arquivo só. Além do problema do segredo, ele viraria uma segunda
lista de rotas protegidas, paralela às páginas — e as três linhas repetidas, em compensação, ficam
ao lado do conteúdo que protegem, que é onde quem edita a página vai olhar. Considerei também
`unauthorized()`/`forbidden()`, que o Next 16 traz e seriam o caminho idiomático: estão atrás da
flag experimental `authInterrupts`, e eu não ligo flag experimental por conveniência.

### Página protegida sem sessão redireciona **com volta**, em vez de mostrar um convite

**Decidi** que abrir `/conta` sem sessão leva para `/login?voltar=%2Fconta`, e que entrar devolve a
pessoa ao destino original.

**Por quê:** ela pediu uma página específica. Depois de provar quem é, entregar essa página é o
mínimo — mandá-la para a raiz obriga a navegar de novo até onde já estava indo, e é atrito puro. O
parâmetro passa por `caminhoInternoSeguro` antes de virar navegação: `?voltar=` é um valor que quem
chega escolhe e a aplicação obedece, e sem filtro é o redirecionamento aberto clássico — um link
para o meu domínio que joga a pessoa em outro site logo depois de ela digitar a senha. Pior: a
documentação do Next avisa que uma URL `javascript:` entregue ao `router.push` executa no contexto
da página, o que faz disso um XSS.

**O que caiu:** **mostrar a página com um convite a entrar**, sem redirecionar. É mais simples, não
tem parâmetro e não tem o que validar — e perde o lugar de onde a pessoa veio. E **redirecionar sem
devolver**, que é o mais barato dos três e tem a mesma perda, sem nem a economia de código do
segundo.

### As contas de avaliação vêm de um script à parte, não de uma migração

**Decidi** que as quatro contas nascem de `backend/seeds/semear.py`, chamado à mão por
`uv run python -m seeds.semear`.

**Por quê:** conta de avaliação é *dado*, e migração é *schema*. Um script separado pode rodar de
novo quando alguém apagar uma conta sem querer, é lido por quem avalia sem precisar entender Alembic,
e o passo extra no README custa uma linha — que é o preço mais barato desta lista.

**O que caiu:** **uma migração Alembic de dados**, que seria zero passo a mais e faria o deploy semear
sozinho. Ela mistura dado com schema, roda **uma vez na vida** (conta apagada não volta nunca), e um
`alembic downgrade base` levaria as contas junto com as tabelas. Caiu também **semear no startup do
FastAPI**, que dispensaria o comando de release na Railway: semearia a cada `--reload` durante o
desenvolvimento e ataria o seed ao ciclo de vida da aplicação — o dia em que o seed falhasse, a API
não subiria.

### A idempotência do seed é uma consulta, não uma limpeza

**Decidi** que o seed pergunta "já existe esse e-mail?" e, se existir, **não escreve nada** — nem
nome, nem senha, nem papel. Não há `DELETE`, `TRUNCATE`, `UPDATE` nem `drop` em lugar nenhum de
`seeds/`.

**Por quê:** este é o primeiro código do projeto escrito para rodar **contra o banco de produção,
repetidamente, sem supervisão** — na Story 1.8 ele entra na sequência de cada deploy. Um seed que
limpasse a tabela antes de inserir funcionaria perfeitamente hoje e, no primeiro redeploy, apagaria a
conta de quem estivesse avaliando no meio de uma compra. A restrição `UNIQUE` do e-mail, criada na
Story 1.3, é o que sustenta isso de graça.

**O que caiu:** **limpar a tabela antes de inserir**, que é o padrão de seed mais comum e garante um
estado conhecido a cada execução — garantia que não vale nada se o preço for destruir dado real. Caiu
junto uma opção `--forcar` que recriaria tudo: é o `TRUNCATE` com outro nome, e quem quiser banco
limpo já tem `docker compose down -v`. E caiu **"atualizar" a conta que já existe** para deixá-la
igual ao script — parece zelo e, em produção, significa trocar a senha de alguém sem avisar. Quando
o e-mail existe com papel diferente do esperado, o script **avisa na saída e continua**, porque
silêncio ali viraria "o organizador não funciona" sem pista nenhuma.

### As quatro contas têm nome de gente, e uma senha só, publicada aqui

**Decidi** que as contas semeadas são pessoas — Helena Marques, Bruno Tavares, Marina Aoki, Jonas
Ribeiro —, com e-mail que diz o papel (`organizador@rockhub.dev`) e **a mesma senha** nas quatro,
impressa na tabela de [Contas semeadas](#contas-semeadas).

**Por quê:** o nome dessas contas aparece na tela, e a identidade visual manda nome próprio em
serifada (é a regra UX-DR2). "Organizador RockHub" em Georgia, no lugar onde deveria estar o nome de
uma pessoa, é exatamente a cara de dado de mentira que o desafio penaliza — o e-mail já diz o papel,
então o nome não precisa dizer. A senha única é sobre a outra ponta: a tabela do README precisa ser
copiável às onze da noite sem erro, e quatro senhas diferentes é quatro vezes mais chance de errar
uma. Ela passa no mínimo de 6 caracteres que a própria interface exige, então não abre exceção para o
seed.

**O que caiu:** **nomes genéricos pelo papel**, que seriam mais óbvios de ler numa lista e mais
honestos sobre serem dado de teste — perderam pela tipografia. **Uma senha por conta**, mais realista
e sem ganho nenhum aqui. E **deixar o seed configurável por variável de ambiente** (`SEED_SENHA`,
`SEED_EMAIL_ORGANIZADOR`), que parece a escolha flexível e é justamente o jeito de as credenciais
divergirem do README sem ninguém notar — o pior desfecho possível para um dado que existe para ser
copiado de um documento.

Isso **não** enfraquece a regra de segredo do projeto, e a distinção é a decisão: senha de conta
semeada é dado de avaliação publicado de propósito; `JWT_SECRET` e `TICKETMASTER_API_KEY` continuam
só no ambiente, fora do repositório. Pelo mesmo raciocínio o comando **não imprime a senha** no
terminal: ele roda no deploy da Railway, e o que ele imprime vai para o log — credencial em log é
hábito que se leva junto para o dia em que a credencial importa.

### A Railway constrói pelo Railpack, sem `Dockerfile` meu

**Decidi** deixar a Railway detectar e construir o backend com o builder dela, o Railpack, em vez de
escrever um `Dockerfile`. Não há arquivo de build neste repositório.

**Por quê:** o Railpack lê exatamente os três arquivos que já existem em `backend/` desde a Story
1.1 — `pyproject.toml`, `uv.lock` e `.python-version` — e monta a imagem com o Python 3.12 e as
versões travadas do lockfile. Ele ainda instala com `--no-dev` e `--locked`, o que me dá duas
garantias de graça: `pytest` não sobe para produção, e o build **falha** se o lockfile divergir do
`pyproject.toml`. Escrever um `Dockerfile` seria reimplementar isso à mão, com uma chance a mais de
errar a versão do Python ou esquecer o `--frozen`.

**O que caiu:** o **`Dockerfile` próprio** a partir da imagem oficial do `uv`. Ele é a escolha mais
defensável em projeto de vida longa, porque o build fica idêntico na minha máquina e no servidor e
imune a mudança de heurística do fornecedor — perdeu por ser mais um arquivo para manter e explicar
num projeto de sete dias, com ganho zero enquanto o Railpack acerta. Caiu também o **Nixpacks
explícito**, o builder anterior da Railway: mais congelado, com suporte a `uv` mais frágil, e já
fora do padrão.

**O que isso me custou:** uma pesquisa que eu não teria feito com `Dockerfile`. O Railpack instala o
`uv` só na fase de build e **não o deixa na imagem final** — os comandos de produção precisam chamar
`alembic`, `uvicorn` e `python` direto, e um `uv run` ali falha com `uv: not found`. Está escrito no
[README do backend](backend/README.md#por-que-os-comandos-não-usam-uv-run), porque é a primeira
"correção" que alguém tentaria fazer.

### Migração e seed rodam no Pre-deploy, não junto com a aplicação

**Decidi** que `alembic upgrade head && python -m seeds.semear` é o **Pre-deploy Command** do
serviço, separado do comando que sobe o `uvicorn`.

**Por quê:** o Pre-deploy roda num contêiner à parte, depois do build e **antes** de o tráfego ser
trocado para a versão nova. Se ele falhar, o deploy não prossegue e a versão anterior continua
atendendo. É exatamente a garantia que eu queria: migração quebrada **impede** a subida, em vez de
subir com o schema errado. E ele roda uma vez por deploy, não uma vez por réplica.

**O que caiu:** encadear tudo no comando de partida (`sh -c "alembic … && seed && uvicorn"`). É mais
portátil — funciona em qualquer plataforma, sem depender de um recurso da Railway — e foi por pouco.
Perdeu porque roda a cada réplica e a cada reinício automático, e porque migração quebrada ali vira
contêiner em ciclo de reinício: em vez de barrar a versão nova, **derruba a que estava funcionando**.
Caiu também um script de release versionado chamado pelo Pre-deploy, que deixaria o conteúdo legível
no repositório ao custo de duplicar o que o painel já mostra.

**A consequência que veio de graça:** duas decisões da Story 1.7 deixaram de ser precaução teórica.
O seed sair em `0` mesmo quando avisa sobre papel divergente é o que impede um aviso de derrubar o
deploy inteiro; e ele não imprimir a senha é o que impede credencial de cair no log de deploy da
Railway. As duas foram escritas prevendo este uso, e é aqui que elas passam a valer.

### A configuração de deploy mora no painel, nas duas plataformas

**Decidi** não versionar `railway.json`, `railway.toml` nem `vercel.json`. Builder, `Root
Directory`, branch, variáveis, comandos e health check estão configurados nos painéis da Railway e
da Vercel, e descritos campo por campo em [Deploy na
Railway](backend/README.md#deploy-na-railway) e [Deploy na Vercel](frontend/README.md#deploy-na-vercel).

**Por quê:** o painel **sobrescreve** o arquivo quando alguém edita por lá, e é por lá que se edita
no meio de um deploy que falhou, às pressas. Duas fontes para a mesma verdade divergem em silêncio, e
a desatualizada é sempre a que fica no repositório — parecendo documentação correta.

**O que caiu:** o **`railway.json` versionado**, que é a escolha de infraestrutura-como-código e teria
uma vantagem real — recriar o serviço viraria reimportar o repositório, e quem avalia leria a
configuração do deploy junto do código.

**O custo que aceitei, e como o cobri:** a configuração some se o serviço for apagado, e não aparece
em nenhum diff. É precisamente por isso que as seções de deploy dos dois READMEs não são um resumo —
elas têm os nomes exatos dos campos, os valores, a ordem e os erros que cada omissão produz.
Documentação substituindo arquivo só funciona se for detalhada a ponto de ser executável por quem
nunca viu o painel; menos que isso, eu teria escolhido errado.

**A Story 1.9 cobrou essa aposta e ela pagou.** Configurar a Vercel foi o mesmo exercício da Railway
num painel diferente, e os **dois** erros que eu já tinha cometido lá — `Root Directory` não
preenchido e branch de produção errada — apareceram de novo, idênticos. Eles estavam documentados
como armadilha desde a Story 1.8, então custaram minutos em vez de uma noite. Uma seção de README
que só descrevesse o final feliz não teria servido para nada ali.

### O `CORS_ORIGENS` lista a origem da Vercel, mesmo o CORS não estando no caminho do navegador

**Decidi** acrescentar `https://elite-dev-rock-hub.vercel.app` ao `CORS_ORIGENS` do backend, ao lado
do `http://localhost:3000` de desenvolvimento.

**Por quê:** é o estado correto do sistema. No dia em que qualquer coisa chamar a API diretamente —
um `curl` de demonstração, uma página futura sem proxy, um cliente de terceiro — a resposta certa já
está configurada, em vez de virar meia hora de depuração num momento ruim. E o critério de aceite
pede CORS e `SameSite` configurados com todas as letras.

**O que caiu:** **manter só o `localhost`** — e essa alternativa tem a verdade técnica do lado dela.
Desde o proxy da Story 1.4 o navegador não fala com a Railway, então a variável não participa de
absolutamente nada que exista hoje, e mexer nela custa um redeploy do backend por um efeito
observável nulo. Perdeu para o argumento de estado correto, mas foi decisão apertada, e registro
assim porque a alternativa não era ruim — era só menos completa.

**O que eu fiz questão de escrever junto:** que **não é isso que faz o login funcionar** entre os
dois fornecedores. CORS é uma política do navegador sobre requisição para outra origem, e em produção
não existe nenhuma: o navegador chama o próprio domínio da Vercel, e quem fala com a Railway é o
servidor do Next — servidor a servidor, sem navegador no meio. Quem faz o cookie sobreviver é o
proxy. Deixar o README sugerir que o CORS é o conserto apagaria a razão de o proxy existir, e no
primeiro login quebrado alguém iria mexer na variável errada.

### Publiquei a branch da epic, não a `main`

**Decidi** apontar a Production Branch dos dois painéis para
`epic-1---fundacao-acesso-e-primeiro-deploy`, e definir o `API_URL` da Vercel para Production **e**
Preview, com o mesmo valor.

**Por quê:** é ordem de eventos. O merge da Epic 1 acontece **depois** do code review da epic, e o
deploy é a última story antes dele. Publicar da `main` hoje significaria mesclar código ainda não
revisado só para conseguir fazer deploy — inverter a revisão e a publicação por conveniência de
configuração.

**O que caiu:** **mesclar na `main` antes e publicar dali**, que é o que as duas plataformas assumem
sozinhas e o que quem avalia espera encontrar. O custo que eu assumi é um campo divergente em dois
painéis, que precisa ser trocado quando a epic entrar na `main` — e é por isso que ele está escrito
nos dois READMEs de camada, em vez de virar surpresa.

Sobre o Preview: caiu **defini-lo só para Production**, que manteria o banco de produção fora do
alcance de qualquer build de branch. Perdeu porque o Preview cairia no padrão `http://localhost:8000`
do `next.config.ts` e ficaria com o login quebrado **sem erro visível** — a tela abre, o formulário
envia, e nada acontece. Preview quebrado é pior que Preview inexistente. A consequência que veio
junto — Preview escreve no banco de produção — está em [O que não está
pronto](#o-que-não-está-pronto).

### O `.gitignore` do Python engoliu `frontend/src/lib/`, e eu ancorei o padrão em vez de abrir exceção

**Decidi** trocar `lib/` e `lib64/` por `/lib/` e `/lib64/` no `.gitignore` da raiz, com a barra
inicial prendendo os dois padrões à raiz do repositório.

**Por quê:** o `.gitignore` deste projeto nasceu do template Python do GitHub, que traz `lib/` na
seção de empacotamento. Padrão sem barra no início **casa em qualquer profundidade** — então ele não
estava ignorando artefato de build do Python, estava ignorando **`frontend/src/lib/`**, desde a
Story 1.2. Os três arquivos que moram lá (`api.ts`, `sessao.ts`, `caminho.ts`) existiam na minha
máquina e nunca entraram no repositório. Com a barra, o padrão volta a significar o que o template
queria dizer.

**O que caiu:** **`!frontend/src/lib/` no fim do arquivo**, que consertaria este caso em uma linha
sem tocar no template. Perdeu porque deixa a armadilha armada: o padrão continua errado, e a próxima
pasta `lib/` aninhada — em qualquer camada, em qualquer epic — some do mesmo jeito e sem aviso. Uma
exceção conserta um sintoma; a âncora conserta a causa.

**E o code review da epic cobrou esse argumento.** Eu tinha ancorado dois padrões — `lib/` e
`lib64/` — e declarado a causa consertada. Só que os vizinhos deles no mesmo template continuavam
soltos: `build/`, `dist/`, `parts/`, `sdist/`, `var/`, `wheels/`, `htmlcov/`, `cover/`, `instance/`,
`target/` e `out/`. Nenhum estava engolindo nada naquele momento, e foi exatamente por isso que
passaram: eu conferi o sintoma, que tinha sumido, em vez da causa, que continuava lá em dez outros
lugares. Um `frontend/public/cover/` para capas de evento na Epic 2 teria reproduzido o mesmo
desastre, com o mesmo diagnóstico de duas horas. Ancorei todos, e a regra virou linha no
`CLAUDE.md`: **padrão de artefato de build entra com `/`.**

**O que eu não ancorei, de propósito:** os padrões de cache e de virtualenv — `__pycache__/`,
`.venv`, `node_modules/`, `env/`, `venv/`, `.pytest_cache/`. Esses **precisam** casar em qualquer
profundidade, porque é justamente em profundidade que eles nascem: `backend/.venv` e
`frontend/node_modules` só ficam de fora do repositório enquanto o padrão for solto. Ancorá-los por
simetria seria trocar um erro por outro maior — commitar uma virtualenv inteira. A distinção que
ficou: **artefato de build se ancora; cache que nasce ao lado do código, não.**

**A verificação que eu passei a ter:** cruzar todos os padrões do `.gitignore` contra a árvore real
de diretórios, em vez de conferir caso a caso. É o que transforma "não vejo problema" em "não existe
colisão", e leva segundos.

**Como isso apareceu, e é a parte que interessa:** o build da Vercel falhou com `Module not found`
em sete arquivos, e o denominador comum era exato — os sete importam de `@/lib`, e nenhum import de
`@/components` aparecia no rastro. **Nada na minha máquina podia ter pego isso.** `npm run build`,
`tsc --noEmit`, ESLint e os 85 testes do backend passam todos, porque os arquivos estão no disco. Só
um clone limpo revela, e o primeiro clone limpo deste projeto foi o da Vercel. É o argumento mais
concreto que eu tenho a favor de publicar cedo: o deploy fez, na Story 1.9, um trabalho de teste que
nenhuma suíte deste projeto faria.

### O pool confere se a conexão está viva antes de entregá-la

**Decidi** criar a engine com `pool_pre_ping=True` e `pool_recycle=1800`, em vez dos padrões do
SQLAlchemy.

**Por quê:** os padrões são `pool_pre_ping=False` e `pool_recycle=-1` — ou seja, o pool guarda a
conexão para sempre e nunca confere se ela ainda existe. O Postgres da Railway reinicia por
manutenção, e a rede interna derruba conexão ociosa. O resultado é o pior cenário possível para
este projeto: **a primeira requisição depois de um período parado responde `500`**, e a segunda
funciona. Quem avalia abre o link dias depois do meu último deploy, tenta entrar, leva um erro, e a
retentativa que consertaria já não acontece — a impressão foi dada. O `pre_ping` custa um `SELECT 1`
por checkout, e é o preço mais barato desta lista inteira.

**O que caiu:** **deixar nos padrões e confiar na retentativa**, que é o que o SQLAlchemy assume — ele
invalida o pool ao detectar o desconecte, então o problema "se resolve sozinho" na segunda tentativa.
Perdeu porque a segunda tentativa é minha suposição, não comportamento de quem está avaliando. Caiu
também **`pool_recycle` sozinho, sem o `pre_ping`**: recycle cobre a conexão que vai morrer de velha,
e não a que já morreu porque o servidor do outro lado reiniciou. São dois problemas, e o segundo é o
que acontece na Railway.

**Como isso apareceu:** não foi teste nem uso — foi o code review da Epic 1, e as duas camadas de
revisão chegaram nele por caminhos diferentes. É um defeito que nenhuma suíte deste projeto pegaria,
porque ele exige tempo passando entre duas requisições.

### O `500` também tem o formato de erro da API, e o framework fala português

**Decidi** registrar um quarto handler, para `Exception`, e traduzir a mensagem que o Starlette gera
sozinho para `404` e `405`.

**Por quê:** o README afirma, na decisão sobre o formato de erro, que **toda** resposta de erro sai
como `{"erro": {...}}`. Não era verdade. Os três handlers cobriam domínio, `HTTPException` e
validação; qualquer outra falha subia até o `ServerErrorMiddleware` do Starlette e voltava como
`Internal Server Error` em **texto puro** — a única resposta da API fora do próprio contrato, e
justamente a que aparece quando o banco cai. Pelo mesmo motivo, `404` e `405` respondiam `"Not
Found"` e `"Method Not Allowed"`: as únicas strings em inglês de um sistema em que até a rota de
saúde é `/saude`, e as primeiras que alguém encontra explorando o `/docs`.

O corpo do `500` **não** carrega a causa. Mensagem de exceção traz host, usuário e nome de tabela com
frequência demais para virar resposta HTTP; o rastro inteiro vai para o log, e um teste garante que
nem o IP nem a senha do texto de exemplo aparecem no corpo.

**O que caiu:** **deixar o `500` como estava e corrigir o README**, que é a alternativa honesta e
custava uma frase. Perdeu porque a promessa era a decisão certa — o frontend tem um caminho só para
tratar erro justamente por causa dela —, e era a implementação que estava incompleta. Caiu também
**devolver a mensagem da exceção no corpo** para facilitar o diagnóstico: ajuda quem depura e entrega
o interior do sistema para qualquer um que provoque uma falha.

### A trava do banco de teste roda antes do `DROP`, não depois

**Decidi** verificar o nome do banco dentro da fixture de sessão, antes do `alembic downgrade base`.

**Por quê:** eu já tinha um teste chamado `test_banco_de_teste_e_o_rockhub_teste`, e ele me dava uma
sensação de segurança que não existia — **teste roda depois da fixture**, e a fixture começa
apagando as tabelas. Ele relatava o desastre em vez de impedi-lo. O cenário concreto: `DATABASE_URL_TESTE`
exportada apontando para a Railway (é a variável mais fácil de errar, porque o `.env.example`
documenta o formato dela ao lado do de produção), um `uv run pytest` distraído, e o banco de produção
migrado do zero. A verificação é pelo **nome** do banco e não pelo host, porque `localhost` não
garante nada — um túnel de porta aponta para qualquer lugar.

**O que caiu:** **confiar no teste que já existia**, que é o que eu estava fazendo. E **conferir o
host em vez do nome**, que parece mais rigoroso e é mais fácil de furar.

### O favicon é a identidade reduzida a uma letra

**Decidi** trocar o `favicon.ico` do `create-next-app` por um `icon.svg` próprio: "R" em âmbar
(`--ambar`) sobre o breu (`--breu`), na serifada do sistema.

**Por quê:** o arquivo do scaffold era o triângulo da Vercel, e ele sobreviveu até a Story 1.9 — a
marca de outro produto na aba do navegador do projeto que está sendo avaliado, presente em qualquer
screenshot. A redução carrega os dois marcadores da identidade e nada mais: o preto quente e o âmbar,
na voz serifada. Uma letra só, porque 16px não comporta o fio duplo do masthead nem a palavra inteira
— a essa altura qualquer estrutura vira borrão. É SVG e não `.ico` porque o formato aceita as fontes
de sistema, e nenhuma fonte é baixada aqui também (UX-DR2).

**O que caiu:** **apagar o arquivo e não pôr nada**, que já seria melhor que exibir a marca errada e
custava zero. Perdeu por meio grau de acabamento numa peça que aparece em toda captura de tela. Caiu
também **um símbolo desenhado** em vez da letra: qualquer forma que eu inventasse seria vocabulário
novo, e a identidade deste projeto é tipográfica de ponta a ponta.

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
| **Limite de tentativas de login** | Não há bloqueio por IP nem por conta depois de N senhas erradas. É a defesa direta contra força bruta, e ficou de fora conscientemente: exige contador com expiração compartilhado entre instâncias, que é infraestrutura demais para o prazo. O que **está** feito é o custo de ~50ms por tentativa (Argon2id) e a resposta idêntica para e-mail inexistente e senha errada, inclusive no tempo |
| **Recuperação de senha** | O enunciado dispensa, e exigiria envio de e-mail — serviço externo, mais uma credencial e mais um fluxo para testar. É por não existir que o cadastro tem campo de confirmação de senha: sem ela, uma letra errada seria conta perdida para sempre |
| **Cadastro de organizador pela interface** | **Adiado, não descartado.** Toda conta criada em `/cadastro` nasce `CLIENTE`, e não há seletor de papel — um seletor numa tela pública seria escalada de privilégio com cara de formulário. A rota separada faz sentido, mas sem uma forma de decidir quem merece o papel (aprovação manual, verificação de CNPJ) ela seria o mesmo buraco com outro endereço. Organizador nasce pelo seed de [Contas semeadas](#contas-semeadas), que é como o próprio enunciado o pede. **Portaria fica de fora em qualquer cenário**, e não por prazo: pelo AD-7 ela só valida onde foi escalada por um organizador, então conta de portaria autocriada não estaria ligada a evento nenhum |
| **Evento publicado entre os dados semeados** | O enunciado pede um evento já publicado junto das quatro contas, e ele **ainda não é semeado**: `Evento` e `Setor` só passam a existir na Story 2.3, e não há como semear tabela que não existe. A dívida está registrada aqui de propósito, e o seed da Epic 2 acrescenta o evento ao mesmo `backend/seeds/`. A alternativa — o avaliador publicar pela interface — mostraria o fluxo do organizador funcionando, mas travaria o roteiro no primeiro passo se a Ticketmaster estivesse fora do ar naquele minuto |
| **Enumeração de e-mail no cadastro** | O `409 EMAIL_JA_CADASTRADO` revela que aquele e-mail tem conta — exatamente o que o login gasta um hash fantasma para não revelar. É inevitável aqui: o login pode esconder porque as duas respostas cabem numa frase só ("e-mail **ou** senha incorretos"), e o cadastro não tem essa saída — ou ele diz que o e-mail já existe, ou mente para quem está tentando criar a conta. A mitigação padrão é responder sempre "enviamos um e-mail para você" e resolver a diferença por fora, o que exige verificação por e-mail, que está fora do escopo. O que continua valendo: o login não entrega a lista de graça — quem quiser precisa passar pelo cadastro, um e-mail por vez |
| **Login que encaminha por papel** | Entrar leva para a raiz, ou para o `?voltar=` quando a pessoa veio de uma página protegida. Encaminhar organizador e portaria para as telas deles depende dessas telas existirem (Epics 2 e 5); inventar a rota antes só produziria um 404 |
| **`Meus ingressos` no masthead** | **Saiu na Story 1.6, e volta na Epic 4** — junto da tela que ele abre. O masthead nasceu na 1.2 com três links, dois deles caindo no 404; a 1.6 criou a `/conta` e removeu o que ainda não existe. É o precedente que firmei na 1.4: link que cai no 404 não fica no repositório. Pelo mesmo motivo não há `Meus eventos` para organizador nem `Turnos` para portaria — navegação diferente por papel nasce nas Epics 2 e 5, com as telas |
| **Editar a própria conta** | A `/conta` mostra nome, e-mail e papel, e permite sair. Trocar nome ou senha não é escopo de story nenhuma |
| **Ambiente separado para os Previews** | Os deploys de branch da Vercel apontam para o **mesmo banco de produção**, porque o `API_URL` está definido com o mesmo valor em Production e Preview. Uma conta criada num Preview é uma conta no banco real. A alternativa — definir a variável só para Production — deixaria todo Preview com o login quebrado em silêncio, que é pior; e um segundo serviço Railway com banco próprio é infraestrutura que não se paga em sete dias. A mitigação que existe hoje: no plano Hobby os Previews ficam atrás do login da Vercel, então não são endereço público |
| **Domínio próprio** | A aplicação vive em `elite-dev-rock-hub.vercel.app` e a API em `elite-dev-rockhub-production.up.railway.app`. Domínio custa dinheiro e propagação de DNS, e não acrescenta nada ao que está sendo avaliado |
| **Branch de produção alinhada com a `main`** | Os dois painéis publicam a branch da epic, não a `main` — o merge vem depois do code review, e publicar da `main` hoje exigiria mesclar código não revisado. É um campo para trocar em dois painéis quando a Epic 1 entrar na `main`, e está escrito assim de propósito para não virar surpresa |
| **Integração contínua** | Não há GitHub Actions nem suíte rodando antes do deploy. Um push na branch publicada dispara o build direto, e quem garante que os testes passam sou eu, na minha máquina. CI aqui exigiria subir um PostgreSQL no runner, porque a suíte roda contra banco de verdade desde a Story 1.3 — é infraestrutura que não se paga em sete dias. O que existe no lugar: o `--locked` do build **falha** se o lockfile divergir do `pyproject.toml`, e a migração roda antes de a aplicação atender, então schema errado não entra no ar |
| **Teste automatizado no frontend** | Não há Vitest, Testing Library nem Playwright, e isso é decisão. As invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a primeira story. Em 7 dias, configurar teste de componente para cobrir markup que ainda vai mudar muito não se paga. O frontend é verificado por `npm run build`, `tsc --noEmit`, ESLint e conferência no navegador |
