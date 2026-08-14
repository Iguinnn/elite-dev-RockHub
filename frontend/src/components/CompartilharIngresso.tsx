"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Confirmacao from "@/components/Confirmacao";
import SessaoExpirada from "@/components/SessaoExpirada";
import { ErroDaApi, chamarApi } from "@/lib/api";
import type { IngressoDetalhe } from "@/lib/ingressos";

import estilos from "./CompartilharIngresso.module.css";

/**
 * O link compartilhável do ingresso — a ilha da Story 4.3.
 *
 * **Recebe o ingresso pronto e guarda o token em estado.** A página é Server
 * Component e já leu o canhoto inteiro; esta ilha existe porque compartilhar é
 * um clique que muda a tela sem recarregar — o mesmo critério que fez o
 * `EscolhaDeIngressos` nascer na Story 3.4.
 *
 * ⚠️ **Quem monta a URL é o navegador, não a API.** A resposta carrega só o
 * token; o endereço sai de `window.location.origin`. O backend não conhece — nem
 * deve — o domínio do frontend, que muda a cada Preview da Vercel.
 *
 * ⚠️ **`router.refresh()` depois de cada mutação.** A página é Server
 * Component: sem o refresh, o estado desta ilha e o que o servidor renderizou
 * divergem, e um *Voltar* do navegador mostraria o link revogado ainda ali. É o
 * mesmo aviso que o `FormularioLogin` carrega desde a Story 1.4.
 *
 * **A Story 4.4 acrescentou *Revogar link*, e ele é a única ação do produto que
 * pergunta antes.** Compartilhar de novo devolve o mesmo token justamente para
 * que revogar seja o único caminho que invalida um link — e um caminho que
 * corta o acesso de quem já recebeu não pode acontecer por um clique distraído.
 */
export default function CompartilharIngresso({
  ingresso,
}: {
  ingresso: IngressoDetalhe;
}) {
  const router = useRouter();

  const [token, setToken] = useState(ingresso.share_token);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<React.ReactNode>(null);
  const [copiado, setCopiado] = useState(false);
  const [confirmando, setConfirmando] = useState(false);

  // ⚠️ **Os dois nascem vazios e são preenchidos no `useEffect`, nunca no
  // `useState` inicial.** `window` e `navigator` não existem no servidor, e um
  // valor que só o navegador conhece dentro do primeiro render é um `text
  // content did not match` na hidratação — a mesma armadilha que o `Cronometro`
  // descreve por extenso. Até o efeito rodar, o link aparece como caminho
  // relativo, que dura um quadro e continua sendo verdade.
  const [origem, setOrigem] = useState("");
  const [podeCopiar, setPodeCopiar] = useState(false);

  useEffect(() => {
    // O `eslint-disable` abaixo vale para o efeito inteiro — as duas escritas
    // rodam **uma vez por montagem** e são justamente o que evita o defeito que
    // a regra `set-state-in-effect` não enxerga: valor que só o navegador
    // conhece dentro do primeiro render é divergência de hidratação. É a mesma
    // exceção que o `Cronometro` documenta desde a Story 3.6.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOrigem(window.location.origin);
    // ⚠️ **`navigator.clipboard` só existe em contexto seguro** — em `http://`
    // que não seja `localhost` ele é `undefined`, e chamá-lo direto levanta
    // `TypeError` dentro do `onClick`. O botão só é renderizado quando existe;
    // o link em texto selecionável é o caminho, não o plano B.
    setPodeCopiar(typeof navigator !== "undefined" && !!navigator.clipboard);
  }, []);

  const link = token ? `${origem}/i/${token}` : "";

  async function compartilhar() {
    // Guarda de reentrância: o `disabled` do botão é a rede de cima, esta é a
    // de baixo. Aqui um clique duplo não custa estoque — a rota é idempotente e
    // devolve o mesmo token —, mas duas chamadas em voo terminam fora de ordem.
    if (enviando) return;

    setErro(null);
    setEnviando(true);

    try {
      const atualizado = await chamarApi<IngressoDetalhe>(
        `/ingressos/${ingresso.id}/compartilhamento`,
        { method: "POST" },
      );
      setToken(atualizado.share_token);
      router.refresh();
    } catch (erroCapturado) {
      // `instanceof` antes de ler `.codigo`: erro de rede não tem código.
      if (erroCapturado instanceof ErroDaApi) {
        setErro(
          mensagemParaCodigo(
            erroCapturado.codigo,
            MENSAGEM_DE_GERACAO,
            ingresso.id,
          ),
        );
      } else {
        setErro(MENSAGEM_DE_GERACAO);
      }
    } finally {
      // Aqui o botão **volta** sempre, ao contrário do `EscolhaDeIngressos`:
      // não há navegação nenhuma a caminho, a tela fica, e um botão preso em
      // "Compartilhando…" seria um botão morto.
      setEnviando(false);
    }
  }

  async function revogar() {
    if (enviando) return;

    // ⚠️ **Desliga a confirmação aqui, e não só pelo `close` do `<dialog>`.**
    // O `close()` do navegador **enfileira** o evento em vez de disparar na
    // hora, e o `setToken(null)` do sucesso desmonta o `<Confirmacao>` — se a
    // desmontagem chegar antes do evento, o `aoFechar` nunca roda e este estado
    // fica preso em `true`. O sintoma seria a caixa abrindo sozinha no clique
    // seguinte em *Compartilhar*, sem ninguém ter pedido.
    setConfirmando(false);
    setErro(null);
    setEnviando(true);

    try {
      // `204` sem corpo: o `chamarApi` corta antes do `.json()` e devolve
      // `undefined`. Não há estado novo para aprender — o link deixou de
      // existir, e quem pediu isso foi esta tela.
      await chamarApi<void>(`/ingressos/${ingresso.id}/compartilhamento`, {
        method: "DELETE",
      });
      setToken(null);
      // O botão de copiar podia estar dizendo "Copiado" de um link que não
      // existe mais.
      setCopiado(false);
      router.refresh();
    } catch (erroCapturado) {
      if (erroCapturado instanceof ErroDaApi) {
        setErro(
          mensagemParaCodigo(
            erroCapturado.codigo,
            MENSAGEM_DE_REVOGACAO,
            ingresso.id,
          ),
        );
      } else {
        setErro(MENSAGEM_DE_REVOGACAO);
      }
    } finally {
      setEnviando(false);
    }
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
      // Volta a dizer "Copiar" depois de um tempo: sem isso o botão fica
      // mentindo "Copiado" para o próximo clique, que copia de novo.
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      // Permissão negada no navegador. Sem frase de erro: o link está inteiro
      // e selecionável logo ao lado, e essa é a saída — não há nada a corrigir.
      setCopiado(false);
    }
  }

  return (
    <div className={estilos.bloco}>
      <span className="kicker">Compartilhar</span>

      {token ? (
        <>
          <p className={estilos.explicacao}>
            Quem abrir este link vê o ingresso com o código de entrada, sem
            precisar de conta.
          </p>

          <div className={estilos.linha}>
            {/* `<code>` e texto selecionável: é dado de máquina (UX-DR9), e é
                por ele que a pessoa copia à mão quando não há `clipboard`. */}
            <code className={estilos.link}>{link}</code>

            {podeCopiar && (
              <button
                type="button"
                className={estilos.copiar}
                onClick={copiar}
                // `polite` porque a troca de palavra é o único retorno do
                // clique — sem ela, quem usa leitor de tela copia no escuro.
                aria-live="polite"
              >
                {copiado ? "Copiado" : "Copiar"}
              </button>
            )}
          </div>

          {/* **O gatilho é o próprio botão destrutivo, no mesmo `--brasa` da
              confirmação** (decisão do Igor). Eu tinha posto um gatilho
              discreto que só ficava vermelho no hover, para o vermelho aparecer
              junto com a intenção de clicar; ele preferiu a cor desde o início,
              e a consistência com o botão que confirma é o argumento a favor —
              a ação é a mesma, e a tinta anuncia a consequência antes do
              clique, não depois. */}
          <div className={estilos.acao}>
            <Botao
              type="button"
              variante="destrutivo"
              onClick={() => setConfirmando(true)}
              disabled={enviando}
            >
              {enviando ? "Revogando…" : "Revogar link"}
            </Botao>
          </div>

          {/* ⚠️ **Cancelar não chama a API.** Fechar a caixa pelo `Esc` ou
              pelo *Cancelar* só desliga este estado — a única linha que fala
              com o servidor é o `aoConfirmar`. (Clique no backdrop não fecha:
              é o comportamento nativo do `<dialog>`, e mantê-lo é de propósito
              numa ação sem volta.) */}
          <Confirmacao
            aberta={confirmando}
            titulo="Revogar este link?"
            consequencia="Quem já recebeu o link deixa de conseguir abrir o ingresso. Você pode gerar um novo depois, mas ele terá outro endereço."
            rotuloDaAcao="Revogar link"
            aoConfirmar={revogar}
            aoFechar={() => setConfirmando(false)}
          />
        </>
      ) : (
        <>
          <p className={estilos.explicacao}>
            Gere um link para enviar este ingresso a quem vai usá-lo.
          </p>

          <div className={estilos.acao}>
            <Botao type="button" onClick={compartilhar} disabled={enviando}>
              {enviando ? "Gerando…" : "Compartilhar"}
            </Botao>
          </div>
        </>
      )}

      {/* Fora do ramo condicional: a região `role="alert"` precisa existir no
          DOM **antes** de a mensagem entrar (a regra inteira está no
          `AvisoDeErro`). Vazia, ela não ocupa espaço nenhum. */}
      <AvisoDeErro mensagem={erro} />
    </div>
  );
}

const MENSAGEM_DE_GERACAO =
  "Não foi possível gerar o link agora. Tente de novo em instantes.";

/**
 * ⚠️ **Uma frase própria para a falha ao revogar, e não a de gerar.** As duas
 * ações moram na mesma ilha e falham pelos mesmos códigos, mas "não foi
 * possível gerar o link" depois de clicar em *Revogar* diria à pessoa que ela
 * fez outra coisa — e, pior, deixaria no ar se o link ainda vale. A frase daqui
 * responde a única pergunta que importa nesse momento: **ele continua valendo**.
 */
const MENSAGEM_DE_REVOGACAO =
  "Não foi possível revogar o link agora, e ele continua valendo. Tente de novo em instantes.";

/**
 * Mesma convenção do resto do frontend: **o texto vem do `codigo`, nunca da
 * `mensagem` do servidor.** A `mensagem` é para humano e pode mudar sem quebrar
 * ninguém; o `codigo` é a parte estável do contrato.
 *
 * A frase genérica chega por parâmetro porque **as duas ações desta ilha falham
 * pelos mesmos códigos e precisam dizer coisas diferentes** — ver o comentário
 * da `MENSAGEM_DE_REVOGACAO` logo acima.
 *
 * ⚠️ `NAO_AUTENTICADO` e `SEM_PERMISSAO` entram desde a primeira linha, e não
 * como remendo: foi o buraco que o code review da Epic 2 encontrou no
 * formulário de publicação. A sessão dura 8 horas (AD-15) e pode cair com a
 * tela aberta — sem estas duas entradas, o `401` cairia na frase genérica
 * "tente de novo em instantes", e tentar de novo daria `401` outra vez.
 */
function mensagemParaCodigo(
  codigo: string,
  generica: string,
  ingressoId: string,
): React.ReactNode {
  if (codigo === "INGRESSO_NAO_ENCONTRADO") {
    return "Esse ingresso não está mais disponível. Recarregue a página.";
  }
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    // ⚠️ **Com o caminho de volta desde 13/08/2026** — ver `SessaoExpirada`.
    return (
      <SessaoExpirada voltar={`/ingressos/${ingressoId}`} acao="continuar" />
    );
  }
  return generica;
}
