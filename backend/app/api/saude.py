"""Rota de saúde: diz apenas que o processo subiu e responde.

Não toca banco nem serviço externo de propósito — é o alvo do health check da
Railway, e um health check que depende de terceiros derruba o deploy por motivo
que não é dele.
"""

from fastapi import APIRouter

router = APIRouter(tags=["saúde"])


@router.get("/saude", summary="Verifica se a API está no ar")
def verificar_saude() -> dict[str, str]:
    return {"status": "ok"}
