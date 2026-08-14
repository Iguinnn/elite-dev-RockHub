"""Semeia os dados de avaliação (NFR2): **seis contas** — dois organizadores,
dois clientes e duas portarias — e **um evento publicado com ingressos à venda**.

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
esse e-mail? então não insere" — não há `DELETE`, `TRUNCATE` nem `drop` em lugar
nenhum deste arquivo, e não deve haver. A Story 1.8 chama este comando a cada
deploy na Railway: um seed que limpasse a tabela antes de inserir funcionaria
hoje e destruiria, no primeiro redeploy, o trabalho de quem estivesse avaliando.

⚠️ **Existe exatamente um `UPDATE` neste arquivo, e ele é o reagendamento do
evento semeado** — `semear_evento` lá embaixo, duas colunas de data, uma linha.
Ele é a exceção consciente à regra do parágrafo acima, e o motivo é que evento
semeado com data fixa não sobrevive à própria idempotência: as rotas públicas
cortam em `data_hora`, então três dias depois do primeiro deploy o show sumiria
da programação, e o "já existe? não insere" garantiria que ele nunca voltasse. O
requisito do enunciado — *"ao menos um evento publicado com ingressos
disponíveis"* — vale no dia da avaliação, não no dia do deploy. *Descartei* data
fixa distante (31/12/2026): nunca envelheceria, e o portão da portaria nunca
abriria nela durante a avaliação, deixando o evento semeado servindo para comprar
e nunca para validar.

O `UPDATE` não toca em mais nada: `vendidos`, preço, setores e os ingressos já
emitidos ficam de pé. Reagendar um show é o que uma casa de espetáculo faz — e
quem já tinha ingresso continua com ele.

Este módulo é o único lugar do backend que grava conta com papel diferente de
`CLIENTE` — `cadastrar()` fixa o papel em literal, de propósito, e nenhuma rota
oferece o outro caminho.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessaoLocal
from app.core.seguranca import gerar_hash
from app.models.evento import Evento, Setor
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


@dataclass(frozen=True)
class SetorSemeado:
    nome: str
    capacidade: int
    preco_centavos: int


# **A marca do evento semeado**, e o jeito de reconhecê-lo em execuções
# seguintes. Vai em `origem_externa_id` porque é a única coluna do `Evento` que
# fala de procedência — e o valor diz a verdade: este show **não** veio da
# Discovery. *Descartei* casar pelo `nome`, que é campo de tela e mudaria a
# identidade do evento no dia em que eu trocasse o nome da banda.
#
# ⚠️ **O seed não chama a Ticketmaster, e isso é decisão.** A `TICKETMASTER_API_KEY`
# é opcional em desenvolvimento justamente para ninguém precisar de conta no
# portal para avaliar; um seed que dependesse dela falharia no `docker compose up`
# de quem clonou o repositório, que é exatamente o cenário que este arquivo
# existe para cobrir. O AD-1 continua valendo para tudo que nasce pela interface
# — o organizador não digita nome nem imagem em lugar nenhum.
ORIGEM_DO_SEED = "rockhub-seed"

# Nome fictício, e de propósito: com o seed fora do catálogo, um nome de banda
# real sugeriria um registro da Discovery que não existe. Trocar é uma linha.
EVENTO_NOME = "Câmara Escura"
EVENTO_LOCAL = "Audio Club"
EVENTO_CIDADE = "São Paulo"

# Sem `imagem_url`: a capa da raiz cai na arte de reserva quando ela é nula
# (`ARTE_DE_RESERVA`, em `(site)/page.tsx`), e colar aqui uma URL do CDN da
# Ticketmaster criaria uma dependência externa que quebra em silêncio — imagem
# some, e o único sintoma é um buraco na tela mais visitada do produto.

# Três dias à frente é o número que resolve as duas pontas: longe o bastante para
# o show não ficar dentro da janela de duas horas do portão logo depois de
# semeado (a portaria da avaliação abre no evento que o próprio avaliador
# publica, não neste), e perto o bastante para ele aparecer no filtro *Esta
# semana* da programação.
DIAS_ATE_O_SHOW = timedelta(days=3)
DURACAO_DO_SHOW = timedelta(hours=3)

SETORES_SEMEADOS: tuple[SetorSemeado, ...] = (
    SetorSemeado("Pista", 800, 12_000),
    # O segundo setor não é enfeite: é ele que torna verificável o AD-12 (preço e
    # capacidade pertencem ao setor, nunca ao evento) e o "a partir de R$ 120,00"
    # da programação, que só significa alguma coisa com dois preços diferentes.
    SetorSemeado("Mezanino", 200, 22_000),
)

CRIADO = "criado"
MANTIDO = "mantido"
REAGENDADO = "reagendado"
SEM_CONTAS = "sem-contas"


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


def proxima_sessao(agora: datetime) -> tuple[datetime, datetime]:
    """A data do show a partir de `agora` — início e término, sempre no futuro.

    **Truncada na hora cheia.** Um show marcado para as 21h47 porque foi essa a
    hora em que alguém rodou o comando não parece dado semeado, parece defeito —
    e a tela do organizador mostra o horário com todas as letras.

    `agora` é parâmetro pelo mesmo motivo de `porta_aberta` em
    `services/evento.py`: quem chama já leu o relógio, e é o que torna a janela
    testável sem congelar o relógio do processo.
    """
    inicio = (agora + DIAS_ATE_O_SHOW).replace(minute=0, second=0, microsecond=0)
    return inicio, inicio + DURACAO_DO_SHOW


def semear_evento(sessao: Session, agora: datetime | None = None) -> str:
    """Cria o evento publicado do NFR2, ou o reagenda se ele já aconteceu.

    **Depende de `semear()` ter rodado antes**: o evento precisa de um
    organizador dono e de gente escalada na porta, e as duas coisas são contas.
    Se elas não estiverem lá, este devolve `SEM_CONTAS` e não grava nada — em vez
    de estourar `AttributeError` no meio de um deploy, que é o que um
    `organizador.id` sobre `None` faria.

    ⚠️ **Não passa por `services/evento.publicar`, e a escolha custa uma coisa.**
    O service recebe `EventoEntrada` e um `Usuario` da sessão HTTP, e valida seis
    recusas que aqui não têm como acontecer — os dados são constantes deste
    arquivo. O que se perde é a garantia de que seed e rota concordam; o que se
    ganha é não ter um script de linha de comando montando schema de requisição
    para satisfazer uma assinatura. Se as invariantes de publicação crescerem,
    esta função é o segundo lugar a olhar.
    """
    agora = agora or datetime.now(timezone.utc)

    organizador = sessao.scalar(
        select(Usuario).where(Usuario.email == CONTAS[0].email)
    )
    portarias = list(
        sessao.scalars(
            select(Usuario).where(
                Usuario.papel == PapelUsuario.PORTARIA.value
            )
        )
    )
    if organizador is None or not portarias:
        return SEM_CONTAS

    existente = sessao.scalar(
        select(Evento).where(Evento.origem_externa_id == ORIGEM_DO_SEED)
    )

    if existente is not None:
        if existente.data_hora > agora:
            # Nada é escrito. É o mesmo `return` que `semear_conta` usa, e pelo
            # mesmo motivo: o caso comum de um seed que roda a cada deploy é não
            # ter nada a fazer.
            return MANTIDO

        # O único `UPDATE` do arquivo. **As duas colunas juntas, num `commit`
        # só**: o CHECK `fim_depois_do_inicio` é conferido por statement, e
        # gravar só o início deixaria a linha com término anterior ao começo.
        existente.data_hora, existente.data_hora_fim = proxima_sessao(agora)
        sessao.commit()
        return REAGENDADO

    inicio, fim = proxima_sessao(agora)
    sessao.add(
        Evento(
            organizador_id=organizador.id,
            nome=EVENTO_NOME,
            data_hora=inicio,
            data_hora_fim=fim,
            local=EVENTO_LOCAL,
            cidade=EVENTO_CIDADE,
            origem_externa_id=ORIGEM_DO_SEED,
            # Publicado no ato: rascunho semeado não apareceria na programação, e
            # o requisito do enunciado fala de evento **publicado**.
            publicado_em=agora,
            # ⚠️ `vendidos` não é passado, aqui como em `publicar`: quem responde
            # por ele é o `server_default=text("0")` da Story 2.3.
            setores=[
                Setor(
                    nome=setor.nome,
                    capacidade=setor.capacidade,
                    preco_centavos=setor.preco_centavos,
                )
                for setor in SETORES_SEMEADOS
            ],
            # **As duas portarias, e não só o Jonas.** Com uma conta escalada, a
            # metade das pessoas que entrasse pela outra veria uma lista de
            # turnos vazia e concluiria que a tela da portaria está quebrada. O
            # recorte do AD-7 continua demonstrável no evento que o próprio
            # avaliador publica, escalando um só — que é onde o roteiro do README
            # manda olhar.
            portarias=portarias,
        )
    )
    sessao.commit()
    return CRIADO


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

        # Depois das contas, sempre: o evento precisa do organizador e da
        # portaria já gravados. A ordem é a dependência, não preferência.
        situacao_do_evento = semear_evento(sessao)
        print(f"{'EVENTO':<12} {EVENTO_NOME:<25} {situacao_do_evento}")

    # A senha não é impressa. Ela está num README público, então não é segredo —
    # mas o mesmo comando roda no deploy da Railway, e o que ele imprime vai
    # para o log. Credencial em log é hábito que se leva junto para o dia em que
    # a credencial importa. E quem rodou o comando tem o README aberto.
    print('As senhas estão no README da raiz, em "Contas semeadas".')


if __name__ == "__main__":
    main()
