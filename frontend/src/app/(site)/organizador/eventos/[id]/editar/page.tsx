import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import FormularioEdicao from "@/components/FormularioEdicao";
import { obterMeuEvento } from "@/lib/eventos";
import { dataPorExtenso } from "@/lib/formato";
import { casaDoPapel } from "@/lib/papel";
import { listarPortarias, type ResultadoDasPortarias } from "@/lib/portarias";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "../../page.module.css";

/**
 * Editar um evento que ainda não vendeu (techspec `docs/techspec-editar-evento.md`,
 * commit 2).
 *
 * Server Component com as **mesmas duas guardas** das irmãs, e o mesmo módulo de
 * estilo da lista e do detalhe: as três telas de "Meus eventos" falam o mesmo
 * vocabulário, e o formulário traz o dele importando o módulo da tela de publicar.
 *
 * **Os dois impedimentos são checados aqui, e não dentro do formulário.** Evento
 * que já vendeu e evento que já aconteceu não montam formulário nenhum — a página
 * mostra a frase e o caminho de volta. É a mesma leitura que o detalhe faz para
 * decidir se mostra o botão, e é ela que garante o AC: **a URL digitada à mão
 * mostra a mesma frase**, sem formulário. A tela nunca é a única barreira — o
 * `PUT` recusa os dois casos com `409 EVENTO_COM_VENDA` e `422
 * EVENTO_NO_PASSADO` —, mas oferecer um formulário que só pode terminar em
 * recusa é o "clique desperdiçado" que a spec descartou.
 *
 * ⚠️ **A leitura de venda é `vendidos > 0`, e não "tem reserva paga".** É a
 * mesma trava do backend, pelo mesmo motivo: `setor.vendidos` sobe na **reserva**
 * (AD-3), não no pagamento, então alguém com o checkout aberto já conta. O que a
 * tela **não** faz, e o backend faz, é colher as reservas vencidas antes de
 * decidir (AD-4): uma reserva abandonada há mais de dez minutos ainda aparece
 * aqui como venda, e some assim que qualquer escrita passar por aquele setor.
 * Colher numa tela de leitura transformaria abrir a página em escrita — é o
 * mesmo corte declarado no README sobre a programação dizer "Esgotado" com
 * reservas já vencidas.
 */
export default async function EditarEvento({
  params,
}: PageProps<"/organizador/eventos/[id]/editar">) {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Forganizador%2Feventos");
  }
  if (usuario.papel !== "ORGANIZADOR") {
    redirect(casaDoPapel(usuario.papel));
  }

  const { id } = await params;
  const resultado = await obterMeuEvento(id);

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  const voltar = (
    <Link href={`/organizador/eventos/${id}`} className={estilos.voltar}>
      ← Voltar ao evento
    </Link>
  );

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        {voltar}
        <p className={estilos.aviso}>
          Não foi possível carregar este evento agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const evento = resultado.evento;
  const origem = [evento.local, evento.cidade].filter(Boolean).join(" · ");
  const vendeu = evento.setores.some((setor) => setor.vendidos > 0);
  const jaAconteceu = new Date(evento.data_hora) <= new Date();

  const cabecalho = (
    <>
      {voltar}
      <div className="kicker">Editar evento</div>
      <h1 className={estilos.nomeDoEvento}>{evento.nome}</h1>
      <p className={estilos.linhaDoShow}>
        {dataPorExtenso(evento.data_hora)} · {origem}
      </p>
    </>
  );

  // A ordem importa: um show que já aconteceu **e** vendeu recebe a frase do
  // show que já aconteceu, porque é a que não tem conserto. "Vendeu" descreve um
  // estado que ainda pode mudar (a reserva vence e o estoque volta); "aconteceu"
  // é definitivo, e mandar a pessoa esperar seria mentira.
  if (jaAconteceu || vendeu) {
    return (
      <section className={estilos.pagina}>
        {cabecalho}
        <p className={estilos.aviso}>
          {jaAconteceu
            ? "Esse show já aconteceu e não pode mais ser editado."
            : "Este evento já vendeu ingressos e não pode mais ser editado. O preço e a data ficariam diferentes do que quem comprou viu na hora da compra."}
        </p>
      </section>
    );
  }

  // Só depois das duas recusas: sem formulário na tela, a lista de contas de
  // portaria não tem consumidor, e buscá-la seria uma chamada para nada. Mesma
  // disciplina da tela de publicar, que só a busca com atração escolhida.
  // `listarPortarias` nunca levanta — o formulário explica a falta em vez de
  // derrubar a página.
  const portarias: ResultadoDasPortarias = await listarPortarias();

  return (
    <section className={estilos.pagina}>
      {cabecalho}
      <FormularioEdicao evento={evento} portarias={portarias} />
    </section>
  );
}
