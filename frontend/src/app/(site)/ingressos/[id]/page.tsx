import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";

import { dataPorExtenso, horaDeEntrada } from "@/lib/formato";
import { obterIngresso } from "@/lib/ingressos";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * O canhoto cheio, com o QR — Story 4.2.
 *
 * **As mesmas duas guardas de `/ingressos`**: sem sessão, `redirect` para o
 * login com o caminho de volta preservado; papel diferente de `CLIENTE`,
 * `redirect` para a raiz. Depois delas, `notFound()` cobre "não existe ou
 * não é seu" — o `404` único que a API já responde.
 *
 * **Existe num lugar só** (decisão da techspec): a reserva paga
 * (`/reservas/{id}`) não desenha mais canhoto, só a confirmação e o link para
 * cá. Duas versões do mesmo canhoto convivendo obrigaria quem lê a decidir
 * qual é o ingresso de verdade.
 */
export default async function CanhotoDoIngresso({
  params,
}: PageProps<"/ingressos/[id]">) {
  const { id } = await params;

  const usuario = await obterUsuarioDaSessao();
  if (!usuario) {
    redirect(`/login?voltar=${encodeURIComponent(`/ingressos/${id}`)}`);
  }
  if (usuario.papel !== "CLIENTE") {
    redirect("/");
  }

  const resultado = await obterIngresso(id);

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <Link href="/ingressos" className={estilos.voltar}>
          ← Meus ingressos
        </Link>
        <p className={estilos.aviso}>
          Não foi possível carregar este ingresso agora. Tente de novo em
          instantes.
        </p>
      </section>
    );
  }

  const ingresso = resultado.ingresso;
  const casa = [ingresso.evento_local, ingresso.evento_cidade]
    .filter(Boolean)
    .join(" · ");
  // "Quebrado em blocos" (techspec da 4.2): o `codigo` é `ID.ASSINATURA`, uma
  // palavra só de ~80 caracteres. Espaçar em grupos de 4 dá ao olho pontos de
  // parada para conferir contra a tela da porta, sem mudar o valor copiado —
  // o espaço é só de exibição.
  const codigoEmBlocos = ingresso.codigo.match(/.{1,4}/g)?.join(" ") ?? ingresso.codigo;

  return (
    <section className={estilos.pagina}>
      <Link href="/ingressos" className={estilos.voltar}>
        ← Meus ingressos
      </Link>

      {ingresso.usado_em && (
        // Neutro, não vermelho (EXPERIENCE.md#veredito): não é fraude nem
        // falha, é um canhoto que já cumpriu o que prometia.
        <p className={estilos.jaUtilizado}>
          <strong>Já utilizado.</strong> Entrou às {horaDeEntrada(ingresso.usado_em)}.
        </p>
      )}

      <div className={estilos.canhoto}>
        <div className={estilos.talao}>
          <span className="kicker">Ingresso</span>
          <h1 className={estilos.nomeDoEvento}>{ingresso.evento_nome}</h1>
          <p className={estilos.dataDoEvento}>
            {dataPorExtenso(ingresso.evento_data_hora)}
          </p>
          <p className={estilos.casa}>{casa}</p>

          <dl className={estilos.dados}>
            <dt>Setor</dt>
            <dd>{ingresso.setor_nome}</dd>
            <dt>Titular</dt>
            <dd>{ingresso.titular_nome}</dd>
          </dl>
        </div>

        <div className={estilos.corpo}>
          {/* `aria-hidden`: o código ao lado carrega a mesma informação em
              texto — um QR anunciado por leitor de tela é ruído (precedente
              do QR do Pix, `FormularioDePagamento`). */}
          <div className={estilos.qr} aria-hidden>
            <QRCodeSVG
              value={ingresso.codigo}
              size={180}
              level="L"
              bgColor="var(--cal)"
              fgColor="var(--breu)"
            />
          </div>

          {/* `<code>`, não `<span>`: dado de máquina (UX-DR9 — o código
              aparece em texto onde é apresentado). */}
          <code className={estilos.codigo}>{codigoEmBlocos}</code>
        </div>
      </div>
    </section>
  );
}
