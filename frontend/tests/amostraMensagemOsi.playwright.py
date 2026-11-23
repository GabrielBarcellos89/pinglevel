"""Percurso OSI completo na prévia. Sem conta real e com toda escrita API bloqueada."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://10.20.0.4:5173'
PATH = '/modulos/fundamentos/modelos-de-rede/previa'
ROOT = Path(__file__).resolve().parent
checks, errors, writes, observations = [], [], [], []


def passed(name):
    checks.append(name)
    print('PASS', name, flush=True)


def next_stage(page):
    page.locator('.aula-navegacao .botao-avancar').click()


def layer(page, number, name):
    banner = page.locator('[data-testid="layer-banner"]')
    assert banner.is_visible()
    assert banner.locator('.osi-camada-numero').inner_text() == str(number)
    assert page.locator('[data-testid="scene-title"]').inner_text() == name


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome', headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    try:
        guest = browser.new_context()
        pg = guest.new_page()
        pg.goto(BASE + PATH, wait_until='networkidle')
        assert pg.url.endswith('/login')
        guest.close()
        passed('rota_sem_sessao_permanece_protegida')
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:previa-visual', 'sim')")
        user = {'id': -100, 'login': 'previa-visual', 'nome': 'Validação visual', 'papel': 'aluno', 'troca_senha_obrigatoria': False}
        def api(route):
            if route.request.method != 'GET':
                writes.append(route.request.method)
                route.abort()
            elif route.request.url.split('?')[0].endswith('/api/auth/me'):
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'sucesso': True, 'usuario': user}))
            else:
                route.abort()
        ctx.route('**/api/**', api)
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + PATH, wait_until='networkidle')
        page.locator('.pagina-previa-osi').wait_for()
        assert page.get_by_role('table', name='As sete camadas do modelo OSI').locator('tbody tr').count() == 7
        next_stage(page)
        next_stage(page)
        layer(page, 7, 'Aplicação')
        page.get_by_role('button', name='Enviar', exact=True).click()
        assert page.locator('[data-testid="bruno-status"]').inner_text() == 'Ainda não recebeu'
        next_stage(page)
        layer(page, 6, 'Apresentação')
        assert page.get_by_text('Preciso decorar esses números?', exact=True).count() == 0, 'Bloco que Gabriel pediu para remover ainda aparece'
        assert 'São apenas os bytes UTF-8' not in page.locator('main').inner_text()
        page.get_by_role('button', name='Ver como o texto é representado', exact=True).click()
        assert page.locator('[data-testid="representation"]').inner_text() == '4f 69 21'
        passed('introducao_e_cenas_aprovadas_preservadas_com_bloco_removido')
        next_stage(page)
        layer(page, 5, 'Sessão')
        assert page.locator('.aula-navegacao .botao-avancar').is_disabled()
        page.get_by_role('button', name='Organizar a troca', exact=True).click()
        assert 'Início' in page.locator('[data-testid="session-flow"]').inner_text()
        page.screenshot(path=str(ROOT / '01-sessao.png'), full_page=True)
        passed('sessao_explicada_por_dialogo_sem_confundir_com_porta_ou_IP')
        next_stage(page)
        layer(page, 4, 'Transporte')
        page.get_by_role('button', name='Ver as portas', exact=True).click()
        assert '55000' in page.locator('[data-testid="transport-flow"]').inner_text()
        assert '80' in page.locator('[data-testid="transport-flow"]').inner_text()
        assert 'servidor' in page.locator('[data-testid="transport-flow"]').inner_text().lower()
        page.screenshot(path=str(ROOT / '02-transporte.png'), full_page=True)
        passed('transporte_mostra_processos_e_portas_do_primeiro_trecho')
        next_stage(page)
        layer(page, 3, 'Rede')
        page.get_by_role('button', name='Identificar o destino IP', exact=True).click()
        dest = page.locator('[data-testid="network-destination"]').inner_text()
        assert '198.51.100.20' in dest and 'servidor' in dest.lower()
        assert page.locator('[data-testid="bruno-status"]').inner_text() == 'Ainda não recebeu'
        page.screenshot(path=str(ROOT / '03-rede.png'), full_page=True)
        passed('rede_distingue_destino_servidor_de_destinatario_Bruno')
        next_stage(page)
        layer(page, 2, 'Enlace')
        page.get_by_role('button', name='Preparar o quadro Wi-Fi', exact=True).click()
        assert 'Pacote IP' in page.locator('[data-testid="link-frame"]').inner_text()
        assert 'Wi-Fi' in page.locator('[data-testid="link-frame"]').inner_text()
        assert 'Quadro Ethernet' not in page.locator('[data-testid="link-frame"]').inner_text()
        passed('enlace_usa_quadro_WiFi_e_entrega_local_sem_Ethernet_ficticio')
        next_stage(page)
        layer(page, 1, 'Física')
        assert page.locator('.aula-navegacao .botao-avancar').is_disabled()
        page.get_by_role('button', name='Transmitir pelo Wi-Fi', exact=True).click()
        assert page.locator('[data-testid="radio-signal"]').get_attribute('data-transmitted') == 'true'
        assert page.locator('[data-testid="bruno-status"]').inner_text() == 'Ainda não recebeu'
        page.screenshot(path=str(ROOT / '04-fisica.png'), full_page=True)
        passed('fisica_transmite_sinais_so_apos_acao_sem_falsa_entrega_final')
        next_stage(page)
        assert page.locator('[data-testid="scene-title"]').inner_text() == 'Quem recebe faz o caminho inverso'
        assert 'outra entrega' in page.locator('[data-testid="server-transition"]').inner_text().lower()
        order = page.locator('[data-testid="receive-order"] [data-layer-number]')
        assert order.evaluate_all('(els) => els.map(e => Number(e.dataset.layerNumber))') == list(range(1, 8))
        page.wait_for_timeout(1500)
        assert page.locator('[data-testid="receive-number"]').inner_text() == '1'
        passed('recebimento_explicito_1_ate_7_sem_avanco_automatico')
        for n in range(1, 8):
            assert page.locator('[data-testid="receive-number"]').inner_text() == str(n)
            if n < 7:
                assert page.locator('.osi-celular-bruno .osi-balao').count() == 0
                assert page.locator('.aula-navegacao .botao-avancar').is_disabled()
                page.get_by_role('button', name='Próxima camada no recebimento', exact=True).click()
        assert page.locator('.osi-celular-bruno .osi-balao').inner_text().startswith('Oi!')
        assert page.locator('.osi-celular-bruno .osi-balao').evaluate('(el) => getComputedStyle(el).alignSelf') == 'flex-start', 'Mensagem recebida deve aparecer à esquerda no celular de Bruno'
        assert page.locator('[data-testid="bruno-status"]').inner_text() == 'Mensagem exibida na simulação'
        page.screenshot(path=str(ROOT / '05-recebimento-aplicacao.png'), full_page=True)
        passed('mensagem_so_aparece_em_Bruno_ao_chegar_a_aplicacao')
        page.get_by_role('button', name='Camada anterior no recebimento', exact=True).click()
        assert page.locator('[data-testid="receive-number"]').inner_text() == '6'
        assert page.locator('.osi-celular-bruno .osi-balao').count() == 0
        page.get_by_role('button', name='Próxima camada no recebimento', exact=True).click()
        page.get_by_role('button', name='Encerrar esta prévia', exact=True).click()
        assert page.get_by_text('Percurso explorado na simulação.', exact=False).is_visible()
        assert 'nenhum XP' in page.locator('main').inner_text()
        passed('retorno_e_fim_da_simulacao_sem_conclusao_ou_XP_reais')
        page.set_viewport_size({'width': 390, 'height': 844})
        collapse = page.get_by_role('button', name='Recolher menu', exact=True)
        if collapse.is_visible():
            collapse.click()
        page.wait_for_timeout(300)
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        page.screenshot(path=str(ROOT / '06-recebimento-mobile.png'), full_page=True)
        passed('recebimento_mobile_sem_overflow_com_menu_global_recolhido')
        page.locator('.aula-navegacao .botao-voltar').click()
        names = ['Física', 'Enlace', 'Rede', 'Transporte', 'Sessão', 'Apresentação', 'Aplicação']
        for number, name in enumerate(names, start=1):
            layer(page, number, name)
            for width in [320, 390]:
                page.set_viewport_size({'width': width, 'height': 844})
                overflow = page.locator('.pagina-previa-osi').evaluate('(el) => el.scrollWidth > el.clientWidth || el.getBoundingClientRect().right > innerWidth')
                if overflow:
                    boxes = page.locator('.pagina-previa-osi *').evaluate_all('(els) => els.map(e=>{const b=e.getBoundingClientRect();return {tag:e.tagName, cls:e.className, text:e.textContent.slice(0,100),right:b.right,left:b.left,width:b.width,minWidth:getComputedStyle(e).minWidth,display:getComputedStyle(e).display}}).filter(e=>e.right>innerWidth+1 && e.width>0).slice(-25)')
                    print('OVERFLOW_DIAGNOSTIC', json.dumps(boxes, ensure_ascii=False), flush=True)
                    page.screenshot(path=str(ROOT / f'overflow-{number}-{width}.png'), full_page=True)
                assert not overflow, (name, width)
                if width == 320 and page.locator('.topbar-acoes').evaluate('(el) => el.getBoundingClientRect().right > innerWidth') and not observations:
                    observations.append('Em 320px com a identidade fictícia Validação visual, o cabeçalho global excede a tela; fora da prévia e não alterado. O conteúdo da prévia é verificado separadamente.')
                for box in page.locator('.osi-atividade-camada button').all():
                    assert box.bounding_box()['height'] >= 44
            if number in [2, 4, 5]:
                page.screenshot(path=str(ROOT / f'camada-{number}-mobile.png'), full_page=True)
            if number < len(names):
                page.locator('.aula-navegacao .botao-voltar').click()
        passed('conteudo_das_camadas_em_320_e_390px_sem_overflow_interno_e_acoes_de_44px')
        for _ in range(len(names)):
            next_stage(page)
        assert page.locator('[data-testid="receive-number"]').inner_text() == '7'
        page.get_by_role('button', name='Encerrar esta prévia', exact=True).click()
        page.get_by_role('button', name='Rever desde a introdução', exact=True).click()
        assert page.get_by_role('table', name='As sete camadas do modelo OSI').is_visible()
        next_stage(page)
        next_stage(page)
        assert page.get_by_role('button', name='Enviar', exact=True).is_enabled()
        assert page.locator('.aula-navegacao .botao-avancar').is_disabled()
        assert page.locator('[data-testid="bruno-status"]').inner_text() == 'Ainda não recebeu'
        passed('revisitar_preserva_a_visita_e_recomecar_limpa_apenas_a_simulacao')
        assert not errors, errors
        assert not writes, writes
        assert 'Link diz' not in page.locator('main').inner_text()
        passed('sem_erros_JavaScript_sem_escritas_API_e_sem_rotulo_Link_diz')
        ctx.close()
    finally:
        browser.close()
result = {'passed': len(checks), 'checks': checks, 'errors': errors, 'writes': writes, 'observations': observations, 'auth': 'fixture apenas no navegador; nenhum usuário ou sessão de produção criado'}
(ROOT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False))
