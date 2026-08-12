import Link from "next/link";
import { redirect } from "next/navigation";

import { horaDeEntrada, partesDaData } from "@/lib/formato";
import { listarIngressos, type IngressoResumo } from "@/lib/ingressos";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * "Meus ingressos": o que o cliente comprou, em dois blocos (Story 4.1).
 *
 * **As mesmas duas guardas de `/organizador/eventos`**, com outro papel: sem
 * sessão, `redirect` para o login com o caminho de volta preservado; com
 * sessão e papel diferente de `CLIENTE`, `redirect` para a raiz.
 *
 * **O corte em *Ativos* e *Utilizados* acontece aqui, e não na API.** `GET
 * /ingressos` responde "quais são os meus ingressos", já ordenados pela data
 * do show; "o que interessa agora" é leitura, e quem decide é a tela — o
 * mesmo molde do `MeusEventos` da 2.6.
 *
 * ⚠️ **O bloco *Utilizados* nasce vazio para sempre até a Story 5.2**: nada
 * escreve `usado_em` antes da porta existir (Epic 5). Não é bug — é a janela
 * que a techspec do grupo descreve como a única ordem possível.
 */
export default async function MeusIngressos() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fingressos");
  }
  if (usuario.papel !== "CLIENTE") {
    redirect("/");
  }

  const resultado = await listarIngressos();
  const itens = resultado.estado === "ok" ? resultado.itens : [];

  // A API já ordena por `evento_data_hora` crescente — o corte aqui é só o
  // `usado_em IS NULL`, sem reordenar os ativos.
  const ativos = itens.filter((item) => item.usado_em === null);
  // Decrescente por hora da entrada: o que importa em "utilizados" é a última
  // vez que se entrou, não a ordem do show.
  const utilizados = itens
    .filter((item) => item.usado_em !== null)
    .sort(
      (a, b) => new Date(b.usado_em as string).getTime() - new Date(a.usado_em as string).getTime(),
    );

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>Meus ingressos</h1>
        <span className="kicker">Cliente</span>
      </div>

      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          Não foi possível carregar seus ingressos agora. Tente de novo em instantes.
        </p>
      )}

      {resultado.estado === "ok" && itens.length === 0 && (
        // A frase exata do EXPERIENCE.md (UX-DR8): sem ilustração, sem botão.
        <p className={estilos.aviso}>
          Você ainda não comprou nenhum ingresso. Quando comprar, ele aparece
          aqui com o código de entrada.
        </p>
      )}

      {ativos.length > 0 && <Secao titulo="Ativos" itens={ativos} />}
      {utilizados.length > 0 && (
        <Secao titulo="Utilizados" itens={utilizados} utilizada />
      )}
    </section>
  );
}

function Secao({
  titulo,
  itens,
  utilizada = false,
}: {
  titulo: string;
  itens: IngressoResumo[];
  utilizada?: boolean;
}) {
  return (
    <div className={estilos.secao}>
      <div className="kicker">{titulo}</div>
      <div className={estilos.lista}>
        {itens.map((item) => (
          <Fila key={item.id} item={item} utilizada={utilizada} />
        ))}
      </div>
    </div>
  );
}

/**
 * Uma fila de jornal: data à esquerda, nome em serifada, prefixo do id em
 * monoespaçada, estado à direita — molde `fila-listagem` do `Meus eventos`.
 *
 * **Leva ao canhoto (`/ingressos/{id}`)**, a tela da Story 4.2 com o QR.
 *
 * **O "código" aqui são os 8 primeiros caracteres do `id`, não `codigo`.**
 * `GET /ingressos` nunca devolve `codigo` — ele é o segredo do QR e não tem
 * leitor nesta tela (techspec da 4.1). O prefixo é identificação visual, do
 * mesmo `id` que a tela já carrega.
 */
function Fila({ item, utilizada }: { item: IngressoResumo; utilizada: boolean }) {
  const { dia, mes, ano } = partesDaData(item.evento_data_hora);
  const origem = [item.evento_local, item.setor_nome].filter(Boolean).join(" · ");
  const prefixo = item.id.slice(0, 8).toUpperCase();

  return (
    <Link
      href={`/ingressos/${item.id}`}
      className={
        utilizada ? `${estilos.fila} ${estilos.utilizada}` : estilos.fila
      }
    >
      <div className={estilos.data}>
        <span className={estilos.diaMes}>
          {dia} {mes}
        </span>
        <span className={estilos.ano}>{ano}</span>
      </div>

      <div>
        <h2 className={estilos.nome}>{item.evento_nome}</h2>
        <div className={estilos.origem}>{origem}</div>
      </div>

      <span className={estilos.prefixo}>{prefixo}</span>

      <div className={estilos.selo}>
        {utilizada && item.usado_em ? (
          <span className={estilos.hora}>Entrou às {horaDeEntrada(item.usado_em)}</span>
        ) : (
          <span className={estilos.ativo}>Ativo</span>
        )}
      </div>
    </Link>
  );
}
