"""Rotas `GET /organizador/eventos` e `GET /organizador/eventos/{evento_id}`
(Story 2.6) — o organizador vendo o que publicou.

Precisa do Compose no ar: faz login de verdade, como os outros testes de rota
do organizador.

As duas são leitura pura, sem transação e sem invariante, e mesmo assim passam
por service — elas tocam o banco, e router que abre `Session` para consultar é
o que o paradigma da espinha proíbe. O critério inteiro está no docstring de
`app/api/organizador.py`.

**Duas coisas que estes testes existem para travar:**

- `capacidade_total` e `vendidos_total` são a **soma** de `setor.capacidade` e
  `setor.vendidos` (AD-13). Os setores são gravados com `vendidos` diferente de
  zero e diferentes entre si, para que um total lido de qualquer outro jeito
  não bata por acidente.
- O `404` de "esse evento não é seu" é **idêntico** ao de "esse id nunca
  existiu". A comparação é entre os dois corpos inteiros, como a Story 2.5 fez
  com o `PORTARIA_INVALIDA`.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

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
    setores: list[tuple[str, int, int]] | None = None,
    portarias: list[Usuario] | None = None,
) -> Evento:
    """Um evento com setores, gravado direto pelo ORM.

    **Não passa pela rota `POST /organizador/eventos` de propósito.** Publicar
    pela rota acoplaria estes testes às quatro recusas das Stories 2.4 e 2.5 —
    setor vazio, setor repetido, portaria vazia, portaria inválida —, e o dia
    em que uma delas mudasse, quinze testes de leitura quebrariam sem ter nada
    a ver com o assunto. Aqui a fixture é o **estado** de que a leitura precisa,
    não o caminho que produz esse estado.

    Cada setor é `(nome, capacidade, vendidos)`. `vendidos` é gravado à mão
    justamente porque nenhuma rota de escrita sabe fazê-lo — só a Epic 3 vai
    saber, pelo `UPDATE` condicional — e sem ele o teste da soma passaria com
    dois zeros.
    """
    # ⚠️ `is None`, e **não** `setores or [...]`: lista vazia é falsy, e o
    # atalho daria um setor de brinde justamente ao teste que existe para
    # provar que evento sem setor nenhum soma zero.
    if setores is None:
        setores = [("Pista", 800, 0)]

    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc),
        setores=[
            Setor(
                nome=nome_do_setor,
                capacidade=capacidade,
                vendidos=vendidos,
                preco_centavos=12000,
            )
            for nome_do_setor, capacidade, vendidos in setores
        ],
        portarias=portarias if portarias is not None else [],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


# --------------------------------------------------------------------------- #
# AC1, AC2 — a lista é a do organizador da sessão, ordenada por data
# --------------------------------------------------------------------------- #


def test_a_lista_traz_so_os_eventos_do_organizador_da_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O escopo vem da sessão, e não há parâmetro por onde outro id entrasse."""
    meu = fabricar_usuario(PapelUsuario.ORGANIZADOR, "meu@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "outro@exemplo.com")
    _evento_gravado(sessao, meu, nome="O meu show")
    _evento_gravado(sessao, outro, nome="O show do outro")
    _entrar(cliente, meu)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    assert [evento["nome"] for evento in resposta.json()] == ["O meu show"]


def test_a_lista_vem_ordenada_por_data_hora_crescente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Gravados fora de ordem: na ordem de inserção o teste passaria por acaso."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "agenda@exemplo.com")
    _evento_gravado(
        sessao,
        organizador,
        nome="Em dezembro",
        data_hora=datetime(2026, 12, 3, 21, 0, tzinfo=timezone.utc),
    )
    _evento_gravado(
        sessao,
        organizador,
        nome="Em janeiro",
        data_hora=datetime(2026, 1, 9, 21, 0, tzinfo=timezone.utc),
    )
    _evento_gravado(
        sessao,
        organizador,
        nome="Em agosto",
        data_hora=datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc),
    )
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    assert [evento["nome"] for evento in resposta.json()] == [
        "Em janeiro",
        "Em agosto",
        "Em dezembro",
    ]


def test_organizador_sem_nenhum_evento_recebe_lista_vazia(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Lista vazia é `200`, não `404` — mesma disciplina do `GET /portarias`.

    A pergunta "quais são os meus eventos?" foi respondida: nenhum. Quem decide
    o que dizer é a tela, e ela diz que ainda não há nada publicado.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "estreante@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# AC3 — os dois totais são soma de setor, nunca COUNT de outra coisa
# --------------------------------------------------------------------------- #


def test_os_totais_somam_a_capacidade_e_os_vendidos_de_todos_os_setores(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """AD-13: os dois totais vêm de `setor`, e de mais lugar nenhum.

    Os quatro números são diferentes entre si e `vendidos` é diferente de zero
    nos dois setores: um total lido de qualquer outro jeito — o primeiro setor,
    o maior, a contagem de setores — não bateria por acaso.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "soma@exemplo.com")
    _evento_gravado(
        sessao,
        organizador,
        setores=[("Pista", 800, 12), ("Camarote", 60, 5)],
    )
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    (evento,) = resposta.json()
    assert evento["capacidade_total"] == 860
    assert evento["vendidos_total"] == 17


def test_evento_sem_setor_nenhum_soma_zero_e_nao_quebra_a_listagem(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Impossível pela rota de publicação, possível por `psql`.

    A listagem não pode ser o lugar onde uma linha gravada à mão derruba a tela
    inteira do organizador.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "vazio@exemplo.com")
    _evento_gravado(sessao, organizador, setores=[])
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    (evento,) = resposta.json()
    assert evento["capacidade_total"] == 0
    assert evento["vendidos_total"] == 0


def test_o_resumo_tem_exatamente_as_chaves_do_evento_resumo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Sem `setores`, sem `imagem_url` e sem `organizador_id`.

    A lista é enxuta de propósito: o detalhe é quem abre setor a setor. Quem
    garante o corte é o `response_model=list[EventoResumo]` — sem ele, o
    FastAPI serializaria o que o service devolvesse.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "chaves@exemplo.com")
    _evento_gravado(sessao, organizador)
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos")

    assert resposta.status_code == 200
    (evento,) = resposta.json()
    assert set(evento) == {
        "id",
        "nome",
        "data_hora",
        "local",
        "cidade",
        "publicado_em",
        "capacidade_total",
        "vendidos_total",
    }


# --------------------------------------------------------------------------- #
# AC5 — o detalhe reusa o EventoSaida da publicação, inteiro
# --------------------------------------------------------------------------- #


def test_o_detalhe_traz_setores_e_portarias_com_nome_e_email(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "detalhe@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "porta@exemplo.com")
    evento = _evento_gravado(
        sessao,
        organizador,
        setores=[("Pista", 800, 12), ("Camarote", 60, 0)],
        portarias=[porteiro],
    )
    _entrar(cliente, organizador)

    resposta = cliente.get(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    # ⚠️ **Alfabético, e não a ordem em que os setores foram gravados.** Até o
    # code review da Epic 2 esta asserção era `["Pista", "Camarote"]` e passava
    # por acidente: sem `ORDER BY`, o Postgres devolvia na ordem de varredura do
    # heap, que coincide com a inserção **até a primeira escrita na linha**. O
    # `UPDATE setor SET vendidos = ...` do AD-3, na Epic 3, reescreve a tupla no
    # fim do heap e trocaria os setores de lugar na tela do organizador, com
    # este teste continuando verde. O `order_by="Setor.nome"` do modelo é o
    # contrato agora, e é isto que o teste afirma.
    assert [setor["nome"] for setor in corpo["setores"]] == ["Camarote", "Pista"]
    assert corpo["setores"][1]["vendidos"] == 12
    assert corpo["portarias"] == [
        {"id": str(porteiro.id), "nome": porteiro.nome, "email": porteiro.email}
    ]
    # Quem chama já sabe quem é: devolver o dono só daria a impressão de que
    # é um campo que se escolhe.
    assert "organizador_id" not in corpo


def test_senha_hash_nao_aparece_em_lugar_nenhum_do_detalhe(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Quem filtra é o `response_model=EventoSaida`.

    Sem ele, um `Usuario` cru dentro de `portarias` traria o hash da senha de
    quem foi escalado numa resposta de rotina.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "sem-hash@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "com-hash@exemplo.com")
    evento = _evento_gravado(sessao, organizador, portarias=[porteiro])
    _entrar(cliente, organizador)

    resposta = cliente.get(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 200
    assert "senha_hash" not in resposta.text


def test_evento_sem_ninguem_escalado_responde_200_com_portarias_vazia(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O resíduo da janela do AD-7 aberta na Story 2.4.

    Existem eventos assim no banco de desenvolvimento: publicados quando a rota
    ainda não exigia portaria escalada. A tela mostra uma frase no lugar da
    lista, e para isso a API precisa responder `200` — não erro.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "sem-porta@exemplo.com")
    evento = _evento_gravado(sessao, organizador, portarias=[])
    _entrar(cliente, organizador)

    resposta = cliente.get(f"/organizador/eventos/{evento.id}")

    assert resposta.status_code == 200
    assert resposta.json()["portarias"] == []


# --------------------------------------------------------------------------- #
# AC6 — um 404 só, e ele não é oráculo
# --------------------------------------------------------------------------- #


def test_o_detalhe_de_evento_alheio_responde_404_evento_nao_encontrado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    meu = fabricar_usuario(PapelUsuario.ORGANIZADOR, "curioso@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "dono@exemplo.com")
    alheio = _evento_gravado(sessao, outro)
    _entrar(cliente, meu)

    resposta = cliente.get(f"/organizador/eventos/{alheio.id}")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"


def test_a_resposta_de_evento_alheio_e_identica_a_de_um_id_inexistente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A rota não vira oráculo de "esse evento existe?".

    Mesma disciplina do `PORTARIA_INVALIDA` da Story 2.5 e do login da 1.4: se
    os dois corpos diferissem em uma palavra, bastaria varrer UUIDs para
    descobrir quais são eventos de outra pessoa.
    """
    meu = fabricar_usuario(PapelUsuario.ORGANIZADOR, "varredor@exemplo.com")
    outro = fabricar_usuario(PapelUsuario.ORGANIZADOR, "alvo@exemplo.com")
    alheio = _evento_gravado(sessao, outro)
    _entrar(cliente, meu)

    do_alheio = cliente.get(f"/organizador/eventos/{alheio.id}")
    do_inexistente = cliente.get(f"/organizador/eventos/{uuid4()}")

    assert do_alheio.status_code == do_inexistente.status_code == 404
    assert do_alheio.json() == do_inexistente.json()


def test_id_em_formato_invalido_responde_422_dados_invalidos(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """De graça, por o parâmetro de caminho ser `UUID`: estrutura é do Pydantic."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "malformado@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/eventos/nao-e-uuid")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# AC7 — papel na assinatura, e 401 antes de 403, nas duas rotas
# --------------------------------------------------------------------------- #


def test_cliente_recebe_403_nas_duas_rotas(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "freguesia@exemplo.com")
    _entrar(cliente, usuario)

    for caminho in ("/organizador/eventos", f"/organizador/eventos/{uuid4()}"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 403, caminho
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_portaria_recebe_403_nas_duas_rotas(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Estar escalado num evento não dá direito de ler o inventário dele."""
    usuario = fabricar_usuario(PapelUsuario.PORTARIA, "portaria@exemplo.com")
    _entrar(cliente, usuario)

    for caminho in ("/organizador/eventos", f"/organizador/eventos/{uuid4()}"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 403, caminho
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_sem_cookie_recebe_401_e_nao_403_nas_duas_rotas(cliente: TestClient) -> None:
    """A ordem é garantida pelo `Depends` encadeado, não por `if` no corpo."""
    for caminho in ("/organizador/eventos", f"/organizador/eventos/{uuid4()}"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 401, caminho
        assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


# --------------------------------------------------------------------------- #
# AC5, AC8 — o contrato declarado no OpenAPI
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_evento_resumo_na_lista_e_evento_saida_no_detalhe(
    cliente: TestClient,
) -> None:
    especificacao = cliente.get("/openapi.json").json()

    lista = especificacao["paths"]["/organizador/eventos"]["get"]
    schema_da_lista = lista["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema_da_lista["items"]["$ref"].endswith("/EventoResumo")

    detalhe = especificacao["paths"]["/organizador/eventos/{evento_id}"]["get"]
    schema_do_detalhe = detalhe["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert schema_do_detalhe["$ref"].endswith("/EventoSaida")
