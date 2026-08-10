---
baseline_commit: "o commit da Story 1.4 (branch epic-1---fundacao-acesso-e-primeiro-deploy)"
---

# Story 1.5: Cadastro de cliente

Status: review

Epic 1 — Fundação, acesso e primeiro deploy · **A story que fecha o acesso pelos dois lados.** A 1.4
deixou uma porta de entrada que só abre para quem já tem chave: existe `/login`, e não existe nenhum
caminho no produto para criar conta — o único usuário do banco foi inserido por um `python -c` no
README. Esta story dá ao visitante o caminho que faltava e, de quebra, paga a dívida que a 1.4
anotou por escrito em três lugares: os componentes `Campo` e `Botao` compartilhados e o link
recíproco entre as duas telas de acesso.

## Story

Como visitante,
quero criar minha conta de cliente,
para poder comprar ingressos.

## Acceptance Criteria

1. **Given** um e-mail ainda não cadastrado
   **When** eu envio nome, e-mail e senha para `POST /auth/cadastro`
   **Then** recebo `201` com `{"id", "nome", "email", "papel"}` e `papel` é `CLIENTE`
   **And** **já entro logado**: a resposta traz o mesmo cookie de sessão do login — `httpOnly`,
   `SameSite=Lax`, `Path=/`, `Max-Age=28800`, e `Secure` quando `AMBIENTE=producao`
   **And** a senha é gravada como hash Argon2id (`$argon2id$…`), e nem `senha` nem `senha_hash`
   aparecem em campo algum da resposta

2. **Given** um e-mail já cadastrado
   **When** eu tento cadastrar de novo
   **Then** recebo `409` com `{"erro": {"codigo": "EMAIL_JA_CADASTRADO", ...}}`
   **And** o mesmo acontece quando o e-mail difere só na caixa (`IGOR@Exemplo.com` para uma conta
   gravada como `igor@exemplo.com`) — nunca um `500` de violação de unicidade

3. **Given** o formulário de cadastro
   **When** eu o navego por teclado
   **Then** todo campo tem `<label>` associado, o foco é visível em âmbar e `Enter` envia
   **And** o erro aparece em região com `role="alert"`, anunciada por leitor de tela — UX-DR9
   **And** em nenhum lugar existe `outline: none`

4. **Given** o cadastro
   **When** eu procuro como escolher o papel da conta
   **Then** não existe seletor na interface e não existe campo `papel` no schema de entrada
   **And** enviar `{"papel": "ORGANIZADOR"}` no corpo cria uma conta `CLIENTE` mesmo assim — o papel
   é decidido pelo service, não pelo cliente HTTP

5. **Given** as regras de senha
   **When** eu envio uma senha com menos de 6 caracteres
   **Then** recebo `422` no formato `{"erro": {...}}` e nenhuma conta é criada
   **And** na tela, digitar senha e confirmação diferentes mostra "As senhas não conferem." **sem
   chamar a API** — a confirmação é do formulário, e o corpo enviado tem só `nome`, `email` e `senha`

6. **Given** um e-mail digitado como `  Igor@Exemplo.COM `
   **When** eu me cadastro com ele
   **Then** a conta é gravada como `igor@exemplo.com` e o login seguinte com essa forma funciona —
   a convenção de e-mail em minúsculas da Story 1.3, agora nos dois lados
   **And** um e-mail sem `@`, sem ponto no domínio ou com espaço no meio responde `422` antes de
   tocar o banco

7. **Given** os dois formulários de acesso
   **When** eu inspeciono o código
   **Then** campo e botão vêm de `Campo.tsx` e `Botao.tsx`, usados pelas duas telas
   **And** o login continua se comportando exatamente como antes: mesmos `id`, `name`, `type`,
   `autoComplete`, mesmo texto de erro, mesmos 40 testes verdes

8. **Given** a tela `/login`
   **When** eu a abro
   **Then** existe um link para `/cadastro`
   **And** em `/cadastro` existe o link recíproco para `/login` — nenhuma das duas telas é alcançável
   apenas digitando a URL

9. **Given** a tela `/cadastro` em uma janela de 375px
   **When** eu a olho
   **Then** a coluna acompanha a largura, nenhum campo transborda e não aparece rolagem horizontal

> **De onde vem cada critério.** Os ACs **1 a 4** são os do `epics.md`, com o detalhamento do cookie
> e do `500` acrescentado.
>
> **AC5 e AC6** são as decisões que você tomou antes de a story ser escrita (ver *Decisões que o Igor
> tomou*). Sem elas o cadastro aceitaria senha de um caractere e e-mail sem arroba — e, como não há
> recuperação de senha nem verificação de e-mail neste projeto, os dois erros são conta perdida para
> sempre.
>
> **AC7** existe porque a Story 1.4 escreveu, em três lugares (tasks, Dev Notes e
> `frontend/README.md`), que `Campo.tsx` e `Botao.tsx` nascem "na Story 1.5, quando existir o segundo
> formulário". A segunda metade do critério é o que importa: extrair componente de código que já
> funciona é a manobra que quebra o que estava pronto sem ninguém notar.
>
> **AC8** paga a outra dívida escrita da 1.4: *"Não há link 'Ainda não tem conta?'. Ele entra na
> Story 1.5, junto da tela de cadastro que ele abre — link que cai no 404 não entra no repositório
> nem por um commit."* Agora a tela existe.
>
> **AC9** existe porque `epics.md#Responsividade` é explícito: cada story que cria tela carrega o
> próprio critério, porque não existe story de "deixar responsivo" no fim.

## Tasks / Subtasks

- [x] **T1. `app/schemas/auth.py` — o schema de entrada do cadastro** (AC: 1, 4, 5, 6)
  - [x] **Nenhuma dependência nova nesta story.** Não instale `email-validator` (e portanto não use
        `EmailStr`), nem `zod`, `react-hook-form` ou qualquer biblioteca de formulário. O motivo do
        e-mail está em *Decisões que o Igor tomou*; o do formulário, em *Escopo*
  - [x] Extrair a normalização de e-mail que hoje é um `field_validator` dentro de `LoginEntrada`
        para um tipo anotado do módulo, usado pelos **dois** schemas:
        ```python
        def normalizar_email(valor: object) -> object:
            return valor.strip().lower() if isinstance(valor, str) else valor

        EmailNormalizado = Annotated[str, BeforeValidator(normalizar_email)]
        ```
  - [x] `LoginEntrada.email` passa a ser `EmailNormalizado`. **O comportamento do login não muda** —
        é a mesma normalização, num lugar só
  - [x] `CadastroEntrada`:
        ```python
        class CadastroEntrada(BaseModel):
            nome: NomeLimpo = Field(min_length=1, max_length=120)
            email: EmailNormalizado = Field(max_length=255)
            senha: str = Field(min_length=6, max_length=128)
        ```
        `NomeLimpo` é o mesmo padrão com um `BeforeValidator` que só faz `.strip()` — sem ele,
        `"   "` passa no `min_length=1`
  - [x] `@field_validator("email")` (modo `after`, o padrão) conferindo o formato contra
        `re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")` e levantando `ValueError`. É a regra mínima que
        você escolheu — o que ela aceita e o que ela recusa está em *A validação de e-mail que
        escolhemos*
  - [x] **O validador de formato fica só em `CadastroEntrada`.** `LoginEntrada` continua sem ele, e
        isso é decisão da Story 1.4: um `422` de formato antes do `401` de credencial recria a
        distinção que o AC3 daquela story existe para eliminar
  - [x] **Não crie campo de confirmação de senha no schema.** A API recebe três campos. A confirmação
        é do formulário — motivo em *Por que a confirmação de senha não chega ao backend*
  - [x] **Não crie campo `papel`.** É o AC4. O papel é decidido no service
  - [x] **Não coloque `model_config = ConfigDict(extra="forbid")`.** Parece a escolha rigorosa e
        quebra o AC4: `{"papel": "ORGANIZADOR"}` no corpo passaria a responder `422` em vez de criar
        uma conta `CLIENTE`. Um campo desconhecido sendo **ignorado** é a garantia mais forte que
        existe — ele não tem como influenciar nada
  - [x] Imports que esta task precisa e que ainda não estão no arquivo: `re`,
        `from typing import Annotated`, `from pydantic import BeforeValidator, Field`
  - [x] `max_length=128` na senha não é enfeite: `Argon2id` não tem o limite de 72 bytes do bcrypt, e
        uma senha de 10 MB seria hasheada inteira, com 64 MB de memória, por requisição

- [x] **T2. `app/services/autenticacao.py` — `cadastrar()`** (AC: 1, 2, 4)
  - [x] `cadastrar(sessao: Session, nome: str, email: str, senha: str) -> Usuario`
  - [x] **Primeiro service do projeto que escreve.** Ele abre e fecha a transação (`commit`), porque
        `obter_sessao()` não abre nenhuma e a convenção do `ARCHITECTURE-SPINE.md#Convenções` é que
        transação é do service. Ler *O primeiro service que escreve* antes de codar
  - [x] `papel=PapelUsuario.CLIENTE.value`, literal, sem parâmetro e sem valor padrão sobrescrevível.
        É o AC4, e a assinatura da função é a garantia
  - [x] `senha_hash=gerar_hash(senha)` — reaproveite `app/core/seguranca.py`. **Não escreva hash novo**
  - [x] **Sem `SELECT` de verificação antes do `INSERT`.** O e-mail duplicado é detectado pelo
        `IntegrityError` do `UNIQUE` que a Story 1.3 criou, com `rollback` e `ErroDeDominio` de `409`.
        O porquê está em *Por que não existe um SELECT antes do INSERT*
  - [x] O erro é `ErroDeDominio("EMAIL_JA_CADASTRADO", "Esse e-mail já tem conta. Entre com ele ou
        use outro.", status_http=409)` — voz jornalística: o que aconteceu **e** o que fazer (UX-DR8)
  - [x] O service não sabe o que é cookie, token ou HTTP. Devolve o `Usuario` ou levanta — mesma
        fronteira que `autenticar()` respeita
  - [x] Imports novos no arquivo: `from sqlalchemy.exc import IntegrityError`, `gerar_hash` de
        `app.core.seguranca` e `PapelUsuario` de `app.models.usuario`

- [x] **T3. `app/api/auth.py` — a rota e o cookie num lugar só** (AC: 1, 4)
  - [x] `POST /auth/cadastro`, corpo `CadastroEntrada`, `response_model=UsuarioSaida`,
        `status_code=201`. Recebe `resposta: Response` e `sessao: Session = Depends(obter_sessao)`
  - [x] Extrair o bloco de `set_cookie` — que agora seria escrito duas vezes — para
        `_gravar_cookie_de_sessao(resposta: Response, usuario: Usuario) -> None`, chamado por
        `entrar` e por `cadastrar_cliente`. Os atributos passam a existir uma vez só
  - [x] Fazer o mesmo com o `delete_cookie` do `sair`: `_limpar_cookie_de_sessao(resposta)`. Os dois
        helpers ficam adjacentes no arquivo, porque a armadilha 3 da Story 1.4 é que atributo
        divergente entre gravar e apagar produz cookie que não é apagado
  - [x] ⚠️ **`obter_settings()` continua sendo chamado dentro do módulo do router.** O teste
        `test_cookie_e_secure_apenas_em_producao` substitui `auth_router.obter_settings` por
        `monkeypatch`; se o helper receber a `Settings` de fora, aquele teste passa a testar nada
  - [x] Nenhum `if papel == ...` em lugar nenhum — AD-9, e é a Story 1.6
  - [x] `app/main.py` **não muda**: o router `auth` já está registrado

- [x] **T4. Componentes de formulário compartilhados** (AC: 3, 7)
  - [x] `src/components/Campo.tsx` + `Campo.module.css` — `<label htmlFor>` + `<input>`, movendo
        `.campo`, `.rotulo` e `.entrada` (com o `:focus` âmbar) do `FormularioLogin.module.css`
  - [x] **Sem `"use client"` no `Campo`, no `Botao` e no `AvisoDeErro`.** Eles não têm interação
        própria; importados por um componente de cliente, vão para o bundle do cliente do mesmo jeito.
        A diretiva só marcaria como ilha algo que não é
  - [x] `src/components/Botao.tsx` + `Botao.module.css` — o primário do `DESIGN.md#Components (botao)`
        (âmbar, texto breu, mono 700 versalete, `:disabled` com `opacity:.35`). **Só o primário.**
        Secundário e destrutivo existem no `DESIGN.md` e ainda não têm consumidor — `variante` com um
        valor só é abstração inventada
  - [x] `src/components/AvisoDeErro.tsx` + CSS — a região `role="alert"` que **existe sempre no DOM,
        vazia**. Vai além dos dois componentes que você nomeou, e a razão está em *A terceira
        extração*: a regra que faz essa região funcionar é invisível, e é a que quebra ao copiar
  - [x] Reescrever `FormularioLogin.tsx` para consumir os três. `FormularioLogin.module.css` fica só
        com o que sobrar dele — se sobrar nada, o arquivo sai
  - [x] ⚠️ **Confira o login depois de reescrever**: `id`/`name` (`email`, `senha`), `type`,
        `autoComplete="email"` e `"current-password"`, `required`, o texto de erro por `codigo` e o
        `router.push("/")`. É o AC7, e é o único lugar desta story onde dá para quebrar algo entregue

- [x] **T5. `src/components/FormularioCadastro.tsx`** (AC: 1, 3, 5, 8)
  - [x] `"use client"`. Quatro campos, nesta ordem: **Nome**, **E-mail**, **Senha**, **Repetir senha**
  - [x] `autoComplete`: `name`, `email`, `new-password`, `new-password`. **`new-password` nos dois
        campos de senha**, não `current-password` — é o que faz o gerenciador de senhas oferecer uma
        senha nova em vez de tentar preencher uma existente
  - [x] Validação no cliente **antes** do `fetch`, na região de alerta:
        - senha com menos de 6 caracteres → "A senha precisa ter ao menos 6 caracteres."
        - senha ≠ confirmação → "As senhas não conferem."
  - [x] `chamarApi("/auth/cadastro", { method: "POST", body: JSON.stringify({ nome, email, senha }) })`
        — **três campos**, a confirmação não vai no corpo
  - [x] Texto do erro escolhido pelo `codigo`, nunca pela `mensagem` (convenção da 1.4):
        `EMAIL_JA_CADASTRADO` → "Esse e-mail já tem conta. Entre com ele ou use outro.";
        `DADOS_INVALIDOS` → "Confira os dados do formulário."; qualquer outro → "Não foi possível
        criar a conta agora. Tente de novo em instantes."
  - [x] `try/catch` em volta da chamada: erro de rede (`TypeError: Failed to fetch`) não passa pelo
        `ErroDaApi` e não tem `codigo` — é a armadilha 9 da Story 1.4
  - [x] Sucesso: `router.push("/")`. Sem encaminhar por papel (toda conta nasce `CLIENTE`, e nem
        `/organizador` nem `/portaria` existem)
  - [x] Botão desabilitado durante o envio, pelo `Botao`

- [x] **T6. Tela `/cadastro` e os dois links** (AC: 3, 8, 9)
  - [x] `src/app/(entrada)/cadastro/page.tsx` — **Server Component**, no grupo `(entrada)`, que a
        Story 1.4 criou já dizendo "o cadastro entra neste mesmo grupo". A casca (logotipo, sem
        masthead) vem de graça do `layout.tsx` que já está lá
  - [x] `page.module.css`: mesma coluna de 440px centrada do login. Se as duas ficarem idênticas,
        **não** invente um terceiro arquivo compartilhado — CSS Module de página é barato e a próxima
        tela do grupo pode divergir
  - [x] Kicker `Criar conta` no topo da coluna. E preencher o kicker de `/login`, que hoje está
        vazio (`<p className="kicker"></p>`), com `Acesso`: sem ele as duas telas ficam idênticas
        acima do primeiro campo, e o kicker vazio está ocupando 22px de margem sem dizer nada. **É um
        ajuste de microcopy, que o `DESIGN.md` classifica como provisório — se você discordar, é uma
        palavra para trocar**
  - [x] Link recíproco abaixo do botão, em cada tela, com `next/link` (não `<a href>`):
        - em `/login`: "Ainda não tem conta? **Cadastre-se**" → `/cadastro`
        - em `/cadastro`: "Já tem conta? **Entrar**" → `/login`
        Frase em mono 11px `--fumaca`, centrada, 24px acima; a palavra-âncora em `--ambar` — é ação,
        e âmbar é o acento de ação (UX-DR1). Sem sublinhado; o foco é o `:focus-visible` global
  - [x] Responsividade: a coluna é `max-width` + `margin auto`, então já acompanha. Confira a 375px
        que nada transborda — o `.conteudo` do grupo já dá os 18px de respiro lateral
  - [x] **Não toque em `Masthead.tsx`.** O "Entrar" no cabeçalho é a Story 1.6, que é quem passa a
        saber se existe sessão — foi decidido com você ao fim da 1.4

- [x] **T7. Testes do backend** (AC: 1, 2, 4, 5, 6)
  - [x] Tudo em `tests/test_auth.py`, reaproveitando as fixtures `cliente` e `usuario_gravado` que já
        estão lá. **Não crie um segundo `conftest.py` nem outra fixture de banco**
  - [x] A lista completa do que cada teste prova está em *Testing*
  - [x] ⚠️ Depois de um `409`, **não afirme nada sobre o estado do banco na mesma sessão**: o
        `rollback` do service desfaz a transação inteira, inclusive o usuário que a fixture inseriu
        por `flush`. Detalhe em *O primeiro service que escreve*
  - [x] Os 40 testes atuais continuam passando, e os de `/saude`, erros, config e segurança continuam
        passando **com o Postgres desligado**

- [x] **T8. Verificação** (AC: todos)
  - [x] `uv run pytest` — 40 anteriores + os novos, todos verdes
  - [x] `uv run pytest tests/test_saude.py tests/test_erros.py tests/test_config.py tests/test_seguranca.py`
        **com o Postgres parado** → continua passando (24 testes)
  - [x] No navegador: `/cadastro` → criar conta → cai em `/` já logado, com `rockhub_sessao` no
        domínio `localhost:3000`, `HttpOnly` marcado, e a chamada no Network para `/api/auth/cadastro`
  - [x] Cadastrar o **mesmo e-mail** de novo → mensagem de e-mail já cadastrado, e `409` no Network
  - [x] Sair (ou apagar o cookie) e **entrar pelo `/login` com a conta recém-criada** — é a prova de
        que hash e normalização batem entre as duas rotas
  - [x] Senhas diferentes → "As senhas não conferem." **sem nenhuma requisição no Network**
  - [x] `Tab` percorre nome → e-mail → senha → repetir → botão → link, com contorno âmbar em todos
  - [x] Ir e voltar entre `/login` e `/cadastro` pelos links, sem digitar URL
  - [x] `npm run build`, `npx tsc --noEmit` e `npm run lint` limpos
  - [x] Busca em `frontend/src/` por `outline: none`, `NEXT_PUBLIC_API_URL` e `localhost:8000` → zero
  - [x] Janela em 375px em `/cadastro`: sem rolagem horizontal

- [x] **T9. Documentação** (obrigatório — regra do projeto)
  - [x] `backend/README.md`: `POST /auth/cadastro` na seção *Autenticação* (corpo, `201`, cookie,
        `409`, `422`); as regras de `CadastroEntrada` com os limites e o porquê de cada um; a decisão
        de detectar duplicata pelo `IntegrityError` em vez de `SELECT`; contagem de testes atualizada;
        entrada *Story 1.5* no *Histórico desta camada*
  - [x] `frontend/README.md`: renomear *A tela de login* para cobrir as duas telas de acesso;
        `Campo`, `Botao` e `AvisoDeErro` com **o critério de quando abstrair** (segundo uso, não o
        primeiro); a validação que roda no cliente e a que roda no servidor, e por que as duas
        existem; a estrutura de pastas atualizada; e **apagar a pendência** "Não há link 'Ainda não
        tem conta?'", que deixou de existir — pendência resolvida que fica escrita vira mentira
  - [x] `README.md` da raiz, *Contas semeadas*: agora dá para criar a conta de cliente **pela
        interface**, sem o `python -c`. Deixe o script, porque ele ainda é o único jeito de criar
        organizador e portaria até a Story 1.7 — mas diga isso
  - [x] `README.md` da raiz, *Roteiro de avaliação*: o passo de criar conta em `/cadastro` e entrar
        com ela em `/login`
  - [x] `README.md` da raiz, *Decisões*: **quatro** entradas novas, cada uma com o que caiu e por quê
        — só cliente cria a própria conta; validação de e-mail mínima escrita à mão em vez de
        `EmailStr`; confirmação de senha porque não há recuperação; `Campo`/`Botao` extraídos no
        segundo formulário e não no primeiro. A matéria-prima está em *Decisões que o Igor tomou*
  - [x] `README.md` da raiz, *O que não está pronto*: **duas** entradas — cadastro de organizador
        pela interface (**adiado, não descartado**, conforme `epics.md#Story 1.5`; portaria fica fora
        em qualquer cenário, por causa do AD-7) e a enumeração de e-mail no cadastro, com o motivo de
        ela ser inevitável aqui (*A assimetria com o login*)
  - [x] **Primeira pessoa, como o Igor escrevendo** ("usei", "decidi", "descartei")

## Dev Notes

### Decisões que o Igor tomou para esta story

Perguntadas e respondidas antes de a story ser escrita. **Não são sugestão, e a alternativa
descartada de cada uma é o material do README da raiz (T9).**

| Assunto | Escolha | O que caiu, e por que não |
|---|---|---|
| Regra de senha | **Mínimo de 6 caracteres**, sem exigir maiúscula, número ou símbolo | *8 caracteres*: é o piso do NIST SP 800-63B e teria sido o padrão, mas 6 é o que basta para um sistema que existe para ser avaliado, e não trava a senha curta que as contas semeadas da 1.7 vão usar. *Nenhuma regra*: aceitaria senha de um caractere, e é o tipo de ausência que quem avalia nota em dez segundos |
| Erro de digitação na senha | **Campo "repetir senha"** | *Botão "mostrar senha"*: menos atrito e uma interação a menos, mas expõe a senha na tela de quem cadastra em público e exigiria um componente novo. *Nenhum dos dois*: com recuperação de senha fora do escopo, uma letra errada é conta perdida para sempre — sem suporte, sem e-mail, sem saída |
| Validação de e-mail | **Regra própria mínima** no `field_validator` | *`EmailStr` do Pydantic*: seria a escolha de um sistema em produção, e o custo é uma dependência (`email-validator`) — mas, nas suas palavras, este sistema não vai para produção real: ele existe para o avaliador ver que o cadastro funciona, e uma regra de três linhas prova isso igual. *Nenhuma validação no backend*: deixaria o `type="email"` do navegador como única barreira, e ele desaparece num `curl` |
| `Campo` e `Botao` compartilhados | **Extrair agora**, reescrevendo o `FormularioLogin` | *Repetir o CSS*, como o 404 fez na 1.2: não tocaria em arquivo já entregue, ao custo de duas cópias do mesmo campo que divergem na primeira vez que alguém ajustar uma só. O critério do projeto é abstrair no segundo uso — e o segundo uso é agora |

**Uma suposição declarada, não uma decisão sua:** a rota da tela é **`/cadastro`**, por simetria com
o `POST /auth/cadastro` que o `epics.md` já fixa. Se preferir `/criar-conta`, é uma pasta para
renomear e dois `href`.

### A assimetria com o login — e por que ela é aceitável

O AC2 manda responder `409 EMAIL_JA_CADASTRADO`. Isso **revela que aquele e-mail tem conta** — que é
exatamente o que a Story 1.4 gastou uma seção inteira e um `HASH_FANTASMA` para não revelar no login.
A contradição é real, e é melhor escrevê-la do que deixar quem revisa encontrá-la.

O login pode esconder porque tem para onde esconder: as duas respostas cabem numa frase só ("e-mail
**ou** senha incorretos"). O cadastro não tem essa saída — ou ele diz que o e-mail já existe, ou
mente para quem está tentando criar a conta e deixa a pessoa sem entender por que não entrou. A
mitigação padrão da indústria é responder sempre "enviamos um e-mail para você" e resolver a
diferença por fora, o que exige **verificação por e-mail** — serviço externo, mais uma credencial e
mais um fluxo, explicitamente fora do escopo (`ARCHITECTURE-SPINE.md#Adiado`).

Então: a enumeração existe, é consequência de não haver verificação de e-mail, e vai para *O que não
está pronto* no README (T9). O que continua valendo é que o **login** não a oferece de graça — quem
quiser a lista precisa passar pelo cadastro, um e-mail por vez.

### A validação de e-mail que escolhemos

```python
_FORMATO_DE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
```

Uma arroba, algo antes, algo depois, um ponto no que vem depois, espaço em lugar nenhum.

| Entrada | Resultado |
|---|---|
| `igor@exemplo.com` | passa |
| `a@b.c` | passa — e tudo bem, é endereço sintaticamente válido |
| `igor` · `igor@` · `@exemplo.com` | `422` |
| `igor@exemplo` (sem ponto no domínio) | `422` |
| `igor exu@exemplo.com` | `422` |
| `igor@@exemplo.com` | `422` |

**Não é RFC 5322 e não pretende ser.** A RFC aceita aspas, comentários e domínios literais em IP;
escrever isso à mão é a receita clássica de errar um caso de borda e recusar o e-mail de alguém real.
Aqui a regra pega o erro de digitação óbvio — que é o que ela existe para pegar — e a decisão de não
ir além está escrita no README, como corte consciente e não como esquecimento.

Escreva a regra com a intenção no comentário. Regex sem comentário é a linha que ninguém ousa mexer
depois.

### Por que não existe um SELECT antes do INSERT

O caminho intuitivo é `SELECT` para ver se o e-mail existe e, se não existir, `INSERT`. Ele tem dois
problemas, e o segundo é o que decide:

1. **É uma corrida.** Entre o `SELECT` e o `INSERT` cabe outra requisição com o mesmo e-mail. O
   segundo `INSERT` bate no `UNIQUE` e vira `500` — justamente no caso que o AC2 cobre
2. **Cria dois caminhos para a mesma regra.** O `SELECT` seria a regra "de verdade" e o `UNIQUE` do
   banco seria uma rede de proteção com comportamento diferente. Duas respostas para uma pergunta é
   como as duas divergem

Então há um caminho só: tenta gravar, e o `UNIQUE` que a Story 1.3 criou é quem responde.

```python
usuario = Usuario(
    nome=nome, email=email, senha_hash=gerar_hash(senha),
    papel=PapelUsuario.CLIENTE.value,
)
sessao.add(usuario)
try:
    sessao.flush()
except IntegrityError as erro:
    sessao.rollback()
    raise ErroDeDominio(
        "EMAIL_JA_CADASTRADO",
        "Esse e-mail já tem conta. Entre com ele ou use outro.",
        status_http=409,
    ) from erro
sessao.commit()
sessao.refresh(usuario)
return usuario
```

Três detalhes que custam tempo se passarem batido:

- **`flush()` dentro do `try`, `commit()` fora.** Assim a exceção aparece na linha que a provoca. Com
  o `commit()` dentro do `try`, o `IntegrityError` viria de dentro dele e a distinção entre "gravou e
  falhou ao confirmar" e "não gravou" se perde
- **O `rollback()` é obrigatório.** Sem ele a `Session` fica em estado inválido e a próxima operação
  levanta `PendingRollbackError` — um erro que aponta para longe da causa
- **`from erro`** mantém a causa original no traceback. `409` sem rastro do que o banco disse é o
  tipo de log que não ajuda ninguém às três da manhã

Como só existe uma restrição `UNIQUE` na tabela `usuario`, não há ambiguidade sobre qual delas
falhou. Se um dia houver duas, isto vira `erro.orig.diag.constraint_name` — e não é hoje.

### O primeiro service que escreve

`autenticar()` só lê. `cadastrar()` é a primeira função de service do projeto a gravar, e é ela que
materializa a convenção do `ARCHITECTURE-SPINE.md#Convenções`: **transação é aberta e fechada no
service**. A dependência `obter_sessao()` da Story 1.3 entrega a `Session` sem transação aberta, e o
router nunca chama `commit`.

Isso funciona sob teste por causa de uma decisão que a Story 1.3 já tinha tomado. A fixture `sessao`
prende a `Session` a uma conexão com transação externa e um `SAVEPOINT`, e reabre o `SAVEPOINT` por
evento a cada vez que ele se encerra — inclusive num `IntegrityError` esperado. É o motivo de
`sessao.commit()` dentro do service não vazar nada para fora do teste: o `rollback` da transação
externa, no teardown, apaga tudo.

⚠️ **A consequência no teste do `409`:** o `sessao.rollback()` do service desfaz a transação **até o
savepoint**, e junto vai o usuário que a fixture `usuario_gravado` inseriu por `flush` sem commit.
A resposta HTTP continua sendo `409` — o que o AC pede —, mas um `assert` posterior contando linhas
na tabela veria zero e pareceria um bug do service. Afirme sobre a **resposta**, não sobre o banco,
depois de um `409`.

### Por que a confirmação de senha não chega ao backend

O campo "repetir senha" existe para pegar um erro de digitação **no teclado de quem está digitando**.
Isso é do formulário: ele tem os dois valores em mãos, compara em memória e nem chega a fazer a
requisição.

Mandar a confirmação para a API acrescentaria um campo ao contrato, um validador cruzado no schema,
uma mensagem de erro e um teste — tudo para verificar algo que o navegador já verificou e que
nenhum outro cliente da API (o `curl` do avaliador, o `pytest`) tem por que enviar. A regra de negócio
é "senha com pelo menos 6 caracteres"; "duas caixas de texto iguais" é ergonomia de tela.

A prova disso é o AC5: senhas diferentes não produzem requisição nenhuma no Network.

### A terceira extração — `AvisoDeErro`

Você aprovou extrair `Campo` e `Botao`. Estou propondo um terceiro, e o critério é diferente do dos
outros dois.

`Campo` e `Botao` são extraídos porque **se repetem** — seis campos e dois botões entre as duas
telas. `AvisoDeErro` é extraído porque a regra que o faz funcionar **é invisível**: a região
`role="alert"` precisa existir no DOM desde o primeiro render, vazia, e receber só o texto depois.
Isso está escrito num comentário dentro do `FormularioLogin` hoje. Copiado para o segundo formulário,
o comentário é a primeira coisa que alguém apaga por parecer óbvio — e o que se perde não é estilo,
é o anúncio do erro para quem usa leitor de tela (UX-DR9).

Componente é onde uma regra dessas se protege sozinha.

`DESIGN.md#Como usar este documento` classifica "quais componentes existem e como se dividem" como
**provisório**, ajustável livremente durante a codificação — então isto cabe na sua margem, e não é
decisão de produto sendo tomada no seu lugar. Se você preferir dois componentes e o comentário
repetido, é reverter um arquivo.

### O que já existe e esta story estende — leia antes de escrever

Sete arquivos são **modificados**, não criados. Cinco deles já funcionam, e é aí que mora o risco
desta story:

| Arquivo | Estado hoje | O que esta story faz |
|---|---|---|
| `backend/app/schemas/auth.py` | `LoginEntrada` (com o `field_validator` de e-mail dentro) e `UsuarioSaida` | **Acrescenta** `CadastroEntrada` e **move** a normalização para `EmailNormalizado`, que os dois passam a usar. `UsuarioSaida` não muda — o cadastro devolve o mesmo schema |
| `backend/app/services/autenticacao.py` | `autenticar()` e `_credenciais_invalidas()` | **Acrescenta** `cadastrar()`. `autenticar()` não é tocada |
| `backend/app/api/auth.py` | `entrar` e `sair`, cada um montando os atributos de cookie por conta própria | **Acrescenta** `cadastrar_cliente` e **extrai** os dois helpers de cookie. As rotas existentes mudam de forma, não de comportamento |
| `backend/tests/test_auth.py` | 10 testes, fixtures `cliente` e `usuario_gravado` | **Acrescenta** casos. Nenhum teste existente muda |
| `frontend/src/components/FormularioLogin.tsx` + `.module.css` | Formulário completo, com campo, botão e região de alerta próprios | **Reescrito** sobre os três componentes novos. Comportamento idêntico — é o AC7 |
| `frontend/src/app/(entrada)/login/page.tsx` | Coluna de 440px com kicker **vazio** | Ganha o texto do kicker e o link para `/cadastro` |

**Não devem ser tocados, e não devem quebrar:** `app/core/seguranca.py` (hash e token já servem),
`app/core/config.py` (nenhuma configuração nova), `app/core/erros.py` (o formato de erro já cobre o
`409`), `app/core/db.py`, `app/models/usuario.py` (**nenhuma coluna muda, nenhuma migração nesta
story**), `app/main.py`, `migrations/`, `pyproject.toml` e `uv.lock` (**nenhuma dependência nova**).
No frontend: `layout.tsx`, `not-found.tsx`, `globals.css` (nenhum token novo — a tela usa os que
existem), `Masthead.tsx`, `NavLink.tsx`, `Logotipo.tsx`, `next.config.ts` e `src/lib/api.ts`.

Se algum deles precisar mudar para o cadastro funcionar, algo foi feito errado.

### Contrato da rota nova

```
POST /auth/cadastro
  ← {"nome": "Igor Duarte", "email": "igor@exemplo.com", "senha": "rockhub"}
  → 201  {"id": "…uuid…", "nome": "Igor Duarte", "email": "igor@exemplo.com", "papel": "CLIENTE"}
         Set-Cookie: rockhub_sessao=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800
                     (+ Secure quando AMBIENTE=producao)
  → 409  {"erro": {"codigo": "EMAIL_JA_CADASTRADO", "mensagem": "Esse e-mail já tem conta. …"}}
  → 422  {"erro": {"codigo": "DADOS_INVALIDOS", "mensagem": "…"}}
         senha curta, e-mail malformado, nome vazio, campo ausente
```

O `codigo` do `409` é `EMAIL_JA_CADASTRADO`, do domínio — **não** o `CONFLITO` que
`CODIGO_POR_STATUS[409]` daria. Os dois convivem pelo mesmo motivo que `CREDENCIAIS_INVALIDAS` e
`NAO_AUTENTICADO` convivem: um é a regra de negócio falando, o outro é o framework.

O corpo de resposta é `UsuarioSaida`, o mesmo do login e o mesmo que a Story 1.6 vai devolver em
`GET /auth/eu`. Três rotas, um schema.

### Anatomia da tela de cadastro

Mesma coluna do login, quatro campos em vez de dois, e o link recíproco no pé.

```
       ┌──────────── 440px, centrada ────────────┐
       │              RockHub                    │  ← do layout de (entrada), não da página
       │                                         │
       │  CRIAR CONTA                            │  ← kicker: mono 600 10px, .22em, versalete
       │                                         │
       │  NOME                                   │
       │  ┌───────────────────────────────────┐  │
       │  │ Igor Duarte                       │  │
       │  └───────────────────────────────────┘  │
       │  E-MAIL                                 │
       │  ┌───────────────────────────────────┐  │
       │  │ igor@exemplo.com                  │  │
       │  └───────────────────────────────────┘  │
       │  SENHA                                  │
       │  ┌───────────────────────────────────┐  │
       │  │ ••••••••                          │  │
       │  └───────────────────────────────────┘  │
       │  REPETIR SENHA                          │
       │  ┌───────────────────────────────────┐  │
       │  │ ••••••••                          │  │
       │  └───────────────────────────────────┘  │
       │  ⚠ As senhas não conferem.              │  ← role="alert", brasa, mono 11px
       │  ┌───────────────────────────────────┐  │
       │  │       C R I A R   C O N T A       │  │  ← âmbar, texto breu, mono 700 12px, .18em
       │  └───────────────────────────────────┘  │
       │        Já tem conta? Entrar             │  ← mono 11px, fumaça; "Entrar" em âmbar
       └─────────────────────────────────────────┘
```

O campo e o botão saem prontos dos componentes da T4 — o CSS deles é o que já está no
`FormularioLogin.module.css` hoje, sem mudança de valor. O que é novo:

```css
.rodape  { margin-top: 24px; text-align: center;
           font: 11px/1.6 var(--mono); color: var(--fumaca); }
.rodape a { color: var(--ambar); }
```

Raio zero, sombra zero, nenhum card, nenhuma serifada — tudo neste formulário é dado de máquina,
então tudo é monoespaçada. A única serifada da tela é o logotipo, e ele vem da casca.

**Nada de indicador de força de senha, nada de ícone, nada de dica sob o campo.** Regra de senha que
precisa ser explicada em três linhas embaixo do campo é regra complicada demais; a nossa cabe na
mensagem de erro, quando ela for necessária.

[Fonte: DESIGN.md#Components (botao), DESIGN.md#Colors, DESIGN.md#Typography, UX-DR1, UX-DR2, UX-DR9]

### Onde a validação mora, e por que em dois lugares

Não é redundância — são responsabilidades diferentes:

| Regra | Cliente | Servidor | Por quê |
|---|---|---|---|
| Campo obrigatório | `required` | `min_length` | O navegador dá o retorno imediato; o servidor é o que vale |
| Senha ≥ 6 | sim, antes do `fetch` | `Field(min_length=6)` | O cliente evita uma ida à rede; o servidor é a garantia |
| Senhas conferem | **só cliente** | — | Não é regra de negócio (ver acima) |
| Formato do e-mail | `type="email"` | `field_validator` | O `type` some no `curl`; o validador não |
| E-mail já existe | — | **só servidor** | Só o banco sabe |

A regra geral: **o cliente valida para ser gentil, o servidor valida para estar correto.** Nenhuma
regra existe só no cliente, exceto a que é sobre o próprio ato de digitar.

### Armadilhas específicas desta story

Em ordem de probabilidade:

1. **Extrair `Campo` e `Botao` é onde o login quebra.** Um `htmlFor` que perde o par com o `id`, um
   `autoComplete` que some, um `name` renomeado — e a tela continua parecendo certa. Os 40 testes do
   backend não olham para o frontend. A conferência manual do login na T8 não é formalidade
2. **`autoComplete="new-password"`, não `current-password`.** Copiar o campo do login sem trocar isso
   faz o gerenciador de senhas tentar preencher a senha da conta que a pessoa está criando agora
3. **`sessao.rollback()` no `409` derruba o que a fixture inseriu** (ver *O primeiro service que
   escreve*). O sintoma é um teste que parece provar que o cadastro apaga usuários
4. **`obter_settings()` precisa continuar sendo chamado no módulo do router.** O
   `test_cookie_e_secure_apenas_em_producao` faz `monkeypatch` nele; um helper que receba a `Settings`
   por parâmetro faz o teste passar sem testar nada
5. **Corpo do `fetch` com três campos.** É fácil montar o objeto a partir do `FormData` inteiro e
   mandar a confirmação junto. O `extra="ignore"` do Pydantic aceitaria calado — e o contrato passa a
   ter um campo fantasma que ninguém documentou
6. **`Field(min_length=1)` não segura `"   "`.** Sem o `.strip()` antes, um nome de três espaços é um
   nome válido de três caracteres
7. **Windows App Control bloqueia executáveis da virtualenv nesta máquina.** `uv run pytest` falha com
   `os error 4551`; o contorno é `uv run python -m pytest`. Documentado desde a Story 1.1
8. **`uv run pytest` exige o Compose no ar** desde a Story 1.3. Falha de conexão em `test_auth.py` é
   `docker compose up -d` faltando, não bug da story
9. **`TaskStop` não mata o `node` filho do `npm run dev`.** O órfão segura a porta 3000 e a
   conferência seguinte bate num build antigo. Encerrar processo em segundo plano inclui conferir a
   porta e matar pelo PID — aprendido na 1.4
10. **`next/link`, não `<a href>`.** Um `<a>` entre `/login` e `/cadastro` recarrega o documento
    inteiro; as duas telas estão no mesmo grupo de rotas e compartilham a casca

### Convenções que esta story confirma ou cria

- **Service que escreve faz `commit`; service que lê não faz nada.** `autenticar()` e `cadastrar()`
  são o par que mostra a regra
- **Duplicata é detectada pelo banco, não por `SELECT` antes.** Vale para os `UNIQUE` que vierem
  (evento, setor, vínculo de portaria)
- **Componente compartilhado nasce no segundo uso, nunca no primeiro.** É a regra escrita desde a
  1.2, e esta story é a primeira aplicação dela no sentido de extrair
- **Regra que protege acessibilidade vira componente, mesmo com poucos usos.** É o critério separado
  do `AvisoDeErro`
- **O papel de uma conta nunca vem do corpo da requisição.** Vale para a Story 2.5, quando o
  organizador escalar portaria: quem define papel é o servidor, a partir de quem está autenticado

### Estrutura alvo ao fim desta story

```text
backend/
  app/
    schemas/
      auth.py                   # +CadastroEntrada, +EmailNormalizado (compartilhado com o login)
    services/
      autenticacao.py           # +cadastrar()
    api/
      auth.py                   # +POST /auth/cadastro, +helpers de cookie
  tests/
    test_auth.py                # +casos de cadastro
frontend/
  src/
    components/
      Campo.tsx                 # NOVO
      Campo.module.css          # NOVO
      Botao.tsx                 # NOVO
      Botao.module.css          # NOVO
      AvisoDeErro.tsx           # NOVO
      AvisoDeErro.module.css    # NOVO
      FormularioCadastro.tsx    # NOVO — "use client"
      FormularioLogin.tsx       # reescrito sobre os três componentes
      FormularioLogin.module.css # esvazia; se não sobrar regra, o arquivo sai
    app/
      (entrada)/
        cadastro/
          page.tsx              # NOVO — Server Component
          page.module.css       # NOVO
        login/
          page.tsx              # +kicker com texto, +link para /cadastro
```

Nenhuma migração, nenhuma dependência, nenhum token de CSS novo. `app/integrations/` e
`backend/seeds/` continuam não existindo — Stories 2.1 e 1.7.

[Fonte: ARCHITECTURE-SPINE.md#Árvore]

### Comandos que esta story precisa deixar funcionando

```bash
# da raiz
docker compose up -d

cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # /docs mostra /auth/cadastro, /auth/login e /auth/logout
uv run pytest                           # contorno nesta máquina: uv run python -m pytest

cd ../frontend
npm run dev                             # http://localhost:3000/cadastro
```

Nada de `uv sync` nem de `npm install` — esta story não acrescenta dependência nenhuma.

### Escopo — o que NÃO fazer aqui

`GET /auth/eu`, a dependência de papel, a identidade do usuário no masthead, o "Entrar" no cabeçalho
e o botão "sair" (**Story 1.6**) · seed e contas documentadas no README (**Story 1.7**) · deploy e
variáveis em produção (**Stories 1.8 e 1.9**) · cadastro de organizador e seletor de papel
(**adiado**, `epics.md#Story 1.5`) · recuperação de senha, verificação de e-mail, limite de
tentativas, *refresh token* · encaminhamento por papel após entrar (**Epics 2 e 5**).

Três tentações concretas desta story:

- **"Já que estou extraindo componentes, faço um `Formulario` genérico."** Não faça. Dois formulários
  com campos diferentes não são um formulário parametrizado — são dois formulários que usam as mesmas
  peças
- **"Já que o cadastro cria sessão, aproveito e faço a dependência `usuario_atual`."** Ela é da 1.6,
  que tem `GET /auth/eu`, `401` e `403` para dar forma verificável a ela. A 1.4 recusou pelo mesmo
  motivo
- **"Já que estou no `auth.py`, adianto `PATCH /auth/eu`."** Editar conta não é story de nenhuma epic

### Testing

Tudo em `tests/test_auth.py`, com as fixtures que já existem. Precisa do Compose no ar.

| O que prova | AC |
|---|---|
| Cadastro responde `201`, corpo com `papel == "CLIENTE"`, e **sem** `senha` nem `senha_hash` | 1, 4 |
| A conta gravada tem `senha_hash` começando com `$argon2id$` e diferente da senha digitada | 1 |
| A resposta do cadastro traz `Set-Cookie` com `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age=28800` — os mesmos atributos do login, comparados contra ele | 1 |
| Cadastrar e **em seguida fazer login** com a mesma senha responde `200` — hash e normalização batem entre as duas rotas | 1, 6 |
| E-mail já cadastrado responde `409` com `codigo == "EMAIL_JA_CADASTRADO"` | 2 |
| E-mail já cadastrado **com caixa diferente** (`IGOR@Exemplo.COM`) também responde `409`, não `500` | 2, 6 |
| `{"papel": "ORGANIZADOR"}` no corpo cria uma conta `CLIENTE` | 4 |
| Senha com 5 caracteres responde `422` no formato `{"erro": {...}}`, e nenhuma conta é criada | 5 |
| E-mail sem `@`, sem ponto no domínio e com espaço no meio respondem `422` (um caso para cada) | 6 |
| Nome só com espaços responde `422` | 5 |
| Nome com 121 caracteres responde `422` — não `500` por truncamento no `VARCHAR(120)` | 5 |
| Campo ausente no corpo responde `422` no formato de erro | 5 |
| `  Igor@Exemplo.COM ` grava `igor@exemplo.com` no banco | 6 |

**Os 40 testes atuais continuam passando sem alteração.** Se um deles precisar mudar, a extração de
componentes ou o `EmailNormalizado` mudaram comportamento — e não deveriam.

**O frontend continua sem teste automatizado**, decisão registrada na Story 1.2 e já escrita no README
da raiz. A verificação das telas é manual, e está na T8 — o que aumenta o peso da conferência do
login, que é código que já funcionava.

### Inteligência das stories anteriores

**Da 1.4 (a story imediatamente anterior — leia estas antes de tudo):**

- **`Campo.tsx` e `Botao.tsx` foram adiados para cá com o motivo escrito**, em três arquivos. Esta
  story é onde a promessa vence
- **O link "Ainda não tem conta?" foi adiado para cá** pela mesma razão: link que cai no 404 não entra
  no repositório. A tela existe agora
- **A região `role="alert"` existe sempre no DOM, vazia** — leitor de tela que recebe o `role` junto
  com o conteúdo pode não anunciar nada
- **O texto de tela é escolhido pelo `codigo`, nunca pela `mensagem`** do servidor
- **Toda chamada passa por `src/lib/api.ts` e todo caminho começa com `/api`.** `chamarApi` já trata
  `204` sem corpo e já levanta `ErroDaApi` com o código
- **`credentials: "include"` é desnecessário** — a chamada é de mesma origem por causa do proxy
- **O grupo `(entrada)` foi criado já contando com esta story**, e o comentário no `layout.tsx` diz
  isso textualmente: *"O cadastro (Story 1.5) entra neste mesmo grupo"*
- **O `outline: none` do protótipo não foi para o código, e não vai.** Nem em comentário: um
  comentário contendo a string literal faz a busca de verificação da T8 acusar falso positivo — foi
  exatamente o que aconteceu na 1.4
- **`frontend/AGENTS.md` manda ler `node_modules/next/dist/docs/`** antes de escrever código de
  Next 16

**Da 1.3 (banco):**

- **`email` é `unique=True`**, e é essa restrição que responde o `409` desta story
- **`nome` é `String(120)`, `email` é `String(255)`** — os `max_length` do schema existem para casar
  com as colunas e transformar um `500` de truncamento em `422`
- **`papel` é `String(20)` com `CHECK`**, e `PapelUsuario` mora em `app/models/usuario.py`. Importe
  de lá; não redeclare
- **A convenção de e-mail em minúsculas nasceu lá** apontando para a 1.4 e para esta
- **A fixture de sessão reabre o `SAVEPOINT` por evento**, e é o que permite `commit()` e `rollback()`
  dentro do service sob teste

**Da 1.2 (frontend):**

- **Precedente de não abstrair cedo:** o CSS do 404 foi repetido, com o motivo escrito no arquivo.
  E o **precedente inverso**, da 1.4: o `Logotipo` foi extraído no segundo uso porque identidade
  divergente racha a marca. Esta story fica do lado do segundo precedente, e é a sua decisão
- **Foco âmbar global e `prefers-reduced-motion` já estão no `globals.css`** — herde, não redeclare
- **A porta 3000 é a origem que o `CORS_ORIGENS` do backend autoriza por padrão**

**Da 1.1 (backend):**

- **O formato de erro já cobre o `409`.** `ErroDeDominio` carrega código, mensagem e status, e o
  handler do `main.py` serializa. **Não escreva handler novo**
- **`CODIGO_POR_STATUS[409]` é `CONFLITO`** — é o código dos `409` do framework. O domínio usa
  `EMAIL_JA_CADASTRADO`
- **`app/schemas/` e `app/services/` foram criadas vazias na 1.1** para que ninguém improvisasse onde
  as coisas moram

**Do estado do repositório:** branch `epic-1---fundacao-acesso-e-primeiro-deploy`, com a Story 1.4
pronta para commit. As Stories 1.1 a 1.4 estão em `review` — o code review é ao fim da epic, não a
cada story. 40 testes passando no backend.

[Fonte: _bmad-output/implementation-artifacts/1-1…1-4-*.md]

### Stack desta story

**Nenhuma versão nova para conferir: esta story não acrescenta dependência.** É a primeira desde a
1.1 em que isso acontece, e é consequência direta de duas decisões suas — validação de e-mail própria
em vez de `email-validator`, e componentes escritos à mão em vez de biblioteca de formulário.

O que ela usa já está no lockfile: Pydantic 2.13.4 (`Annotated` + `BeforeValidator`, `Field`),
SQLAlchemy 2.0.51 (`IntegrityError`), FastAPI 0.141.1, argon2-cffi 25.1.0 e, no frontend, Next 16.3.0
(`next/link`) e React 19.

Se surgir vontade de instalar `email-validator`, `zod`, `react-hook-form` ou `bcrypt`: as quatro já
foram consideradas e recusadas, aqui ou na 1.4.

[Fonte: ARCHITECTURE-SPINE.md#Stack]

### Project Structure Notes

Esta story ocupa as duas camadas, como a 1.4 — e pela mesma razão: o contrato da rota e o formulário
que o consome são uma decisão só.

A diferença é que aqui **mais da metade do risco está em código que já funciona**. A T4 reescreve um
formulário entregue e conferido; a T1 mexe num schema que o login usa. Nada disso muda
comportamento, e é justamente por isso que ninguém percebe se mudar. Se for para fazer numa ordem, a
mais segura é T1 → T2 → T3 → T7 (backend fechado e testado) → T4 → conferir o login no navegador →
T5 → T6.

Não toque em `migrations/`: nenhuma coluna muda. O modelo `Usuario` da Story 1.3 já tem tudo — e o
fato de o cadastro não precisar de migração nenhuma é o sinal de que aquela story dimensionou certo.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5] — os quatro ACs originais e a nota
  sobre cadastro de organizador adiado
- [Source: _bmad-output/planning-artifacts/epics.md#Responsividade] — cada story de tela carrega o
  próprio critério; corte em 900px
- [Source: ARCHITECTURE-SPINE.md#AD-15] — Argon2id, JWT em cookie `httpOnly` de 8 horas
- [Source: ARCHITECTURE-SPINE.md#AD-9] — papel único por conta, autorização como dependência (1.6)
- [Source: ARCHITECTURE-SPINE.md#AD-7] — a portaria só valida onde foi escalada; é por isso que conta
  de portaria nunca é autocriada
- [Source: ARCHITECTURE-SPINE.md#Design Paradigm] · [#Convenções de Consistência] — `routers →
  services → models`, transação no service, erro com `codigo` estável, Server Component por padrão
- [Source: ARCHITECTURE-SPINE.md#Adiado] — sem verificação de e-mail, sem recuperação de senha, sem
  rate limiting; cadastro de organizador adiado e **deve constar no README**
- [Source: EXPERIENCE.md#Voice and Tone] · [UX-DR8] — erro diz o que aconteceu e o que fazer
- [Source: EXPERIENCE.md#Accessibility Floor] · [UX-DR9] — `<label>` em todo campo, foco visível,
  nada de `outline: none`
- [Source: DESIGN.md#Components (botao)] · [#Colors] · [#Typography] · [UX-DR1, UX-DR2]
- [Source: _bmad-output/implementation-artifacts/1-4-entrar-com-e-mail-e-senha.md] — as três dívidas
  que esta story paga, as convenções de service/schema/erro e as armadilhas herdadas
- [Source: backend/app/schemas/auth.py] · [app/services/autenticacao.py] · [app/api/auth.py] ·
  [app/models/usuario.py] · [app/core/erros.py] · [tests/conftest.py] · [tests/test_auth.py]
- [Source: frontend/src/components/FormularioLogin.tsx] · [src/lib/api.ts] ·
  [src/app/(entrada)/layout.tsx] · [src/app/(entrada)/login/page.tsx] · [src/app/globals.css]
- [Source: frontend/AGENTS.md] — Next 16 divergiu; a documentação é a de `node_modules/next/dist/docs/`
- [Source: CLAUDE.md] — READMEs em primeira pessoa; git é responsabilidade do Igor

### Regras do projeto que valem para esta story

1. **Nunca execute comandos git.** Sem `add`, `commit`, `branch`, `push` — nem `status` ou `diff`. O
   Igor faz todo o versionamento. Ao terminar, avise que a story está pronta para commit
2. **Confirme com o Igor antes de `docker compose up`**, se ele não estiver acompanhando. Não há
   `uv sync` nem `npm install` nesta story
3. **Atualize os três READMEs antes de dar a story por concluída.** As quatro entradas de decisão e
   as duas de *O que não está pronto* (T9) são a parte que o desafio avalia
4. **Decisão de produto é do Igor.** As quatro desta story já estão respondidas. Se aparecer uma
   quinta — microcopy dos erros, rótulo do botão, se o kicker do login vira "Acesso" — pergunte em vez
   de escolher
5. **Não emende a próxima story** sem o Igor mandar

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

**`test_token_com_assinatura_alterada_e_recusado` é flaky, e é da Story 1.4 — não desta.** Falhou uma
vez na primeira execução da suíte e passou em 7 de 8 execuções isoladas. A causa não tem relação com
o cadastro: a assinatura HMAC-SHA256 tem 32 bytes, que em `base64url` ocupam 43 caracteres — e 43 × 6
= 258 bits para 256 usados. Os 2 bits finais são padding ignorado na decodificação, então `A`, `B`,
`C` e `D` na última posição decodificam **para os mesmos 32 bytes**. O teste troca o último caractere
por `A` (ou por `B`, se já for `A`), e quando o token termina em um desses quatro, ele não adultera
assinatura nenhuma — o token continua válido e o `assert ... is None` falha.

Não corrigi: `tests/test_seguranca.py` não está entre os arquivos desta story, e a correção (alterar
um caractere do **meio** da assinatura, ou decodificar e virar um bit) é decisão do Igor sobre código
já entregue. Fica registrado para a Story 1.6 ou para o code review da epic.

**Verificação de responsividade (AC9) feita por inspeção de CSS, não por captura de tela.** Não há
driver de navegador instalado na máquina, e instalar Playwright violaria a regra desta story de não
acrescentar dependência. O que foi conferido no código: `box-sizing: border-box` global no reset,
`.coluna` com `max-width: 440px` + `margin: 0 auto`, campos com `width: 100%`, e nenhuma largura fixa
em nenhum dos CSS novos. Sem o `border-box`, o `padding: 14px` do campo somaria à largura e
transbordaria — é a causa clássica de rolagem horizontal em formulário, e ela está desarmada na
origem.

### Completion Notes List

**Backend.** `EmailNormalizado` e `NomeLimpo` como tipos `Annotated` do módulo, `CadastroEntrada` com
os três campos e o validador de formato, `cadastrar()` no service e `POST /auth/cadastro` no router.
Os dois helpers de cookie (`_gravar_cookie_de_sessao` e `_limpar_cookie_de_sessao`) foram extraídos e
ficaram adjacentes; `obter_settings()` continua sendo chamado dentro do módulo do router, para o
`monkeypatch` do teste de `Secure` continuar valendo. Nenhuma dependência nova, nenhuma migração.

**Frontend.** `Campo`, `Botao` e `AvisoDeErro` extraídos do `FormularioLogin`, que foi reescrito sobre
os três. O `FormularioLogin.module.css` **foi apagado**: as quatro regras migraram inteiras e não
sobrou nada nele. `FormularioCadastro` novo, com as duas validações de cliente antes do `fetch` e
corpo de três campos. Tela `/cadastro` no grupo `(entrada)` e o par de links recíprocos no pé das duas
telas. O kicker vazio do login recebeu o texto "Acesso".

**Verificação executada.** 55 testes verdes (40 anteriores + 15 novos), sem alterar nenhum dos 40. Os
23 testes independentes de banco continuam passando (o 24º é o flaky descrito acima). `npx tsc
--noEmit`, `npm run lint` e `npm run build` limpos, com `/cadastro` gerada. Busca em `frontend/src/`
por `outline: none`, `NEXT_PUBLIC_API_URL` e `localhost:8000` → zero ocorrências. Fluxo exercitado
ponta a ponta pelo proxy `/api` do frontend: `201` com nome estripado, e-mail normalizado e
`papel: CLIENTE` mesmo enviando `ORGANIZADOR` no corpo; cookie com `HttpOnly`, `Max-Age=28800`,
`Path=/`, `SameSite=lax` e sem `Secure` em dev; `409` no mesmo e-mail em outra caixa; login funcionando
com a conta recém-criada; e `422` para senha curta, e-mail sem ponto no domínio e nome só com espaços.
HTML renderizado das duas telas conferido campo a campo — `htmlFor`/`id` pareados, `autoComplete`
correto em todos (incluindo `new-password` nos dois campos de senha do cadastro) e `role="alert"`
presente.

**Uma tentação recusada.** O `Botao` ficou só com a variante primária, e não ganhou prop `variante` —
secundário e destrutivo existem no `DESIGN.md` e ainda não têm consumidor.

### File List

**Backend — modificados**
- `backend/app/schemas/auth.py`
- `backend/app/services/autenticacao.py`
- `backend/app/api/auth.py`
- `backend/tests/test_auth.py`
- `backend/README.md`

**Frontend — criados**
- `frontend/src/components/Campo.tsx`
- `frontend/src/components/Campo.module.css`
- `frontend/src/components/Botao.tsx`
- `frontend/src/components/Botao.module.css`
- `frontend/src/components/AvisoDeErro.tsx`
- `frontend/src/components/AvisoDeErro.module.css`
- `frontend/src/components/FormularioCadastro.tsx`
- `frontend/src/app/(entrada)/cadastro/page.tsx`
- `frontend/src/app/(entrada)/cadastro/page.module.css`

**Frontend — modificados**
- `frontend/src/components/FormularioLogin.tsx`
- `frontend/src/app/(entrada)/login/page.tsx`
- `frontend/src/app/(entrada)/login/page.module.css`
- `frontend/README.md`

**Frontend — apagado**
- `frontend/src/components/FormularioLogin.module.css` (esvaziou: as quatro regras migraram para
  `Campo.module.css`, `Botao.module.css` e `AvisoDeErro.module.css`)

**Raiz**
- `README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Data | Mudança |
|---|---|
| 2026-08-10 | Story 1.5 implementada. Backend: `CadastroEntrada` + `EmailNormalizado` compartilhado com o login, `cadastrar()` como primeiro service que escreve (duplicata detectada por `IntegrityError`, não por `SELECT`), `POST /auth/cadastro` com `201` e cookie de sessão, helpers de cookie extraídos. Frontend: `Campo`, `Botao` e `AvisoDeErro` extraídos no segundo uso, `FormularioLogin` reescrito sobre eles (`FormularioLogin.module.css` apagado), `FormularioCadastro` novo, tela `/cadastro` e links recíprocos entre as duas telas de acesso. 15 testes novos, 55 no total, sem alterar nenhum dos 40 anteriores. Nenhuma dependência nova e nenhuma migração — a primeira story desde a 1.1 em que isso acontece. Três READMEs atualizados, com quatro decisões novas e duas entradas em *O que não está pronto* |
| 2026-08-10 | Story 1.5 criada e contextualizada. Quatro decisões do Igor incorporadas: senha com mínimo de 6 caracteres, campo de confirmação, validação de e-mail própria em vez de `EmailStr`, e extração de `Campo`/`Botao` agora. Cinco ACs acrescentados aos quatro do `epics.md` (regras de senha e confirmação, normalização e formato do e-mail, login intacto após a extração, links recíprocos, responsividade). Registrada a assimetria entre o `409` do cadastro e a resposta única do login, com o motivo de ela ser inevitável sem verificação de e-mail |
