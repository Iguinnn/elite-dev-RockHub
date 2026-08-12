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
 * ⚠️ **Quem decide se há botão é a página, não este componente.** `podeReservar`
 * chega pronto de um Server Component que já leu a sessão: visitante,
 * organizador e portaria veem um link para o login no lugar do botão, e isso é
 * decidido **antes** de renderizar — sem uma ida à rede para ouvir `401` sobre
 * algo que a página já sabia.
 */
export default function EscolhaDeIngressos({
  eventoId,
  setores,
  maximoPorCompra,
  podeReservar,
}: {
  eventoId: string;
  setores: SetorPublico[];
  maximoPorCompra: number;
  /** Verdadeiro só para sessão de `CLIENTE` — a página é quem calcula. */
  podeReservar: boolean;
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
  const noTeto = total >= maximoPorCompra;

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

    // O setor nomeado é **um que eu escolhi** e que agora está esgotado; o
    // oferecido é o primeiro da lista fresca que ainda tem ingresso.
    const meuEsgotado = evento.setores.find(
      (setor) => esgotados.has(setor.id) && escolhidosAgora.includes(setor.id),
    );
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
        {meuEsgotado ? `${meuEsgotado.nome} acabou de esgotar. ` : ""}
        Ainda há ingressos no setor {sobrando.nome}.
      </>,
    );
  }

  async function reservar() {
    setErro(null);
    setEnviando(true);

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
        setErro(mensagemParaCodigo(erroCapturado.codigo));
        return;
      }
      setErro(MENSAGEM_GENERICA);
    } finally {
      // ⚠️ Fora do `try` de sucesso de propósito: no caminho feliz o `push` é
      // assíncrono e a tela continua montada por um instante. Um botão que
      // continuasse "Reservando…" depois de um erro seria um botão morto.
      setEnviando(false);
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
      <Toast mensagem={erro} aoFechar={() => setErro(null)} />

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
          {podeReservar ? (
            <div className={estilos.acao}>
              <Botao type="button" onClick={reservar} disabled={enviando}>
                {enviando ? "Reservando…" : "Reservar e pagar"}
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
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "ACIMA_DO_MAXIMO_POR_COMPRA") {
    return "São até 6 ingressos por compra. Reduza a quantidade e tente de novo.";
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
