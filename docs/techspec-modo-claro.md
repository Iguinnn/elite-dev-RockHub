# Techspec — modo claro

Um segundo tema para `(site)` e `(entrada)`, com o escuro continuando padrão. Fora da numeração
das stories: entra na branch de finalizações, como o filtro do catálogo entrou na Epic 2.

## 1. Escopo e commits

| # | Commit | O que entra |
|---|---|---|
| 1 | `feat: a paleta em dois modos` | Reestrutura o `globals.css` em tokens de valor + dois mapas; cria `--vazado`, `--neon2`, `--brasa2`, `--verde2`; migra os usos de acento-como-letra e de `var(--breu)`-sobre-tinta. **Nada muda na tela.** |
| 2 | `feat: a marca no modo claro` | Segundo PNG do lettering e a troca por CSS no `Logotipo`. |
| 3 | `feat: alternador de tema` | `SeletorDeTema`, o cookie, a leitura no layout raiz e a portaria travada no escuro. É o commit que torna o modo claro alcançável. |

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
avise que está pronto para eu commitar — sem escrever README, sem tocar no próximo. Só emende o
seguinte depois que eu mandar. Esta spec cobrir três commits **não** autoriza implementá-los de uma
vez.

**A ordem não é negociável.** O alternador é o último de propósito: enquanto a marca não tiver
versão clara, o modo claro é uma tela com o "Rock" branco invisível no fundo gelo. Só torno o modo
alcançável quando ele estiver inteiro.

## 2. O que existe hoje

O `globals.css` é o único lugar do frontend onde cor é declarada por valor: nove tokens nomeados por
material (`--breu`, `--breu2`, `--cal`, `--fumaca`, `--neon`, `--brasa`, `--verde`, `--fio`,
`--fio2`), consumidos por `var()` em 29 arquivos `.module.css`. Fora deles, três exceções:
`Confirmacao.module.css` (o véu do modal, `rgb(11 22 24 / 78%)`), `Canhoto.tsx` (as cores do QR) e o
PNG da marca em `Logotipo.tsx`.

O layout raiz não lê nada — é síncrono e só desenha `<html>`/`<body>`. As três cascas são
`(site)` (com `Masthead`), `(entrada)` (só a marca) e `/portaria` (`<div class="conteudo">` com
`CabecalhoDaPortaria`).

`:root` declara `color-scheme: dark` e `scrollbar-color`, e é isso que faz o navegador pintar em
escuro o que ele desenha por conta própria.

## 3. Decisões, com a alternativa descartada

**As duas tintas trocam de papel.** O fundo do modo claro é `#e4ebea` — o `--cal` de hoje — e o
texto é `#0b1618`, o `--breu` de hoje. Descartei inventar um branco gelo novo: o `#e4ebea` já é o
branco quente com tinte de petróleo que o sistema usa há três epics, já foi calibrado contra o
rosa e contra o vermelho, e nenhum branco que eu escolhesse agora seria mais "deste produto" do que
ele. O par dá 15,21:1 nos dois sentidos, porque é o mesmo par invertido — o modo claro herda o
contraste do escuro em vez de recomeçar do zero.

**Padrão escuro fixo, e o sistema não opina.** Não existe `prefers-color-scheme` em lugar nenhum:
quem chega vê o jornal noturno, e clara quem quiser. Descartei seguir a preferência do sistema —
metade de quem abrir o produto tem o Windows em claro e nunca veria a identidade que está sendo
avaliada.

**A escolha mora num cookie lido no servidor.** `localStorage` obriga a primeira pintura a sair
escura e virar clara no cliente, e esse pisca-pisca numa tela de avaliação lê como defeito. O custo
é tornar dinâmica toda rota da aplicação; o grupo `(site)` já era, por causa do masthead que lê
sessão.

**Os nomes de material passam a mentir no claro, e eu aceito.** Um `--breu` que vale branco gelo
contraria o próprio comentário do `globals.css`. A alternativa honesta era uma camada semântica
(`--fundo`, `--texto`, `--secundario`) — e ela reescreve 155 ocorrências em 29 arquivos para não
mudar um pixel. Comprei a mentira e escrevi o motivo no arquivo: os nomes descrevem o material do
**modo escuro**, que é o padrão e a identidade.

**O preenchimento não vira; o traço e a letra viram.** Esta é a correção do meu próprio passo 1, e
é a decisão central da spec. Eu havia recomendado escurecer o rosa inteiro no modo claro; isso mata
o botão, que é justamente a peça que já funcionava. `#ff4f9a` como **fundo** com letra escura dá
5,99:1 no claro exatamente como dá no escuro — o botão primário, o destrutivo, o selo de esgotado e
o item ativo do menu atravessam sem uma linha de mudança. O que quebra é o rosa como **letra**:
2,85:1 sobre o gelo, em 47 lugares. Então cada tinta ganha uma segunda versão — `--neon2`,
`--brasa2`, `--verde2` — usada em letra e traço, e idêntica à primeira no escuro. Regra do sistema,
daqui em diante: **tinta chapada é `--neon`; letra e filete são `--neon2`.**

**`--vazado`: a letra dentro do bloco de tinta não tem tema.** Doze declarações escrevem
`color: var(--breu)` em cima de um preenchimento; se o `--breu` virar gelo, elas viram branco sobre
rosa. O token novo é constante `#0b1618` nos dois modos, e é a única forma de o botão sobreviver à
troca sem um `if` por componente. O nome é o termo de impressão que o `DESIGN.md` já usa ("selo
`brasa` vazado"): a letra reservada dentro da tinta.

**A portaria fica travada no escuro.** Lá o escuro é função — o `globals.css` justifica o
verde-limão do veredito com "a portaria lê isso a três metros, no escuro, com pressa", e a distância
de luminância entre `VÁLIDO` (11,5:1) e `INVÁLIDO` (5,0:1) é o que separa os dois para quem tem
daltonismo vermelho-verde. Um fundo claro embaralha isso. Descartei deixá-la clarear junto por
coerência: coerência visual não vale um veredito lido errado na porta.

**O QR e o véu do modal ficam fora do tema.** O QR precisa de fundo claro para leitor óptico e já é
literal no `Canhoto.tsx`; o véu do `Confirmacao` é um escurecimento e continua escuro sobre página
clara, como em qualquer modal. Os dois seguem sendo as exceções declaradas à regra do "cor só no
`globals.css`".

## 4. Contrato

### A paleta

| Token | Escuro | Claro | Contraste sobre o fundo (escuro → claro) |
|---|---|---|---|
| `--breu` (fundo) | `#0b1618` | `#e4ebea` | — |
| `--breu2` (superfície elevada) | `#112124` | `#d8e1e0` | 1,109 → 1,102 |
| `--cal` (texto) | `#e4ebea` | `#0b1618` | 15,21 → 15,21 |
| `--fumaca` (secundário) | `#7e9295` | `#4a5d61` | 5,63 → 5,73 |
| `--neon` (preenchimento) | `#ff4f9a` | `#ff4f9a` | 5,99 → 2,85 ⚠️ nunca em letra no claro |
| `--neon2` (letra e traço) | `#ff4f9a` | `#aa0d52` | 5,99 → 6,01 |
| `--brasa` (preenchimento) | `#e4574a` | `#e4574a` | 5,04 → 2,97 ⚠️ idem |
| `--brasa2` (letra e traço) | `#e4574a` | `#b82e23` | 5,04 → 5,03 |
| `--verde` (preenchimento) | `#9be04a` | `#9be04a` | 11,52 → 1,53 ⚠️ idem |
| `--verde2` (letra e traço) | `#9be04a` | `#2a5a0b` | 11,52 → 6,77 |
| `--fio` | `#1e3134` | `#c3cfce` | 1,35 → 1,32 |
| `--fio2` | `#2b4247` | `#aabab9` | 1,73 → 1,66 |
| `--vazado` (letra sobre tinta) | `#0b1618` | `#0b1618` | 5,99 sobre `--neon`, nos dois modos |

Os pares foram escolhidos para **espelhar a razão de contraste do escuro**, não para parecer bonitos
isolados: é por isso que `--fumaca` cai para 5,73 (e não para 8) e que os fios ficam em 1,3–1,7.
O `--verde2` é a única exceção deliberada — 11,5:1 não tem correspondente claro que não seja
verde-quase-preto, e o veredito que precisava daquela distância mora na portaria, que não clareia.

### A estrutura do `globals.css`

```css
/* os valores, uma vez cada */
:root {
  --breu-escuro: #0b1618;  --breu-claro: #e4ebea;
  /* … os doze pares … */
  --vazado: #0b1618;       /* sem par: não tem tema */
}

/* o mapa do escuro — vale na raiz e em qualquer ilha que peça escuro */
:root,
[data-tema="escuro"] { --breu: var(--breu-escuro); /* … */ }

/* o mapa do claro — depois do de cima, para ganhar por ordem em <html data-tema="claro"> */
[data-tema="claro"] { --breu: var(--breu-claro); /* … */ }
```

`color-scheme` e `scrollbar-color` acompanham:

```css
:root { color-scheme: dark; scrollbar-color: var(--fio2-escuro) var(--breu-escuro); }
:root[data-tema="claro"] { color-scheme: light; scrollbar-color: var(--fio2-claro) var(--breu-claro); }
[data-tema="escuro"] { color-scheme: dark; }
/* a barra do documento acompanha a ilha escura da portaria */
:root[data-tema="claro"]:has([data-tema="escuro"]) {
  color-scheme: dark;
  scrollbar-color: var(--fio2-escuro) var(--breu-escuro);
}
```

### A migração dos usos (commit 1)

Duas varreduras, e nenhuma delas é "trocar tudo":

1. **`var(--neon)` / `var(--brasa)` / `var(--verde)` em `color`, `border-color`, `outline-color`,
   `text-decoration-color`, `caret-color` e em `drop-shadow`/`box-shadow` de filete** → viram
   `--neon2` / `--brasa2` / `--verde2`. Em `background`, `background-image` e `fill` **não mudam**.
   São 47 ocorrências de `color:` em 16 arquivos, mais as bordas.
2. **`var(--breu)` que pinta letra ou filete em cima de tinta** → vira `var(--vazado)`. São dez
   sítios: `Botao.module.css:29` e `:100`, `Masthead.module.css:120` e `:136`,
   `Canhoto.module.css:71`, `SeletorDeData.module.css:116` e `:177`, `(site)/page.module.css:224` e
   `:649`, `eventos/[id]/page.module.css:361` e `:444`, `organizador/eventos/page.module.css:244`.
   O `var(--breu)` que pinta **chão** (`globals.css:136`, o degradê de `page.module.css:292`, o
   rodapé de `eventos/[id]/page.module.css:408`, `SeletorDeData.module.css:170`) **fica como está** —
   é ele que precisa virar gelo.

### O cookie e o alternador (commit 3)

- Cookie `tema`, valores `claro` | `escuro`, `path=/`, `Max-Age` de um ano, `SameSite=Lax`, **sem**
  `httpOnly` — quem escreve é o cliente.
- `app/layout.tsx` vira `async`, faz `const tema = (await cookies()).get("tema")?.value` e renderiza
  `<html lang="pt-BR" data-scroll-behavior="smooth" data-tema={tema === "claro" ? "claro" : "escuro"}>`.
  Qualquer valor que não seja `claro` cai no escuro.
- `components/SeletorDeTema.tsx`, client component: um `<button>` que escreve
  `document.documentElement.dataset.tema` e o cookie na mesma função. **Sem server action e sem
  `router.refresh()`** — a troca é instantânea e o cookie serve só para o próximo SSR.
- Rótulo em monoespaçada versalete, no padrão dos itens do menu, dizendo o modo que o clique liga
  (`MODO CLARO` / `MODO ESCURO`), com `aria-label` completo.
- Entra em duas cascas: ao fim do `<nav>` do `Masthead` e ao lado da marca no `<header>` do
  `(entrada)/layout.tsx`. Sem ele em `(entrada)` quem cai direto em `/login` não teria como voltar.
- `app/portaria/layout.tsx` ganha um invólucro externo:
  `<div data-tema="escuro" className={estilos.casca}>` em volta do `<div className="conteudo">`, com
  `.casca { background: var(--breu); min-height: 100dvh; }` num `layout.module.css` novo. **O
  invólucro precisa pintar o fundo** — redeclarar token sem pintar deixa texto claro sobre página
  clara.

### A marca (commit 2)

`public/logotipo-rockhub-claro.png`, mesmas dimensões e mesmo alfa derivado do brilho, com o "Rock"
em `#0b1618` e o "Hub" em `#ff4f9a`. `Logotipo.tsx` renderiza os dois `<Image>` com `priority`, e o
`Logotipo.module.css` esconde um por CSS (`[data-tema="claro"] .escuro { display: none }` e o par
inverso). Atributo em seletor de CSS Module não é renomeado pelo compilador — não precisa de
`:global`.

## 5. Critérios de pronto, por commit

**Commit 1 — a paleta em dois modos**

- `npm run build` e `npx tsc --noEmit` passam.
- **O modo escuro está idêntico.** Com `data-tema` ausente ou `escuro`, nenhuma tela mudou de cor —
  é o critério principal, e é verificável porque `--neon2` vale `--neon` no escuro.
- Forçando `data-tema="claro"` no inspetor, as telas de `(site)` e `(entrada)` estão legíveis: fundo
  gelo, texto tinta, botões rosa com letra escura. A marca ainda está errada, e isso é esperado.
- Nenhum hex novo fora do `globals.css`.

**Commit 2 — a marca no modo claro**

- Com `data-tema="claro"` forçado, o lettering aparece com o "Rock" escuro e o "Hub" rosa, sem
  retângulo de fundo em volta, no masthead e nas telas de acesso.
- Com o atributo ausente, a marca é exatamente a de hoje.

**Commit 3 — o alternador**

- O botão aparece nas duas cascas, alterna na hora, e a escolha sobrevive a recarregar e a navegar.
- A primeira pintura já vem no tema escolhido: **nenhum pisca**.
- `/portaria` e `/portaria/eventos/[id]` continuam escuras com o tema claro ligado, incluindo a
  barra de rolagem do documento, e o veredito continua verde-limão sobre breu.
- Foco visível em tudo que é focável nos dois temas, o alternador incluído.
- A suíte do backend continua verde (ela não cobre nada disso — roda para provar que nada foi
  arrastado junto).

## 6. Armadilhas

⚠️ **Mexer no JSX do `Masthead` e do `Logotipo` é onde `className` se perde, e as quatro
verificações passam sem ele.** `npm run build`, `tsc --noEmit`, lint e a suíte do backend não veem
estilo. Ao acrescentar o alternador e o segundo `<Image>`, releia os `className` da árvore antes de
dar o commit por pronto.

⚠️ **Ordem importa no `globals.css`.** `:root` e `[data-tema="claro"]` têm a mesma especificidade e
casam no mesmo elemento; se o bloco claro subir para cima do escuro, o modo claro simplesmente não
acontece. O bloco claro é o último dos três.

⚠️ **Não invente token para o registro do botão.** O `drop-shadow(3px 3px 0 var(--fio2))` do
`Botao.module.css` dá 1,73:1 no escuro e 1,66:1 no claro — o deslocamento de serigrafia se lê
igual nos dois modos sozinho.

⚠️ **Não tokenize o QR do `Canhoto.tsx`.** `bgColor="#e4ebea"` e `fgColor="#0b1618"` estão literais
de propósito e continuam literais: leitor óptico exige fundo claro, e no modo claro os dois tokens
que dariam essa dupla estariam invertidos.

⚠️ **O `not-found.tsx` da raiz renderiza o `CabecalhoDaPortaria` e não está sob o layout dela** — ele
segue o tema escolhido, e isso é aceito. A trava do escuro vale para `/portaria/*`, não para o 404.

⚠️ **`cookies()` no layout raiz torna dinâmica toda rota da aplicação**, inclusive `(entrada)` e
`/portaria`, que hoje poderiam ser pré-renderizadas. É o preço declarado da decisão do cookie; se o
build da Vercel reclamar de rota dinâmica, é isto e não um defeito.

⚠️ **Dois `<Image priority>` significam dois downloads da marca em toda tela.** São dois PNGs
pequenos e é o preço de não piscar; não tente resolver com `<picture media=...>`, que responde a
`prefers-color-scheme` e não ao atributo que a gente controla.

⚠️ **A conferência visual é minha.** Ao terminar cada commit, me entregue o roteiro do que olhar e
espere — não abra a aplicação para conferir por conta.
