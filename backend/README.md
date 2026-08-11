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
uv run python -m seeds.semear             # as 4 contas de avaliação — rodar de novo é seguro
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

As quatro contas de avaliação vêm de um comando só, rodado com o banco migrado:

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

O relatório sai uma linha por conta, e o comando termina em `0`:

```
ORGANIZADOR  organizador@rockhub.dev   criada
CLIENTE      cliente@rockhub.dev       criada
CLIENTE      cliente2@rockhub.dev      criada
PORTARIA     portaria@rockhub.dev      criada
As senhas estão no README da raiz, em "Contas semeadas".
```

Na segunda execução as quatro dizem `mantida`. Este é **o único caminho do sistema que cria conta com
papel diferente de `CLIENTE`** — `cadastrar()` fixa o papel em literal, e nenhuma rota oferece
alternativa.

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
      organizador.py  # GET /organizador/catalogo — exceção ao paradigma, ver abaixo
    services/        # regra de negócio, transações e acesso ao banco
      autenticacao.py # autenticar() e obter_usuario() (só leem) · cadastrar() (grava e commita)
    models/          # SQLAlchemy
      base.py        # Base declarativa + convenção de nomes de constraint
      usuario.py      # PapelUsuario + Usuario
    schemas/         # Pydantic de entrada e saída
      auth.py         # CadastroEntrada, LoginEntrada, UsuarioSaida, EmailNormalizado
      catalogo.py     # ItemDoCatalogo — o formato do catálogo, não o da Ticketmaster
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
    versions/
  seeds/              # dados exigidos pelo desafio — não sobe com o uvicorn
    semear.py          # as quatro contas de avaliação; idempotente, nunca apaga nada
  tests/              # espelha a estrutura de app/
    conftest.py        # fixtures de banco + o TestClient ligado a elas
    test_organizador_catalogo.py  # GET /organizador/catalogo — precisa do Compose no ar
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
o nome da pasta é outro. **A exceção vale só para o catálogo.** A Story 2.4 grava evento e setor no
banco: tem transação e invariante, então tem service, sem discussão — o critério que separa os dois
casos é justamente esse.

## Catálogo da Ticketmaster

`app/integrations/ticketmaster.py` (Story 2.1) é a única peça do backend que fala com um serviço
fora dele. `buscar_eventos(termo, *, limite=20)` consulta a Discovery API e devolve
`list[ItemDoCatalogo]` — o formato **deste projeto**, não o da Ticketmaster.

```
# com termo
GET https://app.ticketmaster.com/discovery/v2/events.json
    ?apikey=<TICKETMASTER_API_KEY>&keyword=<termo>&size=<limite>&locale=*&countryCode=BR

# sem termo — lista de exemplos (Story 2.2, revisada)
GET https://app.ticketmaster.com/discovery/v2/events.json
    ?apikey=<TICKETMASTER_API_KEY>&size=<limite>&locale=*&countryCode=BR&sort=date,asc
```

**`countryCode=BR` entrou na Story 2.2**, junto com a superfície HTTP. Sem ele, buscar "metallica"
devolve os vinte primeiros shows do mundo — quase todos nos EUA — e nenhum brasileiro entra no
`size=20`; a tela do organizador pareceria quebrada para quem estiver avaliando. **Limitação
assumida**: um show fora do Brasil não aparece nesta busca. Está registrada também em [O que não
está pronto](../README.md#o-que-não-está-pronto) do README da raiz.

| Limite da Discovery | Valor | O que faço com ele |
|---|---|---|
| Por segundo | 5 req/s | Nada — uma busca por evento publicado não chega perto |
| Por dia | 5 000 chamadas | Termo em branco não gera requisição nenhuma (ver abaixo) |

**Termo vazio, só espaços, ou ausente não faz requisição — devolve `[]` direto.** Um campo de busca
vazio não vale uma chamada da cota diária.

**Toda falha vira o mesmo erro.** Timeout, conexão recusada, `401`, `429`, `500` ou corpo que não é
JSON válido — os seis viram `ErroDeDominio("CATALOGO_INDISPONIVEL", ..., status_http=503)`. Quem
chama não precisa saber qual dos seis aconteceu; o log sabe (`401` vira `logger.error`, porque é
chave errada ou revogada — erro meu, não instabilidade da Ticketmaster; os demais viram
`logger.warning`). **A chave nunca aparece em log nenhum**: as exceções do `httpx` carregam a URL
completa da requisição, e a URL carrega `apikey=` — um `logger.exception()` por reflexo vazaria a
chave para o log da Railway, furando o AD-2 pelo lado de dentro do backend. Um teste prova que o
valor da chave não aparece nem no `caplog` nem na mensagem do `ErroDeDominio`.

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

São **121 testes** em `tests/`, espelhando `app/`. Cobrem a rota de saúde, o `/docs`, as quatro
origens de erro, a leitura de configuração do ambiente, a migração Alembic, o modelo `Usuario`, o
hash e o token de sessão, as quatro rotas de autenticação, a dependência de papel, o seed de
avaliação, o cliente da Ticketmaster (`test_ticketmaster.py`, todo offline — ver
[Catálogo da Ticketmaster](#catálogo-da-ticketmaster)) e a rota `GET /organizador/catalogo`
(`test_organizador_catalogo.py`, Story 2.2, também offline).

### O que `test_seed.py` prova

Quase tudo ali é sobre o que o seed **não** faz, porque é o primeiro código deste repositório escrito
para rodar contra o banco de produção, repetidamente, sem ninguém olhando: que a segunda execução não
duplica nem levanta exceção; que uma conta que já existe com o mesmo e-mail sai com **nome e
`senha_hash` idênticos** aos de antes; que uma conta criada por `/cadastro` continua lá depois do
seed; que um e-mail semeado que existe com outro papel devolve `papel-divergente` sem alterar o
papel; que a senha publicada no README realmente autentica pelas quatro contas (é o que prova que o
hash é Argon2id de verdade, e não uma string colada); e que todo e-mail de `CONTAS` já sai
normalizado — comparado contra o que o `EmailNormalizado` do login produziria.

⚠️ **Nenhum teste chama `main()`.** `main()` abre `SessaoLocal`, que aponta para `DATABASE_URL` — o
banco de **desenvolvimento**. Um teste que o chamasse gravaria quatro contas fora do banco de teste,
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

No log do **Pre-deploy**, nesta ordem: as migrações do Alembic, e logo depois quatro linhas do seed.
Na primeira vez elas dizem `criada`; **em todo redeploy seguinte, `mantida`** — que é a prova, em
produção, de que o seed não recria nem sobrescreve nada.

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
eliminar.

> Escrevi aqui, na 1.4, que `EmailStr` faria sentido na 1.5, onde o e-mail é *gravado*. Quando cheguei
> lá, decidi o contrário — e o porquê está na [Story 1.5](#story-15--cadastro-de-cliente) e no README
> da raiz. Deixo a previsão errada escrita de propósito: apagá-la esconderia que houve uma escolha.

O `PasswordHasher()` sem argumento nenhum já entrega o que o AD-15 pede: Argon2id é o tipo padrão,
os parâmetros são o perfil de baixa memória da RFC 9106, o sal é aleatório por hash e viaja dentro
da própria string — por isso não existe coluna de sal, e não deve existir. Como todos os parâmetros
estão embutidos no hash, trocá-los depois não invalida o que já está gravado. O custo é real e é
proposital: cada verificação leva ~50ms e ~64 MB, o que deixa os testes de login perceptivelmente
mais lentos que os outros e vai importar na hora de escolher o tamanho da instância na Railway
(Story 1.8).

### Story 1.5 — cadastro de cliente

A primeira story desde a 1.1 que **não acrescenta dependência nenhuma**: nada de `uv sync`, nada no
lockfile. Isso é consequência direta de ter escrito a validação de e-mail à mão em vez de instalar
`email-validator` para usar `EmailStr` — decisão de produto, com a alternativa descartada registrada
no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

Também não houve migração. O modelo `Usuario` da Story 1.3 já tinha tudo de que o cadastro precisa, e
o fato de nenhuma coluna ter mudado é o sinal de que aquela story dimensionou certo.

Entraram `CadastroEntrada` e o tipo `EmailNormalizado` no schema, `cadastrar()` no service, e
`POST /auth/cadastro` no router — mais a extração dos dois helpers de cookie, que agora seriam
escritos duas vezes. As regras de cada campo, a detecção de duplicata pelo `IntegrityError` e a
convenção de transação estão na seção [Autenticação](#autenticação) acima.

Três convenções que valem daqui para a frente:

- **Service que escreve faz `commit`; service que lê não faz nada.** `autenticar()` e `cadastrar()`
  são o par que mostra a regra
- **Duplicata é detectada pelo banco, nunca por um `SELECT` antes do `INSERT`**
- **O papel de uma conta nunca vem do corpo da requisição** — é literal no service, e a assinatura da
  função é a garantia

Uma armadilha que só aparece sob teste ficou documentada em [Autenticação](#autenticação): depois de
um `409`, o `rollback()` do service leva junto o que a fixture inseriu por `flush`, e um `assert`
sobre o banco naquele ponto acusa um bug que não existe.

Duas rotas mudaram de forma sem mudar de comportamento (`entrar` e `sair`, agora chamando os
helpers), e os 40 testes anteriores continuaram passando sem uma linha alterada — que era exatamente
o critério dessa refatoração.

### Story 1.6 — cada papel só acessa o que lhe cabe

A segunda story seguida sem dependência nova e sem migração: nada de `uv sync`, nada no lockfile,
nenhuma coluna alterada. O modelo `Usuario` da 1.3 já previa esta story no próprio docstring, e o
`UsuarioSaida` da 1.4 serviu a terceira rota sem mudar uma linha.

Entrou um arquivo: [`app/core/dependencias.py`](app/core/dependencias.py), com `usuario_atual` e
`exigir_papel` — o AD-9 saindo do documento e virando código. O resto foram acréscimos:
`obter_usuario()` no service (leitura por `Session.get`, sem `commit`, do lado que só lê), e
`GET /auth/eu` no router, com uma linha de corpo e nenhuma `Session` na assinatura, porque
`usuario_atual` já recebeu a dela.

Nos testes, a fixture `cliente` saiu de `test_auth.py` e foi para o `conftest.py` — ela é
infraestrutura, e o `test_autorizacao.py` passou a precisar dela. Junto dela nasceu
`fabricar_usuario`, que grava conta com o papel que o teste pedir. A `usuario_gravado` **não** foi
reescrita sobre a fábrica: quinze testes de login e cadastro dependem daquele e-mail exato, e trocar
uma fixture já conferida por uma genérica não ganharia nada. Os 55 testes anteriores passaram sem
uma linha alterada.

Duas armadilhas que custaram tempo e vão se repetir:

- **`exigir_papel` precisa depender de `usuario_atual` por `Depends`**, não por chamada direta. É o
  que faz a ordem `401` antes de `403` acontecer sozinha. O teste
  `test_sem_cookie_na_rota_de_papel_responde_401_e_nao_403` existe exatamente para quebrar se
  alguém "simplificar" isso
- **`UUID(str(carga["sub"]))`, com o `str()`.** O `sub` chega dentro de um `dict` sem tipo; um `sub`
  numérico faria `UUID(int)` levantar `AttributeError` em vez de `ValueError`, o `except` não
  pegaria, e um cookie malformado viraria `500` no lugar de `401`

As quatro decisões de projeto desta story — autorização como dependência, papel lido do banco,
guarda na página em vez de `middleware`, e redirecionar com volta — estão no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo), cada uma com a alternativa que
descartei.

### Story 1.7 — dados semeados para avaliação

A primeira story do projeto que **não toca `app/`**: nenhuma linha da aplicação mudou, nenhuma
coluna, nenhuma migração, nenhuma dependência nova — a terceira seguida sem `uv sync`. Nasceu a pasta
`seeds/`, com `semear.py`, e o `test_seed.py` ao lado dos outros. Ela existe para o avaliador, não
para o usuário: até aqui, organizador e portaria vinham de um `uv run python -c` de dez linhas colado
no README da raiz, que é exatamente o tipo de instrução que alguém copia errado às onze da noite.

O risco desta story não estava na complexidade — o script tem trinta linhas — e sim em **o que ele
faz com dado que já existe**, porque é o primeiro código daqui escrito para rodar contra o banco de
produção a cada deploy. Por isso a maior parte do que eu escrevi e testei é sobre o que ele não faz,
e está em [Dados semeados](#dados-semeados).

Três detalhes de implementação que decidem se isto funciona:

- **`semear()` recebe a `Session`; só o `main()` abre a de produção.** É o que permite ao teste rodar
  o seed dentro da transação revertida do `conftest.py`. Se a função abrisse `SessaoLocal` por conta
  própria, todo teste do arquivo gravaria no banco de desenvolvimento
- **`commit` por conta, não um no fim.** Uma falha na terceira conta não desfaz as duas primeiras, e
  o `rollback()` do `except IntegrityError` fica com escopo de uma conta só. Um `commit` único no fim
  exigiria `SAVEPOINT` para conseguir o mesmo isolamento
- **O `SELECT` antes do `INSERT` é exatamente o que `cadastrar()` recusou na 1.5 — e aqui está
  certo.** Lá era endpoint concorrente, e a janela entre consulta e gravação virava `500` no caso que
  o `409` existia para cobrir. Aqui é script de uma execução, o `except IntegrityError` cobre a
  corrida improvável, e a consulta é o que permite distinguir "criada" de "mantida". Deixei esse
  porquê escrito no código: sem ele, parece contradição com a story anterior

A prova que mais me interessou não foi de teste automatizado. Rodei o seed contra o meu banco de
desenvolvimento, que já tinha quatro contas criadas por `/cadastro` durante as Stories 1.5 e 1.6:
as quatro continuaram lá, com o `criado_em` original — ou seja, não foram recriadas. Depois criei
mais uma no meio do caminho, rodei o seed de novo, e ela voltou do login com o mesmo `id`. É o
critério que o `pytest` verifica dentro de uma transação revertida, verificado uma vez onde ele
realmente importa.

As três decisões desta story — script idempotente em vez de migração de dados, idempotência por
consulta em vez de limpeza da tabela, e senha única publicada no README — estão no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo), cada uma com a alternativa que
descartei.

### Story 1.8 — backend e banco no ar na Railway

A primeira story em que **o entregável não está no repositório**: ele está numa conta de fornecedor.
Nenhuma linha de `app/`, `migrations/`, `seeds/` ou `tests/` mudou, e é a quarta seguida sem
`uv sync`. O que este README ganhou foi a seção [Deploy na Railway](#deploy-na-railway), que descreve
campo por campo o que eu configurei — porque configuração que só existe num painel some junto com o
serviço, e quem avalia precisa poder refazer.

O que me deixou confortável nesta story foi descobrir que **três decisões anteriores foram tomadas
exatamente para hoje, e as três pagaram**:

- O `/saude` da 1.1 não toca banco de propósito. Health check que consulta o Postgres derrubaria o
  deploy por indisponibilidade que não é dele
- A normalização de `postgres://` na `Settings`, escrita na 1.4, traduziu a URL que a Railway injeta.
  O comentário no código dizia "sem esta normalização, o erro na Story 1.8 seria um
  `ModuleNotFoundError` que não aponta para a URL como causa" — não precisei descobrir isso no dia
- O seed da 1.7 nunca apaga linha nenhuma. É ele que roda a cada deploy, e a decisão de idempotência
  por consulta em vez de limpeza deixou de ser hipótese e virou a garantia que segura o dado de quem
  estiver avaliando

A descoberta que custou pesquisa foi a do `uv`: o Railpack o instala só para construir e não o deixa
na imagem final. Os comandos que eu ia escrever usavam `uv run`, como no desenvolvimento local, e
teriam falhado com `uv: not found` — um erro que não sugere causa nenhuma para quem conhece o projeto
pelos comandos daqui. Está registrado em
[Por que os comandos não usam `uv run`](#por-que-os-comandos-não-usam-uv-run), que é o lugar em que
alguém vai procurar antes de "corrigir".

Dois tropeços reais, que deixei documentados porque vão acontecer com quem repetir:

- **O primeiro build falhou** porque o `Root Directory` fica escondido em Settings → Source, e sem
  ele a Railway constrói a raiz do monorepo. O log lista os arquivos da raiz e morre num
  `railpack process exited with an error` que não diz o que faltou
- **O deploy pegou a `main`** por ser a branch padrão do repositório — que ainda não tinha o backend.
  Duas causas empilhadas no mesmo build vermelho

As três decisões desta story — Railpack em vez de `Dockerfile`, migração no Pre-deploy em vez de
encadeada no start, e configuração no painel em vez de `railway.json` versionado — estão no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo), cada uma com a alternativa que
descartei.

### Story 1.9 — frontend no ar na Vercel

**O backend não teve uma linha alterada nesta story.** Nenhum arquivo de `app/`, `migrations/`,
`seeds/` ou `tests/` mudou, os 85 testes continuam valendo sem ajuste, e não houve `uv sync`. O que
mudou foi **uma variável no painel da Railway**: o `CORS_ORIGENS` passou a listar, ao lado do
`http://localhost:3000` de desenvolvimento, a origem do frontend publicado.

Registro isso aqui porque "nada mudou nesta camada, e este é o motivo" também é informação — e
porque a variável que mudou é justamente a que convida à conclusão errada.

**A decisão, e o que caiu.** A alternativa era **manter só o `localhost`**, e ela tem a verdade
técnica do lado dela: desde o proxy da Story 1.4 o navegador não fala com a Railway, então o
`CORS_ORIGENS` não participa de nada que exista hoje, e mexer nele custa um redeploy do backend por
um efeito observável nulo. Caiu por duas razões. A origem publicada estar na lista é o estado
correto do sistema — no dia em que qualquer coisa chamar a API direto, a resposta certa já está
configurada em vez de virar depuração. E o critério de aceite pede CORS e `SameSite` configurados
com todas as letras.

**O que eu fiz questão de não deixar o README sugerir:** que o CORS é o que faz o login funcionar
entre os dois fornecedores. Não é, e escrever isso apagaria a razão de o proxy existir. Está
explicado em [Por que essa variável não é o que faz o login
funcionar](#por-que-essa-variável-não-é-o-que-faz-o-login-funcionar), com o diagrama das duas setas
— nenhuma delas é uma requisição de navegador para outra origem.

A prova de que o backend estava pronto para este dia veio de fora: um `POST` em
`https://elite-dev-rock-hub.vercel.app/api/auth/login` responde `200` com as quatro contas semeadas,
e o `Set-Cookie` volta com `Secure` — que é o `AMBIENTE=producao` da Story 1.8 chegando até a
aplicação — e **sem atributo `Domain=`**, que é o que o mantém como cookie de host da origem do
frontend.

### Story 2.1 — cliente da Ticketmaster com a chave protegida

A primeira story da Epic 2, e a primeira em cinco que escreve código de aplicação — as Stories 1.5
a 1.9 foram tela, dependência e configuração. Esta abre pela ponta que ninguém vê: o backend passa a
falar com um serviço fora dele. Entrou uma peça só, `app/integrations/ticketmaster.py`, com
`app/schemas/catalogo.py` ao lado. **Nenhuma rota, nenhuma tela, nenhum banco** — `GET
/organizador/catalogo?q=` é da Story 2.2, e por isso esta story só é verificável por teste. Detalhes
completos de endpoint, limites e conversão estão em
[Catálogo da Ticketmaster](#catálogo-da-ticketmaster).

O achado técnico que não estava no `epics.md`: o `httpx` põe a URL completa da requisição na
mensagem de toda exceção que levanta, e a URL carrega `apikey=`. Um `logger.exception()` escrito por
reflexo — o jeito idiomático de logar exceção em Python — publicaria a chave no log da Railway,
furando o AD-2 pelo lado de dentro do próprio backend que ele existe para proteger. A correção foi
registrar só o tipo da exceção e o status HTTP, nunca a exceção inteira nem a URL.

`httpx` mudou de dependência de `dev` para dependência de runtime no `pyproject.toml`. Ele já estava
travado no `uv.lock` desde a Story 1.1 (puxado pelo `TestClient`), então o `uv sync` não trouxe
pacote novo nenhum — só moveu o vínculo. Isso importa porque o Railpack builda com `--no-dev`: um
`import httpx` em código de produção, com `httpx` só em `dev`, funcionaria em toda máquina de
desenvolvimento e estouraria `ModuleNotFoundError` só no primeiro deploy da `main` — o mesmo tipo de
defeito que o `.gitignore` sem âncora da Story 1.9 já tinha ensinado a temer.

A `Settings` ganhou um segundo `model_validator`, e de propósito **não** estendi o que já recusava o
`JWT_SECRET` de exemplo: são dois motivos diferentes de não subir em produção — segredo de exemplo
esquecido versus variável nunca definida —, e uma mensagem de erro fundida faria quem depura procurar
a causa errada.

Os testes desta story não tocam rede nem banco. A costura é `httpx.MockTransport`, não
`monkeypatch` em `httpx.get`: o transporte recebe a `httpx.Request` de verdade, construída pelo
código de produção, e é isso que torna verificável que a chave saiu em `apikey` — o teste lê
`request.url.params["apikey"]` em vez de acreditar. Um teste específico prova a ausência: dispara um
`401`, captura o log com `caplog`, e afirma que o valor da chave não aparece nem ali nem na
mensagem do `ErroDeDominio`.

Duas regressões apareceram ao ligar o segundo `model_validator`, e as duas tinham a mesma causa —
um teste que monta `Settings(ambiente="producao", jwt_secret=...)` sem saber que uma segunda
variável passaria a ser exigida: `test_jwt_secret_proprio_em_producao_nao_falha` em
`test_config.py`, prevista no planejamento da story, e
`test_cookie_e_secure_apenas_em_producao` em `test_auth.py`, que não estava. A segunda apareceu só
ao rodar a suíte inteira — reforça por que a Story 9 desta epic sempre roda `uv run pytest` sem
filtro antes de considerar qualquer story pronta, e não só os arquivos que a story tocou.

As quatro decisões desta story — `httpx` síncrono em vez de `AsyncClient` ou `urllib`, o endpoint
`/events.json` em vez de `/attractions.json`, chave ausente derrubando só a produção, e nenhuma rota
nesta story — estão no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo), cada uma
com a alternativa que descartei.

### Story 2.2 — buscar a atração no catálogo

A story que dá superfície ao que a 2.1 entregou: a integração existia, tinha 20 testes, e não era
observável por nenhum caminho — sem rota, sem tela, sem entrada no `/docs`. Entrou um router só,
`app/api/organizador.py`, com uma rota (`GET /organizador/catalogo`) e um corpo de uma linha.
**Nenhum dado é gravado** — a tabela `evento` é da Story 2.3.

A decisão mais visível para quem revisa código é a que **não** tomei: não criei
`app/services/catalogo.py`. Está registrada, com a alternativa descartada, em [O paradigma:
`routers → services → models`](#o-paradigma-routers--services--models) — é a única exceção ao
paradigma que existe no projeto até aqui, e ela é deliberada, não esquecimento.

`countryCode=BR` entrou na chamada da Discovery nesta story, não na 2.1, porque só fazia sentido
decidir isso quando existisse uma tela para mostrar o resultado. Sem ele a busca por "metallica"
volta cheia de shows americanos e a avaliação pareceria estar vendo um catálogo quebrado. É
limitação assumida, não bug: está em [O que não está pronto](../README.md#o-que-não-está-pronto) do
README da raiz.

Doze testes novos (onze em `test_organizador_catalogo.py`, um em `test_ticketmaster.py` para o
`countryCode`), a suíte foi de 107 para 119. Reaproveitei os dois helpers de teste da Epic 1 sem
alteração — `_instalar_transporte` (o `MockTransport` que substitui `_criar_cliente` do módulo da
integração, nunca o da rota) e `_entrar` (login de verdade contra o `TestClient`) — porque a rota
nova não inventa forma de testar nova, só combina as duas que já existiam.

**Revisão pós-review, no mesmo dia.** Testando a tela pela primeira vez, notei — e o Igor confirmou
que queria diferente — que uma busca vazia simplesmente não mostrava nada: era fiel ao AC3 original
("`q` ausente devolve `[]`, zero chamada à Ticketmaster"), mas o organizador abria a tela e via um
convite para digitar, sem noção nenhuma do que existe no catálogo. Reescrevi `buscar_eventos`: sem
termo, ela chama a Discovery do mesmo jeito, só que sem `keyword` e com `sort=date,asc` — os
próximos eventos do Brasil como exemplo do que dá para publicar, sem custar uma segunda forma de
buscar. Dois testes trocaram de forma (de "afirma que não chamou" para "afirma que chamou sem
`keyword`"), e um teste novo cobre a busca com termo continuando sem `sort`. **Suíte final desta
story: 121.**

**A alternativa que caiu:** uma fileira de termos sugeridos (chips clicáveis, tipo "Metallica ·
Baco Exu do Blues") que só disparariam a chamada de verdade ao clicar — preservaria a cota de quem
só abre a tela para olhar, mas exigiria manter uma lista própria de sugestões (fixa no código ou
vinda de algum outro lugar, o que é escopo novo) e não mostraria exemplo real nenhum antes do
clique. Perdeu para "mostrar de verdade o que existe", que é o que o Igor pediu.

O frontend desta story está documentado em [`frontend/README.md`](../frontend/README.md); as
decisões de produto (quem chama a integração, mecânica da busca, onde mora a tela, o filtro de
país, e a listagem sem termo) estão no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo),
cada uma com a alternativa que descartei.
