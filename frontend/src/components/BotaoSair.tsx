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
 *
 * ⚠️ **E ele vem depois do `replace`, não antes.** Este botão só existe na
 * `/conta`, e a `/conta` redireciona para `/login?voltar=%2Fconta` quando não
 * há sessão. Chamar `refresh()` primeiro refaz o RSC de uma página que, com o
 * cookie já apagado, responde com esse redirecionamento — e ele corre contra a
 * navegação para `/`. Quem vence depende da latência: em `localhost` a ordem
 * errada passa despercebida, e na Vercel o `Sair` pode largar a pessoa na tela
 * de login. Saindo primeiro, o `refresh` acontece já na rota de destino, que é
 * onde o masthead precisa ser refeito de qualquer forma.
 *
 * `replace` e não `push`: a `/conta` de onde se está saindo não deve ficar no
 * histórico, senão o botão "voltar" do navegador cai numa página protegida que
 * vai rebater para o login.
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

    router.replace("/");
    router.refresh();
  }

  return (
    <Botao type="button" onClick={aoSair} disabled={saindo}>
      Sair
    </Botao>
  );
}
