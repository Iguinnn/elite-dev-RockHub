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
 * ⚠️ **`voltar` viaja como `string | undefined` desde a Story 5.1, e a diferença
 * entre `undefined` e `"/"` é a story inteira.** Até aqui esta página aplicava o
 * padrão `"/"` do `caminhoInternoSeguro` antes de repassar, e com isso perdia a
 * única informação que o formulário precisa ter: se **alguém pediu** um destino
 * ou se ninguém pediu nada. É só quando ninguém pede que o papel decide para
 * onde ir — a portaria vai para a casa dela, e o `?voltar=` continua soberano
 * para quem foi interrompido no meio de alguma coisa, que é o caso que ele
 * existe para resolver desde a 1.4.
 *
 * O parâmetro **presente e recusado** (`//exemplo.com`, `/login`) vira `"/"` e
 * não `undefined`: quem mandou o link pediu um destino, e a resposta a um
 * destino inseguro é a raiz, não a casa do papel.
 *
 * ⚠️ `searchParams` é Promise no Next 16. Sem o `await`, `voltar` seria
 * `undefined`, cairia calado no destino por papel e pareceria "o voltar não
 * funciona".
 */
export default async function Login({ searchParams }: PageProps<"/login">) {
  const pedido = (await searchParams).voltar;
  const voltar = pedido === undefined ? undefined : caminhoInternoSeguro(pedido);

  // O link de cadastro não tem papel para consultar — ninguém entrou ainda —,
  // então para ele "ninguém pediu" e "pediram a raiz" são a mesma coisa.
  const destinoDoCadastro = voltar ?? "/";

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
            destinoDoCadastro === "/"
              ? "/cadastro"
              : `/cadastro?voltar=${encodeURIComponent(destinoDoCadastro)}`
          }
        >
          Cadastre-se
        </Link>
      </p>
    </section>
  );
}
