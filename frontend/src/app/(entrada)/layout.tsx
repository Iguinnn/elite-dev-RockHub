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
 *
 * ⚠️ **O alternador de tema chegou a entrar aqui e saiu no mesmo dia**
 * (14/08/2026, decisão do Igor com a tela na frente). A `techspec-modo-claro`
 * pedia o contrário — "sem ele em `(entrada)` quem cai direto em `/login` não
 * teria como voltar" —, e a régua desta casca venceu: aqui não entra controle
 * que não seja entrar. O custo é real e é aceito: quem chega direto em `/login`,
 * por link ou rebatido de rota protegida, fica no tema em que chegou até passar
 * pelo masthead. **Não recoloque** achando que é esquecimento.
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
