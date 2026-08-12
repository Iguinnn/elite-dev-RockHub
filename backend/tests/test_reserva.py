"""Invariantes de `Reserva` e `ItemReserva` que o banco garante, não o Python.

Nenhum destes testes passa por rota, service ou schema — nada disso existe
ainda, e não é para existir: a Story 3.5 entrega o schema, e reservar é a 3.6.
O que está sob prova é o formato do banco: o `CHECK` dos cinco estados, as três
constraints de quantidade e dinheiro, a unicidade por reserva, os quatro
`ondelete` e — principalmente — as **duas transições condicionais do AD-4**,
provadas aqui pelo mesmo motivo que o `UPDATE` do AD-3 foi provado na Story
2.3: uma tabela que nasce sem provar a operação que justifica sua forma é uma
tabela que ninguém sabe se está certa.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario

DATA_DO_SHOW = datetime(2026, 12, 1, 21, 0, tzinfo=timezone.utc)

# Os dois e-mails precisam ser diferentes: a `fabricar_usuario` do
# `conftest.py` tem e-mail padrão fixo, e todo teste daqui grava duas contas.
EMAIL_ORGANIZADOR = "organizador@exemplo.com"
EMAIL_CLIENTE = "cliente@exemplo.com"


def _evento(sessao: Session, organizador: Usuario, **campos: Any) -> Evento:
    """Grava um evento com os campos obrigatórios preenchidos.

    Local, e não no `conftest.py`: a convenção da suíte é helper por módulo,
    moldado para o que aquele arquivo prova. O `conftest.py` guarda
    infraestrutura (sessão, cliente HTTP, fábrica de usuário), não fixture de
    domínio.
    """
    valores: dict[str, Any] = {
        "organizador_id": organizador.id,
        "nome": "Noite de Rock",
        "data_hora": DATA_DO_SHOW,
        "local": "Casa de Shows",
    }
    valores.update(campos)

    evento = Evento(**valores)
    sessao.add(evento)
    sessao.flush()
    return evento


def _setor(sessao: Session, evento: Evento, **campos: Any) -> Setor:
    valores: dict[str, Any] = {
        "evento_id": evento.id,
        "nome": "Pista",
        "capacidade": 100,
        "preco_centavos": 12000,
    }
    valores.update(campos)

    setor = Setor(**valores)
    sessao.add(setor)
    sessao.flush()
    return setor


def _reserva(
    sessao: Session, cliente: Usuario, evento: Evento, **campos: Any
) -> Reserva:
    """Uma reserva `PENDENTE` com o prazo de 10 minutos do AD-4.

    O prazo é calculado com `datetime.now(timezone.utc)`, nunca com
    `datetime.now()` sem fuso: a coluna é `TIMESTAMPTZ` e o psycopg recusa
    comparar ingênuo com consciente.
    """
    valores: dict[str, Any] = {
        "cliente_id": cliente.id,
        "evento_id": evento.id,
        "estado": EstadoReserva.PENDENTE.value,
        "expira_em": datetime.now(timezone.utc) + timedelta(minutes=10),
        "total_centavos": 24000,
    }
    valores.update(campos)

    reserva = Reserva(**valores)
    sessao.add(reserva)
    sessao.flush()
    return reserva


def _contas(fabricar_usuario: Any) -> tuple[Usuario, Usuario]:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, EMAIL_ORGANIZADOR)
    cliente = fabricar_usuario(PapelUsuario.CLIENTE, EMAIL_CLIENTE)
    return organizador, cliente


def test_reserva_gera_uuid_e_criado_em_automaticamente(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)

    reserva = _reserva(sessao, cliente, evento)
    sessao.refresh(reserva)

    assert reserva.id is not None
    assert reserva.criado_em is not None
    assert reserva.criado_em.tzinfo is not None
    assert reserva.expira_em.tzinfo is not None
    assert reserva.estado == EstadoReserva.PENDENTE.value


def test_estado_fora_dos_cinco_valores_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Quem recusa é o **banco**, não uma validação de Python.

    O enum em `app/models/reserva.py` é conveniência de quem escreve; a
    garantia é o `ck_reserva_estado_valido`, e é por isso que este teste grava
    a string crua em vez de passar pelo enum.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)

    sessao.add(
        Reserva(
            cliente_id=cliente.id,
            evento_id=evento.id,
            estado="QUALQUERCOISA",
            expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
            total_centavos=24000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_os_cinco_estados_do_ad4_sao_aceitos(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Inclusive `CANCELADA`, que ainda não tem ninguém que a escreva.

    O valor existe no schema porque o AD-4 o fixa, e é ele que torna o corte do
    cancelamento reversível sem migração.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)

    for estado in EstadoReserva:
        reserva = _reserva(sessao, cliente, evento, estado=estado.value)
        assert reserva.id is not None


def test_transicao_condicional_para_paga_afeta_uma_linha_e_depois_zero(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """AD-4: transição sempre condicionada ao estado anterior.

    Zero linhas na segunda vez é o sinal de "alguém chegou primeiro" — não uma
    exceção. É este zero que faz *reprocessar um pagamento aprovado não gerar
    ingresso novo* (AD-14) ser verdade por construção, e não por um `if`. Quem
    executa isto é a Story 3.8; provo aqui, na story em que a tabela nasce,
    pelo mesmo motivo do `UPDATE` do AD-3 na 2.3.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    reserva = _reserva(sessao, cliente, evento)

    sql = text(
        "UPDATE reserva SET estado = 'PAGA' "
        " WHERE id = :id AND estado = 'PENDENTE'"
    )

    primeira = sessao.execute(sql, {"id": reserva.id})
    assert primeira.rowcount == 1

    repetida = sessao.execute(sql, {"id": reserva.id})
    assert repetida.rowcount == 0


def test_colheita_da_expiracao_so_alcanca_a_reserva_vencida(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """A forma da expiração preguiçosa da Story 3.7 (AD-4).

    Prova de quebra que `expira_em` é comparável com o `now()` do **Postgres**
    sem conversão de fuso pelo caminho (AD-11) — o `now()` de dentro do
    `UPDATE` é o do banco, que é o certo para a colheita.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    agora = datetime.now(timezone.utc)
    vencida = _reserva(sessao, cliente, evento, expira_em=agora - timedelta(minutes=1))
    ainda_vale = _reserva(
        sessao, cliente, evento, expira_em=agora + timedelta(minutes=10)
    )

    sql = text(
        "UPDATE reserva SET estado = 'EXPIRADA' "
        " WHERE id = :id AND estado = 'PENDENTE' AND expira_em < now()"
    )

    colhida = sessao.execute(sql, {"id": vencida.id})
    assert colhida.rowcount == 1

    poupada = sessao.execute(sql, {"id": ainda_vale.id})
    assert poupada.rowcount == 0


def test_total_negativo_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)

    sessao.add(
        Reserva(
            cliente_id=cliente.id,
            evento_id=evento.id,
            estado=EstadoReserva.PENDENTE.value,
            expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
            total_centavos=-1,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("quantidade", [0, -1])
def test_quantidade_nao_positiva_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any, quantidade: int
) -> None:
    """Item de quantidade zero consome estoque nenhum e aparece no checkout."""
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)
    reserva = _reserva(sessao, cliente, evento)

    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=setor.id,
            quantidade=quantidade,
            preco_unitario_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_preco_unitario_negativo_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)
    reserva = _reserva(sessao, cliente, evento)

    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=setor.id,
            quantidade=2,
            preco_unitario_centavos=-1,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_dois_itens_do_mesmo_setor_na_mesma_reserva_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Um alvo só por setor para o `UPDATE` de estoque da Story 3.6."""
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)
    reserva = _reserva(sessao, cliente, evento)

    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=setor.id,
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    sessao.flush()

    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=setor.id,
            quantidade=1,
            preco_unitario_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_o_mesmo_setor_em_outra_reserva_e_aceito(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """A unicidade é por reserva, não global: o setor continua à venda."""
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)
    primeira = _reserva(sessao, cliente, evento)
    segunda = _reserva(sessao, cliente, evento)

    sessao.add(
        ItemReserva(
            reserva_id=primeira.id,
            setor_id=setor.id,
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    item_da_segunda = ItemReserva(
        reserva_id=segunda.id,
        setor_id=setor.id,
        quantidade=1,
        preco_unitario_centavos=12000,
    )
    sessao.add(item_da_segunda)
    sessao.flush()

    assert item_da_segunda.id is not None


def test_apagar_a_reserva_leva_os_itens_junto(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """`ON DELETE CASCADE` no banco e `passive_deletes` no ORM, concordando.

    Apagar **pela sessão** é o ponto: com um `relationship` comum, o SQLAlchemy
    tentaria `UPDATE item_reserva SET reserva_id = NULL` antes do `DELETE` e
    estouraria no `NOT NULL` sem nunca chegar ao `CASCADE` da migração. Apagar
    por SQL cru passaria verde com o ORM errado.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    pista = _setor(sessao, evento, nome="Pista")
    camarote = _setor(sessao, evento, nome="Camarote", capacidade=20)
    reserva = _reserva(sessao, cliente, evento)
    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=pista.id,
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=camarote.id,
            quantidade=1,
            preco_unitario_centavos=40000,
        )
    )
    sessao.flush()
    reserva_id = reserva.id

    sessao.delete(reserva)
    sessao.flush()

    restantes = sessao.execute(
        text("SELECT count(*) FROM item_reserva WHERE reserva_id = :id"),
        {"id": reserva_id},
    ).scalar_one()
    assert restantes == 0


def test_apagar_evento_com_reserva_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """Apagar show vendido tem que doer — a chave estrangeira recusa.

    É aqui que o `ON DELETE CASCADE` de `setor` deixa de valer: ele continua
    levando os setores junto num evento **sem** reserva (provado em
    `test_evento.py`), e para no `item_reserva` assim que existe uma venda.
    """
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    _setor(sessao, evento)
    _reserva(sessao, cliente, evento)

    sessao.delete(evento)
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_apagar_setor_com_item_reservado_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)
    reserva = _reserva(sessao, cliente, evento)
    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=setor.id,
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    sessao.flush()

    sessao.delete(setor)
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_apagar_o_cliente_que_reservou_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    """O mesmo tratamento que `evento.organizador_id` dá a quem publicou."""
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    _reserva(sessao, cliente, evento)

    sessao.delete(cliente)
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_reserva_com_cliente_inexistente_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, _ = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)

    sessao.add(
        Reserva(
            cliente_id=uuid.uuid4(),
            evento_id=evento.id,
            estado=EstadoReserva.PENDENTE.value,
            expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
            total_centavos=24000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_reserva_com_evento_inexistente_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    _, cliente = _contas(fabricar_usuario)

    sessao.add(
        Reserva(
            cliente_id=cliente.id,
            evento_id=uuid.uuid4(),
            estado=EstadoReserva.PENDENTE.value,
            expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
            total_centavos=24000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_item_com_reserva_inexistente_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, _ = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    setor = _setor(sessao, evento)

    sessao.add(
        ItemReserva(
            reserva_id=uuid.uuid4(),
            setor_id=setor.id,
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_item_com_setor_inexistente_levanta_integrity_error(
    sessao: Session, fabricar_usuario: Any
) -> None:
    organizador, cliente = _contas(fabricar_usuario)
    evento = _evento(sessao, organizador)
    reserva = _reserva(sessao, cliente, evento)

    sessao.add(
        ItemReserva(
            reserva_id=reserva.id,
            setor_id=uuid.uuid4(),
            quantidade=2,
            preco_unitario_centavos=12000,
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()
