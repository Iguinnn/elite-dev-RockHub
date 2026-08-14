import Logotipo from "./Logotipo";
import estilos from "./Rodape.module.css";

/**
 * O rodapé do site (decisão do Igor, 14/08/2026).
 *
 * **Server Component, sem uma linha de `"use client"`** — não há estado, não há
 * clique, não há relógio. É o componente mais barato do produto e deve continuar
 * assim: qualquer interação que apareça aqui vira ilha, e uma ilha no rodapé
 * torna dinâmica toda tela que já era.
 *
 * ⚠️ **Os dados da empresa são inventados, e isso está dito no código de
 * propósito.** RockHub não existe: o endereço, o CNPJ, o telefone e o horário
 * são cenário para o rodapé ter o peso que um rodapé real tem. Ninguém deve
 * "corrigi-los" com dados verdadeiros de lugar nenhum, e ninguém deve tratá-los
 * como fonte.
 *
 * ⚠️ **As redes sociais não são links, e a ausência é a decisão.** Elas também
 * são inventadas, então não há destino honesto: apontar para
 * `instagram.com/rockhub` mandaria quem clica para a conta de uma pessoa real,
 * em nome de uma marca que não existe, e `href="#"` é o "botão que não faz nada"
 * que o docstring do `Masthead` recusa desde a Story 2.6. Ícone e arroba
 * mostram os canais sem prometer travessia — e o dia em que existirem contas de
 * verdade, cada `<span>` vira `<a>` sem tocar no CSS.
 *
 * **A marca é o mesmo `<Logotipo>` do masthead**, não uma segunda cópia menor:
 * ele é a fonte única da identidade desde a Story 1.2, e o docstring dele avisa
 * que marca escrita de dois jeitos racha a identidade. Ele já resolve o par de
 * imagens claro/escuro sozinho — este arquivo não sabe que existe tema.
 *
 * **O fio de cima é o único separador**, e ele fecha a página do mesmo jeito que
 * o do masthead a abre. Sem caixa, sem fundo próprio, sem sombra (UX-DR3): o
 * rodapé é o fim da folha, não um bloco pousado nela.
 */

/** Os canais inventados. Um `<span>` cada — ver o docstring acima. */
const REDES = [
  { nome: "Instagram", arroba: "@rockhub", icone: <IconeInstagram /> },
  { nome: "X", arroba: "@rockhub", icone: <IconeX /> },
  { nome: "YouTube", arroba: "/rockhub", icone: <IconeYouTube /> },
  { nome: "Spotify", arroba: "RockHub", icone: <IconeSpotify /> },
];

export default function Rodape() {
  return (
    <footer className={estilos.rodape}>
      <div className={estilos.topo}>
        {/* A marca leva para a raiz, como no masthead — é a convenção que todo
            site cumpre, e o `<Logotipo>` já a implementa. */}
        <div className={estilos.marca}>
          <Logotipo />
          <p className={estilos.assinatura}>
            Ingresso de show sem fila, sem taxa escondida e sem mapa de assento
            que ninguém entende.
          </p>
        </div>

        <div className={estilos.colunas}>
          <section className={estilos.coluna}>
            <h2 className="kicker">A empresa</h2>
            {/* `<address>` é o elemento certo para contato — e o `font-style`
                itálico que ele traz do navegador é zerado no CSS, porque a
                serifada do produto não tem versão itálica em uso. */}
            <address className={estilos.dados}>
              RockHub Entretenimento Ltda.
              <br />
              Rua do Lavradio, 148 — Lapa
              <br />
              Rio de Janeiro, RJ — 20230-070
              <br />
              CNPJ 41.902.775/0001-08
            </address>
          </section>

          <section className={estilos.coluna}>
            <h2 className="kicker">Atendimento</h2>
            <p className={estilos.dados}>
              contato@rockhub.com.br
              <br />
              (21) 3181-4400
              <br />
              Segunda a sexta, 10h às 19h
              <br />
              Em dia de show, até o fim da porta
            </p>
          </section>

          <section className={estilos.coluna}>
            <h2 className="kicker">Nas redes</h2>
            <ul className={estilos.redes}>
              {REDES.map((rede) => (
                <li key={rede.nome} className={estilos.rede}>
                  {/* `aria-hidden` no ícone: o nome da rede está escrito ao
                      lado, e um SVG anunciado diria a mesma coisa duas vezes. */}
                  <span className={estilos.icone} aria-hidden="true">
                    {rede.icone}
                  </span>
                  <span className={estilos.nomeDaRede}>{rede.nome}</span>
                  <span className={estilos.arroba}>{rede.arroba}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>

      {/* ⚠️ **O aviso de ficção é visível na tela, e não só no código.** Endereço,
          CNPJ, telefone e redes são cenário; quem avalia precisa saber disso sem
          abrir o repositório, e quem cair aqui por acaso não deve tentar ligar
          para um número que não atende. Ele abre a faixa de baixo, antes do
          `©` — a ordem importa: lido depois da razão social, o aviso corrige
          uma afirmação que já foi feita. */}
      <p className={estilos.aviso}>
        Empresa, endereço, CNPJ, contatos e redes sociais são{" "}
        <strong className={estilos.ficticio}>fictícios</strong> — este é um
        projeto de demonstração, não um serviço em operação.
      </p>

      {/* A faixa de baixo: o que é da marca à esquerda, o que é meu à direita. */}
      <div className={estilos.base}>
        <p className={estilos.legal}>
          © {new Date().getFullYear()} RockHub Entretenimento Ltda.
        </p>
        <p className={estilos.autoria}>
          Feito por <strong className={estilos.nome}>Igor Duarte Vieira</strong>
          <span className={estilos.travessao}>—</span>
          Desafio Elite Dev Verzel
        </p>
      </div>
    </footer>
  );
}

/* Os quatro símbolos são SVG inline, sem biblioteca e sem arquivo: quatro
   caminhos custam menos que uma dependência, e `currentColor` faz todos
   herdarem a cor da linha em qualquer um dos dois temas. Mesmo molde do
   `SeletorDeTema` e do `Veredito`. `viewBox` de 24 nos quatro, para eles
   ocuparem a mesma caixa óptica. */

function IconeInstagram() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconeX() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.5 3h3.1l-6.8 7.8L21.8 21h-6.2l-4.9-6.4L5.1 21H2l7.3-8.3L2.4 3h6.4l4.4 5.8L17.5 3Zm-1.1 16.1h1.7L7.7 4.8H5.9l10.5 14.3Z" />
    </svg>
  );
}

function IconeYouTube() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8ZM10 15.1V8.9l5.2 3.1L10 15.1Z" />
    </svg>
  );
}

function IconeSpotify() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="12" r="9.2" />
      <path
        d="M7.4 9.1c3-.8 6.3-.5 9.1 1M8 12.4c2.4-.6 5-.4 7.3.9M8.6 15.5c1.9-.5 3.9-.3 5.7.7"
        strokeLinecap="round"
      />
    </svg>
  );
}
