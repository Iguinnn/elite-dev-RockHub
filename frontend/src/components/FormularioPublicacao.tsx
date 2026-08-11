"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import estilos from "@/app/(site)/organizador/publicar/page.module.css";
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
// docstring de `lib/formato.ts`. `reaisParaCentavos` ficou, logo abaixo: ela é
// do formulário e não tem consumidor de servidor.
import { centavosParaReais, dataPorExtenso, momentoDaPublicacao } from "@/lib/formato";
import type { ResultadoDasPortarias } from "@/lib/portarias";

/**
 * Passos 2 e 3 da publicação: data, local e setores; e quem valida na porta —
 * mais a confirmação que toma o lugar dos dois quando dá certo.
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

/** Espelha `_MAXIMO_INT4` do `schemas/evento.py` — o tipo da coluna. */
const MAXIMO_CAPACIDADE = 2_147_483_647;

/** Tetos do `EventoEntrada`: 20 setores e 20 escalados por evento. */
const MAXIMO_SETORES = 20;
const MAXIMO_ESCALADOS = 20;

/**
 * Hoje no fuso do produto, em `AAAA-MM-DD` — o formato que o `<input
 * type="date">` exige no `min`.
 *
 * **Em São Paulo, e não no fuso do navegador**, pelo mesmo motivo do `FUSO` do
 * `lib/formato.ts`: quem publica está no Brasil, e um organizador viajando não
 * deve ver o seletor liberar ontem ou barrar hoje.
 */
function hojeEmSaoPaulo(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
  }).format(new Date());
}

/** Mesma convenção do login e do cadastro: o texto vem do `codigo`. */
function mensagemParaCodigo(codigo: string): string {
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
    return "A data do show já passou. Confira o dia e o horário.";
  }
  if (codigo === "DADOS_INVALIDOS") {
    return "Confira os dados do formulário.";
  }
  // ⚠️ Estes dois faltavam, e o buraco era grande: a sessão dura 8 horas
  // (AD-15), esta tela é longa (catálogo → data e local → N setores → escala),
  // e expirando o cookie no meio o `POST` voltava `401`. Sem entrada na tabela,
  // ele caía na mensagem genérica "tente de novo em instantes" — e tentar de
  // novo dava `401` outra vez, para sempre, com tudo digitado na tela e nenhum
  // caminho para o login. As guardas da `page.tsx` rodam na renderização, não
  // no envio. O link do aviso é quem fecha a saída (ver `AvisoDeSessao`).
  if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
    return SESSAO_EXPIRADA;
  }
  return MENSAGEM_GENERICA;
}

/**
 * Marcador de "a sessão morreu", não um texto de tela.
 *
 * O aviso precisa de um `<Link>` dentro dele, e `mensagemParaCodigo` devolve
 * `string`. Comparar contra esta constante é o que deixa o componente decidir
 * entre renderizar texto puro e texto com link, sem transformar a tabela de
 * códigos numa fábrica de JSX.
 */
const SESSAO_EXPIRADA = "__sessao_expirada__";

/**
 * Reais digitados → centavos inteiros. `null` quando não dá para ter certeza.
 *
 * A API só conhece `preco_centavos: int` (AD-11), e a conversão mora aqui, na
 * fronteira: nenhum número decimal atravessa o contrato.
 */
function reaisParaCentavos(valor: string): number | null {
  const bruto = valor.trim();
  // Com vírgula, ela é o separador decimal e o ponto é milhar ("1.234,50").
  // Sem vírgula, o ponto é o decimal ("120.50"). Assim "1.234" não vira
  // 123.400 por adivinhação — ele falha na regra abaixo e vira erro na tela.
  const normalizado = bruto.includes(",")
    ? bruto.replace(/\./g, "").replace(",", ".")
    : bruto;

  if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;

  const centavos = Math.round(Number(normalizado) * 100);
  // ⚠️ **`Math.round` mente em silêncio acima de `MAX_SAFE_INTEGER`**, e o
  // regex acima aceita qualquer quantidade de dígitos. Sem esta guarda,
  // `999999999999999,99` era enviado **arredondado errado** e gravado sem erro
  // nenhum — dinheiro corrompido sem ninguém saber, que é exatamente o que o
  // AD-11 existe para impedir. `null` devolve a mensagem de preço inválido, que
  // é a resposta certa para um número que o JavaScript não sabe representar.
  if (!Number.isSafeInteger(centavos)) return null;
  return centavos;
}

export default function FormularioPublicacao({ item, portarias }: Props) {
  // Uma linha, não três. O protótipo mostra três porque desenha o resultado
  // final; uma linha vazia mais o `+ Adicionar setor` já comunica como
  // funciona, sem sugerir que faltam duas.
  const proximaChave = useRef(1);
  const [setores, setSetores] = useState<LinhaDeSetor[]>([
    { chave: 0, nome: "", capacidade: "", preco: "" },
  ]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
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

    const dados = new FormData(evento.currentTarget);
    const data = String(dados.get("data") ?? "");
    const hora = String(dados.get("hora") ?? "");
    const local = String(dados.get("local") ?? "").trim();
    const cidade = String(dados.get("cidade") ?? "").trim();

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
          // Os três campos do catálogo viajam escondidos: o organizador não os
          // digitou e não pode editá-los (AD-1).
          origem_externa_id: item.id_externo,
          nome: item.nome,
          imagem_url: item.imagem_url,
          data_hora: instante.toISOString(),
          local,
          // Vazio vira `null`: a coluna é anulável, e `""` seria um segundo
          // jeito de dizer a mesma coisa.
          cidade: cidade || null,
          setores: setoresConvertidos,
          portaria_ids: [...escalados],
        }),
      });

      // **Continua sem `router.push`, e agora por outro motivo.** Na Story 2.4
      // era "não há para onde ir"; desde a 2.6 existe — `/organizador/eventos`
      // está pronta e no masthead. A decisão de não saltar para lá é do Igor:
      // esta confirmação é o recibo da publicação, e é a **única** vez que o
      // organizador vê o inventário e quem ficou com a porta. Não há tela de
      // editar evento para conferir depois, e trocar o recibo por um redirect
      // apagaria justamente isso. Quem quiser ir para a lista tem o link
      // abaixo — a escolha é de quem publicou.
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

        {/* Quem ficou com a porta, por nome. É a única confirmação que o
            organizador recebe da escala — não há tela de editar evento, e
            descobrir depois que escalou a pessoa errada não teria conserto. */}
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
    <form onSubmit={aoEnviar} className={estilos.formulario}>
      {/* Travado, e **não** é `<input readOnly>`: campo que ninguém pode
          editar é campo que não deveria ser campo. É texto. */}
      <div className={estilos.atracao}>
        {item.imagem_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.imagem_url} alt="" className={estilos.miniatura} />
        ) : (
          <div className={estilos.miniatura} />
        )}
        <div>
          <h3 className={estilos.nome}>{item.nome}</h3>
          <div className={estilos.origem}>Ticketmaster · {item.id_externo}</div>
        </div>
      </div>

      <div className={estilos.colunas}>
        <div>
          <div className={estilos.duasColunas}>
            {/* `min` em hoje: a API recusa show no passado com
                `EVENTO_NO_PASSADO`, e o seletor de data avisa antes da ida à
                rede. Como não existe tela de editar evento, errar a data é
                permanente — vale as duas barreiras. */}
            <Campo
              id="data"
              name="data"
              rotulo="Data"
              type="date"
              min={hojeEmSaoPaulo()}
              required
            />
            <Campo id="hora" name="hora" rotulo="Horário" type="time" required />
          </div>
          <Campo
            id="local"
            name="local"
            rotulo="Casa de show"
            type="text"
            maxLength={200}
            defaultValue={item.local ?? ""}
            required
          />
          <Campo
            id="cidade"
            name="cidade"
            rotulo="Cidade"
            type="text"
            maxLength={120}
            defaultValue={item.cidade ?? ""}
          />
        </div>

        <div>
          <div className={`kicker ${estilos.tituloSetores}`}>Setores</div>

          {/* Faixa de kickers: decoração que ajuda quem enxerga. Quem serve a
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
            <p className={estilos.aviso}>
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
        <div className={estilos.secTituloPasso3}>
          <h3>3 · Escale a portaria</h3>
          <span className="kicker">Obrigatório</span>
        </div>

        {/* Texto do protótipo, palavra por palavra: é ele que explica o que a
            escala significa, e é requisito de AC. */}
        <p className={estilos.explicacaoEscala}>
          Só quem for escalado aqui poderá validar ingressos deste evento.
        </p>

        {contas.length === 0 ? (
          // Estado vazio (EXPERIENCE.md#Vazio): frase, fim. Sem ilustração e
          // sem botão grande. Vale para os dois casos — não há conta de
          // portaria nenhuma, ou a lista não pôde ser carregada —, e o
          // formulário continua de pé nos dois.
          <p className={estilos.aviso}>
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
              <p className={estilos.aviso}>
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

      {/* O único aviso com link: sem ele, sessão expirada no meio do
          preenchimento não tinha saída nenhuma. `target="_blank"` porque sair
          desta página descartaria o formulário inteiro — a pessoa entra na
          outra aba e volta para clicar em Publicar com tudo ainda preenchido. */}
      <AvisoDeErro
        mensagem={
          erro === SESSAO_EXPIRADA ? (
            <>
              Sua sessão expirou.{" "}
              <Link href="/login?voltar=%2Forganizador%2Fpublicar" target="_blank">
                Entre de novo
              </Link>{" "}
              e clique em Publicar outra vez — o que você preencheu continua aqui.
            </>
          ) : (
            erro
          )
        }
      />

      <div className={estilos.rodape}>
        {/* Nada gira e nada pulsa enquanto envia: o botão fica `disabled`, e é
            só isso (EXPERIENCE.md#Carregando). */}
        <Botao type="submit" disabled={enviando}>
          Publicar evento
        </Botao>
      </div>
    </form>
  );
}
