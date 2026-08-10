# Intent — Plataforma de Eventos e Ingressos

Destilado da sessão de brainstorming (modo Facilitador). Fonte completa: `.memlog.md`.
Entrada para arquitetura, epics e stories.

## Contexto

Resposta ao Desafio Elite Dev (Verzel). Requisitos completos em `docs/desafio-elite-dev.md`.
Sessão realizada no dia 2 de 7 (09/08/2026), sem código escrito ainda.

**Restrição dominante:** prazo. A prioridade é o fluxo obrigatório completo de ponta a ponta.
Incremento visual só depois do básico fechado — o enunciado prefere "o fluxo inteiro simples e
completo a um pedaço sofisticado com telas pela metade".

## Decisões travadas

| # | Bifurcação | Escolha | Razão |
|---|---|---|---|
| 1 | API externa | **Ticketmaster Discovery**, só ela | Sistema focado em shows; TMDb descartada |
| 2 | Modelo de lugar | **Quantidade por setor** (pista, VIP, camarote) | Mapa de assentos não é obrigatório; adiado |
| 3 | Backend | **Python + FastAPI**, **PostgreSQL** | — |
| 4 | Frontend | **Next.js** | — |
| 5 | Deploy | Frontend na **Vercel**, backend e banco na **Railway** | Vale +1 ponto no desafio |

## Diferenciação escolhida: estrutural, não visual

A descoberta central da sessão. A diferenciação do projeto **não vem da aparência** — vem de
decisões de modelo e de fluxo, que são baratas de construir e impossíveis de sair prontas de um
gerador.

### 1. Portaria é escala de trabalho, não nível de permissão

O papel de portaria com login próprio é **exigido pelo enunciado**. O que vai além dele é o
vínculo: o usuário de portaria é **escalado para eventos específicos pelo organizador**, e ao
entrar vê apenas os eventos em que foi escalado.

**Justificativa (a que vale escrever no README):** não é conveniência, é autorização. Sem o
vínculo, qualquer conta com papel de portaria valida ingresso de **qualquer** evento do sistema —
o papel diria *o que* a pessoa pode fazer, mas não *onde*. O vínculo fecha esse furo.

**Onde acontece:** na tela de criação do evento, o organizador escolhe o usuário de portaria.

**Limitação assumida por prazo:** não haverá tela de "editar evento" para adicionar/remover
portaria depois da criação. Em sistema real isso seria necessário. **Deve constar no README.**

**Consequência de fluxo (ganho de brinde):** a validação sempre acontece dentro do contexto de um
evento escolhido, então o retorno "evento errado" surge naturalmente do modelo, em vez de ser uma
regra inventada à parte.

### 2. Ingresso não é produto de prateleira

As duas críticas do Igor — a interface gerada por IA e os sites reais de ingresso — são a mesma
crítica: ambos tratam ingresso como item de catálogo (card, imagem, preço, botão), vocabulário de
e-commerce. Mas ingresso é **o direito de entrar num lugar, numa hora**. Romper com a grade de
catálogo é decisão de layout, não de efeito visual: custo zero, e é a diferenciação "leve" pedida.

### 3. Os três papéis têm ergonomias opostas

- **Cliente** — sentado, com tempo, comparando
- **Organizador** — na mesa, preenchendo formulário
- **Portaria** — em pé, na fila, à noite, uma mão só, com gente esperando

Mesmo produto, três ergonomias. Gerador entrega o mesmo layout para os três; tratar isso
conscientemente é diferenciação barata.

## Arquitetura de navegação

**Cliente** — header com `Início` (eventos disponíveis), `Meus ingressos`, `Minha conta` (inclui sair).
Abaixo, a grade de eventos.

**Organizador** — mesma casca do cliente; `Minha conta` ganha publicar e gerenciar eventos.

**Portaria** — navegação própria: lista dos eventos em que foi escalado → escolhe o evento →
modo de leitura de QR.

## Anti-padrões (o que esta interface não vai fazer)

Marcadores de "AI slop" identificados pelo Igor. Cada item é uma regra de exclusão:

1. Faixa/linha que varre a tela de uma lateral à outra em movimento contínuo (marquee/ticker),
   e hovers que deslizam de um lado ao outro
2. Grid de 6 a 8 cards nomeando seções — assinatura de landing page gerada
3. Par título display gigante + texto pequeno logo abaixo (hero padrão)
4. Fileira horizontal de cards com paleta empresarial — o formato de Sympla/Eventim/Ingresso.com

**Mecanismo por trás:** o modelo foi treinado em landing page, então entrega vocabulário de
landing page mesmo quando o produto é um sistema de venda. O vazamento acontece por omissão.

**Princípio norteador:** *"Podemos deixar bonito de várias formas diferentes."* O AI slop não é
feio — é bonito de um jeito só. O que está sendo avaliado não é a capacidade de fazer algo
bonito, é se alguém **escolheu** qual dos vários bonitos.

## Questões que a arquitetura precisa resolver

Caras de errar, pontuadas pelo desafio, ainda em aberto:

1. **Inventário de setor sem vender duas vezes** — controle de concorrência na reserva por
   quantidade (transação, lock, constraint?)
2. **QR não forjável** — esquema de assinatura do código do ingresso
3. **Link de compartilhamento** — o que o link expõe e como não vira vetor de fraude
4. **Validação idempotente na portaria** — mesmo ingresso não validado duas vezes, sob corrida
5. **Integração Ticketmaster** — o que é copiado para o banco no momento da publicação vs. o que
   é consultado ao vivo
6. **Autenticação dos três papéis** — e o vínculo portaria ↔ evento
7. **Evento sem portaria escalada** — se o vínculo só é criado junto com o evento, um evento
   publicado sem portaria fica sem ninguém autorizado a validar. Como tratar?

## Fora de escopo (decidido, não esquecido)

- Mapa de assentos em arquibancada — possível incremento depois do básico fechado
- TMDb e catálogo de filmes
- Tudo que o enunciado dispensa: nota fiscal, revenda, app nativo, recuperação de senha,
  envio de ingresso por e-mail
