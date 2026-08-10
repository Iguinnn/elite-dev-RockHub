"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Botao from "@/components/Botao";
import { chamarApi } from "@/lib/api";

/**
 * Encerra a sessão. Ilha de cliente dentro de uma página de servidor.
 *
 * ⚠️ **O `router.refresh()` é obrigatório.** O masthead é Server Component: sem
 * ele o cookie some, a navegação acontece — e o cabeçalho continua exibindo
 * `Minha conta`, servido do cache do roteador. Não há erro nenhum na tela; ela
 * só passa a mentir.
 */
export default function BotaoSair() {
  const router = useRouter();
  const [saindo, setSaindo] = useState(false);

  async function aoSair() {
    setSaindo(true);

    try {
      await chamarApi("/auth/logout", { method: "POST" });
    } catch {
      // Sem aviso de erro na tela, mas o `refresh` abaixo acontece de todo
      // jeito: se o cookie sobreviveu, o masthead voltar a mostrar `Minha
      // conta` é a verdade — e é melhor do que uma tela que mente.
    }

    router.refresh();
    router.push("/");
  }

  return (
    <Botao type="button" onClick={aoSair} disabled={saindo}>
      Sair
    </Botao>
  );
}
