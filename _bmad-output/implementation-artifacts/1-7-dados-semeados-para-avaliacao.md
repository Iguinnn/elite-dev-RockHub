---
baseline_commit: "46230d4 — Story 1.6 (branch epic-1---fundacao-acesso-e-primeiro-deploy)"
---

# Story 1.7: Dados semeados para avaliação

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **A primeira story escrita para o avaliador, não para
o usuário.** As 1.4 a 1.6 fecharam o ciclo do acesso, mas só existe um caminho para criar conta —
`/cadastro` — e ele produz `CLIENTE` sempre, de propósito. Organizador e portaria hoje nascem de um
`uv run python -c` de dez linhas colado no README da raiz, que é exatamente o tipo de instrução que
alguém copia errado às onze da noite.

Esta story troca esse trecho por um comando: `uv run python -m seeds.semear`. Ele cria as quatro
contas do NFR2 — um organizador, **dois** clientes e uma portaria —, pode rodar quantas vezes for e
**nunca apaga nem sobrescreve nada** que já esteja no banco. Essa última parte não é zelo: a Story
1.8 vai chamar esse mesmo comando a cada deploy na Railway, e um seed que limpa a tabela antes de
inserir funcionaria hoje e destruiria o trabalho de quem estiver avaliando no primeiro redeploy.

## Story

Como avaliador,
quero contas prontas para os três papéis,
para percorrer o fluxo sem cadastrar nada.

## Acceptance Criteria

1. **Given** um banco migrado (`alembic upgrade head`)
   **When** eu rodo `uv run python -m seeds.semear` a partir de `backend/`
   **Then** existem no banco exatamente quatro contas: **um** `ORGANIZADOR`, **dois** `CLIENTE` e
   **um** `PORTARIA` — NFR2
   **And** o comando imprime uma linha por conta com papel, e-mail e situação, e termina com código
   de saída `0`

2. **Given** que o seed já rodou
   **When** eu rodo de novo
   **Then** ele não duplica conta nenhuma, não levanta exceção e termina em `0`
   **And** cada conta aparece como **mantida**, não como criada

3. **Given** um banco com contas que avaliadores criaram por `/cadastro`
   **When** o seed roda de novo — inclusive depois de um redeploy
   **Then** nenhuma linha da tabela `usuario` é apagada, atualizada ou sobrescrita
   **And** a idempotência vem de **"já existe esse e-mail? então não insere"** — não existe
   `DELETE`, `TRUNCATE`, `UPDATE` nem `drop` em lugar nenhum do seed

4. **Given** uma conta semeada que já existe no banco com `nome` e `senha_hash` diferentes dos do
   script
   **When** o seed roda
   **Then** o `nome` e o `senha_hash` gravados continuam **exatamente** como estavam — o script não
   "conserta" conta nenhuma

5. **Given** uma das credenciais publicadas no README
   **When** eu chamo `POST /auth/login` com ela
   **Then** entro com sucesso e o `papel` devolvido é o do README
   **And** o `senha_hash` gravado é Argon2id de verdade, gerado por `gerar_hash` — o mesmo caminho
   do cadastro, não uma string literal

6. **Given** o e-mail de uma conta semeada
   **When** eu o comparo com o que `EmailNormalizado` produziria
   **Then** ele já está em minúsculas e sem espaços — senão a conta gravada pelo seed não seria
   encontrada pelo `POST /auth/login`, que normaliza a entrada

7. **Given** um e-mail semeado que já existe no banco **com outro papel** — por exemplo, alguém
   cadastrou `organizador@rockhub.dev` por `/cadastro` e a conta nasceu `CLIENTE`
   **When** o seed roda
   **Then** ele **não** sobrescreve o papel (AC3 continua valendo)
   **And** avisa na saída que aquela conta existe com papel diferente do esperado — silêncio aqui
   viraria "o organizador não funciona" sem pista nenhuma
   **And** ainda assim termina em `0`: na Story 1.8 este comando roda antes do `uvicorn`, e sair
   diferente de zero impediria a aplicação de subir por causa de um aviso

8. **Given** o script do seed
   **When** eu o inspeciono
   **Then** ele mora em `backend/seeds/`, o lugar que a árvore da arquitetura reservou
   **And** a função que semeia **recebe** uma `Session` por parâmetro; só o `main()` abre a sessão
   de produção por `SessaoLocal` — é o que permite testá-la sem tocar no banco de desenvolvimento

9. **Given** a suíte do backend
   **When** eu a rodo
   **Then** os 73 testes anteriores continuam passando sem alteração de comportamento
   **And** nenhum teste novo chama `main()` — um `main()` dentro do `pytest` gravaria no banco de
   `DATABASE_URL`, que é o de desenvolvimento

10. **Given** os três READMEs
    **When** eu os leio
    **Then** as quatro credenciais estão numa tabela no README da raiz, com o comando que as cria
    **And** o `uv run python -c` improvisado que criava organizador à mão **saiu** do README
    **And** está escrito que o evento publicado do NFR2 ainda não é semeado, e por quê

> **De onde vem cada critério.** Os ACs **1, 2 e 3** são os três do `epics.md`, com o comando exato,
> a contagem por papel e a proibição explícita de `DELETE`/`TRUNCATE` — que o próprio `epics.md` já
> escreve como "nunca de limpar a tabela antes de inserir".
>
> **AC4 e AC7** são as duas metades que "não sobrescreve" esconde. A primeira é o caso benigno
> (alguém trocou a senha da conta semeada); a segunda é o caso que engana (o e-mail existe, mas com
> o papel errado, e o organizador simplesmente não funciona). Sem o AC7 o script seria honesto e
> mudo ao mesmo tempo.
>
> **AC5 e AC6** existem porque um seed que grava conta que não loga é pior do que seed nenhum: a
> falha aparece no primeiro passo do roteiro de avaliação. O AC6 é o detalhe barato de errar —
> `Organizador@RockHub.dev` no script gravaria maiúscula no banco, e o login normaliza para
> minúscula antes de consultar.
>
> **AC8** é `ARCHITECTURE-SPINE.md#Árvore` (`seeds/  # dados de teste exigidos pelo desafio`) mais a
> lição que a fixture da Story 1.3 já tinha aprendido: o que decide qual banco é tocado precisa ser
> parâmetro, não import.
>
> **AC9** protege os 73 testes que já existem. **AC10** é a NFR8 e a regra do `CLAUDE.md`.

## Tasks / Subtasks

- [x] **T1. `backend/seeds/__init__.py` e `backend/seeds/semear.py` — o script** (AC: 1, 3, 5, 6, 8)
  - [x] `seeds/` é pasta **nova**, irmã de `app/`, `migrations/` e `tests/` — é o que a árvore da
        arquitetura reservou. **Não** ponha isto dentro de `app/`: seed não é código de aplicação e
        não deve subir com o `uvicorn`
  - [x] `__init__.py` vazio, como o de `app/` e o de `tests/`
  - [x] `ContaSemeada` como `@dataclass(frozen=True)` com `nome`, `email`, `senha`, `papel`
  - [x] A tupla `CONTAS` com as quatro contas da tabela em *As quatro contas*, nessa ordem
  - [x] `SENHA_DE_AVALIACAO = "rockhub123"` — uma constante só, as quatro contas a compartilham
  - [x] `semear_conta(sessao, conta) -> str` e `semear(sessao) -> list[tuple[ContaSemeada, str]]`.
        O código completo está em *O script, escrito*
  - [x] **O hash sai de `gerar_hash`**, nunca de uma string colada (AC5). Importe de
        `app.core.seguranca` — não reimplemente Argon2 aqui
  - [x] **O papel gravado é `conta.papel.value`**, `str`, como em `cadastrar()` e na fábrica de
        teste. A coluna é `String(20)` com `CHECK`
  - [x] ⚠️ **Nenhum `delete`, `truncate`, `drop` ou `update`.** É o AC3 e é o motivo de esta story
        existir do jeito que existe
  - [x] Imports do arquivo: `from dataclasses import dataclass`, `from sqlalchemy import select`,
        `from sqlalchemy.exc import IntegrityError`, `from sqlalchemy.orm import Session`,
        `from app.core.db import SessaoLocal`, `from app.core.seguranca import gerar_hash`,
        `from app.models.usuario import PapelUsuario, Usuario`. **Nada além disso**
  - [x] Docstring do módulo explicando o comando e a armadilha do `-m` (T2)

- [x] **T2. `main()` e o ponto de entrada** (AC: 1, 2, 7, 8)
  - [x] `main()` abre `with SessaoLocal() as sessao:`, chama `semear(sessao)` e imprime o relatório.
        **É o único lugar do arquivo que toca `SessaoLocal`** — a função `semear` recebe a sessão
  - [x] `if __name__ == "__main__": main()` no fim
  - [x] **Não imprima a senha.** Ela está no README; jogá-la no stdout a põe também no log de deploy
        da Railway, sem ganho nenhum. A última linha do relatório aponta para o README
  - [x] Quando alguma conta voltar `papel-divergente`, imprima o aviso do AC7 — e **continue saindo
        em `0`**. Nenhum `sys.exit(1)`
  - [x] O comando é `uv run python -m seeds.semear`, rodado de `backend/`.
        ⚠️ **`uv run seeds/semear.py` não funciona**: executar o arquivo direto põe `backend/seeds/`
        no `sys.path` em vez de `backend/`, e `import app.core.db` deixa de resolver. Escreva isso
        no docstring e no README — é o primeiro erro que alguém vai cometer
  - [x] O `.env` é lido pela `Settings` a partir do diretório corrente: o comando só funciona
        rodado de `backend/`. Também vai no README

- [x] **T3. `backend/tests/test_seed.py` — os testes** (AC: 1 a 7, 9)
  - [x] Arquivo **novo**. Usa a fixture `sessao` do `conftest.py` (banco `rockhub_teste`, transação
        revertida no teardown) e a `fabricar_usuario` que a Story 1.6 criou
  - [x] ⚠️ **Nenhum teste chama `main()`.** `main()` abre `SessaoLocal`, que aponta para
        `DATABASE_URL` — o banco de **desenvolvimento**. Um teste que o chamasse gravaria quatro
        contas fora do banco de teste e ninguém veria. É o AC9, e é a mesma trava que a Story 1.3
        pôs na configuração do Alembic
  - [x] `import seeds.semear` funciona sob o `pytest` por causa de `pythonpath = ["."]` no
        `pyproject.toml`, com rootdir em `backend/`. Não acrescente `sys.path` a nada
  - [x] A lista do que cada teste prova está em *Testing*

- [x] **T4. `backend/README.md`** (AC: 10)
  - [x] Seção nova **Dados semeados**, depois de *Banco de dados*: o comando, a tabela das quatro
        contas, a regra de idempotência, a armadilha do `-m` e a razão de a senha não ser impressa
  - [x] Árvore em *Estrutura*: acrescente `seeds/` com `semear.py`, entre `migrations/` e `tests/`
  - [x] *Testes*: atualize a contagem (73 → o total novo) e cite o que `test_seed.py` cobre
  - [x] *Banco de dados*: a frase "a Story 1.7 semeia por ele" já está lá e passa a valer no
        presente — ajuste o tempo verbal
  - [x] Entrada **Story 1.7** no *Histórico desta camada*, em primeira pessoa

- [x] **T5. `README.md` da raiz** (AC: 10)
  - [x] *Como executar → Backend*: acrescente `uv run python -m seeds.semear` logo depois do
        `alembic upgrade head`, com o comentário do que ele cria
  - [x] *Contas semeadas*: **substitua** o texto atual inteiro. Sai o "Ainda não existem" e sai o
        `uv run python -c "..."` de dez linhas; entra a tabela das quatro contas e o comando. Mantenha
        a frase de que conta criada por `/cadastro` nasce `CLIENTE`
  - [x] *Roteiro de avaliação*: o roteiro passa a começar pelas contas semeadas — entrar como
        `organizador@rockhub.dev` e ver `ORGANIZADOR` na `/conta`; entrar como um dos clientes.
        Diga para que serve o **segundo** cliente: provar, na Epic 4, que ingresso de um não aparece
        na conta do outro
  - [x] *Decisões*: **três** entradas novas, cada uma com o que caiu e por quê — script idempotente
        em vez de migração de dados; idempotência por consulta em vez de limpar a tabela; senha única
        publicada no README. Matéria-prima em *Decisões que o Igor tomou* e nas Dev Notes
  - [x] *O que não está pronto*: acrescente a linha do **evento publicado do NFR2**, com o motivo —
        `Evento` e `Setor` só nascem na Story 2.3. E ajuste a linha *Cadastro de organizador pela
        interface*, que hoje diz "até a Story 1.7, organizador nasce pelo script em Contas semeadas"
  - [x] **Primeira pessoa, como o Igor escrevendo**

- [x] **T6. `frontend/README.md`** (AC: 10)
  - [x] Uma entrada curta no histórico: a Story 1.7 **não tocou no frontend**, e as contas para
        entrar em `/login` estão no README da raiz. Não invente mudança que não houve — a regra do
        `CLAUDE.md` é que os três READMEs sejam atualizados, e "nada mudou aqui, e é por isto" é
        uma atualização honesta

- [x] **T7. Verificação** (AC: todos)
  - [x] `docker compose up -d` no ar e `uv run alembic upgrade head` aplicado
  - [x] `uv run python -m seeds.semear` → quatro linhas `criada`, saída `0`
  - [x] Rodar **de novo** → quatro linhas `mantida`, saída `0`, e `SELECT count(*) FROM usuario`
        não mudou
  - [x] Criar uma conta por `http://localhost:3000/cadastro`, rodar o seed de novo, conferir que ela
        continua lá e continua logando — feita por `POST /auth/cadastro` (mesmo caminho de código
        que a tela usa; o frontend só faz proxy). A conferência **pela tela** ficou para o Igor
  - [x] `POST /auth/login` com **cada uma** das quatro credenciais → `200`, com o `papel` do README.
        Pelo `/docs` ou por `curl`
  - [x] Entrar como `organizador@rockhub.dev` no navegador e conferir `ORGANIZADOR` na `/conta` —
        provado por HTTP (`GET /auth/eu` devolve `ORGANIZADOR` e "Helena Marques", que é exatamente
        o que a `/conta` renderiza). **A conferência visual no navegador fica para o Igor**
  - [x] `uv run pytest` — 73 anteriores + os novos, todos verdes. Contorno nesta máquina:
        `uv run python -m pytest`
  - [x] Busca em `backend/seeds/` por `delete`, `DELETE`, `truncate`, `TRUNCATE`, `drop` e `update`
        → zero ocorrências
  - [x] `SELECT email FROM usuario WHERE email <> lower(email)` → zero linhas
  - [x] ⚠️ `uv run seeds/semear.py` (sem o `-m`) → falha com `ModuleNotFoundError: app`. **Isto é o
        esperado**, e é o que a nota do README existe para evitar. Não "conserte" com `sys.path`

- [x] **T8. Documentação** — coberta por T4, T5 e T6 (obrigatório — regra do projeto)

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T5).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Identidade das contas | **Nome de pessoa + e-mail que diz o papel**, senha única | *Tudo genérico pelo papel* ("Organizador RockHub"): mais óbvio de ler, mas a `/conta` e as telas da Epic 2 exibem esse nome em **serifada**, que o UX-DR2 reserva a nome próprio — "Organizador RockHub" em Georgia é exatamente a cara de dado de mentira que o desafio penaliza |
| Como o seed roda | **Script em `backend/seeds/`, chamado à mão** | *Migração Alembic de dados*: zero passo a mais e o deploy semearia sozinho, mas mistura dado com schema, nunca mais roda (conta apagada não volta) e `downgrade base` levaria as contas junto. *Semear no startup do FastAPI*: dispensaria comando de release na Railway, ao custo de semear a cada `--reload` e de atar o seed ao ciclo de vida da aplicação |
| O evento publicado do NFR2 | **Fica para a Epic 2; a dívida vai escrita no README agora** | *O avaliador publica pela interface*: mostraria o fluxo do organizador funcionando, mas trava o roteiro no passo 1 se a Ticketmaster estiver fora do ar naquele minuto. *Semear evento junto*: impossível hoje — `Evento` e `Setor` só existem a partir da Story 2.3 |

**Duas suposições declaradas, não decisões suas** — uma linha para trocar se discordar:

- **A senha é `rockhub123`**, a mesma para as quatro contas. Passa no `min_length=6` do
  `CadastroEntrada`, o que mantém a coerência com o que a interface aceita
- **O domínio é `rockhub.dev`.** Não é registrado por ninguém deste projeto e não recebe e-mail —
  o que é irrelevante, porque não existe envio de e-mail em lugar nenhum do sistema

### As quatro contas

| Papel | Nome | E-mail | Senha |
|---|---|---|---|
| `ORGANIZADOR` | Helena Marques | `organizador@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Bruno Tavares | `cliente@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Marina Aoki | `cliente2@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Jonas Ribeiro | `portaria@rockhub.dev` | `rockhub123` |

**Dois clientes é NFR2 literal, e tem uso.** O segundo existe para provar, na Epic 4, que o ingresso
de um não aparece na conta do outro — e, na Epic 3, que duas pessoas disputando o último ingresso do
setor produzem uma venda e uma recusa. Um cliente só deixaria as duas garantias sem como demonstrar.

Esta tabela é copiada literalmente para o README da raiz (T5).

### O script, escrito

`backend/seeds/semear.py`:

```python
@dataclass(frozen=True)
class ContaSemeada:
    nome: str
    email: str
    senha: str
    papel: PapelUsuario


SENHA_DE_AVALIACAO = "rockhub123"

CONTAS: tuple[ContaSemeada, ...] = (
    ContaSemeada("Helena Marques", "organizador@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.ORGANIZADOR),
    ContaSemeada("Bruno Tavares", "cliente@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.CLIENTE),
    ContaSemeada("Marina Aoki", "cliente2@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.CLIENTE),
    ContaSemeada("Jonas Ribeiro", "portaria@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.PORTARIA),
)

CRIADA = "criada"
MANTIDA = "mantida"
PAPEL_DIVERGENTE = "papel-divergente"


def semear_conta(sessao: Session, conta: ContaSemeada) -> str:
    """Cria a conta se o e-mail ainda não existir. Nunca atualiza o que existe."""
    existente = sessao.scalar(select(Usuario).where(Usuario.email == conta.email))
    if existente is not None:
        # Nada é escrito aqui — nem nome, nem senha, nem papel. Este `return`
        # é o AC3 inteiro.
        return MANTIDA if existente.papel == conta.papel.value else PAPEL_DIVERGENTE

    sessao.add(
        Usuario(
            nome=conta.nome,
            email=conta.email,
            senha_hash=gerar_hash(conta.senha),
            papel=conta.papel.value,
        )
    )
    try:
        sessao.commit()
    except IntegrityError:
        # Duas execuções ao mesmo tempo: o UNIQUE da Story 1.3 decide, e a
        # segunda entende que a conta já está lá. Sem o rollback a Session fica
        # inválida e a conta seguinte falharia por tabela.
        sessao.rollback()
        return MANTIDA

    return CRIADA


def semear(sessao: Session) -> list[tuple[ContaSemeada, str]]:
    return [(conta, semear_conta(sessao, conta)) for conta in CONTAS]
```

Cinco detalhes que decidem se isto funciona:

- **`semear` recebe a `Session`; só `main()` abre a de produção.** É o que permite ao teste rodar o
  seed dentro da transação revertida do `conftest.py`. Se `semear` abrisse `SessaoLocal` por conta
  própria, todo teste do arquivo gravaria no banco de desenvolvimento — a mesma armadilha que a
  Story 1.3 fechou definindo a URL do Alembic em código
- **`commit` por conta, não um no fim.** Uma falha na terceira não desfaz as duas primeiras, e o
  `rollback()` do `except` fica com escopo de uma conta só. Um `commit` único no fim obrigaria a
  `SAVEPOINT` para conseguir o mesmo isolamento
- **Existência é consultada com `select(...).where(email == ...)`, não `Session.get`.** `get` é por
  chave primária, e a chave aqui é o `id` (UUID), que o seed não conhece. O e-mail é `unique`, então
  a consulta devolve zero ou uma linha
- **O `SELECT` antes do `INSERT` é a mesma coisa que `cadastrar()` recusou — e aqui está certo.**
  Lá era endpoint concorrente, e a janela entre consulta e gravação virava `500` no caso que o `409`
  existia para cobrir. Aqui é script de uma execução, o `except IntegrityError` cobre a corrida
  improvável, e o `SELECT` é o que permite distinguir "criada" de "mantida" — que é a informação que
  o AC2 pede na saída. **Escreva esse porquê no código**, senão parece contradição com a 1.5
- **`papel=conta.papel.value`**, `str`, nunca o membro do enum. A coluna é `String(20)` com `CHECK`,
  e é a convenção que a 1.3 fixou e a 1.6 repetiu

### O relatório impresso

```
$ uv run python -m seeds.semear
ORGANIZADOR  organizador@rockhub.dev   criada
CLIENTE      cliente@rockhub.dev       criada
CLIENTE      cliente2@rockhub.dev      criada
PORTARIA     portaria@rockhub.dev      criada
As senhas estão no README da raiz, em "Contas semeadas".
```

Na segunda execução as quatro dizem `mantida`. Quando um e-mail existe com papel diferente:

```
ORGANIZADOR  organizador@rockhub.dev   já existe com papel CLIENTE — não foi alterada
```

**Por que a senha não é impressa.** Ela está publicada num README público, então não é segredo — mas
o mesmo comando roda no deploy da Railway (Story 1.8), e o que ele imprime vai para o log de deploy.
Pôr credencial em log é hábito que se leva junto para o dia em que a credencial importa. E não há
ganho: quem rodou o comando tem o README aberto.

**Por que o código de saída é `0` mesmo com aviso.** Na Story 1.8 o comando entra na sequência
`alembic upgrade head` → `seeds.semear` → `uvicorn`. Um `exit(1)` por causa de um papel divergente
derrubaria o deploy inteiro por um aviso — e o único jeito de subir de novo seria mexer no banco de
produção às pressas. Falha de verdade (banco fora do ar, migração não aplicada) continua estourando
exceção e saindo diferente de zero, que é o comportamento certo: aí a aplicação **não** deve subir.

### O que já existe e esta story reusa — não reescreva nada disto

| O que | Onde | Como usar |
|---|---|---|
| `gerar_hash(senha)` | `app/core/seguranca.py` | é o Argon2id do projeto. **Não** instancie `PasswordHasher` no seed |
| `PapelUsuario` / `Usuario` | `app/models/usuario.py` | enum único do projeto; o docstring de lá proíbe redeclarar |
| `SessaoLocal` | `app/core/db.py` | só no `main()` |
| fixture `sessao` | `tests/conftest.py` | transação revertida; é onde os testes do seed rodam |
| fixture `fabricar_usuario` | `tests/conftest.py` | criada na 1.6; serve para plantar a conta "de avaliador" dos AC3/AC4/AC7 |
| `autenticacao.autenticar` | `app/services/autenticacao.py` | é como o AC5 se prova sem subir HTTP |
| `EmailNormalizado` | `app/schemas/auth.py` | o AC6 compara contra o que ele produz |

**Não devem ser tocados, e não devem quebrar:** `app/` **inteiro** — esta story não acrescenta,
remove nem altera uma linha de `app/`. Nem `models/usuario.py` (**nenhuma coluna muda, nenhuma
migração nesta story**), nem `core/db.py`, nem `core/config.py` (**nenhuma variável de ambiente
nova**), nem `api/auth.py`, nem `main.py`. Também não mudam `migrations/`, `pyproject.toml`,
`uv.lock` (**nenhuma dependência nova**), `.env.example`, `docker-compose.yml` e o `frontend/`
inteiro. Os arquivos existentes que mudam são três, e só de teste e documentação:
`backend/README.md`, `README.md` da raiz e `frontend/README.md`.

Se algum arquivo de `app/` precisar mudar para o seed funcionar, algo foi feito errado.

### Armadilhas específicas desta story

Em ordem de probabilidade:

1. **Rodar sem o `-m`.** `uv run seeds/semear.py` põe `backend/seeds/` no `sys.path` em vez de
   `backend/`, e `import app.core.db` estoura `ModuleNotFoundError`. A correção é o `-m`, **nunca**
   um `sys.path.append` no topo do script
2. **Chamar `main()` de dentro de um teste.** Grava as quatro contas no banco de **desenvolvimento**,
   passa verde, e ninguém percebe até alguém estranhar contas duplicadas em `rockhub`
3. **Esquecer o `rollback()` no `except IntegrityError`.** A `Session` fica em estado inválido e a
   conta seguinte falha com `PendingRollbackError`, que aponta para longe da causa. A Story 1.5
   gastou um comentário inteiro nisso, no `cadastrar()`
4. **Semear com e-mail em maiúscula.** `POST /auth/login` normaliza a entrada para minúsculas antes
   de consultar; a conta gravada com maiúscula existe e não loga nunca (AC6)
5. **"Atualizar" a conta que já existe** para deixá-la igual ao script. Parece zelo e é o AC3 sendo
   violado: em produção isso troca a senha de alguém que estava avaliando
6. **Escrever o `senha_hash` como string literal** copiada de outro lugar. O hash Argon2id carrega
   os parâmetros no próprio texto; um hash colado de outra máquina pode não verificar, e o AC5
   quebra só na hora do login
7. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** `uv run pytest` falha
   com `os error 4551`; o contorno é `uv run python -m pytest`. Documentado desde a Story 1.1 —
   note que o próprio comando do seed já é `python -m`, então ele não sofre disso
8. **`uv run pytest` exige o Compose no ar** desde a Story 1.3
9. **O `.env` é lido do diretório corrente.** Rodar o seed da raiz do repositório pega a `Settings`
   com os padrões, não com o seu `.env` — o que hoje dá no mesmo, mas na Railway não daria

### Convenções que esta story confirma ou cria

- **Seed é script idempotente, nunca migração de dados e nunca limpeza.** Vale para o evento e os
  setores que a Epic 2 vai acrescentar ao mesmo `seeds/`
- **Idempotência é "consulta, e não insere se já existe"** — a chave é o campo `unique` natural
  (aqui, o e-mail)
- **Script que grava recebe a `Session` por parâmetro; só o `__main__` escolhe o banco.** É a mesma
  regra que a 1.3 aplicou ao Alembic dos testes
- **Dado de avaliação é público e vai no README; segredo continua fora do repositório.** As senhas
  semeadas estão no README de propósito; `JWT_SECRET` e `TICKETMASTER_API_KEY` continuam só no
  ambiente (AD-2)
- **Credencial não vai para stdout**, mesmo quando não é segredo

### Estrutura alvo ao fim desta story

```text
backend/
  seeds/
    __init__.py               # NOVO — vazio
    semear.py                 # NOVO — CONTAS, semear(sessao), main()
  tests/
    test_seed.py              # NOVO — idempotência, não sobrescrita, login com a senha semeada
  README.md                   # +Dados semeados, árvore, contagem de testes, histórico
README.md                     # Contas semeadas reescrita, roteiro, 3 decisões, o que não está pronto
frontend/README.md            # nota curta: esta story não tocou aqui
```

`app/` não aparece nesta lista, e isso é a característica mais forte da story: ela não muda a
aplicação. `app/integrations/` continua não existindo — Story 2.1.

[Fonte: ARCHITECTURE-SPINE.md#Árvore — `seeds/  # dados de teste exigidos pelo desafio`]

### Comandos que esta story precisa deixar funcionando

```bash
# da raiz
docker compose up -d

cd backend
uv run alembic upgrade head
uv run python -m seeds.semear           # cria as quatro contas; rodar de novo é seguro
uv run pytest                           # contorno nesta máquina: uv run python -m pytest
```

Nada de `uv sync` nem de `npm install` — esta story não acrescenta dependência nenhuma. É a terceira
seguida em que isso acontece.

### Escopo — o que NÃO fazer aqui

Deploy e variáveis em produção (**Stories 1.8 e 1.9**) · evento, setor e qualquer dado de programação
(**Epic 2 em diante**) · rota ou tela de administração de usuários (**nenhuma story**) · cadastro de
organizador pela interface (**adiado, com o motivo já no README da raiz**) · alterar `app/`.

Quatro tentações concretas desta story:

- **"Já que estou semeando, crio um evento de exemplo."** As tabelas não existem. Qualquer coisa
  nessa direção seria migração nova, modelo novo e escopo da Story 2.3 antecipado
- **"Faço um `--forcar` que recria tudo."** É o `TRUNCATE` com outro nome, e é exatamente o que o
  AC3 proíbe. Quem quiser banco limpo tem `docker compose down -v`, já documentado
- **"Ponho o seed no `alembic upgrade head` para não precisar do segundo comando."** É a alternativa
  que você descartou hoje, com o motivo escrito
- **"Deixo o seed configurável por variável de ambiente"** (`SEED_SENHA`, `SEED_EMAIL_ORGANIZADOR`).
  As credenciais precisam bater com o README; variável de ambiente é justamente o jeito de elas
  divergirem sem ninguém notar

### Testing

Precisa do Compose no ar. Todos os testes novos usam banco.

**`tests/test_seed.py`**

| O que prova | AC |
|---|---|
| Uma execução cria quatro contas: um `ORGANIZADOR`, dois `CLIENTE`, um `PORTARIA` | 1 |
| As quatro voltam com situação `criada` na primeira execução | 1 |
| Segunda execução não muda a contagem de linhas em `usuario` e devolve `mantida` nas quatro | 2 |
| Segunda execução não levanta exceção | 2 |
| Conta pré-existente com o **mesmo e-mail** e nome/`senha_hash` diferentes sai do seed com nome e `senha_hash` **idênticos** aos de antes | 3, 4 |
| Uma conta de "avaliador" plantada com `fabricar_usuario` continua no banco depois do seed | 3 |
| `autenticacao.autenticar(sessao, email, SENHA_DE_AVALIACAO)` devolve o usuário para cada uma das quatro contas — o hash é Argon2id de verdade | 5 |
| Todo `email` de `CONTAS` é igual ao seu `lower().strip()` | 6 |
| E-mail semeado plantado antes com **outro papel** volta `papel-divergente`, e o papel no banco não muda | 7 |

Dois cuidados ao escrever:

- **`semear(sessao)` sempre, `main()` nunca.** Repetido aqui porque é a única forma de este arquivo
  sujar o banco de desenvolvimento
- A contagem de contas usa `select(func.count()).select_from(Usuario)` ou
  `len(sessao.scalars(select(Usuario)).all())` — a fixture reverte tudo no teardown, então a tabela
  começa vazia em cada teste, e a contagem é absoluta, não relativa

**Os 73 testes atuais continuam passando sem alteração.** Nenhum arquivo de `app/` muda e nenhuma
fixture existente é tocada — se algum quebrar, o seed encostou onde não devia.

### Inteligência das stories anteriores

**Da 1.6 (a story imediatamente anterior — leia estas antes de tudo):**

- **A fixture `cliente` e a fábrica `fabricar_usuario` moram no `conftest.py`** desde aquela story, e
  é de lá que os testes desta pegam a segunda
- **`app/core/dependencias.py` existe e nada aqui o toca** — o seed não passa por HTTP
- **Duas conferências visuais ficaram pendentes para você** (`Tab` com contorno âmbar e 375px na
  `/conta`). Continuam pendentes; não são desta story
- **`backend/seeds/` foi explicitamente listado como "continua não existindo — Story 1.7"** na
  estrutura alvo daquela story. É esta

**Da 1.5 (cadastro):**

- **`cadastrar()` recusou o `SELECT` antes do `INSERT`, e o motivo era concorrência de endpoint.**
  O seed faz o contrário, e a justificativa está em *O script, escrito*. Sem escrever o porquê, isto
  parece incoerência
- **`sessao.rollback()` é obrigatório depois de `IntegrityError`**, senão a próxima operação
  levanta `PendingRollbackError`
- **O papel nunca vem do corpo da requisição** — `cadastrar()` fixa `CLIENTE` literal. O seed é
  justamente o outro caminho, o que fica fora do alcance de quem chama a API

**Da 1.3 (banco):**

- **`papel` é `String(20)` com `CHECK`**; papel fora dos três valores levanta `IntegrityError`
- **`email` é `unique`**, e é essa restrição que sustenta a idempotência desta story
- **A fixture de banco nunca aponta para o banco de desenvolvimento**, e a URL do Alembic é definida
  em código. Mesmo princípio do AC8

**Da 1.1 (backend):**

- **Nenhum segredo versionado**, e o `.env.example` é o que fica no repositório. As senhas semeadas
  não são exceção a isso: são dado de avaliação publicado de propósito, não credencial de produção

**Do estado do repositório:** branch `epic-1---fundacao-acesso-e-primeiro-deploy`, com a Story 1.6
commitada (`46230d4`). As Stories 1.1 a 1.6 estão em `review` — o code review é ao fim da epic, não
a cada story. 73 testes passando no backend.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-6-*.md]

### Stack desta story

**Nenhuma versão nova para conferir: esta story não acrescenta dependência.** Tudo que ela usa já
está no lockfile.

| O que ela usa | Versão | Para quê |
|---|---|---|
| SQLAlchemy | 2.0.51 | `select`, `Session.commit/rollback`, `IntegrityError` |
| argon2-cffi | 25.1.0 | por trás de `gerar_hash`; o seed não a importa direto |
| pytest | ≥ 8.4 | fixtures `sessao` e `fabricar_usuario` |

Nenhuma biblioteca de seed, nenhum `faker`, nenhum `typer`/`click`. Quatro contas fixas não são
dados falsos gerados — são contrato com o README, e precisam ser **as mesmas** toda vez. Um gerador
de dados aleatórios aqui produziria credencial que o README não conhece, que é o pior desfecho
possível para esta story.

[Fonte: ARCHITECTURE-SPINE.md#Stack, #Árvore, #Adiado]

### Project Structure Notes

Esta é a primeira story do projeto que **não toca `app/`**, e a segunda inteiramente de backend
(depois da 1.3). O risco não está na complexidade — o script tem trinta linhas — e sim no que ele
faz com dado que já existe: é a primeira coisa deste repositório escrita para rodar **contra o banco
de produção**, repetidamente, sem supervisão.

Por isso a maior parte dos ACs é sobre o que o seed **não** faz. A ordem sugerida acompanha isso:
T1 → T2 → T3 (script e testes fechados, com o `mantida` provado antes de qualquer README) →
conferência manual da T7 → T4 → T5 → T6.

Não crie migração: nenhuma coluna muda. `seeds/` é pasta nova na raiz de `backend/`, irmã de `app/`
— não subpasta de `app/`, não `scripts/`, não `tools/`. A árvore da arquitetura já a nomeou.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.7] — os três ACs originais, incluindo a
  proibição literal de limpar a tabela antes de inserir
- [Source: _bmad-output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR2 (um
  organizador, **dois** clientes, uma portaria, e um evento publicado) e NFR8 (READMEs)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.8] — quem consome o comando desta story
  no deploy: `alembic upgrade head` antes da aplicação atender, e o seed sem apagar o que existe
- [Source: ARCHITECTURE-SPINE.md#Árvore] — `seeds/  # dados de teste exigidos pelo desafio`
- [Source: ARCHITECTURE-SPINE.md#Adiado] — "organizador e portaria vêm do seed, que é como o próprio
  enunciado os pede"; e o cadastro de organizador pela interface, adiado
- [Source: ARCHITECTURE-SPINE.md#AD-2] — segredo só no ambiente do backend; é o contraste que
  justifica publicar as senhas semeadas no README
- [Source: ARCHITECTURE-SPINE.md#AD-15] — Argon2id para senha
- [Source: _bmad-output/implementation-artifacts/1-6-cada-papel-so-acessa-o-que-lhe-cabe.md] —
  `fabricar_usuario`, e a nota de que `backend/seeds/` era desta story
- [Source: _bmad-output/implementation-artifacts/1-5-cadastro-de-cliente.md] — por que `cadastrar()`
  recusou o `SELECT` antes do `INSERT`, e o `rollback` obrigatório
- [Source: backend/app/models/usuario.py] · [core/seguranca.py] · [core/db.py] ·
  [services/autenticacao.py] · [schemas/auth.py] · [tests/conftest.py]
- [Source: backend/pyproject.toml] — `pythonpath = ["."]`, que é o que faz `import seeds.semear`
  resolver sob o pytest
- [Source: README.md#Contas semeadas] — o texto provisório que esta story substitui
- [Source: README.md#O que não está pronto] — a linha do cadastro de organizador, que cita "até a
  Story 1.7"
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Confirme com o Igor antes de `docker compose up`**, se ele não estiver acompanhando. Não há
   `uv sync` nem `npm install` nesta story
3. **Atualize os três READMEs antes de dar a story por concluída.** As três entradas de decisão da
   T5 são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As três desta story já estão respondidas. Se aparecer uma
   quarta — outro domínio de e-mail, senha por conta, um quinto usuário — pergunte em vez de escolher
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (1M) — `claude-opus-5[1m]`

### Debug Log References

- `uv run python -m pytest tests/test_seed.py` — 12 testes novos, verdes
- `uv run python -m pytest` — **85 testes** (73 anteriores + 12), verdes
- `uv run python -m seeds.semear` — 1ª execução: quatro `criada`, exit `0`; 2ª: quatro `mantida`,
  exit `0`
- `uv run seeds/semear.py` (sem `-m`) — `ModuleNotFoundError: No module named 'app'`, exit `1`.
  **Esperado**, e é a armadilha documentada no docstring e nos dois READMEs
- `SELECT papel, count(*) FROM usuario GROUP BY papel` no banco de desenvolvimento, depois do seed —
  1 `ORGANIZADOR`, 6 `CLIENTE` (2 semeados + 4 que já existiam de `/cadastro`), 1 `PORTARIA`
- `SELECT email FROM usuario WHERE email <> lower(email)` — zero linhas
- `POST /auth/login` + `GET /auth/eu` com as quatro credenciais — `200` nas quatro, com o papel e o
  nome da tabela do README

### Completion Notes List

- **O script tem 30 linhas de código e ~60 de comentário, e a proporção é intencional.** O que
  precisa sobreviver a esta story não é o algoritmo — é o motivo de ele não apagar nada, e o motivo
  de o `SELECT` antes do `INSERT` estar certo aqui e errado no `cadastrar()` da 1.5. Sem isso escrito
  no código, a próxima pessoa "corrige" a incoerência aparente
- **`_linha_do_relatorio` faz uma consulta extra só no caso `papel-divergente`**, para o aviso poder
  dizer qual papel está gravado ("já existe com papel CLIENTE — não foi alterada"), como o exemplo
  da story. É apresentação, então mora ao lado do `main()`, não dentro de `semear_conta`, que
  continua devolvendo `str` como a assinatura da story pede
- **AC3 foi provado duas vezes, e a segunda é a que vale.** Além do teste em transação revertida,
  rodei o seed contra o banco de desenvolvimento, que já tinha quatro contas criadas por `/cadastro`
  nas Stories 1.5/1.6: todas continuaram lá com o `criado_em` original. Depois criei mais uma,
  rodei o seed de novo, e ela voltou do login com o mesmo `id`
- **Sobra no banco de desenvolvimento do Igor:** a conta `avaliador.story17@exemplo.com` (papel
  `CLIENTE`), criada para essa verificação. Deixei-a de propósito em vez de apagar — o seed desta
  story não apaga linha nenhuma, e não me pareceu certo eu apagar. Sai com `docker compose down -v`
  quando você quiser o banco do zero
- **Uma falha intermitente pré-existente, fora do escopo desta story:**
  `tests/test_seguranca.py::test_token_com_assinatura_alterada_e_recusado` (Story 1.4) falha em
  ~6% das execuções, com ou sem esta story aplicada. A causa é o último caractere do JWT: a
  assinatura HS256 tem 32 bytes, que em `base64url` ocupam 43 caracteres — e o 43º carrega só 4 bits
  úteis, com 2 de preenchimento. Trocá-lo por `"A"` **não muda a assinatura decodificada** quando ele
  já é `A`, `B`, `C` ou `D`, e o token adulterado continua válido. Medi: 108 de 2000 tokens (5,4%)
  sobrevivem à adulteração. A correção é uma linha — adulterar um caractere do **meio** da assinatura
  (`token[:-8] + "A" + token[-7:]`) ou trocar o último por um que difira nos bits úteis. **Não
  mexi**: é arquivo fora do escopo declarado desta story, e a decisão é sua
- Nenhuma dependência nova, nenhuma migração, **nenhuma linha de `app/` alterada** — a estrutura
  alvo da story previa exatamente isso

### File List

**Novos**

- `backend/seeds/__init__.py`
- `backend/seeds/semear.py`
- `backend/tests/test_seed.py`

**Modificados**

- `backend/README.md`
- `README.md`
- `frontend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-7-dados-semeados-para-avaliacao.md`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.7 implementada. `backend/seeds/` nasceu com `semear.py` — `ContaSemeada`, as quatro contas do NFR2, `semear_conta`/`semear` recebendo a `Session` por parâmetro e `main()` como único ponto que abre `SessaoLocal`. 12 testes novos em `tests/test_seed.py` (85 no total, contra 73 antes), cobrindo os ACs 1 a 7 sem nunca chamar `main()`. Verificação manual contra o banco de desenvolvimento com contas de `/cadastro` já presentes: nenhuma foi apagada, alterada ou recriada, e o login das quatro credenciais publicadas devolve `200` com o papel da tabela. Os três READMEs atualizados: o da raiz trocou o `uv run python -c` improvisado pela tabela de contas, reescreveu o roteiro de avaliação começando pelas contas semeadas, ganhou três decisões novas (script idempotente em vez de migração de dados; idempotência por consulta em vez de limpeza; senha única publicada, com nome de pessoa por causa do UX-DR2) e registrou o evento publicado do NFR2 como dívida da Epic 2. Nenhuma dependência, nenhuma migração, nenhuma linha de `app/` alterada |
| 2026-08-10 | Story 1.7 criada e contextualizada. Três decisões do Igor incorporadas: contas com nome de pessoa e e-mail que diz o papel (o nome vai para tipografia serifada, reservada a nome próprio pelo UX-DR2); seed como script idempotente em `backend/seeds/`, rodado à mão por `uv run python -m seeds.semear`, em vez de migração Alembic de dados ou gancho no startup; e o evento publicado do NFR2 adiado para a Epic 2, com a dívida registrada no README. Sete ACs acrescentados aos três do `epics.md` (não sobrescrever conta pré-existente, avisar em vez de calar quando o papel diverge, provar que a senha semeada realmente autentica, e-mail já normalizado, `seeds/` no lugar reservado pela arquitetura com a `Session` recebida por parâmetro, e não regressão dos 73 testes). Registrado o porquê de o `SELECT` antes do `INSERT` — recusado no `cadastrar()` da 1.5 — ser a escolha certa aqui, e o porquê de o comando sair em `0` mesmo com aviso: na Story 1.8 ele roda antes do `uvicorn` |
