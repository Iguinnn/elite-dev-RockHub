import estilos from "./Campo.module.css";

/**
 * Rótulo e entrada, sempre juntos.
 *
 * Sem `"use client"`: o componente não tem interação própria. Importado por um
 * componente de cliente, ele vai para o bundle do cliente do mesmo jeito — a
 * diretiva só marcaria como ilha algo que não é.
 *
 * O `id` é obrigatório e serve às duas pontas: `htmlFor` no rótulo e `id` na
 * entrada. Não há caminho para renderizar um campo sem rótulo associado, que é
 * o piso de acessibilidade do UX-DR9.
 */
type Props = {
  id: string;
  rotulo: string;
} & Omit<React.ComponentPropsWithoutRef<"input">, "id" | "className">;

export default function Campo({ id, rotulo, ...props }: Props) {
  return (
    <div className={estilos.campo}>
      <label htmlFor={id} className={estilos.rotulo}>
        {rotulo}
      </label>
      <input id={id} className={estilos.entrada} {...props} />
    </div>
  );
}
