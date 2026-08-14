"""Semeia as cinco contas de avaliação (NFR2): um organizador, dois clientes e
**duas** portarias.

A segunda portaria entrou na Story 2.5. O NFR2 pede uma, e uma bastaria para
entrar no sistema — mas com uma só a tela de escalação vira um item único que
não se pode não marcar, e o cenário que o AD-7 existe para provar (a portaria A
não valida o evento da portaria B) dependeria de o avaliador criar uma conta na
mão. Conta de portaria **não se cria pela interface**, de propósito: sem a
segunda semeada, o cenário simplesmente não é demonstrável.

```bash
cd backend
uv run python -m seeds.semear
```

⚠️ **Com o `-m`, sempre.** `uv run seeds/semear.py` põe `backend/seeds/` no
`sys.path` em vez de `backend/`, e `import app.core.db` estoura
`ModuleNotFoundError: app`. A correção é o `-m` — nunca um `sys.path.append`
aqui em cima. E rode a partir de `backend/`: a `Settings` lê o `.env` do
diretório corrente, então da raiz do repositório o script pegaria os valores
padrão em vez do seu.

**Rodar de novo é seguro, e isso é o ponto.** A idempotência vem de "já existe
esse e-mail? então não insere" — não há `DELETE`, `TRUNCATE`, `UPDATE` nem
`drop` em lugar nenhum deste arquivo, e não deve haver. A Story 1.8 chama este
comando a cada deploy na Railway: um seed que limpasse a tabela antes de
inserir funcionaria hoje e destruiria, no primeiro redeploy, o trabalho de quem
estivesse avaliando.

Este módulo é o único lugar do backend que grava conta com papel diferente de
`CLIENTE` — `cadastrar()` fixa o papel em literal, de propósito, e nenhuma rota
oferece o outro caminho.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessaoLocal
from app.core.seguranca import gerar_hash
from app.models.usuario import PapelUsuario, Usuario


@dataclass(frozen=True)
class ContaSemeada:
    nome: str
    email: str
    senha: str
    papel: PapelUsuario


# Uma senha só para todas. Elas são dado de avaliação publicado no README,
# não credencial de produção — e o README precisa conseguir listá-las numa
# tabela que ninguém copia errado.
SENHA_DE_AVALIACAO = "rockhub123"

# Contas fixas, nunca geradas. Um `faker` aqui produziria credencial que o
# README não conhece, que é o pior desfecho possível para um seed de avaliação.
CONTAS: tuple[ContaSemeada, ...] = (
    ContaSemeada("Helena Marques", "organizador@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.ORGANIZADOR),
    # O segundo organizador, pelo mesmo motivo da segunda portaria logo abaixo:
    # com uma conta só, "o organizador vê apenas os eventos dele" é uma frase
    # que ninguém consegue conferir. Com duas, publicar por uma e abrir
    # `Meus eventos` pela outra demonstra o recorte da Story 2.6 em dois cliques
    # — e mostra que um evento publicado por qualquer organizador aparece igual
    # na programação pública, que é o outro lado da mesma pergunta.
    ContaSemeada("Rafael Nunes", "organizador2@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.ORGANIZADOR),
    ContaSemeada("Bruno Tavares", "cliente@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.CLIENTE),
    ContaSemeada("Marina Aoki", "cliente2@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.CLIENTE),
    ContaSemeada("Jonas Ribeiro", "portaria@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.PORTARIA),
    # A segunda portaria (Story 2.5): é ela que faz a escalação ser uma escolha
    # e não um item obrigatório, e é ela que dá o cenário do AD-7 —
    # escalar só o Jonas e tentar validar com a Ana.
    ContaSemeada("Ana Sampaio", "portaria2@rockhub.dev",
                 SENHA_DE_AVALIACAO, PapelUsuario.PORTARIA),
)

CRIADA = "criada"
MANTIDA = "mantida"
PAPEL_DIVERGENTE = "papel-divergente"


def semear_conta(sessao: Session, conta: ContaSemeada) -> str:
    """Cria a conta se o e-mail ainda não existir. Nunca atualiza o que existe.

    O `SELECT` antes do `INSERT` é exatamente o que `cadastrar()` recusou na
    Story 1.5 — e aqui está certo. Lá era endpoint concorrente, e a janela entre
    consulta e gravação virava `500` no caso que o `409` existia para cobrir.
    Aqui é script de uma execução: o `except IntegrityError` cobre a corrida
    improvável, e a consulta é o que permite distinguir "criada" de "mantida",
    que é a informação que quem roda o comando precisa ver.
    """
    existente = sessao.scalar(select(Usuario).where(Usuario.email == conta.email))
    if existente is not None:
        # Nada é escrito aqui — nem nome, nem senha, nem papel. Este `return`
        # é a garantia inteira de que o seed não sobrescreve ninguém.
        return MANTIDA if existente.papel == conta.papel.value else PAPEL_DIVERGENTE

    sessao.add(
        Usuario(
            nome=conta.nome,
            email=conta.email,
            # Nunca um hash colado: os parâmetros do Argon2id viajam dentro da
            # própria string, e um hash de outra máquina pode não verificar —
            # falhando só na hora do login.
            senha_hash=gerar_hash(conta.senha),
            # `str`, nunca o membro do enum: a coluna é `String(20)` com CHECK.
            papel=conta.papel.value,
        )
    )
    try:
        # `commit` por conta, não um no fim: uma falha na terceira não desfaz as
        # duas primeiras, e o `rollback` abaixo tem escopo de uma conta só.
        sessao.commit()
    except IntegrityError:
        # Duas execuções ao mesmo tempo: o UNIQUE da Story 1.3 decide, e a
        # segunda entende que a conta já está lá. Sem o rollback a Session fica
        # inválida e a conta seguinte falharia por `PendingRollbackError`.
        sessao.rollback()
        return MANTIDA

    return CRIADA


def semear(sessao: Session) -> list[tuple[ContaSemeada, str]]:
    """Recebe a `Session` de propósito: só o `main()` escolhe o banco.

    É o que permite ao teste rodar o seed dentro da transação revertida do
    `conftest.py`. Se esta função abrisse `SessaoLocal` por conta própria, todo
    teste gravaria no banco de desenvolvimento — a mesma armadilha que a Story
    1.3 fechou definindo a URL do Alembic em código.
    """
    return [(conta, semear_conta(sessao, conta)) for conta in CONTAS]


def _linha_do_relatorio(sessao: Session, conta: ContaSemeada, situacao: str) -> str:
    if situacao == PAPEL_DIVERGENTE:
        # Calar aqui viraria "o organizador não funciona" sem pista nenhuma:
        # o e-mail existe, mas com outro papel, e a conta não faz o que o README
        # promete. O aviso não vira erro — ver `main()`.
        papel_gravado = sessao.scalar(
            select(Usuario.papel).where(Usuario.email == conta.email)
        )
        situacao = f"já existe com papel {papel_gravado} — não foi alterada"
    return f"{conta.papel.value:<12} {conta.email:<25} {situacao}"


def main() -> None:
    """Único lugar do arquivo que toca `SessaoLocal`, ou seja, o banco real.

    Sai sempre em `0`, inclusive com aviso de papel divergente. Na Story 1.8
    este comando roda entre o `alembic upgrade head` e o `uvicorn`: um
    `exit(1)` por causa de um aviso derrubaria o deploy inteiro, e a única saída
    seria mexer no banco de produção às pressas. Falha de verdade — banco fora
    do ar, migração não aplicada — continua estourando exceção e saindo
    diferente de zero, que aí é o comportamento certo.
    """
    with SessaoLocal() as sessao:
        for conta, situacao in semear(sessao):
            print(_linha_do_relatorio(sessao, conta, situacao))

    # A senha não é impressa. Ela está num README público, então não é segredo —
    # mas o mesmo comando roda no deploy da Railway, e o que ele imprime vai
    # para o log. Credencial em log é hábito que se leva junto para o dia em que
    # a credencial importa. E quem rodou o comando tem o README aberto.
    print('As senhas estão no README da raiz, em "Contas semeadas".')


if __name__ == "__main__":
    main()
