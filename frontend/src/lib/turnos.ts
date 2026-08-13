import { API_URL, cabecalhoDeSessao } from "./servidor";

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
 * O resto do contrato não mudou: nem `capacidade`, nem `vendidos`, nem
 * `setores` — inventário é do organizador, e o contador do turno é a Story 5.6,
 * que vai contar entradas e não estoque.
 */
export type TurnoDaPortaria = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  aberto: boolean;
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
