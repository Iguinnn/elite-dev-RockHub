"""Rotas de quem trabalha na porta. O primeiro arquivo da Epic 5.

**O papel `PORTARIA` existe desde a Story 1.6 e nunca tinha sido usado em rota
nenhuma.** `exigir_papel` é genérica desde então, e é ela que faz esta rota
nascer com `401` e `403` prontos, sem uma linha de `if` no corpo do handler
(AD-9). O papel diz o que a pessoa faz; a `evento_portaria` diz **onde** — e é
por isso que a escala é vínculo, e não uma coluna em `usuario` (AD-7).

**Router próprio, e não mais uma rota em `organizador.py`.** A escala é lida
pelos dois lados: o organizador pergunta "quem eu posso pôr na porta"
(`GET /organizador/portarias`, Story 2.5), e aqui se pergunta "em que portas eu
trabalho". São dois papéis, dois prefixos e duas dependências diferentes na
assinatura — juntá-los num arquivo só faria o próximo leitor conferir o
`Depends` de cada rota para saber de quem é a tela.

**O prefixo `/portaria` não tem armadilha de ordem**, ao contrário do
`/ingressos` da Story 4.3, que passou a morar em dois routers e só se sustenta
pela contagem de segmentos do caminho. Nada mais neste projeto começa por
`/portaria`, e a rota da validação da Story 5.2 entrou aqui embaixo com o
`evento_id` no caminho — é o que permite o `403` do AD-7 sair de uma
dependência, e não de um `if` no corpo do handler.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import PORTARIA_DA_SESSAO, exigir_porta_aberta
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.schemas.evento import TurnoDaPortaria
from app.schemas.ingresso import ResultadoDaValidacao, ValidacaoEntrada
from app.services import evento as servico_de_evento
from app.services import ingresso as servico_de_ingresso

router = APIRouter(prefix="/portaria", tags=["portaria"])


@router.get("/eventos", response_model=list[TurnoDaPortaria])
def meus_turnos(
    portaria: Usuario = Depends(PORTARIA_DA_SESSAO),
    sessao: Session = Depends(obter_sessao),
) -> list[TurnoDaPortaria]:
    """Os eventos em que a conta da sessão foi escalada, do mais próximo em diante.

    **O escopo é a sessão, e só ela.** Não há parâmetro de query, de caminho nem
    de corpo por onde um `usuario_id` pudesse entrar — a mesma assinatura do
    `GET /organizador/eventos`. Ver o turno de outra pessoa não é uma chamada que
    esta rota recusa, é uma chamada que não existe.

    **A lista não corta por tempo**, e evento que já começou continua nela. O
    motivo inteiro está no service: a portaria trabalha exatamente do outro lado
    do corte que as rotas públicas fazem.

    O parâmetro do usuário se chama `portaria`, e não `_` como no
    `GET /organizador/portarias`, porque aqui ele **é usado**: é dele que sai o
    escopo da consulta.

    Lista vazia é `200` com `[]`, nunca erro — a pergunta "onde eu trabalho?" foi
    respondida com "em lugar nenhum ainda", e quem decide o que dizer é a tela.
    """
    return servico_de_evento.listar_escalados(sessao, portaria)


@router.post("/eventos/{evento_id}/validacoes", response_model=ResultadoDaValidacao)
def validar_ingresso(
    dados: ValidacaoEntrada,
    evento: Evento = Depends(exigir_porta_aberta),
    portaria: Usuario = Depends(PORTARIA_DA_SESSAO),
    sessao: Session = Depends(obter_sessao),
) -> ResultadoDaValidacao:
    """O veredito de um código na porta deste evento — o FR6 inteiro (Story 5.2).

    **`POST` e um subrecurso no plural**, e não `POST /portaria/validacoes` com o
    `evento_id` no corpo: com o evento no caminho, a dependência resolve as duas
    recusas **antes de o handler existir**, que é literalmente o AC "recebe `403`
    antes de qualquer consulta ao ingresso". Com o id no corpo, o `403` do AD-7
    viraria a primeira linha daqui — e o AD-9 é explícito: papel e autorização se
    declaram na assinatura, nunca com `if` no corpo.

    **É `POST` porque escreve**, e o que ele escreve é irreversível: `usado_em`
    grava uma vez e não volta. Nada aqui é idempotente por natureza — é o
    contrário, a segunda chamada com o mesmo código responde outra coisa de
    propósito.

    ⚠️ **Os quatro vereditos respondem `200`**, inclusive os três que negam
    entrada. O motivo está inteiro no docstring do `ResultadoDaValidacao`; o
    resumo é que recusar entrada é o trabalho da portaria dando certo. Os `403`
    desta rota são de outra natureza — "você não trabalha aqui" e "a porta ainda
    não abriu" —, e vêm da dependência.

    **`evento` e `portaria` na mesma assinatura, e o `Usuario` é resolvido uma
    vez só**: `PORTARIA_DA_SESSAO` é um nome, não uma chamada nova a
    `exigir_papel` — o comentário dele em `core/dependencias.py` explica por que
    a diferença importa.
    """
    return servico_de_ingresso.validar(sessao, portaria, evento, dados.codigo)
