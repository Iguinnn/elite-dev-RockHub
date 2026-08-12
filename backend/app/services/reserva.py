"""Reservar ingressos: a regra, a transação e o `UPDATE` condicional do AD-3.

Segue a mesma convenção de transação do `services/evento.py` e do
`services/autenticacao.py` (`ARCHITECTURE-SPINE.md#Convenções`): **service que
escreve abre e fecha a transação.** O `commit` é daqui; `obter_sessao()` não
abre transação nenhuma e o router (`app/api/cliente.py`) nunca confirma nada.

**A garantia que este módulo existe para dar** é a do AD-3: duas pessoas
comprando o último ingresso no mesmo instante, e exatamente uma levando. Ela
mora num único statement por item —

```sql
UPDATE setor SET vendidos = vendidos + :q
 WHERE id = :id AND vendidos + :q <= capacidade
```

— e a decisão é o `rowcount`. ⚠️ **`setor.vendidos` nunca é lido para dentro do
Python**: nem para conferir antes, nem para logar, nem para montar mensagem de
erro. `if setor.vendidos + q > setor.capacidade` é uma linha confortável que
passa em todo teste sequencial e perde a corrida — a implementação errada com o
resultado certo em 99% dos casos, que é exatamente o que o desafio avalia. Não
há `SELECT ... FOR UPDATE` em lugar nenhum tampouco: o bloqueio de linha do
`UPDATE` já serializa as duas tentativas, e o `SELECT` explícito seria um
segundo mecanismo para a mesma garantia.

**A ordem das recusas é a garantia do "nada gravado pela metade".** Elas
acontecem antes de qualquer escrita, e as três primeiras nem sequer tocam o
banco:

```
1. itens vazio (ou ausente)                → RESERVA_SEM_ITEM   422
2. o mesmo setor duas vezes no corpo       → ITEM_DUPLICADO     422
3. soma das quantidades > MAXIMO_POR_COMPRA→ ACIMA_DO_MAXIMO…   422
   ── só então o evento é lido: fora de cartaz → EVENTO_NAO_ENCONTRADO 404 ──
4. setor_id que não é setor deste evento   → SETOR_INVALIDO     422
   ── e só então: o UPDATE do AD-3, e depois o INSERT ──
```

As três primeiras vêm antes da consulta do evento porque só dependem do corpo:
um pedido de sete ingressos é malformado com ou sem show em cartaz, e recusá-lo
sem ir ao banco é a mesma economia que a Story 2.4 fez com os setores. A quarta
depende do evento, porque é dele que os setores saem.

**O `ITEM_DUPLICADO` existe pelo mesmo motivo do `SETOR_DUPLICADO` da 2.4**: sem
ele, `uq_item_reserva_reserva_id_setor_id` estouraria como `IntegrityError` no
`commit`, subiria até o handler genérico e viraria `500` — erro de cliente
virando "erro interno do servidor".

**Não há `try/except IntegrityError` aqui**, pelo mesmo argumento escrito no
topo de `services/evento.py`: as violações possíveis vêm do próprio corpo, num
instante só, e as quatro recusas já as pegam na memória. Um `except` genérico
neste ponto só transformaria bug de verdade em `422` bonito.
"""

from collections.abc import Collection
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroDeDominio
from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import Usuario
from app.schemas.reserva import ItemDaReservaSaida, ReservaEntrada, ReservaSaida

# ⚠️ **Importado, nunca redeclarado** (decisão registrada na Story 3.4). O
# docstring do `EventoPublico` diz, com todas as letras, que esta story cobraria
# do servidor o mesmo teto que o stepper já lê do contrato: com o número em dois
# lugares, o dia em que a regra mudar é o dia em que a tela e a rota discordam —
# e quem descobre isso é a pessoa que escolheu 8 ingressos e recebeu uma recusa.
from app.services.evento import MAXIMO_POR_COMPRA

# Os dez minutos do AD-4 (decisão do Igor).
#
# **Constante do service, e não coluna nem variável de ambiente.** É o irmão do
# `MAXIMO_POR_COMPRA` logo acima: regra de produto que vale igual para toda
# reserva, num lugar só, trocável com uma linha e um teste. A alternativa —
# variável de ambiente, para o avaliador baixar o prazo e ver a expiração
# acontecer — custaria uma entrada no `.env.example`, no README, no `Settings` e
# na Railway para um cenário de demonstração, e a expiração da Story 3.7 é
# provada por teste, que é onde ela precisa ser verdade.
PRAZO_DE_RESERVA_MINUTOS = 10


def expirar_vencidas(sessao: Session, setor_ids: Collection[UUID]) -> None:
    """Devolve ao estoque o que reservas vencidas ainda seguram nestes setores.

    **A colheita preguiçosa do AD-4**, e a razão de não existir worker nem cron
    neste projeto: quem colhe é quem precisa do estoque, no instante em que
    precisa. A folga que isso deixa — uma reserva vencida continuar contando até
    alguém pedir aquele setor — é inofensiva por construção, porque no momento em
    que o estoque importa ele já está correto.

    **Só os setores do pedido** (decisão do Igor), e é para este `where` que a
    Story 3.5 indexou `item_reserva.setor_id`. Varrer o evento inteiro ou o banco
    inteiro faria trabalho sobre itens que ninguém pediu.

    **Roda na transação de quem chamou**, sem `commit` próprio: a convenção do
    projeto é que o service de escrita abre e fecha a transação, e aqui quem abre
    é o `criar()` (e, do commit 2 em diante, o pagamento). Se a reserva nova
    terminar em `409`, esta colheita é desfeita junto e refeita na próxima
    tentativa — desperdício sem consequência.

    ⚠️ **A ordem das duas escritas é a garantia de não devolver duas vezes.**
    Primeiro a transição condicionada ao estado anterior (AD-4); só quem a
    *vence* (`rowcount == 1`) ganha o direito de devolver o estoque. Duas
    conexões colhendo a mesma reserva no mesmo instante fazem exatamente uma
    passar pelo `if` — invertida, a ordem devolveria o estoque duas vezes e
    marcaria `EXPIRADA` uma só.

    ⚠️ **Devolve todos os itens da reserva, não só os dos setores pedidos.** A
    reserva expira inteira: deixar de lado os itens de outro setor a marcaria
    `EXPIRADA` com estoque preso para sempre, e nada voltaria a colher aquilo —
    a transição já teria acontecido.
    """
    if not setor_ids:
        return

    # `func.now()` e não o relógio do Python: `expira_em` é TIMESTAMPTZ em UTC
    # (AD-11) justamente para esta comparação acontecer dentro do Postgres, sem
    # conversão de fuso pelo caminho. É o que o modelo da 3.5 já anunciava.
    ids_vencidas = sessao.scalars(
        select(Reserva.id)
        .join(ItemReserva, ItemReserva.reserva_id == Reserva.id)
        .where(
            ItemReserva.setor_id.in_(setor_ids),
            Reserva.estado == EstadoReserva.PENDENTE.value,
            Reserva.expira_em < func.now(),
        )
        # Uma reserva com dois itens nos setores pedidos apareceria duas vezes.
        .distinct()
    ).all()

    for reserva_id in ids_vencidas:
        transicao = sessao.execute(
            update(Reserva)
            .where(
                Reserva.id == reserva_id,
                # Condicionada ao estado anterior, sempre (AD-4). Zero linhas
                # aqui não é erro: é "alguém chegou primeiro".
                Reserva.estado == EstadoReserva.PENDENTE.value,
            )
            .values(estado=EstadoReserva.EXPIRADA.value)
            .execution_options(synchronize_session=False)
        )

        if transicao.rowcount == 0:
            continue

        itens = sessao.scalars(
            select(ItemReserva).where(ItemReserva.reserva_id == reserva_id)
        ).all()

        for item in itens:
            sessao.execute(
                update(Setor)
                .where(
                    Setor.id == item.setor_id,
                    # ⚠️ Condicional também na devolução — o AD-3 vale para
                    # **toda** escrita em estoque, não só para a que consome.
                    # `vendidos - quantidade` calculado em Python parece seguro
                    # porque "devolver nunca estoura", e é a mesma quebra com o
                    # resultado certo em 99% dos casos.
                    Setor.vendidos >= item.quantidade,
                )
                .values(vendidos=Setor.vendidos - item.quantidade)
                .execution_options(synchronize_session=False)
            )


def criar(sessao: Session, cliente: Usuario, dados: ReservaEntrada) -> ReservaSaida:
    """Consome o estoque e grava a reserva `PENDENTE`, na mesma transação.

    `cliente` vem da dependência de papel, ou seja, **da sessão**. Não há
    parâmetro por onde um `cliente_id` do corpo pudesse entrar: reservar em nome
    de outra pessoa não é uma chamada que este service recusa, é uma chamada que
    não existe. Mesma assinatura de `publicar()` e `listar_do_organizador()`.

    ⚠️ **O `409` sobe como `ErroDeDominio` de dentro da transação**, e é o
    handler do `main.py` que responde. Como não houve `commit`, os `UPDATE` já
    aplicados desaparecem: a exceção atravessa o gerador de `obter_sessao`, cujo
    `finally: sessao.close()` (`app/core/db.py`) descarta o trabalho não
    confirmado. É o "tudo ou nada" — um pedido de 2 na Pista (que tem) e 5 no
    Camarote (que não tem) não pode deixar a Pista com 2 vendidos e a pessoa sem
    reserva. E é por isso que **não** cabe um `sessao.rollback()` explícito aqui:
    ele seria um segundo dono da mesma garantia.
    """
    if not dados.itens:
        raise ErroDeDominio(
            "RESERVA_SEM_ITEM",
            "Escolha ao menos um ingresso para reservar.",
            status_http=422,
        )

    vistos: set[UUID] = set()
    for item in dados.itens:
        if item.setor_id in vistos:
            raise ErroDeDominio(
                "ITEM_DUPLICADO",
                "Há mais de um item para o mesmo setor. "
                "Junte as quantidades num item só.",
                status_http=422,
            )
        vistos.add(item.setor_id)

    # O teto é da **compra**, não do item: 4 na Pista e 3 no Camarote são sete
    # ingressos, e o `Field(ge=1)` do schema não tem como saber disso.
    if sum(item.quantidade for item in dados.itens) > MAXIMO_POR_COMPRA:
        raise ErroDeDominio(
            "ACIMA_DO_MAXIMO_POR_COMPRA",
            f"São até {MAXIMO_POR_COMPRA} ingressos por compra.",
            status_http=422,
        )

    # Lido **uma vez**, e usado nos dois lugares que precisam do relógio — o
    # recorte de "em cartaz" e o `expira_em`. Mesma disciplina da
    # `listar_programacao` e do `obter_publico`: duas leituras na mesma
    # requisição podem discordar sobre o evento que começa agora.
    agora = datetime.now(timezone.utc)

    # **O mesmo recorte das quatro rotas públicas**, no mesmo `where` e na mesma
    # ordem: publicado e ainda por acontecer. Não é zelo — sem a condição de
    # data, o link guardado de um show de ontem venderia ingresso para uma noite
    # que já passou, e o evento nem apareceria na programação para a pessoa
    # descobrir o engano.
    evento = sessao.scalars(
        select(Evento)
        .where(
            Evento.id == dados.evento_id,
            Evento.publicado_em.is_not(None),
            Evento.data_hora >= agora,
        )
        # Uma consulta a mais para os setores, e não uma por setor: sem ele, ler
        # `evento.setores` abaixo emitiria o `SELECT` preguiçoso no meio da
        # montagem do pedido.
        .options(selectinload(Evento.setores))
    ).first()

    if evento is None:
        # A **mesma** mensagem do `GET /eventos/{id}`, e pelo mesmo motivo: id
        # inexistente, rascunho e data passada são um caso só para quem chama.
        raise ErroDeDominio(
            "EVENTO_NAO_ENCONTRADO",
            "Esse show não está em cartaz.",
            status_http=404,
        )

    # Os setores saem de `evento.setores`, e **não** de um `select(Setor)`
    # próprio: assim "o setor é deste evento" é verdade por construção, e não uma
    # segunda condição que alguém esquece na próxima rota.
    setores_por_id = {setor.id: setor for setor in evento.setores}

    # Um código e uma mensagem para os dois casos — id que não é setor nenhum, e
    # setor que é de outro evento. Distinguir transformaria a rota num oráculo, e
    # é a mesma disciplina do `PORTARIA_INVALIDA` da 2.5.
    if any(item.setor_id not in setores_por_id for item in dados.itens):
        raise ErroDeDominio(
            "SETOR_INVALIDO",
            "Algum dos setores escolhidos não existe neste show.",
            status_http=422,
        )

    # A colheita do AD-4, **antes** dos `UPDATE` de estoque e **depois** de os
    # setores estarem validados: colher com um `setor_id` que não é deste evento
    # seria varrer o índice à toa. É este ponto que o AC2 da Story 3.7 descreve —
    # "as vencidas são liberadas antes da tentativa e o estoque reflete a
    # realidade".
    expirar_vencidas(sessao, vistos)

    # ⚠️ **De cada setor lê-se `preco_centavos`, e mais nada.** `vendidos` e
    # `capacidade` não entram no Python — esta é a linha que a próxima pessoa vai
    # querer acrescentar "só para conferir antes de gastar um UPDATE", e é
    # exatamente ela que o AD-3 proíbe. Preço não é estoque: ler preço para
    # congelá-lo é o que o AC10 pede.
    precos = {
        item.setor_id: setores_por_id[item.setor_id].preco_centavos
        for item in dados.itens
    }

    for item in dados.itens:
        resultado = sessao.execute(
            update(Setor)
            .where(
                Setor.id == item.setor_id,
                # A condição mora aqui, e não num `if` acima: é o Postgres que
                # bloqueia a linha e **reavalia este `WHERE` contra a versão
                # nova** ao liberá-la (READ COMMITTED). É isso, e só isso, que
                # faz duas tentativas simultâneas terminarem com uma vencedora.
                Setor.vendidos + item.quantidade <= Setor.capacidade,
            )
            # ⚠️ **Expressão SQL, e não um número calculado em Python.**
            # `setor.vendidos + item.quantidade` mandaria um literal para o
            # banco, passaria em todo teste sequencial e perderia a corrida. A
            # diferença é uma maiúscula: a **coluna**, nunca o atributo do
            # objeto.
            .values(vendidos=Setor.vendidos + item.quantidade)
            # ⚠️ **De propósito.** Os `Setor` estão na sessão (vieram do
            # `selectinload`), e a sincronização padrão tentaria reconciliar a
            # coluna nos objetos carregados — trabalho para produzir justamente o
            # valor que o AD-3 proíbe usar. Nada neste service o lê depois.
            .execution_options(synchronize_session=False)
        )

        # Zero linhas afetadas é "não cabe", e é a **única** fonte dessa
        # resposta. A mensagem melhor — qual setor esgotou, o que ainda sobrou —
        # é montada pela tela, com dados frescos, depois deste `409` (UX-DR8).
        if resultado.rowcount == 0:
            raise ErroDeDominio(
                "ESTOQUE_INSUFICIENTE",
                "Não há ingressos suficientes para essa escolha.",
                status_http=409,
            )

    # O `INSERT` **depois** dos `UPDATE`, na ordem do diagrama de sequência da
    # espinha. Os itens vão pelo `relationship`, sem `add` separado e sem
    # `flush` intermediário para descobrir o id do pai — como `publicar()` grava
    # os setores.
    reserva = Reserva(
        # Da sessão, sempre.
        cliente_id=cliente.id,
        evento_id=evento.id,
        # `.value` porque a coluna é `String(20)` + `CHECK` (Story 3.5), nunca um
        # `ENUM` nativo.
        estado=EstadoReserva.PENDENTE.value,
        expira_em=agora + timedelta(minutes=PRAZO_DE_RESERVA_MINUTOS),
        total_centavos=sum(
            precos[item.setor_id] * item.quantidade for item in dados.itens
        ),
        itens=[
            ItemReserva(
                setor_id=item.setor_id,
                quantidade=item.quantidade,
                # Congelado aqui: o organizador pode mudar o preço do setor
                # amanhã, e a reserva tem que continuar dizendo quanto custou.
                preco_unitario_centavos=precos[item.setor_id],
            )
            for item in dados.itens
        ],
    )

    sessao.add(reserva)
    sessao.commit()

    return _para_saida(reserva, evento)


def obter(sessao: Session, cliente: Usuario, reserva_id: UUID) -> ReservaSaida:
    """A reserva de quem está na sessão — a tela `/reservas/{id}`.

    **As duas condições no mesmo `where`, e não um `get()` seguido de um `if`.**
    Mesmo motivo escrito no `obter_do_organizador` da 2.6: com `id` e
    `cliente_id` juntos, "só vejo o que é meu" é verdade por construção, não por
    disciplina de quem escrever a próxima rota.

    **Um `404` só para "não existe" e para "não é seu"** — nunca `403`.
    Distinguir os dois transformaria a rota num oráculo ("esse UUID é reserva de
    alguém?"), e para quem chama os dois casos significam a mesma coisa.

    **O evento é lido sem o recorte de "em cartaz"**, ao contrário do `criar`: a
    reserva de um show que já aconteceu continua sendo uma reserva, e a tela
    precisa saber de que show ela era. O recorte é sobre o que se pode
    **comprar**, não sobre o que se pode **ver do que já foi comprado**.
    """
    reserva = sessao.scalars(
        select(Reserva)
        .where(Reserva.id == reserva_id, Reserva.cliente_id == cliente.id)
        .options(selectinload(Reserva.itens))
    ).first()

    if reserva is None:
        raise ErroDeDominio(
            "RESERVA_NAO_ENCONTRADA",
            "Essa reserva não existe ou não é sua.",
            status_http=404,
        )

    evento = sessao.get(
        Evento, reserva.evento_id, options=[selectinload(Evento.setores)]
    )
    # Impossível pelo banco: `reserva.evento_id` é FK sem `ondelete`, e apagar um
    # evento com reserva é recusado pelo Postgres (Story 3.5). O `assert` diria a
    # mesma coisa e sumiria com `-O`.
    if evento is None:  # pragma: no cover
        raise ErroDeDominio(
            "RESERVA_NAO_ENCONTRADA",
            "Essa reserva não existe ou não é sua.",
            status_http=404,
        )

    return _para_saida(reserva, evento)


def _para_saida(reserva: Reserva, evento: Evento) -> ReservaSaida:
    """Monta o contrato de saída das duas rotas.

    Existe porque três campos da resposta **não** são atributos de `Reserva` nem
    de `ItemReserva`: o nome do show, a data dele e o nome de cada setor. O
    modelo da 3.5 não tem `relationship` para `Evento` nem para `Setor`, e não
    deve ter — um `ItemReserva.setor` convidaria a próxima pessoa a derivar
    disponibilidade de `item_reserva`, que é o que o AD-13 proíbe.

    ⚠️ **O preço vem do item, nunca do setor.** O `Setor` entra aqui para dar
    **só o nome**: o valor cobrado é o congelado em
    `item_reserva.preco_unitario_centavos`, e é ele que continua batendo com o
    total depois de o organizador mudar a tabela de preços.

    ⚠️ **A ordem dos itens é a posição do setor em `evento.setores`, e não um
    `sorted()` pelo nome em Python.** As duas parecem a mesma coisa e discordam
    no primeiro nome com acento: `sorted()` compara pontos de código e põe "Área
    VIP" **depois** de "Camarote", enquanto o `order_by="Setor.nome"` do
    `relationship` (Story 2.3) é ordenado pelo Postgres, na collation do banco,
    que a põe antes. Como o AC pede *a mesma ordem da página do evento*, a ordem
    tem que sair da **mesma fonte** que aquela tela usa — e sair dela por
    construção, não por coincidência de duas implementações. Foi um teste com um
    setor chamado "Área VIP" que revelou isso.
    """
    setores_por_id = {setor.id: setor for setor in evento.setores}
    posicao_do_setor = {setor.id: posicao for posicao, setor in enumerate(evento.setores)}

    return ReservaSaida(
        id=reserva.id,
        evento_id=evento.id,
        evento_nome=evento.nome,
        evento_data_hora=evento.data_hora,
        estado=EstadoReserva(reserva.estado),
        expira_em=reserva.expira_em,
        total_centavos=reserva.total_centavos,
        # Na ordem em que os setores aparecem na página do evento (ver o aviso
        # do docstring). O `relationship` de `Reserva.itens` não ordena de
        # propósito: lá não há coluna de ordem natural, e ordenar por `setor_id`
        # seria ordem de UUID — aleatória fingindo de determinística.
        itens=[
            ItemDaReservaSaida(
                setor_id=item.setor_id,
                setor_nome=setores_por_id[item.setor_id].nome,
                quantidade=item.quantidade,
                preco_unitario_centavos=item.preco_unitario_centavos,
            )
            for item in sorted(
                reserva.itens, key=lambda item: posicao_do_setor[item.setor_id]
            )
        ],
    )
