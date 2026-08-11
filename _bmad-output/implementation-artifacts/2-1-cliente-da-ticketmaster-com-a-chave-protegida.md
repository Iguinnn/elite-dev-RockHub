---
baseline_commit: "abf80d6 — docs: documentando finalização da epic 1 (main, com a Epic 1 já mesclada e revisada)"
---

# Story 2.1: Cliente da Ticketmaster com a chave protegida

Status: review

Epic 2 — Publicação de eventos pelo organizador · **A primeira story da epic, e a primeira em cinco
que escreve código de aplicação.** As Stories 1.5 a 1.9 foram, nesta ordem, uma tela, uma dependência
e três de configuração e documentação. Esta abre a Epic 2 pela ponta que ninguém vê: o backend passa
a falar com um serviço fora dele.

O que entra é uma peça só — `app/integrations/ticketmaster.py` — e ela responde por três coisas: a
chave viaja do backend e nunca sai dali (AD-2), a Ticketmaster fora do ar não derruba nada, e o
formato JSON dela morre na fronteira, virando um schema deste projeto antes de qualquer outra camada
encostar.

**Não há rota, não há tela e não há banco.** `GET /organizador/catalogo?q=` é da Story 2.2. Isso torna
esta story invisível pelo `/docs` e verificável **só por teste** — que é a razão de a seção de testes
aqui ser mais longa que a de código.

## Acceptance Criteria

1. **Given** uma busca por termo
   **When** `buscar_eventos("metallica")` chama a Ticketmaster
   **Then** a requisição sai para `https://app.ticketmaster.com/discovery/v2/events.json` com a chave
   em `apikey` na query string, **a partir do processo do backend** — AD-2
   **And** nenhuma variável `NEXT_PUBLIC_` de credencial existe, e nenhum arquivo de `frontend/` é
   tocado por esta story
   **And** a chave **não aparece em nenhum log**: nem em mensagem de exceção, nem em `repr` de
   requisição, nem em `logger.exception` — as exceções do `httpx` carregam a URL completa, e a URL
   completa carrega a chave

2. **Given** que a Ticketmaster está fora do ar, lenta, estourou o limite de requisições ou recusou a
   chave
   **When** o organizador busca
   **Then** a função levanta `ErroDeDominio("CATALOGO_INDISPONIVEL", …, status_http=503)`
   **And** a aplicação não quebra — nenhuma `httpx.HTTPError` escapa da fronteira
   **And** o corpo de erro da Ticketmaster **não** é repassado: quem chama recebe a mensagem deste
   projeto, em português, e o detalhe fica no log

3. **Given** a resposta da API
   **When** ela é convertida
   **Then** vira uma lista de `ItemDoCatalogo`, com `id_externo`, `nome`, `atracao`, `imagem_url`,
   `local` e `cidade`
   **And** nenhum nome de campo da Ticketmaster (`_embedded`, `_links`, `dates`, `classifications`,
   `ratio`) aparece fora de `app/integrations/ticketmaster.py`
   **And** `app/schemas/catalogo.py` não importa nada de `app/integrations/`

4. **Given** uma resposta incompleta — sem `_embedded`, sem `venues`, sem `attractions`, sem
   `images`, ou com `city` ausente
   **When** ela é convertida
   **Then** os campos que faltam viram `None` e **nenhuma exceção sobe**
   **And** um evento sem `id` ou sem `name` é **descartado da lista**, não devolvido com campo vazio —
   sem os dois ele não serve para publicar nada (Story 2.4)

5. **Given** uma busca que não encontrou nada
   **When** ela termina
   **Then** o retorno é `[]`
   **And** isso **não** é erro: lista vazia e catálogo indisponível são situações diferentes e a
   Story 2.2 precisa distinguir as duas

6. **Given** um termo em branco, só espaços, ou vazio
   **When** eu chamo a busca
   **Then** o retorno é `[]` **sem nenhuma requisição HTTP**
   **And** o motivo está no código: a cota é de 5 000 chamadas por dia e um campo de busca vazio não
   vale uma delas

7. **Given** a `Settings`
   **When** eu a inspeciono
   **Then** existe o campo `ticketmaster_api_key`, com padrão `""`
   **And** com `AMBIENTE=producao` e a chave ausente ou vazia, a aplicação **não sobe** — mesma
   política do `JWT_SECRET` desde a Story 1.4
   **And** com `AMBIENTE=local` e a chave ausente, a aplicação sobe normalmente e a busca responde
   `CATALOGO_INDISPONIVEL` — quem clona o repositório para avaliar não precisa de conta no portal da
   Ticketmaster (NFR1)

8. **Given** o `pyproject.toml`
   **When** eu o inspeciono
   **Then** `httpx` é dependência de **runtime**, não do grupo `dev`
   **And** o motivo está escrito: o build da Railway instala com `--no-dev`, então enquanto o `httpx`
   fosse dev-only ele **não existiria na imagem de produção** — o `import` funcionaria na máquina e
   estouraria `ModuleNotFoundError` no primeiro deploy
   **And** `uv.lock` foi regenerado, e **nenhum pacote novo** entrou nele: `httpx`, `httpcore`,
   `anyio`, `certifi` e `idna` já estavam todos travados

9. **Given** a suíte
   **When** eu a rodo com a rede desligada
   **Then** ela passa inteira — nenhum teste desta story faz requisição de verdade
   **And** a substituição é `httpx.MockTransport`, não `unittest.mock.patch` no `httpx.get`

10. **Given** os três READMEs
    **When** eu os leio
    **Then** `backend/README.md` documenta a `TICKETMASTER_API_KEY` na tabela de variáveis (saindo da
    tabela "ainda não lida"), o endpoint consultado, os limites de 5 req/s e 5 000/dia, e a política
    de chave ausente por ambiente
    **And** `README.md` da raiz ganha as decisões desta story **com a alternativa descartada** de cada
    uma
    **And** `frontend/README.md` registra que nada mudou nesta camada, e que isso é o AD-2 funcionando
    — não um esquecimento

> **De onde vem cada critério.** O `epics.md` traz **três** blocos para a Story 2.1: chave como query
> param a partir do backend, erro tratado com código `CATALOGO_INDISPONIVEL`, e schema próprio. Eles
> viraram os ACs **1, 2 e 3**.
>
> **AC1 (terceira linha)** não estava no `epics.md` e é o achado técnico desta story: `httpx` põe a
> URL da requisição na mensagem de toda exceção que levanta, e a URL tem `apikey=` dentro. Um
> `logger.exception()` escrito por reflexo publica a credencial no log da Railway — o AD-2 protege a
> chave do navegador e seria furado pelo próprio backend.
>
> **AC4 e AC5** existem porque a resposta da Discovery é irregular na prática: evento sem `venue`,
> evento sem imagem, e `_embedded` simplesmente ausente quando a busca não acha nada. As três
> derrubariam um conversor escrito contra o exemplo bonito da documentação.
>
> **AC6** é a cota diária. **AC7** é a decisão do Igor sobre chave ausente. **AC8** é a armadilha de
> empacotamento — o mesmo tipo de defeito que só um ambiente limpo revela, como o `.gitignore` da
> Story 1.9. **AC9** é o que mantém a suíte rodando offline, que é como ela será avaliada. **AC10** é
> a NFR1, a NFR8 e a regra do `CLAUDE.md`.

## Tasks / Subtasks

- [x] **T1. Confirmar que a `TICKETMASTER_API_KEY` está no painel da Railway** — *do Igor* (AC: 7)
  - [x] Ela foi definida na Story 1.8 e a `Settings` ainda não a lia. A partir desta story ela é
        **obrigatória em produção**: se o valor estiver ausente ou vazio, o próximo deploy da `main`
        não sobe
  - [x] Confira antes do merge da branch da epic. O sintoma de esquecer: deploy verde no build,
        aplicação morrendo na inicialização com a mensagem do validador
  - [x] O agente não abre painel de fornecedor (regra firmada nas Stories 1.8 e 1.9) — **confirmado
        pelo Igor em 2026-08-11**: a chave já está definida no painel da Railway

- [x] **T2. `httpx` vira dependência de runtime** (AC: 8)
  - [x] `pyproject.toml`: acrescentar `"httpx==0.28.1"` em `[project].dependencies`, com o `==` que
        as outras oito usam
  - [x] **Remover** `"httpx>=0.28"` de `[dependency-groups].dev` — dependência de runtime não se
        declara duas vezes; o grupo `dev` fica só com `pytest`
  - [x] Comentário de uma linha no `pyproject.toml` dizendo por quê (o `--no-dev` do build)
  - [x] `uv sync` e conferir que o `uv.lock` mudou **só** o vínculo de `httpx` para o pacote raiz —
        nenhuma versão nova, nenhum pacote novo

- [x] **T3. `Settings` passa a ler a chave** (AC: 1, 7)
  - [x] `ticketmaster_api_key: str = ""` em `app/core/config.py`
  - [x] `@model_validator(mode="after")` novo — **não** estenda o `_recusar_segredo_de_exemplo_em_producao`:
        são dois motivos diferentes, e mensagens de erro fundidas mandam quem depura procurar no
        lugar errado
  - [x] A mensagem diz onde definir a variável, como o validador do `JWT_SECRET` diz o comando
  - [x] ⚠️ **Isto quebra `test_jwt_secret_proprio_em_producao_nao_falha`** — ver T6

- [x] **T4. `app/schemas/catalogo.py`** (AC: 3)
  - [x] `ItemDoCatalogo(BaseModel)` com `id_externo: str`, `nome: str`, `atracao: str | None`,
        `imagem_url: str | None`, `local: str | None`, `cidade: str | None`
  - [x] Docstring dizendo que este é o formato **do projeto**, e que a Story 2.4 copia estes campos
        para a tabela `evento` (AD-1)
  - [x] Nenhum import de `app/integrations/` — a dependência é de fora para dentro

- [x] **T5. `app/integrations/ticketmaster.py`** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Criar `app/integrations/__init__.py` — a pasta está prevista na árvore da arquitetura desde
        o começo e nasce aqui
  - [x] `buscar_eventos(termo: str, *, limite: int = 20) -> list[ItemDoCatalogo]`
  - [x] Termo vazio depois de `.strip()` → `[]` antes de qualquer I/O (AC6)
  - [x] `httpx.Client` com timeout explícito, dentro de `with` — conexão que não fecha é conexão
        vazando no processo do uvicorn
  - [x] `raise_for_status()` e captura de `httpx.HTTPError` (a base de timeout, conexão e status)
  - [x] **Redação da chave em todo caminho de log** — ver *A armadilha da chave no log*
  - [x] Conversão tolerante: `_embedded`, `venues`, `attractions`, `images`, `city` são todos
        opcionais (AC4)
  - [x] Evento sem `id` ou sem `name` é descartado (AC4)

- [x] **T6. Testes** (AC: 1 a 9)
  - [x] `tests/test_ticketmaster.py`, novo — `httpx.MockTransport` em todos, **zero rede** (AC9)
  - [x] ⚠️ `tests/test_config.py`: acrescentar `TICKETMASTER_API_KEY` a `_VARIAVEIS_DO_AMBIENTE` **e**
        definir a variável dentro de `test_jwt_secret_proprio_em_producao_nao_falha`, que hoje afirma
        que `AMBIENTE=producao` + `JWT_SECRET` próprio sobe — e a partir da T3 não sobe mais sem a
        chave. **Não apague o teste**: ele guarda o `cookie_secure`
  - [x] Dois testes novos em `test_config.py`: chave ausente em produção falha; chave ausente em
        `local` não falha
  - [x] Rodar `uv run pytest` com o Compose no ar e registrar o número final (eram **87**)

- [x] **T7. `backend/.env.example`** (AC: 7, 10)
  - [x] `TICKETMASTER_API_KEY=` como campo real, com o link do portal e o aviso de que em `producao`
        ela é obrigatória
  - [x] Remover a linha dela do bloco comentado "Em produção (Railway)" — ela deixou de ser uma
        variável que ninguém lê. A do `TICKET_SIGNING_SECRET` **fica**, é da Story 3.9

- [x] **T8. Os três READMEs** (AC: 10) — obrigatório, regra do projeto
  - [x] `backend/README.md`: mover `TICKETMASTER_API_KEY` da tabela "ainda não lida" para a tabela de
        variáveis; nova seção **Catálogo da Ticketmaster** com endpoint, limites, política por
        ambiente e o formato de `ItemDoCatalogo`; `httpx` na estrutura de pastas (`integrations/`);
        entrada da Story 2.1 no *Histórico desta camada*; número de testes atualizado
  - [x] `README.md` da raiz: quatro entradas em *Decisões*, cada uma com a alternativa descartada
        (ver *Decisões que o Igor tomou*); acrescentar a `TICKETMASTER_API_KEY` como pré-requisito de
        produção em *Como executar*
  - [x] `frontend/README.md`: uma entrada curta no histórico — nada mudou aqui, e é o AD-2
  - [x] Primeira pessoa em tudo

- [x] **T9. Verificação de fronteira** (AC: 1, 3)
  - [x] Busca por `_embedded`, `ticketmaster.com` e `apikey` em `backend/app/` → só em
        `app/integrations/ticketmaster.py`
  - [x] Busca por `ticketmaster` e `NEXT_PUBLIC` em `frontend/` → **zero** (só em documentação —
        `frontend/README.md` e `frontend/.env.example`, este último sem relação com a Ticketmaster)
  - [x] Nenhum arquivo de `frontend/`, `migrations/` ou `seeds/` alterado *(conferido por leitura de
        arquivo e por data de modificação — o agente não roda comando git)*

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T8).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Cliente HTTP | **`httpx` síncrono**, promovido a dependência de runtime | *`httpx.AsyncClient`*: daria concorrência real na chamada externa e seria o **único** caminho `async` do backend — a rota da 2.2 viraria `async def` e não poderia tocar a `Session` síncrona no mesmo escopo, criando duas formas de escrever rota num projeto que tem uma. O ganho é teórico: o organizador busca no catálogo uma vez por evento publicado. *`urllib` da biblioteca padrão*: zero dependência nova, ao custo de montar query string, timeout, JSON e hierarquia de erro à mão — e o teste teria que interceptar `urlopen`, em vez do `MockTransport` que o `httpx` já oferece. E "zero dependência nova" é falso aqui: o `httpx` **já está** no `uv.lock` desde a Story 1.1, puxado pelo `TestClient` |
| Endpoint da Discovery | **`/events.json`** | *`/attractions.json`*: busca o artista em vez da apresentação, e **não devolve local nem cidade** — o organizador digitaria os dois na mão na Story 2.4, e o campo `cidade` da tabela `evento` (Story 2.3) nasceria sem origem no catálogo, contrariando o "dados do catálogo copiados" do AD-1. *Os dois, com aba na busca*: cobriria buscar por show e por artista, dobrando schema, conversor e testes numa story que o `epics.md` dimensionou como um commit |
| Chave ausente | **Derruba a subida em produção**, opcional em `local` | *Nunca derrubar, sempre degradar*: a aplicação inteira continuaria no ar sem o catálogo, o que é verdade — catálogo indisponível não impede login nem compra. Caiu porque um deploy com a variável esquecida ficaria **verde**, e a falha só apareceria no dia em que alguém fosse publicar um evento. É o mesmo raciocínio do `JWT_SECRET` da Story 1.4: o modo de falhar que assusta é o que funciona. *Obrigatória em todo ambiente*: consistente, e exigiria conta no portal da Ticketmaster de quem clonou o repositório só para avaliar — atrito direto contra a NFR1 |
| Superfície desta story | **Nenhuma rota** — `GET /organizador/catalogo?q=` fica na 2.2 | *Já expor a rota aqui*: daria para conferir no `/docs` no mesmo commit, ao custo de mover um AC do `epics.md` de story e engordar a 2.1. O recorte de um commit por story é o que o desafio avalia no histórico |

**Duas suposições declaradas, não decisões suas** — uma linha para trocar se discordar:

- **O `ItemDoCatalogo` não carrega data.** A Discovery devolve `dates.start.dateTime`, e a Story 2.4
  pede que o organizador informe data e hora. Carregar a data do catálogo como sugestão seria um campo
  a mais no schema e uma decisão de tela que é da 2.4, não daqui
- **Nenhuma limitação de taxa do nosso lado.** A Discovery aceita 5 req/s, e a espinha adiou
  *rate limiting* próprio. Uma busca por evento publicado não chega perto — e um limitador seria
  estado compartilhado num processo que a Railway pode reiniciar a qualquer momento

### A armadilha da chave no log

É o item que justifica esta story existir separada da 2.2, e ele **não** está no `epics.md`.

O `httpx` transporta a chave como query param — é o que a Ticketmaster exige, e é literalmente o que
o AD-2 cita como motivo de a chamada não sair do navegador. A consequência dentro do backend:

```python
# app/integrations/ticketmaster.py
resposta = cliente.get(_URL_EVENTOS, params={"apikey": chave, "keyword": termo})
resposta.raise_for_status()
```

Quando isso falha, a exceção que sobe carrega a URL **completa**:

```
httpx.HTTPStatusError: Client error '401 Unauthorized' for url
'https://app.ticketmaster.com/discovery/v2/events.json?apikey=Xk9...&keyword=metallica'
```

E aí:

- `logger.exception("falhou")` escreve isso no log da Railway
- `logger.error("erro: %s", erro)` também
- `raise ErroDeDominio(..., mensagem=str(erro))` manda a chave para **dentro da resposta HTTP**, que
  é o pior dos três

**A regra desta story:** o log registra o que aconteceu sem a URL. Status e classe da exceção bastam
para depurar, e nenhum deles carrega credencial.

```python
logger.warning(
    "Catálogo indisponível: %s (status %s)",
    type(erro).__name__,
    getattr(getattr(erro, "response", None), "status_code", "sem resposta"),
)
```

Um teste afirma isso: provoca um `401`, captura o log com `caplog` e a resposta, e verifica que a
chave — definida como um valor reconhecível no teste — **não aparece em nenhum dos dois**. É o teste
que dá ao AC1 a única forma verificável que ele tem, já que "a chave não vaza" não se prova olhando.

⚠️ **`httpx` não redige nada sozinho.** Não existe opção de configuração para isso na 0.28.1; a
redação é responsabilidade de quem escreve o `except`.

### A resposta da Discovery, e por que o conversor precisa ser paranoico

Forma real de uma busca com resultado (campos irrelevantes cortados):

```json
{
  "_embedded": {
    "events": [{
      "name": "Metallica: M72 World Tour",
      "id": "G5vYZ9j1kdXyR",
      "images": [
        {"ratio": "16_9", "width": 1136, "height": 639, "url": "https://s1.ticketm.net/…"},
        {"ratio": "3_2",  "width": 305,  "height": 203, "url": "https://s1.ticketm.net/…"}
      ],
      "dates": {"start": {"dateTime": "2026-11-14T23:00:00Z", "localDate": "2026-11-14"}},
      "_embedded": {
        "venues": [{"name": "Allianz Parque", "city": {"name": "São Paulo"},
                    "country": {"countryCode": "BR"}}],
        "attractions": [{"name": "Metallica", "id": "K8vZ9171C-7"}]
      }
    }]
  },
  "page": {"size": 20, "totalElements": 1, "totalPages": 1, "number": 0}
}
```

**Quatro coisas que a documentação não avisa e que quebram um conversor ingênuo:**

1. **Busca sem resultado não devolve `_embedded` vazio — devolve resposta *sem* `_embedded`.** O
   corpo é só `{"page": {...}, "_links": {...}}`, com `totalElements: 0`. `dados["_embedded"]["events"]`
   estoura `KeyError` justamente no caminho mais comum de teste manual
2. **`_embedded` aninhado tem o mesmo nome nos dois níveis.** O de fora tem `events`; o de dentro de
   cada evento tem `venues` e `attractions`. Ler o de fora quando se queria o de dentro devolve
   `None` em silêncio
3. **Evento sem `venues` existe** — evento online, ou registro incompleto. `_embedded` do evento pode
   faltar inteiro, ou vir com `attractions` e sem `venues`
4. **`images` pode vir vazia, e as proporções variam.** `16_9`, `3_2`, `4_3`, mais entradas com
   `"fallback": true`, que são as genéricas da Ticketmaster e não têm nada a ver com o show

Escolha da imagem, na ordem: a mais larga com `ratio == "16_9"` e `fallback` falso; senão a mais
larga qualquer; senão `None`. É `16_9` porque é a proporção que a chamada principal da Story 3.3
consome (UX-DR4), e resolver isso aqui evita a Epic 3 reescolher imagem no meio de um componente.

Um acesso encadeado com `.get(..., {})` em cada nível resolve os quatro casos sem `try`/`except`
espalhado — e um teste por caso é o que garante que continua resolvendo.

### Endpoint, parâmetros e limites

```
GET https://app.ticketmaster.com/discovery/v2/events.json
    ?apikey=<TICKETMASTER_API_KEY>
    &keyword=<termo>
    &size=20
    &locale=*
```

| Parâmetro | Valor | Por quê |
|---|---|---|
| `apikey` | da `Settings` | Obrigatório em toda chamada. É a única forma de autenticação da Discovery |
| `keyword` | o termo, com `.strip()` | Busca por nome de evento, atração ou casa |
| `size` | `20` (o `limite`) | Padrão da API. Teto de `size × page < 1000` |
| `locale` | `*` | **Sem ele a busca filtra por idioma** e um show brasileiro pode sumir de uma consulta que deveria achá-lo. `*` casa todos |

| Limite | Valor | O que fazer |
|---|---|---|
| Por segundo | **5 req/s** | Nada. Uma busca por evento publicado não chega perto |
| Por dia | **5 000 chamadas** | É o que torna o AC6 (termo vazio não chama) uma regra e não um capricho |
| Paginação profunda | `size × page < 1000` | Fora do escopo: esta story não pagina |

**Respostas de erro da Ticketmaster:**

```json
{"fault": {"faultstring": "Invalid ApiKey",
           "detail": {"errorcode": "oauth.v2.InvalidApiKey"}}}
```

Chega com `401`. Estouro de cota vem com os cabeçalhos `Rate-Limit`, `Rate-Limit-Available` e
`Rate-Limit-Reset`. **Nenhum dos dois formatos é repassado**: os dois viram o mesmo
`CATALOGO_INDISPONIVEL`, porque para quem está buscando são a mesma coisa — o catálogo não respondeu.
A distinção que importa está no log, e ela é para o Igor, não para o organizador.

Vale uma linha no código: `401` aqui é **erro nosso** (chave errada ou revogada), não instabilidade
deles. Merece `logger.error`; os demais, `logger.warning`.

### O que já existe e esta story reusa — não reescreva nada disto

| O que | Onde | Como usar aqui |
|---|---|---|
| `ErroDeDominio` | `app/core/erros.py` | `raise ErroDeDominio("CATALOGO_INDISPONIVEL", "…", status_http=503)`. **Não crie exceção nova** — o handler do `main.py` já traduz esta no formato `{"erro": {...}}` |
| `Settings` + `@lru_cache` | `app/core/config.py` | Acrescente **um campo**. `obter_settings()` é chamado **dentro** da função, nunca no import — a razão está em `dependencias.py:52` e vale igual aqui |
| `_recusar_segredo_de_exemplo_em_producao` | `app/core/config.py:52` | É o **modelo** do validador novo, não o lugar dele. Dois motivos, dois validadores |
| Convenção de mensagem de erro | `MENSAGEM_POR_STATUS`, UX-DR8 | Frase curta que diz o que aconteceu **e** o que fazer: *"O catálogo da Ticketmaster não respondeu. Tente de novo em instantes."* |
| `httpx` no `uv.lock` | `backend/uv.lock:342` | Já travado em **0.28.1**, com `httpcore`, `anyio`, `certifi` e `idna`. A T2 muda o vínculo, não a versão |
| Estrutura `app/integrations/` | `ARCHITECTURE-SPINE.md#Árvore` | A pasta está prevista desde o início e nasce nesta story — como `services/` e `schemas/` nasceram vazias na 1.1 |
| Padrão de app mínima em teste | `tests/test_erros.py:33` | O jeito deste projeto de testar uma peça sem subir a aplicação inteira |
| `docstring` que explica o porquê | todo módulo de `app/` | Convenção firme desde a 1.1: o módulo abre dizendo o que resolve e o que descartou |

**Não devem ser tocados, e não devem quebrar:** `frontend/` **inteiro**, `backend/migrations/`,
`backend/seeds/`, `backend/app/models/`, `backend/app/api/`, `backend/app/services/`,
`docker-compose.yml`. Os arquivos que mudam são oito, e três deles são README.

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    integrations/
      __init__.py              # NOVO — pasta nasce aqui
      ticketmaster.py          # NOVO — a story inteira
    schemas/
      catalogo.py              # NOVO — ItemDoCatalogo
    core/
      config.py                # +ticketmaster_api_key, +validador de produção
  tests/
    test_ticketmaster.py       # NOVO
    test_config.py             # +2 testes, e 1 corrigido (ver T6)
  pyproject.toml               # httpx: dev → runtime
  uv.lock                      # regenerado
  .env.example                 # TICKETMASTER_API_KEY vira campo real
  README.md                    # variável, catálogo, histórico, nº de testes
README.md                      # 4 decisões com alternativa descartada
frontend/README.md             # 1 entrada: nada mudou, e é o AD-2
```

Não existe, e não deve passar a existir: `app/api/organizador.py` (é da 2.2), `app/services/catalogo.py`
(ver *Perguntas em aberto*), migração nova (é da 2.3), cache, retentativa ou limitador de taxa.

[Fonte: ARCHITECTURE-SPINE.md#Árvore — `integrations/ # cliente Ticketmaster`]

### Testing

Onze a treze testes novos, todos offline. **A suíte inteira precisa passar com a rede desligada** —
é como ela será rodada por quem avaliar, e é o AC9.

**A costura é `httpx.MockTransport`**, não `monkeypatch` em `httpx.get`. O `MockTransport` recebe a
`httpx.Request` de verdade — construída pelo `httpx` de verdade, com a query string montada pelo
código de produção — e devolve uma `httpx.Response` que você escolhe. Isso é o que torna verificável
o AC1: o teste **lê o `request.url.params["apikey"]`** e afirma o valor, em vez de acreditar.

Para o transporte ser injetável sem parâmetro extra na assinatura pública, o módulo cria o cliente
por uma função sua — `_criar_cliente()` — e o teste substitui essa função. Uma linha de indireção, e
é ela que sustenta a suíte offline.

| O que o teste prova | AC |
|---|---|
| A chave sai em `apikey` e o termo em `keyword`, na URL que o `httpx` montou | 1 |
| A URL é `app.ticketmaster.com/discovery/v2/events.json` | 1 |
| Timeout (`httpx.TimeoutException`) vira `CATALOGO_INDISPONIVEL` com `503` | 2 |
| Falha de conexão (`httpx.ConnectError`) idem | 2 |
| `429` idem · `401` idem · `500` idem | 2 |
| **A chave não aparece no `caplog` nem na mensagem do `ErroDeDominio`** | 1, 2 |
| Resposta completa vira `ItemDoCatalogo` com os seis campos certos | 3 |
| Resposta **sem `_embedded`** devolve `[]` sem estourar | 4, 5 |
| Evento sem `venues` → `local` e `cidade` viram `None` | 4 |
| Evento sem `attractions` → `atracao` vira `None` | 4 |
| Evento sem `images` → `imagem_url` vira `None`; com várias → a mais larga `16_9` | 4 |
| Evento sem `id` ou sem `name` é descartado da lista | 4 |
| JSON malformado vira `CATALOGO_INDISPONIVEL`, não `JSONDecodeError` | 2 |
| `""`, `"   "` → `[]` **e o transporte nunca é chamado** (afirme com um contador) | 6 |
| `AMBIENTE=producao` sem a chave → `Settings` levanta | 7 |
| `AMBIENTE=local` sem a chave → `Settings` sobe | 7 |

⚠️ **Três coisas que dão trabalho se passarem batido:**

1. **`test_config.py` já quebra na T3.** `test_jwt_secret_proprio_em_producao_nao_falha` define
   `AMBIENTE=producao` e um `JWT_SECRET` próprio, e afirma que a `Settings` sobe. A partir da T3 ela
   não sobe sem a chave. Conserto: definir `TICKETMASTER_API_KEY` dentro desse teste — ele continua
   provando o que provava (`cookie_secure is True`), com um pré-requisito a mais
2. **`_VARIAVEIS_DO_AMBIENTE` precisa da chave.** A fixture `ambiente_limpo` apaga as variáveis que
   os testes definem, para que a shell de quem administra a Railway não os influencie. Sem
   `TICKETMASTER_API_KEY` na lista, o teste "chave ausente derruba em produção" **passa na sua máquina
   e falha na de quem tiver a variável exportada** — ou o contrário
3. **Não teste `str(erro)` como forma de checar redação.** Afirme o contrário: que a string da chave
   usada no teste **não** está em `caplog.text` nem em `erro.mensagem`. Use um valor reconhecível
   (`"chave-de-teste-nao-vaze-isto"`) para a asserção ter significado

**Nenhum teste desta story precisa do Postgres.** Ela não toca banco — mas `uv run pytest` roda a
suíte inteira, e os testes das Stories 1.3 a 1.7 continuam exigindo o Compose no ar.

### Inteligência das stories anteriores

**Da Epic 1 inteira, o que pesa aqui:**

- **`.env.example` já anuncia esta story, com todas as letras** (`backend/.env.example:47`):
  *"TICKETMASTER_API_KEY=<chave do portal da Ticketmaster> ← idem (Story 2.1)"*, seguido de *"Campo só
  nasce quando alguém for consumir o valor"*. Esta é a story em que alguém consome. Atualize aquele
  bloco — deixá-lo dizendo que ninguém lê a variável é README desatualizado no commit que o
  desatualizou (convenção firmada na 1.9)
- **`backend/README.md:103`** promete literalmente: *"Mesmo padrão vai valer para
  `TICKETMASTER_API_KEY` (Story 2.1)"*. A decisão do Igor confirmou o padrão. Aquela frase vira
  documentação do que existe, no tempo verbal certo
- **O `.gitignore` da Story 1.9.** Padrão de artefato de build entra **ancorado com `/`**. Esta story
  não acrescenta nenhum — mas se acrescentar, é com barra inicial
- **Nenhuma verificação local pega arquivo que nunca entrou no repositório** (Story 1.9). Vale para o
  `app/integrations/__init__.py`: pasta nova, arquivo vazio, e o `.gitignore` da raiz nasceu de um
  template Python. Confira que o `__init__.py` **e** o `ticketmaster.py` estão rastreados antes de
  considerar a story pronta — o build da Railway é o primeiro clone limpo, e ele acontece depois do
  merge
- **`pool_pre_ping` do code review da Epic 1** é o precedente do timeout desta story: cliente HTTP sem
  timeout explícito espera para sempre, e o sintoma é o uvicorn com worker preso, não um erro
- **A convenção de docstring** — todo módulo de `app/` abre explicando o problema que resolve e o que
  foi descartado. Não é enfeite: é o que o desafio avalia como raciocínio, e é o material do README

**Do estado do repositório:** `main`, com a Epic 1 mesclada e revisada (`abf80d6`). **87 testes**
passando. `frontend/src/lib/` rastreado desde o conserto da 1.9. Frontend na Vercel e API na Railway,
os dois publicando a `main` — então **o merge desta epic dispara os dois deploys**, e é por isso que
a T1 existe.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-9-*.md · sprint-status.yaml]

### Stack desta story

| O que | Versão | Onde importa |
|---|---|---|
| `httpx` | **0.28.1** (já no `uv.lock`) | O cliente. `Client`, `Timeout`, `HTTPError`, `MockTransport` |
| `httpcore` / `anyio` / `certifi` / `idna` | já travados | Transitivas do `httpx` — nenhuma entra nova |
| Pydantic | 2.13.4 | `ItemDoCatalogo` e o `model_validator` da `Settings` |
| Ticketmaster Discovery | **v2** | `app.ticketmaster.com/discovery/v2/events.json` |

**Sobre a versão do `httpx`:** 0.28.1 é a última estável (lançada em 06/12/2024 e ainda corrente em
agosto de 2026). Ela **já está no lockfile deste projeto** desde a Story 1.1, puxada pelo `TestClient`
do FastAPI. A T2 não instala nada — muda de qual grupo ela vem, e é essa mudança que a põe dentro da
imagem que a Railway constrói com `--no-dev`.

[Fonte: pypi.org/project/httpx · backend/uv.lock:342-353 ·
developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2]

### Escopo — o que NÃO fazer aqui

Rota HTTP (é a 2.2) · tela (é a 2.2) · tabela `evento`/`setor` (é a 2.3) · cache de resposta ·
retentativa com espera progressiva · limitador de taxa próprio · paginação · `/attractions.json` ·
`async` em qualquer lugar · biblioteca de HTTP que não seja o `httpx` · tocar `frontend/`.

Seis tentações concretas:

- **"Ponho um cache, que a cota é de 5 000/dia."** Estado compartilhado num processo que a Railway
  reinicia. A cota não é o gargalo de uma busca por evento publicado, e a espinha adiou cache
  distribuído com esse mesmo motivo
- **"Faço três tentativas antes de desistir."** Três tentativas contra um serviço fora do ar são três
  vezes o timeout que o organizador espera olhando a tela. `CATALOGO_INDISPONIVEL` na primeira falha,
  e quem decide tentar de novo é a pessoa
- **"Aproveito e crio a rota, é uma linha."** É um AC de outra story, e um commit por story é o que
  está sendo avaliado
- **"Devolvo a resposta da Ticketmaster e converto no frontend."** É exatamente o que a AC3 proíbe, e
  o AD-1 existe para que o formato deles nunca vire dependência de nada aqui
- **"Uso `logger.exception` que é o idiomático."** É, e vaza a chave. Leia *A armadilha da chave no log*
- **"Deixo o `httpx` em `dev` porque já funciona."** Funciona na sua máquina. A Railway instala com
  `--no-dev`, e o `ModuleNotFoundError` aparece **depois** do merge, no deploy da `main`

### Project Structure Notes

Esta é a primeira story do projeto em que o backend **chama alguém**. Até aqui todo I/O era com o
Postgres, por uma biblioteca que já sabia falhar do jeito que o SQLAlchemy documenta. Serviço externo
falha de mais jeitos e num deles a credencial está no caminho — daí a fronteira ser uma pasta própria
(`integrations/`) e não uma função dentro de `services/`.

A pasta é peer de `services/` na árvore da arquitetura, e a seta do diagrama é `services → integrations`.
Como esta story não tem rota nem service, a pergunta "quem chama o cliente" não se decide aqui — ela é
da Story 2.2, e está registrada em *Perguntas em aberto* para o Igor decidir quando a 2.2 chegar.

Uma característica prática: **nada nesta story é observável pelo `/docs`, pelo navegador ou por `curl`**.
A verificação é a suíte, e é por isso que os testes desta story listam dezesseis afirmações para menos
de cem linhas de código. Story sem superfície é onde "implementei e funciona" não significa nada — o
`epics.md` a desenhou assim de propósito, para que a 2.2 nasça com a integração já provada em vez de
depurar rede e tela ao mesmo tempo.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] — os três blocos de AC originais:
  chave como query param a partir do backend, `CATALOGO_INDISPONIVEL`, e schema próprio
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — FR8 (gestão das chamadas à Discovery) e
  o objetivo da epic
- [Source: ARCHITECTURE-SPINE.md#AD-1] — Ticketmaster só em endpoints do organizador; ao publicar, os
  dados viram cópia no banco. Nenhum endpoint de cliente ou portaria chama a API externa
- [Source: ARCHITECTURE-SPINE.md#AD-2] — `TICKETMASTER_API_KEY` só existe no ambiente do backend; a
  chave trafega como query param, então chamada do navegador a expõe no histórico e no devtools
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] — `routers → services → models`, com `integrations`
  alcançada pelos services
- [Source: ARCHITECTURE-SPINE.md#Árvore] — `app/integrations/ # cliente Ticketmaster`
- [Source: ARCHITECTURE-SPINE.md#Convenções] — erro sempre `{"erro": {"codigo", "mensagem"}}`;
  configuração só por variável de ambiente
- [Source: ARCHITECTURE-SPINE.md#Adiado] — cache distribuído e rate limiting próprio, fora de escopo
- [Source: backend/app/core/config.py:52] — `_recusar_segredo_de_exemplo_em_producao`, o modelo do
  validador novo
- [Source: backend/app/core/erros.py:88] — `ErroDeDominio`, e o handler que a traduz em `app/main.py:64`
- [Source: backend/.env.example:47] — a linha que anuncia esta story e precisa ser reescrita
- [Source: backend/README.md:88-103] — a tabela "ainda não lida" e a promessa do "mesmo padrão"
- [Source: backend/uv.lock:342-353] — `httpx` 0.28.1 já travado, com as quatro transitivas
- [Source: backend/tests/test_config.py:12] — `_VARIAVEIS_DO_AMBIENTE`, que precisa da chave nova
- [Source: backend/tests/test_erros.py:33] — o padrão de app mínima com handler real
- [Source: developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2] — endpoint
  `events.json`, parâmetros, envelope `_embedded.events` + `page`, limites de 5 req/s e 5 000/dia, e o
  formato `{"fault": {...}}` do erro
- [Source: python-httpx.org/advanced/timeouts] — `httpx.Timeout(connect=, read=, write=, pool=)`;
  padrão de 5s de inatividade
- [Source: CLAUDE.md] — READMEs em primeira pessoa ao fim de toda story; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **`uv sync` é necessário nesta story** (T2) — é a primeira em seis que mexe em dependência
3. **Atualize os três READMEs antes de dar a story por concluída.** As quatro entradas de decisão da
   T8 são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As quatro desta story já estão respondidas. Se aparecer uma
   quinta — paginar, cachear, carregar a data do catálogo — pergunte em vez de escolher
5. **O agente não mexe em painel de fornecedor.** A T1 é do Igor
6. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
7. **Docker Desktop precisa estar no ar** para `uv run pytest`: a suíte roda contra o Postgres real
   desde a Story 1.3, mesmo que **nenhum** teste desta story precise de banco
8. **O code review é ao fim da epic**, não a cada story. Ao terminar a 2.1, o próximo passo é a Story
   2.2 — mas só quando o Igor mandar

## Perguntas em aberto — para o Igor, não para o dev agent

Nenhuma bloqueia esta story. As duas primeiras se decidem na 2.2:

1. **Quem chama o cliente na Story 2.2?** A espinha diz `routers → services` e também rejeita camada
   de repasse. Um `services/catalogo.py` que só encaminha seria exatamente o repasse descartado; um
   router importando `app.integrations` diretamente pula uma camada. A terceira saída é o service
   existir com trabalho real (paginação, ordenação, filtro por país) — que hoje não existe
2. **A busca do organizador filtra por país?** `countryCode=BR` reduziria muito o ruído para um
   projeto brasileiro, e esconderia shows internacionais que o organizador talvez queira publicar
3. **A data do catálogo entra em algum momento?** Hoje o `ItemDoCatalogo` não a carrega, e a 2.4 pede
   ao organizador. Se a 2.4 for pré-preencher o campo, o schema ganha um sétimo campo

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`)

### Debug Log References

- `uv sync` após mover `httpx` para `[project].dependencies`: resolveu 43 pacotes, `uv.lock` mudou
  só o vínculo de `httpx` (dev → runtime), nenhum pacote novo, nenhuma versão nova — conferido lendo
  o diff do lockfile
- `uv run pytest tests/test_ticketmaster.py tests/test_config.py -v`: 25 passed na primeira rodada
- `uv run pytest` (suíte inteira, Compose no ar): 1 failed na primeira rodada —
  `test_cookie_e_secure_apenas_em_producao` em `test_auth.py` quebrou pelo mesmo motivo já previsto
  para `test_config.py` (monta `Settings(ambiente="producao", jwt_secret=...)` sem a chave nova), só
  que não estava listado no T6 da story. Corrigido acrescentando `ticketmaster_api_key` de teste na
  mesma chamada. Segunda rodada: **107 passed**
- Verificação de fronteira (T9): grep por `_embedded`, `ticketmaster.com`, `apikey` em `backend/app/`
  achou também `app/schemas/catalogo.py`, por causa do docstring citando `_embedded` como exemplo do
  que **não** aparece no schema. Reescrevi o docstring sem citar o nome literal do campo, para o grep
  ficar limpo de verdade — só `app/integrations/ticketmaster.py` contém os três termos agora

### Completion Notes List

- Implementado `app/integrations/ticketmaster.py` (`buscar_eventos`) e `app/schemas/catalogo.py`
  (`ItemDoCatalogo`), com `httpx.Client` síncrono injetável por `_criar_cliente()` para o
  `MockTransport` dos testes
- `Settings` ganhou `ticketmaster_api_key: str = ""` e um `model_validator` **novo** (não estendeu o
  do `JWT_SECRET`), recusando a subida em produção sem a chave e permitindo ausência em `local`
- Toda falha da Ticketmaster (timeout, conexão, `401`/`429`/`500`, JSON malformado) vira
  `ErroDeDominio("CATALOGO_INDISPONIVEL", ..., status_http=503)`; `401` loga em `logger.error`
  (chave errada/revogada), os demais em `logger.warning` — nunca a URL da requisição, que carrega
  `apikey=`
- Conversão tolerante a resposta incompleta: evento sem `_embedded`, `venues`, `attractions` ou
  `images` vira campo `None`; evento sem `id` ou `name` é descartado da lista; escolha de imagem
  prioriza a mais larga `16_9` sem `fallback: true`
- 20 testes novos (18 em `tests/test_ticketmaster.py`, um deles parametrizado em 3 casos = 20
  execuções contando os 18 nomeados + 2 em `test_config.py`), todos offline via
  `httpx.MockTransport` — zero rede. Suíte completa: **107 testes passando** (87 → 107)
- Duas regressões corrigidas em testes existentes, causadas pelo novo validador de produção:
  `test_jwt_secret_proprio_em_producao_nao_falha` (`test_config.py`, prevista na story) e
  `test_cookie_e_secure_apenas_em_producao` (`test_auth.py`, **não** prevista na story — achado
  rodando a suíte inteira, não só os arquivos que a story cita)
- Os três READMEs atualizados: `backend/README.md` ganhou a seção **Catálogo da Ticketmaster**, a
  variável na tabela de configuração, a estrutura de pastas e a entrada de histórico da Story 2.1;
  `README.md` da raiz ganhou quatro decisões com a alternativa descartada de cada uma, mais o
  pré-requisito de produção em *Como executar*; `frontend/README.md` ganhou uma entrada curta
  registrando que nada mudou nesta camada — e por quê (AD-2)
- **T1 é do Igor, por regra do projeto (o agente não abre painel de fornecedor).** Confirmado por ele
  em 2026-08-11: a `TICKETMASTER_API_KEY` já está definida no painel da Railway. Sem ela, o próximo
  deploy de produção não subiria — o novo `model_validator` derruba a inicialização

### File List

- `backend/pyproject.toml` — `httpx==0.28.1` movido de `dev` para `dependencies`
- `backend/uv.lock` — regenerado (`uv sync`); só o vínculo de `httpx` mudou de grupo
- `backend/app/core/config.py` — campo `ticketmaster_api_key` e novo `model_validator`
- `backend/app/schemas/catalogo.py` — novo (`ItemDoCatalogo`)
- `backend/app/integrations/__init__.py` — novo (pasta nasce nesta story)
- `backend/app/integrations/ticketmaster.py` — novo (`buscar_eventos`)
- `backend/tests/test_ticketmaster.py` — novo, 18 testes
- `backend/tests/test_config.py` — `TICKETMASTER_API_KEY` em `_VARIAVEIS_DO_AMBIENTE`, teste
  existente corrigido, 2 testes novos
- `backend/tests/test_auth.py` — `test_cookie_e_secure_apenas_em_producao` corrigido (regressão não
  prevista na story)
- `backend/.env.example` — `TICKETMASTER_API_KEY` virou campo real; removida do bloco comentado de
  produção
- `backend/README.md` — variável na tabela de configuração, seção **Catálogo da Ticketmaster**,
  estrutura de pastas, número de testes, tabela de deploy na Railway, histórico da Story 2.1
- `README.md` (raiz) — estado atual, pré-requisito em *Como executar*, quatro decisões com
  alternativa descartada
- `frontend/README.md` — entrada de histórico da Story 2.1 (nada mudou nesta camada, e por quê)

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-11 | Implementação completa (T2 a T9). `app/integrations/ticketmaster.py` e `app/schemas/catalogo.py` novos; `Settings` com `ticketmaster_api_key` e validador próprio; `httpx` promovido a dependência de runtime; 20 testes novos, offline via `httpx.MockTransport`; duas regressões corrigidas em testes existentes (uma prevista na story, outra achada ao rodar a suíte inteira); os três READMEs atualizados. Suíte: 87 → 107 testes. Status movido para `review` |
| 2026-08-11 | T1 confirmada pelo Igor: a `TICKETMASTER_API_KEY` já está definida no painel da Railway |
| 2026-08-11 | Story 2.1 criada e contextualizada. Quatro decisões do Igor incorporadas: `httpx` síncrono promovido a dependência de runtime (em vez de `AsyncClient`, que seria o único caminho async do backend, ou de `urllib`, que exigiria montar query string, timeout e hierarquia de erro à mão — e "zero dependência nova" é falso, porque o `httpx` já está no `uv.lock` desde a 1.1); `/events.json` como endpoint (em vez de `/attractions.json`, que não devolve local nem cidade e deixaria o campo `cidade` do evento sem origem no catálogo); chave ausente derruba a subida em produção e é opcional em `local` (em vez de degradar sempre, que deixaria um deploy com a variável esquecida ficar verde até alguém tentar publicar); e nenhuma rota nesta story (em vez de expor `GET /organizador/catalogo?q=` aqui, o que moveria um AC do `epics.md` de story). Sete ACs acrescentados aos três do `epics.md`: a chave não pode aparecer em log — as exceções do `httpx` carregam a URL completa e a URL carrega o `apikey`, então `logger.exception` publicaria a credencial no log da Railway e furaria o AD-2 pelo lado de dentro; conversor tolerante a resposta incompleta, porque busca sem resultado não devolve `_embedded` vazio e sim resposta sem `_embedded`; lista vazia distinta de catálogo indisponível; termo em branco não gasta chamada da cota de 5 000/dia; `httpx` como dependência de runtime, porque o build da Railway usa `--no-dev` e o `import` estouraria só depois do merge; suíte inteira offline por `httpx.MockTransport`; e os três READMEs. Registradas duas regressões que a story provoca em `tests/test_config.py` e as três perguntas que ficam para a Story 2.2 |
