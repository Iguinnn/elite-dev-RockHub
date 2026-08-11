import Link from "next/link";

import estilos from "./Logotipo.module.css";

/**
 * A marca, num lugar só — e sempre o caminho de volta para a raiz.
 *
 * Aqui eu abri exceção à regra de não abstrair antes do terceiro uso (a mesma
 * que mantém o CSS do estado vazio repetido): aquilo era estilo, e estilo
 * divergente é feio. Isto é o nome da aplicação — se o masthead e a tela de
 * acesso escreverem a marca cada um do seu jeito, a identidade racha.
 *
 * **Por que é um `Link` e não um `span`.** O grupo `(entrada)` não tem masthead,
 * por decisão — quem ainda não entrou não deve ver navegação que não pode usar.
 * O efeito colateral era um beco: quem digitava `/login` na barra de endereço
 * ficava sem nenhum caminho para `/`, porque os únicos links da tela eram o par
 * `/login` ↔ `/cadastro`. Levar a marca de volta para a raiz é a convenção que
 * todo site cumpre e não reintroduz navegação nenhuma — é a mesma marca, agora
 * clicável.
 *
 * O `className` fica no `<a>`, não num elemento por dentro: o `globals.css` já
 * zera cor e sublinhado de link, e o `:focus-visible` âmbar (UX-DR9) precisa
 * contornar a palavra inteira.
 */
export default function Logotipo() {
  return (
    <Link href="/" className={estilos.logo} aria-label="RockHub — página inicial">
      Rock<em>Hub</em>
    </Link>
  );
}
