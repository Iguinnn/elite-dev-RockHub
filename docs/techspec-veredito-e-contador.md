# Techspec — o veredito a três metros e o contador do turno

**Data:** 2026-08-13 · **Escopo:** Stories 5.4 e 5.6
**Pré-requisito:** [techspec-validacao-na-porta.md](techspec-validacao-na-porta.md) **inteira
aplicada** — as Stories 5.2, 5.3 e 5.5 estão commitadas, e o `Leitor` já valida por câmera e
por digitação.

---

## 1 · Escopo e commits

| Commit | Story | O que entra |
|---|---|---|
| 1 | 5.4 · Ver o resultado a três metros | `components/Veredito.tsx`, os quatro símbolos em SVG, a tinta por `data-veredito`, o corpo de 46px e o bloco subindo para cima do formulário. **Só frontend** |
| 2 | 5.6 · Acompanhar as entradas do turno | Tabela `validacao` com migração, o `INSERT` nos quatro caminhos, `contar_entradas_por_evento` e `contar_recusas`, os campos novos nos três schemas e a ilha `ContadorDoTurno` no cabeçalho |

🛑 **Um commit por vez, e pare.** Terminado cada um, rode a suíte inteira, mostre o resultado e
avise que está pronto para eu commitar — sem escrever README, sem tocar no próximo. Só emende o
seguinte depois que eu mandar. **Esta spec cobrir duas stories não autoriza implementá-las de uma
vez**, e aqui a tentação tem nome: o commit 1 é curto e o 2 parece "só um número a mais na mesma
tela". Não é — o 2 cria tabela.

Com estes dois, a Epic 5 fecha e sobra a Epic 6, que é documentação.

## 2 · O que existe hoje

- **O `Leitor` está completo como ferramenta.** Câmera opt-in por botão, campo manual com Enter,
  guarda de reentrância, foco devolvido só no caminho digitado, e a câmera parando sozinha na
  primeira leitura. O `<video>` desmonta quando ela para — é isso que você descreveu como
  "minimiza a câmera", e a 5.4 desenha o veredito exatamente no vão que ele deixa.
- **O veredito hoje é palavra e detalhe em texto**, dentro de uma `<div aria-live="assertive">`
  que existe no DOM mesmo vazia. Ele mora numa função `Veredicto` dentro do `Leitor.tsx`.
- **Nada no banco registra recusa.** `ingresso.usado_em` e `validado_por` só existem quando
  alguém entrou; `INVALIDO`, `JA_UTILIZADO` e `EVENTO_ERRADO` são resposta HTTP e acabam ali.
- **`ingresso.evento_id` é indexado**, e o comentário da coluna já anuncia esta story como o
  consumidor do índice.
- **Tokens disponíveis:** `--verde`, `--brasa`, `--fumaca`, `--cal`, `--fio`, `--fio2`. Não há
  âmbar nem cinza de veredito, e esta spec não cria nenhum.
- **A convenção de enum no banco é `String(20)` + `CHECK`**, com o `Enum` do Python fora do ORM —
  `usuario.papel` e `reserva.estado` são os dois precedentes.

## 3 · Decisões, com a alternativa descartada

### Verde é entrar; vermelho é não entrar

Os quatro vereditos usam **duas** tintas: `--verde` no `VALIDO`, `--brasa` nos outros três.

**Isto contraria um AC escrito da 5.4** — *"`JA_UTILIZADO` … usa tom neutro, não de fraude"* — e
a tabela de quatro cores do `EXPERIENCE.md`. Estou desviando de propósito. Na porta a pergunta é
binária: essa pessoa entra ou não entra. Quatro tinturas obrigam quem está com a fila esperando a
decodificar qual das quatro apareceu antes de saber o que fazer; duas respondem à pergunta que
existe, e a distinção entre os três motivos de recusa continua inteira na palavra e no símbolo —
que é onde ela é lida de perto, quando a pessoa reclama e é preciso explicar.

**Descartei** as quatro cores da tabela, o que exigiria um `--ambar` novo para o `EVENTO_ERRADO`
(o âmbar do documento é da paleta anterior à troca de acento) e um cinza para o `JA_UTILIZADO` —
duas cores novas num sistema que declara duas tintas.

⚠️ **A regra dos três canais (UX-DR5) continua cumprida, e é preciso ver por quê:** ela proíbe
transmitir informação **só** por cor. Cor, palavra e símbolo continuam aparecendo juntos nos
quatro; o que encolheu foi a cardinalidade de um dos canais, não a quantidade deles. Um veredito
colorido sem símbolo — isso, sim, quebraria a regra.

### Os símbolos são SVG, não caractere

`✓ ✕ ↺ ⤫` como texto dependem de haver o glifo na fonte do aparelho. Os três primeiros existem em
qualquer lugar; o `⤫` é um caractere matemático e **pode virar retângulo vazio** no Android ou num
Windows sem fonte de símbolos — justamente no canal que existe para a informação não depender de
cor. Vão quatro `<svg>` inline, `aria-hidden="true"`, `stroke="currentColor"`, herdando a tinta do
bloco.

**Descartei** o glifo de texto (grátis, e aposta na fonte instalada no celular da porta) e
descartei trocar o `⤫` por um `✕` inclinado, que apagaria a distinção entre `INVALIDO` e
`EVENTO_ERRADO` bem no canal que a decisão anterior acabou de tornar o mais importante.

### O veredito sobe para cima do formulário, e não ganha botão de dispensar

O `EXPERIENCE.md` pede que ele saia por ação explícita — *"Ler o próximo"*. **Descartei o botão.**
O fluxo real da 5.5 já é esse: a câmera lê, ela mesma se desliga, o veredito ocupa o lugar do
vídeo, e o próximo toque é no botão da câmera. Um *Ler o próximo* seria um toque a mais por pessoa
na fila para produzir o estado que o toque seguinte produz de qualquer jeito. O veredito continua
sem sumir sozinho — nenhum `setTimeout` entra —, e quem o substitui é a validação seguinte.

Ele sai de baixo do formulário e vai para **cima** dele, entre o bloco da câmera e o campo. A três
metros o que se lê é o topo da tela, e o campo com a dica empurrava o resultado para a dobra no
celular. A ordem de foco por teclado não sofre: o veredito não é focável e quem o anuncia é o
`aria-live`.

### A 5.6 passa a persistir tentativa, e não só entrada

Contar os quatro exige guardar os quatro, e hoje o banco só sabe de quem entrou. Entra a tabela
**`validacao`**: uma linha por chamada da rota, com o evento, quem validou, o veredito e a hora.

**Descartei** contar só as entradas (o AC original, e o mais barato — mas você quer os quatro) e
descartei contar as recusas na tela, em `useState`: um contador que zera quando alguém recarrega a
página não é um contador, e seria exatamente a coisa validada só no frontend que este projeto está
sendo avaliado por não fazer.

O que se ganha além do número é uma **trilha de auditoria**: quem estava na porta, o que leu e o
que o sistema respondeu. É o registro que faltava para responder "por que essa pessoa não entrou?"
depois do show.

### `entradas` sai de `usado_em`; as três recusas saem da `validacao`

Duas fontes para números vizinhos, e é deliberado. `ingresso.usado_em` é a coluna que o `UPDATE`
condicional do AD-6 escreve **atomicamente** — ela é a verdade sobre quem entrou, e continua sendo
mesmo que a `validacao` um dia perca uma linha. A `validacao` é o registro do que foi tentado.

**Descartei** contar `entradas` também da `validacao` para ter uma fonte só: seria trocar a
garantia do AD-6 por uma tabela de log, e o dia em que os dois números divergirem é o dia em que
eu quero que o `usado_em` ganhe.

⚠️ Consequência assumida: `COUNT(validacao WHERE resultado = 'VALIDO')` e `entradas` devem sempre
bater, e um teste confere isso.

### O contador é do evento inteiro, não da minha conta

`COUNT` por `evento_id`, sem filtrar por `validado_por`. A story quer "noção do movimento", e com
duas portas na mesma casa o número da minha própria digitação não mede a fila — mede a minha
digitação. **Descartei** o recorte por conta.

Ele não empurra: atualiza a cada validação, que é exatamente quando alguém olha para ele. **Sem
polling e sem WebSocket** — uma entrada da outra porta aparece no meu contador na minha próxima
leitura, e isso é rápido o suficiente para o único uso que o número tem.

### O `INSERT` é da mesma transação do `UPDATE`, e não guarda o código tentado

A linha da `validacao` é gravada dentro do mesmo `commit` que queima o ingresso. Fora dela,
existiria a janela em que alguém entrou e o registro não saiu — ou o contrário.

O código digitado **não** é persistido. Ele não muda nenhum dos quatro números, e guardar o que as
pessoas digitam errado é reter dado sem consumidor. O `ingresso_id` fica quando ele é conhecido, e
é nulo nos dois casos de `INVALIDO` (código malformado e código de ingresso nenhum) — a coluna
anulável é a distinção que sobra, e ela basta.

### A contagem mora em `services/ingresso.py`

Nem arquivo novo por tabela nova. O agregado continua sendo o ingresso — a `validacao` é o registro
do que aconteceu com ele —, e o critério do projeto é agrupar por agregado: foi ele que recusou um
`services/portaria.py` na spec anterior, e ele vale igual aqui. **Descartei** `services/validacao.py`,
que agruparia por tabela e deixaria `validar` chamando o vizinho a cada linha.

`services/evento.py` passa a importar `services/ingresso.py` para o `entradas` da lista de turnos.
Não há ciclo: `ingresso.py` importa `models` e `schemas`, nunca `services/evento.py`.

### O contador é ilha própria, e fica fora do `aria-live`

O cabeçalho da tela é Server Component e o número muda por estado do cliente, então o `page.tsx`
passa a montar um wrapper cliente com o contador e o `Leitor` dentro — é o que põe o número **no
cabeçalho**, como o AC pede, em vez de no topo do leitor. **Descartei** desenhá-lo dentro do
`Leitor`, que era zero fiação e deixava o número abaixo do fio, e descartei pô-lo no
`CabecalhoDaPortaria`, que aparece em duas telas onde não há evento nenhum.

⚠️ **Fora da região `aria-live="assertive"`, e isso importa.** Dentro dela, cada validação faria o
leitor de tela anunciar *"VÁLIDO. Pista · Igor Duarte. 41 entradas"* — o dado operacional
atropelando o veredito, que é a única coisa que precisa ser ouvida com a fila andando.

## 4 · Contrato

### Commit 1 — Story 5.4 · sem backend, sem migração

`frontend/src/components/Veredito.tsx` — extraído da função `Veredicto` que hoje mora no
`Leitor.tsx` (a grafia certa vai junto). Recebe `resultado: ResultadoDaValidacao` e devolve o
bloco. As tabelas `PALAVRA` e `detalhe()` vêm junto, sem mudança de texto. Novo:
`SIMBOLO: Record<Veredito, ReactNode>`, quatro SVGs de 44px, `aria-hidden`, `currentColor`.

`Veredito.module.css` — bloco com `border: 2px solid var(--tinta)`, símbolo, palavra em
`700 46px var(--mono)` e o detalhe abaixo de um fio. A tinta entra por atributo:

```css
.veredito { --tinta: var(--brasa); }
.veredito[data-veredito="VALIDO"] { --tinta: var(--verde); }
```

Sem raio, sem sombra, sem fundo (UX-DR3). Abaixo de 420px o corpo cai para 38px por `clamp` —
46px em mono com entreletra estoura a coluna do celular.

`Leitor.tsx` — a região `aria-live` sobe para entre `.bloco` (câmera) e `<form>`. O `.painel` do
`Leitor.module.css` perde o `border-top` e ganha `border-bottom`, porque agora o que ele separa
está embaixo.

### Commit 2 — Story 5.6

**Migração** `cria_tabela_validacao` — ⚠️ `uv run alembic upgrade head` no `rockhub` no mesmo
passo em que ela for criada, e conferir com `alembic current` contra `alembic heads`.

`models/validacao.py`:

```python
class Veredito(str, Enum):
    VALIDO = "VALIDO"
    INVALIDO = "INVALIDO"
    JA_UTILIZADO = "JA_UTILIZADO"
    EVENTO_ERRADO = "EVENTO_ERRADO"

class Validacao(Base):
    __tablename__ = "validacao"
    __table_args__ = (
        CheckConstraint(
            "resultado IN ('VALIDO', 'INVALIDO', 'JA_UTILIZADO', 'EVENTO_ERRADO')",
            name="resultado_valido",
        ),
    )
    id: UUID (pk, uuid4)
    evento_id: UUID  FK evento, not null, index      # o `where` de toda contagem
    portaria_id: UUID FK usuario, not null           # sem ondelete, como validado_por
    ingresso_id: UUID | None FK ingresso, nullable   # nulo nos dois INVALIDO
    resultado: str   String(20), not null            # String + CHECK, como papel e estado
    criado_em: datetime TIMESTAMPTZ, not null
```

Índice só em `evento_id` — não composto com `resultado`: são quatro valores distintos numa tabela
que cresce por show, e o `GROUP BY` sobre o recorte de um evento já é barato.

`schemas/ingresso.py`:

```python
class RecusasDoTurno(BaseModel):
    invalidos: int
    ja_utilizados: int
    evento_errado: int

class ResultadoDaValidacao(BaseModel):
    resultado: Veredito          # era Literal[...]; passa a ser o enum do modelo
    titular_nome: str | None = None
    setor_nome: str | None = None
    entrada_em: datetime | None = None
    entradas: int
    recusas: RecusasDoTurno
```

O `Literal` sai porque as quatro palavras passariam a existir em dois lugares. `str, Enum` serializa
igual e o OpenAPI fica melhor.

`schemas/evento.py`: `TurnoDaPortaria` ganha `entradas: int` (a lista de turnos mostra quantas
pessoas já entraram em cada porta). Novo `TurnoDoLeitor(TurnoDaPortaria)` com
`recusas: RecusasDoTurno`, e é ele o `response_model` de `GET /portaria/eventos/{evento_id}` — as
três recusas não entram na lista, que não as desenha.

`services/ingresso.py`:

- `contar_entradas_por_evento(sessao, eventos: list[UUID]) -> dict[UUID, int]` — um `GROUP BY`
  sobre `ingresso`, `usado_em IS NOT NULL`. A rota de um turno chama com uma lista de um.
- `contar_recusas(sessao, evento_id) -> RecusasDoTurno` — `GROUP BY resultado` sobre `validacao`,
  `resultado != 'VALIDO'`. Veredito sem linha nenhuma é `0`, nunca ausente.
- `validar` — grava a `Validacao` **antes do `commit`**, nos quatro caminhos (inclusive nos dois
  `INVALIDO` que hoje respondem sem tocar no banco: eles passam a ter um `INSERT`), e monta a
  resposta com as duas contagens lidas depois do `commit`.

`services/evento.py`: `listar_escalados` e `montar_turno` passam o `entradas`; `montar_turno` ganha
o parâmetro, no molde do `agora`.

`frontend`: `components/ContadorDoTurno.tsx` + `.module.css`; `LeitorDoTurno` (`page.tsx`) passa a
montar um wrapper cliente `PainelDoTurno` com o contador no cabeçalho e o `Leitor` abaixo, e o
estado das contagens sobe para ele — o `Leitor` ganha `onContagens`. `lib/turnos.ts` e
`lib/validacao.ts` ganham os campos nos tipos.

Leitura do cabeçalho: **`ENTRADAS 41`** em mono grande, e abaixo, em versalete pequeno de
`--fumaca`, `INVÁLIDOS 2 · JÁ UTILIZADOS 1 · OUTRO SHOW 0`.

## 5 · Critérios de pronto, por commit

**Commit 1 (5.4)**

- [ ] Os quatro vereditos aparecem com cor, palavra e símbolo simultâneos; `VALIDO` em `--verde` e
      os três outros em `--brasa`
- [ ] Os símbolos são SVG, `aria-hidden`, e herdam a tinta do bloco — nenhum caractere de fonte
- [ ] O resultado **não some sozinho**: nenhum `setTimeout` no arquivo. Quem o substitui é a
      validação seguinte
- [ ] `JA_UTILIZADO` mostra a hora da primeira entrada
- [ ] O bloco fica **acima** do formulário, e a região `aria-live="assertive"` continua no DOM
      mesmo vazia — o anúncio depende disso
- [ ] Palavra de 46px que não estoura a coluna em 360px de largura
- [ ] `npm run build` e `tsc --noEmit` limpos · `uv run pytest` verde (o backend não mudou; é
      conferência de que não mudou)
- [ ] Conferido **na tela**, por você: os quatro resultados, um a um

**Commit 2 (5.6)**

- [ ] Migração aplicada no `rockhub` e no `rockhub_teste`; `alembic current` == `alembic heads`
- [ ] Cada uma das quatro validações grava **uma** linha em `validacao`, com o evento, quem
      validou e a hora — inclusive os dois `INVALIDO`
- [ ] O código digitado **não** aparece em nenhuma coluna
- [ ] `ingresso_id` preenchido quando o ingresso existe, nulo quando não
- [ ] Os contadores vêm do banco: validar, recarregar a página, e os quatro números continuam lá
- [ ] `entradas` bate com `COUNT(validacao WHERE resultado = 'VALIDO')` do mesmo evento
- [ ] Uma validação da **outra** conta de portaria aparece no meu contador na minha leitura
      seguinte
- [ ] A escrita é da mesma transação: um erro depois do `UPDATE` não deixa entrada sem registro
- [ ] `GET /portaria/eventos/{id}` traz os quatro números antes de qualquer validação; a lista de
      turnos traz `entradas` e **não** traz as recusas
- [ ] O contador está **fora** da região `aria-live`
- [ ] `uv run pytest` verde, número registrado · `npm run build` e `tsc --noEmit` limpos
- [ ] Uma linha em `README.md#o-que-não-está-pronto` se algo da epic ficar de fora

## 6 · Armadilhas

⚠️ **As contagens são lidas depois do `commit`, nunca antes.** Lida antes, a contagem enxerga a
própria linha não commitada em alguns caminhos e não em outros, e o número oscila de um em um sem
motivo visível. Depois do `commit`, com `expire_on_commit=False`, a leitura é uma consulta nova e
está certa — é a quarta aparição dessa família de armadilha no projeto.

⚠️ **Os dois `INVALIDO` passam a tocar o banco.** Hoje o código malformado responde "sem tocar no
banco", e o docstring do `validar` se gaba disso. Com a `validacao`, ele grava — a frase do
docstring precisa ser corrigida no mesmo commit, senão fica uma promessa falsa no arquivo mais
lido da epic.

⚠️ **`EVENTO_ERRADO` grava a linha no evento do caminho, não no do ingresso.** É a contagem *deste*
turno; a tentativa aconteceu nesta porta. Gravar no evento do ingresso jogaria a recusa no painel
de um show em que ninguém tentou nada — e vazaria, pelo contador, a existência de um ingresso de
outro evento para a portaria que o AD-7 proíbe de saber disso.

⚠️ **A ordem das etapas do `validar` não muda.** O `EVENTO_ERRADO` continua antes do `UPDATE`, e a
assinatura continua sendo conferida contra o `evento_id` **do ingresso**. Acrescentar escrita no
meio é exatamente o tipo de edição que embaralha ordem sem querer.

⚠️ **`data-veredito` no elemento, e o `switch` de cor no CSS.** A tentação é calcular a classe em
JavaScript e ter `estilos[resultado]` — que o `tsc` não confere e que quebra em silêncio quando um
nome de classe some do CSS Module.

⚠️ **O `Leitor` sobe estado para o wrapper, e o wrapper não pode ser Server Component.** O
`page.tsx` continua Server Component com as guardas; quem tem `"use client"` é o `PainelDoTurno`.
Marcar o `page.tsx` como cliente derrubaria as duas guardas de sessão e papel para dentro do
navegador.

⚠️ **Duas telas leem `TurnoDaPortaria`.** Acrescentar `entradas` nele muda a lista de turnos
também — o cartão dela precisa desenhar o número ou ignorá-lo por escolha, não por esquecimento.

---

**Fontes:** `epics.md` (Stories 5.4 e 5.6) · `EXPERIENCE.md#Os quatro vereditos da portaria`,
`#State Patterns` · `DESIGN.md#veredito` · `ARCHITECTURE-SPINE.md` (AD-6, AD-7, AD-11, AD-13) ·
`docs/techspec-validacao-na-porta.md` · `backend/app/services/ingresso.py`,
`services/evento.py`, `models/ingresso.py`, `schemas/evento.py`, `api/portaria.py` ·
`frontend/src/components/Leitor.tsx`, `app/portaria/eventos/[id]/page.tsx`, `app/globals.css`
