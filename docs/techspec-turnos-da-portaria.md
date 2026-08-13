# Techspec — turnos da portaria

**Data:** 2026-08-12 · **Escopo:** Story 5.1, a primeira da Epic 5
**Formato:** techspec no lugar de arquivo de story (`CLAUDE.md`, *Techspec no lugar de story*)

---

## 1 · Escopo e commits

| Commit | Story | O que entra |
|---|---|---|
| 1 | 5.1 · Ver onde eu trabalho hoje | `GET /portaria/eventos`, a casca própria da portaria em `/portaria`, a lista de turnos com o portão fechado antes da hora, `/portaria/conta`, e o login passando a mandar a portaria para a casa dela |

Uma story, um commit — mas techspec assim mesmo, e a decisão é minha: a 5.1 não é
"mais uma listagem". Ela cria a terceira casca do frontend, muda o fluxo de acesso
da Story 1.4 e decide a régua de tempo que a Epic 5 inteira vai herdar. Isso é
material de decisão, não de tarefa.

🛑 **Um commit por vez, e pare.** Terminado o commit, rode a suíte inteira, mostre o
resultado e avise que está pronto para eu commitar — sem escrever README, sem tocar
na 5.2. A regra vale mesmo aqui, onde a spec cobre uma story só: o próximo passo é
outra spec, não o próximo arquivo.

**Fora desta spec:** a rota de validação (5.2), a tela do leitor (5.3), os quatro
vereditos (5.4), a câmera (5.5) e o contador do turno (5.6). Quatro decisões que já
respondi e que pertencem à próxima spec ficam registradas na seção 3 para não se
perderem no caminho.

## 2 · O que existe hoje

- **A escala já existe e ninguém a consome.** `evento_portaria` é uma `Table` do Core
  (`models/evento.py`), gravada na publicação desde a Story 2.5, e o docstring do
  módulo diz com todas as letras: "ninguém consome a escala ainda: validar ingresso é
  a Epic 5". Esta story é a primeira leitura dela.
- **`usado_em` e `validado_por` já estão no banco**, adiantadas na Story 4.1. O AC1 da
  5.2 nasce satisfeito, e **esta story não tem migração nenhuma**.
- **`exigir_papel(PapelUsuario.PORTARIA)` já funciona** — a dependência do AD-9 é
  genérica desde a 1.6, e o papel `PORTARIA` nunca foi usado em rota alguma.
- **Duas contas de portaria no seed** (`portaria@rockhub.dev` e `portaria2@rockhub.dev`,
  senha `rockhub123`), criadas na 2.5 exatamente para dar o cenário do AD-7.
- **Duas cascas de frontend**: `(site)` com o masthead e `(entrada)` só com a marca.
  A `/conta` mora no `(site)`, com a guarda de sessão na própria página — este projeto
  não tem `middleware`, e o motivo está no docstring dela.
- **O login sempre volta para `?voltar=`**, com padrão `/`. Ele nunca olhou o papel.

## 3 · Decisões, com a alternativa descartada

### A portaria ganha casca própria em `/portaria`, e não um item no masthead

O caminho barato era acrescentar um `NavLink` de *Turnos* no `Masthead`, do jeito que
`ORGANIZADOR` e `CLIENTE` ganharam os deles. **Descartei** porque o `EXPERIENCE.md` é
explícito nos dois sentidos: "Portaria — navegação própria, sem o header do cliente" e
"a única superfície projetada primeiro para telas pequenas". Quem está na porta está em
pé, à noite, com uma mão, e o masthead de jornal come a metade de cima de um celular
para oferecer *Início* — uma programação de shows que essa pessoa não vai comprar.

A casca é `src/app/portaria/layout.tsx`, **sem grupo de rotas**. `(site)` e `(entrada)`
existem porque agrupam caminhos de topo diferentes sob uma casca comum; aqui tudo mora
sob `/portaria`, e o segmento já é o grupo. Um `(porta)/portaria/` seria pasta a mais
sem nada a mais.

**A navegação tem dois itens e para por aí**: *Turnos* e *Minha conta*. É o que você
pediu, e é o que a superfície comporta — quem trabalha na porta tem uma função só.

### O nome de quem está na porta aparece na casca

Contraria o `Masthead`, que decidiu na 1.6 não mostrar o nome de quem está logado
(`DESIGN.md#Components/masthead` é literal, e dado da pessoa é conteúdo da `/conta`).
Aqui é diferente e o protótipo já desenhava assim (`Ana Ribeiro · Portaria`): o celular
da porta é compartilhado, duas contas de portaria existem no seed de propósito, e "quem
está validando" é a primeira coisa que se confere quando o resultado sai errado.

### O login manda a portaria para `/portaria` — mas só quando ninguém pediu outra coisa

O `?voltar=` continua **soberano**. Ele existe desde a 1.4 para quem foi interrompido no
meio de alguma coisa, e sobrescrevê-lo com um destino por papel quebraria exatamente o
caso que ele resolve. A regra nova só vale quando o parâmetro está **ausente**.

Isso obriga uma mudança sutil no `/login`: hoje `caminhoInternoSeguro` devolve `"/"` como
padrão, e a página perde a diferença entre "ninguém pediu" e "pediram a raiz". O
parâmetro passa a viajar como `string | undefined` até o formulário.

**Descartei** deixar a portaria cair na raiz e se virar com o menu: ela entraria numa
tela de compra de ingressos, sem nenhum item de navegação que leve ao trabalho dela.

### A lista não corta por tempo — e o portão abre 2 horas antes

São duas coisas, e vale separar.

**A lista mostra todos os eventos em que a conta foi escalada**, sem peneira de data,
ordenados por `data_hora` crescente. As rotas públicas cortam em `data_hora >= agora`, e
copiar esse corte aqui seria o pior erro possível: **a portaria trabalha exatamente do
outro lado dele**. Às 21h30 de um show que começou às 21h, o evento já sumiu de
`listar_programacao` — se a lista de turnos usasse a mesma regra, o turno desapareceria
no minuto em que a fila começa a andar. O argumento é o mesmo que deixou
`listar_do_organizador` sem filtro: é o inventário de quem lê.

**O portão abre `data_hora - 2h`.** Antes disso o item não é link e traz a frase "O evento
ainda não começou"; a partir dali vira link para `/portaria/eventos/{id}`.

⚠️ **Aqui eu me afastei da sua resposta de propósito, e é a única linha desta spec em que
isso acontece.** Você disse "a partir da hora que começa o evento". Um portão exatamente
em `data_hora` **trava o roteiro de avaliação**: `publicar` recusa data no passado
(`EVENTO_NO_PASSADO`, decidido no review da Epic 2), o seed cria só contas, e as rotas
públicas escondem o evento assim que ele começa. Quem avalia teria de publicar um show,
comprar o ingresso, **esperar o relógio virar** e só então validar. Com a janela de 2h,
publicar para daqui a uma hora deixa a porta aberta na hora — e ainda é o comportamento
certo do mundo real, onde a portaria chega antes de o portão abrir, nunca no instante do
primeiro acorde. É uma constante de uma linha: se você preferir zero, é trocar o número.

### O corte de tempo é da tela, não do contrato

`TurnoDaPortaria` devolve `data_hora` e mais nada derivado — nenhum `aberto: bool`. Quem
compara com o relógio é a página, com o `cache()` do React, no precedente literal da
Story 2.6: "a API responde quais são os meus eventos; o que interessa agora é leitura, e
o relógio que decide é o de quem lê".

**Descartei** mandar o booleano no contrato. Ele parece mais seguro e não é: o portão é
uma conveniência operacional, não uma invariante — um ingresso continua sendo um ingresso
duas horas antes do show, e nada de ruim acontece se alguém digitar a URL. Invariante
desta epic é o vínculo do AD-7, e essa se cumpre no `403` da rota. Se a 5.2 decidir barrar
validação fora da janela, ela calcula a própria regra no servidor — e essa decisão é dela,
não desta tela.

### `Minha conta` da portaria é a mesma da `/conta`, extraída em componente

O conteúdo é idêntico: nome, e-mail, papel e sair. **Descartei** as duas saídas fáceis —
linkar para `/conta`, que jogaria a portaria de volta na casca de jornal que esta story
existe para evitar; e copiar as vinte linhas, que é como se ganha duas telas de conta que
divergem no dia em que uma delas mudar. `components/DadosDaConta.tsx` sai da página atual
e passa a ser renderizado pelas duas, com o CSS junto.

### O item aberto já linka para uma tela que ainda não existe

Janela consciente de **dois commits**: `/portaria/eventos/{id}` nasce na 5.3. Mesma forma
da janela entre a 2.4 e a 2.5, e da fila da 3.1 que apontou para `/eventos/{id}` por três
stories. **Descartei** entregar o item sem link: "escolher rápido onde vou trabalhar" é a
story inteira, e um cartão que não leva a lugar nenhum não a demonstra. Fica registrado no
`sprint-status.yaml` e fecha na 5.3.

### Guardadas para a próxima spec (5.2), já decididas

- **Os quatro vereditos respondem `200`**, com `{resultado, ...detalhe}` — `ErroDeDominio`
  só carrega `{codigo, mensagem}` e não teria onde pôr a hora da primeira entrada.
- **`EVENTO_ERRADO` não diz de qual show o ingresso é.** Sua decisão, contra o
  `EXPERIENCE.md` e o protótipo: uma portaria não escalada num evento não tem por que
  receber o nome dele de volta.
- **Código de ingresso inexistente é `INVALIDO`**, colapsado com assinatura divergente.
- **A rota é `POST /portaria/eventos/{evento_id}/validacoes`**, com o evento no caminho —
  é o que permite o `403` do AD-7 sair de uma dependência, e não de um `if` no corpo do
  handler, que o AD-9 proíbe.
- **A câmera da 5.5 usa `@zxing/browser`.** A `qrcode.react` que já está no
  `package.json` desde a 4.2 só **desenha** QR; decodificar do vídeo é o problema oposto.
  A `BarcodeDetector` nativa custaria zero bytes e não existe no Safari do iPhone, o que
  jogaria metade dos celulares da fila no campo manual.

## 4 · Contrato

**Sem migração.** Nada de `alembic revision` nesta story.

### Backend

`app/schemas/evento.py` — schema novo:

```python
class TurnoDaPortaria(BaseModel):
    id: UUID
    nome: str
    data_hora: datetime
    local: str
    cidade: str | None
```

Sem `capacidade`, `vendidos` ou `setores`: número exato é da 5.6, e o `response_model` é
onde o UX-DR7 se garante — disciplina da 3.1 em diante.

`app/services/evento.py` — função nova, vizinha de `listar_portarias` (o outro lado da
mesma tabela):

```python
def listar_escalados(sessao: Session, portaria: Usuario) -> list[TurnoDaPortaria]:
    ...
    select(Evento)
      .join(evento_portaria, evento_portaria.c.evento_id == Evento.id)
      .where(
          evento_portaria.c.usuario_id == portaria.id,
          Evento.publicado_em.is_not(None),
      )
      .order_by(Evento.data_hora)
```

O `publicado_em IS NOT NULL` entra pela mesma razão da `listar_programacao`: hoje não há
como existir rascunho com escala (publicação e escala são a mesma transação da 2.4/2.5),
e no dia em que houver, a condição já vale.

`app/api/portaria.py` — arquivo novo:

```python
router = APIRouter(prefix="/portaria", tags=["portaria"])

@router.get("/eventos", response_model=list[TurnoDaPortaria])
def meus_turnos(
    portaria: Usuario = Depends(exigir_papel(PapelUsuario.PORTARIA)),
    sessao: Session = Depends(obter_sessao),
) -> list[TurnoDaPortaria]: ...
```

`app/main.py` — `include_router(portaria.router)`. O prefixo `/portaria` não colide com
nada; não há a armadilha de ordem que `/ingressos` criou na 4.3.

**Erros:** `401` sem sessão, `403` com papel diferente — os dois já vêm da dependência.
Lista vazia é `200 []`, nunca erro.

### Frontend

| Arquivo | O que é |
|---|---|
| `src/lib/turnos.ts` | `listarTurnos()` no molde do `lib/portarias.ts`: estado discriminado `ok` / `indisponivel` / `sem-sessao`, **nunca levanta**, e repassa o cookie com `cabecalhoDeSessao()` |
| `src/app/portaria/layout.tsx` | Casca: logotipo, `Nome · Portaria`, nav de dois itens com `NavLink`. Coluna única |
| `src/app/portaria/page.tsx` | A lista. Guardas de sessão e papel, os três estados de `listarTurnos`, o vazio e o portão |
| `src/app/portaria/conta/page.tsx` | Guarda + `<DadosDaConta>` |
| `src/components/DadosDaConta.tsx` | Extraído de `(site)/conta/page.tsx`, com o CSS module junto |
| `src/app/(site)/conta/page.tsx` | Passa a renderizar o componente extraído |
| `src/app/(entrada)/login/page.tsx` | `voltar` vira `string \| undefined`; o link de cadastro usa `voltar ?? "/"` |
| `src/components/FormularioLogin.tsx` | Lê o `papel` do corpo do login e escolhe o destino quando `voltar` é `undefined` |

Frases da tela, literais (`EXPERIENCE.md#Vazio` e sua definição):

- vazio: **"Você não foi escalado para nenhum evento."**
- portão fechado: **"O evento ainda não começou"**

Alvos de no mínimo 44px em qualquer item clicável (UX-DR6).

## 5 · Critérios de pronto (commit 1 — Story 5.1)

- [ ] `GET /portaria/eventos` devolve só os eventos da escala de quem está na sessão,
      ordenados por `data_hora` crescente, com nome, data/hora, casa e cidade
- [ ] Evento em que a conta **não** foi escalada não aparece — teste com as duas contas
      de portaria do seed, que existem para isso
- [ ] `401` sem sessão e `403` para `CLIENTE` e `ORGANIZADOR`, vindos da dependência
- [ ] Evento passado **continua** na lista (é o corte que as rotas públicas fazem e esta
      não faz — teste explícito, senão alguém "uniformiza" depois)
- [ ] A tela `/portaria` renderiza a lista, o vazio com a frase exata, e o estado de
      indisponibilidade sem derrubar a página
- [ ] Item com `data_hora` a mais de 2h no futuro **não é link** e traz "O evento ainda
      não começou"; item dentro da janela é link para `/portaria/eventos/{id}`
- [ ] `/portaria` e `/portaria/conta` rebatem para o login sem sessão e para `/` com papel
      errado, no molde de `/organizador/eventos`
- [ ] A casca da portaria **não** mostra o masthead do `(site)`
- [ ] Login de conta `PORTARIA` **sem** `?voltar=` cai em `/portaria`; **com** `?voltar=`
      obedece o parâmetro; cliente e organizador continuam caindo onde caíam
- [ ] `<DadosDaConta>` extraído, e a `/conta` do `(site)` continua idêntica na tela
- [ ] `npm run build` e `tsc --noEmit` limpos
- [ ] `uv run pytest` inteiro verde (Docker no ar), número final registrado — parte de 451
- [ ] Comentário no `sprint-status.yaml`: a janela de dois commits até a 5.3
- [ ] Igor avisado de que está pronto para commit — **nenhum comando git é executado por
      agente**

## 6 · Armadilhas

⚠️ **O `?voltar=` sumido é o jeito de esta story falhar em silêncio.** Se o `/login`
continuar aplicando o padrão `"/"` antes de repassar, o formulário nunca vê `undefined` e
o destino por papel simplesmente não acontece — sem erro, sem log, com a portaria caindo na
programação como sempre caiu. É a primeira coisa a conferir se o comportamento não
aparecer.

⚠️ **`router.refresh()` continua vindo antes do `push`.** O comentário que já está no
`FormularioLogin` explica: o masthead é Server Component e serviria a versão em cache. A
casca da portaria depende da sessão do mesmo jeito.

⚠️ **`searchParams` é `Promise` no Next 16**, e o `AGENTS.md` do `frontend/` avisa que esta
não é a versão de Next que você conhece — leia `node_modules/next/dist/docs/` antes de
mexer em layout ou em tipagem de rota. Os layouts existentes usam `LayoutProps<"/">`; a
casca nova segue a mesma tipagem gerada.

⚠️ **O `fetch` de Server Component não herda o cookie da requisição.** Sem
`cabecalhoDeSessao()`, o backend responde `401`, `listarTurnos` devolve `sem-sessao` e o
sintoma aponta para o lugar errado. Foi o que aconteceu no `lib/portarias.ts` e está
escrito lá.

⚠️ **Uma leitura do relógio por requisição, com `cache()`** — nunca `Date.now()` solto no
corpo do componente. Duas leituras podem discordar sobre o evento que está exatamente na
borda das 2h, e o item apareceria clicável no cabeçalho e travado no corpo. O
`instanteDaRequisicao` de `/organizador/eventos` é o precedente para copiar.

⚠️ **`cidade` é anulável** (`String(120)`, `nullable=True`). A ficha tem que aguentar o
`None` sem imprimir "null" nem um separador solto.

⚠️ **`redirect()` levanta `NEXT_REDIRECT`** e não pode ficar dentro de `try/catch` — o
docstring da `/conta` já explica. As guardas ficam como `if`, com o `try` do lado do
`lib/`.

⚠️ **Sem migração nesta story**, então não rode `alembic revision`. A pendência do
`CLAUDE.md` sobre `upgrade head` continua valendo para a próxima que criar uma — e a 5.2
também não cria, porque as colunas vieram na 4.1.

⚠️ **A janela de 2h é o que torna a Epic 5 demonstrável.** Ela precisa aparecer no roteiro
da Story 6.4 mais ou menos assim: publicar um show para daqui a uma hora, comprar o
ingresso **antes** da hora marcada (as rotas públicas escondem o evento a partir de
`data_hora`), e validar na porta em seguida.

---

**Fontes:** `_bmad-output/planning-artifacts/epics.md` (Story 5.1) ·
`ARCHITECTURE-SPINE.md` (AD-7, AD-9) · `EXPERIENCE.md` (navegação da portaria, vazios,
UX-DR6) · `mockups/proto-jornal-noturno.html` (telas `t-portaria` e `t-scanner`) ·
`backend/app/models/evento.py`, `services/evento.py`, `core/dependencias.py` ·
`frontend/src/app/(site)/organizador/eventos/page.tsx`, `(site)/conta/page.tsx`,
`(entrada)/login/page.tsx`, `lib/portarias.ts`
