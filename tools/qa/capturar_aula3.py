"""Aula 3 (IPv4) no build candidato: confere /8 e /16 na leitura do prefixo e a ponte para o terminal na conclusão.

Login, progresso e estado da aula são simulados; qualquer escrita é bloqueada e reprovada.
Uso: capturar_aula3.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula3)
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT / '.qa/dist')
OUT = Path(args[1] or ROOT / '.qa/capturas/aula3')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
ESTADO = {'aula_id': 'enderecamento-ipv4', 'versao_estado': 1, 'versao_conteudo': 1, 'revisao': 8, 'modo': 'andamento',
          'concluida': False, 'etapa_retomada': 5, 'etapa_visitada': 5, 'etapa_liberada': 5, 'legado_sem_respostas': False,
          'respostas': {'previsao': 'gateway', 'pratica': {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'},
                        'interpretacao': 'mac-gateway'},
          'validacoes': {'pratica': {'status': 'aprovada'}, 'interpretacao': {'status': 'aprovada'}}}
escritas, erros = [], []


def api(route):
    req = route.request
    if req.method != 'GET':
        escritas.append(f'{req.method} {req.url}')
        return route.abort()
    if req.url.endswith('/api/auth/me'):
        dados = {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
    elif '/api/progresso/me' in req.url:
        dados = {'sucesso': True, 'progresso': {'usuario_id': 17, 'aulas': [], 'laboratorios': [], 'xp_total': 0}}
    elif '/api/progresso/aula/estado' in req.url:
        dados = {'sucesso': True, 'estado': ESTADO}
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
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim');localStorage.setItem('pinglevel:link-apresentado:ipv4-previa','sim')")
        ctx.route('**/api/**', api)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: erros.append(str(e)))

        pg.goto(URL + '/modulos/enderecamento/ipv4/previa', wait_until='networkidle')
        pg.get_by_role('heading', name='Como dois computadores entram na mesma rede?', exact=True).wait_for(timeout=6000)
        for _ in range(3):
            pg.locator('.aula-navegacao .botao-avancar').click()
        escolha = pg.get_by_label('Prefixo em estudo', exact=True)
        opcoes = escolha.locator('option').evaluate_all('(els)=>els.map(e=>Number(e.value))')
        assert opcoes == [8, 16, *range(22, 33)], opcoes
        escolha.select_option('16')
        expect(pg.get_by_test_id('host-capacity')).to_have_text('65.534')
        expect(pg.get_by_test_id('prefixo-largo')).to_contain_text('192.168.20.10')
        pg.screenshot(path=str(OUT / 'cena-capacidade-16.png'), full_page=True)
        escolha.select_option('8')
        expect(pg.get_by_test_id('host-capacity')).to_have_text('16.777.214')
        escolha.select_option('22')
        expect(pg.get_by_test_id('host-capacity')).to_have_text('1.022')
        for _ in range(2):
            pg.locator('.aula-navegacao .botao-avancar').click()
        origem = pg.get_by_label('Prefixo da rede de origem', exact=True)
        assert origem.locator('option').evaluate_all('(els)=>els.map(e=>Number(e.value))') == list(range(22, 33))

        pg.goto(URL + '/modulos/enderecamento/ipv4', wait_until='networkidle')
        ponte = pg.get_by_role('region', name='Como observar isso num computador')
        expect(ponte).to_contain_text('ICMP')
        expect(pg.locator('main')).not_to_contain_text('observar ARP')
        ponte.scroll_into_view_if_needed()
        pg.screenshot(path=str(OUT / 'conclusao.png'), full_page=True)
        b.close()
finally:
    srv.terminate()
if escritas or erros:
    raise SystemExit(f'escritas: {escritas} · erros: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
