# Techspec — filtro de classificação na busca do catálogo

**Data:** 2026-08-11 · **Escopo:** `backend/app/integrations/ticketmaster.py` e seus testes
**Formato:** mudança avulsa, sem story. Um commit `feat`, fora da numeração da Epic 2.

Não é story porque não é escopo de story: são seis linhas de código, quatro testes e dois
parágrafos de README. Criar uma Story 2.7 para isso inflaria o `epics.md` e o `sprint-status.yaml`
com algo que o planejamento não previu — pior para quem lê o histórico depois, não melhor. O que
uma story daria e esta techspec precisa dar do mesmo jeito: o **porquê** registrado enquanto está
fresco, e os critérios de pronto explícitos.

---

## 1 · O problema

`buscar_eventos` chama a Discovery com `countryCode=BR` e mais nada que restrinja **que tipo** de
evento volta. Consequências medidas contra a API real em 11/08/2026:

| Chamada (todas com `countryCode=BR`) | Total | Primeiro item |
|---|---|---|
| **Hoje:** sem filtro de classificação | 168 | `SP2B - São Paulo Beyond Business` — feira de negócios, segmento `Miscellaneous` |
| `classificationName=Rock` | 46 | Rosalía (`World`), Tiago Iorc (`Pop`), tributo ao Michael Jackson (`Pop`) |
| `segmentId=KZFzniwnSyZfZ7v7nJ` (Music) | 124 | só show de música |
| `genreId=KnvZfZ7vAeA` (Rock) | 13 | todos com `classifications[0].genre.name == "Rock"` |

Dois problemas, um de produto e um de identidade:

1. **A tela do organizador abre mostrando uma feira de negócios.** A vitrine de exemplos da Story
   2.2 é a primeira coisa que alguém vê no fluxo de publicação, e ela está anunciando um evento
   corporativo como sugestão de show para vender ingresso.
2. **O nome do produto é RockHub e o catálogo não tem relação nenhuma com rock.** Um filtro de
   gênero é a diferença entre um nome e um recorte.

## 2 · A pesquisa da API — e por que o parâmetro óbvio é o errado

A Discovery v2 (`/events.json`) oferece três formas de filtrar por classificação:

| Parâmetro | O que faz | Serve aqui? |
|---|---|---|
| `classificationName` | Match **textual difuso** contra segmento, gênero, subgênero, tipo e subtipo | **Não.** Testado: `classificationName=Rock` devolve Rosalía (`World`) e Tiago Iorc (`Pop`). O nome promete gênero e entrega busca de texto |
| `segmentId` | Id do segmento na taxonomia — o nível mais alto (Music, Sports, Arts & Theatre, Film, Miscellaneous) | **Sim**, para separar show de feira de negócios |
| `genreId` | Id do gênero — filho do segmento (Rock, Pop, World, Latin…) | **Sim**, e é o único fiel: os 13 resultados vieram todos com `genre.name == "Rock"` |

Os dois ids usados, **confirmados empiricamente em 11/08/2026** (não copiados de memória):

```
segmentId  KZFzniwnSyZfZ7v7nJ   Music
genreId    KnvZfZ7vAeA          Rock  (dentro de Music)
```

Eles são estáveis na taxonomia da Ticketmaster, mas são dado de terceiro fixado no nosso código —
se um dia a busca vier vazia sem explicação, `GET /discovery/v2/classifications.json` lista a
árvore inteira e é por onde se reconfere. Isso vai como comentário no código, não só aqui.

## 3 · A decisão: híbrido, e por quê

**`segmentId=Music` em toda chamada. `genreId=Rock` somente quando não há termo digitado.**

| Situação | Filtros | Resultado |
|---|---|---|
| Tela abre, campo vazio (a vitrine) | `segmentId` + `genreId` + `sort=date,asc` | 13 shows de rock de verdade |
| Organizador digita um termo | `segmentId` + `keyword` | busca dentro dos 124 shows de música |

**O que decidiu foi a contraprova**, medida contra a API real:

```
keyword=rosalia  +  segmentId=Music                 ->  1 resultado
keyword=rosalia  +  segmentId=Music + genreId=Rock  ->  0 resultados
```

Com o gênero preso na busca por termo, o organizador que digita o nome exato do show que quer
publicar **não acha**, e a tela não tem como explicar por quê — ela não sabe que existe um filtro
de gênero atrás. Um campo de busca que não acha o que a pessoa digitou é lido como defeito, sempre.

A vitrine é diferente: ali ninguém pediu nada específico, e mostrar rock é o recorte do produto se
apresentando. É o único lugar onde o filtro de gênero informa em vez de frustrar.

**O que caiu, e por que não:**

- **Só `genreId=Rock`, sempre.** O produto viraria literalmente o que o nome diz, e o recorte é
  defensável como decisão de produto. Caiu por dois números: **13 eventos no catálogo inteiro**, e
  a busca por termo devolvendo vazio para qualquer coisa que não seja rock brasileiro. Some-se a
  isso que a taxonomia deles erra — "Ivan Lins" veio classificado como `Rock` — e o recorte rígido
  passa a excluir por engano tanto quanto inclui.
- **Só `segmentId=Music`.** Resolve o problema de produto (a feira de negócios sai) e não resolve o
  de identidade: o nome RockHub seguiria sendo só um nome. Continua sendo metade da decisão adotada.
- **`classificationName=Rock`.** É o parâmetro que a maioria usaria, e é o errado — devolve Pop e
  World num filtro chamado Rock. Usá-lo demonstraria menos conhecimento da API, não mais.
- **Nada, deixa como está.** Zero risco e zero trabalho, ao custo de o avaliador abrir a tela de
  publicação e ver uma feira de negócios como primeira sugestão.

## 4 · A mudança no código

Arquivo único: `backend/app/integrations/ticketmaster.py`.

**Constantes**, junto de `_PAIS`, cada uma com o comentário do motivo:

```python
# Segmento "Music" da taxonomia da Discovery. Sem ele, a vitrine do organizador
# abre anunciando feira de negócios e evento corporativo como sugestão de show.
_SEGMENTO_MUSICA = "KZFzniwnSyZfZ7v7nJ"

# Gênero "Rock", filho de Music. Só entra na listagem sem termo — ver
# `buscar_eventos`. Ids conferidos em 11/08/2026; a árvore inteira está em
# GET /discovery/v2/classifications.json, que é por onde se reconfere.
_GENERO_ROCK = "KnvZfZ7vAeA"
```

**Em `buscar_eventos`:**

```python
params = {
    "apikey": settings.ticketmaster_api_key,
    "size": limite,
    "locale": "*",
    "countryCode": _PAIS,
    "segmentId": _SEGMENTO_MUSICA,   # ← sempre
}
if termo:
    params["keyword"] = termo
else:
    params["sort"] = "date,asc"
    params["genreId"] = _GENERO_ROCK  # ← só a vitrine
```

**O docstring de `buscar_eventos` ganha o parágrafo do híbrido**, com a contraprova do `rosalia` em
uma linha — é a pergunta que a próxima pessoa a ler a função vai fazer.

⚠️ **No backend, só isto muda.** Nem `_converter_evento`, nem `_melhor_imagem`, nem o tratamento de
erro, nem `ItemDoCatalogo`, nem a rota `/organizador/catalogo`. A tela da Story 2.2 já mostra o que a
API devolver, sem saber por quê.

### Adendo — uma linha de frontend mudou junto

Esta seção dizia originalmente "nem uma linha de frontend", e deixou de ser verdade **durante a
implementação**: conferindo a vitrine com o filtro novo na tela, o Igor notou o `id_externo` exposto
na linha de origem de cada resultado (`Ticketmaster · ZFIMVHTNMZ17KBX_ · Qualistage · Rio de
Janeiro`) e pediu para tirar.

Mudança de uma linha em `frontend/src/app/(site)/organizador/publicar/page.tsx` — o `item.id_externo`
sai do array que monta a `origem`. O id continua vindo da API, continua sendo a `key` de React da
lista e continua indo para `origem_externa_id` na publicação da Story 2.4; só não aparece mais na
tela. Motivo e alternativa descartada no `README.md` da raiz, em *O id da Ticketmaster saiu da tela
do organizador*.

Consequência para a seção 6: **`frontend/README.md` muda**, ao contrário do que estava escrito lá.

## 5 · Testes

Em `backend/tests/test_ticketmaster.py`, quatro testes novos, no padrão `_instalar_transporte` que
já está no arquivo:

| O que prova | Por que existe |
|---|---|
| `segmentId` presente na chamada **com** termo | metade fixa do híbrido |
| `segmentId` presente na chamada **sem** termo | idem, no outro caminho |
| `genreId` presente na chamada **sem** termo | a vitrine é de rock |
| **`genreId` ausente** na chamada **com** termo | ⭐ é este que prova o híbrido. Sem ele, alguém "simplifica" movendo o `genreId` para fora do `else` e nada acusa |

Os testes existentes **não quebram**: eles leem `capturado["url"].params["..."]` item a item, nunca
o conjunto inteiro de parâmetros. Mesma verificação que a Story 2.2 fez ao acrescentar o
`countryCode` — conferido.

`tests/test_organizador_catalogo.py` **não muda**: a rota não sabe que filtro existe.

**Rodar `uv run pytest` inteiro** (Compose no ar) e registrar o número final — parte de 121.

## 6 · Documentação

**`README.md` da raiz** — uma decisão nova em *Decisões: por que isso e não aquilo*, com as três
partes de sempre. A matéria-prima é a seção 3 desta techspec: o híbrido, os números medidos, e as
quatro alternativas descartadas. **É esta entrada que o desafio avalia** — a techspec não a
substitui.

**`README.md` da raiz**, em *O que não está pronto* — uma limitação nova, que já existe hoje e vai
ficar mais visível:

> Busca por artista sem show marcado no Brasil devolve vazio. `metallica` e `coldplay` dão zero
> resultados, e não é o filtro: eles não têm evento no catálogo brasileiro da Ticketmaster hoje.

**`backend/README.md`**, na seção *Catálogo da Ticketmaster* que já existe: os dois parâmetros, os
dois caminhos do híbrido, e os ids com a nota de como reconferi-los.

**`frontend/README.md` muda** — corrigido durante a implementação: o adendo da seção 4 tirou o
`id_externo` da tela, então a camada foi tocada. Entram a linha de origem sem o id, a entrada de
histórico e duas verificações manuais novas (vitrine sem feira de negócios; `rosalia` achando, que é
a prova de que o `genreId` não vazou para a busca por termo).

## 7 · Rastro, já que isto não é story

Três lugares, para daqui a três dias ainda se saber de onde veio este commit:

1. **`_bmad-output/implementation-artifacts/sprint-status.yaml`** — comentário no bloco da Epic 2:
   ```yaml
   # Fora da numeração: filtro de classificação na Discovery (segmentId=Music sempre,
   # genreId=Rock só na vitrine sem termo). Commit `feat` avulso, spec em
   # docs/techspec-filtro-do-catalogo.md. Toca ticketmaster.py, que é da Story 2.1.
   ```
2. **Change Log da Story 2.2** — uma linha, porque `ticketmaster.py` e `test_ticketmaster.py` são
   dela e o File List e a contagem de testes ficam desatualizados sem isso.
3. **Mensagem do commit** — sem `Story X.Y`, de propósito:
   `feat: filtro de classificacao no catalogo da Ticketmaster`

## 8 · Pronto quando

- [ ] `segmentId` em toda chamada; `genreId` só no caminho sem termo
- [ ] Os dois ids como constantes nomeadas, com o comentário do motivo e o ponteiro para
      `/classifications.json`
- [ ] Docstring de `buscar_eventos` explicando o híbrido, com a contraprova do `rosalia`
- [ ] Quatro testes novos, entre eles o do `genreId` **ausente** na busca por termo
- [ ] `uv run pytest` inteiro verde, número final registrado
- [ ] Conferido **na tela** (`/organizador/publicar`, como organizador): a vitrine abre com shows de
      rock e sem feira de negócios; buscar `rosalia` acha; buscar `tiago iorc` acha
- [ ] README da raiz: a decisão com as alternativas descartadas + a limitação da busca vazia
- [ ] `backend/README.md`: o híbrido documentado na seção do catálogo
- [ ] Os três rastros da seção 7
- [ ] Igor avisado de que está pronto para commit — **nenhum comando git é executado por agente**

---

**Fontes:** medições contra `https://app.ticketmaster.com/discovery/v2/events.json` em 11/08/2026 ·
`developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2` ·
`backend/app/integrations/ticketmaster.py` · `_bmad-output/implementation-artifacts/2-2-buscar-a-atracao-no-catalogo.md`
