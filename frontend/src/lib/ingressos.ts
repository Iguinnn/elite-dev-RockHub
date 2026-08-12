import { unstable_rethrow } from "next/navigation";

import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * "Meus ingressos" e o canhoto com o QR (Stories 4.1 e 4.2) — os tipos e a
 * leitura pelo servidor.
 *
 * Molde literal do `lib/eventos.ts` para a lista e do `lib/reservas.ts` para
 * o detalhe: mesma fronteira física (`next/headers` via `servidor.ts`, nunca
 * atravessa para o bundle do navegador), mesma disciplina de nunca levantar.
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

/**
 * Espelha `app/schemas/ingresso.py::IngressoDetalhe` — o canhoto cheio.
 *
 * **`codigo` só existe aqui**, entre os dois tipos deste módulo: é o que vira
 * QR, e a lista (`IngressoResumo`) não o carrega de propósito (techspec da
 * 4.1). `evento_cidade` também é exclusivo daqui — a ficha do canhoto tem
 * espaço para "casa e cidade" por extenso, a fila da lista não.
 */
export type IngressoDetalhe = {
  id: string;
  evento_nome: string;
  evento_data_hora: string;
  evento_local: string;
  evento_cidade: string | null;
  setor_nome: string;
  titular_nome: string;
  codigo: string;
  usado_em: string | null;
};

/**
 * Três estados, no molde do `obterReserva` e do `obterMeuEvento`.
 *
 * `nao-encontrado` existe porque a tela precisa distinguir "esse ingresso não
 * é seu (ou não existe)" de "a API não respondeu": o primeiro é
 * `notFound()`, o segundo é uma frase.
 */
export type ResultadoDoIngresso =
  | { estado: "ok"; ingresso: IngressoDetalhe }
  | { estado: "nao-encontrado" }
  | { estado: "indisponivel" };

/**
 * O canhoto cheio de um ingresso de quem está na sessão, do lado do servidor.
 *
 * O `id` vai por `encodeURIComponent`, como em `obterReserva`: ele vem de um
 * parâmetro de rota, e o que não for UUID recebe `422` do backend — que cai
 * no mesmo `nao-encontrado`, porque para quem lê a tela não há diferença
 * entre "esse endereço está errado" e "esse ingresso não é seu".
 */
export async function obterIngresso(id: string): Promise<ResultadoDoIngresso> {
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(
      `${API_URL}/ingressos/${encodeURIComponent(id)}`,
      {
        headers: cabecalho ?? undefined,
        cache: "no-store",
      },
    );

    // ⚠️ **Antes** do `!resposta.ok` genérico, como no `obterReserva`. Se os
    // dois casos caíssem no mesmo ramo, o ingresso de outra pessoa viraria "a
    // API não respondeu".
    if (resposta.status === 404 || resposta.status === 422) {
      return { estado: "nao-encontrado" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const ingresso = (await resposta.json()) as IngressoDetalhe;
    return { estado: "ok", ingresso };
  } catch (erro) {
    unstable_rethrow(erro);

    console.error(`[RockHub] Ingresso indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
