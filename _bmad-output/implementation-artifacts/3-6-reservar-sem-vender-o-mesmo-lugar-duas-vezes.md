---
baseline_commit: "Story 3.5 implementada e ainda **não commitada** no início desta story, na branch `Epic-3--Descoberta-e-compra`. Migração `head`: `6448866ff965` (`cria_tabelas_reserva_e_item_reserva`). Suíte: 316 testes passando (Story 3.5). ⚠️ Não executei git — este carimbo veio do estado informado no início da sessão; confira antes de começar."
---

# Story 3.6: Reservar sem vender o mesmo lugar duas vezes

Status: review

Epic 3 — Descoberta e compra · **A story que a epic inteira estava construindo.** As quatro
primeiras são de leitura, a 3.5 entregou o schema sem consumidor, e esta é a primeira escrita do
lado do cliente — a que faz `setor.vendidos` sair de zero pela primeira vez na vida do projeto.

Ela carrega a **garantia mais pontuada do desafio**: duas pessoas comprando o último ingresso no
mesmo instante, e exatamente uma levando. O AD-3 diz como — um `UPDATE` condicional atômico, nunca
leitura seguida de escrita — e o `README.md` da raiz já registra isso como decisão desde a Epic 2,
numa seção que descreve um comando *"que já existe e é testado"*. Até hoje ele é testado sobre uma
tabela que ninguém escreve. Desta story em diante ele é o caminho da compra.

Como cliente,
quero que meus lugares fiquem garantidos ao reservar,
para não perder a compra no meio do caminho.

**O que entra:** `POST /reservas` e `GET /reservas/{id}` num router novo (`app/api/cliente.py`), o
service com o `UPDATE` do AD-3, o botão `Reservar e pagar` na página do evento, o tratamento do
`409` com a frase do UX-DR8, e a página `/reservas/{id}` com o cronômetro dos 10 minutos.

**O que não entra:** pagar (3.8), colher reserva vencida (3.7), emitir ingresso (3.9), cancelar
(corte consciente). A página `/reservas/{id}` nasce **sem botão de pagar** — a 3.8 o acrescenta
dentro dela.

## Acceptance Criteria

1. **Given** um cliente logado e um setor com estoque
   **When** ele envia `POST /reservas` com `evento_id` e uma lista de `{setor_id, quantidade}`
   **Then** a resposta é `201` com a reserva em `PENDENTE`, `expira_em` **10 minutos** depois de
   agora e `total_centavos` igual à soma de `preco_unitario_centavos × quantidade` de cada item
   **And** existe uma linha em `reserva` e uma em `item_reserva` **por setor pedido**
   **And** `setor.vendidos` de cada setor subiu exatamente a quantidade pedida
   **And** o prazo é `PRAZO_DE_RESERVA_MINUTOS = 10`, **constante do service** (decisão do Igor) —
   não é coluna, não é variável de ambiente, não é parâmetro do corpo

2. **Given** o código do service
   **When** eu o leio
   **Then** o estoque muda por **um único statement condicional por item**, na forma do AD-3:
   ```sql
   UPDATE setor SET vendidos = vendidos + :q
    WHERE id = :id AND vendidos + :q <= capacidade
   ```
   **And** ⚠️ **`setor.vendidos` nunca é lido para dentro do Python** — nem para conferir antes,
   nem para logar, nem para montar mensagem de erro. A condição mora no `WHERE`, e a decisão é o
   `rowcount`. Ler `capacidade`/`vendidos` e decidir em Python é a implementação errada com o
   resultado certo em 99% dos casos, e é exatamente o que o desafio está avaliando
   **And** o `values()` usa a **expressão SQL** `Setor.vendidos + quantidade`, nunca um número lido
   antes
   **And** não existe `SELECT ... FOR UPDATE` em lugar nenhum: o bloqueio de linha do `UPDATE` já
   serializa as duas tentativas, e o `SELECT` explícito seria um segundo mecanismo para a mesma
   garantia

3. **Given** duas reservas do **último** ingresso de um setor, disparadas ao mesmo tempo em duas
   conexões diferentes
   **When** as duas executam
   **Then** exatamente **uma** afeta uma linha e a outra afeta **zero**
   **And** ao fim, `setor.vendidos == setor.capacidade` — nunca `capacidade + 1`
   **And** a que perdeu recebe `409` com código `ESTOQUE_INSUFICIENTE`
   **And** ⚠️ existe um teste que prova isso com **duas `Session` em conexões distintas e commit de
   verdade** — o único caminho que exercita a corrida. A receita está em *Testing*; o motivo de ele
   não poder passar pelo `TestClient` está lá também

4. **Given** um pedido de mais ingressos do que restam em **qualquer** um dos setores
   **When** ele executa
   **Then** a resposta é `409 ESTOQUE_INSUFICIENTE`
   **And** **nada** foi gravado: nenhuma linha em `reserva`, nenhuma em `item_reserva`, e o
   `vendidos` dos **outros** setores do mesmo pedido voltou ao que era
   **And** ⚠️ este é o AC do "tudo ou nada": um pedido de 2 na Pista (que tem) e 5 no Camarote (que
   não tem) não pode deixar a Pista com 2 vendidos e a pessoa sem reserva. A transação é uma só, e o
   `409` acontece **dentro** dela

5. **Given** um corpo que o service consegue recusar sem tocar em estoque
   **When** ele chega
   **Then** as recusas acontecem **antes de qualquer escrita**, nesta ordem, cada uma com seu código
   e `422`:
   ```
   1. itens vazio (ou ausente)          → RESERVA_SEM_ITEM
   2. o mesmo setor duas vezes no corpo → ITEM_DUPLICADO
   3. soma das quantidades > 6          → ACIMA_DO_MAXIMO_POR_COMPRA
   4. algum setor_id não é setor deste evento → SETOR_INVALIDO
   ── só então: o UPDATE do AD-3, e depois o INSERT ──
   ```
   **And** ⚠️ o `ITEM_DUPLICADO` existe pelo mesmo motivo do `SETOR_DUPLICADO` da Story 2.4: sem ele,
   `uq_item_reserva_reserva_id_setor_id` estoura como `IntegrityError` no `commit`, sobe até o
   handler genérico e vira `500` — erro de cliente virando "erro interno do servidor"
   **And** o `SETOR_INVALIDO` cobre os dois casos com **um** código e **uma** mensagem: id que não é
   setor nenhum, e setor que é de outro evento. Distinguir transformaria a rota num oráculo, e é a
   mesma disciplina do `PORTARIA_INVALIDA` da 2.5

6. **Given** um evento que não está em cartaz — id inexistente, rascunho ou data já passada
   **When** eu tento reservar nele
   **Then** a resposta é `404 EVENTO_NAO_ENCONTRADO`, com a **mesma** mensagem do
   `GET /eventos/{id}`: *"Esse show não está em cartaz."*
   **And** o recorte é literalmente o mesmo das quatro rotas públicas — `publicado_em IS NOT NULL` e
   `data_hora >= agora`, no mesmo `where` e na mesma ordem
   **And** ⚠️ isso não é zelo: sem a condição de data, o link guardado de um show de ontem venderia
   ingresso para uma noite que já passou, e o evento nem apareceria na programação para a pessoa
   descobrir o engano

7. **Given** as duas rotas novas
   **When** eu as chamo
   **Then** as duas exigem `Depends(exigir_papel(PapelUsuario.CLIENTE))` **na assinatura** (AD-9) —
   nunca um `if` no corpo
   **And** sem cookie de sessão é `401 NAO_AUTENTICADO`; com sessão de `ORGANIZADOR` ou `PORTARIA` é
   `403 SEM_PERMISSAO` — nesta ordem, que é a que o `Depends` encadeado do `dependencias.py` garante
   **And** `cliente_id` vem **da sessão**, e não existe parâmetro de corpo, de query ou de caminho
   por onde outro id pudesse entrar: reservar em nome de outra pessoa não é uma chamada que o
   service recusa, é uma chamada que não existe. Mesma assinatura de `publicar()` e
   `listar_do_organizador()`
   **And** o OpenAPI declara as duas rotas com o esquema de segurança, ao contrário das quatro
   públicas — há um teste da 3.1 que afirma o oposto para `/eventos`, e ele continua verde

8. **Given** `GET /reservas/{reserva_id}`
   **When** um cliente a chama
   **Then** ele recebe a reserva **dele**, com os itens, o estado, o `expira_em` e o total
   **And** a reserva de **outra** pessoa e um `id` que não existe recebem o **mesmo**
   `404 RESERVA_NAO_ENCONTRADA` — nunca `403`, pelo mesmo motivo do `obter_do_organizador` da 2.6
   **And** as duas condições (`id` e `cliente_id`) moram no **mesmo `where`**, e não num `get()`
   seguido de um `if`: "só vejo o que é meu" precisa ser verdade por construção
   **And** os itens vêm ordenados **pelo nome do setor** — a mesma ordem da página do evento, e a
   que a Story 3.5 deixou escrita no modelo ao recusar um `order_by` no `relationship`

9. **Given** a resposta das duas rotas de reserva
   **When** eu varro o corpo inteiro em texto
   **Then** **nenhuma** das palavras `capacidade`, `vendidos`, `proporcao`, `disponibilidade`,
   `esgotado` aparece — UX-DR7 e AD-13, garantidos pelo `response_model` e não pela tela
   **And** ⚠️ esta é a **quarta** lista de palavras proibidas diferente do projeto, e a mais fácil de
   errar: `preco_unitario_centavos`, `quantidade` e `total_centavos` são chaves **legítimas** aqui.
   Quantidade que a pessoa pediu não é estoque; quantidade que resta é
   **And** o corpo **não** traz `criado_em` nem nada que a tela não desenhe — mesma disciplina que
   manteve `imagem_url` fora do `EventoNaProgramacao`

10. **Given** um setor cujo preço muda depois da reserva
    **When** eu leio a reserva
    **Then** `preco_unitario_centavos` continua sendo o do **momento da reserva**, e
    `total_centavos` continua batendo com a soma congelada
    **And** o service **lê `setor.preco_centavos`** para congelá-lo, e isso **não** viola o AC2:
    preço não é estoque, e ler preço não é ler `vendidos`

11. **Given** o teto de 6 por compra
    **When** eu peço 4 na Pista e 3 no Camarote
    **Then** a resposta é `422 ACIMA_DO_MAXIMO_POR_COMPRA` — o teto é da **compra**, não do item
    **And** ⚠️ o número vem de `MAXIMO_POR_COMPRA`, **importado de `app/services/evento.py`**, e não
    de um `6` novo. É a constante que o `EventoPublico` já devolve ao stepper desde a 3.4, e o
    docstring de lá diz, com todas as letras, que a 3.6 cobraria o mesmo teto do servidor: com o
    número em dois lugares, o dia em que a regra mudar é o dia em que o stepper e a rota discordam
    **And** exatamente 6 passa; 7 não

12. **Given** a página do evento com quantidade escolhida
    **When** ela é renderizada para um **cliente logado**
    **Then** o rodapé ganha o botão `Reservar e pagar`, que dispara o `POST /reservas` e, no sucesso,
    leva a `/reservas/{id}`
    **And** para **visitante, organizador ou portaria** o botão dá lugar a um link para
    `/login?voltar=%2Feventos%2F{id}` (decisão do Igor) — a página é Server Component e já sabe quem
    está logado, então isso é decidido **antes** de renderizar, sem uma ida à rede para ouvir `401`
    **And** ⚠️ o `?voltar=` **já existe** e já é sanitizado por `caminhoInternoSeguro` desde a Story
    1.4 — não crie parâmetro novo, não crie função nova, e não use `?destino=`
    **And** a escolha do stepper **se perde** na ida ao login (decisão do Igor), e isso é aceito: o
    estoque pode ter mudado nesses segundos, e reescolher é ver o preço e a disponibilidade de agora
    **And** o rodapé continua sem aparecer com zero ingressos escolhidos, como na 3.4

13. **Given** o `409 ESTOQUE_INSUFICIENTE` chegando na tela
    **When** ele acontece
    **Then** a tela **relê `GET /eventos/{id}`** e monta a frase do UX-DR8 a partir dos dados
    frescos (decisão do Igor): *"**Esgotou enquanto você decidia.** A Pista acabou de esgotar. Ainda
    há ingressos na Área VIP."*
    **And** o setor nomeado é o que **eu escolhi** e que agora está `ESGOTADO`; o oferecido é o
    primeiro da lista fresca que ainda tem ingresso
    **And** a lista de setores na tela é substituída pela fresca, e a quantidade dos que esgotaram
    volta a zero — a pessoa não continua olhando um stepper que não pode mais funcionar
    **And** quando **nenhum** setor sobrou, a frase é *"Este show esgotou enquanto você decidia."*,
    sem oferecer nada
    **And** ⚠️ o corpo do erro **não muda de forma** (decisão do Igor): continua
    `{"erro": {"codigo", "mensagem"}}`, e nenhum campo novo entra. O `core/erros.py` existe desde a
    Story 1.1 para a API ter **uma** forma de erro, e a primeira exceção é a que abre a segunda

14. **Given** `/reservas/{id}` de um cliente logado
    **When** ele abre a página
    **Then** vê o nome e a data do show, os itens (setor, quantidade, preço unitário), o total, e o
    **cronômetro** com o tempo que resta dos 10 minutos
    **And** o cronômetro *"não pisca, não muda de cor, não faz contagem regressiva agressiva. Informa;
    não pressiona"* — `EXPERIENCE.md#cronômetro de reserva`, literal
    **And** ao chegar em zero ele diz que a reserva expirou, e **não** navega sozinho para lugar
    nenhum: quem colhe a reserva vencida é a Story 3.7, no servidor
    **And** ⚠️ **não há botão de pagar nesta tela** — pagar é a 3.8, junto com a rota que ele
    chamaria. Mesma disciplina que manteve a 3.4 sem botão de reservar: botão presente e desabilitado
    lê como defeito, não como escopo
    **And** sem sessão a página redireciona para `/login?voltar=%2Freservas%2F{id}`, no molde
    literal de `/conta` e `/organizador/eventos`

15. **Given** a suíte e o build
    **When** eu os rodo
    **Then** o backend passa inteiro e os **316** testes anteriores continuam verdes, com o número
    final registrado
    **And** `npm run build` e `npx tsc --noEmit` passam no frontend
    **And** ⚠️ **nenhum teste antigo deve precisar mudar de asserção.** Se um teste de programação,
    de evento ou de organizador quebrar, algo saiu do escopo: pare e diga

16. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta as duas rotas, o `UPDATE` do AD-3 com o porquê de ele não
    poder virar leitura-e-escrita, a ordem das recusas e o "tudo ou nada" — **até cinco parágrafos**
    **And** `frontend/README.md` documenta o botão, o caminho do visitante para o login e o
    tratamento do `409` — **até cinco parágrafos**
    **And** `README.md` da raiz **não é tocado** — ver *Perguntas em aberto* nº 1

> **De onde vem cada critério.** O `epics.md` traz quatro blocos para a Story 3.6, e eles viraram os
> ACs **1** (reserva `PENDENTE` com prazo de 10 min e estoque consumido), **2** (não existe leitura
> seguida de escrita), **3** (duas simultâneas, uma vence, a outra recebe `409
> ESTOQUE_INSUFICIENTE`) e **13** (a frase do UX-DR8 com o próximo setor oferecido).
>
> As cinco decisões que o Igor tomou antes de a story ser escrita estão em **AC12 e AC14** (o
> escopo da tela: botão aqui, página `/reservas/{id}` aqui, pagamento na 3.8), **AC12** de novo (o
> visitante vai ao login e volta, e a escolha do stepper se perde), **AC13** (o `409` se resolve
> relendo o evento, e o formato do erro não muda) e **AC1** (dez minutos é constante do service).
>
> **AC4, AC5, AC6, AC7, AC8, AC9 e AC10** são consequência das invariantes da espinha e da
> disciplina que as cinco stories anteriores fixaram: transação atômica, recusa antes de escrever, o
> mesmo recorte de "em cartaz", papel na assinatura, o mesmo `404` para "não existe" e "não é seu",
> o estoque fora do contrato, e preço congelado. **AC11** é a dívida que o docstring do
> `EventoPublico` cobrou por escrito na 3.4. **AC15 e AC16** são regra do projeto.

## Tasks / Subtasks

- [x] **T1. `app/schemas/reserva.py` — o contrato de entrada e de saída** (AC: 1, 8, 9, 10)
  - [x] Arquivo novo. Cinco classes, no molde do `schemas/evento.py`: docstring de módulo dizendo o
        que este contrato **recusa** e por quê
  - [x] `ItemDeReservaEntrada`: `setor_id: UUID`, `quantidade: int = Field(ge=1)`
    - [x] ⚠️ **Sem `le` aqui.** O teto é da **compra**, e é o service quem soma (AC11). Um `le=6` por
          item passaria a impressão de estar cobrindo a regra e cobriria a errada — é o mesmo aviso
          que a Story 3.5 escreveu ao recusar um `CHECK (quantidade <= 6)` no banco
  - [x] `ReservaEntrada`: `evento_id: UUID` e
        `itens: list[ItemDeReservaEntrada] = Field(default_factory=list, max_length=20)`
    - [x] `default_factory=list` para que **ausência** e **lista vazia** caiam na mesma regra do
          service (`RESERVA_SEM_ITEM`), como `setores` e `portaria_ids` da 2.4/2.5. Sem ele, o campo
          ausente vira "field required" do Pydantic, ou seja, `DADOS_INVALIDOS` — um código genérico
          para uma regra específica
    - [x] `max_length=20` é proteção contra corpo absurdo, não regra de produto — mesmo teto e mesmo
          argumento dos setores
    - [x] **Sem `extra="forbid"`**, como todos os schemas de entrada do projeto: campo desconhecido
          **ignorado** é garantia mais forte que campo desconhecido recusado. `cliente_id`, `estado`,
          `expira_em` e `total_centavos` não existem para este schema, então não há caminho pelo qual
          o corpo os influencie
  - [x] `ItemDaReservaSaida`: `setor_id`, `setor_nome`, `quantidade`, `preco_unitario_centavos`
  - [x] `ReservaSaida`: `id`, `evento_id`, `evento_nome`, `evento_data_hora`, `estado`, `expira_em`,
        `total_centavos`, `itens`
    - [x] ⚠️ **`capacidade`, `vendidos`, `disponibilidade` e `proporcao_vendida` não entram**
          (AC9). É o `response_model` que garante isso, não a tela. Escreva o porquê no docstring,
          como o `SetorPublico` faz
    - [x] `evento_nome` e `evento_data_hora` entram porque a tela `/reservas/{id}` precisa dizer de
          que show é a reserva sem uma segunda chamada — mesmo argumento que pôs `portarias` no
          `EventoSaida` da 2.5
    - [x] **Sem `from_attributes`** nos dois de saída: `setor_nome`, `evento_nome` e
          `evento_data_hora` não são atributos de `ItemReserva` nem de `Reserva`. Quem monta é o
          service — mesma razão do `EventoResumo` e dos três schemas públicos
    - [x] `estado: EstadoReserva` (o enum do modelo, que é `str, Enum`), e não `str` cru: a lista
          fechada entra no OpenAPI e a 3.7/3.8 herdam o contrato pronto

- [x] **T2. `app/services/reserva.py` — a regra, a transação e o `UPDATE` do AD-3** (AC: 1, 2, 4, 5,
      6, 8, 10, 11)
  - [x] Arquivo novo. Docstring de módulo no molde de `services/evento.py`, com a ordem das recusas
        em bloco de código e o motivo de cada uma
  - [x] `PRAZO_DE_RESERVA_MINUTOS = 10` no topo, com comentário: vem do AD-4, é constante e não
        coluna nem variável de ambiente (decisão do Igor), e é o irmão do `MAXIMO_POR_COMPRA`
  - [x] ⚠️ **`MAXIMO_POR_COMPRA` é importado de `app/services/evento.py`**, nunca redeclarado.
        Se algum dia ele mudar de casa, muda uma vez
  - [x] `criar(sessao, cliente, dados) -> ReservaSaida`:
    - [x] As quatro recusas do AC5, **antes de qualquer escrita**, na ordem escrita lá
    - [x] O evento: **uma consulta** com as três condições (`id`, `publicado_em IS NOT NULL`,
          `data_hora >= agora`) e `selectinload(Evento.setores)`. `agora` lido **uma vez**, no topo,
          e usado nos dois lugares (o recorte e o `expira_em`) — mesma disciplina de
          `listar_programacao`
    - [x] Os setores pedidos saem de `evento.setores` — **não** de um `select(Setor)` próprio.
          Assim "o setor é deste evento" é verdade por construção, e não uma segunda condição que
          alguém esquece
    - [x] ⚠️ **De cada setor lê-se `preco_centavos`, e mais nada.** `vendidos` e `capacidade` não
          entram no Python (AC2). Deixe isso escrito num comentário ao lado do laço: é a linha que a
          próxima pessoa vai querer acrescentar "só para conferir antes"
    - [x] O `UPDATE` do AD-3, **um por item**, dentro da mesma transação:
      ```python
      resultado = sessao.execute(
          update(Setor)
          .where(
              Setor.id == item.setor_id,
              Setor.vendidos + item.quantidade <= Setor.capacidade,
          )
          .values(vendidos=Setor.vendidos + item.quantidade)
          .execution_options(synchronize_session=False)
      )
      if resultado.rowcount == 0:
          raise ErroDeDominio("ESTOQUE_INSUFICIENTE", ..., status_http=409)
      ```
      - [x] ⚠️ `synchronize_session=False` **de propósito**: os `Setor` estão na sessão (vieram do
            `selectinload`), e a sincronização padrão tentaria reconciliar a coluna no objeto. Nada
            neste service lê `vendidos` depois — e é justamente por isso que sincronizar seria
            trabalho para produzir o valor que o AC2 proíbe usar
      - [x] ⚠️ `.values(vendidos=Setor.vendidos + item.quantidade)` é **expressão SQL**. Um
            `setor.vendidos + item.quantidade` calculado em Python passaria em todo teste sequencial
            e perderia a corrida — é a implementação errada com o resultado certo em 99% dos casos
    - [x] O `INSERT` **depois** dos `UPDATE`, na ordem do diagrama de sequência da espinha: a
          reserva com `estado=EstadoReserva.PENDENTE.value`, `expira_em = agora + timedelta(...)`,
          `total_centavos` somado dos itens, e os itens pelo `relationship` (`itens=[...]`), sem
          `add` separado e sem `flush` intermediário — como `publicar()` grava os setores
    - [x] `sessao.commit()` no fim. O router **não** confirma nada (convenção da espinha)
    - [x] ⚠️ **Nenhum `try/except IntegrityError`.** As duas violações possíveis vêm do mesmo corpo,
          num instante só, e as quatro recusas já as pegam na memória. Um `except` genérico aqui só
          transformaria bug de verdade em `422` bonito — o argumento inteiro está no topo de
          `services/evento.py`
    - [x] ⚠️ **O `409` sobe como `ErroDeDominio` de dentro da transação**, e é o handler do
          `main.py` que responde. Como não houve `commit`, os `UPDATE` já aplicados desaparecem: a
          exceção atravessa o gerador de `obter_sessao`, cujo `finally: sessao.close()`
          (`app/core/db.py:38`) descarta o trabalho não confirmado. É o AC4, o "tudo ou nada" — e é
          por isso que **não** cabe um `sessao.rollback()` explícito aqui: ele seria um segundo dono
          da mesma garantia. O teste do AC4 é quem prova que a cadeia funciona de ponta a ponta
  - [x] `obter(sessao, cliente, reserva_id) -> ReservaSaida`: uma consulta com `id` e `cliente_id`
        no mesmo `where` e `selectinload(Reserva.itens)`; `404 RESERVA_NAO_ENCONTRADA` para os dois
        casos
  - [x] Um helper privado `_para_saida(reserva, evento, setores_por_id)` monta o `ReservaSaida` nas
        duas funções — o nome do setor e o do evento não estão em `ItemReserva` nem em `Reserva`
    - [x] Os itens saem **ordenados por nome do setor** (AC8)

- [x] **T3. `app/api/cliente.py` — o router novo** (AC: 1, 7, 8, 9)
  - [x] Arquivo novo, o quinto router. Docstring dizendo o critério de entrada, no molde do
        `publico.py`: **este é o router de quem tem conta de cliente** — toda rota aqui começa por
        `Depends(exigir_papel(PapelUsuario.CLIENTE))`, e é o oposto exato do `publico.py`, que é
        definido pela ausência de autenticação. O `publico.py` já anuncia este arquivo no docstring
        dele desde a 3.4; confira que a frase de lá continua verdadeira e **não a reescreva**
  - [x] **Sem `prefix`**, como o `publico.py`: o recurso é reserva, e a URL é `/reservas`. O
        `organizador.py` tem prefixo porque as rotas dele são *do organizador*; aqui a URL não
        carrega o nome de um papel
  - [x] `POST /reservas` → `status_code=201`, `response_model=ReservaSaida`
  - [x] `GET /reservas/{reserva_id}` → `response_model=ReservaSaida`, `reserva_id: UUID`
  - [x] Docstring por rota, no padrão do projeto: o que o corpo **não** carrega e por quê, os
        códigos de erro possíveis, e o motivo do `404` único
  - [x] `app/main.py`: `from app.api import auth, cliente, organizador, publico, saude` e
        `app.include_router(cliente.router)` — a lista está em ordem alfabética nos dois lugares

- [x] **T4. `tests/test_reservar.py` — a rota, as recusas e o contrato** (AC: 1, 4, 5, 6, 7, 8, 9,
      10, 11)
  - [x] Arquivo novo. ⚠️ **Nome diferente de `test_reserva.py`**, que é da 3.5 e prova o schema. Este
        prova o comportamento
  - [x] Helpers **locais** (`_evento_publicado`, `_entrar`), no espírito do `test_programacao.py` e
        do `test_organizador_eventos.py`. Não mova nada para o `conftest.py`: a convenção real da
        suíte é helper local por módulo
  - [x] Os casos da tabela em *Testing*, um teste cada
  - [x] ⚠️ O `TestClient` guarda cookie entre chamadas — um teste que prova o `401` precisa de
        `cliente.cookies.clear()` ou de outra instância

- [x] **T5. `tests/test_reservar.py` — a corrida do AD-3** (AC: 2, 3)
  - [x] ⚠️ **O teste mais importante da story, e o único que não passa pelo `TestClient`.** A fixture
        `cliente` do `conftest.py` amarra o app a **uma** sessão revertida (`dependency_overrides`):
        duas chamadas HTTP concorrentes compartilhariam a mesma transação e a corrida nunca
        aconteceria. A receita completa está em *Testing* — siga-a
  - [x] Duas `Session` em **conexões distintas** do `engine_teste`, `threading.Barrier(2)` para
        soltar as duas juntas, dados criados com **commit de verdade** e apagados num `finally`
  - [x] A asserção é **independente de ordem**: `sum(rowcounts) == 1` e `vendidos == capacidade`.
        Não asserte *qual* das duas venceu — isso seria flaky, e não é o que o AD-3 promete
  - [x] Um segundo teste, sequencial e determinístico, pelo `TestClient`: esgotar o setor e provar o
        `409 ESTOQUE_INSUFICIENTE` na segunda chamada

- [x] **T6. `frontend/src/lib/reservas.ts` — os tipos e as duas chamadas** (AC: 12, 13, 14)
  - [x] Arquivo novo, no molde do `lib/programacao.ts` e do `lib/eventos.ts`
  - [x] `type ItemDaReserva` e `type ReservaSaida`, espelhando o schema, com o docstring dizendo que
        **não há estoque aqui** e que a garantia é o `response_model` do outro lado da rede
  - [x] `obterReserva(id)` — **do lado do servidor**: `cabecalhoDeSessao()` **fora** do `try` (é
        `cookies()`, e é o que já tira a rota da renderização estática), `cache: "no-store"`, e três
        estados (`ok` / `nao-encontrado` / `indisponivel`), no molde literal do `obterMeuEvento`
  - [x] ⚠️ **`unstable_rethrow` na primeira linha do `catch`** — a mesma armadilha que o
        `lib/programacao.ts` documenta em quatro funções
  - [x] A criação da reserva **não** mora aqui: ela sai de um Client Component e vai por `chamarApi`,
        que é o cliente do navegador. Escreva isso no docstring do módulo, senão a próxima pessoa
        procura a função que falta

- [x] **T7. `EscolhaDeIngressos.tsx` — o botão e o `409`** (AC: 12, 13)
  - [x] Props novas: `eventoId: string` e o que decide o rodapé — sugestão: `podeReservar: boolean`
        (verdadeiro só para `papel === "CLIENTE"`). A página é quem calcula, com
        `obterUsuarioDaSessao()`
  - [x] O botão `Reservar e pagar` no rodapé, usando `Botao` de `components/Botao.tsx`. Sem sessão
        de cliente, um `<Link href={/login?voltar=...}>` no lugar dele
    - [x] O destino vai por `encodeURIComponent`, como as cinco chamadas que já existem
  - [x] `POST /reservas` por `chamarApi`, com `{ evento_id, itens: [{ setor_id, quantidade }] }`
  - [x] Sucesso: `router.refresh()` **antes** do `router.push('/reservas/' + id)`
    - [x] O `refresh` não é o do login (aquele era pelo masthead): aqui o estoque desta página
          acabou de mudar, e sem ele o botão "voltar" do navegador mostraria a disponibilidade
          anterior. Escreva o motivo — os dois `refresh` do projeto existem por razões diferentes
  - [x] `409` → releitura de `/eventos/{id}` por `chamarApi`, guardando a lista fresca em estado e
        montando a frase do UX-DR8 (AC13)
    - [x] `setoresFrescos ?? setores` é o que a tela renderiza. Uma fonte só de cada vez
    - [x] Zerar a quantidade dos setores que viraram `ESGOTADO`
  - [x] `mensagemParaCodigo(codigo)` no padrão do `FormularioLogin` e do `FormularioPublicacao`: o
        texto vem do **código**, nunca da `mensagem` do servidor
    - [x] Cubra `NAO_AUTENTICADO`/`SEM_PERMISSAO` (a sessão dura 8h e pode ter caído com a tela
          aberta — foi o buraco que o code review da Epic 2 encontrou no formulário de publicação),
          `ACIMA_DO_MAXIMO_POR_COMPRA`, `SETOR_INVALIDO`, `EVENTO_NAO_ENCONTRADO` e o genérico
  - [x] `erroCapturado instanceof ErroDaApi` antes de ler `.codigo` — erro de rede não tem código
  - [x] ⚠️ **O arquivo continua sendo a única ilha desta tela.** Nada de `"use client"` no
        `page.tsx`: a diretiva é do módulo e arrastaria o cabeçalho, a ficha e a arte para o cliente

- [x] **T8. `/reservas/[id]` — a página e o cronômetro** (AC: 14)
  - [x] `frontend/src/app/(site)/reservas/[id]/page.tsx` + `page.module.css`, Server Component
  - [x] `await params` (é `Promise` no Next 16), guarda de sessão com
        `redirect("/login?voltar=%2Freservas%2F" + encodeURIComponent(id))`
  - [x] `nao-encontrado` → `notFound()`; `indisponivel` → a frase, no molde literal da página do
        evento
  - [x] O corpo: `← Programação` (ou o link para o evento), nome e data do show, os itens numa lista
        de fios, o total, e o `<Cronometro expiraEm={...} />`
  - [x] ⚠️ **Nenhum botão de pagar** (AC14). Uma linha dizendo que os lugares estão segurados; a 3.8
        acrescenta o pagamento **nesta** página
  - [x] `frontend/src/components/Cronometro.tsx`, `"use client"`:
    - [x] ⚠️ **Estado inicial `null` e cálculo no `useEffect`**, nunca `useState(() => calcular())`:
          o servidor renderiza num instante e o cliente hidrata em outro, e a diferença de um segundo
          é erro de hidratação. Renderize um traço até o primeiro tique
    - [x] `setInterval` de 1s com `clearInterval` no retorno do `useEffect`
    - [x] Ao chegar a zero: a frase de expirada, e **nenhuma navegação automática**
    - [x] Sem piscar, sem trocar de cor, sem animação (`EXPERIENCE.md#cronômetro de reserva`)
    - [x] `aria-live="polite"`, nunca `assertive`: um cronômetro anunciado a cada segundo em
          `assertive` interrompe a leitura da página inteira

- [x] **T9. Verificação** (AC: 15)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final → **340**
  - [x] `npm run build` e `npx tsc --noEmit` no `frontend/`
  - [x] Busca por `\.vendidos` em `app/services/reserva.py` → deve aparecer **só** dentro da
        expressão do `update()` (AC2)
  - [x] Busca por `create_all` em `backend/` → **zero** em código
  - [x] **Nenhuma migração nesta story.** O schema da 3.5 já tem tudo; se o `--autogenerate` for
        chamado por engano e produzir arquivo, apague-o
  - [x] ⚠️ Se subir servidor para conferir, **encerre o processo e confira a porta pelo PID** —
        `Ctrl+C` do Igor não mata processo iniciado por mim
  - [x] **Conferência visual é do Igor.** Entregue o roteiro (qual conta, qual evento, o que apertar,
        onde provocar o `409`) e espere a resposta dele. Não abra a aplicação para conferir

- [x] **T10. Os READMEs** (AC: 16) — obrigatório, regra do projeto
  - [x] `backend/README.md`: seção nova `## Reservar`, **depois de `## Reserva e item de reserva`** e
        antes de `## Convenções que nascem aqui`. **Até cinco parágrafos, nenhuma subseção `###`,
        nenhuma tabela nova**
    - [x] O que entra: as duas rotas; o `UPDATE` condicional e por que ele não pode virar leitura
          seguida de escrita; a ordem das quatro recusas; o "tudo ou nada" de um pedido com dois
          setores; e o teto de 6 vindo da mesma constante que a tela já lê
    - [x] Atualizar *Estrutura* (`api/cliente.py`, `schemas/reserva.py`, `services/reserva.py` na
          árvore, comentário de uma linha cada) e *Testes* (o número novo e `test_reservar.py` na
          lista). Os dois são conteúdo operacional, não parágrafo de decisão
  - [x] `frontend/README.md`: **até cinco parágrafos**, na seção temática que couber — provavelmente
        estendendo o que já existe sobre a tela do evento, mais uma seção `## A reserva:
        /reservas/[id]` se o assunto não tiver casa
    - [x] O que entra: o botão e quem o vê; o caminho do visitante pelo `?voltar=` e o fato de a
          escolha se perder (com o motivo); o `409` relendo o evento em vez de o erro carregar
          campo novo; e o cronômetro que informa sem pressionar
  - [x] `README.md` da raiz **não é tocado**. Conferir só uma coisa, sem reescrever: a seção
        *O estoque é protegido pelo banco, não pela aplicação* diz que o comando *"já existe e é
        testado"* — com esta story isso passa a valer para o caminho da compra, e o texto continua
        correto como está
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna da direita é o material dos
READMEs (T10) — é o "por quê" deles.**

| Assunto | Escolha, e o motivo dela | O que caiu, e por que não |
|---|---|---|
| Até onde vai a tela | **Botão na página do evento + página `/reservas/{id}`** com itens, total e cronômetro. A 3.8 acrescenta o pagamento dentro dela. A 3.4 já tinha escrito que o botão era desta story "junto com a rota que ele chamaria"; a reserva ganha endereço próprio porque ela **existe no servidor** e sobrevive a fechar a aba | *Recibo no rodapé da própria página do evento*, sem rota nova: mais barato, e faria a reserva — que é uma linha no banco com prazo — parecer um estado da tela. Recarregar perderia o caminho de volta para uma reserva que continua valendo. *Só backend nesta story*: deixaria o AC de UX-DR8 do epic sem tela até a 3.8 e contrariaria a nota deixada na 3.4 |
| Visitante sem conta | **O botão vira link para `/login?voltar=/eventos/{id}`,** e o login traz de volta. A página é Server Component e já sabe quem está logado: a decisão acontece antes de renderizar | *Botão para todo mundo, e o `401` vira aviso*: uma ida à rede para descobrir o que a página já sabia antes de renderizar, e um erro exibido para um caso que não é erro nenhum. *Só mostrar o botão para cliente, sem link*: o visitante veria o total e nenhum caminho adiante |
| A escolha do stepper na volta do login | **Perde-se, e a pessoa escolhe de novo.** O destino é `/eventos/{id}` limpo | *Carregar as quantidades na URL* (`?setor=2&...`): menos atrito, e faria a URL carregar estado de compra, o `EscolhaDeIngressos` ler `searchParams` e a tela restaurar uma escolha que pode não ser mais possível — o estoque muda nesses segundos. Reescolher não é só atrito: é ver o preço e a disponibilidade de agora |
| Como a tela sabe o que dizer no `409` | **A tela relê `GET /eventos/{id}`** e monta a frase do UX-DR8 com dados frescos. O corpo do erro continua `{codigo, mensagem}` e nada mais | *O erro carregar `setor_esgotado_id` e `setor_sugerido_id`*: uma ida à rede a menos, e o `core/erros.py` — que existe desde a Story 1.1 para a API ter **uma** forma de erro — ganharia sua primeira exceção. A primeira exceção é a que abre a segunda. *Frase genérica sem nomear setor*: entregaria menos do que o AC do epic pede, e a releitura é justamente o que deixa o stepper atualizado na mesma ação |
| Os 10 minutos do AD-4 | **Constante do service**, `PRAZO_DE_RESERVA_MINUTOS = 10`, ao lado do precedente `MAXIMO_POR_COMPRA` | *Variável de ambiente com padrão 10*, para o avaliador baixar para 1 minuto e ver a expiração acontecer no roteiro da Epic 6: caiu porque custa uma variável no `.env.example`, no README, na Railway e no `Settings` para um cenário de demonstração — e porque a expiração da 3.7 é provada por teste, que é onde ela precisa ser verdade. Se o roteiro da Epic 6 sentir falta, a conversa reabre lá |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **`evento_id` vai no corpo, explícito, e o service confere que todo setor é dele.** A alternativa
  — derivar o evento do primeiro setor — aceitaria em silêncio um corpo que mistura setores de dois
  shows, e `reserva.evento_id` passaria a mentir sobre metade dos itens. Com o campo explícito, a
  mistura é `SETOR_INVALIDO`, e a checagem sai de graça: os setores são lidos de `evento.setores`.
- **`GET /reservas/{id}` nasce nesta story**, e não na 3.8. Ela é consequência direta de a reserva
  ter endereço próprio: uma página que só existisse como resposta do `POST` não sobreviveria a
  recarregar. O custo é uma rota de leitura de dez linhas; o ganho é que a 3.7 e a 3.8 já a
  encontram pronta.
- **Nada impede um cliente de ter várias reservas `PENDENTE` ao mesmo tempo.** Segurar estoque é o
  que a reserva faz, e o prazo é o que a limita — um teto por pessoa seria uma regra de produto que
  ninguém pediu, e ela precisaria de uma resposta para "o que fazer com a anterior". A 3.7 colhe as
  vencidas.
- **O `estado` viaja no contrato desde já.** Só `PENDENTE` existe nesta story, e a tela não ramifica
  por ele. Ele entra porque a 3.7 e a 3.8 vão precisar (`EXPIRADA`, `PAGA`, `RECUSADA`) e porque um
  contrato de reserva sem o estado dela é um contrato que esconde a coisa principal.
- **O cronômetro conta contra `expira_em` do servidor, e o relógio do navegador é só a régua.** Ele
  não pergunta nada à API enquanto conta. Quem decide se a reserva expirou é o banco, na 3.7 — o
  cronômetro chegando a zero é informação, não veredito. Escreva isso no componente: é a diferença
  entre uma tela que informa e uma tela que se acha autoridade.
- **O item da reserva não guarda o nome do setor.** Ele sai do `Setor` na hora de montar a resposta.
  Congelar o **preço** é necessário (o organizador pode mudá-lo); congelar o nome seria uma segunda
  fonte para uma informação que não muda o que foi cobrado.
- **Nenhum dado semeado.** `seeds/semear.py` não muda: ele semeia contas, nunca eventos, e muito
  menos reservas.
- **Nenhuma migração.** O schema da 3.5 tem exatamente o que esta story precisa. Se aparecer
  vontade de acrescentar coluna, **pare e pergunte** — é a quinta decisão de modelagem, e ela é do
  Igor.

### O contrato, rota a rota

**`POST /reservas`** — `201`, `Depends(exigir_papel(CLIENTE))`

```jsonc
// entrada
{
  "evento_id": "…",
  "itens": [{ "setor_id": "…", "quantidade": 2 }]
}
// saída (201)
{
  "id": "…",
  "evento_id": "…",
  "evento_nome": "Baco Exu do Blues",
  "evento_data_hora": "2026-09-04T23:00:00Z",
  "estado": "PENDENTE",
  "expira_em": "2026-08-12T18:40:00Z",
  "total_centavos": 42000,
  "itens": [
    { "setor_id": "…", "setor_nome": "Pista", "quantidade": 2,
      "preco_unitario_centavos": 12000 }
  ]
}
```

**`GET /reservas/{reserva_id}`** — `200`, mesmo corpo, mesma dependência de papel.

**Os erros, e quem os produz:**

| Código | Status | Quando |
|---|---|---|
| `RESERVA_SEM_ITEM` | 422 | `itens` vazio ou ausente |
| `ITEM_DUPLICADO` | 422 | o mesmo `setor_id` duas vezes no corpo |
| `ACIMA_DO_MAXIMO_POR_COMPRA` | 422 | soma das quantidades > `MAXIMO_POR_COMPRA` |
| `SETOR_INVALIDO` | 422 | `setor_id` que não existe **ou** que é de outro evento |
| `EVENTO_NAO_ENCONTRADO` | 404 | id inexistente, rascunho ou data passada — e no `GET`, também "não é seu" (como `RESERVA_NAO_ENCONTRADA`) |
| `ESTOQUE_INSUFICIENTE` | 409 | o `UPDATE` do AD-3 afetou zero linhas |
| `RESERVA_NAO_ENCONTRADA` | 404 | `id` que não existe **ou** reserva de outra pessoa |
| `NAO_AUTENTICADO` / `SEM_PERMISSAO` | 401 / 403 | da dependência de papel, sem uma linha nova |

Todos no formato único: `{"erro": {"codigo": "…", "mensagem": "…"}}`.

[Fonte: ARCHITECTURE-SPINE.md#AD-3, #AD-4, #AD-9, #AD-13, #Convenções · epics.md#Story 3.6 ·
EXPERIENCE.md#Erro de estoque durante o checkout]

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `Reserva`, `ItemReserva`, `EstadoReserva` | `app/models/reserva.py` | O schema pronto da 3.5. ⚠️ **Não muda uma linha** — nem para acrescentar `relationship` |
| `Setor` | `app/models/evento.py:158` | O alvo do `UPDATE`. `CHECK (vendidos >= 0 AND vendidos <= capacidade)` é a rede de segurança, não a regra |
| `MAXIMO_POR_COMPRA` | `app/services/evento.py:84` | **Importe-o.** O comentário de lá já diz que esta story cobraria o mesmo teto |
| `obter_publico` | `app/services/evento.py:653` | O recorte de "em cartaz" e o `404` único, palavra por palavra |
| `publicar` | `app/services/evento.py:87` | **O molde do service inteiro**: ordem das recusas antes de escrever, filhos pelo `relationship`, `commit` no service |
| `obter_do_organizador` | `app/services/evento.py:747` | O molde do `obter()`: duas condições no mesmo `where`, um `404` para "não existe" e "não é seu" |
| `exigir_papel` | `app/core/dependencias.py:81` | `Depends(exigir_papel(PapelUsuario.CLIENTE))` na assinatura. Ele já garante 401 antes de 403 |
| `ErroDeDominio` | `app/core/erros.py:88` | Código estável + mensagem + status. ⚠️ O corpo do erro **não ganha campo novo** |
| `publico.py` | `app/api/publico.py` | O molde do router sem `prefix`, e o docstring que já anuncia este `cliente.py` |
| `test_programacao.py` | `tests/test_programacao.py` | **O molde do `test_reservar.py`**: helpers locais, varredura de palavras proibidas, testes de OpenAPI. ⚠️ **Não muda** |
| `conftest.py` | `tests/conftest.py:75, 91, 120, 139` | `engine_teste` (é dele que saem as duas conexões da corrida), `sessao`, `cliente`, `fabricar_usuario`. ⚠️ **Não muda** |
| `caminhoInternoSeguro` | `frontend/src/lib/caminho.ts` | O `?voltar=` **já existe e já é sanitizado**. Não crie parâmetro novo |
| `chamarApi` / `ErroDaApi` | `frontend/src/lib/api.ts` | O `POST` e a releitura, do lado do navegador. Prefixa `/api` sozinho |
| `obterUsuarioDaSessao` | `frontend/src/lib/sessao.ts` | Quem está logado, no servidor, com `cache()` por requisição |
| `obterMeuEvento` | `frontend/src/lib/eventos.ts` | **O molde do `obterReserva`**: três estados, `cabecalhoDeSessao()` fora do `try` |
| `FormularioPublicacao` | `frontend/src/components/FormularioPublicacao.tsx:79` | O molde do `mensagemParaCodigo`, incluindo os dois códigos de sessão que faltavam |
| `EscolhaDeIngressos` | `frontend/src/components/EscolhaDeIngressos.tsx` | **É este arquivo que cresce** no frontend |
| `Botao`, `AvisoDeErro`, `Campo` | `frontend/src/components/` | Já existem. Não crie um botão novo |

**Não devem ser tocados, e não devem quebrar:** `app/models/` inteiro, `app/core/` inteiro,
`app/integrations/`, `app/schemas/evento.py`, `app/api/publico.py`, `app/api/organizador.py`,
`app/api/auth.py`, as cinco migrações, `seeds/`, `tests/conftest.py` e todos os testes já verdes,
`docker-compose.yml`, `pyproject.toml`, `alembic.ini`, `next.config.ts`, `package.json`.

⚠️ **As exceções, todas por acréscimo:** `app/main.py` (um import e um `include_router`),
`app/services/evento.py` **só se** o `MAXIMO_POR_COMPRA` precisar ser exportado de outro jeito — e
ele não precisa, então o arquivo deve ficar intocado —, `EscolhaDeIngressos.tsx`,
`eventos/[id]/page.tsx` (as props novas) e os dois READMEs de camada.

Se algum outro precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Ler o estoque antes de escrever.** É a armadilha da story inteira, e ela é *confortável*: o
service já tem os `Setor` carregados pelo `selectinload`, e `if setor.vendidos + q > setor.capacidade`
é uma linha que funciona em todo teste sequencial. Ela é **proibida** (AD-3, AC2). A condição mora
no `WHERE`, e a resposta é o `rowcount`. Se você sentir vontade de conferir "só para dar uma
mensagem melhor", a mensagem melhor já existe: é a frase do UX-DR8, e quem a monta é a tela, com
dados frescos, depois do `409`.

**2. Calcular o `vendidos` novo em Python.** Primo da anterior, e mais silencioso:
`.values(vendidos=setor.vendidos + q)` manda um número literal para o banco e perde a corrida mesmo
com o `WHERE` certo. É `.values(vendidos=Setor.vendidos + q)` — a **coluna**, não o atributo do
objeto. A diferença é uma maiúscula.

**3. Testar a corrida pelo `TestClient`.** A fixture `cliente` amarra o app a uma sessão só, por
`dependency_overrides`. Duas chamadas HTTP "concorrentes" ali dentro compartilham a mesma transação:
o teste passaria, sem ter provado nada. A corrida se prova no **service**, com duas `Session` em
conexões distintas e commit de verdade. A receita está em *Testing*.

**4. Esquecer que o teste da corrida escreve de verdade.** Ele não está dentro da transação revertida
do `conftest.py` — ele comita. Sem um `finally` que apague o que criou, a linha fica no
`rockhub_teste` e o próximo `pytest` começa sujo. O `downgrade base`/`upgrade head` da fixture de
sessão limpa uma vez por suíte, não entre testes.

**5. Deixar estoque consumido pela metade num `409`.** Um pedido com dois setores faz dois `UPDATE`.
Se o segundo falhar, o primeiro precisa desaparecer. Como não houve `commit`, o `rollback` cuida —
mas **confira** que o caminho de exceção realmente não confirma nada, e que nenhum `flush()`
intermediário foi acrescentado "para pegar o id". O teste do AC4 é o que revela isso.

**6. `synchronize_session` no `update()`.** O padrão do SQLAlchemy 2.0 tenta reconciliar a coluna nos
objetos carregados, e aqui isso é trabalho para produzir justamente o valor que o AC2 proíbe usar.
`execution_options(synchronize_session=False)`, com o motivo escrito ao lado.

**7. Criar `?destino=`.** O parâmetro de retorno **já existe**, chama-se `?voltar=`, é sanitizado por
`caminhoInternoSeguro` e é usado em cinco lugares. Inventar um segundo nome para a mesma coisa é
duas convenções para um problema resolvido.

**8. Erro de hidratação no cronômetro.** `useState(() => calcularRestante())` roda no servidor e de
novo no cliente, em instantes diferentes: um segundo de diferença é um `text content did not match`.
Estado inicial `null`, cálculo no `useEffect`, traço até o primeiro tique.

**9. Pôr `"use client"` no `page.tsx` do evento ou da reserva.** A diretiva é do **módulo**: ela
arrasta o cabeçalho, a ficha e a arte para o cliente e a página deixa de ser Server Component. O
`npm run build` denuncia; a revisão de quem lê, não.

**10. Afrouxar a varredura de palavras proibidas.** É a quarta lista diferente do projeto, e as três
anteriores já mudaram de conteúdo a cada story. `quantidade`, `total_centavos` e
`preco_unitario_centavos` são legítimas aqui; `capacidade` e `vendidos` continuam proibidas. Se a
asserção reprovar, o defeito é o contrato — não a asserção.

**11. Escrever um `PaymentGateway` "já que estamos aqui".** Pagar é a 3.8 inteira, com a interface do
AD-10, o cartão terminado em `0002` e a devolução de estoque. Esta story não conhece pagamento.

**12. Devolver estoque em algum lugar.** Nenhuma reserva desta story muda de estado. `RECUSADA` é
3.8, `EXPIRADA` é 3.7, `CANCELADA` não tem dono. Se você escreveu um `UPDATE setor SET vendidos =
vendidos - …`, ele é de outra story.

**13. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest` falhar
com `os error 4551`, chame pelo módulo: `uv run python -m pytest`.

**14. O banco de desenvolvimento é do Igor.** Ele tem eventos reais de conferência. Não apague nada,
não semeie nada, e não rode `downgrade base` contra ele.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      cliente.py                 # novo — POST /reservas, GET /reservas/{id}
    schemas/
      reserva.py                 # novo
    services/
      reserva.py                 # novo — PRAZO_DE_RESERVA_MINUTOS, o UPDATE do AD-3
    main.py                      # +1 import, +1 include_router
  tests/
    test_reservar.py             # novo — rota, recusas, contrato e a corrida
  README.md
frontend/
  src/
    app/(site)/
      eventos/[id]/page.tsx      # cresce — props novas para a ilha
      reservas/[id]/
        page.tsx                 # novo
        page.module.css          # novo
    components/
      EscolhaDeIngressos.tsx     # cresce — botão, POST, 409
      Cronometro.tsx             # novo
    lib/
      reservas.ts                # novo
  README.md
```

Não existe, e não deve passar a existir nesta story: migração nova, `app/services/pagamento.py`,
`PaymentGateway`, tabela `ingresso`, rota de cancelar, rota de pagar, seed de reserva, dependência
nova, `error.tsx`.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar. Nenhum teste desta story toca rede externa.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| Reserva nasce `PENDENTE`, com `expira_em` ~10 min à frente e o total somado | `test_reservar.py` | 1 |
| `setor.vendidos` sobe exatamente a quantidade pedida | `test_reservar.py` | 1 |
| Um item por setor pedido, com o preço congelado | `test_reservar.py` | 1, 10 |
| Dois setores no mesmo pedido somam no total e geram dois itens | `test_reservar.py` | 1 |
| **Duas conexões disputando o último ingresso: exatamente uma vence** | `test_reservar.py` | 3 |
| Segunda chamada sequencial num setor esgotado → `409 ESTOQUE_INSUFICIENTE` | `test_reservar.py` | 3 |
| Pedido acima do que resta → `409`, e **nada** gravado (nem reserva, nem estoque parcial) | `test_reservar.py` | 4 |
| `itens` vazio e `itens` ausente → `422 RESERVA_SEM_ITEM` | `test_reservar.py` | 5 |
| Mesmo setor duas vezes → `422 ITEM_DUPLICADO` (nunca `500`) | `test_reservar.py` | 5 |
| Setor de outro evento e `setor_id` inexistente → o mesmo `422 SETOR_INVALIDO` | `test_reservar.py` | 5 |
| Evento inexistente, rascunho e passado → o mesmo `404 EVENTO_NAO_ENCONTRADO` | `test_reservar.py` | 6 |
| Sem cookie → `401`; organizador e portaria → `403`, nas duas rotas | `test_reservar.py` | 7 |
| `cliente_id` vem da sessão: o corpo não tem como influenciá-lo | `test_reservar.py` | 7 |
| `GET` devolve a reserva do dono, com os itens em ordem de nome de setor | `test_reservar.py` | 8 |
| `GET` da reserva de outra pessoa e de um id inexistente → o mesmo `404` | `test_reservar.py` | 8 |
| Nenhuma palavra de estoque no texto da resposta das duas rotas | `test_reservar.py` | 9 |
| O corpo tem exatamente as chaves do contrato (e o item, as quatro dele) | `test_reservar.py` | 9 |
| 4 + 3 → `422 ACIMA_DO_MAXIMO_POR_COMPRA`; 6 passa, 7 não | `test_reservar.py` | 11 |
| `quantidade = 0` e negativa → `422` do Pydantic | `test_reservar.py` | 5 |
| O OpenAPI declara as duas rotas **com** esquema de segurança | `test_reservar.py` | 7 |
| As quatro rotas públicas continuam sem parâmetro de segurança | (já existe, `test_programacao.py`) | 7, 15 |

**A receita do teste da corrida** (AC3) — o único que sai da transação revertida:

```python
# Duas Session em conexões distintas, dados comitados, limpeza no finally.
# Não usa a fixture `cliente`: `dependency_overrides` amarra o app a uma sessão
# só, e duas chamadas HTTP ali dentro compartilhariam a mesma transação.
Fabrica = sessionmaker(bind=engine_teste)   # cada Session pega sua conexão
inicio = threading.Barrier(2)
resultados: list[int] = []

def tentar() -> None:
    with Fabrica() as s:
        inicio.wait()                        # as duas soltam juntas
        r = s.execute(
            update(Setor)
            .where(Setor.id == setor_id, Setor.vendidos + 1 <= Setor.capacidade)
            .values(vendidos=Setor.vendidos + 1)
            .execution_options(synchronize_session=False)
        )
        s.commit()
        resultados.append(r.rowcount)

# ... duas threads, join, e então:
assert sum(resultados) == 1          # exatamente uma venceu
assert vendidos_lido == capacidade   # nunca capacidade + 1
```

⚠️ **Por que a asserção é `sum(...) == 1` e não "a primeira venceu".** O Postgres bloqueia a linha
para a segunda transação e, ao liberá-la, **reavalia o `WHERE` contra a versão nova** (READ
COMMITTED) — é exatamente por isso que o AD-3 funciona. Qual das duas chega primeiro é do escalonador
do sistema operacional; que só uma vença é do banco. Assertar a ordem seria testar o escalonador.

⚠️ **Limpeza obrigatória.** O teste comita: um `try/finally` apaga o evento, o setor e as contas que
criou. Sem isso o `rockhub_teste` acumula lixo entre execuções.

**Frontend: sem teste automatizado**, como todo o resto da camada — é corte consciente registrado no
`README.md` da raiz. A verificação é `npm run build` + `npx tsc --noEmit`, e a conferência visual é
do Igor.

**Roteiro para a conferência do Igor** (entregue junto com a story pronta, e espere a resposta):

1. Entrar como cliente (`cliente@rockhub.dev` / `rockhub123`, do seed), abrir um evento em cartaz
2. Escolher 2 na Pista e 1 em outro setor → o rodapé mostra `3 ingressos · 2 setores` e o botão
3. `Reservar e pagar` → cai em `/reservas/{id}` com o cronômetro correndo
4. Voltar ao evento: a barra do medidor andou (o `router.refresh()` do T7)
5. Sair da conta e abrir o mesmo evento → no lugar do botão, o link para entrar; entrar por ele
   devolve à página do evento (com o stepper zerado, como decidido)
6. Provocar o `409`: pelo `psql`, `UPDATE setor SET vendidos = capacidade WHERE id = …` com a tela
   já aberta, e então apertar o botão → a frase do UX-DR8 e a lista de setores atualizada

**Baseline: 316 testes passando** (Story 3.5).

### Inteligência das stories anteriores

**Da 3.5 — o schema está pronto e não se mexe.** As duas transições condicionais dos ACs 3 e 4 de
lá já estão provadas por `.rowcount`; esta story é quem finalmente as executa a partir de um service.
Três coisas de lá valem literalmente aqui: o `estado` se escreve por `EstadoReserva.X.value` (a
coluna é `String(20)`); `expira_em` é `TIMESTAMPTZ` e se compara com `datetime.now(timezone.utc)`,
nunca com `datetime.now()` ingênuo; e **nada** deriva estoque de `item_reserva` — a resposta é
`setor.vendidos`, sempre. O aviso está no docstring do modelo justamente porque esta é a story que
cria a tentação.

**Da 3.4 — o teto e a soma.** `maximo_por_compra = 6` já viaja no contrato do evento e já governa o
stepper. Esta story é a outra metade que aquele docstring prometeu: o mesmo número, cobrado no
servidor, importado da mesma constante. E é a 3.4 que explica por que o teto é fixo e não
`min(disponivel, 6)` — um teto que acompanhasse o estoque diria "restam 2" pelo devtools.

**Da 2.4 — a ordem das recusas é a garantia do "nada órfão".** O `services/evento.py` abre com um
bloco de código listando as cinco recusas e o motivo de a ordem importar. Copie a forma: as quatro
daqui existem para que um corpo malformado não deixe rastro, e a ordem é o que mantém os testes
provando o que se propuseram a provar quando a próxima story acrescentar a quinta.

**Da 2.2 e da 1.4 — o texto de tela vem do `codigo`, nunca da `mensagem`.** É convenção do projeto
desde o login, e o code review da Epic 2 achou o buraco de a sessão expirada não ter tradução no
formulário de publicação. O `mensagemParaCodigo` desta story nasce com `NAO_AUTENTICADO` e
`SEM_PERMISSAO` cobertos.

**Da 3.1 à 3.4 — o hábito do UX-DR7.** Quatro stories gastaram docstring, `response_model` e teste de
varredura para manter `capacidade` e `vendidos` fora do contrato do cliente. Esta é a primeira rota
de **escrita** do lado do cliente, e a tentação muda de forma: não é devolver o estoque, é *lê-lo
para decidir*. O AC2 é o UX-DR7 do lado de dentro.

[Fonte: _bmad-output/implementation-artifacts/3-5-modelo-de-reserva.md ·
3-4-ver-o-evento-e-seus-setores.md · 2-4-publicar-um-evento-com-seus-setores.md]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| Python | 3.12 | `datetime` com fuso, `threading.Barrier` no teste da corrida |
| FastAPI | 0.141.1 | `Depends(exigir_papel(...))`, `status_code=201`, `response_model` |
| Pydantic | 2.13.4 | `Field(ge=1)`, `default_factory=list`, enum no contrato |
| SQLAlchemy | 2.0.51 | `update()` com `where` + `values` de **coluna**, `execution_options`, `selectinload` |
| PostgreSQL | 16 | Bloqueio de linha e reavaliação do `WHERE` em READ COMMITTED — é isso que faz o AD-3 valer |
| pytest | (instalado) | `TestClient`, e duas `Session` fora da fixture para a corrida |
| Next.js | 16.3.0 | `params`/`searchParams` como `Promise`, `redirect()`, `notFound()`, `useRouter` |
| React | 19 | `useState`, `useEffect` com `clearInterval` |

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock`, `package.json` e `package-lock.json` não
mudam.

⚠️ **Antes de escrever qualquer coisa em `frontend/`, leia o guia da versão instalada** em
`node_modules/next/dist/docs/` — o `AGENTS.md` da pasta avisa que esta versão do Next tem quebras em
relação ao que se costuma saber de cor.

### Escopo — o que NÃO fazer aqui

Pagar · `PaymentGateway` · devolver estoque · colher reserva vencida · tabela `ingresso` · QR ·
cancelar · migração · seed de reserva · "Minhas compras" · dependência nova.

Quatro tentações concretas:

- **"Já ponho o botão de pagar, a página é essa."** É a Story 3.8 inteira, com a interface do AD-10
  e os dois desfechos. Um botão desabilitado aqui leria como defeito.
- **"A reserva vencida devia expirar quando o cronômetro zera."** É a 3.7, e ela acontece no
  **servidor**, condicionada a `estado = 'PENDENTE' AND expira_em < now()`. Um `POST` disparado pelo
  navegador ao zerar seria uma segunda autoridade sobre a mesma transição.
- **"Confiro o estoque antes para dar uma mensagem melhor."** É a armadilha 1, e é o AC2. A mensagem
  melhor é a do UX-DR8, montada pela tela depois do `409`, com dados frescos.
- **"Aproveito e crio `GET /reservas` para 'minhas compras'."** É a Epic 4. `ix_reserva_cliente_id`
  existe desde a 3.5 esperando por ela, e uma rota sem tela é código que ninguém sabe se está certo.

### Project Structure Notes

`app/api/` passa a ter **cinco** routers, e com este o critério do `publico.py` fica exercitado dos
dois lados: lá a superfície é definida pela **ausência** de autenticação; aqui, pela exigência de um
papel. O docstring do `publico.py` já anuncia este arquivo desde a 3.4 — ele estava certo, e não
precisa ser reescrito.

`app/services/` ganha o segundo módulo de domínio (`evento`, `reserva`) e o primeiro que **importa
do outro**: `MAXIMO_POR_COMPRA` vem de `services/evento.py`. A dependência é de constante, não de
função, e vai numa direção só — se algum dia virar mútua, é sinal de que os dois assuntos são um só.

É a primeira story do projeto em que **backend e frontend mudam juntos e dependem um do outro**: até
a 3.5 cada story ficava de um lado, ou copiava um contrato já pronto. A ordem de trabalho que evita
retrabalho é backend → suíte verde → `lib/reservas.ts` → tela.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.6] — os quatro blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — a 3.7, a 3.8 e a 3.9, que consomem o
  que esta story escreve
- [Source: ARCHITECTURE-SPINE.md#AD-3] — o `UPDATE` condicional atômico; a invariante da story
- [Source: ARCHITECTURE-SPINE.md#AD-4] — `PENDENTE`, os 10 minutos, e a transição sempre condicionada
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel na assinatura do endpoint, nunca `if` no corpo
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade
- [Source: ARCHITECTURE-SPINE.md#AD-11] — dinheiro em centavos `BIGINT`, tempo em `TIMESTAMPTZ` UTC
- [Source: ARCHITECTURE-SPINE.md#Convenções] — formato único de erro, transação no service, Server
  Component por padrão
- [Source: ARCHITECTURE-SPINE.md#Fluxo de reserva] — o diagrama que fixa `UPDATE` antes de `INSERT`
- [Source: EXPERIENCE.md#Erro de estoque durante o checkout] — a frase do UX-DR8, literal
- [Source: EXPERIENCE.md#cronômetro de reserva] — informa, não pressiona
- [Source: EXPERIENCE.md#Key Flows] — o fluxo 1, que é exatamente esta story
- [Source: backend/app/services/evento.py] — o molde do service, do recorte e do `404` único
- [Source: backend/app/api/publico.py] — o molde do router e o critério que separa público de cliente
- [Source: backend/app/models/reserva.py] — o schema da 3.5, e as quatro decisões escritas nele
- [Source: frontend/src/lib/caminho.ts] — o `?voltar=` já sanitizado
- [Source: frontend/src/components/EscolhaDeIngressos.tsx] — a ilha que cresce
- [Source: _bmad-output/implementation-artifacts/3-5-modelo-de-reserva.md] — a story que entregou o
  schema
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, régua de cinco parágrafos
  por camada; git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`.
   Ao terminar, avise que a story está pronta para commit
2. **Atualize os READMEs das camadas tocadas antes de dar a story por concluída** — até cinco
   parágrafos cada. Documentação não bloqueia o commit: aplique o código, rode a suíte, mostre o
   resultado, **depois** escreva. Aqui **as duas camadas** mudam. O `README.md` da raiz não é tocado
3. **Decisão de produto ou de modelagem é do Igor.** As cinco desta story estão respondidas e as oito
   suposições estão declaradas. Se aparecer uma sexta — coluna a mais, regra a mais, tela a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por você
6. **Conferência visual é do Igor** — entregue o roteiro da seção *Testing* e espere a resposta dele
7. **Nenhuma dependência nova**
8. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum, mas cria pasta nova em `frontend/src/app/(site)/reservas/` — confira que nenhum padrão
   sem âncora a engole, que foi o que aconteceu com `lib/` na Story 1.2
9. **O code review é ao fim da Epic 3**, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **A raiz recebe decisão nova?** Escrevi para **não** tocar o `README.md` da raiz. A régua diz que
   entra o que faria quem avalia ver um sistema diferente, e a decisão que mais chega perto — *o
   estoque é protegido pelo banco, não pela aplicação* — **já está lá** desde a Epic 2, escrita
   antes de existir o comando. Esta story a torna verdade no caminho da compra, sem mudar a escolha.
   As cinco decisões daqui são de tela e de contrato, e moram nos READMEs de camada.
2. **Dez minutos vira demonstrável na Epic 6?** Você escolheu a constante, e concordo com o motivo.
   Fica registrado que, se o roteiro de avaliação quiser mostrar a expiração acontecendo, a conversa
   reabre na Story 3.7 — que é quem colhe — e o custo é uma variável de ambiente.
3. **Continua sem evento semeado.** É a mesma pergunta desde a 3.1, e agora ela dói mais: numa
   máquina limpa o avaliador não tem em que clicar para chegar até a reserva, que é a garantia mais
   pontuada do desafio. Um seed com um evento e três setores custaria pouco e mudaria o roteiro da
   Epic 6 inteiro.
4. **`README.md:180`** diz que ainda não dá para "descobrir evento, comprar, receber o QR ou validar"
   no ambiente publicado. Continua verdade enquanto a Epic 3 não entrar na `main` — mas é a linha que
   fica desatualizada no dia do merge. Deixei intocada de propósito; a Epic 6 é quem a revisa.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (1M context) — `bmad-dev-story`, 2026-08-12.

### Debug Log References

Três falhas durante a implementação, todas no `test_reservar.py` e todas resolvidas:

1. **`FOREIGN KEY` no preparo do teste da corrida.** `Usuario` e `Evento` adicionados à mesma
   `Session` e comitados juntos: sem `relationship` declarado entre os dois (decisão da Story 2.3), o
   SQLAlchemy não tem como ordenar os dois `INSERT`, e o do evento saiu primeiro. Resolvido com um
   `flush()` entre os dois, com o motivo escrito ao lado.
2. **`422` onde eu esperava `409` no teste do "tudo ou nada".** Eu tinha escrito 2 na Pista + 5 no
   Camarote: sete ingressos, ou seja, `ACIMA_DO_MAXIMO_POR_COMPRA` antes de o estoque ser tocado. O
   teste precisa justamente do caminho em que o primeiro `UPDATE` já aconteceu — passou para 2 + 3.
3. **A ordem dos itens.** Ver a primeira nota de conclusão abaixo.

### Completion Notes List

- **A ordem dos itens não podia ser `sorted()` em Python, e isso só apareceu com um setor acentuado.**
  O AC8 pede "a mesma ordem da página do evento". Escrevi `sorted(..., key=nome)` e o teste com "Área
  VIP", "Camarote" e "Pista" reprovou: `sorted()` compara pontos de código e põe "Área VIP" por
  último, enquanto o `order_by="Setor.nome"` do `relationship` é ordenado pelo Postgres, na collation
  do banco, que a põe primeiro. Duas implementações que pareciam a mesma coisa. A ordem passou a sair
  da **posição do setor em `evento.setores`** — a mesma fonte que a página do evento usa —, e o teste
  passou a comparar com `GET /eventos/{id}` em vez de com uma lista escrita à mão, que é literalmente
  o que o AC afirma. Consequência: `_para_saida` ficou com dois parâmetros (`reserva`, `evento`) em
  vez dos três da T2 — o dicionário de setores virou redundante, porque ele já sai de `evento.setores`
  ali dentro, junto com a ordem.
- **⚠️ AC7, último item: o OpenAPI não declara esquema de segurança, e eu não implementei isso.** Não
  é esquecimento nem descuido de escopo — é que **nenhuma** rota protegida deste projeto o declara,
  desde a Epic 2: `usuario_atual` lê o cookie do `Request` à mão, e não por uma dependência
  `SecurityBase`, então o FastAPI não tem o que publicar. Conferi rodando o `app.openapi()` contra
  `/reservas`, `/reservas/{id}` e `/organizador/eventos`: `security` não aparece em nenhuma das três.
  Fazer o AC virar verdade exigiria mexer em `app/core/dependencias.py` — arquivo que a própria story
  lista como intocável — e mudaria o contrato publicado de todas as rotas de organizador. Escrevi o
  motivo no docstring do teste de OpenAPI e deixei a decisão para o Igor. O que garante a proteção
  das duas rotas são os testes de `401` e `403`, que exercitam a rota de verdade em vez de acreditar
  no documento.
- **Uma escolha de texto que não estava na story: "no setor X" em vez de "na X".** O `EXPERIENCE.md`
  escreve "Ainda há ingressos na Área VIP", que só funciona porque o exemplo é feminino. O nome do
  setor é digitado pelo organizador ("Camarote", "Mezanino"), não há como saber o gênero, e "na
  Camarote" é pior que a frase um pouco mais longa. O núcleo que o UX-DR8 pede — o que esgotou e o
  que sobrou — está inteiro.
- **Um `eslint-disable` no `Cronometro.tsx`, e ele é a parte pensada do arquivo.** A regra
  `react-hooks/set-state-in-effect` reprova o `setState` síncrono dentro do `useEffect`; aqui ele roda
  uma vez por montagem e é exatamente o que evita o erro de hidratação que a armadilha nº 8 da story
  descreve. O motivo está escrito acima da linha.
- **Nenhuma migração, nenhuma dependência nova, nenhum modelo tocado.** `app/models/`, `app/core/`,
  `tests/conftest.py` e todos os testes anteriores ficaram intactos; nenhuma asserção antiga precisou
  mudar. As únicas mudanças por acréscimo foram `app/main.py` (um import, um `include_router`),
  `EscolhaDeIngressos.tsx`, `eventos/[id]/page.tsx` e o CSS dela.
- **⚠️ Um teste antigo é intermitente, e não é desta story.**
  `test_seguranca.py::test_token_com_assinatura_alterada_e_recusado` reprovou numa das execuções e
  passou nas outras três. Ele troca o **último** caractere do JWT, e o último caractere de uma
  assinatura de 32 bytes em base64url carrega só 4 bits significativos: trocar por `A` (ou por `B`,
  quando já era `A`) não muda a assinatura decodificada em ~6% dos tokens, e a verificação passa
  legitimamente. Não toquei no arquivo — ele está na lista de intocáveis da story e o defeito é do
  teste, não do código. Fica registrado para o code review da Epic 3.
- **Dois ajustes pedidos pelo Igor depois da conferência visual.** (1) O `Botao` vinha com uma borda
  clara em volta desde a Story 1.4 — é o padrão `2px outset ButtonBorder` do navegador, e não existe
  reset de `<button>` no `globals.css`. Corrigido no `Botao.module.css`, com `cursor: pointer`,
  `:hover` (`filter: brightness(1.12)`, para não inventar um segundo tom de rosa fora do
  `globals.css`) e `:active`. Vale para **todas** as telas com botão primário, não só esta. (2) A
  mensagem do UX-DR8 saiu do rodapé e virou um `Toast` no canto inferior direito — dentro do rodapé
  ela empurrava o total e o botão para baixo. Ele não some sozinho e tem botão de fechar; a região
  `role="alert"` fica no DOM desde o primeiro render, vazia e com `pointer-events: none`. **Todos** os
  erros da ilha passaram a sair por ele, e não só o `409`: duas superfícies de erro na mesma tela
  seriam duas convenções para o mesmo problema.
- **Verificação:** suíte inteira em **340 testes** (baseline 316, +24), `npm run build` verde com
  `/reservas/[id]` listada como rota dinâmica, `npx tsc --noEmit` sem erro e `npx eslint src` sem
  erro. `\.vendidos` em `services/reserva.py` só aparece dentro da expressão do `update()` e nos
  comentários que explicam a proibição; `create_all` continua zero em código.

### File List

**Novos**

- `backend/app/schemas/reserva.py`
- `backend/app/services/reserva.py`
- `backend/app/api/cliente.py`
- `backend/tests/test_reservar.py`
- `frontend/src/lib/reservas.ts`
- `frontend/src/components/Cronometro.tsx`
- `frontend/src/components/Cronometro.module.css`
- `frontend/src/components/Toast.tsx`
- `frontend/src/components/Toast.module.css`
- `frontend/src/app/(site)/reservas/[id]/page.tsx`
- `frontend/src/app/(site)/reservas/[id]/page.module.css`

**Modificados**

- `backend/app/main.py`
- `backend/README.md`
- `frontend/src/components/EscolhaDeIngressos.tsx`
- `frontend/src/components/Botao.module.css`
- `frontend/src/app/(site)/eventos/[id]/page.tsx`
- `frontend/src/app/(site)/eventos/[id]/page.module.css`
- `frontend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-6-reservar-sem-vender-o-mesmo-lugar-duas-vezes.md`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-12 | Story 3.6 implementada. Backend: `schemas/reserva.py`, `services/reserva.py` (o `UPDATE` condicional do AD-3, as quatro recusas em ordem e o prazo de 10 min como constante), `api/cliente.py` com `POST /reservas` e `GET /reservas/{id}`, e `test_reservar.py` com 24 testes — entre eles o da corrida, com duas `Session` em conexões distintas e commit de verdade. Frontend: `lib/reservas.ts`, o botão `Reservar e pagar` e o tratamento do `409` no `EscolhaDeIngressos`, a página `/reservas/[id]` e o `Cronometro`. Suíte de 316 para **340**, `npm run build`, `tsc` e `eslint` verdes. Nenhuma migração, nenhuma dependência nova, nenhum teste antigo alterado. Duas coisas ficaram diferentes do que a story escreveu, com o motivo nas notas de conclusão: a ordem dos itens saiu da posição do setor em `evento.setores` em vez de um `sorted()` por nome (as duas discordam no primeiro nome acentuado, porque o Python compara pontos de código e o Postgres usa a collation do banco), e o último item do AC7 — o OpenAPI declarar esquema de segurança — **não foi implementado**, porque nenhuma rota protegida deste projeto o declara e fazê-lo exigiria mexer no `core/dependencias.py`, que a story lista como intocável |
| 2026-08-12 | Story 3.6 criada e contextualizada. Cinco decisões do Igor incorporadas: **a tela vai até `/reservas/{id}`**, com botão na página do evento, página de checkout com cronômetro e o pagamento ficando para a 3.8; **o visitante vai ao login e volta** pelo `?voltar=` que já existe desde a 1.4, e **a escolha do stepper se perde** de propósito, porque o estoque pode ter mudado nesses segundos; **o `409` se resolve relendo `GET /eventos/{id}`** e montando a frase do UX-DR8 com dados frescos, mantendo o corpo do erro em `{codigo, mensagem}` — nenhuma exceção ao formato único do `core/erros.py`; e **os 10 minutos do AD-4 são constante do service**, no precedente do `MAXIMO_POR_COMPRA`, e não variável de ambiente. Dezesseis ACs escritos sobre os quatro blocos do `epics.md`, entre eles o AC2 e o AC3, que são a garantia mais pontuada do desafio: o `UPDATE` condicional do AD-3 sem nenhuma leitura de `vendidos` para dentro do Python, provado por duas `Session` em conexões distintas com commit de verdade — o único caminho que exercita a corrida, já que a fixture `cliente` amarra o app a uma sessão só. Oito suposições declaradas — entre elas `evento_id` explícito no corpo, `GET /reservas/{id}` nascendo aqui e várias reservas `PENDENTE` por cliente sendo permitidas — e quatro perguntas registradas para o Igor |
