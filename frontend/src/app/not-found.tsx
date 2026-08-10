import estilos from "./not-found.module.css";

/**
 * 404 com a cara do projeto, no mesmo padrão de estado vazio da raiz.
 *
 * Hoje ela atende `/ingressos` e `/conta`, que só nascem nas Stories 4.1 e
 * 1.5, e vai atender também o link de ingresso compartilhado que foi revogado
 * (Story 4.4). A saída é a navegação do masthead — estado vazio não ganha
 * botão grande de chamada.
 */
export default function NaoEncontrado() {
  return (
    <section className={estilos.vazio}>
      <p className="kicker">Erro 404</p>
      <p className={estilos.frase}>
        Este endereço não existe. Confira o link ou use a navegação acima.
      </p>
    </section>
  );
}
