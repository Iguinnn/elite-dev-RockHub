import { cache } from "react";

import { API_URL, cabecalhoDeSessao } from "./servidor";

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
    // Sem cookie não há o que perguntar. A raiz é pública e visitante é o caso
    // comum: não vale uma ida à rede para ouvir 401.
    const cabecalho = await cabecalhoDeSessao();
    if (!cabecalho) return null;

    try {
      const resposta = await fetch(`${API_URL}/auth/eu`, {
        headers: cabecalho,
        cache: "no-store",
      });
      // 401 aqui é resposta esperada, não falha: cookie velho ou adulterado.
      if (!resposta.ok) return null;
      return (await resposta.json()) as UsuarioDaSessao;
    } catch (erro) {
      // Backend fora do ar não derruba a página: a tela renderiza como
      // visitante. É o comportamento certo para a raiz, que é pública.
      //
      // Mas o `catch` mudo era o problema: ele achatava "sem sessão", "sessão
      // inválida" e "API inalcançável" numa coisa só. Quem tem cookie válido e
      // pega uma instabilidade da Railway vê o masthead voltar para `Entrar` e
      // a `/conta` rebater para o login, conclui que a sessão caiu, e não há
      // pista nenhuma — nem na tela, nem no console, nem no Network. O
      // comportamento continua o mesmo; o que muda é que agora ele deixa
      // rastro no log do servidor.
      console.error(`[RockHub] Não foi possível ler a sessão em ${API_URL}:`, erro);
      return null;
    }
  },
);
