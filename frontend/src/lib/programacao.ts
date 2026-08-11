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
 * A programação pública, do lado do servidor.
 *
 * **Nunca levanta**, no molde do `buscarNoCatalogo` e do `listarMeusEventos`:
 * não existe `error.tsx` neste projeto, e uma exceção não capturada num Server
 * Component derruba a página inteira. Aqui a página é a **raiz do produto** —
 * o custo de esquecer isso é a aplicação inteira mostrando erro de servidor
 * porque o backend piscou.
 */
export async function listarProgramacao(): Promise<ResultadoDaProgramacao> {
  try {
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
    const resposta = await fetch(`${API_URL}/eventos`, { cache: "no-store" });

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
