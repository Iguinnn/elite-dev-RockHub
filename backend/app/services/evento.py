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

**A ordem das duas recusas é a garantia do "nenhum evento órfão".** Elas
acontecem antes de qualquer `add`: se a lista está vazia ou tem nomes
repetidos, nada chega a existir no banco — nem o evento, nem o primeiro setor
antes de o segundo estourar.

**Não há `try/except IntegrityError` aqui**, ao contrário do `cadastrar()`. Lá
o `UNIQUE` do e-mail é a regra, e conferir antes seria uma corrida. Aqui as
duas violações possíveis (`uq_setor_evento_id_nome` e os `CHECK` do setor)
chegam todas do mesmo corpo de requisição, num único instante, sem ninguém
concorrendo — dá para conferi-las na memória, com certeza, antes de gravar. Um
`except` genérico neste ponto só serviria para transformar bug de verdade em
`422` bonito.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.erros import ErroDeDominio
from app.models.evento import Evento, Setor
from app.models.usuario import Usuario
from app.schemas.evento import EventoEntrada


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
    )

    sessao.add(evento)
    sessao.commit()
    sessao.refresh(evento)
    return evento
