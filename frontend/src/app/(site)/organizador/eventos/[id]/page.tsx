import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import BotaoDeExclusao from "@/components/BotaoDeExclusao";
import { obterMeuEvento } from "@/lib/eventos";
import { centavosParaReais, dataPorExtenso, momentoDaPublicacao } from "@/lib/formato";
import { casaDoPapel } from "@/lib/papel";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "../page.module.css";

/**
 * O detalhe de um evento do organizador: o inventário setor a setor e quem
 * está escalado na porta.
 *
 * Server Component, com as **mesmas duas guardas** da lista e da tela de
 * publicar. O módulo de estilo é o da pasta acima, compartilhado com a lista:
 * as duas telas falam o mesmo vocabulário de fila e de inventário.
 *
 * **`nao-encontrado` e `indisponivel` são coisas diferentes, e a tela trata
 * cada uma como tal.** O primeiro é `notFound()` — a 404 do projeto, que já
 * existe e já tem a casca. O segundo é uma frase: a API fora do ar não é
 * evento inexistente, e mandar quem tropeçou numa instabilidade para uma 404
 * seria dizer que o evento dele sumiu.
 *
 * ⚠️ **Daqui se edita, desde 13/08/2026** — e isto reverte a decisão que este
 * docstring anunciava na Story 2.6 ("não há como editar nada aqui... é história
 * para outra story"). A história chegou: `docs/techspec-editar-evento.md`. O que
 * a decisão antiga previa como caro se resolveu de outro jeito — a capacidade não
 * precisa da regra "não pode cair abaixo de `vendidos`" porque **editar só é
 * permitido com `vendidos == 0` em todos os setores**, e uma trava só substitui
 * uma família inteira de invariantes.
 *
 * **O botão fica ao lado do `<h1>`, e a frase toma o lugar dele quando não dá.**
 * Descartei esconder o botão sem dizer nada — quem viu ontem procura hoje e não
 * entende o sumiço —, e descartei um botão que leva a uma tela só para dizer não,
 * que é um clique desperdiçado. A frase no lugar do botão faz as duas coisas: diz
 * que existe uma edição e diz por que ela não está disponível.
 */
export default async function DetalheDoEvento({
  params,
}: PageProps<"/organizador/eventos/[id]">) {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Forganizador%2Feventos");
  }
  if (usuario.papel !== "ORGANIZADOR") {
    redirect(casaDoPapel(usuario.papel));
  }

  // ⚠️ `params` é `Promise` nesta versão do Next — sem o `await`, `id` viraria
  // `undefined` em tempo de execução.
  const { id } = await params;

  // ⚠️ `obterMeuEvento` nunca levanta, e é isso que permite o `if` abaixo:
  // `notFound()` **levanta**, como o `redirect()`, e não pode ficar dentro de
  // um `try/catch` — o `try` mora dentro do `lib/eventos.ts`.
  const resultado = await obterMeuEvento(id);

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <Link href="/organizador/eventos" className={estilos.voltar}>
          ← Meus eventos
        </Link>
        <p className={estilos.aviso}>
          Não foi possível carregar este evento agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const evento = resultado.evento;
  const origem = [evento.local, evento.cidade].filter(Boolean).join(" · ");

  // As mesmas duas leituras da tela de editar, e é essa igualdade que impede o
  // botão de oferecer o que a outra tela recusa. `vendidos > 0` é a trava do
  // backend (AD-3: o estoque sobe na **reserva**, não no pagamento), e o show que
  // já aconteceu é o `EVENTO_NO_PASSADO` visto do lado de cá.
  const vendeu = evento.setores.some((setor) => setor.vendidos > 0);
  const jaAconteceu = new Date(evento.data_hora) <= new Date();

  return (
    <section className={estilos.pagina}>
      <Link href="/organizador/eventos" className={estilos.voltar}>
        ← Meus eventos
      </Link>

      {evento.publicado_em && (
        <div className="kicker">{momentoDaPublicacao(evento.publicado_em)}</div>
      )}
      {/* Título e ação nas pontas — a mesma anatomia do `.secTitulo` da lista,
          sem o fio: aqui o que vem embaixo é a linha do show, não uma fila. */}
      <div className={estilos.cabecalhoDoEvento}>
        <h1 className={estilos.nomeDoEvento}>{evento.nome}</h1>
        {/* Três estados, e não há um quarto:
            · nem vendeu nem aconteceu → `Editar` e `Excluir` lado a lado;
            · já aconteceu e não vendeu → a frase do editar **e o `Excluir`**;
            · vendeu → só a frase, agora falando dos dois verbos. */}
        <div className={estilos.acoesDoEvento}>
          {vendeu ? (
            // ⚠️ **Esta frase mudou de texto no commit 3**, e precisava mudar: ela
            // dizia só "não pode mais ser editado", e agora excluir também está
            // barrado. Frase de tela que sobrevive ao fato que a justificava
            // ensina a pessoa a procurar o que não existe — é a mesma armadilha
            // que o commit 2 já corrigiu uma vez na frase da portaria.
            <p className={estilos.semEdicao}>
              Este evento já vendeu ingressos e não pode mais ser editado nem
              excluído.
            </p>
          ) : (
            <>
              {jaAconteceu ? (
                <p className={estilos.semEdicao}>
                  Esse show já aconteceu e não pode mais ser editado.
                </p>
              ) : (
                <Link
                  href={`/organizador/eventos/${evento.id}/editar`}
                  className={estilos.editar}
                >
                  Editar
                </Link>
              )}
              {/* **Excluir sobrevive ao show que já aconteceu, e editar não** —
                  é a assimetria decidida na spec, vista da tela. Editar a data
                  de um show passado o faria reaparecer na programação pública;
                  excluí-lo não faz nada reaparecer, e é justamente o caso em que
                  a exclusão é faxina. */}
              <BotaoDeExclusao eventoId={evento.id} nome={evento.nome} />
            </>
          )}
        </div>
      </div>
      <p className={estilos.linhaDoShow}>
        {dataPorExtenso(evento.data_hora)} · {origem}
      </p>

      {/* Números exatos, sem medidor: proporção é para quem compra;
          organizador vê o inventário dele (UX-DR7). */}
      <div className={estilos.bloco}>
        <div className="kicker">Setores</div>
        <div className={estilos.linhas}>
          {evento.setores.map((setor) => (
            <div key={setor.id} className={estilos.linhaSetor}>
              <span className={estilos.nomeDoSetor}>{setor.nome}</span>
              <span className={estilos.numero}>
                {setor.vendidos}/{setor.capacidade} vendidos
              </span>
              <span className={estilos.numero}>
                R$ {centavosParaReais(setor.preco_centavos)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className={estilos.bloco}>
        <div className="kicker">Na porta</div>
        {evento.portarias.length === 0 ? (
          // ⚠️ Acontece de verdade: os eventos publicados antes de a Story 2.5
          // exigir a escala ficaram sem ninguém.
          //
          // **A segunda frase mudou em 13/08/2026**, e ela precisava mudar: dizia
          // "não há como mudá-la depois da publicação", que deixou de ser verdade
          // no dia em que esta tela ganhou o botão `Editar`. Frase de tela que
          // sobrevive ao fato que a justificava é pior que frase nenhuma — ela
          // ensina a pessoa a não procurar o conserto que existe.
          <p className={estilos.semNinguem}>
            Ninguém está escalado para validar os ingressos deste evento. Ele foi
            publicado antes de a escala passar a ser obrigatória
            {jaAconteceu || vendeu
              ? ", e agora não há mais como escalar: o evento já vendeu ou já aconteceu."
              : " — dá para resolver em Editar, aqui em cima."}
          </p>
        ) : (
          <div className={estilos.linhas}>
            {evento.portarias.map((conta) => (
              <div key={conta.id} className={estilos.linhaPortaria}>
                <span className={estilos.nomeDaConta}>{conta.nome}</span>
                <span className={estilos.emailDaConta}>{conta.email}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
