import { cookies } from "next/headers";
import { cache } from "react";

/**
 * Leitura da sessão **do lado do servidor**. Só Server Components entram aqui.
 *
 * Por que não fica dentro de `src/lib/api.ts`: aquele módulo é importado pelos
 * formulários, que são `"use client"`. `next/headers` num módulo que chega ao
 * bundle do navegador é erro de build — a fronteira entre servidor e cliente
 * aqui é física, não convenção. Daí dois arquivos.
 *
 * O estado de sessão do frontend **nasce e morre no servidor**: não há contexto
 * React de usuário, não há `localStorage`, não há estado global. A página
 * pergunta ao servidor, e o servidor pergunta ao backend, que é quem tem o
 * segredo do token. Sessão duplicada no cliente é a origem clássica da tela que
 * continua mostrando o usuário antigo depois do logout.
 */

// URL absoluta, e a mesma variável do `next.config.ts`. O `rewrite` de `/api/*`
// é do navegador: um `fetch("/api/…")` daqui não tem origem para resolver.
const API = process.env.API_URL ?? "http://localhost:8000";

// Acoplamento assumido: o mesmo nome está em `cookie_sessao_nome`, no
// `backend/app/core/config.py`. Trocar lá exige trocar aqui.
const NOME_DO_COOKIE = "rockhub_sessao";

export type UsuarioDaSessao = {
  id: string;
  nome: string;
  email: string;
  papel: "ORGANIZADOR" | "CLIENTE" | "PORTARIA";
};

/**
 * Quem está logado nesta requisição, ou `null`.
 *
 * `cache()` do React, e não `unstable_cache` nem revalidação por tempo: a
 * deduplicação que interessa é **dentro de uma requisição**. O masthead e a
 * `/conta` chamam esta função na mesma renderização, e o backend é consultado
 * uma vez só.
 */
export const obterUsuarioDaSessao = cache(
  async (): Promise<UsuarioDaSessao | null> => {
    const sessao = (await cookies()).get(NOME_DO_COOKIE);
    // Sem cookie não há o que perguntar. A raiz é pública e visitante é o caso
    // comum: não vale uma ida à rede para ouvir 401.
    if (!sessao) return null;

    try {
      const resposta = await fetch(`${API}/auth/eu`, {
        // O `fetch` do servidor não herda cookie do pedido que está sendo
        // atendido. Repassar à mão é o que separa "renderiza logado" de
        // "renderiza deslogado sem erro nenhum para investigar".
        headers: { Cookie: `${sessao.name}=${sessao.value}` },
        cache: "no-store",
      });
      // 401 aqui é resposta esperada, não falha: cookie velho ou adulterado.
      if (!resposta.ok) return null;
      return (await resposta.json()) as UsuarioDaSessao;
    } catch {
      // Backend fora do ar não derruba a página: a tela renderiza como
      // visitante. É o comportamento certo para a raiz, que é pública.
      return null;
    }
  },
);
