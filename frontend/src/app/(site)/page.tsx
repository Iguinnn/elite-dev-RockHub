import estilos from "./page.module.css";

/**
 * Raiz da aplicação. Enquanto não há evento publicado, ela é o estado vazio
 * do EXPERIENCE.md: kicker, uma frase, fim. Sem ilustração e sem botão grande
 * de chamada. A listagem de verdade entra na Story 3.1.
 */
export default function Inicio() {
  return (
    <section className={estilos.vazio}>
      <p className="kicker">Programação</p>
      <p className={estilos.frase}>
        A programação entra no ar quando os primeiros eventos forem publicados.
      </p>
    </section>
  );
}
