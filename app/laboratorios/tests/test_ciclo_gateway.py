"""Ciclo de vida do gerenciador real sem SDK/CORE: nenhuma exclusão não confirmada."""
import ast, threading, time, unittest
from apoio_gerenciador import constantes
from pathlib import Path
from types import SimpleNamespace as NS

class CicloGateway(unittest.TestCase):
    def setUp(self):
        filename=Path(__file__).resolve().parents[1]/'gerenciador.py';tree=ast.parse(filename.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GerenciadorLaboratorios');scope={'time':time,**constantes()}
        methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ['encerrar','encerrar_expirados','encerrar_todos']]
        exec(compile(ast.Module(body=methods,type_ignores=[]),str(filename),'exec'),scope);self.methods=scope
        self.lab=NS(laboratorio_id='saindo-da-rede-local',session_id=11,login='qa',prazo=0,heartbeat=0)
        self.other=NS(laboratorio_id='primeiro-contato',session_id=22,login='outro',prazo=0,heartbeat=0)
        self.confirm_calls=[]
        def confirmed(uid,sid,motivo):self.confirm_calls.append((uid,sid));raise RuntimeError('CORE indisponível')
        self.engine=NS(_lock=threading.RLock(),_laboratorios={1:self.lab,2:self.other},_capturas={},_salvar_estado=lambda:None,_core=lambda:NS(delete_session=lambda sid:True),encerrar_confirmado=confirmed)
        self.engine.trava=lambda uid:self.engine._lock
        self.engine.encerrar=lambda uid,motivo='solicitacao':scope['encerrar'](self.engine,uid,motivo)
    def test_encerramento_lab3_nao_descarta_registro_sem_confirmacao(self):
        with self.assertRaises(RuntimeError):self.engine.encerrar(1)
        self.assertIs(self.engine._laboratorios[1],self.lab);self.assertEqual(self.confirm_calls,[(1,11)])
    def test_expiracao_nao_perde_lab3_nem_bloqueia_limpeza_de_outro(self):
        result=self.methods['encerrar_expirados'](self.engine,60)
        self.assertEqual(result,[2]);self.assertIn(1,self.engine._laboratorios);self.assertNotIn(2,self.engine._laboratorios)
        self.assertEqual(self.confirm_calls,[(1,11)])
    def test_parada_tenta_demais_sessoes_sem_descartar_falha_lab3(self):
        self.methods['encerrar_todos'](self.engine)
        self.assertIn(1,self.engine._laboratorios);self.assertNotIn(2,self.engine._laboratorios);self.assertEqual(self.confirm_calls,[(1,11)])

if __name__=='__main__':unittest.main()
