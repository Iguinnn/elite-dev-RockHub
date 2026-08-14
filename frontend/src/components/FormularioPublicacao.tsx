"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import AvisoDaVirada from "@/components/AvisoDaVirada";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import SeletorDeData from "@/components/SeletorDeData";
import SessaoExpirada from "@/components/SessaoExpirada";
import Toast from "@/components/Toast";
import estilos from "@/app/(site)/organizador/publicar/page.module.css";
import { ARTE_DE_RESERVA_QUADRADA } from "@/lib/arte";
import { ErroDaApi, chamarApi } from "@/lib/api";
import type { ItemDoCatalogo } from "@/lib/catalogo";
// O que o `POST /organizador/eventos` devolve é o mesmo `EventoSaida` que o
// detalhe de "Meus eventos" lê, então o tipo é um só e mora em `lib/eventos.ts`
// (Story 2.6). `import type` é apagado pelo compilador — nada daquele módulo,
// que fala com `next/headers`, atravessa para o bundle do navegador.
import type { MeuEventoDetalhe } from "@/lib/eventos";
// As três saíram daqui na Story 2.6, e não por faxina: as telas de "Meus
// eventos" são Server Components, e Server Component **não consegue chamar**
// função exportada de um módulo `"use client"` — o motivo inteiro está no
// docstring de `lib/formato.ts`.
//
// ⚠️ **A `reaisParaCentavos` e a `hojeEmSaoPaulo` seguiram o mesmo caminho em
// 13/08/2026**, quando a tela de editar evento virou o segundo consumidor das
// duas. A primeira carrega a guarda de `Number.isSafeInteger` do code review da
// Epic 2; a segunda carregava uma **segunda cópia** da string do fuso, fora do
// `FUSO` que aquele módulo existe para manter num lugar só.
import {
  centavosParaReais,
  dataPorExtenso,
  hojeEmSaoPaulo,
  momentoDaPublicacao,
  reaisParaCentavos,
  terminoDoShow,
} from "@/lib/formato";
import type { ResultadoDasPortarias } from "@/lib/portarias";

/**
 * Passos 2 e 3 da publicação: data e setores; e quem valida na porta — mais a
 * confirmação que toma o lugar dos dois quando dá certo.
 *
 * ⚠️ **A casa de show e a cidade deixaram de ser campos** (decisão do Igor,
 * 13/08/2026). Eles nasceram editáveis para o caso da turnê que troca de cidade
 * a cada data; a Ticketmaster resolve isso antes de nós, mandando **um evento
 * por cidade** — três datas de uma turnê chegam como três itens do catálogo,
 * cada um com o seu `venue`. Editar aqui só criava a chance de o evento
 * publicado divergir do item que o originou, e o nome do show já carrega a casa.
 * Agora os dois viajam escondidos, junto com `nome` e `imagem_url`, como o AD-1
 * manda: dado do catálogo vira cópia no banco, não campo de formulário.
 *
 * A alternativa descartada foi deixá-los como `<input readOnly>`: campo que
 * ninguém pode editar é campo que não deveria ser campo — é a mesma régua que o
 * bloco da atração escolhida já seguia, e agora eles moram lá, como texto.
 *
 * **A primeira ilha `"use client"` fora das telas de acesso**, e ela existe
 * por um motivo que dá para apontar: `+ Adicionar setor` e o `×` de remover
 * mudam a quantidade de campos na tela a cada clique, e isso é interação que
 * exige o navegador. O resto da página — masthead, busca, catálogo — continua
 * renderizado no servidor; a fronteira entre os dois é a prop `item`, que
 * atravessa serializada.
 *
 * **Um `<form>` só para os dois passos, e um `POST` só.** A escala não é um
 * segundo envio: ou o evento nasce com quem valida na porta, ou não nasce
 * (AD-7). Dois formulários dariam a impressão de duas ações independentes, e a
 * primeira poderia terminar sem a segunda.
 *
 * Os campos do evento são lidos por `FormData` no envio, sem estado, como no
 * `FormularioCadastro`. Têm `useState` só os setores, porque mudam de
 * quantidade, e a escala, porque marcar e filtrar são interação.
 *
 * A prop `portarias` é a primeira vez que dado de servidor entra nesta ilha
 * para ser **usado**, e não só exibido: a lista se filtra, se marca e vira
 * corpo de requisição. A fronteira continua a mesma — o servidor busca, o
 * cliente interage.
 */
type Props = { item: ItemDoCatalogo; portarias: ResultadoDasPortarias };

/** Uma linha do formulário: tudo texto, porque tudo veio de um `<input>`. */
type LinhaDeSetor = { chave: number; nome: string; capacidade: string; preco: string };

const MENSAGEM_GENERICA =
  "Não foi possível publicar o evento agora. Tente de novo em instantes.";

/**
 * A recusa da data no passado, **numa constante porque tem dois emissores**.
 *
 * Ela sai daqui tanto na checagem local, antes do envio, quanto na tradução do
 * `EVENTO_NO_PASSADO` que o servidor devolve. As duas dizem a mesma coisa porque
 * são a mesma regra — a do `services/evento.py`, `data_hora <= agora` —, e
 * escrevê-la duas vezes seria deixar as duas frases divergirem no dia em que uma
 * delas fosse ajustada.
 */
const DATA_NO_PASSADO = "A data do show já passou. Confira o dia e o horário.";

/**
 * A recusa do término, **numa constante pelo mesmo motivo da de cima**: ela sai
 * daqui na checagem local e na tradução do `FIM_ANTES_DO_INICIO` do servidor.
 *
 * ⚠️ **Só a checagem local dispara na prática hoje**, porque a tela infere a
 * virada de meia-noite (ver `terminoDoShow`) e nunca monta um término anterior ao
 * início. A tradução fica assim mesmo: o dia em que a inferência mudar, ou em que
 * alguém chamar a rota por fora, a frase já está aqui — e é a mesma do
 * `services/evento.py`, palavra por palavra.
 */
const FIM_ANTES_DO_INICIO =
  "O show precisa terminar depois de começar. Confira o horário de término.";

/**
 * ⚠️ **O que se grava quando nem o catálogo nem o organizador sabem a casa.**
 *
 * `ItemDoCatalogo.local` é anulável — a Discovery às vezes devolve um evento sem
 * `_embedded.venues` —, e `EventoEntrada.local` é obrigatório (`min_length=1`).
 * Enquanto a casa era um campo do formulário, um item sem `venue` era só um
 * campo vazio para preencher; com o valor vindo do catálogo, ele viraria um
 * `422` sobre um campo que a tela **não mostra e ninguém pode editar** — beco
 * sem saída, e a única mensagem possível seria "confira os dados do
 * formulário". É a mesma armadilha do nome com mais de 200 caracteres,
 * encontrada no code review da Epic 2 (ver `schemas/catalogo.py`).
 *
 * A saída é a regra que vale também para a arte: **o formulário preenche
 * buraco, nunca sobrescreve.** Faltando a casa, e só nesse caso, o campo
 * reaparece — quem publica costuma saber onde o show é. Em branco, grava-se
 * esta frase, que é uma pendência dita em português.
 *
 * A alternativa descartada foi tornar `local` anulável e deixar cada tela
 * escrever a frase. É o modelo mais honesto — o banco diria "não sei" em vez de
 * guardar texto de interface —, e custaria migração, `str | None` em sete
 * schemas e a frase repetida em oito telas, com o risco de esquecer uma e
 * imprimir um separador solto na ficha. Não paga, para um caso que o próprio
 * catálogo quase nunca produz.
 */
const LOCAL_EM_CONFIRMACAO = "Local ainda em confirmação";

/** Espelha `_MAXIMO_INT4` do `schemas/evento.py` — o tipo da coluna. */
const MAXIMO_CAPACIDADE = 2_147_483_647;

/** Tetos do `EventoEntrada`: 20 setores e 20 escalados por evento. */
const MAXIMO_SETORES = 20;
const MAXIMO_ESCALADOS = 20;

/** Mesma convenção do login e do cadastro: o texto vem do `codigo`. */
function mensagemParaCodigo(codigo: string): React.ReactNode {
  if (codigo === "EVENTO_SEM_SETOR") {
    return "Um evento precisa de ao menos um setor à venda.";
  }
  if (codigo === "SETOR_DUPLICADO") {
    return "Há mais de um setor com o mesmo nome. Cada setor precisa de um nome diferente.";
  }
  if (codigo === "EVENTO_SEM_PORTARIA") {
    return "Escale ao menos uma conta de portaria para validar os ingressos deste evento.";
  }
  if (codigo === "PORTARIA_INVALIDA") {
    // Sem dizer **qual** conta: o backend não distingue "não existe" de "não é
    // portaria", de propósito, e a tela não inventa uma precisão que a
    // resposta não tem. Recarregar é o conserto real — a lista mudou.
    return "Alguma das contas escaladas não está mais disponível. Recarregue a página e escale de novo.";
  }
  if (codigo === "EVENTO_NO_PASSADO") {
    // Ainda aqui, e não substituído pela checagem local: o relógio do navegador
    // pode estar atrasado, e o do servidor é o que decide. Um minuto de
    // diferença basta para a checagem daqui aprovar o que a de lá recusa.
    return DATA_NO_PASSADO;
  }
  if (codigo === "FIM_ANTES_DO_INICIO") {
    return FIM_ANTES_DO_INICIO;
  }
  if (codigo === "DADOS_INVALIDOS") {
    return "Confira os dados do formulário.";
  }
  // ⚠️ Estes dois faltavam, e o buraco era grande: a sessão dura 8 horas
  // (AD-15), esta tela é longa (catálogo → data → N setores → escala), e
  // expirando o cookie no meio o `POST` voltava `401`. Sem entrada na tabela,
  // ele caía na mensagem genérica "tente de novo em instantes" — e tentar de
  // novo dava `401` outra vez, para sempre, com tudo digitado na tela e nenhum
  // caminho para o login. As guardas da `page.tsx` rodam na renderização, não
  // no envio.
  //
  // ⚠️ **Era um sentinela local até 13/08/2026** — a string `"__sessao_expirada__"`,
  // comparada no render para trocar o texto por JSX com `<Link>`. O truque existia
  // porque esta função devolvia `string`; devolvendo `ReactNode`, o componente
  // entra direto e o sentinela some. A varredura de superfícies de erro mostrou
  // que outros **quatro** componentes tinham o mesmo `401` sem link nenhum, e
  // era esse remendo local que impedia a correção de valer para todos.
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    return (
      <SessaoExpirada voltar="/organizador/publicar" acao="publicar o evento" />
    );
  }
  return MENSAGEM_GENERICA;
}

export default function FormularioPublicacao({ item, portarias }: Props) {
  // Uma linha, não três. O protótipo mostra três porque desenha o resultado
  // final; uma linha vazia mais o `+ Adicionar setor` já comunica como
  // funciona, sem sugerir que faltam duas.
  const proximaChave = useRef(1);
  const [setores, setSetores] = useState<LinhaDeSetor[]>([
    { chave: 0, nome: "", capacidade: "", preco: "" },
  ]);
  // ⚠️ **Os três campos de tempo passaram a ter estado em 14/08/2026**, e antes
  // eram lidos só no envio, por `FormData`. O motivo é a frase da virada de
  // meia-noite logo abaixo do término: para dizer em que dia o show acaba, a tela
  // precisa saber os três **enquanto** a pessoa digita, e não no `submit`.
  //
  // O `data` é espelho do `SeletorDeData`, alimentado pelo `aoMudar` dele — o
  // campo continua sendo o dono do valor (ver o docstring daquela prop).
  const [data, setData] = useState("");
  const [hora, setHora] = useState("");
  const [horaFim, setHoraFim] = useState("");
  const [enviando, setEnviando] = useState(false);
  // `ReactNode` e não `string` desde 13/08/2026: a mensagem de sessão expirada
  // leva um `<Link>` dentro (ver `SessaoExpirada`). Foi a troca deste tipo que
  // tornou o sentinela `__sessao_expirada__` desnecessário.
  const [erro, setErro] = useState<React.ReactNode>(null);
  const [publicado, setPublicado] = useState<MeuEventoDetalhe | null>(null);

  // ⚠️ **A escala é um conjunto de ids, e a lista filtrada é só a vista.** Se a
  // marcação fosse derivada da lista visível — por índice, por exemplo —
  // digitar no campo de busca apagaria quem já estava escalado. Marcar "Ana",
  // procurar "jonas", marcar "Jonas" e publicar tem que gravar os dois.
  const [escalados, setEscalados] = useState<Set<string>>(new Set());
  const [filtro, setFiltro] = useState("");

  const contas = portarias.estado === "ok" ? portarias.itens : [];
  const termo = filtro.trim().toLowerCase();
  // Filtro em memória, sem ida à rede: a lista inteira já veio do servidor, e
  // são poucas contas. Um `?q=` no endpoint seria a saída se ela crescesse.
  const contasVisiveis = termo
    ? contas.filter((conta) => conta.nome.toLowerCase().includes(termo))
    : contas;

  function alternarEscalado(id: string) {
    setEscalados((atuais) => {
      const proximos = new Set(atuais);
      if (proximos.delete(id)) return proximos;

      // Mesmo teto do `max_length=20` de `portaria_ids`. Desmarcar nunca é
      // barrado — só marcar além do vigésimo, e com o motivo dito na hora, em
      // vez de um `422` genérico depois de publicar.
      if (proximos.size >= MAXIMO_ESCALADOS) {
        setErro(`São até ${MAXIMO_ESCALADOS} contas de portaria por evento.`);
        return atuais;
      }

      setErro(null);
      proximos.add(id);
      return proximos;
    });
  }

  function acrescentarSetor() {
    setSetores((atuais) => [
      ...atuais,
      { chave: proximaChave.current++, nome: "", capacidade: "", preco: "" },
    ]);
  }

  function removerSetor(chave: number) {
    setSetores((atuais) => atuais.filter((setor) => setor.chave !== chave));
  }

  function alterarSetor(chave: number, campo: keyof LinhaDeSetor, valor: string) {
    setSetores((atuais) =>
      atuais.map((setor) =>
        setor.chave === chave ? { ...setor, [campo]: valor } : setor,
      ),
    );
  }

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    // O `disabled={enviando}` do botão cobre o clique, mas só depois do próximo
    // render — e não cobre `Enter` mantido pressionado num campo de texto, que
    // dispara envio atrás de envio. Sem chave de idempotência e sem tela de
    // apagar evento, cada duplicata é permanente.
    if (enviando) return;
    setErro(null);

    // ⚠️ **O `FormData` sobrou só para a casa**, e a data, a hora e o término
    // saem do estado desde 14/08/2026. Ler os mesmos três de duas fontes seria
    // criar a chance de elas discordarem — a frase da virada mostraria um dia e o
    // corpo enviaria outro.
    const dados = new FormData(evento.currentTarget);

    // A casa vem do catálogo (ver o topo do arquivo). O `FormData` só é
    // consultado no caso em que o campo existe — isto é, quando a Discovery não
    // mandou `venue` —, e mesmo aí o vazio tem resposta: `LOCAL_EM_CONFIRMACAO`.
    // `dados.get` devolveria `null` para um campo que não está no DOM, e o
    // `String(null)` seria a string `"null"` gravada no banco.
    const local =
      item.local ?? (String(dados.get("local") ?? "").trim() || LOCAL_EM_CONFIRMACAO);

    // ⚠️ A junção não é estética. `new Date("2026-08-14")` — data sozinha — é
    // lida como **UTC** pela especificação; `new Date("2026-08-14T21:00")` —
    // data com hora e sem offset — é lida como **hora local**. Mandar só a
    // data faria um show das 21h em São Paulo virar 18h na tela de quem
    // compra.
    const instante = new Date(`${data}T${hora}`);
    if (Number.isNaN(instante.getTime())) {
      setErro("Confira a data e o horário do show.");
      return;
    }

    // ⚠️ **O `min` do seletor de data não cobre a hora**, e é esse o buraco que
    // esta linha fecha: às 22h ele aceita hoje, e "hoje às 21h" é um show que já
    // aconteceu. Só o servidor barrava — e barrava depois de a pessoa ter
    // preenchido setores e escalado a portaria.
    //
    // **A comparação é a mesma do `services/evento.py`** (`data_hora <= agora`),
    // e é o mesmo instante nos dois lados: `new Date("…T…")` sem offset é lido
    // como hora local, `toISOString()` o converte para UTC, e o servidor compara
    // com `datetime.now(timezone.utc)`. Nenhum dos dois depende do fuso de quem
    // publica — ao contrário do `min` do seletor, que é de São Paulo de
    // propósito (ver `hojeEmSaoPaulo`).
    if (instante <= new Date()) {
      setErro(DATA_NO_PASSADO);
      return;
    }

    // O término, com a virada de meia-noite já resolvida — o que viaja é um
    // instante completo, e não uma hora solta (ver `terminoDoShow`).
    const fim = terminoDoShow(data, horaFim, instante);
    if (fim === null) {
      setErro("Confira o horário de término do show.");
      return;
    }
    // Cinto e suspensório: a inferência garante `fim > instante` por construção,
    // e esta linha é o que sobra de pé se ela um dia mudar. A frase é a mesma do
    // `FIM_ANTES_DO_INICIO` do servidor, pelo motivo escrito na constante.
    if (fim <= instante) {
      setErro(FIM_ANTES_DO_INICIO);
      return;
    }

    // As validações locais são gentileza: o servidor recusaria igual, e evitar
    // a ida à rede é retorno imediato. Mesma disciplina do `FormularioCadastro`.
    const setoresConvertidos = [];
    for (const setor of setores) {
      const nome = setor.nome.trim();
      const capacidade = Number(setor.capacidade);
      const centavos = reaisParaCentavos(setor.preco);

      if (!nome) {
        setErro("Todo setor precisa de um nome.");
        return;
      }
      if (!Number.isInteger(capacidade) || capacidade < 1) {
        setErro(`A capacidade de "${nome}" precisa ser um número inteiro maior que zero.`);
        return;
      }
      if (capacidade > MAXIMO_CAPACIDADE) {
        setErro(
          `A capacidade de "${nome}" passou do máximo de ${MAXIMO_CAPACIDADE.toLocaleString("pt-BR")} lugares.`,
        );
        return;
      }
      if (centavos === null) {
        setErro(`O preço de "${nome}" precisa ser um valor em reais, como 120,00.`);
        return;
      }

      setoresConvertidos.push({ nome, capacidade, preco_centavos: centavos });
    }

    // O AD-7 conferido aqui também, e não só no servidor: a recusa acontece
    // sem ida à rede, com o formulário inteiro preenchido do lado de cá.
    if (escalados.size === 0) {
      setErro(
        "Escale ao menos uma conta de portaria — só quem estiver escalado poderá validar os ingressos.",
      );
      return;
    }

    setEnviando(true);

    try {
      const criado = await chamarApi<MeuEventoDetalhe>("/organizador/eventos", {
        method: "POST",
        body: JSON.stringify({
          // **Cinco** campos do catálogo viajam escondidos desde 13/08/2026: o
          // organizador não digitou nenhum deles e não pode editá-los (AD-1).
          // `local` e `cidade` eram os dois últimos que ele preenchia à mão.
          origem_externa_id: item.id_externo,
          nome: item.nome,
          imagem_url: item.imagem_url,
          data_hora: instante.toISOString(),
          data_hora_fim: fim.toISOString(),
          local,
          // Já chega `null` do catálogo quando a Discovery não manda a cidade —
          // a coluna é anulável, e não há campo de texto para produzir o `""`
          // que esta linha antes precisava normalizar.
          cidade: item.cidade,
          setores: setoresConvertidos,
          portaria_ids: [...escalados],
        }),
      });

      // **Continua sem `router.push`, e agora por outro motivo.** Na Story 2.4
      // era "não há para onde ir"; desde a 2.6 existe — `/organizador/eventos`
      // está pronta e no masthead. A decisão de não saltar para lá é do Igor:
      // esta confirmação é o recibo da publicação, e trocá-la por um redirect
      // tiraria de quem publicou a chance de conferir o que acabou de nascer.
      // Quem quiser ir para a lista tem o link abaixo — a escolha é de quem
      // publicou.
      //
      // ⚠️ **O argumento original era mais forte, e caiu em 13/08/2026**: "é a
      // **única** vez que o organizador vê o inventário, porque não há tela de
      // editar evento para conferir depois". Existe agora, e o detalhe de "Meus
      // eventos" mostra o mesmo inventário. A decisão fica de pé pelo que sobrou
      // dela; o motivo que morreu não continua escrito como se valesse.
      setPublicado(criado);
    } catch (erroCapturado) {
      // Erro de rede (`TypeError: Failed to fetch`) não passa pelo `ErroDaApi`
      // e não tem `codigo` — daí o `instanceof` antes de ler qualquer coisa.
      setErro(
        erroCapturado instanceof ErroDaApi
          ? mensagemParaCodigo(erroCapturado.codigo)
          : MENSAGEM_GENERICA,
      );
      setEnviando(false);
    }
  }

  if (publicado) {
    const origem = [publicado.local, publicado.cidade].filter(Boolean).join(" · ");

    return (
      <div className={estilos.confirmacao}>
        {publicado.publicado_em && (
          <div className="kicker">{momentoDaPublicacao(publicado.publicado_em)}</div>
        )}
        <h3 className={estilos.nomePublicado}>{publicado.nome}</h3>
        <p className={estilos.linhaDoShow}>
          {dataPorExtenso(publicado.data_hora)} · {origem}
        </p>

        {/* Números exatos, sem medidor: proporção é para quem compra;
            organizador vê o inventário (UX-DR7). */}
        <div className={estilos.inventario}>
          {publicado.setores.map((setor) => (
            <div key={setor.id} className={estilos.linhaInventario}>
              <span className={estilos.setorPublicado}>{setor.nome}</span>
              <span className={estilos.numero}>{setor.capacidade} lugares</span>
              <span className={estilos.numero}>
                R$ {centavosParaReais(setor.preco_centavos)}
              </span>
            </div>
          ))}
        </div>

        {/* Quem ficou com a porta, por nome — a conferência na hora, que é
            quando a memória de quem marcou ainda está fresca.

            ⚠️ Até 13/08/2026 este comentário dizia que era a **única**
            confirmação, "porque não há tela de editar evento e descobrir depois
            que escalou a pessoa errada não teria conserto". Tem conserto agora,
            enquanto o evento não vender. */}
        <div className={estilos.naPorta}>
          <div className="kicker">Na porta</div>
          <p className={estilos.nomesEscalados}>
            {publicado.portarias.map((conta) => conta.nome).join(" · ")}
          </p>
        </div>

        {/* Dois caminhos, nenhum obrigatório: publicar o próximo show ou ir
            ver o que já está no ar. O segundo nasceu na Story 2.6, junto com a
            tela para onde ele aponta. */}
        <div className={estilos.saidas}>
          <Link href="/organizador/publicar" className={estilos.saida}>
            Publicar outro →
          </Link>
          <Link href="/organizador/eventos" className={estilos.saida}>
            Ver meus eventos →
          </Link>
        </div>
      </div>
    );
  }

  return (
    /* ⚠️ **`noValidate`, e é ele que fecha a padronização** (decisão do Igor,
       13/08/2026). Sem ele, esta tela recusava por **dois lugares diferentes**:
       capacidade `0` estourava o balão do navegador grudado no campo, e data no
       passado subia um toast no canto oposto da janela — mesma classe de
       problema, "um campo está preenchido errado", em dois cantos da tela. Qual
       dos dois aparecia dependia de a regra caber ou não num atributo HTML, que
       é um detalhe de implementação e não algo que quem publica possa prever.

       Com `noValidate`, o navegador para de validar e **tudo** passa pelas
       checagens de `aoEnviar`, que já cobriam o mesmo terreno: campo vazio,
       capacidade fora da faixa, preço fora de formato, data inválida e data no
       passado. Um lugar só, e é o toast.

       ⚠️ **O que `noValidate` NÃO desliga, e por isso os atributos ficam:**
       `maxLength` continua impedindo a digitação além do limite (é restrição de
       entrada, não validação de envio), `min`/`max`/`step` continuam controlando
       as setinhas do campo numérico, `type="date"` continua com a máscara e o
       calendário, e o `min` do seletor continua apagando os dias passados. O que
       sai de cena é só o balão de recusa no envio. */
    <form onSubmit={aoEnviar} className={estilos.formulario} noValidate>
      {/* Travado, e **não** é `<input readOnly>`: campo que ninguém pode
          editar é campo que não deveria ser campo. É texto. */}
      <div className={estilos.atracao}>
        {/* Mesma miniatura quadrada do passo 1, com a mesma arte de reserva
            quando o catálogo não trouxe foto (ver `lib/arte.ts`). */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={item.imagem_url ?? ARTE_DE_RESERVA_QUADRADA}
          alt=""
          className={estilos.miniatura}
        />
        <div>
          <h3 className={estilos.nome}>{item.nome}</h3>
          {/* A casa e a cidade, que até 13/08/2026 eram dois campos do passo 2.
              Aqui elas mudam de papel: não são mais procedência, são **o que
              vai ser publicado** — daí a serifada, e não o mono da linha de
              origem logo abaixo. Faltando a casa, o que aparece é a falta, dita
              antes de a pessoa preencher setor nenhum; o campo para resolvê-la
              abre logo abaixo, na coluna da data. */}
          <div className={item.local ? estilos.ondeAcontece : estilos.semLocal}>
            {item.local
              ? [item.local, item.cidade].filter(Boolean).join(" · ")
              : "O catálogo da Ticketmaster não trouxe o local do show."}
          </div>
          <div className={estilos.origem}>Ticketmaster · {item.id_externo}</div>
        </div>
      </div>

      <div className={estilos.colunas}>
        <div>
          <div className={estilos.duasColunas}>
            {/* `min` em hoje: a API recusa show no passado com
                `EVENTO_NO_PASSADO`, e o seletor de data avisa antes da ida à
                rede.

                ⚠️ **O motivo mudou em 13/08/2026, e as duas barreiras ficam.**
                Era "errar a data é permanente, porque não existe tela de editar
                evento". Existe — mas ela recusa exatamente o caso que importa
                aqui: um evento publicado com data no passado **já nasce sem
                conserto**, porque editar show que já aconteceu é recusado pelo
                mesmo `EVENTO_NO_PASSADO`. O erro continua permanente; o que
                mudou é por onde.

                ⚠️ **Não é o `Campo`, e é o único campo do projeto que não é**
                (13/08/2026). O popup do `<input type="date">` é desenhado pelo
                navegador e não aceita CSS nenhum — o azul do Chrome no meio de
                um produto de acento rosa. O `SeletorDeData` mantém o mesmo
                `<input>` por baixo (digitar continua funcionando, e o
                `dados.get("data")` do envio não soube de nada) e troca só o
                popup. O motivo inteiro está no topo dele. */}
            <SeletorDeData
              id="data"
              name="data"
              rotulo="Data"
              minimo={hojeEmSaoPaulo()}
              obrigatorio
              aoMudar={setData}
            />
            <Campo
              id="hora"
              name="hora"
              rotulo="Horário"
              type="time"
              value={hora}
              onChange={(e) => setHora(e.target.value)}
              required
            />
          </div>

          {/* ⚠️ **O término é uma hora, e não uma segunda data** (techspec
              `docs/techspec-fim-do-evento.md`). O rótulo diz `Termina às` de
              propósito: ele anuncia que o campo é uma hora do mesmo show, e não
              um segundo dia a escolher. Quando a hora vira a meia-noite, quem diz
              em que dia o show acaba é a frase logo abaixo — o preço da
              inferência é dizê-la em voz alta.

              ⚠️ **`min` não serve aqui, e não é esquecimento**: o atributo do
              `<input type="time">` compara com uma constante, nunca com outro
              campo. A recusa de fim antes do início é do service, e a tela só
              evita a ida à rede — mesmo desenho do `EVENTO_NO_PASSADO`. */}
          <Campo
            id="hora-fim"
            name="hora_fim"
            rotulo="Termina às"
            type="time"
            value={horaFim}
            onChange={(e) => setHoraFim(e.target.value)}
            required
          />
          <AvisoDaVirada data={data} hora={hora} horaFim={horaFim} />
          {/* A data continua sendo digitada, e ela **não** seguiu a casa e a
              cidade para o bloco de cima. A Discovery manda `dates.start` de
              cada evento, mas quem publica aqui está anunciando a própria data
              de venda — e, ao contrário do local, ela não é o que identifica o
              show no catálogo. */}

          {/* ⚠️ **O campo só existe quando o catálogo não trouxe a casa**, e é
              essa condição que separa "preencher buraco" de "editar o
              catálogo". Ele não é `required`: em branco grava
              `LOCAL_EM_CONFIRMACAO`, e é o `placeholder` que mostra isso antes
              de a pessoa decidir. Um `required` transformaria uma falha do
              fornecedor em trabalho obrigatório de quem publica. */}
          {!item.local && (
            <Campo
              id="local"
              name="local"
              rotulo="Local do show"
              type="text"
              maxLength={200}
              placeholder={LOCAL_EM_CONFIRMACAO}
            />
          )}
        </div>

        <div>
          {/* ⚠️ **O kicker `SETORES` saiu em 13/08/2026** (decisão do Igor). Ele
              era um título de grupo em cima de uma faixa que já começa com a
              palavra `SETOR` — dois rótulos dizendo a mesma coisa, um sobre o
              outro. E era ele que empurrava a coluna inteira uma linha para
              baixo: sem ele, a faixa de kickers nasce na mesma altura dos
              rótulos `DATA` e `HORÁRIO` da coluna ao lado, e as duas metades do
              passo 2 passam a começar juntas.

              Faixa de kickers: decoração que ajuda quem enxerga. Quem serve a
              quem não enxerga é o `<label>` de cada entrada, logo abaixo —
              visualmente oculto, nunca `display:none`. UX-DR9 pede rótulo
              associado, não rótulo visível, e `placeholder` não conta. */}
          <div className={estilos.colunasDoSetor} aria-hidden="true">
            <span className="kicker">Setor</span>
            <span className="kicker">Capacidade</span>
            <span className="kicker">Preço (R$)</span>
            <span />
          </div>

          {setores.map((setor, indice) => (
            <div key={setor.chave} className={estilos.linhaSetor}>
              <div>
                <label htmlFor={`setor-nome-${setor.chave}`} className={estilos.oculto}>
                  Nome do setor {indice + 1}
                </label>
                <input
                  id={`setor-nome-${setor.chave}`}
                  className={estilos.entrada}
                  type="text"
                  maxLength={80}
                  value={setor.nome}
                  onChange={(e) => alterarSetor(setor.chave, "nome", e.target.value)}
                  required
                />
              </div>
              <div>
                <label
                  htmlFor={`setor-capacidade-${setor.chave}`}
                  className={estilos.oculto}
                >
                  Capacidade do setor {indice + 1}
                </label>
                <input
                  id={`setor-capacidade-${setor.chave}`}
                  className={estilos.entrada}
                  type="number"
                  min={1}
                  // Maior `Integer` do Postgres, que é o tipo da coluna. Sem
                  // teto, a capacidade passava pelo schema e estourava no
                  // `commit` como `500` — ver `schemas/evento.py`.
                  max={MAXIMO_CAPACIDADE}
                  step={1}
                  inputMode="numeric"
                  value={setor.capacidade}
                  onChange={(e) =>
                    alterarSetor(setor.chave, "capacidade", e.target.value)
                  }
                  required
                />
              </div>
              <div>
                <label htmlFor={`setor-preco-${setor.chave}`} className={estilos.oculto}>
                  Preço do setor {indice + 1}, em reais
                </label>
                <input
                  id={`setor-preco-${setor.chave}`}
                  className={estilos.entrada}
                  type="text"
                  inputMode="decimal"
                  placeholder="120,00"
                  value={setor.preco}
                  onChange={(e) => alterarSetor(setor.chave, "preco", e.target.value)}
                  required
                />
              </div>
              {/* Some quando resta uma linha só: remover a última deixaria o
                  formulário sem nenhum setor, que é justamente o que a API
                  recusa. */}
              {setores.length > 1 && (
                <button
                  type="button"
                  className={estilos.remover}
                  aria-label={`Remover setor ${indice + 1}`}
                  onClick={() => removerSetor(setor.chave)}
                >
                  ×
                </button>
              )}
            </div>
          ))}

          {/* Some no teto de 20, que é o `max_length` do schema. Antes a tela
              deixava criar a 21ª linha e a API devolvia "confira os dados do
              formulário" depois de tudo digitado, sem dizer que havia teto. */}
          {setores.length < MAXIMO_SETORES ? (
            <button
              type="button"
              className={estilos.acrescentar}
              onClick={acrescentarSetor}
            >
              + Adicionar setor
            </button>
          ) : (
            <p className={estilos.vazio}>
              São até {MAXIMO_SETORES} setores por evento.
            </p>
          )}
        </div>
      </div>

      {/* Passo 3, dentro do mesmo `<form>`: uma publicação só, um `POST` só, e
          a escala atômica com o evento. O título mora aqui, e não na
          `page.tsx`, porque precisa sumir junto com o formulário quando a
          confirmação toma o lugar dele. */}
      <div className={estilos.passo3}>
        {/* ⚠️ **O kicker `OBRIGATÓRIO` saiu em 13/08/2026** (decisão do Igor). A
            frase logo abaixo — "só quem for escalado aqui poderá validar
            ingressos deste evento" — já diz por que o passo existe, e a recusa
            do envio diz o resto quando ninguém é escalado. Uma etiqueta na ponta
            do título repetia isso numa palavra e cobrava antes de a pessoa ter
            feito nada.

            O `.secTituloPasso3` continua sendo um flex de duas pontas, e não
            virou um `<h3>` solto: ele é a mesma anatomia dos títulos dos passos 1
            e 2 da página, e a diferença entre eles passaria a ser estrutural em
            vez de só o conteúdo. */}
        <div className={estilos.secTituloPasso3}>
          <h3>3 · Escale a portaria</h3>
        </div>

        {/* Texto do protótipo, palavra por palavra: é ele que explica o que a
            escala significa, e é requisito de AC. */}
        <p className={estilos.explicacaoEscala}>
          Só quem for escalado aqui poderá validar ingressos deste evento.
        </p>

        {contas.length === 0 ? (
          // Frase, fim (EXPERIENCE.md#Vazio): sem ilustração e sem botão grande.
          // O formulário continua de pé nos três casos.
          //
          // ⚠️ **A classe é escolhida pelo estado desde 13/08/2026.** Os três
          // textos moravam no mesmo `.aviso`, e o comentário aqui dizia "vale
          // para os dois casos" como se fossem equivalentes: não são. Sessão
          // expirada e lista fora do ar são **falhas** — algo quebrou e há o que
          // fazer. "Não há nenhuma conta de portaria cadastrada" é **ausência**:
          // nada falhou, o banco está assim. Só as duas primeiras levam o filete
          // `--brasa`.
          <p
            className={
              portarias.estado === "ok" ? estilos.vazio : estilos.aviso
            }
          >
            {portarias.estado === "sem-sessao" ? (
              <>
                Sua sessão expirou, e por isso a lista de portarias não carregou.{" "}
                <Link
                  href="/login?voltar=%2Forganizador%2Fpublicar"
                  target="_blank"
                >
                  Entre de novo
                </Link>{" "}
                e recarregue esta página.
              </>
            ) : portarias.estado === "indisponivel" ? (
              "Não foi possível carregar as contas de portaria agora. Sem ao menos uma escalada, o evento não pode ser publicado — recarregue a página em instantes."
            ) : (
              "Não há nenhuma conta de portaria cadastrada. Sem ao menos uma escalada, o evento não pode ser publicado."
            )}
          </p>
        ) : (
          <>
            <div className={estilos.filtroPortaria}>
              <Campo
                id="filtro-portaria"
                type="search"
                rotulo="Consulte pelo nome da conta"
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
                // Enter num campo de texto dentro de um `<form>` envia o
                // formulário. Aqui isso publicaria o evento no meio de uma
                // busca — o campo filtra a cada tecla, então não há nada para
                // confirmar com Enter.
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.preventDefault();
                }}
              />
            </div>

            {contasVisiveis.length === 0 ? (
              <p className={estilos.vazio}>
                Nenhuma conta de portaria com esse nome.
              </p>
            ) : (
              <div className={estilos.listaPortarias}>
                {contasVisiveis.map((conta) => (
                  <div key={conta.id} className={estilos.linhaPortaria}>
                    <input
                      type="checkbox"
                      id={`portaria-${conta.id}`}
                      className={estilos.marcacao}
                      checked={escalados.has(conta.id)}
                      onChange={() => alternarEscalado(conta.id)}
                    />
                    {/* O rótulo é a linha inteira: alvo grande, e o nome e o
                        e-mail lidos junto com a marcação. */}
                    <label htmlFor={`portaria-${conta.id}`} className={estilos.alvo}>
                      <span className={estilos.nomeDaConta}>{conta.nome}</span>
                      <span className={estilos.emailDaConta}>{conta.email}</span>
                    </label>
                  </div>
                ))}
              </div>
            )}

            {/* A contagem em texto, e não só pelo estado visual das marcações:
                nenhuma informação só por cor ou só por forma (UX-DR9). */}
            <div className={estilos.contagemEscalados}>
              {escalados.size === 1 ? "1 escalado" : `${escalados.size} escalados`}
            </div>
          </>
        )}
      </div>

      {/* ⚠️ **Toast, e não mais a faixa `AvisoDeErro` acima do botão** (decisão
          do Igor, 13/08/2026). A tela é longa — catálogo, data, N setores, lista
          de portarias — e a faixa ficava presa no rodapé do formulário: quem
          clicava em Publicar depois de rolar até a lista de portarias podia não
          ver a recusa que o próprio clique gerou. Flutuando, o aviso não depende
          de onde a página parou.

          **Uma superfície só para a tela inteira**, e é isso que a decisão
          resolve: com a faixa para uns erros e o toast para outros, qual dos
          dois aparece dependeria de qual campo está errado — que é justamente o
          que quem publicou não sabe ainda.

          `posicao` fica no padrão (`"base"`): aqui não há rodapé `sticky`, ao
          contrário da página do evento.

          ⚠️ **O `mensagem` voltou a ser só `{erro}`** (13/08/2026). Havia um
          ternário aqui comparando o estado contra o sentinela `SESSAO_EXPIRADA`
          para injetar o JSX com `<Link>`; com o `SessaoExpirada` extraído, quem
          monta o aviso é a tabela de códigos, e este ponto volta a não saber de
          caso nenhum — que é o que ele deve saber. */}
      <Toast mensagem={erro} aoFechar={() => setErro(null)} />

      <div className={estilos.rodape}>
        {/* Nada gira e nada pulsa enquanto envia (EXPERIENCE.md#Carregando) — o
            que muda é a palavra, e palavra não é animação. A régua está no
            `FormularioLogin`. */}
        <Botao type="submit" disabled={enviando}>
          {enviando ? "Publicando…" : "Publicar evento"}
        </Botao>
      </div>
    </form>
  );
}
