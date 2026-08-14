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
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario
from app.services import evento as servico_de_evento

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
    local: str = "Espaço Unimed",
    cidade: str | None = "São Paulo",
    imagem_url: str | None = None,
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

    `local` e `cidade` ganharam parâmetro na Story 3.2, **com o mesmo valor de
    antes como default**: os testes da 3.1 continuam gravando "Espaço Unimed" em
    "São Paulo" sem saber que os campos passaram a ser escolhíveis. `cidade`
    aceita `None` de propósito — a coluna é anulável desde a 2.3, e há um teste
    que depende disso.

    ⚠️ **`cidade=None` não cai no ponto cego do `publicado`.** Aqui `None` é um
    valor de domínio ("este evento não tem cidade") e não a ausência do
    argumento, e o helper o repassa cru: não existe `cidade or "São Paulo"`
    nenhum abaixo, justamente para o teste do filtro poder gravar o evento sem
    cidade que ele precisa.

    `imagem_url` ganhou parâmetro na Story 3.3, com `None` como default — que é
    também o valor que a coluna tinha antes de ela ser escolhível. Nenhum teste
    da 3.1 nem da 3.2 precisou mudar por causa disso: a arte não atravessa o
    contrato da programação, e só a rota de destaque a lê. É o mesmo `None` de
    domínio da `cidade`, e ele é repassado cru pelo mesmo motivo.
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
        local=local,
        cidade=cidade,
        imagem_url=imagem_url,
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

    # ⚠️ **As nove que o AC7 enumera, e não cinco** (code review da Epic 3). A
    # varredura cobria metade da lista: `publicado_em` e `origem_externa_id`
    # ficavam de fora justamente em `GET /eventos`, que é a única rota em que os
    # ACs das três stories os declaram proibidos. O helper grava
    # `origem_externa_id="G5vYZ9a1kd"` em todo evento, então um vazamento aninhado
    # atravessava a varredura sem ser visto — que é exatamente o buraco que a
    # busca no texto inteiro existe para fechar.
    # (`capacidade_total` e `vendidos_total` já entram por substring.)
    for palavra in (
        "capacidade",
        "vendidos",
        "setores",
        "imagem_url",
        "origem_externa_id",
        "publicado_em",
        "organizador_id",
    ):
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

    ⚠️ **A segunda asserção mudou na Story 3.2, e é a única linha de teste da
    3.1 que precisou mudar.** Ela dizia `parameters == []`, o que era a forma
    exata de escrever "nenhum parâmetro" enquanto a rota não tinha nenhum. Com
    `?q=`, `?cidade=` e `?periodo=`, essa frase deixou de caber — mas a
    invariante que ela protegia não mudou: o que não pode existir aqui é
    parâmetro **de sessão**. Agora é isso que está escrito, e por construção:
    todo parâmetro declarado precisa vir de `in: query`. Um `Depends` de cookie
    ou de header apareceria como `in: cookie`/`in: header` e derrubaria o teste
    igual — só que agora ele continua derrubando mesmo depois de a rota ganhar
    filtros, que é justamente quando alguém teria a chance de errar.
    """
    esquema = cliente.get("/openapi.json").json()

    rota = esquema["paths"]["/eventos"]["get"]

    assert "security" not in rota
    assert {parametro["in"] for parametro in rota.get("parameters", [])} <= {"query"}


# =========================================================================== #
# Story 3.2 — buscar e filtrar a programação
#
# Tudo daqui para baixo é da 3.2. O helper acima ganhou `local` e `cidade` com
# os mesmos valores de antes como default, e é por isso que nada acima precisou
# mudar (a única exceção está documentada no teste logo acima deste bloco).
# =========================================================================== #


def _nomes(resposta: object) -> list[str]:
    """Os nomes da resposta, na ordem — o que quase toda asserção daqui olha."""
    return [evento["nome"] for evento in resposta.json()]  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# AC1 — o termo casa nome, local ou cidade
# --------------------------------------------------------------------------- #


def test_o_termo_casa_o_nome_do_evento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena")
    _evento_gravado(sessao, organizador, nome="Djavan")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "marina"})

    assert resposta.status_code == 200
    assert _nomes(resposta) == ["Marina Sena"]


def test_o_termo_casa_a_casa_de_show(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O termo é "artista, casa ou cidade" — e a casa é o campo `local`."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Show A", local="Qualistage")
    _evento_gravado(sessao, organizador, nome="Show B", local="Espaço Unimed")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "qualistage"})

    assert _nomes(resposta) == ["Show A"]


def test_o_termo_casa_a_cidade(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Casar cidade pelo `?q=` é o que permite digitar em vez de achar o chip."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="No Rio", cidade="Rio de Janeiro")
    _evento_gravado(sessao, organizador, nome="Em SP", cidade="São Paulo")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "rio de janeiro"})

    assert _nomes(resposta) == ["No Rio"]


def test_termo_sem_resultado_responde_lista_vazia(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`200 []`, nunca `404`: filtrar não cria um endereço que não existe."""
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "orquestra sinfonica"})

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# AC2 — caixa e acento: `MARINA`, `marina`, `sao paulo` e `SÃO` acham o mesmo
# --------------------------------------------------------------------------- #


def test_a_busca_ignora_a_caixa_do_termo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    maiuscula = cliente.get("/eventos", params={"q": "MARINA"})
    minuscula = cliente.get("/eventos", params={"q": "marina"})

    assert _nomes(maiuscula) == ["Marina Sena"]
    assert maiuscula.json() == minuscula.json()


def test_termo_sem_acento_acha_o_evento_com_acento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`sao paulo` acha `São Paulo` — é assim que se digita no celular.

    Este é o teste que prova a extensão `unaccent` (migração `06c1ad5ac276`)
    estar ligada. Se ela sumir do banco, ele **não** falha com asserção: a
    consulta estoura antes, com `function unaccent(text) does not exist`.
    """
    _evento_gravado(
        sessao, _organizador(fabricar_usuario), nome="Show", cidade="São Paulo"
    )
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "sao paulo"})

    assert _nomes(resposta) == ["Show"]


def test_termo_com_acento_acha_o_evento_gravado_sem_acento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O outro sentido, que é o que exige `unaccent` nos **dois** lados.

    Com a extensão só na coluna, quem digitasse `SÃO` não acharia um evento
    gravado como `Sao Joao da Serra` — e o defeito só apareceria para quem tem
    teclado com acento, ou seja, quase ninguém em teste.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Sao Joao da Serra")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "SÃO"})

    assert _nomes(resposta) == ["Sao Joao da Serra"]


# --------------------------------------------------------------------------- #
# AC3 — `%` e `_` são curingas do LIKE, e o termo é escapado
# --------------------------------------------------------------------------- #


def test_buscar_por_porcento_nao_devolve_a_programacao_inteira(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ O teste mais importante desta story, e o defeito mais silencioso dela.

    Sem escape, `?q=%` vira o padrão `%%%` e devolve tudo — com `200`, com cara
    de resultado, e sem ninguém desconfiar porque a tela parece funcionar.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="100% Rock")
    _evento_gravado(sessao, organizador, nome="Marina Sena")
    _evento_gravado(sessao, organizador, nome="Djavan")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "%"})

    assert _nomes(resposta) == ["100% Rock"]


def test_buscar_por_sublinhado_nao_casa_qualquer_caractere(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`_` casa um caractere qualquer no `LIKE` — e não deve casar nada aqui."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Rock_Hub ao vivo")
    _evento_gravado(sessao, organizador, nome="Marina Sena")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "_"})

    assert _nomes(resposta) == ["Rock_Hub ao vivo"]


def test_buscar_por_contrabarra_nao_quebra_a_consulta(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A contrabarra é o caractere de escape: sozinha, ela é padrão inválido.

    Sem escapá-la, o Postgres recusa o `LIKE` com `invalid escape sequence` e
    a rota devolve `500` — para uma busca que uma pessoa digitou por engano.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "\\"})

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# AC4, AC5 — termo vazio, só espaços, e o teto de 120 caracteres
# --------------------------------------------------------------------------- #


def test_termo_vazio_ou_so_com_espacos_devolve_a_programacao_inteira(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Antes", data_hora=_daqui_a(5))
    _evento_gravado(sessao, organizador, nome="Depois", data_hora=_daqui_a(40))
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"q": ""})) == ["Antes", "Depois"]
    assert _nomes(cliente.get("/eventos", params={"q": "   "})) == ["Antes", "Depois"]


def test_o_termo_e_aparado_antes_de_virar_padrao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`?q=%20marina%20` acha `Marina Sena` — espaço colado não é parte do termo."""
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "  marina  "})

    assert _nomes(resposta) == ["Marina Sena"]


def test_termo_acima_de_120_caracteres_e_recusado(cliente: TestClient) -> None:
    """O mesmo teto de `GET /organizador/catalogo`, e o mesmo do `<input>`."""
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "a" * 121})

    assert resposta.status_code == 422


def test_termo_com_exatamente_120_caracteres_passa(cliente: TestClient) -> None:
    """O teto é inclusivo — 120 é válido, 121 não. Prova que o limite é onde se diz."""
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "a" * 120})

    assert resposta.status_code == 200


# --------------------------------------------------------------------------- #
# AC6 — cidade por igualdade exata, e o evento sem cidade
# --------------------------------------------------------------------------- #


def test_o_filtro_de_cidade_recorta_por_igualdade_exata(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Em SP", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="No Rio", cidade="Rio de Janeiro")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"cidade": "São Paulo"})

    assert _nomes(resposta) == ["Em SP"]


def test_cidade_pela_metade_nao_casa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Igualdade, e não `ilike` (decisão do Igor).

    ⚠️ **Este teste afirmava outra coisa até 13/08/2026**: que `?cidade=sao
    paulo`, sem acento, devolvia lista vazia. A regra mudou junto com o
    agrupamento das grafias — a igualdade passou a ser sobre
    `unaccent(lower(...))`, e o teste abaixo cobre o caso novo.

    O que **não** mudou, e é o que esta função guarda: continua sendo igualdade
    de string inteira. `?cidade=sao` não casa `São Paulo`, porque o parâmetro não
    é campo de digitação — quem quer digitar tem o `?q=`, que casa cidade por
    pedaço.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), cidade="São Paulo")
    cliente.cookies.clear()

    assert cliente.get("/eventos", params={"cidade": "sao"}).json() == []
    assert _nomes(cliente.get("/eventos", params={"q": "sao"})) != []


def test_o_filtro_de_cidade_ignora_acento_e_caixa(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """As grafias da mesma cidade são a mesma cidade — inclusive no filtro.

    ⚠️ **O caso real, e o motivo de a regra ter mudado**: a Ticketmaster manda
    `São Paulo` e `Sao Paulo` para a mesma cidade, e nós copiamos o que vem
    (AD-1). Com igualdade crua, o chip `São Paulo` achava um dos dois e **escondia
    o outro sem dizer nada** — o resultado parecia completo.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Com til", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="Sem til", cidade="Sao Paulo")
    _evento_gravado(sessao, organizador, nome="No Rio", cidade="Rio de Janeiro")
    cliente.cookies.clear()

    # Os dois eventos, venha o parâmetro com til, sem til ou em caixa baixa.
    for escrita in ("São Paulo", "Sao Paulo", "são paulo"):
        assert sorted(_nomes(cliente.get("/eventos", params={"cidade": escrita}))) == [
            "Com til",
            "Sem til",
        ], escrita


def test_evento_sem_cidade_fica_fora_do_filtro_e_dentro_da_lista(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A cidade é anulável desde a Story 2.3, e os dois lados importam.

    Fora de qualquer filtro de cidade — `NULL = 'São Paulo'` é `NULL`, nunca
    verdadeiro — e dentro da programação sem filtro, porque o show existe.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Sem cidade", cidade=None)
    _evento_gravado(sessao, organizador, nome="Em SP", cidade="São Paulo")
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"cidade": "São Paulo"})) == ["Em SP"]
    assert sorted(_nomes(cliente.get("/eventos"))) == ["Em SP", "Sem cidade"]


def test_evento_sem_cidade_continua_achavel_pelo_nome(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ `unaccent(NULL) ILIKE …` é `NULL`, e `TRUE OR NULL` é `TRUE`.

    É o comportamento certo, e ele é frágil: qualquer `coalesce(cidade, '')`
    "consertando" a coluna anulável passaria despercebido sem este teste — e
    qualquer troca do `or_` por três condições separadas o quebraria na hora.
    """
    _evento_gravado(
        sessao, _organizador(fabricar_usuario), nome="Marina Sena", cidade=None
    )
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"q": "marina"})) == ["Marina Sena"]


# --------------------------------------------------------------------------- #
# AC7, AC8 — o período, em janelas corridas a partir de agora
# --------------------------------------------------------------------------- #


def test_o_periodo_recorta_em_janelas_corridas_de_7_e_30_dias(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Um show em 3 dias, um em 15 e um em 60 → 1, 2 e 3 eventos.

    As janelas são **corridas a partir de agora** (decisão do Igor), e não a
    semana e o mês do calendário: "esta semana" numa sexta-feira significaria
    dois dias, e o filtro pareceria quebrado no dia em que mais gente procura
    show. Os rótulos da tela dizem `7 DIAS` e `30 DIAS` por isso.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Em 3 dias", data_hora=_daqui_a(3))
    _evento_gravado(sessao, organizador, nome="Em 15 dias", data_hora=_daqui_a(15))
    _evento_gravado(sessao, organizador, nome="Em 60 dias", data_hora=_daqui_a(60))
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"periodo": "semana"})) == [
        "Em 3 dias"
    ]
    assert _nomes(cliente.get("/eventos", params={"periodo": "mes"})) == [
        "Em 3 dias",
        "Em 15 dias",
    ]
    assert len(cliente.get("/eventos").json()) == 3


def test_periodo_todos_devolve_o_mesmo_que_a_ausencia_do_parametro(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`TODOS` não acrescenta condição — ele existe para o chip ter o que apontar."""
    _evento_gravado(sessao, _organizador(fabricar_usuario), data_hora=_daqui_a(300))
    cliente.cookies.clear()

    assert cliente.get("/eventos", params={"periodo": "todos"}).json() == (
        cliente.get("/eventos").json()
    )


def test_periodo_fora_do_enum_e_recusado(cliente: TestClient) -> None:
    """`422` do FastAPI, e não uma comparação silenciosa que devolve tudo."""
    cliente.cookies.clear()

    assert cliente.get("/eventos", params={"periodo": "ontem"}).status_code == 422


# --------------------------------------------------------------------------- #
# AC9 — os três filtros se somam, e não abrem porta nos cortes da 3.1
# --------------------------------------------------------------------------- #


def test_os_tres_filtros_valem_juntos(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Cada um dos três derruba um candidato diferente; sobra um.

    Os distratores existem para provar que os filtros se somam com `AND`: se um
    deles fosse ignorado, ou se as condições virassem `OR`, a lista voltaria com
    dois ou mais nomes.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(
        sessao,
        organizador,
        nome="Marina Sena",
        cidade="São Paulo",
        data_hora=_daqui_a(3),
    )
    # Casa termo e cidade, mas está fora da semana.
    _evento_gravado(
        sessao,
        organizador,
        nome="Marina Sena de novo",
        cidade="São Paulo",
        data_hora=_daqui_a(20),
    )
    # Casa termo e período, mas é em outra cidade.
    _evento_gravado(
        sessao,
        organizador,
        nome="Marina Sena no Rio",
        cidade="Rio de Janeiro",
        data_hora=_daqui_a(3),
    )
    # Casa cidade e período, mas é outro artista.
    _evento_gravado(
        sessao, organizador, nome="Djavan", cidade="São Paulo", data_hora=_daqui_a(3)
    )
    cliente.cookies.clear()

    resposta = cliente.get(
        "/eventos",
        params={"q": "marina", "cidade": "São Paulo", "periodo": "semana"},
    )

    assert _nomes(resposta) == ["Marina Sena"]


def test_rascunho_continua_fora_mesmo_com_termo_que_casaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Um `where` novo não abre porta num corte antigo.

    O termo casa o rascunho perfeitamente, e ele continua invisível: as duas
    condições da Story 3.1 não têm exceção.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena", publicado=False)
    cliente.cookies.clear()

    assert cliente.get("/eventos", params={"q": "marina"}).json() == []


def test_evento_passado_continua_fora_mesmo_com_termo_que_casaria(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O gêmeo do teste acima, para a outra condição da 3.1."""
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        nome="Marina Sena",
        data_hora=_daqui_a(-10),
    )
    cliente.cookies.clear()

    assert cliente.get("/eventos", params={"q": "marina"}).json() == []


# --------------------------------------------------------------------------- #
# AC10 — `GET /eventos/cidades`: o universo dos chips
# --------------------------------------------------------------------------- #


def test_as_cidades_vem_distintas_ordenadas_e_sem_nulo_sem_nenhum_cookie(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Pública como a programação, e sem `null` — chip em branco não é escolha."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="A", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="B", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="C", cidade="Rio de Janeiro")
    _evento_gravado(sessao, organizador, nome="D", cidade="Belo Horizonte")
    _evento_gravado(sessao, organizador, nome="E", cidade=None)
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/cidades")

    assert resposta.status_code == 200
    assert resposta.json() == ["Belo Horizonte", "Rio de Janeiro", "São Paulo"]


def test_as_grafias_da_mesma_cidade_viram_um_chip_so(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Um chip por cidade, na grafia mais frequente (13/08/2026).

    O `venue.city.name` da Ticketmaster não é normalizado, e o `DISTINCT` cru
    desenhava **dois chips com o mesmo nome** na barra — um deles achando um
    evento só. Aqui `Sao Paulo` (um evento) e `São Paulo` (dois) são a mesma
    cidade, e quem aparece é a grafia da maioria.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="A", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="B", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="C", cidade="Sao Paulo")
    _evento_gravado(sessao, organizador, nome="D", cidade="rio de janeiro")
    _evento_gravado(sessao, organizador, nome="E", cidade="Rio de Janeiro")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/cidades")

    assert resposta.status_code == 200
    # Duas cidades, não quatro. `São Paulo` ganha por frequência (dois contra
    # um); `Rio de Janeiro` empata em um evento cada e ganha por ter maiúscula —
    # o desempate que **não** depende do collation do banco. Sem ele, o glibc põe
    # a minúscula na frente e o chip aparece como "rio de janeiro".
    assert resposta.json() == ["Rio de Janeiro", "São Paulo"]


def test_as_cidades_usam_o_mesmo_recorte_de_publicado_e_futuro(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Chip de cidade sem show em cartaz é um filtro que só devolve lista vazia."""
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Em cartaz", cidade="São Paulo")
    _evento_gravado(
        sessao, organizador, nome="Rascunho", cidade="Curitiba", publicado=False
    )
    _evento_gravado(
        sessao,
        organizador,
        nome="Já aconteceu",
        cidade="Salvador",
        data_hora=_daqui_a(-10),
    )
    cliente.cookies.clear()

    assert cliente.get("/eventos/cidades").json() == ["São Paulo"]


def test_as_cidades_nao_reagem_ao_termo_de_busca(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ A lista de escolhas é o universo, não o resultado.

    Encolhê-la conforme se filtra faria o chip sumir debaixo do cursor de quem
    ia clicar — e tiraria o caminho de volta de quem filtrou errado. A rota nem
    declara os parâmetros: eles chegam e são ignorados pelo FastAPI.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="Djavan", cidade="Rio de Janeiro")
    cliente.cookies.clear()

    com_termo = cliente.get("/eventos/cidades", params={"q": "marina"})

    assert com_termo.json() == ["Rio de Janeiro", "São Paulo"]


def test_banco_sem_evento_em_cartaz_devolve_lista_de_cidades_vazia(
    cliente: TestClient,
) -> None:
    """`200 []`: sem cidade nenhuma a tela simplesmente não desenha o grupo."""
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/cidades")

    assert resposta.status_code == 200
    assert resposta.json() == []


# --------------------------------------------------------------------------- #
# AC12 — o contrato não afrouxa por causa de um `where` novo (UX-DR7)
# --------------------------------------------------------------------------- #


def test_com_busca_ativa_o_corpo_continua_com_as_sete_chaves(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O AC7 da Story 3.1, repetido **com filtro ligado**.

    Um `WHERE` novo é exatamente o tipo de mudança em que um `setores` aparece
    "só para a próxima story usar" — e o `response_model` é a garantia, não a
    tela.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    (evento,) = cliente.get(
        "/eventos", params={"q": "marina", "periodo": "mes"}
    ).json()

    assert set(evento) == CHAVES_DO_CONTRATO


def test_com_busca_ativa_nenhuma_palavra_de_estoque_aparece_na_resposta(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A varredura do texto inteiro, também com filtro ligado."""
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        nome="Marina Sena",
        setores=[("Pista", 800, 137, 12000)],
    )
    cliente.cookies.clear()

    corpo = cliente.get(
        "/eventos", params={"q": "marina", "cidade": "São Paulo"}
    ).text

    for palavra in (
        "capacidade",
        "vendidos",
        "setores",
        "imagem_url",
        # Faltava, pelo mesmo motivo do gêmeo da 3.1 — ver o comentário lá.
        "origem_externa_id",
        "publicado_em",
        "organizador_id",
    ):
        assert palavra not in corpo


# --------------------------------------------------------------------------- #
# AC1, AC8, AC10 — o contrato declarado das duas rotas
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_os_tres_parametros_de_filtro(
    cliente: TestClient,
) -> None:
    """Os três, todos em `query`, e o período com os três valores do enum."""
    esquema = cliente.get("/openapi.json").json()

    parametros = {
        parametro["name"]: parametro
        for parametro in esquema["paths"]["/eventos"]["get"]["parameters"]
    }

    assert set(parametros) == {"q", "cidade", "periodo"}
    assert all(parametro["in"] == "query" for parametro in parametros.values())

    # O enum pode vir por `$ref` (Pydantic v2 nomeia o schema) ou inline; o que
    # importa é que os três valores estejam publicados no documento.
    assert esquema["components"]["schemas"]["PeriodoDaProgramacao"]["enum"] == [
        "todos",
        "semana",
        "mes",
    ]


def test_o_openapi_declara_a_rota_de_cidades_como_lista_de_texto(
    cliente: TestClient,
) -> None:
    """`list[str]`, sem parâmetro nenhum e sem segurança."""
    esquema = cliente.get("/openapi.json").json()

    rota = esquema["paths"]["/eventos/cidades"]["get"]
    corpo = rota["responses"]["200"]["content"]["application/json"]["schema"]

    assert corpo["items"]["type"] == "string"
    assert "security" not in rota
    assert rota.get("parameters", []) == []


# =========================================================================== #
# Story 3.3 — a chamada principal na programação
#
# `GET /eventos/destaque`: o próximo show da programação, com a arte e os nomes
# dos setores. Tudo daqui para baixo é da 3.3, e **nenhum teste acima precisou
# mudar** — a rota é nova, `GET /eventos` está intacta e o helper só ganhou um
# parâmetro com default. É o AC9 desta story, e ele é verificável relendo o
# diff: se algo acima mudou, escopo vazou.
# =========================================================================== #

# As nove chaves do `EventoEmDestaque`, e nenhuma a mais (AC5).
#
# ⚠️ Ele é **maior** que o `CHAVES_DO_CONTRATO` da programação, e isso não é
# afrouxamento: `imagem_url` e `setores` (nomes) entram porque a capa os desenha,
# e os dois contratos são independentes de propósito. O AC5 falava em **oito**
# chaves — `preco_minimo_centavos` entrou depois, por decisão do Igor tomada com
# a tela pronta, e o motivo está no docstring do schema.
CHAVES_DO_DESTAQUE = {
    "id",
    "nome",
    "data_hora",
    "local",
    "cidade",
    "imagem_url",
    "setores",
    "preco_minimo_centavos",
    "esgotado",
}


# --------------------------------------------------------------------------- #
# AC1 — pública por assinatura, e sem parâmetro nenhum
# --------------------------------------------------------------------------- #


def test_o_destaque_responde_sem_nenhum_cookie_de_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A terceira rota pública do projeto, e o mesmo cuidado das duas primeiras."""
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    # ⚠️ O `TestClient` guarda cookie entre chamadas — sem isto o teste passaria
    # por acidente numa suíte onde outro já tivesse feito login.
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/destaque")

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Marina Sena"


def test_logado_como_cliente_o_destaque_e_identico_ao_anonimo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A identidade de quem chama não influencia a capa.

    Os corpos **inteiros**, e não só o nome: a garantia é que nenhum campo a
    mais aparece para quem está logado.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Djavan")
    cliente.cookies.clear()
    anonimo = cliente.get("/eventos/destaque")

    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    entrada = cliente.post(
        "/auth/login", json={"email": comprador.email, "senha": "rockhub"}
    )
    assert entrada.status_code == 200

    logado = cliente.get("/eventos/destaque")

    assert logado.status_code == 200
    assert logado.json() == anonimo.json()


def test_o_destaque_e_o_de_menor_data_hora_e_nao_o_primeiro_inserido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O mais distante é gravado **primeiro**, de propósito.

    Sem o `order_by`, um `LIMIT 1` devolve o que o Postgres achar mais barato —
    e, num banco de teste com duas linhas, isso costuma ser a ordem de inserção.
    O teste passaria por acidente com os eventos gravados na ordem natural.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Depois", data_hora=_daqui_a(40))
    _evento_gravado(sessao, organizador, nome="Antes", data_hora=_daqui_a(5))
    cliente.cookies.clear()

    assert cliente.get("/eventos/destaque").json()["nome"] == "Antes"


def test_empate_de_data_hora_desempata_por_id_de_forma_estavel(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Dois shows no mesmo horário não podem trocar de lugar entre requisições.

    ⚠️ Sem `Evento.id` no `order_by`, o `LIMIT 1` sobre um empate é uma escolha
    do planejador — e a capa passaria a alternar entre dois shows a cada
    recarregar, sem que nada tivesse mudado no banco. Duas chamadas seguidas é
    o mínimo que expõe isso; o `min()` do lado direito é quem diz *qual* das
    duas respostas é a certa.
    """
    organizador = _organizador(fabricar_usuario)
    instante = _daqui_a(9)
    primeiro = _evento_gravado(sessao, organizador, nome="A", data_hora=instante)
    segundo = _evento_gravado(sessao, organizador, nome="B", data_hora=instante)
    cliente.cookies.clear()

    uma = cliente.get("/eventos/destaque").json()
    outra = cliente.get("/eventos/destaque").json()

    assert uma == outra
    # `UUID` se compara pelos 16 bytes, que é exatamente o critério do `uuid` do
    # Postgres — as duas pontas concordam sobre qual dos dois é o menor.
    assert uma["id"] == str(min(primeiro.id, segundo.id))


# --------------------------------------------------------------------------- #
# AC4 — o mesmo recorte da programação: rascunho e passado ficam fora
# --------------------------------------------------------------------------- #


def test_rascunho_nao_vira_destaque_mesmo_sendo_o_mais_proximo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O recorte é **idêntico** ao da `listar_programacao`, e não um parecido.

    O rascunho é o mais próximo de propósito: uma consulta que esquecesse a
    condição de `publicado_em` devolveria justamente ele.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(
        sessao, organizador, nome="Rascunho", data_hora=_daqui_a(1), publicado=False
    )
    _evento_gravado(sessao, organizador, nome="Publicado", data_hora=_daqui_a(30))
    cliente.cookies.clear()

    assert cliente.get("/eventos/destaque").json()["nome"] == "Publicado"


def test_evento_passado_nao_vira_destaque_mesmo_sendo_o_mais_proximo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O gêmeo do teste acima, para a outra condição do recorte.

    ⚠️ O evento passado é o de **menor** `data_hora` de todos — sem o
    `data_hora >= agora`, ele seria o destaque, e a capa do produto abriria com
    um show que já aconteceu.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Já aconteceu", data_hora=_daqui_a(-10))
    _evento_gravado(sessao, organizador, nome="Vai acontecer", data_hora=_daqui_a(10))
    cliente.cookies.clear()

    assert cliente.get("/eventos/destaque").json()["nome"] == "Vai acontecer"


# --------------------------------------------------------------------------- #
# AC3 — banco vazio responde `200` com corpo `null`
# --------------------------------------------------------------------------- #


def test_banco_sem_evento_publicado_e_futuro_responde_destaque_nulo(
    cliente: TestClient,
) -> None:
    """`200` com corpo `null` — **nunca `404`**, e nunca `204`.

    Mesma decisão do `200 []` da programação: "não há show em cartaz" é uma
    resposta sobre o produto, não um endereço que não existe. E `204` está fora
    porque ele **não tem corpo**: o `resposta.json()` da tela estouraria num
    `catch` que existe para falha de rede, e o "não há show" viraria "não foi
    possível carregar".
    """
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/destaque")

    assert resposta.status_code == 200
    assert resposta.json() is None


# --------------------------------------------------------------------------- #
# AC5, AC6 — o contrato da capa, e o estoque que continua sem atravessar
# --------------------------------------------------------------------------- #


def test_o_destaque_tem_exatamente_as_nove_chaves_do_contrato(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Igualdade de conjunto: campo a mais reprova tanto quanto a menos."""
    _evento_gravado(sessao, _organizador(fabricar_usuario))
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert set(destaque) == CHAVES_DO_DESTAQUE


def test_nenhuma_palavra_de_estoque_aparece_no_texto_do_destaque(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A varredura do texto inteiro, **sem `setores` e sem `imagem_url`**.

    ⚠️ Esta lista **não é** a do teste gêmeo de `GET /eventos`, e a diferença é
    a armadilha desta story. Ali `setores` e `imagem_url` são palavras
    proibidas; aqui as duas são **chaves legítimas** — a ficha mostra os nomes
    dos setores, e a capa mostra a arte. Nome de setor não é estoque;
    **contagem** é. Quem "consertar" este teste copiando a lista de lá vai vê-lo
    falhar, e apagar a asserção inteira jogaria fora a proteção do UX-DR7 numa
    rota que devolve um relacionamento — que é exatamente onde ela mais importa.

    O que continua proibido é o que conta ingresso (`capacidade`, `vendidos`,
    `preco_centavos`) e o que é assunto de quem publica (`publicado_em`,
    `origem_externa_id`, `organizador_id`).
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 137, 12000)],
    )
    cliente.cookies.clear()

    corpo = cliente.get("/eventos/destaque").text

    for palavra in (
        "capacidade",
        "vendidos",
        "preco_centavos",
        "publicado_em",
        "origem_externa_id",
        "organizador_id",
    ):
        assert palavra not in corpo


# --------------------------------------------------------------------------- #
# AC7, AC8 — os setores como nomes, e o esgotado derivado de `setor.vendidos`
# --------------------------------------------------------------------------- #


def test_os_setores_do_destaque_vem_em_ordem_alfabetica_so_com_nomes(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`list[str]`, e não `list[SetorSaida]` — e o esgotado entra junto.

    Gravados fora de ordem: quem ordena é o `order_by="Setor.nome"` do
    `relationship` (Story 2.3), não a ordem de inserção.

    ⚠️ A **Pista está esgotada** e continua na ficha: ela diz o que o show
    **tem**, não o que sobrou. Filtrar por disponibilidade aqui faria a lista
    mudar sozinha conforme as vendas, sem nenhuma pista do porquê.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[
            ("VIP", 100, 0, 30000),
            ("Pista", 800, 800, 12000),
            ("Camarote", 120, 0, 42000),
        ],
    )
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert destaque["setores"] == ["Camarote", "Pista", "VIP"]
    assert destaque["esgotado"] is False


def test_o_preco_minimo_da_capa_pula_o_setor_esgotado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Pista a R$ 120,00 esgotada, Camarote a R$ 420,00 com ingresso → 42000.

    O gêmeo do teste da fila (Story 3.1), agora na capa. A regra é a mesma e o
    motivo também: anunciar 12000 aqui seria a única forma de a capa mentir com
    número — o visitante clicaria esperando R$ 120,00 e encontraria R$ 420,00.

    ⚠️ Os setores **continuam os dois na ficha**, inclusive o esgotado: ela diz o
    que o show tem. É só o preço que pula.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 800, 12000), ("Camarote", 120, 0, 42000)],
    )
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert destaque["preco_minimo_centavos"] == 42000
    assert destaque["setores"] == ["Camarote", "Pista"]
    assert destaque["esgotado"] is False


def test_destaque_com_todos_os_setores_esgotados_continua_sendo_o_destaque(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Decisão do Igor: show esgotado é informação, não ruído.

    A alternativa — pular para o próximo com ingresso — faria "o próximo show"
    deixar de ser verdade, e a capa esconderia justamente o show mais próximo.
    O evento esgotado tem `data_hora` **menor** que o disponível aqui, e é ele
    que precisa voltar.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(
        sessao,
        organizador,
        nome="Esgotado",
        data_hora=_daqui_a(5),
        setores=[("Pista", 800, 800, 12000), ("Camarote", 120, 120, 42000)],
    )
    _evento_gravado(sessao, organizador, nome="Com ingresso", data_hora=_daqui_a(20))
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert destaque["nome"] == "Esgotado"
    assert destaque["esgotado"] is True
    # `min()` sobre lista vazia levantaria `ValueError` — e viraria `500` na raiz
    # do produto. A capa não anuncia preço nenhum quando não há o que comprar.
    assert destaque["preco_minimo_centavos"] is None


def test_destaque_sem_setor_nenhum_nao_quebra_a_rota(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Impossível pela rota de publicação, possível por `psql`.

    E existe no banco de desenvolvimento deste projeto — que é justamente onde
    a capa vai ser conferida a olho.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), setores=[])
    cliente.cookies.clear()

    resposta = cliente.get("/eventos/destaque")

    assert resposta.status_code == 200
    destaque = resposta.json()
    assert destaque["setores"] == []
    assert destaque["esgotado"] is True
    assert destaque["preco_minimo_centavos"] is None


# --------------------------------------------------------------------------- #
# AC5, AC17 — a arte, que é anulável desde a Story 2.3
# --------------------------------------------------------------------------- #


def test_a_arte_do_destaque_atravessa_o_contrato(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A primeira vez que `imagem_url` sai para o lado público.

    Ela é gravada desde a Story 2.4, copiada da Ticketmaster no ato da
    publicação, e ficou fora do contrato da programação apontando para esta
    story.
    """
    _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        imagem_url="https://s1.ticketm.net/dam/a/exemplo.jpg",
    )
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert destaque["imagem_url"] == "https://s1.ticketm.net/dam/a/exemplo.jpg"


def test_imagem_url_nula_volta_como_null_no_destaque(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A coluna é anulável, e a tela põe um bloco do mesmo tamanho no lugar.

    O que **não** pode acontecer é a chave sumir do corpo: a tela distingue
    "sem arte" de "campo que não veio", e um `exclude_none` no schema faria as
    duas coisas parecerem a mesma.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), imagem_url=None)
    cliente.cookies.clear()

    destaque = cliente.get("/eventos/destaque").json()

    assert destaque["imagem_url"] is None
    assert "imagem_url" in destaque


# --------------------------------------------------------------------------- #
# AC1, AC2 — o contrato declarado, e a rota sem parâmetro nenhum
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_o_destaque_sem_parametro_nenhum(
    cliente: TestClient,
) -> None:
    """Nem `query`, nem sessão — a rota não recebe nada.

    ⚠️ `parameters == []` é a asserção certa **aqui**, ao contrário do que
    aconteceu com `GET /eventos` na Story 3.2: aquela rota ganhou filtros e a
    frase deixou de caber. Esta não tem filtro por decisão — a capa é o próximo
    show, não o resultado de uma busca —, e se um `?q=` aparecer aqui um dia,
    esta linha é quem vai perguntar por quê.
    """
    esquema = cliente.get("/openapi.json").json()

    rota = esquema["paths"]["/eventos/destaque"]["get"]

    assert "security" not in rota
    assert rota.get("parameters", []) == []

    propriedades = esquema["components"]["schemas"]["EventoEmDestaque"]["properties"]
    assert set(propriedades) == CHAVES_DO_DESTAQUE


# =========================================================================== #
# Story 3.4 — ver o evento e seus setores
#
# `GET /eventos/{id}`: a quarta rota pública, e a única que abre o evento setor a
# setor. Tudo daqui para baixo é da 3.4, e **nenhum teste acima precisou mudar** —
# a rota é nova, as três antigas estão intactas e o helper não foi tocado. É o
# AC11 desta story, e ele é verificável relendo o diff.
#
# É também a rota que chega **mais perto do estoque** em todo o lado público: é
# nela que a pessoa escolhe quantos ingressos quer. Dois testes daqui existem só
# para isso — o das chaves e o da varredura de texto.
# =========================================================================== #

# As oito chaves do `EventoPublico`, e nenhuma a mais (AC5).
CHAVES_DO_EVENTO_PUBLICO = {
    "id",
    "nome",
    "data_hora",
    "local",
    "cidade",
    "imagem_url",
    "maximo_por_compra",
    "setores",
}

# As cinco de cada item de `setores` (AC5).
#
# ⚠️ Note o que **não** está aqui: `capacidade` e `vendidos`. O `SetorSaida` do
# organizador tem os dois, e ele está a um import de distância do service desta
# rota — reusá-lo "porque já existe um schema de setor" é a armadilha que este
# conjunto pega.
CHAVES_DO_SETOR_PUBLICO = {
    "id",
    "nome",
    "preco_centavos",
    "disponibilidade",
    "proporcao_vendida",
}


# --------------------------------------------------------------------------- #
# AC1 — pública por assinatura: responde sem cookie, e igual para todo mundo
# --------------------------------------------------------------------------- #


def test_o_evento_responde_sem_nenhum_cookie_de_sessao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A quarta rota pública do projeto, e o mesmo cuidado das três primeiras."""
    evento = _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    # ⚠️ O `TestClient` guarda cookie entre chamadas — sem isto o teste passaria
    # por acidente numa suíte onde outro já tivesse feito login.
    cliente.cookies.clear()

    resposta = cliente.get(f"/eventos/{evento.id}")

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Marina Sena"


def test_logado_como_cliente_o_evento_e_identico_ao_anonimo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A identidade de quem chama não influencia a página do evento.

    Os corpos **inteiros**, e não só o nome: a garantia que interessa é que nenhum
    campo a mais aparece para quem está logado — nem estoque, nem nada. É a rota
    em que essa diferença seria mais tentadora de introduzir, porque é a tela onde
    a pessoa vai comprar.
    """
    evento = _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Djavan")
    cliente.cookies.clear()
    anonimo = cliente.get(f"/eventos/{evento.id}")

    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    entrada = cliente.post(
        "/auth/login", json={"email": comprador.email, "senha": "rockhub"}
    )
    assert entrada.status_code == 200

    logado = cliente.get(f"/eventos/{evento.id}")

    assert logado.status_code == 200
    assert logado.json() == anonimo.json()


# --------------------------------------------------------------------------- #
# AC3, AC4 — o recorte, e o `404` único para os três casos
# --------------------------------------------------------------------------- #


def test_os_tres_casos_fora_de_cartaz_recebem_o_mesmo_404(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`id` inexistente, rascunho e evento passado: mesma resposta, palavra por
    palavra.

    ⚠️ **A asserção é sobre os três corpos serem iguais entre si**, e não sobre
    cada um ser `404`. Três `assert status == 404` passariam com três mensagens
    diferentes — e é justamente a diferença de mensagem que transformaria a rota
    num oráculo: "esse UUID é o rascunho de alguém?" seria respondível varrendo
    endereços. É a mesma disciplina do `EVENTO_NAO_ENCONTRADO` do organizador
    (Story 2.6) e do login da 1.4, que não diz se o e-mail existe.
    """
    organizador = _organizador(fabricar_usuario)
    rascunho = _evento_gravado(sessao, organizador, nome="Rascunho", publicado=False)
    passado = _evento_gravado(sessao, organizador, nome="Ontem", data_hora=_daqui_a(-3))
    cliente.cookies.clear()

    respostas = [
        cliente.get(f"/eventos/{uuid4()}"),
        cliente.get(f"/eventos/{rascunho.id}"),
        cliente.get(f"/eventos/{passado.id}"),
    ]

    for resposta in respostas:
        assert resposta.status_code == 404
        assert resposta.json()["erro"]["codigo"] == "EVENTO_NAO_ENCONTRADO"

    corpos = {resposta.text for resposta in respostas}
    assert len(corpos) == 1


def test_id_que_nao_e_uuid_recebe_422_do_pydantic(cliente: TestClient) -> None:
    """O path param é tipado `UUID`, então a recusa acontece antes da consulta.

    A tela trata `404` e `422` no **mesmo** ramo, como o `obterMeuEvento` da
    Story 2.6 já faz: para quem lê, "esse endereço está errado" e "esse show não
    está em cartaz" são a mesma coisa.
    """
    cliente.cookies.clear()

    assert cliente.get("/eventos/banana").status_code == 422


# --------------------------------------------------------------------------- #
# AC5, AC6 — o contrato, e o estoque que não atravessa
# --------------------------------------------------------------------------- #


def test_o_evento_tem_oito_chaves_e_cada_setor_tem_cinco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Igualdade de conjunto nos dois níveis: campo a mais reprova tanto quanto a
    menos.

    O setor é conferido **dentro** do evento, e não num schema à parte: é o
    aninhamento que um teste de chaves de topo deixaria passar, e é exatamente
    onde `capacidade` entraria se alguém reusasse o `SetorSaida`.
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 137, 12000), ("Área VIP", 100, 80, 26000)],
    )
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").json()

    assert set(corpo) == CHAVES_DO_EVENTO_PUBLICO
    assert len(corpo["setores"]) == 2
    for setor in corpo["setores"]:
        assert set(setor) == CHAVES_DO_SETOR_PUBLICO


def test_nenhuma_palavra_de_contagem_aparece_no_texto_do_evento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A varredura do texto inteiro — e esta é a **terceira** lista deste arquivo.

    ⚠️ **Não copie a de `GET /eventos` nem a de `/eventos/destaque`.** Na 3.1
    `setores` e `imagem_url` eram proibidas; na 3.3 as duas viraram legítimas;
    aqui **`preco_centavos` também é** — é o preço de cada setor, e é a
    informação principal da tela: ninguém escolhe entre Pista e Camarote sem
    saber quanto custa cada um. Preço não é contagem.

    O que continua proibido é o que **conta ingresso** — `capacidade` e
    `vendidos` — e o que é assunto de quem publica: `publicado_em`,
    `origem_externa_id`, `organizador_id`.

    ⚠️ **Se este teste falhar, não apague a asserção.** Esta é a rota pública que
    chega mais perto do estoque, e a proteção do UX-DR7 vale mais aqui do que nas
    outras três. Falha aqui significa que um campo de contagem atravessou o
    `response_model` — ou que alguém nomeou o campo derivado
    `proporcao_vendidos`, no plural masculino, e casou a palavra proibida sem
    querer. É `proporcao_vendida`, concordando com "proporção", e o nome é
    escolhido justamente para não colidir.
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 800, 137, 12000)],
    )
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").text

    for palavra in (
        "capacidade",
        "vendidos",
        "publicado_em",
        "origem_externa_id",
        "organizador_id",
    ):
        assert palavra not in corpo


def test_imagem_url_nula_volta_como_null_no_evento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A chave **continua no corpo** quando é nula, como na capa da 3.3.

    A tela distingue "sem arte" — bloco do mesmo tamanho no lugar — de "campo que
    não veio", e um `exclude_none` no schema faria as duas coisas parecerem a
    mesma.
    """
    evento = _evento_gravado(sessao, _organizador(fabricar_usuario), imagem_url=None)
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").json()

    assert corpo["imagem_url"] is None
    assert "imagem_url" in corpo


# --------------------------------------------------------------------------- #
# AC7 — a proporção, que é o que substitui os dois números
# --------------------------------------------------------------------------- #


def test_a_proporcao_vendida_e_a_divisao_arredondada_em_duas_casas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`0.39`, `0.0` e `1.0` — os três extremos da largura da barra.

    39/100 é o caso do meio e é escolhido de propósito: ele só bate se a conta
    for `vendidos / capacidade`. Um setor com 50/100 passaria por acidente com
    meia dúzia de contas erradas.
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[
            ("Camarote", 100, 39, 42000),
            ("Mezanino", 50, 0, 18000),
            ("Pista", 50, 50, 12000),
        ],
    )
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").json()
    proporcoes = {
        setor["nome"]: setor["proporcao_vendida"] for setor in corpo["setores"]
    }

    assert proporcoes == {"Camarote": 0.39, "Mezanino": 0.0, "Pista": 1.0}


# --------------------------------------------------------------------------- #
# AC8 — os três estados, e a borda dos 20%
# --------------------------------------------------------------------------- #


def test_os_tres_estados_de_disponibilidade_com_a_borda_dos_vinte_por_cento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A borda é o teste, e os três setores têm **15 lugares** por isso.

    ⚠️ 12 vendidos de 15 deixa **exatamente** 20% — é o caso em que
    `(15 - 12) <= 15 * 0.2` depende de arredondamento binário e o `float` decide
    sozinho. A conta do service é em inteiros (`restam * 5 <= capacidade`), e é
    esta linha que prova que ela está lá: 11/15 (26,7% restante) é
    `DISPONIVEL`, 12/15 é `ULTIMOS`.

    ⚠️ E 15/15 é `ESGOTADO`, não `ULTIMOS`: zero restante também é "20% ou
    menos", e é a **ordem** das condições no service que decide — esgotado
    primeiro, sempre. Com as duas trocadas, o setor acabado apareceria como
    "Últimos ingressos", com a barra cheia e a palavra errada.
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[
            ("A tranquila", 15, 11, 12000),
            ("B na borda", 15, 12, 18000),
            ("C acabada", 15, 15, 26000),
        ],
    )
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").json()
    estados = {setor["nome"]: setor["disponibilidade"] for setor in corpo["setores"]}

    assert estados == {
        "A tranquila": "DISPONIVEL",
        "B na borda": "ULTIMOS",
        "C acabada": "ESGOTADO",
    }


# --------------------------------------------------------------------------- #
# AC9 — todos os setores, em ordem alfabética
# --------------------------------------------------------------------------- #


def test_os_setores_vem_em_ordem_alfabetica_incluindo_o_esgotado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Gravados fora de ordem: quem ordena é o `order_by="Setor.nome"` do
    `relationship` (Story 2.3), não a ordem de inserção nem um `sorted()`.

    ⚠️ **A Pista está esgotada e continua na lista.** A tela a esmaece e tira o
    stepper dela; sumir com ela faria a pessoa procurar o setor que o amigo
    comprou na semana passada e concluir que o site está quebrado.
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[
            ("Pista", 800, 800, 12000),
            ("Camarote", 60, 10, 42000),
            ("Área VIP", 100, 20, 26000),
        ],
    )
    cliente.cookies.clear()

    corpo = cliente.get(f"/eventos/{evento.id}").json()

    assert [setor["nome"] for setor in corpo["setores"]] == [
        "Área VIP",
        "Camarote",
        "Pista",
    ]


def test_evento_sem_setor_nenhum_nao_quebra_a_rota_do_evento(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`setores: []`, e `200`.

    Impossível pela rota de publicação (`EVENTO_SEM_SETOR`) e possível por `psql`
    — e existe no banco de desenvolvimento do Igor, o que faz deste um caminho
    que a conferência visual atravessa de verdade.
    """
    evento = _evento_gravado(sessao, _organizador(fabricar_usuario), setores=[])
    cliente.cookies.clear()

    resposta = cliente.get(f"/eventos/{evento.id}")

    assert resposta.status_code == 200
    assert resposta.json()["setores"] == []


# --------------------------------------------------------------------------- #
# AC10 — o teto fixo por compra
# --------------------------------------------------------------------------- #


def test_o_maximo_por_compra_e_seis_e_nao_varia_com_o_estoque(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Um setor com **2 ingressos restantes**, e o teto continua `6`.

    ⚠️ É este o teste que trava a decisão do Igor. `maximo_por_compra =
    min(disponivel, 6)` daria um stepper mais honesto — e diria "restam 2" pela
    tela e pelo devtools toda vez que restassem poucos, que é exatamente o que o
    UX-DR7 mantém fora da tela do cliente. Quem recusa o pedido maior do que
    existe é o `UPDATE` condicional do AD-3, na Story 3.6.

    O evento com estoque folgado entra na mesma comparação: o ponto não é que o
    número seja 6, é que ele seja **o mesmo** nos dois casos.
    """
    organizador = _organizador(fabricar_usuario)
    apertado = _evento_gravado(
        sessao, organizador, nome="Quase esgotado", setores=[("Pista", 100, 98, 12000)]
    )
    folgado = _evento_gravado(
        sessao, organizador, nome="Recém-aberto", setores=[("Pista", 800, 0, 12000)]
    )
    cliente.cookies.clear()

    teto_apertado = cliente.get(f"/eventos/{apertado.id}").json()["maximo_por_compra"]
    teto_folgado = cliente.get(f"/eventos/{folgado.id}").json()["maximo_por_compra"]

    assert teto_apertado == 6
    assert teto_apertado == teto_folgado


# --------------------------------------------------------------------------- #
# AC2 — a ordem de declaração das rotas no router
# --------------------------------------------------------------------------- #


def test_as_duas_rotas_de_path_fixo_continuam_de_pe_depois_do_detalhe_existir(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A regressão que esta story torna possível — e o motivo do comentário no
    `publico.py`.

    ⚠️ `/eventos/cidades` e `/eventos/destaque` são paths **fixos**, e
    `/eventos/{evento_id}` é path param no mesmo router. O FastAPI casa as rotas
    na ordem em que foram registradas: com o detalhe declarado antes das duas,
    uma chamada a `/eventos/cidades` tentaria ler `"cidades"` como UUID e
    devolveria `422`.

    E o sintoma apareceria longe da causa: a raiz perderia os chips de cidade e a
    capa sumiria, sem que nada ligasse isso a uma rota nova de **detalhe**. Sem
    este teste, a regressão só aparece na tela.

    O comentário do bloco de ordem no `publico.py` foi escrito na Story 3.2
    apontando para esta story; é aqui que ele para de ser precaução.
    """
    _evento_gravado(sessao, _organizador(fabricar_usuario), nome="Marina Sena")
    cliente.cookies.clear()

    cidades = cliente.get("/eventos/cidades")
    destaque = cliente.get("/eventos/destaque")

    assert cidades.status_code == 200
    assert cidades.json() == ["São Paulo"]

    assert destaque.status_code == 200
    assert destaque.json()["nome"] == "Marina Sena"


# --------------------------------------------------------------------------- #
# AC1, AC5 — o contrato declarado, e a rota sem parâmetro de query nem de sessão
# --------------------------------------------------------------------------- #


def test_o_openapi_declara_o_evento_com_um_parametro_de_path_e_nada_mais(
    cliente: TestClient,
) -> None:
    """Um `path`, zero `query`, zero segurança.

    Se alguém acrescentar `Depends(exigir_papel(...))` aqui um dia, a rota passa a
    declarar o cookie no OpenAPI — e este teste cai antes de o sintoma chegar à
    tela do visitante. Um `?quantidade=` também: esta tela não filtra nada, e o
    dia em que ela receber um parâmetro é o dia de perguntar por quê.
    """
    esquema = cliente.get("/openapi.json").json()

    rota = esquema["paths"]["/eventos/{evento_id}"]["get"]

    assert "security" not in rota
    assert [parametro["in"] for parametro in rota["parameters"]] == ["path"]
    assert rota["parameters"][0]["name"] == "evento_id"

    evento = esquema["components"]["schemas"]["EventoPublico"]["properties"]
    assert set(evento) == CHAVES_DO_EVENTO_PUBLICO

    setor = esquema["components"]["schemas"]["SetorPublico"]["properties"]
    assert set(setor) == CHAVES_DO_SETOR_PUBLICO


# --------------------------------------------------------------------------- #
# Code review da Epic 3 — o curinga que o `unaccent` fabricava, e a busca
# com mais de uma palavra
# --------------------------------------------------------------------------- #


def test_curinga_fullwidth_nao_devolve_a_programacao_inteira(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **O mesmo defeito do `?q=%`, por uma porta que o escape não cobria.**

    O escape rodava em Python e o `unaccent` no Postgres, nessa ordem — e
    `unaccent` normaliza as formas *fullwidth*: `unaccent('％')` (U+FF05) devolve
    `'%'`, `unaccent('＿')` devolve `'_'`. O curinga era **fabricado depois** de a
    proteção já ter passado, e `?q=％` virava o padrão `%%%`: a programação
    inteira, com `200` e cara de resultado, que é exatamente o desfecho que o
    `test_buscar_por_porcento_nao_devolve_a_programacao_inteira` existe para
    impedir.

    O conserto foi inverter a ordem — `unaccent` primeiro, escape em SQL sobre o
    resultado. Ver `_padrao_de_busca` em `services/evento.py`.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena")
    _evento_gravado(sessao, organizador, nome="Djavan")
    cliente.cookies.clear()

    # U+FF05 FULLWIDTH PERCENT SIGN e U+FF3F FULLWIDTH LOW LINE.
    assert _nomes(cliente.get("/eventos", params={"q": "\uff05"})) == []
    assert _nomes(cliente.get("/eventos", params={"q": "\uff3f"})) == []


def test_busca_com_duas_palavras_cruza_nome_e_cidade(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Artista + cidade é o que se digita primeiro, e devolvia vazio.

    O termo era um substring único testado contra `nome`, `local` e `cidade` com
    `OR`: nenhuma coluna sozinha contém `"marina são paulo"`, então a resposta era
    `200 []` — indistinguível de "esse show não existe". Agora cada palavra
    precisa aparecer em alguma das três colunas (`AND` de `OR`s).
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena", cidade="São Paulo")
    _evento_gravado(sessao, organizador, nome="Marina Sena", cidade="Recife")
    _evento_gravado(sessao, organizador, nome="Djavan", cidade="São Paulo")
    cliente.cookies.clear()

    resposta = cliente.get("/eventos", params={"q": "marina sao paulo"})

    # Só o que casa as duas palavras — e sem acento, pelo `unaccent`.
    assert _nomes(resposta) == ["Marina Sena"]
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["cidade"] == "São Paulo"


def test_palavra_que_nao_casa_nenhuma_coluna_derruba_o_resultado_inteiro(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O `AND` entre palavras é o que dá sentido à busca de duas palavras.

    Sem ele bastaria uma palavra casar para o evento entrar, e `?q=marina
    curitiba` traria a Marina de São Paulo — pior que devolver vazio, porque
    parece resposta.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena", cidade="São Paulo")
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"q": "marina curitiba"})) == []


def test_espacos_entre_as_palavras_nao_criam_termo_vazio(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`split()` sem argumento colapsa espaço repetido — e é por isso que é ele.

    Com `split(" ")`, `"marina  sena"` produziria um token vazio, cujo padrão
    `%%` casa tudo: a condição extra não filtraria nada e o `AND` viraria enfeite.
    """
    organizador = _organizador(fabricar_usuario)
    _evento_gravado(sessao, organizador, nome="Marina Sena")
    _evento_gravado(sessao, organizador, nome="Djavan")
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos", params={"q": "marina   sena"})) == [
        "Marina Sena"
    ]


def test_barra_nao_enche_enquanto_ainda_ha_ingresso(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ Barra cheia é reservada a quem esgotou — o resto tem teto de `0.99`.

    `round(999/1000, 2)` é `1.0`, e nesse ponto a disponibilidade ainda é
    `ULTIMOS`: a tela mostrava a barra em 100% ao lado de "últimos ingressos",
    com o stepper ativo, indistinguível de esgotado. É o mesmo sintoma que a
    ordem das condições do `_disponibilidade_do_setor` previne, reintroduzido
    pelo arredondamento em capacidade grande (code review da Epic 3).
    """
    evento = _evento_gravado(
        sessao,
        _organizador(fabricar_usuario),
        setores=[("Pista", 1000, 999, 12000), ("Camarote", 1000, 1000, 30000)],
    )
    cliente.cookies.clear()

    setores = {s["nome"]: s for s in cliente.get(f"/eventos/{evento.id}").json()["setores"]}

    assert setores["Pista"]["disponibilidade"] == "ULTIMOS"
    assert setores["Pista"]["proporcao_vendida"] == 0.99

    # Quem de fato esgotou continua chegando a 1.0.
    assert setores["Camarote"]["disponibilidade"] == "ESGOTADO"
    assert setores["Camarote"]["proporcao_vendida"] == 1.0


def test_a_programacao_tem_teto_de_linhas(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rota da tela mais visitada não devolve o catálogo inteiro sem limite.

    O teto real é `TETO_DA_PROGRAMACAO`; aqui ele é baixado para três, porque
    gravar 201 eventos para provar um `LIMIT` é custo sem informação. O que o
    teste prova é que **existe** um teto e que ele corta pelo fim da fila
    ordenada por data — o show mais distante é o que fica de fora.
    """
    monkeypatch.setattr(servico_de_evento, "TETO_DA_PROGRAMACAO", 3)

    organizador = _organizador(fabricar_usuario)
    for dias in (5, 10, 15, 20, 25):
        _evento_gravado(
            sessao,
            organizador,
            nome=f"Show em {dias} dias",
            data_hora=_daqui_a(dias),
        )
    cliente.cookies.clear()

    assert _nomes(cliente.get("/eventos")) == [
        "Show em 5 dias",
        "Show em 10 dias",
        "Show em 15 dias",
    ]
