"""Testes isolados: nunca importam progresso com o banco da plataforma."""
import atexit
import importlib
import importlib.util
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

RAIZ_TESTES = tempfile.TemporaryDirectory(prefix='retomada-ipv4-', dir=os.environ['TMPDIR'])
atexit.register(RAIZ_TESTES.cleanup)
with patch.dict(os.environ, {'PINGLEVEL_AUTH_DB': str(Path(RAIZ_TESTES.name) / 'bootstrap.db')}):
    import progresso


class BancoIsolado(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(dir=RAIZ_TESTES.name)
        self.addCleanup(self.pasta.cleanup)
        self.banco_anterior = progresso.BANCO
        progresso.BANCO = Path(self.pasta.name) / 'teste.db'
        self.addCleanup(setattr, progresso, 'BANCO', self.banco_anterior)
        progresso.inicializar_banco()
        with progresso._conectar() as c:
            c.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY)')
            c.executemany('INSERT INTO usuarios VALUES (?)', [(1,), (2,)])



class TestRetomadaIPv4(BancoIsolado):
    def modulo(self):
        self.assertIsNotNone(importlib.util.find_spec('estado_aula_ipv4'),
                             'Falta o backend de estado da aula IPv4')
        return importlib.import_module('estado_aula_ipv4')

    def test_respostas_parciais_sao_recuperadas_sem_aprovacao(self):
        m = self.modulo()
        inicial = m.obter_estado(1, 'enderecamento-ipv4')
        self.assertEqual(inicial['modo'], 'andamento')
        salvo = m.salvar_estado(1, 'enderecamento-ipv4', 0,
                               {'previsao': 'destino', 'pratica': {'rede': 'rede-10'}})
        retomado = m.obter_estado(1, 'enderecamento-ipv4')
        self.assertEqual(retomado, salvo)
        self.assertEqual(retomado['respostas']['previsao'], 'destino')
        self.assertEqual(retomado['respostas']['pratica'], {'rede': 'rede-10'})
        self.assertEqual(retomado['validacoes']['pratica']['status'], 'pendente')
        self.assertEqual(m.obter_estado(2, 'enderecamento-ipv4')['respostas']['pratica'], {})

    def iniciar_pratica(self, m):
        estado = m.avancar(1, 'enderecamento-ipv4', 0, 1)
        estado = m.salvar_estado(1, 'enderecamento-ipv4', estado['revisao'],
                                 {'previsao': 'destino'})
        return m.avancar(1, 'enderecamento-ipv4', estado['revisao'], 2)

    def test_conferencia_real_e_invalidada_ao_editar_resposta(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m, 'validar_atividade', None)),
                        'Falta conferir a atividade no servidor')
        estado = self.iniciar_pratica(m)
        respostas = {'pratica': {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'}}
        estado = m.salvar_estado(1, 'enderecamento-ipv4', estado['revisao'], respostas)
        self.assertEqual(estado['validacoes']['pratica']['status'], 'pendente')
        estado = m.validar_atividade(1, 'enderecamento-ipv4', estado['revisao'], 'pratica')
        self.assertEqual(estado['validacoes']['pratica']['status'], 'aprovada')
        estado = m.avancar(1, 'enderecamento-ipv4', estado['revisao'], 3)
        estado = m.salvar_estado(1, 'enderecamento-ipv4', estado['revisao'],
                                 {'pratica': {'local': 'nao'}})
        self.assertEqual(estado['validacoes']['pratica']['status'], 'pendente')
        self.assertEqual(estado['etapa_retomada'], 2)
        estado = m.validar_atividade(1, 'enderecamento-ipv4', estado['revisao'], 'pratica')
        self.assertEqual(estado['validacoes']['pratica']['status'], 'incorreta')
        self.assertEqual(estado['validacoes']['pratica']['erros'], ['local'])
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4'), estado)
    def test_conexao_e_fechada_ao_sair_do_contexto(self):
        with progresso._conectar() as c:
            c.execute('SELECT 1')
        with self.assertRaises(sqlite3.ProgrammingError):
            c.execute('SELECT 1')

    def test_endpoint_antigo_nao_permite_pular_atividades_ipv4(self):
        with self.assertRaises(ValueError):
            progresso.registrar_etapa(1, 'enderecamento-ipv4', 5)

    def concluir_percurso(self, m):
        estado = self.iniciar_pratica(m)
        estado = m.salvar_estado(1, 'enderecamento-ipv4', estado['revisao'],
                                 {'pratica': {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'}})
        estado = m.validar_atividade(1, 'enderecamento-ipv4', estado['revisao'], 'pratica')
        for etapa in (3, 4):
            estado = m.avancar(1, 'enderecamento-ipv4', estado['revisao'], etapa)
        estado = m.salvar_estado(1, 'enderecamento-ipv4', estado['revisao'],
                                 {'interpretacao': 'mac-gateway'})
        estado = m.validar_atividade(1, 'enderecamento-ipv4', estado['revisao'], 'interpretacao')
        return m.avancar(1, 'enderecamento-ipv4', estado['revisao'], 5)

    def test_conclusao_exige_evidencias_e_preserva_revisao_e_xp_unico(self):
        m = self.modulo()
        # Simula progresso legado: índice final não prova respostas nem conferências.
        with progresso._conectar() as c:
            c.execute("INSERT INTO progresso_aulas (usuario_id,aula_id,modulo_id,etapa_atual,percentual,concluida,iniciado_em,atualizado_em) VALUES (1,'enderecamento-ipv4','enderecamento',5,100,0,1,1)")
        with self.assertRaises(ValueError):
            progresso.concluir_aula(1, 'enderecamento-ipv4')
        estado = self.concluir_percurso(m)
        resultado = progresso.concluir_aula(1, 'enderecamento-ipv4', revisao=estado['revisao'])
        self.assertEqual(resultado['xp_concedido'], 100)
        historico = progresso.obter_resumo_usuario(1)
        self.assertEqual(progresso.concluir_aula(1, 'enderecamento-ipv4')['xp_concedido'], 0)
        self.assertEqual(progresso.obter_resumo_usuario(1), historico)
        revisao = m.obter_estado(1, 'enderecamento-ipv4')
        self.assertEqual(revisao['modo'], 'revisao')
        self.assertEqual(revisao['etapa_retomada'], 0)
        with self.assertRaises(ValueError):
            m.salvar_estado(1, 'enderecamento-ipv4', revisao['revisao'], {'previsao': 'switch'})
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4'), revisao)
    def test_revisao_desatualizada_nao_sobrescreve_respostas(self):
        m = self.modulo()
        self.assertTrue(isinstance(getattr(m, 'ConflitoEstado', None), type),
                        'Falta distinguir conflito de estado')
        salvo = m.salvar_estado(1, 'enderecamento-ipv4', 0, {'previsao': 'gateway'})
        with self.assertRaises(m.ConflitoEstado):
            m.salvar_estado(1, 'enderecamento-ipv4', 0, {'previsao': 'switch'})
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4'), salvo)

    def test_opcoes_e_aprovacoes_enviadas_pelo_cliente_sao_rejeitadas(self):
        m = self.modulo()
        for respostas in ({'aprovada': True}, {'pratica': {'rede': 'inexistente'}},
                          {'previsao': True}, {'pratica': {'estranho': 'sim'}}, []):
            with self.subTest(respostas=respostas), self.assertRaises(ValueError):
                m.salvar_estado(1, 'enderecamento-ipv4', 0, respostas)
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4')['revisao'], 0)

    def test_migracao_aditiva_preserva_conclusao_legada(self):
        with progresso._conectar() as c:
            c.execute('DROP TABLE estado_aulas')
            c.execute("INSERT INTO progresso_aulas (usuario_id,aula_id,modulo_id,etapa_atual,percentual,concluida,iniciado_em,atualizado_em,concluida_em) VALUES (1,'enderecamento-ipv4','enderecamento',5,100,1,1,2,2)")
            c.execute("INSERT INTO eventos_xp (usuario_id,origem_tipo,origem_id,pontos,descricao,criado_em) VALUES (1,'aula','enderecamento-ipv4',100,'fixture legada',2)")
        antes = progresso.obter_resumo_usuario(1)
        progresso.inicializar_banco()
        progresso.inicializar_banco()
        estado = self.modulo().obter_estado(1, 'enderecamento-ipv4')
        self.assertEqual(estado['modo'], 'revisao')
        self.assertTrue(estado['legado_sem_respostas'])
        self.assertEqual(estado['validacoes']['pratica']['status'], 'pendente')
        self.assertEqual(progresso.concluir_aula(1, 'enderecamento-ipv4')['xp_concedido'], 0)
        self.assertEqual(progresso.obter_resumo_usuario(1), antes)

    def test_outras_aulas_e_laboratorio_preservam_comportamento(self):
        for aula, etapa in [('fundamentos-aula-1', 6), ('fundamentos-modelos-osi-tcpip', 5)]:
            progresso.registrar_etapa(1, aula, etapa)
            self.assertEqual(progresso.concluir_aula(1, aula)['xp_concedido'], 100)
            self.assertEqual(progresso.concluir_aula(1, aula)['xp_concedido'], 0)
        self.assertEqual(progresso.concluir_laboratorio(1, 'primeiro-contato')['xp_concedido'], 100)
        self.assertEqual(progresso.concluir_laboratorio(1, 'primeiro-contato')['xp_concedido'], 0)
    def test_duas_abas_concorrentes_nao_perdem_respostas(self):
        m = self.modulo()
        barreira = Barrier(2)
        def salvar(previsao):
            barreira.wait(timeout=5)
            try:
                m.salvar_estado(1, 'enderecamento-ipv4', 0, {'previsao': previsao})
                return 'salvo'
            except m.ConflitoEstado:
                return 'conflito'
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(salvar, ['gateway', 'switch']))
        self.assertCountEqual(resultados, ['salvo', 'conflito'])
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4')['revisao'], 1)

    def test_conclusoes_concorrentes_concedem_uma_unica_recompensa(self):
        m = self.modulo()
        estado = self.concluir_percurso(m)
        barreira = Barrier(2)
        def concluir(_):
            barreira.wait(timeout=5)
            return progresso.concluir_aula(1, 'enderecamento-ipv4', revisao=estado['revisao'])['xp_concedido']
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(concluir, range(2)))
        self.assertCountEqual(resultados, [100, 0])
        self.assertEqual(progresso.obter_resumo_usuario(1)['xp_total'], 100)

    def test_erro_de_escrita_reverte_estado_e_resumo_juntos(self):
        m = self.modulo()
        with progresso._conectar() as c:
            c.execute("CREATE TRIGGER impedir_atualizacao BEFORE UPDATE ON progresso_aulas BEGIN SELECT RAISE(ABORT, 'falha sintética'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            m.avancar(1, 'enderecamento-ipv4', 0, 1)
        self.assertEqual(m.obter_estado(1, 'enderecamento-ipv4')['revisao'], 0)
        self.assertEqual(progresso.obter_resumo_usuario(1)['aulas'], [])

    def test_leitura_nao_cria_progresso_e_tipos_invalidos_nao_gravam(self):
        m = self.modulo()
        m.obter_estado(1, 'enderecamento-ipv4')
        self.assertEqual(progresso.obter_resumo_usuario(1)['aulas'], [])
        for revisao in (None, True, '0', -1):
            with self.subTest(revisao=revisao), self.assertRaises(ValueError):
                m.salvar_estado(1, 'enderecamento-ipv4', revisao, {})
        for etapa in (True, '1', -1, 6, 2):
            with self.subTest(etapa=etapa), self.assertRaises(ValueError):
                m.avancar(1, 'enderecamento-ipv4', 0, etapa)
        self.assertEqual(progresso.obter_resumo_usuario(1)['aulas'], [])


if __name__ == '__main__':
    unittest.main()
