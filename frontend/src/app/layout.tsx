import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "RockHub",
  description:
    "A programação de shows, os ingressos comprados e a entrada validada na porta.",
};

/**
 * Layout raiz: só o documento. A casca visível fica um nível abaixo, e são
 * três, diferentes de propósito — `(site)` tem masthead com navegação,
 * `(entrada)` não tem (quem está tentando entrar não deve ver links para "Meus
 * ingressos" e "Minha conta", que ele ainda não pode abrir), e `/portaria` tem
 * navegação própria, de dois itens, numa coluna estreita.
 *
 * **A terceira não é grupo de rotas, e é o certo** (Story 5.1). `(site)` e
 * `(entrada)` existem porque agrupam caminhos de topo diferentes sob uma casca
 * comum; a da portaria tem tudo sob `/portaria`, e o segmento já é o grupo.
 *
 * Grupo de rotas em vez de segundo layout raiz: a documentação do Next avisa
 * que navegar entre dois layouts raiz força recarga completa da página, e
 * `not-found.tsx` precisaria virar `global-not-found` (experimental) por não
 * ter mais layout de onde herdar.
 *
 * ⚠️ **`data-scroll-behavior="smooth"` é o que faz a tela nova começar no topo**
 * (13/08/2026), e ele não é decoração: é o atributo que o **Next 16** passou a
 * exigir para voltar a fazer o que o 15 fazia sozinho.
 *
 * O `globals.css` declara `html { scroll-behavior: smooth }` para o link com
 * âncora da tela de publicar (`#passo-2`). Até o Next 15, o roteador **anulava**
 * essa regra durante uma navegação — trocava para `auto`, saltava para o topo e
 * devolvia o `smooth` —, e é por isso que ninguém tinha reparado. O Next 16
 * deixou de anular por padrão (`docs/01-app/02-guides/upgrading/version-16.md`,
 * seção *Scroll Behavior Override*), então o salto para o topo virou uma
 * **animação**, e ela corre contra a renderização da tela de destino: quando o
 * conteúdo chega no meio do caminho, a rolagem para onde estiver e a pessoa cai
 * numa página com o cabeçalho fora da vista. Era intermitente porque é corrida.
 *
 * Sintoma clássico: entrar pelo login com a tela anterior rolada para baixo e
 * chegar em `/` no meio da programação. O atributo devolve o salto instantâneo
 * na navegação **sem** custar o `smooth` das âncoras, que continua valendo.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
