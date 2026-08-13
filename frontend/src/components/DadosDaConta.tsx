import BotaoSair from "./BotaoSair";
import estilos from "./DadosDaConta.module.css";

import type { UsuarioDaSessao } from "@/lib/sessao";

/**
 * Nome, e-mail, papel e a saída — a "Minha conta" das duas cascas.
 *
 * **Nasceu como o corpo de `(site)/conta/page.tsx` e virou componente na Story
 * 5.1**, quando a portaria ganhou casca própria e precisou da mesma tela dentro
 * dela. As duas saídas fáceis foram descartadas:
 *
 * - **Linkar `/portaria/conta` para `/conta`** jogaria a portaria de volta no
 *   masthead de jornal que a casca própria existe justamente para evitar — quem
 *   está em pé na porta veria a programação de shows ocupando a metade de cima
 *   do celular.
 * - **Copiar as vinte linhas** produziria duas telas de conta que divergem no
 *   dia em que uma delas mudar, e ninguém saberia qual está certa.
 *
 * O CSS veio junto, no módulo ao lado: estilo que mora numa página e conteúdo
 * que mora noutra é a divergência de volta pela porta dos fundos.
 *
 * **Recebe o usuário por prop em vez de chamar `obterUsuarioDaSessao()`.** As
 * duas páginas que o renderizam já leram a sessão para a guarda de redirecionar,
 * e a leitura é `cache()`ada por requisição — não haveria ida à rede a mais.
 * Mas a prop torna o componente puro: ele não decide se há sessão, e não existe
 * caminho em que ele renderize um `usuario` nulo com a página achando que
 * protegeu.
 */
export default function DadosDaConta({ usuario }: { usuario: UsuarioDaSessao }) {
  return (
    <section className={estilos.pagina}>
      <p className="kicker">Minha conta</p>

      {/* Serifada só no nome: é nome próprio. E-mail e papel são dado de
          máquina, então mono em versalete — UX-DR2, a mesma divisão do
          formulário de cadastro. */}
      <h1 className={estilos.nome}>{usuario.nome}</h1>

      <dl className={estilos.dados}>
        <dt>E-mail</dt>
        <dd>{usuario.email}</dd>
        <dt>Papel</dt>
        <dd>{usuario.papel}</dd>
      </dl>

      <div className={estilos.saida}>
        <BotaoSair />
      </div>
    </section>
  );
}
