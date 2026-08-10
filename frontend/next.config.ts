import type { NextConfig } from "next";

// Lido em tempo de build (a Vercel compila as rotas no `next build`). Trocar
// a variável no painel depois não muda o proxy sem um redeploy.
const destinoDaApi = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  rewrites() {
    return [{ source: "/api/:caminho*", destination: `${destinoDaApi}/:caminho*` }];
  },
};

export default nextConfig;
