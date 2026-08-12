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
from app.models.evento import Evento, Setor
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.evento import (
    EventoEntrada,
    EventoNaProgramacao,
    EventoResumo,
    PeriodoDaProgramacao,
)


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
    """
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
        # ⚠️ **`unaccent` do Postgres, e não normalização em Python** (decisão
        # do Igor): `sao paulo` precisa achar `São Paulo` porque é assim que as
        # pessoas digitam no celular. A extensão é habilitada pela migração
        # `06c1ad5ac276`, e sem ela esta linha estoura com `function
        # unaccent(text) does not exist` — não é a busca que falha, é a raiz do
        # produto que vira `500`.
        #
        # Nos **dois lados** da comparação: sem `unaccent` no padrão, quem
        # digitasse `SÃO` não acharia um evento gravado sem acento.
        padrao = func.unaccent(f"%{_escapar_curingas(termo_limpo)}%")
        condicoes.append(
            or_(
                *(
                    # `escape="\\"` é o que faz o escape do helper valer: sem
                    # ele o Postgres lê a contrabarra como caractere comum.
                    func.unaccent(coluna).ilike(padrao, escape="\\")
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
