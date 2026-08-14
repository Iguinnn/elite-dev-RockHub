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

**A ordem das seis recusas é a garantia do "nenhum evento órfão".** Elas
acontecem antes de qualquer `add`: se a lista está vazia, tem nomes repetidos,
não traz portaria nenhuma, traz um id que não resolve, a data já passou ou o
término não vem depois do início, nada chega a existir no banco — nem o evento,
nem o primeiro setor antes de o segundo estourar.

```
1. setores vazio          → EVENTO_SEM_SETOR
2. nome de setor repetido → SETOR_DUPLICADO
3. portaria_ids vazio     → EVENTO_SEM_PORTARIA
4. id que não resolve     → PORTARIA_INVALIDA
5. data_hora no passado   → EVENTO_NO_PASSADO
6. fim <= início          → FIM_ANTES_DO_INICIO
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

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroDeDominio
from app.models.evento import Evento, Setor, evento_portaria
from app.models.ingresso import Ingresso
from app.models.reserva import EstadoReserva, ItemReserva, Reserva
from app.models.usuario import PapelUsuario, Usuario
from app.models.validacao import Validacao
from app.schemas.evento import (
    DisponibilidadeDoSetor,
    EstadoDoTurno,
    EventoEdicao,
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
# aberta enquanto a API recusa. A tela lê `TurnoDaPortaria.estado`, que sai
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
# ⚠️ **Havia um "não há fechamento, de propósito" escrito aqui, e ele caiu em
# 14/08/2026** (techspec `docs/techspec-fim-do-evento.md`). A justificativa era
# em duas partes: *"o show acaba e ainda há gente entrando"* e *"este projeto não
# tem coluna de duração nenhuma"*. A segunda deixou de valer — `evento.data_hora_
# fim` existe e é obrigatória —, e sem ela a primeira não sustenta o que
# sustentava: o que a porta sem teto produzia não era o retardatário atendido, era
# o turno de um show da semana passada continuando na lista da portaria, clicável
# e validável. A gente que entra depois do primeiro acorde está coberta pela hora
# que o organizador declara; quem quiser mais margem marca 03h em vez de 02h.
#
# **Esta constante não ganhou irmã.** Não existe `TOLERANCIA_APOS_O_FIM`, e o
# porquê está no docstring de `evento_encerrado`: uma folga fixa deste lado faria
# o sistema discordar do número que o organizador acabou de digitar.
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
    # aconteceu não é um caso de uso — é erro de digitação na data, e na Epic 3
    # esse evento entraria na programação e venderia ingresso para uma noite que
    # já passou.
    #
    # ⚠️ **"Permanente porque não existe tela de editar" deixou de ser o motivo,
    # e o erro continua permanente** (13/08/2026). Existe o `atualizar()` logo
    # acima — e ele recusa editar evento cuja `data_hora` já passou, pelo mesmo
    # código. Um evento publicado com data no passado nasce sem conserto pelas
    # duas pontas, e é essa simetria que mantém esta recusa valendo o que valia.
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

    # Sexta recusa, e a última — techspec `docs/techspec-fim-do-evento.md`.
    #
    # **Depois do `EVENTO_NO_PASSADO`, e não antes**, pelo mesmo motivo que
    # aquele entrou por último: a ordem das recusas anteriores é o que mantém os
    # testes das Stories 2.4 e 2.5 provando o que se propuseram a provar, e um
    # corpo daqueles não tem `data_hora_fim` nenhum a conferir.
    #
    # `<=` e não `<`: um show que termina no instante em que começa dura zero
    # minutos, e é erro de digitação igual ao término anterior ao início. Os dois
    # recebem a mesma frase de propósito — para quem digitou, é o mesmo engano.
    if dados.data_hora_fim <= dados.data_hora:
        raise ErroDeDominio(
            "FIM_ANTES_DO_INICIO",
            "O show precisa terminar depois de começar. Confira o horário de "
            "término.",
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
        data_hora_fim=dados.data_hora_fim,
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


def _travar_setores_e_exigir_sem_venda(
    sessao: Session, evento: Evento, mensagem: str
) -> list[Setor]:
    """Trava os setores do evento, colhe as vencidas e recusa se sobrou venda.

    **Os passos 2, 3 e 4 do contrato das duas rotas de escrita** — `atualizar` e
    `excluir` —, numa função só. É **função compartilhada, e não cópia**, ao
    contrário das cinco recusas do `publicar` logo abaixo: lá o que se repete são
    frases, e a convenção do projeto manda copiar duas e extrair na terceira;
    aqui o que se repete é a **garantia**, e a spec a enuncia como igualdade —
    "é essa igualdade que faz as duas rotas nunca discordarem sobre vendeu".
    Igualdade por disciplina de quem escreveu dura até a primeira das duas ser
    ajustada sozinha.

    A `mensagem` é o único parâmetro que varia, e varia porque o verbo muda: uma
    recusa de exclusão que diz "não pode mais ser editado" é a tela mentindo
    sobre o que o organizador acabou de tentar. O **código** é o mesmo
    `EVENTO_COM_VENDA` nas duas, que é a parte estável do contrato.

    Devolve os setores travados, em ordem de `id`.
    """
    # ⚠️ **Isto não é otimização, é a correção.** Sem o bloqueio, entre ler
    # `vendidos == 0` e escrever cabe uma reserva inteira: o `UPDATE` condicional
    # do AD-3 é um statement só, e ele passa no vão. Na edição o resultado seria
    # uma reserva paga apontando para um setor que acabou de mudar de preço; na
    # exclusão, para um evento que acabou de sumir.
    #
    # `ORDER BY setor.id` segue a disciplina de ordem já escrita no `criar()` e
    # no `_devolver_estoque`: travar em ordens cruzadas é como se ganha um
    # `40P01 deadlock detected`, que não é `ErroDeDominio` e vira `500`.
    #
    # ⚠️ `populate_existing` não é enfeite: os mesmos objetos já vieram no
    # `selectinload` do `obter_do_organizador`, e sem ele o SQLAlchemy devolveria
    # as instâncias do identity map **com os valores de antes do bloqueio**.
    # Travar a linha e continuar lendo o passado é ter o custo do `FOR UPDATE`
    # sem a garantia.
    setores = list(
        sessao.scalars(
            select(Setor)
            .where(Setor.evento_id == evento.id)
            .order_by(Setor.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    ids = [setor.id for setor in setores]

    # A colheita do AD-4, **na mesma transação**, entre o bloqueio e a leitura do
    # estoque.
    #
    # ⚠️ **Import dentro da função, e não no topo do módulo.** `services/reserva`
    # importa `MAXIMO_POR_COMPRA` daqui (linha 91 de lá, decisão registrada na
    # Story 3.4), então um import de módulo na direção contrária é ciclo na hora
    # de carregar o app. O que se move não é a direção da seta: é o momento do
    # import.
    from app.services.reserva import expirar_vencidas

    expirar_vencidas(sessao, ids)

    # Relê **do banco**, e não dos objetos. A colheita acima escreve `vendidos`
    # por `UPDATE ... synchronize_session=False`, que de propósito deixa o
    # atributo em Python desatualizado (AD-3). Decidir a trava pelo atributo seria
    # decidir pelo valor de antes da colheita — o setor cuja reserva acabou de
    # expirar continuaria "vendido" e a operação seria recusada.
    #
    # Um `select` de colunas, e não de entidades: ele não passa pelo identity
    # map, então não há como um objeto carregado responder no lugar do banco.
    vendidos_por_setor = sessao.execute(
        select(Setor.id, Setor.vendidos).where(Setor.id.in_(ids))
    ).all()

    if any(vendidos > 0 for _, vendidos in vendidos_por_setor):
        raise ErroDeDominio("EVENTO_COM_VENDA", mensagem, status_http=409)

    return setores


def atualizar(
    sessao: Session,
    organizador: Usuario,
    evento_id: UUID,
    dados: EventoEdicao,
) -> Evento:
    """Reescreve data, setores e escala de um evento que **ainda não vendeu**.

    A segunda rota de escrita do organizador, e a primeira que altera linha
    existente. Ela reabre um corte que o README declarava como consciente
    (13/08/2026); a spec inteira é `docs/techspec-editar-evento.md`.

    **A trava é `vendidos == 0` em todos os setores, depois de colher as
    vencidas.** *Descartei* travar só com reserva `PAGA`: o preço já vai
    congelado na reserva, então não haveria prejuízo contábil — mas alguém
    digitando o cartão veria o preço mudar na tela no meio da compra. E
    *descartei* checar sem colher antes: como a expiração é preguiçosa (AD-4),
    um checkout abandonado seguraria a edição por até dez minutos, e a tela
    diria "esse evento já vendeu" sobre um evento que não vendeu nada — mentira
    temporária que o organizador não tem como distinguir da verdadeira.

    ⚠️ **`vendidos` é lido para dentro do Python aqui, e o AD-3 proíbe isso.** A
    exceção é o `FOR UPDATE` do passo 2: as linhas estão **travadas** até o
    `commit`, e é isso — e só isso — que torna a leitura confiável. Fora de um
    bloqueio explícito, este `SELECT` seria exatamente o antipadrão que o
    `services/reserva.py` recusa no docstring dele.
    """
    # Lido **uma vez**, e usado nas duas comparações de tempo — a do show que já
    # aconteceu e a da data nova. Mesma disciplina do `criar()` da reserva: duas
    # leituras do relógio na mesma requisição podem discordar sobre o evento que
    # começa agora.
    agora = datetime.now(timezone.utc)

    # Passo 1 — o mesmo `404` da leitura, **pela mesma função**. Byte a byte o
    # mesmo corpo para "não existe" e "não é seu": escrever aqui um segundo
    # `select` com as duas condições criaria um segundo lugar para a regra do
    # oráculo morar, e o segundo é o que alguém esquece na próxima rota.
    evento = obter_do_organizador(sessao, organizador, evento_id)

    # Show que já aconteceu não se edita, e a recusa vem **antes do bloqueio**:
    # nenhum corpo conserta essa chamada, então travar as linhas de `setor` para
    # descobrir isso seria segurar o estoque do evento à toa. O código é o mesmo
    # `EVENTO_NO_PASSADO` da data nova — para quem edita, "a data que está lá
    # passou" e "a data que você mandou passou" são o mesmo impedimento.
    if evento.data_hora <= agora:
        raise ErroDeDominio(
            "EVENTO_NO_PASSADO",
            "Esse show já aconteceu e não pode mais ser editado.",
            status_http=422,
        )

    # Passos 2, 3 e 4 — travar, colher e conferir. Os três moram na função
    # compartilhada com o `excluir`, e é lá que está o motivo de cada um.
    setores_atuais = _travar_setores_e_exigir_sem_venda(
        sessao,
        evento,
        "Este evento já vendeu ingressos e não pode mais ser editado.",
    )

    # ── Passo 5: as seis recusas do `publicar`, na mesma ordem e com as mesmas
    # frases. **Cópia, e não função comum**, pela convenção escrita no
    # `_limpar_texto` de `schemas/evento.py`: duas ocorrências se copiam, e é a
    # terceira que vira código compartilhado.
    #
    # ⚠️ Frase que mudar aqui muda lá também. O organizador não pode receber duas
    # explicações diferentes para a mesma recusa dependendo de estar publicando
    # ou editando — é o mesmo formulário, com um botão diferente.
    if not dados.setores:
        raise ErroDeDominio(
            "EVENTO_SEM_SETOR",
            "Um evento precisa de ao menos um setor à venda.",
            status_http=422,
        )

    vistos: set[str] = set()
    for setor_pedido in dados.setores:
        chave = setor_pedido.nome.casefold()
        if chave in vistos:
            raise ErroDeDominio(
                "SETOR_DUPLICADO",
                f'Há mais de um setor chamado "{setor_pedido.nome}". '
                "Cada setor precisa de um nome diferente.",
                status_http=422,
            )
        vistos.add(chave)

    if not dados.portaria_ids:
        raise ErroDeDominio(
            "EVENTO_SEM_PORTARIA",
            "Escale ao menos um usuário de portaria para validar os ingressos "
            "deste evento.",
            status_http=422,
        )

    ids_pedidos = list(dict.fromkeys(dados.portaria_ids))

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

    if dados.data_hora <= agora:
        raise ErroDeDominio(
            "EVENTO_NO_PASSADO",
            "A data do show já passou. Confira o dia e o horário.",
            status_http=422,
        )

    # A sexta, cópia da do `publicar` — **mesma frase**, e ela é a razão de o
    # aviso do topo deste bloco existir: o organizador não pode receber duas
    # explicações diferentes para a mesma recusa dependendo de estar publicando
    # ou editando.
    if dados.data_hora_fim <= dados.data_hora:
        raise ErroDeDominio(
            "FIM_ANTES_DO_INICIO",
            "O show precisa terminar depois de começar. Confira o horário de "
            "término.",
            status_http=422,
        )

    # ── Passo 6: `id` que não é deste evento.
    atuais_por_id = {setor.id: setor for setor in setores_atuais}
    editados: set[UUID] = set()

    for setor_pedido in dados.setores:
        if setor_pedido.id is None:
            continue
        if setor_pedido.id not in atuais_por_id:
            # Um código e uma mensagem para os dois casos — id que não é setor
            # nenhum, e setor que é de outro evento. Mesma disciplina do
            # `SETOR_INVALIDO` da reserva: distinguir transformaria a rota num
            # oráculo sobre os setores alheios.
            raise ErroDeDominio(
                "SETOR_DESCONHECIDO",
                "Algum dos setores enviados não é deste evento.",
                status_http=422,
            )
        # ⚠️ **O mesmo `id` duas vezes não é recusado por nada acima**, e o
        # estrago é silencioso: dois nomes diferentes para o mesmo setor passam
        # pelo `SETOR_DUPLICADO`, a segunda entrada sobrescreve a primeira e o
        # setor que ficou de fora da lista é **removido**. O organizador mandou
        # dois setores e recebeu um, sem erro nenhum. Reusa o `SETOR_DUPLICADO`
        # porque é a mesma frase de tela — "tem coisa repetida no formulário".
        if setor_pedido.id in editados:
            raise ErroDeDominio(
                "SETOR_DUPLICADO",
                "O mesmo setor foi enviado mais de uma vez.",
                status_http=422,
            )
        editados.add(setor_pedido.id)

    # ── Passo 7: o que sumiu da lista, e a armadilha central desta feature.
    removidos = [setor for setor in setores_atuais if setor.id not in editados]

    if removidos:
        ids_removidos = [setor.id for setor in removidos]
        # ⚠️ **`item_reserva.setor_id` e `ingresso.setor_id` são FK sem
        # `ondelete`**, e a linha de uma reserva `EXPIRADA` ou `RECUSADA` fica lá
        # para sempre. Essa reserva **passa** na trava do passo 4, porque não é
        # venda — e o `DELETE` do setor estouraria `IntegrityError` no `commit`,
        # que sobe ao handler genérico e vira `500 ERRO_INTERNO`. É a mesma "pior
        # resposta possível" que o `SETOR_DUPLICADO` existe para evitar.
        #
        # *Descartei* apagar as reservas mortas junto: destruir histórico que
        # ninguém pediu para destruir, só para poupar uma mensagem. E *descartei*
        # proibir remoção de qualquer setor: mataria o caso legítimo mais comum,
        # que é ter criado "Camarote" por engano e ninguém ter encostado nele.
        com_historico = set(
            sessao.scalars(
                select(ItemReserva.setor_id).where(
                    ItemReserva.setor_id.in_(ids_removidos)
                )
            )
        ) | set(
            sessao.scalars(
                select(Ingresso.setor_id).where(Ingresso.setor_id.in_(ids_removidos))
            )
        )

        # Por nome, e não na ordem de `id`: com dois setores impedidos, a
        # mensagem precisa ser a mesma em toda tentativa — ordem de UUID é
        # aleatória fingindo de determinística.
        for setor in sorted(removidos, key=lambda setor: setor.nome):
            if setor.id in com_historico:
                raise ErroDeDominio(
                    "SETOR_COM_HISTORICO",
                    f'O setor "{setor.nome}" já teve reservas e não pode ser '
                    "removido. Dá para alterar o nome, a capacidade e o preço "
                    "dele.",
                    status_http=422,
                )

    # ── Passo 8: aplica, em quatro fases.
    #
    # ⚠️ **As fases existem por causa do `uq_setor_evento_id_nome`**, e a spec não
    # previa isto. A restrição é conferida a cada statement, não no fim da
    # transação: trocar "Pista" e "Camarote" de nome, ou remover "Pista" e criar
    # outro setor chamado "Pista", são dois corpos perfeitamente válidos que o
    # SQLAlchemy executaria numa ordem que viola o índice no meio do caminho —
    # `IntegrityError` → `500`, na mesma família do que o passo 7 evita. A ordem
    # padrão do unit of work piora o segundo caso: ele emite os `INSERT` **antes**
    # dos `DELETE`.
    #
    # Fase A — todo setor que muda de nome passa por um nome temporário. Depois
    # dela, nenhum nome final colide com nenhum nome que ainda esteja no banco.
    # `~` mais o UUID do próprio setor é único por construção e cabe nos 80
    # caracteres da coluna; ele não sobrevive à transação.
    for setor_pedido in dados.setores:
        if setor_pedido.id is None:
            continue
        atual = atuais_por_id[setor_pedido.id]
        if atual.nome != setor_pedido.nome:
            atual.nome = f"~{atual.id}"
    sessao.flush()

    # Fase B — as remoções, pelo `cascade="all, delete-orphan"` do
    # `relationship`. O que libera o nome de um setor removido para um setor
    # novo não é a ordem das fases no código: é **o `flush` no fim desta**, que
    # emite o `DELETE` antes de a fase D sequer criar o objeto. Sem ele os dois
    # ficam pendentes até o `commit`, e aí quem escolhe a ordem é o unit of work
    # — que emite `INSERT` primeiro. Conferido desligando o `flush`: o teste
    # `..._criar_outro_com_o_mesmo_nome_nao_e_500` volta a dar `UniqueViolation`.
    for setor in removidos:
        evento.setores.remove(setor)
    sessao.flush()

    # Fase C — as alterações, já com os nomes definitivos.
    for setor_pedido in dados.setores:
        if setor_pedido.id is None:
            continue
        atual = atuais_por_id[setor_pedido.id]
        atual.nome = setor_pedido.nome
        atual.capacidade = setor_pedido.capacidade
        atual.preco_centavos = setor_pedido.preco_centavos
    sessao.flush()

    # Fase D — os setores novos, pelo `relationship`, como o `publicar()` grava.
    #
    # ⚠️ `vendidos` **não** é passado, e não pode passar a ser: o
    # `server_default=text("0")` da Story 2.3 é quem responde por ele. Escrever
    # `vendidos=0` aqui funcionaria hoje e criaria uma segunda fonte para o mesmo
    # valor — e, ao contrário do `publicar()`, esta rota roda sobre um evento em
    # que o número já significa alguma coisa.
    for setor_pedido in dados.setores:
        if setor_pedido.id is not None:
            continue
        evento.setores.append(
            Setor(
                nome=setor_pedido.nome,
                capacidade=setor_pedido.capacidade,
                preco_centavos=setor_pedido.preco_centavos,
            )
        )

    evento.data_hora = dados.data_hora
    evento.data_hora_fim = dados.data_hora_fim
    # A escala inteira, substituída: o `PUT` manda o estado final, e o
    # SQLAlchemy resolve a diferença em `evento_portaria`. `publicado_em` **não**
    # se toca — editar não é republicar, e mexer no carimbo faria o evento pular
    # de lugar em qualquer coisa que um dia ordene por ele.
    evento.portarias = escalados

    sessao.commit()

    # ⚠️ **Relê do banco, e não devolve os objetos da transação.** Esta é a forma
    # exata do bug do code review da Epic 3: a colheita do passo 3 escreveu
    # `vendidos` com `synchronize_session=False`, e com `expire_on_commit=False`
    # no `SessaoLocal` o `commit` não expira nada — o corpo da resposta sairia com
    # o `vendidos` de antes da expiração, enquanto o banco tem o certo. O
    # `expire_all` é o que faz esta resposta e o `GET` seguinte dizerem a mesma
    # coisa.
    sessao.expire_all()
    return obter_do_organizador(sessao, organizador, evento_id)


def excluir(sessao: Session, organizador: Usuario, evento_id: UUID) -> None:
    """Apaga um evento que **ainda não vendeu**, com o rastro morto dele junto.

    A terceira e última rota de escrita do organizador
    (`docs/techspec-editar-evento.md`, commit 3).

    **Excluir apaga o rastro morto, e isso reverte o que o `atualizar` decide
    três funções acima.** Lá, remover um setor com histórico é recusado
    (`SETOR_COM_HISTORICO`) para não destruir registro que ninguém pediu para
    destruir — e aquilo continua valendo, porque lá o evento permanece e o
    histórico continua tendo dono. Aqui o dono vai embora inteiro: uma reserva
    `EXPIRADA` de um evento que não existe mais não é histórico, é linha órfã
    apontando para um nome que ninguém consegue ler.

    *Descartei* um `EVENTO_COM_HISTORICO` simétrico ao do setor: seria beco sem
    saída — um checkout abandonado uma vez travaria a exclusão para sempre, e ao
    contrário do setor, que dava para renomear em vez de remover, não sobraria
    saída nenhuma. *Descartei também* o soft delete com `removido_em`: preserva
    tudo e é reversível, mas custa migração mais um filtro em **toda** leitura do
    sistema — as quatro públicas, as três do organizador, reserva, ingresso,
    portaria e o link compartilhado. Cada leitura esquecida seria um evento
    fantasma vazando numa tela.

    ⚠️ **A trava é a mesma da edição, e é a única: `vendidos == 0`.** Show que já
    aconteceu **pode** ser excluído, ao contrário do que o `atualizar` faz — e a
    assimetria é deliberada. O motivo de lá é específico do verbo: editar a data
    de um show passado o faria reaparecer na programação pública; excluí-lo não
    faz nada reaparecer, e é justamente o caso em que a exclusão é faxina.
    Recusar prenderia todo evento antigo em `Meus eventos` para sempre.

    Devolve `None`: a rota responde `204`, e não há estado novo para a tela
    aprender além de "não existe mais".
    """
    # Passo 1 — o mesmo `404` da leitura, pela mesma função, byte a byte igual
    # para "não existe" e "não é seu". Excluir duas vezes cai aqui na segunda.
    evento = obter_do_organizador(sessao, organizador, evento_id)

    # Passos 2, 3 e 4 — os mesmos três do `atualizar`, pela mesma função. É essa
    # igualdade que impede as duas rotas de discordarem sobre o que é "vendeu".
    # Só a frase muda, porque o verbo mudou.
    _travar_setores_e_exigir_sem_venda(
        sessao,
        evento,
        "Este evento já vendeu ingressos e não pode mais ser excluído.",
    )

    # ⚠️ **Passo 5 — a `validacao` é a que passa batido**, e é a única das três FKs
    # sem `ondelete` que ninguém associa a "excluir evento": ela nasce na porta.
    # A tentativa frustrada é gravada **mesmo quando o código não resolve para
    # ingresso nenhum** (`services/ingresso.py`), então ela existe em evento que
    # nunca vendeu nada — que é exatamente o único evento que esta rota consegue
    # apagar. Sem esta linha, o `500` só aparece depois de alguém ter apontado a
    # câmera para um QR errado.
    sessao.execute(
        delete(Validacao)
        .where(Validacao.evento_id == evento.id)
        .execution_options(synchronize_session=False)
    )

    # ⚠️ **Passo 6 — o filtro `estado != 'PAGA'` é de propósito, mesmo sendo
    # impossível encontrar uma reserva paga aqui.** Ingresso só nasce de reserva
    # paga, e `vendidos` **nunca** volta de uma paga — só a expiração devolve
    # estoque, e ela só toca `PENDENTE`. Logo venda paga implica `vendidos > 0`, e
    # a trava do passo 4 já recusou.
    #
    # Ele existe para o dia em que essa cadeia quebrar: sem o filtro, o bug vira
    # "a exclusão apagou uma venda"; com ele, a FK sem `ondelete` de
    # `ingresso.evento_id` segura, a transação inteira volta e nada é destruído.
    # Trocar um `500` por um apagamento silencioso de venda seria o pior negócio
    # desta feature — e é pelo mesmo motivo que **`ingresso` não é apagado em
    # lugar nenhum daqui**.
    #
    # `item_reserva` cai junto pelo `ondelete="CASCADE"` do `reserva_id`, no
    # banco: é o caso feliz do mapa de chaves estrangeiras.
    sessao.execute(
        delete(Reserva)
        .where(
            Reserva.evento_id == evento.id,
            Reserva.estado != EstadoReserva.PAGA.value,
        )
        .execution_options(synchronize_session=False)
    )

    # Passo 7 — a fronteira explícita entre "o rastro morto já foi" e "agora o
    # evento vai".
    #
    # ⚠️ **A spec o descreve como "não opcional", e medindo eu não confirmei
    # isso** (14/08/2026): desliguei este `flush` e os 85 testes continuaram
    # verdes. O motivo é que os dois `sessao.execute(delete(...))` acima são Core,
    # e Core **executa na hora** — não entra na fila do unit of work, ao contrário
    # do `evento.setores.remove()` da fase B do `atualizar`, que é ORM e onde o
    # flush **é** comprovadamente indispensável (desligá-lo lá derruba um teste).
    # As duas situações se parecem no texto e não são a mesma.
    #
    # **Fica assim mesmo**, e não por superstição: ele custa nada, escreve a
    # ordem em vez de deixá-la depender de "Core executa na hora" — que é
    # verdade sobre a biblioteca, não sobre esta função —, e o dia em que um
    # destes dois `DELETE` virar ORM é o dia em que a ausência dele passaria a
    # ser um `500` sem teste que o pegue.
    sessao.flush()

    # Passo 8 — `setor` e `evento_portaria` caem pelo `ondelete="CASCADE"` que os
    # dois declaram desde a Story 2.3.
    #
    # ⚠️ **Nada de mexer no `cascade` dos `relationship` para "ajudar" aqui.** O
    # `cascade="all, delete-orphan"` de `evento.setores` é o mesmo que a fase B do
    # `atualizar` usa para remover um setor, e afrouxá-lo reabriria lá o caminho
    # de um setor virar órfão em vez de apagado.
    sessao.delete(evento)
    sessao.commit()


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


def evento_encerrado(evento: Evento, agora: datetime) -> bool:
    """O show já acabou? (techspec `docs/techspec-fim-do-evento.md`)

    **Uma linha, e ela existe para ter dois chamadores.** `porta_aberta` logo
    abaixo e `estado_do_turno` mais adiante saem daqui, e é essa identidade que
    impede a dependência de recusar um turno que a tela desenha como aberto —
    ou, pior, a tela travar um turno que a rota ainda aceita. Escrever
    `data_hora_fim <= agora` nos dois lugares seria a mesma divergência que a
    Story 5.2 corrigiu na borda de abrir, reintroduzida na borda de fechar.

    ⚠️ **Sem tolerância depois do fim, e a ausência é a decisão.** *Descartei*
    uma `TOLERANCIA_APOS_O_FIM` simétrica às duas horas de `ABERTURA_DOS_PORTOES`:
    ela cobriria o retardatário, e o preço seria o sistema discordando do número
    que o organizador acabou de digitar — o ingresso valeria por X horas a mais do
    que a tela do cliente diz. A folga mora na hora declarada: quem quiser margem
    marca 03h em vez de 02h.

    `<=` e não `<`: no instante exato do término o show acabou. É a mesma
    convenção do `data_hora <= agora` do `EVENTO_NO_PASSADO`.
    """
    return evento.data_hora_fim <= agora


def porta_aberta(evento: Evento, agora: datetime) -> bool:
    """O portão deste evento está aberto **agora**? (Story 5.2)

    **A única fonte da resposta**, e é isso que ela existe para ser: a dependência
    `exigir_porta_aberta` recusa `403` com ela, e o `estado_do_turno` que a tela
    lê sai da mesma dupla de comparações. Duas implementações da mesma janela —
    uma na tela, outra na rota — discordariam no primeiro ajuste de uma das duas,
    e o sintoma seria o pior possível: o item aparece clicável e a validação
    recusa.

    **`agora` é parâmetro, e não `datetime.now()` aqui dentro.** Quem chama já
    leu o relógio uma vez para a resposta inteira; ler de novo por item faria
    dois turnos na mesma borda saírem com vereditos diferentes. De quebra, é o
    que torna a janela testável sem congelar o relógio do processo.

    ⚠️ **Ela ganhou teto em 14/08/2026**, e o comentário de `ABERTURA_DOS_PORTOES`
    dizia o contrário: *"não há fechamento, de propósito (…) sem contar que este
    projeto não tem coluna de duração nenhuma."* A coluna passou a existir
    (`evento.data_hora_fim`), e o que a ausência de teto custava era visível em
    produção — o turno de um show da semana passada continuava na lista da
    portaria, clicável e validável. O argumento de então — *"o show acaba e ainda
    há gente entrando"* — continua de pé e é atendido pela hora que o organizador
    declara, não por uma porta que nunca fecha.
    """
    return (
        evento.data_hora - ABERTURA_DOS_PORTOES <= agora
        and not evento_encerrado(evento, agora)
    )


def estado_do_turno(evento: Evento, agora: datetime) -> EstadoDoTurno:
    """Onde este turno está na noite — os três estados que a tela desenha.

    ⚠️ **`ENCERRADO` é conferido primeiro**, e a ordem não é estética: as duas
    condições são simultaneamente verdadeiras para um evento cujo término foi
    digitado antes do início e escapou das recusas do service. Na ordem inversa,
    um show que acabou responderia `NAO_COMECOU` — a tela diria "o evento ainda
    não começou" sobre um show de ontem. É a **mesma** ordem das duas recusas da
    dependência `exigir_porta_aberta`, e ela é a mesma nos dois lugares de
    propósito.

    **Sai da mesma `evento_encerrado` que a `porta_aberta` usa**, e é isso que
    impede a tela e a rota de divergirem: se uma disser aberto e a outra
    encerrado, o item aparece clicável e a validação bate na porta.
    """
    if evento_encerrado(evento, agora):
        return EstadoDoTurno.ENCERRADO
    if porta_aberta(evento, agora):
        return EstadoDoTurno.ABERTO
    return EstadoDoTurno.NAO_COMECOU


def montar_turno(
    evento: Evento, entradas: int, agora: datetime | None = None
) -> TurnoDaPortaria:
    """Projeta o `Evento` no contrato da portaria, com o `estado` calculado.

    Campo a campo, e não `model_validate(evento)`: nem `estado` nem `entradas` são
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
        estado=estado_do_turno(evento, agora or datetime.now(timezone.utc)),
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
    #
    # ⚠️ **A igualdade é sobre o normalizado, e isso conserta um filtro que
    # escondia evento** (13/08/2026). A Ticketmaster manda a mesma cidade em mais
    # de uma grafia — `São Paulo` em seis eventos e `Sao Paulo`, sem til, num
    # sétimo —, e nós copiamos o que vem (AD-1). Com `Evento.cidade == "São
    # Paulo"` o sétimo sumia da lista, **sem nada na tela dizendo que ele
    # existia**: o pior tipo de defeito de filtro, porque o resultado parece
    # completo. Comparar `unaccent(lower(...))` dos dois lados junta as grafias
    # sem reescrever o que está gravado.
    #
    # É a mesma normalização que a `listar_cidades_em_cartaz` usa para montar os
    # chips — as duas precisam concordar, senão o chip oferece uma cidade que o
    # filtro não acha.
    if cidade.strip():
        condicoes.append(
            _cidade_normalizada(Evento.cidade)
            == _cidade_normalizada(cidade.strip())
        )

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


def _cidade_normalizada(valor):
    """A chave que junta as grafias da mesma cidade — `unaccent` mais `lower`.

    **Uma função porque são dois consumidores que precisam concordar**: o filtro
    de `listar_programacao` e o agrupamento de `listar_cidades_em_cartaz`. Se as
    duas normalizações divergirem, o chip passa a oferecer uma cidade que o
    filtro não acha — e o sintoma seria uma lista vazia depois de um clique num
    chip que o próprio sistema desenhou.

    ⚠️ **`unaccent` é do Postgres, não do Python.** A extensão já está instalada
    desde a Story 3.2, que a usa na busca por termo; fazer a dobra em Python
    obrigaria a trazer a coluna inteira para a memória antes de comparar.
    """
    return func.unaccent(func.lower(valor))


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

    ⚠️ **As grafias da mesma cidade viram um chip só** (13/08/2026). A
    Ticketmaster não normaliza o `venue.city.name`: o banco de desenvolvimento
    tem `São Paulo` em seis eventos e `Sao Paulo`, sem til, num sétimo, e nós
    copiamos o que vem (AD-1). Um `DISTINCT` simples via duas strings diferentes
    e desenhava **dois chips com o mesmo nome na tela**, um deles achando um
    evento só.

    A dobra é por `unaccent(lower(...))`, e o que se mostra é a **grafia mais
    frequente** — `São Paulo`, e não `Sao Paulo`.

    ⚠️ **O empate não desempata por ordem alfabética**, e a primeira versão
    desta função desempatava: `ORDER BY cidade` parece a escolha óbvia e entrega
    o rótulo da tela ao *collation* do banco. Com uma grafia por conta cada,
    `rio de janeiro` vinha antes de `Rio de Janeiro` — porque no glibc a
    minúscula precede a maiúscula no desempate — e o chip aparecia em caixa
    baixa. Pior: isso muda com a configuração do cluster, então o mesmo dado
    daria rótulos diferentes no meu banco, no de teste e na Railway.

    O critério agora é explícito: entre grafias empatadas, **ganha a que tem
    maiúscula**, que é a que alguém digitou como nome próprio. Sem depender de
    ordenação de texto nenhuma.

    **A alternativa descartada foi normalizar na publicação**, reescrevendo a
    cidade para uma grafia canônica antes de gravar. Ela conserta o futuro e
    deixa o passado como está — os dois `Sao/São Paulo` de hoje continuariam
    separados até alguém rodar um `UPDATE` — e, pior, decide no ato da gravação
    qual grafia é a certa, sem ter como saber: a primeira a chegar venceria, e
    poderia ser a sem acento. Aqui a dobra é de leitura, o dado bruto continua
    intacto, e a grafia mostrada acompanha o que o catálogo majoritariamente diz.
    """
    agora = datetime.now(timezone.utc)

    # Uma contagem por grafia, para a de fora saber qual mostrar.
    contagem = (
        select(
            Evento.cidade.label("cidade"),
            _cidade_normalizada(Evento.cidade).label("chave"),
            func.count().label("quantos"),
        )
        .where(
            Evento.publicado_em.is_not(None),
            Evento.data_hora >= agora,
            Evento.cidade.is_not(None),
        )
        .group_by(Evento.cidade)
        .subquery()
    )

    return list(
        sessao.scalars(
            # `DISTINCT ON (chave)` — específico do Postgres, e é ele que permite
            # escolher **qual linha** sobrevive de cada grupo, coisa que um
            # `DISTINCT` comum não faz. O `order_by` abaixo é quem decide: a
            # regra do desempate mora nele, não numa lambda em Python.
            select(contagem.c.cidade)
            .distinct(contagem.c.chave)
            # Alfabética pela chave sem acento, e não por quantidade de shows: a
            # ordem da **lista** precisa ser estável entre visitas para o chip
            # não trocar de lugar debaixo do cursor a cada evento publicado. Os
            # dois termos seguintes escolhem a grafia **dentro** de cada grupo,
            # que é o que o `DISTINCT ON` exige.
            .order_by(
                contagem.c.chave,
                contagem.c.quantos.desc(),
                # `cidade = lower(cidade)` é verdadeiro só para a grafia toda em
                # caixa baixa, e `FALSE` ordena antes de `TRUE` no Postgres — ou
                # seja, a grafia com maiúscula ganha. É o desempate explicado no
                # docstring, e o motivo de não haver `order_by(cidade)` aqui.
                contagem.c.cidade == func.lower(contagem.c.cidade),
            )
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
