import { chamarApi } from "./api";

/**
 * A validação de um código na porta (Story 5.2 no backend, 5.3 na tela).
 *
 * ⚠️ **Este módulo é do navegador, e por isso não fica no `lib/turnos.ts`.**
 * Aquele importa `servidor.ts`, que importa `next/headers` — e `next/headers`
 * dentro de um módulo alcançado por um componente `"use client"` quebra o build.
 * A separação é física, não estilística: o leitor é uma ilha, e validar acontece
 * a cada código digitado, sem recarregar a página.
 */

/**
 * Os quatro vereditos do FR6, espelhando o `Literal` de
 * `app/schemas/ingresso.py::ResultadoDaValidacao`.
 *
 * **São exatamente quatro, e a tela não inventa um quinto.** Código malformado,
 * código de ingresso nenhum e assinatura divergente chegam todos como
 * `INVALIDO` — a decisão é do backend, e está no docstring do service.
 */
export type Veredito = "VALIDO" | "INVALIDO" | "JA_UTILIZADO" | "EVENTO_ERRADO";

/**
 * Espelha `app/schemas/ingresso.py::ResultadoDaValidacao`.
 *
 * **Um tipo com campos opcionais, e não uma união de quatro formas.** Foi
 * decidido no contrato justamente para a tela não precisar estreitar tipo antes
 * de desenhar: os quatro casos são a mesma tela trocando de palavra.
 *
 * ⚠️ **`EVENTO_ERRADO` não diz de qual show o ingresso é** (decisão do Igor,
 * contra o protótipo). Os três campos chegam nulos nesse caso, e não há o que
 * a tela possa preencher no lugar.
 */
export type ResultadoDaValidacao = {
  resultado: Veredito;
  /** Preenchido em `VALIDO` e `JA_UTILIZADO`. É o nome da **conta** que comprou. */
  titular_nome: string | null;
  /** Só em `VALIDO` — em `JA_UTILIZADO` ninguém vai entrar, e apontar não serve. */
  setor_nome: string | null;
  /** Em `VALIDO`, esta entrada; em `JA_UTILIZADO`, a **primeira**. */
  entrada_em: string | null;
};

/**
 * Manda o código à porta e devolve o veredito.
 *
 * **Levanta `ErroDaApi`**, ao contrário das funções de leitura do `lib/`: aqui
 * quem chama é uma ilha do navegador com `try/catch` à volta, e não um Server
 * Component que não pode deixar a exceção subir. Os quatro vereditos chegam em
 * `200` — o que levanta é `401`, `403` e `422`, que são de outra natureza:
 * recusa de atendimento, não resultado de leitura.
 *
 * **O código vai cru**, com espaços, hífens e a caixa como vieram. Quem
 * normaliza é o `normalizar_codigo` do backend, e normalizar aqui também daria
 * duas regras para o mesmo valor — a que o navegador aplica e a que o servidor
 * aplica —, com o dia em que discordam já marcado.
 */
export async function validarCodigo(
  eventoId: string,
  codigo: string,
): Promise<ResultadoDaValidacao> {
  return chamarApi<ResultadoDaValidacao>(
    `/portaria/eventos/${encodeURIComponent(eventoId)}/validacoes`,
    { method: "POST", body: JSON.stringify({ codigo }) },
  );
}
