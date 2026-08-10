"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ErroDaApi, chamarApi } from "@/lib/api";

import estilos from "./FormularioLogin.module.css";

const MENSAGEM_GENERICA = "Não foi possível entrar agora. Tente de novo em instantes.";

/**
 * O texto do erro é escolhido pelo `codigo` que a API devolve, nunca pela
 * `mensagem` — a mensagem do servidor é para humano que lê log; o texto de
 * tela é decisão de produto (convenção da Story 1.4).
 */
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "CREDENCIAIS_INVALIDAS") {
    return "E-mail ou senha incorretos.";
  }
  return MENSAGEM_GENERICA;
}

export default function FormularioLogin() {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    const dados = new FormData(evento.currentTarget);

    try {
      await chamarApi("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: dados.get("email"),
          senha: dados.get("senha"),
        }),
      });
      router.push("/");
    } catch (erroCapturado) {
      const mensagem =
        erroCapturado instanceof ErroDaApi
          ? mensagemParaCodigo(erroCapturado.codigo)
          : MENSAGEM_GENERICA;
      setErro(mensagem);
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar}>
      <div className={estilos.campo}>
        <label htmlFor="email" className={estilos.rotulo}>
          E-mail
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          className={estilos.entrada}
        />
      </div>

      <div className={estilos.campo}>
        <label htmlFor="senha" className={estilos.rotulo}>
          Senha
        </label>
        <input
          id="senha"
          name="senha"
          type="password"
          autoComplete="current-password"
          required
          className={estilos.entrada}
        />
      </div>

      {/* A região existe sempre, vazia, e só o texto entra depois: leitor de
          tela que recebe o `role="alert"` junto com o conteúdo pode não
          anunciar nada. Vazia ela não ocupa espaço. */}
      <div role="alert">
        {erro && <p className={estilos.erro}>{erro}</p>}
      </div>

      <button type="submit" disabled={enviando} className={estilos.botao}>
        Entrar
      </button>
    </form>
  );
}
