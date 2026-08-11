import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * Espelha `app/schemas/evento.py::PortariaSaida` do backend — uma conta que o
 * organizador pode escalar na porta do evento. Sem `papel`: aqui ele seria
 * sempre `PORTARIA`.
 */
export type PortariaDisponivel = {
  id: string;
  nome: string;
  email: string;
};

export type ResultadoDasPortarias =
  | { estado: "ok"; itens: PortariaDisponivel[] }
  | { estado: "indisponivel" };

/**
 * As contas de portaria disponíveis para escalar, do lado do servidor.
 *
 * **Nunca levanta**, pelo mesmo motivo do `buscarNoCatalogo`: não existe
 * `error.tsx` neste projeto, e uma exceção não capturada num Server Component
 * derruba a página inteira — aqui, o formulário de publicação junto. A falha
 * vira um estado discriminado, e o passo 3 diz que não há quem escalar em vez
 * de sumir.
 */
export async function listarPortarias(): Promise<ResultadoDasPortarias> {
  // ⚠️ O `fetch` do servidor **não herda** o cookie do pedido que está sendo
  // atendido. Sem repassá-lo à mão, o backend responde `401`, isto vira
  // "indisponível", e o sintoma aponta para o lugar errado.
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(`${API_URL}/organizador/portarias`, {
      headers: cabecalho ?? undefined,
      cache: "no-store",
    });

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as PortariaDisponivel[];
    return { estado: "ok", itens };
  } catch (erro) {
    console.error(`[RockHub] Lista de portarias indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
