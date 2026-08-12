"use client";

import { useEffect, useState } from "react";

import estilos from "./Cronometro.module.css";

/**
 * O tempo que resta de uma reserva — o cronômetro dos 10 minutos (Story 3.6).
 *
 * *"Não pisca, não muda de cor, não faz contagem regressiva agressiva. Informa;
 * não pressiona"* — `EXPERIENCE.md#cronômetro de reserva`, literal. Não há
 * animação, não há vermelho no fim, não há tamanho que cresce. Ele é mono
 * versalete como todo estado do sistema.
 *
 * ⚠️ **Ele conta contra o `expira_em` do servidor, e o relógio do navegador é só
 * a régua.** Ele não pergunta nada à API enquanto conta, e **não navega para
 * lugar nenhum ao chegar a zero**: quem decide se a reserva expirou é o banco, na
 * Story 3.7, com o `UPDATE` condicionado a `estado = 'PENDENTE' AND expira_em <
 * now()`. O cronômetro chegando a zero é **informação, não veredito** — uma tela
 * que se acha autoridade sobre a transição seria uma segunda dona dela.
 *
 * ⚠️ **Estado inicial `null` e cálculo no `useEffect`, nunca
 * `useState(() => calcular())`.** O servidor renderiza num instante e o cliente
 * hidrata em outro: um segundo de diferença é um `text content did not match`.
 * Até o primeiro tique a tela mostra um traço, que dura um quadro.
 */
export default function Cronometro({ expiraEm }: { expiraEm: string }) {
  const [restante, setRestante] = useState<number | null>(null);

  useEffect(() => {
    const alvo = new Date(expiraEm).getTime();
    const calcular = () => Math.max(0, alvo - Date.now());

    // O primeiro valor sai aqui, já no navegador — é isso que mantém o HTML do
    // servidor e o da hidratação idênticos.
    //
    // ⚠️ **O `eslint-disable` é a parte pensada desta linha.** A regra
    // `set-state-in-effect` existe para impedir renderização em cascata, e ela
    // está certa na maioria dos casos. Aqui o `setState` síncrono roda **uma vez
    // por montagem** e é justamente o que evita o defeito que a regra não
    // enxerga: com o valor calculado no `useState` inicial, o servidor
    // renderizaria `9:58` e o cliente `9:57` um instante depois, e isso é um
    // `text content did not match`. O relógio é um sistema externo cujo primeiro
    // valor só existe no navegador — que é exatamente a exceção que a própria
    // documentação da regra descreve.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRestante(calcular());

    const intervalo = setInterval(() => setRestante(calcular()), 1000);
    // Sem isto, sair da página deixa o `setInterval` rodando e o React avisa que
    // houve `setState` em componente desmontado.
    return () => clearInterval(intervalo);
  }, [expiraEm]);

  if (restante === null) {
    return (
      <span className={estilos.cronometro} aria-live="polite">
        <span className={estilos.rotulo}>Tempo restante</span>
        <span className={estilos.numero}>—</span>
      </span>
    );
  }

  if (restante === 0) {
    return (
      <span className={estilos.cronometro} aria-live="polite">
        <span className={estilos.rotulo}>Reserva</span>
        {/* Sem link, sem botão, sem navegação: a frase diz o que aconteceu, e o
            caminho de volta já está no topo da página. */}
        <span className={estilos.numero}>Expirada</span>
      </span>
    );
  }

  const segundos = Math.floor(restante / 1000);
  const minutos = Math.floor(segundos / 60);

  return (
    // ⚠️ **`polite`, nunca `assertive`.** Um cronômetro anunciado a cada segundo
    // em `assertive` interrompe a leitura da página inteira — o leitor de tela
    // nunca chegaria à lista de itens. Em `polite` ele espera a pausa.
    <span className={estilos.cronometro} aria-live="polite">
      <span className={estilos.rotulo}>Tempo restante</span>
      <span className={estilos.numero}>
        {minutos}:{String(segundos % 60).padStart(2, "0")}
      </span>
    </span>
  );
}
