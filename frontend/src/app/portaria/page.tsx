import Link from "next/link";
import { redirect } from "next/navigation";

import { partesDaFilaPublica } from "@/lib/formato";
import { casaDoPapel } from "@/lib/papel";
import { obterUsuarioDaSessao } from "@/lib/sessao";
import { listarTurnos, type TurnoDaPortaria } from "@/lib/turnos";

import estilos from "./page.module.css";

/**
 * "Turnos": os eventos em que esta conta foi escalada na porta (Story 5.1).
 *
 * **A lista não tem peneira de data, e essa é a decisão da tela.** As telas
 * públicas mostram só o que ainda vai acontecer; aqui isso seria o pior erro
 * possível, porque a portaria trabalha exatamente do outro lado desse corte —
 * às 21h30 de um show das 21h a fila está andando e o turno **não** pode ter
 * sumido. O que a API devolve é o inventário de quem lê, ordenado por data
 * crescente; a tela não reordena nem esconde nada.
 *
 * ⚠️ **O portão deixou de ser decisão desta tela na Story 5.2.** Aqui ele era
 * uma constante de duas horas comparada com o relógio da requisição, e a 5.2
 * passou a recusar validação fora da janela — com a regra valendo dos dois
 * lados, as duas constantes discordariam algum dia e esta tela liberaria o link
 * de um turno que a API recusa. A tela agora **lê `turno.estado`** e não calcula
 * nada: `ABERTO` é link para a tela do evento, `NAO_COMECOU` e `ENCERRADO` são
 * blocos sem link, com a frase de cada um.
 *
 * ⚠️ **O turno encerrado continua na lista, e sumir com ele seria o erro.**
 * `listar_escalados` é o inventário de quem lê, não a vitrine de quem compra —
 * tirar o show que acabou transformaria esta lista na quinta cópia do corte
 * público, o mesmo que o parágrafo acima recusa pelo outro lado. Quem trabalhou
 * ontem à noite precisa reconhecer o turno de ontem ao abrir a tela.
 *
 * **As mesmas duas guardas de `/organizador/eventos` e `/ingressos`**, com outro
 * papel: sem sessão, `redirect` para o login com o caminho de volta preservado;
 * com sessão e papel diferente de `PORTARIA`, `redirect` para a raiz — a rota
 * não é segredo (a API responde `403`, que é público por natureza), e mandar
 * alguém logado para um 404 pareceria defeito.
 *
 * ⚠️ **O link do item aberto aponta para uma tela que ainda não existe.**
 * `/portaria/eventos/{id}` nasce na Story 5.3, e a janela dura dois commits —
 * mesma forma da janela entre a 2.4 e a 2.5, e da fila da 3.1, que apontou para
 * `/eventos/{id}` por três stories. Entregar o item sem link seria pior:
 * "escolher rápido onde vou trabalhar" é a story inteira, e um cartão que não
 * leva a lugar nenhum não a demonstra.
 */
export default async function Turnos() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fportaria");
  }
  if (usuario.papel !== "PORTARIA") {
    redirect(casaDoPapel(usuario.papel));
  }

  // `listarTurnos` nunca levanta: o projeto não tem `error.tsx`, e a
  // indisponibilidade é um estado da tela, não uma falha da aplicação.
  const resultado = await listarTurnos();

  // A sessão valia no `obterUsuarioDaSessao` e não vale mais aqui — expirou
  // entre as duas chamadas. É raro e é real, e a resposta certa é a mesma da
  // guarda de cima, não a frase de indisponibilidade: quem está na porta
  // precisa saber que o conserto é entrar de novo, não esperar.
  if (resultado.estado === "sem-sessao") {
    redirect("/login?voltar=%2Fportaria");
  }

  const itens = resultado.estado === "ok" ? resultado.itens : [];

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>Turnos</h1>
        <span className="kicker">Portaria</span>
      </div>

      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          Não foi possível carregar seus turnos agora. Tente de novo em instantes.
        </p>
      )}

      {resultado.estado === "ok" && itens.length === 0 && (
        // Estado vazio (EXPERIENCE.md#Vazio): frase, fim. Sem ilustração e sem
        // botão grande — não há nada que esta pessoa possa fazer daqui para
        // aparecer numa escala; quem escala é o organizador.
        <p className={estilos.vazio}>Você não foi escalado para nenhum evento.</p>
      )}

      {itens.length > 0 && (
        <div className={estilos.lista}>
          {itens.map((turno) => (
            <Turno key={turno.id} turno={turno} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Um turno: dia grande à esquerda, nome do show em serifada, casa e cidade
 * abaixo, hora à direita.
 *
 * **O bloco inteiro é o alvo quando há link** (padrão `fila-listagem`), e o
 * `padding` generoso é o que o mantém acima dos 44px do UX-DR6 — aqui isso não é
 * conformidade de checklist, é a diferença entre acertar e errar o toque em pé,
 * no escuro, com uma mão.
 *
 * ⚠️ **`cidade` é anulável** (a Discovery pode não trazê-la). O `filter(Boolean)`
 * é o que impede a ficha de imprimir um separador solto — ou pior, a palavra
 * "null" — quando ela não vem.
 *
 * ⚠️ **`turno.estado` vem pronto do backend, e o componente não recebe mais
 * relógio nenhum** (Story 5.2). Ele deixou de comparar `data_hora` com
 * `Date.now()` porque a mesma janela decide o `403` da rota de validação: com o
 * cálculo aqui, esta tela poderia liberar o link de um turno que a API recusa.
 *
 * ⚠️ **O campo era `aberto: boolean` e virou um enum de três valores**
 * (techspec `docs/techspec-fim-do-evento.md`). O motivo aparece inteiro nesta
 * tela: sem o terceiro estado, o turno de um show da semana passada continuava
 * com link — a portaria clicava, chegava ao leitor e só ali descobria, pelo
 * `403`, que o evento tinha acabado. Agora ele diz isso na própria lista.
 *
 * ⚠️ **`entradas` é desenhado, e só nos turnos abertos** (Story 5.6). O campo
 * entrou no `TurnoDaPortaria`, que **duas** telas leem, e ignorá-lo aqui seria
 * esquecimento disfarçado de escolha. Ele responde à pergunta que se faz antes de
 * escolher a porta — onde o movimento está —, e é o que faz esta lista valer uma
 * segunda visita no meio do turno.
 *
 * **Fora da janela ele não aparece**, e a ausência é a decisão: um `0 ENTRADAS`
 * ao lado de "O evento ainda não começou" seria um número dizendo o que a frase
 * já disse, e zero antes de a porta abrir não é medida de nada. **No turno
 * encerrado ele também some**, e aí a escolha é outra: o número existiria e seria
 * verdadeiro, mas esta é uma tela de **escolher onde trabalhar**, e o encerrado
 * não é escolha nenhuma — o total da noite é assunto do leitor, que continua
 * mostrando os quatro contadores. As três recusas não vêm nem no contrato desta
 * rota: elas são do `TurnoDoLeitor`, e numa tela de escolha seriam ruído.
 */
function Turno({ turno }: { turno: TurnoDaPortaria }) {
  // `partesDaFilaPublica` e não `partesDaData`: é a única que devolve a **hora**
  // junto, e a hora é o dado que decide o turno de quem lê esta tela. O nome
  // fala da fila da programação porque foi lá que ela nasceu; a função é
  // formatação pura, sem nada de tela dentro.
  const { diaDaSemana, dia, mesEAno, hora } = partesDaFilaPublica(turno.data_hora);
  const origem = [turno.local, turno.cidade].filter(Boolean).join(" · ");

  const conteudo = (
    <>
      <div className={estilos.data}>
        <span className={estilos.diaDaSemana}>{diaDaSemana}</span>
        <span className={estilos.dia}>{dia}</span>
        <span className={estilos.mesEAno}>{mesEAno}</span>
      </div>

      <div className={estilos.corpo}>
        <h2 className={estilos.nome}>{turno.nome}</h2>
        <div className={estilos.origem}>{origem}</div>
        {turno.estado === "ABERTO" ? (
          // O plural fixo é escolha: "1 entradas" é feio e "1 entrada" custaria
          // uma regra de concordância numa etiqueta em versalete, onde a palavra
          // funciona como rótulo de coluna e não como frase.
          <p className={estilos.entradas}>{turno.entradas} entradas</p>
        ) : turno.estado === "ENCERRADO" ? (
          // ⚠️ **A mesma classe do `NAO_COMECOU`, e não uma cor nova.** Os dois
          // são turnos que não se abrem, e o que muda é a frase — no pretérito de
          // um lado, no futuro do outro. Um tom de alerta aqui diria que algo
          // falhou, e nada falhou: o show acabou.
          <p className={estilos.fechado}>O evento acabou</p>
        ) : (
          <p className={estilos.fechado}>O evento ainda não começou</p>
        )}
      </div>

      <span className={estilos.hora}>{hora}</span>
    </>
  );

  // Sem link, o elemento é uma `<div>` e não um `<a>` desativado: link que não
  // navega continua recebendo foco de teclado e continua sendo anunciado como
  // link, e a pessoa descobre que não vai a lugar nenhum depois de tentar.
  //
  // ⚠️ **`=== "ABERTO"`, e não `!== "ENCERRADO"`.** A comparação positiva é o que
  // mantém o quarto estado — se um dia existir — nascendo sem link, em vez de
  // ganhando um por omissão. O mesmo raciocínio do `!= VALIDO` do
  // `contar_recusas`, do lado de lá.
  return turno.estado === "ABERTO" ? (
    <Link href={`/portaria/eventos/${turno.id}`} className={estilos.turno}>
      {conteudo}
    </Link>
  ) : (
    <div className={`${estilos.turno} ${estilos.travado}`}>{conteudo}</div>
  );
}
