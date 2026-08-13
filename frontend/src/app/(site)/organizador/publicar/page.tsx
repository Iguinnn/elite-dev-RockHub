import Link from "next/link";
import { redirect } from "next/navigation";

import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import FormularioPublicacao from "@/components/FormularioPublicacao";
import { ARTE_DE_RESERVA_QUADRADA } from "@/lib/arte";
import { buscarNoCatalogo } from "@/lib/catalogo";
import { listarPortarias, type ResultadoDasPortarias } from "@/lib/portarias";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * Fluxo de publicação: passo 1, buscar a atração no catálogo da Ticketmaster;
 * passo 2, preencher data e setores; passo 3, escalar a portaria.
 *
 * ⚠️ **A casa de show e a cidade deixaram de ser campos em 13/08/2026** — o
 * motivo inteiro está no topo do `FormularioPublicacao`. O que muda aqui é só o
 * título do passo 2, e ele muda porque o passo mudou de tamanho.
 * Server Component — a busca vive na URL (`?q=`) **e a escolha também**
 * (`?escolhido=`), não em estado de cliente, e por isso a página é
 * recarregável, compartilhável e o botão voltar funciona.
 *
 * **Duas guardas, não uma.** Sem sessão, `redirect` para o login com o
 * caminho de volta preservado — o mesmo padrão da `/conta`. Com sessão e
 * papel diferente de `ORGANIZADOR`, `redirect` para a raiz: a rota não é
 * segredo (a API responde `403`, que é público por natureza), e mandar
 * alguém logado para um 404 pareceria defeito.
 *
 * **A escolha é navegação, não estado** (Story 2.4). Clicar numa fila é
 * seguir um `<Link>`, e é o que mantém esta página inteira no servidor: a
 * única ilha `"use client"` da tela é o `FormularioPublicacao`, que precisa do
 * navegador para acrescentar e remover linha de setor — e, desde a Story 2.5,
 * para filtrar e marcar quem trabalha na porta.
 *
 * **Os títulos dos passos 1 e 2 moram aqui; o do passo 3, não.** Os dois
 * primeiros são da página: continuam de pé o tempo todo. O terceiro pertence
 * ao formulário, e precisa desaparecer junto com ele quando a confirmação toma
 * o seu lugar — um "3 · Escale a portaria" sozinho, acima de um recibo de
 * evento publicado, seria uma instrução para fazer o que já foi feito.
 *
 * **A busca acontece sempre, mesmo sem termo** — revisado depois do corte
 * original da Story 2.2: em vez de um convite "busque pelo nome do show" antes
 * de qualquer chamada, a tela já chega mostrando exemplos reais do catálogo
 * (os próximos eventos no Brasil), para o organizador ver do que se trata sem
 * precisar digitar nada primeiro.
 */
export default async function PublicarEvento({
  searchParams,
}: PageProps<"/organizador/publicar">) {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Forganizador%2Fpublicar");
  }
  if (usuario.papel !== "ORGANIZADOR") {
    redirect("/");
  }

  // Os dois podem chegar como `string[]` (`?q=a&q=b`) — o primeiro valor
  // basta, não há motivo para a busca aceitar mais de um termo nem para a
  // tela ter duas atrações escolhidas.
  const parametros = await searchParams;
  const primeiro = (valor: string | string[] | undefined) =>
    (Array.isArray(valor) ? valor[0] : valor) ?? "";

  const termo = primeiro(parametros.q);
  const termoLimpo = termo.trim();
  const idEscolhido = primeiro(parametros.escolhido);

  // `buscarNoCatalogo` nunca levanta: o `503` da Ticketmaster é um estado da
  // tela, não uma falha da aplicação — não existe `error.tsx` neste projeto.
  // Chama sempre, com ou sem termo: sem termo, o backend lista os próximos
  // eventos do catálogo como exemplo.
  const resultado = await buscarNoCatalogo(termoLimpo);

  // ⚠️ Pode ser `undefined` de verdade, e isso **não** é erro: `?escolhido=`
  // sobrevive à troca do termo de busca, e o id na URL pode não estar mais na
  // lista. Nesse caso o passo 2 simplesmente não aparece — sem aviso, sem
  // tela quebrada. Nunca use `!` para calar o TypeScript aqui.
  const escolhido =
    resultado.estado === "ok"
      ? resultado.itens.find((item) => item.id_externo === idEscolhido)
      : undefined;

  // Só com atração escolhida: sem ela não há passo 3 na tela, e buscar a lista
  // a cada busca no catálogo seria uma chamada por tecla enter que ninguém vai
  // ler. `listarPortarias` também nunca levanta — o passo 3 explica a falta em
  // vez de derrubar a página.
  const portarias: ResultadoDasPortarias = escolhido
    ? await listarPortarias()
    : { estado: "ok", itens: [] };

  // `URLSearchParams` e só ele: `q` chega aqui já decodificado pelo Next, e
  // concatenar `encodeURIComponent` à mão em cima disso produz `%2520` e uma
  // busca que não acha nada.
  //
  // O `#passo-2` no fim não é enfeite: sem ele, escolher uma atração deixa a
  // pessoa exatamente onde estava, com o formulário nascendo lá embaixo, fora
  // da tela — parece que o clique não fez nada. A âncora resolve isso **pela
  // navegação**, sem `onClick` e sem `useEffect`: o `<Link>` leva até o passo
  // 2 porque o destino é o passo 2, não porque alguém rolou a página com
  // JavaScript depois.
  function destinoDaEscolha(idExterno: string): string {
    const parametros = new URLSearchParams();
    // Termo vazio não entra na URL: `?q=&escolhido=…` é ruído para quem
    // compartilha o link.
    if (termoLimpo) {
      parametros.set("q", termoLimpo);
    }
    parametros.set("escolhido", idExterno);
    return `/organizador/publicar?${parametros}#passo-2`;
  }

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>1 · Escolha no catálogo</h1>
        <span className="kicker">Ticketmaster Discovery</span>
      </div>

      <form method="get" className={estilos.busca}>
        <div className={estilos.campoBusca}>
          {/* `maxLength` igual ao `Query(max_length=120)` da rota: sem ele,
              colar um texto longo devolvia `422` e a tela acusava a
              Ticketmaster por um erro do próprio formulário. */}
          <Campo
            id="q"
            name="q"
            type="search"
            rotulo="Buscar no catálogo"
            defaultValue={termo}
            maxLength={120}
          />
        </div>
        <div className={estilos.botaoBusca}>
          <Botao type="submit">Buscar</Botao>
        </div>
      </form>

      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          O catálogo da Ticketmaster não respondeu. Tente de novo em instantes.
        </p>
      )}

      {/* Três estados de falha e três textos, porque três consertos diferentes:
          esperar, entrar de novo, e encurtar a busca. Um texto só mandava a
          pessoa esperar por coisa que não melhora sozinha. */}
      {resultado.estado === "sem-sessao" && (
        <p className={estilos.aviso}>
          Sua sessão expirou.{" "}
          <Link href="/login?voltar=%2Forganizador%2Fpublicar">Entre de novo</Link>{" "}
          para ver o catálogo.
        </p>
      )}

      {resultado.estado === "busca-invalida" && (
        <p className={estilos.aviso}>
          A busca ficou longa demais. Use até 120 caracteres.
        </p>
      )}

      {resultado.estado === "ok" && resultado.itens.length === 0 && (
        <p className={estilos.aviso}>
          {termoLimpo
            ? "Nenhum show encontrado para essa busca."
            : "Não há shows no catálogo agora."}
        </p>
      )}

      {resultado.estado === "ok" && resultado.itens.length > 0 && (
        <div className={estilos.catalogo}>
          {resultado.itens.map((item) => {
            // A linha de origem só entra com o que existe: `local` e `cidade`
            // podem faltar, e juntar tudo com `filter` evita o "Ticketmaster ·
            //  · " de buracos que sobraria se algum estivesse ausente.
            //
            // O `id_externo` saiu daqui: ele identifica o show para o nosso
            // código, não para quem está escolhendo o que publicar — quem
            // olha reconhece pelo nome, pela casa e pela cidade, que já estão
            // logo ao lado. Ele continua vindo da API e vira `key` abaixo.
            const origem = ["Ticketmaster", item.local, item.cidade]
              .filter(Boolean)
              .join(" · ");
            const selecionado = item.id_externo === escolhido?.id_externo;

            return (
              <Link
                key={item.id_externo}
                href={destinoDaEscolha(item.id_externo)}
                className={`${estilos.item} ${selecionado ? estilos.itemEscolhido : ""}`}
                aria-current={selecionado ? "true" : undefined}
              >
                {/* A Discovery serve imagem de mais de um host
                    (`s1.ticketm.net`, `media.ticketmaster.com`), e `next/image`
                    exige `remotePatterns` declarado por host — errar um produz
                    erro em tempo de execução. `<img>` com dimensão fixa no CSS
                    resolve sem essa dependência.

                    Sem arte no catálogo, entra o disco do RockHub na versão
                    **quadrada** — a 16/10 espremida em 70×70 viraria borrão
                    (ver `lib/arte.ts`). O bloco cinza vazio saiu daqui. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.imagem_url ?? ARTE_DE_RESERVA_QUADRADA}
                  alt=""
                  loading="lazy"
                  className={estilos.miniatura}
                />
                <div>
                  <h4 className={estilos.nome}>{item.nome}</h4>
                  <div className={estilos.origem}>{origem}</div>
                </div>
                <span className={estilos.estado}>
                  {selecionado ? "Selecionado" : "Selecionar"}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      {escolhido && (
        <>
          <div
            id="passo-2"
            className={`${estilos.secTitulo} ${estilos.secTituloPasso2}`}
          >
            <h2>2 · Data e setores</h2>
          </div>
          <FormularioPublicacao item={escolhido} portarias={portarias} />
        </>
      )}
    </section>
  );
}
