---
baseline_commit: "7120ad0 — feat: techspec - filtro de classificacao no catalogo da Ticketmaster (branch Epic-2---Publicação-de-eventos-pelo-organizador). ⚠️ A Story 2.3 está implementada e **ainda não commitada** no momento em que esta story foi escrita: `app/models/evento.py`, a migração `b91316d771ae` e `tests/test_evento.py` existem no disco. Esta story depende dos três."
---

# Story 2.4: Publicar um evento com seus setores

Status: review

Epic 2 — Publicação de eventos pelo organizador · **A story em que a epic entrega o que promete.**
Hoje o organizador busca no catálogo, enxerga o resultado e não pode fazer nada com ele; as tabelas
`evento` e `setor` existem desde a 2.3 e nenhuma linha de aplicação as toca. Esta story fecha os
dois buracos de uma vez: a fila do catálogo vira clicável, o passo 2 aparece, o formulário grava, e
**o primeiro evento real do sistema passa a existir** — criado pela interface, não por seed.

Como organizador,
quero publicar o evento com data, local e setores,
para colocá-lo à venda.

Três peças: `POST /organizador/eventos` protegida por papel, o service que grava evento e setores na
mesma transação, e o passo 2 da tela `/organizador/publicar`. **Escalar a portaria é a Story 2.5** —
e a consequência disso está declarada abaixo, em letra grande, porque ela contraria temporariamente
o AD-7. "Meus eventos" é a 2.6.

## Acceptance Criteria

1. **Given** que estou autenticado como organizador e escolhi uma atração
   **When** eu chamo `POST /organizador/eventos` com data, local e uma lista de setores
   **Then** recebo `201` com o evento gravado e seus setores
   **And** os campos do catálogo (`nome`, `imagem_url`, `origem_externa_id`) foram **copiados** para
   as colunas do evento — AD-1
   **And** cada setor nasce com `vendidos = 0`
   **And** `publicado_em` vem preenchido: publicar é o ato desta rota, não um passo posterior

2. **Given** a mesma chamada
   **When** o evento é gravado
   **Then** `organizador_id` é o do usuário **da sessão**, nunca um id vindo do corpo
   **And** o schema de entrada não tem campo `organizador_id` — o corpo não tem como influenciá-lo
   **And** existe um teste com **dois** organizadores provando que o dono é quem publicou

3. **Given** a publicação
   **When** ela acontece
   **Then** **nenhuma** chamada à Ticketmaster é feita — AD-1: na publicação o catálogo já foi
   copiado, e da 2.4 em diante o dado vive no banco
   **And** o teste prova isso instalando um transporte que **falha** se alguém o chamar

4. **Given** um corpo com a lista de setores vazia (ou ausente)
   **When** eu publico
   **Then** recebo `422` com código `EVENTO_SEM_SETOR` — e **não** `DADOS_INVALIDOS`
   **And** nenhum evento órfão fica no banco: a recusa acontece antes de qualquer `INSERT`
   **And** a regra mora no **service**, não em `min_length=1` do Pydantic — ver *Armadilhas*,
   armadilha 1

5. **Given** dois setores com o mesmo nome no mesmo corpo
   **When** eu publico
   **Then** recebo `422` com código `SETOR_DUPLICADO`, e **nunca** um `500` vindo do
   `uq_setor_evento_id_nome` da Story 2.3
   **And** a comparação ignora caixa e espaços em volta: `Pista` e ` pista ` são o mesmo setor
   **And** nada é gravado — nem o evento

6. **Given** um corpo sem `origem_externa_id` (ausente, vazio ou só espaços)
   **When** eu publico
   **Then** recebo `422`
   **And** é aqui que a regra *"publicação exige atração do catálogo"* passa a ser **aplicada** — a
   coluna continua anulável no banco, como a Story 2.3 decidiu, e a tensão declarada lá se fecha
   nesta story, no schema de entrada

7. **Given** a rota
   **When** um cliente ou a portaria a chama
   **Then** recebo `403` com `SEM_PERMISSAO`
   **And** sem cookie de sessão recebo `401` com `NAO_AUTENTICADO`, **não** `403`
   **And** a proteção é `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` na assinatura, nunca um
   `if` no corpo — AD-9

8. **Given** valores fora do que o domínio aceita
   **When** eu publico
   **Then** `capacidade <= 0`, `preco_centavos < 0`, nome de setor vazio e nome de evento vazio são
   recusados com `422` **antes** de chegar ao banco
   **And** `vendidos` e `id` mandados no corpo são **ignorados** — não estão no schema de entrada, e
   um setor nasce com `vendidos = 0` mesmo que alguém peça outra coisa (AD-13)

9. **Given** `data_hora`
   **When** ela chega sem fuso horário
   **Then** recebo `422` — AD-11 pede ISO-8601 **com offset**, e um horário sem fuso é um horário
   sem significado
   **And** com offset, ela é gravada em `TIMESTAMPTZ`, e o `Z` do frontend é o que o navegador
   converteu do fuso de quem preencheu

10. **Given** a tela `/organizador/publicar` com resultados
    **When** eu clico numa fila do catálogo
    **Then** a escolha vai para a URL (`?q=baco&escolhido=G5vYZ9a1kd`), a fila fica marcada e o
    passo **2 · Data, local e setores** aparece abaixo
    **And** recarregar mantém a escolha, o botão voltar a desfaz, e o link é compartilhável
    **And** o passo 1 continua **sem** `"use client"` — a seleção é navegação, não estado

11. **Given** o passo 2
    **When** eu o preencho
    **Then** nome e imagem aparecem **travados**, copiados do catálogo, e o `origem_externa_id`
    viaja escondido no envio
    **And** `local` e `cidade` chegam pré-preenchidos com o que o catálogo trouxe e **são
    editáveis**
    **And** data e horário são dois campos, cada um com seu `<label>`
    **And** cada linha de setor tem nome, capacidade e preço em reais, com `+ Adicionar setor` e um
    `×` que some quando resta uma linha só

12. **Given** que a publicação deu certo
    **When** a resposta chega
    **Then** o formulário dá lugar a uma **confirmação na própria tela**, com nome, data por
    extenso, local, cidade e a lista de setores com **capacidade e preço exatos** — UX-DR7, é o
    inventário do organizador
    **And** não há `redirect`: "Meus eventos" é a Story 2.6, e mandar alguém para a raiz vazia
    pareceria defeito
    **And** existe um caminho de volta ao passo 1 (`Publicar outro`), com a URL limpa

13. **Given** um erro da API
    **When** ele chega na tela
    **Then** o texto é escolhido pelo `codigo` (`EVENTO_SEM_SETOR`, `SETOR_DUPLICADO`,
    `DADOS_INVALIDOS`), **nunca** pela `mensagem` do servidor — convenção da Story 1.4
    **And** o aviso vai no `AvisoDeErro` que já existe, com o `role="alert"` dele

14. **Given** uma tela abaixo de 900px
    **When** eu preencho o formulário
    **Then** os campos ocupam a largura inteira, um por linha
    **And** nada transborda na horizontal — inclusive a linha de setor, que tem quatro colunas no
    desktop

15. **Given** a tela inteira
    **When** eu a inspeciono
    **Then** não há card, sombra nem canto arredondado — UX-DR3
    **And** nenhum dos cinco anti-padrões do UX-DR10 aparece
    **And** nenhum hex novo entra em `*.module.css`: só `var(--token)`

16. **Given** a suíte do backend
    **When** eu a rodo com o Compose no ar e a rede desligada
    **Then** ela passa inteira, e os **140** testes anteriores continuam verdes
    **And** o número final está registrado
    **And** `npm run build`, `npx tsc --noEmit` e `npm run lint` passam limpos

17. **Given** os três READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta a rota, o service, os dois códigos de erro novos e por
    que a lista vazia não é validação do Pydantic
    **And** `frontend/README.md` documenta a seleção pela URL, a primeira ilha `"use client"` do
    organizador e a conversão de reais para centavos
    **And** `README.md` da raiz ganha as decisões desta story **com a alternativa descartada** de
    cada uma, em primeira pessoa
    **And** a linha *"Tela de editar evento"* de *O que não está pronto* ganha a companhia da dívida
    temporária do AD-7 (ver AC abaixo)

18. **Given** o AD-7 (*publicar exige ao menos um usuário de portaria escalado*)
    **When** esta story termina
    **Then** ele **ainda não vale** — e isso está escrito, não escondido
    **And** o `README.md` registra a janela: entre a 2.4 e a 2.5 é possível publicar evento sem
    ninguém autorizado a validar, e os eventos criados nessa janela ficam sem vínculo de portaria
    **And** a Story 2.5 é quem fecha isso, acrescentando `EVENTO_SEM_PORTARIA` a esta mesma rota

> **De onde vem cada critério.** O `epics.md` traz **cinco** blocos para a Story 2.4: os dados do
> catálogo copiados com `vendidos = 0`; os dados que não mudam depois; o `422 EVENTO_SEM_SETOR`; os
> passos numerados com números exatos (UX-DR7); e o comportamento abaixo de 900px. Eles viraram os
> ACs **1, 3, 4, 12 e 14**.
>
> **AC10, AC11 e AC12** são as decisões que o Igor tomou antes de a story ser escrita — seleção pela
> URL, o que é editável e para onde se vai depois de publicar. **AC5** existe porque a
> `uq_setor_evento_id_nome` nasceu na 2.3 e, sem tratamento, ela transforma um erro de digitação do
> organizador num `500`. **AC2, AC7 e AC8** são a superfície de escrita chegando: é a primeira rota
> do projeto que **grava** algo pedido por quem chamou, e as três coisas que um corpo malicioso
> tentaria (dono, papel, estoque) precisam estar fechadas por construção. **AC6** fecha a tensão que
> a 2.3 declarou de propósito. **AC9** é o AD-11. **AC18** é honestidade: a story contraria uma
> invariante da arquitetura por uma story de distância, e isso se escreve.

## Tasks / Subtasks

- [x] **T1. `app/schemas/evento.py` — o contrato de entrada e de saída** (AC: 1, 6, 8, 9)
  - [x] Arquivo novo. Quatro classes: `SetorEntrada`, `EventoEntrada`, `SetorSaida`, `EventoSaida`
  - [x] Docstring do módulo explicando **o que este schema recusa e por quê** — no estilo do
        `schemas/auth.py`, que é o modelo de referência de comentário neste projeto
  - [x] Campos e limites exatamente como em *O contrato da API, campo a campo*. Nada além deles
  - [x] `origem_externa_id` é **obrigatório** aqui, e é a única amarra da regra de produto — a
        coluna do banco continua anulável (decisão da 2.3, não a mude)
  - [x] Reusar o `BeforeValidator` de `.strip()` do padrão de `schemas/auth.py`. ⚠️ **Não importe
        `_limpar_texto` de lá** — é privado daquele módulo; ou você o copia (duas linhas), ou o
        promove. Ver *Suposições declaradas*
  - [x] ⚠️ **`setores` NÃO leva `min_length=1`.** O AC4 pede o código `EVENTO_SEM_SETOR`, e
        `min_length` produziria `DADOS_INVALIDOS`. Armadilha 1
  - [x] `data_hora`: validador exigindo `tzinfo is not None`
  - [x] `EventoSaida` e `SetorSaida` com `ConfigDict(from_attributes=True)`, como o `UsuarioSaida`
  - [x] **Sem `extra="forbid"`**, pelo mesmo motivo escrito no `CadastroEntrada`: campo
        desconhecido ignorado é garantia mais forte que campo desconhecido recusado. `vendidos` no
        corpo não existe para o schema, então não tem como chegar ao modelo

- [x] **T2. `app/services/evento.py` — a regra e a transação** (AC: 1, 2, 4, 5)
  - [x] Arquivo novo, uma função pública: `publicar(sessao, organizador, dados) -> Evento`
  - [x] Docstring seguindo a convenção do `services/autenticacao.py`: **service que escreve abre e
        fecha a transação**; o router nunca dá `commit`
  - [x] Ordem obrigatória: (1) lista vazia → `EVENTO_SEM_SETOR`; (2) nomes duplicados →
        `SETOR_DUPLICADO`; (3) só então monta `Evento` e `Setor`. As duas recusas acontecem **antes**
        de qualquer `add`, e é isso que garante o "nenhum evento órfão" do AC4
  - [x] Duplicata: comparar `nome.strip().casefold()`. ⚠️ `casefold()` e não `lower()` — é o certo
        para comparação insensível a caixa em texto que não é ASCII
  - [x] `publicado_em=datetime.now(timezone.utc)` no ato
  - [x] **Nunca** passe `vendidos` ao construir `Setor`: o `server_default=text("0")` da 2.3 é quem
        responde. Passar `vendidos=0` funcionaria e criaria uma segunda fonte para o mesmo valor
  - [x] `sessao.add(evento)` com os setores dentro do `relationship` — o `cascade="all,
        delete-orphan"` da 2.3 grava os filhos junto, numa transação só
  - [x] `commit()` e `refresh()` no fim, como o `cadastrar()` faz
  - [x] **Sem `try/except IntegrityError`.** As duas violações possíveis já foram barradas acima; um
        `except` genérico aqui esconderia bug de verdade

- [x] **T3. `app/api/organizador.py` — a rota** (AC: 1, 2, 7)
  - [x] Estender o arquivo que já existe, **sem reescrever** a rota do catálogo nem o docstring dela
  - [x] `@router.post("/eventos", response_model=EventoSaida, status_code=201)`
  - [x] Assinatura: `dados: EventoEntrada`,
        `organizador: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`,
        `sessao: Session = Depends(obter_sessao)`
  - [x] ⚠️ O parâmetro do usuário se chama **`organizador`**, não `_`: aqui ele é usado. O `_` da
        rota do catálogo existe porque lá o objeto é descartado — copiar o `_` para cá e depois
        precisar dele é o caminho para alguém ler o `organizador_id` do corpo
  - [x] Corpo: `return evento.publicar(sessao, organizador, dados)`. **Uma linha** — sem `commit`,
        sem `try`, sem montar objeto
  - [x] Docstring curta explicando que **esta** rota tem service, e por quê: existe transação e
        existem invariantes. É o critério que o próprio arquivo já declara para a exceção do
        catálogo — agora com o outro lado do par
  - [x] `app/main.py` **não muda**: o router já está registrado desde a 2.2

- [x] **T4. `tests/test_organizador_eventos.py`** (AC: 1–9, 16)
  - [x] Arquivo novo. Precisa do Compose no ar (faz login de verdade) e **zero rede**
  - [x] Helper local `_corpo(**ajustes)` devolvendo um corpo válido, com ajuste por parâmetro — é o
        que impede quinze dicionários quase iguais
  - [x] `_entrar(cliente, usuario)` copiado de `tests/test_organizador_catalogo.py:38`
  - [x] `fabricar_usuario(PapelUsuario.ORGANIZADOR, "organizador1@exemplo.com")` — ⚠️ o e-mail
        padrão da fixture é fixo; dois usuários no mesmo teste precisam de e-mails distintos
  - [x] Os quinze casos da tabela em *Testing*, um teste cada
  - [x] ⚠️ O teste do AC3 instala um transporte que levanta se for chamado:
        `_instalar_transporte(monkeypatch, lambda r: pytest.fail("a publicação chamou a Ticketmaster"))`
  - [x] Ler do **banco** para conferir o que foi gravado (`sessao.get(Evento, id)`), não só o corpo
        da resposta — a resposta prova o schema, o banco prova a gravação

- [x] **T5. O passo 1 fica selecionável** (AC: 10, 15)
  - [x] `src/app/(site)/organizador/publicar/page.tsx`: ler `escolhido` de `searchParams` do mesmo
        jeito que `q` já é lido (pode chegar como `string[]`)
  - [x] Cada fila vira `<Link href={...}>`. Montar o destino com `URLSearchParams` — ⚠️ **não**
        concatene à mão: `q` já passou por `encodeURIComponent` uma vez em `catalogo.ts` e
        concatenar aqui é onde nasce a codificação dupla
  - [x] Quando `q` está vazio, ele **não** entra na URL — `?escolhido=…` sozinho
  - [x] A fila escolhida ganha a marca: fio âmbar de 3px à esquerda e a etiqueta `Selecionado` em
        versalete (`proto-jornal-noturno.html:558-563`). As outras mostram `Selecionar` em kicker
  - [x] `const escolhido = resultado.estado === "ok" ? resultado.itens.find(...) : undefined`
  - [x] ⚠️ **Se o `escolhido` não estiver na lista atual, o passo 2 simplesmente não aparece** — sem
        erro, sem aviso. Acontece quando o termo muda ou o catálogo cai. Armadilha 4
  - [x] Passo 2 só é renderizado com `escolhido` definido, sob um `secTitulo` novo:
        `2 · Data, local e setores`
  - [x] **Nenhum `"use client"` neste arquivo.** Ele continua Server Component

- [x] **T6. `src/components/FormularioPublicacao.tsx` — a ilha** (AC: 11, 12, 13, 14)
  - [x] Arquivo novo, `"use client"` na primeira linha. É a **primeira** ilha de cliente do fluxo do
        organizador — escreva no comentário do componente por que ela existe
  - [x] `type Props = { item: ItemDoCatalogo }`
  - [x] Estado: `setores` (lista de `{ nome, capacidade, preco }`, começando com **uma** linha),
        `enviando`, `erro`, `publicado` (o `EventoSaida` devolvido, ou `null`)
  - [x] Campos de evento com o `Campo` que já existe: `Data` (`type="date"`), `Horário`
        (`type="time"`), `Casa de show` (`defaultValue={item.local ?? ""}`), `Cidade`
        (`defaultValue={item.cidade ?? ""}`)
  - [x] Bloco travado no topo: miniatura, nome em serifada e a origem em versalete. **Não** é
        `<input readOnly>` — é texto. Campo desabilitado que ninguém pode editar é campo que não
        deveria ser campo
  - [x] Linhas de setor escritas à mão (não com `Campo`): grade de quatro colunas, `<label htmlFor>`
        **visualmente oculto** em toda linha, com uma faixa de kickers acima nomeando as colunas.
        UX-DR9 pede rótulo associado, não rótulo visível — mas `placeholder` não conta. Ver *A tela,
        em texto*
  - [x] `+ Adicionar setor` e `×` por linha (`aria-label={\`Remover setor ${i + 1}\`}`); o `×` some
        quando `setores.length === 1`
  - [x] Conversões antes do `POST`, ambas na própria página: `reaisParaCentavos` e a junção de data
        com hora. As duas estão escritas em *As duas conversões*
  - [x] `chamarApi<EventoSaida>("/organizador/eventos", { method: "POST", body: JSON.stringify(...) })`
  - [x] `mensagemParaCodigo(codigo)` local, no padrão do `FormularioCadastro.tsx:15`
  - [x] `AvisoDeErro` para o erro; `Botao` para `Publicar evento`, com `disabled={enviando}`
  - [x] Sucesso → `setPublicado(evento)`, e o retorno vira o bloco de confirmação. **Sem
        `router.push`, sem `router.refresh`** — nada da sessão mudou, e não há para onde ir
  - [x] `src/app/(site)/organizador/publicar/page.module.css`: as classes do passo 2, da linha de
        setor e da confirmação. Só `var(--token)` — nenhum hex

- [x] **T7. Verificação** (AC: 14, 15, 16)
  - [x] `uv run pytest` **inteiro**, com o Compose no ar. Registrar o número final
  - [x] `npm run build`, `npx tsc --noEmit`, `npm run lint` — os três limpos
  - [x] ⚠️ `PageProps<"/organizador/publicar">` já existe (a rota é da 2.2), mas o **componente
        novo** não muda tipos de rota — se o `tsc` reclamar de `PageProps`, rode `npx next typegen`
  - [x] Conferir na tela, com o `next dev` no ar: publicar de verdade e ver a linha no banco
        (`docker compose exec ... psql`, `select * from setor;`)
  - [x] Abaixo de 900px: um campo por linha, e **nada** rolando na horizontal
  - [x] ⚠️ Conferir que `schemas/evento.py`, `services/evento.py`, `tests/test_organizador_eventos.py`
        e `FormularioPublicacao.tsx` **estão rastreados** pelo git antes de dar a story por pronta
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero (AD-2 continua valendo)

- [x] **T8. Os três READMEs** (AC: 17, 18) — obrigatório, regra do projeto
  - [x] `backend/README.md`:
    - [x] Seção nova **Publicar evento** (depois de *Evento e setor*): a rota, o corpo, os dois
          códigos novos, e **por que `EVENTO_SEM_SETOR` não é validação do Pydantic**
    - [x] *O paradigma: `routers → services → models`*: esta rota é o **outro lado** da exceção do
          catálogo. Escreva o par — o critério "existe transação ou invariante?" agora tem um
          exemplo de cada lado
    - [x] *Estrutura*: `schemas/evento.py` e `services/evento.py` na árvore
    - [x] *Testes*: número novo e `test_organizador_eventos.py` na lista
    - [x] *Histórico desta camada*: entrada **Story 2.4**
  - [x] `frontend/README.md`:
    - [x] Em *A tela do organizador*: o passo 2, a seleção pela URL e a primeira ilha `"use client"`
    - [x] *Estrutura*: `components/FormularioPublicacao.tsx`
    - [x] A conversão de reais para centavos, e por que ela mora no cliente
    - [x] *Histórico desta camada*: entrada **Story 2.4**
  - [x] `README.md` da raiz — **a parte que o desafio avalia**:
    - [x] As decisões desta story em *Decisões: por que isso e não aquilo*, **uma seção cada**, no
          formato das anteriores: o que decidi · por quê · o que caiu e por que não
    - [x] ⚠️ **Escreva o motivo que o Igor deu, não um motivo plausível.** A matéria-prima está em
          *Decisões que o Igor tomou* — a coluna do meio é a voz dele, e a de trás é a alternativa
          descartada. Se faltar o porquê de alguma, **pergunte a ele** antes de inventar um
    - [x] *O que não está pronto*: linha nova para a **janela do AD-7** (AC18) — publicar sem
          portaria é possível entre a 2.4 e a 2.5, e a 2.5 fecha
    - [x] *O que não está pronto*: a linha **"Evento publicado entre os dados semeados"** continua
          verdadeira (o seed não mudou), mas o impedimento agora é só a decisão do show — confira se
          o texto ainda está correto depois desta story
    - [x] Primeira pessoa em tudo, como o Igor escrevendo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A coluna do meio é o material do README da
raiz (T8) — é o "por quê" dele, e é isso que precisa aparecer lá, em primeira pessoa.**

| Assunto | Escolha, e o motivo dele | O que caiu, e por que não |
|---|---|---|
| Como a atração chega ao passo 2 | **Pela URL**, como a busca: cada fila é um `<Link>` para `?q=…&escolhido=…`. É a mesma decisão que já está registrada no README para a busca da 2.2 — a escolha na URL é recarregável, compartilhável e o botão voltar a desfaz, sem uma linha de estado | *Estado no cliente com `onClick`*: mostraria o passo 2 sem recarregar, e é o que qualquer formulário moderno faria — caiu porque tiraria a escolha da URL (recarregar perde, voltar não desfaz, o link não abre no mesmo lugar) e transformaria a tela **inteira** numa ilha de cliente, contra a convenção "Server Component por padrão" da espinha. *Rota própria `/organizador/publicar/[id_externo]`*: mais limpa de ler e a mais parecida com um wizard de verdade; caiu porque a atração precisaria ser buscada de novo por id na Discovery — endpoint novo na integração e mais uma chamada de cota por publicação — ou ter todos os campos repassados pela URL, que é a mesma coisa com mais barulho |
| Como o formulário envia | **Client Component com `chamarApi`**, a primeira ilha do fluxo do organizador. Linha de setor que aparece e some ao clicar é interação que exige o navegador, e é exatamente o caso que a espinha reserva para `"use client"` | *Server Action do Next*: manteria a tela sem JavaScript nenhum e é o idiomático da versão instalada — caiu por ser mecanismo novo no projeto (nenhuma story usou até aqui) e por não resolver o setor dinâmico, que continuaria exigindo número fixo de linhas. *Cinco linhas fixas, sem JavaScript*: mais simples de tudo, e ainda assim precisaria de Server Action ou route handler para o `POST` — e o `+ Adicionar setor` do protótipo deixaria de existir |
| Publicar de fato agora | **`publicado_em` preenchido no ato**, mesmo com o AD-7 (portaria obrigatória) chegando só na 2.5. A story entrega algo observável de ponta a ponta: o primeiro evento real do sistema, à venda, criado pela interface. E o motivo do Igor, nas palavras dele: **feito assim o risco real é baixo, então é melhor fazer agora para não sobrar trabalho nas próximas stories.** A janela dura uma story, dentro de uma branch que só ele publica — não existe ninguém de fora criando evento nesse intervalo, e o pior caso é um evento de teste sem portaria, que ele mesmo apaga. Segurar o `publicado_em` até a 2.5 pagaria essa janela com retrabalho garantido: a 2.5 teria que reabrir o service, a rota e a tela de confirmação que a 2.4 acabou de escrever, só para mover o carimbo de lugar | *Gravar rascunho e deixar a 2.5 publicar*: o AD-7 valeria desde o primeiro minuto e nunca existiria evento publicado sem alguém autorizado a validar — caiu pelo motivo acima, e porque a 2.4 terminaria sem nada visível no produto, com um botão "Publicar evento" que não publica. **O custo continua real e está no AC18:** entre a 2.4 e a 2.5 dá para publicar sem portaria, e os eventos criados nessa janela ficam sem vínculo. Vai para o README como dívida datada, não como omissão |
| Para onde vai depois de publicar | **Confirmação na própria tela**, com os números exatos do que foi gravado | *`redirect("/")`*: uma linha e o padrão de todo formulário — caiu porque a raiz é o estado vazio da programação até a Story 3.1, e publicar para cair numa tela que diz "a programação entra no ar quando os primeiros eventos forem publicados" pareceria defeito. *Adiantar `/organizador/meus-eventos`*: resolveria o destino de vez e invadiria a Story 2.6, estourando o recorte de um commit por story |
| Preço | **Campo em reais (`120,00`), convertido para centavos antes do `POST`.** A API só conhece `preco_centavos: int` — o AD-11 fica intacto na fronteira | *Aceitar reais na API e converter no backend*: tiraria o parsing do cliente — caiu porque põe ponto flutuante no contrato, que é exatamente o que o AD-11 existe para impedir, e criaria dois campos monetários com unidades diferentes no mesmo projeto. *Campo em centavos direto*: zero conversão e zero ambiguidade, ao custo de o organizador fazer a conta de cabeça a cada setor |
| Data e hora | **Dois campos**, data e horário, como o protótipo desenha. Cada um com seu rótulo, e o horário legível em tela pequena | *Um `<input type="datetime-local">`*: um campo a menos e uma junção a menos — caiu porque o widget nativo varia bastante entre navegadores, e o protótipo mostra os dois lado a lado |
| O que é editável | **Nome e imagem travados; `local` e `cidade` pré-preenchidos do catálogo e editáveis.** O motivo do Igor, nas palavras dele: **turnê.** A mesma atração do catálogo vira várias datas, em casas e cidades diferentes — o registro da Discovery traz a casa de *uma* data, que não é necessariamente a que o organizador está publicando. Quem sabe onde o show dele acontece é ele, não a Ticketmaster. É o mesmo raciocínio que fez `origem_externa_id` nascer **sem** `UNIQUE` na Story 2.3 | *Tudo editável, inclusive o nome*: o catálogo viraria sugestão de preenchimento e cobriria mais casos — caiu porque esvazia a decisão já registrada no README (*"publicação exige atração do catálogo"*): com o nome livre, o cadastro manual volta pela porta dos fundos, e o ingresso emitido poderia dizer um nome que a listagem não diz. *Nada pré-preenchido*: evitaria que um dado errado do catálogo passasse despercebido, ao custo de redigitar o que a Ticketmaster já informou certo na maioria das vezes |

### ⚠️ A dívida que esta story cria de propósito

O **AD-7** diz, com estas palavras: *"Publicar um evento exige ao menos um usuário de portaria
escalado — isso impede evento publicado sem ninguém autorizado a validar."*

Esta story **não cumpre isso**, e a decisão foi consciente (tabela acima, terceira linha): o risco
real da janela é baixo — ela dura uma story, numa branch que só o Igor publica — e fechá-la agora
custaria retrabalho garantido na 2.5, que teria que reabrir o service, a rota e a confirmação para
mover um carimbo de lugar. A Story 2.5 é quem acrescenta `EVENTO_SEM_PORTARIA` a esta mesma rota.

Três consequências que você precisa conhecer:

1. **Não "adiante" a regra.** Escrever a validação de portaria aqui exigiria a tabela
   `evento_portaria`, que é migração da 2.5, e a recusa de escalar quem não tem papel `PORTARIA`,
   que é AC de lá. Meia regra é pior que nenhuma
2. **Escreva a janela no README.** É o AC18. Uma invariante contrariada e não registrada é a
   diferença entre decisão e descuido
3. **Eventos publicados nesta janela ficam sem portaria para sempre**, porque não há tela de editar
   evento (corte consciente já registrado). Se você publicar eventos de teste agora, eles não são
   validáveis na Epic 5

### Suposições declaradas, não decisões suas

Uma linha para trocar se o Igor discordar. Estão aqui porque a story precisa de uma resposta para
existir, não porque alguém escolheu por ele.

- **O backend copia o que o corpo mandou; não vai à Discovery conferir.** `nome`, `imagem_url` e
  `origem_externa_id` chegam do cliente, que os leu da lista que o próprio backend devolveu na mesma
  sessão. A alternativa é o service buscar a atração por id na Discovery e copiar dela — seria à
  prova de corpo forjado, ao custo de uma chamada de cota por publicação, de um endpoint novo na
  integração (`/events/{id}.json`) e de a publicação passar a falhar quando a Ticketmaster cai. O
  que **é** verificado continua sendo o que importa: só organizador publica, o dono é a sessão, e o
  estoque nasce em zero
- **Não há validação de data no passado.** Publicar um show para ontem é aceito. Validar exigiria
  decidir a margem (o dia inteiro? a hora?) e um relógio no teste. Está em *Perguntas em aberto*
- **Teto de 20 setores por evento.** Número redondo, escolhido para haver um teto — sem ele, um
  corpo com 10.000 setores é 10.000 `INSERT` numa transação. Se o Igor achar baixo, é uma constante
- **`_limpar_texto` é copiado, não importado.** `schemas/auth.py` o declara com `_` inicial, ou
  seja, privado do módulo. Copiar duas linhas para `schemas/evento.py` é menos ruim que importar um
  privado de outro módulo; promovê-lo para um `schemas/_comum.py` é o certo **no terceiro
  consumidor**, seguindo a mesma convenção de `Campo` e `Botao` registrada no README
- **A linha de setor começa com uma, não com três.** O protótipo mostra três preenchidas porque
  desenha o resultado final. Uma linha vazia mais o `+ Adicionar setor` é o mínimo que já comunica
  como funciona
- **As duas funções de conversão moram no próprio componente.** Um consumidor só. A convenção do
  projeto é extrair no segundo — precedente de `Campo` e `Botao`, registrado no README da raiz

### O contrato da API, campo a campo

`POST /organizador/eventos` · `201` · `response_model=EventoSaida`

```json
{
  "origem_externa_id": "G5vYZ9a1kd",
  "nome": "Baco Exu do Blues — Bluesman Vivo",
  "imagem_url": "https://s1.ticketm.net/dam/a/....jpg",
  "data_hora": "2026-08-15T00:00:00.000Z",
  "local": "Espaço Unimed",
  "cidade": "São Paulo",
  "setores": [
    { "nome": "Pista", "capacidade": 800, "preco_centavos": 12000 },
    { "nome": "Camarote", "capacidade": 60, "preco_centavos": 42000 }
  ]
}
```

**`EventoEntrada`**

| Campo | Tipo | Regra | Por quê |
|---|---|---|---|
| `origem_externa_id` | `str` | **obrigatório**, `1..64` depois do `strip` | A regra "todo evento nasce do catálogo" mora aqui, não no banco (AC6) |
| `nome` | `str` | `1..200` depois do `strip` | Copiado do catálogo (AD-1). O tamanho é o da coluna |
| `imagem_url` | `str \| None` | `≤500` | A Discovery pode não trazer |
| `data_hora` | `datetime` | **com `tzinfo`**, senão `422` | AD-11: ISO-8601 com offset |
| `local` | `str` | `1..200` depois do `strip` | Quem preenche é o organizador |
| `cidade` | `str \| None` | `≤120` | Pode faltar no catálogo |
| `setores` | `list[SetorEntrada]` | `max_length=20`, **sem `min_length`** | Armadilha 1 |

**`SetorEntrada`**

| Campo | Tipo | Regra |
|---|---|---|
| `nome` | `str` | `1..80` depois do `strip` |
| `capacidade` | `int` | `ge=1` — o `CHECK` da 2.3 diz `> 0`, e o schema recusa antes |
| `preco_centavos` | `int` | `ge=0` — inteiro, nunca `float` (AD-11) |

**Não existem, e não devem passar a existir:** `organizador_id` (vem da sessão), `vendidos` (nasce
zero, AD-13), `id` (o banco gera), `publicado_em` (o service carimba).

**`EventoSaida`** — o que a tela usa para montar a confirmação. `ConfigDict(from_attributes=True)`,
como o `UsuarioSaida`:

```json
{
  "id": "3f2a…", "nome": "…", "data_hora": "2026-08-15T00:00:00Z",
  "local": "Espaço Unimed", "cidade": "São Paulo", "imagem_url": "…",
  "origem_externa_id": "G5vYZ9a1kd", "publicado_em": "2026-08-11T17:22:04Z",
  "setores": [
    { "id": "9c1b…", "nome": "Pista", "capacidade": 800, "vendidos": 0,
      "preco_centavos": 12000 }
  ]
}
```

`vendidos` **entra** na saída — é o inventário do organizador (UX-DR7), e o AC1 se prova lendo
zero ali. `organizador_id` fica de fora: quem pediu já sabe quem é.

**Códigos de erro novos:**

| Código | Status | Quando |
|---|---|---|
| `EVENTO_SEM_SETOR` | `422` | Lista de setores vazia ou ausente |
| `SETOR_DUPLICADO` | `422` | Dois setores com o mesmo nome no mesmo corpo, ignorando caixa |

Os dois seguem o formato único da API (`{"erro": {"codigo", "mensagem"}}`) porque são
`ErroDeDominio` — o handler de `app/main.py:64` já traduz. **Nenhum handler novo.**

[Fonte: epics.md#Story 2.4 · ARCHITECTURE-SPINE.md#AD-1, #AD-9, #AD-11, #AD-13 · backend/app/core/erros.py]

### As duas conversões, e por que elas são do cliente

**Reais para centavos.** O campo aceita `120`, `120,00` ou `120.00`. A regra evita adivinhar:

```ts
function reaisParaCentavos(valor: string): number | null {
  const bruto = valor.trim();
  // Com vírgula, ela é o separador decimal e o ponto é milhar ("1.234,50").
  // Sem vírgula, o ponto é o decimal ("120.50"). Assim "1.234" não vira
  // 123.400 por adivinhação — ele falha na regra abaixo e vira erro na tela.
  const normalizado = bruto.includes(",")
    ? bruto.replace(/\./g, "").replace(",", ".")
    : bruto;

  if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;
  return Math.round(Number(normalizado) * 100);
}
```

`null` é erro de preenchimento, tratado na tela **antes** do `fetch` — mesma disciplina das duas
regras do `FormularioCadastro`.

**Data e hora para instante.**

```ts
const instante = new Date(`${data}T${hora}`);   // "2026-08-14" + "21:00"
if (Number.isNaN(instante.getTime())) { /* erro na tela */ }
const data_hora = instante.toISOString();       // "2026-08-15T00:00:00.000Z"
```

⚠️ **A junção é obrigatória, e não é estética.** `new Date("2026-08-14")` — data sozinha — é
interpretada como **UTC** pela especificação; `new Date("2026-08-14T21:00")` — data com hora e sem
offset — é interpretada como **hora local**. Um show às 21h em São Paulo viraria 21h UTC, ou seja,
18h local, se alguém "simplificasse" mandando só a data. É a armadilha 3.

### A tela, em texto

Referência: `proto-jornal-noturno.html:545-608`. O protótipo é **ponto de partida, não gesso** —
grade e espaçamento estão na lista do que se ajusta livremente (`DESIGN.md#Como usar este documento`).

```
  1 · Escolha no catálogo                    TICKETMASTER DISCOVERY
  ─────────────────────────────────────────────────────────────────
  [ Buscar no catálogo             ]  [ BUSCAR ]
  ═════════════════════════════════════════════════════════════════
 ┃▓▓▓▓  Baco Exu do Blues — Bluesman Vivo            SELECIONADO      ← fio âmbar
 ┃▓▓▓▓  TICKETMASTER · ESPAÇO UNIMED · SÃO PAULO
  ─────────────────────────────────────────────────────────────────
  ▓▓▓▓  Baco Exu do Blues — Festival Turá             SELECIONAR
  ▓▓▓▓  TICKETMASTER · JEUNESSE ARENA · RIO DE JANEIRO
  ─────────────────────────────────────────────────────────────────

  2 · Data, local e setores
  ─────────────────────────────────────────────────────────────────
  ▓▓▓▓  Baco Exu do Blues — Bluesman Vivo        ← travado, não é campo
        TICKETMASTER · G5VYZ9A1KD

  DATA                    HORÁRIO
  [ 14/08/2026 ]          [ 21:00 ]
  CASA DE SHOW
  [ Espaço Unimed                                    ]
  CIDADE
  [ São Paulo                                        ]

  SETORES
  SETOR              CAPACIDADE      PREÇO (R$)
  [ Pista        ]   [ 800      ]    [ 120,00 ]   ×
  [ Camarote     ]   [ 60       ]    [ 420,00 ]   ×
  + ADICIONAR SETOR
  ─────────────────────────────────────────────────────────────────
                                              [ PUBLICAR EVENTO ]
```

E a confirmação, no lugar do formulário:

```
  2 · Publicado
  ─────────────────────────────────────────────────────────────────
  PUBLICADO EM 11 DE AGOSTO, 14H22
  Baco Exu do Blues — Bluesman Vivo
  14 de agosto de 2026, 21h00 · Espaço Unimed · São Paulo

  PISTA        800 lugares      R$ 120,00
  CAMAROTE      60 lugares      R$ 420,00

  Publicar outro →
```

- **Números exatos, sem medidor** — UX-DR7 e `EXPERIENCE.md#medidor`: proporção é para o cliente;
  organizador vê o inventário
- Nome do show em **serifada**; rótulo, origem e estado em **mono versalete** — UX-DR2
- Fio embaixo de cada linha de setor. **Sem caixa, sem sombra, sem raio** — UX-DR3
- O `×` de remover é `fumaca`, vira `brasa` no hover. Alvo de 44px de altura
- Nada gira e nada pulsa enquanto envia: o `Botao` fica `disabled`, e é só isso
  (`EXPERIENCE.md#Carregando`)
- **Rótulo oculto ≠ rótulo ausente.** As linhas de setor têm `<label htmlFor>` para cada entrada,
  escondido visualmente pelo padrão de "visually hidden" (`position:absolute; width:1px;
  height:1px; clip-path: inset(50%)` — nunca `display:none`, que o tira da árvore de
  acessibilidade). A faixa de kickers acima é decoração que ajuda quem enxerga; o `<label>` é o que
  serve a quem não enxerga

### O que já existe e esta story reusa — leia antes de escrever

| O que | Onde | Como usar aqui |
|---|---|---|
| `Evento` e `Setor` | `app/models/evento.py` | Instancie. **Não mexa no modelo** — nenhuma coluna nova nesta story |
| `exigir_papel` | `app/core/dependencias.py:81` | `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`. Já garante `401` antes de `403` |
| `obter_sessao` | `app/core/db.py` | A `Session` da rota. **Ela não abre transação** — quem confirma é o service |
| `ErroDeDominio` | `app/core/erros.py:88` | Os dois códigos novos. O handler que os traduz já existe |
| Padrão de service que escreve | `app/services/autenticacao.py:61` | `flush`/`commit`/`refresh` e o docstring de transação |
| Padrão de schema | `app/schemas/auth.py` | `BeforeValidator` de `strip`, `Field(min_length/max_length)`, `ConfigDict(from_attributes=True)` |
| Router do organizador | `app/api/organizador.py` | **Estenda**. Não crie `app/api/eventos.py` |
| `_entrar` | `tests/test_organizador_catalogo.py:38` | Login de verdade no `TestClient` |
| `_instalar_transporte` | `tests/test_organizador_catalogo.py:25` | Só para o AC3 — provar que a Ticketmaster **não** é chamada |
| `fabricar_usuario` | `tests/conftest.py:139` | Os três papéis, com e-mail por parâmetro |
| A tela do passo 1 | `frontend/src/app/(site)/organizador/publicar/page.tsx` | **Estenda**. Não crie rota nova |
| `chamarApi` / `ErroDaApi` | `frontend/src/lib/api.ts` | O caminho do navegador. `/api` é prefixado lá dentro — passe `/organizador/eventos` |
| `ItemDoCatalogo` (TS) | `frontend/src/lib/catalogo.ts` | O tipo da prop do formulário. **Não redeclare** |
| `Campo`, `Botao`, `AvisoDeErro` | `frontend/src/components/` | Os três. Não recrie nenhum |
| Formulário de referência | `frontend/src/components/FormularioCadastro.tsx` | O padrão exato: `FormData`, validação local antes do `fetch`, `mensagemParaCodigo`, `disabled={enviando}` |
| Tokens | `frontend/src/app/globals.css` | `var(--fio)`, `var(--breu2)`, `var(--ambar)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)` |

**Não devem ser tocados, e não devem quebrar:** `backend/migrations/` (nenhuma migração nesta
story), `app/models/`, `app/integrations/`, `app/core/`, `app/main.py`, `seeds/`, `tests/conftest.py`,
`docker-compose.yml`, `pyproject.toml`, `frontend/src/lib/servidor.ts`, `sessao.ts`, `api.ts`,
`caminho.ts`, `components/Masthead.tsx`, e as telas de `(entrada)/`.

Se algum deles precisar mudar para esta story funcionar, algo foi feito errado — pare e diga.

### Armadilhas específicas desta story

Em ordem de probabilidade.

**1. `min_length=1` no `setores` produz o código errado.** É a "correção" que qualquer um faria: o
campo exige ao menos um item, então põe o mínimo no `Field`. O resultado é `422` com
`DADOS_INVALIDOS`, e o AC4 pede `EVENTO_SEM_SETOR`. A validação de estrutura é do Pydantic; **"um
evento precisa de ao menos um setor" é regra de negócio**, e regra de negócio mora no service. O
teste que pega isso afirma o `codigo`, não o status.

**2. Nome de setor repetido vira `500` se ninguém o tratar.** A `uq_setor_evento_id_nome` nasceu na
Story 2.3 e é o banco quem a aplica: dois `Pista` no mesmo `INSERT` estouram `IntegrityError` no
`commit`, que sobe até o handler de `Exception` e volta como `ERRO_INTERNO`. Um erro de digitação do
organizador viraria "erro interno do servidor". A verificação no service, **antes** do `add`, é o que
transforma isso num `422` legível.

**3. `new Date("2026-08-14")` é UTC; `new Date("2026-08-14T21:00")` é local.** Explicado em *As duas
conversões*. O sintoma é o show aparecer três horas antes do que foi digitado — e só em produção,
porque quem testa costuma olhar a resposta da API, não o horário renderizado.

**4. `?escolhido=` sobrevive à mudança de termo.** Buscar "baco", escolher, e depois buscar "rosalia"
deixa o `escolhido` na URL apontando para um id que não está mais na lista. O `find` devolve
`undefined`, o passo 2 some — e isso é o comportamento certo, desde que ninguém tenha escrito
`itens.find(...)!` ou lido `escolhido.nome` sem checar. **Nunca use `!` para calar o TypeScript
aqui**; o `undefined` é um estado real da tela.

**5. Codificação dupla no link.** `q` chega na `page.tsx` já decodificado pelo Next, e
`URLSearchParams` codifica de novo ao montar o `href` — o certo. Concatenar com
`encodeURIComponent` à mão em cima disso produz `%2520` e uma busca que não acha nada. Use
`URLSearchParams` e pare por aí.

**6. `Setor(vendidos=0)` cria uma segunda fonte de verdade.** O `server_default=text("0")` da 2.3 já
responde. Passar `vendidos=0` funciona hoje e é uma linha que alguém vai ter que decidir qual é a
certa no dia em que as duas divergirem.

**7. Rodar só o arquivo novo não é verificação.** A 2.1 perdeu tempo com uma regressão que só
apareceu no `pytest` completo. O AC16 pede a suíte inteira.

**8. Windows App Control bloqueia os `.exe` da virtualenv nesta máquina.** Se `uv run pytest` falhar
com `os error 4551`, chame pelo módulo: `uv run python -m pytest`. Documentado desde a Story 1.1.

**9. `Campo` traz `margin-bottom` do rótulo.** Já mordeu na 2.2 (o `.botaoBusca` do
`page.module.css` compensa isso à mão). Vale lembrar ao alinhar `Data` e `Horário` lado a lado.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      organizador.py           # +POST /organizador/eventos
    schemas/
      evento.py                # NOVO — EventoEntrada, SetorEntrada, EventoSaida, SetorSaida
    services/
      evento.py                # NOVO — publicar()
  tests/
    test_organizador_eventos.py  # NOVO
  README.md
frontend/
  src/
    app/(site)/organizador/publicar/
      page.tsx                 # +seleção pela URL, +passo 2
      page.module.css          # +classes do passo 2, linha de setor e confirmação
    components/
      FormularioPublicacao.tsx # NOVO — a primeira ilha "use client" do organizador
  README.md
README.md                      # decisões + a janela do AD-7
```

Não existe, e não deve passar a existir nesta story: migração nova, `app/models/` alterado,
`evento_portaria` (2.5), `/organizador/meus-eventos` (2.6), `app/api/eventos.py`, `error.tsx`,
`middleware.ts`, `next/image`, qualquer enum de status, qualquer dependência nova.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · backend/README.md#Estrutura · frontend/README.md#Estrutura]

### Testing

**Backend, `tests/test_organizador_eventos.py`** — precisa do Compose no ar (login de verdade) e
**zero rede**.

| O que o teste prova | AC |
|---|---|
| Organizador publica → `201`, e o evento está no **banco** com os campos do catálogo copiados | 1 |
| Cada setor gravado tem `vendidos == 0` e o `preco_centavos` que foi mandado | 1 |
| `publicado_em` vem preenchido e com fuso | 1 |
| `organizador_id` é o da sessão — com **dois** organizadores, o dono é quem publicou | 2 |
| Um `organizador_id` mandado no corpo é ignorado | 2 |
| Publicar **não** chama a Ticketmaster (transporte que falha se chamado) | 3 |
| `setores: []` → `422` com `EVENTO_SEM_SETOR`, e **nenhum** evento no banco depois | 4 |
| Dois `Pista` → `422` com `SETOR_DUPLICADO`, e nada gravado | 5 |
| `Pista` e ` pista ` também colidem | 5 |
| `origem_externa_id` ausente ou vazio → `422` | 6 |
| Cliente → `403 SEM_PERMISSAO`; portaria → `403` | 7 |
| Sem cookie → `401 NAO_AUTENTICADO`, **não** `403` | 7 |
| `capacidade = 0` e `preco_centavos = -1` → `422` (Pydantic, antes do banco) | 8 |
| `vendidos: 99` no corpo é ignorado — o setor nasce com `0` | 8 |
| `data_hora` sem fuso → `422`; com offset → gravada | 9 |
| A rota aparece no `/openapi.json` com `201` e o schema de saída | 1 |

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são sete caminhos:

1. Entrar como `organizador@rockhub.dev`, buscar, **clicar numa fila** → a URL ganha `escolhido=`, a
   fila fica marcada, o passo 2 aparece
2. Recarregar a página → a escolha continua. Botão voltar → a escolha some
3. Buscar outro termo com a escolha na URL → o passo 2 some, sem erro na tela
4. Publicar com um setor → confirmação com nome, data por extenso, capacidade e preço
5. Publicar com dois setores de mesmo nome → a tela diz o que aconteceu, sem quebrar
6. Publicar com preço `abc` → recusa **antes** de ir à rede
7. Abaixo de 900px: um campo por linha, nada rolando na horizontal

**Baseline: 140 testes passando** (`backend/README.md#Testes`, conferido em 2026-08-11, ao fim da
Story 2.3). Registre o número final no `backend/README.md` e nas notas de conclusão.

### Inteligência das stories anteriores

**Da 2.3 — a story que criou as tabelas que esta grava:**

- **A tensão declarada se fecha aqui.** `origem_externa_id` é anulável no banco *de propósito*, e a
  regra "todo evento nasce de uma atração do catálogo" foi explicitamente adiada para o schema de
  entrada desta story. É o AC6 — **não** mude a coluna
- **`publicado_em` é anulável para tornar verificável o AC da Story 3.1.** Esta story sempre o
  preenche; o estado `NULL` continua existindo no banco e sem tela que o produza, como a 2.3 previu
- **`vendidos` tem `server_default`**, não `default` do Python. Armadilha 6
- **As quatro constraints do `setor` são rede de segurança, não a regra.** O schema de entrada
  recusa antes; o `CHECK` é o que sobra se algum caminho escapar

**Da 2.2 — a story que criou a tela que esta estende:**

- **A busca vive na URL, e a escolha passa a viver junto.** A decisão está registrada no README; esta
  story a estende em vez de contradizê-la
- **`buscarNoCatalogo` nunca levanta.** Não existe `error.tsx`: uma exceção num Server Component
  derruba a tela inteira. O passo 2 depende do resultado do passo 1, então herda essa disciplina
- **A fila do catálogo ficou dentro da `page.tsx`, não virou componente** — um consumidor só. Com o
  passo 2 aparecendo, ela **continua** com um consumidor; não a extraia "já que estou aqui"
- **`Meus eventos` não entra no masthead nesta story.** A tela é a 2.6, e link que cai no 404 não
  fica no repositório

**Da 2.1:** a suíte inteira é a verificação, não o arquivo novo — uma mudança em `Settings` quebrou
um teste de cookie que a story não previa.

**Da 1.5 — o formulário de referência:** `FormularioCadastro.tsx` decide o texto pelo `codigo`, faz
duas validações locais antes do `fetch` e desabilita o botão enquanto envia. Os três padrões valem
aqui sem mudança.

**Do estado do repositório:** branch `Epic-2---Publicação-de-eventos-pelo-organizador`. Último commit
`7120ad0` (a techspec do filtro de classificação); **a Story 2.3 está no disco e ainda não
commitada**. Stories 2.1, 2.2 e 2.3 em `review` — o code review é ao fim da epic. Duas migrações no
repositório: `b750db91bf49` e `b91316d771ae` (esta é a `head`).

[Fonte: _bmad-output/implementation-artifacts/2-1-*.md · 2-2-*.md · 2-3-*.md · 1-5-*.md ·
sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `@router.post`, `status_code=201`, `response_model` |
| Pydantic | 2.13.4 | `Field`, `BeforeValidator`, `field_validator`, `ConfigDict(from_attributes=True)` |
| SQLAlchemy | 2.0.51 | `Session`, `relationship` gravando os filhos junto |
| Next.js | **16.3.0** | `searchParams` é **Promise**; `PageProps<"/rota">` é global e gerado |
| React | 19 | `useState` na ilha; Server Component em todo o resto |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** Esta versão do Next tem quebras em relação ao
que um modelo tem memorizado; a documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudam.

[Fonte: ARCHITECTURE-SPINE.md#Stack · backend/pyproject.toml · frontend/package.json]

### Escopo — o que NÃO fazer aqui

Escalar portaria e `evento_portaria` (2.5) · "Meus eventos" (2.6) · listagem pública (3.1) · página
do evento (3.4) · reserva, pagamento, ingresso (Epic 3) · editar ou apagar evento (corte consciente)
· seed com evento · migração nova · paginação do catálogo · upload de imagem própria.

Cinco tentações concretas:

- **"Já valido a portaria, o AD-7 pede."** Pede, e a validação exige a tabela da 2.5. Meia regra é
  pior que nenhuma — o que esta story deve fazer é **escrever a janela no README** (AC18)
- **"Crio `/organizador/meus-eventos` para ter para onde ir depois de publicar."** A decisão do
  destino já está tomada: confirmação na própria tela. A 2.6 é uma story inteira, com o AC de não
  mostrar evento de outro organizador
- **"Semeio um evento agora que dá."** Dá, e continua sendo decisão de produto do Igor — qual show,
  qual data, quais setores, quais preços. A dívida está registrada no README de propósito
- **"Aproveito e faço o backend buscar a atração na Discovery para conferir."** É a alternativa
  descartada em *Suposições declaradas*: uma chamada de cota por publicação e uma publicação que
  falha quando a Ticketmaster cai. Se discordar, fale com o Igor
- **"Transformo a tela toda em `use client`, fica mais simples."** É exatamente a alternativa que
  caiu na primeira decisão da tabela. A ilha é o formulário; o resto da página fica no servidor

### Project Structure Notes

Esta é a **primeira rota de escrita do domínio** do projeto. `/auth/cadastro` grava, mas grava a
conta de quem chamou; aqui alguém autenticado cria um objeto que outras pessoas vão ver e comprar. É
por isso que três coisas estão fechadas por construção e não por validação: o dono vem da sessão, o
papel vem da assinatura, e o estoque vem do `server_default`.

É também o **outro lado da exceção da Story 2.2**. Aquele router chama a integração direto porque não
sobra regra de negócio; este tem service porque existe transação e existem invariantes. O critério
que separa os dois está escrito no docstring de `app/api/organizador.py` desde a 2.2 — esta story é
quem o exemplifica pela primeira vez. Depois dela, `app/services/` tem dois moradores
(`autenticacao.py` e `evento.py`), e o paradigma da espinha passa a ser observável no código, não só
no diagrama.

No frontend, é a **primeira ilha `"use client"` fora das telas de acesso**. Login e cadastro são
ilhas porque são formulários; esta é a primeira vez que um formulário convive na mesma página com
conteúdo renderizado no servidor — e a fronteira entre os dois é a prop `item`, que atravessa
serializada. As Epics 3 a 5 terão mais (stepper de quantidade, câmera da portaria), e o desenho de
"ilha pequena dentro de página de servidor" nasce aqui.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] — os cinco blocos de AC originais
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR2, FR8, FR16 e o objetivo da epic
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5] — o que **não** é desta story:
  `evento_portaria`, `EVENTO_SEM_PORTARIA` e a recusa de escalar quem não é portaria
- [Source: ARCHITECTURE-SPINE.md#AD-1] — o catálogo é **copiado** na publicação; é o AC1 e o AC3
- [Source: ARCHITECTURE-SPINE.md#AD-7] — publicar exige portaria escalada; é a dívida do AC18
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel declarado na assinatura, nunca `if` no corpo
- [Source: ARCHITECTURE-SPINE.md#AD-11] — centavos em `BIGINT`, tempo em `TIMESTAMPTZ` UTC
- [Source: ARCHITECTURE-SPINE.md#AD-12] — preço e capacidade pertencem ao setor
- [Source: ARCHITECTURE-SPINE.md#AD-13] — `vendidos` é a única fonte de verdade; nasce zero
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`; transação no
  service, nunca no router
- [Source: ARCHITECTURE-SPINE.md#Convenções] — erro sempre `{"erro": {...}}`; Server Component por
  padrão, `"use client"` só onde há interação que exige o navegador
- [Source: EXPERIENCE.md#Information Architecture] — `Publicar evento → 1 catálogo · 2 data, local e
  setores · 3 escalar portaria`
- [Source: EXPERIENCE.md#medidor] — organizador e portaria veem **números exatos**; é o UX-DR7
- [Source: EXPERIENCE.md#Carregando] — sem spinner
- [Source: EXPERIENCE.md#Key Flows] — o fluxo 3, "Carla publica um show", passo a passo
- [Source: DESIGN.md#Components] — `botao`, `fila-listagem`; raio zero e sombra zero
- [Source: DESIGN.md#Como usar este documento] — grade e espaçamento são provisórios; a ausência de
  card, sombra e raio é duradoura
- [Source: mockups/proto-jornal-noturno.html:545-608] — a tela inteira do organizador
- [Source: mockups/proto-jornal-noturno.html:235-238] — o CSS de `.linha-setor`
- [Source: backend/app/models/evento.py] — as duas tabelas e as quatro constraints da Story 2.3
- [Source: backend/app/schemas/auth.py] — o padrão de schema: `BeforeValidator`, `Field`, o motivo de
  não usar `extra="forbid"`
- [Source: backend/app/services/autenticacao.py:61] — o padrão de service que escreve
- [Source: backend/app/api/organizador.py] — o router a estender, e o docstring da exceção
- [Source: backend/app/core/dependencias.py:81] — `exigir_papel`
- [Source: backend/app/core/erros.py:88] — `ErroDeDominio` e o formato único
- [Source: backend/tests/test_organizador_catalogo.py:25-44] — `_instalar_transporte` e `_entrar`
- [Source: backend/tests/conftest.py:139] — `fabricar_usuario`
- [Source: frontend/src/app/(site)/organizador/publicar/page.tsx] — o passo 1 a estender
- [Source: frontend/src/lib/catalogo.ts] — `ItemDoCatalogo` e o resultado discriminado
- [Source: frontend/src/components/FormularioCadastro.tsx] — o formulário de referência
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: README.md#publicação-exige-atração-do-catálogo] — a decisão que o AC6 passa a aplicar
- [Source: README.md#o-que-não-está-pronto] — onde a janela do AD-7 vai ser registrada
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do
  Igor; decisão é dele

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os três READMEs antes de dar a story por concluída.** As decisões da T8 são a parte que
   o desafio avalia — e **o "por quê" precisa ser o do Igor**, em primeira pessoa. Se faltar o motivo
   de alguma, pergunte a ele em vez de escrever um plausível
3. **Decisão de produto ou de modelagem é do Igor.** As sete desta story estão respondidas e as seis
   suposições estão declaradas. Se aparecer uma oitava — campo a mais, regra a mais, tela a mais —
   **pergunte** em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente — vale para o `npm run dev` desta story
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que os quatro arquivos novos foram rastreados (T7)
8. **O code review é ao fim da epic**, não a cada story. Ao terminar a 2.4, o próximo passo é a Story
   2.5 — mas só quando o Igor mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **Evento com data no passado deve ser recusado?** Hoje é aceito. Recusar exige decidir a margem
   (o dia inteiro? a hora exata?) e um relógio no teste. Vale decidir antes da 2.6, que vai listar
   "o que está em cartaz" e precisa saber o que fazer com um show que já aconteceu.
2. **O evento semeado sai em qual story?** A dívida está no README desde a 2.3 e o impedimento
   técnico acabou. Falta escolher o show, a data, os setores e os preços — e se isso entra na 2.6,
   numa story nova de seed ou na Epic 6.
3. **Um organizador pode publicar duas datas da mesma atração?** Pode, e é de propósito
   (`origem_externa_id` sem `UNIQUE`, decisão da 2.3 — turnê). Vale conferir na tela da 2.6 se duas
   linhas com o mesmo nome e datas diferentes ficam distinguíveis à primeira vista.
4. **Vinte setores por evento é um teto razoável?** É um número escolhido para haver um número. Uma
   constante resolve se você quiser outro.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context) — `bmad-dev-story`.

### Debug Log References

- `uv run python -m pytest tests/test_organizador_eventos.py -q` → 24 passed
- `uv run python -m pytest -q` → **164 passed** (baseline da 2.3 era 140)
- `npx tsc --noEmit` → limpo · `npm run lint` → limpo · `npm run build` → compilado, 8 páginas
- Conferência de tela com `next dev` + `uvicorn` + Compose no ar, e as portas 3000/8000 conferidas
  e liberadas ao fim
- ⚠️ As contas semeadas não existiam no banco de desenvolvimento (só `igor@rockhub.com`); rodei
  `uv run python -m seeds.semear` antes da conferência manual
- ⚠️ `baco` e `metallica` devolvem zero resultados no catálogo hoje (é a limitação já registrada no
  README da raiz, não regressão). A conferência manual usou a vitrine sem termo — `Sticky Fingers -
  Rio de Janeiro`, `ZFIMVHtnMZ17kbx_`

### Completion Notes List

**Backend — três arquivos, nenhuma migração.**

- `schemas/evento.py`: quatro classes. `setores` **sem** `min_length` e com `default_factory=list`,
  para que lista vazia e campo ausente caiam na mesma regra do service (AC4, armadilha 1).
  `origem_externa_id` obrigatório fecha a tensão declarada pela 2.3 (AC6). `data_hora` exige
  `tzinfo` (AC9). Sem `extra="forbid"`, então `organizador_id`, `vendidos`, `id` e `publicado_em`
  no corpo são ignorados em vez de recusados (AC2, AC8).
- Acrescentei um `_limpar_opcional` além do `_limpar_texto` copiado do `schemas/auth.py`: `cidade` e
  `imagem_url` em branco viram `None` em vez de `""`, para a coluna anulável não passar a ter dois
  jeitos de dizer "não tem". Não estava na story; é normalização de fronteira, não campo novo.
- `services/evento.py`: `publicar()` recusa lista vazia e nome duplicado (`casefold()`) **antes** de
  qualquer `add`, monta os `Setor` dentro do `relationship` sem passar `vendidos`, carimba
  `publicado_em` e é quem dá `commit`/`refresh`. Sem `try/except IntegrityError`, pelo motivo escrito
  no docstring.
- `api/organizador.py`: `POST /eventos` com `Depends(exigir_papel(...))` e corpo de uma linha. O
  docstring do módulo agora escreve o **par** — a rota do catálogo sem service, esta com service, e o
  critério entre as duas.

**Frontend — a tela do organizador ganhou o passo 2.**

- `page.tsx` continua Server Component. A escolha vem de `?escolhido=`, o link é montado com
  `URLSearchParams` (armadilha 5), e `escolhido` pode ser `undefined` sem `!` nenhum (armadilha 4 —
  conferido de verdade: `?q=xpto-nao-existe&escolhido=…` responde `200` e o passo 2 some).
- ⚠️ **Corrigido depois que o Igor usou a tela:** o passo 2 nascia abaixo da dobra, e clicar na fila
  parecia não fazer nada. O destino do link passou a terminar em `#passo-2`, com `id="passo-2"` no
  título da seção e `scroll-margin-top` nele. **Não** virou `onClick` com `scrollIntoView`: como a
  escolha é navegação, bastou dizer para onde a navegação vai — a página segue sem uma linha de
  `"use client"` a mais. O `scroll-behavior: smooth` entrou no `html` do `globals.css`, e o bloco de
  `prefers-reduced-motion` que já existia lá o desliga para quem pediu menos movimento. Conferido
  pelo Igor no navegador.
- `FormularioPublicacao.tsx`: primeira ilha `"use client"` do fluxo do organizador. Setores em
  `useState` com chave estável; campos do evento por `FormData`. As duas conversões dentro do
  componente. Confirmação na própria tela, sem `router.push`/`refresh`.
- CSS no `page.module.css` da rota, só com `var(--token)` — nenhum hex novo. Abaixo de 900px a grade
  vira uma coluna **e o rótulo oculto volta a ser visível**, porque a faixa de kickers some.

**Verificado de ponta a ponta, não só por teste:** publiquei pela API através do proxy `/api` com o
cookie de sessão real e conferi as três linhas no Postgres (`evento` + dois `setor` com
`vendidos = 0`). Os dois códigos novos também foram conferidos pelo proxy.

⚠️ **Sobrou um evento de teste no banco de desenvolvimento** (`Sticky Fingers - Rio de Janeiro`),
criado nessa conferência. Ele é da janela do AD-7, ou seja, **sem portaria escalada** — não será
validável na Epic 5. Apagar é `docker compose exec db psql -U rockhub -d rockhub -c "delete from
evento;"` (o `CASCADE` leva os setores junto). Nada disso toca o banco de produção.

⚠️ **AC18 cumprido:** a janela do AD-7 está escrita nos três READMEs — no da raiz como linha própria
em *O que não está pronto*, com a consequência de que evento publicado nela fica sem portaria para
sempre.

**Nenhuma dependência nova.** `pyproject.toml`, `uv.lock` e `package.json` não mudaram. Nenhum
arquivo da lista "não devem ser tocados" foi alterado.

### File List

**Novos**

- `backend/app/schemas/evento.py`
- `backend/app/services/evento.py`
- `backend/tests/test_organizador_eventos.py`
- `frontend/src/components/FormularioPublicacao.tsx`

**Modificados**

- `backend/app/api/organizador.py`
- `backend/README.md`
- `frontend/src/app/(site)/organizador/publicar/page.tsx`
- `frontend/src/app/(site)/organizador/publicar/page.module.css`
- `frontend/src/app/globals.css` — `scroll-behavior: smooth` no `html`, para a âncora do passo 2
- `frontend/README.md`
- `README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-4-publicar-um-evento-com-seus-setores.md`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Story 2.4 implementada. Backend: `schemas/evento.py`, `services/evento.py` e `POST /organizador/eventos` no router que já existia — nenhuma migração, o schema da 2.3 bastou. Frontend: a fila do catálogo virou `<Link>` com a escolha na URL, e nasceu o `FormularioPublicacao`, primeira ilha `"use client"` fora das telas de acesso. Vinte e quatro testes novos; a suíte foi de **140 para 164**, sem regressão. `npm run build`, `npx tsc --noEmit` e `npm run lint` limpos. Conferido de ponta a ponta com os servidores no ar: publiquei pelo proxy `/api` com cookie real e li as três linhas no Postgres. Uma decisão além da story: `cidade` e `imagem_url` em branco viram `None` em vez de `""`, para a coluna anulável não ter dois jeitos de dizer "não tem". Os três READMEs atualizados, incluindo as oito decisões desta story com a alternativa descartada de cada uma e a janela do AD-7 registrada em *O que não está pronto* |
| 2026-08-11 | **Correção depois da conferência do Igor na tela.** O passo 2 aparecia abaixo da dobra: a URL mudava, a fila ficava marcada, e clicar no evento parecia não fazer nada — o formulário só era encontrado por quem rolasse até o rodapé. O destino do `<Link>` passou a terminar em `#passo-2`, o título da seção ganhou `id="passo-2"` e `scroll-margin-top`, e o `html` do `globals.css` ganhou `scroll-behavior: smooth` (desligado pelo bloco de `prefers-reduced-motion` que já existia). A alternativa descartada foi `onClick` com `scrollIntoView`: exigiria transformar a fila do catálogo em componente de cliente e contradiria a decisão central desta story — a escolha é navegação, e navegação sabe para onde vai. `tsc`, `lint` e `build` limpos; conferido pelo Igor no navegador |
| 2026-08-11 | Story 2.4 criada e contextualizada. Sete decisões do Igor incorporadas: a atração escolhida viaja **pela URL** (`?q=…&escolhido=…`), estendendo a decisão já registrada da busca da 2.2 — em vez de estado no cliente, que tiraria a escolha da URL e transformaria a tela inteira em ilha, ou de uma rota `/publicar/[id]`, que exigiria buscar a atração de novo na Discovery ou repassar tudo pela URL; o formulário é **Client Component com `chamarApi`**, a primeira ilha do fluxo do organizador — em vez de Server Action, mecanismo novo que não resolveria o setor dinâmico, ou de linhas fixas sem JavaScript, que mataria o `+ Adicionar setor`; a rota **publica de fato** (`publicado_em` no ato) mesmo com o AD-7 chegando só na 2.5, pelo motivo que o Igor deu — o risco real da janela é baixo (ela dura uma story, numa branch que só ele publica) e fechá-la agora custaria retrabalho garantido na 2.5, que teria que reabrir service, rota e confirmação para mover um carimbo de lugar — em vez de gravar rascunho, que faria a story terminar sem nada visível, e com a janela registrada como dívida datada no AC18; depois de publicar há **confirmação na própria tela** — em vez de `redirect("/")`, que cairia no estado vazio da programação até a 3.1, ou de adiantar "Meus eventos", que é a 2.6; o preço é digitado **em reais e convertido para centavos antes do `POST`** — em vez de aceitar decimal na API, que poria ponto flutuante no contrato contra o AD-11, ou de pedir centavos ao organizador; **data e horário em dois campos**, como o protótipo — em vez de um `datetime-local`, cujo widget varia entre navegadores; e **nome e imagem travados, `local` e `cidade` editáveis**, pelo motivo que o Igor deu: **turnê** — a mesma atração vira várias datas em casas e cidades diferentes, e o catálogo traz a casa de uma delas, não necessariamente a que ele está publicando (mesmo raciocínio que deixou `origem_externa_id` sem `UNIQUE` na 2.3), em vez de tudo editável, que faria o cadastro manual voltar pela porta dos fundos, ou de nada pré-preenchido, que obrigaria a redigitar o que a Ticketmaster já traz certo. Dezoito ACs escritos sobre os cinco blocos do `epics.md`, entre eles o AC5 — nome de setor repetido vira `422 SETOR_DUPLICADO` e não o `500` que a `uq_setor_evento_id_nome` da 2.3 produziria sozinha — e o AC18, que registra por escrito a única invariante da arquitetura que esta story contraria. Seis suposições declaradas (o backend copia o que o corpo manda em vez de reconferir na Discovery, sem validação de data no passado, teto de 20 setores, `_limpar_texto` copiado e não importado, uma linha de setor inicial, conversões dentro do próprio componente) e quatro perguntas registradas para as stories seguintes |
