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

/**
 * ⚠️ **O fuso é fixo, e é isto que impede a mesma publicação de aparecer com
 * duas datas.** Achado no code review da Epic 2.
 *
 * `Intl.DateTimeFormat` sem `timeZone` usa o fuso **do runtime**. As telas de
 * "Meus eventos" são Server Components, e o runtime delas é o container da
 * Vercel, cujo `TZ` é UTC — enquanto a confirmação da publicação renderiza no
 * navegador, em `America/Sao_Paulo`. Um show às 21h de 14/08 é gravado certo
 * (`2026-08-15T00:00:00Z`) e aparecia como "14 de agosto, 21h00" numa tela e
 * "15 de agosto, 00h00" na outra. Em desenvolvimento nunca dava: a máquina e o
 * servidor são o mesmo fuso.
 *
 * **Por que fixo e não "o fuso de quem lê"**, que é o que o AD-11 pede ao pé da
 * letra: num Server Component não existe "quem lê" — não há navegador do outro
 * lado no momento de formatar. As saídas seriam renderizar a data no cliente
 * (e conviver com divergência de hidratação) ou fixar. Como o catálogo já é
 * `countryCode=BR` e todo show deste produto acontece no Brasil, fixar diz a
 * verdade e custa uma linha. O dia em que houver show fora do país, esta
 * constante é o único lugar a mudar.
 */
const FUSO = "America/Sao_Paulo";

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
    timeZone: FUSO,
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: FUSO,
  })
    .format(instante)
    .replace(":", "h");
  return `${dia}, ${hora}`;
}

/**
 * ISO-8601 → as três partes da data como a fila de "Meus eventos" as mostra,
 * separadas porque cada uma tem tipografia própria: `{ dia: "15", mes: "ago",
 * ano: "2026" }`.
 *
 * **Mora aqui, e não na tela, para o `FUSO` continuar existindo num lugar só.**
 * As três formatações nasceram inline em `organizador/eventos/page.tsx` e foram
 * justamente as que passaram despercebidas quando o `timeZone` entrou no resto
 * do módulo. Uma cópia da regra é uma chance de a próxima tela repetir o erro.
 */
export function partesDaData(iso: string): { dia: string; mes: string; ano: string } {
  const instante = new Date(iso);
  const parte = (opcoes: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat("pt-BR", { ...opcoes, timeZone: FUSO }).format(instante);

  return {
    dia: parte({ day: "2-digit" }),
    // O `Intl` do pt-BR devolve "ago." com ponto; a fila é versalete e o ponto
    // vira sujeira entre o mês e o ano.
    mes: parte({ month: "short" }).replace(".", ""),
    ano: parte({ year: "numeric" }),
  };
}

/** ISO-8601 → `"Publicado em 11 de agosto, 17h22"`. Sem o ano: é recente. */
export function momentoDaPublicacao(iso: string): string {
  const instante = new Date(iso);
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
    timeZone: FUSO,
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: FUSO,
  })
    .format(instante)
    .replace(":", "h");
  return `Publicado em ${dia}, ${hora}`;
}
