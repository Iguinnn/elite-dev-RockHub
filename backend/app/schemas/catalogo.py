"""Schema do catálogo de eventos — o formato **deste projeto**, não da Ticketmaster.

`ItemDoCatalogo` é o que sobra depois que `app/integrations/ticketmaster.py`
converte a resposta da Discovery. Nenhum nome de campo aninhado ou de envelope
do fornecedor externo atravessa esta fronteira — é o AD-1 funcionando: o
catálogo externo só existe do lado de dentro da integração, e o resto do
backend enxerga só isto aqui.

A Story 2.4 copia estes seis campos para a tabela `evento` no momento da
publicação (AD-1: dado do catálogo vira cópia no banco, não referência viva).
"""

from pydantic import BaseModel, field_validator


def _cortar(valor: str | None, limite: int) -> str | None:
    return valor[:limite] if valor is not None else None


class ItemDoCatalogo(BaseModel):
    """⚠️ **Os limites daqui são os do `EventoEntrada`, e não é coincidência.**

    Descoberto no code review da Epic 2: sem eles, um show da Discovery com nome
    acima de 200 caracteres — turnê mais patrocinador mais "presented by" é
    rotina lá — aparecia na lista, era clicável, o passo 2 abria, e o `POST`
    voltava `422 DADOS_INVALIDOS` sobre o campo `nome`, que a tela **não mostra
    e ninguém pode editar** (AD-1: os campos do catálogo viajam escondidos).
    Beco sem saída, e a única mensagem possível era "confira os dados do
    formulário".

    Cortar e não recusar: um nome comprido é um show legítimo, e descartá-lo
    do catálogo seria esconder da pessoa exatamente o que ela procurou.
    """

    id_externo: str
    nome: str
    atracao: str | None
    imagem_url: str | None
    local: str | None
    cidade: str | None

    @field_validator("id_externo", "nome", "imagem_url", "local", "cidade")
    @classmethod
    def _cortar_no_limite_da_coluna(cls, valor: str | None, info) -> str | None:
        limites = {
            "id_externo": 64,
            "nome": 200,
            "imagem_url": 500,
            "local": 200,
            "cidade": 120,
        }
        return _cortar(valor, limites[info.field_name])
