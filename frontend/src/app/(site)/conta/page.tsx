import { redirect } from "next/navigation";

import DadosDaConta from "@/components/DadosDaConta";
import { obterUsuarioDaSessao } from "@/lib/sessao";

/**
 * Dados da conta e a saída. Server Component com a guarda de sessão.
 *
 * **A guarda mora aqui, não num `middleware`.** O caminho que todo tutorial
 * mostra é conferir o cookie antes de a rota renderizar — mas o middleware só
 * consegue ver que **existe** um cookie, não que ele vale; validar o JWT ali
 * exigiria o `JWT_SECRET` no ambiente do frontend, que é o contrário do AD-2.
 * E ele viraria uma segunda lista de rotas protegidas, paralela às páginas:
 * duas listas divergem, e a que fica desatualizada é sempre a que ninguém olha.
 *
 * O custo é repetir três linhas em cada página protegida. Elas ficam ao lado do
 * conteúdo que protegem, que é onde quem edita a página vai olhar.
 *
 * ⚠️ `redirect()` funciona levantando `NEXT_REDIRECT` e não pode ficar dentro
 * de `try/catch`. Aqui não fica: o `try` mora dentro do `sessao.ts`, e o que
 * sobra é um `if`.
 *
 * **O conteúdo saiu daqui na Story 5.1** e virou `<DadosDaConta>`: a portaria
 * ganhou casca própria e precisa da mesma tela dentro dela. O que sobrou nesta
 * página é a guarda — que é justamente a parte que **não** se compartilha,
 * porque o caminho de volta do `?voltar=` é diferente em cada rota.
 *
 * ⚠️ **`PORTARIA` é mandada para `/portaria/conta`, e este `redirect` é a única
 * entrada da casca da portaria a partir do site** (decisão do Igor, Story 5.1).
 *
 * O masthead do `(site)` não tem — e não vai ter — item de portaria: a casca
 * própria existe justamente para não obrigar quem está em pé na porta a
 * atravessar uma programação de shows. O efeito colateral era um beco. Quem
 * caísse no `(site)` por qualquer motivo (o 404 da raiz carrega o masthead de
 * propósito, e a barra de endereço sempre existiu) ficava com dois links —
 * `Início` e `Minha conta` — e nenhum deles voltava para `/portaria`.
 *
 * Este `redirect` fecha o laço **sem tocar no masthead**, por um link que ele já
 * oferece: `Minha conta` devolve a portaria para dentro da casca dela, e de lá
 * *Turnos* está a um toque. A alternativa era o item novo no masthead, e ela
 * custava exatamente a decisão que a casca própria comprou.
 *
 * E resolve uma duplicação que a extração do `<DadosDaConta>` criou: sem ele,
 * `/conta` e `/portaria/conta` mostram a **mesma tela**, e qual casca aparece
 * depende de qual endereço foi digitado. Agora cada papel tem uma conta só, na
 * casca dele.
 *
 * O organizador **não** é rebatido: a casca dele é o próprio `(site)`, e as duas
 * telas de `/organizador` moram lá dentro.
 */
export default async function Conta() {
  const usuario = await obterUsuarioDaSessao();

  if (!usuario) {
    redirect("/login?voltar=%2Fconta");
  }
  if (usuario.papel === "PORTARIA") {
    redirect("/portaria/conta");
  }

  return <DadosDaConta usuario={usuario} />;
}
