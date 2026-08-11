import Logotipo from "@/components/Logotipo";

import estilos from "./layout.module.css";

/**
 * Casca das telas de acesso: só a marca, sem navegação.
 *
 * Quem está aqui ainda não entrou — mostrar "Meus ingressos" e "Minha conta"
 * seria oferecer duas portas que ele não pode abrir. O masthead volta assim
 * que a sessão existe, do outro lado do `(site)`.
 *
 * O cadastro (Story 1.5) entra neste mesmo grupo, e é por isso que a casca é
 * um layout e não markup dentro da página de login.
 */
export default function LayoutDeEntrada({ children }: LayoutProps<"/">) {
  return (
    <div className="conteudo">
      <header className={estilos.marca}>
        <Logotipo />
      </header>
      <main>{children}</main>
    </div>
  );
}
