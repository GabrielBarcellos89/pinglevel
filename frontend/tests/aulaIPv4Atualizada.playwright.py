"""UI na rota oficial: identidade/estado interceptados; zero escrita no servidor real."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
BASE = 'http://10.20.0.4:5173'
URL = BASE + '/modulos/enderecamento/ipv4'
checks, errors, writes = [], [], []
def ok(name):
    checks.append(name)
    print('PASS', name, flush=True)
def avancar(page):
    page.locator('.aula-navegacao .botao-avancar').click()
def fixture(context, revisao=False):
    uid = 942 if revisao else 941
    def api(route):
        req = route.request
        if req.method != 'GET':
            writes.append(req.method + ' ' + req.url)
            route.abort()
            return
        if '/api/auth/me' in req.url:
            data = {'sucesso': True, 'usuario': {'id': uid, 'login': 'qa-ui-local', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
        elif '/api/progresso/aula/estado?' in req.url:
            data = {'sucesso': True, 'estado': {'aula_id': 'enderecamento-ipv4', 'versao_estado': 1, 'versao_conteudo': 1, 'revisao': 8 if revisao else 0, 'modo': 'revisao' if revisao else 'andamento', 'concluida': revisao, 'etapa_retomada': 0, 'etapa_visitada': 5 if revisao else 0, 'etapa_liberada': 5 if revisao else 0, 'legado_sem_respostas': False, 'respostas': {'previsao': 'gateway' if revisao else '', 'pratica': {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'} if revisao else {}, 'interpretacao': 'mac-gateway' if revisao else ''}, 'validacoes': {'pratica': {'status': 'aprovada' if revisao else 'pendente'}, 'interpretacao': {'status': 'aprovada' if revisao else 'pendente'}}}}
        elif '/api/progresso/me' in req.url:
            data = {'sucesso': True, 'progresso': {'usuario_id': uid, 'aulas': [], 'laboratorios': [], 'xp_total': 0}}
        else:
            route.abort()
            return
        route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    context.route('**/api/**', api)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    return page

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome', headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    try:
        c = b.new_context(viewport={'width': 1440, 'height': 1000})
        page = fixture(c)
        page.goto(URL, wait_until='networkidle')
        if page.get_by_role('button', name='Pular apresentação', exact=True).is_visible():
            page.get_by_role('button', name='Pular apresentação', exact=True).click()
        page.get_by_role('heading', name='Como dois computadores entram na mesma rede?', exact=True).wait_for(timeout=6000)
        assert 'Aula oficial' in page.locator('.v4-aviso').inner_text()
        assert 'Prévia em validação' not in page.locator('main').inner_text()
        page.screenshot(path=str(ROOT / 'oficial-01-introducao-desktop.png'), full_page=True)
        ok('rota_oficial_apresenta_conteudo_aprovado')
        avancar(page)
        assert page.locator('.v4-no > svg').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).color==="rgb(240, 32, 53)")')
        avancar(page)
        page.get_by_label('Prefixo em estudo', exact=True).select_option('26')
        page.get_by_role('button', name='2 · Ler o prefixo', exact=True).click()
        assert page.locator('[data-bit-type="rede"]').count() == 26
        assert page.locator('[data-bit-type="host"]').count() == 6
        page.reload(wait_until='networkidle')
        page.locator('.v4-cena[data-scene="2"]').wait_for()
        assert page.get_by_label('Prefixo em estudo', exact=True).input_value() == '26'
        ok('cena_e_prefixo_retomados_no_mesmo_navegador')
        page.get_by_role('button', name='3 · Formar a máscara', exact=True).click()
        page.get_by_role('button', name='Revelar valores das posições', exact=True).click()
        assert page.get_by_test_id('binary-sum').inner_text() == '128 + 64 = 192'
        page.screenshot(path=str(ROOT / 'oficial-02-mascara-desktop.png'), full_page=True)
        avancar(page)
        page.get_by_label('Prefixo em estudo', exact=True).select_option('31')
        assert 'ponto a ponto' in page.get_by_test_id('prefix-special').inner_text().lower()
        page.get_by_label('Prefixo em estudo', exact=True).select_option('32')
        assert page.get_by_test_id('host-capacity').inner_text() == '1'
        assert page.get_by_test_id('broadcast').count() == 0
        ok('prefixos_especiais_preservados_na_oficial')
        avancar(page)
        page.get_by_role('button', name='Conectar computadores', exact=True).click()
        page.get_by_label('IPv4 do Computador 2', exact=True).select_option('192.168.10.20')
        page.get_by_role('button', name='Testar configuração simulada', exact=True).click()
        assert page.get_by_test_id('lan-result').get_attribute('data-result') == 'compativel'
        assert 'Simulação didática' in page.locator('main').inner_text()
        for width in [390, 320]:
            page.set_viewport_size({'width': width, 'height': 1000})
            collapse = page.get_by_role('button', name='Recolher menu', exact=True)
            if collapse.is_visible():
                collapse.click()
            assert page.locator('.aula-conteudo').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
        page.set_viewport_size({'width': 390, 'height': 1000})
        page.screenshot(path=str(ROOT / 'oficial-03-lan-mobile.png'), full_page=True)
        ok('simulacao_honesta_e_conteudo_mobile_sem_overflow_interno')
        assert not writes and not errors, (writes, errors)
        c.close()
        c = b.new_context(viewport={'width': 1440, 'height': 1000})
        c.add_init_script('localStorage.setItem("pinglevel:ipv4:introducao:v1:usuario:942", JSON.stringify({versao:1,cena:5,outroHost:false,prefixo:26,ipB:"",lanPrefixo:24,conectada:false,divisao:25,prefixoBase:24,paginaSubredes:0,subredeAtiva:0}))')
        page = fixture(c, revisao=True)
        page.goto(URL, wait_until='networkidle')
        if page.get_by_role('button', name='Pular apresentação', exact=True).is_visible():
            page.get_by_role('button', name='Pular apresentação', exact=True).click()
        page.locator('.v4-cena[data-scene="0"]').wait_for()
        assert 'Revisão' in page.locator('.v4-aviso').inner_text()
        for _ in range(7):
            avancar(page)
        page.locator('input[name="previsao-ipv4"]').first.wait_for()
        page.locator('input[name="previsao-ipv4"]').last.check()
        avancar(page)
        page.locator('.ipv4-exercicios select').nth(1).select_option('nao')
        page.get_by_role('button', name='Conferir respostas', exact=True).click()
        avancar(page)
        page.screenshot(path=str(ROOT / 'oficial-04-gateway-preservado.png'), full_page=True)
        avancar(page)
        avancar(page)
        page.get_by_role('button', name='Finalizar revisão', exact=False).click()
        page.wait_for_url(BASE + '/')
        assert not writes and not errors, (writes, errors)
        ok('revisao_ignora_cache_antigo_e_preserva_gateway_sem_POST_ou_XP')
        c.close()
    finally:
        b.close()
        result = {'passed': len(checks), 'checks': checks, 'errors': errors, 'writes': writes, 'auth': 'fixture no navegador; nenhuma conta criada ou login real'}
        (ROOT / 'oficial-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False))
