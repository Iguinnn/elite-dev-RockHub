import { redirect } from "next/navigation";

import DadosDaConta from "@/components/DadosDaConta";
import { casaDoPapel } from "@/lib/papel";
import { obterUsuarioDaSessao } from "@/lib/sessao";

/**
 * "Minha conta" dentro da casca da portaria (Story 5.1).
 *
 * **É a mesma tela da `/conta` do `(site)`, pelo mesmo componente.** As duas
 * saídas fáceis estão descartadas no docstring do `<DadosDaConta>`: linkar para
 * `/conta` jogaria a portaria de volta na casca de jornal que a casca própria
 * existe para evitar, e copiar as vinte linhas daria duas telas de conta que
 * divergem no dia em que uma delas mudar.
 *
 * **O que não se compartilha é a guarda**, e é por isso que ela ficou nas
 * páginas: o `?voltar=` aponta para uma rota diferente em cada uma, e o papel
 * exigido aqui é `PORTARIA` — quem entra nesta URL com conta de cliente não
 * pertence a esta casca, mesmo que a tela que veria fosse idêntica.
 *
 * ⚠️ `redirect()` levanta `NEXT_REDIRECT` e não pode ficar dentro de
 * `try/catch`. Aqui não fica: o `try` mora no `sessao.ts`, e o que sobra é `if`.
 */
export default async function ContaDaPortaria() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fportaria%2Fconta");
  }
  if (usuario.papel !== "PORTARIA") {
    redirect(casaDoPapel(usuario.papel));
  }

  return <DadosDaConta usuario={usuario} />;
}
