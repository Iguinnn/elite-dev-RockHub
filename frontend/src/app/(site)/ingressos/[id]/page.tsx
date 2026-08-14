import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import Canhoto from "@/components/Canhoto";
import CompartilharIngresso from "@/components/CompartilharIngresso";
import { horaDeEntrada } from "@/lib/formato";
import { obterIngresso } from "@/lib/ingressos";
import { casaDoPapel } from "@/lib/papel";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * O canhoto cheio, com o QR — Story 4.2, mais o link compartilhável da 4.3.
 *
 * **As mesmas duas guardas de `/ingressos`**: sem sessão, `redirect` para o
 * login com o caminho de volta preservado; papel diferente de `CLIENTE`,
 * `redirect` para a raiz. Depois delas, `notFound()` cobre "não existe ou
 * não é seu" — o `404` único que a API já responde.
 *
 * **O canhoto virou `<Canhoto>` na Story 4.3**, quando `/i/{token}` passou a
 * desenhar o mesmo objeto para quem recebeu o link. Isto **não** contradiz a
 * decisão da 4.2 de não extrair entre `/reservas/{id}` e esta tela: lá os dois
 * endereços falavam de coisas diferentes; aqui os dois falam do **mesmo
 * ingresso para pessoas diferentes**, e eles serem idênticos é o requisito.
 *
 * O que fica de fora do componente é o chrome desta página — o caminho de
 * volta, a faixa de "já utilizado" e a ilha de compartilhar, que só o dono vê.
 */
export default async function CanhotoDoIngresso({
  params,
}: PageProps<"/ingressos/[id]">) {
  const { id } = await params;

  const usuario = await obterUsuarioDaSessao();
  if (!usuario) {
    redirect(`/login?voltar=${encodeURIComponent(`/ingressos/${id}`)}`);
  }
  if (usuario.papel !== "CLIENTE") {
    redirect(casaDoPapel(usuario.papel));
  }

  const resultado = await obterIngresso(id);

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <Link href="/ingressos" className={estilos.voltar}>
          ← Meus ingressos
        </Link>
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
      <Link href="/ingressos" className={estilos.voltar}>
        ← Meus ingressos
      </Link>

      {ingresso.situacao === "UTILIZADO" && ingresso.usado_em && (
        // Neutro, não vermelho (EXPERIENCE.md#veredito): não é fraude nem
        // falha, é um canhoto que já cumpriu o que prometia.
        <p className={estilos.jaUtilizado}>
          <strong>Já utilizado.</strong> Entrou às {horaDeEntrada(ingresso.usado_em)}.
        </p>
      )}

      {/* ⚠️ **A faixa do expirado é irmã da de cima, e as duas nunca aparecem
          juntas** — `situacao` é um valor só, e é ela que decide qual das duas
          sai. Enquanto a condição era `ingresso.usado_em`, não havia onde encaixar
          um terceiro caso sem inventar uma precedência na tela; agora a
          precedência é do backend (`usado_em` ganha de tudo), e aqui só se lê.

          Mesma classe e mesmo tom neutro: um ingresso que perdeu a validade não é
          um erro de quem está olhando. O que muda é a frase, e ela diz a única
          coisa acionável — o show acabou, não adianta ir à porta. */}
      {ingresso.situacao === "EXPIRADO" && (
        <p className={estilos.jaUtilizado}>
          <strong>O evento já acabou.</strong> Este ingresso não vale mais para
          entrada.
        </p>
      )}

      <div className={estilos.miolo}>
        <Canhoto ingresso={ingresso} />

        {/* A ilha só existe nesta tela: quem abre o link recebido não
            compartilha de novo — e não é dono para poder. */}
        <CompartilharIngresso ingresso={ingresso} />
      </div>
    </section>
  );
}
