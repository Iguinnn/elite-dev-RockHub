import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * "Meus ingressos" (Story 4.1) — os tipos e a leitura pelo servidor.
 *
 * Molde literal do `lib/eventos.ts`: mesma fronteira física (`next/headers`
 * via `servidor.ts`, nunca atravessa para o bundle do navegador), mesma
 * disciplina de nunca levantar.
 */

/**
 * Espelha `app/schemas/ingresso.py::IngressoNaLista`.
 *
 * **Sem `codigo` nem `titular_nome`**: nenhum dos dois é desenhado nesta
 * tela — o primeiro é o canhoto (`/ingressos/{id}`, Story 4.2), o segundo não
 * tem leitor aqui. `usado_em` é `string | null` e é ele que decide o bloco: a
 * API devolve a lista chapada, e quem corta em *Ativos* e *Utilizados* é esta
 * tela, no mesmo molde do `Meus eventos` da 2.6.
 */
export type IngressoResumo = {
  id: string;
  evento_id: string;
  evento_nome: string;
  evento_data_hora: string;
  evento_local: string;
  setor_nome: string;
  usado_em: string | null;
};

export type ResultadoDosIngressos =
  | { estado: "ok"; itens: IngressoResumo[] }
  | { estado: "indisponivel" };

/**
 * Os ingressos de todas as compras pagas de quem está na sessão.
 *
 * **Nunca levanta**, como todas as funções de leitura do `lib/`: não existe
 * `error.tsx` neste projeto, e uma exceção não capturada num Server Component
 * derruba a página inteira.
 */
export async function listarIngressos(): Promise<ResultadoDosIngressos> {
  // ⚠️ O `fetch` do servidor **não herda** o cookie do pedido que está sendo
  // atendido. Sem repassá-lo à mão, o backend responde `401`, isto vira
  // "indisponível", e o sintoma aponta para o lugar errado.
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(`${API_URL}/ingressos`, {
      headers: cabecalho ?? undefined,
      cache: "no-store",
    });

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as IngressoResumo[];
    return { estado: "ok", itens };
  } catch (erro) {
    console.error(`[RockHub] Lista de ingressos indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
