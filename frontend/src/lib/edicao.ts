import { chamarApi } from "./api";
import type { MeuEventoDetalhe } from "./eventos";

/**
 * A edição de um evento que ainda não vendeu — `PUT /organizador/eventos/{id}`
 * (techspec `docs/techspec-editar-evento.md`, commit 2).
 *
 * ⚠️ **A spec pedia esta função dentro do `lib/eventos.ts`, e ela não cabe
 * lá.** Aquele módulo importa `servidor.ts`, que importa `next/headers`, e
 * `next/headers` alcançado por um componente `"use client"` quebra o build —
 * não é preferência de organização, é limite de execução, e o `lib/api.ts`, o
 * `lib/reservas.ts` e o `lib/sessao.ts` já o documentam cada um do seu lado. O
 * `lib/reservas.ts` chega a dizer, com todas as letras, que a função de escrita
 * que falta nele **não pode existir ali**.
 *
 * O precedente que este arquivo segue é o `lib/validacao.ts`: escrita que sai do
 * navegador, num módulo próprio, nomeado pela ação. A alternativa era chamar o
 * `chamarApi` inline no formulário, como o `FormularioPublicacao` faz — descartei
 * porque o corpo do `PUT` tem forma própria (o `id` opcional de cada setor é o
 * que separa alterar de criar), e um tipo com nome é onde essa forma fica escrita
 * uma vez só.
 */

/**
 * Um setor no corpo do `PUT` — espelha `app/schemas/evento.py::SetorEdicao`.
 *
 * ⚠️ **`id` ausente significa setor novo, e é o campo inteiro desta feature.**
 * Com `id`, altera aquele setor; sem `id`, cria; o setor que **não aparece na
 * lista** é removido. Não existe um campo `remover: true` em lugar nenhum: o
 * `PUT` manda o estado final, e a diferença contra o banco é o que o service
 * executa.
 */
export type SetorParaEditar = {
  id?: string;
  nome: string;
  capacidade: number;
  preco_centavos: number;
};

/**
 * O corpo inteiro — espelha `app/schemas/evento.py::EventoEdicao`.
 *
 * **Três campos, e os cinco do catálogo não estão aqui** (AD-1): `nome`,
 * `imagem_url`, `local`, `cidade` e `origem_externa_id` são copiados do catálogo
 * na publicação e o organizador não digita nenhum deles. O schema do backend
 * ignora esses campos se vierem; este tipo é o que impede que venham.
 */
export type EdicaoDeEvento = {
  /** ISO-8601 com offset (AD-11) — o `toISOString()` do instante montado na tela. */
  data_hora: string;
  setores: SetorParaEditar[];
  portaria_ids: string[];
};

/**
 * Manda o estado final do evento e devolve o evento como ele ficou.
 *
 * **Levanta `ErroDaApi`**, como o `validarCodigo` e ao contrário das leituras do
 * `lib/`: quem chama é uma ilha do navegador com `try/catch` à volta, e não um
 * Server Component que não pode deixar a exceção subir.
 *
 * A resposta é o **mesmo** `EventoSaida` das outras três rotas de evento, então
 * o tipo é o mesmo `MeuEventoDetalhe` — `import type`, que o compilador apaga:
 * nada do `lib/eventos.ts`, que fala com `next/headers`, atravessa para o bundle.
 */
export async function atualizarMeuEvento(
  id: string,
  corpo: EdicaoDeEvento,
): Promise<MeuEventoDetalhe> {
  return chamarApi<MeuEventoDetalhe>(
    `/organizador/eventos/${encodeURIComponent(id)}`,
    { method: "PUT", body: JSON.stringify(corpo) },
  );
}
