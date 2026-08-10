"""Erro de domínio e o formato único de resposta de erro da API.

**Toda** resposta de erro desta API tem exatamente esta forma, venha ela da regra
de negócio, de um `HTTPException` ou da validação do Pydantic:

    {"erro": {"codigo": "...", "mensagem": "..."}}

O `codigo` é a parte estável do contrato: é por ele que o frontend decide o que
mostrar. A `mensagem` é texto para humano e pode mudar sem quebrar ninguém.
"""

from typing import Any, Iterable, Mapping

# Código estável para as falhas que não vêm da regra de negócio — as que o
# próprio framework levanta. Sem esta tabela, um `404` do router e um `404` de um
# service falariam línguas diferentes com o frontend.
CODIGO_POR_STATUS: dict[int, str] = {
    400: "REQUISICAO_INVALIDA",
    401: "NAO_AUTENTICADO",
    403: "SEM_PERMISSAO",
    404: "NAO_ENCONTRADO",
    405: "METODO_NAO_PERMITIDO",
    409: "CONFLITO",
    422: "DADOS_INVALIDOS",
    429: "MUITAS_REQUISICOES",
}

MENSAGEM_PADRAO = "Não foi possível completar a requisição."


def corpo_de_erro(codigo: str, mensagem: str) -> dict[str, Any]:
    """Monta o corpo de erro. Único lugar que conhece esse formato."""
    return {"erro": {"codigo": codigo, "mensagem": mensagem}}


def codigo_para_status(status_http: int) -> str:
    """Código estável correspondente a um status HTTP não mapeado pelo domínio."""
    if status_http in CODIGO_POR_STATUS:
        return CODIGO_POR_STATUS[status_http]
    return "ERRO_INTERNO" if status_http >= 500 else "ERRO_HTTP"


def descrever_erros_de_validacao(erros: Iterable[Mapping[str, Any]]) -> str:
    """Resume os erros do Pydantic numa frase.

    O formato bruto do Pydantic é uma lista de objetos aninhados, ótima para
    depurar e péssima para o contrato: obrigaria o corpo de erro a ter uma forma
    diferente só neste caso. Achatar em texto mantém uma forma só na API sem
    perder qual campo reprovou.
    """
    partes: list[str] = []
    for erro in erros:
        caminho = [str(pedaco) for pedaco in erro.get("loc", ())]
        # O primeiro item é a origem ("body", "query", "path") — ruído para quem
        # lê. Só é mantido quando não há mais nada depois dele.
        if len(caminho) > 1:
            caminho = caminho[1:]
        campo = ".".join(caminho) or "requisição"
        partes.append(f"{campo}: {erro.get('msg', 'valor inválido')}")

    return "; ".join(partes) or "Dados inválidos."


class ErroDeDominio(Exception):
    """Falha prevista pela regra de negócio, com código estável e status HTTP."""

    def __init__(
        self,
        codigo: str,
        mensagem: str,
        status_http: int = 400,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status_http = status_http

    def como_corpo(self) -> dict[str, Any]:
        """Serializa no formato de erro que a API inteira usa."""
        return corpo_de_erro(self.codigo, self.mensagem)
