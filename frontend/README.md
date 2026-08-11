# RockHub — frontend

Next.js 16 com App Router, TypeScript e React 19. É a interface da plataforma: a programação de
shows, a compra, o ingresso com QR e a tela de validação da portaria. A API vive em
[`../backend`](../backend/README.md) e este projeto só a consome.

Hoje está de pé a casca — o sistema visual "jornal noturno" aplicado, o masthead, a raiz em estado
vazio e um 404 com a cara do projeto —, as **duas telas de acesso**, login e cadastro, o **ciclo
de sessão fechado**: o masthead sabe quem está do outro lado, existe uma `/conta` com os dados e o
botão de sair, e quem abre uma página protegida sem sessão é levado ao login e devolvido ao destino
depois de entrar — e a primeira tela **restrita por papel**: `/organizador/publicar`, onde o
organizador busca a atração no catálogo da Ticketmaster para publicar um evento (passo 1 de 3; os
outros dois chegam nas Stories 2.4 e 2.5).

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
| `Module not found` em vários arquivos de uma vez, sempre no mesmo import | Uma pasta existe na sua máquina e **não no repositório**. Aconteceu comigo na Story 1.9: o `.gitignore` da raiz veio do template Python, que traz `lib/` — e padrão sem barra inicial casa em **qualquer profundidade**, então ele ignorava `frontend/src/lib/` desde a 1.2. Nada local pega isso (`npm run build` e `tsc` leem o disco, não o índice do git); só um clone limpo revela. O conserto foi ancorar o padrão (`/lib/`), não abrir exceção |
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

### E o caminho do servidor: `src/lib/servidor.ts` e `sessao.ts`

`api.ts` é o caminho do **navegador**. A leitura de dado a partir de um Server Component é outro
arquivo, e a separação não é organização — é obrigatória: `api.ts` é importado pelos formulários,
que são `"use client"`, e `next/headers` num módulo que chega ao bundle do cliente **quebra o
build**. A fronteira aqui é física.

**`src/lib/servidor.ts` nasceu na Story 2.2**, quando `catalogo.ts` se tornou o segundo consumidor
do que até então era detalhe interno do `sessao.ts`: `API_URL`, o aviso de `API_URL` ausente em
produção, o nome do cookie e `cabecalhoDeSessao()` — a função que devolve `{ Cookie: string } |
null` a partir do cookie da requisição. O corpo de `obterUsuarioDaSessao` não mudou de
comportamento ao ser extraído — o `cache()`, o curto-circuito sem cookie e o `console.error` do
`catch` são exatamente os que o code review da Epic 1 conquistou, só que agora chamando
`cabecalhoDeSessao()` em vez de repetir a leitura do cookie.

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
        page.tsx              # raiz — a programação pública (Story 3.1)
        page.module.css       # a fila de jornal em quatro colunas, e o colapso em duas
        conta/
          page.tsx            # Server Component com a guarda de sessão
          page.module.css
        organizador/
          publicar/
            page.tsx          # Server Component — passos 1 (2.2), 2 (2.4) e 3 (2.5); a escolha vem da URL
            page.module.css   # classes dos três passos, da linha de setor e da confirmação
          eventos/            # "Meus eventos" (Story 2.6) — só leitura, sem uma linha de "use client"
            page.tsx          # a lista, partida em "Em cartaz" e "Já aconteceram"
            page.module.css   # compartilhado com o detalhe: mesmo vocabulário de fila e inventário
            [id]/
              page.tsx        # o detalhe: inventário setor a setor e quem está na porta
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
      FormularioPublicacao.tsx # "use client" — a primeira ilha fora das telas de acesso (2.4/2.5)
      BotaoSair.tsx           # "use client" — logout + router.refresh()
    lib/
      api.ts                  # chamarApi + ErroDaApi — o caminho do navegador
      servidor.ts             # API_URL + cabecalhoDeSessao() — o que os três módulos de servidor compartilham
      sessao.ts               # obterUsuarioDaSessao() — só servidor
      catalogo.ts             # buscarNoCatalogo() — só servidor (Story 2.2)
      portarias.ts            # listarPortarias() — só servidor (Story 2.5)
      eventos.ts              # listarMeusEventos() e obterMeuEvento() — só servidor (Story 2.6)
      programacao.ts          # listarProgramacao() — só servidor, e o único sem cookie (Story 3.1)
      formato.ts              # data, hora e dinheiro em pt-BR — módulo puro, os dois lados o usam (2.6)
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

Ele virou Server Component `async`: lê a sessão e monta a navegação a partir dela — e, desde a
Story 2.2, também a partir do **papel**.

| Estado | Navegação |
|---|---|
| Sem sessão | `Início` · `Entrar` |
| Com sessão, papel `CLIENTE` ou `PORTARIA` | `Início` · `Minha conta` |
| Com sessão, papel `ORGANIZADOR` | `Início` · `Publicar evento` · `Minha conta` |

**`Meus ingressos` e `Meus eventos` saíram do masthead** até as Stories 4.1 e 2.6 criarem as telas.
É o precedente que firmei na 1.4: link que cai no 404 não fica no repositório — e ele valeu de novo
na 2.2, quando fiquei tentado a incluir `Meus eventos` "já que estava ali".

`Publicar evento` é a primeira entrada do masthead condicionada a **papel**, não só a sessão existir
ou não. O `usuario?.papel === "ORGANIZADOR"` mora no próprio `Masthead.tsx`: entrando como cliente
ou portaria o link **não existe no HTML**, nem escondido por CSS — a decisão é do servidor, antes de
qualquer coisa chegar ao navegador.

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

## A tela do organizador: `/organizador/publicar`

Três passos, na mesma tela: buscar a atração no catálogo da Ticketmaster (Story 2.2), preencher
data, local e setores (Story 2.4) e escalar quem valida na porta (Story 2.5).

### A escolha da atração vive na URL, como a busca

Clicar numa fila do catálogo não muda estado: **segue um `<Link>`**. O destino é a mesma página com
um parâmetro a mais — `?q=baco&escolhido=G5vYZ9a1kd` —, o Next re-renderiza no servidor, a fila
escolhida ganha o fio âmbar e o passo 2 aparece abaixo.

É a mesma decisão da busca da 2.2, estendida em vez de contradita, e ela paga três coisas de graça:
recarregar mantém a escolha, o botão voltar a desfaz, e o link abre no mesmo lugar para outra
pessoa. A alternativa — `onClick` guardando a escolha em `useState` — mostraria o passo 2 sem
recarregar, e é o que qualquer formulário moderno faria; caiu porque tiraria a escolha da URL e
transformaria a página **inteira** em ilha de cliente, contra a convenção *"Server Component por
padrão"*. O motivo completo, com a terceira alternativa que também caiu (uma rota
`/organizador/publicar/[id]`), está no [README da
raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

```tsx
const parametros = new URLSearchParams();
if (termoLimpo) parametros.set("q", termoLimpo);
parametros.set("escolhido", idExterno);
return `/organizador/publicar?${parametros}#passo-2`;
```

⚠️ **O `#passo-2` no fim do destino não é enfeite, e ele veio de um defeito real.** Sem a âncora,
escolher uma atração deixava a pessoa exatamente onde estava, com o passo 2 nascendo abaixo da
dobra — clicar na fila parecia **não fazer nada**, e o formulário só era encontrado por quem
rolasse a página até o rodapé. A âncora resolve isso pela **navegação**: o `<Link>` leva até o passo
2 porque o destino é o passo 2. Nenhum `onClick`, nenhum `useEffect`, nenhuma linha de
`"use client"` a mais — e o link continua compartilhável, agora apontando para o lugar certo da
página. O `scroll-behavior: smooth` fica no `html` do `globals.css`, e o bloco de
`prefers-reduced-motion` que já existia lá o desliga para quem pediu menos movimento.

⚠️ **`URLSearchParams` e para por aí.** `q` chega na `page.tsx` já decodificado pelo Next, e
concatenar um `encodeURIComponent` à mão em cima disso produz `%2520` e uma busca que não acha nada.

⚠️ **`?escolhido=` sobrevive à troca do termo**, e o comportamento certo é o passo 2 sumir. Buscar
"baco", escolher e depois buscar "rosalia" deixa na URL um id que não está mais na lista; o `find`
devolve `undefined` e a tela volta a ter só o passo 1 — sem erro, sem aviso, sem nada quebrado. É
por isso que **nunca** uso `!` para calar o TypeScript aqui: `undefined` é um estado real da tela,
não um caso impossível.

### `FormularioPublicacao` é a primeira ilha `"use client"` fora das telas de acesso

Login e cadastro são ilhas porque são formulários. Esta é a primeira vez que um formulário convive
na **mesma página** com conteúdo renderizado no servidor, e a fronteira entre os dois é a prop
`item`, que atravessa serializada.

A ilha existe por um motivo que dá para apontar com o dedo: `+ Adicionar setor` e o `×` de remover
mudam a quantidade de campos na tela a cada clique, e isso é interação que exige o navegador. O que
**não** está na ilha continua no servidor: masthead, busca, catálogo, e a página que decide qual
atração foi escolhida.

Dentro dela, só os setores têm `useState`. Os campos do evento — data, horário, casa de show, cidade
— são lidos por `FormData` no envio, sem estado, exatamente como no `FormularioCadastro`: eles não
mudam de quantidade, então não precisam ser controlados.

Nome e imagem da atração aparecem **travados**, e são texto, não `<input readOnly>`: campo que
ninguém pode editar é campo que não deveria ser campo. `local` e `cidade` chegam pré-preenchidos do
catálogo e **são editáveis** — o porquê disso (turnê) está no README da raiz.

### A conversão de reais para centavos mora aqui, na fronteira

A API só conhece `preco_centavos: int` (AD-11). O organizador digita `120,00`, e a conversão
acontece no cliente, antes do `POST`:

```ts
const normalizado = bruto.includes(",")
  ? bruto.replace(/\./g, "").replace(",", ".")   // "1.234,50" → "1234.50"
  : bruto;                                        // "120.50" já está pronto
if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;
return Math.round(Number(normalizado) * 100);
```

A regra evita adivinhar: **com vírgula**, ela é o decimal e o ponto é milhar; **sem vírgula**, o
ponto é o decimal. Assim `"1.234"` não vira 123.400 por chute — ele falha no teste da regex, devolve
`null` e vira erro na tela **antes** de qualquer ida à rede. Mesma disciplina das duas validações
locais do `FormularioCadastro`.

Ela mora no cliente porque a alternativa é pior: aceitar decimal na API poria ponto flutuante no
contrato, que é exatamente o que o AD-11 existe para impedir. O motivo completo está no README da
raiz.

⚠️ **A junção de data com hora não é estética.** `new Date("2026-08-14")` — data sozinha — é lida
como **UTC** pela especificação; `new Date("2026-08-14T21:00")` — data com hora, sem offset — é lida
como **hora local**. Mandar só a data faria um show das 21h em São Paulo virar 18h na tela de quem
compra, e o sintoma só apareceria em produção, porque quem testa costuma olhar a resposta da API e
não o horário renderizado. O `toISOString()` do resultado é o que vira `data_hora` no corpo.

### Publicar não leva a lugar nenhum, e é de propósito

Deu certo, a confirmação toma o lugar do formulário na mesma tela: nome, data por extenso, local,
cidade e a lista de setores com **capacidade e preço exatos**. Números exatos e nenhum medidor —
proporção é para quem compra; organizador vê inventário (UX-DR7).

Sem `router.push` e sem `router.refresh` — e desde a Story 2.6 **por outro motivo**. Na 2.4 era "não
há para onde mandar alguém": `Meus eventos` não existia, e a raiz era o estado vazio da programação.
Agora existe para onde ir, e eu decidi continuar sem redirecionar: esta confirmação é o recibo da
publicação, e é a **única** vez que o organizador vê o inventário e quem ficou com a porta. Não há
tela de editar evento onde conferir depois. Saltar para a lista assim que o `POST` responde apagaria
justamente isso — a lista mostra os totais, não a escala.

Os caminhos de saída são dois, e nenhum é obrigatório: `Publicar outro →`, que leva à URL limpa, e
`Ver meus eventos →`, que entrou na 2.6 junto com a tela para onde aponta.

Desde a Story 2.5 a confirmação também lista, **por nome**, quem ficou com a porta — abaixo do
inventário de setores, sob o kicker `Na porta`. É a única confirmação da escala que o organizador
recebe: não há tela de editar evento, e descobrir depois que escalou a pessoa errada não teria
conserto.

O erro vem pelo `codigo`, nunca pela `mensagem` do servidor — convenção desde a Story 1.4. Os
códigos desta tela são `EVENTO_SEM_SETOR`, `SETOR_DUPLICADO` (2.4), `EVENTO_SEM_PORTARIA` e
`PORTARIA_INVALIDA` (2.5). O texto de `PORTARIA_INVALIDA` **não diz qual** conta falhou, porque o
backend não distingue "não existe" de "não é portaria", de propósito — a tela não inventa uma
precisão que a resposta não tem, e manda recarregar, que é o conserto real.

### O passo 3: escalar a portaria (Story 2.5)

O bloco fica **dentro do mesmo `<form>` do passo 2**, e isso é a decisão inteira: é uma publicação
só, um `POST` só, e a escala nasce atômica com o evento. Dois formulários dariam a impressão de duas
ações independentes, e a primeira poderia terminar sem a segunda — que é exatamente o evento sem
portaria que o AD-7 existe para impedir.

**O título do passo 3 mora na ilha, não na `page.tsx`.** Os títulos dos passos 1 e 2 são da página, e
continuam de pé o tempo todo. O do passo 3 pertence ao formulário e precisa **desaparecer junto com
ele** quando a confirmação toma o lugar: um "3 · Escale a portaria" sozinho, acima de um recibo de
evento publicado, é uma instrução para fazer o que já foi feito.

**A busca por nome acontece em memória, não como `?q=` na rota.** A lista inteira já viaja para a
tela (são poucas contas de portaria), e filtrar no cliente responde a cada tecla sem ida à rede. Um
`q` no endpoint seria a saída se a lista crescesse, e aí o filtro passaria a ser estado de servidor
dentro de uma ilha que já é cliente. Trocar depois é barato; começar assim é o que custa menos hoje.

⚠️ **Filtrar é ver menos, não desmarcar.** A fonte da verdade é um `Set` de ids; a lista filtrada é só
a vista. Se a marcação fosse derivada da lista visível — por índice, por exemplo —, digitar no campo
de busca apagaria a escala. Marcar "Ana", procurar "jonas", marcar "Jonas" e publicar grava **os
dois**.

⚠️ **Enter no campo de busca não publica o evento.** Um campo de texto dentro de um `<form>` envia o
formulário quando alguém aperta Enter, e aqui isso publicaria no meio de uma consulta. O campo filtra
a cada tecla, então não há nada para confirmar — o `onKeyDown` chama `preventDefault` e pronto.

O rótulo é **"Consulte pelo nome da conta"**, visível, e não um `placeholder`: `placeholder` não
conta como rótulo (UX-DR9), e aqui ele carrega informação que ninguém adivinha — que se digita o
nome, não o e-mail. A quantidade de escalados aparece em **texto** (`2 escalados`), e não só pelo
estado visual das marcações, pela mesma regra: nenhuma informação só por cor ou só por forma. Cada
linha tem `<label htmlFor>` e 44px de alvo.

**Sem nenhuma conta de portaria, ou com a lista indisponível, a tela não quebra.** `listarPortarias`
nunca levanta (ver abaixo), e o passo 3 vira uma frase explicando que não há quem escalar e que sem
isso o evento não pode ser publicado — kicker, frase, fim, sem ilustração e sem botão grande
(UX-DR8). O formulário continua de pé.

E a recusa por não ter escalado ninguém acontece **antes** da ida à rede, com a mesma disciplina de
validação local do `FormularioCadastro`: o servidor recusaria igual, e evitar a viagem é retorno
imediato.

### Rótulo oculto não é rótulo ausente

A linha de setor tem quatro colunas no desktop e uma faixa de kickers acima nomeando cada uma. Essa
faixa é decoração: ela é `aria-hidden` e serve a quem enxerga. Quem serve a quem **não** enxerga é
um `<label htmlFor>` em cada entrada, escondido pelo padrão "visually hidden" (`position:absolute;
width:1px; clip-path: inset(50%)`) — nunca `display:none`, que tiraria o rótulo da árvore de
acessibilidade e é exatamente o que o UX-DR9 proíbe. `placeholder` não conta como rótulo.

Abaixo de 900px a grade vira uma coluna e a faixa de kickers some — e **o rótulo oculto volta a
ser visível**, na mesma media query. Sem a faixa acima, "Pista" e "800" empilhados não diriam qual é
qual para quem enxerga; o `<label>` já estava lá, e só precisou deixar de estar escondido.

### A busca é `<form method="get">`, sem uma linha de `"use client"`

```tsx
<form method="get">
  <input name="q" defaultValue={termo} />
  <Botao type="submit">Buscar</Botao>
</form>
```

Sem `action`: o formulário envia para a própria URL, o navegador monta `?q=…` sozinho, o Next
re-renderiza no servidor com o termo novo. A busca inteira é `zero JavaScript, zero estado`. Foi a
decisão que mais pesei nesta story, contra um `Client Component` com `chamarApi` — que reusaria mais
código (`AvisoDeErro`, o tratamento por `codigo`), mas tiraria a busca da URL (nada de recarregar,
compartilhar ou voltar), transformaria a tela inteira em ilha de cliente contra a convenção *"Server
Component por padrão"*, e faria o estado do resultado morar em dois lugares quando a Story 2.4
acrescentar os passos 2 e 3. A alternativa completa, com o motivo de cada peça descartada, está no
[README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

`defaultValue`, nunca `value`: com `value` sem `onChange` o campo vira somente-leitura e o React
avisa no console. `defaultValue` é o certo para campo não controlado, que é exatamente o que este é
— o servidor manda o valor inicial, o navegador cuida do resto.

### A tela busca sempre — não existe mais um "ninguém buscou ainda"

⚠️ **Revisado no mesmo dia, depois do primeiro corte da story.** A primeira versão tinha um terceiro
estado — "ninguém buscou ainda", com um convite curto e nenhuma chamada à Ticketmaster — igual ao
padrão de estado vazio do resto do site. Testando a tela, o Igor pediu o contrário: que ela já
chegue mostrando exemplos reais do catálogo, para o organizador ver do que se trata sem precisar
digitar nada primeiro. `page.tsx` agora chama `buscarNoCatalogo(termoLimpo)` sempre, mesmo com
`termoLimpo` vazio — e é `catalogo.ts` → a rota do backend quem decide o que "sem termo" significa
(ver [Catálogo da Ticketmaster](../backend/README.md#catálogo-da-ticketmaster) no README do
backend: sem termo, sem `keyword`, com `sort=date,asc`).

Restaram dois estados vazios, e `itens.length === 0` continua verdadeiro nos dois — achatá-los
continua sendo o defeito mais fácil de cometer:

| Situação | O que a tela diz |
|---|---|
| Sem resultado, sem termo (listagem padrão vazia) | "Não há shows no catálogo agora." |
| Buscou um termo, não achou | "Nenhum show encontrado para essa busca." — literal do `EXPERIENCE.md#Vazio` |
| Catálogo fora do ar (com ou sem termo) | "O catálogo da Ticketmaster não respondeu. Tente de novo em instantes." |

O terceiro é escolhido pelo **estado** que `buscarNoCatalogo` devolve
(`{ estado: "ok" | "indisponivel" }`), nunca por uma exceção pega no meio do caminho — não existe
`error.tsx` neste projeto, e uma exceção não capturada num Server Component derruba a página
inteira, não só esta seção. É por isso que `catalogo.ts` **nunca levanta**: `try/catch` em volta do
`fetch`, e `!resposta.ok` também vira `"indisponivel"`.

**O que caiu:** uma fileira de termos sugeridos e clicáveis ("chips") — Metallica, Baco Exu do
Blues — que só disparariam a busca de verdade ao clicar. Preservaria a cota de quem só abre a tela
para olhar, mas exigiria manter uma lista de sugestões própria (fixa no código, ou vinda de algum
outro lugar — escopo novo) e não mostraria nada real antes do clique. A alternativa completa está
no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

### `src/lib/catalogo.ts` reusa a armadilha que `sessao.ts` já tinha resolvido

O `fetch` do servidor não herda o cookie do pedido que está sendo atendido — é a mesma armadilha que
o `sessao.ts` resolve desde a Story 1.9, e `catalogo.ts` precisava resolver de novo. Daí
`servidor.ts` ter ganhado `cabecalhoDeSessao()` nesta story, em vez de `catalogo.ts` reimplementar a
leitura do cookie por conta própria: sem o cabeçalho repassado à mão, o backend responde `401`, o
`!resposta.ok` vira `"indisponivel"`, e a tela diz "o catálogo não respondeu" quando o catálogo
respondeu perfeitamente — o sintoma aponta para o lugar errado, e é o motivo de esta ser a armadilha
mais cara da story.

A segunda: `encodeURIComponent(termo)` ao montar a query. Sem ele, buscar `AC/DC & Guns` monta
`?q=AC/DC & Guns`, o `&` encerra o parâmetro `q`, e o backend recebe `q=AC/DC ` mais um parâmetro
`Guns` que ninguém pediu.

`src/lib/portarias.ts` (Story 2.5) nasceu no **molde exato** deste arquivo: resultado discriminado
(`{ estado: "ok" | "indisponivel" }`), `try/catch` que nunca levanta, `cache: "no-store"` e o
`cabecalhoDeSessao()` repassado à mão. A disciplina é a mesma e o motivo também: não existe
`error.tsx` neste projeto, e uma exceção não capturada num Server Component derrubaria a página
inteira — aqui, o formulário de publicação junto com a lista.

A `page.tsx` só chama `listarPortarias()` **quando há atração escolhida**. Sem ela não existe passo 3
na tela, e buscar a lista a cada busca no catálogo seria uma chamada por consulta que ninguém lê.

#### Nem todo `!resposta.ok` é "o fornecedor não respondeu"

Correção do code review da Epic 2, e ela é a continuação exata do parágrafo acima. Eu tinha
resolvido o **sintoma** (repassar o cookie) e deixado a **causa** de pé: qualquer status não-ok
virava `indisponivel`, então a tela seguia capaz de acusar a Ticketmaster por erro que não era dela.

| Status | Era | É | Por quê |
|---|---|---|---|
| `401`, `403` | `indisponivel` | `sem-sessao` | A sessão morreu. "Tente de novo em instantes" nunca se cumpre — o conserto é entrar de novo, e a tela agora oferece o link |
| `422` | `indisponivel` | `busca-invalida` | O termo passou dos 120 caracteres da rota. A Discovery **nem chegou a ser chamada** |
| Demais | `indisponivel` | `indisponivel` | Aí sim é o fornecedor |

O `src/lib/eventos.ts` já fazia essa separação desde a 2.6 (ele distingue `nao-encontrado` de
`indisponivel`); foram `catalogo.ts` e `portarias.ts` que ficaram para trás. O campo de busca também
ganhou `maxLength={120}`, para o `422` deixar de ser alcançável pela interface.

**A mesma raiz aparecia no envio do formulário**, e ali era pior. `mensagemParaCodigo` não conhecia
`NAO_AUTENTICADO` nem `SEM_PERMISSAO`, então um `POST` com sessão expirada caía na mensagem genérica
"tente de novo em instantes" — e tentar de novo dava `401` outra vez, para sempre, com todos os
setores digitados na tela e nenhum caminho para o login. As guardas da `page.tsx` rodam na
**renderização**, não no envio, e a sessão dura 8 horas contra uma tela longa (catálogo → data e
local → N setores → escala).

O aviso agora leva um `<Link>` com `target="_blank"`, e o alvo em nova aba não é detalhe: sair da
página descartaria o formulário inteiro, que é justamente o que a correção existe para evitar. Foi
por isso que o `AvisoDeErro` passou a aceitar `ReactNode` em vez de `string`.

**Outras cinco do mesmo review, todas de "a tela deixa fazer o que a API recusa":** `max` na
capacidade e `Number.isSafeInteger` no preço (acima do inteiro seguro o `Math.round` arredondava
errado e enviava valor diferente do digitado); `min` de hoje no seletor de data, junto com o
`EVENTO_NO_PASSADO` novo do backend; o botão `+ Adicionar setor` some no vigésimo, e marcar a 21ª
portaria avisa em vez de deixar publicar e receber `422`; `if (enviando) return` em `aoEnviar`,
porque o `disabled` do botão só vale depois do próximo render e não segura `Enter` mantido
pressionado; e o kicker que faltava no cabeçalho de `Meus eventos` — é ele que aparece no estado
vazio, quando nenhuma seção é renderizada (AC14).

### A imagem é `<img>`, não `next/image`

A Discovery serve imagem de mais de um host (`s1.ticketm.net`, `media.ticketmaster.com`), e
`next/image` exige `remotePatterns` declarado por host — errar um produz erro em tempo de execução,
na tela do organizador. `<img loading="lazy">` com dimensão fixa no CSS (70×70px, `object-fit:
cover`) resolve sem essa dependência, com o
`// eslint-disable-next-line @next/next/no-img-element` acompanhado do motivo, no próprio código.
Sem `imagem_url`, o bloco fica com o fundo `--breu2` do mesmo tamanho — a grade não pode dançar
entre uma fila e outra.

A linha de origem (`Ticketmaster · <local> · <cidade>`) monta só o que existe: `local` e `cidade`
podem ser `null`, e um `.filter(Boolean).join(" · ")` evita o `Ticketmaster ·  · ` cheio de buracos
que sobraria de concatenar direto.

⚠️ **O `id_externo` já esteve nessa linha, e saiu** — num commit avulso, fora da numeração das
stories, junto do filtro de classificação do catálogo
([techspec](../docs/techspec-filtro-do-catalogo.md)). Ela era
`Ticketmaster · ZFIMVHTNMZ17KBX_ · Qualistage · Rio de Janeiro`. Aquele código identifica o show
para o **código**, não para quem escolhe o que publicar: quem olha reconhece pelo nome, pela casa e
pela cidade, que já estão do lado. O id não sumiu do sistema — continua vindo da API, continua sendo
a `key` de React da lista e continua indo para `origem_externa_id` na publicação; só não aparece
mais. A alternativa era mantê-lo por rastreabilidade — dá para conferir o evento direto na Discovery
se a publicação sair errada —, e caiu porque ninguém no fluxo avaliado faz isso, e um hash de API
atravessado numa tela que imita jornal impresso é ruído na parte que carrega a identidade.

### Duas guardas, e por que a segunda não é `notFound()`

```ts
if (!usuario) redirect("/login?voltar=%2Forganizador%2Fpublicar");
if (usuario.papel !== "ORGANIZADOR") redirect("/");
```

O padrão da guarda é o mesmo da `/conta` (ler a sessão, `redirect` na página, sem `middleware` — ver
[A guarda mora na página](#a-guarda-mora-na-página-não-em-middleware)). O que é novo aqui é a
segunda linha: **papel errado vai para a raiz, não para um 404.** Um cliente que digitar
`/organizador/publicar` na barra é mandado para a programação, não para `notFound()`. Cogitei o
404 — reusaria o `not-found.tsx` que já existe e não revelaria que a rota existe —, mas mandar
alguém **logado** para um 404 parece defeito de navegação, e a rota não é segredo nenhum: a API
responde `403`, que é público por natureza. Fica registrado como suposição minha, não decisão de
produto — é uma linha para trocar se eu discordar depois de ver a tela no ar.

## Meus eventos: `/organizador/eventos` e `/organizador/eventos/[id]`

As duas telas da Story 2.6, e as **primeiras telas de leitura de domínio** do projeto — todas as
anteriores ou eram formulário (login, cadastro, publicar) ou eram vista de um dado externo (o
catálogo). Nenhuma das duas tem uma linha de `"use client"`: não há interação nenhuma aqui, só
leitura e navegação.

As guardas são as mesmas duas de `/organizador/publicar`, com o `?voltar=` trocado. O papel errado
continua indo para a raiz, e não para `notFound()`, pelo motivo já registrado acima.

### `src/lib/formato.ts`, e por que ele precisou existir

Esta é a terceira vez que uma função sai de onde nasceu para virar módulo compartilhado, e a primeira
em que o motivo é **físico**, não estético.

`dataPorExtenso`, `momentoDaPublicacao` e `centavosParaReais` moravam dentro do
`FormularioPublicacao.tsx`, que é uma ilha `"use client"`. Quando as telas novas precisaram das
mesmas formatações, importá-las de lá não era uma opção ruim — era **impossível**: o Next transforma
cada export de um módulo `"use client"` numa *client reference*, e chamá-la de um Server Component
estoura em tempo de execução, não em build. (Elas nem eram exportadas, para começo de conversa.)

As duas saídas erradas eram copiar as três funções para as telas novas — segunda fonte para o mesmo
formato de data, e no dia em que uma mudasse ninguém saberia qual está certa — e marcar as telas
novas como `"use client"`, que é jogar fora o Server Component por causa de um `Intl.DateTimeFormat`.

O `formato.ts` é um **módulo puro**: nenhum `"use client"`, nenhum import de `next/headers`. É isso
que o deixa rodar dos dois lados da fronteira — ele não depende de nenhum dos dois. É o oposto exato
do `servidor.ts`, cujo import de `next/headers` é justamente o que o prende ao servidor.

`reaisParaCentavos` **ficou onde estava**: ela converte o que uma pessoa digitou, é do formulário e
não tem consumidor de servidor. Mover tudo "já que estou aqui" é escopo que ninguém pediu.

#### O fuso é fixo, e sem isso a mesma publicação aparecia com duas datas

O bug mais sério que o code review da Epic 2 encontrou, e um que **não dava para ver aqui na minha
máquina**.

`Intl.DateTimeFormat` sem `timeZone` usa o fuso **do runtime**. As telas de `Meus eventos` são
Server Components, e o runtime delas é o container da Vercel, cujo `TZ` é **UTC** — enquanto a
confirmação da publicação renderiza no navegador, em `America/Sao_Paulo`. Um show às 21h de 14/08:

| Tela | Onde renderiza | Mostrava |
|---|---|---|
| Confirmação da publicação | Client Component | 14 de agosto, 21h00 |
| Lista de `Meus eventos` | Server Component | **15 AGO** |
| Detalhe do evento | Server Component | **15 de agosto, 00h00** |

O dado estava **certo** no banco: o `FormularioPublicacao` monta `new Date("2026-08-14T21:00")` no
fuso do navegador e envia `2026-08-15T00:00:00Z`, que é o instante correto. O erro era todo na
leitura. Em desenvolvimento os dois lados concordam, porque a máquina e o "servidor" são o mesmo
fuso — o defeito só nascia no deploy.

A saída é uma constante `FUSO = "America/Sao_Paulo"` em `formato.ts`, aplicada em todas as
formatações do módulo. **Ela contraria a letra do AD-11** ("a conversão para o fuso do usuário
acontece só na renderização"), e é uma contradição que a regra não previu: num Server Component não
existe "o usuário" no momento de formatar — não há navegador do outro lado. As duas alternativas
eram renderizar a data num componente `"use client"` só para isso (e conviver com divergência de
hidratação, ou com a data piscando) ou fixar. Fixei, porque o catálogo já é `countryCode=BR` e todo
show deste produto acontece no Brasil. O dia em que não acontecer, `FUSO` é o único lugar a mudar.

⚠️ **As três formatações da fila de `Meus eventos` eram inline na `page.tsx`** — dia, mês e ano, cada
um com tipografia própria — e foram justamente as que passaram despercebidas quando o `timeZone`
entrou no resto do módulo. Viraram `partesDaData(iso)`, exportada daqui. Uma cópia da regra é uma
chance de a próxima tela repetir o erro.

O que **não** estava errado, apesar de parecer: o corte `Em cartaz / Já aconteceram` logo abaixo. Ele
compara `getTime()` contra `getTime()`, que são instantes absolutos — fuso nenhum entra na conta.
Errado estava só o que a tela **escrevia**, nunca em que seção o evento caía.

### O corte "Em cartaz / Já aconteceram" mora na tela, não na API

A API responde uma pergunta só — "quais são os meus eventos" —, em ordem crescente de data. Quem
decide o que é passado e o que é futuro é o relógio de **quem está lendo**, e por isso o corte
acontece aqui, com uma comparação de `Date` contra `Date`:

```ts
const agora = instanteDaRequisicao();
const emCartaz = itens.filter((e) => new Date(e.data_hora).getTime() >= agora);
const jaAconteceram = itens.filter((e) => new Date(e.data_hora).getTime() < agora).reverse();
```

⚠️ **`Date` contra `Date`, nunca texto contra texto.** Comparar as strings ISO funciona por acidente
enquanto todos os offsets forem `Z`, e para de funcionar no primeiro `-03:00`.

⚠️ **E o relógio vem de um `cache()` do React, não de um `Date.now()` solto no corpo do componente.**
Ler o relógio no meio da renderização é uma chamada impura — o lint do React reprova, e com razão:
duas leituras podem devolver valores diferentes, e um evento que começa exatamente agora cairia numa
seção no primeiro filtro e na outra no segundo. Com `cache()` o valor nasce uma vez por requisição e
vale para a página inteira. É a mesma mecânica que o `obterUsuarioDaSessao` usa para consultar a
sessão uma vez só.

Seção sem nenhum evento **não é renderizada**: bloco vazio com título é pior que ausência.

### `src/lib/eventos.ts` tem três estados, e não dois

`listarMeusEventos()` segue o molde exato do `catalogo.ts` e do `portarias.ts` — só servidor,
`cache: "no-store"`, cookie repassado à mão, `try/catch` que **nunca levanta** — e devolve `ok` ou
`indisponivel`.

`obterMeuEvento(id)` devolve **três**: `ok`, `nao-encontrado` e `indisponivel`. O terceiro estado
existe porque a tela precisa distinguir "esse evento não é seu" de "a API não respondeu": o primeiro
é `notFound()`, o segundo é uma frase. Só o `404` separa os dois, e achatá-los faria a tela mentir —
um evento alheio apareceria como instabilidade do servidor.

```ts
if (resposta.status === 404 || resposta.status === 422) return { estado: "nao-encontrado" };
if (!resposta.ok) return { estado: "indisponivel" };
```

⚠️ A ordem importa: o `404` é conferido **antes** do `!resposta.ok` genérico.

⚠️ **`notFound()` levanta, como o `redirect()`.** Ele não pode ficar dentro de um `try/catch` — e não
fica: o `try` mora dentro do `lib/eventos.ts`, e o que sobra na página é um `if`.

### A fila, o inventário e o que não tem

A lista é uma **fila de jornal**: data à esquerda (dia e mês em mono versalete), nome em serifada,
`local · cidade` abaixo, e `vendidos/capacidade` à direita. A fila **inteira** é o `<Link>`, não só o
nome — padrão `fila-listagem`, o mesmo do catálogo do passo 1.

**Números exatos, sem medidor e sem proporção.** É o inventário de quem é dono da informação
(UX-DR7); medidor é da tela de quem compra, na Epic 3. E o par de números não fica sem nome: o rótulo
`vendidos` é visível ao lado, porque `12/860` sozinho é ambíguo para quem chega de leitor de tela.

O detalhe abre os setores um a um, com `vendidos/capacidade` e preço, e traz o bloco `Na porta` com
nome e e-mail de quem foi escalado. **Evento sem ninguém escalado mostra uma frase e não quebra** —
existem eventos assim no banco, publicados na janela em que a 2.4 já publicava e a 2.5 ainda não
exigia a escala.

**Não há botão de editar, cancelar ou trocar a escala**, e é decisão, não esquecimento: "gerenciar"
aqui é acompanhar. Botão que não faz nada é pior que botão ausente. O porquê completo, com as
alternativas descartadas, está no [README da raiz](../README.md#decisões-por-que-isso-e-não-aquilo).

**Um `page.module.css` para as duas telas**, em `eventos/`, importado pelo detalhe como
`../page.module.css`. Elas compartilham o vocabulário de fila e de inventário, e dois arquivos quase
iguais divergiriam na primeira mudança. Precedente: o `FormularioPublicacao` já importa o módulo da
página que o hospeda.

### O masthead ganhou `Meus eventos`

A navegação do organizador passou a ser `Início · Meus eventos · Publicar evento · Minha conta`.
`Meus eventos` vem **antes** de `Publicar evento` porque acompanhar o que está no ar é o que se faz
todo dia; publicar é eventual. Ele só aparece para `ORGANIZADOR` — cliente, portaria e visitante não
o veem —, e só entrou agora porque link que cai em 404 não fica no repositório (precedente da Story
1.4). Sobrou `Meus ingressos`, que espera a Story 4.1.

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

## A raiz: a programação

A raiz deixou de ser o estado vazio provisório da Story 1.2 e passou a ser a programação — e é a
primeira tela deste projeto que **não tem dono**. Todas as outras ou são de quem entra (login,
cadastro) ou de quem publica (`/organizador/*`), e todas começam por `obterUsuarioDaSessao()`. Esta
não tem guarda, não tem `redirect` e não lê sessão nenhuma: qualquer um dos três aqui seria uma
exigência que o backend não faz. Continua Server Component, sem uma linha de `"use client"`, porque
não há interação — só leitura e navegação. O corte de "só o que ainda vai acontecer" vem pronto da
API, ao contrário de "Meus eventos", onde ele mora na tela; o motivo dessa inversão está no README da
raiz.

**`src/lib/programacao.ts` é o primeiro módulo daqui que fala com a API sem repassar cookie**, e a
ausência do `cabecalhoDeSessao()` está comentada no código de propósito. Ele está a um import de
distância e não faria mal nenhum — é exatamente por isso que entraria sem ninguém notar, e o próximo
leitor tomaria a sessão por exigência da rota. São dois estados, e não três como no `eventos.ts`:
não há `404` nem `401` possíveis numa rota que responde `200 []` para banco vazio e não conhece
sessão. Como todos os outros, ele **nunca levanta** — só que aqui a página é a raiz do produto, e o
custo de esquecer isso seria a aplicação inteira caindo porque o backend piscou.

⚠️ **E é justamente por não ler cookie que ele precisou de `unstable_rethrow`.** O `cache: "no-store"`
é uma das APIs que o Next interrompe *lançando* um erro interno (`DYNAMIC_SERVER_USAGE`) para tirar a
rota da renderização estática, e o meu `try/catch` engolia esse sinal: o build registrava
"Programação indisponível" mesmo com a API no ar, e a raiz corria o risco de nascer estática com a
frase de erro impressa dentro. Os outros três módulos de `lib/` nunca tiveram esse problema porque
chamam `cookies()` **fora** do `try`, e já saem do modo estático antes de chegar ao `fetch`. Aqui não
há cookie, e o `fetch` é o único sinal que resta — daí a chamada ser a primeira linha do `catch`.

`partesDaFilaPublica` entrou no `formato.ts` em vez de nascer dentro do `page.tsx`, e não é a
`partesDaData` com outro nome. As duas filas do produto são primas, não gêmeas: a do organizador
mostra `15 ago 2026` inteiro em mono, porque ele precisa saber o ano de um show de 2001; a pública só
lista o que ainda vai acontecer, então o que decide é o dia da semana e a hora. A tipografia segue
essa divisão — dia da semana e hora em mono versalete, o dia em serifada de 30px, que é a assinatura
visual da listagem e a primeira coisa desta story a sair do protótipo. O `FUSO` continua num lugar
só: foram as três formatações inline da fila de "Meus eventos" que ficaram sem `timeZone` e fizeram a
mesma publicação aparecer com duas datas.

**A fila esgotada é um `<div>`, e a com ingresso é um `<Link>`** — a troca é do elemento, não do CSS.
Um `<Link>` com `pointer-events: none` continua no Tab e continua sendo anunciado como link por
leitor de tela, e o padrão pede que a fila esgotada **não** seja clicável: a ausência de resposta ao
hover é a informação. A palavra "Esgotado" está escrita no selo, então a informação não depende de
enxergar o vermelho da brasa. ⚠️ O `href` aponta para `/eventos/{id}`, **que só nasce na Story 3.4** —
até lá o clique cai na 404 do projeto. É janela consciente, do mesmo tipo da que o AD-7 teve entre a
2.4 e a 2.5: ela vive dentro da branch da epic, que só eu publico, e a 3.4 é quem a fecha. Ela
contraria o precedente escrito no `Masthead.tsx` ("link que cai no 404 não fica no repositório"), e a
diferença que aceitei é de alcance — lá é navegação permanente, visível em toda tela; aqui é um
`href` que fecha na mesma epic.

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

A lista da Story 2.2, `/organizador/publicar`:

- **`organizador@rockhub.dev`** → `Publicar evento` aparece no masthead, e a tela abre
- **`cliente@rockhub.dev`** → o link **não** aparece; digitar `/organizador/publicar` na barra
  manda para a raiz
- **Sem sessão**, abrir `/organizador/publicar` → cai no login, e entrar leva de volta para a tela
- **Abrir a tela sem digitar nada** → já vêm exemplos reais do catálogo, ordenados por data, sem
  precisar buscar primeiro — e **só show de música**, nenhuma feira de negócios ou evento
  corporativo (é o filtro de classificação; ver a
  [techspec](../docs/techspec-filtro-do-catalogo.md))
- **Buscar `rosalia`** → acha. É a contraprova do filtro híbrido: se voltar vazio, o `genreId`
  vazou do `else` e passou a valer também na busca por termo
- **Buscar `baco`** → filas com fio, sem card, origem em versalete monoespaçada
  (`Ticketmaster · <local> · <cidade>`)
- **Derrubar a Ticketmaster de propósito** (`TICKETMASTER_API_KEY` errada no `.env` do backend) →
  a tela mostra o aviso de indisponível e **não quebra**, com ou sem termo digitado

A lista da Story 2.4, o passo 2 da mesma tela:

- **Clicar numa fila** → a URL ganha `escolhido=…#passo-2`, a fila fica com o fio âmbar e a etiqueta
  `Selecionado`, e a página **leva você até** o passo **2 · Data, local e setores**. Se ele aparecer
  mas a página não se mexer, a âncora quebrou — é o defeito que motivou o `#passo-2`
- **Recarregar** → a escolha continua. **Botão voltar** → a escolha some, e a tela volta ao passo 1
- **Buscar outro termo com a escolha na URL** → o passo 2 some, sem erro e sem aviso. É o `find`
  devolvendo `undefined`, e é o comportamento certo
- **Publicar com um setor** → o formulário dá lugar à confirmação, com nome, data por extenso,
  capacidade e preço exatos. **Sem redirect**
- **Publicar com dois setores de mesmo nome** (`Pista` e ` pista `) → a tela diz o que aconteceu e
  **não** quebra: é o `SETOR_DUPLICADO`. Se aparecer "erro interno", a verificação do service caiu
- **Preço `abc`** → recusa **antes** de ir à rede. Se aparecer chamada no Network, a validação local
  vazou
- **`+ Adicionar setor` e o `×`** → o `×` só aparece a partir da segunda linha
- **Abaixo de 900px** → um campo por linha, os rótulos dos setores ficam **visíveis**, e nada rola na
  horizontal

A lista da Story 2.5, o passo 3:

- **Escolher uma atração** → o passo **3 · Escale a portaria** aparece com as **duas** contas
  semeadas, `Ana Sampaio` e `Jonas Ribeiro`, e a contagem lendo `0 escalados`
- **Digitar `ana` na busca** → só uma linha; apagar → as duas voltam. Sem nenhuma chamada no
  Network: o filtro é em memória
- **Marcar Ana, filtrar por `jonas`, marcar Jonas, limpar o filtro** → **as duas** continuam
  marcadas. É a verificação de que filtrar não desmarca ninguém, e é a que mais importa aqui
- **Apertar Enter no campo de busca** → não acontece nada. Se o evento for publicado, o
  `preventDefault` sumiu
- **Publicar sem marcar ninguém** → recusa **sem** ida à rede. Se aparecer chamada no Network, a
  validação local vazou
- **Publicar com duas pessoas marcadas** → a confirmação lista os dois nomes sob `Na porta`, e o
  Postgres tem duas linhas (`select * from evento_portaria;`)
- **Abaixo de 900px** → busca e lista ocupam a largura inteira, o e-mail desce para baixo do nome, e
  nada rola na horizontal
- **`Tab`** → cada marcação recebe foco visível em âmbar, e o rótulo é lido junto

A lista da Story 2.6, `/organizador/eventos`:

- **`organizador@rockhub.dev`** → o masthead mostra `Início · Meus eventos · Publicar evento ·
  Minha conta`, nessa ordem
- **Abrir a lista** → os eventos publicados nas 2.4/2.5 aparecem com `vendidos/capacidade` à direita,
  e um evento com data passada cai em **Já aconteceram**, separado dos que estão **Em cartaz**
- **Clicar numa fila em qualquer ponto dela**, não só no nome → o detalhe abre. Se só o nome
  responder, a fila deixou de ser o `<Link>`
- **Detalhe de um evento publicado antes da 2.5** → `Na porta` mostra a frase de "ninguém escalado" e
  a tela **não** quebra
- **Publicar um evento novo** → a confirmação mostra `Ver meus eventos →` ao lado de `Publicar
  outro →`, **sem redirect**, e o evento aparece na lista
- **`cliente@rockhub.dev`** → `Meus eventos` não aparece no masthead, e digitar `/organizador/eventos`
  na barra manda para a raiz
- **`/organizador/eventos/<uuid-que-não-existe>`** → a 404 do projeto, com a casca. O mesmo vale para
  o id de um evento de outro organizador: a resposta é idêntica, de propósito
- **Abaixo de 900px** → um bloco por linha, a data da fila vira uma linha só acima do nome, e nada
  rola na horizontal

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

O que o `curl` cobre — raiz, 404 com a casca, `401` sem cookie, login nas contas semeadas e os
atributos do `Set-Cookie` — está em [Como saber que deu certo](#4--como-saber-que-deu-certo).
