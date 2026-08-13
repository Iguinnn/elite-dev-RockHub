"""Publicação de eventos: a regra de negócio e a transação que a grava.

Segue a convenção de transação do `ARCHITECTURE-SPINE.md#Convenções`, a mesma
do `services/autenticacao.py`: **service que escreve abre e fecha a
transação.** O `commit` é daqui; `obter_sessao()` não abre transação nenhuma e
o router (`app/api/organizador.py`) nunca confirma nada — ele chama esta função
e devolve o resultado.

Este módulo é o **outro lado** da exceção documentada no router do
organizador. Lá, a busca no catálogo chama a integração direto porque não sobra
regra de negócio para um service fazer. Aqui sobra: existem duas invariantes
que o banco sozinho não sabe recusar de forma legível, e existe uma transação
que precisa gravar evento e setores juntos ou nada.

**A ordem das cinco recusas é a garantia do "nenhum evento órfão".** Elas
acontecem antes de qualquer `add`: se a lista está vazia, tem nomes repetidos,
não traz portaria nenhuma, traz um id que não resolve ou a data já passou, nada
chega a existir no banco — nem o evento, nem o primeiro setor antes de o segundo
estourar.

```
1. setores vazio          → EVENTO_SEM_SETOR
2. nome de setor repetido → SETOR_DUPLICADO
3. portaria_ids vazio     → EVENTO_SEM_PORTARIA
4. id que não resolve     → PORTARIA_INVALIDA
5. data_hora no passado   → EVENTO_NO_PASSADO
   ── só então: monta o Evento e grava ──
```

**Setor antes de portaria não é estética.** A Story 2.5 acrescentou as duas
últimas a uma rota que a 2.4 já tinha entregado, e os testes de recusa daquela
story mandam corpo sem `portaria_ids` porque o campo ainda não existia.
Conferir setor primeiro é o que os mantém provando o que se propuseram a
provar, sem reescrita.

**Não há `try/except IntegrityError` aqui**, ao contrário do `cadastrar()`. Lá
o `UNIQUE` do e-mail é a regra, e conferir antes seria uma corrida. Aqui as
duas violações que vêm do corpo (`uq_setor_evento_id_nome` e os `CHECK` do
setor) chegam do mesmo corpo de requisição, num único instante, sem ninguém
concorrendo — dá para conferi-las na memória, com certeza, antes de gravar. Um
`except` genérico neste ponto só serviria para transformar bug de verdade em
`422` bonito.

⚠️ **A justificativa acima tem um limite, apontado no code review da Epic 2 e
adiado de propósito** (`deferred-work.md`): existe uma terceira violação
possível, e ela **não** vem do corpo — a FK `evento_portaria.usuario_id`, que
aponta para outra linha, de outro dono. O `SELECT` das contas escaladas não
trava nada, então uma conta apagada entre ele e o `COMMIT` daria
`IntegrityError` → `500`. A janela é teórica enquanto não existir rota de
apagar usuário; quem escrever essa rota precisa voltar aqui.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroDeDominio
from app.models.evento import Evento, Setor, evento_portaria
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.evento import (
    DisponibilidadeDoSetor,
    EventoEmDestaque,
    EventoEntrada,
    EventoNaProgramacao,
    EventoPublico,
    EventoResumo,
    PeriodoDaProgramacao,
    SetorPublico,
    TurnoDaPortaria,
    TurnoDoLeitor,
)

# ⚠️ **A seta aponta só para este lado, e é o que impede o ciclo.**
# `services/ingresso.py` importa `models` e `schemas`, nunca este módulo — se um
# dia precisar de algo daqui, o que se move é a função, não a direção do import.
# Ele entrou na Story 5.6 para o `entradas` do turno: contar quem passou pela
# porta é assunto do ingresso, e projetar o turno é assunto do evento.
from app.services import ingresso as servico_de_ingresso

# Quantos ingressos uma pessoa leva numa compra só (Story 3.4, decisão do Igor).
#
# **Teto fixo, e não `min(disponivel, 6)`**: é o que dá ao stepper um limite sem
# que o contrato revele quanto resta em estoque (UX-DR7). Quem recusa o pedido
# maior do que existe é o `UPDATE` condicional do AD-3, na Story 3.6 — e ele
# recusa por concorrência, que é a garantia que o desafio mais pontua.
#
# **Seis não vem de regra de negócio nenhuma** — não existe uma neste produto, e
# Sympla e Eventim usam entre 4 e 10. Ele está aqui, numa constante e no
# contrato, porque é o único jeito de a tela e a futura rota de reserva não
# discordarem sobre qual é o teto: trocá-lo é uma linha e um teste.
MAXIMO_POR_COMPRA = 6

# Teto de linhas da programação pública (code review da Epic 3, decisão do Igor).
#
# **A rota não tinha teto nenhum**, e ela é a da tela mais visitada do produto:
# `GET /eventos` sem filtro devolvia todo evento publicado e futuro, com o
# `selectinload` trazendo os setores de todos eles. O docstring de
# `listar_programacao` descarta filtrar no cliente porque "a programação inteira
# atravessaria a rede a cada visita" — que era exatamente o que a rota fazia no
# estado inicial da raiz, sem filtro nenhum.
#
# **Teto fixo, e não paginação** (alternativa descartada): `?pagina=`/`?limite=`
# seria rota, schema, tela e testes para um contrato que nenhuma tela consome
# hoje, com três dias de prazo. Duzentos shows futuros é muito acima de qualquer
# catálogo que este projeto vá ver, e o corte é no fim da lista — a fila já sai
# ordenada por data, então o que cai fora é o mais distante.
#
# ⚠️ Quando este número apertar, o conserto **não** é aumentá-lo: é a paginação
# que ficou de fora aqui.
TETO_DA_PROGRAMACAO = 200

# Quanto antes do show a porta do evento abre (Story 5.2, techspec
# `docs/techspec-validacao-na-porta.md`).
#
# **Nasceu na tela, na Story 5.1, e desceu para cá.** Lá ela era conveniência
# operacional: a lista de turnos comparava `data_hora` com o relógio do
# navegador e só então liberava o link. A 5.2 mostrou que isso não bastava —
# uma chamada à rota de validação três dias antes do show grava `usado_em`, e na
# noite do evento aquela pessoa é barrada com `JA_UTILIZADO` sem nunca ter
# entrado. A tela impedia; a rota não, e credencial de portaria mais um `curl`
# bastavam.
#
# **Constante do service, no precedente do `MAXIMO_POR_COMPRA` logo acima**, e
# num lugar só: com a regra valendo nos dois lados, duas constantes de duas
# horas em duas camadas discordariam algum dia, e a tela mostraria a porta
# aberta enquanto a API recusa. A tela lê `TurnoDaPortaria.aberto`, que sai
# daqui.
#
# **Duas horas, e não o instante exato do show.** Um portão em `data_hora` trava
# o roteiro de avaliação da Story 6.4: `publicar` recusa data no passado, e as
# rotas públicas escondem o evento a partir de `data_hora` — quem avalia teria
# de publicar um show, comprar, **esperar o relógio virar** e só então validar.
# Com a janela, publicar para daqui a uma hora deixa a porta aberta na hora. E é
# o comportamento certo do mundo real: a portaria chega antes do primeiro
# acorde, nunca junto com ele.
#
# ⚠️ **Não há fechamento**, de propósito. Depois que abre, a porta fica aberta:
# o show acaba e ainda há gente entrando, e um teto pela duração faria a
# validação parar de funcionar no meio do turno — sem contar que este projeto
# não tem coluna de duração nenhuma.
ABERTURA_DOS_PORTOES = timedelta(hours=2)


def publicar(sessao: Session, organizador: Usuario, dados: EventoEntrada) -> Evento:
    """Grava o evento e seus setores na mesma transação, já publicado.

    `organizador` vem da dependência de papel, ou seja, **da sessão**. Não há
    parâmetro por onde um `organizador_id` do corpo pudesse entrar: publicar
    em nome de outra pessoa não é uma chamada malformada que o service recusa,
    é uma chamada que não existe.
    """
    if not dados.setores:
        raise ErroDeDominio(
            "EVENTO_SEM_SETOR",
            "Um evento precisa de ao menos um setor à venda.",
            status_http=422,
        )

    # `casefold()` e não `lower()`: é a normalização certa para comparação
    # insensível a caixa fora do ASCII (o clássico é o "ß" alemão, que vira
    # "ss"). Um organizador que digita "Pista" e " pista " quis dizer a mesma
    # coisa duas vezes, e o `uq_setor_evento_id_nome` da Story 2.3 recusaria os
    # dois — só que com um `500`, porque `IntegrityError` no `commit` sobe até
    # o handler genérico. Erro de digitação virando "erro interno do servidor"
    # é a pior resposta possível para quem só quer corrigir uma linha.
    vistos: set[str] = set()
    for setor in dados.setores:
        chave = setor.nome.casefold()
        if chave in vistos:
            raise ErroDeDominio(
                "SETOR_DUPLICADO",
                f'Há mais de um setor chamado "{setor.nome}". '
                "Cada setor precisa de um nome diferente.",
                status_http=422,
            )
        vistos.add(chave)

    # AD-7: um evento sem ninguém escalado é um evento cujo ingresso ninguém
    # pode validar na porta. A regra vale para ausência e para lista vazia — o
    # schema manda as duas para cá justamente por isso.
    if not dados.portaria_ids:
        raise ErroDeDominio(
            "EVENTO_SEM_PORTARIA",
            "Escale ao menos um usuário de portaria para validar os ingressos "
            "deste evento.",
            status_http=422,
        )

    # Silenciosamente, e ao contrário do `SETOR_DUPLICADO` logo acima. Dois
    # setores com o mesmo nome são duas intenções em conflito — qual das duas
    # capacidades vale? A mesma pessoa marcada duas vezes é uma intenção só, e
    # recusá-la seria pedir que alguém corrigisse um formulário que já dizia o
    # que queria dizer. `dict.fromkeys` preserva a ordem do corpo; `set`
    # tornaria a escala não determinística entre execuções.
    ids_pedidos = list(dict.fromkeys(dados.portaria_ids))

    # Uma consulta só, e um erro só para os dois casos possíveis: o id não
    # existe, ou existe e não é portaria. Distinguir seria transformar esta
    # rota num oráculo — "esse UUID já foi conta um dia?" — e é a mesma
    # disciplina do login da Story 1.4, que não diz se o e-mail existe.
    escalados = list(
        sessao.scalars(
            select(Usuario).where(
                Usuario.id.in_(ids_pedidos),
                Usuario.papel == PapelUsuario.PORTARIA.value,
            )
        )
    )

    if len(escalados) != len(ids_pedidos):
        raise ErroDeDominio(
            "PORTARIA_INVALIDA",
            "Alguma das contas escaladas não existe ou não é de portaria.",
            status_http=422,
        )

    # Quinta recusa, decidida no code review da Epic 2. Publicar show que já
    # aconteceu não é um caso de uso — é erro de digitação na data, e ele é
    # **permanente**, porque não existe tela de editar nem de apagar evento. Na
    # Epic 3 esse evento entraria na programação e venderia ingresso para uma
    # noite que já passou.
    #
    # **Por último, e não primeiro.** A ordem das recusas anteriores é o que
    # mantém os testes das Stories 2.4 e 2.5 provando o que se propuseram a
    # provar (ver o topo deste módulo); entrar antes delas mudaria o código de
    # erro de casos que já estão cobertos, sem nenhum ganho.
    if dados.data_hora <= datetime.now(timezone.utc):
        raise ErroDeDominio(
            "EVENTO_NO_PASSADO",
            "A data do show já passou. Confira o dia e o horário.",
            status_http=422,
        )

    evento = Evento(
        # Da sessão, sempre. É a diferença entre "quem publicou" e "quem o
        # corpo da requisição disse que publicou".
        organizador_id=organizador.id,
        # AD-1: o catálogo é **copiado** no ato da publicação, não referenciado.
        # Daqui em diante o evento vive no banco e a Ticketmaster pode sair do
        # ar, mudar o registro ou apagá-lo sem afetar quem já comprou ingresso.
        nome=dados.nome,
        imagem_url=dados.imagem_url,
        origem_externa_id=dados.origem_externa_id,
        data_hora=dados.data_hora,
        local=dados.local,
        cidade=dados.cidade,
        # Publicar é o ato desta rota, não um passo posterior: o carimbo nasce
        # aqui. `NULL` (rascunho) continua sendo um estado possível no banco,
        # sem nenhuma tela que o produza — é o que torna verificável o AC da
        # Story 3.1, "evento não publicado não aparece na programação".
        publicado_em=datetime.now(timezone.utc),
        # Os filhos vão dentro do `relationship`: o `cascade="all,
        # delete-orphan"` da Story 2.3 grava os dois na mesma transação, sem
        # `add` separado e sem `flush` intermediário para descobrir o id do pai.
        #
        # ⚠️ `vendidos` **não** é passado. O `server_default=text("0")` da
        # Story 2.3 é quem responde por ele. Escrever `vendidos=0` aqui
        # funcionaria hoje e criaria uma segunda fonte para o mesmo valor —
        # alguém teria que decidir qual é a certa no dia em que divergirem.
        setores=[
            Setor(
                nome=setor.nome,
                capacidade=setor.capacidade,
                preco_centavos=setor.preco_centavos,
            )
            for setor in dados.setores
        ],
        # Pelo `relationship`, como os setores — o SQLAlchemy grava as linhas
        # de `evento_portaria` na mesma transação, depois de conhecer o id do
        # evento. Nada de `INSERT` manual na tabela de associação: seria um
        # segundo caminho para o mesmo fato, e o dia em que os dois
        # divergissem ninguém saberia qual estava certo.
        portarias=escalados,
    )

    sessao.add(evento)
    sessao.commit()
    sessao.refresh(evento)
    return evento


def listar_portarias(sessao: Session) -> list[Usuario]:
    """Todas as contas de papel `PORTARIA`, por nome — quem pode ser escalado.

    **Mora neste service, e não em `services/autenticacao.py`.** Ela consulta
    `Usuario`, que é o assunto de lá, mas não é uma pergunta sobre
    autenticação: é "quem eu posso pôr na porta deste evento", e existe para a
    publicação. Em `autenticacao.py` ela ficaria cercada de login, cadastro e
    hash de senha, sem nenhuma relação com o motivo de existir — e o próximo
    leitor procuraria a regra da escala em dois arquivos.

    Sem paginação e sem filtro por termo: o filtro por nome acontece na tela,
    em memória, porque a lista inteira já viaja e responder a cada tecla sem
    ida à rede é melhor do que qualquer `?q=` faria com este volume.
    """
    return list(
        sessao.scalars(
            select(Usuario)
            .where(Usuario.papel == PapelUsuario.PORTARIA.value)
            .order_by(Usuario.nome)
        )
    )


def listar_escalados(sessao: Session, portaria: Usuario) -> list[TurnoDaPortaria]:
    """Os eventos em que a conta da sessão foi escalada na porta (Story 5.1).

    **O outro lado do `listar_portarias`, e por isso a vizinha dele**: aquela
    responde "quem eu posso pôr na porta deste evento", esta responde "em que
    portas eu trabalho". As duas leem a `evento_portaria` do AD-7, cada uma por
    uma das colunas.

    **Ela não corta por tempo, e é a decisão mais importante desta função.** As
    quatro rotas públicas filtram `data_hora >= agora`, e copiar esse corte aqui
    seria o pior erro possível: **a portaria trabalha exatamente do outro lado
    dele**. Às 21h30 de um show que começou às 21h o evento já sumiu de
    `listar_programacao` — se o turno sumisse junto, ele desapareceria da mão de
    quem está na porta no minuto em que a fila começa a andar. O argumento é o
    mesmo que deixou `listar_do_organizador` sem filtro: isto é o inventário de
    quem lê, não a vitrine de quem compra.

    **`publicado_em IS NOT NULL` entra**, pela mesma razão da
    `listar_programacao`: hoje não existe rascunho com escala — publicação e
    escala são a mesma transação das Stories 2.4 e 2.5 —, e no dia em que
    existir, a condição já vale. Rascunho não tem porta para abrir.

    **`join` explícito na `Table`, e não `Usuario.eventos`.** Não há
    `relationship` desse lado de propósito: `models/evento.py` declara
    `Evento.portarias` **sem** `back_populates`, e o comentário lá explica que o
    inverso obrigaria `usuario.py` a importar `evento.py`, que já importa
    `usuario.py` — ciclo de import. A `Table` do Core resolve isso sem nenhum
    dos dois.

    **Devolve `TurnoDaPortaria`, e não `Evento` do ORM**, no molde do
    `listar_do_organizador`: a rota até declararia o `response_model` e o corte
    aconteceria de qualquer jeito, mas a projeção feita aqui é a que um teste de
    service consegue ler sem subir HTTP.
    """
    eventos = sessao.scalars(
        select(Evento)
        .join(evento_portaria, evento_portaria.c.evento_id == Evento.id)
        .where(
            evento_portaria.c.usuario_id == portaria.id,
            Evento.publicado_em.is_not(None),
        )
        # `Evento.id` como desempate, pelo mesmo motivo escrito no
        # `listar_do_organizador`: duas casas na mesma noite é rotina, e sem
        # critério total o Postgres não promete ordem nenhuma entre dois shows
        # do mesmo horário. Esta é a tela que a portaria recarrega na fila.
        .order_by(Evento.data_hora, Evento.id)
    )

    # `list()` porque a sequência é percorrida **duas** vezes daqui em diante — a
    # primeira para juntar os ids da contagem, a segunda no laço de montagem. Um
    # `ScalarResult` se esgota na primeira, e a lista sairia vazia sem erro
    # nenhum.
    escalados = list(eventos)

    # ⚠️ **Uma consulta para a lista inteira, e não uma por turno** (Story 5.6).
    # Um `COUNT` dentro do laço abaixo é o N+1 que o `selectinload` da programação
    # existe para não fazer, reintroduzido por outra porta — e esta é a tela que a
    # portaria recarrega na fila.
    entradas = servico_de_ingresso.contar_entradas_por_evento(
        sessao, [evento.id for evento in escalados]
    )

    # ⚠️ **Um relógio só para a lista inteira**, e não uma leitura por item. Com
    # `datetime.now()` dentro do laço, dois turnos na mesma borda das duas horas
    # podem sair com respostas diferentes na mesma resposta — o mesmo motivo do
    # `instanteDaRequisicao` com `cache()` que a tela da 5.1 usava antes de o
    # campo existir.
    agora = datetime.now(timezone.utc)
    return [
        montar_turno(evento, entradas[evento.id], agora) for evento in escalados
    ]


def porta_aberta(evento: Evento, agora: datetime) -> bool:
    """O portão deste evento já abriu? (Story 5.2)

    **A única fonte da resposta**, e é isso que ela existe para ser: a lista de
    turnos preenche `TurnoDaPortaria.aberto` com ela, e a dependência
    `exigir_porta_aberta` recusa `403 EVENTO_NAO_ABERTO` com ela. Duas
    implementações da mesma janela — uma na tela, outra na rota — discordariam no
    primeiro ajuste de uma das duas, e o sintoma seria o pior possível: o item
    aparece clicável e a validação recusa.

    **`agora` é parâmetro, e não `datetime.now()` aqui dentro.** Quem chama já
    leu o relógio uma vez para a resposta inteira; ler de novo por item faria
    dois turnos na mesma borda saírem com vereditos diferentes. De quebra, é o
    que torna a janela testável sem congelar o relógio do processo.

    **Não há fechamento** — ver o comentário de `ABERTURA_DOS_PORTOES`.
    """
    return evento.data_hora - ABERTURA_DOS_PORTOES <= agora


def montar_turno(
    evento: Evento, entradas: int, agora: datetime | None = None
) -> TurnoDaPortaria:
    """Projeta o `Evento` no contrato da portaria, com o `aberto` calculado.

    Campo a campo, e não `model_validate(evento)`: nem `aberto` nem `entradas` são
    coluna, e o schema deixou de declarar `from_attributes` justamente por isso (o
    docstring dele explica a troca).

    **`agora` opcional, e os dois modos de chamar são de propósito.** A lista
    passa o relógio que leu uma vez para a resposta inteira; a rota de um turno
    só (`GET /portaria/eventos/{id}`, Story 5.3) não tem o que sincronizar e
    deixa a função ler. Sem o parâmetro, a lista precisaria montar o schema à
    mão para não ler o relógio N vezes — e aí haveria duas projeções do mesmo
    `Evento` no arquivo, que é exatamente a divergência que esta função existe
    para não acontecer.

    ⚠️ **`entradas` é obrigatório, e não opcional como o `agora`** (Story 5.6). A
    simetria seria bonita e mentiria: um padrão `0` faria o chamador que esquecesse
    de contar responder "ninguém entrou ainda" em vez de estourar, e zero é o
    número mais plausível que existe nesta tela — o defeito passaria o turno
    inteiro sem ser visto. Já o relógio não tem esse problema: `datetime.now()` é
    a resposta certa quando ninguém passa nada.
    """
    return TurnoDaPortaria(
        id=evento.id,
        nome=evento.nome,
        data_hora=evento.data_hora,
        local=evento.local,
        cidade=evento.cidade,
        aberto=porta_aberta(evento, agora or datetime.now(timezone.utc)),
        entradas=entradas,
    )


def montar_turno_do_leitor(sessao: Session, evento: Evento) -> TurnoDoLeitor:
    """O turno com os quatro números — `GET /portaria/eventos/{id}` (Story 5.6).

    **Ela existe para o contador nascer preenchido.** Sem os quatro números na
    resposta do cabeçalho, a tela abriria com zeros e só mostraria a verdade
    depois da primeira validação do turno — quem assumisse a porta no meio da noite
    veria "0 entradas" com trezentas pessoas dentro. É o AC "os contadores vêm do
    banco" valendo antes de qualquer leitura, e não só depois dela.

    **Duas consultas, e não uma.** As entradas saem de `ingresso.usado_em` e as
    recusas da tabela `validacao` — fontes diferentes de propósito, e o porquê está
    em `models/validacao.py`. Juntá-las num `UNION` economizaria uma ida ao banco
    numa rota que roda uma vez por turno, ao custo de escrever em SQL a decisão que
    hoje se lê em duas linhas de Python.

    **Reaproveita o `montar_turno`** em vez de montar os sete campos de novo: é a
    mesma projeção mais um campo, e duas montagens do mesmo `Evento` no arquivo é
    exatamente o que o docstring daquela função existe para evitar.
    """
    turno = montar_turno(
        evento,
        servico_de_ingresso.contar_entradas_por_evento(sessao, [evento.id])[
            evento.id
        ],
    )
    return TurnoDoLeitor(
        **turno.model_dump(),
        recusas=servico_de_ingresso.contar_recusas(sessao, evento.id),
    )


def obter_escalado(sessao: Session, portaria: Usuario, evento_id: UUID) -> Evento | None:
    """O evento em que **esta** conta foi escalada — ou `None` (Story 5.2).

    **As duas condições no mesmo `where`**, e não um `get()` seguido de um `if`:
    a mesma disciplina do `_carregar_do_cliente` de `services/ingresso.py`. O
    vínculo do AD-7 fica verdade por construção, não por quem lembrar de checar.

    ⚠️ **Evento inexistente e evento de outra portaria devolvem o mesmo
    `None`**, e quem chama responde a mesma recusa para os dois. Distinguir os
    casos transformaria a rota num oráculo de "esse UUID é um evento?" para quem
    não trabalha nele — a mesma razão do `404` único do `_carregar_do_cliente` e
    do login da Story 1.4.

    Devolve o `Evento` do ORM, e não o `TurnoDaPortaria`: quem chama é a
    dependência da validação, que precisa da entidade para o `where` do ingresso
    e para o relógio do portão. A rota de leitura projeta depois.
    """
    return sessao.scalars(
        select(Evento)
        .join(evento_portaria, evento_portaria.c.evento_id == Evento.id)
        .where(
            Evento.id == evento_id,
            evento_portaria.c.usuario_id == portaria.id,
            # Mesmo corte do `listar_escalados`: rascunho não tem porta para
            # abrir. Sem ele, um turno invisível na lista aceitaria validação.
            Evento.publicado_em.is_not(None),
        )
    ).first()


def listar_do_organizador(sessao: Session, organizador: Usuario) -> list[EventoResumo]:
    """Os eventos publicados por quem está na sessão, com os totais somados.

    **Mora neste service pelo mesmo motivo do `listar_portarias`**: é leitura
    sem transação e sem invariante, mas toca o banco — e router que abre uma
    `Session` para consultar é o que o paradigma da espinha proíbe sem exceção.
    O critério inteiro está no docstring de `app/api/organizador.py`.

    **O parâmetro é o `Usuario` da sessão, nunca um `organizador_id` solto.**
    É a mesma assinatura do `publicar()`: ver os eventos de outra pessoa não é
    uma chamada que este service recusa, é uma chamada que não existe. Sem
    parâmetro de query, de caminho ou de corpo por onde outro id pudesse entrar,
    o escopo deixa de depender da disciplina de quem chama.

    **Devolve `EventoResumo`, e não `Evento` do ORM.** Os dois totais não são
    atributos da entidade — são uma vista de leitura, e é aqui que eles nascem.
    A alternativa (`@computed_field` no schema, ou `@property` no modelo)
    esconderia a soma do AD-13 na camada de serialização, um passo mais longe
    do teste que a prova. Precedente: `ticketmaster.buscar_eventos` também
    devolve schema, não ORM.
    """
    eventos = sessao.scalars(
        select(Evento)
        .where(Evento.organizador_id == organizador.id)
        # `Evento.id` como desempate: dois shows no mesmo horário — duas casas
        # na mesma noite é rotina — trocavam de lugar entre requisições, porque
        # sem critério total o Postgres não promete ordem nenhuma. A lista do
        # organizador é a tela que ele recarrega o dia inteiro.
        .order_by(Evento.data_hora, Evento.id)
        # ⚠️ Não é otimização prematura: sem ele, ler `evento.setores` no laço
        # abaixo emite **uma consulta por evento**, e o custo cresce com o
        # sucesso do organizador. O sintoma só aparece com volume, ou seja,
        # nunca, na avaliação — e é exatamente por isso que a linha entra agora.
        .options(selectinload(Evento.setores))
    )

    # A soma acontece aqui, num lugar só, onde um teste consegue lê-la.
    #
    # ⚠️ **AD-13**: `setor.capacidade` e `setor.vendidos` são a única fonte da
    # disponibilidade. É proibido derivar qualquer um dos dois com `COUNT`
    # sobre reserva ou ingresso — nem hoje, que as duas tabelas não existem,
    # nem depois da Epic 3, que é quem vai escrever em `vendidos` pelo `UPDATE`
    # condicional. Evento sem setor nenhum (impossível pela rota, possível por
    # `psql`) soma zero e não quebra a listagem.
    return [
        EventoResumo(
            id=evento.id,
            nome=evento.nome,
            data_hora=evento.data_hora,
            local=evento.local,
            cidade=evento.cidade,
            publicado_em=evento.publicado_em,
            capacidade_total=sum(setor.capacidade for setor in evento.setores),
            vendidos_total=sum(setor.vendidos for setor in evento.setores),
        )
        for evento in eventos
    ]


def _escapar_curingas(termo: str) -> str:
    r"""Neutraliza `%`, `_` e `\` antes de o termo virar padrão de `LIKE`.

    ⚠️ **A armadilha mais silenciosa desta rota.** `%` e `_` são curingas do
    `LIKE`, e o termo vem digitado por gente: sem isto, `?q=%` devolve a
    programação inteira e `?q=_` devolve quase tudo — os dois com `200` e com
    cara de resultado. Ninguém descobre pela tela, porque a tela funciona.

    **A contrabarra é escapada primeiro**, e a ordem não é estética: fazendo
    `%` antes, a contrabarra que acabou de ser inserida como escape seria
    escapada de novo no passo seguinte, e o padrão sairia com `\\%` — que casa
    uma contrabarra literal seguida de qualquer coisa, não um `%` literal.

    Quem informa ao Postgres que a contrabarra é o caractere de escape é o
    `escape="\\"` declarado no `ilike` de quem chama. Sem ele o padrão continua
    errado, só que de outro jeito.

    ⚠️ **Este helper sozinho não basta, e por isso ele não é chamado direto.**
    Ver `_padrao_de_busca` logo abaixo: escapar em Python e só então aplicar
    `unaccent` no Postgres deixa passar o curinga que o próprio `unaccent`
    fabrica.
    """
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _padrao_de_busca(palavra: str) -> ColumnElement[str]:
    r"""O `%palavra%` do `ILIKE`, sem acento e com os curingas neutralizados.

    ⚠️ **A ordem é `unaccent` primeiro, escape depois — e a ordem é o conserto**
    (code review da Epic 3). Antes o padrão era
    `func.unaccent(f"%{_escapar_curingas(termo)}%")`, ou seja: escapava em Python
    e **então** mandava o Postgres tirar os acentos. Só que `unaccent` também
    normaliza as formas *fullwidth* — `unaccent('％')` (U+FF05) devolve `'%'`,
    e `unaccent('＿')` devolve `'_'`. O escape via Python nunca via esses
    caracteres, e o `unaccent` os convertia em curingas **depois** que a
    proteção já tinha passado.

    O resultado era exatamente a falha que o `_escapar_curingas` existe para
    impedir, por uma porta que ele não cobria: `?q=％` virava o padrão `%%%` e
    devolvia a programação inteira, com `200` e cara de resultado. Confirmado
    contra o Postgres do `docker-compose`:

    ```sql
    SELECT unaccent(U&'\FF05');                                  -- %
    SELECT unaccent('Show Secreto') ILIKE unaccent('%'||U&'\FF05'||'%');  -- t
    ```

    Escapando **em SQL, sobre o resultado do `unaccent`**, não sobra caractere
    que vire curinga depois da proteção. O `_escapar_curingas` continua existindo
    porque a ordem interna dele (contrabarra primeiro) é a mesma que estes três
    `replace` aninhados precisam ter — e o motivo está escrito lá.
    """
    sem_acento = func.unaccent(palavra)
    escapado = func.replace(
        func.replace(func.replace(sem_acento, "\\", "\\\\"), "%", "\\%"),
        "_",
        "\\_",
    )
    return func.concat("%", escapado, "%")


def listar_programacao(
    sessao: Session,
    termo: str = "",
    cidade: str = "",
    periodo: PeriodoDaProgramacao = PeriodoDaProgramacao.TODOS,
) -> list[EventoNaProgramacao]:
    """A programação pública: o que está publicado e ainda vai acontecer.

    **Quatro decisões moram nesta função.**

    *Por que a peneira é do banco, e não da tela* (decisão do Igor, Story 3.2).
    Os três filtros entram no `where` do Postgres, e o estado deles mora na URL
    (`?q=&cidade=&periodo=`). A alternativa — devolver a lista inteira e
    filtrá-la em JavaScript — daria uma busca instantânea ao digitar, e custaria
    três coisas: a raiz viraria uma ilha `"use client"` (hoje ela não tem uma
    linha), o filtro não sobreviveria a recarregar nem a compartilhar o link, e
    a programação inteira atravessaria a rede a cada visita. Filtrar em Python
    **aqui dentro** teria o mesmo defeito por outra porta: traria a tabela
    inteira para a memória e desfaria o motivo de a condição existir. Se uma
    condição não couber no `where`, ela está errada.

    *Por que só publicado.* `publicado_em IS NULL` é rascunho (Story 2.3), e o
    comentário do modelo diz, com todas as letras, que esse estado existe para
    tornar verificável o AC desta story. Não há tela que produza um rascunho
    hoje; a condição está no `where` — e não num filtro em Python — porque o
    dia em que houver, ela já vale, e vale para qualquer volume.
    ⚠️ `listar_do_organizador` **continua sem esse filtro**, de propósito: o
    rascunho de alguém é dele, e a entrada do `deferred-work.md` sobre a rota do
    organizador permanece aberta.

    *Por que só futuro, e por que no backend* (decisão do Igor). A programação
    pública é o que está por vir: quem chega na raiz quer saber o que dá para
    comprar, e show que já aconteceu não é nenhuma das duas coisas. O histórico
    não se perde — ele continua inteiro em `/organizador/eventos`, que é de
    quem publicou. O corte ficou aqui, e não na tela como em "Meus eventos",
    porque lá o dono da informação é o organizador e o histórico é o inventário
    dele; aqui o visitante veria metade da página inicial ocupada por shows que
    não pode comprar.

    *Por que o estoque não atravessa o contrato.* `EventoNaProgramacao` não tem
    `capacidade`, `vendidos` nem `setores` — UX-DR7 se garante no
    `response_model`, não na tela. Os dois campos derivados daqui existem
    justamente para dizer o que interessa sem revelar número nenhum.
    """
    # Lido **uma vez**, antes da consulta, e ele serve aos **dois** cortes de
    # tempo: o de eventos passados e o teto do `?periodo=`. Duas leituras do
    # relógio na mesma requisição podem discordar sobre o evento que começa
    # agora — é a mesma disciplina que o `cache()` da tela de "Meus eventos"
    # impôs no frontend. Um `datetime` com fuso, nunca texto: comparar strings
    # ISO funciona por acidente enquanto todo offset for `Z`.
    agora = datetime.now(timezone.utc)

    # As condições se acumulam numa lista e entram num `where` só. As duas da
    # Story 3.1 vêm primeiro, e **não têm exceção**: rascunho e evento passado
    # continuam fora mesmo quando o termo casa perfeitamente com o nome deles.
    # Um filtro novo nunca abre porta num corte antigo.
    condicoes: list[ColumnElement[bool]] = [
        Evento.publicado_em.is_not(None),
        Evento.data_hora >= agora,
    ]

    # `.strip()` antes de qualquer coisa: `?q=` vazio e `?q=%20%20` são a mesma
    # intenção — "não filtrei" —, e `?q=%20marina%20` é uma busca por "marina".
    termo_limpo = termo.strip()
    if termo_limpo:
        # ⚠️ **Uma condição por palavra, todas exigidas** (code review da Epic 3,
        # decisão do Igor). Antes o termo inteiro era um substring só, testado
        # contra as três colunas com `OR` — e `?q=marina sena são paulo` devolvia
        # vazio, porque nenhuma coluna sozinha contém a string inteira. Artista +
        # cidade é a primeira coisa que alguém digita, e o desfecho era
        # indistinguível de "esse show não existe".
        #
        # Agora cada palavra precisa aparecer em **alguma** das três colunas
        # (`AND` de `OR`s): "marina" casa o nome, "paulo" casa a cidade, e o
        # evento entra. Buscar uma palavra só continua exatamente como era.
        for palavra in termo_limpo.split():
            condicoes.append(
                or_(
                    *(
                        # `escape="\\"` é o que faz o escape valer: sem ele o
                        # Postgres lê a contrabarra como caractere comum.
                        func.unaccent(coluna).ilike(
                            _padrao_de_busca(palavra), escape="\\"
                        )
                        # ⚠️ `Evento.cidade` é anulável (Story 2.3), e isso está
                        # certo assim: `unaccent(NULL) ILIKE …` é `NULL`, e
                        # `TRUE OR NULL` é `TRUE` — o evento sem cidade continua
                        # achável pelo nome e pelo local. Não "conserte" com
                        # `coalesce`: não há nada quebrado.
                        for coluna in (Evento.nome, Evento.local, Evento.cidade)
                    )
                )
            )

    # **Igualdade exata, e não `ilike`** (decisão do Igor): o valor vem dos
    # nossos próprios chips, que vêm de `listar_cidades_em_cartaz` — ou seja, do
    # banco. Este parâmetro não é campo de digitação, e tratá-lo como se fosse
    # daria a `?cidade=sao` um resultado que nenhum chip produz. Quem quer
    # digitar tem o `?q=`, que casa cidade também.
    if cidade.strip():
        condicoes.append(Evento.cidade == cidade.strip())

    # Janelas **corridas** a partir de agora, não semana e mês do calendário —
    # o motivo inteiro está no docstring do `PeriodoDaProgramacao`. `TODOS` não
    # acrescenta condição nenhuma: "sem filtro" é a ausência de um `where`, não
    # um teto infinito escrito em SQL.
    if periodo == PeriodoDaProgramacao.SEMANA:
        condicoes.append(Evento.data_hora < agora + timedelta(days=7))
    elif periodo == PeriodoDaProgramacao.MES:
        condicoes.append(Evento.data_hora < agora + timedelta(days=30))

    eventos = sessao.scalars(
        select(Evento)
        .where(*condicoes)
        # `Evento.id` como desempate, pelo mesmo motivo escrito na
        # `listar_do_organizador`: sem critério total, dois shows no mesmo
        # horário trocam de lugar entre requisições.
        .order_by(Evento.data_hora, Evento.id)
        # Sem ele, ler `evento.setores` no laço abaixo emite uma consulta por
        # evento. É a raiz do produto: a tela mais visitada que existe aqui.
        # ⚠️ Filtrar não pode reintroduzir o N+1 que a Story 3.1 fechou.
        .options(selectinload(Evento.setores))
        .limit(TETO_DA_PROGRAMACAO)
    )

    programacao: list[EventoNaProgramacao] = []
    for evento in eventos:
        # ⚠️ **AD-13**: disponível é `setor.vendidos < setor.capacidade`, lido
        # do próprio setor. É **proibido** derivar disponibilidade com `COUNT`
        # sobre reserva ou ingresso, em qualquer camada — as duas tabelas
        # nascem nas Stories 3.5 e 3.9, e é agora que o hábito se forma.
        precos = [
            setor.preco_centavos
            for setor in evento.setores
            if setor.vendidos < setor.capacidade
        ]

        # ⚠️ `min()` sobre sequência vazia levanta `ValueError`, e dois casos
        # caem aqui: o evento com todos os setores esgotados e o evento sem
        # setor nenhum (impossível pela rota de publicação, possível por
        # `psql` — e existe no banco de desenvolvimento). O `if` trata os dois
        # antes; um `try/except ValueError` esconderia a regra dentro de um
        # tratamento de exceção.
        #
        # O evento esgotado **continua na lista**: ele é informação (o show
        # existe e acabou), não ruído.
        programacao.append(
            EventoNaProgramacao(
                id=evento.id,
                nome=evento.nome,
                data_hora=evento.data_hora,
                local=evento.local,
                cidade=evento.cidade,
                # O menor preço **entre os setores que ainda têm ingresso**
                # (decisão do Igor). Se a Pista, que é a mais barata, esgotou,
                # a fila passa a anunciar o preço do que dá para comprar:
                # anunciar um preço que não existe mais é a única forma de a
                # listagem mentir com número.
                preco_minimo_centavos=min(precos) if precos else None,
                esgotado=not precos,
            )
        )

    return programacao


def obter_destaque(sessao: Session) -> EventoEmDestaque | None:
    """O próximo show da programação — a chamada principal da raiz (Story 3.3).

    **Mesmo recorte da `listar_programacao`**: publicado (`publicado_em IS NOT
    NULL`) e ainda por acontecer (`data_hora >= agora`). Não é "parecido" — é o
    mesmo, e por isso as duas condições estão escritas na mesma ordem: um
    destaque que aparecesse fora do recorte da lista seria um show na capa que
    não existe na programação logo abaixo.

    **Por que uma consulta própria, e não `listar_programacao(sessao)[0]`.** A
    de cima monta três filtros opcionais e roda um laço de derivação de preço
    sobre a programação **inteira** para descartar tudo menos a primeira linha.
    O `LIMIT 1` daqui é a diferença entre ler um evento e ler todos para jogar
    quase todos fora — e essa distância cresce com o catálogo, na rota da tela
    mais visitada do produto. A duplicação das duas condições é real e é o preço
    consciente: extrair um helper `_em_cartaz()` economizaria duas linhas e
    espalharia o recorte por um terceiro lugar, sem que nenhum dos dois
    chamadores ficasse mais fácil de ler.

    **Por que o esgotado continua sendo destaque** (decisão do Igor). Mesma
    regra da fila da Story 3.1: show esgotado é informação, não ruído. A
    alternativa — pular para o próximo com ingresso — desperdiçaria menos o
    bloco grande da tela, e em troca faria "o próximo show" deixar de ser
    verdade: a capa esconderia do visitante justamente o show mais próximo. Quem
    trata o esgotado é a tela, com selo e sem link.

    **`None` quando não há nada em cartaz**, e o router devolve isso como `200`
    com corpo `null` — nunca `404`. O motivo está lá.
    """
    # Lido **uma vez**, como na `listar_programacao` e pelo mesmo motivo: duas
    # leituras do relógio na mesma requisição podem discordar sobre o evento que
    # começa agora. Aqui só há um corte de tempo, mas a disciplina é a mesma —
    # e um `datetime` com fuso, nunca texto.
    agora = datetime.now(timezone.utc)

    evento = sessao.scalars(
        select(Evento)
        .where(
            Evento.publicado_em.is_not(None),
            Evento.data_hora >= agora,
        )
        # ⚠️ `Evento.id` como desempate, o **mesmo** da `listar_programacao`.
        # Sem ele, dois shows no mesmo horário fariam a capa alternar entre um e
        # outro a cada recarregar: com `LIMIT 1`, qual das duas linhas volta
        # passa a ser escolha do planejador, não do código.
        .order_by(Evento.data_hora, Evento.id)
        .limit(1)
        # Uma consulta a mais para os setores, e não uma por setor: sem ele, ler
        # `evento.setores` duas linhas abaixo emitiria o `SELECT` preguiçoso no
        # meio da montagem do schema.
        .options(selectinload(Evento.setores))
    ).first()

    if evento is None:
        return None

    # ⚠️ **AD-13**: disponível é `setor.vendidos < setor.capacidade`, lido do
    # próprio setor. É **proibido** derivar disponibilidade com `COUNT` sobre
    # reserva ou ingresso, em qualquer camada — as duas tabelas nascem nas
    # Stories 3.5 e 3.9, e é agora que o hábito se forma. Uma lista só serve aos
    # dois campos derivados abaixo, como na `listar_programacao`.
    precos = [
        setor.preco_centavos
        for setor in evento.setores
        if setor.vendidos < setor.capacidade
    ]

    return EventoEmDestaque(
        id=evento.id,
        nome=evento.nome,
        data_hora=evento.data_hora,
        local=evento.local,
        cidade=evento.cidade,
        imagem_url=evento.imagem_url,
        # **Todos os setores, inclusive o esgotado** (suposição declarada na
        # story): a ficha diz o que o show tem, não o que sobrou. Filtrar por
        # disponibilidade aqui faria a lista mudar sozinha conforme as vendas,
        # sem nenhuma pista do porquê. A ordem alfabética já vem do
        # `order_by="Setor.nome"` do `relationship` — não há `sorted()` aqui, e
        # não deve haver: duas fontes para a mesma ordem é uma chance de elas
        # discordarem.
        setores=[setor.nome for setor in evento.setores],
        # ⚠️ `min()` sobre sequência vazia levanta `ValueError`, e dois casos
        # caem aqui: o evento com todos os setores esgotados e o evento sem setor
        # nenhum (possível por `psql`, e existe no banco de desenvolvimento). O
        # `if` trata os dois antes, como na `listar_programacao`.
        preco_minimo_centavos=min(precos) if precos else None,
        esgotado=not precos,
    )


def listar_cidades_em_cartaz(sessao: Session) -> list[str]:
    """As cidades que têm show na programação — o universo dos chips `ONDE`.

    **Mesmo recorte da `listar_programacao`**: publicado e ainda por acontecer.
    Chip que oferece uma cidade sem show em cartaz é um filtro que só sabe
    devolver lista vazia — e quem clicou concluiria que a busca está quebrada,
    não que a cidade não tem nada marcado. Ela vem do banco pelo mesmo motivo:
    uma lista fixa no código (`São Paulo`, `Rio`, como no protótipo) é barata e
    mente no dia em que houver um show em Belo Horizonte.

    ⚠️ **Ela não recebe o termo nem a cidade escolhida, de propósito** — e não é
    esquecimento. A lista de escolhas é o **universo**, não o resultado:
    encolhê-la conforme a pessoa filtra faz o chip sumir debaixo do cursor de
    quem ia clicar, e tira o caminho de volta de quem filtrou errado. É o mesmo
    raciocínio que mantém a barra de busca na tela quando a busca não achou
    nada.

    `NULL` fica fora: a cidade é anulável desde a Story 2.3, e um chip em branco
    não é uma escolha. O evento sem cidade continua na programação — ele só não
    gera chip nem aparece em filtro de cidade nenhum.
    """
    agora = datetime.now(timezone.utc)

    return list(
        sessao.scalars(
            select(Evento.cidade)
            .where(
                Evento.publicado_em.is_not(None),
                Evento.data_hora >= agora,
                Evento.cidade.is_not(None),
            )
            .distinct()
            # Alfabética, e não por quantidade de shows: a ordem precisa ser
            # estável entre visitas para o chip não trocar de lugar debaixo do
            # cursor a cada evento publicado.
            .order_by(Evento.cidade)
        )
    )


def _disponibilidade_do_setor(setor: Setor) -> DisponibilidadeDoSetor:
    """Quanto resta de um setor, em palavra (Story 3.4).

    **Função própria para a regra do limiar existir num lugar só** e ser lida por
    um teste. Ela é uma linha e meia; inline no laço de `obter_publico` ela
    ficaria igual de curta e sem nome — e "por que 20% e não 10?" é uma pergunta
    que precisa de um lugar para ser respondida.

    ⚠️ **`ESGOTADO` é conferido primeiro, e a ordem é a regra.** Zero restante
    também é "20% ou menos": com as condições trocadas, o setor esgotado sairia
    como `ULTIMOS` — barra cheia e a palavra errada, dizendo "corre" sobre o que
    já acabou.

    ⚠️ **A conta é em inteiros — `(capacidade - vendidos) * 5 <= capacidade` —, e
    não com `0.2` em ponto flutuante.** As duas formas dizem a mesma coisa em
    álgebra e discordam na borda: um setor de 15 lugares com 12 vendidos deixa
    exatamente 20%, e `3 <= 15 * 0.2` depende de arredondamento binário. É
    justamente na borda que o `float` decide sozinho, e é a borda que o teste
    exercita.

    **`capacidade > 0` é `CHECK` no banco desde a Story 2.3**, então não há
    divisão por zero possível aqui — nem nesta função, que não divide, nem no
    `round()` de quem a chama.
    """
    restam = setor.capacidade - setor.vendidos

    if restam <= 0:
        return DisponibilidadeDoSetor.ESGOTADO
    if restam * 5 <= setor.capacidade:
        return DisponibilidadeDoSetor.ULTIMOS
    return DisponibilidadeDoSetor.DISPONIVEL


def obter_publico(sessao: Session, evento_id: UUID) -> EventoPublico:
    """Um evento em cartaz com seus setores — a tela da escolha (Story 3.4).

    **Mesmo recorte das outras três rotas públicas**: publicado (`publicado_em IS
    NOT NULL`) e ainda por acontecer (`data_hora >= agora`). Não é "parecido" — é
    o mesmo, escrito na mesma ordem, e um evento que abrisse aqui fora do recorte
    da programação seria um show que existe pelo link e não existe na lista.

    **Uma consulta com as três condições no mesmo `where`, e não um
    `sessao.get()` seguido de dois `if`.** Mesmo motivo escrito no
    `obter_do_organizador`: com tudo no `where`, "só vejo o que está em cartaz" é
    verdade **por construção**, não por disciplina de quem escrever a próxima
    rota. Dois `if` depois do `get()` criam dois caminhos para a mesma decisão, e
    o segundo é o que alguém esquece.

    ⚠️ **Os três casos recebem o mesmo `404`, com o mesmo código e a mesma
    mensagem** (decisão do Igor): `id` que não é evento nenhum, evento em
    rascunho e evento cuja data já passou. Distinguir "não existe" de "é rascunho
    de alguém" transformaria esta rota num oráculo — daria para varrer UUIDs e
    descobrir o que um organizador ainda não publicou. É a mesma disciplina do
    `EVENTO_NAO_ENCONTRADO` do organizador (Story 2.6) e do login da 1.4, que não
    diz se o e-mail existe. E é por isso que o "evento passado" também não ganha
    resposta própria: ela custaria um estado de tela ("este show já aconteceu")
    para uma informação que quem guardou o link de ontem não vai fazer nada com.

    **O estoque não atravessa, e é esta a rota em que isso mais importa.** O
    `EventoPublico` não tem `capacidade` nem `vendidos`; o que sai é o par
    derivado do `SetorPublico` — a proporção que desenha a barra e a palavra que
    diz o estado (AD-13, UX-DR7). O `response_model` da rota é quem garante isso,
    não a tela.
    """
    # Lido **uma vez**, como na `listar_programacao` e no `obter_destaque`, e pelo
    # mesmo motivo: duas leituras do relógio na mesma requisição podem discordar
    # sobre o evento que começa agora. Um `datetime` com fuso, nunca texto.
    agora = datetime.now(timezone.utc)

    evento = sessao.scalars(
        select(Evento)
        .where(
            Evento.id == evento_id,
            Evento.publicado_em.is_not(None),
            Evento.data_hora >= agora,
        )
        # Uma consulta a mais para os setores, e não uma por setor: sem ele, ler
        # `evento.setores` no laço abaixo emitiria o `SELECT` preguiçoso no meio
        # da montagem do schema.
        .options(selectinload(Evento.setores))
    ).first()

    if evento is None:
        raise ErroDeDominio(
            "EVENTO_NAO_ENCONTRADO",
            "Esse show não está em cartaz.",
            status_http=404,
        )

    return EventoPublico(
        id=evento.id,
        nome=evento.nome,
        data_hora=evento.data_hora,
        local=evento.local,
        cidade=evento.cidade,
        imagem_url=evento.imagem_url,
        maximo_por_compra=MAXIMO_POR_COMPRA,
        # **Todos os setores, inclusive o esgotado**, e sem `sorted()`: a ordem
        # alfabética já vem do `order_by="Setor.nome"` do `relationship` (Story
        # 2.3). Duas fontes para a mesma ordem é uma chance de elas discordarem.
        #
        # Evento **sem setor nenhum** cai aqui como lista vazia e não quebra —
        # ele é impossível pela rota de publicação, possível por `psql`, e existe
        # no banco de desenvolvimento. Ao contrário da `listar_programacao`, não
        # há `min()` nenhum para proteger: a compreensão sobre lista vazia é
        # lista vazia.
        setores=[
            SetorPublico(
                id=setor.id,
                nome=setor.nome,
                preco_centavos=setor.preco_centavos,
                disponibilidade=_disponibilidade_do_setor(setor),
                # ⚠️ **AD-13**: a proporção nasce de `setor.vendidos` e
                # `setor.capacidade`, lidos do próprio setor — é **proibido**
                # derivá-la com `COUNT` sobre reserva ou ingresso, em qualquer
                # camada. As duas tabelas nascem nas Stories 3.5 e 3.9.
                #
                # Duas casas: a barra tem 5px de altura e não mostra mais que 1%,
                # e menos dígitos é menos superfície para alguém tentar
                # reconstruir a capacidade a partir da proporção.
                #
                # ⚠️ **O teto de `0.99` não é estético** (code review da Epic 3).
                # `round(999/1000, 2)` é `1.0`, e nesse ponto a disponibilidade
                # ainda é `ULTIMOS`: a tela mostrava a barra cheia ao lado da
                # palavra "últimos ingressos", com o stepper ativo — indistinguível
                # de esgotado. É o mesmo sintoma que o `_disponibilidade_do_setor`
                # previne pela ordem das condições ("barra cheia e a palavra
                # errada"), reintroduzido pelo arredondamento em capacidade
                # grande. Barra cheia fica reservada a quem de fato esgotou.
                proporcao_vendida=(
                    1.0
                    if setor.vendidos >= setor.capacidade
                    else min(round(setor.vendidos / setor.capacidade, 2), 0.99)
                ),
            )
            for setor in evento.setores
        ],
    )


def obter_do_organizador(
    sessao: Session, organizador: Usuario, evento_id: UUID
) -> Evento:
    """Um evento do organizador da sessão, com setores e escala.

    **Uma consulta com as duas condições, e não `sessao.get()` seguido de um
    `if` conferindo o dono.** As duas versões funcionam; a segunda cria dois
    caminhos para a mesma decisão, e o segundo é o que alguém esquece na
    próxima rota. Com `id` e `organizador_id` no mesmo `where`, "só vejo o que é
    meu" é verdade por construção — não por disciplina de quem escreveu.

    **Uma mensagem só para "não existe" e para "não é seu".** Distinguir os
    dois transformaria esta rota num oráculo — "esse UUID é um evento de
    alguém?" —, e é a mesma disciplina do `PORTARIA_INVALIDA` da Story 2.5 e do
    login da 1.4, que não diz se o e-mail existe. Quem chama não perde nada:
    para o organizador, os dois casos significam a mesma coisa.
    """
    evento = sessao.scalars(
        select(Evento)
        .where(Evento.id == evento_id, Evento.organizador_id == organizador.id)
        .options(selectinload(Evento.setores), selectinload(Evento.portarias))
    ).first()

    if evento is None:
        raise ErroDeDominio(
            "EVENTO_NAO_ENCONTRADO",
            "Esse evento não existe ou não é seu.",
            status_http=404,
        )

    return evento
