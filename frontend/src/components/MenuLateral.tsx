"use client";

import { useEffect, useRef, useState } from "react";

import estilos from "./MenuLateral.module.css";

/**
 * A gaveta de navegação das telas estreitas (decisão do Igor, 14/08/2026).
 *
 * **O que ela conserta:** abaixo de 900px os quatro itens do `<nav>` quebravam
 * em três linhas de caixas, e no celular a última encostava na borda cortada. A
 * fileira do masthead foi desenhada para caber numa linha ao lado do logotipo —
 * quando ela não cabe, empilhar não é o mesmo desenho em outro tamanho, é outro
 * desenho. Aqui os destinos saem da faixa e viram uma lista, que é a forma que
 * uma navegação longa tem em tela estreita.
 *
 * ⚠️ **`<dialog>` nativo com `showModal()`, no molde exato da `Confirmacao`.**
 * Trava de foco, fechar com `Esc`, `::backdrop`, resto da página inerte e
 * **devolver o foco ao botão que abriu** vêm de graça e corretos. *Descartei* o
 * `<div>` com `role="dialog"`, que seria mais código para reimplementar pior o
 * que o navegador já faz — e o projeto já tinha escolhido isso uma vez.
 *
 * ⚠️ **Ela desliza da direita, e isso é a TERCEIRA exceção consciente ao
 * `EXPERIENCE.md`** (pedido do Igor, 14/08/2026 — as outras duas são a espera de
 * 6s do checkout e a varredura do item de menu). O documento proíbe travessia com
 * todas as letras: *"nada desliza de uma lateral à outra"* é o primeiro
 * anti-padrão da lista. Eu avisei da regra e ele confirmou o pedido; fica
 * registrado aqui e no `MenuLateral.module.css`, ao lado da linha que anima —
 * mesmo tratamento que as outras duas exceções receberam.
 *
 * O argumento a favor: gaveta lateral é o único componente do produto cuja
 * **origem é informação**. Parada, ela não diz de onde veio nem para onde volta.
 * Aqui o movimento carrega significado em vez de enfeitar — que é exatamente a
 * fronteira que o `EXPERIENCE.md` desenha quando libera a espera do checkout.
 *
 * Quem pede menos movimento recebe a gaveta parada: o bloco de
 * `prefers-reduced-motion` do `globals.css` desliga toda transição com
 * `!important`, e o estado final é idêntico.
 *
 * ⚠️ **Fecha sozinha quando o caminho muda.** Sem isso, tocar num destino
 * navegaria por baixo e deixaria a gaveta aberta sobre a tela nova — o defeito
 * clássico de gaveta em roteador de cliente, porque a navegação do Next não
 * recarrega a página e nada desmonta este componente.
 *
 * **Os destinos chegam por `children`, e são os mesmos `NavLink` do masthead.**
 * Nada de uma segunda lista escrita aqui dentro: quem decide o que aparece por
 * papel é o `Masthead`, num lugar só. O item ativo continua se marcando sozinho
 * pelo `usePathname` de cada `NavLink`.
 */
export default function MenuLateral({
  children,
}: {
  children: React.ReactNode;
}) {
  const [aberta, setAberta] = useState(false);
  const dialogo = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento) return;

    // Os dois `if` conferem `elemento.open` antes de agir: `showModal()` num
    // diálogo já aberto levanta `InvalidStateError`. Mesma guarda da
    // `Confirmacao`, pelo mesmo motivo.
    if (aberta && !elemento.open) elemento.showModal();
    if (!aberta && elemento.open) elemento.close();
  }, [aberta]);

  return (
    <>
      <button
        type="button"
        className={estilos.sanduiche}
        onClick={() => setAberta(true)}
        aria-label="Abrir o menu"
        aria-expanded={aberta}
      >
        {/* Três filetes desenhados por `<span>`, e não um caractere `☰`: o
            glifo muda de forma e de peso conforme a fonte instalada, e esta
            fileira precisa casar com a espessura de 1px dos fios do produto. */}
        <span className={estilos.filete} />
        <span className={estilos.filete} />
        <span className={estilos.filete} />
      </button>

      <dialog
        ref={dialogo}
        className={estilos.gaveta}
        onClose={() => setAberta(false)}
        aria-label="Navegação principal"
      >
        <div className={estilos.topoDaGaveta}>
          <span className={estilos.kicker}>Menu</span>
          {/* O `Esc` fecha, mas no celular não há `Esc` — e tocar no backdrop
              não é descoberto por ninguém. O botão é o único caminho de saída
              que se vê. */}
          <button
            type="button"
            className={estilos.fechar}
            onClick={() => setAberta(false)}
            aria-label="Fechar o menu"
          >
            ✕
          </button>
        </div>

        {/* ⚠️ **O clique fecha por delegação, e não por um efeito no
            `usePathname`.** A navegação do Next não recarrega a página e nada
            desmonta este componente, então sem fechar à mão a gaveta ficaria
            aberta sobre a tela nova — o defeito clássico de gaveta em roteador
            de cliente.

            **Por que aqui e não num efeito de caminho:** tocar no destino que já
            é o atual não muda o `usePathname`, e pelo efeito a gaveta ficaria
            aberta justamente no toque mais provável de quem se enganou. O clique
            é o fato; a mudança de rota é uma consequência dele que às vezes não
            acontece. (De quebra, `setState` dentro de efeito é o que a regra
            `react-hooks/set-state-in-effect` recusa — e aqui ela estava certa.)

            O `<nav>` recebe o `onClick` em vez de cada `NavLink`: quem escreve os
            destinos é o `Masthead`, e exigir que ele passasse um `aoNavegar` a
            cada item poria a responsabilidade de fechar esta gaveta em quem não
            sabe que ela existe. */}
        <nav
          className={estilos.destinos}
          onClick={() => setAberta(false)}
        >
          {children}
        </nav>
      </dialog>
    </>
  );
}
