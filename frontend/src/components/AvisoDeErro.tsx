import estilos from "./AvisoDeErro.module.css";

/**
 * Região de erro do formulário — e a regra invisível que a faz funcionar.
 *
 * O `<div role="alert">` **existe sempre no DOM, vazio**, e só o texto entra
 * depois. Leitor de tela que recebe o `role` junto com o conteúdo, num nó que
 * acabou de aparecer, pode não anunciar nada: ele observa mudanças *dentro* de
 * uma região viva. Vazia, a região não ocupa espaço nenhum na tela.
 *
 * Este componente existe por um critério diferente do `Campo` e do `Botao`.
 * Aqueles dois foram extraídos porque se repetem. Este foi extraído porque a
 * regra acima é invisível: escrita como comentário dentro de um formulário, ela
 * é a primeira coisa que alguém apaga por parecer óbvia ao copiar para o
 * segundo — e o que se perde não é estilo, é o anúncio do erro para quem usa
 * leitor de tela (UX-DR9). Componente é onde uma regra dessas se protege
 * sozinha.
 */
/**
 * `ReactNode` e não `string`: desde o code review da Epic 2 um dos avisos leva
 * `<Link>` dentro — "sua sessão expirou, entre de novo" sem o caminho para
 * entrar é um beco sem saída. A regra do `role="alert"` acima vale igual para
 * texto e para JSX.
 */
export default function AvisoDeErro({ mensagem }: { mensagem: React.ReactNode }) {
  return (
    <div role="alert">
      {mensagem && <p className={estilos.erro}>{mensagem}</p>}
    </div>
  );
}
