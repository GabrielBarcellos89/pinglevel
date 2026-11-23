"""Prepara o banco para a apresentação de 18/11/2026: remove todas as contas de aluno (com progresso, XP e vínculos)
e cria aluno01 a aluno25 na turma de demonstração, com a mesma senha e validade até 19/11/2026 às 04:00 (Brasília).

Professores e administradores não são tocados. Faz backup consistente antes (tools/backup) e roda numa transação só.
Sem --aplicar, só mostra o que faria. A senha vem da variável PINGLEVEL_SENHA_APRESENTACAO ou é pedida sem eco.

Rodar em produção, depois de publicar a validade das contas e reiniciar o backend (a coluna expira_em é criada
na inicialização):
    /opt/packetlab/venv/bin/python /opt/packetlab/tools/admin/preparar_apresentacao.py [--aplicar]
"""
import argparse
import getpass
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / 'app/prototipo'), str(RAIZ / 'tools/backup')]
from autenticacao import BANCO, _hash_senha  # noqa: E402
import backup_banco  # noqa: E402

VALIDADE = datetime(2026, 11, 19, 4, 0, tzinfo=timezone(timedelta(hours=-3)))
LOGINS = [f'aluno{n:02d}' for n in range(1, 26)]
TURMA = 'demonstracao'


def resumo(conexao):
    alunos = [linha[0] for linha in conexao.execute("SELECT login FROM usuarios WHERE papel = 'aluno' ORDER BY login")]
    ids = "SELECT id FROM usuarios WHERE papel = 'aluno'"
    contagem = {t: conexao.execute(f'SELECT COUNT(*) FROM {t} WHERE usuario_id IN ({ids})').fetchone()[0]
                for t in ('progresso_aulas', 'progresso_laboratorios', 'eventos_xp', 'estado_aulas', 'turma_usuarios', 'sessoes_auth')}
    return alunos, contagem


def aplicar(conexao, senha, agora):
    turma = conexao.execute('SELECT id FROM turmas WHERE codigo = ? AND ativo = 1', (TURMA,)).fetchone()
    if not turma:
        raise SystemExit(f'Turma "{TURMA}" não encontrada ou inativa.')
    ids = "SELECT id FROM usuarios WHERE papel = 'aluno'"
    conexao.execute('BEGIN IMMEDIATE')
    # estado_aulas depende de progresso_aulas; os demais, do usuário. Apagados explicitamente, sem depender do CASCADE.
    for tabela in ('estado_aulas', 'progresso_aulas', 'progresso_laboratorios', 'eventos_xp', 'turma_usuarios', 'sessoes_auth'):
        conexao.execute(f'DELETE FROM {tabela} WHERE usuario_id IN ({ids})')
    # A auditoria fica; só perde a referência às contas removidas.
    conexao.execute(f'UPDATE auditoria_admin SET alvo_usuario_id = NULL WHERE alvo_usuario_id IN ({ids})')
    conexao.execute(f'UPDATE auditoria_seguranca SET usuario_id = NULL WHERE usuario_id IN ({ids})')
    removidos = conexao.execute("DELETE FROM usuarios WHERE papel = 'aluno'").rowcount
    validade = int(VALIDADE.timestamp())
    for numero, login in enumerate(LOGINS, 1):
        salt, senha_hash = _hash_senha(senha)
        cursor = conexao.execute(
            """INSERT INTO usuarios (login, nome, papel, senha_salt, senha_hash, ativo, criado_em, administrador,
                                     troca_senha_obrigatoria, expira_em)
               VALUES (?, ?, 'aluno', ?, ?, 1, ?, 0, 0, ?)""",
            (login, f'Aluno {numero:02d}', salt, senha_hash, agora, validade))
        conexao.execute('INSERT INTO turma_usuarios (turma_id, usuario_id, matriculado_em) VALUES (?, ?, ?)',
                        (turma[0], cursor.lastrowid, agora))
    conexao.execute('COMMIT')
    return removidos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--aplicar', action='store_true', help='faz o backup e altera o banco')
    parser.add_argument('--banco', type=Path, default=BANCO)
    args = parser.parse_args()

    conexao = sqlite3.connect(args.banco, timeout=10, isolation_level=None)
    conexao.execute('PRAGMA foreign_keys = ON')
    colunas = {linha[1] for linha in conexao.execute('PRAGMA table_info(usuarios)')}
    if 'expira_em' not in colunas:
        raise SystemExit('O banco ainda não tem a coluna expira_em: publique a validade das contas e reinicie o backend antes.')
    alunos, contagem = resumo(conexao)
    print(f'Alunos a remover ({len(alunos)}): {", ".join(alunos) or "nenhum"}')
    print('Registros ligados a eles: ' + ', '.join(f'{t} {n}' for t, n in contagem.items()))
    print(f'Contas a criar: {LOGINS[0]} a {LOGINS[-1]} ({len(LOGINS)}), turma "{TURMA}", válidas até {VALIDADE:%d/%m/%Y %H:%M} (Brasília).')
    if not args.aplicar:
        print('Nada foi alterado. Use --aplicar para fazer o backup e aplicar.')
        return

    senha = os.environ.get('PINGLEVEL_SENHA_APRESENTACAO') or getpass.getpass('Senha das contas da apresentação: ')
    if len(senha) < 6:
        raise SystemExit('A senha precisa ter pelo menos 6 caracteres.')
    copia, _, _ = backup_banco.fazer_backup(args.banco, backup_banco.DESTINO)
    print(f'Backup: {copia}')
    removidos = aplicar(conexao, senha, int(time.time()))
    print(f'Removidos {removidos} alunos; criadas {len(LOGINS)} contas.')


if __name__ == '__main__':
    main()
