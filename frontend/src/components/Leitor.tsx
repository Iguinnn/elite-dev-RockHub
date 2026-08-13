"use client";

import { useEffect, useRef, useState } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Veredito from "@/components/Veredito";
import { ErroDaApi } from "@/lib/api";
import { validarCodigo, type ResultadoDaValidacao } from "@/lib/validacao";

import estilos from "./Leitor.module.css";

/**
 * Os estados da câmera (Story 5.5).
 *
 * **`abrindo` existe separado de `lendo`** porque entre o toque no botão e o
 * primeiro quadro há duas esperas reais: baixar o `@zxing/browser` (~200 kB, que
 * só chegam agora) e o navegador perguntar da permissão. Sem o estado
 * intermediário, o botão ficaria mudo nesse intervalo e a pessoa tocaria de
 * novo.
 *
 * **Os três últimos são desfechos, não erros de aplicação**, e por isso não
 * passam pelo `<AvisoDeErro>`: câmera negada não é falha do RockHub, é uma
 * escolha de quem está na porta — e o campo manual continua ali, funcionando.
 */
type EstadoDaCamera =
  | "desligada"
  | "abrindo"
  | "lendo"
  | "negada"
  | "ausente"
  | "sem-suporte";

/**
 * O leitor da porta: campo manual (5.3) e câmera (5.5).
 *
 * **Ilha porque validar é a única coisa que acontece nesta tela**, e ela
 * acontece dezenas de vezes seguidas sem recarregar nada. O cabeçalho com o nome
 * do show é Server Component; daqui para baixo é estado.
 *
 * ⚠️ **Enter valida, e é o requisito, não uma conveniência.** O
 * `EXPERIENCE.md#Interaction Primitives` diz com todas as letras: *"o operador
 * não deve precisar mirar num botão"*. É `<form onSubmit>` e não `onKeyDown`: a
 * submissão implícita do formulário de um campo só é comportamento nativo do
 * navegador, funciona com o "Ir" do teclado do celular e não custa uma linha de
 * JavaScript.
 *
 * ⚠️ **A câmera é opt-in, por botão** (decisão do Igor). Ela evita o pior padrão
 * possível: pedir permissão assim que a página abre, antes de a pessoa querer
 * usá-la — negada uma vez, o navegador lembra, e recuperar exige mexer nas
 * configurações do site. Aqui a permissão é pedida no toque, quando o pedido tem
 * contexto.
 *
 * ⚠️ **O veredito não some sozinho** (`EXPERIENCE.md#veredito`): ele fica até a
 * próxima validação substituí-lo. A portaria precisa poder olhar duas vezes com
 * a fila esperando, e um resultado que se apaga por conta própria obriga a ler
 * no susto. O que o limpa é a submissão seguinte — ação explícita de quem está
 * lendo, não um `setTimeout`.
 *
 * **A apresentação a três metros — cor, símbolo e corpo de 46px — mora no
 * `<Veredito>`** desde a Story 5.4. Este arquivo decide *quando* há veredito;
 * o outro decide como ele se lê.
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
  const [camera, setCamera] = useState<EstadoDaCamera>("desligada");

  const campo = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const controles = useRef<{ stop: () => void } | null>(null);
  // ⚠️ **A trava que cumpre o AC "o mesmo QR lido duas vezes em sequência rápida
  // dispara uma validação só"** — e ela é `ref`, não `state`, porque precisa
  // valer **dentro do mesmo quadro**: o `zxing` chama o callback a cada frame
  // decodificado, e um `setState` só chegaria no render seguinte, depois de duas
  // ou três leituras já terem passado. Sem timer nenhum: o scanner para na
  // primeira leitura e só reabre no próximo pedido, então o AC se cumpre por
  // construção.
  const jaLeu = useRef(false);

  async function enviar(bruto: string, devolverFoco = true) {
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
    if (!bruto.trim()) {
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
      setResultado(await validarCodigo(eventoId, bruto));
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
      // ⚠️ **O foco volta ao campo nos dois caminhos — quando veio do campo.**
      // Sem isto, depois de clicar em *Validar* o foco fica no botão e o Enter
      // seguinte reenvia o mesmo código em vez de mandar o próximo; o defeito só
      // aparece para quem usa o botão, que é justamente quem está com uma mão
      // só.
      //
      // ⚠️ **Vindo da câmera, o foco NÃO volta**, e é por isso que o parâmetro
      // existe: focar um campo de texto num celular abre o teclado, que come
      // metade da tela justamente no instante em que a portaria está lendo o
      // veredito e virando para a próxima pessoa da fila.
      if (devolverFoco) campo.current?.focus();
    }
  }

  // A referência ao `enviar` mais recente, para o efeito da câmera não precisar
  // dele nas dependências. Sem isto, o efeito recomeçaria a cada tecla digitada
  // no campo — desligando e religando a câmera no meio da leitura.
  const enviarAtual = useRef(enviar);
  useEffect(() => {
    enviarAtual.current = enviar;
  });

  function desligarCamera() {
    controles.current?.stop();
    controles.current = null;
  }

  // ⚠️ **A câmera para ao sair da tela, e isso não é higiene opcional.** O
  // `BrowserMultiFormatReader` segura o `MediaStream`; sem este `stop()`, a luz
  // da câmera continua acesa depois de navegar para outra rota — o que, na
  // porta, lê como aplicativo travado, e é o tipo de coisa que faz alguém matar
  // o app no meio do turno.
  //
  // **Efeito próprio com `[]`**, separado do que liga a câmera: o de baixo roda
  // de novo a cada troca de estado, e a limpeza que importa aqui é a da
  // desmontagem.
  useEffect(() => desligarCamera, []);

  useEffect(() => {
    if (camera !== "abrindo") return;

    let cancelado = false;

    (async () => {
      // ⚠️ **`navigator.mediaDevices` é `undefined` fora de contexto seguro** —
      // `https` ou `localhost`, e nada mais. Um celular abrindo
      // `http://192.168.0.x:3000` cai aqui, e sem esta guarda o `await` abaixo
      // levantaria `TypeError` dentro de um efeito, que vira erro não tratado em
      // vez de frase na tela. Está registrado em `README.md#o-que-não-está-pronto`.
      if (typeof navigator === "undefined" || !navigator.mediaDevices) {
        setCamera("sem-suporte");
        return;
      }

      try {
        // ⚠️ **`import()` dinâmico, e é aqui que ele se paga.** São ~200 kB que
        // ficam fora do primeiro carregamento da tela mais sensível a tempo do
        // produto — quem só vai digitar o código nunca os baixa. É o que a
        // techspec pede por `next/dynamic`; `next/dynamic` embrulha
        // *componente*, e o `@zxing/browser` é biblioteca, então o mecanismo
        // certo para o mesmo efeito é o `import()` — e ele já é só do navegador,
        // porque só roda dentro deste efeito.
        //
        // **Descartei a `BarcodeDetector` nativa** (zero bytes, e inexistente no
        // Safari do iPhone — que é metade da fila) e o import estático.
        const { BrowserMultiFormatReader } = await import("@zxing/browser");
        if (cancelado || !video.current) return;

        jaLeu.current = false;
        const leitor = new BrowserMultiFormatReader();

        // ⚠️ **`facingMode: environment`, e não `decodeFromVideoDevice(undefined)`.**
        // Aquele pega o primeiro dispositivo da lista, que no celular costuma ser
        // a câmera **frontal**: a portaria apontaria o telefone para o próprio
        // rosto. `ideal` e não `exact` de propósito — num notebook com uma
        // webcam só, `exact` falharia como "câmera ausente" e a tela mentiria.
        const abertos = await leitor.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } } },
          video.current,
          (leitura) => {
            // O callback roda a cada quadro, e a maioria vem sem QR nenhum.
            if (!leitura || jaLeu.current) return;
            jaLeu.current = true;
            desligarCamera();
            setCamera("desligada");
            void enviarAtual.current(leitura.getText(), false);
          },
        );

        // ⚠️ **A corrida entre o primeiro quadro e a resolução da promessa é
        // real**: um QR já enquadrado quando a câmera abre é decodificado antes
        // de `abertos` existir, e aí o `desligarCamera()` do callback não tinha
        // o que desligar. Este ramo é quem para a câmera nesse caso.
        if (cancelado || jaLeu.current) {
          abertos.stop();
          return;
        }

        controles.current = abertos;
        setCamera("lendo");
      } catch (falha) {
        if (cancelado) return;
        setCamera(motivoDaFalha(falha));
      }
    })();

    return () => {
      cancelado = true;
    };
  }, [camera]);

  function alternarCamera() {
    if (camera === "abrindo" || camera === "lendo") {
      desligarCamera();
      setCamera("desligada");
      return;
    }
    // Recomeça de `abrindo` mesmo vindo de `negada`/`ausente`: quem tocou de
    // novo pode ter acabado de liberar a permissão nas configurações do
    // navegador, e insistir é a única saída que a tela pode oferecer.
    setCamera("abrindo");
  }

  const lendo = camera === "abrindo" || camera === "lendo";

  return (
    <div className={estilos.leitor}>
      {/* ⚠️ **A câmera vem ANTES do campo**, e a ordem é a da jornada 2 do
          `EXPERIENCE.md`: Ana aponta a câmera para a fila inteira e só digita
          quando a leitura falha — "câmera falha numa quarta pessoa. Ana digita o
          código no campo abaixo". O campo é o plano B, e fica onde o plano B
          fica. */}
      <div className={estilos.bloco}>
        <button
          type="button"
          className={estilos.botaoCamera}
          onClick={alternarCamera}
          disabled={camera === "abrindo"}
        >
          {ROTULO_DA_CAMERA[camera]}
        </button>

        {/* O `<video>` só existe enquanto a câmera está no ar: um elemento
            escondido com `display:none` não toca em vários navegadores, e o
            `zxing` precisa dele tocando para decodificar. */}
        {lendo && (
          <video
            ref={video}
            className={estilos.video}
            // Os três são obrigatórios para o vídeo tocar sozinho no iOS sem
            // abrir em tela cheia. `muted` inclusive: sem ele o Safari recusa o
            // autoplay, e a mira fica preta.
            muted
            playsInline
            autoPlay
          />
        )}

        {AVISO_DA_CAMERA[camera] && (
          // Não é `<AvisoDeErro>` (que é `role="alert"` e tinta de erro): câmera
          // negada não é falha da aplicação, e o campo abaixo continua sendo um
          // caminho inteiro. Pintar isto de `--brasa` diria que o turno parou.
          <p className={estilos.avisoCamera}>{AVISO_DA_CAMERA[camera]}</p>
        )}
      </div>

      {/* ⚠️ **A região existe no DOM sempre, mesmo vazia**, e é isso que faz o
          `aria-live` funcionar: leitor de tela só anuncia mudança dentro de uma
          região que já estava lá — inserir a região junto com o texto não
          dispara anúncio nenhum. É a mesma regra que o `AvisoDeErro` carrega.

          ⚠️ **Ela fica ACIMA do formulário desde a Story 5.4**, e a razão é de
          leitura a três metros: o que se lê à distância é o topo da tela, e o
          campo com a dica empurrava o resultado para a dobra no celular. Aqui
          ele ocupa o vão que o `<video>` deixa ao desmontar — a câmera lê, se
          desliga, e o veredito nasce onde a mira estava.

          A ordem de foco por teclado não sofre: o bloco não é focável, e quem o
          anuncia é o `aria-live`, não a posição. */}
      <div className={estilos.painel} aria-live="assertive">
        {resultado && <Veredito resultado={resultado} />}
      </div>

      <form
        className={estilos.formulario}
        onSubmit={(submissao) => {
          submissao.preventDefault();
          void enviar(codigo);
        }}
      >
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
          // ⚠️ **Sem `autoFocus`, e ele existiu até a Story 5.5.** Enquanto o
          // campo era a tela inteira, o teclado subindo sozinho economizava um
          // toque; com a câmera, o caminho primário passou a ser outro e o
          // teclado passou a cobrir metade da tela — inclusive o botão e a mira
          // — antes de a pessoa pedir. O foco continua sendo devolvido ao campo
          // depois de cada validação **digitada**, que é onde ele ajuda.
          //
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

      <AvisoDeErro mensagem={erro} />
    </div>
  );
}

/**
 * O rótulo do botão em cada estado.
 *
 * **`abrindo` diz "Abrindo…" e o botão fica desativado**: é o intervalo do
 * download da biblioteca mais o diálogo de permissão, e um botão que não
 * responde ali seria tocado de novo.
 */
const ROTULO_DA_CAMERA: Record<EstadoDaCamera, string> = {
  desligada: "Ler pela câmera",
  abrindo: "Abrindo…",
  lendo: "Parar a câmera",
  negada: "Tentar a câmera de novo",
  ausente: "Tentar a câmera de novo",
  "sem-suporte": "Tentar a câmera de novo",
};

/**
 * A frase de cada desfecho da câmera. `null` nos três estados em que não há o
 * que explicar.
 *
 * ⚠️ **Toda frase termina lembrando do campo**, e é o requisito do AC: a câmera
 * falhar não pode parar o turno. Quem está na porta precisa saber, na mesma
 * linha, que ainda tem como trabalhar.
 */
const AVISO_DA_CAMERA: Record<EstadoDaCamera, string | null> = {
  desligada: null,
  abrindo: null,
  lendo: null,
  negada:
    "A câmera foi bloqueada para este site. Libere nas configurações do navegador, ou digite o código no campo abaixo.",
  ausente:
    "Não encontrei nenhuma câmera neste aparelho. Digite o código no campo abaixo.",
  "sem-suporte":
    "O navegador só libera a câmera em endereços seguros (https). Digite o código no campo abaixo.",
};

/**
 * Traduz a falha do `getUserMedia` em um dos três desfechos.
 *
 * ⚠️ **Os nomes vêm do padrão, e são conferidos por `name`, nunca pela
 * mensagem** — a mensagem é texto do navegador, muda entre eles e é traduzida.
 * `NotAllowedError` é permissão negada; `NotFoundError` e `OverconstrainedError`
 * são "não há câmera que sirva". Qualquer outra coisa cai em `ausente`, que é o
 * desfecho mais honesto para uma falha desconhecida: a câmera não vai abrir, e a
 * frase manda usar o campo.
 */
function motivoDaFalha(falha: unknown): EstadoDaCamera {
  const nome = falha instanceof Error ? falha.name : "";

  if (nome === "NotAllowedError" || nome === "SecurityError") return "negada";
  return "ausente";
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
