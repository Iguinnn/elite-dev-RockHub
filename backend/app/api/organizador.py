"""Rotas exclusivas do organizador: buscar no catálogo e publicar o evento.

**Por que não há `services/catalogo.py`.** A espinha diz `routers → services →
models`, e este router chama `app.integrations` direto — pula uma camada.
`buscar_eventos` já faz tudo que um service faria: `.strip()` no termo,
montagem dos parâmetros certos (com ou sem `keyword`), limite, conversão para
o schema do projeto e tradução de toda falha em `ErroDeDominio`. Não sobra
regra de negócio para lugar nenhum, e interpor um módulo cujo corpo inteiro
seria `return ticketmaster.buscar_eventos(termo)` é a "camada de repasse" que
a própria espinha rejeita em *Design Paradigm*.

Esta é a **única** exceção ao paradigma neste projeto, e desde a Story 2.4 o
arquivo tem o par completo: `POST /eventos` **tem** service, porque existe
transação (evento e setores gravados juntos ou nada) e existem invariantes
(nenhum setor, setor repetido). O critério que separa os dois casos está
escrito acima — *existe transação ou invariante?* — e agora dá para ler os dois
lados dele sem sair deste arquivo.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import exigir_papel
from app.integrations import ticketmaster
from app.models.evento import Evento
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.catalogo import ItemDoCatalogo
from app.schemas.evento import EventoEntrada, EventoSaida
from app.services import evento as servico_de_evento

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


@router.post("/eventos", response_model=EventoSaida, status_code=201)
def publicar_evento(
    dados: EventoEntrada,
    organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> Evento:
    """Publica um evento com seus setores. A primeira rota de escrita do domínio.

    **Esta rota tem service, e a do catálogo não.** O critério está no
    docstring do módulo: aqui existe transação (evento e setores gravados
    juntos ou nada) e existem invariantes (nenhum setor, setor repetido). O
    corpo é de uma linha justamente porque tudo isso é do
    `services/evento.py` — inclusive o `commit`, que nunca é do router.

    **Nenhuma chamada à Ticketmaster acontece aqui.** AD-1: o catálogo já foi
    copiado pelo cliente na busca, e da publicação em diante o dado vive no
    banco. Publicar não pode depender de a Discovery estar no ar.

    O parâmetro do usuário se chama `organizador`, e não `_` como na rota
    acima, porque aqui ele é **usado**: é dele que sai o `organizador_id` do
    evento. Se o objeto fosse descartado, o dono teria que vir de algum outro
    lugar — e o único outro lugar seria o corpo da requisição.
    """
    return servico_de_evento.publicar(sessao, organizador, dados)
