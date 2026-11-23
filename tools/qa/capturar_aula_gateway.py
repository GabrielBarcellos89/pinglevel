"""Aula Gateway e entrega local no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_gateway.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-gateway)
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
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-gateway')
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

        pg.goto(URL + '/modulos/fundamentos/gateway', wait_until='networkidle')
        expect(avancar).to_be_disabled()
        pg.get_by_role('button', name='Enviar ao Servidor').click()
        expect(pg.locator('.ag-decisao')).to_contain_text('outra rede')
        pg.get_by_role('button', name='Enviar ao PC Colega').click()
        expect(pg.locator('.ag-decisao')).to_contain_text('entrega é direta')
        pg.screenshot(path=str(OUT / '1-dois-caminhos.png'), full_page=True)
        avancar.click()

        for destino, caminho in (('PC Colega', 'Entrega direta'), ('Servidor', 'Entrega direta'),
                                 ('Impressora', 'Entrega direta'), ('Um site na Internet', 'Pelo gateway')):
            pg.get_by_role('group', name=f'Caminho até {destino}').get_by_role('button', name=caminho).click()
        pg.get_by_role('button', name='Conferir previsões').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(1)
        expect(avancar).to_be_disabled()
        pg.get_by_role('group', name='Caminho até Servidor').get_by_role('button', name='Pelo gateway').click()
        pg.get_by_role('button', name='Conferir previsões').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '2-prever.png'), full_page=True)
        avancar.click()

        pg.get_by_role('button', name='192.168.20.1').click()
        expect(pg.get_by_role('status')).to_contain_text('não a alcança diretamente')
        expect(avancar).to_be_disabled()
        pg.get_by_role('button', name='192.168.10.1').click()
        expect(pg.get_by_role('status')).to_contain_text('Isso!')
        pg.screenshot(path=str(OUT / '3-gateway.png'), full_page=True)
        avancar.click()

        proximo = pg.get_by_role('button', name='Próximo passo')
        while proximo.is_enabled():
            proximo.click()
        expect(pg.locator('.ag-passo')).to_contain_text('Ida e volta completas')
        expect(avancar).to_be_disabled()
        pg.get_by_role('button', name='Remover o gateway do servidor').click()
        while proximo.is_enabled():
            proximo.click()
        expect(pg.locator('.ag-passo-falha')).to_contain_text('a volta não')
        pg.screenshot(path=str(OUT / '4-ida-e-volta-falha.png'), full_page=True)
        avancar.click()

        for pergunta, resposta in (('Por que o PC Colega', 'Porque está na mesma rede'),
                                   ('Se o PC Atendimento usar', 'Não funciona'),
                                   ('Na etapa anterior', 'Porque o Servidor não tinha caminho de volta')):
            pg.get_by_role('group', name=pergunta).get_by_label(resposta).check()
        pg.get_by_role('button', name='Conferir respostas').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '5-rota-padrao.png'), full_page=True)
        avancar.click()

        expect(pg.locator('.aula-conclusao')).to_contain_text('ip route')
        pg.screenshot(path=str(OUT / '6-conclusao.png'), full_page=True)
        pg.set_viewport_size({'width': 390, 'height': 844})
        pg.screenshot(path=str(OUT / '6-conclusao-celular.png'), full_page=True)
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')

        # Celular: o menu lateral começa recolhido e não cobre a aula.
        celular = b.new_context(viewport={'width': 390, 'height': 844})
        celular.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim')")
        celular.route('**/api/**', api)
        pc = celular.new_page()
        pc.goto(URL + '/modulos/fundamentos/gateway', wait_until='networkidle')
        expect(pc.locator('.aplicacao')).to_have_class(re.compile('menu-recolhido'))
        expect(pc.get_by_role('heading', name='Dois destinos, dois caminhos')).to_be_in_viewport()
        pc.screenshot(path=str(OUT / 'celular-inicio.png'))
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'fundamentos-gateway'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
