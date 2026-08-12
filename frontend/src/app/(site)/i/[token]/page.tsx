import { notFound } from "next/navigation";

import Canhoto from "@/components/Canhoto";
import { horaDeEntrada } from "@/lib/formato";
import { obterIngressoCompartilhado } from "@/lib/ingressos";

import estilos from "./page.module.css";

/**
 * O ingresso que um link compartilhado abre — a Story 4.3.
 *
 * ⚠️ **Sem guarda nenhuma, e a ausência é a decisão.** Esta é a única tela do
 * projeto que mostra dado de uma conta sem exigir sessão: quem recebeu o link
 * por WhatsApp pode nunca ter entrado no RockHub, e é essa pessoa que vai
 * passar na porta com ele. Nenhum `obterUsuarioDaSessao()` aqui — acrescentar
 * um faria a próxima pessoa supor que a tela é do dono.
 *
 * **Dentro de `(site)`, com masthead.** A casca já lida com visitante desde a
 * Story 3.1: quem abre o link vê o cabeçalho com *Entrar*, como em qualquer
 * tela pública. Uma casca própria seria uma segunda identidade para a mesma
 * marca.
 *
 * **`/i/{token}`, curto de propósito**: é um endereço para colar em conversa,
 * e cada segmento a mais é caractere que atravessa a rede social junto.
 *
 * O canhoto é **o mesmo** `<Canhoto>` do dono, `titular_nome` e `usado_em`
 * inclusive — um canhoto que escondesse o titular ou fingisse que o ingresso
 * ainda vale seria um segundo canhoto, e a diferença apareceria na porta.
 */
export default async function IngressoCompartilhado({
  params,
}: PageProps<"/i/[token]">) {
  const { token } = await params;

  const resultado = await obterIngressoCompartilhado(token);

  // Link revogado e link que nunca existiu caem os dois aqui, com a 404 do
  // projeto — é o que faz a revogação da Story 4.4 ser um corte, e não um
  // aviso de que existiu algo ali.
  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.aviso}>
          Não foi possível carregar este ingresso agora. Tente de novo em
          instantes.
        </p>
      </section>
    );
  }

  const ingresso = resultado.ingresso;

  return (
    <section className={estilos.pagina}>
      {/* Quem abre o link precisa saber que está vendo o ingresso de outra
          pessoa — sem isso, a tela parece "meu ingresso" para quem chegou
          direto pelo endereço. */}
      <p className={`kicker ${estilos.procedencia}`}>Ingresso compartilhado</p>

      {ingresso.usado_em && (
        // A gêmea da faixa de `/ingressos/[id]`, e pelo mesmo motivo: neutra,
        // não vermelha (EXPERIENCE.md#veredito). Aqui ela pesa mais — quem
        // recebeu o link não tem como saber que o ingresso já foi usado, e
        // descobrir isso na fila é o pior lugar possível.
        <p className={estilos.jaUtilizado}>
          <strong>Já utilizado.</strong> Entrou às {horaDeEntrada(ingresso.usado_em)}.
        </p>
      )}

      <div className={estilos.miolo}>
        <Canhoto ingresso={ingresso} />
      </div>
    </section>
  );
}
