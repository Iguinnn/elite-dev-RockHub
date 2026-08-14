"""O corpo do checkout — dados do comprador e do meio de pagamento (Story 3.8).

**Nada aqui é persistido, exceto o `nome`.** E-mail, CPF e telefone são
validados no formato, usados na tela e descartados: não existe coluna para eles
e não vou criar. Guardar CPF de gente é dado sensível sem nenhum consumidor
neste sistema — o único campo que sobrevive à requisição é o `nome`, que a Story
3.9 grava como `ingresso.pagador_nome`.

⚠️ **Este `nome` é o de quem paga, e não o titular do ingresso** (decisão do
Igor, techspec `docs/techspec-codigo-curto.md`). A coluna se chamava
`titular_nome` até 2026-08-12; o titular passou a ser o nome da **conta**, porque
o cartão pode ser de outra pessoa. O que ele grava continua não tendo leitor
nenhum em tela — é o registro de quem pagou, e fica por isso.

⚠️ **O CPF valida só o formato, sem dígito verificador — e isso é decisão, não
esquecimento.** O algoritmo do DV rejeita `111.111.111-11` e a maioria dos
números que alguém inventa na hora, o que brigaria de frente com o aviso que a
própria tela mostra: *use dados fictícios*. Um checkout que exige CPF válido de
verdade num ambiente de avaliação é um checkout que não deixa avaliar.

**Os campos de cartão são condicionais, e a condição é o `meio`.** Eles não são
opcionais no sentido de "pode faltar": faltam quando o pagamento é Pix e são
obrigatórios quando é cartão. Quem afirma isso é o `model_validator` no fim do
arquivo — o `| None` sozinho aceitaria um pagamento de cartão sem cartão nenhum.

**Sem `extra="forbid"`**, como todo schema de entrada do projeto: campo
desconhecido **ignorado** é garantia mais forte que campo desconhecido recusado.
"""

import re
from datetime import datetime, timezone
from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

from app.schemas.auth import FORMATO_DE_EMAIL, EmailNormalizado, NomeLimpo
from app.services.pagamento import MeioDePagamento

# CPF, telefone e cartão chegam com máscara da tela (`123.456.789-01`,
# `(11) 98888-7777`, `4111 1111 1111 1111`). O que se valida é a quantidade de
# **dígitos**, então a pontuação sai antes de contar — senão o mesmo número
# passaria ou reprovaria conforme quem digitou tivesse usado máscara.
_NAO_DIGITO = re.compile(r"\D")

# `MM/AA`, com mês entre 01 e 12.
#
# ⚠️ **A validade vencida passou a ser recusada** (decisão do Igor, 2026-08-13),
# e este comentário dizia o contrário: "não confere se a data já passou — cartão
# de teste com validade vencida é exatamente o que alguém digita ao inventar
# dados". A troca tem motivo concreto: cartão vencido aprovando a compra é das
# primeiras coisas que quem avalia tenta, e um `12/20` que passa lê como um
# checkout que não valida nada. O risco que o comentário antigo temia continua
# tratado, mas na tela: a dica do formulário manda inventar o **número**, não a
# data, e a máscara já impede o mês inválido.
_FORMATO_DE_VALIDADE = re.compile(r"^(0[1-9]|1[0-2])/\d{2}$")


# Até dezembro de 2040 (decisão do Igor). Cartão nenhum é emitido com 60 anos de
# validade, e `12/90` passando é a mesma classe de coisa que `12/20` passando: um
# campo que aceita qualquer coisa lê como campo que não valida nada.
_ANO_MAXIMO_DA_VALIDADE = 2040


def _alem_do_horizonte(validade: str) -> bool:
    """Ano impresso além de `_ANO_MAXIMO_DA_VALIDADE`."""
    _, ano = validade.split("/")
    return 2000 + int(ano) > _ANO_MAXIMO_DA_VALIDADE


def _esta_vencida(validade: str) -> bool:
    """`MM/AA` já passou? O cartão vale até o **último dia** do mês impresso.

    ⚠️ **A comparação é por `(ano, mês)`, nunca por data completa.** Um cartão
    `08/26` vale durante agosto de 2026 inteiro, inclusive no dia 31 — comparar
    contra a data de hoje o recusaria já no dia 2.

    Dois dígitos viram `20AA`, que é a leitura de todo cartão impresso. O limite
    dela é o ano 2099, e isso não é problema deste código.
    """
    mes, ano = validade.split("/")
    agora = datetime.now(timezone.utc)
    return (2000 + int(ano), int(mes)) < (agora.year, agora.month)


# ⚠️ **Teto do valor BRUTO, e é por isso que ele mora aqui e não num
# `Field(max_length=...)`** (code review da Epic 3). O `BeforeValidator` roda
# **antes** de qualquer restrição do campo, então um `max_length` limitaria só o
# resultado já normalizado — e o `re.sub` abaixo continuaria varrendo o corpo
# inteiro que chegou. Com `meio=PIX` os quatro campos de cartão nem chegam ao
# `model_validator`, então não havia teto nenhum sobre eles.
#
# 64 é folga larga: o maior campo real aqui é um cartão de 19 dígitos com
# separadores. O `schemas/auth.py` documenta o mesmo risco ao limitar `email` e
# `senha` — "um corpo de 10 MB vira 10 MB hasheados".
_TAMANHO_MAXIMO_BRUTO = 64


def _so_digitos(valor: object) -> object:
    if not isinstance(valor, str):
        return valor
    if len(valor) > _TAMANHO_MAXIMO_BRUTO:
        raise ValueError(
            f"campo longo demais (máximo {_TAMANHO_MAXIMO_BRUTO} caracteres)"
        )
    return _NAO_DIGITO.sub("", valor)


# Normalizados **antes** da validação, e é o que permite a regra ser contada em
# dígitos. O valor normalizado é o que chega ao service — que, para estes três,
# não faz nada com ele além de existir.
SoDigitos = Annotated[str, BeforeValidator(_so_digitos)]


class PagamentoEntrada(BaseModel):
    # O nome de quem paga, que vira `ingresso.pagador_nome`. A tela o entrega
    # preenchido com o nome da conta e deixa editar: quem compra pode estar
    # pagando pelo ingresso de outra pessoa — e o ingresso continua sendo da
    # conta, não deste campo.
    nome: NomeLimpo = Field(min_length=1, max_length=120)
    email: EmailNormalizado = Field(max_length=255)
    cpf: SoDigitos
    telefone: SoDigitos

    meio: MeioDePagamento

    # ⚠️ **`| None` por causa do Pix, não por serem dispensáveis.** A
    # obrigatoriedade real está no `_exigir_cartao_quando_for_cartao` abaixo.
    numero_cartao: SoDigitos | None = None
    nome_no_cartao: NomeLimpo | None = Field(default=None, max_length=120)
    # `validade` não passa pelo `SoDigitos` (a barra do `MM/AA` faz parte do
    # formato), então o teto dela é declarado no campo mesmo.
    validade: str | None = Field(default=None, max_length=_TAMANHO_MAXIMO_BRUTO)
    cvv: SoDigitos | None = None

    @field_validator("email")
    @classmethod
    def _conferir_formato_do_email(cls, valor: str) -> str:
        # A mesma expressão do cadastro, importada e não recopiada: duas regras
        # de e-mail no mesmo projeto divergem no primeiro ajuste de uma delas.
        if not FORMATO_DE_EMAIL.match(valor):
            raise ValueError("e-mail inválido")
        return valor

    @field_validator("cpf")
    @classmethod
    def _conferir_cpf(cls, valor: str) -> str:
        # Onze dígitos, e ponto final — ver o aviso no topo do módulo.
        if len(valor) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return valor

    @field_validator("telefone")
    @classmethod
    def _conferir_telefone(cls, valor: str) -> str:
        # Dez ou onze: fixo com DDD, e celular com o nono dígito.
        if len(valor) not in (10, 11):
            raise ValueError("telefone deve ter 10 ou 11 dígitos, com DDD")
        return valor

    @model_validator(mode="after")
    def _exigir_cartao_quando_for_cartao(self) -> Self:
        """Os quatro campos do cartão, exigidos só quando o meio é cartão.

        ⚠️ **Um `ValueError` aqui vira `422 DADOS_INVALIDOS`**, pelo handler de
        validação do `main.py`, e não um código de domínio próprio. É de
        propósito: "mandou cartão sem número" é corpo malformado, não regra de
        negócio — mesma porta por onde passam os outros erros de forma desta API.
        """
        if self.meio is not MeioDePagamento.CARTAO:
            return self

        # ⚠️ **Teto de 16, e era 19** (decisão do Igor, 2026-08-13). Os 19 vinham
        # do Maestro, mas a máscara da tela corta em 16 e um teto só na tela é
        # cosmético: 19 dígitos por `curl` continuavam pagando. Amex tem 15 e
        # continua cabendo; o que sai é o Maestro, que não existe no roteiro de
        # avaliação.
        if not self.numero_cartao or not (13 <= len(self.numero_cartao) <= 16):
            raise ValueError("numero_cartao: informe um cartão com 13 a 16 dígitos")

        if not self.nome_no_cartao:
            raise ValueError("nome_no_cartao: informe o nome impresso no cartão")

        if not self.validade or not _FORMATO_DE_VALIDADE.match(self.validade):
            raise ValueError("validade: informe no formato MM/AA")

        # Depois do formato, nunca antes: `_esta_vencida` faz `split("/")` e
        # `int()`, e um valor que não passou pelo regex quebraria os dois.
        if _esta_vencida(self.validade):
            raise ValueError("validade: este cartão está vencido")

        if _alem_do_horizonte(self.validade):
            raise ValueError(
                f"validade: o ano não pode passar de {_ANO_MAXIMO_DA_VALIDADE}"
            )

        if not self.cvv or not (3 <= len(self.cvv) <= 4):
            raise ValueError("cvv: informe 3 ou 4 dígitos")

        return self
