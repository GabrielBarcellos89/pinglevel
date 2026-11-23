"""Aula VLSM no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_vlsm.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-vlsm)
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
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-vlsm')
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

        pg.goto(URL + '/modulos/planejamento/vlsm', wait_until='networkidle')
        pg.get_by_role('group', name='Prefixo dos blocos iguais').get_by_role('button', name=re.compile(r'^\/26')).click()
        pg.get_by_role('group', name='Cabem as quatro necessidades').get_by_role('button', name='Não').click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(1)
        pg.get_by_role('group', name='Prefixo dos blocos iguais').get_by_role('button', name=re.compile(r'^\/25')).click()
        conferir.click()
        expect(pg.locator('.av-comparacao .av-faixa')).to_have_count(2)
        pg.screenshot(path=str(OUT / '1-blocos-iguais.png'), full_page=True)
        avancar.click()

        for nome in ('Vendas', 'Atendimento', 'Financeiro', 'Enlace entre roteadores'):
            pg.locator('.av-ordem button', has_text=nome).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('mais endereços')
        pg.get_by_role('button', name='Recomeçar a ordem').click()
        for nome in ('Atendimento', 'Vendas', 'Financeiro', 'Enlace entre roteadores'):
            pg.locator('.av-ordem button', has_text=nome).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.ok')).to_be_visible()
        avancar.click()

        for rede, valor in (('192.168.60.64/26', 'Início válido'), ('192.168.60.32/26', 'Não pode começar aí'),
                            ('192.168.60.96/27', 'Início válido'), ('192.168.60.40/28', 'Não pode começar aí')):
            pg.get_by_role('group', name=f'{rede} é um início válido').get_by_role('button', name=valor).click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()

        plano = {'Atendimento': ('25', '192.168.60.0'), 'Vendas': ('26', '192.168.60.130'), 'Financeiro': ('27', '192.168.60.192'),
                 'Enlace entre roteadores': ('30', '192.168.60.224')}
        for nome, (prefixo, rede) in plano.items():
            pg.get_by_label(f'Prefixo de {nome}').select_option(prefixo)
            pg.get_by_label(f'Rede de {nome}').fill(rede)
        conferir.click()
        expect(pg.locator('.ap-linha small', has_text='múltiplos de 64')).to_be_visible()
        pg.get_by_label('Rede de Vendas').fill('192.168.60.128')
        conferir.click()
        expect(pg.locator('.ag-retorno.ok')).to_contain_text('sem sobreposição')
        expect(pg.locator('.av-faixa span')).to_have_count(4)
        pg.screenshot(path=str(OUT / '4-plano.png'), full_page=True)
        avancar.click()

        pg.get_by_role('group', name='Par sobreposto').get_by_role('button', name='Atendimento × Vendas').click()
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_be_visible()
        pg.get_by_role('group', name='Par sobreposto').get_by_role('button', name='Vendas × Financeiro').click()
        conferir.click()
        expect(pg.locator('.ag-retorno.ok')).to_contain_text('.192')
        pg.screenshot(path=str(OUT / '5-sobreposicao.png'), full_page=True)
        avancar.click()
        expect(pg.locator('.aula-conclusao')).to_contain_text('Laboratório 6')
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'planejamento-vlsm'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
