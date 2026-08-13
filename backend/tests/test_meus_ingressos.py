"""`GET /ingressos` e `GET /ingressos/{id}` — "Meus ingressos" e o canhoto com
o QR (Stories 4.1 e 4.2, a mesma techspec do grupo).

Precisa do Compose no ar: a consulta faz `join` com `reserva`, `evento` e
`setor`, e os quatro leem do mesmo Postgres da suíte.

**As fixtures gravam o estado direto pelo ORM, sem passar pela rota de
pagamento** — mesma disciplina do `_evento_gravado` em
`test_organizador_meus_eventos.py`: aqui o que importa é o estado que a
leitura precisa (uma reserva `PAGA` com ingresso emitido), não o caminho que o
produz, que já está coberto por `test_ingresso.py`. `usado_em` é gravado à mão
porque nada além da Story 5.2 escreve nele — a janela que a techspec descreve
como aberta de propósito até lá.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguranca import gerar_codigo, gerar_nonce
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _evento_publicado(
    sessao: Session,
    organizador: Usuario,
    *,
    nome: str = "Baco Exu do Blues",
    data_hora: datetime | None = None,
    setor_nome: str = "Pista",
) -> tuple[Evento, Setor]:
    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or (datetime.now(timezone.utc) + timedelta(days=30)),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=datetime.now(timezone.utc),
        setores=[Setor(nome=setor_nome, capacidade=800, vendidos=0, preco_centavos=12000)],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento, evento.setores[0]


def _ingresso_gravado(
    sessao: Session,
    cliente: Usuario,
    evento: Evento,
    setor: Setor,
    *,
    usado_em: datetime | None = None,
    validado_por: Usuario | None = None,
) -> Ingresso:
    """Uma reserva `PAGA` com um ingresso emitido, gravadas direto pelo ORM.

    Não passa por `POST /reservas/{id}/pagamento` de propósito: essa rota já
    tem cobertura própria em `test_ingresso.py`, e acoplar estes testes de
    leitura ao fluxo de pagamento os quebraria a cada mudança de lá sem nada a
    ver com a listagem.
    """
    reserva = Reserva(
        cliente_id=cliente.id,
        evento_id=evento.id,
        estado=EstadoReserva.PAGA.value,
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
        total_centavos=setor.preco_centavos,
        itens=[
            ItemReserva(
                setor_id=setor.id,
                quantidade=1,
                preco_unitario_centavos=setor.preco_centavos,
            )
        ],
    )
    sessao.add(reserva)
    sessao.flush()

    ingresso_id = uuid4()
    nonce = gerar_nonce()
    ingresso = Ingresso(
        id=ingresso_id,
        reserva_id=reserva.id,
        evento_id=evento.id,
        setor_id=setor.id,
        # Quem pagou, e não o titular: o titular do canhoto é `usuario.nome`, e
        # sai do join com `reserva` (techspec `docs/techspec-codigo-curto.md`).
        # A fixture põe um nome **diferente** do da conta de propósito — com os
        # dois iguais, uma rota que lesse a coluna errada passaria batido.
        pagador_nome=f"Cartão de {cliente.nome}",
        codigo=gerar_codigo(ingresso_id, evento.id, nonce),
        nonce=nonce,
        usado_em=usado_em,
        validado_por=validado_por.id if validado_por else None,
    )
    sessao.add(ingresso)
    sessao.flush()
    sessao.refresh(ingresso)
    return ingresso


# --------------------------------------------------------------------------- #
# O escopo é o cliente da sessão, e nada mais
# --------------------------------------------------------------------------- #


def test_a_lista_traz_so_os_ingressos_do_cliente_da_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi1@exemplo.com")
    meu = fabricar_usuario(PapelUsuario.CLIENTE, "meu-mi1@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.CLIENTE, "outro-mi1@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador, nome="O meu show")
    _ingresso_gravado(sessao, meu, evento, setor)
    outro_evento, outro_setor = _evento_publicado(sessao, organizador, nome="O show do outro")
    _ingresso_gravado(sessao, outro, outro_evento, outro_setor)
    _entrar(cliente, meu)

    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 200
    assert [item["evento_nome"] for item in resposta.json()] == ["O meu show"]


def test_cliente_sem_nenhuma_compra_recebe_lista_vazia(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """`200` com `[]`, nunca `404` — a pergunta foi respondida: nenhum."""
    estreante = fabricar_usuario(PapelUsuario.CLIENTE, "estreante-mi@exemplo.com")
    _entrar(cliente, estreante)

    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_a_lista_soma_ingressos_de_varias_compras_pagas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi2@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-mi2@exemplo.com")
    primeiro_evento, primeiro_setor = _evento_publicado(sessao, organizador, nome="Show A")
    segundo_evento, segundo_setor = _evento_publicado(
        sessao, organizador, nome="Show B", data_hora=datetime.now(timezone.utc) + timedelta(days=60)
    )
    _ingresso_gravado(sessao, comprador, primeiro_evento, primeiro_setor)
    _ingresso_gravado(sessao, comprador, segundo_evento, segundo_setor)
    _entrar(cliente, comprador)

    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2


# --------------------------------------------------------------------------- #
# Ordem e formato
# --------------------------------------------------------------------------- #


def test_a_lista_vem_ordenada_pela_data_do_evento_crescente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Gravados fora de ordem: na ordem de inserção o teste passaria por acaso."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi3@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-mi3@exemplo.com")
    agora = datetime.now(timezone.utc)

    evento_dezembro, setor_dezembro = _evento_publicado(
        sessao, organizador, nome="Em dezembro", data_hora=agora + timedelta(days=120)
    )
    evento_janeiro, setor_janeiro = _evento_publicado(
        sessao, organizador, nome="Em janeiro", data_hora=agora + timedelta(days=10)
    )
    evento_agosto, setor_agosto = _evento_publicado(
        sessao, organizador, nome="Em agosto", data_hora=agora + timedelta(days=30)
    )
    _ingresso_gravado(sessao, comprador, evento_dezembro, setor_dezembro)
    _ingresso_gravado(sessao, comprador, evento_janeiro, setor_janeiro)
    _ingresso_gravado(sessao, comprador, evento_agosto, setor_agosto)
    _entrar(cliente, comprador)

    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 200
    assert [item["evento_nome"] for item in resposta.json()] == [
        "Em janeiro",
        "Em agosto",
        "Em dezembro",
    ]


def test_o_item_tem_exatamente_as_chaves_do_ingresso_na_lista(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem `codigo` nem `titular_nome`: nenhum dos dois é desenhado nesta tela."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi4@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-mi4@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, comprador)

    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 200
    (item,) = resposta.json()
    assert set(item) == {
        "id",
        "evento_id",
        "evento_nome",
        "evento_data_hora",
        "evento_local",
        "setor_nome",
        "usado_em",
    }
    assert "codigo" not in resposta.text
    assert "titular_nome" not in resposta.text


# --------------------------------------------------------------------------- #
# O bloco Utilizados — provado gravando `usado_em` à mão (a janela da 4.1)
# --------------------------------------------------------------------------- #


def test_ingresso_nunca_validado_tem_usado_em_nulo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi5@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-mi5@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, comprador)

    (item,) = cliente.get("/ingressos").json()

    assert item["usado_em"] is None


def test_usado_em_gravado_a_mao_aparece_na_resposta(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Nada além da Story 5.2 escreve `usado_em` — esta é a prova possível
    hoje. A janela é a mesma que a techspec descreve como aberta de propósito.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-mi6@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "porteiro-mi6@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-mi6@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    entrada = datetime(2026, 8, 15, 20, 51, tzinfo=timezone.utc)
    _ingresso_gravado(
        sessao, comprador, evento, setor, usado_em=entrada, validado_por=porteiro
    )
    _entrar(cliente, comprador)

    (item,) = cliente.get("/ingressos").json()

    assert item["usado_em"] == entrada.isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------- #
# Autorização — o mesmo critério das outras rotas de `cliente.py`
# --------------------------------------------------------------------------- #


def test_organizador_e_portaria_recebem_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    for papel, email in (
        (PapelUsuario.ORGANIZADOR, "org-403-mi@exemplo.com"),
        (PapelUsuario.PORTARIA, "porta-403-mi@exemplo.com"),
    ):
        usuario = fabricar_usuario(papel, email)
        _entrar(cliente, usuario)

        resposta = cliente.get("/ingressos")

        assert resposta.status_code == 403, papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"
        cliente.cookies.clear()


def test_sem_cookie_recebe_401_e_nao_403(cliente: TestClient) -> None:
    resposta = cliente.get("/ingressos")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


# --------------------------------------------------------------------------- #
# O contrato declarado no OpenAPI
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_ingresso_na_lista(cliente: TestClient) -> None:
    especificacao = cliente.get("/openapi.json").json()

    rota = especificacao["paths"]["/ingressos"]["get"]
    schema = rota["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["items"]["$ref"].endswith("/IngressoNaLista")


# =============================================================================
# `GET /ingressos/{id}` — o canhoto cheio, com o `codigo` que vira QR (4.2)
# =============================================================================


def test_o_canhoto_traz_evento_setor_titular_codigo_e_usado_em(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cd1@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-cd1@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador, nome="Baco Exu do Blues")
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, comprador)

    resposta = cliente.get(f"/ingressos/{ingresso.id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(ingresso.id)
    assert corpo["evento_nome"] == "Baco Exu do Blues"
    assert corpo["evento_local"] == evento.local
    assert corpo["evento_cidade"] == evento.cidade
    assert corpo["setor_nome"] == setor.nome
    # ⚠️ **O titular é o nome da CONTA, e não `ingresso.pagador_nome`** (techspec
    # `docs/techspec-codigo-curto.md`). A fixture grava um pagador diferente de
    # propósito: sem a segunda asserção, uma rota que lesse a coluna do pagador
    # passaria por aqui no dia em que os dois nomes coincidissem.
    assert corpo["titular_nome"] == comprador.nome
    assert corpo["titular_nome"] != ingresso.pagador_nome
    assert corpo["usado_em"] is None


def test_o_codigo_sai_da_coluna_sem_recalcular(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ `ingresso.codigo`, e nada mais — o aviso do AD-5.

    Recalcular o HMAC aqui daria o mesmo valor no caso feliz e esconderia o
    ponto: só a portaria (Epic 5) recalcula, nunca esta rota.

    ⚠️ **A coluna é adulterada de propósito, e é isso que dá força ao teste**
    (code review da Epic 4). Antes, a asserção comparava a resposta contra o
    valor que a própria fixture havia gravado pelo HMAC — e ler a coluna ou
    recalcular produzem **o mesmo valor** no caminho feliz. Trocar o
    `_montar_detalhe` por um `gerar_codigo(...)` deixava a suíte inteira verde e o
    critério de pronto da 4.2 virava letra morta.

    Gravando aqui um valor que o HMAC **nunca** produziria para este ingresso, os
    dois caminhos divergem: se a rota recalcular, o código volta o legítimo e a
    asserção quebra. O que estaria em jogo em produção é a coluna deixar de ser a
    fonte do QR — e as duas rotas de leitura, a do dono e a pública, passarem a
    depender do `TICKET_SIGNING_SECRET` em tempo de leitura. Aí trocar o segredo
    no painel da Railway mudaria o QR exibido, em vez de só invalidar a validação
    na porta.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cd2@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-cd2@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)

    # Oito símbolos válidos do alfabeto — cabe na coluna e passa pela
    # normalização —, mas que o HMAC deste ingresso não produz. Se este texto
    # voltar na resposta, a rota leu a coluna.
    codigo_impossivel = "ZZZZZZZZ"
    assert gerar_codigo(ingresso.id, evento.id, ingresso.nonce) != codigo_impossivel
    ingresso.codigo = codigo_impossivel
    sessao.flush()

    _entrar(cliente, comprador)

    assert cliente.get(f"/ingressos/{ingresso.id}").json()["codigo"] == codigo_impossivel


def test_usado_em_aparece_no_canhoto_quando_gravado_a_mao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Um canhoto já utilizado não pode parecer válido na tela."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cd3@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "porteiro-cd3@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "comprador-cd3@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    entrada = datetime(2026, 8, 15, 20, 51, tzinfo=timezone.utc)
    ingresso = _ingresso_gravado(
        sessao, comprador, evento, setor, usado_em=entrada, validado_por=porteiro
    )
    _entrar(cliente, comprador)

    corpo = cliente.get(f"/ingressos/{ingresso.id}").json()

    assert corpo["usado_em"] == entrada.isoformat().replace("+00:00", "Z")


def test_ingresso_de_outra_pessoa_responde_404_ingresso_nao_encontrado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cd4@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cd4@exemplo.com")
    curioso = fabricar_usuario(PapelUsuario.CLIENTE, "curioso-cd4@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    alheio = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, curioso)

    resposta = cliente.get(f"/ingressos/{alheio.id}")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "INGRESSO_NAO_ENCONTRADO"


def test_a_resposta_de_ingresso_alheio_e_identica_a_de_um_id_inexistente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A rota não vira oráculo de "esse ingresso existe?" — mesma disciplina
    do `PORTARIA_INVALIDA` da 2.5 e do `RESERVA_NAO_ENCONTRADA` da 3.6."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cd5@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cd5@exemplo.com")
    curioso = fabricar_usuario(PapelUsuario.CLIENTE, "curioso-cd5@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    alheio = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, curioso)

    do_alheio = cliente.get(f"/ingressos/{alheio.id}")
    do_inexistente = cliente.get(f"/ingressos/{uuid4()}")

    assert do_alheio.status_code == do_inexistente.status_code == 404
    assert do_alheio.json() == do_inexistente.json()


def test_id_em_formato_invalido_responde_422_dados_invalidos(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "malformado-cd@exemplo.com")
    _entrar(cliente, comprador)

    resposta = cliente.get("/ingressos/nao-e-uuid")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_organizador_e_portaria_recebem_403_no_canhoto(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    for papel, email in (
        (PapelUsuario.ORGANIZADOR, "org-403-cd@exemplo.com"),
        (PapelUsuario.PORTARIA, "porta-403-cd@exemplo.com"),
    ):
        usuario = fabricar_usuario(papel, email)
        _entrar(cliente, usuario)

        resposta = cliente.get(f"/ingressos/{uuid4()}")

        assert resposta.status_code == 403, papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"
        cliente.cookies.clear()


def test_sem_cookie_recebe_401_no_canhoto(cliente: TestClient) -> None:
    resposta = cliente.get(f"/ingressos/{uuid4()}")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_o_openapi_declara_ingresso_detalhe(cliente: TestClient) -> None:
    especificacao = cliente.get("/openapi.json").json()

    rota = especificacao["paths"]["/ingressos/{ingresso_id}"]["get"]
    schema = rota["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/IngressoDetalhe")
