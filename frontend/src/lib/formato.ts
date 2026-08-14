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
 * ⚠️ **`reaisParaCentavos` e `hojeEmSaoPaulo` chegaram em 13/08/2026**, com a
 * tela de editar evento. O docstring dizia que a primeira ficaria de fora "por
 * não ter consumidor de servidor", e isso continua verdade — o que mudou é que
 * ela passou a ter **dois** consumidores de cliente, e as duas trazem coisa que
 * não se copia impunemente: a `reaisParaCentavos` carrega a guarda de
 * `Number.isSafeInteger` que o code review da Epic 2 acrescentou, e a
 * `hojeEmSaoPaulo` carrega o `FUSO` — que é justamente o que este módulo existe
 * para manter num lugar só. Uma cópia de qualquer uma das duas é a chance de a
 * próxima tela repetir um bug que já foi corrigido.
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

/**
 * Reais digitados → centavos inteiros. `null` quando não dá para ter certeza.
 *
 * A inversa da de cima, e a fronteira onde o decimal morre: a API só conhece
 * `preco_centavos: int` (AD-11), e nenhum número com casa atravessa o contrato.
 *
 * ⚠️ **Ela nasceu no `FormularioPublicacao` e veio para cá quando a tela de
 * editar virou o segundo consumidor** (13/08/2026). Não é faxina: a guarda de
 * `Number.isSafeInteger` abaixo foi um achado de code review, e uma segunda
 * cópia dela é uma segunda chance de alguém escrever a versão sem a guarda.
 */
export function reaisParaCentavos(valor: string): number | null {
  const bruto = valor.trim();
  // Com vírgula, ela é o separador decimal e o ponto é milhar ("1.234,50").
  // Sem vírgula, o ponto é o decimal ("120.50"). Assim "1.234" não vira
  // 123.400 por adivinhação — ele falha na regra abaixo e vira erro na tela.
  const normalizado = bruto.includes(",")
    ? bruto.replace(/\./g, "").replace(",", ".")
    : bruto;

  if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;

  const centavos = Math.round(Number(normalizado) * 100);
  // ⚠️ **`Math.round` mente em silêncio acima de `MAX_SAFE_INTEGER`**, e o
  // regex acima aceita qualquer quantidade de dígitos. Sem esta guarda,
  // `999999999999999,99` era enviado **arredondado errado** e gravado sem erro
  // nenhum — dinheiro corrompido sem ninguém saber, que é exatamente o que o
  // AD-11 existe para impedir. `null` devolve a mensagem de preço inválido, que
  // é a resposta certa para um número que o JavaScript não sabe representar.
  if (!Number.isSafeInteger(centavos)) return null;
  return centavos;
}

/**
 * Hoje no fuso do produto, em `AAAA-MM-DD` — o formato que o `min` do
 * `<input type="date">` exige.
 *
 * **Em São Paulo, e não no fuso do navegador**, pelo mesmo motivo do `FUSO`
 * acima: quem publica está no Brasil, e um organizador viajando não deve ver o
 * seletor liberar ontem ou barrar hoje.
 *
 * ⚠️ **Veio do `FormularioPublicacao` junto com a de cima**, e aqui o argumento
 * é ainda mais forte: lá ela repetia a string `"America/Sao_Paulo"` fora do
 * `FUSO`, que é a **segunda fonte** do fuso que este módulo inteiro existe para
 * impedir (ver o comentário do `FUSO`). Agora é uma só.
 */
export function hojeEmSaoPaulo(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: FUSO }).format(new Date());
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

/**
 * ISO-8601 → as quatro partes da data como a **fila da programação pública** as
 * mostra: `{ diaDaSemana: "sex", dia: "15", mesEAno: "ago 2026", hora: "22h30" }`.
 *
 * **Não é a `partesDaData` com outro nome.** As duas filas deste produto são
 * primas, não gêmeas: a do organizador é um inventário e mostra `15 ago 2026`
 * em três blocos de mono, todos do mesmo tamanho; a pública é uma linha de
 * jornal, e a tipografia separa o que decide de o que situa
 * (`DESIGN.md#Typography`) — o dia em serifada grande, e dia da semana, mês,
 * ano e hora em mono versalete ao redor dele.
 *
 * ⚠️ **`mesEAno` entrou depois, e a ausência dele era um defeito.** A Story 3.1
 * devolvia só `diaDaSemana`, `dia` e `hora`, argumentando que a programação
 * pública "só mostra o que ainda vai acontecer, então o ano é sempre o mesmo ou
 * o próximo". Isso está errado por dois motivos que a primeira tela com quatro
 * eventos reais mostrou: sem o mês, `14`, `12` e `23` não dizem qual vem antes,
 * e a coluna que deveria ser a âncora de leitura da lista vira decoração; e
 * "sempre o mesmo ou o próximo" ainda são **dois** anos diferentes — havia um
 * show em setembro de 2026 e outro em setembro de 2027 na mesma tela, idênticos.
 * O ano vem sempre, e não só quando difere do atual: uma regra que muda com o
 * relógio produziria duas formas para a mesma coluna, e ninguém saberia qual
 * está certa ao olhar uma captura de tela.
 *
 * **Mora aqui, e não na tela, para o `FUSO` continuar existindo num lugar só.**
 * As três formatações inline da fila de "Meus eventos" foram exatamente as que
 * passaram despercebidas quando o `timeZone` entrou no resto do módulo, e a
 * mesma publicação apareceu com duas datas diferentes. Uma cópia da regra é uma
 * chance de a próxima tela repetir o erro.
 */
export function partesDaFilaPublica(iso: string): {
  diaDaSemana: string;
  dia: string;
  mesEAno: string;
  hora: string;
} {
  const instante = new Date(iso);
  const parte = (opcoes: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat("pt-BR", { ...opcoes, timeZone: FUSO }).format(instante);

  return {
    // O `Intl` do pt-BR devolve "sex." com ponto, como já devolvia "ago." em
    // `partesDaData`. Em versalete o ponto vira sujeira.
    diaDaSemana: parte({ weekday: "short" }).replace(".", ""),
    dia: parte({ day: "2-digit" }),
    // Uma string só, e não `mes` e `ano` separados como na `partesDaData`: lá
    // os três blocos têm tipografia própria, aqui os dois ocupam a mesma linha
    // e nunca aparecem um sem o outro. Devolvê-los partidos daria à tela uma
    // escolha que ela não tem.
    mesEAno: `${parte({ month: "short" }).replace(".", "")} ${parte({
      year: "numeric",
    })}`,
    hora: parte({ hour: "2-digit", minute: "2-digit" }).replace(":", "h"),
  };
}

/**
 * ISO-8601 → o kicker da **chamada principal**, com o dia da semana junto:
 * `"sexta, 15 de agosto de 2026, 22h30"` (Story 3.3). A tela o põe em versalete.
 *
 * **Não é a `dataPorExtenso` com um parâmetro a mais**, e a diferença é o dia da
 * semana. Um `comDiaDaSemana?: boolean` naquela função lhe daria **duas** saídas
 * e obrigaria as quatro telas do organizador que já a chamam a declarar qual
 * delas querem — para uma escolha que só esta tela faz. Duas funções nomeadas
 * dizem o que devolvem; uma função com bandeira exige ler a implementação.
 * `dataPorExtenso` fica exatamente como está.
 *
 * **Por que "sexta" e não "sexta-feira"**: o `Intl` do pt-BR devolve a forma
 * longa com o sufixo, e numa capa de show o sufixo é ruído — o protótipo escreve
 * `Sexta, 14 de agosto`. O corte é no hífen, e ele é seguro para os sete dias:
 * sábado e domingo não têm sufixo nenhum e atravessam inteiros.
 *
 * ⚠️ **Mora aqui, e não inline na tela**, pelo motivo de sempre: o `FUSO` fixo é
 * deste módulo, e as formatações inline foram exatamente as que passaram
 * despercebidas quando o `timeZone` entrou (code review da Epic 2) — a mesma
 * publicação apareceu com duas datas diferentes.
 */
export function dataDaChamada(iso: string): string {
  const instante = new Date(iso);
  const parte = (opcoes: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat("pt-BR", { ...opcoes, timeZone: FUSO }).format(instante);

  // O `.replace(".", "")` acompanha o corte no hífen pelo mesmo motivo das
  // outras duas funções daqui: em versalete o ponto vira sujeira. A forma longa
  // do pt-BR não o traz hoje, e a linha custa nada se um dia trouxer.
  const diaDaSemana = parte({ weekday: "long" }).split("-")[0].replace(".", "");
  const dia = parte({ day: "numeric", month: "long", year: "numeric" });
  const hora = parte({ hour: "2-digit", minute: "2-digit" }).replace(":", "h");

  return `${diaDaSemana}, ${dia}, ${hora}`;
}

/**
 * ISO-8601 → só a hora: `"20h51"` (Story 4.1).
 *
 * A hora da entrada (`ingresso.usado_em`) é TIMESTAMPTZ em UTC (AD-11) e
 * chega ISO-8601 com offset; formatá-la aqui, com o mesmo `FUSO` fixo das
 * outras funções deste módulo, é o que impede o mesmo instante de aparecer
 * com duas horas em duas telas — o defeito que a `dataPorExtenso` já corrigiu
 * uma vez para data completa.
 */
export function horaDeEntrada(iso: string): string {
  const instante = new Date(iso);
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: FUSO,
  })
    .format(instante)
    .replace(":", "h");
}

/**
 * ISO-8601 → os dois campos do formulário: `{ data: "2026-09-13", hora: "21:00" }`
 * (13/08/2026, tela de editar evento).
 *
 * Os formatos são os que `<input type="date">` e `<input type="time">` exigem —
 * não são para ler, são para preencher.
 *
 * ⚠️ **No `FUSO`, e não no fuso do navegador, e a razão aqui é outra das deste
 * módulo.** O formulário de edição é uma ilha `"use client"`, e ilha
 * `"use client"` **também renderiza no servidor** antes de hidratar: com
 * `instante.getHours()` o valor sairia em UTC no HTML da Vercel e em horário
 * local no navegador, que é divergência de hidratação — o React reclama e o
 * campo pode ficar com o valor errado. Com `Intl` e `timeZone` fixo, os dois
 * lados calculam a mesma coisa.
 */
export function partesDoFormulario(iso: string): { data: string; hora: string } {
  const instante = new Date(iso);
  return {
    // `en-CA` é o truque de sempre para `AAAA-MM-DD` sem montar a string à mão.
    data: new Intl.DateTimeFormat("en-CA", { timeZone: FUSO }).format(instante),
    // `hourCycle: "h23"` e não o padrão: sem ele, meia-noite sai como `24:00`
    // em algumas combinações de locale, e o `<input type="time">` rejeita.
    hora: new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
      timeZone: FUSO,
    }).format(instante),
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
