"""O `Ingresso` — o que nasce quando a reserva vira `PAGA`, e o que vale na porta.

**Arquivo próprio, ao contrário de `ItemReserva`.** Um item não tem vida fora da
reserva ("2 × Pista" sem a reserva não significa nada) e por isso mora junto
dela; um ingresso tem vida própria: ele é compartilhado por link (Epic 4),
validado na portaria (Epic 5) e continua existindo depois de o show acabar. A
regra do projeto é agrupar por **agregado**, e este é um agregado novo.

**Três decisões da arquitetura estão materializadas aqui:**

- **O código é um token assinado, não um identificador** (AD-5). O conteúdo do
  QR é `ID.ASSINATURA`, e é a assinatura que impede forja: sem o segredo do
  servidor, nem adivinhar UUID nem incrementar id produz um ingresso válido.
- **Um ingresso por unidade.** Dois ingressos da Pista são duas linhas, com dois
  ids e dois códigos — e não uma linha com `quantidade = 2`. É o que permite
  validar um e o outro não, que é o comportamento inteiro da Epic 5.
- **Só quem paga emite** (AD-14), e só dentro da transação que marca a reserva
  como `PAGA`. Nenhum outro service, rota ou tarefa cria ingresso.

⚠️ **Faltam de propósito `usado_em` e `validado_por`**, as duas colunas do AD-6.
Elas são da Epic 5, e a disciplina do projeto é não criar coluna sem consumidor:
aqui não existe validação nenhuma ainda. Isto **não** é esquecimento — a
migração que as acrescenta é da Story 5.2.
"""

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Ingresso(Base):
    __tablename__ = "ingresso"

    # ⚠️ **UUIDv4, nunca sequencial** (AD-5). Com id sequencial, quem tem um
    # ingresso conhece o vizinho — e ainda que a assinatura o barre, o id é
    # metade do código: entregá-lo de graça é entregar metade do problema.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # Sem `ondelete`, ao contrário de `item_reserva.reserva_id`: apagar uma
    # reserva que já virou ingresso é recusado pelo banco. Item de checkout some
    # junto com o checkout; ingresso pago é dinheiro.
    #
    # Indexado porque é o `where` de "meus ingressos" (Epic 4), que chega à
    # reserva pelo cliente e daqui aos ingressos dela.
    reserva_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reserva.id"), nullable=False, index=True
    )

    # Redundante com `reserva.evento_id`, e de propósito: ele entra na
    # assinatura (AD-5) e é o `where` do painel do turno (Story 5.6). Derivá-lo
    # por join a cada validação seria uma consulta a mais no caminho mais
    # sensível a tempo do produto — a fila da porta.
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evento.id"), nullable=False, index=True
    )

    # ⚠️ **Sem índice**, ao contrário dos dois acima: nenhuma story planejada
    # filtra ingresso por setor. Ele existe para o canhoto dizer de que setor é.
    # A disciplina desde a Story 2.3 é indexar a chave que **é lida** num
    # `where`, não todas.
    setor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("setor.id"), nullable=False
    )

    # O nome que a pessoa digitou no checkout, e não uma cópia de
    # `usuario.nome`: o campo chega preenchido com o nome da conta e é editável,
    # porque quem compra pode estar comprando para outra pessoa. Congelado aqui
    # pelo mesmo motivo do preço em `item_reserva` — trocar o nome da conta
    # amanhã não reescreve ingresso já emitido.
    titular_nome: Mapped[str] = mapped_column(String(120), nullable=False)

    # base64url do HMAC-SHA256 sem padding: 43 caracteres. `String(64)` dá
    # folga para o dia em que o algoritmo mudar sem virar migração.
    #
    # ⚠️ **Guardada só para montar o QR sem recalcular.** A validação da
    # portaria **sempre recalcula** (AD-5), e assinatura divergente é recusada
    # sem consultar o banco. Esta coluna nunca é fonte da verdade — comparar
    # contra ela transformaria o banco em oráculo de assinatura, que é
    # exatamente o que o AD-5 evita. Consequência assumida: girar o
    # `TICKET_SIGNING_SECRET` invalida os ingressos já emitidos, que é o
    # comportamento correto de um segredo rotacionado.
    assinatura: Mapped[str] = mapped_column(String(64), nullable=False)

    # `secrets.token_urlsafe(24)` → 32 caracteres. É o que faz dois ingressos do
    # mesmo evento, do mesmo setor e da mesma reserva terem assinaturas
    # diferentes mesmo com o mesmo segredo.
    nonce: Mapped[str] = mapped_column(String(32), nullable=False)

    # Sem `criado_em`: o ingresso nasce na transação do pagamento, e nenhuma
    # story lê a hora de emissão. Mesmo argumento que deixou `setor` e
    # `item_reserva` sem a coluna.

    # ⚠️ **Nenhum `relationship`**, aqui nem do outro lado. Precedente de
    # `Reserva`, que também não tem: relacionamento sem consumidor é promessa
    # vazia, e quem monta a saída lê `Evento` e `Setor` por conta própria. Um
    # `Ingresso.setor` criado agora convidaria a próxima pessoa a contar
    # ingressos para derivar disponibilidade — o que o AD-13 proíbe.
