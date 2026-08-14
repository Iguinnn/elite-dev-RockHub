import { cookies } from "next/headers";

import { obterUsuarioDaSessao } from "@/lib/sessao";
import { COOKIE_DO_TEMA, normalizarTema } from "@/lib/tema";

import Logotipo from "./Logotipo";
import estilos from "./Masthead.module.css";
import MenuLateral from "./MenuLateral";
import NavLink from "./NavLink";
import SeletorDeTema from "./SeletorDeTema";

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
 * As ilhas de cliente são três: o `NavLink`, que precisa do caminho atual para
 * marcar o item ativo, o `SeletorDeTema`, que precisa do clique, e o
 * `MenuLateral`, que precisa de estado para abrir.
 *
 * ⚠️ **O alternador de tema saiu do `<nav>` em 14/08/2026** (decisão do Igor,
 * junto com a gaveta). Ele era o último item da fileira, e a razão de estar lá
 * era proximidade visual; a razão de sair é mais forte. Com os destinos indo para
 * o `MenuLateral` abaixo de 900px, um alternador dentro do `<nav>` sumiria junto
 * com eles — trocar o tema passaria a exigir abrir o menu, e preferência visual
 * não é destino. Ele agora mora na faixa, ao lado do sanduíche, **visível em
 * qualquer largura**. O argumento antigo continua de pé e só ficou mais forte:
 * item que não navega não pertence à navegação.
 *
 * ⚠️ **Os destinos são escritos uma vez e usados em dois lugares.** A fileira
 * (≥900px) e a gaveta (<900px) recebem o **mesmo** `destinos`, e quem some é
 * decidido por CSS — `.navbar` e `.sanduiche` nunca aparecem juntos. Escrever a
 * lista duas vezes no JSX seria a duplicata que ninguém vê drifar: um papel
 * acrescentado num lugar e esquecido no outro daria a um organizador um menu no
 * celular e outro no desktop, e nenhum teste pegaria.
 */
export default async function Masthead() {
  const usuario = await obterUsuarioDaSessao();
  const tema = normalizarTema((await cookies()).get(COOKIE_DO_TEMA)?.value);

  const destinos = (
    <>
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
    </>
  );

  return (
    <header className={estilos.masthead}>
      <div className={estilos.topo}>
        <Logotipo />

        <div className={estilos.controles}>
          <nav className={estilos.navbar} aria-label="Navegação principal">
            {destinos}
          </nav>
          <SeletorDeTema tema={tema} />
          <MenuLateral>{destinos}</MenuLateral>
        </div>
      </div>
    </header>
  );
}
