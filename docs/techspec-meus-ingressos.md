# Techspec — Meus ingressos e o canhoto com o QR

**Data:** 2026-08-12 · **Cobre:** Stories 4.1 e 4.2 da Epic 4
**Formato:** ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As duas viram um documento só porque são o **grupo de leitura** do mesmo agregado: a lista e o
detalhe leem a tabela `ingresso` pelo mesmo caminho (reserva → cliente da sessão), com o mesmo
`404` de "não é seu" e o mesmo recorte de colunas. Especificar em dois arquivos duplicaria a
consulta e deixaria a fronteira entre o resumo e o canhoto — quem carrega o `codigo`, quem carrega
o `usado_em` — caindo no vão entre eles.

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
| 1 | 4.1 | Migração de `usado_em`/`validado_por`, `services/ingresso.py`, `GET /ingressos`, a tela `/ingressos` e o link no masthead |
| 2 | 4.2 | `GET /ingressos/{id}`, a tela do canhoto com o QR, e a tela da reserva paga enxugada |

⚠️ **Uma janela consciente, e ela dura até a Story 5.2.** O bloco *Utilizados* nasce no commit 1
com consulta, ordenação e tela prontas — e **vazio para sempre até a portaria existir**, porque
nada escreve `usado_em` antes do AD-6. Não é pendência: é a única ordem possível, já que os ACs da
4.1 pedem o bloco e a coluna é da mesma tabela. Ele é provado por teste que grava `usado_em` à mão.

## 2 · O que existe hoje

A 3.9 criou a tabela `ingresso` com sete colunas (`migrations/versions/20260812_e43874e0cf3a_*`) e a
emissão dentro da transação do pagamento (AD-14). O `app/api/cliente.py` tem as três rotas de
reserva, todas com `Depends(exigir_papel(PapelUsuario.CLIENTE))` na assinatura (AD-9). O
`services/reserva.py` já monta canhotos com `montar_codigo(id, assinatura)` em `_ingressos()`, e a
tela `/reservas/{id}` desenha um bloco por ingresso — **com o código em texto e sem QR**.

O `qrcode.react` entrou na 3.8 pelo QR do Pix, e o `Masthead.tsx` guarda o lugar do link
`Meus ingressos` num comentário desde a 1.4.

O que **não** existe: nenhuma rota lê `ingresso` fora da reserva que o gerou, não há
`services/ingresso.py`, e as colunas `usado_em` e `validado_por` do AD-6 não existem no schema.

## 3 · Decisões, e o que descartei

**As colunas `usado_em` e `validado_por` entram agora, na migração da 4.1.** A disciplina do projeto
é não criar coluna sem consumidor, e a partir daqui existe um: a leitura. *Descartei* deixá-las na
Story 5.2, como o docstring do modelo previa — o bloco *Utilizados* e a hora da entrada são dois ACs
da 4.1, e adiá-los deixaria a janela aberta por **seis stories**, não por um commit como a que abri
entre a 3.7 e a 3.8. *Descartei também* trazer só `usado_em`: as duas são a mesma migração e o mesmo
AD-6, e meia migração faria a 5.2 voltar a mexer na mesma tabela por uma coluna.

**Duas rotas: `GET /ingressos` e `GET /ingressos/{id}`, com dois schemas.** O ingresso é um agregado
com vida própria — é o que o docstring do modelo diz desde a 3.9 —, e é neste endereço que a 4.3
vai pendurar o compartilhamento. *Descartei* uma rota só, com a tela de detalhe filtrando a lista:
economizaria uma rota hoje e obrigaria a criá-la na story seguinte. Dois schemas pelo precedente
`EventoNaProgramacao` / `EventoPublico`: com um schema só, o `codigo` de entrada de N ingressos
trafegaria numa tela que não desenha nenhum. Não é vazamento — é o dono lendo o que é dele —, é
payload sem leitor.

**A lista chega chapada, e quem corta em dois blocos é a tela.** É o molde literal do `Meus eventos`
da 2.6, onde a API responde "quais são os meus" e a tela responde "o que interessa agora".
*Descartei* devolver `{ativos, utilizados}` nomeados pela API, que impediria a tela de discordar do
backend sobre a regra — e criaria uma segunda forma de listar recurso neste projeto, para uma
distinção que é um `usado_em IS NULL` de uma linha.

**"Ativo" é `usado_em IS NULL`, e nada mais.** Um ingresso de um show de ontem que ninguém leu na
porta continua em *Ativos*, no fim da lista. *Descartei* jogá-lo em *Utilizados* — diria que alguém
entrou com ele, o que é falso — e *descartei* um terceiro bloco "Encerrados", que é honesto e é AC
que não existe. Ordem: *Ativos* por data do evento crescente (o próximo primeiro); *Utilizados* por
hora de entrada decrescente, porque ali o que importa é a última vez que se entrou.

**O canhoto cheio existe num lugar só, e a tela da reserva paga vira confirmação.**
`/reservas/{id}` perde os blocos de canhoto e ganha a frase do protótipo mais o caminho para
`Meus ingressos`. *Descartei* extrair um `<Canhoto>` compartilhado entre as duas rotas: o mesmo
objeto desenhado em dois endereços obriga quem lê a decidir qual é o ingresso de verdade, e a tela
da reserva é sobre a **compra** — o que foi cobrado e o desfecho —, não sobre o que se apresenta na
porta. *Descartei também* deixar as duas como estão, que preservaria a 3.9 intacta ao custo de duas
versões do mesmo canhoto convivendo. O comentário que deixei na 3.9 já prometia o QR "junto do
canhoto cheio", em um lugar.

**O canhoto mostra o código inteiro; a lista mostra oito caracteres.** O `codigo` é
`ID.ASSINATURA` — cerca de 80 caracteres —, e o UX-DR9 pede que ele apareça em texto **onde é
apresentado**, que é o canhoto. Na lista ele é identificação visual, não dado de uso: saem os oito
primeiros caracteres do `id`, que a tela já tem. *Descartei* criar um campo `codigo_curto` no
contrato, cujo único consumidor seria decoração.

⚠️ **Isto decide uma coisa da Story 5.3**, e decido agora para não descobrir na porta: *digitar o
código* na portaria é **colar**, não datilografar oitenta caracteres. Um código curto digitável
seria coluna nova e um segundo mecanismo de verificação ao lado do HMAC — o oposto do AD-5.

**A leitura mora em `services/ingresso.py`, arquivo novo.** É onde a 4.3 e a 4.4 vão escrever o
`share_token`, e o agregado é outro. *Descartei* pendurar em `services/reserva.py`, que já passa de
800 linhas e atenderia duas epics. O topo do arquivo novo carrega o aviso do AD-14 em letra grande —
**este módulo lê e, da 4.3 em diante, escreve `share_token`; ele nunca cria ingresso** —, na mesma
forma como o `reserva.py` carrega o aviso do AD-3.

**As URLs são `/ingressos` e `/ingressos/{id}`.** *Descartei* `/meus-ingressos`, no espírito de
`/organizador/eventos`: lá o prefixo é o papel, e aqui o recurso já tem nome próprio — a mesma razão
pela qual `cliente.py` não tem `prefix`.

## 4 · Contrato

### Migração (commit 1)

`acrescenta_usado_em_e_validado_por_ao_ingresso`, a partir do head atual (`e43874e0cf3a`).

| Coluna | Tipo | Notas |
|---|---|---|
| `usado_em` | `DateTime(timezone=True)`, nulável | TIMESTAMPTZ em UTC (AD-11). Nulo = nunca validado |
| `validado_por` | `Uuid`, FK `usuario.id`, **sem `ondelete`**, nulável | quem leu na porta |

**Sem índice em nenhuma das duas.** O `UPDATE` da 5.2 é `WHERE id = :id AND usado_em IS NULL` —
busca por chave primária —, e o painel da 5.6 filtra por `evento_id`, que já é indexado. Índice
preventivo é peso sem gargalo demonstrado, e a disciplina é a mesma desde a 2.3.

⚠️ `uv run alembic upgrade head` no banco de desenvolvimento **no mesmo passo** em que a migração é
criada, e conferir com `alembic current` contra `alembic heads`. A suíte não avisa que faltou.

### `GET /ingressos` → `200` com `list[IngressoNaLista]`

Todos os ingressos de todas as reservas pagas de quem está na sessão, ordenados por
`evento.data_hora` **crescente**. Lista vazia é resposta legítima — nunca `404`.

```
id · evento_id · evento_nome · evento_data_hora · evento_local · setor_nome · usado_em
```

`evento_id` entra porque o item da lista leva ao show; `usado_em` é `datetime | None` e é a regra do
bloco. **Não entram** `titular_nome` nem `codigo`: nenhum dos dois é desenhado nesta tela.

A consulta é um `select(Ingresso)` com `join(Reserva)` — `Reserva.cliente_id == cliente.id` —, mais
`Evento` e `Setor` pelo `id`. **Não há filtro por `reserva.estado`**: ingresso só nasce dentro da
transação que marca `PAGA` (AD-14), então o estado não é uma segunda condição, é uma consequência.

### `GET /ingressos/{ingresso_id}` → `200` com `IngressoDetalhe`

```
id · evento_nome · evento_data_hora · evento_local · evento_cidade
setor_nome · titular_nome · codigo · usado_em
```

`codigo` é `montar_codigo(ingresso.id, ingresso.assinatura)` — a mesma função da 3.9, montada **a
partir da coluna, sem recalcular**. `usado_em` entra também aqui: um canhoto já utilizado que
parecesse válido é alguém sendo mandado para a fila à toa.

| Situação | Status | Código |
|---|---|---|
| ingresso inexistente **ou** de outra pessoa | `404` | `INGRESSO_NAO_ENCONTRADO` |
| `{ingresso_id}` que não é UUID | `422` | (Pydantic) |

O `404` único é a disciplina do `obter` da reserva e do `obter_do_organizador` da 2.6: distinguir
"não existe" de "não é seu" diria a quem varresse UUIDs quais deles são ingressos de alguém. As duas
condições vão no **mesmo `where`**, nunca um `get()` seguido de um `if`.

### Frontend

**`/ingressos`** (commit 1) — Server Component. Guardas literais do `/organizador/eventos`: sem
sessão, `redirect` para o login com `voltar`; papel diferente de `CLIENTE`, `redirect` para a raiz.
Dois blocos com `sec-titulo` (*Ativos*, *Utilizados*), fila de quatro colunas no molde do
`fila-listagem`: ficha de data, nome do show + `casa · setor`, prefixo do código em monoespaçada, e
estado à direita. Utilizados com `opacity: .45` e a hora da entrada no lugar do selo. Vazio: a frase
exata do `EXPERIENCE.md`, sem ilustração e sem botão (UX-DR8).

`lib/ingressos.ts` no molde do `lib/reservas.ts`: `cabecalhoDeSessao()` **fora** do `try`,
`unstable_rethrow(erro)` na primeira linha do `catch`, e os três estados
(`ok` / `nao-encontrado` / `indisponivel`). Nunca levanta.

O `Masthead` ganha `<NavLink href="/ingressos">Meus ingressos</NavLink>` quando
`usuario?.papel === "CLIENTE"`, **antes** de `Minha conta`, e o comentário que reservava o lugar sai.

**`/ingressos/{id}`** (commit 2) — canhoto em duas colunas com `2px dashed var(--fio)` no picote: à
esquerda a ficha (data por extenso, nome do show, casa e cidade, setor, titular); à direita, fundo
`--cal` com o QR e o código em monoespaçada, quebrado em blocos. `<QRCodeSVG value={codigo}
bgColor="#e4ebea" fgColor="#0b1618" level="L" />`, com no mínimo 180px — o payload tem ~80
caracteres, e o QR é o elemento de maior peso visual da tela. Abaixo de 900px, corpo e talão
empilham e o picote vira linha horizontal; o QR continua sobre `--cal` e do mesmo tamanho.

**`/reservas/{id}`** (commit 2) — o bloco `PAGA` perde os canhotos e fica com a confirmação mais
`<Link href="/ingressos">Ver meus ingressos</Link>`. O CSS órfão sai junto.

## 5 · Critérios de pronto, por commit

**Commit 1 — 4.1.** O schema tem `ingresso.usado_em` e `ingresso.validado_por`, nuláveis; `GET
/ingressos` devolve os ingressos de todas as compras do cliente da sessão e **nenhum** de outro
cliente; a lista separa ativos de utilizados, com o utilizado esmaecido e mostrando a hora da
entrada; quem nunca comprou vê a frase do UX-DR8, sem ilustração e sem botão grande; o corpo não
carrega `codigo` nem `titular_nome`; o link aparece no masthead só para `CLIENTE`.

**Commit 2 — 4.2.** O canhoto mostra evento, data, local, setor e titular à esquerda e o QR à
direita do picote; o QR está sobre `cal`, nunca sobre o breu; o código aparece também em texto
(UX-DR9); **decodificar o QR devolve exatamente `montar_codigo(id, assinatura)`** — provado por
teste sobre o valor passado ao componente, não por leitura de imagem; abaixo de 900px corpo e talão
empilham com o picote horizontal; ingresso de outra pessoa devolve `404
INGRESSO_NAO_ENCONTRADO`; a tela da reserva paga não desenha mais canhoto.

## 6 · Armadilhas

⚠️ **Não conte ingresso para derivar nada** (AD-13). Esta é a primeira tela que lista ingressos, e a
tentação nasce aqui: `COUNT(ingresso)` por setor é a resposta errada mais óbvia de escrever para
"quantos restam". Disponibilidade é `capacidade - vendidos`, sempre, e nesta epic ela nem aparece.

⚠️ **`join(Reserva)` e não um `cliente_id` novo em `ingresso`.** A coluna atalho parece tentadora e
duplicaria o dono em duas tabelas, com o dia em que discordam já marcado. `reserva_id` é indexado
desde a 3.9 exatamente para esta consulta.

⚠️ **O bloco *Utilizados* não tem produtor até a 5.2** — nada escreve `usado_em`. O teste que o
prova grava a coluna à mão; um teste que passe pelo fluxo real não existe ainda, e esperá-lo é
esperar a Epic 5.

⚠️ **`montar_codigo` a partir da coluna, sem recalcular** — o mesmo aviso do `_ingressos()` da 3.9.
Recalcular aqui daria o mesmo valor e esconderia o ponto: a coluna existe para montar o QR, e a
validação da portaria é que sempre recalcula (AD-5).

⚠️ **O QR de 80 caracteres não é o QR do Pix.** O do Pix é um código curto gerado na tela; este
carrega o `ID.ASSINATURA` inteiro, com muito mais módulos. Copiar o `size={148}` de lá deixa o
código denso demais para leitor de celular a meio metro.

⚠️ **A hora da entrada é renderizada no fuso de quem lê**, a partir de um TIMESTAMPTZ em UTC
(AD-11). O `usado_em` chega ISO-8601 com offset; comparar ou formatar como texto funciona por
acidente enquanto todos forem `Z`.
