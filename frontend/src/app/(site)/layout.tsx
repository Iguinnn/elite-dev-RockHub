import Masthead from "@/components/Masthead";

/**
 * A casca do site: masthead com navegação e o conteúdo na coluna única.
 * Tudo que é navegável por quem já entrou mora aqui.
 */
export default function LayoutDoSite({ children }: LayoutProps<"/">) {
  return (
    <div className="conteudo">
      <Masthead />
      <main>{children}</main>
    </div>
  );
}
