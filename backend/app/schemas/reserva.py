"""Schemas de entrada e saída da reserva — a primeira escrita do lado do cliente.

**O que este contrato recusa, e por quê.** Ele é a segunda rota de escrita do
domínio, e a primeira que consome estoque. Três coisas ficam de fora de
propósito:

- **Nenhum teto por item.** `quantidade` tem `ge=1` e **não** tem `le`: o teto é
  da **compra** (`MAXIMO_POR_COMPRA`, seis ingressos), e quem soma as
  quantidades é o service. Um `le=6` por item passaria a impressão de estar
  cobrindo a regra e cobriria a errada — quatro na Pista mais três no Camarote
  passariam aqui e dariam sete. É o mesmo aviso que a Story 3.5 escreveu ao
  recusar um `CHECK (quantidade <= 6)` no banco.
- **`itens` sem `min_length`.** "Uma reserva precisa de ao menos um item" é
  regra de negócio e mora no service, que responde `RESERVA_SEM_ITEM`. Com
  `min_length=1`, o Pydantic responderia `DADOS_INVALIDOS` — um código genérico
  para uma regra específica, e a tela não teria como dizer o que faltou. Mesma
  porta por onde `setores` e `portaria_ids` passam desde a 2.4/2.5.
- **`cliente_id`, `estado`, `expira_em` e `total_centavos` não existem aqui.**
  Os quatro nascem no service: o primeiro vem da sessão, os outros três são
  consequência da regra. Não há campo de entrada por onde o corpo os influencie.

**Sem `extra="forbid"`**, como todos os schemas de entrada do projeto: campo
desconhecido **ignorado** é garantia mais forte que campo desconhecido recusado.
Recusar anuncia quais nomes existem; ignorar não dá nem essa pista, e o efeito
prático é o mesmo — o campo não chega a lugar nenhum.

**E o que a saída recusa:** `capacidade`, `vendidos`, `disponibilidade` e
`proporcao_vendida` (UX-DR7, AD-13). É o `response_model` da rota que garante
isso, não a tela. `quantidade`, `preco_unitario_centavos` e `total_centavos`
**entram** e não contradizem nada: quantidade que a pessoa pediu não é estoque;
quantidade que resta é.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.reserva import EstadoReserva


class ItemDeReservaEntrada(BaseModel):
    setor_id: UUID
    # ⚠️ **`ge=1` e nenhum `le`** — o motivo inteiro está no topo do módulo. Zero
    # é recusado aqui, e não pelo `CHECK (quantidade > 0)` da Story 3.5: item de
    # quantidade zero não consome estoque nenhum e ainda assim apareceria no
    # checkout, e o banco recusá-lo viraria `IntegrityError` → `500`.
    quantidade: int = Field(ge=1)


class ReservaEntrada(BaseModel):
    # **Explícito no corpo, e não derivado do primeiro setor.** Derivar aceitaria
    # em silêncio um corpo que mistura setores de dois shows, e `reserva.evento_id`
    # passaria a mentir sobre metade dos itens. Com o campo aqui, a mistura é
    # `SETOR_INVALIDO` — e a checagem sai de graça, porque o service lê os setores
    # de `evento.setores`.
    evento_id: UUID
    # `default_factory=list` para que **ausência** e **lista vazia** caiam na
    # mesma regra do service (`RESERVA_SEM_ITEM`), como `setores` e
    # `portaria_ids` da 2.4/2.5. Sem ele, o campo ausente vira "field required"
    # do Pydantic, ou seja, `DADOS_INVALIDOS`.
    #
    # `max_length=20` é proteção contra corpo absurdo, não regra de produto —
    # mesmo teto e mesmo argumento dos setores. O teto de produto é o
    # `MAXIMO_POR_COMPRA`, e ele é do service.
    itens: list[ItemDeReservaEntrada] = Field(default_factory=list, max_length=20)


class ItemDaReservaSaida(BaseModel):
    """Um item da reserva como a tela do checkout o mostra.

    **Sem `from_attributes`**: `setor_nome` não é atributo de `ItemReserva` — o
    modelo da 3.5 não tem `relationship` para `Setor`, e nem deve ter. Quem monta
    é o service, e o nome sai do próprio `Setor`.

    **O preço é o congelado no ato da reserva**, lido de
    `item_reserva.preco_unitario_centavos` e nunca de `setor.preco_centavos`: o
    dia em que o organizador mudar o preço, a reserva tem que continuar dizendo
    quanto custou.
    """

    setor_id: UUID
    setor_nome: str
    quantidade: int
    preco_unitario_centavos: int


class IngressoSaida(BaseModel):
    """Um canhoto — o que a tela desenha e o que a portaria vai ler (Story 3.9).

    **`codigo` são os 8 símbolos de base32 de Crockford** que viram QR — o HMAC
    do AD-5 truncado a 40 bits (techspec `docs/techspec-codigo-curto.md`; até
    2026-08-12 era `ID.ASSINATURA`, 80 caracteres). O `nonce` **não** entra: ele é
    ingrediente secreto da fórmula e nunca sai do servidor, e expor as partes
    convidaria alguém a recombiná-las por fora.

    ⚠️ **`titular_nome` é o nome da conta, e não o digitado no checkout** (decisão
    do Igor). O ingresso é de quem tem a conta; quem pagou fica em
    `ingresso.pagador_nome`, que não tem leitor nenhum hoje.

    **`setor_nome` e não `setor_id`**: quem lê o canhoto quer saber onde vai
    ficar. O id não é desenhado em lugar nenhum desta tela.
    """

    id: UUID
    titular_nome: str
    setor_nome: str
    codigo: str


class ReservaSaida(BaseModel):
    """A reserva como o cliente a vê — o corpo das duas rotas da Story 3.6.

    ⚠️ **`capacidade`, `vendidos`, `disponibilidade` e `proporcao_vendida` não
    entram**, e é este `response_model` que garante isso (UX-DR7, AD-13). Esta é
    a primeira rota de **escrita** do lado do cliente, e a tentação muda de
    forma: não é devolver o estoque, é lê-lo para decidir. O contrato não o
    carrega nas duas direções.

    **`evento_nome` e `evento_data_hora` entram** porque a tela `/reservas/{id}`
    precisa dizer de que show é a reserva sem uma segunda chamada — mesmo
    argumento que pôs `portarias` no `EventoSaida` da 2.5.

    **`criado_em` fica de fora**, e com ele qualquer campo que a tela não
    desenhe: mesma disciplina que manteve `imagem_url` fora do
    `EventoNaProgramacao`. O que a reserva mostra é o prazo que ela ainda tem,
    não a hora em que nasceu.

    **Sem `from_attributes`**: três dos oito campos não são atributos de
    `Reserva`. Declarar a conversão prometeria uma leitura que não acontece.
    """

    id: UUID
    evento_id: UUID
    evento_nome: str
    evento_data_hora: datetime
    # O enum do modelo, e não `str` cru: a lista fechada entra no OpenAPI, e a
    # 3.7 (`EXPIRADA`) e a 3.8 (`PAGA`, `RECUSADA`) herdam o contrato pronto. Só
    # `PENDENTE` é produzível nesta story, e a tela não ramifica por ele — mas um
    # contrato de reserva sem o estado dela esconde a coisa principal.
    estado: EstadoReserva
    # TIMESTAMPTZ em UTC (AD-11). É contra ele que o cronômetro da tela conta, e
    # quem decide se a reserva expirou é o banco, na Story 3.7 — o cronômetro
    # chegando a zero é informação, não veredito.
    expira_em: datetime
    # A soma congelada, em centavos (AD-11). Bate com a soma dos itens no
    # instante da reserva e continua batendo depois de o preço do setor mudar.
    total_centavos: int
    # Ordenados **pelo nome do setor** — a mesma ordem da página do evento, e a
    # que a Story 3.5 deixou escrita no modelo ao recusar um `order_by` no
    # `relationship` (lá não há coluna de ordem natural; aqui há o nome).
    itens: list[ItemDaReservaSaida]
    # ⚠️ **Vazia enquanto a reserva não é `PAGA`**, e é isso que a torna segura
    # de estar sempre no contrato: ingresso só nasce dentro da transação que
    # marca o pagamento (AD-14), então não há estado em que ela minta. A tela
    # ramifica pelo `estado`, não pelo tamanho desta lista.
    #
    # **Aqui, e não numa rota própria** (decisão do Igor): a reserva paga já é o
    # endereço da confirmação, e quem acabou de pagar não deveria precisar de
    # uma segunda chamada para ver o que comprou. `Meus ingressos` é a Epic 4, e
    # é ela que ganha rota própria — para listar ingressos de **várias** compras,
    # que é uma pergunta diferente.
    ingressos: list[IngressoSaida] = []
