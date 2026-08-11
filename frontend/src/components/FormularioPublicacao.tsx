"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import estilos from "@/app/(site)/organizador/publicar/page.module.css";
import { ErroDaApi, chamarApi } from "@/lib/api";
import type { ItemDoCatalogo } from "@/lib/catalogo";

/**
 * Passo 2 da publicação: data, local e setores — e a confirmação que toma o
 * lugar do formulário quando dá certo.
 *
 * **A primeira ilha `"use client"` fora das telas de acesso**, e ela existe
 * por um motivo que dá para apontar: `+ Adicionar setor` e o `×` de remover
 * mudam a quantidade de campos na tela a cada clique, e isso é interação que
 * exige o navegador. O resto da página — masthead, busca, catálogo — continua
 * renderizado no servidor; a fronteira entre os dois é a prop `item`, que
 * atravessa serializada.
 *
 * Os campos do evento são lidos por `FormData` no envio, sem estado, como no
 * `FormularioCadastro`. Só os setores têm `useState`, porque só eles mudam de
 * quantidade.
 */
type Props = { item: ItemDoCatalogo };

/** Espelha `SetorSaida` do backend (`app/schemas/evento.py`). */
type SetorPublicado = {
  id: string;
  nome: string;
  capacidade: number;
  vendidos: number;
  preco_centavos: number;
};

/** Espelha `EventoSaida` do backend (`app/schemas/evento.py`). */
type EventoPublicado = {
  id: string;
  nome: string;
  data_hora: string;
  local: string;
  cidade: string | null;
  imagem_url: string | null;
  origem_externa_id: string | null;
  publicado_em: string | null;
  setores: SetorPublicado[];
};

/** Uma linha do formulário: tudo texto, porque tudo veio de um `<input>`. */
type LinhaDeSetor = { chave: number; nome: string; capacidade: string; preco: string };

const MENSAGEM_GENERICA =
  "Não foi possível publicar o evento agora. Tente de novo em instantes.";

/** Mesma convenção do login e do cadastro: o texto vem do `codigo`. */
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "EVENTO_SEM_SETOR") {
    return "Um evento precisa de ao menos um setor à venda.";
  }
  if (codigo === "SETOR_DUPLICADO") {
    return "Há mais de um setor com o mesmo nome. Cada setor precisa de um nome diferente.";
  }
  if (codigo === "DADOS_INVALIDOS") {
    return "Confira os dados do formulário.";
  }
  return MENSAGEM_GENERICA;
}

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
  return Math.round(Number(normalizado) * 100);
}

function centavosParaReais(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function dataPorExtenso(iso: string): string {
  const instante = new Date(iso);
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })
    .format(instante)
    .replace(":", "h");
  return `${dia}, ${hora}`;
}

function momentoDaPublicacao(iso: string): string {
  const instante = new Date(iso);
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
  }).format(instante);
  const hora = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })
    .format(instante)
    .replace(":", "h");
  return `Publicado em ${dia}, ${hora}`;
}

export default function FormularioPublicacao({ item }: Props) {
  // Uma linha, não três. O protótipo mostra três porque desenha o resultado
  // final; uma linha vazia mais o `+ Adicionar setor` já comunica como
  // funciona, sem sugerir que faltam duas.
  const proximaChave = useRef(1);
  const [setores, setSetores] = useState<LinhaDeSetor[]>([
    { chave: 0, nome: "", capacidade: "", preco: "" },
  ]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [publicado, setPublicado] = useState<EventoPublicado | null>(null);

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
      if (centavos === null) {
        setErro(`O preço de "${nome}" precisa ser um valor em reais, como 120,00.`);
        return;
      }

      setoresConvertidos.push({ nome, capacidade, preco_centavos: centavos });
    }

    setEnviando(true);

    try {
      const criado = await chamarApi<EventoPublicado>("/organizador/eventos", {
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
        }),
      });

      // Sem `router.push` e sem `router.refresh`: nada da sessão mudou, e não
      // há para onde ir — "Meus eventos" é a Story 2.6, e a raiz é o estado
      // vazio da programação até a 3.1. A confirmação toma o lugar do
      // formulário aqui mesmo.
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

        <Link href="/organizador/publicar" className={estilos.publicarOutro}>
          Publicar outro →
        </Link>
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
            <Campo id="data" name="data" rotulo="Data" type="date" required />
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

          <button
            type="button"
            className={estilos.acrescentar}
            onClick={acrescentarSetor}
          >
            + Adicionar setor
          </button>
        </div>
      </div>

      <AvisoDeErro mensagem={erro} />

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
