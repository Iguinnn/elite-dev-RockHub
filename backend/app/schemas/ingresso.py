"""Schema de saída de `GET /ingressos` — a lista de "Meus ingressos" (Story 4.1).

**Um schema próprio, e não o `IngressoSaida` de `schemas/reserva.py`.** Aquele
é o canhoto de uma compra — nasce com `codigo` e `titular_nome`, os dois
campos que a tela `/ingressos` não desenha, e sem `evento_id` nem `usado_em`,
os dois que ela precisa. Reusá-lo faria o `codigo` (o segredo do QR)
atravessar a rede para uma tela que não o mostra: payload sem leitor, exigindo
inteligência de quem lê para saber quais dos campos ignorar.

`IngressoDetalhe` mora no mesmo arquivo, mas nasce só na Story 4.2 — é o
canhoto cheio, com `codigo`. Este módulo cresce junto com as duas rotas que a
techspec do grupo descreve.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IngressoNaLista(BaseModel):
    """Um ingresso como a tela `/ingressos` o vê — sem `codigo` nem `titular_nome`.

    **`usado_em` é `datetime | None`, e é ele que separa os dois blocos da
    tela**: `NULL` cai em *Ativos*, preenchido cai em *Utilizados*. A API não
    devolve `{ativos, utilizados}` nomeados — a lista chega chapada e quem
    corta em dois blocos é a tela, o mesmo molde do `Meus eventos` da 2.6.

    `evento_id` entra porque o item leva ao show (`/eventos/{evento_id}`);
    nenhum dos dois campos que faltam — `codigo`, `titular_nome` — é desenhado
    aqui: o primeiro é o canhoto (`/ingressos/{id}`, Story 4.2), o segundo não
    tem leitor nesta tela.

    **Sem `from_attributes`**: `evento_nome`, `evento_data_hora`, `evento_local`
    e `setor_nome` não são atributos de `Ingresso` — o modelo não tem
    `relationship` para `Evento` nem para `Setor` (mesma disciplina de
    `Reserva`), e quem os monta é `services/ingresso.py`.
    """

    id: UUID
    evento_id: UUID
    evento_nome: str
    evento_data_hora: datetime
    evento_local: str
    setor_nome: str
    usado_em: datetime | None


class IngressoDetalhe(BaseModel):
    """O canhoto cheio — `GET /ingressos/{id}` (Story 4.2), o que vira QR.

    **`codigo` entra aqui, e só aqui.** É `ID.ASSINATURA` (AD-5), montado a
    partir da coluna `assinatura` sem recalcular — o mesmo aviso do
    `_ingressos()` de `services/reserva.py`: a validação da portaria é quem
    sempre recalcula (AD-5), esta rota só monta o texto que vira QR.

    **`usado_em` entra também aqui**, e não só na lista: um canhoto já
    utilizado que parecesse válido mandaria alguém para a fila da porta à
    toa. A tela não desenha um veredito — isso é a Epic 5 —, mas não pode
    fingir que o ingresso ainda vale.

    `evento_cidade` entra e não entrava em `IngressoNaLista`: a ficha do
    canhoto tem espaço para "casa e cidade" por extenso; a fila da lista já
    aperta com quatro colunas.

    **Sem `from_attributes`**, pelo mesmo motivo do `IngressoNaLista`: nenhum
    dos campos de `Evento`/`Setor` é atributo de `Ingresso`, e `codigo` não é
    coluna nenhuma — quem monta os três é `services/ingresso.py`.
    """

    id: UUID
    evento_nome: str
    evento_data_hora: datetime
    evento_local: str
    evento_cidade: str | None
    setor_nome: str
    titular_nome: str
    codigo: str
    usado_em: datetime | None
