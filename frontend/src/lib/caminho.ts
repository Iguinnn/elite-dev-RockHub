/**
 * Sanitização de caminho vindo da URL — o `?voltar=` das telas de acesso.
 *
 * Função pura, sem nada de `next/*`: é importada tanto de Server quanto de
 * Client Component.
 *
 * **Por que ela existe.** `?voltar=` é um valor que quem chega escolhe e a
 * aplicação obedece. Sem filtro é o redirecionamento aberto clássico: um link
 * para o nosso domínio que joga a pessoa em outro site logo depois de ela
 * digitar a senha. E entregar string não sanitizada ao `router.push` é pior —
 * a documentação do Next avisa que uma URL `javascript:` **executa no contexto
 * da página**, o que faz disto um XSS, não só um redirecionamento indevido.
 */

// Lista de **prefixos recusados**, não de caminhos permitidos. Uma lista de
// permitidos seria mais rigorosa e obrigaria a editar este arquivo a cada tela
// nova das Epics 3 a 5 — e no dia em que alguém esquecesse, a tela nova
// deixaria de receber o retorno em silêncio.
//
// `//` e `/\` porque o navegador lê os dois como início de host (`//exemplo.com`
// é protocolo relativo; a contrabarra é normalizada para barra por vários
// navegadores). `/login` e `/cadastro` porque entrar para cair na tela de
// entrar é laço.
const PREFIXOS_RECUSADOS = ["//", "/\\", "/login", "/cadastro"];

export function caminhoInternoSeguro(valor: unknown, padrao = "/"): string {
  // `unknown` e não `string`: `searchParams` entrega `string | string[] |
  // undefined`, e `?voltar=a&voltar=b` chega como lista.
  if (typeof valor !== "string" || !valor.startsWith("/")) return padrao;
  if (PREFIXOS_RECUSADOS.some((prefixo) => valor.startsWith(prefixo))) return padrao;
  return valor;
}
