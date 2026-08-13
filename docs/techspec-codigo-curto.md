# Techspec — o código do ingresso encolhe para 8 caracteres

**Data:** 2026-08-12 · **Escopo:** `core/seguranca.py`, `models/ingresso.py`, a emissão em
`services/reserva.py`, `services/ingresso.py`, uma migração e o `Canhoto`
**Formato:** mudança avulsa, sem story. Um commit, fora da numeração da Epic 5 —
precedente de [techspec-filtro-do-catalogo.md](techspec-filtro-do-catalogo.md)

---

## 1 · Escopo e commits

| Commit | O que entra |
|---|---|
| 1 | Código de 8 caracteres em base32 de Crockford, derivado do mesmo HMAC; migração que calcula o código dos ingressos existentes, apaga `assinatura` e renomeia `titular_nome`; o canhoto passando a mostrar o nome da conta |

Não é story porque não é escopo de story: nenhuma das 38 previu isto. É consequência de uma
decisão de produto que eu tomei ao escrever a spec da validação na porta — o código de 80
caracteres torna o campo manual da Story 5.3 inutilizável na fila.

🛑 **Um commit, e pare.** Rode a suíte inteira, mostre o resultado e avise que está pronto
para eu commitar — sem escrever README e sem começar a 5.2. A techspec da validação
(`docs/techspec-validacao-na-porta.md`) **assume este commit já aplicado**.

## 2 · O que existe hoje

- **`assinar_ingresso(id, evento_id, nonce)`** devolve `HMAC-SHA256` em base64url sem
  padding: 43 caracteres. Guardado em `ingresso.assinatura` (`String(64)`).
- **`montar_codigo(id, assinatura)`** concatena `ID.ASSINATURA` — 36 + 1 + 43 = **80
  caracteres**, que é o conteúdo do QR e o que o `Canhoto` desenha em 20 blocos de quatro.
- **`conferir_codigo(codigo, evento_id, nonce)`** parte no ponto, valida o UUID, exige
  ASCII e compara com `hmac.compare_digest`. **Nunca foi chamada por ninguém** — ela nasceu
  na 3.9 esperando a Epic 5.
- **`ingresso.titular_nome`** guarda o nome digitado no checkout (`PagamentoEntrada.nome`),
  e é o único campo do checkout que sobrevive à requisição (decisão da 3.8).
- **`nonce`** (`token_urlsafe(24)`) é o que dá entropia por ingresso. Ele fica.

## 3 · Decisões, com a alternativa descartada

### O código encolhe para 8 caracteres, e isso é decisão de produto

O campo manual da Story 5.3 existe para quando a câmera falha. Com 80 caracteres, ele não
serve: são ~1 minuto por pessoa, lidos do celular de outra pessoa, com fila esperando e um
erro de digitação a cada tentativa. Um fallback que ninguém consegue usar é um fallback que
não existe — e o AC diz, com todas as letras, "para não travar a fila quando a câmera
falha".

`9K4M-7QX2` são 40 bits. **Descartei** manter os 80 caracteres e declarar a limitação no
README: é a saída barata, e ela troca a usabilidade da única tela do produto com contexto
de uso declarado (em pé, no escuro, uma mão) por não mexer em código de outra epic.

Sobre os 40 bits: adivinhar um código exige **já estar logado como uma conta de portaria
escalada naquele evento**, porque a rota da validação recusa antes de olhar o ingresso
(AD-7). Quem tem essa credencial não precisa forjar código nenhum — está autorizado a
validar. **Descartei** 10 e 12 caracteres: dariam mais margem contra um ataque que a
autorização já barra, ao custo de exatamente o que esta mudança existe para comprar.

### O código continua sendo HMAC — truncado, não sorteado

`codigo = crockford32(HMAC-SHA256(segredo, id + evento_id + nonce))[:8]`, guardado numa
coluna única. A validação acha a linha **pelo código** e **recalcula** o HMAC; divergência
é `INVALIDO`. É o mecanismo que o AD-5 descreve, e é o mesmo que o TOTP faz há vinte anos
— HMAC-SHA1 truncado a seis dígitos.

**Descartei** um valor aleatório à moda do `share_token`, que é mais simples e, no mesmo
tamanho, indistinguível em segurança. Ele custaria a frase que dá título ao AD-5: *"o
código do ingresso é um token assinado, **não** um identificador"*. Com o HMAC truncado eu
reescrevo a representação do AD-5; com o sorteio, eu o revogo. E o recálculo continua
valendo a pena mesmo com a busca pelo código: ele é o que impede a coluna de virar oráculo
de assinatura no dia em que alguém conseguir escrever no banco.

### Base32 de Crockford, e é ela que resolve o AC da caixa

Alfabeto de 32 símbolos **sem `I`, `L`, `O` e `U`**: os três primeiros porque `1`/`I` e
`0`/`O` se confundem quando alguém lê o código em voz alta na fila, e o `U` porque tirá-lo
evita que o gerador produza palavrão por acaso.

Isso resolve de graça um AC que, com base64, era **fisicamente impossível**: "não diferencia
maiúsculas de minúsculas". Base64url é sensível a caixa — `aB` e `Ab` são bytes diferentes
—, e um `.upper()` na entrada destruiria toda assinatura legítima. Em Crockford não existe
minúscula no alfabeto, e a normalização de entrada (maiúsculas, `I`/`L` → `1`, `O` → `0`,
fora espaços e hífens) é o comportamento correto, não um risco.

### O ingresso é da conta; `titular_nome` vira `pagador_nome`

Decisão do Igor: o ingresso está no nome de quem tem a conta. O nome do checkout é o de
quem pagou — a namorada compra na conta dela, eu ponho meu cartão.

A coluna é renomeada para `pagador_nome`, e o campo `titular_nome` das respostas
(`IngressoDetalhe`, `IngressoSaida`) passa a vir de `usuario.nome`, pelo join
`Ingresso → Reserva → Usuario`. O canhoto acompanha, senão o mesmo ingresso mostra um nome
na tela de quem chega e outro na tela de quem valida, e a conferência com o documento fica
sem resposta.

**Descartei duas saídas.** Deixar a coluna com o nome antigo e preencher a resposta com
outra coisa: coluna e campo com o mesmo nome significando pessoas diferentes é o tipo de
armadilha que só se descobre depurando. E **apagar a coluna**, já que ela fica sem nenhuma
tela: ela é o registro de quem pagou, que é o que a Story 3.8 decidiu persistir, e a
ausência de leitor hoje não a torna ruído.

⚠️ Consequência: `obter_por_share_token` passa a precisar do join com `Reserva`, que o
docstring dela hoje diz explicitamente **não** fazer. O link compartilhado passa a mostrar
o nome da conta que comprou — mesma classe de exposição do nome que ele já mostrava.

### Nenhum ingresso emitido é invalidado

O código novo é derivável das colunas que já existem (`id`, `evento_id`, `nonce`), então a
migração calcula o valor de cada linha em vez de zerar a tabela. **Descartei** apagar os
ingressos existentes — o Igor disse que não haveria problema, mas dez linhas de migração de
dados evitam a frase "invalidei ingressos" no README, e o mesmo código serve de prova de
que a derivação funciona.

## 4 · Contrato

**Migração nova** (`ingresso`), nesta ordem:

1. `ADD COLUMN codigo VARCHAR(8) NULL` + índice **único**
2. Preenche `codigo` para cada linha, calculando do `id`, `evento_id` e `nonce` — o
   `TICKET_SIGNING_SECRET` sai de `obter_settings()` dentro da própria migração
3. `ALTER COLUMN codigo SET NOT NULL`
4. `DROP COLUMN assinatura`
5. `RENAME COLUMN titular_nome TO pagador_nome`

`core/seguranca.py`:

```python
_ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford: sem I, L, O, U
TAMANHO_DO_CODIGO = 8                            # 40 bits

def _hmac_do_ingresso(ingresso_id, evento_id, nonce) -> bytes: ...   # extraído
def gerar_codigo(ingresso_id, evento_id, nonce) -> str: ...          # trunca em 5 bytes
def normalizar_codigo(bruto: str) -> str | None: ...                 # None se não for código
def conferir_codigo(codigo, ingresso_id, evento_id, nonce) -> bool:  # recalcula + compare_digest
```

`assinar_ingresso` e `montar_codigo` **saem**, junto de `SEPARADOR_DO_CODIGO`.
`normalizar_codigo` devolve `None` para qualquer entrada que não seja 8 símbolos do
alfabeto depois da normalização — é ela que a Story 5.3 chama antes de tocar no banco.

`models/ingresso.py`: `assinatura` sai; entra `codigo: Mapped[str]`, `String(8)`,
`unique=True`, `index=True`. `titular_nome` vira `pagador_nome`.

`services/reserva.py`, na emissão: `codigo=gerar_codigo(...)`, `pagador_nome=dados.nome`, e
`IngressoSaida.codigo` passa a ser `ingresso.codigo` (nada de montar). `titular_nome` da
resposta vem de `cliente.nome`, que a função já tem em mãos.

`services/ingresso.py`: `_montar_detalhe` recebe o `Usuario` e devolve `titular_nome=
usuario.nome`; as quatro consultas do arquivo ganham o join com `Usuario`, inclusive a
pública.

**Frontend:** `Canhoto.tsx` não muda uma linha — o `codigo.match(/.{1,4}/g)` já transforma
`9K4M7QX2` em `9K4M 7QX2`.

## 5 · Critérios de pronto

- [ ] `gerar_codigo` devolve 8 símbolos do alfabeto de Crockford, e o mesmo trio
      (`id`, `evento_id`, `nonce`) devolve sempre o mesmo código
- [ ] `normalizar_codigo` aceita `9k4m 7qx2`, `9K4M-7QX2` e `9K4M7QX2` como o mesmo valor;
      converte `I`/`L` em `1` e `O` em `0`; devolve `None` para tamanho errado, símbolo
      fora do alfabeto e entrada não-ASCII
- [ ] `conferir_codigo` recusa código de assinatura adulterada — e o teste **não** adultera
      só o último caractere (armadilha registrada no review da Epic 3)
- [ ] Migração aplicada com `uv run alembic upgrade head` **no banco de desenvolvimento**,
      conferida com `alembic current` contra `alembic heads`
- [ ] Ingresso emitido **antes** da migração continua válido: teste que grava uma linha no
      formato antigo, roda a migração e valida o código resultante
- [ ] `ingresso.codigo` é único no banco — teste que tenta gravar dois iguais
- [ ] `IngressoDetalhe.titular_nome` traz o nome da **conta**, inclusive na rota pública do
      link compartilhado
- [ ] `uv run pytest` inteiro verde (Docker no ar), número final registrado — a suíte estava
      em 451 antes da Story 5.1, que somou os testes dela
- [ ] `npm run build` e `tsc --noEmit` limpos
- [ ] Comentário no `sprint-status.yaml`, no bloco da Epic 5, apontando para esta spec
- [ ] Igor avisado de que está pronto para commit — **nenhum comando git é executado por
      agente**

## 6 · Armadilhas

⚠️ **Colisão de código é um `500` no meio do pagamento se ninguém tratar.** Com o índice
único, dois códigos iguais viram `IntegrityError` dentro da transação que marca a reserva
`PAGA`. A chance é ínfima (40 bits, poucos ingressos), e o desfecho é péssimo: pagamento
aprovado que estoura. A emissão sorteia **outro `nonce` e recalcula**, dentro de um
`begin_nested()` (SAVEPOINT) — sem o savepoint, o `IntegrityError` já invalidou a transação
inteira e não há o que reaproveitar.

⚠️ **A migração de dados precisa do `TICKET_SIGNING_SECRET`.** Se ele não estiver no
ambiente, ela falha — e falhar é o comportamento certo, porque o app já se recusa a subir
sem ele. Na Railway, isso significa que o deploy roda a migração com o mesmo segredo de
produção; girar o segredo **depois** da migração invalida os códigos calculados nela, como
sempre invalidou.

⚠️ **`compare_digest` com `str` só aceita ASCII** — fora dele levanta `TypeError`, não
devolve `False`. A guarda continua necessária, e a `normalizar_codigo` é quem a exerce
agora: qualquer coisa fora do alfabeto sai como `None` antes de chegar ao `compare_digest`.

⚠️ **O `U` não está no alfabeto.** Quem for testar à mão não invente código com `U` e
conclua que a validação está quebrada — ela está certa.

⚠️ **Renomear coluna quebra teste que constrói `Ingresso(...)` na mão.** Os testes das
Stories 3.9, 4.1, 4.2, 4.3 e 4.4 fabricam ingressos direto no modelo; todos passam a
escrever `pagador_nome` e `codigo`. É mecânico, mas é onde a suíte vai reclamar primeiro.

⚠️ **`expire_on_commit=False` continua valendo.** Depois de gravar o ingresso, o objeto em
memória não recarrega sozinho — a mesma armadilha que o code review da Epic 3 achou no
pagamento e a 4.3 achou de novo no `share_token`.

---

**Fontes:** `ARCHITECTURE-SPINE.md` (AD-5, AD-7) · `backend/app/core/seguranca.py` ·
`backend/app/models/ingresso.py` · `backend/app/services/reserva.py` (emissão) ·
`backend/app/services/ingresso.py` · `backend/app/schemas/pagamento.py` ·
RFC 4226 (truncamento de HMAC) · Crockford base32
