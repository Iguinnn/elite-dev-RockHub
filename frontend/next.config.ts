import type { NextConfig } from "next";

// Lido em tempo de build (a Vercel compila as rotas no `next build`). Trocar
// a variável no painel depois não muda o proxy sem um redeploy.
const destinoDaApi = process.env.API_URL ?? "http://localhost:8000";

// O padrão `localhost:8000` é o valor certo em desenvolvimento e um erro mudo
// em produção: o proxy é congelado no build apontando para uma máquina que não
// existe do lado da Vercel, a tela abre, o formulário envia e nada acontece.
//
// O aviso **não** derruba o build de propósito. O simétrico do backend seria
// falhar (a `Settings` recusa o JWT_SECRET de exemplo em produção), mas ali a
// consequência de subir é uma sessão forjável, e aqui é um Preview quebrado —
// e Preview que não sobe é pior que Preview quebrado, pelo mesmo argumento que
// levou a definir a variável para Production E Preview na Story 1.9.
if (process.env.NODE_ENV === "production" && !process.env.API_URL) {
  console.warn(
    "\n[RockHub] ⚠️  API_URL não está definida neste build.\n" +
      "   O proxy /api/* vai apontar para http://localhost:8000, que não\n" +
      "   existe no servidor — o login vai falhar em silêncio.\n" +
      "   Defina API_URL no painel da Vercel (Production E Preview), sem\n" +
      "   barra no fim e com https://, e refaça o deploy.\n",
  );
}

const nextConfig: NextConfig = {
  rewrites() {
    return [{ source: "/api/:caminho*", destination: `${destinoDaApi}/:caminho*` }];
  },
};

export default nextConfig;
