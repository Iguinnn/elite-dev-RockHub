"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import CampoDeSenha from "@/components/CampoDeSenha";
import ContasDeAvaliacao from "@/components/ContasDeAvaliacao";
import { ErroDaApi, chamarApi } from "@/lib/api";
import { casaDoPapel } from "@/lib/papel";

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
 * ⚠️ **A função saiu daqui em 13/08/2026** e mora em `lib/papel.ts`. Ela servia
 * a este arquivo só, e a conferência mostrou que as **guardas de papel** das
 * páginas precisavam do mesmo mapa: elas faziam `redirect("/")`, e `/` não é a
 * casa da portaria. O motivo inteiro está lá.
 */

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
/**
 * `children` é o rodapé "Ainda não tem conta?", que continua sendo montado no
 * Server Component da página — o `<Link>` dele depende do `?voltar=` já
 * validado lá. Ele chega aqui como children para que as *Contas de avaliação*
 * possam ficar **abaixo** dele sem que a página precise saber preencher campo
 * nenhum: o estado dos dois campos mora neste componente, e só nele.
 *
 * A alternativa era o bloco de contas escrever direto no DOM por
 * `document.getElementById`, o que dispensaria o children e traria de volta um
 * segundo dono do valor dos campos.
 */
type Props = { voltar?: string; children?: React.ReactNode };

export default function FormularioLogin({ voltar, children }: Props) {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // ⚠️ **Os campos passaram a ser controlados**, e antes eram lidos por
  // `FormData` no envio. É o que permite às *Contas de avaliação* preenchê-los:
  // com entrada não controlada, escrever o valor exigiria alcançar o nó do DOM.
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    try {
      const usuario = await chamarApi<RespostaDoLogin>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, senha }),
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
    <>
      <form onSubmit={aoEnviar}>
        <Campo
          id="email"
          name="email"
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(evento) => setEmail(evento.target.value)}
        />
        <CampoDeSenha
          id="senha"
          name="senha"
          rotulo="Senha"
          autoComplete="current-password"
          required
          value={senha}
          onChange={(evento) => setSenha(evento.target.value)}
        />

        <AvisoDeErro mensagem={erro} />

        {/* ⚠️ **O rótulo muda desde 13/08/2026** (decisão do Igor, depois da
            varredura de superfícies de erro). Quatro botões do produto já
            trocavam de palavra durante o envio e quatro não — sem regra, só pela
            ordem em que foram escritos. O `disabled` sozinho **não anuncia
            progresso**: quem usa leitor de tela ouve "botão indisponível" e não
            fica sabendo que algo está acontecendo. A palavra é o anúncio. */}
        <Botao type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </Botao>
      </form>

      {children}

      {/* O erro anterior sai junto: preencher com outra conta e continuar
          lendo "E-mail ou senha incorretos" da tentativa passada faria a tela
          responder pelo que não está mais nos campos. */}
      <ContasDeAvaliacao
        onEscolher={(emailEscolhido, senhaEscolhida) => {
          setEmail(emailEscolhido);
          setSenha(senhaEscolhida);
          setErro(null);
        }}
      />
    </>
  );
}
