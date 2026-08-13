"use client";

import { useState } from "react";

import ContadorDoTurno from "@/components/ContadorDoTurno";
import Leitor from "@/components/Leitor";
import type { TurnoDoLeitor } from "@/lib/turnos";
import type { ContagensDoTurno } from "@/lib/validacao";

/**
 * A parte viva da tela do leitor: o painel do turno e o leitor (Story 5.6).
 *
 * **Ele existe por uma razão só: os quatro números mudam por estado do cliente,
 * e quem os produz é o `<Leitor>`, que fica abaixo deles na tela.** Estado não
 * desce de irmão para irmão — precisa de um pai —, e este é o menor pai possível.
 * O `page.tsx` continua Server Component com as duas guardas de sessão e papel.
 *
 * **Descartei desenhar o contador dentro do `<Leitor>`**, que era zero fiação e
 * deixava os números **abaixo** do botão da câmera, ou seja, dentro da ferramenta
 * em vez de na ficha do turno. E descartei pô-lo no `CabecalhoDaPortaria`, que
 * aparece em duas telas onde não há evento nenhum para contar.
 *
 * ⚠️ **Ele não recebe mais a ficha do show por `children`, e já recebeu.** Isso
 * existia enquanto o contador morava **dentro** do bloco do cabeçalho: era o que
 * permitia ao `page.tsx` montar o nome do show no servidor mesmo com um wrapper
 * cliente em volta. Com o contador em faixa própria, o cabeçalho voltou a ser
 * inteiro do `page.tsx` e o `children` virou fiação sem carga.
 *
 * ⚠️ **O estado nasce do servidor, e não em zero.** `turno.entradas` e
 * `turno.recusas` vêm de `GET /portaria/eventos/{id}`; sem isso, quem assume a
 * porta no meio da noite abriria o leitor marcando zero com trezentas pessoas
 * dentro, e só veria a verdade depois da primeira leitura dela.
 */
export default function PainelDoTurno({ turno }: { turno: TurnoDoLeitor }) {
  const [contagens, setContagens] = useState<ContagensDoTurno>({
    entradas: turno.entradas,
    recusas: turno.recusas,
  });

  return (
    <>
      <ContadorDoTurno contagens={contagens} />

      {/* O `<Leitor>` reporta as contagens de cada resposta e não as guarda: elas
          vêm nos quatro vereditos, e quem as desenha está aqui em cima. */}
      <Leitor eventoId={turno.id} onContagens={setContagens} />
    </>
  );
}
