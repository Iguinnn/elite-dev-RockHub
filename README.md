# RockHub

Plataforma de eventos e ingressos: o organizador publica um show buscando a atração no catálogo da
Ticketmaster e define os setores à venda; o cliente descobre o evento, reserva por quantidade, paga
e recebe um ingresso com QR; a portaria valida esse QR na entrada. É a minha resposta ao **Desafio
Elite Dev** da Verzel — o enunciado completo está em
[docs/desafio-elite-dev.md](docs/desafio-elite-dev.md).

Monorepo com `backend/` (FastAPI + PostgreSQL) e `frontend/` (Next.js), publicado nas duas metades.
O fluxo está completo de ponta a ponta: publicar, descobrir, reservar, pagar (com aprovação **e**
recusa), receber o ingresso, compartilhar por link, revogar o link e validar na porta — pela câmera
ou digitando o código.

---

## Roteiro de avaliação

**Comece por aqui.** Este é o caminho de ponta a ponta — publicar, comprar, receber o ingresso e
validar na porta — em uns 10 minutos, com as contas já prontas.

| Se você quer… | Vá para |
|---|---|
| Abrir a aplicação agora, sem instalar nada | **<https://elite-dev-rock-hub.vercel.app>** |
| As credenciais dos três papéis | [Contas semeadas](#contas-semeadas) |
| Rodar na sua máquina | [Como executar](#como-executar) |
| Ver o contrato da API | [Documentação da API](#documentação-da-api) |

### ⚠️ Antes de começar: as duas janelas de tempo

Estas duas regras são a única coisa deste projeto que dá para descobrir do jeito errado, perdendo
tempo. Elas são deliberadas e estão testadas:

> **1. O cliente só compra ANTES de o show começar.**
> No minuto em que a `data_hora` do evento chega, ele some da programação, da busca e da criação de
> reserva. Um show que começou não é mais programação e não é mais compra.
>
> **2. A portaria só valida da abertura dos portões até o término.**
> O portão abre **2 horas antes** da `data_hora` e fecha **na `data_hora_fim`** que o organizador
> declarou. Fora dessa janela a rota responde `403` (`EVENTO_NAO_ABERTO` ou `EVENTO_ENCERRADO`) e o
> turno nem aparece como aberto na lista da portaria.

As duas juntas deixam uma janela de **2 horas** em que dá para comprar e validar o mesmo ingresso —
entre `início − 2h` e o `início`. É por isso que o roteiro abaixo manda criar o evento **para daqui
a uma hora**: o portão já está aberto, e a venda ainda não fechou.

### O caminho recomendado, do começo ao fim

Funciona igual [na aplicação publicada](https://elite-dev-rock-hub.vercel.app) e na sua máquina.
São uns 10 minutos.

**1 · Como organizador — publicar o show**

1. Entre com `organizador@rockhub.dev` / `rockhub123` e abra **Publicar evento**. A tela já chega
   mostrando shows reais do catálogo da Ticketmaster, sem precisar buscar nada
2. Clique numa fila para escolher a atração. Repare que a URL ganha `?escolhido=…`: recarregar
   mantém a escolha, e o botão voltar a desfaz
3. **Marque a data de hoje e um horário de início cerca de UMA HORA à frente do relógio.** É este o
   passo que faz o resto do roteiro funcionar — veja as janelas acima. Em *Termina às*, ponha três
   ou quatro horas depois
4. Preencha a casa de show e ao menos um setor (`Pista`, `50`, `120,00`)
5. No passo 3, **escale apenas o Jonas Ribeiro** — deixe a Ana de fora de propósito, que é o que
   torna verificável o item 4 abaixo. A confirmação aparece na própria tela

**2 · Como cliente — comprar**

6. Saia, entre com `cliente@rockhub.dev` / `rockhub123`. O show que você acabou de publicar está na
   programação da raiz
7. Abra o evento, escolha a quantidade e reserve. A reserva **segura o estoque por 10 minutos**, com
   cronômetro na tela
8. No checkout, pague com **cartão** — qualquer número aprova, exceto o caso do item 12. Depois de
   uma tela de espera de 6 segundos, o ingresso é emitido
9. Abra **Meus ingressos** → o canhoto com o **QR** e o código de 8 caracteres. **Anote o código**,
   você vai precisar dele
10. Clique em *Compartilhar* → um link público que abre o canhoto sem login. Abra numa janela
    anônima para conferir, volte e clique em *Revogar link* → o mesmo link agora responde como se
    nunca tivesse existido

**3 · Como portaria — validar**

11. Saia, entre com `portaria@rockhub.dev` / `rockhub123`. Você cai direto na casca da portaria, com
    a lista de turnos — e o show que você publicou está lá, com o portão **aberto**
12. Abra o turno e valide o ingresso, pela **câmera** (apontando para o QR na outra tela ou no
    celular) ou digitando o código de 8 caracteres. Resultado: **VÁLIDO**, em verde, com símbolo
13. **Valide o mesmo ingresso de novo** → **JÁ UTILIZADO**, com a hora da primeira entrada. É a
    garantia que o desafio pede, e ela é um `UPDATE` condicional no banco, não um `if` em Python
14. Digite um código inventado → **INVÁLIDO**. ⚠️ Não use as letras `I`, `L`, `O` ou `U`: o alfabeto
    é base32 de Crockford e não as contém — um código com elas é malformado, não forjado
15. O contador do turno sobe a cada leitura, e sobrevive a recarregar a página

### Os quatro caminhos que valem a pena provocar

| O quê | Como |
|---|---|
| **Recusa de pagamento** | No checkout, use um cartão **terminado em `0002`**. A recusa é determinística, a reserva vira `RECUSADA` e **o estoque volta** |
| **Evento errado** | Publique um segundo evento, compre nele, e tente validar aquele ingresso no turno do primeiro → **EVENTO ERRADO**. Repare que a tela **não diz de qual show o ingresso é** — devolver isso a quem não foi escalado nele é justamente o furo que a escala existe para fechar |
| **Portaria não escalada** | Entre como `portaria2@rockhub.dev` (Ana, que você deixou de fora no passo 5) → o turno **não aparece** na lista dela. Digitar a URL do turno à mão devolve `403` e cai de volta em `/portaria` |
| **Estoque disputado** | Publique um evento com **1 lugar**, e reserve por dois navegadores ao mesmo tempo → uma venda e uma recusa, nunca duas vendas. É `UPDATE ... WHERE vendidos + :q <= capacidade`, decidido no banco |

### O que dá para conferir sem instalar nada

Se você só quer olhar por cima, sem seguir o roteiro: o evento semeado já está na programação e é
comprável (ele começa daqui a três dias, então **não** dá para validar o ingresso dele na porta —
essa é a janela de 2h da regra 2). E o cookie de sessão: no DevTools → Application, `rockhub_sessao`
está no domínio da **Vercel**, com `HttpOnly` marcado, e `document.cookie` no console não o mostra.
Na aba Network, toda chamada saiu para `/api/...` no domínio da Vercel, **nunca** para
`up.railway.app`.

---

## Documentação da API

A API é documentada automaticamente pelo FastAPI, a partir dos próprios schemas Pydantic. **São 27
operações**, e dá para exercitar todas pelo navegador, logando com qualquer
[conta semeada](#contas-semeadas):

| | |
|---|---|
| **Swagger UI** | **<https://elite-dev-rockhub-production.up.railway.app/docs>** |
| ReDoc | <https://elite-dev-rockhub-production.up.railway.app/redoc> |
| OpenAPI (JSON) | <https://elite-dev-rockhub-production.up.railway.app/openapi.json> |
| Saúde | <https://elite-dev-rockhub-production.up.railway.app/saude> |

Rodando local, os mesmos endereços em <http://127.0.0.1:8000/docs>.

> **Para autenticar no Swagger:** chame `POST /auth/login` com um e-mail e senha da tabela de
> contas. A sessão volta num cookie `httpOnly`, que o navegador guarda sozinho — daí em diante todo
> `Try it out` das rotas protegidas já vai autenticado. Não há campo `Authorize`, e é de propósito:
> não existe `Authorization: Bearer` neste projeto ([por quê](#5--sessão-em-cookie-httponly-e-nunca-token-no-localstorage)).

As 27 operações, por grupo:

| Grupo | Operações |
|---|---|
| **Acesso** (`auth`) | `POST /auth/cadastro` · `POST /auth/login` · `POST /auth/logout` · `GET /auth/eu` |
| **Público** | `GET /eventos` · `GET /eventos/cidades` · `GET /eventos/destaque` · `GET /eventos/{id}` · `GET /ingressos/compartilhados/{token}` |
| **Organizador** | `GET /organizador/catalogo` · `GET`/`POST /organizador/eventos` · `GET`/`PUT`/`DELETE /organizador/eventos/{id}` · `GET /organizador/portarias` |
| **Cliente** | `POST /reservas` · `GET /reservas/{id}` · `POST /reservas/{id}/pagamento` · `GET /ingressos` · `GET /ingressos/{id}` · `POST`/`DELETE /ingressos/{id}/compartilhamento` |
| **Portaria** | `GET /portaria/eventos` · `GET /portaria/eventos/{id}` · `POST /portaria/eventos/{id}/validacoes` |
| **Operação** | `GET /saude` |

**Todo erro sai no mesmo formato**, venha da regra de negócio, do Pydantic ou de uma rota
inexistente — `{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}}`. O `codigo` é
estável e é por ele que o frontend decide o texto, nunca pela mensagem.

---

## No ar

| | |
|---|---|
| **Aplicação** (Vercel) | **<https://elite-dev-rock-hub.vercel.app>** |
| **API + PostgreSQL** (Railway) | <https://elite-dev-rockhub-production.up.railway.app> |

É a URL da Vercel que abre a interface. Você não precisa da API para usar a aplicação — o navegador
nunca fala com aquele endereço, e é de propósito
([por quê](#6--o-navegador-nunca-fala-com-a-api-o-next-faz-proxy)).

```bash
curl -i -X POST https://elite-dev-rock-hub.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"organizador@rockhub.dev","senha":"rockhub123"}'
```

Essa chamada prova o sistema inteiro num comando: ela só responde `200` se o build da Vercel leu o
endereço da API, **e** o proxy `/api/*` reescreveu para a Railway do lado do servidor, **e** as
migrações rodaram, **e** o seed gravou as contas. Repare no `Set-Cookie`: ele volta pelo domínio da
Vercel, com `HttpOnly`, `Secure` e `SameSite=lax`.

---

## Como executar

### Pré-requisitos

- **[uv](https://docs.astral.sh/uv/)** para o backend. Ele mesmo baixa o Python 3.12 se a máquina
  não tiver
- **Docker**, com o plugin Compose (`docker compose`, com espaço), para o PostgreSQL 16
- **Node ≥ 20.9** e **npm** para o frontend. O Next 16 não roda no Node 18

### 1 · O banco, com Docker Compose

```bash
docker compose up -d      # Postgres 16 em localhost:5432
docker compose ps         # conferir que o serviço está "healthy"
```

O `docker-compose.yml` está na raiz e sobe **o PostgreSQL**, com volume nomeado para os dados
persistirem entre reinícios e um script de inicialização que já cria o banco `rockhub_teste` usado
pela suíte. **Ele não sobe a API nem o frontend** — os dois rodam com `uv` e `npm` nos passos
abaixo. Foi escolha: containerizar as duas camadas acrescentaria dois Dockerfiles e um entrypoint
para resolver um problema que `uv sync` e `npm install` já resolvem em uma linha cada, e o que
realmente dói de instalar à mão numa máquina limpa é o Postgres.

Não quer Docker? Qualquer PostgreSQL 16 serve — aponte a `DATABASE_URL` para ele e crie o
`rockhub_teste` à mão se for rodar os testes.

### 2 · O backend

```bash
cd backend

cp .env.example .env      # no Windows: copy .env.example .env
uv sync                   # cria a .venv/ e instala exatamente o que está no uv.lock

uv run alembic upgrade head       # cria o schema
uv run python -m seeds.semear     # cria as contas e o evento de avaliação
uv run uvicorn app.main:app --reload
```

Sobe em <http://127.0.0.1:8000>, com `/saude` e `/docs` respondendo.

Em desenvolvimento o `JWT_SECRET` de exemplo funciona e você pode pular a geração de segredo; com
`AMBIENTE=producao` ele **derruba a aplicação na subida**, de propósito, e o mesmo vale para o
`TICKET_SIGNING_SECRET`. A `TICKETMASTER_API_KEY` pode ficar vazia aqui — em `local` a busca no
catálogo responde `CATALOGO_INDISPONIVEL` em vez de travar a avaliação por falta de conta no portal
da Ticketmaster.

### 3 · O frontend

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

### 4 · Os testes

```bash
cd backend
uv run pytest       # 585 testes
```

Exigem o Compose no ar: a suíte roda contra **PostgreSQL de verdade**, e ela mesma migra o banco de
teste pelo Alembic a cada sessão. Não há teste automatizado no frontend, e isso é
[corte consciente](#o-que-não-está-pronto).

### Variáveis de ambiente

Cada camada tem um `.env.example` versionado, comentado linha a linha, **sem nenhum segredo real**.

| Variável | Camada | Para quê |
|---|---|---|
| `AMBIENTE` | backend | `local` ou `producao`. Em `producao` ativa o `Secure` do cookie e recusa segredos de exemplo |
| `DATABASE_URL` | backend | Conexão com o Postgres. Aceita `postgres://`, `postgresql://` e `postgresql+psycopg://` |
| `DATABASE_URL_TESTE` | backend | Banco usado pelo `pytest` |
| `JWT_SECRET` | backend | Assina o JWT da sessão |
| `TICKET_SIGNING_SECRET` | backend | Assina o código do ingresso. **Variável própria**, e não o `JWT_SECRET` reaproveitado: girar a chave de sessão passaria a invalidar todo ingresso já emitido |
| `TICKETMASTER_API_KEY` | backend | Chave da Discovery. Opcional em `local` |
| `CORS_ORIGENS` | backend | Origens autorizadas a chamar a API direto |
| `COOKIE_SESSAO_NOME` | backend | Nome do cookie. ⚠️ O frontend procura esse nome por literal — trocar só de um lado deixa todo mundo deslogado sem um erro sequer |
| `API_URL` | frontend | Endereço da API, lido **no servidor**. Sem `NEXT_PUBLIC_`, sem barra no fim, sempre `https://` em produção |

---

## Contas semeadas

Um comando cria as **seis contas** e **um evento publicado com ingressos à venda**:

```bash
cd backend
uv run python -m seeds.semear
```

| Papel | Nome | E-mail | Senha |
|---|---|---|---|
| `ORGANIZADOR` | Helena Marques | `organizador@rockhub.dev` | `rockhub123` |
| `ORGANIZADOR` | Rafael Nunes | `organizador2@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Bruno Tavares | `cliente@rockhub.dev` | `rockhub123` |
| `CLIENTE` | Marina Aoki | `cliente2@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Jonas Ribeiro | `portaria@rockhub.dev` | `rockhub123` |
| `PORTARIA` | Ana Sampaio | `portaria2@rockhub.dev` | `rockhub123` |

**São duas de cada papel de propósito.** Dois clientes, porque o ingresso de um não aparecer na
conta do outro é uma frase que ninguém confere com uma conta só. Dois organizadores, pelo mesmo
motivo, em `Meus eventos`. Duas portarias, porque é isso que torna demonstrável a regra de que a
portaria A não valida o evento da portaria B. **Conta de portaria não se cria pela interface**, de
propósito.

**O evento semeado** é *Câmara Escura*, no Audio Club (São Paulo), marcado para **três dias à
frente**, com dois setores à venda — `Pista` (800 lugares, R$ 120,00) e `Mezanino` (200, R$ 220,00)
— e as duas portarias escaladas. Ele existe para o enunciado ("ao menos um evento publicado com
ingressos disponíveis") e para você poder comprar sem precisar publicar nada antes. Ele **não** vem
do catálogo da Ticketmaster: o seed não chama a API externa, senão avaliar exigiria uma conta no
portal.

**Rodar de novo é seguro:** o comando não duplica conta, não apaga e não sobrescreve nada. Imprime
`criada` na primeira execução e `mantida` nas seguintes. A única escrita que ele faz numa execução
seguinte é **reagendar o evento semeado** se a data dele já tiver passado — duas colunas de data, e
nada mais; quem já tinha ingresso continua com ele.

Dois detalhes que evitam dez minutos de confusão: rode **com o `-m`** (executar o arquivo direto
quebra o caminho de import) e **a partir de `backend/`**, que é de onde o `.env` é lido.

**As mesmas contas existem no banco da Railway**, criadas por este mesmo comando, que roda a cada
deploy logo depois das migrações. **Conta criada por `/cadastro` nasce sempre `CLIENTE`**: não há
seletor de papel, e enviar `papel` na requisição não muda nada.

---

## Stack e estrutura

| Camada | Escolha |
|---|---|
| Backend | FastAPI 0.141 · Python 3.12 · Pydantic v2 |
| Sessão | Argon2id (`argon2-cffi`) para a senha · JWT HS256 (`PyJWT`) em cookie `httpOnly` |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript · CSS próprio, sem framework |
| Leitura do QR | `@zxing/browser`, carregado sob demanda |
| Catálogo externo | Ticketmaster Discovery v2 |
| Testes | `pytest`, 585 testes contra PostgreSQL real |
| Deploy | Vercel (frontend) e Railway (API e banco) |

```text
docker-compose.yml   # Postgres 16 local — infraestrutura do projeto inteiro, por isso na raiz
docker/initdb/       # script que cria o banco de teste na primeira subida do Compose
backend/
  app/api/           # rotas HTTP, uma por área (auth, publico, cliente, organizador, portaria)
  app/services/      # regra de negócio e transações — é aqui que mora o domínio
  app/models/        # tabelas SQLAlchemy
  app/schemas/       # contratos de entrada e saída (Pydantic)
  app/core/          # config, sessão do banco, segurança, formato de erro
  app/integrations/  # cliente da Ticketmaster
  migrations/        # Alembic
  seeds/             # dados de avaliação
  tests/             # 585 testes
frontend/src/
  app/(site)/        # casca do jornal: programação, evento, reserva, ingressos, organizador
  app/(entrada)/     # login e cadastro
  app/portaria/      # casca própria da portaria, sem o masthead do site
  components/        # componentes e ilhas "use client"
  lib/               # acesso à API, formatação, sessão
docs/                # enunciado do desafio, techspecs e uso de IA
_bmad-output/        # artefatos de planejamento: brainstorm, arquitetura, UX, epics e stories
```

**`_bmad-output/` é versionado de propósito**, porque o desafio pede os artefatos de planejamento
junto do código. Lá estão a sessão de brainstorming (com o `.memlog.md` completo, que registra o que
foi considerado e recusado), a espinha de arquitetura com as 14 decisões vinculantes, o design de UX
com protótipo navegável de 11 telas, e as 38 stories.

---

## Deploy e integração contínua

**As duas metades sobem sozinhas a partir do `main`.** É um monorepo, e cada plataforma está
apontada para o seu diretório: um `git push` na `main` dispara o build do frontend na Vercel e o do
backend na Railway, em paralelo, sem nenhum passo manual.

| | Vercel | Railway |
|---|---|---|
| **Root Directory** | `frontend` | `backend` |
| **Branch de produção** | `main` | `main` |
| **Build** | detectado (Next.js) | Railpack, detectado pelo `pyproject.toml` |
| **Pré-deploy** | — | `alembic upgrade head && python -m seeds.semear` |
| **Start** | — | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health check** | — | `/saude` |
| **Variáveis** | `API_URL` | `AMBIENTE`, `DATABASE_URL`, `JWT_SECRET`, `TICKET_SIGNING_SECRET`, `TICKETMASTER_API_KEY`, `CORS_ORIGENS` |

**Não existe `vercel.json`, `railway.json`, `Dockerfile` nem `Procfile` neste repositório** — a
configuração de deploy mora no painel de cada plataforma, e esta tabela é onde ela está escrita.

Três armadilhas que me custaram build, e que valem para quem for subir a própria cópia:

- **O `Root Directory` é o campo que derruba o primeiro build nas duas plataformas.** Ele não vem
  preenchido, e sem ele a plataforma olha a raiz do monorepo, não acha `package.json` nem
  `pyproject.toml`, e falha sem dizer o que faltou
- **A branch de produção é escolhida sozinha** (`main`, `master`, ou a padrão do repositório).
  Trocá-la no painel não dispara deploy nenhum
- **Os comandos da Railway não usam `uv run`.** O `uv` só existe na fase de build; o que chega ao
  contêiner de execução é a virtualenv, com `alembic`, `uvicorn` e `python` já no `PATH`

**Migração e seed rodam num contêiner separado, antes de o tráfego ser trocado.** Se a migração
falhar, o deploy não prossegue e a versão anterior continua atendendo — em vez de tirar do ar o que
estava funcionando. É também por isso que o seed sai em `0` mesmo quando avisa: um `exit(1)` por
causa de um aviso derrubaria o deploy inteiro.

O que **não** existe é integração contínua no sentido de rodar a suíte a cada push: não há GitHub
Actions ([por quê](#o-que-não-está-pronto)).

---

## Decisões: por que isso e não aquilo

O desafio diz, com todas as letras, que o que interessa não é volume entregue — é como se pensa, o
que foi descartado, por que a tela é assim e não de outro jeito. Esta seção é a resposta a isso.

A régua para uma decisão entrar aqui: **se eu tivesse escolhido a alternativa, quem avalia veria um
sistema diferente.** Detalhe de tela, nome de componente e biblioteca menor ficam de fora — eles
estão documentados ao lado do código, nas techspecs em [`docs/`](docs/).

### 1 · Setores por quantidade, não mapa de assentos

**Decidi** vender por setor com capacidade e contador (`Pista`, `800`, `120,00`), sem assento
numerado. O desafio aceita qualquer um dos dois.

**Por quê:** a plataforma é focada em show — pista, área VIP, camarote —, onde assento numerado não
é o padrão. Escolher o formato que casa com o produto vale mais do que escolher o mais vistoso.

**O que caiu:** o **mapa de assentos** de cinema e teatro, que é o mais impressionante de demonstrar
e o que o enunciado cita primeiro. Ele exigiria modelar assento individual, desenhar a planta e
resolver seleção em tempo real — e a invariante que importa ("o mesmo lugar não é vendido duas
vezes") é a **mesma** nos dois modelos, só que com muito mais tela pela frente. Preferi o fluxo
inteiro completo à metade sofisticada, que é literalmente o que o enunciado recomenda.

### 2 · Portaria é escala de trabalho, não nível de permissão

**Decidi** que o usuário de portaria é **escalado para eventos específicos** pelo organizador, no
ato da publicação. Ao entrar, ele vê só os eventos em que trabalha. É a tabela `evento_portaria`,
com chave composta, e um evento aceita vários escalados.

**Por quê:** a leitura óbvia do enunciado é tratar os três papéis como níveis de permissão — e aí
**qualquer conta de portaria valida ingresso de qualquer evento do sistema**. O papel diz o que a
pessoa pode fazer, mas não *onde*. Numa plataforma com vários organizadores, isso é um furo de
autorização. Um efeito colateral bem-vindo: como a validação sempre acontece dentro do contexto de
um evento escolhido, o retorno "evento errado" que o desafio pede **surge do modelo**, em vez de ser
uma regra inventada à parte.

**O que caiu:** **papel como permissão pura**, que é o que o enunciado sugere e custa uma tabela a
menos. E, dentro da escala, **um único porteiro por evento** (um `<select>`, que é o que o protótipo
desenhava): caiu porque a interface passaria a ser a única coisa impedindo o que o banco permite, e
um evento com uma pessoa só escalada, faltando na noite do show, é um evento sem portaria.

### 3 · O catálogo externo é copiado na publicação, não consultado ao vivo

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
na origem tem que continuar dizendo o que dizia quando foi vendido. Caiu junto o **TMDb**, a outra
API que o enunciado oferece: ela é catálogo de filme, e um catálogo de filme empurraria o produto
para sessão de cinema — que é onde o mapa de assentos faria falta, e eu já tinha decidido não
fazê-lo.

### 4 · O estoque é protegido pelo banco, não pela aplicação

**Decidi** que toda mudança de estoque é um único comando condicional, e que o banco carrega uma
constraint que torna o estado inválido impossível de gravar:

```sql
UPDATE setor SET vendidos = vendidos + :quantidade
 WHERE id = :setor_id AND vendidos + :quantidade <= capacidade
```

**Por quê:** o caso que interessa não é o normal, é o simultâneo — duas pessoas comprando o último
ingresso no mesmo instante. Como a verificação e a escrita acontecem no mesmo comando, não existe
intervalo entre "conferir" e "gravar", que é exatamente onde a corrida aconteceria. Se o comando
afetar zero linhas, não havia estoque, e a transação é revertida.

**O que caiu:** **`SELECT` para conferir e depois `UPDATE`**, que é o caminho intuitivo e tem a
corrida embutida entre as duas linhas. E **lock na aplicação**, que resolveria numa instância só e
quebraria assim que houvesse duas réplicas — que é justamente a situação de um deploy real. A mesma
disciplina vale para a validação na porta: `WHERE id = :id AND usado_em IS NULL`. Nos dois casos eu
provei a diferença por **mutação**, não por leitura: trocar o `UPDATE` condicional por um `if` em
Python passa em todos os testes sequenciais e falha só no de duas conexões simultâneas.

### 5 · Sessão em cookie `httpOnly`, e nunca token no `localStorage`

**Decidi** que o JWT viaja num cookie `httpOnly`, `SameSite=Lax`, `Path=/`, com 8 horas de validade
e `Secure` em produção. JavaScript nunca lê o token. A senha é Argon2id.

**Por quê:** token em `localStorage` é legível por qualquer script que rode na página — uma única
falha de XSS, em qualquer dependência, entrega a sessão inteira. E como o frontend é Next com Server
Components, cookie é também a única forma que funciona nos dois lados: `localStorage` não existe no
servidor, então eu acabaria com dois jeitos de autenticar. As 8 horas cobrem um turno de portaria,
que é o cenário mais longo do sistema.

**O que caiu:** `Authorization: Bearer` com o token no `localStorage`, que é o padrão que quase todo
tutorial de SPA ensina: mais simples de depurar e imune a CSRF por construção, mas troca uma classe
de ataque difícil por uma fácil e quebraria os Server Components. Caiu junto o **refresh token** —
para 8 horas de validade num sistema avaliado em dias, expirou e faz login de novo.

### 6 · O navegador nunca fala com a API: o Next faz proxy

**Decidi** que o navegador chama `/api/auth/login` no domínio do próprio frontend, e o Next reescreve
para a API do lado do servidor.

**Por quê:** o deploy separa as duas metades em `vercel.app` e `up.railway.app`, e para o navegador
esses são *sites diferentes* — os dois estão na Public Suffix List, então não existe domínio
registrável em comum, e um cookie `SameSite=Lax` não é aceito nem reenviado nesse cruzamento. O
detalhe cruel é que isso passa despercebido: em `localhost`, `:3000` e `:8000` são o mesmo site
(porta não conta), então a suíte inteira ficaria verde e o login só falharia em produção. Com o
proxy, o cookie é de origem própria e o `SameSite=Lax` vale literalmente.

**O que caiu:** **`SameSite=None; Secure` em produção**, que é menos código e a saída óbvia — ela
transforma a sessão em cookie de terceiro, que o Safari bloqueia por padrão, então o login
simplesmente não entraria naquele navegador.

### 7 · A expiração da reserva é preguiçosa, não agendada

**Decidi** que a reserva nasce `PENDENTE` já consumindo estoque, com 10 minutos de validade, e que
**não há worker nem cron**. Uma reserva vencida é colhida no momento em que alguém a toca: ao tentar
pagá-la, ou quando outra pessoa pede estoque daquele setor.

**Por quê:** quem devolve o estoque é quem precisa dele, no instante em que precisa. Um agendador
resolveria o mesmo problema ao custo de um processo a mais para hospedar, monitorar e explicar — e
faria trabalho varrendo reservas que ninguém está disputando. Só as rotas de **escrita** colhem; as
de leitura não, senão a programação, que é Server Component, viraria escrita a cada visita.

**O que caiu:** o **worker com `APScheduler` ou cron da Railway**, que é a resposta de manual. E
**colher também na leitura**, que deixaria o número da tela sempre exato. A consequência que aceito
está declarada abaixo: a página pode dizer "Esgotado" com reservas já vencidas. É inofensiva, porque
no momento em que o estoque importa — o clique em reservar — ele já está correto.

### 8 · `routers → services → models`, sem camada de repositórios

**Decidi** duas camadas antes do modelo: `app/api/` cuida do HTTP, `app/services/` cuida da regra de
negócio e das transações. Não existe `app/repositories/`.

**Por quê:** a `Session` do SQLAlchemy já é, na prática, um repositório com unidade de trabalho.
Numa aplicação deste tamanho, a camada extra viraria uma pilha de funções de repasse — `criar`,
`buscar_por_id`, `salvar` — que não separam nada e só afastam a regra do lugar onde ela acontece.

**O que caiu:** o `router → service → repository` que é padrão em projeto grande. Ele se paga quando
há mais de uma fonte de dados ou troca de ORM no horizonte; não é o caso, e adotar por hábito seria
cerimônia sem contrapartida. A mesma régua criou **uma exceção deliberada**: a rota do catálogo
chama a integração da Ticketmaster direto, sem service, porque um service ali teria como corpo
inteiro `return ticketmaster.buscar_eventos(q)` — a definição de camada de repasse que eu acabei de
recusar.

### 9 · Backend separado em FastAPI, e não Next.js full-stack

**Decidi** separar a API do frontend, com FastAPI de um lado e Next.js do outro.

**Por quê:** o núcleo do desafio é concorrência — não vender o mesmo lugar duas vezes, não validar o
mesmo ingresso duas vezes. Isso se resolve com `UPDATE` condicional e transação, e eu queria a
ferramenta que deixa isso explícito. Separar também torna o contrato da API visível, que é
justamente o que está sendo avaliado.

**O que caiu:** Next.js full-stack com Route Handlers e Prisma. Seria menos código e um deploy só,
mas empurraria a regra de concorrência para dentro do framework de tela, onde ela fica difícil de
enxergar — e apagaria a fronteira entre API e interface que o desafio pede para demonstrar.

### 10 · A interface é um jornal noturno, e o CSS é escrito à mão

**Decidi** que a listagem de shows não tem card: são filas separadas por fio, com a data na margem
esquerda, nome de artista em serifada e etiquetas em monoespaçada versalete. Chão de petróleo
`#0B1618`, rosa neon `#FF4F9A` como acento único, raio zero e sombra zero em todo o sistema. Sem
shadcn, MUI, Chakra ou Tailwind — um `globals.css` com os tokens e um `.module.css` por componente.
Nenhuma fonte é baixada.

**Por quê:** ingresso não é produto de prateleira — é o direito de entrar num lugar, numa hora. Card
com imagem, preço e botão é vocabulário de e-commerce, e carrega junto a promessa errada. O desafio
penaliza por escrito a interface que "parece gerada", e o que denuncia uma interface gerada não é
ser feia: é ser bonita de um jeito só. Biblioteca de componentes não traz só código pronto — traz
junto um vocabulário visual, e é exatamente o vocabulário que este projeto está tentando não ter: o
card arredondado com sombra sutil vem de graça, e tirá-lo depois dá mais trabalho do que nunca
tê-lo.

**O que caiu:** a fileira horizontal de cards com paleta empresarial — o formato de Sympla, Eventim
e Ingresso.com, e o que qualquer gerador entrega por padrão. Caiu junto uma lista de padrões que
proibi de propósito: faixa que varre a tela, grade de 6 a 8 cards por seção, par de título gigante
com textinho embaixo, e a linha de contexto decorativa no cabeçalho — essa última eu cheguei a
montar no protótipo e removi, porque soava gerada. Duas direções competiram antes: um jornal de
eventos londrino, editorial e claro, e uma parede de cartazes noturna; a identidade final é a fusão
— estrutura de impresso, cor de madrugada. E **o primeiro acento era âmbar `#F2A413` sobre preto
quente** — quase o `amber-500` do Tailwind, que é a receita exata do tema escuro gerado que eu tinha
acabado de listar como anti-padrão. Descartei também vermelho de jornal (colide com o vermelho de
erro e com o `INVÁLIDO` da portaria) e roxo sobre cinza (o dark mode padrão de metade das
ferramentas — trocaria um default por outro pior).

---

## O que não está pronto

O enunciado pede que o que não estiver pronto seja dito. Estes são **cortes conscientes**, não
esquecimentos:

| O quê | Por quê |
|---|---|
| **Mapa de assentos** | Escolhi venda por quantidade em setores, que o desafio aceita. O raciocínio está em [Setores por quantidade](#1--setores-por-quantidade-não-mapa-de-assentos) |
| **Cadastro de organizador pela interface** | **Adiado, não descartado** — sem uma forma de decidir quem merece o papel, a rota separada seria o mesmo buraco com outro endereço. **Portaria fica de fora em qualquer cenário**, porque ela só valida onde foi escalada |
| **Cancelamento pelo cliente** | O modelo já suporta (a reserva tem estado que devolve estoque); faltam endpoint e tela |
| **Editar evento depois de ele ter vendido** | Editar existe — data, setores e escala —, mas só enquanto `vendidos == 0` em **todos** os setores. Descartei travar só com reserva paga: o preço já vai congelado na reserva, então não haveria prejuízo, mas quem estivesse digitando o cartão veria o preço mudar na tela no meio da compra. `nome`, `imagem`, `local` e `cidade` vêm do catálogo e não são campo de formulário em caso nenhum |
| **Evento sem entrada no catálogo da Ticketmaster** | Não dá para publicar um cover de bar ou um evento independente. É consequência direta de o enunciado pedir que o evento nasça "a partir de" a API externa |
| **Busca do organizador limitada ao Brasil** | `countryCode=BR` é fixo na chamada à Discovery. Sem ele, buscar "metallica" devolve os vinte primeiros shows do mundo e nenhum brasileiro entra — a tela pareceria quebrada justamente para quem avalia |
| **Pagamento real** | O gateway é simulado, com recusa determinística para que os dois caminhos sejam testáveis: cartão terminado em `0002` é recusado, qualquer outro aprova |
| **O Pix é encenação** | O QR e o código copia-e-cola são gerados na tela, aleatórios, e não chegam ao servidor — um app de banco recusa aquele código. O botão "cobrança paga" é o atalho do avaliador. Simular cobrança de verdade exigiria provedor, webhook e conciliação; o caminho que o enunciado pontua é a **recusa**, e ela vive no cartão. A tela avisa em letras que a cobrança é fictícia |
| **Os dados do comprador não são guardados** | O checkout pede nome, e-mail, CPF e telefone porque um checkout sem eles não parece um checkout. Só o **nome** sobrevive à requisição — os outros três são validados no formato e descartados. Pelo mesmo motivo o CPF valida só o formato, sem dígito verificador: o algoritmo rejeita `111.111.111-11`, que é exatamente o que se digita quando a tela manda usar dado fictício |
| **O portão fecha no instante exato do término, sem tolerância** | Às 02h00 em ponto de um show marcado até 02h00, o retardatário na fila não entra mais. Descartei uma tolerância simétrica às duas horas com que a porta abre — ela cobriria esse caso, e o preço seria o sistema discordando do número que o organizador acabou de digitar. A folga mora na hora declarada: quem quiser margem marca 03h em vez de 02h |
| **O corte das telas públicas é no início do show, não no fim** | Um evento some da programação, da busca e da criação de reserva no minuto em que começa — e não quando acaba. Isso deixa a portaria trabalhando do outro lado do corte. Mover o corte para o término é o comportamento certo do mundo real, mas custa quatro rotas públicas, a criação de reserva, a edição, o roteiro de avaliação e uma pergunta de produto nova — vender ingresso durante o show. É uma feature boa que merece decisão própria |
| **A página pode dizer "Esgotado" com reservas já vencidas** | A expiração é [preguiçosa por decisão](#7--a-expiração-da-reserva-é-preguiçosa-não-agendada). Na prática quem clicar em reservar consegue: no momento em que o estoque importa, ele já está correto |
| **Nada limita quantas reservas uma conta segura ao mesmo tempo** | O teto de 6 ingressos é **por compra**, não por pessoa: uma conta autenticada chamando `POST /reservas` em laço prende o show inteiro por 10 minutos, renováveis. Fechar exige um limite de reservas `PENDENTE` por cliente e evento, com código de erro e tela próprios; escolhi declarar em vez de implementar. Não afeta o roteiro de avaliação, que é um comprador de cada vez |
| **Nenhuma rota tem limite de chamadas** | Não há rate limit por IP nem por conta em lugar nenhum, e não há bloqueio por tentativas de login. É a defesa direta contra força bruta e exige contador com expiração compartilhado entre instâncias — infraestrutura que não se paga no prazo. O que **está** feito é o custo de ~50ms por tentativa e a resposta idêntica para e-mail inexistente e senha errada, inclusive no tempo |
| **A programação devolve no máximo 200 shows** | Teto fixo em vez de paginação. Paginar seria rota, schema, tela e testes para um contrato que nenhuma tela consome. Quando apertar, o conserto é a paginação — não aumentar o número |
| **Recuperação de senha** | O enunciado dispensa, e exigiria envio de e-mail. É por não existir que o cadastro tem confirmação de senha: sem ela, uma letra errada seria conta perdida para sempre |
| **Enumeração de e-mail no cadastro** | O `409` revela que aquele e-mail tem conta — o que o login gasta um hash fantasma para não revelar. É inevitável: o login esconde porque as duas respostas cabem numa frase só; o cadastro ou diz que o e-mail já existe, ou mente |
| **Editar a própria conta** | A `/conta` mostra nome, e-mail e papel, e permite sair. Trocar nome ou senha não entrou no escopo |
| **A câmera da portaria não abre por IP na rede local** | `getUserMedia` só existe em **contexto seguro**: `https` ou `localhost`, e nada mais. Na Vercel funciona, e no `localhost:3000` também — mas um celular apontado para `http://192.168.0.x:3000` não recebe a câmera, e nenhum código meu contorna isso. A tela detecta o caso e explica, com o campo manual continuando a funcionar. Para testar a câmera no celular, use a URL da Vercel |
| **Integração contínua (testes a cada push)** | Não há GitHub Actions. CI aqui exigiria subir um PostgreSQL no runner, porque a suíte roda contra banco de verdade. O **deploy** contínuo existe e é automático nas duas plataformas. O que existe no lugar do CI: o `--locked` do build **falha** se o lockfile divergir do `pyproject.toml`, e a migração roda antes de a aplicação atender |
| **Teste automatizado no frontend** | Não há Vitest, Testing Library nem Playwright, e é decisão. As invariantes que valem ponto — não vender o mesmo lugar duas vezes, não validar o mesmo ingresso duas vezes, assinatura do QR — moram todas no backend, que tem `pytest` desde a primeira story. O frontend é verificado por `npm run build`, `tsc --noEmit`, ESLint e conferência no navegador |
| **Sete arestas conhecidas de interface** | Achados dos meus code reviews que escolhi declarar em vez de consertar, porque cada um pede refactor de componente e não patch. Estão listadas [logo abaixo da tabela](#as-sete-arestas-de-interface) |
| **Ambiente separado para os Previews** | Os deploys de branch da Vercel apontam para o **mesmo banco de produção**. A alternativa deixaria todo Preview com o login quebrado em silêncio, que é pior; um segundo banco é infraestrutura que não se paga em sete dias |
| **Domínio próprio** | Custa dinheiro e propagação de DNS, e não acrescenta nada ao que está sendo avaliado |

### As sete arestas de interface

Saíram dos meus code reviews e eu **escolhi declará-las em vez de consertá-las**: cada uma pede
refactor de componente, não um patch, e nenhuma bloqueia o roteiro de avaliação.

1. **A chamada à API não tem timeout.** Se a rede pendurar, o botão fica em *"Reservando…"* sem
   resolver, e a única saída é recarregar sem saber se a reserva foi criada
2. **Trocar Cartão → Pix → Cartão apaga o cartão já digitado.** Os quatro campos são não
   controlados e o bloco é montado condicionalmente; o código do Pix é preservado, o do cartão não
3. **Editar no meio do CPF ou do telefone joga o cursor para o fim.** A máscara remonta o valor
   inteiro a cada tecla sem restaurar a posição do cursor
4. **A validade do cartão é o único campo sem máscara.** Digitar `0826` sem a barra volta `422`, e a
   tela mostra o erro sobre o formulário inteiro sem destacar o campo culpado
5. **Sessão expirada no stepper e no checkout não oferece caminho de volta** — mostra a frase de
   erro sem link para relogar, embora o padrão já exista na tela de publicar
6. **O chip de cidade ignora o filtro de período.** Único show em BH daqui a 60 dias, com o filtro
   de 7 dias ligado: o chip aparece e devolve lista vazia
7. **No Safari, a arte quebrada da Ticketmaster reaparece.** O pseudo-elemento que a cobre não é
   desenhado sobre `<img>` naquele motor, e o ícone de imagem quebrada volta ao meio da capa

Os **24 achados adiados**, cada um com onde está e o que fecharia, estão em
[`deferred-work.md`](_bmad-output/implementation-artifacts/deferred-work.md).

---

## Uso de IA

O enunciado pede que eu conte quais ferramentas usei, em que partes, e o que foi feito sem IA. A
resposta completa está em **[docs/uso_de_ia.md](docs/uso_de_ia.md)**.

O resumo: usei **Claude Code**, com o BMAD Method instalado, para **quebrar o projeto em epics e
stories** e para **escrever o código** a partir de specs que eu redigi. **As decisões foram minhas**
— arquitetura, identidade visual, modelo de venda, recorte de escopo, o que entra e o que fica de
fora. Cada uma delas está na seção acima, com a alternativa que eu descartei e o motivo. Os
artefatos do processo estão versionados em [`_bmad-output/`](_bmad-output/), inclusive os `.memlog.md`
com as sessões completas.
