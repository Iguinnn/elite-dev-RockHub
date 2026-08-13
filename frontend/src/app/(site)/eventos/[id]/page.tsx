import Link from "next/link";
import { notFound } from "next/navigation";

import EscolhaDeIngressos, {
  type AcaoDeCompra,
} from "@/components/EscolhaDeIngressos";
import { ARTE_DE_RESERVA } from "@/lib/arte";
import { dataDaChamada } from "@/lib/formato";
import { obterEvento } from "@/lib/programacao";
import { obterUsuarioDaSessao, type UsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * Quem vê o quê no rodapé da compra — a tradução de papel em desfecho.
 *
 * **`Record` fechado, e não uma cadeia de ternários** (mesma disciplina do
 * `ESTADO` e do `PREENCHIMENTO` da ilha): no dia em que um quarto papel entrar
 * no `UsuarioDaSessao`, é o **build** que reclama da falta de tradução, em vez
 * de o papel novo cair calado no ramo do visitante e ganhar um link de login que
 * não serve para ele. Foi assim que o organizador ficou com "Entrar para
 * reservar" na tela até 13/08/2026.
 *
 * `VISITANTE` não é papel do backend — é o `null` da sessão com nome, para o
 * mapa poder ser total.
 */
const ACAO_POR_PAPEL: Record<
  UsuarioDaSessao["papel"] | "VISITANTE",
  AcaoDeCompra
> = {
  CLIENTE: "reservar",
  ORGANIZADOR: "recusar",
  PORTARIA: "recusar",
  VISITANTE: "entrar",
};

/**
 * A página de um evento: a ficha, a arte e os setores com o seletor de quantidade
 * (Story 3.4).
 *
 * **É esta tela que fecha a janela aberta na Story 3.1.** A fila da programação
 * aponta para `/eventos/{id}` desde então, e a chamada principal desde a 3.3 — um
 * endereço que não existia e caía na 404 do projeto. A partir daqui os dois links
 * chegam a algum lugar.
 *
 * ⚠️ **Server Component, e nenhuma linha de `"use client"` neste arquivo.** A
 * diretiva é do **módulo**: pô-la aqui arrastaria o cabeçalho, a ficha e a arte
 * para o cliente. O que precisa de navegador é o seletor de quantidade, e ele é um
 * arquivo separado (`components/EscolhaDeIngressos.tsx`) que recebe dados prontos
 * por props. O `npm run build` é quem denuncia se isso mudar.
 *
 * **`nao-encontrado` e `indisponivel` são coisas diferentes**, e a tela trata cada
 * uma como tal — mesmo desenho da tela de detalhe do organizador (Story 2.6). O
 * primeiro é `notFound()`; o segundo é uma frase. Aqui a distinção vale ainda
 * mais: quem chega nesta página nunca fez login, e uma 404 dizendo "esse show não
 * existe" para quem tropeçou numa instabilidade é a única das duas mensagens que
 * manda a pessoa desistir.
 *
 * **A Story 3.6 trouxe o botão** — e com ele a única leitura de sessão desta
 * tela. A página continua **pública**: quem não está logado como cliente vê um
 * link para o login no lugar do botão, e o resto da tela é idêntico. A sessão é
 * lida aqui, no servidor, e desce como um `boolean` para a ilha: é o que evita
 * uma ida à rede para ouvir `401` sobre algo que esta página já sabia antes de
 * renderizar.
 */
export default async function PaginaDoEvento({
  params,
}: PageProps<"/eventos/[id]">) {
  // ⚠️ `params` é `Promise` nesta versão do Next — sem o `await`, `id` viraria
  // `undefined` em tempo de execução. O gêmeo está no
  // `organizador/eventos/[id]/page.tsx`.
  const { id } = await params;

  // ⚠️ `obterEvento` nunca levanta, e é isso que permite o `if` abaixo:
  // `notFound()` **levanta**, como o `redirect()`, e não pode ficar dentro de um
  // `try/catch` — o `try` mora dentro do `lib/programacao.ts`.
  const resultado = await obterEvento(id);

  // ⚠️ **Sem guarda de sessão, e a ausência é a decisão**: esta página é pública
  // e continua sendo. A sessão é lida só para saber se **há botão**, e
  // `obterUsuarioDaSessao` já devolve `null` sem ida à rede quando não há cookie
  // (o caso comum aqui). Nenhum `redirect`, nenhum `403`: visitante, organizador
  // e portaria leem a página inteira.
  const usuario = await obterUsuarioDaSessao();

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <Link href="/" className={estilos.voltar}>
          ← Programação
        </Link>
        <p className={estilos.aviso}>
          Não foi possível carregar este evento agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const evento = resultado.evento;

  return (
    <section className={estilos.pagina}>
      {/* Um `<Link>` de texto, e não um botão: voltar é navegação, e a identidade
          não usa botão para isso. Mesmo padrão do `← Meus eventos` da tela do
          organizador. */}
      <Link href="/" className={estilos.voltar}>
        ← Programação
      </Link>

      <div className={estilos.cabecalho}>
        <div className={estilos.cabecalhoTexto}>
          {/* `<h1>` — esta página é o evento, ao contrário da capa, que é um item
              dentro da programação e usa `<h2>`. Ele abre a coluna: **não há
              kicker acima dele nesta tela** (ver a ficha, logo abaixo). */}
          <h1 className={estilos.nomeDoEvento}>{evento.nome}</h1>

          {/* ⚠️ **`DATA`, `CASA` e, quando existe, `CIDADE` — e mais nada**
              (decisão do Igor). O protótipo desenha `ENDEREÇO`, `CLASSIFICAÇÃO` e
              `FONTE`, e nenhum dos três existe no `Evento`: não há coluna de
              endereço, o formulário de publicação não pede uma, e
              `origem_externa_id` é assunto de quem publica. O que a tela mostra é
              o que o banco tem.

              ⚠️ **A data desceu do kicker para dentro da ficha** (decisão do
              Igor, tomada com a tela montada), e o kicker **saiu** em vez de
              ficar junto: os dois diriam a mesma frase com dois tamanhos de fonte
              a três centímetros de distância, que era exatamente a razão de eu ter
              deixado a data de fora daqui. Movida, ela enche a coluna de texto —
              que é o problema que a decisão resolve — sem repetir nada.

              `<dl>` porque é literalmente uma lista de pares rótulo/valor. */}
          <dl className={estilos.ficha}>
            {/* A mesma `dataDaChamada` da capa, e pelo mesmo motivo: num show,
                "sexta" é a informação que situa antes do número. Dia da semana,
                data e hora numa linha só — os três respondem "quando", e partidos
                em três pares o rótulo pesaria mais que o valor. */}
            <div>
              <dt className={estilos.fichaRotulo}>Data</dt>
              <dd className={estilos.fichaValor}>
                {dataDaChamada(evento.data_hora)}
              </dd>
            </div>

            <div>
              <dt className={estilos.fichaRotulo}>Casa</dt>
              <dd className={estilos.fichaValor}>{evento.local}</dd>
            </div>

            {/* A cidade é anulável desde a Story 2.3: a linha **some** inteira,
                em vez de a ficha mostrar um rótulo sobre o vazio. */}
            {evento.cidade && (
              <div>
                <dt className={estilos.fichaRotulo}>Cidade</dt>
                <dd className={estilos.fichaValor}>{evento.cidade}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* A arte **ao lado do cabeçalho** (decisão do Igor), no mesmo padrão da
            capa da 3.3. O quadro sempre tem foto desde 13/08/2026 — o `.arteVazia`
            saiu junto com o caso nulo, aqui e na capa. */}
        <div className={estilos.arte}>
          {/* ⚠️ **`<img>` comum, e não `next/image`** — não existe
              `images.remotePatterns` no `next.config.ts`, e o componente do Next
              estoura em tempo de execução com host não declarado. Mesmo
              `eslint-disable` da capa e da miniatura do catálogo.

              `alt=""` porque a arte é **decorativa**: o nome do artista está
              escrito ao lado dela em 52px, e um `alt` com o mesmo nome faria o
              leitor de tela anunciar o show duas vezes.

              A imagem morta é coberta pelo `.imagemDaArte::after` do CSS, e não
              por um `onError` — que obrigaria esta metade da página a virar ilha
              de cliente. O motivo inteiro está no `page.module.css` da raiz.

              O `??` cobre o evento sem arte com o disco do RockHub, o mesmo
              arquivo 16/10 da capa (ver `lib/arte.ts`). */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={evento.imagem_url ?? ARTE_DE_RESERVA}
            alt=""
            className={estilos.imagemDaArte}
          />
        </div>
      </div>

      <div className={estilos.tituloDosSetores}>
        <h2 className="kicker">Setores</h2>
        <span className={estilos.instrucao}>Escolha a quantidade</span>
      </div>

      {/* Evento **sem setor nenhum**: impossível pela rota de publicação e
          possível por `psql` — e existe no banco de desenvolvimento. Uma frase no
          lugar da lista, sem ilustração e sem botão grande (UX-DR8). O cabeçalho
          continua inteiro acima: o show existe, só não tem setor para vender. */}
      {evento.setores.length === 0 ? (
        <p className={estilos.vazio}>
          Este show ainda não tem setores à venda.
        </p>
      ) : (
        // ⚠️ **A ilha começa aqui**, e o que atravessa a fronteira são dados
        // serializáveis: a lista de setores e o teto por compra. Nenhuma função
        // passa por aqui.
        <EscolhaDeIngressos
          eventoId={evento.id}
          setores={evento.setores}
          maximoPorCompra={evento.maximo_por_compra}
          // ⚠️ **Três desfechos, e quem escolhe continua sendo a página** — era um
          // `podeReservar: boolean` até 13/08/2026. Só o papel `CLIENTE` reserva
          // (AD-9, e a rota cobra o mesmo); o que mudou é que "não reserva"
          // deixou de ser um caso só.
          //
          // O organizador **precisa** ver esta tela: é assim que ele confere como
          // o show dele ficou listado (decisão do Igor). Mandá-lo para o login,
          // como era antes, era pedir que entrasse numa conta em que ele já
          // estava — o link dizia "Entrar para reservar" para quem estava
          // logado. Agora ele vê o botão e recebe a recusa em palavras.
          //
          // ⚠️ **A portaria entra pela mesma porta que o organizador**, e não é
          // descuido: ela quase nunca chega aqui — a tela dela é `/portaria`, e
          // não a programação —, mas a URL de um evento é pública e digitável.
          // Deixá-la no `"entrar"` seria manter, para ela, exatamente o link
          // errado que esta mudança veio consertar. O aviso fala de quem **pode**
          // reservar, não de quem clicou, então serve igual às duas.
          acaoDeCompra={ACAO_POR_PAPEL[usuario?.papel ?? "VISITANTE"]}
        />
      )}
    </section>
  );
}
