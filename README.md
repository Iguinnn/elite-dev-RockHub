# RockHub

Plataforma de eventos e ingressos: o organizador publica um show buscando a atração no catálogo da
Ticketmaster e define os setores à venda; o cliente descobre o evento, reserva por quantidade, paga
e recebe um ingresso com QR; a portaria valida esse QR na entrada. É a minha resposta ao **Desafio
Elite Dev** da Verzel — o enunciado completo está em
[docs/desafio-elite-dev.md](docs/desafio-elite-dev.md).

Monorepo com `backend/` (FastAPI + PostgreSQL) e `frontend/` (Next.js). Este README é o histórico
de decisões do projeto: o que eu escolhi, por que, e o que eu descartei no caminho. Os READMEs de
[backend/](backend/README.md) e [frontend/](frontend/README.md) tratam do que é específico de cada
camada.

> **Estado atual:** em construção. **O acesso está fechado pelos dois lados:** dá para criar conta em
> `/cadastro` e entrar em `/login` — senha em Argon2id, sessão em cookie `httpOnly` de 8 horas, e o
> navegador falando só com o domínio do frontend. O backend sobe com PostgreSQL migrado por Alembic e
> a tabela `usuario`; o frontend sobe com a identidade visual aplicada, o cabeçalho e as páginas de
> estado vazio. Ainda não há contas semeadas (Story 1.7) nem rota protegida (Story 1.6). A seção
> [O que não está pronto](#o-que-não-está-pronto) é mantida honesta a cada passo.

## Como executar

### Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** para o backend. Ele mesmo baixa o Python 3.12 se a máquina
  não tiver
- **Docker**, com o plugin Compose (`docker compose`, com espaço — é o Compose v2, embutido em
  qualquer instalação atual), para o PostgreSQL 16
- **Node ≥ 20.9** e **npm** para o frontend. O Next 16 não roda no Node 18

### Banco de dados

```bash
docker compose up -d      # Postgres 16 em localhost:5432, com o banco de teste já criado
docker compose ps         # conferir que o serviço está saudável
```

### Backend

```bash
cd backend

cp .env.example .env      # no Windows: copy .env.example .env
uv sync                   # cria a .venv/ e instala exatamente o que está no uv.lock

# gere o segredo que assina a sessão e cole no .env, em JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(48))"

uv run alembic upgrade head       # cria o schema (tabela usuario)
uv run uvicorn app.main:app --reload
```

Em desenvolvimento o valor de exemplo do `JWT_SECRET` funciona e você pode pular esse passo. Com
`AMBIENTE=producao` ele **derruba a aplicação na subida**, de propósito — o motivo está no
[README do backend](backend/README.md#configuração).

Sobe em <http://127.0.0.1:8000>. Para conferir que está no ar:

- <http://127.0.0.1:8000/saude> → `{"status": "ok"}`
- <http://127.0.0.1:8000/docs> → documentação automática do FastAPI

Testes (exigem o Compose no ar a partir da Story 1.3 — os testes de banco migram
`rockhub_teste` pelo próprio Alembic):

```bash
cd backend
uv run pytest
```

Detalhes de configuração, variáveis de ambiente e o contorno para o bloqueio de executáveis do
Windows estão no [README do backend](backend/README.md).

### Frontend

Em outro terminal:

```bash
cd frontend

cp .env.example .env.local    # no Windows: copy .env.example .env.local
npm install

npm run dev
```

Abre em <http://localhost:3000>, com o cabeçalho e o sistema visual aplicados.

**Suba o backend antes.** Desde o login, o frontend chama a API — e ele a alcança por um proxy
próprio: o navegador só conhece `/api/...`, e o Next reescreve para `http://localhost:8000` do lado
do servidor. Convenções de CSS, tokens da identidade, o proxy e as armadilhas do Next 16 estão no
[README do frontend](frontend/README.md).

## Contas semeadas

Ainda não existem — o seed com os quatro usuários de avaliação (organizador, cliente e portaria)
entra na Story 1.7.

**Para conta de cliente não é mais preciso script:** abra <http://localhost:3000/cadastro>, preencha
nome, e-mail e senha, e você já entra logado. Toda conta criada pela interface nasce `CLIENTE`, de
propósito — não há seletor de papel, e enviar `papel` na requisição não muda nada.

Para **organizador** e **portaria**, o script abaixo continua sendo o único caminho até a Story 1.7.
Rode a partir de `backend/`, com o Compose no ar e a migração aplicada, trocando o `PapelUsuario`
conforme o papel desejado:

```bash
uv run python -c "
from app.core.db import SessaoLocal
from app.core.seguranca import gerar_hash
from app.models.usuario import PapelUsuario, Usuario
s = SessaoLocal()
s.add(Usuario(nome='Igor Teste', email='igor@exemplo.com',
              senha_hash=gerar_hash('rockhub'), papel=PapelUsuario.ORGANIZADOR.value))
s.commit()
"
```

## Roteiro de avaliação

O caminho de ponta a ponta — publicar, comprar, receber o ingresso, provocar a recusa de pagamento
e validar na portaria — é escrito quando o fluxo estiver completo. Hoje dá para verificar:

1. `http://127.0.0.1:8000/saude` responde `{"status": "ok"}`, e `/docs` lista `/auth/cadastro`,
   `/auth/login` e `/auth/logout`
2. Abrir `http://localhost:3000/cadastro` e criar uma conta com nome, e-mail e senha (mínimo de 6
   caracteres) → **cai na raiz já logado**, sem precisar entrar de novo
3. No DevTools, aba Application: o cookie `rockhub_sessao` está no domínio `localhost:3000` — o do
   frontend — com `HttpOnly` marcado. E `document.cookie` no console não o mostra
4. Na aba Network, a chamada foi para `/api/auth/cadastro`, nunca para `localhost:8000`
5. Tentar cadastrar **o mesmo e-mail de novo** (inclusive com outra caixa: `IGOR@Exemplo.COM`) mostra
   "Esse e-mail já tem conta. Entre com ele ou use outro." e responde `409` — nunca um `500`
6. No cadastro, digitar senha e confirmação diferentes mostra "As senhas não conferem." **sem
   nenhuma requisição no Network** — a confirmação nunca sai do navegador
7. Apagar o cookie e entrar em `/login` com a conta que você acabou de criar → cai na raiz. É a prova
   de que hash e normalização de e-mail batem entre as duas rotas
8. Errar a senha mostra "E-mail ou senha incorretos." numa região anunciada por leitor de tela; a
   resposta é `401` com `CREDENCIAIS_INVALIDAS`. Um e-mail que não existe devolve **exatamente** a
   mesma coisa
9. Ir e voltar entre `/login` e `/cadastro` pelos links no pé de cada tela, sem digitar URL
10. `Tab` percorre os campos → botão → link, com o contorno âmbar visível em todos

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Sessão | Argon2id (`argon2-cffi`) para a senha · JWT HS256 (`PyJWT`) em cookie `httpOnly` |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript · CSS próprio, sem framework |
| Catálogo externo | Ticketmaster Discovery v2 *(Epic 2)* |
| Deploy | Railway (API e banco) · Vercel (frontend) *(Stories 1.8 e 1.9)* |

```text
docker-compose.yml   # Postgres 16 local — infraestrutura do projeto inteiro, por isso na raiz
docker/initdb/       # script que cria o banco de teste na primeira subida do Compose
backend/             # API FastAPI
frontend/            # Next.js
docs/                # enunciado do desafio e decisões técnicas em prosa
_bmad-output/        # artefatos de planejamento: brainstorm, arquitetura, UX, epics e stories
```

`_bmad-output/` é versionado de propósito: o desafio pede que os artefatos de planejamento sejam
entregues junto com o código. Lá dentro estão a sessão de brainstorming, a espinha de arquitetura
com as decisões vinculantes, o design de UX e as 38 stories.

## Decisões: por que isso e não aquilo

Esta seção cresce a cada story, enquanto o motivo ainda está fresco. As decisões de regra de
negócio que ainda não viraram código estão detalhadas em
[docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md).

### Backend separado em FastAPI, e não Next.js full-stack

**Decidi** separar a API do frontend, com FastAPI de um lado e Next.js do outro.

**Por quê:** o núcleo do desafio é concorrência — não vender o mesmo lugar duas vezes, não validar
o mesmo ingresso duas vezes. Isso se resolve com `UPDATE` condicional e transação, e eu queria a
ferramenta que deixa isso explícito. Separar também torna o contrato da API visível, o que é
justamente o que está sendo avaliado.

**O que caiu:** Next.js full-stack com Route Handlers e Prisma. Seria menos código e um deploy só,
mas empurraria a regra de concorrência para dentro do framework de tela, onde ela fica difícil de
enxergar — e apagaria a fronteira entre API e interface que o desafio pede para demonstrar.

### Sem camada de repositórios: `routers → services → models`

**Decidi** que o backend tem duas camadas antes do modelo. `app/api/` cuida do HTTP,
`app/services/` cuida da regra de negócio e das transações. Não existe `app/repositories/`.

**Por quê:** a `Session` do SQLAlchemy já é, na prática, um repositório com unidade de trabalho.
Numa aplicação deste tamanho, a camada extra viraria uma pilha de funções de repasse — `criar`,
`buscar_por_id`, `salvar` — que não separam nada de novo e só afastam a regra do lugar onde ela
acontece.

**O que caiu:** o `router → service → repository` que é padrão em projeto grande. Ele se paga
quando há mais de uma fonte de dados ou troca de ORM no horizonte. Não é o caso aqui, e adotar por
hábito seria cerimônia sem contrapartida. Deixei registrado para não parecer esquecimento.

### Erro da API tem código estável, e o frontend decide por ele

**Decidi** que **toda** resposta de erro sai como
`{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}}` — as mesmas duas chaves, venha o
erro da regra de negócio, do framework (rota inexistente, método errado) ou da validação do
Pydantic. Fixei isso na primeira story, antes de existir qualquer regra de negócio.

**Por quê:** o `codigo` é contrato; a `mensagem` é texto para humano. Com essa separação eu reescrevo
qualquer mensagem sem quebrar tela nenhuma. E o ponto de padronizar as três origens de uma vez é
que o frontend passa a ter um caminho só para tratar erro — se o `404` do router falasse
`{"detail": ...}` e o do meu service falasse `{"erro": ...}`, cada tela teria que saber os dois.

**O que caiu:** deixar cada endpoint devolver o `detail` padrão do FastAPI e o frontend interpretar
o texto. Funciona até a primeira vez que alguém corrige uma vírgula na mensagem e derruba um `if`
do outro lado.

**O que abri mão junto:** o erro de validação do Pydantic vem como uma lista de objetos aninhados,
que é mais rica para depurar. Achatei em texto (`quantidade: não é um inteiro`) para não ter uma
forma de erro diferente só nesse caso. Contrato uniforme valeu mais que detalhe estruturado num
cenário em que quem consome é a minha própria tela.

### Configuração só por variável de ambiente

**Decidi** que tudo que muda entre máquinas vem do ambiente, lido por uma classe `Settings` do
Pydantic, e que nenhum segredo entra no repositório — o que é versionado é o `.env.example`.

**Por quê:** a chave da Ticketmaster e o segredo que assina os ingressos chegam nas próximas epics.
Com o hábito já estabelecido, não existe o momento de tentação em que alguém "só comita o valor
para testar". O Pydantic ainda valida na subida: `AMBIENTE=homologacao` derruba a aplicação na hora,
em vez de causar um comportamento estranho três telas adiante.

**O que caiu:** um `config.py` com valores por ambiente versionado no repositório. É mais cômodo de
ler, mas é exatamente o arquivo em que segredo acaba caindo.

### O domínio é escrito em português

**Decidi** nomear as entidades como o enunciado as chama: `evento`, `setor`, `reserva`, `ingresso`,
`portaria`. Inclusive a rota de saúde é `/saude`.

**Por quê:** quem avalia lê o enunciado em português e depois o código. Sem tradução no meio, a
correspondência é direta e não sobra dúvida sobre qual requisito cada parte atende.

**O que caiu:** o inglês por convenção de mercado. Criaria um dicionário mental entre requisito e
código — `sector` é setor ou seção? `gate` é portaria ou portão? — em troca de nada que o projeto
aproveite.

### `uv` em vez de `pip` + `requirements.txt`

**Decidi** usar o `uv` como gerenciador do backend, com `uv.lock` versionado.

**Por quê:** o desafio vai ser rodado numa máquina que eu nunca vi. O `uv` baixa o próprio Python
3.12, cria a virtualenv e instala versões travadas — um comando, sem passo manual pelo caminho.
Cada instrução a menos no README é um jeito a menos de a avaliação travar antes de ver o produto.

**O que caiu:** `pip` + `requirements.txt`, que assume que a pessoa já tem a versão certa do Python
e sabe criar a venv. E o Poetry, que resolve o mesmo problema, mas é ele próprio mais uma
instalação a fazer antes de começar.

### A interface é um jornal noturno, e não um catálogo de e-commerce

**Decidi** que a listagem de shows não tem card: são filas separadas por fio, com a data na margem
esquerda, nome de artista em serifada e etiquetas em monoespaçada versalete. Fundo preto quente,
âmbar como acento único, raio zero e sombra zero em todo o sistema.

**Por quê:** ingresso não é produto de prateleira — é o direito de entrar num lugar, numa hora. Card
com imagem, preço e botão é vocabulário de e-commerce, e ele carrega junto a promessa errada. A
estrutura de impresso diz a coisa certa sobre o que está sendo vendido, e custa o mesmo para
construir. O desafio penaliza por escrito a interface que "parece gerada", e o que denuncia uma
interface gerada não é ser feia: é ser bonita de um jeito só. Escolher qual dos vários bonitos era
justamente o ponto.

**O que caiu:** a fileira horizontal de cards com paleta empresarial — o formato de Sympla, Eventim e
Ingresso.com. É o que o mercado faz e é o que qualquer gerador entrega por padrão, então seria a
escolha segura. Caiu junto uma lista de padrões que eu proibi de propósito e que estão anotados no
[DESIGN.md](_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md):
faixa que varre a tela, grade de 6 a 8 cards de seção, par de título gigante com textinho embaixo, e
a linha de contexto decorativa no cabeçalho ("Edição de sexta · 14 apresentações em cartaz") — essa
última eu cheguei a montar no protótipo e removi, porque soava gerada.

Duas direções visuais competiram antes: um jornal de eventos londrino, editorial e claro, e uma
parede de cartazes de casa de show, noturna. Nenhuma das duas resolvia sozinha — a primeira não tem
noite, a segunda não tem estrutura. A identidade final é a fusão: estrutura de impresso, cor de
madrugada.

### CSS escrito à mão, sem biblioteca de componentes

**Decidi** não usar shadcn, MUI, Chakra nem Tailwind. O frontend tem um `globals.css` com os nove
tokens da identidade e um `.module.css` por componente.

**Por quê:** é a mesma razão da decisão acima. Biblioteca de componentes não traz só código pronto —
traz junto um vocabulário visual, e é exatamente o vocabulário que este projeto está tentando não
ter. O card arredondado com sombra sutil vem de graça, e tirar ele depois dá mais trabalho do que
nunca tê-lo. Com CSS Modules o token fica num lugar só e o estilo de cada componente tem escopo
isolado, sem colisão de nome de classe.

**O que caiu:** Tailwind, que é o padrão do `create-next-app` e teria sido mais rápido de escrever.
Além do argumento acima, ele empurra a decisão visual para dentro do JSX, onde eu não consigo mais
ler a identidade inteira num arquivo só. Caiu também a folha global única no estilo do protótipo:
funciona hoje, mas com 30 telas pela frente vira um arquivo enorme com nomes de classe brigando.

### Fontes do sistema, nenhuma fonte externa

**Decidi** usar Georgia para a voz serifada e a monoespaçada do sistema para etiqueta e código.
Nenhuma fonte é baixada.

**Por quê:** a tensão entre as duas famílias é o que faz a identidade funcionar — serifada sozinha
vira convite de casamento, monoespaçada sozinha vira terminal —, e essa tensão eu consigo com o que
já existe em qualquer máquina. Sem requisição de rede, sem salto de layout enquanto a fonte carrega,
sem depender de um CDN de terceiro estar no ar durante a avaliação.

**O que caiu:** uma serifada de display do Google Fonts, que seria mais distinta. O `create-next-app`
inclusive já vem com a `Geist` configurada — eu arranquei. Ganhar meio grau de personalidade não
paga o custo de fazer a primeira renderização depender de rede.

### TypeScript no frontend

**Decidi** escrever o frontend em TypeScript.

**Por quê:** o que trafega entre as duas camadas é um contrato com muitos campos, em português, com
dinheiro em centavos e data em UTC — `preco_centavos`, `data_hora`, `vendidos`, `expira_em`. É
precisamente o tipo de coisa em que se erra o nome do campo e só se descobre com um `undefined`
aparecendo na tela. Como não há teste automatizado no frontend, o `tsc` é a única rede que eu tenho
ali.

**O que caiu:** JavaScript puro, que é mais rápido de escrever. Ele é mais rápido até a primeira vez
que eu renomeio um campo no backend — aí eu descubro as telas quebradas uma a uma, abrindo cada
uma, em vez de ler a lista que o compilador me dá de uma vez.

### Postgres local por `docker-compose.yml` na raiz, não instalado na máquina

**Decidi** subir o PostgreSQL 16 por Compose, num `docker-compose.yml` na raiz do repositório —
não dentro de `backend/`, porque o banco é infraestrutura do projeto inteiro (a Story 1.7 semeia
por ele, e o frontend em desenvolvimento depende do backend que depende dele).

**Por quê:** quem avalia vai clonar o repositório numa máquina que eu nunca vi. Um comando que sobe
o banco do zero, com volume nomeado e `healthcheck`, é um passo manual a menos para a avaliação
travar antes de chegar no produto.

**O que caiu:** Postgres instalado direto na máquina — obrigaria instalar, criar banco e usuário à
mão, mais passos manuais e mais formas de a avaliação travar cedo. E o banco da Railway direto
durante o desenvolvimento — zero setup local, mas passaria a depender de rede o tempo todo e todo
mundo (inclusive eu, testando) escreveria no mesmo banco de produção.

### SQLAlchemy síncrono, não `AsyncSession`

**Decidi** usar a `Session` síncrona do SQLAlchemy 2, no estilo tipado (`Mapped` / `mapped_column`).

**Por quê:** o núcleo deste desafio é concorrência — não vender o mesmo lugar duas vezes, não
validar o mesmo ingresso duas vezes — e isso se resolve com `UPDATE` condicional dentro de uma
transação. Esse código fica mais legível no síncrono. O volume de uma avaliação não cobra o preço
de I/O assíncrono, e `AsyncSession` exigiria `await` disciplinado em toda consulta e em toda
fixture de teste.

**O que caiu:** `AsyncSession` — melhor sob carga alta de I/O, mas um `await` esquecido bloqueia o
event loop de um jeito difícil de diagnosticar, e a disciplina que isso exige não se paga no
tamanho deste projeto.

### `papel` como `VARCHAR` + `CHECK`, não enum nativo do Postgres

**Decidi** que a coluna `papel` é `VARCHAR(20)` com um `CheckConstraint` nomeado
(`papel_valido`), listando os três valores (`ORGANIZADOR`, `CLIENTE`, `PORTARIA`), em vez do tipo
enum nativo do Postgres.

**Por quê:** o Alembic não cria nem derruba um tipo enum nativo sozinho no `downgrade()` — isso
quebraria a garantia de que o banco pode ser reconstruído do zero (é literalmente um critério de
aceite da Story 1.3). Alterar os valores permitidos depois também exigiria `ALTER TYPE` numa ordem
específica, mais frágil que reescrever uma migração de `CHECK`.

**O que caiu:** o enum nativo — mais idiomático no Postgres, mas o `downgrade` frágil e a evolução
mais custosa pesaram mais que o ganho de idiomatismo.

### Alembic desde a primeira tabela, nunca `create_all` — nem em teste

**Decidi** que todo schema nasce por migração Alembic versionada, sem exceção — inclusive nos
testes, que migram o banco de teste pelo Alembic em vez de criar as tabelas a partir dos modelos.

**Por quê:** `create_all` seria mais rápido de montar, mas deixaria de verificar exatamente o que
esta story entrega: a migração em si. Sem um `downgrade()` exercitado, uma migração pode estar
quebrada por meses sem que ninguém perceba — e seria a Story 1.8 (deploy na Railway) a descobrir
isso da pior forma possível, no meio de um deploy.

**O que caiu:** `Base.metadata.create_all`, cogitado especificamente para os testes por ser mais
rápido de escrever. Cai fora do projeto inteiro, não só desta story — é regra para as tabelas das
Epics 2 a 5 também.

### Testes de banco contra Postgres real, migrado pelo Alembic — não SQLite em memória

**Decidi** que a suíte roda `alembic downgrade base` seguido de `upgrade head` contra um banco de
teste real (`rockhub_teste`) antes de qualquer asserção, em vez de usar SQLite em memória.

**Por quê:** SQLite não tem UUID nativo, não tem `TIMESTAMPTZ` e trata `CHECK` de outro jeito —
passaria verde sem provar nada sobre o schema que a migração de verdade cria. O custo que eu aceitei
foi que `uv run pytest` passa a exigir o Compose no ar, e isso está documentado no
[README do backend](backend/README.md#testes).

**O que caiu:** SQLite em memória — mais rápido e sem dependência externa, mas testando um banco
que não é o de produção. `create_all` para os testes caiu pelo mesmo motivo da decisão anterior.

### Senha em Argon2id, não bcrypt nem SHA com sal

**Decidi** gravar senha como hash **Argon2id**, pelo `argon2-cffi`, com os parâmetros padrão da
biblioteca — que já são o perfil de baixa memória da RFC 9106.

**Por quê:** Argon2id é o vencedor da Password Hashing Competition e a recomendação atual do OWASP,
e é o único dos candidatos que resiste tanto a ataque por GPU quanto a ataque por hardware dedicado,
porque custa **memória** além de tempo. Na prática ele me dá de graça três coisas que eu teria que
construir e defender sozinho: sal aleatório por hash (por isso a mesma senha hasheada duas vezes dá
strings diferentes, e por isso não existe coluna de sal no banco — ele viaja dentro da própria
string), todos os parâmetros embutidos no hash (posso endurecê-los depois sem invalidar o que já
está gravado), e um custo deliberado de ~50ms por verificação.

**O que caiu:** **bcrypt**, que ainda é perfeitamente aceitável, mas trunca a senha em 72 bytes
silenciosamente e não impõe custo de memória. E **SHA-256 com sal**, que é o erro clássico: parece
seguro porque é criptografia de verdade, mas é rápido *por projeto* — e velocidade é exatamente a
propriedade errada aqui, porque quem tem o banco vazado testa bilhões de palpites por segundo.
Descartei junto o `passlib`, que é o wrapper que a documentação antiga do FastAPI usa: está sem
lançamento desde 2020, quebrou com o bcrypt 4, e não acrescenta nada sobre a API direta do
`argon2-cffi`.

**O custo que aceitei:** ~50ms e ~64 MB por verificação de senha. É o objetivo do algoritmo, não um
problema a otimizar, mas aparece de duas formas concretas — a suíte de testes de login é
perceptivelmente mais lenta que o resto, e isso pesa na escolha do tamanho da instância na Railway.

### Sessão em cookie `httpOnly`, não token no `localStorage`

**Decidi** que o JWT viaja num cookie `httpOnly`, `SameSite=Lax`, `Path=/`, com 8 horas de validade
e `Secure` quando `AMBIENTE=producao`. JavaScript nunca lê o token.

**Por quê:** token em `localStorage` é legível por qualquer script que rode na página — uma única
falha de XSS, em qualquer dependência, entrega a sessão inteira. Com `httpOnly` o navegador envia o
cookie e o JavaScript não o enxerga, então o mesmo XSS não consegue exfiltrar a credencial. E como o
frontend é Next com Server Components, cookie é também a única forma que funciona nos dois lados:
`localStorage` não existe no servidor, então eu acabaria com dois jeitos de autenticar — um no
cliente, outro no servidor — que é precisamente o que o AD-15 existe para impedir.

As 8 horas cobrem um turno de portaria, que é o cenário mais longo do sistema. Elas não são
configuráveis de propósito: invariante de arquitetura com justificativa de domínio não vira knob,
senão o valor em produção passa a divergir do documentado e ninguém descobre até alguém ser
deslogado no meio do turno.

**O que caiu:** `Authorization: Bearer` com o token no `localStorage`, que é o padrão que quase todo
tutorial de SPA ensina. É mais simples de depurar (dá para ver o token) e imune a CSRF por
construção — mas troca uma classe de ataque difícil por uma fácil, e quebraria os Server Components.
Caiu junto o **refresh token**: resolveria a sessão expirar no meio de um uso longo, ao custo de
mais um endpoint, mais uma tabela e uma regra de rotação para escrever e testar. Para 8 horas de
validade num sistema avaliado em dias, expirou e faz login de novo.

### PyJWT, não `python-jose` nem HMAC na mão

**Decidi** usar **PyJWT 2.13.0** para assinar e ler o token, sempre em HS256 com a lista de
algoritmos fixa no código.

**Por quê:** é a biblioteca de JWT mantida e minimalista do ecossistema Python — para HMAC ela não
traz dependência nenhuma a mais. E ela me protege de um erro específico: `jwt.decode` recusa rodar
sem `algorithms=[...]` explícito. Isso não é burocracia. Aceitar o algoritmo que vem escrito *dentro
do próprio token* é a vulnerabilidade clássica de JWT — um token forjado com `"alg": "none"` passaria
a valer. A biblioteca me obriga a fechar essa porta.

**O que caiu:** **`python-jose`**, que era a recomendação antiga da documentação do FastAPI. Último
lançamento em maio de 2025, e implementa o JOSE inteiro (JWE, JWK) — trazendo `pyasn1`, `rsa` e
`ecdsa` para o lockfile — quando eu uso exatamente uma primitiva. E **`hmac` + `hashlib` da
biblioteca padrão**, que teria zero dependência nova e é o mesmo mecanismo que eu vou usar na
assinatura do QR (AD-5): caiu porque me obrigaria a escrever à mão expiração, `base64url` e
comparação em tempo constante. Código de segurança escrito à mão, quando existe versão testada por
muita gente, é risco sem contrapartida.

### Proxy `/api/*` no Next, não `SameSite=None` em produção

**Decidi** que o navegador **nunca fala com o backend diretamente**. Ele chama `/api/auth/login` no
domínio do próprio frontend, e o Next reescreve para a API do lado do servidor.

**Por quê:** o deploy separa as duas metades em `rockhub.vercel.app` e `rockhub.up.railway.app`, e
para o navegador esses são *sites diferentes* — `vercel.app` e `up.railway.app` estão os dois na
Public Suffix List, então não existe domínio registrável em comum. Um cookie `SameSite=Lax` não é
aceito nem reenviado nesse cruzamento. O detalhe cruel é que isso passa despercebido: em
`localhost`, `:3000` e `:8000` são o mesmo site (porta não conta), então a suíte inteira ficaria
verde e o login só falharia em produção. Com o proxy, o `Set-Cookie` volta pelo domínio da Vercel, o
cookie é de origem própria, e o `SameSite=Lax` do AD-15 vale literalmente — sem exceção por
ambiente e sem depender da política de cookie de terceiro de cada navegador, que muda por decisão de
fornecedor.

**O que caiu:** **`SameSite=None; Secure` em produção**, que é menos código e a saída óbvia. Ela
transforma a sessão em cookie de terceiro — o Safari bloqueia isso por padrão, então o login
simplesmente não entraria naquele navegador — e exigiria emendar o AD-15 com uma exceção por
ambiente. Caiu também **deixar `Lax` cru e resolver no dia do deploy**: empurraria para a Story 1.9
uma correção que mexe no frontend, descoberta no pior momento possível.

**O que veio junto:** como as chamadas passaram a ser de mesma origem, CORS deixou de participar do
caminho do navegador — mas eu **não** removi o `CORSMiddleware` do backend, que continua sendo a
rede de proteção de qualquer chamada direta. E a variável `NEXT_PUBLIC_API_URL` virou `API_URL`,
lida no servidor: com o proxy, o navegador não precisa mais saber o endereço da API, e manter as
duas seria manter dois caminhos para alcançar a mesma coisa.

### Credencial inválida tem uma resposta só — inclusive no tempo

**Decidi** que e-mail inexistente e senha errada devolvem exatamente a mesma resposta: mesmo `401`,
mesmo `CREDENCIAIS_INVALIDAS`, mesma mensagem. E que as duas custam o mesmo tempo.

**Por quê:** a metade fácil é a mensagem — "esse e-mail não está cadastrado" entrega, para quem
perguntar, quem tem conta no sistema. Eu garanto isso usando literalmente a *mesma construção* de
erro nos dois caminhos, não duas strings iguais que alguém pode divergir depois; e o teste compara
as duas respostas **entre si**, em vez de comparar cada uma com um literal.

A metade que quase todo mundo esquece é o tempo. O caminho natural — não achou o usuário, levanta o
erro na hora — responde em ~1ms para e-mail desconhecido e em ~50ms para e-mail existente com senha
errada, porque só o segundo paga o custo do Argon2. Cinquenta vezes de diferença é medível de fora
com um `for` e um cronômetro, e transforma o endpoint num oráculo de cadastro sem precisar de senha
nenhuma. A correção é uma linha: quando o usuário não existe, eu confiro a senha contra um hash
descartável e jogo o resultado fora.

**O que caiu:** a resposta específica ("e-mail não cadastrado", com link para criar conta), que é
mais gentil e é o que muito site grande faz. Ela ajuda o usuário legítimo que errou o e-mail e
entrega a base de cadastro para qualquer um que perguntar — e num sistema com dados de compra, a
lista de quem tem conta já é informação. Caiu também **limitar tentativas de login** por IP ou por
conta, que seria a defesa mais direta contra força bruta: está declarado em
[O que não está pronto](#o-que-não-está-pronto), porque é infraestrutura (contador com expiração,
armazenamento compartilhado entre instâncias) que não se paga no prazo deste desafio.

### A tela de acesso não tem a navegação do site

**Decidi** partir o frontend em duas cascas: `(site)`, com o masthead completo, e `(entrada)`, que
mostra só o logotipo. `/login` e `/cadastro` ficam na segunda.

**Por quê:** a primeira versão da tela de login herdava o masthead do layout raiz, e o resultado era
oferecer "Meus ingressos" e "Minha conta" para quem ainda não tinha entrado. São dois links que essa
pessoa não consegue abrir, e que hoje caem no 404 — a tela pedia credencial com uma mão e apontava
para portas trancadas com a outra. Uma tela de acesso mostra a marca e o formulário; o resto é
ruído, e ruído numa tela de duas entradas é o que faz parecer template.

**O que caiu:** dois **layouts raiz** separados, que é o outro jeito de fazer isso no App Router.
Caiu por dois motivos concretos: a documentação do Next avisa que navegar entre layouts raiz
diferentes força recarga completa da página, e layout raiz múltiplo exige abrir mão do
`app/layout.tsx` — o que deixaria o `not-found.tsx` sem layout de onde herdar e obrigaria a adotar
`global-not-found`, que ainda é experimental. Caiu também esconder o masthead com `usePathname()`:
funcionaria em três linhas, mas transformaria o masthead inteiro num componente de cliente para
resolver o que é uma questão de estrutura de rota.

**O que eu aprendi tentando:** cheguei a mover o `not-found.tsx` para dentro de `(site)` para ele
herdar o masthead de graça. Não funciona — só o `not-found` na raiz de `app/` atende URL que não
casa com rota nenhuma, e o efeito foi o visitante cair no 404 padrão do Next, sem identidade. Ele
voltou para a raiz montando a própria casca, e isso está escrito no arquivo para ninguém repetir a
tentativa.

### Só cliente cria a própria conta; organizador e portaria nascem por fora

**Decidi** que o cadastro pela interface produz **sempre** uma conta `CLIENTE`. Não existe seletor de
papel na tela, não existe campo `papel` no schema de entrada, e o papel é literal dentro do service —
enviar `{"papel": "ORGANIZADOR"}` na requisição cria uma conta cliente do mesmo jeito, calada.

**Por quê:** um seletor de papel numa tela pública é uma escalada de privilégio com aparência de
formulário — qualquer visitante viraria organizador e passaria a publicar eventos. E o AD-7 é ainda
mais direto sobre a portaria: ela só valida onde foi *escalada* por um organizador, então uma conta
de portaria autocriada não faria sentido nenhum, porque não estaria ligada a evento algum. O papel é
uma afirmação sobre confiança, e afirmação de confiança não pode vir de quem está pedindo o acesso.

Fiz questão de que o campo desconhecido seja **ignorado** em vez de recusado com `422`: um `422`
provaria que o servidor viu o campo, enquanto ignorá-lo prova que ele não tem como influenciar nada.
A garantia mais forte é a que não depende de validação.

**O que caiu:** um seletor "sou cliente / sou organizador" no cadastro, que é o que várias
plataformas de evento fazem — elas resolvem o problema com aprovação manual ou verificação de CNPJ,
que é exatamente a etapa que este projeto não tem. Caiu também **um cadastro de organizador separado,
em rota própria**: é o caminho certo, e está *adiado, não descartado* — sem uma forma de decidir quem
merece o papel, a rota seria o mesmo buraco com um endereço diferente. Até a Story 1.7, organizador e
portaria nascem pelo script documentado em [Contas semeadas](#contas-semeadas).

### Validação de e-mail escrita à mão, não `EmailStr` do Pydantic

**Decidi** conferir o formato do e-mail com uma expressão regular de uma linha —
`^[^@\s]+@[^@\s]+\.[^@\s]+$` — em vez de instalar `email-validator` para usar o `EmailStr`.

**Por quê:** essa regra pega o que ela precisa pegar: `igor`, `igor@`, `igor@exemplo` sem ponto no
domínio, e-mail com espaço no meio. Ou seja, o erro de digitação, que é o único caso realista aqui.
`EmailStr` seria a escolha de um sistema em produção, e o custo é uma dependência a mais no lockfile
— e este sistema não vai para produção real: ele existe para o avaliador ver que o cadastro funciona,
e três linhas provam isso igual. **Não é RFC 5322 e não pretende ser**, e essa decisão está escrita
como corte consciente no código, ao lado da regex, e não deixada para quem ler adivinhar.

**O que caiu:** `EmailStr` + `email-validator`, mais correto e mais caro. E, do outro lado,
**nenhuma validação no backend**, que deixaria o `type="email"` do navegador como única barreira — e
ele desaparece num `curl`. Ficar sem validação nenhuma é o tipo de ausência que quem avalia nota em
dez segundos.

**O efeito colateral que eu gostei:** esta foi a primeira story desde a 1.1 a não acrescentar
nenhuma dependência, em nenhuma das duas camadas.

### Confirmação de senha, porque não existe recuperação de senha

**Decidi** que o cadastro tem quatro campos, e o quarto é "repetir senha". A senha mínima é de **6
caracteres**, sem exigir maiúscula, número ou símbolo.

**Por quê:** as duas metades desta decisão vêm do mesmo lugar — **não há recuperação de senha neste
projeto**, e isso não vai mudar. Uma letra digitada errada seria conta perdida para sempre: sem
suporte, sem e-mail de redefinição, sem saída. O campo de confirmação custa uma comparação em memória
e elimina a falha inteira. Já o piso de 6 caracteres é o que basta para um sistema que existe para
ser avaliado, sem travar as senhas curtas que as contas semeadas da Story 1.7 vão usar.

A confirmação **não chega ao backend**, e isso é parte da decisão: o formulário tem os dois valores em
mãos, compara antes do `fetch` e nem faz a requisição. Mandá-la para a API acrescentaria um campo ao
contrato, um validador cruzado, uma mensagem e um teste — tudo para verificar algo que nenhum outro
cliente da API teria por que enviar. A regra de negócio é "senha com pelo menos 6 caracteres"; "duas
caixas de texto iguais" é ergonomia de tela.

**O que caiu:** **8 caracteres**, que é o piso do NIST SP 800-63B e teria sido o padrão defensável —
6 ganhou por ser suficiente no contexto real deste sistema. **Nenhuma regra de senha**, que aceitaria
senha de um caractere. E, no lugar da confirmação, um **botão "mostrar senha"**: menos atrito e uma
interação a menos, mas expõe a senha na tela de quem se cadastra em público, e exigiria um componente
novo para resolver o mesmo problema com menos garantia.

### `Campo` e `Botao` extraídos no segundo formulário, não no primeiro

**Decidi** que componente compartilhado nasce no **segundo uso**, nunca no primeiro. Na Story 1.4, com
só a tela de login, o campo e o botão ficaram dentro do próprio formulário. Nesta story, com o
cadastro, eles viraram `Campo.tsx` e `Botao.tsx` — e o login foi reescrito sobre eles.

**Por quê:** dois campos num único formulário não dão evidência nenhuma sobre qual é a abstração
certa; seis campos e dois botões entre duas telas dão. Componente extraído cedo é componente com
`props` inventadas para casos que nunca chegam, e que a próxima story reescreve inteiro. Extrair
depois custa reescrever código que já funciona — que é um custo real e conhecido — mas em troca a
forma do componente sai dos usos de verdade.

**O que caiu:** **repetir o CSS nas duas telas**, que é o precedente que eu mesmo abri na 1.2 com o
404. Cairia bem aqui também, e não tocaria em arquivo já entregue — mas ao custo de duas cópias do
mesmo campo que divergem na primeira vez que alguém ajustar uma só. O 404 e o formulário são casos
diferentes: uma tela isolada pode divergir sem consequência; um campo de formulário que diverge entre
o login e o cadastro racha a identidade em duas.

**O risco que eu assumi, e como cobri:** reescrever o `FormularioLogin` foi o ponto mais perigoso da
story — um `htmlFor` que perde o par com o `id`, um `autoComplete` que some, e a tela continua
*parecendo* certa, sem nenhum teste de frontend para acusar. A cobertura foi conferir o login inteiro
no navegador depois da extração, campo por campo, e os 40 testes anteriores do backend passarem sem
uma linha alterada.

**Um terceiro componente que eu não tinha planejado:** o `AvisoDeErro`, extraído por um critério
diferente. `Campo` e `Botao` saíram porque se repetem; ele saiu porque a regra que o faz funcionar é
*invisível* — a região `role="alert"` precisa existir no DOM desde o primeiro render, vazia, para que
o leitor de tela anuncie o erro quando o texto chegar. Escrita como comentário dentro de um
formulário, essa regra é a primeira coisa que alguém apaga por parecer óbvia ao copiar para o
segundo. **Regra que protege acessibilidade vira componente mesmo com poucos usos**, porque é onde
ela se protege sozinha.

## O que não está pronto

Além do que ainda está por vir nas stories, estes são cortes conscientes — estão detalhados em
[docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md):

| O quê | Por quê |
|---|---|
| **Mapa de assentos** | O desafio aceita venda por quantidade em setores. A plataforma é focada em shows — pista, VIP, camarote — onde assento numerado não é o padrão |
| **Tela de editar evento** | O vínculo com a portaria só é definido na publicação. Num sistema real seria preciso escalar e remover porteiros depois |
| **Cancelamento pelo cliente** | O modelo já suporta; faltam endpoint e tela |
| **Pagamento real** | O gateway é simulado, com recusa determinística para que os dois caminhos sejam testáveis |
| **Refresh token** | Sessão de 8 horas basta para o cenário avaliado |
| **Limite de tentativas de login** | Não há bloqueio por IP nem por conta depois de N senhas erradas. É a defesa direta contra força bruta, e ficou de fora conscientemente: exige contador com expiração compartilhado entre instâncias, que é infraestrutura demais para o prazo. O que **está** feito é o custo de ~50ms por tentativa (Argon2id) e a resposta idêntica para e-mail inexistente e senha errada, inclusive no tempo |
| **Recuperação de senha** | O enunciado dispensa, e exigiria envio de e-mail — serviço externo, mais uma credencial e mais um fluxo para testar. É por não existir que o cadastro tem campo de confirmação de senha: sem ela, uma letra errada seria conta perdida para sempre |
| **Cadastro de organizador pela interface** | **Adiado, não descartado.** Toda conta criada em `/cadastro` nasce `CLIENTE`, e não há seletor de papel — um seletor numa tela pública seria escalada de privilégio com cara de formulário. A rota separada faz sentido, mas sem uma forma de decidir quem merece o papel (aprovação manual, verificação de CNPJ) ela seria o mesmo buraco com outro endereço. Até a Story 1.7, organizador nasce pelo script em [Contas semeadas](#contas-semeadas). **Portaria fica de fora em qualquer cenário**, e não por prazo: pelo AD-7 ela só valida onde foi escalada por um organizador, então conta de portaria autocriada não estaria ligada a evento nenhum |
| **Enumeração de e-mail no cadastro** | O `409 EMAIL_JA_CADASTRADO` revela que aquele e-mail tem conta — exatamente o que o login gasta um hash fantasma para não revelar. É inevitável aqui: o login pode esconder porque as duas respostas cabem numa frase só ("e-mail **ou** senha incorretos"), e o cadastro não tem essa saída — ou ele diz que o e-mail já existe, ou mente para quem está tentando criar a conta. A mitigação padrão é responder sempre "enviamos um e-mail para você" e resolver a diferença por fora, o que exige verificação por e-mail, que está fora do escopo. O que continua valendo: o login não entrega a lista de graça — quem quiser precisa passar pelo cadastro, um e-mail por vez |
| **Login que encaminha por papel** | Entrar leva todo mundo para a raiz. Encaminhar organizador e portaria para as telas deles depende dessas telas existirem (Epics 2 e 5); inventar a rota antes só produziria um 404 |
| **Teste automatizado no frontend** | Não há Vitest, Testing Library nem Playwright, e isso é decisão. As invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a primeira story. Em 7 dias, configurar teste de componente para cobrir markup que ainda vai mudar muito não se paga. O frontend é verificado por `npm run build`, `tsc --noEmit`, ESLint e conferência no navegador |
