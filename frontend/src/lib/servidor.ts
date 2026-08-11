import { cookies } from "next/headers";

/**
 * O caminho do servidor para falar com a API: URL absoluta e cookie
 * repassado à mão. Compartilhado por `sessao.ts` (sessão do usuário) e
 * `catalogo.ts` (Story 2.2, primeiro Server Component a buscar dado de
 * domínio, não sessão) — daí ter saído do `sessao.ts` e ganho arquivo
 * próprio a partir do momento em que passou a ter dois consumidores.
 *
 * `next/headers` aqui dentro é o que impede este módulo de ser importado por
 * um Client Component: a fronteira servidor/cliente é física, não convenção
 * — igual ao motivo de `sessao.ts` não morar em `api.ts`.
 */

// URL absoluta, e a mesma variável do `next.config.ts`. O `rewrite` de
// `/api/*` é do navegador: um `fetch("/api/…")` daqui não tem origem para
// resolver.
export const API_URL = process.env.API_URL ?? "http://localhost:8000";

// O padrão `localhost` é o valor certo em desenvolvimento e um bug silencioso
// em produção: o servidor da Vercel tentaria falar consigo mesmo, toda
// chamada cairia no `catch` de quem usa este módulo, e o sintoma seria
// silencioso — sem sessão, sem catálogo, sem uma linha de erro visível na
// tela. O aviso é impresso uma vez, na primeira renderização do servidor, e
// não derruba o build de propósito — derrubar deixaria todo deploy de
// Preview sem subir.
if (process.env.NODE_ENV === "production" && !process.env.API_URL) {
  console.error(
    "[RockHub] API_URL não está definida. As chamadas ao backend vão tentar " +
      "http://localhost:8000 e falhar, e a aplicação inteira vai renderizar " +
      "como visitante. Defina API_URL no painel da Vercel, para Production E " +
      "Preview, e refaça o deploy.",
  );
}

// Acoplamento assumido: o mesmo nome está em `cookie_sessao_nome`, no
// `backend/app/core/config.py`. Trocar lá exige trocar aqui.
export const NOME_DO_COOKIE = "rockhub_sessao";

/**
 * O cabeçalho `Cookie` para repassar numa chamada de servidor, ou `null` sem
 * sessão.
 *
 * **O `fetch` do servidor não herda o cookie do pedido que está sendo
 * atendido.** É a armadilha mais cara de um Server Component que fala com a
 * API (Story 2.2, Dev Notes): sem repassar à mão, o backend responde `401`,
 * quem chama trata como indisponibilidade, e o sintoma aponta para o lugar
 * errado — a tela parece com o catálogo fora do ar quando o catálogo
 * respondeu perfeitamente.
 */
export async function cabecalhoDeSessao(): Promise<{ Cookie: string } | null> {
  const sessao = (await cookies()).get(NOME_DO_COOKIE);
  if (!sessao) return null;
  return { Cookie: `${sessao.name}=${sessao.value}` };
}
