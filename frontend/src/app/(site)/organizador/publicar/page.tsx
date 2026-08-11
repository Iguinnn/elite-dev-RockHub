import { redirect } from "next/navigation";

import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import { buscarNoCatalogo } from "@/lib/catalogo";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * Passo 1 do fluxo de publicação: buscar a atração no catálogo da
 * Ticketmaster. Server Component — a busca vive na URL (`?q=`), não em
 * estado de cliente, e por isso a página é recarregável, compartilhável e o
 * botão voltar funciona.
 *
 * **Duas guardas, não uma.** Sem sessão, `redirect` para o login com o
 * caminho de volta preservado — o mesmo padrão da `/conta`. Com sessão e
 * papel diferente de `ORGANIZADOR`, `redirect` para a raiz: a rota não é
 * segredo (a API responde `403`, que é público por natureza), e mandar
 * alguém logado para um 404 pareceria defeito.
 *
 * **Nada é clicável nesta story.** Selecionar a atração é a Story 2.4 — aqui
 * o organizador só busca e enxerga o resultado.
 *
 * **A busca acontece sempre, mesmo sem termo** — revisado depois do corte
 * original desta story: em vez de um convite "busque pelo nome do show" antes
 * de qualquer chamada, a tela já chega mostrando exemplos reais do catálogo
 * (os próximos eventos no Brasil), para o organizador ver do que se trata sem
 * precisar digitar nada primeiro.
 */
export default async function PublicarEvento({
  searchParams,
}: PageProps<"/organizador/publicar">) {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Forganizador%2Fpublicar");
  }
  if (usuario.papel !== "ORGANIZADOR") {
    redirect("/");
  }

  // `q` pode chegar como `string[]` (`?q=a&q=b`) — o primeiro valor basta,
  // não há motivo para a busca aceitar mais de um termo.
  const bruto = (await searchParams).q;
  const termo = (Array.isArray(bruto) ? bruto[0] : bruto) ?? "";
  const termoLimpo = termo.trim();

  // `buscarNoCatalogo` nunca levanta: o `503` da Ticketmaster é um estado da
  // tela, não uma falha da aplicação — não existe `error.tsx` neste projeto.
  // Chama sempre, com ou sem termo: sem termo, o backend lista os próximos
  // eventos do catálogo como exemplo.
  const resultado = await buscarNoCatalogo(termoLimpo);

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>1 · Escolha no catálogo</h1>
        <span className="kicker">Ticketmaster Discovery</span>
      </div>

      <form method="get" className={estilos.busca}>
        <div className={estilos.campoBusca}>
          <Campo
            id="q"
            name="q"
            type="search"
            rotulo="Buscar no catálogo"
            defaultValue={termo}
          />
        </div>
        <div className={estilos.botaoBusca}>
          <Botao type="submit">Buscar</Botao>
        </div>
      </form>

      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          O catálogo da Ticketmaster não respondeu. Tente de novo em instantes.
        </p>
      )}

      {resultado.estado === "ok" && resultado.itens.length === 0 && (
        <p className={estilos.aviso}>
          {termoLimpo
            ? "Nenhum show encontrado para essa busca."
            : "Não há shows no catálogo agora."}
        </p>
      )}

      {resultado.estado === "ok" && resultado.itens.length > 0 && (
        <div className={estilos.catalogo}>
          {resultado.itens.map((item) => {
            // A linha de origem só entra com o que existe: `local` e `cidade`
            // podem faltar, e juntar tudo com `filter` evita o "Ticketmaster ·
            // G5VYZ9A1KD ·  · " de buracos que sobraria se algum estivesse
            // ausente.
            const origem = [
              "Ticketmaster",
              item.id_externo,
              item.local,
              item.cidade,
            ]
              .filter(Boolean)
              .join(" · ");

            return (
              <div key={item.id_externo} className={estilos.item}>
                {item.imagem_url ? (
                  // A Discovery serve imagem de mais de um host
                  // (`s1.ticketm.net`, `media.ticketmaster.com`), e
                  // `next/image` exige `remotePatterns` declarado por host —
                  // errar um produz erro em tempo de execução. `<img>` com
                  // dimensão fixa no CSS resolve sem essa dependência.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.imagem_url}
                    alt=""
                    loading="lazy"
                    className={estilos.miniatura}
                  />
                ) : (
                  <div className={estilos.miniatura} />
                )}
                <div>
                  <h4 className={estilos.nome}>{item.nome}</h4>
                  <div className={estilos.origem}>{origem}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
