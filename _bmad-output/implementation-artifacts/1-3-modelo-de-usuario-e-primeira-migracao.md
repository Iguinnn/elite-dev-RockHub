---
baseline_commit: c801bef
---

# Story 1.3: Modelo de usuário e primeira migração

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **Primeira story que toca banco de dados: hoje não
existe nenhuma dependência de banco no `pyproject.toml`, nenhum modelo, nenhuma migração e nenhum
PostgreSQL no repositório.**

## Story

Como desenvolvedor,
quero a tabela de usuários criada por migração versionada,
para que o banco possa ser reconstruído do zero de forma reproduzível.

## Acceptance Criteria

1. **Given** um banco PostgreSQL vazio
   **When** eu rodo `alembic upgrade head`
   **Then** a tabela `usuario` existe com `id` UUID, `nome`, `email` único, `senha_hash` e `papel`
   **And** `papel` aceita apenas `ORGANIZADOR`, `CLIENTE` ou `PORTARIA`

2. **Given** o projeto
   **When** eu procuro criação de schema
   **Then** não existe `create_all` fora de teste — só migrações Alembic

3. **Given** um clone novo do repositório e Docker instalado
   **When** eu subo o banco e rodo a migração
   **Then** o schema nasce igual, sem nenhum passo manual de criar banco ou usuário
   **And** `alembic downgrade base` desfaz a migração por inteiro, e `upgrade head` a refaz

4. **Given** a conexão com o banco
   **When** eu procuro no código
   **Then** ela vem de `DATABASE_URL` lida pela classe `Settings` já existente
   **And** nenhuma string de conexão real está versionada — nem no `alembic.ini`

> **AC3 e AC4 não estão no `epics.md`.** O AC3 existe porque "reconstruído do zero de forma
> reproduzível" está na própria narrativa da story e não tinha critério que o verificasse: sem o
> `downgrade`, uma migração pode estar quebrada por meses sem ninguém perceber, e é exatamente a
> Story 1.8 (deploy na Railway) que descobriria isso da pior maneira. O AC4 existe porque o
> `alembic init` grava uma URL de exemplo no `alembic.ini` — é o ponto mais provável do projeto
> inteiro para uma credencial vazar para o commit, e a regra "segredo nenhum no repositório" já
> está travada desde a Story 1.1.

## Tasks / Subtasks

- [x] **T1. Subir o PostgreSQL 16 por Docker Compose** (AC: 1, 3)
  - [x] `docker-compose.yml` **na raiz do repositório** (decisão do Igor — ver *Decisões que o Igor
        tomou*), com serviço `db` na imagem `postgres:16`
  - [x] Usuário/senha/banco: `rockhub` / `rockhub` / `rockhub`. Não é segredo: é banco local, e o
        valor precisa bater com o padrão do `DATABASE_URL` do `.env.example`
  - [x] Porta `5432:5432`, volume nomeado `rockhub-pgdata` e `healthcheck` com `pg_isready`
  - [x] **Sem a chave `version:`** — ela é obsoleta no Compose v2 e só produz aviso
  - [x] `docker/initdb/01-cria-banco-de-teste.sql` montado em `/docker-entrypoint-initdb.d/`,
        criando o banco `rockhub_teste` (`CREATE DATABASE rockhub_teste OWNER rockhub;`). É o banco
        que a T7 usa; criá-lo na inicialização evita um passo manual no README
  - [x] Conferir: `docker compose up -d` e depois `docker compose ps` mostrando o serviço saudável

- [x] **T2. Dependências de banco** (AC: 1)
  - [x] Acrescentar ao `backend/pyproject.toml`: `sqlalchemy==2.0.51`, `alembic==1.19.1`,
        `psycopg[binary]==3.3.4` (versões conferidas na tabela *Stack desta story*)
  - [x] `uv sync` para atualizar o `uv.lock` — o lockfile é versionado
  - [x] **Não instale `argon2-cffi`** — é da Story 1.4, que é quem faz o primeiro hash
  - [x] **Não instale `psycopg2`.** O driver é o psycopg 3, e a URL precisa dizer isso
        (`postgresql+psycopg://`) — ver *Armadilhas*

- [x] **T3. `DATABASE_URL` na `Settings` existente** (AC: 4)
  - [x] Acrescentar `database_url: str` a `app/core/config.py`, com padrão apontando para o Compose:
        `postgresql+psycopg://rockhub:rockhub@localhost:5432/rockhub`
  - [x] Acrescentar `database_url_teste: str`, padrão `.../rockhub_teste`
  - [x] **Validador `mode="before"` normalizando o esquema:** `postgres://` e `postgresql://` viram
        `postgresql+psycopg://`. Motivo em *Armadilhas* — é o que a Railway injeta na Story 1.8, e
        sem isso o SQLAlchemy procura o psycopg2, que não existe aqui
  - [x] `backend/.env.example` ganha as duas chaves comentadas, como as três que já estão lá
  - [x] **Não crie um `Settings` novo nem um módulo de config paralelo** — a classe já existe e é
        exposta por `obter_settings()` com `@lru_cache`

- [x] **T4. Engine e sessão** (AC: 2, 4)
  - [x] `app/core/db.py`: `engine` criado a partir de `obter_settings().database_url`,
        `SessaoLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)` e a
        dependência `obter_sessao()` (gerador com `yield` e `finally: sessao.close()`)
  - [x] **`create_engine` no import é aceitável e desejado** — ele não abre conexão. O que **não**
        pode é qualquer conexão acontecer na subida: os testes de `/saude` precisam continuar
        passando com o Postgres desligado (ver *Armadilhas*)
  - [x] **A dependência não abre nem fecha transação.** Quem faz `commit`/`rollback` é o service —
        `ARCHITECTURE-SPINE.md#Convenções`. Nesta story não há service ainda; a peça nasce pronta
        para a Story 1.4
  - [x] **Nenhum `Base.metadata.create_all` neste arquivo nem em lugar nenhum** — é o AC2

- [x] **T5. `Base` declarativa com convenção de nomes** (AC: 1)
  - [x] `app/models/base.py`: `class Base(DeclarativeBase)` com
        `metadata = MetaData(naming_convention=...)` — dicionário completo em *Base e convenção de
        nomes*
  - [x] Sem a convenção, o `CHECK` do `papel` nasce com nome gerado pelo Postgres e o `downgrade`
        do AC3 fica frágil. Não é detalhe cosmético
  - [x] `app/models/__init__.py` reexporta `Base` e `Usuario` — é o import que o `env.py` do Alembic
        vai usar para enxergar o metadata (ver *Armadilhas*)

- [x] **T6. Modelo `Usuario` e enum `PapelUsuario`** (AC: 1)
  - [x] `app/models/usuario.py` com `PapelUsuario(str, Enum)` — `ORGANIZADOR`, `CLIENTE`, `PORTARIA`
  - [x] Tabela `usuario` (singular), colunas conforme a tabela em *O modelo `Usuario`*
  - [x] `CheckConstraint` **nomeado** (`name="papel_valido"`) em `__table_args__`, listando os três
        valores. VARCHAR + CHECK, **não** enum nativo do Postgres — decisão do Igor
  - [x] Estilo tipado do SQLAlchemy 2.0: `Mapped[...]` + `mapped_column(...)`. **Não** use o
        `Column()` do estilo 1.x
  - [x] `PapelUsuario` mora aqui e é o único do projeto. A dependência de papel da Story 1.6 e os
        schemas das Stories 1.4/1.5 importam **deste** arquivo — não redeclare o enum lá

- [x] **T7. Alembic em `backend/migrations/`** (AC: 1, 2, 3, 4)
  - [x] `cd backend && uv run alembic init migrations` — o diretório é `migrations/`, como manda a
        árvore da arquitetura. **Não** aceite o `alembic/` padrão
  - [x] `alembic.ini`: `script_location = migrations`, `prepend_sys_path = .`, e
        **`sqlalchemy.url` esvaziado** (linha em branco ou removida) — AC4
  - [x] `file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s`, para as migrações
        ficarem em ordem cronológica na pasta
  - [x] `migrations/env.py`: `target_metadata = Base.metadata`, `compare_type=True`, e a URL
        resolvida assim, **nesta ordem** — `config.get_main_option("sqlalchemy.url")` se estiver
        preenchida, senão `obter_settings().database_url`. A precedência não é estética: é o que
        permite a fixture da T8 apontar o Alembic para o banco de teste sem variável de ambiente
        (ver *A fixture não pode migrar o banco de desenvolvimento*)
  - [x] **`env.py` precisa importar `app.models`** — sem isso o metadata vem vazio e o
        `--autogenerate` produz uma migração que não cria nada (ver *Armadilhas*)
  - [x] Gerar: `uv run alembic revision --autogenerate -m "cria tabela usuario"`
  - [x] **Revise o arquivo gerado à mão.** Confirme que `sa.CheckConstraint` do papel está lá, que o
        `unique=True` do e-mail virou constraint nomeada e que o `downgrade()` derruba a tabela
  - [x] `uv run alembic upgrade head` e conferir no `psql`: `\d usuario`

- [x] **T8. Testes contra Postgres real, migrado pelo Alembic** (AC: 1, 2, 3)
  - [x] `backend/tests/conftest.py` com fixture de escopo `session` que roda
        `alembic downgrade base` + `alembic upgrade head` por `alembic.command`, **com
        `cfg.set_main_option("sqlalchemy.url", settings.database_url_teste)` antes de qualquer
        chamada**. Ler primeiro *A fixture não pode migrar o banco de desenvolvimento*
  - [x] Fixture de função entregando uma `Session` dentro de transação revertida ao fim, para um
        teste não sujar o outro
  - [x] `backend/tests/test_migracoes.py` e `backend/tests/test_usuario.py` cobrindo o que está
        listado em *Testing*
  - [x] As fixtures de banco ficam **isoladas**: os testes de `/saude`, erros e config existentes
        continuam passando com o Postgres desligado. Não coloque nada que conecte no `conftest.py`
        em escopo de import

- [x] **T9. Verificação** (AC: 1, 2, 3, 4)
  - [x] `docker compose down -v && docker compose up -d` → `uv run alembic upgrade head` do zero,
        sem erro (é o AC3 literalmente)
  - [x] `uv run alembic downgrade base` → `uv run alembic upgrade head` de novo, sem erro
  - [x] `uv run pytest` — os 14 testes anteriores continuam verdes, mais os novos
  - [x] Busca em `backend/` por `create_all` → **zero ocorrência**, inclusive em teste, porque aqui
        o teste também migra pelo Alembic (verificação literal do AC2)
  - [x] Busca por `postgresql://`, `postgres://`, `psycopg2` e por qualquer senha em `alembic.ini` →
        nada que não seja o normalizador da T3 e os exemplos do `.env.example`
  - [x] `uv run uvicorn app.main:app --reload` sobe **com o Postgres desligado** — a aplicação não
        conecta na subida

- [x] **T10. Documentação** (obrigatório — regra do projeto)
  - [x] `backend/README.md`: seção de banco (subir o Compose, migrar, criar nova migração), a
        estrutura de pastas atualizada com `migrations/` e `models/`, e as variáveis `DATABASE_URL`
        e `DATABASE_URL_TESTE` na tabela de configuração. Anotar que `uv run pytest` agora exige o
        banco no ar
  - [x] `README.md` da raiz: "Pré-requisitos" ganha Docker; "Como executar" ganha o passo do banco
        **antes** do backend; "Estado atual" e "Stack e estrutura" saem de *(Story 1.3)*
  - [x] `README.md` da raiz, seção "Decisões": **cinco** entradas novas, cada uma com o que caiu e
        por quê — Postgres por Docker Compose; SQLAlchemy síncrono; VARCHAR + CHECK no lugar do enum
        nativo; Alembic desde a primeira tabela, sem `create_all`; teste contra Postgres de verdade.
        A matéria-prima está em *Decisões que o Igor tomou*, com as alternativas descartadas
  - [x] **`frontend/README.md` não muda nesta story, e isso é intencional** — nada da camada de
        frontend foi tocado. Mesmo precedente da Story 1.1, que deixou o README do frontend vazio
        por não ter tocado nele. Não invente conteúdo para cumprir a regra dos três READMEs
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "descartei")

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **Não são sugestão, e a alternativa
descartada de cada uma é o material do README da raiz (T10).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Postgres local | **`docker-compose.yml` na raiz** | *Postgres instalado na máquina*: obriga o avaliador a instalar, criar banco e usuário à mão — mais passos manuais, mais formas de a avaliação travar antes de ver o produto. *Banco da Railway direto*: zero setup, mas o desenvolvimento passa a depender de rede e todo mundo escreve no mesmo banco |
| ORM | **SQLAlchemy síncrono (`Session`)** | *`AsyncSession`*: melhor sob carga alta de I/O, mas exige `await` em toda consulta e disciplina em todo o código, complica fixture de teste, e um `await` esquecido bloqueia o event loop de um jeito difícil de diagnosticar. O volume de uma avaliação não cobra esse preço, e os `UPDATE` condicionais dos AD-3/AD-6 ficam mais legíveis no síncrono |
| `papel` no banco | **VARCHAR + `CHECK`** | *Enum nativo do Postgres*: mais idiomático, mas o Alembic não cria nem derruba o tipo sozinho no `downgrade` — quebraria o AC3 — e alterar valores depois exige `ALTER TYPE` com ordem específica |
| Banco nos testes | **Postgres real, migrado por Alembic** | *`create_all` pelos modelos*: mais rápido de montar, mas deixaria de verificar exatamente o que a story entrega — a migração. *SQLite em memória*: nenhuma dependência externa, mas sem UUID nativo, sem `TIMESTAMPTZ` e com outro tratamento de `CHECK`; passaria verde sem provar nada. Custo aceito: `uv run pytest` passa a exigir o Compose no ar, e isso vai para o README |

### Stack desta story — versões conferidas na web em 10/08/2026

| Pacote | Versão | Papel |
|---|---|---|
| `sqlalchemy` | 2.0.51 | ORM, no estilo tipado 2.0 (`Mapped` / `mapped_column`) |
| `alembic` | 1.19.1 | Migrações versionadas |
| `psycopg[binary]` | 3.3.4 | Driver PostgreSQL. O extra `binary` traz o wheel compilado — sem ele, a instalação exige toolchain de C na máquina |
| PostgreSQL | 16 | Imagem `postgres:16` no Compose. É a versão que a arquitetura fixa |

**Não instale ainda:** `argon2-cffi` (Story 1.4), `python-jose`/`pyjwt` (1.4), `psycopg-pool`. Pool de
conexão é otimização sem gargalo medido; o pool padrão do SQLAlchemy já basta.

[Fonte: ARCHITECTURE-SPINE.md#Stack]

### O que já existe e esta story estende — leia antes de escrever

Três arquivos são **modificados**, não criados. Ler o estado atual deles evita reescrever o que já
está decidido:

| Arquivo | Estado hoje | O que esta story faz |
|---|---|---|
| `backend/app/core/config.py` | `Settings(BaseSettings)` com `app_nome`, `ambiente`, `cors_origens`. Exposta por `obter_settings()` com `@lru_cache`. Já tem um `field_validator(mode="before")` para o `cors_origens` | **Acrescenta** dois campos e um validador. Não reescreve a classe |
| `backend/pyproject.toml` | `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` fixados por `==`; grupo `dev` com `pytest` e `httpx` | **Acrescenta** três dependências, no mesmo estilo de versão fixa |
| `backend/.env.example` | Três chaves comentadas (`APP_NOME`, `AMBIENTE`, `CORS_ORIGENS`) | **Acrescenta** duas, no mesmo formato |

Não modificados, mas **não devem quebrar**: `app/main.py` (CORS e três handlers de erro),
`app/core/erros.py`, `app/api/saude.py` e os 14 testes existentes. Nenhum deles precisa saber que
existe banco. Se algum precisar mudar para esta story funcionar, algo foi feito errado.

`app/models/` e `app/services/` existem hoje **vazias, só com `__init__.py`** — foi de propósito,
para as stories seguintes não improvisarem onde as coisas moram. Esta é a story que enche a
primeira delas.

### O modelo `Usuario`

Tabela `usuario`, no singular, `snake_case`, domínio em português —
`ARCHITECTURE-SPINE.md#Convenções de Consistência`.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `Uuid` (UUIDv4) | Chave primária. `default=uuid.uuid4` no lado do Python — não depende de extensão do Postgres |
| `nome` | `String(120)`, `NOT NULL` | — |
| `email` | `String(255)`, `NOT NULL`, `unique=True` | Ver a nota de normalização abaixo |
| `senha_hash` | `String(255)`, `NOT NULL` | Só a coluna. **Nada é hasheado nesta story** — Argon2id entra na 1.4. Um hash Argon2id tem ~97 caracteres; 255 dá folga para trocar de parâmetros |
| `papel` | `String(20)`, `NOT NULL` | `CHECK (papel IN ('ORGANIZADOR','CLIENTE','PORTARIA'))`, nomeado `papel_valido` |
| `criado_em` | `DateTime(timezone=True)`, `NOT NULL`, `server_default=func.now()` | `TIMESTAMPTZ` em UTC — AD-11 |

**`criado_em` não está no AC1, e entra mesmo assim.** Três motivos concretos: o seed da Story 1.7
precisa de um critério de ordenação estável, "quando esta conta foi criada" é a primeira pergunta de
qualquer depuração, e acrescentar coluna depois é uma segunda migração para algo que custa uma linha
agora. É a única coluna além das que o AC lista — não adicione outras "por precaução".

**E-mail e maiúsculas — convenção que nasce aqui.** O `UNIQUE` do Postgres diferencia maiúsculas de
minúsculas: `Igor@x.com` e `igor@x.com` conviveriam como duas contas. A convenção do projeto é
**gravar sempre em minúsculas, normalizando na entrada**. Nesta story não há entrada nenhuma — é a
Story 1.5 (cadastro) que aplica, e a 1.4 (login) que precisa buscar do mesmo jeito. Está escrito aqui
porque é onde a coluna nasce; a alternativa (índice funcional em `lower(email)`) foi descartada por
resolver no banco um problema que uma linha de service resolve, ao custo de uma consulta que precisa
lembrar de usar `lower()` para bater com o índice.

[Fonte: epics.md#Story 1.3, ARCHITECTURE-SPINE.md#AD-9, #AD-11, #Semente Estrutural]

### `Base` e convenção de nomes

```python
convencao_de_nomes = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

Com ela, o `CheckConstraint(name="papel_valido")` vira `ck_usuario_papel_valido` e o e-mail vira
`uq_usuario_email` — nomes determinísticos, iguais na sua máquina e na Railway.

Sem ela, o Postgres batiza as constraints sozinho e o Alembic passa a gerar `downgrade()` que tenta
derrubar constraint por um nome que pode não existir naquele banco. É o tipo de coisa que só aparece
no dia do deploy. Isso vale para todas as tabelas das Epics 2 a 5 — a `Base` nasce certa agora ou
todas herdam o problema.

### Alembic — o que a story exige do setup

- **Diretório `migrations/`**, não `alembic/`. É o que a árvore da arquitetura declara e é o que os
  READMEs vão apontar
- **A URL não mora no `alembic.ini`.** Ela vem do `env.py`, de `obter_settings().database_url`.
  O `alembic init` grava um exemplo (`driver://user:pass@localhost/dbname`) — esvazie a linha. É o
  ponto mais provável do projeto para uma credencial vazar
- **`compare_type=True`** no `context.configure` de ambos os modos (online e offline). Sem isso, uma
  mudança de tipo de coluna passa despercebida pelo `--autogenerate` nas stories seguintes
- **`--autogenerate` é ponto de partida, não resultado.** Ele erra em constraint, em `server_default`
  e em ordem de operações. Leia a migração gerada linha a linha antes de aplicar
- **Uma migração por story que mexe em schema.** As próximas: 2.3 (evento, setor), 2.5
  (`evento_portaria`), 3.5 (reserva, item_reserva), 3.9 (ingresso), 4.3 (`share_token`), 5.2
  (`usado_em`, `validado_por`). Esta é a raiz da cadeia — `down_revision = None`

[Fonte: ARCHITECTURE-SPINE.md#Convenções de Consistência (Migrações), #Árvore]

### A fixture não pode migrar o banco de desenvolvimento

**O maior risco desta story, e ele apaga dados.** A fixture da T8 começa com `alembic downgrade
base` — que derruba a tabela. Se o `env.py` resolver a URL sempre por `obter_settings().database_url`,
um `uv run pytest` distraído zera o banco de desenvolvimento, e mais adiante, com o seed da Story 1.7
dentro, isso custa uma reconstrução inteira.

O contrato que impede isso tem duas pontas, e as duas precisam existir:

1. **No `env.py`:** a URL do `alembic.ini` tem precedência sobre a `Settings`. Como a T7 esvazia essa
   linha do `.ini`, o uso normal na linha de comando cai na `Settings` e usa o banco de
   desenvolvimento — que é o comportamento desejado
2. **No `conftest.py`:** a fixture monta um `Config("alembic.ini")` e chama
   `set_main_option("sqlalchemy.url", obter_settings().database_url_teste)` **antes** de qualquer
   `command.upgrade`/`command.downgrade`. Assim o Alembic recebe a URL de teste explicitamente, e
   nunca por acidente

Escreva um teste que prove a ponte: a fixture ativa, consultar `current_database()` na sessão de
teste deve devolver `rockhub_teste`. É barato e transforma um risco silencioso em falha visível.

Alternativa descartada: apontar `DATABASE_URL` para o banco de teste por variável de ambiente dentro
do `pytest`. Funciona, mas depende de a variável ser exportada antes do `@lru_cache` de
`obter_settings()` ser preenchido — uma ordem de import invisível no código, que quebra no dia em que
alguém importar `app.main` mais cedo.

### Armadilhas específicas desta story

Cada uma destas já custou tempo a alguém. Em ordem de probabilidade:

1. **`postgresql://` não usa o psycopg 3.** O SQLAlchemy resolve `postgresql://` para o **psycopg2**,
   que não está instalado, e o erro (`ModuleNotFoundError: No module named 'psycopg2'`) não diz que o
   problema é a URL. O esquema correto é **`postgresql+psycopg://`**. A Railway injeta `DATABASE_URL`
   como `postgresql://` ou `postgres://` — por isso o validador da T3 normaliza os três casos. Fazer
   isso agora resolve de graça uma armadilha da Story 1.8

2. **`env.py` sem importar os modelos gera migração vazia.** O `alembic init` escreve
   `target_metadata = None`. Trocar por `Base.metadata` **não basta**: se ninguém importar
   `app.models.usuario`, a classe nunca é registrada no metadata e o `--autogenerate` produz um
   `upgrade()` com `pass`. O import precisa estar explícito no `env.py` (via `app.models`, que a T5
   faz reexportar). Sintoma: migração gerada sem nenhum `create_table`

3. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** Já documentado na Story
   1.1: `uv run pytest` e `uv run uvicorn` falham com `os error 4551`. O contorno é chamar pelo
   módulo, e vale para o Alembic também:
   ```bash
   uv run python -m alembic upgrade head
   uv run python -m pytest
   ```
   Os comandos canônicos do README continuam sendo `uv run alembic ...`, com o contorno logo abaixo —
   mesmo padrão que o `backend/README.md` já usa

4. **A aplicação não pode conectar na subida.** `create_engine()` não abre conexão, e é por isso que
   ele pode viver no import de `app/core/db.py`. O que quebraria: qualquer `engine.connect()`,
   `inspect(engine)` ou `create_all` em tempo de import. Se isso entrar, os testes de `/saude`
   passam a exigir Postgres e a Story 1.8 ganha um deploy que morre quando o banco demora a subir

5. **Porta 5432 ocupada.** Se já houver um Postgres na máquina, o `docker compose up` falha com
   `port is already allocated`. Saída: mapear `5433:5432` no Compose e ajustar a porta no
   `.env.example`. Se precisar mudar, mude nos dois lugares — e diga ao Igor, porque muda o README

6. **`docker compose down` sem `-v` preserva o volume.** Para testar de verdade "banco vazio" do AC1
   e do AC3, é `docker compose down -v`. Sem o `-v` o banco reaparece migrado e o teste do zero é uma
   ilusão

7. **`server_default=func.now()` fixa `now()` no banco, não `datetime.utcnow()` no Python.** É o que
   se quer (AD-11: tempo em UTC, gerado por quem tem a hora canônica). Não troque por `default=` do
   lado do Python "para ficar igual" — passariam a existir duas fontes de hora

8. **`docker compose` (com espaço) é o Compose v2**, embutido no Docker atual. Em máquina com o v1
   antigo o comando é `docker-compose` (com hífen). Os READMEs usam a forma v2, que é a atual; se a
   máquina do Igor só tiver a v1, avise em vez de reescrever o README para a forma antiga

### Convenções que valem daqui para a frente

- **`app/core/db.py` é o único lugar que cria engine e sessão.** Nenhum service instancia `Session`
  por conta própria; todos recebem por dependência
- **Transação é responsabilidade do service.** `router` nunca abre transação nem dá `commit` —
  `ARCHITECTURE-SPINE.md#Convenções`. A dependência `obter_sessao()` só entrega e fecha
- **Nunca `create_all` fora de teste — e aqui, nem em teste.** Toda mudança de schema é migração
  Alembic versionada. É o AC2
- **`app/repositories/` não existe e não vai existir.** Se der vontade de criar ao escrever o
  primeiro acesso a dados, pare: a decisão está tomada e documentada no README da raiz
- **Estilo tipado do SQLAlchemy 2.0** em todos os modelos: `Mapped[tipo]` + `mapped_column(...)`.
  O `Column()` do estilo 1.x não convive bem com o `Mapped` e produz modelos meio tipados
- **Dinheiro em centavos, `BIGINT`, campo sufixado `_centavos`** — não aparece nesta story, aparece
  na 2.3. Está aqui porque é a `Base` desta story que as tabelas de lá vão herdar

### Estrutura alvo ao fim desta story

```text
docker-compose.yml            # NOVO — Postgres 16, volume nomeado, healthcheck
docker/
  initdb/
    01-cria-banco-de-teste.sql  # NOVO — cria rockhub_teste na inicialização
backend/
  alembic.ini                 # NOVO — script_location=migrations, url vazia
  pyproject.toml              # +sqlalchemy, +alembic, +psycopg[binary]
  uv.lock                     # regerado
  .env.example                # +DATABASE_URL, +DATABASE_URL_TESTE
  app/
    core/
      config.py               # +database_url, +database_url_teste, +normalizador
      db.py                   # NOVO — engine, SessaoLocal, obter_sessao
    models/
      __init__.py             # reexporta Base e Usuario
      base.py                 # NOVO — DeclarativeBase + naming_convention
      usuario.py              # NOVO — PapelUsuario + Usuario
  migrations/                 # NOVO
    env.py                    # URL da Settings, target_metadata=Base.metadata
    script.py.mako
    versions/
      2026...._cria_tabela_usuario.py
  tests/
    conftest.py               # NOVO — fixtures de banco migrado
    test_migracoes.py         # NOVO
    test_usuario.py           # NOVO
```

`app/services/` continua vazia — o primeiro service nasce na Story 1.4, com o login. Não crie
`app/services/usuario.py` "já que estamos aqui": service sem consumidor é service que a próxima
story reescreve.

[Fonte: ARCHITECTURE-SPINE.md#Árvore]

### Comandos que esta story precisa deixar funcionando

Vão para os dois READMEs e são os mesmos que a Story 1.8 vai usar no deploy da Railway.

```bash
# da raiz do repositório
docker compose up -d          # Postgres 16 em localhost:5432
docker compose ps             # conferir que está saudável
docker compose down -v        # derruba e apaga o volume (banco do zero)

cd backend
cp .env.example .env          # no Windows: copy .env.example .env
uv sync

uv run alembic upgrade head                                  # aplica as migrações
uv run alembic downgrade base                                # desfaz tudo
uv run alembic revision --autogenerate -m "descrição"        # nova migração
uv run alembic current                                       # em que revisão o banco está

uv run pytest                 # agora exige o Compose no ar
```

O comando de produção da Story 1.8 vai ser `alembic upgrade head` antes de subir o uvicorn. Por isso
ele precisa funcionar contra um banco vazio, sem nenhum passo prévio — é o AC3.

### Escopo — o que NÃO fazer aqui

Login, cadastro, hash de senha, JWT, cookie, dependência de papel, `GET /auth/eu`, seed, qualquer
endpoint novo, qualquer schema Pydantic de usuário, e as tabelas `evento`, `setor`, `reserva`,
`item_reserva`, `ingresso` e `evento_portaria`. Cada uma tem a sua story — 1.4, 1.5, 1.6, 1.7, e as
Epics 2 e 3.

É tentador criar as outras tabelas na mesma migração, "já que o diagrama de entidades está pronto".
**Não crie.** Cada tabela nasce na story que a usa, com as constraints que aquela story precisa
justificar — a `setor` sem o `CHECK` do AD-3 seria pior que não existir, e o AD-3 só é decidido de
verdade na Story 2.3.

Também não toque em `frontend/`. Esta story é backend e raiz do repositório, só.

### Testing

**Postgres real, com o schema criado pelo próprio Alembic** — decisão do Igor. A fixture roda
`downgrade base` seguido de `upgrade head` contra `DATABASE_URL_TESTE`, o que faz cada execução da
suíte verificar a migração de ida e de volta antes de qualquer asserção.

Os testes desta story:

| Arquivo | O que prova | AC |
|---|---|---|
| `test_migracoes.py` | `upgrade head` num banco vazio cria a tabela `usuario`; `downgrade base` a derruba por inteiro; `upgrade` de novo funciona | 1, 3 |
| `test_migracoes.py` | Colunas e tipos por `sqlalchemy.inspect`: `id` UUID, `email` com constraint única, `criado_em` `TIMESTAMPTZ` | 1 |
| `test_usuario.py` | Inserir dois usuários com o mesmo e-mail levanta `IntegrityError` | 1 |
| `test_usuario.py` | Inserir `papel='ADMIN'` levanta `IntegrityError` — é o `CHECK` recusando | 1 |
| `test_usuario.py` | Inserir sem informar `id` gera UUID; `criado_em` vem preenchido e com timezone | 1 |
| `test_migracoes.py` | Com a fixture ativa, `SELECT current_database()` devolve `rockhub_teste` — a trava contra migrar o banco de desenvolvimento | 3 |

Os 14 testes existentes (`test_saude.py`, `test_erros.py`, `test_config.py`) **continuam passando com
o Postgres desligado** — nenhum deles toca banco, e as fixtures novas não podem mudar isso. Se
`uv run pytest` passar a falhar em `test_saude.py` sem o Compose, algo conecta cedo demais.

Que `uv run pytest` passe a exigir o banco no ar é o custo aceito da decisão, e **precisa estar
escrito no `backend/README.md`** — a Story 6.2 valida o README numa máquina limpa.

### Inteligência das stories anteriores

**Da 1.1 (backend):**

- **`Settings` já existe** com `@lru_cache` em `obter_settings()`, pensada para virar dependência do
  FastAPI e para ser substituída por `dependency_overrides` em teste. **Estenda, não recrie**
- **O `cors_origens` já usa `NoDecode` + `field_validator(mode="before")`.** O normalizador de
  `DATABASE_URL` da T3 segue exatamente esse padrão — há um exemplo pronto no arquivo
- **`.gitignore` único, na raiz**, a pedido do Igor. Não crie `backend/.gitignore` nem
  `docker/.gitignore`. O volume do Compose é nomeado e vive no Docker, então não há nada novo a
  ignorar nesta story
- **Windows App Control** bloqueia os `.exe` da virtualenv — contorno pelo módulo (armadilha 3)
- **Aviso de depreciação do Starlette 1.6** sobre `httpx` no `TestClient` é conhecido e não é falha

**Da 1.2 (frontend):**

- **Nada desta story afeta o frontend.** Ele não chama a API ainda — a primeira chamada real é o
  login da Story 1.4. Não há contrato novo a propagar
- **O padrão dos READMEs**: primeira pessoa, denso, cada decisão com "o que caiu e por quê". Foi
  estabelecido na 1.1 e mantido na 1.2 — é o que a T10 continua

**Do estado do repositório:** último commit `c801bef feat: Story 1.2: Esqueleto do frontend com a
identidade aplicada`, na branch `epic-1---fundacao-acesso-e-primeiro-deploy`, árvore limpa. Stories
1.1 e 1.2 estão em `review`; o code review acontece ao fim da epic, não a cada story.

[Fonte: _bmad-output/implementation-artifacts/1-1-esqueleto-do-backend-que-responde.md,
_bmad-output/implementation-artifacts/1-2-esqueleto-do-frontend-com-a-identidade-aplicada.md]

### Project Structure Notes

Esta story ocupa `backend/` e a **raiz do repositório** (`docker-compose.yml`, `docker/initdb/`,
`README.md`). É a primeira que cria arquivo na raiz desde o `.gitignore` — o Compose fica lá, e não
em `backend/`, porque o banco é infraestrutura do projeto inteiro: a Story 1.7 vai semear por ele e o
frontend, em desenvolvimento, depende do backend que depende dele.

**Não toque em `frontend/`.** Nem no `frontend/README.md` — ver a última subtarefa da T10.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`, sem repositórios
- [Source: ARCHITECTURE-SPINE.md#Convenções de Consistência] — migrações Alembic, `snake_case`,
  UUIDv4, `TIMESTAMPTZ` em UTC, transação no service, configuração por ambiente
- [Source: ARCHITECTURE-SPINE.md#Stack] — PostgreSQL 16, SQLAlchemy 2, Alembic
- [Source: ARCHITECTURE-SPINE.md#Semente Estrutural] — `USUARIO` carrega o papel; diagrama de
  entidades com as tabelas que vêm depois
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel único por conta, três valores fechados
- [Source: ARCHITECTURE-SPINE.md#AD-11] — dinheiro em centavos, tempo em UTC
- [Source: ARCHITECTURE-SPINE.md#AD-15] — `senha_hash` guarda Argon2id (aplicado na Story 1.4)
- [Source: ARCHITECTURE-SPINE.md#Árvore] — `migrations/` e `models/` no backend
- [Source: backend/app/core/config.py] · [Source: backend/pyproject.toml] ·
  [Source: backend/.env.example] — os três arquivos modificados
- [Source: backend/README.md#Configuração] — tabela de variáveis a estender
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`.
   O Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Confirme com o Igor antes de rodar `docker compose up`** se ele não estiver acompanhando — vai
   baixar a imagem do Postgres 16 e ocupar a porta 5432
3. **Atualize os READMEs antes de dar a story por concluída** — `backend/README.md` e o da raiz, em
   primeira pessoa, com o que foi feito **e por quê**. As cinco entradas de decisão da T10 são a
   parte que o desafio avalia
4. **Decisão de produto ou de modelagem é do Igor.** As quatro desta story já estão respondidas; se
   aparecer uma quinta — nome de tabela, coluna a mais, política de índice — pergunte em vez de
   escolher
5. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- `docker compose up -d` (com a imagem `postgres:16` baixada do zero) → `docker compose ps` mostrou
  `db` saudável; `\l` no `psql` confirmou `rockhub` e `rockhub_teste` criados pelo script de initdb.
- `uv run alembic revision --autogenerate -m "cria tabela usuario"` gerou
  `migrations/versions/20260810_b750db91bf49_cria_tabela_usuario.py` — revisado à mão: `CheckConstraint`
  nomeado `ck_usuario_papel_valido`, `UniqueConstraint` `uq_usuario_email`, `downgrade()` derruba a
  tabela por inteiro. Nada precisou ser corrigido manualmente.
- `uv run alembic upgrade head` + `\d usuario` no `psql` confirmaram o schema esperado (AC1).
- AC3, literal: `docker compose down -v && docker compose up -d` (banco vazio de verdade, sem
  volume) → `uv run alembic upgrade head` sem erro; depois `downgrade base` → `upgrade head` de novo
  sem erro.
- `uv run pytest -v`: 20 passed (14 anteriores + 6 novos), 0 falhas, 1 warning pré-existente do
  Starlette (não relacionado a esta story).
- Um `SAWarning: transaction already deassociated from connection` apareceu nos dois testes que
  provocam `IntegrityError` de propósito — corrigido isolando cada `flush()` de teste num
  `SAVEPOINT` reaberto via evento `after_transaction_end` em `conftest.py`. Suíte voltou a rodar sem
  warnings novos.
- `uv run uvicorn app.main:app --port 8123` com o Postgres **desligado** (`docker compose down`
  sem `-v`) → `/saude` respondeu `200 OK` normalmente, confirmando que `create_engine()` não abre
  conexão no import (AC4/armadilha 4).
- Grep de segurança: `create_all` → zero ocorrências em `backend/`; `postgresql://`/`postgres://` →
  só aparecem no normalizador de `app/core/config.py` e no comentário do `.env.example`;
  `psycopg2` → só no comentário que explica a armadilha; `sqlalchemy.url` do `alembic.ini` → vazio,
  sem credencial.

### Completion Notes List

- Implementadas as 10 tarefas da story. Todos os 4 ACs verificados manualmente, além da suíte
  automatizada (20 testes, 6 novos: 3 em `test_migracoes.py`, 3 em `test_usuario.py`).
- Segui a decisão do Igor de `docker-compose.yml` na raiz do repositório, Postgres 16 com volume
  nomeado `rockhub-pgdata`, sem a chave `version:` (obsoleta no Compose v2).
- `PapelUsuario` como `str, Enum` em `app/models/usuario.py`, único enum de papel do projeto — as
  Stories 1.4/1.5/1.6 devem importar dele, não redeclarar.
- `env.py` do Alembic resolve a URL com a precedência exigida pelas Dev Notes: `sqlalchemy.url` do
  `.ini` (deixado vazio) tem prioridade sobre `Settings.database_url`; a fixture de teste sobrescreve
  essa opção em código antes de qualquer `command.upgrade`/`downgrade`, nunca por variável de
  ambiente — é a trava contra migrar o banco de desenvolvimento por acidente.
- Ajuste não previsto no texto da story, mas dentro do escopo de "testes contra Postgres real": a
  fixture `sessao` em `conftest.py` usa um `SAVEPOINT` reaberto a cada transação encerrada (padrão
  documentado do SQLAlchemy para suíte de teste), porque sem isso um `flush()` que falha de
  propósito (os dois testes de `IntegrityError`) deassocia a transação externa e o `rollback()` do
  teardown emite um `SAWarning`. É infraestrutura de teste, não mudança de comportamento do modelo.
- Não toquei em `frontend/` nem em `frontend/README.md`, como a story instrui.
- Backend segue funcionando sem Postgres no ar (testado explicitamente) — os testes de `/saude`,
  erros e config continuam isolados do banco.
- `backend/README.md` e o `README.md` da raiz atualizados em primeira pessoa, com as cinco decisões
  desta story (Postgres por Compose, SQLAlchemy síncrono, VARCHAR+CHECK, Alembic sem `create_all`,
  testes contra Postgres real) cada uma com o que caiu e por quê.
- Ao final da sessão, o Postgres local ficou **no ar** (`docker compose up -d`) e migrado
  (`alembic upgrade head`), para o Igor poder inspecionar o resultado sem precisar repetir os
  comandos.

### File List

- `docker-compose.yml` (novo)
- `docker/initdb/01-cria-banco-de-teste.sql` (novo)
- `backend/pyproject.toml` (modificado — +sqlalchemy, +alembic, +psycopg[binary])
- `backend/uv.lock` (regenerado por `uv sync`)
- `backend/.env.example` (modificado — +DATABASE_URL, +DATABASE_URL_TESTE)
- `backend/app/core/config.py` (modificado — +database_url, +database_url_teste, +normalizador de
  esquema)
- `backend/app/core/db.py` (novo — engine, SessaoLocal, obter_sessao)
- `backend/app/models/base.py` (novo — Base declarativa + convenção de nomes)
- `backend/app/models/usuario.py` (novo — PapelUsuario + Usuario)
- `backend/app/models/__init__.py` (modificado — reexporta Base e Usuario)
- `backend/alembic.ini` (novo)
- `backend/migrations/env.py` (modificado — target_metadata, resolução de URL, compare_type)
- `backend/migrations/script.py.mako` (novo, gerado pelo `alembic init`)
- `backend/migrations/README` (novo, gerado pelo `alembic init`)
- `backend/migrations/versions/20260810_b750db91bf49_cria_tabela_usuario.py` (novo)
- `backend/tests/conftest.py` (novo — fixtures `engine_teste` e `sessao`)
- `backend/tests/test_migracoes.py` (novo)
- `backend/tests/test_usuario.py` (novo)
- `backend/README.md` (modificado — seção de banco, estrutura, testes, histórico)
- `README.md` (modificado — pré-requisitos, passo do banco, estado atual, stack, cinco decisões)

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.3 criada e contextualizada. Quatro decisões do Igor incorporadas: Postgres por `docker-compose.yml` na raiz, SQLAlchemy síncrono, `papel` como VARCHAR + `CHECK`, testes contra Postgres real migrado pelo Alembic. AC3 e AC4 acrescentados aos dois do `epics.md` |
| 2026-08-10 | Story implementada: T1–T10 completas. Postgres 16 por Compose, `Settings` estendida, `app/core/db.py`, `Base` declarativa, modelo `Usuario` + `PapelUsuario`, Alembic em `migrations/` com a migração raiz, testes contra `rockhub_teste` migrado pelo próprio Alembic (20 passando), READMEs atualizados. Status → `review` |
