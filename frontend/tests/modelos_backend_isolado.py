"""Handler real + SQLite temporário. Não acessa o banco de produção nem CORE."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'app/prototipo'))
from testar_http_retomada_ipv4 import TestHTTPRetomadaIPv4, progresso
AULA = 'fundamentos-modelos-osi-tcpip'

class TestModelosHTTP(TestHTTPRetomadaIPv4):
    def post(self, rota, dados):
        status, d = self.requisicao('POST', rota, dados)
        self.assertEqual(status, 200, d)
        return d['progresso']

    def test_conclusao_e_xp_unico(self):
        for etapa in range(5):
            self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': etapa})
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula/concluir', {'aula_id': AULA})[0], 400)
        self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 5})
        self.assertEqual(self.post('/api/progresso/aula/concluir', {'aula_id': AULA})['xp_concedido'], 100)
        self.assertEqual(self.post('/api/progresso/aula/concluir', {'aula_id': AULA})['xp_concedido'], 0)
        with progresso._conectar() as c:
            self.assertEqual(tuple(c.execute('SELECT COUNT(*), SUM(pontos) FROM eventos_xp WHERE origem_id=?', (AULA,)).fetchone()), (1, 100))

    def test_progresso_e_conclusao_legados_nao_regridem(self):
        self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 4})
        p = self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 1})
        self.assertEqual(p['aulas'][0]['etapa_atual'], 4)
        self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 5})
        self.post('/api/progresso/aula/concluir', {'aula_id': AULA})
        p = self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 0})
        a = next(a for a in p['aulas'] if a['aula_id'] == AULA)
        self.assertTrue(a['concluida'])
        self.assertEqual(a['percentual'], 100)
        self.assertEqual(a['etapa_atual'], 5)
        self.assertEqual(p['xp_total'], 100)

    def test_isolamento_e_limites_do_contrato_existente(self):
        self.post('/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 3})
        self.assertEqual(self.requisicao('GET', '/api/progresso/me', usuario='usuario-2')[1]['progresso']['aulas'], [])
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 9})[0], 400)
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula', {'aula_id': AULA, 'etapa_atual': 2}, usuario=None)[0], 401)

if __name__ == '__main__':
    names = [f'TestModelosHTTP.{n}' for n in ['test_conclusao_e_xp_unico', 'test_progresso_e_conclusao_legados_nao_regridem', 'test_isolamento_e_limites_do_contrato_existente']]
    r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names, module=sys.modules[__name__]))
    sys.exit(0 if r.wasSuccessful() else 1)
