# Techspec — a hora em que o show acaba

**Data:** 2026-08-14 · **Cobre:** três commits `feat` **fora da numeração das stories**
**Formato:** ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As Epics 1 a 5 estão fechadas e só a 6 (documentação) sobra, então isto não é story de epic
nenhuma — mesmo precedente do filtro do catálogo e do editar/excluir evento. O `sprint-status.yaml`
ganha comentário na Epic 5, que é onde o assunto mais pesado mora, e nenhuma linha de status nova.

**O que motivou:** achei um defeito de produção em 14/08/2026. Evento que já aconteceu continua com
o ingresso marcado **Ativo** na conta do cliente, e o turno continua na lista da portaria — clicável,
validável — dias depois do show. As três metades têm causas diferentes e uma raiz só: **o sistema
não sabe quando um show termina.** O `ABERTURA_DOS_PORTOES` diz isso com todas as letras no comentário
dele: *"não há fechamento, de propósito (…) sem contar que este projeto não tem coluna de duração
nenhuma."*

A correção é o organizador declarar a hora de término na publicação. Depois dela, ingresso não
utilizado deixa de valer e o turno vira *"O evento acabou"*.

---

## 1 · Escopo e commits

| Commit | O que entrega |
|---|---|
| 1 | `evento.data_hora_fim` com a migração e o preenchimento retroativo, os dois schemas de entrada, a recusa `FIM_ANTES_DO_INICIO` e o campo nos dois formulários — publicar e editar |
| 2 | `IngressoNaLista.situacao` e `IngressoDetalhe.situacao`, o terceiro bloco em `/ingressos` e o canhoto encerrado |
| 3 | O fechamento do portão: `porta_aberta` com teto, `403 EVENTO_ENCERRADO`, `EstadoDoTurno` no lugar de `aberto`, e a tag na lista de turnos |

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para eu commitar** — sem escrever README, sem tocar no seguinte. Só emende o
próximo depois de eu mandar. Esta spec cobrir três commits **não** autoriza implementá-los de uma
vez: o histórico do git é parte da avaliação, e o commit por story é a única coisa que a spec
agrupada não pode custar.

**A ordem não é negociável.** O commit 1 é o único que mexe no banco, e os outros dois leem a coluna
que ele cria. Ele abre uma janela consciente de um commit: a coluna existe, o formulário a preenche
e **nada muda de comportamento** — nem o ingresso, nem a porta. Mesma forma da janela entre a 2.4 e
a 2.5, e ela fecha no commit 3.

## 2 · O que existe hoje

`Evento` tem `data_hora` e mais nada sobre tempo. As quatro rotas públicas e a criação de reserva
cortam em `data_hora >= agora` — o show some da programação no minuto em que começa.

`porta_aberta(evento, agora)` (`services/evento.py:851`) devolve `data_hora - 2h <= agora`, **sem
teto**. Ela é a fonte única de duas coisas: o `TurnoDaPortaria.aberto` que a lista de turnos desenha,
e o `403 EVENTO_NAO_ABERTO` da dependência `exigir_porta_aberta`. Uma regra, um relógio, um lugar —
isso não muda, só ganha o outro lado.

`listar_escalados` **não corta por tempo**, e continua não cortando: a portaria trabalha do outro
lado do corte público, e o docstring dela defende isso desde a 5.1.

`GET /ingressos` devolve `IngressoNaLista` com `usado_em`, e a tela ([ingressos/page.tsx:42]) separa
*Ativos* de *Utilizados* comparando `usado_em === null`. Não existe terceiro estado em lugar nenhum.

`_montar_detalhe` (`services/ingresso.py:147`) é o **único** lugar que monta o canhoto, e ele serve as
três rotas — a do dono, a do detalhe e a pública do link compartilhado. Campo novo ali atravessa para
quem não tem conta, e o docstring já avisa disso.

Os dois formulários montam `data_hora` de dois campos (`data` + `hora`) e mandam
`instante.toISOString()`.

## 3 · Decisões, com a alternativa descartada

**Só a hora de término, com a virada de meia-noite inferida.** O formulário ganha um `<input
type="time">` e nada mais; se a hora de fim for menor ou igual à de início, o sistema soma um dia — o
show das 23h que acaba às 02h cai no dia seguinte, sozinho. *Descartei* pedir data **e** hora com um
segundo `SeletorDeData`: nada seria inferido, ao custo de um calendário a mais num formulário que já
tem seis campos, para resolver um show de mais de 24 horas que este produto não vende. O preço da
inferência é que ela precisa ser dita em voz alta — o rótulo é `Termina às`, e a tela mostra a data
resultante quando ela vira.

**A coluna é obrigatória, e a migração calcula o término dos eventos antigos como `data_hora + 6h`.**
Todo evento do banco passa a ter término, inclusive os que já estão na Railway servindo o roteiro de
avaliação — e é isso que faz o defeito que motivou esta spec sumir **também nos eventos que já
existem**. *Descartei* deixar a coluna anulável: nada seria inventado, mas `porta_aberta`, a tela do
ingresso e a do turno passariam a carregar um "e se não tem término?" para sempre, e os eventos de
produção continuariam exatamente com o bug. Invariante que vale para os novos e não para os antigos é
invariante pela metade — é a mesma disciplina do `EVENTO_SEM_PORTARIA`. As seis horas são folga
deliberada: com três, um evento antigo do banco poderia aparecer já encerrado no meio de um teste meu,
e eu descobriria o comportamento novo pelo susto.

**Ingresso expirado é estado derivado na leitura, não coluna.** `situacao` nasce da comparação entre
o término do evento e o relógio, a cada resposta. *Descartei* uma coluna `expirado_em` colhida
preguiçosamente no molde do AD-4: aquela colheita existe porque **estoque precisa voltar para
alguém**, e aqui nada é liberado — o ingresso só deixa de valer. Escrever uma coluna para registrar a
passagem do tempo é guardar o que o relógio já responde, e ainda obrigaria a tela de ingressos, que é
Server Component e leitura pura, a virar escrita a cada visita.

**A recusa na porta é `403 EVENTO_ENCERRADO`, na dependência — não um quinto veredito.** Ela entra ao
lado do `EVENTO_NAO_ABERTO` que já mora lá, pelo mesmo motivo: a recusa é sobre **o turno**, não sobre
o ingresso. E o comportamento de tela sai pronto, porque a 5.3 já manda todo `403` do leitor
redirecionar para `/portaria` — a portaria volta à lista e lê a tag. *Descartei* um quinto veredito
`EVENTO_ENCERRADO` respondido `200` pelo `validar`: seria mais claro para quem está na fila, e custa o
`CHECK` de `validacao.resultado`, o enum `Veredito`, o `RecusasDoTurno` de três campos, o contador do
turno e um quinto símbolo SVG — contrariando de uma vez as duas decisões escritas *"sem quinto
veredito"* (5.2) e *"duas tintas para quatro vereditos"* (5.4).

**O portão fecha no instante exato do término, sem tolerância.** *Descartei* uma
`TOLERANCIA_APOS_O_FIM` simétrica às duas horas de abertura: ela cobriria o retardatário, e o preço
seria o sistema discordando do número que o organizador acabou de digitar — o ingresso valeria por X
horas a mais do que a tela do cliente diz. A folga mora na hora declarada: quem quiser margem marca
03h em vez de 02h.

**O corte das rotas públicas continua em `data_hora`.** *Descartei* movê-lo para `data_hora_fim`, o
que deixaria o show visível e vendável enquanto acontece — comportamento certo do mundo real, e que
conserta a assimetria de a portaria trabalhar do outro lado do corte. Ele custa quatro rotas públicas,
a criação de reserva, o `EVENTO_NO_PASSADO` do `atualizar`, o roteiro de avaliação e uma pergunta de
produto nova (vender durante o show). É uma feature boa que merece decisão própria e não pega carona
nesta.

**O turno encerrado continua na lista, com tag.** *Descartei* sumir com ele: `listar_escalados` é o
inventário de quem lê, não a vitrine de quem compra, e some-lo transformaria esta lista na quinta
cópia do corte público.

**`EstadoDoTurno` de três valores no lugar de `aberto: bool`.** *Descartei* acrescentar um
`encerrado: bool` ao lado do que existe: dois booleanos permitem quatro combinações e uma delas é
impossível (`aberto=True, encerrado=True`) — exatamente o antipadrão que o docstring do
`DisponibilidadeDoSetor` recusa por escrito. Um enum fechado não tem estado inválido para esquecer.

## 4 · Contrato

### Migração

`evento.data_hora_fim`, `TIMESTAMPTZ NOT NULL`, em três passos no mesmo `upgrade`: cria anulável,
preenche com `data_hora + interval '6 hours'`, aplica o `NOT NULL`. Mais o `CHECK
fim_depois_do_inicio` (`data_hora_fim > data_hora`).

O `downgrade` derruba a coluna e a constraint.

### Schemas

| Schema | Mudança |
|---|---|
| `EventoEntrada` | `data_hora_fim: DataComFuso`, obrigatório |
| `EventoEdicao` | `data_hora_fim: DataComFuso`, obrigatório |
| `EventoSaida` | `data_hora_fim: datetime` — é dele que o formulário de edição se preenche |
| `IngressoNaLista` | `situacao: SituacaoDoIngresso` |
| `IngressoDetalhe` | `situacao: SituacaoDoIngresso` |
| `TurnoDaPortaria` | `aberto: bool` **sai**; entra `estado: EstadoDoTurno` |

Os três schemas públicos (`EventoNaProgramacao`, `EventoEmDestaque`, `EventoPublico`) **não** ganham
nada: nenhuma tela pública lê o término, e campo sem consumidor não viaja — disciplina desde a 3.1.

```python
class SituacaoDoIngresso(str, Enum):
    ATIVO = "ATIVO"
    UTILIZADO = "UTILIZADO"
    EXPIRADO = "EXPIRADO"


class EstadoDoTurno(str, Enum):
    NAO_COMECOU = "NAO_COMECOU"
    ABERTO = "ABERTO"
    ENCERRADO = "ENCERRADO"
```

### Erros

| Código | HTTP | Onde |
|---|---|---|
| `FIM_ANTES_DO_INICIO` | 422 | `publicar` e `atualizar`, como **sexta** recusa — depois do `EVENTO_NO_PASSADO` |
| `EVENTO_ENCERRADO` | 403 | `exigir_porta_aberta`, **antes** do `EVENTO_NAO_ABERTO` |

Frase do primeiro: *"O show precisa terminar depois de começar. Confira o horário de término."*
Frase do segundo: *"Este evento já terminou."*

### Funções

```python
def evento_encerrado(evento: Evento, agora: datetime) -> bool:
    return evento.data_hora_fim <= agora

def porta_aberta(evento: Evento, agora: datetime) -> bool:
    return (
        evento.data_hora - ABERTURA_DOS_PORTOES <= agora
        and not evento_encerrado(evento, agora)
    )

def estado_do_turno(evento: Evento, agora: datetime) -> EstadoDoTurno: ...
def situacao_do_ingresso(usado_em, data_hora_fim, agora) -> SituacaoDoIngresso: ...
```

`situacao_do_ingresso` mora em `services/ingresso.py` e é chamada por `listar` e por
`_montar_detalhe`. **`usado_em` ganha de tudo:** ingresso utilizado num show que já acabou é
`UTILIZADO`, nunca `EXPIRADO` — a pessoa entrou.

## 5 · Critérios de pronto, por commit

### Commit 1 — `feat: hora de término do evento`

- [ ] Migração criada **e aplicada** com `uv run alembic upgrade head` no banco de desenvolvimento,
      conferida com `alembic current` contra `alembic heads` (ver *Pendências técnicas* do `CLAUDE.md`)
- [ ] Teste provando que um evento pré-existente ganhou `data_hora + 6h` — cria a linha com SQL antes
      do `upgrade`, ou confere o `data_hora_fim` de um evento semeado sem ele
- [ ] `data_hora_fim` obrigatório nos dois schemas de entrada, com fuso exigido pelo `DataComFuso`
- [ ] `FIM_ANTES_DO_INICIO` recusado nas duas rotas, com a **mesma frase**, e igual quando os dois
      instantes são idênticos
- [ ] O `CHECK` do banco provado por `INSERT` direto — é rede de segurança, não a regra
- [ ] Campo `Termina às` nos dois formulários; o de edição abre preenchido com o valor atual
- [ ] A virada de meia-noite conferida na tela: início 23h, término 02h → grava o dia seguinte
- [ ] `uv run pytest` inteiro verde (parte de 506), `npm run build` e `tsc --noEmit`

### Commit 2 — `feat: ingresso expira quando o show acaba`

- [ ] `situacao` nas duas respostas, derivada — **nenhuma coluna nova**
- [ ] Teste dos três valores, incluindo o que importa: ingresso **utilizado** de evento **encerrado**
      sai `UTILIZADO`
- [ ] Terceiro bloco *Expirados* em `/ingressos`, abaixo dos outros dois
- [ ] O canhoto de ingresso expirado diz que o evento acabou, e diz igual no link compartilhado
      (`/i/{token}`) — é o mesmo `_montar_detalhe`
- [ ] `uv run pytest`, `npm run build` e `tsc --noEmit`

### Commit 3 — `feat: o turno acaba quando o show acaba`

- [ ] `porta_aberta` com teto, e `TurnoDaPortaria.aberto` substituído por `estado`
- [ ] `403 EVENTO_ENCERRADO` na dependência, **antes** do `EVENTO_NAO_ABERTO`
- [ ] Teste provando que `usado_em` continua nulo depois do `403` — o mesmo teste barato que a 5.2
      usou para provar que a recusa acontece antes de qualquer consulta ao ingresso
- [ ] Os três estados na tela: `NAO_COMECOU` sem link com a frase atual, `ABERTO` com link e
      contador, `ENCERRADO` sem link com *"O evento acabou"*
- [ ] `README.md#o-que-não-está-pronto` ganha a linha do fechamento sem tolerância — **escrita neste
      commit**, que é a exceção do `CLAUDE.md`
- [ ] `uv run pytest`, `npm run build` e `tsc --noEmit`
- [ ] Comentário no `sprint-status.yaml`, bloco da Epic 5

## 6 · Armadilhas

⚠️ **`situacao` no frontend, nunca `estado`.** `lib/ingressos.ts` já usa `estado` como discriminante
do resultado da chamada (`{estado: "ok"} | {estado: "indisponivel"}`). Um `item.estado` ao lado de um
`resultado.estado` na mesma tela é a confusão pronta, e o `tsc` não acusa nada — os dois existem.

⚠️ **`usado_em` continua no contrato do ingresso, e não é redundância.** `situacao` é o **balde** que
a tela agrupa; `usado_em` é a **hora** que ela imprime em *"Entrou às 21h14"*. Derivar a situação de
`usado_em` na tela é o que esta spec desfaz — a regra é do backend, um lugar só.

⚠️ **`estado_do_turno` e `porta_aberta` não podem divergir.** A dependência recusa e a tela desenha:
se uma disser aberto e a outra encerrado, o item aparece clicável e a validação bate na porta. As
duas saem da **mesma** `evento_encerrado` — é o motivo inteiro de a 5.2 ter descido a regra do portão
para o service, e vale igual do outro lado.

⚠️ **Um relógio só para a lista inteira.** `listar_escalados` já lê `datetime.now()` uma vez para
todos os turnos; `listar` de ingressos passa a precisar do mesmo. Uma leitura por item faz dois
ingressos na mesma borda saírem com situações diferentes na mesma resposta.

⚠️ **A ordem das duas recusas da porta.** `EVENTO_ENCERRADO` vem **antes** do `EVENTO_NAO_ABERTO`.
Invertida, um evento que acabou responderia *"a porta ainda não abriu"* — e as duas condições são
simultaneamente verdadeiras para um evento futuro cujo término foi digitado errado.

⚠️ **A migração roda em três passos, não em um.** `add_column` com `nullable=False` direto estoura em
qualquer banco que já tenha linha de evento — e todos têm.

⚠️ **O `min` do `<input type="time">` não existe para relação entre dois campos.** A recusa de fim
antes do início é do service, e a tela só evita a ida à rede — mesmo desenho do `EVENTO_NO_PASSADO`,
que o formulário já confere e o service recusa de novo.

⚠️ **Editar evento continua recusando pelo início.** `atualizar` compara `evento.data_hora <= agora`
para dizer `EVENTO_NO_PASSADO`, e isso **não muda** nesta spec — mover para o término é o corte da
decisão D6, que ficou de fora de propósito.

---

**Fontes:** `backend/app/services/evento.py` (`ABERTURA_DOS_PORTOES`, `porta_aberta`,
`listar_escalados`) · `backend/app/services/ingresso.py` (`listar`, `_montar_detalhe`) ·
`backend/app/core/dependencias.py` (`exigir_porta_aberta`) ·
`frontend/src/app/(site)/ingressos/page.tsx` · `frontend/src/app/portaria/page.tsx` ·
`docs/techspec-validacao-na-porta.md` · `docs/techspec-editar-evento.md`
