"""Servidor HTTP sintético para conferir o frontend sem tocar em produção.

Reutiliza o Handler real e o banco temporário dos testes do backend. Não inicia CORE.
Uso: /opt/packetlab/venv/bin/python -B frontend/tests/servidor_ipv4_isolado.py
"""
import importlib
import json
import os
import signal
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'app/prototipo'))
testes = importlib.import_module('testar_http_retomada_ipv4')


def main():
    caso = testes.TestHTTPRetomadaIPv4('test_percurso_completo_por_http')
    caso.setUp()
    handler = caso.servidor.RequestHandlerClass
    def usuario_sintetico(token):
        if token not in ('usuario-1', 'usuario-2'):
            return None
        return {'id': int(token[-1]), 'login': token, 'nome': 'Aluno de teste',
                'papel': 'aluno', 'troca_senha_obrigatoria': False}
    handler.usuario_da_requisicao.__globals__['obter_usuario'] = usuario_sintetico
    post_original = handler.do_POST
    def post_teste(self):
        if self.path == '/__teste__/reset':
            # Exclusivo do servidor loopback com banco temporário.
            with testes.progresso._conectar() as c:
                c.execute('DELETE FROM eventos_xp')
                c.execute('DELETE FROM progresso_aulas')
            self.enviar_json({'sucesso': True})
            return
        if self.path == '/__teste__/legado':
            try:
                dados = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                if not isinstance(dados, dict) or set(dados) != {'concluida'} or type(dados['concluida']) is not bool:
                    raise ValueError('Informe somente concluida como booleano.')
                concluida = dados['concluida']
                with testes.progresso._conectar() as c:
                    c.execute('''
                        INSERT INTO progresso_aulas (
                            usuario_id, aula_id, modulo_id, etapa_atual, percentual,
                            concluida, iniciado_em, atualizado_em, concluida_em
                        ) VALUES (1, 'enderecamento-ipv4', 'enderecamento', 5, 100, ?, 1, 2, ?)
                    ''', (int(concluida), 2 if concluida else None))
                    if concluida:
                        c.execute('''
                            INSERT INTO eventos_xp (
                                usuario_id, origem_tipo, origem_id, pontos, descricao, criado_em
                            ) VALUES (1, 'aula', 'enderecamento-ipv4', 100, 'Fixture legada sintética', 2)
                        ''')
            except (TypeError, ValueError) as erro:
                self.enviar_json({'sucesso': False, 'mensagem': str(erro)}, 400)
                return
            self.enviar_json({'sucesso': True})
            return
        post_original(self)
    handler.do_POST = post_teste
    pasta = Path(os.environ['TMPDIR']) / 'retomada-ipv4-frontend'
    pasta.mkdir(exist_ok=True)
    dados = {'api': f'http://127.0.0.1:{caso.servidor.server_address[1]}'}
    (pasta / 'api-teste.json').write_text(json.dumps(dados))
    print('API_ISOLADA_PRONTA ' + dados['api'], flush=True)
    parar = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: parar.set())
    signal.signal(signal.SIGINT, lambda *_: parar.set())
    try:
        parar.wait()
    finally:
        caso.doCleanups()


if __name__ == '__main__':
    main()
