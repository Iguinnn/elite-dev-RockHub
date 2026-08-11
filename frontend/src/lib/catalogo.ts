import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * Espelha `app/schemas/catalogo.py::ItemDoCatalogo` do backend — o formato
 * já convertido da Ticketmaster, sem nenhum campo aninhado dela.
 */
export type ItemDoCatalogo = {
  id_externo: string;
  nome: string;
  atracao: string | null;
  imagem_url: string | null;
  local: string | null;
  cidade: string | null;
};

export type ResultadoDaBusca =
  | { estado: "ok"; itens: ItemDoCatalogo[] }
  | { estado: "indisponivel" }
  // A sessão morreu enquanto a tela estava aberta. Culpar a Ticketmaster por
  // isso manda a pessoa esperar por algo que nunca vai melhorar sozinho.
  | { estado: "sem-sessao" }
  // O termo passou do `max_length=120` da rota. Erro do formulário, não do
  // fornecedor — e a Discovery nem chegou a ser chamada.
  | { estado: "busca-invalida" };

/**
 * Busca no catálogo do organizador, do lado do servidor.
 *
 * **Nunca levanta.** Não existe `error.tsx` neste projeto: uma exceção não
 * capturada num Server Component derruba a página inteira, não só esta
 * seção. Por isso o `503` do backend (e qualquer outra falha) vira um estado
 * discriminado — a tela decide o texto pelo `estado`, nunca por uma exceção
 * pega no meio do caminho.
 */
export async function buscarNoCatalogo(termo: string): Promise<ResultadoDaBusca> {
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(
      // `encodeURIComponent`: sem ele, um `&` no termo (ex.: "AC/DC & Guns")
      // encerra o parâmetro `q` e vaza um segundo parâmetro que ninguém pediu.
      `${API_URL}/organizador/catalogo?q=${encodeURIComponent(termo)}`,
      {
        headers: cabecalho ?? undefined,
        cache: "no-store",
      },
    );

    // ⚠️ `401`, `403` e `422` **não** são "a Ticketmaster não respondeu".
    // Achado no code review da Epic 2: qualquer `!resposta.ok` virava
    // "indisponível", e a tela acusava a Ticketmaster por sessão expirada ou
    // por um termo de busca acima do `max_length=120` da rota — sem que a
    // Discovery tivesse sido chamada. O `lib/eventos.ts` já separava assim.
    if (resposta.status === 401 || resposta.status === 403) {
      return { estado: "sem-sessao" };
    }
    if (resposta.status === 422) {
      return { estado: "busca-invalida" };
    }
    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as ItemDoCatalogo[];
    return { estado: "ok", itens };
  } catch (erro) {
    console.error(`[RockHub] Catálogo indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
