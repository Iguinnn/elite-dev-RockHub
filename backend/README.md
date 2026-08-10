# RockHub — backend

API em FastAPI da plataforma de eventos e ingressos. Este README é a camada de backend: como
rodar, como está organizado e por que optei por cada convenção. O histórico de decisões do
projeto inteiro está no [README da raiz](../README.md).

## Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** — ele mesmo baixa o Python 3.12 se a máquina não tiver,
  lendo o `.python-version` daqui.
- **Docker** com o plugin Compose (`docker compose`, com espaço — é o Compose v2, embutido em
  qualquer instalação atual) — sobe o PostgreSQL 16 que o backend precisa desde a Story 1.3.

Escolhi o `uv` em vez de `pip` + `requirements.txt` porque ele resolve três coisas de uma vez:
instala o interpretador certo, cria a virtualenv e trava as versões num lockfile. Numa avaliação
em que alguém vai clonar o repositório e rodar numa máquina que eu nunca vi, cada passo manual a
menos é um jeito a menos de dar errado.

## Como rodar

```bash
# da raiz do repositório
docker compose up -d      # Postgres 16 em localhost:5432

cd backend

cp .env.example .env      # no Windows: copy .env.example .env
uv sync                   # cria a .venv/ e instala exatamente o que está no uv.lock

uv run alembic upgrade head               # cria o schema (tabela usuario)
uv run uvicorn app.main:app --reload      # sobe em http://127.0.0.1:8000
uv run pytest                             # roda os testes — exige o Compose no ar (ver Testes)
```

O `uv sync` cria a virtualenv em `backend/.venv/` — não é preciso ativar nada à mão, o `uv run`
já executa dentro dela.

Com o servidor no ar:

- <http://127.0.0.1:8000/saude> → `{"status": "ok"}`
- <http://127.0.0.1:8000/docs> → documentação automática do FastAPI

> **Se `uv run pytest` ou `uv run uvicorn` falhar com "política de Controle de Aplicativo bloqueou
> este arquivo"**, é o Windows barrando os executáveis instalados na virtualenv — não é problema do
> projeto. Chame pelo módulo, que faz exatamente o mesmo:
>
> ```bash
> uv run python -m pytest
> uv run python -m uvicorn app.main:app --reload
> ```

## Configuração

Toda configuração vem de variável de ambiente, lida pela classe `Settings`
([`app/core/config.py`](app/core/config.py)). O que é versionado é o `.env.example`; o `.env` real
fica de fora. **Nenhum segredo entra no repositório** — essa é a regra que protege a chave da
Ticketmaster mais adiante.

| Variável | Padrão | Para que serve |
|---|---|---|
| `APP_NOME` | `RockHub API` | Título que aparece no `/docs` |
| `AMBIENTE` | `local` | `local` ou `producao`. Qualquer outro valor derruba a aplicação na subida, de propósito |
| `CORS_ORIGENS` | `http://localhost:3000` | Origens autorizadas, separadas por vírgula |
| `DATABASE_URL` | `postgresql+psycopg://rockhub:rockhub@localhost:5432/rockhub` | Conexão com o Postgres do `docker-compose.yml` da raiz |
| `DATABASE_URL_TESTE` | `.../rockhub_teste` | Banco usado por `uv run pytest`. Criado pelo script de `docker/initdb/` na primeira subida do Compose |
| `JWT_SECRET` | `troque-este-valor-em-producao` | Segredo que assina o cookie de sessão. **Gere o seu antes de subir em produção** (comando abaixo) |

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Com `AMBIENTE=producao`, o valor de exemplo do `JWT_SECRET` derruba a aplicação na
inicialização**, com a mensagem dizendo o comando acima. Isso é de propósito: o ponto mais provável
de um segredo vazar não é alguém colar a chave no código — é o valor de exemplo continuar
funcionando e ninguém perceber. Um `JWT_SECRET` padrão rodando em produção é um segredo público
assinando sessões, e o deploy não teria como descobrir sozinho, porque *funciona*. Mesmo padrão vai
valer para `TICKETMASTER_API_KEY` (Story 2.1) e `TICKET_SIGNING_SECRET` (Story 3.9).

`DATABASE_URL` e `DATABASE_URL_TESTE` aceitam também `postgres://` e `postgresql://` — os
esquemas que a Railway injeta. Um validador normaliza os três casos para `postgresql+psycopg://`,
porque o SQLAlchemy resolve `postgresql://` para o driver **psycopg2**, que não está instalado
aqui (o driver é o psycopg 3). Sem essa normalização o erro no dia do deploy da Story 1.8 seria um
`ModuleNotFoundError` que não aponta para a URL como causa.

`CORS_ORIGENS` aceita lista separada por vírgula em vez de JSON. O padrão do `pydantic-settings`
para campos de lista é interpretar a variável como JSON, e eu desliguei isso (`NoDecode` + um
validador). O motivo é prático: quem for colar essa variável no painel da Railway vai digitar
`https://a.com,https://b.com`, não `["https://a.com","https://b.com"]` — e um JSON malformado num
painel de deploy é um erro chato de achar.

## Banco de dados

O Postgres sobe pelo `docker-compose.yml` da raiz — não pela pasta `backend/`, porque o banco é
infraestrutura do projeto inteiro (a Story 1.7 semeia por ele, e é a mesma instância que o
frontend depende em desenvolvimento).

```bash
# da raiz do repositório
docker compose up -d          # Postgres 16 em localhost:5432
docker compose ps             # conferir que o serviço está saudável
docker compose down -v        # derruba e apaga o volume — banco do zero

cd backend
uv run alembic upgrade head                              # aplica as migrações
uv run alembic downgrade base                             # desfaz tudo
uv run alembic revision --autogenerate -m "descrição"      # nova migração
uv run alembic current                                     # em que revisão o banco está
```

O `docker compose up` também cria o `rockhub_teste` na primeira subida (script em
`docker/initdb/`) — é o banco que `uv run pytest` migra e usa.

**Nunca `Base.metadata.create_all` — nem em teste.** Toda mudança de schema é migração Alembic
versionada, verificada em código pela T9 desta story (busca literal por `create_all` no
repositório). O `--autogenerate` é ponto de partida, não resultado: sempre revi a migração gerada
à mão antes de aplicar, confirmando `CheckConstraint`, `UniqueConstraint` e o `downgrade()`.

## Estrutura

```text
backend/
  app/
    main.py          # cria o FastAPI, aplica CORS, registra o handler de erro e os routers
    api/             # routers: HTTP puro — entrada, autenticação, status
      saude.py
      auth.py         # POST /auth/login, POST /auth/logout
    services/        # regra de negócio, transações e acesso ao banco
      autenticacao.py # autenticar(sessao, email, senha) -> Usuario
    models/          # SQLAlchemy
      base.py        # Base declarativa + convenção de nomes de constraint
      usuario.py      # PapelUsuario + Usuario
    schemas/         # Pydantic de entrada e saída
      auth.py         # LoginEntrada, UsuarioSaida
    core/
      config.py      # Settings
      db.py           # engine, SessaoLocal, a dependência obter_sessao()
      erros.py        # erro de domínio + formato único de resposta
      seguranca.py    # hash Argon2id e token de sessão (JWT)
  migrations/         # Alembic
    env.py
    versions/
  tests/              # espelha a estrutura de app/
    conftest.py        # fixtures que migram rockhub_teste pelo Alembic
  alembic.ini
  pyproject.toml
  uv.lock
  .env.example
```

`services/` e `schemas/` nasceram vazias na Story 1.1, só com `__init__.py`, e ganharam o primeiro
morador na 1.4 com o login. Foi proposital: elas materializaram o paradigma desde o primeiro
commit, para que as stories seguintes não tivessem que decidir no calor da hora onde cada coisa
mora.

## Autenticação

Duas rotas, e nada além disso até a Story 1.6:

```
POST /auth/login
  ← {"email": "igor@exemplo.com", "senha": "..."}
  → 200  {"id": "…", "nome": "…", "email": "…", "papel": "CLIENTE"}
         Set-Cookie: rockhub_sessao=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800
                     (+ Secure quando AMBIENTE=producao)
  → 401  {"erro": {"codigo": "CREDENCIAIS_INVALIDAS", "mensagem": "E-mail ou senha incorretos."}}

POST /auth/logout
  → 204  sem corpo; apaga o cookie. Não exige sessão válida — quem tem token vencido
         é justamente quem mais precisa sair
```

O JWT carrega só `sub` (id do usuário, **como string**), `papel`, `iat` e `exp`. Nome e e-mail não
entram: token é credencial que trafega em toda requisição, então quanto menos carrega, menos vaza
se for lido — e menos fica velho quando o usuário troca o nome.

Três coisas que valem saber antes de mexer nisso:

- **A validade da sessão tem uma fonte só.** `EXPIRACAO_SESSAO` em `app/core/seguranca.py` é uma
  constante de módulo, e dela saem tanto o `exp` do JWT quanto o `max_age` do cookie. Não é
  variável de ambiente de propósito: as 8 horas vêm do AD-15 com justificativa de domínio (cobre um
  turno de portaria), e knob de configuração faria o valor em produção divergir do documentado sem
  ninguém descobrir até alguém ser deslogado no meio do turno. Se ficassem em dois lugares, um dia
  divergiriam — e o sintoma é cookie válido carregando token vencido, ou seja, `401` numa tela que
  parece logada
- **`sub` precisa ser `str`.** O PyJWT valida essa claim desde a 2.10 e levanta `InvalidSubjectError`
  se ela não for string. `usuario.id` é `UUID`: passar direto funciona no `encode` e explode no
  `decode`, então o login pareceria certo e quem quebraria seria a rota autenticada da Story 1.6
- **`jwt.decode` sempre com `algorithms=["HS256"]` fixo no código.** Não é burocracia da biblioteca:
  aceitar o algoritmo que vem escrito dentro do próprio token é a vulnerabilidade clássica de JWT —
  um token com `"alg": "none"` passaria a valer

E a resposta de erro do login é uma só. E-mail inexistente e senha errada devolvem **a mesma
construção** de `ErroDeDominio`, não duas strings iguais por coincidência — e quando o usuário não
existe, o service ainda confere a senha contra um `HASH_FANTASMA` e descarta o resultado. Sem isso a
rota responderia em ~1ms para e-mail desconhecido e em ~50ms para e-mail existente com senha errada:
uma diferença de cinquenta vezes, medível de fora com um `for` e um cronômetro, que transformaria o
endpoint num oráculo de "quem tem conta aqui" sem precisar de senha nenhuma.

### O paradigma: `routers → services → models`

Dependência sempre para dentro, nunca o inverso, nunca pulando camada.

| Camada | Pasta | Responsabilidade |
|---|---|---|
| `routers` | `app/api/` | HTTP: validação de entrada, autenticação, código de status. Sem regra de negócio, sem tocar no banco |
| `services` | `app/services/` | Regra de negócio, transações e acesso ao banco |
| `models` | `app/models/` | SQLAlchemy |

**Não existe `app/repositories/`, e isso foi escolhido.** O motivo está no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

## Convenções que nascem aqui

Estas valem para o projeto inteiro daqui para a frente:

- **Nomes** — Python e banco em `snake_case`. O domínio é em português (`evento`, `setor`,
  `reserva`, `ingresso`) para bater com o vocabulário do enunciado do desafio. Traduzir para inglês
  só criaria um dicionário mental entre o requisito e o código
- **Erro da API** — sempre `{"erro": {"codigo": "...", "mensagem": "..."}}`
- **Configuração** — só por variável de ambiente
- **Datas** — UTC, ISO-8601 (a partir da Story 1.3)
- **Dinheiro** — inteiro em centavos, campo sufixado `_centavos` (a partir da Epic 2)

### O formato de erro

**Toda** resposta de erro desta API tem a mesma forma:

```json
{ "erro": { "codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "Não há ingressos suficientes." } }
```

Sempre estas duas chaves, nunca mais, nunca menos. O `codigo` é a parte estável do contrato — é por
ele que o frontend decide o que mostrar. A `mensagem` é texto para humano e pode ser reescrita a
qualquer momento sem quebrar nada.

Isso vale para as três origens de erro, cobertas por três handlers em
[`app/main.py`](app/main.py):

| Origem | Como chega | Código |
|---|---|---|
| Regra de negócio | `raise ErroDeDominio(codigo=..., mensagem=..., status_http=...)` | o que o `raise` disser |
| Framework | rota inexistente, método errado, `raise HTTPException(...)` | pela tabela `CODIGO_POR_STATUS` — `404` vira `NAO_ENCONTRADO`, `403` vira `SEM_PERMISSAO` |
| Validação do Pydantic | corpo, query ou path reprovados | `DADOS_INVALIDOS` |

O erro de validação merece uma nota. O Pydantic devolve uma lista de objetos aninhados, ótima para
depurar e péssima como contrato — obrigaria o corpo de erro a ter uma forma diferente só neste
caso. Achatei tudo numa frase (`setor_id: campo obrigatório; quantidade: não é um inteiro`), o que
mantém uma forma só na API sem perder qual campo reprovou.

Deixei isso pronto já na primeira story, antes de existir qualquer regra de negócio, porque
padronizar erro depois significa voltar em todo endpoint já escrito.

**O que ainda não passa por aqui:** exceção não tratada, que vira `500` com o texto padrão do
Starlette. Tratá-la exigiria decidir o que registrar em log, e observabilidade ficou fora do
escopo deste projeto.

## Testes

```bash
docker compose up -d      # a partir da Story 1.3, os testes exigem o Postgres no ar
cd backend
uv run pytest
```

São **40 testes** em `tests/`, espelhando `app/`. Cobrem a rota de saúde, o `/docs`, as três origens
de erro, a leitura de configuração do ambiente, a migração Alembic, o modelo `Usuario`, o hash e o
token de sessão, e as duas rotas de autenticação.

Para testar os erros eu montei apps mínimas com os handlers reais e rotas que só existem para
falhar. Assim o contrato fica verificado desde já, sem precisar esperar o primeiro endpoint de
negócio aparecer para descobrir que ele estava errado. O `404` e o `405` são testados direto na
aplicação de verdade, e um teste confere que os três handlers estão de fato registrados nela — de
nada adianta o handler certo se ninguém o pendurou na app.

**Os testes de banco rodam contra Postgres real, migrado pelo próprio Alembic** — não `create_all`,
não SQLite. A fixture de sessão em `tests/conftest.py` roda `alembic downgrade base` seguido de
`upgrade head` contra `DATABASE_URL_TESTE` antes da suíte, o que verifica a migração de ida e de
volta a cada execução. Cada teste individual roda dentro de uma transação (com um `SAVEPOINT`
reaberto a cada flush) que é revertida ao final, para um teste não sujar o outro.

Esse custo — `uv run pytest` agora exige o Compose no ar — foi deliberado. As alternativas
(`create_all` pelos modelos, SQLite em memória) rodariam mais rápido, mas nenhuma das duas prova
que a migração de verdade funciona, e é exatamente isso que a Story 1.3 entrega. Os testes de
`/saude`, erros e config continuam passando com o Postgres desligado — as fixtures de banco ficam
isoladas em `conftest.py` e não conectam em escopo de import.

**Os testes de HTTP que precisam de banco usam `dependency_overrides`.** Até a Story 1.3 havia dois
tipos de teste que não se encontravam: os de `TestClient` não tocavam banco, e os de banco não
subiam HTTP. O login precisa dos dois ao mesmo tempo, e a ponte é substituir a dependência
`obter_sessao` pela sessão da fixture — que já roda dentro da transação revertida. Duas sutilezas
que custam tempo: o `app.dependency_overrides.clear()` no fim é obrigatório (o `app` é módulo
importado, o override é global e sobrevive ao teste, e a falha depois aparece longe da causa), e o
override é `lambda: sessao`, devolvendo a sessão em vez de um gerador — com `yield`, o FastAPI
fecharia a sessão da fixture ao fim da requisição e o teste seguinte receberia uma sessão morta.

A fixture tem uma trava específica: ela nunca aponta para o banco de desenvolvimento, mesmo que o
`.env` esteja carregado. A URL do Alembic é definida em código
(`cfg.set_main_option("sqlalchemy.url", ...)`) a partir de `DATABASE_URL_TESTE`, nunca por
variável de ambiente — e um teste (`test_banco_de_teste_e_o_rockhub_teste`) confere via
`SELECT current_database()` que a trava está de fato ativa. Um `alembic downgrade base` acidental
contra o banco de desenvolvimento apaga dados; essa é a garantia de que isso não acontece pela
suíte de testes.

## Histórico desta camada

### Story 1.1 — esqueleto que responde

Subi o backend do zero: projeto `uv` com Python 3.12 e dependências travadas, a árvore de pastas do
paradigma, `Settings` por variável de ambiente, CORS configurável, o formato único de erro,
`GET /saude` e os primeiros testes.

Duas coisas eu antecipei de propósito, mesmo sem serem necessárias para responder um `200`:

- **CORS já configurável.** O frontend chega na Story 1.2 e o deploy na 1.8/1.9. Mais adiante, a
  sessão vai ser um cookie `httpOnly`, e cookie entre origens diferentes só funciona com
  `allow_credentials` ligado e origem explícita — curinga `*` é incompatível com credencial.
  Deixar isso para depois significaria mexer no `main.py` três vezes
- **Formato de erro.** Mesmo motivo: é contrato, e contrato definido depois vira retrabalho

O que deliberadamente **não** entrou: banco, SQLAlchemy, Alembic, autenticação, Docker, CI. Cada um
tem a sua story. Instalar dependência antes da hora só polui o lockfile com coisa que ainda não
tem uso.

### Story 1.3 — modelo de usuário e primeira migração

Primeira story que toca banco: até aqui não havia PostgreSQL, SQLAlchemy, Alembic nem
`docker-compose.yml` no repositório. Subi o Postgres 16 local pelo Compose (na raiz, não aqui —
ver [README da raiz](../README.md)), estendi a `Settings` existente com `DATABASE_URL` e
`DATABASE_URL_TESTE`, criei `app/core/db.py` (engine + `SessaoLocal` + `obter_sessao()`), a `Base`
declarativa com convenção de nomes de constraint, o modelo `Usuario` com o enum `PapelUsuario`, e
o setup do Alembic em `migrations/` com a primeira migração.

As cinco decisões de projeto por trás disso — Postgres por Compose, SQLAlchemy síncrono, `papel`
como `VARCHAR` + `CHECK` em vez de enum nativo, migração Alembic desde a primeira tabela e testes
contra Postgres real — estão no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo),
cada uma com a alternativa que descartei e por quê.

Duas armadilhas valeram a pena registrar aqui porque vão se repetir nas próximas migrações
(Epics 2 a 5, que também mexem em schema):

- **`env.py` precisa importar os modelos.** O `alembic init` deixa `target_metadata = None`; trocar
  por `Base.metadata` não basta sozinho — se nada importar `app.models.usuario`, a classe nunca é
  registrada no metadata e o `--autogenerate` gera um `upgrade()` vazio. `app/models/__init__.py`
  reexporta `Base` e `Usuario` justamente para o `env.py` importar um módulo só.
- **A URL do Alembic nunca vem só da variável de ambiente na fixture de teste.** Ela precisa ser
  escrita em código (`cfg.set_main_option`) a partir de `DATABASE_URL_TESTE`, porque a fixture
  começa com `alembic downgrade base` — e se essa chamada resolvesse a URL da forma normal (que
  cai na `Settings`, ou seja, no banco de desenvolvimento), um `uv run pytest` distraído apagaria
  dados de verdade. Documentei o contrato completo na seção [Testes](#testes) acima.

O `Base.metadata.create_all` nunca aparece neste projeto, nem em teste — é a primeira regra que
travei nesta story, porque contrariá-la resolveria o problema imediato e criaria um schema que a
migração Alembic não conhece.

### Story 1.4 — entrar com e-mail e senha

A tabela `usuario` ganhou o primeiro consumidor, e as pastas `services/` e `schemas/` deixaram de
estar vazias. Entraram `argon2-cffi` e `pyjwt`, o `app/core/seguranca.py` (hash Argon2id, criação e
leitura do token), o `app/schemas/auth.py`, o `app/services/autenticacao.py` e o `app/api/auth.py`
com as duas rotas. A `Settings` ganhou `JWT_SECRET`, o nome do cookie e a propriedade `cookie_secure`.

As decisões de projeto — Argon2id, sessão em cookie `httpOnly` em vez de token no `localStorage`,
PyJWT no lugar do `python-jose`, e a mensagem única para credenciais inválidas — estão no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo), cada uma com a alternativa que
descartei.

Quatro convenções nasceram aqui e valem para as stories seguintes:

- **`app/services/<assunto>.py` com funções de módulo, não classes.** O service recebe a `Session`
  como primeiro parâmetro e devolve modelo ou levanta `ErroDeDominio`. Não há classe de service,
  não há injeção de service — a função é a unidade
- **O service nunca sabe de HTTP.** Nem status, nem cookie, nem header. Ele levanta `ErroDeDominio`
  com o status embutido, e o router não traduz nada. `autenticar()` devolve um `Usuario`; quem monta
  o token e grava o cookie é a rota
- **`app/schemas/<assunto>.py`**, um arquivo por assunto, com os nomes sufixados `Entrada` e
  `Saida`. **Nunca reaproveite um schema de entrada como saída** — é assim que um `senha_hash` acaba
  num corpo de resposta
- **Todo segredo é campo da `Settings` com valor de exemplo, e o `model_validator` recusa o exemplo
  em produção**

Duas escolhas de biblioteca que valem registrar aqui porque a documentação antiga do FastAPI sugere
o contrário: **não uso `passlib`** (sem lançamento desde 2020, e era só um wrapper — o `argon2-cffi`
é a API direta), e **não uso `EmailStr`** no login. Nesse endpoint não há o que validar: o e-mail é
chave de busca, e formato inválido simplesmente não encontra ninguém. Pior, um `422` de formato
antes do `401` de credencial criaria exatamente a distinção que a resposta única existe para
eliminar. `EmailStr` faz sentido na Story 1.5, onde o e-mail é *gravado*.

O `PasswordHasher()` sem argumento nenhum já entrega o que o AD-15 pede: Argon2id é o tipo padrão,
os parâmetros são o perfil de baixa memória da RFC 9106, o sal é aleatório por hash e viaja dentro
da própria string — por isso não existe coluna de sal, e não deve existir. Como todos os parâmetros
estão embutidos no hash, trocá-los depois não invalida o que já está gravado. O custo é real e é
proposital: cada verificação leva ~50ms e ~64 MB, o que deixa os testes de login perceptivelmente
mais lentos que os outros e vai importar na hora de escolher o tamanho da instância na Railway
(Story 1.8).
