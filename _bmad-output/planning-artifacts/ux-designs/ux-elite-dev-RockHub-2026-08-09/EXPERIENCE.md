---
name: RockHub — Experiência
status: final
created: '2026-08-09'
updated: '2026-08-10'
sources:
  - '_bmad-output/brainstorming/brainstorm-plataforma-eventos-ingressos-2026-08-08/brainstorm-intent.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md'
  - 'docs/desafio-elite-dev.md'
companions:
  - 'DESIGN.md'
---

# EXPERIENCE.md — RockHub

Identidade visual em [DESIGN.md](DESIGN.md); tokens referenciados aqui por nome, ex. `{colors.ambar}`.
Protótipo navegável: [mockups/proto-jornal-noturno.html](mockups/proto-jornal-noturno.html).

**O protótipo é referência, não gesso.** O Igor vai ajustar telas durante a implementação — isso é
esperado. Ver *Como usar este documento* em [DESIGN.md](DESIGN.md) para o que é duradouro e o que é
provisório. O que não muda sem decisão dele: os anti-padrões proibidos, a regra dos três canais nos
vereditos, o piso de acessibilidade e a ergonomia distinta por papel.

## Foundation

**Form-factor:** web responsiva, desktop-first para cliente e organizador, **mobile-first para a
portaria** — que trabalha de celular, em pé, na fila.

Sem biblioteca de componentes. Next.js com CSS próprio; não há shadcn, MUI nem equivalente. A
razão é a mesma que sustenta a direção visual: sistema de componentes pronto traz consigo o
vocabulário visual que este projeto está tentando não ter.

**Princípio que organiza tudo:** os três papéis têm ergonomias físicas opostas, e a interface
reconhece isso.

| Papel | Situação real | Consequência de projeto |
|---|---|---|
| Cliente | Sentado, com tempo, comparando opções | Densidade alta, informação lado a lado, leitura confortável |
| Organizador | Na mesa, preenchendo formulário longo | Formulário em etapas numeradas, campos largos, dados exatos |
| Portaria | **Em pé, na fila, à noite, uma mão só, com gente esperando** | Alvos grandes, tipografia enorme, resultado legível a três metros, mínimo de toques |

## Information Architecture

**Cliente**

```
Início (listagem)  →  Evento (setores)  →  Checkout  →  Aprovado | Recusado
Meus ingressos     →  Ingresso (QR, compartilhar, revogar)
Minha conta        →  dados, sair
```

**Organizador** — mesma casca do cliente, com navegação própria.

```
Meus eventos
Publicar evento  →  1 catálogo Ticketmaster · 2 data, local e setores · 3 escalar portaria
Minha conta
```

**Portaria** — navegação própria, sem o header do cliente.

```
Turnos (eventos em que foi escalado)  →  Leitor  →  Veredito  →  Leitor
```

**Público, sem login:** `/i/TOKEN` — ingresso compartilhado com QR.

Fechamento: toda necessidade declarada tem superfície, e toda superfície tem jornada que chega
nela. Não há tela órfã.

## Voice and Tone

Jornalística: específica, curta, sem entusiasmo comercial. Nunca exclamação. Nunca "incrível",
"imperdível", "garanta já".

| Situação | Escreva | Não escreva |
|---|---|---|
| Setor com pouco estoque | "Últimos ingressos" | "Corra! Restam só 41!" |
| Pagamento recusado | "O cartão não foi autorizado" | "Ops! Algo deu errado 😕" |
| Lista vazia | "Você ainda não comprou nenhum ingresso" | "Nada por aqui ainda... que tal explorar?" |
| Esgotado na corrida | "A Pista acabou de esgotar" | "Poxa, chegou tarde!" |
| Veredito negativo | "Já utilizado — entrou às 20h51" | "Ingresso inválido!!!" |

**Erro sempre diz o que aconteceu e o que fazer agora.** "Nada foi cobrado, e os seus lugares
voltaram para a venda" vale mais que qualquer pedido de desculpas.

## Component Patterns

Especificação visual em `DESIGN.md`; aqui só o comportamento.

### fila-listagem
Toda a fila é clicável, não só o nome. Hover pinta `{colors.breu2}`. Fila esgotada não é clicável
e não muda no hover — a ausência de resposta é a informação.

### setor + stepper
Stepper não desce abaixo de zero nem acima do disponível. Setor esgotado aparece com opacidade
reduzida, sem stepper. O total no rodapé recalcula a cada toque, sem confirmação.

### medidor
Mostra proporção, nunca número. Cliente lê três estados: `Disponível`, `Últimos ingressos`
(`{colors.ambar}`) e `Esgotado`. **Organizador e portaria veem números exatos** — é o inventário
deles, e esconder ali só atrapalha operação.

### rodapé de compra
Fixo na base ao rolar (`position: sticky`), mostrando quantidade, setor e total. Nunca deixa o
usuário rolar de volta ao topo para saber quanto vai pagar.

### cronômetro de reserva
Aparece no checkout mostrando o tempo restante dos 10 minutos (AD-4). Não pisca, não muda de cor,
não faz contagem regressiva agressiva. Informa; não pressiona.

### canhoto
Um canhoto por ingresso — dois ingressos são dois canhotos, com códigos diferentes. O QR é sempre
o elemento de maior peso visual da tela.

### veredito
Ver *State Patterns*. Some apenas por ação explícita ("Ler o próximo"), nunca por tempo — a
portaria precisa poder olhar duas vezes com fila esperando.

## State Patterns

### Os quatro vereditos da portaria

Requisito do desafio (FR6). Cada um usa **três canais simultâneos** — cor, palavra e símbolo —
porque cor sozinha falha na pressa, no escuro e para quem tem daltonismo.

| Estado | Cor | Símbolo | Palavra | Detalhe exibido |
|---|---|---|---|---|
| `VALIDO` | `{colors.verde}` | ✓ | VÁLIDO | Setor, quantidade, titular, hora da entrada |
| `INVALIDO` | `{colors.brasa}` | ✕ | INVÁLIDO | "Assinatura não confere" |
| `JA_UTILIZADO` | `#6E675C` | ↺ | JÁ UTILIZADO | Hora em que entrou |
| `EVENTO_ERRADO` | `{colors.ambar}` | ⤫ | EVENTO ERRADO | De qual show o ingresso é |

`JA_UTILIZADO` é deliberadamente neutro, não vermelho: não é fraude nem falha do sistema, é uma
pessoa tentando entrar duas vezes ou um crachá lido em duplicidade. Tratar como erro grave gera
atrito desnecessário na porta.

### Vazio

| Superfície | Mensagem |
|---|---|
| Meus ingressos | "Você ainda não comprou nenhum ingresso. Quando comprar, ele aparece aqui com o código de entrada." |
| Busca sem resultado | "Nenhum show encontrado para essa busca." |
| Turnos da portaria | "Você não foi escalado para nenhum evento." |

Estado vazio não ganha ilustração nem botão grande de chamada. Kicker em versalete, frase, fim.

### Carregando

Sem *spinner*. A estrutura da página aparece com os fios e as etiquetas no lugar, e o conteúdo
preenche. Nada gira, nada pulsa.

### Erro de estoque durante o checkout

Consequência direta do AD-3. Quando o `UPDATE` condicional afeta zero linhas:

> **Esgotou enquanto você decidia.** A Pista acabou de esgotar. Ainda há ingressos na Área VIP.

Oferece o próximo setor disponível. Nunca devolve o usuário ao início.

## Interaction Primitives

- **Sem animação de travessia.** Nada desliza de uma lateral à outra — é o primeiro anti-padrão da
  lista. Transições permitidas: mudança de cor em hover, até 120ms
- **Foco visível sempre**: contorno `{colors.ambar}` de 2px, jamais `outline: none`
- **Toque mínimo de 44px** em qualquer alvo da portaria
- **Enter valida** no campo de código manual — o operador não deve precisar mirar num botão
- **Sem confirmação dupla** em ação reversível. Revogar link pede confirmação; ajustar quantidade não

## Accessibility Floor

- Contraste AA em todo texto; AAA no texto principal (ver `DESIGN.md`)
- Nenhuma informação transmitida **só** por cor — daí a regra dos três canais nos vereditos
- Todo campo tem `<label>` associado, não apenas *placeholder*
- Resultado da validação é anunciado por leitor de tela via `aria-live="assertive"`
- Navegação completa por teclado nas telas de cliente e organizador
- QR acompanhado do código em texto, para quem não consegue escanear
- `prefers-reduced-motion` remove as transições de cor

## Responsive & Platform

| Faixa | Comportamento |
|---|---|
| ≥ 900px | Layout pleno: listagem em quatro colunas, chamada principal em duas |
| < 900px | Chamada principal e ficha de evento empilham; fila vira duas colunas (data + bloco) |
| Portaria | Sempre coluna única, mira quadrada ocupando a largura, botão de largura inteira |

A portaria é a única superfície projetada **primeiro** para telas pequenas.

## Key Flows

### 1. Igor compra dois ingressos

Igor, 26 anos, quer levar a namorada no show de sexta. Está no sofá, no notebook.

1. Abre o RockHub e vê a chamada principal com o show de sexta
2. Percorre a programação — data à esquerda, nome grande, preço à direita
3. Clica na fila do Baco Exu do Blues
4. Vê três setores. Pista está disponível, VIP com "Últimos ingressos", Camarote esgotado
5. Põe 2 na Pista. O rodapé mostra R$ 240,00
6. **Clímax:** clica em reservar — e o cronômetro aparece dizendo que os lugares são dele por 10
   minutos. É o momento em que a compra deixa de ser navegação e vira compromisso
7. Paga. Dois canhotos, dois códigos diferentes

### 2. Ana valida na porta

Ana trabalha na portaria do Espaço Unimed. 20h40, fila na calçada, celular numa mão.

1. Entra e vê **dois** eventos — só aqueles em que foi escalada
2. Toca no show de hoje
3. Câmera abre com a mira. Aponta para o celular da primeira pessoa
4. **Clímax:** a tela inteira vira verde com um ✓ e a palavra VÁLIDO em corpo enorme. Ana não
   precisa ler nada — a três metros já sabe. Toca em "Ler o próximo"
5. Terceira pessoa: tela cinza, ↺, JÁ UTILIZADO, "entrou às 20h51". Ana explica sem se alterar,
   porque a tela não a tratou como se fosse fraude
6. Câmera falha numa quarta pessoa. Ana digita o código no campo abaixo e aperta Enter

### 3. Carla publica um show

Carla é produtora e vai publicar a data de sexta.

1. Entra em "Publicar evento" e busca "baco exu" no catálogo da Ticketmaster
2. Escolhe a atração certa entre duas
3. Preenche data, horário e casa
4. Monta três setores com nome, capacidade e preço — números exatos, é o inventário dela
5. **Clímax:** no passo 3, precisa escalar quem vai validar. Sem ao menos um usuário de portaria,
   o botão de publicar não libera — e o texto explica por quê: *"Só quem for escalado aqui poderá
   validar ingressos deste evento"*
6. Publica

## Inspiration & Anti-patterns

**Referência assumida:** jornal impresso de programação cultural — masthead, fios, versaletes,
listagem em pauta. Não sites de ingresso.

**Referências explicitamente rejeitadas:** Sympla, Eventim e Ingresso.com, pela fileira horizontal
de cards com paleta empresarial. A crítica não é estética, é conceitual: tratam ingresso como item
de catálogo de e-commerce.

**Anti-padrões proibidos** — os cinco de `DESIGN.md`. Cada um vira critério de aceite nas stories
de interface: uma tela que reintroduza qualquer um deles está errada, mesmo que fique bonita.
