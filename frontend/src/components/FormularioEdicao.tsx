"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";

import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import SeletorDeData from "@/components/SeletorDeData";
import SessaoExpirada from "@/components/SessaoExpirada";
import Toast from "@/components/Toast";
import estilos from "@/app/(site)/organizador/publicar/page.module.css";
import { ErroDaApi } from "@/lib/api";
import { atualizarMeuEvento, type SetorParaEditar } from "@/lib/edicao";
import type { MeuEventoDetalhe } from "@/lib/eventos";
import {
  centavosParaReais,
  hojeEmSaoPaulo,
  partesDoFormulario,
  reaisParaCentavos,
} from "@/lib/formato";
import type { ResultadoDasPortarias } from "@/lib/portarias";

/**
 * A tela de editar evento: data, setores e escala de um evento que ainda não
 * vendeu (techspec `docs/techspec-editar-evento.md`, commit 2).
 *
 * **Formulário novo, e não uma generalização do `FormularioPublicacao`.** Aquele
 * tem 777 linhas construídas em volta de "escolher no catálogo e publicar", já
 * passadas por code review, e mexer nelas para economizar componentes que já são
 * reusáveis (`Campo`, `SeletorDeData`, a lista de portarias) é risco na tela mais
 * crítica do organizador em troca de nada. O preço é duas telas parecidas para
 * manter, e ele é menor.
 *
 * **O CSS, esse sim, é o mesmo** — este arquivo importa o módulo da tela de
 * publicar. Não é contradição: o que a spec descartou generalizar é a *lógica*,
 * e o vocabulário visual das duas é literalmente o mesmo (linha de setor com
 * quatro colunas, lista de portarias com alvo de 44px, rodapé com fio). Copiar
 * 250 linhas de CSS seria criar a segunda fonte que o módulo de "Meus eventos"
 * já evita ao ser importado pelas suas duas telas.
 *
 * ⚠️ **O que esta tela NÃO edita, e é o ponto da spec:** `nome`, `imagem_url`,
 * `local`, `cidade` e `origem_externa_id`. Os cinco vêm do catálogo (AD-1) e o
 * organizador não digita nenhum deles nem ao publicar — abrir aqui faria a tela
 * de editar ficar **mais poderosa que a de publicar**, e o evento poderia virar
 * outro show sem trocar de `origem_externa_id`. Eles aparecem como texto no
 * cabeçalho da página, não como campo.
 *
 * **Quem decide se esta tela sequer aparece é a `page.tsx`**, com a mesma leitura
 * de estoque que o detalhe usa para mostrar ou não o botão. Aqui dentro não há
 * checagem de venda nenhuma: o componente que existe é o formulário, e o
 * formulário só é montado quando dá para editar.
 */
type Props = { evento: MeuEventoDetalhe; portarias: ResultadoDasPortarias };

/**
 * Uma linha do formulário. Tudo texto — veio de um `<input>` —, menos o `id`.
 *
 * ⚠️ **`id: string | null` é o campo que separa alterar de criar**, e ele não é
 * a `chave`. A `chave` é do React e existe para a lista não embaralhar quando
 * uma linha some do meio; o `id` é do banco e viaja no corpo. Linha nova nasce
 * com `id: null`, e é isso que o backend lê como "setor novo".
 */
type LinhaDeSetor = {
  chave: number;
  id: string | null;
  nome: string;
  capacidade: string;
  preco: string;
};

const MENSAGEM_GENERICA =
  "Não foi possível salvar as alterações agora. Tente de novo em instantes.";

/** A mesma frase do `FormularioPublicacao`, e a mesma do `services/evento.py`. */
const DATA_NO_PASSADO = "A data do show já passou. Confira o dia e o horário.";

/** Espelha `_MAXIMO_INT4` do `schemas/evento.py` — o tipo da coluna. */
const MAXIMO_CAPACIDADE = 2_147_483_647;

/** Tetos do `EventoEdicao`: 20 setores e 20 escalados por evento. */
const MAXIMO_SETORES = 20;
const MAXIMO_ESCALADOS = 20;

export default function FormularioEdicao({ evento, portarias }: Props) {
  const router = useRouter();
  const detalhe = `/organizador/eventos/${evento.id}`;

  // `useState(() => …)`, com função: sem ela a lista seria remontada a cada
  // render e o `.map` rodaria à toa. O estado inicial é o evento como ele está
  // hoje — é o que faz "salvar sem mexer em nada" ser uma operação que não muda
  // nada, e não um formulário em branco que apaga o que existia.
  const [setores, setSetores] = useState<LinhaDeSetor[]>(() =>
    evento.setores.map((setor, indice) => ({
      chave: indice,
      id: setor.id,
      nome: setor.nome,
      // Centavos viram reais na entrada e voltam a centavos na saída, pelo par
      // de funções do `lib/formato.ts`. A ida e a volta batem: `12000` sai
      // `"120,00"` e volta `12000`.
      capacidade: String(setor.capacidade),
      preco: centavosParaReais(setor.preco_centavos),
    })),
  );
  const proximaChave = useRef(evento.setores.length);

  const [escalados, setEscalados] = useState<Set<string>>(
    () => new Set(evento.portarias.map((conta) => conta.id)),
  );
  const [filtro, setFiltro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<React.ReactNode>(null);

  const inicial = partesDoFormulario(evento.data_hora);

  const contas = portarias.estado === "ok" ? portarias.itens : [];
  const termo = filtro.trim().toLowerCase();
  const contasVisiveis = termo
    ? contas.filter((conta) => conta.nome.toLowerCase().includes(termo))
    : contas;

  /**
   * Os nomes dos setores que sumiram da lista — o que o `SETOR_COM_HISTORICO`
   * precisa para dizer de quem está falando.
   *
   * ⚠️ **O backend põe o nome do setor na mensagem dele, e a mensagem não chega
   * aqui**: o `chamarApi` guarda só o `codigo`, porque é o `codigo` que é a parte
   * estável do contrato (ver `app/core/erros.py`). Em vez de afrouxar essa regra
   * para um caso, a tela reconstrói a informação do lado de cá — ela sabe o que
   * o organizador removeu, que é exatamente o conjunto de suspeitos.
   */
  function nomesRemovidos(): string[] {
    const mantidos = new Set(
      setores.map((linha) => linha.id).filter((id): id is string => id !== null),
    );
    return evento.setores
      .filter((setor) => !mantidos.has(setor.id))
      .map((setor) => setor.nome);
  }

  /** Mesma convenção do resto do projeto: o texto vem do `codigo`. */
  function mensagemParaCodigo(codigo: string): React.ReactNode {
    if (codigo === "EVENTO_COM_VENDA") {
      // Acontece de verdade, e não é corrida teórica: alguém comprou entre a
      // hora em que esta tela abriu e o clique em salvar. A tela estava certa
      // quando renderizou.
      return "Alguém comprou um ingresso enquanto você editava. Este evento não pode mais ser alterado.";
    }
    if (codigo === "SETOR_COM_HISTORICO") {
      const removidos = nomesRemovidos();
      const alvo =
        removidos.length === 1
          ? `O setor "${removidos[0]}"`
          : removidos.length > 1
            ? `Um dos setores que você removeu (${removidos.join(", ")})`
            : "Um dos setores que você removeu";
      return `${alvo} já teve reservas e não pode ser apagado — o histórico continua apontando para ele. Traga-o de volta à lista: dá para mudar o nome, a capacidade e o preço.`;
    }
    if (codigo === "SETOR_DESCONHECIDO") {
      // Não é erro de digitação de ninguém: é a tela trabalhando sobre um
      // evento que mudou embaixo dela. Recarregar é o conserto real.
      return "Algum dos setores desta tela não existe mais neste evento. Recarregue a página e edite de novo.";
    }
    if (codigo === "EVENTO_SEM_SETOR") {
      return "Um evento precisa de ao menos um setor à venda.";
    }
    if (codigo === "SETOR_DUPLICADO") {
      return "Há mais de um setor com o mesmo nome, ou o mesmo setor entrou duas vezes. Cada setor precisa de um nome diferente.";
    }
    if (codigo === "EVENTO_SEM_PORTARIA") {
      return "Escale ao menos uma conta de portaria para validar os ingressos deste evento.";
    }
    if (codigo === "PORTARIA_INVALIDA") {
      return "Alguma das contas escaladas não está mais disponível. Recarregue a página e escale de novo.";
    }
    if (codigo === "EVENTO_NO_PASSADO") {
      // Duas situações, um código só (é assim no backend): a data nova caiu no
      // passado, ou o show aconteceu enquanto esta tela estava aberta. A
      // segunda é rara e a frase cobre as duas sem mentir em nenhuma.
      return DATA_NO_PASSADO;
    }
    if (codigo === "EVENTO_NAO_ENCONTRADO") {
      return "Este evento não existe mais, ou não é seu.";
    }
    if (codigo === "DADOS_INVALIDOS") {
      return "Confira os dados do formulário.";
    }
    if (codigo === "NAO_AUTENTICADO" || codigo === "SEM_PERMISSAO") {
      return <SessaoExpirada voltar={`${detalhe}/editar`} acao="salvar o evento" />;
    }
    return MENSAGEM_GENERICA;
  }

  function alternarEscalado(id: string) {
    setEscalados((atuais) => {
      const proximos = new Set(atuais);
      if (proximos.delete(id)) return proximos;

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
      { chave: proximaChave.current++, id: null, nome: "", capacidade: "", preco: "" },
    ]);
  }

  function removerSetor(chave: number) {
    setSetores((atuais) => atuais.filter((setor) => setor.chave !== chave));
  }

  function alterarSetor(chave: number, campo: "nome" | "capacidade" | "preco", valor: string) {
    setSetores((atuais) =>
      atuais.map((setor) =>
        setor.chave === chave ? { ...setor, [campo]: valor } : setor,
      ),
    );
  }

  async function aoEnviar(formulario: FormEvent<HTMLFormElement>) {
    formulario.preventDefault();
    // Mesma guarda do `FormularioPublicacao`: o `disabled` do botão só vale a
    // partir do próximo render, e não cobre `Enter` mantido pressionado.
    if (enviando) return;
    setErro(null);

    const dados = new FormData(formulario.currentTarget);
    const data = String(dados.get("data") ?? "");
    const hora = String(dados.get("hora") ?? "");

    // ⚠️ A junção é a mesma do formulário de publicar, copiada de lá e não
    // reinventada (a spec pede isso com todas as letras): `new Date("2026-08-14")`
    // é lido como **UTC**, e `new Date("2026-08-14T21:00")` como **hora local**.
    // O `toISOString()` logo abaixo é o que manda UTC ao servidor (AD-11).
    const instante = new Date(`${data}T${hora}`);
    if (Number.isNaN(instante.getTime())) {
      setErro("Confira a data e o horário do show.");
      return;
    }

    if (instante <= new Date()) {
      setErro(DATA_NO_PASSADO);
      return;
    }

    const setoresConvertidos: SetorParaEditar[] = [];
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

      setoresConvertidos.push({
        // A chave só entra quando existe: `id: undefined` no corpo é o mesmo que
        // ausente depois do `JSON.stringify`, mas o `...(x && {})` deixa escrito
        // na linha que setor novo **não manda** o campo.
        ...(setor.id ? { id: setor.id } : {}),
        nome,
        capacidade,
        preco_centavos: centavos,
      });
    }

    if (escalados.size === 0) {
      setErro(
        "Escale ao menos uma conta de portaria — só quem estiver escalado poderá validar os ingressos.",
      );
      return;
    }

    setEnviando(true);

    try {
      await atualizarMeuEvento(evento.id, {
        data_hora: instante.toISOString(),
        setores: setoresConvertidos,
        portaria_ids: [...escalados],
      });

      // **Volta para o detalhe, e aqui a decisão é o oposto da tela de
      // publicar.** Lá a confirmação fica no lugar do formulário porque ela é o
      // recibo — a única vez que o organizador vê o inventário recém-criado.
      // Aqui esse recibo já existe e é uma página: o detalhe mostra os mesmos
      // setores e a mesma escala, agora atualizados. Repetir tudo numa
      // confirmação seria construir uma segunda versão da tela para onde a
      // pessoa vai em seguida de qualquer jeito.
      //
      // `replace` e não `push`: com `push`, o botão voltar traz de volta o
      // formulário que acabou de ser salvo, exibindo o estado de antes como se
      // ainda fosse editável.
      router.replace(detalhe);
      // ⚠️ Sem ele o detalhe pode vir do Router Cache do Next, com os valores de
      // antes de salvar. O `cache: "no-store"` do `obterMeuEvento` fala do fetch
      // no servidor, e não do payload já renderizado que o cliente guardou.
      router.refresh();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof ErroDaApi
          ? mensagemParaCodigo(erroCapturado.codigo)
          : MENSAGEM_GENERICA,
      );
      setEnviando(false);
    }
  }

  return (
    /* `noValidate` pelo mesmo motivo da tela de publicar: com ele, toda recusa
       sai por um lugar só — o toast —, em vez de metade pelo balão do navegador
       grudado no campo. O motivo inteiro está no `FormularioPublicacao`. */
    <form onSubmit={aoEnviar} className={estilos.formulario} noValidate>
      <div className={estilos.colunas}>
        <div>
          <div className={estilos.duasColunas}>
            {/* `valorInicial` é o que faz esta tela abrir preenchida — e ele vem
                no `FUSO` do produto, não no fuso do navegador, porque esta ilha
                também renderiza no servidor antes de hidratar (ver
                `partesDoFormulario`). */}
            <SeletorDeData
              id="data"
              name="data"
              rotulo="Data"
              minimo={hojeEmSaoPaulo()}
              valorInicial={inicial.data}
              obrigatorio
            />
            <Campo
              id="hora"
              name="hora"
              rotulo="Horário"
              type="time"
              defaultValue={inicial.hora}
              required
            />
          </div>
        </div>

        <div>
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
                  evento sem setor nenhum, que é o que a API recusa com
                  `EVENTO_SEM_SETOR`.

                  ⚠️ **Aqui o `×` pode ser recusado pelo servidor, e na tela de
                  publicar não podia**: setor que já apareceu numa reserva —
                  mesmo expirada — não pode ser apagado (`SETOR_COM_HISTORICO`).
                  A tela não tem como saber quais são: `SetorSaida` traz
                  `vendidos`, que volta a zero quando a reserva expira, e não
                  "já teve reserva um dia". Marcar as linhas exigiria um campo
                  novo no contrato para prevenir um erro que a mensagem já
                  explica e que se desfaz trazendo a linha de volta. */}
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

      <div className={estilos.passo3}>
        <div className={estilos.secTituloPasso3}>
          <h3>Quem valida na porta</h3>
        </div>

        <p className={estilos.explicacaoEscala}>
          Só quem estiver marcado aqui poderá validar ingressos deste evento.
        </p>

        {contas.length === 0 ? (
          <p className={portarias.estado === "ok" ? estilos.vazio : estilos.aviso}>
            {portarias.estado === "sem-sessao" ? (
              <>
                Sua sessão expirou, e por isso a lista de portarias não carregou.{" "}
                <Link
                  href={`/login?voltar=${encodeURIComponent(`${detalhe}/editar`)}`}
                  target="_blank"
                >
                  Entre de novo
                </Link>{" "}
                e recarregue esta página.
              </>
            ) : portarias.estado === "indisponivel" ? (
              "Não foi possível carregar as contas de portaria agora. Sem ao menos uma escalada, o evento não pode ser salvo — recarregue a página em instantes."
            ) : (
              "Não há nenhuma conta de portaria cadastrada. Sem ao menos uma escalada, o evento não pode ser salvo."
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
                // formulário — aqui isso salvaria o evento no meio de uma busca.
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.preventDefault();
                }}
              />
            </div>

            {contasVisiveis.length === 0 ? (
              <p className={estilos.vazio}>Nenhuma conta de portaria com esse nome.</p>
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

      <Toast mensagem={erro} aoFechar={() => setErro(null)} />

      <div className={estilos.rodape}>
        <Link href={detalhe} className={estilos.saida}>
          Cancelar
        </Link>
        {/* Nada gira e nada pulsa enquanto envia (EXPERIENCE.md#Carregando) — o
            que muda é a palavra, e palavra não é animação. */}
        <Botao type="submit" disabled={enviando}>
          {enviando ? "Salvando…" : "Salvar alterações"}
        </Botao>
      </div>
    </form>
  );
}
