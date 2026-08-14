"use client";

import { useEffect, useRef, useState } from "react";
import { DayPicker } from "react-day-picker";
import { ptBR } from "react-day-picker/locale";
import "react-day-picker/style.css";

import estilos from "./SeletorDeData.module.css";

/**
 * O campo de data com calendário próprio — `react-day-picker` vestido de jornal
 * noturno (13/08/2026).
 *
 * **Por que ele existe.** O popup do `<input type="date">` é desenhado pelo
 * navegador e **não é estilizável**: não é shadow DOM que a página alcance, e
 * nem `accent-color` nem CSS chegam nele. O `color-scheme: dark` do
 * `globals.css` já o deixa escuro desde a Epic 1 — o que sobra é o azul do
 * Chrome no meio de um produto que tem um acento só, e ele é rosa (UX-DR1). Para
 * a data ficar na identidade, o seletor tinha que deixar de ser o do navegador.
 *
 * **A biblioteca foi decisão do Igor.** A alternativa era escrever o calendário
 * à mão: sem dependência nova, mas com grade, navegação de mês, teclado (setas,
 * Home/End, PageUp/PageDown), `role="grid"` e anúncio de mês — que é onde um
 * calendário caseiro costuma virar um seletor bonito que ninguém opera pelo
 * teclado, e o UX-DR9 cobra. A dependência custa três pacotes e traz tudo isso
 * testado; escrever custaria as mesmas horas com menos garantia, a três dias do
 * prazo.
 *
 * ⚠️ **O `<input type="date">` continua aqui, e isso é de propósito.** Ele não
 * foi trocado por um campo de texto — é ele quem mantém três coisas que a
 * biblioteca não dá:
 *
 * - **digitar continua funcionando**, com a máscara do navegador;
 * - **o `FormData` do formulário não muda**: `dados.get("data")` lê este mesmo
 *   `name="data"`, e `aoEnviar` não soube de nada;
 * - **no celular, tocar o campo abre o seletor nativo**, que é grande, tem
 *   rolagem de dedo e é melhor que qualquer grade nossa num alvo de 44px. Não dá
 *   para impedir isso, e não se quer impedir.
 *
 * O que sumiu foi só o **ícone** do navegador (`::-webkit-calendar-picker-indicator`
 * no CSS ao lado), substituído pelo botão daqui. No desktop, portanto, o popup
 * feio não abre mais por nenhum caminho.
 */
export default function SeletorDeData({
  id,
  name,
  rotulo,
  minimo,
  obrigatorio = false,
  valorInicial = "",
  aoMudar,
}: {
  id: string;
  name: string;
  rotulo: string;
  /** `AAAA-MM-DD`, o mesmo formato do `min` do `<input type="date">`. */
  minimo: string;
  obrigatorio?: boolean;
  /**
   * Avisa o formulário a cada mudança — digitada ou escolhida no calendário
   * (techspec `docs/techspec-fim-do-evento.md`).
   *
   * ⚠️ **Ele não transforma o campo em controlado pelo pai**, e a diferença
   * importa: o `valorInicial` acima continua sendo valor inicial, o estado
   * continua morando aqui, e quem manda no campo depois da primeira renderização
   * continua sendo quem está digitando. O que este retorno dá ao pai é uma
   * **cópia derivada**, para ele conseguir dizer em que dia o show termina quando
   * a hora de fim vira a meia-noite. Sem ele, o formulário só descobriria a data
   * no envio, que é tarde demais para avisar.
   *
   * Chamado nos **dois** lugares que escrevem `valor`. Um só deixaria a frase da
   * virada desatualizada por um dos dois caminhos — e seria justamente o do
   * calendário, que é o mais usado.
   */
  aoMudar?: (valor: string) => void;
  /**
   * `AAAA-MM-DD` com que o campo abre — vazio ao publicar, a data do show ao
   * editar (13/08/2026).
   *
   * ⚠️ **É valor inicial, não valor controlado**, e por isso não há
   * `useEffect` sincronizando os dois: quem manda no campo depois da primeira
   * renderização é quem está digitando. Um efeito que reescrevesse o estado a
   * cada render da página apagaria a data escolhida no meio da edição.
   */
  valorInicial?: string;
}) {
  // `AAAA-MM-DD` ou `""` — o valor do `<input>`, e o que o `FormData` vai ler.
  // Controlado desde 13/08/2026: antes o campo era lido só no envio, e agora o
  // calendário também escreve nele.
  const [valor, setValor] = useState(valorInicial);
  const [aberto, setAberto] = useState(false);
  const invólucro = useRef<HTMLDivElement>(null);

  // ⚠️ **Fechar no clique de fora e no Esc, e os dois no mesmo efeito**: são a
  // mesma intenção ("saí daqui"), e separá-los em dois `useEffect` duplicaria a
  // condição de montagem. `mousedown` e não `click`: no `click` o popup já
  // sumiu quando o navegador decide quem recebeu o evento, e um clique na
  // própria grade fecharia antes de selecionar.
  useEffect(() => {
    if (!aberto) return;

    function aoClicarFora(evento: MouseEvent) {
      if (!invólucro.current?.contains(evento.target as Node)) setAberto(false);
    }
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") setAberto(false);
    }

    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  return (
    <div className={estilos.campo} ref={invólucro}>
      <label htmlFor={id} className={estilos.rotulo}>
        {rotulo}
      </label>

      <div className={estilos.linha}>
        {/* `min` continua no `<input>`, e continua sendo o de São Paulo (ver
            `hojeEmSaoPaulo` no formulário): ele é a barreira de quem **digita**,
            e o `disabled` do calendário é a de quem **clica**. As duas leem a
            mesma prop, então não têm como discordar. */}
        <input
          id={id}
          name={name}
          type="date"
          className={estilos.entrada}
          min={minimo}
          required={obrigatorio}
          value={valor}
          onChange={(e) => {
            setValor(e.target.value);
            aoMudar?.(e.target.value);
          }}
        />

        {/* `aria-expanded` e `aria-haspopup` porque este botão abre uma coisa que
            não está no fluxo da página: sem eles, quem usa leitor de tela ouve
            "botão, escolher no calendário" e não sabe que algo abriu. */}
        <button
          type="button"
          className={estilos.abrir}
          onClick={() => setAberto((estava) => !estava)}
          aria-expanded={aberto}
          aria-haspopup="dialog"
          aria-label="Escolher no calendário"
        >
          {/* SVG inline, e não uma fonte de ícones: o UX-DR2 proíbe fonte
              externa, e um `<img>` seria uma requisição para desenhar 16px.
              `currentColor` faz o traço seguir a cor do botão no hover. */}
          <svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true">
            <rect
              x="1.5"
              y="2.5"
              width="13"
              height="12"
              fill="none"
              stroke="currentColor"
            />
            <path d="M1.5 6h13M5 1v3M11 1v3" stroke="currentColor" fill="none" />
          </svg>
        </button>
      </div>

      {aberto && (
        <div className={estilos.popover} role="dialog" aria-label={rotulo}>
          <DayPicker
            mode="single"
            locale={ptBR}
            selected={aDataDe(valor)}
            // ⚠️ **`defaultMonth`, e nunca `month`.** A primeira versão passava
            // `month` — que é a prop **controlada** — sem um `onMonthChange`, e
            // isso prende o calendário no mês calculado: a seta de avançar fica
            // acesa, recebe o clique e não muda nada, porque quem manda no mês
            // passou a ser esta linha e ela devolve sempre o mesmo valor. Com
            // `defaultMonth`, quem navega é a biblioteca.
            //
            // Ele continua abrindo no mês certo a cada vez porque o popover é
            // **desmontado** ao fechar (`{aberto && …}`): cada abertura remonta o
            // `DayPicker` e recalcula este valor a partir do que está no campo.
            defaultMonth={aDataDe(valor) ?? aDataDe(minimo)}
            // ⚠️ **As duas travas do passado, e elas não são a mesma.**
            // `disabled` apaga os dias anteriores no mês visível; `startMonth`
            // impede navegar para antes deles. Sem a segunda, a seta de voltar
            // desce até 1900 mostrando meses inteiros apagados — que é o
            // "travado" de um calendário que deixa ir aonde não dá para escolher.
            disabled={{ before: aDataDe(minimo) ?? new Date() }}
            startMonth={aDataDe(minimo) ?? new Date()}
            // O foco entra na grade ao abrir: é o que faz o teclado funcionar
            // sem um `Tab` às cegas por cima do popup.
            autoFocus
            onSelect={(escolhida) => {
              if (!escolhida) return;
              const iso = emISO(escolhida);
              setValor(iso);
              aoMudar?.(iso);
              setAberto(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * `AAAA-MM-DD` → `Date` **no fuso local**, e `undefined` para vazio ou inválido.
 *
 * ⚠️ **Nunca `new Date("2026-08-14")`.** Data sozinha, nessa forma, é lida como
 * **UTC** pela especificação — e no Brasil isso volta como dia 13 às 21h. O
 * calendário destacaria o dia errado, e o erro apareceria só para quem está a
 * oeste de Greenwich. É a mesma armadilha que o `aoEnviar` do formulário
 * documenta ao juntar data e hora antes de construir o `Date`.
 */
function aDataDe(iso: string): Date | undefined {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!partes) return undefined;

  const [, ano, mes, dia] = partes;
  return new Date(Number(ano), Number(mes) - 1, Number(dia));
}

/** `Date` → `AAAA-MM-DD`, o formato que o `<input type="date">` exige. */
function emISO(data: Date): string {
  const doisDígitos = (numero: number) => String(numero).padStart(2, "0");
  return `${data.getFullYear()}-${doisDígitos(data.getMonth() + 1)}-${doisDígitos(
    data.getDate(),
  )}`;
}
