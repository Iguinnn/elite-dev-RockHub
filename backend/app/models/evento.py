"""Modelos `Evento` e `Setor` — o show e as faixas de ingresso que ele vende.

As duas classes moram juntas porque `Setor` não tem vida fora de `Evento`:
um "Pista" sem show não significa nada. Mesmo precedente do `usuario.py`, que
abriga `Usuario` e `PapelUsuario`.

Três decisões da arquitetura estão materializadas aqui, e vale saber qual é
qual antes de mexer:

- **Preço e capacidade pertencem ao setor, nunca ao evento** (AD-12). É o que
  permite Pista e Camarote no mesmo show com preços e lotações diferentes.
- **`setor.vendidos` é a única fonte de verdade da disponibilidade** (AD-13).
  Disponível é `capacidade - vendidos`, calculado na hora; é proibido derivar
  a conta com `COUNT` sobre reservas ou ingressos.
- **O `CHECK` de estoque é rede de segurança, não a regra** (AD-3). A regra
  de verdade é o `UPDATE` condicional que o service da Epic 3 executa
  (`... WHERE id = :id AND vendidos + :q <= capacidade`), e é ele quem devolve
  "sem estoque" afetando zero linhas. A constraint é o que sobra de pé se
  algum caminho da aplicação escapar desse `UPDATE`.

Nada na aplicação lê ou escreve nestas tabelas ainda — publicar evento é a
Story 2.4.
"""

import uuid
from datetime import datetime

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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Evento(Base):
    __tablename__ = "evento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Sem `ondelete`: apagar um organizador com eventos publicados deve doer.
    organizador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    # TIMESTAMPTZ em UTC, como todo tempo do projeto (AD-11).
    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Quem preenche é o organizador na 2.4; o catálogo entra só como sugestão.
    local: Mapped[str] = mapped_column(String(200), nullable=False)
    # Anuláveis porque a Discovery pode não trazer nenhum dos dois.
    cidade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    imagem_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # O id da atração no catálogo. Sem unicidade de propósito: a mesma atração
    # vira uma data em São Paulo e outra no Rio, e isso é uma turnê, não um
    # engano. A regra "todo evento nasce de uma atração" é de produto e vive
    # no service da Story 2.4, não no banco.
    origem_externa_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # `NULL` é rascunho. É o que torna verificável o AC da Story 3.1 —
    # "eventos não publicados não aparecem" precisa de um evento não publicado
    # para provar alguma coisa.
    publicado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    setores: Mapped[list["Setor"]] = relationship(
        back_populates="evento",
        cascade="all, delete-orphan",
        # Sem isto o ORM emite `UPDATE setor SET evento_id = NULL` antes do
        # DELETE, estoura no NOT NULL e nunca chega no CASCADE que a migração
        # declarou. As duas metades precisam concordar.
        passive_deletes=True,
    )


class Setor(Base):
    __tablename__ = "setor"
    __table_args__ = (
        # AD-3: rede de segurança do banco. A regra de verdade é o UPDATE
        # condicional do service da Epic 3 — esta constraint é o que sobra de
        # pé se algum caminho da aplicação escapar dela.
        CheckConstraint(
            "vendidos >= 0 AND vendidos <= capacidade", name="estoque_valido"
        ),
        # Capacidade zero produz um setor que nasce esgotado, aparece na tela e
        # ninguém entende por que não dá para comprar.
        CheckConstraint("capacidade > 0", name="capacidade_positiva"),
        # Preço negativo é dinheiro andando para trás.
        CheckConstraint("preco_centavos >= 0", name="preco_nao_negativo"),
        # Dois "Pista" no mesmo evento deixariam o cliente escolhendo no escuro
        # na tela da Story 3.4. Por evento, não global: outro show pode ter
        # Pista. O nome vai explícito porque o template `uq` da convenção usa
        # só a primeira coluna, e sairia `uq_setor_evento_id` — que parece
        # dizer "um setor por evento", o oposto do que a constraint faz.
        UniqueConstraint("evento_id", "nome", name="uq_setor_evento_id_nome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Índice explícito: o Postgres não cria um para chave estrangeira, e esta é
    # lida em todo carregamento de evento e varrida a cada DELETE em cascata.
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evento.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    capacidade: Mapped[int] = mapped_column(Integer, nullable=False)
    # `server_default` e não `default`: o DEFAULT 0 fica no schema e vale
    # também para INSERT vindo de migração, seed ou psql.
    vendidos: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    # BIGINT em centavos (AD-11). Nunca Float nem Numeric: dinheiro em ponto
    # flutuante é erro de arredondamento esperando acontecer.
    preco_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)

    evento: Mapped["Evento"] = relationship(back_populates="setores")
