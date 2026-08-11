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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.schemas.evento import EventoNaProgramacao
from app.services import evento as servico_de_evento

router = APIRouter(tags=["público"])


@router.get("/eventos", response_model=list[EventoNaProgramacao])
def listar_programacao(
    sessao: Session = Depends(obter_sessao),
) -> list[EventoNaProgramacao]:
    """A programação: eventos publicados que ainda vão acontecer.

    **Pública por assinatura, não por disciplina.** Não há
    `Depends(exigir_papel(...))` nem nenhuma outra dependência de sessão aqui —
    é a lista de parâmetros que garante que ela responde sem cookie, e não a
    boa vontade de quem a mantiver. Chamá-la logada como cliente, organizador
    ou portaria devolve exatamente a mesma coisa: não existe caminho pelo qual
    a identidade de quem chama influencie o resultado.

    **O corpo não carrega estoque** — nem `capacidade`, nem `vendidos`, nem os
    setores. O `response_model` é quem garante isso (UX-DR7); o motivo inteiro
    está no docstring de `EventoNaProgramacao`. `esgotado` e
    `preco_minimo_centavos` são derivados do estoque sem revelá-lo.

    Banco vazio devolve `200 []`, nunca `404`: "não há show em cartaz" é uma
    resposta sobre o produto, não um endereço que não existe.
    """
    return servico_de_evento.listar_programacao(sessao)
