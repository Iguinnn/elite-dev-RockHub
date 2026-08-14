"""Rotas do organizador: buscar no catálogo, publicar o evento e listar quem
pode ser escalado na portaria.

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

A Story 2.5 acrescentou o **terceiro** caso, e ele afina o critério:
`GET /portarias` é leitura, sem transação e sem invariante nenhuma — e mesmo
assim passa por service. O motivo é outro: ela toca o banco, e router que abre
uma `Session` para consultar é o que o paradigma proíbe sem exceção. A do
catálogo escapa porque não toca banco nenhum; toca uma integração que já
devolve o schema do projeto. Os três casos estão lado a lado neste arquivo:
leitura sem service (integração externa), leitura com service (banco), escrita
com service (transação e invariantes).

A Story 2.6 levou o arquivo a **cinco** rotas, e o critério passou a ter dois
exemplos de cada lado: `GET /eventos` e `GET /eventos/{evento_id}` são leituras
que tocam o banco, então passam por service — como a `/portarias`, e ao
contrário da `/catalogo`. Se este router crescer na Epic 3, parti-lo por
assunto passa a valer a discussão; hoje não vale, e é este docstring que segura
a coerência.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import exigir_papel
from app.integrations import ticketmaster
from app.models.evento import Evento
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.catalogo import ItemDoCatalogo
from app.schemas.evento import (
    EventoEdicao,
    EventoEntrada,
    EventoResumo,
    EventoSaida,
    PortariaSaida,
)
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


@router.get("/portarias", response_model=list[PortariaSaida])
def listar_portarias(
    _: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> list[Usuario]:
    """As contas de portaria que o organizador pode escalar num evento.

    **A lista é do organizador porque é ele quem escala** (AD-7): sem ver quem
    existe, ele teria que saber o e-mail de cada porteiro de cor, e uma letra
    errada viraria um `422` sem pista de qual conta existe.

    O custo é assumido e está registrado no README da raiz: qualquer
    organizador enxerga nome e e-mail de **todas** as contas de portaria do
    sistema. Numa plataforma com vários organizadores isso viraria escopo por
    organizador — que exige convite, que é outra epic.

    O parâmetro do usuário se chama `_` porque a rota realmente descarta o
    objeto: aqui só o papel importa. É o oposto do `POST /eventos`, onde ele é
    o dono do evento.
    """
    return servico_de_evento.listar_portarias(sessao)


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


@router.get("/eventos", response_model=list[EventoResumo])
def listar_meus_eventos(
    organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> list[EventoResumo]:
    """Os eventos que o organizador da sessão publicou, do mais próximo em diante.

    **O escopo é a sessão, e só ela.** Não há parâmetro de query, de caminho
    nem de corpo por onde um `organizador_id` pudesse entrar — a mesma
    disciplina de assinatura do `POST /eventos`. Aqui o objeto do usuário
    **é usado**, então ele não se chama `_` como no `GET /portarias`: é dele
    que sai o escopo da consulta.

    Lista vazia é `200` com `[]`, não `404`: a pergunta foi respondida, e quem
    decide o que dizer é a tela.
    """
    return servico_de_evento.listar_do_organizador(sessao, organizador)


@router.get("/eventos/{evento_id}", response_model=EventoSaida)
def obter_meu_evento(
    evento_id: UUID,
    organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> Evento:
    """Um evento do organizador, com setores e quem está escalado na porta.

    **`EventoSaida` reusado inteiro, o mesmo schema da publicação.** É o mesmo
    significado nas duas rotas — "o evento inteiro, como o organizador o vê" —,
    e é o que faz o recibo da publicação e esta tela nunca divergirem. (Foi o
    caminho oposto ao do `PortariaSaida` da Story 2.5, que **não** reusou o
    `UsuarioSaida`: lá a forma era parecida e o significado, outro.)

    **O `404` é o mesmo para "esse evento não existe" e "esse evento não é
    seu"**, byte a byte. Distinguir os dois faria desta rota um oráculo sobre
    os eventos alheios, e é a mesma regra que faz o login não dizer se o e-mail
    existe (Story 1.4). O motivo está inteiro no service.

    `evento_id: UUID` é o que dá o `422 DADOS_INVALIDOS` de graça para um id
    malformado — a estrutura é do Pydantic; o que o service decide é se o id
    **resolve** para um evento seu.
    """
    return servico_de_evento.obter_do_organizador(sessao, organizador, evento_id)


@router.put("/eventos/{evento_id}", response_model=EventoSaida)
def editar_meu_evento(
    evento_id: UUID,
    dados: EventoEdicao,
    organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> Evento:
    """Edita data, setores e escala de um evento que ainda não vendeu.

    **`PUT` com o corpo inteiro, e não `PATCH`.** Com uma lista de filhos,
    "não mandei" e "removi" viram a mesma coisa no corpo — e a ambiguidade cai
    justo na operação que pode apagar linha. O `PUT` manda o estado final: o que
    tem `id` é alteração, o que não tem é setor novo, e o que sumiu da lista é
    remoção.

    **O corpo é o `EventoEdicao`, e não o `EventoEntrada` da publicação.** Os
    cinco campos copiados do catálogo (AD-1) não entram: o organizador não digita
    nenhum deles nem ao publicar, e aceitá-los aqui faria esta tela ficar **mais
    poderosa que a de publicar** — o evento poderia virar outro show sem trocar
    de `origem_externa_id`.

    **`EventoSaida` de volta, o mesmo das outras três rotas de evento.** É o
    mesmo significado — "o evento inteiro, como o organizador o vê" —, e é o que
    faz o recibo da edição e a tela de detalhe nunca divergirem.

    Sexta rota do arquivo e a segunda de escrita, com service pelo critério do
    docstring do módulo — aqui existem transação e invariantes, e são as mais
    pesadas do projeto: um `SELECT ... FOR UPDATE`, a colheita do AD-4 e a trava
    de `vendidos == 0` acontecem todas antes de a primeira linha mudar.
    """
    return servico_de_evento.atualizar(sessao, organizador, evento_id, dados)


@router.delete("/eventos/{evento_id}", status_code=204, response_class=Response)
def excluir_meu_evento(
    evento_id: UUID,
    organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    sessao: Session = Depends(obter_sessao),
) -> Response:
    """Apaga um evento que ainda não vendeu, com o rastro morto dele junto.

    **`204` sem corpo, e não `200` com o evento apagado.** Não há consumidor para
    esse corpo — a tela já sabe o que pediu, e o que ela faz em seguida é sair
    para `Meus eventos`. O precedente é o `DELETE` do compartilhamento de
    ingresso (Story 4.4), o primeiro da API, e o `chamarApi` do frontend já corta
    antes do `.json()` neste status.

    ⚠️ **Não é idempotente como aquele, e a diferença é real.** Revogar um link
    duas vezes responde `204` nas duas, porque "o link não vale mais" continua
    verdade. Excluir duas vezes responde `404` na segunda: o recurso do caminho
    deixou de existir, e dizer `204` fingiria que esta chamada apagou alguma
    coisa. O `404` é o mesmo de sempre — byte a byte igual para "não existe" e
    "não é seu".

    **A trava é `vendidos == 0`, e é a única.** Show que já aconteceu **pode** ser
    excluído, ao contrário da edição — o motivo inteiro da assimetria está no
    service. Erro possível além do `404`: `409 EVENTO_COM_VENDA`, com a frase no
    verbo certo.

    Sétima rota do arquivo, terceira de escrita, e a única sem schema de entrada:
    o caminho é o pedido inteiro.
    """
    servico_de_evento.excluir(sessao, organizador, evento_id)
    # `Response` explícito, e não `return None`: com `status_code=204` o
    # FastAPI ainda tentaria serializar o retorno e emitir `content-length`,
    # que é o que quebra um `204` de verdade. Mesma linha do `DELETE` da
    # Story 4.4, em `api/cliente.py`.
    return Response(status_code=204)
