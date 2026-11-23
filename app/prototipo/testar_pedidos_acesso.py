"""Pedidos de acesso: validação, banco isolado, aviso por e-mail com SMTP falso e a rota pública pelo Handler real
(extraído com AST, sem CORE nem RAG). Nunca usa o banco nem o ambiente da plataforma."""
import ast
import atexit
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

RAIZ = tempfile.TemporaryDirectory(prefix='pedidos-acesso-', dir=os.environ.get('TMPDIR'))
atexit.register(RAIZ.cleanup)
with patch.dict(os.environ, {'PINGLEVEL_AUTH_DB': str(Path(RAIZ.name) / 'bootstrap.db')}):
    import pedidos_acesso

SEM_SMTP = {f'PINGLEVEL_SMTP_{n}': '' for n in ('HOST', 'USUARIO', 'SENHA', 'PORTA', 'REMETENTE')}
VALIDO = {'nome': 'Maria  Souza', 'email': 'Maria@Exemplo.com.br', 'instituicao': 'Senac', 'mensagem': 'Quero testar.'}


class BancoIsolado(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory(dir=RAIZ.name)
        self.addCleanup(pasta.cleanup)
        anterior = pedidos_acesso.BANCO
        pedidos_acesso.BANCO = Path(pasta.name) / 'teste.db'
        self.addCleanup(setattr, pedidos_acesso, 'BANCO', anterior)
        with sqlite3.connect(pedidos_acesso.BANCO) as c:
            c.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT)')
            c.execute("INSERT INTO usuarios VALUES (1, 'Admin')")
        pedidos_acesso.inicializar_banco()


class TestPedidos(BancoIsolado):
    def test_valida_limpa_e_salva(self):
        pedido = pedidos_acesso.registrar(VALIDO, '203.0.113.7')
        self.assertEqual((pedido['nome'], pedido['email']), ('Maria Souza', 'maria@exemplo.com.br'))
        lista = pedidos_acesso.listar()
        self.assertEqual(len(lista), 1)
        self.assertIsNone(lista[0]['atendido_em'])
        pedidos_acesso.marcar_atendido(1, pedido['id'])
        self.assertEqual(pedidos_acesso.listar()[0]['atendido_por_nome'], 'Admin')
        pedidos_acesso.marcar_atendido(1, pedido['id'], False)
        self.assertIsNone(pedidos_acesso.listar()[0]['atendido_em'])
        with self.assertRaises(ValueError):
            pedidos_acesso.marcar_atendido(1, 999)
        with self.assertRaises(ValueError):
            pedidos_acesso.marcar_atendido(1, '1')

    def test_recusa_campos_invalidos(self):
        for troca in ({'nome': 'A'}, {'email': 'sem-arroba'}, {'email': 'a@b'}, {'instituicao': ''},
                      {'nome': 'Maria\r\nBcc: x@y.com'}, {'email': 'a@b.com\nBcc: c@d.com'}, {'mensagem': 'x' * 1001},
                      {'nome': 123}):
            with self.subTest(troca=troca), self.assertRaises(ValueError):
                pedidos_acesso.registrar({**VALIDO, **troca})
        self.assertEqual(pedidos_acesso.listar(), [])
        with self.assertRaises(ValueError):
            pedidos_acesso.registrar(['nao', 'e', 'dict'])

    def test_limite_de_pendentes(self):
        with patch.object(pedidos_acesso, 'MAXIMO_PENDENTES', 2):
            pedidos_acesso.registrar(VALIDO)
            pedidos_acesso.registrar(VALIDO)
            with self.assertRaises(OverflowError):
                pedidos_acesso.registrar(VALIDO)

    def test_email_so_com_configuracao_e_responde_para_quem_pediu(self):
        pedido = pedidos_acesso.registrar(VALIDO)
        with patch.dict(os.environ, SEM_SMTP):
            self.assertFalse(pedidos_acesso.avisar_por_email(pedido, smtp=lambda *a, **k: self.fail('não devia conectar')))
        enviados = []

        class SMTPFalso:
            def __init__(self, host, porta, timeout):
                enviados.append(('conectar', host, porta))
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False
            def starttls(self, context):
                enviados.append(('tls',))
            def login(self, usuario, senha):
                enviados.append(('login', usuario))
            def send_message(self, mensagem):
                enviados.append(('mensagem', mensagem))

        config = {'PINGLEVEL_SMTP_HOST': 'smtp.exemplo', 'PINGLEVEL_SMTP_USUARIO': 'envio@exemplo.com',
                  'PINGLEVEL_SMTP_SENHA': 'segredo-de-teste', 'PINGLEVEL_SMTP_PORTA': '', 'PINGLEVEL_SMTP_REMETENTE': '',
                  'PINGLEVEL_EMAIL_ACESSO': ''}
        with patch.dict(os.environ, config):
            self.assertTrue(pedidos_acesso.avisar_por_email(pedido, smtp=SMTPFalso))
        self.assertEqual(enviados[:3], [('conectar', 'smtp.exemplo', 587), ('tls',), ('login', 'envio@exemplo.com')])
        mensagem = enviados[3][1]
        self.assertEqual(mensagem['To'], 'acesso@pinglevel.com.br')
        self.assertEqual(mensagem['Reply-To'], 'maria@exemplo.com.br')
        self.assertIn('Senac', mensagem.get_content())
        self.assertNotIn('segredo-de-teste', mensagem.as_string())

        class SMTPFora(SMTPFalso):
            def login(self, usuario, senha):
                raise OSError('sem rede')
        with patch.dict(os.environ, config):
            self.assertFalse(pedidos_acesso.avisar_por_email(pedido, smtp=SMTPFora))


class TestRotaPublica(BancoIsolado):
    ORIGEM = 'https://site.exemplo'

    def setUp(self):
        super().setUp()
        arquivo = Path(__file__).with_name('pinglevel_poc.py')
        arvore = ast.parse(arquivo.read_text())
        classe = next(n for n in arvore.body if isinstance(n, ast.ClassDef) and n.name == 'Handler')
        self.limites = {}
        self.auditoria = []
        self.avisos = []

        def permitir(chave, limite, janela):
            self.limites[chave] = self.limites.get(chave, 0) + 1
            return self.limites[chave] <= limite

        aviso = threading.Event()
        self.aviso = aviso
        contexto = {
            'BaseHTTPRequestHandler': BaseHTTPRequestHandler, 'json': json, 'urlsplit': urlsplit, 'parse_qs': parse_qs,
            'threading': threading, 'FRONTEND_URL': self.ORIGEM + '/',
            'token_do_cookie': lambda cookie: cookie, 'obter_usuario': lambda token: None,
            'permitir': permitir, 'auditar': lambda evento, origem, *a, **k: self.auditoria.append(evento),
            'pedidos_acesso': type('M', (), {
                'registrar': staticmethod(pedidos_acesso.registrar),
                'avisar_por_email': staticmethod(lambda pedido: (self.avisos.append(pedido['id']), aviso.set())),
            }),
        }
        exec(compile(ast.Module(body=[classe], type_ignores=[]), str(arquivo), 'exec'), contexto)
        handler = contexto['Handler']
        handler.log_message = lambda *args: None
        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.servidor.shutdown(), self.servidor.server_close(), thread.join(timeout=5)))

    def enviar(self, dados, origem=ORIGEM, ip='198.51.100.1'):
        c = http.client.HTTPConnection('127.0.0.1', self.servidor.server_address[1], timeout=5)
        try:
            headers = {'Content-Type': 'application/json', 'X-Forwarded-For': ip}
            if origem:
                headers['Origin'] = origem
            c.request('POST', '/api/acesso/pedido', body=json.dumps(dados), headers=headers)
            r = c.getresponse()
            return r.status, json.loads(r.read())
        finally:
            c.close()

    def test_salva_avisa_e_nao_exige_login(self):
        status, dados = self.enviar(VALIDO)
        self.assertEqual(status, 201, dados)
        self.assertTrue(self.aviso.wait(5))
        self.assertEqual([p['id'] for p in pedidos_acesso.listar()], self.avisos)
        self.assertIn('pedido_acesso', self.auditoria)

    def test_recusa_outra_origem_e_dados_invalidos(self):
        self.assertEqual(self.enviar(VALIDO, origem='https://outro.exemplo')[0], 403)
        self.assertEqual(self.enviar(VALIDO, origem=None)[0], 403)
        status, dados = self.enviar({**VALIDO, 'email': 'errado'})
        self.assertEqual(status, 400)
        self.assertIn('e-mail', dados['mensagem'])
        self.assertEqual(pedidos_acesso.listar(), [])

    def test_isca_responde_como_sucesso_sem_salvar(self):
        status, _ = self.enviar({**VALIDO, 'site': 'http://spam.exemplo'})
        self.assertEqual(status, 201)
        self.assertEqual(pedidos_acesso.listar(), [])
        self.assertIn('pedido_acesso_isca', self.auditoria)

    def test_limite_por_ip(self):
        for _ in range(3):
            self.assertEqual(self.enviar(VALIDO)[0], 201)
        self.assertEqual(self.enviar(VALIDO)[0], 429)
        self.assertEqual(self.enviar(VALIDO, ip='198.51.100.2')[0], 201)
        self.assertEqual(len(pedidos_acesso.listar()), 4)


if __name__ == '__main__':
    unittest.main()
