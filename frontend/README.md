# RockHub — frontend

Next.js 16 com App Router, TypeScript e React 19. É a interface da plataforma: a programação de
shows, a compra, o ingresso com QR e a tela de validação da portaria. A API vive em
[`../backend`](../backend/README.md) e este projeto só a consome.

Hoje está de pé a **casca**: o sistema visual "jornal noturno" aplicado, o masthead, a raiz em
estado vazio e um 404 com a cara do projeto. Nenhuma chamada à API ainda — o cliente HTTP entra na
Story 1.4, junto com o login.

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

Abre em <http://localhost:3000>.

**A porta 3000 não é detalhe.** É a origem que o `CORS_ORIGENS` do backend já autoriza por padrão.
Se você subir em outra porta, o login da Story 1.4 vai falhar com um erro de CORS que custa a
achar.

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
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Endereço da API |

**Nenhuma variável `NEXT_PUBLIC_` carrega credencial.** Tudo que tem esse prefixo vai embutido no
bundle e fica visível para qualquer visitante — é endereço público, nada mais. A chave da
Ticketmaster e o segredo que assina os ingressos moram no backend e nunca atravessam para cá
(AD-2).

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
      layout.tsx              # <html lang="pt-BR">, masthead, <main>, metadata
      page.tsx                # raiz
      not-found.tsx           # 404 com a identidade
      globals.css             # tokens, reset, foco, utilitários
      *.module.css            # estilo das páginas
    components/
      Masthead.tsx            # cabeçalho de jornal
      Masthead.module.css
      NavLink.tsx             # "use client" — marca o item ativo
    lib/                      # vazia por enquanto: o cliente da API entra na Story 1.4
```

`src/lib/` nasce vazia de propósito, pelo mesmo motivo que `app/services/` e `app/models/`
nasceram vazias no backend: deixar a estrutura materializada desde o primeiro commit, para que as
stories seguintes não improvisem onde as coisas moram.

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

## Convenções

- **Server Component por padrão.** `"use client"` só onde há interação que exige o navegador. Hoje a
  única ilha de cliente é o `NavLink`, que precisa de `usePathname()` para marcar o item ativo
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
