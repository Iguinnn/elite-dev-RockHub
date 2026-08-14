"use client";

import { useState } from "react";

import { COOKIE_DO_TEMA, VALIDADE_DO_TEMA, type Tema } from "@/lib/tema";

import estilosDoMenu from "./Masthead.module.css";
import estilos from "./SeletorDeTema.module.css";

/**
 * O botão que troca o tema — a única peça que torna o modo claro alcançável.
 *
 * **O tema atual chega por prop, e não é preguiça de não ler o DOM.** Quem
 * renderiza este botão é um Server Component que já leu o cookie; se o estado
 * inicial viesse de `document.documentElement.dataset.tema`, ele só existiria
 * na hidratação e o servidor teria de chutar um rótulo — que é a definição de
 * divergência de hidratação. Com a prop, servidor e cliente escrevem a mesma
 * palavra na primeira pintura.
 *
 * ⚠️ **Sem server action e sem `router.refresh()`, de propósito.** O clique faz
 * duas coisas na mesma função: escreve o atributo no `<html>`, que é o que a
 * tela obedece **na hora**, e escreve o cookie, que serve só para o **próximo**
 * SSR. Uma server action daria uma ida ao servidor entre o clique e a troca de
 * cor — a pessoa clicaria em "modo claro" e olharia para uma tela escura
 * enquanto a rede responde. Trocar tema não é mutação de dado; é preferência de
 * quem está olhando.
 *
 * **O rótulo diz o modo que o clique liga**, não o que está ligado: um botão
 * escrito `MODO ESCURO` numa tela clara é uma promessa, e é assim que todo
 * alternador de tema se lê. O `aria-label` completa a frase para quem ouve, e
 * contém o rótulo visível — quem navega por voz diz "modo escuro" e o comando
 * casa (WCAG 2.5.3).
 *
 * **A caixa é a do item de menu, importada do `Masthead.module.css`.** É o mesmo
 * atalho que o `NavLink` já faz, e aqui ele vale ainda mais: o botão fica no fim
 * do `<nav>`, encostado nos itens, e uma caixa "quase igual" ao lado de quatro
 * iguais é pior que uma cópia — é a que ninguém vê drifar. O módulo próprio ao
 * lado carrega só o que `<button>` precisa e `<a>` não.
 */
type Props = {
  tema: Tema;
};

export default function SeletorDeTema({ tema }: Props) {
  const [atual, setAtual] = useState<Tema>(tema);
  const proximo: Tema = atual === "claro" ? "escuro" : "claro";

  function alternar() {
    // O atributo primeiro: é ele que a tela obedece, e a troca é instantânea.
    document.documentElement.dataset.tema = proximo;
    // O cookie depois, para a próxima requisição já nascer no tema certo.
    // Sem `httpOnly` porque quem escreve é esta linha; `SameSite=Lax` porque
    // preferência visual não tem por que atravessar site de terceiro.
    document.cookie = `${COOKIE_DO_TEMA}=${proximo}; path=/; max-age=${VALIDADE_DO_TEMA}; samesite=lax`;
    setAtual(proximo);
  }

  return (
    <button
      type="button"
      onClick={alternar}
      className={`${estilosDoMenu.navLink} ${estilos.seletor}`}
      aria-label={`Mudar para o modo ${proximo}`}
    >
      Modo {proximo}
    </button>
  );
}
