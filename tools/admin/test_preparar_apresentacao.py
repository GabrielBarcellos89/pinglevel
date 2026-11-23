"""Preparação da apresentação num banco temporário: alunos removidos com tudo o que é deles, professores intactos,
25 contas novas que expiram, e um reinício que não recria as contas iniciais."""
import importlib
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BANCO = Path(tempfile.mkdtemp(prefix='pinglevel-apresentacao-')) / 'auth.db'
os.environ['PINGLEVEL_AUTH_DB'] = str(BANCO)
sys.path[:0] = [str(RAIZ / 'app/prototipo'), str(RAIZ / 'tools/admin')]

import autenticacao  # noqa: E402
import administracao  # noqa: E402,F401
import progresso  # noqa: E402,F401
import seguranca  # noqa: E402
import turmas  # noqa: E402,F401
import preparar_apresentacao as p  # noqa: E402


def conectar():
    conexao = sqlite3.connect(BANCO, isolation_level=None)
    conexao.execute('PRAGMA foreign_keys = ON')
    return conexao


def test_remove_alunos_cria_contas_temporarias_e_nao_recria_iniciais():
    seguranca.inicializar_auditoria()
    c = conectar()
    user1 = c.execute("SELECT id FROM usuarios WHERE login = 'user1'").fetchone()[0]
    agora = int(time.time())
    c.execute("INSERT INTO progresso_laboratorios (usuario_id, laboratorio_id, concluido, iniciado_em, atualizado_em) VALUES (?, 'primeira-lan', 1, ?, ?)", (user1, agora, agora))
    c.execute("INSERT INTO eventos_xp (usuario_id, origem_tipo, origem_id, pontos, descricao, criado_em) VALUES (?, 'laboratorio', 'primeira-lan', 50, 'Lab 2', ?)", (user1, agora))
    c.execute("INSERT INTO auditoria_seguranca (usuario_id, evento, origem, criado_em) VALUES (?, 'teste', 'teste', ?)", (user1, agora))
    professores = c.execute("SELECT id, senha_hash FROM usuarios WHERE papel = 'professor'").fetchall()

    assert p.aplicar(c, 'senha-da-demo', agora) == 10
    logins = [linha[0] for linha in c.execute("SELECT login FROM usuarios WHERE papel = 'aluno' ORDER BY login")]
    assert logins == p.LOGINS
    assert c.execute("SELECT COUNT(*) FROM eventos_xp").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM progresso_laboratorios").fetchone()[0] == 0
    assert c.execute("SELECT usuario_id FROM auditoria_seguranca").fetchone()[0] is None
    assert c.execute("SELECT id, senha_hash FROM usuarios WHERE papel = 'professor'").fetchall() == professores
    assert c.execute("SELECT COUNT(*) FROM turma_usuarios tu JOIN turmas t ON t.id = tu.turma_id WHERE t.codigo = 'demonstracao'").fetchone()[0] == 25

    # A validade real (19/11/2026) já passou: para conferir o login, as contas criadas valem mais uma hora.
    c.execute("UPDATE usuarios SET expira_em = ? WHERE papel = 'aluno'", (int(time.time()) + 3600,))
    token, usuario = autenticacao.autenticar('aluno07', 'senha-da-demo')
    assert usuario['login'] == 'aluno07' and not usuario['troca_senha_obrigatoria']
    assert autenticacao.obter_usuario(token)['login'] == 'aluno07'

    # Depois da validade: login recusado e a sessão aberta cai.
    c.execute("UPDATE usuarios SET expira_em = ? WHERE login = 'aluno07'", (int(time.time()) - 1,))
    assert autenticacao.autenticar('aluno07', 'senha-da-demo') is None
    assert autenticacao.obter_usuario(token) is None
    assert autenticacao.autenticar('aluno08', 'senha-da-demo') is not None

    # Um reinício do backend não traz de volta user1..user10 com a senha padrão.
    importlib.reload(autenticacao)
    assert c.execute("SELECT COUNT(*) FROM usuarios WHERE login LIKE 'user%'").fetchone()[0] == 0


def test_validade_e_19_11_as_4h_de_brasilia():
    assert p.VALIDADE.isoformat() == '2026-11-19T04:00:00-03:00'
    assert int(p.VALIDADE.timestamp()) == 1795071600  # 2026-11-19 07:00 UTC


def test_administrador_cria_com_validade_e_impoe_estende_ou_tira_o_limite():
    import pytest
    c = conectar()
    admin = c.execute("SELECT id FROM usuarios WHERE papel = 'professor' ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE usuarios SET administrador = 1 WHERE id = ?", (admin,))
    turma = c.execute("SELECT id FROM turmas WHERE codigo = 'demonstracao'").fetchone()[0]
    agora = int(time.time())
    criado = administracao.criar_usuario(admin, 'visitante', 'Visitante', 'aluno', turma, agora + 3600)
    assert criado['expira_em'] == agora + 3600
    assert administracao.criar_usuario(admin, 'semlimite', 'Sem Limite', 'professor')['expira_em'] is None
    with pytest.raises(ValueError):
        administracao.criar_usuario(admin, 'errado', 'Errado', 'aluno', turma, 'amanhã')
    validade = lambda login: c.execute("SELECT expira_em FROM usuarios WHERE login = ?", (login,)).fetchone()[0]  # noqa: E731
    # Diminuir para o passado expira na hora; estender devolve o acesso; sem limite tira a data.
    assert administracao.definir_validade(admin, criado['id'], agora - 60) == 1
    assert autenticacao.autenticar('visitante', criado['senha_temporaria']) is None
    administracao.definir_validade(admin, criado['id'], agora + 86400)
    assert autenticacao.autenticar('visitante', criado['senha_temporaria']) is not None
    administracao.definir_validade(admin, criado['id'], None)
    assert validade('visitante') is None
    # A turma inteira de uma vez (a partir de um aluno); o administrador nunca expira.
    total = c.execute("SELECT COUNT(*) FROM turma_usuarios WHERE turma_id = ?", (turma,)).fetchone()[0]
    assert administracao.definir_validade(admin, criado['id'], agora + 7200, turma_inteira=True) == total
    assert validade('aluno25') == agora + 7200 and validade('visitante') == agora + 7200
    with pytest.raises(ValueError, match='administrador'):
        administracao.definir_validade(admin, admin, agora + 60)


def test_redefinir_senha_continua_funcionando():
    c = conectar()
    admin = c.execute("SELECT id FROM usuarios WHERE administrador = 1 ORDER BY id LIMIT 1").fetchone()
    admin = admin[0] if admin else c.execute("SELECT id FROM usuarios WHERE papel = 'professor' ORDER BY id LIMIT 1").fetchone()[0]
    alvo = c.execute("SELECT id, login FROM usuarios WHERE login = 'aluno03'").fetchone()
    senha = administracao.redefinir_senha(admin, alvo[0])
    _, usuario = autenticacao.autenticar('aluno03', senha)
    assert usuario['troca_senha_obrigatoria']
