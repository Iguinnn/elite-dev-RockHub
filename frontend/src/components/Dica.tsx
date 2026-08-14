"use client";

import { useId } from "react";

import estilos from "./Dica.module.css";

/**
 * Um `?` ao lado de um título, que revela uma explicação curta ao passar o mouse.
 *
 * ⚠️ **Abria no clique até 14/08/2026, e passou a abrir no `hover`** (decisão do
 * Igor). A versão anterior era um *disclosure*: `useState`, `aria-expanded`, e as
 * mecânicas de fechar no `Esc` e no clique de fora, copiadas do `SeletorDeData`.
 * Sumiu tudo — não sobrou estado, efeito nem `document.addEventListener`, e o
 * componente virou CSS com dois seletores.
 *
 * **O que se ganhou:** nenhum gesto. A explicação aparece no caminho do ponteiro,
 * que é o que se espera de um `?` ao lado de um título, e o componente deixou de
 * ter ciclo de vida para manter.
 *
 * ⚠️ **O que se perdeu, e como está mitigado:** `hover` não existe em touch. O
 * gatilho continua sendo um `<button>` focável de propósito — e é isso que
 * mantém três caminhos abertos: o ponteiro (`:hover`), o teclado (`:focus`) e o
 * toque, porque tocar num botão o **foca**, mesmo sem `onClick` para chamar. Um
 * `<span>` sem `tabIndex` seria mais simples e fecharia os dois últimos.
 *
 * ⚠️ **Agora é `role="tooltip"` de verdade, e antes não era.** A redação anterior
 * deste docstring dizia, com todas as letras, que a ARIA reserva `tooltip` para o
 * rótulo curto que aparece sozinho no foco, e que aqui era *disclosure* — estava
 * certa **para aquele comportamento**. Trocado o gatilho, o papel trocou junto:
 * isto agora é exatamente o rótulo curto que aparece no foco. O `aria-describedby`
 * é o que amarra os dois, e é ele que faz o leitor de tela anunciar o texto como
 * **descrição** do botão, e não como o nome dele.
 *
 * **Sem `useState`, mas com `"use client"`** — e a diretiva não é sobra: o `useId`
 * é hook, e hook não roda em Server Component. Ele existe porque o
 * `aria-describedby` precisa de um id **único por instância**, e derivá-lo do
 * `rotulo` quebraria no dia em que duas dicas na mesma tela tivessem o mesmo
 * rótulo — sem erro nenhum, com o leitor de tela lendo a descrição errada.
 */
export default function Dica({
  rotulo,
  children,
}: {
  /**
   * O nome acessível do botão — o que o leitor de tela lê no lugar do `?`.
   * Obrigatório: um botão cujo conteúdo visível é um sinal de pontuação não tem
   * nome nenhum sem isto, e o UX-DR9 pede rótulo associado em todo controle.
   *
   * ⚠️ **Ele não é o texto da dica**, e os dois papéis não se trocam: este é o
   * **nome** ("Sobre os shows que aparecem aqui"), e o `children` é a
   * **descrição**. Repetir a explicação aqui faria o leitor de tela lê-la duas
   * vezes seguidas.
   */
  rotulo: string;
  /** O texto da explicação. Curto — é uma nota, não uma seção de ajuda. */
  children: React.ReactNode;
}) {
  const id = useId();

  return (
    <span className={estilos.involucro}>
      <button
        type="button"
        className={estilos.gatilho}
        aria-label={rotulo}
        aria-describedby={id}
      >
        {/* `aria-hidden` no glifo: quem anuncia o botão é o `aria-label` acima,
            e sem isto o leitor de tela leria "ponto de interrogação" junto. */}
        <span aria-hidden="true">?</span>
      </button>

      {/* ⚠️ **Sempre no DOM, e escondido por CSS** — nunca por `{aberta && …}`.
          O `aria-describedby` acima aponta para este id, e uma referência que não
          resolve é silenciosamente ignorada: o leitor de tela anunciaria o botão
          sem descrição nenhuma. Montado sempre, ele resolve — e no foco, que é
          quando o teclado chega aqui, o painel está visível de qualquer forma.

          **Irmão do botão, e não filho dele**: dentro, o texto entraria no nome
          acessível do gatilho, que é justamente o que o `aria-describedby` existe
          para evitar. */}
      <span id={id} role="tooltip" className={estilos.painel}>
        {children}
      </span>
    </span>
  );
}
