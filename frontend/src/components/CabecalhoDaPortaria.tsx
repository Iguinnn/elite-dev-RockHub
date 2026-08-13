import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./CabecalhoDaPortaria.module.css";
import Logotipo from "./Logotipo";
import NavLink from "./NavLink";

/**
 * A navegação de quem trabalha na porta: marca, quem está validando, dois itens.
 *
 * **Componente e não markup dentro do layout**, e o motivo é o 404. O
 * `not-found.tsx` da **raiz** é o único que atende URL que não casa com rota
 * nenhuma — o docstring dele explica —, e ele renderiza fora de qualquer layout
 * de grupo, então carrega o `Masthead` por conta própria. O efeito para a
 * portaria era o pior possível: errar o endereço (ou clicar num turno enquanto
 * `/portaria/eventos/{id}` não existe, a janela até a Story 5.3) devolvia a
 * casca de jornal, com `Início` e `Minha conta` e nenhum caminho para `/portaria`
 * — e a leitura de quem está na porta é "eu nem estou mais logado".
 *
 * Com o cabeçalho num componente, o 404 da raiz pergunta o papel e desenha a
 * casca certa. Duas telas, uma navegação; copiá-la para o `not-found` daria
 * duas navegações que divergem na primeira mudança.
 *
 * Server Component `async` pelo mesmo motivo do `Masthead`: lê a sessão para
 * escrever o nome. O `usuario` pode ser nulo — o cabeçalho renderiza antes de a
 * página decidir rebater para o login —, e nesse caso a linha de identificação
 * não sai. **Quem protege a rota é a página, nunca este componente.**
 *
 * **O nome de quem está na porta aparece, e isso contraria o `Masthead`.** A
 * Story 1.6 decidiu não mostrar o nome de quem está logado, e
 * `DESIGN.md#Components/masthead` é literal: dado da pessoa é conteúdo da
 * `/conta`. Aqui é outra situação, e o protótipo já a desenhava assim
 * (`Ana Ribeiro · Portaria`) — o celular da porta é **compartilhado**, as duas
 * contas de portaria existem no seed exatamente por isso, e "quem está
 * validando" é a primeira coisa que se confere quando o resultado sai errado.
 *
 * **Dois itens, e para por aí**: *Turnos* e *Minha conta*. Quem trabalha na
 * porta tem uma função só.
 */
export default async function CabecalhoDaPortaria() {
  const usuario = await obterUsuarioDaSessao();

  return (
    <header className={estilos.topo}>
      <div className={estilos.marca}>
        {/* ⚠️ A marca leva para `/portaria`, e não para `/`. O padrão do
            componente mandava quem está na porta para a programação pública, de
            onde o masthead do `(site)` — que não tem item de portaria, por
            decisão — não oferece nenhum caminho de volta. Casca que não leva de
            volta para si mesma é um beco. */}
        <Logotipo href="/portaria" rotulo="RockHub — turnos da portaria" />
        {usuario && (
          <p className={estilos.quem}>
            {usuario.nome} <span aria-hidden="true">·</span> Portaria
          </p>
        )}
      </div>

      <nav className={estilos.nav} aria-label="Navegação da portaria">
        <NavLink href="/portaria">Turnos</NavLink>
        <NavLink href="/portaria/conta">Minha conta</NavLink>
      </nav>
    </header>
  );
}
