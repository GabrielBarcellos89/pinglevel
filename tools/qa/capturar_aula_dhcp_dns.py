"""Aula DHCP e DNS no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_dhcp_dns.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-dhcp-dns)
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT / '.qa/dist')
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-dhcp-dns')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
envios, erros = [], []


def api(route):
    req = route.request
    if req.url.endswith('/api/auth/me'):
        dados = {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
    elif '/api/progresso/me' in req.url:
        dados = {'sucesso': True, 'progresso': {'usuario_id': 17, 'aulas': [], 'laboratorios': [], 'xp_total': 0}}
    elif req.method == 'POST' and '/api/progresso/aula' in req.url:
        envios.append((req.url.split('/api/')[-1], json.loads(req.post_data)))
        dados = {'sucesso': True}
    else:
        return route.abort()
    route.fulfill(status=200, content_type='application/json', body=json.dumps(dados))


log = open(OUT / 'preview.log', 'w')
srv = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(DIST), '--host', '127.0.0.1',
                        '--port', '5179', '--strictPort'], cwd=ROOT / 'frontend', stdout=log, stderr=log)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(.1)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 1440, 'height': 1000})
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim')")
        ctx.route('**/api/**', api)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: erros.append(str(e)))
        avancar = pg.locator('.botao-avancar')
        conferir = pg.get_by_role('button', name='Conferir')

        pg.goto(URL + '/modulos/servicos/dhcp-dns', wait_until='networkidle')

        def responder(pares, erros_esperados=0):
            for grupo, resposta in pares:
                pg.get_by_role('group', name=grupo).get_by_role('button', name=resposta, exact=True).click()
            conferir.click()
            expect(pg.locator('.ag-retorno.erro')).to_have_count(erros_esperados)

        evita, nao = 'O DHCP evita', 'O DHCP não evita'
        responder([('Dois computadores com o mesmo endereço IP.', evita), ('Gateway digitado errado num computador.', evita),
                   ('Cabo de rede desconectado.', evita), ('Computador sem servidor DNS configurado.', evita)], 1)
        expect(avancar).to_be_disabled()
        responder([('Cabo de rede desconectado.', nao)])
        expect(pg.locator('.aula-explica')).to_contain_text('O que o DHCP não resolve')
        pg.screenshot(path=str(OUT / '1-por-que.png'), full_page=True)
        avancar.click()
        expect(pg.locator('.aula-explica')).to_contain_text('As quatro mensagens, em ordem')
        pg.screenshot(path=str(OUT / '2-dora.png'), full_page=True)
        responder([('Qual é a ordem das mensagens?', 'Descoberta, oferta, pedido, confirmação'), ('A descoberta vai para quem?', 'Para todos (broadcast)'),
                   ('Que endereço IP de origem o cliente usa antes de receber o seu?', '0.0.0.0'),
                   ('Por que o DHCP usa UDP, e não TCP?', 'Sem endereço não há conexão TCP; e o pedido vai em broadcast')])
        avancar.click()
        responder([('Que endereço este computador recebeu?', '192.168.40.117'),
                   ('O que significa "lease time 3600"?', 'O empréstimo vale 3600 s (uma hora) e precisa ser renovado'),
                   ('Para onde vai o "adding dns 192.168.40.2"?', 'Para o /etc/resolv.conf (nameserver)'),
                   ('Um colega aparece com 169.254.20.7. O que isso indica?', 'Que não conseguiu endereço de um servidor DHCP')])
        pg.screenshot(path=str(OUT / '3-concessao.png'), full_page=True)
        avancar.click()
        responder([('O que aconteceu? (caso nx)', 'O nome não existe no DNS (veja a grafia)'),
                   ('O que aconteceu? (caso timeout)', 'O computador consulta um servidor DNS errado'),
                   ('O que aconteceu? (caso rede)', 'O problema é antes: o computador nem alcança a rede')])
        pg.screenshot(path=str(OUT / '4-dns.png'), full_page=True)
        avancar.click()
        for rotulo, comando in (('Pedir um endereço', 'dhclient'), ('Ver qual servidor DNS', 'cat /etc/resolv.conf'),
                                ('Perguntar ao DNS', 'nslookup intranet.empresa.local'), ('Testar a comunicação', 'ping intranet.empresa.local')):
            pg.get_by_label(re.compile('^' + re.escape(rotulo))).fill(comando)
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('dhclient eth0')
        ajuda = pg.locator('.af-caso', has_text='Pedir um endereço').locator('.ajuda-comando')
        for botao in ('Pedir ajuda ao Link', 'Ver um exemplo', 'Quero uma pista'):
            ajuda.get_by_role('button', name=botao).click()
        expect(ajuda).to_contain_text('dhclient eth1')
        pg.screenshot(path=str(OUT / '5-comandos-ajuda.png'), full_page=True)
        pg.get_by_label(re.compile('^Pedir um endereço')).fill('dhclient eth0')
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()
        expect(pg.locator('.aula-conclusao')).to_contain_text('Laboratório 9')
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'servicos-dhcp-dns'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
