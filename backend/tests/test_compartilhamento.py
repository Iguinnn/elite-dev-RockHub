"""`POST /ingressos/{id}/compartilhamento` e a rota pública do link (Story 4.3).

Precisa do Compose no ar: as consultas fazem `join` com `reserva`, `evento` e
`setor`, e todas leem do mesmo Postgres da suíte.

**As fixtures vêm do `test_meus_ingressos.py`**, e não são reescritas aqui: o
estado que estes testes precisam é o mesmo — uma reserva `PAGA` com ingresso
emitido, gravada direto pelo ORM. Duplicar as fábricas faria as duas versões
divergirem no dia em que o modelo mudasse, e só uma delas seria corrigida.

**Arquivo próprio, e não mais um bloco no `test_meus_ingressos.py`.** Aquele
arquivo cobre a leitura do dono (4.1 e 4.2); este cobre o ciclo de vida do
link — que nasce aqui e morre na Story 4.4, no mesmo arquivo.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingresso import Ingresso
from app.models.usuario import PapelUsuario, Usuario
from tests.test_meus_ingressos import (
    _entrar,
    _evento_publicado,
    _ingresso_gravado,
)

# --------------------------------------------------------------------------- #
# Compartilhar: gera o token, e gera **um** só
# --------------------------------------------------------------------------- #


def test_compartilhar_devolve_o_canhoto_com_um_share_token(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp1@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp1@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador, nome="Baco Exu do Blues")
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    resposta = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["share_token"]
    # O corpo é o canhoto inteiro, e não um schema de um campo só: a ilha da
    # tela troca o estado todo em vez de juntar duas respostas.
    assert corpo["evento_nome"] == "Baco Exu do Blues"
    assert corpo["codigo"]


def test_o_token_e_gravado_na_coluna_share_token(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp2@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp2@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]

    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert gravado.share_token == token


def test_compartilhar_duas_vezes_devolve_o_mesmo_token(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ A decisão central da techspec: compartilhar é **idempotente**.

    Um token novo a cada clique transformaria "compartilhar de novo" numa
    revogação silenciosa — cortaria quem já recebeu o link, sem a confirmação
    que a Story 4.4 existe para exigir.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp3@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp3@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    primeiro = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()
    segundo = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()

    assert primeiro["share_token"] == segundo["share_token"]
    assert primeiro == segundo


def test_dois_ingressos_recebem_tokens_diferentes(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp4@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp4@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    um = _ingresso_gravado(sessao, dono, evento, setor)
    outro = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    token_de_um = cliente.post(f"/ingressos/{um.id}/compartilhamento").json()[
        "share_token"
    ]
    token_do_outro = cliente.post(f"/ingressos/{outro.id}/compartilhamento").json()[
        "share_token"
    ]

    assert token_de_um != token_do_outro


# --------------------------------------------------------------------------- #
# O token não é o código do QR (AD-8 × AD-5)
# --------------------------------------------------------------------------- #


def test_o_share_token_e_diferente_do_codigo_e_nao_aparece_dentro_dele(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ São dois valores com exposições opostas, e o link não pode carregar o QR.

    O `codigo` é `ID.ASSINATURA` (AD-5) e vale na porta; o `share_token` é um
    endereço opaco que viaja por WhatsApp (AD-8). Se um estivesse contido no
    outro, quem recebesse o link teria o código de entrada de graça — e a
    entropia da assinatura junto.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp5@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp5@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    corpo = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()

    token = corpo["share_token"]
    codigo = corpo["codigo"]
    assert token != codigo
    assert token not in codigo
    assert codigo not in token
    # E ele também não é o `nonce`, que é ingrediente secreto do HMAC.
    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert token != gravado.nonce


# --------------------------------------------------------------------------- #
# Compartilhar é do dono, e de mais ninguém
# --------------------------------------------------------------------------- #


def test_compartilhar_ingresso_de_outra_pessoa_responde_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp6@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp6@exemplo.com")
    curioso = fabricar_usuario(PapelUsuario.CLIENTE, "curioso-cp6@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    alheio = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, curioso)

    resposta = cliente.post(f"/ingressos/{alheio.id}/compartilhamento")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "INGRESSO_NAO_ENCONTRADO"
    # E nada foi gravado: a tentativa não pode deixar o ingresso do outro com
    # um link que ele nunca pediu.
    gravado = sessao.get(Ingresso, alheio.id)
    assert gravado is not None
    assert gravado.share_token is None


def test_compartilhar_aceita_a_chamada_como_o_navegador_a_faz(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Corpo vazio **com** `Content-Type: application/json` — é assim que o
    `chamarApi` do frontend chama, porque ele põe o cabeçalho em toda chamada.

    A rota não declara corpo nenhum, então o FastAPI nem lê o do pedido; sem
    este teste, a suíte só provaria o `POST` sem cabeçalho, que é o jeito que
    nenhuma tela usa.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp12@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp12@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    resposta = cliente.post(
        f"/ingressos/{ingresso.id}/compartilhamento",
        headers={"Content-Type": "application/json"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["share_token"]


def test_compartilhar_com_id_que_nao_e_uuid_responde_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "malformado-cp@exemplo.com")
    _entrar(cliente, dono)

    resposta = cliente.post("/ingressos/nao-e-uuid/compartilhamento")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_organizador_e_portaria_recebem_403_ao_compartilhar(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp7@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp7@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)

    for papel, email in (
        (PapelUsuario.ORGANIZADOR, "org-403-cp@exemplo.com"),
        (PapelUsuario.PORTARIA, "porta-403-cp@exemplo.com"),
    ):
        usuario = fabricar_usuario(papel, email)
        _entrar(cliente, usuario)

        resposta = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

        assert resposta.status_code == 403, papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"
        cliente.cookies.clear()


def test_sem_cookie_recebe_401_ao_compartilhar(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp8@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp8@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)

    resposta = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


# --------------------------------------------------------------------------- #
# O `GET /ingressos/{id}` do dono passa a devolver o token
# --------------------------------------------------------------------------- #


def test_o_canhoto_do_dono_nasce_com_share_token_nulo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp9@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp9@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    corpo = cliente.get(f"/ingressos/{ingresso.id}").json()

    assert corpo["share_token"] is None


def test_o_dono_reencontra_o_proprio_link_sem_compartilhar_de_novo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Depois de compartilhar, o `GET` devolve o mesmo token — recarregar a
    tela não pode fazer o link sumir nem gerar um segundo."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp10@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp10@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]

    assert cliente.get(f"/ingressos/{ingresso.id}").json()["share_token"] == token


def test_a_lista_de_ingressos_nao_carrega_share_token(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`IngressoNaLista` não mudou: o link é assunto do canhoto, não da fila."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-cp11@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-cp11@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

    resposta = cliente.get("/ingressos")

    assert "share_token" not in resposta.text


# --------------------------------------------------------------------------- #
# A rota pública: o link abre sem sessão nenhuma
# --------------------------------------------------------------------------- #


def test_o_link_abre_o_canhoto_sem_nenhuma_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O teste que prova a rota **pública** de pé, mesmo com `cliente.py`
    registrado antes do `publico.py`. O que a salva são os três segmentos do
    caminho; sem esta prova, o dia em que alguém a encurtar para dois é o dia
    em que ela passa a responder `401` sem mencionar autenticação nenhuma.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-pb1@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-pb1@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador, nome="Titãs")
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]
    # Quem abre o link não tem conta: fora o cookie, e nada de login.
    cliente.cookies.clear()

    resposta = cliente.get(f"/ingressos/compartilhados/{token}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(ingresso.id)
    assert corpo["evento_nome"] == "Titãs"


def test_o_canhoto_publico_e_identico_ao_do_dono(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Mesmo canhoto, com `titular_nome`, `codigo` e `usado_em` — é o requisito.

    Quem abre o link vai entrar com ele: um canhoto que escondesse o titular ou
    fingisse que o ingresso ainda vale seria um segundo canhoto, e a diferença
    apareceria na porta.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-pb2@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-pb2@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    do_dono = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()
    cliente.cookies.clear()

    do_link = cliente.get(f"/ingressos/compartilhados/{do_dono['share_token']}").json()

    assert do_link == do_dono
    assert do_link["titular_nome"] == dono.nome
    assert do_link["codigo"]


def test_token_inexistente_responde_404_link_nao_encontrado(
    cliente: TestClient,
) -> None:
    resposta = cliente.get("/ingressos/compartilhados/token-que-nunca-existiu")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "LINK_NAO_ENCONTRADO"


def test_o_link_de_um_ingresso_nunca_compartilhado_nao_existe(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Um ingresso com `share_token` nulo não pode ser alcançado por
    caminho nenhum: `NULL` não é um endereço."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-pb3@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-pb3@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    _ingresso_gravado(sessao, dono, evento, setor)

    for tentativa in ("null", "None", "%20"):
        resposta = cliente.get(f"/ingressos/compartilhados/{tentativa}")

        assert resposta.status_code == 404, tentativa
        assert resposta.json()["erro"]["codigo"] == "LINK_NAO_ENCONTRADO"


def test_a_rota_publica_responde_igual_para_quem_esta_logado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Não existe caminho pelo qual a identidade de quem chama mude o corpo —
    a mesma prova que a programação da Story 3.1 carrega."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-pb4@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-pb4@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.CLIENTE, "outro-pb4@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]

    cliente.cookies.clear()
    sem_conta = cliente.get(f"/ingressos/compartilhados/{token}")
    _entrar(cliente, outro)
    logado_como_outro = cliente.get(f"/ingressos/compartilhados/{token}")

    assert sem_conta.status_code == logado_como_outro.status_code == 200
    assert sem_conta.json() == logado_como_outro.json()


def test_a_rota_do_dono_continua_de_pe_ao_lado_da_publica(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ `/ingressos` mora em dois routers, e `cliente.py` é registrado antes.

    Este teste é o par do de cima: prova que a rota **autenticada** de dois
    segmentos não foi engolida pela pública ao ganhar uma vizinha.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-pb5@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-pb5@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    resposta = cliente.get(f"/ingressos/{ingresso.id}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == str(ingresso.id)


# --------------------------------------------------------------------------- #
# Revogar: o link para de valer, e nada diz que ele existiu (Story 4.4)
# --------------------------------------------------------------------------- #


def test_revogar_apaga_o_token_e_o_link_antigo_passa_a_responder_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O AC central da 4.4: o endereço que funcionava para de funcionar."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv1@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv1@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]
    assert cliente.get(f"/ingressos/compartilhados/{token}").status_code == 200

    resposta = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    assert resposta.status_code == 204
    # `204` é sem corpo — com corpo, a resposta é malformada.
    assert resposta.content == b""
    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert gravado.share_token is None
    assert cliente.get(f"/ingressos/compartilhados/{token}").status_code == 404


def test_o_link_revogado_responde_igual_a_um_token_que_nunca_existiu(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Mesmo status, mesmo código, mesma frase — é o que faz a revogação ser
    um corte, e não um aviso de que existiu algo ali."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv2@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv2@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    token = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]
    cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")
    cliente.cookies.clear()

    do_revogado = cliente.get(f"/ingressos/compartilhados/{token}")
    do_inexistente = cliente.get("/ingressos/compartilhados/token-que-nunca-existiu")

    assert do_revogado.status_code == do_inexistente.status_code == 404
    assert do_revogado.json() == do_inexistente.json()


def test_compartilhar_depois_de_revogar_gera_um_token_diferente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O par exato do teste da idempotência: **com** link, devolve o mesmo;
    **sem** link — inclusive por revogação —, gera outro. Se o token voltasse a
    ser o mesmo, revogar não teria cortado nada."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv3@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv3@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    primeiro = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]
    cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    segundo = cliente.post(f"/ingressos/{ingresso.id}/compartilhamento").json()[
        "share_token"
    ]

    assert segundo != primeiro
    # E o primeiro continua morto: revogar não é "trocar de endereço".
    cliente.cookies.clear()
    assert cliente.get(f"/ingressos/compartilhados/{primeiro}").status_code == 404


def test_revogar_duas_vezes_responde_204_nas_duas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Idempotência do `DELETE`: a segunda chamada não é erro nenhum.

    Quem pediu para o link não valer mais obteve exatamente isso — e a tela não
    precisa tratar um caso que, para quem clicou, é sucesso.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv4@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv4@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

    primeira = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")
    segunda = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    assert primeira.status_code == segunda.status_code == 204


def test_revogar_ingresso_nunca_compartilhado_responde_204(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem link nenhum desde o começo é o mesmo caso da segunda revogação."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv5@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv5@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)

    resposta = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    assert resposta.status_code == 204


def test_revogar_nao_apaga_o_ingresso_nem_o_codigo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O `DELETE` é do **link**, não do ingresso.

    O endereço é `/compartilhamento`, e é só isso que ele remove: o canhoto
    continua inteiro, com o mesmo `codigo` que vale na porta. Um `DELETE` que
    encostasse na linha do ingresso apagaria a compra de alguém.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv6@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv6@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    antes = cliente.get(f"/ingressos/{ingresso.id}").json()
    cliente.post(f"/ingressos/{ingresso.id}/compartilhamento")

    cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    depois = cliente.get(f"/ingressos/{ingresso.id}").json()
    assert depois == antes
    assert depois["codigo"] == antes["codigo"]
    assert depois["share_token"] is None


def test_revogar_o_link_de_outra_pessoa_responde_404_e_nao_apaga_nada(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O teste que a `_carregar_do_cliente` existe para garantir: sem o
    `Reserva.cliente_id` no mesmo `where`, qualquer cliente derrubaria o link
    de qualquer outro."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv7@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv7@exemplo.com")
    curioso = fabricar_usuario(PapelUsuario.CLIENTE, "curioso-rv7@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    alheio = _ingresso_gravado(sessao, dono, evento, setor)
    _entrar(cliente, dono)
    token = cliente.post(f"/ingressos/{alheio.id}/compartilhamento").json()[
        "share_token"
    ]
    cliente.cookies.clear()
    _entrar(cliente, curioso)

    resposta = cliente.delete(f"/ingressos/{alheio.id}/compartilhamento")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "INGRESSO_NAO_ENCONTRADO"
    # O link do dono continua de pé.
    cliente.cookies.clear()
    assert cliente.get(f"/ingressos/compartilhados/{token}").status_code == 200


def test_revogar_com_id_que_nao_e_uuid_responde_422(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "malformado-rv@exemplo.com")
    _entrar(cliente, dono)

    resposta = cliente.delete("/ingressos/nao-e-uuid/compartilhamento")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_organizador_e_portaria_recebem_403_ao_revogar(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv8@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv8@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)

    for papel, email in (
        (PapelUsuario.ORGANIZADOR, "org-403-rv@exemplo.com"),
        (PapelUsuario.PORTARIA, "porta-403-rv@exemplo.com"),
    ):
        usuario = fabricar_usuario(papel, email)
        _entrar(cliente, usuario)

        resposta = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

        assert resposta.status_code == 403, papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"
        cliente.cookies.clear()


def test_sem_cookie_recebe_401_ao_revogar(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-rv9@exemplo.com")
    dono = fabricar_usuario(PapelUsuario.CLIENTE, "dono-rv9@exemplo.com")
    evento, setor = _evento_publicado(sessao, organizador)
    ingresso = _ingresso_gravado(sessao, dono, evento, setor)

    resposta = cliente.delete(f"/ingressos/{ingresso.id}/compartilhamento")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_a_rota_publica_nao_aceita_delete(cliente: TestClient) -> None:
    """⚠️ Revogar é do dono, e o endereço público não é um segundo caminho para
    isso. Sem sessão, o `DELETE` ali não existe — e o `405` do `erros.py` já
    responde no formato da API."""
    resposta = cliente.delete("/ingressos/compartilhados/qualquer-token")

    assert resposta.status_code == 405
    assert resposta.json()["erro"]["codigo"] == "METODO_NAO_PERMITIDO"


# --------------------------------------------------------------------------- #
# O contrato declarado no OpenAPI
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_as_duas_rotas_do_compartilhamento(
    cliente: TestClient,
) -> None:
    especificacao = cliente.get("/openapi.json").json()

    criacao = especificacao["paths"]["/ingressos/{ingresso_id}/compartilhamento"]["post"]
    publica = especificacao["paths"]["/ingressos/compartilhados/{token}"]["get"]

    for rota in (criacao, publica):
        schema = rota["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema["$ref"].endswith("/IngressoDetalhe")


def test_o_openapi_declara_o_delete_sem_corpo_de_resposta(cliente: TestClient) -> None:
    """`204` declarado, e **nenhum** `200` — a rota não devolve ingresso."""
    especificacao = cliente.get("/openapi.json").json()

    rota = especificacao["paths"]["/ingressos/{ingresso_id}/compartilhamento"]["delete"]

    assert "204" in rota["responses"]
    assert "content" not in rota["responses"]["204"]
    assert "200" not in rota["responses"]
