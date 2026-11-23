"""Recuperação do caso exato da revisão: falha pré-nós + remoção transitória.
O gerenciador é o código real compilado por AST; somente o CORE é fixture.
"""
import __future__
from apoio_gerenciador import constantes
import ast
import collections
import contextlib
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

class Session:
    id=77
    def __init__(self,directory):self.dir=str(directory);self.nodes={}
    def set_options(self,options):raise RuntimeError('falha antes dos nós')

class Core:
    def __init__(self,directory):self.session=Session(directory);self.ids={77};self.deleted=[];self.fail_delete=True
    def create_session(self):return self.session
    def get_sessions(self):return [NS(id=i) for i in self.ids]
    def get_session(self,sid):return self.session
    def delete_session(self,sid):
        if self.fail_delete:raise RuntimeError('falha transitória na remoção')
        self.deleted.append(sid);self.ids.discard(sid);return True
    def close(self):pass

class RecuperacaoVazia(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/'pycore.77';self.directory.mkdir()
        self.core=Core(self.directory)
        file=Path(__file__).resolve().parents[1]/'gerenciador.py';tree=ast.parse(file.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GerenciadorLaboratorios')
        scope={**constantes(),'Path':Path,'time':time,'contextmanager':contextlib.contextmanager,'deque':collections.deque,'threading':threading,'re':re,'Laboratorio':lambda **kw:NS(**kw),
            'LABORATORIO_PADRAO':'primeiro-contato','obter_cenario':lambda lab:NS(LABORATORIO_ID=lab,TEMPO_LIMITE=900,TEMPO_EXTENSAO=300,MAX_EXTENSOES=1)}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(file),'exec',flags=__future__.annotations.compiler_flag),scope)
        self.engine=scope['GerenciadorLaboratorios']();self.engine._core=lambda:self.core;self.saved=[]
        self.engine._salvar_estado=lambda:self.saved.append(True)
    def quarantine(self):
        with self.assertRaises(RuntimeError):self.engine.criar(1,'qa','saindo-da-rede-local')
        self.assertFalse(self.engine._laboratorios[1].preparacao_confirmada)
        self.assertFalse(self.core.deleted);self.core.fail_delete=False
    def test_falha_antes_dos_nos_pode_ser_encerrada_apos_rpc_recuperar(self):
        self.quarantine()
        self.assertTrue(self.engine.encerrar_confirmado(1,77))
        self.assertEqual(self.core.deleted,[77]);self.assertNotIn(1,self.engine._laboratorios)
    def test_id_reutilizado_com_diretorio_diferente_nao_pode_ser_removido(self):
        self.quarantine();other=Path(self.temp.name)/'outra-sessao';other.mkdir();self.core.session.dir=str(other)
        with self.assertRaises(RuntimeError):self.engine.encerrar_confirmado(1,77)
        self.assertFalse(self.core.deleted);self.assertIn(1,self.engine._laboratorios)
    def test_mesmo_caminho_com_diretorio_recriado_nao_comprova_propriedade(self):
        self.quarantine();self.directory.rename(Path(self.temp.name)/'diretorio-anterior');self.directory.mkdir()
        with self.assertRaises(RuntimeError):self.engine.encerrar_confirmado(1,77)
        self.assertFalse(self.core.deleted);self.assertIn(1,self.engine._laboratorios)
    def test_no_alheio_bloqueia_remocao_mesmo_com_identidade_da_criacao(self):
        self.quarantine();self.core.session.nodes={1:NS(name='pl-s77-outro-aluno-pc1')}
        with self.assertRaises(RuntimeError):self.engine.encerrar_confirmado(1,77)
        self.assertFalse(self.core.deleted)
    def test_sessao_vazia_sem_prova_da_criacao_permanece_bloqueada(self):
        self.engine._laboratorios[1]=NS(session_id=77,laboratorio_id='saindo-da-rede-local',login='qa',preparacao_confirmada=False)
        self.core.fail_delete=False
        with self.assertRaises(RuntimeError):self.engine.encerrar_confirmado(1,77)
        self.assertFalse(self.core.deleted)

    def test_cleanup_inicial_nao_remove_vazia_sem_identidade_disponivel(self):
        self.core.session.dir=None;self.core.fail_delete=False
        with self.assertRaises(RuntimeError):self.engine.criar(1,'qa','saindo-da-rede-local')
        self.assertFalse(self.core.deleted);self.assertIn(1,self.engine._laboratorios)
        self.assertFalse(self.engine._laboratorios[1].preparacao_confirmada)
    def test_lab2_vazia_nao_recebe_excecao_de_propriedade_do_lab3(self):
        self.engine._laboratorios[1]=NS(session_id=77,laboratorio_id='primeira-lan',login='qa',preparacao_confirmada=False)
        self.core.fail_delete=False
        with self.assertRaises(RuntimeError):self.engine.encerrar_confirmado(1,77)
        self.assertFalse(self.core.deleted)

if __name__=='__main__':unittest.main()
