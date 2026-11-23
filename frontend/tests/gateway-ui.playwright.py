"""Navegador + serviço Python real; só I/O dos nós e login são simulados.

Requer frontend/node_modules, pytest, playwright e Chromium.
Uso: PINGLEVEL_QA_BROWSER=/caminho/chromium python frontend/tests/gateway-ui.playwright.py
Não conecta ao servidor, ao Docker nem ao CORE. Capturas ficam em diretório temporário.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'app/laboratorios/tests')]
from test_gateway_guiado import setup_service
from laboratorios.api_gateway_guiado import despachar_gateway
from laboratorios.tutor_referencias import TutorReferencias

URL = 'http://127.0.0.1:5179'
OUT = Path(os.environ.get('PINGLEVEL_QA_OUT', tempfile.mkdtemp(prefix='pinglevel-lab3-qa-')))
OUT.mkdir(parents=True, exist_ok=True)


class Fixture:
    def __init__(self):
        self.service, self.engine, self.saved, _ = setup_service()
        self.deadline = time.time() + 900
        self.engine.dados_temporais = lambda lab: {'prazo': self.deadline, 'agora': time.time(), 'segundos_restantes': max(0, self.deadline-time.time()), 'pode_estender': True, 'extensoes_utilizadas': 0}
        self.service.tutor = TutorReferencias(
            buscar=lambda q: [] if 'indisponível' in q else [{'livro':'Material de redes para teste','pagina_pdf':9,'conteudo':'A máscara identifica a rede. Compare os endereços dos equipamentos.'}],
            gerar=lambda *args:json.dumps({'tipo':'resposta','trechos_usados':[1],'resposta':'Compare a máscara e os endereços visíveis na topologia. Qual parte identifica a rede?'}),
            ancoras=lambda ids: [])
        self.calls = []
        self.fail_next = None
        self.user = {'id': 7, 'login': 'aluno', 'nome': 'Aluno de teste', 'papel': 'aluno'}

    def route(self, route):
        req = route.request
        if req.url.split('/api/')[-1] == 'auth/me':
            return route.fulfill(json={'usuario': self.user})
        assert '/api/gateway/' in req.url, req.url
        action = req.url.split('/api/gateway/')[-1]
        body = (req.post_data or '').encode()
        self.calls.append(action)
        if self.fail_next and action != 'status':
            code, self.fail_next = self.fail_next, None
            data = self.service.executar_acao(7, 'aluno', 'status', {})
            return route.fulfill(status=code, json={**data, 'sucesso': False, 'mensagem': 'Falha simulada; consulte o estado.'})
        data, code = despachar_gateway(self.service, self.user, req.method, '/api/gateway/'+action, body, origem_autorizada=req.headers.get('origin') == URL, limitar=lambda *args: True)
        return route.fulfill(status=code, json=data)


def main():
    errors = []
    results = []
    with open(OUT/'vite.log', 'w') as log:
        # PINGLEVEL_QA_DIST permite testar um build candidato sem publicá-lo em frontend/dist.
        dist = os.environ.get('PINGLEVEL_QA_DIST', 'dist')
        server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', dist, '--host', '127.0.0.1', '--port', '5179', '--strictPort'], cwd=ROOT/'frontend', stdout=log, stderr=log)
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError((OUT/'vite.log').read_text())
                try:
                    urllib.request.urlopen(URL, timeout=1)
                    break
                except Exception:
                    time.sleep(.1)
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get('PINGLEVEL_QA_BROWSER'), args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-webgl', '--no-zygote', '--single-process'])
                context = browser.new_context(viewport={'width':1600,'height':1000}, service_workers='block')
                context.add_init_script("localStorage.setItem('pinglevel:link-apresentado:aluno','sim');localStorage.setItem('pinglevel:apresentacao:lab3','sim')")
                fixture = Fixture()
                context.route('**/api/**', fixture.route)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(URL+'/laboratorios/saindo-da-rede-local')
                expect(page.get_by_role('button',name='Iniciar ambiente',exact=True)).to_be_enabled()
                expect(page.locator('.sidebar')).not_to_be_visible()
                expect(page.get_by_role('heading',name='Quando usar o gateway?',exact=True)).not_to_be_visible()
                assert not page.get_by_label('Endereço IP',exact=True).count()
                assert not page.get_by_label('Comando do terminal',exact=True).count()
                assert fixture.engine.created == 0
                page.screenshot(path=str(OUT/'lab3-inicial-foco.png'),full_page=True)
                expect(page.get_by_role('complementary',name='Tutor Link',exact=True)).to_be_visible()
                expect(page.get_by_label('Qual é sua dúvida?',exact=True)).to_be_disabled()
                assert not page.get_by_role('button',name='Pedir uma pista',exact=True).count()
                assert 'tutor' not in fixture.calls
                page.get_by_role('button',name='Consultar PC Atendimento',exact=True).click()
                expect(page.get_by_label('Endereço IP',exact=True)).to_have_value('192.168.10.10')
                page.get_by_role('button',name='Consultar PC Atendimento',exact=True).click()
                assert not page.get_by_label('Endereço IP',exact=True).count()
                results.append('Modo foco, guia Agora faça, Link sempre visível e endereçamento por inspeção.')

                page.get_by_role('button',name='Iniciar ambiente',exact=True).click()
                expect(page.get_by_label('Sem gateway, o PC Atendimento alcançará o colega?')).to_be_enabled()
                assert not page.get_by_label('Gateway padrão',exact=True).count()
                pergunta=page.get_by_label('Qual é sua dúvida?',exact=True)
                expect(pergunta).to_be_enabled()
                assert 'tutor' not in fixture.calls
                # Em três colunas o Link fica recolhido até o aluno pedir.
                page.locator('.pl-tutor-alternar').click()
                expect(page.locator('.pl-tutor-alternar')).to_have_text('Recolher')
                pergunta.fill('Como comparo os equipamentos da topologia?')
                page.get_by_role('button',name='Perguntar ao Link',exact=True).click()
                expect(pergunta).to_have_value('')
                expect(page.get_by_text('Link · materiais consultados',exact=True)).to_be_visible()
                page.get_by_text('Materiais consultados',exact=True).click()
                expect(page.get_by_text('Material de redes para teste · página 9 do PDF',exact=True)).to_be_visible()
                assert not fixture.engine.commands and not fixture.saved
                pergunta.fill('O material está indisponível?')
                page.get_by_role('button',name='Perguntar ao Link',exact=True).click()
                expect(pergunta).to_have_value('')
                expect(page.get_by_text('Ajuda alternativa',exact=True)).to_be_visible()
                assert page.locator('.pl-mensagens article').last.locator('.pl-fontes').count()==0
                results.append('Link responde somente após pergunta; referências reais da fixture e contingência identificadas sem alterar a rede.')
                page.get_by_label('Sem gateway, o PC Atendimento alcançará o colega?').select_option('nao')
                campo=page.get_by_label('Comando do terminal',exact=True)
                expect(campo).to_have_value('')
                campo.fill('$ ping 192.168.10.20')
                page.get_by_role('button',name='Executar',exact=True).click()
                expect(page.locator('#gw-terminal-erro')).to_contain_text('indicador do terminal')
                assert 'terminal' not in fixture.calls
                campo.fill('ping 8.8.8.8')
                campo.press('Enter')
                expect(page.locator('#gw-terminal-erro')).to_contain_text('PC Colega ou do Servidor')
                assert 'terminal' not in fixture.calls

                def ping(comando, enter=False):
                    campo.fill(comando)
                    if enter:campo.press('Enter')
                    else:page.get_by_role('button',name='Executar',exact=True).click()
                    expect(campo).to_have_value('')
                    expect(page.locator('.gw-saida-comando').first).to_contain_text(comando)

                ping('ping 192.168.10.20',enter=True)
                expect(page.get_by_label('O servidor pertence à mesma rede do computador?')).to_be_visible()
                expect(page.get_by_test_id('agora-faca')).to_contain_text('Compare as redes')
                expect(page.locator('[data-acao=classificacao]')).to_have_class(__import__('re').compile('gw-proxima-acao'))
                page.get_by_role('button',name='Ir para ação',exact=True).click()
                expect(page.get_by_label('O servidor pertence à mesma rede do computador?')).to_be_focused()
                expect(page.get_by_role('region',name='Topologia de duas redes')).to_be_in_viewport()
                expect(page.get_by_test_id('link-persistente')).to_be_in_viewport()
                assert not any('192.168.20.10' in cmd for *_,cmd in fixture.engine.commands if cmd.startswith('ping'))
                expect(page.locator('.gw-linha-comando code').first).to_have_text('$ ping 192.168.10.20')
                expect(page.locator('.gw-detalhes-execucao pre').first).not_to_be_visible()
                page.get_by_text('Detalhes da execução',exact=True).click()
                expect(page.locator('.gw-detalhes-execucao pre').first).to_contain_text('ping -n -I eth0 -c 2 -W 1')
                page.get_by_text('Detalhes da execução',exact=True).click()
                page.get_by_role('button',name='Ir para ação',exact=True).click()
                expect(page.get_by_label('O servidor pertence à mesma rede do computador?')).to_be_focused()
                page.wait_for_function("document.querySelector('.pl-tres') || document.querySelector('[data-acao=classificacao]').getBoundingClientRect().top >= document.querySelector('.pl-agora').getBoundingClientRect().bottom")
                page.screenshot(path=str(OUT/'lab3-terminal-local.png'),full_page=True)
                assert 'ping 192.168.10.20' not in page.get_by_test_id('agora-faca').inner_text()
                results.append('Prática pede observação da topologia; entrada digitada do zero executa teste real; parâmetros recolhidos.')

                page.get_by_label('O servidor pertence à mesma rede do computador?').select_option('mesma-rede')
                page.get_by_role('button',name='Comparar redes',exact=True).click()
                expect(page.get_by_text('Tente novamente.',exact=False)).to_be_visible()
                page.get_by_label('O servidor pertence à mesma rede do computador?').select_option('outra-rede')
                page.get_by_role('button',name='Comparar redes',exact=True).click()
                expect(page.get_by_label('Gateway padrão',exact=True)).to_be_enabled()
                assert not campo.count()
                page.get_by_role('button',name='Consultar Roteador',exact=True).click()
                expect(page.get_by_test_id('interfaces-roteador')).to_contain_text('192.168.10.1/24')
                page.get_by_label('Gateway padrão',exact=True).fill('192.168.20.1')
                page.get_by_role('button',name='Aplicar gateway',exact=True).click()
                expect(page.get_by_text('O próximo salto precisa',exact=False)).to_be_visible()
                page.get_by_label('Gateway padrão',exact=True).fill('192.168.10.20')
                page.get_by_role('button',name='Aplicar gateway',exact=True).click()
                expect(campo).to_be_enabled()
                ping('ping 192.168.20.10')
                expect(page.locator('.gw-teste').filter(has_text='Servidor')).to_contain_text('Não respondeu')
                assert not fixture.saved
                page.get_by_label('Gateway padrão',exact=True).fill('192.168.10.1')
                expect(campo).to_be_disabled()
                page.get_by_role('button',name='Aplicar gateway',exact=True).click()
                expect(page.get_by_text('Aplicado e conferido no nó: 192.168.10.1',exact=True)).to_be_visible()
                expect(campo).to_have_value('')
                page.screenshot(path=str(OUT/'lab3-gateway-desktop.png'),full_page=True)
                results.append('Classificação libera formulário; gateway fora da rede rejeitado; tentativa local incorreta não alcança servidor; rascunho bloqueia teste.')

                for width,height in [(1920,1080),(1600,900),(1366,768),(1024,768),(768,1024),(390,844),(360,800)]:
                    page.set_viewport_size({'width':width,'height':height})
                    page.wait_for_function('document.documentElement.scrollWidth <= window.innerWidth',timeout=3000)
                    expect(page.get_by_test_id('link-persistente')).to_be_in_viewport()
                    if width<=850:
                        abrir=page.get_by_role('button',name='Ver topologia e equipamentos',exact=True)
                        if abrir.get_attribute('aria-expanded')=='false':abrir.click()
                    assert page.locator('.gw-equipamento').count() == 5
                    for item in page.locator('.gw-equipamento').all():
                        box=item.bounding_box()
                        ip=item.locator('small')
                        assert float(ip.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)'))>=14
                        assert box and box['x']>=0 and box['x']+box['width']<=width+1, (width,box)
                    if width<=850:page.get_by_role('button',name='Recolher topologia',exact=True).click()
                    page.get_by_role('button',name='Ir para ação',exact=True).click()
                    expect(campo).to_be_focused()
                    expect(campo).to_be_in_viewport()
                    page.wait_for_function("document.querySelector('.pl-tres') || document.querySelector('#gw-comando').getBoundingClientRect().top >= document.querySelector('.pl-agora').getBoundingClientRect().bottom",timeout=3000)
                    cb=campo.bounding_box(); lb=page.get_by_test_id('link-persistente').bounding_box()
                    if width<=850:assert cb['y']+cb['height']<=lb['y'],(width,cb,lb)
                    else:
                        topo=page.get_by_test_id('topologia-persistente').bounding_box()
                        link=page.get_by_test_id('link-persistente').bounding_box()
                        page.get_by_role('region',name='Área de prática',exact=True).evaluate('(el)=>el.scrollTop=el.scrollHeight')
                        assert page.get_by_test_id('topologia-persistente').bounding_box()==topo
                        assert page.get_by_test_id('link-persistente').bounding_box()==link
                        page.get_by_role('button',name='Ir para ação',exact=True).click()
                    expect(page.get_by_test_id('agora-faca')).to_be_in_viewport()
                    page.screenshot(path=str(OUT/f'lab3-{width}x{height}.png'))
                    if width>850:
                        expect(page.get_by_role('region',name='Topologia de duas redes')).to_be_in_viewport()
                    if width==390:
                        if page.get_by_role('button',name='Ver ajuda',exact=True).count():
                            page.get_by_role('button',name='Ver ajuda',exact=True).click()
                        expect(page.get_by_label('Qual é sua dúvida?',exact=True)).to_be_in_viewport()
                        page.get_by_role('button',name='Recolher ajuda',exact=True).click()
                        page.screenshot(path=str(OUT/'lab3-terminal-mobile.png'),full_page=True)
                page.set_viewport_size({'width':1600,'height':1000})
                results.append('Campo do terminal e topologia sem overflow horizontal em sete dimensões.')
                page.get_by_role('button',name='Mostrar Bastidores',exact=True).click()
                expect(page.get_by_role('heading',name='Quando usar o gateway?',exact=True)).to_be_visible()
                page.get_by_role('button',name='Ocultar Bastidores',exact=True).click()
                page.get_by_role('button',name='Sair do modo foco',exact=True).click()
                expect(page.locator('.sidebar')).to_be_visible()
                page.get_by_role('button',name='Modo foco',exact=True).click()
                expect(page.locator('.sidebar')).not_to_be_visible()
                ping('ping 192.168.20.10',enter=True)
                expect(page.get_by_label('Escolha a explicação para os resultados')).to_be_visible()
                page.get_by_label('Escolha a explicação para os resultados').select_option('gateway-sempre')
                page.get_by_role('button',name='Conferir interpretação',exact=True).click()
                expect(page.get_by_role('button',name='Validar missão',exact=True)).to_be_disabled()
                page.get_by_label('Escolha a explicação para os resultados').select_option('gateway-remoto')
                page.get_by_role('button',name='Conferir interpretação',exact=True).click()
                expect(page.get_by_role('button',name='Validar missão',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Consultar Roteador',exact=True).click()
                expect(page.get_by_role('button',name='Validar missão',exact=True)).to_be_enabled()
                page.screenshot(path=str(OUT/'lab3-comprovacao-desktop.png'),full_page=True)
                page.get_by_role('button',name='Validar missão',exact=True).click()
                expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP confirmados.')
                assert fixture.saved == [(7,'saindo-da-rede-local')]
                results.append('Ping remoto digitado, interpretação e consulta preservados; conclusão concede 100 XP uma vez.')

                page.reload()
                expect(page.get_by_test_id('conclusao')).to_contain_text('Progresso recuperado')
                assert fixture.engine.created==1 and len(fixture.saved)==1
                page.get_by_role('button',name='Iniciar novo treino',exact=True).click()
                expect(page.get_by_label('Sem gateway, o PC Atendimento alcançará o colega?')).to_be_enabled()
                assert fixture.engine.created==2 and len(fixture.saved)==1
                fixture.fail_next=503
                page.get_by_label('Sem gateway, o PC Atendimento alcançará o colega?').select_option('sim')
                campo.fill('ping 192.168.10.20');campo.press('Enter')
                expect(page.get_by_role('button',name='Atualizar estado',exact=True).first).to_be_enabled()
                expect(page.get_by_role('button',name='Executar',exact=True)).to_be_disabled()
                expect(campo).to_have_value('ping 192.168.10.20')
                page.get_by_role('button',name='Atualizar estado',exact=True).first.click()
                expect(page.get_by_role('button',name='Executar',exact=True)).to_be_enabled()
                ping('ping 192.168.10.20')
                expect(page.get_by_label('O servidor pertence à mesma rede do computador?')).to_be_visible()
                page.get_by_text('Experimento opcional',exact=True).click()
                page.get_by_role('button',name='Experimentar acesso ao servidor (opcional)',exact=True).click()
                expect(campo).to_have_value('')
                ping('ping 192.168.20.10')
                expect(page.locator('.gw-teste').filter(has_text='Servidor')).to_contain_text('Não respondeu')
                results.append('Recarga preserva progresso; erro503 preserva comando; novo treino não duplica XP; experimento remoto também digitado.')
                assert not errors, errors
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
    (OUT/'resultado.json').write_text(json.dumps({'aprovado':True,'limites':'Login e I/O dos nós simulados; serviço Python e frontend reais; sem Docker/CORE real.','casos':results,'erros_browser':errors},ensure_ascii=False,indent=2))
    print(json.dumps({'aprovado':True,'casos':len(results),'evidencias':str(OUT)},ensure_ascii=False))


if __name__=='__main__':main()
