"""Rotas do visitante: o que dá para ver sem ter conta.

**O critério de entrada aqui é "não exige conta"** — e é isso que separa este
router dos outros. `auth.py` é de quem entra, `organizador.py` é por **papel**
(toda rota de lá começa por `Depends(exigir_papel(ORGANIZADOR))`), `saude.py` é
da Railway. Este é o único cuja superfície é definida pela ausência de
autenticação: qualquer rota que passe a exigir sessão está no arquivo errado.

A distinção importa porque ela vai ser exercitada logo: a Story 3.4 pendura
`/eventos/{id}` aqui, e as Stories 3.5 em diante criam `cliente.py`, que é o
oposto — exige conta, e é onde a reserva mora. "Público" não é o mesmo que
"cliente", e misturar os dois num arquivo só faria a próxima pessoa procurar a
guarda de sessão em dois lugares.

**Sem `prefix`**, ao contrário do `organizador.py`: o recurso é evento, e a
rota pública dele é `/eventos` — a URL de quem só está olhando não carrega o
nome de um papel.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.schemas.evento import (
    EventoEmDestaque,
    EventoNaProgramacao,
    PeriodoDaProgramacao,
)
from app.services import evento as servico_de_evento

router = APIRouter(tags=["público"])


# ⚠️ **As duas rotas de path fixo abaixo — `/eventos/cidades` e
# `/eventos/destaque` — precisam continuar declaradas antes de qualquer
# `/eventos/{id}`.** A Story 3.4 pendura o detalhe do evento neste mesmo router,
# e o FastAPI casa as rotas na ordem em que elas foram registradas: com
# `/eventos/{id}` em cima, uma chamada a `/eventos/cidades` tentaria ler
# `"cidades"` como UUID e devolveria `422` — um erro de validação para um
# endereço que existe, que é a pior pista possível para quem for procurar o
# defeito.
#
# O aviso é **um só para as duas**, e não um por rota: elas formam um bloco, e
# repetir a explicação faria a terceira parecer uma exceção quando ela for a
# regra. Quem acrescentar a próxima rota de path fixo acrescenta-a aqui dentro.
@router.get("/eventos/cidades", response_model=list[str])
def listar_cidades_em_cartaz(
    sessao: Session = Depends(obter_sessao),
) -> list[str]:
    """As cidades com show na programação, distintas e em ordem alfabética.

    **Pública pelo mesmo critério da rota abaixo**: nenhuma dependência de
    sessão, nenhum `Depends(exigir_papel(...))`. Ela alimenta os chips de filtro
    da raiz, que é a tela de quem ainda não tem conta.

    **Sem parâmetro nenhum, e isso é a decisão** — ela é o universo de escolhas,
    não o resultado da busca. O motivo inteiro está no service; o resumo é que
    uma lista de facetas que encolhe conforme se filtra faz o chip sumir debaixo
    do cursor de quem ia clicar.
    """
    return servico_de_evento.listar_cidades_em_cartaz(sessao)


@router.get("/eventos/destaque", response_model=EventoEmDestaque | None)
def obter_destaque(
    sessao: Session = Depends(obter_sessao),
) -> EventoEmDestaque | None:
    """O próximo show da programação — a chamada principal da raiz (Story 3.3).

    **Pública pelo mesmo critério das outras duas**: nenhuma dependência de
    sessão, nenhum `Depends(exigir_papel(...))`. Ela desenha o bloco grande da
    raiz, que é a tela de quem ainda não tem conta.

    **Sem parâmetro nenhum** — nem `q`, nem `cidade`, nem `periodo`, ao
    contrário da `listar_programacao` logo abaixo. A capa é *o próximo show*,
    não o resultado de uma busca: com filtro ativo a tela não a renderiza e nem
    sequer a chama (decisão do Igor). Uma rota que aceitasse os mesmos filtros
    convidaria a "capa que reflete o resultado filtrado", que é a alternativa
    descartada — com um resultado só, a tela mostraria o mesmo evento em cima e
    embaixo.

    **Corpo `null` com `200` quando não há show em cartaz — nunca `404`.** É a
    mesma decisão do `200 []` da programação: "não há nada marcado" é uma
    resposta sobre o produto, não um endereço que não existe. E **`204` está
    fora** por um motivo concreto do outro lado da rede: ele não tem corpo, e o
    `resposta.json()` da tela estouraria num `catch` que existe para falha —
    "não há show em cartaz" viraria "não foi possível carregar", que é a única
    das duas frases que manda a pessoa fazer a coisa errada.

    **O que o corpo não carrega**: `capacidade`, `vendidos`, `preco_centavos` —
    UX-DR7, garantido pelo `response_model` e não pela tela. `setores` vem como
    **lista de nomes**, que é o que a ficha desenha, e `preco_minimo_centavos` é
    derivado dos setores com ingresso sem revelar nenhum dos dois números; o
    motivo inteiro está no docstring de `EventoEmDestaque`.
    """
    return servico_de_evento.obter_destaque(sessao)


@router.get("/eventos", response_model=list[EventoNaProgramacao])
def listar_programacao(
    sessao: Session = Depends(obter_sessao),
    # ⚠️ **Os três são `Query`, e nenhum é `Depends`.** É essa lista que mantém
    # a rota pública: ela ganhou entrada de gente sem ganhar exigência de conta.
    #
    # `max_length=120` é o **mesmo** teto de `GET /organizador/catalogo`, e o
    # `<input>` da tela leva o `maxLength` gêmeo — foi assim que a Story 2.2
    # impediu a tela de acusar a Ticketmaster por um erro do próprio formulário.
    q: str = Query("", max_length=120),
    cidade: str = Query("", max_length=120),
    periodo: PeriodoDaProgramacao = Query(PeriodoDaProgramacao.TODOS),
) -> list[EventoNaProgramacao]:
    """A programação: eventos publicados que ainda vão acontecer.

    **Pública por assinatura, não por disciplina.** Não há
    `Depends(exigir_papel(...))` nem nenhuma outra dependência de sessão aqui —
    é a lista de parâmetros que garante que ela responde sem cookie, e não a
    boa vontade de quem a mantiver. Chamá-la logada como cliente, organizador
    ou portaria devolve exatamente a mesma coisa: não existe caminho pelo qual
    a identidade de quem chama influencie o resultado. Os três filtros da Story
    3.2 não mudaram isso: são `Query`, e parâmetro de query não é credencial.

    **Os três filtros, e o que cada um faz:**

    - `q` — trecho de `nome`, `local` **ou** `cidade`, sem caixa e sem acento.
      Vazio ou só espaços vale como ausente
    - `cidade` — igualdade exata; o valor vem dos chips, ou seja, de
      `GET /eventos/cidades`
    - `periodo` — `todos`, `semana` (7 dias corridos) ou `mes` (30 dias
      corridos). Valor fora do enum morre aqui, com `422`, em vez de virar uma
      comparação silenciosa lá dentro

    Eles se somam com `AND`, **sobre** as duas condições que a Story 3.1 já
    impunha: rascunho e evento passado continuam fora, com ou sem busca.

    **O corpo não carrega estoque** — nem `capacidade`, nem `vendidos`, nem os
    setores. O `response_model` é quem garante isso (UX-DR7); o motivo inteiro
    está no docstring de `EventoNaProgramacao`. `esgotado` e
    `preco_minimo_centavos` são derivados do estoque sem revelá-lo. Um `where`
    novo não afrouxa nada disso.

    Banco vazio devolve `200 []`, nunca `404`: "não há show em cartaz" é uma
    resposta sobre o produto, não um endereço que não existe. Busca sem
    resultado também — quem distingue os dois casos é a tela, não o status.
    """
    return servico_de_evento.listar_programacao(sessao, q, cidade, periodo)
