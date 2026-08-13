"""O `Ingresso` — o que nasce quando a reserva vira `PAGA`, e o que vale na porta.

**Arquivo próprio, ao contrário de `ItemReserva`.** Um item não tem vida fora da
reserva ("2 × Pista" sem a reserva não significa nada) e por isso mora junto
dela; um ingresso tem vida própria: ele é compartilhado por link (Epic 4),
validado na portaria (Epic 5) e continua existindo depois de o show acabar. A
regra do projeto é agrupar por **agregado**, e este é um agregado novo.

**Três decisões da arquitetura estão materializadas aqui:**

- **O código é um token assinado, não um identificador** (AD-5). O conteúdo do
  QR são 8 símbolos de base32 de Crockford, e eles são o HMAC do servidor
  truncado — não um sorteio: sem o segredo, nem adivinhar UUID nem incrementar id
  produz um ingresso válido. O formato antigo era `ID.ASSINATURA`, 80 caracteres,
  e encolheu em 2026-08-12 para o campo manual da portaria ser usável na fila
  (techspec `docs/techspec-codigo-curto.md`).
- **Um ingresso por unidade.** Dois ingressos da Pista são duas linhas, com dois
  ids e dois códigos — e não uma linha com `quantidade = 2`. É o que permite
  validar um e o outro não, que é o comportamento inteiro da Epic 5.
- **Só quem paga emite** (AD-14), e só dentro da transação que marca a reserva
  como `PAGA`. Nenhum outro service, rota ou tarefa cria ingresso.

**`usado_em` e `validado_por` entram na Story 4.1**, antes de existir validação
alguma (Epic 5): o consumidor é a leitura, não a escrita. `GET /ingressos`
separa *Ativos* de *Utilizados* por `usado_em IS NULL`, e a Story 5.2 é quem
primeiro grava as duas — até lá, ambas ficam sempre `NULL` (techspec
`docs/techspec-meus-ingressos.md`).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
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

    # O nome de **quem pagou**, digitado no checkout — e não o titular do
    # ingresso (decisão do Igor, techspec `docs/techspec-codigo-curto.md`). O
    # ingresso está no nome de quem tem a conta; o cartão pode ser de outra
    # pessoa. A coluna nasceu como `titular_nome` na Story 3.9 e foi renomeada
    # quando a decisão foi tomada: coluna e campo de resposta com o mesmo nome
    # significando pessoas diferentes é armadilha que só se descobre depurando.
    #
    # ⚠️ **Hoje ela não tem leitor nenhum**, e fica de propósito: é o registro
    # de quem pagou, que é o que a Story 3.8 decidiu persistir. Ausência de tela
    # não a torna ruído. Congelada aqui pelo mesmo motivo do preço em
    # `item_reserva`.
    pagador_nome: Mapped[str] = mapped_column(String(120), nullable=False)

    # O código que vira QR: o HMAC truncado a 40 bits em base32 de Crockford,
    # 8 símbolos exatos (`String(8)`, sem folga — o tamanho é o contrato).
    #
    # ⚠️ **Único e indexado, e as duas coisas pelo mesmo motivo:** a validação da
    # portaria acha a linha **pelo código** — é o `where` dela, e é o caminho mais
    # sensível a tempo do produto. O único impede que duas linhas respondam à
    # mesma leitura de QR, e é ele que obriga a emissão a sortear outro `nonce`
    # quando colide (40 bits colidem; 43 caracteres de base64 não colidiam).
    #
    # ⚠️ **Achar a linha pelo código não é conferir o código.** A validação
    # **sempre recalcula** o HMAC das colunas (AD-5): esta coluna nunca é fonte da
    # verdade na comparação, senão bastaria a alguém conseguir escrever nela.
    # Consequência assumida: girar o `TICKET_SIGNING_SECRET` invalida os
    # ingressos já emitidos, que é o comportamento correto de um segredo
    # rotacionado.
    codigo: Mapped[str] = mapped_column(
        String(8), nullable=False, unique=True, index=True
    )

    # `secrets.token_urlsafe(24)` → 32 caracteres. É o que faz dois ingressos do
    # mesmo evento, do mesmo setor e da mesma reserva terem códigos diferentes
    # mesmo com o mesmo segredo.
    #
    # ⚠️ **Nunca sai do servidor**, ao contrário do `share_token` logo abaixo,
    # que sai do mesmo gerador — ver o par de docstrings em `core/seguranca.py`.
    nonce: Mapped[str] = mapped_column(String(32), nullable=False)

    # O endereço do link compartilhável (Story 4.3). `NULL` é "nunca
    # compartilhado" **ou** "revogado" — os dois casos são o mesmo estado, e é
    # isso que faz a revogação da 4.4 ser um corte e não um aviso de que algo
    # existiu ali.
    #
    # **Índice único**, e sem índice parcial: no Postgres `NULL` não colide com
    # `NULL` num índice único, então milhares de ingressos sem link convivem sem
    # complicação nenhuma. O índice é o `where` da rota pública, que busca por
    # esta coluna e por mais nada.
    #
    # ⚠️ **Coluna pública por construção** (AD-8): ela vira URL, viaja por
    # WhatsApp e aparece em print. Nada derivado de segredo entra aqui, e ela
    # **não** participa da assinatura do AD-5 — quem valida na porta recalcula o
    # HMAC a partir do `nonce`, que é o vizinho de cima e o oposto exato desta.
    share_token: Mapped[str | None] = mapped_column(
        String(32), nullable=True, unique=True, index=True
    )

    # Sem `criado_em`: o ingresso nasce na transação do pagamento, e nenhuma
    # story lê a hora de emissão. Mesmo argumento que deixou `setor` e
    # `item_reserva` sem a coluna.

    # `NULL` é "nunca validado" — o estado de todo ingresso emitido até a Epic
    # 5 existir. TIMESTAMPTZ em UTC (AD-11), como todo tempo do projeto: é
    # contra ele que `GET /ingressos` decide *Ativos* de *Utilizados*
    # (`usado_em IS NULL`), e é o `usado_em IS NULL` do `UPDATE` condicional
    # da Story 5.2 que impede validar o mesmo ingresso duas vezes.
    #
    # ⚠️ **Sem índice** (decisão da techspec da 4.1). O `UPDATE` da 5.2 é
    # `WHERE id = :id AND usado_em IS NULL` — busca por chave primária —, e o
    # painel da 5.6 filtra por `evento_id`, que já é indexado.
    usado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Quem leu o QR na porta. Sem `ondelete`: apagar uma conta de portaria que
    # já validou um ingresso é recusado pelo Postgres, o mesmo tratamento que
    # `reserva.cliente_id` dá a quem comprou.
    validado_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True
    )

    # ⚠️ **Nenhum `relationship`**, aqui nem do outro lado. Precedente de
    # `Reserva`, que também não tem: relacionamento sem consumidor é promessa
    # vazia, e quem monta a saída lê `Evento` e `Setor` por conta própria. Um
    # `Ingresso.setor` criado agora convidaria a próxima pessoa a contar
    # ingressos para derivar disponibilidade — o que o AD-13 proíbe.
