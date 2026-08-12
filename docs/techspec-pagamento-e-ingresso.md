# Techspec — expiração, pagamento e emissão do ingresso

**Data:** 2026-08-12 · **Cobre:** Stories 3.7, 3.8 e 3.9 da Epic 3
**Formato:** primeira techspec agrupada do projeto. Ver `CLAUDE.md`, seção *Techspec no lugar de story*.

As três viram um documento só porque os próprios ACs as costuram na mesma função. A expiração da
3.7 dispara dentro da rota que a 3.8 cria; a emissão da 3.9 acontece na mesma transação da
transição para `PAGA` (AD-14). Especificar isso em três arquivos deixaria as decisões de fronteira
— pagamento que chega em reserva vencida, pagamento reprocessado que não pode emitir de novo —
caindo no vão entre eles.

---

## 1 · Escopo e commits

Três commits, na ordem numerada. Cada um passa na suíte sozinho.

🛑 **Um commit por vez, e pare.** Terminado um commit, rode a suíte inteira, mostre o resultado e
**avise que está pronto para eu commitar** — sem escrever README, sem tocar no seguinte. Só emende o
próximo depois de eu mandar. Esta spec cobrir três stories **não** autoriza implementá-las de uma
vez: o histórico do git é parte da avaliação, e o commit por story é o que a spec agrupada não pode
custar.

| Commit | Story | O que entrega |
|---|---|---|
| 1 | 3.7 | `expirar_vencidas()` no service e a chamada dela em `criar()` |
| 2 | 3.8 | `PaymentGateway`, `POST /reservas/{id}/pagamento`, os estados `PAGA`/`RECUSADA`, a colheita no pagamento e a tela de checkout |
| 3 | 3.9 | Migração da tabela `ingresso`, emissão dentro da transação, HMAC do código, canhotos na tela |

⚠️ **Uma janela consciente, de um commit.** O AC1 da 3.7 (*reserva vencida que eu tento pagar vira
`EXPIRADA` e devolve `409`*) acontece dentro da rota que só nasce no commit 2. Depois do commit 1 a
3.7 está cumprida pelo lado da reserva (AC2) e do "não existe worker" (AC3); o AC1 fecha no commit
seguinte. É a mesma janela que abri entre a 2.4 e a 2.5, e pelo mesmo motivo: fechá-la agora
significaria escrever a rota de pagamento dentro da story da expiração.

## 2 · O que existe hoje

A 3.5 criou `reserva` e `item_reserva` com os cinco estados do AD-4 em `String(20)` + `CHECK`. A
3.6 entregou `POST /reservas` e `GET /reservas/{id}` em `app/api/cliente.py`, com o service em
`app/services/reserva.py` fazendo o `UPDATE` condicional do AD-3, o `PRAZO_DE_RESERVA_MINUTOS = 10`
e a tela `/reservas/{id}` com o cronômetro.

O que **não** existe: nada lê `expira_em` para decidir coisa alguma, nenhuma reserva sai de
`PENDENTE`, e não há tabela de ingresso. `EstadoReserva` já declara `PAGA`, `RECUSADA` e `EXPIRADA`
— o contrato de saída os aceita desde a 3.6, e nenhum deles é produzível ainda.

## 3 · Decisões, e o que descartei

**A colheita só varre os setores do pedido.** `WHERE item_reserva.setor_id IN (...)`, usando o
`ix_item_reserva_setor_id` que a 3.5 criou exatamente para isto. *Descartei* varrer o evento inteiro
ou o banco inteiro: as duas fazem trabalho sobre itens que ninguém pediu, e o AD-4 descreve o
gatilho como "alguém pedir estoque **daquele setor**".

**Rota de leitura não colhe.** Só `POST /reservas` e o pagamento escrevem. A consequência é
visível e eu a aceito: um setor pode aparecer **"Esgotado"** na página com reservas já vencidas, e
quem clicar em reservar consegue mesmo assim. *Descartei* colher no `GET /eventos/{id}`, que deixaria
a tela sempre honesta ao custo de transformar as quatro rotas públicas em escrita — a raiz é Server
Component e renderiza a cada visita. O próprio AD-4 já registra essa folga como consequência aceita.

**A colheita roda na mesma transação de quem a disparou.** Segue a convenção do projeto: service que
escreve abre e fecha a transação. Se a reserva nova terminar em `409`, a colheita é desfeita junto e
refeita na próxima tentativa — desperdício inofensivo. *Descartei* transação própria, que daria dois
`commit` a um request e dois donos de transação ao mesmo service.

**`POST /reservas/{id}/pagamento`.** Ação sobre um recurso que já tem endereço. *Descartei*
`POST /pagamentos` (inventa um recurso sem tabela) e `PATCH /reservas/{id}` com o estado no corpo,
que deixaria o cliente **nomear** o estado de destino — o oposto do AD-4.

**A recusa é `402 Payment Required`.** Recusa de pagamento não é conflito de estado: é a resposta do
gateway, e o 402 existe para exatamente isto. *Descartei* o `409` das outras recusas do domínio; ele
seria mais consistente na tabela de status, e menos preciso onde importa. O corpo continua
`{"erro": {"codigo", "mensagem"}}`, sem exceção ao formato único do `core/erros.py`.

**O checkout pede Nome, E-mail, CPF e telefone, e escolhe entre cartão e Pix.** Escolher cartão
expande o formulário; escolher Pix mostra um QR e um código aleatório com o botão **"cobrança
paga"**. É a decisão que mais muda a tela: o avaliador não precisa digitar cartão para completar a
compra. *Descartei* o checkout de um campo só — tecnicamente suficiente para o AD-10, e visivelmente
uma maquete.

**Nada disso é persistido, exceto o Nome.** E-mail, CPF e telefone são validados no formato, usados
na tela e descartados: não crio coluna para eles. Guardar CPF de gente é dado sensível sem nenhum
consumidor neste sistema. O Nome vira `ingresso.titular_nome`, vem preenchido com o da conta e é
editável — quem compra pode estar comprando para outra pessoa.

**O CPF valida só o formato, sem dígito verificador.** O algoritmo do DV rejeita `111.111.111-11` e
a maioria dos números que alguém inventa na hora, o que brigaria de frente com o aviso de usar dados
fictícios. *Descartei* a validação completa; a decisão vai comentada no código para não parecer
esquecimento.

**O Pix não existe no backend.** O QR e o código copia-e-cola são gerados na tela, aleatórios, e não
atravessam para lugar nenhum: o backend recebe `meio: PIX` e aprova. *Descartei* simular cobrança
Pix no servidor — seria mentira com custo de manutenção, e o aviso na tela diz com todas as letras
que a cobrança é fictícia. **O caminho da recusa continua sendo o cartão** (AD-10, final `0002`), e é
ele que o roteiro do README vai mandar o avaliador exercitar.

**`TICKET_SIGNING_SECRET` é variável própria.** *Descartei* reusar o `JWT_SECRET`: segredo com dois
usos é o que impede girar um sem derrubar o outro — trocar a chave de sessão invalidaria todo
ingresso já emitido.

**A coluna `assinatura` guarda o valor só para montar o QR.** A validação da portaria (Epic 5)
**sempre recalcula**, como manda o AD-5, e assinatura divergente é recusada sem consultar o banco. A
coluna nunca é fonte da verdade. Consequência aceita: girar o segredo invalida os ingressos antigos,
que é o comportamento correto de um segredo rotacionado.

**A biblioteca de QR é `qrcode.react`**, entrando um story antes do previsto por causa do Pix. Gera
SVG no cliente, sem chamada de rede, e o canhoto da Story 4.2 reusa o mesmo componente.
*Descartei* gerar no backend como data-URI, que engordaria o payload do ingresso e traria uma
dependência Python para um problema de renderização.

## 4 · Contrato

### Migração (commit 3)

Tabela `ingresso`, exatamente as sete colunas do AC:

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | `Uuid` PK | UUIDv4, nunca sequencial (AD-5) |
| `reserva_id` | FK `reserva.id`, **sem `ondelete`** | apagar reserva paga é recusado pelo banco; indexado (lido pela Epic 4) |
| `evento_id` | FK `evento.id`, sem `ondelete` | indexado — é o `where` da 5.6 |
| `setor_id` | FK `setor.id`, sem `ondelete` | **sem índice**: nenhuma story planejada filtra por ele |
| `titular_nome` | `String(120)` | do campo Nome do checkout |
| `assinatura` | `String(64)` | base64url do HMAC |
| `nonce` | `String(32)` | `secrets.token_urlsafe(24)`, por ingresso |

Sem `criado_em`: o ingresso nasce na transação do pagamento, e nenhuma story lê a hora de emissão —
mesma disciplina que deixou `setor` e `item_reserva` sem a coluna. As colunas `usado_em` e
`validado_por` do AD-6 são **da Epic 5**, e não estão aqui de propósito.

### Configuração

`TICKET_SIGNING_SECRET` entra no `Settings` com valor de exemplo e validador que recusa o exemplo em
produção — mesma forma do `JWT_SECRET`. Entra também no `.env.example`.

⚠️ **Ação no painel da Railway antes do merge da epic**, junto com a conferência do `unaccent` da 3.2.

### `POST /reservas/{id}/pagamento` → `200` com `ReservaSaida`

Corpo (`PagamentoEntrada`): `nome`, `email`, `cpf`, `telefone`, `meio` (`CARTAO` | `PIX`) e, quando
`meio == CARTAO`, `numero_cartao`, `nome_no_cartao`, `validade`, `cvv` — exigidos por
`model_validator`, nunca gravados, nunca logados.

| Situação | Status | Código |
|---|---|---|
| reserva inexistente ou de outra pessoa | `404` | `RESERVA_NAO_ENCONTRADA` |
| `PENDENTE` com `expira_em` no passado | `409` | `RESERVA_EXPIRADA` — vira `EXPIRADA`, estoque volta, nada é cobrado |
| já `PAGA`, `RECUSADA` ou `CANCELADA` | `409` | `RESERVA_NAO_PENDENTE` |
| cartão terminado em `0002` | `402` | `PAGAMENTO_RECUSADO` — vira `RECUSADA`, estoque volta |
| aprovado | `200` | reserva `PAGA`, com os ingressos no corpo |

### `ReservaSaida` ganha `ingressos: list[IngressoSaida]`

Lista vazia enquanto a reserva não é `PAGA`. `IngressoSaida` carrega `id`, `titular_nome`,
`setor_nome` e `codigo` (`ID.ASSINATURA`). Nada de `capacidade`, `vendidos` ou disponibilidade
continua atravessando (UX-DR7, AD-13). *Descartei* criar rota nova para os ingressos: a reserva paga
já é o endereço da confirmação, e "Meus ingressos" é a Epic 4.

### A ordem dentro do service (commit 2 + 3)

```
1. carrega a reserva por (id, cliente_id)                  → 404
2. UPDATE reserva SET estado='EXPIRADA'
     WHERE id AND estado='PENDENTE' AND expira_em < now()
   rowcount == 1 → devolve o estoque dos itens             → 409 RESERVA_EXPIRADA
3. estado != 'PENDENTE'                                    → 409 RESERVA_NAO_PENDENTE
4. gateway.autorizar(reserva, meio) → Aprovado | Recusado
5. Recusado:  UPDATE ... estado='RECUSADA' WHERE estado='PENDENTE'
              rowcount == 1 → devolve o estoque            → 402 PAGAMENTO_RECUSADO
   Aprovado:  UPDATE ... estado='PAGA'     WHERE estado='PENDENTE'
              rowcount == 0 → alguém chegou primeiro, não emite nada
              rowcount == 1 → emite um ingresso por unidade, mesma transação (AD-14)
6. commit
```

Devolver estoque também é `UPDATE` condicional (AD-3, que vale para **toda** escrita em estoque):
`SET vendidos = vendidos - :q WHERE id = :id AND vendidos >= :q`.

### Frontend

`/reservas/{id}` ganha o formulário, o seletor de meio, a área que expande, o QR do Pix, o aviso de
dados fictícios e — quando `PAGA` — os canhotos no lugar do cronômetro. O cronômetro continua
informando sem piscar e sem mudar de cor (EXPERIENCE.md, *cronômetro de reserva*).

## 5 · Critérios de pronto, por commit

**Commit 1 — 3.7.** Reserva vencida em um setor libera o estoque para outra pessoa reservar; a
liberação acontece **antes** da tentativa; a transição para `EXPIRADA` é condicionada a `PENDENTE` e
provada por `.rowcount`; uma varredura do projeto não encontra worker, cron nem tarefa agendada.

**Commit 2 — 3.8.** Cartão comum aprova e a reserva vira `PAGA`; cartão terminado em `0002` devolve
`402 PAGAMENTO_RECUSADO`, deixa a reserva `RECUSADA` e o estoque de volta; Pix aprova pelo botão;
pagar reserva vencida devolve `409 RESERVA_EXPIRADA` sem cobrar; o service depende de
`PaymentGateway`, nunca da implementação (AD-10); a tela mostra o tempo restante e o aviso de dados
fictícios.

**Commit 3 — 3.9.** O schema tem a tabela `ingresso` com as sete colunas; uma reserva recém-paga
nasce com um ingresso por unidade, cada um com `id` e código próprios, na mesma transação da
transição (AD-14); o código tem formato `ID.ASSINATURA` com HMAC-SHA256 do segredo do servidor
(AD-5); pagamento reprocessado não cria ingresso adicional; assinatura adulterada falha na
verificação **sem consultar o banco**.

## 6 · Armadilhas

⚠️ **Ler `setor.vendidos` para dentro do Python continua proibido**, inclusive na devolução. A
tentação muda de forma aqui: `vendidos - quantidade` calculado em Python parece seguro porque
"devolver nunca estoura". Continua sendo AD-3 quebrado, e continua passando em todo teste
sequencial.

⚠️ **A corrida do pagamento não se prova pelo `TestClient`.** A fixture `cliente` amarra o app a uma
sessão só; o teste de reprocessamento precisa de duas `Session` em conexões distintas, com commit e
limpeza — foi o que a 3.6 aprendeu na corrida da reserva.

⚠️ **O gateway é chamado antes da transição.** Duas requisições simultâneas podem ambas autorizar, e
é o `UPDATE` condicional que decide quem emite ingresso — `rowcount == 0` significa "alguém chegou
primeiro", não erro. É exatamente isso que faz o AC de reprocessamento ser verdade por construção.

⚠️ **`expira_em` não é apagado ao pagar.** Ele é o prazo que valeu, não um campo que expira e some;
quem diz se o prazo ainda importa é o `estado`. A tela ramifica pelo estado, nunca pelo relógio.

⚠️ **Comparação de assinatura usa `hmac.compare_digest`**, nunca `==`.
