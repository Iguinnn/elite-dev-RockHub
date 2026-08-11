---
baseline_commit: "bbc9916 — Story 1.7 (branch epic-1---fundacao-acesso-e-primeiro-deploy)"
---

# Story 1.8: Backend e banco no ar na Railway

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **A primeira story em que o entregável não é código.**
As 1.1 a 1.7 construíram um backend que sobe, migra, autentica e semeia — tudo em `localhost`. Esta
não acrescenta comportamento nenhum: ela muda **onde** o sistema roda, e prova que ele roda lá.

O trabalho está dividido em duas metades que não podem se misturar. A metade do **Igor** é clicar no
painel da Railway: criar o serviço, apontar para a pasta certa, colar as variáveis, escrever dois
comandos e gerar o domínio. A metade do **agente** é conferir por HTTP que o resultado responde, e
escrever nos READMEs o passo a passo exato que foi executado — porque quem avalia precisa poder
refazer isso na conta dele.

O repositório já vinha sendo preparado para este dia, em três stories diferentes: o `/saude` da 1.1
não toca banco de propósito, para servir de health check; a `Settings` da 1.4 normaliza
`postgres://` para `postgresql+psycopg://` porque é isso que a Railway injeta; e o seed da 1.7 nunca
apaga linha nenhuma porque roda a cada deploy. Se alguma dessas três não existisse, esta story seria
uma tarde de depuração em produção. Existindo, ela é configuração.

## Acceptance Criteria

1. **Given** o serviço do backend publicado na Railway
   **When** eu acesso `https://<dominio>/saude`
   **Then** responde `200` com `{"status": "ok"}`
   **And** `https://<dominio>/docs` lista `/auth/cadastro`, `/auth/login`, `/auth/logout` e
   `/auth/eu`

2. **Given** o projeto na Railway
   **When** eu inspeciono os serviços
   **Then** existe um **PostgreSQL provisionado lá**, e o `DATABASE_URL` do backend aponta para ele
   **And** o `docker-compose.yml` da raiz **não** participa de produção — ele existe só para o
   desenvolvimento local, e nada no painel o referencia

3. **Given** as variáveis de ambiente do serviço
   **When** eu as inspeciono
   **Then** `DATABASE_URL`, `JWT_SECRET`, `TICKET_SIGNING_SECRET` e `TICKETMASTER_API_KEY` existem
   **só lá** — `git grep` por qualquer um dos quatro valores no repositório devolve zero ocorrências
   **And** `AMBIENTE=producao` está definido, o que ativa o `Secure` do cookie e a recusa do
   `JWT_SECRET` de exemplo
   **And** **nenhum campo novo entrou na `Settings`** para acomodar `TICKET_SIGNING_SECRET` e
   `TICKETMASTER_API_KEY`: o `extra="ignore"` já os aceita sem lê-los, e quem os lê são as Stories
   3.9 e 2.1

4. **Given** um deploy novo
   **When** ele executa
   **Then** `alembic upgrade head` roda **antes** de a aplicação começar a atender requisição, como
   Pre-deploy Command
   **And** migração que falha **impede o deploy novo de entrar no ar** — a versão anterior continua
   servindo, em vez de o contêiner entrar em ciclo de reinício com o schema errado

5. **Given** o seed em produção
   **When** ele roda no mesmo Pre-deploy, depois da migração
   **Then** as quatro contas do NFR2 existem no banco da Railway, com as credenciais do README
   **And** um **redeploy posterior** não apaga nem altera conta criada por quem estiver avaliando —
   é a garantia que a Story 1.7 construiu, agora exercida onde ela importa

6. **Given** a imagem que o Railpack constrói
   **When** o Start Command e o Pre-deploy Command são executados
   **Then** eles chamam `uvicorn`, `alembic` e `python` **direto**, nunca `uv run`
   **And** o motivo está escrito no README: o Railpack instala o `uv` só na fase de build e põe
   `/app/.venv/bin` no `PATH` da imagem final — `uv run` ali falha com `uv: not found`

7. **Given** o serviço no ar
   **When** eu chamo `POST /auth/login` na URL pública com `organizador@rockhub.dev` / `rockhub123`
   **Then** responde `200` com `"papel": "ORGANIZADOR"`
   **And** o `Set-Cookie` traz `Secure`, `HttpOnly` e `SameSite=Lax` — o `Secure` é o que prova que
   `AMBIENTE=producao` chegou de fato à aplicação

8. **Given** o health check configurado no painel
   **When** um deploy sobe
   **Then** o caminho verificado é `/saude`, e não `/`
   **And** a aplicação escuta em `0.0.0.0` na porta de `$PORT` — a Railway injeta essa variável, e
   escutar em `127.0.0.1` ou em porta fixa produz `502 Application failed to respond`

9. **Given** os três READMEs
   **When** eu os leio
   **Then** o README do backend tem uma seção **Deploy na Railway** com os campos do painel,
   valores e ordem, refazível numa conta vazia
   **And** o README da raiz publica a URL da API e registra as decisões desta story com a
   alternativa descartada
   **And** está escrito que o frontend ainda **não** está publicado, e que `CORS_ORIGENS` e
   `API_URL` só ganham valor de produção na Story 1.9

10. **Given** o repositório ao fim desta story
    **When** eu comparo com o estado anterior
    **Then** **nenhuma linha de `app/`, `migrations/`, `seeds/` ou `tests/` mudou**
    **And** não existe `railway.json`, `railway.toml`, `Dockerfile`, `Procfile` nem script de
    release novo — a configuração mora no painel, por decisão registrada
    **And** os 85 testes continuam passando sem alteração

> **De onde vem cada critério.** Os ACs **1 a 5** são os cinco blocos do `epics.md`, com os nomes
> reais dos campos do painel e a distinção entre "deploy barrado" e "contêiner em crash-loop", que é
> a diferença prática entre as duas formas de rodar a migração.
>
> **AC6** existe porque é o erro que esta story quase cometeu: a recomendação inicial usava
> `uv run`, e a leitura do provider Python do Railpack mostrou que o `uv` não sobrevive ao build.
> Sem esse AC, o primeiro deploy falharia num `uv: not found` que não aponta para causa nenhuma.
>
> **AC7 e AC8** são a prova de que a configuração *chegou* na aplicação. `Secure` no cookie é o
> único sintoma observável de fora de que `AMBIENTE=producao` está valendo; `0.0.0.0` + `$PORT` é a
> causa mais comum de `502` na Railway, e é erro de configuração, não de código.
>
> **AC9** é a NFR1 e a regra do `CLAUDE.md`. **AC10** é a fronteira: esta story não tem por que tocar
> em código, e código que aparecer aqui é sinal de que alguma coisa foi resolvida no lugar errado.

## Tasks / Subtasks

> **Ordem obrigatória.** A T1 é do Igor e acontece **antes** de tudo: sem o domínio público, não há
> o que verificar na T2 nem o que documentar na T4. O agente começa pela T2, com a URL em mãos.

- [x] **T1. Configurar o serviço na Railway** — *executada pelo Igor, no painel* (AC: 1, 2, 3, 4, 5, 8)
  - [x] **Dois pré-requisitos de git, antes de abrir o painel** (e os dois são seus, não do agente):
        o repositório precisa estar **no GitHub** — é de lá que a Railway lê —, e a **branch que a
        Railway vai acompanhar** precisa conter o código da Epic 1. Hoje isso é
        `epic-1---fundacao-acesso-e-primeiro-deploy`, não a `main`: apontar para a `main` publicaria
        um repositório sem backend nenhum, e o sintoma seria um build que não encontra
        `pyproject.toml`. Se você preferir publicar a `main`, faça o merge da epic antes
  - [x] O passo a passo completo, campo por campo, está em *O painel da Railway, campo por campo*
  - [x] Ao terminar, passe ao agente: a **URL pública** gerada e o **nome do serviço Postgres**
  - [x] Se algum passo falhar, mande o print — a leitura do log de deploy está em *Quando falhar,
        onde olhar*

- [x] **T2. Verificar o que está no ar** (AC: 1, 3, 5, 7, 8)
  - [x] `curl -i https://<dominio>/saude` → `200 {"status":"ok"}`
  - [x] `curl -i https://<dominio>/docs` → `200`, e o `/openapi.json` lista as quatro rotas de auth
  - [x] `POST /auth/login` com **cada uma** das quatro credenciais semeadas → `200` com o papel da
        tabela. É o que prova, de uma vez, que a migração rodou, que o seed rodou e que o banco é o
        da Railway
  - [x] No `Set-Cookie` do login: `HttpOnly`, `SameSite=Lax` **e `Secure`**. Sem o `Secure`,
        `AMBIENTE` não chegou como `producao` — pare e corrija antes de documentar
  - [x] `curl -i https://<dominio>/auth/eu` **sem cookie** → `401` com `NAO_AUTENTICADO`
  - [x] `curl -i https://<dominio>/rota-que-nao-existe` → `404` no formato `{"erro":{...}}`, que é o
        handler da 1.1 valendo em produção
  - [x] ⚠️ **Não crie conta pela API de produção para "testar"** sem necessidade. Se criar, deixe
        anotado — a conta fica, porque o seed não apaga nada
  - [x] Peça ao Igor que **rode um redeploy** e repita o login das quatro contas: é o AC5 exercido
        onde ele vale. A conferência do painel é dele; a do HTTP é sua

- [x] **T3. `backend/.env.example`** (AC: 3, 9)
  - [x] Acrescente, ao fim, um bloco comentado **"Em produção (Railway)"** listando as variáveis que
        existem só lá: `AMBIENTE=producao`, `DATABASE_URL` (injetada por referência ao serviço
        Postgres), `JWT_SECRET`, `TICKET_SIGNING_SECRET`, `TICKETMASTER_API_KEY`
  - [x] ⚠️ **Nenhum valor real.** O arquivo é versionado; ele lista **nomes** e diz onde o valor
        mora. É a mesma regra desde a 1.1
  - [x] Deixe escrito que `DATABASE_URL_TESTE` **não** existe em produção: `pytest` não roda lá, e o
        Railpack instala com `--no-dev`, então o `pytest` sequer está na imagem

- [x] **T4. `backend/README.md`** (AC: 6, 8, 9)
  - [x] Seção nova **Deploy na Railway**, depois de *Testes*: a tabela de campos do painel, as
        variáveis, os dois comandos e o health check. O conteúdo está em *O painel da Railway, campo
        por campo* — copie de lá, é para isso que ele existe
  - [x] Subseção **Por que os comandos não usam `uv run`** — o AC6 explicado em três linhas, com o
        que acontece se alguém "corrigir" para `uv run`
  - [x] Subseção **Como o banco é alcançado**: variável de referência, rede privada, e o que fazer
        quando o Postgres está em **outro projeto** da Railway
  - [x] *Configuração*: a tabela de variáveis ganha uma coluna ou uma nota dizendo quais têm valor
        próprio em produção. `TICKET_SIGNING_SECRET` e `TICKETMASTER_API_KEY` entram como
        **definidas no ambiente, ainda não lidas pela `Settings`** — com as stories que as leem
  - [x] Entrada **Story 1.8** no *Histórico desta camada*, em primeira pessoa

- [x] **T5. `README.md` da raiz** (AC: 9)
  - [x] *Estado atual*: acrescente que a API está publicada, com a URL, e que o frontend ainda não
  - [x] Seção nova (ou bloco em *Como executar*) **No ar**: a URL da API e o que dá para abrir nela
        hoje — `/saude` e `/docs`. Diga que o frontend publicado é a Story 1.9
  - [x] *Contas semeadas*: uma linha dizendo que as mesmas quatro contas existem também no banco da
        Railway, criadas pelo mesmo comando a cada deploy
  - [x] *Roteiro de avaliação*: um item novo — abrir `/saude` e `/docs` na URL pública e entrar com
        uma conta semeada por lá, sem instalar nada. **Sem prometer as telas**: elas só chegam na 1.9
  - [x] *Stack e estrutura*: a linha `Deploy | Railway ... *(Stories 1.8 e 1.9)*` perde o "1.8"
  - [x] *Decisões*: **três** entradas novas, cada uma com o que caiu e por quê — Railpack em vez de
        Dockerfile; migração no Pre-deploy em vez de encadeada no start; configuração no painel em
        vez de `railway.json` versionado. Matéria-prima em *Decisões que o Igor tomou*
  - [x] *O que não está pronto*: a linha do **frontend ainda não publicado** (Story 1.9) e a de que
        **não há CI** — o deploy dispara por push na branch, sem suíte rodando antes
  - [x] **Primeira pessoa, como o Igor escrevendo**

- [x] **T6. `frontend/README.md`** (AC: 9)
  - [x] Entrada curta: esta story **não tocou no frontend**, e o `API_URL` local continua apontando
        para `localhost:8000`. O valor de produção — a URL da Railway — entra na Story 1.9, junto do
        deploy na Vercel, e é lido em **tempo de build** pelo `rewrites()`, o que significa que
        trocá-lo depois exige redeploy
  - [x] Não invente mudança que não houve

- [x] **T7. Verificação** (AC: todos)
  - [ ] `uv run pytest` local → 85 testes verdes, sem alteração (contorno nesta máquina:
        `uv run python -m pytest`). **Não re-executado:** nenhum arquivo `.py` mudou nesta story, e
        a suíte exige `docker compose up -d`, que eu não subo sem o Igor pedir. Fica para ele
  - [x] Peça ao Igor que confirme no log do Pre-deploy do **próximo deploy** que as quatro linhas do
        seed dizem `mantida` — o push do commit desta story dispara esse deploy sozinho
  - [x] Busca no repositório por `railway.json`, `railway.toml`, `Dockerfile`, `Procfile` → zero
  - [x] Busca por `git diff` mental: `backend/app/`, `backend/migrations/`, `backend/seeds/`,
        `backend/tests/` e `frontend/src/` **não aparecem** na lista de arquivos alterados
  - [x] Busca pelos valores reais de `JWT_SECRET` e `TICKET_SIGNING_SECRET` no repositório → zero
  - [x] Os três READMEs atualizados

- [x] **T8. Documentação** — coberta por T3, T4, T5 e T6 (obrigatório — regra do projeto)

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T5).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Como a imagem é construída | **Railpack**, o builder padrão da Railway, sem arquivo novo no repositório | *`Dockerfile` próprio a partir da imagem oficial do `uv`*: build idêntico aqui e lá, imune a mudança de heurística do fornecedor — caiu porque é um arquivo a mais para manter e para quem avalia entender, e o Railpack já lê `pyproject.toml`, `uv.lock` e o `.python-version` que estão lá desde a 1.1. *Nixpacks explícito*: o builder anterior, ainda selecionável, mas com suporte a `uv` mais frágil e já fora do padrão |
| Onde rodam migração e seed | **Pre-deploy Command** da Railway | *Encadeado no Start Command* (`sh -c "alembic … && seed && uvicorn"`): funciona em qualquer plataforma e não depende de recurso do fornecedor — caiu porque roda a cada réplica e a cada reinício automático, e migração quebrada vira contêiner em ciclo de reinício, derrubando a API que estava no ar, em vez de barrar o deploy novo. *Script de release versionado* chamado pelo Pre-deploy: o conteúdo ficaria legível no repositório, ao custo de um arquivo que duplica o que o painel já mostra |
| Onde mora a configuração do serviço | **No painel da Railway**, documentada no README | *`railway.json` versionado*: recriar o serviço viraria reimportar o repositório, e quem avalia leria a configuração do deploy junto do código — caiu porque o painel sobrescreve o arquivo quando alguém edita por lá, e duas fontes para a mesma verdade divergem em silêncio. O custo assumido: a configuração some se o serviço for apagado, e é por isso que o README a descreve campo por campo |
| `TICKET_SIGNING_SECRET` e `TICKETMASTER_API_KEY` | **Só no painel; a `Settings` não muda** | *Acrescentar os dois campos à `Settings` agora*, com valor de exemplo e a mesma recusa em produção do `JWT_SECRET`: provaria o contrato completo de segredos hoje — caiu porque é código que nada lê até a Epic 2, e um valor de exemplo recusado derrubaria a aplicação por causa de uma funcionalidade que ainda não existe. *Adiar as duas variáveis para as stories delas*: mais honesto com o escopo, e deixaria um AC do `epics.md` em aberto na entrega da epic |

**Duas suposições declaradas, não decisões suas** — uma linha para trocar se discordar:

- **`CORS_ORIGENS` fica no padrão** (`http://localhost:3000`) até a Story 1.9. Desde o proxy da 1.4
  o navegador não fala com a Railway diretamente, então CORS não está no caminho de nada que exista
  hoje. A URL da Vercel entra lá quando existir
- **`TICKETMASTER_API_KEY` pode entrar com valor provisório** se você ainda não tiver a chave da
  Ticketmaster. O AC3 é sobre a variável existir **só no ambiente**, nunca no repositório — e a
  Story 2.1 é quem passa a lê-la

### O painel da Railway, campo por campo

Esta seção é a matéria-prima da T4: ela vai para o `backend/README.md` quase como está.

**Antes de começar.** Você já tem um PostgreSQL na Railway. A primeira coisa a descobrir é se ele
está **no mesmo projeto** em que o backend vai morar — isso decide como o banco é alcançado, e é a
única bifurcação real deste roteiro.

#### 1 · O serviço do backend

| Onde | Campo | Valor |
|---|---|---|
| `New` → `GitHub Repo` | repositório | `elite-dev-RockHub` |
| Settings → Source | **Root Directory** | `backend` |
| Settings → Source | Branch | a branch que você quiser publicar |
| Settings → Build | Builder | `Railpack` (padrão — não precisa mexer) |

⚠️ **O `Root Directory` é o passo que não pode faltar.** Sem ele a Railway tenta construir a raiz do
monorepo, encontra `frontend/package.json` junto de `backend/pyproject.toml` e constrói a coisa
errada — ou nada. Com `backend`, o `/app` da imagem é o conteúdo de `backend/`, que é exatamente o
diretório de onde todos os comandos deste projeto são rodados desde a 1.1.

#### 2 · As variáveis

| Variável | Valor | Por quê |
|---|---|---|
| `AMBIENTE` | `producao` | Ativa o `Secure` no cookie e a recusa do `JWT_SECRET` de exemplo |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Referência ao serviço Postgres — ver a bifurcação abaixo |
| `JWT_SECRET` | um valor gerado, só seu | Sem ele a aplicação **não sobe**, de propósito (1.4) |
| `TICKET_SIGNING_SECRET` | outro valor gerado | Ainda não lido; a Story 3.9 o consome |
| `TICKETMASTER_API_KEY` | a chave da Ticketmaster | Ainda não lida; a Story 2.1 a consome |

Gere os dois segredos com valores **diferentes** — são propósitos diferentes, e reaproveitar um
segredo faz com que trocar um obrigue a trocar o outro:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

⚠️ **Defina as variáveis antes do primeiro deploy.** O Pre-deploy Command importa
`app.core.config`, e a `Settings` recusa o `JWT_SECRET` de exemplo quando `AMBIENTE=producao`. Se
faltar `JWT_SECRET`, o deploy falha na **migração**, com uma mensagem sobre segredo — e você vai
procurar o problema no banco.

**A bifurcação do banco:**

- **Postgres no mesmo projeto e ambiente** → use a variável de referência
  `${{Postgres.DATABASE_URL}}` (troque `Postgres` pelo nome exato do serviço). Ela resolve para o
  host interno `postgres.railway.internal`, que não passa pela internet e não consome egress
- **Postgres em outro projeto** → a rede privada **não** atravessa projetos. Copie o valor de
  `DATABASE_PUBLIC_URL` do serviço de banco e cole como `DATABASE_URL` do backend. Funciona, é mais
  lento e passa pela internet — se incomodar, mova o banco para o mesmo projeto e volte à referência

Nos dois casos a URL chega como `postgresql://…`, e a `Settings` a normaliza para
`postgresql+psycopg://` — é o validador que a Story 1.4 escreveu **exatamente** para este dia.

#### 3 · Os dois comandos

| Onde | Campo | Valor |
|---|---|---|
| Settings → Deploy | **Pre-deploy Command** | `alembic upgrade head && python -m seeds.semear` |
| Settings → Deploy | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Settings → Deploy | **Healthcheck Path** | `/saude` |

⚠️ **Sem `uv run` em nenhum dos dois.** O Railpack instala o `uv` só na fase de build; a imagem
final recebe `/app/.venv/bin` no `PATH` e **não** recebe o binário do `uv`. `uv run alembic …` ali
falha com `uv: not found`. Os executáveis `alembic`, `uvicorn` e `python` estão no `PATH` porque
vêm da virtualenv — é a mesma virtualenv, alcançada de outro jeito.

Três detalhes que sustentam esses comandos:

- **`--host 0.0.0.0`** — escutar em `127.0.0.1` produz `502 Application failed to respond`, porque
  o proxy da Railway não alcança a aplicação. É a causa nº 1 de 502 lá
- **`--port $PORT`** — a Railway injeta `PORT`; porta fixa dá o mesmo `502`
- **`python -m seeds.semear`, com o `-m`** — a mesma armadilha da Story 1.7, agora em produção:
  executar o arquivo direto põe `/app/seeds` no caminho de import em vez de `/app`, e `import app`
  para de resolver

#### 4 · O domínio

Settings → Networking → Public Networking → **Generate Domain**. Sai algo como
`rockhub-backend-production.up.railway.app`. É essa URL que vai para os READMEs e, na Story 1.9,
para o `API_URL` da Vercel.

#### 5 · A conferência

Com o deploy verde, o log do Pre-deploy precisa mostrar as duas coisas, nesta ordem: as migrações do
Alembic e as quatro linhas do seed. Na **primeira** vez elas dizem `criada`; em **todo redeploy
seguinte**, `mantida`. Ver `mantida` a partir do segundo deploy é a prova, em produção, da story
anterior inteira.

### Quando falhar, onde olhar

Em ordem de probabilidade, com o sintoma que cada uma produz:

1. **`uv: not found` no Pre-deploy ou no start.** Alguém escreveu `uv run`. Tire o `uv run`
2. **Build constrói a coisa errada ou não encontra `pyproject.toml`.** Falta o `Root Directory =
   backend`
3. **`502 Application failed to respond`.** `--host 0.0.0.0` ou `--port $PORT` ausentes. O deploy
   fica verde e a URL não responde — é o sintoma que mais engana
4. **Deploy falha na migração com mensagem sobre `JWT_SECRET`.** As variáveis não foram definidas
   antes do primeiro deploy. Não é problema de banco
5. **`could not translate host name "postgres.railway.internal"`.** O Postgres está em outro
   projeto, ou a referência aponta para um nome de serviço que não existe. Confira o nome exato do
   serviço e considere `DATABASE_PUBLIC_URL`
6. **`ModuleNotFoundError: No module named 'psycopg2'`.** A `DATABASE_URL` chegou como
   `postgresql://` **e** a normalização da `Settings` não rodou — o que só acontece se alguém a
   tiver removido. Ela existe desde a 1.4 exatamente para isso
7. **`uv sync --locked` falha no build.** O `uv.lock` está fora de sincronia com o
   `pyproject.toml`. Rode `uv sync` localmente e comite o lockfile. Não deve acontecer nesta story:
   nenhuma dependência muda
8. **Health check falhando com a aplicação de pé.** O caminho é `/saude`, não `/` — a raiz da API
   responde `404` de propósito

### O que já existe e esta story reusa — não reescreva nada disto

| O que | Onde | Por que importa hoje |
|---|---|---|
| `GET /saude` sem banco | `app/api/saude.py` | É o health check. O docstring já diz que não toca banco de propósito |
| Normalização de `postgres://` | `app/core/config.py` | Traduz a URL que a Railway injeta para o driver psycopg 3 |
| Recusa do `JWT_SECRET` de exemplo | `app/core/config.py` | A trava que impede subir em produção com segredo público |
| `cookie_secure` derivado de `AMBIENTE` | `app/core/config.py` | Não é campo configurável — ninguém o desliga por engano no painel |
| Seed idempotente | `seeds/semear.py` | Roda a cada deploy e nunca apaga nada. É a Story 1.7 inteira |
| `extra="ignore"` na `Settings` | `app/core/config.py` | É o que deixa `TICKET_SIGNING_SECRET` e `TICKETMASTER_API_KEY` existirem no ambiente sem campo correspondente |
| `.python-version` = `3.12` | `backend/.python-version` | O Railpack o lê via mise; sem ele, cairia no padrão 3.13 |
| `prepend_sys_path = .` | `backend/alembic.ini` | É o que faz `alembic upgrade head` encontrar `app.core.config` a partir de `/app` |

**Não devem ser tocados, e não devem quebrar:** `backend/app/` **inteiro**, `backend/migrations/`,
`backend/seeds/`, `backend/tests/`, `backend/pyproject.toml`, `backend/uv.lock` (**nenhuma
dependência nova**), `docker-compose.yml`, `docker/` e o `frontend/` inteiro. Os arquivos que mudam
são quatro, e são de documentação: `backend/.env.example`, `backend/README.md`, `README.md` da raiz
e `frontend/README.md`.

Se algum arquivo de `app/` precisar mudar para o deploy funcionar, algo foi resolvido no lugar
errado — o lugar é o painel.

### O que o Railpack faz com este projeto

Lido no provider Python do Railpack, não deduzido:

| Fase | O que acontece |
|---|---|
| Detecção | Encontra `pyproject.toml`; identifica `uv` pelo `uv.lock` |
| Versão do Python | Lê `.python-version` via mise → **3.12**. (Sem esse arquivo, o padrão seria 3.13) |
| Install | `uv sync --locked --no-dev --no-install-project` |
| Build | `uv sync --locked --no-dev --no-editable` |
| Ambiente | `VIRTUAL_ENV=/app/.venv`, `PATH` com `/app/.venv/bin`, `UV_COMPILE_BYTECODE=1`, `PYTHONUNBUFFERED=1` |
| Imagem final | Contém a virtualenv. **Não contém o `uv`** |
| Workdir | `/app` — que, com `Root Directory = backend`, é o conteúdo de `backend/` |

Três consequências que valem para os comandos:

- **`--no-dev`**: `pytest` e `httpx` não sobem para produção. A suíte não roda lá, e não deve —
  ela apagaria e recriaria o banco de teste, que não existe naquele servidor
- **`--locked`**: o build **falha** se o `uv.lock` divergir do `pyproject.toml`. É uma garantia de
  graça: a versão que sobe é literalmente a que está travada no repositório
- **workdir `/app`**: `uvicorn` insere o diretório corrente no `sys.path` (é o `--app-dir`, que já
  vem como `.`), o Alembic tem o `prepend_sys_path = .`, e `python -m` põe o corrente no caminho.
  Os três comandos encontram `app` e `seeds` sem nenhuma variável de ambiente extra

### Por que o Pre-deploy e não o start

O Pre-deploy Command roda **num contêiner separado**, com as variáveis de ambiente do serviço,
depois do build e antes de o tráfego ser trocado para a versão nova. Se ele sair diferente de zero,
**não é repetido e o deploy não prossegue** — a versão anterior continua atendendo.

É essa frase que atende o AC4 literalmente. A alternativa encadeada no Start Command não a atende:
lá a migração roda dentro do contêiner da aplicação, uma vez por réplica e outra a cada reinício
automático, e uma migração quebrada tira do ar a versão que estava funcionando.

Há uma restrição do Pre-deploy que este projeto respeita sem esforço: ele não deve ler nem escrever
em volume. O nosso escreve no Postgres, que é serviço à parte.

E há uma consequência boa do seed rodar ali: o log do Pre-deploy é onde as quatro linhas
`criada`/`mantida` aparecem. É por isso que a Story 1.7 decidiu **não imprimir a senha** — o que o
comando escreve vai para o log de deploy da Railway.

### Armadilhas específicas desta story

1. **`uv run` nos comandos do painel.** A primeira, a mais provável e a que o AC6 existe para
   impedir. Vale inclusive se você copiar comando de outro projeto Python na Railway
2. **Esquecer o `Root Directory`.** Monorepo com duas linguagens: sem ele o build é loteria
3. **Escutar em `127.0.0.1`.** Deploy verde, URL morta, `502`. Nada no log acusa
4. **Definir as variáveis depois do primeiro deploy.** O erro sai na migração e fala de segredo
5. **Assumir que a rede privada atravessa projetos.** Não atravessa. É o caso mais provável aqui,
   porque o banco já existia antes desta story
6. **"Rodar a suíte no deploy para garantir".** `--no-dev`: `pytest` não está na imagem. E se
   estivesse, a fixture derruba e recria o banco pelo Alembic — contra o `DATABASE_URL` que
   estivesse configurado
7. **Corrigir alguma coisa em `app/` para o deploy passar.** Se aparecer essa vontade, o problema é
   de configuração. A única exceção legítima seria um comportamento que não existe no código, e
   nesta story não há nenhum
8. **Publicar a URL nos READMEs antes de conferir o login.** URL no README que devolve `502` é pior
   que README sem URL
9. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** `uv run pytest` falha
   com `os error 4551`; o contorno é `uv run python -m pytest`. Vale só para a verificação local

### Convenções que esta story confirma ou cria

- **Configuração de plataforma mora na plataforma, e o README a descreve.** Vale para a Vercel na
  Story 1.9: mesma forma, mesma seção, mesmo nível de detalhe
- **Comando de produção chama o executável direto**, nunca através de um gerenciador de pacotes que
  pode não estar na imagem
- **Segredo novo nasce como variável no painel; campo na `Settings` só quando alguém for lê-lo.**
  É o que impede código morto com validação ativa
- **Deploy que falha na migração não entra no ar.** Nunca "sobe e corrige depois"
- **Nada de valor real de segredo no repositório**, nem em `.env.example`, nem em README —
  incluindo os dois segredos que ainda não são lidos por ninguém

### Estrutura alvo ao fim desta story

```text
backend/
  .env.example              # +bloco comentado "Em produção (Railway)"
  README.md                 # +Deploy na Railway, +por que não `uv run`, +histórico
README.md                   # +No ar (URL), roteiro, 3 decisões, o que não está pronto
frontend/README.md          # nota curta: esta story não tocou aqui; API_URL é da 1.9
```

Quatro arquivos, todos de documentação. `app/` não aparece nesta lista — é a segunda story seguida
em que isso acontece, e aqui é ainda mais forte: nem `seeds/` nem `tests/` mudam.

Não existe, e não deve passar a existir: `railway.json`, `railway.toml`, `backend/Dockerfile`,
`Procfile`, `.github/workflows/`. Cada um desses foi considerado e descartado, e o motivo do
primeiro está em *Decisões que o Igor tomou*.

[Fonte: ARCHITECTURE-SPINE.md#Implantação — Vercel → Railway → Postgres, com a chave da Ticketmaster
só no ambiente da Railway (AD-2)]

### Comandos que esta story precisa deixar funcionando

Na Railway (configurados no painel, não rodados por você):

```bash
alembic upgrade head && python -m seeds.semear      # Pre-deploy
uvicorn app.main:app --host 0.0.0.0 --port $PORT    # Start
```

Na sua máquina, para verificar o que está no ar:

```bash
curl -i https://<dominio>/saude
curl -i -X POST https://<dominio>/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

E o desenvolvimento local segue **exatamente igual** ao que os READMEs já descrevem — `docker
compose up -d`, `uv sync`, `alembic upgrade head`, `seeds.semear`, `uvicorn --reload`. Esta story
não muda um passo sequer disso, e é bom que não mude: dois jeitos de rodar o mesmo projeto é como
eles divergem.

Nada de `uv sync` nem de `npm install`: **nenhuma dependência nova**. É a quarta story seguida.

### Escopo — o que NÃO fazer aqui

Deploy do frontend na Vercel e `CORS_ORIGENS`/`API_URL` de produção (**Story 1.9**) · qualquer
funcionalidade nova · CI, GitHub Actions, teste rodando no deploy (**nenhuma story**) · domínio
próprio, TLS customizado, observabilidade, rate limiting (**fora do escopo do projeto**) · alterar
`app/`, `migrations/`, `seeds/` ou `tests/`.

Quatro tentações concretas desta story:

- **"Já que estou no deploy, ponho um CI que roda o pytest antes."** É story nenhuma, e a suíte
  exige Postgres no ar — o CI teria que subir um serviço. Fica em *O que não está pronto*, escrito
- **"Acrescento `/` respondendo alguma coisa, porque a raiz dá 404."** A raiz de uma API dar `404`
  está certo. O health check é `/saude`, e é isso que o painel aponta
- **"Ponho `CORS_ORIGENS` com `*` para não dar problema depois."** Curinga é incompatível com
  `allow_credentials=True` desde a 1.1, e o valor certo só existe na 1.9
- **"Crio o `railway.json` de qualquer jeito, não custa nada."** Custa: duas fontes para a mesma
  configuração, e o painel vence a arquivo quando alguém edita por lá

### Testing

**Nenhum teste novo, e nenhum teste alterado.** Esta story não acrescenta comportamento — ela muda
onde o comportamento existente executa, e isso não é observável por `pytest`.

O que a substitui, e é o motivo de a T2 ser tão detalhada, é a **verificação por HTTP contra a URL
pública**. Ela prova, de fora, o que nenhum teste local prova:

| O que a chamada prova | AC |
|---|---|
| `GET /saude` → `200` | 1 |
| `GET /docs` e `/openapi.json` listam as quatro rotas de auth | 1 |
| `POST /auth/login` com as quatro credenciais → `200` com o papel certo | 5, 7 |
| ↳ ...o que só é possível se a migração rodou **e** o seed rodou **e** o banco é o da Railway | 2, 4, 5 |
| `Set-Cookie` com `Secure` | 3, 7 |
| `GET /auth/eu` sem cookie → `401 NAO_AUTENTICADO` | 7 |
| Rota inexistente → `404` no formato `{"erro":{...}}` | — (o handler da 1.1 em produção) |
| Redeploy → seed diz `mantida`, e as contas continuam entrando | 5 |

**Os 85 testes locais continuam passando sem alteração.** Nenhum arquivo de `app/`, `tests/`,
`seeds/` ou `migrations/` muda — se algum quebrar, esta story encostou onde não devia.

⚠️ **Não escreva teste que fale com a URL de produção.** Ele dependeria de rede e do estado do banco
de produção, falharia em avaliação offline, e gravaria dado real. A verificação de deploy é manual e
está registrada nas notas do agente; ela não vira suíte.

### Inteligência das stories anteriores

**Da 1.7 (a story imediatamente anterior — leia estas antes de tudo):**

- **O seed existe, é idempotente e nunca apaga nada.** Esta story é quem o chama a cada deploy — era
  literalmente a justificativa daquela decisão. Se o seed apagasse a tabela, esta story seria o
  desastre que ele foi escrito para evitar
- **O comando é `python -m seeds.semear`**, com o `-m`, rodado do diretório do projeto
- **O comando sai em `0` mesmo quando avisa sobre papel divergente** — e o motivo escrito lá era
  exatamente este Pre-deploy: sair diferente de zero por causa de um aviso barraria o deploy
- **A senha não vai para o stdout** porque o stdout do seed é o log de deploy da Railway
- **Sobra no banco de desenvolvimento do Igor:** a conta `avaliador.story17@exemplo.com`. Ela é
  local; não tem nada a ver com o banco de produção

**Da 1.4 (login), e é a mais importante para hoje:**

- **A `Settings` normaliza `postgres://` e `postgresql://` para `postgresql+psycopg://`**, com o
  comentário dizendo "sem esta normalização, o erro na Story 1.8 seria um `ModuleNotFoundError`".
  Este é o dia
- **O valor de exemplo do `JWT_SECRET` derruba a aplicação com `AMBIENTE=producao`**
- **`cookie_secure` é derivado de `AMBIENTE`**, não é campo — é por isso que o `Secure` no
  `Set-Cookie` serve de prova de que a variável chegou
- **O proxy `/api/*` do Next é o que faz o cookie `SameSite=Lax` funcionar entre Vercel e Railway.**
  Já está resolvido, no `next.config.ts`. **Não reabra essa discussão nesta story nem na 1.9** — o
  `ARCHITECTURE-SPINE.md#AD-15` diz isso com todas as letras

**Da 1.3 (banco):**

- **Toda mudança de schema é migração Alembic; nunca `create_all`.** É o que torna
  `alembic upgrade head` no Pre-deploy suficiente para criar o schema do zero num banco vazio
- **A migração foi exercitada de ida e volta a cada `pytest` desde então** — o `downgrade` testado é
  o que dá confiança de rodar `upgrade` contra um banco de produção sem ensaio

**Da 1.1 (backend):**

- **`/saude` não toca banco de propósito**, e o docstring já dizia "é o alvo do health check da
  Railway"
- **`app.main:app` é caminho fixo**, e o docstring diz que o deploy da Railway aponta para ele
- **Nenhum segredo versionado.** `.env.example` lista nomes, nunca valores

**Do estado do repositório:** branch `epic-1---fundacao-acesso-e-primeiro-deploy`, com a Story 1.7
commitada (`bbc9916`). As Stories 1.1 a 1.7 estão em `review` — o code review é ao fim da epic. 85
testes passando no backend. Restam a 1.8 e a 1.9 para fechar a Epic 1.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-7-*.md]

### Stack desta story

**Nenhuma dependência nova, e nenhuma versão a conferir no lockfile.** O que esta story precisa
saber é sobre a plataforma, não sobre biblioteca:

| O que | Versão / estado | Onde importa |
|---|---|---|
| Railpack | builder padrão da Railway em ago/2026 | Constrói a imagem; instala com `--no-dev` e não deixa o `uv` na imagem final |
| Python | 3.12, vindo do `.python-version` | Sem esse arquivo, o Railpack cairia no 3.13 |
| PostgreSQL | 16 local (Compose) · o da Railway é o que ela provisiona | O schema é criado pelo Alembic nos dois |
| uvicorn | 0.52.1 (lockfile) | Start Command, com `--host 0.0.0.0 --port $PORT` |
| Alembic | 1.19.1 (lockfile) | Pre-deploy Command |
| psycopg | 3.3.4 `[binary]` | Por isso a URL precisa ser `postgresql+psycopg://` |

[Fonte: ARCHITECTURE-SPINE.md#Stack, #Implantação · docs.railway.com/deployments/pre-deploy-command ·
railpack.com/languages/python]

### Project Structure Notes

Esta é a primeira story do projeto em que **o entregável principal não está no repositório** — ele
está numa conta de fornecedor. O repositório recebe a documentação daquilo, e essa assimetria é o
risco: é fácil terminar com um serviço no ar e um README que descreve outra configuração.

A defesa contra isso é a ordem das tasks. A T1 (painel) acontece primeiro, a T2 verifica por HTTP o
que de fato subiu, e só então a T4 escreve o README **a partir do que foi executado** — não a partir
do que se pretendia executar. Documentação de deploy escrita antes do deploy é ficção.

A segunda característica é a divisão de responsabilidade. O agente **não tem acesso ao painel da
Railway** e não deve fingir que tem: ele não pode criar serviço, colar variável nem gerar domínio.
O que ele pode, e deve, é verificar por HTTP e escrever. Se a story parecer bloqueada, o desbloqueio
é o Igor executar a T1 e passar a URL.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.8] — os cinco blocos de AC originais,
  incluindo "migração que falha impede o deploy de entrar no ar" e "o `docker-compose.yml` não é
  usado em produção"
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.9] — o que herda desta story: a URL da
  API vira o `API_URL` da Vercel, e o `CORS_ORIGENS` ganha a URL do frontend
- [Source: _bmad-output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR3 (frontend na
  Vercel, backend e banco na Railway, vale +1 ponto), NFR1 e NFR8
- [Source: ARCHITECTURE-SPINE.md#Implantação] — o diagrama Navegador → Vercel → Railway → Postgres,
  e a chave da Ticketmaster só no ambiente da Railway
- [Source: ARCHITECTURE-SPINE.md#AD-2] — segredo só no ambiente do backend
- [Source: ARCHITECTURE-SPINE.md#AD-15] — cookie `Secure` em produção, e a nota de que "as Stories
  1.8 e 1.9 herdam isso pronto — não reabram a discussão"
- [Source: _bmad-output/implementation-artifacts/1-7-dados-semeados-para-avaliacao.md] — o seed que
  este deploy chama, e o porquê de ele sair em `0` mesmo com aviso
- [Source: backend/app/core/config.py] — normalização de `postgres://`, recusa do segredo de
  exemplo, `cookie_secure`, `extra="ignore"`
- [Source: backend/app/api/saude.py] · [app/main.py] · [alembic.ini] · [.python-version]
- [Source: README.md#Decisões] — onde as três decisões desta story entram
- [Source: docs.railway.com/deployments/pre-deploy-command] — contêiner separado, acesso às
  variáveis, e "if your command fails, it will not be retried and the deployment will not proceed"
- [Source: docs.railway.com/guides/monorepo] — `Root Directory`, e o aviso de que ele **não** vale
  para o arquivo de configuração da Railway
- [Source: docs.railway.com/guides/fixing-common-errors] — bind em `0.0.0.0` e `$PORT` como causa
  nº 1 de `502`
- [Source: railpack.com/languages/python + provider Python do Railpack] — `uv sync --locked
  --no-dev`, `VIRTUAL_ENV=/app/.venv`, `.python-version` via mise, e o `uv` ausente da imagem final
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Não há `uv sync` nem `npm install` nesta story.** Se precisar do backend local para conferir
   alguma coisa, confirme com o Igor antes de `docker compose up`
3. **Atualize os três READMEs antes de dar a story por concluída.** As três entradas de decisão da
   T5 são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As quatro desta story já estão respondidas. Se aparecer uma
   quinta — domínio próprio, CI, região do banco, plano pago — pergunte em vez de escolher
5. **O agente não mexe no painel da Railway.** Nem pede credencial, nem sugere caminho por CLI
   autenticada. A T1 é do Igor, e o resultado dela chega como URL e print
6. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
7. **Não emende a próxima story** sem o Igor mandar — a 1.9 fecha a Epic 1, e o code review vem
   depois dela

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (1M) — `claude-opus-5[1m]`

### Debug Log References

Verificação por HTTP contra `https://elite-dev-rockhub-production.up.railway.app`:

- `GET /saude` → `200 {"status":"ok"}`, servido por `railway-hikari`
- `GET /docs` → `200`; `/openapi.json` lista `/saude`, `/auth/cadastro`, `/auth/login`,
  `/auth/logout`, `/auth/eu`
- `POST /auth/login` × 4 → `200` nas quatro, com Helena Marques/`ORGANIZADOR`,
  Bruno Tavares/`CLIENTE`, Marina Aoki/`CLIENTE`, Jonas Ribeiro/`PORTARIA`
- `Set-Cookie` em todas: `HttpOnly; Max-Age=28800; Path=/; SameSite=lax; **Secure**`
- `GET /auth/eu` sem cookie → `401 NAO_AUTENTICADO`
- `POST /auth/login` com senha errada → `401 CREDENCIAIS_INVALIDAS`
- `GET /rota-que-nao-existe` → `404` no formato `{"erro":{"codigo":"NAO_ENCONTRADO",...}}`
- Ausência confirmada de `railway.json`, `railway.toml`, `Dockerfile`, `Procfile` e `.github/`

No painel (executado pelo Igor): primeiro build **falhou** por falta de `Root Directory`, com o log
listando a raiz do monorepo e `railpack process exited with an error`; o mesmo build apontava para a
`main` (commit `d90076ae`, do planejamento), por ser a branch padrão. Corrigidos os dois campos, o
deploy passou, com o `uvicorn` reportando `0.0.0.0:8080` e o health check verde em `/saude`.

### Completion Notes List

- **O `uv` não sobrevive ao build do Railpack**, e essa foi a descoberta que mudou a story. O
  provider Python instala o `uv` só na fase de build e entrega ao contêiner de execução apenas a
  virtualenv, com `/app/.venv/bin` no `PATH`. Os comandos que eu tinha proposto usavam `uv run`
  — como no desenvolvimento local — e teriam falhado com `uv: not found`, um erro que não sugere
  causa nenhuma para quem conhece o projeto pelos comandos daqui. Corrigido antes do primeiro
  deploy, e virou o AC6 mais uma subseção do README do backend, porque é a primeira "correção" que
  alguém tentaria
- **Duas causas empilhadas no primeiro build vermelho**, e as duas estavam previstas na story:
  `Root Directory` ausente (o campo fica escondido em Settings → Source) e a Railway assumindo a
  branch padrão do repositório, que ainda não tem o backend. Ficaram documentadas com o sintoma
  exato de cada uma, porque o log não aponta nenhuma das duas
- **Três decisões anteriores foram tomadas para hoje e pagaram**: o `/saude` sem banco da 1.1 como
  alvo do health check, a normalização de `postgres://` da 1.4 traduzindo a URL que a Railway
  injeta, e a idempotência por consulta do seed da 1.7 — que agora roda a cada deploy contra o
  banco real. Nenhuma delas precisou ser descoberta no dia do deploy, que era exatamente o ponto de
  tê-las escrito antes
- **O AC5 não foi provado com conta de avaliador plantada.** Propus criar uma conta pela API de
  produção antes de um redeploy para exercer literalmente "redeploy não apaga conta de quem está
  avaliando"; o Igor não autorizou sujar o banco, e a prova ficou pelo teste em transação revertida
  da Story 1.7 mais as quatro linhas `mantida` que o próximo deploy vai imprimir. **O push do commit
  desta story dispara esse deploy sozinho** (Auto deploys ligado), então a confirmação é olhar o log
  do Pre-deploy depois de commitar
- **Fora de escopo, anotado e não corrigido:** o `404` de produção devolve
  `{"erro":{"codigo":"NAO_ENCONTRADO","mensagem":"Not Found"}}` — a mensagem é o texto padrão do
  Starlette, em inglês, destoando do UX-DR8. Vem da Story 1.1, não desta, e a decisão é do Igor
- **`uv run pytest` não foi re-executado.** Nenhum arquivo `.py` mudou, e a suíte exige
  `docker compose up -d`, que eu não subo sem pedido. Os 85 testes continuam válidos por construção:
  os quatro arquivos alterados são `.env.example` e três READMEs
- Nenhuma dependência nova, nenhuma migração, **nenhuma linha de `app/`, `migrations/`, `seeds/`,
  `tests/` ou `frontend/src/` alterada** — a estrutura alvo da story previa exatamente isso

### File List

**Modificados**

- `backend/.env.example`
- `backend/README.md`
- `README.md`
- `frontend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-8-backend-e-banco-no-ar-na-railway.md`

**Fora do repositório** — serviço `elite-dev-RockHub` no projeto `diplomatic-upliftment` da Railway,
ambiente `production`, ao lado do serviço `Postgres`. A configuração está descrita em
`backend/README.md#deploy-na-railway`.

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.8 implementada. A API subiu na Railway em `elite-dev-rockhub-production.up.railway.app`, com o PostgreSQL no mesmo projeto, alcançado por rede privada via `${{Postgres.DATABASE_URL}}`. Build pelo Railpack com `Root Directory = backend`; `alembic upgrade head && python -m seeds.semear` como Pre-deploy Command; `uvicorn app.main:app --host 0.0.0.0 --port $PORT` como start; health check em `/saude`. A descoberta que mudou a story: o Railpack instala o `uv` só na fase de build e não o deixa na imagem final, então os comandos chamam `alembic`/`python`/`uvicorn` direto — `uv run` ali falharia com `uv: not found`. Verificado por HTTP de fora: `/saude` e `/docs` respondendo, login das quatro contas semeadas devolvendo `200` com o papel certo (o que prova migração, seed e banco numa chamada só) e o `Set-Cookie` vindo com `Secure`, único sintoma observável de que `AMBIENTE=producao` chegou à aplicação. Nenhuma linha de `app/`, `migrations/`, `seeds/`, `tests/` ou `frontend/src/` alterada, nenhuma dependência nova, e nenhum `railway.json`/`Dockerfile`/`Procfile` criado — a configuração mora no painel, por decisão registrada, e o README do backend a descreve campo por campo para ser refazível numa conta vazia. Os três READMEs atualizados: o da raiz ganhou a seção *No ar* com a URL, um passo novo no roteiro de avaliação, três decisões novas (Railpack em vez de `Dockerfile`; Pre-deploy em vez de start encadeado; painel em vez de `railway.json`) e duas limitações declaradas (frontend ainda não publicado; nenhuma integração contínua) |
| 2026-08-10 | Story 1.8 criada e contextualizada. Quatro decisões do Igor incorporadas: Railpack como builder (em vez de `Dockerfile` próprio ou Nixpacks), migração e seed no Pre-deploy Command (em vez de encadeados no Start Command ou num script de release versionado), configuração no painel da Railway (em vez de `railway.json` versionado) e os dois segredos ainda não lidos definidos só no ambiente, sem tocar a `Settings`. Cinco ACs acrescentados aos cinco do `epics.md`: comandos sem `uv run` — o Railpack não deixa o `uv` na imagem final, o que faria o primeiro deploy falhar num erro que não aponta para causa nenhuma —, login pela URL pública com `Secure` no cookie como prova de que `AMBIENTE=producao` chegou, health check em `/saude` com bind em `0.0.0.0:$PORT`, os três READMEs refazíveis numa conta vazia, e a fronteira de que nenhuma linha de `app/`, `migrations/`, `seeds/` ou `tests/` muda. Registrada a divisão de responsabilidade que esta story tem e nenhuma anterior teve: a configuração do painel é do Igor, a verificação por HTTP e a documentação são do agente, e o README é escrito a partir do que foi executado, não do que se pretendia executar |
