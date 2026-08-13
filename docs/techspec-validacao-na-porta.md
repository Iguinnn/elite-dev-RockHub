# Techspec — validação na porta

**Data:** 2026-08-12 · **Escopo:** Stories 5.2, 5.3 e 5.5
**Pré-requisito:** [techspec-codigo-curto.md](techspec-codigo-curto.md) **já aplicada** — o
código tem 8 caracteres e a coluna `assinatura` não existe mais

---

## 1 · Escopo e commits

| Commit | Story | O que entra |
|---|---|---|
| 1 | 5.2 · Validar sem deixar passar duas vezes | `POST /portaria/eventos/{id}/validacoes`, a dependência que junta o AD-7 e o portão, `ingresso.validar` com o `UPDATE` condicional do AD-6, e o campo `aberto` em `TurnoDaPortaria` |
| 2 | 5.3 · Digitar o código quando a câmera não ajuda | `GET /portaria/eventos/{id}`, a tela `/portaria/eventos/{id}` com o campo manual e o resultado em forma simples |
| 3 | 5.5 · Ler o QR pela câmera | O botão da câmera, `@zxing/browser` por import dinâmico, e os estados de permissão negada |

🛑 **Um commit por vez, e pare.** Terminado cada um, rode a suíte inteira, mostre o
resultado e avise que está pronto para eu commitar — sem escrever README, sem tocar no
próximo. Só emende o seguinte depois que eu mandar. **Esta spec cobrir três stories não
autoriza implementá-las de uma vez**, e aqui a tentação é a maior de todo o projeto: os
commits 2 e 3 mexem no mesmo arquivo de tela.

**Fora daqui:** os três canais do veredito (5.4) e o contador do turno (5.6), que saem numa
terceira spec. O commit 2 mostra o resultado em texto simples — o próprio AC da 5.3 diz que
isso já torna a portaria utilizável, e que a apresentação a três metros é refinamento.

## 2 · O que existe hoje

- **A Story 5.1 está pronta e commitada.** `GET /portaria/eventos` devolve os turnos da
  conta, `api/portaria.py` existe, e a casca `/portaria` tem duas abas.
- **O portão de 2 horas hoje mora na tela** — `ANTECEDENCIA_DO_PORTAO_MS`, constante de
  `app/portaria/page.tsx`. Esta spec o move para o backend; ver a seção 3.
- **`usado_em` e `validado_por` já estão no banco** desde a Story 4.1. **Não há migração
  nesta spec.**
- **`conferir_codigo` e `normalizar_codigo` existem e ainda não foram chamadas** por
  ninguém — nasceram na 3.9 e na techspec do código curto esperando esta epic.
- **`evento_portaria`** é lida hoje só por `listar_portarias` e `listar_escalados`.
- **`@zxing/browser` ainda não está instalada.** `qrcode.react` está, e só desenha QR.

## 3 · Decisões, com a alternativa descartada

### Os quatro vereditos respondem `200`

`VALIDO`, `INVALIDO`, `JA_UTILIZADO` e `EVENTO_ERRADO` chegam no corpo de uma resposta de
sucesso, com o detalhe de cada caso. **Descartei** tratar os três últimos como
`ErroDeDominio`, que seria coerente com o `402` do pagamento e o `409` do estoque: o
`ErroDeDominio` carrega `{codigo, mensagem}` e nada mais, e não há onde pôr a hora da
primeira entrada nem o setor. Encaixar isso na `mensagem` seria montar frase no backend, o
que este projeto não faz desde a 3.6. Some-se que a 5.4 vai anunciar o resultado por
`aria-live="assertive"`: é um resultado sendo lido em voz alta, não uma falha de protocolo.

Os quatro são **o produto** deste endpoint — é o FR6 inteiro. Um deles ser "sucesso" e três
serem "erro" inverteria o que a portaria vê: recusar entrada é o trabalho dela dando certo.

### `EVENTO_ERRADO` não diz de qual show o ingresso é

O `EXPERIENCE.md` e o protótipo pedem "ESTE INGRESSO É DO SHOW DA CÉU". **Descartado por
decisão do Igor**, e a razão é boa: uma portaria que não foi escalada num evento acabaria
recebendo o nome dele de volta, e a rota é justamente a que o AD-7 existe para restringir.
A tela diz que o ingresso é de outro show, e para aí — quem está na fila sabe qual ingresso
comprou.

### Código que não existe é `INVALIDO`

Nenhum AC cobre `<código bem formado, mas de nenhum ingresso>`. Ele é colapsado com
assinatura divergente. **Descartei** um quinto veredito: o `EXPERIENCE.md` fixa quatro, cada
um com cor, palavra e símbolo próprios, e "assinatura não confere" continua verdadeiro —
sem linha, não há assinatura que confira. É também a disciplina do `404` único do
`_carregar_do_cliente` e do login da 1.4: a rota não vira oráculo de "esse código existe?".

### O evento vai no caminho, e as duas recusas saem de uma dependência

`POST /portaria/eventos/{evento_id}/validacoes`. **Descartei** `POST /portaria/validacoes`
com o `evento_id` no corpo: o `403` do AD-7 viraria a primeira linha do handler, e o AD-9 é
explícito — papel e autorização se declaram na assinatura, nunca com `if` no corpo. Com o
evento no caminho, uma dependência resolve as duas recusas antes de o handler existir, que
é literalmente o AC "recebe `403` **antes de qualquer consulta ao ingresso**".

### Validar antes da hora queima o ingresso — então a rota recusa

Na spec da 5.1 eu escrevi que o portão era conveniência da tela, não invariante. **Estava
errado, e o motivo é concreto:** uma chamada três dias antes grava `usado_em`, e na noite do
show aquela pessoa é barrada com `JA_UTILIZADO` sem nunca ter entrado. A tela impede; a rota
não impedia, e credencial de portaria mais um `curl` bastam.

A rota passa a recusar com `403 EVENTO_NAO_ABERTO`, na mesma dependência do vínculo — é
recusa de atendimento, da mesma família do "você não trabalha aqui", e **não** um quinto
veredito. Os quatro continuam quatro e nenhuma palavra nova entra na tela da portaria.

**Consequência: a regra desce para o backend, e `TurnoDaPortaria` ganha `aberto: bool`.** A
tela da 5.1 apaga a constante `ANTECEDENCIA_DO_PORTAO_MS` e passa a ler o campo. Isso
reverte uma decisão daquela spec — "o contrato não carrega campo derivado, o relógio é de
quem lê" —, e reverter é o certo: com a regra valendo nos dois lados, duas constantes de
duas horas em duas camadas discordariam algum dia, e a tela mostraria a porta aberta
enquanto a API recusa. Uma regra, um relógio, um lugar.

**Descartei** duplicar a constante nas duas camadas com um comentário pedindo que fiquem
iguais. Comentário não é mecanismo.

### O nome que a porta mostra é o da conta

`titular_nome` na resposta vem de `usuario.nome` — a conta que comprou. É o que a techspec
do código curto já implantou no canhoto, e as duas telas mostram a mesma pessoa: quem chega
com o ingresso na mão vê o mesmo nome que a portaria lê. **Descartei** o `pagador_nome`, que
é de quem passou o cartão e pode ser um terceiro.

### A validação mora em `services/ingresso.py`

O que se escreve é `ingresso.usado_em`, e a regra do projeto é agrupar por agregado —
foi por isso que o arquivo nasceu na 4.1. **Descartei** um `services/portaria.py`, que
agruparia por quem chama e é exatamente o critério recusado quando `ingresso.py` foi
separado de `reserva.py`.

⚠️ Com um aviso obrigatório no docstring: **`validar` é a primeira função do arquivo que não
passa pelo `_carregar_do_cliente`**, e aquele docstring diz "toda rota do dono passa por
aqui". Aqui não há dono — quem chama é um terceiro autorizado, e o `where` é o código, não o
`cliente_id`. Sem o aviso, o próximo leitor supõe uma proteção que não está lá.

### A tela precisa de `GET /portaria/eventos/{id}`, porque a rota pública some no show

O cabeçalho do leitor mostra o nome do evento. `GET /eventos/{id}` não serve: ela corta em
`data_hora >= agora` e responde `404` **exatamente durante o show**, que é quando a portaria
trabalha. Entra `GET /portaria/eventos/{evento_id}`, com a mesma dependência do commit 1 —
o que dá de graça a recusa antes de a tela renderizar. **Descartei** buscar a lista inteira
e achar o item pelo id na tela: funciona, e faz a tela do turno depender de uma rota que
fala de todos os outros.

### A câmera é opt-in, por botão

Foi o que o Igor descreveu, e evita o pior padrão possível: pedir permissão de câmera
assim que a página abre, antes de a pessoa querer usá-la — negada uma vez, o navegador
lembra. `@zxing/browser` entra por `next/dynamic` com `ssr: false`, carregada só quando o
botão é apertado: são ~200 kB que não podem estar no primeiro carregamento da tela mais
sensível a tempo do produto. **Descartei** a `BarcodeDetector` nativa (zero bytes, e
inexistente no Safari do iPhone) e o import estático.

### Um schema de resposta, com campos opcionais

`ResultadoDaValidacao` tem `resultado` e três campos que se preenchem conforme o caso.
**Descartei** uma união discriminada de quatro formas: vira `anyOf` no OpenAPI e obriga a
tela a estreitar tipo antes de desenhar, para nenhum ganho — os quatro casos são a mesma
tela trocando de palavra.

### `entradas_no_evento` fica para a 5.6

O contador já foi decidido (viaja no corpo da validação), mas o campo entra junto da tela
que o desenha. Disciplina desde a 3.1: contrato não carrega campo sem consumidor.

## 4 · Contrato

**Sem migração** em nenhum dos três commits.

### Commit 1 — Story 5.2

`core/dependencias.py` — dependência nova, com o `evento_id` do caminho:

```python
def exigir_porta_aberta(
    evento_id: UUID,
    portaria: Usuario = Depends(exigir_papel(PapelUsuario.PORTARIA)),
    sessao: Session = Depends(obter_sessao),
) -> Evento: ...
```

Ordem das recusas: sem vínculo → `403 SEM_ESCALA_NO_EVENTO`; com vínculo e fora da janela →
`403 EVENTO_NAO_ABERTO`. Evento inexistente responde a **primeira** — quem não está escalado
não descobre se o evento existe. A janela é `ABERTURA_DOS_PORTOES = timedelta(hours=2)`,
constante de `services/evento.py`, no precedente do `MAXIMO_POR_COMPRA`.

`schemas/ingresso.py`:

```python
class ResultadoDaValidacao(BaseModel):
    resultado: Literal["VALIDO", "INVALIDO", "JA_UTILIZADO", "EVENTO_ERRADO"]
    titular_nome: str | None = None   # VALIDO e JA_UTILIZADO
    setor_nome: str | None = None     # VALIDO
    entrada_em: datetime | None = None  # VALIDO (agora) e JA_UTILIZADO (a primeira vez)
```

`services/ingresso.py::validar(sessao, portaria, evento, codigo)`, nesta ordem:

1. `normalizar_codigo` → `None` ⇒ `INVALIDO`
2. `SELECT` do ingresso pelo `codigo`, com `Setor`, `Reserva` e `Usuario` ⇒ sem linha,
   `INVALIDO`
3. `conferir_codigo(...)` com o `evento_id` **do ingresso** e o `nonce` da linha ⇒ falso,
   `INVALIDO`
4. `ingresso.evento_id != evento.id` ⇒ `EVENTO_ERRADO`
5. `UPDATE ingresso SET usado_em = now(), validado_por = :portaria WHERE id = :id AND
   usado_em IS NULL` com `RETURNING usado_em` (AD-6) ⇒ uma linha, `VALIDO`; zero linhas,
   relê `usado_em` e devolve `JA_UTILIZADO`

`api/portaria.py`: `POST /eventos/{evento_id}/validacoes`, corpo `{codigo: str}`, resposta
`200 ResultadoDaValidacao`.

`schemas/evento.py`: `TurnoDaPortaria` ganha `aberto: bool`, calculado no
`listar_escalados`. `app/portaria/page.tsx` apaga `ANTECEDENCIA_DO_PORTAO_MS` e lê o campo.

### Commit 2 — Story 5.3

`GET /portaria/eventos/{evento_id}` → `TurnoDaPortaria`, mesma dependência.

`frontend/src/app/portaria/eventos/[id]/page.tsx` — Server Component com as guardas de
sessão e papel; busca o turno; `403` da API vira redirect para `/portaria`.
`frontend/src/components/Leitor.tsx` — ilha `"use client"`: campo de código, **Enter valida**
(o AC pede: sem mirar em botão), código em branco não envia nada e mantém o foco. O
resultado aparece como palavra + detalhe em texto e **não some sozinho**.

`frontend/src/lib/validacao.ts` — a chamada, no molde do `lib/` do projeto.

### Commit 3 — Story 5.5

`@zxing/browser` no `package.json`. Botão *Ler pela câmera* no `Leitor`; import dinâmico;
permissão negada ou câmera ausente ⇒ frase explicando, e o campo continua funcionando. O
scanner **para na primeira leitura** e só reabre no próximo pedido — é assim que o AC "o
mesmo QR lido duas vezes em sequência rápida dispara uma validação só" se cumpre por
construção, sem timer.

## 5 · Critérios de pronto, por commit

**Commit 1 (5.2)**

- [ ] Código válido, ingresso não usado, evento certo ⇒ `VALIDO`, com `usado_em` e
      `validado_por` gravados
- [ ] O mesmo ingresso de novo ⇒ `JA_UTILIZADO` com a hora da **primeira** entrada
- [ ] Dois leitores no mesmo instante ⇒ exatamente um `VALIDO`, e o resultado vem do
      `rowcount` (AD-6). ⚠️ A corrida **não** se prova pelo `TestClient` — precisa de duas
      `Session` em conexões distintas, como na 3.6
- [ ] Assinatura adulterada ⇒ `INVALIDO`; código de nenhum ingresso ⇒ `INVALIDO`
- [ ] Ingresso de outro evento ⇒ `EVENTO_ERRADO`, **sem** o nome do outro show na resposta
- [ ] Portaria sem vínculo ⇒ `403 SEM_ESCALA_NO_EVENTO`, e o ingresso **não** é tocado
- [ ] Evento a mais de 2h ⇒ `403 EVENTO_NAO_ABERTO`; a menos de 2h e depois do começo ⇒
      atende
- [ ] `CLIENTE` e `ORGANIZADOR` ⇒ `403`; sem sessão ⇒ `401`
- [ ] `TurnoDaPortaria.aberto` no contrato, e `/portaria` sem a constante de duas horas
- [ ] `uv run pytest` verde, número registrado · `npm run build` e `tsc --noEmit` limpos

**Commit 2 (5.3)**

- [ ] Digitar um código e apertar **Enter** valida, sem clicar em botão
- [ ] Os quatro resultados aparecem como palavra + detalhe em texto, e **não somem sozinhos**
- [ ] Código em branco não envia nada e o campo continua focado
- [ ] Código com espaços e em minúsculas funciona (é o que o canhoto exibe)
- [ ] `GET /portaria/eventos/{id}` de evento em que não fui escalado ⇒ `403`, e a tela
      manda de volta para `/portaria`
- [ ] Alvos de no mínimo 44px, coluna única (UX-DR6)
- [ ] A janela aberta pela 5.1 fechou: o link do turno chega numa tela que existe

**Commit 3 (5.5)**

- [ ] QR válido apontado à câmera valida sozinho
- [ ] Permissão negada ou câmera ausente ⇒ frase explicando, e o campo manual continua
      funcionando
- [ ] O mesmo QR lido duas vezes em sequência dispara **uma** validação
- [ ] `@zxing/browser` fora do bundle inicial da tela — conferir no `npm run build`
- [ ] Conferido **na tela**, por você: validar um ingresso, tentar de novo, tentar um de
      outro evento e digitar lixo

## 6 · Armadilhas

⚠️ **`expire_on_commit=False` de novo.** Depois do `UPDATE` condicional, o objeto em memória
continua com `usado_em = None`. O `RETURNING` resolve o caminho do `VALIDO`; o do
`JA_UTILIZADO` precisa reler a linha, senão a resposta sai com `entrada_em: null` e a tela
diz "já utilizado" sem dizer quando. É a mesma armadilha que derrubou o pagamento na Epic 3
e o `share_token` na 4.3 — terceira aparição.

⚠️ **A assinatura se confere contra o `evento_id` do ingresso, nunca contra o do caminho.**
Conferir contra o contexto faria um código legítimo de outro show falhar como `INVALIDO` em
vez de `EVENTO_ERRADO` — dois vereditos trocados, e o da fila fica com a palavra errada.

⚠️ **`EVENTO_ERRADO` vem antes do `UPDATE`, e isso não é ordem estética:** invertido, o
ingresso do outro show seria **queimado** por uma portaria que nem podia lê-lo.

⚠️ **O `403` do AD-7 não pode virar `404`.** O ingresso não é consultado nesse caminho; se
alguém "melhorar" carregando o ingresso antes da dependência, o AC que exige a recusa
**antes de qualquer consulta** deixa de valer sem nenhum teste mudar de cor. Um teste que
conta consultas é caro; um que confirma que o `usado_em` continua nulo depois do `403` é
barato e pega o caso que importa.

⚠️ **`getUserMedia` exige contexto seguro.** Funciona na Vercel e em `localhost`, e **não**
funciona num celular abrindo `http://192.168.0.x:3000`. Isso vira linha em
`README.md#o-que-não-está-pronto` **no commit 3**, na hora — é a exceção do `CLAUDE.md` que
continua valendo.

⚠️ **Parar a câmera ao sair da tela.** `BrowserMultiFormatReader` segura o `MediaStream`; sem
o `reset()` no `useEffect`, a luz da câmera fica acesa depois de navegar, o que na porta lê
como aplicativo travado.

⚠️ **A tela não pode reordenar nem reinterpretar o veredito.** Ela desenha o que veio. A
tentação do commit 2 é "se `INVALIDO` e o código tiver 8 caracteres, então…" — não há
"então": o backend já decidiu.

⚠️ **Nada de `alembic revision` nesta spec.** As colunas vieram na 4.1 e o código curto veio
na spec anterior.

---

**Fontes:** `epics.md` (Stories 5.2, 5.3, 5.5) · `ARCHITECTURE-SPINE.md` (AD-5, AD-6, AD-7,
AD-9) · `EXPERIENCE.md` (os quatro vereditos, primitivas de interação) ·
`docs/techspec-turnos-da-portaria.md` · `docs/techspec-codigo-curto.md` ·
`backend/app/core/seguranca.py`, `core/dependencias.py`, `services/ingresso.py`,
`api/portaria.py` · `frontend/src/app/portaria/page.tsx`
