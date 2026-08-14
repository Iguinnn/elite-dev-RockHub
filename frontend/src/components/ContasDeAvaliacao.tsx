"use client";

import estilos from "./ContasDeAvaliacao.module.css";

/**
 * As contas semeadas, clicáveis, na tela de login.
 *
 * Existe para quem avalia: o enunciado dá uma hora de teste, e digitar cinco
 * e-mails a partir de outra aba é atrito puro num caminho que não é o que está
 * sendo avaliado. Um toque preenche os dois campos.
 *
 * ⚠️ **Estas constantes são uma segunda fonte de verdade, e isso é consciente.**
 * A primeira é `backend/seeds/semear.py` — trocar um e-mail lá e esquecer daqui
 * faz esta tela mentir, sem teste nenhum acusar (não há teste de frontend neste
 * projeto). A alternativa era uma rota pública devolvendo as contas semeadas, o
 * que resolve a divergência e cria um endpoint público que lista credenciais;
 * para cinco linhas que só mudam se eu mudar o seed de propósito, o preço não se
 * paga. **Quem mexer no `semear.py` mexe aqui.**
 *
 * A senha não é segredo: ela já está publicada no README, que é o que o
 * enunciado pede. O comentário do `semear.py` diz o mesmo em espelho — é dado de
 * avaliação, não credencial de produção.
 *
 * `<details>` nativo, como o `<dialog>` da Story 4.4 e o `<form onSubmit>` da
 * 5.3: expandir e recolher é comportamento que o navegador já tem, com teclado e
 * leitor de tela junto, e escrevê-lo em `useState` seria refazer pior.
 */
const SENHA_DE_AVALIACAO = "rockhub123";

const GRUPOS: ReadonlyArray<{
  papel: string;
  pessoas: ReadonlyArray<{ nome: string; email: string }>;
}> = [
  {
    // Duas, pelo mesmo motivo das duas portarias: com uma conta só não dá para
    // conferir que `Meus eventos` mostra só os eventos de quem está na sessão.
    papel: "Organizador",
    pessoas: [
      { nome: "Helena Marques", email: "organizador@rockhub.dev" },
      { nome: "Rafael Nunes", email: "organizador2@rockhub.dev" },
    ],
  },
  {
    papel: "Cliente",
    pessoas: [
      { nome: "Bruno Tavares", email: "cliente@rockhub.dev" },
      { nome: "Marina Aoki", email: "cliente2@rockhub.dev" },
    ],
  },
  {
    // As duas existem porque a escala da portaria é uma escolha: escalar só o
    // Jonas e tentar validar com a Ana é o cenário do AD-7, e é o que o roteiro
    // de avaliação percorre.
    papel: "Portaria",
    pessoas: [
      { nome: "Jonas Ribeiro", email: "portaria@rockhub.dev" },
      { nome: "Ana Sampaio", email: "portaria2@rockhub.dev" },
    ],
  },
];

export default function ContasDeAvaliacao({
  onEscolher,
}: {
  onEscolher: (email: string, senha: string) => void;
}) {
  return (
    <details className={estilos.contas}>
      <summary className={estilos.resumo}>
        {/* Decorativa: quem lê por leitor de tela já ouve "expandido/recolhido"
            do próprio `<details>`. */}
        <svg
          className={estilos.seta}
          viewBox="0 0 24 24"
          width="10"
          height="10"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M8 4l9 8-9 8" />
        </svg>
        Contas de avaliação
      </summary>

      <p className={estilos.senha}>
        Toque numa conta para preencher. Todas usam a senha{" "}
        <code>{SENHA_DE_AVALIACAO}</code>.
      </p>

      {GRUPOS.map((grupo) => (
        <div key={grupo.papel} className={estilos.grupo}>
          <p className={estilos.papel}>{grupo.papel}</p>
          <ul className={estilos.lista}>
            {grupo.pessoas.map((pessoa) => (
              <li key={pessoa.email}>
                {/* ⚠️ `type="button"`: este bloco fica **fora** do `<form>`, mas
                    o padrão `submit` de um `<button>` sem tipo é o tipo de coisa
                    que passa a valer no dia em que alguém mover o bloco para
                    dentro. */}
                <button
                  type="button"
                  className={estilos.conta}
                  onClick={() => onEscolher(pessoa.email, SENHA_DE_AVALIACAO)}
                >
                  <span className={estilos.nome}>{pessoa.nome}</span>
                  <span className={estilos.email}>{pessoa.email}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </details>
  );
}
