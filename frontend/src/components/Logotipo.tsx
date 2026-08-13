import Image from "next/image";
import Link from "next/link";
import type { ComponentProps } from "react";

import marca from "../../public/logotipo-rockhub.png";

import estilos from "./Logotipo.module.css";

/**
 * A marca, num lugar só — e sempre o caminho de volta para a **casa de quem
 * está lendo**.
 *
 * Aqui eu abri exceção à regra de não abstrair antes do terceiro uso (a mesma
 * que mantém o CSS do estado vazio repetido): aquilo era estilo, e estilo
 * divergente é feio. Isto é o nome da aplicação — se o masthead e a tela de
 * acesso escreverem a marca cada um do seu jeito, a identidade racha.
 *
 * **Por que é um `Link` e não um `span`.** O grupo `(entrada)` não tem masthead,
 * por decisão — quem ainda não entrou não deve ver navegação que não pode usar.
 * O efeito colateral era um beco: quem digitava `/login` na barra de endereço
 * ficava sem nenhum caminho para `/`, porque os únicos links da tela eram o par
 * `/login` ↔ `/cadastro`. Levar a marca de volta para a raiz é a convenção que
 * todo site cumpre e não reintroduz navegação nenhuma — é a mesma marca, agora
 * clicável.
 *
 * ⚠️ **`href` virou prop na Story 5.1, e o motivo é o mesmo beco, de novo.** O
 * destino era fixo em `/`, e a casca da portaria herdou isso: clicar na marca
 * mandava quem está na porta para a programação pública — de onde o masthead do
 * `(site)`, que não tem e não vai ter item de portaria, não oferece nenhum
 * caminho de volta. A marca só cumpre a convenção que a torna um `Link` se ela
 * levar para a **casa de quem está lendo**, e a casa da portaria é `/portaria`.
 * O padrão continua `/`, então `(site)` e `(entrada)` não mudaram uma linha.
 *
 * O `rotulo` acompanha o `href` e não é enfeite: quem navega por leitor de tela
 * ouve o destino, e "página inicial" apontando para a lista de turnos é a marca
 * mentindo sobre para onde leva.
 *
 * O `className` fica no `<a>`, não num elemento por dentro: o `globals.css` já
 * zera cor e sublinhado de link, e o `:focus-visible` neon (UX-DR9) precisa
 * contornar a marca inteira.
 *
 * **A marca virou imagem** (2026-08-12). Era `Rock<em>Hub</em>` em Georgia 44px,
 * com o "Hub" em itálico neon; agora é o lettering próprio do projeto. Três
 * notas sobre a troca:
 *
 * - **PNG com fundo transparente, gerado a partir do JPEG de origem.** O
 *   original é branco e rosa sobre preto sólido (#030303), e o fundo desta
 *   aplicação é `--breu` (#0b1618, petróleo). Coladas uma na outra, as duas
 *   cores não se encontram: sobraria um retângulo preto em volta da marca, no
 *   topo de toda tela. O alfa foi derivado do brilho de cada pixel — o JPEG é
 *   literalmente "cor × alfa sobre preto" —, o que preserva o antialias das
 *   pontas do lettering em vez de serrilhá-las.
 * - **`next/image` com import estático, e aqui ele cabe.** A capa da
 *   programação usa `<img>` cru porque a URL é da Ticketmaster e o
 *   `images.remotePatterns` não a declara; este arquivo é nosso e local, então o
 *   componente do Next resolve dimensão, `srcset` e formato moderno sem
 *   configuração nenhuma.
 * - **`priority`**: a marca está acima da dobra em toda tela do produto,
 *   inclusive nas de acesso. Sem ele o Next a carrega preguiçosamente e o topo
 *   pisca vazio na primeira pintura.
 *
 * O `alt` fica **vazio de propósito**: o `aria-label` do link já anuncia a marca
 * e o destino, e um `alt="RockHub"` faria o leitor de tela dizer o nome duas
 * vezes — a mesma disciplina da arte da chamada principal.
 */
type Props = {
  href?: ComponentProps<typeof Link>["href"];
  rotulo?: string;
};

export default function Logotipo({
  href = "/",
  rotulo = "RockHub — página inicial",
}: Props = {}) {
  return (
    <Link href={href} className={estilos.logo} aria-label={rotulo}>
      <Image src={marca} alt="" className={estilos.marca} priority />
    </Link>
  );
}
