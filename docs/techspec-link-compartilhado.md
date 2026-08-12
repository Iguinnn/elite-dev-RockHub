# Techspec — O link compartilhável do ingresso, e a revogação

**Data:** 2026-08-12 · **Cobre:** Stories 4.3 e 4.4 da Epic 4
**Formato:** ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As duas viram um documento só porque são **um recurso e seu ciclo de vida**: o `share_token` nasce
na 4.3 e morre na 4.4, na mesma coluna, no mesmo subrecurso e no mesmo arquivo de service.
Especificar em dois documentos deixaria a pergunta que mais importa — *compartilhar de novo gera
token novo ou devolve o mesmo?* — caindo no vão entre eles, e ela decide as duas.

---

## 1 · Escopo e commits

Dois commits, na ordem numerada. Cada um passa na suíte sozinho.

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para eu commitar** — sem escrever README, sem tocar no seguinte. Só emende o
próximo depois de eu mandar. Esta spec cobrir duas stories **não** autoriza implementá-las de uma
vez: o histórico do git é parte da avaliação, e o commit por story é o que a spec agrupada não pode
custar.

| Commit | Story | O que entrega |
|---|---|---|
| 1 | 4.3 | Migração de `share_token`, `gerar_share_token`, `POST /ingressos/{id}/compartilhamento`, a rota pública, o `<Canhoto>` extraído e a tela `/i/{token}` |
| 2 | 4.4 | `DELETE /ingressos/{id}/compartilhamento`, o `Botao` com variante destrutiva, o `<Confirmacao>` e o botão de revogar na ilha |

⚠️ **Uma janela consciente, e ela dura um commit.** Entre o commit 1 e o 2 existe link gerado sem
como revogar — a mesma forma da janela que abri entre a 2.4 e a 2.5, e pelo mesmo motivo: a ordem
dos ACs é essa, e fechá-la antes custaria escrever metade da 4.4 dentro da 4.3.

## 2 · O que existe hoje

A techspec de `docs/techspec-meus-ingressos.md` entregou o agregado inteiro do lado do dono:
`services/ingresso.py` com `listar` e `obter`, `schemas/ingresso.py` com `IngressoNaLista` e
`IngressoDetalhe`, as duas rotas em `cliente.py` sob `Depends(exigir_papel(CLIENTE))` (AD-9), e a
tela `/ingressos/{id}` desenhando o canhoto em duas colunas com o `QRCodeSVG`.

O `core/seguranca.py` já tem `gerar_nonce()` (`secrets.token_urlsafe(24)`), `montar_codigo()` e
`conferir_codigo()`. O `publico.py` é o router cujo critério declarado é **"não exige conta"**. O
`lib/api.ts` (`chamarApi`) é o caminho do navegador e repassa `opcoes` inteiras ao `fetch`. O
`Botao.tsx` tem uma variante só, e o docstring dele promete a segunda "quando o segundo aparecer".

O que **não** existe: a coluna `share_token`, qualquer rota que não seja `GET` ou `POST`, qualquer
confirmação de ação na interface — nem modal, nem `window.confirm` —, e nenhuma tela pública que
mostre dado de uma conta.

## 3 · Decisões, e o que descartei

**O `DELETE` entra no projeto, e o par vira o subrecurso `compartilhamento`.** Avaliei se valia
quebrar a superfície só-`GET`/`POST` e a resposta é que **não há padrão sendo quebrado**: nunca
houve operação com forma de remoção aqui. `POST /reservas/{id}/pagamento` não é "evitamos `DELETE`",
é um comando que de fato não é remoção de nada. Conferi o que poderia quebrar de verdade — o CORS é
`allow_methods=["*"]`, o `rewrites()` do `next.config.ts` repassa qualquer método, o `chamarApi`
aceita `method`, e o `erros.py` já mapeia `405` — e não quebra nada. Então:
`POST /ingressos/{id}/compartilhamento` cria, `DELETE` do mesmo endereço revoga. *Descartei*
`POST /ingressos/{id}/revogar`, que preservaria a uniformidade ao custo de esconder num verbo em
português a operação idempotente que o HTTP já nomeia — e que teria de ser explicada num comentário
em vez de ser lida no método.

**Compartilhar é idempotente: com link ativo, devolve o mesmo.** *Descartei* gerar token novo a cada
clique, que transformaria "compartilhar de novo" numa revogação silenciosa — cortando o acesso de
quem já recebeu o link **sem** a confirmação que o AC da 4.4 existe justamente para exigir. Revogar
é a única ação que invalida link, e é a única que pergunta antes.

**O `POST` responde `IngressoDetalhe`, e o schema ganha `share_token: str | None`.** A ilha troca o
estado inteiro em vez de remendar um campo, e o `GET /ingressos/{id}` passa a devolver o token
sempre que houver um — o dono reencontra o próprio link sem precisar recompartilhar. Esconder o
token de quem é dono do ingresso não protege coisa alguma: ele já é público para quem recebeu o
link, por construção (AD-8). *Descartei* um schema `LinkDeCompartilhamento` de um campo só, que
obrigaria a ilha a saber juntar duas respostas.

**Quem monta a URL é o navegador, não a API.** A resposta carrega o token; a ilha monta
`${window.location.origin}/i/${token}`. O backend não conhece — nem deve — o domínio do frontend, e
*descartei* acrescentar uma `FRONTEND_URL` à `Settings`: seria a primeira variável de ambiente cujo
valor errado produz um link que abre uma página em branco em vez de derrubar o processo, e ela
quebraria sozinha em cada Preview da Vercel, que tem domínio novo a cada deploy.

**A rota pública mora em `publico.py`, e o espaço de URL `/ingressos` fica partido em dois
arquivos.** O critério declarado daquele router é *ausência de autenticação*, não o recurso, e esta
é a primeira vez que um recurso tem uma face privada e uma pública. *Descartei* pendurá-la em
`cliente.py`, ao lado das irmãs: seria uma rota sem guarda de sessão dentro do arquivo cuja
invariante escrita é que toda rota dali tem uma — o tipo de exceção que faz a próxima pessoa
procurar a guarda em dois lugares.

**A visualização pública é o canhoto inteiro, e o `<Canhoto>` vira componente compartilhado.** Mesmo
`IngressoDetalhe`, com `titular_nome` e `usado_em` inclusive: quem abre o link vai entrar com ele, e
um canhoto que escondesse o titular ou fingisse que o ingresso ainda vale seria um segundo canhoto,
diferente do de verdade. **Isto não contradiz a decisão da 4.2** de não extrair `<Canhoto>` entre
`/reservas/{id}` e `/ingressos/{id}`: lá os dois endereços falavam de coisas diferentes — um da
compra, outro do ingresso — e desenhar o mesmo objeto nos dois obrigava quem lia a escolher qual era
o real. Aqui os dois endereços falam **do mesmo ingresso para pessoas diferentes**, e eles serem
idênticos é o requisito, não o defeito.

**O `Botao` ganha `variante`, exatamente como o docstring dele previu.** Revogar é a primeira ação
destrutiva do produto, e é o segundo consumidor que aquele comentário esperava desde a 1.2 —
`destrutivo` é fundo `--brasa`, do `DESIGN.md#botao`. O `<Confirmacao>` usa o `<dialog>` **nativo**
com `showModal()`: trava de foco, `Esc`, `::backdrop` e o resto da página inerte vêm de graça e
corretos, e *descartei* um `<div role="dialog">` à mão, que seria mais código para reimplementar
pior o que o navegador já faz. *Descartei também* o `window.confirm()`, que custaria zero e poria a
única caixa de diálogo do produto fora da identidade visual inteira.

**O diálogo aparece sem animação.** O `EXPERIENCE.md#Interaction Primitives` proíbe travessia e
libera só mudança de cor até 120ms, e o `CLAUDE.md` registra a espera do checkout como **a única
animação do produto** — uma segunda tornaria falsa uma frase escrita em dois arquivos. Aparecer
inteiro e parado é o mesmo comportamento que "sem *spinner*, a estrutura aparece com os fios no
lugar". Se você quiser o fade mesmo assim, é uma linha e vira a segunda exceção declarada.

**Copiar é acelerador, não o caminho.** O link aparece sempre como texto selecionável; o botão de
copiar só é renderizado quando `navigator.clipboard` existe. *Descartei* o botão sempre presente com
`catch` mudo: `clipboard` não existe fora de contexto seguro, e um botão que não faz nada é pior que
um botão que não está lá.

## 4 · Contrato

### Migração (commit 1)

`acrescenta_share_token_ao_ingresso`, a partir do head atual (`8b97ae6bae09`).

| Coluna | Tipo | Notas |
|---|---|---|
| `share_token` | `String(32)`, nulável, **índice único** | `NULL` = nunca compartilhado ou revogado |

`secrets.token_urlsafe(24)` → 32 caracteres, o mesmo tamanho do `nonce` e por engenharia igual: 192
bits não se adivinham. No Postgres, `NULL` **não colide com `NULL`** num índice único — milhares de
ingressos sem link convivem, e índice parcial seria complicação sem causa.

⚠️ `uv run alembic upgrade head` no banco de desenvolvimento **no mesmo passo** em que a migração é
criada, e conferir `alembic current` contra `alembic heads`. A suíte não avisa que faltou.

### `core/seguranca.py`

`gerar_share_token() -> str`, vizinho de `gerar_nonce()` e com o mesmo gerador. O docstring carrega a
diferença entre os dois em letra grande — ver *Armadilhas*.

### `POST /ingressos/{ingresso_id}/compartilhamento` → `200` com `IngressoDetalhe`

Exige `CLIENTE` (AD-9). Sem corpo. Com `share_token` nulo, gera e grava; com token ativo, devolve o
que já existe, sem escrever. `200` nos dois casos: um `201` na primeira vez informaria "foi agora"
a ninguém que lê.

### `DELETE /ingressos/{ingresso_id}/compartilhamento` → `204`

Exige `CLIENTE`. Grava `NULL` no `share_token`. **`204` também quando já não havia link** — o
`DELETE` é idempotente por definição, e quem pediu para o link não valer mais obteve exatamente
isso.

| Situação (nas duas rotas acima) | Status | Código |
|---|---|---|
| ingresso inexistente **ou** de outra pessoa | `404` | `INGRESSO_NAO_ENCONTRADO` |
| `{ingresso_id}` que não é UUID | `422` | (Pydantic) |

O `404` único é a disciplina do `obter`, e as duas condições vão no **mesmo `where`**.

### `GET /ingressos/compartilhados/{token}` → `200` com `IngressoDetalhe`

Em `publico.py`, sem sessão nenhuma. Busca por `Ingresso.share_token == token`; `None` é
`404 LINK_NAO_ENCONTRADO`. **Token revogado e token que nunca existiu são indistinguíveis** — mesmo
status, mesmo código, mesma frase. É o que faz a revogação ser um corte, e não um aviso de que algo
existiu ali.

`GET /ingressos/{id}` passa a devolver `share_token` — `str | None`, o único campo novo do
`IngressoDetalhe`.

### Frontend

**`components/Canhoto.tsx`** (commit 1) — o corpo do canhoto extraído de `/ingressos/[id]`, sem
`"use client"`: recebe `IngressoDetalhe` e desenha a ficha, o picote, o QR e o código. Sem
`<Link>` de voltar e sem a faixa de "já utilizado" — essas são chrome de cada página.

**`/i/[token]`** (commit 1) — dentro de `(site)`, com masthead: quem abre o link pode não ter conta,
e a casca já lida com visitante desde a 3.1. Server Component, `notFound()` no `nao-encontrado`, a
frase de indisponível no outro estado. Acima do canhoto, uma linha em `kicker` dizendo que é um
ingresso compartilhado — quem abre precisa saber que está vendo o ingresso de outra pessoa.
`lib/ingressos.ts` ganha `obterIngressoCompartilhado(token)`, no molde exato do `obterIngresso`.

**`components/CompartilharIngresso.tsx`** (ilha `"use client"`, commit 1) — recebe o ingresso como
prop inicial e guarda o `share_token` em estado. Sem link: botão *Compartilhar*. Com link: o
endereço em monoespaçada, o botão de copiar (quando houver `clipboard`) e, no commit 2, *Revogar
link*. Erros pelo `ErroDaApi`/`AvisoDeErro`, como os formulários. **`router.refresh()` depois de
cada mutação bem-sucedida.**

**`components/Confirmacao.tsx`** (commit 2) — `<dialog>` nativo, `showModal()`, título, uma frase de
consequência, `Cancelar` (secundário) e a ação em `Botao variante="destrutivo"`. Genérico por
props: nada de "revogar" escrito dentro dele.

## 5 · Critérios de pronto, por commit

**Commit 1 — 4.3.** O schema tem `ingresso.share_token`, nulável e com índice único; compartilhar
um ingresso meu devolve um token opaco e o link `/i/TOKEN`; **compartilhar duas vezes devolve o
mesmo token**; abrir o link **sem nenhuma sessão** mostra o canhoto com o QR; o `share_token` é
**diferente** do `codigo` de validação e não aparece dentro dele (AD-8); token inexistente devolve
`404 LINK_NAO_ENCONTRADO`; compartilhar ingresso de outra pessoa devolve `404
INGRESSO_NAO_ENCONTRADO`; a tela `/ingressos/{id}` continua desenhando o mesmo canhoto de antes da
extração.

**Commit 2 — 4.4.** Revogar apaga o `share_token` e o link antigo passa a responder `404`;
compartilhar depois de revogar gera um token **diferente** do primeiro; revogar duas vezes devolve
`204` nas duas; a ação abre confirmação, e cancelar não chama a API; o `<dialog>` fecha com `Esc` e
devolve o foco ao botão que o abriu; o botão destrutivo é `--brasa`, e o `Botao` sem `variante`
continua idêntico ao que era.

## 6 · Armadilhas

⚠️ **`share_token` e `nonce` saem do mesmo gerador e têm exposições opostas.** O `nonce` é
ingrediente secreto do HMAC e nunca sai do servidor; o `share_token` é feito para viajar por
WhatsApp. Trocar um pelo outro — ou logar o `nonce` "porque o outro a gente mostra" — entrega a
entropia da assinatura. Os dois docstrings dizem isso, em espelho.

⚠️ **A rota pública não valida assinatura, e não deve.** Ela é visualização (AD-8); o `share_token`
**não** substitui o HMAC do AD-5, e quem recalcula é a porta, na Epic 5. Chamar `conferir_codigo`
aqui daria a impressão de que o token autentica alguma coisa.

⚠️ **`/ingressos` mora em dois routers, e o `cliente.py` é registrado antes do `publico.py`.** O que
salva `/ingressos/compartilhados/{token}` é ter **três** segmentos contra os dois de
`/ingressos/{ingresso_id}`. Qualquer rota pública futura de dois segmentos sob `/ingressos` seria
engolida pela autenticada e voltaria `401` ou `422` — um erro que não menciona autenticação nenhuma.
Há teste provando a pública de pé sem sessão, pelo mesmo motivo que existe o da 3.2.

⚠️ **`router.refresh()` depois de compartilhar e de revogar.** A página é Server Component; sem o
refresh, o estado da ilha e o que o servidor renderizou divergem, e um `Voltar` do navegador mostra
o link revogado ainda ali. É o mesmo aviso que o `FormularioLogin` carrega desde a 1.4.

⚠️ **`showModal()`, nunca `show()`.** O segundo abre o `<dialog>` sem backdrop, sem travar o foco e
sem tornar a página inerte — parece funcionar e não é diálogo modal nenhum.

⚠️ **`navigator.clipboard` só existe em contexto seguro.** Em `http://` que não seja `localhost` ele
é `undefined`, e chamá-lo direto levanta `TypeError` dentro do `onClick`. O botão só é renderizado
quando existe; o link em texto é o caminho, não o plano B.
