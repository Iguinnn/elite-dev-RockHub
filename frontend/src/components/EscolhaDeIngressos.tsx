"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import estilos from "@/app/(site)/eventos/[id]/page.module.css";
import Botao from "@/components/Botao";
import Toast from "@/components/Toast";
import { ErroDaApi, chamarApi } from "@/lib/api";
import { centavosParaReais } from "@/lib/formato";
import type { EventoPublico, SetorPublico } from "@/lib/programacao";
import type { ReservaSaida } from "@/lib/reservas";

/**
 * A lista de setores com o seletor de quantidade e o rodapé do total — **a
 * primeira ilha `"use client"` do lado público** (Story 3.4).
 *
 * **Por que ela é uma ilha.** Até aqui todo `"use client"` do projeto está em
 * formulário atrás de login (`FormularioLogin`, `FormularioCadastro`,
 * `FormularioPublicacao`) ou em navegação (`NavLink`, `BotaoSair`). O seletor de
 * quantidade é o caso que a tabela de convenções do `ARCHITECTURE-SPINE.md` nomeia
 * por extenso: apertar `+` muda um número na tela sem ir ao servidor, e não existe
 * jeito de fazer isso sem JavaScript no navegador.
 *
 * ⚠️ **Por que ela mora em `components/` e não dentro da tela**, ao contrário do
 * `ChamadaPrincipal` da Story 3.3. A diretiva `"use client"` é do **módulo**: um
 * `"use client"` no `page.tsx` arrastaria o cabeçalho, a ficha e a arte para o
 * cliente, e a página deixaria de ser Server Component. O precedente é o
 * `FormularioPublicacao`. A fronteira precisa ficar visível no código — a página é
 * servidor, este arquivo é cliente, e entre os dois passam **dados**, nunca
 * funções.
 *
 * **Nenhum número de estoque chega aqui**, e não é por disciplina desta tela: o
 * contrato não os tem (UX-DR7). O que ela recebe por setor é uma proporção — a
 * largura da barra — e uma palavra. `capacidade` e `vendidos` não existem do lado
 * de cá da rede.
 *
 * ⚠️ **Nada de `Intl` neste arquivo.** Dinheiro é `centavosParaReais` do
 * `lib/formato.ts`, que é módulo puro e atravessa a fronteira de propósito: o
 * `FUSO` e as regras de formatação do produto continuam existindo num lugar só.
 *
 * **A Story 3.6 acrescentou a ação.** O rodapé ganhou `Reservar e pagar`, que
 * dispara o `POST /reservas` e leva a `/reservas/{id}`; e ganhou o tratamento do
 * `409 ESTOQUE_INSUFICIENTE`, que é a única resposta desta tela capaz de dizer
 * algo que a pessoa não sabia — o setor esgotou entre a escolha e o clique.
 *
 * ⚠️ **Quem decide o desfecho é a página, não este componente.** `acaoDeCompra`
 * chega pronto de um Server Component que já leu a sessão, e isso é decidido
 * **antes** de renderizar — sem uma ida à rede para ouvir `403` sobre algo que a
 * página já sabia.
 *
 * **Eram dois desfechos até 13/08/2026, e agora são quatro** (decisão do Igor).
 * O `podeReservar: boolean` mandava organizador e portaria para o mesmo link de
 * login do visitante — ou seja, dizia "Entrar para reservar" a quem já estava
 * logado, e o clique levava a uma tela de entrar numa conta em que a pessoa já
 * estava. O organizador **precisa** desta página: é onde ele confere como o show
 * dele aparece para quem compra. O que ele não pode é comprar (AD-9), e agora é
 * isso que a tela diz, em palavras, no lugar de fingir que ele é um visitante.
 */
/**
 * O que o rodapé oferece a quem está olhando — calculado pela página, a partir
 * do papel da sessão.
 *
 * **`recusar` é um valor só para organizador e portaria**, e chegou a ser dois:
 * enquanto cada conta tinha a sua frase, a diferença precisava atravessar a
 * fronteira. Com o texto único, separá-las seria carregar aqui uma distinção que
 * nada lê — e a página continua sendo quem decide, porque é ela quem traduz
 * papel em desfecho.
 */
export type AcaoDeCompra = "reservar" | "recusar" | "entrar";

export default function EscolhaDeIngressos({
  eventoId,
  setores,
  maximoPorCompra,
  acaoDeCompra,
}: {
  eventoId: string;
  setores: SetorPublico[];
  maximoPorCompra: number;
  /** O desfecho do rodapé — a página é quem calcula, a partir do papel. */
  acaoDeCompra: AcaoDeCompra;
}) {
  const router = useRouter();

  // A quantidade por `setor.id`, e não um array paralelo à lista: a chave é o
  // que liga o número ao setor mesmo que a lista mude de ordem.
  const [quantidades, setQuantidades] = useState<Record<string, number>>({});
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<React.ReactNode>(null);

  // ⚠️ **A lista fresca relida depois de um `409`, e `null` enquanto não houve
  // nenhum.** Uma fonte só de cada vez: a tela renderiza `setoresFrescos ??
  // setores`, nunca uma mistura das duas. Sem isso, a pessoa continuaria olhando
  // um stepper que não pode mais funcionar.
  const [setoresFrescos, setSetoresFrescos] = useState<SetorPublico[] | null>(null);
  const listaDeSetores = setoresFrescos ?? setores;

  // O teto segue a mesma disciplina da lista: o da releitura quando houve uma,
  // o da prop enquanto não houve. Ver o aviso em `tratarEstoqueInsuficiente`.
  const [tetoFresco, setTetoFresco] = useState<number | null>(null);
  const tetoDaCompra = tetoFresco ?? maximoPorCompra;

  const escolhidos = listaDeSetores
    .map((setor) => ({ setor, quantidade: quantidades[setor.id] ?? 0 }))
    .filter(({ quantidade }) => quantidade > 0);

  const total = escolhidos.reduce((soma, { quantidade }) => soma + quantidade, 0);
  const valor = escolhidos.reduce(
    (soma, { setor, quantidade }) => soma + setor.preco_centavos * quantidade,
    0,
  );

  // ⚠️ **O teto é da compra, não do setor** (decisão do Igor). Com 4 na Pista e 2
  // no Camarote, **todos** os `+` da tela travam — é o que a palavra "por compra"
  // diz, e é o mesmo teto que o `POST /reservas` cobra do lado do servidor desde
  // a Story 3.6, da mesma constante. Seis por setor daria até dezoito numa
  // reserva.
  const noTeto = total >= tetoDaCompra;

  const mudar = (id: string, passo: number) =>
    setQuantidades((atual) => ({
      ...atual,
      // `Math.max(0, …)` é a rede de baixo; o `disabled` do `−` no zero é a de
      // cima. As duas existem porque o `disabled` é do DOM e este cálculo é da
      // regra: uma quantidade negativa no estado viraria um total negativo no
      // rodapé, e ninguém procuraria o defeito aqui.
      [id]: Math.max(0, (atual[id] ?? 0) + passo),
    }));

  /**
   * Relê o evento depois de um `409` e monta a frase do UX-DR8 (decisão do Igor).
   *
   * ⚠️ **É a tela que descobre o que dizer, e não o corpo do erro.** O `409`
   * continua sendo `{codigo, mensagem}` como toda resposta de erro desta API — o
   * `core/erros.py` existe desde a Story 1.1 para haver **uma** forma de erro, e
   * a primeira exceção é a que abre a segunda. O preço é uma ida a mais à rede;
   * o ganho é que essa mesma ida atualiza o stepper, que é o que a pessoa precisa
   * para tentar de novo.
   */
  async function tratarEstoqueInsuficiente(escolhidosAgora: string[]) {
    const evento = await chamarApi<EventoPublico>(`/eventos/${eventoId}`);
    setSetoresFrescos(evento.setores);

    // ⚠️ **O teto vem junto na releitura, e era descartado** (code review da
    // Epic 3). O corpo do `GET /eventos/{id}` traz `maximo_por_compra`, e ignorá-lo
    // deixava o stepper preso no valor da primeira renderização — o desencontro
    // que o comentário do próprio tipo `EventoPublico` existe para impedir.
    setTetoFresco(evento.maximo_por_compra);

    // A quantidade dos que esgotaram volta a zero: ninguém continua olhando um
    // stepper que não pode mais funcionar.
    const esgotados = new Set(
      evento.setores
        .filter((setor) => setor.disponibilidade === "ESGOTADO")
        .map((setor) => setor.id),
    );
    setQuantidades((atual) => {
      const proximas = { ...atual };
      for (const id of esgotados) delete proximas[id];
      return proximas;
    });

    // O setor nomeado é **um que eu escolhi** e que agora está esgotado.
    const meuEsgotado = evento.setores.find(
      (setor) => esgotados.has(setor.id) && escolhidosAgora.includes(setor.id),
    );

    // ⚠️ **`ESTOQUE_INSUFICIENTE` não quer dizer "esgotou"** (code review da
    // Epic 3), e tratá-lo como se quisesse era um beco sem saída. O servidor
    // levanta esse código sempre que `vendidos + quantidade > capacidade` — e o
    // caso mais comum de longe é a falta **parcial**: restam 3, a pessoa pediu 4.
    // Aí o setor volta como `ULTIMOS`, não `ESGOTADO`, e a versão anterior desta
    // função não tinha o que fazer com ele: nada era zerado, `meuEsgotado` ficava
    // `undefined`, e a frase saía "Esgotou enquanto você decidia. Ainda há
    // ingressos no setor Pista" — nomeando como alternativa exatamente o setor
    // que tinha acabado de falhar, com a quantidade impossível ainda no stepper.
    // Cada novo clique repetia o mesmo `409`, com o mesmo texto, para sempre.
    //
    // A frase daqui diz a única coisa verdadeira e acionável que a tela pode
    // dizer sem violar o UX-DR7: **reduza**. Quanto ainda cabe é justamente o que
    // o contrato não conta — e continua não contando.
    if (!meuEsgotado) {
      setErro(
        <>
          <strong>Não há mais essa quantidade.</strong> Alguém comprou enquanto
          você decidia. Reduza os ingressos e tente de novo.
        </>,
      );
      return;
    }

    // Daqui para baixo, um setor que eu escolhi esgotou de fato.
    const sobrando = evento.setores.find(
      (setor) => setor.disponibilidade !== "ESGOTADO",
    );

    if (!sobrando) {
      // Sem oferecer nada: não há para onde mandar a pessoa, e uma sugestão
      // inventada seria pior que o silêncio.
      setErro("Este show esgotou enquanto você decidia.");
      return;
    }

    // ⚠️ **"no setor X", e não "na X"** — o `EXPERIENCE.md` escreve "Ainda há
    // ingressos na Área VIP", que só funciona porque o exemplo dele é feminino.
    // O nome do setor é digitado pelo organizador e pode ser qualquer coisa
    // ("Camarote", "Pista Premium", "Mezanino"): não há como saber o gênero, e
    // "na Camarote" é pior do que a frase um pouco mais longa. O núcleo da frase
    // — o que esgotou e o que sobrou — é o que o UX-DR8 pede, e ele está inteiro.
    setErro(
      <>
        <strong>Esgotou enquanto você decidia.</strong>{" "}
        {`${meuEsgotado.nome} acabou de esgotar. `}
        Ainda há ingressos no setor {sobrando.nome}.
      </>,
    );
  }

  async function reservar() {
    // Guarda de reentrância: o `disabled` do botão é a rede de cima, e esta é a
    // de baixo. Duas reservas por um clique duplo custam estoque de verdade.
    if (enviando) return;

    setErro(null);
    setEnviando(true);

    let reservou = false;
    const escolhidosAgora = escolhidos.map(({ setor }) => setor.id);

    try {
      const reserva = await chamarApi<ReservaSaida>("/reservas", {
        method: "POST",
        body: JSON.stringify({
          evento_id: eventoId,
          itens: escolhidos.map(({ setor, quantidade }) => ({
            setor_id: setor.id,
            quantidade,
          })),
        }),
      });

      // ⚠️ **`refresh` antes do `push`, e não é o mesmo `refresh` do login.**
      // Aquele existia por causa do masthead; este existe porque o estoque
      // **desta** página acabou de mudar — sem ele, o botão "voltar" do
      // navegador mostraria o medidor e a disponibilidade de antes da compra.
      router.refresh();
      router.push(`/reservas/${reserva.id}`);
      // A navegação está a caminho e esta tela vai embora: o botão **não** volta
      // a ficar clicável. Ver o aviso no `finally`.
      reservou = true;
    } catch (erroCapturado) {
      // `instanceof` antes de ler `.codigo`: erro de rede não tem código.
      if (erroCapturado instanceof ErroDaApi) {
        if (erroCapturado.codigo === "ESTOQUE_INSUFICIENTE") {
          try {
            await tratarEstoqueInsuficiente(escolhidosAgora);
          } catch {
            // A releitura também falhou: a tela não tem dado fresco para nomear
            // setor nenhum, e inventar seria pior. A frase genérica do UX-DR8
            // continua verdadeira.
            setErro("Esgotou enquanto você decidia. Recarregue a página.");
          }
          return;
        }
        setErro(mensagemParaCodigo(erroCapturado.codigo, tetoDaCompra));
        return;
      }
      setErro(MENSAGEM_GENERICA);
    } finally {
      // ⚠️ **No caminho feliz o botão NÃO volta, e essa é a correção** (code
      // review da Epic 3). O `router.push` é assíncrono e a tela continua
      // montada enquanto o RSC da próxima rota é buscado — o `router.refresh()`
      // da linha acima ainda alonga essa janela. Reabilitar o botão aqui, como
      // era antes, punha "Reservar e pagar" clicável de novo durante a
      // navegação: um segundo clique numa conexão lenta disparava um **segundo**
      // `POST /reservas`, que o backend aceita (não há dedupe nem limite de
      // `PENDENTE` por cliente). Duas reservas, estoque consumido duas vezes, e
      // a pessoa aterrissa na primeira sem nunca ver a outra — que só solta os
      // lugares dez minutos depois.
      //
      // Num erro ele volta, e continua tendo que voltar: aí a tela fica, e um
      // botão preso em "Reservando…" seria um botão morto.
      if (!reservou) setEnviando(false);
    }
  }

  return (
    <>
      <div className={estilos.setores}>
        {listaDeSetores.map((setor) => {
          const esgotado = setor.disponibilidade === "ESGOTADO";
          const quantidade = quantidades[setor.id] ?? 0;

          return (
            <div
              key={setor.id}
              className={`${estilos.setor} ${esgotado ? estilos.setorEsgotado : ""}`}
            >
              <div className={estilos.identidadeDoSetor}>
                <span className={estilos.nomeDoSetor}>{setor.nome}</span>

                {/* ⚠️ `aria-hidden` **de propósito** (suposição declarada na
                    story): a palavra ao lado carrega a mesma informação, e uma
                    barra anunciada como "39 por cento" convidaria justamente à
                    leitura numérica que o UX-DR7 evita. Quem usa leitor de tela
                    ouve `Últimos ingressos`, não uma porcentagem sem contexto.

                    O `style` inline é a única coisa que não cabe no CSS Module: a
                    largura vem do dado, e é por setor. */}
                <div className={estilos.medidor} aria-hidden>
                  <div
                    className={`${estilos.preenchimento} ${
                      PREENCHIMENTO[setor.disponibilidade]
                    }`}
                    style={{ width: `${setor.proporcao_vendida * 100}%` }}
                  />
                </div>

                {/* ⚠️ **A informação não é dada só por cor** (UX-DR9): a palavra
                    está escrita, e é ela que atravessa para quem não vê a barra.
                    E **nenhum número de estoque** aqui — nem como texto, nem como
                    `title`, nem como `aria-label`. */}
                <span className={estilos.estado}>{ESTADO[setor.disponibilidade]}</span>
              </div>

              <div className={estilos.escolha}>
                <span className={estilos.preco}>
                  R$ {centavosParaReais(setor.preco_centavos)}
                </span>

                {esgotado ? (
                  // ⚠️ **Sem stepper, e os botões não existem no DOM** — não são
                  // botões desabilitados por CSS. Mesmo motivo já escrito na fila
                  // da 3.1 e na capa da 3.3: opacidade sem o atributo deixa o
                  // elemento clicável e no Tab, anunciado como ativo.
                  <span className={estilos.selo}>Esgotado</span>
                ) : (
                  <div className={estilos.stepper}>
                    {/* ⚠️ **Nome acessível por setor.** `−` e `+` sozinhos não
                        dizem de que setor são, e numa tela com três setores quem
                        navega por leitor de tela ouviria seis botões idênticos.
                        `type="button"` porque não há formulário aqui e o default
                        de `<button>` é `submit`.

                        E **`disabled` de verdade**, atributo e não opacidade: o
                        botão no limite sai do Tab e é anunciado como
                        indisponível. */}
                    <button
                      type="button"
                      className={estilos.passo}
                      onClick={() => mudar(setor.id, -1)}
                      disabled={quantidade === 0}
                      aria-label={`Um ingresso menos da ${setor.nome}`}
                    >
                      −
                    </button>

                    {/* `aria-live="polite"` é o que faz a mudança ser anunciada
                        sem que a pessoa precise reler a tela — apertar `+` sem
                        retorno nenhum é apertar no escuro. */}
                    <span className={estilos.quantidade} aria-live="polite">
                      {quantidade}
                    </span>

                    <button
                      type="button"
                      className={estilos.passo}
                      onClick={() => mudar(setor.id, 1)}
                      disabled={noTeto}
                      aria-label={`Mais um ingresso da ${setor.nome}`}
                    >
                      +
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ⚠️ **Fora do `{total > 0 && …}` de propósito.** A região `role="alert"`
          precisa existir no DOM **antes** de a mensagem entrar, senão o leitor de
          tela pode não anunciar nada (a regra inteira está no `Toast.tsx`) — e o
          rodapé abaixo aparece e some conforme a escolha. Vazio, o toast não
          ocupa espaço nem intercepta clique. */}
      {/* `acima-do-rodape` porque o rodapé abaixo é `sticky`: no pé da janela o
          aviso cairia sobre o `Reservar e pagar`, que é a ação que ele pede para
          refazer. É a prop que nasceu quando o formulário de publicar virou o
          segundo consumidor deste componente. */}
      <Toast
        mensagem={erro}
        aoFechar={() => setErro(null)}
        posicao="acima-do-rodape"
      />

      {/* ⚠️ **Com zero escolhido o rodapé não é renderizado** (suposição
          declarada, mantida na 3.6): `R$ 0,00` grudado na base é ruído, e o
          rodapé existe para responder "quanto vou pagar" — pergunta que ainda não
          foi feita. Sem escolha não há o que reservar, então o botão também não
          tem por que existir. */}
      {total > 0 && (
        <div className={estilos.rodape}>
          <span className={estilos.resumo}>
            {total} {total === 1 ? "ingresso" : "ingressos"} ·{" "}
            {/* Com **um** setor escolhido o rodapé o nomeia, como o protótipo
                escreve; com mais, conta. Três nomes virariam uma lista dentro de
                uma linha que tem de caber num celular. */}
            {escolhidos.length === 1
              ? escolhidos[0].setor.nome
              : `${escolhidos.length} setores`}
          </span>
          <span className={estilos.total}>R$ {centavosParaReais(valor)}</span>

          {/* ⚠️ **Link, e não botão desabilitado, para quem não é cliente**
              (decisão do Igor). A página já sabe quem está logado — ela é Server
              Component —, então não há ida à rede para ouvir `401` sobre algo
              que já se sabia antes de renderizar.

              O `?voltar=` **já existe desde a Story 1.4** e já é sanitizado por
              `caminhoInternoSeguro` do lado de lá: nada de parâmetro novo, nada
              de `?destino=`. E a escolha do stepper **se perde** nessa ida
              (decisão do Igor): o estoque pode ter mudado nesses segundos, e
              reescolher é ver o preço e a disponibilidade de agora. */}
          {acaoDeCompra === "reservar" ? (
            <div className={estilos.acao}>
              <Botao type="button" onClick={reservar} disabled={enviando}>
                {enviando ? "Reservando…" : "Reservar e pagar"}
              </Botao>
            </div>
          ) : acaoDeCompra !== "entrar" ? (
            /* ⚠️ **O botão existe e é clicável de verdade, e é essa a decisão.**
               Ele podia vir `disabled` — a regra é conhecida antes do clique —,
               mas botão apagado não diz por quê, e a pergunta de quem publicou o
               show é exatamente essa. Um clique, uma frase, nenhuma ida à rede: a
               recusa já é do backend (`Depends(exigir_papel(CLIENTE))`, AD-9), e
               aqui ela só chega antes, em português.

               `type="button"`, como em todo botão desta ilha: não há formulário,
               e o default de `<button>` é `submit`. */
            <div className={estilos.acao}>
              <Botao type="button" onClick={() => setErro(RECUSA_DE_COMPRA)}>
                Reservar e pagar
              </Botao>
            </div>
          ) : (
            <Link
              href={`/login?voltar=${encodeURIComponent(`/eventos/${eventoId}`)}`}
              className={estilos.entrar}
            >
              Entrar para reservar
            </Link>
          )}
        </div>
      )}
    </>
  );
}

const MENSAGEM_GENERICA =
  "Não foi possível reservar agora. Tente de novo em instantes.";

/**
 * Mesma convenção do login, do cadastro e da publicação: **o texto vem do
 * `codigo`, nunca da `mensagem` do servidor.** A `mensagem` é para humano e pode
 * mudar sem quebrar ninguém; o `codigo` é a parte estável do contrato.
 *
 * ⚠️ `ESTOQUE_INSUFICIENTE` **não** está aqui de propósito: ele é o único código
 * desta tela que precisa de dados frescos para virar frase, e quem o trata é o
 * `tratarEstoqueInsuficiente` lá em cima.
 *
 * ⚠️ `NAO_AUTENTICADO` e `SEM_PERMISSAO` entram desde a primeira linha, e não
 * como remendo: foi exatamente o buraco que o code review da Epic 2 encontrou no
 * formulário de publicação. A sessão dura 8 horas (AD-15) e pode cair com a tela
 * aberta — sem estas duas entradas, o `401` cairia na frase genérica "tente de
 * novo em instantes", e tentar de novo daria `401` outra vez, para sempre.
 */
function mensagemParaCodigo(codigo: string, tetoDaCompra: number): string {
  if (codigo === "ACIMA_DO_MAXIMO_POR_COMPRA") {
    // ⚠️ **O número vem do contrato, e não escrito à mão aqui** (code review da
    // Epic 3). O stepper já lia `maximo_por_compra` da rota; só esta frase tinha
    // um `6` literal — o que significa que, no dia em que o teto mudar, o
    // stepper trava no número novo e a recusa continua dizendo seis. É
    // exatamente o desencontro que o comentário do tipo `EventoPublico` e o AC11
    // da Story 3.6 existem para impedir, sobrevivendo na única linha que ninguém
    // olhou.
    return `São até ${tetoDaCompra} ingressos por compra. Reduza a quantidade e tente de novo.`;
  }
  if (codigo === "SETOR_INVALIDO") {
    // Sem dizer **qual**: o backend não distingue "não existe" de "é de outro
    // show", de propósito, e a tela não inventa uma precisão que a resposta não
    // tem. Recarregar é o conserto real — a lista mudou.
    return "Algum dos setores escolhidos não está mais disponível. Recarregue a página.";
  }
  if (codigo === "EVENTO_NAO_ENCONTRADO") {
    return "Esse show não está mais em cartaz.";
  }
  if (codigo === "RESERVA_SEM_ITEM" || codigo === "ITEM_DUPLICADO") {
    return "Escolha ao menos um ingresso para reservar.";
  }
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    return "Sua sessão expirou. Entre de novo para reservar.";
  }
  return MENSAGEM_GENERICA;
}

/**
 * A recusa de quem está logado e não é cliente (13/08/2026).
 *
 * **Ela não vem do servidor, e é a primeira mensagem desta tela que não vem.**
 * Todas as outras nascem de um `codigo` de resposta — é a convenção do projeto
 * desde a Story 1.4. Esta é anterior à requisição: a página já sabe o papel, e
 * gastar uma ida à rede para ouvir o `403 SEM_PERMISSAO` que a rota devolveria
 * (AD-9) seria perguntar o que já se sabe. A regra continua sendo do backend; o
 * que mora aqui é só a tradução dela para quem clicou.
 *
 * **Uma frase, sem `<strong>`, e sem uma versão por papel** (texto do Igor). A
 * primeira redação abria com um título em versalete e explicava a cada conta por
 * que ela não compra — o organizador ouvia que esta é a mesma página que o
 * público vê, a portaria que ela valida na porta. Ficou comprido para um aviso
 * que responde a um clique só: quem clicou quer saber o que houve, não ler um
 * parágrafo sobre o próprio papel. A regra é a mesma para os dois, então o texto
 * também é.
 */
const RECUSA_DE_COMPRA = "Somente contas de clientes podem reservar ingressos.";

/**
 * A palavra de cada estado, em português e fora do componente.
 *
 * Um objeto e não um `switch`: o tipo do backend é um enum fechado de três
 * valores, e um `Record` sobre ele **quebra o build** no dia em que um quarto
 * valor entrar no contrato sem tradução — que é exatamente o aviso que se quer.
 */
const ESTADO: Record<SetorPublico["disponibilidade"], string> = {
  DISPONIVEL: "Disponível",
  ULTIMOS: "Últimos ingressos",
  ESGOTADO: "Esgotado",
};

/**
 * A cor da barra de cada estado — `Record` pelo mesmo motivo do `ESTADO` acima.
 *
 * A cor **acompanha** a palavra e não a substitui (UX-DR9): ela é a leitura
 * periférica, e a palavra é a informação.
 */
const PREENCHIMENTO: Record<SetorPublico["disponibilidade"], string> = {
  DISPONIVEL: estilos.preenchimentoDisponivel,
  ULTIMOS: estilos.preenchimentoUltimos,
  ESGOTADO: estilos.preenchimentoEsgotado,
};
