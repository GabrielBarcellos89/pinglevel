from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import string
import time
from pathlib import Path

from autenticacao import BANCO, ITERACOES


def _conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    return conexao


def _hash_senha(senha: str):
    salt = secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, ITERACOES
    )
    return salt.hex(), derivada.hex()


def _senha_temporaria() -> str:
    """Senha provisória aleatória (23/11/2026): antes era uma senha fixa, e com o código público qualquer um saberia
    a senha de uma conta recém-criada ou redefinida. O aluno é obrigado a trocá-la no primeiro acesso."""
    alfabeto = string.ascii_letters + string.digits
    return "Pl!" + "".join(secrets.choice(alfabeto) for _ in range(9))


def _codigo_base(nome: str) -> str:
    codigo = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return codigo[:24] or "turma"


def inicializar_banco():
    with _conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS turmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                professor_id INTEGER NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em INTEGER NOT NULL,
                FOREIGN KEY (professor_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS turma_usuarios (
                turma_id INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL UNIQUE,
                matriculado_em INTEGER NOT NULL,
                PRIMARY KEY (turma_id, usuario_id),
                FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_turmas_professor
            ON turmas(professor_id);
        """)

        professor = conexao.execute(
            "SELECT id FROM usuarios WHERE papel = 'professor' ORDER BY id LIMIT 1"
        ).fetchone()
        alunos_sem_turma = conexao.execute("""
            SELECT id FROM usuarios
            WHERE papel = 'aluno'
              AND id NOT IN (SELECT usuario_id FROM turma_usuarios)
            ORDER BY id
        """).fetchall()
        if professor and alunos_sem_turma:
            agora = int(time.time())
            conexao.execute("""
                INSERT OR IGNORE INTO turmas
                    (nome, codigo, professor_id, ativo, criado_em)
                VALUES ('Turma de demonstração', 'demonstracao', ?, 1, ?)
            """, (professor["id"], agora))
            turma = conexao.execute(
                "SELECT id FROM turmas WHERE codigo = 'demonstracao'"
            ).fetchone()
            for aluno in alunos_sem_turma:
                conexao.execute("""
                    INSERT OR IGNORE INTO turma_usuarios
                        (turma_id, usuario_id, matriculado_em)
                    VALUES (?, ?, ?)
                """, (turma["id"], aluno["id"], agora))


def listar_turmas(professor_id: int) -> list[dict]:
    with _conectar() as conexao:
        turmas = [dict(linha) for linha in conexao.execute("""
            SELECT t.id, t.nome, t.codigo, t.ativo, t.criado_em,
                   COUNT(tu.usuario_id) AS total_alunos
            FROM turmas t
            LEFT JOIN turma_usuarios tu ON tu.turma_id = t.id
            WHERE t.professor_id = ?
            GROUP BY t.id
            ORDER BY t.ativo DESC, t.nome
        """, (professor_id,))]
        for turma in turmas:
            turma["ativo"] = bool(turma["ativo"])
            turma["alunos"] = [dict(linha) for linha in conexao.execute("""
                SELECT u.id AS usuario_id, u.login, u.nome, u.ativo,
                       COALESCE((SELECT SUM(e.pontos) FROM eventos_xp e
                                 WHERE e.usuario_id = u.id), 0) AS xp_total,
                       COUNT(DISTINCT CASE WHEN p.concluida = 1 THEN p.aula_id END)
                           AS aulas_concluidas,
                       COALESCE((
                           SELECT COUNT(*)
                           FROM progresso_laboratorios pl
                           WHERE pl.usuario_id = u.id AND pl.concluido = 1
                       ), 0) AS laboratorios_concluidos,
                       MAX(p.percentual) AS percentual,
                       MAX(
                           COALESCE(p.atualizado_em, 0),
                           COALESCE((
                               SELECT MAX(pl.atualizado_em)
                               FROM progresso_laboratorios pl
                               WHERE pl.usuario_id = u.id
                           ), 0)
                       ) AS ultima_atividade
                FROM turma_usuarios tu
                JOIN usuarios u ON u.id = tu.usuario_id
                LEFT JOIN progresso_aulas p ON p.usuario_id = u.id
                WHERE tu.turma_id = ?
                GROUP BY u.id
                ORDER BY u.nome COLLATE NOCASE
            """, (turma["id"],))]
            for aluno in turma["alunos"]:
                aluno["ativo"] = bool(aluno["ativo"])
                aluno["percentual"] = int(aluno["percentual"] or 0)
    return turmas


def criar_turma(professor_id: int, nome: str, quantidade: int) -> dict:
    nome = str(nome or "").strip()
    quantidade = int(quantidade)
    if len(nome) < 3 or len(nome) > 80:
        raise ValueError("Informe um nome de turma entre 3 e 80 caracteres.")
    if quantidade < 1 or quantidade > 40:
        raise ValueError("A turma deve ter entre 1 e 40 alunos.")

    agora = int(time.time())
    credenciais = []
    with _conectar() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        base = _codigo_base(nome)
        codigo = base
        sequencia = 2
        while conexao.execute(
            "SELECT 1 FROM turmas WHERE codigo = ?", (codigo,)
        ).fetchone():
            codigo = f"{base}-{sequencia}"
            sequencia += 1
        cursor = conexao.execute("""
            INSERT INTO turmas (nome, codigo, professor_id, ativo, criado_em)
            VALUES (?, ?, ?, 1, ?)
        """, (nome, codigo, professor_id, agora))
        turma_id = cursor.lastrowid

        proximo = 1
        for numero in range(1, quantidade + 1):
            while conexao.execute(
                "SELECT 1 FROM usuarios WHERE login = ?", (f"aluno{proximo}",)
            ).fetchone():
                proximo += 1
            login = f"aluno{proximo}"
            nome_aluno = f"Aluno {numero}"
            senha_inicial = _senha_temporaria()
            salt, senha_hash = _hash_senha(senha_inicial)
            usuario = conexao.execute("""
                INSERT INTO usuarios
                    (
                        login,
                        nome,
                        papel,
                        senha_salt,
                        senha_hash,
                        ativo,
                        criado_em,
                        troca_senha_obrigatoria
                    )
                VALUES (?, ?, 'aluno', ?, ?, 1, ?, 1)
            """, (login, nome_aluno, salt, senha_hash, agora))
            conexao.execute("""
                INSERT INTO turma_usuarios (turma_id, usuario_id, matriculado_em)
                VALUES (?, ?, ?)
            """, (turma_id, usuario.lastrowid, agora))
            credenciais.append({
                "usuario_id": usuario.lastrowid,
                "nome": nome_aluno,
                "login": login,
                "senha_temporaria": senha_inicial,
            })
            proximo += 1

    return {
        "id": turma_id, "nome": nome, "codigo": codigo,
        "credenciais": credenciais,
    }


def atualizar_aluno(professor_id: int, usuario_id: int, nome: str, ativo: bool):
    nome = str(nome or "").strip()
    if len(nome) < 2 or len(nome) > 80:
        raise ValueError("Informe um nome válido para o aluno.")
    with _conectar() as conexao:
        cursor = conexao.execute("""
            UPDATE usuarios SET nome = ?, ativo = ?
            WHERE id = ? AND papel = 'aluno' AND EXISTS (
                SELECT 1 FROM turma_usuarios tu JOIN turmas t ON t.id = tu.turma_id
                WHERE tu.usuario_id = usuarios.id AND t.professor_id = ?
            )
        """, (nome, 1 if ativo else 0, int(usuario_id), professor_id))
        if cursor.rowcount != 1:
            raise ValueError("Aluno não encontrado nesta turma.")


def redefinir_senha(professor_id: int, usuario_id: int) -> str:
    senha = _senha_temporaria()
    salt, senha_hash = _hash_senha(senha)
    with _conectar() as conexao:
        cursor = conexao.execute("""
            UPDATE usuarios
            SET senha_salt = ?,
                senha_hash = ?,
                troca_senha_obrigatoria = 1
            WHERE id = ? AND papel = 'aluno' AND EXISTS (
                SELECT 1 FROM turma_usuarios tu JOIN turmas t ON t.id = tu.turma_id
                WHERE tu.usuario_id = usuarios.id AND t.professor_id = ?
            )
        """, (salt, senha_hash, int(usuario_id), professor_id))
        if cursor.rowcount != 1:
            raise ValueError("Aluno não encontrado nesta turma.")
        conexao.execute("DELETE FROM sessoes_auth WHERE usuario_id = ?", (usuario_id,))
    return senha


inicializar_banco()
