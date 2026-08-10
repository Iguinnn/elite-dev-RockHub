"""Teste da rota de saúde — a verificação mais barata de que a aplicação sobe."""

from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_saude_responde_ok() -> None:
    resposta = cliente.get("/saude")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_documentacao_automatica_esta_disponivel() -> None:
    """O `/docs` é o contrato navegável que a avaliação vai abrir primeiro."""
    resposta = cliente.get("/docs")

    assert resposta.status_code == 200
