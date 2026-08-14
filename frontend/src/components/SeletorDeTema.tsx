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
 * ⚠️ **Virou ícone em 14/08/2026** (decisão do Igor), junto com a gaveta lateral.
 * Era o rótulo `Modo claro` / `Modo escuro` numa caixa igual à dos destinos.
 * O motivo é largura: com os destinos saindo para o `MenuLateral` abaixo de
 * 900px, sobra na faixa o logotipo, o sanduíche e este botão — e uma caixa de
 * ~150px escrita `MODO CLARO` ao lado de um quadrado de 44px desequilibra a
 * única linha que restou. O ícone ocupa o mesmo lado do sanduíche e some do
 * caminho.
 *
 * **O símbolo diz o modo que o clique liga**, não o que está ligado — a mesma
 * regra que o rótulo seguia: sol para acender, lua para apagar. É assim que todo
 * alternador de tema se lê, e trocar essa direção junto com a troca de forma
 * seria mudar duas coisas de uma vez.
 *
 * ⚠️ **O `aria-label` continua sendo a frase inteira, e agora ele é a única
 * fonte do nome acessível** — antes o texto visível cumpria esse papel. Sem ele
 * o botão vira "botão" no leitor de tela. A frase mantém o mesmo formato de
 * antes para quem navega por voz (WCAG 2.5.3).
 *
 * **O SVG é inline e sem biblioteca**, no molde dos símbolos do `Veredito`:
 * dois ícones custam menos que uma dependência, e `currentColor` faz os dois
 * herdarem a cor do botão em qualquer um dos dois temas sem uma linha a mais.
 *
 * **A caixa continua sendo a do item de menu, importada do
 * `Masthead.module.css`** — o mesmo atalho que o `NavLink` faz. Uma caixa "quase
 * igual" ao lado das outras é pior que uma cópia: é a que ninguém vê drifar.
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
      {/* `aria-hidden` nos dois: o nome acessível é o `aria-label` do botão, e
          um SVG anunciado ao lado dele diria a mesma coisa duas vezes. */}
      {proximo === "claro" ? (
        // Sol — o clique acende. Miolo cheio e oito raios; `stroke-linecap`
        // redondo para os raios não terminarem em quina, que na entreletra
        // larga do produto leria como serrilha.
        <svg
          className={estilos.simbolo}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4.2" fill="currentColor" stroke="none" />
          <path d="M12 2.4v2.6M12 19v2.6M2.4 12h2.6M19 12h2.6M5.2 5.2l1.85 1.85M16.95 16.95l1.85 1.85M18.8 5.2l-1.85 1.85M7.05 16.95L5.2 18.8" />
        </svg>
      ) : (
        // Lua — o clique apaga. Crescente por recorte de caminho, e não duas
        // circunferências sobrepostas: com `fill` chapado, a segunda precisaria
        // da cor do fundo, e aí o ícone deixaria de funcionar sobre a varredura
        // do hover, que preenche a caixa inteira.
        <svg
          className={estilos.simbolo}
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M20.1 14.9A8.6 8.6 0 0 1 9.1 3.9a8.6 8.6 0 1 0 11 11Z" />
        </svg>
      )}
    </button>
  );
}
