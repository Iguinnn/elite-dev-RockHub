import FormularioLogin from "@/components/FormularioLogin";

import estilos from "./page.module.css";

/**
 * Tela de acesso: coluna centrada de no máximo 440px, kicker e formulário.
 * Sem segundo logotipo — o masthead do layout raiz já traz um.
 */
export default function Login() {
  return (
    <section className={estilos.coluna}>
      <p className="kicker"></p>
      <FormularioLogin />
    </section>
  );
}
