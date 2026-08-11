"""O seed de avaliação — precisa do Compose no ar.

**Nenhum teste daqui chama `main()`.** `main()` abre `SessaoLocal`, que aponta
para `DATABASE_URL` — o banco de **desenvolvimento**. Um teste que o chamasse
gravaria quatro contas fora do banco de teste, passaria verde, e ninguém
descobriria até estranhar contas repetidas em `rockhub`. Por isso `semear()`
recebe a `Session` por parâmetro: é o que permite exercitá-lo aqui dentro, na
transação revertida da fixture `sessao`. Mesma trava que a Story 1.3 pôs na
configuração do Alembic.

A maior parte destes testes afirma sobre o que o seed **não** faz. É o ponto da
story: este é o primeiro código do repositório escrito para rodar contra o banco
de produção, repetidamente, sem ninguém olhando.
"""

from collections.abc import Callable

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.usuario import PapelUsuario, Usuario
from app.schemas.auth import LoginEntrada
from app.services.autenticacao import autenticar
from seeds.semear import (
    CONTAS,
    CRIADA,
    MANTIDA,
    PAPEL_DIVERGENTE,
    SENHA_DE_AVALIACAO,
    ContaSemeada,
    semear,
)


def _contar_usuarios(sessao: Session) -> int:
    """Contagem absoluta, não relativa: a fixture reverte tudo no teardown,
    então a tabela começa vazia em cada teste."""
    return sessao.scalar(select(func.count()).select_from(Usuario)) or 0


def test_uma_execucao_cria_as_quatro_contas_do_nfr2(sessao: Session) -> None:
    semear(sessao)

    papeis = sessao.scalars(select(Usuario.papel)).all()

    assert _contar_usuarios(sessao) == 4
    assert papeis.count(PapelUsuario.ORGANIZADOR.value) == 1
    assert papeis.count(PapelUsuario.CLIENTE.value) == 2
    assert papeis.count(PapelUsuario.PORTARIA.value) == 1


def test_primeira_execucao_devolve_criada_nas_quatro(sessao: Session) -> None:
    resultado = semear(sessao)

    assert [situacao for _, situacao in resultado] == [CRIADA] * 4


def test_segunda_execucao_nao_duplica_e_devolve_mantida(sessao: Session) -> None:
    semear(sessao)
    total_depois_da_primeira = _contar_usuarios(sessao)

    resultado = semear(sessao)

    assert [situacao for _, situacao in resultado] == [MANTIDA] * 4
    assert _contar_usuarios(sessao) == total_depois_da_primeira == 4


def test_segunda_execucao_nao_levanta_excecao(sessao: Session) -> None:
    semear(sessao)

    # Sem `pytest.raises`: o que este teste prova é que rodar de novo é seguro.
    # Se o seed levantasse qualquer coisa, o deploy da Story 1.8 pararia antes
    # do `uvicorn` — o comando roda a cada redeploy, não uma vez só.
    semear(sessao)


def test_conta_preexistente_com_mesmo_email_nao_e_sobrescrita(
    sessao: Session, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """AC4: nome e `senha_hash` de quem já está no banco continuam intactos."""
    organizador = CONTAS[0]
    fabricar_usuario(organizador.papel, email=organizador.email)
    gravado = sessao.scalar(select(Usuario).where(Usuario.email == organizador.email))
    assert gravado is not None
    nome_antes, hash_antes = gravado.nome, gravado.senha_hash

    resultado = dict(semear(sessao))

    depois = sessao.scalar(select(Usuario).where(Usuario.email == organizador.email))
    assert depois is not None
    assert resultado[organizador] == MANTIDA
    assert depois.nome == nome_antes != organizador.nome
    assert depois.senha_hash == hash_antes


def test_conta_criada_por_avaliador_continua_no_banco_depois_do_seed(
    sessao: Session, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """AC3: o seed não apaga nada. É o motivo de esta story existir assim."""
    avaliador = fabricar_usuario(PapelUsuario.CLIENTE, email="avaliador@exemplo.com")
    id_do_avaliador = avaliador.id

    semear(sessao)

    assert sessao.get(Usuario, id_do_avaliador) is not None
    assert _contar_usuarios(sessao) == 5


def test_senha_semeada_autentica_nas_quatro_contas(sessao: Session) -> None:
    """AC5: prova que o `senha_hash` gravado é Argon2id de verdade.

    Um seed que grava conta que não loga é pior que seed nenhum — a falha
    apareceria no primeiro passo do roteiro de avaliação.
    """
    semear(sessao)

    for conta in CONTAS:
        usuario = autenticar(sessao, conta.email, SENHA_DE_AVALIACAO)
        assert usuario.email == conta.email
        assert usuario.papel == conta.papel.value


@pytest.mark.parametrize("conta", CONTAS, ids=lambda conta: conta.email)
def test_email_semeado_ja_esta_normalizado(conta: ContaSemeada) -> None:
    """AC6: comparado contra o que `EmailNormalizado` produziria.

    `POST /auth/login` normaliza a entrada antes de consultar. Um
    `Organizador@RockHub.dev` no script gravaria maiúscula no banco, e a conta
    existiria sem nunca conseguir entrar.
    """
    assert LoginEntrada(email=conta.email, senha="nao-usada").email == conta.email


def test_email_semeado_com_outro_papel_avisa_e_nao_altera_o_papel(
    sessao: Session, fabricar_usuario: Callable[..., Usuario]
) -> None:
    """AC7: alguém cadastrou `organizador@rockhub.dev` por `/cadastro`, e a
    conta nasceu `CLIENTE`. O seed não conserta — avisa."""
    organizador = CONTAS[0]
    fabricar_usuario(PapelUsuario.CLIENTE, email=organizador.email)

    resultado = dict(semear(sessao))

    gravado = sessao.scalar(select(Usuario).where(Usuario.email == organizador.email))
    assert gravado is not None
    assert resultado[organizador] == PAPEL_DIVERGENTE
    assert gravado.papel == PapelUsuario.CLIENTE.value
