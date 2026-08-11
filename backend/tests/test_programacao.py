"""Rota `GET /eventos` (Story 3.1) — a programação pública.

Precisa do Compose no ar: grava eventos de verdade pelo ORM e lê pela rota.

**A primeira rota do projeto que responde sem sessão**, e é isso que o primeiro
teste daqui prova. Todos os testes anteriores de leitura de domínio começam por
um login; estes começam por `cliente.cookies.clear()` — o `TestClient` guarda
cookie entre chamadas, e um teste que "prova" acesso anônimo depois de um login
não prova nada.

**Três coisas que estes testes existem para travar:**

- **O estoque não atravessa o contrato** (AC7, UX-DR7). O corpo tem
  exatamente sete chaves, e a busca por `capacidade`/`vendidos` acontece no
  **texto inteiro** da resposta — não numa chave de topo, que é o que um
  `setores` aninhado escaparia.
- **`preco_minimo_centavos` pula o setor esgotado.** Os setores são gravados
  com preços diferentes e um deles com `vendidos == capacidade`, para que um
  mínimo lido de qualquer outro jeito não bata por acidente.
- **`min()` sobre lista vazia levanta `ValueError`.** Dois testes cobrem o
  caminho: todos os setores esgotados e evento sem setor nenhum.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario

# As sete chaves do `EventoNaProgramacao`, e nenhuma a mais (AC1, AC7).
CHAVES_DO_CONTRATO = {
    "id",
    "nome",
    "data_hora",
    "local",
    "cidade",
    "preco_minimo_centavos",
    "esgotado",
}


def _daqui_a(dias: int) -> datetime:
    """Uma data relativa ao relógio, e não uma constante como `2026-08-15`.

    O corte desta rota é `data_hora >= agora`, então uma data fixa no futuro
    vira uma data no passado assim que o calendário a alcança — e o teste que
    prova "o evento futuro aparece" passaria a falhar sozinho, meses depois,
    sem ninguém ter mexido em nada.
    """
    return datetime.now(timezone.utc) + timedelta(days=dias)


def _evento_gravado(
    sessao: Session,
    organizador: Usuario,
    *,
    nome: str = "Um show qualquer",
    data_hora: datetime | None = None,
    publicado: bool = True,
    setores: list[tuple[str, int, int, int]] | None = None,
) -> Evento:
    """Um evento com setores, gravado direto pelo ORM.

    Mesmo precedente do `test_organizador_meus_eventos.py`: não passa pela rota
    de publicação de propósito, porque a fixture é o **estado** de que a
    leitura precisa, não o caminho que produz esse estado. Aqui o argumento é
    ainda mais forte — a rota `POST /organizador/eventos` recusa data no
    passado (`EVENTO_NO_PASSADO`) e `publicado_em = None` não é produzível por
    tela nenhuma, e os dois estados são justamente o que os ACs 2 e 3 pedem.

    Cada setor é `(nome, capacidade, vendidos, preco_centavos)`. `preco_centavos`
    entrou na tupla — ao contrário do helper da 2.6, onde ele era fixo — porque
    a regra do preço mínimo só é verificável com preços diferentes entre si.

    ⚠️ **`publicado: bool`, e não `publicado_em: datetime | None`.** A segunda
    forma foi escrita primeiro e o teste do rascunho falhou: `None` é ao mesmo
    tempo "não informei" e "é rascunho", e o `if publicado_em is not None` do
    default engolia a segunda intenção. Um `bool` não tem esse ponto cego — e
    nenhum teste daqui precisa escolher *qual* carimbo o evento publicado leva.
    """
    # `is None`, e não `setores or [...]`: lista vazia é falsy, e o atalho daria
    # um setor de brinde ao teste que existe para provar que evento sem setor
    # nenhum não quebra a listagem.
    if setores is None:
        setores = [("Pista", 800, 0, 12000)]

    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or _daqui_a(30),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        # `NULL` é rascunho (Story 2.3). O default é "publicado" porque o
        # rascunho é o caso excepcional — só o AC2 o pede.
        publicado_em=(
            datetime(2026, 8, 11, 17, 22, tzinfo=timezone.utc) if publicado else None
        ),
        setores=[
            Setor(
                nome=nome_do_setor,
                capacidade=capacidade,
                vendidos=vendidos,
                preco_centavos=preco,
            )
            for nome_do_setor, capacidade, vendidos, preco in setores
        ],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento


def _organizador(fabricar_usuario: Callable[..., Usuario]) -> Usuario:
    return fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador@exemplo.com")


# --------------------------------------------------------------------------- #
# AC1 — pública por assinatura: responde sem cookie, e igual para todo mundo
# --------------------------------------------------------------------------- #


def test_a_programacao_responde_sem_nenhum_cookie_de_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O teste principal desta story: nenhuma sessão, `200` mesmo assim."""
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    # ⚠️ O `TestClient` guarda cookie entre chamadas. Sem isto, o teste passaria
    # por acidente numa suíte onde outro teste já tivesse feito login.
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert resposta.status_code == 200
    assert [evento["nome"] for evento in resposta.json()] == ["Marina Sena"]


def test_logado_como_cliente_o_corpo_e_identico_ao_anonimo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A identidade de quem chama não influencia o resultado.

    A comparação é entre os dois corpos **inteiros**, e não entre os nomes: a
    garantia que interessa é que nenhum campo a mais aparece para quem está
    logado — nem estoque, nem nada.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Djavan")
    cliente.cookies.clear()
    anonimo = cliente.get("/eventos")

    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    entrada = cliente.post(
        "/auth/login", json={"email": comprador.email, "senha": "rockhub"}
    )
    assert entrada.status_code == 200

    logado = cliente.get("/eventos")

    assert logado.status_code == 200
    assert logado.json() == anonimo.json()


def test_banco_sem_evento_publicado_e_futuro_responde_lista_vazia(
    cliente: TestClient,
) -> None:
    """`200 []`, nunca `404`: "não há show em cartaz" é resposta sobre o produto."""
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# AC2, AC3 — o que a programação recorta: rascunho e passado
# --------------------------------------------------------------------------- #


def test_evento_em_rascunho_nao_aparece_na_programacao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`publicado_em = NULL` é rascunho, e a rota pública não o mostra.

    ⚠️ É este o teste que o `deferred-work.md` previu. Ele cobre **a rota
    pública**; `listar_do_organizador` continua sem o filtro de propósito — o
    rascunho de alguém é dele —, e aquela entrada permanece aberta.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Publicado")
    _evento_gravado(sessao, organizador, nome="Rascunho", publicado=False)
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert [evento["nome"] for evento in resposta.json()] == ["Publicado"]


def test_evento_com_data_no_passado_nao_aparece_na_programacao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O corte é `data_hora >= agora`, no backend (decisão do Igor)."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Vai acontecer", data_hora=_daqui_a(10))
    _evento_gravado(sessao, organizador, nome="Já aconteceu", data_hora=_daqui_a(-10))
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert [evento["nome"] for evento in resposta.json()] == ["Vai acontecer"]


# --------------------------------------------------------------------------- #
# AC4 — ordem
# --------------------------------------------------------------------------- #


def test_a_programacao_vem_ordenada_por_data_hora_crescente(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Gravados fora de ordem, lidos em ordem — o `order_by` é quem decide."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Depois", data_hora=_daqui_a(40))
    _evento_gravado(sessao, organizador, nome="Antes", data_hora=_daqui_a(5))
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert [evento["nome"] for evento in resposta.json()] == ["Antes", "Depois"]


# --------------------------------------------------------------------------- #
# AC5, AC6 — preço mínimo e esgotado, derivados de `setor.vendidos` (AD-13)
# --------------------------------------------------------------------------- #


def test_o_preco_minimo_pula_o_setor_esgotado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Pista a R$ 120,00 esgotada, Camarote a R$ 420,00 com ingresso → 42000.

    A listagem anuncia o preço do que dá para comprar. Anunciar 12000 aqui
    seria a única forma de ela mentir com número: o visitante clicaria na fila
    esperando R$ 120,00 e encontraria R$ 420,00.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 800, 12000), ("Camarote", 120, 0, 42000)],
    )
    cliente.cookies.clear()

    (evento,) = cliente.get("/eventos").json()

    assert evento["preco_minimo_centavos"] == 42000
    assert evento["esgotado"] is False


def test_evento_com_todos_os_setores_esgotados_traz_preco_nulo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`esgotado` verdadeiro, preço `null` — e o evento **continua na lista**.

    Ele é informação (o show existe e acabou), não ruído.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 800, 12000), ("Camarote", 120, 120, 42000)],
    )
    cliente.cookies.clear()

    (evento,) = cliente.get("/eventos").json()

    assert evento["esgotado"] is True
    assert evento["preco_minimo_centavos"] is None


def test_evento_sem_setor_nenhum_nao_quebra_a_listagem(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`min()` sobre lista vazia levantaria `ValueError`, e viraria `500`.

    Impossível pela rota de publicação (`EVENTO_SEM_SETOR`), possível por
    `psql` — e existe no banco de desenvolvimento deste projeto.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), setores=[])
    cliente.cookies.clear()

    resposta = cliente.get("/eventos")

    assert resposta.status_code == 200
    (evento,) = resposta.json()
    assert evento["esgotado"] is True
    assert evento["preco_minimo_centavos"] is None


# --------------------------------------------------------------------------- #
# AC7 — o estoque não atravessa o contrato (UX-DR7). O AC que mais importa.
# --------------------------------------------------------------------------- #


def test_o_corpo_tem_exatamente_as_sete_chaves_do_contrato(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Igualdade de conjunto, e não `in`: campo a mais reprova tanto quanto a menos."""
    _evento_gravado(sessao, _organizador(fabricar_usuario))
    cliente.cookies.clear()

    (evento,) = cliente.get("/eventos").json()

    assert set(evento) == CHAVES_DO_CONTRATO


def test_nenhuma_palavra_de_estoque_aparece_no_texto_da_resposta(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A busca é no **texto inteiro**, e não nas chaves de topo.

    Um `setores` aninhado passaria pelo teste anterior se alguém o pusesse
    dentro de outro objeto. O que a tela não desenha, o devtools mostra — a
    garantia é o `response_model`, e este teste é quem a cobra.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 137, 12000)],
    )
    cliente.cookies.clear()

    corpo = cliente.get("/eventos").text

    for palavra in ("capacidade", "vendidos", "setores", "imagem_url", "organizador_id"):
        assert palavra not in corpo


# --------------------------------------------------------------------------- #
# AC1, AC9 — o contrato declarado, e a rota sem dependência de sessão
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_a_lista_de_evento_na_programacao(
    cliente: TestClient,
) -> None:
    """O contrato publicado é o mesmo que o código promete."""
    esquema = cliente.get("/openapi.json").json()

    resposta_200 = esquema["paths"]["/eventos"]["get"]["responses"]["200"]
    corpo = resposta_200["content"]["application/json"]["schema"]

    assert corpo["items"]["$ref"].endswith("/EventoNaProgramacao")

    propriedades = esquema["components"]["schemas"]["EventoNaProgramacao"]["properties"]
    assert set(propriedades) == CHAVES_DO_CONTRATO


def test_a_rota_publica_nao_declara_parametro_de_seguranca(
    cliente: TestClient,
) -> None:
    """Pública **por assinatura**, e não por disciplina de quem a mantiver.

    Se alguém acrescentar `Depends(exigir_papel(...))` aqui um dia, a rota
    passa a declarar o cookie no OpenAPI — e este teste cai antes de o sintoma
    chegar à tela do visitante.
    """
    esquema = cliente.get("/openapi.json").json()

    rota = esquema["paths"]["/eventos"]["get"]

    assert "security" not in rota
    assert rota.get("parameters", []) == []
