---
baseline_commit: "3d2af3f — `feat: Story 3.4 - Ver os eventos e seus setores`, na branch `Epic-3--Descoberta-e-compra`. Migração `head`: 06c1ad5ac276 (`habilita_extensao_unaccent`). Suíte: 293 testes passando (Story 3.4). ⚠️ Não executei git — este carimbo veio do estado informado no início da sessão; confira antes de começar."
---

# Story 3.5: Modelo de reserva

Status: review

Epic 3 — Descoberta e compra · **A story de fundação da segunda metade da epic, e a primeira
migração desde a 3.2** (que não criou tabela nenhuma — ligou a extensão `unaccent`). As quatro
stories anteriores são de leitura: a programação, a busca, a capa e a página do evento. Nenhuma
escreve nada. Desta aqui em diante a epic escreve — e não existe onde.

Esta story cria `reserva` e `item_reserva`, e **só isso**. Nenhuma rota, nenhum schema Pydantic,
nenhum service, nenhuma tela, nenhum frontend. Reservar é a Story 3.6; a expiração preguiçosa é a
3.7; pagar é a 3.8; o ingresso é a 3.9.

Como desenvolvedor,
quero as tabelas de reserva e item de reserva criadas por migração,
para que a compra tenha estado e possa ser revertida.

**O critério de pronto é o schema, não o comportamento.** Ao fim desta story `alembic upgrade head`
num banco vazio cria `usuario`, `evento`, `setor`, `evento_portaria`, `reserva` e `item_reserva`;
`downgrade base` derruba as seis; e o banco recusa, sozinho, todo estado que o AD-4 proíbe. Nada na
aplicação sabe que essas duas tabelas existem — e isso é o recorte, não uma falta. O precedente
literal é a Story 2.3, que criou `evento` e `setor` do mesmo jeito, uma epic antes de alguém as ler.

## Acceptance Criteria

1. **Given** o banco migrado
   **When** eu inspeciono o schema
   **Then** `reserva` tem `id` UUID, `cliente_id`, `evento_id`, `estado`, `expira_em`,
   `total_centavos` e `criado_em`
   **And** `item_reserva` tem `id` UUID, `reserva_id`, `setor_id`, `quantidade` e
   `preco_unitario_centavos`
   **And** as duas tabelas nascem numa **única** migração Alembic, filha de `06c1ad5ac276`
   **And** `reserva` é criada **antes** de `item_reserva` no `upgrade()`, e derrubada **depois** no
   `downgrade()` — ordem trocada quebra a chave estrangeira

2. **Given** o campo `estado`
   **When** eu o inspeciono
   **Then** ele é `String(20)` com `CHECK estado IN ('PENDENTE', 'PAGA', 'RECUSADA', 'EXPIRADA',
   'CANCELADA')`, chamado `ck_reserva_estado_valido` — os cinco estados do AD-4
   **And** o enum vive **em Python**, como `EstadoReserva(str, Enum)` em `app/models/reserva.py`,
   no molde exato do `PapelUsuario` (decisão do Igor)
   **And** ⚠️ **não** é o tipo `ENUM` nativo do Postgres: acrescentar um estado seria `ALTER TYPE`,
   e o projeto inteiro já resolve enum de domínio assim desde a Story 1.3
   **And** gravar `estado = 'QUALQUERCOISA'` é recusado pelo **banco**, com `IntegrityError` no
   `flush()` — não por validação de Python

3. **Given** a transição de estado que o AD-4 fixa
   **When** eu executo
   ```sql
   UPDATE reserva SET estado = 'PAGA' WHERE id = :id AND estado = 'PENDENTE'
   ```
   **Then** ela afeta **uma** linha na primeira vez e **zero** na segunda, sem levantar exceção
   **And** existe um teste que prova isso **agora**, na story em que a tabela nasce — é o mesmo
   raciocínio do AC9 da Story 2.3, que provou o `UPDATE` condicional do AD-3 antes de existir
   service para chamá-lo
   **And** ⚠️ é este zero que faz *"reprocessar um pagamento aprovado não gera ingresso novo"*
   (AD-14) ser verdade por construção, e não por um `if` em algum lugar

4. **Given** uma reserva `PENDENTE` com `expira_em` no passado e outra com `expira_em` no futuro
   **When** eu executo
   ```sql
   UPDATE reserva SET estado = 'EXPIRADA'
    WHERE id = :id AND estado = 'PENDENTE' AND expira_em < now()
   ```
   **Then** a vencida afeta **uma** linha e a que ainda vale afeta **zero**
   **And** é a forma da colheita preguiçosa da Story 3.7 (AD-4), provada aqui pelo mesmo motivo do
   AC3 — e é o que prova que `expira_em` é comparável com `now()` no banco, sem conversão de fuso
   pelo caminho (AD-11)

5. **Given** `expira_em`, `criado_em` e todo campo monetário
   **When** eu inspeciono os tipos no banco
   **Then** `expira_em` e `criado_em` são `TIMESTAMPTZ` (`timezone is True`), e `criado_em` tem
   `server_default now()` — AD-11
   **And** `total_centavos` e `preco_unitario_centavos` são `BIGINT`, nunca `float` nem `NUMERIC`,
   e os dois carregam o sufixo `_centavos` da convenção
   **And** `expira_em` é `NOT NULL`: toda reserva nasce com prazo, inclusive a que vai ser paga em
   trinta segundos (ver *Suposições declaradas*)

6. **Given** a tabela `item_reserva`
   **When** eu tento gravar dois itens do **mesmo setor** na **mesma** reserva
   **Then** o banco recusa por `uq_item_reserva_reserva_id_setor_id` (decisão do Igor)
   **And** o mesmo setor em **outra** reserva é aceito — a unicidade é por reserva, não global
   **And** ⚠️ o nome da constraint vai **explícito** no `UniqueConstraint`: o template `uq` da
   convenção usa só a primeira coluna e produziria `uq_item_reserva_reserva_id`, que parece dizer
   "um item por reserva" — o oposto do que a constraint faz. É a mesma armadilha, e a mesma saída,
   do `uq_setor_evento_id_nome` da Story 2.3

7. **Given** `item_reserva.quantidade` e os dois campos monetários
   **When** eu tento gravar `quantidade = 0` ou negativa, ou preço negativo, ou `total_centavos`
   negativo
   **Then** o banco recusa nos três casos, por `ck_item_reserva_quantidade_positiva`,
   `ck_item_reserva_preco_nao_negativo` e `ck_reserva_total_nao_negativo`
   **And** o motivo de cada uma está escrito no modelo: item de quantidade zero é linha que consome
   estoque nenhum e aparece no checkout; dinheiro negativo é dinheiro andando para trás

8. **Given** uma reserva com itens
   **When** a reserva é apagada
   **Then** os itens somem junto, por `ON DELETE CASCADE` em `item_reserva.reserva_id`
   **And** o `relationship` do ORM concorda com o banco (`passive_deletes=True`) — sem ele o
   SQLAlchemy emite `UPDATE item_reserva SET reserva_id = NULL` antes do `DELETE`, estoura no
   `NOT NULL` e nunca chega ao `CASCADE` que a migração declarou. É a armadilha 3 da Story 2.3,
   inteira, de novo

9. **Given** um evento que já tem reserva
   **When** alguém tenta apagá-lo — ou apagar um setor dele, ou a conta do cliente que reservou
   **Then** o **banco recusa** nos três casos, por chave estrangeira (decisão do Igor)
   **And** `reserva.cliente_id`, `reserva.evento_id` e `item_reserva.setor_id` são declarados
   **sem `ondelete`**, que é o `RESTRICT` do Postgres — o mesmo tratamento que
   `evento.organizador_id` e `evento_portaria.usuario_id` já dão a quem publicou e a quem foi
   escalado
   **And** ⚠️ isso muda o alcance prático do `CASCADE` de `setor`: apagar um evento **sem** reserva
   continua levando os setores junto, e apagar um evento **com** reserva passa a falhar no
   `item_reserva`. Os dois comportamentos são desejados, e o AC exige um teste para cada

10. **Given** uma reserva ou um item com `cliente_id`, `evento_id`, `reserva_id` ou `setor_id`
    apontando para uma linha que não existe
    **When** eu tento gravá-lo
    **Then** o banco recusa por chave estrangeira

11. **Given** as chaves estrangeiras lidas
    **When** eu inspeciono os índices
    **Then** existem `ix_reserva_cliente_id`, `ix_item_reserva_reserva_id` e
    `ix_item_reserva_setor_id`
    **And** `reserva.evento_id` fica **sem** índice, de propósito e com o motivo escrito no modelo —
    ver *Suposições declaradas*. O Postgres não cria índice para chave estrangeira, e a disciplina
    do projeto desde a Story 2.3 é indexar a que **é lida**, não todas

12. **Given** o projeto inteiro
    **When** eu procuro criação de schema
    **Then** continua não existindo `create_all` em lugar nenhum — nem em teste
    **And** `alembic downgrade base` derruba as **seis** tabelas, e `upgrade head` refaz todas
    **And** ⚠️ `test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz` precisa passar a
    afirmar as seis: hoje a tupla dele tem quatro, e uma migração nova com o `downgrade()` quebrado
    passaria por ele sem ser notada

13. **Given** o `models/__init__.py`
    **When** eu o leio
    **Then** `Reserva`, `ItemReserva` e `EstadoReserva` estão reexportados e no `__all__`
    **And** ⚠️ **é este import que o `migrations/env.py` usa**: sem ele o `--autogenerate` produz
    uma migração vazia e a story parece pronta sem ter criado nada

14. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar
    **Then** ela passa inteira e os **293** testes anteriores continuam verdes
    **And** o número final está registrado
    **And** ⚠️ **nenhum teste antigo deve precisar mudar de asserção.** O único arquivo já existente
    que cresce é `test_migracoes.py`, e ele cresce por **acréscimo** — mais a tupla de seis tabelas
    do AC12. Se um teste de evento, de programação ou de organizador quebrar, algo saiu do escopo:
    pare e diga

15. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta as duas tabelas, as constraints, o que cada `ondelete`
    faz e por quê, e as duas transições condicionais dos ACs 3 e 4 — **até cinco parágrafos**
    **And** `frontend/README.md` **não muda**, e é intencional: nenhum arquivo de `frontend/` foi
    tocado. Precedente literal das Stories 1.3 e 2.3. Não invente conteúdo para cumprir regra
    **And** `README.md` da raiz **não é tocado** nesta story — ver *Perguntas em aberto* nº 1

> **De onde vem cada critério.** O `epics.md` traz **dois** blocos para a Story 3.5: as colunas das
> duas tabelas e os cinco valores de `estado` (AD-4). Eles viraram os ACs **1 e 2**.
>
> As quatro decisões que o Igor tomou antes de a story ser escrita estão espalhadas por **AC6 e
> parte do AC1** (o `id` próprio do item, que o `epics.md` não pede, mais a unicidade), **AC9** (as
> três chaves estrangeiras sem `ondelete`), **AC2** (`String` + `CHECK` em vez de `ENUM` nativo) e
> **AC1/AC5** (só `criado_em` de carimbo novo). **AC3 e AC4** existem porque o AD-4
> descreve transições condicionais que **esta story não executa** — o primeiro consumidor é a 3.6 —
> e uma tabela que nasce sem provar a operação que justifica sua forma é uma tabela que
> ninguém sabe se está certa; é o AC9 da Story 2.3 repetido de propósito. **AC5, AC7, AC8, AC10 e
> AC11** são consequência das convenções da espinha e da disciplina de schema que a 2.3 fixou.
> **AC12 e AC13** repetem literalmente o que a 1.3 e a 2.3 já cobravam: são as garantias que se
> perdem sem alguém conferindo a cada migração nova. **AC14 e AC15** são regra do projeto.

## Tasks / Subtasks

- [x] **T1. `app/models/reserva.py` — `EstadoReserva`, `Reserva` e `ItemReserva`** (AC: 1, 2, 5, 6,
      7, 8, 9, 10, 11)
  - [x] Arquivo novo, **as três coisas juntas**. `ItemReserva` não tem vida fora de `Reserva`, e o
        enum é o estado dela — mesmo precedente do `usuario.py` (`Usuario` + `PapelUsuario`) e do
        `evento.py` (`Evento` + `Setor`)
  - [x] Docstring do módulo no estilo do `evento.py`, dizendo quais decisões da arquitetura estão
        materializadas aqui e qual é qual:
    - [x] **A reserva segura estoque desde a criação** (AD-4) — ela nasce `PENDENTE` já tendo
          consumido `setor.vendidos` pelo `UPDATE` do AD-3, e é isso que dá sentido ao `expira_em`
    - [x] **Transição de estado é sempre condicionada ao estado anterior** (AD-4), e é o que o
          teste do AC3 prova antes de existir service
    - [x] **A expiração é preguiçosa** (AD-4): não há worker nem cron, e `expira_em` é lido por
          quem toca a reserva. A Story 3.7 é quem colhe
    - [x] **O estoque não se deriva daqui** (AD-13): é proibido responder "quantos restam" com
          `COUNT` sobre `item_reserva`. A resposta é `setor.capacidade - setor.vendidos`, sempre.
          Esta frase precisa estar escrita **no arquivo que mais convida a desobedecê-la**
  - [x] `class EstadoReserva(str, Enum)` com os cinco valores do AD-4, no molde do `PapelUsuario`
        (nome sem "Da": o precedente de enum de **modelo** é `PapelUsuario`, não os
        `DisponibilidadeDoSetor`/`PeriodoDaProgramacao` dos schemas)
  - [x] `Reserva`: colunas exatamente conforme a tabela em *As duas tabelas, coluna a coluna*.
        Nada além delas
  - [x] `ItemReserva`: idem, com as duas `CheckConstraint` e a `UniqueConstraint` nomeada à mão
  - [x] Estilo tipado do SQLAlchemy 2.0: `Mapped[...]` + `mapped_column(...)`. **Nunca** o
        `Column()` do estilo 1.x — a convenção é da Story 1.3. (A exceção do projeto é a `Table` do
        Core em `evento_portaria`, e ela não se aplica aqui: as duas tabelas têm colunas próprias)
  - [x] `relationship` **só entre `Reserva` e `ItemReserva`**, com `back_populates`,
        `cascade="all, delete-orphan"` e `passive_deletes=True`
  - [x] ⚠️ **Nenhum `relationship` para `Usuario`, `Evento` ou `Setor`**, e nenhuma linha nova em
        `usuario.py` ou `evento.py` — ver *Suposições declaradas*. Só as colunas de chave
        estrangeira
  - [x] Comentário por coluna no padrão do `evento.py`: o porquê fica ao lado do que, não num
        documento à parte
  - [x] ⚠️ `app/models/evento.py` e `app/models/usuario.py` **não mudam uma linha**

- [x] **T2. `app/models/__init__.py`** (AC: 13)
  - [x] Reexportar `EstadoReserva`, `ItemReserva` e `Reserva`; acrescentar os três ao `__all__`,
        que está em ordem alfabética
  - [x] ⚠️ Sem isto o `--autogenerate` produz migração **vazia** (armadilha 1)

- [x] **T3. A migração** (AC: 1, 12)
  - [x] `cd backend && uv run alembic revision --autogenerate -m "cria tabelas reserva e item_reserva"`
  - [x] Conferir no arquivo gerado, linha a linha — `--autogenerate` é ponto de partida, não
        resultado:
    - [x] `down_revision = '06c1ad5ac276'` (a extensão `unaccent`), **não** `None` e não a de
          `evento_portaria`
    - [x] `reserva` criada **antes** de `item_reserva` no `upgrade()`, e derrubada **depois** no
          `downgrade()`
    - [x] As duas `CheckConstraint` do item e o `CHECK` do estado saíram com os nomes que a
          convenção produz (`ck_reserva_estado_valido`, `ck_reserva_total_nao_negativo`,
          `ck_item_reserva_quantidade_positiva`, `ck_item_reserva_preco_nao_negativo`)
    - [x] A `UniqueConstraint` saiu como `uq_item_reserva_reserva_id_setor_id`
    - [x] `item_reserva.reserva_id` carrega `ondelete='CASCADE'`; **as outras três chaves
          estrangeiras não carregam `ondelete` nenhum** (AC9). O `--autogenerate` tem histórico de
          emitir chave estrangeira sem o `ondelete` — aqui são três que **devem** sair sem e uma
          que **deve** sair com
    - [x] `total_centavos` e `preco_unitario_centavos` saíram como `sa.BigInteger()`, não
          `sa.Integer()`
    - [x] `expira_em` e `criado_em` saíram com `sa.DateTime(timezone=True)`, e `criado_em` com
          `server_default=sa.text('now()')`
    - [x] Os **três** `op.create_index` do AC11 estão lá, e o `downgrade()` derruba os três
  - [x] `uv run alembic upgrade head` e conferir no `psql`: `\d reserva` e `\d item_reserva`
  - [x] **Uma migração só.** Não crie duas revisões "para separar as tabelas": elas nascem juntas,
        uma depende da outra, e um `downgrade` no meio deixaria `item_reserva` órfã
  - [x] Docstring no topo do arquivo da migração dizendo o que ela cria e por que as duas tabelas
        vêm juntas — as quatro migrações anteriores têm uma, e a do `unaccent` é o melhor exemplo

- [x] **T4. `tests/test_migracoes.py` — o schema lido do banco** (AC: 1, 5, 9, 11, 12)
  - [x] Estender o arquivo existente, **sem reescrever** nenhum dos testes que já estão lá
  - [x] `reserva` e `item_reserva` aparecem em `inspetor.get_table_names()`, com as colunas do AC1
  - [x] Tipos por `inspect`: `total_centavos` e `preco_unitario_centavos` são `BIGINT`;
        `expira_em` e `criado_em` têm `timezone is True`; os dois `id` são UUID
  - [x] As quatro chaves estrangeiras: `item_reserva.reserva_id` com `ondelete='CASCADE'`, e as
        outras três **sem** `ondelete` nas `options` — lido do banco, não do modelo, pelo mesmo
        motivo escrito em `test_os_dois_ondelete_de_evento_portaria_sao_diferentes`
  - [x] Os três índices do AC11 existem
  - [x] ⚠️ **`test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz` passa a afirmar as seis
        tabelas** — é o AC12, e é a linha que faz este arquivo continuar valendo alguma coisa

- [x] **T5. `tests/test_reserva.py` — as invariantes que o banco garante** (AC: 2, 3, 4, 6, 7, 8, 9,
      10)
  - [x] Arquivo novo, no espírito do `test_evento.py`: *"invariantes que o banco garante, não o
        Python"*. Nenhum destes testes passa por rota, service ou schema — nada disso existe
  - [x] Helpers **locais**: `_evento`, `_setor` e `_reserva`, gravando com `flush()`
  - [x] ⚠️ **Não mova os helpers do `test_evento.py` para o `conftest.py`, e não os importe de lá.**
        A convenção real da suíte é helper local por módulo: `_entrar` existe em quatro arquivos e
        `_evento_gravado` em dois, cada um moldado para o que aquele arquivo prova. O `conftest.py`
        guarda **infraestrutura** (sessão, cliente HTTP, fábrica de usuário), não fixture de
        domínio. Mexer no `test_evento.py` para "reaproveitar" é churn em código já revisado
  - [x] O organizador e o cliente vêm de `fabricar_usuario(...)`. ⚠️ O e-mail padrão dela é fixo —
        dois usuários no mesmo teste precisam de e-mails distintos
  - [x] Os casos da tabela em *Testing*, um teste cada
  - [x] `pytest.raises(IntegrityError)` no `flush()`, como o `test_evento.py` faz. O `SAVEPOINT`
        reaberto do `conftest.py` já cobre o `flush()` que falha de propósito — não invente
        `rollback` manual
  - [x] Os ACs 3 e 4 são `sessao.execute(text(...))` com `.rowcount`, no molde exato do
        `test_update_condicional_do_ad3_pedindo_mais_do_que_resta_afeta_zero_linhas`
  - [x] ⚠️ Para o AC4, `expira_em` no passado e no futuro se produzem com
        `datetime.now(timezone.utc) ± timedelta(...)` — **nunca** com `datetime.now()` sem fuso: a
        coluna é `TIMESTAMPTZ` e o `psycopg` recusa comparar ingênuo com consciente

- [x] **T6. Verificação** (AC: 12, 14)
  - [x] `uv run alembic downgrade base` → `uv run alembic upgrade head`, sem erro (AC12 literal).
        ⚠️ Executado **só contra o `rockhub_teste`**, pelo `command.downgrade`/`command.upgrade` do
        `test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz` (e pela fixture de sessão, que
        faz o mesmo a cada suíte). **Não rodei `downgrade base` no banco de desenvolvimento** — é a
        armadilha 12, e o banco do Igor tem eventos reais de conferência
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final → **316**
  - [x] Busca por `create_all` em `backend/` → **zero** em código (só as quatro menções em prosa do
        próprio README, que existem para proibi-lo)
  - [x] Busca por `Float`, `float` e `Numeric` em `app/models/` → **zero** em campo monetário (AC5).
        A única ocorrência é o comentário do `evento.py` que proíbe os três
  - [x] ⚠️ Conferir que `app/models/reserva.py`, a migração nova e `tests/test_reserva.py` **estão
        rastreados** pelo git — **não executo git** (regra do projeto), a conferência é do Igor
  - [x] **Nenhum servidor precisa subir nesta story.** Nenhum subiu
  - [x] `frontend/` **não é tocado**: nenhum `npm run build`, nenhum `tsc`, nenhum arquivo

- [x] **T7. Os READMEs** (AC: 15) — obrigatório, regra do projeto
  - [x] `backend/README.md`: seção nova `## Reserva e item de reserva`, **depois de
        `## Programação pública`** e antes de `## Convenções que nascem aqui`
    - [x] **Até cinco parágrafos, e nenhuma subseção `###`.** A régua do `CLAUDE.md` proíbe
          subseção nova e tabela nova; uma seção temática `##` para um assunto que ainda não tem
          casa é exatamente a estrutura que o README de camada declara ("seções temáticas por
          assunto") — é onde a Story 2.3 pôs `## Evento e setor`
    - [x] O que entra: as duas tabelas e para que servem; os cinco estados e por que `String` +
          `CHECK` em vez de `ENUM` nativo; as duas transições condicionais dos ACs 3 e 4, com o
          zero-linhas como sinal; por que apagar evento vendido dói; e a frase que evita a próxima
          dúvida — *nada na aplicação lê ou escreve nessas tabelas ainda*
    - [x] Atualizar *Estrutura* (`models/reserva.py` na árvore, comentário de uma linha no padrão
          das outras entradas) e *Testes* (o número novo e `test_reserva.py` na lista). Os dois são
          conteúdo operacional, não parágrafo de decisão
  - [x] `frontend/README.md` **não muda** (AC15)
  - [x] `README.md` da raiz **não é tocado**. Conferir só uma coisa: a linha
        **"Cancelamento pelo cliente"** de `#o-que-não-está-pronto` diz *"o modelo já suporta (a
        reserva tem estado que devolve estoque)"* — com esta story ela **passa a ser literalmente
        verdade** e continua valendo como está. Não reescreva → conferida em `README.md:752`,
        mantida palavra por palavra
  - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna da direita é o material do
README (T7) — é o "por quê" dele.**

| Assunto | Escolha, e o motivo dela | O que caiu, e por que não |
|---|---|---|
| Identidade de `item_reserva` | **`id` UUID próprio + `UNIQUE (reserva_id, setor_id)`.** Cada item tem identidade, e o banco recusa duas linhas do mesmo setor na mesma reserva — o `UPDATE` de estoque da 3.6 fica com um alvo só por setor, e a soma que a tela da 3.4 já faz ("3 ingressos · 2 setores") vira uma linha por setor no banco, sem ambiguidade | *PK composta `(reserva_id, setor_id)`*, o precedente literal da `evento_portaria`: o par é a identidade e não sobra coluna nenhuma — caiu porque `evento_portaria` é vínculo puro e `item_reserva` **carrega dado próprio** (quantidade e preço congelado), e o dia em que algo precisar apontar para um item (uma devolução parcial, um ingresso por item) a chave composta vira migração. *`id` sem unicidade*, que permitiria dois lotes do mesmo setor com preços diferentes: caiu porque a 3.6 teria que somar linhas antes de reservar e a tela mostraria o mesmo setor duas vezes — o mesmo argumento que já derrubou dois "Pista" no mesmo evento na Story 2.3 |
| Apagar evento, setor ou conta que já tem reserva | **O banco recusa.** `reserva.cliente_id`, `reserva.evento_id` e `item_reserva.setor_id` ficam **sem `ondelete`**, que é o `RESTRICT` do Postgres. Apagar show vendido tem que doer, do mesmo jeito que apagar quem publicou e quem foi escalado já dói hoje | *`CASCADE` em tudo*: consistente com a composição já declarada em `setor`, e um `DELETE FROM evento` limparia o rastro inteiro — caiu porque o rastro é dinheiro: um `DELETE` distraído no `psql` apagaria reserva paga sem uma linha de aviso, e não existe nenhuma rota que apague evento para justificar a facilidade. *Recusa no evento e `CASCADE` no setor*: protegeria o show e deixaria o setor sumir — caiu porque a reserva ficaria com item faltando e `total_centavos` mentindo, que é pior do que qualquer um dos dois extremos. **Consequência assumida:** o `ON DELETE CASCADE` de `setor` continua valendo para evento sem venda e deixa de valer no instante da primeira reserva — e isso é o que se quer dizer |
| Carimbos de tempo na `reserva` | **Só `criado_em`**, além do `expira_em` que o AD-4 exige. Precedente de `usuario` e `evento`; "quando a reserva mudou de estado" não é pergunta que nenhuma tela deste produto faz | *`criado_em` + `pago_em`*: o canhoto da Epic 4 poderia dizer "comprado em" — caiu porque o ingresso vai carregar a própria data de emissão (Story 3.9) e a coluna seria uma segunda resposta para a mesma pergunta. *Uma coluna por transição* (`pago_em`, `recusada_em`, `expirada_em`, `cancelada_em`): auditoria completa da máquina de estados — caiu por quatro colunas anuláveis que duplicam o que `estado` já diz, num sistema sem nenhum requisito de auditoria |
| Como `estado` existe no Postgres | **`String(20)` + `CHECK`,** com o enum em Python (`EstadoReserva(str, Enum)`). Precedente literal do `usuario.papel`, que é o mesmo problema resolvido na Story 1.3 | *Tipo `ENUM` nativo*: o banco recusaria pelo próprio tipo e o `psql` mostraria o domínio — caiu porque quebra o precedente do `papel` (duas formas de dizer a mesma coisa no mesmo schema) e porque acrescentar um estado vira `ALTER TYPE` dentro de migração Alembic, que é o ponto de atrito conhecido dessa escolha. Com `CHECK`, acrescentar um valor é um `DROP`/`CREATE` de constraint que o `downgrade()` desfaz sem cerimônia |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **`Reserva`, `ItemReserva` e `EstadoReserva` moram no mesmo arquivo, `app/models/reserva.py`.**
  Precedente duplo: `usuario.py` abriga `Usuario` + `PapelUsuario`, e `evento.py` abriga `Evento` +
  `Setor` + `evento_portaria`. O que nasce junto e não existe separado fica junto.
- **`expira_em` é `NOT NULL` e continua preenchido depois do pagamento.** Ele é o prazo com que a
  reserva nasceu, não um campo que expira e se apaga. A alternativa — anulável, zerado ao pagar —
  daria uma coluna a mais para tratar em toda consulta e nenhuma informação nova, porque `estado`
  já diz se o prazo ainda importa.
- **`estado` não tem `server_default`.** É o contrário do `vendidos`, que tem `DEFAULT 0` no schema
  de propósito, e a diferença é real: zero é o começo natural de um contador, e `PENDENTE` é uma
  **transição** — a primeira da máquina de estados. Com default, um `INSERT` que esquecesse de
  atribuir o estado passaria em silêncio como se tivesse decidido; sem ele, o banco recusa e o
  esquecimento aparece na hora. O service da 3.6 escreve `EstadoReserva.PENDENTE.value`, explícito.
- **`reserva.evento_id` fica sem índice; os outros três FKs ganham o deles.** A disciplina da Story
  2.3 é indexar a chave estrangeira **que é lida**, e as três que ganham índice têm consumidor com
  nome: `reserva.cliente_id` é o `where` de "minhas compras" (Epic 4), `item_reserva.reserva_id` é
  lido em todo carregamento de reserva e varrido a cada `DELETE` em cascata, e
  `item_reserva.setor_id` é o `where` da colheita preguiçosa da Story 3.7. `reserva.evento_id` não
  é lido por nenhuma story planejada — ele existe para a reserva saber de que show ela é, não para
  ser consultado. Índice preventivo é peso sem gargalo demonstrado, e acrescentá-lo depois é uma
  linha de migração. **Escreva o motivo no modelo**, senão o code review da epic o lê como
  esquecimento.
- **Nenhum `relationship` para `Usuario`, `Evento` ou `Setor`.** Precedente literal de
  `Evento.portarias`, que existe sem `back_populates` em `usuario.py`: um `relationship` sem
  consumidor é promessa vazia, e aqui **nenhum** dos três tem consumidor — não existe service.
  Criar `ItemReserva.setor` agora, além de não ser usado, tentaria a próxima pessoa a escrever
  `sum(item.quantidade for item in setor.itens)` e derivar disponibilidade por `COUNT`, que é
  exatamente o que o AD-13 proíbe. Quando a 3.6 precisar do setor, é uma linha e **não** é migração.
- **`Reserva.itens` não tem `order_by`.** Diferente de `Evento.setores`, aqui não existe coluna de
  ordem natural: ordenar por `setor_id` seria ordem de UUID, que é aleatória se fingindo de
  determinística. Quem exibir os itens (3.6 e 3.8) ordena pelo **nome do setor**, que é a mesma
  ordem que a página do evento já mostra — e é decisão da story que exibir, não desta.
- **`total_centavos` é redundante com a soma dos itens, e fica.** O `epics.md` pede a coluna, e ela
  congela o valor cobrado: o dia em que o organizador mudar o preço de um setor, a reserva paga tem
  que continuar dizendo quanto custou. Quem escreve é o service da 3.6; o banco só garante que não
  é negativo. **Não** ponha `CHECK` amarrando o total à soma dos itens: seria um `TRIGGER`, e o
  projeto não tem nenhum.
- **`item_reserva` não ganha `criado_em`.** Itens nascem na mesma transação da reserva; a data dela
  já responde "quando isso apareceu". Mesmo argumento que deixou `setor` sem a coluna na 2.3.
- **Nenhum dado semeado.** `seeds/semear.py` não muda: ele semeia contas, nunca eventos, e muito
  menos reservas. Semear é decisão de produto do Igor, e continua em aberto no README da raiz.

### As duas tabelas, coluna a coluna

Tabelas no singular, `snake_case`, domínio em português — `ARCHITECTURE-SPINE.md#Convenções`.

**`reserva`**

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `Uuid` | PK, `default=uuid.uuid4`. UUID porque aparece em URL (`/reservas/{id}/pagar`) — convenção da espinha |
| `cliente_id` | `Uuid` | FK → `usuario.id`, `NOT NULL`, **sem `ondelete`**, `index=True` |
| `evento_id` | `Uuid` | FK → `evento.id`, `NOT NULL`, **sem `ondelete`**, **sem índice** (suposição declarada) |
| `estado` | `String(20)` | `NOT NULL`, `CHECK` com os cinco valores. Sem `server_default` |
| `expira_em` | `DateTime(timezone=True)` | `NOT NULL`. Escrito pelo service da 3.6 como criação + 10 min (AD-4) |
| `total_centavos` | `BigInteger` | `NOT NULL`, `CHECK >= 0` (AD-11) |
| `criado_em` | `DateTime(timezone=True)` | `NOT NULL`, `server_default=func.now()` |

Constraints: `ck_reserva_estado_valido`, `ck_reserva_total_nao_negativo`.
Índice: `ix_reserva_cliente_id`.

**`item_reserva`**

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `Uuid` | PK, `default=uuid.uuid4` (decisão do Igor) |
| `reserva_id` | `Uuid` | FK → `reserva.id` **`ondelete="CASCADE"`**, `NOT NULL`, `index=True` |
| `setor_id` | `Uuid` | FK → `setor.id`, `NOT NULL`, **sem `ondelete`**, `index=True` |
| `quantidade` | `Integer` | `NOT NULL`, `CHECK > 0` |
| `preco_unitario_centavos` | `BigInteger` | `NOT NULL`, `CHECK >= 0`. É o preço **congelado** no ato da reserva, não uma cópia viva de `setor.preco_centavos` |

Constraints: `ck_item_reserva_quantidade_positiva`, `ck_item_reserva_preco_nao_negativo`,
`uq_item_reserva_reserva_id_setor_id` (**nome explícito**, AC6).
Índices: `ix_item_reserva_reserva_id`, `ix_item_reserva_setor_id`.

**Os cinco estados** (AD-4), e quem escreve cada um:

| Estado | Quem grava | Story |
|---|---|---|
| `PENDENTE` | nasce assim, já tendo consumido estoque pelo `UPDATE` do AD-3 | 3.6 |
| `PAGA` | transição condicionada a `PENDENTE`, na mesma transação que emite os ingressos (AD-14) | 3.8 / 3.9 |
| `RECUSADA` | pagamento negado; devolve o estoque | 3.8 |
| `EXPIRADA` | colheita preguiçosa, condicionada a `PENDENTE` **e** `expira_em < now()`; devolve o estoque | 3.7 |
| `CANCELADA` | **ninguém, ainda.** O cancelamento pelo cliente é corte consciente registrado no README da raiz. O valor existe no schema porque o AD-4 o fixa e porque é ele que torna o corte reversível sem migração | — |

[Fonte: ARCHITECTURE-SPINE.md#AD-4, #AD-3, #AD-11, #AD-13, #AD-14, #Convenções ·
epics.md#Story 3.5]

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `Evento` e `Setor` | `app/models/evento.py:81, 158` | **O molde do arquivo inteiro**: docstring que explica as decisões, comentário por coluna, `__table_args__` com os `CHECK` nomeados, `Mapped[...]`. ⚠️ **Não muda** |
| `evento_portaria` | `app/models/evento.py:68` | O precedente dos **dois `ondelete` diferentes na mesma tabela**, com o motivo escrito ao lado. ⚠️ **Não muda** |
| `PapelUsuario` | `app/models/usuario.py:17` | O molde do `str, Enum` de modelo + `CHECK` com a lista literal. É o precedente que o Igor mandou seguir |
| `CONVENCAO_DE_NOMES` | `app/models/base.py:13` | De onde saem `ck_`, `uq_`, `fk_`, `ix_` e `pk_`. É por causa dela que o nome da `UniqueConstraint` vai explícito |
| `models/__init__.py` | (arquivo inteiro) | Reexporta tudo e alimenta o `env.py` do Alembic. **Cresce nesta story** |
| Migração `b91316d771ae` | `migrations/versions/20260811_...evento_e_setor.py` | O molde da migração de duas tabelas com FK entre elas, `CHECK`, `UNIQUE` e `create_index` à mão |
| Migração `06c1ad5ac276` | `migrations/versions/20260811_...unaccent.py` | O `head` atual (o `down_revision` da sua) e o melhor exemplo de docstring de migração |
| `test_evento.py` | (arquivo inteiro) | **O molde do `test_reserva.py`**: helpers locais, `pytest.raises(IntegrityError)` no `flush()`, um teste por invariante. ⚠️ **Não muda** |
| `test_update_condicional_do_ad3_...` | `tests/test_evento.py:217` | **O molde exato dos ACs 3 e 4**: `sessao.execute(text(...))` e `.rowcount`, provando a operação na story em que a tabela nasce |
| `test_migracoes.py` | `tests/test_migracoes.py` | **É este arquivo que cresce** do lado do schema, e é dele a tupla de tabelas do AC12 |
| `fabricar_usuario` | `tests/conftest.py:139` | A conta gravada, com papel à escolha. ⚠️ E-mail padrão fixo — dois usuários no mesmo teste precisam de e-mails distintos |
| `sessao` | `tests/conftest.py:91` | Transação revertida com `SAVEPOINT` reaberto: o `flush()` que falha de propósito já está coberto |

**Não devem ser tocados, e não devem quebrar:** `app/api/` inteiro, `app/services/` inteiro,
`app/schemas/` inteiro, `app/core/` inteiro, `app/integrations/`, `app/main.py`,
`app/models/usuario.py`, `app/models/evento.py`, as quatro migrações existentes, `seeds/`,
`tests/conftest.py`, `tests/test_evento.py` e todos os outros testes já verdes, `docker-compose.yml`,
`pyproject.toml`, `alembic.ini`, e **`frontend/` inteiro**.

⚠️ **`app/models/__init__.py` e `tests/test_migracoes.py` são as duas exceções**, e as duas são
exceção por **acréscimo** — mais a tupla de seis tabelas, que é o AC12 e é a única linha existente
que muda em todo o repositório.

Se algum outro precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Esquecer o `models/__init__.py` e gerar uma migração vazia.** O `migrations/env.py` enxerga o
metadata por aquele import. Sem ele o `--autogenerate` roda, escreve um arquivo com `pass` nos dois
lados, o `upgrade head` passa e nada é criado — e a story parece pronta. O sintoma aparece no T4,
quando o `inspetor` não acha as tabelas.

**2. Deixar o `--autogenerate` decidir os `ondelete`.** São **quatro** chaves estrangeiras e apenas
**uma** leva `CASCADE`. O gerador tem histórico de omitir `ondelete` — o que aqui acerta três e erra
justamente a que importa para o AC8. Confira as quatro no arquivo, uma a uma, e confira de novo no
`psql`.

**3. `passive_deletes=True` esquecido no `relationship`.** Sem ele o SQLAlchemy emite
`UPDATE item_reserva SET reserva_id = NULL` antes do `DELETE`, estoura no `NOT NULL` e nunca chega
ao `CASCADE`. O teste do AC8 apaga **pela sessão**, que é o caminho que revela isso; apagar por SQL
cru passaria verde com o ORM errado.

**4. Nomear a `UniqueConstraint` pelo template.** `uq_%(table_name)s_%(column_0_name)s` produz
`uq_item_reserva_reserva_id`, que lido em voz alta diz "um item por reserva" — o oposto. Nome
explícito, como o `uq_setor_evento_id_nome` da 2.3.

**5. Criar `ENUM` nativo sem perceber.** `Mapped[EstadoReserva]` com um enum do Python faz o
SQLAlchemy inferir `sa.Enum(...)`, que no Postgres vira **tipo nativo** — exatamente a alternativa
descartada, e por um caminho silencioso. A coluna é `Mapped[str] = mapped_column(String(20), ...)`,
igual à `usuario.papel`, e o enum serve para o Python escrever `.value`.

**6. Comparar `expira_em` com `datetime.now()` sem fuso.** A coluna é `TIMESTAMPTZ`; ingênuo
contra consciente é `TypeError` no Python e comportamento indefinido no banco. É
`datetime.now(timezone.utc)`, sempre — e no AC4 o `now()` de dentro do `UPDATE` é o do Postgres, que
é o certo para a colheita da 3.7.

**7. Achar que o AC9 quebrou o `test_apagar_evento_leva_os_setores_junto`.** Ele não quebra: aquele
teste apaga um evento **sem** reserva, e o `CASCADE` de `setor` continua igual. O que muda é o
evento **com** reserva, e é caso novo, em arquivo novo. Se aquele teste ficar vermelho, a chave
estrangeira do item saiu com `CASCADE` por engano.

**8. Escrever um service "pequeno" para não deixar a tabela sozinha.** Reservar é a 3.6 inteira, com
o `UPDATE` condicional do AD-3, a máquina de estados e o `409 ESTOQUE_INSUFICIENTE`. Uma função
`criar_reserva()` aqui nasceria sem rota, sem schema e sem teste de contrato — e a 3.6 a reescreveria.

**9. Derivar estoque a partir de `item_reserva`.** Assim que a tabela existir, `SELECT
sum(quantidade) FROM item_reserva WHERE setor_id = ...` vira a resposta mais óbvia para "quantos
foram vendidos". É **proibido** (AD-13): a resposta é `setor.vendidos`. Esta story não faz nenhuma
consulta, mas é a story que cria a tentação — e por isso a proibição vai escrita no docstring do
modelo novo, não só nos três lugares onde já está.

**10. Duas migrações "para separar as tabelas".** Elas nascem juntas e uma referencia a outra; um
`downgrade` no meio deixaria `item_reserva` apontando para uma tabela que não existe.

**11. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest`
falhar com `os error 4551`, chame pelo módulo: `uv run python -m pytest`. Vale igual para o
`alembic`: `uv run python -m alembic ...`.

**12. O banco de desenvolvimento é do Igor.** Ele tem eventos reais de conferência. O `upgrade head`
desta story só acrescenta tabelas vazias e é seguro — mas **não apague nada, não semeie nada** e não
rode `downgrade base` contra ele. O `downgrade`/`upgrade` do AC12 é no `rockhub_teste`, que é o que
o `conftest.py` já faz a cada sessão.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    models/
      reserva.py                 # novo — EstadoReserva, Reserva, ItemReserva
      __init__.py                # +3 reexports
  migrations/
    versions/
      2026MMDD_<rev>_cria_tabelas_reserva_e_item_reserva.py   # novo, filho de 06c1ad5ac276
  tests/
    test_reserva.py              # novo
    test_migracoes.py            # cresce, e a tupla passa a ter seis tabelas
  README.md
```

Não existe, e não deve passar a existir nesta story: `app/schemas/reserva.py`,
`app/services/reserva.py`, `app/api/cliente.py`, rota de reserva, rota de pagamento, `PaymentGateway`,
tabela `ingresso`, cronômetro, seed de reserva, qualquer arquivo em `frontend/`, dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar. Nenhum teste desta story toca rede.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| `reserva` e `item_reserva` existem, com as colunas esperadas | `test_migracoes.py` | 1 |
| `total_centavos` e `preco_unitario_centavos` são `BIGINT`; `expira_em` e `criado_em` têm fuso | `test_migracoes.py` | 5 |
| `item_reserva.reserva_id` tem `ondelete=CASCADE`; as outras três FKs **não** têm `ondelete` | `test_migracoes.py` | 9 |
| Os três índices do AC11 existem | `test_migracoes.py` | 11 |
| `downgrade base` derruba as **seis** tabelas e `upgrade head` refaz todas | `test_migracoes.py` | 12 |
| Reserva gravada ganha `id` e `criado_em` com fuso, e o estado que foi escrito | `test_reserva.py` | 1, 5 |
| `estado` fora dos cinco valores → `IntegrityError` | `test_reserva.py` | 2 |
| Os cinco valores válidos são aceitos | `test_reserva.py` | 2 |
| `PENDENTE → PAGA` condicional afeta 1 linha; repetido, afeta 0 | `test_reserva.py` | 3 |
| `PENDENTE → EXPIRADA` com `expira_em < now()` afeta 1; com `expira_em` futuro, afeta 0 | `test_reserva.py` | 4 |
| `total_centavos` negativo → `IntegrityError` | `test_reserva.py` | 7 |
| `quantidade` zero e negativa → `IntegrityError` | `test_reserva.py` | 7 |
| `preco_unitario_centavos` negativo → `IntegrityError` | `test_reserva.py` | 7 |
| Dois itens do mesmo setor na mesma reserva → `IntegrityError` | `test_reserva.py` | 6 |
| O mesmo setor em **outra** reserva é aceito | `test_reserva.py` | 6 |
| Apagar a reserva leva os itens junto (pela sessão) | `test_reserva.py` | 8 |
| Apagar evento **com** reserva → `IntegrityError` | `test_reserva.py` | 9 |
| Apagar o cliente que reservou → `IntegrityError` | `test_reserva.py` | 9 |
| Apagar evento **sem** reserva continua levando os setores junto | (já existe, `test_evento.py`) | 9, 14 |
| FK inexistente em `cliente_id`, `evento_id`, `reserva_id` e `setor_id` → `IntegrityError` | `test_reserva.py` | 10 |

**Frontend: nada.** Esta story não toca a camada.

**Baseline: 293 testes passando** (Story 3.4).

### Inteligência das stories anteriores

**Da 2.3 — é ela o gêmeo desta story, não a 3.4.** Mesma forma: duas tabelas, uma migração, um
arquivo de modelo, um arquivo de teste novo, `test_migracoes.py` crescendo, nenhum consumidor. Três
coisas de lá valem literalmente aqui:

- **Provar a operação que justifica a forma da tabela** (o AC9 de lá, os ACs 3 e 4 daqui). Uma
  tabela que nasce sem isso é uma tabela que ninguém sabe se está certa.
- **`passive_deletes` e `ON DELETE CASCADE` são duas metades** que precisam concordar; a metade do
  ORM é a que se esquece.
- **`--autogenerate` é ponto de partida, não resultado.** A lista de conferência da T3 é a de lá,
  adaptada.

**Da 3.4 — o teto e a soma.** `maximo_por_compra = 6` é **por compra**, e a tela já deixa a pessoa
somar vários setores na mesma escolha. É por isso que `item_reserva` é lista e por isso que a
unicidade é `(reserva_id, setor_id)` e não só `reserva_id`. Quem cobra o teto do lado do servidor é
a 3.6 — **não** ponha `CHECK (quantidade <= 6)` aqui: o teto é da compra inteira, não de um item, e
uma constraint por item cobriria a coisa errada com cara de estar certa.

**Da 3.1 à 3.4 — o hábito do AD-13.** As quatro stories públicas gastaram docstring, comentário e
teste de varredura para manter `capacidade` e `vendidos` fora do contrato do cliente e para não
derivar disponibilidade por `COUNT`. Esta é a story que cria a tabela sobre a qual o `COUNT` errado
seria escrito. O aviso muda de lugar: sai dos serviços de leitura e entra no modelo novo.

**Da 1.3 — o `conftest.py` não migra o banco de desenvolvimento.** A URL do Alembic é definida em
código e há uma guarda que recusa qualquer banco que não se chame `rockhub_teste`. Não mexa nisso, e
não exporte `DATABASE_URL_TESTE` "para testar mais rápido".

[Fonte: _bmad-output/implementation-artifacts/2-3-modelo-de-evento-e-setor.md ·
3-4-ver-o-evento-e-seus-setores.md · 1-3-modelo-de-usuario-e-primeira-migracao.md]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| Python | 3.12 | `enum.Enum`, `datetime` com fuso |
| SQLAlchemy | 2.0.51 | `Mapped[...]` + `mapped_column`, `relationship` com `passive_deletes` |
| Alembic | 1.19.1 | `revision --autogenerate`, `downgrade base` / `upgrade head` |
| PostgreSQL | 16 | `TIMESTAMPTZ`, `BIGINT`, `CHECK`, `ON DELETE` |
| pytest | (instalado) | `pytest.raises(IntegrityError)` no `flush()` |

**Nenhuma dependência nova.** `pyproject.toml` e `uv.lock` não mudam. Nada de FastAPI, Pydantic,
`httpx` ou frontend nesta story.

### Escopo — o que NÃO fazer aqui

Rota · schema Pydantic · service · `PaymentGateway` · `UPDATE` de estoque de verdade · cronômetro ·
tela · tabela `ingresso` · seed de reserva · qualquer arquivo em `frontend/`.

Quatro tentações concretas:

- **"Já escrevo o `POST /reservas`, a tabela está aqui."** É a Story 3.6 inteira, com a garantia
  mais pontuada do desafio (AD-3) e o `409 ESTOQUE_INSUFICIENTE`. Esta story entrega schema.
- **"Já crio a `ingresso` junto, é a mesma epic."** É a Story 3.9, e ela traz `assinatura`, `nonce`
  e o HMAC do AD-5 — decisões que ninguém tomou ainda.
- **"Ponho um `TRIGGER` para o `total_centavos` bater com a soma dos itens."** O projeto não tem
  nenhum trigger, e a soma é responsabilidade do service que escreve os dois (3.6). Uma regra em
  PL/pgSQL é uma segunda fonte de verdade em uma linguagem que nenhum teste deste projeto lê.
- **"Aproveito e crio o `relationship` para `Setor`, vai precisar."** Vai — na 3.6, e lá é uma
  linha sem migração. Aqui ele é código sem consumidor e um convite ao `COUNT` que o AD-13 proíbe.

### Project Structure Notes

`app/models/` passa a ter **quatro** módulos (`base`, `usuario`, `evento`, `reserva`) e o schema
passa a ter **seis** tabelas. A regra de agrupamento continua a mesma desde a 1.3: um módulo por
agregado, com o que não existe fora dele junto — e `item_reserva`, que carrega dado próprio, é
classe mapeada, ao contrário da `evento_portaria`, que é `Table` do Core por não ter coluna nenhuma
além das duas chaves.

É a **quinta** migração do projeto e a primeira desde a 3.2 que cria tabela. A cadeia fica
`b750db91bf49 → b91316d771ae → c7cb4a29b7f3 → 06c1ad5ac276 → (esta)`.

É também a primeira vez que uma chave estrangeira do projeto **bloqueia** uma cascata declarada
antes: `evento → setor` é `CASCADE` desde a 2.3, e a partir daqui ela para no `item_reserva` assim
que existir uma venda. Isso não é conflito — é a ordem de prioridade sendo dita pelo schema:
composição some junto, dinheiro não some.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5] — os dois blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] — as stories 3.6, 3.7, 3.8 e 3.9, que
  são as consumidoras destas tabelas
- [Source: ARCHITECTURE-SPINE.md#AD-4] — a máquina de estados, o `expira_em` de 10 minutos, a
  expiração preguiçosa e a transição sempre condicionada ao estado anterior
- [Source: ARCHITECTURE-SPINE.md#AD-3] — o `UPDATE` condicional de estoque, que a 3.6 executa
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte da disponibilidade; é
  proibido derivá-la com `COUNT` sobre reserva
- [Source: ARCHITECTURE-SPINE.md#AD-14] — ingresso só nasce na transação que marca `PAGA`; é o AC3
  que torna isso possível
- [Source: ARCHITECTURE-SPINE.md#AD-11] — dinheiro em centavos `BIGINT`, tempo em `TIMESTAMPTZ` UTC
- [Source: ARCHITECTURE-SPINE.md#Convenções] — `snake_case`, domínio em português, UUID no que
  aparece em URL, migração Alembic para toda mudança de schema, nunca `create_all`
- [Source: ARCHITECTURE-SPINE.md#Semente Estrutural] — o ER com `RESERVA ||--o{ ITEM_RESERVA` e
  `SETOR ||--o{ ITEM_RESERVA`
- [Source: backend/app/models/evento.py] — o molde do módulo de modelo, dos `CHECK` nomeados e dos
  dois `ondelete` diferentes
- [Source: backend/app/models/usuario.py:17-30] — `PapelUsuario` + `CHECK`, o precedente do `estado`
- [Source: backend/app/models/base.py:13-19] — a convenção de nomes de constraint
- [Source: backend/tests/test_evento.py:217-239] — o molde dos ACs 3 e 4
- [Source: backend/tests/test_migracoes.py:154-178] — a tupla de tabelas que precisa crescer
- [Source: backend/migrations/versions/20260811_b91316d771ae_cria_tabelas_evento_e_setor.py] — o
  molde da migração
- [Source: _bmad-output/implementation-artifacts/2-3-modelo-de-evento-e-setor.md] — a story gêmea
- [Source: CLAUDE.md] — READMEs ao fim de toda story, em primeira pessoa, régua de cinco parágrafos
  por camada; git é responsabilidade do Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`.
   Ao terminar, avise que a story está pronta para commit
2. **Atualize o README da camada antes de dar a story por concluída** — até cinco parágrafos.
   Documentação não bloqueia o commit: aplique o código, rode a suíte, mostre o resultado,
   **depois** escreva. `frontend/README.md` e o `README.md` da raiz **não** são tocados aqui
3. **Decisão de produto ou de modelagem é do Igor.** As quatro desta story estão respondidas e as
   nove suposições estão declaradas. Se aparecer uma quinta — coluna a mais, tabela a mais,
   constraint a mais — **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest` e para o `alembic` local
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** Esta story não
   precisa de servidor nenhum
6. **Conferência visual é do Igor** — e aqui não há tela para conferir
7. **Nenhuma dependência nova**
8. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum e não cria pasta nova — só arquivos dentro de pastas já rastreadas
9. **O code review é ao fim da Epic 3**, não a cada story

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **A raiz recebe decisão nova?** Escrevi para **não** tocar o `README.md` da raiz. A régua diz que
   entra o que faria quem avalia ver um sistema diferente, e as quatro decisões daqui são de schema:
   a identidade do item, o `RESTRICT`, os carimbos e a forma do enum. A que mais chega perto é
   *"apagar show vendido dói"*, e mesmo ela é consequência de um princípio que a raiz **já**
   registra em *O estoque é protegido pelo banco, não pela aplicação*. A máquina de estados em si é
   AD-4 e ganha sua entrada quando o comportamento existir — 3.6, 3.7 e 3.8.
2. **`CANCELADA` nasce sem ninguém que a escreva.** O valor está no AD-4 e no schema, e o
   cancelamento pelo cliente é corte consciente registrado na raiz. Vale a pena a Epic 3 gastar meia
   story num `POST /reservas/{id}/cancelar`? O modelo suporta, e o custo real é a tela.
3. **Dez minutos é o prazo certo?** Está no AD-4 e vira constante do service na 3.6, não coluna. Um
   avaliador que queira ver a expiração acontecer vai precisar esperar dez minutos ou mexer no banco
   — se quiser que isso seja demonstrável no roteiro da Epic 6, o número precisa ser configurável, e
   essa decisão é melhor tomada na 3.6 do que aqui.
4. **Continua sem evento semeado**, e agora com duas tabelas a mais esperando por um. É a mesma
   pergunta da 3.1, 3.2, 3.3 e 3.4: numa máquina limpa, o avaliador não tem em que clicar para
   chegar até a reserva.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5[1m]`), via `bmad-dev-story`.

### Debug Log References

- `uv run python -m alembic revision --autogenerate -m "cria tabelas reserva e item_reserva"` →
  detectou as duas tabelas e os três índices, nada além. Revisão `6448866ff965`, filha de
  `06c1ad5ac276`
- `uv run python -m alembic upgrade head` → `06c1ad5ac276 -> 6448866ff965` sem erro
- `docker compose exec db psql -c "\d reserva" -c "\d item_reserva"` → schema conferido no banco:
  os sete e os cinco campos, os quatro `CHECK`, a `UNIQUE`, os quatro `ondelete` e os três índices
- `uv run python -m pytest` → **316 passed** (baseline 293)
- ⚠️ Os `.exe` da virtualenv continuam bloqueados pelo Windows App Control nesta máquina: todos os
  comandos foram chamados por módulo (`uv run python -m alembic`, `-m pytest`), como manda a
  armadilha 11

### Completion Notes List

**O que foi entregue:** as tabelas `reserva` e `item_reserva`, criadas por uma migração só, mais o
enum `EstadoReserva` em Python. Nenhuma rota, nenhum schema Pydantic, nenhum service, nenhuma tela
— o recorte da story foi respeitado à risca. `app/models/evento.py`, `app/models/usuario.py`,
`tests/conftest.py` e `tests/test_evento.py` não tiveram uma linha alterada, e `frontend/` não foi
tocado.

**O `--autogenerate` acertou os quatro `ondelete` de primeira**, contra o que a armadilha 2 previa:
saiu `ondelete='CASCADE'` em `item_reserva.reserva_id` e nenhum `ondelete` nas outras três. Conferi
mesmo assim, no arquivo e depois no `psql`. Os quatro nomes de `CheckConstraint` saíram da convenção
como esperado, e a `UniqueConstraint` saiu com o nome explícito.

**Os ACs 3 e 4 são os testes que mais importam aqui.** Os dois `UPDATE` condicionais do AD-4 estão
provados por `.rowcount` — `PENDENTE → PAGA` afeta 1 na primeira vez e 0 na segunda; a colheita de
`EXPIRADA` alcança a reserva vencida e não alcança a que ainda vale. É o AC9 da Story 2.3 repetido
de propósito: a tabela nasce com a operação que justifica sua forma já provada, antes de existir
service para executá-la.

**23 testes novos, 316 no total.** 19 em `test_reserva.py` (os cinco estados aceitos, o sexto
recusado pelo banco, as duas transições, as três constraints de quantidade e dinheiro, a unicidade
por reserva nos dois sentidos, o `CASCADE` dos itens apagado pela sessão, as três recusas de apagar
venda e as quatro chaves estrangeiras inexistentes) e 4 em `test_migracoes.py`. Nenhum teste
existente precisou mudar de asserção: a única linha já escrita que mudou no repositório inteiro é a
tupla do `test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz`, que passou de quatro tabelas
para seis — o AC12.

**Acrescentei um teste que a tabela de *Testing* não listava:** `apagar setor com item reservado →
IntegrityError`. O AC9 diz "o banco recusa nos três casos" e nomeia evento, setor e conta, mas a
tabela de testes só trazia dois. Preferi cobrir o terceiro a deixar o AC meio provado.

**Duas coisas ficaram deliberadamente sem cobertura de teste automatizado**, e as duas são decisões
da story, não esquecimento: `reserva.evento_id` sem índice está afirmado pela **ausência** no
`test_so_as_chaves_estrangeiras_lidas_da_compra_tem_indice` (asserto que `evento_id` não aparece
entre as colunas indexadas, para que acrescentar um índice "por segurança" quebre o teste e obrigue
a conversa); e o `downgrade base`/`upgrade head` do AC12 roda contra o `rockhub_teste`, nunca contra
o banco de desenvolvimento do Igor.

**Para o Igor, antes do commit:** três arquivos novos precisam entrar no índice do git —
`backend/app/models/reserva.py`, `backend/migrations/versions/20260812_6448866ff965_cria_tabelas_reserva_e_item_reserva.py`
e `backend/tests/test_reserva.py`. Não executo git, então essa conferência é sua.

### File List

**Novos**

- `backend/app/models/reserva.py`
- `backend/migrations/versions/20260812_6448866ff965_cria_tabelas_reserva_e_item_reserva.py`
- `backend/tests/test_reserva.py`

**Modificados**

- `backend/app/models/__init__.py`
- `backend/tests/test_migracoes.py`
- `backend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-5-modelo-de-reserva.md`

**Não tocados, de propósito:** `frontend/` inteiro, `README.md` da raiz, `app/models/evento.py`,
`app/models/usuario.py`, `app/api/`, `app/services/`, `app/schemas/`, `app/core/`, `seeds/`,
`tests/conftest.py`, `tests/test_evento.py`, as quatro migrações anteriores, `pyproject.toml` e
`uv.lock`.

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-12 | Story 3.5 implementada. Migração `6448866ff965`, filha de `06c1ad5ac276`, cria `reserva` e `item_reserva` numa revisão só — o schema passa a ter seis tabelas. `app/models/reserva.py` traz `EstadoReserva`, `Reserva` e `ItemReserva`, com o `estado` em `String(20)` + `CHECK` (nunca `ENUM` nativo), `expira_em` e `criado_em` em `TIMESTAMPTZ`, dinheiro em `BIGINT` de centavos, `UNIQUE (reserva_id, setor_id)` de nome explícito, e as quatro chaves estrangeiras com o `ondelete` que a decisão do Igor pede: `CASCADE` só em `item_reserva.reserva_id`, e `RESTRICT` nas três que protegem venda. 23 testes novos (19 em `test_reserva.py`, 4 em `test_migracoes.py`), entre eles os dois `UPDATE` condicionais do AD-4 provados por `.rowcount` antes de existir service; a suíte foi de 293 para **316**. Nenhum teste existente mudou de asserção — a única linha já escrita alterada no repositório é a tupla de tabelas do teste de ida e volta, que passou de quatro para seis. `backend/README.md` ganhou a seção `## Reserva e item de reserva`; `frontend/README.md` e o `README.md` da raiz não foram tocados |
| 2026-08-12 | Story 3.5 criada e contextualizada. Quatro decisões do Igor incorporadas: **`item_reserva` ganha `id` UUID próprio + `UNIQUE (reserva_id, setor_id)`**, e não a PK composta da `evento_portaria`, porque o item carrega dado próprio e a unicidade é o que dá um alvo só por setor ao `UPDATE` da 3.6; **apagar evento, setor ou conta com reserva é recusado pelo banco** (as três FKs sem `ondelete`), com a consequência assumida de o `CASCADE` de `setor` deixar de valer no instante da primeira venda; **só `criado_em`** além do `expira_em` que o AD-4 exige, porque nenhuma tela pergunta quando a reserva mudou de estado; e **`String(20)` + `CHECK`** para o `estado`, no precedente literal do `usuario.papel`, em vez do `ENUM` nativo do Postgres. Quinze ACs escritos sobre os dois blocos do `epics.md`, entre eles os ACs 3 e 4, que são o AC9 da Story 2.3 repetido de propósito: as duas transições condicionais do AD-4 provadas por `.rowcount` na story em que a tabela nasce, antes de existir service para executá-las. Nove suposições declaradas — entre elas o `estado` **sem** `server_default`, ao contrário do `vendidos`, e `reserva.evento_id` sem índice com o motivo escrito no modelo — e quatro perguntas registradas para o Igor |
