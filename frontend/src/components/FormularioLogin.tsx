"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import { ErroDaApi, chamarApi } from "@/lib/api";

import type { UsuarioDaSessao } from "@/lib/sessao";

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
 * O corpo de `POST /auth/login` — o `UsuarioSaida` do backend. Só o `papel`
 * interessa aqui, e é `import type`: o compilador apaga a linha, e nada do
 * `lib/sessao.ts` (que fala com `next/headers`) atravessa para o bundle do
 * navegador. Mesmo caminho que o `FormularioPublicacao` usa com o
 * `lib/eventos.ts`.
 */
type RespostaDoLogin = { papel: UsuarioDaSessao["papel"] };

/**
 * Para onde vai quem acabou de entrar **sem** ter pedido destino nenhum.
 *
 * **Só a portaria muda de casa** (Story 5.1). Ela tem casca própria em
 * `/portaria`, e a alternativa — deixá-la cair na raiz e se virar com o menu —
 * a jogaria numa tela de compra de ingressos sem um único item de navegação que
 * leve ao trabalho dela: o masthead do `(site)` não tem, e não vai ter, item de
 * portaria. Cliente e organizador continuam caindo na raiz, que é a programação
 * e é onde os dois querem estar.
 *
 * Uma função e não um `Record`: o mapa completo teria duas entradas iguais a
 * `"/"` só para não parecer que faltou papel, e uma consulta a um mapa
 * incompleto devolve `undefined` — que o `router.push` não sabe navegar. Aqui o
 * caso não previsto cai no `"/"` por construção.
 */
function casaDoPapel(papel: string): string {
  return papel === "PORTARIA" ? "/portaria" : "/";
}

/**
 * O `voltar` chega **já validado** por `caminhoInternoSeguro`, do Server
 * Component que renderiza esta tela. Nada de `useSearchParams()` aqui: além de
 * exigir fronteira de `<Suspense>`, faria a sanitização acontecer no navegador.
 *
 * ⚠️ **`undefined` significa "ninguém pediu destino", e não é o mesmo que `"/"`**
 * (Story 5.1). É a ausência que libera a regra por papel; o `?voltar=` continua
 * soberano quando existe, porque ele resolve o caso de quem foi interrompido no
 * meio de alguma coisa, e sobrescrevê-lo com um destino por papel quebraria
 * exatamente esse caso. Por isso **não há valor padrão nesta prop**: repor o
 * `"/"` aqui apagaria a distinção que a página tomou o cuidado de preservar, e o
 * destino por papel simplesmente não aconteceria — sem erro, sem log, com a
 * portaria caindo na programação como sempre caiu.
 */
type Props = { voltar?: string };

export default function FormularioLogin({ voltar }: Props) {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    const dados = new FormData(evento.currentTarget);

    try {
      const usuario = await chamarApi<RespostaDoLogin>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: dados.get("email"),
          senha: dados.get("senha"),
        }),
      });
      // ⚠️ O `refresh()` vem antes do `push` e não é opcional: o masthead é
      // Server Component e o roteador serviria a versão em cache, ainda com
      // `Entrar` no lugar de `Minha conta`. Não dá erro nenhum — só a tela
      // mente. Vale igual para a casca da portaria, que também lê a sessão no
      // servidor para escrever o nome de quem está na porta.
      router.refresh();
      router.push(voltar ?? casaDoPapel(usuario.papel));
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
