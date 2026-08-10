import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "RockHub",
  description:
    "A programação de shows, os ingressos comprados e a entrada validada na porta.",
};

/**
 * Layout raiz: só o documento. A casca visível fica nos grupos de rotas, que
 * são duas e diferentes de propósito — `(site)` tem masthead com navegação,
 * `(entrada)` não tem. Quem está tentando entrar não deve ver links para
 * "Meus ingressos" e "Minha conta", que ele ainda não pode abrir.
 *
 * Grupo de rotas em vez de segundo layout raiz: a documentação do Next avisa
 * que navegar entre dois layouts raiz força recarga completa da página, e
 * `not-found.tsx` precisaria virar `global-not-found` (experimental) por não
 * ter mais layout de onde herdar.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
