---
baseline_commit: "Story 1.8 — branch epic-1---fundacao-acesso-e-primeiro-deploy (o push dela dispara o deploy da Railway)"
---

# Story 1.9: Frontend no ar na Vercel

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **A story que fecha a epic.** A 1.8 pôs a API e o
banco na Railway; esta põe a interface na Vercel e liga as duas metades. Ao fim dela existe **uma
URL só** que alguém abre no navegador, entra com uma conta semeada e vê a `/conta` — sem clonar
repositório, sem Docker, sem `uv`.

Como a 1.8, o entregável principal não é código: é configuração num painel de fornecedor, mais a
documentação que a torna refazível. A divisão é a mesma — **o Igor** clica no painel da Vercel (e num
campo do painel da Railway), **o agente** verifica por HTTP o que subiu e escreve os READMEs a partir
do que foi executado.

A diferença desta para a anterior é o que está sendo provado. A 1.8 provou que *a API responde*.
Esta prova que **o cookie de sessão sobrevive entre dois fornecedores diferentes** — que é a única
coisa nova aqui, e a que a Story 1.4 já resolveu com o proxy `/api/*`. Se o login funcionar em
produção na primeira tentativa, é aquela decisão pagando; se falhar, o lugar de olhar é o
`API_URL`, nunca o código do cookie.

## Acceptance Criteria

1. **Given** o frontend publicado na Vercel
   **When** eu abro a URL pública **numa janela anônima**, sem conta na Vercel
   **Then** a raiz carrega com a identidade aplicada — fundo `#0E0D0C`, masthead com o fio duplo,
   serifada nos títulos e mono versalete nas etiquetas
   **And** a URL publicada é o **domínio de produção do projeto** (`<projeto>.vercel.app`), nunca a
   URL gerada por deploy (`<projeto>-<hash>-<escopo>.vercel.app`) — esta última fica atrás do login
   da Vercel pela proteção padrão, e quem avalia veria uma tela de autenticação em vez do site

2. **Given** o projeto na Vercel
   **When** eu inspeciono as configurações de build
   **Then** o **Root Directory** é `frontend`, o Framework Preset é **Next.js**, e nem Build Command
   nem Install Command foram sobrescritos — a Vercel usa `npm run build` e o `package-lock.json` que
   já estão no repositório
   **And** **não existe `vercel.json`** no repositório: a configuração mora no painel, pela mesma
   decisão registrada na Story 1.8 para a Railway

3. **Given** as variáveis de ambiente do projeto na Vercel
   **When** eu as inspeciono
   **Then** existe **`API_URL`** — sem o prefixo `NEXT_PUBLIC_` — apontando para
   `https://elite-dev-rockhub-production.up.railway.app`, **sem barra no fim**, marcada para
   **Production e Preview**
   **And** essa URL **não** aparece em nenhum arquivo versionado como valor efetivo: o
   `frontend/.env.example` continua com `localhost:8000`, que é o valor de desenvolvimento
   **And** nenhuma variável `NEXT_PUBLIC_` foi criada — não há nada para o navegador saber (AD-2)

4. **Given** a aplicação publicada
   **When** eu faço `POST` em `https://<vercel>/api/auth/login` com `organizador@rockhub.dev` /
   `rockhub123`
   **Then** responde `200` com `"papel": "ORGANIZADOR"` — o que só é possível se o proxy `/api/*`
   alcançou a Railway a partir do servidor da Vercel
   **And** o `Set-Cookie` volta pelo **domínio da Vercel**, com `HttpOnly`, `Secure`, `SameSite=Lax`
   e **sem atributo `Domain=`** (cookie de host, da origem do frontend)

5. **Given** a URL pública no navegador
   **When** eu percorro o ciclo de sessão inteiro
   **Then** entrar com uma conta semeada leva à raiz já logado, o masthead vira `Início` ·
   `Minha conta`, a `/conta` mostra nome, e-mail e papel, e `Sair` volta o masthead para `Entrar`
   **sem recarregar a página**
   **And** `/conta` sem sessão cai em `/login?voltar=%2Fconta` e devolve a `/conta` depois de entrar
   **And** na aba Network toda chamada sai para o **domínio da Vercel** em `/api/...`, nunca para
   `up.railway.app`
   **And** `document.cookie` no console **não** mostra `rockhub_sessao`

6. **Given** o backend na Railway
   **When** eu inspeciono `CORS_ORIGENS`
   **Then** ela vale `http://localhost:3000,https://<projeto>.vercel.app` — a origem publicada foi
   acrescentada, e o `localhost` continua lá para o desenvolvimento
   **And** o backend foi **redeployado** depois da mudança, porque `Settings` é lida uma vez por
   processo
   **And** os READMEs registram que **isso não é o que faz o login funcionar**: o navegador nunca
   fala com a Railway: quem fala é o servidor do Next. O `CORSMiddleware` é rede de proteção para
   chamada direta, não caminho de nada que exista hoje

7. **Given** a configuração de Git do projeto na Vercel
   **When** eu a inspeciono
   **Then** a **Production Branch** é `epic-1---fundacao-acesso-e-primeiro-deploy`, a mesma que a
   Railway acompanha — a Vercel assume `main` sozinha, e a `main` ainda não tem frontend nenhum
   **And** está escrito no README que trocar `API_URL` no painel **não** muda o proxy sem um
   redeploy: o `rewrites()` é avaliado no `next build` e o valor fica congelado na build

8. **Given** os três READMEs
   **When** eu os leio
   **Then** o `frontend/README.md` tem uma seção **Deploy na Vercel**, campo por campo, refazível
   numa conta vazia — do jeito que a Story 1.8 fez para a Railway
   **And** o `README.md` da raiz publica a URL do frontend, abre o *Roteiro de avaliação* pela URL
   pública (sem instalar nada), e registra as decisões desta story com a alternativa descartada
   **And** o `backend/README.md` registra a mudança do `CORS_ORIGENS` e por que ela não está no
   caminho do navegador
   **And** a linha **"Frontend publicado"** sai de *O que não está pronto* — ela deixou de ser
   verdade

9. **Given** o repositório ao fim desta story
   **When** eu comparo com o estado anterior
   **Then** **nenhuma linha de `frontend/src/`, `frontend/next.config.ts`, `backend/app/`,
   `migrations/`, `seeds/` ou `tests/` mudou**
   **And** não existe `vercel.json`, `Dockerfile`, `Procfile` nem workflow de CI novo
   **And** **nenhuma dependência nova** — nem `npm install`, nem `uv sync`. É a quinta story seguida
   **And** os 85 testes do backend continuam válidos sem alteração

10. **Given** a Epic 1 encerrada
    **When** eu abro a URL do frontend numa máquina que nunca viu este projeto
    **Then** dá para criar conta, entrar, ver a `/conta` e sair — o NFR3 (frontend na Vercel,
    backend e banco na Railway) está cumprido nas duas metades
    **And** o que ainda **não** dá para fazer por lá — descobrir evento, comprar, validar ingresso —
    está dito explicitamente em *O que não está pronto*, e não prometido pelo roteiro

> **De onde vem cada critério.** O `epics.md` traz **dois** blocos: a aplicação carrega com a
> identidade aplicada, e o login funciona contra a Railway com o cookie aceito entre os domínios.
> Eles viraram os ACs **1, 4 e 5**.
>
> **AC1 (segunda metade)** existe por causa da proteção de deploy da Vercel: no plano Hobby, a
> *Standard Protection* deixa o **domínio de produção** público mas **protege a URL gerada de cada
> deploy** — que é exatamente a URL que aparece em destaque na tela do deploy e a que se copia por
> reflexo. Publicar a errada nos READMEs põe quem avalia diante de um login da Vercel.
>
> **AC2, AC3 e AC7** são as três armadilhas de configuração, na ordem em que aparecem: `Root
> Directory` (o mesmo campo que fez o primeiro build da 1.8 falhar), a variável sem
> `NEXT_PUBLIC_` e sem barra final, e a branch de produção (o mesmo erro da 1.8, que apontou para
> `main` e construiu um commit de planejamento).
>
> **AC6** é a decisão do Igor desta story, com o cuidado de não deixar o README sugerir que o CORS é
> o que faz o login funcionar — porque não é, e escrever isso apagaria a razão de o proxy existir.
>
> **AC8 e AC10** são a NFR1, a NFR3 e a regra do `CLAUDE.md`. **AC9** é a fronteira: como na 1.8,
> código que aparecer aqui é sinal de que alguma coisa foi resolvida no lugar errado.

## Tasks / Subtasks

> **Ordem obrigatória.** T1 e T2 são do Igor e acontecem **antes** de tudo: sem a URL pública não há
> o que verificar na T3 nem o que documentar. O agente começa pela T3, com a URL em mãos.

- [x] **T1. Publicar o frontend na Vercel** — *executada pelo Igor, no painel* (AC: 1, 2, 3, 7)
  - [x] O passo a passo completo, campo por campo, está em *O painel da Vercel, campo por campo*
  - [x] ⚠️ **Três campos que não podem faltar**, na ordem em que a tela os pede: `Root Directory` =
        `frontend`, a variável `API_URL`, e a **Production Branch** apontando para a branch da epic
  - [x] Ao terminar, passe ao agente: o **domínio de produção** (`<projeto>.vercel.app`, o que
        aparece em Settings → Domains — **não** o link do deploy)
  - [x] Se o build falhar, mande o log — a leitura está em *Quando falhar, onde olhar*

- [x] **T2. Acrescentar a origem da Vercel ao `CORS_ORIGENS`** — *executada pelo Igor, no painel da
      Railway* (AC: 6)
  - [x] Variável `CORS_ORIGENS` = `http://localhost:3000,https://elite-dev-rock-hub.vercel.app`
  - [x] Separador vírgula sem espaço, forma canônica dos READMEs
  - [x] Sem barra no fim e sem caminho — origem é esquema + host
  - [x] **Redeploy do backend feito.** O primeiro valor salvo tinha o marcador `<projeto>` colado
        literalmente (`https://<projeto>.vercel.app`), e o preflight recusava por isso — corrigido
        para o domínio real e redeployado
  - [x] Nenhum `*` — preflight de origem não autorizada responde `400`, como deve

- [x] **T3. Verificar o que está no ar** (AC: 1, 4, 5)
  - [x] `curl -i https://elite-dev-rock-hub.vercel.app/` → `200`, e o HTML traz o masthead. Os nove
        tokens da identidade estão no CSS publicado (minificados em minúsculo: `#0e0d0c`, `#ede8dc`,
        `#f2a413`, `#2a2622`, `#d93b2b`, `#3fa96b`, mais `--breu`/`--cal`/`--ambar` e Georgia)
  - [x] `POST /api/auth/login` com as **quatro** credenciais semeadas → `200` com o papel de cada
        uma: Helena Marques/`ORGANIZADOR`, Bruno Tavares/`CLIENTE`, Marina Aoki/`CLIENTE`, Jonas
        Ribeiro/`PORTARIA`
  - [x] `Set-Cookie`: `HttpOnly; Max-Age=28800; Path=/; SameSite=lax; Secure` e **nenhum `Domain=`**
  - [x] `GET /api/auth/eu` **sem cookie** → `401 {"erro":{"codigo":"NAO_AUTENTICADO",…}}`
  - [x] `GET /rota-que-nao-existe` → `404` com o masthead no HTML — é o `not-found.tsx` da raiz
  - [x] ⚠️ A URL abre sem autenticação da Vercel: `200` na raiz, sem `Authentication Required` nem
        `_vercel_sso` no corpo. É o domínio de produção, não a URL gerada por deploy
  - [x] Conferência de navegador **feita pelo Igor em janela anônima**: entrar, masthead virar
        `Minha conta`, `/conta`, `Sair` e o masthead voltar **sem recarregar**, e a aba Network
        mostrando `/api/...` no domínio da Vercel
  - [x] ⚠️ Nenhuma conta foi criada pela URL de produção. Só login, que não escreve nada

- [x] **T4. `frontend/.env.example`** (AC: 3, 8)
  - [x] Bloco comentado **"Em produção (Vercel)"** ao fim, com `API_URL` em Production e Preview
  - [x] As três regras escritas: sem barra no fim, `https://` e não `http://`, sem `NEXT_PUBLIC_`
  - [x] O valor efetivo do arquivo continua `localhost:8000`

- [x] **T5. `frontend/README.md`** (AC: 7, 8)
  - [x] Seção **Deploy na Vercel** em cinco partes: o projeto, a variável, qual URL publicar, como
        saber que deu certo, e quando falhar onde olhar — mais *O que a Vercel faz com este projeto*
  - [x] Subseção **Qual URL publicar**, com a proteção de deploy do plano Hobby e a conferência em
        janela anônima
  - [x] O diagrama do proxy com os domínios reais, marcado como **verificado, não previsto**
  - [x] A frase "isso ainda não aconteceu" reescrita — aconteceu, e o valor mora no painel
  - [x] Seção **Histórico desta camada**, nova, com a entrada da Story 1.9 em primeira pessoa
  - [x] Subseção **E a mesma lista, em produção** na verificação manual

- [x] **T6. `README.md` da raiz** (AC: 8, 10)
  - [x] *Estado atual*: as duas metades no ar
  - [x] *No ar*: a URL do frontend em primeiro lugar; a da API abaixo, com a ressalva de que o
        navegador nunca fala com ela
  - [x] *Roteiro de avaliação*: bloco **Sem instalar nada** no topo, em 6 passos, e o roteiro local
        abaixo como *Na sua máquina*
  - [x] *Contas semeadas*: as quatro entram pela URL pública, conferidas
  - [x] *Stack e estrutura*: `Vercel (frontend) e Railway (API e banco) — as duas no ar`
  - [x] *Decisões*: **quatro** mexidas em vez de duas — a entrada da configuração no painel virou
        decisão das duas plataformas, mais três novas: `CORS_ORIGENS`, branch da epic publicada
        (com o Preview dentro) e o `.gitignore` que engolia `src/lib/`
  - [x] *O que não está pronto*: "Frontend publicado" removida; entraram Preview escrevendo no banco
        de produção, ausência de domínio próprio e a branch divergente da `main`
  - [x] Primeira pessoa em tudo

- [x] **T7. `backend/README.md`** (AC: 6, 8)
  - [x] `CORS_ORIGENS` na tabela de variáveis, com o valor real
  - [x] Subseção **Por que essa variável não é o que faz o login funcionar**, com o diagrama das
        duas setas e o `curl` de preflight para conferir de fora
  - [x] Entrada **Story 1.9** no *Histórico desta camada*: nenhuma linha alterada, o que mudou foi
        uma variável no painel
  - [x] Nenhuma mudança inventada

- [x] **T8. Verificação** (AC: todos)
  - [x] `vercel.json`, `Dockerfile`, `Procfile`, `.github/`, `middleware.ts` → **zero**
  - [x] Busca por `vercel` em `frontend/src/`, `frontend/next.config.ts` e `backend/app/` → **zero**
  - [x] `frontend/.env.example` continua com `localhost:8000` como valor efetivo
  - [x] Nenhum arquivo de `frontend/src/`, `backend/app/`, `migrations/`, `seeds/` ou `tests/`
        alterado. **Cinco** arquivos em vez de quatro — o `.gitignore` entrou (ver Completion Notes)
  - [x] `npm run build` local não foi rodado — o Igor não pediu, e o build da Vercel já provou
  - [x] **85 testes do backend passando** (`uv run pytest -q` → `85 passed in 7.50s`)
  - [x] Os três READMEs atualizados

- [x] **T9. Documentação** — coberta por T4, T5, T6 e T7 (obrigatório — regra do projeto)

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T6).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| `CORS_ORIGENS` na Railway | **Acrescentar a origem da Vercel**, ao lado do `localhost:3000` | *Manter só o `localhost`*: é a verdade técnica — desde o proxy da 1.4 o navegador não fala com a Railway, então a variável não participa de nada que exista hoje, e mexer nela custa um redeploy do backend por um efeito nulo. Caiu porque o AC do `epics.md` pede "CORS e `SameSite` configurados" com todas as letras, e porque a origem publicada existir na lista é o estado correto do sistema: no dia em que qualquer coisa chamar a API direto — um `curl` de demonstração, uma página futura sem proxy — a resposta certa já está configurada, em vez de virar meia hora de depuração. **O README precisa dizer que não é isso que faz o login funcionar**, senão a explicação do proxy se perde |
| Branch publicada na Vercel | **A branch da epic**, `epic-1---fundacao-acesso-e-primeiro-deploy`, igual à Railway | *Fazer o merge na `main` antes e publicar a `main`*: é o que a Vercel assume sozinha, é o que quem avalia espera, e acabaria com o campo divergente nos dois painéis. Caiu por ordem de eventos — o merge da Epic 1 acontece **depois** do code review da epic, e esta story é a última antes dele. Publicar da `main` hoje significaria mesclar código ainda não revisado só para conseguir fazer deploy. O custo assumido: um campo para trocar em dois painéis quando a epic entrar na `main`, e isso fica escrito nos dois READMEs |
| `API_URL` nos deploys de Preview | **Production e Preview, mesmo valor** | *Só em Production*: manteria o banco de produção fora do alcance de qualquer build de branch. Caiu porque o Preview cairia no padrão `http://localhost:8000` do `next.config.ts` e ficaria com o login quebrado **sem erro visível** — a tela abre, o formulário envia, e nada acontece. Preview quebrado é pior que Preview inexistente. *Desligar os deploys de branch*: resolveria pelo outro lado, ao custo de perder a pré-visualização das próximas epics. **A consequência assumida** — Preview escreve no banco de produção — vai para *O que não está pronto*, e é mitigada por os Previews ficarem atrás do login da Vercel no plano Hobby |

**Duas suposições declaradas, não decisões suas** — uma linha para trocar se discordar:

- **Nenhum `engines.node` no `package.json`.** O padrão da Vercel hoje é Node **24.x**, que é o que a
  sua máquina roda (v24.14.0) e satisfaz o piso do Next 16 (≥ 20.9). Fixar a versão seria a escolha
  rigorosa, e é uma linha de código num commit que não tem por que ter código
- **Domínio próprio fica de fora.** `<projeto>.vercel.app` é suficiente para avaliação, e domínio
  custa dinheiro e propagação de DNS

### O painel da Vercel, campo por campo

Esta seção é a matéria-prima da T5: ela vai para o `frontend/README.md` quase como está.

#### 1 · O projeto

| Onde | Campo | Valor |
|---|---|---|
| `Add New` → `Project` | Import Git Repository | `elite-dev-RockHub` |
| Configure Project | **Root Directory** | `frontend` |
| Configure Project | Framework Preset | **Next.js** (detectado sozinho depois do Root Directory) |
| Configure Project | Build / Output / Install Command | **não sobrescreva nenhum** |
| Settings → Environments → Production Branch | Branch | `epic-1---fundacao-acesso-e-primeiro-deploy` |

⚠️ **O `Root Directory` é o mesmo passo que derrubou o primeiro build da 1.8.** Sem ele a Vercel
olha a raiz do monorepo, não encontra `package.json`, não detecta framework nenhum e cai em "Other" —
o build ou falha ou publica uma pasta vazia. Com `frontend`, o Framework Preset vira Next.js sozinho
e o `npm run build` e o `package-lock.json` que já estão versionados são usados sem sobrescrita.

⚠️ **A Production Branch precisa ser trocada.** A Vercel escolhe, nesta ordem: `main`, `master`, a
branch padrão do repositório. A `main` deste repositório ainda não tem frontend nenhum — publicar
dali é um build sem `frontend/package.json`, exatamente o sintoma que a Railway deu na 1.8. Se você
importar o projeto estando na `main`, o primeiro deploy vai falhar; troque a branch e faça um
redeploy.

#### 2 · A variável

| Variável | Valor | Ambientes |
|---|---|---|
| `API_URL` | `https://elite-dev-rockhub-production.up.railway.app` | **Production** e **Preview** |

Três detalhes que sustentam esse valor:

- **Sem `NEXT_PUBLIC_`.** Quem lê `API_URL` é o servidor: o `rewrites()` do `next.config.ts` e o
  `fetch` do `sessao.ts`. Com o prefixo, a variável iria embutida no bundle do navegador sem
  necessidade nenhuma — e o nome que os dois arquivos leem é `API_URL`, sem prefixo, desde a 1.4
- **`https://`, nunca `http://`.** A Railway responde `301` em HTTP, e um `POST` redirecionado perde
  o corpo em vários clientes. O sintoma é o login falhando só em produção
- **Sem barra no fim.** O rewrite concatena `${API_URL}/:caminho*`; com barra vira
  `https://…app//auth/login`, e o roteador do FastAPI não casa esse caminho

⚠️ **Defina a variável antes do primeiro deploy** — ou faça um redeploy depois de defini-la. O
`rewrites()` é avaliado no `next build`, e o valor fica **congelado na build**. Trocar a variável no
painel depois não muda o proxy até o próximo deploy: o sintoma é o frontend novo falando com a API
antiga, e não há nada no log acusando.

#### 3 · O domínio

Settings → **Domains**. O domínio de produção é `<projeto>.vercel.app` — algo como
`elite-dev-rockhub.vercel.app`. **É essa URL que vai para os READMEs.**

⚠️ **Não copie a URL da tela do deploy.** A Vercel gera, por deploy, uma URL do tipo
`<projeto>-<hash>-<escopo>.vercel.app`, e é ela que aparece em destaque quando o build termina. No
plano Hobby a proteção padrão (*Vercel Authentication* + *Standard Protection*) deixa o **domínio de
produção público** e **protege as URLs geradas** — quem abrir a errada vê uma tela de login da
Vercel. A conferência é abrir a URL numa **janela anônima**: se pedir login, é a URL errada.

#### 4 · O outro painel: a Railway

Uma variável, no serviço do backend:

| Variável | De | Para |
|---|---|---|
| `CORS_ORIGENS` | *(ausente — valia o padrão `http://localhost:3000`)* | `http://localhost:3000,https://<projeto>.vercel.app` |

E **redeploy do backend** depois de salvar: a `Settings` é `@lru_cache` e nasce junto com o processo.

#### 5 · A conferência

Com o deploy verde, três coisas, nesta ordem — a segunda é a que vale:

1. A raiz abre em janela anônima, com fundo escuro e o masthead
2. `POST /api/auth/login` no domínio da Vercel devolve `200` e um `Set-Cookie` com `Secure`
3. No navegador: entrar, `/conta`, `Sair`, e o masthead mudando sem recarregar

### Quando falhar, onde olhar

Em ordem de probabilidade, com o sintoma que cada uma produz:

1. **Build falha em "No framework detected" ou não acha `package.json`.** Falta o `Root Directory =
   frontend`. É o item nº 1 porque foi exatamente o que aconteceu na 1.8
2. **Build verde, mas o site é de um commit velho — ou o build falha citando a raiz do repositório.**
   A Production Branch ainda é `main`
3. **A URL pede login da Vercel.** É a URL gerada por deploy, não o domínio de produção
4. **A tela abre, o login envia e nada acontece; o Network mostra `500` ou `502` em
   `/api/auth/login`.** O `API_URL` não existe, tem `http://` em vez de `https://`, tem barra no
   fim, ou foi definido **depois** do build. Nos quatro casos, o conserto termina em **redeploy**
5. **Login responde `200` mas a página continua deslogada.** O cookie não foi aceito. Confira se o
   `Set-Cookie` tem `Secure` (vem do `AMBIENTE=producao` da 1.8) e se **não** tem `Domain=`
6. **`404` do Next sem a identidade do projeto.** O `not-found.tsx` não subiu — ou alguém o moveu
   para dentro de `(site)`, que é o erro documentado na 1.2
7. **Preview quebrado com Production funcionando.** A variável foi marcada só para Production
8. **Push que só mexe em `backend/` não gera deploy do frontend.** É o *Skip deployment* de monorepo
   funcionando como deveria, não um defeito

### O que já existe e esta story reusa — não reescreva nada disto

| O que | Onde | Por que importa hoje |
|---|---|---|
| Proxy `/api/:caminho*` | `frontend/next.config.ts` | **É a story inteira.** Foi escrito na 1.4 exatamente para este dia |
| `process.env.API_URL` no servidor | `next.config.ts` + `src/lib/sessao.ts` | Os dois leem a **mesma** variável, sem prefixo. Nada mais precisa saber o endereço |
| `chamarApi` com caminho relativo | `src/lib/api.ts` | Todo `fetch` do navegador é `/api/...` — nenhum componente monta URL de backend |
| Cookie repassado à mão no servidor | `src/lib/sessao.ts` | O `fetch` do servidor não herda cookie; já está resolvido |
| `cookie_secure` derivado de `AMBIENTE` | `backend/app/core/config.py` | Já vale `producao` na Railway desde a 1.8 — o `Secure` chega de graça |
| `_separar_por_virgula` do `CORS_ORIGENS` | `backend/app/core/config.py` | É o que faz a variável aceitar `a,b` do jeito que se digita num painel |
| `not-found.tsx` na raiz de `app/` | `frontend/src/app/` | O 404 com a casca do projeto, que a T3 confere em produção |
| `.gitignore` com `.vercel` e `.next/` | raiz | Já pronto desde a 1.2 — nada de artefato de deploy entrando no repositório |

**Não devem ser tocados, e não devem quebrar:** `frontend/src/` **inteiro**, `frontend/next.config.ts`,
`frontend/package.json`, `frontend/package-lock.json`, `backend/` **inteiro** (`app/`, `migrations/`,
`seeds/`, `tests/`, `pyproject.toml`, `uv.lock`), `docker-compose.yml` e `docker/`. Os arquivos que
mudam são quatro, e são de documentação: `frontend/.env.example`, `frontend/README.md`, `README.md`
da raiz e `backend/README.md`.

Se algum arquivo de `src/` precisar mudar para o deploy funcionar, algo foi resolvido no lugar
errado — o lugar é o painel.

### O que a Vercel faz com este projeto

Lido na documentação da plataforma, não deduzido:

| Fase | O que acontece |
|---|---|
| Clone | `git clone --depth=10` da Production Branch — histórico raso, sem efeito aqui |
| Root Directory | `frontend` vira a raiz do build; nada fora dela é acessível, e `..` não é permitido |
| Detecção | Encontra `frontend/package.json` → Framework Preset **Next.js** |
| Install | Detecta o gerenciador pelo `package-lock.json` → **npm** |
| Build | `npm run build` (o script `build` do `package.json`), com Turbopack, que é o padrão do Next 16 |
| Node | **24.x**, o LTS padrão para projeto novo. Sem `engines.node`, é o que vale |
| Variáveis | `API_URL` está disponível **no build** e **em execução** — o `rewrites()` a lê no build, o `sessao.ts` a lê em execução |
| Output | Automático para Next.js — nada a configurar |

Três consequências que valem para esta story:

- **A mudança de variável só vale para deploys novos.** A documentação é literal: *"Any change you
  make to environment variables are not applied to previous deployments"*. Somado ao `rewrites()`
  congelado no build, dá a regra prática: **mexeu no `API_URL`, redeploy**
- **`devDependencies` são instaladas no build** — é assim que `typescript` e os `@types` entram no
  `next build`. Não tente excluí-las
- **Preview é branch que não é a de produção.** Com a variável marcada para Preview, cada branch
  nova ganha um site funcional apontando para a API de produção

### Por que o CORS não é o que resolve isto

Vale escrever com clareza, porque é a explicação que quem lê o AC vai procurar.

O caminho da requisição em produção é:

```
navegador ──► <projeto>.vercel.app/api/auth/login        (mesma origem: sem CORS)
                    │  rewrite do next.config.ts, no servidor da Vercel
                    ▼
              elite-dev-rockhub-production.up.railway.app/auth/login   (servidor↔servidor: sem CORS)

o Set-Cookie volta pelo domínio da Vercel → cookie de host, próprio → SameSite=Lax funciona
```

CORS é uma política **do navegador** sobre requisição que ele mesmo faz para outra origem. Nenhuma
das duas setas é isso: a primeira é mesma origem, a segunda não passa por navegador nenhum. Por isso
o `CORS_ORIGENS` novo **não muda nada no caminho do login** — ele é a resposta correta para uma
chamada direta que hoje não existe.

O que **de fato** faz o cookie funcionar entre os dois fornecedores é o proxy da Story 1.4, e o
motivo está no AD-15: `vercel.app` e `up.railway.app` estão os dois na *Public Suffix List*, então
são sites diferentes para o navegador, e um cookie `SameSite=Lax` não sobrevive ao cruzamento. Sem o
proxy, a saída seria `SameSite=None`, que exige `Secure` e entrega o cookie em requisição de
terceiros — **essa discussão está encerrada, e o `ARCHITECTURE-SPINE.md#AD-15` diz para não
reabri-la nesta story.**

### Armadilhas específicas desta story

1. **Esquecer o `Root Directory`.** A primeira, a mais provável, e a que já custou um build vermelho
   na 1.8. Monorepo com duas linguagens: sem ele, o build é loteria
2. **Deixar a Production Branch em `main`.** Mesmo erro da 1.8, mesmo sintoma
3. **Publicar a URL gerada por deploy.** Ela pede login da Vercel. Confira em janela anônima **antes**
   de escrever qualquer README
4. **Definir `API_URL` depois do primeiro build.** O rewrite fica congelado; sem redeploy, nada muda
5. **Barra no fim do `API_URL`, ou `http://` em vez de `https://`.** Os dois produzem falha só no
   login, só em produção
6. **Escrever `NEXT_PUBLIC_API_URL`** por hábito. Ninguém lê essa variável desde a 1.4 — o valor
   simplesmente não chega, e o proxy cai no padrão `localhost:8000`
7. **Achar que o `CORS_ORIGENS` é o conserto** quando o login falhar. Ele não está no caminho. O
   lugar de olhar é o `API_URL` e o redeploy
8. **Criar `vercel.json` "porque não custa nada".** Custa: duas fontes para a mesma configuração, e
   o painel vence quando alguém edita por lá. É a mesma decisão da 1.8
9. **Mexer em `src/` para "adaptar à produção".** Não há nada a adaptar: o código já foi escrito para
   este dia. Vontade de mexer aqui é sintoma de configuração errada
10. **Prometer no roteiro o que a URL não faz.** Não há evento, compra nem portaria publicados — a
    Epic 2 é quem começa isso. Roteiro que promete tela inexistente é pior que roteiro curto

### Convenções que esta story confirma

- **Configuração de plataforma mora na plataforma, e o README a descreve** — firmada na 1.8 para a
  Railway, agora aplicada à Vercel com a mesma forma e o mesmo nível de detalhe. Duas plataformas,
  uma convenção
- **Endereço de outro serviço é variável de ambiente, nunca literal no código**
- **Documentação de deploy é escrita a partir do que foi executado**, nunca do que se pretendia
- **URL publicada é conferida em janela anônima antes de entrar no README**
- **README que ficou desatualizado é corrigido na story que o desatualizou** — a frase "isso ainda
  não aconteceu" do `frontend/README.md` é desta story para arrumar

### Estrutura alvo ao fim desta story

```text
frontend/
  .env.example              # +bloco comentado "Em produção (Vercel)"
  README.md                 # +Deploy na Vercel, +qual URL publicar, proxy verificado, +histórico
README.md                   # +URL do frontend, roteiro pela URL pública, 2 decisões, limitações
backend/README.md           # CORS_ORIGENS com valor de produção + por que não é o que resolve
```

Quatro arquivos, todos de documentação. `src/` e `app/` não aparecem — é a terceira story seguida em
que nenhuma linha de código de aplicação muda.

Não existe, e não deve passar a existir: `vercel.json`, `frontend/Dockerfile`, `.github/workflows/`,
`frontend/middleware.ts`. O último tem motivo próprio: a guarda de rota mora na página por decisão da
Story 1.6, e "middleware para redirecionar em produção" é a tentação clássica de quem acabou de
publicar.

[Fonte: ARCHITECTURE-SPINE.md#Implantação — Navegador → Vercel → Railway → Postgres]

### Comandos que esta story precisa deixar funcionando

Na Vercel, configurados no painel (você não roda nenhum):

```
Root Directory: frontend
Build Command:  npm run build      (detectado, não sobrescrito)
API_URL:        https://elite-dev-rockhub-production.up.railway.app
```

Na sua máquina, para verificar o que está no ar:

```bash
curl -i https://<projeto>.vercel.app/

curl -i -X POST https://<projeto>.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

⚠️ **No PowerShell, `curl` é apelido de `Invoke-WebRequest`** e não entende `-i` nem `-d` — use
`curl.exe` explicitamente, ou rode pelo Git Bash. É atrito de dois minutos que parece falha de
deploy.

O desenvolvimento local segue **exatamente igual**: `docker compose up -d`, backend em `:8000`,
`npm run dev` em `:3000` com o `.env.local` apontando para `localhost:8000`. Esta story não muda um
passo sequer disso — dois jeitos de rodar o mesmo projeto é como eles divergem.

Nada de `npm install` nem de `uv sync`: **nenhuma dependência nova**. É a quinta story seguida.

### Escopo — o que NÃO fazer aqui

Qualquer funcionalidade nova · CI, GitHub Actions, teste rodando no deploy (**nenhuma story**) ·
domínio próprio, analytics, Speed Insights, observabilidade (**fora do escopo do projeto**) ·
alterar `frontend/src/`, `next.config.ts` ou qualquer coisa de `backend/app/` · reabrir a decisão do
proxy `/api/*` (AD-15).

Cinco tentações concretas desta story:

- **"Já que estou publicando, ligo o Vercel Analytics / Speed Insights."** É dependência nova e um
  script no cliente, numa story que não muda código
- **"Ponho um `middleware.ts` para proteger rota em produção."** A guarda mora na página desde a 1.6,
  e middleware exigiria o `JWT_SECRET` na Vercel — contra o AD-2
- **"Crio o `vercel.json` para deixar a configuração no repositório."** Decidido e descartado, com o
  motivo escrito
- **"Aproveito e ponho a URL da Vercel no `.env.example`."** Não: aquele arquivo é o valor de
  desenvolvimento. O bloco comentado diz que a de produção existe e onde ela mora
- **"Já que a Epic 1 acabou, começo a 2.1."** Não emende. O code review da epic vem antes

### Testing

**Nenhum teste novo, e nenhum teste alterado** — nem no backend, nem no frontend (que não tem suíte,
por decisão registrada no `frontend/README.md#sobre-não-ter-teste-automatizado-aqui`).

O que substitui é a **verificação por HTTP contra a URL pública**, mais a conferência no navegador —
que aqui pesa mais que na 1.8, porque parte do que esta story prova só existe no navegador:

| O que a verificação prova | AC | Quem faz |
|---|---|---|
| `GET /` → `200` com a identidade no HTML | 1 | agente (`curl`) |
| A URL abre sem login da Vercel | 1 | agente (`curl`) + Igor (janela anônima) |
| `POST /api/auth/login` → `200` com o papel certo | 4 | agente (`curl`) |
| ↳ ...o que só é possível se o build leu `API_URL` **e** o proxy alcançou a Railway **e** o banco de lá respondeu | 2, 3, 7 | — |
| `Set-Cookie` com `Secure`, `HttpOnly`, `SameSite=lax`, sem `Domain=` | 4 | agente (`curl`) |
| `GET /api/auth/eu` sem cookie → `401 NAO_AUTENTICADO` | 4 | agente (`curl`) |
| Rota inexistente → `404` com a casca do projeto | 1 | agente (`curl`) |
| Masthead mudando ao entrar e ao sair, **sem recarregar** | 5 | **só Igor** — é o `router.refresh()`, e não há teste que o cubra |
| Network mostrando `/api/...` no domínio da Vercel | 5 | **só Igor** |
| `document.cookie` sem o `rockhub_sessao` | 5 | **só Igor** |

⚠️ **Não escreva teste que fale com a URL de produção.** Dependeria de rede e do estado do banco de
produção, falharia em avaliação offline e gravaria dado real. A verificação de deploy é manual e fica
registrada nas notas do agente; ela não vira suíte. É a mesma regra da 1.8.

**Os 85 testes do backend continuam válidos sem alteração** — nenhum arquivo `.py` muda.

### Inteligência das stories anteriores

**Da 1.8 (a story imediatamente anterior — leia estas antes de tudo):**

- **O primeiro build falhou por falta de `Root Directory`**, e o log não apontava a causa: ele
  listava a raiz do monorepo. A Vercel tem o mesmo campo e a mesma armadilha
- **A Railway assumiu a branch padrão do repositório** (`main`, sem backend) e construiu um commit de
  planejamento. A Vercel faz igual — `main`, depois `master`, depois a padrão
- **A configuração mora no painel, e o README a descreve campo por campo.** A seção *Deploy na
  Railway* do `backend/README.md` é o modelo literal da seção que a T5 escreve
- **`AMBIENTE=producao` já vale na Railway**, então o cookie já volta com `Secure`. Esta story não
  precisa configurar nada disso — só provar que chega
- **A API está em `https://elite-dev-rockhub-production.up.railway.app`**, verificada por HTTP, com
  as quatro contas semeadas entrando

**Da 1.4 (login e proxy), e é a mais importante para hoje:**

- **O proxy `/api/*` foi escrito exatamente para este cenário.** O `next.config.ts` já está pronto;
  esta story só dá a ele o endereço de produção
- **`API_URL` perdeu o `NEXT_PUBLIC_` nessa story**, de propósito, e os dois arquivos que a leem
  (`next.config.ts` e `sessao.ts`) usam o nome sem prefixo
- **O `rewrites()` é avaliado em tempo de build** — está escrito em comentário no próprio
  `next.config.ts` e no `frontend/README.md`, com o aviso de que "custa uma tarde na Story 1.9".
  Este é o dia

**Da 1.6 (ciclo de sessão):**

- **`router.refresh()` depois de toda mudança de sessão**, em três lugares. É a verificação que não
  tem substituto automatizado, e agora precisa ser conferida também em produção
- **A guarda mora na página, não em `middleware`** — e um dos motivos era não pôr o `JWT_SECRET` no
  ambiente da Vercel. Esta story é onde esse ambiente passa a existir de verdade
- **Todas as rotas ficaram dinâmicas** (`ƒ` no build), e está certo: o masthead lê `cookies()`

**Da 1.2 (casca do frontend):**

- **`.gitignore` da raiz já cobre `.vercel`, `.next/` e `*.tsbuildinfo`** — nada de artefato de deploy
  entrando no repositório
- **O `not-found.tsx` fica na raiz de `app/` e monta a própria casca.** Se o 404 de produção vier sem
  identidade, é isso que quebrou
- **Nenhuma fonte externa, nenhuma biblioteca de componentes** — o build da Vercel não busca nada na
  rede além do `npm install`

**Do estado do repositório:** branch `epic-1---fundacao-acesso-e-primeiro-deploy`, com as Stories 1.1
a 1.7 commitadas (`bbc9916` é a 1.7) e a **1.8 pronta para commit** — o push dela dispara o deploy da
Railway que imprime as quatro linhas `mantida` no log do Pre-deploy. As oito stories anteriores estão
em `review`: o code review é ao fim da epic, e **esta é a última**. 85 testes passando no backend,
nenhum no frontend.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-8-*.md]

### Stack desta story

**Nenhuma dependência nova.** O que esta story precisa saber é sobre a plataforma:

| O que | Versão / estado | Onde importa |
|---|---|---|
| Vercel | plataforma, plano Hobby | Root Directory, variável, Production Branch, proteção de deploy |
| Next.js | 16.3.0 (lockfile) | `rewrites()` avaliado no build; Turbopack padrão |
| React | 19.2.8 (lockfile) | — |
| Node na Vercel | **24.x**, o LTS padrão para projeto novo | Bate com a máquina do Igor (v24.14.0); Next 16 exige ≥ 20.9 |
| npm | detectado pelo `package-lock.json` versionado | Não troque por pnpm/yarn |
| FastAPI na Railway | no ar desde a 1.8 | O destino do proxy |

[Fonte: ARCHITECTURE-SPINE.md#Stack, #Implantação · vercel.com/docs/builds/configure-a-build ·
vercel.com/docs/environment-variables · vercel.com/docs/deployment-protection ·
vercel.com/docs/functions/runtimes/node-js/node-js-versions]

### Project Structure Notes

Como na 1.8, o entregável principal **não está no repositório** — está numa conta de fornecedor, e o
repositório recebe a documentação daquilo. A defesa contra o descompasso é a mesma: T1 e T2 (painéis)
primeiro, T3 verifica por HTTP o que de fato subiu, e só então T5 a T7 escrevem os READMEs **a partir
do que foi executado**.

Há uma assimetria nova, e ela é o risco desta story: **parte do que precisa ser provado só existe no
navegador**. O `curl` prova que o proxy alcança a Railway e que o cookie volta com os atributos
certos; ele não prova que o masthead troca ao sair, nem que a chamada saiu para o domínio da Vercel e
não para a Railway. Esses três itens são do Igor, estão marcados como tal na T3 e na tabela de
verificação, e **não devem ser dados por feitos pelo agente**.

A segunda característica é a mesma da anterior: o agente **não tem acesso ao painel da Vercel nem ao
da Railway** e não deve fingir que tem — não cria projeto, não cola variável, não gera domínio, não
pede credencial e não sugere caminho por CLI autenticada. Se a story parecer bloqueada, o desbloqueio
é o Igor executar T1 e T2 e passar a URL.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.9] — os dois blocos de AC originais:
  identidade aplicada na URL pública, e login contra a Railway com o cookie aceito entre os domínios
- [Source: _bmad-output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR3 (frontend na
  Vercel, backend e banco na Railway, vale +1 ponto), NFR1 e NFR8
- [Source: ARCHITECTURE-SPINE.md#Implantação] — Navegador → Vercel → Railway → Postgres
- [Source: ARCHITECTURE-SPINE.md#AD-15] — cookie `httpOnly`/`Secure`/`SameSite=Lax` de 8 horas, e a
  nota de que "as Stories 1.8 e 1.9 herdam isso pronto — não reabram a discussão"
- [Source: ARCHITECTURE-SPINE.md#AD-2] — segredo só no ambiente do backend; nada de credencial na
  Vercel
- [Source: _bmad-output/implementation-artifacts/1-8-backend-e-banco-no-ar-na-railway.md] — o deploy
  da API, as duas causas do primeiro build vermelho, e o modelo da seção de README
- [Source: frontend/next.config.ts] — `const destinoDaApi = process.env.API_URL ?? "http://localhost:8000"`
  e o comentário sobre tempo de build
- [Source: frontend/src/lib/sessao.ts] — a mesma variável, lida em execução, com o cookie repassado
- [Source: frontend/README.md#o-proxy-api] — o diagrama, o motivo (Public Suffix List) e o aviso
  "custa uma tarde na Story 1.9"
- [Source: backend/app/core/config.py] — `cors_origens` com `NoDecode` + separação por vírgula;
  `cookie_secure` derivado de `AMBIENTE`
- [Source: README.md#decisões-por-que-isso-e-não-aquilo] — onde as duas decisões desta story entram,
  e o modelo das três da 1.8
- [Source: vercel.com/docs/builds/configure-a-build] — Root Directory, Framework Preset, Install
  Command detectado, e o aviso de que a mudança vale no próximo deploy
- [Source: vercel.com/docs/environment-variables] — escopo Production/Preview/Development, e
  "changes to environment variables are not applied to previous deployments"
- [Source: vercel.com/docs/deployment-protection] — Hobby: *Standard Protection* protege as URLs de
  deploy e deixa o domínio de produção público
- [Source: vercel.com/kb/guide/can-i-use-a-non-default-branch-for-production] — Production Branch:
  `main`, senão `master`, senão a branch padrão
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Não há `npm install` nem `uv sync` nesta story.** `npm run build` local só se o Igor pedir
3. **Atualize os três READMEs antes de dar a story por concluída.** As duas entradas de decisão da T6
   são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As três desta story já estão respondidas. Se aparecer uma quarta
   — domínio próprio, analytics, plano pago, merge na `main` — pergunte em vez de escolher
5. **O agente não mexe em painel de fornecedor.** Nem Vercel, nem Railway. Nem pede credencial, nem
   sugere caminho por CLI autenticada. T1 e T2 são do Igor
6. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
7. **Esta é a última story da Epic 1.** Ao terminar, o próximo passo é o **code review da epic**
   (`bmad-code-review`), não a Story 2.1. Não emende

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m]

### Debug Log References

Verificação por HTTP contra `https://elite-dev-rock-hub.vercel.app`, em 2026-08-11:

| Verificação | Resultado |
|---|---|
| `GET /` | `200`, `X-Powered-By: Next.js`, HTML com o masthead. Sem `Authentication Required` |
| Tokens da identidade no CSS publicado | Os nove presentes (`#0e0d0c`, `#ede8dc`, `#f2a413`, `#2a2622`, `#d93b2b`, `#3fa96b`, `--breu`…`--verde`, Georgia) |
| `POST /api/auth/login` × 4 contas | `200` nas quatro, com nome e papel corretos |
| `Set-Cookie` | `HttpOnly; Max-Age=28800; Path=/; SameSite=lax; Secure` — **sem `Domain=`** |
| `GET /api/auth/eu` sem cookie | `401 NAO_AUTENTICADO` |
| `GET /rota-que-nao-existe` | `404` com o masthead — `not-found.tsx` da raiz |
| `OPTIONS /auth/login` na Railway, `Origin` da Vercel | `200` com `access-control-allow-origin: https://elite-dev-rock-hub.vercel.app` ✅ *(antes da correção: `400` sem o cabeçalho)* |
| `OPTIONS /auth/login`, `Origin: http://localhost:3000` | `200` com `access-control-allow-origin` ecoado |
| `OPTIONS /auth/login`, `Origin: https://exemplo.com` | `400` — origem não autorizada recusada, sem curinga |
| `POST /api/auth/login` **depois** do redeploy do backend | `200`, `Set-Cookie` intacto — o redeploy não regrediu nada |
| `uv run pytest -q` | `85 passed in 7.50s` |

**Build vermelho nº 1** — Production Branch em `main` e `Root Directory` em `./`. Esperado; as duas
armadilhas estavam previstas nas Dev Notes por terem acontecido na Story 1.8, no painel da Railway.

**Build vermelho nº 2** — `Module not found` em sete arquivos, com o `Root Directory` e a branch já
corretos. Diagnóstico pelo rastro de import: `BotaoSair.tsx:7`, `FormularioCadastro.tsx:9`,
`FormularioLogin.tsx:9`, `(entrada)/cadastro/page.tsx:4`, `(entrada)/login/page.tsx:4`,
`(site)/conta/page.tsx:4` e `Masthead.tsx:1` — **os sete importam de `@/lib`, e nenhum import de
`@/components` aparecia**. Causa: `.gitignore:17` trazia `lib/` do template Python do GitHub, e
padrão sem barra inicial casa em qualquer profundidade → `frontend/src/lib/` nunca foi versionado.

### Completion Notes List

**A story provou o que se propôs a provar.** O cookie de sessão atravessa Vercel → Railway sem
ajuste nenhum de código, e o proxy `/api/*` escrito na Story 1.4 funcionou de primeira assim que o
build ficou correto. Nenhuma linha de `frontend/src/`, `frontend/next.config.ts`, `backend/app/`,
`migrations/`, `seeds/` ou `tests/` foi editada — a quinta story seguida sem dependência nova.

**Dois desvios do escopo previsto, ambos para registro:**

1. **Cinco arquivos em vez de quatro.** O `.gitignore` da raiz entrou. Não é mudança de escopo por
   conveniência: sem ela o deploy é impossível, porque `frontend/src/lib/` nunca esteve no
   repositório. O AC9 pede que nenhuma linha de `frontend/src/` mude, e isso continua verdadeiro —
   os três arquivos de `src/lib/` passaram a ser **rastreados**, não editados. A decisão de ancorar
   `/lib/` em vez de abrir exceção com `!frontend/src/lib/` foi do Igor, e está no README da raiz com
   a alternativa descartada.
2. **Quatro entradas de decisão no README da raiz, não duas.** A entrada existente sobre
   configuração no painel foi ampliada para as duas plataformas (em vez de criar uma segunda
   quase idêntica), e entraram três novas: `CORS_ORIGENS`, branch da epic publicada com o Preview
   dentro, e o `.gitignore`.

**A descoberta que vale mais que o deploy:** o bug do `.gitignore` estava latente desde a Story 1.2 e
**nenhuma verificação local podia encontrá-lo** — `npm run build`, `tsc --noEmit`, ESLint e os 85
testes do backend passam todos, porque os arquivos existem no disco. Só um clone limpo revela, e o
primeiro clone limpo deste projeto foi o da Vercel. É o argumento concreto a favor de publicar cedo,
e está registrado nos três READMEs.

**O terceiro tropeço, e ele não estava previsto em lugar nenhum: um marcador de posição colado como
valor.** O `CORS_ORIGENS` foi salvo na Railway como
`http://localhost:3000,https://<projeto>.vercel.app` — com o `<projeto>` literal, do jeito que a
story o escreve para ser substituído. O preflight recusava a origem da Vercel enquanto o painel
mostrava uma variável de aparência correta, e a metade `localhost` continuava funcionando, o que
tornava o sintoma ainda mais confuso. Foi encontrado porque o `curl` de preflight compara **as duas**
origens, não só a nova. Fica a lição para as seções de deploy dos READMEs: quando o valor tem
marcador, o exemplo copiável precisa vir com o valor real ao lado — e é assim que ele está escrito
agora em `backend/README.md`.

**Os dois itens que dependiam do Igor foram fechados:** a variável corrigida e redeployada
(preflight `200` com a origem ecoada, e `400` para origem não autorizada), e a conferência de
navegador feita em janela anônima — masthead trocando ao entrar e ao sair sem recarregar, Network
com `/api/...` no domínio da Vercel. Um `POST /api/auth/login` depois do redeploy confirmou que o
reinício do backend não regrediu nada.

### File List

| Arquivo | Mudança |
|---|---|
| `.gitignore` | `lib/` e `lib64/` → `/lib/` e `/lib64/`, com o comentário do porquê |
| `frontend/.env.example` | +bloco comentado "Em produção (Vercel)" |
| `frontend/README.md` | +Deploy na Vercel (5 subseções + o que a Vercel faz), +Histórico desta camada com a Story 1.9, +verificação em produção; diagrama do proxy com domínios reais; parágrafo desatualizado de `API_URL` reescrito; aviso do `next build` atualizado; intro com a URL publicada |
| `README.md` | Estado atual, No ar, Roteiro de avaliação (bloco "Sem instalar nada"), Contas semeadas, Stack, 4 entradas de decisão, O que não está pronto |
| `backend/README.md` | `CORS_ORIGENS` na tabela de variáveis, +Por que essa variável não é o que faz o login funcionar, +Story 1.9 no Histórico desta camada |

**Rastreados pela primeira vez** (existiam no disco desde a Story 1.2, nunca no repositório):
`frontend/src/lib/api.ts`, `frontend/src/lib/sessao.ts`, `frontend/src/lib/caminho.ts`.

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Frontend publicado em `https://elite-dev-rock-hub.vercel.app`, com `Root Directory = frontend`, `API_URL` em Production e Preview, e a branch da epic como Production Branch. Verificado por HTTP: raiz `200` com os nove tokens da identidade no CSS publicado, login `200` nas quatro contas semeadas com os papéis certos, `Set-Cookie` com `HttpOnly`/`Secure`/`SameSite=lax` e sem `Domain=`, `401` sem cookie e `404` com a casca do projeto. Documentação escrita a partir do que foi executado, nos quatro arquivos previstos. **Um quinto arquivo entrou fora do previsto:** o `.gitignore` da raiz trazia `lib/` do template Python, que casa em qualquer profundidade e mantinha `frontend/src/lib/` fora do repositório desde a Story 1.2 — o segundo build da Vercel falhou com `Module not found` nos sete arquivos que importam de `@/lib`. Consertado ancorando o padrão (`/lib/`), com `!frontend/src/lib/` descartado por deixar a armadilha armada para a próxima pasta aninhada. Nenhuma linha de `frontend/src/` ou `backend/` editada; 85 testes do backend passando. **Fechamento:** o `CORS_ORIGENS` da Railway tinha sido salvo com o marcador `<projeto>` colado literalmente, e o preflight recusava a origem da Vercel enquanto o painel parecia certo — corrigido para o domínio real e redeployado, com preflight `200` ecoando a origem e `400` para origem não autorizada. Conferência de navegador feita pelo Igor em janela anônima: masthead trocando ao entrar e ao sair sem recarregar, Network com `/api/...` no domínio da Vercel. Todos os 10 ACs cumpridos |
| 2026-08-10 | Story 1.9 criada e contextualizada. Três decisões do Igor incorporadas: acrescentar a origem da Vercel ao `CORS_ORIGENS` da Railway (em vez de manter só o `localhost`, ainda que o CORS não esteja no caminho do navegador por causa do proxy), publicar a branch da epic na Vercel (em vez de mesclar na `main` antes do code review) e definir `API_URL` também para os deploys de Preview (em vez de só Production, o que deixaria todo Preview com o login quebrado em silêncio). Oito ACs acrescentados aos dois do `epics.md`: a URL publicada precisa ser o domínio de produção e não a URL gerada por deploy — no plano Hobby esta última fica atrás do login da Vercel, e é justamente a que aparece em destaque ao fim do build; `Root Directory = frontend` e Production Branch trocada, que são os dois erros que a Story 1.8 já cometeu no painel da Railway; `API_URL` sem `NEXT_PUBLIC_`, com `https://` e sem barra final, definida antes do build porque o `rewrites()` congela no `next build`; o `Set-Cookie` voltando pelo domínio da Vercel sem atributo `Domain=`; os três READMEs refazíveis numa conta vazia; e a fronteira de que nenhuma linha de `frontend/src/` ou `backend/app/` muda. Registrada a divisão de verificação que esta story tem e a 1.8 não tinha: o `curl` prova o proxy, o cookie e o 404, mas o `router.refresh()` do masthead e a origem das chamadas na aba Network só existem no navegador e são conferência do Igor |
