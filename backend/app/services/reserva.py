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

**Não há `try/except IntegrityError` na criação da reserva**, pelo mesmo
argumento escrito no topo de `services/evento.py`: as violações possíveis vêm do
próprio corpo, num instante só, e as quatro recusas já as pegam na memória. Um
`except` genérico neste ponto só transformaria bug de verdade em `422` bonito.

⚠️ **O único `except IntegrityError` do arquivo está no `_emitir`, e ele não
contradiz o parágrafo acima**: lá a violação não vem do corpo da requisição — vem
de dois códigos de 40 bits sorteados iguais —, não há como recusá-la na memória
antes de tentar gravar, e ela é **recuperável** sorteando outro `nonce`. Ele
também não é genérico: `_e_colisao_de_codigo` confere o nome da restrição, e
qualquer outra violação sobe.
"""

import logging
from collections.abc import Collection
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroDeDominio
from app.core.seguranca import gerar_codigo, gerar_nonce
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import Usuario
from app.schemas.pagamento import PagamentoEntrada
from app.schemas.reserva import (
    IngressoSaida,
    ItemDaReservaSaida,
    ReservaEntrada,
    ReservaSaida,
)
from app.services.pagamento import PaymentGateway

# ⚠️ **Importado, nunca redeclarado** (decisão registrada na Story 3.4). O
# docstring do `EventoPublico` diz, com todas as letras, que esta story cobraria
# do servidor o mesmo teto que o stepper já lê do contrato: com o número em dois
# lugares, o dia em que a regra mudar é o dia em que a tela e a rota discordam —
# e quem descobre isso é a pessoa que escolheu 8 ingressos e recebeu uma recusa.
from app.services.evento import MAXIMO_POR_COMPRA

logger = logging.getLogger(__name__)

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


def _transicionar(
    sessao: Session,
    reserva_id: UUID,
    *,
    de: EstadoReserva,
    para: EstadoReserva,
    condicao_extra: ColumnElement[bool] | None = None,
) -> bool:
    """Muda o estado da reserva **condicionado ao estado anterior** (AD-4).

    Este é o único lugar do projeto que escreve `reserva.estado`, e existe para
    a regra do AD-4 ser verdade por construção em vez de por disciplina de quem
    escrever a próxima transição. Devolve se **esta** chamada foi a que mudou:
    `False` não é erro, é "alguém chegou primeiro".

    É daqui que sai, de graça, a garantia que o AC de reprocessamento da Story
    3.9 pede — um pagamento executado duas vezes só emite ingresso na execução
    que vence o `rowcount`.
    """
    condicoes = [Reserva.id == reserva_id, Reserva.estado == de.value]
    if condicao_extra is not None:
        condicoes.append(condicao_extra)

    resultado = sessao.execute(
        update(Reserva)
        .where(*condicoes)
        .values(estado=para.value)
        # Os `Reserva` carregados ficam com o estado velho na sessão; quem
        # precisa do novo relê. Sincronizar aqui seria trabalho para manter em
        # dia um objeto que este service não consulta mais.
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount == 1


def _devolver_estoque(sessao: Session, reserva_id: UUID) -> None:
    """Solta ao estoque tudo o que os itens desta reserva seguravam.

    ⚠️ **Chamado só por quem venceu um `_transicionar`.** Devolver sem ter
    vencido a transição é devolver duas vezes quando duas conexões colhem a
    mesma reserva — a transição é o cadeado, e esta função é o que ele protege.

    ⚠️ **Todos os itens, sempre.** A colheita pode ter sido disparada por um
    setor só, mas a reserva expira inteira: deixar um item de fora a marcaria
    `EXPIRADA` com estoque preso para sempre, porque nada volta a colher uma
    reserva que já saiu de `PENDENTE`.
    """
    itens = sessao.scalars(
        select(ItemReserva)
        .where(ItemReserva.reserva_id == reserva_id)
        # ⚠️ **`order_by` é prevenção de deadlock, não estética** (code review da
        # Epic 3). Cada `UPDATE` abaixo trava a linha do setor até o `commit` de
        # quem chamou. Sem uma ordem estável, duas colheitas simultâneas tocam os
        # mesmos setores em ordens que o plano de execução escolhe — A trava
        # Pista e espera Camarote, B trava Camarote e espera Pista, e o Postgres
        # aborta uma com `40P01`, que vira `500` numa operação recuperável.
        # `setor_id` é a mesma chave que o `criar()` ordena, e é isso que faz as
        # duas famílias de escrita concordarem sobre a ordem de travamento.
        .order_by(ItemReserva.setor_id)
    ).all()

    for item in itens:
        resultado = sessao.execute(
            update(Setor)
            .where(
                Setor.id == item.setor_id,
                # ⚠️ Condicional também na devolução — o AD-3 vale para **toda**
                # escrita em estoque, não só para a que consome.
                # `vendidos - quantidade` calculado em Python parece seguro
                # porque "devolver nunca estoura", e é a mesma quebra com o
                # resultado certo em 99% dos casos.
                Setor.vendidos >= item.quantidade,
            )
            .values(vendidos=Setor.vendidos - item.quantidade)
            .execution_options(synchronize_session=False)
        )

        # ⚠️ **O AD-3 é `UPDATE` condicional provado por `rowcount`** — a
        # condição sozinha é metade dele (code review da Epic 3). Aqui o
        # `rowcount == 0` significa que `vendidos` já estava abaixo do que este
        # item segurava, ou seja: a contabilidade do estoque está inconsistente.
        # Sem esta linha o desfecho é silêncio — a reserva vira `EXPIRADA` ou
        # `RECUSADA` e o estoque simplesmente não volta, sem erro e sem rastro.
        #
        # **Log e não `raise`**, de propósito: quem chama já venceu a transição e
        # está prestes a confirmar. Derrubar a operação aqui deixaria a reserva
        # presa em `PENDENTE` para sempre, que é pior que a perda contábil. O
        # `CheckConstraint` do modelo já impede o estoque de ficar negativo.
        if resultado.rowcount != 1:
            logger.error(
                "Devolução de estoque não aplicada: reserva %s, setor %s, "
                "quantidade %s. O `vendidos` do setor está abaixo do que esta "
                "reserva segurava.",
                reserva_id,
                item.setor_id,
                item.quantidade,
            )


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
        # Mesma razão do `order_by` do `_devolver_estoque`: duas colheitas
        # simultâneas precisam percorrer as reservas vencidas na mesma ordem,
        # senão elas travam as linhas de `setor` em ordens cruzadas e uma morre
        # com `40P01`. Sem `ORDER BY` a ordem é a que o plano escolher.
        .order_by(Reserva.id)
    ).all()

    for reserva_id in ids_vencidas:
        if _transicionar(
            sessao,
            reserva_id,
            de=EstadoReserva.PENDENTE,
            para=EstadoReserva.EXPIRADA,
            # A condição de prazo entra **na mesma linha da transição**, e não
            # num `if` antes dela: entre ler "venceu" e gravar "expirou" cabe
            # outra conexão fazendo o mesmo.
            condicao_extra=Reserva.expira_em < func.now(),
        ):
            _devolver_estoque(sessao, reserva_id)


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

    # ⚠️ **A ordem do laço é a ordem em que as linhas de `setor` são travadas, e
    # ela não pode ser a do corpo da requisição** (code review da Epic 3). Cada
    # `UPDATE` abaixo segura a linha até o `commit` do fim desta função. Com a
    # ordem do cliente, dois pedidos concorrentes no mesmo evento — um mandando
    # `[Pista, Camarote]` e outro `[Camarote, Pista]` — travam em cruz e o
    # Postgres mata um com `40P01 deadlock detected`. Não é `ErroDeDominio`:
    # sobe até o handler genérico e vira `500 ERRO_INTERNO` numa recusa que
    # deveria ser `201` ou `409`. Um cliente hostil provoca isso de propósito;
    # dois compradores comuns tropeçam nisso por acaso.
    #
    # Ordenar por `setor_id` dá uma ordem global que **todo** caminho de escrita
    # respeita (o `_devolver_estoque` ordena pela mesma chave), e ordem global é
    # o que torna o ciclo de espera impossível. Não muda nada do que é validado:
    # as quatro recusas acima já rodaram sobre o corpo inteiro, e o `409` de
    # estoque desfaz tudo de qualquer jeito.
    for item in sorted(dados.itens, key=lambda item: item.setor_id):
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

    # Os canhotos entram aqui também, e não só na resposta do pagamento: a tela
    # da reserva paga precisa sobreviver a recarregar, e ela é servida por esta
    # função. Em `PENDENTE` a lista sai vazia sem ida ao banco.
    return _para_saida(reserva, evento, _ingressos(sessao, reserva, evento, cliente))


def pagar(
    sessao: Session,
    cliente: Usuario,
    reserva_id: UUID,
    dados: PagamentoEntrada,
    gateway: PaymentGateway,
) -> ReservaSaida:
    """Cobra a reserva e a leva a `PAGA` ou `RECUSADA` — a Story 3.8.

    ⚠️ **Aqui o `commit` acontece ANTES de duas das recusas, e isso é o oposto
    do `criar()` logo acima.** Lá, levantar `ErroDeDominio` é a forma de desfazer
    os `UPDATE` já aplicados — o "tudo ou nada". Aqui, dois caminhos de recusa
    **precisam** que o trabalho sobreviva: reserva vencida vira `EXPIRADA` e
    devolve estoque *antes* de responder `409`, e pagamento recusado vira
    `RECUSADA` e devolve estoque *antes* de responder `402`. Sem o `commit`
    antes do `raise`, o `finally: sessao.close()` do `obter_sessao` descartaria
    exatamente a mudança que o AC exige — e o sintoma seria o estoque nunca
    voltar de uma recusa, com o teste sequencial passando.

    **O gateway é chamado antes da transição**, e é o `UPDATE` condicional que
    decide quem escreve. Duas requisições simultâneas podem ambas autorizar
    (contra um gateway simulado isso é grátis; contra um real, é o problema que
    idempotência de cobrança resolve, e está fora do escopo do desafio) — mas
    exatamente uma vence o `rowcount`, e é ela que emite ingresso na Story 3.9.

    ⚠️ **O prazo é conferido na entrada e NÃO na transição para `PAGA`, e isso é
    escolha** (code review da Epic 3, decisão do Igor). Uma reserva que vence
    *durante* a chamada ao gateway é aprovada: a transição vencedora condiciona
    só `de=PENDENTE`, sem `expira_em`. A alternativa — acrescentar
    `expira_em >= func.now()` a esta transição — fecharia a janela ao custo de
    recusar depois de o gateway já ter autorizado, que com um gateway real é
    cobrança sem ingresso. A folga é coerente com a colheita preguiçosa do AD-4,
    que já parte de "a reserva vencida só morre quando alguém precisa do estoque
    dela": quem estava pagando quando o relógio virou não é quem o AD-4 quer
    punir. O estoque continua coerente nos dois casos, porque a reserva sai de
    `PENDENTE` e a colheita nunca mais a alcança.
    """
    reserva = sessao.scalars(
        select(Reserva)
        .where(Reserva.id == reserva_id, Reserva.cliente_id == cliente.id)
        .options(selectinload(Reserva.itens))
    ).first()

    if reserva is None:
        # O mesmo `404` do `obter`, e pelo mesmo motivo: distinguir "não existe"
        # de "não é sua" diria a quem varresse UUIDs quais deles são reservas de
        # alguém.
        raise ErroDeDominio(
            "RESERVA_NAO_ENCONTRADA",
            "Essa reserva não existe ou não é sua.",
            status_http=404,
        )

    # A colheita da Story 3.7 no segundo dos dois gatilhos do AD-4 — é este o
    # AC1 que a 3.7 deixou aberto por uma story, porque a rota que ele descreve
    # é a desta função.
    if _transicionar(
        sessao,
        reserva.id,
        de=EstadoReserva.PENDENTE,
        para=EstadoReserva.EXPIRADA,
        condicao_extra=Reserva.expira_em < func.now(),
    ):
        _devolver_estoque(sessao, reserva.id)
        sessao.commit()
        raise ErroDeDominio(
            "RESERVA_EXPIRADA",
            "O prazo desta reserva acabou e os ingressos voltaram para a venda. "
            "Nada foi cobrado.",
            status_http=409,
        )

    # Relê o estado: a reserva pode ter saído de `PENDENTE` por outra conexão
    # entre o `select` acima e agora.
    sessao.expire(reserva)

    if reserva.estado == EstadoReserva.EXPIRADA.value:
        # Já estava expirada quando chegou aqui — nada mudou, nada a confirmar.
        raise ErroDeDominio(
            "RESERVA_EXPIRADA",
            "O prazo desta reserva acabou e os ingressos voltaram para a venda. "
            "Nada foi cobrado.",
            status_http=409,
        )

    if reserva.estado != EstadoReserva.PENDENTE.value:
        # `PAGA`, `RECUSADA` ou `CANCELADA`. Um `409` e não um `200` silencioso:
        # quem repete o pagamento de uma reserva já paga precisa saber que a
        # segunda tentativa não fez nada, e `GET /reservas/{id}` diz o estado.
        raise ErroDeDominio(
            "RESERVA_NAO_PENDENTE",
            "Esta reserva não está mais aguardando pagamento.",
            status_http=409,
        )

    autorizacao = gateway.autorizar(
        total_centavos=reserva.total_centavos,
        meio=dados.meio,
        numero_cartao=dados.numero_cartao,
    )

    if not autorizacao.aprovada:
        if not _transicionar(
            sessao,
            reserva.id,
            de=EstadoReserva.PENDENTE,
            para=EstadoReserva.RECUSADA,
        ):
            # ⚠️ **Perder a transição muda a resposta** (code review da Epic 3).
            # Outra conexão tirou a reserva de `PENDENTE` entre a recusa do
            # gateway e esta linha — ela está `PAGA` ou `EXPIRADA`, e nada foi
            # gravado aqui. Responder `402` neste ramo afirmaria duas coisas
            # falsas de uma vez: que a recusa é o estado final da reserva, e que
            # "os lugares voltaram para a venda" quando ninguém os devolveu.
            # Este é o mesmo desfecho do ramo vencedor logo abaixo, e leva a
            # mesma resposta.
            raise ErroDeDominio(
                "RESERVA_NAO_PENDENTE",
                "Esta reserva não está mais aguardando pagamento.",
                status_http=409,
            )

        _devolver_estoque(sessao, reserva.id)
        sessao.commit()

        # ⚠️ **`402`, e não o `409` das outras recusas do domínio** (decisão do
        # Igor): recusa de pagamento não é conflito de estado, é a resposta do
        # gateway, e o `402 Payment Required` existe para exatamente isto. O
        # corpo continua `{codigo, mensagem}`, sem exceção ao formato único.
        raise ErroDeDominio(
            "PAGAMENTO_RECUSADO",
            "O pagamento foi recusado. Nada foi cobrado, e os lugares voltaram "
            "para a venda.",
            status_http=402,
        )

    if not _transicionar(
        sessao,
        reserva.id,
        de=EstadoReserva.PENDENTE,
        para=EstadoReserva.PAGA,
    ):
        # Outra conexão saiu de `PENDENTE` entre a autorização e esta linha.
        # Nada é emitido, e nada é confirmado — a transação morre no `raise`.
        raise ErroDeDominio(
            "RESERVA_NAO_PENDENTE",
            "Esta reserva não está mais aguardando pagamento.",
            status_http=409,
        )

    # ⚠️ **A emissão acontece aqui, e o lugar é a garantia inteira** (AD-14).
    # Mesma transação da transição, e **depois** do `if` acima: só quem venceu o
    # `rowcount` chega nesta linha. É isso, e só isso, que faz "pagamento
    # reprocessado não gera ingresso novo" ser verdade por construção — não há
    # `if ja_tem_ingresso` em lugar nenhum, e não deve haver.
    #
    # **Um ingresso por unidade**, e não um por item: `2 × Pista` são duas
    # linhas, com dois ids e dois códigos. É o que permite validar um e o outro
    # não, que é o comportamento inteiro da Epic 5.
    for item in reserva.itens:
        for _ in range(item.quantidade):
            _emitir(sessao, reserva, item, dados.nome)

    sessao.commit()

    # ⚠️ **Sem este `refresh`, a resposta mente em produção e a suíte não vê**
    # (code review da Epic 3). O `_transicionar` roda com
    # `synchronize_session=False` de propósito, então o `reserva.estado` deste
    # objeto continua `'PENDENTE'` depois do `UPDATE`. Quem desfazia isso, por
    # acidente, era o `expire_on_commit` do `commit` acima — que é `True` no
    # `sessionmaker` do `conftest.py` e **`False`** no `SessaoLocal` de
    # `app/core/db.py`. Resultado: em teste a releitura traz `PAGA`; em produção
    # nada expira, `_ingressos` devolve `[]` e `_para_saida` serializa
    # `PENDENTE`. O banco fica certo e o corpo do `200` fica errado.
    #
    # Hoje nenhuma tela quebra porque o `FormularioDePagamento` descarta o corpo
    # e relê por `GET` — mas o docstring da rota promete o contrário, e a Epic 4
    # lê justamente estes ingressos.
    sessao.refresh(reserva)

    evento = sessao.get(
        Evento, reserva.evento_id, options=[selectinload(Evento.setores)]
    )
    if evento is None:  # pragma: no cover
        raise ErroDeDominio(
            "RESERVA_NAO_ENCONTRADA",
            "Essa reserva não existe ou não é sua.",
            status_http=404,
        )

    return _para_saida(reserva, evento, _ingressos(sessao, reserva, evento, cliente))


# Quantas vezes a emissão sorteia outro `nonce` antes de deixar o erro subir.
# Cinco é generoso: cada tentativa é independente e a chance de uma colidir já é
# de uma em bilhões. O número existe para o laço ter fim, não porque se espere
# chegar perto dele.
_TENTATIVAS_DE_CODIGO = 5

# O nome do índice único de `ingresso.codigo`, como o Postgres o reporta. Escrito
# aqui porque é o que distingue "dois códigos iguais" — que se resolve sorteando
# outro `nonce` — de qualquer outra violação de integridade, que é bug e precisa
# subir.
_INDICE_DO_CODIGO = "ix_ingresso_codigo"


def _e_colisao_de_codigo(erro: IntegrityError) -> bool:
    """Se a violação foi o único de `codigo`, e não outra restrição da tabela.

    ⚠️ **Sem esta distinção o `except` viraria uma rede que engole bug.** Uma FK
    quebrada ou um `NOT NULL` esquecido também chegam como `IntegrityError`, e
    tentar de novo com outro `nonce` não os resolve — só os transformaria em cinco
    tentativas idênticas e um erro no fim, longe da causa.

    O `diag.constraint_name` do psycopg é a resposta estruturada; o texto é o
    fallback para o dia em que o driver mudar.
    """
    restricao = getattr(getattr(erro.orig, "diag", None), "constraint_name", None)
    if restricao is not None:
        return restricao == _INDICE_DO_CODIGO
    return _INDICE_DO_CODIGO in str(erro.orig)


def _emitir(
    sessao: Session, reserva: Reserva, item: ItemReserva, pagador_nome: str
) -> None:
    """Grava **um** ingresso, sorteando outro `nonce` se o código colidir.

    ⚠️ **Colisão de código é um `500` no meio do pagamento se ninguém a tratar,
    e é o desfecho mais feio do produto**: pagamento aprovado que estoura. Com o
    código em 40 bits (techspec `docs/techspec-codigo-curto.md`) a chance deixou
    de ser zero, e o índice único a transforma em `IntegrityError` dentro da mesma
    transação que acabou de marcar a reserva `PAGA`. Sortear outro `nonce` e
    recalcular é a saída — o código é derivado dele, então trocá-lo dá um código
    novo sem mexer em mais nada.

    ⚠️ **O `begin_nested()` não é enfeite: sem o SAVEPOINT não há o que
    reaproveitar.** Um `IntegrityError` sem savepoint invalida a transação
    inteira, e com ela o `UPDATE` que levou a reserva a `PAGA` e os ingressos
    irmãos já gravados — a segunda tentativa gravaria num contexto morto e a
    requisição terminaria em `PendingRollbackError`, apontando para longe da
    causa. O savepoint limita o estrago à linha que colidiu.

    O id é gerado **aqui**, e não deixado para o `default` do modelo: ele entra
    no HMAC (AD-5), então precisa existir antes do INSERT. Esperar o banco
    devolvê-lo obrigaria a um `flush` e a um segundo `UPDATE` só para gravar o
    código.
    """
    ingresso_id = uuid4()

    for tentativa in range(_TENTATIVAS_DE_CODIGO):
        nonce = gerar_nonce()
        ponto = sessao.begin_nested()
        try:
            sessao.add(
                Ingresso(
                    id=ingresso_id,
                    reserva_id=reserva.id,
                    evento_id=reserva.evento_id,
                    setor_id=item.setor_id,
                    # Quem **pagou**, e não o titular: o ingresso é da conta, e o
                    # cartão pode ser de outra pessoa (decisão do Igor). O valor
                    # é o digitado no checkout, congelado — trocar o nome da
                    # conta amanhã não reescreve ingresso já emitido.
                    pagador_nome=pagador_nome,
                    codigo=gerar_codigo(ingresso_id, reserva.evento_id, nonce),
                    nonce=nonce,
                )
            )
            # `flush` dentro do `try`, `commit` do savepoint fora: assim a
            # exceção aparece na linha que a provoca — mesma disciplina do
            # `cadastrar` de `services/autenticacao.py`.
            sessao.flush()
        except IntegrityError as erro:
            ponto.rollback()
            ultima = tentativa == _TENTATIVAS_DE_CODIGO - 1
            if ultima or not _e_colisao_de_codigo(erro):
                raise
            logger.warning(
                "código de ingresso colidiu na emissão da reserva %s "
                "(tentativa %d); sorteando outro nonce",
                reserva.id,
                tentativa + 1,
            )
            continue

        ponto.commit()
        return


def _ingressos(
    sessao: Session, reserva: Reserva, evento: Evento, cliente: Usuario
) -> list[IngressoSaida]:
    """Os canhotos de uma reserva paga — vazio em qualquer outro estado.

    **A consulta só acontece quando faz sentido**: ingresso nasce dentro da
    transação que marca `PAGA` (AD-14), então em `PENDENTE` não há o que buscar
    e a ida ao banco seria certa de voltar vazia.

    A ordem é a dos setores na página do evento — a mesma dos itens, e pelo
    mesmo motivo escrito no `_para_saida`. Dentro de um setor, os canhotos saem
    ordenados por `id`: eles são intercambiáveis, e o que não pode é a ordem
    mudar entre duas leituras da mesma tela.
    """
    if reserva.estado != EstadoReserva.PAGA.value:
        return []

    setores_por_id = {setor.id: setor for setor in evento.setores}
    posicao = {setor.id: indice for indice, setor in enumerate(evento.setores)}

    ingressos = sessao.scalars(
        select(Ingresso).where(Ingresso.reserva_id == reserva.id)
    ).all()

    return [
        IngressoSaida(
            # ⚠️ **O titular é a conta, e não o nome do checkout** (decisão do
            # Igor). O `cliente` é o dono da reserva por construção — as duas
            # rotas que chegam aqui filtram por `cliente_id` —, então não há join
            # a fazer: quem comprou é quem está na sessão.
            id=ingresso.id,
            titular_nome=cliente.nome,
            setor_nome=setores_por_id[ingresso.setor_id].nome,
            # ⚠️ Lido da coluna, **sem recalcular**. Recalcular aqui daria o mesmo
            # valor e escondia o ponto: a coluna existe para esta linha, e a
            # validação da portaria recalcula sempre (AD-5).
            codigo=ingresso.codigo,
        )
        for ingresso in sorted(
            ingressos, key=lambda i: (posicao[i.setor_id], str(i.id))
        )
    ]


def _para_saida(
    reserva: Reserva,
    evento: Evento,
    ingressos: list[IngressoSaida] | None = None,
) -> ReservaSaida:
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
        ingressos=ingressos or [],
    )
