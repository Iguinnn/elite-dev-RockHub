import CabecalhoDaPortaria from "@/components/CabecalhoDaPortaria";
import Masthead from "@/components/Masthead";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./not-found.module.css";

/**
 * 404 com a cara do projeto, no mesmo padrão de estado vazio da raiz.
 *
 * Ela atende **URL que não casa com rota nenhuma**. A saída é a navegação do
 * cabeçalho — estado vazio não ganha botão grande de chamada.
 *
 * **Ela carrega a própria casca, e isso é obrigatório.** Só o `not-found.tsx`
 * da raiz de `app/` atende URL que não casa com rota nenhuma — dentro de um
 * grupo de rotas ele deixa de pegar, e o visitante cai no 404 padrão do Next,
 * sem identidade nenhuma. Testei: é exatamente o que acontece. Como o layout
 * raiz é só `<html><body>`, o cabeçalho precisa vir daqui.
 *
 * ⚠️ **E é justamente por isso que existe o `(site)/not-found.tsx`.** Todo
 * `notFound()` chamado de uma página do grupo era renderizado **aqui dentro**,
 * mas embrulhado pelo layout do `(site)` — que já tem masthead. Duas marcas,
 * duas navegações. A cópia sem casca do grupo é quem atende esses casos desde
 * a Story 4.4; esta continua atendendo o endereço que não existe.
 *
 * ⚠️ **Qual casca depende do papel, desde a Story 5.1.** Como este arquivo
 * carrega a casca à mão, ele carregava *uma* casca: a de jornal. Para quem está
 * na porta isso era o pior desfecho possível — errar o endereço, ou clicar num
 * turno enquanto `/portaria/eventos/{id}` não existe (a janela até a 5.3),
 * devolvia `Início` e `Minha conta` e nenhum caminho para `/portaria`. A leitura
 * de quem está na porta, e foi a do Igor na conferência, é "eu nem estou mais
 * logado". O 404 continua sendo o mesmo endereço inexistente; o que muda é que
 * ele agora devolve a pessoa para a casca dela.
 *
 * A leitura da sessão é `cache()`ada por requisição e o `Masthead` já a faria de
 * qualquer jeito — não há ida à rede a mais por causa desta escolha.
 */
export default async function NaoEncontrado() {
  const usuario = await obterUsuarioDaSessao();
  const naPorta = usuario?.papel === "PORTARIA";

  return (
    <div className="conteudo">
      {naPorta ? <CabecalhoDaPortaria /> : <Masthead />}
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
