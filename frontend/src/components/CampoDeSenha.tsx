"use client";

import { useState } from "react";

import Campo from "@/components/Campo";

import estilos from "./CampoDeSenha.module.css";

/**
 * O `<Campo>` de senha, com o botão que revela o que foi digitado.
 *
 * **Componente separado, e não uma prop no `<Campo>`.** O `Campo` não tem
 * `"use client"` de propósito — ele não tem interação própria —, e revelar a
 * senha é estado. Uma prop `revelavel` ali dentro obrigaria o componente inteiro
 * a virar ilha para servir a dois campos de todo o produto.
 *
 * ⚠️ **`type="button"`, e essa é a linha que mais importa aqui.** O padrão de um
 * `<button>` dentro de `<form>` é `submit`: sem isto, tocar no olho **envia o
 * formulário** — no login, com a senha ainda pela metade, e o que aparece na
 * tela é "E-mail ou senha incorretos".
 *
 * ⚠️ **O ícone é SVG inline, nunca caractere de fonte** — mesma regra do
 * `<Veredito>` da Story 5.4: `👁` e afins viram retângulo vazio em Android sem
 * fonte de emoji, e aí o botão fica invisível sem nada acusar.
 *
 * O `type` do input é a única coisa que muda. O valor não é tocado, então o
 * campo continua podendo ser controlado (login, que preenche pelas contas de
 * avaliação) ou não controlado (cadastro, que lê tudo por `FormData` no envio).
 */
type Props = {
  id: string;
  rotulo: string;
} & Omit<React.ComponentPropsWithoutRef<"input">, "id" | "className" | "type">;

export default function CampoDeSenha({ id, rotulo, ...props }: Props) {
  const [visivel, setVisivel] = useState(false);

  return (
    <div className={estilos.envolucro}>
      <Campo id={id} rotulo={rotulo} type={visivel ? "text" : "password"} {...props} />
      <button
        type="button"
        className={estilos.olho}
        onClick={() => setVisivel((atual) => !atual)}
        // O rótulo diz a **ação**, não o estado — é o que o leitor de tela
        // anuncia ao chegar no botão. O `aria-pressed` é quem carrega o estado.
        aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
        aria-pressed={visivel}
        // ⚠️ **Sem `tabIndex={-1}`**, embora tirá-lo da tabulação seja tentador
        // para não interromper o caminho campo → enviar. Quem depende de teclado
        // é justamente quem mais precisa conferir o que digitou, e um controle
        // que só o mouse alcança não é um controle acessível.
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M1.8 12S5.6 5.6 12 5.6 22.2 12 22.2 12 18.4 18.4 12 18.4 1.8 12 1.8 12Z" />
          <circle cx="12" cy="12" r="3.1" />
          {visivel && <line x1="3.6" y1="3.6" x2="20.4" y2="20.4" />}
        </svg>
      </button>
    </div>
  );
}
