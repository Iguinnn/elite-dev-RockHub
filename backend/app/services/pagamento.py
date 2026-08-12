"""O gateway de pagamento do AD-10: uma interface, e uma implementação simulada.

**A regra que este módulo existe para dar** é a do AD-10: o serviço de reserva
depende da **interface**, nunca da implementação. É isso que torna o caminho da
recusa testável sem rede, e é isso que faria a troca por um gateway de verdade
não encostar em `services/reserva.py`.

**A recusa é determinística e documentada**: cartão terminado em `0002` é
recusado, qualquer outro é aprovado — a mesma convenção dos cartões de teste da
Stripe. O enunciado do desafio pede que a recusa seja provocável de propósito, e
número mágico escondido é pior do que número mágico escrito.

⚠️ **O Pix não existe deste lado.** O QR e o código copia-e-cola são desenhados
na tela, aleatórios, e não atravessam a rede: aqui só chega `meio=PIX`, e a
resposta é sempre aprovada. Simular cobrança Pix no servidor seria mentira com
custo de manutenção — o aviso na tela diz com todas as letras que a cobrança é
fictícia. **O caminho da recusa continua sendo o cartão**, e é ele que o roteiro
de avaliação do README manda exercitar.

⚠️ **A assinatura do `autorizar` não recebe o `Reserva`**, e é um desvio
consciente da letra do AD-10 (`autorizar(reserva)`). Passar o modelo ORM
acorrentaria o adaptador de pagamento ao SQLAlchemy — o dia em que o gateway
virasse chamada HTTP, ele estaria importando tabela. O que o AD-10 amarra é a
**direção da dependência**, e essa continua de pé: quem chama conhece a
interface, e a interface não conhece o banco.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

# ⚠️ Mora aqui, e não em `models/`: meio de pagamento **não é persistido** em
# lugar nenhum. A reserva guarda o estado (`PAGA`, `RECUSADA`), não como foi
# paga — nenhuma story planejada pergunta "quantos pagaram no Pix", e coluna sem
# consumidor é peso. O schema de entrada importa daqui.
class MeioDePagamento(str, Enum):
    CARTAO = "CARTAO"
    PIX = "PIX"


# O final que recusa, com nome. Espalhado como literal `"0002"` dentro de um
# `if`, ele viraria a linha que ninguém encontra quando o README e o código
# discordarem.
FINAL_QUE_RECUSA = "0002"

_NAO_DIGITO = re.compile(r"\D")


@dataclass(frozen=True)
class Autorizacao:
    """A resposta do gateway — `Aprovado | Recusado` do AD-10, com um campo só.

    Um `bool` cru serviria hoje e não sobreviveria ao primeiro motivo de recusa
    que precisasse chegar à tela. `frozen=True` porque resposta de gateway é
    fato consumado: quem recebe lê, não corrige.
    """

    aprovada: bool


class PaymentGateway(Protocol):
    """A interface do AD-10 — o que `services/reserva.py` conhece.

    `Protocol` e não classe-base abstrata: o dublê dos testes não precisa herdar
    de nada para valer como gateway, e nada no projeto se beneficia de uma
    hierarquia aqui. O que importa é a forma da chamada, e é ela que está escrita.
    """

    def autorizar(
        self,
        *,
        total_centavos: int,
        meio: MeioDePagamento,
        numero_cartao: str | None,
    ) -> Autorizacao: ...


class PagamentoSimulado:
    """A implementação fake — a única que existe, e a que o desafio pede.

    ⚠️ **Não guarda nem registra o número do cartão.** Ele entra, é reduzido a
    dígitos para a comparação e sai do escopo com a função. Não há atributo de
    instância, log nem retorno que o carregue.
    """

    def autorizar(
        self,
        *,
        total_centavos: int,
        meio: MeioDePagamento,
        numero_cartao: str | None,
    ) -> Autorizacao:
        if meio is MeioDePagamento.PIX:
            return Autorizacao(aprovada=True)

        # Máscara da tela (`4111 1111 1111 0002`) reduzida a dígitos antes de
        # olhar o final: sem isto, o mesmo cartão aprovaria ou recusaria conforme
        # quem digitou tivesse posto espaço.
        digitos = _NAO_DIGITO.sub("", numero_cartao or "")
        return Autorizacao(aprovada=not digitos.endswith(FINAL_QUE_RECUSA))


def obter_gateway() -> PaymentGateway:
    """Dependência do FastAPI, e o ponto de troca.

    É por ela que o teste substitui o gateway com `dependency_overrides`, e é
    por ela que uma implementação de verdade entraria sem que
    `services/reserva.py` mudasse uma linha — que é a prova prática do AD-10.
    """
    return PagamentoSimulado()
