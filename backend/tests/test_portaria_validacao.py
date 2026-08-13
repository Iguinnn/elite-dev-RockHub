"""`POST /portaria/eventos/{id}/validacoes` — o veredito da porta (Story 5.2).

Precisa do Compose no ar: faz login de verdade e escreve `usado_em` no Postgres
da suíte.

**A primeira escrita da Epic 5, e a primeira do projeto feita por quem não é
dono do que escreve.** Toda escrita anterior tinha o `cliente_id` da sessão no
`where`; aqui o `where` é o **código**, e quem autoriza é o vínculo do AD-7,
numa dependência que roda antes do handler.

**Quatro coisas que este arquivo existe para travar:**

- **Os quatro vereditos respondem `200`.** Recusar entrada é o trabalho da
  portaria dando certo, não uma falha de protocolo. Os `403` daqui são de outra
  natureza: "você não trabalha aqui" e "a porta ainda não abriu".
- **A dupla entrada é decidida pelo banco** (AD-6), não por um `if` em Python. É
  a mesma garantia do AD-3 na Story 3.6, e ela só se prova com duas conexões.
- **A assinatura é recalculada** (AD-5). A coluna `codigo` acha a linha e não
  participa da comparação — o teste do código adulterado é o que separa as duas
  coisas.
- **O `403` acontece antes de o ingresso ser consultado.** Contar consultas
  seria caro; confirmar que `usado_em` continua nulo depois da recusa é barato e
  pega o caso que importa.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.seguranca import gerar_codigo, gerar_hash, gerar_nonce
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.services import ingresso as servico_de_ingresso

# O alfabeto do código, repetido aqui de propósito: `_trocar_um_simbolo` precisa
# de um símbolo **diferente** e legítimo, e importar o `_ALFABETO` privado de
# `core/seguranca.py` acoplaria o teste a um detalhe que aquele módulo não
# exporta.
_SIMBOLOS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _daqui_a(**intervalo: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**intervalo)


def _evento_gravado(
    sessao: Session,
    organizador: Usuario,
    *,
    nome: str = "Baco Exu do Blues",
    data_hora: datetime | None = None,
    portarias: list[Usuario] | None = None,
    publicado: bool = True,
    setor_nome: str = "Pista",
) -> tuple[Evento, Setor]:
    """Um evento com um setor e a escala escolhida, gravado direto pelo ORM.

    ⚠️ **O padrão é daqui a uma hora, ou seja, com a porta já aberta.** A janela
    é `data_hora - 2h`, e um evento a 30 dias — o padrão dos outros arquivos —
    faria toda chamada deste aqui responder `403 EVENTO_NAO_ABERTO`. Os testes
    do portão escolhem a data explicitamente.

    Não passa por `POST /organizador/eventos` pelo mesmo motivo do
    `test_portaria_turnos.py`: `publicar` recusa data no passado, e um dos casos
    que mais importam aqui é o show que já começou.
    """
    evento = Evento(
        organizador_id=organizador.id,
        nome=nome,
        data_hora=data_hora or _daqui_a(hours=1),
        local="Espaço Unimed",
        cidade="São Paulo",
        origem_externa_id="G5vYZ9a1kd",
        publicado_em=datetime.now(timezone.utc) if publicado else None,
        setores=[
            Setor(nome=setor_nome, capacidade=800, vendidos=1, preco_centavos=12000)
        ],
        portarias=portarias if portarias is not None else [],
    )
    sessao.add(evento)
    sessao.flush()
    sessao.refresh(evento)
    return evento, evento.setores[0]


def _ingresso_gravado(
    sessao: Session,
    comprador: Usuario,
    evento: Evento,
    setor: Setor,
    *,
    codigo: str | None = None,
    usado_em: datetime | None = None,
    validado_por: Usuario | None = None,
) -> Ingresso:
    """Uma reserva `PAGA` com um ingresso emitido, gravadas direto pelo ORM.

    Mesmo helper do `test_meus_ingressos.py`, com uma diferença: `codigo` pode
    ser forçado. É o que permite gravar um ingresso cuja coluna **não** é o HMAC
    das próprias colunas — o cenário do código adulterado, que é o único jeito
    de provar que a validação recalcula em vez de comparar com a coluna.

    `pagador_nome` é diferente do nome da conta de propósito: com os dois iguais,
    uma resposta que lesse a coluna errada passaria batido.
    """
    reserva = Reserva(
        cliente_id=comprador.id,
        evento_id=evento.id,
        estado=EstadoReserva.PAGA.value,
        expira_em=_daqui_a(minutes=10),
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
        pagador_nome=f"Cartão de {comprador.nome}",
        codigo=codigo or gerar_codigo(ingresso_id, evento.id, nonce),
        nonce=nonce,
        usado_em=usado_em,
        validado_por=validado_por.id if validado_por else None,
    )
    sessao.add(ingresso)
    sessao.flush()
    sessao.refresh(ingresso)
    return ingresso


def _trocar_um_simbolo(codigo: str) -> str:
    """O mesmo código com o primeiro símbolo trocado por outro do alfabeto.

    ⚠️ **Adulteração garantida, e é a lição do code review da Epic 4.** Lá o
    teste de forja mexia no **último** caractere de uma assinatura base64 — que
    em ~4,7% dos casos não adultera nada, porque os bits de padding do fim não
    entram no valor. O teste passava sem ter forjado. Aqui cada símbolo são 5
    bits inteiros do HMAC truncado, e trocá-lo por outro do alfabeto muda o valor
    sempre.
    """
    posicao_atual = _SIMBOLOS.index(codigo[0])
    return _SIMBOLOS[(posicao_atual + 1) % len(_SIMBOLOS)] + codigo[1:]


def _validar(cliente: TestClient, evento: Evento, codigo: str) -> dict:
    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": codigo}
    )
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()


def _cenario(
    sessao: Session, fabricar_usuario: Callable[..., Usuario], sufixo: str
) -> tuple[Usuario, Usuario, Usuario]:
    """Organizador, comprador e a portaria escalada — os três de todo teste daqui."""
    return (
        fabricar_usuario(PapelUsuario.ORGANIZADOR, f"org-{sufixo}@exemplo.com"),
        fabricar_usuario(PapelUsuario.CLIENTE, f"cli-{sufixo}@exemplo.com"),
        fabricar_usuario(PapelUsuario.PORTARIA, f"porta-{sufixo}@exemplo.com"),
    )


# --------------------------------------------------------------------------- #
# VALIDO: deixa entrar uma vez, e grava quem deixou
# --------------------------------------------------------------------------- #


def test_codigo_valido_responde_valido_com_titular_setor_e_hora(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O caso feliz, com os três campos que só ele preenche.

    ⚠️ **`titular_nome` é o nome da conta**, e não o `pagador_nome` do checkout —
    o mesmo nome que o canhoto mostra. Quem chega com o ingresso na mão vê o que
    a portaria lê, e a conferência com o documento tem resposta. A fixture grava
    os dois diferentes justamente para esta asserção ter o que provar.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "ok")
    evento, setor = _evento_gravado(
        sessao, organizador, portarias=[porteiro], setor_nome="Camarote"
    )
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, porteiro)

    corpo = _validar(cliente, evento, ingresso.codigo)

    assert corpo["resultado"] == "VALIDO"
    assert corpo["titular_nome"] == comprador.nome
    assert corpo["setor_nome"] == "Camarote"
    assert corpo["entrada_em"] is not None


def test_validar_grava_usado_em_e_validado_por_na_linha(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A resposta é uma coisa; o que ficou no banco é outra, e é ela que vale.

    ⚠️ **`entrada_em` da resposta tem de ser o `usado_em` da coluna.** Sem o
    `RETURNING`, o objeto em memória continuaria com `None` (`expire_on_commit=
    False`) e a resposta sairia com `entrada_em: null` num `VALIDO` — a terceira
    aparição desta armadilha no projeto.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "grava")
    evento, setor = _evento_gravado(sessao, organizador, portarias=[porteiro])
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, porteiro)

    corpo = _validar(cliente, evento, ingresso.codigo)

    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert gravado.usado_em is not None
    assert gravado.validado_por == porteiro.id
    assert corpo["entrada_em"].startswith(
        gravado.usado_em.astimezone(timezone.utc).isoformat()[:19]
    )


def test_codigo_com_espacos_hifens_e_minusculas_vale_o_mesmo(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """É o que o campo manual da Story 5.3 vai receber de quem digita na fila.

    A normalização é do `normalizar_codigo`, dentro do service — não do schema.
    Este teste é o que garante que a rota inteira a exercita, e não só a função.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "sujo")
    evento, setor = _evento_gravado(sessao, organizador, portarias=[porteiro])
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, porteiro)

    sujo = f" {ingresso.codigo[:4].lower()}-{ingresso.codigo[4:].lower()} "

    corpo = _validar(cliente, evento, sujo)

    assert corpo["resultado"] == "VALIDO"


# --------------------------------------------------------------------------- #
# JA_UTILIZADO: a segunda leitura do mesmo ingresso
# --------------------------------------------------------------------------- #


def test_o_mesmo_ingresso_de_novo_responde_ja_utilizado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **A hora é a da PRIMEIRA entrada**, e é aí que a armadilha mora.

    O caminho do `JA_UTILIZADO` não passa por `RETURNING` nenhum — o `UPDATE`
    casou zero linhas. Sem reler a linha, o objeto em memória ainda tem
    `usado_em = None` (`expire_on_commit=False`) e a resposta sai dizendo "já
    utilizado" sem dizer quando, que é a única informação que resolve a discussão
    na porta.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "duas")
    evento, setor = _evento_gravado(sessao, organizador, portarias=[porteiro])
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, porteiro)

    primeira = _validar(cliente, evento, ingresso.codigo)
    segunda = _validar(cliente, evento, ingresso.codigo)

    assert primeira["resultado"] == "VALIDO"
    assert segunda["resultado"] == "JA_UTILIZADO"
    assert segunda["entrada_em"] == primeira["entrada_em"]
    assert segunda["titular_nome"] == comprador.nome
    # Ninguém vai entrar: apontar o setor não serve para nada aqui.
    assert segunda["setor_nome"] is None


def test_a_segunda_validacao_nao_reescreve_quem_validou(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O `WHERE usado_em IS NULL` protege as duas colunas, não só uma.

    Sem ele, a segunda leitura carimbaria a portaria da vez por cima da primeira
    — e o registro de quem deixou entrar, que é o motivo de a coluna existir,
    passaria a apontar para quem **não** deixou.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "reescreve")
    colega = fabricar_usuario(PapelUsuario.PORTARIA, "colega-reescreve@exemplo.com")
    evento, setor = _evento_gravado(
        sessao, organizador, portarias=[porteiro, colega]
    )
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)

    _entrar(cliente, porteiro)
    _validar(cliente, evento, ingresso.codigo)
    cliente.cookies.clear()
    _entrar(cliente, colega)
    segunda = _validar(cliente, evento, ingresso.codigo)

    assert segunda["resultado"] == "JA_UTILIZADO"
    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert gravado.validado_por == porteiro.id


# --------------------------------------------------------------------------- #
# INVALIDO: o que não é código deste sistema, e o que não confere
# --------------------------------------------------------------------------- #


def test_codigo_adulterado_na_coluna_responde_invalido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **O teste que separa "achar a linha" de "conferir a assinatura".**

    A linha existe e é achada **pelo** código; o que não bate é o recálculo do
    HMAC a partir de `id`, `evento_id` e `nonce` (AD-5). Se a validação comparasse
    com a coluna, este ingresso entraria — e bastaria a alguém conseguir escrever
    numa coluna para forjar entrada.

    O símbolo trocado é garantido diferente, e o porquê está em
    `_trocar_um_simbolo`: é a lição do teste de forja da Epic 4.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "adulterado")
    evento, setor = _evento_gravado(sessao, organizador, portarias=[porteiro])
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    legitimo = gerar_codigo(ingresso.id, evento.id, ingresso.nonce)
    ingresso.codigo = _trocar_um_simbolo(legitimo)
    sessao.flush()
    _entrar(cliente, porteiro)

    corpo = _validar(cliente, evento, ingresso.codigo)

    assert corpo["resultado"] == "INVALIDO"
    assert corpo["titular_nome"] is None
    gravado = sessao.get(Ingresso, ingresso.id)
    assert gravado is not None
    assert gravado.usado_em is None


def test_codigo_bem_formado_de_nenhum_ingresso_responde_invalido(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Colapsado com a assinatura divergente **de propósito**.

    O `EXPERIENCE.md` fixa quatro vereditos, cada um com cor, palavra e símbolo
    próprios, e "assinatura não confere" continua verdadeiro: sem linha, não há
    assinatura que confira. Um quinto veredito transformaria a rota num oráculo
    de "esse código existe?", a mesma disciplina do `404` único do
    `_carregar_do_cliente` e do login da Story 1.4.
    """
    organizador, _, porteiro = _cenario(sessao, fabricar_usuario, "fantasma")
    evento, _ = _evento_gravado(sessao, organizador, portarias=[porteiro])
    _entrar(cliente, porteiro)

    # Bem formado: 8 símbolos do alfabeto de Crockford, e de ingresso nenhum.
    corpo = _validar(cliente, evento, "ZZZZZZZZ")

    assert corpo["resultado"] == "INVALIDO"


def test_lixo_da_camera_responde_invalido_sem_tocar_no_banco(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Tamanho errado, símbolo fora do alfabeto e não-ASCII, todos `INVALIDO`.

    ⚠️ **O acento é o caso que já derrubou a rota antes de ela existir.** A
    guarda de não-ASCII entrou em `normalizar_codigo` no code review da Epic 3:
    sem ela, `hmac.compare_digest` levanta `TypeError` fora do ASCII e um QR que
    decodificasse com acento virava `500 ERRO_INTERNO` na fila da porta, para um
    código simplesmente inválido.

    O `U` está na lista porque ele **não** é do alfabeto de Crockford — nem `I`,
    `L` e `O`, que entram como sinônimos de `1`, `1` e `0`.
    """
    organizador, _, porteiro = _cenario(sessao, fabricar_usuario, "lixo")
    evento, _ = _evento_gravado(sessao, organizador, portarias=[porteiro])
    _entrar(cliente, porteiro)

    for entrada in ("", "ABC", "ABCDEFGHIJ", "AÇÃOAÇÃO", "UUUUUUUU", "https://x/y"):
        corpo = _validar(cliente, evento, entrada)
        assert corpo["resultado"] == "INVALIDO", entrada


def test_corpo_absurdamente_grande_e_recusado_como_requisicao_invalida(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """`422`, e não `INVALIDO` — a diferença é deliberada.

    Passar de 64 caracteres não é um código recusado, é um pedido malformado: o
    teto existe para um corpo de 10 MB não ser 10 MB varridos pelo
    `.upper().translate()` do normalizador, mesmo motivo dos limites de
    `schemas/pagamento.py` e `schemas/auth.py`. Nada que uma câmera deste sistema
    produza chega perto: o código tem 8 símbolos.
    """
    organizador, _, porteiro = _cenario(sessao, fabricar_usuario, "gigante")
    evento, _ = _evento_gravado(sessao, organizador, portarias=[porteiro])
    _entrar(cliente, porteiro)

    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": "A" * 5000}
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# EVENTO_ERRADO: o ingresso é de outro show — e não é queimado
# --------------------------------------------------------------------------- #


def test_ingresso_de_outro_evento_responde_evento_errado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **E a resposta não diz de qual show o ingresso é** (decisão do Igor).

    O protótipo do `EXPERIENCE.md` pedia "ESTE INGRESSO É DO SHOW DA CÉU". Uma
    portaria que não foi escalada no outro evento acabaria recebendo o nome dele
    de volta — e restringir exatamente isso é o motivo de o AD-7 existir. Quem
    está na fila sabe qual ingresso comprou.

    ⚠️ **A assinatura foi conferida contra o `evento_id` do INGRESSO**, e é por
    isso que este caso não cai em `INVALIDO`. Conferir contra o evento do caminho
    faria um código legítimo de outro show falhar como assinatura divergente:
    dois vereditos trocados, e a fila recebe a palavra errada.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "outro")
    daqui, setor_daqui = _evento_gravado(
        sessao, organizador, nome="O show desta porta", portarias=[porteiro]
    )
    de_la, setor_de_la = _evento_gravado(
        sessao, organizador, nome="O show da Céu", portarias=[porteiro]
    )
    ingresso = _ingresso_gravado(sessao, comprador, de_la, setor_de_la)
    _entrar(cliente, porteiro)

    corpo = _validar(cliente, daqui, ingresso.codigo)

    assert corpo["resultado"] == "EVENTO_ERRADO"
    assert corpo["titular_nome"] is None
    assert corpo["setor_nome"] is None
    assert "Céu" not in str(corpo)
    assert setor_de_la.nome not in str(corpo)


def test_ingresso_de_outro_evento_nao_e_queimado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **A ordem `EVENTO_ERRADO` antes do `UPDATE` não é estética.**

    Invertida, o ingresso do outro show sairia com `usado_em` gravado por uma
    portaria que nem podia lê-lo — e na noite daquele evento a pessoa seria
    barrada com `JA_UTILIZADO` sem nunca ter entrado. A resposta continuaria
    `EVENTO_ERRADO`, então nenhuma asserção sobre o corpo pegaria isso.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "queima")
    daqui, _ = _evento_gravado(sessao, organizador, nome="Esta porta", portarias=[porteiro])
    de_la, setor_de_la = _evento_gravado(
        sessao, organizador, nome="A outra porta", portarias=[porteiro]
    )
    ingresso = _ingresso_gravado(sessao, comprador, de_la, setor_de_la)
    _entrar(cliente, porteiro)

    _validar(cliente, daqui, ingresso.codigo)

    intacto = sessao.get(Ingresso, ingresso.id)
    assert intacto is not None
    assert intacto.usado_em is None
    assert intacto.validado_por is None


# --------------------------------------------------------------------------- #
# As duas recusas da dependência: o vínculo (AD-7) e o portão
# --------------------------------------------------------------------------- #


def test_portaria_sem_escala_recebe_403_e_o_ingresso_nao_e_tocado(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """AD-7: papel diz o que a pessoa faz, a `evento_portaria` diz **onde**.

    ⚠️ **A segunda asserção é a que protege o AC.** Ele exige a recusa "antes de
    qualquer consulta ao ingresso", e um teste que conte consultas é caro. Este
    é barato e pega o caso que importa: se alguém "melhorar" a rota carregando o
    ingresso antes da dependência, o `usado_em` deixa de ser nulo aqui.
    """
    organizador, comprador, _ = _cenario(sessao, fabricar_usuario, "sem-escala")
    de_fora = fabricar_usuario(PapelUsuario.PORTARIA, "de-fora@exemplo.com")
    evento, setor = _evento_gravado(sessao, organizador, portarias=[])
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, de_fora)

    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": ingresso.codigo}
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_ESCALA_NO_EVENTO"
    intacto = sessao.get(Ingresso, ingresso.id)
    assert intacto is not None
    assert intacto.usado_em is None


def test_evento_inexistente_responde_a_mesma_recusa_do_sem_escala(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """E **não** `404`: quem não está escalado não descobre se o evento existe.

    Distinguir os dois transformaria a rota num oráculo de "esse UUID é um
    evento?" para quem não trabalha nele — a mesma disciplina do `404` único do
    `_carregar_do_cliente`.
    """
    _, _, porteiro = _cenario(sessao, fabricar_usuario, "inexistente")
    _entrar(cliente, porteiro)

    resposta = cliente.post(
        f"/portaria/eventos/{uuid4()}/validacoes", json={"codigo": "ZZZZZZZZ"}
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_ESCALA_NO_EVENTO"


def test_rascunho_com_escala_nao_aceita_validacao(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Mesmo corte do `listar_escalados`: rascunho não tem porta para abrir.

    Sem esta condição no `where`, um turno invisível na lista aceitaria validação.
    """
    organizador, _, porteiro = _cenario(sessao, fabricar_usuario, "rascunho")
    evento, _ = _evento_gravado(
        sessao, organizador, portarias=[porteiro], publicado=False
    )
    _entrar(cliente, porteiro)

    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": "ZZZZZZZZ"}
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_ESCALA_NO_EVENTO"


def test_evento_a_mais_de_duas_horas_recebe_403_e_nao_queima_o_ingresso(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """⚠️ **A recusa que a Story 5.1 dizia não ser necessária, e era.**

    Lá o portão era "conveniência da tela, não invariante". O motivo concreto de
    ele ter descido para o backend está nesta asserção: uma chamada três dias
    antes gravaria `usado_em`, e na noite do show aquela pessoa seria barrada com
    `JA_UTILIZADO` sem nunca ter entrado. A tela impedia; a rota não, e
    credencial de portaria mais um `curl` bastavam.

    ⚠️ **É `403`, e não um quinto veredito.** É recusa de atendimento, da mesma
    família do "você não trabalha aqui" — os quatro vereditos continuam quatro, e
    nenhuma palavra nova entra na tela da portaria.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "fechado")
    evento, setor = _evento_gravado(
        sessao, organizador, data_hora=_daqui_a(days=3), portarias=[porteiro]
    )
    ingresso = _ingresso_gravado(sessao, comprador, evento, setor)
    _entrar(cliente, porteiro)

    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": ingresso.codigo}
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "EVENTO_NAO_ABERTO"
    intacto = sessao.get(Ingresso, ingresso.id)
    assert intacto is not None
    assert intacto.usado_em is None


def test_dentro_da_janela_e_depois_do_comeco_a_rota_atende(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Os dois lados que precisam funcionar: faltando 1h e tendo começado há 30min.

    O segundo é o que mais importa — é o horário em que a fila anda, e é
    exatamente o lado do corte que as rotas públicas escondem.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "janela")
    _entrar(cliente, porteiro)

    for sufixo, quando in (
        ("falta-uma-hora", _daqui_a(hours=1)),
        ("comecou-ha-meia-hora", _daqui_a(minutes=-30)),
    ):
        evento, setor = _evento_gravado(
            sessao, organizador, nome=sufixo, data_hora=quando, portarias=[porteiro]
        )
        ingresso = _ingresso_gravado(sessao, comprador, evento, setor)

        corpo = _validar(cliente, evento, ingresso.codigo)

        assert corpo["resultado"] == "VALIDO", sufixo


# --------------------------------------------------------------------------- #
# Papel na assinatura, e 401 antes de 403
# --------------------------------------------------------------------------- #


def test_sem_cookie_recebe_401_e_nao_403(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """A ordem é do `Depends` encadeado, não de um `if` no corpo (AD-9)."""
    organizador, _, porteiro = _cenario(sessao, fabricar_usuario, "sem-cookie")
    evento, _ = _evento_gravado(sessao, organizador, portarias=[porteiro])

    resposta = cliente.post(
        f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": "ZZZZZZZZ"}
    )

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_cliente_e_organizador_recebem_403_de_papel(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Nem quem publicou o show, nem quem comprou o ingresso, abre a porta dele.

    O código é `SEM_PERMISSAO`, do `exigir_papel` — diferente do
    `SEM_ESCALA_NO_EVENTO`, que é de quem **tem** o papel e não está naquela
    escala. São recusas de camadas diferentes e é certo que se distingam.
    """
    organizador, comprador, porteiro = _cenario(sessao, fabricar_usuario, "papel")
    evento, _ = _evento_gravado(sessao, organizador, portarias=[porteiro])

    for quem in (comprador, organizador):
        cliente.cookies.clear()
        _entrar(cliente, quem)

        resposta = cliente.post(
            f"/portaria/eventos/{evento.id}/validacoes", json={"codigo": "ZZZZZZZZ"}
        )

        assert resposta.status_code == 403, quem.papel
        assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_o_openapi_declara_resultado_da_validacao_na_rota(cliente: TestClient) -> None:
    especificacao = cliente.get("/openapi.json").json()

    rota = especificacao["paths"]["/portaria/eventos/{evento_id}/validacoes"]["post"]
    schema = rota["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/ResultadoDaValidacao")


# --------------------------------------------------------------------------- #
# A corrida do AD-6 — dois leitores, um ingresso
# --------------------------------------------------------------------------- #


def test_duas_conexoes_validando_o_mesmo_ingresso_deixam_entrar_uma_vez(
    engine_teste: Engine,
) -> None:
    """**O terceiro teste da suíte fora do `TestClient`**, e pelo mesmo motivo.

    A fixture `cliente` amarra o app a **uma** sessão revertida: duas chamadas
    "concorrentes" ali dentro compartilhariam a mesma transação, a corrida nunca
    aconteceria e o teste passaria sem ter provado nada. Aqui são duas `Session`
    em **conexões distintas**, soltas juntas por um `threading.Barrier(2)`, com
    commit de verdade — o mesmo molde da corrida do AD-3 na Story 3.6 e da do
    `share_token` na 4.3.

    ⚠️ **O que ele pega, e o que a suíte sequencial não pegaria.** Um
    `if ingresso.usado_em is None` em Python antes do `UPDATE` passa em todos os
    testes acima e deixa **as duas** pessoas entrarem com o mesmo ingresso: as
    duas transações leem `NULL` e as duas gravam. Quem decide é o
    `WHERE usado_em IS NULL`, no banco, pelo `rowcount` — que é a garantia do
    AD-6, irmã da do AD-3.

    ⚠️ **A asserção é "um `VALIDO` e um `JA_UTILIZADO`"**, e não "a primeira
    venceu". Qual thread chega antes é do escalonador do sistema operacional;
    que exatamente uma vença é do `where`. Assertar a ordem seria testar o
    escalonador.

    ⚠️ **Este teste comita, então ele limpa** — está fora da transação revertida
    do `conftest.py`, e sem o `finally` as linhas ficariam no `rockhub_teste`
    para o próximo `pytest`.
    """
    Fabrica = sessionmaker(bind=engine_teste)

    organizador_id = uuid4()
    comprador_id = uuid4()
    porteiro_id = uuid4()
    evento_id = uuid4()
    setor_id = uuid4()

    with Fabrica() as preparo:
        contas = [
            Usuario(
                id=organizador_id,
                nome="Organizador da corrida da porta",
                email=f"org-porta-{organizador_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.ORGANIZADOR.value,
            ),
            Usuario(
                id=comprador_id,
                nome="Comprador da corrida da porta",
                email=f"cli-porta-{comprador_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.CLIENTE.value,
            ),
            Usuario(
                id=porteiro_id,
                nome="Porteiro da corrida",
                email=f"porta-{porteiro_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.PORTARIA.value,
            ),
        ]
        preparo.add_all(contas)
        # `flush` entre as contas e o evento pelo mesmo motivo do teste do AD-3:
        # sem `relationship` declarado entre `Evento` e `Usuario`, o SQLAlchemy
        # não tem como ordenar os `INSERT` e o evento sai antes da FK existir.
        preparo.flush()

        preparo.add(
            Evento(
                id=evento_id,
                organizador_id=organizador_id,
                nome="Show da corrida da porta",
                data_hora=datetime.now(timezone.utc) + timedelta(hours=1),
                local="Espaço Unimed",
                cidade="São Paulo",
                origem_externa_id="G5vYZ9a1kd",
                publicado_em=datetime.now(timezone.utc),
                setores=[
                    Setor(
                        id=setor_id,
                        nome="Pista",
                        capacidade=800,
                        vendidos=1,
                        preco_centavos=12000,
                    )
                ],
            )
        )
        preparo.flush()

        evento = preparo.get(Evento, evento_id)
        comprador = preparo.get(Usuario, comprador_id)
        assert evento is not None and comprador is not None
        setor = preparo.get(Setor, setor_id)
        assert setor is not None
        ingresso = _ingresso_gravado(preparo, comprador, evento, setor)
        ingresso_id = ingresso.id
        reserva_id = ingresso.reserva_id
        codigo = ingresso.codigo
        preparo.commit()

    try:
        inicio = threading.Barrier(2)
        vereditos: list[str] = []
        horas: list[str | None] = []
        trava = threading.Lock()

        def tentar() -> None:
            with Fabrica() as s:
                porteiro = s.get(Usuario, porteiro_id)
                show = s.get(Evento, evento_id)
                assert porteiro is not None and show is not None
                # As duas soltam juntas, cada uma na sua conexão.
                inicio.wait()
                resultado = servico_de_ingresso.validar(s, porteiro, show, codigo)
                with trava:
                    vereditos.append(resultado.resultado)
                    horas.append(
                        resultado.entrada_em.isoformat()
                        if resultado.entrada_em
                        else None
                    )

        threads = [threading.Thread(target=tentar) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert sorted(vereditos) == ["JA_UTILIZADO", "VALIDO"]
        # ⚠️ As duas respostas apontam para a **mesma** entrada. Quem perdeu relê
        # a linha; sem o `refresh`, ela sairia com `entrada_em: null` — e a tela
        # diria "já utilizado" sem dizer quando.
        assert horas[0] is not None and horas[0] == horas[1]

        with Fabrica() as leitura:
            gravado = leitura.get(Ingresso, ingresso_id)
            assert gravado is not None
            assert gravado.usado_em is not None
            assert gravado.validado_por == porteiro_id
    finally:
        with Fabrica() as limpeza:
            limpeza.execute(delete(Ingresso).where(Ingresso.id == ingresso_id))
            limpeza.execute(
                delete(ItemReserva).where(ItemReserva.reserva_id == reserva_id)
            )
            limpeza.execute(delete(Reserva).where(Reserva.id == reserva_id))
            limpeza.execute(delete(Setor).where(Setor.id == setor_id))
            _limpar_escala(limpeza, evento_id)
            limpeza.execute(delete(Evento).where(Evento.id == evento_id))
            limpeza.execute(
                delete(Usuario).where(
                    Usuario.id.in_([organizador_id, comprador_id, porteiro_id])
                )
            )
            limpeza.commit()


def _limpar_escala(sessao: Session, evento_id: UUID) -> None:
    """Apaga as linhas de `evento_portaria` deste evento.

    Este teste grava o evento **sem** escala (a autorização é chamada direto no
    service, sem passar pela dependência), então hoje não há linha a apagar. A
    chamada fica porque a FK não tem `ondelete`: o dia em que o preparo escalar
    alguém, o `DELETE` do evento passaria a falhar no `finally` — dentro de um
    `try` de limpeza, que é o pior lugar para descobrir um erro.
    """
    from app.models.evento import evento_portaria

    sessao.execute(
        delete(evento_portaria).where(evento_portaria.c.evento_id == evento_id)
    )
