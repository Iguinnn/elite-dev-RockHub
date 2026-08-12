import Masthead from "@/components/Masthead";

import estilos from "./not-found.module.css";

/**
 * 404 com a cara do projeto, no mesmo padrão de estado vazio da raiz.
 *
 * Ela atende **URL que não casa com rota nenhuma**. A saída é a navegação do
 * masthead — estado vazio não ganha botão grande de chamada.
 *
 * **Ela carrega a própria casca, e isso é obrigatório.** Só o `not-found.tsx`
 * da raiz de `app/` atende URL que não casa com rota nenhuma — dentro de um
 * grupo de rotas ele deixa de pegar, e o visitante cai no 404 padrão do Next,
 * sem identidade nenhuma. Testei: é exatamente o que acontece. Como o layout
 * raiz é só `<html><body>`, o masthead precisa vir daqui.
 *
 * ⚠️ **E é justamente por isso que existe o `(site)/not-found.tsx`.** Todo
 * `notFound()` chamado de uma página do grupo era renderizado **aqui dentro**,
 * mas embrulhado pelo layout do `(site)` — que já tem masthead. Duas marcas,
 * duas navegações. A cópia sem casca do grupo é quem atende esses casos desde
 * a Story 4.4; esta continua atendendo o endereço que não existe.
 */
export default function NaoEncontrado() {
  return (
    <div className="conteudo">
      <Masthead />
      <main>
        <section className={estilos.vazio}>
          <p className="kicker">Erro 404</p>
          <p className={estilos.frase}>
            Este endereço não existe. Confira o link ou use a navegação acima.
          </p>
        </section>
      </main>
    </div>
  );
}
