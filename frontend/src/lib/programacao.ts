import { unstable_rethrow } from "next/navigation";

import { API_URL } from "./servidor";

/**
 * Espelha `app/schemas/evento.py::EventoNaProgramacao` — o evento como o
 * **visitante** o vê.
 *
 * **Não tem `capacidade`, `vendidos` nem `setores`, e isso não é um recorte
 * deste tipo**: é o contrato inteiro que a API devolve (UX-DR7). O que chega
 * aqui já vem sem estoque, então não existe nada para a tela deixar de
 * renderizar por disciplina — a garantia está no `response_model` do backend,
 * um lado de lá da rede. `imagem_url` também não vem: a fila de quatro colunas
 * não tem imagem, e a arte é assunto da chamada principal da Story 3.3.
 */
export type EventoNaProgramacao = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  /** `null` quando não há setor com ingresso — o evento está esgotado. */
  preco_minimo_centavos: number | null;
  esgotado: boolean;
};

/**
 * **Dois estados, e não três como no `lib/eventos.ts`.** Não há `404` nem
 * `401` possíveis nesta rota: ela responde `200 []` para banco vazio e não
 * conhece sessão nenhuma. Um terceiro estado aqui seria um ramo que nenhuma
 * resposta do backend consegue produzir.
 */
export type ResultadoDaProgramacao =
  | { estado: "ok"; itens: EventoNaProgramacao[] }
  | { estado: "indisponivel" };

/**
 * Espelha o enum `PeriodoDaProgramacao` do backend (Story 3.2).
 *
 * As janelas são **corridas a partir de agora** — 7 e 30 dias —, e não a semana
 * e o mês do calendário: é por isso que os chips da tela dizem `7 DIAS` e
 * `30 DIAS`, e não "Esta semana" e "Este mês". O motivo inteiro está no
 * docstring do enum, do lado de lá.
 */
export type PeriodoDaProgramacao = "todos" | "semana" | "mes";

/**
 * ⚠️ **A tela normaliza contra esta lista antes de chamar a API.** Valor fora
 * do enum devolve `422`, e a raiz mostraria "não foi possível carregar a
 * programação" — uma mentira sobre o backend — para quem digitou
 * `/?periodo=xyz` na barra de endereço.
 */
export const PERIODOS: readonly PeriodoDaProgramacao[] = [
  "todos",
  "semana",
  "mes",
];

export type FiltrosDaProgramacao = {
  q?: string;
  cidade?: string;
  periodo?: PeriodoDaProgramacao;
};

/**
 * A programação pública, do lado do servidor.
 *
 * **Nunca levanta**, no molde do `buscarNoCatalogo` e do `listarMeusEventos`:
 * não existe `error.tsx` neste projeto, e uma exceção não capturada num Server
 * Component derruba a página inteira. Aqui a página é a **raiz do produto** —
 * o custo de esquecer isso é a aplicação inteira mostrando erro de servidor
 * porque o backend piscou.
 */
export async function listarProgramacao(
  filtros: FiltrosDaProgramacao = {},
): Promise<ResultadoDaProgramacao> {
  try {
    // `URLSearchParams` e só ele, dos dois lados da tela: os valores chegam
    // decodificados do `searchParams` do Next, e interpolá-los direto na string
    // da URL produz `%2520` em `?cidade=São Paulo` e uma busca que não acha
    // nada. Foi o que a Story 2.4 aprendeu montando o destino do `<Link>`.
    const busca = new URLSearchParams();

    // **Omitindo o que está vazio**, e omitindo `periodo=todos`: `/eventos`
    // limpo continua sendo a chamada sem filtro nenhum. Não é cosmético — é o
    // que mantém a requisição de quem só abriu a raiz idêntica à da Story 3.1,
    // e o que faz `?q=&cidade=&periodo=todos` não virar três parâmetros de
    // ruído no log de quem for depurar.
    if (filtros.q?.trim()) {
      busca.set("q", filtros.q.trim());
    }
    if (filtros.cidade) {
      busca.set("cidade", filtros.cidade);
    }
    if (filtros.periodo && filtros.periodo !== "todos") {
      busca.set("periodo", filtros.periodo);
    }

    const consulta = busca.size > 0 ? `?${busca}` : "";

    // ⚠️ **Sem `headers`, e a ausência é intencional.** `cabecalhoDeSessao()`
    // está a um import de distância e não faria mal nenhum — é exatamente por
    // isso que ele entraria sem ninguém notar. Repassar cookie que ninguém lê
    // é acoplamento: o próximo leitor tomaria a sessão por exigência da rota,
    // e a Story 3.2 herdaria a suposição. Esta é a primeira rota pública do
    // projeto, e é aqui que a diferença entre "esqueci" e "é público" precisa
    // estar escrita.
    //
    // `cache: "no-store"` é o que mantém a raiz dinâmica. Sem ele o build da
    // Vercel renderizaria a lista uma vez e ela congelaria — o masthead já
    // torna toda rota do `(site)` dinâmica por ler a sessão, mas isso é efeito
    // colateral de outro componente e não é garantia desta tela.
    const resposta = await fetch(`${API_URL}/eventos${consulta}`, {
      cache: "no-store",
    });

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as EventoNaProgramacao[];
    return { estado: "ok", itens };
  } catch (erro) {
    // ⚠️ **Antes do `console.error`, sempre.** O `cache: "no-store"` acima é
    // uma das APIs que o Next interrompe **lançando** um erro interno
    // (`DYNAMIC_SERVER_USAGE`) para tirar a rota da renderização estática — a
    // doc da versão instalada nomeia o `fetch` sem cache junto com `cookies()`
    // e `notFound()`. Sem este `rethrow`, o `catch` engolia o sinal, o build
    // registrava "[RockHub] Programação indisponível" e a raiz corria o risco
    // de nascer estática com a frase de erro impressa dentro — que é
    // exatamente a armadilha que o `no-store` existe para evitar.
    //
    // **Este módulo é o único do `lib/` que precisa disso**, e o motivo é o
    // mesmo que o torna especial: os outros três chamam `cabecalhoDeSessao()`
    // — ou seja, `cookies()` — **fora** do `try`, e já saem da renderização
    // estática antes de chegar ao `fetch`. Aqui não há cookie nenhum, porque a
    // rota é pública, e o `fetch` é o único sinal que resta.
    unstable_rethrow(erro);

    console.error(`[RockHub] Programação indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}

/**
 * As cidades com show em cartaz — o universo dos chips `ONDE` (Story 3.2).
 *
 * **Devolve `string[]` e engole a falha**, e é a única função do `lib/` que não
 * discrimina o erro (decisão declarada na story). Sem os chips a tela continua
 * inteira e a busca continua funcionando: não há nada diferente para ela fazer,
 * e um `{ estado: "indisponivel" }` aqui criaria um ramo que a tela renderiza
 * exatamente igual ao caso feliz — ou seja, um ramo morto que alguém teria que
 * manter. `[]` já significa "não há grupo de cidade para desenhar", e é a mesma
 * coisa que o banco sem evento devolve.
 *
 * **Sem parâmetro nenhum, e isso é a decisão.** A lista de escolhas é o
 * universo, não o resultado: ela não reage ao termo nem à cidade escolhida. A
 * rota do backend nem os declara.
 *
 * Sem `cabecalhoDeSessao()` e sem `headers`, como a função acima e pelo mesmo
 * motivo escrito lá.
 */
export async function listarCidadesEmCartaz(): Promise<string[]> {
  try {
    const resposta = await fetch(`${API_URL}/eventos/cidades`, {
      cache: "no-store",
    });

    if (!resposta.ok) {
      return [];
    }

    return (await resposta.json()) as string[];
  } catch (erro) {
    // ⚠️ **Primeira linha do `catch`, igual à função acima.** O risco é
    // idêntico: o `cache: "no-store"` interrompe a renderização estática
    // **lançando** `DYNAMIC_SERVER_USAGE`, e um `catch` que o engole faz a rota
    // correr o risco de nascer estática — aqui, com a lista de chips congelada
    // no build. O comentário longo está na `listarProgramacao`; esta função tem
    // exatamente o mesmo motivo e nenhuma diferença.
    unstable_rethrow(erro);

    console.error(`[RockHub] Cidades indisponíveis em ${API_URL}:`, erro);
    return [];
  }
}
