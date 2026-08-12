import { unstable_rethrow } from "next/navigation";

import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * A reserva do lado do frontend (Story 3.6) — os tipos e a leitura pelo servidor.
 *
 * ⚠️ **A criação da reserva não mora aqui.** Ela sai de um Client Component (o
 * `EscolhaDeIngressos`) e vai por `chamarApi`, que é o cliente do navegador: o
 * `POST` acontece no clique de quem está lendo a página, não na renderização
 * dela. Este módulo importa `next/headers` pelo `servidor.ts` e nunca atravessa
 * para o bundle — por isso a função que falta não pode existir aqui. Mesma
 * fronteira física descrita no `lib/api.ts` e no `lib/sessao.ts`.
 */

/**
 * Espelha `app/schemas/reserva.py::ItemDaReservaSaida`.
 *
 * `preco_unitario_centavos` é o preço **congelado** no ato da reserva, e não uma
 * cópia viva de `setor.preco_centavos`: o organizador pode mudar a tabela de
 * preços amanhã, e a reserva continua dizendo quanto custou.
 */
export type ItemDaReserva = {
  setor_id: string;
  setor_nome: string;
  quantidade: number;
  preco_unitario_centavos: number;
};

/**
 * Espelha `app/schemas/reserva.py::ReservaSaida`.
 *
 * ⚠️ **Não há estoque aqui, e isso não é um recorte deste tipo**: é o contrato
 * inteiro que a API devolve (UX-DR7, AD-13). `capacidade`, `vendidos` e
 * disponibilidade de setor não existem do lado de cá da rede, e a garantia é o
 * `response_model` do backend — um lado de lá dela. `quantidade` e os dois campos
 * de dinheiro são a **compra**, não o inventário: quantidade que a pessoa pediu
 * não é estoque; quantidade que resta é.
 *
 * `estado` é o enum fechado do backend. Só `PENDENTE` é produzível hoje e a tela
 * não ramifica por ele — os outros quatro entram porque a 3.7 e a 3.8 os
 * escrevem, e um contrato de reserva sem o estado dela esconde a coisa principal.
 *
 * `expira_em` é ISO-8601 com fuso (AD-11). É contra ele que o `Cronometro`
 * conta, e quem decide se a reserva expirou é o servidor, na Story 3.7 — o
 * cronômetro chegando a zero é informação, não veredito.
 */
/**
 * Espelha `app/schemas/reserva.py::IngressoSaida` (Story 3.9).
 *
 * `codigo` é `ID.ASSINATURA` (AD-5) — o conteúdo que vira QR. A assinatura e o
 * nonce **não** chegam separados: o código já os traz no formato que a
 * validação da portaria espera, e expor as partes convidaria a recombiná-las
 * por fora.
 */
export type IngressoDaReserva = {
  id: string;
  titular_nome: string;
  setor_nome: string;
  codigo: string;
};

export type ReservaSaida = {
  id: string;
  evento_id: string;
  evento_nome: string;
  evento_data_hora: string;
  estado: "PENDENTE" | "PAGA" | "RECUSADA" | "EXPIRADA" | "CANCELADA";
  expira_em: string;
  total_centavos: number;
  itens: ItemDaReserva[];
  /**
   * ⚠️ **Vazia até a reserva ser `PAGA`**, e é isso que a torna segura de estar
   * sempre no contrato: ingresso só nasce dentro da transação do pagamento
   * (AD-14). A tela ramifica pelo `estado`, nunca pelo tamanho desta lista.
   */
  ingressos: IngressoDaReserva[];
};

/**
 * **Três estados**, no molde literal do `obterMeuEvento` e do `obterEvento`.
 *
 * `nao-encontrado` existe porque a tela precisa distinguir "essa reserva não é
 * sua (ou não existe)" de "a API não respondeu": o primeiro é `notFound()`, o
 * segundo é uma frase. Só o `404` separa os dois, e achatá-los faria a reserva
 * de outra pessoa aparecer como instabilidade do servidor.
 */
export type ResultadoDaReserva =
  | { estado: "ok"; reserva: ReservaSaida }
  | { estado: "nao-encontrado" }
  | { estado: "indisponivel" };

/**
 * Uma reserva do cliente da sessão, do lado do servidor.
 *
 * **Nunca levanta**, como todas as funções de leitura do `lib/`: não existe
 * `error.tsx` neste projeto, e uma exceção não capturada num Server Component
 * derruba a página inteira.
 *
 * O `id` vai por `encodeURIComponent`: ele vem de um parâmetro de rota, e o que
 * não for UUID recebe `422` do backend — que cai no mesmo `nao-encontrado`,
 * porque para quem lê a tela não há diferença entre "esse endereço está errado" e
 * "essa reserva não é sua".
 */
export async function obterReserva(id: string): Promise<ResultadoDaReserva> {
  // ⚠️ **Fora do `try`, e a posição é a decisão.** É ele que chama `cookies()`, e
  // é `cookies()` que tira esta rota da renderização estática — se ele estivesse
  // dentro, o `unstable_rethrow` abaixo seria a única rede de proteção. Molde
  // literal do `obterMeuEvento`.
  //
  // O `fetch` do servidor **não herda** o cookie do pedido que está sendo
  // atendido: sem repassá-lo à mão, o backend responde `401`, isto vira
  // "indisponível", e o sintoma aponta para o lugar errado.
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(`${API_URL}/reservas/${encodeURIComponent(id)}`, {
      headers: cabecalho ?? undefined,
      cache: "no-store",
    });

    // ⚠️ **Antes** do `!resposta.ok` genérico, como no `obterEvento`. Se os dois
    // casos caíssem no mesmo ramo, a reserva de outra pessoa viraria "a API não
    // respondeu", e a tela mostraria falha de servidor para o que é, na verdade,
    // um endereço que não existe para quem está lendo.
    if (resposta.status === 404 || resposta.status === 422) {
      return { estado: "nao-encontrado" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const reserva = (await resposta.json()) as ReservaSaida;
    return { estado: "ok", reserva };
  } catch (erro) {
    // ⚠️ **Primeira linha do `catch`, como nas quatro funções do
    // `lib/programacao.ts`.** O `cache: "no-store"` é uma das APIs que o Next
    // interrompe **lançando** um erro interno (`DYNAMIC_SERVER_USAGE`), e um
    // `catch` que o engole faria a página nascer estática com a frase de erro
    // impressa dentro. O comentário longo está na `listarProgramacao`.
    unstable_rethrow(erro);

    console.error(`[RockHub] Reserva indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
