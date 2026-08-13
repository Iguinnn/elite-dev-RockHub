"""O ingresso como agregado próprio: "Meus ingressos", o link e a porta.

⚠️ **Este módulo lê, escreve `share_token` desde a 4.3, `usado_em` desde a 5.2 e
insere em `validacao` desde a 5.6. Ele nunca cria ingresso.** A emissão é do
`services/reserva.py`, dentro da transação que marca a reserva `PAGA` (AD-14) —
mesmo aviso que aquele arquivo carrega sobre si, em espelho. Um `INSERT INTO
ingresso` fora daquela transação quebraria a garantia inteira da Epic 3. A
`validacao` é outra tabela e não é exceção nenhuma a isso: ela registra o que
aconteceu **com** o ingresso, e não o cria.

**A contagem do turno mora aqui, e não num `services/validacao.py`.** O agregado
continua sendo o ingresso — a `validacao` é o registro do que aconteceu com ele —,
e o critério do projeto é agrupar por agregado, não por tabela. Foi ele que
recusou um `services/portaria.py` na techspec anterior, e vale igual aqui: um
arquivo por tabela deixaria o `validar` chamando o vizinho a cada linha.

**Por que arquivo próprio, e não mais uma função em `services/reserva.py`.**
O ingresso tem vida depois de a reserva sair de cena — é lido por várias
compras de uma vez (`GET /ingressos`), compartilhado por link (Epic 4) e
validado na porta (Epic 5) — e `reserva.py` já passa de 800 linhas cobrindo o
agregado dele. Agrupar por agregado, não por arquivo que cresce.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.erros import ErroDeDominio
from app.core.seguranca import conferir_codigo, gerar_share_token, normalizar_codigo
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.models.validacao import Validacao, Veredito
from app.schemas.ingresso import (
    IngressoDetalhe,
    IngressoNaLista,
    RecusasDoTurno,
    ResultadoDaValidacao,
)


def listar(sessao: Session, cliente: Usuario) -> list[IngressoNaLista]:
    """Todos os ingressos de todas as reservas pagas de quem está na sessão.

    **`join(Reserva)`, e não um `cliente_id` em `ingresso`** (techspec da 4.1).
    `reserva_id` já é indexado desde a Story 3.9 exatamente para este `where`;
    uma coluna atalho duplicaria o dono em duas tabelas, com o dia em que
    discordam já marcado.

    **Sem filtro por `reserva.estado`.** Ingresso só nasce dentro da transação
    que marca a reserva `PAGA` (AD-14) — o estado da reserva não é uma segunda
    condição desta consulta, é uma consequência de a linha existir.

    Ordenado por `evento.data_hora` **crescente**: o próximo show primeiro. A
    tela corta em *Ativos*/*Utilizados* por `usado_em IS NULL`; esta função
    não sabe de blocos, só devolve a lista inteira, chapada — o mesmo molde do
    `listar_meus_eventos` da 2.6.

    Lista vazia é resposta legítima, nunca uma falha: quem nunca comprou tem
    zero ingressos, e isso não é diferente de ter zero eventos publicados.
    """
    linhas = sessao.execute(
        select(Ingresso, Evento, Setor)
        .join(Reserva, Reserva.id == Ingresso.reserva_id)
        .join(Evento, Evento.id == Ingresso.evento_id)
        .join(Setor, Setor.id == Ingresso.setor_id)
        .where(Reserva.cliente_id == cliente.id)
        .order_by(Evento.data_hora)
    ).all()

    return [
        IngressoNaLista(
            id=ingresso.id,
            evento_id=evento.id,
            evento_nome=evento.nome,
            evento_data_hora=evento.data_hora,
            evento_local=evento.local,
            setor_nome=setor.nome,
            usado_em=ingresso.usado_em,
        )
        for ingresso, evento, setor in linhas
    ]


def _carregar_do_cliente(
    sessao: Session, cliente: Usuario, ingresso_id: UUID
) -> tuple[Ingresso, Evento, Setor, Usuario]:
    """O ingresso de quem está na sessão, com evento, setor e a conta — ou `404`.

    **As duas condições no mesmo `where`**, e não um `get()` seguido de um
    `if`: mesma disciplina do `obter()` de `services/reserva.py`. "Só vejo o
    que é meu" fica verdade por construção, não por quem lembrar de checar.

    **Um `404` só, para "não existe" e para "não é seu"** — nunca `403`.
    Distinguir os dois transformaria a rota num oráculo de "esse UUID é
    ingresso de alguém?", a mesma disciplina do `RESERVA_NAO_ENCONTRADA`.

    ⚠️ **Toda rota do dono passa por aqui**, e é isso que a função protege: a
    Story 4.3 acrescentou a segunda (`compartilhar`) e a 4.4 acrescenta a
    terceira. Com o `where` copiado em cada uma, a primeira que esquecesse o
    `Reserva.cliente_id` deixaria alguém compartilhar — ou revogar — o ingresso
    de outra pessoa, e o defeito estaria numa linha idêntica a duas que estão
    certas. Rota nova do dono **usa esta função**; não escreve o `where` de novo.

    ⚠️ **"Do dono" é a parte que importa da frase acima, e a Story 5.2 é a
    primeira exceção.** O `validar` deste arquivo **não** passa por aqui, e nem
    poderia: quem chama é um terceiro autorizado — a portaria escalada —, não há
    dono a conferir, e o `where` de lá é o **código**, não o `cliente_id`. Quem
    autoriza aquele caminho é a dependência `exigir_porta_aberta`, do AD-7. O
    aviso está escrito porque a leitura natural desta frase é a errada: sem ele,
    o próximo leitor supõe que todo `SELECT` de ingresso do arquivo é protegido
    por esta função, e essa proteção não está lá.

    Devolve o objeto ORM, e não o schema: quem escreve na linha (`compartilhar`)
    precisa da entidade viva na sessão, não de uma cópia.

    ⚠️ **O `Usuario` vem do join, e não do parâmetro `cliente`.** Neste caminho os
    dois são a mesma pessoa — o `where` filtra por `Reserva.cliente_id` —, e
    devolver `cliente` daria o mesmo nome com uma linha menos. O join é para o
    titular do canhoto sair da **reserva** por construção: no dia em que uma rota
    carregar ingresso sem ser o dono, ela mostra o nome de quem comprou em vez do
    de quem está olhando, sem ninguém precisar lembrar da diferença.
    """
    linha = sessao.execute(
        select(Ingresso, Evento, Setor, Usuario)
        .join(Reserva, Reserva.id == Ingresso.reserva_id)
        .join(Evento, Evento.id == Ingresso.evento_id)
        .join(Setor, Setor.id == Ingresso.setor_id)
        .join(Usuario, Usuario.id == Reserva.cliente_id)
        .where(Ingresso.id == ingresso_id, Reserva.cliente_id == cliente.id)
    ).first()

    if linha is None:
        raise ErroDeDominio(
            "INGRESSO_NAO_ENCONTRADO",
            "Esse ingresso não existe ou não é seu.",
            status_http=404,
        )

    ingresso, evento, setor, usuario = linha
    return ingresso, evento, setor, usuario


def _montar_detalhe(
    ingresso: Ingresso, evento: Evento, setor: Setor, usuario: Usuario
) -> IngressoDetalhe:
    """O canhoto cheio, montado a partir das quatro entidades.

    `codigo` é a coluna, lida **sem recalcular**: a validação da portaria (Epic 5)
    é quem sempre recalcula (AD-5); estas rotas só montam o texto que a tela
    desenha em QR.

    ⚠️ **`titular_nome` vem de `usuario.nome`, e não de `ingresso.pagador_nome`**
    (decisão do Igor, techspec `docs/techspec-codigo-curto.md`). O ingresso está
    no nome de quem tem a conta; a coluna guarda quem **pagou**, que pode ser
    outra pessoa — a namorada compra na conta dela, eu ponho meu cartão. Se o
    canhoto mostrasse o pagador, a tela de quem chega e a de quem valida diriam
    nomes diferentes do mesmo ingresso, e a conferência com o documento ficaria
    sem resposta.

    ⚠️ **Um lugar só monta o canhoto, e ele serve a rota pública também.** As
    três rotas do ingresso respondem `IngressoDetalhe` pelo mesmo caminho, e é
    isso que garante que quem abre o link compartilhado vê **o mesmo canhoto**
    que o dono — que é o requisito da Story 4.3, não um efeito colateral. A
    consequência é a que o docstring do schema já anuncia: campo novo aqui
    atravessa para quem não tem conta.
    """
    return IngressoDetalhe(
        id=ingresso.id,
        evento_nome=evento.nome,
        evento_data_hora=evento.data_hora,
        evento_local=evento.local,
        evento_cidade=evento.cidade,
        setor_nome=setor.nome,
        titular_nome=usuario.nome,
        codigo=ingresso.codigo,
        usado_em=ingresso.usado_em,
        share_token=ingresso.share_token,
    )


def obter(sessao: Session, cliente: Usuario, ingresso_id: UUID) -> IngressoDetalhe:
    """O canhoto cheio de um ingresso de quem está na sessão — a Story 4.2.

    **Devolve o `share_token` sempre que houver um** (Story 4.3): o dono
    reencontra o próprio link ao voltar à tela, sem precisar compartilhar de
    novo — o que geraria token novo em quem lesse a resposta como um comando.
    """
    return _montar_detalhe(*_carregar_do_cliente(sessao, cliente, ingresso_id))


def compartilhar(
    sessao: Session, cliente: Usuario, ingresso_id: UUID
) -> IngressoDetalhe:
    """Gera — ou devolve — o link público de um ingresso meu (Story 4.3).

    ⚠️ **Idempotente: com link ativo, devolve o mesmo token e não escreve
    nada.** Gerar um token novo a cada clique transformaria "compartilhar de
    novo" numa revogação silenciosa, cortando o acesso de quem já recebeu o
    link **sem** a confirmação que o AC da Story 4.4 existe justamente para
    exigir. Revogar é a única ação que invalida link, e é a única que pergunta
    antes.

    **Responde o `IngressoDetalhe` inteiro**, e não só o token: a ilha da tela
    troca o estado todo em vez de remendar um campo, e não precisa saber juntar
    duas respostas.

    O `404` de ingresso inexistente ou de outra pessoa vem do
    `_carregar_do_cliente`, com o mesmo código e a mesma frase do `obter`.

    ⚠️ **A gravação é um `UPDATE` condicional, no precedente do AD-3** — achado
    do code review da Epic 4. Ler `share_token IS None` em Python e gravar
    depois é um par leitura→escrita sem trava: com o mesmo ingresso aberto em
    duas abas, as duas transações leem `NULL`, a primeira grava o token A e a
    segunda grava B por cima. O banco fica com B, e a aba que gravou A recebeu
    `200` com A — que não existe mais. A pessoa manda `/i/A` por WhatsApp e
    quem abre lê "esse link não vale mais", sem ninguém ter revogado nada.
    O `WHERE share_token IS NULL` faz a segunda transação casar zero linhas, e
    as duas abas saem com o mesmo token.

    ⚠️ **O `refresh` não é opcional.** `SessaoLocal` usa `expire_on_commit=
    False`, então o objeto em memória continua com `share_token = None` depois
    do commit — sem reler a linha, quem perde a corrida devolveria `null` e
    quem ganha devolveria um token que o `_montar_detalhe` não enxerga. É a
    mesma armadilha de sessão que o code review da Epic 3 encontrou no
    pagamento, aqui pelo lado oposto: lá o objeto expirava, aqui ele não
    expira.

    *Descartei* `SELECT ... FOR UPDATE` no `_carregar_do_cliente`: aquele
    helper serve também `obter` e `revogar_compartilhamento`, e travar linha
    nas duas leituras puras seria cobrar de toda a epic o preço de uma corrida
    que só existe aqui.
    """
    ingresso, evento, setor, usuario = _carregar_do_cliente(
        sessao, cliente, ingresso_id
    )

    if ingresso.share_token is None:
        sessao.execute(
            update(Ingresso)
            .where(Ingresso.id == ingresso.id, Ingresso.share_token.is_(None))
            .values(share_token=gerar_share_token())
        )
        sessao.commit()
        # Relê a linha: pode ter sido o token desta transação que venceu, ou o
        # de outra que chegou primeiro. As duas respostas são o valor gravado.
        sessao.refresh(ingresso)

    return _montar_detalhe(ingresso, evento, setor, usuario)


def revogar_compartilhamento(
    sessao: Session, cliente: Usuario, ingresso_id: UUID
) -> None:
    """Apaga o link público de um ingresso meu — a Story 4.4.

    **Grava `NULL`, e não um estado "revogado".** A coluna volta a ser
    exatamente o que era antes de o link existir, e é isso que torna token
    revogado indistinguível de token que nunca existiu na rota pública: mesmo
    `404`, mesma frase. Uma marca de "isto já foi um link" transformaria a
    revogação num aviso de que existiu algo ali.

    ⚠️ **Idempotente: sem link, não faz nada e não é erro.** Quem pediu para o
    link não valer mais obteve exatamente isso, e o `DELETE` do HTTP é
    idempotente por definição. Um `404` ou um `409` na segunda chamada faria a
    tela ter de tratar um caso que, para quem clicou, é sucesso.

    **Compartilhar de novo depois disto gera um token diferente**, porque o
    `compartilhar` só reaproveita o que existe — e é aqui que o link antigo
    morre de verdade: ninguém volta a recebê-lo.

    Devolve `None`: a rota responde `204`, e não há corpo a montar. O `404` de
    ingresso inexistente ou de outra pessoa vem do `_carregar_do_cliente`, o
    mesmo das duas irmãs.
    """
    ingresso, _, _, _ = _carregar_do_cliente(sessao, cliente, ingresso_id)

    if ingresso.share_token is not None:
        ingresso.share_token = None
        sessao.commit()


def obter_por_share_token(sessao: Session, token: str) -> IngressoDetalhe:
    """O canhoto que um link compartilhado abre — **sem sessão nenhuma** (4.3).

    A única leitura de ingresso do projeto que não conhece quem está chamando:
    o `where` é o `share_token` e nada mais, e é por isso que a rota mora em
    `publico.py`, cujo critério declarado é a ausência de autenticação.

    ⚠️ **Token revogado e token que nunca existiu são indistinguíveis** — mesmo
    status, mesmo código, mesma frase. É o que faz a revogação da Story 4.4 ser
    um corte, e não um aviso de que existiu algo ali.

    ⚠️ **Nada de `conferir_codigo` aqui, e a ausência é a decisão.** O
    `share_token` **não** autentica coisa alguma e não substitui o HMAC do AD-5:
    isto é visualização (AD-8), e quem recalcula a assinatura é a portaria, na
    Epic 5. Validar assinatura neste caminho daria a impressão de que o token
    prova alguma coisa sobre o ingresso.

    ⚠️ **O `join` com `Reserva` entrou aqui, e este docstring dizia o contrário**
    (techspec `docs/techspec-codigo-curto.md`). A redação antiga — *não há dono a
    conferir, e a reserva não tem nada a dizer sobre um canhoto que já existe* —
    valia enquanto o titular era uma coluna do próprio ingresso. Desde que ele
    passou a ser o nome da **conta**, a reserva é o único caminho até ela:
    `Ingresso → Reserva → Usuario`. A reserva continua não sendo consultada para
    **autorizar** nada — o `where` é o `share_token` e nada mais.

    Consequência assumida: o link compartilhado mostra o nome da conta que
    comprou, em vez do nome digitado no checkout. É a mesma classe de exposição de
    nome que ele já fazia, com outro nome dentro.
    """
    linha = sessao.execute(
        select(Ingresso, Evento, Setor, Usuario)
        .join(Reserva, Reserva.id == Ingresso.reserva_id)
        .join(Evento, Evento.id == Ingresso.evento_id)
        .join(Setor, Setor.id == Ingresso.setor_id)
        .join(Usuario, Usuario.id == Reserva.cliente_id)
        .where(Ingresso.share_token == token)
    ).first()

    if linha is None:
        raise ErroDeDominio(
            "LINK_NAO_ENCONTRADO",
            "Esse link não vale mais.",
            status_http=404,
        )

    return _montar_detalhe(*linha)


def contar_entradas_por_evento(
    sessao: Session, eventos: list[UUID]
) -> dict[UUID, int]:
    """Quantas pessoas já entraram em cada um destes eventos (Story 5.6).

    ⚠️ **A fonte é `ingresso.usado_em`, e não a tabela `validacao`.** Aquela coluna
    é escrita pelo `UPDATE` condicional do AD-6, que é atômico — ela é a verdade
    sobre quem entrou, e continua sendo mesmo que a `validacao` um dia perca uma
    linha. **Descartei** contar `VALIDO` na `validacao` para ter uma fonte só:
    seria trocar a garantia do AD-6 por uma tabela de log, e o dia em que os dois
    números divergirem é o dia em que eu quero que o `usado_em` ganhe.

    ⚠️ **Isto não é o `COUNT` que o AD-13 proíbe**, e a diferença é o que se
    conta. Lá o proibido é derivar **disponibilidade** de reserva ou ingresso —
    quanto ainda dá para vender tem dono, que é `setor.vendidos`. Aqui a pergunta
    é quantas pessoas **passaram pela porta**, que nenhuma coluna de estoque
    responde: vendidos não é entrou.

    **Uma consulta para a lista inteira, e não uma por evento.** A rota de um
    turno só chama com uma lista de um; a lista de `/portaria` chama com todos, e
    é ela que o `GROUP BY` existe para não fazer N+1 — o mesmo motivo do
    `selectinload` da programação.

    **Devolve todos os eventos pedidos, e os sem entrada nenhuma vêm com `0`.** Um
    `dict` que só traz quem tem linha obrigaria cada chamador a lembrar do
    `.get(id, 0)`, e o que esquecesse estouraria com `KeyError` no turno mais
    tranquilo do dia — aquele em que ninguém entrou ainda.
    """
    if not eventos:
        return {}

    linhas = sessao.execute(
        select(Ingresso.evento_id, func.count())
        .where(Ingresso.evento_id.in_(eventos), Ingresso.usado_em.is_not(None))
        .group_by(Ingresso.evento_id)
    ).all()

    totais = dict.fromkeys(eventos, 0)
    totais.update({evento_id: total for evento_id, total in linhas})
    return totais


def contar_recusas(sessao: Session, evento_id: UUID) -> RecusasDoTurno:
    """Os três vereditos de recusa deste evento, contados (Story 5.6).

    **A fonte é a `validacao`**, ao contrário do `entradas` logo acima, e é para
    isso que a tabela existe: `INVALIDO`, `JA_UTILIZADO` e `EVENTO_ERRADO` não
    deixam marca em coluna nenhuma do ingresso. O porquê das duas fontes está no
    docstring de `models/validacao.py`.

    **`!= VALIDO` no `where`, e não os três nomes listados.** Um quinto veredito
    inventado um dia entraria na consulta em vez de sumir dela em silêncio — e
    apareceria no `KeyError` de um teste, que é onde eu quero descobrir isso.

    ⚠️ **Veredito sem linha nenhuma sai `0`, nunca ausente.** O `GROUP BY` só
    devolve o que existe; os três `.get(..., 0)` abaixo são o que impede o
    contador de desenhar um buraco no começo do turno, quando os três são zero.
    """
    linhas = sessao.execute(
        select(Validacao.resultado, func.count())
        .where(
            Validacao.evento_id == evento_id,
            Validacao.resultado != Veredito.VALIDO.value,
        )
        .group_by(Validacao.resultado)
    ).all()

    por_resultado = {resultado: total for resultado, total in linhas}
    return RecusasDoTurno(
        invalidos=por_resultado.get(Veredito.INVALIDO.value, 0),
        ja_utilizados=por_resultado.get(Veredito.JA_UTILIZADO.value, 0),
        evento_errado=por_resultado.get(Veredito.EVENTO_ERRADO.value, 0),
    )


def _anotar(
    sessao: Session,
    portaria: Usuario,
    evento: Evento,
    resultado: Veredito,
    ingresso_id: UUID | None,
) -> None:
    """Grava a linha de auditoria e **fecha a transação** (Story 5.6).

    ⚠️ **O `commit` é daqui, e é o mesmo dos quatro caminhos.** Antes desta story
    ele morava no `validar`, depois do `UPDATE`; agora ele fecha o `INSERT` e o
    `UPDATE` **juntos**. Fora da mesma transação existiria a janela em que alguém
    entrou e o registro não saiu — ou o contrário, um registro de entrada que o
    banco desfez.

    ⚠️ **Os dois `INVALIDO` passam a tocar o banco por causa desta função**, e o
    docstring do `validar` dizia o contrário até a 5.6: o código malformado
    respondia "sem tocar no banco". A frase foi corrigida no mesmo commit — é uma
    consulta economizada que deixou de existir, e o preço declarado da trilha de
    auditoria.

    `evento.id` é o do **caminho**, nunca o do ingresso: no `EVENTO_ERRADO` os
    dois diferem de propósito, e o porquê está no comentário da coluna
    `validacao.evento_id`.

    ⚠️ **`criado_em` é escrito daqui, e não por `server_default=func.now()`.** O
    `now()` do Postgres é o instante de início da **transação**: duas linhas
    gravadas na mesma transação sairiam com o carimbo idêntico, e uma trilha cujas
    linhas não se ordenam entre si responde pior à pergunta que ela existe para
    responder. É o mesmo relógio que grava `ingresso.usado_em` no `validar`, e os
    dois registram o mesmo acontecimento.
    """
    sessao.add(
        Validacao(
            evento_id=evento.id,
            portaria_id=portaria.id,
            ingresso_id=ingresso_id,
            resultado=resultado.value,
            criado_em=datetime.now(timezone.utc),
        )
    )
    sessao.commit()


def _montar_veredito(
    sessao: Session,
    evento: Evento,
    resultado: Veredito,
    titular_nome: str | None = None,
    setor_nome: str | None = None,
    entrada_em: datetime | None = None,
) -> ResultadoDaValidacao:
    """O veredito com as duas contagens — sempre **depois** do `commit` (5.6).

    ⚠️ **As contagens são lidas depois do `commit`, nunca antes**, e esta é a
    quarta aparição desta família de armadilha no projeto (pagamento na Epic 3,
    `share_token` na 4.3, `usado_em` na 5.2). Lida antes, a contagem enxerga a
    própria linha não commitada em alguns caminhos e não em outros, e o número
    oscila de um em um sem motivo visível. Depois do `commit`, com
    `expire_on_commit=False`, a leitura é uma consulta nova e está certa.

    **Quem garante a ordem é a assinatura**: esta função não escreve nada e não
    commita nada — quem faz as duas coisas é o `_anotar`, que roda antes. Chamar
    esta primeiro devolveria números de uma tentativa atrás, e é a única forma de
    errar que sobrou.
    """
    return ResultadoDaValidacao(
        resultado=resultado,
        titular_nome=titular_nome,
        setor_nome=setor_nome,
        entrada_em=entrada_em,
        entradas=contar_entradas_por_evento(sessao, [evento.id])[evento.id],
        recusas=contar_recusas(sessao, evento.id),
    )


def validar(
    sessao: Session, portaria: Usuario, evento: Evento, codigo: str
) -> ResultadoDaValidacao:
    """O veredito da porta, e a queima do ingresso quando ele vale (Story 5.2).

    ⚠️ **A primeira função deste arquivo que não passa pelo
    `_carregar_do_cliente`**, e o docstring daquele diz "toda rota do dono passa
    por aqui". Aqui não há dono: quem chama é um terceiro autorizado, e o `where`
    é o código, não o `cliente_id`. Quem autoriza é a dependência
    `exigir_porta_aberta` (AD-7), **antes** de esta função existir na requisição.

    **Os quatro vereditos são resposta de sucesso**, e o motivo inteiro está no
    docstring do `ResultadoDaValidacao`: recusar entrada é o trabalho da portaria
    dando certo.

    ⚠️ **A ordem das etapas não mudou na Story 5.6, e não pode mudar.** O
    `EVENTO_ERRADO` continua **antes** do `UPDATE`, e a assinatura continua sendo
    conferida contra o `evento_id` **do ingresso**. Acrescentar escrita no meio é
    exatamente o tipo de edição que embaralha ordem sem querer; o que entrou foram
    duas linhas por desfecho, no fim de cada ramo, e nada entre as etapas.

    A ordem das etapas é a garantia, e cada troca dela tem consequência:

    1. `normalizar_codigo` → `None` ⇒ `INVALIDO`.
       ⚠️ **Este caminho tocava o banco zero vezes, e a Story 5.6 acabou com
       isso.** A redação anterior se gabava de "sem tocar no banco" — uma consulta
       economizada no caminho mais sensível a tempo do produto. Com a tabela
       `validacao`, ele grava uma linha como os outros três: contar os quatro
       vereditos exige guardar os quatro, e um `INVALIDO` que não deixasse
       registro sumiria do contador exatamente quando alguém tenta entender por
       que a fila parou. É o preço declarado da trilha de auditoria.
    2. O ingresso, achado **pelo** código. Sem linha ⇒ `INVALIDO`.
       ⚠️ Código bem formado que não é de ingresso nenhum é colapsado com
       assinatura divergente de propósito: o `EXPERIENCE.md` fixa quatro
       vereditos, e "assinatura não confere" continua verdadeiro — sem linha,
       não há assinatura que confira. Um quinto veredito transformaria a rota
       num oráculo de "esse código existe?".
    3. `conferir_codigo` recalculando o HMAC das colunas (AD-5).
       ⚠️ **Contra o `evento_id` do ingresso, nunca contra o do caminho.**
       Conferir contra o contexto faria um código legítimo de outro show falhar
       como `INVALIDO` em vez de `EVENTO_ERRADO` — dois vereditos trocados, e
       quem está na fila recebe a palavra errada.
    4. Evento diferente ⇒ `EVENTO_ERRADO`.
       ⚠️ **Antes do `UPDATE`, e isso não é ordem estética:** invertido, o
       ingresso do outro show seria **queimado** por uma portaria que nem podia
       lê-lo.
    5. O `UPDATE` condicional do AD-6, e a decisão é o `rowcount`.

    ⚠️ **A dupla validação não se decide em Python.** `if ingresso.usado_em is
    None` antes de gravar é a linha confortável que passa em todo teste
    sequencial e perde a corrida — dois leitores no mesmo instante leem `NULL` e
    os dois deixam entrar. É a mesma armadilha do `setor.vendidos` no AD-3, com
    a mesma resposta: a condição vai no `where`, e quem responde é o banco.

    ⚠️ **O `RETURNING` não é enfeite.** `SessaoLocal` usa
    `expire_on_commit=False`, então o objeto em memória continua com `usado_em =
    None` depois do `UPDATE`: sem ele, o caminho do `VALIDO` responderia
    `entrada_em: null`. E é por isso que o `JA_UTILIZADO` **relê a linha** — ali
    não houve `RETURNING` nenhum, e a hora que a fila precisa ouvir é a da
    primeira entrada. Terceira aparição desta armadilha no projeto, depois do
    pagamento na Epic 3 e do `share_token` na 4.3.
    """
    normalizado = normalizar_codigo(codigo)
    if normalizado is None:
        # `ingresso_id` nulo, e é um dos dois casos em que ele é: não há ingresso
        # a apontar porque não houve código legível. O outro é o `linha is None`
        # logo abaixo — a coluna anulável é a distinção que sobra entre os dois, e
        # ela basta.
        _anotar(sessao, portaria, evento, Veredito.INVALIDO, None)
        return _montar_veredito(sessao, evento, Veredito.INVALIDO)

    # Sem `Evento` no `join`: o nome do show não entra em resposta nenhuma desta
    # rota — nem no `EVENTO_ERRADO`, e principalmente nele.
    linha = sessao.execute(
        select(Ingresso, Setor, Usuario)
        .join(Reserva, Reserva.id == Ingresso.reserva_id)
        .join(Setor, Setor.id == Ingresso.setor_id)
        .join(Usuario, Usuario.id == Reserva.cliente_id)
        .where(Ingresso.codigo == normalizado)
    ).first()

    if linha is None:
        _anotar(sessao, portaria, evento, Veredito.INVALIDO, None)
        return _montar_veredito(sessao, evento, Veredito.INVALIDO)

    ingresso, setor, titular = linha

    if not conferir_codigo(
        normalizado, ingresso.id, ingresso.evento_id, ingresso.nonce
    ):
        # Aqui o `ingresso_id` **é** conhecido: existe linha com este código, ela
        # só não sobrevive ao recálculo do HMAC. Guardá-lo é o que permite
        # descobrir depois do show qual ingresso foi adulterado — que é a pergunta
        # para a qual a trilha existe.
        _anotar(sessao, portaria, evento, Veredito.INVALIDO, ingresso.id)
        return _montar_veredito(sessao, evento, Veredito.INVALIDO)

    if ingresso.evento_id != evento.id:
        _anotar(sessao, portaria, evento, Veredito.EVENTO_ERRADO, ingresso.id)
        return _montar_veredito(sessao, evento, Veredito.EVENTO_ERRADO)

    entrada = sessao.execute(
        update(Ingresso)
        .where(Ingresso.id == ingresso.id, Ingresso.usado_em.is_(None))
        .values(usado_em=datetime.now(timezone.utc), validado_por=portaria.id)
        .returning(Ingresso.usado_em)
        # Mesmo motivo do `_transicionar` de `services/reserva.py`: o objeto
        # carregado fica com o valor velho, e quem precisa do novo o pega do
        # `RETURNING` ou relê. Sincronizar aqui seria manter em dia um objeto
        # que esta função não consulta mais.
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()

    # ⚠️ **O `commit` continua sendo um só, e agora ele é do `_anotar`** — service
    # que escreve abre e fecha a transação (`ARCHITECTURE-SPINE.md#Convenções`).
    # O `UPDATE` acima e o `INSERT` da `validacao` fecham **juntos**: um erro
    # depois do `UPDATE` desfaz os dois, e não existe estado em que alguém entrou
    # sem deixar registro. Ele acontece nos dois caminhos — quem perdeu a corrida
    # não gravou `usado_em` nenhum, e fechar a transação é o que solta a trava da
    # linha para o próximo da fila.
    if entrada is not None:
        _anotar(sessao, portaria, evento, Veredito.VALIDO, ingresso.id)
        return _montar_veredito(
            sessao,
            evento,
            Veredito.VALIDO,
            titular_nome=titular.nome,
            setor_nome=setor.nome,
            entrada_em=entrada,
        )

    # Zero linhas: ou já estava usado, ou outro leitor venceu neste instante. Os
    # dois são a mesma coisa para quem está na porta, e a hora a mostrar é a da
    # entrada que valeu — que está no banco, não neste objeto.
    _anotar(sessao, portaria, evento, Veredito.JA_UTILIZADO, ingresso.id)
    # ⚠️ **Depois do `_anotar`, porque ele é quem commita.** `refresh` antes do
    # `commit` releria a linha dentro da transação aberta e traria o mesmo valor
    # velho — o `RETURNING` do `UPDATE` já mostrou que ela não mudou aqui.
    sessao.refresh(ingresso)
    return _montar_veredito(
        sessao,
        evento,
        Veredito.JA_UTILIZADO,
        titular_nome=titular.nome,
        entrada_em=ingresso.usado_em,
    )
