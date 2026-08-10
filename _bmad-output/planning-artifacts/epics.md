---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
status: final
inputDocuments:
  - 'docs/desafio-elite-dev.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-elite-dev-RockHub-2026-08-09/ARCHITECTURE-SPINE.md'
  - '_bmad-output/brainstorming/brainstorm-plataforma-eventos-ingressos-2026-08-08/brainstorm-intent.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-elite-dev-RockHub-2026-08-09/EXPERIENCE.md'
---

# elite-dev-RockHub - Epic Breakdown

## Overview

Quebra em epics e stories da Plataforma de Eventos e Ingressos. Cada story é dimensionada para
virar **exatamente um commit**.

Não há PRD: o desafio já veio especificado, e `docs/desafio-elite-dev.md` cumpre esse papel.
As decisões técnicas vinculantes (AD-1 a AD-15) estão na espinha de arquitetura.

## Requirements Inventory

### Functional Requirements

**Front-End**

- **FR1:** Navegação e busca pelos eventos publicados, exibindo data, local e preço
- **FR2:** Criação e gerenciamento dos eventos pelo organizador
- **FR3:** Fluxo de reserva com seleção da quantidade de ingressos por setor (pista, VIP, camarote)
- **FR4:** Pagamento simulado, contemplando a confirmação **e também a recusa**
- **FR5:** Área "Meus ingressos", exibindo o ingresso e o seu código em QR
- **FR6:** Tela de portaria com retorno claro: `VALIDO`, `INVALIDO`, `JA_UTILIZADO` ou `EVENTO_ERRADO`
- **FR7:** Leitura do QR pela câmera na portaria, com digitação manual do código como alternativa

**Back-End**

- **FR8:** Gestão das chamadas à API Ticketmaster Discovery v2
- **FR9:** Autenticação com três papéis distintos: Organizador, Cliente e Portaria
- **FR10:** Armazenamento dos eventos, das reservas e dos ingressos
- **FR11:** Garantia de que o mesmo lugar não seja vendido duas vezes
- **FR12:** Geração do ingresso com um código em QR que não possa ser forjado
- **FR13:** Compartilhamento de um ingresso via link gerado pela aplicação
- **FR14:** Validação do ingresso na portaria, garantindo que não seja validado duas vezes
- **FR15:** Cobrança simulada, sem transação financeira real

**Acrescentado pelo Igor (não consta no enunciado)**

- **FR16:** Vínculo entre usuário de portaria e eventos específicos, definido pelo organizador na
  publicação. Fecha o furo de autorização em que qualquer conta de portaria validaria qualquer
  evento

### NonFunctional Requirements

- **NFR1:** README detalhado com passo a passo de configuração e execução. O que não estiver
  funcionando **deve ser mencionado** — ausência de explicação impacta a nota
- **NFR2:** Dados de teste semeados: um organizador, **dois** clientes, um usuário de portaria e
  ao menos um evento publicado com ingressos disponíveis
- **NFR3:** Aplicação publicada — frontend na Vercel, backend e banco na Railway (vale +1 ponto)
- **NFR4:** Repositório público no GitHub, com commits ao longo da semana e mensagens descritivas
- **NFR5:** Documentação do uso de IA: quais ferramentas, em que partes, e o que foi feito sem IA
- **NFR6:** Prazo de 7 dias corridos — o fluxo obrigatório completo tem prioridade sobre refinamento
- **NFR7:** Interface que não pareça gerada. Anti-padrões proibidos: faixa/marquee que varre a
  tela, grid de 6–8 cards de seção, par título-gigante-com-textinho, fileira horizontal de cards
  com paleta empresarial
- **NFR8:** Os três READMEs (raiz, frontend, backend) são atualizados ao fim de toda story, em
  primeira pessoa, registrando o que mudou e **por quê**

### Additional Requirements

Da espinha de arquitetura — vinculantes, código que as contraria está errado:

- **Sem starter template pronto.** O projeto nasce do zero: `create-next-app` no frontend e
  scaffold FastAPI no backend. Isso define a Story 1.1
- **AD-1:** Ticketmaster só é chamada em endpoints do organizador; ao publicar, os dados viram
  cópia no banco. Nenhum endpoint de cliente ou portaria toca a API externa
- **AD-2:** `TICKETMASTER_API_KEY` só existe no ambiente do backend
- **AD-3:** Estoque muda por `UPDATE` condicional atômico + `CHECK` constraint
- **AD-4:** Reserva com máquina de estados, expiração preguiçosa de 10 minutos, sem worker
- **AD-5:** QR carrega `ID.ASSINATURA` com HMAC-SHA256
- **AD-6:** Validação é `UPDATE ... WHERE usado_em IS NULL`
- **AD-7:** Portaria só valida evento em que foi escalada; publicar exige ao menos uma portaria
- **AD-8:** Compartilhamento usa token opaco revogável, separado da assinatura
- **AD-9:** Autorização por papel declarada como dependência do FastAPI
- **AD-10:** `PaymentGateway` como interface; cartão terminando em `0002` recusa
- **AD-11:** Dinheiro em centavos, tempo em UTC
- **AD-12:** Setores definidos pelo organizador, não fixos no código
- **AD-13:** `setor.vendidos` é a única fonte de verdade da disponibilidade
- **AD-14:** Ingresso só nasce dentro da transação que marca a reserva como `PAGA`
- **AD-15:** Senha em Argon2id; JWT em cookie `httpOnly`, 8 horas
- **Paradigma:** `routers → services → models`. Sem camada de repositórios
- **Migrações:** toda mudança de schema é migração Alembic versionada

### UX Design Requirements

Do par `DESIGN.md` + `EXPERIENCE.md` (direção **"jornal noturno"**), com protótipo navegável em
`mockups/proto-jornal-noturno.html`. Medidas e microcopy são provisórios; o que está listado aqui
é o que **não** muda sem decisão do Igor.

- **UX-DR1:** Sistema de tokens da identidade: `breu #0E0D0C`, `breu2 #151311`, `cal #EDE8DC`,
  `fumaca #8F877A`, `ambar #F2A413`, `brasa #D93B2B`, `verde #3FA96B`, `fio #2A2622`.
  Âmbar é o **acento único** — nenhum segundo acento decorativo
- **UX-DR2:** Pareamento tipográfico obrigatório: serifada (Georgia) para nome próprio, título e
  valor; monoespaçada em versalete com letterspacing largo para etiqueta, código, hora e estado.
  Nenhuma fonte externa
- **UX-DR3:** Listagem **sem card**: filas separadas por fio, data na margem esquerda. Raio zero,
  sombra zero em todo o sistema. É o que materializa "ingresso não é produto de prateleira"
- **UX-DR4:** Componente `chamada-principal` (lead de jornal) no topo da listagem — arte, kicker,
  manchete serifada, standfirst em itálico e ficha de três dados
- **UX-DR5:** Os quatro vereditos da portaria em **três canais simultâneos** — cor, palavra e
  símbolo: `VALIDO` verde ✓, `INVALIDO` brasa ✕, `JA_UTILIZADO` cinza ↺ (neutro de propósito, não
  é fraude), `EVENTO_ERRADO` âmbar ⤫
- **UX-DR6:** Ergonomias distintas por papel. Cliente e organizador desktop-first; **portaria é a
  única superfície mobile-first**, coluna única, alvo mínimo de 44px, tipografia legível a três
  metros
- **UX-DR7:** Cliente nunca vê contagem exata de estoque — só `Disponível`, `Últimos ingressos` ou
  `Esgotado`, mais uma barra de proporção. Organizador e portaria veem números exatos
- **UX-DR8:** Voz jornalística: específica, curta, sem entusiasmo comercial, sem exclamação. Erro
  diz o que aconteceu **e** o que fazer agora
- **UX-DR9:** Piso de acessibilidade: contraste AA em tudo, nenhuma informação transmitida só por
  cor, foco visível em âmbar (nunca `outline:none`), `<label>` em todo campo, resultado da
  validação anunciado por `aria-live="assertive"`, QR sempre acompanhado do código em texto
- **UX-DR10:** Os cinco anti-padrões proibidos (NFR7): marquee/faixa que varre a tela; grade de 6–8
  cards de seção; par título-gigante-com-textinho; fileira horizontal de cards com paleta
  empresarial; linha de contexto decorativa no masthead. Nenhuma animação de travessia lateral;
  transições só de cor, até 120ms
- **UX-DR11:** QR sempre renderizado sobre fundo claro (`cal`), nunca sobre o breu — legibilidade
  de leitor óptico

**Responsividade — onde ela mora.** O corte é **900px** (`EXPERIENCE.md#Responsive & Platform`).
Cliente e organizador são desktop-first e **colapsam** abaixo disso; a portaria é mobile-first e é
coluna única sempre. Cada story que cria tela carrega o seu próprio critério de aceite para isso —
**não existe uma story de "deixar responsivo" no fim**, porque o breakpoint só faz sentido escrito
junto da grade que ele colapsa, e trabalho de layout adiado para o último dia é onde o prazo morre.

### FR Coverage Map

| FR | Epic | Onde é entregue |
|---|---|---|
| FR1 · Navegação e busca de eventos | Epic 3 | Listagem em filas com busca e filtros |
| FR2 · Criação e gestão de eventos | Epic 2 | Fluxo de publicação em três passos |
| FR3 · Reserva por quantidade em setor | Epic 3 | Stepper por setor + reserva com estoque atômico |
| FR4 · Pagamento simulado (aprova e recusa) | Epic 3 | Checkout + `FakePaymentGateway` |
| FR5 · Meus ingressos com QR | Epic 4 | Lista de ingressos e canhoto |
| FR6 · Tela de portaria com 4 retornos | Epic 5 | Veredito em três canais |
| FR7 · Leitura por câmera + digitação manual | Epic 5 | Leitor com alternativa manual |
| FR8 · Chamadas à Ticketmaster Discovery | Epic 2 | Busca no catálogo, só para o organizador |
| FR9 · Autenticação com três papéis | Epic 1 | Argon2id + JWT em cookie `httpOnly` |
| FR10 · Armazenamento de eventos, reservas e ingressos | Epic 1 | Esquema e migrações; tabelas evoluem nos epics seguintes |
| FR11 · Mesmo lugar não vendido duas vezes | Epic 3 | `UPDATE` condicional + `CHECK` |
| FR12 · QR não forjável | Epic 3 | Assinatura HMAC na emissão |
| FR13 · Compartilhamento por link | Epic 4 | Token opaco revogável + rota pública |
| FR14 · Validação sem duplicar | Epic 5 | `UPDATE ... WHERE usado_em IS NULL` |
| FR15 · Cobrança simulada sem transação real | Epic 3 | Interface `PaymentGateway` |
| FR16 · Vínculo portaria ↔ evento | Epic 2 | Escalação obrigatória na publicação |

## Epic List

### Epic 1: Fundação, acesso e primeiro deploy
O projeto roda na máquina e **em produção**, e as três pessoas entram com papéis distintos:
organizador, cliente e portaria. Ao fim deste epic existe uma aplicação publicada, com banco,
migrações, dados semeados e a identidade visual aplicada — ainda sem nenhuma regra de negócio.

**FRs cobertos:** FR9, FR10
**NFRs:** NFR1, NFR2, NFR3, NFR4, NFR8 · **UX:** UX-DR1, UX-DR2, UX-DR9
**Estimativa:** 7 a 8 stories

> **Por que deploy já no primeiro epic:** publicar uma aplicação vazia leva minutos; publicar no dia
> 7, com tudo pronto, é onde o prazo costuma morrer. Subir cedo transforma o deploy em rotina em vez
> de evento.

### Epic 2: Publicação de eventos pelo organizador
O organizador busca a atração no catálogo da Ticketmaster, define data, local e setores com preço e
capacidade, escala quem vai validar na porta, e publica. Ao fim deste epic **existem eventos reais no
sistema**, criados pela interface e não por seed.

**FRs cobertos:** FR2, FR8, FR16
**Arquitetura:** AD-1, AD-2, AD-7, AD-12 · **UX:** UX-DR7
**Estimativa:** 5 a 6 stories

### Epic 3: Descoberta e compra
O cliente encontra o show, escolhe setor e quantidade, paga — com os dois desfechos, aprovado e
recusado — e recebe ingressos com código assinado. É o epic que carrega as duas garantias mais
pontuadas do desafio: não vender o mesmo lugar duas vezes e não permitir QR forjado.

**FRs cobertos:** FR1, FR3, FR4, FR11, FR12, FR15
**Arquitetura:** AD-3, AD-4, AD-5, AD-10, AD-13, AD-14 · **UX:** UX-DR3, UX-DR4, UX-DR7, UX-DR8
**Estimativa:** 8 a 9 stories

### Epic 4: Meus ingressos e compartilhamento
O cliente acessa os ingressos que comprou, vê o canhoto com o QR, e manda para quem vai com ele por
um link que pode revogar depois.

**FRs cobertos:** FR5, FR13
**Arquitetura:** AD-8 · **UX:** UX-DR11
**Estimativa:** 4 stories

### Epic 5: Portaria
Quem trabalha na porta entra, vê só os eventos em que foi escalado, escolhe onde vai trabalhar, lê o
QR pela câmera — ou digita o código quando a câmera falha — e recebe um dos quatro retornos. O mesmo
ingresso nunca passa duas vezes, nem quando dois leitores escaneiam no mesmo instante.

**FRs cobertos:** FR6, FR7, FR14
**Arquitetura:** AD-6, AD-7 · **UX:** UX-DR5, UX-DR6
**Estimativa:** 5 a 6 stories

### Epic 6: Avaliação sem atrito
Quem avalia percorre o fluxo inteiro sem montar nada e entende as decisões antes de abrir o código.
Não é epic de usuário final — é de **usuário avaliador**, que neste projeto é quem importa.

**NFRs cobertos:** NFR1, NFR2, NFR5, NFR6
**Estimativa:** 3 a 4 stories

---

## Epic 1: Fundação, acesso e primeiro deploy

O projeto roda na máquina e em produção, e as três pessoas entram com papéis distintos. Ao fim
deste epic existe uma aplicação publicada, com banco, migrações, dados semeados e a identidade
visual aplicada — ainda sem nenhuma regra de negócio.

### Story 1.1: Esqueleto do backend que responde

Como desenvolvedor,
quero um backend FastAPI que sobe e responde a uma chamada de saúde,
para ter uma base verificável antes de escrever qualquer regra.

**Acceptance Criteria:**

**Given** o repositório recém-clonado com Python 3.12
**When** eu instalo as dependências e subo o servidor
**Then** `GET /saude` responde `200` com `{"status": "ok"}`
**And** `/docs` mostra a documentação automática do FastAPI

**Given** a estrutura de pastas
**When** eu a inspeciono
**Then** existem `app/api/`, `app/services/`, `app/models/`, `app/schemas/`, `app/core/`
**And** não existe pasta `repositories/` — o paradigma é `routers → services → models`

**Given** qualquer configuração sensível
**When** eu procuro no código
**Then** ela é lida de variável de ambiente por uma classe `Settings` do Pydantic
**And** nenhum segredo está versionado

### Story 1.2: Esqueleto do frontend com a identidade aplicada

Como visitante,
quero abrir a aplicação e ver a identidade "jornal noturno",
para que toda tela construída depois já nasça no sistema visual certo.

**Acceptance Criteria:**

**Given** um projeto Next.js 16 com App Router
**When** eu abro a raiz
**Then** vejo o masthead com o logotipo em serifada sobre fio duplo
**And** o fundo é `#0E0D0C` e o texto `#EDE8DC`

**Given** os tokens de `DESIGN.md`
**When** eu inspeciono o CSS
**Then** as nove cores existem como variáveis CSS
**And** nenhum elemento tem `border-radius` ou `box-shadow`
**And** nenhuma fonte externa é carregada

**Given** o masthead
**When** eu o inspeciono
**Then** ele contém apenas logotipo e navegação
**And** não há linha de contexto decorativa (data, contador, subtítulo) — UX-DR10

### Story 1.3: Modelo de usuário e primeira migração

Como desenvolvedor,
quero a tabela de usuários criada por migração versionada,
para que o banco possa ser reconstruído do zero de forma reproduzível.

**Acceptance Criteria:**

**Given** um banco PostgreSQL vazio
**When** eu rodo `alembic upgrade head`
**Then** a tabela `usuario` existe com `id` UUID, `nome`, `email` único, `senha_hash` e `papel`
**And** `papel` aceita apenas `ORGANIZADOR`, `CLIENTE` ou `PORTARIA`

**Given** o projeto
**When** eu procuro criação de schema
**Then** não existe `create_all` fora de teste — só migrações Alembic

### Story 1.4: Entrar com e-mail e senha

Como organizador, cliente ou portaria,
quero entrar com meu e-mail e senha,
para acessar o que o meu papel permite.

**Acceptance Criteria:**

**Given** uma conta existente
**When** eu envio e-mail e senha corretos para `POST /auth/login`
**Then** recebo `200` e um cookie `httpOnly`, `Secure`, `SameSite=Lax` com o JWT
**And** o JWT expira em 8 horas e carrega `sub` e `papel`

**Given** uma senha gravada no banco
**When** eu a inspeciono
**Then** ela é um hash Argon2id — nunca texto puro nem hash reversível

**Given** credenciais erradas
**When** eu tento entrar
**Then** recebo `401` com `{"erro": {"codigo": "CREDENCIAIS_INVALIDAS", ...}}`
**And** a mensagem não revela se o e-mail existe

**Given** que estou autenticado
**When** eu chamo `POST /auth/logout`
**Then** o cookie é limpo

### Story 1.5: Cadastro de cliente

Como visitante,
quero criar minha conta de cliente,
para poder comprar ingressos.

**Acceptance Criteria:**

**Given** um e-mail ainda não cadastrado
**When** eu envio nome, e-mail e senha para `POST /auth/cadastro`
**Then** a conta é criada com papel `CLIENTE` e eu já entro logado

**Given** um e-mail já cadastrado
**When** eu tento cadastrar de novo
**Then** recebo `409` com código `EMAIL_JA_CADASTRADO`

**Given** o formulário de cadastro
**When** eu o navego por teclado
**Then** todo campo tem `<label>` associado e o foco é visível em âmbar — UX-DR9

### Story 1.6: Cada papel só acessa o que lhe cabe

Como o sistema,
quero recusar acesso fora do papel,
para que a autorização não dependa de disciplina em cada handler.

**Acceptance Criteria:**

**Given** uma rota que exige papel `ORGANIZADOR`
**When** um cliente autenticado a chama
**Then** recebo `403`
**And** a verificação vem de uma dependência do FastAPI na assinatura, não de `if` no corpo — AD-9

**Given** uma rota autenticada
**When** eu a chamo sem cookie
**Then** recebo `401`

**Given** `GET /auth/eu`
**When** eu chamo autenticado
**Then** recebo meu nome, e-mail e papel

### Story 1.7: Dados semeados para avaliação

Como avaliador,
quero contas prontas para os três papéis,
para percorrer o fluxo sem cadastrar nada.

**Acceptance Criteria:**

**Given** um banco migrado
**When** eu rodo o comando de seed
**Then** existem um organizador, **dois** clientes e um usuário de portaria — NFR2
**And** as credenciais estão documentadas no README

**Given** que o seed já rodou
**When** eu rodo de novo
**Then** ele não duplica contas nem falha

### Story 1.8: Backend e banco no ar na Railway

Como avaliador,
quero acessar a API publicada,
para ver o projeto funcionando sem instalar nada.

**Acceptance Criteria:**

**Given** o projeto na Railway
**When** eu acesso a URL pública
**Then** `/saude` responde `200`
**And** as migrações rodaram e o seed foi aplicado

**Given** as variáveis de ambiente em produção
**When** eu as inspeciono
**Then** `DATABASE_URL`, `JWT_SECRET`, `TICKET_SIGNING_SECRET` e `TICKETMASTER_API_KEY` existem só lá

### Story 1.9: Frontend no ar na Vercel

Como avaliador,
quero abrir a aplicação publicada,
para percorrer as telas pelo navegador.

**Acceptance Criteria:**

**Given** o frontend na Vercel
**When** eu abro a URL pública
**Then** a aplicação carrega com a identidade visual aplicada

**Given** a aplicação publicada
**When** eu faço login com uma conta semeada
**Then** o login funciona contra o backend da Railway
**And** o cookie de sessão é aceito entre os dois domínios (CORS e `SameSite` configurados)

---

## Epic 2: Publicação de eventos pelo organizador

O organizador busca a atração no catálogo da Ticketmaster, define data, local e setores, escala
quem vai validar na porta, e publica. Ao fim deste epic existem eventos reais no sistema, criados
pela interface e não por seed.

### Story 2.1: Cliente da Ticketmaster com a chave protegida

Como o sistema,
quero falar com a API Discovery a partir do servidor,
para nunca expor a credencial e não depender dela no caminho do cliente.

**Acceptance Criteria:**

**Given** uma busca por termo
**When** o serviço chama a Ticketmaster
**Then** a chave vai como query param a partir do backend — AD-2
**And** nenhuma variável `NEXT_PUBLIC_` contém credencial

**Given** que a Ticketmaster está fora do ar ou estourou o limite
**When** o organizador busca
**Then** recebo erro tratado com código `CATALOGO_INDISPONIVEL`
**And** a aplicação não quebra

**Given** a resposta da API
**When** ela é convertida
**Then** vira um schema próprio com nome, atração, imagem, local e id externo — o formato da
Ticketmaster não vaza para o resto do sistema

### Story 2.2: Buscar a atração no catálogo

Como organizador,
quero procurar o show que vou publicar,
para não digitar os dados na mão.

**Acceptance Criteria:**

**Given** que estou autenticado como organizador
**When** eu busco por um termo em `GET /organizador/catalogo?q=`
**Then** recebo uma lista com nome, imagem, local e identificador de origem

**Given** a mesma rota
**When** um cliente ou a portaria a chama
**Then** recebo `403` — só o organizador toca o catálogo (AD-1)

**Given** a tela de busca
**When** eu vejo os resultados
**Then** eles aparecem em filas com fio, sem card — UX-DR3
**And** cada item mostra a origem (`Ticketmaster · id`)

### Story 2.3: Modelo de evento e setor

Como desenvolvedor,
quero as tabelas de evento e setor criadas por migração,
para que preço e capacidade pertençam ao setor, não ao evento.

**Acceptance Criteria:**

**Given** o banco migrado
**When** eu inspeciono o schema
**Then** `evento` tem `id` UUID, `organizador_id`, `nome`, `data_hora` TIMESTAMPTZ, `local`,
`cidade`, `imagem_url`, `origem_externa_id` e `publicado_em`
**And** `setor` tem `id`, `evento_id`, `nome`, `capacidade`, `vendidos` e `preco_centavos`

**Given** a tabela `setor`
**When** eu tento gravar `vendidos` negativo ou maior que `capacidade`
**Then** o banco recusa por constraint `CHECK` — AD-3

**Given** qualquer valor monetário
**When** eu o inspeciono
**Then** é inteiro em centavos, nunca `float` — AD-11

### Story 2.4: Publicar um evento com seus setores

Como organizador,
quero publicar o evento com data, local e setores,
para colocá-lo à venda.

**Acceptance Criteria:**

**Given** uma atração escolhida no catálogo
**When** eu publico com data, hora, local e uma lista de setores
**Then** o evento é gravado com os dados do catálogo **copiados** para o banco — AD-1
**And** cada setor nasce com `vendidos = 0`

**Given** que a Ticketmaster mude o registro depois
**When** eu abro o evento publicado
**Then** os dados continuam os do momento da publicação

**Given** um evento sem nenhum setor
**When** eu tento publicar
**Then** recebo `422` com código `EVENTO_SEM_SETOR`

**Given** a tela de publicação
**When** eu a uso
**Then** vejo os passos numerados e os números exatos de capacidade — UX-DR7

**Given** uma tela abaixo de 900px
**When** eu preencho o formulário
**Then** os campos ocupam a largura inteira, um por linha
**And** nada transborda na horizontal

### Story 2.5: Escalar quem valida na porta

Como organizador,
quero indicar qual usuário de portaria vai trabalhar no meu evento,
para que ninguém de fora consiga validar ingressos dele.

**Acceptance Criteria:**

**Given** a publicação de um evento
**When** eu não escalo nenhum usuário de portaria
**Then** a publicação é recusada com código `EVENTO_SEM_PORTARIA` — AD-7

**Given** o banco migrado por esta story
**When** eu inspeciono o schema
**Then** existe a tabela `evento_portaria` com `evento_id` e `usuario_id`, chave primária composta

**Given** que escalei um usuário de portaria
**When** o evento é publicado
**Then** existe registro em `evento_portaria` ligando os dois

**Given** que tento escalar uma conta que não tem papel `PORTARIA`
**When** eu publico
**Then** recebo `422`

**Given** a tela
**When** eu chego no passo de escalação
**Then** o texto explica que só quem for escalado poderá validar ingressos deste evento

### Story 2.6: Ver e gerenciar meus eventos

Como organizador,
quero ver os eventos que publiquei,
para acompanhar o que está em cartaz.

**Acceptance Criteria:**

**Given** que sou organizador com eventos publicados
**When** abro "Meus eventos"
**Then** vejo cada evento com data, local, setores e **números exatos** de vendidos e capacidade

**Given** eventos de outro organizador
**When** eu abro minha lista
**Then** eles não aparecem

---

## Epic 3: Descoberta e compra

O cliente encontra o show, escolhe setor e quantidade, paga — com os dois desfechos — e recebe
ingressos com código assinado. Carrega as duas garantias mais pontuadas do desafio.

### Story 3.1: Ver a programação

Como visitante,
quero ver os eventos publicados com data, local e preço,
para descobrir o que está em cartaz.

**Acceptance Criteria:**

**Given** eventos publicados
**When** abro a página inicial
**Then** vejo cada um em fila com data à esquerda, nome em serifada, local e preço a partir de
**And** eventos não publicados não aparecem

**Given** a listagem
**When** eu a inspeciono
**Then** não há card, sombra nem canto arredondado — UX-DR3
**And** as filas são separadas por fio de 1px

**Given** um evento esgotado
**When** ele aparece na lista
**Then** exibe selo "Esgotado" em `brasa` e não é clicável

**Given** a listagem
**When** eu procuro contagem de ingressos
**Then** nenhum número absoluto de estoque aparece — UX-DR7

**Given** uma tela abaixo de 900px
**When** abro a programação
**Then** a fila colapsa de quatro para duas colunas — data à esquerda, o resto num bloco
**And** nada transborda na horizontal
**And** os fios continuam alinhados de ponta a ponta

### Story 3.2: Buscar e filtrar a programação

Como visitante,
quero buscar por artista, casa ou cidade,
para chegar rápido ao show que me interessa.

**Acceptance Criteria:**

**Given** a barra de busca
**When** eu digito um termo
**Then** a listagem mostra só os eventos cujo nome, local ou cidade batem

**Given** um filtro de cidade ou período
**When** eu o aciono
**Then** a listagem reduz e o filtro ativo fica marcado em âmbar

**Given** uma busca sem resultado
**When** ela termina
**Then** vejo "Nenhum show encontrado para essa busca", sem ilustração nem botão grande — UX-DR8

### Story 3.3: Chamada principal na programação

Como visitante,
quero uma chamada de destaque no topo,
para a página parecer uma capa de jornal e não uma tabela.

**Acceptance Criteria:**

**Given** que há eventos publicados
**When** abro a programação
**Then** o próximo evento aparece como chamada principal com arte, kicker, manchete serifada,
standfirst em itálico e ficha de três dados — UX-DR4

**Given** a chamada principal
**When** eu a inspeciono
**Then** existe **uma só** por tela
**And** a ficha não mostra contagem de ingressos

**Given** que não há nenhum evento publicado
**When** abro a programação
**Then** a chamada não é renderizada e vejo o estado vazio

**Given** uma tela abaixo de 900px
**When** eu vejo a chamada principal
**Then** arte e texto empilham numa coluna só, a arte acima — UX-DR6
**And** a ficha de três dados quebra em linha sem cortar nenhum valor

### Story 3.4: Ver o evento e seus setores

Como cliente,
quero ver os setores com preço e disponibilidade,
para escolher onde quero ficar.

**Acceptance Criteria:**

**Given** um evento publicado
**When** abro sua página
**Then** vejo nome, data, local, endereço e a lista de setores com preço

**Given** cada setor
**When** eu o vejo
**Then** a disponibilidade aparece como `Disponível`, `Últimos ingressos` ou `Esgotado`, com barra
de proporção — nunca número absoluto (UX-DR7, AD-13)

**Given** um setor esgotado
**When** eu o vejo
**Then** ele aparece esmaecido e sem stepper de quantidade

**Given** o stepper
**When** eu ajusto a quantidade
**Then** o total recalcula no rodapé fixo, sem confirmação

**Given** uma tela abaixo de 900px
**When** abro a página do evento
**Then** a ficha do evento e a lista de setores empilham
**And** o rodapé de compra continua fixo na base e legível

### Story 3.5: Modelo de reserva

Como desenvolvedor,
quero as tabelas de reserva e item de reserva,
para que a compra tenha estado e possa ser revertida.

**Acceptance Criteria:**

**Given** o banco migrado
**When** inspeciono o schema
**Then** `reserva` tem `id` UUID, `cliente_id`, `evento_id`, `estado`, `expira_em` e `total_centavos`
**And** `item_reserva` tem `reserva_id`, `setor_id`, `quantidade` e `preco_unitario_centavos`

**Given** o campo `estado`
**When** eu o inspeciono
**Then** aceita `PENDENTE`, `PAGA`, `RECUSADA`, `EXPIRADA` e `CANCELADA` — AD-4

### Story 3.6: Reservar sem vender o mesmo lugar duas vezes

Como cliente,
quero que meus lugares fiquem garantidos ao reservar,
para não perder a compra no meio do caminho.

**Acceptance Criteria:**

**Given** um setor com estoque
**When** eu reservo N ingressos
**Then** a reserva nasce `PENDENTE` com `expira_em` em 10 minutos
**And** o estoque foi consumido por um único `UPDATE` condicional — AD-3

**Given** duas reservas simultâneas para o último ingresso
**When** ambas executam
**Then** exatamente uma tem sucesso
**And** a outra recebe `409` com código `ESTOQUE_INSUFICIENTE`

**Given** o código do serviço
**When** eu o leio
**Then** não existe leitura de estoque seguida de escrita — a checagem está no `WHERE`

**Given** que o estoque acabou durante minha decisão
**When** eu tento reservar
**Then** vejo "Esgotou enquanto você decidia" e o próximo setor disponível é oferecido — UX-DR8

### Story 3.7: Reserva abandonada devolve o estoque

Como cliente,
quero que reservas esquecidas liberem os lugares,
para que ingresso não fique preso por quem desistiu.

**Acceptance Criteria:**

**Given** uma reserva `PENDENTE` com `expira_em` no passado
**When** eu tento pagá-la
**Then** ela vira `EXPIRADA`, o estoque volta, e recebo `409` com código `RESERVA_EXPIRADA`
**And** nada é cobrado

**Given** reservas vencidas naquele setor
**When** outra pessoa tenta reservar
**Then** as vencidas são liberadas antes da tentativa e o estoque reflete a realidade

**Given** o projeto
**When** eu procuro tarefa agendada
**Then** não existe worker nem cron — a expiração é preguiçosa (AD-4)

### Story 3.8: Pagar, com aprovação e com recusa

Como cliente,
quero pagar minha reserva,
para receber os ingressos.

**Acceptance Criteria:**

**Given** uma reserva `PENDENTE` e um cartão qualquer
**When** eu pago
**Then** a reserva vira `PAGA` e recebo confirmação

**Given** um cartão terminado em `0002`
**When** eu pago
**Then** o pagamento é recusado com código `PAGAMENTO_RECUSADO`
**And** a reserva vira `RECUSADA` e o estoque volta
**And** a tela diz que nada foi cobrado e que os lugares voltaram para a venda

**Given** o código
**When** eu o leio
**Then** o serviço de reserva depende da interface `PaymentGateway`, nunca da implementação — AD-10

**Given** o checkout
**When** eu o abro
**Then** vejo o tempo restante da reserva, sem piscar nem pressionar — UX-DR8

### Story 3.9: Receber ingressos com código não forjável

Como cliente,
quero um código de entrada que ninguém consiga inventar,
para que meu ingresso valha na porta.

**Acceptance Criteria:**

**Given** o banco migrado por esta story
**When** eu inspeciono o schema
**Then** existe a tabela `ingresso` com `id` UUID, `reserva_id`, `evento_id`, `setor_id`,
`titular_nome`, `assinatura` e `nonce`

**Given** uma reserva que acabou de ser paga
**When** os ingressos são emitidos
**Then** nasce um ingresso por unidade, cada um com `id` UUID e código próprio
**And** a emissão acontece na mesma transação da transição para `PAGA` — AD-14

**Given** o código de um ingresso
**When** eu o inspeciono
**Then** tem o formato `ID.ASSINATURA`, com assinatura HMAC-SHA256 do segredo do servidor — AD-5

**Given** um pagamento reprocessado
**When** ele executa de novo
**Then** nenhum ingresso adicional é criado

**Given** um código com assinatura adulterada
**When** ele é verificado
**Then** a verificação falha sem consultar o banco

---

## Epic 4: Meus ingressos e compartilhamento

O cliente acessa os ingressos que comprou, vê o canhoto com o QR, e manda para quem vai com ele por
um link que pode revogar depois.

### Story 4.1: Ver meus ingressos

Como cliente,
quero ver os ingressos que comprei,
para saber o que tenho e para quando.

**Acceptance Criteria:**

**Given** que comprei ingressos
**When** abro "Meus ingressos"
**Then** vejo os ativos e os já utilizados em blocos separados

**Given** um ingresso já utilizado
**When** ele aparece
**Then** está esmaecido e mostra a hora da entrada

**Given** que nunca comprei nada
**When** abro a área
**Then** vejo "Você ainda não comprou nenhum ingresso. Quando comprar, ele aparece aqui com o
código de entrada." — sem ilustração e sem botão grande (UX-DR8)

**Given** ingressos de outro cliente
**When** abro minha lista
**Then** eles não aparecem

### Story 4.2: Ver o canhoto com o QR

Como cliente,
quero ver meu ingresso com o código em QR,
para apresentar na entrada.

**Acceptance Criteria:**

**Given** um ingresso meu
**When** abro seu detalhe
**Then** vejo o canhoto com evento, data, local, setor e titular, e o QR à direita do picote

**Given** o QR
**When** eu o inspeciono
**Then** está renderizado sobre fundo claro (`cal`), nunca sobre o breu — UX-DR11
**And** o código aparece também em texto, para quem não consegue escanear (UX-DR9)

**Given** o conteúdo do QR
**When** eu o decodifico
**Then** é exatamente o código assinado do ingresso

**Given** uma tela abaixo de 900px
**When** abro o canhoto
**Then** corpo e talão empilham, e o picote tracejado vira linha horizontal
**And** o QR continua sobre fundo `cal`, do tamanho que dá para escanear — UX-DR11

### Story 4.3: Compartilhar o ingresso por link

Como cliente,
quero mandar o ingresso para quem vai comigo,
para que a pessoa entre com o próprio celular.

**Acceptance Criteria:**

**Given** o banco migrado por esta story
**When** eu inspeciono o schema
**Then** `ingresso` ganhou a coluna `share_token`, nula por padrão e com índice único

**Given** um ingresso meu
**When** eu peço para compartilhar
**Then** é gerado um `share_token` aleatório e opaco, e recebo o link `/i/TOKEN`

**Given** o link
**When** alguém sem login o abre
**Then** vê o ingresso com o QR

**Given** o `share_token`
**When** eu o comparo com o código de validação
**Then** são valores diferentes — o token de compartilhamento não substitui a assinatura (AD-8)

**Given** um token inexistente
**When** alguém tenta abrir
**Then** recebe `404`

### Story 4.4: Revogar o link compartilhado

Como cliente,
quero cortar o acesso de um link que já mandei,
para retomar o controle do meu ingresso.

**Acceptance Criteria:**

**Given** um ingresso com link ativo
**When** eu revogo
**Then** o `share_token` é apagado e o link antigo passa a responder `404`

**Given** que revoguei
**When** eu compartilho de novo
**Then** um token novo e diferente é gerado

**Given** a ação de revogar
**When** eu a aciono
**Then** ela pede confirmação — é irreversível para quem já tem o link

---

## Epic 5: Portaria

Quem trabalha na porta entra, vê só os eventos em que foi escalado, escolhe onde vai trabalhar, lê
o QR pela câmera — ou digita o código — e recebe um dos quatro retornos.

### Story 5.1: Ver onde eu trabalho hoje

Como portaria,
quero ver só os eventos em que fui escalado,
para escolher rápido onde vou trabalhar.

**Acceptance Criteria:**

**Given** que sou portaria escalado em dois eventos
**When** eu entro
**Then** vejo apenas esses dois, com nome, data, hora e casa

**Given** eventos em que não fui escalado
**When** eu abro a lista
**Then** eles não aparecem

**Given** que não fui escalado em nada
**When** eu entro
**Then** vejo "Você não foi escalado para nenhum evento"

**Given** a tela
**When** eu a uso no celular
**Then** é coluna única, com alvos de no mínimo 44px — UX-DR6

### Story 5.2: Validar o ingresso sem deixar passar duas vezes

Como o sistema,
quero decidir o resultado da validação de forma atômica,
para que o mesmo ingresso nunca seja aceito duas vezes.

**Acceptance Criteria:**

**Given** o banco migrado por esta story
**When** eu inspeciono o schema
**Then** `ingresso` ganhou as colunas `usado_em` TIMESTAMPTZ nula e `validado_por` referenciando
`usuario`

**Given** um código válido, de um ingresso ainda não usado, no evento correto
**When** a portaria valida
**Then** recebo `VALIDO` e o ingresso passa a ter `usado_em` e `validado_por` preenchidos

**Given** o mesmo ingresso
**When** ele é lido de novo
**Then** recebo `JA_UTILIZADO` com a hora da primeira entrada

**Given** dois leitores validando o mesmo ingresso no mesmo instante
**When** ambos executam
**Then** exatamente um recebe `VALIDO` e o outro `JA_UTILIZADO`
**And** o resultado vem do número de linhas afetadas pelo `UPDATE ... WHERE usado_em IS NULL` — AD-6

**Given** um código com assinatura inválida
**When** ele é validado
**Then** recebo `INVALIDO`

**Given** um ingresso válido de outro evento
**When** ele é lido no contexto do meu evento
**Then** recebo `EVENTO_ERRADO`

**Given** uma portaria sem vínculo com aquele evento
**When** ela chama a validação
**Then** recebe `403` antes de qualquer consulta ao ingresso — AD-7

### Story 5.3: Digitar o código quando a câmera não ajuda

Como portaria,
quero digitar o código à mão,
para não travar a fila quando a câmera falha.

**Acceptance Criteria:**

**Given** a tela do leitor
**When** eu digito um código e aperto Enter
**Then** a validação acontece — sem precisar mirar num botão

**Given** uma validação concluída
**When** a resposta chega
**Then** o resultado aparece na tela em forma simples — a palavra do enum e o detalhe em texto
**And** isso já torna a portaria utilizável de ponta a ponta; a apresentação em três canais é
refinamento da Story 5.4, não pré-requisito desta

**Given** o campo
**When** eu o uso
**Then** ele aceita o código com ou sem espaços e não diferencia maiúsculas de minúsculas

**Given** um código em branco
**When** eu envio
**Then** nada acontece e o campo continua focado

### Story 5.4: Ver o resultado a três metros

Como portaria,
quero entender o resultado sem ler com atenção,
para manter a fila andando no escuro.

Refina a exibição simples entregue na Story 5.3.

**Acceptance Criteria:**

**Given** cada um dos quatro resultados
**When** ele aparece
**Then** usa cor, palavra e símbolo ao mesmo tempo — UX-DR5
**And** `VALIDO` é verde ✓, `INVALIDO` é brasa ✕, `JA_UTILIZADO` é cinza ↺, `EVENTO_ERRADO` é âmbar ⤫

**Given** um resultado na tela
**When** eu espero
**Then** ele **não** some sozinho — só sai quando eu peço o próximo

**Given** `JA_UTILIZADO`
**When** ele aparece
**Then** mostra a hora da primeira entrada e usa tom neutro, não de fraude

**Given** um leitor de tela
**When** o resultado aparece
**Then** ele é anunciado por `aria-live="assertive"` — UX-DR9

### Story 5.5: Ler o QR pela câmera

Como portaria,
quero apontar a câmera para o celular da pessoa,
para validar sem digitar nada.

**Acceptance Criteria:**

**Given** permissão de câmera concedida
**When** eu aponto para um QR válido
**Then** o código é lido e validado automaticamente

**Given** permissão negada ou câmera indisponível
**When** eu abro o leitor
**Then** vejo mensagem explicando e o campo de digitação continua funcionando

**Given** o mesmo QR lido duas vezes em sequência rápida
**When** a leitura dispara
**Then** apenas uma validação é enviada

### Story 5.6: Acompanhar as entradas do turno

Como portaria,
quero ver quantas pessoas já entraram,
para ter noção do movimento.

**Acceptance Criteria:**

**Given** que estou trabalhando num evento
**When** eu valido ingressos
**Then** o contador de entradas sobe e fica visível no cabeçalho

**Given** o contador
**When** eu o vejo
**Then** mostra número exato — é dado operacional de quem é dono da informação (UX-DR7)

---

## Epic 6: Avaliação sem atrito

Quem avalia percorre o fluxo inteiro sem montar nada e entende as decisões antes de abrir o código.

> **Estas stories não escrevem os READMEs do zero.** Os três READMEs são construídos
> incrementalmente, uma story por vez, conforme a regra do `CLAUDE.md` — cada commit adiciona o
> comando que passou a existir e o motivo da decisão que acabou de ser tomada. A Epic 6 é a
> **passagem final**: conferir numa máquina limpa se o passo a passo funciona mesmo, ordenar o
> histórico de decisões, fechar lacunas e escrever o roteiro de avaliação.

### Story 6.1: README da raiz com o histórico de decisões

Como avaliador,
quero entender por que o projeto é assim,
para julgar o raciocínio e não só o resultado.

**Acceptance Criteria:**

**Given** o `README.md` da raiz
**When** eu o leio
**Then** cada decisão relevante aparece com o que foi decidido, por quê, e **o que foi descartado
e por que não**

**Given** as decisões documentadas
**When** eu as confiro
**Then** incluem no mínimo: Ticketmaster em vez de TMDb; setores por quantidade em vez de mapa de
assentos; portaria escalada por evento; expiração preguiçosa em vez de worker; ausência de camada
de repositórios; e a fusão das duas direções visuais

**Given** o README
**When** eu procuro o que não está pronto
**Then** as limitações assumidas estão declaradas — NFR1

### Story 6.2: Conferir o passo a passo numa máquina limpa

Como avaliador,
quero subir a aplicação na minha máquina,
para conferir o que quiser.

As instruções já foram escritas ao longo do projeto; esta story **verifica** que funcionam.

**Acceptance Criteria:**

**Given** um clone novo do repositório, sem nenhum estado local
**When** eu sigo o passo a passo do README exatamente como está escrito
**Then** consigo subir banco, backend e frontend do zero, sem nenhum passo implícito
**And** todo comando é copiável e roda como está

**Given** as instruções do banco
**When** eu as leio
**Then** explicam como criar, migrar e semear o PostgreSQL

**Given** `frontend/README.md` e `backend/README.md`
**When** eu os leio
**Then** cada um traz como rodar sua camada, estrutura de pastas e convenções

**Given** as variáveis de ambiente
**When** eu procuro
**Then** existe `.env.example` em cada camada, sem segredo real

### Story 6.3: Documentar o uso de IA

Como avaliador,
quero saber onde a IA foi usada e onde não foi,
para entender o processo.

**Acceptance Criteria:**

**Given** o repositório
**When** eu procuro
**Then** existe seção ou arquivo dizendo quais ferramentas foram usadas, em que partes, e o que
foi feito sem IA — NFR5

**Given** os artefatos do processo
**When** eu os procuro
**Then** brainstorming, arquitetura, UX e epics estão versionados em `_bmad-output/`

### Story 6.4: Roteiro de avaliação de ponta a ponta

Como avaliador,
quero um caminho pronto para percorrer,
para ver o fluxo inteiro em poucos minutos.

**Acceptance Criteria:**

**Given** o README
**When** eu procuro por onde começar
**Then** existe um roteiro numerado: entrar como cliente, comprar, ver o ingresso, compartilhar,
entrar como portaria, validar, e tentar validar de novo

**Given** o roteiro
**When** eu o executo em produção
**Then** cada passo funciona com os dados semeados
**And** o caminho de recusa está descrito com o cartão terminado em `0002`
