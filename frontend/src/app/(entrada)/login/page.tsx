import Link from "next/link";

import FormularioLogin from "@/components/FormularioLogin";
import { caminhoInternoSeguro } from "@/lib/caminho";

import estilos from "./page.module.css";

/**
 * Tela de acesso: coluna centrada de no máximo 440px, kicker e formulário.
 * Sem segundo logotipo — o masthead do layout raiz já traz um.
 *
 * O `?voltar=` é lido e **validado aqui**, no servidor, antes de chegar ao
 * formulário. Deixar a validação no Client Component exigiria
 * `useSearchParams()` (que pede fronteira de `<Suspense>`) e mandaria a regra
 * de segurança para o navegador, onde ela vale menos.
 *
 * ⚠️ `searchParams` é Promise no Next 16. Sem o `await`, `voltar` seria
 * `undefined`, cairia calado no padrão `/` e pareceria "o voltar não funciona".
 */
export default async function Login({ searchParams }: PageProps<"/login">) {
  const voltar = caminhoInternoSeguro((await searchParams).voltar);

  return (
    <section className={estilos.coluna}>
      <p className="kicker">Acesso</p>
      <FormularioLogin voltar={voltar} />
      <p className={estilos.rodape}>
        Ainda não tem conta?{" "}
        {/* O destino viaja junto: quem foi mandado para cá, resolveu se
            cadastrar e criou a conta perderia o caminho de volta no meio. */}
        <Link
          href={
            voltar === "/"
              ? "/cadastro"
              : `/cadastro?voltar=${encodeURIComponent(voltar)}`
          }
        >
          Cadastre-se
        </Link>
      </p>
    </section>
  );
}
