"""Capturas da topologia do Lab 3 em vários tamanhos, antes e depois de consultar o roteador.

Serviço Python real com I/O dos nós e login simulados; não toca no servidor real nem no CORE.
Uso: capturar_lab3.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/lab3-topologia)
Salva PNGs e geometria.json (posição de cada nó e rótulo relativa ao mapa)."""
import json, re, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'app/laboratorios/tests')]
from test_gateway_guiado import setup_service
from laboratorios.api_gateway_guiado import despachar_gateway
from playwright.sync_api import sync_playwright, expect

args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT/'.qa/dist')
OUT = Path(args[1] or ROOT/'.qa/capturas/lab3-topologia')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
TAMANHOS = [(1600, 1000), (1280, 800), (1024, 700), (390, 844)]

class Fixture:
    def __init__(self):
        self.service, self.engine, _, _ = setup_service()
        prazo = time.time() + 900
        self.engine.dados_temporais = lambda lab: {'prazo': prazo, 'agora': time.time(), 'segundos_restantes': 900, 'pode_estender': True, 'extensoes_utilizadas': 0}
        self.user = {'id': 7, 'login': 'aluno', 'nome': 'Aluno', 'papel': 'aluno'}
    def route(self, route):
        req = route.request
        if req.url.endswith('/api/auth/me'):
            return route.fulfill(json={'usuario': self.user})
        if '/api/gateway/' not in req.url:
            return route.fulfill(status=404, json={})
        data, code = despachar_gateway(self.service, self.user, req.method, '/api/gateway/'+req.url.split('/api/gateway/')[-1],
                                       (req.post_data or '').encode(), origem_autorizada=True, limitar=lambda *a: True)
        return route.fulfill(status=code, json=data)

def geometria(page):
    return page.evaluate("""() => { const m=document.querySelector('.gw-mapa').getBoundingClientRect();
      const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.left-m.left),Math.round(b.top-m.top),Math.round(b.width),Math.round(b.height)]};
      const o={mapa:[Math.round(m.width),Math.round(m.height)]};
      document.querySelectorAll('.gw-mapa .gw-equipamento, .gw-mapa .gw-interface, .gw-mapa .gw-porta').forEach(e=>o[(e.className.match(/gw-(no-\\d|interface-\\w+|porta-\\w+)/)||[])[1]+':'+e.textContent.trim().slice(0,24)]=r(e)); return o }""")

log = open(OUT/'preview.log', 'w')
srv = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(DIST), '--host', '127.0.0.1', '--port', '5179', '--strictPort'],
                       cwd=ROOT/'frontend', stdout=log, stderr=log)
try:
    for _ in range(100):
        try: urllib.request.urlopen(URL, timeout=1); break
        except Exception: time.sleep(.1)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 1600, 'height': 1000}, service_workers='block')
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:aluno','sim');localStorage.setItem('pinglevel:apresentacao:lab3','sim')")
        fx = Fixture(); ctx.route('**/api/**', fx.route)
        pg = ctx.new_page(); erros = []; pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.goto(URL + '/laboratorios/saindo-da-rede-local')
        pg.get_by_role('button', name='Iniciar ambiente', exact=True).click()
        expect(pg.locator('.gw-no-5')).to_be_enabled()
        geo = {}
        for fase in ('antes', 'depois'):
            if fase == 'depois':
                pg.set_viewport_size({'width': 1600, 'height': 1000}); pg.wait_for_timeout(250)
                pg.locator('.gw-no-5').click()
                expect(pg.get_by_test_id('interfaces-roteador')).to_contain_text('eth0')
            for w, h in TAMANHOS:
                pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_timeout(250)
                alt = pg.locator('.pl-topologia-alternar')
                if alt.is_visible() and alt.get_attribute('aria-expanded') == 'false': alt.click()
                topo = pg.get_by_role('region', name='Topologia de duas redes')
                topo.scroll_into_view_if_needed()
                topo.screenshot(path=str(OUT/f'topologia-{fase}-{w}x{h}.png'))
                geo[f'{fase}-{w}x{h}'] = geometria(pg)
                if w < 651:
                    pg.locator('.gw-no-5').scroll_into_view_if_needed(); pg.wait_for_timeout(150)
                    pg.locator('.pl-topologia-fixa').screenshot(path=str(OUT/f'roteador-{fase}-{w}x{h}.png'))
        (OUT/'geometria.json').write_text(json.dumps(geo, indent=1, ensure_ascii=False))
        print('erros de página:', erros)
finally:
    srv.terminate()
