"""Os schemas do ingresso: a lista, o canhoto e o veredito da porta.

Schema de saída de `GET /ingressos` — a lista de "Meus ingressos" (Story 4.1).

**Um schema próprio, e não o `IngressoSaida` de `schemas/reserva.py`.** Aquele
é o canhoto de uma compra — nasce com `codigo` e `titular_nome`, os dois
campos que a tela `/ingressos` não desenha, e sem `evento_id` nem `usado_em`,
os dois que ela precisa. Reusá-lo faria o `codigo` (o segredo do QR)
atravessar a rede para uma tela que não o mostra: payload sem leitor, exigindo
inteligência de quem lê para saber quais dos campos ignorar.

`IngressoDetalhe` mora no mesmo arquivo, mas nasce só na Story 4.2 — é o
canhoto cheio, com `codigo`. Este módulo cresce junto com as duas rotas que a
techspec do grupo descreve.

`ValidacaoEntrada` e `ResultadoDaValidacao` entram na Story 5.2 e são a outra
ponta do mesmo agregado: os dois primeiros mostram o ingresso a quem o comprou,
estes dois o julgam na porta. Moram aqui pelo mesmo critério que fez
`services/ingresso.py` nascer — agrupar por agregado, não por quem chama.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.validacao import Veredito


class SituacaoDoIngresso(str, Enum):
    """Em que pé está este ingresso (techspec `docs/techspec-fim-do-evento.md`).

    **`str, Enum`, no molde do `DisponibilidadeDoSetor`**: os três valores entram
    no OpenAPI, e quem consome o contrato sabe que a lista é fechada. A tela lê a
    palavra e escolhe o bloco; ela não tem como inventar um quarto estado porque
    não é ela quem decide qual é o estado.

    ⚠️ **É estado derivado na leitura, nunca coluna.** Ele nasce da comparação
    entre `evento.data_hora_fim` e o relógio, a cada resposta. *Descartei* uma
    coluna `expirado_em` colhida preguiçosamente no molde do AD-4: aquela colheita
    existe porque **estoque precisa voltar para alguém**, e aqui nada é liberado —
    o ingresso só deixa de valer. Escrever uma coluna para registrar a passagem do
    tempo é guardar o que o relógio já responde, e ainda obrigaria a tela de
    ingressos, que é Server Component e leitura pura, a virar escrita a cada
    visita.

    ⚠️ **`UTILIZADO` ganha de `EXPIRADO`.** Ingresso usado num show que já acabou
    é `UTILIZADO`, e nunca o contrário: a pessoa entrou, e é isso que o canhoto e
    a lista precisam dizer. A regra mora numa função só (`situacao_do_ingresso`,
    em `services/ingresso.py`), e é a ordem dos `if` dela que a garante.

    **Por que um enum de três valores e não `expirado: bool` ao lado do
    `usado_em`**: dois sinais permitem quatro combinações, e a tela precisaria
    decidir qual vence — que é exatamente a decisão que este enum tira dela. É o
    mesmo argumento escrito no `DisponibilidadeDoSetor`.
    """

    ATIVO = "ATIVO"
    UTILIZADO = "UTILIZADO"
    EXPIRADO = "EXPIRADO"


class IngressoNaLista(BaseModel):
    """Um ingresso como a tela `/ingressos` o vê — sem `codigo` nem `titular_nome`.

    **`usado_em` é `datetime | None`, e é ele que separa os dois blocos da
    tela**: `NULL` cai em *Ativos*, preenchido cai em *Utilizados*. A API não
    devolve `{ativos, utilizados}` nomeados — a lista chega chapada e quem
    corta em dois blocos é a tela, o mesmo molde do `Meus eventos` da 2.6.

    `evento_id` entra porque o item leva ao show (`/eventos/{evento_id}`);
    nenhum dos dois campos que faltam — `codigo`, `titular_nome` — é desenhado
    aqui: o primeiro é o canhoto (`/ingressos/{id}`, Story 4.2), o segundo não
    tem leitor nesta tela.

    **Sem `from_attributes`**: `evento_nome`, `evento_data_hora`, `evento_local`
    e `setor_nome` não são atributos de `Ingresso` — o modelo não tem
    `relationship` para `Evento` nem para `Setor` (mesma disciplina de
    `Reserva`), e quem os monta é `services/ingresso.py`.
    """

    id: UUID
    evento_id: UUID
    evento_nome: str
    evento_data_hora: datetime
    evento_local: str
    setor_nome: str
    usado_em: datetime | None
    # ⚠️ **`usado_em` continua no contrato ao lado dele, e não é redundância.**
    # `situacao` é o **balde** que a tela agrupa; `usado_em` é a **hora** que ela
    # imprime em *"Entrou às 21h14"*. O que esta techspec desfaz é a tela derivar
    # a situação de `usado_em` sozinha — a regra é do backend, num lugar só, e é
    # ela que sabe do término do evento, que a lista nem devolve.
    situacao: SituacaoDoIngresso


class IngressoDetalhe(BaseModel):
    """O canhoto cheio — `GET /ingressos/{id}` (Story 4.2), o que vira QR.

    **`codigo` entra aqui, e só aqui.** São os 8 símbolos de base32 de Crockford
    do AD-5, lidos da coluna `codigo` sem recalcular — o mesmo aviso do
    `_ingressos()` de `services/reserva.py`: a validação da portaria é quem
    sempre recalcula (AD-5), esta rota só entrega o texto que vira QR.

    ⚠️ **`titular_nome` é o nome da conta que comprou** (decisão do Igor,
    techspec `docs/techspec-codigo-curto.md`), buscado pelo join
    `Ingresso → Reserva → Usuario`. Não é o nome digitado no checkout: aquele é de
    quem **pagou**, mora em `ingresso.pagador_nome` e não é desenhado em tela
    nenhuma. Ele muda quando o nome da conta muda, ao contrário do preço e do
    pagador, que são congelados na compra.

    **`usado_em` entra também aqui**, e não só na lista: um canhoto já
    utilizado que parecesse válido mandaria alguém para a fila da porta à
    toa. A tela não desenha um veredito — isso é a Epic 5 —, mas não pode
    fingir que o ingresso ainda vale.

    `evento_cidade` entra e não entrava em `IngressoNaLista`: a ficha do
    canhoto tem espaço para "casa e cidade" por extenso; a fila da lista já
    aperta com quatro colunas.

    **Sem `from_attributes`**, pelo mesmo motivo do `IngressoNaLista`: nenhum
    dos campos de `Evento`/`Setor` é atributo de `Ingresso`, e `codigo` não é
    coluna nenhuma — quem monta os três é `services/ingresso.py`.

    **`share_token` entrou na Story 4.3**, e é o único campo novo dela. Ele vai
    junto sempre que houver um — o dono reencontra o próprio link sem precisar
    compartilhar de novo. Escondê-lo de quem é dono do ingresso não protegeria
    nada: ele já é público para quem recebeu o link, por construção (AD-8).

    ⚠️ **Este é o schema das três rotas do ingresso**, e a terceira delas é
    **pública** — `GET /ingressos/compartilhados/{token}`, sem sessão nenhuma.
    Todo campo que entrar aqui de agora em diante atravessa para quem abriu um
    link recebido por WhatsApp, e não só para o dono. É de propósito: quem abre
    o link vai entrar com ele, e um canhoto que escondesse o titular seria um
    segundo canhoto, diferente do de verdade. Mas o critério para um campo novo
    passou a ser esse, e não mais "o dono pode ver".
    """

    id: UUID
    evento_nome: str
    evento_data_hora: datetime
    evento_local: str
    evento_cidade: str | None
    setor_nome: str
    titular_nome: str
    codigo: str
    usado_em: datetime | None
    # O mesmo campo derivado da lista, e aqui ele atravessa também para quem abriu
    # o link compartilhado — é o que o aviso do fim deste docstring anuncia, e é
    # de propósito: um canhoto que fingisse que o ingresso ainda vale mandaria
    # para a fila da porta alguém que já não entra. Quem recebeu o link precisa da
    # mesma verdade que o dono.
    situacao: SituacaoDoIngresso
    # `None` é "nunca compartilhado" **ou** "revogado" — os dois são o mesmo
    # estado, e a tela desenha o botão *Compartilhar* nos dois casos.
    share_token: str | None


class ValidacaoEntrada(BaseModel):
    """O que a portaria leu — do QR ou do campo manual (Story 5.2).

    **Um campo só, e cru.** O que chega é o que a câmera decodificou ou o que a
    pessoa digitou, com espaços, hífens e caixa como vieram: quem normaliza é o
    `normalizar_codigo` de `core/seguranca.py`, dentro do service. Normalizar
    aqui, num `field_validator`, moveria uma regra de domínio para o schema e
    deixaria a rota com duas normalizações possíveis para o mesmo valor.

    ⚠️ **`max_length` generoso, e ele não é validação de código.** O contrato do
    código são 8 símbolos; 64 é folga de sobra para separadores e espaço colado
    numa colagem. O teto existe pelo mesmo motivo do `_TAMANHO_MAXIMO_BRUTO` de
    `schemas/pagamento.py` e dos limites de `schemas/auth.py` — sem ele, um corpo
    de 10 MB é 10 MB varridos pelo `.upper().translate()` do normalizador. O que
    é **código inválido** responde `INVALIDO` no corpo de um `200`, e não `422`:
    passar de 64 caracteres não é um código recusado, é um pedido malformado.
    """

    codigo: str = Field(max_length=64)


class RecusasDoTurno(BaseModel):
    """Os três vereditos de recusa deste evento, contados (Story 5.6).

    **Um objeto, e não três campos soltos no `ResultadoDaValidacao`.** Eles são
    lidos juntos, desenhados juntos numa linha só do contador e vêm da mesma
    consulta — e é o mesmo objeto que o `TurnoDoLeitor` de `schemas/evento.py`
    carrega, o que seria impossível com três campos avulsos.

    ⚠️ **`VALIDO` não está aqui, e a ausência é a decisão.** As entradas saem de
    `ingresso.usado_em`, a coluna que o `UPDATE` condicional do AD-6 escreve
    atomicamente; esta contagem sai da tabela `validacao`, que é o registro do que
    foi **tentado**. Duas fontes para números vizinhos, de propósito: no dia em que
    divergirem, é o `usado_em` que ganha. Um `validos` aqui seria a terceira
    resposta para a mesma pergunta.

    ⚠️ **Veredito sem linha nenhuma é `0`, nunca ausente.** O `GROUP BY` do
    service só devolve o que existe, e um campo faltando faria a tela desenhar
    `undefined` no lugar do número — num contador em que zero é a informação mais
    comum do começo do turno.
    """

    invalidos: int
    ja_utilizados: int
    evento_errado: int


class ResultadoDaValidacao(BaseModel):
    """O veredito da porta — a resposta de `POST /portaria/.../validacoes` (5.2).

    ⚠️ **Os quatro resultados respondem `200`**, inclusive os três que negam
    entrada. Eles são **o produto** deste endpoint — é o FR6 inteiro —, e tratar
    três deles como `ErroDeDominio` inverteria o que a portaria vê: recusar
    entrada é o trabalho dela dando certo, não uma falha de protocolo. Some-se
    que o `ErroDeDominio` carrega `{codigo, mensagem}` e nada mais, e não haveria
    onde pôr a hora da primeira entrada nem o setor — encaixar isso na
    `mensagem` seria montar frase no backend, o que este projeto não faz desde a
    Story 3.6.

    **Um schema com campos opcionais, e não uma união discriminada de quatro
    formas.** A união vira `anyOf` no OpenAPI e obriga a tela a estreitar tipo
    antes de desenhar, para nenhum ganho: os quatro casos são a mesma tela
    trocando de palavra.

    ⚠️ **`EVENTO_ERRADO` não diz de qual show o ingresso é** (decisão do Igor,
    contra o protótipo do `EXPERIENCE.md`, que pedia "ESTE INGRESSO É DO SHOW DA
    CÉU"). Uma portaria que não foi escalada num evento acabaria recebendo o nome
    dele de volta — e restringir exatamente isso é o motivo de o AD-7 existir.
    Quem está na fila sabe qual ingresso comprou.

    **As contagens do turno entraram na Story 5.6**, e é o que a redação anterior
    deste docstring prometia — *"o contador do turno já foi decidido e viaja no
    corpo da validação, mas o campo entra junto da tela que o desenha"*. A tela
    chegou, e com ela os dois campos do fim desta classe.

    ⚠️ **Elas viajam na resposta da validação, e não numa rota própria de
    contador.** Atualizar o número é exatamente o que acontece a cada leitura, e
    quem acabou de validar já está numa ida à rede — uma segunda chamada seria uma
    latência a mais na fila para um dado que a primeira já podia trazer. **Sem
    polling e sem WebSocket**: uma entrada da outra porta aparece no meu contador
    na minha próxima leitura, e isso é rápido o suficiente para o único uso que o
    número tem.
    """

    # ⚠️ **Era um `Literal[...]`, e virou o enum do modelo na Story 5.6.** As
    # quatro palavras passaram a existir também no `CHECK` da tabela `validacao`,
    # e mantê-las escritas aqui de novo seria a terceira cópia — com o dia em que
    # discordam já marcado. `str, Enum` serializa igual (`"VALIDO"` no JSON) e o
    # OpenAPI ganha um nome em vez de uma união anônima. Precedente:
    # `PapelUsuario`, que nasce em `models/usuario.py` e é importado pelos schemas
    # de autenticação desde a Story 1.4.
    resultado: Veredito

    # O nome da **conta** que comprou (`usuario.nome`), o mesmo que o canhoto
    # mostra — e não `ingresso.pagador_nome`, que é de quem passou o cartão e
    # pode ser um terceiro. As duas telas mostram a mesma pessoa: quem chega com
    # o ingresso na mão vê o nome que a portaria lê, e a conferência com o
    # documento tem resposta.
    #
    # Preenchido em `VALIDO` e em `JA_UTILIZADO`. Nulo nos outros dois: sem
    # ingresso identificado não há titular, e em `EVENTO_ERRADO` dizer o nome
    # seria contar de quem é o ingresso do outro show.
    titular_nome: str | None = None

    # Só em `VALIDO` — é a informação que faz a portaria apontar a direção certa
    # ("Pista, por ali"). Em `JA_UTILIZADO` ela não serve: ninguém vai entrar.
    setor_nome: str | None = None

    # Em `VALIDO`, o instante **desta** entrada; em `JA_UTILIZADO`, o da
    # **primeira**. É o dado que transforma "já utilizado" numa frase que a fila
    # entende — "entrou às 20h47" —, e é ele que a armadilha do
    # `expire_on_commit=False` fazia sair nulo.
    entrada_em: datetime | None = None

    # ⚠️ **Os dois vêm nos quatro vereditos, e não têm valor padrão.** Um
    # `entradas: int = 0` faria a resposta que esquecesse de contar sair com zero
    # em vez de estourar — e zero é um número plausível no começo do turno, ou
    # seja, o defeito seria invisível. Aqui a ausência precisa doer.
    #
    # **Quantas pessoas já entraram neste evento**, de todas as portas — `COUNT`
    # por `evento_id`, sem filtrar por quem validou. A story quer "noção do
    # movimento", e com duas portas na mesma casa o número da minha própria
    # digitação não mede a fila, mede a minha digitação.
    #
    # ⚠️ **Sai de `ingresso.usado_em`, não da tabela `validacao`** — ver o
    # docstring do `RecusasDoTurno` logo acima e o do `models/validacao.py`.
    entradas: int

    recusas: RecusasDoTurno
