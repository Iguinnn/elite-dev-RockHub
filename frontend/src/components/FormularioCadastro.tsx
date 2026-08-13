"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import AvisoDeErro from "@/components/AvisoDeErro";
import Botao from "@/components/Botao";
import Campo from "@/components/Campo";
import CampoDeSenha from "@/components/CampoDeSenha";
import { ErroDaApi, chamarApi } from "@/lib/api";

const MENSAGEM_GENERICA =
  "Não foi possível criar a conta agora. Tente de novo em instantes.";

/** Mesma convenção do login: o texto vem do `codigo`, nunca da `mensagem`. */
function mensagemParaCodigo(codigo: string): string {
  if (codigo === "EMAIL_JA_CADASTRADO") {
    return "Esse e-mail já tem conta. Entre com ele ou use outro.";
  }
  if (codigo === "DADOS_INVALIDOS") {
    return "Confira os dados do formulário.";
  }
  return MENSAGEM_GENERICA;
}

/** Mesma prop do login, pelo mesmo motivo: já validada no servidor. */
type Props = { voltar?: string };

export default function FormularioCadastro({ voltar = "/" }: Props) {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function aoEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);

    const dados = new FormData(evento.currentTarget);
    const nome = String(dados.get("nome") ?? "");
    const email = String(dados.get("email") ?? "");
    const senha = String(dados.get("senha") ?? "");
    const confirmacao = String(dados.get("confirmacao") ?? "");

    // Duas regras conferidas antes do `fetch`. A primeira é gentileza: o
    // servidor recusaria igual, e evitar a ida à rede é retorno imediato. A
    // segunda **só existe aqui** — "duas caixas de texto iguais" é ergonomia
    // de quem digita, não regra de negócio, e por isso a confirmação nem
    // chega ao corpo da requisição.
    if (senha.length < 6) {
      setErro("A senha precisa ter ao menos 6 caracteres.");
      return;
    }
    if (senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }

    setEnviando(true);

    try {
      await chamarApi("/auth/cadastro", {
        method: "POST",
        body: JSON.stringify({ nome, email, senha }),
      });
      // Sem encaminhar por papel: toda conta criada aqui nasce CLIENTE, e nem
      // `/organizador` nem `/portaria` existem. O destino é o `voltar`, quando
      // veio de uma página protegida.
      //
      // ⚠️ `refresh()` obrigatório antes do `push` — o cadastro já abre sessão,
      // e sem ele o masthead continuaria mostrando `Entrar`.
      router.refresh();
      router.push(voltar);
    } catch (erroCapturado) {
      // Erro de rede (`TypeError: Failed to fetch`) não passa pelo `ErroDaApi`
      // e não tem `codigo` — daí o `instanceof` antes de ler qualquer coisa.
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
      <Campo id="nome" name="nome" rotulo="Nome" type="text" autoComplete="name" required />
      <Campo id="email" name="email" rotulo="E-mail" type="email" autoComplete="email" required />
      {/* `new-password` nos dois, nunca `current-password`: é o que faz o
          gerenciador de senhas oferecer uma senha nova em vez de tentar
          preencher a de uma conta que ainda não existe. */}
      <CampoDeSenha
        id="senha"
        name="senha"
        rotulo="Senha"
        autoComplete="new-password"
        required
      />
      {/* O olhinho vale nos dois, e aqui ele resolve mais do que no login: esta
          tela não tem "esqueci minha senha", então uma divergência de digitação
          entre os dois campos só aparece como recusa no envio. */}
      <CampoDeSenha
        id="confirmacao"
        name="confirmacao"
        rotulo="Repetir senha"
        autoComplete="new-password"
        required
      />

      <AvisoDeErro mensagem={erro} />

      <Botao type="submit" disabled={enviando}>
        Criar conta
      </Botao>
    </form>
  );
}
