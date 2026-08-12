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
nome de um papel. A partir da Story 4.3 há um segundo recurso aqui, o ingresso
compartilhado, e a ausência de prefixo é o que permite que a URL dele seja
`/ingressos/...` mesmo com as rotas do dono morando em `cliente.py` — ver o
aviso no fim do arquivo.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.schemas.evento import (
    EventoEmDestaque,
    EventoNaProgramacao,
    EventoPublico,
    PeriodoDaProgramacao,
)
from app.schemas.ingresso import IngressoDetalhe
from app.services import evento as servico_de_evento
from app.services import ingresso as servico_de_ingresso

router = APIRouter(tags=["público"])


# ⚠️ **As duas rotas de path fixo abaixo — `/eventos/cidades` e
# `/eventos/destaque` — precisam continuar declaradas antes do
# `/eventos/{evento_id}` do fim do arquivo.** Ele existe desde a Story 3.4, e o
# FastAPI casa as rotas na ordem em que elas foram registradas: com o detalhe em
# cima, uma chamada a `/eventos/cidades` tentaria ler `"cidades"` como UUID e
# devolveria `422` — um erro de validação para um endereço que existe, que é a
# pior pista possível para quem for procurar o defeito. Há um teste provando as
# duas de pé justamente por isso.
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


# ⚠️ **Esta é a rota de path param do bloco de cima, e é por isso que ela está no
# fim do arquivo.** Mover qualquer coisa para depois dela é seguro; mover ela para
# antes de `/eventos/cidades` ou `/eventos/destaque` quebra as duas.
@router.get("/eventos/{evento_id}", response_model=EventoPublico)
def obter_evento(
    evento_id: UUID,
    sessao: Session = Depends(obter_sessao),
) -> EventoPublico:
    """Um evento em cartaz com seus setores — a tela da escolha (Story 3.4).

    **Pública pelo mesmo critério das outras três**: nenhuma dependência de
    sessão, nenhum `Depends(exigir_papel(...))`, nenhum parâmetro de query.
    Chamá-la logado como cliente, organizador ou portaria devolve exatamente o
    mesmo corpo — não existe caminho pelo qual a identidade de quem chama
    influencie o resultado. É ela que fecha o link que a fila da programação (3.1)
    e a chamada principal (3.3) já apontavam.

    **`evento_id: UUID`, e não `str`.** O Pydantic recusa `/eventos/banana` com
    `422` antes de a consulta ser montada, e a tela trata `404` e `422` no mesmo
    ramo: para quem lê, "esse endereço está errado" e "esse show não está em
    cartaz" são a mesma coisa.

    **`404` único para três casos** — `id` inexistente, evento em rascunho e
    evento cuja data já passou. O motivo está no service: distinguir os três
    transformaria a rota num oráculo sobre o que ainda não foi publicado.

    **O que o corpo recusa**: `capacidade` e `vendidos` (UX-DR7, AD-13), e
    `publicado_em`, `origem_externa_id` e `organizador_id` (assunto de quem
    publica). Esta é a rota pública que chega mais perto do estoque — é nela que a
    pessoa escolhe **quantos** ingressos quer —, e o que atravessa em lugar dos
    dois números é uma proporção e uma palavra por setor. `preco_centavos`
    **entra**, e é a primeira vez em rota de cliente: preço não é contagem.
    """
    return servico_de_evento.obter_publico(sessao, evento_id)


# --------------------------------------------------------------------------- #
# O ingresso compartilhado (Story 4.3)
#
# ⚠️ **O espaço de URL `/ingressos` mora em dois arquivos a partir daqui**, e o
# `cliente.py` é registrado **antes** deste no `main.py`. O que salva a rota
# abaixo é ela ter **três** segmentos contra os dois de
# `/ingressos/{ingresso_id}`: uma rota pública futura de dois segmentos sob
# `/ingressos` seria engolida pela autenticada e voltaria `401` ou `422` — um
# erro que não menciona autenticação nenhuma para quem for procurar o defeito.
# Há teste provando esta de pé sem sessão, pelo mesmo motivo que existe o das
# duas rotas de path fixo lá em cima.
#
# **Ela está aqui, e não ao lado das irmãs em `cliente.py`**, porque o critério
# declarado deste arquivo é a **ausência de autenticação**, não o recurso. Uma
# rota sem guarda de sessão dentro do arquivo cuja invariante escrita é que toda
# rota dali tem uma seria o tipo de exceção que faz a próxima pessoa procurar a
# guarda em dois lugares.
# --------------------------------------------------------------------------- #
@router.get("/ingressos/compartilhados/{token}", response_model=IngressoDetalhe)
def obter_ingresso_compartilhado(
    token: str,
    sessao: Session = Depends(obter_sessao),
) -> IngressoDetalhe:
    """O canhoto que um link compartilhado abre — sem conta nenhuma (Story 4.3).

    **Pública pelo mesmo critério das outras quatro**: nenhuma dependência de
    sessão, nenhum `Depends(exigir_papel(...))`. Quem recebeu o link por
    WhatsApp pode nunca ter entrado no RockHub, e é essa pessoa que vai passar
    na porta com ele.

    **O corpo é o `IngressoDetalhe` inteiro**, `titular_nome` e `usado_em`
    inclusive — o mesmo canhoto que o dono vê. Esconder o titular ou fingir que
    um ingresso já utilizado ainda vale seria um segundo canhoto, diferente do
    de verdade, e quem chegasse na porta com ele descobriria a diferença no pior
    lugar possível.

    ⚠️ **Token revogado e token que nunca existiu respondem igual** — `404
    LINK_NAO_ENCONTRADO`, mesma frase. É o que faz a revogação da Story 4.4 ser
    um corte, e não um aviso de que existiu algo ali.

    ⚠️ **O `token` é `str`, e não há validação de formato — de propósito.** Ele
    não é UUID nem carrega estrutura: é `secrets.token_urlsafe(24)`, e qualquer
    coisa que não bata com a coluna cai no mesmo `404`. Um `422` para "esse
    token tem forma estranha" contaria a quem varresse endereços qual é o
    formato certo.

    ⚠️ **Esta rota não confere assinatura, e não deve.** Ela é visualização
    (AD-8); o `share_token` **não** substitui o HMAC do AD-5. Quem recalcula é a
    portaria, na Epic 5 — chamar `conferir_codigo` aqui daria a impressão de que
    o token autentica alguma coisa.
    """
    return servico_de_ingresso.obter_por_share_token(sessao, token)
