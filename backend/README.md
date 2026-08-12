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
uv run python -m seeds.semear             # as 5 contas de avaliação — rodar de novo é seguro
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
| `COOKIE_SESSAO_NOME` | `rockhub_sessao` | Nome do cookie de sessão. ⚠️ **Não mexa nele** — leia o aviso abaixo |
| `TICKETMASTER_API_KEY` | `""` | Chave do portal da Ticketmaster, usada por `app/integrations/ticketmaster.py`. **Obrigatória em produção**; opcional em `local` (ver [Catálogo da Ticketmaster](#catálogo-da-ticketmaster)) |

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

O `uv run` na frente não é enfeite: os pré-requisitos deste projeto são `uv`, Docker e Node, e é o
próprio `uv` que baixa o Python 3.12. Numa máquina limpa — no Windows em especial, onde `python`
abre o stub da Microsoft Store — o comando sem ele falha.

⚠️ **`COOKIE_SESSAO_NOME` está documentada para você saber que ela existe e não tocá-la.** O
`frontend/src/lib/sessao.ts` procura o cookie por um literal, `"rockhub_sessao"`, porque o frontend
não tem como perguntar ao backend qual nome ele usou. Defini-la no painel da Railway faz o backend
gravar um cookie e o frontend procurar outro: o login responde `200`, o cookie chega no navegador, e
mesmo assim **todo mundo aparece deslogado** — masthead em `Entrar`, `/conta` rebatendo para o
login, sem um erro sequer na tela ou no log. Se um dia precisar mesmo trocar, troque nos dois lugares
no mesmo commit.

Em produção, uma variável a mais existe no ambiente da Railway e **não é campo da `Settings`**:

| Variável | Estado hoje | Quem vai lê-la |
|---|---|---|
| `TICKET_SIGNING_SECRET` | definida no ambiente, ninguém lê | Story 3.9 (assinatura do QR) |

O `extra="ignore"` da `Settings` a aceita sem declará-la. **Campo só nasce quando alguém for
consumir o valor** — declarar agora seria código que ninguém lê, com um validador ativo capaz de
derrubar a aplicação por causa de uma funcionalidade que ainda não existe. O que já vale desde hoje
é o lugar dela: ambiente do backend, nunca repositório (AD-2). `TICKETMASTER_API_KEY` seguiu esse
mesmo caminho até a Story 2.1 — a partir dela é campo de verdade, na tabela acima.

**Com `AMBIENTE=producao`, o valor de exemplo do `JWT_SECRET` derruba a aplicação na
inicialização**, com a mensagem dizendo o comando acima. Isso é de propósito: o ponto mais provável
de um segredo vazar não é alguém colar a chave no código — é o valor de exemplo continuar
funcionando e ninguém perceber. Um `JWT_SECRET` padrão rodando em produção é um segredo público
assinando sessões, e o deploy não teria como descobrir sozinho, porque *funciona*. Mesmo padrão
passou a valer para `TICKETMASTER_API_KEY` na Story 2.1, e vai valer para `TICKET_SIGNING_SECRET`
na Story 3.9 — cada uma com o seu próprio `model_validator`, e não o mesmo estendido: são motivos
diferentes de recusar a subida, e uma mensagem fundida manda quem depura procurar no lugar errado.

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
infraestrutura do projeto inteiro (é nele que o seed de [Dados semeados](#dados-semeados) grava, e é
a mesma instância de que o frontend depende em desenvolvimento).

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

## Dados semeados

As cinco contas de avaliação vêm de um comando só, rodado com o banco migrado:

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
| `PORTARIA` | Ana Sampaio | `portaria2@rockhub.dev` | `rockhub123` |

O relatório sai uma linha por conta, e o comando termina em `0`:

```
ORGANIZADOR  organizador@rockhub.dev   criada
CLIENTE      cliente@rockhub.dev       criada
CLIENTE      cliente2@rockhub.dev      criada
PORTARIA     portaria@rockhub.dev      criada
PORTARIA     portaria2@rockhub.dev     criada
As senhas estão no README da raiz, em "Contas semeadas".
```

Na segunda execução as cinco dizem `mantida`. Este é **o único caminho do sistema que cria conta com
papel diferente de `CLIENTE`** — `cadastrar()` fixa o papel em literal, e nenhuma rota oferece
alternativa.

**A segunda portaria entrou na Story 2.5**, e o NFR2 pede uma só. Semeei duas pelo mesmo motivo de
haver dois clientes: com uma conta só, a tela de escalação vira um item obrigatório que não se pode
não marcar — e, principalmente, o cenário que o AD-7 existe para provar (a portaria A **não** valida
o evento da portaria B) dependeria de o avaliador criar uma conta de portaria na mão. Conta de
portaria não se cria pela interface, de propósito. Sem a segunda semeada, o cenário simplesmente não
é demonstrável.

### Rodar de novo é seguro, e é o requisito central

A idempotência vem de **"já existe esse e-mail? então não insere"**. Não há `DELETE`, `TRUNCATE`,
`UPDATE` nem `drop` em lugar nenhum de `seeds/`, e não deve passar a haver: a Story 1.8 chama este
mesmo comando a cada deploy na Railway, e um seed que limpasse a tabela antes de inserir funcionaria
hoje e destruiria, no primeiro redeploy, o trabalho de quem estivesse avaliando. Conta criada por
`/cadastro` continua exatamente onde está.

Pelo mesmo motivo o script **não "conserta" conta nenhuma**. Se o e-mail já existir com nome ou senha
diferentes, os valores gravados ficam como estão — em produção, "consertar" significaria trocar a
senha de alguém no meio da avaliação. E se o e-mail existir com **outro papel** (alguém criou
`organizador@rockhub.dev` por `/cadastro`, e a conta nasceu `CLIENTE`), o script avisa e segue:

```
ORGANIZADOR  organizador@rockhub.dev   já existe com papel CLIENTE — não foi alterada
```

**Mesmo aí ele sai em `0`.** Na Story 1.8 o comando roda entre o `alembic upgrade head` e o
`uvicorn`: um `exit(1)` por causa de um aviso derrubaria o deploy inteiro, e a única saída seria
mexer no banco de produção às pressas. Falha de verdade — banco fora do ar, migração não aplicada —
continua estourando exceção e saindo diferente de zero, que aí é o comportamento certo.

### Duas armadilhas do comando

⚠️ **Com o `-m`, sempre.** `uv run seeds/semear.py` põe `backend/seeds/` no `sys.path` em vez de
`backend/`, e `import app.core.db` estoura `ModuleNotFoundError: No module named 'app'`. A correção é
o `-m` — **nunca** um `sys.path.append` no topo do script.

⚠️ **Rode a partir de `backend/`.** A `Settings` lê o `.env` do diretório corrente; da raiz do
repositório o script pegaria os valores padrão em vez dos seus. Hoje dá no mesmo, na Railway não daria.

**A senha não vai para o stdout**, de propósito. Ela está publicada num README, então não é segredo —
mas o mesmo comando roda no deploy, e o que ele imprime vai para o log de deploy. Credencial em log é
hábito que se leva junto para o dia em que a credencial importa, e não há ganho: quem rodou o comando
tem o README aberto.

## Estrutura

```text
backend/
  app/
    main.py          # cria o FastAPI, aplica CORS, registra o handler de erro e os routers
    api/             # routers: HTTP puro — entrada, autenticação, status
      saude.py
      auth.py         # POST /auth/cadastro, /auth/login, /auth/logout · GET /auth/eu
      organizador.py  # GET /organizador/catalogo (exceção ao paradigma) · GET /organizador/portarias
                      # · POST /organizador/eventos · GET /organizador/eventos e /eventos/{id} (2.6)
      publico.py      # GET /eventos (com ?q=, ?cidade=, ?periodo=) e /eventos/cidades — sem conta
    services/        # regra de negócio, transações e acesso ao banco
      autenticacao.py # autenticar() e obter_usuario() (só leem) · cadastrar() (grava e commita)
      evento.py       # publicar() (2.4/2.5) · listar_programacao() com os filtros no where (3.2)
                      # · listar_portarias() — quem pode ser escalado (2.5)
                      # · listar_do_organizador() e obter_do_organizador() — as leituras da 2.6
                      # · listar_programacao() — a leitura pública da 3.1
    models/          # SQLAlchemy
      base.py        # Base declarativa + convenção de nomes de constraint
      usuario.py      # PapelUsuario + Usuario
      evento.py       # Evento + Setor + a Table evento_portaria (a escala, Story 2.5)
    schemas/         # Pydantic de entrada e saída
      auth.py         # CadastroEntrada, LoginEntrada, UsuarioSaida, EmailNormalizado
      catalogo.py     # ItemDoCatalogo — o formato do catálogo, não o da Ticketmaster
      evento.py       # EventoEntrada/Saida, EventoResumo, EventoNaProgramacao, PeriodoDaProgramacao
                      # · EventoResumo — a vista de lista, com os dois totais somados (2.6)
                      # · EventoNaProgramacao — a vista pública, sem estoque nenhum (3.1)
    integrations/    # clientes de serviço externo — a única pasta que sai da rede
      ticketmaster.py # buscar_eventos() — cliente da Discovery API (Story 2.1)
    core/
      config.py      # Settings
      db.py           # engine (com pool_pre_ping), SessaoLocal, obter_sessao()
      dependencias.py # usuario_atual() e exigir_papel() — a autorização do AD-9
      erros.py        # erro de domínio + formato único de resposta
      seguranca.py    # hash Argon2id e token de sessão (JWT)
  migrations/         # Alembic
    env.py
    versions/         # 4: usuario · evento+setor · evento_portaria · e a extensão unaccent,
                      #    a única que não cria tabela (Story 3.2)
  seeds/              # dados exigidos pelo desafio — não sobe com o uvicorn
    semear.py          # as cinco contas de avaliação; idempotente, nunca apaga nada
  tests/              # espelha a estrutura de app/
    conftest.py        # fixtures de banco + o TestClient ligado a elas
    test_evento.py     # invariantes de evento e setor que o banco garante
    test_organizador_catalogo.py  # GET /organizador/catalogo — precisa do Compose no ar
    test_organizador_eventos.py   # POST /organizador/eventos — idem, e com zero rede
    test_organizador_portarias.py # GET /organizador/portarias (Story 2.5)
    test_organizador_meus_eventos.py # GET /organizador/eventos e /eventos/{id} (Story 2.6)
    test_programacao.py # as duas rotas públicas, com busca e filtros (Stories 3.1 e 3.2)
  alembic.ini
  pyproject.toml
  uv.lock
  .env.example
```

`seeds/` é irmã de `app/`, não subpasta dela: seed não é código de aplicação e não tem por que subir
com o `uvicorn`. É o lugar que a árvore da arquitetura reservou, e é onde o evento e os setores de
exemplo da Epic 2 vão morar.

`services/` e `schemas/` nasceram vazias na Story 1.1, só com `__init__.py`, e ganharam o primeiro
morador na 1.4 com o login. Foi proposital: elas materializaram o paradigma desde o primeiro
commit, para que as stories seguintes não tivessem que decidir no calor da hora onde cada coisa
mora.

## Autenticação

Quatro rotas, e nada além disso — todas abertas a qualquer papel:

```
POST /auth/cadastro
  ← {"nome": "Igor Duarte", "email": "igor@exemplo.com", "senha": "..."}
  → 201  {"id": "…", "nome": "…", "email": "…", "papel": "CLIENTE"}
         Set-Cookie: rockhub_sessao=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800
                     (+ Secure quando AMBIENTE=producao)
  → 409  {"erro": {"codigo": "EMAIL_JA_CADASTRADO", "mensagem": "Esse e-mail já tem conta. …"}}
  → 422  {"erro": {"codigo": "DADOS_INVALIDOS", "mensagem": "…"}}

POST /auth/login
  ← {"email": "igor@exemplo.com", "senha": "..."}
  → 200  {"id": "…", "nome": "…", "email": "…", "papel": "CLIENTE"}
         Set-Cookie: rockhub_sessao=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800
                     (+ Secure quando AMBIENTE=producao)
  → 401  {"erro": {"codigo": "CREDENCIAIS_INVALIDAS", "mensagem": "E-mail ou senha incorretos."}}

POST /auth/logout
  → 204  sem corpo; apaga o cookie. Não exige sessão válida — quem tem token vencido
         é justamente quem mais precisa sair

GET /auth/eu
  ← Cookie: rockhub_sessao=<jwt>
  → 200  {"id": "…", "nome": "…", "email": "…", "papel": "CLIENTE"}
  → 401  {"erro": {"codigo": "NAO_AUTENTICADO", "mensagem": "Entre para continuar."}}
         sem cookie · token adulterado · token expirado · conta apagada
```

O cadastro **já devolve a sessão**: o mesmo cookie que o login gravaria. Obrigar a pessoa a digitar
de novo o e-mail e a senha que acabou de escolher é atrito sem contrapartida — a credencial já foi
provada no ato de criar a conta. Os atributos do cookie são montados por um helper único
(`_gravar_cookie_de_sessao`), usado pelas duas rotas, e o `delete_cookie` do logout mora
imediatamente ao lado dele: atributo que diverge entre gravar e apagar produz um cookie que o
navegador não apaga, e a única defesa contra isso é os dois estarem sempre à vista um do outro.

O cadastro, o login e o `GET /auth/eu` devolvem o **mesmo** `UsuarioSaida`. Três rotas, um schema —
e um teste afirma que o corpo do `/auth/eu` é idêntico ao que o login acabou de devolver, para que
divergência entre elas seja o que quebra.

### O que `CadastroEntrada` aceita, e por que cada limite existe

| Campo | Regra | Motivo |
|---|---|---|
| `nome` | `.strip()`, depois 1 a 120 caracteres | O `.strip()` vem antes porque `min_length=1` sozinho não segura `"   "` — três espaços são três caracteres válidos. O teto de 120 casa com o `VARCHAR(120)` da coluna, transformando num `422` legível o que seria um `500` de truncamento |
| `email` | `.strip().lower()`, até 255, formato conferido | A normalização é a convenção que nasceu na Story 1.3, agora aplicada nos dois lados |
| `senha` | 6 a 128 caracteres | O piso é decisão de produto (ver [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo)). O teto não é enfeite: Argon2id não tem o limite de 72 bytes do bcrypt, e uma senha de 10 MB seria hasheada inteira, com 64 MB de memória, por requisição |

A normalização de e-mail é um tipo só — `EmailNormalizado`, um `Annotated` com `BeforeValidator` —
usado pelo cadastro **e** pelo login. Estava duplicada como `field_validator` dentro do
`LoginEntrada`; se as duas rotas normalizassem de jeitos diferentes, a conta gravada por uma não
seria encontrada pela outra. O validador de *formato*, esse fica só no cadastro: no login o e-mail é
chave de busca, e um `422` de formato antes do `401` de credencial recriaria a distinção entre
"e-mail não existe" e "senha errada" que a resposta única existe para eliminar.

**Não há `extra="forbid"` no schema, e isso é deliberado.** Parece a escolha rigorosa e quebraria a
garantia mais importante da rota: enviar `{"papel": "ORGANIZADOR"}` no corpo passaria a responder
`422` em vez de simplesmente criar uma conta `CLIENTE`. O papel é literal dentro do service, sem
parâmetro e sem valor padrão sobrescrevível — um campo desconhecido sendo **ignorado** é a garantia
mais forte que existe, porque ele não tem como influenciar nada. **O papel de uma conta nunca vem do
corpo da requisição**, e essa regra vale para a Story 2.5, quando o organizador escalar portaria.

### Duplicata é detectada pelo banco, não por um `SELECT` antes

O caminho intuitivo seria consultar se o e-mail existe e, se não existir, gravar. Não é o que
`cadastrar()` faz, por dois motivos:

1. **Seria uma corrida.** Entre a consulta e a gravação cabe outra requisição com o mesmo e-mail. A
   segunda bate no `UNIQUE` e vira `500` — justamente no caso que o `409` existe para cobrir
2. **Criaria dois caminhos para a mesma regra.** O `SELECT` seria a regra "de verdade" e o `UNIQUE`
   uma rede de proteção com comportamento diferente. Duas respostas para uma pergunta é como as duas
   divergem

Então há um caminho só: tenta gravar, e a restrição criada na Story 1.3 é quem responde. O
`IntegrityError` vira `ErroDeDominio("EMAIL_JA_CADASTRADO", …, status_http=409)`. Três detalhes do
bloco que custam tempo se passarem batido: o `flush()` fica dentro do `try` e o `commit()` fora
(assim a exceção aparece na linha que a provoca); o `rollback()` é obrigatório, senão a `Session`
fica em estado inválido e a próxima operação levanta um `PendingRollbackError` que aponta para longe
da causa; e o `raise ... from erro` mantém no traceback o que o banco disse.

Isso vale para os `UNIQUE` que vierem — evento, setor, vínculo de portaria. Como só existe uma
restrição única na tabela `usuario`, não há ambiguidade sobre qual falhou; no dia em que houver duas,
isto vira `erro.orig.diag.constraint_name`.

**`cadastrar()` é o primeiro service do projeto que escreve**, e o par com `autenticar()` materializa
a convenção de transação: *service que lê não faz nada; service que escreve abre e fecha a
transação.* `obter_sessao()` entrega a `Session` sem transação aberta, e o router nunca chama
`commit`.

### A engine confere a conexão antes de entregá-la

`create_engine` é chamado com `pool_pre_ping=True` e `pool_recycle=1800`, e não com os padrões —
que são `False` e `-1`, ou seja: o pool guarda a conexão para sempre e nunca confere se ela ainda
existe. Isso saiu do code review da Epic 1, e é o achado de maior retorno dele.

O Postgres da Railway reinicia por manutenção, e a rede interna derruba conexão ociosa. Sem o
`pre_ping`, a primeira requisição depois de um período parado pega uma conexão morta do pool e
responde `500` — `psycopg.OperationalError: server closed the connection unexpectedly`. O SQLAlchemy
invalida o pool ao detectar o desconecte, então a **segunda** tentativa funciona. É exatamente o
pior desenho possível para este projeto: quem avalia abre o link dias depois do último deploy, leva
um erro no primeiro login, e a retentativa que consertaria não é comportamento de quem está
avaliando — é suposição minha.

Os dois parâmetros resolvem problemas diferentes e por isso estão os dois: o `pre_ping` cobre a
conexão que **já** morreu (custa um `SELECT 1` por checkout), e o `recycle` cobre a que **vai**
morrer num timeout de proxy no meio de uma requisição. É o defeito mais barato de corrigir e o mais
difícil de encontrar: nenhuma suíte deste projeto o pegaria, porque ele exige tempo passando entre
duas requisições.

Uma consequência disso aparece nos testes e vale o aviso: depois de um `409`, o `rollback()` do
service desfaz a transação **até o savepoint** da fixture, e leva junto o usuário que ela inseriu por
`flush`. A resposta HTTP continua sendo `409`, mas um `assert` contando linhas na tabela depois disso
veria zero e pareceria um bug do service. Afirme sobre a **resposta**, não sobre o banco.

### A enumeração de e-mail que o cadastro oferece

O `409` revela que aquele e-mail tem conta — exatamente o que o login gasta um `HASH_FANTASMA` para
não revelar. A contradição é real e está registrada em *O que não está pronto* no
[README da raiz](../README.md): o login pode esconder porque as duas respostas cabem numa frase só;
o cadastro não tem essa saída sem verificação por e-mail, que está fora do escopo. O que continua
valendo é que o login não entrega a lista de graça — quem quiser precisa passar pelo cadastro, um
e-mail por vez.

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

## Autorização: papel se declara, não se confere

A regra vale para todas as rotas das Epics 2 a 5, e mora em
[`app/core/dependencias.py`](app/core/dependencias.py):

```python
@router.get("/organizador/eventos")
def meus_eventos(
    usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
) -> ...
```

**Nenhum `if usuario.papel == ...` dentro do corpo de um handler, no projeto inteiro.** Funcionaria
igual, e é errado por duas razões: some da documentação gerada — o `/docs` não teria como saber que
a rota é restrita — e depende de alguém lembrar de escrever a linha em cada rota nova. Na
assinatura, esquecer a proteção é uma linha ausente que se vê à distância. É o AD-9, e a alternativa
que descartei está no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

São duas peças:

| Peça | O que faz |
|---|---|
| `usuario_atual` | Traduz o cookie no `Usuario`. Levanta `401` se não houver sessão válida |
| `exigir_papel(*papeis)` | **Fábrica** que devolve uma dependência. Levanta `403` se o papel não estiver na lista |

### Autenticação antes de autorização

Sem sessão é `401`; com sessão e papel errado é `403`. Primeiro se pergunta quem é, depois o que
pode. Quem garante a ordem é o `Depends` encadeado: `exigir_papel` depende de `usuario_atual`
**por `Depends`**, não por chamada direta. Chamar `usuario_atual(...)` à mão lá dentro obrigaria a
repassar `Request` e `Session` e faria quem não tem sessão nenhuma receber `403` — uma resposta que
diz "seu papel está errado" para alguém que sequer entrou.

Os dois códigos, `NAO_AUTENTICADO` e `SEM_PERMISSAO`, são exatamente os que `CODIGO_POR_STATUS`
daria para `401` e `403`. É de propósito, e é o contrário do que aconteceu com o `409` do cadastro:
lá o domínio tinha algo a dizer que o status não dizia (`EMAIL_JA_CADASTRADO`); aqui não tem — "não
autenticado" é a informação inteira. Uso `ErroDeDominio` mesmo assim pela **mensagem**: um
`HTTPException` daria o mesmo código com a `MENSAGEM_PADRAO` genérica, e o UX-DR8 pede uma frase que
diga o que fazer agora ("Entre para continuar.").

### Os quatro modos de não ter sessão respondem igual

Cookie ausente, token adulterado, token expirado e conta apagada são situações diferentes para quem
depura e **a mesma** para quem chama: não há sessão válida. Diferenciá-las na resposta transformaria
a rota num oráculo — "esse id já existiu?" —, pela mesma razão que o login gasta um `HASH_FANTASMA`
para não revelar se o e-mail existe. O `ler_token_sessao` já colapsa expirado e adulterado num
`None` só, porque o `jwt.decode` levanta `PyJWTError` para os dois.

### O papel vem do banco, nunca do token

O JWT carrega `papel` desde a Story 1.4, e o caminho curto seria lê-lo dali. Não faço isso:

1. **A sessão dura 8 horas (AD-15).** Um papel corrigido no banco continuaria valendo o antigo por
   todo esse tempo, e a única saída seria trocar o `JWT_SECRET` e deslogar todo mundo
2. **A consulta acontece de qualquer jeito.** `usuario_atual` precisa do usuário inteiro para o
   `GET /auth/eu`, então ler o papel do banco não custa uma consulta a mais — custa zero

O `papel` no token continua útil como possibilidade futura (recusar antes da ida ao banco), mas hoje
não é lido para autorizar nada, e um teste prova isso: um usuário gravado como `CLIENTE`, com um
token forjado dizendo `ORGANIZADOR`, recebe `403`.

Isso vale também para o vínculo portaria ↔ evento do AD-7, que será lido do banco a cada validação
em vez de carregado na sessão.

### O paradigma: `routers → services → models`

Dependência sempre para dentro, nunca o inverso, nunca pulando camada.

| Camada | Pasta | Responsabilidade |
|---|---|---|
| `routers` | `app/api/` | HTTP: validação de entrada, autenticação, código de status. Sem regra de negócio, sem tocar no banco |
| `services` | `app/services/` | Regra de negócio, transações e acesso ao banco |
| `models` | `app/models/` | SQLAlchemy |

**Não existe `app/repositories/`, e isso foi escolhido.** O motivo está no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

**`app/api/organizador.py` é a única exceção ao paradigma, e é deliberada.** `GET
/organizador/catalogo` (Story 2.2) chama `app.integrations.ticketmaster` direto — pula a camada de
`services`. Não existe `services/catalogo.py` porque `buscar_eventos` já faz tudo que um service
faria: `.strip()` no termo, curto-circuito de termo vazio antes de qualquer I/O, limite, conversão
para `ItemDoCatalogo` e tradução de toda falha em `ErroDeDominio`. Interpor um módulo cujo corpo
inteiro seria `return ticketmaster.buscar_eventos(termo)` é a "camada de repasse" que este próprio
parágrafo rejeita para `repositories/` — seria inconsistente aceitar aqui o que recuso ali só porque
o nome da pasta é outro. **A exceção vale só para o catálogo.**

Desde a Story 2.4 o mesmo arquivo tem o **outro lado do par**, e é o que torna o critério
verificável em vez de retórico. `POST /organizador/eventos` grava evento e setores no banco: tem
transação (os dois juntos ou nada) e tem invariante (nenhum setor, setor repetido), então tem
service — `app/services/evento.py` —, e o corpo do endpoint é uma linha só. Duas rotas no mesmo
router, uma com service e outra sem, e a pergunta que separa as duas escrita entre elas: *existe
transação ou invariante?*

## Catálogo da Ticketmaster

`app/integrations/ticketmaster.py` (Story 2.1) é a única peça do backend que fala com um serviço
fora dele. `buscar_eventos(termo, *, limite=20)` consulta a Discovery API e devolve
`list[ItemDoCatalogo]` — o formato **deste projeto**, não o da Ticketmaster.

```
# com termo
GET https://app.ticketmaster.com/discovery/v2/events.json
    ?apikey=<TICKETMASTER_API_KEY>&keyword=<termo>&size=<limite>&locale=*
    &countryCode=BR&segmentId=KZFzniwnSyZfZ7v7nJ

# sem termo — a vitrine (Story 2.2, revisada)
GET https://app.ticketmaster.com/discovery/v2/events.json
    ?apikey=<TICKETMASTER_API_KEY>&size=<limite>&locale=*&sort=date,asc
    &countryCode=BR&segmentId=KZFzniwnSyZfZ7v7nJ&genreId=KnvZfZ7vAeA
```

**`countryCode=BR` entrou na Story 2.2**, junto com a superfície HTTP. Sem ele, buscar "metallica"
devolve os vinte primeiros shows do mundo — quase todos nos EUA — e nenhum brasileiro entra no
`size=20`; a tela do organizador pareceria quebrada para quem estiver avaliando. **Limitação
assumida**: um show fora do Brasil não aparece nesta busca. Está registrada também em [O que não
está pronto](../README.md#o-que-não-está-pronto) do README da raiz.

### O filtro de classificação é híbrido

Acrescentado **fora da numeração das stories**, num commit `feat` avulso: descobri o problema abrindo
a tela da Story 2.2 já pronta, e o planejamento não tinha como prever isso. A especificação, com o
raciocínio completo e as alternativas medidas contra a API, está em
[docs/techspec-filtro-do-catalogo.md](../docs/techspec-filtro-do-catalogo.md).

> **Esta seção é o registro definitivo da decisão** — ela não sobe para o README da raiz. A techspec
> pedia uma entrada lá, mas a régua que instituí no `CLAUDE.md` no mesmo dia barra: escolher dois ids
> da taxonomia da Ticketmaster não faz quem avalia ver um sistema diferente. Alinhado no code review
> da Epic 2, com o aviso escrito na seção 6 da própria techspec.

| Constante | Valor | Entra quando |
|---|---|---|
| `_SEGMENTO_MUSICA` | `KZFzniwnSyZfZ7v7nJ` (segmento *Music*) | **Sempre**, nos dois caminhos |
| `_GENERO_ROCK` | `KnvZfZ7vAeA` (gênero *Rock*, filho de Music) | **Só sem termo** — a vitrine |

Sem o segmento, o catálogo do Brasil devolve 168 eventos e o primeiro é uma feira de negócios — a
tela de publicação abria anunciando evento corporativo como sugestão de show. Com ele, sobram os 124
que são música de verdade.

O gênero fica **fora** da busca por termo de propósito, e a razão é uma contraprova medida:
`keyword=rosalia` com o segmento devolve 1 resultado; com segmento **e** gênero devolve 0. Quem
digita o nome exato do show que quer publicar precisa achá-lo — a tela não tem como explicar um
filtro de gênero que ela não sabe que existe. Na vitrine é o contrário: ninguém pediu nada
específico, e mostrar rock é o produto se apresentando.

⚠️ **Os dois ids são dado de terceiro fixado aqui no código.** São estáveis na taxonomia da
Ticketmaster, e foram conferidos empiricamente em 11/08/2026 — não copiados de memória. Se um dia a
busca vier vazia sem explicação, `GET /discovery/v2/classifications.json` lista a árvore inteira e é
por onde se reconfere.

Um dos quatro testes deste filtro prova o `genreId` **ausente** na busca por termo. Ele existe para
acusar a "simplificação" de mover o parâmetro para fora do `else` — sem ele, nada quebraria e a
busca por termo passaria a esconder resultado legítimo em silêncio.

| Limite da Discovery | Valor | O que faço com ele |
|---|---|---|
| Por segundo | 5 req/s | Nada — uma busca por evento publicado não chega perto |
| Por dia | 5 000 chamadas | Nada hoje. Toda abertura da tela gasta uma chamada (ver a revisão abaixo); 5 000/dia é folga larga para o volume de uma avaliação |

**Toda falha vira o mesmo erro.** Timeout, conexão recusada, `401`, `429`, `500`, corpo que não é
JSON válido e **JSON válido com forma inesperada** — os sete viram
`ErroDeDominio("CATALOGO_INDISPONIVEL", ..., status_http=503)`. Quem
chama não precisa saber qual dos sete aconteceu; o log sabe (`401` vira `logger.error`, porque é
chave errada ou revogada — erro meu, não instabilidade da Ticketmaster; os demais viram
`logger.warning`). **A chave nunca aparece em log nenhum**: as exceções do `httpx` carregam a URL
completa da requisição, e a URL carrega `apikey=` — um `logger.exception()` por reflexo vazaria a
chave para o log da Railway, furando o AD-2 pelo lado de dentro do backend. Um teste prova que o
valor da chave não aparece nem no `caplog` nem na mensagem do `ErroDeDominio`.

⚠️ **A sétima entrou no code review da Epic 2, e é a que mostra o buraco que a promessa tinha.** O
`try` cobria só `cliente.get`, `raise_for_status` e `.json()` — a **conversão** da resposta ficava de
fora. Resultado: uma resposta perfeitamente bem formada como JSON, mas com forma inesperada, não era
nem `HTTPError` nem `ValueError`, e subia como `AttributeError`/`TypeError`/`ValidationError` até o
handler genérico. `500`, no módulo cujo propósito declarado é nunca deixar a Ticketmaster derrubar
nada. Quatro casos reais, todos com teste agora: corpo que é lista em vez de objeto (um proxy no
meio do caminho), `_embedded.events` que não é lista, `width` das imagens como texto (o `max()`
comparava `str` com `int`), e `name` numérico (o Pydantic v2 não coage `int` para `str`).

A lição que fica: **`try/except` que cobre a chamada mas não a interpretação da resposta protege
metade do caminho** — e a metade que ele deixa de fora é justamente a que ninguém testa, porque
exige um fornecedor devolvendo algo estranho em vez de simplesmente falhar.

**Política de chave ausente, por ambiente** — o mesmo padrão do `JWT_SECRET`:

| Ambiente | Chave ausente | Por quê |
|---|---|---|
| `producao` | Aplicação **não sobe** | Um deploy com a variável esquecida ficaria verde, e a falha só apareceria no dia em que alguém fosse publicar um evento |
| `local` | Aplicação sobe normalmente; a busca responde `CATALOGO_INDISPONIVEL` | Quem clona o repositório para avaliar não precisa de conta no portal da Ticketmaster (NFR1) |

`ItemDoCatalogo` (`app/schemas/catalogo.py`): `id_externo`, `nome`, `atracao`, `imagem_url`,
`local`, `cidade` — os seis campos que sobram depois da conversão. Nenhum nome de campo da
Ticketmaster (`_embedded`, `dates`, `classifications`, `ratio`) atravessa essa fronteira, e o
schema não importa nada de `app/integrations/`: a dependência é sempre de fora para dentro. A
conversão é tolerante — evento sem `venues`, sem `attractions` ou sem `images` vira campo `None`,
nunca exceção — e descarta da lista qualquer evento sem `id` ou sem `name`, porque sem os dois não
dá para publicar nada na Story 2.4. Quando há mais de uma imagem, escolho a mais larga com
`ratio == "16_9"` e sem `fallback: true` (as `fallback` são genéricas da Ticketmaster e não têm
nada a ver com o show) — é a proporção que a chamada principal da Story 3.3 vai consumir (UX-DR4).

**A rota é `GET /organizador/catalogo?q=`** (Story 2.2), protegida por
`Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` — só o organizador toca o catálogo (AD-1). `q`
tem `max_length=120` porque vai inteiro para a URL da Ticketmaster. O corpo do handler é uma linha
(`return ticketmaster.buscar_eventos(q)`); por que não há service ao redor dela está em [O
paradigma: `routers → services → models`](#o-paradigma-routers--services--models).

⚠️ **`q` ausente, vazio ou só espaços não devolve `[]` — revisado depois do primeiro corte desta
story.** A primeira versão respondia lista vazia sem chamar a Ticketmaster, pelo mesmo raciocínio de
poupar cota que valia para a integração isolada da Story 2.1. Pedido do Igor depois de testar a
tela: sem termo, `buscar_eventos` chama a Discovery sem o parâmetro `keyword` e com
`sort=date,asc`, e devolve os próximos eventos do catálogo no Brasil como **exemplo** do que dá para
publicar — o organizador não precisa digitar nada antes de ver do que se trata. `422` continua fora
de cogitação: campo de busca vazio é o estado inicial da tela, não erro de quem chamou.

Zero rede na suíte: `tests/test_ticketmaster.py` e `tests/test_organizador_catalogo.py` substituem o
cliente por `httpx.MockTransport`, que recebe a `httpx.Request` de verdade — construída pelo código
de produção, com a query string montada por ele — em vez de um `monkeypatch` em `httpx.get`.

## Evento e setor

Duas tabelas, criadas juntas na Story 2.3 pela migração `b91316d771ae` — a primeira desde a
`usuario`, e a primeira do projeto com chave estrangeira e relacionamento no ORM.

Desde a Story 2.4 elas têm gente dentro: `POST /organizador/eventos` grava as duas, e a seção
[Publicar evento](#publicar-evento) logo abaixo é a rota que faz isso. Até a 2.3 o schema existiu
sozinho, sem rota, service nem tela — de propósito: o formato do banco nasce antes do comportamento
que o consome.

**`evento`** — o show, com os campos do catálogo já **copiados** para dentro (AD-1: a Ticketmaster
é consultada uma vez, na publicação, e nunca mais):

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `uuid` | Chave primária, gerada no Python com `uuid.uuid4` |
| `organizador_id` | `uuid`, `NOT NULL` | FK para `usuario.id`, **sem `ondelete`** |
| `nome` | `varchar(200)`, `NOT NULL` | O nome do show |
| `data_hora` | `timestamptz`, `NOT NULL` | UTC (AD-11) |
| `local` | `varchar(200)`, `NOT NULL` | A casa de show — quem preenche é o organizador |
| `cidade` | `varchar(120)`, anulável | A Discovery pode não trazer |
| `imagem_url` | `varchar(500)`, anulável | Idem |
| `origem_externa_id` | `varchar(64)`, anulável | O id da atração no catálogo, **sem unicidade** |
| `publicado_em` | `timestamptz`, anulável | `NULL` = rascunho |
| `criado_em` | `timestamptz`, `NOT NULL`, `DEFAULT now()` | |

**`setor`** — a faixa de ingresso. É aqui que moram preço e capacidade, nunca no evento (AD-12):
é o que permite Pista e Camarote no mesmo show com lotações e valores diferentes.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `uuid` | Chave primária |
| `evento_id` | `uuid`, `NOT NULL`, indexado | FK para `evento.id` com `ON DELETE CASCADE` |
| `nome` | `varchar(80)`, `NOT NULL` | "Pista", "Camarote" — único **por evento** |
| `capacidade` | `integer`, `NOT NULL` | `> 0` |
| `vendidos` | `integer`, `NOT NULL`, `DEFAULT 0` | A única fonte de verdade da disponibilidade (AD-13) |
| `preco_centavos` | `bigint`, `NOT NULL` | Centavos inteiros, `>= 0` (AD-11) |

**Disponível é `capacidade - vendidos`, calculado na hora.** Não existe coluna `disponivel`, e é
proibido derivar a conta com `COUNT` sobre reservas — duas fontes para o mesmo número é uma a mais
do que se quer, e a segunda sempre discorda da primeira em algum caminho.

### As quatro constraints do `setor`, e o motivo de cada uma

| Constraint | Regra | Por que existe |
|---|---|---|
| `ck_setor_estoque_valido` | `vendidos >= 0 AND vendidos <= capacidade` | AD-3. É **rede de segurança**, não a regra: a regra é o `UPDATE` condicional abaixo. Esta constraint é o que sobra de pé se algum caminho da aplicação escapar dele |
| `ck_setor_capacidade_positiva` | `capacidade > 0` | Setor com capacidade zero nasce esgotado, aparece na tela do cliente e ninguém entende por que não dá para comprar |
| `ck_setor_preco_nao_negativo` | `preco_centavos >= 0` | Preço negativo é dinheiro andando para trás |
| `uq_setor_evento_id_nome` | `(evento_id, nome)` único | Dois "Pista" no mesmo evento deixariam o cliente escolhendo no escuro na tela da Story 3.4. **Por evento, não global**: outro show pode ter uma Pista |

⚠️ **O nome da `UniqueConstraint` vai escrito à mão, e é o único lugar do projeto onde isso
acontece.** O template `uq` da convenção da `Base` é `uq_%(table_name)s_%(column_0_name)s`, que usa
só a **primeira** coluna: sem nome explícito a constraint sairia `uq_setor_evento_id` — que parece
dizer "um setor por evento", exatamente o oposto do que ela faz. Os três `CheckConstraint` não
precisam disso, porque o template `ck` já carrega o nome que passo.

### O `UPDATE` condicional do AD-3, testado antes de existir consumidor

```sql
UPDATE setor SET vendidos = vendidos + :q
 WHERE id = :id AND vendidos + :q <= capacidade
```

**Zero linhas afetadas é o sinal de "sem estoque"** — não uma exceção, não um `SELECT` antes. Quem
executa isso é o service da Epic 3; nenhuma story da Epic 2 chega perto dele. Mesmo assim testei o
`UPDATE` aqui, na story em que a tabela nasce, e o motivo é direto: `capacidade` e `vendidos` são
colunas separadas — em vez de um `disponivel` decrescente — **só** para tornar essa operação
atômica possível. Uma tabela que nasce sem provar a operação que justifica seu formato é uma tabela
que ninguém sabe se está certa.

Repare que o `CHECK` nunca chega a ser violado nesse caminho: quem barra é a condição do `WHERE`. O
`CHECK` fica de rede para quem esquecer o `WHERE`.

### `ON DELETE CASCADE` no banco exige `passive_deletes` no ORM

Esta é a armadilha sutil das duas tabelas, e vale saber antes de mexer no `relationship`. Com um
`relationship` comum, apagar um `Evento` pela sessão faz o SQLAlchemy carregar os setores e emitir
`UPDATE setor SET evento_id = NULL` **antes** do `DELETE` — que estoura no `NOT NULL` e nunca chega
no `CASCADE` que a migração declarou. As duas metades precisam concordar:

```python
setores: Mapped[list["Setor"]] = relationship(
    back_populates="evento",
    cascade="all, delete-orphan",
    passive_deletes=True,   # ← manda o SQLAlchemy confiar no banco
)
```

O teste disso apaga **pela sessão** (`sessao.delete(evento)`) e confere a contagem por SQL cru.
Apagar por SQL cru provaria só a metade que já se sabe.

## Publicar evento

Uma rota, criada na Story 2.4. É a **primeira rota de escrita do domínio**: `/auth/cadastro` também
grava, mas grava a conta de quem chamou; aqui alguém autenticado cria um objeto que outras pessoas
vão ver e comprar.

```
POST /organizador/eventos     → 201, o evento gravado com seus setores
```

```bash
curl -i -X POST http://localhost:8000/organizador/eventos \
  -b cookies.txt -H 'Content-Type: application/json' \
  -d '{
    "origem_externa_id": "ZFIMVHtnMZ17kbx_",
    "nome": "Sticky Fingers - Rio de Janeiro",
    "imagem_url": "https://s1.ticketm.net/dam/a/....jpg",
    "data_hora": "2026-08-15T00:00:00Z",
    "local": "Qualistage",
    "cidade": "Rio de Janeiro",
    "setores": [
      {"nome": "Pista", "capacidade": 800, "preco_centavos": 12000},
      {"nome": "Camarote", "capacidade": 60, "preco_centavos": 42000}
    ],
    "portaria_ids": ["<id de GET /organizador/portarias>"]
  }'
```

⚠️ **`portaria_ids` é obrigatório desde a Story 2.5** (AD-7), e os ids saem de
[`GET /organizador/portarias`](#get-organizadorportarias). Sem ele, a resposta é `422
EVENTO_SEM_PORTARIA`.

**Três coisas estão fechadas por construção, não por validação.** É a diferença entre "o service
confere" e "não existe caminho":

| O que | Como | Por que assim |
|---|---|---|
| O dono | `organizador_id` vem do `Usuario` da dependência de papel | Não há parâmetro por onde um id do corpo pudesse entrar. Publicar em nome de outra pessoa não é uma chamada que o service recusa — é uma chamada que não existe |
| O papel | `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` na assinatura (AD-9) | Sem sessão é `401`, com papel errado é `403`, e a restrição aparece no `/docs` |
| O estoque | `vendidos` não é passado ao construir `Setor`; quem responde é o `server_default` da 2.3 | `vendidos` não existe no schema de entrada, então mandá-lo no corpo não faz nada (AD-13) |

**Nenhuma chamada à Ticketmaster acontece na publicação** (AD-1). O catálogo já foi copiado pelo
cliente na busca, e daqui em diante o dado vive no banco: publicar não pode depender de a Discovery
estar no ar, e ingresso vendido não pode mudar de nome porque alguém editou um registro lá fora. O
teste prova isso instalando um transporte HTTP que **falha** se alguém o chamar.

### Dois códigos de erro novos

| Código | Status | Quando |
|---|---|---|
| `EVENTO_SEM_SETOR` | `422` | Lista de setores vazia **ou ausente** |
| `SETOR_DUPLICADO` | `422` | Dois setores com o mesmo nome no mesmo corpo, ignorando caixa e espaços em volta |

Os dois são `ErroDeDominio`, então saem no formato único da API sem handler novo.

### Por que "lista vazia" não é validação do Pydantic

Esta é a parte que parece um detalhe e não é. A correção óbvia seria `Field(min_length=1)` no
`setores` — o campo exige ao menos um item, então põe o mínimo no schema. Não fiz, e o motivo é o
`codigo`: `min_length` produz `422` com `DADOS_INVALIDOS`, que é o código genérico de "algum campo
está errado". A tela não teria como dizer **o que** faltou, porque o contrato do frontend é o
código, nunca a mensagem.

O critério que uso é esse: **validação de estrutura é do Pydantic; regra de negócio é do service.**
"O corpo tem uma lista de setores" é estrutura. "Um evento precisa de ao menos um setor à venda" é
regra — e regra tem nome próprio. Pelo mesmo motivo o campo tem `default_factory=list`: sem ele, o
campo **ausente** viraria "field required" do Pydantic, e a mesma situação teria duas respostas
diferentes dependendo de o cliente ter mandado `[]` ou não ter mandado nada.

O teste que segura isso afirma `resposta.json()["erro"]["codigo"] == "EVENTO_SEM_SETOR"`, não o
status: com `min_length` o status continuaria `422` e o teste passaria sem querer.

### Todo número tem teto, e o `ge` sozinho não bastava

Descoberto no code review da Epic 2. `capacidade` tinha `Field(ge=1)` sem `le`, contra uma coluna
`Integer` — que no Postgres é **int4**. Um corpo com `"capacidade": 3000000000` passava pelo schema,
passava pelas cinco recusas do service e só estourava no `commit`, como `DataError: integer out of
range`. Isso **não** é `IntegrityError`, ninguém previa, e caía no handler genérico: `500
ERRO_INTERNO` para um erro de digitação. É a mesma "pior resposta possível" que o `SETOR_DUPLICADO`
existe para evitar, por um caminho que ninguém tinha fechado.

| Campo | Teto | De onde vem |
|---|---|---|
| `capacidade` | `2 147 483 647` | O maior `int4`, que é o tipo da coluna |
| `preco_centavos` | `100 000 000 000` (R$ 1 bi) | **Não** é o limite da coluna, que é `BigInteger`. É o do JavaScript: acima de `Number.MAX_SAFE_INTEGER` o `Math.round` do formulário arredonda errado e envia um valor que não é o digitado — dinheiro corrompido em silêncio, exatamente o que o AD-11 existe para impedir. O frontend também recusa, com `Number.isSafeInteger` |

`imagem_url` ganhou validação de esquema na mesma leva: só `http://` e `https://`. O campo chega
pelo **corpo**, não da Ticketmaster — o service não confere nada contra o catálogo, então "veio do
fornecedor" nunca foi garantia —, e a Epic 3 vai renderizá-lo em `<img src>` na programação pública.

### Nome de setor repetido seria um `500` se ninguém tratasse

A `uq_setor_evento_id_nome` nasceu na Story 2.3 e é o banco quem a aplica. Dois "Pista" no mesmo
corpo estouram `IntegrityError` no `commit`, que sobe até o handler genérico de `Exception` e volta
como `ERRO_INTERNO`. Um erro de digitação do organizador viraria "erro interno do servidor" — a pior
resposta possível para quem só quer corrigir uma linha.

Por isso o service compara os nomes **antes** de qualquer `add`, com `nome.casefold()` depois do
`.strip()` que o schema já aplicou. `casefold()` e não `lower()`: é a normalização correta para
comparação insensível a caixa fora do ASCII.

A ordem das duas recusas é o que garante que **nada** fica no banco quando o corpo é inválido —
nem um evento órfão, nem o primeiro setor antes de o segundo estourar.

E é também o motivo de **não** haver `try/except IntegrityError` aqui, ao contrário do `cadastrar()`.
Lá o `UNIQUE` do e-mail é a regra, e conferir antes seria uma corrida entre duas requisições. Aqui as
violações possíveis chegam todas do mesmo corpo, num instante só, sem ninguém concorrendo: dá para
conferi-las na memória, com certeza. Um `except` genérico neste ponto só serviria para transformar
bug de verdade em `422` bonito.

### `publicado_em` é carimbado no ato

Publicar é o ato desta rota, não um passo posterior. `NULL` (rascunho) continua sendo um estado
possível no banco e continua sem tela que o produza — é o que torna verificável o AC da Story 3.1,
"evento não publicado não aparece na programação".

✅ **O AD-7 passou a valer nesta rota na Story 2.5.** Entre a 2.4 e a 2.5 foi possível publicar um
evento sem ninguém autorizado a validar ingresso nele — janela deliberada, registrada por escrito, e
fechada por [Escalar a portaria](#escalar-a-portaria), logo abaixo. O corpo passou a exigir
`portaria_ids`, e o curl acima **não publica mais nada sem ele**.

## Escalar a portaria

Quem valida ingresso na porta de um evento é escolhido pelo organizador no ato de publicar. É o AD-7,
e desde a Story 2.5 ele é código: uma tabela, uma rota de leitura e duas recusas novas na rota de
publicação.

### A tabela `evento_portaria`

Criada pela migração `c7cb4a29b7f3`. É a **primeira tabela de associação** do projeto:

| Coluna | Tipo | Regras |
|---|---|---|
| `evento_id` | `uuid`, `NOT NULL` | FK para `evento.id` com `ON DELETE CASCADE` |
| `usuario_id` | `uuid`, `NOT NULL` | FK para `usuario.id`, **sem `ondelete`** |

**Chave primária composta pelas duas colunas**, e nenhuma coluna própria — nem `id`, nem `criado_em`.
O par (evento, pessoa) *é* a identidade da linha, e é essa chave que impede a mesma pessoa escalada
duas vezes no mesmo evento.

**Os dois `ondelete` são diferentes de propósito**, e é o mesmo raciocínio da Story 2.3: apagar o
evento leva a escala junto, porque escala de um show que não existe mais não significa nada; apagar
alguém que já trabalhou numa porta tem que doer, e o Postgres recusa.

No ORM ela é uma **`Table` do Core, não uma classe mapeada** (`app/models/evento.py`). Uma classe
prometeria o que a tabela não tem — "um dia isto vai ter `turno`, `escalado_por`" — e alguém
acabaria acrescentando. Quando a escala passar a carregar dado próprio, ela vira classe numa
migração explícita, e não numa casa vazia que já estava lá.

`Evento.portarias` existe; **o lado inverso, em `Usuario`, não.** "Os eventos em que fui escalado" é
a Story 5.1, e criá-lo agora seria um `relationship` sem consumidor — com o agravante de que
`usuario.py` passaria a importar `evento.py`, que já importa `usuario.py`.

### `GET /organizador/portarias`

```
GET /organizador/portarias   → 200, todas as contas de papel PORTARIA, ordenadas por nome
```

```json
[
  { "id": "8c26…", "nome": "Ana Sampaio",   "email": "portaria2@rockhub.dev" },
  { "id": "fa34…", "nome": "Jonas Ribeiro", "email": "portaria@rockhub.dev" }
]
```

Protegida por `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` — cliente e a **própria portaria**
recebem `403`; sem cookie é `401`. Estar na lista não dá direito de lê-la: escalar é ato do
organizador.

`PortariaSaida` é um schema novo, e não o `UsuarioSaida` de `schemas/auth.py`. A forma é quase a
mesma hoje (falta o `papel`, que aqui seria constante), mas o significado não é: um diz "quem está
logado", o outro "quem pode ser escalado". Reusar acoplaria o contrato de evento ao de autenticação.
É também o `response_model` que garante que `senha_hash` não vaze — sem ele declarado, o FastAPI
serializaria o `Usuario` inteiro, e um teste afirma a ausência da chave por isso.

Sem paginação e sem `?q=`: o filtro por nome acontece na tela, em memória. O porquê está no
[frontend/README.md](../frontend/README.md).

**Esta rota é o terceiro caso do critério de service**, e ela afina a regra que a 2.4 deixou escrita.
Ela é leitura, sem transação e sem invariante — e mesmo assim passa por `services/evento.py`, porque
**toca o banco**, e router que abre uma `Session` é o que o paradigma proíbe sem exceção. A do
catálogo escapa por não tocar banco nenhum. Os três casos ficam lado a lado no mesmo arquivo:
leitura sem service (integração externa), leitura com service (banco), escrita com service.

`listar_portarias()` mora em `services/evento.py`, e não em `autenticacao.py`, que já é dono das
consultas a `Usuario`. Ela consulta usuários, mas não é pergunta sobre autenticação: é "quem eu posso
pôr na porta deste evento", e existe para a publicação. Em `autenticacao.py` ficaria cercada de login
e hash de senha, sem relação com o motivo de existir.

### Três códigos de erro novos, e a ordem das cinco recusas

| Código | Status | Quando |
|---|---|---|
| `EVENTO_SEM_PORTARIA` | `422` | `portaria_ids` vazio **ou ausente** — AD-7 |
| `PORTARIA_INVALIDA` | `422` | Algum id não existe **ou** não tem papel `PORTARIA` |
| `EVENTO_NO_PASSADO` | `422` | `data_hora` já passou — entrou no code review da Epic 2 |

```
1. setores vazio          → EVENTO_SEM_SETOR
2. nome de setor repetido → SETOR_DUPLICADO
3. portaria_ids vazio     → EVENTO_SEM_PORTARIA
4. id que não resolve     → PORTARIA_INVALIDA
5. data_hora no passado   → EVENTO_NO_PASSADO
   ── só então: monta o Evento e grava ──
```

As cinco acontecem **antes** de qualquer `add`. É isso, e não uma transação esperta, que garante o
"nenhum evento órfão" desde a 2.4.

**Por que a data é a quinta, e não a primeira.** Ela é do evento, não dos setores, e a leitura
natural pediria que viesse antes de tudo. Pus por último pelo mesmo motivo que pôs setor antes de
portaria: as quatro anteriores já têm testes que provam o código que devolvem, e mover a nova para
cima trocaria a resposta de casos já cobertos sem ganho nenhum.

**O que ela me custou, e por que aceitei.** Sem evento no passado publicável, a seção *Já
aconteceram* de `Meus eventos` não tem como ser vista na avaliação — está em
[*O que não está pronto*](../README.md#o-que-não-está-pronto). Escolhi assim porque errar a data é
**permanente**: não existe tela de editar nem de apagar evento, e na Epic 3 esse show entraria na
programação vendendo ingresso para uma noite que já passou.

⚠️ Foi ela que obrigou o `_corpo` de `tests/test_organizador_eventos.py` a parar de usar data fixa.
O padrão era `"2026-08-15T00:00:00Z"`, escrito quatro dias antes dessa data: com esta recusa
valendo, a suíte inteira passaria a falhar na quinta-feira sem ninguém ter tocado em nada. Hoje é
`_daqui_a(30)`.

**Setor antes de portaria não é estética.** As duas recusas novas entraram numa rota que a 2.4 já
tinha entregado, e os dezesseis testes de recusa daquela story mandam corpo sem `portaria_ids`,
porque o campo não existia. Conferir setor primeiro é o que os mantém provando o que se propuseram a
provar — inverter a ordem os faria receber `EVENTO_SEM_PORTARIA` e virariam trabalho de reescrita,
sem nenhum ganho.

`portaria_ids` também **não** tem `min_length=1`, pelo mesmo motivo do `setores`: `min_length`
responderia `DADOS_INVALIDOS`, e "publicar exige portaria escalada" é o AD-7, uma invariante de
arquitetura. Invariante não mora num `Field(...)` — mora no service, onde tem nome próprio.

### Por que a lista não distingue "não existe" de "não é portaria"

Uma consulta só (`id.in_(ids)` **e** `papel == PORTARIA`), e uma mensagem só para os dois casos. Se a
resposta separasse "esse id não existe" de "essa conta não é de portaria", a rota viraria um oráculo
de existência de conta: quem tivesse uma sessão de organizador poderia varrer UUIDs e descobrir quais
já foram gente. É a mesma disciplina do login da Story 1.4, que não diz se o e-mail existe — e um
teste compara os dois corpos de erro para garantir que continuam **idênticos**, não só parecidos.

### Ids repetidos são deduplicados em silêncio

Ao contrário do `SETOR_DUPLICADO`, logo acima. Dois setores com o mesmo nome são duas intenções em
conflito — qual das duas capacidades vale? A mesma pessoa marcada duas vezes é uma intenção só, e
recusá-la seria pedir que alguém corrigisse um formulário que já dizia o que queria dizer. A dedução
é `dict.fromkeys`, que preserva a ordem do corpo; um `set` deixaria a escala não determinística.

A escala é gravada pelo `relationship`, na mesma transação do evento e dos setores — **nunca** um
`INSERT` manual na tabela de associação, pela mesma razão de `vendidos` não ser passado ao construir
`Setor`: dois caminhos para o mesmo fato é um a mais do que se quer.

## Meus eventos

Publicar é metade do trabalho; a outra é conseguir olhar o que já está no ar. A Story 2.6 abriu as
duas rotas de leitura do organizador — e é a primeira story da epic que **não escreve nada**: sem
migração, sem modelo novo, sem coluna nova.

```
GET /organizador/eventos                → 200, os meus eventos, por data crescente
GET /organizador/eventos/{evento_id}    → 200, um evento com setores e escala
```

### `EventoResumo`: a primeira vista que não espelha uma linha do banco

```json
[
  {
    "id": "3f2a…",
    "nome": "Baco Exu do Blues — Bluesman Vivo",
    "data_hora": "2026-08-15T00:00:00Z",
    "local": "Espaço Unimed",
    "cidade": "São Paulo",
    "publicado_em": "2026-08-11T17:22:04Z",
    "capacidade_total": 860,
    "vendidos_total": 12
  }
]
```

`capacidade_total` e `vendidos_total` **não existem em coluna nenhuma**: são a soma de
`setor.capacidade` e `setor.vendidos`, feita no service, em Python, num lugar só onde um teste
consegue lê-la. É o **AD-13** — `setor.vendidos` é a única fonte de verdade da disponibilidade, e é
proibido derivar qualquer um dos dois com `COUNT` sobre reserva ou ingresso, em qualquer camada.
As duas tabelas nem existem ainda, e é agora que o hábito se forma.

Por isso `EventoResumo` é o único schema de `schemas/evento.py` **sem `from_attributes`**: não há
`Evento` do ORM de onde ler esses dois atributos. E por isso `listar_do_organizador()` devolve
`list[EventoResumo]`, não `list[Evento]` — a alternativa era um `@computed_field` no schema ou uma
`@property` no modelo, e as duas escondem a soma na camada de serialização, um passo mais longe do
teste que a prova.

A lista **não** traz `setores` nem `imagem_url`. Ela é enxuta de propósito: o detalhe é quem abre
setor a setor, e com três setores por evento e dez eventos a listagem viraria um paredão de números.

Um evento **sem setor nenhum** — impossível pela rota de publicação, possível por `psql` — soma zero
e não quebra a listagem. Tem teste.

### Uma consulta a mais, não uma por evento

```python
select(Evento)
    .where(Evento.organizador_id == organizador.id)
    .order_by(Evento.data_hora, Evento.id)
    .options(selectinload(Evento.setores))
```

O `selectinload` não é otimização prematura: sem ele, ler `evento.setores` no laço da soma emite uma
consulta **por evento**, e o custo cresce com o sucesso do organizador. O sintoma só aparece com
volume — ou seja, nunca, numa avaliação —, e é exatamente por isso que a linha entra agora.

### Ordem sem `ORDER BY` é ordem que o Postgres não prometeu

Três correções do code review da Epic 2, e as três têm a mesma raiz: eu estava lendo a ordem física
do heap e chamando de contrato.

| Onde | Era | É |
|---|---|---|
| `listar_do_organizador` | `.order_by(Evento.data_hora)` | `.order_by(Evento.data_hora, Evento.id)` |
| `Evento.setores` | sem `order_by` | `order_by="Setor.nome"` |
| `Evento.portarias` | sem `order_by` | `order_by=Usuario.nome` |

Sem critério **total**, dois eventos no mesmo horário — duas casas na mesma noite é rotina — trocam
de lugar entre requisições, na tela que o organizador recarrega o dia inteiro.

Os setores eram o caso mais traiçoeiro, porque funcionavam. Sem `ORDER BY`, o Postgres devolve na
ordem de varredura do heap, que coincide com a de inserção **até a primeira escrita na linha**. O
`UPDATE setor SET vendidos = ...` do AD-3, que a Epic 3 vai fazer a cada venda, reescreve a tupla no
fim do heap: "Pista, Camarote" viraria "Camarote, Pista" depois da primeira venda de Pista, sem nada
ter mudado. Havia um teste afirmando `["Pista", "Camarote"]` — ele passava por acidente e teria
continuado verde.

**Por nome, e não por ordem de digitação**, porque não existe coluna de ordem e inventar uma seria
uma migração para resolver uma tela. Alfabético é estável, previsível, e não finge registrar uma
intenção que ninguém gravou.

### `evento.organizador_id` ganhou índice

O Postgres cria índice para chave **primária** e para `UNIQUE`, nunca para chave estrangeira.
`setor.evento_id` tinha o dele desde a Story 2.3, com o motivo escrito ao lado; `organizador_id`
não, mesmo sendo a coluna do `where` das duas leituras desta seção. Corrigido no code review da
Epic 2, **dentro da migração `b91316d771ae`** e não numa revisão nova — naquela altura ela só tinha
rodado em banco local e de teste, e a `main` ainda não conhecia a tabela `evento`. Depois do merge
isso não se faz mais: migração aplicada não se reescreve.

### O escopo é a sessão, e não há por onde outro id entrar

`listar_do_organizador(sessao, organizador)` recebe o `Usuario` da dependência de papel, nunca um
`organizador_id` solto. É a mesma assinatura do `publicar()` da Story 2.4, e o efeito é o mesmo: ver
os eventos de outra pessoa não é uma chamada que o service recusa, é uma chamada que **não existe**.
Não há parâmetro de query, de caminho nem de corpo por onde um id alheio pudesse chegar.

No detalhe, o mesmo princípio vira uma consulta com **as duas** condições:

```python
select(Evento).where(Evento.id == evento_id, Evento.organizador_id == organizador.id)
```

E não `sessao.get(Evento, id)` seguido de um `if evento.organizador_id != organizador.id`. As duas
versões funcionam; a segunda cria dois caminhos para a mesma decisão, e o segundo é o que alguém
esquece na próxima rota.

### `EVENTO_NAO_ENCONTRADO`, e por que o 404 é um só

| Código | Status | Quando |
|---|---|---|
| `EVENTO_NAO_ENCONTRADO` | `404` | O id não existe **ou** o evento é de outro organizador |

Os dois casos respondem **a mesma coisa, byte a byte** — e um teste compara os dois corpos inteiros
para garantir que continuam idênticos, não só parecidos. Se diferissem em uma palavra, bastaria uma
sessão de organizador e um laço sobre UUIDs para descobrir quais são eventos de outra pessoa. É a
mesma disciplina do `PORTARIA_INVALIDA` da Story 2.5 e do login da 1.4, que não diz se o e-mail
existe.

Um código próprio em vez do `NAO_ENCONTRADO` genérico que o `CODIGO_POR_STATUS` já daria de graça:
com ele, a tela distingue "esse evento não é seu" de "esse endereço não existe nesta API" — que é a
diferença entre chamar `notFound()` e ter um bug de URL.

Id em formato inválido é `422 DADOS_INVALIDOS`, de graça, porque o parâmetro de caminho é `UUID`:
estrutura é do Pydantic. O que o service decide é outra coisa — se o id **resolve** para um evento
seu.

### O detalhe reusa o `EventoSaida` da publicação, inteiro

Sem um campo novo. É o **mesmo significado** nas duas rotas — "o evento inteiro, como o organizador o
vê" —, e reusar é o que impede o recibo da publicação e a tela de detalhe de divergirem. Foi o
caminho oposto ao do `PortariaSaida` da Story 2.5, que **não** reusou o `UsuarioSaida`, e por isso
mesmo consistente: lá a forma era parecida e o significado, outro.

`senha_hash` não aparece porque o `response_model` está declarado — sem ele, um `Usuario` cru dentro
de `portarias` traria o hash de quem foi escalado numa resposta de rotina. E `organizador_id` também
fica de fora: quem chama já sabe quem é.

Evento **sem ninguém escalado** responde `200` com `"portarias": []`, não erro. Existem eventos assim
no banco — publicados na janela em que a 2.4 já publicava e a 2.5 ainda não exigia a escala.

### As duas passam por service, e o router ficou com cinco rotas

Nenhuma das duas tem transação ou invariante, e mesmo assim nenhuma abre `Session` no router: elas
**tocam o banco**, e é isso que o critério decide. Com elas, `app/api/organizador.py` passou a ter
dois exemplos de cada lado — duas leituras com service (`/portarias` e as duas novas), uma leitura
sem service (`/catalogo`, que fala com integração e não com banco), uma escrita com service
(`POST /eventos`). Se o arquivo crescer na Epic 3, parti-lo por assunto passa a valer a discussão.

## Programação pública

`GET /eventos` é a primeira rota deste projeto que responde **sem conta**, e por isso ela nasceu num
router próprio, `app/api/publico.py`. O critério de entrada ali é literalmente "não exige conta" — o
que é diferente do critério do `organizador.py`, que é por papel. Fiz questão de escrever isso no
docstring do módulo porque a Story 3.4 vai pendurar `/eventos/{id}` no mesmo arquivo e as seguintes
vão criar um `cliente.py`, que é o oposto: exige conta, e é onde a reserva mora. "Público" e
"cliente" não são a mesma coisa, e misturá-los faria a próxima pessoa procurar a guarda de sessão em
dois lugares. A rota é pública **por assinatura**: não há `Depends(exigir_papel(...))` nem nenhuma
outra dependência de sessão na lista de parâmetros, e um dos testes lê o OpenAPI justamente para
falhar no dia em que alguém acrescentar uma.

**O `EventoNaProgramacao` recusa o estoque, e é esse o ponto da story inteira.** Ele devolve sete
campos — `id`, `nome`, `data_hora`, `local`, `cidade`, `preco_minimo_centavos` e `esgotado` — e
nenhum deles é `capacidade`, `vendidos` ou `setores`. O UX-DR7 proíbe contagem exata de ingresso em
tela de cliente, e eu não quis que essa garantia dependesse da tela: o que a API devolve, o devtools
mostra. Quem garante é o `response_model` declarado na rota — sem ele o FastAPI serializaria o que o
service devolvesse. O teste correspondente procura as palavras `capacidade` e `vendidos` no **texto
inteiro** da resposta, e não nas chaves de topo, porque um `setores` aninhado escaparia de uma
conferência de chaves. `imagem_url` também ficou de fora, por outro motivo: a fila de quatro colunas
não tem imagem, e o campo entra na 3.3, junto com a tela que o consome.

Os dois campos derivados existem para dizer o que interessa **sem** revelar número nenhum.
`esgotado` é "nenhum setor com `vendidos < capacidade`", e `preco_minimo_centavos` é o menor preço
**entre os setores que ainda têm ingresso** — não entre todos. Se a Pista, que costuma ser a mais
barata, esgotou, a fila passa a anunciar o preço do camarote, porque anunciar um preço que ninguém
mais consegue pagar é a única forma de a listagem mentir com número. Os dois saem de `setor.vendidos`
e `setor.capacidade` (AD-13); derivar disponibilidade com `COUNT` sobre reserva ou ingresso continua
proibido em qualquer camada, e é agora que o hábito se forma — as duas tabelas só nascem nas Stories
3.5 e 3.9. Evento com **todos** os setores esgotados, e evento sem setor nenhum, caem os dois em
`esgotado: true` com preço `null`: `min()` sobre lista vazia levantaria `ValueError`, e um `if` antes
resolve sem esconder a regra dentro de um `try`.

O filtro é `publicado_em IS NOT NULL` **e** `data_hora >= agora`, os dois no `where`. O primeiro é o
rascunho, cujo teste o code review da Epic 2 tinha adiado esperando esta epic — ele cobre a rota
pública, e a `listar_do_organizador` continua sem o filtro de propósito, porque o rascunho de alguém
é dele. O segundo é decisão de produto minha, e o motivo está no README da raiz. `agora` é lido uma
vez, antes da consulta: duas leituras do relógio na mesma requisição podem discordar sobre o evento
que começa neste instante. A ordem é `data_hora` com `Evento.id` de desempate, pelo mesmo motivo da
lista do organizador, e os setores vêm por `selectinload` — esta é a raiz do produto, a tela mais
visitada que existe aqui, e uma consulta por evento seria o custo crescendo junto com o catálogo.

**A peneira roda no `where` do Postgres, e não na tela** (Story 3.2). A mesma rota ganhou
`?q=`, `?cidade=` e `?periodo=`: o termo casa `nome`, `local` **ou** `cidade` por trecho; a cidade é
igualdade exata, porque o valor vem sempre dos nossos próprios chips e não de um campo de digitação;
e o período é um `str, Enum` com `todos`, `semana` (7 dias corridos) e `mes` (30 dias corridos) — o
teto usa o **mesmo** `agora` do corte de eventos passados, nunca um segundo relógio. Os três se
somam com `AND` **sobre** as duas condições que já existiam, e há um teste para cada um dos dois
provando que rascunho e evento passado continuam fora mesmo quando o termo casa perfeitamente com o
nome deles: um `WHERE` novo não abre porta num corte antigo. A alternativa — devolver a lista
inteira e filtrá-la em JavaScript — daria busca instantânea ao digitar e custaria três coisas: a
raiz viraria uma ilha de cliente, o filtro não sobreviveria a recarregar nem a compartilhar o link,
e a programação inteira atravessaria a rede a cada visita. Filtrar em Python dentro do próprio
service teria o mesmo defeito por outra porta, trazendo a tabela toda para a memória.

**A busca ignora acento, e isso obrigou a primeira migração deste projeto que não cria tabela.**
`sao paulo` precisa achar `São Paulo` porque é assim que as pessoas digitam no celular, e quem
avalia vai digitar assim. Uso a extensão `unaccent` do Postgres nos **dois** lados da comparação —
`unaccent(coluna) ILIKE unaccent(padrão)` —, e ela é habilitada por `06c1ad5ac276`, escrita à mão,
com `CREATE EXTENSION IF NOT EXISTS unaccent` no `upgrade` e o `DROP` no `downgrade`. Descartei um
`translate()` com mapa de letras na consulta: resolveria a mesma tela sem tocar o banco, e é um mapa
de trinta caracteres que ninguém revisa de novo e que esquece `ü` e `ñ` em silêncio. Duas
consequências valem lembrar: sem rodar `alembic upgrade head` no banco de desenvolvimento a suíte
passa e a tela quebra com `function unaccent(text) does not exist`, porque o `conftest.py` migra
sozinho só o `rockhub_teste`; e `unaccent()` não é `IMMUTABLE`, então ela não entra em índice sem
uma função wrapper — com este volume não há índice para criar.

**O termo é escapado antes de virar padrão de `LIKE`, e essa é a linha mais fácil de esquecer da
story.** `%` e `_` são curingas, e o termo vem digitado por gente: sem escape, `?q=%` devolve a
programação inteira com `200` e cara de resultado, e ninguém descobre porque a tela funciona. Escapo
`\`, `%` e `_` nessa ordem — a contrabarra primeiro, ou ela escapa as próprias escapadas — e declaro
`escape="\\"` no `ilike`. Há três testes só sobre isso: `%`, `_` e a contrabarra sozinha, que sem
tratamento derruba a consulta com `invalid escape sequence`, ou seja, `500` para uma busca digitada
por engano. O teto do termo é `Query("", max_length=120)`, o mesmo de `GET /organizador/catalogo`, e
o `<input>` da tela leva o `maxLength` gêmeo.

**`GET /eventos/cidades` existe para os chips não mentirem.** Ela devolve as cidades distintas, em
ordem alfabética, sem `null`, e usando o **mesmo** recorte de publicado e futuro — chip que oferece
uma cidade sem show em cartaz é um filtro que só sabe devolver lista vazia, e quem clicasse
concluiria que a busca está quebrada. Ela **não** recebe parâmetro nenhum, de propósito: a lista de
escolhas é o universo, não o resultado, e encolhê-la conforme se filtra faz o chip sumir debaixo do
cursor de quem ia clicar. Declarei-a **antes** de qualquer rota com path param no `publico.py`, com
comentário explicando: a Story 3.4 pendura `/eventos/{id}` no mesmo router, e com ela em cima o
FastAPI tentaria ler `"cidades"` como UUID e devolveria `422` para um endereço que existe.

**`GET /eventos/destaque` é uma rota própria, e não dois campos a mais na lista** (Story 3.3). A
chamada principal da raiz precisa de duas coisas que a fila não desenha: a arte do evento e os nomes
dos setores. A alternativa era pôr `imagem_url` no `EventoNaProgramacao` e a tela usar `itens[0]`
como capa — uma linha de schema e zero rota nova. Descartei porque **todo** item da programação
passaria a carregar uma URL que só um deles usa, que é exatamente o que eu tinha recusado na 3.1
("campo que nenhuma tela lê é campo que ninguém sabe se está certo"); e pior no caso dos setores,
porque a ficha exigiria `setores` na lista, que é o campo que o UX-DR7 mantém fora dela. Dois
contratos independentes custam uma classe; um contrato que serve às duas telas custa a disciplina de
todas as próximas. O `EventoEmDestaque` devolve nove campos: os sete da fila mais `imagem_url` e
`setores`. **O preço eu tinha deixado de fora e voltei atrás com a tela montada** — a ficha nasceu
como `CASA · CIDADE · SETORES`, e ao ver a capa pronta percebi a consequência de o destaque **sair**
da programação: ele passava a ser o único show da raiz sem "a partir de" em lugar nenhum. Ele voltou
como **um campo derivado**, e não como a lista de setores com preço dentro — que é a diferença entre
devolver um número e devolver o estoque que o produziu.

**`setores` é `list[str]`, e não `list[SetorSaida]`.** A ficha quer três nomes — `Pista, VIP e
Camarote` —, e o `SetorSaida` que já existe carrega `capacidade`, `vendidos` e `preco_centavos`:
reusá-lo "porque já existe um schema de setor" seria o UX-DR7 caindo por reuso, com o estoque inteiro
atravessando a rede para a tela desenhar três palavras. É a primeira vez que um schema deste projeto
devolve uma **projeção** de um relacionamento, e o schema novo é a fronteira que impede o atalho.
Nome de setor não é estoque; contagem é — e essa distinção tem uma consequência no teste que eu quase
deixei passar: a varredura de palavras proibidas desta rota **não pode** ser a mesma de `GET
/eventos`, porque ali `setores` e `imagem_url` são palavras proibidas e aqui são chaves legítimas.
Tirei as duas da lista e escrevi o motivo dentro do teste, ou a próxima pessoa "conserta" apagando a
asserção inteira.

Banco sem show em cartaz responde **`200` com corpo `null`, nunca `404`** — a mesma decisão do `200
[]` da lista, e `204` ficou fora por um motivo concreto do outro lado da rede: ele não tem corpo, e o
`resposta.json()` da tela estouraria num `catch` que existe para falha, transformando "não há show em
cartaz" em "não foi possível carregar". A consulta é própria, com `LIMIT 1`, em vez de
`listar_programacao()[0]`: aquela monta três filtros e roda um laço de derivação de preço sobre a
programação inteira para descartar tudo menos a primeira linha. O recorte é **idêntico** ao da lista
(`publicado_em IS NOT NULL` e `data_hora >= agora`, com `Evento.id` de desempate), e o evento
esgotado **continua sendo o destaque**, com selo e sem link: pular para o próximo com ingresso faria
"o próximo show" deixar de ser verdade, e a capa esconderia justamente o show mais próximo. A rota
não recebe parâmetro nenhum, e está declarada no mesmo bloco de path fixo da `/eventos/cidades` —
agora com um aviso só cobrindo as duas. `preco_minimo_centavos` segue a mesma regra da fila: é o
menor preço **entre os setores que ainda têm ingresso**, `null` quando não há nenhum, e há um teste
com a Pista esgotada a R$ 120,00 ao lado do Camarote a R$ 420,00 provando que ele pula o esgotado —
os setores, esses, continuam os dois na ficha. A suíte foi de 231 para 263 e agora para **279
testes**.

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

Isso vale para as **quatro** origens de erro, cobertas por quatro handlers em
[`app/main.py`](app/main.py):

| Origem | Como chega | Código |
|---|---|---|
| Regra de negócio | `raise ErroDeDominio(codigo=..., mensagem=..., status_http=...)` | o que o `raise` disser |
| Framework | rota inexistente, método errado, `raise HTTPException(...)` | pela tabela `CODIGO_POR_STATUS` — `404` vira `NAO_ENCONTRADO`, `403` vira `SEM_PERMISSAO` |
| Validação do Pydantic | corpo, query ou path reprovados | `DADOS_INVALIDOS` |
| Falha não prevista | qualquer exceção que ninguém tratou — banco fora do ar, bug meu | `ERRO_INTERNO`, com `500` |

O erro de validação merece uma nota. O Pydantic devolve uma lista de objetos aninhados, ótima para
depurar e péssima como contrato — obrigaria o corpo de erro a ter uma forma diferente só neste
caso. Achatei tudo numa frase (`setor_id: campo obrigatório; quantidade: não é um inteiro`), o que
mantém uma forma só na API sem perder qual campo reprovou.

Deixei isso pronto já na primeira story, antes de existir qualquer regra de negócio, porque
padronizar erro depois significa voltar em todo endpoint já escrito.

**O quarto handler entrou no code review da Epic 1, e ele fecha a promessa.** Até ali eu tinha três,
e escrevia que "toda" resposta de erro tem esta forma — não tinha. Exceção não tratada subia até o
`ServerErrorMiddleware` do Starlette e voltava como `Internal Server Error` em **texto puro**: a
única resposta da API fora do próprio contrato, e justo a que aparece quando o banco cai. Eu tinha
registrado a ausência aqui como corte de escopo ("tratá-la exigiria decidir o que registrar em
log"), e a revisão mostrou que a decisão de log cabia em uma linha — enquanto o contrato quebrado
custava a promessa inteira.

O corpo do `500` **não** carrega a causa: mensagem de exceção traz host, usuário e nome de tabela
com frequência demais para virar resposta HTTP. O rastro completo vai para o log via
`logger.error(..., exc_info=erro)`, e um teste garante que nem o IP nem a senha do texto de exemplo
aparecem no corpo da resposta.

**A mensagem do framework também virou português.** O Starlette preenche o `detail` sozinho quando
ninguém passa um — `"Not Found"`, `"Method Not Allowed"` —, e essas eram as únicas strings em inglês
de um sistema em que até a rota de saúde é `/saude`. O `tratar_erro_http` compara o `detail` com a
frase padrão do `HTTPStatus`: se for igual, o framework não disse nada e a mensagem vem da tabela
`MENSAGEM_POR_STATUS`; se for diferente, alguém a escreveu de propósito e ela é preservada. Isso não
mexe no contrato, porque quem decide o texto de tela é o `codigo`.

## Testes

```bash
docker compose up -d      # a partir da Story 1.3, os testes exigem o Postgres no ar
cd backend
uv run pytest
```

São **263 testes** em `tests/`, espelhando `app/`. Cobrem a rota de saúde, o `/docs`, as quatro
origens de erro, a leitura de configuração do ambiente, a migração Alembic, os modelos `Usuario`,
`Evento` e `Setor`, o hash e o token de sessão, as quatro rotas de autenticação, a dependência de
papel, o seed de avaliação, o cliente da Ticketmaster (`test_ticketmaster.py`, todo offline — ver
[Catálogo da Ticketmaster](#catálogo-da-ticketmaster), incluindo os quatro do filtro de
classificação), a rota `GET /organizador/catalogo` (`test_organizador_catalogo.py`, Story 2.2,
também offline), a rota `POST /organizador/eventos` (`test_organizador_eventos.py`, Stories 2.4 e
2.5), a rota `GET /organizador/portarias` (`test_organizador_portarias.py`, Story 2.5) e as duas
rotas de leitura do organizador (`test_organizador_meus_eventos.py`, Story 2.6) e as duas rotas
públicas, `GET /eventos` e `GET /eventos/cidades` (`test_programacao.py`, Stories 3.1 e 3.2 —
incluindo os três testes do escape do `LIKE` e os dois da busca sem acento nos dois sentidos).

`test_programacao.py` é o único arquivo cujos testes começam por `cliente.cookies.clear()` em vez de
um login: o `TestClient` guarda cookie entre chamadas, e um teste que "prova" acesso anônimo depois
de outro ter feito login não prova nada. As datas ali são relativas (`datetime.now() + timedelta`),
e não constantes como `2026-08-15` — o corte da rota é `data_hora >= agora`, então uma data fixa no
futuro vira passado assim que o calendário a alcança, e o teste passaria a falhar sozinho meses
depois sem ninguém ter mexido em nada.

`test_organizador_portarias.py` prova a ordenação por nome com contas de **nomes diferentes**, criadas
no próprio arquivo: a `fabricar_usuario` do `conftest.py` grava todo mundo como "Alguém" e parametriza
só o e-mail, e com nomes iguais "ordenado por nome" não decide nada — o teste passaria por acaso.
Prova também que a lista não traz organizador nem cliente, que o corpo tem exatamente `id`, `nome` e
`email`, que `senha_hash` não aparece, e que lista vazia é `200` e não `404`.

`test_organizador_meus_eventos.py` (Story 2.6) grava os eventos **direto pelo ORM**, e não pela rota
`POST /organizador/eventos`. Publicar pela rota acoplaria dezesseis testes de leitura às quatro
recusas das Stories 2.4 e 2.5, e o dia em que uma delas mudasse todos quebrariam sem ter nada a ver
com o assunto — a fixture aqui é o **estado** de que a leitura precisa, não o caminho que o produz.
É também o único jeito de gravar `vendidos` diferente de zero: nenhuma rota de escrita sabe fazê-lo,
e só a Epic 3 vai saber. Sem isso, o teste da soma passaria somando dois zeros.

⚠️ **Nenhuma contagem de `test_seed.py` é literal desde a Story 2.5.** Elas derivam de `CONTAS` —
`len(CONTAS)`, `Counter` dos papéis declarados. A quinta conta semeada quebrou seis testes que tinham
`4` escrito na mão, nenhum deles com qualquer relação com quantas contas existem. Acrescentar a sexta
agora não custa nada.

`test_organizador_eventos.py` (Story 2.4) é o primeiro arquivo que prova **escrita** de domínio, e
por isso quase todo teste ali lê do **banco** depois da resposta: a resposta prova o schema de
saída, só o `sessao.get(Evento, id)` prova que a linha existe do jeito que deveria. Cobre os campos
do catálogo copiados, `vendidos` nascendo zero, `publicado_em` carimbado, o dono vindo da sessão com
**dois** organizadores no mesmo teste, um `organizador_id` no corpo sendo ignorado, os dois códigos
de erro novos sem deixar nada gravado, a data sem fuso recusada e a com offset gravada em UTC, e os
três papéis batendo na porta (`401` sem cookie, `403` para cliente e portaria). Um deles instala um
transporte HTTP que chama `pytest.fail` se for tocado — é assim que "publicar não fala com a
Ticketmaster" vira um teste em vez de uma promessa.

`test_evento.py` (Story 2.3) prova as invariantes que **o banco** garante, não o Python: as quatro
constraints do `setor` recusando cada estado proibido com `IntegrityError`, o `CASCADE` levando os
setores junto quando o evento é apagado pela sessão, o rascunho com `publicado_em` em `NULL`, e o
`UPDATE` condicional do AD-3 afetando zero linhas quando se pede mais do que resta. Precisa do
Compose no ar — é Postgres real, não um dublê.

### O que `test_seed.py` prova

Quase tudo ali é sobre o que o seed **não** faz, porque é o primeiro código deste repositório escrito
para rodar contra o banco de produção, repetidamente, sem ninguém olhando: que a segunda execução não
duplica nem levanta exceção; que uma conta que já existe com o mesmo e-mail sai com **nome e
`senha_hash` idênticos** aos de antes; que uma conta criada por `/cadastro` continua lá depois do
seed; que um e-mail semeado que existe com outro papel devolve `papel-divergente` sem alterar o
papel; que a senha publicada no README realmente autentica por **todas** as contas (é o que prova que
o hash é Argon2id de verdade, e não uma string colada); e que todo e-mail de `CONTAS` já sai
normalizado — comparado contra o que o `EmailNormalizado` do login produziria.

⚠️ **Nenhum teste chama `main()`.** `main()` abre `SessaoLocal`, que aponta para `DATABASE_URL` — o
banco de **desenvolvimento**. Um teste que o chamasse gravaria as contas fora do banco de teste,
passaria verde, e ninguém descobriria até estranhar contas repetidas em `rockhub`. É por isso que
`semear()` recebe a `Session` por parâmetro e só o `main()` escolhe o banco: a mesma regra que a
Story 1.3 aplicou à URL do Alembic na fixture.

### A rota `/_teste` não existe no código de produção

Se você procurar `/_teste/so-organizador` em `app/`, não vai achar: ela é declarada **dentro de**
`tests/test_autorizacao.py`, montada no `app` real por uma fixture de módulo e removida no teardown.
`app/` não importa `tests/`, então nada disso sobe com a aplicação.

Ela existe porque provar o `403` exige uma rota que exija papel, e a primeira rota real de
organizador é escopo da Epic 2. As duas alternativas: criar uma rota provisória de verdade em
`app/api/` (daria `curl` no navegador, ao custo de uma rota que não faz nada esquecida em produção)
ou adiar o `403` para a Epic 2 (deixaria um AC do `epics.md` sem cumprir e o AD-9 sem materialização
nesta epic).

Dois detalhes que a fizeram funcionar: ela é montada no `app` **real**, e não num `FastAPI()` novo —
os três `exception_handler` que dão à API a forma `{"erro": {...}}` estão em `app/main.py`, e um app
novo não os teria, fazendo os testes afirmarem sobre um `{"detail": ...}` que a API nunca devolve. E
o teardown remove as rotas **e** zera `app.openapi_schema`: o `app` é módulo importado por toda a
suíte, e rota que fica é rota que outro arquivo encontra por acidente.

⚠️ **O `TestClient` guarda cookie entre chamadas.** Um teste que faz login e depois quer provar o
`401` precisa de outra instância ou de `cliente.cookies.clear()` — senão o cookie da chamada
anterior autentica a seguinte sem ninguém pedir.

Um dos testes de cadastro merece nota: em vez de afirmar à mão os quatro atributos do cookie, ele
**compara o cabeçalho do cadastro contra o do login**, ignorando só o valor do token. Repetir as
quatro asserções nos dois lugares deixaria a suíte passar no dia em que apenas uma das rotas mudasse;
do jeito que está, divergência entre elas é o que quebra — que é exatamente o que o helper
compartilhado existe para impedir.

Para testar os erros eu montei apps mínimas com os handlers reais e rotas que só existem para
falhar. Assim o contrato fica verificado desde já, sem precisar esperar o primeiro endpoint de
negócio aparecer para descobrir que ele estava errado. O `404` e o `405` são testados direto na
aplicação de verdade, e um teste confere que os quatro handlers estão de fato registrados nela — de
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
variável de ambiente.

⚠️ **E a trava roda antes do `DROP`, não depois — isso mudou no code review da Epic 1.** Eu tinha só
o `test_banco_de_teste_e_o_rockhub_teste`, que confere `SELECT current_database()`, e ele me dava
uma sensação de segurança que não existia: **teste roda depois da fixture de sessão**, e a fixture
começa com `alembic downgrade base`. Ele relatava o desastre em vez de impedi-lo. Agora
`_exigir_banco_de_teste()` roda dentro da fixture, antes da primeira chamada destrutiva, e levanta
`RuntimeError` sem executar migração nenhuma se o banco não se chamar `rockhub_teste`.

O cenário que isso fecha: `DATABASE_URL_TESTE` exportada apontando para a Railway — é a variável mais
fácil de errar, porque o `.env.example` documenta o formato dela ao lado do de produção — e um
`uv run pytest` distraído migrando o banco de produção do zero. A conferência é pelo **nome** do
banco e não pelo host: `localhost` não garante nada, porque um túnel de porta aponta para qualquer
lugar.

## Deploy na Railway

A API está no ar em <https://elite-dev-rockhub-production.up.railway.app>, com o PostgreSQL no
mesmo projeto da Railway. **Não existe `railway.json`, `Dockerfile` nem `Procfile` neste
repositório** — a configuração mora no painel, e esta seção é onde ela está escrita. É de propósito,
e o motivo está no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

Se você for subir a sua própria cópia, é isto, na ordem:

### 1 · O serviço

O backend e o Postgres precisam ficar **no mesmo projeto e ambiente** da Railway. A rede privada não
atravessa projetos, e é por ela que um alcança o outro sem passar pela internet.

| Onde | Campo | Valor |
|---|---|---|
| `Create` → `GitHub Repo` | repositório | `elite-dev-RockHub` |
| Settings → Source | **Root Directory** | `backend` |
| Settings → Source | **Branch** | a branch que você quer publicar |
| Settings → Build | Builder | `Railpack` (é o padrão; não precisa mexer) |

⚠️ **O `Root Directory` é o passo que ninguém encontra de primeira** — ele fica escondido no meio de
Settings → Source. Sem ele a Railway olha a raiz do monorepo, onde não há `pyproject.toml` nem
`package.json`, não detecta linguagem nenhuma e o build morre num `railpack process exited with an
error` que não diz o que faltou. Foi exatamente assim que o meu primeiro build falhou.

E confira a **branch**: a Railway assume a branch padrão do repositório, que pode não ser a que tem
o código.

### 2 · As variáveis

| Variável | Valor | Por quê |
|---|---|---|
| `AMBIENTE` | `producao` | Ativa o `Secure` no cookie e a recusa do `JWT_SECRET` de exemplo |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Referência ao serviço Postgres |
| `JWT_SECRET` | um valor gerado | Sem ele a aplicação não sobe, de propósito |
| `TICKET_SIGNING_SECRET` | outro valor gerado | Ainda não lido — Story 3.9 |
| `TICKETMASTER_API_KEY` | a chave do portal da Ticketmaster | Lida desde a Story 2.1. Sem ela, a aplicação não sobe com `AMBIENTE=producao` |
| `CORS_ORIGENS` | `http://localhost:3000,https://elite-dev-rock-hub.vercel.app` | As origens autorizadas a chamar a API direto. **Não é o que faz o login funcionar** — ver abaixo |

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Rode duas vezes: os dois segredos precisam ser **diferentes**, senão trocar um obriga a trocar o
outro.

`${{Postgres.DATABASE_URL}}` vai **literal**, com as chaves duplas — é a sintaxe de referência da
Railway, e `Postgres` é o nome do serviço de banco. Ela resolve para o host interno
`postgres.railway.internal`. Quando a referência bate, o canvas do projeto desenha uma seta de um
serviço para o outro; se ficar sem seta, o nome não corresponde a serviço nenhum.

A URL chega como `postgresql://…` e a `Settings` a normaliza para `postgresql+psycopg://`. Esse
validador existe desde a Story 1.4, escrito para este dia — sem ele o erro seria um
`ModuleNotFoundError: psycopg2` que não aponta para a URL como causa.

⚠️ **Defina as variáveis antes do primeiro deploy.** O Pre-deploy Command importa
`app.core.config`, e a `Settings` recusa o `JWT_SECRET` de exemplo com `AMBIENTE=producao`. Se
faltar `JWT_SECRET`, o deploy falha na *migração*, com uma mensagem sobre segredo — e você vai
procurar o problema no banco.

O valor do `CORS_ORIGENS` é **público de propósito** — origem não é segredo, e escrevê-lo aqui é o
que torna esta seção refazível. Separador é vírgula; espaço depois não quebra, porque o
`_separar_por_virgula` da `Settings` faz `strip()`, mas a forma canônica é sem. **Sem barra no fim e
sem caminho**: origem é esquema + host, nunca URL. E **nada de `*`** — curinga é incompatível com
`allow_credentials=True` desde a Story 1.1, e a sessão vive num cookie.

⚠️ **Trocar essa variável exige redeploy do backend.** A `Settings` é `@lru_cache` e nasce junto com
o processo: valor novo no painel, sem redeploy, não chega a lugar nenhum. O sintoma é conferir a
variável no painel, vê-la certa, e o preflight continuar recusando.

Como conferir de fora, sem abrir o painel:

```bash
curl -i -X OPTIONS https://elite-dev-rockhub-production.up.railway.app/auth/login \
  -H "Origin: https://elite-dev-rock-hub.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

`200` com um cabeçalho `access-control-allow-origin` ecoando a origem = configurado. `400` **sem**
esse cabeçalho = a origem não está na lista, ou o redeploy não aconteceu.

#### Por que essa variável não é o que faz o login funcionar

Vale escrever com todas as letras, porque é a conclusão errada mais fácil de tirar — e tirá-la
apagaria a razão de o proxy existir.

Em produção, o caminho de uma requisição de login é:

```
navegador ──► elite-dev-rock-hub.vercel.app/api/auth/login      (mesma origem: sem CORS)
                     │  rewrite do next.config.ts, no servidor da Vercel
                     ▼
   elite-dev-rockhub-production.up.railway.app/auth/login    (servidor↔servidor: sem CORS)
```

CORS é uma política **do navegador** sobre requisição que ele mesmo faz para outra origem. **Nenhuma
das duas setas é isso**: a primeira é mesma origem, e a segunda não passa por navegador nenhum. O
`CORS_ORIGENS` não está no caminho do login, e mexer nele não conserta login quebrado — o lugar de
olhar é o `API_URL` da Vercel, e o conserto termina em redeploy.

O que **de fato** faz o cookie funcionar entre os dois fornecedores é o proxy `/api/*` da Story 1.4:
`vercel.app` e `up.railway.app` estão os dois na *Public Suffix List*, então são sites diferentes
para o navegador, e um cookie `SameSite=Lax` não sobreviveria ao cruzamento (AD-15).

**Então por que acrescentei a origem?** Porque o `CORSMiddleware` é a rede de proteção de **chamada
direta** — um `curl` de demonstração, uma página futura sem proxy, um cliente de terceiro. A origem
publicada existir na lista é o estado correto do sistema: no dia em que algo chamar a API sem passar
pelo Next, a resposta certa já está configurada, em vez de virar meia hora de depuração. É
configuração de um caminho que hoje não existe, e está aqui declarado como tal.

### 3 · Os comandos e o health check

| Campo | Valor |
|---|---|
| **Pre-deploy Command** | `alembic upgrade head && python -m seeds.semear` |
| **Custom Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Healthcheck Path** | `/saude` |

Depois do primeiro deploy verde: Settings → Networking → **Generate Domain**. Ele pergunta a porta
em que a aplicação escuta — a Railway detecta e preenche (aqui foi `8080`, e confere com a linha
`Uvicorn running on http://0.0.0.0:8080` do log). Porta alvo errada dá `502` **com o deploy verde**,
que é o sintoma mais enganoso da plataforma.

#### Por que os comandos não usam `uv run`

Porque o `uv` não existe na imagem final. O Railpack instala o `uv` só na fase de build; o que ele
entrega para o contêiner de execução é a virtualenv, com `/app/.venv/bin` no `PATH`. Ali dentro
`alembic`, `uvicorn` e `python` são chamáveis diretamente, e `uv run alembic …` falha com
`uv: not found`.

É a mesma virtualenv que o `uv run` usaria localmente — alcançada por outro caminho. **Não
"corrija" esses comandos para `uv run`**: é o primeiro erro que quem conhece o projeto pelo
desenvolvimento local vai cometer.

Dois detalhes do Start Command que não são enfeite: **`--host 0.0.0.0`**, porque o proxy da Railway
não alcança quem escuta em `127.0.0.1`, e **`--port $PORT`**, porque a porta é injetada por ela. Os
dois erros produzem o mesmo `502 Application failed to respond`.

E o `-m` do `python -m seeds.semear` é a armadilha da Story 1.7, agora em produção: executar o
arquivo direto põe `/app/seeds` no caminho de import em vez de `/app`, e `import app` para de
resolver.

#### Por que Pre-deploy e não encadeado no start

O Pre-deploy Command roda **num contêiner separado**, depois do build e antes de o tráfego ser
trocado para a versão nova, com as variáveis de ambiente do serviço. Se ele sair diferente de zero,
não é repetido e **o deploy não prossegue** — a versão anterior continua atendendo.

Encadear `alembic … && seed && uvicorn` no Start Command funcionaria em qualquer plataforma, mas
roda uma vez por réplica e outra a cada reinício automático, e uma migração quebrada tiraria do ar
a versão que estava funcionando, em vez de barrar a nova.

Isso também explica por que o seed da Story 1.7 sai em `0` mesmo quando avisa sobre papel
divergente: um `exit(1)` por causa de um aviso derrubaria o deploy inteiro. E por que ele **não
imprime a senha** — o que ele escreve vai para o log de deploy da Railway.

### 4 · Como saber que deu certo

No log do **Pre-deploy**, nesta ordem: as migrações do Alembic, e logo depois uma linha por conta
semeada. Na primeira vez elas dizem `criada`; **em todo redeploy seguinte, `mantida`** — que é a
prova, em produção, de que o seed não recria nem sobrescreve nada. No primeiro deploy depois da Story
2.5, `portaria2@rockhub.dev` sai `criada` e as outras quatro `mantida`: é o comportamento certo, e é
o que mostra que acrescentar conta não mexe em nada do que já estava lá.

De fora, com `curl`:

```bash
URL=https://elite-dev-rockhub-production.up.railway.app

curl -i $URL/saude          # 200 {"status":"ok"}
curl -i -X POST $URL/auth/login -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

O login é a verificação que mais paga: ele só devolve `200` se a migração criou a tabela **e** o
seed gravou a conta **e** o `DATABASE_URL` aponta mesmo para o Postgres da Railway. Três coisas
provadas numa chamada.

E confira o `Set-Cookie`: ele precisa vir com **`Secure`**. É o único sintoma observável de fora de
que `AMBIENTE=producao` chegou até a aplicação, porque `cookie_secure` é derivado do ambiente e não
é campo configurável.

### 5 · Quando falhar, onde olhar

| Sintoma | Causa |
|---|---|
| `railpack process exited with an error`, com a raiz do repositório listada no log | Falta `Root Directory = backend` |
| `uv: not found` | Alguém escreveu `uv run` nos comandos |
| Deploy verde e URL respondendo `502` | `--host 0.0.0.0` ou `--port $PORT` ausentes, ou porta alvo errada no domínio |
| Deploy falha na migração com mensagem sobre `JWT_SECRET` | Variáveis não definidas antes do primeiro deploy. Não é problema de banco |
| `could not translate host name "postgres.railway.internal"` | O Postgres está em outro projeto, ou o nome na referência não existe. Use `DATABASE_PUBLIC_URL` ou mova o banco |
| `ModuleNotFoundError: No module named 'psycopg2'` | A normalização de URL da `Settings` foi removida |
| `uv sync --locked` falha no build | O `uv.lock` divergiu do `pyproject.toml`. Rode `uv sync` e comite o lockfile |
| Health check falhando com a aplicação de pé | O caminho é `/saude`; a raiz da API responde `404` de propósito |

### O que o Railpack faz com este projeto

Lido no provider Python dele, não deduzido:

| Fase | O que acontece |
|---|---|
| Detecção | Acha `pyproject.toml`; identifica `uv` pelo `uv.lock` |
| Versão do Python | Lê o `.python-version` → **3.12** (sem esse arquivo, cairia no 3.13) |
| Install / build | `uv sync --locked --no-dev --no-install-project`, depois `uv sync --locked --no-dev --no-editable` |
| Ambiente | `VIRTUAL_ENV=/app/.venv`, `PATH` com `/app/.venv/bin`, `PYTHONUNBUFFERED=1` |
| Imagem final | Contém a virtualenv. **Não contém o `uv`** |
| Workdir | `/app` — com `Root Directory = backend`, é o conteúdo de `backend/` |

Três consequências que valem no dia a dia:

- **`--no-dev`**: `pytest` e `httpx` não sobem para produção. A suíte não roda lá, e não deve — a
  fixture de banco derruba e recria o schema pelo Alembic
- **`--locked`**: o build **falha** se o lockfile divergir do `pyproject.toml`. A versão que sobe é
  literalmente a travada no repositório
- **workdir `/app`**: o `uvicorn` insere o diretório corrente no `sys.path` (é o `--app-dir`, que já
  vem como `.`), o Alembic tem `prepend_sys_path = .` no `alembic.ini`, e `python -m` põe o corrente
  no caminho. Os três comandos acham `app` e `seeds` sem variável de ambiente nenhuma
