"""Handler real + SQLite temporário + engine fixture; não inicia CORE real."""
import ast
import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from testar_retomada_ipv4 import BancoIsolado, progresso
from laboratorios.api_gateway_guiado import despachar_gateway
from laboratorios.gateway_guiado import ServicoGateway
from laboratorios.tests.test_gateway_guiado import Engine

class EngineFixture(Engine):
    def obter(self, uid, heartbeat=True):
        return super().obter(uid)


class TestHandlerGateway(BancoIsolado):
    def setUp(self):
        super().setUp()
        self.engine = EngineFixture()
        self.service = ServicoGateway(self.engine, progresso.concluir_laboratorio, progresso.obter_resumo_usuario)
        filename = Path(__file__).with_name('pinglevel_poc.py')
        tree = ast.parse(filename.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Handler')
        context = {'BaseHTTPRequestHandler': BaseHTTPRequestHandler, 'json': json,
            'urlsplit': urlsplit, 'parse_qs': parse_qs, 'GERENCIADOR': self.engine,
            'GATEWAY_GUIADO': self.service, 'despachar_gateway': despachar_gateway,
            'FRONTEND_URL': 'http://localhost', 'LABORATORIO_PADRAO': 'primeiro-contato', 'permitir': lambda *_: True,
            'token_do_cookie': lambda cookie: cookie,
            'obter_usuario': lambda token: {'id': int(token[-1]), 'login': 'fixture'} if token in ('usuario-1', 'usuario-2') else None,
            'auditar': lambda *_args, **_kwargs: None}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(filename), 'exec'), context)
        self.context = context
        handler = context['Handler']
        handler.log_message = lambda *_: None
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def req(self, path, data=None, user='usuario-1', origin='http://localhost'):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=5)
        headers = {'Content-Type': 'application/json'}
        if user: headers['Cookie'] = user
        if origin: headers['Origin'] = origin
        c.request('GET' if data is None else 'POST', path,
            body=None if data is None else json.dumps(data), headers=headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try: payload = json.loads(raw)
        except ValueError: payload = {'erro': raw.decode(errors='replace')}
        return r.status, payload

    def base(self):
        status, s = self.req('/api/gateway/status')
        self.assertEqual(status, 200, s)
        return {'session_id': s['laboratorio']['session_id'], 'revisao': s['missao']['revisao']}

    def fluxo(self):
        self.assertEqual(self.req('/api/gateway/iniciar', {})[0],200)
        for action,extra in [('prever',{'local':'nao','remota':'sim'}),('testar-antes',{}),('classificar',{'resposta':'outra-rede'}),('conferir',{}),('aplicar',{'gateway':'192.168.10.1'}),('testar-depois',{}),('interpretar',{'resposta':'gateway-remoto'})]:
            status,data=self.req('/api/gateway/'+action,{**self.base(),**extra})
            self.assertEqual(status,200,(action,data))
        return self.base()

    def test_fluxo_http_com_banco_temporario_xp_unico_e_retoma_conclusao(self):
        status,data=self.req('/api/gateway/status');self.assertEqual(status,200,data);self.assertFalse(data['ativo']);self.assertIsNone(self.engine.lab)
        payload=self.fluxo();status,data=self.req('/api/gateway/validar',payload)
        self.assertEqual(status,200,data);self.assertEqual(data['xp_concedido'],100);self.assertFalse(data['ativo']);self.assertTrue(data['conclusao']['registrada'])
        self.assertEqual(self.req('/api/gateway/validar',payload)[1]['xp_concedido'],0)
        self.context['GATEWAY_GUIADO']=ServicoGateway(self.engine,progresso.concluir_laboratorio,progresso.obter_resumo_usuario)
        status,data=self.req('/api/gateway/status');self.assertEqual(status,200,data);self.assertTrue(data['conclusao']['registrada']);self.assertFalse(data['ativo'])
        self.assertIsNone(self.req('/api/gateway/status',user='usuario-2')[1]['conclusao'])
        with progresso._conectar() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM eventos_xp WHERE origem_id='saindo-da-rede-local'").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM eventos_xp WHERE origem_id IN ('primeira-lan','primeiro-contato')").fetchone()[0],0)

    def test_autenticacao_origem_e_protecao_legada(self):
        self.assertEqual(self.req('/api/gateway/status',user=None)[0],401)
        for origin in [None,'http://nao-confiavel']:
            self.assertEqual(self.req('/api/gateway/iniciar',{},origin=origin)[0],403)
        self.assertIsNone(self.engine.lab)
        self.assertEqual(self.req('/api/gateway/iniciar',{})[0],200)
        sid=self.engine.lab.session_id
        for path in ['/api/comando','/api/validar','/api/encerrar','/api/estender','/api/aprendizagem','/api/tutor']:
            self.assertEqual(self.req(path,{})[0],409,path);self.assertEqual(self.engine.lab.session_id,sid)
        self.assertEqual(self.req('/api/iniciar',{'laboratorio_id':'saindo-da-rede-local'})[0],409)
        self.assertEqual(self.req('/api/gateway/encerrar',self.base(),user='usuario-2')[0],409)
        self.assertEqual(self.engine.lab.session_id,sid)

    def test_conclusao_persistida_mesmo_com_limpeza_pendente(self):
        payload=self.fluxo();self.engine.cleanup=False
        status,data=self.req('/api/gateway/validar',payload);self.assertEqual(status,200,data);self.assertTrue(data['conclusao']['encerramento_pendente']);self.assertEqual(data['xp_concedido'],100)
        self.engine.cleanup=True
        status,data=self.req('/api/gateway/encerrar',self.base());self.assertEqual(status,200,data);self.assertFalse(data['ativo']);self.assertEqual(data['xp_concedido'],0)
        with progresso._conectar() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM eventos_xp WHERE origem_id='saindo-da-rede-local'").fetchone()[0],1)
