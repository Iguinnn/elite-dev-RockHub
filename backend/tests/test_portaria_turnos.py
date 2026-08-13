"""Rota `GET /portaria/eventos` (Story 5.1) — a portaria vendo onde trabalha.

Precisa do Compose no ar: faz login de verdade, como os outros testes de rota
autenticada.

**A primeira leitura da `evento_portaria`.** A tabela existe desde a Story 2.3 e
é gravada desde a 2.5, e até aqui nenhuma rota a consultava — o docstring de
`models/evento.py` dizia com todas as letras que consumi-la seria a Epic 5.

**Três coisas que estes testes existem para travar:**

- **Evento passado continua na lista.** É o corte que as quatro rotas públicas
  fazem e esta **não** faz, e é a única asserção deste arquivo que protege contra
  alguém "uniformizar" o service depois. Às 21h30 de um show das 21h a portaria
  está trabalhando; se o turno sumisse junto com a vitrine, ele desapareceria no
  minuto em que a fila começa a andar.
- **A escala é vínculo, não papel** (AD-7). Duas contas de portaria, um evento
  para cada: ter papel `PORTARIA` não põe ninguém na porta de todo show. As duas
  contas do seed existem exatamente para dar este cenário.
- **O contrato não carrega inventário.** `capacidade`, `vendidos` e `setores`
  ficam de fora, e quem garante é o `response_model=list[TurnoDaPortaria]` — sem
  ele o FastAPI serializaria o que o service devolvesse.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _evento_gravado(
    sessao: Session,
    organizador: Usuario,
    *,
    nome: str = "Um show qualquer",
    data_hora: datetime | None = None,
    cidade: str | None = "São Paulo",
    portarias: list[Usuario] | None = None,
    publicado: bool = True,
) -> Evento:
    """Um evento com um setor e a escala escolhida, gravado direto pelo ORM.

    **Não passa pela rota `POST /organizador/eventos` de propósito**, pelo mesmo
    motivo escrito no `test_organizador_meus_eventos.py`: publicar pela rota
    acoplaria estes testes de leitura às cinco recusas das Stories 2.4 e 2.5. E
    aqui há um motivo a mais, decisivo — `publicar` recusa data no passado
    (`EVENTO_NO_PASSADO`), e o teste que mais importa neste arquivo é justamente
    o do evento que já aconteceu. Pela rota ele seria impossível de montar.
    """
    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc),
        local="Espaço Unimed",
        cidade=cidade,
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=(
            datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc) if publicado else None
        ),
        setores=[
            Setor(nome="Pista", capacidade=800, vendidos=12, preco_centavos=12000)
        ],
        portarias=portarias if portarias is not None else [],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


# --------------------------------------------------------------------------- #
# A lista é a da escala de quem está na sessão, ordenada por data
# --------------------------------------------------------------------------- #


def test_a_lista_traz_so_os_eventos_em_que_a_conta_foi_escalada(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """AD-7: a escala é vínculo por evento, não nível de permissão.

    Duas contas de portaria — o cenário que as duas do seed existem para dar —,
    um evento para cada, mais um evento sem ninguém escalado. Ter o papel não põe
    ninguém na porta de show nenhum.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "quem-publica@exemplo.com")
    eu = fabricar_usuario(PapelUsuario.PORTARIA, "porta1@exemplo.com")
    colega = fabricar_usuario(PapelUsuario.PORTARIA, "porta2@exemplo.com")

    _evento_gravado(sessao, organizador, nome="O meu turno", portarias=[eu])
    _evento_gravado(sessao, organizador, nome="O turno do colega", portarias=[colega])
    _evento_gravado(sessao, organizador, nome="Sem ninguém na porta", portarias=[])
    _entrar(cliente, eu)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert [turno["nome"] for turno in resposta.json()] == ["O meu turno"]


def test_o_mesmo_evento_aparece_para_as_duas_contas_escaladas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Vários escalados por evento é decisão da Story 2.5, e a leitura a honra.

    Sem esta asserção, um `join` que devolvesse só a primeira linha da escala
    passaria no teste acima e falharia na porta de um show com dois porteiros.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "dupla@exemplo.com")
    uma = fabricar_usuario(PapelUsuario.PORTARIA, "dupla1@exemplo.com")
    outra = fabricar_usuario(PapelUsuario.PORTARIA, "dupla2@exemplo.com")
    _evento_gravado(sessao, organizador, nome="Show de dois", portarias=[uma, outra])

    _entrar(cliente, uma)
    da_uma = cliente.get("/portaria/eventos")
    cliente.cookies.clear()
    _entrar(cliente, outra)
    da_outra = cliente.get("/portaria/eventos")

    assert [turno["nome"] for turno in da_uma.json()] == ["Show de dois"]
    assert [turno["nome"] for turno in da_outra.json()] == ["Show de dois"]


def test_a_lista_vem_ordenada_por_data_hora_crescente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Gravados fora de ordem: na ordem de inserção o teste passaria por acaso."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "agenda@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "agenda-porta@exemplo.com")
    for nome, quando in (
        ("Em dezembro", datetime(2026, 12, 3, 21, 0, tzinfo=timezone.utc)),
        ("Em janeiro", datetime(2026, 1, 9, 21, 0, tzinfo=timezone.utc)),
        ("Em agosto", datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc)),
    ):
        _evento_gravado(
            sessao, organizador, nome=nome, data_hora=quando, portarias=[porteiro]
        )
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert [turno["nome"] for turno in resposta.json()] == [
        "Em janeiro",
        "Em agosto",
        "Em dezembro",
    ]


def test_portaria_sem_escala_nenhuma_recebe_lista_vazia(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Lista vazia é `200 []`, nunca erro — mesma disciplina do `GET /portarias`.

    A pergunta "onde eu trabalho?" foi respondida com "em lugar nenhum ainda", e
    quem decide o que dizer é a tela.
    """
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "estreante@exemplo.com")
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# O corte que esta rota NÃO faz — e o único que ela faz
# --------------------------------------------------------------------------- #


def test_evento_que_ja_aconteceu_continua_na_lista(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **A asserção mais importante deste arquivo.**

    As quatro rotas públicas cortam em `data_hora >= agora`; esta **não corta**.
    A portaria trabalha exatamente do outro lado desse corte: às 21h30 de um show
    das 21h o evento já sumiu de `listar_programacao`, e é justamente quando a
    fila anda. Copiar o filtro daqui faria o turno desaparecer da mão de quem
    está na porta.

    O teste é explícito porque a uniformização é tentadora — o service vizinho
    tem o `where` do tempo escrito três vezes.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "ontem@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "ontem-porta@exemplo.com")
    agora = datetime.now(timezone.utc)
    _evento_gravado(
        sessao,
        organizador,
        nome="Foi na semana passada",
        data_hora=agora - timedelta(days=7),
        portarias=[porteiro],
    )
    _evento_gravado(
        sessao,
        organizador,
        nome="Começou há meia hora",
        data_hora=agora - timedelta(minutes=30),
        portarias=[porteiro],
    )
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert [turno["nome"] for turno in resposta.json()] == [
        "Foi na semana passada",
        "Começou há meia hora",
    ]


def test_rascunho_com_escala_nao_aparece(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`publicado_em IS NOT NULL` é o único corte da consulta.

    Impossível pela rota hoje — publicação e escala são a mesma transação das
    Stories 2.4 e 2.5 —, possível por `psql`, e a condição já vale para o dia em
    que houver rascunho de verdade. Rascunho não tem porta para abrir.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "rascunho@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "rascunho-porta@exemplo.com")
    _evento_gravado(
        sessao,
        organizador,
        nome="Ainda é rascunho",
        portarias=[porteiro],
        publicado=False,
    )
    _evento_gravado(sessao, organizador, nome="Esse está no ar", portarias=[porteiro])
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert [turno["nome"] for turno in resposta.json()] == ["Esse está no ar"]


# --------------------------------------------------------------------------- #
# O contrato: a ficha da tela, e nada de inventário
# --------------------------------------------------------------------------- #


def test_o_turno_tem_exatamente_as_chaves_do_turno_da_portaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem `capacidade`, `vendidos` nem `setores` — e **com** `aberto`.

    Os três primeiros são inventário e o contador do turno é a Story 5.6, que vai
    contar `ingresso.usado_em` e não estoque.

    ⚠️ **`aberto` entrou na Story 5.2 e reverte o que este teste travava**: até a
    5.1 ele estava na lista de chaves proibidas, porque o portão das 2h era regra
    da tela. Desde que a rota de validação passou a recusar fora da janela, a
    janela tem um dono só — `ABERTURA_DOS_PORTOES`, no service —, e a tela lê o
    campo em vez de recalcular.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "chaves@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "chaves-porta@exemplo.com")
    _evento_gravado(sessao, organizador, portarias=[porteiro])
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    (turno,) = resposta.json()
    assert set(turno) == {"id", "nome", "data_hora", "local", "cidade", "aberto"}


def test_aberto_segue_a_janela_de_duas_horas_do_service(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O campo é `data_hora - ABERTURA_DOS_PORTOES <= agora`, e nada mais.

    Três turnos numa resposta só: um daqui a três horas (fechado), um daqui a uma
    hora (aberto, dentro da janela) e um que começou há meia hora (aberto, do
    outro lado do corte que as rotas públicas fazem). O terceiro é o que importa
    — é a hora em que a fila anda.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "janela@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "janela-porta@exemplo.com")
    agora = datetime.now(timezone.utc)
    for nome, quando in (
        ("Começou faz meia hora", agora - timedelta(minutes=30)),
        ("Daqui a uma hora", agora + timedelta(hours=1)),
        ("Daqui a três horas", agora + timedelta(hours=3)),
    ):
        _evento_gravado(
            sessao, organizador, nome=nome, data_hora=quando, portarias=[porteiro]
        )
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    assert [(turno["nome"], turno["aberto"]) for turno in resposta.json()] == [
        ("Começou faz meia hora", True),
        ("Daqui a uma hora", True),
        ("Daqui a três horas", False),
    ]


def test_a_ficha_traz_nome_data_casa_e_cidade(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "ficha@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "ficha-porta@exemplo.com")
    evento = _evento_gravado(sessao, organizador, nome="Sepultura", portarias=[porteiro])
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    (turno,) = resposta.json()
    assert turno["id"] == str(evento.id)
    assert turno["nome"] == "Sepultura"
    assert turno["local"] == "Espaço Unimed"
    assert turno["cidade"] == "São Paulo"
    assert turno["data_hora"].startswith("2026-08-15T21:00:00")


def test_cidade_nula_atravessa_como_null_e_nao_some_do_corpo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A coluna é anulável desde a Story 2.3 — a Discovery pode não trazê-la.

    A chave **continua no corpo**: a tela distingue "sem cidade" de "campo que
    não veio", e é isso que a impede de imprimir um separador solto na ficha.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "sem-cidade@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "sem-cidade-porta@exemplo.com")
    _evento_gravado(sessao, organizador, cidade=None, portarias=[porteiro])
    _entrar(cliente, porteiro)

    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 200
    (turno,) = resposta.json()
    assert "cidade" in turno
    assert turno["cidade"] is None


# --------------------------------------------------------------------------- #
# Papel na assinatura, e 401 antes de 403
# --------------------------------------------------------------------------- #


def test_sem_cookie_recebe_401_e_nao_403(cliente: TestClient) -> None:
    """A ordem é garantida pelo `Depends` encadeado, não por `if` no corpo."""
    resposta = cliente.get("/portaria/eventos")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_cliente_e_organizador_recebem_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Publicar o show não dá direito de abrir a porta dele — nem comprar.

    O organizador é o caso que mais tenta: ele **é** quem escala a portaria
    (Story 2.5). Escalar e trabalhar continuam sendo coisas diferentes.
    """
    for papel, email in (
        (PapelUsuario.CLIENTE, "freguesia@exemplo.com"),
        (PapelUsuario.ORGANIZADOR, "quem-escala@exemplo.com"),
    ):
        cliente.cookies.clear()
        _entrar(cliente, fabricar_usuario(papel, email))

        resposta = cliente.get("/portaria/eventos")

        assert resposta.status_code == 403, papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_o_openapi_declara_turno_da_portaria_na_rota(cliente: TestClient) -> None:
    especificacao = cliente.get("/openapi.json").json()

    rota = especificacao["paths"]["/portaria/eventos"]["get"]
    schema = rota["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["items"]["$ref"].endswith("/TurnoDaPortaria")


# --------------------------------------------------------------------------- #
# `GET /portaria/eventos/{id}` — o cabeçalho do leitor (Story 5.3)
# --------------------------------------------------------------------------- #


def test_o_turno_de_um_evento_so_traz_a_mesma_ficha_da_lista(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Mesmo schema da lista, e é de propósito: é a mesma ficha, de um item só.

    A tela do leitor precisa do nome do show no cabeçalho, e a rota pública
    `GET /eventos/{id}` não serve — ela corta em `data_hora >= agora` e responde
    `404` **exatamente durante o show**, que é quando a portaria trabalha.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "um@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "um-porta@exemplo.com")
    evento = _evento_gravado(
        sessao,
        organizador,
        nome="Sepultura",
        data_hora=datetime.now(timezone.utc) + timedelta(hours=1),
        portarias=[porteiro],
    )
    _entrar(cliente, porteiro)

    resposta = cliente.get(f"/portaria/eventos/{evento.id}")

    assert resposta.status_code == 200
    turno = resposta.json()
    assert set(turno) == {"id", "nome", "data_hora", "local", "cidade", "aberto"}
    assert turno["id"] == str(evento.id)
    assert turno["nome"] == "Sepultura"
    assert turno["aberto"] is True


def test_o_turno_de_um_evento_que_ja_comecou_continua_atendendo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **A asserção que justifica a rota existir.**

    `GET /eventos/{id}` responderia `404` aqui, porque as rotas públicas escondem
    o evento a partir de `data_hora`. É o horário em que a fila anda.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "andando@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "andando-porta@exemplo.com")
    evento = _evento_gravado(
        sessao,
        organizador,
        nome="Começou às 21h",
        data_hora=datetime.now(timezone.utc) - timedelta(minutes=30),
        portarias=[porteiro],
    )
    _entrar(cliente, porteiro)

    publica = cliente.get(f"/eventos/{evento.id}")
    da_portaria = cliente.get(f"/portaria/eventos/{evento.id}")

    assert publica.status_code == 404
    assert da_portaria.status_code == 200
    assert da_portaria.json()["nome"] == "Começou às 21h"


def test_o_turno_de_um_evento_sem_escala_responde_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A mesma dependência da validação, e a mesma recusa — sem uma linha nova.

    É o que a tela usa para mandar de volta a `/portaria`: quem não trabalha
    naquele evento não abre o leitor dele.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "alheio@exemplo.com")
    de_fora = fabricar_usuario(PapelUsuario.PORTARIA, "alheio-porta@exemplo.com")
    evento = _evento_gravado(sessao, organizador, portarias=[])
    _entrar(cliente, de_fora)

    resposta = cliente.get(f"/portaria/eventos/{evento.id}")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_ESCALA_NO_EVENTO"


def test_o_turno_antes_da_porta_abrir_responde_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O leitor não abre antes da hora — a mesma janela que recusa a validação.

    Sem isso, a tela do leitor renderizaria e o primeiro código digitado
    receberia `403` da validação: a recusa apareceria depois de a portaria já ter
    começado a trabalhar, em vez de antes.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "cedo@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "cedo-porta@exemplo.com")
    evento = _evento_gravado(
        sessao,
        organizador,
        data_hora=datetime.now(timezone.utc) + timedelta(days=3),
        portarias=[porteiro],
    )
    _entrar(cliente, porteiro)

    resposta = cliente.get(f"/portaria/eventos/{evento.id}")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NAO_ABERTO"


def test_o_turno_exige_sessao_e_papel_de_portaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`401` antes de `403`, e o organizador do próprio show também não entra."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "dono@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "dono-porta@exemplo.com")
    evento = _evento_gravado(sessao, organizador, portarias=[porteiro])

    sem_sessao = cliente.get(f"/portaria/eventos/{evento.id}")
    assert sem_sessao.status_code == 401
    assert sem_sessao.json()["erro"]["codigo"] == "NAO_AUTENTICADO"

    _entrar(cliente, organizador)
    resposta = cliente.get(f"/portaria/eventos/{evento.id}")
    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_a_rota_da_lista_nao_e_engolida_pela_do_turno(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """⚠️ **`/portaria/eventos` e `/portaria/eventos/{id}` convivem**, e a prova
    é barata.

    O `/ingressos` da Story 4.3 passou a morar em dois routers e só se sustenta
    pela contagem de segmentos do caminho; aqui o risco é o vizinho — uma rota de
    um segmento e outra de dois sob o mesmo prefixo. Elas não colidem, e esta
    asserção é o que garante que continuam não colidindo se alguém reordenar as
    declarações do arquivo.
    """
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "ordem-porta@exemplo.com")
    _entrar(cliente, porteiro)

    lista = cliente.get("/portaria/eventos")

    assert lista.status_code == 200
    assert lista.json() == []
