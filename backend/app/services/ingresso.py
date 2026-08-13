"""O ingresso como agregado próprio: a leitura de "Meus ingressos" — Stories 4.1 e 4.2.

⚠️ **Este módulo lê, e da Story 4.3 em diante escreve `share_token`. Ele nunca
cria ingresso.** A emissão é do `services/reserva.py`, dentro da transação que
marca a reserva `PAGA` (AD-14) — mesmo aviso que aquele arquivo carrega sobre
si, em espelho. Um `INSERT INTO ingresso` fora daquela transação quebraria a
garantia inteira da Epic 3.

**Por que arquivo próprio, e não mais uma função em `services/reserva.py`.**
O ingresso tem vida depois de a reserva sair de cena — é lido por várias
compras de uma vez (`GET /ingressos`), compartilhado por link (Epic 4) e
validado na porta (Epic 5) — e `reserva.py` já passa de 800 linhas cobrindo o
agregado dele. Agrupar por agregado, não por arquivo que cresce.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.erros import ErroDeDominio
from app.core.seguranca import gerar_share_token
from app.models.evento import Evento, Setor
from app.models.ingresso import Ingresso
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.schemas.ingresso import IngressoDetalhe, IngressoNaLista


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
