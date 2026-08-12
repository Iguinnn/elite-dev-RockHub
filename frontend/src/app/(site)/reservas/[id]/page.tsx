import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import Cronometro from "@/components/Cronometro";
import { centavosParaReais, dataDaChamada } from "@/lib/formato";
import { obterReserva } from "@/lib/reservas";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * A reserva: os itens, o total e o cronômetro dos 10 minutos (Story 3.6).
 *
 * **Ela tem endereço próprio porque a reserva existe no servidor** (decisão do
 * Igor). Uma reserva é uma linha no banco com prazo, não um estado desta tela:
 * ela sobrevive a fechar a aba, e recarregar aqui continua mostrando o mesmo
 * tempo correndo. Um recibo no rodapé da página do evento seria mais barato e
 * perderia o caminho de volta na primeira recarga.
 *
 * ⚠️ **Não há botão de pagar nesta tela** (decisão do Igor): pagar é a Story
 * 3.8, junto com a rota que o botão chamaria. Mesma disciplina que manteve a 3.4
 * sem botão de reservar — botão presente e desabilitado lê como defeito, não
 * como escopo. É **nesta** página que a 3.8 acrescenta o pagamento.
 *
 * ⚠️ **Server Component, sem uma linha de `"use client"` neste arquivo.** A
 * diretiva é do módulo e arrastaria a página inteira para o cliente; o que
 * precisa de navegador é o cronômetro, e ele é um componente separado que recebe
 * uma string por prop.
 *
 * **A guarda de sessão é a de `/conta` e de `/organizador/eventos`, literal**:
 * sem sessão, `redirect` para o login com o caminho de volta preservado. Não há
 * guarda de papel aqui — o `404` da API já responde por "não é sua", e um
 * organizador logado que abrisse este endereço veria a mesma 404 que veria para
 * uma reserva inexistente.
 */
export default async function PaginaDaReserva({
  params,
}: PageProps<"/reservas/[id]">) {
  // ⚠️ `params` é `Promise` nesta versão do Next — o gêmeo está na página do
  // evento e na do organizador.
  const { id } = await params;

  const usuario = await obterUsuarioDaSessao();
  if (!usuario) {
    redirect(`/login?voltar=${encodeURIComponent(`/reservas/${id}`)}`);
  }

  // `obterReserva` nunca levanta, e é isso que permite os dois `if` abaixo:
  // `notFound()` e `redirect()` **levantam**, e não podem ficar dentro de um
  // `try/catch` — o `try` mora no `lib/reservas.ts`.
  const resultado = await obterReserva(id);

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
          Não foi possível carregar esta reserva agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const reserva = resultado.reserva;

  return (
    <section className={estilos.pagina}>
      {/* O caminho de volta é o **evento**, e não a programação: quem está nesta
          tela veio de lá, e é para lá que se volta para escolher outro setor. */}
      <Link href={`/eventos/${reserva.evento_id}`} className={estilos.voltar}>
        ← {reserva.evento_nome}
      </Link>

      <div className={estilos.cabecalho}>
        <div>
          <span className="kicker">Reserva</span>
          <h1 className={estilos.nomeDoEvento}>{reserva.evento_nome}</h1>
          <p className={estilos.data}>{dataDaChamada(reserva.evento_data_hora)}</p>
        </div>

        <Cronometro expiraEm={reserva.expira_em} />
      </div>

      {/* Uma lista de fios, como todo agrupamento deste produto: sem card, sem
          sombra, sem raio (UX-DR3). */}
      <div className={estilos.itens}>
        {reserva.itens.map((item) => (
          <div key={item.setor_id} className={estilos.item}>
            <span className={estilos.nomeDoSetor}>{item.setor_nome}</span>
            <span className={estilos.quantidade}>
              {item.quantidade} ×{" "}
              {/* O preço **congelado** no ato da reserva. Se o organizador mudar
                  a tabela amanhã, esta linha continua dizendo quanto custou. */}
              R$ {centavosParaReais(item.preco_unitario_centavos)}
            </span>
            <span className={estilos.subtotal}>
              R$ {centavosParaReais(item.preco_unitario_centavos * item.quantidade)}
            </span>
          </div>
        ))}
      </div>

      <div className={estilos.rodape}>
        <span className={estilos.rotuloDoTotal}>Total</span>
        <span className={estilos.total}>
          R$ {centavosParaReais(reserva.total_centavos)}
        </span>
      </div>

      {/* ⚠️ **Uma frase, e nenhum botão.** Ela diz o que está garantido e o que
          acontece se o prazo acabar — que é a informação que falta a quem chegou
          aqui. O pagamento é a Story 3.8, e entra logo abaixo desta linha. */}
      <p className={estilos.nota}>
        Seus lugares estão segurados até o fim do prazo acima. Passado ele, os
        ingressos voltam para a venda.
      </p>
    </section>
  );
}
