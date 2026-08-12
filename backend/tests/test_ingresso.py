"""Emissão do ingresso e o código não forjável (Story 3.9) — AD-5 e AD-14.

Precisa do Compose no ar: os ingressos são contados no banco, e não no corpo da
resposta.

⚠️ **A garantia mais pontuada do desafio mora em duas linhas de código, e as
duas são fáceis de quebrar sem quebrar nenhum teste ingênuo:**

- **A emissão só acontece depois do `_transicionar` vencer** (AD-14). Movida
  para antes, ou protegida por um `if ja_tem_ingresso`, ela continua passando em
  todo teste sequencial e emite ingresso duplo no reprocessamento.
- **A assinatura é recalculada, nunca comparada com a coluna** (AD-5). Comparar
  com o que está gravado dá o mesmo resultado em todo caso feliz e transforma o
  banco em oráculo de assinatura.

**O teste de forja é o que mais importa aqui**: ele altera um caractere da
assinatura e exige que a verificação falhe **sem tocar o banco** — por isso ele
chama `conferir_codigo` direto, sem sessão nenhuma.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.seguranca import (
    SEPARADOR_DO_CODIGO,
    assinar_ingresso,
    conferir_codigo,
    gerar_nonce,
    montar_codigo,
)
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario

CARTAO_APROVA = "4111111111111111"
CARTAO_RECUSA = "4111111111110002"


def _daqui_a(dias: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=dias)


def _evento_publicado(
    sessao: Session,
    organizador: Usuario,
    *,
    setores: list[tuple[str, int, int, int]] | None = None,
) -> Evento:
    if setores is None:
        setores = [("Pista", 800, 0, 12000)]

    evento = Evento(
        organizador_id=organizador.id,
        nome="Baco Exu do Blues",
        data_hora=_daqui_a(30),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc),
        setores=[
            Setor(nome=n, capacidade=c, vendidos=v, preco_centavos=p)
            for n, c, v, p in setores
        ],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


def _reserva(
    sessao: Session,
    dono: Usuario,
    evento: Evento,
    *itens: tuple[Setor, int],
) -> Reserva:
    for setor, quantidade in itens:
        setor.vendidos += quantidade

    reserva = Reserva(
        cliente_id=dono.id,
        evento_id=evento.id,
        estado=EstadoReserva.PENDENTE.value,
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
        total_centavos=sum(s.preco_centavos * q for s, q in itens),
        itens=[
            ItemReserva(
                setor_id=setor.id,
                quantidade=quantidade,
                preco_unitario_centavos=setor.preco_centavos,
            )
            for setor, quantidade in itens
        ],
    )
    sessao.add(reserva)
    sessao.flush()
    sessao.refresh(reserva)
    return reserva


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    assert (
        cliente.post(
            "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
        ).status_code
        == 200
    )


def _corpo(numero: str = CARTAO_APROVA, nome: str = "Igor Duarte") -> dict:
    return {
        "nome": nome,
        "email": "igor@exemplo.com",
        "cpf": "123.456.789-01",
        "telefone": "(11) 98888-7777",
        "meio": "CARTAO",
        "numero_cartao": numero,
        "nome_no_cartao": "IGOR D VIEIRA",
        "validade": "12/30",
        "cvv": "123",
    }


def _quantos_ingressos(sessao: Session, reserva: Reserva) -> int:
    return sessao.scalar(
        select(func.count()).select_from(Ingresso).where(
            Ingresso.reserva_id == reserva.id
        )
    )


# --------------------------------------------------------------------------- #
# AC2 — um ingresso por unidade, na transação do pagamento
# --------------------------------------------------------------------------- #


def test_nasce_um_ingresso_por_unidade_comprada(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`2 × Pista` são **dois** ingressos, não um com quantidade 2.

    É essa multiplicidade que permite validar um e o outro não — o
    comportamento inteiro da Epic 5 depende dela.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i1@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i1@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 2))
    _entrar(cliente, comprador)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 200
    assert _quantos_ingressos(sessao, reserva) == 2
    assert len(resposta.json()["ingressos"]) == 2


def test_cada_ingresso_tem_id_e_codigo_proprios(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Dois canhotos do mesmo setor não podem compartilhar código.

    O `nonce` por ingresso é o que garante isso mesmo com o mesmo segredo, o
    mesmo evento e o mesmo setor.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i2@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i2@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 3))
    _entrar(cliente, comprador)

    ingressos = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo()
    ).json()["ingressos"]

    assert len({i["id"] for i in ingressos}) == 3
    assert len({i["codigo"] for i in ingressos}) == 3

    gravados = sessao.scalars(
        select(Ingresso).where(Ingresso.reserva_id == reserva.id)
    ).all()
    assert len({g.nonce for g in gravados}) == 3
    assert len({g.assinatura for g in gravados}) == 3


def test_dois_setores_geram_ingressos_do_setor_certo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i3@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i3@exemplo.com")
    evento = _evento_publicado(
        sessao,
        organizador,
        setores=[("Camarote", 50, 0, 30000), ("Pista", 800, 0, 12000)],
    )
    por_nome = {s.nome: s for s in evento.setores}
    reserva = _reserva(
        sessao, comprador, evento, (por_nome["Pista"], 2), (por_nome["Camarote"], 1)
    )
    _entrar(cliente, comprador)

    ingressos = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo()
    ).json()["ingressos"]

    assert [i["setor_nome"] for i in ingressos].count("Pista") == 2
    assert [i["setor_nome"] for i in ingressos].count("Camarote") == 1


def test_o_titular_e_o_nome_digitado_no_checkout(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Decisão do Igor: o campo vem preenchido com o nome da conta, e é editável.

    Quem compra pode estar comprando para outra pessoa — então o que vale é o
    que foi digitado, não `usuario.nome`.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i4@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i4@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)

    ingressos = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(nome="Fulana de Tal")
    ).json()["ingressos"]

    # A conta se chama "Alguém" (fixture) — o ingresso, não.
    assert ingressos[0]["titular_nome"] == "Fulana de Tal"
    assert comprador.nome != "Fulana de Tal"


def test_recusa_nao_emite_ingresso(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Só `PAGA` emite (AD-4). O `402` não pode deixar rastro."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i5@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i5@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 2))
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(numero=CARTAO_RECUSA)
    )

    assert resposta.status_code == 402
    assert _quantos_ingressos(sessao, reserva) == 0


# --------------------------------------------------------------------------- #
# AC4 — pagamento reprocessado não cria ingresso adicional (AD-14)
# --------------------------------------------------------------------------- #


def test_pagar_de_novo_nao_emite_ingresso_adicional(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O teste que a emissão dentro do `if` existe para fazer passar.

    Se a emissão saísse de dentro do ramo que vence o `_transicionar`, este
    teste veria quatro ingressos onde deve haver dois — e nenhum outro teste do
    projeto notaria.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i6@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i6@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 2))
    _entrar(cliente, comprador)

    assert cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo()).status_code == 200
    assert _quantos_ingressos(sessao, reserva) == 2

    segunda = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert segunda.status_code == 409
    assert _quantos_ingressos(sessao, reserva) == 2


def test_os_ingressos_sobrevivem_a_recarregar_a_pagina(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`GET /reservas/{id}` devolve os mesmos canhotos do `POST`.

    A tela da reserva paga precisa sobreviver a `F5`, e quem a serve é o `GET`.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i7@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i7@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 2))
    _entrar(cliente, comprador)

    do_pagamento = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo()
    ).json()["ingressos"]
    da_leitura = cliente.get(f"/reservas/{reserva.id}").json()["ingressos"]

    assert [i["codigo"] for i in do_pagamento] == [i["codigo"] for i in da_leitura]


def test_reserva_pendente_nao_tem_ingresso_no_contrato(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A lista existe sempre e é vazia até o pagamento — a tela ramifica pelo
    `estado`, nunca pelo tamanho dela."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i8@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i8@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)

    corpo = cliente.get(f"/reservas/{reserva.id}").json()

    assert corpo["estado"] == EstadoReserva.PENDENTE.value
    assert corpo["ingressos"] == []


# --------------------------------------------------------------------------- #
# AC3 e AC5 — o código é `ID.ASSINATURA`, e assinatura adulterada não passa
# --------------------------------------------------------------------------- #


def test_o_codigo_tem_o_formato_id_ponto_assinatura(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i9@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i9@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)

    codigo = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo()
    ).json()["ingressos"][0]["codigo"]

    id_bruto, separador, assinatura = codigo.partition(SEPARADOR_DO_CODIGO)
    assert separador == SEPARADOR_DO_CODIGO
    # A primeira metade é o id do ingresso, e ele existe no banco.
    assert sessao.get(Ingresso, UUID(id_bruto)) is not None
    # base64url de SHA-256 sem padding: 43 caracteres, e nenhum `=`.
    assert len(assinatura) == 43
    assert "=" not in assinatura


def test_assinatura_adulterada_falha_sem_consultar_o_banco() -> None:
    """⚠️ **Sem fixture de sessão, e a ausência dela é o teste** (AD-5).

    A verificação recalcula o HMAC e compara; ela não conhece o banco, não
    recebe sessão e não teria como consultar nada. Se um dia alguém trocar o
    recálculo por um `SELECT ... WHERE assinatura = :valor`, este teste para de
    compilar antes de parar de passar.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()
    codigo = montar_codigo(ingresso_id, assinar_ingresso(ingresso_id, evento_id, nonce))

    assert conferir_codigo(codigo, evento_id, nonce) is True

    # Um caractere trocado na assinatura — o `A`/`B` cobre o caso de o último já
    # ser `A`.
    adulterado = codigo[:-1] + ("B" if codigo[-1] == "A" else "A")
    assert conferir_codigo(adulterado, evento_id, nonce) is False


def test_o_codigo_nao_vale_para_outro_evento_nem_outro_nonce() -> None:
    """Os três componentes entram na conta (AD-5), e trocar qualquer um invalida."""
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()
    codigo = montar_codigo(ingresso_id, assinar_ingresso(ingresso_id, evento_id, nonce))

    assert conferir_codigo(codigo, uuid4(), nonce) is False
    assert conferir_codigo(codigo, evento_id, gerar_nonce()) is False
    # E o id: o mesmo par (evento, nonce) com outro id é outro código.
    outro = montar_codigo(uuid4(), assinar_ingresso(uuid4(), evento_id, nonce))
    assert conferir_codigo(outro, evento_id, nonce) is False


def test_codigo_malformado_nao_estoura(
) -> None:
    """Lixo entra, `False` sai — nunca exceção.

    A portaria vai alimentar isto com o que a câmera ler, e o que a câmera lê
    nem sempre é um código deste sistema.
    """
    evento_id = uuid4()
    nonce = gerar_nonce()

    for lixo in ("", "sem-separador", ".", "nao-e-uuid.assinatura", f"{uuid4()}."):
        assert conferir_codigo(lixo, evento_id, nonce) is False


def test_ingresso_de_outra_pessoa_nao_aparece(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O canhoto é o passe de entrada: ele só sai pela reserva de quem o comprou."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i10@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i10@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)
    assert cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo()).status_code == 200

    cliente.cookies.clear()
    intruso = fabricar_usuario(PapelUsuario.CLIENTE, "intruso-i@exemplo.com")
    _entrar(cliente, intruso)

    assert cliente.get(f"/reservas/{reserva.id}").status_code == 404
