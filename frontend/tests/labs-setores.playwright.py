"""Labs 2, 5, 6, 7, 8, 9 e 10 no navegador: serviço Python real; só o I/O dos equipamentos (rede simulada) e o login são substituídos.

Uso: PINGLEVEL_QA_DIST=<build> PINGLEVEL_QA_OUT=<pasta> python frontend/tests/labs-setores.playwright.py
Percorre os dois laboratórios digitando o plano e os comandos, confere recusas e grava capturas.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import re
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'app/laboratorios/tests')]
from test_terminal_rede import Engine  # noqa: E402
from test_lan_vlans import Engine as EngineLan  # noqa: E402
from test_servicos_dhcp_dns import Engine as EngineDhcp, Rede  # noqa: E402
from test_primeira_lan import Engine as EngineSala, Sala  # noqa: E402
from laboratorios.api_terminal_rede import despachar_rede  # noqa: E402
from laboratorios.cenarios import (conectando_redes, desafio_empresa, dividindo_rede, enderecos_nomes,  # noqa: E402
    investigando_lan, planejando_empresa, primeira_lan)
from laboratorios.terminal_rede import ServicoRede  # noqa: E402
from laboratorios.tutor_setores import (PERFIL_LAB2, PERFIL_LAB5, PERFIL_LAB6, PERFIL_LAB7, PERFIL_LAB8, PERFIL_LAB9,  # noqa: E402
    PERFIL_LAB10)

URL = 'http://127.0.0.1:5179'
OUT = Path(os.environ.get('PINGLEVEL_QA_OUT', tempfile.mkdtemp(prefix='pinglevel-labs56-qa-')))
OUT.mkdir(parents=True, exist_ok=True)


@contextmanager
def observar_simulado(uid, node):
    # Bastidores do Lab 2: a captura real (tshark) é provada no ensaio CORE; aqui só o formato que o servidor devolve.
    resultado = {}
    yield resultado
    ev = lambda n, tipo, proto, o, d, **c: {'sequencia': n, 'tempo_relativo': n / 100, 'protocolo': proto, 'tipo': tipo,
                                            'origem': o, 'destino': d, 'resumo': tipo, 'campos': c}
    resultado.update({'id': f'cap{time.time_ns()}', 'node_id': node, 'estado': 'concluida', 'mensagem': '', 'eventos': [
        ev(1, 'ARP Request', 'ARP', '192.168.10.20', '192.168.10.10', **{'eth.src': '02:00:00:00:00:02'}),
        ev(2, 'ARP Reply', 'ARP', '192.168.10.10', '192.168.10.20', **{'eth.src': '02:00:00:00:00:01'}),
        ev(3, 'ICMP Echo Request', 'ICMP', '192.168.10.20', '192.168.10.10', **{'icmp.type': '8', 'icmp.seq': '1', 'ip.ttl': '64'}),
        ev(4, 'ICMP Echo Reply', 'ICMP', '192.168.10.10', '192.168.10.20', **{'icmp.type': '0', 'icmp.seq': '1', 'ip.ttl': '64'})]})


class Fixture:
    def __init__(self):
        self.user = {'id': 7, 'login': 'aluno', 'nome': 'Aluno', 'papel': 'aluno'}
        self.servicos = {}
        for prefixo, cenario, perfil in (('/api/lab2/', primeira_lan, PERFIL_LAB2), ('/api/lab5/', dividindo_rede, PERFIL_LAB5), ('/api/lab6/', planejando_empresa, PERFIL_LAB6),
                                         ('/api/lab7/', conectando_redes, PERFIL_LAB7), ('/api/lab9/', investigando_lan, PERFIL_LAB9),
                                         ('/api/lab8/', enderecos_nomes, PERFIL_LAB8), ('/api/lab10/', desafio_empresa, PERFIL_LAB10)):
            engine = (EngineSala(Sala()) if cenario is primeira_lan else EngineLan() if cenario is investigando_lan else EngineDhcp(Rede(cenario), cenario) if cenario in (enderecos_nomes, desafio_empresa)
                      else Engine(cenario))
            if cenario is primeira_lan:
                engine.observar = observar_simulado
            prazo = time.time() + 900
            engine.dados_temporais = lambda lab, prazo=prazo: {'prazo': prazo, 'agora': time.time(), 'segundos_restantes': 900,
                                                               'pode_estender': True, 'extensoes_utilizadas': 0}
            self.servicos[prefixo] = ServicoRede(engine, lambda uid, lab: {'xp_concedido': 100}, cenario=cenario, perfil_tutor=perfil)

    def route(self, route):
        req = route.request
        if req.url.endswith('/api/auth/me'):
            return route.fulfill(json={'usuario': self.user})
        prefixo = next((p for p in self.servicos if f'{p}' in req.url.split('?')[0]), None)
        if not prefixo:
            return route.fulfill(status=404, json={})
        caminho = prefixo + req.url.split(prefixo)[-1]
        data, code = despachar_rede(self.servicos[prefixo], prefixo, self.user, req.method, caminho, (req.post_data or '').encode(),
                                    origem_autorizada=True, limitar=lambda *a: True)
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
                # A apresentação inicial é conferida no Lab 6; nos outros labs ela já foi vista.
                context.add_init_script("localStorage.setItem('pinglevel:link-apresentado:aluno','sim');localStorage.setItem('pinglevel:apresentacao:primeira-lan','sim');localStorage.setItem('pinglevel:apresentacao:dividindo-uma-rede','sim');localStorage.setItem('pinglevel:apresentacao:conectando-redes','sim');localStorage.setItem('pinglevel:apresentacao:investigando-a-lan','sim');localStorage.setItem('pinglevel:apresentacao:enderecos-e-nomes','sim');localStorage.setItem('pinglevel:apresentacao:desafio-rede-da-empresa','sim')")
                context.route('**/api/**', Fixture().route)
                page = context.new_page()
                page.on('pageerror', lambda error: erros.append(str(error)))
                campo = page.locator('#lt-comando')
                tela = page.get_by_role('log')

                def digitar(comando):
                    campo.fill(comando)
                    campo.press('Enter')
                    expect(campo).to_be_enabled()
                    expect(campo).to_have_value('')

                def aba(nome):
                    page.get_by_role('tab', name=nome, exact=True).click()

                # ---- Lab 2 (versão 2): descobrir a rede, PC 2 na rede e o chamado do prefixo do PC 3 ----
                page.goto(URL + '/laboratorios/primeira-lan')
                expect(page.locator('.lt-fila li')).to_have_count(3)
                expect(page.locator('.lr-briefing-link img')).to_be_visible()
                page.screenshot(path=str(OUT / 'lab2-inicio.png'))
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.locator('.lt-topologia')).to_contain_text('REDE A DESCOBRIR')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Descubra o endereço do PC 1')
                expect(page.get_by_test_id('agora-faca')).not_to_contain_text('ip addr show')
                expect(page.locator('.tv-validar')).to_be_disabled()
                expect(page.locator('.tv-validar')).to_contain_text('Conclua as etapas (0 de 4)')
                page.get_by_role('button', name='Preciso de uma pista (1 de 2)').click()
                page.get_by_role('button', name='Outra pista (2 de 2)').click()
                expect(page.locator('.pl-pista')).to_have_count(2)
                expect(page.locator('.pl-pista').nth(1)).to_contain_text('ip addr show')
                page.screenshot(path=str(OUT / 'lab2-pistas.png'))
                expect(page.locator('.lr-lan-pc')).to_have_count(3)
                expect(page.locator('.lr-lan')).not_to_contain_text('192.168.10.40')
                digitar('ip addr show')
                expect(tela).to_contain_text('192.168.10.10/24')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Planeje a rede da sala')
                expect(page.locator('.lr-lan')).to_contain_text('192.168.10.10/24')
                page.get_by_label('Endereço da rede de Sala de estudos').fill('192.168.10.1')
                page.get_by_label('Prefixo de Sala de estudos').fill('/24')
                page.get_by_label('Máscara de Sala de estudos').fill('255.255.0.0')
                page.get_by_role('button', name='Conferir o planejamento').click()
                expect(page.get_by_label('Máscara de Sala de estudos')).to_have_class('erro')
                expect(page.locator('.lr-plano .lt-retorno')).to_contain_text('é um endereço de host')
                page.screenshot(path=str(OUT / 'lab2-plano-erro.png'), full_page=True)
                page.get_by_label('Endereço da rede de Sala de estudos').fill('192.168.10.0')
                page.get_by_label('Máscara de Sala de estudos').fill('255.255.255.0')
                page.get_by_role('button', name='Conferir o planejamento').click()
                expect(page.locator('.lr-plano.conferido')).to_be_visible()
                expect(page.locator('.lt-topologia')).to_contain_text('192.168.10.0/24')
                page.screenshot(path=str(OUT / 'lab2-plano.png'), full_page=True)
                aba('PC 2')
                digitar('ip addr add 192.168.10.20/24 dev eth0')
                digitar('ping 192.168.10.10')
                page.get_by_role('button', name='Bastidores da rede').click()
                bastidores = page.get_by_role('region', name='Bastidores da rede')
                expect(bastidores).to_contain_text('PC 2 $ ping 192.168.10.10')
                expect(bastidores).to_contain_text('PC 2 (192.168.10.20) pergunta a toda a rede: quem tem PC 1 (192.168.10.10)?')
                bastidores.get_by_role('button', name='Ver como o tshark mostra').click()
                expect(bastidores.get_by_label('Saída do tshark')).to_contain_text('Who has 192.168.10.10')
                page.screenshot(path=str(OUT / 'lab2-bastidores.png'))
                page.get_by_role('button', name='Bastidores da rede').click()
                expect(page.locator('.lt-chamado blockquote')).to_contain_text('Não fala com o PC 1')
                expect(page.locator('.lt-chamado[data-chamado]')).to_be_in_viewport()
                casos += 1
                aba('PC 3')
                digitar('ping 192.168.10.10')
                expect(tela).to_contain_text('Network is unreachable')
                digitar('ip addr show')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Qual é a causa?')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab2-chamado.png'), full_page=True)
                page.get_by_label('O prefixo do PC 3 é /28, diferente do /24 da sala: para ele, o PC 1 está em outra rede.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                expect(page.locator('.lt-causa-ok')).to_be_visible()
                digitar('ip addr del 192.168.10.40/28 dev eth0')
                digitar('ip addr add 192.168.10.40/24 dev eth0')
                digitar('ping 192.168.10.10')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                expect(page.locator('.tv-validar.pronta')).to_be_enabled()
                page.screenshot(path=str(OUT / 'lab2-validar.png'))
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                expect(page.locator('img[src*="confetes"]').first).to_be_attached()
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab2-concluido.png'), full_page=True)
                casos += 1

                # ---- Lab 5 ----
                page.goto(URL + '/laboratorios/dividindo-uma-rede')
                expect(page.locator('.lt-fila li')).to_have_count(4)
                page.screenshot(path=str(OUT / 'lab5-missao.png'), full_page=True)
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Planeje o bloco do Financeiro')
                page.get_by_label('Rede de Financeiro').fill('192.168.50.64')
                page.get_by_label('Gateway (1º host) de Financeiro').fill('192.168.50.65')
                page.get_by_label('Broadcast de Financeiro').fill('192.168.50.128')
                page.get_by_role('button', name='Conferir plano').click()
                expect(page.locator('.lr-plano .lt-retorno')).to_contain_text('1 campo')
                expect(page.get_by_label('Broadcast de Financeiro')).to_have_class('erro')
                # Explica sem entregar: régua dos blocos e uma dica para o campo errado.
                expect(page.locator('.lr-regua li')).to_have_count(4)
                expect(page.locator('.lr-dicas-plano li')).to_have_count(1)
                expect(page.locator('.lr-dicas-plano')).to_contain_text('some 63')
                page.wait_for_timeout(400)
                page.screenshot(path=str(OUT / 'lab5-plano-erro.png'), full_page=True)
                page.get_by_label('Broadcast de Financeiro').fill('192.168.50.127')
                page.get_by_role('button', name='Conferir plano').click()
                expect(page.locator('.lr-plano.conferido')).to_be_visible()
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba Roteador')
                casos += 1

                campo.fill('ip addr add 192.168.50.66/26 dev eth0')
                campo.press('Enter')
                expect(page.locator('.lt-recusado')).to_contain_text('só se altera: Roteador')
                aba('Roteador')
                digitar('ip addr add 192.168.50.65/26 dev eth1')
                expect(page.locator('.lt-confirmacao').last).to_contain_text('eth1: 192.168.50.65/26')
                digitar('ip route')
                expect(tela).to_contain_text('192.168.50.64/26 dev eth1')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba PC F1')
                casos += 1

                for pc, ip in (('PC F1', '192.168.50.66'), ('PC F2', '192.168.50.67')):
                    aba(pc)
                    digitar(f'ip addr add {ip}/26 dev eth0')
                    digitar('ip route add default via 192.168.50.65')
                aba('PC F1')
                digitar('ping 192.168.50.67')
                digitar('ping 192.168.50.10')
                expect(page.locator('.lt-chamado blockquote')).to_contain_text('Não fala com ninguém')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab5-chamado.png'), full_page=True)
                casos += 1

                aba('PC V2')
                digitar('ping 192.168.50.10')
                expect(tela).to_contain_text('Network unreachable')
                digitar('ip addr show')
                page.get_by_label('O endereço está fora do bloco do Vendas: pertence ao bloco do Financeiro.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                expect(page.locator('.lt-causa-ok')).to_be_visible()
                digitar('ip addr del 192.168.50.70/26 dev eth0')
                digitar('ip addr add 192.168.50.20/26 dev eth0')
                digitar('ip route add default via 192.168.50.1')
                digitar('ping 192.168.50.66')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.screenshot(path=str(OUT / 'lab5-pronto.png'), full_page=True)
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                casos += 1

                # ---- Lab 6 ----
                page.goto(URL + '/laboratorios/planejando-uma-empresa')
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                cartao = page.locator('.pl-tour-cartao')
                expect(cartao).to_contain_text('Comece por aqui')
                expect(page.locator('.pl-tour-acao')).to_have_count(1)
                page.screenshot(path=str(OUT / 'lab6-apresentacao-1.png'))
                cartao.get_by_role('button', name='Entendi').click()
                expect(cartao).to_contain_text('Esta é a rede')
                cartao.get_by_role('button', name='Começar').click()
                expect(cartao).to_have_count(0)
                assert page.evaluate("localStorage.getItem('pinglevel:apresentacao:planejando-uma-empresa')") == 'sim'
                for setor, prefixo, rede in (('Atendimento', '25', '192.168.80.0'), ('Vendas', '26', '192.168.80.192'), ('Financeiro', '27', '192.168.80.128')):
                    page.get_by_label(f'Prefixo de {setor}').fill(prefixo)
                    page.get_by_label(f'Rede de {setor}').fill(rede)
                page.get_by_role('button', name='Conferir plano').click()
                expect(page.locator('.lr-plano .lt-retorno')).to_contain_text('2 campo')
                expect(page.locator('.lr-dicas-plano li')).to_have_count(2)
                expect(page.locator('.lr-dicas-plano')).to_contain_text('do maior para o menor')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab6-plano-erro.png'), full_page=True)
                page.get_by_label('Rede de Vendas').fill('192.168.80.128')
                page.get_by_label('Rede de Financeiro').fill('192.168.80.192')
                page.get_by_role('button', name='Conferir plano').click()
                expect(page.locator('.lr-plano.conferido')).to_be_visible()
                agora = page.get_by_test_id('agora-faca')
                expect(agora).to_contain_text('Abra a aba Roteador')
                aba('Roteador')
                expect(agora).to_contain_text('Configure a eth0 · Atendimento')
                digitar('ip addr add 192.168.80.1/25 dev eth0')
                expect(agora).to_contain_text('Configure a eth1 · Vendas')
                expect(agora).to_contain_text('Interfaces prontas: 1 de 3')
                digitar('ip addr add 192.168.80.130/26 dev eth1')
                expect(agora).to_contain_text('Corrija a eth1 · Vendas')
                digitar('ip addr del 192.168.80.130/26 dev eth1')
                for linha in ('ip addr add 192.168.80.129/26 dev eth1', 'ip addr add 192.168.80.193/27 dev eth2'):
                    digitar(linha)
                expect(agora).to_contain_text('Abra a aba PC Atendimento')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab6-depois-roteador.png'), full_page=True)
                for pc, ip, gw in (('PC Atendimento', '192.168.80.10/25', '192.168.80.1'), ('PC Vendas', '192.168.80.140/26', '192.168.80.129'),
                                   ('PC Financeiro', '192.168.80.200/27', '192.168.80.193')):
                    aba(pc)
                    expect(agora).to_contain_text(f'{pc} · 1/2: endereço')
                    digitar(f'ip addr add {ip} dev eth0')
                    expect(agora).to_contain_text(f'{pc} · 2/2: rota padrão')
                    digitar(f'ip route add default via {gw}')
                expect(agora).to_contain_text('Abra a aba PC Atendimento')
                aba('PC Atendimento')
                expect(agora).to_contain_text('Teste entre os setores')
                digitar('ping 192.168.80.140')
                digitar('ping 192.168.80.200')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab6-pronto.png'), full_page=True)
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                casos += 1

                # ---- Lab 7 ----
                page.goto(URL + '/laboratorios/conectando-redes')
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                aba('PC A')
                digitar('ping 192.168.20.10')
                expect(tela).to_contain_text('100% packet loss')
                expect(page.locator('.lr-plano-trancado')).to_be_visible()
                expect(page.locator('.lt-suspeitas li')).to_have_count(3)
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Suspeita 1 de 3')
                digitar('ip route')
                aba('R1')
                digitar('ip route')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab7-suspeitas.png'), full_page=True)
                digitar('ping 10.0.0.2')
                expect(page.locator('.lt-suspeitas li.feito')).to_have_count(3)
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Qual é a causa?')
                page.get_by_label('O R1 não tem rota para a rede do PC B.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Planeje as rotas')
                for roteador, destino, via in (('R1', '192.168.20.0/24', '10.0.0.2'), ('R2', '192.168.10.0/24', '10.0.0.1')):
                    page.get_by_label(f'Rede de destino de Rota no {roteador}').fill(destino)
                    page.get_by_label(f'Próximo salto de Rota no {roteador}').fill(via)
                page.get_by_role('button', name='Conferir plano').click()
                expect(page.locator('.lr-plano.conferido')).to_be_visible()
                digitar('ip route add 192.168.20.0/24 via 10.0.0.2')
                expect(page.locator('.lr-roteador', has_text='R1')).to_contain_text('192.168.20.0/24 via 10.0.0.2')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba PC A')
                aba('PC A')
                digitar('ping 192.168.20.10')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba R2')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab7-ida.png'), full_page=True)
                aba('R2')
                digitar('ip route add 192.168.10.0/24 via 10.0.0.1')
                aba('PC A')
                digitar('ping 192.168.20.10')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.screenshot(path=str(OUT / 'lab7-pronto.png'), full_page=True)
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                casos += 1

                # ---- Lab 9 ----
                page.goto(URL + '/laboratorios/investigando-a-lan')
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.locator('.tq-lan-switch')).to_contain_text('eth1 VLAN 20')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba PC F1')
                expect(page.locator('[data-acao="aba-f1"]')).to_have_class(re.compile('gw-proxima-acao'))
                expect(page.locator('.tq-lan .tq-equip.aguardando')).to_contain_text('PC F1')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab9-inicio.png'), full_page=True)
                aba('PC F1')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Fale com o PC F2')
                digitar('ping 192.168.30.22')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Leia a tabela ARP do PC F1')
                digitar('ip neigh show')
                expect(tela).to_contain_text('lladdr 02:16:3e:7d:02:9f')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba Switch')
                expect(page.locator('[data-acao="aba-switch"]')).to_have_class(re.compile('gw-proxima-acao'))
                expect(page.locator('.tq-lan-switch.aguardando')).to_be_visible()
                for rotulo, valor in (('MAC do PC F2 de PC F2', '02:16:3e:7d:02:9f'), ('Porta do switch de PC F2', 'eth3')):
                    page.get_by_label(rotulo).fill(valor)
                    expect(page.get_by_label(rotulo)).to_have_value(valor)
                expect(page.get_by_role('button', name='Conferir investigação')).to_be_enabled()
                page.get_by_role('button', name='Conferir investigação').click()
                expect(page.locator('.lr-plano .lt-retorno')).to_contain_text('bridge fdb show')
                aba('Switch')
                expect(page.locator('.lt-boasvindas')).to_contain_text('bridge link show, bridge fdb show e bridge vlan show')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Leia a tabela MAC do switch')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab9-tabela-mac.png'), full_page=True)
                digitar('bridge fdb show')
                expect(tela).to_contain_text('02:16:3e:7d:02:9f dev eth3')
                page.get_by_role('button', name='Conferir investigação').click()
                expect(page.locator('.lr-plano.conferido')).to_be_visible()
                expect(page.locator('.tq-lan-switch')).to_contain_text('eth3 VLAN 1 · PC F2')
                expect(page.locator('.lt-chamado blockquote')).to_contain_text('O PC V2 não fala com o PC V1')
                digitar('bridge vlan show')
                page.get_by_label('A porta do PC V2 no switch está numa VLAN diferente da do PC V1.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                campo.fill('bridge vlan add dev eth2 vid 20 pvid untagged')
                campo.press('Enter')
                expect(page.locator('.lt-recusado')).to_contain_text('só se altera: eth1')
                digitar('bridge vlan add dev eth1 vid 10 pvid untagged')
                expect(page.locator('.lt-confirmacao').last).to_contain_text('eth1: VLANs 10, 20 (PVID 10)')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('eth1 fora da VLAN 20 · 2 de 2')
                digitar('bridge vlan del dev eth1 vid 20')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Abra a aba PC V2')
                aba('PC V2')
                digitar('ping 192.168.30.11')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Separe o Financeiro do Vendas')
                aba('Switch')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('eth2 na VLAN 20 · 1 de 2')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Hoje a eth2 está na VLAN 1.')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab9-separar.png'), full_page=True)
                for porta in ('eth2', 'eth3'):
                    digitar(f'bridge vlan add dev {porta} vid 20 pvid untagged')
                    digitar(f'bridge vlan del dev {porta} vid 1')
                aba('PC F1')
                digitar('ping 192.168.30.22')
                digitar('ping 192.168.30.11')
                expect(tela).to_contain_text('100% packet loss')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab9-pronto.png'), full_page=True)
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                casos += 1

                # ---- Lab 8 ----
                page.goto(URL + '/laboratorios/enderecos-e-nomes')
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.locator('.lt-chamado header')).to_contain_text('CHAMADO 1 DE 3')
                expect(page.locator('.lt-objetivo')).to_contain_text('automaticamente')
                expect(page.locator('.lt-checklist li.atual')).to_contain_text('Investigar o PC Novo')
                aba('PC Novo')
                digitar('ip addr show')
                page.get_by_label('A interface está ligada, mas o PC ainda não recebeu um endereço do servidor DHCP.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                expect(page.locator('.lt-checklist li.atual')).to_contain_text('Corrigir a configuração do PC Novo')
                digitar('dhclient eth0')
                expect(tela).to_contain_text('adding dns 192.168.40.2')
                expect(page.locator('.lt-estado')).to_contain_text('servidor DNS 192.168.40.2')
                digitar('ping intranet.empresa.local')
                expect(page.locator('.lt-resolvidos')).to_contain_text('Chamado 1 · PC Novo: resolvido.')
                expect(page.locator('.lt-resolvidos')).to_contain_text('Ainda na fila: Chamado 3 · PC Financeiro')
                expect(page.locator('.lt-chamado header')).to_contain_text('CHAMADO 2 DE 3')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab8-chamado2.png'), full_page=True)
                aba('PC Recepção')
                digitar('cat /etc/resolv.conf')
                page.get_by_label('O PC Recepção está configurado com um servidor DNS que não é o da empresa.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                digitar('dhclient eth0')
                digitar('ping intranet.empresa.local')
                aba('PC Financeiro')
                digitar('nslookup impresora.empresa.local')
                expect(tela).to_contain_text('NXDOMAIN')
                page.get_by_label('O nome digitado não existe no DNS: está escrito errado.').check()
                page.get_by_role('button', name='Confirmar causa').click()
                digitar('ping impressora.empresa.local')
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Validar missão')
                page.locator('[data-acao="concluir"]').click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP')
                casos += 1

                # ---- Lab 10 (apresentação; o percurso é ensaiado no CORE) ----
                page.goto(URL + '/laboratorios/desafio-rede-da-empresa')
                expect(page.locator('.lt-fila li')).to_have_count(4)
                expect(page.locator('.lt-missao')).to_contain_text('150 XP')
                page.screenshot(path=str(OUT / 'lab10-missao.png'), full_page=True)
                page.get_by_role('button', name='Iniciar ambiente', exact=True).click()
                expect(page.locator('.lt-chamado header')).to_contain_text('CHAMADO 1 DE 4')
                expect(page.locator('.lt-aberto')).to_contain_text('PC V1')
                expect(page.locator('.tq-equip', has_text='PC V1').locator('em')).to_have_text('abriu o chamado')
                expect(page.locator('.tq-equip', has_text='PC F1').locator('em')).to_have_text('chamado 3 · fila')
                expect(page.locator('.tq-lan-switch', has_text='Switch')).to_contain_text('eth1 VLAN 20 · PC V2')
                expect(page.locator('.tq-lan-coluna .tq-lan-switch', has_text='Intranet')).to_contain_text('gw .60.254')
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / 'lab10-inicio.png'), full_page=True)
                casos += 1
                browser.close()
        finally:
            server.terminate()
    if erros:
        raise SystemExit(f'Erros de página: {erros}')
    print(json.dumps({'aprovado': True, 'casos': casos, 'evidencias': str(OUT)}))


if __name__ == '__main__':
    main()
