# RockHub

Plataforma de eventos e ingressos: o organizador publica um show buscando a atração no catálogo da
Ticketmaster e define os setores à venda; o cliente descobre o evento, reserva por quantidade, paga
e recebe um ingresso com QR; a portaria valida esse QR na entrada. É a minha resposta ao **Desafio
Elite Dev** da Verzel — o enunciado completo está em
[docs/desafio-elite-dev.md](docs/desafio-elite-dev.md).

Monorepo com `backend/` (FastAPI + PostgreSQL) e `frontend/` (Next.js). Este README é o histórico
de decisões do projeto: o que eu escolhi, por que, e o que eu descartei no caminho. Os READMEs de
[backend/](backend/README.md) e [frontend/](frontend/README.md) tratam do que é específico de cada
camada — como rodar, estrutura de pastas, convenções e armadilhas.

> **Estado atual:** em construção, e **as duas metades estão no ar** —
> <https://elite-dev-rock-hub.vercel.app> é a aplicação, com o PostgreSQL da Railway migrado e
> semeado por trás. O acesso está fechado pelos dois lados (cadastro, login, sessão em cookie
> `httpOnly`, guarda por papel) e a **Epic 2 publica de verdade**: em `/organizador/publicar` o
> organizador busca a atração no catálogo, preenche data, local e setores, escala quem vai validar
> na porta, e acompanha o que publicou em `/organizador/eventos`. O que ainda não existe é o outro
> lado — descobrir, comprar e validar são as Epics 3 a 5. A seção
> [O que não está pronto](#o-que-não-está-pronto) é mantida honesta a cada passo.

## No ar

A aplicação está publicada na Vercel — **é esta URL que abre a interface**:

**<https://elite-dev-rock-hub.vercel.app>**

Entre com qualquer uma das credenciais de [Contas semeadas](#contas-semeadas). O caminho completo
está em [Roteiro de avaliação](#roteiro-de-avaliação).

A API vive à parte, na Railway, com o banco no mesmo projeto:

**<https://elite-dev-rockhub-production.up.railway.app>**

Você não precisa dela para usar a aplicação — o navegador nunca fala com esse endereço, e é de
propósito ([por quê](#proxy-api-no-next-não-samesitenone-em-produção)). Ela está aqui para quem
quiser ver o contrato:

- **[`/saude`](https://elite-dev-rockhub-production.up.railway.app/saude)** → `{"status": "ok"}`
- **[`/docs`](https://elite-dev-rockhub-production.up.railway.app/docs)** → documentação automática,
  com todas as rotas. Dá para entrar por ali mesmo, com qualquer conta semeada

```bash
curl -i -X POST https://elite-dev-rock-hub.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

Essa chamada prova o sistema inteiro num comando: ela só responde `200` se o build da Vercel leu o
endereço da API, **e** o proxy `/api/*` reescreveu para a Railway do lado do servidor, **e** as
migrações rodaram, **e** o seed gravou as contas. Repare no `Set-Cookie`: ele volta pelo domínio da
Vercel, com `HttpOnly`, `Secure` e `SameSite=lax` — é o cookie de sessão atravessando dois
fornecedores, que é a coisa que este deploy existe para provar.

Como cada plataforma foi configurada, campo por campo, está em
[Deploy na Vercel](frontend/README.md#deploy-na-vercel) e
[Deploy na Railway](backend/README.md#deploy-na-railway).

## Como executar

### Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** para o backend. Ele mesmo baixa o Python 3.12 se a máquina
  não tiver
- **Docker**, com o plugin Compose (`docker compose`, com espaço), para o PostgreSQL 16
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

uv run alembic upgrade head       # cria o schema
uv run python -m seeds.semear     # cria as 5 contas de avaliação
uv run uvicorn app.main:app --reload
```

Sobe em <http://127.0.0.1:8000>, com `/saude` e `/docs` respondendo.

Em desenvolvimento o `JWT_SECRET` de exemplo funciona e você pode pular a geração de segredo; com
`AMBIENTE=producao` ele **derruba a aplicação na subida**, de propósito. A
`TICKETMASTER_API_KEY` segue a mesma regra e pode ficar vazia aqui — em `local` a busca no catálogo
responde `CATALOGO_INDISPONIVEL` em vez de travar a avaliação por falta de conta no portal da
Ticketmaster. Detalhes em [Configuração](backend/README.md#configuração).

Testes (exigem o Compose no ar — a suíte migra o banco de teste pelo próprio Alembic):

```bash
cd backend
uv run pytest
```

### Frontend

Em outro terminal:

```bash
cd frontend

cp .env.example .env.local    # no Windows: copy .env.example .env.local
npm install
npm run dev
```

Abre em <http://localhost:3000>. **Suba o backend antes** — o frontend o alcança por um proxy
próprio: o navegador só conhece `/api/...`, e o Next reescreve para `http://localhost:8000` do lado
do servidor.

## Contas semeadas

Um comando cria as cinco contas de avaliação, com o Compose no ar e a migração aplicada:

```bash
cd backend
uv run python -m seeds.semear
```

| Papel | Nome | E-mail | Senha |
|---|---|---|---|
| `ORGANIZADOR` | Helena Marques | `organizador@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Bruno Tavares | `cliente@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Marina Aoki | `cliente2@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Jonas Ribeiro | `portaria@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Ana Sampaio | `portaria2@rockhub.dev` | `rockhub123` |

**São dois clientes de propósito**, para demonstrar duas garantias que um cliente só deixaria no ar:
que o ingresso de um não aparece na conta do outro (Epic 4) e que duas pessoas disputando o último
ingresso produzem uma venda e uma recusa (Epic 3). **E são duas portarias** desde a Story 2.5, para
que o cenário do AD-7 — a portaria A **não** valida o evento da portaria B — seja demonstrável sem
criar conta na mão. Conta de portaria não se cria pela interface, de propósito.

**As mesmas cinco contas existem no banco da Railway**, criadas por este mesmo comando, que roda a
cada deploy logo depois das migrações. Então elas valem nos três lugares: local, aplicação publicada
e `/docs` da API.

**Rodar de novo é seguro:** o comando não duplica conta, não apaga e não sobrescreve nada. Ele
imprime `criada` na primeira execução e `mantida` nas seguintes. Dois detalhes que evitam dez minutos
de confusão: rode **com o `-m`** (executar o arquivo direto quebra o caminho de import) e **a partir
de `backend/`**, que é de onde o `.env` é lido.

**Conta criada por `/cadastro` nasce sempre `CLIENTE`**: não há seletor de papel, e enviar `papel` na
requisição não muda nada.

## Roteiro de avaliação

O caminho de ponta a ponta — publicar, comprar, receber o ingresso, provocar a recusa de pagamento e
validar na portaria — é escrito quando o fluxo estiver completo. O que dá para verificar hoje:

### Sem instalar nada

Abra <https://elite-dev-rock-hub.vercel.app>. São cinco minutos, sem clonar, sem Docker:

1. A raiz abre com a identidade aplicada — fundo escuro, masthead com o fio duplo, serifada nos
   títulos. O masthead mostra `Início` · `Entrar`, porque você ainda não tem sessão
2. Abra `/conta` direto na barra de endereço → você é levado para `/login?voltar=%2Fconta`. A guarda
   de rota está valendo em produção
3. Entre com `organizador@rockhub.dev` / `rockhub123` → você **volta para a `/conta`**, e ela mostra
   **Helena Marques**, papel `ORGANIZADOR`. Essa conta não poderia ter nascido pela interface
4. O masthead vira `Início` · `Meus eventos` · `Publicar evento` · `Minha conta`. Clique em `Sair` →
   ele volta para `Entrar` **imediatamente, sem recarregar a página**
5. No DevTools, aba Application: o cookie `rockhub_sessao` está no domínio da **Vercel**, com
   `HttpOnly` marcado — e `document.cookie` no console não o mostra. Na aba Network, toda chamada
   saiu para `/api/...` no domínio da Vercel, **nunca** para `up.railway.app`

O passo 5 é o que eu pediria para olhar com atenção: a interface está na Vercel, a API na Railway, e
mesmo assim não existe requisição entre domínios nem cookie de terceiro. O motivo está em
[Proxy `/api/*` no Next](#proxy-api-no-next-não-samesitenone-em-produção).

**O que ainda não dá para fazer por lá:** descobrir evento, comprar, receber o QR ou validar na
portaria. Publicar **existe**, mas o roteiro dele está abaixo, em *Na sua máquina*, porque publicar
em produção criaria um evento no banco real que ninguém pediu.

### Na sua máquina

Rodando local pelos passos de [Como executar](#como-executar), começando pelo seed.

**Acesso e sessão**

1. Entrar como `organizador@rockhub.dev` → a `/conta` mostra **Helena Marques**, `ORGANIZADOR`
2. Rodar `uv run python -m seeds.semear` **de novo** → as cinco linhas dizem `mantida`, o comando sai
   em `0`, e nenhuma conta criada por você desaparece. É a garantia que faz esse comando poder rodar
   a cada deploy
3. Criar uma conta em `/cadastro` → cai na raiz já logado. Senhas diferentes nos dois campos mostram
   o erro **sem nenhuma requisição no Network** — a confirmação nunca sai do navegador
4. Cadastrar **o mesmo e-mail de novo** (inclusive com outra caixa: `IGOR@Exemplo.COM`) → `409`, com
   mensagem legível. Nunca um `500`
5. Errar a senha → `401 CREDENCIAIS_INVALIDAS`. Um e-mail que **não existe** devolve exatamente a
   mesma coisa, no mesmo tempo ([por quê](#recusa-não-entrega-o-que-ela-sabe))
6. `curl -i http://127.0.0.1:8000/auth/eu` sem cookie → `401 NAO_AUTENTICADO` no formato
   `{"erro": {...}}`. E `/rota-que-nao-existe` → `404` no mesmo formato, em português
7. Abrir `/login?voltar=//exemplo.com` (ou `?voltar=javascript:alert(1)`) e entrar → você cai em `/`.
   **Nunca fora do site**

**Publicar um evento** — o primeiro fluxo completo do produto, do catálogo externo até o banco

8. Como organizador, abrir `Publicar evento`. A tela **já chega mostrando shows reais** do catálogo
   da Ticketmaster, sem precisar buscar nada primeiro
9. **Clicar numa fila** → a URL ganha `?escolhido=…` e o passo 2 aparece. Recarregar mantém a
   escolha; o botão voltar a desfaz
10. Preencher data, horário, casa de show e um setor (`Pista`, `800`, `120,00`); no passo 3, marcar
    **as duas** portarias → a confirmação aparece **na própria tela**, com capacidade, preço e os dois
    nomes sob `Na porta`
11. Conferir que as linhas existem de verdade:
    `docker compose exec db psql -U rockhub -d rockhub -c "select nome, data_hora, local from evento;"`
    e `... -c "select * from evento_portaria;"` → duas linhas para esse evento
12. Repetir com **dois setores de mesmo nome** (`Pista` e `pista`) → `422 SETOR_DUPLICADO`, nunca um
    `500`, e nada fica gravado. `"setores": []` pela API → `422 EVENTO_SEM_SETOR`
13. **Publicar sem marcar ninguém no passo 3** → a tela recusa sem requisição. Pela API, corpo sem
    `portaria_ids` → `422 EVENTO_SEM_PORTARIA`
14. **Escalar uma conta que não é de portaria** (`"portaria_ids": ["<id do cliente>"]`) →
    `422 PORTARIA_INVALIDA`. Um UUID que não existe responde **exatamente o mesmo**
15. `curl` em `/organizador/portarias` com cookie de **cliente** → `403 SEM_PERMISSAO`; sem cookie →
    `401 NAO_AUTENTICADO`

**Acompanhar o que foi publicado**

16. Abrir `Meus eventos` → os shows numa fila com data, nome, `local · cidade` e
    `vendidos/capacidade` à direita. **Números exatos, sem medidor** — é o inventário de quem é dono
    da informação
17. Publicar um show com **data no passado** → ele aparece em `Já aconteceram`, separado de
    `Em cartaz`
18. **Clicar numa fila** → o detalhe abre com os setores um a um, com preço, e o bloco `Na porta`.
    Não há nada para editar aqui, e é [corte consciente](#o-que-não-está-pronto)
19. Pedir pela API o detalhe de **um evento que não é seu** → `404 EVENTO_NAO_ENCONTRADO`, com corpo
    **idêntico** ao de um UUID que nunca existiu
20. Entrar como `cliente@rockhub.dev` e digitar `/organizador/eventos` → você cai na raiz, e
    `Meus eventos` não está no masthead

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Sessão | Argon2id (`argon2-cffi`) para a senha · JWT HS256 (`PyJWT`) em cookie `httpOnly` |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript · CSS próprio, sem framework |
| Catálogo externo | Ticketmaster Discovery v2 |
| Deploy | Vercel (frontend) e Railway (API e banco) — **as duas no ar** |

```text
docker-compose.yml   # Postgres 16 local — infraestrutura do projeto inteiro, por isso na raiz
docker/initdb/       # script que cria o banco de teste na primeira subida do Compose
backend/             # API FastAPI          → backend/README.md
frontend/            # Next.js              → frontend/README.md
docs/                # enunciado do desafio e specs avulsas
_bmad-output/        # artefatos de planejamento: brainstorm, arquitetura, UX, epics e stories
```

**`_bmad-output/` é versionado de propósito**, porque o desafio pede os artefatos de planejamento
junto do código. Lá dentro estão a sessão de brainstorming (com o `.memlog.md` completo, que registra
o que foi considerado e recusado), a espinha de arquitetura com as 14 decisões vinculantes
(AD-1 a AD-14), o design de UX com protótipo navegável, e as 38 stories — uma por commit.

## Decisões: por que isso e não aquilo

Esta seção só guarda decisão que **muda o produto ou a arquitetura** — a régua é: se eu tivesse
escolhido a alternativa, quem avalia veria um sistema diferente. Decisão de detalhe (nome de
componente, ordem de campo, escolha de biblioteca menor) mora no README da camada, ao lado do código
que ela afeta.

### Setores por quantidade, não mapa de assentos

**Decidi** vender por setor com capacidade e contador (`Pista`, `800`, `120,00`), sem assento
numerado. O desafio aceita qualquer um dos dois.

**Por quê:** a plataforma é focada em show — pista, área VIP, camarote —, onde assento numerado não é
o padrão. Escolher o formato que casa com o produto vale mais do que escolher o mais vistoso.

**O que caiu:** o **mapa de assentos** de cinema e teatro, que é o mais impressionante de demonstrar
e o que o enunciado cita primeiro. Ele exigiria modelar assento individual, desenhar a planta e
resolver seleção em tempo real — e a invariante que importa ("o mesmo lugar não é vendido duas
vezes") é a **mesma** nos dois modelos, só que com muito mais tela pela frente. Preferi o fluxo
inteiro completo à metade sofisticada, que é literalmente o que o enunciado recomenda.

### Portaria é escala de trabalho, não nível de permissão

**Decidi** que o usuário de portaria é **escalado para eventos específicos** pelo organizador, no ato
da publicação. Ao entrar, ele vê só os eventos em que trabalha. É a tabela `evento_portaria`, com
chave composta, e um evento aceita vários escalados.

**Por quê:** a leitura óbvia do enunciado é tratar os três papéis como níveis de permissão — e aí
**qualquer conta de portaria valida ingresso de qualquer evento do sistema**. O papel diz o que a
pessoa pode fazer, mas não *onde*. Numa plataforma com vários organizadores, isso é um furo de
autorização. Um efeito colateral bem-vindo: como a validação sempre acontece dentro do contexto de um
evento escolhido, o retorno "evento errado" que o desafio pede **surge do modelo**, em vez de ser uma
regra inventada à parte.

**O que caiu:** **papel como permissão pura**, que é o que o enunciado sugere e custa uma tabela a
menos. E, dentro da escala, **um único porteiro por evento** (um `<select>`, que é o que o protótipo
desenhava): caiu porque a interface passaria a ser a única coisa impedindo o que o banco permite, e
não há tela de editar evento para corrigir depois — um evento com uma pessoa só escalada, e ela
faltando na noite do show, é um evento sem portaria.

### O catálogo externo é copiado na publicação, não consultado ao vivo

**Decidi** que a Ticketmaster é chamada **apenas** quando o organizador busca uma atração para
publicar. No ato da publicação, os dados usados são gravados no banco. Nenhuma tela de cliente ou de
portaria toca a API externa.

**Por quê:** a Discovery permite 5 requisições por segundo e 5.000 por dia. Se a listagem de eventos
consultasse a API a cada visita, a aplicação quebraria com pouquíssimo uso — e ficaria refém da
disponibilidade de um terceiro no meio de uma compra. Isso também resolve integridade: o nome, a
imagem e o local que aparecem no ingresso são os do momento da compra, mesmo que a Ticketmaster mude
o registro depois.

**O que caiu:** **consultar ao vivo com cache**, que manteria os dados sempre atualizados. Caiu
porque "atualizado" é a propriedade errada aqui: um ingresso vendido para um show que mudou de nome
na origem tem que continuar dizendo o que dizia quando foi vendido.

### Publicação exige atração do catálogo — sem cadastro manual de evento

**Decidi** que o organizador só publica a partir de uma atração encontrada no catálogo. Não existe, e
não vai existir, um caminho de "não achei — cadastro na mão".

**Por quê:** é o que o enunciado descreve literalmente — "o organizador monta um evento **a partir
de** um catálogo vindo de uma API externa" — e é o que a decisão acima pressupõe: o dado do catálogo
vira cópia no banco, o que só faz sentido existindo uma atração de origem.

**O que caiu:** um segundo caminho, "não encontrou? cadastre manualmente". Cobriria casos reais —
cover, evento independente, show sem página na Ticketmaster — mas abriria um formulário novo com
validação própria e sairia do que o enunciado pede para demonstrar. Fica registrado como
[limitação](#o-que-não-está-pronto).

### Só cliente cria a própria conta; organizador e portaria nascem por fora

**Decidi** que o cadastro pela interface produz **sempre** uma conta `CLIENTE`. Não há seletor de
papel, não há campo `papel` no schema de entrada, e enviar `{"papel": "ORGANIZADOR"}` cria uma conta
cliente do mesmo jeito, calada.

**Por quê:** um seletor de papel numa tela pública é escalada de privilégio com aparência de
formulário. E a portaria é ainda mais direta: ela só valida onde foi *escalada*, então uma conta de
portaria autocriada não estaria ligada a evento algum. Papel é uma afirmação sobre confiança, e
afirmação de confiança não pode vir de quem está pedindo o acesso. Fiz questão de que o campo
desconhecido seja **ignorado** em vez de recusado com `422`: um `422` provaria que o servidor viu o
campo; ignorá-lo prova que ele não influencia nada.

**O que caiu:** um seletor "sou cliente / sou organizador", que várias plataformas de evento têm —
elas resolvem com aprovação manual ou verificação de CNPJ, que é exatamente a etapa que este projeto
não tem. E **um cadastro de organizador em rota própria**, que está *adiado, não descartado*: sem uma
forma de decidir quem merece o papel, seria o mesmo buraco com outro endereço.

### Backend separado em FastAPI, e não Next.js full-stack

**Decidi** separar a API do frontend, com FastAPI de um lado e Next.js do outro.

**Por quê:** o núcleo do desafio é concorrência — não vender o mesmo lugar duas vezes, não validar o
mesmo ingresso duas vezes. Isso se resolve com `UPDATE` condicional e transação, e eu queria a
ferramenta que deixa isso explícito. Separar também torna o contrato da API visível, que é justamente
o que está sendo avaliado.

**O que caiu:** Next.js full-stack com Route Handlers e Prisma. Seria menos código e um deploy só,
mas empurraria a regra de concorrência para dentro do framework de tela, onde ela fica difícil de
enxergar — e apagaria a fronteira entre API e interface que o desafio pede para demonstrar.

### `routers → services → models`, sem camada de repositórios

**Decidi** duas camadas antes do modelo: `app/api/` cuida do HTTP, `app/services/` cuida da regra de
negócio e das transações. Não existe `app/repositories/`.

**Por quê:** a `Session` do SQLAlchemy já é, na prática, um repositório com unidade de trabalho. Numa
aplicação deste tamanho, a camada extra viraria uma pilha de funções de repasse — `criar`,
`buscar_por_id`, `salvar` — que não separam nada e só afastam a regra do lugar onde ela acontece.

**O que caiu:** o `router → service → repository` que é padrão em projeto grande. Ele se paga quando
há mais de uma fonte de dados ou troca de ORM no horizonte; não é o caso, e adotar por hábito seria
cerimônia sem contrapartida. A mesma régua criou **uma exceção deliberada**: a rota do catálogo chama
a integração da Ticketmaster direto, sem service, porque um service ali teria como corpo inteiro
`return ticketmaster.buscar_eventos(q)` — a definição de camada de repasse que eu acabei de recusar.

### O estoque é protegido pelo banco, não pela aplicação

**Decidi** que toda mudança de estoque é um único comando condicional, e que o banco carrega uma
constraint que torna o estado inválido impossível de gravar:

```sql
UPDATE setor SET vendidos = vendidos + :quantidade
 WHERE id = :setor_id AND vendidos + :quantidade <= capacidade
```

**Por quê:** o caso que interessa não é o normal, é o simultâneo — duas pessoas comprando o último
ingresso no mesmo instante. Como a verificação e a escrita acontecem no mesmo comando, não existe
intervalo entre "conferir" e "gravar", que é exatamente onde a corrida aconteceria. Se o comando
afetar zero linhas, não havia estoque, e a transação é revertida. O comando já existe e é testado
desde a Story 2.3, antes de a Epic 3 ter consumidor para ele.

**O que caiu:** **`SELECT` para conferir e depois `UPDATE`**, que é o caminho intuitivo e tem a
corrida embutida entre as duas linhas. E **lock na aplicação**, que resolveria numa instância só e
quebraria assim que houvesse duas réplicas — que é justamente a situação de um deploy real. A mesma
disciplina vai valer para a validação de ingresso na Epic 5: `WHERE id = :id AND usado_em IS NULL`.

### Dinheiro é inteiro em centavos, do banco à fronteira

**Decidi** que todo valor monetário é `int` em centavos no banco e no contrato da API. A conversão de
`120,00` para `12000` acontece no cliente, antes do `POST`.

**Por quê:** ponto flutuante não representa `0,10` exatamente, e preço de ingresso somado várias
vezes é onde isso aparece. A fronteira é o lugar certo para a conversão: do lado de fora quem digita
escreve como escreveria num cartaz; do lado de dentro, todo valor é inteiro, sem exceção.

**O que caiu:** **aceitar reais na API e converter no backend**, que tiraria o parsing do cliente —
caiu porque põe ponto flutuante no contrato. E **pedir centavos direto ao organizador**, zero
conversão e zero ambiguidade, ao custo de ele fazer a conta de cabeça a cada setor.

### Erro da API tem código estável, e o frontend decide por ele

**Decidi** que **toda** resposta de erro sai como
`{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}}` — as mesmas duas chaves, venha o
erro da regra de negócio, do framework (rota inexistente, método errado), da validação do Pydantic ou
de uma exceção não prevista. Fixei isso na primeira story, antes de existir qualquer regra de
negócio.

**Por quê:** o `codigo` é contrato; a `mensagem` é texto para humano. Com essa separação eu reescrevo
qualquer mensagem sem quebrar tela nenhuma. E padronizar as origens de uma vez é o que dá ao frontend
**um caminho só** para tratar erro — se o `404` do framework falasse `{"detail": ...}` e o do meu
service falasse `{"erro": ...}`, cada tela teria que saber os dois. O corpo do `500` não carrega a
causa: mensagem de exceção traz host, usuário e nome de tabela com frequência demais para virar
resposta HTTP.

**O que caiu:** deixar cada endpoint devolver o `detail` padrão do FastAPI e o frontend interpretar o
texto. Funciona até a primeira vez que alguém corrige uma vírgula na mensagem e derruba um `if` do
outro lado. **O que abri mão junto:** o erro de validação do Pydantic vem como lista de objetos
aninhados, mais rica para depurar; achatei em texto para não ter uma forma de erro diferente só nesse
caso.

### Alembic desde a primeira tabela, nunca `create_all` — nem em teste

**Decidi** que todo schema nasce por migração versionada, sem exceção — inclusive nos testes, que
migram o banco de teste pelo Alembic em vez de criar as tabelas a partir dos modelos.

**Por quê:** `create_all` seria mais rápido de montar, mas deixaria de verificar exatamente o que a
migração entrega. Sem um `downgrade()` exercitado, uma migração pode estar quebrada por meses sem
ninguém perceber — e seria o deploy a descobrir isso, da pior forma possível.

**O que caiu:** `Base.metadata.create_all`, cogitado especificamente para os testes por ser mais
rápido de escrever. Cai fora do projeto inteiro, não só de uma story.

### Testes de banco contra Postgres real, não SQLite em memória

**Decidi** que a suíte roda `alembic downgrade base` seguido de `upgrade head` contra um banco de
teste real (`rockhub_teste`) antes de qualquer asserção.

**Por quê:** SQLite não tem UUID nativo, não tem `TIMESTAMPTZ` e trata `CHECK` de outro jeito —
passaria verde sem provar nada sobre o schema que a migração de verdade cria. Como as invariantes
deste projeto **moram no banco** (a decisão do estoque, acima), testar contra um banco que não é o de
produção testaria a coisa errada.

**O que caiu:** **SQLite em memória**, mais rápido e sem dependência externa. O custo que aceitei foi
que `uv run pytest` passa a exigir o Compose no ar, e isso está documentado.

### SQLAlchemy síncrono, não `AsyncSession`

**Decidi** usar a `Session` síncrona do SQLAlchemy 2, no estilo tipado (`Mapped` / `mapped_column`).

**Por quê:** o núcleo do desafio é concorrência resolvida com `UPDATE` condicional dentro de uma
transação, e esse código fica mais legível no síncrono. O volume de uma avaliação não cobra o preço
de I/O assíncrono.

**O que caiu:** `AsyncSession` — melhor sob carga alta de I/O, mas exigiria `await` disciplinado em
toda consulta e em toda fixture, e um `await` esquecido bloqueia o event loop de um jeito difícil de
diagnosticar. A mesma régua manteve a integração com a Ticketmaster em `httpx` **síncrono**: um único
caminho `async` no backend inteiro criaria duas formas de escrever rota num projeto que tem uma só.

### Configuração só por variável de ambiente

**Decidi** que tudo que muda entre máquinas vem do ambiente, lido por uma classe `Settings` do
Pydantic, e que nenhum segredo entra no repositório — o que é versionado é o `.env.example`. Segredo
ausente em `AMBIENTE=producao` **derruba a aplicação na subida**.

**Por quê:** com o hábito estabelecido desde a primeira story, não existe o momento de tentação em
que alguém "só comita o valor para testar". E derrubar na subida é deliberado: um deploy com a
variável esquecida ficaria **verde**, e a falha só apareceria no dia em que alguém fosse publicar o
primeiro evento. O modo de falhar que assusta é justamente o que funciona.

**O que caiu:** um `config.py` com valores por ambiente versionado — mais cômodo de ler, e é
exatamente o arquivo em que segredo acaba caindo. E **nunca derrubar, sempre degradar**, que é mais
tolerante e esconderia o esquecimento até o pior momento possível.

### Senha em Argon2id, não bcrypt nem SHA com sal

**Decidi** gravar senha como hash **Argon2id**, pelo `argon2-cffi`.

**Por quê:** é o vencedor da Password Hashing Competition e a recomendação atual do OWASP, e o único
dos candidatos que resiste tanto a ataque por GPU quanto a hardware dedicado, porque custa **memória**
além de tempo. Ele me dá de graça três coisas que eu teria que construir e defender sozinho: sal
aleatório por hash (por isso não existe coluna de sal no banco), parâmetros embutidos no próprio hash
(dá para endurecê-los depois sem invalidar o que já está gravado) e um custo deliberado de ~50ms por
verificação.

**O que caiu:** **bcrypt**, ainda aceitável, mas trunca a senha em 72 bytes silenciosamente e não
impõe custo de memória. E **SHA-256 com sal**, que é o erro clássico: parece seguro porque é
criptografia de verdade, mas é rápido *por projeto* — e velocidade é exatamente a propriedade errada,
porque quem tem o banco vazado testa bilhões de palpites por segundo.

### Sessão em cookie `httpOnly`, não token no `localStorage`

**Decidi** que o JWT viaja num cookie `httpOnly`, `SameSite=Lax`, `Path=/`, com 8 horas de validade e
`Secure` em produção. JavaScript nunca lê o token.

**Por quê:** token em `localStorage` é legível por qualquer script que rode na página — uma única
falha de XSS, em qualquer dependência, entrega a sessão inteira. E como o frontend é Next com Server
Components, cookie é também a única forma que funciona nos dois lados: `localStorage` não existe no
servidor, então eu acabaria com dois jeitos de autenticar. As 8 horas cobrem um turno de portaria,
que é o cenário mais longo do sistema, e não são configuráveis de propósito — invariante com
justificativa de domínio não vira knob.

**O que caiu:** `Authorization: Bearer` com o token no `localStorage`, que é o padrão que quase todo
tutorial de SPA ensina: mais simples de depurar e imune a CSRF por construção, mas troca uma classe
de ataque difícil por uma fácil e quebraria os Server Components. Caiu junto o **refresh token** —
para 8 horas de validade num sistema avaliado em dias, expirou e faz login de novo.

### O papel vem do banco, não do que está escrito no token

**Decidi** que a dependência de autorização consulta o usuário no banco a cada requisição, mesmo com
o `papel` gravado dentro do JWT.

**Por quê:** a sessão dura 8 horas. Um papel corrigido no banco continuaria valendo o antigo por todo
esse tempo, e a única forma de derrubar o token seria trocar o `JWT_SECRET` — deslogando todo mundo.
Além disso, a consulta acontece de qualquer jeito, porque a dependência precisa do usuário inteiro
para responder o `GET /auth/eu`: ler o papel do banco custa zero.

**O que caiu:** **ler `carga["papel"]` do token**, que é o caminho curto e o que a maior parte dos
exemplos de JWT faz. A economia é real e paga-se com uma janela de 8 horas em que a autorização está
errada e ninguém consegue corrigir. Um teste guarda isso: um usuário gravado como `CLIENTE`, com
token forjado dizendo `ORGANIZADOR`, recebe `403`.

### Autorização é dependência na assinatura do endpoint, não `if` no corpo

**Decidi** que papel se declara, não se confere:

```python
@router.get("/organizador/eventos")
def meus_eventos(usuario: Usuario = Depends(exigir_papel(PapelUsuario.ORGANIZADOR))): ...
```

Não existe um `if usuario.papel == ...` dentro do corpo de handler nenhum, no projeto inteiro.

**Por quê:** a proteção passa a fazer parte da *assinatura* da rota. Ela aparece na documentação
gerada, e esquecê-la vira uma linha ausente que se vê à distância, em vez de uma verificação que
alguém precisava lembrar de escrever. Autorização espalhada por handler é o tipo de coisa que
funciona em 19 rotas e falha na vigésima, sem nada acusando.

**O que caiu:** **conferir o papel dentro do handler**, o caminho de menos código e o que qualquer
tutorial mostra — não custa nada na primeira rota, custa na décima. E um **middleware que inspeciona
o caminho da URL** (`/organizador/*` exige `ORGANIZADOR`): resolveria de um lugar só, ao preço de
manter uma tabela caminho→papel paralela às rotas — duas listas que divergem, e a desatualizada é
sempre a que ninguém olha.

### Proxy `/api/*` no Next, não `SameSite=None` em produção

**Decidi** que o navegador **nunca fala com o backend diretamente**. Ele chama `/api/auth/login` no
domínio do próprio frontend, e o Next reescreve para a API do lado do servidor.

**Por quê:** o deploy separa as duas metades em `vercel.app` e `up.railway.app`, e para o navegador
esses são *sites diferentes* — os dois estão na Public Suffix List, então não existe domínio
registrável em comum, e um cookie `SameSite=Lax` não é aceito nem reenviado nesse cruzamento. O
detalhe cruel é que isso passa despercebido: em `localhost`, `:3000` e `:8000` são o mesmo site
(porta não conta), então a suíte inteira ficaria verde e o login só falharia em produção. Com o
proxy, o cookie é de origem própria e o `SameSite=Lax` vale literalmente.

**O que caiu:** **`SameSite=None; Secure` em produção**, que é menos código e a saída óbvia — ela
transforma a sessão em cookie de terceiro, que o Safari bloqueia por padrão, então o login
simplesmente não entraria naquele navegador. **O que veio junto:** como as chamadas passaram a ser de
mesma origem, o CORS deixou de participar do caminho do navegador — mas eu **não** removi o
`CORSMiddleware`, que continua sendo a rede de proteção de qualquer chamada direta.

### Recusa não entrega o que ela sabe

**Decidi** que respostas de recusa não distinguem casos que revelariam quem existe no sistema. E-mail
inexistente e senha errada devolvem o mesmo `401 CREDENCIAIS_INVALIDAS`, com a mesma mensagem **e no
mesmo tempo**. Escalar um id que não existe e escalar uma conta que não é de portaria devolvem o
mesmo `422 PORTARIA_INVALIDA`. Pedir o detalhe de um evento de outro organizador devolve o mesmo
`404` de um UUID que nunca existiu.

**Por quê:** a metade fácil é a mensagem — "esse e-mail não está cadastrado" entrega, para quem
perguntar, quem tem conta no sistema. A metade que quase todo mundo esquece é o **tempo**: o caminho
natural responde em ~1ms para e-mail desconhecido e ~50ms para e-mail existente com senha errada,
porque só o segundo paga o custo do Argon2. Cinquenta vezes de diferença é medível de fora com um
`for` e um cronômetro. A correção é uma linha: quando o usuário não existe, eu confiro a senha contra
um hash descartável e jogo o resultado fora. Os testes comparam as duas respostas **entre si**, não
cada uma com um literal.

**O que caiu:** a resposta específica ("e-mail não cadastrado", com link para criar conta), que é
mais gentil e é o que muito site grande faz — ela ajuda o usuário legítimo que errou o e-mail e
entrega a base de cadastro para qualquer um que perguntar. Caiu também **distinguir os casos da
escala** para facilitar a depuração: o ganho é meu, no console, e o custo é de quem tem conta.

### A interface é um jornal noturno, e não um catálogo de e-commerce

**Decidi** que a listagem de shows não tem card: são filas separadas por fio, com a data na margem
esquerda, nome de artista em serifada e etiquetas em monoespaçada versalete. Fundo preto quente,
âmbar como acento único, raio zero e sombra zero em todo o sistema.

**Por quê:** ingresso não é produto de prateleira — é o direito de entrar num lugar, numa hora. Card
com imagem, preço e botão é vocabulário de e-commerce, e carrega junto a promessa errada. A estrutura
de impresso diz a coisa certa sobre o que está sendo vendido, e custa o mesmo para construir. O
desafio penaliza por escrito a interface que "parece gerada", e o que denuncia uma interface gerada
não é ser feia: é ser bonita de um jeito só. Escolher qual dos vários bonitos era o ponto.

**O que caiu:** a fileira horizontal de cards com paleta empresarial — o formato de Sympla, Eventim e
Ingresso.com. É o que o mercado faz e o que qualquer gerador entrega por padrão, então seria a
escolha segura. Caiu junto uma lista de padrões que proibi de propósito, anotada no
[DESIGN.md](_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md):
faixa que varre a tela, grade de 6 a 8 cards por seção, par de título gigante com textinho embaixo, e
a linha de contexto decorativa no cabeçalho — essa última eu cheguei a montar no protótipo e removi,
porque soava gerada. Duas direções competiram antes: um jornal de eventos londrino, editorial e
claro, e uma parede de cartazes noturna. Nenhuma resolvia sozinha; a identidade final é a fusão —
estrutura de impresso, cor de madrugada.

### CSS escrito à mão, sem biblioteca de componentes

**Decidi** não usar shadcn, MUI, Chakra nem Tailwind. O frontend tem um `globals.css` com os nove
tokens da identidade e um `.module.css` por componente. Nenhuma fonte é baixada — Georgia para a voz
serifada, monoespaçada do sistema para etiqueta.

**Por quê:** é a mesma razão da decisão acima. Biblioteca de componentes não traz só código pronto —
traz junto um vocabulário visual, e é exatamente o vocabulário que este projeto está tentando não
ter. O card arredondado com sombra sutil vem de graça, e tirá-lo depois dá mais trabalho do que nunca
tê-lo.

**O que caiu:** **Tailwind**, que é o padrão do `create-next-app` e teria sido mais rápido de
escrever — além do argumento acima, ele empurra a decisão visual para dentro do JSX, onde eu não
consigo mais ler a identidade inteira num arquivo só. E **uma serifada de display do Google Fonts**,
que seria mais distinta: ganhar meio grau de personalidade não paga fazer a primeira renderização
depender de rede.

### O frontend é server-first; `"use client"` é exceção justificada

**Decidi** que toda tela nasce Server Component, e que estado que o usuário pode querer compartilhar,
recarregar ou desfazer mora **na URL**. A busca do catálogo é um `<form method="get">`; a atração
escolhida é um `<Link>` que muda a query. Ilha de cliente só onde a interação exige o navegador — o
formulário de setores, que adiciona e remove linhas.

**Por quê:** com o estado na URL, recarregar mantém, o botão voltar desfaz, e o link abre no mesmo
lugar para outra pessoa — três coisas de graça. E o "sem spinner: a estrutura aparece e o conteúdo
preenche" do UX é natural no servidor e artificial no cliente. A fronteira que sai daqui vale para as
Epics 3 a 5, que vão ter mais interação (stepper de quantidade, câmera da portaria): ilha pequena
dentro de página de servidor, com a prop serializada como fronteira.

**O que caiu:** **estado no cliente com `onClick`**, que é o que qualquer formulário moderno faria —
tiraria a escolha da URL e transformaria a tela **inteira** numa ilha, levando junto a busca, o
catálogo e a guarda de sessão, sem nenhum deles precisar do navegador. E **Server Actions**, que
seriam o idiomático da versão instalada: caíram por ser mecanismo novo no projeto e por não resolver
o que motivou a ilha — o setor dinâmico continuaria exigindo número fixo de linhas.

### A guarda de rota mora na página, não em `middleware` do Next

**Decidi** que cada página protegida lê a sessão e redireciona por conta própria — três linhas
repetidas por página — e que o redirecionamento leva o destino junto (`/login?voltar=%2Fconta`),
filtrado para aceitar só caminho interno.

**Por quê:** o middleware só consegue ver que **existe** um cookie, não que ele vale. Validar o JWT
ali exigiria o `JWT_SECRET` no ambiente do frontend, e o segredo que assina a sessão não tem por que
existir na Vercel. A guarda na página pergunta ao backend, que é quem tem o segredo. Quanto ao
`?voltar=`: é um valor que quem chega escolhe e a aplicação obedece — sem filtro é o redirecionamento
aberto clássico, e a documentação do Next avisa que uma URL `javascript:` entregue ao `router.push`
executa no contexto da página, o que faz disso um XSS.

**O que caiu:** **o `middleware.ts` conferindo o cookie**, que é o caminho que todo tutorial mostra e
centraliza a regra num arquivo só — além do problema do segredo, viraria uma segunda lista de rotas
protegidas, paralela às páginas. E `unauthorized()`/`forbidden()`, que o Next 16 traz e seriam o
caminho idiomático: estão atrás de flag experimental, e eu não ligo flag experimental por
conveniência.

### O domínio é escrito em português

**Decidi** nomear as entidades como o enunciado as chama: `evento`, `setor`, `reserva`, `ingresso`,
`portaria`. Inclusive a rota de saúde é `/saude`, e as mensagens de erro do framework foram
traduzidas.

**Por quê:** quem avalia lê o enunciado em português e depois o código. Sem tradução no meio, a
correspondência é direta e não sobra dúvida sobre qual requisito cada parte atende.

**O que caiu:** o inglês por convenção de mercado. Criaria um dicionário mental entre requisito e
código — `sector` é setor ou seção? `gate` é portaria ou portão? — em troca de nada que o projeto
aproveite.

### A configuração de deploy mora no painel, não versionada

**Decidi** não versionar `railway.json`, `railway.toml` nem `vercel.json`. Builder, `Root Directory`,
branch, variáveis, comandos e health check estão nos painéis, e descritos campo por campo em
[Deploy na Railway](backend/README.md#deploy-na-railway) e
[Deploy na Vercel](frontend/README.md#deploy-na-vercel). A migração e o seed rodam no **Pre-deploy**,
separados do comando que sobe a aplicação.

**Por quê:** o painel **sobrescreve** o arquivo quando alguém edita por lá, e é por lá que se edita
no meio de um deploy que falhou, às pressas. Duas fontes para a mesma verdade divergem em silêncio, e
a desatualizada é sempre a que fica no repositório, parecendo documentação correta. Quanto ao
Pre-deploy: ele roda num contêiner à parte, **antes** de o tráfego ser trocado — migração quebrada
impede a subida em vez de derrubar a versão que estava funcionando.

**O que caiu:** o **`railway.json` versionado**, que é a escolha de infraestrutura-como-código e teria
uma vantagem real: recriar o serviço viraria reimportar o repositório. **O custo que aceitei, e como
cobri:** a configuração some se o serviço for apagado e não aparece em nenhum diff — por isso as
seções de deploy dos dois READMEs não são resumo, são os nomes exatos dos campos, os valores e os
erros que cada omissão produz. **A aposta foi cobrada e pagou:** configurar a Vercel reproduziu os
**dois** erros que eu já tinha cometido na Railway — `Root Directory` vazio e branch de produção
errada. Estavam documentados como armadilha, e custaram minutos em vez de uma noite.

## O que não está pronto

O enunciado pede que o que não estiver pronto seja dito. Estes são **cortes conscientes**, não
esquecimentos:

| O quê | Por quê |
|---|---|
| **Mapa de assentos** | Escolhi venda por quantidade em setores, que o desafio aceita. O raciocínio está em [Setores por quantidade](#setores-por-quantidade-não-mapa-de-assentos) |
| **Editar evento ou trocar a escala depois de publicar** | Desde a Story 2.6 existe a tela onde alguém procuraria — `Meus eventos`, com lista e detalhe — e nenhuma das duas edita nada. Publicado é publicado. A rota de escrita traria uma invariante nova ("a escala não pode chegar a zero") e editar capacidade traria a regra de ela não poder cair abaixo de `vendidos`: são duas stories, não meia |
| **Evento publicado entre a Story 2.4 e a 2.5 fica sem portaria** | A janela fechou — publicar exige portaria escalada desde a 2.5. O que não volta atrás é o que foi publicado antes: nada é escalado retroativamente e não há tela de edição. O conserto é apagar e publicar de novo |
| **Evento publicado entre os dados semeados** | O enunciado pede um evento já publicado junto das contas, e o seed continua criando só contas. O impedimento técnico acabou na Story 2.3; o que falta é decidir qual show, com que setores e em qual story isso entra. O fluxo de publicar pela interface existe e funciona, mas não substitui o seed: travaria o roteiro no primeiro passo se a Ticketmaster estivesse fora do ar |
| **A seção "Já aconteceram" de `Meus eventos` não tem como ser vista** | Decidi no code review da Epic 2 que publicar show com data no passado é recusado (`EVENTO_NO_PASSADO`): errar a data é permanente, porque não existe tela de editar, e na Epic 3 esse evento venderia ingresso para uma noite que já passou. O preço é que a seção do histórico fica vazia na avaliação — só apareceria com evento antigo no seed, que ainda não existe. Preferi assim: seção vazia é menos grave que evento impossível gravado para sempre |
| **Cancelamento pelo cliente** | O modelo já suporta (a reserva tem estado que devolve estoque); faltam endpoint e tela |
| **Pagamento real** | O gateway é simulado, com recusa determinística para que os dois caminhos sejam testáveis |
| **Refresh token** | Sessão de 8 horas basta para o cenário avaliado |
| **Limite de tentativas de login** | Não há bloqueio por IP nem por conta. É a defesa direta contra força bruta e exige contador com expiração compartilhado entre instâncias — infraestrutura demais para o prazo. O que **está** feito é o custo de ~50ms por tentativa e a resposta idêntica para e-mail inexistente e senha errada, inclusive no tempo |
| **Recuperação de senha** | O enunciado dispensa, e exigiria envio de e-mail. É por não existir que o cadastro tem confirmação de senha: sem ela, uma letra errada seria conta perdida para sempre |
| **Cadastro de organizador pela interface** | **Adiado, não descartado** — sem uma forma de decidir quem merece o papel, a rota separada seria o mesmo buraco com outro endereço. **Portaria fica de fora em qualquer cenário**, porque ela só valida onde foi escalada |
| **Enumeração de e-mail no cadastro** | O `409` revela que aquele e-mail tem conta — o que o login gasta um hash fantasma para não revelar. É inevitável: o login esconde porque as duas respostas cabem numa frase só; o cadastro ou diz que o e-mail já existe, ou mente. A mitigação padrão exige verificação por e-mail, que está fora do escopo |
| **Busca do organizador limitada ao Brasil** | `countryCode=BR` é fixo na chamada à Discovery. Sem ele, buscar "metallica" devolve os vinte primeiros shows do mundo e nenhum brasileiro entra — a tela pareceria quebrada justamente para quem avalia. O custo é que um show fora do Brasil não aparece |
| **Evento sem entrada no catálogo da Ticketmaster** | Não dá para publicar um cover de bar ou um evento independente. É consequência direta de o enunciado pedir que o evento nasça "a partir de" a API externa |
| **Editar a própria conta** | A `/conta` mostra nome, e-mail e papel, e permite sair. Trocar nome ou senha não é escopo de story nenhuma |
| **Ambiente separado para os Previews** | Os deploys de branch da Vercel apontam para o **mesmo banco de produção**. A alternativa deixaria todo Preview com o login quebrado em silêncio, que é pior; um segundo banco é infraestrutura que não se paga em sete dias. No plano Hobby os Previews ficam atrás do login da Vercel, então não são endereço público |
| **Integração contínua** | Não há GitHub Actions. CI aqui exigiria subir um PostgreSQL no runner, porque a suíte roda contra banco de verdade. O que existe no lugar: o `--locked` do build **falha** se o lockfile divergir do `pyproject.toml`, e a migração roda antes de a aplicação atender |
| **Teste automatizado no frontend** | Não há Vitest, Testing Library nem Playwright, e é decisão. As invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a primeira story. O frontend é verificado por `npm run build`, `tsc --noEmit`, ESLint e conferência no navegador |
| **Domínio próprio** | Custa dinheiro e propagação de DNS, e não acrescenta nada ao que está sendo avaliado |

## Uso de IA

O enunciado pede que eu conte quais ferramentas usei, em que partes, e o que foi feito sem IA.

**Ferramentas:** Claude Code, com o **BMAD Method v6.10.0** instalado e configurado em português.
Opus para planejamento e specs, Sonnet para implementação de código.

**Onde entrou:** o fluxo BMAD produziu, nesta ordem, a sessão de brainstorming, a espinha de
arquitetura (AD-1 a AD-14), o design de UX com protótipo navegável, as 6 epics com 38 stories, e o
plano de sprint. Depois, story a story, o `bmad-dev-story` implementou o código a partir da spec, e o
`bmad-code-review` revisou ao fim de cada epic. Todos esses artefatos estão versionados em
[`_bmad-output/`](_bmad-output/) — inclusive os `.memlog.md`, que registram a sessão completa, com o
que foi considerado e recusado no caminho.

**O que foi meu, sem IA:** as decisões. Stack, modelo de venda, identidade visual, recorte de escopo,
o que entra e o que fica de fora — cada item desta seção de decisões foi escolha minha, e a seção
existe para mostrar o raciocínio por trás delas. Também são meus o versionamento (todo commit foi
escrito e feito à mão, um por story) e a condução: os agentes produziram spec e código a partir de
direção minha, e o que eles propuseram sem eu ter escolhido foi recusado.

Esta seção é fechada na Story 6.3, com o detalhamento por camada.
