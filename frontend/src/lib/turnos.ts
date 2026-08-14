import { unstable_rethrow } from "next/navigation";

import { API_URL, cabecalhoDeSessao } from "./servidor";
import type { RecusasDoTurno } from "./validacao";

/**
 * Espelha `app/schemas/evento.py::TurnoDaPortaria` — um evento em que a conta
 * da sessão foi escalada na porta (Story 5.1).
 *
 * ⚠️ **`aberto` entrou na Story 5.2, e ele reverte o que estava escrito aqui.**
 * Até a 5.1 o portão das duas horas era regra da página, comparada com o relógio
 * de quem lê — e a 5.2 passou a recusar validação fora da janela com `403
 * EVENTO_NAO_ABERTO`. Com a regra valendo dos dois lados, duas constantes de
 * duas horas em duas camadas discordariam algum dia, e esta tela mostraria a
 * porta aberta enquanto a API recusa. A janela agora tem um dono só:
 * `ABERTURA_DOS_PORTOES`, em `services/evento.py`.
 *
 * ⚠️ **E ele virou `estado` em 14/08/2026**, quando o portão ganhou o outro lado
 * — ver o `EstadoDoTurno` logo abaixo. `data_hora_fim` **não** entra no contrato:
 * a tela lê o estado, que já é a resposta, e devolver o instante deixaria a
 * portaria recalculando a mesma regra do outro lado, que é exatamente o que a 5.2
 * desfez.
 *
 * ⚠️ **`entradas` entrou na Story 5.6, e ele é o contador que este docstring
 * anunciava** — *"o contador do turno é a Story 5.6, que vai contar entradas e
 * não estoque"*. É `COUNT` sobre `ingresso.usado_em IS NOT NULL`, de todas as
 * portas do evento. O resto do contrato continua fora: nem `capacidade`, nem
 * `vendidos`, nem `setores` — inventário é do organizador, e vendidos não é
 * entrou.
 */
export type TurnoDaPortaria = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  estado: EstadoDoTurno;
  entradas: number;
};

/**
 * Espelha `app/schemas/evento.py::EstadoDoTurno` — onde este turno está na noite
 * (techspec `docs/techspec-fim-do-evento.md`).
 *
 * ⚠️ **Ele substituiu o `aberto: boolean`, e não entrou ao lado dele.** Com
 * `evento.data_hora_fim`, a noite passou a ter três partes em vez de duas: o
 * booleano não tinha onde pôr o show que acabou, e por isso o turno de um evento
 * da semana passada continuava clicável e validável. Um `encerrado: boolean` ao
 * lado do que existia permitiria quatro combinações para três estados, e uma
 * delas é impossível — a tela precisaria de um ramo para um caso que o backend
 * jamais manda, ou o esqueceria.
 *
 * União de literais, e não `string`: é ela que faz o `tsc` cobrar o terceiro ramo
 * de quem desenhar o cartão.
 */
export type EstadoDoTurno = "NAO_COMECOU" | "ABERTO" | "ENCERRADO";

/**
 * Espelha `app/schemas/evento.py::TurnoDoLeitor` — o turno **do leitor**, com as
 * três recusas (Story 5.6).
 *
 * ⚠️ **Só `GET /portaria/eventos/{id}` responde este tipo.** A lista devolve o
 * `TurnoDaPortaria` acima, sem as recusas, e a assimetria é do contrato: o cartão
 * de `/portaria` desenha um número só — onde está o movimento —, e três recusas
 * por item numa tela de escolha seriam ruído operacional. Campo sem consumidor
 * não viaja.
 */
export type TurnoDoLeitor = TurnoDaPortaria & {
  recusas: RecusasDoTurno;
};

export type ResultadoDosTurnos =
  | { estado: "ok"; itens: TurnoDaPortaria[] }
  | { estado: "indisponivel" }
  // Mesma separação do `lib/portarias.ts` e do `lib/catalogo.ts`, pelo mesmo
  // motivo: sessão expirada não é indisponibilidade, e "tente de novo em
  // instantes" nunca se cumpre. Aqui a distinção pesa mais do que em qualquer
  // outra tela — quem está na porta com o turno começando precisa saber se o
  // conserto é esperar ou entrar de novo.
  | { estado: "sem-sessao" };

/**
 * Os eventos em que a conta da sessão foi escalada, do lado do servidor.
 *
 * **Nunca levanta**, no molde exato do `listarPortarias` e do
 * `listarMeusEventos`: não existe `error.tsx` neste projeto, e uma exceção não
 * capturada num Server Component derruba a página inteira. A falha vira um
 * estado discriminado, e a tela diz numa frase que a lista não pôde ser
 * carregada.
 *
 * **A lista chega sem corte de tempo, e é assim de propósito**: evento que já
 * começou continua nela. A portaria trabalha exatamente do outro lado do corte
 * que as rotas públicas fazem — o motivo inteiro está no
 * `services/evento.py::listar_escalados`.
 */
export async function listarTurnos(): Promise<ResultadoDosTurnos> {
  // ⚠️ O `fetch` do servidor **não herda** o cookie do pedido que está sendo
  // atendido. Sem repassá-lo à mão, o backend responde `401`, isto vira
  // "sem sessão", e o sintoma aponta para o lugar errado — a tela rebateria
  // para o login de quem tem sessão perfeitamente válida.
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(`${API_URL}/portaria/eventos`, {
      headers: cabecalho ?? undefined,
      cache: "no-store",
    });

    if (resposta.status === 401 || resposta.status === 403) {
      return { estado: "sem-sessao" };
    }
    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const itens = (await resposta.json()) as TurnoDaPortaria[];
    return { estado: "ok", itens };
  } catch (erro) {
    console.error(`[RockHub] Lista de turnos indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}

/**
 * Quatro estados, um a mais que os do `obterIngresso` — e o novo é `sem-turno`.
 *
 * Ele existe porque a recusa desta rota **não** é "não encontrado": a API
 * responde `403` para quem não foi escalado no evento e para quem chegou antes
 * de a porta abrir, e a tela precisa mandar essa pessoa de volta a `/portaria`,
 * onde a lista dela está. Um `notFound()` diria que o show não existe, o que é
 * falso e manda a portaria procurar o defeito no lugar errado.
 */
export type ResultadoDoTurno =
  | { estado: "ok"; turno: TurnoDoLeitor }
  | { estado: "sem-turno" }
  | { estado: "sem-sessao" }
  | { estado: "indisponivel" };

/**
 * O turno de um evento só — o cabeçalho da tela do leitor (Story 5.3).
 *
 * **Não se busca a lista inteira para achar o item pelo id**, e não se usa
 * `GET /eventos/{id}`: aquela é pública e corta em `data_hora >= agora`, ou
 * seja, responde `404` justamente durante o show. O motivo inteiro está no
 * docstring da rota, em `app/api/portaria.py`.
 *
 * ⚠️ **Todo `403` cai em `sem-turno`, e os três códigos possíveis não são
 * separados.** `SEM_ESCALA_NO_EVENTO` e `EVENTO_NAO_ABERTO` são o mesmo fato
 * para quem lê — este turno não é seu, agora —, e `SEM_PERMISSAO` (papel
 * errado) não chega aqui: a página já conferiu o papel antes de chamar, e quem
 * cair em `/portaria` pelo redirect encontra a guarda de lá. Distinguir os três
 * daria três frases para uma tela que não chega a ser desenhada.
 *
 * **Nunca levanta**, como todas as funções de leitura do `lib/`.
 */
export async function obterTurno(id: string): Promise<ResultadoDoTurno> {
  const cabecalho = await cabecalhoDeSessao();

  try {
    const resposta = await fetch(
      `${API_URL}/portaria/eventos/${encodeURIComponent(id)}`,
      { headers: cabecalho ?? undefined, cache: "no-store" },
    );

    // ⚠️ **Os dois status antes do `!resposta.ok` genérico**, como no
    // `obterIngresso`. Juntos no mesmo ramo, "você não está escalado" viraria
    // "a API não respondeu" e a tela pediria para tentar de novo em instantes —
    // o que nunca daria certo.
    if (resposta.status === 401) {
      return { estado: "sem-sessao" };
    }
    // O `422` entra aqui, e não num estado próprio: um `id` que não é UUID veio
    // da barra de endereço, e para quem lê é a mesma coisa que um turno que não
    // é seu.
    if (resposta.status === 403 || resposta.status === 422) {
      return { estado: "sem-turno" };
    }

    if (!resposta.ok) {
      return { estado: "indisponivel" };
    }

    const turno = (await resposta.json()) as TurnoDoLeitor;
    return { estado: "ok", turno };
  } catch (erro) {
    unstable_rethrow(erro);

    console.error(`[RockHub] Turno indisponível em ${API_URL}:`, erro);
    return { estado: "indisponivel" };
  }
}
