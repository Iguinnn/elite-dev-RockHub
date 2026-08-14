"""O seed de avaliação — precisa do Compose no ar.

**Nenhum teste daqui chama `main()`.** `main()` abre `SessaoLocal`, que aponta
para `DATABASE_URL` — o banco de **desenvolvimento**. Um teste que o chamasse
gravaria as contas fora do banco de teste, passaria verde, e ninguém
descobriria até estranhar contas repetidas em `rockhub`. Por isso `semear()`
recebe a `Session` por parâmetro: é o que permite exercitá-lo aqui dentro, na
transação revertida da fixture `sessao`. Mesma trava que a Story 1.3 pôs na
configuração do Alembic.

A maior parte destes testes afirma sobre o que o seed **não** faz. É o ponto da
story: este é o primeiro código do repositório escrito para rodar contra o banco
de produção, repetidamente, sem ninguém olhando.

⚠️ **Nenhuma contagem é literal.** Elas derivam de `CONTAS`, desde a Story 2.5:
a quinta conta semeada quebrou seis testes que tinham `4` escrito na mão, e
nenhum deles tinha qualquer relação com quantas contas existem. Acrescentar a
sexta agora não custa nada.
"""

from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.auth import LoginEntrada
from app.services.autenticacao import autenticar
from app.services.evento import listar_programacao
from seeds.semear import (
    CONTAS,
    CRIADA,
    CRIADO,
    EVENTO_NOME,
    MANTIDA,
    MANTIDO,
    ORIGEM_DO_SEED,
    PAPEL_DIVERGENTE,
    REAGENDADO,
    SEM_CONTAS,
    SENHA_DE_AVALIACAO,
    SETORES_SEMEADOS,
    ContaSemeada,
    proxima_sessao,
    semear,
    semear_evento,
)


def _contar_usuarios(sessao: Session) -> int:
    """Contagem absoluta, não relativa: a fixture reverte tudo no teardown,
    então a tabela começa vazia em cada teste."""
    return sessao.scalar(select(func.count()).select_from(Usuario)) or 0


def test_uma_execucao_cria_todas_as_contas_do_nfr2(sessao: Session) -> None:
    """Uma conta por entrada de `CONTAS`, com os papéis que `CONTAS` declara.

    A comparação é contra o próprio `CONTAS`, e não contra números escritos
    aqui: o que este teste prova é que o seed grava o que a lista diz — não que
    a lista tem um tamanho específico, que é decisão de produto e muda.
    """
    semear(sessao)

    papeis_gravados = Counter(sessao.scalars(select(Usuario.papel)).all())
    papeis_esperados = Counter(conta.papel.value for conta in CONTAS)

    assert _contar_usuarios(sessao) == len(CONTAS)
    assert papeis_gravados == papeis_esperados
    # A partir da Story 2.5 são **duas** portarias, e é isso que torna
    # demonstrável o AD-7: a portaria A não valida o evento da portaria B.
    assert papeis_esperados[PapelUsuario.PORTARIA.value] == 2


def test_primeira_execucao_devolve_criada_em_todas(sessao: Session) -> None:
    resultado = semear(sessao)

    assert [situacao for _, situacao in resultado] == [CRIADA] * len(CONTAS)


def test_segunda_execucao_nao_duplica_e_devolve_mantida(sessao: Session) -> None:
    semear(sessao)
    total_depois_da_primeira = _contar_usuarios(sessao)

    resultado = semear(sessao)

    assert [situacao for _, situacao in resultado] == [MANTIDA] * len(CONTAS)
    assert _contar_usuarios(sessao) == total_depois_da_primeira == len(CONTAS)


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
    # As semeadas mais a do avaliador, que continua lá.
    assert _contar_usuarios(sessao) == len(CONTAS) + 1


def test_senha_semeada_autentica_em_todas_as_contas(sessao: Session) -> None:
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


def _evento_semeado(sessao: Session) -> Evento:
    evento = sessao.scalar(
        select(Evento).where(Evento.origem_externa_id == ORIGEM_DO_SEED)
    )
    assert evento is not None
    return evento


def _contar_eventos(sessao: Session) -> int:
    return sessao.scalar(select(func.count()).select_from(Evento)) or 0


# ---------------------------------------------------------------------------
# O evento publicado do NFR2 — o enunciado pede "ao menos um evento publicado
# com ingressos disponíveis" junto das contas.
# ---------------------------------------------------------------------------


def test_evento_semeado_nasce_publicado_e_no_futuro(sessao: Session) -> None:
    """O requisito inteiro numa asserção: publicado, à venda e ainda por acontecer.

    Qualquer uma das três falhando torna o evento inútil para quem avalia — um
    rascunho não aparece na programação, um show passado também não, e um sem
    setor não vende ingresso nenhum.
    """
    semear(sessao)

    assert semear_evento(sessao) == CRIADO

    evento = _evento_semeado(sessao)
    assert evento.publicado_em is not None
    assert evento.data_hora > datetime.now(timezone.utc)
    assert evento.data_hora_fim > evento.data_hora
    assert {setor.nome for setor in evento.setores} == {
        setor.nome for setor in SETORES_SEMEADOS
    }
    # Sem isto o evento nasceria esgotado e o roteiro de avaliação travaria no
    # primeiro clique.
    assert all(setor.capacidade > setor.vendidos for setor in evento.setores)


def test_evento_semeado_aparece_na_programacao_publica(sessao: Session) -> None:
    """A prova que importa, e a única que o avaliador vê.

    As três colunas conferidas acima são meio caminho: o que decide se o
    requisito foi cumprido é o show estar na tela que abre sem conta nenhuma.
    """
    semear(sessao)
    semear_evento(sessao)

    nomes = [evento.nome for evento in listar_programacao(sessao)]

    assert EVENTO_NOME in nomes


def test_evento_semeado_tem_portaria_escalada(sessao: Session) -> None:
    """AD-7: evento sem ninguém escalado é evento cujo ingresso ninguém valida.

    `publicar` recusa isso com `EVENTO_SEM_PORTARIA` desde a Story 2.5, e o seed
    não passa pelo service — então a invariante precisa ser afirmada aqui, senão
    o único caminho que a contorna é justamente o que roda em produção.
    """
    semear(sessao)
    semear_evento(sessao)

    escalados = _evento_semeado(sessao).portarias

    assert escalados
    assert all(pessoa.papel == PapelUsuario.PORTARIA.value for pessoa in escalados)


def test_segunda_execucao_nao_duplica_o_evento(sessao: Session) -> None:
    semear(sessao)
    semear_evento(sessao)

    assert semear_evento(sessao) == MANTIDO
    assert _contar_eventos(sessao) == 1


def test_evento_que_ja_aconteceu_e_reagendado_para_o_futuro(sessao: Session) -> None:
    """A razão de o `UPDATE` existir neste arquivo.

    Sem o reagendamento, o "já existe? não insere" garantiria que o show sumisse
    da programação três dias depois do deploy e nunca mais voltasse — o
    requisito do enunciado vale no dia da avaliação, não no do deploy.
    """
    semear(sessao)
    semear_evento(sessao)
    evento = _evento_semeado(sessao)
    id_original = evento.id
    evento.data_hora = datetime.now(timezone.utc) - timedelta(days=2)
    evento.data_hora_fim = evento.data_hora + timedelta(hours=3)
    sessao.commit()

    assert semear_evento(sessao) == REAGENDADO

    reagendado = _evento_semeado(sessao)
    # O **mesmo** evento, não um segundo: reagendar é mover a data, e criar um
    # novo a cada semana encheria o banco de produção de shows fantasma.
    assert reagendado.id == id_original
    assert _contar_eventos(sessao) == 1
    assert reagendado.data_hora > datetime.now(timezone.utc)
    assert reagendado.data_hora_fim > reagendado.data_hora


def test_reagendar_nao_apaga_o_que_ja_foi_vendido(sessao: Session) -> None:
    """Reagendar mexe em duas colunas de data, e em nada mais.

    Quem já tinha ingresso continua com ele — e é isto que separa este `UPDATE`
    do `TRUNCATE` que o resto do arquivo existe para não fazer.
    """
    semear(sessao)
    semear_evento(sessao)
    evento = _evento_semeado(sessao)
    setor = evento.setores[0]
    setor.vendidos = 7
    evento.data_hora = datetime.now(timezone.utc) - timedelta(days=1)
    evento.data_hora_fim = evento.data_hora + timedelta(hours=3)
    sessao.commit()

    semear_evento(sessao)

    depois = _evento_semeado(sessao)
    assert {(s.nome, s.vendidos) for s in depois.setores} >= {(setor.nome, 7)}
    assert depois.nome == EVENTO_NOME


def test_evento_nao_e_gravado_sem_as_contas(sessao: Session) -> None:
    """Banco sem as contas: devolve aviso e não grava, em vez de estourar.

    Este comando roda entre o `alembic upgrade head` e o `uvicorn` no deploy da
    Railway (Story 1.8). Um `AttributeError` sobre `None` aqui derrubaria a
    subida inteira por causa de um dado de conveniência.
    """
    assert semear_evento(sessao) == SEM_CONTAS
    assert _contar_eventos(sessao) == 0


def test_data_do_show_cai_na_hora_cheia() -> None:
    """Show marcado para as 21h47 não parece dado semeado, parece defeito."""
    inicio, fim = proxima_sessao(datetime(2026, 8, 14, 21, 47, 33, tzinfo=timezone.utc))

    assert (inicio.minute, inicio.second, inicio.microsecond) == (0, 0, 0)
    assert fim > inicio


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
