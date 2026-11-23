"""Garante que a prévia não substitui a rota oficial nem remove autenticação."""
import argparse
import json
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)
parser.add_argument('--skip-live-auth', action='store_true', help='Somente Vite isolado local, sem backend disponível')
args = parser.parse_args()
requests, errors = [], []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome', headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1366, 'height': 650}, service_workers='block')
    def api(route):
        r = route.request
        requests.append({'method': r.method, 'url': r.url})
        if '/api/auth/me' in r.url:
            return route.fulfill(json={'usuario': {'id': 987654, 'nome': 'Professor Gabriel', 'login': 'qa-layout', 'papel': 'professor', 'primeiro_acesso': False, 'trocar_senha': False}})
        if '/api/status' in r.url and r.method == 'GET':
            return route.fulfill(json={'sucesso': True, 'ativo': False, 'missao': {'nos': [], 'etapas': [], 'descricao': 'Fixture de regressão sem ambiente', 'xp': 0}})
        return route.fulfill(status=503, json={'sucesso': False})
    context.route('**/api/**', api)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(args.base_url + '/laboratorio/previa-responsiva')
    if page.get_by_role('button', name='Pular apresentação').is_visible(): page.get_by_role('button', name='Pular apresentação').click()
    expect(page.get_by_text('PRÉVIA DE LAYOUT', exact=True)).to_be_visible()
    expect(page.locator('.aplicacao')).to_have_class(__import__('re').compile('menu-recolhido'))
    page.get_by_role('button', name='Modo foco', exact=True).click()
    page.get_by_role('button', name='Voltar ao laboratório oficial', exact=True).click()
    expect(page).to_have_url(args.base_url + '/laboratorio')
    expect(page.get_by_role('heading', name='Primeiro Contato', exact=True)).to_be_visible()
    expect(page.locator('.lab-responsivo .responsivo-progresso-integrado')).to_be_visible()
    expect(page.locator('.lab-previa')).to_have_count(0)
    expect(page.locator('.sidebar')).to_be_visible()
    expect(page.locator('.topbar')).to_be_visible()
    expect(page.get_by_role('button', name='Abrir menu', exact=True)).to_be_visible()
    original = page.locator('.laboratorio-pagina').evaluate('(e) => ({height: getComputedStyle(e).height, overflow: getComputedStyle(e).overflow, expected: innerHeight-74})')
    assert original['overflow'] == 'visible', original
    expect(page.get_by_label('Comando do terminal')).to_be_in_viewport(ratio=1)
    assert not [r for r in requests if r['method'] != 'GET'], requests
    assert not errors, errors
    context.close()
    context = browser.new_context(service_workers='block')
    context.route('**/api/**', lambda r: r.fulfill(status=401, json={'autenticado': False, 'sucesso': False}))
    page = context.new_page()
    page.goto(args.base_url + '/laboratorio/previa-responsiva')
    expect(page).to_have_url(__import__('re').compile('/login'))
    expect(page.locator('.lab-previa')).to_have_count(0)
    context.close()
    anonymous_auth, live_http = [], {}
    if args.skip_live_auth:
        assert args.base_url.startswith('http://127.0.0.1:'), 'Não pular auth real em publicação'
    else:
        context = browser.new_context(service_workers='block')
        page = context.new_page()
        anonymous_auth = []
        page.on('response', lambda r: anonymous_auth.append(r.status) if '/api/auth/me' in r.url and r.request.method == 'GET' else None)
        page.goto(args.base_url + '/laboratorio/previa-responsiva')
        expect(page).to_have_url(__import__('re').compile('/login'))
        assert 401 in anonymous_auth, anonymous_auth
        live_http = page.evaluate('''async () => {
          const paths = [['/laboratorio/previa-responsiva', null], ['/src/pages/PreviaLaboratorioResponsivo.jsx', 'previa-progresso-integrado'], ['/src/pages/PreviaLaboratorioResponsivo.css', 'previa-faixa-missao']];
          const results = {};
          for (const [path, token] of paths) {
            const r = await fetch(path, {credentials:'omit', cache:'no-store'});
            const text = await r.text();
            results[path] = {status:r.status, marker:token === null || text.includes(token)};
          }
          return results;
        }''')
        assert all(r['status'] == 200 and r['marker'] for r in live_http.values()), live_http
    browser.close()
print(json.dumps({'ok': True, 'rota_oficial_preservada': original, 'sem_escritas_api': True, 'autenticacao_exigida': True, 'auth_real_testada': not args.skip_live_auth, 'auth_anonima_real': anonymous_auth, 'http_real': live_http}, ensure_ascii=False))
