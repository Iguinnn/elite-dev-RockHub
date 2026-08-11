---
baseline_commit: "e1aceff — feat: Story 2.2 - Buscar atracao no catalogo (branch Epic-2---Publicação-de-eventos-pelo-organizador)"
---

# Story 2.3: Modelo de evento e setor

Status: ready-for-dev

Epic 2 — Publicação de eventos pelo organizador · **A segunda story de fundação da epic, e a
primeira migração desde a 1.3.** Hoje o organizador acha o show no catálogo e não pode fazer nada
com ele: não existe tabela para gravar evento nem setor. Esta story cria as duas — e **só isso**.
Nenhuma rota, nenhum schema Pydantic, nenhum service, nenhuma tela. Publicar é a Story 2.4.

Como desenvolvedor,
quero as tabelas de evento e setor criadas por migração,
para que preço e capacidade pertençam ao setor, não ao evento.

**O critério de pronto é o schema, não o comportamento.** Ao fim desta story `alembic upgrade head`
num banco vazio cria `usuario`, `evento` e `setor`; `downgrade base` derruba as três; e o banco
recusa, sozinho, todo estado de estoque que o AD-3 proíbe. Nada na aplicação sabe que essas tabelas
existem — e isso é o recorte, não uma falta.

## Acceptance Criteria

1. **Given** o banco migrado
   **When** eu inspeciono o schema
   **Then** `evento` tem `id` UUID, `organizador_id`, `nome`, `data_hora` `TIMESTAMPTZ`, `local`,
   `cidade`, `imagem_url`, `origem_externa_id` e `publicado_em`
   **And** `setor` tem `id`, `evento_id`, `nome`, `capacidade`, `vendidos` e `preco_centavos`
   **And** as duas tabelas nascem numa **única** migração Alembic, filha de `b750db91bf49`

2. **Given** a tabela `setor`
   **When** eu tento gravar `vendidos` negativo ou maior que `capacidade`
   **Then** o banco recusa por `CHECK` — AD-3, e a constraint se chama `ck_setor_estoque_valido`
   **And** a recusa é do **banco**, não do Python: o teste prova com `IntegrityError` no `flush()`

3. **Given** qualquer valor monetário
   **When** eu o inspeciono
   **Then** `preco_centavos` é `BIGINT`, nunca `float` nem `NUMERIC` — AD-11
   **And** o nome do campo carrega o sufixo `_centavos`, como a convenção da espinha exige

4. **Given** a tabela `setor`
   **When** eu tento gravar `capacidade = 0` ou negativa, ou `preco_centavos` negativo
   **Then** o banco recusa nos dois casos, por `ck_setor_capacidade_positiva` e
   `ck_setor_preco_nao_negativo`
   **And** o motivo de cada uma está escrito no modelo: setor com capacidade zero nasce esgotado e
   ninguém entende por quê; preço negativo é dinheiro andando para trás

5. **Given** um evento com um setor chamado `Pista`
   **When** eu tento gravar um segundo setor `Pista` no **mesmo** evento
   **Then** o banco recusa por `uq_setor_evento_id_nome`
   **And** o mesmo nome em **outro** evento é aceito — a unicidade é por evento, não global

6. **Given** um evento com setores
   **When** o evento é apagado
   **Then** os setores dele somem junto, por `ON DELETE CASCADE` na chave estrangeira
   **And** o `relationship` do ORM concorda com o banco (`passive_deletes=True`) — as duas metades
   dizendo coisas diferentes é o defeito que esta story existe para não deixar nascer

7. **Given** um `setor` com `evento_id` que não existe
   **When** eu tento gravá-lo
   **Then** o banco recusa por chave estrangeira — `fk_setor_evento_id_evento`

8. **Given** `evento.publicado_em`
   **When** eu gravo um evento sem preenchê-lo
   **Then** a coluna aceita `NULL`, e o evento existe sem estar publicado
   **And** `criado_em` vem preenchido de qualquer jeito, com `TIMESTAMPTZ` gerado pelo banco
   **And** isso é a decisão do Igor que torna verificável o AC da Story 3.1 (*"eventos não
   publicados não aparecem"*) — ver *Decisões que o Igor tomou*

9. **Given** o `UPDATE` condicional que o AD-3 fixa
   **When** eu o executo pedindo mais do que resta
   ```sql
   UPDATE setor SET vendidos = vendidos + :q
    WHERE id = :id AND vendidos + :q <= capacidade
   ```
   **Then** ele afeta **zero linhas** e não levanta exceção — é assim que a Epic 3 vai descobrir
   "sem estoque"
   **And** existe um teste que prova isso **agora**, na story em que a tabela nasce

10. **Given** o projeto inteiro
    **When** eu procuro criação de schema
    **Then** continua não existindo `create_all` em lugar nenhum — nem em teste
    **And** `alembic downgrade base` derruba as três tabelas, e `upgrade head` refaz todas

11. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar
    **Then** ela passa inteira, e os **121** testes anteriores continuam verdes
    **And** o número final está registrado

12. **Given** os READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta as duas tabelas, as quatro constraints e o `CASCADE`
    **And** `README.md` da raiz ganha as quatro decisões desta story **com a alternativa descartada**
    de cada uma
    **And** `frontend/README.md` **não muda** — nada da camada de frontend foi tocado

> **De onde vem cada critério.** O `epics.md` traz **três** blocos para a Story 2.3: as colunas das
> duas tabelas, o `CHECK` do AD-3 e o dinheiro em centavos. Eles viraram os ACs **1, 2 e 3**.
>
> **AC4, AC5, AC6 e AC8** são as quatro decisões que o Igor tomou antes de a story ser escrita.
> **AC7** é a consequência de existir chave estrangeira e vale ser provada uma vez. **AC9** existe
> porque o AD-3 descreve um `UPDATE` que nenhuma story desta epic executa — o primeiro consumidor é
> a Epic 3 — e uma tabela que nasce sem provar a operação que justifica sua forma é uma tabela que
> ninguém sabe se está certa. **AC10** repete literalmente o AC2 da Story 1.3: é a garantia que se
> perde sem alguém conferindo a cada migração nova. **AC11 e AC12** são regra do projeto.

## Tasks / Subtasks

- [ ] **T1. `app/models/evento.py` — `Evento` e `Setor`** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [ ] Arquivo novo, **as duas classes juntas**. `Setor` não tem vida fora de `Evento` — ver
        *Suposições declaradas*
  - [ ] Docstring do módulo explicando o que o arquivo resolve, no estilo de `models/usuario.py`:
        preço e capacidade pertencem ao **setor** (AD-12), `vendidos` é a **única** fonte de verdade
        da disponibilidade (AD-13), e o `CHECK` é rede de segurança do AD-3 — não a regra em si, que
        vive no `UPDATE` condicional do service da Epic 3
  - [ ] `Evento`: colunas exatamente conforme a tabela em *As duas tabelas, coluna a coluna*.
        Nada além delas
  - [ ] `Setor`: idem, com as **quatro** constraints em `__table_args__`
  - [ ] Estilo tipado do SQLAlchemy 2.0: `Mapped[...]` + `mapped_column(...)`. **Nunca** o
        `Column()` do estilo 1.x — é a convenção fixada na Story 1.3
  - [ ] `relationship` nos dois lados, com `back_populates`, `cascade="all, delete-orphan"` e
        `passive_deletes=True`. O motivo do `passive_deletes` está em *Armadilhas*, armadilha 3 —
        sem ele o ORM desfaz o `CASCADE` que a migração declarou
  - [ ] `app/models/__init__.py`: reexportar `Evento` e `Setor` e acrescentá-los ao `__all__`.
        **É o import que o `migrations/env.py` usa** — sem ele o `--autogenerate` produz migração
        vazia (armadilha 1)

- [ ] **T2. A migração** (AC: 1, 10)
  - [ ] `cd backend && uv run alembic revision --autogenerate -m "cria tabelas evento e setor"`
  - [ ] Conferir no arquivo gerado, linha a linha — `--autogenerate` é ponto de partida, não
        resultado:
    - [ ] `down_revision = 'b750db91bf49'` (a migração da `usuario`), **não** `None`
    - [ ] `evento` é criada **antes** de `setor` no `upgrade()`, e derrubada **depois** no
          `downgrade()`. Ordem trocada quebra a chave estrangeira
    - [ ] As quatro constraints do `setor` estão no `create_table`, com os nomes que a convenção
          produz (`ck_setor_estoque_valido`, `ck_setor_capacidade_positiva`,
          `ck_setor_preco_nao_negativo`, `uq_setor_evento_id_nome`)
    - [ ] O `ForeignKeyConstraint` carrega `ondelete='CASCADE'`
    - [ ] `preco_centavos` saiu como `sa.BigInteger()`, não `sa.Integer()`
    - [ ] `data_hora`, `publicado_em` e `criado_em` saíram com `sa.DateTime(timezone=True)`
    - [ ] O índice de `setor.evento_id` está lá (`op.create_index`) — e o `downgrade()` o derruba
  - [ ] `uv run alembic upgrade head` e conferir no `psql`: `\d evento` e `\d setor`
  - [ ] **Uma migração só.** Não crie duas revisões "para separar as tabelas": elas nascem juntas,
        uma depende da outra, e um `downgrade` no meio deixaria `setor` órfã

- [ ] **T3. Testes de schema em `tests/test_migracoes.py`** (AC: 1, 3, 10)
  - [ ] Estender o arquivo existente, **sem reescrever** os quatro testes que já estão lá
  - [ ] `evento` e `setor` aparecem em `inspetor.get_table_names()`
  - [ ] Tipos por `inspect`: `preco_centavos` é `BIGINT`; `data_hora`, `publicado_em` e `criado_em`
        têm `timezone is True`; `id` das duas é UUID
  - [ ] `publicado_em` é `nullable`; `data_hora` e `criado_em` não são
  - [ ] A chave estrangeira de `setor` aponta para `evento` com `ondelete='CASCADE'`
        (`inspetor.get_foreign_keys("setor")` → `options["ondelete"]`)
  - [ ] ⚠️ **`test_downgrade_base_derruba_a_tabela_e_upgrade_head_a_refaz` precisa passar a afirmar
        as três tabelas**, não só `usuario`. Ele é o AC10, e hoje uma migração nova quebrada
        passaria por ele sem ser notada

- [ ] **T4. `tests/test_evento.py` — as invariantes que o banco garante** (AC: 2, 4, 5, 6, 7, 8, 9)
  - [ ] Arquivo novo, no espírito do `test_usuario.py`: *"invariantes que o banco garante, não o
        Python"*
  - [ ] Helper local `_evento(sessao, organizador, **campos)` gravando um evento com `flush()`.
        **Não** mexa no `conftest.py` — a convenção do projeto é extrair no segundo consumidor, e
        esta story tem um só (precedente de `Campo` e `Botao`, registrado no README da raiz)
  - [ ] O organizador vem de `fabricar_usuario(PapelUsuario.ORGANIZADOR)`, fixture que já existe.
        ⚠️ O e-mail padrão dela é fixo — dois usuários no mesmo teste precisam de e-mails distintos
  - [ ] Os dez casos da tabela em *Testing*, um teste cada
  - [ ] `pytest.raises(IntegrityError)` no `flush()`, como o `test_usuario.py` faz. O `SAVEPOINT`
        reaberto do `conftest.py` já cobre o `flush()` que falha de propósito — não invente
        `rollback` manual

- [ ] **T5. Verificação** (AC: 10, 11)
  - [ ] `uv run alembic downgrade base` → `uv run alembic upgrade head`, sem erro (AC10 literal)
  - [ ] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [ ] Busca por `create_all` em `backend/` → **zero**, inclusive em teste
  - [ ] Busca por `float`, `Numeric` e `Float` nos modelos → **zero** em campo monetário (AC3)
  - [ ] ⚠️ Conferir que `app/models/evento.py`, a migração nova e `tests/test_evento.py` **estão
        rastreados** pelo git antes de dar a story por pronta — `.gitignore` nascido de template
        Python já engoliu pasta uma vez neste projeto (Story 1.9)

- [ ] **T6. Os READMEs** (AC: 12) — obrigatório, regra do projeto
  - [ ] `backend/README.md`:
    - [ ] Seção nova **Evento e setor** (depois de *Catálogo da Ticketmaster*): as duas tabelas
          coluna a coluna, as quatro constraints com o motivo de cada uma, o `CASCADE`, e a frase
          que evita a próxima dúvida — *nada na aplicação lê ou escreve nessas tabelas ainda*
    - [ ] *Estrutura*: `models/evento.py` na árvore, com o comentário de uma linha no padrão das
          outras entradas
    - [ ] *Testes*: o número novo, e `test_evento.py` na lista
    - [ ] *Histórico desta camada*: entrada **Story 2.3**, no formato das anteriores
  - [ ] `README.md` da raiz:
    - [ ] Quatro decisões novas em *Decisões: por que isso e não aquilo*, cada uma com **o que
          caiu e por quê** — a matéria-prima está em *Decisões que o Igor tomou*
    - [ ] ⚠️ *O que não está pronto*: a linha **"Evento publicado entre os dados semeados"** diz
          hoje que *"`Evento` e `Setor` só passam a existir na Story 2.3"*. Isso deixa de ser
          verdade com esta story — reescreva a frase mantendo a dívida (o seed continua sem evento),
          não apague a linha
  - [ ] **`frontend/README.md` não muda, e é intencional** — nenhum arquivo de `frontend/` foi
        tocado. Precedente literal da Story 1.3. Não invente conteúdo para cumprir a regra dos três
  - [ ] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T6).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| `publicado_em` | **Nullable — rascunho é possível no schema** | *`NOT NULL` com `server_default=now()`*: mais honesto com o produto de hoje, porque publicar é o único caminho de criação e a 2.4 grava o evento já no ar — uma coluna a menos para tratar em toda consulta. Caiu porque o AC da Story 3.1 diz literalmente *"eventos não publicados não aparecem"*, e com `NOT NULL` esse critério vira vacuidade: não existiria evento não publicado para provar coisa nenhuma. Nullable custa uma coluna anulável e torna aquele AC verificável — insere um evento com `publicado_em = NULL`, prova que ele não aparece na programação. Custo assumido: existe um estado que nenhuma tela produz hoje |
| `origem_externa_id` | **Nullable, sem unicidade** | *`UNIQUE`*: protegeria contra publicar a mesma atração duas vezes por engano na avaliação, mas quebra o caso legítimo da turnê — o mesmo registro do catálogo vira uma data em São Paulo e outra no Rio — e o erro que o organizador veria na segunda data seria um `IntegrityError` cru que alguém teria que traduzir na 2.4. *`NOT NULL` sem unicidade*: descreve exatamente o fluxo da Epic 2 e fecha a porta do evento sem catálogo; caiu por ser uma trava de banco para uma regra de produto que pode mudar sem migração |
| Apagar evento | **`ON DELETE CASCADE`** | *`RESTRICT` (o padrão)*: nada some por acidente, e como nenhuma story apaga evento a diferença só apareceria em SQL rodado à mão. Caiu por declarar uma relação mais frouxa do que a real: setor é **composição**, não associação — um `Pista` sem evento não significa nada, e o schema deve dizer isso. Custo assumido: apagar evento por engano leva os setores junto, sem aviso |
| Constraints do `setor` | **AD-3 + `capacidade > 0` + `preco_centavos >= 0` + nome único no evento** | *Só o `CHECK` do AD-3*, que é o mínimo que o `epics.md` pede, deixando capacidade e preço para o schema Pydantic da 2.4 — onde o erro sai bonito em vez de `IntegrityError`. Caiu porque a rede de segurança do AD-3 existe justamente para o caso em que algum caminho escapa do schema, e o mesmo raciocínio vale para os outros dois. *AD-3 + os dois `CHECK`, sem unicidade de nome*: permitiria dois "Pista" no mesmo evento, o que **pode** ser proposital (dois lotes com preços diferentes) — caiu porque a tela do cliente na 3.4 mostraria dois itens de nome idêntico e ele escolheria no escuro |

### ⚠️ Uma tensão declarada, para você não "corrigir" por conta própria

`origem_externa_id` é **nullable** no banco, e o `README.md` da raiz registra a decisão
*"Publicação exige atração do catálogo — sem cadastro manual de evento"*. As duas coisas convivem de
propósito, e a distinção é a que vale a pena entender:

- **O banco** aceita evento sem origem externa. É uma coluna, não uma regra.
- **A regra** — todo evento nasce de uma atração do catálogo — é do produto, e vive no schema de
  entrada e no service da **Story 2.4**. É lá que ela é aplicada e testada.

Não "conserte" isso pondo `NOT NULL` na coluna. A escolha foi feita com essa consequência à vista, e
está registrada acima com a alternativa descartada. Se você achar que ela está errada, **fale com o
Igor** — não mude o schema.

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **`Evento` e `Setor` moram no mesmo arquivo, `app/models/evento.py`.** Precedente literal do
  `usuario.py`, que abriga `Usuario` e `PapelUsuario`: o que nasce junto e não existe separado fica
  junto. A alternativa é `evento.py` + `setor.py`, um arquivo por tabela — mais previsível de achar,
  ao custo de dois imports circulares em potencial (`back_populates` nos dois sentidos) e de dois
  arquivos que nunca são lidos separadamente.
- **`evento.criado_em` entra, mesmo não estando no AC do `epics.md`.** Mesmo raciocínio de três
  linhas que justificou a coluna na `usuario` (Story 1.3), com um motivo a mais que é específico
  daqui: com `publicado_em` anulável, um rascunho não teria **nenhuma** data — nem quando foi
  criado, nem quando foi publicado. É a única coluna além das que o AC lista. Não acrescente outras
  "por precaução".
- **`setor` não ganha `criado_em`.** Setores nascem na mesma transação do evento (Story 2.4); a data
  do evento já responde "quando isso apareceu".
- **`setor.evento_id` ganha índice; `evento.data_hora` e `evento.organizador_id` não.** O Postgres
  **não** cria índice automático para chave estrangeira, e este é lido em todo carregamento de
  evento e varrido a cada `DELETE` em cascata — uma linha, e o custo aparece cedo. Os outros dois
  entram quando alguém medir lentidão: a programação da Story 3.1 e a lista da 2.6 vão varrer uma
  tabela de dezenas de linhas na avaliação, e índice preventivo é peso sem gargalo demonstrado.
- **Nenhum `enum` novo.** `PapelUsuario` continua sendo o único enum do projeto. Não existe
  `StatusEvento`: o estado de publicação é `publicado_em` ser `NULL` ou não.

### As duas tabelas, coluna a coluna

Tabelas no singular, `snake_case`, domínio em português — `ARCHITECTURE-SPINE.md#Convenções`.

**`evento`**

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `Uuid` | Chave primária, `default=uuid.uuid4` no Python — igual à `usuario`, sem depender de extensão do Postgres |
| `organizador_id` | `Uuid`, `NOT NULL` | `ForeignKey("usuario.id")`. **Sem `ondelete`** — apagar um organizador com eventos publicados deve doer, e nenhuma story apaga usuário |
| `nome` | `String(200)`, `NOT NULL` | O nome do show, copiado do catálogo (AD-1) |
| `data_hora` | `DateTime(timezone=True)`, `NOT NULL` | `TIMESTAMPTZ` em UTC — AD-11. Quem preenche é o organizador, na 2.4 |
| `local` | `String(200)`, `NOT NULL` | O nome da casa de show. A 2.4 pede ao organizador; o catálogo entra como sugestão |
| `cidade` | `String(120)`, **nullable** | O catálogo pode não trazer (`ItemDoCatalogo.cidade` é `str \| None`) |
| `imagem_url` | `String(500)`, **nullable** | Idem. 500 é folga larga para as URLs da Ticketmaster (~100 caracteres) |
| `origem_externa_id` | `String(64)`, **nullable** | O id da Discovery. Nullable e sem unicidade — ver *Decisões* e a *tensão declarada* |
| `publicado_em` | `DateTime(timezone=True)`, **nullable** | `NULL` = rascunho. Quem preenche é a 2.4 |
| `criado_em` | `DateTime(timezone=True)`, `NOT NULL`, `server_default=func.now()` | Suposição declarada acima |

**`setor`**

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `Uuid` | Chave primária, `default=uuid.uuid4` |
| `evento_id` | `Uuid`, `NOT NULL`, `index=True` | `ForeignKey("evento.id", ondelete="CASCADE")` |
| `nome` | `String(80)`, `NOT NULL` | "Pista", "Camarote". Único **por evento** |
| `capacidade` | `Integer`, `NOT NULL` | `> 0` |
| `vendidos` | `Integer`, `NOT NULL`, `server_default=text("0")` | A **única** fonte de verdade da disponibilidade — AD-13 |
| `preco_centavos` | `BigInteger`, `NOT NULL` | Inteiro em centavos, `>= 0` — AD-11. **Nunca** `Float` nem `Numeric` |

**As quatro constraints, em `__table_args__` de `Setor`:**

```python
__table_args__ = (
    # AD-3: rede de segurança do banco. A regra de verdade é o UPDATE
    # condicional do service da Epic 3 — esta constraint é o que sobra de pé
    # se algum caminho da aplicação escapar dela.
    CheckConstraint(
        "vendidos >= 0 AND vendidos <= capacidade", name="estoque_valido"
    ),
    # Capacidade zero produz um setor que nasce esgotado, aparece na tela e
    # ninguém entende por que não dá para comprar.
    CheckConstraint("capacidade > 0", name="capacidade_positiva"),
    # Preço negativo é dinheiro andando para trás.
    CheckConstraint("preco_centavos >= 0", name="preco_nao_negativo"),
    # Dois "Pista" no mesmo evento deixariam o cliente escolhendo no escuro na
    # tela da Story 3.4. Por evento, não global: outro show pode ter Pista.
    UniqueConstraint("evento_id", "nome", name="uq_setor_evento_id_nome"),
)
```

⚠️ **O nome da `UniqueConstraint` vai explícito, e as três `CheckConstraint` não.** A convenção da
`Base` (`models/base.py`) é `ck_%(table_name)s_%(constraint_name)s` — daí `name="estoque_valido"`
virar `ck_setor_estoque_valido` sozinho. Mas o template de unicidade é
`uq_%(table_name)s_%(column_0_name)s`, que **só usa a primeira coluna**: sem nome explícito a
constraint sairia `uq_setor_evento_id`, escondendo que ela cobre duas colunas. Passar o nome
completo à mão resolve, e é o único lugar do projeto onde isso acontece.

[Fonte: epics.md#Story 2.3 · ARCHITECTURE-SPINE.md#AD-3, #AD-11, #AD-12, #AD-13 · backend/app/models/base.py]

### O que já existe e esta story estende — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `Base` com convenção de nomes | `app/models/base.py` | Herde. **Não** crie outra `DeclarativeBase`, e não mexa na `CONVENCAO_DE_NOMES` |
| Modelo de referência | `app/models/usuario.py` | O estilo exato: docstring que explica o porquê, `Mapped`/`mapped_column`, `CheckConstraint` nomeado em `__table_args__` |
| Reexport para o Alembic | `app/models/__init__.py` | Acrescente `Evento` e `Setor`. É o que faz o `--autogenerate` enxergar as tabelas |
| Migração de referência | `migrations/versions/20260810_b750db91bf49_cria_tabela_usuario.py` | O formato do arquivo gerado, e o `down_revision` que a nova aponta |
| Fixture de banco | `tests/conftest.py:75` | `engine_teste` migra `rockhub_teste` do zero por Alembic, uma vez por sessão |
| Transação revertida | `tests/conftest.py:91` | A fixture `sessao`, com o `SAVEPOINT` reaberto que já cobre `flush()` que falha de propósito |
| Fábrica de usuário | `tests/conftest.py:139` | `fabricar_usuario(PapelUsuario.ORGANIZADOR)` — o dono do evento nos testes |
| Testes de invariante | `tests/test_usuario.py` | O padrão: `pytest.raises(IntegrityError)` no `flush()` |
| Testes de schema | `tests/test_migracoes.py` | `sqlalchemy.inspect` sobre `engine_teste` |
| `ItemDoCatalogo` | `app/schemas/catalogo.py` | **Só como referência de nome e nulidade** dos campos que a 2.4 vai copiar. Esta story não importa nem toca esse arquivo |

**Não devem ser tocados, e não devem quebrar:** `app/main.py`, `app/api/`, `app/services/`,
`app/schemas/`, `app/integrations/`, `app/core/`, `seeds/semear.py`, `alembic.ini`,
`migrations/env.py`, `docker-compose.yml`, `pyproject.toml`, e **tudo** dentro de `frontend/`.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade. As três primeiras já custaram tempo a alguém neste projeto ou são o
modo de falha clássico da ferramenta.

**1. Modelo não reexportado gera migração vazia.** O `migrations/env.py` importa `app.models` — se
`Evento` e `Setor` não estiverem no `__init__.py`, as classes nunca entram em `Base.metadata` e o
`--autogenerate` produz um `upgrade()` com `pass`. Sintoma: migração gerada sem nenhum
`create_table`. É a armadilha 2 da Story 1.3, e ela volta em toda tabela nova.

**2. `--autogenerate` erra ordem e constraint.** Ele acerta bem o caso simples, e este não é
totalmente simples: duas tabelas com dependência entre elas, quatro constraints e um índice. Leia o
arquivo gerado inteiro antes de aplicar — a checklist está na T2. Especificamente, confira o
`downgrade()`: ele precisa derrubar `setor` **antes** de `evento`.

**3. `ON DELETE CASCADE` no banco não basta — o ORM desfaz.** Esta é a mais sutil da lista. Com um
`relationship` normal, apagar um `Evento` pela sessão faz o SQLAlchemy carregar os setores e emitir
`UPDATE setor SET evento_id = NULL` antes do `DELETE` — que estoura em `NOT NULL` e nem chega no
`CASCADE` que a migração declarou. As duas metades precisam concordar:

```python
setores: Mapped[list["Setor"]] = relationship(
    back_populates="evento",
    cascade="all, delete-orphan",
    passive_deletes=True,   # ← sem isto, o ORM tenta desassociar antes de apagar
)
```

`passive_deletes=True` é o que manda o SQLAlchemy confiar no banco. O AC6 existe para provar que a
combinação funciona, e o teste dele **precisa** apagar pela sessão (`sessao.delete(evento)`), não
por SQL cru — SQL cru provaria só a metade que já se sabe.

**4. A convenção de nomes cobre `ck` e `fk`, mas a `uq` composta engana.** Explicado acima, no bloco
das constraints. O sintoma é uma constraint chamada `uq_setor_evento_id` que parece dizer "um setor
por evento" — o oposto do que ela faz.

**5. `server_default=text("0")` para `vendidos`, não `default=0`.** O `default` do Python só vale
para linha inserida pela sessão; o `server_default` grava o `DEFAULT 0` no schema e vale também para
`INSERT` vindo de migração, seed ou `psql`. Mesmo raciocínio do `server_default=func.now()` do
`criado_em` da `usuario` — duas fontes de valor padrão é uma a mais do que se quer.

**6. `BigInteger` para dinheiro, e a suíte precisa provar isso.** `Integer` estoura em ~21 milhões
de reais, o que é irrelevante aqui e ainda assim é o tipo errado: o AD-11 diz `BIGINT`, e a única
forma de a decisão sobreviver a um `--autogenerate` distraído é um teste lendo o tipo do banco.

**7. Rodar só o arquivo novo não é verificação.** `pytest tests/test_evento.py` não roda a fixture
de sessão inteira do jeito que a suíte roda, e a Story 2.1 já perdeu tempo com uma regressão que só
apareceu no `uv run pytest` completo. O AC11 pede a suíte inteira.

**8. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Documentado desde a
Story 1.1. Se `uv run alembic ...` falhar com `os error 4551`, chame pelo módulo:
`uv run python -m alembic upgrade head`. Os comandos canônicos do README continuam os curtos.

### O `UPDATE` condicional, e por que ele é testado aqui

O AD-3 descreve a operação que a Epic 3 vai usar para reservar. Nenhuma story desta epic a executa —
o primeiro consumidor é a 3.6. Mesmo assim ela é testada aqui, e o motivo é direto: a forma da
tabela (`capacidade` e `vendidos` como colunas separadas, em vez de um `disponivel` decrescente)
existe **só** para tornar esse `UPDATE` possível. Uma tabela que nasce sem provar a operação que
justifica seu formato é uma tabela que ninguém sabe se está certa.

```python
resultado = sessao.execute(
    text(
        "UPDATE setor SET vendidos = vendidos + :q "
        " WHERE id = :id AND vendidos + :q <= capacidade"
    ),
    {"q": 5, "id": setor.id},
)
assert resultado.rowcount == 0   # pediu mais do que resta: zero linhas, sem exceção
```

**Zero linhas afetadas é o sinal de "sem estoque"** — não uma exceção, não um `SELECT` anterior. O
`CHECK` da tabela nunca chega a ser violado nesse caminho, e é isso que se quer provar: a condição
do `WHERE` barra antes, e o `CHECK` fica de rede para quem não usar o `WHERE`.

⚠️ **Isto é um teste, não uma função.** Não crie `services/evento.py` nem nenhum helper para
encapsular esse `UPDATE` nesta story — ele nasce no service da Epic 3, junto do consumidor real.

[Fonte: ARCHITECTURE-SPINE.md#AD-3, #AD-13]

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    models/
      __init__.py              # +Evento, +Setor no reexport e no __all__
      evento.py                # NOVO — Evento e Setor
  migrations/
    versions/
      2026...._cria_tabelas_evento_e_setor.py   # NOVO — down_revision = b750db91bf49
  tests/
    test_evento.py             # NOVO — as invariantes que o banco garante
    test_migracoes.py          # +schema das duas tabelas; downgrade cobre as três
  README.md                    # seção nova + estrutura + testes + histórico
README.md                      # 4 decisões + a linha do seed reescrita
```

Não existe, e não deve passar a existir nesta story: `app/services/evento.py`,
`app/schemas/evento.py`, `app/api/` com qualquer rota nova, `seeds/` com evento,
`app/models/setor.py`, migração de `evento_portaria` (é a 2.5), qualquer enum de status.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura]

### Testing

**Postgres real, migrado pelo próprio Alembic** — a decisão da Story 1.3, e ela vale aqui sem
mudança. A fixture `engine_teste` roda `downgrade base` + `upgrade head` contra `rockhub_teste`
antes da suíte, o que faz **toda** execução verificar a migração desta story de ida e de volta antes
de qualquer asserção. **Docker Desktop precisa estar no ar.**

`tests/test_evento.py` — dez casos:

| O que o teste prova | AC |
|---|---|
| Evento gravado sem `id` gera UUID; `criado_em` vem preenchido e com timezone | 8 |
| Evento gravado sem `publicado_em` existe, com a coluna em `None` | 8 |
| `vendidos` maior que `capacidade` levanta `IntegrityError` | 2 |
| `vendidos` negativo levanta `IntegrityError` | 2 |
| `capacidade = 0` levanta `IntegrityError` | 4 |
| `preco_centavos` negativo levanta `IntegrityError` | 4 |
| Dois setores com o mesmo nome no mesmo evento levantam `IntegrityError` | 5 |
| O mesmo nome de setor em **outro** evento é aceito | 5 |
| `sessao.delete(evento)` leva os setores junto (contagem vai a zero) | 6 |
| `setor` com `evento_id` inexistente levanta `IntegrityError` | 7 |
| O `UPDATE` condicional do AD-3 pedindo mais do que resta afeta **zero** linhas | 9 |

`tests/test_migracoes.py` — quatro asserções novas, no arquivo que já existe:

| O que o teste prova | AC |
|---|---|
| `evento` e `setor` existem depois do `upgrade head` | 1 |
| `preco_centavos` é `BIGINT`; as três colunas de data têm `timezone is True` | 1, 3 |
| `publicado_em` é anulável, `data_hora` e `criado_em` não | 8 |
| A FK de `setor` aponta para `evento` com `ondelete='CASCADE'` | 6 |
| O `downgrade base` derruba **as três** tabelas — teste existente, estendido | 10 |

**Baseline: 121 testes passando** (`uv run python -m pytest --collect-only -q`, conferido em
2026-08-11). Registre o número final no `backend/README.md` e nas notas de conclusão.

**Frontend: nada.** Esta story não tem verificação manual de tela porque não tem tela.

### Inteligência das stories anteriores

**Da 1.3 — a story que criou este mesmo tipo de coisa:**

- **A convenção de nomes da `Base` foi criada exatamente para este momento.** A Story 1.3 escreveu:
  *"isso vale para todas as tabelas das Epics 2 a 5 — a `Base` nasce certa agora ou todas herdam o
  problema"*. Esta é a primeira story a colher isso. Não redeclare a convenção, não a ajuste
- **`--autogenerate` é ponto de partida, não resultado** — a 1.3 registrou isso e teve sorte (a
  migração da `usuario` não precisou de correção manual). Esta story tem quatro constraints, uma FK
  com `ondelete` e um índice; a chance de precisar de ajuste é maior
- **A fixture não pode migrar o banco de desenvolvimento.** `_exigir_banco_de_teste` já protege
  isso e roda **antes** do `downgrade base`. Não mexa nessa parte do `conftest.py`
- **"Cada tabela nasce na story que a usa, com as constraints que aquela story precisa
  justificar"** — a 1.3 escreveu isso recusando criar `evento` e `setor` na mesma migração da
  `usuario`, e citou nominalmente *"a `setor` sem o `CHECK` do AD-3 seria pior que não existir, e o
  AD-3 só é decidido de verdade na Story 2.3"*. É esta story. O `CHECK` é o AC2

**Da 2.1 e 2.2 (a epic corrente):**

- **A suíte inteira é a verificação, não o arquivo novo.** A 2.1 quebrou um teste de cookie por uma
  mudança em `Settings` que a story não previa, e só apareceu no `pytest` completo
- **O `ItemDoCatalogo` já define quais campos do catálogo podem ser `None`** (`atracao`,
  `imagem_url`, `local`, `cidade`). A nulidade das colunas de `evento` foi decidida olhando para
  ele — mas `evento.local` é `NOT NULL` mesmo assim, porque quem preenche é o organizador na 2.4, e
  não o catálogo
- **Nenhuma dependência nova.** A 2.1 acrescentou `httpx` e explicou por que ele é runtime e não
  dev. Esta story não acrescenta nada: `sqlalchemy` e `alembic` já estão lá

**Do estado do repositório:** branch `Epic-2---Publicação-de-eventos-pelo-organizador`, com a 2.2
commitada em `e1aceff`. Stories 2.1 e 2.2 em `review` — o code review é ao fim da epic. Uma única
migração no repositório hoje (`b750db91bf49`), e ela é a raiz da cadeia.

[Fonte: _bmad-output/implementation-artifacts/1-3-*.md · 2-1-*.md · 2-2-*.md · sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| SQLAlchemy | 2.0.51 | `Mapped`/`mapped_column`, `relationship(passive_deletes=True)`, `BigInteger` |
| Alembic | 1.19.1 | `revision --autogenerate`, `down_revision` encadeado |
| PostgreSQL | 16 | `CHECK`, `UNIQUE` composto, FK com `ON DELETE CASCADE`, `BIGINT`, `TIMESTAMPTZ` |
| psycopg | 3.3.4 | Driver — a URL é `postgresql+psycopg://`, já normalizada pela `Settings` |

Nada é instalado nesta story. `pyproject.toml` e `uv.lock` **não mudam**.

[Fonte: ARCHITECTURE-SPINE.md#Stack · backend/pyproject.toml]

### Escopo — o que NÃO fazer aqui

Rota, schema Pydantic, service, tela, seed com evento, `evento_portaria` (2.5), reserva e ingresso
(Epic 3), qualquer `"use client"`, qualquer arquivo em `frontend/`.

Cinco tentações concretas:

- **"Já crio o `services/evento.py`, a 2.4 vai precisar."** Service sem consumidor é service que a
  próxima story reescreve — a regra é da Story 1.3, e ela recusou `services/usuario.py` pelo mesmo
  motivo. A 2.4 é quem sabe o que aquele service precisa fazer
- **"Já semeio um evento, o README diz que falta."** Diz mesmo, e é dívida registrada — mas semear
  exige decidir qual show, com que data, com que setores e com que preços, e isso é decisão de
  produto do Igor, não subproduto de uma story de schema
- **"Crio `evento_portaria` junto, é uma tabela pequena."** É a Story 2.5, e ela carrega o AD-7
  inteiro: a chave primária composta, a regra de "publicar exige ao menos um escalado", e a recusa
  de escalar quem não tem papel `PORTARIA`. Nada disso é decidido nesta story
- **"Ponho um `status` em vez de `publicado_em` nulo, fica mais explícito."** A decisão está tomada
  e registrada acima com a alternativa descartada. Um enum de status é uma terceira forma de dizer a
  mesma coisa, e as três precisariam concordar para sempre
- **"Escrevo o `revision` à mão, é mais rápido que rodar o autogenerate."** É, e perde a conferência
  que o Alembic faz contra o `metadata` — a migração escrita à mão diverge do modelo em silêncio, e
  a divergência só aparece no `alembic check` que este projeto não roda

### Project Structure Notes

Esta story ocupa **só `backend/`**, e dentro dele só `models/`, `migrations/` e `tests/`. É a
primeira migração desde a 1.3 e a primeira vez que o projeto tem **duas** revisões encadeadas — o
`down_revision` deixa de ser `None` e a cadeia começa a existir de verdade. As próximas, na ordem
que a 1.3 previu: 2.5 (`evento_portaria`), 3.5 (`reserva`, `item_reserva`), 3.9 (`ingresso`), 4.3
(`share_token`), 5.2 (`usado_em`, `validado_por`).

É também a primeira tabela do projeto com **chave estrangeira** e com **relacionamento no ORM** — a
`usuario` não tem nem uma nem outra. Daí a atenção do AC6 e da armadilha 3: as decisões de cascata
tomadas aqui são o precedente das quatro tabelas seguintes, todas elas com FK.

`app/services/` e `app/schemas/` **não ganham morador nesta story**, e é proposital: o schema nasce
antes do comportamento, e cada camada aparece quando tem consumidor. Mesmo padrão da 1.3, que criou
`models/` sem tocar em `services/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] — os três blocos de AC originais:
  colunas de `evento` e `setor`, o `CHECK` do AD-3, dinheiro em centavos
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR2, FR8, FR16 e o objetivo da epic
- [Source: ARCHITECTURE-SPINE.md#AD-3] — o `UPDATE` condicional e o `CHECK` como rede de segurança;
  é o AC2 e o AC9
- [Source: ARCHITECTURE-SPINE.md#AD-11] — dinheiro em centavos (`BIGINT`, sufixo `_centavos`),
  tempo em `TIMESTAMPTZ` UTC; é o AC3
- [Source: ARCHITECTURE-SPINE.md#AD-12] — setores definidos pelo organizador; preço e capacidade
  pertencem ao setor, nunca ao evento
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `setor.vendidos` é a única fonte de verdade da
  disponibilidade; é proibido derivar com `COUNT`
- [Source: ARCHITECTURE-SPINE.md#AD-1] — o catálogo é **copiado** na publicação; é o motivo de
  `nome`, `local`, `cidade`, `imagem_url` e `origem_externa_id` serem colunas de `evento`
- [Source: ARCHITECTURE-SPINE.md#Convenções de Consistência] — `snake_case`, UUIDv4 em tudo que
  aparece em URL, migração Alembic sempre, nunca `create_all`
- [Source: ARCHITECTURE-SPINE.md#Semente Estrutural] — o diagrama de entidades: `EVENTO ||--o{
  SETOR`, `USUARIO ||--o{ EVENTO`
- [Source: ARCHITECTURE-SPINE.md#Árvore] — `models/` e `migrations/` no backend
- [Source: backend/app/models/base.py] — a convenção de nomes de constraint, e por que ela existe
- [Source: backend/app/models/usuario.py] — o modelo de referência: estilo, docstring, `__table_args__`
- [Source: backend/app/models/__init__.py] — o reexport que o Alembic enxerga
- [Source: backend/migrations/versions/20260810_b750db91bf49_cria_tabela_usuario.py] — a migração
  raiz e o formato do arquivo gerado
- [Source: backend/migrations/env.py] — `target_metadata`, `compare_type=True`, resolução de URL
- [Source: backend/tests/conftest.py:75] — `engine_teste`, que migra `rockhub_teste` do zero
- [Source: backend/tests/conftest.py:91] — a fixture `sessao` e o `SAVEPOINT` reaberto
- [Source: backend/tests/conftest.py:139] — `fabricar_usuario`, o dono do evento nos testes
- [Source: backend/tests/test_usuario.py] — o padrão de teste de invariante de banco
- [Source: backend/tests/test_migracoes.py] — o padrão de teste de schema por `inspect`
- [Source: backend/app/schemas/catalogo.py] — quais campos do catálogo podem ser `None`
- [Source: README.md#o-que-não-está-pronto] — a linha do evento semeado, que esta story reescreve
- [Source: README.md#publicação-exige-atração-do-catálogo] — a decisão que convive com
  `origem_externa_id` anulável; ver *tensão declarada*
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os READMEs antes de dar a story por concluída.** As quatro entradas de decisão da T6
   são a parte que o desafio avalia. `frontend/README.md` fica intocado de propósito
3. **Decisão de produto ou de modelagem é do Igor.** As quatro desta story estão respondidas e as
   cinco suposições estão declaradas. Se aparecer uma quinta — coluna a mais, índice novo, nome de
   tabela — **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest` e para o `alembic upgrade`
5. **Nenhuma dependência nova.** `pyproject.toml` e `uv.lock` não mudam
6. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que a migração nova e `models/evento.py` foram rastreados (T5)
7. **O code review é ao fim da epic**, não a cada story. Ao terminar a 2.3, o próximo passo é a
   Story 2.4 — mas só quando o Igor mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **Qual show vira o evento semeado, e em que story?** O `README.md` registra a dívida ("o
   enunciado pede um evento já publicado junto das quatro contas") e aponta para "o seed da Epic 2".
   Com `evento` e `setor` existindo a partir daqui, a dívida deixa de ter impedimento técnico —
   falta decidir o show, a data, os setores e os preços, e em qual story isso entra (2.4, 2.6 ou uma
   story nova de seed).
2. **A `data_hora` do evento vem do catálogo ou o organizador digita sempre?** Continua aberta desde
   a 2.1 — o `ItemDoCatalogo` não carrega data. Se a 2.4 for pré-preencher, o schema do catálogo
   ganha um sétimo campo e o `evento.data_hora` passa a ter duas origens possíveis.
3. **Um evento pode ficar sem setor depois de publicado?** A 2.4 recusa publicar sem setor
   (`EVENTO_SEM_SETOR`), mas o banco aceita `evento` sem `setor` — e precisa aceitar, porque os dois
   são gravados na mesma transação. Se um dia existir tela de editar evento (hoje é corte
   consciente), remover o último setor de um evento publicado é uma regra que alguém vai ter que
   escrever.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Story 2.3 criada e contextualizada. Quatro decisões do Igor incorporadas: `publicado_em` anulável, permitindo rascunho no schema (em vez de `NOT NULL` com `server_default=now()`, que é mais honesto com o produto de hoje mas tornaria vacuidade o AC da Story 3.1, *"eventos não publicados não aparecem"* — sem estado não publicado não há o que provar); `origem_externa_id` anulável e sem unicidade (em vez de `UNIQUE`, que protegeria contra duplicata acidental mas quebraria o caso da turnê — mesma atração, duas datas — devolvendo um `IntegrityError` cru para a 2.4 traduzir; ou de `NOT NULL`, que é o fluxo real da epic mas trava no banco uma regra de produto que pode mudar sem migração); `ON DELETE CASCADE` na FK de `setor` (em vez de `RESTRICT`, que nada apagaria por acidente mas declararia associação onde existe composição — um "Pista" sem evento não significa nada); e quatro constraints no `setor` em vez de só o `CHECK` do AD-3 (a alternativa mínima deixaria capacidade e preço para o Pydantic da 2.4, onde o erro sai bonito — caiu porque a rede de segurança do AD-3 existe exatamente para o caminho que escapa do schema; e a variante sem unicidade de nome permitiria dois "Pista" no mesmo evento, deixando o cliente escolher no escuro na tela da 3.4). Nove ACs acrescentados aos três do `epics.md`, entre eles o AC9 — o `UPDATE` condicional do AD-3 provado na story em que a tabela nasce, porque a forma da tabela existe só para torná-lo possível. Cinco suposições declaradas (as duas classes no mesmo arquivo, `criado_em` no evento, `setor` sem `criado_em`, índice só na FK, nenhum enum de status) e três perguntas registradas para as stories seguintes. Tensão declarada em destaque: `origem_externa_id` anulável convive de propósito com a decisão de README *"publicação exige atração do catálogo"* — a regra vive no service da 2.4, não no banco |
