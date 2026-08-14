import type { UsuarioDaSessao } from "./sessao";

/**
 * A tela inicial de cada papel — a "casa" de quem está logado (13/08/2026).
 *
 * ⚠️ **Ela existia dentro do `FormularioLogin` e servia a um consumidor só.** A
 * extração veio de um defeito encontrado na conferência: a portaria entrou por
 * uma tela de login que carregava `?voltar=/ingressos` (herdado de uma sessão de
 * cliente anterior), o login respeitou o `voltar`, `/ingressos` recusou o papel
 * e mandou para `/` — e ela terminou na programação pública, com um masthead que
 * não a identificava e sem nenhum caminho de volta para os turnos.
 *
 * O `voltar` continua ganhando do destino por papel no login, e isso está certo:
 * quem clicou em "Entrar" no meio de alguma coisa quer voltar para lá. O que
 * estava errado era a **recusa**: `redirect("/")` manda todo mundo para o mesmo
 * lugar, e `/` só é a casa de duas das três contas.
 *
 * ⚠️ **Módulo puro, sem `next/headers`**, e é isso que permite ao
 * `FormularioLogin` (ilha de cliente) e às guardas das páginas (Server
 * Components) consumirem o mesmo mapa. O `import type` do `UsuarioDaSessao` é
 * apagado na compilação e não arrasta o `lib/sessao.ts` para o bundle do
 * navegador.
 */
export function casaDoPapel(papel: UsuarioDaSessao["papel"] | string): string {
  // `"/"` para o desconhecido, e não `undefined`: uma consulta a um mapa
  // incompleto devolveria `undefined`, e nem `router.push` nem `redirect` sabem
  // navegar para isso. O papel novo cai na programação, que é pública — e não
  // numa tela em branco.
  return papel === "PORTARIA" ? "/portaria" : "/";
}
