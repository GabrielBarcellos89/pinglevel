"""Senhas provisórias das turmas (23/11/2026): aleatórias, diferentes entre alunos e a cada redefinição, nunca a antiga
senha fixa. Banco temporário; nunca usa o banco da plataforma."""
import atexit
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

RAIZ = tempfile.TemporaryDirectory(prefix='senhas-turma-', dir=os.environ.get('TMPDIR'))
atexit.register(RAIZ.cleanup)
os.environ['PINGLEVEL_AUTH_DB'] = str(Path(RAIZ.name) / 'auth.db')

import autenticacao  # noqa: E402

autenticacao.inicializar_banco()
import turmas  # noqa: E402


class TestSenhasTurma(unittest.TestCase):
    def test_senhas_aleatorias_na_criacao_e_na_redefinicao(self):
        with sqlite3.connect(autenticacao.BANCO) as c:
            professor = c.execute("SELECT id FROM usuarios WHERE papel = 'professor'").fetchone()[0]
        turma = turmas.criar_turma(professor, 'Turma de teste', 5)
        senhas = [item['senha_temporaria'] for item in turma['credenciais']]
        self.assertEqual(len(set(senhas)), 5)
        for item in turma['credenciais']:
            self.assertGreaterEqual(len(item['senha_temporaria']), 12)
            self.assertNotEqual(item['senha_temporaria'], 'Senac')
            self.assertTrue(autenticacao.autenticar(item['login'], item['senha_temporaria']))
        aluno = turma['credenciais'][0]
        nova = turmas.redefinir_senha(professor, aluno['usuario_id'])
        self.assertNotIn(nova, (aluno['senha_temporaria'], 'Senac'))
        self.assertFalse(autenticacao.autenticar(aluno['login'], aluno['senha_temporaria']))
        self.assertTrue(autenticacao.autenticar(aluno['login'], nova))
        self.assertNotEqual(turmas.redefinir_senha(professor, aluno['usuario_id']), nova)


if __name__ == '__main__':
    unittest.main()
