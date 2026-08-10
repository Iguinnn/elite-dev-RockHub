import type { Metadata } from "next";

import Masthead from "@/components/Masthead";

import "./globals.css";

export const metadata: Metadata = {
  title: "RockHub",
  description:
    "A programação de shows, os ingressos comprados e a entrada validada na porta.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="conteudo">
          <Masthead />
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
