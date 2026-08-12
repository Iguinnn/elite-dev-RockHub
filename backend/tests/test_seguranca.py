"""Hash Argon2id e token de sessão — nenhuma conexão de banco aqui."""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.seguranca import (
    EXPIRACAO_SESSAO,
    conferir_senha,
    criar_token_sessao,
    gerar_hash,
    ler_token_sessao,
)
from app.core.config import obter_settings
from app.models.usuario import PapelUsuario, Usuario


def test_gerar_hash_produz_string_argon2id() -> None:
    assert gerar_hash("rockhub").startswith("$argon2id$")


def test_mesma_senha_hasheada_duas_vezes_da_valores_diferentes() -> None:
    assert gerar_hash("rockhub") != gerar_hash("rockhub")


def test_conferir_senha_aceita_a_certa_e_recusa_a_errada() -> None:
    hash_gravado = gerar_hash("rockhub")

    assert conferir_senha(hash_gravado, "rockhub") is True
    assert conferir_senha(hash_gravado, "outra-senha") is False


def test_conferir_senha_com_hash_corrompido_devolve_false_sem_levantar() -> None:
    assert conferir_senha("isto-nao-e-um-hash-argon2id", "rockhub") is False


def _usuario_teste() -> Usuario:
    return Usuario(
        nome="Igor Teste",
        email="igor@exemplo.com",
        senha_hash="não importa aqui",
        papel=PapelUsuario.CLIENTE.value,
    )


def test_token_criado_e_lido_de_volta_traz_sub_e_papel_e_expira_em_8h() -> None:
    usuario = _usuario_teste()

    token = criar_token_sessao(usuario)
    carga = ler_token_sessao(token)

    assert carga is not None
    assert carga["sub"] == str(usuario.id)
    assert carga["papel"] == PapelUsuario.CLIENTE.value
    assert carga["exp"] - carga["iat"] == int(EXPIRACAO_SESSAO.total_seconds())


def test_token_com_assinatura_alterada_e_recusado() -> None:
    """⚠️ **A adulteração é no PRIMEIRO caractere da assinatura, nunca no último.**

    Trocar o último era o que este teste fazia, e o tornava intermitente (code
    review da Epic 3). A assinatura HS256 tem 32 bytes, que em base64url sem
    padding dão 43 caracteres: 258 bits para 256 de dado. Os **2 bits sobrando
    ficam no último caractere**, então `A`, `B`, `C` e `D` decodificam para os
    mesmos bytes — e a troca por `"A"` era invisível sempre que o token terminava
    em `B`, `C` ou `D`. Nesses ~4,7% dos casos a assinatura continuava válida, o
    token era aceito, e o teste falhava dizendo que o sistema aceita token
    adulterado. O contrário — um teste verde afirmando que a recusa funciona
    quando o byte nem mudou — é o que aconteceria se a asserção fosse `is not
    None`.

    O primeiro caractere carrega 6 bits significativos: trocá-lo muda o byte
    sempre.
    """
    token = criar_token_sessao(_usuario_teste())
    cabecalho, payload, assinatura = token.rsplit(".", 2)
    adulterada = ("A" if assinatura[0] != "A" else "B") + assinatura[1:]

    assert ler_token_sessao(f"{cabecalho}.{payload}.{adulterada}") is None


def test_token_assinado_com_outro_segredo_e_recusado() -> None:
    usuario = _usuario_teste()
    agora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "papel": usuario.papel,
            "iat": int(agora.timestamp()),
            "exp": int((agora + EXPIRACAO_SESSAO).timestamp()),
        },
        "outro-segredo-qualquer",
        algorithm="HS256",
    )

    assert ler_token_sessao(token) is None


def test_token_com_exp_no_passado_e_recusado() -> None:
    usuario = _usuario_teste()
    agora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "papel": usuario.papel,
            "iat": int((agora - timedelta(hours=9)).timestamp()),
            "exp": int((agora - timedelta(hours=1)).timestamp()),
        },
        obter_settings().jwt_secret,
        algorithm="HS256",
    )

    assert ler_token_sessao(token) is None
