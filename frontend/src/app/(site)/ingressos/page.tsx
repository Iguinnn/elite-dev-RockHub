import Link from "next/link";
import { redirect } from "next/navigation";

import { horaDeEntrada, partesDaData } from "@/lib/formato";
import { listarIngressos, type IngressoResumo } from "@/lib/ingressos";
import { casaDoPapel } from "@/lib/papel";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * "Meus ingressos": o que o cliente comprou, em dois blocos (Story 4.1).
 *
 * **As mesmas duas guardas de `/organizador/eventos`**, com outro papel: sem
 * sessão, `redirect` para o login com o caminho de volta preservado; com
 * sessão e papel diferente de `CLIENTE`, `redirect` para a raiz.
 *
 * **O agrupamento em três blocos acontece aqui, e não na API.** `GET /ingressos`
 * responde "quais são os meus ingressos", já ordenados pela data do show e com a
 * `situacao` de cada um; "como agrupar" é leitura, e quem decide é a tela — o
 * mesmo molde do `MeusEventos` da 2.6.
 *
 * ⚠️ **A tela cortava por `usado_em === null`, e isso era um defeito**
 * (techspec `docs/techspec-fim-do-evento.md`). Aquela comparação não sabe quando
 * o show acabou: um ingresso nunca usado de um evento da semana passada aparecia
 * marcado *Ativo* na conta do cliente, para sempre. A regra desceu para o backend,
 * onde ela tem acesso ao `evento.data_hora_fim`, e a tela passou a ler o balde
 * pronto — um lugar só, e é o mesmo que a portaria consulta do outro lado.
 *
 * **`switch` não; três filtros.** Os blocos têm ordem, título e tratamento
 * próprios, e um deles reordena os itens — não é a mesma coisa repetida três
 * vezes.
 */
export default async function MeusIngressos() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fingressos");
  }
  if (usuario.papel !== "CLIENTE") {
    redirect(casaDoPapel(usuario.papel));
  }

  const resultado = await listarIngressos();
  const itens = resultado.estado === "ok" ? resultado.itens : [];

  // A API já ordena por `evento_data_hora` crescente — o agrupamento aqui é só
  // pelo balde, sem reordenar os ativos: o próximo show primeiro.
  const ativos = itens.filter((item) => item.situacao === "ATIVO");
  // Decrescente por hora da entrada: o que importa em "utilizados" é a última
  // vez que se entrou, não a ordem do show.
  //
  // O `as string` continua seguro, e agora por um motivo do contrato em vez de
  // uma coincidência: `UTILIZADO` **é** a situação de quem tem `usado_em`
  // preenchido, e é a primeira coisa que o `situacao_do_ingresso` decide.
  const utilizados = itens
    .filter((item) => item.situacao === "UTILIZADO")
    .sort(
      (a, b) => new Date(b.usado_em as string).getTime() - new Date(a.usado_em as string).getTime(),
    );
  // ⚠️ **Decrescente pela data do show, e não crescente como os ativos.** Aqui a
  // lista olha para trás: o que a pessoa procura num arquivo morto é o show mais
  // recente, e não o de dois anos atrás. É a mesma inversão dos utilizados, com o
  // campo que este bloco tem para ordenar.
  const expirados = itens
    .filter((item) => item.situacao === "EXPIRADO")
    .sort(
      (a, b) =>
        new Date(b.evento_data_hora).getTime() -
        new Date(a.evento_data_hora).getTime(),
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
        <p className={estilos.vazio}>
          Você ainda não comprou nenhum ingresso. Quando comprar, ele aparece
          aqui com o código de entrada.
        </p>
      )}

      {ativos.length > 0 && <Secao titulo="Ativos" itens={ativos} />}
      {utilizados.length > 0 && <Secao titulo="Utilizados" itens={utilizados} />}
      {/* ⚠️ **O terceiro bloco fica por último**, abaixo dos outros dois, e a
          ordem é a da atenção: o que vale agora, o que já foi usado, e só então o
          que não vale mais. Um *Expirados* no topo faria a tela abrir mostrando
          shows que já aconteceram. */}
      {expirados.length > 0 && <Secao titulo="Expirados" itens={expirados} />}
    </section>
  );
}

function Secao({ titulo, itens }: { titulo: string; itens: IngressoResumo[] }) {
  return (
    <div className={estilos.secao}>
      <div className="kicker">{titulo}</div>
      <div className={estilos.lista}>
        {itens.map((item) => (
          <Fila key={item.id} item={item} />
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
 *
 * ⚠️ **A fila não recebe mais o bloco a que pertence, e lê a `situacao` do
 * próprio item** (techspec `docs/techspec-fim-do-evento.md`). Antes havia uma prop
 * `utilizada` que a `Secao` passava por fora, e com três baldes ela viraria duas
 * bandeiras booleanas — quatro combinações para três estados, uma delas
 * impossível. É o mesmo antipadrão que o enum do backend recusa, e a resposta é a
 * mesma: um valor fechado, lido de um lugar só.
 *
 * **Expirado esmaece como o utilizado**, e o selo é que muda. Os dois são
 * ingressos que não abrem mais nenhuma porta, e o tratamento visual diz isso; o
 * que os separa é a frase — *"Entrou às 21h14"* registra que a pessoa esteve lá,
 * e *"Expirado"* que a noite passou sem ela.
 */
function Fila({ item }: { item: IngressoResumo }) {
  const { dia, mes, ano } = partesDaData(item.evento_data_hora);
  const origem = [item.evento_local, item.setor_nome].filter(Boolean).join(" · ");
  const prefixo = item.id.slice(0, 8).toUpperCase();
  const apagada = item.situacao !== "ATIVO";

  return (
    <Link
      href={`/ingressos/${item.id}`}
      className={apagada ? `${estilos.fila} ${estilos.utilizada}` : estilos.fila}
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
        {item.situacao === "UTILIZADO" && item.usado_em ? (
          <span className={estilos.hora}>Entrou às {horaDeEntrada(item.usado_em)}</span>
        ) : item.situacao === "EXPIRADO" ? (
          // Mesma tipografia do `Ativo` — versalete mono em `--fumaca`, sem cor
          // de alerta. Não é falha nem fraude: é uma noite que passou.
          <span className={estilos.ativo}>Expirado</span>
        ) : (
          <span className={estilos.ativo}>Ativo</span>
        )}
      </div>
    </Link>
  );
}
