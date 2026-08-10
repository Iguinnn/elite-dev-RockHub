import Link from "next/link";

import FormularioCadastro from "@/components/FormularioCadastro";

import estilos from "./page.module.css";

/**
 * Tela de cadastro: mesma coluna centrada do login, no mesmo grupo `(entrada)`
 * — o logotipo sem navegação vem do layout do grupo, não daqui.
 *
 * Server Component. Só o formulário é ilha de cliente.
 */
export default function Cadastro() {
  return (
    <section className={estilos.coluna}>
      <p className="kicker">Criar conta</p>
      <FormularioCadastro />
      <p className={estilos.rodape}>
        Já tem conta? <Link href="/login">Entrar</Link>
      </p>
    </section>
  );
}
