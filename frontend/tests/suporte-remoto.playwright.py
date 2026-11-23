"""Teste de carga (demonstração "Suporte remoto") no navegador: atividade do aluno e painel do professor.

Serviço Python real com a rede simulada de test_suporte_remoto; o SSH e a impressão reais são provados no ensaio CORE
(tools/qa/ensaio_core_suporte.py). Uso: PINGLEVEL_QA_DIST=… PINGLEVEL_QA_OUT=… python frontend/tests/suporte-remoto.playwright.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'app/laboratorios/tests')]
from test_suporte_remoto import Engine  # noqa: E402
from laboratorios import painel_carga  # noqa: E402
from laboratorios.api_terminal_rede import despachar_rede  # noqa: E402
from laboratorios.cenarios import suporte_remoto  # noqa: E402
from laboratorios.terminal_rede import ServicoRede  # noqa: E402
from laboratorios.tutor_setores import PERFIL_SUPORTE  # noqa: E402

URL = 'http://127.0.0.1:5179'
OUT = Path(os.environ.get('PINGLEVEL_QA_OUT', tempfile.mkdtemp(prefix='pinglevel-carga-qa-')))
OUT.mkdir(parents=True, exist_ok=True)


class Fixture:
    def __init__(self):
        self.user = {'id': 7, 'login': 'aluno', 'nome': 'Aluno', 'papel': 'administrador'}
        self.engine = Engine()
        prazo = time.time() + 900
        self.engine.dados_temporais = lambda lab: {'prazo': prazo, 'agora': time.time(), 'segundos_restantes': 900,
                                                   'pode_estender': True, 'extensoes_utilizadas': 0}
        self.engine.criacoes = [(int(time.time()) - 60 + i * 5, 'suporte-remoto', s) for i, s in enumerate((8.4, 12.1, 29.3, 31.0))]
        self.servico = ServicoRede(self.engine, lambda uid, lab: {'xp_concedido': 0}, cenario=suporte_remoto, perfil_tutor=PERFIL_SUPORTE)

    def route(self, route):
        req = route.request
        url = req.url.split('?')[0]
        if url.endswith('/api/auth/me'):
            return route.fulfill(json={'usuario': self.user})
        if url.endswith('/api/painel-carga'):
            return route.fulfill(json={'sucesso': True, **painel_carga.coletar(self.engine), 'alunos': self.servico.painel()})
        if '/api/carga/' not in url:
            return route.fulfill(json={'sucesso': True, 'progresso': {'aulas': [], 'laboratorios': []}})
        caminho = '/api/carga/' + url.split('/api/carga/')[-1]
        data, code = despachar_rede(self.servico, '/api/carga/', self.user, req.method, caminho, (req.post_data or '').encode(),
                                    origem_autorizada=True, limitar=lambda *a: True)
        return route.fulfill(status=code, body=json.dumps(data), content_type='application/json')


def main():
    erros = []
    dist = os.environ.get('PINGLEVEL_QA_DIST', 'dist')
    with open(OUT / 'vite.log', 'w') as log:
        server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', dist, '--host', '127.0.0.1',
                                   '--port', '5179', '--strictPort'], cwd=ROOT / 'frontend', stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(URL, timeout=1)
                    break
                except Exception:
                    time.sleep(.1)
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get('PINGLEVEL_QA_BROWSER'), args=['--no-sandbox'])
                context = browser.new_context(viewport={'width': 1600, 'height': 1000}, service_workers='block')
                context.add_init_script("localStorage.setItem('pinglevel:link-apresentado:aluno','sim')")
                fixture = Fixture()
                context.route('**/api/**', fixture.route)
                page = context.new_page()
                page.on('pageerror', lambda error: erros.append(str(error)))
                campo = page.locator('#lt-comando')

                def digitar(comando):
                    campo.fill(comando)
                    campo.press('Enter')
                    expect(campo).to_be_enabled()
                    expect(campo).to_have_value('')

                page.goto(URL + '/')
                expect(page.get_by_role('link', name='Teste de carga')).to_be_visible()
                expect(page.get_by_role('link', name='Painel de carga')).to_be_visible()
                page.get_by_role('link', name='Teste de carga').click()
                expect(page.locator('.lt-fila li')).to_have_count(3)
                page.screenshot(path=str(OUT / 'carga-inicio.png'), full_page=True)
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.get_by_role('tab')).to_have_count(1)
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Entre no Financeiro B por SSH')
                expect(page.locator('.tq-equip')).to_have_count(6)
                expect(page.locator('.tq-equip.voce')).to_contain_text('T.I.')
                expect(page.locator('.tq-equip.gw-errado')).to_contain_text('Financeiro B')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'carga-topologia.png'))
                digitar('ssh suporte@192.168.20.21')
                expect(page.locator('label.lt-ps1')).to_have_text('senha:')
                expect(campo).to_have_attribute('type', 'password')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Digite a senha')
                digitar('suporte123')
                expect(page.locator('.tq-equip.remoto')).to_contain_text('Financeiro B')
                expect(page.locator('label.lt-ps1')).to_have_text('suporte@financeiro-b:~$')
                expect(campo).to_have_attribute('type', 'text')
                expect(page.get_by_role('log')).not_to_contain_text('suporte123\n')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Corrija o gateway')
                digitar('ip route')
                expect(page.get_by_role('log')).to_contain_text('default via 192.168.20.254')
                digitar('curl http://192.168.10.50')
                expect(page.get_by_role('log')).to_contain_text('A página da impressora não abriu')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'carga-ssh.png'))
                digitar('ip route del default')
                digitar('ip route add default via 192.168.20.1')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Imprima uma folha')
                expect(page.locator('.tq-equip.gw-errado')).to_have_count(0)
                digitar('curl http://192.168.10.50')
                expect(page.get_by_role('log')).to_contain_text('Folhas impressas: 0')
                digitar('curl -d "texto=Relatorio do Financeiro" http://192.168.10.50/imprimir')
                expect(page.locator('.lr-folhas li')).to_have_count(1)
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                digitar('exit')
                expect(page.locator('label.lt-ps1')).to_have_text('suporte@ti:~$')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'carga-pronto.png'))

                page.goto(URL + '/administrador/painel-carga')
                expect(page.locator('.pc-mural li')).to_have_count(1)
                expect(page.locator('.pc-mural')).to_contain_text('Relatorio do Financeiro')
                expect(page.locator('.pc-tabela tbody tr')).to_have_count(1)
                page.wait_for_timeout(4500)  # duas leituras: a CPU e os gráficos precisam de dois pontos
                page.screenshot(path=str(OUT / 'carga-painel.png'), full_page=True)
                browser.close()
        finally:
            server.terminate()
    if erros:
        raise AssertionError(erros)
    print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))


if __name__ == '__main__':
    main()
