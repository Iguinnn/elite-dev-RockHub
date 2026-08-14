import { obterUsuarioDaSessao } from "@/lib/sessao";

import Logotipo from "./Logotipo";
import estilos from "./Masthead.module.css";
import NavLink from "./NavLink";

/**
 * Cabeçalho de jornal: logotipo, fio, navegação, fio fechando o bloco. Os fios
 * são estruturais, não decorativos — eles separam itens de natureza diferente.
 *
 * ⚠️ **O de baixo era `3px double` e virou simples** (decisão do Igor,
 * 2026-08-12): o fio duplo é convenção de jornal impresso, e na tela os dois
 * filetes de 1px colados leem como falha de renderização em vez de escolha
 * tipográfica. O `DESIGN.md` continua descrevendo o duplo e **não** foi
 * atualizado — é artefato de planejamento congelado. O motivo inteiro está no
 * `Masthead.module.css`, ao lado da linha que mudou.
 *
 * Aqui não entra linha de contexto (data, contador de eventos, subtítulo):
 * foi testada no protótipo e removida por soar gerada (UX-DR10). Pela mesma
 * razão o nome de quem está logado **não** aparece aqui, mesmo agora que o
 * componente o conhece — `DESIGN.md#Components/masthead` é literal, e os dados
 * da pessoa são o conteúdo da `/conta`.
 *
 * Server Component `async`: lê a sessão para decidir entre `Entrar` e `Minha
 * conta`, e agora também por papel — `Publicar evento` só aparece para quem
 * está logado como `ORGANIZADOR`. Isso torna dinâmica toda rota do grupo
 * `(site)`, e é correto — cabeçalho que depende de quem pediu não pode ser
 * pré-renderizado.
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

        <nav className={estilos.navbar} aria-label="Navegação principal">
          <NavLink href="/">Início</NavLink>
          {/* `Meus eventos` entrou na 2.6, quando a tela dele passou a existir —
              e vem **antes** de `Publicar evento`, porque acompanhar o que está
              no ar é o que o organizador faz todo dia; publicar é eventual. */}
          {usuario?.papel === "ORGANIZADOR" && (
            <>
              <NavLink href="/organizador/eventos">Meus eventos</NavLink>
              <NavLink href="/organizador/publicar">Publicar evento</NavLink>
            </>
          )}
          {/* Só para `CLIENTE`, e antes de `Minha conta`: acompanhar o que se
              comprou é o que se faz depois de comprar, ao contrário dos dados
              da conta, que se olha bem menos (Story 4.1). */}
          {usuario?.papel === "CLIENTE" && (
            <NavLink href="/ingressos">Meus ingressos</NavLink>
          )}
          {usuario ? (
            <NavLink href="/conta">Minha conta</NavLink>
          ) : (
            <NavLink href="/login">Entrar</NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}
