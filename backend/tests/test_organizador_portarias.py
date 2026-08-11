"""Rota `GET /organizador/portarias` (Story 2.5) — quem o organizador pode
escalar na porta do evento.

Precisa do Compose no ar: faz login de verdade, como os outros testes de rota
do organizador.

A rota é de leitura e não tem invariante nenhuma, mas **passa por service**:
ela toca o banco, e router que abre `Session` para consultar é o que o
paradigma da espinha proíbe. O critério inteiro está no docstring de
`app/api/organizador.py`.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguranca import gerar_hash
from app.models.usuario import PapelUsuario, Usuario


def _entrar(cliente: TestClient, usuario: Usuario) -> None:
    resposta = cliente.post(
        "/auth/login", json={"email": usuario.email, "senha": "rockhub"}
    )
    assert resposta.status_code == 200


def _portaria_chamada(sessao: Session, nome: str, email: str) -> Usuario:
    """Uma conta de portaria com **nome** à escolha do teste.

    A `fabricar_usuario` do `conftest.py` grava todo mundo como "Alguém", e
    parametriza só o e-mail — o que basta para os quinze testes que a usam e
    não basta para um só: o da ordenação. Com nomes iguais, "ordenado por
    nome" não decide nada, e o teste passaria (ou falharia) por acaso.
    """
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=gerar_hash("rockhub"),
        papel=PapelUsuario.PORTARIA.value,
    )
    sessao.add(usuario)
    sessao.flush()
    sessao.refresh(usuario)
    return usuario


# --------------------------------------------------------------------------- #
# AC8 — a lista traz só portaria, com nome e e-mail, ordenada por nome
# --------------------------------------------------------------------------- #


def test_organizador_recebe_as_contas_de_portaria_ordenadas_por_nome(
    cliente: TestClient,
    sessao: Session,
    fabricar_usuario: Callable[..., Usuario],
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "quem-escala@exemplo.com")
    # Gravados fora de ordem alfabética de propósito: se a rota devolvesse na
    # ordem de inserção, este teste passaria por acidente.
    _portaria_chamada(sessao, "Zulmira Nogueira", "zulmira@exemplo.com")
    _portaria_chamada(sessao, "Amanda Prado", "amanda@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 200
    assert [conta["nome"] for conta in resposta.json()] == [
        "Amanda Prado",
        "Zulmira Nogueira",
    ]


def test_a_lista_nao_traz_organizador_nem_cliente(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "chefe@exemplo.com")
    fabricar_usuario(PapelUsuario.CLIENTE, "freguesia@exemplo.com")
    porteiro = fabricar_usuario(PapelUsuario.PORTARIA, "so-esse@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 200
    assert [conta["id"] for conta in resposta.json()] == [str(porteiro.id)]


def test_cada_conta_traz_id_nome_e_email_e_mais_nada(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """O `papel` fica de fora: aqui ele é sempre `PORTARIA`, ou seja, ruído."""
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "manda@exemplo.com")
    fabricar_usuario(PapelUsuario.PORTARIA, "porta@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 200
    (conta,) = resposta.json()
    assert set(conta) == {"id", "nome", "email"}


def test_sem_nenhuma_conta_de_portaria_a_resposta_e_uma_lista_vazia(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Lista vazia é `200`, não `404`: a pergunta foi respondida.

    É a tela que decide o que dizer — e o AC16 pede que ela diga que não há
    quem escalar, sem quebrar.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "sozinho@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_senha_hash_nao_aparece_na_lista(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Quem filtra é o `response_model=list[PortariaSaida]`.

    Sem ele declarado na rota, o FastAPI serializaria o `Usuario` inteiro — e o
    hash da senha de toda a portaria estaria numa resposta de rotina.
    """
    organizador = fabricar_usuario(PapelUsuario.ORGANIZADOR, "confere@exemplo.com")
    fabricar_usuario(PapelUsuario.PORTARIA, "com-hash@exemplo.com")
    _entrar(cliente, organizador)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 200
    assert "senha_hash" not in resposta.text


# --------------------------------------------------------------------------- #
# AC9 — papel na assinatura, e 401 antes de 403
# --------------------------------------------------------------------------- #


def test_cliente_recebe_403_sem_permissao(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    usuario = fabricar_usuario(PapelUsuario.CLIENTE, "cliente@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_a_propria_portaria_tambem_recebe_403(
    cliente: TestClient, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """Estar na lista não dá direito de lê-la: escalar é ato do organizador."""
    usuario = fabricar_usuario(PapelUsuario.PORTARIA, "portaria@exemplo.com")
    _entrar(cliente, usuario)

    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_sem_cookie_recebe_401_e_nao_403(cliente: TestClient) -> None:
    resposta = cliente.get("/organizador/portarias")

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_rota_aparece_no_openapi_com_a_lista_de_portaria_saida(
    cliente: TestClient,
) -> None:
    especificacao = cliente.get("/openapi.json").json()
    operacao = especificacao["paths"]["/organizador/portarias"]["get"]
    schema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["items"]["$ref"].endswith("/PortariaSaida")
