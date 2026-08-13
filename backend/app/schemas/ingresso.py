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
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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

    **`entradas_no_evento` fica para a Story 5.6.** O contador do turno já foi
    decidido e viaja no corpo da validação, mas o campo entra junto da tela que o
    desenha: disciplina desde a 3.1, contrato não carrega campo sem consumidor.
    """

    resultado: Literal["VALIDO", "INVALIDO", "JA_UTILIZADO", "EVENTO_ERRADO"]

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
