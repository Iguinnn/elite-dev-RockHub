import { horaDeEntrada } from "@/lib/formato";
import { type ResultadoDaValidacao } from "@/lib/validacao";

import estilos from "./Veredito.module.css";

/**
 * O veredito da porta, legível a três metros (Story 5.4).
 *
 * Saiu de dentro do `Leitor.tsx`, onde nasceu como a função `Veredicto` da 5.3 —
 * a grafia certa veio junto. Ele é arquivo próprio pelo mesmo critério do
 * `AvisoDeErro`: o que se protege aqui não é reuso (só uma tela desenha isto),
 * é a **regra dos três canais**, que some se ela virar comentário no meio de um
 * componente de 500 linhas.
 *
 * ⚠️ **Os três canais entram juntos — cor, palavra e símbolo (UX-DR5).** A regra
 * proíbe transmitir informação **só** por cor; meio caminho é pior que nenhum,
 * porque um veredito colorido sem símbolo é exatamente o que ela veta. Se algum
 * dia o símbolo sair daqui, a cor sai junto.
 *
 * ⚠️ **Duas tintas, e não quatro** (decisão do Igor, contra o AC da 5.4 e a
 * tabela do `EXPERIENCE.md`): `--verde` no `VALIDO`, `--brasa` nos outros três.
 * Na porta a pergunta é binária — essa pessoa entra ou não entra. Quatro
 * tinturas obrigam quem está com a fila esperando a decodificar qual das quatro
 * apareceu antes de saber o que fazer. A distinção entre os três motivos de
 * recusa continua inteira na palavra e no símbolo, que é onde ela é lida de
 * perto, quando a pessoa reclama e é preciso explicar. O que encolheu foi a
 * cardinalidade de um canal, não a quantidade deles.
 *
 * ⚠️ **A tinta é escolhida no CSS, por `data-veredito`** — nunca um
 * `estilos[resultado]` calculado em JavaScript. Aquele o `tsc` não confere, e
 * quebra em silêncio no dia em que um nome de classe some do CSS Module.
 *
 * ⚠️ **Nada some sozinho.** Não existe `setTimeout` neste arquivo nem no
 * `Leitor`: quem substitui o veredito é a validação seguinte. A portaria precisa
 * poder olhar duas vezes com a fila esperando.
 *
 * ⚠️ **`EVENTO_ERRADO` não nomeia o outro show**, e é a única linha em que esta
 * tela se afasta da tabela do `EXPERIENCE.md` (decisão do Igor). Devolver o nome
 * de um evento a uma portaria que não foi escalada nele é o que o AD-7 existe
 * para impedir — e a resposta da API nem carrega o dado, então não há como esta
 * tela mudar de ideia sozinha.
 */
export default function Veredito({
  resultado,
}: {
  resultado: ResultadoDaValidacao;
}) {
  return (
    // O atributo é o que pinta o bloco; a classe é sempre a mesma.
    <div className={estilos.veredito} data-veredito={resultado.resultado}>
      {SIMBOLO[resultado.resultado]}
      <p className={estilos.palavra}>{PALAVRA[resultado.resultado]}</p>
      <p className={estilos.detalhe}>{detalhe(resultado)}</p>
    </div>
  );
}

/** As quatro palavras do `EXPERIENCE.md`, sem sinônimo e sem tradução livre. */
const PALAVRA: Record<ResultadoDaValidacao["resultado"], string> = {
  VALIDO: "VÁLIDO",
  INVALIDO: "INVÁLIDO",
  JA_UTILIZADO: "JÁ UTILIZADO",
  EVENTO_ERRADO: "EVENTO ERRADO",
};

/**
 * O terceiro canal.
 *
 * ⚠️ **SVG, e não caractere de fonte.** `✓ ✕ ↺ ⤫` como texto dependem de haver o
 * glifo instalado no aparelho: os três primeiros existem em qualquer lugar, mas
 * o `⤫` é um caractere matemático e **pode virar retângulo vazio** no Android ou
 * num Windows sem fonte de símbolos — justamente no canal que existe para a
 * informação não depender de cor. Quatro `<svg>` inline não têm esse risco.
 *
 * ⚠️ **`EVENTO_ERRADO` é o X dentro do círculo, e a diferença de silhueta é o
 * ponto.** O `⤫` do documento é desenhado igual a um `✕` em quase toda fonte —
 * copiá-lo ao pé da letra apagaria a distinção entre `INVALIDO` e
 * `EVENTO_ERRADO` bem no canal que a decisão das duas tintas acabou de tornar o
 * mais importante. A três metros o que se lê é a silhueta: dois traços soltos
 * contra um disco fechado se separam; dois X quase iguais, não.
 *
 * `aria-hidden` nos quatro: quem anuncia é a palavra, dentro do `aria-live` do
 * `Leitor`. Sem isto o leitor de tela leria o símbolo e a palavra em sequência,
 * dizendo a mesma coisa duas vezes com a fila andando.
 *
 * `stroke="currentColor"` é o que faz o símbolo herdar a tinta do bloco — a cor
 * continua morando num lugar só, o `--tinta` do CSS.
 */
const SIMBOLO: Record<ResultadoDaValidacao["resultado"], React.ReactNode> = {
  VALIDO: (
    <Marca>
      <path d="M4 12.5 9.5 18 20 6" />
    </Marca>
  ),
  INVALIDO: (
    <Marca>
      <path d="M6 6l12 12M18 6L6 18" />
    </Marca>
  ),
  // A seta circular do `↺`: o arco aberto mais a farpa que fecha a volta.
  JA_UTILIZADO: (
    <Marca>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.49-6.01L3.5 7.5" />
      <path d="M3.5 3v4.5H8" />
    </Marca>
  ),
  EVENTO_ERRADO: (
    <Marca>
      <circle cx="12" cy="12" r="9" />
      <path d="M15.5 8.5l-7 7M8.5 8.5l7 7" />
    </Marca>
  ),
};

/**
 * A moldura comum dos quatro símbolos.
 *
 * **44px porque é o piso de alvo do UX-DR6**, e aqui ele não é alvo de toque —
 * é a medida que o projeto já usa para "grande o bastante para se acertar sem
 * mirar", que é a mesma pergunta a três metros. `stroke-width` de 2,5 no
 * `viewBox` de 24 dá um traço de ~4,6px na tela: grosso o suficiente para o
 * símbolo não sumir no breu.
 */
function Marca({ children }: { children: React.ReactNode }) {
  return (
    <svg
      className={estilos.simbolo}
      viewBox="0 0 24 24"
      width="44"
      height="44"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/**
 * O detalhe de cada veredito, montado dos campos que vieram.
 *
 * ⚠️ **`filter(Boolean)` nos dois primeiros casos, e não interpolação direta.**
 * `titular_nome` e `setor_nome` são anuláveis no contrato; sem o filtro, um
 * campo ausente imprimiria " · " solto ou a palavra "null" no meio da frase que
 * a portaria lê em voz alta — o mesmo cuidado que a `cidade` recebe na lista de
 * turnos.
 */
function detalhe(resultado: ResultadoDaValidacao): string {
  switch (resultado.resultado) {
    case "VALIDO":
      return (
        [resultado.setor_nome, resultado.titular_nome]
          .filter(Boolean)
          .join(" · ") || "Pode entrar."
      );
    case "JA_UTILIZADO":
      return (
        [
          resultado.entrada_em && `Entrou às ${horaDeEntrada(resultado.entrada_em)}`,
          resultado.titular_nome,
        ]
          .filter(Boolean)
          .join(" · ") || "Este ingresso já foi utilizado."
      );
    case "EVENTO_ERRADO":
      // Sem o nome do outro show, de propósito — ver o docstring acima.
      return "Este ingresso é de outro show.";
    case "INVALIDO":
      // A frase é a do `EXPERIENCE.md`, e ela vale também para o código que não
      // é de ingresso nenhum: sem linha no banco, não há assinatura que confira.
      return "Assinatura não confere.";
  }
}
