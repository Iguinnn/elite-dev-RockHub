import estilos from "./Botao.module.css";

/**
 * Ação primária: neon sobre breu, mono 700 em versalete.
 *
 * **A `variante` nasceu na Story 4.4**, exatamente como este docstring previa
 * desde a 1.2: *"quando o segundo aparecer, ela nasce ali"*. O segundo é o
 * `destrutivo` — fundo `--brasa`, do `DESIGN.md#botao` —, e o consumidor é o
 * botão que confirma a revogação do link compartilhado. Revogar é a primeira
 * ação destrutiva do produto.
 *
 * **O secundário continua fora.** O `DESIGN.md` também o descreve, e ele
 * continua sem consumidor: o *Cancelar* do `<Confirmacao>` e o *Copiar* do
 * compartilhamento são botões de texto com fio, escritos na folha de estilo de
 * cada um. Uma terceira variante sem segundo consumidor seria o mesmo excesso
 * que manteve esta prop fora do componente por três epics.
 *
 * **`variante` é opcional e o padrão é o primário**, de propósito: as sete
 * telas que já usam `<Botao>` não mudaram uma linha, e nenhuma delas passa a
 * declarar que é primária — o que já era continua sendo, sem migração.
 *
 * Sem `"use client"` pelo mesmo motivo do `Campo`: nenhuma interação própria.
 */
type Props = React.ComponentPropsWithoutRef<"button"> & {
  variante?: "primario" | "destrutivo";
};

export default function Botao({
  children,
  variante = "primario",
  ...props
}: Props) {
  return (
    <button
      className={`${estilos.botao} ${variante === "destrutivo" ? estilos.destrutivo : ""}`}
      {...props}
    >
      {children}
    </button>
  );
}
