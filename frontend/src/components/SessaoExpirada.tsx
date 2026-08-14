import Link from "next/link";

/**
 * A mensagem de sessão expirada — **num lugar só, com o caminho de volta
 * dentro** (13/08/2026).
 *
 * ⚠️ **Ela existe porque a frase sem o link é um beco sem saída.** A sessão dura
 * 8 horas (AD-15) e pode cair com a tela aberta; quando cai, o `POST` volta
 * `401`, a tela diz "sua sessão expirou", a pessoa clica em tentar de novo e
 * recebe `401` outra vez — para sempre, sem nenhum caminho para o login. O code
 * review da Epic 2 encontrou isso no formulário de publicação e o corrigiu **ali
 * dentro**, com um sentinela local; os outros quatro componentes que traduzem o
 * mesmo código nunca receberam a correção, e cada um repetia a frase seca.
 *
 * Extrair não é faxina: é o que faz a correção valer para os cinco de uma vez, e
 * para o sexto que vier. A varredura de superfícies de erro de 13/08/2026 é
 * quem contou os cinco.
 *
 * ⚠️ **`target="_blank"` sempre, e não só na publicação.** Sair da página para
 * entrar de novo descarta o que estiver preenchido — os setores digitados, os
 * ingressos escolhidos no stepper, o número do cartão. Numa aba nova a pessoa
 * entra e volta para clicar de novo com tudo no lugar. É o motivo que o
 * formulário de publicação já registrava, e ele vale igual nos outros quatro.
 *
 * **Não é um componente de erro completo, de propósito**: ele devolve só o
 * conteúdo. Quem decide se isso vai para um `Toast` ou para um `AvisoDeErro` é a
 * tela — a regra de qual superfície usar está escrita no `Toast.tsx`.
 */
export default function SessaoExpirada({
  voltar,
  acao,
}: {
  /**
   * Caminho interno para onde voltar depois de entrar, **sem codificar** — a
   * codificação acontece aqui. É o mesmo `?voltar=` da Story 1.4, sanitizado do
   * lado de lá por `caminhoInternoSeguro`.
   */
  voltar: string;
  /**
   * O que a pessoa estava tentando fazer, em infinitivo: `reservar`, `pagar`,
   * `publicar o evento`. Entra na frase — "entre de novo para reservar" diz mais
   * que "entre de novo", e é a diferença entre um aviso e uma instrução.
   */
  acao: string;
}) {
  return (
    <>
      Sua sessão expirou.{" "}
      <Link href={`/login?voltar=${encodeURIComponent(voltar)}`} target="_blank">
        Entre de novo
      </Link>{" "}
      para {acao} — o que você preencheu continua aqui.
    </>
  );
}
