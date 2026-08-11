/**
 * Data, hora e dinheiro em português — as três formatações que atravessam a
 * fronteira servidor/cliente.
 *
 * **Por que este arquivo existe, e por que não é faxina.** As três nasceram
 * dentro do `FormularioPublicacao.tsx`, que é uma ilha `"use client"`. Quando
 * as telas de "Meus eventos" (Story 2.6) precisaram das mesmas formatações,
 * importá-las de lá não era uma opção ruim — era uma opção **impossível**: o
 * Next transforma cada export de um módulo `"use client"` numa *client
 * reference*, e chamá-la de um Server Component estoura em tempo de execução,
 * não em build. A fronteira do React Server Components não é convenção, é
 * limite de execução.
 *
 * As duas saídas erradas eram copiar as funções para as telas novas — segunda
 * fonte para o mesmo formato de data, e o dia em que uma mudasse ninguém
 * saberia qual está certa — e marcar as telas novas como `"use client"`, que é
 * jogar fora o Server Component por causa de um `Intl.DateTimeFormat`.
 *
 * **Módulo puro, e é isso que o torna possível**: nenhum `"use client"`,
 * nenhum import de `next/headers`. Ele roda dos dois lados da fronteira porque
 * não depende de nenhum dos dois. É o oposto do `servidor.ts`, cujo import de
 * `next/headers` é justamente o que o prende ao servidor.
 *
 * `reaisParaCentavos` **não** veio junto: ela é do formulário, converte o que
 * uma pessoa digitou e não tem consumidor de servidor. Mover tudo "já que
 * estou aqui" seria escopo que ninguém pediu.
 */

/** Centavos inteiros → reais com duas casas, sem o "R$". Ex.: `12000` → `"120,00"`. */
export function centavosParaReais(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** ISO-8601 → `"15 de agosto de 2026, 21h00"`. */
export function dataPorExtenso(iso: string): string {
  const instante = new Date(iso);
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })
    .format(instante)
    .replace(":", "h");
  return `${dia}, ${hora}`;
}

/** ISO-8601 → `"Publicado em 11 de agosto, 17h22"`. Sem o ano: é recente. */
export function momentoDaPublicacao(iso: string): string {
  const instante = new Date(iso);
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })
    .format(instante)
    .replace(":", "h");
  return `Publicado em ${dia}, ${hora}`;
}
