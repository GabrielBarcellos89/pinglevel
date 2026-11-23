"""Aula Plano de endereçamento no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_plano.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-plano)
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
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-plano')
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

        pg.goto(URL + '/modulos/planejamento/enderecamento', wait_until='networkidle')
        respostas = {'10.20.5.4': 'Privado', '172.32.0.5': 'Público', '192.168.1.10': 'Privado', '8.8.8.8': 'Público',
                     '172.31.200.1': 'Privado', '192.169.0.1': 'Privado'}
        for ip, tipo in respostas.items():
            pg.get_by_role('group', name=f'Tipo de {ip}').get_by_role('button', name=tipo, exact=True).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(1)
        expect(avancar).to_be_disabled()
        pg.get_by_role('group', name='Tipo de 192.169.0.1').get_by_role('button', name='Público', exact=True).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '1-publico-privado.png'), full_page=True)
        avancar.click()

        for ip, papel in (('127.0.0.1', 'Loopback'), ('169.254.12.7', 'Link-local'), ('0.0.0.0', 'Ainda sem endereço'),
                          ('192.168.10.255', 'Broadcast')):
            pg.get_by_role('group', name=f'Papel de {ip}').get_by_role('button', name=re.compile(papel)).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()

        pg.get_by_label('Prefixo /24').fill('26')
        expect(pg.locator('.ap-controle dl')).to_contain_text('62')
        expect(pg.locator('.ap-controle .ap-faixa span')).to_have_count(4)
        for prefixo, valor in ((26, '62'), (27, '30'), (28, '14')):
            pg.get_by_label(f'/{prefixo}', exact=True).fill(valor)
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '3-tamanho.png'), full_page=True)
        avancar.click()

        for setor, prefixo in (('Vendas', '/26'), ('Atendimento', '/25'), ('Diretoria', '/28'), ('Suporte', '/28')):
            pg.get_by_role('group', name=f'Prefixo para {setor}').get_by_role('button', name=re.compile('^\\' + prefixo)).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('não comporta 15')
        pg.get_by_role('group', name='Prefixo para Diretoria').get_by_role('button', name=re.compile(r'^\/27')).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '4-prefixo.png'), full_page=True)
        avancar.click()

        for i, (rede, broadcast) in enumerate((('192.168.50.0', '192.168.50.63'), ('192.168.50.64', '192.168.50.127'),
                                               ('192.168.50.128', '192.168.50.191'), ('192.168.50.192', '192.168.50.256')), 1):
            pg.get_by_label(f'Rede do bloco {i}').fill(rede)
            pg.get_by_label(f'Broadcast do bloco {i}').fill(broadcast)
        conferir.click()
        expect(pg.locator('.ap-linha small')).to_contain_text('completo')
        pg.get_by_label('Broadcast do bloco 4').fill('192.168.50.255')
        conferir.click()
        expect(pg.locator('.ag-retorno.ok')).to_contain_text('192.168.50.1 a 192.168.50.62')
        pg.screenshot(path=str(OUT / '5-divisao.png'), full_page=True)
        avancar.click()
        expect(pg.locator('.aula-conclusao')).to_contain_text('Laboratório 5')
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'planejamento-enderecamento'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
