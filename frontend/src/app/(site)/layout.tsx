import Masthead from "@/components/Masthead";
import Rodape from "@/components/Rodape";

/**
 * A casca do site: masthead com navegação, o conteúdo na coluna única e o
 * rodapé fechando a folha.
 * Tudo que é navegável por quem já entrou mora aqui.
 *
 * ⚠️ **O rodapé é só deste grupo** (14/08/2026). O `(entrada)` não o recebe pelo
 * mesmo motivo que não recebe masthead — login e cadastro são uma coluna só, sem
 * nada em volta, e quem ainda não entrou não deve ver cercadura que não pode
 * usar. A `/portaria` também fica de fora: é ferramenta de trabalho, usada em pé
 * e com fila esperando, e endereço de escritório embaixo da leitura de QR é
 * exatamente o ruído que a casca de lá existe para não ter.
 */
export default function LayoutDoSite({ children }: LayoutProps<"/">) {
  return (
    <div className="conteudo">
      <Masthead />
      <main>{children}</main>
      <Rodape />
    </div>
  );
}
