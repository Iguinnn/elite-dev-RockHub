import { obterUsuarioDaSessao } from "@/lib/sessao";

import Logotipo from "./Logotipo";
import estilos from "./Masthead.module.css";
import NavLink from "./NavLink";

/**
 * Cabeçalho de jornal: logotipo, fio simples, navegação, fio duplo fechando o
 * bloco. Os fios são estruturais — o simples separa itens de mesma natureza, o
 * duplo fecha o masthead e o separa do conteúdo.
 *
 * Aqui não entra linha de contexto (data, contador de eventos, subtítulo):
 * foi testada no protótipo e removida por soar gerada (UX-DR10). Pela mesma
 * razão o nome de quem está logado **não** aparece aqui, mesmo agora que o
 * componente o conhece — `DESIGN.md#Components/masthead` é literal, e os dados
 * da pessoa são o conteúdo da `/conta`.
 *
 * Server Component `async`: lê a sessão para decidir entre `Entrar` e `Minha
 * conta`. Isso torna dinâmica toda rota do grupo `(site)`, e é correto —
 * cabeçalho que depende de quem pediu não pode ser pré-renderizado.
 *
 * A única ilha de cliente continua sendo o `NavLink`, que precisa do caminho
 * atual para marcar o item ativo.
 */
export default async function Masthead() {
  const usuario = await obterUsuarioDaSessao();

  return (
    <header className={estilos.masthead}>
      <div className={estilos.topo}>
        <Logotipo />
      </div>

      <nav className={estilos.navbar} aria-label="Navegação principal">
        <NavLink href="/">Início</NavLink>
        {/* `Meus ingressos` saiu daqui até a Epic 4 criar a tela: link que cai
            no 404 não fica no repositório (precedente da Story 1.4). */}
        {usuario ? (
          <NavLink href="/conta">Minha conta</NavLink>
        ) : (
          <NavLink href="/login">Entrar</NavLink>
        )}
      </nav>
    </header>
  );
}
