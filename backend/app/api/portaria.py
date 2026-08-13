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
`/portaria`, e a rota da validação (Story 5.2) vai entrar aqui embaixo, com o
`evento_id` no caminho — é o que permitirá o `403` do AD-7 sair de uma
dependência, e não de um `if` no corpo do handler.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.dependencias import exigir_papel
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.evento import TurnoDaPortaria
from app.services import evento as servico_de_evento

router = APIRouter(prefix="/portaria", tags=["portaria"])


@router.get("/eventos", response_model=list[TurnoDaPortaria])
def meus_turnos(
    portaria: Usuario = Depends(exigir_papel(PapelUsuario.PORTARIA)),
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
