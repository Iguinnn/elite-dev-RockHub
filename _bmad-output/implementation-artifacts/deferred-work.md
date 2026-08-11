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
