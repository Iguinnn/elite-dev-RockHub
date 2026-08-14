import { dataPorExtenso, terminoDoShow } from "@/lib/formato";

import estilos from "./AvisoDaVirada.module.css";

/**
 * "Termina no dia seguinte, 15 de agosto de 2026, 02h00" — a frase que torna
 * visível a inferência da meia-noite (techspec `docs/techspec-fim-do-evento.md`).
 *
 * **Por que ela existe.** O formulário pede só a **hora** de término, e quando ela
 * é menor ou igual à de início o sistema soma um dia sozinho: o show das 23h que
 * acaba às 02h cai no dia seguinte. Isso é conveniência para quem publica — um
 * calendário a menos num formulário que já tem seis campos —, e o preço é que a
 * inferência precisa ser dita em voz alta. Sem esta frase, quem digita `02:00` não
 * tem como saber se marcou de madrugada ou se acabou de criar um show que termina
 * antes de começar.
 *
 * ⚠️ **Ela só aparece quando a data vira**, e o silêncio é a decisão: num show
 * das 21h às 23h30 não há nada a explicar, e um aviso permanente dizendo "termina
 * no mesmo dia" seria ruído embaixo de todo campo. A frase é a exceção falando, e
 * é assim que ela se faz notar.
 *
 * **Componente compartilhado desde o primeiro dia, e não copiado**, porque nasce
 * com dois consumidores: publicar e editar. É a convenção do `Campo` e do `Botao`
 * lida ao contrário — a régua diz que o **terceiro** consumidor obriga a extrair,
 * e aqui os dois já existem antes de a primeira linha ser escrita.
 *
 * Sem `"use client"`, como o `Campo`: nenhuma interação própria. Importado pelas
 * duas ilhas, ele vai para o bundle do navegador do mesmo jeito — a diretiva só
 * marcaria como ilha algo que não é.
 */
export default function AvisoDaVirada({
  data,
  hora,
  horaFim,
}: {
  /** `AAAA-MM-DD` do campo de data. */
  data: string;
  /** `HH:MM` do horário de início. */
  hora: string;
  /** `HH:MM` do horário de término. */
  horaFim: string;
}) {
  // Enquanto um dos três estiver vazio não há o que inferir, e o `Date` montado
  // seria inválido. Silêncio, e não uma frase de erro: a pessoa está no meio de
  // preencher, e não errou nada ainda.
  if (!data || !hora || !horaFim) return null;

  const inicio = new Date(`${data}T${hora}`);
  if (Number.isNaN(inicio.getTime())) return null;

  const fim = terminoDoShow(data, horaFim, inicio);
  if (fim === null) return null;

  // A comparação é entre os **dias do calendário local**, e não entre os
  // instantes: `fim > inicio` é sempre verdadeiro por construção, e o que decide
  // se há algo a dizer é a data ter mudado de página.
  if (fim.getDate() === inicio.getDate() && fim.getMonth() === inicio.getMonth()) {
    return null;
  }

  return (
    <p className={estilos.aviso}>
      Termina no dia seguinte — {dataPorExtenso(fim.toISOString())}
    </p>
  );
}
