"""Rotas exclusivas do organizador: hoje só o catálogo, que dá superfície à
integração da Story 2.1.

**Por que não há `services/catalogo.py`.** A espinha diz `routers → services →
models`, e este router chama `app.integrations` direto — pula uma camada.
`buscar_eventos` já faz tudo que um service faria: `.strip()` no termo,
montagem dos parâmetros certos (com ou sem `keyword`), limite, conversão para
o schema do projeto e tradução de toda falha em `ErroDeDominio`. Não sobra
regra de negócio para lugar nenhum, e interpor um módulo cujo corpo inteiro
seria `return ticketmaster.buscar_eventos(termo)` é a "camada de repasse" que
a própria espinha rejeita em *Design Paradigm*.

Esta é a **única** exceção ao paradigma neste projeto — quando a Story 2.4
gravar no banco, ela ganha service, sem discussão: o critério que separa os
dois casos é existir transação ou invariante.
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencias import exigir_papel
from app.integrations import ticketmaster
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.catalogo import ItemDoCatalogo

router = APIRouter(prefix="/organizador", tags=["organizador"])


@router.get("/catalogo", response_model=list[ItemDoCatalogo])
def buscar_no_catalogo(
    q: str = Query("", max_length=120),
    _: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
) -> list[ItemDoCatalogo]:
    """Busca na Ticketmaster Discovery pelo termo `q`.

    `q` vazio **não** devolve lista vazia sem chamar a Ticketmaster — devolve
    os próximos eventos do catálogo no Brasil, para o organizador ver
    exemplos do que pode publicar assim que abre a tela.

    `max_length=120` não é enfeite: `q` vai inteiro para a URL da Ticketmaster
    (mesmo raciocínio dos tetos de `LoginEntrada`, Story 1.4). O parâmetro do
    usuário autenticado se chama `_` porque a rota não usa o objeto, só exige
    o papel — nomeá-lo `usuario` sem usá-lo é ruído que o linter reclama.
    """
    return ticketmaster.buscar_eventos(q)
