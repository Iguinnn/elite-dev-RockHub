---
baseline_commit: f2751a4b3f0e2664ba1d7b5afe4a6be05c9d53b1
---

# Story 1.1: Esqueleto do backend que responde

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **Primeira story do projeto: não existe código ainda.**

## Story

Como desenvolvedor,
quero um backend FastAPI que sobe e responde a uma chamada de saúde,
para ter uma base verificável antes de escrever qualquer regra de negócio.

## Acceptance Criteria

1. **Given** o repositório recém-clonado com Python 3.12
   **When** eu instalo as dependências e subo o servidor
   **Then** `GET /saude` responde `200` com `{"status": "ok"}`
   **And** `/docs` mostra a documentação automática do FastAPI

2. **Given** a estrutura de pastas
   **When** eu a inspeciono
   **Then** existem `app/api/`, `app/services/`, `app/models/`, `app/schemas/`, `app/core/`
   **And** **não existe** pasta `repositories/` — o paradigma é `routers → services → models`

3. **Given** qualquer configuração sensível
   **When** eu procuro no código
   **Then** ela é lida de variável de ambiente por uma classe `Settings` do Pydantic
   **And** nenhum segredo está versionado

## Tasks / Subtasks

- [x] **T1. Criar o projeto Python em `backend/`** (AC: 1)
  - [x] `backend/pyproject.toml` com Python `>=3.12` e as dependências fixadas abaixo
  - [x] Gerar lockfile (`uv lock`) e versioná-lo
  - [x] `backend/.gitignore` para `.venv/`, `__pycache__/`, `.env`

- [x] **T2. Montar a árvore de pastas do paradigma** (AC: 2)
  - [x] Criar `app/api/`, `app/services/`, `app/models/`, `app/schemas/`, `app/core/`
  - [x] `__init__.py` em cada pacote
  - [x] **NÃO criar** `app/repositories/`

- [x] **T3. Configuração por ambiente com `Settings`** (AC: 3)
  - [x] `app/core/config.py` com `Settings(BaseSettings)` de `pydantic-settings`
  - [x] Campos desta story: `app_nome`, `ambiente` (`local|producao`), `cors_origens`
  - [x] `Settings` exposto por função cacheada (`@lru_cache`) para virar dependência do FastAPI
  - [x] `backend/.env.example` com as chaves e valores de exemplo — **sem segredo real**

- [x] **T4. Aplicação FastAPI e rota de saúde** (AC: 1)
  - [x] `app/main.py` criando o `FastAPI(title=...)`
  - [x] `app/api/saude.py` com `router = APIRouter()` e `GET /saude` → `{"status": "ok"}`
  - [x] Registrar o router em `main.py` via `include_router`
  - [x] Middleware de CORS lendo origens de `Settings` (o frontend virá na Story 1.2)

- [x] **T5. Formato de erro padronizado** (AC: 3)
  - [x] `app/core/erros.py` com exceção de domínio carregando `codigo` e `mensagem`
  - [x] Exception handler em `main.py` devolvendo `{"erro": {"codigo": "...", "mensagem": "..."}}`
  - [x] Este é o contrato que **todas** as stories seguintes vão usar — acertar aqui evita retrabalho

- [x] **T6. Teste da rota de saúde** (AC: 1)
  - [x] `backend/tests/test_saude.py` usando `TestClient`
  - [x] Verifica status `200` e corpo exato

- [x] **T7. Documentação** (obrigatório — regra do projeto)
  - [x] Criar `backend/README.md`: o que é, como instalar, como rodar, como testar, estrutura de pastas
  - [x] Atualizar `README.md` da raiz: seção "Como executar" ganha o backend; seção de decisões ganha
        a entrada sobre o paradigma sem camada de repositórios
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "optei por")

## Dev Notes

### Stack fixada — versões conferidas na web em 10/08/2026

| Pacote | Versão | Papel |
|---|---|---|
| Python | 3.12 | FastAPI exige `>=3.10`; 3.12 é o alvo |
| `fastapi` | 0.141.1 | Framework |
| `uvicorn[standard]` | 0.52.1 | Servidor ASGI |
| `pydantic` | 2.13.4 | Validação (vem com o FastAPI) |
| `pydantic-settings` | 2.15.0 | `Settings` por variável de ambiente — pacote **separado** do `pydantic` |
| `pytest` | atual | Testes |
| `httpx` | atual | Necessário para o `TestClient` do FastAPI |

**Não instale ainda:** SQLAlchemy, Alembic, argon2-cffi, psycopg. Eles entram nas Stories 1.3 e 1.4.
Instalar antes gera dependência morta e polui o lockfile.

O gerenciador é o **uv** (já instalado na máquina, em `C:\Users\Asus\.local\bin`).

### Paradigma — vinculante

`routers → services → models`. Dependência sempre para dentro, nunca o inverso, nunca pulando camada.

| Camada | Pasta | Responsabilidade |
|---|---|---|
| `routers` | `app/api/` | HTTP: validação de entrada, autenticação, status. Sem regra de negócio, sem acesso a banco |
| `services` | `app/services/` | Regra de negócio, transações e acesso ao banco |
| `models` | `app/models/` | SQLAlchemy (a partir da Story 1.3) |

**Não existe camada de repositórios, e isso foi decidido de propósito** — a `Session` do SQLAlchemy já
cumpre esse papel, e a camada extra viraria repasse sem separar nada neste tamanho de projeto.
Se você sentir vontade de criar `app/repositories/`, pare: é uma decisão já tomada e revertê-la
silenciosamente quebra o contrato.
[Fonte: ARCHITECTURE-SPINE.md#Design Paradigm]

### Convenções que nascem aqui e valem para o projeto inteiro

- **Nomes:** Python e banco em `snake_case`; domínio em português (`evento`, `setor`, `reserva`,
  `ingresso`) para bater com o enunciado do desafio
- **Erro da API:** sempre `{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}}`.
  O `codigo` é estável e é por ele que o frontend decide o texto — nunca pela mensagem
- **Configuração:** só por variável de ambiente, lida por `Settings` do Pydantic. **Segredo nenhum no
  repositório**
- **Datas:** UTC, ISO-8601 (relevante a partir da Story 1.3)
- **Dinheiro:** inteiro em centavos, campo sufixado `_centavos` (relevante na Epic 2)

[Fonte: ARCHITECTURE-SPINE.md#Convenções de Consistência]

### Estrutura alvo ao fim desta story

```text
backend/
  pyproject.toml
  uv.lock
  .env.example
  .gitignore
  README.md
  app/
    __init__.py
    main.py            # cria o FastAPI, CORS, handler de erro, include_router
    api/
      __init__.py
      saude.py         # GET /saude
    services/
      __init__.py      # vazio nesta story
    models/
      __init__.py      # vazio nesta story
    schemas/
      __init__.py      # vazio nesta story
    core/
      __init__.py
      config.py        # Settings
      erros.py         # exceção de domínio + handler
  tests/
    __init__.py
    test_saude.py
```

Pastas vazias com `__init__.py` são intencionais: elas materializam o paradigma desde o primeiro
commit, para que as stories seguintes não improvisem onde colocar as coisas.

### Comandos que esta story precisa deixar funcionando

Estes vão para o `backend/README.md` e são os mesmos que a Story 1.8 vai usar no deploy da Railway.
Definir agora evita divergência depois.

```bash
cd backend
uv sync                                   # instala a partir do lockfile
uv run uvicorn app.main:app --reload      # desenvolvimento, porta 8000
uv run pytest                             # testes
```

`app.main:app` é o caminho do objeto FastAPI. **Não mude esse nome nem esse local** — a Story 1.8
vai apontar o comando de produção para exatamente ele.

Em produção a porta vem do ambiente (`--port $PORT`), porque a Railway a injeta. Não é escopo desta
story configurar isso, mas **não fixe a porta no código** — deixe-a como argumento do uvicorn.

### Cuidados específicos desta story

- **`pydantic-settings` é pacote separado.** Em Pydantic v2, `BaseSettings` não vive mais no
  `pydantic` — importar de lá dá erro. É `from pydantic_settings import BaseSettings`
- **CORS agora, não depois.** O frontend (Story 1.2) e o deploy (1.8/1.9) vão precisar, e o cookie
  de sessão `SameSite` da Story 1.4 depende de CORS bem configurado. Deixar a origem configurável
  desde já evita mexer em `main.py` três vezes
- **A rota é `/saude`, em português.** É o que a Story 1.8 vai checar no deploy da Railway
- **Não crie autenticação, banco ou modelo nenhum.** Escopo desta story é o esqueleto que responde

### Escopo — o que NÃO fazer aqui

Banco de dados, SQLAlchemy, Alembic, modelo de usuário, login, seed, Docker, CI. Cada um tem sua
story. Antecipar cria trabalho que a story seguinte vai ter que desfazer.

### Testing

- `pytest` com `TestClient` do FastAPI (que exige `httpx` instalado)
- Nesta story, um teste basta: `/saude` responde `200` com o corpo exato
- Testes ficam em `backend/tests/`, espelhando a estrutura de `app/`
- O desafio cita "testes básicos" como diferencial — o hábito começa aqui, na primeira story

### Project Structure Notes

O repositório é um monorepo com `backend/` e `frontend/` já criados na raiz, ao lado de `docs/` e
`_bmad-output/`. Esta story ocupa **apenas** `backend/`. Não toque em `frontend/`.

O `.gitignore` da raiz é o template Python do GitHub e **não cobre `node_modules/`** — irrelevante
para esta story, mas será um problema na Story 1.2. O Igor já está ciente.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md#Design Paradigm]
- [Source: ARCHITECTURE-SPINE.md#Convenções de Consistência] — formato de erro, nomes, configuração
- [Source: ARCHITECTURE-SPINE.md#Stack] — versões fixadas
- [Source: ARCHITECTURE-SPINE.md#AD-2] — credencial só no ambiente do backend
- [Source: CLAUDE.md] — regra dos READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`.
   O Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída** — `backend/README.md` e o da raiz,
   em primeira pessoa, com o que foi feito **e por quê**
3. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

**Duas descobertas de ambiente, ambas contornadas — nenhuma altera o código:**

1. **Windows App Control bloqueia os `.exe` da virtualenv.** `uv run pytest` e
   `uv run uvicorn` falham com `os error 4551` ("Uma política de Controle de Aplicativo bloqueou
   este arquivo") nesta máquina. Chamar pelo módulo funciona sem nenhuma diferença de
   comportamento: `uv run python -m pytest`, `uv run python -m uvicorn app.main:app --reload`.
   Os comandos canônicos do README continuam sendo os da story (`uv run pytest`), com o contorno
   documentado logo abaixo deles.

2. **Aviso de depreciação do Starlette 1.6:** `Using httpx with starlette.testclient is
   deprecated; install httpx2 instead`. Os 7 testes passam; é aviso, não falha. Mantive o `httpx`
   porque é o que a story fixa — trocar por `httpx2` é decisão de dependência do Igor.

**Verificação manual do servidor** (uvicorn na porta 8123, além dos testes automatizados):
`GET /saude` → `200 {"status":"ok"}` · `/docs` → `200` · `/openapi.json` → `200`.
CORS conferido nos dois sentidos: com `Origin: http://localhost:3000` a resposta traz
`access-control-allow-origin`; com origem não listada, o cabeçalho não vem — o navegador barra.

### Completion Notes List

**AC1 — sobe e responde.** `uv sync` cria a `.venv/` com Python 3.12.13 (o `uv` baixou o
interpretador sozinho a partir do `.python-version`; a máquina só tinha 3.14). `GET /saude`
devolve `200 {"status": "ok"}` e `/docs` publica a documentação automática. Verificado por teste
automatizado e por chamada real ao servidor.

**AC2 — árvore do paradigma.** `app/api/`, `app/services/`, `app/models/`, `app/schemas/` e
`app/core/` criados, cada um com `__init__.py`. **Não existe `app/repositories/`** — as três
pastas ainda vazias existem justamente para que as stories seguintes não improvisem onde colocar
as coisas.

**AC3 — configuração e segredos.** Tudo que varia entre máquinas passa por `Settings`
(`pydantic-settings`), exposta por `obter_settings()` com `@lru_cache` para virar dependência do
FastAPI e permitir `dependency_overrides` em teste. O `.env` está no `.gitignore`; o versionado é
o `.env.example`, sem valor sensível.

**Decisão tomada dentro do escopo:** `CORS_ORIGENS` usa `NoDecode` + validador para aceitar lista
separada por vírgula em vez do JSON que o `pydantic-settings` espera por padrão em campos de
lista. Motivo: é o formato que se digita num painel de deploy, e JSON malformado em variável de
ambiente é um erro caro de diagnosticar. Relevante para a Story 1.8.

**Erro de domínio ganhou `status_http` (padrão 400).** A story pedia `codigo` e `mensagem`; sem o
status o contrato não conseguiria expressar o `409 ESTOQUE_INSUFICIENTE` e o
`402 PAGAMENTO_RECUSADO` que a arquitetura exige na Epic 3. Adicionar depois obrigaria a mexer no
handler e em todos os `raise` já escritos.

**Formato de erro unificado nas três origens** (ampliação de T5 aprovada pelo Igor durante a
implementação). Além do `ErroDeDominio`, `main.py` registra handlers para `HTTPException` (do
Starlette, do qual o do FastAPI herda) e `RequestValidationError`. Assim rota inexistente, método
errado e corpo reprovado saem no mesmo `{"erro": {"codigo", "mensagem"}}` — o frontend passa a ter
um caminho só. Os códigos das falhas do framework vêm da tabela `CODIGO_POR_STATUS`
(`404 → NAO_ENCONTRADO`, `403 → SEM_PERMISSAO`, …). O handler de HTTP preserva `exc.headers`, que
carrega o `Allow` do `405` e o `WWW-Authenticate` do `401`.

O erro de validação foi achatado em texto (`setor_id: campo obrigatório; quantidade: não é um
inteiro`) em vez de expor a lista aninhada do Pydantic. Contrato uniforme valeu mais que detalhe
estruturado — a alternativa exigiria uma terceira chave presente só neste caso.

**Continua fora:** exceção não tratada vira `500` com o texto padrão do Starlette. Tratá-la exige
decidir política de log, e observabilidade está no "Adiado" da arquitetura.

**`backend/.gitignore` foi criado e depois removido, a pedido do Igor.** O `.gitignore` da raiz é o
template Python do GitHub e já cobre tudo que a T1 pedia — `__pycache__/` (linha 2),
`.pytest_cache/` (51), `.env` (151), `.venv` (153) — e ainda `node_modules/` (226) e `.ruff_cache/`
(207). O `.env.example` **não** é pego, porque o padrão é o literal `.env`, não `.env*`. Um segundo
arquivo de ignore seria duplicação sem regra nova. A subtarefa segue marcada porque o efeito que
ela pedia está garantido, só que pelo arquivo da raiz.

**Testes:** 14 passando. Além do exigido pela story (rota de saúde), cobri o `/docs`, as três
origens de erro, a preservação do cabeçalho `Allow`, o registro dos handlers na app real e a
leitura de `Settings` do ambiente — os contratos que todas as stories seguintes vão herdar.

**Decisões do Igor durante a implementação:**

- Padronizar os três formatos de erro agora, e não depois — feito
- `frontend/README.md` fica vazio até a Story 1.2, apesar da regra dos três READMEs no CLAUDE.md.
  Esta story diz explicitamente "não toque em `frontend/`"
- `.gitignore` único, na raiz — feito

### File List

**Criados:**

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/.python-version`
- `backend/.env.example`
- `backend/README.md`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/api/__init__.py`
- `backend/app/api/saude.py`
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/core/erros.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/services/__init__.py`
- `backend/tests/__init__.py`
- `backend/tests/test_saude.py`
- `backend/tests/test_erros.py`
- `backend/tests/test_config.py`

**Modificados:**

- `README.md` — seções "Como executar", "Stack e estrutura", "Decisões" e "O que não está pronto"
- `.gitignore` — variantes de `.env` (com `!.env.example`), certificados, lixo de SO e saídas de build do front
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story 1.1 → `review`
- `_bmad-output/implementation-artifacts/1-1-esqueleto-do-backend-que-responde.md` — este arquivo

**Não versionados** (já cobertos pelo `.gitignore` da raiz): `backend/.venv/`,
`backend/.pytest_cache/`, `backend/__pycache__/`.

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.1 implementada: projeto `uv` com Python 3.12, árvore do paradigma `routers → services → models` sem camada de repositórios, `Settings` por variável de ambiente, CORS configurável, formato de erro, `GET /saude` e 7 testes. `backend/README.md` criado e `README.md` da raiz atualizado com as decisões |
| 2026-08-10 | Formato de erro unificado nas três origens (domínio, `HTTPException`, validação do Pydantic), a pedido do Igor. +7 testes, total de 14. READMEs atualizados |
| 2026-08-10 | `backend/.gitignore` removido: o `.gitignore` da raiz já cobre tudo. Um arquivo de ignore só, a pedido do Igor |
| 2026-08-10 | `.gitignore` da raiz reforçado: `.env.*` com exceção para `.env.example`, `*.pem`/`*.key`, lixo de SO e saídas de build do front. Status → `review` |
