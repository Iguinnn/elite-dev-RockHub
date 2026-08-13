import Link from "next/link";

import Botao from "@/components/Botao";
import { ARTE_DE_RESERVA } from "@/lib/arte";
import {
  centavosParaReais,
  dataDaChamada,
  partesDaFilaPublica,
} from "@/lib/formato";
import {
  listarCidadesEmCartaz,
  listarProgramacao,
  obterDestaque,
  PERIODOS,
  type EventoEmDestaque,
  type EventoNaProgramacao,
  type PeriodoDaProgramacao,
} from "@/lib/programacao";

import estilos from "./page.module.css";

/** Os chips do grupo `QUANDO`, na ordem em que eles aparecem. */
const CHIPS_DE_PERIODO: ReadonlyArray<{
  valor: PeriodoDaProgramacao;
  rotulo: string;
}> = [
  { valor: "todos", rotulo: "Todos" },
  // ⚠️ `7 DIAS` e `30 DIAS`, e não "Esta semana" e "Este mês" (decisão do
  // Igor). As janelas são corridas a partir de agora: "esta semana" numa
  // sexta-feira significaria dois dias, e o filtro pareceria quebrado
  // justamente no dia em que mais gente procura show. O rótulo diz exatamente
  // o que o filtro faz.
  { valor: "semana", rotulo: "7 dias" },
  { valor: "mes", rotulo: "30 dias" },
];

/**
 * A raiz do produto: a programação pública, com busca e filtros
 * (Stories 3.1 e 3.2).
 *
 * **A primeira tela deste projeto que não tem dono.** Todas as outras ou são
 * de quem entra (login, cadastro) ou de quem publica (`/organizador/*`) — esta
 * responde a quem chegou pelo endereço, sem conta e sem cookie. Por isso não há
 * `obterUsuarioDaSessao`, não há guarda e não há `redirect`: qualquer um dos
 * três aqui seria uma exigência que o backend não faz.
 *
 * **Server Component, sem uma linha de `"use client"` — mesmo depois de ganhar
 * um campo de texto, dois grupos de chips e um botão.** O estado da busca mora
 * na **URL**, não em `useState`: a barra é um `<form method="get">` e cada chip
 * é um `<Link>`. É a mesma escolha que a tela de publicar fez na Story 2.4 ("a
 * escolha é navegação, não estado"), agora na tela mais visitada do produto — e
 * é o que torna `/?q=marina&cidade=São Paulo` um endereço recarregável,
 * compartilhável, e com o botão voltar funcionando.
 *
 * ⚠️ A alternativa — filtrar em JavaScript a lista já carregada — foi
 * descartada pelo Igor: seria instantânea ao digitar e custaria as três coisas
 * acima, além de mandar a programação inteira pela rede a cada visita. Um
 * `onChange` no campo ou um `useRouter().push()` no chip refaz esse erro sem
 * ninguém decidir; o sintoma é o `npm run build` deixando de marcar `/` como
 * `ƒ`.
 *
 * **Só o que ainda vai acontecer** (decisão do Igor), e o corte é do backend:
 * `GET /eventos` já devolve `data_hora >= agora`. É o oposto de "Meus eventos",
 * onde o corte é da tela — lá o dono da informação é o organizador e o
 * histórico é o inventário dele; aqui o visitante veria metade da página
 * inicial ocupada por shows que não pode comprar.
 */
export default async function Programacao({ searchParams }: PageProps<"/">) {
  // Cada um pode chegar como `string[]` (`?q=a&q=b`) — o primeiro valor basta.
  // O gêmeo destas duas linhas está em `organizador/publicar/page.tsx` e
  // **fica lá**: duas cópias de duas linhas não são um módulo, e promovê-lo
  // mexeria numa tela já revisada sem ninguém ganhar nada.
  const parametros = await searchParams;
  const primeiro = (valor: string | string[] | undefined) =>
    (Array.isArray(valor) ? valor[0] : valor) ?? "";

  // ⚠️ **Cortados em 120, pelo mesmo motivo do `periodo` logo abaixo** (code
  // review da Epic 3). A rota declara `Query(max_length=120)` para os dois, e o
  // `maxLength={120}` do `<input>` só protege quem digita no formulário — um
  // endereço colado, um link compartilhado ou uma URL editada à mão passavam
  // direto e voltavam `422`, que cai no `!resposta.ok` de `listarProgramacao` e
  // imprime "não foi possível carregar a programação agora". É literalmente a
  // mentira sobre o backend que a normalização do `periodo` foi escrita para
  // evitar, dois parâmetros ao lado dela.
  //
  // Cortar e buscar é melhor que recusar: quem colou um texto enorme na busca
  // vê o resultado dos primeiros 120 caracteres, não uma tela de erro.
  const TETO_DO_PARAMETRO = 120;
  const termo = primeiro(parametros.q).slice(0, TETO_DO_PARAMETRO);
  const cidade = primeiro(parametros.cidade).slice(0, TETO_DO_PARAMETRO);

  // ⚠️ **Normalizado antes da chamada, e é isso que protege a tela.** O backend
  // devolve `422` para valor fora do enum, e sem esta linha um `/?periodo=xyz`
  // digitado à mão mostraria "não foi possível carregar a programação" — uma
  // frase sobre o backend estar fora, para um backend que está no ar. O
  // desconhecido vira "todos", que é a programação inteira: exatamente o que
  // quem errou a URL esperava ver.
  const periodoBruto = primeiro(parametros.periodo);
  const periodo: PeriodoDaProgramacao = PERIODOS.includes(
    periodoBruto as PeriodoDaProgramacao,
  )
    ? (periodoBruto as PeriodoDaProgramacao)
    : "todos";

  const termoLimpo = termo.trim();

  // ⚠️ **Calculado antes das buscas, e não depois** (era depois até a Story
  // 3.2). Ele só depende da URL, e agora é ele que decide se a capa é
  // **buscada** — não só se ela é renderizada. Renderizar condicionalmente é a
  // metade fácil; a outra é não pagar uma ida à rede por um resultado que a tela
  // vai jogar fora, e mover esta linha é o que a torna possível.
  const filtrando = Boolean(termoLimpo) || Boolean(cidade) || periodo !== "todos";

  // **`Promise.all`, e não uma depois da outra.** As três não dependem umas das
  // outras, e encadeá-las custaria idas à rede em série na tela mais visitada do
  // produto.
  //
  // Nenhuma das três levanta: sem `error.tsx`, uma exceção aqui derrubaria a
  // aplicação inteira, não só esta seção.
  //
  // ⚠️ **A terceira é a única condicional**, e é a decisão do Igor: com `?q=`,
  // `?cidade=` ou `?periodo=` a tela vira lista pura, e a capa não é buscada. As
  // alternativas descartadas foram a capa refletindo o resultado filtrado (com
  // um resultado só, o mesmo show em cima e embaixo) e a capa fixa ignorando o
  // filtro (um show de São Paulo acima de "nenhum show encontrado" numa busca
  // por Rio).
  const [resultado, cidades, destaque] = await Promise.all([
    listarProgramacao({ q: termoLimpo, cidade, periodo }),
    listarCidadesEmCartaz(),
    filtrando ? null : obterDestaque(),
  ]);

  const itens = resultado.estado === "ok" ? resultado.itens : [];

  // ⚠️ **O corte é por `id`, e não `slice(1)`.** As duas rotas são consultas
  // independentes, e "o primeiro item da lista é o destaque" é uma coincidência
  // do `order_by` de hoje: o dia em que a ordenação da programação mudar, um
  // `slice(1)` passaria a esconder o segundo show e a mostrar o primeiro duas
  // vezes — sem erro nenhum, e sem ninguém perceber.
  const itensDaFila = destaque
    ? itens.filter((evento) => evento.id !== destaque.id)
    : itens;

  // ⚠️ **"Nenhum show em cartaz" embaixo de uma capa que mostra um show** seria
  // a tela se contradizendo em duas linhas — e é o que acontece com **um** único
  // evento no banco, porque ele vira a capa e a fila fica vazia depois do corte.
  // Nesse caso somem o título e a lista inteira; com filtro ativo não há capa, e
  // os três estados de vazio da Story 3.2 continuam exatamente como estavam.
  const aFilaSobrouVazia = Boolean(destaque) && itensDaFila.length === 0;

  /**
   * O endereço de um chip de período: o termo e a cidade viajam junto.
   *
   * ⚠️ É o defeito clássico de busca com filtro — clicar em "7 dias" apagando o
   * que a pessoa digitou ou a cidade que ela escolheu. O outro lado dele está no
   * `<input type="hidden">` do período dentro do form.
   *
   * `URLSearchParams` e só ele: `searchParams` chega decodificado, e concatenar
   * `encodeURIComponent` em cima produz `%2520` (Story 2.4).
   */
  function destino(proximoPeriodo: PeriodoDaProgramacao): string {
    const busca = new URLSearchParams();
    // Valor vazio não entra: `/?q=&cidade=&periodo=todos` é ruído para quem
    // compartilha o link, e a raiz limpa é o endereço de "sem filtro".
    if (termoLimpo) {
      busca.set("q", termoLimpo);
    }
    if (cidade) {
      busca.set("cidade", cidade);
    }
    if (proximoPeriodo !== "todos") {
      busca.set("periodo", proximoPeriodo);
    }

    return busca.size > 0 ? `/?${busca}` : "/";
  }

  return (
    <section className={estilos.pagina}>
      {/* ⚠️ **O invólucro existe para o `<select>` e o `Buscar` poderem atravessar
          as duas linhas** (decisão do Igor, 13/08/2026). O bloco de filtros é uma
          faixa só entre dois fios — campo e chips em cima e embaixo, controles à
          direita —, e os dois controles altos ficavam grudados no topo dela
          enquanto os chips ficavam no pé. Como `<form>` e chips são irmãos, nada
          em CSS os alinhava: o `.filtros` é a grade comum que faltava, e o form
          vira `display: contents` para os campos dele participarem dela.

          O form continua sendo o form — `display: contents` mexe na caixa, não na
          árvore: `Buscar` segue submetendo o campo e a cidade juntos, sem uma
          linha de JavaScript. */}
      <div className={estilos.filtros}>
        {/* ⚠️ **A barra existe sempre**, inclusive quando a lista voltou vazia e
            quando a API está fora. Sumir a busca quando a busca não achou nada
            tira da pessoa a única ferramenta de corrigir o que ela digitou. */}
        <form method="get" action="/" className={estilos.barraBusca}>
          {/* Rótulo de verdade, visualmente escondido (UX-DR9). `placeholder`
              não é rótulo: ele some quando se digita, e leitor de tela não é
              obrigado a anunciá-lo. O `Campo` do projeto cumpre a mesma regra com
              rótulo visível — aqui ele quebraria a faixa de uma linha só, então a
              regra é cumprida pelo `<label>` escondido. */}
          <label htmlFor="q" className={estilos.rotuloOculto}>
            Buscar artista, casa de show ou cidade
          </label>
          <input
            id="q"
            name="q"
            type="search"
            className={estilos.campoBusca}
            placeholder="Buscar artista, casa de show ou cidade"
            defaultValue={termo}
            // O mesmo teto do `Query(max_length=120)` da rota: sem ele, colar um
            // texto longo devolve `422` e a tela acusa o backend por um erro do
            // próprio formulário (Story 2.2).
            maxLength={120}
          />

          {/* ⚠️ **A cidade é um `<select>`, e o período é chip** — e a diferença
              não é arbitrária. O período é um conjunto **fechado**: sempre serão
              três opções, e chip é o elemento certo para isso. A cidade é um
              conjunto **aberto**, que cresce com o catálogo: com duas cidades os
              chips pareciam um filtro que não filtra, e com quinze seriam três
              linhas de botões empurrando a programação para baixo da dobra. Uma
              lista tem a mesma altura nos dois casos.

              **E ele não custa uma linha de JavaScript**: está dentro do form
              que já existe, então escolher a cidade e apertar `Buscar` submete os
              dois juntos. O preço, que é real e é um só: a cidade deixou de
              filtrar num clique. Um `onChange` com `useRouter().push()` devolveria
              o clique único e transformaria a raiz numa ilha de cliente — que é a
              decisão desta story ao contrário. */}
          {cidades.length > 1 && (
            <>
              <label htmlFor="cidade" className={estilos.rotuloOculto}>
                Filtrar por cidade
              </label>
              {/* ⚠️ **Marcado em neon quando há cidade escolhida** (code review
                  da Epic 3). O AC da Story 3.2 pede que o filtro ativo fique
                  marcado em neon; o chip de período cumpria e este controle não —
                  o neon dele só aparecia no `:hover`, então nada distinguia
                  "filtrando por São Paulo" de "todas as cidades" além do texto
                  dentro da caixa. A decisão registrada trocou o **elemento** (lista
                  em vez de chips, porque cidade é conjunto aberto); ela não
                  dispensou a marcação do estado. O UX-DR9 continua satisfeito
                  pelo próprio texto selecionado — o neon é reforço, não a única
                  pista. */}
              <select
                id="cidade"
                name="cidade"
                className={`${estilos.seletorCidade} ${
                  cidade ? estilos.seletorCidadeAtivo : ""
                }`}
                defaultValue={cidade}
              >
                {/* `value=""` e não o nome de uma cidade: é o que apaga o filtro,
                    e é o mesmo "sem filtro" que a rota limpa significa. */}
                <option value="">Todas as cidades</option>
                {cidades.map((nomeDaCidade) => (
                  <option key={nomeDaCidade} value={nomeDaCidade}>
                    {nomeDaCidade}
                  </option>
                ))}
              </select>
            </>
          )}

          {/* O período escolhido sobrevive à busca. Sem esta linha, buscar um
              termo desligaria o filtro de tempo — e um teste de tela não pegaria
              isso. A cidade não precisa de gêmeo **enquanto o `<select>` está na
              tela**: ele já é um campo do form, e se submete sozinho. */}
          {periodo !== "todos" && (
            <input type="hidden" name="periodo" value={periodo} />
          )}

          {/* ⚠️ **E precisa de gêmeo quando o `<select>` NÃO está na tela** (code
              review da Epic 3). Ele é renderizado sob `cidades.length > 1`, mas a
              `?cidade=` da URL é aplicada sempre. Com o catálogo em uma cidade só
              — ou com `GET /eventos/cidades` fora do ar, que devolve `[]` — a
              lista saía filtrada por um controle invisível, e **buscar um termo
              apagava a cidade em silêncio** enquanto clicar num chip de período a
              preservava: dois caminhos da mesma barra discordando sobre o mesmo
              parâmetro. */}
          {cidades.length <= 1 && cidade && (
            <input type="hidden" name="cidade" value={cidade} />
          )}

          {/* ⚠️ **O `Botao` precisa do invólucro de largura fixa.** Ele é
              `width: 100%` desde a Story 1.4 (é a ação primária de formulário
              empilhado), e solto num flex esse `100%` resolve contra a linha
              inteira e espreme o campo a zero — a barra vira um botão gigante
              sem lugar para digitar. É o mesmo `<div>` que
              `organizador/publicar/page.tsx` usa, e pelo mesmo motivo. */}
          <div className={estilos.botaoBusca}>
            <Botao type="submit">Buscar</Botao>
          </div>
        </form>

        <div className={estilos.grupos}>
          <span className="kicker">Quando</span>
          {CHIPS_DE_PERIODO.map((opcao) => (
            <Chip
              key={opcao.valor}
              href={destino(opcao.valor)}
              ativo={periodo === opcao.valor}
            >
              {opcao.rotulo}
            </Chip>
          ))}
        </div>
      </div>

      {/* A chamada principal: o bloco grande que faz a tela parecer jornal
          (UX-DR4, `DESIGN.md#Components/chamada-principal`). **Uma só por
          tela**, e ela é o próximo show — não uma curadoria. */}
      {destaque && (
        <ChamadaPrincipal evento={destaque} ehOTituloDaTela={aFilaSobrouVazia} />
      )}

      {!aFilaSobrouVazia && (
        <div className={estilos.secTitulo}>
          <h1>Programação</h1>
        </div>
      )}

      {/* ⚠️ **Três frases diferentes, e elas não se misturam.** "Nenhum show em
          cartaz" é verdade sobre o produto — não há show marcado; "nenhum show
          para essa busca" é verdade sobre o que a pessoa digitou; "não deu para
          carregar" é falha temporária que melhora sozinha. Cada uma pede um
          conserto diferente: esperar, corrigir a busca, ou desistir. Uma frase
          só para os três casos mandaria a pessoa fazer a coisa errada em dois
          deles. */}
      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          Não foi possível carregar a programação agora. Tente de novo em
          instantes.
        </p>
      )}

      {resultado.estado === "ok" && itens.length === 0 && filtrando && (
        // Estado vazio (EXPERIENCE.md#Vazio): frase, e um link de texto para
        // voltar. Sem ilustração e sem botão grande — UX-DR8.
        <div className={estilos.vazio}>
          <p className={estilos.frase}>Nenhum show encontrado para essa busca.</p>
          <p className={estilos.frase}>
            <Link href="/" className={estilos.linkDeTexto}>
              Ver toda a programação
            </Link>
          </p>
        </div>
      )}

      {/* ⚠️ O `!destaque` é o que impede a contradição do AC14. As duas rotas
          usam o mesmo recorte, então hoje "há capa" implica "há ao menos um
          item" e esta condição nunca difere — mas ela é uma linha, e o dia em
          que as duas discordarem por meio segundo de diferença entre as
          consultas, a tela não vai dizer que não há show em cima de um show. */}
      {resultado.estado === "ok" &&
        itens.length === 0 &&
        !filtrando &&
        !destaque && (
          <div className={estilos.vazio}>
            <p className="kicker">Em cartaz</p>
            <p className={estilos.frase}>
              Nenhum show em cartaz por enquanto. Assim que um evento for
              publicado, ele aparece aqui.
            </p>
          </div>
        )}

      {itensDaFila.length > 0 && (
        <div className={estilos.lista}>
          {itensDaFila.map((evento) => (
            <Fila key={evento.id} evento={evento} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Nomes de setor como frase: `["Pista", "VIP", "Camarote"]` → `"Pista, VIP e
 * Camarote"`.
 *
 * Vírgulas e um `e` antes do último, e não uma lista com marcador: a ficha é uma
 * linha de texto ao lado de um rótulo, e uma `<ul>` de três itens ali
 * desalinharia a única coisa que a ficha precisa fazer, que é ler como três
 * pares. Duas linhas nesta tela, e não em `lib/formato.ts`: aquele módulo é de
 * data e dinheiro, e esta é a única tela que junta nomes assim.
 */
function comoFrase(nomes: string[]): string {
  if (nomes.length < 2) {
    return nomes.join("");
  }

  return `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}`;
}

/**
 * A chamada principal: arte à esquerda, kicker/manchete/ficha à direita.
 *
 * **É ela que faz a tela parecer jornal** (`DESIGN.md#Components/chamada-principal`)
 * — sem ela a listagem vira só uma tabela. **Uma só por tela** (UX-DR4), e ela é
 * *o próximo show*: não há carrossel, não há rotação, e não há selo "Destaque da
 * semana" como no protótipo. Aquele rótulo é curadoria, e mentiria num show
 * marcado para daqui a três meses.
 *
 * ⚠️ **Não existe standfirst** (decisão do Igor), que é a linha em itálico que o
 * protótipo põe entre a manchete e a ficha. O `Evento` não tem campo de texto
 * livre — nem coluna, nem entrada no formulário de publicação, nem nada que a
 * Ticketmaster devolva —, e uma frase montada com os mesmos dados que o kicker e
 * a ficha já mostram ("No Qualistage, no Rio de Janeiro, nesta sexta") é o
 * anti-padrão nº 5 do `DESIGN.md`: a linha de contexto que soa gerada.
 *
 * ⚠️ **`<Link>` quando há ingresso, `<div>` quando esgotado** — o mesmo padrão
 * da `Fila` logo abaixo, e nunca um link desativado por CSS: `pointer-events:
 * none` tira o clique do mouse e deixa o elemento no Tab, ainda anunciado como
 * link. E **não há botão "Ver setores"** como no protótipo: o bloco inteiro é o
 * alvo, e dois alvos para o mesmo destino no mesmo bloco é uma escolha falsa.
 *
 * Componente **desta tela**, ao lado do `Chip` e da `Fila`, e não em
 * `components/`: ele lê `estilos` deste módulo e não tem segundo consumidor —
 * promovê-lo agora seria inventar uma API para um chamador só.
 */
function ChamadaPrincipal({
  evento,
  ehOTituloDaTela,
}: {
  evento: EventoEmDestaque;
  /** Verdadeiro quando a fila esvaziou e esta capa é o único show da tela. */
  ehOTituloDaTela: boolean;
}) {
  const conteudo = (
    <>
      {/* ⚠️ **O `.arteVazia` saiu daqui em 13/08/2026, e com ele o caso nulo.**
          Enquanto o evento sem arte era um bloco chapado, o degradê do
          `.arte::after` precisava sumir — sombra sobre superfície lisa não tem
          origem —, e por isso existia a classe. Agora o caso nulo é uma
          imagem como qualquer outra: sempre há foto no quadro, sempre há
          degradê, e o selo `Esgotado` assenta igual nos dois casos. */}
      <div className={estilos.arte}>
        {/* ⚠️ **`<img>` comum, e não `next/image`.** Não existe
            `images.remotePatterns` no `next.config.ts`, e o componente do Next
            estoura **em tempo de execução** com host não declarado — em
            produção, não em build. O host vem de uma API externa e não é nosso
            para prometer: declarar `s1.ticketm.net` hoje é uma configuração que
            quebra calada no dia em que a Discovery servir de outro domínio. O
            precedente é a miniatura do catálogo, com o mesmo `eslint-disable`.

            `alt=""` porque a arte é **decorativa**: o nome do artista está
            escrito ao lado dela em serifada 46px, e um `alt` com o mesmo nome
            faria o leitor de tela anunciar o show duas vezes.

            ⚠️ **A imagem que não carrega não precisa de `onError` aqui.** A URL
            é da Ticketmaster e pode morrer sem aviso; quem trata isso é o
            `.imagemDaArte::after` do `page.module.css`, que cobre o ícone
            quebrado com o mesmo cinza do quadro vazio. É CSS puro de propósito:
            um `onError` obrigaria esta capa a virar ilha `"use client"`, com
            hidratação e `useState`, na tela mais visitada do produto.

            O `??` cobre o evento que o catálogo mandou sem arte: o disco do
            RockHub em 16/10, servido do `public/` (ver `lib/arte.ts`). O
            `alt=""` vale para ele pelo mesmo motivo — decoração, e o nome do
            show está ao lado. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={evento.imagem_url ?? ARTE_DE_RESERVA}
          alt=""
          className={estilos.imagemDaArte}
        />

        {/* Sobre a arte, canto superior esquerdo — a anatomia do `.lead-selo`
            do protótipo. A informação **não é dada só por cor** (UX-DR9): a
            palavra está escrita, e o bloco não responde ao hover porque não é
            link. */}
        {evento.esgotado && (
          <span className={estilos.seloDaArte}>Esgotado</span>
        )}
      </div>

      <div className={estilos.textoDaChamada}>
        {/* O dia da semana vem junto — `SEXTA, 15 DE AGOSTO DE 2026, 22H30`.
            Numa capa de show, "sexta" é a informação que situa antes do número,
            e é assim que o protótipo escreve. Não é a `dataPorExtenso`, que não
            devolve dia da semana: o motivo de serem duas funções está no
            `lib/formato.ts`. */}
        <p className="kicker">{dataDaChamada(evento.data_hora)}</p>

        {/* `<h2>` e não `<h1>`: o `<h1>` da tela é "Programação", e a capa é um
            item dentro dela — dois `<h1>` deixariam o documento sem título
            único.

            ⚠️ **Menos quando a capa é a tela inteira** (code review da Epic 3).
            Com um único show em cartaz ele vira a capa, a fila esvazia, o bloco
            "Programação" é suprimido — e a página inicial do produto ficava sem
            `<h1>` nenhum, com um `<h2>` como cabeçalho de maior nível. É estado
            alcançável no primeiro dia de qualquer instalação nova. Quando não há
            fila, este título **é** o título do documento. */}
        {ehOTituloDaTela ? (
          <h1 className={estilos.manchete}>{evento.nome}</h1>
        ) : (
          <h2 className={estilos.manchete}>{evento.nome}</h2>
        )}

        {/* `CASA · CIDADE · SETORES` (decisão do Igor), e **nenhuma contagem de
            ingresso em lugar nenhum** (UX-DR7). `<dl>` porque é literalmente uma
            lista de pares rótulo/valor — o `<div>` do protótipo desenha igual e
            não diz isso a quem usa leitor de tela. */}
        <dl className={estilos.ficha}>
          <div>
            <dt className={estilos.fichaRotulo}>Casa</dt>
            <dd className={estilos.fichaValor}>{evento.local}</dd>
          </div>

          {/* A cidade é anulável desde a Story 2.3: a linha **some** inteira, em
              vez de a ficha mostrar um rótulo sobre o vazio. */}
          {evento.cidade && (
            <div>
              <dt className={estilos.fichaRotulo}>Cidade</dt>
              <dd className={estilos.fichaValor}>{evento.cidade}</dd>
            </div>
          )}

          {/* **Todos os setores, inclusive o esgotado**: a ficha diz o que o
              show tem, não o que sobrou. A lista vazia só acontece com evento
              sem setor nenhum (possível por `psql`), e aí a linha some pela
              mesma regra da cidade. */}
          {evento.setores.length > 0 && (
            <div>
              <dt className={estilos.fichaRotulo}>Setores</dt>
              <dd className={estilos.fichaValor}>{comoFrase(evento.setores)}</dd>
            </div>
          )}
        </dl>

        {/* ⚠️ **O preço entrou depois de a tela ficar pronta** (decisão do Igor,
            e a *Pergunta em aberto* nº 1 da story). Ele fica **abaixo** da
            ficha, e não como um quarto par dentro dela: os três de cima
            descrevem o show — onde, em que cidade, com que setores — e o preço é
            a única linha que fala de comprar. Como o destaque **sai da fila**,
            sem esta linha ele seria o único show da programação sem "a partir
            de" em lugar nenhum da raiz.

            O rótulo vem **antes** do valor, como na `Fila`: "a partir de" é
            preposição, não legenda — lido depois do número ele vira nota de
            rodapé sobre um preço já apresentado como se fosse o preço.

            Estreitado pelo **preço** e não só por `esgotado`: os dois dizem a
            mesma coisa (o backend garante que um implica o outro), mas só este
            dá ao TypeScript a certeza de que não é `null` aqui dentro. Com
            `esgotado` sozinho seria preciso um `?? 0`, e "R$ 0,00" é um preço
            que existe — a capa anunciaria ingresso de graça se o contrato
            mudasse. */}
        {evento.preco_minimo_centavos !== null && (
          <p className={estilos.precoDaChamada}>
            <span>a partir de</span>
            <b>R$ {centavosParaReais(evento.preco_minimo_centavos)}</b>
          </p>
        )}
      </div>
    </>
  );

  if (evento.esgotado) {
    return <div className={estilos.chamada}>{conteudo}</div>;
  }

  // `/eventos/{id}` **só nasce na Story 3.4** — a mesma janela consciente que a
  // `Fila` abriu na 3.1, registrada no `frontend/README.md`.
  return (
    <Link href={`/eventos/${evento.id}`} className={estilos.chamada}>
      {conteudo}
    </Link>
  );
}

/**
 * Um chip de filtro: `<Link>`, nunca `<button>` com JavaScript.
 *
 * **O elemento é o que descreve o comportamento.** Clicar num chip troca a URL
 * — isso é navegação, e navegação é um link. O mesmo raciocínio que fez a fila
 * esgotada ser um `<div>` em vez de um `<Link>` desativado na Story 3.1.
 *
 * ⚠️ **A informação não é dada só por cor** (UX-DR9): o ativo é *preenchido* e
 * os outros são *vazados* — muda a forma, não só a matiz —, e o `aria-current`
 * diz a mesma coisa a quem usa leitor de tela. Quem não distingue o neon do
 * fundo lê o estado pelo contorno e pelo anúncio.
 *
 * Sem `"use client"`, ao contrário do `NavLink`: aquele precisa de
 * `usePathname()` para descobrir onde está, e aqui quem sabe qual filtro está
 * ativo é a própria página, que já leu a URL no servidor.
 */
function Chip({
  href,
  ativo,
  children,
}: {
  href: string;
  ativo: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`${estilos.chip} ${ativo ? estilos.chipAtivo : ""}`}
      aria-current={ativo ? "true" : undefined}
    >
      {children}
    </Link>
  );
}

/**
 * Uma fila de jornal em quatro colunas: data | nome | local e cidade | preço.
 *
 * **A assinatura visual da listagem** (`DESIGN.md#Typography`), e a primeira
 * vez que ela sai do protótipo: dia da semana e hora em mono versalete com o
 * dia em serifada grande. É o que a diferencia da fila do organizador, que é
 * toda mono porque é um inventário.
 *
 * **A fila inteira é o alvo**, não só o nome (padrão `fila-listagem`).
 *
 * ⚠️ **`<Link>` quando há ingresso, `<div>` quando não há** — e não um `<Link>`
 * desativado por CSS. `pointer-events: none` tira o clique do mouse e deixa o
 * elemento no Tab, ainda anunciado como link por leitor de tela: quem navega
 * por teclado chegaria num link que não leva a lugar nenhum. O AC pede que ela
 * **não seja clicável**, e a única forma honesta de fazer isso é o elemento
 * não ser um link.
 *
 * O `href` aponta para `/eventos/{id}`, que **só nasce na Story 3.4** — janela
 * consciente de três stories, registrada no `frontend/README.md`.
 */
function Fila({ evento }: { evento: EventoNaProgramacao }) {
  const { diaDaSemana, dia, mesEAno, hora } = partesDaFilaPublica(evento.data_hora);
  // ⚠️ Estreitar pelo **preço**, e não só por `esgotado`. Os dois dizem a mesma
  // coisa (o backend garante que um implica o outro), mas só este dá ao
  // TypeScript a certeza de que `preco` não é `null` no ramo do `<b>`. Com
  // `esgotado` sozinho seria preciso um `?? 0`, e "R$ 0,00" é um preço que
  // existe — a fila anunciaria ingresso de graça se o contrato mudasse.
  const preco = evento.preco_minimo_centavos;
  const semIngresso = evento.esgotado || preco === null;

  const conteudo = (
    <>
      {/* ⚠️ **O mês e o ano não são enfeite.** Sem eles a coluna mostrava `14`,
          `12` e `23` — agosto, setembro e novembro — e a âncora de leitura da
          lista não dizia qual show vinha antes. O ano vem junto porque dois
          setembros de anos diferentes já convivem na mesma tela. */}
      <div className={estilos.data}>
        <span className={estilos.diaDaSemana}>{diaDaSemana}</span>
        <span className={estilos.dia}>{dia}</span>
        <span className={estilos.mesEAno}>{mesEAno}</span>
        <span className={estilos.hora}>{hora}</span>
      </div>

      <h2 className={estilos.nome}>{evento.nome}</h2>

      {/* A cidade é anulável desde a Story 2.3: sem ela, a fila mostra só o
          local, em vez de uma linha em branco onde deveria haver uma cidade. */}
      <div className={estilos.local}>
        {evento.local}
        {evento.cidade && (
          <>
            <br />
            {evento.cidade}
          </>
        )}
      </div>

      <div className={estilos.preco}>
        {semIngresso ? (
          // ⚠️ A informação **não** é dada só por cor (UX-DR9): a palavra
          // "Esgotado" está escrita, e a fila não é um link. Quem não
          // distingue o vermelho da brasa lê a palavra e percebe a ausência de
          // resposta ao hover — que é a informação (EXPERIENCE.md#fila-listagem).
          <span className={estilos.selo}>Esgotado</span>
        ) : (
          // O rótulo vem **antes** do valor, e não abaixo dele como no
          // protótipo: "a partir de" é preposição, não legenda — lido depois do
          // número ele vira uma nota de rodapé sobre um preço que já foi
          // apresentado como se fosse o preço. Em cima, as duas linhas se leem
          // como uma frase só: "a partir de R$ 120,00".
          <>
            {/* ⚠️ **Classe própria, e não um `<span>` pelado.** O CSS o
                estilizava por `.preco span`, e o seletor pegava **qualquer**
                span desta célula — inclusive o selo `Esgotado` do outro ramo
                deste mesmo ternário, que é um `<span>` também. Com
                especificidade maior que a do `.selo`, era `.preco span` quem
                decidia a cor da palavra dentro do bloco vermelho. */}
            <span className={estilos.aPartirDe}>a partir de</span>
            <b>R$ {centavosParaReais(preco)}</b>
          </>
        )}
      </div>
    </>
  );

  if (semIngresso) {
    return <div className={`${estilos.fila} ${estilos.esgotada}`}>{conteudo}</div>;
  }

  return (
    <Link href={`/eventos/${evento.id}`} className={estilos.fila}>
      {conteudo}
    </Link>
  );
}
