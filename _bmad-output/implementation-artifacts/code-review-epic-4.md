# Code review — Epic 4 (Meus ingressos e compartilhamento)

**Data:** 2026-08-12 · **Alvo:** `Epic-4---Meus-ingressos-e-compartilhamento` contra `main`
**Diff:** 35 arquivos, +4.217 / −127 (4.195 linhas de código, fora documentação)
**Commits:** 4.1, 4.2, o fix do canhoto, 4.3 e 4.4

## Como este review foi diferente

**Escopo estreito, por pedido meu:** só o que quebra código ou derruba deploy, reportando
apenas Critical e High. Nada de estilo, nomenclatura, refactor ou cobertura genérica. A Epic 3
rodou nove subagentes e produziu 58 achados triados; aqui eu queria a fração que impede a epic
de ir para a `main`, e queria rápido.

**O recorte do diff foi por fronteira de autenticação**, não por tamanho: o que exige sessão
contra o que não exige. É a invariante nova desta epic — `/i/{token}` é a primeira tela do
produto que mostra dado de uma conta sem pedir login — e é onde o defeito caro moraria.

**As verificações mecânicas rodaram antes das camadas, e o resultado foi passado a elas.**
Suíte inteira, `next build`, `tsc --noEmit`, cadeia Alembic, `alembic current` contra `heads`.
Todas verdes. Dizer isso aos revisores evitou que gastassem a passagem reconfirmando o que já
estava fechado.

## Saldo

| | |
|---|---|
| Critical | **0** |
| High | **4** — todos corrigidos |
| Suíte | 449 → **451** |
| Camadas | 3 (backend, frontend, testes) |

Um dos quatro é defeito de código; três são testes que passavam sem provar. Nenhum bloqueava
deploy — o que bloquearia foi verificado executando, não lendo.

## A lição desta epic

**Achado de revisor vale o que a mutação provar.**

A camada de testes levantou o achado nº 1 afirmando que um `share_token` sequencial passaria nos
449 testes. Mutei para conferir e ela estava errada: com um contador, o `"1"` cai dentro do UUID
que compõe o código e um teste existente pega por acaso. Mas mutando para `secrets.token_urlsafe(4)`
— 32 bits, força-bruta viável numa tarde — os 53 testes de compartilhamento e migração passam
**todos**.

O achado era real; a justificativa dele não era. Se eu tivesse aceitado a explicação sem mutar,
teria escrito o teste certo pelo motivo errado — e o registro no README diria uma coisa que não
acontece. Os quatro achados abaixo foram confirmados por mutação, um a um.

## Os quatro achados

### 1 · Nenhum teste provava a entropia do `share_token` — HIGH

**Onde:** ausência em `tests/`. `gerar_share_token` não aparecia em arquivo de teste nenhum,
enquanto `gerar_nonce` tinha unitários desde a 3.9.

**Por que importa:** o `share_token` é o **único** cadeado de `GET /ingressos/compartilhados/{token}`,
que é público e devolve o `IngressoDetalhe` inteiro — `codigo` `ID.ASSINATURA` incluso, que é o que
vale na porta (AD-5), mais `titular_nome`. A techspec escreve "192 bits não se adivinham" como a
razão de o endereço só chegar a quem recebeu o link, e essa frase não estava fixada em asserção
nenhuma.

**Prova por mutação:** com `secrets.token_urlsafe(4)`, os 53 testes de `test_compartilhamento.py`
e `test_migracoes.py` passam. As asserções existentes (`token != codigo`, `token not in codigo`,
`token != nonce`, tokens distintos entre ingressos) são todas satisfeitas por um token de 32 bits,
e o teste de migração só lê `nullable`/`unique` — `String(32)` aceita um caractere.

**Correção:** `test_share_token_tem_32_caracteres_e_nao_se_repete`, em `test_ingresso.py`, vizinho
dos testes do `nonce` de propósito: os dois saem do mesmo gerador e têm exposições opostas, e o
contraste só ensina lado a lado.

### 2 · `compartilhar` perdia escrita em corrida — HIGH

**Onde:** `app/services/ingresso.py`, a função `compartilhar`.

O par ler→escrever não era atômico: `if ingresso.share_token is None` em Python, gravação depois,
sem trava. Com o mesmo ingresso aberto em duas abas, as duas transações leem `NULL`, a primeira
grava o token A, a segunda grava B por cima. O banco fica com B.

**O que fazia isso doer de verdade** é a soma com duas coisas que estão certas isoladamente:
`expire_on_commit=False` faz a resposta devolver o A que está em memória, e o `useState` da ilha
não é resetado pelo `router.refresh()`. A aba de A copia `/i/A`, manda por WhatsApp, e quem abre
lê "esse link não vale mais" — sem ninguém ter revogado nada.

**Correção:** `UPDATE ... WHERE id = :id AND share_token IS NULL` mais `sessao.refresh(ingresso)`,
no precedente literal do AD-3. A segunda transação casa zero linhas e o `refresh` devolve o token
vencedor às duas abas. Descartei `SELECT ... FOR UPDATE` no `_carregar_do_cliente`: aquele helper
serve também as duas leituras puras, e travar linha nelas cobraria de toda a epic o preço de uma
corrida que só existe aqui.

**Prova por mutação:** revertida a função ao read-then-write, o teste novo
`test_duas_conexoes_compartilhando_o_mesmo_ingresso_geram_um_token_so` falha. Ele é o segundo teste
da suíte fora do `TestClient`, pelo mesmo motivo do primeiro: a fixture `cliente` amarra o app a uma
sessão só, e a corrida nunca aconteceria ali dentro.

### 3 · O teste do "sem recalcular" passaria se o código recalculasse — HIGH

**Onde:** `tests/test_meus_ingressos.py::test_o_codigo_e_montado_a_partir_da_coluna_sem_recalcular`.

A asserção comparava a resposta contra `montar_codigo(id, assinatura)` com a assinatura que a
própria fixture havia gravado pelo HMAC. No caminho feliz, **ler a coluna e recalcular produzem o
mesmo valor** — o teste que existe para provar a disciplina do AD-5 passava nos dois sentidos.

É o mesmo padrão do teste de forja que o review da Epic 3 pegou, e por isso vale registrar: aquele
adulterava o último caractere de um base64 e em ~4,7% dos casos não adulterava nada.

**O que estaria em jogo:** a coluna deixar de ser a fonte do QR, e as duas rotas de leitura — a do
dono e a pública — passarem a depender do `TICKET_SIGNING_SECRET` em tempo de leitura. Trocar o
segredo no painel da Railway mudaria o QR exibido, em vez de só invalidar a validação na porta.

**Correção:** gravar na coluna um valor que o HMAC nunca produziria e exigir que ele apareça na
resposta. **Prova por mutação:** trocado o `_montar_detalhe` por `assinar_ingresso(...)`, só este
teste falha — os outros 51 do arquivo passam.

### 4 · O `404` unificado das rotas de escrita só tinha metade dos casos — HIGH

**Onde:** `tests/test_compartilhamento.py`, os testes de `POST` e `DELETE` com ingresso alheio.

A techspec declara, para as duas rotas, "inexistente **ou** de outra pessoa → `404
INGRESSO_NAO_ENCONTRADO`", e a disciplina anti-oráculo exige que sejam indistinguíveis. Só o ramo
"de outra pessoa" tinha teste; nenhum chamava as rotas com um UUID bem-formado e inexistente, e não
havia o par `alheio.json() == inexistente.json()` que o `GET` já tinha.

Estava correto por as três rotas passarem pelo `_carregar_do_cliente` — mas era exatamente essa
suposição que nenhuma asserção registrava.

**Prova por mutação:** posto um `sessao.get(Ingresso, id)` antes do helper "para melhorar a
mensagem", a rota vira oráculo de "esse UUID é ingresso de alguém?" e o teste corrigido cai.

## O que as camadas verificaram e estava limpo

Registrado porque a ausência de achado aqui é resultado, não omissão.

**A rota pública não pode ser cacheada.** O `prerender-manifest.json` traz `dynamicRoutes: []` e só
`/_global-error` e `/icon.png` em `routes` — nenhuma rota do app é prerenderizada, porque o layout
`(site)` renderiza o `Masthead`, que chama `cookies()`. Não há como o canhoto de uma pessoa ser
servido a outra por cache de CDN. Sem `middleware.ts`, sem `vercel.json`, sem `revalidate`,
`dynamic` ou `generateStaticParams` em lugar nenhum. Era o risco mais caro da epic.

**`expire_on_commit` não repete a Epic 3.** `SessaoLocal` e a fábrica do `conftest.py` são
idênticas (`autoflush=False, expire_on_commit=False`), e a fixture `cliente` faz `expire_all()` por
requisição. A divergência que escondeu o bug do pagamento está fechada — e reaparece nesta epic só
como parte da *correção* do achado nº 2, nunca como defeito.

**`Canhoto.tsx` sem `"use client"` está correto.** O `QRCodeSVG` do `qrcode.react@4.2.0` usa apenas
`useMemo`, hook suportado no dispatcher RSC; `useState`/`useEffect` estão no `QRCodeCanvas`, que não
é usado. Era o tipo de coisa que estoura em runtime e não em build.

**Autorização.** As três rotas do dono têm `Depends(exigir_papel(CLIENTE))` e nenhuma reescreve o
`where` — todas passam pelo `_carregar_do_cliente`. O `nonce` não aparece em schema, resposta ou log
(só em `core/seguranca.py`, no modelo e na emissão). A rota pública é a única sem dono, e é
intencional.

**Roteamento.** `/ingressos/compartilhados/{token}` sobrevive por ter três segmentos contra os dois
de `/ingressos/{ingresso_id}`, com `cliente.py` registrado antes. Correto hoje, e frágil por
construção — a armadilha está escrita no `publico.py`.

## Fora de escopo, registrado sem virar achado

- **`Botao.tsx` espalha `{...props}` depois do `className`.** Nenhum dos dez consumidores passa
  `className` hoje, então a armadilha é latente. Vale lembrar ao acrescentar o onze.
- **A janela de hidratação de `/ingressos/{id}`.** Antes do `useEffect` rodar, o `<code>` mostra
  `/i/TOKEN` sem o domínio. O botão *Copiar* não existe nesse quadro, então não dá para copiar
  errado por clique — mas quem selecionar o texto à mão nesse intervalo cola um link quebrado.
  Defeito de UX, não crash nem vazamento.
- **`test_compartilhar_duas_vezes_devolve_o_mesmo_token`** prova que o token não muda, não que a
  segunda chamada não escreveu. Um `UPDATE` do mesmo valor passaria. Não é quebra de segurança, e a
  igualdade do corpo inteiro cobre o que a spec promete a quem usa.

## Fora da numeração das stories

O QR do canhoto voltou de `bgColor="var(--cal)"`/`fgColor="var(--breu)"` para os hex
`#e4ebea`/`#0b1618` que a techspec da 4.2 pedia. Eles viram atributo `fill` do SVG, e o modo de um
`var()` não resolver ali é a cor cair para o preto padrão — QR preto sobre preto, que nenhuma suíte
vê e que só falha na fila da porta, no leitor de celular de outra pessoa. O canhoto é a única
superfície do produto que não pode seguir o tema: leitor de QR precisa do contraste fixo.
