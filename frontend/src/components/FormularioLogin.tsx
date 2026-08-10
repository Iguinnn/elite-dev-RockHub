"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import { ErroDaApi, chamarApi } from "@/lib/api";

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

/**
 * O `voltar` chega **já validado** por `caminhoInternoSeguro`, do Server
 * Component que renderiza esta tela. Nada de `useSearchParams()` aqui: além de
 * exigir fronteira de `<Suspense>`, faria a sanitização acontecer no navegador.
 */
type Props = { voltar?: string };

export default function FormularioLogin({ voltar = "/" }: Props) {
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
      // ⚠️ O `refresh()` vem antes do `push` e não é opcional: o masthead é
      // Server Component e o roteador serviria a versão em cache, ainda com
      // `Entrar` no lugar de `Minha conta`. Não dá erro nenhum — só a tela
      // mente.
      router.refresh();
      router.push(voltar);
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
      <Campo id="email" name="email" rotulo="E-mail" type="email" autoComplete="email" required />
      <Campo
        id="senha"
        name="senha"
        rotulo="Senha"
        type="password"
        autoComplete="current-password"
        required
      />

      <AvisoDeErro mensagem={erro} />

      <Botao type="submit" disabled={enviando}>
        Entrar
      </Botao>
    </form>
  );
}
