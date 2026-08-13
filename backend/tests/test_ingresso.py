"""Emissão do ingresso e o código não forjável (Story 3.9) — AD-5 e AD-14.

Precisa do Compose no ar: os ingressos são contados no banco, e não no corpo da
resposta.

⚠️ **A garantia mais pontuada do desafio mora em duas linhas de código, e as
duas são fáceis de quebrar sem quebrar nenhum teste ingênuo:**

- **A emissão só acontece depois do `_transicionar` vencer** (AD-14). Movida
  para antes, ou protegida por um `if ja_tem_ingresso`, ela continua passando em
  todo teste sequencial e emite ingresso duplo no reprocessamento.
- **O código é recalculado, nunca comparado com a coluna** (AD-5). Comparar
  com o que está gravado dá o mesmo resultado em todo caso feliz e transforma o
  banco em oráculo de assinatura.

**O teste de forja é o que mais importa aqui**: ele altera um símbolo do código e
exige que a verificação falhe **sem tocar o banco** — por isso ele chama
`conferir_codigo` direto, sem sessão nenhuma.

⚠️ **O código encolheu de 80 para 8 caracteres em 2026-08-12** (techspec
`docs/techspec-codigo-curto.md`), e com ele três coisas mudaram de forma aqui:
não há mais `ID.ASSINATURA` para partir no ponto, a normalização de entrada
passou a ser parte do contrato, e **colisão de código deixou de ser
impossível** — 40 bits colidem, e a emissão sorteia outro `nonce` quando isso
acontece.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.erros import ErroDeDominio
from app.core.seguranca import (
    TAMANHO_DO_CODIGO,
    conferir_codigo,
    gerar_codigo,
    gerar_hash,
    gerar_nonce,
    gerar_share_token,
    normalizar_codigo,
)
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.pagamento import MeioDePagamento, PagamentoEntrada
from app.services.pagamento import Autorizacao
from app.services.reserva import pagar

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
    assert len({g.codigo for g in gravados}) == 3


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


def test_o_titular_e_a_conta_e_o_nome_do_checkout_vai_para_o_pagador(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """Decisão do Igor: **o ingresso é da conta**, o cartão pode ser de outro.

    O campo do checkout vem preenchido com o nome da conta e é editável — a
    namorada compra na conta dela, eu ponho meu cartão. O que foi digitado é
    quem **pagou**, e vai para `ingresso.pagador_nome`, que não tem leitor em
    tela nenhuma; o titular do canhoto é `usuario.nome`.

    ⚠️ **Este teste afirmava exatamente o contrário até 2026-08-12** (techspec
    `docs/techspec-codigo-curto.md`). As duas asserções abaixo são a decisão
    invertida, e não uma correção de bug: se um dia o titular voltar a ser o
    nome do checkout, é aqui que se vê.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i4@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i4@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)

    ingressos = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo(nome="Fulana de Tal")
    ).json()["ingressos"]

    # A conta se chama "Alguém" (fixture), e é ela que aparece no canhoto.
    assert ingressos[0]["titular_nome"] == comprador.nome
    assert comprador.nome != "Fulana de Tal"

    # E o nome digitado não se perdeu: ele está na coluna do pagador.
    gravado = sessao.scalars(
        select(Ingresso).where(Ingresso.reserva_id == reserva.id)
    ).one()
    assert gravado.pagador_nome == "Fulana de Tal"


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
# AC3 e AC5 — o código são 8 símbolos de Crockford, e código adulterado não passa
# --------------------------------------------------------------------------- #

# O alfabeto da base32 de Crockford, escrito aqui à mão de propósito: se o
# `_ALFABETO` do módulo mudar, é este teste que tem de dizer não. Importá-lo faria
# as asserções abaixo concordarem com qualquer alfabeto, inclusive um com `O` e
# `I` de volta — que é o defeito que elas existem para pegar.
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def test_o_codigo_tem_oito_simbolos_de_crockford(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """8 caracteres, todos do alfabeto — e `I`, `L`, `O` e `U` fora dele.

    O tamanho é o contrato (`String(8)` na coluna), e o alfabeto é o que resolve
    de graça o AC de "não diferencia maiúsculas de minúsculas": não existe
    minúscula nele.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-i9@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-i9@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 1))
    _entrar(cliente, comprador)

    codigo = cliente.post(
        f"/reservas/{reserva.id}/pagamento", json=_corpo()
    ).json()["ingressos"][0]["codigo"]

    assert len(codigo) == TAMANHO_DO_CODIGO == 8
    assert set(codigo) <= set(CROCKFORD)
    assert not set(codigo) & set("ILOU")

    # E é o código que acha a linha: é assim que a portaria vai chegar nela.
    gravado = sessao.scalars(
        select(Ingresso).where(Ingresso.codigo == codigo)
    ).one()
    assert gravado.reserva_id == reserva.id


def test_gerar_codigo_e_deterministico_e_muda_com_qualquer_ingrediente() -> None:
    """O mesmo trio devolve sempre o mesmo código — é o que o recálculo exige.

    Um gerador que sorteasse qualquer coisa passaria em todo teste de formato e
    reprovaria **todo ingresso legítimo** na porta, porque a validação recalcula
    (AD-5). É esta função que não pode ter aleatoriedade nenhuma dentro.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()

    codigo = gerar_codigo(ingresso_id, evento_id, nonce)

    assert gerar_codigo(ingresso_id, evento_id, nonce) == codigo
    # E os três ingredientes entram na conta (AD-5): trocar qualquer um muda.
    assert gerar_codigo(uuid4(), evento_id, nonce) != codigo
    assert gerar_codigo(ingresso_id, uuid4(), nonce) != codigo
    assert gerar_codigo(ingresso_id, evento_id, gerar_nonce()) != codigo


def test_normalizar_codigo_aceita_o_que_a_fila_produz() -> None:
    """`9k4m 7qx2`, `9K4M-7QX2` e `9K4M7QX2` são o mesmo valor.

    É esta função que faz o AC de "não diferencia maiúsculas de minúsculas" ser
    verdade, e ela também desfaz as confusões de leitura em voz alta: `I` e `L`
    viram `1`, `O` vira `0`. Quem digita na porta não sabe que o alfabeto não tem
    esses três — e não precisa saber.
    """
    assert normalizar_codigo("9K4M7QX2") == "9K4M7QX2"
    assert normalizar_codigo("9k4m 7qx2") == "9K4M7QX2"
    assert normalizar_codigo("9K4M-7QX2") == "9K4M7QX2"
    assert normalizar_codigo("  9k4m-7qx2  ") == "9K4M7QX2"

    # Os confundíveis, nas duas caixas: `I`/`L` → `1`, `O` → `0`.
    assert normalizar_codigo("IL0O9K4M") == "11009K4M"
    assert normalizar_codigo("il0o9k4m") == "11009K4M"


def test_normalizar_codigo_recusa_o_que_nao_e_codigo() -> None:
    """`None` para tamanho errado, símbolo fora do alfabeto e não-ASCII.

    ⚠️ **O `U` não está no alfabeto de Crockford**, e por isso `UUUUUUUU` é
    recusado. Quem testar à mão não invente código com `U` e conclua que a
    validação está quebrada — ela está certa.

    ⚠️ **O caso não-ASCII é o que evitava um `500` na fila da porta** (code review
    da Epic 3): `hmac.compare_digest` com `str` fora do ASCII levanta
    `TypeError`, não devolve `False`. A guarda mudou de lugar quando o código
    encolheu, e continua sendo esta função que a exerce.
    """
    for lixo in (
        "",
        "9K4M7QX",  # sete
        "9K4M7QX23",  # nove
        "9K4M7QX!",  # símbolo fora do alfabeto
        "UUUUUUUU",  # `U` não existe em Crockford
        "9K4M7QXÇ",  # não-ASCII com o tamanho certo
        "アイウエオカキク",  # oito caracteres, nenhum ASCII
        "9K4M 7QX2 EXTRA",
    ):
        assert normalizar_codigo(lixo) is None, lixo


def test_share_token_tem_32_caracteres_e_nao_se_repete() -> None:
    """⚠️ **A imprevisibilidade do `share_token` é o único cadeado de `/i/{token}`.**

    Achado do code review da Epic 4: a suíte inteira passava sem provar isto.
    Os testes de `test_compartilhamento.py` conferem que o token **existe**,
    que ele é **diferente** do `codigo` e do `nonce`, e que dois ingressos têm
    tokens **distintos** — e um `gerar_share_token()` que devolvesse `"1"`,
    `"2"`, `"3"` satisfaz todos eles. Inclusive o `token not in codigo`: a
    chance de poucos caracteres urlsafe caírem dentro dos ~80 do código é
    desprezível. O teste da migração também não segura nada, porque só lê
    `nullable` e `unique`, e `String(32)` aceita um caractere.

    O que estaria em jogo com um contador: `GET /ingressos/compartilhados/
    {token}` é **público** e devolve o `IngressoDetalhe` inteiro — incluindo o
    `codigo` `ID.ASSINATURA`, que é o que vale na porta (AD-5), e o
    `titular_nome`. Quem enumerasse `/i/1`, `/i/2` sairia com o QR de entrada
    de outra pessoa. A spec escreve "192 bits não se adivinham" como a razão
    de o endereço só chegar a quem recebeu o link; é essa frase que este teste
    fixa em asserção.

    **Vizinho dos testes do `nonce` de propósito**, e não em
    `test_seguranca.py`: os dois saem do mesmo `secrets.token_urlsafe(24)` e
    têm exposições opostas — um nunca sai do servidor, o outro é feito para
    viajar por WhatsApp. Os docstrings de `core/seguranca.py` dizem isso em
    espelho, e o contraste só ensina alguma coisa se estiver lado a lado.
    """
    # 24 bytes em base64url sem padding: 24 é divisível por 3, então são
    # sempre exatamente 32 caracteres — nunca 31, nunca 33. É o mesmo tamanho
    # do `nonce`, e é o que a coluna `String(32)` comporta sem truncar.
    assert len(gerar_share_token()) == 32
    assert len(gerar_nonce()) == 32

    # 500 chamadas, 500 valores distintos. Um contador, um `uuid` fatiado curto
    # ou um `token_urlsafe(4)` cai aqui; o gerador de verdade não cai nunca —
    # com 192 bits, uma colisão em 500 sorteios tem probabilidade da ordem de
    # 10⁻⁵³.
    assert len({gerar_share_token() for _ in range(500)}) == 500


def test_codigo_adulterado_falha_sem_consultar_o_banco() -> None:
    """⚠️ **Sem fixture de sessão, e a ausência dela é o teste** (AD-5).

    A verificação recalcula o HMAC das colunas e compara; ela não conhece o
    banco, não recebe sessão e não teria como consultar nada. Se um dia alguém
    trocar o recálculo por um `SELECT ... WHERE codigo = :valor`, este teste para
    de compilar antes de parar de passar.

    ⚠️ **A adulteração é no PRIMEIRO símbolo, nunca no último** — a armadilha
    registrada no code review da Epic 3. Lá o motivo era aritmético: os 43
    caracteres de base64 tinham 2 bits sobrando no último símbolo, então `A`, `B`,
    `C` e `D` decodificavam para os mesmos bytes e a "adulteração" não adulterava
    nada em ~4,7% das execuções — o teste que prova que o ingresso não é forjável
    passava sem ter forjado. Aqui os 40 bits fecham exatos com os 8 símbolos e
    nenhuma posição tem folga, mas a regra fica: **trocar o último caractere não é
    o teste que se quer escrever**, porque ele depende de uma conta de bits em vez
    de depender do HMAC.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()
    codigo = gerar_codigo(ingresso_id, evento_id, nonce)

    assert conferir_codigo(codigo, ingresso_id, evento_id, nonce) is True

    # Outro símbolo do alfabeto no lugar do primeiro, sempre diferente do que
    # estava lá — nada de `+ 1` no índice, que sairia do alfabeto no último.
    trocado = CROCKFORD[1] if codigo[0] == CROCKFORD[0] else CROCKFORD[0]
    adulterado = trocado + codigo[1:]

    assert adulterado != codigo
    assert conferir_codigo(adulterado, ingresso_id, evento_id, nonce) is False

    # E o do meio também, para não haver posição privilegiada.
    meio = CROCKFORD[1] if codigo[4] == CROCKFORD[0] else CROCKFORD[0]
    assert (
        conferir_codigo(
            codigo[:4] + meio + codigo[5:], ingresso_id, evento_id, nonce
        )
        is False
    )


def test_o_codigo_nao_vale_para_outro_ingresso_evento_nem_nonce() -> None:
    """Os três componentes entram na conta (AD-5), e trocar qualquer um invalida.

    É o que impede o código de um ingresso valer no show do lado, ou de um
    `nonce` reaproveitado produzir dois códigos iguais de propósito.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()
    codigo = gerar_codigo(ingresso_id, evento_id, nonce)

    assert conferir_codigo(codigo, uuid4(), evento_id, nonce) is False
    assert conferir_codigo(codigo, ingresso_id, uuid4(), nonce) is False
    assert conferir_codigo(codigo, ingresso_id, evento_id, gerar_nonce()) is False


def test_conferir_codigo_normaliza_a_entrada() -> None:
    """O que a portaria digita confere igual ao que a câmera lê.

    A mesma função serve as três formas de entrada da Epic 5 — QR, digitação e
    colagem —, e é a normalização que faz as três chegarem ao mesmo lugar.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()
    codigo = gerar_codigo(ingresso_id, evento_id, nonce)

    for forma in (
        codigo.lower(),
        f"{codigo[:4]} {codigo[4:]}",
        f"{codigo[:4]}-{codigo[4:]}",
        f"  {codigo.lower()}  ",
    ):
        assert conferir_codigo(forma, ingresso_id, evento_id, nonce) is True, forma


def test_codigo_malformado_nao_estoura() -> None:
    """Lixo entra, `False` sai — nunca exceção.

    A portaria vai alimentar isto com o que a câmera ler, e o que a câmera lê nem
    sempre é um código deste sistema.

    ⚠️ **Os últimos três são o que faltava** (code review da Epic 3).
    `compare_digest` com `str` só aceita ASCII: fora dele ele levanta
    `TypeError`, não devolve `False`. Um QR que decodificasse com acento subia até
    o handler genérico e virava `500 ERRO_INTERNO` na fila da porta — para um
    código simplesmente inválido, que é o caso que este teste promete cobrir. Quem
    barra agora é o `normalizar_codigo`, e a asserção não muda.
    """
    ingresso_id = uuid4()
    evento_id = uuid4()
    nonce = gerar_nonce()

    for lixo in (
        "",
        "curto",
        "muito-longo-para-ser-codigo",
        f"{uuid4()}",  # o formato antigo do QR, que não vale mais
        "9K4M7QX!",
        "UUUUUUUU",
        "9K4M7QXÇ",
        "assinatura-com-acentuação",
        "アイ",
    ):
        assert conferir_codigo(lixo, ingresso_id, evento_id, nonce) is False, lixo


def test_dois_ingressos_nao_podem_gravar_o_mesmo_codigo(
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    """O índice único de `ingresso.codigo`, lido do banco.

    ⚠️ **Sem ele, duas linhas responderiam à mesma leitura de QR** — e a validação
    da porta, que acha a linha *pelo* código, escolheria uma das duas em silêncio.
    Com 40 bits a colisão deixou de ser impossível, e é o índice que a transforma
    em `IntegrityError` no lugar certo: dentro da emissão, onde sortear outro
    `nonce` resolve.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-uq@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-uq@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    reserva = _reserva(sessao, comprador, evento, (evento.setores[0], 2))

    for _ in range(2):
        sessao.add(
            Ingresso(
                reserva_id=reserva.id,
                evento_id=evento.id,
                setor_id=evento.setores[0].id,
                pagador_nome="Quem pagou",
                # O mesmo código nas duas linhas, à mão: o que o HMAC nunca
                # produziria por acidente é exatamente o que o índice tem de
                # recusar.
                codigo="9K4M7QX2",
                nonce=gerar_nonce(),
            )
        )

    with pytest.raises(IntegrityError):
        sessao.flush()


def test_codigo_repetido_na_emissao_sorteia_outro_nonce(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⚠️ **Pagamento aprovado não pode estourar por colisão de código.**

    É a primeira armadilha da techspec `docs/techspec-codigo-curto.md`: com 40
    bits e o índice único, dois códigos iguais viram `IntegrityError` **dentro da
    transação que acabou de marcar a reserva `PAGA`**. A chance é ínfima e o
    desfecho é o pior do produto — cobrança feita, `500` na tela —, então a
    emissão sorteia outro `nonce` e recalcula.

    A colisão é forçada aqui porque **nenhum teste honesto a produz por sorteio**:
    esperar 40 bits colidirem é esperar bilhões de execuções. O `gerar_codigo`
    visto por `services/reserva.py` devolve um código já ocupado na primeira
    chamada e o real nas seguintes.

    ⚠️ **O que este teste protege de verdade é o `begin_nested()`.** Sem o
    SAVEPOINT, o `IntegrityError` invalida a transação inteira — inclusive o
    `UPDATE` que levou a reserva a `PAGA` —, a segunda tentativa grava num
    contexto morto e a requisição termina em `PendingRollbackError`. Trocar o
    savepoint por um `try/except` simples deixa o resto da suíte verde e quebra
    aqui.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "org-col@exemplo.com")
    comprador = fabricar_usuario(PapelUsuario.CLIENTE, "cli-col@exemplo.com")
    evento = _evento_publicado(sessao, organizador)
    setor = evento.setores[0]

    # O ocupante do código: um ingresso de outra reserva, já gravado.
    dona_do_codigo = _reserva(sessao, comprador, evento, (setor, 1))
    ocupado = "9K4M7QX2"
    sessao.add(
        Ingresso(
            reserva_id=dona_do_codigo.id,
            evento_id=evento.id,
            setor_id=setor.id,
            pagador_nome="Quem chegou primeiro",
            codigo=ocupado,
            nonce=gerar_nonce(),
        )
    )
    sessao.flush()

    reserva = _reserva(sessao, comprador, evento, (setor, 1))
    _entrar(cliente, comprador)

    nonces: list[str] = []

    def gerar_codigo_que_colide_uma_vez(
        ingresso_id: object, evento_id: object, nonce: str
    ) -> str:
        nonces.append(nonce)
        if len(nonces) == 1:
            return ocupado
        return gerar_codigo(ingresso_id, evento_id, nonce)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "app.services.reserva.gerar_codigo", gerar_codigo_que_colide_uma_vez
    )

    resposta = cliente.post(f"/reservas/{reserva.id}/pagamento", json=_corpo())

    # O pagamento passou, e a reserva ficou `PAGA` — o savepoint preservou tudo
    # que a transação já tinha feito.
    assert resposta.status_code == 200
    assert resposta.json()["estado"] == EstadoReserva.PAGA.value

    # Duas tentativas, com **nonces diferentes**: o segundo não é o primeiro
    # reaproveitado, senão o código recalculado seria o mesmo e colidiria de novo.
    assert len(nonces) == 2
    assert nonces[0] != nonces[1]

    emitido = sessao.scalars(
        select(Ingresso).where(Ingresso.reserva_id == reserva.id)
    ).one()
    assert emitido.codigo != ocupado
    # E o código gravado é o do `nonce` gravado: sem isso, o ingresso existe e
    # não passa na porta.
    assert (
        conferir_codigo(emitido.codigo, emitido.id, evento.id, emitido.nonce) is True
    )


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


def test_dois_pagamentos_simultaneos_emitem_um_conjunto_so_de_ingressos(
    engine_teste: Engine,
) -> None:
    """⚠️ **O teste que o AD-14 precisava e não tinha** (code review da Epic 3).

    O `test_pagar_de_novo_nao_emite_ingresso_adicional` logo acima afirma no
    docstring que é ele quem prova a emissão dentro do `if`. Não é: a segunda
    chamada dele é barrada pela guarda de leitura (`if reserva.estado !=
    PENDENTE`) **antes** de o `_transicionar` sequer rodar. Ele prova a guarda.
    Mover a emissão para fora do ramo vencedor — a regressão que o AD-14 proíbe —
    deixava a suíte inteira verde.

    Provar o AD-14 exige duas conexões que passem **as duas** pela guarda de
    leitura e só então disputem o `rowcount`. O ponto de injeção é o gateway: ele
    é chamado depois da guarda e antes da transição, então um `PaymentGateway`
    que espera numa `Barrier` para as duas exatamente no ramo que nunca foi
    exercitado. Uma vence o `UPDATE` condicional e emite; a outra levanta
    `RESERVA_NAO_PENDENTE` sem emitir nada.

    A asserção que importa é a contagem: **dois** ingressos para dois lugares, e
    não quatro. Com a emissão fora do `if`, este teste vê quatro.

    ⚠️ **Este teste comita, então ele limpa** — mesma disciplina do
    `test_duas_reservas_simultaneas...` do `test_reservar.py`: ele roda fora da
    transação revertida do `conftest.py`.
    """
    Fabrica = sessionmaker(bind=engine_teste, autoflush=False, expire_on_commit=False)

    cliente_id = uuid4()
    organizador_id = uuid4()
    evento_id = uuid4()
    setor_id = uuid4()
    reserva_id = uuid4()
    quantidade = 2

    with Fabrica() as preparo:
        preparo.add(
            Usuario(
                id=organizador_id,
                nome="Organizador da corrida de pagamento",
                email=f"org-corrida-{organizador_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.ORGANIZADOR.value,
            )
        )
        preparo.add(
            Usuario(
                id=cliente_id,
                nome="Cliente da corrida de pagamento",
                email=f"cli-corrida-{cliente_id}@exemplo.com",
                senha_hash=gerar_hash("rockhub"),
                papel=PapelUsuario.CLIENTE.value,
            )
        )
        preparo.flush()
        preparo.add(
            Evento(
                id=evento_id,
                organizador_id=organizador_id,
                nome="Show da corrida de pagamento",
                data_hora=_daqui_a(30),
                local="Espaço Unimed",
                cidade="São Paulo",
                origem_externa_id="G5vYZ9a1kd",
                publicado_em=datetime.now(timezone.utc),
                setores=[
                    Setor(
                        id=setor_id,
                        nome="Pista",
                        capacidade=10,
                        # Já consumido pela reserva abaixo.
                        vendidos=quantidade,
                        preco_centavos=12000,
                    )
                ],
            )
        )
        preparo.flush()
        preparo.add(
            Reserva(
                id=reserva_id,
                cliente_id=cliente_id,
                evento_id=evento_id,
                estado=EstadoReserva.PENDENTE.value,
                expira_em=datetime.now(timezone.utc) + timedelta(minutes=10),
                total_centavos=12000 * quantidade,
                itens=[
                    ItemReserva(
                        setor_id=setor_id,
                        quantidade=quantidade,
                        preco_unitario_centavos=12000,
                    )
                ],
            )
        )
        preparo.commit()

    try:
        # As duas threads chegam aqui depois da guarda de leitura e antes da
        # transição. É esta linha que cria a corrida que o AD-14 descreve.
        no_gateway = threading.Barrier(2)

        class GatewayQueEspera:
            def autorizar(
                self,
                *,
                total_centavos: int,
                meio: MeioDePagamento,
                numero_cartao: str | None,
            ) -> Autorizacao:
                no_gateway.wait(timeout=30)
                return Autorizacao(aprovada=True)

        dados = PagamentoEntrada(**_corpo())
        vitorias: list[bool] = []
        trava = threading.Lock()

        def tentar() -> None:
            with Fabrica() as s:
                comprador = s.get(Usuario, cliente_id)
                assert comprador is not None
                try:
                    pagar(s, comprador, reserva_id, dados, GatewayQueEspera())
                    venceu = True
                except ErroDeDominio as erro:
                    # A perdedora sai por aqui, e o código dela é o do ramo que
                    # perde o `rowcount` — não o da guarda de leitura.
                    assert erro.codigo == "RESERVA_NAO_PENDENTE"
                    venceu = False
                with trava:
                    vitorias.append(venceu)

        threads = [threading.Thread(target=tentar) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert len(vitorias) == 2
        # Exatamente uma venceu a transição.
        assert sum(vitorias) == 1

        with Fabrica() as leitura:
            reserva = leitura.get(Reserva, reserva_id)
            assert reserva is not None
            assert reserva.estado == EstadoReserva.PAGA.value

            emitidos = leitura.scalar(
                select(func.count())
                .select_from(Ingresso)
                .where(Ingresso.reserva_id == reserva_id)
            )
            # ⚠️ **Dois, e não quatro.** É esta linha, e só ela, que falha quando
            # a emissão sai de dentro do ramo que vence o `_transicionar`.
            assert emitidos == quantidade
    finally:
        with Fabrica() as limpeza:
            limpeza.execute(delete(Ingresso).where(Ingresso.reserva_id == reserva_id))
            limpeza.execute(delete(ItemReserva).where(ItemReserva.reserva_id == reserva_id))
            limpeza.execute(delete(Reserva).where(Reserva.id == reserva_id))
            limpeza.execute(delete(Setor).where(Setor.id == setor_id))
            limpeza.execute(delete(Evento).where(Evento.id == evento_id))
            limpeza.execute(
                delete(Usuario).where(Usuario.id.in_([cliente_id, organizador_id]))
            )
            limpeza.commit()
