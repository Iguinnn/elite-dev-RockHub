---
name: RockHub — Jornal Noturno
status: final
created: '2026-08-09'
updated: '2026-08-10'
sources:
  - '_bmad-output/brainstorming/brainstorm-plataforma-eventos-ingressos-2026-08-08/brainstorm-intent.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md'
companions:
  - 'EXPERIENCE.md'
colors:
  breu: '#0E0D0C'
  breu2: '#151311'
  cal: '#EDE8DC'
  fumaca: '#8F877A'
  ambar: '#F2A413'
  brasa: '#D93B2B'
  verde: '#3FA96B'
  fio: '#2A2622'
  fio2: '#3A352F'
typography:
  serif: "Georgia, 'Times New Roman', serif"
  mono: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
  display: '46px/1.02, letter-spacing -0.03em, serif regular'
  titulo: '27px/1.14, letter-spacing -0.022em, serif regular'
  corpo: '16px/1.55 serif'
  standfirst: 'italic 18px/1.5 serif'
  kicker: '600 10px/1 mono, letter-spacing 0.22em, uppercase'
  etiqueta: '600 11px/1 mono, letter-spacing 0.15em, uppercase'
rounded:
  tudo: '0'
spacing:
  base: '4px'
  fio: '1px'
  fio_duplo: '3px double'
components:
  - masthead
  - fila-listagem
  - chamada-principal
  - setor
  - stepper
  - canhoto
  - veredito
  - botao
  - medidor
---

# DESIGN.md — RockHub

## Como usar este documento

O protótipo e as medidas aqui são **ponto de partida, não gesso**. O Igor vai ajustar e aperfeiçoar
durante a implementação, e isso é esperado — não é desvio.

Mas nem tudo tem o mesmo peso:

**Duradouro** — mexer só com decisão consciente dele:

- A identidade "jornal noturno": estrutura editorial impressa sobre preto
- A paleta e a regra do acento único em âmbar
- Serifada para nome próprio, monoespaçada para dado de máquina
- Ausência de card, sombra e canto arredondado
- Os cinco anti-padrões proibidos
- Contagem exata de estoque escondida do cliente

**Provisório** — ajuste livre durante a codificação:

- Tamanhos, espaçamentos e proporções exatas
- Grade de colunas de cada tela
- Microcopy
- Quais componentes existem e como se dividem

Na dúvida entre seguir a medida literal e melhorar a tela, melhore a tela — e registre a mudança
aqui e no README.

## Brand & Style

**Jornal noturno.** Um *broadsheet* de programação musical impresso sobre preto. A estrutura é de
impresso — masthead, fios, filas, versaletes, serifada nos nomes próprios — e a cor é de casa de
show à noite.

A direção nasceu da fusão de duas alternativas rejeitadas pela metade: a identidade editorial de um
jornal de eventos londrino, e a paleta noturna de uma parede de cartazes. Nenhuma das duas sozinha
resolvia; a mistura resolve.

**Voz da marca:** jornalística e específica. Frases curtas, informação antes de adjetivo, nada de
entusiasmo de e-commerce. A interface informa o que está em cartaz; não convence ninguém a comprar.

**O que esta identidade recusa** — cada item é um anti-padrão nomeado pelo Igor no brainstorming:

1. Faixa ou linha que varre a tela em movimento contínuo (marquee, ticker), e hovers que deslizam
   de uma lateral à outra
2. Grade de 6 a 8 cards nomeando seções do site
3. Par de título display gigante com um texto pequeno logo abaixo, como bloco de abertura
4. Fileira horizontal de cards com paleta empresarial — o formato de Sympla, Eventim e Ingresso.com
5. Linha de contexto decorativa no cabeçalho ("Edição de sexta · 14 de agosto · 14 apresentações
   em cartaz"). Foi testada e removida: soa gerada

## Colors

Preto quente de tinta, nunca `#000`. Branco quente de jornal, nunca `#FFF`.

| Token | Hex | Uso |
|---|---|---|
| `breu` | `#0E0D0C` | Fundo de toda a aplicação |
| `breu2` | `#151311` | Superfície elevada: resumo, campo de formulário, fila em hover |
| `cal` | `#EDE8DC` | Texto principal |
| `fumaca` | `#8F877A` | Texto secundário, etiquetas, kickers |
| `ambar` | `#F2A413` | Acento único da marca. Ação primária, item ativo, alerta de escassez |
| `brasa` | `#D93B2B` | Erro, esgotado, pagamento recusado, ingresso inválido |
| `verde` | `#3FA96B` | Exclusivo do veredito `VALIDO` e da confirmação de pagamento |
| `fio` | `#2A2622` | Todos os fios, filetes e bordas |
| `fio2` | `#3A352F` | Fio sobre superfície elevada; medidor esgotado |

**Regra do âmbar:** é o único acento de marca. Se algo precisa de destaque e não é erro nem
sucesso, é âmbar. Não introduza um segundo acento decorativo.

**Contraste:** `cal` sobre `breu` = 14.8:1. `fumaca` sobre `breu` = 5.2:1. `ambar` sobre `breu` =
9.6:1. Todos passam AA; os dois primeiros passam AAA.

## Typography

Duas famílias, ambas de sistema — **nenhuma fonte externa**, por decisão de performance e de
não depender de rede.

**Serifada (Georgia)** — nomes de artista, títulos, manchetes, valores monetários, corpo de texto.
É a voz do jornal.

**Monoespaçada** — tudo que é máquina ou etiqueta: códigos de ingresso, horários em lista, kickers,
rótulos de campo, estados. Sempre em versalete com `letter-spacing` largo (`0.15em` a `0.22em`).

A tensão entre as duas é a identidade. Serifada sozinha vira convite de casamento; monoespaçada
sozinha vira terminal.

| Papel | Especificação |
|---|---|
| Manchete (chamada principal) | serif 46px/1.02, `-0.03em` |
| Título de evento (página) | serif 52px/1, `-0.035em` |
| Nome em fila de listagem | serif 27px/1.14, `-0.022em` |
| Standfirst | serif italic 18px/1.5, cor `#BEB6A8` |
| Corpo | serif 16px/1.55 |
| Kicker | mono 600 10px, `0.22em`, versalete, `fumaca` |
| Etiqueta de campo | mono 600 10px, `0.15em`, versalete, `fumaca` |
| Código de ingresso | mono 10–11px, `0.13em` |
| Veredito da portaria | mono 700 46px, `0.06em`, versalete |

Números de data em fila usam serifada em corpo grande (30px), com dia da semana e hora em
monoespaçada acima e abaixo. É a assinatura visual da listagem.

## Layout & Spacing

**Sem cards.** A listagem é uma pauta: filas separadas por fio de 1px, sem caixa, sem sombra, sem
raio. Esta é a decisão estrutural que sustenta *"ingresso não é produto de prateleira"*.

Grade da fila de listagem: `96px | 1fr | 210px | 150px` — data, nome, local, preço. Colapsa para
duas colunas abaixo de 900px.

Largura máxima do conteúdo: `1180px`, com `18px` de respiro lateral.

Ritmo vertical: múltiplos de 4px. Padding de fila: 20px. Padding de seção: 22px acima, 11px abaixo
do fio.

**Fios são estruturais, não decorativos.** Fio simples (`1px solid fio`) separa itens iguais. Fio
duplo (`3px double fio`) fecha o masthead e separa blocos de natureza diferente. Não existe fio
"para preencher espaço".

## Elevation & Depth

Praticamente ausente. Não há sombra em nenhum elemento de interface — profundidade se expressa por
`breu2` sobre `breu` e por fios. A única sombra do sistema é a do próprio protótipo, para simular
a moldura do navegador, e não faz parte do produto.

## Shapes

**Raio zero em tudo.** Botão, campo, medidor, selo, moldura. Papel não tem canto arredondado.

Exceções permitidas: nenhuma.

O picote do canhoto é `2px dashed fio` — a única linha tracejada do sistema, reservada para separar
o corpo do ingresso do seu talão.

## Components

### masthead
Logotipo em serifada 44px com `Hub` em itálico âmbar, sobre fio simples, com a barra de navegação
abaixo e fio duplo fechando o bloco. **Não recebe linha de contexto, data, contador nem subtítulo.**

### fila-listagem
Quatro colunas, sem caixa, fio embaixo, `breu2` no hover. Estado esgotado: nome e data em
`#5F5A52`, preço substituído por selo `brasa` vazado.

### chamada-principal
Duas colunas: arte 16/10 com degradê para o `breu` na base, e coluna de texto com kicker, manchete,
standfirst e ficha de três dados. Existe uma única por tela, no topo da listagem. **É o elemento
que faz a tela parecer jornal** — sem ela, a listagem vira só uma tabela.

### setor
Nome em serifada 25px, medidor de proporção, estado em versalete. Stepper de quantidade à direita.
Nunca exibe contagem absoluta em tela de cliente.

### medidor
Barra de 5px, `#221F1C` de fundo, preenchimento `ambar`. Preenchimento `brasa` quando restam
poucos. Esgotado: preenchimento total em `fio2`. Comunica proporção, jamais número.

### stepper
Três células com fio entre elas, 38px de altura. Hover no botão inverte para âmbar sobre breu.

### canhoto
Duas colunas com picote tracejado: à esquerda, dados em ficha; à direita, fundo `cal` com o QR em
`breu` e o código em monoespaçada. **O QR sempre sobre `cal`** — nunca sobre fundo escuro, por
legibilidade de leitor óptico.

### veredito
Bloco de resultado da portaria com borda de 2px, símbolo grande, palavra em monoespaçada 46px e
detalhe abaixo de um fio. Ver `EXPERIENCE.md` para os quatro estados e a regra dos três canais.

### botao
Retangular, sem raio, monoespaçada 700 12px em versalete com `0.18em`. Primário: fundo `ambar`,
texto `breu`. Secundário: transparente com fio. Destrutivo: fundo `brasa`.

## Do's and Don'ts

**Faça**

- Use fio para separar; use espaço para agrupar
- Ponha nome próprio em serifada e dado de máquina em monoespaçada
- Deixe o âmbar ser raro — quanto menos aparece, mais funciona
- Use versalete com letterspacing largo em toda etiqueta
- Mantenha o QR sobre fundo claro

**Não faça**

- Não use card, caixa, sombra ou canto arredondado
- Não introduza um segundo acento além do âmbar
- Não mostre contagem exata de ingressos em tela de cliente
- Não coloque linha de contexto decorativa no masthead
- Não use `#000` nem `#FFF`
- Não anime nada que atravesse a tela lateralmente
- Não use serifada em etiqueta, nem monoespaçada em nome de artista
