"""UI do catálogo com fixture de progresso e todas as escritas bloqueadas."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
BASE='http://10.20.0.4:5173'
checks, errors, writes = [], [], []
flags={"error":False,"wrongUser":False}

def ok(s):
    checks.append(s)
    print('PASS',s,flush=True)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    try:
        c=b.new_context(viewport={'width':1440,'height':1000})
        c.add_init_script("localStorage.setItem('pinglevel:link-apresentado:catalogo-qa','sim')")
        def api(r):
            if r.request.method!='GET':
                writes.append(r.request.method+' '+r.request.url)
                r.abort();return
            if r.request.url.endswith('/api/auth/me'):
                d={'sucesso':True,'usuario':{'id':17,'login':'catalogo-qa','nome':'Aluno QA','papel':'aluno','troca_senha_obrigatoria':False}}
            elif r.request.url.endswith('/api/progresso/me'):
                if flags['error']:
                    r.fulfill(status=503,content_type='application/json',body=json.dumps({'sucesso':False,'mensagem':'Falha sintética de consulta'}));return
                d={'sucesso':True,'progresso':{'usuario_id':18 if flags['wrongUser'] else 17,'aulas':[{'aula_id':'fundamentos-modelos-osi-tcpip','etapa_atual':2,'percentual':50,'concluida':False},{'aula_id':'enderecamento-ipv4','etapa_atual':5,'percentual':100,'concluida':True}],'laboratorios':[{'laboratorio_id':'primeiro-contato','concluido':True}]}}
            elif r.request.url.endswith('/api/lan/status'):
                r.fulfill(status=404,content_type='application/json',body=json.dumps({'sucesso':False}));return
            elif r.request.url.endswith('/api/status'):
                d={'sucesso':True,'ativo':False,'missao':{'titulo':'Missão: Primeiro Contato','descricao':'Consulta sintética sem iniciar ambiente.','xp':100,'nos':[],'etapas':[],'evidencias':[],'proxima_etapa':None,'concluido':False}}
            else:
                r.abort();return
            r.fulfill(status=200,content_type='application/json',body=json.dumps(d))
        c.route('**/api/**',api)
        page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/modulos',wait_until='networkidle')
        page.get_by_role('heading',name='Aulas e laboratórios',exact=True).wait_for(timeout=6000)
        assert page.locator('[data-atividade]').count()==5
        for id,label in [('fundamentos-aula-1','Iniciar'),('fundamentos-modelos-osi-tcpip','Continuar'),('enderecamento-ipv4','Revisar'),('primeira-lan','Iniciar')]:
            assert page.locator(f'[data-atividade="{id}"]').get_by_role('button',name=label,exact=True).is_enabled()
        ok('catalogo_lista_conteudos_existentes_com_acoes_do_progresso')
        page.locator('[data-atividade="fundamentos-modelos-osi-tcpip"]').get_by_role('button',name='Continuar',exact=True).click()
        page.wait_for_url(BASE+'/modulos/fundamentos/modelos-de-rede')
        assert 'Revisão da aula concluída' not in page.locator('main').inner_text()
        ok('continuar_abre_rota_oficial_existente_sem_alterar_identificador')
        page.goto(BASE+'/modulos',wait_until='networkidle')
        page.get_by_label('Buscar conteúdo',exact=True).fill('enderecamento')
        assert page.locator('[data-atividade]').count()==1
        assert page.locator('[data-atividade="enderecamento-ipv4"]').is_visible()
        assert page.get_by_label('Tipo de atividade',exact=True).count()==1
        page.get_by_label('Tipo de atividade',exact=True).select_option('laboratorio')
        assert page.get_by_text('Nenhuma atividade encontrada',exact=True).is_visible()
        page.get_by_label('Buscar conteúdo',exact=True).fill('')
        assert page.locator('[data-atividade]').count()==2
        page.get_by_label('Situação',exact=True).select_option('pendente')
        assert page.locator('[data-atividade]').count()==1
        assert page.locator('[data-atividade="primeira-lan"]').is_visible()
        page.get_by_label('Situação',exact=True).select_option('todas')
        page.get_by_label('Tipo de atividade',exact=True).select_option('todas')
        page.get_by_label('Módulo',exact=True).select_option('enderecamento')
        assert page.locator('[data-atividade]').count()==2
        page.get_by_label('Módulo',exact=True).select_option('todos')
        ok('busca_sem_acentos_e_filtros_por_tipo_modulo_situacao')
        page.screenshot(path=str(ROOT/'01-catalogo-desktop.png'),full_page=True)
        page.locator('[data-atividade="primeiro-contato"]').get_by_role('button',name='Revisar',exact=True).click()
        page.wait_for_url(BASE+'/laboratorio')
        page.get_by_role('button',name='Iniciar laboratório',exact=True).wait_for()
        assert not writes,writes
        ok('consultar_laboratorio_nao_inicia_CORE_automaticamente')
        page.goto(BASE+'/modulos',wait_until='networkidle')
        page.locator('[data-atividade="primeira-lan"]').get_by_role('button',name='Iniciar',exact=True).click()
        page.wait_for_url(BASE+'/laboratorios/primeira-lan')
        page.get_by_role('heading',name='Monte sua primeira LAN',exact=True).wait_for()
        assert not writes,writes
        ok('lab2_listado_e_abertura_nao_inicia_CORE')
        flags['error']=True
        page.goto(BASE+'/modulos',wait_until='networkidle')
        page.get_by_role('alert').wait_for()
        assert page.locator('.catalogo-acao:enabled').count()==0
        assert page.get_by_text('Progresso indisponível',exact=True).count()==5
        flags['error']=False
        page.get_by_role('button',name='Tentar novamente',exact=True).click()
        page.locator('[data-atividade="fundamentos-aula-1"]').get_by_role('button',name='Iniciar',exact=True).wait_for()
        ok('falha_na_consulta_nao_inventa_progresso_e_permite_repetir')
        flags['wrongUser']=True
        page.reload(wait_until='networkidle')
        page.get_by_role('alert').wait_for()
        assert page.locator('.catalogo-acao:enabled').count()==0
        flags['wrongUser']=False
        page.reload(wait_until='networkidle')
        ok('resumo_de_outro_usuario_e_rejeitado')
        page.set_viewport_size({'width':390,'height':844})
        collapse=page.get_by_role('button',name='Recolher menu',exact=True)
        if collapse.is_visible():collapse.click()
        for width in [320,390]:
            page.set_viewport_size({'width':width,'height':844})
            assert not page.locator('.catalogo-pagina').evaluate('(el)=>el.scrollWidth>el.clientWidth')
            for action in page.locator('.catalogo-acao').all():assert action.bounding_box()['height']>=44
        page.screenshot(path=str(ROOT/'02-catalogo-mobile.png'),full_page=True)
        ok('catalogo_320_e_390px_sem_overflow_interno_com_alvos_44px')
        guest=b.new_context();g=guest.new_page();g.goto(BASE+'/modulos',wait_until='networkidle');assert g.url.endswith('/login');guest.close()
        ok('catalogo_mantem_protecao_de_login_real')
        assert not writes,writes
        assert not errors,errors
        ok('catalogo_e_navegacao_sem_escritas_API_e_sem_erros_JS')
        c.close()
    finally:b.close()
(ROOT/'results.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'errors':errors,'writes':writes},ensure_ascii=False,indent=2))
