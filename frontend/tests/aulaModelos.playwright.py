"""Aceite UI da aula oficial, APIs de escrita interceptadas; não altera produção."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE = 'http://10.20.0.4:5173'
PATH = '/modulos/fundamentos/modelos-de-rede'
ROOT = Path(__file__).resolve().parent
checks, errors, writes = [], [], []
state = {'uid': 7, 'complete': False, 'phase': -1, 'fail': False, 'conclude_fail': False}

def ok(name):
    checks.append(name)
    print('PASS', name, flush=True)

def next_stage(page):
    page.locator('.aula-navegacao .botao-avancar').click()

def journey(page):
    next_stage(page)
    next_stage(page)
    page.get_by_role('button', name='Enviar', exact=True).click()
    next_stage(page)
    page.get_by_role('button', name='Ver como o texto é representado', exact=True).click()
    next_stage(page)
    for name in ['Organizar a troca', 'Ver as portas', 'Identificar o destino IP', 'Preparar o quadro Wi-Fi', 'Transmitir pelo Wi-Fi']:
        page.get_by_role('button', name=name, exact=True).click()
        next_stage(page)
    for _ in range(6):
        page.get_by_role('button', name='Próxima camada no recebimento', exact=True).click()
    page.get_by_role('button', name='Relacionar com TCP/IP', exact=True).click()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome', headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    try:
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:previa-visual','sim')")
        def api(route):
            url = route.request.url.split('?')[0]
            d = {'sucesso': True}
            if url.endswith('/api/auth/me'):
                d['usuario'] = {'id': state['uid'], 'nome': 'Validação visual', 'login': 'previa-visual', 'papel': 'aluno', 'troca_senha_obrigatoria': False}
            elif url.endswith('/api/progresso/me'):
                aulas = [] if state['phase'] < 0 else [{'aula_id': 'fundamentos-modelos-osi-tcpip', 'etapa_atual': state['phase'], 'concluida': state['complete'], 'percentual': 100 if state['complete'] else 67}]
                d['progresso'] = {'usuario_id': state['uid'], 'aulas': aulas, 'laboratorios': [], 'xp_total': 100 if state['complete'] else 0, 'aulas_concluidas': int(state['complete']), 'laboratorios_concluidos': 0}
            elif route.request.method == 'POST':
                body = route.request.post_data_json
                writes.append({'url': url, 'body': body})
                assert body['aula_id'] == 'fundamentos-modelos-osi-tcpip'
                if state['fail']:
                    state['fail'] = False
                    route.fulfill(status=500, content_type='application/json', body=json.dumps({'sucesso': False, 'mensagem': 'Falha sintética ao salvar'}))
                    return
                if url.endswith('/api/progresso/aula/concluir'):
                    if state['conclude_fail']:
                        state['conclude_fail'] = False
                        route.fulfill(status=500, content_type='application/json', body=json.dumps({'sucesso': False, 'mensagem': 'Conclusão sintética indisponível'}))
                        return
                    assert state['phase'] == 5
                    state['complete'] = True
                elif url.endswith('/api/progresso/aula'):
                    assert 0 <= body['etapa_atual'] <= 5
                    state['phase'] = max(state['phase'], body['etapa_atual'])
                else:
                    raise AssertionError('Escrita inesperada ' + url)
                d['progresso'] = {'xp_concedido': 100 if state['complete'] else 0}
            else:
                route.abort()
                return
            route.fulfill(status=200, content_type='application/json', body=json.dumps(d))
        ctx.route('**/api/**', api)
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + PATH, wait_until='networkidle')
        page.get_by_role('heading', name='Vamos conhecer a tabela OSI', exact=True).wait_for()
        assert 'Prévia para validar' not in page.locator('main').inner_text()
        assert 'Modelos OSI e TCP/IP' in page.locator('main').inner_text()
        ok('rota_oficial_substituida_sem_rotulo_de_previa')
        state['fail'] = True
        next_stage(page)
        page.get_by_role('alert').wait_for()
        assert page.locator('[data-testid="scene-title"]').inner_text() == 'Vamos conhecer a tabela OSI'
        ok('erro_de_gravacao_nao_avanca_silenciosamente')
        next_stage(page)
        next_stage(page)
        page.get_by_role('button', name='Enviar', exact=True).click()
        next_stage(page)
        page.get_by_role('button', name='Ver como o texto é representado', exact=True).click()
        page.reload(wait_until='networkidle')
        assert page.locator('[data-testid="scene-title"]').inner_text() == 'Apresentação'
        assert page.locator('[data-testid="representation"]').inner_text() == '4f 69 21'
        ok('retoma_cena_e_interacao_no_mesmo_navegador')
        state['uid'] = 8; state['phase'] = -1
        page.reload(wait_until='networkidle')
        page.get_by_role('heading', name='Vamos conhecer a tabela OSI', exact=True).wait_for()
        state['uid'] = 7; state['phase'] = 1
        page.reload(wait_until='networkidle')
        assert page.locator('[data-testid="scene-title"]').inner_text() == 'Apresentação'
        ok('rascunho_separado_por_usuario')
        next_stage(page)
        for name in ['Organizar a troca', 'Ver as portas', 'Identificar o destino IP', 'Preparar o quadro Wi-Fi', 'Transmitir pelo Wi-Fi']:
            page.get_by_role('button', name=name, exact=True).click(); next_stage(page)
        for _ in range(6): page.get_by_role('button', name='Próxima camada no recebimento', exact=True).click()
        page.get_by_role('button', name='Relacionar com TCP/IP', exact=True).click()
        assert page.get_by_role('table', name='Correspondência entre TCP/IP e OSI').locator('tbody tr').count() == 4
        assert page.get_by_role('button', name='Concluir aula', exact=True).is_disabled()
        page.get_by_label('Grupo TCP/IP', exact=True).select_option('transporte')
        page.get_by_label('Ordem do recebimento', exact=True).select_option('7-1')
        page.get_by_role('button', name='Conferir entendimento', exact=True).click()
        assert page.get_by_role('button', name='Concluir aula', exact=True).is_disabled()
        page.get_by_label('Grupo TCP/IP', exact=True).select_option('aplicacao')
        page.get_by_label('Ordem do recebimento', exact=True).select_option('1-7')
        page.get_by_role('button', name='Conferir entendimento', exact=True).click()
        assert page.get_by_role('button', name='Concluir aula', exact=True).is_enabled()
        page.reload(wait_until='networkidle')
        assert page.get_by_role('table', name='Correspondência entre TCP/IP e OSI').is_visible()
        assert page.get_by_role('button', name='Concluir aula', exact=True).is_disabled()
        page.get_by_role('button', name='Conferir entendimento', exact=True).click()
        page.screenshot(path=str(ROOT / '01-tcpip-oficial.png'), full_page=True)
        ok('TCPIP_preservado_e_respostas_exigem_conferencia_apos_retomada')
        state['conclude_fail'] = True
        page.get_by_role('button', name='Concluir aula', exact=True).click()
        page.get_by_role('alert').wait_for()
        assert page.url.endswith(PATH)
        page.get_by_role('button', name='Concluir aula', exact=True).click()
        page.wait_for_url(BASE + '/')
        assert state['complete']
        assert all(x['body']['aula_id'] == 'fundamentos-modelos-osi-tcpip' for x in writes)
        ok('conclusao_com_recuperacao_de_erro_e_mesmo_identificador')
        before = len(writes)
        page.goto(BASE + PATH, wait_until='networkidle')
        assert 'Revisão da aula concluída' in page.locator('main').inner_text()
        journey(page)
        assert len(writes) == before
        assert page.get_by_role('button', name='Voltar ao início', exact=True).is_enabled()
        ok('aula_ja_concluida_vira_revisao_sem_POST_ou_novo_XP')
        page.set_viewport_size({'width': 390, 'height': 844})
        collapse = page.get_by_role('button', name='Recolher menu', exact=True)
        if collapse.is_visible(): collapse.click()
        assert not page.locator('.pagina-previa-osi').evaluate('(el)=>el.scrollWidth>el.clientWidth')
        page.screenshot(path=str(ROOT / '02-tcpip-mobile.png'), full_page=True)
        ok('fechamento_TCPIP_mobile_sem_overflow_interno')
        assert not errors, errors
        ctx.close()
    finally:
        browser.close()
r = {'passed': len(checks), 'checks': checks, 'errors': errors, 'writes_intercepted': writes, 'production_writes': 0, 'auth': 'fixture UI, não login real'}
(ROOT / 'results.json').write_text(json.dumps(r, ensure_ascii=False, indent=2))
print(json.dumps({'passed': len(checks), 'checks': checks, 'errors': errors, 'production_writes': 0}, ensure_ascii=False))
