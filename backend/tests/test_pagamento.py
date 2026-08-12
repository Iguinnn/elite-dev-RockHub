"""`POST /reservas/{id}/pagamento` (Story 3.8) — aprovação, recusa e o prazo.

Precisa do Compose no ar: as transições de estado e a devolução de estoque são
lidas do banco, nunca do corpo da resposta.

⚠️ **Este arquivo prova duas coisas que passariam despercebidas num teste
sequencial ingênuo:**

- **A recusa e a expiração precisam sobreviver ao `raise`.** No `criar()` da 3.6,
  levantar `ErroDeDominio` é o mecanismo de desfazer tudo; aqui, dois caminhos de
  recusa gravam de propósito **antes** de responder erro. Se o `commit` sumir do
  service, o estoque simplesmente nunca volta de uma recusa — e o corpo `402`
  continua idêntico. É por isso que todo teste de recusa aqui confere
  `setor.vendidos` no banco, e não só o status.
- **O AD-10 é sobre direção de dependência**, e a forma de provar isso é trocar o
  gateway por um dublê que não é o `PagamentoSimulado` e ver a rota funcionar.

**Helpers locais**, como o resto da suíte.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.evento import Evento, Setor
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.services.pagamento import Autorizacao, MeioDePagamento, obter_gateway

# Um cartão que aprova e um que recusa — o final `0002` é o do AD-10, e é o que
# o README manda o avaliador digitar.
CARTAO_APROVA = "4111111111111111"
CARTAO_RECUSA = "4111111111110002"

# O que a mesma lista de palavras proibidas da 3.6 continua recusando: o
# inventário. `quantidade` e os campos de dinheiro seguem legítimos.
PALAVRAS_DE_ESTOQUE = ("capacidade", "vendidos", "proporcao", "disponibilidade")

# Os campos do comprador **não** voltam na resposta — nem para conferência.
PALAVRAS_DO_COMPRADOR = ("cpf", "telefone", "email", "cartao", "cvv", "validade")


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
    setor: Setor,
    quantidade: int = 2,
    *,
    vencida: bool = False,
    estado: EstadoReserva = EstadoReserva.PENDENTE,
) -> Reserva:
    """Uma reserva gravada pelo ORM, com o estoque já consumido por ela.

    ⚠️ **O `setor.vendidos` é mexido à mão junto**, porque a reserva criada assim
    não passa pelo `UPDATE` do `criar()`. Sem isso, a devolução da recusa levaria
    o contador abaixo de zero e o teste provaria o contrário do que quer.
    """
    setor.vendidos += quantidade

    reserva = Reserva(
        cliente_id=dono.id,
        evento_id=evento.id,
        estado=estado.value,
        expira_em=(
            datetime.now(timezone.utc)
            + (timedelta(minutes=-1) if vencida else timedelta(minutes=10))
        ),
        total_centavos=setor.preco_centavos * quantidade,
        itens=[
            ItemReserva(
                setor_id=setor.id,
                quantidade=quantidade,
                preco_unitario_centavos=setor.preco_centavos,
            )
        ],
    )
    sessao.add(reserva)
    sessao.flush()
    sessao.refresh(reserva)
    return reserva


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _corpo(meio: str = "CARTAO", numero: str = CARTAO_APROVA, **trocas) -> dict:
    """O corpo do checkout, com os campos do comprador sempre presentes."""
    corpo = {
        "nome": "Igor Duarte",
        "email": "igor@exemplo.com",
        "cpf": "123.456.789-01",
        "telefone": "(11) 98888-7777",
        "meio": meio,
    }
    if meio == "CARTAO":
        corpo |= {
            "numero_cartao": numero,
            "nome_no_cartao": "IGOR D VIEIRA",
            "validade": "12/30",
            "cvv": "123",
        }
    return corpo | trocas


def _cenario(
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    sufixo: str,
    **kwargs,
) -> tuple[Usuario, Setor, Reserva]:
    """Organizador, evento de um setor, comprador e a reserva dele."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, f"org-p{sufixo}@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, f"cli-p{sufixo}@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    setor = evento.setores[0]
    reserva = _reserva(sessao, comprador, evento, setor, **kwargs)
    return comprador, setor, reserva


# --------------------------------------------------------------------------- #
# AC1 — cartão comum aprova
# --------------------------------------------------------------------------- #


def test_cartao_comum_aprova_e_a_reserva_vira_paga(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "1")
    _entrar(cliente, comprador)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == EstadoReserva.PAGA.value

    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.PAGA.value
    # O estoque **não** volta numa aprovação: o lugar tem dono agora.
    assert sessao.get(Setor, setor.id).vendidos == 2


def test_pix_aprova_sem_nenhum_campo_de_cartao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O atalho do avaliador: o botão "cobrança paga" manda exatamente isto."""
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "2")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(meio="PIX")
    )

    assert resposta.status_code == 200
    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.PAGA.value


# --------------------------------------------------------------------------- #
# AC2 — o cartão terminado em 0002 é recusado, e o estoque volta
# --------------------------------------------------------------------------- #


def test_cartao_final_0002_recusa_com_402_e_devolve_o_estoque(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O `vendidos` é o que prova o `commit` antes do `raise`.

    Sem ele no service, o status continua `402` e o estoque nunca volta — a
    falha mais silenciosa desta story.
    """
    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "3")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(numero=CARTAO_RECUSA)
    )

    assert resposta.status_code == 402
    assert resposta.json()["erro"]["codigo"] == "PAGAMENTO_RECUSADO"

    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.RECUSADA.value
    assert sessao.get(Setor, setor.id).vendidos == 0


def test_a_mascara_do_cartao_nao_muda_o_veredito(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`4111 1111 1111 0002` é o mesmo cartão que `4111111111110002`.

    Sem a normalização, o mesmo número aprovaria ou recusaria conforme quem
    digitou tivesse usado espaço — e a recusa que o enunciado pontua viraria
    loteria.
    """
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "4")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento",
        json=_corpo(numero="4111 1111 1111 0002"),
    )

    assert resposta.status_code == 402


# --------------------------------------------------------------------------- #
# AC1 da Story 3.7 — pagar reserva vencida
# --------------------------------------------------------------------------- #


def test_pagar_reserva_vencida_expira_devolve_estoque_e_nao_cobra(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Fecha a janela que o commit da Story 3.7 deixou aberta de propósito."""
    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "5", vencida=True)
    _entrar(cliente, comprador)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "RESERVA_EXPIRADA"

    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.EXPIRADA.value
    assert sessao.get(Setor, setor.id).vendidos == 0


def test_reserva_ja_expirada_responde_o_mesmo_codigo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Quem chegou depois da colheita vê a mesma frase de quem a disparou."""
    comprador, _, reserva = _cenario(
        sessao, fabricar_usuario, "6", estado=EstadoReserva.EXPIRADA
    )
    _entrar(cliente, comprador)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "RESERVA_EXPIRADA"


# --------------------------------------------------------------------------- #
# AD-14 — reprocessar não faz nada de novo
# --------------------------------------------------------------------------- #


def test_pagar_de_novo_uma_reserva_paga_nao_muda_nada(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A transição condicionada ao estado anterior é a garantia (AD-4, AD-14).

    Este é o teste que a Story 3.9 herda pronto: onde hoje "nada muda", lá será
    "nenhum ingresso adicional nasce" — e pelo mesmo `rowcount`.
    """
    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "7")
    _entrar(cliente, comprador)

    assert cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo()).status_code == 200

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "RESERVA_NAO_PENDENTE"
    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.PAGA.value
    # Nem devolveu, nem consumiu de novo.
    assert sessao.get(Setor, setor.id).vendidos == 2


def test_pagar_reserva_recusada_nao_devolve_estoque_de_novo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Insistir numa recusa não pode fazer o contador andar para trás."""
    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "8")
    _entrar(cliente, comprador)

    assert (
        cliente.post(
            f"/reservas/{reserva.id}/pagamento", json=_corpo(numero=CARTAO_RECUSA)
        ).status_code
        == 402
    )
    assert sessao.get(Setor, setor.id).vendidos == 0

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(numero=CARTAO_RECUSA)
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "RESERVA_NAO_PENDENTE"
    assert sessao.get(Setor, setor.id).vendidos == 0


# --------------------------------------------------------------------------- #
# Quem pode pagar o quê
# --------------------------------------------------------------------------- #


def test_reserva_de_outra_pessoa_responde_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Nunca `403`: distinguir transformaria a rota num oráculo de UUIDs."""
    _, setor, reserva = _cenario(sessao, fabricar_usuario, "9")
    intruso = fabricar_usuario(PapelUsuario.CLIENTE, "intruso@exemplo.com")
    _entrar(cliente, intruso)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "RESERVA_NAO_ENCONTRADA"
    sessao.expire(reserva)
    assert reserva.estado == EstadoReserva.PENDENTE.value
    assert sessao.get(Setor, setor.id).vendidos == 2


def test_sem_sessao_responde_401(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    _, _, reserva = _cenario(sessao, fabricar_usuario, "10")

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 401


def test_organizador_nao_paga_reserva(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A rota é de `CLIENTE` na assinatura (AD-9), como todo o `cliente.py`."""
    _, _, reserva = _cenario(sessao, fabricar_usuario, "11")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-intruso@exemplo.com")
    _entrar(cliente, outro)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 403


# --------------------------------------------------------------------------- #
# O corpo do checkout
# --------------------------------------------------------------------------- #


def test_meio_cartao_sem_numero_responde_422(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`| None` no schema é por causa do Pix; a exigência é do `model_validator`."""
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "12")
    _entrar(cliente, comprador)

    corpo = _corpo()
    del corpo["numero_cartao"]

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=corpo)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_cpf_com_numero_errado_de_digitos_responde_422(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "13")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(cpf="123")
    )

    assert resposta.status_code == 422


def test_cpf_repetido_e_aceito_porque_o_aviso_pede_dado_ficticio(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Este teste existe para travar uma decisão, não um comportamento óbvio.

    `111.111.111-11` reprova no dígito verificador e é exatamente o que alguém
    digita quando a tela manda usar dados fictícios. Validar o DV faria o
    checkout recusar o avaliador — e é por isso que a validação é só de formato.
    """
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "14")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(cpf="111.111.111-11")
    )

    assert resposta.status_code == 200


def test_email_malformado_responde_422(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "15")
    _entrar(cliente, comprador)

    resposta = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(email="igor@")
    )

    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# AD-10 — o service depende da interface, nunca da implementação
# --------------------------------------------------------------------------- #


def test_a_rota_usa_o_gateway_injetado_e_nao_o_simulado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A prova prática do AD-10, e a única forma honesta de dá-la.

    O dublê **não herda de nada** — é `Protocol`, e o que vale é a forma da
    chamada. Ele recusa um cartão que o `PagamentoSimulado` aprovaria: se a rota
    conhecesse a implementação em vez da interface, a resposta seria `200`.
    """
    chamadas: list[tuple[int, MeioDePagamento, str | None]] = []

    class GatewayDeTeste:
        def autorizar(self, *, total_centavos, meio, numero_cartao):
            chamadas.append((total_centavos, meio, numero_cartao))
            return Autorizacao(aprovada=False)

    comprador, setor, reserva = _cenario(sessao, fabricar_usuario, "16")
    _entrar(cliente, comprador)

    app.dependency_overrides[obter_gateway] = lambda: GatewayDeTeste()
    try:
        resposta = cliente.post(
            f"/reservas/{reserva.id}/pagamento", json=_corpo(numero=CARTAO_APROVA)
        )
    finally:
        del app.dependency_overrides[obter_gateway]

    assert resposta.status_code == 402
    # O gateway recebeu o total da reserva, o meio e o cartão — e nada mais.
    assert chamadas == [(24000, MeioDePagamento.CARTAO, CARTAO_APROVA)]
    assert sessao.get(Setor, setor.id).vendidos == 0


# --------------------------------------------------------------------------- #
# O contrato de saída
# --------------------------------------------------------------------------- #


def test_a_resposta_nao_carrega_estoque_nem_dados_do_comprador(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Duas varreduras numa: o inventário (UX-DR7, AD-13) e o dado pessoal.

    Os campos do comprador não voltam nem para conferência — eles não são
    persistidos, e ecoá-los daria a impressão contrária a quem lê a resposta.
    """
    comprador, _, reserva = _cenario(sessao, fabricar_usuario, "17")
    _entrar(cliente, comprador)

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    assert resposta.status_code == 200
    bruto = resposta.text.lower()
    for palavra in PALAVRAS_DE_ESTOQUE + PALAVRAS_DO_COMPRADOR:
        assert palavra not in bruto, f"'{palavra}' vazou no corpo do pagamento"
