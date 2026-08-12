"""Rotas de quem tem conta de cliente: reservar, pagar e ver o que comprou.

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

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import exigir_papel
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.ingresso import IngressoDetalhe, IngressoNaLista
from app.schemas.pagamento import PagamentoEntrada
from app.schemas.reserva import ReservaEntrada, ReservaSaida
from app.services import ingresso as servico_de_ingresso
from app.services import reserva as servico_de_reserva
from app.services.pagamento import PaymentGateway, obter_gateway

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


@router.post("/reservas/{reserva_id}/pagamento", response_model=ReservaSaida)
def pagar_reserva(
    reserva_id: UUID,
    dados: PagamentoEntrada,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
    gateway: PaymentGateway = Depends(obter_gateway),
) -> ReservaSaida:
    """Cobra a reserva e a leva a `PAGA` ou `RECUSADA` (Story 3.8).

    **Ação sobre um recurso que já tem endereço**, e não `POST /pagamentos` com
    `reserva_id` no corpo — que inventaria um recurso sem tabela — nem
    `PATCH /reservas/{id}` com o estado, que deixaria o cliente **nomear** o
    estado de destino. O AD-4 diz que transição é do servidor; a URL não pode
    dizer o contrário.

    **`200`, e não `201`**: nada nasce com endereço próprio aqui. A reserva
    continua sendo a mesma, com outro estado — e é ela que volta no corpo, para
    a tela não precisar de uma segunda chamada para saber o que aconteceu.

    **O gateway entra por dependência** (AD-10). É o que permite ao teste trocar
    a implementação com `dependency_overrides`, e é a prova prática de que este
    caminho não conhece `PagamentoSimulado`.

    **Os erros possíveis:**

    - `404 RESERVA_NAO_ENCONTRADA` — inexistente **ou** de outra pessoa, como no
      `GET` acima e pelo mesmo motivo
    - `409 RESERVA_EXPIRADA` — o prazo acabou. A reserva vira `EXPIRADA`, o
      estoque volta e **nada é cobrado** (AC1 da Story 3.7)
    - `409 RESERVA_NAO_PENDENTE` — já `PAGA`, `RECUSADA` ou `CANCELADA`.
      Pagamento reprocessado cai aqui, e é por isso que ele não emite ingresso
      novo (AD-14)
    - `402 PAGAMENTO_RECUSADO` — cartão terminado em `0002` (AD-10). A reserva
      vira `RECUSADA` e o estoque volta
    - `422 DADOS_INVALIDOS` — corpo malformado, inclusive "meio é cartão e
      faltou o número"

    ⚠️ **O `402` é o único status desta API fora da tabela de sempre**, e é
    decisão do Igor: recusa de pagamento não é conflito de estado. O **corpo**
    continua `{"erro": {"codigo", "mensagem"}}`, sem exceção ao `core/erros.py`.
    """
    return servico_de_reserva.pagar(sessao, cliente, reserva_id, dados, gateway)


@router.get("/ingressos", response_model=list[IngressoNaLista])
def listar_ingressos(
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> list[IngressoNaLista]:
    """Todos os ingressos de todas as compras pagas de quem está na sessão.

    **Rota própria, e não a lista filtrada da tela de detalhe da reserva**
    (techspec da 4.1): o ingresso é um agregado com vida própria desde a Story
    3.9, e é neste endereço que a Story 4.3 vai pendurar o compartilhamento.

    **`200` com lista vazia é resposta legítima** — nunca `404`. Quem nunca
    comprou recebeu a pergunta certa, e a resposta é "nenhum".

    A lista chega **chapada**, ordenada por `evento_data_hora` crescente: quem
    corta em *Ativos* e *Utilizados* — por `usado_em IS NULL` — é a tela, o
    mesmo molde do `GET /organizador/eventos` da 2.6.
    """
    return servico_de_ingresso.listar(sessao, cliente)


@router.get("/ingressos/{ingresso_id}", response_model=IngressoDetalhe)
def obter_ingresso(
    ingresso_id: UUID,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> IngressoDetalhe:
    """O canhoto cheio, com o `codigo` que vira QR — a Story 4.2.

    **Um `404 INGRESSO_NAO_ENCONTRADO` para "não existe" e para "não é seu"**,
    nunca `403`: mesma disciplina do `obter_reserva` acima e do
    `obter_do_organizador` da 2.6.

    **`ingresso_id: UUID`, e não `str`**: o Pydantic recusa um caminho que não
    seja UUID com `422` antes de a consulta ser montada.

    **`share_token` entra na resposta a partir da Story 4.3** — `null` quando
    nunca foi compartilhado ou depois de revogado. É o que faz o dono
    reencontrar o próprio link ao voltar à tela.
    """
    return servico_de_ingresso.obter(sessao, cliente, ingresso_id)


@router.post("/ingressos/{ingresso_id}/compartilhamento", response_model=IngressoDetalhe)
def compartilhar_ingresso(
    ingresso_id: UUID,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> IngressoDetalhe:
    """Gera o link público deste ingresso, ou devolve o que já existe (4.3).

    **Subrecurso `compartilhamento`, e não `POST /ingressos/{id}/compartilhar`.**
    O par de operações é criar e remover um link, e o HTTP já nomeia as duas: o
    `DELETE` do mesmo endereço revoga (Story 4.4). Um verbo em português na URL
    esconderia num nome inventado a operação idempotente que o método já diz, e
    ela teria de ser explicada num comentário em vez de ser lida.

    **Sem corpo.** Não há nada para escolher: o token é gerado pelo servidor, e
    o endereço do ingresso já diz de qual link se trata.

    ⚠️ **`200` nas duas vezes, e nunca `201`.** Compartilhar é idempotente: com
    link ativo, a chamada devolve **o mesmo token** e não escreve nada. Um `201`
    na primeira vez informaria "foi agora" a ninguém que lê, e um token novo a
    cada clique seria uma revogação silenciosa — cortaria quem já recebeu o
    link, sem a confirmação que a Story 4.4 existe para exigir.

    **A URL de compartilhamento é montada pelo navegador**, não aqui: a resposta
    carrega o token, e a tela monta `{origem}/i/{token}`. O backend não conhece
    — nem deve — o domínio do frontend, que muda a cada Preview da Vercel.

    Erro possível: `404 INGRESSO_NAO_ENCONTRADO` — inexistente **ou** de outra
    pessoa, com a mesma frase do `GET` acima e pelo mesmo motivo.
    """
    return servico_de_ingresso.compartilhar(sessao, cliente, ingresso_id)


@router.delete(
    "/ingressos/{ingresso_id}/compartilhamento",
    status_code=204,
    response_class=Response,
)
def revogar_compartilhamento(
    ingresso_id: UUID,
    cliente: Usuario = Depends(exigir_papel(PapelUsuario.CLIENTE)),
    sessao: Session = Depends(obter_sessao),
) -> Response:
    """Faz o link deste ingresso parar de valer — a Story 4.4.

    ⚠️ **O primeiro `DELETE` da API, e ele não quebra padrão nenhum.** Nunca
    houve aqui uma operação com forma de remoção: `POST /reservas/{id}/pagamento`
    não é "evitamos `DELETE`", é um comando que de fato não remove nada.
    *Descartei* `POST /ingressos/{id}/revogar`, que preservaria a uniformidade
    ao custo de esconder num verbo em português a operação idempotente que o
    HTTP já nomeia — e que teria de ser explicada num comentário em vez de ser
    lida no método. O par fica: `POST` cria o link, `DELETE` do mesmo endereço o
    revoga.

    ⚠️ **`204` também quando já não havia link.** O `DELETE` é idempotente por
    definição, e quem pediu para o link não valer mais obteve exatamente isso.
    Revogar duas vezes responde `204` nas duas — a segunda chamada não é erro
    nenhum, é a mesma verdade dita de novo.

    **`204`, e não `200` com o ingresso.** Não há estado novo para a tela
    aprender: o link deixou de existir, e a ilha já sabe disso por ter pedido. O
    `share_token` volta a `null` no próximo `GET`, que o `router.refresh()`
    dispara.

    **Depois disto, compartilhar gera um token diferente** — o link antigo não
    volta, e é isso que faz a revogação ser um corte de verdade.

    Erro possível: `404 INGRESSO_NAO_ENCONTRADO` — inexistente **ou** de outra
    pessoa, como nas duas irmãs e pelo mesmo motivo.
    """
    servico_de_ingresso.revogar_compartilhamento(sessao, cliente, ingresso_id)
    # `Response` explícito, e não `return None`: com `status_code=204` o
    # FastAPI serializaria o `None` como o corpo `null`, e uma resposta `204`
    # com corpo é resposta malformada — o `chamarApi` do frontend, que corta no
    # `status === 204` antes de chamar `.json()`, nunca veria o defeito.
    return Response(status_code=204)
