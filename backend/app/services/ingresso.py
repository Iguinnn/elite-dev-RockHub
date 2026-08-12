"""O ingresso como agregado próprio: a leitura de "Meus ingressos" — Story 4.1.

⚠️ **Este módulo lê, e da Story 4.3 em diante escreve `share_token`. Ele nunca
cria ingresso.** A emissão é do `services/reserva.py`, dentro da transação que
marca a reserva `PAGA` (AD-14) — mesmo aviso que aquele arquivo carrega sobre
si, em espelho. Um `INSERT INTO ingresso` fora daquela transação quebraria a
garantia inteira da Epic 3.

**Por que arquivo próprio, e não mais uma função em `services/reserva.py`.**
O ingresso tem vida depois de a reserva sair de cena — é lido por várias
compras de uma vez (`GET /ingressos`), compartilhado por link (Epic 4) e
validado na porta (Epic 5) — e `reserva.py` já passa de 800 linhas cobrindo o
agregado dele. Agrupar por agregado, não por arquivo que cresce.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.schemas.ingresso import IngressoNaLista


def listar(sessao: Session, cliente: Usuario) -> list[IngressoNaLista]:
    """Todos os ingressos de todas as reservas pagas de quem está na sessão.

    **`join(Reserva)`, e não um `cliente_id` em `ingresso`** (techspec da 4.1).
    `reserva_id` já é indexado desde a Story 3.9 exatamente para este `where`;
    uma coluna atalho duplicaria o dono em duas tabelas, com o dia em que
    discordam já marcado.

    **Sem filtro por `reserva.estado`.** Ingresso só nasce dentro da transação
    que marca a reserva `PAGA` (AD-14) — o estado da reserva não é uma segunda
    condição desta consulta, é uma consequência de a linha existir.

    Ordenado por `evento.data_hora` **crescente**: o próximo show primeiro. A
    tela corta em *Ativos*/*Utilizados* por `usado_em IS NULL`; esta função
    não sabe de blocos, só devolve a lista inteira, chapada — o mesmo molde do
    `listar_meus_eventos` da 2.6.

    Lista vazia é resposta legítima, nunca uma falha: quem nunca comprou tem
    zero ingressos, e isso não é diferente de ter zero eventos publicados.
    """
    linhas = sessao.execute(
        select(Ingresso, Evento, Setor)
        .join(Reserva, Reserva.id == Ingresso.reserva_id)
        .join(Evento, Evento.id == Ingresso.evento_id)
        .join(Setor, Setor.id == Ingresso.setor_id)
        .where(Reserva.cliente_id == cliente.id)
        .order_by(Evento.data_hora)
    ).all()

    return [
        IngressoNaLista(
            id=ingresso.id,
            evento_id=evento.id,
            evento_nome=evento.nome,
            evento_data_hora=evento.data_hora,
            evento_local=evento.local,
            setor_nome=setor.nome,
            usado_em=ingresso.usado_em,
        )
        for ingresso, evento, setor in linhas
    ]
