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
from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

from app.schemas.auth import FORMATO_DE_EMAIL, EmailNormalizado, NomeLimpo
from app.services.pagamento import MeioDePagamento

# CPF, telefone e cartão chegam com máscara da tela (`123.456.789-01`,
# `(11) 98888-7777`, `4111 1111 1111 1111`). O que se valida é a quantidade de
# **dígitos**, então a pontuação sai antes de contar — senão o mesmo número
# passaria ou reprovaria conforme quem digitou tivesse usado máscara.
_NAO_DIGITO = re.compile(r"\D")

# `MM/AA`, com mês entre 01 e 12. Não confere se a data já passou: cartão de
# teste com validade vencida é exatamente o que alguém digita ao inventar dados.
_FORMATO_DE_VALIDADE = re.compile(r"^(0[1-9]|1[0-2])/\d{2}$")


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

        if not self.numero_cartao or not (13 <= len(self.numero_cartao) <= 19):
            raise ValueError("numero_cartao: informe um cartão com 13 a 19 dígitos")

        if not self.nome_no_cartao:
            raise ValueError("nome_no_cartao: informe o nome impresso no cartão")

        if not self.validade or not _FORMATO_DE_VALIDADE.match(self.validade):
            raise ValueError("validade: informe no formato MM/AA")

        if not self.cvv or not (3 <= len(self.cvv) <= 4):
            raise ValueError("cvv: informe 3 ou 4 dígitos")

        return self
