/**
 * Cliente HTTP único do frontend: toda chamada à API passa por aqui, e todo
 * caminho começa com `/api` — o proxy de `next.config.ts` reescreve para o
 * backend do lado do servidor. Nenhum componente monta URL de backend por
 * conta própria.
 *
 * **Só o caminho do navegador** (`fetch` de Client Component) mora aqui. A
 * busca a partir de Server Component precisa de URL absoluta e de repassar o
 * cookie lido por `cookies()`, e vive em `src/lib/sessao.ts` — separado porque
 * este arquivo é importado por componentes `"use client"`, e `next/headers`
 * num módulo do cliente quebra o build.
 */

export class ErroDaApi extends Error {
  codigo: string;

  constructor(codigo: string) {
    super(codigo);
    this.codigo = codigo;
  }
}

export async function chamarApi<T>(
  caminho: string,
  opcoes?: RequestInit,
): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    ...opcoes,
    headers: {
      "Content-Type": "application/json",
      ...opcoes?.headers,
    },
  });

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ErroDaApi(corpo?.erro?.codigo ?? "ERRO_DESCONHECIDO");
  }

  if (resposta.status === 204) {
    return undefined as T;
  }

  return resposta.json() as Promise<T>;
}
