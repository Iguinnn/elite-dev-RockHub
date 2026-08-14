"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Toast from "@/components/Toast";
import estilos from "@/app/(site)/organizador/eventos/page.module.css";
import { ErroDaApi, chamarApi } from "@/lib/api";

/**
 * O botão de excluir evento, ao lado do `Editar` no detalhe
 * (`docs/techspec-editar-evento.md`, commit 3).
 *
 * ⚠️ **A tela de detalhe é Server Component e continua sendo.** O botão é que é
 * cliente — é a menor ilha possível em volta do único `useState` desta tela.
 * Marcar a página inteira com `"use client"` para acomodar a confirmação
 * jogaria fora as duas guardas de sessão que rodam no servidor, que é o oposto
 * do que o `FormularioEdicao` fez.
 *
 * **Confirmação em dois estágios no próprio botão, sem modal:** `Excluir` vira
 * `Confirmar exclusão`, com `Cancelar` ao lado. *Descartei* o `<dialog>` — não
 * existe modal nenhum no projeto, e a primeira sobreposição de tela do produto
 * não vai nascer para uma operação de organizador. *Descartei* exigir digitar o
 * nome do evento: é a proteção certa para apagar conta ou banco, e
 * desproporcional para um evento sem venda nenhuma, que o organizador republica
 * em dois minutos.
 *
 * **Quem decide se ele aparece é a `page.tsx`**, pela mesma leitura de estoque
 * que decide o `Editar`. Aqui dentro não há checagem de venda: o componente que
 * existe é o botão, e o botão só é montado quando dá para excluir.
 */
export default function BotaoDeExclusao({
  eventoId,
  nome,
}: {
  eventoId: string;
  /** Só para o `aria-label` — a confirmação visível não repete o nome do show. */
  nome: string;
}) {
  const router = useRouter();
  const [confirmando, setConfirmando] = useState(false);
  const [excluindo, setExcluindo] = useState(false);
  const [erro, setErro] = useState<React.ReactNode>(null);

  function mensagemParaCodigo(codigo: string): string {
    if (codigo === "EVENTO_COM_VENDA") {
      // Acontece sem ninguém trapacear: basta esta aba estar aberta desde antes
      // de alguém reservar. A tela estava certa quando renderizou.
      return "Alguém comprou um ingresso enquanto esta página estava aberta. Este evento não pode mais ser excluído.";
    }
    if (codigo === "EVENTO_NAO_ENCONTRADO") {
      // Idem: outra aba excluiu o mesmo evento antes desta.
      return "Este evento já não existe mais. Volte para Meus eventos.";
    }
    return "Não foi possível excluir o evento agora. Tente de novo em instantes.";
  }

  async function excluir() {
    if (excluindo) return;
    setExcluindo(true);
    setErro(null);

    try {
      // `204` sem corpo: o `chamarApi` corta antes do `.json()` e devolve
      // `undefined` — o mesmo caminho do `DELETE` da Story 4.4.
      await chamarApi<void>(`/organizador/eventos/${eventoId}`, {
        method: "DELETE",
      });

      // **`replace` e não `push`**, pelo motivo do commit 2 elevado ao quadrado:
      // com `push`, o botão voltar levaria ao detalhe de um evento que não
      // existe mais — uma 404 no lugar onde a pessoa acabou de estar.
      router.replace("/organizador/eventos");
      // ⚠️ E sem ele a lista pode vir do Router Cache do Next **ainda com a
      // linha apagada dentro**. O `cache: "no-store"` do `listarMeusEventos`
      // fala do fetch no servidor, não do payload que o cliente guardou.
      router.refresh();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof ErroDaApi
          ? mensagemParaCodigo(erroCapturado.codigo)
          : "Não foi possível excluir o evento agora. Tente de novo em instantes.",
      );
      // Volta ao estado inicial: insistir no `Confirmar exclusão` depois de uma
      // recusa que não muda sozinha (venda, evento sumido) é oferecer o mesmo
      // erro de novo. Quem quiser tentar outra vez clica em `Excluir` de novo.
      setConfirmando(false);
      setExcluindo(false);
    }
  }

  if (!confirmando) {
    return (
      <>
        <button
          type="button"
          className={estilos.excluir}
          onClick={() => setConfirmando(true)}
        >
          Excluir
        </button>
        <Toast mensagem={erro} aoFechar={() => setErro(null)} />
      </>
    );
  }

  return (
    <>
      <div className={estilos.confirmacaoDeExclusao}>
        <button
          type="button"
          className={estilos.confirmarExclusao}
          onClick={excluir}
          disabled={excluindo}
          // O nome do show mora aqui, e não no rótulo visível: quem enxerga a
          // tela já tem o `<h1>` ao lado; quem ouve, não.
          aria-label={`Confirmar exclusão de ${nome}`}
        >
          {/* Nada gira e nada pulsa (EXPERIENCE.md#Carregando) — o que muda é a
              palavra. */}
          {excluindo ? "Excluindo…" : "Confirmar exclusão"}
        </button>
        <button
          type="button"
          className={estilos.cancelarExclusao}
          onClick={() => setConfirmando(false)}
          disabled={excluindo}
        >
          Cancelar
        </button>
      </div>
      <Toast mensagem={erro} aoFechar={() => setErro(null)} />
    </>
  );
}
