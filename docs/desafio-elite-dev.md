# Desafio Elite Dev — Verzel

Transcrição dos requisitos do PDF original, para servir de fonte de verdade do projeto.

## Proposta

Uma **Plataforma de Eventos e Ingressos**, onde um organizador publica eventos e um cliente
compra ingressos.

O **organizador** monta um evento a partir de um catálogo de shows ou filmes vindo de uma API
externa, definindo data, local, capacidade e preço. O **cliente** navega pelos eventos publicados,
reserva seu lugar, paga de forma simulada, recebe um ingresso com código em QR e pode
compartilhá-lo por link. Na entrada do evento, a **portaria** valida o ingresso.

## O que a Verzel quer ver

> "Vivemos na era da IA, e sabemos o que isso significa aqui: qualquer enunciado colado numa
> ferramenta devolve um sistema inteiro. Um desenvolvedor nosso fez exatamente isso com este PDF,
> sem escrever mais nada, e recebeu a aplicação pronta."

O escopo é **pequeno de propósito**. O que interessa não é volume entregue, é *como você pensa*:
as decisões tomadas, o que foi descartado, por que a tela é assim e não de outro jeito.

> "Fuja do **AI slop**: aquela interface que sai pronta da ferramenta e que você reconhece de longe,
> porque todo projeto gerado tem exatamente a mesma cara. O problema não é a IA ter feito, é
> ninguém ter escolhido nada."

**Queremos ver a sua mão no resultado.**

## Requisitos funcionais

### Front-End

- Navegação e busca pelos eventos publicados (shows ou filmes em cartaz), com data, local e preço
- Criação e gerenciamento dos eventos pelo organizador
- Fluxo de reserva, com seleção do lugar num **mapa de assentos** (cinema, teatro) **ou** da
  **quantidade de ingressos** (pista). Implementar um dos dois, ou os dois
- Pagamento simulado, contemplando a confirmação **e também a recusa**
- Área de "Meus ingressos", exibindo o ingresso e o seu código em QR
- Tela de portaria, com retorno claro: **válido, inválido, já utilizado ou evento errado**
- Leitura do QR **pela câmera** na portaria, com digitação manual do código como alternativa

### Back-End

- Gestão das chamadas para API externa: **Ticketmaster Discovery** ou **TMDb** (uma, outra, ou as duas)
  - https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2
  - https://developer.themoviedb.org/docs
- Autenticação com **três papéis distintos**: Organizador, Cliente e Portaria
- Armazenamento dos eventos, das reservas e dos ingressos
- Garantia de que **o mesmo lugar não seja vendido duas vezes**
- Geração do ingresso com um código em QR **que não possa ser forjado**
- Lógica para o cliente **compartilhar um ingresso via link** gerado pela aplicação
- Validação na portaria, garantindo que **o mesmo ingresso não seja validado duas vezes**
- Cobrança simulada, sem transação financeira real (ambiente de testes de um provedor real é aceito)

## Tecnologias obrigatórias

| Camada | Exigência |
|---|---|
| Front-End | React, com ou sem framework (Next.js, Vite, Remix…) |
| Back-End | NodeJS, Python ou Java (NestJS, Express, FastAPI, Django, Spring Boot…) |
| Banco | Qualquer distribuição — README precisa explicar setup e uso |

## Requisitos não funcionais

- **Prazo:** 7 dias corridos a partir do recebimento
- **Documentação:** README detalhado com passo a passo de configuração e execução. O que não
  estiver funcionando **deve ser mencionado**. Ausência de explicações impacta a nota
- **Dados de teste semeados:** um organizador, **dois** clientes, um usuário de portaria e ao
  menos um evento publicado com ingressos disponíveis
- **Deploy:** não obrigatório, mas **rende +1 ponto** na nota final (Vercel ou similar)

## Opcionais (contam na avaliação)

- Busca e filtro de eventos, painel do organizador, cancelamento com devolução ao estoque
- Mapa de assentos em tempo real, Docker Compose, testes, aplicação publicada

**Não precisa fazer:** nota fiscal, revenda entre usuários, aplicativo nativo, recuperação de
senha, envio de ingresso por e-mail.

## Uso de IA

Recomendado, e não tira ponto. Deve-se contar **quais ferramentas** foram usadas, **em que
partes**, e **o que foi feito sem IA** — no README ou arquivo dedicado.

> "Se você produziu artefatos no caminho, como specs, PRD, fluxo BMAD ou arquivos de contexto,
> **versione junto no repositório**. Ver como você conduziu a ferramenta conta a seu favor."

## Entrega

- Repositório **público** no GitHub
- **Commits ao longo da semana, com mensagens descritivas** — o histórico mostra o processo
- Envio pelo formulário https://elitedev.verzel.com.br

## Referências citadas (ponto de partida, não copiar)

- **ingresso.com** — mapa de assentos de cinema
- **eventim.com.br** — pista e setores por quantidade
- **sympla.com.br** — criação de evento e checkout

## Dica final do enunciado

> "Faça o básico rodar de ponta a ponta e só depois agregue valor. Preferimos o fluxo inteiro
> simples e completo a um pedaço sofisticado com telas pela metade."

Diferenciais citados: interface bem feita e agradável, documentação clara, organização do código,
tratamento de erros, boas práticas de versionamento, testes básicos.

> "Adoramos iniciativa. Se você olhar a proposta e pensar 'isso ficaria melhor com tal coisa',
> faça e conte no README por quê."
