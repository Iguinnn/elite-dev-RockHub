"use client";

import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useState, type FormEvent } from "react";

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
      router.refresh();
    } catch (erroCapturado) {
      if (erroCapturado instanceof ErroDaApi) {
        // ⚠️ **Recusa, prazo vencido e "não está mais pendente" também dão
        // `refresh`**: os três mudaram o estado no servidor, e a página tem uma
        // cara para cada um. Mostrar só a frase de erro deixaria o formulário
        // no ar oferecendo pagar de novo uma reserva que já morreu.
        if (ESTADO_MUDOU.has(erroCapturado.codigo)) {
          router.refresh();
          return;
        }
        setErro(mensagemParaCodigo(erroCapturado.codigo));
        return;
      }
      setErro(MENSAGEM_GENERICA);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className={estilos.formulario} onSubmit={aoEnviar}>
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
            autoComplete="cc-number"
            maxLength={23}
            required
          />
          <Campo
            id="nome_no_cartao"
            name="nome_no_cartao"
            rotulo="Nome impresso no cartão"
            autoComplete="cc-name"
            maxLength={120}
            required
          />

          <div className={estilos.dupla}>
            <Campo
              id="validade"
              name="validade"
              rotulo="Validade"
              placeholder="MM/AA"
              autoComplete="cc-exp"
              maxLength={5}
              required
            />
            <Campo
              id="cvv"
              name="cvv"
              rotulo="CVV"
              inputMode="numeric"
              placeholder="000"
              autoComplete="cc-csc"
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
