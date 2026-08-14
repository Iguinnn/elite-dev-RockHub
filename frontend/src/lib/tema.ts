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
 * **Sem `prefers-color-scheme` em lugar nenhum, de propósito.** O modo de entrada
 * é decisão do produto, não do sistema operacional de quem chega — seguir a
 * preferência da máquina faria a primeira tela ser sorteada por uma
 * configuração que ninguém fez pensando neste site.
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
 * ⚠️ **O claro virou o padrão em 14/08/2026** (decisão do Igor). Era o escuro
 * desde a Story 1.2, e a inversão é de uma linha porque a assimetria sempre
 * esteve concentrada aqui: `layout.tsx` escreve `data-tema` explícito em toda
 * requisição, e a cascata do `globals.css` funciona nos dois sentidos sem tocar
 * num token. A `/portaria` **não muda**, e não por sorte — ela declara
 * `data-tema="escuro"` na própria casca (`portaria/layout.tsx:56`), justamente
 * para ficar travada no jornal noturno enquanto o resto do produto clareia.
 *
 * **Qualquer coisa que não seja `escuro` cai no claro** — cookie ausente, valor
 * antigo, lixo digitado à mão no inspetor. A leitura continua deliberadamente
 * assimétrica; o que mudou é o lado para o qual o erro cai.
 *
 * ⚠️ **Isto contraria a identidade "jornal noturno"** do `DESIGN.md`, que é
 * artefato de planejamento congelado e não foi atualizado. O escuro era o padrão
 * exatamente para que quem abre o produto visse a identidade sem pedir. Fica
 * registrado que a troca é escolha consciente, não descuido: o modo claro já
 * era um modo inteiro e calibrado (contraste conferido em 14/08/2026), e a
 * decisão de qual deles recebe quem chega é de produto, não de arquitetura.
 */
export function normalizarTema(valor: string | undefined): Tema {
  return valor === "escuro" ? "escuro" : "claro";
}
