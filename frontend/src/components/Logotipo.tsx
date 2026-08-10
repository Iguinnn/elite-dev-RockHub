import estilos from "./Logotipo.module.css";

/**
 * A marca, num lugar só.
 *
 * Aqui eu abri exceção à regra de não abstrair antes do terceiro uso (a mesma
 * que mantém o CSS do estado vazio repetido): aquilo era estilo, e estilo
 * divergente é feio. Isto é o nome da aplicação — se o masthead e a tela de
 * acesso escreverem a marca cada um do seu jeito, a identidade racha.
 */
export default function Logotipo() {
  return (
    <span className={estilos.logo}>
      Rock<em>Hub</em>
    </span>
  );
}
