# Techspec — editar evento que ainda não vendeu

**Data:** 2026-08-13 · **Cobre:** dois commits `feat` **fora da numeração das stories**
**Formato:** ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As Epics 1 a 5 estão fechadas e só a 6 (documentação) sobra, então isto não é story de epic
nenhuma — é o mesmo precedente do filtro de classificação do catálogo, que entrou como `feat`
avulso com spec própria. O `sprint-status.yaml` ganha duas linhas de comentário na Epic 2, que é
onde o assunto mora, e nenhuma linha de status nova.

Os dois commits viram um documento só porque a invariante é **a mesma dos dois lados**: o backend
recusa editar evento que vendeu, e o frontend decide se mostra o botão pela mesma leitura de
estoque. Especificar separado deixaria a fronteira — quem responde "não dá", e com que palavra —
caindo no vão entre os dois arquivos.

⚠️ **Isto reabre um corte que o README declara como consciente** (`README.md#o-que-não-está-pronto`,
linha do *Editar evento ou trocar a escala depois de publicar*). A troca é escolha minha, tomada em
13/08/2026, e o commit 2 apaga aquela linha da tabela — corte que deixou de ser corte não pode
continuar declarado como tal.

---

## 1 · Escopo e commits

Dois commits, na ordem numerada. Cada um passa na suíte sozinho.

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para eu commitar** — sem escrever README, sem tocar no seguinte. Só emende o
próximo depois de eu mandar. Esta spec cobrir dois commits **não** autoriza implementá-los de uma
vez: o histórico do git é parte da avaliação, e o commit por story é a única coisa que a spec
agrupada não pode custar.

| Commit | O que entrega |
|---|---|
| 1 | `PUT /organizador/eventos/{id}`, o schema `EventoEdicao`, `atualizar()` em `services/evento.py` e os testes em `test_organizador_eventos.py` |
| 2 | A tela `/organizador/eventos/{id}/editar`, o botão no detalhe, `atualizarMeuEvento` em `lib/eventos.ts` e a linha removida do README |

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

### Frontend

`atualizarMeuEvento(id, corpo)` em `lib/eventos.ts`, no molde de `obterMeuEvento`. A tela
`/organizador/eventos/[id]/editar` é Server Component que busca com `obterMeuEvento` e entrega a um
`FormularioEdicao` client. Se o evento já vendeu, a tela não monta o formulário: mostra a frase e o
caminho de volta.

No detalhe, o botão `Editar` ao lado do `<h1>`; quando `setores.some(s => s.vendidos > 0)`, a frase
`Este evento já vendeu ingressos e não pode mais ser editado.` ocupa o lugar dele. Mensagens novas
entram no `mensagemParaCodigo`, uma por código da tabela acima.

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
