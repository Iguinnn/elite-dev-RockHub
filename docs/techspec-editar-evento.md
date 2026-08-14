# Techspec — editar e excluir evento que ainda não vendeu

**Data:** 2026-08-13, com o commit 3 acrescentado em 2026-08-14 · **Cobre:** três commits `feat`
**fora da numeração das stories** · **Formato:** ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As Epics 1 a 5 estão fechadas e só a 6 (documentação) sobra, então isto não é story de epic
nenhuma — é o mesmo precedente do filtro de classificação do catálogo, que entrou como `feat`
avulso com spec própria. O `sprint-status.yaml` ganha duas linhas de comentário na Epic 2, que é
onde o assunto mora, e nenhuma linha de status nova.

Os commits viram um documento só porque a invariante é **a mesma dos três lados**: o backend recusa
editar e excluir evento que vendeu, e o frontend decide se mostra cada botão pela mesma leitura de
estoque. Especificar separado deixaria a fronteira — quem responde "não dá", e com que palavra —
caindo no vão entre os arquivos. **O commit 3 (excluir) entrou depois**, em 14/08/2026, e veio para
cá em vez de virar spec nova exatamente por isso: ele reusa a trava, o bloqueio e a colheita da rota
de editar, e a decisão dele mais pesada é uma **reversão** de uma decisão escrita na seção 3.

⚠️ **Isto reabre um corte que o README declara como consciente** (`README.md#o-que-não-está-pronto`,
linha do *Editar evento ou trocar a escala depois de publicar*). A troca é escolha minha, tomada em
13/08/2026, e o commit 2 apaga aquela linha da tabela — corte que deixou de ser corte não pode
continuar declarado como tal.

---

## 1 · Escopo e commits

Três commits, na ordem numerada. Cada um passa na suíte sozinho.

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para eu commitar** — sem escrever README, sem tocar no seguinte. Só emende o
próximo depois de eu mandar. Esta spec cobrir três commits **não** autoriza implementá-los de uma
vez: o histórico do git é parte da avaliação, e o commit por story é a única coisa que a spec
agrupada não pode custar.

| Commit | O que entrega |
|---|---|
| 1 | `PUT /organizador/eventos/{id}`, o schema `EventoEdicao`, `atualizar()` em `services/evento.py` e os testes em `test_organizador_eventos.py` |
| 2 | A tela `/organizador/eventos/{id}/editar`, o botão no detalhe, `atualizarMeuEvento` em `lib/eventos.ts` e a linha removida do README |
| 3 | `DELETE /organizador/eventos/{id}`, `excluir()` em `services/evento.py`, o `BotaoDeExclusao` no detalhe e os testes das duas pontas — **backend e frontend no mesmo commit** |

**O commit 3 junta as duas metades de propósito**, e é a única exceção ao formato dos dois de cima.
Ele é uma rota sem schema de entrada, uma função de service e um botão: partir isso em dois deixaria
o commit do backend entregando uma rota que nenhuma tela chama, e o da tela entregando trinta linhas.
Os critérios de pronto dele cobrem `pytest`, `npm run build` e `tsc --noEmit` juntos.

## 2 · O que existe hoje

`publicar()` (`services/evento.py:146`) grava evento, setores e escala **numa transação**, pelos
`relationship`, e carrega cinco recusas nomeadas: `EVENTO_SEM_SETOR`, `SETOR_DUPLICADO`,
`EVENTO_SEM_PORTARIA`, `PORTARIA_INVALIDA` e `EVENTO_NO_PASSADO`. Três delas valem igual na edição e
se copiam; nenhuma se reescreve.

`obter_do_organizador()` já devolve `EventoSaida` com `setores[].id`, `setores[].vendidos` e
`portarias[]` — ou seja, **a tela de edição já tem tudo o que precisa para montar o formulário**,
sem rota nova de leitura.

`expirar_vencidas(sessao, setor_ids)` (`services/reserva.py:206`) é a colheita preguiçosa do AD-4, e
o docstring dela é explícito: **roda na transação de quem chamou, sem `commit` próprio**. É o que
torna possível colher e decidir no mesmo `BEGIN`.

`setor.vendidos` sobe **na reserva**, não no pagamento (AD-3, `UPDATE` condicional em
`reserva.py:407`), e volta na expiração. Logo `vendidos == 0` significa "ninguém comprou e ninguém
está segurando".

No frontend: `obterMeuEvento`, a tela de detalhe (128 linhas, Server Component), o
`FormularioPublicacao` (777 linhas, client, `chamarApi`) e os componentes `Campo`, `SeletorDeData`,
`Botao` e `AvisoDeErro`.

O que **não** existe: nenhuma rota de escrita além do `POST`, nenhuma tela que edite coisa alguma, e
nenhum `ondelete` nas FKs `item_reserva.setor_id` e `ingresso.setor_id`.

**Para o commit 3, o que os commits 1 e 2 já deixaram pronto:** `atualizar()`
(`services/evento.py:292`) com o `SELECT ... FOR UPDATE` ordenado por `setor.id`, a chamada de
`expirar_vencidas` na mesma transação e a releitura de `vendidos` **por colunas**, fora do identity
map. A rota de excluir reusa esses quatro passos inteiros — mesma ordem, mesmos motivos. No
frontend, o `cabecalhoDoEvento` do detalhe já tem a anatomia "título de um lado, ação do outro" e a
frase que substitui o botão quando não dá, e o `chamarApi` (`lib/api.ts:40`) **já trata `204`**,
devolvendo `undefined` em vez de tentar ler um corpo que não existe.

**E o mapa de chaves estrangeiras que apontam para `evento`**, que é o que decide a rota inteira:
`setor.evento_id` (`models/evento.py:185`) e `evento_portaria.evento_id` (`models/evento.py:74`) têm
`ondelete="CASCADE"` e somem sozinhas. `reserva.evento_id` (`models/reserva.py:110`),
`ingresso.evento_id` (`models/ingresso.py:62`) e `validacao.evento_id` (`models/validacao.py:81`)
**não têm `ondelete` nenhum**: qualquer linha dessas em pé transforma o `DELETE` em `IntegrityError`
no `commit`, que vira `500 ERRO_INTERNO`. `item_reserva` é o caso feliz — o `reserva_id` dele tem
`ondelete="CASCADE"` (`models/reserva.py:197`), então ele cai junto com a reserva.

## 3 · Decisões, e o que descartei

**Edita-se o que se escolhe ao publicar: data/hora, setores e escala. Nada mais.** Desde 13/08/2026
o formulário de publicar manda `origem_externa_id`, `nome`, `imagem_url`, `local` e `cidade`
escondidos, copiados do catálogo (AD-1) — o organizador não digita nenhum dos cinco. *Descartei*
abrir `nome` e `imagem`: a tela de editar ficaria **mais poderosa que a de publicar**, e o evento
poderia virar outro show sem trocar de `origem_externa_id`. *Descartei também* o meio-termo com
`local` e `cidade` — a Ticketmaster erra "onde" com frequência, mas eu acabei de fechar esses dois
campos, e reabri-los aqui seria desfazer em um dia uma decisão de ontem por conveniência.

**A trava é `vendidos == 0` em todos os setores — depois de colher as vencidas.** *Descartei* travar
só com reserva `PAGA`: o preço já vai congelado na reserva, então não haveria prejuízo, mas alguém
digitando o cartão veria o preço mudar na tela no meio da compra. *Descartei* checar sem colher
antes: como a expiração é preguiçosa, um checkout abandonado seguraria a edição por até dez minutos,
e a tela diria "esse evento já vendeu" sobre um evento que não vendeu nada — mentira temporária que
o organizador não tem como distinguir da verdadeira.

**Remover setor que já teve reserva é recusado, com código próprio (`SETOR_COM_HISTORICO`).** Aqui
está a armadilha central desta feature: `item_reserva.setor_id` e `ingresso.setor_id` são FK **sem
`ondelete`** (`models/reserva.py:211`), e a linha de uma reserva `EXPIRADA` ou `RECUSADA` fica lá
para sempre. Essa reserva **passa** na trava acima, porque não é venda — e o `DELETE` do setor
estoura `IntegrityError` no `commit`, que sobe ao handler genérico e vira `500 ERRO_INTERNO`. É
exatamente a "pior resposta possível" que o `SETOR_DUPLICADO` existe para evitar, dois erros ao lado.
*Descartei* apagar as reservas mortas junto: destruir histórico que ninguém pediu para destruir, para
poupar uma mensagem. *Descartei* proibir remoção de qualquer setor: mataria o caso legítimo mais
comum, que é ter criado "Camarote" por engano e ninguém ter encostado nele.

**`PUT` com o corpo inteiro, e os setores casados por `id`.** *Descartei* `PATCH`: com lista de
filhos, "não mandei" e "removi" viram a mesma coisa no corpo, e a ambiguidade cai justo na operação
que pode apagar linha. *Descartei* casar por nome, ainda que `uq_setor_evento_id_nome` o permita:
renomear "Pista" para "Pista Premium" viraria remover um setor e criar outro — a operação que a
decisão acima recusa —, e o organizador levaria um erro por ter corrigido uma palavra.

**Schema próprio `EventoEdicao`, e não reuso do `EventoEntrada`.** Os cinco campos do catálogo não
entram, e `SetorEdicao` precisa de um `id` opcional que o de publicação não tem. *Descartei* reusar
com campos opcionais: o mesmo schema significando duas coisas diferentes é como uma rota passa a
aceitar corpo que ela não deveria aceitar — e aqui o corpo que ela não deveria aceitar é justamente
o que troca o nome do show.

**Formulário novo, e não generalização do `FormularioPublicacao`.** *Descartei* generalizar: são 777
linhas construídas em volta de "escolher no catálogo e publicar", já revisadas em code review, e
mexer nelas para economizar componentes que já são reusáveis (`Campo`, `SeletorDeData`, a lista de
portarias) é risco na tela mais crítica do organizador em troca de nada. O preço é duas telas
parecidas para manter, e ele é menor.

**O botão fica sempre visível no detalhe, com o impedimento escrito ao lado quando não dá.**
*Descartei* esconder o botão — quem viu ontem procura hoje —, e *descartei* botão que leva a uma tela
só para dizer não, que é um clique desperdiçado.

**Evento que já aconteceu não se edita**, e a nova data também não pode cair no passado — o
`EVENTO_NO_PASSADO` do `publicar` vale nas duas pontas. *Descartei* deixar editar o passado: seria
consertar a data de um show que já foi, e o único efeito seria ele reaparecer na programação pública.

### As decisões do commit 3 — excluir

**Excluir apaga o rastro morto junto com o evento, e isto reverte o que está escrito três parágrafos
acima.** Lá eu descartei "apagar as reservas mortas junto" para não destruir histórico que ninguém
pediu para destruir — e mantenho aquilo para a edição, porque lá o evento continua existindo e o
histórico continua tendo dono. Aqui o dono vai embora inteiro: uma reserva `EXPIRADA` de um evento
que não existe mais não é histórico, é linha órfã apontando para um nome que ninguém consegue ler.
*Descartei* recusar com um `EVENTO_COM_HISTORICO` simétrico ao do setor: seria beco sem saída — um
checkout abandonado uma vez travaria a exclusão para sempre, e ao contrário do setor, que dava para
renomear em vez de remover, o organizador não teria saída nenhuma. *Descartei também* o soft delete
com uma coluna `removido_em`: preserva tudo e é reversível, mas custa migração mais um filtro em
**toda** leitura do sistema — as quatro públicas, as três do organizador, reserva, ingresso, portaria
e o link compartilhado. Cada leitura esquecida é um evento fantasma vazando numa tela, e a três dias
do prazo eu prefiro a operação que apaga à que vaza em silêncio.

**A trava é a mesma da edição — `vendidos == 0` depois da colheita — e é a única.** *Descartei*
recusar também o show que já aconteceu, que é o que a edição faz: o motivo lá é específico e não
sobrevive à mudança de verbo. Editar a data de um show passado o faria reaparecer na programação
pública; excluí-lo não faz nada reaparecer, e é justamente o caso em que a exclusão é faxina. Recusar
prenderia todo evento antigo no `Meus eventos` para sempre, sem nenhum ganho.

**O `DELETE` das reservas filtra `estado != 'PAGA'` de propósito, mesmo sendo impossível encontrar
uma.** Ingresso só nasce de reserva paga, e `vendidos` **nunca** volta de uma paga — só a expiração
devolve estoque, e ela só toca `PENDENTE`. Então venda paga implica `vendidos > 0`, e a trava já
recusou. O filtro existe para o dia em que essa cadeia quebrar: sem ele, o bug vira "a exclusão
apagou uma venda"; com ele, a FK sem `ondelete` segura, a transação inteira volta e nada é destruído.
Trocar um `500` por um apagamento silencioso de venda seria o pior negócio desta feature — pelo mesmo
motivo, `ingresso` não é apagado em lugar nenhum desta rota.

**Confirmação em dois estágios no próprio botão**, sem modal: `Excluir` vira `Confirmar exclusão`,
com `Cancelar` ao lado. *Descartei* o `<dialog>` — não existe modal nenhum no projeto, e a primeira
sobreposição de tela do produto não vai nascer para uma operação de organizador. *Descartei* exigir
digitar o nome do evento: é a proteção certa para apagar conta ou banco, e desproporcional para um
evento sem venda nenhuma, que o organizador republica em dois minutos.

**O botão fica ao lado do `Editar`, e a frase de impedimento passa a falar dos dois verbos.**
*Descartei* pôr o `Excluir` também na lista de `Meus eventos`: lá as linhas são próximas e o clique
errado é fácil, e a lista não mostra `vendidos` para justificar a ausência do botão numa linha e a
presença em outra. Uma frase só no lugar dos dois botões, e não duas quase iguais empilhadas.

## 4 · Contrato

### `PUT /organizador/eventos/{evento_id}` → `200` com `EventoSaida`

Mesma dependência de papel das irmãs: `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`. Sem
migração — nenhuma coluna nasce aqui.

```python
class SetorEdicao(BaseModel):
    # Ausente = setor novo. Presente = altera aquele setor, e ele precisa ser
    # deste evento (SETOR_DESCONHECIDO). O que não vier na lista é removido.
    id: UUID | None = None
    nome: TextoLimpo = Field(min_length=1, max_length=80)
    capacidade: int = Field(ge=1, le=_MAXIMO_INT4)
    preco_centavos: int = Field(ge=0, le=_MAXIMO_PRECO_CENTAVOS)


class EventoEdicao(BaseModel):
    data_hora: datetime
    setores: list[SetorEdicao] = Field(default_factory=list, max_length=20)
    portaria_ids: list[UUID] = Field(default_factory=list, max_length=20)
```

**A ordem dentro da transação, e ela é a especificação:**

1. Carrega o evento com o mesmo `404` de `obter_do_organizador` — byte a byte o mesmo para "não
   existe" e "não é seu".
2. `SELECT … FROM setor WHERE evento_id = :id ORDER BY setor.id FOR UPDATE`. **Isto não é
   otimização, é a correção**: sem o bloqueio, entre ler `vendidos == 0` e gravar cabe uma reserva
   inteira. O `ORDER BY setor.id` segue a disciplina de ordem já escrita em `_devolver_estoque` —
   travar em ordens cruzadas é como se ganha um `40P01`.
3. `expirar_vencidas(sessao, [ids dos setores])`, na mesma transação.
4. Relê `vendidos` das linhas travadas. Se qualquer um for `> 0` → `409 EVENTO_COM_VENDA`.
5. As recusas copiadas do `publicar`, **nesta ordem**: lista vazia → `EVENTO_SEM_SETOR`; nome
   repetido por `casefold()` → `SETOR_DUPLICADO`; escala vazia → `EVENTO_SEM_PORTARIA`; id que não
   resolve para conta de portaria → `PORTARIA_INVALIDA`; `data_hora <= agora` → `EVENTO_NO_PASSADO`.
6. `id` de setor que não é deste evento → `422 SETOR_DESCONHECIDO`.
7. Para cada setor que sumiu da lista: se existe `item_reserva` ou `ingresso` apontando para ele →
   `422 SETOR_COM_HISTORICO`, com o nome do setor na mensagem. Senão, remove.
8. Aplica as alterações e o `commit`, devolvendo `EventoSaida`.

| Código | HTTP | Quando |
|---|---|---|
| `EVENTO_NAO_ENCONTRADO` | 404 | Não existe, ou não é do organizador da sessão |
| `EVENTO_COM_VENDA` | 409 | Algum setor com `vendidos > 0` depois da colheita |
| `SETOR_COM_HISTORICO` | 422 | Removeria setor que alguma reserva ou ingresso referencia |
| `SETOR_DESCONHECIDO` | 422 | `id` de setor que não pertence a este evento |
| `EVENTO_SEM_SETOR` · `SETOR_DUPLICADO` · `EVENTO_SEM_PORTARIA` · `PORTARIA_INVALIDA` · `EVENTO_NO_PASSADO` | 422 | Idênticos aos do `publicar` |

### `DELETE /organizador/eventos/{evento_id}` → `204` sem corpo

Mesma dependência de papel das irmãs. Sem corpo de entrada, sem migração, sem schema novo.
`204` e não `200` com o evento apagado: não há consumidor para o corpo, e o `chamarApi` já devolve
`undefined` nesse status desde a Story 3.8.

**A ordem dentro da transação — os passos 1 a 4 são os mesmos do `PUT`, e é essa igualdade que faz as
duas rotas nunca discordarem sobre "vendeu":**

1. `obter_do_organizador` — o mesmo `404`, pela mesma função.
2. `SELECT … FROM setor WHERE evento_id = :id ORDER BY setor.id FOR UPDATE`, com
   `populate_existing=True`. Mesmo motivo: entre ler `vendidos == 0` e apagar cabe uma reserva
   inteira, e aqui o estrago é maior — a reserva ficaria apontando para um evento que sumiu.
3. `expirar_vencidas(sessao, ids)`, na mesma transação.
4. Relê `vendidos` **por colunas**. Qualquer um `> 0` → `409 EVENTO_COM_VENDA`.
5. `DELETE FROM validacao WHERE evento_id = :id` — a tentativa frustrada na porta é gravada mesmo
   sem resolver para ingresso (`services/ingresso.py:442`), então ela existe em evento sem venda.
6. `DELETE FROM reserva WHERE evento_id = :id AND estado != 'PAGA'`. `item_reserva` cai junto pelo
   `ondelete="CASCADE"` do `reserva_id`, no banco.
7. `sessao.flush()` — **e ele não é opcional**. É o que garante que as linhas de `item_reserva` já
   sumiram quando o passo 8 mandar apagar os setores; sem ele, quem escolhe a ordem é o unit of work.
   Mesma lição da fase B do `atualizar`.
8. `sessao.delete(evento)` e `commit`. `setor` e `evento_portaria` caem pelo `ondelete="CASCADE"`.

**Não há passo que apague `ingresso`**, por decisão — ver a seção 3.

| Código | HTTP | Quando |
|---|---|---|
| `EVENTO_NAO_ENCONTRADO` | 404 | Não existe, ou não é do organizador da sessão |
| `EVENTO_COM_VENDA` | 409 | Algum setor com `vendidos > 0` depois da colheita |

**Nenhum código novo nasce aqui.** `EVENTO_COM_VENDA` é reusado com a frase trocada para o verbo —
"Este evento já vendeu ingressos e não pode mais ser excluído." O código é a parte estável do
contrato (`core/erros.py`) e é por ele que a tela decide; a frase é da resposta, e uma frase que diz
"editado" numa recusa de exclusão seria a tela mentindo sobre o que o organizador acabou de tentar.
`EVENTO_NO_PASSADO` **não aparece nesta rota** — é a decisão da seção 3.

### Frontend

`atualizarMeuEvento(id, corpo)` em `lib/eventos.ts`, no molde de `obterMeuEvento`. A tela
`/organizador/eventos/[id]/editar` é Server Component que busca com `obterMeuEvento` e entrega a um
`FormularioEdicao` client. Se o evento já vendeu, a tela não monta o formulário: mostra a frase e o
caminho de volta.

No detalhe, o botão `Editar` ao lado do `<h1>`; quando `setores.some(s => s.vendidos > 0)`, a frase
`Este evento já vendeu ingressos e não pode mais ser editado.` ocupa o lugar dele. Mensagens novas
entram no `mensagemParaCodigo`, uma por código da tabela acima.

**Excluir (commit 3):** `BotaoDeExclusao`, Client Component novo ao lado do `Editar` no
`cabecalhoDoEvento` — a tela de detalhe é Server Component e continua sendo. Ele chama o
`chamarApi` no caminho `/organizador/eventos/{id}` com `{ method: "DELETE" }` direto, como o
`FormularioEdicao` chama o `PUT`, e no sucesso faz `router.replace("/organizador/eventos")` seguido de
`router.refresh()`. **`replace` e não `push`**, pelo mesmo motivo do commit 2 elevado ao quadrado: o
botão voltar levaria ao detalhe de um evento que não existe mais, e o `refresh` é o que impede a
lista de vir do Router Cache ainda com a linha apagada dentro.

Os três estados do cabeçalho, e não há um quarto:

| Estado | O que aparece |
|---|---|
| Nem vendeu nem aconteceu | `Editar` e `Excluir`, lado a lado |
| Já aconteceu, não vendeu | A frase `Esse show já aconteceu e não pode mais ser editado.` **e o `Excluir`** — é a decisão da seção 3 vista da tela |
| Vendeu | Só a frase, agora `Este evento já vendeu ingressos e não pode mais ser editado nem excluído.` |

⚠️ **A frase do caso "vendeu" muda de texto no commit 3**, e é a mesma armadilha que o commit 2 já
corrigiu uma vez na frase da portaria: frase de tela que sobrevive ao fato que a justificava ensina a
pessoa a não procurar o que existe — ou, aqui, a procurar o que não existe.

No `BotaoDeExclusao`, `EVENTO_COM_VENDA` e `EVENTO_NAO_ENCONTRADO` têm frase própria; qualquer outro
código cai na genérica do projeto. Os dois acontecem de verdade sem ninguém trapacear — basta a aba
estar aberta desde antes de alguém reservar, ou desde antes de outra aba excluir o mesmo evento.

## 5 · Critérios de pronto, por commit

**Commit 1** — a rota existe e recusa o que tem de recusar:

- Editar evento sem venda troca data, setores e escala, e o `GET` seguinte devolve o novo estado.
- Setor com `id` é alterado; setor sem `id` é criado; setor ausente da lista é removido.
- Evento com reserva `PAGA` → `409 EVENTO_COM_VENDA`. Evento com reserva `PENDENTE` viva → o mesmo.
- **Evento com reserva `PENDENTE` vencida e não colhida → edita normalmente**, e o teste prova que o
  `vendidos` voltou a zero na mesma chamada.
- Remover setor que tem `item_reserva` de reserva `EXPIRADA` → `422 SETOR_COM_HISTORICO`, **não**
  `500`. Este é o teste que justifica a spec inteira.
- Evento de outro organizador → `404`, com corpo idêntico ao de evento inexistente.
- As cinco recusas copiadas do `publicar`, uma asserção cada.
- Suíte inteira verde.

**Commit 2** — a tela existe e não oferece o que não dá:

- Botão no detalhe leva a `/organizador/eventos/{id}/editar` com os campos preenchidos.
- Evento vendido: sem botão de editar no detalhe, com a frase no lugar; e a URL da edição digitada à
  mão mostra a mesma frase, sem formulário.
- Cada código de erro da tabela tem frase própria — nenhum cai na genérica.
- `npm run build` e `tsc --noEmit` limpos, e `/organizador/eventos/[id]/editar` sai como `ƒ`.
- A linha do *Editar evento* sai de `README.md#o-que-não-está-pronto`.

**Commit 3** — a exclusão apaga o que tem de apagar e nada além disso:

- Excluir evento sem venda devolve `204`, e o `GET` seguinte devolve `404`.
- O evento sai de `Meus eventos` e das rotas públicas, e os setores e a escala somem com ele — nada
  de linha órfã em `setor` nem em `evento_portaria`.
- **Evento com reserva `EXPIRADA` é excluído normalmente, e a reserva e os `item_reserva` dela somem
  junto — `204`, não `500`.** Este é o teste que justifica o commit inteiro; é a armadilha do
  `SETOR_COM_HISTORICO` um nível acima, e a única forma de errar aqui é testar só com evento limpo.
- Evento com `validacao` de tentativa frustrada (`ingresso_id` NULL) é excluído normalmente.
- Evento com reserva `PENDENTE` viva → `409 EVENTO_COM_VENDA`; evento com reserva `PAGA` → o mesmo,
  e um teste prova que **a reserva paga continua no banco** depois da recusa.
- **Evento com reserva `PENDENTE` vencida e não colhida → exclui normalmente**, pela colheita do
  passo 3.
- **Evento que já aconteceu e não vendeu → exclui normalmente**, e o teste diz no nome que isso é
  intencional e diferente do `PUT`.
- Evento de outro organizador → `404`, corpo idêntico ao de evento inexistente. Excluir duas vezes →
  `404` na segunda.
- Na tela: `Excluir` pede confirmação antes de chamar a API, o `Cancelar` volta ao estado inicial, e
  o sucesso cai em `Meus eventos` já sem a linha. Evento vendido não mostra botão nenhum; evento
  passado sem venda mostra o `Excluir` e não o `Editar`.
- `pytest` inteiro verde, `npm run build` e `tsc --noEmit` limpos — os três no mesmo commit.
- 🚩 **README: não escreva nada.** A pendência está registrada no fim desta spec e entra na Epic 6.

## 6 · Armadilhas

⚠️ **A FK sem `ondelete` é o `500` mais fácil desta feature.** Quem implementar vai testar com evento
limpo, e tudo passa. O caso que quebra é o evento cuja reserva expirou: ele passa na trava e morre no
`DELETE`. O passo 7 do contrato existe só por isso.

⚠️ **Sem o `FOR UPDATE` do passo 2, a rota tem uma corrida que nenhum teste sequencial pega.** Ler
`vendidos == 0` e gravar são dois momentos, e o `UPDATE` condicional do AD-3 cabe inteiro entre eles
— resultado: reserva paga apontando para um setor que acabou de mudar de preço, ou pior, que acabou
de ser apagado.

⚠️ **`vendidos` não se lê para dentro do Python para decidir escrita** (AD-3) — aqui ele é lido
porque as linhas estão **travadas**, e é isso que torna a leitura confiável. Fora de um `FOR UPDATE`,
essa leitura seria exatamente o antipadrão que o AD-3 proíbe.

⚠️ **`expirar_vencidas` não commita, e não deve passar a commitar.** Se alguém "consertar" isso, a
trava passa a decidir sobre um estado que outra transação ainda pode mudar.

⚠️ **A fixture `sessao` do `conftest.py` precisa imitar produção** (`expire_on_commit`) — é a lição
escrita no docstring dela desde o code review da Epic 3, e esta rota devolve objeto depois do
`commit`, que é a forma exata do bug daquela vez.

⚠️ **`data_hora` chega em UTC** (AD-11). O formulário monta a partir de data e hora locais, como o de
publicar já faz — copie o `instante.toISOString()` de lá, não reinvente a conversão.

### Do commit 3

⚠️ **Três FKs apontam para `evento` sem `ondelete`, e só duas delas são óbvias.** `reserva` e
`ingresso` qualquer um lembra; `validacao` é a que passa batido, porque ela nasce na porta e ninguém
associa "portaria" a "excluir evento". Ela é gravada **mesmo quando o código não resolve para
ingresso nenhum**, então existe em evento que nunca vendeu nada — que é exatamente o único evento que
esta rota consegue apagar. Esquecer o passo 5 dá um `500` que só aparece depois de alguém ter
apontado a câmera para um QR errado.

⚠️ **O `flush` do passo 7 é a mesma pegadinha da fase B do `atualizar`, e já custou um teste lá.**
Sem ele, o `DELETE` das reservas e o dos setores ficam os dois pendentes até o `commit`, e o unit of
work escolhe a ordem — se ele apagar o setor primeiro, o `item_reserva` ainda vivo segura a FK e a
transação inteira morre.

⚠️ **Nada de `passive_deletes` ou de mexer no `cascade` dos `relationship` para "ajudar".** O
`cascade="all, delete-orphan"` de `evento.setores` é o mesmo que a fase B do `atualizar` usa para
remover um setor, e afrouxá-lo aqui reabriria lá o caminho de um setor virar órfão em vez de
apagado.

⚠️ **A tela de detalhe é Server Component e continua sendo.** O botão é que é cliente. Marcar a
página inteira com `"use client"` para acomodar um `useState` de confirmação jogaria fora as duas
guardas de sessão que rodam no servidor — é o oposto do que o `FormularioEdicao` fez.

---

## 🚩 Pendência da Epic 6 — a linha do README

Não escrita de propósito (decisão do Igor em 14/08/2026: a Epic 6 passa nos três READMEs de uma vez).
A linha para a tabela `README.md#o-que-não-está-pronto`, pronta para colar:

> | **Excluir evento depois de ele ter vendido** | Excluir existe desde 14/08/2026, com a mesma trava da edição: só enquanto `vendidos == 0` em **todos** os setores. Vendeu uma vez, o evento fica para sempre — e é o que eu quero, porque a alternativa seria apagar reserva paga e ingresso emitido para limpar a tela de um organizador. Show que já aconteceu, esse **pode** ser excluído: ao contrário da edição, apagar um evento antigo não faz nada reaparecer na programação. O que a exclusão apaga junto são as reservas **não pagas** do evento, seus itens e as validações — histórico de um evento que deixou de existir é linha órfã, não histórico |

E o que **muda numa linha que já está lá**: a do *Cancelamento pelo cliente* segue verdadeira, mas a
do *Editar evento depois de ele ter vendido* agora tem uma irmã — vale citar uma na outra para quem
lê a tabela não achar que são a mesma regra escrita duas vezes.
