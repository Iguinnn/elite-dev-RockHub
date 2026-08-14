/**
 * O tema escolhido, que mora num cookie.
 *
 * **Cookie lido no servidor, e não `localStorage`.** Com `localStorage` a
 * primeira pintura sai sempre escura e vira clara no cliente, e esse pisca-pisca
 * numa tela de avaliação lê como defeito, não como recurso. O preço é tornar
 * dinâmica toda rota da aplicação, porque quem lê o cookie é o layout raiz — o
 * grupo `(site)` já era dinâmico por causa do masthead que lê sessão, e as
 * outras duas cascas passam a ser.
 *
 * **Sem `prefers-color-scheme` em lugar nenhum, de propósito.** Quem chega vê o
 * jornal noturno; clara quem quiser. Seguir a preferência do sistema faria
 * metade de quem abre o produto nunca ver a identidade que está sendo avaliada.
 *
 * Este módulo **não importa `next/headers`**, e isso não é descuido: ele é
 * importado dos dois lados da fronteira — os layouts leem o cookie no servidor,
 * o `SeletorDeTema` o escreve no navegador. `next/headers` num módulo que chega
 * ao bundle do cliente é erro de build, a mesma razão pela qual `lib/sessao.ts`
 * e `lib/api.ts` são dois arquivos.
 *
 * Ele existe porque a regra de normalização tem **três** sítios (o layout raiz,
 * o masthead e o próprio seletor), e a convenção do projeto é copiar em dois e
 * extrair no terceiro. Uma cópia que drifte aqui não quebra o build: ela mostra
 * o rótulo errado no botão de uma casca só.
 */

export type Tema = "claro" | "escuro";

export const COOKIE_DO_TEMA = "tema";

/** Um ano, em segundos. A escolha de tema não deve expirar durante o uso. */
export const VALIDADE_DO_TEMA = 60 * 60 * 24 * 365;

/**
 * O escuro é o padrão, e **qualquer coisa que não seja `claro` cai nele** —
 * cookie ausente, valor antigo, lixo digitado à mão no inspetor. A leitura é
 * deliberadamente assimétrica: o modo escuro é a identidade do produto, então
 * ele é o estado para o qual o erro cai.
 */
export function normalizarTema(valor: string | undefined): Tema {
  return valor === "claro" ? "claro" : "escuro";
}
