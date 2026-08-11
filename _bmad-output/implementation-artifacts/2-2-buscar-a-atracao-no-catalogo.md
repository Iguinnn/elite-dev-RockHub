---
baseline_commit: "63f8e8a — feat: Story 2.1 - Cliente da Ticketmaster com a chave protegida (branch Epic-2---Publicação-de-eventos-pelo-organizador)"
---

# Story 2.2: Buscar a atração no catálogo

Status: review

Epic 2 — Publicação de eventos pelo organizador · **A story que dá superfície à 2.1.** A integração
com a Ticketmaster existe, está provada por 20 testes e não é observável por nenhum caminho: não há
rota, não há tela, o `/docs` não sabe que ela existe. Esta story abre os dois de uma vez.

Como organizador,
quero procurar o show que vou publicar,
para não digitar os dados na mão.

Três peças: `GET /organizador/catalogo?q=` protegida por papel, a tela `/organizador/publicar` com o
passo 1 do fluxo de publicação, e o link no masthead que leva até ela. **Nenhum dado é gravado** — a
tabela `evento` é da Story 2.3 e a publicação é da 2.4. Ao fim desta story o organizador busca,
enxerga o resultado e não pode fazer mais nada com ele. Isso é o recorte, não uma falta.

## Acceptance Criteria

1. **Given** que estou autenticado como organizador
   **When** eu chamo `GET /organizador/catalogo?q=metallica`
   **Then** recebo `200` com uma lista de `ItemDoCatalogo` — `id_externo`, `nome`, `atracao`,
   `imagem_url`, `local` e `cidade`
   **And** a rota aparece no `/docs` com o schema de saída, porque o `response_model` está declarado

2. **Given** a mesma rota
   **When** um cliente ou a portaria a chama
   **Then** recebo `403` com código `SEM_PERMISSAO` — só o organizador toca o catálogo (AD-1)
   **And** sem cookie de sessão recebo `401` com `NAO_AUTENTICADO`, **não** `403` — autenticação
   antes de autorização, a garantia que a Story 1.6 fixou
   **And** a proteção é `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))` na assinatura, **nunca** um
   `if` dentro do corpo (AD-9)

3. **Given** `q` ausente, vazio ou só espaços
   **When** eu chamo a rota
   **Then** recebo `200` com os próximos eventos do catálogo no Brasil, ordenados por data
   (`sort=date,asc`), sem o parâmetro `keyword` na chamada à Discovery
   **And** isso não é `422`: campo de busca vazio é o estado inicial da tela, não erro de quem chamou
   **And** é uma decisão tomada **depois** da primeira versão desta story: a Ticketmaster é chamada
   mesmo sem termo, para o organizador ver exemplos do que pode publicar sem precisar digitar nada
   antes (ver Change Log)

4. **Given** a chamada à Discovery
   **When** ela é montada
   **Then** carrega `countryCode=BR` além de `apikey`, `keyword`, `size` e `locale`
   **And** o motivo está escrito no código: sem ele, buscar "metallica" devolve 20 shows americanos e
   nenhum brasileiro dentro do `size=20`
   **And** a limitação entra no README da raiz — show fora do Brasil não aparece nesta busca

5. **Given** que a Ticketmaster está fora do ar
   **When** o organizador busca
   **Then** a rota responde `503` com `{"erro": {"codigo": "CATALOGO_INDISPONIVEL", ...}}` — o
   `ErroDeDominio` que a 2.1 já levanta, traduzido pelo handler que já existe
   **And** **nenhum handler novo é escrito** para isso

6. **Given** a tela `/organizador/publicar`
   **When** eu busco por um termo
   **Then** o termo vai para a URL (`/organizador/publicar?q=baco`), a página é recarregável,
   compartilhável e o botão voltar funciona
   **And** o campo de busca continua mostrando o termo depois da busca
   **And** a tela é Server Component: **nenhum `"use client"` novo** nasce nesta story

7. **Given** a tela
   **When** eu vejo os resultados
   **Then** eles aparecem em **filas separadas por fio, sem card, sem sombra e sem canto arredondado**
   — UX-DR3
   **And** cada fila mostra a origem em versalete monoespaçada: `Ticketmaster · <id_externo>`
   **And** nome do show em serifada, origem e cidade em monoespaçada — UX-DR2
   **And** nenhum dos cinco anti-padrões do UX-DR10 aparece

8. **Given** os dois estados possíveis da tela — depois desta ter deixado de ter um estado "sem
   busca ainda" (revisado após o primeiro corte da story, ver Change Log)
   **When** eu chego nela sem resultado (nem exemplo nem busca acham nada) ou a Ticketmaster está
   fora do ar
   **Then** eles são **distintos**:
   - sem resultado → *"Nenhum show encontrado para essa busca."* (texto literal do
     `EXPERIENCE.md`) quando há termo digitado; *"Não há shows no catálogo agora."* quando é a
     listagem padrão sem termo
   - catálogo indisponível → aviso que diz o que aconteceu **e** o que fazer, escolhido pelo
     `codigo` da API e não pela `mensagem` dela
   **And** a tela **sempre** chama a Ticketmaster ao carregar, com ou sem termo — não existe mais
   convite "busque pelo nome do show" precedendo uma chamada

9. **Given** o catálogo fora do ar
   **When** a página renderiza
   **Then** ela **não quebra** e não cai em fronteira de erro — não existe `error.tsx` neste
   projeto, e uma exceção não capturada num Server Component derruba a tela inteira

10. **Given** o masthead
    **When** eu entro como organizador
    **Then** vejo `Publicar evento` na navegação, e ele leva a `/organizador/publicar`
    **And** entrando como cliente, portaria ou visitante, o link **não existe** — nem escondido por
    CSS
    **And** o masthead continua sem nome de quem está logado, sem data e sem contador
    (`DESIGN.md#Components/masthead`)

11. **Given** a tela, acessada por quem não deveria
    **When** um cliente ou a portaria abre `/organizador/publicar`
    **Then** não vê a tela
    **And** sem sessão nenhuma, sou mandado para o login com o caminho de volta preservado

12. **Given** o bundle do navegador
    **When** eu o inspeciono depois de `npm run build`
    **Then** não há nenhuma URL da Ticketmaster, nenhum `apikey`, e nenhuma variável
    `NEXT_PUBLIC_` de credencial — AD-2 continua valendo com a tela no ar

13. **Given** a suíte do backend
    **When** eu a rodo com a rede desligada
    **Then** ela passa inteira — os testes da rota usam `httpx.MockTransport`, como os da 2.1
    **And** o número final está registrado (eram **107**)

14. **Given** os três READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta a rota, o `countryCode=BR` e a decisão de o router chamar
    a integração sem service
    **And** `frontend/README.md` documenta a tela, o formulário GET, o novo `src/lib/servidor.ts` e
    a estrutura de pastas atualizada
    **And** `README.md` da raiz ganha as decisões desta story **com a alternativa descartada** de
    cada uma

> **De onde vem cada critério.** O `epics.md` traz **três** blocos para a Story 2.2: a rota devolvendo
> nome, imagem, local e identificador de origem; o `403` para quem não é organizador; e as filas com
> fio mostrando `Ticketmaster · id`. Eles viraram os ACs **1, 2 e 7**.
>
> **AC4** é a decisão do Igor sobre filtro de país, que estava aberta desde a 2.1. **AC6** é a decisão
> dele sobre a mecânica da busca. **AC3, AC5 e AC9** existem porque a 2.1 entregou três
> comportamentos que esta story precisa **não estragar**: lista vazia distinta de indisponível, erro
> traduzido por handler que já existe, e nada escapando da fronteira. **AC8** é o UX-DR8 e o
> `EXPERIENCE.md#Vazio`. **AC10 e AC11** são a consequência de a tela existir: sem link ela é
> inalcançável, sem guarda ela é pública. **AC12** é o AD-2 conferido de novo, agora que existe tela.

## Tasks / Subtasks

- [x] **T1. `countryCode=BR` na chamada à Discovery** (AC: 4)
  - [x] `app/integrations/ticketmaster.py`: constante `_PAIS = "BR"` no topo, junto de `_URL_EVENTOS`,
        e `"countryCode": _PAIS` no dicionário de `params`
  - [x] Comentário de duas linhas com o motivo — o mesmo raciocínio do `locale="*"` que já está lá:
        parâmetro que muda o que a busca **acha**, não como ela é transportada
  - [x] Um teste novo em `tests/test_ticketmaster.py` afirmando o parâmetro, ao lado dos que já leem
        `apikey` e `keyword`
  - [x] ✅ Os testes existentes **não quebram**: eles leem `capturado["url"].params["apikey"]` item a
        item, nunca o conjunto inteiro de parâmetros

- [x] **T2. `app/api/organizador.py` — a rota** (AC: 1, 2, 3, 5)
  - [x] Arquivo novo. `router = APIRouter(prefix="/organizador", tags=["organizador"])`
  - [x] `@router.get("/catalogo", response_model=list[ItemDoCatalogo])`
  - [x] Assinatura: `q: str = Query("", max_length=120)` e
        `_: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`
  - [x] Corpo: `return ticketmaster.buscar_eventos(q)`. **Uma linha** — ver *A camada que não existe*
  - [x] `max_length=120` não é enfeite: `q` vai inteiro para a URL da Ticketmaster. Mesmo raciocínio
        dos tetos de `LoginEntrada` (Story 1.4)
  - [x] O parâmetro do usuário se chama `_` de propósito: a rota não usa o objeto, só exige o papel.
        Nomeá-lo `usuario` sem usá-lo é ruído que o linter reclama
  - [x] Docstring explicando **por que não há service** — é a exceção ao Design Paradigm, e ela
        precisa estar escrita onde alguém a encontra
  - [x] `app/main.py`: `from app.api import auth, organizador, saude` e
        `app.include_router(organizador.router)`, na mesma ordem alfabética dos outros dois

- [x] **T3. `src/lib/servidor.ts` — extrair o caminho do servidor** (AC: 6, 9)
  - [x] Arquivo novo com o que hoje está dentro do `sessao.ts` e passa a ter dois consumidores:
        `API_URL`, `NOME_DO_COOKIE`, o aviso de `API_URL` ausente em produção, e
        `cabecalhoDeSessao(): Promise<{ Cookie: string } | null>`
  - [x] `src/lib/sessao.ts`: importa os quatro e apaga as cópias locais. **O corpo de
        `obterUsuarioDaSessao` não muda** — nem o `cache()`, nem o curto-circuito sem cookie, nem o
        `console.error` do `catch`, que foram conquistados no code review da Epic 1
  - [x] ⚠️ Esta é a única refatoração da story, e ela mexe no caminho da sessão (AD-15). Confira
        **na tela** que login, `/conta` e masthead continuam funcionando antes de seguir

- [x] **T4. `src/lib/catalogo.ts` — a busca do lado do servidor** (AC: 5, 8, 9)
  - [x] `export type ItemDoCatalogo` espelhando os seis campos do schema do backend
  - [x] `buscarNoCatalogo(termo: string): Promise<ResultadoDaBusca>`, com
        `ResultadoDaBusca = { estado: "ok"; itens: ItemDoCatalogo[] } | { estado: "indisponivel" }`
  - [x] **Nunca levanta.** `try/catch` em volta do `fetch`, `!resposta.ok` também vira
        `indisponivel`, e o `catch` registra no log antes de devolver — mesma disciplina do
        `sessao.ts` (AC9)
  - [x] `encodeURIComponent(termo)` ao montar a query — ver *Cinco armadilhas*
  - [x] `cache: "no-store"`, e o cabeçalho de sessão repassado à mão

- [x] **T5. A tela `/organizador/publicar`** (AC: 6, 7, 8, 11)
  - [x] `src/app/(site)/organizador/publicar/page.tsx` + `page.module.css`
  - [x] Guarda no topo: sem sessão → `redirect("/login?voltar=%2Forganizador%2Fpublicar")`; papel
        diferente de `ORGANIZADOR` → `redirect("/")`
  - [x] `const parametros = await searchParams` — **`searchParams` é Promise no Next 16**; o
        precedente está em `(entrada)/login/page.tsx`
  - [x] ⚠️ `PageProps<"/organizador/publicar">` **não existe até o Next gerar os tipos da rota**. Crie
        o `page.tsx`, rode `npx next typegen` (ou deixe o `next dev` rodando) e só então o
        `tsc --noEmit` passa. Sem isso o erro é "Type '\"/organizador/publicar\"' does not satisfy
        the constraint", que parece rota escrita errada e é só tipo não gerado
  - [x] `q` pode chegar como `string[]` (`?q=a&q=b`): trate como o `caminho.ts` trata o `voltar`
  - [x] `<form method="get">` com `<input name="q" defaultValue={termo}>` e o `Botao` existente
  - [x] Título do passo: `1 · Escolha no catálogo`, com kicker `Ticketmaster Discovery` —
        `proto-jornal-noturno.html:555`
  - [x] Filas: grade `70px | 1fr | auto`, `border-bottom: 1px solid var(--fio)`, sem caixa
  - [x] Os três estados do AC8, cada um com seu texto
  - [x] Nenhum `"use client"` neste arquivo nem em nada que ele crie

- [x] **T6. O link no masthead** (AC: 10)
  - [x] `src/components/Masthead.tsx`: `{usuario?.papel === "ORGANIZADOR" && <NavLink
        href="/organizador/publicar">Publicar evento</NavLink>}`
  - [x] `Meus eventos` **não entra** — a tela é da Story 2.6, e link que cai no 404 não fica no
        repositório (precedente da 1.4, escrito no próprio comentário do `Masthead.tsx`)
  - [x] O comentário do componente ganha uma linha: agora ele decide por papel, não só por
        autenticado ou não

- [x] **T7. Testes do backend** (AC: 1, 2, 3, 5, 13)
  - [x] `tests/test_organizador_catalogo.py`, novo. Precisa do Compose no ar (faz login de verdade)
  - [x] Fixture local instalando `MockTransport` em `ticketmaster._criar_cliente`, e outra fixando
        `ticketmaster.obter_settings` — copie o padrão de `tests/test_ticketmaster.py:26-44`
  - [x] `_entrar(cliente, usuario)` é o helper de `tests/test_autorizacao.py:73` — mesmo jeito
  - [x] Um teste novo em `tests/test_ticketmaster.py` para o `countryCode` (T1)
  - [x] Rodar `uv run pytest` inteiro e registrar o número final

- [x] **T8. Verificação de fronteira** (AC: 12)
  - [x] `npm run build` no `frontend/`, e busca por `ticketmaster`, `apikey` e `discovery` em
        `frontend/.next/static/` → **zero**
  - [x] Busca por `NEXT_PUBLIC` em `frontend/src/` → zero
  - [x] `npx tsc --noEmit` e `npm run lint` limpos
  - [x] ⚠️ Confira que `page.tsx`, `page.module.css`, `servidor.ts` e `catalogo.ts` **estão
        rastreados** pelo git antes de dar a story por pronta. Pasta nova + `.gitignore` nascido de
        template Python é exatamente o defeito da Story 1.9, e o primeiro clone limpo é o build da
        Vercel — que acontece depois do merge

- [x] **T9. Os três READMEs** (AC: 14) — obrigatório, regra do projeto
  - [x] `backend/README.md`: a rota na seção **Catálogo da Ticketmaster** (que já existe, criada na
        2.1), o `countryCode=BR`, a exceção ao paradigma em *O paradigma: `routers → services →
        models`*, `api/organizador.py` na *Estrutura*, número de testes, entrada da 2.2 no *Histórico
        desta camada*
  - [x] `frontend/README.md`: `src/lib/servidor.ts` e `catalogo.ts` em *Falar com a API* e na
        *Estrutura*; seção nova sobre a tela do organizador; o formulário GET e por que não é
        `"use client"`
  - [x] `README.md` da raiz: quatro decisões com a alternativa descartada (ver *Decisões que o Igor
        tomou*), mais a limitação do `countryCode=BR` em *O que não está pronto*
  - [x] Primeira pessoa em tudo

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T9).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Quem chama a integração | **O router, direto.** Não existe `services/catalogo.py` | *Service fino*: manteria a seta `routers → services` literal e uniforme, ao custo de um módulo cujo corpo inteiro é `return ticketmaster.buscar_eventos(termo)` — a "camada de repasse" que a própria espinha nomeia e descarta com estas palavras: *"só adicionaria código sem separar nada de novo neste tamanho de projeto"*. *Service com trabalho real*, subindo o `strip`, o limite e o filtro de país para ele: não é repasse e deixaria o diagrama verdadeiro, mas reabriria `ticketmaster.py` — entregue e revisado ontem — e moveria dois ACs da 2.1 de arquivo, por uma story que não precisa disso |
| Mecânica da busca | **`<form method="get">` + Server Component** | *Client Component com `chamarApi`*: reusaria `lib/api.ts`, `AvisoDeErro` e o tratamento por `codigo` que já existem, e buscaria sem recarregar. Caiu por três coisas: a busca não ficaria na URL (nada de recarregar, compartilhar ou voltar), a tela inteira viraria ilha de cliente contra a convenção *"Server Component por padrão"*, e quando a 2.4 acrescentar os passos 2 e 3 o estado do resultado passaria a viver em dois lugares. O `"sem spinner: a estrutura aparece e o conteúdo preenche"` do `EXPERIENCE.md` também é natural no servidor e artificial no cliente |
| Onde mora a tela | **`/organizador/publicar`**, dentro da casca `(site)` | *`/publicar`*: mais curto, e o papel estaria implícito — mas a 2.6 viraria `/meus-eventos`, perto demais de `/meus-ingressos` da Epic 4. *Grupo de rotas `(organizador)` com layout próprio*: daria casca separada, e o `EXPERIENCE.md` diz o contrário — o organizador usa *"a mesma casca do cliente, com navegação própria"*. Um terceiro layout para manter, sem nada que o justifique |
| Filtro de país | **`countryCode=BR` fixo** | *Sem filtro*: é literalmente o que o `epics.md` especifica e não esconderia resultado nenhum — mas buscar "metallica" devolveria 20 shows americanos e nenhum brasileiro dentro do `size=20`, e a tela pareceria quebrada para quem estiver avaliando. *Filtro visível, marcado por padrão*: honesto com os dois lados, ao custo de mais um parâmetro na rota, mais um campo na tela e mais dois testes — numa story dimensionada como um commit. A limitação assumida vai para o README |

**Três suposições declaradas, não decisões suas** — uma linha para trocar se discordar:

- **Papel errado é `redirect("/")`, não 404 nem tela de recusa.** Cliente que digitar
  `/organizador/publicar` vai para a programação. A alternativa é `notFound()`, que reusaria o
  `not-found.tsx` existente e não revelaria que a rota existe — mas mandar alguém logado para o 404
  parece defeito, e a rota não é segredo (a API responde `403`, que é público por natureza)
- **A imagem é `<img>`, não `next/image`.** A Discovery serve de mais de um host (`s1.ticketm.net`,
  `media.ticketmaster.com`), e `next/image` exige `remotePatterns` declarado por host — errar um
  produz erro em tempo de execução, e um curinga permissivo faria a Vercel otimizar e cobrar por
  cada miniatura de terceiro. `<img loading="lazy">` com dimensão fixa no CSS resolve. O
  `eslint-disable-next-line @next/next/no-img-element` precisa vir **com o motivo escrito**
- **A fila do catálogo fica dentro da `page.tsx`, não vira componente.** Tem um consumidor só. A
  convenção do projeto é extrair no segundo — foi assim com `Campo` e `Botao`, e está registrado no
  README da raiz. Quando a 2.4 precisar dela para o passo de confirmação, ela nasce ali

### A camada que não existe

Esta é a decisão mais visível da story para quem revisa código, e ela precisa estar escrita no
arquivo, não só aqui.

A espinha diz `routers → services → models`, e o diagrama liga `services → integrations`. Um router
importando `app.integrations` pula uma camada. O motivo de fazer isso mesmo assim:

```python
# o service que não vai existir
def buscar(termo: str) -> list[ItemDoCatalogo]:
    return ticketmaster.buscar_eventos(termo)
```

`buscar_eventos` **já faz tudo** que um service faria: `.strip()` no termo, curto-circuito de termo
vazio antes de qualquer I/O, limite, conversão para o schema do projeto e tradução de toda falha em
`ErroDeDominio`. Não sobra regra de negócio para lugar nenhum. E a espinha rejeita exatamente isso,
em *Design Paradigm*: *"não existe camada de repositório: interpor uma camada de repasse só
adicionaria código sem separar nada de novo neste tamanho de projeto"*.

**O que isso custa, e é honesto reconhecer:** quando a Story 2.4 criar `services/evento.py`, o
catálogo será o único caminho da API sem service. É uma exceção, e exceção não escrita vira
inconsistência que ninguém sabe explicar. Daí a docstring da rota e a entrada no README.

⚠️ **A exceção vale para o catálogo, e só para ele.** A Story 2.4 grava no banco: ela **tem** service,
sem discussão. O critério que separa os dois: existe transação ou invariante? Então existe service.

### Cinco armadilhas desta story

**1. O `fetch` do servidor não herda o cookie.** É o erro que faz a tela renderizar como se ninguém
estivesse logado, com sessão perfeitamente válida, e sem nada no console. O `sessao.ts` já resolve
isso desde a 1.9 e o `catalogo.ts` precisa resolver de novo — daí a T3 extrair o helper em vez de
cada arquivo lembrar por conta própria.

```ts
const cabecalho = await cabecalhoDeSessao();   // { Cookie: "rockhub_sessao=…" } | null
```

Sem ele o backend responde `401`, o `!resposta.ok` vira `indisponivel`, e a tela diz "o catálogo não
respondeu" quando o catálogo respondeu perfeitamente. **O sintoma aponta para o lugar errado** — é o
que torna esta a armadilha mais cara da lista.

**2. `encodeURIComponent` no termo.** Um organizador buscando `AC/DC & Guns` monta:

```
/organizador/catalogo?q=AC/DC & Guns
                            ↑ o & encerra o parâmetro
```

O backend recebe `q=AC/DC ` e um parâmetro `Guns` que ninguém pediu. Com `#`, pior: tudo depois vira
fragmento e não sai da máquina. Uma linha resolve, e o teste que a prova é buscar por um termo com
`&`.

**3. `searchParams` é Promise no Next 16.** Sem `await`, `q` é `undefined`, cai calado no estado
inicial, e o sintoma é *"a busca não faz nada"*. O precedente está em
`(entrada)/login/page.tsx:21`, com o mesmo ⚠️ no comentário.

**4. Server Component que levanta derruba a tela inteira.** Não existe `error.tsx` neste projeto:
uma exceção não capturada num Server Component sobe até a fronteira de erro padrão do Next, e a
página inteira some. É por isso que `buscarNoCatalogo` devolve um resultado discriminado em vez de
levantar — o `503` do catálogo é um estado da tela, não uma falha da aplicação.

**5. Os dois estados vazios não são o mesmo estado.** ⚠️ **Revisado após o primeiro corte da
story**: originalmente havia um terceiro estado, "ninguém buscou ainda", que não chamava a
Ticketmaster. O Igor pediu, depois de testar, que a tela sempre mostre exemplos do catálogo ao
carregar — então esse terceiro estado deixou de existir, e a tela chama a Discovery em toda
renderização, com ou sem termo. Os dois que sobram continuam fáceis de achatar, porque
`itens.length === 0` é verdadeiro nos dois:

| Situação | O que a tela diz |
|---|---|
| Sem resultado, sem termo (listagem padrão vazia) | *"Não há shows no catálogo agora."* |
| Buscou um termo, não achou | *"Nenhum show encontrado para essa busca."* — literal do `EXPERIENCE.md#Vazio` |
| Catálogo fora do ar (com ou sem termo) | *"O catálogo da Ticketmaster não respondeu. Tente de novo em instantes."* |

O terceiro é escolhido pelo **estado** que o `catalogo.ts` devolve, não pela `mensagem` que a API
mandou — convenção da Story 1.4, registrada no README da raiz: *"a tela escolhe o texto pelo
`codigo`, nunca pela `mensagem` vinda do servidor"*.

E nenhum dos três ganha ilustração ou botão grande de chamada: *"kicker em versalete, frase, fim"*.

### O formulário GET, e por que ele basta

```tsx
<form method="get">
  <input name="q" defaultValue={termo} />
  <Botao type="submit">Buscar</Botao>
</form>
```

Sem `action`: o formulário envia para a própria URL. O navegador monta `?q=…` sozinho, o Next trata
como navegação normal, a página re-renderiza no servidor com o termo novo. Zero JavaScript, zero
estado, zero `"use client"`.

**`defaultValue` e não `value`.** Com `value` sem `onChange` o campo fica somente-leitura e o React
avisa no console. `defaultValue` é o certo para campo não controlado — que é o que ele é aqui: o
servidor manda o valor inicial, o navegador cuida do resto.

**O `<label>` é obrigatório**, não `placeholder` — UX-DR9, e o `Campo` existente já faz isso. Reuse-o
se a grade da barra de busca permitir; se não, o `<label htmlFor>` é escrito à mão do mesmo jeito.

### A tela, em texto

Referência: `proto-jornal-noturno.html:545-570`. O protótipo é **ponto de partida, não gesso** — o
`DESIGN.md#Como usar este documento` é explícito sobre isso, e grade e espaçamento estão na lista do
que você ajusta livremente.

```
┌ masthead (Início · Publicar evento · Minha conta) ────────────────┐
│                                                                    │
│  1 · Escolha no catálogo            TICKETMASTER DISCOVERY (kicker)│
│  ──────────────────────────────────────────────────────────────    │
│  [ Buscar no catálogo          ]  [ BUSCAR ]                       │
│  ══════════════════════════════════════════════════════════════    │
│  ▓▓▓▓  Baco Exu do Blues — Bluesman Vivo                           │
│  ▓▓▓▓  TICKETMASTER · G5VYZ9A1KD · SÃO PAULO                       │
│  ──────────────────────────────────────────────────────────────    │
│  ▓▓▓▓  Baco Exu do Blues — Festival Turá                           │
│  ▓▓▓▓  TICKETMASTER · K8BQ2W7LP · RIO DE JANEIRO                   │
│  ──────────────────────────────────────────────────────────────    │
└────────────────────────────────────────────────────────────────────┘
```

- Miniatura quadrada de 70px. Sem `imagem_url`, o bloco vazio em `breu2` ocupa o mesmo espaço — a
  grade não pode dançar entre uma fila e outra
- Nome do show em **serifada 20px**; origem e cidade em **mono 10px, versalete, `0.13em`,
  `fumaca`** (`.cat-item h4` e `.cat-item .fonte` do protótipo)
- Fio de 1px embaixo de cada fila. **Sem caixa, sem sombra, sem raio** — UX-DR3
- `local` e `cidade` podem ser `None`: monte a linha de origem juntando só o que existe, com `·`
  entre as partes. `Ticketmaster · G5VYZ9A1KD ·  · ` com buracos é o defeito visível de esquecer isto
- **Nada é clicável nesta story.** Selecionar a atração é a Story 2.4. O protótipo mostra o estado
  `Selecionado` porque desenha o fluxo inteiro; aqui ele não existe ainda

### O que já existe e esta story reusa — não reescreva nada disto

| O que | Onde | Como usar aqui |
|---|---|---|
| `buscar_eventos` | `app/integrations/ticketmaster.py:120` | A rota chama e devolve. Termo vazio, limite, conversão e erro **já estão resolvidos** |
| `ItemDoCatalogo` | `app/schemas/catalogo.py` | O `response_model`. **Não crie schema de saída novo** |
| `exigir_papel` | `app/core/dependencias.py:81` | `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`. Já garante `401` antes de `403` |
| Handler de `ErroDeDominio` | `app/main.py:64` | Já traduz o `CATALOGO_INDISPONIVEL` em `503` no formato `{"erro": {...}}`. **Nenhum handler novo** |
| Padrão de router | `app/api/auth.py:20` | `APIRouter(prefix=…, tags=[…])`, docstring explicando o que o módulo resolve |
| `obterUsuarioDaSessao` | `frontend/src/lib/sessao.ts:57` | A guarda da página, e o papel para o masthead. `cache()` já deduplica na mesma renderização |
| Guarda de página | `(site)/conta/page.tsx:25-30` | O padrão exato: ler a sessão, `if (!usuario) redirect(...)`. **Não crie `middleware`** — o motivo está no docstring de lá |
| `NavLink` | `frontend/src/components/NavLink.tsx` | Já marca o item ativo e põe `aria-current`. O masthead só acrescenta um |
| `Botao`, `Campo` | `frontend/src/components/` | O primário âmbar e o par rótulo+entrada. Não recrie |
| Tokens do sistema | `frontend/src/app/globals.css` | `var(--fio)`, `var(--breu2)`, `var(--fumaca)`, `var(--serif)`, `var(--mono)`. **Nenhum hex novo em `*.module.css`** |
| `.kicker` | `globals.css:86` | Classe global. Não redeclare no módulo |
| Padrão de teste com `MockTransport` | `tests/test_ticketmaster.py:36-44` | `_instalar_transporte`, copiado para o arquivo novo |
| `_entrar` | `tests/test_autorizacao.py:73` | Login de verdade no `TestClient` — o cookie do teste é o do navegador |

**Não devem ser tocados, e não devem quebrar:** `backend/migrations/`, `backend/seeds/`,
`backend/app/models/`, `backend/app/services/`, `backend/app/core/config.py`, `docker-compose.yml`,
`frontend/next.config.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/caminho.ts`, e as telas de
`(entrada)/`.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    api/
      organizador.py           # NOVO — GET /organizador/catalogo
    integrations/
      ticketmaster.py          # +countryCode=BR
    main.py                    # +include_router(organizador.router)
  tests/
    test_organizador_catalogo.py  # NOVO
    test_ticketmaster.py       # +1 teste (countryCode)
  README.md
frontend/
  src/
    app/(site)/organizador/publicar/
      page.tsx                 # NOVO — a tela, Server Component
      page.module.css          # NOVO
    components/
      Masthead.tsx             # +link para organizador
    lib/
      servidor.ts              # NOVO — API_URL, cookie, aviso de produção
      sessao.ts                # passa a importar de servidor.ts
      catalogo.ts              # NOVO — buscarNoCatalogo()
  README.md
README.md                      # 4 decisões + limitação do countryCode
```

Não existe, e não deve passar a existir: `app/services/catalogo.py` (ver *A camada que não existe*),
`middleware.ts`, `error.tsx`, migração nova, componente de fila extraído, `"use client"` novo.

[Fonte: ARCHITECTURE-SPINE.md#Árvore · frontend/README.md#Estrutura]

### Testing

**Backend, `tests/test_organizador_catalogo.py`** — precisa do Compose no ar (os testes fazem login
de verdade), e **zero rede**: a Ticketmaster é `MockTransport`, como na 2.1.

| O que o teste prova | AC |
|---|---|
| Organizador autenticado recebe `200` e a lista convertida, com os seis campos | 1 |
| Cliente recebe `403` com `SEM_PERMISSAO` | 2 |
| Portaria recebe `403` — a recusa não é só contra o cliente | 2 |
| Sem cookie recebe `401` com `NAO_AUTENTICADO`, **não** `403` | 2 |
| `?q=` ausente → `200`, o transporte **é chamado**, sem `keyword` nos params e com `sort=date,asc` | 3 |
| `?q=   ` → idem (o `.strip()` esvazia o termo, mas a chamada acontece do mesmo jeito) | 3 |
| Termo com `&` chega inteiro na `keyword` da Discovery | 6 |
| Ticketmaster fora do ar → `503` com `CATALOGO_INDISPONIVEL` no formato `{"erro": {...}}` | 5 |
| Busca sem resultado → `200` com `[]`, e **não** `503` | 5 |
| `q` acima de 120 caracteres → `422` | 2 |

**Em `tests/test_ticketmaster.py`:** um teste novo afirmando `countryCode == "BR"` na URL montada.

⚠️ **Três coisas que dão trabalho se passarem batido:**

1. **A rota precisa estar registrada no `app` real.** As fixtures montam o `app` de `app.main`; um
   `include_router` esquecido faz **todos** os testes do arquivo novo responderem `404`, o que parece
   erro de caminho e é erro de registro
2. **O `TestClient` guarda cookie entre chamadas** (⚠️ já anotado no `conftest.py:130`). O teste do
   `401` precisa rodar antes de qualquer login no mesmo cliente, ou chamar `cliente.cookies.clear()`
3. **`_instalar_transporte` substitui `ticketmaster._criar_cliente`, não o do router.** A rota chama
   `ticketmaster.buscar_eventos`, que chama `_criar_cliente` **do próprio módulo** — o monkeypatch
   precisa apontar para `app.integrations.ticketmaster`, exatamente como na 2.1. Apontar para o
   módulo da rota não substitui nada e o teste tenta ir à rede de verdade

**Frontend: não há teste automatizado**, e é corte consciente registrado na espinha
(`ARCHITECTURE-SPINE.md#Adiado`). A verificação é manual, e são cinco caminhos:

1. Entrar como `organizador@rockhub.dev` → o link `Publicar evento` aparece no masthead
2. Entrar como `cliente@rockhub.dev` → o link **não** aparece; digitar `/organizador/publicar` na
   barra manda para a raiz
3. Sem sessão, abrir `/organizador/publicar` → cai no login, e entrar leva de volta para a tela
4. Buscar `baco` → filas com fio, origem em versalete, nenhum card
5. Derrubar a busca de propósito (`TICKETMASTER_API_KEY` errada no `.env`) → a tela mostra o aviso e
   **não** quebra

### Inteligência da Story 2.1

**O que a 2.1 deixou pronto e esta story não deve refazer:**

- ⚠️ **Termo vazio deixou de significar "sem requisição" — revisado depois do primeiro corte.**
  Na versão original da story, `buscar_eventos` fazia `.strip()` e devolvia `[]` antes de qualquer
  I/O quando o termo vinha vazio. Isso foi revisto: agora `buscar_eventos` sempre chama a
  Discovery — sem `keyword` quando o termo é vazio, com `sort=date,asc` para listar os próximos
  eventos como exemplo do que dá para publicar. A rota **não** precisa de lógica nova; a mudança
  fica inteira dentro de `buscar_eventos`
- **Lista vazia e catálogo indisponível já são distintos.** `[]` para busca sem resultado,
  `ErroDeDominio` para falha. O AC5 desta story só confere que a rota preserva a distinção
- **O `503` já tem tradutor.** O handler de `ErroDeDominio` em `app/main.py:64` devolve
  `{"erro": {"codigo": "CATALOGO_INDISPONIVEL", ...}}` com o status certo. Escrever um `try/except`
  na rota desfaria isso
- **A chave já é redigida em todo caminho de log.** Esta story não acrescenta nenhum `logger` que
  toque a URL da Ticketmaster — e não deve. Se precisar registrar algo no `catalogo.ts` do frontend,
  lembre que ali nem existe chave: o frontend fala com a **nossa** API
- **`app/api/organizador.py` não existe ainda de propósito.** A 2.1 registrou isso em *Escopo — o
  que NÃO fazer aqui*: "Aproveito e crio a rota, é uma linha". Esta é a story em que ela nasce

**Duas regressões que a 2.1 encontrou e valem de lição:** o `test_cookie_e_secure_apenas_em_producao`
quebrou por uma mudança em `Settings` que a story não previu, e só apareceu ao rodar a **suíte
inteira**. Rodar só `pytest tests/test_organizador_catalogo.py` não é verificação suficiente.

**Do estado do repositório:** branch `Epic-2---Publicação-de-eventos-pelo-organizador`, com a 2.1
commitada em `63f8e8a`. **107 testes** passando. `TICKETMASTER_API_KEY` já definida no painel da
Railway (confirmado pelo Igor em 2026-08-11) — e a partir da 2.1 ela é **obrigatória em produção**,
então o merge desta epic não sobe sem ela.

[Fonte: _bmad-output/implementation-artifacts/2-1-*.md · sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| FastAPI | 0.141.1 | `APIRouter`, `Query`, `Depends`, `response_model` |
| Next.js | **16.3.0** | `searchParams` é **Promise**; `PageProps<"/rota">` é global, gerado por `next dev`/`next build`/`next typegen` — não se importa |
| React | 19 | Server Components por padrão |
| httpx | 0.28.1 | Só nos testes, via `MockTransport` |
| Ticketmaster Discovery | v2 | `countryCode` é parâmetro documentado de `/events.json` |

⚠️ **Leia `frontend/AGENTS.md` antes de escrever TSX.** Esta versão do Next tem quebras em relação ao
que um modelo tem memorizado; a documentação da versão instalada está em
`frontend/node_modules/next/dist/docs/`. A de `searchParams` e `PageProps` é
`01-app/03-api-reference/03-file-conventions/page.md`.

[Fonte: node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/page.md ·
developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2]

### Escopo — o que NÃO fazer aqui

Selecionar a atração (2.4) · tabela `evento` ou `setor` (2.3) · formulário de data, local e setores
(2.4) · escalar portaria (2.5) · "Meus eventos" (2.6) · paginação · cache · `"use client"` ·
`error.tsx` · `middleware.ts` · `services/catalogo.py` · `next/image` · tocar `app/core/config.py`.

Cinco tentações concretas:

- **"Já ponho o `onClick` para selecionar, é uma linha."** É o primeiro `"use client"` da tela e um
  AC da Story 2.4. Um commit por story é o que está sendo avaliado
- **"Crio o service para não furar a arquitetura."** A decisão está tomada e o motivo está escrito
  em *A camada que não existe*. Se discordar, fale com o Igor — não escreva o arquivo
- **"Busco enquanto digito, fica melhor."** Cada tecla é uma chamada à Discovery, contra uma cota de
  5 000 por dia, e exigiria cliente, `useState` e *debounce*. O botão Buscar é uma chamada por busca
- **"Uso `next/image` que é o idiomático."** É, e exige `remotePatterns` por host da Ticketmaster —
  errar um deles é erro em tempo de execução, na tela do organizador
- **"Ponho `Meus eventos` no masthead junto, já que estou aqui."** A tela é da 2.6, e link que cai no
  404 não fica no repositório — o próprio `Masthead.tsx` diz isso num comentário

### Project Structure Notes

Esta é a primeira story do projeto com **uma rota de papel específico**. Até aqui a API tinha
`/saude` (pública) e `/auth/*` (aberta a todos os papéis por natureza); a dependência `exigir_papel`
existe desde a 1.6 e só era exercitada por uma rota de mentira que vive dentro de `tests/`. A partir
daqui ela protege algo real — e `app/api/organizador.py` é o primeiro dos três routers por papel que
a árvore da arquitetura prevê (`publico`, `cliente`, `organizador`, `portaria`).

No frontend, é a primeira tela **restrita por papel**, e não só por sessão. A `/conta` pergunta "tem
alguém?"; esta pergunta "quem?". As duas guardas moram na página, pelo mesmo motivo já escrito no
`conta/page.tsx`: um `middleware` só enxerga que existe cookie, não que ele vale, e validar o JWT ali
exigiria o segredo no ambiente do frontend — o contrário do AD-2.

É também a primeira vez que um Server Component chama a API para buscar **dados de domínio**, e não
sessão. Daí a T3: o que era detalhe interno do `sessao.ts` (URL absoluta, cookie repassado à mão,
aviso de `API_URL` ausente) passa a ter dois consumidores e vira `servidor.ts`. As Epics 3 a 5 terão
mais — cada tela de listagem é outro caso.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2] — os três blocos de AC originais:
  lista com nome/imagem/local/identificador, `403` para os outros papéis, filas com fio e a origem
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR2, FR8 e o objetivo da epic
- [Source: ARCHITECTURE-SPINE.md#AD-1] — Ticketmaster **só** em endpoint do organizador; é este AC2
- [Source: ARCHITECTURE-SPINE.md#AD-2] — a chave só no ambiente do backend; é o AC12
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel declarado na assinatura, nunca `if` no corpo
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models` e a rejeição da
  camada de repasse; a tensão entre as duas frases é o assunto de *A camada que não existe*
- [Source: ARCHITECTURE-SPINE.md#Convenções] — erro sempre `{"erro": {"codigo", "mensagem"}}`; Server
  Component por padrão, `"use client"` só onde há interação que exige o navegador
- [Source: ARCHITECTURE-SPINE.md#Adiado] — teste automatizado de frontend fora de escopo
- [Source: EXPERIENCE.md#Information Architecture] — organizador com "a mesma casca do cliente, com
  navegação própria"; `Publicar evento → 1 catálogo · 2 data, local e setores · 3 escalar portaria`
- [Source: EXPERIENCE.md#Vazio] — *"Nenhum show encontrado para essa busca."*, e a regra de estado
  vazio sem ilustração e sem botão grande
- [Source: EXPERIENCE.md#Carregando] — sem spinner; a estrutura aparece e o conteúdo preenche
- [Source: DESIGN.md#Components] — `fila-listagem`, `botao`, `masthead` (sem linha de contexto)
- [Source: DESIGN.md#Como usar este documento] — grade e espaçamento são provisórios; a ausência de
  card, sombra e raio é duradoura
- [Source: mockups/proto-jornal-noturno.html:545-570 e :227-234] — a tela do organizador e o CSS de
  `.catalogo`, `.cat-item`, `.cat-thumb`, `.cat-item .fonte`
- [Source: backend/app/integrations/ticketmaster.py:120] — `buscar_eventos`, e o `params` que ganha
  o `countryCode`
- [Source: backend/app/core/dependencias.py:81] — `exigir_papel`, e por que ele usa `Depends`
- [Source: backend/app/api/auth.py:20] — o padrão de router deste projeto
- [Source: backend/app/main.py:64] — o handler que traduz `ErroDeDominio`
- [Source: backend/tests/test_autorizacao.py:73] — `_entrar`, o login de verdade no `TestClient`
- [Source: backend/tests/test_ticketmaster.py:36] — `_instalar_transporte`
- [Source: backend/tests/conftest.py:130] — ⚠️ o `TestClient` guarda cookie entre chamadas
- [Source: frontend/src/lib/sessao.ts] — as cinco decisões do caminho do servidor, das quais três
  viram `servidor.ts`
- [Source: frontend/src/app/(site)/conta/page.tsx:25] — a guarda de página, e por que não `middleware`
- [Source: frontend/src/app/(entrada)/login/page.tsx:20] — ⚠️ `searchParams` é Promise no Next 16
- [Source: frontend/README.md#Falar com a API] — a tela escolhe o texto pelo `codigo`, nunca pela
  `mensagem`
- [Source: frontend/AGENTS.md] — leia a documentação da versão instalada antes de escrever TSX
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Atualize os três READMEs antes de dar a story por concluída.** As quatro entradas de decisão da
   T9 são a parte que o desafio avalia
3. **Decisão de produto é do Igor.** As quatro desta story estão respondidas e as três suposições
   estão declaradas. Se aparecer uma quinta, pergunte em vez de escolher
4. **Docker Desktop precisa estar no ar** para `uv run pytest`: os testes da rota fazem login de
   verdade contra o Postgres
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente — vale para o `npm run dev` desta story
6. **Nenhuma dependência nova.** Nem no `pyproject.toml`, nem no `package.json`
7. **`.gitignore`: padrão de artefato de build entra ancorado com `/`.** Esta story não acrescenta
   nenhum — mas confira que a pasta nova de `app/(site)/organizador/` foi rastreada (T8)
8. **O code review é ao fim da epic**, não a cada story. Ao terminar a 2.2, o próximo passo é a Story
   2.3 — mas só quando o Igor mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story.

1. **A busca do organizador vai paginar?** Hoje são 20 resultados e não há "carregar mais". Se a
   Story 2.4 mostrar que 20 não bastam, a Discovery aceita `page`, com o teto de `size × page < 1000`
2. **A data do catálogo entra em algum momento?** Continua aberta desde a 2.1. O `ItemDoCatalogo` não
   a carrega, e a 2.4 pede ao organizador. Se a 2.4 for pré-preencher, o schema ganha um sétimo campo
   — e aí o `countryCode=BR` desta story vira precedente: dado do catálogo que o projeto escolhe
   consumir ou ignorar se decide na 2.1/2.2, não na tela
3. **`Meus eventos` no masthead, na 2.6, muda a navegação do organizador para três itens.** Vale
   conferir naquele momento se `Início` continua fazendo sentido para quem publica — o protótipo não
   o mostra na navegação do organizador

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (BMAD dev-story workflow)

### Debug Log References

Nenhum log de depuração separado. `uv run pytest` rodou limpo em 119/119 na primeira leva de
código; depois da revisão da busca vazia, um teste novo (que reusava o mesmo `httpx.Client` mockado
em duas chamadas de `buscar_eventos`) falhou com `RuntimeError: Cannot reopen a client instance,
once it has been closed` — corrigido separando em dois testes, cada um com seu próprio
`_instalar_transporte`. Suíte final: 121/121. `npm run build`, `npx tsc --noEmit` e `npm run lint`
passaram sem ajuste nas duas levas.

### Completion Notes List

- Backend: `countryCode=BR` acrescentado a `ticketmaster.py` com teste dedicado; rota
  `GET /organizador/catalogo` nova em `app/api/organizador.py`, registrada em `main.py`; onze testes
  novos em `test_organizador_catalogo.py` cobrindo os ACs 1, 2, 3, 5 e a Armadilha 2 dos Dev Notes
  (`&` no termo). Suíte: 107 → 119 testes, todos passando com o Compose no ar.
- Frontend: `src/lib/servidor.ts` extraído de `sessao.ts` (API_URL, NOME_DO_COOKIE, aviso de
  produção, `cabecalhoDeSessao()`), sem alterar o comportamento de `obterUsuarioDaSessao`;
  `src/lib/catalogo.ts` novo, nunca levanta; tela `/organizador/publicar` como Server Component com
  `<form method="get">`, guarda dupla (sessão + papel) e os três estados distintos do AC8 original;
  link `Publicar evento` no masthead, condicionado a `papel === "ORGANIZADOR"`.
- Verificação de fronteira (AC12): `npm run build` limpo, `npx tsc --noEmit` sem erro, `npm run lint`
  limpo, e busca por `ticketmaster`/`apikey`/`discovery` em `frontend/.next/static/` e por
  `NEXT_PUBLIC` em `frontend/src/` — zero ocorrências nos dois casos.
- **Verificação manual, feita ao vivo com o Igor no mesmo dia.** Login como organizador via `curl`
  contra o backend local confirmou `503 CATALOGO_INDISPONIVEL` sem `TICKETMASTER_API_KEY` no `.env`
  (comportamento esperado do AC5), e depois, com a chave configurada, a busca por `metallica` e a
  listagem sem termo trouxeram shows reais. Foi nesse teste que o Igor pediu a revisão abaixo.
- **Revisão pós-review (mesmo dia): busca vazia deixou de devolver `[]`.** AC3 e AC8 reescritos —
  a tela não tem mais um estado "ninguém buscou ainda"; `buscar_eventos` chama a Discovery mesmo sem
  termo, sem `keyword` e com `sort=date,asc`, listando os próximos eventos do catálogo no Brasil
  como exemplo do que o organizador pode publicar. Dois testes de `test_ticketmaster.py` reescritos
  (de "não chama" para "chama sem `keyword`"), dois de `test_organizador_catalogo.py` idem, um teste
  novo em cada arquivo. Suíte final: **121**. `page.tsx` e `page.module.css` ajustados: a busca
  agora acontece sempre; dois estados vazios distintos no lugar de três. Decisão registrada no
  README da raiz com a alternativa descartada (fileira de termos sugeridos/"chips").
- Os três READMEs atualizados duas vezes: a primeira leva com as quatro decisões originais da
  story; a segunda com a revisão da busca vazia (backend: seção *Catálogo da Ticketmaster* e
  Histórico; frontend: seção *A tela do organizador* e Histórico; raiz: nova decisão com a
  alternativa descartada).

### File List

**Backend**
- `backend/app/integrations/ticketmaster.py` (modificado — `countryCode=BR`; revisado depois —
  termo vazio chama sem `keyword` e com `sort=date,asc`, em vez de devolver `[]` sem I/O)
- `backend/app/api/organizador.py` (novo; docstrings revisadas na segunda leva)
- `backend/app/main.py` (modificado — registra `organizador.router`, reordena os `include_router`
  em ordem alfabética)
- `backend/tests/test_ticketmaster.py` (modificado — teste do `countryCode`; revisado depois —
  testes de termo vazio reescritos, um teste novo)
- `backend/tests/test_organizador_catalogo.py` (novo; revisado depois — dois testes de `q` vazio
  reescritos)

**Frontend**
- `frontend/src/lib/servidor.ts` (novo)
- `frontend/src/lib/sessao.ts` (modificado — importa de `servidor.ts`)
- `frontend/src/lib/catalogo.ts` (novo)
- `frontend/src/app/(site)/organizador/publicar/page.tsx` (novo; revisado depois — busca sempre,
  sem o estado "ninguém buscou ainda")
- `frontend/src/app/(site)/organizador/publicar/page.module.css` (novo)
- `frontend/src/components/Masthead.tsx` (modificado — link `Publicar evento` por papel)

**Documentação**
- `backend/README.md` (modificado)
- `frontend/README.md` (modificado)
- `README.md` (modificado)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modificado — status da story)
- `_bmad-output/implementation-artifacts/2-2-buscar-a-atracao-no-catalogo.md` (este arquivo)

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Story 2.2 criada e contextualizada. Quatro decisões do Igor incorporadas: o router chama `app.integrations.ticketmaster` direto, sem `services/catalogo.py` (em vez de um service fino, que seria a camada de repasse que a própria espinha descarta, ou de subir a política para um service com trabalho real, que reabriria o `ticketmaster.py` entregue ontem e moveria dois ACs da 2.1 de arquivo); `<form method="get">` + Server Component (em vez de Client Component com `chamarApi`, que reusaria mais código existente mas tiraria a busca da URL, transformaria a tela em ilha de cliente e duplicaria o estado quando a 2.4 acrescentar os passos 2 e 3); `/organizador/publicar` dentro da casca `(site)` (em vez de `/publicar`, que empurraria a 2.6 para `/meus-eventos`, perto demais de `/meus-ingressos` da Epic 4; ou de um grupo `(organizador)` com layout próprio, que contraria o "mesma casca do cliente, com navegação própria" do `EXPERIENCE.md`); e `countryCode=BR` fixo (em vez de não filtrar, que devolveria 20 shows americanos numa busca por "metallica" e faria a tela parecer quebrada na avaliação, ou de um filtro visível, que custaria parâmetro, campo e dois testes numa story de um commit). Onze ACs acrescentados aos três do `epics.md`, e as cinco armadilhas que a story existe para prevenir: o `fetch` do servidor não herda cookie e o sintoma aponta para o lugar errado — a tela diz "catálogo indisponível" quando o catálogo respondeu bem e o `401` foi nosso; `encodeURIComponent` no termo, sem o qual um `&` na busca corta o parâmetro; `searchParams` é Promise no Next 16 e sem `await` a busca cai calada no estado inicial; Server Component que levanta derruba a tela inteira, porque não existe `error.tsx` — daí `buscarNoCatalogo` devolver resultado discriminado em vez de exceção; e os três estados vazios que `itens.length === 0` torna indistinguíveis. Três suposições declaradas (papel errado redireciona para a raiz, imagem em `<img>` e não `next/image`, fila sem componente extraído) e três perguntas registradas para as stories seguintes |
| 2026-08-11 | Story implementada: backend (rota + `countryCode=BR` + 12 testes novos, suíte 107 → 119), frontend (`servidor.ts`, `catalogo.ts`, a tela `/organizador/publicar`, o link por papel no masthead) e os três READMEs atualizados com as quatro decisões desta story. Status → review |
| 2026-08-11 | **Revisão pós-review, pedida pelo Igor ao testar a tela.** AC3 e AC8 reescritos: a tela deixa de ter um estado "ninguém buscou ainda" e passa a chamar a Ticketmaster **sempre**, com ou sem termo — sem `keyword` e com `sort=date,asc` quando `q` é vazio, para o organizador ver exemplos reais do que pode publicar sem digitar nada antes. Decisão registrada no README da raiz com a alternativa descartada (uma fileira de termos sugeridos/"chips" que só dispararia a chamada ao clicar, preservando cota sem exemplo real) |
| 2026-08-11 | **Mudança avulsa, fora desta story e fora da numeração da epic** — registrada aqui porque `ticketmaster.py`, `test_ticketmaster.py` e `publicar/page.tsx` são desta story, e sem esta linha o File List e a contagem de testes acima ficam desatualizados. Filtro de classificação na Discovery: `segmentId=Music` em toda chamada, `genreId=Rock` só na listagem sem termo. Motivo: a vitrine desta story abria com o *SP2B — São Paulo Beyond Business*, uma feira de negócios, como primeira sugestão de show. O gênero fica fora da busca por termo porque `keyword=rosalia` devolve 1 resultado com o segmento e **0** com segmento + gênero — campo de busca que não acha o que a pessoa digitou é lido como defeito. Quatro testes novos em `test_ticketmaster.py` (suíte 121 → **125**), entre eles o do `genreId` **ausente** na busca por termo, que é o que impede alguém de "simplificar" movendo o parâmetro para fora do `else`. Junto, uma linha de `publicar/page.tsx`: o `id_externo` saiu da linha de origem de cada resultado — identifica o show para o código, não para quem escolhe o que publicar. Spec em `docs/techspec-filtro-do-catalogo.md`; por que não virou Story 2.7, e as alternativas descartadas das duas decisões, no `README.md` da raiz. **A story 2.2 continua em `review` — esta linha não altera o status dela** |
