import Logotipo from "./Logotipo";
import estilos from "./Masthead.module.css";
import NavLink from "./NavLink";

/**
 * Cabeçalho de jornal: logotipo, fio simples, navegação, fio duplo fechando o
 * bloco. Os fios são estruturais — o simples separa itens de mesma natureza, o
 * duplo fecha o masthead e o separa do conteúdo.
 *
 * Aqui não entra linha de contexto (data, contador de eventos, subtítulo):
 * foi testada no protótipo e removida por soar gerada (UX-DR10).
 *
 * Server Component. A única ilha de cliente é o `NavLink`, que precisa do
 * caminho atual para marcar o item ativo.
 */
export default function Masthead() {
  return (
    <header className={estilos.masthead}>
      <div className={estilos.topo}>
        <Logotipo />
      </div>

      <nav className={estilos.navbar} aria-label="Navegação principal">
        <NavLink href="/">Início</NavLink>
        <NavLink href="/ingressos">Meus ingressos</NavLink>
        <NavLink href="/conta">Minha conta</NavLink>
      </nav>
    </header>
  );
}
