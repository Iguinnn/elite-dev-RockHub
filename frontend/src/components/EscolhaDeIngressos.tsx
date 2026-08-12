"use client";

import { useState } from "react";

import estilos from "@/app/(site)/eventos/[id]/page.module.css";
import { centavosParaReais } from "@/lib/formato";
import type { SetorPublico } from "@/lib/programacao";

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
 */
export default function EscolhaDeIngressos({
  setores,
  maximoPorCompra,
}: {
  setores: SetorPublico[];
  maximoPorCompra: number;
}) {
  // A quantidade por `setor.id`, e não um array paralelo à lista: a chave é o
  // que liga o número ao setor mesmo que a lista mude de ordem.
  const [quantidades, setQuantidades] = useState<Record<string, number>>({});

  const escolhidos = setores
    .map((setor) => ({ setor, quantidade: quantidades[setor.id] ?? 0 }))
    .filter(({ quantidade }) => quantidade > 0);

  const total = escolhidos.reduce((soma, { quantidade }) => soma + quantidade, 0);
  const valor = escolhidos.reduce(
    (soma, { setor, quantidade }) => soma + setor.preco_centavos * quantidade,
    0,
  );

  // ⚠️ **O teto é da compra, não do setor** (decisão do Igor). Com 4 na Pista e 2
  // no Camarote, **todos** os `+` da tela travam — é o que a palavra "por compra"
  // diz, e é o que a Story 3.6 vai cobrar do lado do servidor. Seis por setor
  // daria até dezoito ingressos numa reserva.
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

  return (
    <>
      <div className={estilos.setores}>
        {setores.map((setor) => {
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

      {/* ⚠️ **Com zero escolhido o rodapé não é renderizado** (suposição
          declarada): `R$ 0,00` grudado na base é ruído, e o rodapé existe para
          responder "quanto vou pagar" — pergunta que ainda não foi feita.

          ⚠️ E **não há botão aqui** (decisão do Igor): `Reservar e pagar` é a
          Story 3.6, junto com a rota que ele chamaria. Nada nesta tela promete uma
          ação que ainda não existe, e um botão presente e desabilitado leria como
          defeito, não como escopo. */}
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
        </div>
      )}
    </>
  );
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
