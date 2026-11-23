"""Exercita o Handler real por HTTP, sem inicializar CORE, RAG ou o serviço.

Extrai somente a classe com AST; autenticação usa usuários sintéticos e o
SQLite é o banco isolado preparado pelo teste de retomada.
"""
import ast
import http.client
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from testar_retomada_ipv4 import BancoIsolado, progresso
import estado_aula_ipv4 as ipv4


class TestHTTPRetomadaIPv4(BancoIsolado):
    def setUp(self):
        super().setUp()
        arquivo = Path(__file__).with_name('pinglevel_poc.py')
        arvore = ast.parse(arquivo.read_text())
        classe = next(n for n in arvore.body if isinstance(n, ast.ClassDef) and n.name == 'Handler')
        contexto = {
            'BaseHTTPRequestHandler': BaseHTTPRequestHandler,
            'json': json, 'urlsplit': urlsplit, 'parse_qs': parse_qs,
            'token_do_cookie': lambda cookie: cookie,
            'obter_usuario': lambda token: {'id': int(token[-1])} if token in ('usuario-1', 'usuario-2') else None,
            'registrar_etapa': progresso.registrar_etapa,
            'concluir_aula': progresso.concluir_aula,
            'obter_resumo_usuario': progresso.obter_resumo_usuario,
            'obter_estado_aula': ipv4.obter_estado,
            'salvar_estado_aula': ipv4.salvar_estado,
            'validar_atividade_aula': ipv4.validar_atividade,
            'ConflitoEstado': ipv4.ConflitoEstado,
            'auditar': lambda *args, **kwargs: None,
        }
        exec(compile(ast.Module(body=[classe], type_ignores=[]), str(arquivo), 'exec'), contexto)
        handler = contexto['Handler']
        handler.log_message = lambda *args: None
        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.fechar_servidor)

    def fechar_servidor(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(timeout=5)

    def requisicao(self, metodo, caminho, dados=None, usuario: str | None = 'usuario-1', bruto=None) -> tuple[int, dict]:
        c = http.client.HTTPConnection('127.0.0.1', int(self.servidor.server_address[1]), timeout=5)
        try:
            headers = {'Content-Type': 'application/json'}
            if usuario:
                headers['Cookie'] = usuario
            body = bruto if bruto is not None else (json.dumps(dados) if dados is not None else None)
            c.request(metodo, caminho, body=body, headers=headers)
            r = c.getresponse()
            conteudo = r.read()
            try:
                payload = json.loads(conteudo)
            except ValueError:
                payload = {'erro': conteudo.decode(errors='replace')}
            return r.status, payload
        finally:
            c.close()

    def test_get_e_salvamento_autenticados_isolam_usuarios(self):
        rota = '/api/progresso/aula/estado?aula_id=enderecamento-ipv4'
        status, dados = self.requisicao('GET', rota)
        self.assertEqual(status, 200, dados)
        self.assertEqual(dados['estado']['revisao'], 0)
        self.assertEqual(self.requisicao('GET', rota, usuario=None)[0], 401)
        status, dados = self.requisicao('POST', '/api/progresso/aula/estado', {
            'aula_id': 'enderecamento-ipv4', 'revisao': 0, 'respostas': {'previsao': 'switch'},
        })
        self.assertEqual(status, 200, dados)
        self.assertEqual(dados['estado']['respostas']['previsao'], 'switch')
        self.assertEqual(self.requisicao('GET', rota, usuario='usuario-2')[1]['estado']['respostas']['previsao'], '')

    def test_erros_de_payload_e_conflito_nao_viram_500(self):
        rota = '/api/progresso/aula/estado'
        for bruto in ('{', '[]', 'null'):
            self.assertEqual(self.requisicao('POST', rota, bruto=bruto)[0], 400)
        dados = {'aula_id': 'enderecamento-ipv4', 'revisao': 0, 'respostas': {}}
        self.assertEqual(self.requisicao('POST', rota, {**dados, 'usuario_id': 2})[0], 400)
        self.assertEqual(self.requisicao('POST', rota, dados)[0], 200)
        self.assertEqual(self.requisicao('POST', rota, dados)[0], 409)
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula', {
            'aula_id': 'enderecamento-ipv4', 'etapa_atual': 5, 'revisao': 1,
        })[0], 400)
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula/concluir', {
            'aula_id': 'enderecamento-ipv4', 'revisao': 1,
        })[0], 400)
    def test_percurso_completo_por_http(self):
        aula = 'enderecamento-ipv4'
        status, dados = self.requisicao('GET', '/api/progresso/aula/estado?aula_id=' + aula)
        self.assertEqual(status, 200)
        estado = dados['estado']
        def executar(rota, **campos):
            nonlocal estado
            status, dados = self.requisicao('POST', rota, {
                'aula_id': aula, 'revisao': estado['revisao'], **campos,
            })
            self.assertEqual(status, 200, dados)
            estado = dados['estado']
            return dados
        executar('/api/progresso/aula', etapa_atual=1)
        executar('/api/progresso/aula/estado', respostas={'previsao': 'destino'})
        executar('/api/progresso/aula', etapa_atual=2)
        executar('/api/progresso/aula/estado', respostas={
            'pratica': {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'},
        })
        executar('/api/progresso/aula/validar', atividade='pratica')
        for etapa in (3, 4):
            executar('/api/progresso/aula', etapa_atual=etapa)
        executar('/api/progresso/aula/estado', respostas={'interpretacao': 'mac-gateway'})
        executar('/api/progresso/aula/validar', atividade='interpretacao')
        executar('/api/progresso/aula', etapa_atual=5)
        resultado = executar('/api/progresso/aula/concluir')
        self.assertEqual(resultado['progresso']['xp_concedido'], 100)
        self.assertEqual(estado['modo'], 'revisao')
        self.assertEqual(executar('/api/progresso/aula/concluir')['progresso']['xp_concedido'], 0)
        self.assertEqual(self.requisicao('POST', '/api/progresso/aula/estado', {
            'aula_id': aula, 'revisao': estado['revisao'], 'respostas': {'previsao': 'switch'},
        })[0], 400)


if __name__ == '__main__':
    unittest.main()
