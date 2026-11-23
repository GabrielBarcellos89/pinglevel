from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from pathlib import Path


BANCO = Path(os.environ.get(
    "PINGLEVEL_AUTH_DB",
    "/opt/packetlab/data/auth/pinglevel_auth.db",
))
DURACAO_SESSAO = int(os.environ.get("PINGLEVEL_AUTH_SESSION_SECONDS", "28800"))
COOKIE_SEGURO = os.environ.get("PINGLEVEL_COOKIE_SECURE", "0") == "1"
NOME_COOKIE = "pinglevel_session"
ITERACOES = 310_000


USUARIOS_INICIAIS = [
    ("user1", "João", "aluno"),
    ("user2", "Maria", "aluno"),
    ("user3", "Pedro", "aluno"),
    ("user4", "Ana", "aluno"),
    ("user5", "Lucas", "aluno"),
    ("user6", "Juliana", "aluno"),
    ("user7", "Rafael", "aluno"),
    ("user8", "Camila", "aluno"),
    ("user9", "Bruno", "aluno"),
    ("user10", "Larissa", "aluno"),
    ("professor", "Professor Gabriel", "professor"),
]


def _conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    return conexao


def _hash_senha(senha, salt=None):
    salt = salt or secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, ITERACOES
    )
    return salt.hex(), derivada.hex()


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def inicializar_banco():
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with _conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL UNIQUE COLLATE NOCASE,
                nome TEXT NOT NULL,
                papel TEXT NOT NULL CHECK (papel IN ('aluno', 'professor')),
                senha_salt TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessoes_auth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                criado_em INTEGER NOT NULL,
                expira_em INTEGER NOT NULL,
                ultimo_acesso INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessoes_auth_expira
            ON sessoes_auth(expira_em);
        """)

        colunas = {
            linha["name"]
            for linha in conexao.execute("PRAGMA table_info(usuarios)")
        }
        if "administrador" not in colunas:
            conexao.execute(
                "ALTER TABLE usuarios ADD COLUMN administrador INTEGER NOT NULL DEFAULT 0"
            )

        # Validade da conta (contas temporárias, como as da apresentação): NULL = sem validade.
        if "expira_em" not in colunas:
            conexao.execute("ALTER TABLE usuarios ADD COLUMN expira_em INTEGER")

        if "troca_senha_obrigatoria" not in colunas:
            conexao.execute(
                """
                ALTER TABLE usuarios
                ADD COLUMN troca_senha_obrigatoria INTEGER NOT NULL DEFAULT 0
                """
            )

        # Contas iniciais só num banco novo: contas removidas depois (como na limpeza para a apresentação de
        # 18/11/2026) não podem voltar com a senha padrão a cada reinício.
        if conexao.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            return
        agora = int(time.time())
        for login, nome, papel in USUARIOS_INICIAIS:
            salt, senha_hash = _hash_senha("Senac")
            conexao.execute(
                """
                INSERT OR IGNORE INTO usuarios
                    (login, nome, papel, senha_salt, senha_hash, ativo, criado_em)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (login, nome, papel, salt, senha_hash, agora),
            )


def autenticar(login, senha):
    login = str(login or "").strip().lower()
    senha = str(senha or "")
    if not login or not senha:
        return None

    with _conectar() as conexao:
        usuario = conexao.execute(
            """
            SELECT * FROM usuarios
            WHERE login = ? AND ativo = 1 AND (expira_em IS NULL OR expira_em > ?)
            """,
            (login, int(time.time())),
        ).fetchone()
        if not usuario:
            return None

        _, calculado = _hash_senha(senha, bytes.fromhex(usuario["senha_salt"]))
        if not hmac.compare_digest(calculado, usuario["senha_hash"]):
            return None

        agora = int(time.time())
        conexao.execute("DELETE FROM sessoes_auth WHERE expira_em <= ?", (agora,))
        token = secrets.token_urlsafe(32)
        conexao.execute(
            """
            INSERT INTO sessoes_auth
                (usuario_id, token_hash, criado_em, expira_em, ultimo_acesso)
            VALUES (?, ?, ?, ?, ?)
            """,
            (usuario["id"], _hash_token(token), agora, agora + DURACAO_SESSAO, agora),
        )
        return token, _usuario_publico(usuario)


def _usuario_publico(usuario):
    return {
        "id": usuario["id"],
        "login": usuario["login"],
        "nome": usuario["nome"],
        "papel": (
            "administrador"
            if "administrador" in usuario.keys() and usuario["administrador"]
            else usuario["papel"]
        ),
        "troca_senha_obrigatoria": bool(
            usuario["troca_senha_obrigatoria"]
            if "troca_senha_obrigatoria" in usuario.keys()
            else 0
        ),
    }


def _validar_nova_senha(nova_senha, confirmacao):
    nova_senha = str(nova_senha or "")
    confirmacao = str(confirmacao or "")

    if nova_senha != confirmacao:
        raise ValueError("A confirmação não corresponde à nova senha.")
    if len(nova_senha) < 10:
        raise ValueError("A nova senha deve ter pelo menos 10 caracteres.")
    if len(nova_senha) > 128:
        raise ValueError("A nova senha deve ter no máximo 128 caracteres.")
    if not any(caractere.islower() for caractere in nova_senha):
        raise ValueError("Inclua pelo menos uma letra minúscula.")
    if not any(caractere.isupper() for caractere in nova_senha):
        raise ValueError("Inclua pelo menos uma letra maiúscula.")
    if not any(caractere.isdigit() for caractere in nova_senha):
        raise ValueError("Inclua pelo menos um número.")
    if not any(not caractere.isalnum() for caractere in nova_senha):
        raise ValueError("Inclua pelo menos um caractere especial.")

    return nova_senha


def alterar_senha(usuario_id, senha_atual, nova_senha, confirmacao):
    senha_atual = str(senha_atual or "")
    nova_senha = _validar_nova_senha(nova_senha, confirmacao)

    if not senha_atual:
        raise ValueError("Informe a senha atual.")
    if hmac.compare_digest(senha_atual, nova_senha):
        raise ValueError("A nova senha deve ser diferente da senha atual.")

    with _conectar() as conexao:
        conexao.execute("BEGIN IMMEDIATE")

        usuario = conexao.execute(
            """
            SELECT id, senha_salt, senha_hash
            FROM usuarios
            WHERE id = ? AND ativo = 1
            """,
            (int(usuario_id),),
        ).fetchone()

        if not usuario:
            raise ValueError("Usuário não encontrado ou conta inativa.")

        _, hash_atual = _hash_senha(
            senha_atual,
            bytes.fromhex(usuario["senha_salt"]),
        )

        if not hmac.compare_digest(hash_atual, usuario["senha_hash"]):
            raise ValueError("A senha atual está incorreta.")

        novo_salt, novo_hash = _hash_senha(nova_senha)

        conexao.execute(
            """
            UPDATE usuarios
            SET senha_salt = ?,
                senha_hash = ?,
                troca_senha_obrigatoria = 0
            WHERE id = ?
            """,
            (novo_salt, novo_hash, usuario["id"]),
        )

        conexao.execute(
            "DELETE FROM sessoes_auth WHERE usuario_id = ?",
            (usuario["id"],),
        )


def token_do_cookie(cabecalho_cookie):
    if not cabecalho_cookie:
        return None
    try:
        cookies = SimpleCookie()
        cookies.load(cabecalho_cookie)
        item = cookies.get(NOME_COOKIE)
        return item.value if item else None
    except Exception:
        return None


def obter_usuario(token):
    if not token:
        return None
    agora = int(time.time())
    with _conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT u.*
            FROM sessoes_auth s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token_hash = ? AND s.expira_em > ? AND u.ativo = 1
              AND (u.expira_em IS NULL OR u.expira_em > ?)
            """,
            (_hash_token(token), agora, agora),
        ).fetchone()
        if not linha:
            return None
        conexao.execute(
            "UPDATE sessoes_auth SET ultimo_acesso = ? WHERE token_hash = ?",
            (agora, _hash_token(token)),
        )
        return _usuario_publico(linha)


def encerrar_sessao(token):
    if not token:
        return
    with _conectar() as conexao:
        conexao.execute(
            "DELETE FROM sessoes_auth WHERE token_hash = ?", (_hash_token(token),)
        )


def cookie_login(token):
    partes = [
        f"{NOME_COOKIE}={token}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        f"Max-Age={DURACAO_SESSAO}",
    ]
    if COOKIE_SEGURO:
        partes.append("Secure")
    return "; ".join(partes)


def cookie_logout():
    partes = [
        f"{NOME_COOKIE}=",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        "Max-Age=0",
    ]
    if COOKIE_SEGURO:
        partes.append("Secure")
    return "; ".join(partes)


inicializar_banco()
