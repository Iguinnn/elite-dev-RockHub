"""Autenticação e autorização como **dependências do FastAPI** (AD-9).

A regra do projeto inteiro está aqui: papel se declara na assinatura do
endpoint, nunca se confere no corpo dele.

    @router.get("/eventos")
    def meus_eventos(
        usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
    ) -> ...

Um `if usuario.papel == ...` dentro do handler funcionaria igual e é errado por
duas razões: some da documentação gerada (`/docs` não tem como saber que a rota
é restrita) e depende de alguém lembrar de escrevê-lo em cada rota nova. Na
assinatura, esquecer a proteção é uma linha ausente que se vê à distância.

**Autenticação vem antes de autorização.** Sem sessão válida é `401`; com sessão
válida e papel errado é `403`. Quem garante essa ordem é o `Depends` encadeado
lá embaixo — primeiro se pergunta quem é, depois o que pode.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.db import obter_sessao
from app.core.erros import ErroDeDominio
from app.core.seguranca import ler_token_sessao
from app.models.evento import Evento
from app.models.usuario import PapelUsuario, Usuario
from app.services import autenticacao
from app.services import evento as servico_de_evento


def _nao_autenticado() -> ErroDeDominio:
    return ErroDeDominio("NAO_AUTENTICADO", "Entre para continuar.", status_http=401)


def usuario_atual(
    requisicao: Request,
    sessao: Session = Depends(obter_sessao),
) -> Usuario:
    """Traduz o cookie de sessão no `Usuario` que está do outro lado.

    Os quatro modos de falhar — cookie ausente, token corrompido, token
    expirado e conta apagada — respondem **exatamente a mesma coisa**. São
    situações diferentes para quem depura e a mesma para quem chama: não há
    sessão válida. Diferenciá-las na resposta transformaria a rota num oráculo
    ("esse id já existiu?"), pela mesma razão que o login da Story 1.4 não
    revela se o e-mail existe.

    `obter_settings()` é chamado aqui dentro, e não no import: preso no import,
    a configuração congela no primeiro carregamento do módulo e o
    `monkeypatch` dos testes deixa de valer.
    """
    token = requisicao.cookies.get(obter_settings().cookie_sessao_nome)
    if not token:
        raise _nao_autenticado()

    # `ler_token_sessao` já colapsa expirado e adulterado num `None` só —
    # `jwt.decode` levanta `PyJWTError` para os dois (Story 1.4).
    carga = ler_token_sessao(token)
    if carga is None:
        raise _nao_autenticado()

    try:
        # `str(...)` antes do `UUID(...)` de propósito: `carga` é um `dict` sem
        # tipo, e um `sub` numérico faria `UUID(int)` levantar `AttributeError`
        # — que o `except` abaixo não pegaria, virando 500.
        usuario_id = UUID(str(carga["sub"]))
    except (KeyError, ValueError):
        raise _nao_autenticado()

    usuario = autenticacao.obter_usuario(sessao, usuario_id)
    if usuario is None:
        raise _nao_autenticado()

    return usuario


def exigir_papel(*papeis: PapelUsuario) -> Callable[..., Usuario]:
    """Fábrica de dependência: `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`.

    O papel conferido é o do **banco**, não o do token. O JWT carrega `papel`
    desde a Story 1.4 e lê-lo daqui seria uma consulta a menos — mas a sessão
    dura 8 horas (AD-15), e um papel corrigido no banco continuaria valendo o
    antigo por todo esse tempo. Além disso a consulta acontece de qualquer
    jeito: `usuario_atual` precisa do usuário inteiro.
    """
    # Calculado uma vez, no momento em que a rota é declarada — e não a cada
    # requisição. O conjunto é fixo; deixá-lo dentro de `verificar` esconderia
    # isso.
    permitidos = {papel.value for papel in papeis}

    def verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        # `usuario.papel` é `str` (coluna `String(20)`), então a comparação é
        # com `papel.value`. `PapelUsuario` herda de `str`, então o `==` até
        # funcionaria — mas `{PapelUsuario.CLIENTE}` e `{"CLIENTE"}` não são
        # conjuntos equivalentes para o `in`, e o bug seria silencioso.
        if usuario.papel not in permitidos:
            raise ErroDeDominio(
                "SEM_PERMISSAO",
                "Esta área é de outro papel. Entre com a conta certa.",
                status_http=403,
            )
        return usuario

    # `Depends(usuario_atual)` e não uma chamada direta: é o `Depends` que faz o
    # FastAPI resolver a autenticação primeiro, e é por isso que a falta de
    # sessão responde `401` e não `403`. Chamar `usuario_atual(...)` à mão aqui
    # obrigaria a repassar `Request` e `Session` e inverteria a ordem.
    return verificar


# ⚠️ **Uma instância só, guardada num nome** — e não `exigir_papel(PORTARIA)`
# escrito em cada lugar que precisa dela. `exigir_papel` é uma **fábrica**: cada
# chamada devolve uma função nova, e o cache de dependências do FastAPI é por
# objeto. Com duas instâncias na mesma rota — uma dentro do
# `exigir_porta_aberta` abaixo, outra na assinatura do handler que também
# precisa saber **quem** validou —, a checagem de papel rodaria duas vezes e as
# duas devolveriam objetos `Usuario` distintos da mesma linha. Com o nome, o
# FastAPI resolve uma vez e entrega o mesmo objeto aos dois.
PORTARIA_DA_SESSAO = exigir_papel(PapelUsuario.PORTARIA)


def exigir_porta_aberta(
    evento_id: UUID,
    portaria: Usuario = Depends(PORTARIA_DA_SESSAO),
    sessao: Session = Depends(obter_sessao),
) -> Evento:
    """O evento do caminho, se quem está na sessão pode atendê-lo agora (5.2).

    **As três recusas da portaria numa dependência só**, e é isso que a torna
    diferente do `exigir_papel`: papel diz o que a pessoa faz, esta diz **onde**
    e **quando**. As três respondem `403`:

    - sem vínculo na `evento_portaria` → `SEM_ESCALA_NO_EVENTO` (AD-7)
    - com vínculo, mas depois de `data_hora_fim` → `EVENTO_ENCERRADO`
    - com vínculo, mas antes de `data_hora - ABERTURA_DOS_PORTOES`
      → `EVENTO_NAO_ABERTO`

    ⚠️ **Evento inexistente responde a primeira**, e não `404`. Quem não está
    escalado não descobre se o evento existe — o `obter_escalado` colapsa os dois
    casos num `None` de propósito, e o docstring dele explica o porquê.

    ⚠️ **A ordem das três não é estética.** A escala vem primeiro: invertida,
    alguém sem escala nenhuma descobriria pelo código do erro se o show começa em
    breve. E `EVENTO_ENCERRADO` vem **antes** do `EVENTO_NAO_ABERTO` — na ordem
    inversa, um evento que já acabou responderia *"a porta ainda não abriu"*,
    porque as duas condições são simultaneamente verdadeiras para um evento futuro
    cujo término foi digitado errado.

    ⚠️ **`EVENTO_ENCERRADO` é uma recusa da dependência, e não um quinto veredito
    do `validar`** (techspec `docs/techspec-fim-do-evento.md`). Ele entra ao lado
    do `EVENTO_NAO_ABERTO` pelo mesmo motivo daquele: a recusa é sobre **o
    turno**, não sobre o ingresso — nada foi lido, nada foi julgado. *Descartei*
    um quinto veredito respondido `200` pelo `validar`: seria mais claro para quem
    está na fila, e custa o `CHECK` de `validacao.resultado`, o enum `Veredito`, o
    `RecusasDoTurno` de três campos, o contador do turno e um quinto símbolo SVG —
    contrariando de uma vez as duas decisões escritas *"sem quinto veredito"* (5.2)
    e *"duas tintas para quatro vereditos"* (5.4). O comportamento de tela sai
    pronto: a 5.3 já manda todo `403` do leitor redirecionar para `/portaria`, e
    lá a portaria lê a tag do turno encerrado.

    ⚠️ **É uma dependência, e não as primeiras linhas do handler** (AD-9). É
    isso que faz o `403` acontecer **antes de qualquer consulta ao ingresso** —
    o AC da Story 5.2 é literal nisso, e ele deixa de valer sem nenhum teste
    mudar de cor se alguém "melhorar" carregando o ingresso antes. O teste
    barato que pega o caso que importa é o que confirma que `usado_em` continua
    nulo depois do `403`.

    Devolve o `Evento` para o handler não reconsultar o que a dependência já
    leu: é o mesmo molde do `exigir_papel`, que devolve o `Usuario` em vez de só
    autorizar.
    """
    evento = servico_de_evento.obter_escalado(sessao, portaria, evento_id)

    if evento is None:
        raise ErroDeDominio(
            "SEM_ESCALA_NO_EVENTO",
            "Você não está escalado para este evento.",
            status_http=403,
        )

    # Lido **uma vez** e usado nas duas comparações, no molde do `atualizar` de
    # `services/evento.py`: duas leituras do relógio na mesma requisição podem
    # discordar sobre o show que termina agora, e aí as duas recusas responderiam
    # sobre instantes diferentes.
    agora = datetime.now(timezone.utc)

    if servico_de_evento.evento_encerrado(evento, agora):
        raise ErroDeDominio(
            "EVENTO_ENCERRADO",
            "Este evento já terminou.",
            status_http=403,
        )

    if not servico_de_evento.porta_aberta(evento, agora):
        raise ErroDeDominio(
            "EVENTO_NAO_ABERTO",
            "A porta deste evento ainda não abriu.",
            status_http=403,
        )

    return evento
