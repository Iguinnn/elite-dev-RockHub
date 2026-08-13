"use client";

import { useRef, useState } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import { ErroDaApi } from "@/lib/api";
import { horaDeEntrada } from "@/lib/formato";
import {
  validarCodigo,
  type ResultadoDaValidacao,
  type Veredito,
} from "@/lib/validacao";

import estilos from "./Leitor.module.css";

/**
 * O leitor da porta: um campo, Enter, e o veredito abaixo (Story 5.3).
 *
 * **Ilha porque validar é a única coisa que acontece nesta tela**, e ela
 * acontece dezenas de vezes seguidas sem recarregar nada. O cabeçalho com o
 * nome do show é Server Component; daqui para baixo é estado.
 *
 * ⚠️ **Enter valida, e é o requisito, não uma conveniência.** O
 * `EXPERIENCE.md#Interaction Primitives` diz com todas as letras: *"o operador
 * não deve precisar mirar num botão"*. Quem está na porta digita oito símbolos
 * com uma mão, em pé, com fila esperando — e a tecla de confirmar já está
 * debaixo do polegar. É `<form onSubmit>` e não `onKeyDown`: a submissão
 * implícita do formulário de um campo só é comportamento nativo do navegador,
 * funciona com o "Ir" do teclado do celular e não custa uma linha de
 * JavaScript.
 *
 * **O botão *Validar* existe além do Enter, e não no lugar dele.** Nem todo
 * teclado de celular oferece a tecla de confirmar num campo de texto comum, e um
 * alvo de 44px é o que o UX-DR6 pede para esta superfície.
 *
 * ⚠️ **O veredito não some sozinho** (`EXPERIENCE.md#veredito`): ele fica até a
 * próxima validação substituí-lo. A portaria precisa poder olhar duas vezes com
 * a fila esperando, e um resultado que se apaga por conta própria obriga a ler
 * no susto. O que o limpa é a submissão seguinte — ação explícita de quem está
 * lendo, não um `setTimeout`.
 *
 * **A apresentação a três metros — cor, símbolo e corpo enorme — é a Story
 * 5.4.** Aqui é palavra e detalhe em texto, que é o que o AC da 5.3 pede: com
 * isso a portaria já trabalha, e o resto é refinamento de leitura. Os três
 * canais do `EXPERIENCE.md` entram todos juntos, na story que os desenha.
 *
 * ⚠️ **A tela não reinterpreta o veredito.** Ela desenha o que veio. A tentação
 * é "se `INVALIDO` e o código tiver 8 caracteres, então…" — não há "então": o
 * backend já decidiu, e uma segunda opinião aqui seria uma regra de validação
 * morando na tela.
 */
export default function Leitor({ eventoId }: { eventoId: string }) {
  const [codigo, setCodigo] = useState("");
  const [resultado, setResultado] = useState<ResultadoDaValidacao | null>(null);
  const [erro, setErro] = useState<React.ReactNode>(null);
  const [enviando, setEnviando] = useState(false);
  const campo = useRef<HTMLInputElement>(null);

  async function validar(submissao: React.FormEvent<HTMLFormElement>) {
    submissao.preventDefault();

    // Guarda de reentrância: o `disabled` do botão é a rede de cima, esta é a de
    // baixo — e aqui ela pesa, porque o Enter continua submetendo o formulário
    // mesmo com o botão desativado. Duas validações do mesmo código em voo
    // terminariam fora de ordem, e a segunda diria `JA_UTILIZADO` de uma entrada
    // que a primeira acabou de gravar.
    if (enviando) return;

    // ⚠️ **Campo em branco não chama a API, e o foco fica onde está** (AC da
    // 5.3). Um Enter distraído — que na porta acontece o tempo todo — não vale
    // uma ida à rede nem, pior, um `INVALIDO` na tela: não houve leitura
    // nenhuma, e um veredito ali diria que houve.
    if (!codigo.trim()) {
      campo.current?.focus();
      return;
    }

    setErro(null);
    // O veredito anterior sai **agora**, e não quando a resposta chegar: durante
    // a chamada ele estaria respondendo pela leitura errada, e a fila lê o que
    // está na tela, não o que está em voo.
    setResultado(null);
    setEnviando(true);

    try {
      setResultado(await validarCodigo(eventoId, codigo));
      // O campo esvazia no sucesso — o próximo da fila digita num campo limpo,
      // sem apagar oito símbolos antes. Na falha ele **fica**: o código pode
      // estar certo e a rede não.
      setCodigo("");
    } catch (erroCapturado) {
      // `instanceof` antes de ler `.codigo`: erro de rede não tem código.
      setErro(
        erroCapturado instanceof ErroDaApi
          ? mensagemParaCodigo(erroCapturado.codigo)
          : MENSAGEM_GENERICA,
      );
    } finally {
      setEnviando(false);
      // ⚠️ **O foco volta ao campo nos dois caminhos.** Sem isto, depois de
      // clicar em *Validar* o foco fica no botão e o Enter seguinte reenvia o
      // mesmo código em vez de mandar o próximo — o defeito só aparece para
      // quem usa o botão, que é justamente quem está com uma mão só.
      campo.current?.focus();
    }
  }

  return (
    <div className={estilos.leitor}>
      <form className={estilos.formulario} onSubmit={validar}>
        {/* `<label>` de verdade, nunca só `placeholder` (UX-DR9). Ele fica
            visível: na porta, no escuro, o rótulo que some ao digitar é o que
            deixa a pessoa em dúvida sobre o que está preenchendo. */}
        <label htmlFor="codigo" className={estilos.rotulo}>
          Código do ingresso
        </label>

        <input
          id="codigo"
          ref={campo}
          className={estilos.entrada}
          value={codigo}
          onChange={(evento) => setCodigo(evento.target.value)}
          // ⚠️ **`autoFocus` porque este campo é a tela inteira** enquanto a
          // câmera não existe (Story 5.5): quem abre o leitor abriu para
          // digitar, e o teclado subir sozinho economiza o toque que o
          // EXPERIENCE.md pede para economizar. Quando o botão da câmera
          // entrar, esta linha é a primeira a revisitar — ali o caminho
          // primário passa a ser outro, e o teclado subindo por conta própria
          // vira estorvo.
          autoFocus
          // Dado de máquina: nada de corretor, de caixa automática nem de
          // preenchimento do navegador atrapalhando oito símbolos.
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          // Mesmo teto do `ValidacaoEntrada` do backend. Ele não valida o
          // código — quem faz isso é o servidor —, só impede que uma colagem
          // distraída vire `422` num campo que deveria responder `INVALIDO`.
          maxLength={64}
          inputMode="text"
          disabled={enviando}
        />

        <p className={estilos.dica}>
          Digite o código e aperte Enter. Maiúsculas, espaços e hífens não
          importam.
        </p>

        {/* **Largura inteira da coluna**, como o `EXPERIENCE.md#Responsive` pede
            para esta superfície — e é o que o `<Botao>` já é por padrão. Quem
            fecha a coluna é o `.leitor`, e o porquê está lá: sem ele, "largura
            inteira" viraria uma faixa neon de 1180px no desktop. Ele vem
            **depois** da dica de propósito: a ordem de foco por teclado passa
            pelo campo, lê a instrução e chega ao botão, que é o secundário. */}
        <Botao type="submit" disabled={enviando}>
          {enviando ? "Validando…" : "Validar"}
        </Botao>
      </form>

      {/* ⚠️ **A região existe no DOM sempre, mesmo vazia**, e é isso que faz o
          `aria-live` funcionar: leitor de tela só anuncia mudança dentro de uma
          região que já estava lá — inserir a região junto com o texto não
          dispara anúncio nenhum. É a mesma regra que o `AvisoDeErro` carrega. */}
      <div className={estilos.painel} aria-live="assertive">
        {resultado && <Veredicto resultado={resultado} />}
      </div>

      <AvisoDeErro mensagem={erro} />
    </div>
  );
}

/**
 * A palavra e o detalhe — o veredito em texto (Story 5.3).
 *
 * **Palavra e detalhe saem de duas tabelas**, e as duas vêm do
 * `EXPERIENCE.md#Os quatro vereditos da portaria`. A cor, o símbolo e o corpo de
 * 46px são o terceiro e o quarto canais, e entram na Story 5.4 — aqui o veredito
 * já é legível e já é completo, só não é legível a três metros.
 *
 * ⚠️ **`EVENTO_ERRADO` não nomeia o outro show**, e é a única linha em que esta
 * tela se afasta da tabela do `EXPERIENCE.md` (decisão do Igor). O detalhe lá é
 * "de qual show o ingresso é"; devolver o nome de um evento a uma portaria que
 * não foi escalada nele é exatamente o que o AD-7 existe para impedir. A resposta
 * da API nem carrega o dado — não há como esta tela mudar de ideia sozinha.
 */
function Veredicto({ resultado }: { resultado: ResultadoDaValidacao }) {
  return (
    <div className={estilos.veredito}>
      <p className={estilos.palavra}>{PALAVRA[resultado.resultado]}</p>
      <p className={estilos.detalhe}>{detalhe(resultado)}</p>
    </div>
  );
}

/** As quatro palavras do `EXPERIENCE.md`, sem sinônimo e sem tradução livre. */
const PALAVRA: Record<Veredito, string> = {
  VALIDO: "VÁLIDO",
  INVALIDO: "INVÁLIDO",
  JA_UTILIZADO: "JÁ UTILIZADO",
  EVENTO_ERRADO: "EVENTO ERRADO",
};

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
      // Sem o nome do outro show, de propósito — ver o docstring do `Veredicto`.
      return "Este ingresso é de outro show.";
    case "INVALIDO":
      // A frase é a do `EXPERIENCE.md`, e ela vale também para o código que não
      // é de ingresso nenhum: sem linha no banco, não há assinatura que confira.
      return "Assinatura não confere.";
  }
}

const MENSAGEM_GENERICA =
  "Não foi possível validar agora. Tente de novo em instantes.";

/**
 * Mesma convenção do resto do frontend: **o texto vem do `codigo`, nunca da
 * `mensagem` do servidor** — aquela é para humano e pode mudar sem quebrar
 * ninguém; o `codigo` é a parte estável do contrato.
 *
 * ⚠️ **Nenhum dos quatro vereditos passa por aqui.** Eles chegam em `200` e são
 * o produto desta tela; o que cai neste caminho é recusa de atendimento. Confundir
 * as duas coisas faria "ingresso inválido" aparecer como falha da aplicação.
 *
 * ⚠️ **`EVENTO_NAO_ABERTO` tem frase própria, e ela pede recarregar em vez de
 * tentar de novo.** A janela abre por relógio: quem deixou a tela aberta desde a
 * tarde tem um leitor que a API não atende mais — "tente de novo em instantes"
 * seria verdade só daqui a horas.
 */
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "SEM_ESCALA_NO_EVENTO") {
    return "Você não está escalado para este evento. Volte aos seus turnos.";
  }
  if (codigo === "EVENTO_NAO_ABERTO") {
    return "A porta deste evento ainda não abriu. Recarregue a página quando estiver na hora.";
  }
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    return "Sua sessão expirou. Entre de novo para continuar.";
  }
  return MENSAGEM_GENERICA;
}
