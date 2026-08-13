"""A `Validacao` — uma linha por tentativa na porta, não por entrada (Story 5.6).

**Por que a tabela existe.** Contar os quatro vereditos exige guardar os quatro, e
até aqui o banco só sabia de quem entrou: `ingresso.usado_em` e `validado_por` só
nascem no caminho do `VALIDO`, e `INVALIDO`, `JA_UTILIZADO` e `EVENTO_ERRADO` eram
resposta HTTP que acabava ali.

**O que se ganha além do número é uma trilha de auditoria**: quem estava na porta,
o que leu e o que o sistema respondeu. É o registro que faltava para responder
"por que essa pessoa não entrou?" depois do show.

⚠️ **Ela não é a fonte da verdade sobre quem entrou** — `ingresso.usado_em` é, e
continua sendo. Aquela coluna é escrita pelo `UPDATE` condicional do AD-6, que é
atômico; esta tabela é o registro do que foi **tentado**. O `entradas` do contador
sai do `usado_em`, e não de `COUNT(validacao WHERE resultado = 'VALIDO')`, porque
no dia em que os dois divergirem é o `usado_em` que eu quero que ganhe. Os dois
devem sempre bater, e um teste confere isso.

⚠️ **O código tentado não é persistido**, e a ausência é a decisão. Ele não muda
nenhum dos quatro números, e guardar o que as pessoas digitam errado é reter dado
sem consumidor. O `ingresso_id` fica quando ele é conhecido, e é nulo nos dois
casos de `INVALIDO` — código malformado e código que não é de ingresso nenhum. A
coluna anulável é a distinção que sobra, e ela basta.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Veredito(str, Enum):
    """Os quatro vereditos do FR6 — o único lugar em que os nomes existem.

    **Ele nasce no modelo e é importado pelo schema**, no precedente exato do
    `PapelUsuario`: `schemas/ingresso.py::ResultadoDaValidacao` trocou um
    `Literal[...]` por este enum quando a Story 5.6 passou a gravá-los numa
    coluna. As quatro palavras existindo em dois arquivos é o começo de elas
    discordarem — e agora um dos dois é o `CHECK` do banco.

    `str, Enum` serializa igual ao `Literal` que substituiu (o JSON continua
    `"VALIDO"`), e o OpenAPI fica melhor: um nome em vez de uma união anônima.
    """

    VALIDO = "VALIDO"
    INVALIDO = "INVALIDO"
    JA_UTILIZADO = "JA_UTILIZADO"
    EVENTO_ERRADO = "EVENTO_ERRADO"


class Validacao(Base):
    __tablename__ = "validacao"
    # `String(20)` + `CHECK`, e o `Enum` do Python fora do ORM — a convenção do
    # projeto desde a Story 1.3, com `usuario.papel` e `reserva.estado` como os
    # dois precedentes. Um `ENUM` nativo do Postgres exigiria migração de tipo
    # para acrescentar um quinto veredito; o `CHECK` é um `ALTER` de constraint.
    __table_args__ = (
        CheckConstraint(
            "resultado IN ('VALIDO', 'INVALIDO', 'JA_UTILIZADO', 'EVENTO_ERRADO')",
            name="resultado_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # ⚠️ **O evento do caminho, e não o do ingresso.** No `EVENTO_ERRADO` os dois
    # são diferentes de propósito: é a contagem *deste* turno, e a tentativa
    # aconteceu nesta porta. Gravar no evento do ingresso jogaria a recusa no
    # painel de um show em que ninguém tentou nada — e vazaria, pelo contador, a
    # existência de um ingresso de outro evento para a portaria que o AD-7 proíbe
    # de saber disso.
    #
    # Indexado porque é o `where` de toda contagem. **Sem índice composto com
    # `resultado`**: são quatro valores distintos numa tabela que cresce por show,
    # e o `GROUP BY` sobre o recorte de um evento já é barato.
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evento.id"), nullable=False, index=True
    )

    # Quem estava na porta. Sem `ondelete`, o mesmo tratamento de
    # `ingresso.validado_por`: apagar uma conta que já validou é recusado pelo
    # Postgres. Trilha de auditoria que some quando a conta some não é trilha.
    portaria_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )

    # Nulo nos dois `INVALIDO`, preenchido nos outros três. **Sem índice**: nenhum
    # `where` do projeto filtra validação por ingresso — a disciplina desde a
    # Story 2.3 é indexar a chave que é lida, não todas.
    ingresso_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ingresso.id"), nullable=True
    )

    resultado: Mapped[str] = mapped_column(String(20), nullable=False)

    # ⚠️ **Escrito em Python, e não por `server_default=func.now()` como o
    # `usuario.criado_em`.** O `now()` do Postgres é o instante de **início da
    # transação**, não o do `INSERT`: várias linhas gravadas na mesma transação
    # saem com o carimbo idêntico, e uma trilha de auditoria cujas linhas não se
    # ordenam entre si responde pior a pergunta para a qual ela existe — "o que
    # aconteceu nesta porta, e em que ordem?". Em `usuario` isso nunca apareceu
    # porque conta se cria uma por transação.
    #
    # De quebra, é o mesmo relógio que escreve `ingresso.usado_em` duas linhas
    # adiante no `validar`. Os dois registram o mesmo acontecimento; lê-los de
    # fontes diferentes seria pedir que discordassem por alguns milissegundos.
    #
    # TIMESTAMPTZ em UTC (AD-11), como todo tempo do projeto.
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ⚠️ **Nenhum `relationship`**, aqui nem do outro lado — precedente de
    # `Ingresso` e de `Reserva`. Um `Evento.validacoes` criado agora convidaria a
    # próxima pessoa a contar linhas desta tabela para derivar disponibilidade ou
    # entradas, e as duas coisas têm dono: `setor.vendidos` (AD-13) e
    # `ingresso.usado_em` (AD-6).
