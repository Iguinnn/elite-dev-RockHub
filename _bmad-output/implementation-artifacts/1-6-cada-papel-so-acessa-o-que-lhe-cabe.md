---
baseline_commit: "a5d5d31 — Story 1.5 (branch epic-1---fundacao-acesso-e-primeiro-deploy)"
---

# Story 1.6: Cada papel só acessa o que lhe cabe

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **A story que fecha o ciclo do acesso.** A 1.4 abriu a
sessão, a 1.5 deu o caminho para criar conta — e até aqui a sessão não serve para nada: nenhuma rota
lê o cookie, nenhuma tela sabe se existe alguém do outro lado, e o `POST /auth/logout` da 1.4 nunca
foi chamado por botão nenhum. Esta story transforma o cookie em identidade (`GET /auth/eu`), a
identidade em permissão (`exigir_papel`, AD-9) e a permissão em comportamento de tela: o masthead
passa a saber quem está lá, existe uma `/conta` para sair, e quem chega sem sessão numa página que
exige conta vai para o login **e volta depois para onde queria ir**.

Também paga a última dívida escrita da 1.5: o "Entrar" no masthead, adiado com o motivo registrado
em três lugares.

## Story

Como o sistema,
quero recusar acesso fora do papel,
para que a autorização não dependa de disciplina em cada handler.

## Acceptance Criteria

1. **Given** uma rota que exige papel `ORGANIZADOR`
   **When** um cliente autenticado a chama
   **Then** recebo `403` com `{"erro": {"codigo": "SEM_PERMISSAO", ...}}`
   **And** a verificação vem de uma dependência do FastAPI **na assinatura** do endpoint — AD-9
   **And** não existe `if usuario.papel ==` no corpo de handler nenhum do projeto

2. **Given** uma rota autenticada
   **When** eu a chamo sem cookie
   **Then** recebo `401` com `{"erro": {"codigo": "NAO_AUTENTICADO", ...}}`
   **And** o mesmo `401` responde a cookie com token adulterado, expirado ou de usuário que não
   existe mais no banco — nunca `500`, nunca `403`
   **And** numa rota que exige papel, a **falta de sessão responde `401`, não `403`**: primeiro se
   pergunta quem é, depois o que pode

3. **Given** `GET /auth/eu`
   **When** eu chamo autenticado
   **Then** recebo `200` com `{"id", "nome", "email", "papel"}` — o mesmo `UsuarioSaida` do login e
   do cadastro, três rotas e um schema
   **And** `senha_hash` não aparece em campo algum

4. **Given** um token cujo `papel` não bate mais com o do banco
   **When** ele é usado numa rota de papel
   **Then** vale o papel gravado no **banco**, não o que está escrito no token — a sessão dura 8
   horas e o papel não pode ficar congelado nela por todo esse tempo

5. **Given** a página `/conta` e nenhum cookie de sessão
   **When** eu a abro
   **Then** sou levado para `/login?voltar=%2Fconta`
   **And** ao entrar com sucesso caio de volta em `/conta`, não em `/`
   **And** a raiz `/` **continua pública**: visitante sem sessão vê a programação e não é
   redirecionado para lugar nenhum

6. **Given** um `voltar` forjado — `//exemplo.com`, `https://exemplo.com`, `javascript:alert(1)`,
   `/\exemplo.com` ou `/login`
   **When** eu entro com ele na URL
   **Then** caio em `/` — só caminho interno é aceito, e nunca uma das próprias telas de acesso

7. **Given** o masthead
   **When** não há sessão
   **Then** a navegação é `Início` · `Entrar`
   **And** com sessão é `Início` · `Minha conta` — `/ingressos` sai do masthead até a Epic 4 criar a
   tela, porque link que cai no 404 não fica no repositório (precedente da 1.4)
   **And** o masthead continua sem linha de contexto, sem nome de usuário e sem data — UX-DR10

8. **Given** a `/conta` com sessão
   **When** eu a abro
   **Then** vejo nome, e-mail e papel, e um botão `Sair`
   **And** clicar em `Sair` chama `POST /auth/logout`, me leva para `/` e o masthead volta a mostrar
   `Entrar` **sem eu recarregar a página à mão**

9. **Given** a `/conta` em uma janela de 375px
   **When** eu a olho
   **Then** nada transborda e não aparece rolagem horizontal — cada story que cria tela carrega o
   próprio critério (`epics.md#Responsividade`)

10. **Given** a suíte do backend
    **When** eu a rodo
    **Then** os 55 testes anteriores continuam passando sem alteração de comportamento
    **And** os testes independentes de banco continuam passando com o Postgres desligado

> **De onde vem cada critério.** Os ACs **1 a 3** são os três do `epics.md`, com os códigos de erro,
> o formato do corpo e a precedência `401 antes de 403` explicitados.
>
> **AC4** existe porque a alternativa — ler `papel` do JWT — é o caminho mais curto e está errado:
> o token vale 8 horas, e um papel corrigido no banco continuaria valendo o antigo até o cookie
> expirar. Detalhe em *A fonte de verdade do papel é o banco*.
>
> **AC5 e AC6** são a decisão que você tomou hoje sobre o comportamento da tela diante do `401` — a
> pendência que ficou anotada ao fim da 1.5. O AC6 é a metade que ninguém escreve: parâmetro de
> retorno na URL é redirecionamento aberto esperando acontecer.
>
> **AC7 e AC8** são a outra decisão de hoje: a `/conta` mínima nasce agora, e `/ingressos` sai do
> masthead até existir. Sem isso o `GET /auth/eu` ficaria sem consumidor de tela e os dois links
> quebrados desde a 1.2 continuariam lá.
>
> **AC9** é `epics.md#Responsividade`.
>
> **AC10** existe porque esta story mexe em `tests/conftest.py` e no docstring/estrutura do
> `app/api/auth.py` — código já entregue e conferido.

## Tasks / Subtasks

- [x] **T1. `app/services/autenticacao.py` — a leitura por id** (AC: 2, 3, 4)
  - [x] `obter_usuario(sessao: Session, usuario_id: UUID) -> Usuario | None`
  - [x] É **leitura**: nenhum `commit`, nenhum `flush`, nada. A convenção do par da 1.5 continua
        valendo — *service que lê não faz nada; service que escreve abre e fecha a transação*
  - [x] `return sessao.get(Usuario, usuario_id)` — `Session.get` é a busca por chave primária, e
        ainda aproveita o objeto já identificado na sessão. Não escreva `select(...).where(id == ...)`
  - [x] Devolve `None` quando não existe. **Não levante `ErroDeDominio` aqui**: o service não sabe
        que a ausência vira `401` — quem traduz é a dependência
  - [x] Import novo no arquivo: `from uuid import UUID`

- [x] **T2. `app/core/dependencias.py` — o arquivo novo desta story** (AC: 1, 2, 4)
  - [x] Arquivo **novo**. O lugar é o que a árvore da arquitetura já reservou:
        `core/ # config, segurança, assinatura HMAC, dependências de papel`
  - [x] `usuario_atual(requisicao: Request, sessao: Session = Depends(obter_sessao)) -> Usuario`,
        na ordem: cookie ausente → `401`; `ler_token_sessao` devolveu `None` → `401`; `sub` ausente
        ou que não é UUID → `401`; `obter_usuario` devolveu `None` → `401`. O código completo está
        em *A dependência, escrita*
  - [x] **Um único `_nao_autenticado()`** para os quatro caminhos: mesma mensagem e mesmo código,
        `NAO_AUTENTICADO` / `401`. Motivo em *Por que os quatro caminhos respondem igual*
  - [x] `exigir_papel(*papeis: PapelUsuario)` é uma **fábrica** que devolve a dependência. O
        conjunto de papéis permitidos é calculado **uma vez, fora** da função interna
  - [x] A dependência interna depende de `usuario_atual` por `Depends` — é o que garante que a
        falta de sessão responda `401` e não `403` (AC2)
  - [x] Compare `usuario.papel` (que é `str`, coluna `String(20)`) com `papel.value`, **nunca** com
        o membro do enum: `"CLIENTE" == PapelUsuario.CLIENTE` é `True` porque o enum é `str, Enum`,
        mas `{PapelUsuario.CLIENTE}` e `{"CLIENTE"}` não são conjuntos equivalentes para `in`
  - [x] `obter_settings()` chamado **dentro** da função, nunca no import. Mesma razão do router
  - [x] Imports do arquivo: `from collections.abc import Callable`, `from uuid import UUID`,
        `from fastapi import Depends, Request`, `from sqlalchemy.orm import Session`,
        `obter_settings`, `obter_sessao`, `ErroDeDominio`, `ler_token_sessao`,
        `PapelUsuario`/`Usuario` e `from app.services import autenticacao`
  - [x] ⚠️ **Nenhum `if` de papel dentro de handler.** É o AC1 e é o AD-9 inteiro

- [x] **T3. `app/api/auth.py` — `GET /auth/eu`** (AC: 3)
  - [x] `@router.get("/eu", response_model=UsuarioSaida)`, corpo de uma linha:
        `return UsuarioSaida.model_validate(usuario)`, com
        `usuario: Usuario = Depends(usuario_atual)` na assinatura
  - [x] **Nenhuma sessão de banco na assinatura desta rota.** `usuario_atual` já recebeu a dele
  - [x] Atualizar o docstring do módulo: a frase *"Nenhuma verificação de papel aqui — … é assunto
        da Story 1.6"* deixou de ser verdade. Aponte para `app/core/dependencias.py`
  - [x] `app/main.py` **não muda** — o router `auth` já está registrado
  - [x] Não crie `PATCH /auth/eu` nem rota de organizador: *Escopo*

- [x] **T4. Fixtures compartilhadas em `tests/conftest.py`** (AC: 1, 2, 10)
  - [x] **Mover** a fixture `cliente` de `tests/test_auth.py` para `tests/conftest.py`, **verbatim**.
        Ela é infraestrutura (`TestClient` + `dependency_overrides[obter_sessao]`), e o segundo
        arquivo de teste desta story precisa dela
  - [x] Acrescentar em `conftest.py` a fábrica que os dois arquivos usam:
        ```python
        @pytest.fixture()
        def fabricar_usuario(sessao: Session):
            def fabricar(papel: PapelUsuario, email: str = "alguem@exemplo.com") -> Usuario:
                usuario = Usuario(nome="Alguém", email=email,
                                  senha_hash=gerar_hash("rockhub"), papel=papel.value)
                sessao.add(usuario)
                sessao.flush()
                sessao.refresh(usuario)
                return usuario
            return fabricar
        ```
  - [x] **`usuario_gravado` fica onde está**, em `test_auth.py`: 15 testes de login e cadastro
        dependem dela com aquele e-mail exato. Não a reescreva sobre a fábrica
  - [x] Depois de mover, limpe em `test_auth.py` só os imports que ficaram sem uso — e confira que
        `TestClient` continua importado, porque as anotações de tipo dos testes o usam

- [x] **T5. `tests/test_autorizacao.py` — a rota que só existe no teste** (AC: 1, 2, 4)
  - [x] Arquivo **novo**. Declara um `APIRouter` com prefixo `/_teste`, dois endpoints protegidos
        (`exigir_papel(ORGANIZADOR)` e `usuario_atual` puro), montado no `app` real por uma fixture
        `scope="module", autouse=True` que **remove as rotas no teardown**. O código está em
        *A rota que só existe no teste*
  - [x] Montar no `app` real, e não num `FastAPI()` novo, é o que dá aos testes os três
        `exception_handler` do `main.py` — sem eles o corpo do erro não teria a forma `{"erro": …}`
  - [x] Teardown: filtrar `app.router.routes` pelas rotas de `/_teste` **e** zerar
        `app.openapi_schema` — o `/docs` de `test_saude.py` não força a geração do schema hoje, mas
        um schema cacheado com uma rota fantasma é o tipo de acoplamento que aparece semanas depois
  - [x] A lista do que cada teste prova está em *Testing*

- [x] **T6. `GET /auth/eu` nos testes** (AC: 2, 3)
  - [x] Em `tests/test_auth.py`, junto das rotas de auth. Casos em *Testing*
  - [x] ⚠️ **`TestClient` guarda cookie entre chamadas.** Depois de um `POST /auth/login` no mesmo
        `cliente`, o `GET /auth/eu` já vai autenticado sem você fazer nada. Para testar o `401`,
        use um `cliente` que nunca fez login, ou `cliente.cookies.clear()` antes

- [x] **T7. `src/lib/sessao.ts` — ler a sessão do lado do servidor** (AC: 5, 7, 8)
  - [x] Arquivo **novo**, e **não** dentro de `src/lib/api.ts`: `api.ts` é importado por Client
        Components, e `next/headers` num módulo do cliente quebra o build. A separação é a razão
        de o arquivo existir
  - [x] `obterUsuarioDaSessao()` embrulhada em `cache()` do React — o masthead e a `/conta` a
        chamam na mesma requisição, e sem isso são duas idas ao backend por página
  - [x] Sem cookie no `cookies()`, devolve `null` **sem chamar a API**. Visitante é o caso comum na
        raiz pública, e não custa uma ida à rede
  - [x] URL **absoluta** para o backend: `process.env.API_URL ?? "http://localhost:8000"`, a mesma
        variável e o mesmo padrão do `next.config.ts`. O proxy `/api/*` é reescrita do navegador e
        não existe para quem já está no servidor
  - [x] `cache: "no-store"` explícito, e o cookie repassado à mão no cabeçalho `Cookie` — o `fetch`
        do servidor não herda cookie de ninguém
  - [x] `try/catch` em volta do `fetch`: backend fora do ar devolve `null`, não estoura a página. E
        `resposta.ok` falso (o `401`) também é `null`
  - [x] O código completo está em *Ler a sessão do servidor*

- [x] **T8. `src/lib/caminho.ts` — o `voltar` que não vira redirecionamento aberto** (AC: 5, 6)
  - [x] Arquivo **novo**, função pura, sem nada de `next/*` — é importada de Server e de Client
        Component
  - [x] `caminhoInternoSeguro(valor: unknown, padrao = "/"): string`, recusando: o que não é
        string; o que não começa com `/`; `//…` e `/\…` (o navegador lê os dois como host); e
        `/login`/`/cadastro` (voltar para a tela de acesso é laço)
  - [x] Escreva o motivo no comentário. `router.push` com URL não sanitizada é XSS — está escrito na
        própria documentação do Next, em *Armadilhas*
  - [x] Código e tabela de casos em *O `voltar`, e por que ele é perigoso*

- [x] **T9. Masthead com sessão e a `/conta`** (AC: 7, 8, 9)
  - [x] `Masthead.tsx` vira **`async` Server Component**: `const usuario = await obterUsuarioDaSessao()`.
        Continua sem `"use client"` — a única ilha é o `NavLink`, como já era
  - [x] Navegação: `Início` sempre; com sessão `Minha conta` → `/conta`; sem sessão `Entrar` →
        `/login`. **`Meus ingressos` sai** — volta na Epic 4, junto da tela
  - [x] **Nada de nome de usuário no masthead.** `DESIGN.md#Components/masthead` é literal:
        logotipo, fio, navegação, fio duplo — e nada mais. Os dados da pessoa são o conteúdo da
        `/conta`
  - [x] `src/app/(site)/conta/page.tsx` — Server Component. Sem sessão: `redirect("/login?voltar=%2Fconta")`
  - [x] ⚠️ **`redirect()` levanta `NEXT_REDIRECT`** e precisa ficar **fora** de qualquer `try/catch`.
        Como o `try` já mora dentro do `sessao.ts`, aqui é só um `if`
  - [x] Conteúdo: kicker `Minha conta`, o nome em serifada, e-mail e papel em mono versalete
        `--fumaca`, separados por fio, e o `BotaoSair` embaixo
  - [x] `src/components/BotaoSair.tsx` — `"use client"`. Chama `chamarApi("/auth/logout", { method: "POST" })`,
        depois `router.refresh()` e `router.push("/")`
  - [x] ⚠️ **Sem o `router.refresh()` o masthead continua mostrando a sessão.** Ele é Server
        Component e o roteador do cliente serve a versão em cache. É o AC8, e é a armadilha 1
  - [x] O `catch` do logout **não engole em silêncio a consequência**: mesmo em erro, chame
        `router.refresh()`. Se o cookie sobreviveu, o masthead voltar a mostrar `Minha conta` é a
        verdade, e é melhor do que uma tela que mente
  - [x] O botão reusa `.navLink`? **Não.** Ele é ação dentro do conteúdo, não navegação: use o
        `Botao` que já existe. Se ele ficar largo demais na coluna, é uma regra de `max-width` no
        CSS da página — não uma prop nova no `Botao`

- [x] **T10. O `voltar` nas duas telas de acesso** (AC: 5, 6)
  - [x] `(entrada)/login/page.tsx` vira `async` e recebe `PageProps<"/login">`:
        `const voltar = caminhoInternoSeguro((await searchParams).voltar)`.
        ⚠️ `searchParams` é **Promise** no Next 16 — sem o `await` você valida um objeto
  - [x] Passa `voltar` como prop para o `FormularioLogin`. **Não use `useSearchParams()`** no
        formulário: além de exigir fronteira de `<Suspense>`, faria a validação acontecer no cliente
  - [x] `FormularioLogin` ganha `{ voltar = "/" }` e troca `router.push("/")` por
        `router.push(voltar)` **seguido de `router.refresh()`** — pelo mesmo motivo do logout: o
        masthead precisa saber que agora existe sessão
  - [x] Mesma coisa em `(entrada)/cadastro/page.tsx` e `FormularioCadastro`
  - [x] O link recíproco carrega o `voltar` adiante quando ele existe: em `/login`, `href` é
        `/cadastro` ou `` `/cadastro?voltar=${encodeURIComponent(voltar)}` ``; em `/cadastro`, o
        espelho. Sem isso, quem foi mandado para o login, resolveu se cadastrar e criou a conta
        perde o destino no meio do caminho
  - [x] O resto das duas telas **não muda**: mesmos `id`, `name`, `type`, `autoComplete`, mesmos
        textos de erro por `codigo`, mesmo kicker

- [x] **T11. Verificação** (AC: todos)
  - [x] `uv run pytest` — 55 anteriores + os novos, todos verdes. Contorno nesta máquina:
        `uv run python -m pytest`
  - [x] `uv run pytest tests/test_saude.py tests/test_erros.py tests/test_config.py tests/test_seguranca.py`
        **com o Postgres parado** → continua passando
  - [x] Busca em `backend/app/` por `papel ==` e `papel in` → só em `app/core/dependencias.py`.
        Nenhuma ocorrência dentro de `app/api/`
  - [x] No navegador, sem sessão: `/` abre normalmente e o masthead mostra `Início` · `Entrar`
  - [x] Sem sessão, abrir `/conta` → cai em `/login?voltar=%2Fconta`; entrar → volta em `/conta`
  - [x] `/login?voltar=//exemplo.com`, `?voltar=https://exemplo.com`, `?voltar=javascript:alert(1)`
        e `?voltar=/login` → entrar leva a `/`, nunca para fora do site
  - [x] Com sessão: masthead mostra `Início` · `Minha conta`; a `/conta` traz nome, e-mail e papel
  - [x] `Sair` → volta para `/` **e o masthead vira `Entrar` na hora**, sem recarregar
  - [x] Cookie apagado à mão no DevTools + `/conta` → redireciona para o login
  - [x] `curl` sem cookie em `/auth/eu` → `401 NAO_AUTENTICADO` no formato `{"erro": …}`
  - [x] `npm run build`, `npx tsc --noEmit` e `npm run lint` limpos.
        ⚠️ **`/` vai aparecer como dinâmica (`ƒ`) no build, e isso é esperado** — motivo na
        armadilha 5
  - [x] Busca em `frontend/src/` por `outline: none`, `NEXT_PUBLIC_API_URL` e `localhost:8000` →
        zero (o `localhost:8000` do `sessao.ts` é o mesmo padrão do `next.config.ts`; se a busca
        acusar, é porque ele está lá — mantenha e registre)
  - [ ] `Tab` percorre a navegação do masthead e a `/conta` inteira com contorno âmbar
        — **pendente de conferência visual do Igor** (não há navegador headless nesta máquina;
        o que dá para afirmar é que não existe `outline: none` em `frontend/src/`)
  - [ ] Janela em 375px em `/conta`: sem rolagem horizontal
        — **pendente de conferência visual do Igor** (o CSS empilha os pares abaixo de 560px e o
        e-mail quebra por `overflow-wrap: anywhere`, mas medir isso exige navegador)

- [x] **T12. Documentação** (obrigatório — regra do projeto)
  - [x] `backend/README.md`: `GET /auth/eu` na seção *Autenticação*; uma seção nova sobre a
        autorização como dependência (`usuario_atual`, `exigir_papel`, a precedência `401` antes de
        `403`, e por que o papel vem do banco e não do token); a rota `/_teste` explicada em
        *Testes*, para ninguém procurá-la no código de produção; contagem de testes atualizada;
        entrada *Story 1.6* no *Histórico desta camada*
  - [x] `frontend/README.md`: `src/lib/sessao.ts` e por que ele não mora no `api.ts`; o `voltar` e
        a regra de caminho interno; o `router.refresh()` depois de toda mudança de sessão, em
        *Armadilhas do Next 16*; a `/conta`; a estrutura de pastas atualizada; e a nota de que `/`
        deixou de ser estática, com o motivo
  - [x] `README.md` da raiz, *Roteiro de avaliação*: entrar, ver a `/conta`, sair — e o passo de
        abrir `/conta` sem sessão para ver o redirecionamento com volta
  - [x] `README.md` da raiz, *Decisões*: **quatro** entradas novas, cada uma com o que caiu e por
        quê — autorização como dependência e não `if` no handler; papel lido do banco e não do
        token; guarda na página e não em `middleware`; redirecionar com volta em vez de mostrar
        convite. Matéria-prima em *Decisões que o Igor tomou* e nas seções de Dev Notes
  - [x] `README.md` da raiz, *O que não está pronto*: `Meus ingressos` saiu do masthead até a Epic 4
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "descartei")

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **A alternativa descartada de cada uma é o
material do README da raiz (T12).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Página protegida sem sessão | **Manda para `/login?voltar=…` e devolve depois** | *Mostrar a página com um convite a entrar*: mais simples, sem parâmetro nem validação — mas perde o lugar de onde a pessoa veio, e ela precisa navegar de novo depois de entrar. *Redirecionar sem devolver*: o mais barato dos três, e a perda é a mesma, sem nem a economia de código do segundo |
| O masthead com `/ingressos` e `/conta` no 404 | **Cria uma `/conta` mínima com "sair"; `/ingressos` sai até a Epic 4** | *Só esconder o que não existe*, sem tela nova: story menor, mas o `GET /auth/eu` ficaria sem consumidor de tela e o logout sem botão. *Deixar os dois links como estão*: contraria o precedente que você firmou na 1.4 — link que cai no 404 não fica no repositório — e o 404 ficaria visível para quem avaliar antes da Epic 4 |
| Como provar o `403` sem rota de organizador | **Dependência real, endpoint só dentro do `pytest`** | *Rota real e provisória de organizador* (`GET /organizador/eventos` devolvendo lista vazia): daria `curl` no navegador, mas é escopo da Epic 2 antecipado, e rota que não faz nada é rota que fica esquecida. *Adiar o `403` para a Epic 2*: story menor, com o custo de deixar um AC do `epics.md` sem cumprir e o AD-9 sem materialização nesta epic |

**Duas suposições declaradas, não decisões suas** — cada uma é uma linha para trocar se discordar:

- **O `Sair` fica na `/conta`, não no masthead.** `DESIGN.md#Components/masthead` diz "logotipo, fio,
  navegação, fio duplo" e o `EXPERIENCE.md#Information Architecture` diz "Minha conta → dados, sair".
  Os dois apontam para o mesmo lugar. `DESIGN.md#Como usar este documento` classifica "quais
  componentes existem e como se dividem" como **provisório**, então isto cabe na sua margem
- **O parâmetro se chama `voltar`**, por simetria com o resto do domínio em português

### A dependência, escrita

`app/core/dependencias.py`, o arquivo novo:

```python
def _nao_autenticado() -> ErroDeDominio:
    return ErroDeDominio("NAO_AUTENTICADO", "Entre para continuar.", status_http=401)


def usuario_atual(
    requisicao: Request,
    sessao: Session = Depends(obter_sessao),
) -> Usuario:
    token = requisicao.cookies.get(obter_settings().cookie_sessao_nome)
    if not token:
        raise _nao_autenticado()

    carga = ler_token_sessao(token)
    if carga is None:
        raise _nao_autenticado()

    try:
        usuario_id = UUID(str(carga["sub"]))
    except (KeyError, ValueError):
        raise _nao_autenticado()

    usuario = autenticacao.obter_usuario(sessao, usuario_id)
    if usuario is None:
        raise _nao_autenticado()

    return usuario


def exigir_papel(*papeis: PapelUsuario) -> Callable[..., Usuario]:
    """Fábrica de dependência: `Depends(exigir_papel(PapelUsuario.ORGANIZADOR))`."""
    permitidos = {papel.value for papel in papeis}

    def verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.papel not in permitidos:
            raise ErroDeDominio(
                "SEM_PERMISSAO",
                "Esta área é de outro papel. Entre com a conta certa.",
                status_http=403,
            )
        return usuario

    return verificar
```

Quatro detalhes que decidem se isto funciona:

- **`permitidos` é calculado fora da função interna.** Dentro, seria recalculado a cada requisição —
  e, pior, esconderia que o conjunto é fixo no momento em que a rota é declarada
- **`verificar` depende de `usuario_atual` por `Depends`, não por chamada direta.** É isso que faz
  o FastAPI resolver a autenticação primeiro e o `401` chegar antes do `403` (AC2). Chamar
  `usuario_atual(...)` à mão dentro de `verificar` obrigaria a repassar `Request` e `Session` e
  quebraria a resolução em cadeia
- **`ErroDeDominio` levantado dentro de dependência é tratado normalmente** pelo
  `@app.exception_handler(ErroDeDominio)` do `main.py`: a exceção sobe pelo solucionador de
  dependências até o middleware de exceção do Starlette. Não escreva handler novo, e não use
  `HTTPException` — ela daria os mesmos códigos (`NAO_AUTENTICADO` e `SEM_PERMISSAO` estão em
  `CODIGO_POR_STATUS`), mas com a `MENSAGEM_PADRAO` genérica no lugar de uma frase que diz o que
  fazer agora (UX-DR8)
- **`UUID(str(carga["sub"]))`.** O `sub` do JWT chega como string, mas `carga` é um `dict` sem tipo:
  um `sub` numérico, se algum dia existir, faria `UUID(int)` levantar `AttributeError` em vez de
  `ValueError`, e o `except` não pegaria

### Por que os quatro caminhos respondem igual

Cookie ausente, token corrompido, token expirado e usuário apagado são situações diferentes para
quem depura e **a mesma situação** para quem chama: não há sessão válida. Diferenciá-los na resposta
transformaria a rota num oráculo — "este id já existiu?" — pela mesma razão que a Story 1.4 gastou
uma seção inteira e um `HASH_FANTASMA` para o login não revelar se o e-mail existe.

O `ler_token_sessao` da 1.4 já colapsa expirado e adulterado num `None` só, porque o `jwt.decode`
levanta `PyJWTError` para os dois. Esta story mantém a linha.

### A fonte de verdade do papel é o banco

O JWT carrega `papel` desde a 1.4 — está no `_CargaSessao` — e o caminho curto seria ler dali e
poupar uma consulta. É errado por dois motivos:

1. **A sessão dura 8 horas (AD-15).** Um papel corrigido no banco continuaria valendo o antigo por
   até 8 horas, sem nada que se possa fazer a respeito além de trocar o `JWT_SECRET` e derrubar
   todo mundo
2. **A consulta acontece de qualquer jeito.** `GET /auth/eu` precisa de `nome` e `email`, que não
   estão no token. Ler o papel do banco não custa uma consulta a mais — custa zero

O `papel` no token continua útil: é o que permitiria, um dia, uma recusa antes da ida ao banco. Hoje
ele não é lido para autorizar nada, e isso é intencional.

### A rota que só existe no teste

```python
# tests/test_autorizacao.py
router_de_teste = APIRouter(prefix="/_teste")


@router_de_teste.get("/so-organizador")
def _so_organizador(
    usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR)),
) -> dict[str, str]:
    return {"papel": usuario.papel}


@router_de_teste.get("/so-autenticado")
def _so_autenticado(usuario: Usuario = Depends(usuario_atual)) -> dict[str, str]:
    return {"papel": usuario.papel}


@pytest.fixture(scope="module", autouse=True)
def _montar_rotas_de_teste():
    app.include_router(router_de_teste)
    yield
    app.router.routes = [
        rota for rota in app.router.routes
        if not getattr(rota, "path", "").startswith("/_teste")
    ]
    app.openapi_schema = None
```

**Por que no `app` real e não num `FastAPI()` novo:** os três `exception_handler` que dão à API a
forma `{"erro": {...}}` estão registrados em `app/main.py`. Um app novo no teste não os teria, e os
testes passariam a afirmar sobre um `{"detail": ...}` que a API de verdade nunca devolve — o pior
tipo de teste verde.

**Por que remover no teardown:** o `app` é módulo importado, compartilhado por toda a suíte. Uma
rota que fica é uma rota que outro arquivo de teste pode encontrar por acidente, e a ordem de
execução do pytest passa a importar. O `app.openapi_schema = None` é a mesma ideia: o schema é
cacheado na primeira geração, e `/docs` (que `test_saude.py` abre) hoje não a força — mas isso é
detalhe de implementação do Swagger, não contrato.

**Estas rotas nunca existem em produção.** Elas são declaradas dentro de `tests/`, que não é
importado por `app/`.

### Ler a sessão do servidor

`src/lib/sessao.ts`, o arquivo novo:

```ts
import { cookies } from "next/headers";
import { cache } from "react";

const API = process.env.API_URL ?? "http://localhost:8000";
const NOME_DO_COOKIE = "rockhub_sessao";

export type UsuarioDaSessao = {
  id: string;
  nome: string;
  email: string;
  papel: "ORGANIZADOR" | "CLIENTE" | "PORTARIA";
};

export const obterUsuarioDaSessao = cache(
  async (): Promise<UsuarioDaSessao | null> => {
    const sessao = (await cookies()).get(NOME_DO_COOKIE);
    if (!sessao) return null;

    try {
      const resposta = await fetch(`${API}/auth/eu`, {
        headers: { Cookie: `${sessao.name}=${sessao.value}` },
        cache: "no-store",
      });
      if (!resposta.ok) return null;
      return (await resposta.json()) as UsuarioDaSessao;
    } catch {
      return null;
    }
  },
);
```

Cinco decisões dentro de quinze linhas:

- **Arquivo separado do `api.ts`.** `api.ts` é importado por `FormularioLogin`, que é
  `"use client"`. `next/headers` num módulo que chega ao bundle do cliente é erro de build. A
  fronteira servidor/cliente aqui é física, não convenção
- **`cache()` do React**, não `unstable_cache` nem revalidação: a deduplicação é **dentro de uma
  requisição**. O masthead e a `/conta` chamam a mesma função e o backend é consultado uma vez
- **Sem cookie, sem ida à rede.** A raiz é pública e visitante é o caso comum
- **URL absoluta.** O `rewrite` de `/api/*` do `next.config.ts` é do navegador. Um `fetch("/api/…")`
  no servidor não tem origem para resolver e falha
- **O cookie é repassado à mão.** `fetch` do servidor não herda nada do pedido que está sendo
  atendido — este é o erro que faz a página renderizar deslogada mesmo com sessão válida

O nome `rockhub_sessao` está escrito nos dois lados: aqui, e como padrão de `cookie_sessao_nome` em
`app/core/config.py`. É acoplamento assumido — trocar o nome no backend exige trocar aqui, e isso
vai no `frontend/README.md` (T12).

### O `voltar`, e por que ele é perigoso

`?voltar=` é um valor que **quem chega escolhe** e a aplicação obedece. Sem filtro, é o clássico
redirecionamento aberto: um link para o seu domínio que joga a pessoa em outro site logo depois de
ela digitar a senha. E `router.push` com string não sanitizada é pior: a própria documentação do
Next avisa que uma URL `javascript:` entregue ao `push` **executa no contexto da página**.

```ts
const PREFIXOS_RECUSADOS = ["//", "/\\", "/login", "/cadastro"];

export function caminhoInternoSeguro(valor: unknown, padrao = "/"): string {
  if (typeof valor !== "string" || !valor.startsWith("/")) return padrao;
  if (PREFIXOS_RECUSADOS.some((prefixo) => valor.startsWith(prefixo))) return padrao;
  return valor;
}
```

| `?voltar=` | Destino | Por quê |
|---|---|---|
| `/conta` | `/conta` | caminho interno |
| `/ingressos?filtro=x` | `/ingressos?filtro=x` | query preservada; ainda é caminho interno |
| ausente, `""`, lista | `/` | não é string que começa com `/` |
| `https://exemplo.com` | `/` | não começa com `/` |
| `//exemplo.com` | `/` | o navegador lê como protocolo relativo e sai do site |
| `/\exemplo.com` | `/` | vários navegadores normalizam a contrabarra para barra |
| `javascript:alert(1)` | `/` | não começa com `/` — e é o caso que a doc do Next chama de XSS |
| `/login`, `/cadastro` | `/` | entrar para cair na tela de entrar é laço |

Repare que a lista é de **prefixos recusados**, não de caminhos permitidos. Uma lista de permitidos
seria mais rigorosa e obrigaria a editar este arquivo a cada tela nova das Epics 3 a 5 — e o dia em
que alguém esquecer, a tela nova para de receber o retorno em silêncio.

### Onde a guarda mora: na página, não em `middleware`

O caminho que todo tutorial mostra é um `proxy.ts`/`middleware.ts` conferindo o cookie antes de a
rota renderizar. Não é o que esta story faz, por dois motivos:

1. **O middleware só consegue ver que existe um cookie, não que ele vale.** Validar o JWT ali
   significaria pôr o `JWT_SECRET` no ambiente do frontend — o AD-2 e a decisão de configuração do
   projeto dizem o contrário, e o segredo de sessão do backend não tem por que existir na Vercel
2. **Ele viraria uma segunda lista de rotas protegidas**, paralela às páginas. Duas listas divergem;
   a que fica desatualizada é sempre a que ninguém olha

A guarda na página confere a sessão contra o backend, que é quem tem o segredo. O custo é que cada
página protegida repete três linhas — e essas três linhas ficam **ao lado** do conteúdo que elas
protegem, que é exatamente onde alguém que edita a página vai olhar.

Next 16 também traz `unauthorized()` e `forbidden()`, com `unauthorized.tsx`/`forbidden.tsx`, que
seriam o caminho idiomático para o 401 e o 403 de tela. Estão atrás da flag experimental
`authInterrupts` — e o projeto não liga flag experimental por conveniência.

### O que já existe e esta story estende — leia antes de escrever

Oito arquivos são **modificados**, não criados:

| Arquivo | Estado hoje | O que esta story faz |
|---|---|---|
| `backend/app/services/autenticacao.py` | `autenticar()` e `cadastrar()` | **Acrescenta** `obter_usuario()`. Nenhuma das duas é tocada |
| `backend/app/api/auth.py` | `cadastrar_cliente`, `entrar`, `sair`, dois helpers de cookie | **Acrescenta** `GET /auth/eu`. O docstring do módulo deixa de dizer que papel é assunto de outra story |
| `backend/tests/conftest.py` | fixtures `engine_teste` e `sessao` | **Recebe** a `cliente` vinda do `test_auth.py` e a fábrica `fabricar_usuario` |
| `backend/tests/test_auth.py` | os testes de login, logout e cadastro; fixtures `cliente` e `usuario_gravado` | **Perde** a definição da `cliente` (que continua disponível pelo `conftest`) e **acrescenta** os casos de `/auth/eu` |
| `frontend/src/components/Masthead.tsx` | Server Component síncrono, três links fixos | Vira `async`, lê a sessão e monta a navegação conforme ela |
| `frontend/src/components/FormularioLogin.tsx` | `router.push("/")` fixo | Ganha a prop `voltar` e o `router.refresh()` |
| `frontend/src/components/FormularioCadastro.tsx` | idem | idem |
| `frontend/src/app/(entrada)/login/page.tsx` + `cadastro/page.tsx` | Server Components síncronos | Viram `async`, leem `searchParams`, repassam `voltar` e o carregam no link recíproco |

**Não devem ser tocados, e não devem quebrar:** `app/core/seguranca.py` (`ler_token_sessao` já faz
tudo que a dependência precisa), `app/core/config.py`, `app/core/erros.py` (`NAO_AUTENTICADO` e
`SEM_PERMISSAO` já estão em `CODIGO_POR_STATUS`), `app/core/db.py`, `app/models/usuario.py`
(**nenhuma coluna muda, nenhuma migração nesta story**), `app/schemas/auth.py` (`UsuarioSaida`
serve a terceira rota sem mudança), `app/main.py`, `migrations/`, `pyproject.toml` e `uv.lock`
(**nenhuma dependência nova**). No frontend: `layout.tsx` da raiz, `(site)/layout.tsx`,
`(entrada)/layout.tsx`, `not-found.tsx`, `globals.css` (nenhum token novo), `NavLink.tsx`,
`Logotipo.tsx`, `Campo`, `Botao`, `AvisoDeErro`, `next.config.ts` e `src/lib/api.ts`.

Se algum deles precisar mudar para a autorização funcionar, algo foi feito errado.

### Contrato da rota nova

```
GET /auth/eu
  ← Cookie: rockhub_sessao=<jwt>
  → 200  {"id": "…uuid…", "nome": "Igor Duarte", "email": "igor@exemplo.com", "papel": "CLIENTE"}
  → 401  {"erro": {"codigo": "NAO_AUTENTICADO", "mensagem": "Entre para continuar."}}
         sem cookie · token adulterado · token expirado · usuário apagado

qualquer rota com Depends(exigir_papel(...))
  → 401  {"erro": {"codigo": "NAO_AUTENTICADO", ...}}   sem sessão válida
  → 403  {"erro": {"codigo": "SEM_PERMISSAO", ...}}     sessão válida, papel errado
```

`NAO_AUTENTICADO` e `SEM_PERMISSAO` são os mesmos códigos que `CODIGO_POR_STATUS[401]` e `[403]`
dariam. É de propósito, e é o contrário do que aconteceu no `409` do cadastro: ali o domínio tinha
algo a dizer que o status não dizia (`EMAIL_JA_CADASTRADO`); aqui não tem — "não autenticado" é
exatamente a informação. Usar `ErroDeDominio` mesmo assim é pela mensagem, não pelo código.

### Anatomia da `/conta`

```
       ┌──────────── coluna do site ─────────────┐
       │  RockHub                                │  ← masthead, do layout de (site)
       │  ─────────────────────────────────────  │
       │  INÍCIO   MINHA CONTA                   │  ← "Meus ingressos" volta na Epic 4
       │  ═════════════════════════════════════  │
       │                                         │
       │  MINHA CONTA                            │  ← kicker: mono 600 10px, .22em
       │                                         │
       │  Igor Duarte                            │  ← serifada: é nome próprio (UX-DR2)
       │  ─────────────────────────────────────  │  ← fio simples
       │  E-MAIL      igor@exemplo.com           │  ← rótulo e valor em mono; dado de máquina
       │  PAPEL       CLIENTE                    │
       │  ─────────────────────────────────────  │
       │                                         │
       │  ┌──────────┐                           │
       │  │  S A I R │                           │  ← o Botao que já existe
       │  └──────────┘                           │
       └─────────────────────────────────────────┘
```

Serifada só no nome. E-mail e papel são dado de máquina, então monoespaçada em versalete — a regra
do UX-DR2, e a mesma divisão que o formulário de cadastro já segue. Raio zero, sombra zero, nenhum
card. Nenhum avatar, nenhuma inicial em círculo: círculo com letra dentro é o vocabulário visual que
este projeto está inteiro tentando não ter.

[Fonte: DESIGN.md#Typography, #Components (masthead), #Spacing & Grid, UX-DR1, UX-DR2, UX-DR10]

### Armadilhas específicas desta story

Em ordem de probabilidade:

1. **`router.refresh()` esquecido depois de entrar, cadastrar ou sair.** É a armadilha central desta
   story e não dá erro nenhum: a tela navega, o `fetch` acontece, o cookie muda — e o masthead
   continua exibindo o estado antigo, porque é Server Component servido do cache do roteador. Os
   três lugares são `FormularioLogin`, `FormularioCadastro` e `BotaoSair`
2. **`await` esquecido no `cookies()` e no `searchParams`.** Os dois são Promise no Next 16. Sem o
   `await`, `cookies().get` não existe e `searchParams.voltar` é `undefined` — que cai calado no
   padrão `/` e parece "o voltar não funciona"
3. **`redirect()` dentro de `try/catch`.** Ele funciona levantando `NEXT_REDIRECT`; um `catch` em
   volta transforma o redirecionamento numa página em branco
4. **`fetch` do servidor sem repassar o `Cookie`.** Renderiza sempre deslogado, mesmo com sessão
   boa, e não há erro para investigar
5. **`/` deixa de ser estática no build.** O masthead lê `cookies()`, e isso torna dinâmica toda
   rota do grupo `(site)`. O `npm run build` vai marcar `/` com `ƒ` em vez de `○`. **É correto** —
   uma página cujo cabeçalho depende de quem pediu não pode ser pré-renderizada. Não tente
   consertar com `export const dynamic`
6. **`TestClient` guarda cookie entre chamadas.** Um teste que faz login e depois quer provar o
   `401` precisa de outro `cliente` ou de `cliente.cookies.clear()`
7. **`usuario_atual` chamado à mão dentro de `exigir_papel`**, em vez de por `Depends`. Some com a
   resolução em cadeia e inverte a ordem `401`/`403`
8. **`obter_settings()` no import de `dependencias.py`.** Prende a configuração no momento do
   import e quebra a substituição por `monkeypatch`, do mesmo jeito que quebraria no router
9. **Mover a fixture `cliente` e deixar import órfão no `test_auth.py`.** O `npm run lint` não olha
   Python; quem acusa é o `ruff`, se estiver configurado — confira à mão
10. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** `uv run pytest` falha
    com `os error 4551`; o contorno é `uv run python -m pytest`. Documentado desde a Story 1.1
11. **`uv run pytest` exige o Compose no ar** desde a Story 1.3
12. **`TaskStop` não mata o `node` filho do `npm run dev`.** O órfão segura a porta 3000 e a
    conferência seguinte bate num build antigo. Encerrar processo em segundo plano inclui conferir
    a porta e matar pelo PID — aprendido na 1.4

### Convenções que esta story confirma ou cria

- **Autorização é dependência declarada na assinatura, nunca `if` no corpo.** Vale para todas as
  rotas das Epics 2 a 5. A Epic 2 não escreve nada disso de novo: importa `exigir_papel`
- **Autenticação vem antes de autorização.** Sem sessão é `401`; com sessão e papel errado é `403`
- **O papel vem do banco, não do token.** Vale para o vínculo portaria ↔ evento do AD-7, que também
  vai ser lido do banco a cada validação, e não carregado na sessão
- **Estado de sessão no frontend é lido no servidor, nunca guardado no cliente.** Não há contexto
  React de usuário, não há `localStorage`, não há estado global — a página pergunta ao servidor e o
  servidor pergunta ao backend
- **Toda mudança de sessão é seguida de `router.refresh()`**
- **Parâmetro de URL que vira navegação passa por `caminhoInternoSeguro`**. Vale para o retorno
  depois do checkout (Epic 3) e para o link compartilhado (Epic 4)
- **Rota que só existe para provar uma garantia mora em `tests/`**, com prefixo `/_teste` e teardown

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    core/
      dependencias.py           # NOVO — usuario_atual, exigir_papel
    services/
      autenticacao.py           # +obter_usuario()
    api/
      auth.py                   # +GET /auth/eu
  tests/
    conftest.py                 # +cliente (movida), +fabricar_usuario
    test_auth.py                # -cliente (movida), +casos de /auth/eu
    test_autorizacao.py         # NOVO — rota /_teste, 401 e 403
frontend/
  src/
    lib/
      sessao.ts                 # NOVO — só servidor
      caminho.ts                # NOVO — função pura
    components/
      BotaoSair.tsx             # NOVO — "use client"
      Masthead.tsx              # vira async, lê a sessão
      FormularioLogin.tsx       # +prop voltar, +router.refresh()
      FormularioCadastro.tsx    # idem
    app/
      (site)/
        conta/
          page.tsx              # NOVO — Server Component com a guarda
          page.module.css       # NOVO
      (entrada)/
        login/page.tsx          # vira async, lê searchParams
        cadastro/page.tsx       # idem
```

Nenhuma migração, nenhuma dependência, nenhum token de CSS novo. `app/integrations/` e
`backend/seeds/` continuam não existindo — Stories 2.1 e 1.7.

[Fonte: ARCHITECTURE-SPINE.md#Árvore — `core/` é onde moram as "dependências de papel"]

### Comandos que esta story precisa deixar funcionando

```bash
# da raiz
docker compose up -d

cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # /docs mostra /auth/eu ao lado de login, logout e cadastro
uv run pytest                           # contorno nesta máquina: uv run python -m pytest

cd ../frontend
npm run dev                             # http://localhost:3000/conta
```

Nada de `uv sync` nem de `npm install` — esta story não acrescenta dependência nenhuma. É a segunda
seguida em que isso acontece.

### Escopo — o que NÃO fazer aqui

Seed e contas documentadas (**Story 1.7**) · deploy e variáveis em produção (**Stories 1.8 e 1.9**) ·
qualquer rota de organizador, cliente ou portaria de verdade (**Epics 2 a 5**) · tela de
`/ingressos` (**Epic 4**) · navegação diferente por papel no masthead — "Meus eventos" para
organizador, "Turnos" para portaria (**Epics 2 e 5**) · encaminhamento por papel logo depois de
entrar (**Epics 2 e 5**) · edição de conta, troca de senha, `refresh token`, expiração deslizante.

Quatro tentações concretas desta story:

- **"Já que estou no masthead, faço a navegação por papel agora."** Não faça: nem `/organizador`
  nem `/portaria` existem, e a story voltaria a criar links que caem no 404 — exatamente o que o
  AC7 está consertando
- **"Já que a `/conta` existe, coloco 'editar dados' nela."** Editar conta não é story de epic
  nenhuma
- **"Já que `exigir_papel` existe, crio `/organizador/eventos` para provar."** É a alternativa que
  você descartou hoje, com o motivo escrito
- **"Já que estou lendo a sessão, faço um `ContextoDeUsuario` no cliente."** Estado de sessão
  duplicado no cliente é a fonte clássica de tela que mostra o usuário errado depois do logout. O
  servidor já sabe; a página pergunta a ele

### Testing

Precisa do Compose no ar. Nenhum teste novo é independente de banco.

**`tests/test_auth.py` — `GET /auth/eu`**

| O que prova | AC |
|---|---|
| Com o cookie do login, responde `200` com `id`, `nome`, `email` e `papel`, e **sem** `senha_hash` | 3 |
| O corpo é idêntico ao que o próprio `POST /auth/login` devolveu — três rotas, um schema | 3 |
| Sem cookie nenhum responde `401` com `codigo == "NAO_AUTENTICADO"`, no formato `{"erro": …}` | 2 |
| Cookie com token adulterado (um caractere trocado no **meio** da assinatura) responde `401` | 2 |
| Cookie com texto que não é JWT (`"nao-e-um-token"`) responde `401`, não `500` | 2 |
| Token válido de um usuário apagado do banco responde `401` | 2 |
| Depois de `POST /auth/logout`, o mesmo cliente recebe `401` | 2 |

**`tests/test_autorizacao.py` — a dependência**

| O que prova | AC |
|---|---|
| `ORGANIZADOR` autenticado em `/_teste/so-organizador` responde `200` | 1 |
| `CLIENTE` autenticado responde `403` com `codigo == "SEM_PERMISSAO"` | 1 |
| `PORTARIA` autenticado responde `403` — a fábrica recusa todo papel fora da lista, não só um | 1 |
| **Sem cookie** responde `401`, **não** `403` — autenticação antes de autorização | 2 |
| `exigir_papel(ORGANIZADOR, PORTARIA)` aceita os dois e recusa `CLIENTE` | 1 |
| Um usuário gravado como `CLIENTE` recebe `403` mesmo com um token forjado dizendo `papel: ORGANIZADOR` — o banco decide | 4 |
| `/_teste/so-autenticado` responde `200` para qualquer um dos três papéis | 2 |

O caso do token forjado é o único que precisa montar um JWT à mão: use `criar_token_sessao` sobre um
`Usuario` de mentira com o papel trocado, ou `jwt.encode` direto com o `jwt_secret` das settings. É o
teste que prova o AC4 — sem ele, ler o papel do token passaria despercebido.

**Os 55 testes atuais continuam passando sem alteração.** Se um deles precisar mudar, a mudança de
`conftest.py` ou o docstring do `auth.py` alteraram comportamento — e não deveriam.

**O frontend continua sem teste automatizado**, decisão registrada na Story 1.2 e já no README da
raiz. A verificação das telas é manual, e está na T11. Nesta story ela pesa mais do que o normal: o
`router.refresh()` esquecido não quebra build, não quebra tipo e não quebra lint — só a tela mente.

### Inteligência das stories anteriores

**Da 1.5 (a story imediatamente anterior — leia estas antes de tudo):**

- **O "Entrar" no masthead foi adiado para cá**, com o motivo escrito na T6 daquela story:
  *"Não toque em `Masthead.tsx`. O 'Entrar' no cabeçalho é a Story 1.6, que é quem passa a saber se
  existe sessão"*. Esta story é onde a promessa vence
- **`GET /auth/eu` já está prometido em três docstrings**: `app/schemas/auth.py` ("a Story 1.6
  reaproveita em `GET /auth/eu`"), `app/api/auth.py` e `src/lib/api.ts`. Os três precisam parar de
  falar no futuro
- **`cadastrar()` fixou a convenção de transação**: service que lê não faz `commit`. `obter_usuario`
  é do lado que lê
- **O texto de tela vem do `codigo`, nunca da `mensagem`** — vale se algum formulário desta story
  precisar tratar erro
- **`sessao.rollback()` no `409` derruba o que a fixture inseriu.** Não é caminho desta story, mas
  a fábrica `fabricar_usuario` usa o mesmo `flush` sem commit
- **`test_token_com_assinatura_alterada_e_recusado` é flaky, e a causa está diagnosticada** no
  *Debug Log* da 1.5: a assinatura HMAC-SHA256 ocupa 43 caracteres em `base64url`, e os 2 bits
  finais são padding — trocar o **último** caractere por `A`, `B`, `C` ou `D` decodifica para os
  mesmos 32 bytes e não adultera nada. **Consequência direta para esta story:** o teste de token
  adulterado em `/auth/eu` deve trocar um caractere do **meio** da assinatura, nunca o último. O
  conserto do teste antigo não é desta story — é do code review da epic

**Da 1.4 (sessão):**

- **`ler_token_sessao` devolve `None` para qualquer `PyJWTError`** — expirado e adulterado já
  chegam colapsados
- **`EXPIRACAO_SESSAO` é a única fonte da validade** da sessão, e é invariante do AD-15
- **A resposta não pode virar oráculo.** É a linha de raciocínio que o `401` único desta story herda
- **`credentials: "include"` é desnecessário** — a chamada do navegador é de mesma origem por causa
  do proxy. Isso vale para o `chamarApi` do logout
- **`obter_settings()` é chamado dentro do módulo que o usa**, para o `monkeypatch` do teste de
  `Secure` continuar valendo
- **`frontend/AGENTS.md` manda ler `node_modules/next/dist/docs/`** antes de escrever código de
  Next 16. Os arquivos que importam aqui:
  `01-app/03-api-reference/04-functions/cookies.md`, `redirect.md`, `use-router.md` e
  `01-app/03-api-reference/03-file-conventions/page.md`

**Da 1.3 (banco):**

- **`papel` é `String(20)` com `CHECK`**, e `PapelUsuario` mora em `app/models/usuario.py` — cujo
  docstring já diz, desde aquela story, *"A dependência de papel da Story 1.6 … importa
  `PapelUsuario` daqui. Não redeclare o enum em outro lugar"*
- **`id` é `Uuid`**, e é por isso que o `sub` do token precisa voltar a `UUID` antes da consulta
- **A fixture de sessão reabre o `SAVEPOINT` por evento**

**Da 1.2 (frontend):**

- **O masthead nasceu sem linha de contexto de propósito** (UX-DR10), e continua assim: esta story
  acrescenta itens de navegação, não informação
- **Foco âmbar global e `prefers-reduced-motion` já estão no `globals.css`** — herde, não redeclare
- **`.conteudo` é a coluna única de 1180px** compartilhada por masthead e conteúdo

**Da 1.1 (backend):**

- **O formato de erro já cobre `401` e `403`.** `CODIGO_POR_STATUS` tem `NAO_AUTENTICADO` e
  `SEM_PERMISSAO`. **Não escreva handler novo**
- **`tratar_erro_http` preserva `headers`**, inclusive `WWW-Authenticate` — que esta story não usa,
  porque a sessão é cookie e não `Bearer`

**Do estado do repositório:** branch `epic-1---fundacao-acesso-e-primeiro-deploy`, com a Story 1.5
commitada (`a5d5d31`). As Stories 1.1 a 1.5 estão em `review` — o code review é ao fim da epic, não a
cada story. 55 testes passando no backend.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-5-*.md]

### Stack desta story

**Nenhuma versão nova para conferir: esta story não acrescenta dependência.** Tudo que ela usa já
está no lockfile.

| O que ela usa | Versão | Para quê |
|---|---|---|
| FastAPI | 0.141.1 | `Depends` encadeado, dependência-fábrica, `Request.cookies` |
| PyJWT | (do lock) | já embrulhado por `ler_token_sessao`; só o teste do token forjado a toca direto |
| SQLAlchemy | 2.0.51 | `Session.get` para a busca por chave primária |
| Next | 16.3.0 | `cookies()` e `searchParams` **assíncronos**, `redirect()`, `PageProps<"/login">` |
| React | 19.2.8 | `cache()` para deduplicar a leitura da sessão dentro da requisição |

Duas notas de versão que mudam o código:

- **`cookies()` e `searchParams` são Promise a partir do Next 15**, e o modo síncrono está a caminho
  da remoção. Todo exemplo de blog anterior a isso está errado nesse ponto
- **`typedRoutes` está desligado** (não aparece no `next.config.ts`), então `href` e `router.push`
  aceitam string comum: `/login?voltar=…` montado em tempo de execução não precisa de conversão de
  tipo. Os tipos globais `PageProps`/`LayoutProps` existem de qualquer jeito, gerados em
  `.next/types/routes.d.ts`

Se surgir vontade de instalar `next-auth`, `jose`, `zod` ou uma biblioteca de estado: nenhuma tem
lugar aqui. A sessão é um cookie que o backend assina e o servidor do Next lê — não há o que uma
biblioteca de autenticação faça neste desenho além de acrescentar um modelo mental a mais.

[Fonte: ARCHITECTURE-SPINE.md#Stack, #AD-9, #AD-15]

### Project Structure Notes

Esta story ocupa as duas camadas, como a 1.4 e a 1.5, e pela mesma razão: a garantia do backend e o
comportamento da tela diante dela são uma decisão só. Um `401` que nenhuma tela sabe interpretar não
é autorização — é uma porta trancada sem maçaneta.

A diferença é a distribuição do risco. No backend, quase tudo é código novo em arquivo novo
(`dependencias.py`), e o único ponto de contato com o que já funciona é a fixture que muda de lugar.
No frontend é o oposto: cinco dos sete arquivos já estavam entregues e conferidos, e três deles
(`Masthead`, `FormularioLogin`, `FormularioCadastro`) fazem parte do caminho que o avaliador percorre
primeiro.

Ordem sugerida: T1 → T2 → T3 → T4 → T5 → T6 (backend inteiro fechado e testado) → T7 → T8 → T9 →
conferir masthead e `/conta` no navegador → T10 → conferir login e cadastro de novo.

Não toque em `migrations/`: nenhuma coluna muda. O modelo `Usuario` da Story 1.3 já previa esta
story no próprio docstring.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.6] — os três ACs originais
- [Source: _bmad-output/planning-artifacts/epics.md#Responsividade] — cada story de tela carrega o
  próprio critério; corte em 900px
- [Source: ARCHITECTURE-SPINE.md#AD-9] — autorização declarada no endpoint, papel único por conta
- [Source: ARCHITECTURE-SPINE.md#AD-15] — Argon2id, JWT em cookie `httpOnly` de 8 horas
- [Source: ARCHITECTURE-SPINE.md#AD-2] — chave sensível só no ambiente do backend; é o argumento
  contra validar JWT no middleware do Next
- [Source: ARCHITECTURE-SPINE.md#AD-7] — a portaria só valida onde foi escalada; é a próxima camada
  de autorização, e ela também lê do banco
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] · [#Convenções de Consistência] · [#Árvore] —
  `routers → services → models`, transação no service, `core/` guarda as dependências de papel
- [Source: ARCHITECTURE-SPINE.md#Adiado] — sem refresh token; teste automatizado de frontend fora
- [Source: EXPERIENCE.md#Information Architecture] — "Minha conta → dados, sair"
- [Source: EXPERIENCE.md#Voice and Tone] · [UX-DR8] — erro diz o que aconteceu e o que fazer
- [Source: DESIGN.md#Components (masthead)] · [#Typography] · [#Como usar este documento] ·
  [UX-DR1, UX-DR2, UX-DR9, UX-DR10]
- [Source: _bmad-output/implementation-artifacts/1-5-cadastro-de-cliente.md] — a dívida do "Entrar"
  no masthead, o flaky do token adulterado e as convenções de service/erro/fixture
- [Source: backend/app/core/seguranca.py] · [core/erros.py] · [core/db.py] · [core/config.py] ·
  [api/auth.py] · [services/autenticacao.py] · [schemas/auth.py] · [models/usuario.py] ·
  [tests/conftest.py] · [tests/test_auth.py]
- [Source: frontend/src/components/Masthead.tsx] · [NavLink.tsx] · [FormularioLogin.tsx] ·
  [FormularioCadastro.tsx] · [src/lib/api.ts] · [src/app/(site)/layout.tsx] · [next.config.ts]
- [Source: frontend/node_modules/next/dist/docs/01-app/03-api-reference/04-functions/cookies.md] —
  `cookies()` é assíncrona e torna a rota dinâmica
- [Source: .../04-functions/redirect.md] — `redirect()` levanta `NEXT_REDIRECT`; fora do `try`
- [Source: .../04-functions/use-router.md] — `router.refresh()`; e o aviso sobre URL não sanitizada
  entregue ao `push`
- [Source: .../03-file-conventions/page.md] — `searchParams` é Promise
- [Source: .../05-config/01-next-config-js/typedRoutes.md] — desligado por padrão
- [Source: frontend/AGENTS.md] — Next 16 divergiu; a documentação é a de `node_modules/next/dist/docs/`
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Confirme com o Igor antes de `docker compose up`**, se ele não estiver acompanhando. Não há
   `uv sync` nem `npm install` nesta story
3. **Atualize os três READMEs antes de dar a story por concluída.** As quatro entradas de decisão da
   T12 são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As três desta story já estão respondidas. Se aparecer uma
   quarta — o rótulo do item de navegação, o texto do `401`, se o `Sair` também vai para o masthead
   — pergunte em vez de escolher
5. **Encerrar processo em segundo plano inclui conferir a porta e matar pelo PID.** O `Ctrl+C` do
   Igor não mata processo iniciado por agente
6. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Code)

### Debug Log References

**A suíte com o Postgres desligado foi provada sem desligar o Postgres.** O AC10 pede que os testes
independentes de banco continuem passando com o Compose parado, e derrubar o contêiner na máquina do
Igor no meio da sessão não era necessário: rodei `tests/test_saude.py test_erros.py test_config.py
test_seguranca.py` com `DATABASE_URL` e `DATABASE_URL_TESTE` apontando para uma porta inexistente
(`127.0.0.1:59999`). Os 24 passaram — o que prova a afirmação mais forte: nada em `conftest.py`, nem
na cadeia de import de `app.main`, abre conexão em escopo de import. Se o `create_engine` do
`app/core/db.py` conectasse no import, esses testes falhariam na coleta.

**Conferência de tela por resposta HTTP, não por navegador.** Não há Playwright nem Puppeteer nesta
máquina, e a story proíbe dependência nova. Os itens "no navegador" da T11 foram verificados contra
o `next dev` que já estava no ar, por `curl`, olhando o HTML renderizado pelo servidor:

- sem cookie, o masthead da raiz traz exatamente dois links: `/` e `/login`
- `GET /conta` sem cookie, seguindo o redirecionamento, termina em
  `http://localhost:3000/login?voltar=%2Fconta`
- com o cookie de um login real, o masthead traz `/` e `/conta`, e a `/conta` renderiza nome, e-mail
  e papel mais o botão `Sair`
- o `?voltar=` foi provado pelo `href` do link recíproco, que carrega o valor **já sanitizado**:
  `/conta` e `/ingressos?filtro=x` sobrevivem; `//exemplo.com`, `https://exemplo.com`,
  `javascript:alert(1)`, `/\exemplo.com` e `/login` viram `/`

Duas conferências continuam pendentes por serem visuais: percurso de `Tab` com contorno âmbar e a
ausência de rolagem horizontal em 375px. Estão desmarcadas na T11.

**A flaky da 1.5 não se repetiu aqui.** O teste novo de token adulterado troca um caractere do
**meio** da assinatura, como o Debug Log daquela story recomendava — os 2 bits finais do `base64url`
são padding, e mexer no último caractere não adultera nada.

### Completion Notes List

**O que a story entrega, em uma frase:** o cookie da 1.4 virou identidade (`GET /auth/eu`), a
identidade virou permissão (`usuario_atual` + `exigir_papel`, AD-9) e a permissão virou comportamento
de tela (masthead por estado de sessão, `/conta` com logout, redirecionamento com volta).

**Backend.** Um arquivo novo, `app/core/dependencias.py`, e mais nada estrutural: `obter_usuario()`
entrou no service que já existia (leitura por `Session.get`, sem `commit`), `GET /auth/eu` entrou no
router que já existia, e o `UsuarioSaida` da 1.4 serviu a terceira rota sem mudar uma linha. Nenhuma
migração, nenhuma dependência nova — segunda story seguida sem tocar no lockfile.

**A ordem `401` antes de `403` não é código, é estrutura.** `exigir_papel` depende de `usuario_atual`
por `Depends`, e é isso que faz o FastAPI resolver a autenticação primeiro. O teste
`test_sem_cookie_na_rota_de_papel_responde_401_e_nao_403` existe para quebrar se alguém trocar o
`Depends` por uma chamada direta.

**O papel vem do banco, e há teste provando.** `test_papel_forjado_no_token_nao_vale_contra_o_banco`
monta um JWT válido dizendo `ORGANIZADOR` sobre um usuário gravado como `CLIENTE` e espera `403`.
Sem ele, ler `carga["papel"]` passaria despercebido — e a sessão de 8 horas congelaria o papel.

**Frontend.** Dois arquivos novos em `lib/` (`sessao.ts`, só servidor; `caminho.ts`, função pura), a
`/conta` com a guarda, o `BotaoSair`, e o masthead virando `async`. A separação `sessao.ts` ×
`api.ts` não é organização: `api.ts` é importado por Client Components, e `next/headers` num módulo
do cliente quebra o build.

**O `router.refresh()` está nos três lugares** — `FormularioLogin`, `FormularioCadastro`,
`BotaoSair`. É a armadilha que não quebra build, tipo nem lint: sem ele o masthead continua
mostrando o estado antigo, servido do cache do roteador.

**`/` deixou de ser estática, e é esperado.** O `npm run build` marca todas as rotas com `ƒ`: o
masthead lê `cookies()` e torna dinâmico o grupo `(site)`; as telas de acesso leem `searchParams`.
Uma página cujo cabeçalho depende de quem pediu não pode ser pré-renderizada. Registrado no
`frontend/README.md` para ninguém tentar "consertar".

**Os 55 testes anteriores passaram sem uma linha alterada**, apesar de a fixture `cliente` ter
mudado de arquivo. Total: **73 testes**. O único `localhost:8000` em `frontend/src/` está no
`sessao.ts`, é o mesmo padrão do `next.config.ts` e está registrado no README, como a T11 previa.

**Nenhum `if` de papel em handler:** busca por `papel ==` e `papel in` em `backend/app/` só acha
`app/core/dependencias.py` — e lá é a construção do conjunto de permitidos, não uma verificação
solta. Zero ocorrências em `app/api/`.

**Duas conferências visuais ficaram para o Igor** (`Tab` com contorno âmbar e 375px sem rolagem
horizontal): não há navegador headless na máquina e a story proíbe dependência nova. O resto da T11
foi verificado, com o método no Debug Log.

### File List

**Backend — novos**

- `backend/app/core/dependencias.py`
- `backend/tests/test_autorizacao.py`

**Backend — modificados**

- `backend/app/services/autenticacao.py` (+`obter_usuario`, docstring do módulo)
- `backend/app/api/auth.py` (+`GET /auth/eu`, docstring do módulo)
- `backend/app/schemas/auth.py` (só o docstring: `/auth/eu` deixou de ser promessa futura)
- `backend/tests/conftest.py` (+`cliente` vinda do `test_auth.py`, +`fabricar_usuario`)
- `backend/tests/test_auth.py` (−`cliente`, +7 testes de `/auth/eu`, imports ajustados)
- `backend/README.md`

**Frontend — novos**

- `frontend/src/lib/sessao.ts`
- `frontend/src/lib/caminho.ts`
- `frontend/src/components/BotaoSair.tsx`
- `frontend/src/app/(site)/conta/page.tsx`
- `frontend/src/app/(site)/conta/page.module.css`

**Frontend — modificados**

- `frontend/src/components/Masthead.tsx` (async, navegação por estado de sessão)
- `frontend/src/components/FormularioLogin.tsx` (prop `voltar`, `router.refresh()`)
- `frontend/src/components/FormularioCadastro.tsx` (idem)
- `frontend/src/app/(entrada)/login/page.tsx` (async, lê e valida `searchParams`)
- `frontend/src/app/(entrada)/cadastro/page.tsx` (idem)
- `frontend/src/lib/api.ts` (só o docstring: aponta para o `sessao.ts`)
- `frontend/README.md`

**Raiz**

- `README.md` (roteiro de avaliação, quatro decisões novas, *O que não está pronto*)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.6 implementada. Backend: `app/core/dependencias.py` (`usuario_atual`, `exigir_papel`), `obter_usuario()` no service, `GET /auth/eu`. Testes: fixture `cliente` movida para o `conftest.py`, `fabricar_usuario` nova, `tests/test_autorizacao.py` com a rota `/_teste`, 7 casos de `/auth/eu` — 55 → **73 testes**, os 55 anteriores sem alteração. Frontend: `lib/sessao.ts` e `lib/caminho.ts`, `/conta` com guarda, `BotaoSair`, masthead `async` por estado de sessão, `?voltar=` sanitizado nas duas telas de acesso e `router.refresh()` nos três pontos de mudança de sessão. `npm run build`, `tsc --noEmit` e `lint` limpos; todas as rotas passaram a ser dinâmicas, o que é esperado. Os três READMEs atualizados, com quatro decisões novas no da raiz. Pendentes: duas conferências visuais (`Tab` e 375px) |
| 2026-08-10 | Story 1.6 criada e contextualizada. Três decisões do Igor incorporadas: página protegida sem sessão redireciona para `/login?voltar=…` e devolve depois; `/conta` mínima com "sair" nasce agora e `/ingressos` sai do masthead até a Epic 4; o `403` é provado por uma rota que só existe dentro do `pytest`, sem antecipar escopo da Epic 2. Sete ACs acrescentados aos três do `epics.md` (precedência `401` antes de `403`, papel lido do banco e não do token, `voltar` à prova de redirecionamento aberto, masthead por estado de sessão, `/conta` com logout que atualiza o cabeçalho, responsividade e não regressão dos 55 testes). Registrada a escolha de guardar a rota na página em vez de `middleware`, com o motivo — o `JWT_SECRET` não vai para o ambiente do frontend |
