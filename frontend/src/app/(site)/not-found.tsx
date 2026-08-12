import estilos from "@/app/not-found.module.css";

/**
 * A 404 de dentro do site — **sem casca própria**, ao contrário da raiz.
 *
 * ⚠️ **Ela existe porque o `not-found.tsx` da raiz carrega o próprio
 * masthead, e tem de carregar.** Aquele é o único que atende URL que não casa
 * com rota nenhuma, e ali o layout ao redor é só `<html><body>` — o motivo
 * inteiro está no docstring dele. Mas todo `notFound()` chamado de uma página
 * do grupo `(site)` é renderizado **dentro** do layout do grupo, que já
 * desenha `.conteudo`, o masthead e o `<main>`: o resultado era a marca e a
 * navegação aparecendo duas vezes, uma embaixo da outra.
 *
 * O defeito existia desde a Epic 3 e atingia todo `notFound()` do produto —
 * `/eventos/{id}` fora de cartaz, `/reservas/{id}` de outra pessoa,
 * `/ingressos/{id}` que não é seu. Apareceu na Story 4.4, na conferência do
 * link revogado.
 *
 * **O CSS é importado da raiz, e não copiado**: são as mesmas sete linhas de
 * estado vazio, e agora com dois consumidores de verdade.
 */
export default function NaoEncontradoNoSite() {
  return (
    <section className={estilos.vazio}>
      <p className="kicker">Erro 404</p>
      <p className={estilos.frase}>
        Este endereço não existe. Confira o link ou use a navegação acima.
      </p>
    </section>
  );
}
