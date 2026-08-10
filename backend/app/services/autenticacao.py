"""Autenticação por e-mail e senha: entrar e criar conta.

Nenhuma das duas funções sabe o que é cookie, HTTP ou token — devolvem o
`Usuario` ou levantam `ErroDeDominio`. Quem monta o token e grava o cookie é o
router (`app/api/auth.py`).

O par mostra a convenção de transação do `ARCHITECTURE-SPINE.md#Convenções`:
**service que lê não faz nada; service que escreve abre e fecha a transação.**
`autenticar()` só consulta, então não há `commit` nenhum nele. `cadastrar()`
grava, então o `commit` é dele — `obter_sessao()` não abre transação e o
router nunca confirma nada.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import ErroDeDominio
from app.core.seguranca import HASH_FANTASMA, conferir_senha, gerar_hash
from app.models.usuario import PapelUsuario, Usuario


def _credenciais_invalidas() -> ErroDeDominio:
    return ErroDeDominio(
        "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.", status_http=401
    )


def autenticar(sessao: Session, email: str, senha: str) -> Usuario:
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))

    if usuario is None:
        # Nivela o tempo de resposta com o caminho de usuário existente, para
        # a resposta não virar um oráculo de "esse e-mail está cadastrado?".
        conferir_senha(HASH_FANTASMA, senha)
        raise _credenciais_invalidas()

    if not conferir_senha(usuario.senha_hash, senha):
        raise _credenciais_invalidas()

    return usuario


def cadastrar(sessao: Session, nome: str, email: str, senha: str) -> Usuario:
    """Cria a conta e devolve o usuário gravado. Sempre com papel CLIENTE.

    O papel é literal na chamada, sem parâmetro e sem valor padrão que dê para
    sobrescrever: **o papel de uma conta nunca vem do corpo da requisição.**
    Organizador e portaria são criados por outro caminho (Stories 1.7 e 2.5).

    Não há `SELECT` conferindo o e-mail antes do `INSERT`, por dois motivos.
    Primeiro, seria uma corrida: entre a consulta e a gravação cabe outra
    requisição com o mesmo e-mail, e a segunda bateria no `UNIQUE` virando
    `500` justamente no caso que o `409` existe para cobrir. Segundo, criaria
    dois caminhos para a mesma regra — o `SELECT` seria a regra "de verdade" e
    o `UNIQUE` uma rede de proteção com outro comportamento. Aqui há um
    caminho só: tenta gravar, e a restrição da Story 1.3 é quem responde.
    """
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=gerar_hash(senha),
        papel=PapelUsuario.CLIENTE.value,
    )
    sessao.add(usuario)

    try:
        # `flush()` dentro do try e `commit()` fora: assim a exceção aparece na
        # linha que a provoca. Com o `commit()` aqui dentro, a distinção entre
        # "não gravou" e "gravou e falhou ao confirmar" se perderia.
        sessao.flush()
    except IntegrityError as erro:
        # Obrigatório: sem o rollback a `Session` fica em estado inválido e a
        # próxima operação levanta `PendingRollbackError`, que aponta para
        # longe da causa. O `from erro` mantém no traceback o que o banco
        # disse — um 409 sem rastro é o log que não ajuda ninguém.
        sessao.rollback()
        raise ErroDeDominio(
            "EMAIL_JA_CADASTRADO",
            "Esse e-mail já tem conta. Entre com ele ou use outro.",
            status_http=409,
        ) from erro

    sessao.commit()
    sessao.refresh(usuario)
    return usuario
