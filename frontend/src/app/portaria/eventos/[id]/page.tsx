import { redirect } from "next/navigation";

import PainelDoTurno from "@/components/PainelDoTurno";
import { partesDaFilaPublica } from "@/lib/formato";
import { obterUsuarioDaSessao } from "@/lib/sessao";
import { obterTurno } from "@/lib/turnos";

import estilos from "./page.module.css";

/**
 * O leitor de um turno (Story 5.3) — **e é ela que fecha a janela da 5.1**.
 *
 * O item aberto da lista de turnos linka para cá desde o commit daquela story, e
 * até agora caía no `not-found`. Era janela consciente de dois commits, da mesma
 * forma da que existiu entre a 2.4 e a 2.5 e da fila da 3.1: entregar o cartão
 * sem link seria pior, porque "escolher rápido onde vou trabalhar" é a story
 * inteira da 5.1 e um cartão que não leva a lugar nenhum não a demonstra.
 *
 * **As mesmas duas guardas de `/portaria` e `/portaria/conta`**: sem sessão,
 * `redirect` para o login com o caminho de volta preservado; com sessão e papel
 * diferente de `PORTARIA`, `redirect` para a raiz. A rota não é segredo — a API
 * responde `403`, que é público por natureza —, e mandar alguém logado para um
 * 404 pareceria defeito.
 *
 * ⚠️ **O `403` da API vira `/portaria`, e não `notFound()`.** São duas recusas
 * atrás do mesmo status — "você não foi escalado neste evento" e "a porta ainda
 * não abriu" —, e as duas têm a mesma resposta certa: a lista de turnos, que é
 * onde a portaria descobre onde ela de fato trabalha hoje. Um 404 diria que o
 * show não existe, o que é falso, e mandaria procurar o defeito no lugar errado.
 *
 * ⚠️ **A porta aberta é conferida pela API, não por esta tela.** Se `obterTurno`
 * respondeu `ok`, a dependência `exigir_porta_aberta` do backend já deixou
 * passar; conferir `turno.aberto` aqui de novo seria a segunda constante de duas
 * horas que a Story 5.2 acabou de eliminar. O campo continua no contrato porque
 * a **lista** o desenha.
 *
 * ⚠️ `redirect()` levanta `NEXT_REDIRECT` e não pode ficar dentro de
 * `try/catch`. Aqui não fica: o `try` mora no `lib/turnos.ts`, e o que sobra é
 * `if`.
 */
export default async function LeitorDoTurno({
  params,
}: PageProps<"/portaria/eventos/[id]">) {
  const { id } = await params;
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect(`/login?voltar=${encodeURIComponent(`/portaria/eventos/${id}`)}`);
  }
  if (usuario.papel !== "PORTARIA") {
    redirect("/");
  }

  const resultado = await obterTurno(id);

  // A sessão valia no `obterUsuarioDaSessao` e não vale mais aqui — expirou
  // entre as duas chamadas. É raro e é real, e a resposta certa é a mesma da
  // guarda de cima, não a frase de indisponibilidade: quem está na porta precisa
  // saber que o conserto é entrar de novo, não esperar.
  if (resultado.estado === "sem-sessao") {
    redirect(`/login?voltar=${encodeURIComponent(`/portaria/eventos/${id}`)}`);
  }
  if (resultado.estado === "sem-turno") {
    redirect("/portaria");
  }

  // Sobra `indisponivel`, e ele **não** redireciona: mandar de volta para
  // `/portaria` quando a API está fora do ar daria um vaivém entre duas telas
  // que não conseguem carregar nada. A frase fica, e o link de volta é o
  // cabeçalho da casca.
  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.aviso}>
          Não foi possível abrir este turno agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const turno = resultado.turno;
  const { diaDaSemana, dia, mesEAno, hora } = partesDaFilaPublica(turno.data_hora);
  const origem = [turno.local, turno.cidade].filter(Boolean).join(" · ");

  return (
    <section className={estilos.pagina}>
      {/* O cabeçalho responde a uma pergunta só, e ela é real: **é este o show
          certo?** Quem trabalha em duas casas na mesma noite abre o leitor
          errado com facilidade, e descobrir isso pelo primeiro `EVENTO_ERRADO`
          seria descobrir na frente de quem está entrando.

          ⚠️ **Ele é montado aqui, no Server Component**, e a Story 5.6 chegou a
          movê-lo para dentro do `<PainelDoTurno>` por `children` — enquanto o
          contador morava neste bloco. Com o contador em faixa própria logo
          abaixo, o cabeçalho voltou para cá: nome do show e ficha não têm estado
          nenhum, e não há motivo para atravessarem um componente cliente. */}
      <div className={estilos.cabecalho}>
        <span className="kicker">Leitor</span>
        <h1 className={estilos.nome}>{turno.nome}</h1>
        <p className={estilos.ficha}>
          {diaDaSemana}, {dia} {mesEAno} · {hora}
          {origem && ` · ${origem}`}
        </p>
      </div>

      <PainelDoTurno turno={turno} />
    </section>
  );
}
