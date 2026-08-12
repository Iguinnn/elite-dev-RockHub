import Link from "next/link";

import Botao from "@/components/Botao";
import { centavosParaReais, partesDaFilaPublica } from "@/lib/formato";
import {
  listarCidadesEmCartaz,
  listarProgramacao,
  PERIODOS,
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

  const termo = primeiro(parametros.q);
  const cidade = primeiro(parametros.cidade);

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

  // **`Promise.all`, e não uma depois da outra.** A programação e as cidades
  // não dependem uma da outra, e encadeá-las custaria uma ida à rede em série
  // na tela mais visitada do produto.
  //
  // Nenhuma das duas levanta: sem `error.tsx`, uma exceção aqui derrubaria a
  // aplicação inteira, não só esta seção.
  const [resultado, cidades] = await Promise.all([
    listarProgramacao({ q: termoLimpo, cidade, periodo }),
    listarCidadesEmCartaz(),
  ]);

  const itens = resultado.estado === "ok" ? resultado.itens : [];
  const filtrando = Boolean(termoLimpo) || Boolean(cidade) || periodo !== "todos";

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
            <select
              id="cidade"
              name="cidade"
              className={estilos.seletorCidade}
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
            isso. A cidade não precisa de gêmeo: o `<select>` acima já é um
            campo do form, e se submete sozinho. */}
        {periodo !== "todos" && (
          <input type="hidden" name="periodo" value={periodo} />
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

      <div className={estilos.secTitulo}>
        <h1>Programação</h1>
      </div>

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

      {resultado.estado === "ok" && itens.length === 0 && !filtrando && (
        <div className={estilos.vazio}>
          <p className="kicker">Em cartaz</p>
          <p className={estilos.frase}>
            Nenhum show em cartaz por enquanto. Assim que um evento for
            publicado, ele aparece aqui.
          </p>
        </div>
      )}

      {itens.length > 0 && (
        <div className={estilos.lista}>
          {itens.map((evento) => (
            <Fila key={evento.id} evento={evento} />
          ))}
        </div>
      )}
    </section>
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
            <span>a partir de</span>
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
