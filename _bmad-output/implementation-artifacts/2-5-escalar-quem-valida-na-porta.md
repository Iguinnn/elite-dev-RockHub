---
baseline_commit: "f4e02fd — feat: Story 2.4 - Publicar um evento com seus setores (branch Epic-2---Publicação-de-eventos-pelo-organizador). Árvore limpa: as Stories 2.1 a 2.4 estão commitadas. Migração `head`: b91316d771ae. Suíte: 164 testes passando."
---

# Story 2.5: Escalar quem valida na porta

Status: review

Epic 2 — Publicação de eventos pelo organizador · **A story que paga a dívida da anterior.**
A 2.4 publicou de verdade, e publicou contrariando o AD-7 de propósito: hoje é possível criar um
evento sem ninguém autorizado a validar ingresso nele, e isso está escrito no `README.md` da raiz
como janela datada. Esta story fecha a janela — a mesma rota `POST /organizador/eventos` passa a
exigir ao menos um usuário de portaria escalado, e a linha de *O que não está pronto* deixa de
descrever uma dívida para descrever um fato.

Como organizador,
quero indicar qual usuário de portaria vai trabalhar no meu evento,
para que ninguém de fora consiga validar ingressos dele.

Quatro peças: a tabela `evento_portaria` por migração, a exigência dentro do `publicar()` que já
existe, a rota `GET /organizador/portarias` que alimenta a tela, e o passo 3 do formulário. **A
validação na portaria é a Epic 5** — esta story só cria o vínculo; ninguém o lê ainda.

## Acceptance Criteria

1. **Given** o banco migrado por esta story
   **When** eu inspeciono o schema
   **Then** existe a tabela `evento_portaria` com `evento_id` e `usuario_id`, **chave primária
   composta** pelas duas colunas
   **And** `evento_id` referencia `evento.id` com `ON DELETE CASCADE` — apagar um evento leva a
   escala junto, mesmo raciocínio do `setor` na Story 2.3
   **And** `usuario_id` referencia `usuario.id` **sem** `ondelete` — apagar quem já foi escalado
   deve doer, mesmo raciocínio do `organizador_id` na 2.3
   **And** `downgrade base` derruba a tabela e `upgrade head` a refaz, com o nome dela na lista
   nominal do `test_migracoes.py`

2. **Given** o modelo
   **When** eu leio `app/models/evento.py`
   **Then** `Evento.portarias` existe como `relationship(secondary=...)` para `Usuario`
   **And** a associação é uma `Table` do Core, não uma classe ORM: ela não tem coluna própria
   nenhuma, e uma classe daria a impressão de que um dia terá
   **And** **não** existe o lado inverso em `Usuario` — "os eventos em que fui escalado" é a
   Story 5.1, e criá-lo aqui seria um `relationship` sem consumidor

3. **Given** que estou publicando um evento
   **When** o corpo chega sem `portaria_ids` (ausente, ou lista vazia)
   **Then** recebo `422` com código `EVENTO_SEM_PORTARIA` — AD-7
   **And** **nada** é gravado: nem o evento, nem os setores, nem a escala
   **And** a recusa acontece no service, antes de qualquer `add`, como as duas da 2.4

4. **Given** um corpo que erra **duas** coisas — sem setor e sem portaria
   **When** eu publico
   **Then** recebo `EVENTO_SEM_SETOR`, não `EVENTO_SEM_PORTARIA`
   **And** essa ordem não é estética: é o que mantém verdes, sem tocá-los, os testes de recusa da
   Story 2.4, que mandam corpo sem `portaria_ids` porque o campo não existia

5. **Given** que escalo uma conta que **não** tem papel `PORTARIA`
   **When** eu publico
   **Then** recebo `422` com código `PORTARIA_INVALIDA`
   **And** um `usuario_id` que **não existe** devolve o **mesmo** código e a mesma mensagem — a rota
   não vira oráculo de "esse id já existiu?", pela mesma disciplina do login da Story 1.4
   **And** um `portaria_ids` com id em formato inválido é `422` do Pydantic (`DADOS_INVALIDOS`),
   porque o campo é `list[UUID]`

6. **Given** que escalo três pessoas de uma vez
   **When** eu publico
   **Then** as três linhas existem em `evento_portaria`, ligadas a este evento
   **And** o mesmo id repetido no corpo é **deduplicado em silêncio**, sem erro e sem linha
   duplicada — ao contrário do `SETOR_DUPLICADO`, repetir a mesma pessoa não muda o que ela é
   **And** há teto de `max_length=20` no campo, mesmo motivo do `setores` da 2.4

7. **Given** a publicação bem-sucedida
   **When** a resposta chega
   **Then** `EventoSaida` traz `portarias`, cada uma com `id`, `nome` e `email`
   **And** `senha_hash` não aparece em lugar nenhum da resposta — nem aqui, nem na rota do AC8

8. **Given** que estou autenticado como organizador
   **When** eu chamo `GET /organizador/portarias`
   **Then** recebo `200` com todas as contas de papel `PORTARIA`, com `id`, `nome` e `email`,
   **ordenadas por nome**
   **And** organizador e cliente **não** aparecem na lista
   **And** a rota lê o banco por um service — router não toca `Session`, é o paradigma da espinha

9. **Given** a mesma rota
   **When** um cliente ou a própria portaria a chama
   **Then** recebo `403` com `SEM_PERMISSAO`
   **And** sem cookie de sessão recebo `401` com `NAO_AUTENTICADO`, **não** `403`
   **And** a proteção é `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` na assinatura — AD-9

10. **Given** o seed de avaliação
    **When** eu o rodo
    **Then** existe uma **segunda** conta de portaria, e o total de contas semeadas passa a ser cinco
    **And** rodar de novo continua devolvendo `mantida` para todas, sem duplicar nem sobrescrever
    **And** os testes do seed deixam de contar `4` na mão e passam a derivar de `CONTAS` — do
    contrário toda conta nova quebra seis testes que não têm nada a ver com ela

11. **Given** a tela `/organizador/publicar` com uma atração escolhida
    **When** eu chego ao fim do passo 2
    **Then** aparece **3 · Escale a portaria**, com o kicker `Obrigatório` ao lado
    **And** abaixo há a frase *"Só quem for escalado aqui poderá validar ingressos deste evento."*
    **And** o passo 3 vive **dentro do mesmo `<form>`** do passo 2: é uma publicação só, um `POST`
    só, e a escala é atômica com o evento
    **And** o título do passo 3 mora **dentro** da ilha, não na `page.tsx` — ele precisa sumir junto
    com o formulário quando a confirmação toma o lugar

12. **Given** o passo 3
    **When** eu procuro alguém
    **Then** há um campo de busca com o texto **"Consulte pelo nome da conta"** visível como rótulo
    ou dica — não só como `placeholder`, que não conta para o UX-DR9
    **And** digitar filtra a lista **pelo nome**, na hora, sem ida à rede
    **And** filtro sem resultado mostra *"Nenhuma conta de portaria com esse nome."* — frase, sem
    ilustração e sem botão grande (UX-DR8)
    **And** quem já está escalado **continua escalado** quando o filtro o esconde: filtrar é ver
    menos, não desmarcar

13. **Given** a lista
    **When** eu marco quem vai trabalhar
    **Then** posso marcar **mais de uma** pessoa
    **And** cada linha tem `<label htmlFor>` associado ao seu controle — UX-DR9, e `placeholder`
    não conta
    **And** a quantidade de escalados aparece em texto (ex.: `2 escalados`), não só pelo estado
    visual das marcações — nenhuma informação só por cor (UX-DR9)
    **And** o alvo de cada linha tem no mínimo 44px de altura

14. **Given** que tento publicar sem escalar ninguém
    **When** eu clico em `Publicar evento`
    **Then** a tela recusa **antes** da ida à rede, com a mesma disciplina de validação local do
    `FormularioCadastro`
    **And** se a recusa vier do servidor mesmo assim, `EVENTO_SEM_PORTARIA` e `PORTARIA_INVALIDA`
    têm texto próprio em `mensagemParaCodigo` — escolhido pelo `codigo`, nunca pela `mensagem`

15. **Given** que a publicação deu certo
    **When** a confirmação aparece
    **Then** ela lista **quem foi escalado**, por nome, junto do inventário de setores que a 2.4 já
    mostra
    **And** continua sem `redirect`: "Meus eventos" é a Story 2.6

16. **Given** que não existe nenhuma conta de portaria no sistema, ou que a lista não pôde ser
    carregada
    **When** eu abro o passo 3
    **Then** vejo uma frase explicando que não há quem escalar e que sem isso o evento não pode ser
    publicado — a tela **não** quebra e o formulário continua de pé
    **And** o `page.tsx` continua sem `error.tsx`: a falha da lista é um estado discriminado, como
    o `buscarNoCatalogo` da 2.2

17. **Given** uma tela abaixo de 900px
    **When** eu uso o passo 3
    **Then** campo de busca e lista ocupam a largura inteira, um por linha
    **And** nada transborda na horizontal

18. **Given** a tela inteira
    **When** eu a inspeciono
    **Then** não há card, sombra nem canto arredondado — UX-DR3
    **And** nenhum dos cinco anti-padrões do UX-DR10 aparece
    **And** nenhum hex novo entra em `*.module.css`: só `var(--token)`

19. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira, e os **164** testes anteriores continuam verdes — inclusive os da
    2.4, que precisam do ajuste descrito na armadilha 1
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos

20. **Given** os três READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta a tabela, a rota nova, os dois códigos de erro novos, a
    ordem das recusas e a quinta conta semeada
    **And** `frontend/README.md` documenta o passo 3, a busca em memória e por que o título dele
    mora na ilha
    **And** `README.md` da raiz ganha as decisões desta story **com a alternativa descartada** de
    cada uma, em primeira pessoa, e a tabela **Contas semeadas** passa a listar cinco
    **And** ⚠️ a linha **"Publicar exige portaria escalada (AD-7) — vale só a partir da Story 2.5"**
    de *O que não está pronto* é **reescrita**: a janela fechou. O que sobra dela é histórico (a
    decisão da 2.4 continua registrada em *Decisões*) e o resíduo real — eventos publicados durante
    a janela ficam sem portaria para sempre, porque não há tela de editar evento

> **De onde vem cada critério.** O `epics.md` traz **cinco** blocos para a Story 2.5: a publicação
> recusada sem portaria; a tabela `evento_portaria` com chave composta; o registro criado ao
> publicar; o `422` para conta sem papel `PORTARIA`; e o texto que explica o que a escala significa.
> Eles viraram os ACs **3, 1, 6, 5 e 11**.
>
> **AC8, AC9 e AC12** são a decisão que o Igor tomou antes de a story ser escrita: a lista vem de uma
> rota própria e a tela tem busca por nome. **AC10** é a segunda conta de portaria, também escolha
> dele. **AC4** existe porque a ordem das recusas decide se dezesseis testes da 2.4 continuam válidos
> ou viram trabalho de reescrita. **AC7** é o que a confirmação da tela precisa para existir.
> **AC20** é a contraparte do AC18 da 2.4 — a dívida foi registrada por escrito, e agora precisa ser
> baixada por escrito.

## Tasks / Subtasks

- [x] **T1. `app/models/evento.py` — a associação** (AC: 1, 2)
  - [x] Acrescentar a `Table` `evento_portaria` no mesmo módulo, **acima** da classe `Evento`
  - [x] Duas colunas, as duas `primary_key=True`: `evento_id` → `ForeignKey("evento.id",
        ondelete="CASCADE")` e `usuario_id` → `ForeignKey("usuario.id")` **sem** `ondelete`
  - [x] Comentário explicando as **duas** decisões: por que é `Table` e não classe, e por que os
        dois `ondelete` são diferentes
  - [x] `Evento.portarias: Mapped[list[Usuario]] = relationship(secondary=evento_portaria)`
  - [x] ⚠️ **Sem `back_populates`** e sem nada em `usuario.py`: o lado inverso é da Story 5.1
  - [x] Atualizar o docstring do módulo — hoje ele diz "Nada na aplicação lê ou escreve nestas
        tabelas ainda", frase que já estava desatualizada desde a 2.4
  - [x] `app/models/__init__.py`: exportar `evento_portaria` no `__all__`, como `Evento` e `Setor`

- [x] **T2. A migração** (AC: 1)
  - [x] `uv run alembic revision --autogenerate -m "cria tabela evento_portaria"`, a partir de
        `backend/`. `down_revision` tem que sair `b91316d771ae`
  - [x] Conferir o arquivo gerado **linha a linha** antes de rodar: o `--autogenerate` erra
        `ondelete` com frequência, e são dois `ondelete` diferentes nesta tabela
  - [x] `upgrade` e `downgrade` conferidos nos dois sentidos
  - [x] Nenhuma coluna `criado_em` aqui: a tabela não tem vida própria

- [x] **T3. `app/schemas/evento.py` — entrada, saída e a lista** (AC: 3, 5, 6, 7, 8)
  - [x] `EventoEntrada` ganha `portaria_ids: list[UUID] = Field(default_factory=list,
        max_length=20)`
  - [x] ⚠️ **`default_factory=list`, nunca `min_length=1`** — pelo mesmo motivo do `setores` da 2.4:
        o AC3 pede o código `EVENTO_SEM_PORTARIA`, e `min_length` produziria `DADOS_INVALIDOS`.
        Ausente e vazio caem na mesma regra do service. Armadilha 2
  - [x] `PortariaSaida` nova: `id`, `nome`, `email`, com `ConfigDict(from_attributes=True)`
  - [x] `EventoSaida` ganha `portarias: list[PortariaSaida]`
  - [x] Estender o docstring do módulo com a quarta recusa que passa a morar aqui — e com o motivo
        de `portaria_ids` **não** ter `min_length`, ao lado do parágrafo que já explica isso para
        `setores`

- [x] **T4. `app/services/evento.py` — a exigência e a lista** (AC: 3, 4, 5, 6, 8)
  - [x] Em `publicar()`, **depois** das duas recusas de setor e **antes** de qualquer `add`:
    - [x] lista vazia → `ErroDeDominio("EVENTO_SEM_PORTARIA", ..., 422)`
    - [x] ⚠️ **A ordem é obrigatória e está no AC4.** Setor primeiro. Inverter quebra os testes de
          recusa da 2.4 sem nenhum ganho
    - [x] deduplicar os ids preservando a ordem (`dict.fromkeys`), sem erro — AC6
    - [x] um `SELECT` só: `Usuario` com `id.in_(ids)` **e** `papel == PORTARIA.value`
    - [x] se o número de encontrados for menor que o de pedidos →
          `ErroDeDominio("PORTARIA_INVALIDA", ..., 422)`. ⚠️ **Uma consulta e uma mensagem para os
          dois casos** (não existe / não é portaria): distinguir seria transformar a rota em oráculo
          de existência de conta
  - [x] Passar `portarias=[...]` ao construir `Evento` — o `relationship` grava as linhas da
        associação na mesma transação, como já faz com os setores
  - [x] `listar_portarias(sessao) -> list[Usuario]`: `select(Usuario).where(papel == PORTARIA)
        .order_by(Usuario.nome)`
  - [x] Docstring de `listar_portarias` dizendo por que ela mora **neste** service e não em
        `autenticacao.py` — ver *Suposições declaradas*
  - [x] **Sem `try/except IntegrityError`**, pelo motivo que o docstring do módulo já registra

- [x] **T5. `app/api/organizador.py` — a rota da lista** (AC: 8, 9)
  - [x] `@router.get("/portarias", response_model=list[PortariaSaida])`
  - [x] `_: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` — aqui o objeto **é**
        descartado, então `_` está certo, ao contrário do `organizador` do `POST /eventos`
  - [x] `sessao: Session = Depends(obter_sessao)`, corpo de uma linha:
        `return servico_de_evento.listar_portarias(sessao)`
  - [x] Docstring curta: por que a lista é do organizador e o que ela revela (nome e e-mail das
        contas de portaria) — a decisão está registrada no README da raiz
  - [x] `app/main.py` **não muda**

- [x] **T6. `backend/seeds/semear.py` — a quinta conta** (AC: 10)
  - [x] Uma `ContaSemeada` a mais, papel `PORTARIA`. Sugestão: `Ana Sampaio ·
        portaria2@rockhub.dev`, mesmo padrão de `cliente2@` — ver *Suposições declaradas*
  - [x] Atualizar o docstring do módulo: hoje ele diz "as quatro contas de avaliação (NFR2): um
        organizador, dois clientes e uma portaria"
  - [x] **Nada mais muda no arquivo** — a idempotência é a mesma, e nenhum `DELETE`/`UPDATE` entra

- [x] **T7. Testes do backend** (AC: 1–10, 19)
  - [x] ⚠️ **`tests/test_organizador_eventos.py` primeiro, antes de escrever caso novo.** Sem o
        `portaria_ids`, **todo** teste que espera `201` passa a receber `422`. Armadilha 1:
    - [x] fixture local `porteiro` devolvendo `fabricar_usuario(PapelUsuario.PORTARIA,
          "porteiro@exemplo.com")`
    - [x] cada teste de caminho feliz passa `_corpo(portaria_ids=[str(porteiro.id)])`
    - [x] os testes de recusa (`403`, `401`, `setores: []`, `origem_externa_id` vazio) **não**
          mudam — e é o AC4 que garante isso
  - [x] Casos novos em `tests/test_organizador_eventos.py`:
    - [x] `portaria_ids` ausente → `422 EVENTO_SEM_PORTARIA`, e zero eventos no banco
    - [x] `portaria_ids: []` → o mesmo
    - [x] sem setor **e** sem portaria → `EVENTO_SEM_SETOR` (AC4)
    - [x] escalar um `CLIENTE` → `422 PORTARIA_INVALIDA`, nada gravado
    - [x] escalar um UUID que não existe → **mesmo** código, e a mesma mensagem
    - [x] escalar dois porteiros → duas linhas em `evento_portaria`, lidas do **banco**
    - [x] o mesmo id duas vezes → `201` e **uma** linha
    - [x] a resposta traz `portarias` com nome e e-mail, e **sem** `senha_hash`
    - [x] extra: id em formato inválido → `DADOS_INVALIDOS`; mais de 20 ids → `DADOS_INVALIDOS`
  - [x] `tests/test_organizador_portarias.py` (arquivo novo):
    - [x] organizador → `200`, só contas `PORTARIA`, ordenadas por nome
    - [x] cliente → `403 SEM_PERMISSAO`; portaria → `403`; sem cookie → `401 NAO_AUTENTICADO`
    - [x] nenhuma chave `senha_hash` no corpo
  - [x] `tests/test_migracoes.py`: `evento_portaria` na lista nominal do teste de ida e volta, mais
        um teste da chave primária composta e dos dois `ondelete`
  - [x] `tests/test_seed.py`: trocar os `4` literais por `len(CONTAS)`, e a contagem de papéis por
        uma derivada de `CONTAS` — AC10. Renomear
        `test_uma_execucao_cria_as_quatro_contas_do_nfr2`

- [x] **T8. `src/lib/portarias.ts` — a busca do lado do servidor** (AC: 8, 16)
  - [x] Arquivo novo, no molde **exato** do `src/lib/catalogo.ts`: tipo `PortariaDisponivel`,
        resultado discriminado (`{ estado: "ok"; itens } | { estado: "indisponivel" }`), `try/catch`
        que **nunca levanta**, `cache: "no-store"`, `cabecalhoDeSessao()` repassado à mão
  - [x] ⚠️ O `fetch` do servidor **não herda o cookie** do pedido — é a armadilha que o
        `servidor.ts` documenta e que já custou uma story

- [x] **T9. `page.tsx` — só o que ela precisa saber** (AC: 11, 16)
  - [x] Buscar as portarias **apenas quando `escolhido` estiver definido**: sem atração escolhida
        não há passo 3, e a chamada seria desperdício a cada busca no catálogo
  - [x] Passar o resultado inteiro (discriminado) como prop para `FormularioPublicacao` — quem
        decide o texto do estado "indisponível" é a ilha, que é quem desenha o passo 3
  - [x] **Nenhum `"use client"` neste arquivo**, e nenhum título de passo 3 aqui — AC11

- [x] **T10. `FormularioPublicacao.tsx` — o passo 3** (AC: 11–17)
  - [x] Prop nova: `portarias: ResultadoDasPortarias`
  - [x] Estado novo: `escalados` (um `Set<string>` de ids, ou lista) e `filtro` (string)
  - [x] O bloco do passo 3 **dentro** do `<form>`, depois da grade de setores: título
        `3 · Escale a portaria` + kicker `Obrigatório` + a frase do AC11
  - [x] Campo de busca com `Campo` (rótulo `Consulte pelo nome da conta`) — rótulo, não
        `placeholder`
  - [x] Filtro em memória: `nome.toLowerCase().includes(filtro.trim().toLowerCase())`.
        ⚠️ Filtrar **não** desmarca ninguém — o `Set` é a fonte da verdade, a lista é só a vista
  - [x] Cada linha: `<input type="checkbox" id=… >` + `<label htmlFor=…>` com nome e e-mail
  - [x] Contagem em texto abaixo da lista (`{n} escalado(s)`), não só a marcação — AC13
  - [x] Validação local antes do `fetch`: `escalados.size === 0` → mensagem e `return`, sem rede
  - [x] `portaria_ids: [...escalados]` no corpo do `POST`
  - [x] `mensagemParaCodigo`: `EVENTO_SEM_PORTARIA` e `PORTARIA_INVALIDA` com texto próprio
  - [x] Confirmação: a lista de escalados, por nome, abaixo do inventário de setores
  - [x] `estado === "indisponivel"` ou lista vazia → a frase do AC16, e nenhuma lista renderizada
  - [x] `page.module.css`: as classes do passo 3. Só `var(--token)`, nenhum hex, alvo de 44px, e a
        media query de 900px
  - [x] extra (não previsto): `preventDefault` no `Enter` do campo de busca — sem ele, Enter no
        filtro envia o `<form>` e publica o evento no meio de uma consulta

- [x] **T11. Verificação** (AC: 17, 18, 19)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final → **187**
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos
  - [x] Rodar `uv run python -m seeds.semear` **duas vezes** e conferir `criada` → `mantida`
  - [x] Conferir na tela, com `next dev` e `uvicorn` no ar: publicar de verdade escalando **duas**
        pessoas, e ler as duas linhas no Postgres (`select * from evento_portaria;`)
  - [~] Tentar publicar sem marcar ninguém: a recusa acontece **sem** ida à rede (Network vazio) —
        **conferido só pela API** (`422 EVENTO_SEM_PORTARIA`); o "sem rede" depende do DevTools e
        ficou para o Igor
  - [~] Abaixo de 900px: um campo por linha, nada rolando na horizontal — CSS escrito e conferido
        no código; a conferência visual é do Igor
  - [~] ⚠️ Conferir que a migração nova, `tests/test_organizador_portarias.py` e
        `src/lib/portarias.ts` **estão rastreados** pelo git antes de dar a story por pronta —
        **não executo git** (regra do projeto). Conferi o `.gitignore`: nenhum padrão alcança os
        três. A conferência é do Igor, no `git status`
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2 continua valendo)
  - [x] ⚠️ **Encerrar os servidores e conferir as portas 3000/8000 pelo PID** ao terminar

- [x] **T12. Os três READMEs** (AC: 20) — obrigatório, regra do projeto
  - [x] `backend/README.md`:
    - [x] Seção **Escalar a portaria** (depois de *Publicar evento*): a tabela, a rota nova, os dois
          códigos, a ordem das quatro recusas e por que a lista não distingue "não existe" de "não é
          portaria"
    - [x] *Dados semeados*: a quinta conta, e o motivo de haver **duas** portarias
    - [x] *Estrutura* e *Testes*: arquivos novos e número novo
    - [x] *Histórico desta camada*: entrada **Story 2.5**
  - [x] `frontend/README.md`:
    - [x] Em *A tela do organizador*: o passo 3, a busca em memória, e por que o título dele mora na
          ilha e não na `page.tsx`
    - [x] *Estrutura*: `src/lib/portarias.ts`
    - [x] *Histórico desta camada*: entrada **Story 2.5**
  - [x] `README.md` da raiz — **a parte que o desafio avalia**:
    - [x] As decisões desta story em *Decisões: por que isso e não aquilo*, **uma seção cada**, no
          formato das anteriores: o que decidi · por quê · o que caiu e por que não
    - [x] ⚠️ **Escreva o motivo que o Igor deu, não um motivo plausível.** A matéria-prima está em
          *Decisões que o Igor tomou*. Se faltar o porquê de alguma, **pergunte a ele**
    - [x] *Contas semeadas*: a tabela passa a ter **cinco** linhas, e o texto explica por que são
          duas portarias — como já explica por que são dois clientes
    - [x] *O que não está pronto*: **reescrever** a linha da janela do AD-7 (AC20). A janela fechou;
          o que sobra é o resíduo — evento publicado durante ela fica sem portaria para sempre
    - [x] *O que não está pronto*: conferir se a linha **"Evento publicado entre os dados semeados"**
          continua correta depois desta story
    - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README da
raiz (T12) — é o "por quê" dele, e é isso que precisa aparecer lá, em primeira pessoa.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| Como o organizador escolhe quem valida | **Rota própria `GET /organizador/portarias`**, e a tela mostra a lista para marcar. É o que o protótipo desenha, e é o único desenho em que o organizador não precisa saber nada de cor: ele reconhece a pessoa pelo nome, marca, e pronto. **Com um campo de busca pelo nome da conta**, e o campo diz isso explicitamente — *"Consulte pelo nome da conta"* — para não sobrar dúvida do que se digita ali | *Digitar o e-mail e o backend resolver* (`portaria_emails: [...]`): nenhuma rota nova e nenhuma lista exposta — caiu porque obriga o organizador a saber o e-mail de cor, e uma letra errada vira `422` sem pista de qual conta existe, exatamente o tipo de erro que ninguém consegue corrigir sozinho. **O custo assumido da escolha:** qualquer organizador enxerga nome e e-mail de todas as contas de portaria do sistema. Numa plataforma com vários organizadores isso viraria escopo por organizador; aqui é um custo consciente, e está registrado |
| Um ou vários escalados | **Vários.** A tabela `evento_portaria` já é N:N por chave composta, o AD-7 fala em "ao menos um", e uma porta de show real tem mais de um operador — escolher um só seria desenhar contra o próprio modelo | *Um `<select>` de escolha única*, como o protótipo desenha: menos tela e menos teste — caiu porque a interface passaria a ser a única coisa impedindo o que o banco permite, e **não há tela de editar evento** para corrigir depois. Um evento com uma pessoa só escalada e ela faltando na noite do show é um evento sem portaria |
| A segunda conta de portaria no seed | **Sim.** Com duas contas, a tela de escalação vira uma escolha de verdade em vez de um item único que não se pode não marcar — e a Epic 5 ganha o cenário que o AD-7 existe para provar: a portaria A não valida o evento da portaria B. O NFR2 pede uma; duas continuam atendendo, com um cenário a mais demonstrável | *Deixar uma só*, exatamente o que o enunciado pede: menos alteração no seed e no README — caiu porque a demonstração mais forte do AD-7 ficaria dependendo de o avaliador criar uma conta na mão, e conta de portaria **não se cria pela interface** (decisão já registrada). Ou seja: sem a segunda conta semeada, o cenário simplesmente não é demonstrável |

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **O filtro por nome acontece em memória, não como `?q=` na rota.** A lista inteira já viaja para a
  tela (são poucas contas), e filtrar no cliente responde a cada tecla sem ida à rede. Um `q` no
  endpoint seria a saída se a lista crescesse — e aí o filtro passaria a ser estado de servidor,
  dentro de uma ilha que já é cliente. Trocar depois é barato; começar assim é o que custa menos hoje
- **`PORTARIA_INVALIDA` é o nome do código.** Cobre os dois casos (id inexistente e conta com outro
  papel) de propósito, pelo motivo do AC5. Se o Igor preferir `USUARIO_NAO_E_PORTARIA`, é uma string
  em três lugares
- **`PortariaSaida` é um schema novo, não o `UsuarioSaida` do `schemas/auth.py`.** A forma é quase a
  mesma hoje (falta o `papel`, que aqui é constante e seria ruído), mas o significado não é: um diz
  "quem está logado", o outro "quem pode ser escalado". Reusar acoplaria o contrato de evento ao de
  autenticação, e o dia em que um dos dois mudar de campo seria o dia de descobrir isso
- **`listar_portarias()` mora em `services/evento.py`.** Ela existe para a publicação — é "quem pode
  ser escalado neste evento" — e não para autenticar ninguém. A alternativa é `services/autenticacao.py`,
  que já é dono das consultas a `Usuario` (`obter_usuario`); caiu porque ali ela ficaria cercada de
  login e cadastro, sem relação com o motivo de existir
- **Ids repetidos são deduplicados em silêncio.** Diferente do `SETOR_DUPLICADO`: dois setores com o
  mesmo nome são duas intenções conflitantes, e a mesma pessoa marcada duas vezes é uma intenção só.
  A tela nem produz esse corpo — a dedução existe para a API, que aceita qualquer cliente
- **A segunda conta semeada é `Ana Sampaio · portaria2@rockhub.dev`.** O e-mail segue o padrão do
  `cliente2@`; o nome é do mesmo registro dos outros quatro (nome de gente, brasileiro, sem repetir
  sobrenome de ninguém — o protótipo sugere "Ana Ribeiro", que colidiria com o Jonas Ribeiro e
  pareceria família). Trocar é uma linha
- **A escala não é reordenável e não tem papel de "principal".** Todo mundo escalado tem exatamente
  a mesma autorização. Hierarquia entre porteiros não está em requisito nenhum
- **Nenhum evento existente ganha portaria retroativamente.** A migração cria a tabela vazia. Os
  eventos publicados na janela da 2.4 continuam sem escala — é o resíduo que o AC20 manda registrar,
  e o único jeito de consertá-los seria a tela de editar evento, que é corte consciente

### O contrato da API, campo a campo

**`POST /organizador/eventos`** — o corpo da 2.4 ganha **um** campo:

```json
{
  "origem_externa_id": "G5vYZ9a1kd",
  "nome": "Baco Exu do Blues — Bluesman Vivo",
  "imagem_url": "https://s1.ticketm.net/dam/a/....jpg",
  "data_hora": "2026-08-15T00:00:00.000Z",
  "local": "Espaço Unimed",
  "cidade": "São Paulo",
  "setores": [{ "nome": "Pista", "capacidade": 800, "preco_centavos": 12000 }],
  "portaria_ids": ["7c2f…", "9a11…"]
}
```

| Campo | Tipo | Regra | Por quê |
|---|---|---|---|
| `portaria_ids` | `list[UUID]` | `max_length=20`, **sem `min_length`** | O AD-7 vira código no service, não no Pydantic. Armadilha 2 |

**A saída ganha `portarias`:**

```json
{
  "id": "3f2a…", "nome": "…", "publicado_em": "2026-08-11T17:22:04Z",
  "setores": [{ "id": "9c1b…", "nome": "Pista", "capacidade": 800, "vendidos": 0,
               "preco_centavos": 12000 }],
  "portarias": [
    { "id": "7c2f…", "nome": "Jonas Ribeiro", "email": "portaria@rockhub.dev" }
  ]
}
```

**`GET /organizador/portarias`** · `200` · `response_model=list[PortariaSaida]`

```json
[
  { "id": "5b0e…", "nome": "Ana Sampaio",   "email": "portaria2@rockhub.dev" },
  { "id": "7c2f…", "nome": "Jonas Ribeiro", "email": "portaria@rockhub.dev" }
]
```

Ordenada por `nome`. Sem paginação e sem `q`: ver *Suposições declaradas*.

**Códigos de erro novos:**

| Código | Status | Quando |
|---|---|---|
| `EVENTO_SEM_PORTARIA` | `422` | `portaria_ids` vazio ou ausente — AD-7 |
| `PORTARIA_INVALIDA` | `422` | Algum id não existe **ou** não tem papel `PORTARIA` |

Os dois são `ErroDeDominio`, e o handler de `app/main.py` já os traduz para o formato único.
**Nenhum handler novo.**

**A ordem das quatro recusas, agora:**

```
1. setores vazio         → EVENTO_SEM_SETOR
2. nome de setor repetido → SETOR_DUPLICADO
3. portaria_ids vazio    → EVENTO_SEM_PORTARIA
4. id que não resolve    → PORTARIA_INVALIDA
   ── só então: monta o Evento e grava ──
```

As quatro acontecem **antes** de qualquer `add`. É isso, e não uma transação esperta, que garante o
"nenhum evento órfão" desde a 2.4.

[Fonte: epics.md#Story 2.5 · ARCHITECTURE-SPINE.md#AD-7, #AD-9 · backend/app/core/erros.py]

### A tela, em texto

Referência: `proto-jornal-noturno.html:594-608`. O protótipo desenha um `<select>` de escolha única;
esta story usa lista de marcação, pela decisão da tabela acima. Grade e espaçamento continuam sendo
o que se ajusta livremente (`DESIGN.md#Como usar este documento`).

```
  3 · Escale a portaria                          OBRIGATÓRIO
  ─────────────────────────────────────────────────────────────────
  CONSULTE PELO NOME DA CONTA
  [ ana                                              ]

  [x] Ana Sampaio      PORTARIA2@ROCKHUB.DEV
  [ ] Jonas Ribeiro    PORTARIA@ROCKHUB.DEV
  ─────────────────────────────────────────────────────────────────
  1 ESCALADO

  Só quem for escalado aqui poderá validar ingressos deste evento.
  ─────────────────────────────────────────────────────────────────
                                              [ PUBLICAR EVENTO ]
```

E na confirmação, abaixo do inventário de setores que a 2.4 já mostra:

```
  PISTA        800 lugares      R$ 120,00
  CAMAROTE      60 lugares      R$ 420,00

  NA PORTA
  Ana Sampaio · Jonas Ribeiro

  Publicar outro →
```

- Nome em **serifada**; e-mail, rótulo e contagem em **mono versalete** — UX-DR2
- Fio embaixo de cada linha. **Sem caixa, sem sombra, sem raio** — UX-DR3
- Linha inteira clicável, com no mínimo 44px de altura
- A frase explicativa é o texto do protótipo, e é requisito de AC do `epics.md` — não a reescreva
  "para ficar melhor"
- Nada gira e nada pulsa enquanto envia (`EXPERIENCE.md#Carregando`)

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `publicar()` | `app/services/evento.py:39` | **Estenda**. Duas recusas novas entram na sequência que já está lá |
| `EventoEntrada` / `EventoSaida` | `app/schemas/evento.py` | **Estenda**. Um campo em cada |
| `Evento`, `Setor` | `app/models/evento.py` | A `Table` nova mora neste arquivo. Nenhuma coluna nova nas duas classes |
| `Usuario`, `PapelUsuario` | `app/models/usuario.py` | **Não mexa.** O lado inverso do relacionamento é da 5.1 |
| `exigir_papel` | `app/core/dependencias.py:81` | As duas rotas. Já garante `401` antes de `403` |
| `ErroDeDominio` | `app/core/erros.py:88` | Os dois códigos novos |
| Router do organizador | `app/api/organizador.py` | **Estenda**. Não crie `app/api/portarias.py` |
| Convenção de nomes de constraint | `app/models/base.py` | A migração sai com os nomes certos por causa dela |
| Migração da 2.3 | `migrations/versions/20260811_b91316d771ae_*.py` | O modelo do que uma migração revisada à mão parece neste projeto |
| `_entrar`, `_corpo`, `_instalar_transporte` | `tests/test_organizador_eventos.py:28-67` | O arquivo a estender. `_corpo` ganha `portaria_ids` por parâmetro |
| `fabricar_usuario` | `tests/conftest.py:139` | Os três papéis, com e-mail por parâmetro |
| `CONTAS`, `semear` | `seeds/semear.py:54` | Uma tupla a mais. Nada mais muda |
| `buscarNoCatalogo` | `frontend/src/lib/catalogo.ts` | O **molde exato** de `portarias.ts`: resultado discriminado, nunca levanta |
| `cabecalhoDeSessao` | `frontend/src/lib/servidor.ts:51` | O cookie repassado à mão no `fetch` de servidor |
| `FormularioPublicacao` | `frontend/src/components/FormularioPublicacao.tsx` | **Estenda**. O passo 3 é um bloco a mais no mesmo `<form>` |
| `Campo`, `Botao`, `AvisoDeErro` | `frontend/src/components/` | Os três. Não recrie nenhum |
| `.oculto`, `.linhaSetor` | `frontend/src/app/(site)/organizador/publicar/page.module.css` | O padrão de "visually hidden" e o de linha com grade já estão escritos |
| Tokens | `frontend/src/app/globals.css` | `var(--fio)`, `var(--breu2)`, `var(--ambar)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)` |

**Não devem ser tocados, e não devem quebrar:** `app/models/usuario.py`, `app/integrations/`,
`app/core/`, `app/main.py`, `app/schemas/auth.py`, `app/services/autenticacao.py`,
`tests/conftest.py`, `docker-compose.yml`, `pyproject.toml`, `package.json`,
`frontend/src/lib/servidor.ts`, `sessao.ts`, `api.ts`, `caminho.ts`, `components/Masthead.tsx`, e as
telas de `(entrada)/`.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. Oito testes da 2.4 quebram no primeiro `pytest`, e isso é esperado.** Todo teste de
`test_organizador_eventos.py` que espera `201` manda um corpo **sem** `portaria_ids`, porque o campo
não existia. Com o AC3 valendo, eles passam a receber `422 EVENTO_SEM_PORTARIA`. A correção é a
fixture `porteiro` e o `portaria_ids` no `_corpo` — **não** é afrouxar a regra, e **não** é dar
`default` de portaria no schema. Os testes de recusa (`403`, `401`, `setores: []`) continuam
intactos por causa da ordem do AC4.

**2. `min_length=1` no `portaria_ids` produz o código errado.** É a mesma armadilha que a 2.4
documentou para `setores`, e ela volta idêntica: `min_length` responde `DADOS_INVALIDOS`, o AC3 pede
`EVENTO_SEM_PORTARIA`. A validação de estrutura é do Pydantic; **"publicar exige portaria escalada"
é o AD-7**, e invariante de arquitetura mora no service. O teste que pega isso afirma o `codigo`.

**3. `--autogenerate` erra o `ondelete`.** São dois diferentes na mesma tabela — `CASCADE` no evento,
nada no usuário — e o Alembic tem histórico de emitir a chave estrangeira sem a opção. Leia a
migração gerada antes de rodar, como a 2.3 fez.

**4. Filtrar a lista não pode desmarcar ninguém.** Se a marcação for derivada da lista filtrada (por
índice, por exemplo), digitar no campo de busca apaga a escala. A fonte da verdade é o conjunto de
ids; a lista filtrada é só o que se vê. Marcar "Ana", digitar "jonas", marcar "Jonas" e publicar tem
que gravar **os dois**.

**5. `relationship(secondary=...)` sem `Usuario` importado no lugar certo.** `evento.py` já importa
de `usuario.py`, então o sentido está livre. O que **não** pode acontecer é `usuario.py` passar a
importar `evento.py` para declarar o lado inverso — vira ciclo de import, e o lado inverso é da 5.1
de qualquer jeito.

**6. Cinco contas semeadas quebram seis testes que contam `4` na mão.** `test_seed.py` tem `== 4`,
`[CRIADA] * 4` e `papeis.count(...) == 1` espalhados. Derivar de `CONTAS` conserta os seis de uma vez
e faz a próxima conta não custar nada. É AC10, não faxina opcional.

**7. `senha_hash` vaza se alguém devolver o `Usuario` cru.** O `response_model` do FastAPI filtra —
mas só se ele estiver declarado. Sem `response_model=list[PortariaSaida]` na rota, o SQLAlchemy
serializa o que der. O teste que afirma a ausência da chave existe por isso.

**8. Rodar só o arquivo novo não é verificação.** Esta story mexe em três arquivos de teste que já
existiam. O AC19 pede a suíte inteira, e é ela que revela a armadilha 1.

**9. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest` falhar
com `os error 4551`, chame pelo módulo: `uv run python -m pytest`. Documentado desde a Story 1.1.

**10. As contas semeadas podem não existir no banco de desenvolvimento.** Aconteceu na 2.4. Rode
`uv run python -m seeds.semear` a partir de `backend/`, **com o `-m`**, antes da conferência manual.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      organizador.py             # +GET /organizador/portarias
    models/
      evento.py                  # +Table evento_portaria, +Evento.portarias
      __init__.py                # +evento_portaria no __all__
    schemas/
      evento.py                  # +portaria_ids, +PortariaSaida, +EventoSaida.portarias
    services/
      evento.py                  # +duas recusas em publicar(), +listar_portarias()
  migrations/versions/
    <nova>_cria_tabela_evento_portaria.py   # NOVO
  seeds/
    semear.py                    # +a quinta conta
  tests/
    test_organizador_eventos.py  # +fixture porteiro, +8 casos
    test_organizador_portarias.py  # NOVO
    test_migracoes.py            # +evento_portaria
    test_seed.py                 # contagens derivadas de CONTAS
  README.md
frontend/
  src/
    lib/
      portarias.ts               # NOVO — no molde do catalogo.ts
    app/(site)/organizador/publicar/
      page.tsx                   # +busca das portarias, +prop
      page.module.css            # +classes do passo 3
    components/
      FormularioPublicacao.tsx   # +passo 3, +estado de escala, +confirmação
  README.md
README.md                        # decisões + contas semeadas + a janela do AD-7 fechada
```

Não existe, e não deve passar a existir nesta story: `app/api/portarias.py`, `services/usuario.py`,
lado inverso em `Usuario`, tela de editar evento, `/organizador/meus-eventos` (2.6), qualquer rota de
portaria (Epic 5), qualquer dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend** — precisa do Compose no ar (login de verdade) e **zero rede**.

| O que o teste prova | Arquivo | AC |
|---|---|---|
| `evento_portaria` existe, com PK composta das duas colunas | `test_migracoes.py` | 1 |
| FK de evento tem `CASCADE`; a de usuário, não | `test_migracoes.py` | 1 |
| `downgrade base` derruba as quatro tabelas e `upgrade head` as refaz | `test_migracoes.py` | 1 |
| `portaria_ids` ausente → `422 EVENTO_SEM_PORTARIA`, zero eventos no banco | `test_organizador_eventos.py` | 3 |
| `portaria_ids: []` → o mesmo | `test_organizador_eventos.py` | 3 |
| Sem setor **e** sem portaria → `EVENTO_SEM_SETOR` | `test_organizador_eventos.py` | 4 |
| Escalar um `CLIENTE` → `422 PORTARIA_INVALIDA`, nada gravado | `test_organizador_eventos.py` | 5 |
| Escalar um UUID inexistente → **mesmo** código | `test_organizador_eventos.py` | 5 |
| Escalar dois → duas linhas em `evento_portaria`, lidas do banco | `test_organizador_eventos.py` | 6 |
| O mesmo id duas vezes → `201` e **uma** linha | `test_organizador_eventos.py` | 6 |
| A resposta traz `portarias` com nome e e-mail | `test_organizador_eventos.py` | 7 |
| Nenhuma chave `senha_hash` na resposta da publicação | `test_organizador_eventos.py` | 7 |
| Organizador lista as portarias, ordenadas por nome | `test_organizador_portarias.py` | 8 |
| A lista não traz organizador nem cliente | `test_organizador_portarias.py` | 8 |
| Nenhuma chave `senha_hash` na lista | `test_organizador_portarias.py` | 7, 8 |
| Cliente → `403`; portaria → `403`; sem cookie → `401` | `test_organizador_portarias.py` | 9 |
| O seed cria `len(CONTAS)` contas, com **duas** de papel `PORTARIA` | `test_seed.py` | 10 |
| Segunda execução devolve `mantida` para todas, sem duplicar | `test_seed.py` | 10 |
| A senha semeada autentica nas cinco | `test_seed.py` | 10 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são sete caminhos:

1. Entrar como `organizador@rockhub.dev`, escolher uma atração → o passo 3 aparece com as **duas**
   contas semeadas
2. Digitar `ana` no campo de busca → só uma linha; apagar → as duas voltam
3. Marcar Ana, filtrar por `jonas`, marcar Jonas, limpar o filtro → **as duas** continuam marcadas
4. Publicar sem marcar ninguém → recusa **sem** ida à rede (Network vazio)
5. Publicar com duas → confirmação lista os dois nomes, e o Postgres tem duas linhas em
   `evento_portaria`
6. Abaixo de 900px: um campo por linha, nada rolando na horizontal
7. Navegar com Tab: cada marcação recebe foco visível em âmbar, e o rótulo é lido junto

**Baseline: 164 testes passando** (`backend/README.md#Testes`, conferido em 2026-08-11, ao fim da
Story 2.4). Registre o número final no `backend/README.md` e nas notas de conclusão.

### Inteligência das stories anteriores

**Da 2.4 — a story que esta completa:**

- **A dívida do AD-7 é desta story.** O AC18 da 2.4 mandou registrar a janela por escrito; o AC20
  daqui manda baixá-la por escrito. Documentação de dívida que ninguém apaga vira documentação
  errada
- **A ordem das recusas é contrato, não detalhe.** As duas que existem acontecem antes de qualquer
  `add`, e é isso que garante "nenhum evento órfão". As duas novas entram no fim dessa sequência
- **O `_corpo(**ajustes)` do teste foi escrito para mudar assim** — um helper e quinze testes que
  mostram só o que mudam. Aproveite-o em vez de reescrever dicionários
- **`vendidos` não é passado ao construir `Setor`.** Mesma disciplina vale aqui: nada de `INSERT`
  manual na tabela de associação — quem grava é o `relationship`
- **A tela ganhou `#passo-2` depois que o Igor a usou**, porque o passo nascia abaixo da dobra. O
  passo 3 nasce ainda mais abaixo: **confira isso no navegador**, não só no código
- **Sobrou um evento de teste no banco de desenvolvimento** (`Sticky Fingers - Rio de Janeiro`),
  criado na janela do AD-7 e portanto sem portaria. Ele não é validável na Epic 5. Apagar é
  `docker compose exec db psql -U rockhub -d rockhub -c "delete from evento;"`

**Da 2.3 — a story que criou o schema:**

- **`ON DELETE CASCADE` no banco exige `passive_deletes=True` no ORM.** Vale reler antes de escrever
  a `Table` nova: sem isso o ORM emite `UPDATE ... SET evento_id = NULL` antes do `DELETE`
- **As constraints são rede de segurança, não a regra.** A chave composta impede linha duplicada; a
  dedução do AC6 é o que a impede de virar `500`

**Da 2.2 — o padrão de busca no servidor:** `buscarNoCatalogo` **nunca levanta**, porque não existe
`error.tsx` e uma exceção num Server Component derruba a tela inteira. `portarias.ts` nasce com a
mesma disciplina — é o AC16.

**Da 1.7 — o seed:** rodar de novo é seguro, e a idempotência é uma consulta, não uma limpeza.
Acrescentar conta não pode introduzir `DELETE`, `UPDATE` nem `TRUNCATE` no arquivo.

**Da 1.6 — autorização:** papel se declara na assinatura. `401` antes de `403` é garantido pelo
`Depends` encadeado, não por ordem de `if`.

[Fonte: _bmad-output/implementation-artifacts/2-4-*.md · 2-3-*.md · 2-2-*.md · 1-7-*.md ·
sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `@router.get` com `response_model=list[...]` |
| Pydantic | 2.13.4 | `list[UUID]`, `Field(max_length)`, `ConfigDict(from_attributes=True)` |
| SQLAlchemy | 2.0.51 | `Table` do Core, `relationship(secondary=...)`, `in_()` |
| Alembic | 1.19.1 | `--autogenerate` da tabela de associação |
| Next.js | **16.3.0** | `searchParams` é **Promise**; `PageProps<"/rota">` é global e gerado |
| React | 19 | `useState` na ilha; Server Component em todo o resto |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** Esta versão do Next tem quebras em relação ao
que um modelo tem memorizado; a documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

[Fonte: ARCHITECTURE-SPINE.md#Stack · backend/pyproject.toml · frontend/package.json]

### Escopo — o que NÃO fazer aqui

Tela de turnos da portaria e validação de ingresso (Epic 5) · "Meus eventos" (2.6) · tela de editar
evento ou de trocar a escala depois da publicação (corte consciente) · listagem pública (3.1) ·
lado inverso `Usuario.eventos_escalados` (5.1) · seed com evento publicado · paginação ou `?q=` na
rota de portarias · convite ou cadastro de conta de portaria.

Cinco tentações concretas:

- **"Já crio `Usuario.eventos_escalados`, é uma linha."** É, e é uma linha sem consumidor até a 5.1,
  com risco de ciclo de import. A 5.1 sabe o que precisa
- **"Faço uma tela de editar a escala, senão o organizador não tem como corrigir."** Ele não tem
  mesmo, e isso é corte consciente já registrado em *O que não está pronto*. Story nova é decisão do
  Igor
- **"Aproveito e semeio um evento, agora que ele nasceria com portaria."** Nasceria — e continua
  sendo decisão de produto do Igor: qual show, qual data, quais setores, quais preços. A dívida está
  registrada no README de propósito
- **"Deixo `portaria_ids` opcional para não quebrar os testes da 2.4."** Isso é não fazer a story. Os
  testes é que se ajustam, e a armadilha 1 explica como
- **"Distingo 'conta não existe' de 'conta não é portaria' — ajuda a depurar."** Ajuda, e transforma
  a rota num oráculo de existência de conta. É o AC5, e é a mesma disciplina do login da 1.4

### Project Structure Notes

Esta é a **primeira tabela de associação** do projeto, e a primeira vez que uma invariante da
arquitetura é cumprida em duas etapas de propósito. A 2.4 escreveu a dívida; esta a paga. O par
inteiro — decisão, custo, prazo e baixa — está registrado nos ACs das duas stories e no README da
raiz, e é exatamente o tipo de rastro que o desafio avalia: não "não houve dívida", mas "houve, foi
escolhida, e fechou onde eu disse que fecharia".

É também a primeira vez que uma rota de leitura do organizador **passa por service**. A do catálogo
não passa, e o docstring de `app/api/organizador.py` explica por quê (não sobra regra de negócio
para lugar nenhum). A de portarias passa, não por invariante, mas porque toca o banco — e router que
toca `Session` é o que o paradigma da espinha proíbe sem exceção. O arquivo passa a ter os **três**
casos lado a lado: leitura sem service (integração externa), leitura com service (banco), escrita com
service (transação e invariantes).

No frontend, o passo 3 é o primeiro bloco em que a ilha `"use client"` recebe **dado de servidor por
prop** e o usa como fonte de uma interação. A prop `item` da 2.4 era só exibição; `portarias` é uma
lista que se filtra, se marca e vira corpo de requisição. A fronteira continua a mesma — o servidor
busca, o cliente interage — e é o desenho que as Epics 3 e 5 vão repetir.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5] — os cinco blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR2, FR16 e o objetivo da epic
- [Source: _bmad-output/planning-artifacts/epics.md#Requirements Inventory] — FR16, o requisito que
  o Igor acrescentou e que esta story fecha
- [Source: ARCHITECTURE-SPINE.md#AD-7] — o vínculo `evento_portaria` e a exigência na publicação
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel declarado na assinatura, nunca `if` no corpo
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`; router não toca a
  `Session`
- [Source: ARCHITECTURE-SPINE.md#Convenções] — erro sempre `{"erro": {...}}`; Server Component por
  padrão
- [Source: ARCHITECTURE-SPINE.md#Adiado] — tela de editar evento e teste de frontend, os dois cortes
  que esta story não reabre
- [Source: docs/decisoes-tecnicas.md#Portaria é escala de trabalho, não nível de permissão] — o
  raciocínio do AD-7 em linguagem de gente, pronto para o README
- [Source: EXPERIENCE.md#Information Architecture] — `Publicar evento → 1 catálogo · 2 data, local e
  setores · 3 escalar portaria`
- [Source: EXPERIENCE.md#Key Flows] — o fluxo 3, passo 5: "sem ao menos um usuário de portaria, o
  botão de publicar não libera"
- [Source: EXPERIENCE.md#Vazio] — kicker, frase, fim; sem ilustração e sem botão grande
- [Source: DESIGN.md#Como usar este documento] — grade e espaçamento são provisórios; a ausência de
  card, sombra e raio é duradoura
- [Source: mockups/proto-jornal-noturno.html:594-608] — o passo 3 e a frase que o explica
- [Source: backend/app/models/evento.py] — onde a `Table` nova entra, e os dois `ondelete` de
  referência
- [Source: backend/app/models/base.py] — a convenção de nomes que a migração herda
- [Source: backend/app/services/evento.py:39] — `publicar()`, a função a estender
- [Source: backend/app/schemas/evento.py] — o docstring que explica por que `setores` não tem
  `min_length`; o de `portaria_ids` fica ao lado
- [Source: backend/app/api/organizador.py] — o router a estender e o critério "existe transação ou
  invariante?"
- [Source: backend/app/core/dependencias.py:81] — `exigir_papel`
- [Source: backend/seeds/semear.py:54] — `CONTAS`, e a idempotência que não pode mudar
- [Source: backend/tests/test_organizador_eventos.py:48] — `_corpo`, o helper que a armadilha 1 ajusta
- [Source: backend/tests/test_migracoes.py:104] — a lista nominal de tabelas
- [Source: frontend/src/lib/catalogo.ts] — o molde de `portarias.ts`
- [Source: frontend/src/lib/servidor.ts:51] — o cookie repassado à mão no `fetch` de servidor
- [Source: frontend/src/components/FormularioPublicacao.tsx] — a ilha a estender
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: README.md#o-que-não-está-pronto] — a linha da janela do AD-7, que esta story reescreve
- [Source: README.md#contas-semeadas] — a tabela que passa a ter cinco linhas
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do
  Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os três READMEs antes de dar a story por concluída.** As decisões da T12 são a parte
   que o desafio avalia — e **o "por quê" precisa ser o do Igor**, em primeira pessoa. Se faltar o
   motivo de alguma, pergunte a ele em vez de escrever um plausível
3. **Decisão de produto ou de modelagem é do Igor.** As três desta story estão respondidas e as sete
   suposições estão declaradas. Se aparecer uma quarta — campo a mais, regra a mais, tela a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente — vale para o `npm run dev` desta story
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os arquivos novos foram rastreados (T11)
8. **O code review é ao fim da epic**, não a cada story. Depois da 2.5 vem a 2.6, e só quando o Igor
   mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **A escala deve poder mudar depois da publicação?** Hoje não — não há tela de editar evento, e é
   corte consciente registrado. Com a Story 2.6 ("Meus eventos") chegando, o lugar natural para isso
   existiria. Vale decidir antes da 2.6 se ela ganha essa capacidade ou se o corte continua.
2. **O nome e o e-mail da segunda conta semeada.** Sugeri `Ana Sampaio · portaria2@rockhub.dev`
   seguindo o padrão do `cliente2@`. É uma linha em `seeds/semear.py` e uma no README.
3. **A lista de portarias deveria ser escopo por organizador?** Hoje todo organizador enxerga todas
   as contas de portaria do sistema — custo assumido da decisão desta story. Numa plataforma com
   vários organizadores isso viraria "só quem eu convidei", que exige convite, que é outra epic.
4. **Evento com data no passado continua aceito** (pergunta herdada da 2.4). Vale decidir antes da
   2.6, que vai listar "o que está em cartaz".

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context) — implementação via `bmad-dev-story`.

### Debug Log References

- `uv run alembic revision --autogenerate -m "cria tabela evento_portaria"` → revisão
  `c7cb4a29b7f3`, `down_revision = b91316d771ae`. **O `--autogenerate` acertou desta vez**, ao
  contrário do que a armadilha 3 previa: emitiu `ondelete='CASCADE'` na FK de evento, nenhum
  `ondelete` na de usuário, `PrimaryKeyConstraint('evento_id', 'usuario_id')` e nenhuma coluna
  extra. Conferido linha a linha antes de aplicar, e depois `upgrade head` → `downgrade -1` →
  `upgrade head` nos dois sentidos.
- `uv run python -m pytest` → **187 passed** (baseline 164). Uma única falha no caminho, e foi
  teste meu, não código: `test_organizador_recebe_as_contas_de_portaria_ordenadas_por_nome` usava a
  `fabricar_usuario` do `conftest.py`, que grava **todo mundo com o nome "Alguém"** e parametriza só
  o e-mail. Com nomes iguais, "ordenado por nome" não decide nada e a ordem observada era a de
  inserção. Corrigido com um helper local `_portaria_chamada(sessao, nome, email)` — sem tocar no
  `conftest.py`, que a story marca como intocável.
- `uv run python -m seeds.semear` duas vezes contra o banco de desenvolvimento: na primeira,
  `portaria2@rockhub.dev` sai `criada` e as outras quatro `mantida`; na segunda, as cinco `mantida`.
- Conferência de ponta a ponta com `uvicorn` e `next dev` no ar: `GET /organizador/portarias`
  devolveu Ana antes de Jonas (ordenação real, com os nomes do seed); a `page.tsx` renderizou o
  passo 3 com as duas contas, o rótulo *"Consulte pelo nome da conta"*, a contagem `0 escalados` e a
  frase do AC11; uma publicação real com dois escalados gravou **duas** linhas em `evento_portaria`
  (lidas por `psql`); corpo sem `portaria_ids` → `422 EVENTO_SEM_PORTARIA`; UUID que não resolve →
  `422 PORTARIA_INVALIDA`.
- ⚠️ **Ficou um evento de conferência no banco de desenvolvimento**, `Rock in Rio 2026 (conferencia
  2.5)`, com duas linhas de escala. Não apaguei nada: o banco é do Igor. Para limpar:
  `docker compose exec db psql -U rockhub -d rockhub -c "delete from evento;"` — o mesmo comando
  serve para o `Sticky Fingers - Rio de Janeiro` da 2.4, que continua sem portaria.
- Servidores encerrados por PID ao fim; portas 3000 e 8000 conferidas livres.

### Completion Notes List

**O que foi implementado.** A escala da portaria, de ponta a ponta: a tabela `evento_portaria`
(migração `c7cb4a29b7f3`, chave primária composta, `CASCADE` no evento e nada no usuário), a
`Table` do Core com `Evento.portarias` e **sem** lado inverso, as duas recusas novas no `publicar()`
(`EVENTO_SEM_PORTARIA` e `PORTARIA_INVALIDA`, nessa ordem, depois das duas de setor), a rota
`GET /organizador/portarias` com `PortariaSaida`, a quinta conta semeada (`Ana Sampaio ·
portaria2@rockhub.dev`), `src/lib/portarias.ts` no molde do `catalogo.ts`, e o passo 3 da tela
dentro do mesmo `<form>` do passo 2.

**A janela do AD-7 fechou.** É a contraparte do AC18 da 2.4: a linha de *O que não está pronto* no
README da raiz foi reescrita — deixou de descrever uma dívida em aberto e passa a descrever o
resíduo real (evento publicado durante a janela fica sem portaria para sempre, porque não há tela de
editar evento).

**A armadilha 1 se comportou exatamente como a story previu.** Oito testes de caminho feliz da 2.4
passaram a receber `422`; a correção foi a fixture `porteiro` mais `_corpo(portaria_ids=[...])` em
cada um. Os testes de recusa não foram tocados — é o AC4 valendo na prática, e é a prova de que a
ordem das recusas era decisão de contrato e não de estilo.

**Uma decisão pequena que não estava na story, e que eu tomei sozinho:** o campo de busca do passo 3
vive dentro do `<form>` do passo 2 (é um `POST` só), e Enter num campo de texto envia formulário — o
que publicaria o evento no meio de uma consulta. Pus `preventDefault` no `Enter` desse campo. Não é
decisão de produto: o campo filtra a cada tecla e não tem nada a confirmar. Está documentado no
`frontend/README.md` e no comentário do código.

**Também não previsto:** três testes a mais do que a story pediu — id em formato inválido virando
`DADOS_INVALIDOS`, mais de vinte ids batendo no `max_length`, e a comparação byte a byte dos dois
corpos de erro de `PORTARIA_INVALIDA` (não existe × não é portaria), que é o que impede a rota de
virar oráculo de existência de conta.

**Suíte: 164 → 187.** Nenhuma dependência nova em `pyproject.toml`, `uv.lock` ou `package.json`.
`npm run build`, `npx tsc --noEmit` e `npm run lint` limpos.

**O que ficou para o Igor**, e está marcado com `[~]` na T11: as três conferências que exigem
navegador ou git — o "Network vazio" na recusa local, o comportamento abaixo de 900px, e confirmar
no `git status` que os três arquivos novos entraram no índice (conferi o `.gitignore`: nenhum padrão
os alcança).

### File List

**Backend — novos**

- `backend/migrations/versions/20260811_c7cb4a29b7f3_cria_tabela_evento_portaria.py`
- `backend/tests/test_organizador_portarias.py`

**Backend — modificados**

- `backend/app/models/evento.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/evento.py`
- `backend/app/services/evento.py`
- `backend/app/api/organizador.py`
- `backend/seeds/semear.py`
- `backend/tests/test_organizador_eventos.py`
- `backend/tests/test_migracoes.py`
- `backend/tests/test_seed.py`
- `backend/README.md`

**Frontend — novos**

- `frontend/src/lib/portarias.ts`

**Frontend — modificados**

- `frontend/src/app/(site)/organizador/publicar/page.tsx`
- `frontend/src/app/(site)/organizador/publicar/page.module.css`
- `frontend/src/components/FormularioPublicacao.tsx`
- `frontend/README.md`

**Raiz**

- `README.md`
- `_bmad-output/implementation-artifacts/2-5-escalar-quem-valida-na-porta.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Story 2.5 implementada. Migração `c7cb4a29b7f3` cria `evento_portaria` com chave primária composta, `ON DELETE CASCADE` na FK de evento e nenhum `ondelete` na de usuário; a associação é `Table` do Core e `Evento.portarias` nasce sem lado inverso (Story 5.1). `publicar()` ganhou as duas recusas novas **depois** das de setor — `EVENTO_SEM_PORTARIA` e `PORTARIA_INVALIDA`, esta última com uma consulta e uma mensagem só para "não existe" e "não é portaria" —, e os ids repetidos são deduplicados em silêncio por `dict.fromkeys`. Nasceram `GET /organizador/portarias` (leitura com service, o terceiro caso do critério do router), o schema `PortariaSaida`, a quinta conta semeada (`Ana Sampaio · portaria2@rockhub.dev`), `src/lib/portarias.ts` no molde do `catalogo.ts`, e o passo 3 da tela dentro do mesmo `<form>` do passo 2, com busca em memória, marcação múltipla e contagem em texto. A armadilha 1 se confirmou: os oito testes de caminho feliz da 2.4 quebraram e foram ajustados com a fixture `porteiro`; os de recusa não foram tocados, que era o ponto do AC4. Um teste meu falhou por motivo próprio — a `fabricar_usuario` grava todo mundo como "Alguém", e ordenar por nome não decidia nada; resolvido com um helper local, sem tocar no `conftest.py`. Decisão pequena não prevista pela story: `preventDefault` no Enter do campo de busca, porque Enter num campo de texto dentro do `<form>` publicaria o evento no meio de uma consulta. A janela do AD-7 aberta na 2.4 foi baixada por escrito no README da raiz (AC20). Suíte de 164 para **187**; `npm run build`, `tsc --noEmit` e `lint` limpos; nenhuma dependência nova |
| 2026-08-11 | Story 2.5 criada e contextualizada. Três decisões do Igor incorporadas: a lista de quem pode ser escalado vem de uma **rota própria** (`GET /organizador/portarias`) com **campo de busca pelo nome da conta**, rotulado explicitamente *"Consulte pelo nome da conta"* — em vez de digitar o e-mail e o backend resolver, que obrigaria o organizador a saber o endereço de cor e transformaria uma letra errada num `422` sem pista, ao custo assumido de qualquer organizador enxergar nome e e-mail de todas as contas de portaria; a escala aceita **vários** usuários por evento — em vez do `<select>` de escolha única que o protótipo desenha, que faria a interface ser a única coisa impedindo o que o banco permite, sem tela de editar evento para corrigir; e o seed ganha uma **segunda conta de portaria** — em vez de manter a única que o NFR2 pede, porque sem ela o cenário que o AD-7 existe para provar (a portaria A não valida o evento da portaria B) dependeria de o avaliador criar uma conta na mão, e conta de portaria não se cria pela interface. Vinte ACs escritos sobre os cinco blocos do `epics.md`, entre eles o AC4 — a ordem das recusas mantém `EVENTO_SEM_SETOR` na frente de `EVENTO_SEM_PORTARIA`, que é o que deixa os testes de recusa da 2.4 intactos, sobrando só os oito de caminho feliz para ajustar — e o AC20, que manda **reescrever** a linha da janela do AD-7 em *O que não está pronto*: o AC18 da story anterior registrou a dívida, e esta é a que a baixa. Sete suposições declaradas (filtro em memória e não `?q=` na rota, `PORTARIA_INVALIDA` como código único para "não existe" e "não é portaria", `PortariaSaida` novo em vez de reusar `UsuarioSaida`, `listar_portarias()` em `services/evento.py`, ids repetidos deduplicados em silêncio, `Ana Sampaio · portaria2@rockhub.dev` como quinta conta, nenhuma escala retroativa para os eventos da janela) e quatro perguntas registradas para as stories seguintes |
