import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import Cronometro from "@/components/Cronometro";
import FormularioDePagamento from "@/components/FormularioDePagamento";
import { centavosParaReais, dataDaChamada } from "@/lib/formato";
import { obterReserva } from "@/lib/reservas";
import { obterUsuarioDaSessao } from "@/lib/sessao";

import estilos from "./page.module.css";

/**
 * A reserva: os itens, o total e o cronômetro dos 10 minutos (Story 3.6).
 *
 * **Ela tem endereço próprio porque a reserva existe no servidor** (decisão do
 * Igor). Uma reserva é uma linha no banco com prazo, não um estado desta tela:
 * ela sobrevive a fechar a aba, e recarregar aqui continua mostrando o mesmo
 * tempo correndo. Um recibo no rodapé da página do evento seria mais barato e
 * perderia o caminho de volta na primeira recarga.
 *
 * **A Story 3.8 acrescentou o pagamento, e com ele a tela passou a ter quatro
 * caras** — uma por estado da reserva (decisão do Igor: fica no mesmo endereço,
 * sem redirecionar). `PENDENTE` mostra o cronômetro e o checkout; `PAGA` troca os
 * dois pela confirmação; `RECUSADA` e `EXPIRADA` explicam que nada foi cobrado e
 * que os lugares voltaram. O endereço é o mesmo porque a reserva é a mesma: o que
 * mudou foi o estado dela, e é isso que o `router.refresh()` do formulário relê.
 *
 * ⚠️ **Server Component, sem uma linha de `"use client"` neste arquivo.** A
 * diretiva é do módulo e arrastaria a página inteira para o cliente; o que
 * precisa de navegador é o cronômetro, e ele é um componente separado que recebe
 * uma string por prop.
 *
 * **A guarda de sessão é a de `/conta` e de `/organizador/eventos`, literal**:
 * sem sessão, `redirect` para o login com o caminho de volta preservado. Não há
 * guarda de papel aqui — o `404` da API já responde por "não é sua", e um
 * organizador logado que abrisse este endereço veria a mesma 404 que veria para
 * uma reserva inexistente.
 */
export default async function PaginaDaReserva({
  params,
}: PageProps<"/reservas/[id]">) {
  // ⚠️ `params` é `Promise` nesta versão do Next — o gêmeo está na página do
  // evento e na do organizador.
  const { id } = await params;

  const usuario = await obterUsuarioDaSessao();
  if (!usuario) {
    redirect(`/login?voltar=${encodeURIComponent(`/reservas/${id}`)}`);
  }

  // `obterReserva` nunca levanta, e é isso que permite os dois `if` abaixo:
  // `notFound()` e `redirect()` **levantam**, e não podem ficar dentro de um
  // `try/catch` — o `try` mora no `lib/reservas.ts`.
  const resultado = await obterReserva(id);

  if (resultado.estado === "nao-encontrado") {
    notFound();
  }

  if (resultado.estado === "indisponivel") {
    return (
      <section className={estilos.pagina}>
        <Link href="/" className={estilos.voltar}>
          ← Programação
        </Link>
        <p className={estilos.aviso}>
          Não foi possível carregar esta reserva agora. Tente de novo em instantes.
        </p>
      </section>
    );
  }

  const reserva = resultado.reserva;
  const pendente = reserva.estado === "PENDENTE";

  return (
    <section className={estilos.pagina}>
      {/* O caminho de volta é o **evento**, e não a programação: quem está nesta
          tela veio de lá, e é para lá que se volta para escolher outro setor. */}
      <Link href={`/eventos/${reserva.evento_id}`} className={estilos.voltar}>
        ← {reserva.evento_nome}
      </Link>

      <div className={estilos.cabecalho}>
        <div>
          <span className="kicker">Reserva</span>
          <h1 className={estilos.nomeDoEvento}>{reserva.evento_nome}</h1>
          <p className={estilos.data}>{dataDaChamada(reserva.evento_data_hora)}</p>
        </div>

        {/* ⚠️ **O cronômetro só existe enquanto ele significa alguma coisa.**
            Numa reserva paga ele contaria para trás um prazo que não vale mais;
            numa expirada, contaria de zero para baixo. Quem diz se o prazo
            importa é o `estado`, nunca o relógio (Story 3.7). */}
        {pendente && <Cronometro expiraEm={reserva.expira_em} />}
      </div>

      {/* A cara de cada desfecho, acima dos itens: quem chega aqui depois de
          pagar quer saber o que aconteceu antes de reler a conta. */}
      {reserva.estado === "PAGA" && (
        <>
          <p className={estilos.confirmacao}>
            <strong>Pagamento aprovado.</strong> Seus lugares estão garantidos.
          </p>

          {/* ⚠️ **Um canhoto por ingresso** (EXPERIENCE.md): dois ingressos são
              dois blocos, com códigos diferentes — nunca uma linha dizendo
              "2 ×". É essa separação que faz sentido na porta, onde cada pessoa
              apresenta o dela.

              ⚠️ **O código aparece, o QR ainda não.** Esta story entrega o
              código não forjável; desenhá-lo como QR é a Story 4.2, junto do
              canhoto cheio e de `Meus ingressos`. O componente de QR já existe
              no projeto desde o Pix da 3.8, então lá é reuso, não trabalho
              novo. Antecipá-lo aqui deixaria a 4.2 sem conteúdo e duplicaria a
              tela em duas rotas. */}
          <div className={estilos.canhotos}>
            {reserva.ingressos.map((ingresso) => (
              <div key={ingresso.id} className={estilos.canhoto}>
                <div className={estilos.identidadeDoCanhoto}>
                  <span className={estilos.setorDoCanhoto}>
                    {ingresso.setor_nome}
                  </span>
                  <span className={estilos.titular}>{ingresso.titular_nome}</span>
                </div>

                {/* `<code>` e não `<span>`: é dado de máquina, e a semântica
                    ajuda quem copia com leitor de tela. */}
                <code className={estilos.codigoDoIngresso}>{ingresso.codigo}</code>
              </div>
            ))}
          </div>
        </>
      )}

      {reserva.estado === "RECUSADA" && (
        <p className={estilos.recusa}>
          <strong>Pagamento recusado.</strong> Nada foi cobrado, e os lugares
          voltaram para a venda.
        </p>
      )}

      {reserva.estado === "EXPIRADA" && (
        <p className={estilos.recusa}>
          <strong>O prazo acabou.</strong> Nada foi cobrado, e os ingressos
          voltaram para a venda.
        </p>
      )}

      {reserva.estado === "CANCELADA" && (
        <p className={estilos.recusa}>
          <strong>Reserva cancelada.</strong> Nada foi cobrado.
        </p>
      )}

      {/* Uma lista de fios, como todo agrupamento deste produto: sem card, sem
          sombra, sem raio (UX-DR3). */}
      <div className={estilos.itens}>
        {reserva.itens.map((item) => (
          <div key={item.setor_id} className={estilos.item}>
            <span className={estilos.nomeDoSetor}>{item.setor_nome}</span>
            <span className={estilos.quantidade}>
              {item.quantidade} ×{" "}
              {/* O preço **congelado** no ato da reserva. Se o organizador mudar
                  a tabela amanhã, esta linha continua dizendo quanto custou. */}
              R$ {centavosParaReais(item.preco_unitario_centavos)}
            </span>
            <span className={estilos.subtotal}>
              R$ {centavosParaReais(item.preco_unitario_centavos * item.quantidade)}
            </span>
          </div>
        ))}
      </div>

      <div className={estilos.rodape}>
        <span className={estilos.rotuloDoTotal}>Total</span>
        <span className={estilos.total}>
          R$ {centavosParaReais(reserva.total_centavos)}
        </span>
      </div>

      {pendente ? (
        <>
          <p className={estilos.nota}>
            Seus lugares estão segurados até o fim do prazo acima. Passado ele, os
            ingressos voltam para a venda.
          </p>

          {/* O nome da conta desce como **dado**, não como função — a fronteira
              servidor/cliente do projeto. É ele que preenche o campo Nome, e é
              dele que sai o `titular_nome` do ingresso na Story 3.9. */}
          <FormularioDePagamento reservaId={reserva.id} nomeDaConta={usuario.nome} />
        </>
      ) : (
        // ⚠️ **Sem "tentar de novo" aqui**, e é decisão: a reserva morreu, e o
        // estoque já voltou. Reservar de novo é ver preço e disponibilidade de
        // agora, na página do evento — a escolha antiga não sobrevive de
        // propósito, como já não sobrevive à ida ao login desde a 3.6.
        <p className={estilos.nota}>
          <Link href={`/eventos/${reserva.evento_id}`}>
            Ver o show na programação
          </Link>
        </p>
      )}
    </section>
  );
}
