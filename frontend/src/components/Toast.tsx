import estilos from "./Toast.module.css";

/**
 * Aviso flutuante no canto inferior direito — o erro que não cabe no rodapé.
 *
 * **Ele existe porque a mensagem do UX-DR8 é longa e chega depois do clique.**
 * A frase nomeia dois setores ("A Pista acabou de esgotar. Ainda há ingressos no
 * setor Área VIP") e não cabe na linha do total sem espremer o botão; posta
 * acima dela, empurraria o rodapé inteiro e a lista de setores junto, no
 * instante em que a pessoa mais precisa que a tela fique parada. Flutuando, ela
 * aparece sem mexer em nada do que já estava desenhado.
 *
 * ⚠️ **A regra invisível é a mesma do `AvisoDeErro`, e é por isso que este é um
 * componente e não três linhas de JSX na ilha**: o `<div role="alert">` **existe
 * sempre no DOM, vazio**, e só o conteúdo entra depois. Leitor de tela que recebe
 * o `role` junto com o conteúdo, num nó recém-criado, pode não anunciar nada —
 * ele observa mudanças *dentro* de uma região viva. Vazia, a região não ocupa
 * espaço nem intercepta clique (ver o `pointer-events` do CSS).
 *
 * **Não some sozinho, de propósito.** Toast com temporizador é o padrão da
 * internet e está errado aqui: esta mensagem diz que o estoque mudou e que a
 * escolha precisa ser refeita, e ela sumir enquanto a pessoa lê a lista atrás
 * dela é perder justamente a explicação do que acabou de acontecer na tela.
 * Quem fecha é quem leu — ou a próxima tentativa, que limpa o aviso antes de
 * enviar.
 *
 * Sem `"use client"`: ele não tem interação própria: o `onFechar` chega pronto
 * de quem o usa, como no `Campo` e no `Botao`.
 *
 * ⚠️ **A altura virou prop em 13/08/2026, e o comentário do CSS previa o dia.**
 * Enquanto a página do evento era a única consumidora, o `bottom` estava fixo em
 * 104px para o toast não cair sobre o rodapé `sticky` dela — que é justamente a
 * ação que a mensagem pede para refazer. O formulário de publicar não tem rodapé
 * fixo, e herdar aquele valor deixaria o aviso flutuando no meio do nada, com um
 * vão vazio embaixo. Um `104px` copiado para o segundo consumidor é o tipo de
 * número que ninguém revisa quando o rodapé do primeiro mudar de altura.
 */
export default function Toast({
  mensagem,
  aoFechar,
  posicao = "base",
}: {
  mensagem: React.ReactNode;
  aoFechar: () => void;
  /**
   * `"base"` encosta o aviso no pé da janela — é o padrão, e serve a qualquer
   * tela. `"acima-do-rodape"` o sobe o suficiente para não cobrir o rodapé
   * `sticky` da página do evento.
   */
  posicao?: "base" | "acima-do-rodape";
}) {
  return (
    <div
      className={`${estilos.area} ${
        posicao === "acima-do-rodape" ? estilos.acimaDoRodape : ""
      }`}
      role="alert"
    >
      {mensagem && (
        <div className={estilos.toast}>
          <p className={estilos.texto}>{mensagem}</p>
          {/* `aria-label` porque `×` sozinho é lido como "multiplicação" ou
              como nada. `type="button"` porque este componente pode acabar
              dentro de um `<form>`, e o default de `<button>` é `submit`. */}
          <button
            type="button"
            className={estilos.fechar}
            onClick={aoFechar}
            aria-label="Fechar aviso"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
