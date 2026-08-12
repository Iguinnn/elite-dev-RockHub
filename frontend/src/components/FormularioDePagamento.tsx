"use client";

import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import { ErroDaApi, chamarApi } from "@/lib/api";
import type { ReservaSaida } from "@/lib/reservas";

import estilos from "./FormularioDePagamento.module.css";

/**
 * O checkout da reserva (Story 3.8) — dados do comprador, meio de pagamento e a
 * cobrança.
 *
 * ⚠️ **Ilha `"use client"`, e a página continua Server Component.** A diretiva é
 * do **módulo**: um `"use client"` no `page.tsx` arrastaria o cabeçalho, os itens
 * e o total para o cliente. Mesmo precedente do `EscolhaDeIngressos` e do
 * `FormularioPublicacao` — entre a página e este arquivo passam **dados**, nunca
 * funções.
 *
 * **Por que o formulário é ilha e não Server Action:** ele muda de forma conforme
 * a escolha do meio (o bloco do cartão aparece, o do Pix aparece com QR), e isso
 * é estado de tela que não vai ao servidor. O projeto inteiro fala com a API por
 * `chamarApi`, e esta tela não abre exceção.
 *
 * **O Pix é enfeite honesto.** O QR e o código copia-e-cola são gerados aqui,
 * aleatórios, e não atravessam a rede: o backend recebe `meio: PIX` e aprova. O
 * aviso no topo diz isso com todas as letras — simular cobrança de verdade seria
 * mentira com custo de manutenção. **O caminho da recusa é o cartão** (final
 * `0002`), que é o item pontuado do enunciado.
 *
 * ⚠️ **O código do Pix nasce no clique, nunca na renderização.** Gerar aleatório
 * durante o render faria o HTML do servidor divergir do primeiro render do
 * cliente — erro de hidratação clássico. Como o bloco do Pix só existe depois de
 * alguém escolher Pix, gerá-lo no `onChange` resolve o problema por construção.
 */
/**
 * Quanto a espera da confirmação aguenta antes de devolver o formulário.
 *
 * Doze segundos: o `POST` costuma responder em menos de um, e o `router.refresh()`
 * é uma segunda ida à rede. O número não é um limite de paciência — é o ponto em
 * que "está demorando" vira "alguma coisa não voltou", e a pessoa precisa de uma
 * saída em vez de uma frase parada.
 */
const ESPERA_MAXIMA_MS = 20_000;

/**
 * O piso de tempo que a confirmação fica na tela.
 *
 * ⚠️ **Sem ele a tela de espera não existe na prática.** O gateway é simulado e o
 * banco é local: o `POST` responde em ~100ms, o `router.refresh()` em mais um
 * pouco, e o painel aparecia e sumia antes de alguém registrar que apareceu.
 * Piscar por 90ms é pior que não ter nada: vira um tremor na tela sem informação
 * nenhuma.
 *
 * **Seis segundos, por pedido do Igor** (2026-08-12). Foi para 900ms primeiro, o
 * suficiente para a frase não piscar, e ele pediu de 5 a 7 — a espera aqui não é
 * só feedback, é a encenação de uma cobrança sendo processada, e uma cobrança que
 * volta instantânea não parece uma cobrança. Este número é a duração do teatro,
 * não uma medida de latência.
 *
 * O piso **não** atrasa a resposta do servidor: a cobrança já foi processada e
 * confirmada quando o relógio corre; o que ele segura é a troca de tela. E é um
 * mínimo, não um acréscimo — com um gateway de verdade que demore mais que isso,
 * ele deixa de ter efeito.
 */
const ESPERA_MINIMA_MS = 6_000;

/** Segura o que falta para a espera completar o piso — ver `ESPERA_MINIMA_MS`. */
function completarEsperaMinima(inicio: number): Promise<void> {
  const decorrido = Date.now() - inicio;
  const resto = ESPERA_MINIMA_MS - decorrido;
  return resto > 0
    ? new Promise((resolver) => setTimeout(resolver, resto))
    : Promise.resolve();
}

export default function FormularioDePagamento({
  reservaId,
  nomeDaConta,
}: {
  reservaId: string;
  /** O nome da conta, que preenche o campo — e que a 3.9 grava no ingresso. */
  nomeDaConta: string;
}) {
  const router = useRouter();

  const [meio, setMeio] = useState<Meio | null>(null);
  const [codigoPix, setCodigoPix] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // ⚠️ **A espera é um estado próprio, e não o `enviando` do botão.** Ela começa
  // no clique e **não** termina quando a resposta chega: termina quando o
  // servidor devolve a página com a reserva no estado novo e este formulário
  // deixa de existir. Entre uma coisa e outra há o `router.refresh()`, que é uma
  // segunda ida à rede — e era nela que a tela ficava mostrando o checkout de uma
  // reserva já paga, com o botão "Pagar" clicável.
  const [confirmando, setConfirmando] = useState(false);
  const painelDaEspera = useRef<HTMLElement | null>(null);

  // ⚠️ **A página encolhe embaixo de quem clicou, e por isso o painel se traz
  // para a vista.** O formulário é alto — quatro campos, os dois meios, o bloco
  // do cartão ou o QR do Pix — e a espera tem três linhas. Trocar um pelo outro
  // derruba a altura do documento; o navegador grampeia o scroll no novo limite
  // e a viewport pula. Quem tinha rolado até o botão "Pagar" ficava olhando para
  // o total, com o painel fora de vista: a tela de espera existia e ninguém a
  // via, que foi exatamente o relato.
  //
  // `block: "center"` e não `"start"`: o painel é curto, e encostá-lo no topo
  // deixa meia tela vazia embaixo. `behavior: "auto"` porque rolagem suave é
  // movimento, e movimento é o que o `EXPERIENCE.md` recusa — aqui o salto é
  // instantâneo, como o resto do produto.
  useEffect(() => {
    if (!confirmando) return;
    painelDaEspera.current?.scrollIntoView({ block: "center", behavior: "auto" });
  }, [confirmando]);

  // ⚠️ **A rede de baixo da espera.** `router.refresh()` não devolve promessa: se
  // ele falhar, nada avisa este componente e a tela ficaria parada na frase de
  // confirmação para sempre. O relógio devolve o formulário com uma saída — e a
  // frase dele **não** manda pagar de novo, porque a essa altura a cobrança pode
  // ter sido aprovada e é o servidor quem sabe.
  useEffect(() => {
    if (!confirmando) return;

    const relogio = setTimeout(() => {
      setConfirmando(false);
      setEnviando(false);
      setErro(
        "A confirmação está demorando. Recarregue a página para ver como ficou " +
          "sua reserva — não pague de novo.",
      );
    }, ESPERA_MAXIMA_MS);

    return () => clearTimeout(relogio);
  }, [confirmando]);

  // Máscaras no estado, e não só no `value` do DOM: o backend descarta a
  // pontuação de qualquer jeito, então elas existem para quem digita — e o
  // estado precisa acompanhar para o cursor não pular.
  const [cpf, setCpf] = useState("");
  const [telefone, setTelefone] = useState("");

  function escolher(novoMeio: Meio) {
    setMeio(novoMeio);
    setErro(null);
    if (novoMeio === "PIX" && !codigoPix) {
      setCodigoPix(gerarCodigoPix());
    }
  }

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);

    if (!meio) {
      setErro("Escolha como você quer pagar.");
      return;
    }

    setEnviando(true);
    // A espera cobre os dois meios: no cartão ela começa no "Pagar", no Pix no
    // "Cobrança paga". Os dois passam por aqui — o Pix não tem caminho próprio.
    setConfirmando(true);
    const inicioDaEspera = Date.now();
    const dados = new FormData(evento.currentTarget);

    try {
      await chamarApi<ReservaSaida>(`/reservas/${reservaId}/pagamento`, {
        method: "POST",
        body: JSON.stringify({
          nome: dados.get("nome"),
          email: dados.get("email"),
          cpf: dados.get("cpf"),
          telefone: dados.get("telefone"),
          meio,
          // Os quatro só existem no DOM quando o meio é cartão — com Pix eles
          // viram `null`, que é o que o schema do backend espera.
          numero_cartao: dados.get("numero_cartao"),
          nome_no_cartao: dados.get("nome_no_cartao"),
          validade: dados.get("validade"),
          cvv: dados.get("cvv"),
        }),
      });

      // ⚠️ **`refresh()` sem `push`: o endereço é o mesmo, o que muda é o
      // estado da reserva.** A página é Server Component e relê `GET
      // /reservas/{id}`; com `PAGA`, ela troca o cronômetro e este formulário
      // pela confirmação. Sem o `refresh`, a tela continuaria mostrando o
      // checkout de uma reserva já paga.
      await completarEsperaMinima(inicioDaEspera);
      router.refresh();
      // Sem desligar `confirmando`: a página vai voltar `PAGA` e este formulário
      // sai do ar junto com a espera. Desligar aqui devolveria o checkout por
      // uma fração de segundo, com "Pagar" clicável, sobre uma reserva já paga.
    } catch (erroCapturado) {
      if (erroCapturado instanceof ErroDaApi) {
        // ⚠️ **Recusa, prazo vencido e "não está mais pendente" também dão
        // `refresh`**: os três mudaram o estado no servidor, e a página tem uma
        // cara para cada um. Mostrar só a frase de erro deixaria o formulário
        // no ar oferecendo pagar de novo uma reserva que já morreu.
        //
        // A espera continua ligada nestes três pelo mesmo motivo do caminho
        // feliz: quem troca a tela é o servidor, e até ele responder não há o
        // que a pessoa possa fazer aqui.
        if (ESTADO_MUDOU.has(erroCapturado.codigo)) {
          // O mesmo piso do caminho feliz: a recusa do cartão `0002` é a mais
          // rápida de todas, e sem ele a tela pisca e já mostra o resultado.
          await completarEsperaMinima(inicioDaEspera);
          router.refresh();
          return;
        }
        setErro(mensagemParaCodigo(erroCapturado.codigo));
      } else {
        setErro(MENSAGEM_GENERICA);
      }

      // O mesmo piso dos outros dois caminhos, e aqui ele evita um tremor: sem
      // ele o painel de 260px aparece e some em ~100ms, e a tela dá um solavanco
      // antes de mostrar a mensagem. Atrasar o erro em menos de um segundo custa
      // pouco perto disso.
      await completarEsperaMinima(inicioDaEspera);

      // Só os erros que deixam a pessoa **nesta** tela desligam a espera: dados
      // inválidos, sessão caída, rede fora. Aí o formulário volta com o que foi
      // digitado — ele nunca desmontou, e é por isso que não desmonta.
      setConfirmando(false);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      {/* ⚠️ **Os pontinhos contrariam o `EXPERIENCE.md#Carregando`, e é decisão
          do Igor** (2026-08-12). O documento é literal — *"Sem spinner. A
          estrutura da página aparece com os fios e as etiquetas no lugar, e o
          conteúdo preenche. Nada gira, nada pulsa."* — e esta é a **única**
          animação do produto: não há outro `@keyframes` em nenhum CSS daqui.
          A primeira versão saiu sem movimento, por causa da regra; ele pediu com,
          e o pedido dele vence o documento que ele mesmo escreveu.

          O que a exceção **não** abriu: nada desliza de uma lateral à outra
          (primeiro anti-padrão do `DESIGN.md`), nada gira, e o resto da tela
          continua sem transição.

          A anatomia do bloco segue a de qualquer outro: kicker em versalete,
          frase, fio de topo. `aria-live="polite"` e não `assertive` — a frase
          interessa a quem espera, mas interromper a leitura da página inteira
          para anunciá-la é o exagero que o cronômetro também evita. */}
      {confirmando && (
        <section
          ref={painelDaEspera}
          className={estilos.confirmando}
          aria-live="polite"
        >
          <p className="kicker">Pagamento</p>

          <p className={estilos.confirmandoFrase}>
            Confirmando a cobrança
            {/* `aria-hidden` porque os pontos são a reticência que saiu do
                texto: leitor de tela já ouviu a frase, e três marcadores
                pulando não acrescentam nada a ela. */}
            <span className={estilos.pontos} aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </p>

          <p className={estilos.confirmandoDetalhe}>
            Não feche esta página. Seus ingressos aparecem aqui em instantes.
          </p>
        </section>
      )}

      {/* ⚠️ **Escondido, e não desmontado.** Metade dos campos é não-controlada
          (nome, e-mail e os quatro do cartão vivem no DOM), então tirar o
          formulário da árvore apagaria tudo o que foi digitado — e um `422` de
          validade mal digitada devolveria a pessoa a um formulário vazio, tendo
          que redigitar o cartão inteiro. Com `display: none` o DOM continua lá e
          o `catch` só reexibe. Some da árvore de acessibilidade junto, então o
          leitor de tela não navega por um formulário que não está em uso. */}
      <form
        className={`${estilos.formulario} ${confirmando ? estilos.oculto : ""}`}
        onSubmit={aoEnviar}
      >
        <p className={estilos.titulo}>Pagamento</p>

        {/* ⚠️ O aviso vem **antes** dos campos, não depois do botão: quem lê
            depois de preencher já digitou o CPF de verdade. */}
        <p className={estilos.aviso}>
          <strong>Ambiente de avaliação.</strong> Use dados fictícios — nada além do
          nome é guardado. A cobrança por Pix é simulada e o QR não é válido;
          nenhum valor é cobrado em nenhum dos dois caminhos.
        </p>

        <Campo
          id="nome"
          name="nome"
          rotulo="Nome"
          defaultValue={nomeDaConta}
          autoComplete="name"
          maxLength={120}
          required
        />
        <Campo
          id="email"
          name="email"
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          maxLength={255}
          required
        />

        <div className={estilos.dupla}>
          <Campo
            id="cpf"
            name="cpf"
            rotulo="CPF"
            inputMode="numeric"
            placeholder="000.000.000-00"
            value={cpf}
            onChange={(e) => setCpf(mascararCpf(e.target.value))}
            required
          />
          <Campo
            id="telefone"
            name="telefone"
            rotulo="Telefone"
            inputMode="tel"
            placeholder="(00) 00000-0000"
            autoComplete="tel"
            value={telefone}
            onChange={(e) => setTelefone(mascararTelefone(e.target.value))}
            required
          />
        </div>

        {/* `<fieldset>` com `<legend>`, e não um `<div>` com um `<p>`: é o que faz
            o leitor de tela anunciar "Como você quer pagar" antes de cada opção. */}
        <fieldset className={estilos.meios}>
          <legend className={estilos.legenda}>Como você quer pagar</legend>

          <div className={estilos.opcoes}>
            {MEIOS.map(({ valor, rotulo }) => (
              <label
                key={valor}
                className={`${estilos.opcao} ${meio === valor ? estilos.opcaoAtiva : ""}`}
              >
                <input
                  className={estilos.radio}
                  type="radio"
                  name="meio"
                  value={valor}
                  checked={meio === valor}
                  onChange={() => escolher(valor)}
                />
                {rotulo}
              </label>
            ))}
          </div>
        </fieldset>

        {meio === "CARTAO" && (
          <div className={estilos.expansao}>
            {/* ⚠️ **`autoComplete="off"` nos quatro campos do cartão, e não os
                tokens `cc-*`** (code review da Epic 3). Eles estavam declarados
                como `cc-number`, `cc-name`, `cc-exp` e `cc-csc` — que é
                exatamente o que faz o navegador oferecer o **cartão salvo de
                verdade**, com um clique, três linhas abaixo de um aviso pedindo
                dados fictícios. O número completo então viajaria no corpo JSON até
                um gateway simulado. O backend está limpo (reduz a dígitos, compara
                o final e descarta, sem logar), mas pedir o dado é o problema, não
                o que se faz com ele depois. Num projeto que vai ser avaliado por
                gente abrindo a tela no próprio navegador, isso não passa. */}
            <p className={estilos.dicaDoCartao}>
              Qualquer número aprova. Para ver a recusa de propósito, use um cartão
              terminado em <code>0002</code>.
            </p>

            <Campo
              id="numero_cartao"
              name="numero_cartao"
              rotulo="Número do cartão"
              inputMode="numeric"
              placeholder="0000 0000 0000 0000"
              autoComplete="off"
              maxLength={23}
              required
            />
            <Campo
              id="nome_no_cartao"
              name="nome_no_cartao"
              rotulo="Nome impresso no cartão"
              autoComplete="off"
              maxLength={120}
              required
            />

            <div className={estilos.dupla}>
              <Campo
                id="validade"
                name="validade"
                rotulo="Validade"
                placeholder="MM/AA"
                autoComplete="off"
                maxLength={5}
                required
              />
              <Campo
                id="cvv"
                name="cvv"
                rotulo="CVV"
                inputMode="numeric"
                placeholder="000"
                autoComplete="off"
                maxLength={4}
                required
              />
            </div>
          </div>
        )}

        {meio === "PIX" && codigoPix && (
          <div className={estilos.expansao}>
            <div className={estilos.pix}>
              {/* `level="L"` e sem logotipo no meio: o código é fictício e o que
                  importa é ele **parecer** um QR de Pix na tela, não sobreviver a
                  dano. `aria-hidden` porque o código ao lado carrega a mesma
                  informação em texto — um QR anunciado por leitor de tela é ruído. */}
              <div className={estilos.qr} aria-hidden>
                <QRCodeSVG value={codigoPix} size={148} level="L" />
              </div>

              <div className={estilos.pixTexto}>
                <span className={estilos.rotuloDoCodigo}>Pix copia e cola</span>
                <code className={estilos.codigo}>{codigoPix}</code>
              </div>
            </div>
          </div>
        )}

        <AvisoDeErro mensagem={erro} />

        <div className={estilos.acao}>
          {/* ⚠️ **O texto do botão muda com o meio**, e é o que o Igor pediu: no
              Pix ele é o atalho do avaliador — "já paguei, siga" —, e no cartão é
              a cobrança de verdade. Um "Pagar" genérico nos dois deixaria a tela
              do Pix sem dizer o que o clique faz. */}
          <Botao type="submit" disabled={enviando}>
            {enviando ? "Processando…" : meio === "PIX" ? "Cobrança paga" : "Pagar"}
          </Botao>
        </div>
      </form>
    </>
  );
}

type Meio = "CARTAO" | "PIX";

const MEIOS: { valor: Meio; rotulo: string }[] = [
  { valor: "CARTAO", rotulo: "Cartão" },
  { valor: "PIX", rotulo: "Pix" },
];

/**
 * Os códigos que **mudaram o estado da reserva no servidor** — a tela relê em
 * vez de mostrar frase. Cada um tem uma cara própria na página.
 */
const ESTADO_MUDOU = new Set([
  "PAGAMENTO_RECUSADO",
  "RESERVA_EXPIRADA",
  "RESERVA_NAO_PENDENTE",
]);

const MENSAGEM_GENERICA =
  "Não foi possível concluir o pagamento agora. Tente de novo em instantes.";

/**
 * Mesma convenção do login, do cadastro, da publicação e da reserva: **o texto
 * vem do `codigo`, nunca da `mensagem` do servidor.**
 *
 * ⚠️ `NAO_AUTENTICADO` e `SEM_PERMISSAO` entram desde a primeira linha, e não
 * como remendo — foi o buraco que o code review da Epic 2 achou no formulário de
 * publicação. A sessão dura 8 horas (AD-15) e pode cair com a tela aberta.
 */
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "DADOS_INVALIDOS") {
    return "Confira os dados preenchidos: algum campo está incompleto ou fora do formato.";
  }
  if (codigo === "RESERVA_NAO_ENCONTRADA") {
    return "Esta reserva não existe mais.";
  }
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    return "Sua sessão expirou. Entre de novo para pagar.";
  }
  return MENSAGEM_GENERICA;
}

/**
 * Um código copia-e-cola de mentira, com cara de Pix.
 *
 * ⚠️ **Não é EMV de verdade e não pretende ser** — não tem CRC, não tem chave, e
 * um app de banco vai recusá-lo. É exatamente o que o aviso da tela promete. O
 * prefixo `00020126` existe só para o bloco parecer o que parece; inventar um
 * payload válido daria a impressão contrária ao que a tela diz.
 */
function gerarCodigoPix(): string {
  const aleatorio = Array.from({ length: 4 }, () =>
    Math.random().toString(36).slice(2, 10).toUpperCase(),
  ).join("");
  return `00020126${aleatorio}5204000053039865802BR5913ROCKHUB FAKE6009SAO PAULO`;
}

/** `000.000.000-00`, aplicada enquanto se digita. */
function mascararCpf(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  return digitos
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d{1,2})$/, ".$1-$2");
}

/** `(00) 00000-0000`, com o nono dígito opcional. */
function mascararTelefone(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  if (digitos.length <= 2) return digitos;
  const corpo = digitos.slice(2);
  const corte = digitos.length > 10 ? 5 : 4;
  return corpo.length <= corte
    ? `(${digitos.slice(0, 2)}) ${corpo}`
    : `(${digitos.slice(0, 2)}) ${corpo.slice(0, corte)}-${corpo.slice(corte)}`;
}
