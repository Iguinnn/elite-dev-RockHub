import type { ContagensDoTurno } from "@/lib/validacao";

import estilos from "./ContadorDoTurno.module.css";

/**
 * O movimento do turno, numa faixa de quatro colunas (Story 5.6).
 *
 * ⚠️ **Nenhum dos quatro é grande sozinho — quem tem presença é o conjunto**
 * (decisão do Igor, na tela). As duas formas anteriores erravam pelos dois lados:
 * `ENTRADAS 41` em corpo grande dentro do cabeçalho virava o segundo maior
 * elemento da tela e disputava leitura com o nome do show; encolhido para caber
 * ao lado dos rótulos, sumia. Enquanto o número morasse **dentro** do bloco do
 * título, todo tamanho era escolher entre sumir e competir.
 *
 * Em faixa própria, entre o fio do cabeçalho e o botão da câmera, ele tem
 * território — e os quatro números passam a ser lidos como um painel, que é o que
 * eles são. De quebra, as três recusas deixam de ser nota de rodapé em versalete
 * e ganham o mesmo corpo das entradas.
 *
 * **A hierarquia passou da medida para a cor.** `ENTRADAS` é a pergunta do turno
 * e vem em `--cal`; as três recusas são a segunda pergunta e vêm em `--fumaca`,
 * no mesmo corpo. Diferenciar por tamanho desmontaria a grade que a decisão
 * acabou de comprar.
 *
 * ⚠️ **Ele fica FORA da região `aria-live="assertive"` do `<Leitor>`, e isso não
 * é detalhe de posição.** Dentro dela, cada validação faria o leitor de tela
 * anunciar *"VÁLIDO. Pista · Igor Duarte. 41 entradas. Inválidos 2…"* — o dado
 * operacional atropelando o veredito, que é a única coisa que precisa ser ouvida
 * com a fila andando. O número continua legível para quem usa leitor de tela: ele
 * está no DOM e se lê navegando. O que ele não faz é interromper.
 *
 * ⚠️ **Os números são do evento inteiro, não desta conta.** Uma validação da
 * outra porta aparece aqui na minha próxima leitura — sem polling e sem
 * WebSocket, que é rápido o suficiente para o único uso que o número tem.
 *
 * **Nenhuma transição e nenhum contador animado.** Um número que sobe de 40 para
 * 41 girando é movimento no meio da fila, e o `EXPERIENCE.md#Carregando` não abre
 * exceção para enfeite — a única do produto é a espera de 6s do checkout.
 */
export default function ContadorDoTurno({
  contagens,
}: {
  contagens: ContagensDoTurno;
}) {
  const { entradas, recusas } = contagens;

  return (
    <div className={estilos.contador}>
      {/* `data-destaque` no elemento, e o peso decidido no CSS — nunca um
          `estilos[chave]` calculado aqui, que o `tsc` não confere e que quebra em
          silêncio no dia em que um nome de classe some do CSS Module. */}
      <Coluna rotulo="Entradas" valor={entradas} destaque />
      <Coluna rotulo="Inválidos" valor={recusas.invalidos} />
      <Coluna rotulo="Já usados" valor={recusas.ja_utilizados} />
      <Coluna rotulo="Outro show" valor={recusas.evento_errado} />
    </div>
  );
}

/**
 * Uma coluna: etiqueta em cima, número embaixo.
 *
 * ⚠️ **As etiquetas são curtas por medida, não por gosto.** Em 360px de largura
 * cada coluna fica com ~72px, e `JÁ UTILIZADOS` por extenso não cabe numa linha
 * — quebrado em duas, ele desalinharia os quatro números entre si e desfaria a
 * grade. `OUTRO SHOW` segue o mesmo critério e é, de quebra, o que a portaria diz
 * em voz alta; nenhuma das duas nomeia **qual** show, que o AD-7 não permite e a
 * resposta da API nem carrega.
 *
 * **Os quatro aparecem sempre, inclusive zerados.** Esconder o que está em zero
 * faria a faixa mudar de forma no meio do turno, e faria "não houve recusa"
 * parecer "o sistema não conta isso". Zero é a informação mais comum aqui, e é
 * uma informação boa.
 */
function Coluna({
  rotulo,
  valor,
  destaque = false,
}: {
  rotulo: string;
  valor: number;
  destaque?: boolean;
}) {
  return (
    <div className={estilos.coluna}>
      <span className={estilos.rotulo}>{rotulo}</span>
      <span className={estilos.numero} data-destaque={destaque || undefined}>
        {valor}
      </span>
    </div>
  );
}
