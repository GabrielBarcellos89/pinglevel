from __future__ import annotations

import re
import secrets
import sqlite3
import string
import time

from autenticacao import BANCO, _hash_senha


def _conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    return conexao


def _registrar(conexao, administrador_id, acao, alvo_id=None, detalhes=""):
    conexao.execute(
        """
        INSERT INTO auditoria_admin
            (administrador_id, acao, alvo_usuario_id, detalhes, criado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        (administrador_id, acao, alvo_id, detalhes[:500], int(time.time())),
    )


def _senha_temporaria():
    alfabeto = string.ascii_letters + string.digits
    return "Pl!" + "".join(secrets.choice(alfabeto) for _ in range(9))


def inicializar_banco():
    with _conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS auditoria_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                administrador_id INTEGER NOT NULL,
                acao TEXT NOT NULL,
                alvo_usuario_id INTEGER,
                detalhes TEXT NOT NULL DEFAULT '',
                criado_em INTEGER NOT NULL,
                FOREIGN KEY (administrador_id) REFERENCES usuarios(id),
                FOREIGN KEY (alvo_usuario_id) REFERENCES usuarios(id)
            );

            CREATE INDEX IF NOT EXISTS idx_auditoria_admin_criado
            ON auditoria_admin(criado_em DESC);
            """
        )


def criar_administrador_inicial(login, nome, senha):
    login = str(login or "").strip().lower()
    nome = str(nome or "").strip()
    if not re.fullmatch(r"[a-z0-9._-]{4,32}", login):
        raise ValueError("Login administrativo inválido.")
    if len(nome) < 3 or len(nome) > 80:
        raise ValueError("Nome administrativo inválido.")
    if len(senha) < 10:
        raise ValueError("A senha administrativa deve ter ao menos 10 caracteres.")
    salt, senha_hash = _hash_senha(senha)
    agora = int(time.time())
    with _conectar() as conexao:
        existente = conexao.execute(
            "SELECT id, administrador FROM usuarios WHERE login = ?", (login,)
        ).fetchone()
        if existente:
            if not existente["administrador"]:
                raise ValueError("O login já pertence a uma conta não administrativa.")
            return existente["id"], False
        cursor = conexao.execute(
            """
            INSERT INTO usuarios
                (login, nome, papel, senha_salt, senha_hash, ativo, criado_em, administrador)
            VALUES (?, ?, 'professor', ?, ?, 1, ?, 1)
            """,
            (login, nome, salt, senha_hash, agora),
        )
        return cursor.lastrowid, True


def obter_painel():
    with _conectar() as conexao:
        usuarios = [dict(linha) for linha in conexao.execute(
            """
            SELECT u.id, u.login, u.nome,
                   CASE WHEN u.administrador = 1 THEN 'administrador' ELSE u.papel END AS papel,
                   u.ativo, u.criado_em, u.expira_em,
                   t.id AS turma_id, t.nome AS turma_nome
            FROM usuarios u
            LEFT JOIN turma_usuarios tu ON tu.usuario_id = u.id
            LEFT JOIN turmas t ON t.id = tu.turma_id
            ORDER BY u.administrador DESC, u.papel DESC, u.nome COLLATE NOCASE
            """
        )]
        for usuario in usuarios:
            usuario["ativo"] = bool(usuario["ativo"])
        turmas = [dict(linha) for linha in conexao.execute(
            """
            SELECT t.id, t.nome, t.codigo, t.ativo, u.nome AS professor_nome,
                   COUNT(tu.usuario_id) AS total_alunos
            FROM turmas t
            JOIN usuarios u ON u.id = t.professor_id
            LEFT JOIN turma_usuarios tu ON tu.turma_id = t.id
            GROUP BY t.id
            ORDER BY t.nome COLLATE NOCASE
            """
        )]
        auditoria = [dict(linha) for linha in conexao.execute(
            """
            SELECT a.acao, a.detalhes, a.criado_em, u.nome AS administrador_nome,
                   alvo.nome AS alvo_nome
            FROM auditoria_admin a
            JOIN usuarios u ON u.id = a.administrador_id
            LEFT JOIN usuarios alvo ON alvo.id = a.alvo_usuario_id
            ORDER BY a.id DESC LIMIT 20
            """
        )]
    return {"usuarios": usuarios, "turmas": turmas, "auditoria": auditoria}


def _validade(valor):
    """Validade de uma conta: None (sem limite) ou um instante em segundos (o navegador converte a data e hora locais)."""
    if valor in (None, ""):
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError("Informe a data de validade ou escolha sem limite.")
    valor = int(valor)
    if not 1_577_836_800 <= valor <= 4_102_444_800:  # 2020 a 2100
        raise ValueError("Data de validade fora do intervalo aceito.")
    return valor


def definir_validade(administrador_id, usuario_id, expira_em, turma_inteira=False):
    """Impõe, estende ou reduz a validade (ou tira o limite). Com turma_inteira, vale para todos os alunos da turma
    do aluno escolhido. Administradores nunca expiram, para ninguém perder o acesso à administração."""
    expira_em = _validade(expira_em)
    with _conectar() as conexao:
        alvo = conexao.execute(
            "SELECT u.id, u.papel, u.administrador, tu.turma_id FROM usuarios u "
            "LEFT JOIN turma_usuarios tu ON tu.usuario_id = u.id WHERE u.id = ?",
            (int(usuario_id),),
        ).fetchone()
        if not alvo:
            raise ValueError("Usuário não encontrado.")
        if alvo["administrador"]:
            raise ValueError("A conta de administrador não tem validade.")
        if turma_inteira:
            if alvo["papel"] != "aluno" or not alvo["turma_id"]:
                raise ValueError("Só dá para aplicar à turma a partir de um aluno matriculado.")
            ids = [linha[0] for linha in conexao.execute(
                "SELECT u.id FROM usuarios u JOIN turma_usuarios tu ON tu.usuario_id = u.id "
                "WHERE tu.turma_id = ? AND u.papel = 'aluno' AND u.administrador = 0",
                (alvo["turma_id"],),
            )]
        else:
            ids = [alvo["id"]]
        conexao.executemany("UPDATE usuarios SET expira_em = ? WHERE id = ?", [(expira_em, i) for i in ids])
        detalhes = ("sem limite" if expira_em is None else f"até {expira_em}") + (f" · turma {alvo['turma_id']}, {len(ids)} contas" if turma_inteira else "")
        _registrar(conexao, administrador_id, "validade_alterada", alvo["id"], detalhes)
    return len(ids)


def criar_usuario(administrador_id, login, nome, papel, turma_id=None, expira_em=None):
    login = str(login or "").strip().lower()
    nome = str(nome or "").strip()
    papel = str(papel or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", login):
        raise ValueError("Use de 3 a 32 caracteres: letras minúsculas, números, ponto, hífen ou sublinhado.")
    if len(nome) < 2 or len(nome) > 80:
        raise ValueError("Informe um nome entre 2 e 80 caracteres.")
    if papel not in {"aluno", "professor"}:
        raise ValueError("O perfil deve ser aluno ou professor.")
    if papel == "aluno":
        try:
            turma_id = int(turma_id)
        except (TypeError, ValueError) as erro:
            raise ValueError("Selecione uma turma para criar o aluno.") from erro
    else:
        turma_id = None
    expira_em = _validade(expira_em)
    senha = _senha_temporaria()
    salt, senha_hash = _hash_senha(senha)
    agora = int(time.time())
    try:
        with _conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO usuarios
                    (
                        login,
                        nome,
                        papel,
                        senha_salt,
                        senha_hash,
                        ativo,
                        criado_em,
                        administrador,
                        troca_senha_obrigatoria,
                        expira_em
                    )
                VALUES (?, ?, ?, ?, ?, 1, ?, 0, 1, ?)
                """,
                (login, nome, papel, salt, senha_hash, agora, expira_em),
            )
            if papel == "aluno":
                turma = conexao.execute(
                    "SELECT id FROM turmas WHERE id = ? AND ativo = 1",
                    (turma_id,),
                ).fetchone()
                if not turma:
                    raise ValueError("A turma selecionada não existe ou está desativada.")
                conexao.execute(
                    """
                    INSERT INTO turma_usuarios
                        (turma_id, usuario_id, matriculado_em)
                    VALUES (?, ?, ?)
                    """,
                    (turma_id, cursor.lastrowid, agora),
                )
            _registrar(conexao, administrador_id, "usuario_criado", cursor.lastrowid, papel)
            return {"id": cursor.lastrowid, "login": login, "nome": nome,
                    "papel": papel, "turma_id": turma_id, "expira_em": expira_em,
                    "senha_temporaria": senha}
    except sqlite3.IntegrityError as erro:
        raise ValueError("Este login já está em uso.") from erro


def atualizar_usuario(administrador_id, usuario_id, nome, ativo):
    usuario_id = int(usuario_id)
    nome = str(nome or "").strip()
    if len(nome) < 2 or len(nome) > 80:
        raise ValueError("Informe um nome válido.")
    if usuario_id == int(administrador_id) and not ativo:
        raise ValueError("Você não pode desativar sua própria conta.")
    with _conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE usuarios SET nome = ?, ativo = ? WHERE id = ?",
            (nome, 1 if ativo else 0, usuario_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Usuário não encontrado.")
        if not ativo:
            conexao.execute("DELETE FROM sessoes_auth WHERE usuario_id = ?", (usuario_id,))
        _registrar(conexao, administrador_id, "usuario_atualizado", usuario_id,
                   f"ativo={bool(ativo)}")


def redefinir_senha(administrador_id, usuario_id):
    usuario_id = int(usuario_id)
    senha = _senha_temporaria()
    salt, senha_hash = _hash_senha(senha)
    with _conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE usuarios
            SET senha_salt = ?,
                senha_hash = ?,
                troca_senha_obrigatoria = 1
            WHERE id = ?
            """,
            (salt, senha_hash, usuario_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Usuário não encontrado.")
        conexao.execute("DELETE FROM sessoes_auth WHERE usuario_id = ?", (usuario_id,))
        _registrar(conexao, administrador_id, "senha_redefinida", usuario_id)
    return senha


def vincular_aluno(administrador_id, usuario_id, turma_id):
    usuario_id = int(usuario_id)
    turma_id = int(turma_id) if turma_id not in (None, "", 0, "0") else None
    with _conectar() as conexao:
        aluno = conexao.execute(
            "SELECT id FROM usuarios WHERE id = ? AND papel = 'aluno' AND administrador = 0",
            (usuario_id,),
        ).fetchone()
        if not aluno:
            raise ValueError("Aluno não encontrado.")
        conexao.execute("DELETE FROM turma_usuarios WHERE usuario_id = ?", (usuario_id,))
        if turma_id is not None:
            turma = conexao.execute("SELECT id FROM turmas WHERE id = ?", (turma_id,)).fetchone()
            if not turma:
                raise ValueError("Turma não encontrada.")
            conexao.execute(
                "INSERT INTO turma_usuarios (turma_id, usuario_id, matriculado_em) VALUES (?, ?, ?)",
                (turma_id, usuario_id, int(time.time())),
            )
        _registrar(conexao, administrador_id, "aluno_vinculado", usuario_id,
                   f"turma_id={turma_id}")


inicializar_banco()
