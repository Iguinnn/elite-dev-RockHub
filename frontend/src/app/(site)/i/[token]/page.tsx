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
 *
 * **Três estados, e nenhum deles é a 404 do projeto**: o canhoto, o link que
 * não vale mais e a indisponibilidade da API. O do meio é o que a Story 4.4
 * acrescentou — ver o comentário longo dentro da função.
 */
export default async function IngressoCompartilhado({
  params,
}: PageProps<"/i/[token]">) {
  const { token } = await params;

  const resultado = await obterIngressoCompartilhado(token);

  // ⚠️ **Tela própria, e não o `notFound()` do projeto** (decisão do Igor, na
  // conferência da 4.4). A 404 genérica — "este endereço não existe, confira o
  // link" — manda quem recebeu o link conferir um endereço que ele copiou
  // certo, e não diz a única coisa acionável: o link foi cortado, peça outro.
  //
  // ⚠️ **A frase é a mesma para link revogado e para token que nunca
  // existiu**, e é isso que preserva a decisão da techspec: os dois casos
  // continuam indistinguíveis daqui de fora, porque o backend responde o mesmo
  // `404 LINK_NAO_ENCONTRADO` para ambos e não guarda nada que diga que um
  // link existiu. Distinguir de verdade exigiria gravar a revogação numa
  // coluna — o oposto de escrever `NULL` — e aí o endereço morto viraria um
  // oráculo de "este ingresso existe". O custo assumido é que um token
  // digitado errado também lê "revogado"; é o caso raro, e a orientação que a
  // frase dá (peça um link novo) continua sendo a certa nele.
  if (resultado.estado === "nao-encontrado") {
    return (
      <section className={estilos.pagina}>
        <p className={`kicker ${estilos.procedencia}`}>Link indisponível</p>
        <p className={estilos.frase}>
          Link revogado pelo proprietário do ingresso.
        </p>
        <p className={estilos.detalhe}>
          Peça um link novo a quem compartilhou o ingresso com você.
        </p>
      </section>
    );
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
