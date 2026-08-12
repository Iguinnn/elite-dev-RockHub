"""Rotas de quem tem conta de cliente: reservar e acompanhar a reserva.

**O critério de entrada aqui é o papel `CLIENTE`** — toda rota deste arquivo
começa por `Depends(exigir_papel(PapelUsuario.CLIENTE))`, na assinatura (AD-9),
e é isso que o separa dos outros quatro routers. Ele é o **oposto exato** do
`publico.py`, cuja superfície é definida pela **ausência** de autenticação: o
docstring de lá anuncia este arquivo desde a Story 3.4, e a frase continua
verdadeira. Qualquer rota que passe a responder sem sessão está no arquivo
errado, e vice-versa.

O critério é o mesmo do `organizador.py`, com outro papel — mas **sem `prefix`**,
como o `publico.py`. O `organizador.py` tem prefixo porque as rotas dele são *do
organizador* (o catálogo, os eventos dele); aqui o recurso é a reserva, e a URL
dela é `/reservas`. A URL não carrega o nome de um papel quando o recurso já tem
nome próprio.

**`cliente_id` vem sempre da sessão.** Não existe parâmetro de corpo, de query
ou de caminho por onde outro id pudesse entrar — reservar em nome de outra
pessoa não é uma chamada que o service recusa, é uma chamada que não existe.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import exigir_papel
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.reserva import ReservaEntrada, ReservaSaida
from app.services import reserva as servico_de_reserva

router = APIRouter(tags=["cliente"])


@router.post("/reservas", response_model=ReservaSaida, status_code=201)
def reservar(
    dados: ReservaEntrada,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> ReservaSaida:
    """Segura os ingressos escolhidos por 10 minutos — a primeira escrita do cliente.

    **O corpo não carrega `cliente_id`, `estado`, `expira_em` nem
    `total_centavos`**, e os quatro nascem do outro lado: o primeiro da sessão,
    os outros três da regra. O que atravessa é o show e a lista de
    `{setor_id, quantidade}`.

    **`201`, e não `200`**: a chamada cria um recurso com endereço próprio, que é
    o `GET /reservas/{id}` logo abaixo. Mesma escolha do `POST
    /organizador/eventos`.

    **Os erros possíveis, e o que cada um significa:**

    - `422 RESERVA_SEM_ITEM` — `itens` vazio ou ausente
    - `422 ITEM_DUPLICADO` — o mesmo setor em dois itens do corpo
    - `422 ACIMA_DO_MAXIMO_POR_COMPRA` — a **soma** das quantidades passa do teto
      que o `EventoPublico` já declara ao stepper
    - `422 SETOR_INVALIDO` — setor que não existe **ou** que é de outro show; um
      código só, porque distinguir transformaria a rota num oráculo
    - `404 EVENTO_NAO_ENCONTRADO` — id inexistente, rascunho ou data já passada,
      com a mesma mensagem do `GET /eventos/{id}` e pelo mesmo motivo
    - `409 ESTOQUE_INSUFICIENTE` — o `UPDATE` condicional do AD-3 afetou zero
      linhas. É a resposta da corrida, e a única fonte dela

    ⚠️ **O corpo do `409` não tem campo novo** (decisão do Igor): ele continua
    `{"erro": {"codigo", "mensagem"}}`, como toda resposta de erro desta API. A
    frase do UX-DR8 — qual setor esgotou, o que ainda sobrou — é montada pela
    tela, relendo `GET /eventos/{id}` com dados frescos. O `core/erros.py` existe
    desde a Story 1.1 para a API ter **uma** forma de erro, e a primeira exceção
    é a que abre a segunda.
    """
    return servico_de_reserva.criar(sessao, cliente, dados)


@router.get("/reservas/{reserva_id}", response_model=ReservaSaida)
def obter_reserva(
    reserva_id: UUID,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> ReservaSaida:
    """A reserva de quem está na sessão, com os itens, o prazo e o total.

    **Nasce nesta story, e não na 3.8**, porque a reserva tem endereço próprio: a
    página que só existisse como resposta do `POST` não sobreviveria a recarregar
    — e a reserva é uma linha no banco com prazo, não um estado de tela.

    **Um `404 RESERVA_NAO_ENCONTRADA` para "não existe" e para "não é sua"**,
    nunca `403`. Distinguir os dois diria a quem varresse UUIDs quais deles são
    reservas de alguém; é a mesma disciplina do `obter_do_organizador` da 2.6.

    **`reserva_id: UUID`, e não `str`**: o Pydantic recusa `/reservas/banana` com
    `422` antes de a consulta ser montada, e a tela trata `404` e `422` no mesmo
    ramo.

    **O corpo não carrega estoque** — nem `capacidade`, nem `vendidos`, nem
    disponibilidade de setor (UX-DR7, AD-13). `quantidade`,
    `preco_unitario_centavos` e `total_centavos` são a compra, não o inventário.
    """
    return servico_de_reserva.obter(sessao, cliente, reserva_id)
