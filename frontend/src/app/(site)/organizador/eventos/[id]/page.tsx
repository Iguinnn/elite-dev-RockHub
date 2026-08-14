import Link from "next/link";
import { notFound, redirect } from "next/navigation";

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
 * **Não há como editar nada aqui**, e é decisão do Igor (Story 2.6): nem os
 * dados do evento, nem a escala da portaria. As duas coisas custariam rota de
 * escrita, invariante nova e uma dúzia de testes — e a capacidade, em
 * particular, não pode cair abaixo de `vendidos`, o que é história para outra
 * story.
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

  return (
    <section className={estilos.pagina}>
      <Link href="/organizador/eventos" className={estilos.voltar}>
        ← Meus eventos
      </Link>

      {evento.publicado_em && (
        <div className="kicker">{momentoDaPublicacao(evento.publicado_em)}</div>
      )}
      <h1 className={estilos.nomeDoEvento}>{evento.nome}</h1>
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
          // exigir a escala ficaram sem ninguém, e não há como escalar depois.
          // A frase diz o que é, sem quebrar a tela.
          <p className={estilos.semNinguem}>
            Ninguém está escalado para validar os ingressos deste evento. Ele foi
            publicado antes de a escala passar a ser obrigatória, e não há como
            mudá-la depois da publicação.
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
