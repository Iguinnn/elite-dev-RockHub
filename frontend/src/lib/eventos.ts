import { API_URL, cabecalhoDeSessao } from "./servidor";

/**
 * Espelha `app/schemas/evento.py::EventoResumo` — o evento como ele aparece na
 * **lista** do organizador. Enxuto de propósito: os setores e a imagem ficam
 * para o detalhe, e `capacidade_total`/`vendidos_total` já vêm somados do
 * service (AD-13), nunca contados aqui.
 */
export type MeuEventoResumo = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  publicado_em: string | null;
  capacidade_total: number;
  vendidos_total: number;
};

/** Espelha `SetorSaida` do backend (`app/schemas/evento.py`). */
export type SetorDoEvento = {
  id: string;
  nome: string;
  capacidade: number;
  vendidos: number;
  preco_centavos: number;
};

/** Espelha `PortariaSaida` do backend (`app/schemas/evento.py`). */
export type PortariaDoEvento = { id: string; nome: string; email: string };

/**
 * Espelha `EventoSaida` — o evento inteiro, como o organizador o vê.
 *
 * É o **mesmo** tipo que o `POST /organizador/eventos` devolve, e por isso o
 * `FormularioPublicacao` o importa daqui em vez de declarar o seu: os dois leem
 * o mesmo `EventoSaida`, e duas cópias divergiriam na primeira mudança do
 * schema. A importação é `import type`, que o compilador apaga — nada deste
 * módulo, que fala com `next/headers` pelo `servidor.ts`, atravessa para o
 * bundle do navegador.
 */
export type MeuEventoDetalhe = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  imagem_url: string | null;
  origem_externa_id: string | null;
  publicado_em: string | null;
  setores: SetorDoEvento[];
  portarias: PortariaDoEvento[];
};

export type ResultadoDosMeusEventos =
  | { estado: "ok"; itens: MeuEventoResumo[] }
  | { estado: "indisponivel" };

/**
 * Três estados, e não dois como nos outros módulos deste diretório.
 *
 * `nao-encontrado` existe porque a tela precisa distinguir "esse evento não é
 * seu (ou não existe)" de "a API não respondeu": o primeiro é `notFound()`, o
 * segundo é uma frase. Só o `404` separa os dois, e achatá-los faria a tela
 * mentir — um evento alheio apareceria como instabilidade do servidor.
 */
export type ResultadoDoMeuEvento =
  | { estado: "ok"; evento: MeuEventoDetalhe }
  | { estado: "nao-encontrado" }
  | { estado: "indisponivel" };

/**
 * Os eventos publicados por quem está na sessão, do lado do servidor.
 *
 * **Nunca levanta**, no molde exato do `buscarNoCatalogo` e do
 * `listarPortarias`: não existe `error.tsx` neste projeto, e uma exceção não
 * capturada num Server Component derruba a página inteira. A falha vira um
 * estado discriminado, e a tela diz numa frase que a lista não pôde ser
 * carregada.
 */
export async function listarMeusEventos(): Promise<ResultadoDosMeusEventos> {
  // ⚠️ O `fetch` do servidor **não herda** o cookie do pedido que está sendo
  // atendido. Sem repassá-lo à mão, o backend responde `401`, isto vira
  // "indisponível", e o sintoma aponta para o lugar errado.
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(`${API_URL}/organizador/eventos`, {
      headers: cabecalho ?? undefined,
      cache: "no-store",
    });

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as MeuEventoResumo[];
    return { estado: "ok", itens };
  } catch (erro) {
    console.error(`[RockHub] Lista de eventos indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}

/**
 * Um evento do organizador da sessão, com setores e escala.
 *
 * O `id` vai cru na URL: ele é um UUID vindo de um parâmetro de rota, e um
 * valor que não seja UUID recebe `422` do backend — que cai no mesmo
 * `nao-encontrado`, porque para quem lê a tela não há diferença entre "esse
 * endereço está errado" e "esse evento não é seu".
 */
export async function obterMeuEvento(id: string): Promise<ResultadoDoMeuEvento> {
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(
      `${API_URL}/organizador/eventos/${encodeURIComponent(id)}`,
      {
        headers: cabecalho ?? undefined,
        cache: "no-store",
      },
    );

    // ⚠️ **Antes** do `!resposta.ok` genérico. Se os dois casos caíssem no
    // mesmo ramo, o evento de outro organizador viraria "a API não respondeu",
    // e a tela mostraria uma falha de servidor para o que é, na verdade, um
    // endereço que não existe para quem está lendo.
    if (resposta.status === 404 || resposta.status === 422) {
      return { estado: "nao-encontrado" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const evento = (await resposta.json()) as MeuEventoDetalhe;
    return { estado: "ok", evento };
  } catch (erro) {
    console.error(`[RockHub] Evento indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
