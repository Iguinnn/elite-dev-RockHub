"""Modelos `Reserva` e `ItemReserva` — a compra enquanto ela ainda não é uma
compra — mais o enum `EstadoReserva`, que é a máquina de estados do AD-4.

As três coisas moram juntas porque `ItemReserva` não tem vida fora de
`Reserva` (um "2 × Pista" sem a reserva não significa nada) e o enum é o
estado dela. Mesmo precedente do `usuario.py`, que abriga `Usuario` e
`PapelUsuario`, e do `evento.py`, que abriga `Evento` e `Setor`.

Quatro decisões da arquitetura estão materializadas aqui, e vale saber qual é
qual antes de mexer:

- **A reserva segura estoque desde a criação** (AD-4). Ela nasce `PENDENTE` já
  tendo consumido `setor.vendidos` pelo `UPDATE` condicional do AD-3 — e é
  isso que dá sentido ao `expira_em`: o lugar já está preso, e o prazo é o que
  impede que fique preso para sempre.
- **Transição de estado é sempre condicionada ao estado anterior** (AD-4).
  Nunca `SET estado = 'PAGA' WHERE id = :id`, sempre
  `... WHERE id = :id AND estado = 'PENDENTE'`. Zero linhas afetadas é o sinal
  de "alguém chegou primeiro", não uma exceção — e é isso que faz
  *reprocessar um pagamento aprovado não gerar ingresso novo* (AD-14) ser
  verdade por construção, e não por um `if` em algum lugar.
- **A expiração é preguiçosa** (AD-4). Não há worker nem cron: `expira_em` é
  lido por quem toca a reserva, e quem colhe as vencidas é a Story 3.7.
- **O estoque não se deriva daqui** (AD-13). É proibido responder "quantos
  restam" com `COUNT` ou `sum(quantidade)` sobre `item_reserva`. A resposta é
  `setor.capacidade - setor.vendidos`, sempre. Esta é a tabela sobre a qual a
  conta errada seria a mais óbvia de escrever, e por isso a proibição está
  escrita aqui, e não só nos serviços de leitura.

**Ninguém lê nem escreve nestas tabelas ainda.** A Story 3.5 entrega o schema;
reservar é a 3.6, colher o que expirou é a 3.7, pagar é a 3.8 e emitir o
ingresso é a 3.9. É o mesmo recorte da Story 2.3, que criou `evento` e `setor`
uma epic antes de alguém as ler.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EstadoReserva(str, Enum):
    """Os cinco estados do AD-4, e quem grava cada um.

    `PENDENTE` nasce assim na Story 3.6; `PAGA` e `RECUSADA` são a resposta do
    pagamento (3.8); `EXPIRADA` é a colheita preguiçosa (3.7). `CANCELADA` não
    tem ninguém que a escreva: o cancelamento pelo cliente é corte consciente
    registrado no README da raiz, e o valor existe no schema porque o AD-4 o
    fixa — é ele que torna o corte reversível sem migração.
    """

    PENDENTE = "PENDENTE"
    PAGA = "PAGA"
    RECUSADA = "RECUSADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"


class Reserva(Base):
    __tablename__ = "reserva"
    __table_args__ = (
        # A lista literal, e não o tipo `ENUM` nativo do Postgres: é o
        # precedente do `usuario.papel` desde a Story 1.3. Acrescentar um
        # estado aqui é um DROP/CREATE de constraint que o `downgrade()`
        # desfaz sem cerimônia; com tipo nativo seria `ALTER TYPE` dentro da
        # migração, que é o ponto de atrito conhecido daquela escolha.
        CheckConstraint(
            "estado IN ('PENDENTE', 'PAGA', 'RECUSADA', 'EXPIRADA', 'CANCELADA')",
            name="estado_valido",
        ),
        # Dinheiro negativo é dinheiro andando para trás — o mesmo argumento do
        # `ck_setor_preco_nao_negativo`.
        CheckConstraint("total_centavos >= 0", name="total_nao_negativo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Sem `ondelete`: apagar quem já comprou tem que doer, e o Postgres recusa.
    # Mesmo tratamento que `evento.organizador_id` dá a quem publicou e que
    # `evento_portaria.usuario_id` dá a quem foi escalado.
    #
    # `index=True` porque esta é a coluna do `where` de "minhas compras"
    # (Epic 4) — o Postgres não cria índice para chave estrangeira.
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    # Sem `ondelete` pelo mesmo motivo do `cliente_id`: apagar um show que já
    # vendeu ingresso é recusado pelo banco.
    #
    # ⚠️ **Sem índice, de propósito.** A disciplina desde a Story 2.3 é indexar
    # a chave estrangeira que **é lida**, não todas — e esta não é lida por
    # nenhuma story planejada: ela existe para a reserva saber de que show ela
    # é, não para ser consultada. Índice preventivo é peso sem gargalo
    # demonstrado, e acrescentá-lo depois é uma linha de migração. Isto não é
    # esquecimento.
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evento.id"), nullable=False
    )
    # `String(20)` + `CHECK`, como `usuario.papel`. O enum acima é quem
    # escreve, sempre pelo `.value`.
    #
    # **Sem `server_default`**, ao contrário do `setor.vendidos`: zero é o
    # começo natural de um contador, mas `PENDENTE` é uma **transição** — a
    # primeira da máquina de estados. Com default, um INSERT que esquecesse o
    # estado passaria em silêncio como se tivesse decidido.
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    # O prazo com que a reserva nasceu (criação + 10 min, AD-4), escrito pelo
    # service da Story 3.6. `NOT NULL` e **não** apagado ao pagar: ele não é um
    # campo que expira e some, é o prazo que valeu — quem diz se o prazo ainda
    # importa é o `estado`. TIMESTAMPTZ em UTC, como todo tempo do projeto
    # (AD-11), e é isso que permite compará-lo com o `now()` do Postgres na
    # colheita da 3.7 sem conversão de fuso pelo caminho.
    expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # BIGINT em centavos (AD-11). É o valor **congelado** no ato da reserva:
    # o dia em que o organizador mudar o preço de um setor, a reserva paga tem
    # que continuar dizendo quanto custou. Quem soma é o service da 3.6; o
    # banco só garante que não é negativo — amarrar o total à soma dos itens
    # seria um TRIGGER, e este projeto não tem nenhum.
    total_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ⚠️ Sem `order_by`, e ao contrário de `Evento.setores` isso é deliberado:
    # aqui não existe coluna de ordem natural, e ordenar por `setor_id` seria
    # ordem de UUID — aleatória fingindo de determinística. Quem exibir os
    # itens (3.6 e 3.8) ordena pelo **nome do setor**, que é a mesma ordem da
    # página do evento.
    itens: Mapped[list["ItemReserva"]] = relationship(
        back_populates="reserva",
        cascade="all, delete-orphan",
        # Sem isto o ORM emite `UPDATE item_reserva SET reserva_id = NULL`
        # antes do DELETE, estoura no NOT NULL e nunca chega no CASCADE que a
        # migração declarou. As duas metades precisam concordar — é a mesma
        # armadilha de `Evento.setores`.
        passive_deletes=True,
    )

    # ⚠️ **Nenhum `relationship` para `Usuario`, `Evento` ou `Setor`**, aqui
    # nem no `ItemReserva`. Precedente de `Evento.portarias`, que existe sem
    # `back_populates` em `usuario.py`: relacionamento sem consumidor é
    # promessa vazia, e não existe service nenhum ainda. Um `ItemReserva.setor`
    # criado agora, além de não ser usado, convidaria a próxima pessoa a
    # escrever `sum(item.quantidade for item in setor.itens)` e derivar
    # disponibilidade — exatamente o que o AD-13 proíbe. Quando a 3.6 precisar,
    # é uma linha, e **não** é migração.


class ItemReserva(Base):
    __tablename__ = "item_reserva"
    __table_args__ = (
        # Item de quantidade zero é linha que não consome estoque nenhum e
        # ainda assim aparece no checkout.
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint("preco_unitario_centavos >= 0", name="preco_nao_negativo"),
        # Um item por setor em cada reserva: o `UPDATE` de estoque da 3.6 fica
        # com um alvo só por setor, e a soma que a página do evento já mostra
        # ("3 ingressos · 2 setores") vira uma linha por setor, sem ambiguidade.
        # Por reserva, não global: o mesmo setor em outra reserva é outra venda.
        #
        # O nome vai explícito porque o template `uq` da convenção usa só a
        # primeira coluna e sairia `uq_item_reserva_reserva_id` — que lido em
        # voz alta diz "um item por reserva", o oposto do que a constraint faz.
        # Mesma armadilha e mesma saída do `uq_setor_evento_id_nome` da 2.3.
        UniqueConstraint(
            "reserva_id", "setor_id", name="uq_item_reserva_reserva_id_setor_id"
        ),
    )

    # `id` próprio, e não a chave primária composta `(reserva_id, setor_id)` da
    # `evento_portaria`: aquela é vínculo puro, e esta **carrega dado próprio**
    # (quantidade e preço congelado). O dia em que algo precisar apontar para
    # um item — uma devolução parcial, um ingresso por item — a chave composta
    # viraria migração.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # O único `CASCADE` das quatro chaves estrangeiras destas duas tabelas:
    # item sem reserva não significa nada. Indexado porque é lido em todo
    # carregamento de reserva e varrido a cada DELETE em cascata — o mesmo
    # argumento do `ix_setor_evento_id`.
    reserva_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reserva.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Sem `ondelete`: apagar um setor que já foi vendido é recusado pelo banco.
    #
    # ⚠️ É esta chave que muda o alcance prático do `ON DELETE CASCADE` de
    # `setor`: apagar um evento **sem** reserva continua levando os setores
    # junto, e apagar um evento **com** reserva passa a falhar aqui. Os dois
    # comportamentos são desejados — composição some junto, dinheiro não some.
    #
    # Indexado porque é o `where` da colheita preguiçosa da Story 3.7, que
    # devolve ao estoque o que as reservas vencidas seguravam.
    setor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("setor.id"), nullable=False, index=True
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    # O preço **congelado** no ato da reserva, não uma cópia viva de
    # `setor.preco_centavos`. BIGINT em centavos (AD-11).
    preco_unitario_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Sem `criado_em`: itens nascem na mesma transação da reserva, e a data
    # dela já responde "quando isso apareceu". Mesmo argumento que deixou
    # `setor` sem a coluna na Story 2.3.

    reserva: Mapped["Reserva"] = relationship(back_populates="itens")
