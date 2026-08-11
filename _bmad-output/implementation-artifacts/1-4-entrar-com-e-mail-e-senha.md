---
baseline_commit: 5e47eb3
---

# Story 1.4: Entrar com e-mail e senha

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **Primeira story que cruza as duas camadas.** Hoje não
existe nenhum hash, nenhum token, nenhum cookie, nenhum service, nenhum schema Pydantic e nenhuma
chamada do frontend para a API — `app/services/` e `app/schemas/` estão vazias com só o
`__init__.py`, e `frontend/src/lib/` tem só um `.gitkeep`. É esta story que enche as três.

## Story

Como organizador, cliente ou portaria,
quero entrar com meu e-mail e senha,
para acessar o que o meu papel permite.

## Acceptance Criteria

1. **Given** uma conta existente
   **When** eu envio e-mail e senha corretos para `POST /auth/login`
   **Then** recebo `200` e um cookie `httpOnly` com o JWT, `SameSite=Lax`, `Path=/` e
   `Max-Age` de 8 horas
   **And** o cookie é `Secure` quando `AMBIENTE=producao`
   **And** o JWT expira em 8 horas e carrega `sub` (id do usuário) e `papel`

2. **Given** uma senha gravada no banco
   **When** eu a inspeciono
   **Then** ela é um hash Argon2id — o valor começa com `$argon2id$`, nunca texto puro nem hash
   reversível
   **And** a mesma senha hasheada duas vezes produz valores diferentes (sal por hash)

3. **Given** credenciais erradas
   **When** eu tento entrar
   **Then** recebo `401` com `{"erro": {"codigo": "CREDENCIAIS_INVALIDAS", ...}}`
   **And** a resposta de "e-mail inexistente" é **byte a byte igual** à de "senha errada" — mesmo
   status, mesmo código, mesma mensagem

4. **Given** que estou autenticado
   **When** eu chamo `POST /auth/logout`
   **Then** o cookie é limpo

5. **Given** a tela `/login` no frontend
   **When** eu envio credenciais corretas
   **Then** sou levado para `/` e o cookie de sessão foi gravado **pelo domínio do próprio frontend**
   **And** com credenciais erradas vejo "E-mail ou senha incorretos", escolhido pelo `codigo` do erro
   e nunca pela `mensagem` vinda do servidor
   **And** o navegador nunca chama o backend diretamente: a única URL que ele conhece é `/api/...`

6. **Given** o formulário de login
   **When** eu o navego por teclado
   **Then** todo campo tem `<label>` associado, o foco é visível em âmbar e `Enter` envia
   **And** o erro aparece em região com `role="alert"`, anunciada por leitor de tela — UX-DR9
   **And** em nenhum lugar existe `outline: none`

7. **Given** uma conta gravada como `igor@exemplo.com`
   **When** eu entro digitando `Igor@Exemplo.COM ` (maiúsculas e espaço no fim)
   **Then** eu entro — a busca normaliza o e-mail, como a convenção da Story 1.3 estabeleceu

8. **Given** o segredo que assina o JWT
   **When** eu procuro no repositório
   **Then** ele vem de `JWT_SECRET` pela `Settings`, e nenhum valor real está versionado
   **And** subir com `AMBIENTE=producao` usando o valor de exemplo do `.env.example` falha na
   inicialização, com mensagem dizendo o que fazer

> **ACs 5 a 8 não estão no `epics.md`.** Os quatro primeiros são os do epic, e cobrem só a API.
>
> **AC5 e AC6** existem porque a tela de login entra nesta story (decisão do Igor — ver *Decisões que
> o Igor tomou*), e sem critério ela nasceria sem contrato de acessibilidade nem de tratamento de
> erro. O "pelo domínio do próprio frontend" do AC5 não é detalhe de implementação: é o que faz o
> `SameSite=Lax` do AD-15 continuar válido em produção (ver *O cookie entre dois domínios*).
>
> **AC7** existe porque a Story 1.3 fixou "gravar sempre em minúsculas, normalizando na entrada" como
> convenção do projeto e disse, textualmente, que "a 1.4 (login) precisa buscar do mesmo jeito". Sem
> este critério, a 1.5 grava normalizado e a 1.4 busca cru — e quem digitou o e-mail com a primeira
> letra maiúscula no celular não consegue entrar, com o sistema respondendo "credenciais inválidas".
>
> **AC8** existe pelo mesmo motivo que o AC4 da Story 1.3: o ponto mais provável de um segredo vazar
> é o valor de exemplo que fica funcionando. Um `JWT_SECRET` padrão que sobe em produção sem reclamar
> é um segredo público que assina sessões — e a Story 1.8 não tem como descobrir isso, porque
> funciona.

## Tasks / Subtasks

- [x] **T1. Dependências de segurança** (AC: 1, 2)
  - [x] Acrescentar ao `backend/pyproject.toml`, no estilo de versão fixa que já está lá:
        `argon2-cffi==25.1.0` e `pyjwt==2.13.0` (versões conferidas — ver *Stack desta story*)
  - [x] `uv sync` para atualizar o `uv.lock`, que é versionado
  - [x] **Não instale `python-jose`, `passlib`, `bcrypt` nem `email-validator`.** Os motivos de cada
        um estão em *Stack desta story* — `passlib` em particular está sem lançamento desde 2020 e
        não é necessário para usar Argon2
  - [x] **Não instale nada de rate limiting.** Está em `ARCHITECTURE-SPINE.md#Adiado`

- [x] **T2. `Settings` ganha o segredo e a política de cookie** (AC: 1, 8)
  - [x] Acrescentar a `app/core/config.py` — **estenda a classe existente, não crie outra**:
        - `jwt_secret: str = "troque-este-valor-em-producao"`
        - `cookie_sessao_nome: str = "rockhub_sessao"`
  - [x] `cookie_secure` é **propriedade derivada**, não campo: `return self.ambiente == "producao"`.
        Não é configurável de fora de propósito — ver *Por que `Secure` depende do ambiente*
  - [x] `@model_validator(mode="after")` recusando o valor de exemplo quando
        `ambiente == "producao"`, com mensagem que diz o comando para gerar um novo. É o AC8
  - [x] `backend/.env.example` ganha `JWT_SECRET` com o valor de exemplo e o comando de geração em
        comentário, no mesmo formato das chaves que já estão lá
  - [x] **Não crie `JWT_EXPIRACAO_HORAS`.** As 8 horas são invariante do AD-15, não configuração —
        ver *A expiração não é uma variável de ambiente*

- [x] **T3. `app/core/seguranca.py` — hash e token** (AC: 1, 2)
  - [x] Uma instância de módulo de `PasswordHasher()` (parâmetros padrão, que já são Argon2id —
        ver *Argon2id: o que vem de graça*)
  - [x] `gerar_hash(senha: str) -> str`
  - [x] `conferir_senha(hash_gravado: str, senha: str) -> bool` — captura `VerifyMismatchError`,
        `VerificationError` e `InvalidHashError` e devolve `False`. **Nunca deixe a exceção subir**:
        um hash corrompido no banco viraria `500` em vez de "credenciais inválidas"
  - [x] `HASH_FANTASMA`: hash de uma senha descartável, gerado **uma vez** no import. É contra quem
        ele existe está em *A resposta não pode revelar se o e-mail existe*
  - [x] `EXPIRACAO_SESSAO = timedelta(hours=8)` — constante de módulo, com o AD-15 citado no
        comentário. É a única fonte da validade: o `exp` do JWT e o `max_age` do cookie saem daqui
  - [x] `criar_token_sessao(usuario) -> str`: `jwt.encode({"sub": str(usuario.id), "papel":
        usuario.papel, "iat": agora, "exp": agora + EXPIRACAO_SESSAO}, segredo, algorithm="HS256")`.
        **`sub` precisa ser `str`** — ver *Armadilhas*, item 1
  - [x] `ler_token_sessao(token: str) -> dict | None`: `jwt.decode(..., algorithms=["HS256"])`
        devolvendo `None` em qualquer `PyJWTError`. A lista de algoritmos é obrigatória e não é
        burocracia — ver *Armadilhas*, item 2
  - [x] **Não escreva a dependência `usuario_atual` aqui.** Ela é da Story 1.6, e vai consumir
        exatamente este `ler_token_sessao`. Escrever agora é escrever sem consumidor
  - [x] **Não coloque a assinatura HMAC do ingresso neste arquivo.** É o AD-5, Story 3.9, com outro
        segredo (`TICKET_SIGNING_SECRET`). Os dois não se misturam

- [x] **T4. `app/schemas/auth.py` — primeiro schema Pydantic do projeto** (AC: 1, 3, 7)
  - [x] `LoginEntrada`: `email: str` e `senha: str`, com `field_validator(mode="before")` no e-mail
        aplicando `.strip().lower()` — é o AC7, e é o mesmo padrão de validador que o `cors_origens`
        já usa no `config.py`
  - [x] **`email` é `str`, não `EmailStr`** — motivo em *Stack desta story*. Não instale
        `email-validator` para isto
  - [x] `UsuarioSaida`: `id: UUID`, `nome: str`, `email: str`, `papel: PapelUsuario`, com
        `model_config = ConfigDict(from_attributes=True)`
  - [x] `PapelUsuario` é **importado** de `app.models.usuario`. Não redeclare o enum — a própria
        Story 1.3 escreveu isso no topo do arquivo do modelo
  - [x] `UsuarioSaida` é o schema que a Story 1.6 vai devolver em `GET /auth/eu`. Nasce com esse nome
        por isso — não o chame de `LoginSaida`

- [x] **T5. `app/services/autenticacao.py` — primeiro service do projeto** (AC: 1, 2, 3, 7)
  - [x] `autenticar(sessao: Session, email: str, senha: str) -> Usuario`
  - [x] Busca por e-mail já normalizado: `sessao.scalar(select(Usuario).where(Usuario.email == email))`
  - [x] Usuário inexistente: **confere a senha contra o `HASH_FANTASMA` e descarta o resultado**,
        depois levanta o erro. Sem isso a rota responde em 1ms para e-mail desconhecido e em ~50ms
        para e-mail existente, e virou um oráculo de cadastro
  - [x] Senha errada e usuário inexistente levantam **o mesmo** `ErroDeDominio("CREDENCIAIS_INVALIDAS",
        "E-mail ou senha incorretos.", status_http=401)` — literalmente a mesma construção, para o
        AC3 não depender de duas strings continuarem iguais por acidente
  - [x] Esta função **só lê**: nenhum `commit`, nenhum `flush`. A regra "transação é do service" vale;
        acontece que aqui não há escrita nenhuma
  - [x] **O service não sabe o que é cookie, nem HTTP, nem token.** Ele devolve o `Usuario` ou
        levanta. Quem monta o token e grava o cookie é o router — é a fronteira do
        `ARCHITECTURE-SPINE.md#Design Paradigm`

- [x] **T6. `app/api/auth.py` — as duas rotas** (AC: 1, 3, 4)
  - [x] `router = APIRouter(prefix="/auth", tags=["autenticação"])`
  - [x] `POST /auth/login`, corpo `LoginEntrada`, resposta `UsuarioSaida` com `status_code=200`.
        Recebe `sessao: Session = Depends(obter_sessao)` — a dependência já existe em `app/core/db.py`
  - [x] Chama `autenticacao.autenticar(...)`, monta o token e grava o cookie:
        ```python
        resposta.set_cookie(
            key=settings.cookie_sessao_nome,
            value=token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
            max_age=int(EXPIRACAO_SESSAO.total_seconds()),
        )
        ```
  - [x] `POST /auth/logout` → `204`, `delete_cookie` com **os mesmos** `path`, `samesite` e `secure`.
        Atributo diferente = cookie que não é apagado — ver *Armadilhas*, item 3
  - [x] **`logout` não exige cookie válido.** Chamar sem sessão, ou com token expirado, devolve `204`
        e limpa o que houver. Quem tem token vencido é justamente quem mais precisa sair
  - [x] Nenhum `if papel == ...` em nenhuma das duas. Autorização por papel é dependência do FastAPI
        e é a Story 1.6 — AD-9
  - [x] Registrar em `app/main.py`: `app.include_router(auth.router)`, ao lado do `saude`. É a única
        linha que o `main.py` recebe nesta story

- [x] **T7. Testes do backend** (AC: 1, 2, 3, 4, 7, 8)
  - [x] `tests/test_seguranca.py` — **não toca banco**, roda com o Postgres desligado
  - [x] `tests/test_auth.py` — usa a fixture `sessao` do `conftest.py` e um `TestClient` com
        `app.dependency_overrides[obter_sessao]` apontando para ela. Ler *Ligar o `TestClient` ao
        banco de teste* antes de escrever: é a primeira vez que isso aparece no projeto
  - [x] `tests/test_config.py` ganha o caso do AC8 (segredo de exemplo + `producao` = falha)
  - [x] A lista completa do que cada teste prova está em *Testing*. Os 20 testes atuais continuam
        passando, e os de `/saude`, erros e config continuam passando **com o Postgres desligado**

- [x] **T8. Proxy `/api/*` no Next** (AC: 5)
  - [x] `frontend/next.config.ts`:
        ```ts
        const destinoDaApi = process.env.API_URL ?? "http://localhost:8000";

        const nextConfig: NextConfig = {
          rewrites() {
            return [{ source: "/api/:caminho*", destination: `${destinoDaApi}/:caminho*` }];
          },
        };
        ```
  - [x] **Renomear `NEXT_PUBLIC_API_URL` para `API_URL`** no `frontend/.env.example`. Com o proxy o
        navegador não precisa mais saber o endereço da API — e variável `NEXT_PUBLIC_` vai embutida no
        bundle. Deixar a antiga viva é deixar duas formas de chamar a mesma API
  - [x] Atualizar o comentário do `.env.example`: a variável agora é lida **no servidor**, em tempo de
        build, e o motivo disso está em *Armadilhas*, item 5
  - [x] **Não crie `src/app/api/`.** O caminho `/api` pertence ao proxy; um Route Handler ali ganha do
        rewrite e o login para de funcionar por um motivo invisível

- [x] **T9. `src/lib/api.ts` — o cliente HTTP que a Story 1.2 deixou reservado** (AC: 5)
  - [x] `chamarApi<T>(caminho: string, opcoes?: RequestInit): Promise<T>` — monta `/api${caminho}`,
        `Content-Type: application/json`, e em resposta não-ok extrai `erro.codigo` e levanta um
        `ErroDaApi` que carrega **o código**, não a mensagem
  - [x] `ErroDaApi extends Error` com o campo `codigo: string`. É o que a tela usa para decidir o
        texto — contrato da Story 1.1, e a razão de o `codigo` existir
  - [x] Resposta `204` não tem corpo: não chame `.json()` nela. O `logout` é `204`
  - [x] **Só o caminho do navegador nesta story.** A busca a partir de Server Component precisa de URL
        absoluta e de repassar o cookie lido por `cookies()` — ela nasce na Story 1.6, com
        `GET /auth/eu`, que é o primeiro consumidor real. Deixe um comentário dizendo isso, não o código
  - [x] Não instale `axios`, `swr`, `react-query` nem biblioteca de formulário. `fetch` e
        `useState` bastam para dois campos

- [x] **T10. Tela `/login`** (AC: 5, 6)
  - [x] `src/app/login/page.tsx` — **Server Component**, coluna centrada de no máximo 440px: kicker
        `Acesso` (ou equivalente em voz jornalística) e o formulário. Sem segundo logotipo: o masthead
        já traz um, e dois logotipos na mesma tela é redundância — ver *Uma decisão de tela que ficou
        para você conferir*
  - [x] `src/components/FormularioLogin.tsx` — `"use client"`. É ilha de cliente legítima: formulário
        está na lista do `ARCHITECTURE-SPINE.md#Convenções`
  - [x] `<form onSubmit>` de verdade, para `Enter` enviar sem botão-alvo. Botão desabilitado enquanto
        envia, com `opacity:.35`
  - [x] Campos com `<label htmlFor>` explícito, `autoComplete="email"` e `autoComplete="current-password"`,
        `type="email"` e `type="password"`, `required`
  - [x] Erro numa região `role="alert"` acima do botão, texto escolhido pelo `codigo`:
        `CREDENCIAIS_INVALIDAS` → "E-mail ou senha incorretos."; qualquer outro → "Não foi possível
        entrar agora. Tente de novo em instantes." (voz jornalística: diz o que aconteceu e o que
        fazer — UX-DR8)
  - [x] Sucesso: `router.push("/")`. **Nada de redirecionar por papel** — `/organizador/...` e
        `/portaria` não existem ainda; inventar rota aqui produz 404 na cara do avaliador. O
        encaminhamento por papel nasce quando aquelas telas existirem (Epics 2 e 5)
  - [x] `src/components/FormularioLogin.module.css` com `.campo`, `.rotulo`, `.entrada`, `.botao`,
        `.erro` — especificação em *Anatomia da tela de login*
  - [x] **Não copie o `outline:none` do protótipo** (l. 152). É proibido no projeto inteiro desde a
        Story 1.2. O foco é o `:focus-visible` global âmbar; o `border-color: var(--ambar)` no `:focus`
        é *além* dele, não em vez dele
  - [x] **Não crie `Campo.tsx` nem `Botao.tsx` agora.** Dois campos no mesmo formulário não justificam
        abstração — mesmo critério que a Story 1.2 aplicou ao CSS do 404. Viram componente na Story 1.5,
        quando existir o segundo formulário
  - [x] Nada de link "esqueci minha senha" (o enunciado dispensa) nem "criar conta" (a tela de cadastro
        é da Story 1.5 — o link entra lá, junto da tela que ele abre)

- [x] **T11. Verificação** (AC: todos)
  - [x] `uv run pytest` — 20 anteriores + os novos, todos verdes
  - [x] `uv run pytest tests/test_saude.py tests/test_erros.py tests/test_config.py` **com o Postgres
        desligado** — continua passando
  - [x] Criar um usuário à mão para o teste manual, com o trecho de *Como entrar sem ter seed ainda*.
        **Não versione script para isso** — o seed é a Story 1.7
  - [x] No navegador, com backend e frontend no ar: `/login` → credenciais certas → cai em `/`;
        no DevTools, aba Application, o cookie `rockhub_sessao` aparece com domínio `localhost:3000`
        (o do frontend), `HttpOnly` marcado, e a aba Network mostra chamada para `/api/auth/login` —
        nunca para `localhost:8000`. É a verificação literal do AC5
  - [x] Credenciais erradas → mensagem única na região de alerta, e a resposta no Network é `401`
        com `CREDENCIAIS_INVALIDAS`
  - [x] `document.cookie` no console **não** mostra o cookie de sessão (é o `httpOnly` funcionando)
  - [x] `Tab` percorre e-mail → senha → botão com contorno âmbar visível em todos
  - [x] `npm run build`, `npx tsc --noEmit` e `npm run lint` limpos
  - [x] Busca em `frontend/src/` por `outline: none`, `NEXT_PUBLIC_API_URL` e `localhost:8000` → zero
        ocorrência
  - [x] Busca em `backend/` por senha em texto e por segredo literal: o único valor de `JWT_SECRET` no
        repositório é o de exemplo, no `.env.example` e no padrão da `Settings`

- [x] **T12. Documentação** (obrigatório — regra do projeto)
  - [x] `backend/README.md`: `JWT_SECRET` na tabela de configuração (com o comando de geração), as
        duas rotas novas, `app/schemas/`, `app/services/autenticacao.py` e `app/core/seguranca.py` na
        estrutura, contagem de testes atualizada, e a entrada *Story 1.4* no histórico da camada
  - [x] `frontend/README.md`: a variável passou a ser `API_URL` (não `NEXT_PUBLIC_`) **e por quê**; o
        proxy `/api/*` com o motivo; a rota `/login`; `src/lib/api.ts` e o contrato de erro por
        `codigo`; a armadilha do rewrite congelado no build; a estrutura de pastas atualizada
  - [x] `README.md` da raiz, "Como executar": o passo de gerar o `JWT_SECRET` antes de subir o backend
  - [x] `README.md` da raiz, "Roteiro de avaliação": já dá para entrar na aplicação — mas ainda não há
        contas semeadas, então descreva o que existe hoje sem prometer o que é da 1.7
  - [x] `README.md` da raiz, "Decisões": **cinco** entradas novas, cada uma com o que caiu e por quê —
        Argon2id; sessão em cookie `httpOnly` em vez de token no `localStorage`; PyJWT; proxy do Next
        em vez de `SameSite=None`; mensagem única para credenciais inválidas. A matéria-prima, com as
        alternativas descartadas, está em *Decisões que o Igor tomou* e em *O cookie entre dois domínios*
  - [x] `README.md` da raiz, "O que não está pronto": sem limite de tentativas de login, sem
        recuperação de senha, sem *refresh token*, e o login ainda não encaminha por papel
  - [x] `ARCHITECTURE-SPINE.md`: acrescentar `PyJWT 2.13.0` à tabela `Stack` (ela lista `argon2-cffi`
        e não lista a biblioteca de JWT), e uma frase no **AD-15** registrando que o `SameSite=Lax`
        se sustenta em produção porque o navegador só fala com o domínio do frontend. Sem essa frase,
        as Stories 1.8 e 1.9 vão reabrir a discussão do zero
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "descartei")

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **Não são sugestão, e a alternativa descartada
de cada uma é o material do README da raiz (T12).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Escopo | **Backend + tela de login** | *Só a API*: fecharia login como endpoint testado por `pytest`, mas a tela de login ficaria órfã — nenhuma story do `epics.md` a tem (a 1.5 é o formulário de cadastro, a 1.6 é `/auth/eu` e a identidade no masthead), e a T8 da Story 1.2 já havia reservado o cliente HTTP para cá: "a 1.4 é quem faz a primeira chamada real" |
| Biblioteca de JWT | **PyJWT 2.13.0** | *python-jose*: era a recomendação antiga do FastAPI, mas o último lançamento é de maio/2025 e ela traz `pyasn1`, `rsa` e `ecdsa` a mais no lockfile para implementar JOSE inteiro (JWE, JWK), que este projeto não usa. *`hmac` + `hashlib` da stdlib*: zero dependência nova e o mesmo mecanismo do AD-5, mas obrigaria a escrever à mão expiração, base64url e comparação em tempo constante — código de segurança que já existe testado |
| Cookie entre Vercel e Railway | **Proxy `/api/*` no Next** | *`SameSite=None; Secure` em produção*: menos código, mas transformaria a sessão em cookie de terceiro — o Safari o bloqueia por padrão e o login simplesmente não entra naquele navegador — e exigiria emendar o AD-15. *Deixar `Lax` cru e resolver na 1.8/1.9*: empurraria para o dia do deploy uma correção que mexe no frontend |
| Rota da tela | **`/login`** | *`/entrar`*: seria o único caminho em português puro e combinaria com o rótulo do botão, mas `login` é o termo que o avaliador reconhece de imediato e é o rótulo que o próprio protótipo usa na navegação |

### O cookie entre dois domínios — a razão do proxy

**O problema.** `rockhub.vercel.app` e `rockhub.up.railway.app` são sites diferentes para o navegador:
`vercel.app` e `up.railway.app` estão os dois na *Public Suffix List*, então não há domínio registrável
em comum. Um cookie `SameSite=Lax`, como o AD-15 fixa, **não é aceito nem reenviado** nesse cruzamento.
O login passaria em toda a suíte, funcionaria perfeitamente em `localhost` — onde `:3000` e `:8000` são
o mesmo site, porque porta não conta — e falharia calado em produção. É exatamente o que a AC da Story
1.9 cobra: *"o cookie de sessão é aceito entre os dois domínios"*.

**A saída escolhida.** O navegador nunca fala com a Railway. Ele chama `/api/auth/login` no domínio da
Vercel, e o Next reescreve para a Railway do lado do servidor:

```
navegador ──► rockhub.vercel.app/api/auth/login
                     │  rewrite do next.config.ts
                     ▼
              rockhub.up.railway.app/auth/login

o Set-Cookie volta pelo domínio da Vercel → cookie de origem própria → Lax funciona
```

Três consequências que valem escrever:

1. **O AD-15 continua literal.** `SameSite=Lax` sem emenda, sem exceção por ambiente, e sem depender
   da política de cookie de terceiro de cada navegador — que muda por decisão de fornecedor
2. **CORS deixa de participar do caminho do navegador**, porque as chamadas passam a ser de mesma
   origem. **Não remova o `CORSMiddleware` do `main.py`** por causa disso: ele continua sendo a rede
   de proteção de qualquer chamada direta e não custa nada
3. **`NEXT_PUBLIC_API_URL` deixa de fazer sentido** e vira `API_URL`, lida no servidor. Duas formas de
   alcançar a mesma API é o tipo de coisa que produz um bug que só aparece em um dos dois caminhos

### Por que `Secure` depende do ambiente

O AC1 pede o cookie `Secure`, e o AD-15 também. `Secure` significa "só trafega por HTTPS" — e o
desenvolvimento roda em `http://localhost:3000`. Chrome e Firefox tratam `localhost` como origem
confiável e aceitam o cookie mesmo assim; **o Safari, historicamente, não** — o cookie é descartado em
silêncio e o login parece funcionar e não funciona.

Por isso `cookie_secure` é derivado de `AMBIENTE`: `False` em `local`, `True` em `producao`. Não é um
campo configurável, para ninguém desligar em produção por engano num painel de deploy.

**Isto é uma suposição declarada, não uma decisão sua.** Se você preferir `Secure` sempre ligado, é
uma linha — e o custo é o desenvolvimento local passar a exigir HTTPS ou navegador específico.

### A expiração não é uma variável de ambiente

As 8 horas vêm do AD-15, com motivo escrito: "o suficiente para um turno de portaria". Invariante de
arquitetura com justificativa de domínio não vira knob de configuração — se virar, o valor que está em
produção deixa de ser o valor que está documentado, e ninguém descobre até alguém ser deslogado no meio
do turno.

Por isso `EXPIRACAO_SESSAO` é constante de módulo em `seguranca.py`, e é dela que saem **os dois**
prazos: o `exp` do JWT e o `max_age` do cookie. Se ficarem em lugares separados, um dia divergem — e o
sintoma é cookie que existe carregando token que já venceu, o que dá `401` numa tela que parece logada.

### Argon2id: o que vem de graça

`PasswordHasher()` do `argon2-cffi`, sem argumento nenhum, já é o que a story precisa:

- **Argon2id** é o tipo padrão (`Type.ID`) — o AD-15 pede exatamente esse, e é o que o AC2 verifica
  pelo prefixo `$argon2id$` da string
- **Perfil de baixa memória da RFC 9106** nos parâmetros padrão (`m=65536` KiB, `t=3`, `p=4`)
- **Sal aleatório por hash**, embutido na própria string — daí o AC2 exigir que a mesma senha produza
  hashes diferentes. Não existe coluna de sal e não deve existir
- **Todos os parâmetros viajam dentro do hash**, então trocá-los depois não invalida o que já está
  gravado

Duas consequências práticas:

- **Cada verificação custa ~50ms e ~64 MB de memória.** É o objetivo do algoritmo, não um problema a
  otimizar. Só aparece de duas formas: a suíte de testes de login fica perceptivelmente mais lenta que
  as outras, e vale lembrar disso na Story 1.8, ao escolher o tamanho da instância na Railway
- **Não use `passlib`.** É o wrapper que a documentação antiga do FastAPI usava; está sem lançamento
  desde 2020 e quebrou com o bcrypt 4. Aqui ele não acrescentaria nada: `argon2-cffi` é a API direta

`String(255)` em `senha_hash` já foi dimensionada para isto na Story 1.3 — um hash Argon2id tem ~97
caracteres, e a folga existe para trocar de parâmetros sem migração.

### A resposta não pode revelar se o e-mail existe

O AC3 tem duas metades, e a segunda é a que se esquece.

**A metade fácil** é a mensagem: "E-mail ou senha incorretos", nunca "esse e-mail não está cadastrado".
Para não depender de duas strings continuarem iguais no futuro, o erro é **a mesma construção de
`ErroDeDominio`** nos dois caminhos, e o teste compara os dois corpos de resposta entre si em vez de
comparar cada um com um literal.

**A metade que vaza é o tempo.** O caminho natural é: não achou o usuário, levanta o erro na hora.
Isso responde em ~1ms para e-mail desconhecido e em ~50ms para e-mail existente com senha errada — uma
diferença de cinquenta vezes, medível de fora com um `for` e um cronômetro. Quem faz isso não precisa
de nenhuma senha para descobrir quem tem conta no sistema.

A correção é uma linha: quando o usuário não existe, confira a senha contra o `HASH_FANTASMA` e jogue o
resultado fora. Os dois caminhos passam a custar o mesmo.

```python
usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))
if usuario is None:
    conferir_senha(HASH_FANTASMA, senha)   # nivela o tempo; resultado descartado
    raise _credenciais_invalidas()
if not conferir_senha(usuario.senha_hash, senha):
    raise _credenciais_invalidas()
return usuario
```

**Fora do escopo, e é decisão registrada:** limite de tentativas por IP ou por conta. Rate limiting
está em `ARCHITECTURE-SPINE.md#Adiado` e entra em *O que não está pronto* no README (NFR1) — o desafio
pede que o que ficou de fora seja declarado.

### Ligar o `TestClient` ao banco de teste

Primeira vez que isto aparece no projeto, e é onde a story pode travar. Os testes atuais são de dois
tipos que não se encontram: `test_saude.py` usa `TestClient` e não toca banco; `test_usuario.py` usa a
fixture `sessao` e não sobe HTTP. O login precisa dos dois ao mesmo tempo.

A ponte é a `dependency_overrides` do FastAPI, substituindo `obter_sessao` pela sessão da fixture — que
já roda dentro de uma transação revertida no fim de cada teste:

```python
@pytest.fixture()
def cliente(sessao: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obter_sessao] = lambda: sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Três pontos que custam tempo se passarem batido:

- **`clear()` no fim é obrigatório.** `app` é módulo importado, o override é global e sobrevive ao
  teste. Sem limpar, um teste de `/saude` numa execução seguinte pode receber a sessão de um banco já
  fechado, e a falha aparece longe da causa
- **`lambda: sessao` devolve a sessão, não um gerador.** O FastAPI aceita as duas formas; a diferença é
  que a versão com `yield` fecharia a sessão da fixture no fim da requisição, e o teste seguinte
  receberia uma sessão morta
- **Reverta o override, não a fixture.** Não crie uma segunda fixture de banco nem um segundo engine —
  o `conftest.py` da Story 1.3 já resolve migração e isolamento, e duplicá-lo reabre o risco de migrar
  o banco de desenvolvimento que aquela story fechou com cuidado

### Como entrar sem ter seed ainda

O seed com as quatro contas é a Story 1.7. Para verificar a tela à mão nesta story, crie **um** usuário
descartável, do diretório `backend/`, com o Compose no ar e a migração aplicada:

```bash
uv run python -c "
from app.core.db import SessaoLocal
from app.core.seguranca import gerar_hash
from app.models.usuario import PapelUsuario, Usuario
s = SessaoLocal()
s.add(Usuario(nome='Igor Teste', email='igor@exemplo.com',
              senha_hash=gerar_hash('rockhub'), papel=PapelUsuario.CLIENTE.value))
s.commit()
print('criado')
"
```

**Não versione isto como script.** Um `seed.py` improvisado nesta story é um arquivo que a 1.7 vai
apagar ou, pior, manter em paralelo ao seed de verdade. E não coloque o e-mail nem a senha no README —
"Contas semeadas" pertence à 1.7, e credencial anunciada que não existe é pior que credencial ausente.

### Anatomia da tela de login

Do protótipo (`proto-jornal-noturno.html`, l. 699-711 para a tela, l. 140-153 para `.btn` e `.campo`).
Medidas são ponto de partida; a estrutura e as regras do sistema não são.

```
       ┌──────────── 440px, centrada ────────────┐
       │  ACESSO                                 │  ← kicker: mono 600 10px, .22em, versalete, fumaça
       │                                         │
       │  E-MAIL                                 │  ← rótulo: mono 600 10px, .15em, versalete, fumaça
       │  ┌───────────────────────────────────┐  │
       │  │ igor@exemplo.com                  │  │  ← breu2, fio 1px, mono 16px, padding 14px
       │  └───────────────────────────────────┘  │
       │  SENHA                                  │
       │  ┌───────────────────────────────────┐  │
       │  │ ••••••••                          │  │
       │  └───────────────────────────────────┘  │
       │  ⚠ E-mail ou senha incorretos.          │  ← role="alert", brasa, mono 11px
       │  ┌───────────────────────────────────┐  │
       │  │            E N T R A R            │  │  ← âmbar, texto breu, mono 700 12px, .18em
       │  └───────────────────────────────────┘  │
       └─────────────────────────────────────────┘
```

```css
.campo   { margin-bottom: 20px; }
.rotulo  { display:block; margin-bottom:7px; font:600 10px/1 var(--mono);
           letter-spacing:.15em; text-transform:uppercase; color:var(--fumaca); }
.entrada { width:100%; background:var(--breu2); border:1px solid var(--fio);
           color:var(--cal); padding:14px; font:16px/1 var(--mono); }
.entrada:focus { border-color: var(--ambar); }   /* ALÉM do :focus-visible global, nunca em vez dele */
.botao   { width:100%; background:var(--ambar); color:var(--breu); padding:18px;
           font:700 12px/1 var(--mono); letter-spacing:.18em; text-transform:uppercase; }
.botao:disabled { opacity:.35; }
.erro    { margin-bottom:16px; color:var(--brasa); font:11px/1.6 var(--mono); }
```

O que o protótipo tem e **não** vai para a tela:

- **`outline:none` no input** (l. 152). Proibido no projeto desde a Story 1.2, sem exceção
- **O bloco de contas semeadas em âmbar** no pé da tela. É útil, e é da Story 1.7 — antes do seed
  existir, seria uma lista de credenciais que não funcionam
- **O segundo logotipo.** No protótipo a tela é isolada, sem masthead; aqui o masthead vem do layout
  raiz

Raio zero, sombra zero, nenhum card. Sem serifada em etiqueta e sem monoespaçada em nome próprio —
neste formulário tudo é dado de máquina, então tudo é monoespaçada, e é por isso que a tela não tem
nenhum trecho em Georgia além do logotipo do masthead.

[Fonte: DESIGN.md#Components (botao), DESIGN.md#Colors, UX-DR1, UX-DR2, UX-DR9]

### Uma decisão de tela que ficou para você conferir

**O masthead aparece em `/login`**, porque ele vive no layout raiz e esta story não mexe no layout. A
consequência é que quem não está logado vê "Meus ingressos" e "Minha conta" na navegação — dois links
que ainda caem no 404 da Story 1.2 e que, mesmo depois, não fazem sentido para visitante.

Mantive assim de propósito: tirar o masthead exige um grupo de rotas com layout próprio, e isso é
estrutura nova numa story que já cruza as duas camadas. `DESIGN.md#Como usar este documento` classifica
"quais componentes existem e como se dividem" como **provisório**, ajustável livremente — então é seu
para decidir na hora de olhar a tela. As duas saídas, se você quiser trocar:

- um grupo de rotas `src/app/(entrada)/` com `layout.tsx` sem masthead, e a tela ganha o logotipo
  próprio do protótipo
- ou o masthead passa a mostrar navegação diferente para quem não está logado — o que naturalmente é
  assunto da Story 1.6, que é quem traz a identidade do usuário para o cabeçalho

### O que já existe e esta story estende — leia antes de escrever

Cinco arquivos são **modificados**, não criados:

| Arquivo | Estado hoje | O que esta story faz |
|---|---|---|
| `backend/app/core/config.py` | `Settings` com `app_nome`, `ambiente`, `cors_origens`, `database_url`, `database_url_teste`. Dois `field_validator(mode="before")` como exemplo pronto | **Acrescenta** `jwt_secret`, `cookie_sessao_nome`, a propriedade `cookie_secure` e um `model_validator`. Não reescreve a classe |
| `backend/app/main.py` | CORS + três handlers de erro + `include_router(saude.router)` | **Uma linha**: `include_router(auth.router)`. Os handlers já cobrem o `ErroDeDominio` do login — não escreva handler novo |
| `backend/pyproject.toml` · `backend/.env.example` | Versões fixas por `==`; três chaves ativas e duas comentadas | **Acrescentam** duas dependências e uma chave, no mesmo estilo |
| `frontend/next.config.ts` | Objeto vazio com o comentário do template | Ganha o bloco `rewrites()` |
| `frontend/.env.example` | `NEXT_PUBLIC_API_URL=http://localhost:8000` | A variável **vira** `API_URL` — a antiga sai |

Não modificados, e **não devem quebrar**: `app/core/erros.py` (o formato de erro já serve),
`app/core/db.py` (a dependência `obter_sessao` já serve), `app/models/usuario.py` (o modelo já tem
`senha_hash` e `PapelUsuario`), `app/api/saude.py`, `migrations/`, e os 20 testes atuais. Se algum
deles precisar mudar para o login funcionar, algo foi feito errado.

No frontend, `layout.tsx`, `Masthead.tsx`, `NavLink.tsx`, `page.tsx`, `not-found.tsx` e `globals.css`
**não mudam**. Em especial: não acrescente token novo ao `globals.css` — a tela de login usa só os nove
que já existem.

### Contrato das duas rotas

```
POST /auth/login
  ← {"email": "igor@exemplo.com", "senha": "rockhub"}
  → 200  {"id": "…uuid…", "nome": "Igor Teste", "email": "igor@exemplo.com", "papel": "CLIENTE"}
         Set-Cookie: rockhub_sessao=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800
                     (+ Secure quando AMBIENTE=producao)
  → 401  {"erro": {"codigo": "CREDENCIAIS_INVALIDAS", "mensagem": "E-mail ou senha incorretos."}}
  → 422  {"erro": {"codigo": "DADOS_INVALIDOS", "mensagem": "…"}}   ← campo ausente; já é automático

POST /auth/logout
  → 204  sem corpo; Set-Cookie apagando rockhub_sessao com os mesmos atributos
         Não exige sessão válida.
```

Carga do JWT: `{"sub": "<uuid do usuário como string>", "papel": "CLIENTE", "iat": …, "exp": …}`.
Nada além disso — nome e e-mail não entram no token. Token é credencial que trafega em toda requisição:
quanto menos carrega, menos vaza se for lido, e menos fica velho quando o usuário troca o nome.

**O corpo de resposta do login devolve o usuário** para a Story 1.6 reaproveitar o mesmo `UsuarioSaida`
em `GET /auth/eu`. Nesta story a tela não usa esse corpo — ela só redireciona — e isso é aceitável:
o schema nasce onde nasce o endpoint que o produz.

### Armadilhas específicas desta story

Em ordem de probabilidade:

1. **`sub` precisa ser string.** O PyJWT valida a claim `sub` desde a 2.10 e levanta
   `InvalidSubjectError` se ela não for `str`. `usuario.id` é `UUID`. Passar direto funciona no
   `encode` e explode no `decode` — ou seja, o login parece certo e a Story 1.6 é que quebra.
   `str(usuario.id)` na criação, `uuid.UUID(payload["sub"])` na leitura

2. **`jwt.decode` sem `algorithms=[...]` levanta erro.** E não é burocracia do PyJWT: aceitar o
   algoritmo que vem escrito no próprio token é a vulnerabilidade clássica de JWT — um token com
   `"alg": "none"` passaria a valer. Sempre `algorithms=["HS256"]`, fixo no código

3. **Apagar cookie exige repetir os atributos.** `delete_cookie` monta um `Set-Cookie` com valor
   vazio; se `path`, `samesite` ou `secure` diferirem do que foi gravado, o navegador trata como outro
   cookie e o original continua lá. Sintoma: `logout` responde `204` e o usuário segue logado. Use as
   mesmas constantes da `Settings` nos dois lugares

4. **`response.set_cookie` precisa da `Response` na assinatura.** No FastAPI, para gravar cookie e
   ainda devolver corpo com `response_model`, declare `resposta: Response` como parâmetro da função e
   escreva nela — o FastAPI mescla no retorno. Construir um `JSONResponse` à mão funciona, e joga fora
   a serialização do `response_model` junto com a documentação automática do `/docs`

5. **O `destination` do rewrite é congelado no build.** A Vercel compila as rotas no `next build`, e
   `process.env.API_URL` é lido ali. Trocar a variável no painel depois **não** muda o proxy sem um
   redeploy. Isso vai morder na Story 1.9 se não estiver escrito no `frontend/README.md` — e o
   sintoma é o frontend novo apontando para a API antiga

6. **Rewrite perde para arquivo do App Router.** Um `rewrites()` que devolve array é avaliado *depois*
   do sistema de arquivos. Se alguém criar `src/app/api/qualquer/route.ts`, ele ganha do proxy naquele
   caminho. Por isso `/api` é reservado neste projeto

7. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** Documentado desde a
   Story 1.1: `uv run pytest` falha com `os error 4551`. O contorno é chamar pelo módulo —
   `uv run python -m pytest`. Os comandos canônicos do README continuam na forma direta, com o
   contorno logo abaixo

8. **`uv run pytest` exige o Compose no ar** desde a Story 1.3. Se `test_auth.py` falhar em conectar,
   é `docker compose up -d` que está faltando — não é bug da story

9. **Erro de rede no `fetch` não tem `codigo`.** Backend desligado produz `TypeError: Failed to fetch`,
   que não passa pelo caminho do `ErroDaApi`. Trate: `try/catch` em volta da chamada e a mensagem
   genérica de "não foi possível entrar agora". Sem isso a tela quebra em branco quando a API cai —
   e é o primeiro estado que qualquer avaliador encontra se subir só o frontend

10. **`credentials` não precisa de `include`.** A chamada é de mesma origem por causa do proxy, e
    `same-origin` já é o padrão do `fetch`. Escrever `include` funciona e sugere, para quem ler depois,
    que existe uma chamada cruzando domínio — que é justamente o que o proxy eliminou

### Convenções que nascem aqui

Valem para as 34 stories seguintes:

- **`app/services/<assunto>.py` com funções de módulo, não classes.** O service recebe a `Session` como
  primeiro parâmetro e devolve modelo ou levanta `ErroDeDominio`. Não há classe de service, não há
  injeção de service — a função é a unidade
- **O service nunca sabe de HTTP.** Nem status, nem cookie, nem header. Ele levanta `ErroDeDominio` com
  o status embutido e o router não traduz nada
- **`app/schemas/<assunto>.py`**, um arquivo por assunto, com os nomes sufixados `Entrada` e `Saida`.
  Nunca reaproveite um schema de entrada como saída: é assim que um `senha_hash` acaba num corpo de
  resposta
- **Todo segredo é campo da `Settings` com valor de exemplo, e o `model_validator` recusa o exemplo em
  produção.** `TICKET_SIGNING_SECRET` (Story 3.9) e `TICKETMASTER_API_KEY` (Story 2.1) seguem este
  mesmo padrão
- **No frontend, toda chamada à API passa por `src/lib/api.ts`** e todo caminho começa com `/api`.
  Nenhum componente monta URL de backend por conta própria
- **A tela escolhe o texto pelo `codigo` do erro, nunca pela `mensagem`.** A mensagem do servidor é
  para humano que lê log; o texto de tela é decisão de produto, e mora no frontend

### Estrutura alvo ao fim desta story

```text
backend/
  pyproject.toml            # +argon2-cffi, +pyjwt
  uv.lock                   # regerado
  .env.example              # +JWT_SECRET
  app/
    core/
      config.py             # +jwt_secret, +cookie_sessao_nome, +cookie_secure, +model_validator
      seguranca.py          # NOVO — Argon2id, HASH_FANTASMA, criar/ler token, EXPIRACAO_SESSAO
    schemas/
      auth.py               # NOVO — LoginEntrada, UsuarioSaida
    services/
      autenticacao.py       # NOVO — autenticar()
    api/
      auth.py               # NOVO — POST /auth/login, POST /auth/logout
    main.py                 # +include_router(auth.router)
  tests/
    test_seguranca.py       # NOVO — sem banco
    test_auth.py            # NOVO — TestClient + fixture de sessão
    test_config.py          # +caso do segredo de exemplo em produção
frontend/
  next.config.ts            # +rewrites: /api/* → API_URL
  .env.example              # NEXT_PUBLIC_API_URL → API_URL
  src/
    lib/
      api.ts                # NOVO — chamarApi, ErroDaApi (o .gitkeep pode sair)
    app/
      login/
        page.tsx            # NOVO — Server Component, coluna de 440px
        page.module.css     # NOVO
    components/
      FormularioLogin.tsx        # NOVO — "use client"
      FormularioLogin.module.css # NOVO
```

`app/integrations/` e `backend/seeds/` continuam não existindo — são as Stories 2.1 e 1.7.

[Fonte: ARCHITECTURE-SPINE.md#Árvore]

### Comandos que esta story precisa deixar funcionando

```bash
# gerar o segredo de sessão (vai para o .env, nunca para o repositório)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# da raiz
docker compose up -d

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # http://localhost:8000/docs mostra /auth/login e /auth/logout
uv run pytest

cd ../frontend
npm run dev                             # http://localhost:3000/login
```

### Escopo — o que NÃO fazer aqui

`GET /auth/eu`, a dependência de papel, a identidade do usuário no masthead e o botão "sair" na
interface (**Story 1.6**) · cadastro, tela de cadastro e componente `Campo` compartilhado
(**Story 1.5**) · seed e contas documentadas no README (**Story 1.7**) · deploy, variável de ambiente
em produção (**Stories 1.8 e 1.9**) · redirecionamento por papel, telas de organizador e de portaria
(**Epics 2 e 5**) · recuperação de senha, *refresh token*, limite de tentativas, `TICKET_SIGNING_SECRET`.

É tentador escrever a dependência `usuario_atual` "já que o `ler_token_sessao` está pronto".
**Não escreva:** sem nenhuma rota protegida para consumi-la, ela nasce sem forma verificável, e a
Story 1.6 — que tem o `403`, o `401` e o `GET /auth/eu` para provar o comportamento — reescreveria.

### Testing

Duas famílias, deliberadamente separadas por dependência de banco.

**`tests/test_seguranca.py`** — nenhuma conexão, passa com o Postgres desligado:

| O que prova | AC |
|---|---|
| `gerar_hash` produz string começando com `$argon2id$` | 2 |
| A mesma senha hasheada duas vezes dá valores diferentes (sal por hash) | 2 |
| `conferir_senha` aceita a senha certa e recusa a errada | 2 |
| `conferir_senha` devolve `False` — sem levantar — para um hash corrompido | 2 |
| Token criado e lido de volta traz `sub` e `papel`, e `exp - iat == 8h` | 1 |
| Token com um caractere alterado na assinatura é recusado (`None`) | 1 |
| Token assinado com outro segredo é recusado | 1 |
| Token com `exp` no passado é recusado | 1 |

**`tests/test_auth.py`** — precisa do Compose no ar; usa a fixture `sessao` + `dependency_overrides`:

| O que prova | AC |
|---|---|
| Login correto responde `200`, corpo com `papel`, e **sem** `senha_hash` em campo algum | 1 |
| O valor de `senha_hash` lido do banco começa com `$argon2id$` e é diferente da senha digitada — o AC2 fala do que está gravado, não só do que a função devolve | 2 |
| O `Set-Cookie` traz `HttpOnly`, `SameSite=Lax`, `Path=/` e `Max-Age=28800` | 1 |
| Em `AMBIENTE=local` o cookie **não** é `Secure`; com a `Settings` sobrescrita para `producao`, é | 1 |
| Senha errada responde `401` com `codigo == "CREDENCIAIS_INVALIDAS"` | 3 |
| E-mail inexistente responde **exatamente o mesmo corpo e status** que a senha errada — comparando as duas respostas entre si | 3 |
| `Igor@Exemplo.COM ` com espaço e maiúsculas entra na conta gravada em minúsculas | 7 |
| Corpo sem o campo `senha` responde `422` no formato `{"erro": {...}}` | — |
| `POST /auth/logout` responde `204` e o `Set-Cookie` esvazia o cookie com os mesmos atributos | 4 |
| `POST /auth/logout` sem cookie nenhum também responde `204` | 4 |

**`tests/test_config.py`** ganha: `Settings(ambiente="producao")` com o `jwt_secret` de exemplo levanta
`ValidationError`; com um segredo próprio, não levanta. É o AC8.

**O frontend continua sem teste automatizado** — decisão registrada na Story 1.2, com o motivo, e já
escrita no README da raiz. A verificação da tela é manual, e está na T11.

### Inteligência das stories anteriores

**Da 1.1 (backend):**

- **O formato de erro já existe e já é único.** `ErroDeDominio` carrega código, mensagem e status, e o
  handler do `main.py` o serializa. O `401` do login **não** precisa de handler novo, e não deve
  ganhar um
- **`CODIGO_POR_STATUS[401]` é `NAO_AUTENTICADO`** — é o código para os `401` que o framework levanta.
  O login usa `CREDENCIAIS_INVALIDAS`, que é do domínio. Os dois convivem: um diz "você não se
  identificou", o outro diz "a identificação não bateu"
- **`Settings` tem `@lru_cache` em `obter_settings()`** e dois validadores prontos para copiar o padrão.
  Estenda, não recrie
- **CORS já lê `CORS_ORIGENS`** com `http://localhost:3000` por padrão e `allow_credentials=True` — foi
  antecipado na 1.1 pensando neste cookie
- **Windows App Control** bloqueia os `.exe` da virtualenv (armadilha 7)

**Da 1.2 (frontend):**

- **O cliente HTTP foi reservado para esta story**, textualmente: "o wrapper de `fetch` é da Story 1.4,
  que é quem faz a primeira chamada real". `src/lib/` existe vazia esperando isso
- **A porta 3000 não é escolha livre** — é a origem que o `CORS_ORIGENS` do backend autoriza por padrão
- **Foco âmbar global e `prefers-reduced-motion` já estão no `globals.css`.** A tela herda; não
  redeclare, e não desligue
- **Precedente de não abstrair cedo:** o CSS do 404 foi repetido em vez de virar componente, com o
  motivo escrito no arquivo. É o mesmo critério que mantém `Campo.tsx` fora desta story
- **`frontend/AGENTS.md` e `frontend/CLAUDE.md` são gerados pelo `next dev`**, não são seus. O
  `AGENTS.md` manda ler `node_modules/next/dist/docs/` antes de escrever código de Next 16 — vale para
  o `rewrites()` desta story, que é onde a API do 16 pode divergir do que você lembra
- **Pendência aberta:** o `favicon.ico` ainda é o do `create-next-app`. Não é desta story; não mexa
  sem o Igor decidir

**Da 1.3 (banco):**

- **`PapelUsuario` mora em `app/models/usuario.py`** e é o único enum de papel do projeto. O schema
  desta story importa dele
- **A convenção de e-mail em minúsculas nasceu lá**, apontando explicitamente para esta story: "a 1.4
  (login) precisa buscar do mesmo jeito". É o AC7
- **`obter_sessao()` não abre transação** — quem faz `commit`/`rollback` é o service. O login não
  escreve nada, então não há transação a abrir
- **`senha_hash` é `String(255)`**, dimensionada para Argon2id com folga
- **A fixture de sessão usa SAVEPOINT reaberto** por evento, para um `IntegrityError` esperado não
  sujar a transação externa. Se um teste novo de login provocar erro de banco de propósito, o
  mecanismo já está lá — não o reescreva
- **`uv run pytest` passou a exigir o Compose no ar**, e isso já está no `backend/README.md`

**Do estado do repositório:** último commit `5e47eb3 feat: Story 1.3: Modelo de usuário e primeira
migração`, na branch `epic-1---fundacao-acesso-e-primeiro-deploy`, árvore limpa. As Stories 1.1, 1.2 e
1.3 estão em `review` — o code review acontece ao fim da epic, não a cada story. 20 testes passando.

[Fonte: _bmad-output/implementation-artifacts/1-1-esqueleto-do-backend-que-responde.md,
1-2-esqueleto-do-frontend-com-a-identidade-aplicada.md,
1-3-modelo-de-usuario-e-primeira-migracao.md]

### Stack desta story — versões conferidas na web em 10/08/2026

| Pacote | Versão | Papel |
|---|---|---|
| `argon2-cffi` | 25.1.0 | Hash de senha. `PasswordHasher()` já é Argon2id no perfil de baixa memória da RFC 9106 |
| `pyjwt` | 2.13.0 (21/05/2026) | Assinatura e leitura do JWT em HS256. Nenhuma dependência extra para HMAC |

**Descartados, e por quê:**

- **`python-jose` 3.5.0** — último lançamento em maio/2025; implementa JOSE inteiro e traz `pyasn1`,
  `rsa` e `ecdsa` que este projeto não usa
- **`passlib`** — sem lançamento desde 2020. Era wrapper para `bcrypt`; com `argon2-cffi` não
  acrescenta nada
- **`email-validator`** (que o `EmailStr` do Pydantic exige) — no **login** não há o que validar: o
  e-mail é chave de busca, e formato inválido já não encontra ninguém. Pior, um `422` de formato antes
  do `401` de credencial cria a distinção que o AC3 quer eliminar. A decisão de usar `EmailStr`
  pertence à Story 1.5, onde o formato é gravado no banco
- **Qualquer biblioteca de rate limiting** — `ARCHITECTURE-SPINE.md#Adiado`

[Fonte: ARCHITECTURE-SPINE.md#Stack, AD-15]

### Project Structure Notes

Esta story ocupa `backend/` e `frontend/` — a primeira a tocar as duas camadas no mesmo commit. É
inevitável: o proxy do Next e o atributo do cookie são **uma** decisão, e separá-la em dois commits
deixaria um dos lados sem sentido durante um deles.

Ela também é a primeira a preencher `app/services/` e `app/schemas/`, que a Story 1.1 criou vazias
justamente para que a story que precisasse não improvisasse onde as coisas moram.

Não toque em `migrations/` — nenhuma coluna muda nesta story. O modelo `Usuario` já tem tudo o que o
login precisa.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- [Source: ARCHITECTURE-SPINE.md#AD-15] — Argon2id, JWT em cookie `httpOnly`/`Secure`/`SameSite=Lax`,
  8 horas, sem *refresh token*, nada em `localStorage`
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel único por conta; autorização como dependência (Story 1.6)
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`, sem repositórios
- [Source: ARCHITECTURE-SPINE.md#Convenções de Consistência] — formato de erro com `codigo` estável,
  transação no service, configuração por variável de ambiente, Server Component por padrão
- [Source: ARCHITECTURE-SPINE.md#Stack] · [Source: ARCHITECTURE-SPINE.md#Adiado] — sem rate limiting,
  sem *refresh token*, sem recuperação de senha
- [Source: EXPERIENCE.md#Voice and Tone] — erro diz o que aconteceu e o que fazer
- [Source: EXPERIENCE.md#Accessibility Floor] · [Source: UX-DR9] — `<label>` em todo campo, foco
  visível, resultado anunciado a leitor de tela
- [Source: DESIGN.md#Components (botao)] · [Source: DESIGN.md#Colors] · [Source: UX-DR1, UX-DR2] —
  botão, campo, paleta e o pareamento tipográfico
- [Source: mockups/proto-jornal-noturno.html#L699-L711] — a tela de login;
  [#L140-L153] — `.btn` e `.campo` (com o `outline:none` que **não** vai para o código)
- [Source: backend/app/core/config.py] · [backend/app/core/erros.py] · [backend/app/core/db.py] ·
  [backend/app/models/usuario.py] · [backend/tests/conftest.py] — o que a story estende
- [Source: frontend/next.config.ts] · [frontend/.env.example] · [frontend/src/app/globals.css]
- [Source: frontend/AGENTS.md] — Next 16 divergiu; a documentação é a de
  `node_modules/next/dist/docs/`
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Confirme com o Igor antes de `docker compose up`** e antes de `uv sync`/`npm install`, se ele não
   estiver acompanhando
3. **Atualize os três READMEs antes de dar a story por concluída.** Nesta story os três mudam — é a
   primeira em que o `frontend/README.md` também tem o que registrar desde a 1.2. As cinco entradas de
   decisão da T12 são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As quatro desta story já estão respondidas. Se aparecer uma quinta
   — microcopy do erro, nome do cookie, se o masthead sai da tela de login — pergunte em vez de escolher
5. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (implementação) / claude-opus-5 (fechamento da story)

### Debug Log References

- `uv run python -m pytest` → **40 passed** (20 anteriores + 20 novos)
- `uv run python -m pytest tests/test_saude.py tests/test_erros.py tests/test_config.py tests/test_seguranca.py`
  **com o container do Postgres parado** → 24 passed. A separação por dependência de banco continua valendo
- `npm run build` → 3 rotas estáticas (`/`, `/_not-found`, `/login`) · `npx tsc --noEmit` limpo · `npm run lint` limpo
- Busca em `frontend/src/` por `outline: none`, `NEXT_PUBLIC_API_URL` e `localhost:8000` → **zero ocorrências**
- Busca por segredo no `backend/`: o único valor de `JWT_SECRET` versionado é o de exemplo, no
  `.env.example` e como padrão da `Settings`
- Verificação HTTP de ponta a ponta **através do proxy** (`curl` contra `localhost:3000`, não contra a API):
  login correto → `200` + `Set-Cookie: rockhub_sessao=…; HttpOnly; Max-Age=28800; Path=/; SameSite=lax`;
  `Igor@Exemplo.COM ` (maiúsculas + espaço) entrou na conta gravada em minúsculas; senha errada e e-mail
  inexistente devolveram corpos idênticos; `logout` → `204` esvaziando o cookie
- Conferência no navegador feita pelo Igor: `/login` funcionando

### Completion Notes List

**O que foi implementado.** Backend: `app/core/seguranca.py` (Argon2id, `HASH_FANTASMA`,
`EXPIRACAO_SESSAO`, criar/ler token), `app/schemas/auth.py`, `app/services/autenticacao.py`,
`app/api/auth.py` com `POST /auth/login` e `POST /auth/logout`, e a `Settings` estendida com
`jwt_secret`, `cookie_sessao_nome`, a propriedade derivada `cookie_secure` e o `model_validator` que
recusa o segredo de exemplo em produção. Frontend: proxy `/api/*` no `next.config.ts`,
`src/lib/api.ts` (`chamarApi` + `ErroDaApi`), a tela `/login` como Server Component e o
`FormularioLogin` como ilha de cliente.

**Três decisões de implementação que valem registrar:**

1. **A região de erro (`role="alert"`) existe sempre no DOM, vazia**, e só o texto entra depois. Se
   ela fosse montada junto com o conteúdo, parte dos leitores de tela não anunciaria nada — que é
   exatamente o que o AC6 pede. Vazia ela não ocupa espaço, então não custa layout.
2. **O teste de `Secure` em produção substitui `obter_settings` no módulo do router** por uma
   `Settings(ambiente="producao", jwt_secret=…)` de verdade, em vez de um objeto falso. Assim o teste
   exercita a propriedade `cookie_secure` real, incluindo o `model_validator`.
3. **O comentário do CSS foi reescrito para não conter a string literal proibida.** A primeira versão
   dizia "nenhum `outline:none` aqui" — o que fazia a busca de verificação da T11 acusar uma
   ocorrência num arquivo que estava correto. O comentário agora diz a mesma coisa sem o literal.

**Um usuário descartável foi criado no banco de desenvolvimento** (`igor@exemplo.com` / `rockhub`)
para a conferência manual. Não foi versionado script nenhum para isso — o seed é a Story 1.7.

**Correção depois da conferência do Igor: a tela de acesso perdeu o masthead.** A story previa que
ele apareceria em `/login` e classificava isso como "decisão que ficou para você conferir" — o Igor
conferiu e recusou, com razão: a tela oferecia "Meus ingressos" e "Minha conta" para quem ainda não
tinha entrado, dois links que caem no 404. O frontend passou a ter dois grupos de rotas, `(site)`
(com masthead) e `(entrada)` (só o logotipo), o layout raiz virou apenas `<html><body>`, e o
logotipo saiu do `Masthead` para um componente próprio, já que as duas cascas o usam.

Três coisas que essa correção ensinou e que estão escritas no código e no `frontend/README.md`:

1. **`not-found.tsx` só atende URL não casada quando está na raiz de `app/`.** Movi para dentro de
   `(site)` esperando que herdasse o masthead; o efeito foi o visitante cair no 404 padrão do Next,
   sem identidade nenhuma. Voltou para a raiz montando a própria casca — é a única duplicação de
   casca do projeto, e é obrigatória.
2. **Grupo de rotas, não layout raiz múltiplo.** A documentação do Next avisa da recarga completa
   entre layouts raiz, e layout raiz múltiplo exigiria abrir mão do `app/layout.tsx`, empurrando o
   404 para o `global-not-found` experimental.
3. **`TaskStop` não mata o `node` filho do `npm run dev`/`start`.** O órfão segurou a porta 3000 e
   um `npm run start` seguinte falhou com `EADDRINUSE` — enquanto as conferências batiam num build
   antigo ainda no ar. Encerrar processo de segundo plano agora inclui conferir a porta e matar pelo
   PID.

**Duas decisões do Igor tomadas nessa conversa, que viram trabalho das próximas stories:** o link
"Ainda não tem conta? Cadastre-se agora" entra na **Story 1.5**, junto da tela que ele abre (link
para 404 não entra no repositório nem por um commit); e o "Entrar" no masthead entra na **Story
1.6**, que é quem passa a saber se existe sessão — lá as duas navegações nascem juntas. Ele também
confirmou que **a raiz continua pública**: nada de redirecionar visitante para `/login`, porque a
Story 3.1 é literal em "como visitante... abro a página inicial".

**O que ficou intencionalmente de fora**, conforme o escopo da story: a dependência `usuario_atual`
(Story 1.6, que tem `GET /auth/eu` para dar forma verificável a ela), o caminho de Server Component
do `src/lib/api.ts` (mesma story, primeiro consumidor real), os componentes `Campo.tsx`/`Botao.tsx`
(Story 1.5, quando existir o segundo formulário) e o encaminhamento por papel após o login (Epics 2
e 5, quando as telas existirem).

**Nenhum arquivo que a story marcou como "não deve quebrar" foi tocado:** `erros.py`, `db.py`,
`usuario.py`, `saude.py`, `migrations/` e, no frontend, `layout.tsx`, `Masthead.tsx`, `NavLink.tsx`,
`page.tsx`, `not-found.tsx` e `globals.css` seguem intactos. O `main.py` recebeu só as duas linhas do
router, como previsto.

### File List

**Criados**

- `backend/app/core/seguranca.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/autenticacao.py`
- `backend/app/api/auth.py`
- `backend/tests/test_seguranca.py`
- `backend/tests/test_auth.py`
- `frontend/src/lib/api.ts`
- `frontend/src/app/(entrada)/login/page.tsx`
- `frontend/src/app/(entrada)/login/page.module.css`
- `frontend/src/app/(entrada)/layout.tsx`
- `frontend/src/app/(entrada)/layout.module.css`
- `frontend/src/app/(site)/layout.tsx`
- `frontend/src/components/FormularioLogin.tsx`
- `frontend/src/components/FormularioLogin.module.css`
- `frontend/src/components/Logotipo.tsx`
- `frontend/src/components/Logotipo.module.css`

**Movidos** (grupos de rotas — ver Completion Notes)

- `frontend/src/app/page.tsx` → `frontend/src/app/(site)/page.tsx`
- `frontend/src/app/page.module.css` → `frontend/src/app/(site)/page.module.css`

**Modificados**

- `backend/pyproject.toml` · `backend/uv.lock` · `backend/.env.example`
- `backend/app/core/config.py` · `backend/app/main.py`
- `backend/tests/test_config.py`
- `backend/README.md`
- `frontend/next.config.ts` · `frontend/.env.example`
- `frontend/src/app/layout.tsx` (virou só `<html><body>`)
- `frontend/src/app/not-found.tsx` (passou a montar a própria casca)
- `frontend/src/components/Masthead.tsx` · `frontend/src/components/Masthead.module.css`
  (logotipo extraído)
- `frontend/README.md`
- `README.md`
- `_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Removidos**

- `frontend/src/lib/.gitkeep` (a pasta deixou de estar vazia)

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Correção pós-conferência do Igor: a tela de acesso perdeu o masthead. Frontend partido em dois grupos de rotas — `(site)` com masthead, `(entrada)` só com a marca; layout raiz virou `<html><body>`; logotipo extraído para componente próprio; `not-found.tsx` passou a montar a própria casca (só a raiz de `app/` atende URL não casada). Decidido com o Igor: link de cadastro na Story 1.5, "Entrar" no masthead na Story 1.6, e a raiz continua pública |
| 2026-08-10 | Story 1.4 implementada. Backend: Argon2id, JWT em cookie `httpOnly` de 8h, `POST /auth/login` e `POST /auth/logout`, primeiro service e primeiro schema do projeto, `JWT_SECRET` recusado em produção quando é o valor de exemplo. Frontend: proxy `/api/*`, `src/lib/api.ts` com erro por `codigo`, tela `/login`. 40 testes passando. Os três READMEs e o `ARCHITECTURE-SPINE.md` (AD-15 + tabela Stack) atualizados |
| 2026-08-10 | Story 1.4 criada e contextualizada. Quatro decisões do Igor incorporadas: escopo backend + tela de login, PyJWT 2.13.0, proxy `/api/*` no Next em vez de `SameSite=None`, rota `/login`. Quatro ACs acrescentados aos quatro do `epics.md` (tela, acessibilidade do formulário, e-mail normalizado, segredo recusado em produção). Registrado o conflito entre `SameSite=Lax` e os dois domínios de deploy, que o `epics.md` cobrava na Story 1.9 sem ter dono |
