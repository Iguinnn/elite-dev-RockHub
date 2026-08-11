# RockHub — frontend

Next.js 16 com App Router, TypeScript e React 19. É a interface da plataforma: a programação de
shows, a compra, o ingresso com QR e a tela de validação da portaria. A API vive em
[`../backend`](../backend/README.md) e este projeto só a consome.

Hoje está de pé a casca — o sistema visual "jornal noturno" aplicado, o masthead, a raiz em estado
vazio e um 404 com a cara do projeto —, as **duas telas de acesso**, login e cadastro, e o **ciclo
de sessão fechado**: o masthead sabe quem está do outro lado, existe uma `/conta` com os dados e o
botão de sair, e quem abre uma página protegida sem sessão é levado ao login e devolvido ao destino
depois de entrar.

**E está publicado:** <https://elite-dev-rock-hub.vercel.app> — dá para entrar por lá, com as contas
de avaliação, sem instalar nada. Como o projeto foi configurado no painel, campo por campo, está em
[Deploy na Vercel](#deploy-na-vercel).

O histórico de decisões do projeto inteiro está no [README da raiz](../README.md). Aqui fica o que
é específico desta camada.

> **Com que conta entrar em `/login`:** as quatro credenciais de avaliação — organizador, dois
> clientes e portaria — estão no [README da raiz](../README.md#contas-semeadas). Elas nascem de um
> comando do backend (`uv run python -m seeds.semear`), e **a Story 1.7, que as criou, não alterou
> nenhum arquivo desta pasta**: entrar com uma conta semeada usa exatamente a mesma tela e o mesmo
> caminho de qualquer outra, prontos desde a Story 1.4. Registro aqui porque "nada mudou nesta
> camada, e este é o motivo" também é informação — e porque quem abre o frontend primeiro precisa
> saber onde estão as senhas.

## Como executar

### Pré-requisitos

- **Node ≥ 20.9** (a minha máquina roda a v24.14.0). O Next 16 derrubou o suporte ao Node 18
- **npm** — é o gerenciador do projeto, com `package-lock.json` versionado. Não troque por pnpm ou
  yarn: a Vercel usa npm por padrão, e é esse lockfile que ela vai ler no deploy

### Subir

```bash
cd frontend

cp .env.example .env.local    # no Windows: copy .env.example .env.local
npm install

npm run dev
```

Abre em <http://localhost:3000>. Para as telas de acesso funcionarem, o backend precisa estar no ar em
`localhost:8000` — é para lá que o proxy `/api/*` aponta por padrão.

A porta 3000 é também a origem que o `CORS_ORIGENS` do backend autoriza. Desde o proxy da Story 1.4
o CORS deixou de estar no caminho do navegador, então subir em outra porta não quebra mais o login —
mas mantenha a 3000 mesmo assim, porque é a porta que os dois READMEs documentam e é o padrão do
`npm run dev`.

### Outros comandos

```bash
npm run build    # build de produção — é exatamente o que a Vercel roda
npm run start    # serve o build de produção
npm run lint     # ESLint
npx tsc --noEmit # checagem de tipos isolada
```

## Variáveis de ambiente

O arquivo que o Next lê é o **`.env.local`**. O `.env.example` é só o modelo versionado, para
documentar quais chaves existem — copie-o, não o renomeie.

| Variável | Padrão | Para quê |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Endereço da API, lido **no servidor** pelo proxy `/api/*` |

**`API_URL` não é `NEXT_PUBLIC_`, e isso mudou na Story 1.4.** Ela nasceu como
`NEXT_PUBLIC_API_URL` na 1.2, quando a ideia era o navegador chamar o backend diretamente. Com o
proxy (seção abaixo) o navegador não precisa mais saber o endereço da API — ele só conhece `/api/...`
—, e quem lê a variável é o Next, no servidor. Renomeei em vez de deixar as duas: manter a antiga
viva seria manter dois caminhos para alcançar a mesma API, e é o tipo de coisa que produz um bug
que só aparece em um dos dois.

**Em produção, `API_URL` aponta para a Railway — e isso aconteceu na Story 1.9.** O frontend está
publicado em <https://elite-dev-rock-hub.vercel.app>, com a variável definida **no painel da
Vercel**, para Production e Preview, valendo
`https://elite-dev-rockhub-production.up.railway.app`. O `.env.example` daqui continua com
`localhost:8000` de propósito: ele é o modelo de desenvolvimento, e o valor de produção mora na
plataforma, não no repositório. O passo a passo do painel está em [Deploy na
Vercel](#deploy-na-vercel).

Um detalhe dessa variável que importou exatamente como previsto: o `rewrites()` é avaliado em
**tempo de build**, e a Vercel compila as rotas no `next build`. Trocar `API_URL` no painel depois
**não** muda o proxy sem um redeploy — o valor fica congelado na build. Está escrito também no
`next.config.ts`, ao lado da linha que a lê. A regra prática que eu levei da Story 1.9: **mexeu no
`API_URL`, redeploy.**

**Nenhuma variável `NEXT_PUBLIC_` carrega credencial.** Tudo que tem esse prefixo vai embutido no
bundle e fica visível para qualquer visitante — é endereço público, nada mais. A chave da
Ticketmaster e o segredo que assina os ingressos moram no backend e nunca atravessam para cá
(AD-2).

## Deploy na Vercel

O frontend está no ar em **<https://elite-dev-rock-hub.vercel.app>**. **Não existe `vercel.json`
neste repositório** — a configuração mora no painel, e esta seção é onde ela está escrita. É a mesma
decisão que eu tomei para a Railway na Story 1.8, e o motivo está no [README da
raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

Se você for subir a sua própria cópia, é isto, na ordem:

### 1 · O projeto

| Onde | Campo | Valor |
|---|---|---|
| `Add New` → `Project` | Import Git Repository | `elite-dev-RockHub` |
| Configure Project | **Root Directory** | `frontend` |
| Configure Project | Framework Preset | **Next.js** (detectado sozinho depois do Root Directory) |
| Configure Project | Build / Output / Install Command | **não sobrescreva nenhum** |
| Settings → Environments | **Production Branch** | a branch que você quer publicar |

⚠️ **O `Root Directory` é o campo que derruba o build de quem tem pressa.** Ele não vem preenchido:
o valor inicial é `./`, e o `frontend` que aparece em cinza no campo é *sugestão*, não valor
gravado. Clique em `Edit`, escolha `frontend` na árvore e confirme — o campo precisa mostrar
`frontend` depois de salvar. Sem isso a Vercel olha a raiz do monorepo, não acha `package.json`, não
detecta framework nenhum e cai em "Other". É o mesmo passo que derrubou o meu primeiro build na
Railway, no painel do outro fornecedor.

⚠️ **A Production Branch precisa ser conferida.** A Vercel escolhe sozinha, nesta ordem: `main`,
`master`, a branch padrão do repositório. Se o seu código está noutra branch, o primeiro deploy
constrói a errada. Trocar o campo **não dispara deploy nenhum** e o botão `Redeploy` do deploy que
falhou reconstrói *o mesmo commit* — para publicar a branch certa é preciso um push nela, ou
promover a produção um deploy dela na aba Deployments.

### 2 · A variável

| Variável | Valor | Ambientes |
|---|---|---|
| `API_URL` | `https://elite-dev-rockhub-production.up.railway.app` | **Production** e **Preview** |

Três detalhes que sustentam esse valor, e cada um tem um sintoma próprio quando erra:

- **Sem `NEXT_PUBLIC_`.** Quem lê `API_URL` é o servidor: o `rewrites()` do `next.config.ts` e o
  `fetch` do `sessao.ts`. Escrever `NEXT_PUBLIC_API_URL` por hábito faz o valor simplesmente não
  chegar, e o proxy cai no padrão `localhost:8000`
- **`https://`, nunca `http://`.** A Railway responde `301` em HTTP, e um `POST` redirecionado perde
  o corpo em vários clientes. Falha só no login, só em produção
- **Sem barra no fim.** O rewrite concatena `${API_URL}/:caminho*`; com barra vira
  `https://…app//auth/login`, e o roteador do FastAPI não casa esse caminho

Eu também **não** marquei a variável como *sensitive*. Ela é endereço público, não segredo (AD-2), e
marcada como sensível o painel deixa de mostrar o valor — justamente quando você precisa conferir se
sobrou uma barra no fim.

⚠️ **Defina a variável antes do primeiro deploy**, ou faça um redeploy depois de defini-la. O
`rewrites()` é avaliado no `next build` e o valor fica **congelado na build**. Trocar a variável no
painel depois não muda o proxy até o próximo deploy, e não há nada no log acusando.

### 3 · Qual URL publicar

Settings → **Domains**. O domínio de produção é `<projeto>.vercel.app` — aqui,
`elite-dev-rock-hub.vercel.app`. **É essa URL que vai para os READMEs.**

⚠️ **Não copie a URL da tela do deploy.** A Vercel gera, por deploy, uma URL do tipo
`<projeto>-<hash>-<escopo>.vercel.app`, e é ela que aparece em destaque quando o build termina — é a
que se copia por reflexo. No plano Hobby a proteção padrão (*Vercel Authentication* + *Standard
Protection*) deixa o **domínio de produção público** e **protege as URLs geradas por deploy**: quem
abrir a errada vê uma tela de login da Vercel.

A conferência custa dez segundos e evita pôr uma tela de autenticação na cara de quem avalia: abra a
URL numa **janela anônima**. Se pedir login, é a URL errada.

### 4 · Como saber que deu certo

Com o deploy verde, de fora, sem abrir o navegador:

```bash
URL=https://elite-dev-rock-hub.vercel.app

curl -i $URL/                       # 200, e o HTML traz o masthead
curl -i $URL/rota-que-nao-existe    # 404 com a casca do projeto
curl -i $URL/api/auth/eu            # 401 NAO_AUTENTICADO

curl -i -X POST $URL/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

**O login é a chamada que prova o deploy inteiro**, e é a única que vale repetir: ela só devolve
`200` se o build leu o `API_URL`, **e** o proxy reescreveu para a Railway a partir do servidor da
Vercel, **e** o banco de lá respondeu. Três fornecedores atravessados numa chamada.

No `Set-Cookie` dessa resposta: `HttpOnly`, `Secure`, `SameSite=lax` e **nenhum `Domain=`** — cookie
de host, da origem do frontend. Se aparecer `Domain=.up.railway.app`, alguma coisa mudou no backend.

⚠️ No PowerShell, `curl` é apelido de `Invoke-WebRequest` e não entende `-i` nem `-d`. Use
`curl.exe`, ou rode pelo Git Bash. É atrito de dois minutos que parece falha de deploy.

E três coisas que **só o navegador prova**, porque nenhuma delas aparece num `curl`: o masthead
virando `Minha conta` ao entrar e voltando a `Entrar` ao sair **sem recarregar a página** (é o
`router.refresh()`), a aba Network mostrando `/api/...` no domínio da Vercel e nunca em
`up.railway.app`, e `document.cookie` no console **não** mostrando o `rockhub_sessao`.

### 5 · Quando falhar, onde olhar

Em ordem de probabilidade, com o sintoma que cada uma produz:

| Sintoma | Causa |
|---|---|
| Build morre em "No framework detected", ou não acha `package.json` | Falta `Root Directory = frontend` |
| Build verde mas o site é de um commit velho, ou o build lista a raiz do monorepo | A Production Branch é a errada |
| `Module not found` em vários arquivos de uma vez, sempre no mesmo import | Uma pasta existe na sua máquina e **não no repositório**. Foi o que aconteceu comigo — ver [Histórico](#story-19--frontend-no-ar-na-vercel) |
| A URL pede login da Vercel | É a URL gerada por deploy, não o domínio de produção |
| A tela abre, o login envia e nada acontece; Network mostra `500`/`502` em `/api/auth/login` | `API_URL` ausente, com `http://`, com barra no fim, ou definida **depois** do build. Nos quatro casos o conserto termina em **redeploy** |
| Login responde `200` mas a página continua deslogada | O cookie não foi aceito. Confira `Secure` no `Set-Cookie` (vem do `AMBIENTE=producao` da Story 1.8) e que **não** há `Domain=` |
| `404` sem a identidade do projeto | O `not-found.tsx` saiu da raiz de `app/` — é o erro documentado na Story 1.2 |
| Preview quebrado com Production funcionando | A variável foi marcada só para Production |
| Push que só mexe em `backend/` não gera deploy do frontend | É o *Skip deployment* de monorepo funcionando como deveria, não um defeito |

### O que a Vercel faz com este projeto

Lido na documentação da plataforma, não deduzido:

| Fase | O que acontece |
|---|---|
| Clone | `git clone --depth=10` da Production Branch |
| Root Directory | `frontend` vira a raiz do build; nada fora dela é acessível |
| Detecção | Encontra `frontend/package.json` → Framework Preset **Next.js** |
| Install | Detecta o gerenciador pelo `package-lock.json` → **npm** |
| Build | `npm run build`, com Turbopack, que é o padrão do Next 16 |
| Node | **24.x**, o LTS padrão para projeto novo. Não fixei `engines.node` |
| Variáveis | `API_URL` disponível **no build** e **em execução** — o `rewrites()` a lê no build, o `sessao.ts` em execução |
| Output | Automático para Next.js — nada a configurar |

Duas consequências que valem no dia a dia:

- **Mudança de variável só vale para deploys novos.** A documentação é literal: *"Any change you make
  to environment variables are not applied to previous deployments"*. Somado ao `rewrites()`
  congelado no build, dá a regra: mexeu no `API_URL`, redeploy
- **`devDependencies` são instaladas no build** — é assim que `typescript` e os `@types` entram no
  `next build`. Não tente excluí-las

## O proxy `/api/*`

`next.config.ts` reescreve tudo que chega em `/api/:caminho*` para `${API_URL}/:caminho*`. O
navegador chama o domínio do próprio frontend; quem fala com o backend é o servidor do Next.

```
navegador ──► elite-dev-rock-hub.vercel.app/api/auth/login      (mesma origem: sem CORS)
                     │  rewrite do next.config.ts (lado do servidor)
                     ▼
   elite-dev-rockhub-production.up.railway.app/auth/login    (servidor↔servidor: sem CORS)

o Set-Cookie volta pelo domínio da Vercel → cookie de origem própria → SameSite=Lax funciona
```

**Desde a Story 1.9 esse diagrama é verificado, não previsto.** Os dois domínios são os reais, e um
`POST` em `https://elite-dev-rock-hub.vercel.app/api/auth/login` responde `200` com o `Set-Cookie`
vindo pelo domínio da Vercel — `HttpOnly; Max-Age=28800; Path=/; SameSite=lax; Secure`, e **sem
atributo `Domain=`**. O proxy foi escrito na 1.4 para exatamente este dia, e não precisou de uma
linha de ajuste para atravessar dois fornecedores.

**Por que isso existe:** o AD-15 fixa a sessão como cookie `SameSite=Lax`, e `vercel.app` e
`up.railway.app` estão os dois na *Public Suffix List* — são sites diferentes para o navegador, sem
domínio registrável em comum. Um cookie `Lax` não sobrevive a esse cruzamento. Sem o proxy, o login
passaria em toda a suíte, funcionaria perfeitamente em `localhost` (onde `:3000` e `:8000` são o
mesmo site, porque porta não conta) e falharia calado só em produção. O motivo completo, com a
alternativa que descartei, está no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

Três consequências práticas:

- **As chamadas passaram a ser de mesma origem**, então CORS deixou de participar do caminho do
  navegador. **Não removi o `CORSMiddleware` do backend** por causa disso: ele continua sendo a rede
  de proteção de qualquer chamada direta, e não custa nada
- **`credentials: "include"` não é necessário** no `fetch`. `same-origin` já é o padrão, e escrever
  `include` sugeriria, para quem ler depois, que existe uma chamada cruzando domínio — que é
  justamente o que o proxy eliminou
- **`/api` é caminho reservado neste projeto.** Um `rewrites()` que devolve array é avaliado *depois*
  do sistema de arquivos, então um `src/app/api/qualquer/route.ts` ganharia do proxy naquele caminho
  e o login pararia de funcionar por um motivo invisível. Não crie `src/app/api/`

⚠️ **O `destination` do rewrite é congelado no `next build`.** A Vercel compila as rotas no build, e
é ali que `process.env.API_URL` é lido — trocar a variável no painel depois **não** muda o proxy sem
um redeploy. O sintoma é o frontend novo apontando para a API antiga, e não há nada no log acusando.
Este aviso estava escrito aqui desde a Story 1.4 dizendo que ia custar uma tarde na 1.9; **não
custou, justamente porque estava escrito** — a variável foi definida antes do primeiro build.

## Falar com a API

**Toda chamada passa por `src/lib/api.ts`, e todo caminho começa com `/api`.** Nenhum componente
monta URL de backend por conta própria.

```ts
const usuario = await chamarApi<UsuarioSaida>("/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, senha }),
});
```

Em resposta não-ok, `chamarApi` extrai o `erro.codigo` do corpo e levanta um `ErroDaApi` que carrega
**o código, não a mensagem**. É de propósito: **a tela escolhe o texto pelo `codigo`, nunca pela
`mensagem` vinda do servidor.** A mensagem do backend é para humano que lê log; o texto de tela é
decisão de produto e mora aqui. Assim eu reescrevo qualquer mensagem no backend sem quebrar tela
nenhuma.

Dois detalhes que já estão tratados e que é fácil quebrar sem querer:

- **`204` não tem corpo** — não chame `.json()` nela. O `logout` é `204`
- **Erro de rede não tem `codigo`.** Backend desligado produz um `TypeError: Failed to fetch`, que
  nem chega a passar pelo caminho do `ErroDaApi`. Quem chama trata com `try/catch` e cai na mensagem
  genérica — sem isso a tela quebra em branco quando a API cai, que é o primeiro estado que alguém
  encontra ao subir só o frontend

### E o caminho do servidor: `src/lib/sessao.ts`

`api.ts` é o caminho do **navegador**. A leitura da sessão a partir de um Server Component é outro
arquivo, e a separação não é organização — é obrigatória: `api.ts` é importado pelos formulários,
que são `"use client"`, e `next/headers` num módulo que chega ao bundle do cliente **quebra o
build**. A fronteira aqui é física.

```ts
const usuario = await obterUsuarioDaSessao();   // UsuarioDaSessao | null
```

Cinco decisões dentro de quinze linhas:

- **URL absoluta**, `process.env.API_URL`, a mesma variável do `next.config.ts`. O `rewrite` de
  `/api/*` é do navegador; um `fetch("/api/…")` do servidor não tem origem para resolver
- **O cookie é repassado à mão** no cabeçalho `Cookie`. O `fetch` do servidor não herda nada do
  pedido que está sendo atendido — este é o erro que faz a página renderizar deslogada com sessão
  perfeitamente válida, e sem erro nenhum para investigar
- **`cache()` do React**, não `unstable_cache` nem revalidação por tempo: a deduplicação que
  interessa é *dentro de uma requisição*. O masthead e a `/conta` chamam a mesma função na mesma
  renderização, e o backend é consultado uma vez
- **Sem cookie, sem ida à rede.** A raiz é pública e visitante é o caso comum
- **`try/catch` em volta do `fetch`, e `!resposta.ok` também devolve `null`.** Backend fora do ar
  ou cookie vencido renderizam a página como visitante, em vez de derrubá-la — **mas o `catch`
  agora registra a falha antes de devolver `null`.** Era um `catch` mudo, e o code review da Epic 1
  mostrou o custo: ele achatava três coisas diferentes — "sem sessão", "sessão inválida" e "API
  inalcançável" — num resultado só. Quem tem cookie válido e pega uma instabilidade da Railway vê o
  masthead voltar para `Entrar`, a `/conta` rebater para o login, conclui que a sessão caiu, e não
  há pista nenhuma: nem na tela, nem no console, nem no Network. O comportamento continua idêntico;
  o que mudou é que agora sobra rastro no log do servidor

O nome do cookie, `rockhub_sessao`, está escrito nos dois lados: aqui e como padrão de
`cookie_sessao_nome` no `backend/app/core/config.py`. É acoplamento assumido — trocar lá exige
trocar aqui. ⚠️ E `COOKIE_SESSAO_NOME` **é variável de ambiente real do backend**: defini-la no
painel da Railway faz o backend gravar um cookie e este arquivo procurar outro, com o sintoma sendo
"todo mundo aparece deslogado" e nenhum erro em lugar nenhum. Está documentada no
[README do backend](../backend/README.md#configuração) exatamente para ninguém mexer nela sozinha.

**`API_URL` ausente também deixou de ser silenciosa.** O padrão `http://localhost:8000` é o valor
certo em desenvolvimento e um bug mudo em produção — o servidor da Vercel tentaria falar consigo
mesmo. Agora tanto o `next.config.ts` (no build) quanto o `sessao.ts` (na primeira renderização)
avisam quando `NODE_ENV === "production"` e a variável não existe. **Avisam, não derrubam:** o
simétrico do backend seria falhar, como a `Settings` faz com o `JWT_SECRET` de exemplo, mas lá a
consequência de subir é uma sessão forjável e aqui é um Preview quebrado — e Preview que não sobe é
pior que Preview quebrado, pelo mesmo argumento da Story 1.9.

**Estado de sessão é lido no servidor, nunca guardado no cliente.** Não há contexto React de
usuário, não há `localStorage`, não há estado global. A página pergunta ao servidor, e o servidor
pergunta ao backend, que é quem tem o segredo do token. Sessão duplicada no cliente é a origem
clássica da tela que continua mostrando o usuário antigo depois do logout.

## Estrutura

```text
frontend/
  .env.example
  eslint.config.mjs
  next.config.ts
  tsconfig.json
  public/                     # estáticos servidos na raiz
  src/
    app/
      layout.tsx              # <html lang="pt-BR"><body> e metadata — só o documento
      globals.css             # tokens, reset, foco, utilitários
      not-found.tsx           # 404 — carrega a própria casca (ver abaixo)
      not-found.module.css
      (site)/                 # casca com masthead: tudo que é navegável
        layout.tsx
        page.tsx              # raiz
        page.module.css
        conta/
          page.tsx            # Server Component com a guarda de sessão
          page.module.css
      (entrada)/              # casca sem masthead: só a marca
        layout.tsx
        layout.module.css
        login/
          page.tsx            # Server Component async: lê e valida o ?voltar=
          page.module.css
        cadastro/
          page.tsx            # Server Component async: o mesmo ?voltar=
          page.module.css
    components/
      Logotipo.tsx            # a marca, num lugar só — e Link para a raiz
      Logotipo.module.css
      Masthead.tsx            # cabeçalho de jornal — async, lê a sessão
      Masthead.module.css
      NavLink.tsx             # "use client" — marca o item ativo
      Campo.tsx               # rótulo + entrada, sempre juntos
      Campo.module.css
      Botao.tsx               # ação primária âmbar
      Botao.module.css
      AvisoDeErro.tsx         # a região role="alert" e a regra que a faz funcionar
      AvisoDeErro.module.css
      FormularioLogin.tsx     # "use client"
      FormularioCadastro.tsx  # "use client"
      BotaoSair.tsx           # "use client" — logout + router.refresh()
    lib/
      api.ts                  # chamarApi + ErroDaApi — o caminho do navegador
      sessao.ts               # obterUsuarioDaSessao() — só servidor
      caminho.ts              # caminhoInternoSeguro() — função pura
```

### Duas cascas, e por quê

O layout raiz é só `<html><body>`. A casca visível vem de dois grupos de rotas:

| Grupo | O que mostra | O que mora nele |
|---|---|---|
| `(site)` | Masthead: logotipo, navegação, fio duplo | A raiz, e daqui em diante tudo que exige sessão ou é navegável |
| `(entrada)` | Só o logotipo, centrado | `/login` e `/cadastro` |

**Quem está tentando entrar não pode ver "Minha conta".** É um link que ele não consegue abrir. A
tela de acesso mostra a marca e o formulário, nada mais.

**O efeito colateral que o code review da Epic 1 achou:** sem masthead, quem digitava `/login` na
barra de endereço ficava sem nenhum caminho de volta para `/` — os únicos links da tela eram o par
`/login` ↔ `/cadastro`, e a decisão de tirar a navegação tinha criado um beco. A correção foi
transformar o `Logotipo` de `<span>` em `<Link href="/">`, o que resolve nas duas cascas de uma vez
e **não reintroduz navegação nenhuma**: é a mesma marca que já estava lá, agora clicável, seguindo a
convenção que todo site cumpre. O `className` fica no `<a>` porque o `globals.css` já zera cor e
sublinhado de link, e o `:focus-visible` âmbar (UX-DR9) precisa contornar a palavra inteira.

Usei grupo de rotas em vez de **dois layouts raiz** (que também separaria as cascas) porque a
documentação do Next avisa que navegar entre layouts raiz diferentes força **recarga completa da
página** — e porque layout raiz múltiplo exige abrir mão do `app/layout.tsx`, o que deixaria o
`not-found.tsx` sem layout de onde herdar e obrigaria a usar `global-not-found`, que ainda é
experimental. Descartei também esconder o masthead com `usePathname()`: funcionaria, mas
transformaria o masthead inteiro num componente de cliente para resolver uma questão que é de
estrutura de rota.

⚠️ **O `not-found.tsx` tem que ficar na raiz de `app/`, e carrega a própria casca.** Só o
`not-found` da raiz atende URL que não casa com rota nenhuma — eu movi para dentro de `(site)` para
ele herdar o masthead de graça, e o resultado foi o visitante caindo no 404 padrão do Next, sem
identidade. Como o layout raiz é só `<html><body>`, o masthead precisa ser montado dentro do próprio
`not-found.tsx`. É a única duplicação da casca no projeto, e ela é obrigatória.

`src/lib/` nasceu vazia na Story 1.2, pelo mesmo motivo que `app/services/` e `app/schemas/`
nasceram vazias no backend: deixar a estrutura materializada desde o primeiro commit, para que as
stories seguintes não improvisem onde as coisas moram. Ganhou morador na 1.4.

## As telas de acesso

Duas: `/login` e `/cadastro`. Rota em inglês para a primeira, sendo o resto tudo em português, e foi
escolha — `/entrar` combinaria com o rótulo do botão, mas `login` é o termo que quem avalia reconhece
de imediato, e é o que o próprio protótipo usa. `/cadastro` é português e casa com o
`POST /auth/cadastro` do backend.

**As duas se alcançam uma da outra.** No pé de cada coluna há o link recíproco — "Ainda não tem
conta? Cadastre-se" e "Já tem conta? Entrar" —, com `next/link`, nunca `<a href>`: as duas telas
compartilham a casca do grupo `(entrada)`, e um `<a>` recarregaria o documento inteiro para trocar de
formulário. Nenhuma das duas é alcançável só digitando a URL, que era a pendência aberta na 1.4.

Cada página é Server Component; a ilha de cliente é só o formulário — interação de formulário está na
lista de exceções legítimas do `"use client"`. O contrato de acessibilidade, que vale para todo
formulário daqui em diante (UX-DR9):

- `<label htmlFor>` explícito em todo campo — nada de placeholder fazendo as vezes de rótulo. O
  `Campo` não tem caminho para renderizar entrada sem rótulo associado: o `id` é obrigatório e serve
  às duas pontas
- `<form onSubmit>` de verdade, para `Enter` enviar sem precisar acertar o botão
- `autoComplete` em todo campo. No login, `email` e `current-password`. No cadastro, `name`, `email` e
  **`new-password` nos dois campos de senha** — é o que faz o gerenciador oferecer uma senha nova em
  vez de tentar preencher a de uma conta que ainda não existe
- o erro vive numa região `role="alert"` **que existe sempre, vazia** — se ela só entrasse no DOM
  junto com o texto, parte dos leitores de tela não anunciaria nada. Vazia ela não ocupa espaço
- o foco é o `:focus-visible` âmbar global; o `border-color` âmbar no `:focus` do campo é *além*
  dele, nunca em vez dele. O protótipo tem um `outline: none` no input (l. 152) que **não** foi para
  o código

E **o sucesso leva para `/` nas duas**, sem encaminhar por papel: `/organizador/...` e `/portaria`
ainda não existem, e inventar rota aqui produziria um 404 na cara de quem está avaliando. No cadastro
isso é ainda mais direto, porque toda conta criada pela interface nasce `CLIENTE`. O encaminhamento
por papel nasce quando aquelas telas existirem (Epics 2 e 5).

**As telas não têm masthead** — só a marca, pela casca do grupo `(entrada)` descrita acima. A
primeira versão do login herdava o masthead do layout raiz, e ficava oferecendo "Meus ingressos" e
"Minha conta" para quem ainda não entrou. Corrigi antes de fechar a 1.4.

> A frase "o sucesso leva para `/` nas duas" continua valendo como padrão, mas deixou de ser
> absoluta na Story 1.6: quando a pessoa chegou por um `?voltar=`, o destino é ele. O que **não**
> mudou é o resto — não há encaminhamento por papel, e não vai haver até as telas de organizador e
> portaria existirem.

### `Campo`, `Botao`, `AvisoDeErro` — e quando abstrair

Os três nasceram na Story 1.5, **não na 1.4**, e o critério é o que interessa: **componente
compartilhado nasce no segundo uso, nunca no primeiro.** Dois campos num único formulário não
justificavam abstração; seis campos e dois botões entre duas telas, sim. Antes disso, componente sem
consumidor firme é componente que a próxima story reescreve — foi o mesmo critério que manteve o CSS
do 404 repetido em vez de abstraído, na 1.2.

Extrair custou reescrever o `FormularioLogin`, que já estava entregue e conferido. Foi o ponto de
maior risco da story: um `htmlFor` que perde o par com o `id`, um `autoComplete` que some, um `name`
renomeado — e a tela continua parecendo certa, sem nenhum teste para acusar. A alternativa era
repetir o CSS nas duas telas, e ela cai por um motivo simples: duas cópias do mesmo campo divergem na
primeira vez que alguém ajustar só uma.

O `Botao` tem **só a variante primária**. O `DESIGN.md` descreve também um secundário e um
destrutivo, e nenhum dos dois tem consumidor — uma prop `variante` com um valor só é abstração
inventada. Quando o segundo aparecer, ela nasce ali.

**O `AvisoDeErro` foi extraído por um critério diferente dos outros dois.** `Campo` e `Botao` saíram
porque se repetem. Este saiu porque a regra que o faz funcionar é *invisível*: a região `role="alert"`
precisa existir no DOM desde o primeiro render, vazia, e receber só o texto depois. Escrita como
comentário dentro de um formulário, essa regra é a primeira coisa que alguém apaga por parecer óbvia
ao copiar para o segundo — e o que se perde não é estilo, é o anúncio do erro para quem usa leitor de
tela. Componente é onde uma regra dessas se protege sozinha. **Regra que protege acessibilidade vira
componente mesmo com poucos usos.**

Os três não têm `"use client"`. Nenhum tem interação própria, e importados por um componente de
cliente vão para o bundle do cliente do mesmo jeito — a diretiva só marcaria como ilha algo que não é.

### Onde cada validação mora, e por que em dois lugares

Não é redundância; são responsabilidades diferentes. **O cliente valida para ser gentil, o servidor
valida para estar correto.**

| Regra | Cliente | Servidor | Por quê |
|---|---|---|---|
| Campo obrigatório | `required` | `min_length` | O navegador dá o retorno imediato; o servidor é o que vale |
| Senha ≥ 6 caracteres | sim, antes do `fetch` | `Field(min_length=6)` | O cliente evita uma ida à rede; o servidor é a garantia |
| Senhas conferem | **só cliente** | — | Não é regra de negócio |
| Formato do e-mail | `type="email"` | `field_validator` | O `type` some num `curl`; o validador não |
| E-mail já existe | — | **só servidor** | Só o banco sabe |

A única regra que existe **só** no cliente é a confirmação de senha, e ela é a exceção que confirma o
critério: "duas caixas de texto iguais" é sobre o próprio ato de digitar, não sobre o domínio. O
formulário tem os dois valores em mãos, compara em memória e nem chega a fazer a requisição — o corpo
enviado tem três campos (`nome`, `email`, `senha`), nunca quatro. Mandar a confirmação para a API
acrescentaria um campo ao contrato, um validador cruzado, uma mensagem e um teste, tudo para
verificar algo que nenhum outro cliente da API teria por que enviar.

O campo "repetir senha" existe porque **não há recuperação de senha neste projeto**: uma letra errada
seria conta perdida para sempre, sem suporte e sem e-mail. A alternativa considerada e descartada
está no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

> Aquela pendência — "não há link para `/login` a partir do resto do site" — foi paga na Story 1.6,
> na seção abaixo.

## A sessão na tela

### O masthead sabe quem está do outro lado

Ele virou Server Component `async`: lê a sessão e monta a navegação a partir dela.

| Estado | Navegação |
|---|---|
| Sem sessão | `Início` · `Entrar` |
| Com sessão | `Início` · `Minha conta` |

**`Meus ingressos` saiu do masthead** até a Epic 4 criar a tela. É o precedente que firmei na 1.4:
link que cai no 404 não fica no repositório.

**E o nome de quem entrou não aparece ali**, mesmo agora que o componente o conhece. O
`DESIGN.md#Components/masthead` é literal — logotipo, fio, navegação, fio duplo, e nada mais —, e o
UX-DR10 já tinha derrubado a linha de contexto pelo mesmo motivo. Os dados da pessoa são o conteúdo
da `/conta`.

### A `/conta`

Kicker, o nome em serifada (nome próprio), e-mail e papel em mono versalete entre dois fios, e o
botão `Sair`. Nenhum card, nenhum avatar, nenhuma inicial em círculo — círculo com letra dentro é
justamente o vocabulário visual que este projeto está inteiro tentando não ter.

**O `Sair` fica aqui, não no masthead.** O `EXPERIENCE.md#Information Architecture` diz "Minha conta
→ dados, sair", e o `DESIGN.md` não prevê ação dentro do masthead. Ele usa o `Botao` que já existe,
com um `max-width` no CSS da página — largura é decisão do contexto, não uma prop nova no componente.

### A guarda mora na página, não em `middleware`

Cada página protegida repete três linhas: lê a sessão, e se não houver, `redirect()`. O caminho que
todo tutorial mostra é um `middleware.ts` conferindo o cookie antes da rota renderizar, e eu
descartei por dois motivos:

1. **O middleware só consegue ver que o cookie existe, não que ele vale.** Validar o JWT ali
   significaria pôr o `JWT_SECRET` no ambiente do frontend, e o AD-2 diz o contrário — o segredo de
   sessão do backend não tem por que existir na Vercel
2. **Ele viraria uma segunda lista de rotas protegidas**, paralela às páginas. Duas listas divergem,
   e a que fica desatualizada é sempre a que ninguém olha

O custo são as três linhas repetidas, e elas ficam **ao lado** do conteúdo que protegem — que é
exatamente onde quem edita a página vai olhar. O Next 16 traz `unauthorized()` e `forbidden()`, que
seriam o caminho idiomático, mas estão atrás da flag experimental `authInterrupts`, e eu não ligo
flag experimental por conveniência.

**A raiz continua pública.** Visitante sem sessão vê a programação e não é redirecionado para lugar
nenhum.

### O `?voltar=`, e por que ele passa por um filtro

Quem abre `/conta` sem sessão vai para `/login?voltar=%2Fconta` e, depois de entrar, cai de volta em
`/conta` — não em `/`. O link recíproco entre login e cadastro carrega o parâmetro adiante, senão
quem foi mandado para o login, resolveu se cadastrar e criou a conta perderia o destino no meio do
caminho.

**`?voltar=` é um valor que quem chega escolhe e a aplicação obedece** — o redirecionamento aberto
clássico: um link para o meu domínio que joga a pessoa em outro site logo depois de ela digitar a
senha. E pior: a própria documentação do Next avisa que uma URL `javascript:` entregue ao
`router.push` **executa no contexto da página**, o que faz disto um XSS, não só um redirecionamento
indevido. Daí `src/lib/caminho.ts`:

| `?voltar=` | Destino | Por quê |
|---|---|---|
| `/conta` | `/conta` | caminho interno |
| `/ingressos?filtro=x` | `/ingressos?filtro=x` | query preservada; ainda é interno |
| ausente, `""`, lista | `/` | não é string que começa com `/` |
| `https://exemplo.com` | `/` | não começa com `/` |
| `//exemplo.com` | `/` | o navegador lê como protocolo relativo e sai do site |
| `/\exemplo.com` | `/` | vários navegadores normalizam a contrabarra para barra |
| `javascript:alert(1)` | `/` | o caso que a doc do Next chama de XSS |
| `/login`, `/cadastro` | `/` | entrar para cair na tela de entrar é laço |

A lista é de **prefixos recusados**, não de caminhos permitidos. Uma lista de permitidos seria mais
rigorosa e obrigaria a editar aquele arquivo a cada tela nova das Epics 3 a 5 — e no dia em que
alguém esquecesse, a tela nova deixaria de receber o retorno em silêncio.

A validação acontece **no servidor**, na página, e o valor já limpo desce como prop para o
formulário. `useSearchParams()` no Client Component funcionaria e exigiria fronteira de
`<Suspense>`, além de mandar a regra para o navegador, onde ela vale menos.

**Convenção:** parâmetro de URL que vira navegação passa por `caminhoInternoSeguro`. Vale para o
retorno depois do checkout (Epic 3) e para o link compartilhado (Epic 4).

## O sistema visual

A identidade é **"jornal noturno"**: papel escuro, serifada, fios em vez de caixas. A especificação
completa está em
[`_bmad-output/planning-artifacts/ux-designs/.../DESIGN.md`](../_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md),
com um protótipo navegável de 11 telas ao lado.

### Tokens

Todos em `src/app/globals.css`, no `:root`. **É o único arquivo do frontend onde cor e família
tipográfica aparecem por valor.** Módulo de componente sempre usa `var(--token)` — se você digitou
um hex dentro de um `.module.css`, está errado.

| Token | Uso |
|---|---|
| `--breu` `#0E0D0C` | Fundo de toda a aplicação |
| `--breu2` `#151311` | Superfície elevada: resumo, campo, fila em hover |
| `--cal` `#EDE8DC` | Texto principal |
| `--fumaca` `#8F877A` | Texto secundário, etiquetas, kickers |
| `--ambar` `#F2A413` | Acento único: ação primária, item ativo, escassez |
| `--brasa` `#D93B2B` | Erro, esgotado, pagamento recusado, ingresso inválido |
| `--verde` `#3FA96B` | Só o veredito `VÁLIDO` e a confirmação de pagamento |
| `--fio` `#2A2622` | Todos os fios, filetes e bordas |
| `--fio2` `#3A352F` | Fio sobre superfície elevada; medidor esgotado |

Preto quente de tinta, **nunca `#000`**. Branco quente de papel, **nunca `#FFF`**. E o âmbar é o
acento único: se algo precisa de destaque e não é erro nem sucesso, é âmbar. Não introduza um
segundo acento decorativo, nem "só para esta tela".

### Tipografia

Duas famílias, ambas de sistema: `--serif` (Georgia) e `--mono` (ui-monospace). Serifada é a voz do
jornal — nome de artista, título, valor, corpo de texto. Monoespaçada é tudo que é máquina ou
etiqueta — código, kicker, rótulo de campo, hora, estado —, sempre em versalete com entreletra
larga.

A tensão entre as duas é a identidade. Serifada sozinha vira convite de casamento; monoespaçada
sozinha vira terminal. **Nunca serifada em etiqueta, nunca monoespaçada em nome próprio.**

### Regras que não têm exceção

- **Raio zero e sombra zero, em qualquer elemento.** Papel não tem canto arredondado
- **Nenhuma fonte externa.** Sem `next/font`, sem `@font-face`, sem `@import` do Google Fonts
- **Ninguém desliga o contorno de foco.** O foco é âmbar e é visível em tudo que é focável
- **Nada atravessa a tela.** A única animação permitida é mudança de cor em hover, até 120ms — e com
  `prefers-reduced-motion` ativo nem isso roda
- **Sem linha de contexto no cabeçalho** (data, contador de eventos, subtítulo). Foi testada no
  protótipo e removida por soar gerada

## Responsividade

O corte é **900px**, e a regra vem do UX:

| Faixa | Comportamento |
|---|---|
| ≥ 900px | Layout pleno: listagem em quatro colunas, chamada principal em duas |
| < 900px | Chamada principal e ficha de evento empilham; a fila vira duas colunas — data e bloco |
| Portaria | Coluna única sempre, alvos de no mínimo 44px |

**Cliente e organizador são desktop-first; a portaria é a única superfície mobile-first.** Não é
descuido — é o UX-DR6. As ergonomias são opostas: o cliente compara opções sentado, com tempo; quem
está na porta trabalha em pé, à noite, com uma mão e gente esperando.

**Cada tela carrega o seu próprio ajuste, na story que a cria.** Não há uma etapa de "deixar
responsivo" no fim: o breakpoint só faz sentido escrito junto da grade que ele colapsa, e layout
adiado para o último dia não acontece.

Nesta casca o único ponto que precisava de tratamento era a navegação do masthead — os itens em
versalete com entreletra larga não cabem lado a lado em celular, então ela quebra linha
(`flex-wrap`). Encolher a entreletra não era opção: ela é parte da identidade. O resto já reflui
sozinho, porque não existe largura fixa em lugar nenhum — só `max-width`.

A `/conta` tem um ajuste próprio, abaixo de 560px: os pares rótulo/valor deixam a grade de duas
colunas e empilham. A coluna fixa de 90px para os rótulos aperta demais o valor em tela de celular, e
e-mail é justamente o dado mais longo da tela — ele também recebeu `overflow-wrap: anywhere`, que é o
que segura a ausência de rolagem horizontal em 375px.

As telas de acesso não precisaram de media query nenhuma, e isso é consequência de três escolhas
anteriores: a coluna é `max-width: 440px` com `margin: 0 auto`, os campos são `width: 100%`, e o
reset global aplica `box-sizing: border-box` em tudo. Sem o `border-box`, o `padding: 14px` do campo
somaria à largura total e transbordaria a coluna em telas estreitas — é a causa mais comum de rolagem
horizontal em formulário, e ela está desarmada na origem.

## Convenções

- **Server Component por padrão.** `"use client"` só onde há interação que exige o navegador. Hoje
  são quatro ilhas: o `NavLink`, que precisa de `usePathname()` para marcar o item ativo, os dois
  formulários — a exceção prevista no `ARCHITECTURE-SPINE.md#Convenções` — e o `BotaoSair`. `Campo`,
  `Botao` e `AvisoDeErro` **não** levam a diretiva: sem interação própria, ela marcaria como ilha
  algo que não é
- **Estado de sessão é lido no servidor, nunca guardado no cliente.** Sem contexto React de usuário,
  sem `localStorage`, sem estado global
- **Componente compartilhado nasce no segundo uso, nunca no primeiro** — com uma exceção: regra que
  protege acessibilidade vira componente mesmo com poucos usos, porque é o tipo de regra que se perde
  ao copiar
- **CSS Modules por componente** (`Componente.module.css`), com os tokens vindo do `globals.css`.
  Sem folha global gigante e sem colisão de nome de classe
- **Componentes em `PascalCase`**; o domínio continua em português (`evento`, `setor`, `reserva`,
  `ingresso`), igual ao backend e igual ao enunciado do desafio
- **Rotas com substantivo curto em português**: `/ingressos`, `/conta`, `/eventos`. Mesma gramática
  do backend (`/saude`, `/eventos`, `/reservas`)
- **`lang="pt-BR"`** e todo texto de interface em português
- **Sem biblioteca de componentes.** Nada de shadcn, MUI, Chakra. Sistema pronto traz junto o
  vocabulário visual que este projeto está tentando não ter
- **Voz jornalística:** específica, curta, sem entusiasmo comercial, **nunca exclamação**

## Armadilhas do Next 16 que eu já tropecei ou vou tropeçar

- **⚠️ `router.refresh()` depois de toda mudança de sessão.** É a armadilha central da Story 1.6 e
  não dá erro nenhum: a tela navega, o `fetch` acontece, o cookie muda — e o masthead continua
  exibindo o estado antigo, porque é Server Component servido do cache do roteador. São três
  lugares: `FormularioLogin`, `FormularioCadastro` e `BotaoSair`. **Convenção do projeto:** entrou,
  cadastrou ou saiu, chama `refresh()`
- **⚠️ Mas a ORDEM do `refresh()` depende de a página atual sobreviver à mudança.** Descoberto no
  code review da Epic 1. Ao **entrar**, a página onde se está (`/login`) continua acessível depois
  do cookie chegar, então `refresh()` antes do `push` é seguro. Ao **sair**, não: o `BotaoSair` só
  existe na `/conta`, e a `/conta` redireciona para `/login?voltar=%2Fconta` quando não há sessão.
  Chamar `refresh()` primeiro refaz o RSC de uma página que agora responde com esse redirecionamento
  — e ele corre contra a navegação para `/`. Quem vence depende da latência: em `localhost` a ordem
  errada passa despercebida, e na Vercel o `Sair` pode largar a pessoa na tela de login. **Regra:
  saia da rota primeiro, atualize depois** (`router.replace("/")` e então `router.refresh()`). O
  `replace` e não `push` é para a `/conta` não ficar no histórico, senão o botão "voltar" cai numa
  página protegida que rebate para o login
- **`params`, `searchParams` e `cookies()` são `Promise`.** O acesso síncrono foi removido de vez
  (era só depreciado no 15). Sem o `await`, `cookies().get` não existe e `searchParams.voltar` é
  `undefined` — que cai calado no padrão e parece "o voltar não funciona"
- **`redirect()` funciona levantando `NEXT_REDIRECT`** e não pode ficar dentro de `try/catch`, que o
  transformaria numa página em branco. Na `/conta` isso está resolvido por construção: o `try` mora
  dentro do `sessao.ts`, e o que sobra na página é um `if`
- **`fetch` do servidor não herda o cookie** do pedido que está sendo atendido. Sem repassar à mão,
  a página renderiza deslogada com sessão válida — e não há erro nenhum para investigar
- **`next lint` não existe mais.** O script `npm run lint` chama o ESLint direto
- **Turbopack é o bundler padrão**, em dev e no build. Não configure webpack, não adicione flag
- **O `create-next-app` gera coisa que viola o projeto.** Ele importa a fonte `Geist` de
  `next/font/google` e escreve um `globals.css` com variáveis próprias e bloco de
  `prefers-color-scheme`. Tudo isso foi arrancado — se você regerar o template algum dia, arranque
  de novo. **O que sobreviveu escondido até o code review da Epic 1 foi o `favicon.ico`**: o
  triângulo da Vercel, 25.931 bytes, na aba do navegador de um projeto que está sendo avaliado.
  Trocado por `src/app/icon.svg`, próprio. Convenção do App Router: `icon.svg` em `app/` vira o
  ícone da aba sozinho, e o `favicon.ico` **tem precedência sobre ele** — por isso o arquivo antigo
  precisou ser apagado, não só acompanhado
- **`.gitignore` só existe na raiz.** O que o `create-next-app` cria aqui é redundante; a única
  regra que ele tinha a mais (`next-env.d.ts`) eu movi para o arquivo da raiz

### `/` deixou de ser estática, e está certo

Desde a Story 1.6 o `npm run build` marca **todas** as rotas com `ƒ` (renderizadas sob demanda), a
raiz inclusive. O masthead lê `cookies()`, e isso torna dinâmica toda rota do grupo `(site)`; as
telas de acesso ficaram dinâmicas por lerem `searchParams`.

**É o comportamento correto**, não uma regressão: uma página cujo cabeçalho depende de quem pediu não
pode ser pré-renderizada — a versão em cache mostraria `Entrar` para quem está logado. Não tente
consertar com `export const dynamic` nem tirando o masthead do layout.

## Sobre não ter teste automatizado aqui

**Não há teste no frontend, e isso é decisão, não esquecimento.** O desafio não exige teste, o prazo
é de 7 dias, e as invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o
mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a
primeira story. Montar Vitest e Testing Library aqui custaria configuração para cobrir markup que
ainda vai mudar muito.

A verificação desta camada é:

```bash
npm run build      # tem que passar
npx tsc --noEmit   # sem erro
npm run lint       # limpo
```

mais a conferência no navegador: fundo escuro, fio duplo fechando o masthead e `Tab` desenhando o
contorno âmbar em todo link.

O preço disso é que **a reescrita de um formulário já entregue não tem rede de proteção** — foi
exatamente o caso da Story 1.5, ao extrair `Campo` e `Botao` do login. Os 73 testes do backend não
olham para o markup, e na 1.6 isso pesou mais que o normal: o `router.refresh()` esquecido não quebra
build, não quebra tipo e não quebra lint. Só a tela mente.

A lista da sessão, acrescentada na 1.6:

- **Sem sessão:** `/` abre normalmente e o masthead mostra `Início` · `Entrar`
- **`/conta` sem sessão** cai em `/login?voltar=%2Fconta`; entrar leva de volta a `/conta`, não a `/`
- **`?voltar=` forjado** — `//exemplo.com`, `https://exemplo.com`, `javascript:alert(1)`,
  `/\exemplo.com`, `/login` — leva a `/`, nunca para fora do site
- **Com sessão:** o masthead mostra `Início` · `Minha conta`, e a `/conta` traz nome, e-mail e papel
- **`Sair` volta para `/` e o masthead vira `Entrar` na hora**, sem recarregar a página à mão. É a
  verificação do `router.refresh()`, e é a que não tem substituto automatizado
- **Cookie apagado à mão no DevTools + abrir `/conta`** → redireciona para o login
- **`Tab`** percorre a navegação do masthead e a `/conta` inteira com contorno âmbar
- **Janela em 375px na `/conta`:** nada transborda, sem rolagem horizontal

E a lista original das telas de acesso:

- **Login, com credenciais certas:** o DevTools mostra o cookie `rockhub_sessao` no domínio
  `localhost:3000`, com `HttpOnly` marcado, e a aba Network mostra a chamada indo para
  `/api/auth/login`, nunca para `localhost:8000`. É a verificação literal de que o proxy está no
  caminho. `document.cookie` no console **não** pode mostrar o cookie: isso é o `httpOnly` funcionando
- **Cadastro:** criar conta cai em `/` já logado, com o mesmo cookie; repetir o mesmo e-mail mostra a
  mensagem de conta existente e um `409` no Network; e **senhas diferentes mostram "As senhas não
  conferem." sem nenhuma requisição** — se aparecer chamada no Network, a confirmação vazou para o
  backend
- **Sair e entrar pelo `/login` com a conta recém-criada.** É a prova de que hash e normalização de
  e-mail batem entre as duas rotas
- **`Tab` percorre** nome → e-mail → senha → repetir → botão → link, com contorno âmbar em todos, e os
  links levam de uma tela à outra sem digitar URL

### E a mesma lista, em produção

Desde a Story 1.9 as verificações acima deixaram de valer só em `localhost`. Contra
<https://elite-dev-rock-hub.vercel.app>, o que eu confiro depois de todo deploy — e que **nenhum
`curl` substitui**, porque as três primeiras só existem no navegador:

- **O masthead muda ao entrar e ao sair, sem recarregar a página.** É o `router.refresh()` da Story
  1.6 sobrevivendo à build de produção. Não há teste que o cubra, em ambiente nenhum
- **A aba Network mostra `/api/...` no domínio da Vercel**, nunca em `up.railway.app`. Se aparecer o
  domínio da Railway ali, o proxy foi contornado por alguém e o cookie vai parar de funcionar
- **`document.cookie` no console não mostra o `rockhub_sessao`** — é o `httpOnly` valendo em
  produção, e o cookie está no domínio da Vercel, não no da API
- **A URL abre em janela anônima**, sem tela de login da Vercel. Se pedir, é a URL gerada por deploy
  em vez do domínio de produção
- **A `/conta` sem sessão cai em `/login?voltar=%2Fconta`** e devolve para a `/conta` depois de
  entrar — o mesmo comportamento de `localhost`, agora atravessando dois fornecedores

O que o `curl` cobre — raiz, 404 com a casca, `401` sem cookie, login nas quatro contas e os
atributos do `Set-Cookie` — está em [Como saber que deu certo](#4--como-saber-que-deu-certo).

## Histórico desta camada

Até a Story 1.8 o histórico desta camada morava dentro de cada seção, junto do assunto — é onde ele
é mais útil de ler. Abro a seção aqui porque a Story 1.9 não cabe em nenhuma delas: ela não mudou
comportamento nenhum do frontend, e ainda assim é a story mais importante desta pasta até agora.

### Story 1.9 — frontend no ar na Vercel

**Não escrevi uma linha de `src/` nesta story, e esse era o ponto.** O proxy `/api/*` foi escrito na
Story 1.4 exatamente para o dia em que as duas metades ficassem em fornecedores diferentes; a Story
1.9 só deu a ele o endereço de produção, numa variável de painel. O login funcionou na primeira
tentativa em que o build estava correto — o cookie atravessou `vercel.app` → `up.railway.app` sem
ajuste nenhum, que é o retorno daquela decisão pagando com juros.

O que essa story **não** foi: um dia de depurar cookie entre domínios. Está registrado assim de
propósito, porque era o desfecho provável se eu tivesse deixado o `SameSite` cru para resolver no
deploy — e eu cheguei a considerar isso na 1.4.

**O tropeço real veio de onde eu não estava olhando: o `.gitignore`.** O primeiro build com a branch
e o Root Directory já corretos falhou com `Module not found` em sete arquivos — `BotaoSair`, os dois
formulários, as três páginas e o `Masthead`. O denominador comum era exato: **os sete importam de
`@/lib`**, e nenhum import de `@/components` aparecia no rastro.

A causa: o `.gitignore` da raiz veio do template Python do GitHub, e ele traz `lib/` na seção de
empacotamento. Padrão sem barra no início **casa em qualquer profundidade** — então ele estava
ignorando `frontend/src/lib/` desde a Story 1.2. Os três arquivos (`api.ts`, `sessao.ts`,
`caminho.ts`) existiam na minha máquina e **nunca entraram no repositório**.

Duas coisas que eu levo daqui:

- **Nada na minha máquina podia ter pego isso.** `npm run build`, `tsc --noEmit`, ESLint e os 85
  testes do backend passam todos, porque os arquivos estão no disco. Só um clone limpo revela — e o
  primeiro clone limpo deste projeto foi o da Vercel. Foi o deploy fazendo trabalho de teste
- **O conserto foi ancorar, não abrir exceção.** Troquei `lib/` e `lib64/` por `/lib/` e `/lib64/`,
  com a barra inicial prendendo o padrão à raiz do repositório. Descartei o `!frontend/src/lib/`,
  que consertaria este caso e deixaria a armadilha armada para a próxima pasta `lib/` aninhada, em
  qualquer camada — e o motivo está escrito em comentário no próprio `.gitignore`, para ninguém
  "limpar" a barra depois

Os dois campos do painel que eu já sabia que iam morder morderam, os dois — `Root Directory` em `./`
e Production Branch em `main` —, e os dois estavam previstos porque a Story 1.8 já tinha cometido os
mesmos dois erros no painel da Railway. Estão documentados em [Deploy na Vercel](#deploy-na-vercel)
com o sintoma de cada um. Dois fornecedores diferentes, as mesmas duas armadilhas.

### Story 2.1 — cliente da Ticketmaster com a chave protegida

**Nenhum arquivo desta pasta mudou nesta story**, e isso não é esquecimento — é o AD-2 funcionando.
A Story 2.1 deu ao backend um cliente da Ticketmaster Discovery (`app/integrations/ticketmaster.py`),
e a chave (`TICKETMASTER_API_KEY`) viaja só pelo processo do backend: nenhuma variável
`NEXT_PUBLIC_` de credencial existe aqui, nem vai existir. Se um dia o frontend precisar chamar o
catálogo, é o backend quem consulta a Ticketmaster e devolve o formato próprio do projeto — o
navegador nunca vê `apikey=` na URL. Confirmado por busca: `ticketmaster` e `NEXT_PUBLIC` não
aparecem em `frontend/` nenhuma vez.
