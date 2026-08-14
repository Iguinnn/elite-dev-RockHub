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
 * Espelha `app/schemas/evento.py::EventoEmDestaque` — o próximo show, como a
 * **chamada principal** da raiz o mostra (Story 3.3).
 *
 * **Não é o `EventoNaProgramacao` com dois campos a mais.** São dois contratos
 * independentes, e é isso que mantém a fila enxuta: `imagem_url` e `setores`
 * existem aqui porque a capa os desenha, e ela mesma decide o que mostrar deles.
 * O motivo inteiro está no docstring do schema, do lado de lá.
 *
 * `setores` é uma lista de **nomes**, e nunca de objetos: nome de setor não é
 * estoque, contagem é. Nenhum campo daqui carrega `capacidade` ou `vendidos`
 * (UX-DR7) — e a garantia é o `response_model` do backend, não este tipo.
 */
export type EventoEmDestaque = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  /** `null` quando o evento não tem arte — a coluna é anulável desde a 2.3. */
  imagem_url: string | null;
  /** Só os nomes, em ordem alfabética. Todos, inclusive os esgotados. */
  setores: string[];
  /** `null` quando não há setor com ingresso — o evento está esgotado. */
  preco_minimo_centavos: number | null;
  esgotado: boolean;
};

/**
 * Espelha o enum `DisponibilidadeDoSetor` do backend (Story 3.4).
 *
 * **Três palavras, e nenhum número.** O limiar de `ULTIMOS` — 20% ou menos da
 * capacidade — é calculado do lado de lá, de `capacidade` e `vendidos`, e é
 * **só a palavra** que atravessa a rede (AD-13, UX-DR7). A tela escolhe a cor da
 * barra a partir dela; ela não tem como inventar um quarto estado porque não é
 * ela quem decide qual é o estado.
 */
export type DisponibilidadeDoSetor = "DISPONIVEL" | "ULTIMOS" | "ESGOTADO";

/**
 * Espelha `app/schemas/evento.py::SetorPublico` — um setor como **quem vai
 * comprar** o vê (Story 3.4).
 *
 * ⚠️ **Não tem `capacidade` nem `vendidos`, e isso não é um recorte deste tipo**:
 * é o contrato inteiro que a API devolve (UX-DR7). Não existe nada aqui para a
 * tela deixar de renderizar por disciplina — o que chega já vem sem contagem, e a
 * garantia é o `response_model` do backend, um lado de lá da rede. É a rota
 * pública que chega mais perto do estoque, e é justamente por isso que ela não o
 * carrega.
 *
 * `preco_centavos` **entra**, e é a primeira vez em rota de cliente: preço não é
 * contagem, e ninguém escolhe entre Pista e Camarote sem saber quanto custa cada
 * um. `proporcao_vendida` é a largura da barra, entre `0` e `1` — proporção, não
 * contagem, e não há caminho de volta daqui para os dois números que a
 * produziram.
 */
export type SetorPublico = {
  id: string;
  nome: string;
  preco_centavos: number;
  disponibilidade: DisponibilidadeDoSetor;
  /** `0`–`1`, duas casas. A largura do medidor, e nada mais. */
  proporcao_vendida: number;
};

/**
 * Espelha `app/schemas/evento.py::EventoPublico` — o evento com seus setores, na
 * tela onde a pessoa escolhe a quantidade (Story 3.4).
 *
 * **Não é o `EventoEmDestaque` com os setores completos.** São contratos
 * independentes, como os outros dois deste módulo: a capa quer três nomes para a
 * ficha, esta tela quer preço e estado de cada setor. O motivo inteiro está no
 * docstring do schema, do lado de lá.
 *
 * `maximo_por_compra` vem **do contrato** e não é constante daqui: a Story 3.6 vai
 * cobrar o mesmo teto do lado do servidor, e com o número em dois lugares o dia
 * em que a regra mudar é o dia em que o stepper e a rota de reserva passam a
 * discordar — e quem descobre isso é a pessoa que escolheu 8 ingressos e recebeu
 * uma recusa. Ele é fixo por compra, e **não** o que resta em estoque: um teto que
 * acompanhasse o estoque diria "restam 2" pelo devtools.
 */
export type EventoPublico = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  /** `null` quando o evento não tem arte — a coluna é anulável desde a 2.3. */
  imagem_url: string | null;
  maximo_por_compra: number;
  /** Todos, inclusive os esgotados, em ordem alfabética. */
  setores: SetorPublico[];
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
 * **Três estados, ao contrário das outras funções deste módulo** — e o molde é o
 * `ResultadoDoMeuEvento` do `lib/eventos.ts` (Story 3.4).
 *
 * `nao-encontrado` existe porque a tela precisa distinguir "esse show não está em
 * cartaz" de "a API não respondeu": o primeiro é `notFound()`, o segundo é uma
 * frase. Só o `404` separa os dois, e achatá-los faria um show fora de cartaz
 * virar instabilidade de servidor — ou, pior no outro sentido, faria quem
 * tropeçou numa API fora do ar receber uma 404 dizendo que o show não existe.
 *
 * ⚠️ **Aqui a distinção vale mais do que na tela do organizador.** Esta é a
 * primeira rota dinâmica **pública** do frontend: quem chega pelo endereço nunca
 * fez login, não tem contexto nenhum e não sabe distinguir as duas coisas por
 * conta própria. A frase é a única informação que ele recebe.
 */
export type ResultadoDoEvento =
  | { estado: "ok"; evento: EventoPublico }
  | { estado: "nao-encontrado" }
  | { estado: "indisponivel" };

/**
 * Espelha o enum `PeriodoDaProgramacao` do backend (Story 3.2).
 *
 * As janelas são **corridas a partir de agora** — 7 e 30 dias —, e não a semana
 * e o mês do calendário: é por isso que os chips da tela dizem `PRÓXIMOS 7 DIAS`
 * e `PRÓXIMOS 30 DIAS`, e não "Esta semana" e "Este mês". A palavra `PRÓXIMOS` é
 * quem diz que a janela é um intervalo e não um prazo — sem ela, `7 DIAS` se lê
 * como "daqui a 7 dias". O motivo inteiro está no docstring do enum, do lado de
 * lá.
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

/**
 * O próximo show da programação — o que a chamada principal desenha (Story 3.3).
 *
 * **Devolve `null` e engole a falha**, no mesmo argumento da
 * `listarCidadesEmCartaz`: sem a capa a tela continua inteira, a programação
 * continua listada e a busca continua funcionando. Não há nada diferente para
 * ela fazer, e um `{ estado: "indisponivel" }` aqui criaria um ramo que a tela
 * renderiza **exatamente igual** ao caso feliz — um ramo morto que alguém teria
 * que manter. A capa não ganha frase de erro nem espaço reservado: ela
 * simplesmente não aparece.
 *
 * ⚠️ **`null` também é a resposta certa do backend, e isso não é falha.** Banco
 * sem show em cartaz responde `200` com corpo `null` (nunca `404`), e
 * `resposta.json()` devolve `null` legitimamente. Não pode haver nenhum
 * `if (!dados) return { estado: "indisponivel" }` aqui: ele transformaria "não
 * há show em cartaz" em "não foi possível carregar" — a mesma classe de mentira
 * que a normalização do período evitou na Story 3.2. O tipo de retorno já cobre
 * os dois casos com o mesmo valor porque a tela faz a mesma coisa nos dois.
 *
 * **Sem parâmetro nenhum**: a rota não os declara, e a decisão é essa — a capa é
 * *o próximo show*, não o resultado da busca. Com filtro ativo a tela nem chama
 * esta função (`page.tsx`), para não pagar uma ida à rede por um resultado que
 * ela vai jogar fora.
 *
 * Sem `cabecalhoDeSessao()` e sem `headers`, como as duas funções acima e pelo
 * motivo escrito na primeira delas.
 */
export async function obterDestaque(): Promise<EventoEmDestaque | null> {
  try {
    const resposta = await fetch(`${API_URL}/eventos/destaque`, {
      cache: "no-store",
    });

    if (!resposta.ok) {
      return null;
    }

    return (await resposta.json()) as EventoEmDestaque | null;
  } catch (erro) {
    // ⚠️ **Primeira linha do `catch`, igual às duas funções acima.** O risco é
    // idêntico e é o mesmo `cache: "no-store"`: ele interrompe a renderização
    // estática **lançando** `DYNAMIC_SERVER_USAGE`, e um `catch` que o engole
    // faria a raiz correr o risco de nascer estática — aqui, com a capa
    // congelada no build ou ausente para sempre. O comentário longo está na
    // `listarProgramacao`; esta função tem o mesmo motivo e nenhuma diferença.
    unstable_rethrow(erro);

    console.error(`[RockHub] Destaque indisponível em ${API_URL}:`, erro);
    return null;
  }
}

/**
 * Um evento em cartaz com seus setores — a página de `/eventos/{id}` (Story 3.4).
 *
 * **Discrimina três estados**, ao contrário das duas funções acima, e o molde é o
 * `obterMeuEvento` do `lib/eventos.ts`. A diferença com as outras daqui é que esta
 * tela **é** o evento: sem ele não sobra página, então "não está em cartaz" e "a
 * API caiu" levam a lugares diferentes — a 404 do projeto e uma frase.
 *
 * ⚠️ **Sem `cabecalhoDeSessao()` e sem `headers`, e a ausência é intencional** —
 * mesmo motivo escrito na `listarProgramacao`: a rota é pública, e repassar cookie
 * que ninguém lê faria o próximo leitor tomar a sessão por exigência da rota.
 *
 * O `id` vai por `encodeURIComponent`: ele vem de um parâmetro de rota, e o que
 * não for UUID recebe `422` do backend — que cai no mesmo `nao-encontrado`.
 */
export async function obterEvento(id: string): Promise<ResultadoDoEvento> {
  try {
    const resposta = await fetch(`${API_URL}/eventos/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });

    // ⚠️ **Antes** do `!resposta.ok` genérico, exatamente como no
    // `obterMeuEvento`. Se os dois casos caíssem no mesmo ramo, o show fora de
    // cartaz viraria "a API não respondeu", e a tela mostraria uma falha de
    // servidor para o que é, na verdade, um endereço que não existe para quem
    // está lendo. O `422` entra junto: para quem lê, "esse endereço está errado"
    // e "esse show não está em cartaz" são a mesma coisa.
    if (resposta.status === 404 || resposta.status === 422) {
      return { estado: "nao-encontrado" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const evento = (await resposta.json()) as EventoPublico;
    return { estado: "ok", evento };
  } catch (erro) {
    // ⚠️ **Primeira linha do `catch`, igual às três funções acima.** O risco é o
    // mesmo `cache: "no-store"`: ele interrompe a renderização estática
    // **lançando** `DYNAMIC_SERVER_USAGE`, e um `catch` que o engole faria a
    // página do evento nascer estática com a frase de erro impressa dentro. O
    // comentário longo está na `listarProgramacao`.
    unstable_rethrow(erro);

    console.error(`[RockHub] Evento indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
