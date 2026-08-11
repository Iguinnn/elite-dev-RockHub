import Link from "next/link";

import { centavosParaReais, partesDaFilaPublica } from "@/lib/formato";
import { listarProgramacao, type EventoNaProgramacao } from "@/lib/programacao";

import estilos from "./page.module.css";

/**
 * A raiz do produto: a programação pública (Story 3.1).
 *
 * **A primeira tela deste projeto que não tem dono.** Todas as outras ou são
 * de quem entra (login, cadastro) ou de quem publica (`/organizador/*`) — esta
 * responde a quem chegou pelo endereço, sem conta e sem cookie. Por isso não há
 * `obterUsuarioDaSessao`, não há guarda e não há `redirect`: qualquer um dos
 * três aqui seria uma exigência que o backend não faz.
 *
 * Server Component, sem uma linha de `"use client"`. Não há interação nenhuma
 * nesta tela — só leitura e navegação.
 *
 * **Só o que ainda vai acontecer** (decisão do Igor), e o corte é do backend:
 * `GET /eventos` já devolve `data_hora >= agora`. É o oposto de "Meus eventos",
 * onde o corte é da tela — lá o dono da informação é o organizador e o
 * histórico é o inventário dele; aqui o visitante veria metade da página
 * inicial ocupada por shows que não pode comprar.
 */
export default async function Programacao() {
  // `listarProgramacao` nunca levanta: sem `error.tsx`, uma exceção aqui
  // derrubaria a aplicação inteira, não só esta seção.
  const resultado = await listarProgramacao();
  const itens = resultado.estado === "ok" ? resultado.itens : [];

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>Programação</h1>
      </div>

      {/* ⚠️ Duas frases diferentes, de propósito. "Nenhum evento" é verdade
          sobre o produto — não há show marcado; "não deu para carregar" é uma
          falha temporária que melhora sozinha. Uma frase só para os dois casos
          mandaria a pessoa esperar por algo que não vai mudar, ou desistir de
          algo que voltaria em dez segundos. */}
      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          Não foi possível carregar a programação agora. Tente de novo em
          instantes.
        </p>
      )}

      {resultado.estado === "ok" && itens.length === 0 && (
        // Estado vazio (EXPERIENCE.md#Vazio): kicker, frase, fim. Sem
        // ilustração e sem botão grande de chamada — UX-DR8.
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
  const { diaDaSemana, dia, hora } = partesDaFilaPublica(evento.data_hora);
  // ⚠️ Estreitar pelo **preço**, e não só por `esgotado`. Os dois dizem a mesma
  // coisa (o backend garante que um implica o outro), mas só este dá ao
  // TypeScript a certeza de que `preco` não é `null` no ramo do `<b>`. Com
  // `esgotado` sozinho seria preciso um `?? 0`, e "R$ 0,00" é um preço que
  // existe — a fila anunciaria ingresso de graça se o contrato mudasse.
  const preco = evento.preco_minimo_centavos;
  const semIngresso = evento.esgotado || preco === null;

  const conteudo = (
    <>
      <div className={estilos.data}>
        <span className={estilos.diaDaSemana}>{diaDaSemana}</span>
        <span className={estilos.dia}>{dia}</span>
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
