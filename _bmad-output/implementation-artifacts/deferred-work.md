# Trabalho adiado

Achados reais que não foram consertados no momento em que apareceram, com o
motivo de terem ficado para depois. Cada entrada diz onde está e o que fecharia.

## Deferred from: code review da Epic 2 (2026-08-11)

- **Catálogo fora do ar impede publicar** — `frontend/src/app/(site)/organizador/publicar/page.tsx:71-82`.
  O item escolhido só existe se a busca da Discovery voltou `ok`, então recarregar
  a página com a Ticketmaster fora derruba o formulário inteiro, mesmo com tudo
  preenchido. A rota de escrita não depende da Discovery — quem depende é a tela.
  **Adiado porque** o conserto é persistir o item escolhido na URL (ou reconstruí-lo),
  o que redesenha o passo 2, e não cabe num patch de code review.

- **O teste da chave da Ticketmaster não cobre `__cause__`** — `backend/tests/test_ticketmaster.py:197`.
  `raise _catalogo_indisponivel() from erro` encadeia o `HTTPStatusError`, cujo
  `str()` contém a URL com `apikey=`. Hoje não vaza, porque o handler de
  `ErroDeDominio` não loga nada (`backend/app/main.py:64-67`) — mas o teste
  continuaria verde se alguém trocasse por `logger.exception`.
  **Adiado porque** fechar exige escolher entre perder a cadeia de depuração
  (`raise ... from None`) e sanear a mensagem do `httpx`, e isso é decisão, não patch.

- **`test_publicar_nao_chama_a_ticketmaster` mocka a indireção, não o transporte** — `backend/tests/test_organizador_eventos.py:266`.
  Substitui `ticketmaster._criar_cliente`. Uma chamada por qualquer outro caminho
  passaria verde e iria à rede de verdade.
  **Adiado porque** a barreira forte (`MockTransport` global no `conftest.py` ou
  `pytest-socket`) muda a infraestrutura da suíte inteira, que é assunto de epic,
  não de review.

- **`GET /organizador/portarias` entrega nome e e-mail de toda a portaria do sistema** — `backend/app/services/evento.py:176`.
  Decisão consciente, registrada no docstring e no README. Continua sendo PII sem
  escopo, sem paginação e sem limite de taxa, varrível por qualquer organizador.
  **Adiado porque** escopar exige decidir a quem cada conta de portaria pertence,
  e não existe modelo de "casa/produtora" no domínio.

- **`listar_do_organizador` não filtra `publicado_em IS NOT NULL`** — `backend/app/services/evento.py:222`.
  O modelo declara que `NULL` significa rascunho. Nenhum caminho cria rascunho hoje.
  **Adiado porque** é inofensivo até a Epic 3 depender de "evento não publicado não
  aparece na programação" — e é lá que a regra ganha teste.

- **A justificativa do `commit()` sem `try/except` está incompleta** — `backend/app/services/evento.py:170`.
  O docstring afirma que as violações possíveis "chegam todas do mesmo corpo, sem
  ninguém concorrendo". Esquece a FK `evento_portaria.usuario_id`, que aponta para
  outra linha de outro dono: uma conta apagada entre o `SELECT` e o `COMMIT` daria
  `IntegrityError` → `500`.
  **Adiado porque** a janela é teórica enquanto não existir rota de apagar usuário.
  O que precisa mudar antes disso é o **texto** — é ele que vai autorizar o próximo
  autor a não tratar nada.

- **`atracao` atravessa todo o contrato e ninguém usa** — `backend/app/schemas/catalogo.py:14`.
  Declarada no schema, preenchida pelo cliente da Discovery, tipada no frontend,
  com teste dedicado — e lida por nenhuma tela e nenhuma coluna.
  **Adiado porque** a Epic 3 pode consumi-la na página do evento; removê-la agora
  para reintroduzir depois é churn.

## Deferred from: code review da Epic 3 (2026-08-12)

- **O `downgrade` do `unaccent` derruba extensão que o `upgrade` não criou** — `backend/migrations/versions/20260811_06c1ad5ac276_habilita_extensao_unaccent.py:65`.
  Na Railway a extensão já existia, então o `upgrade` é no-op e o `downgrade` não é: ele apaga um
  objeto que esta migração nunca criou. E sem `CASCADE` o `DROP` falha duro se algo passar a depender
  dela — travando inclusive o `downgrade base` que o `conftest.py` roda por sessão.
  **Adiado porque** o conserto correto é registrar no `upgrade` se foi esta migração que criou a
  extensão, e isso é decisão de forma, não patch óbvio.

- **A collation do cluster não está fixada, e dois testes cravam ordem alfabética** — `docker/initdb/01-cria-banco-de-teste.sql:1`.
  `test_programacao.py:1872` exige `["Área VIP", "Camarote", "Pista"]` e `:926` exige as cidades
  acentuadas na posição certa. Num cluster com collation `C` — default plausível em Postgres
  gerenciado — `"Área VIP"` ordena depois de `"Pista"`. Verde no CI, ordem errada na Railway.
  **Adiado porque** fixar collation é mudança de infraestrutura da suíte, assunto de epic.

- **Nenhum índice em `evento.data_hora`, e a busca é seq scan obrigatório** — `backend/app/models/evento.py:95`.
  O recorte base (`publicado_em IS NOT NULL AND data_hora >= agora ORDER BY data_hora, id`) é
  indexável e não tem índice. O `unaccent()` na coluna não é `IMMUTABLE` e nunca entrará em índice —
  isso a migração já reconhece —, mas o recorte é outra coisa.
  **Adiado porque** o volume do desafio não expõe o custo, e criar índice é migração nova.

- **`chamarApi` não tem timeout** — `frontend/src/lib/api.ts:27`.
  Sem `AbortSignal.timeout`, uma requisição pendurada nunca resolve nem rejeita: o `finally` não roda,
  o botão fica em "Reservando…" para sempre, e a única saída é recarregar sem saber se a reserva foi
  criada. **Adiado porque** mexe no cliente HTTP de todas as telas, não só nas da Epic 3.

- **Safari não desenha pseudo-elemento em `<img>`** — `frontend/src/app/(site)/page.module.css:260`.
  O `.imagemDaArte::after` que cobre a arte quebrada da Ticketmaster funciona em Chrome e Firefox e
  não em Safari, onde o ícone de imagem quebrada volta ao meio da capa — o defeito que a regra existe
  para cobrir, declarado resolvido no comentário ao lado.
  **Adiado porque** o conserto é envolver a `<img>` num elemento próprio, o que mexe no layout de
  duas telas.

- **Exceção do gateway não tem `try/except`** — `backend/app/services/reserva.py:535`.
  `Autorizacao(True)` e `Autorizacao(False)` têm caminho; "não respondeu" não tem. Resultado seria
  `500`, reserva presa em `PENDENTE` e estoque retido até alguém pedir aquele setor.
  **Adiado porque** é inalcançável com o `PagamentoSimulado`, que nunca levanta — vira real no dia em
  que houver gateway de verdade, que é justamente a troca que o AD-10 promete isolar.

- **O AC8 da 3.1 (N+1) não tem teste, e o AC4 da 2.6 também nunca teve** — `backend/app/services/evento.py:443`.
  O `selectinload` está nas três consultas e o AC está cumprido, mas nenhum teste observa consulta
  emitida: remover a linha deixa os 60+ testes de `test_programacao.py` verdes, porque as respostas
  são idênticas e só muda o número de consultas.
  **Adiado porque** contar consultas exige um listener de `before_cursor_execute` no `conftest.py` —
  infraestrutura de suíte, e serve as duas epics de uma vez.

- **Dois relógios decidem a mesma expiração** — `backend/app/services/reserva.py:275` contra `:208`.
  O `expira_em` é gravado com o relógio do processo Python e julgado com `func.now()` do Postgres —
  hosts diferentes na Railway. Skew de 45 s muda o prazo real da reserva, e o cronômetro da tela é um
  terceiro relógio. **Adiado porque** o conserto (`func.now() + interval` na escrita) muda a forma de
  gravar em dois pontos e pede teste próprio.

- **`validade` é o único campo do checkout sem máscara** — `frontend/src/components/FormularioDePagamento.tsx:232`.
  CPF e telefone têm máscara ao digitar; a validade tem só `placeholder` e `maxLength`. Digitar `0826`
  sem a barra chega ao servidor e volta `422`, e a tela mostra a frase sobre o formulário inteiro sem
  destacar o campo culpado. **Adiado porque** é o mesmo trabalho de destaque por campo que nenhuma
  tela do projeto faz ainda.

- **Evento sem nenhum setor sai da programação como `esgotado: true`** — `backend/app/services/evento.py:482`.
  O `min()` está protegido, o significado não: um show que nunca teve ingresso à venda é anunciado
  como esgotado, e no detalhe o `EventoPublico` não tem campo `esgotado` para a tela explicar a página
  vazia. **Adiado porque** o estado não é criável pela rota de publicação — só por `psql`.

- **O chip de cidade não considera o `?periodo=` ativo** — `backend/app/services/evento.py:603`.
  `listar_cidades_em_cartaz` recorta por publicado + futuro, sem a janela do período. Único show em BH
  daqui a 60 dias, filtro `7 DIAS` ligado: o chip aparece e devolve lista vazia — o defeito que o
  docstring da função declara querer evitar. **Adiado porque** a justificativa escrita cobre `q` e
  `cidade` de propósito e ficou omissa quanto a `periodo`; decidir se o eixo é ortogonal é decisão de
  produto, não patch.

- **O `max_length=120` do `?q=` é medido antes do `.strip()`** — `backend/app/api/publico.py:111`.
  118 caracteres com três espaços em volta devolve `422` para um termo legal. Alcançável só por URL
  colada. **Adiado porque** o conserto é um `BeforeValidator` na rota, e o P20 já trata o sintoma
  visível pelo lado da tela.

- **Editar no meio do CPF ou do telefone joga o cursor para o fim** — `frontend/src/components/FormularioDePagamento.tsx:164`.
  A máscara remonta o valor inteiro a cada `onChange` sem restaurar `selectionStart`. O comentário das
  linhas 57-60 afirma o contrário, o que vale só para digitação no fim da string.
  **Adiado porque** restaurar caret com máscara é trabalho de componente, não de review.

- **Sessão expirada no stepper e no checkout não oferece caminho de volta** — `frontend/src/components/EscolhaDeIngressos.tsx:400` e `FormularioDePagamento.tsx:324`.
  As duas telas devolvem uma `string`, e tanto o `Toast` quanto o `AvisoDeErro` aceitam `ReactNode`
  exatamente para carregar o `<Link href="/login?voltar=…" target="_blank">` que o code review da
  Epic 2 já introduziu em `FormularioPublicacao.tsx:632`. **Adiado porque** é o mesmo padrão em dois
  lugares novos e cabe numa passagem só, não espalhado nos patches desta epic.

- **Trocar Cartão → Pix → Cartão apaga o cartão digitado** — `frontend/src/components/FormularioDePagamento.tsx:205`.
  O bloco do cartão é montado condicionalmente e os quatro campos são não controlados, sem
  `defaultValue`. O código do Pix é preservado de propósito; o do cartão não tem equivalente.
  **Adiado porque** controlar quatro campos a mais é refactor do formulário.

- **`router.refresh()` que falha no caminho de sucesso passa em silêncio** — `frontend/src/components/FormularioDePagamento.tsx:105`.
  Ele não devolve promessa, então falha de rede na re-renderização não cai no `catch`. O pagamento foi
  aprovado, o botão volta a "Pagar", e clicar de novo cai no ramo silencioso.
  **Adiado porque** depende de decidir o que a tela faz quando o servidor não responde depois de já
  ter cobrado — e isso é a mesma família da D3.

- **O AC10 da 3.2 nomeia `?q=` e `?cidade=`, e só o `?q=` tem teste** — `backend/tests/test_programacao.py`.
  A invariante está protegida indiretamente pelo teste de OpenAPI, que cai se a rota ganhar qualquer
  parâmetro. **Adiado porque** o risco real é baixo e é completude, não comportamento.
