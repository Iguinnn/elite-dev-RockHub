import CabecalhoDaPortaria from "@/components/CabecalhoDaPortaria";

import estilos from "./layout.module.css";

/**
 * A terceira casca do frontend: a da porta (Story 5.1).
 *
 * **Casca própria, e não um item de navegação no masthead.** O caminho barato
 * era acrescentar um `NavLink` de *Turnos* ao `Masthead`, como `ORGANIZADOR` e
 * `CLIENTE` ganharam os deles. Descartei porque o `EXPERIENCE.md` é explícito
 * nos dois sentidos — "Portaria: navegação própria, sem o header do cliente" e
 * "a única superfície projetada primeiro para telas pequenas". Quem está na
 * porta está em pé, à noite, com uma mão livre, e o masthead de jornal come a
 * metade de cima de um celular para oferecer *Início*: uma programação de shows
 * que essa pessoa não vai comprar.
 *
 * **Sem grupo de rotas, ao contrário de `(site)` e `(entrada)`.** Aqueles
 * existem porque agrupam caminhos de topo diferentes sob uma casca comum —
 * `/conta`, `/login`, `/ingressos` não têm prefixo em comum. Aqui tudo mora sob
 * `/portaria`, e o segmento já é o grupo: um `(porta)/portaria/` seria uma pasta
 * a mais sem nada a mais.
 *
 * **`.conteudo`, a mesma medida do `(site)` e do `(entrada)`** (decisão do
 * Igor). A primeira versão fechava numa coluna de 560px pelo "primeiro para
 * telas pequenas" do `EXPERIENCE.md`; na tela, a casca ficou visivelmente mais
 * estreita que o resto do produto e a diferença leu como defeito, não como
 * escolha. O motivo inteiro está no `CabecalhoDaPortaria.module.css`.
 *
 * **O cabeçalho é componente, e não markup daqui**, porque o `not-found.tsx` da
 * raiz também precisa dele: ele atende URL que não casa com rota nenhuma, roda
 * fora de qualquer layout de grupo, e sem isso o 404 devolvia a portaria para a
 * casca de jornal. O motivo inteiro está no docstring do componente.
 *
 * **Nenhuma guarda aqui.** Quem protege as rotas são as páginas: layout do App
 * Router não roda de novo em navegação dentro do mesmo segmento, e uma guarda
 * neste arquivo daria a impressão de proteger sem proteger.
 *
 * ⚠️ **A portaria fica travada no escuro** (14/08/2026), e o invólucro externo é
 * como isso é feito: `data-tema="escuro"` redeclara os tokens da paleta para
 * tudo que estiver dentro, mesmo com a página em modo claro. Aqui o escuro é
 * **função, não estilo** — o `globals.css` justifica o verde-limão do veredito
 * com "a portaria lê isso a três metros, no escuro, com pressa", e a distância
 * de luminância entre `VÁLIDO` (11,5:1) e `INVÁLIDO` (5,0:1) é o que separa os
 * dois para quem tem daltonismo vermelho-verde. Um fundo claro embaralha isso, e
 * coerência visual não vale um veredito lido errado na porta.
 *
 * ⚠️ **Não há alternador de tema nesta casca**, e a ausência é a decisão: um
 * botão que não faz nada é pior que botão nenhum.
 *
 * O `not-found.tsx` da raiz renderiza o mesmo `CabecalhoDaPortaria` e **não**
 * está sob este layout — ele segue o tema escolhido, e isso é aceito: a trava
 * vale para `/portaria/*`, onde há veredito a ler, não para o 404.
 */
export default function LayoutDaPortaria({ children }: LayoutProps<"/portaria">) {
  return (
    <div data-tema="escuro" className={estilos.casca}>
      <div className="conteudo">
        <CabecalhoDaPortaria />
        <main>{children}</main>
      </div>
    </div>
  );
}
