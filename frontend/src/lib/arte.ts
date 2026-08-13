/**
 * A arte de reserva do evento sem foto — o disco do RockHub (13/08/2026).
 *
 * **Ela é do frontend, e o banco não sabe que ela existe.** `evento.imagem_url`
 * continua nulo quando o catálogo não trouxe arte; o que muda é só o que a tela
 * desenha nesse caso. É a mesma natureza do `logotipo-rockhub.png` ao lado dela
 * no `public/`, e é o que faz a arte sumir sozinha no dia em que o evento
 * ganhar foto de verdade — sem migração, sem varrer linha nenhuma.
 *
 * A alternativa descartada foi gravar este caminho em `imagem_url` na
 * publicação. Custaria o mesmo hoje e cobraria caro depois: o banco passaria a
 * guardar um caminho de arquivo do frontend, "sem arte" viraria indistinguível
 * de "arte escolhida", e trocar o desenho um dia exigiria um `UPDATE` em todo
 * evento publicado — em vez de trocar um arquivo.
 *
 * **São dois arquivos porque são duas proporções**, e não por capricho de
 * exportação. Os quadros grandes são 16/10 (`DESIGN.md`, e a decisão de manter
 * a mesma proporção na página do evento); as miniaturas do organizador são
 * quadradas de 70px. A arte 16/10 espremida em 70×70 com `object-fit: cover`
 * perderia as laterais e viraria borrão; a quadrada esticada na capa perderia o
 * topo e o pé do disco.
 *
 * ⚠️ **JPG, não PNG.** O original entregue era um PNG de 2,8 MB — PNG guarda
 * imagem fotográfica sem compressão com perda, e este arquivo aparece na tela
 * mais visitada do produto. Convertidos, os dois somam 302 KB.
 */

/** 1600×1000. Capa da raiz e página do evento. */
export const ARTE_DE_RESERVA = "/disco-rockhub.jpg";

/** 400×400. Miniaturas de 70px do catálogo e do passo 2 da publicação. */
export const ARTE_DE_RESERVA_QUADRADA = "/disco-rockhub-quadrado.jpg";
