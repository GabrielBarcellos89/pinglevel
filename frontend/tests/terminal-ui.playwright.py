"""Lab 4 no navegador: serviço Python real; só o I/O dos três PCs (rede simulada) e o login são substituídos.

Uso: PINGLEVEL_QA_DIST=<build> PINGLEVEL_QA_OUT=<pasta> python frontend/tests/terminal-ui.playwright.py
Atende os três chamados digitando os comandos, confere recusas e grava capturas em computador e celular.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'app/laboratorios/tests')]
from test_terminal_guiado import Engine  # noqa: E402
from laboratorios.api_terminal_guiado import despachar_terminal  # noqa: E402
from laboratorios.terminal_guiado import ServicoTerminal  # noqa: E402

URL = 'http://127.0.0.1:5179'
OUT = Path(os.environ.get('PINGLEVEL_QA_OUT', tempfile.mkdtemp(prefix='pinglevel-lab4-qa-')))
OUT.mkdir(parents=True, exist_ok=True)


class Fixture:
    def __init__(self):
        self.engine = Engine()
        prazo = time.time() + 900
        self.engine.dados_temporais = lambda lab: {'prazo': prazo, 'agora': time.time(), 'segundos_restantes': 900,
                                                   'pode_estender': True, 'extensoes_utilizadas': 0}
        self.service = ServicoTerminal(self.engine, lambda uid, lab: {'xp_concedido': 100})
        self.user = {'id': 7, 'login': 'aluno', 'nome': 'Aluno', 'papel': 'aluno'}

    def route(self, route):
        req = route.request
        if req.url.endswith('/api/auth/me'):
            return route.fulfill(json={'usuario': self.user})
        if '/api/terminal/' not in req.url:
            return route.fulfill(status=404, json={})
        data, code = despachar_terminal(self.service, self.user, req.method, '/api/terminal/' + req.url.split('/api/terminal/')[-1],
                                        (req.post_data or '').encode(), origem_autorizada=True, limitar=lambda *a: True)
        return route.fulfill(status=code, json=data)


def main():
    erros, casos = [], 0
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
                page.goto(URL + '/laboratorios/configure-pelo-terminal')
                expect(page.locator('.lt-fila li')).to_have_count(3)
                expect(page.locator('.aplicacao .sidebar')).to_be_visible()
                page.screenshot(path=str(OUT / 'lab4-missao-desktop.png'), full_page=True)
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                # A tela de missão dá lugar à área de trabalho, em modo foco (sem menu lateral).
                expect(page.locator('.lt-missao')).to_have_count(0)
                expect(page.locator('.aplicacao .sidebar')).to_be_hidden()
                expect(page.get_by_test_id('agora-faca')).to_contain_text('ip addr show')
                expect(page.get_by_role('button', name='PC Novo: sem endereço; Chamado aberto')).to_be_visible()
                page.wait_for_timeout(400)  # transição do menu lateral
                # Apresentação: primeiro acende o Agora faça e o chamado, depois a topologia; vista uma vez só.
                cartao = page.locator('.pl-tour-cartao')
                expect(cartao).to_contain_text('Comece por aqui')
                expect(page.locator('.pl-tour-acao')).to_have_count(1)
                page.screenshot(path=str(OUT / 'lab4-apresentacao-1.png'))
                cartao.get_by_role('button', name='Entendi').click()
                expect(cartao).to_contain_text('Esta é a rede')
                page.screenshot(path=str(OUT / 'lab4-apresentacao-2.png'))
                cartao.get_by_role('button', name='Começar').click()
                expect(cartao).to_have_count(0)
                assert page.evaluate("localStorage.getItem('pinglevel:apresentacao:lab4')") == 'sim'
                page.screenshot(path=str(OUT / 'lab4-inicio-desktop.png'), full_page=True)
                casos += 1

                campo = page.locator('#lt-comando')
                tela = page.get_by_role('log')

                def digitar(comando):
                    campo.fill(comando)
                    campo.press('Enter')
                    expect(campo).to_be_enabled()
                    expect(campo).to_have_value('')

                def causa(texto):
                    page.get_by_label(texto).check()
                    page.get_by_role('button', name='Confirmar causa').click()

                digitar('ping 192.168.10.12')
                expect(tela).to_contain_text('suporte@pc-novo:~$ ping 192.168.10.12')
                expect(tela).to_contain_text('Network unreachable')
                digitar('ip addr show')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Qual é a causa?')
                casos += 1

                # Alterar antes de identificar a causa é recusado; o interpretador recusa o que não conhece.
                campo.fill('ip addr add 192.168.10.30/24 dev eth0')
                campo.press('Enter')
                expect(page.locator('.lt-recusado')).to_contain_text('qual é a causa')
                campo.fill('ip a; reboot')
                campo.press('Enter')
                expect(page.locator('.lt-recusado')).to_contain_text('Use apenas')
                causa('O cabo de rede está desconectado.')
                expect(page.locator('.lt-retorno')).to_contain_text('UP')
                causa('A interface está ativa, mas não tem endereço IPv4.')
                expect(page.locator('.lt-causa-ok')).to_contain_text('Causa identificada')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('ip addr add <endereço>/<prefixo> dev eth0')
                casos += 1

                digitar('ip addr add 192.168.10.30/24 dev eth0')
                expect(page.locator('.lt-confirmacao').last).to_contain_text('eth0: 192.168.10.30/24 · rota padrão: nenhuma')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('ip route add default via <gateway>')
                digitar('ip route add default via 192.168.10.1')
                campo.press('ArrowUp')
                expect(campo).to_have_value('ip route add default via 192.168.10.1')
                campo.fill('')
                digitar('ip route')
                expect(tela).to_contain_text('default via 192.168.10.1 dev eth0')
                expect(tela).not_to_contain_text('172.30')
                digitar('ping 192.168.20.10')
                # Chamado 1 resolvido: o terminal passa sozinho para o PC Financeiro, com a ajuda reduzida.
                expect(page.get_by_role('tab', name='PC Financeiro chamado')).to_have_attribute('aria-selected', 'true')
                expect(page.locator('.lt-chamado blockquote')).to_contain_text('não alcança o servidor')
                expect(page.locator('.lt-ajuda-chamado')).to_contain_text('Compare')
                casos += 1

                digitar('ip route')
                expect(tela).to_contain_text('default via 192.168.10.11')
                page.get_by_role('tab', name='PC Novo').click()
                expect(tela).to_contain_text('suporte@pc-novo:~$ ip route')
                campo.fill('ip route del default')
                campo.press('Enter')
                expect(page.locator('.lt-recusado')).to_contain_text('chamado aberto é do PC Financeiro')
                page.get_by_role('tab', name='PC Financeiro chamado').click()
                causa('A rota padrão aponta para um computador, não para o roteador.')
                for comando in ('ip route del default', 'ip route add default via 192.168.10.1'):
                    digitar(comando)
                page.screenshot(path=str(OUT / 'lab4-chamado2-desktop.png'), full_page=True)
                digitar('ping 192.168.20.10')
                expect(page.get_by_role('tab', name='PC Recepção chamado')).to_have_attribute('aria-selected', 'true')
                expect(page.locator('.lt-ajuda-chamado')).to_have_count(0)
                casos += 1

                digitar('ping 192.168.20.10')
                expect(tela).to_contain_text('100% packet loss')
                digitar('ip addr show')
                causa('O prefixo é largo demais: o servidor parece estar na mesma rede.')
                digitar('ip addr del 192.168.10.11/16 dev eth0')
                digitar('ip addr add 192.168.10.11/24 dev eth0')
                expect(page.locator('.lt-confirmacao').last).to_contain_text('rota padrão: nenhuma')
                digitar('ip route add default via 192.168.10.1')
                digitar('ping 192.168.20.10')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.screenshot(path=str(OUT / 'lab4-pronto-desktop.png'), full_page=True)
                casos += 1

                page.get_by_role('button', name='Sair do modo foco').click()
                expect(page.locator('.aplicacao .sidebar')).to_be_visible()
                page.get_by_role('button', name='Modo foco').click()
                for largura, altura in ((390, 844), (1024, 700), (1366, 768), (1920, 1080)):
                    page.set_viewport_size({'width': largura, 'height': altura})
                    expect(campo).to_be_attached()
                    page.screenshot(path=str(OUT / f'lab4-terminal-{largura}.png'), full_page=True)
                page.set_viewport_size({'width': 1600, 'height': 1000})
                page.evaluate('window.scrollTo(0, 0)')
                casos += 1

                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                expect(page.get_by_role('button', name='Iniciar novo treino')).to_be_visible()
                page.wait_for_timeout(400)
                page.screenshot(path=str(OUT / 'lab4-concluido-desktop.png'), full_page=True)
                casos += 1
                browser.close()
        finally:
            server.terminate()
    if erros:
        raise SystemExit(f'Erros de página: {erros}')
    print(json.dumps({'aprovado': True, 'casos': casos, 'evidencias': str(OUT)}))


if __name__ == '__main__':
    main()
