"""Browser -> Vite -> Handler/serviço reais -> SQLite temporário; engine só I/O fake."""
from pathlib import Path
import json, os, socket, subprocess, tempfile, time
from http.cookies import SimpleCookie
from playwright.sync_api import sync_playwright, expect
from testar_gateway_guiado_http import TestHandlerGateway, progresso

ROOT=Path(__file__).resolve().parents[2]
FRONT=ROOT/'frontend';OUT=ROOT/'qa/gateway-integrado';OUT.mkdir(parents=True,exist_ok=True)
case=TestHandlerGateway();case.setUp();server=None;config=None
try:
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    case.context['FRONTEND_URL']=base
    def cookie(header):
        c=SimpleCookie();c.load(header or '');return c['qa'].value if 'qa' in c else None
    case.context['token_do_cookie']=cookie
    disconnected=[]
    original_json=case.context['Handler'].enviar_json
    def send_json(handler,*args,**kwargs):
        try:return original_json(handler,*args,**kwargs)
        except (BrokenPipeError,ConnectionResetError):
            if handler.command!='GET':raise
            disconnected.append(handler.path)
    case.context['Handler'].enviar_json=send_json
    def temporal(lab):
        now=time.time()
        return {'prazo':now+900,'agora':now,'segundos_restantes':900,'tempo_extensao':300,
                'max_extensoes':1,'extensoes_utilizadas':case.engine.extended,'pode_estender':case.engine.extended<1}
    case.engine.dados_temporais=temporal
    f=tempfile.NamedTemporaryFile(prefix='.gateway-integracao-',suffix='.mjs',dir=FRONT,delete=False,mode='w');config=Path(f.name)
    text=(FRONT/'vite.config.js').read_text().replace("host: '0.0.0.0'","host: '127.0.0.1'").replace('http://127.0.0.1:8088',f'http://127.0.0.1:{case.server.server_address[1]}');f.write(text);f.close()
    log=open(OUT/'vite.log','w')
    server=subprocess.Popen(['node',str(FRONT/'node_modules/vite/bin/vite.js'),'--config',str(config),'--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=FRONT,stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
        assert server.poll() is None,'Vite terminou antes de ficar disponível'
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:break
        time.sleep(.1)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1366,'height':650},service_workers='block')
        context.add_cookies([{'name':'qa','value':'usuario-1','url':base}])
        context.route('**/api/auth/me',lambda r:r.fulfill(json={'usuario':{'id':1,'nome':'Aluno QA','login':'gateway-qa','papel':'aluno'}}))
        context.add_init_script("localStorage.setItem('pinglevel:link-apresentado:gateway-qa','sim')")
        page=context.new_page();errors=[];calls=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:calls.append({'url':r.url,'method':r.method}) if '/api/gateway/' in r.url else None)
        page.goto(base+'/laboratorios/saindo-da-rede-local')
        if page.get_by_role('button',name='Pular apresentação',exact=True).is_visible():page.get_by_role('button',name='Pular apresentação',exact=True).click()
        expect(page.get_by_role('heading',name='Saindo da rede local',exact=True)).to_be_visible()
        assert case.engine.lab is None
        assert not [r for r in calls if r['method']=='POST']
        button=lambda name:page.get_by_role('button',name=name,exact=True)
        command=page.get_by_label('Gateway do Computador 1',exact=True)
        expect(command).to_have_value('');expect(command).to_be_in_viewport(ratio=1)
        page.screenshot(path=str(OUT/'01-inicial-1366x650.png'))
        button('Iniciar ambiente').click();expect(button('Registrar hipótese')).to_be_visible()
        page.get_by_label('Hipótese local').select_option('nao');page.get_by_label('Hipótese remota').select_option('sim');button('Registrar hipótese').click();button('Testar antes').click()
        expect(page.get_by_test_id('comparacao-antes')).to_contain_text('Não alcançou')
        page.route('**/api/status',lambda route:route.fulfill(json={'sucesso':True,'ativo':True,'laboratorio':{'session_id':case.engine.lab.session_id,'laboratorio_id':'saindo-da-rede-local'}}))
        page.goto(base+'/laboratorio')
        expect(page.get_by_role('heading',name='Outra missão está em execução')).to_be_visible()
        button('Abrir Saindo da rede local').click()
        expect(page.get_by_role('heading',name='Saindo da rede local',exact=True)).to_be_visible()
        expect(page.get_by_test_id('comparacao-antes')).to_contain_text('Não alcançou')
        assert case.engine.created==1
        button('Consultar interfaces do roteador').click();expect(page.get_by_test_id('interfaces-roteador')).to_contain_text('192.168.10.1/24');expect(command).to_have_value('')
        command.fill('192.168.10.20');button('Aplicar gateway').click();button('Conferir rota aplicada').click();button('Testar depois').click();expect(page.get_by_test_id('comparacao-depois')).to_contain_text('Não alcançou');expect(button('Concluir missão')).to_be_disabled()
        command.fill('192.168.10.1');button('Aplicar gateway').click();button('Conferir rota aplicada').click();button('Testar depois').click();expect(page.get_by_test_id('comparacao-depois')).to_contain_text('Alcançou')
        page.screenshot(path=str(OUT/'02-depois-1366x650.png'))
        page.get_by_label('Interpretação').select_option('gateway-remoto');button('Conferir interpretação').click();expect(button('Concluir missão')).to_be_enabled();button('Concluir missão').click()
        expect(page.get_by_test_id('conclusao')).to_contain_text('+100 XP');assert case.engine.lab is None
        page.screenshot(path=str(OUT/'03-conclusao-1366x650.png'))
        with progresso._conectar() as conn:
            count=conn.execute("SELECT COUNT(*) FROM eventos_xp WHERE origem_id='saindo-da-rede-local'").fetchone()[0]
            assert count==1
        page.reload();expect(page.get_by_test_id('conclusao')).to_contain_text('Progresso recuperado');assert case.engine.lab is None
        with progresso._conectar() as conn:assert conn.execute("SELECT COUNT(*) FROM eventos_xp WHERE origem_id='saindo-da-rede-local'").fetchone()[0]==1
        case.engine.criar(1,'fixture','saindo-da-rede-local');case.engine.lab.preparacao_confirmada=False
        page.reload()
        expect(page.get_by_test_id('preparacao-pendente')).to_contain_text('Preparação incompleta')
        expect(command).to_be_disabled();expect(button('Iniciar ambiente')).to_be_disabled()
        button('Encerrar este ambiente').click();expect(button('Iniciar novo treino')).to_be_enabled();assert case.engine.lab is None
        assert not errors,errors
        assert all(path=='/api/gateway/status' for path in disconnected),disconnected
        browser.close()
    report={'aprovado':True,'http_gateway_real_local':True,'servico_real':True,'sqlite_temporario':True,'eventos_xp_no_banco_temporario':count,'errors':errors,'get_status_cancelados_pelo_cliente':disconnected,'requests':calls,'limite':'Auth sintética e engine I/O fake; nenhum CORE, login ou XP de produção'}
    (OUT/'resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
finally:
    if server:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        log.close()
    if config:config.unlink(missing_ok=True)
    case.doCleanups()
