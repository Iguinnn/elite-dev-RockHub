# RockHub — frontend

Next.js 16 com App Router, TypeScript e React 19. É a interface da plataforma: a programação de
shows, a compra, o ingresso com QR e a tela de validação da portaria. A API vive em
[`../backend`](../backend/README.md) e este projeto só a consome.

Hoje está de pé a casca — o sistema visual "jornal noturno" aplicado, o masthead, a raiz em estado
vazio e um 404 com a cara do projeto — mais as **duas telas de acesso**, login e cadastro, que são as
primeiras a conversar de verdade com a API.

O histórico de decisões do projeto inteiro está no [README da raiz](../README.md). Aqui fica o que
é específico desta camada.

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

**Nenhuma variável `NEXT_PUBLIC_` carrega credencial.** Tudo que tem esse prefixo vai embutido no
bundle e fica visível para qualquer visitante — é endereço público, nada mais. A chave da
Ticketmaster e o segredo que assina os ingressos moram no backend e nunca atravessam para cá
(AD-2).

## O proxy `/api/*`

`next.config.ts` reescreve tudo que chega em `/api/:caminho*` para `${API_URL}/:caminho*`. O
navegador chama o domínio do próprio frontend; quem fala com o backend é o servidor do Next.

```
navegador ──► rockhub.vercel.app/api/auth/login
                     │  rewrite do next.config.ts (lado do servidor)
                     ▼
              rockhub.up.railway.app/auth/login

o Set-Cookie volta pelo domínio da Vercel → cookie de origem própria → SameSite=Lax funciona
```

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
um redeploy. O sintoma é o frontend novo apontando para a API antiga, e é o tipo de coisa que custa
uma tarde na Story 1.9.

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

**Só o caminho do navegador existe hoje.** Buscar dados a partir de um Server Component precisa de
URL absoluta e de repassar o cookie lido por `cookies()`; isso nasce na Story 1.6, com o
`GET /auth/eu`, que é o primeiro consumidor real.

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
      (entrada)/              # casca sem masthead: só a marca
        layout.tsx
        layout.module.css
        login/
          page.tsx            # Server Component: coluna de 440px
          page.module.css
        cadastro/
          page.tsx            # Server Component: a mesma coluna
          page.module.css
    components/
      Logotipo.tsx            # a marca, num lugar só
      Logotipo.module.css
      Masthead.tsx            # cabeçalho de jornal
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
    lib/
      api.ts                  # chamarApi + ErroDaApi — o único caminho até a API
```

### Duas cascas, e por quê

O layout raiz é só `<html><body>`. A casca visível vem de dois grupos de rotas:

| Grupo | O que mostra | O que mora nele |
|---|---|---|
| `(site)` | Masthead: logotipo, navegação, fio duplo | A raiz, e daqui em diante tudo que exige sessão ou é navegável |
| `(entrada)` | Só o logotipo, centrado | `/login` e `/cadastro` |

**Quem está tentando entrar não pode ver "Meus ingressos" e "Minha conta".** São dois links que ele
não consegue abrir, e que hoje caem no 404. A tela de acesso mostra a marca e o formulário, nada
mais.

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

Uma pendência continua aberta, e tem dono: **não há link para `/login` a partir do resto do site.**
O "Entrar" entra no masthead na **Story 1.6**, que é quem passa a saber se existe sessão — lá as duas
navegações nascem juntas ("Entrar" para visitante, "Minha conta / Sair" para quem entrou), sem estado
intermediário errado.

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

Nesta casca o único ponto que precisava de tratamento era a navegação do masthead — os três itens em
versalete com entreletra larga não cabem lado a lado em celular, então ela quebra linha
(`flex-wrap`). Encolher a entreletra não era opção: ela é parte da identidade. O resto já reflui
sozinho, porque não existe largura fixa em lugar nenhum — só `max-width`.

As telas de acesso não precisaram de media query nenhuma, e isso é consequência de três escolhas
anteriores: a coluna é `max-width: 440px` com `margin: 0 auto`, os campos são `width: 100%`, e o
reset global aplica `box-sizing: border-box` em tudo. Sem o `border-box`, o `padding: 14px` do campo
somaria à largura total e transbordaria a coluna em telas estreitas — é a causa mais comum de rolagem
horizontal em formulário, e ela está desarmada na origem.

## Convenções

- **Server Component por padrão.** `"use client"` só onde há interação que exige o navegador. Hoje
  são três ilhas: o `NavLink`, que precisa de `usePathname()` para marcar o item ativo, e os dois
  formulários — a exceção prevista no `ARCHITECTURE-SPINE.md#Convenções`. `Campo`, `Botao` e
  `AvisoDeErro` **não** levam a diretiva: sem interação própria, ela marcaria como ilha algo que não é
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

- **`params` e `searchParams` são `Promise`.** O acesso síncrono foi removido de vez (era só
  depreciado no 15). Não morde hoje, porque nenhuma rota é dinâmica ainda — vai morder na Story 3.4,
  em `/eventos/[id]`. Sempre `const { id } = await params`
- **`next lint` não existe mais.** O script `npm run lint` chama o ESLint direto
- **Turbopack é o bundler padrão**, em dev e no build. Não configure webpack, não adicione flag
- **O `create-next-app` gera coisa que viola o projeto.** Ele importa a fonte `Geist` de
  `next/font/google` e escreve um `globals.css` com variáveis próprias e bloco de
  `prefers-color-scheme`. Tudo isso foi arrancado — se você regerar o template algum dia, arranque
  de novo
- **`.gitignore` só existe na raiz.** O que o `create-next-app` cria aqui é redundante; a única
  regra que ele tinha a mais (`next-env.d.ts`) eu movi para o arquivo da raiz

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
exatamente o caso da Story 1.5, ao extrair `Campo` e `Botao` do login. Os 55 testes do backend não
olham para o markup. Por isso a conferência manual das telas de acesso tem uma lista fixa:

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
