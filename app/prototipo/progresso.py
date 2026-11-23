from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


BANCO = Path(os.environ.get(
    "PINGLEVEL_AUTH_DB",
    "/opt/packetlab/data/auth/pinglevel_auth.db",
))

AULAS = {
    "fundamentos-modelos-osi-tcpip": {
        "modulo_id": "fundamentos",
        "titulo": "Modelos OSI e TCP/IP",
        "total_etapas": 6,
        "xp": 100,
    },
    "fundamentos-aula-1": {
        "modulo_id": "fundamentos",
        "titulo": "O que é uma rede?",
        "total_etapas": 7,
        "xp": 100,
    },
    "fundamentos-gateway": {
        "modulo_id": "fundamentos",
        "titulo": "Gateway e entrega local",
        "total_etapas": 6,
        "xp": 100,
    },
    "fundamentos-ferramentas": {
        "modulo_id": "fundamentos",
        "titulo": "Ferramentas: interfaces, rotas e testes",
        "total_etapas": 6,
        "xp": 100,
    },
    "planejamento-enderecamento": {
        "modulo_id": "planejamento",
        "titulo": "Plano de endereçamento e sub-redes",
        "total_etapas": 6,
        "xp": 100,
    },
    "planejamento-vlsm": {
        "modulo_id": "planejamento",
        "titulo": "VLSM",
        "total_etapas": 6,
        "xp": 100,
    },
    "planejamento-roteamento": {
        "modulo_id": "planejamento",
        "titulo": "Roteamento estático",
        "total_etapas": 7,
        "xp": 100,
    },
    "servicos-dhcp-dns": {
        "modulo_id": "servicos",
        "titulo": "DHCP e DNS",
        "total_etapas": 6,
        "xp": 100,
    },
    "servicos-lan": {
        "modulo_id": "servicos",
        "titulo": "Switch e VLANs",
        "total_etapas": 5,
        "xp": 100,
    },
    "servicos-transporte": {
        "modulo_id": "servicos",
        "titulo": "Transporte: portas, TCP e UDP",
        "total_etapas": 5,
        "xp": 100,
    },
    "fundamentos-ethernet-arp": {
        "modulo_id": "fundamentos",
        "titulo": "Ethernet, MAC e ARP",
        "total_etapas": 4,
        "xp": 100,
    },
    "enderecamento-ipv4": {
        "modulo_id": "enderecamento",
        "titulo": "Endereçamento IPv4",
        "total_etapas": 6,
        "xp": 100,
    },
}

LABORATORIOS = {
    "saindo-da-rede-local": {"titulo": "Saindo da rede local", "xp": 100},
    "configure-pelo-terminal": {"titulo": "Configure pelo terminal", "xp": 100},
    "dividindo-uma-rede": {"titulo": "Dividindo uma rede", "xp": 100},
    "planejando-uma-empresa": {"titulo": "Planejando uma empresa", "xp": 100},
    "conectando-redes": {"titulo": "Conectando redes", "xp": 100},
    "investigando-a-lan": {"titulo": "Investigando e separando a LAN", "xp": 100},
    "enderecos-e-nomes": {"titulo": "Endereços e nomes automáticos", "xp": 100},
    "desafio-rede-da-empresa": {"titulo": "Desafio final: a rede da empresa", "xp": 150},
    "primeira-lan": {"titulo": "Monte sua primeira LAN", "xp": 100},
    "primeiro-contato": {
        "titulo": "Missão: Primeiro Contato",
        "xp": 100,
    },
}


@contextmanager
def _conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    try:
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("PRAGMA journal_mode = WAL")
        with conexao:
            yield conexao
    finally:
        conexao.close()


def inicializar_banco():
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with _conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS progresso_aulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                aula_id TEXT NOT NULL,
                modulo_id TEXT NOT NULL,
                etapa_atual INTEGER NOT NULL DEFAULT 0,
                percentual INTEGER NOT NULL DEFAULT 0,
                concluida INTEGER NOT NULL DEFAULT 0,
                iniciado_em INTEGER NOT NULL,
                atualizado_em INTEGER NOT NULL,
                concluida_em INTEGER,
                UNIQUE(usuario_id, aula_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS eventos_xp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                origem_tipo TEXT NOT NULL,
                origem_id TEXT NOT NULL,
                pontos INTEGER NOT NULL CHECK(pontos >= 0),
                descricao TEXT NOT NULL,
                criado_em INTEGER NOT NULL,
                UNIQUE(usuario_id, origem_tipo, origem_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS progresso_laboratorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                laboratorio_id TEXT NOT NULL,
                concluido INTEGER NOT NULL DEFAULT 0,
                iniciado_em INTEGER NOT NULL,
                atualizado_em INTEGER NOT NULL,
                concluido_em INTEGER,
                UNIQUE(usuario_id, laboratorio_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS estado_aulas (
                usuario_id INTEGER NOT NULL,
                aula_id TEXT NOT NULL,
                versao_estado INTEGER NOT NULL,
                versao_conteudo INTEGER NOT NULL,
                etapa_visitada INTEGER NOT NULL DEFAULT 0,
                etapa_liberada INTEGER NOT NULL DEFAULT 0,
                respostas_json TEXT NOT NULL,
                validacoes_json TEXT NOT NULL,
                revisao INTEGER NOT NULL DEFAULT 0,
                atualizado_em INTEGER NOT NULL,
                PRIMARY KEY (usuario_id, aula_id),
                FOREIGN KEY (usuario_id, aula_id)
                    REFERENCES progresso_aulas(usuario_id, aula_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_progresso_usuario
            ON progresso_aulas(usuario_id);

            CREATE INDEX IF NOT EXISTS idx_eventos_xp_usuario
            ON eventos_xp(usuario_id);

            CREATE INDEX IF NOT EXISTS idx_laboratorios_usuario
            ON progresso_laboratorios(usuario_id);
        """)


def _aula(aula_id: str) -> dict:
    configuracao = AULAS.get(str(aula_id or ""))
    if not configuracao:
        raise ValueError("Aula não reconhecida.")
    return configuracao


def registrar_etapa(usuario_id: int, aula_id: str, etapa_atual: int, revisao=None) -> dict:
    if aula_id == "enderecamento-ipv4":
        from estado_aula_ipv4 import avancar
        avancar(usuario_id, aula_id, revisao, etapa_atual)
        return obter_resumo_usuario(usuario_id)
    configuracao = _aula(aula_id)
    total = configuracao["total_etapas"]
    etapa = int(etapa_atual)
    if etapa < 0 or etapa >= total:
        raise ValueError("Etapa inválida.")
    percentual = round(((etapa + 1) / total) * 100)
    agora = int(time.time())

    with _conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO progresso_aulas (
                usuario_id, aula_id, modulo_id, etapa_atual, percentual,
                concluida, iniciado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(usuario_id, aula_id) DO UPDATE SET
                etapa_atual = MAX(progresso_aulas.etapa_atual, excluded.etapa_atual),
                percentual = CASE
                    WHEN progresso_aulas.concluida = 1 THEN 100
                    ELSE MAX(progresso_aulas.percentual, excluded.percentual)
                END,
                atualizado_em = excluded.atualizado_em
            """,
            (
                usuario_id, aula_id, configuracao["modulo_id"], etapa,
                percentual, agora, agora,
            ),
        )
    return obter_resumo_usuario(usuario_id)


def concluir_aula(usuario_id: int, aula_id: str, revisao=None) -> dict:
    configuracao = _aula(aula_id)
    agora = int(time.time())
    etapa_final = configuracao["total_etapas"] - 1

    with _conectar() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        atual = conexao.execute(
            """
            SELECT etapa_atual, concluida
            FROM progresso_aulas
            WHERE usuario_id = ? AND aula_id = ?
            """,
            (usuario_id, aula_id),
        ).fetchone()
        if aula_id == "enderecamento-ipv4":
            if atual and atual["concluida"]:
                resumo = obter_resumo_usuario(usuario_id)
                resumo.update({"primeira_conclusao": False, "xp_concedido": 0})
                return resumo
            from estado_aula_ipv4 import verificar_conclusao
            verificar_conclusao(conexao, usuario_id, revisao)
        if not atual or atual["etapa_atual"] < etapa_final:
            raise ValueError("Conclua todas as etapas antes de finalizar a aula.")

        primeira_conclusao = not bool(atual["concluida"])
        conexao.execute(
            """
            UPDATE progresso_aulas
            SET etapa_atual = ?, percentual = 100, concluida = 1,
                atualizado_em = ?, concluida_em = COALESCE(concluida_em, ?)
            WHERE usuario_id = ? AND aula_id = ?
            """,
            (etapa_final, agora, agora, usuario_id, aula_id),
        )
        cursor = conexao.execute(
            """
            INSERT OR IGNORE INTO eventos_xp (
                usuario_id, origem_tipo, origem_id, pontos, descricao, criado_em
            ) VALUES (?, 'aula', ?, ?, ?, ?)
            """,
            (
                usuario_id, aula_id, configuracao["xp"],
                f"Conclusão: {configuracao['titulo']}", agora,
            ),
        )
        xp_concedido = configuracao["xp"] if cursor.rowcount == 1 else 0

    resumo = obter_resumo_usuario(usuario_id)
    resumo.update({
        "primeira_conclusao": primeira_conclusao,
        "xp_concedido": xp_concedido,
    })
    return resumo


def concluir_laboratorio(usuario_id: int, laboratorio_id: str) -> dict:
    laboratorio_id = str(laboratorio_id or "")
    configuracao = LABORATORIOS.get(laboratorio_id)
    if not configuracao:
        raise ValueError("Laboratório não reconhecido.")

    agora = int(time.time())
    with _conectar() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        atual = conexao.execute(
            """
            SELECT concluido
            FROM progresso_laboratorios
            WHERE usuario_id = ? AND laboratorio_id = ?
            """,
            (usuario_id, laboratorio_id),
        ).fetchone()
        primeira_conclusao = not atual or not bool(atual["concluido"])

        conexao.execute(
            """
            INSERT INTO progresso_laboratorios (
                usuario_id, laboratorio_id, concluido,
                iniciado_em, atualizado_em, concluido_em
            ) VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(usuario_id, laboratorio_id) DO UPDATE SET
                concluido = 1,
                atualizado_em = excluded.atualizado_em,
                concluido_em = COALESCE(
                    progresso_laboratorios.concluido_em,
                    excluded.concluido_em
                )
            """,
            (usuario_id, laboratorio_id, agora, agora, agora),
        )
        cursor = conexao.execute(
            """
            INSERT OR IGNORE INTO eventos_xp (
                usuario_id, origem_tipo, origem_id,
                pontos, descricao, criado_em
            ) VALUES (?, 'laboratorio', ?, ?, ?, ?)
            """,
            (
                usuario_id,
                laboratorio_id,
                configuracao["xp"],
                f"Conclusão: {configuracao['titulo']}",
                agora,
            ),
        )
        xp_concedido = configuracao["xp"] if cursor.rowcount == 1 else 0

    resumo = obter_resumo_usuario(usuario_id)
    resumo.update({
        "primeira_conclusao": primeira_conclusao,
        "xp_concedido": xp_concedido,
    })
    return resumo


def obter_resumo_usuario(usuario_id: int) -> dict:
    with _conectar() as conexao:
        aulas = [dict(linha) for linha in conexao.execute(
            """
            SELECT aula_id, modulo_id, etapa_atual, percentual, concluida,
                   iniciado_em, atualizado_em, concluida_em
            FROM progresso_aulas
            WHERE usuario_id = ?
            ORDER BY modulo_id, aula_id
            """,
            (usuario_id,),
        )]
        xp_total = conexao.execute(
            "SELECT COALESCE(SUM(pontos), 0) FROM eventos_xp WHERE usuario_id = ?",
            (usuario_id,),
        ).fetchone()[0]
        laboratorios = [dict(linha) for linha in conexao.execute(
            """
            SELECT laboratorio_id, concluido, iniciado_em,
                   atualizado_em, concluido_em
            FROM progresso_laboratorios
            WHERE usuario_id = ?
            ORDER BY laboratorio_id
            """,
            (usuario_id,),
        )]

    for item in aulas:
        item["concluida"] = bool(item["concluida"])
    for item in laboratorios:
        item["concluido"] = bool(item["concluido"])
    return {
        "usuario_id": usuario_id,
        "xp_total": int(xp_total),
        "aulas_concluidas": sum(1 for item in aulas if item["concluida"]),
        "laboratorios_concluidos": sum(
            1 for item in laboratorios if item["concluido"]
        ),
        "aulas": aulas,
        "laboratorios": laboratorios,
    }


def listar_progresso_turma() -> list[dict]:
    with _conectar() as conexao:
        linhas = conexao.execute("""
            SELECT
                u.id AS usuario_id,
                u.login,
                u.nome,
                COUNT(DISTINCT CASE WHEN p.concluida = 1 THEN p.aula_id END)
                    AS aulas_concluidas,
                COALESCE((
                    SELECT COUNT(*) FROM progresso_laboratorios l
                    WHERE l.usuario_id = u.id AND l.concluido = 1
                ), 0) AS laboratorios_concluidos,
                COALESCE((
                    SELECT SUM(e.pontos) FROM eventos_xp e WHERE e.usuario_id = u.id
                ), 0) AS xp_total,
                MAX(
                    COALESCE(p.atualizado_em, 0),
                    COALESCE((
                        SELECT MAX(l.atualizado_em)
                        FROM progresso_laboratorios l
                        WHERE l.usuario_id = u.id
                    ), 0)
                ) AS ultima_atividade
            FROM usuarios u
            LEFT JOIN progresso_aulas p ON p.usuario_id = u.id
            WHERE u.papel = 'aluno' AND u.ativo = 1
            GROUP BY u.id, u.login, u.nome
            ORDER BY u.id
        """).fetchall()
    return [dict(linha) for linha in linhas]


inicializar_banco()
