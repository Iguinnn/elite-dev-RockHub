import Link from "next/link";
import { redirect } from "next/navigation";
import { cache } from "react";

import { listarMeusEventos, type MeuEventoResumo } from "@/lib/eventos";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * O instante em que esta requisição foi atendida — o relógio que decide o que
 * está "em cartaz" e o que "já aconteceu".
 *
 * **`cache()` do React, e não `Date.now()` solto no corpo do componente.**
 * Ler o relógio no meio da renderização é uma chamada impura: duas leituras
 * podem devolver valores diferentes, e um evento que começa exatamente agora
 * cairia numa seção no primeiro filtro e na outra no segundo. Com `cache()` o
 * valor nasce uma vez por requisição e vale para a página inteira — a mesma
 * mecânica que o `obterUsuarioDaSessao` usa para consultar a sessão uma vez só.
 */
const instanteDaRequisicao = cache(() => Date.now());

/**
 * "Meus eventos": o que o organizador publicou, em duas seções.
 *
 * **A primeira tela de leitura de domínio do projeto** — todas as anteriores
 * ou eram formulário (login, cadastro, publicar) ou eram vista de um dado
 * externo (o catálogo). Server Component sem uma linha de `"use client"`: não
 * há interação nenhuma aqui, só leitura e navegação.
 *
 * **As mesmas duas guardas de `/organizador/publicar`.** Sem sessão, `redirect`
 * para o login com o caminho de volta preservado; com sessão e papel diferente
 * de `ORGANIZADOR`, `redirect` para a raiz — a rota não é segredo (a API
 * responde `403`, que é público por natureza), e mandar alguém logado para um
 * 404 pareceria defeito.
 *
 * **"Gerenciar" aqui é acompanhar, não editar** (decisão do Igor, Story 2.6).
 * Não há botão de editar, cancelar ou trocar a escala: botão que não faz nada
 * é pior que botão ausente, e cada uma dessas ações custaria rota de escrita,
 * invariante nova e tela própria.
 *
 * **O corte em "Em cartaz" e "Já aconteceram" acontece aqui, e não na API.** A
 * API responde "quais são os meus eventos"; "o que interessa agora" é leitura,
 * e o relógio que decide é o de quem lê. Filtrar no backend criaria dois
 * endpoints ou um parâmetro que a Epic 5 vai querer diferente — e faria o
 * organizador **perder** o histórico dele.
 */
export default async function MeusEventos() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Forganizador%2Feventos");
  }
  if (usuario.papel !== "ORGANIZADOR") {
    redirect("/");
  }

  // `listarMeusEventos` nunca levanta: o projeto não tem `error.tsx`, e a
  // indisponibilidade é um estado da tela, não uma falha da aplicação.
  const resultado = await listarMeusEventos();
  const itens = resultado.estado === "ok" ? resultado.itens : [];

  // ⚠️ `Date` contra `Date`, nunca texto contra texto. Comparar as strings ISO
  // funciona por acidente enquanto todos os offsets forem `Z`, e para de
  // funcionar no primeiro `-03:00`.
  const agora = instanteDaRequisicao();
  const emCartaz = itens.filter(
    (evento) => new Date(evento.data_hora).getTime() >= agora,
  );
  // Decrescente: o histórico começa pelo que aconteceu por último. A lista já
  // chega crescente da API, então basta inverter — sem segunda ordenação.
  const jaAconteceram = itens
    .filter((evento) => new Date(evento.data_hora).getTime() < agora)
    .reverse();

  return (
    <section className={estilos.pagina}>
      <div className={estilos.secTitulo}>
        <h1>Meus eventos</h1>
      </div>

      {resultado.estado === "indisponivel" && (
        <p className={estilos.aviso}>
          Não foi possível carregar seus eventos agora. Tente de novo em instantes.
        </p>
      )}

      {resultado.estado === "ok" && itens.length === 0 && (
        // Estado vazio (EXPERIENCE.md#Vazio): kicker, frase, fim. Sem
        // ilustração e sem botão grande — o caminho para publicar já está no
        // masthead, e repeti-lo aqui em tamanho grande seria a chamada de ação
        // que o UX-DR8 recusa.
        <p className={estilos.aviso}>
          Você ainda não publicou nenhum evento. Quando publicar, ele aparece aqui
          com o inventário de cada setor.
        </p>
      )}

      {/* Seção sem nenhum evento simplesmente não é renderizada: bloco vazio
          com título é pior que ausência. */}
      {emCartaz.length > 0 && <Secao titulo="Em cartaz" eventos={emCartaz} />}
      {jaAconteceram.length > 0 && (
        <Secao titulo="Já aconteceram" eventos={jaAconteceram} />
      )}
    </section>
  );
}

function Secao({ titulo, eventos }: { titulo: string; eventos: MeuEventoResumo[] }) {
  return (
    <div className={estilos.secao}>
      <div className="kicker">{titulo}</div>
      <div className={estilos.lista}>
        {eventos.map((evento) => (
          <Fila key={evento.id} evento={evento} />
        ))}
      </div>
    </div>
  );
}

/**
 * Uma fila de jornal: data à esquerda, nome em serifada, local e cidade
 * abaixo, e o par `vendidos/capacidade` à direita.
 *
 * **A fila inteira é o link**, não só o nome (padrão `fila-listagem`): o alvo
 * é a linha toda, como no catálogo do passo 1 da publicação.
 *
 * **Números exatos, sem medidor e sem proporção** — é o inventário de quem é
 * dono da informação (UX-DR7). Medidor é da tela de quem compra, na Epic 3.
 */
function Fila({ evento }: { evento: MeuEventoResumo }) {
  const instante = new Date(evento.data_hora);
  const dia = new Intl.DateTimeFormat("pt-BR", { day: "2-digit" }).format(instante);
  const mes = new Intl.DateTimeFormat("pt-BR", { month: "short" })
    .format(instante)
    // O `Intl` do pt-BR devolve "ago." com ponto; a fila é versalete e o ponto
    // vira sujeira entre o mês e o ano.
    .replace(".", "");
  const ano = new Intl.DateTimeFormat("pt-BR", { year: "numeric" }).format(instante);
  const origem = [evento.local, evento.cidade].filter(Boolean).join(" · ");

  return (
    <Link href={`/organizador/eventos/${evento.id}`} className={estilos.fila}>
      <div className={estilos.data}>
        <span className={estilos.diaMes}>
          {dia} {mes}
        </span>
        <span className={estilos.ano}>{ano}</span>
      </div>

      <div>
        <h2 className={estilos.nome}>{evento.nome}</h2>
        <div className={estilos.origem}>{origem}</div>
      </div>

      {/* O par de números não fica sem nome: `12/860` sozinho é ambíguo para
          quem chega de leitor de tela. O rótulo é visível e lido junto. */}
      <div className={estilos.inventario}>
        <span className={estilos.numeros}>
          {evento.vendidos_total}/{evento.capacidade_total}
        </span>
        <span className={estilos.rotulo}>vendidos</span>
      </div>
    </Link>
  );
}
