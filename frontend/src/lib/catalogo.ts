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
  | { estado: "indisponivel" };

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
