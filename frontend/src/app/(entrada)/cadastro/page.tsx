import Link from "next/link";

import FormularioCadastro from "@/components/FormularioCadastro";
import { caminhoInternoSeguro } from "@/lib/caminho";

import estilos from "./page.module.css";

/**
 * Tela de cadastro: mesma coluna centrada do login, no mesmo grupo `(entrada)`
 * — o logotipo sem navegação vem do layout do grupo, não daqui.
 *
 * Server Component `async`, pelo mesmo motivo do login: o `?voltar=` é lido e
 * validado aqui. Só o formulário é ilha de cliente.
 */
export default async function Cadastro({ searchParams }: PageProps<"/cadastro">) {
  const voltar = caminhoInternoSeguro((await searchParams).voltar);

  return (
    <section className={estilos.coluna}>
      <p className="kicker">Criar conta</p>
      <FormularioCadastro voltar={voltar} />
      <p className={estilos.rodape}>
        Já tem conta?{" "}
        <Link
          href={
            voltar === "/" ? "/login" : `/login?voltar=${encodeURIComponent(voltar)}`
          }
        >
          Entrar
        </Link>
      </p>
    </section>
  );
}
