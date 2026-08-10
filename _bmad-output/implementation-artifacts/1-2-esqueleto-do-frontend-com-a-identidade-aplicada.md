---
baseline_commit: 25598ff
---

# Story 1.2: Esqueleto do frontend com a identidade aplicada

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **Primeira story do frontend: a pasta `frontend/` está
vazia (só um `README.md` de 0 byte).**

## Story

Como visitante,
quero abrir a aplicação e ver a identidade "jornal noturno",
para que toda tela construída depois já nasça no sistema visual certo.

## Acceptance Criteria

1. **Given** um projeto Next.js 16 com App Router
   **When** eu abro a raiz
   **Then** vejo o masthead com o logotipo em serifada sobre fio duplo
   **And** o fundo é `#0E0D0C` e o texto `#EDE8DC`

2. **Given** os tokens de `DESIGN.md`
   **When** eu inspeciono o CSS
   **Then** as **nove** cores existem como variáveis CSS
   **And** nenhum elemento tem `border-radius` ou `box-shadow`
   **And** nenhuma fonte externa é carregada

3. **Given** o masthead
   **When** eu o inspeciono
   **Then** ele contém apenas logotipo e navegação
   **And** não há linha de contexto decorativa (data, contador, subtítulo) — UX-DR10

4. **Given** qualquer elemento focável
   **When** eu navego por teclado
   **Then** o foco é visível em âmbar e em nenhum lugar existe `outline: none` — UX-DR9
   **And** com `prefers-reduced-motion` ativo, nenhuma transição roda

> AC4 não está no `epics.md`. Foi acrescentado porque foco e movimento são regra **global** de CSS: o
> lugar onde eles nascem é este arquivo de tokens, e a Story 1.5 (`UX-DR9` no formulário de cadastro)
> vai depender de já existirem. Escrever depois significa voltar no CSS base com telas em cima.

## Tasks / Subtasks

- [x] **T1. Criar o projeto Next.js em `frontend/`** (AC: 1)
  - [x] Rodar a partir da **raiz do repositório**:
        `npx create-next-app@16.3.0 frontend --ts --app --src-dir --no-tailwind --eslint --import-alias "@/*" --turbopack`
  - [x] Se ele perguntar sobre **React Compiler**, responda **não** — custo de build sem contrapartida aqui
  - [x] Gerenciador é o **npm** (`package-lock.json` versionado) — é o que a Vercel usa por padrão na
        Story 1.9. Não troque por pnpm ou yarn
  - [x] Conferir no `package.json`: `next` 16.3.x, `react` 19.x, `typescript` ≥ 5.1
  - [x] **Não crie `frontend/.gitignore` próprio** além do que o `create-next-app` gera. O
        `.gitignore` da raiz já cobre `node_modules/` (l. 226), `.next/` (245), `out/` (247) e as
        variantes de `.env` com exceção do `.env.example` (237-238)

- [x] **T2. Tokens, reset e base tipográfica em `src/app/globals.css`** (AC: 1, 2, 4)
  - [x] Apagar **todo** o conteúdo que o `create-next-app` gerou nesse arquivo — inclusive as
        variáveis `--font-geist-*` e o bloco `@media (prefers-color-scheme: dark)`
  - [x] `:root` com as **nove** cores da tabela em *Identidade* mais `--serif` e `--mono`
  - [x] Reset: `*{box-sizing:border-box;margin:0;padding:0}`
  - [x] `html,body{background:var(--breu);color:var(--cal);font:16px/1.55 var(--serif)}`
  - [x] `a{color:inherit;text-decoration:none}`
  - [x] Foco global: `:focus-visible{outline:2px solid var(--ambar);outline-offset:2px}`.
        **`outline:none` é proibido no projeto inteiro**
  - [x] `@media (prefers-reduced-motion: reduce)` zerando `transition` e `animation`
  - [x] Utilitários `.kicker` e `.mono` (especificação em *Tipografia*)
  - [x] `.conteudo`: `max-width:1180px; margin:0 auto; padding:0 18px`

- [x] **T3. Arrancar a fonte externa que o template traz** (AC: 2)
  - [x] `src/app/layout.tsx` do `create-next-app` importa `Geist` de `next/font/google` — **remova o
        import, as chamadas e as classes que ele injeta no `<body>`**
  - [x] Conferir que não sobrou nenhum `next/font`, `@font-face`, `<link rel="preconnect">` para
        Google Fonts nem `@import url(...)` no CSS
  - [x] As duas famílias são de sistema: `Georgia,'Times New Roman',serif` e
        `ui-monospace,'SF Mono',Menlo,Consolas,monospace` — UX-DR2

- [x] **T4. Layout raiz** (AC: 1, 3)
  - [x] `src/app/layout.tsx`: `<html lang="pt-BR">`, `metadata` com `title: "RockHub"` e uma
        `description` em voz jornalística
  - [x] Renderiza `<Masthead />` e `<main>` dentro do wrapper `.conteudo`
  - [x] **Server Component** — sem `"use client"`

- [x] **T5. Componente `Masthead`** (AC: 1, 3)
  - [x] `src/components/Masthead.tsx` + `src/components/Masthead.module.css`
  - [x] Logotipo `Rock<em>Hub</em>`: serifada 44px/.86, `letter-spacing:-.035em`, com `Hub` em
        itálico `var(--ambar)`
  - [x] Bloco do logotipo fechado por fio simples (`1px solid var(--fio)`, `padding-bottom:10px`)
  - [x] Navegação abaixo: `Início`, `Meus ingressos`, `Minha conta` — mono 600 11px, `.15em`,
        versalete, `var(--fumaca)`; item ativo em `var(--cal)` com `border-bottom:2px solid var(--ambar)`
  - [x] O `<header>` inteiro fecha com `border-bottom:3px double var(--fio)`
  - [x] Links por `<Link>` do `next/link`, apontando para `/`, `/ingressos` e `/conta`
  - [x] Item ativo vem de um `NavLink` client mínimo com `usePathname()`. É a **única** ilha de
        cliente desta story; o `Masthead` continua Server Component
  - [x] **Proibido:** qualquer linha de contexto — data, contador de eventos, subtítulo, "edição de
        sexta". Foi testada no protótipo e removida por soar gerada (UX-DR10, anti-padrão 5)
  - [x] **Fora desta story:** o bloco de identidade do usuário (`IGOR DUARTE · CLIENTE` no protótipo).
        Não há autenticação ainda, e o AC3 exige "apenas logotipo e navegação". Entra na Story 1.6

- [x] **T6. Página raiz** (AC: 1)
  - [x] `src/app/page.tsx` — Server Component
  - [x] Conteúdo no padrão de **estado vazio** do `EXPERIENCE.md`: kicker em versalete, uma frase, fim.
        Sem ilustração, sem botão grande
  - [x] Voz jornalística, sem exclamação. Algo como: kicker `Programação` + *"A programação entra no
        ar quando os primeiros eventos forem publicados."*
  - [x] **Proibido:** título display gigante com um texto pequeno embaixo. É o anti-padrão 3, e é
        exatamente o que um placeholder de home tende a virar

- [x] **T7. Página 404 com a identidade** (AC: 1)
  - [x] `src/app/not-found.tsx` no mesmo padrão do T6
  - [x] `/ingressos` e `/conta` ainda não existem e caem aqui até as Stories 4.1 e 1.5 — é uma tela
        honesta com a cara do projeto, não a página de erro crua do Next
  - [x] A Story 4.4 (link compartilhado revogado responde `404`) vai reaproveitar esta tela

- [x] **T8. Configuração por ambiente** (AC: —)
  - [x] `frontend/.env.example` com `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - [x] O arquivo que o Next lê é o **`.env.local`** (não `.env`, que aqui é só o exemplo). Documente
        `cp .env.example .env.local` no `frontend/README.md` — o `.gitignore` da raiz já cobre
        `.env.local` (l. 232) e libera o `.env.example` (l. 238)
  - [x] Nada além disso. **Nenhuma variável `NEXT_PUBLIC_` carrega credencial** — AD-2
  - [x] Não escreva cliente HTTP nesta story: o wrapper de `fetch` é da Story 1.4, que é quem faz a
        primeira chamada real

- [x] **T9. Verificação** (AC: 2, 3, 4)
  - [x] `npm run build` passa e `npx tsc --noEmit` não acusa nada
  - [x] `npm run lint` limpo
  - [x] Busca no `src/` por `border-radius`, `box-shadow`, `outline: none`, `#000`, `#fff` e
        `next/font` — todas sem ocorrência
  - [x] Conferir no navegador: fundo `#0E0D0C`, texto `#EDE8DC`, fio duplo fechando o masthead,
        `Tab` desenhando contorno âmbar
  - [x] Conferir com o backend no ar que **nada** foi chamado — esta story não fala com a API

- [x] **T10. Documentação** (obrigatório — regra do projeto)
  - [x] Criar `frontend/README.md`: pré-requisitos (Node ≥ 20.9), como rodar, variáveis de ambiente,
        estrutura de pastas, as convenções de CSS e de Server Component, e o sistema de tokens
  - [x] `README.md` da raiz: "Como executar" ganha o frontend; "Stack e estrutura" sai de *(Story 1.2)*;
        "Decisões" ganha as entradas de TypeScript, CSS Modules, fonte de sistema e ausência de
        biblioteca de componentes — **cada uma com o que caiu e por quê**
  - [x] `README.md` da raiz, seção "O que não está pronto": acrescentar que o frontend não tem teste
        automatizado, com o motivo (NFR1 exige declarar o que ficou de fora)
  - [x] O `README.md` que o `create-next-app` gera em `frontend/` é descartável — substitua-o inteiro
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "descartei")

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita — não são sugestão:

| Assunto | Escolha | Consequência |
|---|---|---|
| Linguagem | **TypeScript** | `.tsx`/`.ts` em tudo; o contrato da API vira tipo compartilhado a partir da Epic 2 |
| CSS | **`globals.css` + CSS Modules por componente** | Token e reset num lugar só; estilo de componente com escopo isolado. Sem folha global gigante |
| Escopo | **Casca + `.env.example`** | Entra `NEXT_PUBLIC_API_URL`; **não** entra cliente HTTP |
| Teste de frontend | **Nenhum** | Sem Vitest, sem Testing Library, sem Playwright. Ver *Testing* |
| Rotas | **`/ingressos` e `/conta`** | Substantivo curto, igual ao backend (`/saude`, `/eventos`, `/reservas`) e ao `/i/TOKEN` da Story 4.3 |

### Stack fixada — versões conferidas em 10/08/2026

| Pacote | Versão | Papel |
|---|---|---|
| Node | ≥ 20.9 (a máquina tem **v24.14.0**) | Next 16 derrubou o suporte a Node 18 |
| npm | 11.9.0 | Gerenciador; `package-lock.json` versionado |
| `next` | 16.3.0 | App Router. Turbopack é o bundler padrão de dev |
| `react` / `react-dom` | 19.x | — |
| `typescript` | ≥ 5.1 | Mínimo exigido pelo Next 16 |

**Não instale ainda:** `qrcode.react` (Story 4.2), `@yudiel/react-qr-scanner` (Story 5.5), nenhuma
biblioteca de componentes, nenhuma de estado, nenhuma de formulário. Dependência antes da hora polui
o lockfile e infla o build da Vercel.

[Fonte: ARCHITECTURE-SPINE.md#Stack]

### Identidade — os nove tokens

`DESIGN.md` define nove cores; o protótipo publica só oito no `:root` (falta `fio2`). O AC2 pede as
**nove** — inclua `fio2`.

| Token | Hex | Uso |
|---|---|---|
| `--breu` | `#0E0D0C` | Fundo de toda a aplicação |
| `--breu2` | `#151311` | Superfície elevada: resumo, campo, fila em hover |
| `--cal` | `#EDE8DC` | Texto principal |
| `--fumaca` | `#8F877A` | Texto secundário, etiquetas, kickers |
| `--ambar` | `#F2A413` | **Acento único.** Ação primária, item ativo, escassez |
| `--brasa` | `#D93B2B` | Erro, esgotado, pagamento recusado, ingresso inválido |
| `--verde` | `#3FA96B` | Só o veredito `VALIDO` e a confirmação de pagamento |
| `--fio` | `#2A2622` | Todos os fios, filetes e bordas |
| `--fio2` | `#3A352F` | Fio sobre superfície elevada; medidor esgotado |

**Preto quente de tinta, nunca `#000`. Branco quente de jornal, nunca `#FFF`.**

**Regra do âmbar:** é o único acento de marca. Se algo precisa de destaque e não é erro nem sucesso,
é âmbar. Não introduza um segundo acento decorativo — nem "só para esta tela".

O protótipo usa algumas cores fora da paleta (`#BEB6A8` no standfirst, `#5F5A52` no esgotado,
`#6E675C` no `JA_UTILIZADO`, `#221F1C` no fundo do medidor, `#5B554D` no placeholder). **Nenhuma
delas é usada nesta story.** Quando a story que precisar delas chegar, ela decide se vira token ou
fica local — não invente agora.

[Fonte: DESIGN.md#Colors, UX-DR1]

### Tipografia — UX-DR2

Duas famílias, **ambas de sistema**. Nenhuma fonte externa, por decisão de performance e de não
depender de rede.

```css
--serif: Georgia,'Times New Roman',serif;
--mono: ui-monospace,'SF Mono',Menlo,Consolas,monospace;
```

**Serifada** — nome de artista, título, manchete, valor monetário, corpo de texto. É a voz do jornal.
**Monoespaçada** — tudo que é máquina ou etiqueta: código, kicker, rótulo de campo, hora, estado.
Sempre em versalete com `letter-spacing` largo (`.15em` a `.22em`).

A tensão entre as duas é a identidade. Serifada sozinha vira convite de casamento; monoespaçada
sozinha vira terminal. **Nunca serifada em etiqueta, nunca monoespaçada em nome próprio.**

O que esta story usa:

| Papel | Especificação |
|---|---|
| Logotipo | `400 44px/.86 var(--serif)`, `letter-spacing:-.035em`; `Hub` em itálico âmbar |
| Link de navegação | `600 11px/1 var(--mono)`, `.15em`, versalete, `var(--fumaca)` |
| Kicker (`.kicker`) | `600 10px/1 var(--mono)`, `.22em`, versalete, `var(--fumaca)` |
| Corpo | `16px/1.55 var(--serif)` |

### Anatomia do masthead

Extraída do protótipo (`proto-jornal-noturno.html`, l. 45-55 e 262-274). Medidas são ponto de
partida ajustável; a **estrutura** não é.

```
┌────────────────────────────────────────────┐
│  RockHub                                   │  ← serifada 44px, "Hub" itálico âmbar
├────────────────────────────────────────────┤  ← fio simples 1px
│  INÍCIO   MEUS INGRESSOS   MINHA CONTA     │  ← mono versalete, ativo com fio âmbar embaixo
╞════════════════════════════════════════════╡  ← fio duplo 3px, fecha o bloco
```

```css
.masthead { border-bottom: 3px double var(--fio); padding-top: 26px; }
.mastTop  { display:flex; justify-content:space-between; align-items:flex-end;
            padding-bottom:10px; border-bottom:1px solid var(--fio); }
.navbar   { display:flex; justify-content:space-between; align-items:center; padding:9px 0; }
```

**Fios são estruturais, não decorativos.** Fio simples separa itens iguais; fio duplo fecha o
masthead e separa blocos de natureza diferente. Não existe fio "para preencher espaço".

[Fonte: DESIGN.md#Components/masthead, DESIGN.md#Layout & Spacing]

### Os cinco anti-padrões — cada um é critério de aceite

Uma tela que reintroduza qualquer um deles **está errada, mesmo que fique bonita**. Foram nomeados
pelo Igor no brainstorming como marcadores de "AI slop", que é o que o desafio penaliza por escrito.

1. Faixa ou linha que varre a tela em movimento contínuo (marquee, ticker); hover que desliza de uma
   lateral à outra
2. Grade de 6 a 8 cards nomeando seções do site
3. **Par de título display gigante com um texto pequeno logo abaixo, como bloco de abertura** —
   o risco direto do T6
4. Fileira horizontal de cards com paleta empresarial (o formato de Sympla, Eventim, Ingresso.com)
5. **Linha de contexto decorativa no cabeçalho** ("Edição de sexta · 14 de agosto · 14 apresentações
   em cartaz") — o risco direto do T5. Foi testada no protótipo e removida: soa gerada

Reforçando o que já está nos tokens: **sem card, sem sombra, sem canto arredondado, em nada.**
Raio zero é regra do sistema inteiro, sem exceção permitida. Papel não tem canto arredondado.

Animação permitida: só mudança de cor em hover, até 120ms. Nada atravessa a tela lateralmente.

[Fonte: brainstorm-intent.md#Anti-padrões, DESIGN.md#Brand & Style, UX-DR10, NFR7]

### Convenções do frontend que nascem aqui

Valem para as 30 stories seguintes:

- **Server Component por padrão.** `"use client"` só onde há interação que exige o navegador: câmera
  da portaria, stepper de quantidade, formulário. Nesta story a única exceção é o `NavLink`, por
  causa do `usePathname()`
- **CSS Modules por componente** (`Componente.module.css`), com os tokens vindo do `globals.css`.
  Não repita valor hex dentro de módulo — sempre `var(--token)`
- **Componentes React em `PascalCase`**; o domínio continua em português (`evento`, `setor`,
  `reserva`, `ingresso`), igual ao backend
- **`lang="pt-BR"`** e todo texto de interface em português
- **Sem biblioteca de componentes.** Nada de shadcn, MUI, Chakra ou equivalente. A razão é a mesma
  que sustenta a direção visual: sistema pronto traz junto o vocabulário visual que este projeto
  está tentando não ter
- **Voz jornalística:** específica, curta, sem entusiasmo comercial, **nunca exclamação**. Nada de
  "incrível", "imperdível", "garanta já"

[Fonte: ARCHITECTURE-SPINE.md#Convenções de Consistência, EXPERIENCE.md#Foundation, EXPERIENCE.md#Voice and Tone]

### Armadilhas específicas desta story

- **O template do `create-next-app` viola dois requisitos de saída da caixa.** Ele importa a fonte
  `Geist` de `next/font/google` (quebra UX-DR2 — fonte externa) e traz um `globals.css` com
  `prefers-color-scheme: dark` e variáveis próprias (conflita com os tokens). **T2 e T3 existem só
  para desfazer isso.** Não é opcional
- **`frontend/` não está vazia:** tem um `README.md` de 0 byte. O `create-next-app` tolera
  `README.md` numa pasta existente e vai sobrescrevê-lo com o dele — sem perda, porque o arquivo
  está vazio e o T10 reescreve tudo mesmo
- **`node_modules/` já está no `.gitignore` da raiz** (l. 226), assim como `.next/` (245) e `out/`
  (247). A pendência anotada no `CLAUDE.md` foi resolvida na Story 1.1 — **não peça ao Igor para
  adicionar de novo**
- **Um `.gitignore` só, na raiz.** Decisão explícita do Igor na Story 1.1, quando ele mandou remover
  o `backend/.gitignore`. Se o `create-next-app` gerar um `frontend/.gitignore`, ele é redundante:
  confira se acrescenta alguma regra que a raiz não tem; se não acrescentar, remova
- **Next 16: `params` e `searchParams` são `Promise`.** O acesso síncrono foi removido de vez (era
  depreciado no 15). Não morde nesta story — nenhuma rota é dinâmica ainda — mas morde na Story 3.4
  (`/eventos/[id]`). Anote no `frontend/README.md`
- **`next lint` saiu no Next 16.** O comando é o ESLint direto, pelo script que o `create-next-app`
  escreve no `package.json`
- **Turbopack é o padrão de dev no 16.** Não configure webpack, não adicione flag

### Estrutura alvo ao fim desta story

```text
frontend/
  package.json
  package-lock.json
  tsconfig.json
  next.config.ts
  eslint.config.mjs
  .env.example
  README.md
  public/
  src/
    app/
      layout.tsx        # <html lang="pt-BR">, Masthead, <main>, metadata
      page.tsx          # raiz: kicker + frase, no padrão de estado vazio
      not-found.tsx     # 404 com a identidade
      globals.css       # os nove tokens, reset, foco, utilitários, .conteudo
    components/
      Masthead.tsx
      Masthead.module.css
      NavLink.tsx       # "use client" — usePathname() para marcar o item ativo
    lib/                # vazia nesta story; o cliente da API entra na 1.4
```

`src/lib/` nasce vazia de propósito, mesmo motivo pelo qual `app/services/` e `app/models/`
nasceram vazias no backend: materializar a estrutura desde o primeiro commit para que as stories
seguintes não improvisem onde as coisas moram.

[Fonte: ARCHITECTURE-SPINE.md#Árvore]

### Comandos que esta story precisa deixar funcionando

Vão para o `frontend/README.md` e são os mesmos que a Story 1.9 vai usar no deploy da Vercel.

```bash
cd frontend

cp .env.example .env.local    # no Windows: copy .env.example .env.local
npm install

npm run dev      # desenvolvimento em http://localhost:3000
npm run build    # build de produção — é o que a Vercel roda
npm run lint
```

A porta 3000 não é detalhe: é a origem que o `CORS_ORIGENS` do backend já autoriza por padrão
(`backend/.env.example`). Se você mudar a porta, o login da Story 1.4 quebra e o motivo fica difícil
de achar.

### Escopo — o que NÃO fazer aqui

Listagem de eventos, chamada principal, busca, filtro, página de evento, setor, stepper, canhoto,
QR, tela de portaria, login, formulário, cliente HTTP, biblioteca de componentes, tema claro, Docker,
CI. Cada um tem a sua story.

Os componentes `fila-listagem`, `chamada-principal`, `setor`, `medidor`, `stepper`, `canhoto`,
`veredito` e `botao` estão especificados no `DESIGN.md`, e é tentador adiantá-los. **Não adiante:**
cada um nasce na story que o usa, com o dado real na mão. Componente escrito sem consumidor é
componente que a próxima story reescreve.

### Testing

**Não há teste automatizado no frontend, e isso é decisão tomada, não esquecimento.** O desafio não
exige teste, o prazo é de 7 dias, e o backend — onde moram as invariantes que valem ponto
(concorrência de estoque, assinatura do QR, validação idempotente) — já tem `pytest` desde a Story
1.1. Montar Vitest e Testing Library aqui custaria tempo de configuração para cobrir markup que
ainda vai mudar muito. **Não instale biblioteca de teste nesta story nem nas seguintes**; se isso
mudar, o Igor avisa.

Isso entra no `README.md` da raiz, seção *O que não está pronto* — o desafio pede explicitamente que
o que não foi feito seja declarado (NFR1).

A verificação desta story é:

- `npm run build` passa
- `npx tsc --noEmit` sem erro
- `npm run lint` limpo
- Busca no `src/` por `border-radius`, `box-shadow`, `outline: none`, `#000`, `#fff`, `next/font` —
  zero ocorrência (é a verificação literal do AC2)
- Conferência visual no navegador e navegação por `Tab` para o AC4

### Inteligência da story anterior (1.1)

O que a 1.1 estabeleceu e esta story herda:

- **O contrato de erro da API** é `{"erro": {"codigo": "...", "mensagem": "..."}}`, uniforme nas três
  origens (regra de negócio, framework, validação do Pydantic). **O frontend decide o texto pelo
  `codigo`, nunca pela `mensagem`** — a mensagem pode ser reescrita a qualquer momento. Não vale para
  esta story, que não chama a API, mas é o contrato que a 1.4 vai consumir
- **CORS já está configurado** e lê `CORS_ORIGENS` do ambiente, com `http://localhost:3000` como
  padrão. Foi antecipado na 1.1 exatamente para esta story e para o deploy
- **Padrão de `.env.example` versionado, `.env` fora.** Repita no frontend
- **O Igor removeu o `backend/.gitignore`** para manter um arquivo de ignore só, na raiz. Mesma
  regra aqui
- **Windows App Control bloqueia executáveis de virtualenv** naquela máquina. É problema do
  ecossistema Python; `npm` e `npx` não foram afetados. Se `npx create-next-app` falhar com
  bloqueio de política, avise em vez de tentar contornar sozinho
- **A 1.1 escreveu READMEs densos, em primeira pessoa, com "o que caiu e por quê" em cada decisão.**
  É o padrão a manter — o `README.md` da raiz é o histórico de decisões do projeto, não changelog

[Fonte: _bmad-output/implementation-artifacts/1-1-esqueleto-do-backend-que-responde.md]

### Estado do repositório

Último commit: `25598ff feat: Story 1.1 - esqueleto FastAPI que sobe e responde`, na branch
`epic-1---fundacao-acesso-e-primeiro-deploy`. Árvore limpa. O `backend/` está completo e testado;
o `frontend/` tem só o `README.md` vazio. Nenhum arquivo de frontend foi escrito ainda em nenhum
commit — não há convenção anterior de JS/TS neste repositório para seguir ou contrariar.

### Project Structure Notes

Esta story ocupa **apenas** `frontend/`, mais duas linhas no `README.md` da raiz. **Não toque em
`backend/`** — nem para "só ajustar o CORS": o padrão já contempla a porta 3000.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md] — tokens, tipografia, masthead, raio zero
- [Source: DESIGN.md#Como usar este documento] — o que é duradouro e o que é ajustável livremente
- [Source: EXPERIENCE.md#Foundation] — sem biblioteca de componentes, ergonomia por papel
- [Source: EXPERIENCE.md#Voice and Tone] · [Source: EXPERIENCE.md#State Patterns/Vazio] — padrão do T6 e do T7
- [Source: EXPERIENCE.md#Accessibility Floor] · [Source: EXPERIENCE.md#Interaction Primitives] — AC4
- [Source: mockups/proto-jornal-noturno.html#L24-L55, #L262-L274] — `:root` e markup do masthead
- [Source: brainstorm-intent.md#Anti-padrões] — os quatro originais; o quinto nasceu no UX
- [Source: ARCHITECTURE-SPINE.md#Convenções de Consistência] — Server Component por padrão, PascalCase
- [Source: ARCHITECTURE-SPINE.md#Árvore] · [Source: ARCHITECTURE-SPINE.md#Stack] · [Source: AD-2]
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`.
   O Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **`npm install` baixa muita coisa** — confirme com o Igor antes de rodar, se ele não estiver
   acompanhando. (O `.gitignore` já cobre `node_modules/`, então não há risco de versionar.)
3. **Atualize os READMEs antes de dar a story por concluída** — `frontend/README.md` e o da raiz, em
   primeira pessoa, com o que foi feito **e por quê**
4. **Decisão de produto é do Igor.** Se faltar definição — microcopy, nome de rota, ordem dos links —
   pergunte em vez de escolher
5. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code). A implementação começou em outra sessão, que **caiu no meio da T10**,
com o `frontend/README.md` pronto e o `README.md` da raiz atualizado só na abertura e nos
pré-requisitos. Esta sessão auditou o que estava em disco, rodou a verificação da T9 e terminou a
T10.

### Debug Log References

**Verificação da T9, executada nesta sessão:**

- `npx tsc --noEmit` → sem erro
- `npm run lint` → limpo
- `npm run build` → passa. Next.js 16.3.0 com Turbopack, compilação em 285ms, `/` e `/_not-found`
  ambas pré-renderizadas como estáticas (`○ Static`) — nenhuma virou dinâmica por engano
- Busca em `src/` por `border-radius`, `box-shadow`, `outline: none`, `#000`, `#fff`, `next/font`,
  `@font-face`, `@import url` e `fonts.googleapis` → **zero ocorrência** (verificação literal do AC2)
- A T9 pedia conferir que nada foi chamado na API: não há `fetch`, `axios` nem `NEXT_PUBLIC_API_URL`
  sendo lido em nenhum arquivo de `src/` — a variável existe só no `.env.example`, documentada

### Completion Notes List

**AC1 — casca com a identidade.** Next.js 16.3.0, App Router, TypeScript, `src/`. A raiz sobe com
fundo `#0E0D0C`, texto `#EDE8DC`, logotipo em Georgia 44px com `Hub` em itálico âmbar, e o masthead
fechado por fio duplo `3px double`.

**AC2 — nove tokens, nenhuma fonte externa.** As nove cores estão no `:root` do `globals.css`,
incluindo o `fio2` que faltava no `:root` do protótipo. Nenhum `border-radius`, nenhum `box-shadow`,
nenhuma fonte baixada — a `Geist` que o `create-next-app` injeta via `next/font/google` foi
arrancada do `layout.tsx`, junto com o `globals.css` do template e seu bloco de
`prefers-color-scheme`.

**AC3 — masthead sem linha de contexto.** Só logotipo e navegação. Não há data, contador de eventos
nem subtítulo, e o bloco de identidade do usuário (`IGOR DUARTE · CLIENTE` no protótipo) ficou de
fora porque não existe autenticação ainda — entra na Story 1.6.

**AC4 — foco e movimento.** `:focus-visible` global com contorno âmbar de 2px e `outline-offset`;
nenhum `outline: none` em lugar nenhum. `prefers-reduced-motion: reduce` zera `transition`,
`animation` e `scroll-behavior`. A única transição do sistema é a cor do link de navegação, em
120ms — o teto que o `EXPERIENCE.md` permite.

**Decisões tomadas dentro do escopo pela sessão de implementação:**

- **`.gitkeep` em `public/` e em `src/lib/`.** Git não versiona pasta vazia, e as duas precisavam
  existir no commit — `src/lib/` para materializar onde o cliente da API vai morar na Story 1.4. Os
  SVGs do template (`next.svg`, `vercel.svg` e companhia) foram apagados do `public/`: são a marca
  de outro produto
- **`.module.css` do 404 repetido em vez de abstraído**, com o motivo escrito no próprio arquivo:
  são sete linhas, e componente sem consumidor firme é componente que a próxima story reescreve.
  Vira componente quando aparecer o terceiro estado vazio, na Story 4.1
- **A borda inferior do link de navegação nasce transparente** e só troca de cor no item ativo,
  para a linha não mudar de altura quando a navegação troca de página
- **`aria-current="page"`** no item ativo: a marcação em âmbar é visual, e sozinha não chega a quem
  usa leitor de tela
- **`flex-wrap` na navegação do masthead**, com `gap: 8px 26px`. Os três itens em versalete com
  entreletra larga não cabem lado a lado abaixo de ~390px, e sem `wrap` eles transbordavam em vez de
  quebrar linha. Encolher a entreletra não era opção — ela é parte da identidade (UX-DR2). Era o
  único ponto desta tela que de fato quebrava: `.conteudo` é `max-width` e já encolhe sozinho

**`frontend/.gitignore` removido, mesma decisão da Story 1.1.** Um arquivo de ignore só, na raiz. A
única regra que o do `create-next-app` tinha a mais era `next-env.d.ts`, que foi para o `.gitignore`
da raiz (l. 248), junto com `*.tsbuildinfo` (251). `.next/` (245), `out/` (247) e `node_modules/`
(226) já estavam lá.

**`frontend/AGENTS.md` e `frontend/CLAUDE.md` apareceram sem estar na story.** Não são do agente: o
`next dev` do Next 16 os gera sozinho e os **recria a cada execução**, então apagá-los só produz
árvore suja de novo. O `CLAUDE.md` é uma linha (`@AGENTS.md`) e o `AGENTS.md` avisa que o Next 16 tem
mudanças que não estão no treino dos modelos. Decisão do Igor se entram no commit — o próprio arquivo
recomenda que sim.

**Continua fora, de propósito:** cliente HTTP (Story 1.4), qualquer componente do `DESIGN.md` que não
seja o masthead, e teste automatizado — este último é decisão registrada, não pendência.

### File List

**Criados:**

- `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`
- `frontend/next.config.ts`, `frontend/eslint.config.mjs`, `frontend/next-env.d.ts`
- `frontend/.env.example`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx` · `frontend/src/app/page.module.css`
- `frontend/src/app/not-found.tsx` · `frontend/src/app/not-found.module.css`
- `frontend/src/app/globals.css`
- `frontend/src/components/Masthead.tsx` · `frontend/src/components/Masthead.module.css`
- `frontend/src/components/NavLink.tsx`
- `frontend/src/lib/.gitkeep` · `frontend/public/.gitkeep`
- `frontend/AGENTS.md` · `frontend/CLAUDE.md` — gerados pelo `next dev`, não escritos à mão

**Modificados:**

- `frontend/README.md` — era um arquivo de 0 byte; agora é o README da camada
- `README.md` — "Estado atual", "Como executar" (pré-requisitos e a seção do frontend), "Roteiro de
  avaliação", "Stack e estrutura", quatro entradas novas em "Decisões" (identidade, CSS sem
  biblioteca, fontes de sistema, TypeScript) e uma linha em "O que não está pronto"
- `.gitignore` — `next-env.d.ts` e `*.tsbuildinfo`
- `_bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md` — a tabela `Stack` omitia
  Node, npm e TypeScript; "Adiado" ganhou a linha de teste de frontend
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story 1.2 → `review`
- `_bmad-output/implementation-artifacts/1-2-...md` — este arquivo

**Não versionados** (cobertos pelo `.gitignore` da raiz): `frontend/node_modules/`, `frontend/.next/`,
`frontend/next-env.d.ts`, `frontend/tsconfig.tsbuildinfo`.

### Pendência para o Igor decidir

**`frontend/src/app/favicon.ico` ainda é o do `create-next-app`** — o triângulo da Vercel. É a única
coisa do template que sobrou, e aparece na aba do navegador de quem for avaliar. Não troquei porque
desenhar a marca do RockHub é decisão sua. Duas saídas: um favicon próprio, ou apagar o arquivo e
deixar o navegador mostrar o ícone genérico, que já é melhor que exibir a marca de outro produto.

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.2 criada e contextualizada. Decisões do Igor incorporadas: TypeScript, `globals.css` + CSS Modules, escopo "casca + `.env.example`" |
| 2026-08-10 | Story 1.2 implementada: projeto Next.js 16 com App Router e TypeScript, os nove tokens da identidade, masthead com fio duplo, raiz e 404 em estado vazio, foco âmbar e `prefers-reduced-motion`. `frontend/README.md` criado |
| 2026-08-10 | Sessão de implementação interrompida no meio da T10. Auditoria e conclusão em nova sessão: verificação da T9 executada (build, `tsc`, lint e as buscas do AC2, todas limpas) e `README.md` da raiz terminado. Status → `review` |
| 2026-08-10 | Navegação do masthead ganhou `flex-wrap` — único ponto da tela que transbordava em celular. Em paralelo, o `epics.md` recebeu critérios de responsividade nas cinco stories de tela (2.4, 3.1, 3.3, 3.4, 4.2): o corte de 900px estava no `EXPERIENCE.md` e não tinha sido transportado para nenhum critério de aceite |
