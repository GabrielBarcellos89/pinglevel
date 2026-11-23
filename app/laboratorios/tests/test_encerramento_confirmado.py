"""Executa o método real de remoção com cliente CORE fixture; sem host/SDK reais."""
import ast
from apoio_gerenciador import constantes
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest


class CoreFixture:
    def __init__(self):
        self.ids = {11, 12}
        self.apagadas = []
        self.falhar = False
        self.confirmar = True
        self.nome = 'pl-s11-aluno-docker1'
        self.fechado = False

    def get_sessions(self):
        return [SimpleNamespace(id=i) for i in self.ids]

    def get_session(self, sid):
        return SimpleNamespace(nodes={1: SimpleNamespace(name=self.nome)})

    def delete_session(self, sid):
        self.apagadas.append(sid)
        if self.falhar:
            raise RuntimeError('fixture: CORE indisponível')
        if self.confirmar:
            self.ids.discard(sid)
        return True

    def close(self):
        self.fechado = True


class TestEncerramentoConfirmado(unittest.TestCase):
    def setUp(self):
        filename = Path(__file__).resolve().parents[1] / 'gerenciador.py'
        tree = ast.parse(filename.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'GerenciadorLaboratorios')
        metodos = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('encerrar_confirmado', '_encerrar_confirmado')]
        method = next((n for n in metodos if n.name == 'encerrar_confirmado'), None)
        self.assertIsNotNone(method, 'Falta remoção Lab2 confirmada por leitura de retorno do CORE')
        scope = constantes()
        exec(compile(ast.Module(body=metodos, type_ignores=[]), str(filename), 'exec'), scope)
        self.executar = scope['encerrar_confirmado']
        self.core = CoreFixture()
        self.lab = SimpleNamespace(session_id=11, laboratorio_id='primeira-lan', login='aluno')
        self.outro = SimpleNamespace(session_id=12, laboratorio_id='primeiro-contato', login='outro')
        self.salvos = []
        self.engine = SimpleNamespace(_lock=threading.RLock(), _laboratorios={1: self.lab, 2: self.outro},
            _capturas={}, _core=lambda: self.core, _nome_seguro=lambda login: login,
            _salvar_estado=lambda: self.salvos.append(True))
        self.engine.trava = lambda uid: self.engine._lock
        self.engine._encerrar_confirmado = lambda *a: scope['_encerrar_confirmado'](self.engine, *a)

    def test_confirma_remocao_e_preserva_sessao_de_outro_aluno(self):
        self.assertTrue(self.executar(self.engine, 1, 11))
        self.assertEqual(self.core.apagadas, [11])
        self.assertEqual(self.core.ids, {12})
        self.assertNotIn(1, self.engine._laboratorios)
        self.assertIs(self.engine._laboratorios[2], self.outro)
        self.assertTrue(self.core.fechado)
        self.assertEqual(len(self.salvos), 1)

    def test_falha_core_nao_descarta_registro_local(self):
        self.core.falhar = True
        with self.assertRaises(RuntimeError):
            self.executar(self.engine, 1, 11)
        self.assertIs(self.engine._laboratorios[1], self.lab)
        self.assertEqual(self.core.ids, {11, 12})
        self.assertTrue(self.core.fechado)
        self.assertFalse(self.salvos)

    def test_rpc_positivo_sem_remocao_nao_significa_encerrado(self):
        self.core.confirmar = False
        with self.assertRaises(RuntimeError):
            self.executar(self.engine, 1, 11)
        self.assertIs(self.engine._laboratorios[1], self.lab)
        self.assertFalse(self.salvos)

    def test_id_alheio_nao_remove_nenhuma_sessao(self):
        self.assertFalse(self.executar(self.engine, 1, 12))
        self.assertFalse(self.core.apagadas)
        self.assertEqual(self.core.ids, {11, 12})

    def test_no_alheio_impede_exclusao_de_id_reutilizado(self):
        self.core.nome = 'pl-s11-outra-conta-docker1'
        with self.assertRaises(RuntimeError):
            self.executar(self.engine, 1, 11)
        self.assertFalse(self.core.apagadas)
        self.assertIs(self.engine._laboratorios[1], self.lab)

    def test_missao_primeiro_contato_nao_e_alvo_deste_metodo(self):
        with self.assertRaises(ValueError):
            self.executar(self.engine, 2, 12)
        self.assertFalse(self.core.apagadas)

    def test_sessao_ja_ausente_finaliza_so_registro_do_dono(self):
        self.core.ids.discard(11)
        self.assertTrue(self.executar(self.engine, 1, 11))
        self.assertFalse(self.core.apagadas)
        self.assertIs(self.engine._laboratorios[2], self.outro)


if __name__ == '__main__':
    unittest.main()
