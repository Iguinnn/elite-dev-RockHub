# Decisões técnicas

Rascunho da seção do README voltada a quem vai avaliar o projeto. Explica **por que** as coisas
são como são. O contrato técnico completo está em
[ARCHITECTURE-SPINE.md](../_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md);
aqui está a versão em linguagem de gente.

---

## Portaria é escala de trabalho, não nível de permissão

O desafio pede três papéis: organizador, cliente e portaria. A leitura óbvia é tratá-los como
níveis de permissão — e foi aí que apareceu um problema que o enunciado não menciona.

Se o papel de portaria for só uma permissão, **qualquer conta de portaria valida ingresso de
qualquer evento do sistema**. O papel diz o que a pessoa pode fazer, mas não *onde*. Numa
plataforma com vários organizadores, isso é um furo de autorização.

Então o usuário de portaria é **escalado para eventos específicos pelo organizador**, no momento
da publicação. Ao entrar, ele vê apenas os eventos em que trabalha, escolhe um, e só então começa
a ler QR. Uma conta sem vínculo com aquele evento recebe `403` antes mesmo de o ingresso ser
consultado.

Um efeito colateral bem-vindo: como a validação sempre acontece dentro do contexto de um evento
escolhido, o retorno "evento errado" que o desafio pede **surge naturalmente do modelo**, em vez
de ser uma regra inventada à parte.

## O catálogo externo é copiado, não consultado ao vivo

A API Discovery da Ticketmaster permite 5 requisições por segundo e 5.000 por dia. Se a listagem
de eventos consultasse a API a cada visita, a aplicação quebraria com pouquíssimo uso, e ainda
ficaria refém da disponibilidade de um serviço de terceiro no meio de uma compra.

A Ticketmaster é chamada **apenas** quando o organizador busca uma atração para publicar. No ato
da publicação, os dados usados são gravados no banco. Nenhuma tela de cliente ou de portaria toca
a API externa.

Isso também resolve um problema de integridade: o nome, a imagem e o local que aparecem no
ingresso são os mesmos do momento da compra, mesmo que a Ticketmaster mude o registro depois.

## O mesmo lugar não é vendido duas vezes

O ponto de atenção não é o caso normal, é o simultâneo: duas pessoas comprando o último ingresso
no mesmo instante.

A solução não usa lock na aplicação nem verificação prévia. Toda mudança de estoque é um único
comando condicional no banco:

```sql
UPDATE setor SET vendidos = vendidos + :quantidade
 WHERE id = :setor_id AND vendidos + :quantidade <= capacidade
```

Se o comando afetar zero linhas, não havia estoque, e a transação é revertida. Como a verificação
e a escrita acontecem no mesmo comando, não existe intervalo entre "conferir" e "gravar" — que é
exatamente onde a corrida aconteceria. A tabela ainda carrega uma constraint `CHECK` que torna o
estado inválido impossível de gravar, mesmo que um bug futuro tente.

## A reserva segura o estoque e expira sozinha

A reserva nasce **já consumindo estoque**, com validade de 10 minutos. Isso evita dois problemas
opostos: alguém abandonar o checkout e prender o lugar para sempre, e duas pessoas chegarem ao
pagamento acreditando que o mesmo lugar é delas.

Pagamento recusado, reserva expirada ou cancelada devolvem o estoque.

## O QR não pode ser forjado

O código do ingresso não é um identificador sequencial — se fosse, bastaria incrementar um número
para inventar ingressos.

O QR carrega `ID.ASSINATURA`, onde a assinatura é um HMAC-SHA256 calculado com um segredo que só
existe no servidor. Na portaria, a assinatura é recalculada: se não bate, o ingresso é rejeitado
como inválido **sem sequer consultar o banco**. Sem o segredo, não há como produzir um código que
passe.

## O mesmo ingresso não é validado duas vezes

Mesmo raciocínio do estoque. Validar é um comando condicional:

```sql
UPDATE ingresso SET usado_em = now(), validado_por = :portaria_id
 WHERE id = :id AND usado_em IS NULL
```

Zero linhas afetadas, com o ingresso existindo, significa que ele já tinha sido usado. Dois
leitores escaneando o mesmo ingresso no mesmo instante não conseguem passar os dois, porque o
banco só deixa um dos comandos encontrar a linha ainda não utilizada.

## O link de compartilhamento

Compartilhar gera um token aleatório e opaco, guardado no ingresso e revogável pelo dono a
qualquer momento. A rota pública mostra o ingresso com o QR, sem exigir login.

**Isso significa que quem recebe o link consegue entrar no evento** — e é intencional. É assim que
Sympla e Eventim funcionam: você manda o ingresso para quem vai com você. A proteção não está em
esconder o QR, está no fato de o ingresso valer **uma entrada só** e o dono poder revogar o link.

O token de compartilhamento é separado da assinatura de validação. Ele dá acesso à visualização,
nunca substitui a prova de autenticidade do ingresso.

## Login e sessão

A senha é guardada como hash **Argon2id**, que é a recomendação atual da OWASP. Nunca em texto,
nunca com hash reversível.

O token de sessão viaja em **cookie `httpOnly`**, e não em `localStorage`. A diferença importa: com
`httpOnly`, o JavaScript da página não consegue ler o token, então uma falha de XSS não vira roubo
de sessão. De quebra, é o que permite os Server Components do Next.js lerem a sessão direto no
servidor, sem precisar buscar tudo pelo navegador.

A sessão dura 8 horas — tempo suficiente para um turno de portaria sem relogar. Não implementei
refresh token: expirou, faz login de novo. Num sistema real com sessões longas isso seria
necessário, mas aqui só adicionaria complexidade sem mudar o que está sendo avaliado.

## Pagamento simulado

Não há transação financeira real. O gateway é uma interface com implementação falsa, e a regra de
recusa é determinística para que a avaliação consiga testar os dois caminhos:

| Cartão | Resultado |
|---|---|
| Número terminando em `0002` | **Recusado** |
| Qualquer outro número | Aprovado |

A convenção é a mesma dos cartões de teste da Stripe.

---

## O que eu deliberadamente não fiz, mesmo sabendo que sistema real faria

Fiz uma varredura procurando decisões que só se pagam em escala, e cortei o que sobrou:

**Não criei camada de repositórios.** O padrão em projeto grande é `router → service → repository`.
Aqui ficou `router → service → models`, porque a `Session` do SQLAlchemy já é, na prática, um
repositório com unidade de trabalho. A camada extra viraria um monte de função de repasse sem
separar nada de novo. Num sistema com várias fontes de dados ou com troca de ORM no horizonte, eu
teria feito diferente.

**A reserva expira de forma preguiçosa, sem worker.** Em vez de uma tarefa agendada varrendo
reservas vencidas, elas são colhidas no momento em que alguém as toca: ao tentar pagar, ou quando
outra pessoa pede estoque daquele setor. O efeito prático é o mesmo — no instante em que o estoque
importa, ele está correto — e evita manter um processo rodando na Railway só para isso. Num sistema
com relatórios em tempo real de ocupação, o worker faria falta.

**Não implementei refresh token.** Explicado acima.

## O que ficou de fora, e por quê

O desafio pede que o que não estiver pronto seja dito. Estes foram cortes conscientes de prazo,
não esquecimentos:

| O quê | Por quê |
|---|---|
| **Mapa de assentos** | O desafio aceita venda por quantidade em setores, que foi o caminho escolhido. A plataforma é focada em shows — pista, área VIP e camarote — onde numeração de assento não é o padrão |
| **Tela de editar evento** | O vínculo com a portaria só pode ser definido na publicação. Num sistema real seria necessário adicionar e remover porteiros a qualquer momento |
| **Cancelamento pelo cliente** | O modelo de dados já suporta (a reserva tem estado `CANCELADA` e devolve estoque); faltam o endpoint e a tela |
| **TMDb e catálogo de filmes** | A plataforma foi deliberadamente focada em shows. Suportar filmes exigiria um segundo modelo de sessão e sala |
