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
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.db import obter_sessao
from app.core.erros import ErroDeDominio
from app.core.seguranca import ler_token_sessao
from app.models.usuario import PapelUsuario, Usuario
from app.services import autenticacao


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
