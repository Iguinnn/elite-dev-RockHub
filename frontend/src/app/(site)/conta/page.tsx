import { redirect } from "next/navigation";

import BotaoSair from "@/components/BotaoSair";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * Dados da conta e a saída. Server Component com a guarda de sessão.
 *
 * **A guarda mora aqui, não num `middleware`.** O caminho que todo tutorial
 * mostra é conferir o cookie antes de a rota renderizar — mas o middleware só
 * consegue ver que **existe** um cookie, não que ele vale; validar o JWT ali
 * exigiria o `JWT_SECRET` no ambiente do frontend, que é o contrário do AD-2.
 * E ele viraria uma segunda lista de rotas protegidas, paralela às páginas:
 * duas listas divergem, e a que fica desatualizada é sempre a que ninguém olha.
 *
 * O custo é repetir três linhas em cada página protegida. Elas ficam ao lado do
 * conteúdo que protegem, que é onde quem edita a página vai olhar.
 *
 * ⚠️ `redirect()` funciona levantando `NEXT_REDIRECT` e não pode ficar dentro
 * de `try/catch`. Aqui não fica: o `try` mora dentro do `sessao.ts`, e o que
 * sobra é um `if`.
 */
export default async function Conta() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fconta");
  }

  return (
    <section className={estilos.pagina}>
      <p className="kicker">Minha conta</p>

      {/* Serifada só no nome: é nome próprio. E-mail e papel são dado de
          máquina, então mono em versalete — UX-DR2, a mesma divisão do
          formulário de cadastro. */}
      <h1 className={estilos.nome}>{usuario.nome}</h1>

      <dl className={estilos.dados}>
        <dt>E-mail</dt>
        <dd>{usuario.email}</dd>
        <dt>Papel</dt>
        <dd>{usuario.papel}</dd>
      </dl>

      <div className={estilos.saida}>
        <BotaoSair />
      </div>
    </section>
  );
}
