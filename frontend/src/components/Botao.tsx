import estilos from "./Botao.module.css";

/**
 * Ação primária: âmbar sobre breu, mono 700 em versalete.
 *
 * **Só o primário.** O `DESIGN.md` descreve também um secundário e um
 * destrutivo, e nenhum dos dois tem consumidor ainda — uma prop `variante` com
 * um valor só é abstração inventada. Quando o segundo aparecer, ela nasce ali.
 *
 * Sem `"use client"` pelo mesmo motivo do `Campo`: nenhuma interação própria.
 */
type Props = React.ComponentPropsWithoutRef<"button">;

export default function Botao({ children, ...props }: Props) {
  return (
    <button className={estilos.botao} {...props}>
      {children}
    </button>
  );
}
