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
  situacao: SituacaoDoIngresso;
};

/**
 * Espelha `app/schemas/ingresso.py::SituacaoDoIngresso` — o balde de cada
 * ingresso (techspec `docs/techspec-fim-do-evento.md`).
 *
 * ⚠️ **O nome do campo é `situacao`, e nunca `estado`.** Este módulo já usa
 * `estado` como discriminante do **resultado da chamada** (`{estado: "ok"} |
 * {estado: "indisponivel"}`), e um `item.estado` ao lado de um `resultado.estado`
 * na mesma tela é a confusão pronta — com o agravante de que o `tsc` não acusa
 * nada, porque os dois existem e os dois são strings.
 *
 * ⚠️ **`usado_em` continua no tipo ao lado dele, e não é redundância.**
 * `situacao` é o balde que a tela agrupa; `usado_em` é a hora que ela imprime em
 * *"Entrou às 21h14"*. O que a techspec desfaz é a tela **derivar** a situação de
 * `usado_em` — aquela comparação não sabia quando o evento acabou, e por isso um
 * ingresso nunca usado de um show da semana passada saía *Ativo* para sempre.
 *
 * União de literais, e não `string`: são os três valores do enum do backend, e é
 * ela que faz o `tsc` cobrar o terceiro bloco quando alguém escrever um `switch`.
 */
export type SituacaoDoIngresso = "ATIVO" | "UTILIZADO" | "EXPIRADO";

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
 *
 * ⚠️ **Este é o tipo das três rotas do ingresso, e a terceira é pública**
 * (`GET /ingressos/compartilhados/{token}`, Story 4.3). Tudo que está aqui
 * atravessa também para quem abriu um link recebido por WhatsApp, e não só
 * para o dono — é de propósito: o canhoto compartilhado é **o mesmo** canhoto,
 * `titular_nome` e `usado_em` inclusive.
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
  /**
   * O mesmo balde da lista, e aqui ele atravessa também para quem abriu o link
   * compartilhado — de propósito. Um canhoto que dissesse "ativo" sobre um show
   * que já acabou mandaria para a fila da porta alguém que não entra mais, e quem
   * recebeu o link por WhatsApp é justamente quem não tem outra forma de saber.
   */
  situacao: SituacaoDoIngresso;
  /**
   * `null` é "nunca compartilhado" **ou** "revogado" — os dois são o mesmo
   * estado, e a ilha desenha *Compartilhar* nos dois casos. Ele **não** é o
   * `codigo`: aquele vale na porta (AD-5), este só endereça a visualização
   * (AD-8). A URL do link é montada pelo navegador, não pela API.
   */
  share_token: string | null;
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

/**
 * O canhoto que um link compartilhado abre — **sem sessão nenhuma** (4.3).
 *
 * Molde exato do `obterIngresso` acima, com os mesmos três estados e a mesma
 * disciplina de nunca levantar. Duas diferenças, e as duas são a decisão:
 *
 * ⚠️ **Sem `cabecalhoDeSessao()` e sem `headers`, e a ausência é intencional**
 * — mesmo motivo escrito na `listarProgramacao` do `lib/programacao.ts`: a
 * rota é pública, e repassar cookie que ninguém lê faria o próximo leitor
 * tomar a sessão por exigência dela. Quem abre este link pode nunca ter tido
 * conta, e a tela precisa funcionar exatamente igual para os dois.
 *
 * **O `token` vai por `encodeURIComponent`**, como o `id` das funções acima:
 * ele vem da barra de endereço e pode ser qualquer coisa que alguém digitou. O
 * backend responde `404` para o que não bate com a coluna — inclusive para
 * token revogado, que é indistinguível de token que nunca existiu.
 */
export async function obterIngressoCompartilhado(
  token: string,
): Promise<ResultadoDoIngresso> {
  try {
    const resposta = await fetch(
      `${API_URL}/ingressos/compartilhados/${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );

    // ⚠️ **Antes** do `!resposta.ok` genérico, como nas irmãs. Aqui só o `404`
    // é possível — o token não é UUID e não há `422` de formato —, mas o `422`
    // fica junto pelo mesmo motivo de sempre: para quem lê, "esse endereço
    // está errado" e "esse link não vale mais" são a mesma coisa.
    if (resposta.status === 404 || resposta.status === 422) {
      return { estado: "nao-encontrado" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const ingresso = (await resposta.json()) as IngressoDetalhe;
    return { estado: "ok", ingresso };
  } catch (erro) {
    // ⚠️ **Primeira linha do `catch`, e aqui ela pesa mais que nas irmãs
    // acima.** Elas chamam `cabecalhoDeSessao()` — ou seja, `cookies()` — fora
    // do `try`, e já saem da renderização estática antes de chegar ao `fetch`.
    // Esta não chama cookie nenhum, porque a rota é pública: o `cache:
    // "no-store"` é o único sinal que tira a página da renderização estática, e
    // ele chega **lançando** `DYNAMIC_SERVER_USAGE`. Sem o rethrow, o `catch`
    // engoliria o sinal e a página do link correria o risco de nascer estática
    // com a frase de erro impressa dentro. É a mesma armadilha do
    // `lib/programacao.ts`, onde o comentário longo mora.
    unstable_rethrow(erro);

    console.error(
      `[RockHub] Ingresso compartilhado indisponível em ${API_URL}:`,
      erro,
    );
    return { estado: "indisponivel" };
  }
}
