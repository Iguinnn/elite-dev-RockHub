"use client";

import { useEffect, useRef } from "react";

import Botao from "@/components/Botao";

import estilos from "./Confirmacao.module.css";

/**
 * A caixa que pergunta antes de uma ação sem volta — a primeira do produto
 * (Story 4.4).
 *
 * ⚠️ **`<dialog>` nativo com `showModal()`, e não um `<div role="dialog">`.**
 * Trava de foco, fechar com `Esc`, `::backdrop` e o resto da página inerte vêm
 * de graça e corretos — inclusive **devolver o foco ao elemento que abriu o
 * diálogo**, que é a parte que quase toda implementação à mão esquece.
 * *Descartei* o `<div>` com `role`, que seria mais código para reimplementar
 * pior o que o navegador já faz, e *descartei* o `window.confirm()`, que
 * custaria zero e poria a única caixa de diálogo do produto fora da identidade
 * visual inteira.
 *
 * ⚠️ **`showModal()`, nunca `show()`.** O segundo abre o `<dialog>` sem
 * backdrop, sem travar o foco e sem tornar a página inerte: parece funcionar e
 * não é diálogo modal nenhum.
 *
 * ⚠️ **Aparece sem animação**, e isso é decisão registrada. O
 * `EXPERIENCE.md#Interaction Primitives` proíbe travessia e libera só mudança
 * de cor até 120ms, e o `CLAUDE.md` registra a espera do checkout como **a
 * única animação do produto** — uma segunda tornaria falsa uma frase escrita em
 * dois arquivos. Aparecer inteiro e parado é o mesmo comportamento que "sem
 * *spinner*, a estrutura aparece com os fios no lugar".
 *
 * **Genérico por props**: nada de "revogar" escrito aqui dentro. Quem sabe o
 * que está sendo confirmado é quem chama.
 *
 * **Todo caminho de fechar passa pelo evento `close` do próprio `<dialog>`** —
 * `Esc`, o botão *Cancelar* e o clique em confirmar. É isso que garante que o
 * estado de quem chama nunca fique "aberto" com a caixa fechada na tela, que é
 * o defeito clássico de controlar um diálogo por fora.
 */
export default function Confirmacao({
  aberta,
  titulo,
  consequencia,
  rotuloDaAcao,
  aoConfirmar,
  aoFechar,
}: {
  aberta: boolean;
  titulo: string;
  /** Uma frase dizendo o que acontece se a pessoa seguir. */
  consequencia: React.ReactNode;
  /** O verbo da ação, no botão destrutivo. Nunca "OK". */
  rotuloDaAcao: string;
  aoConfirmar: () => void;
  /** Chamado quando o diálogo fecha por qualquer caminho, inclusive `Esc`. */
  aoFechar: () => void;
}) {
  const dialogo = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento) return;

    // ⚠️ Os dois `if` conferem `elemento.open` antes de agir: chamar
    // `showModal()` num diálogo já aberto levanta `InvalidStateError`, e o
    // efeito roda de novo a cada render em que `aberta` mudou de identidade.
    if (aberta && !elemento.open) elemento.showModal();
    if (!aberta && elemento.open) elemento.close();
  }, [aberta]);

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      // O evento `close` é disparado pelo `Esc` e por todo `close()` deste
      // arquivo — um lugar só avisa quem chama que a caixa saiu da tela.
      onClose={aoFechar}
      aria-labelledby="confirmacao-titulo"
    >
      <h2 id="confirmacao-titulo" className={estilos.titulo}>
        {titulo}
      </h2>

      <p className={estilos.consequencia}>{consequencia}</p>

      <div className={estilos.acoes}>
        {/* Secundário: fio e texto, sem tinta. Ele é a saída, e a saída não
            compete com a ação. `type="button"` porque não há formulário aqui
            e o padrão de `<button>` é `submit`. */}
        <button
          type="button"
          className={estilos.cancelar}
          onClick={() => dialogo.current?.close()}
        >
          Cancelar
        </button>

        <div className={estilos.acao}>
          <Botao
            type="button"
            variante="destrutivo"
            onClick={() => {
              // Fecha primeiro: quem chamou trata o resultado na própria tela,
              // com o botão de origem em estado de espera. Uma caixa que
              // continuasse aberta durante a chamada precisaria de um terceiro
              // estado ("confirmando") só para ela.
              dialogo.current?.close();
              aoConfirmar();
            }}
          >
            {rotuloDaAcao}
          </Botao>
        </div>
      </div>
    </dialog>
  );
}
