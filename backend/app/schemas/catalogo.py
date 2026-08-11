"""Schema do catálogo de eventos — o formato **deste projeto**, não da Ticketmaster.

`ItemDoCatalogo` é o que sobra depois que `app/integrations/ticketmaster.py`
converte a resposta da Discovery. Nenhum nome de campo aninhado ou de envelope
do fornecedor externo atravessa esta fronteira — é o AD-1 funcionando: o
catálogo externo só existe do lado de dentro da integração, e o resto do
backend enxerga só isto aqui.

A Story 2.4 copia estes seis campos para a tabela `evento` no momento da
publicação (AD-1: dado do catálogo vira cópia no banco, não referência viva).
"""

from pydantic import BaseModel


class ItemDoCatalogo(BaseModel):
    id_externo: str
    nome: str
    atracao: str | None
    imagem_url: str | None
    local: str | None
    cidade: str | None
