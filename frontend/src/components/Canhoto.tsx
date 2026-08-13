import { QRCodeSVG } from "qrcode.react";

import { dataPorExtenso } from "@/lib/formato";
import type { IngressoDetalhe } from "@/lib/ingressos";

import estilos from "./Canhoto.module.css";

/**
 * O canhoto: ficha, picote, QR e código — o corpo da Story 4.2, extraído na 4.3.
 *
 * **Por que ele virou componente agora, e não na 4.2.** Lá a decisão foi
 * **não** extrair entre `/reservas/{id}` e `/ingressos/{id}`, e ela continua
 * certa: aqueles dois endereços falavam de coisas diferentes — um da compra,
 * outro do ingresso — e desenhar o mesmo objeto nos dois obrigava quem lia a
 * escolher qual era o real. Aqui os dois endereços (`/ingressos/{id}` e
 * `/i/{token}`) falam **do mesmo ingresso para pessoas diferentes**, e eles
 * serem idênticos é o requisito, não o defeito: quem abre o link vai entrar
 * com ele.
 *
 * ⚠️ **Sem `<Link>` de voltar e sem a faixa de "já utilizado".** As duas são
 * chrome de cada página — o dono volta para *Meus ingressos*, quem chegou pelo
 * link não tem para onde voltar —, e a faixa é desenhada pelas duas telas por
 * fora. Trazê-las para cá faria o componente conhecer quem está olhando, que é
 * exatamente o que ele não pode saber.
 *
 * Sem `"use client"`, pelo mesmo motivo do `Campo` e do `Botao`: nenhuma
 * interação própria. O QR é SVG renderizado no servidor.
 */
export default function Canhoto({ ingresso }: { ingresso: IngressoDetalhe }) {
  const casa = [ingresso.evento_local, ingresso.evento_cidade]
    .filter(Boolean)
    .join(" · ");
  // "Quebrado em blocos" (techspec da 4.2): o `codigo` são 8 símbolos de base32
  // de Crockford, e em grupos de 4 ele sai `9K4M 7QX2`. O espaço dá ao olho um
  // ponto de parada para ler o código em voz alta na fila, sem mudar o valor
  // codificado — ele é só de exibição, e o QR recebe `ingresso.codigo` puro.
  //
  // ⚠️ **Esta linha não mudou quando o código encolheu de 80 para 8 caracteres**
  // (techspec `docs/techspec-codigo-curto.md`): o `match(/.{1,4}/g)` já fazia o
  // certo nos dois tamanhos. Quem valida na porta normaliza a entrada — sobem as
  // letras, caem espaços e hífens —, então o que está na tela pode ser digitado
  // exatamente como se lê.
  const codigoEmBlocos =
    ingresso.codigo.match(/.{1,4}/g)?.join(" ") ?? ingresso.codigo;

  return (
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
          {/* ⚠️ **Hex literal, e não `var(--cal)`/`var(--breu)`.** São os mesmos
              dois valores do `globals.css`, escritos à mão de propósito: estes
              viram atributos de apresentação (`fill`) do SVG, e o modo de um
              `var()` falhar ali é a cor cair para o preto padrão — QR preto
              sobre preto, que nenhuma suíte vê e que só falha na fila da porta,
              no leitor de celular de outra pessoa. O ganho de amarrar ao tema
              não existe: o canhoto é a única superfície do produto que **não**
              pode seguir o tema, porque leitor de QR precisa do contraste
              claro-sobre-escuro fixo. Se o `globals.css` mudar, esta linha muda
              junto — e é para isso que este comentário está aqui. */}
          <QRCodeSVG
            value={ingresso.codigo}
            size={180}
            level="L"
            bgColor="#e4ebea"
            fgColor="#0b1618"
          />
        </div>

        {/* `<code>`, não `<span>`: dado de máquina (UX-DR9 — o código
            aparece em texto onde é apresentado). */}
        <code className={estilos.codigo}>{codigoEmBlocos}</code>
      </div>
    </div>
  );
}
