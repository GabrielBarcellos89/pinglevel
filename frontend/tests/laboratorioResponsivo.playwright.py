"""UI oficial + APIs HTTP interceptadas. Nunca inicia CORE ou grava XP reais."""
import argparse, copy, json, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:4180')
parser.add_argument('--report', default='tests/laboratorio-responsivo.json')
args = parser.parse_args()
report = Path(args.report); report.parent.mkdir(parents=True, exist_ok=True)
results, errors, unexpected = [], [], []
STEPS = [
    {'id':'identificacao', 'titulo':'Identifique o dispositivo', 'orientacao':'Descubra o nome do Computador 1.'},
    {'id':'enderecamento', 'titulo':'Consulte o endereço IPv4', 'orientacao':'Consulte a interface eth0.'},
    {'id':'conectividade', 'titulo':'Teste a comunicação', 'orientacao':'Registre a previsão e teste o Computador 2.'},
]
class Fixture:
    def __init__(self):
        self.active=False; self.done=set(); self.prediction=None; self.interpretation=None; self.other=None; self.fail_command=False; self.calls=[]
    def mission(self):
        return {'titulo':'Missão: Primeiro Contato', 'descricao':'Identifique os computadores, consulte IPv4 e observe a comunicação local.', 'xp':100,
                'nos':[{'id':1,'nome':'Computador 1','tipo':'computador','ip':'10.0.0.20','prefixo':24}, {'id':3,'nome':'Switch','tipo':'switch'}, {'id':2,'nome':'Computador 2','tipo':'computador','ip':'10.0.0.21','prefixo':24}],
                'etapas':[dict(e,concluida=e['id'] in self.done) for e in STEPS], 'evidencias':[], 'proxima_etapa':next((e['id'] for e in STEPS if e['id'] not in self.done),None), 'concluido':len(self.done)==3,
                'aprendizagem':{'previsao':self.prediction,'interpretacao':self.interpretation,'interpretacao_correta':self.interpretation=='alcance','pode_prever':'enderecamento' in self.done,'pode_interpretar':'conectividade' in self.done,
                    'perguntas':{'previsao':{'enunciado':'Você espera comunicação entre estes dois PCs?','opcoes':[{'id':'sim','texto':'Sim, estão conectados à mesma rede.'},{'id':'nao','texto':'Não sei ainda.'}]},'interpretacao':{'enunciado':'O que o ping demonstra?','opcoes':[{'id':'alcance','texto':'Alcance entre estes computadores.'},{'id':'internet','texto':'Internet completa.'}]}},'feedback':''}}
    def status(self):
        now=time.time()
        return {'sucesso':True,'ativo':self.active,'missao':self.mission(),'bastidores':None,'laboratorio':({'session_id':987650,'laboratorio_id':self.other or 'primeiro-contato','prazo':now+900,'agora':now,'pode_estender':True,'tempo_extensao':180} if self.active else None)}
    def route(self, route):
        req=route.request; path=req.url.split('/api/',1)[-1].split('?',1)[0]
        self.calls.append({'path':path,'method':req.method,'body':req.post_data_json if req.post_data else None})
        if path=='auth/me': return route.fulfill(json={'usuario':{'id':987654,'nome':'Professor Gabriel','login':'qa-layout','papel':'professor','primeiro_acesso':False,'trocar_senha':False}})
        if path=='status' and req.method=='GET': return route.fulfill(json=self.status())
        if path=='iniciar' and req.method=='POST': self.active=True; self.done.clear(); return route.fulfill(json=self.status())
        if path=='estender' and req.method=='POST': return route.fulfill(json=dict(self.status(),mensagem='Prazo estendido pela fixture.'))
        if path=='encerrar' and req.method=='POST': self.active=False; return route.fulfill(json=dict(self.status(),mensagem='Fixture encerrada.'))
        if path=='aprendizagem' and req.method=='POST':
            d=req.post_data_json
            if d['fase']=='previsao': self.prediction=d['resposta']
            else: self.interpretation=d['resposta']
            return route.fulfill(json=self.status())
        if path=='comando' and req.method=='POST':
            d=req.post_data_json; node=d['node_id']; cmd=d['comando']
            if self.fail_command: return route.fulfill(status=503,json={'sucesso':False,'mensagem':'Falha de comando da fixture.'})
            output='Fixture de saída longa\n'+'\n'.join(f'Linha de teste {i}' for i in range(40))
            if cmd=='hostname':
                output=f'computador-{node}'
                if node==1:self.done.add('identificacao')
            if cmd=='ip addr show eth0':
                output=f'eth0: UP\ninet 10.0.0.{20 if node==1 else 21}/24'
                if node==1:self.done.add('enderecamento')
            if cmd.startswith('ping '):
                assert self.prediction is not None
                output='2 packets transmitted, 2 received, 0% packet loss [fixture]'
                if node==1:self.done.add('conectividade')
            return route.fulfill(json=dict(self.status(),codigo=0,saida=output))
        if path=='tutor' and req.method=='POST': return route.fulfill(json={'sucesso':True,'resposta':'Orientação interceptada: observe o endereço da interface.','fonte':'Fixture HTTP, não tutor real'})
        if path=='validar' and req.method=='POST': return route.fulfill(json=dict(self.status(),xp_concedido=100,mensagem='Conclusão interceptada; nenhum XP real.'))
        if path=='progresso' and req.method=='GET': return route.fulfill(json={'sucesso':True,'aulas':[],'laboratorios':[]})
        unexpected.append({'path':path,'method':req.method});route.fulfill(status=503,json={'sucesso':False,'mensagem':'Rota bloqueada pelo QA'})

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox'])
    for width,height in [(1093,550),(1280,620),(1366,650),(1536,754),(1920,950)]:
        context=browser.new_context(viewport={'width':width,'height':height},service_workers='block')
        fixture=Fixture();context.route('**/api/**',fixture.route)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base_url+'/laboratorio')
        if page.get_by_role('button',name='Pular apresentação').is_visible():page.get_by_role('button',name='Pular apresentação').click()
        band=page.locator('.responsivo-progresso-integrado');expect(band).to_be_visible()
        expect(page.get_by_text('PRÉVIA DE LAYOUT',exact=True)).to_have_count(0)
        expect(band).to_contain_text('100 XP')
        command=page.get_by_label('Comando do terminal');execute=page.get_by_role('button',name='Executar',exact=True)
        expect(command).to_be_disabled();expect(command).to_be_in_viewport(ratio=1);expect(execute).to_be_in_viewport(ratio=1)
        assert not [r for r in fixture.calls if r['method']!='GET'],fixture.calls
        panel=page.get_by_role('region',name='O caminho do ping')
        expect(panel.get_by_role('heading',name='Aguardando a etapa 3',exact=True)).to_be_visible()
        expect(panel).not_to_contain_text('hostname')
        expect(panel).not_to_contain_text('ip addr')
        expect(panel).not_to_contain_text('Execute um ping')
        expect(panel.get_by_role('radio')).to_have_count(0)
        page.get_by_role('button',name='Iniciar laboratório',exact=True).click();expect(command).to_be_enabled()
        expect(panel.get_by_role('heading',name='Aguardando a etapa 3',exact=True)).to_be_visible()
        expect(panel).not_to_contain_text('hostname')
        expect(panel).not_to_contain_text('ip addr')
        expect(panel).not_to_contain_text('Execute um ping')
        expect(band).to_be_in_viewport(ratio=1);expect(command).to_be_in_viewport(ratio=1);expect(execute).to_be_in_viewport(ratio=1)
        expect(page.locator('.lab-terminal-cabecalho')).to_contain_text('SSH protegido')
        assert page.evaluate('visualViewport.scale')==1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        output=page.locator('.lab-terminal-saida')
        assert output.bounding_box()['height'] >= (150 if height<600 else 200),output.bounding_box()
        page.screenshot(path=str(report.with_suffix(f'.inicial-{width}x{height}.png')))
        command.fill('rascunho sem executar')
        page.get_by_role('button',name='Ver etapas',exact=True).click();expect(page.get_by_role('dialog',name='Etapas da missão')).to_be_visible()
        page.get_by_role('button',name='Fechar etapas',exact=True).click();expect(command).to_have_value('rascunho sem executar')
        page.get_by_role('button',name='Conversar com o Link',exact=True).click()
        page.get_by_placeholder('Digite sua pergunta...').fill('Como observo a interface?')
        page.get_by_role('button',name='Enviar pergunta').click();expect(page.locator('.lab-tutor-conversa')).to_contain_text('Orientação interceptada')
        page.get_by_role('button',name='Minimizar conversa com o Link').click();expect(command).to_have_value('rascunho sem executar')
        page.get_by_role('button',name='Ocultar Bastidores',exact=True).click();expect(command).to_have_value('rascunho sem executar')
        page.get_by_role('button',name='Mostrar Bastidores',exact=True).click()
        menu=page.get_by_role('button',name='Recolher menu',exact=True)
        if menu.count():menu.click()
        else:page.get_by_role('button',name='Abrir menu',exact=True).first.click()
        page.evaluate('scrollTo(0,0)');expect(command).to_be_in_viewport(ratio=1);expect(execute).to_be_in_viewport(ratio=1)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        command.fill('hostname');execute.click();expect(output).to_contain_text('computador-1');expect(band).to_contain_text('1 de 3 etapas')
        expect(panel.get_by_role('heading',name='Aguardando a etapa 3',exact=True)).to_be_visible()
        expect(panel).not_to_contain_text('hostname')
        expect(panel).not_to_contain_text('ip addr')
        expect(panel.get_by_role('radio')).to_have_count(0)
        command.fill('ip addr show eth0');execute.click();expect(output).to_contain_text('10.0.0.20/24');expect(band).to_contain_text('2 de 3 etapas')
        expect(panel.get_by_role('heading',name='Etapa 3: faça sua previsão antes do ping',exact=True)).to_be_visible()
        expect(panel).not_to_contain_text('Execute um ping')
        command.fill('ping -c 2 10.0.0.21');before=len([r for r in fixture.calls if r['path']=='comando']);execute.click()
        expect(page.get_by_text('Registre sua previsão nos Bastidores antes de executar o ping.',exact=True)).to_be_visible()
        assert len([r for r in fixture.calls if r['path']=='comando'])==before
        page.get_by_role('radio',name='Sim, estão conectados à mesma rede.',exact=True).check();page.get_by_role('button',name='Registrar minha previsão',exact=True).click()
        expect(page.get_by_role('heading',name='Etapa 4: pratique e observe',exact=True)).to_be_visible()
        fixture.fail_command=True;command.fill('hostname');execute.click();expect(output).to_contain_text('Falha de comando da fixture.');fixture.fail_command=False
        command.fill('ip link show');execute.click();expect(output).to_contain_text('Linha de teste 39')
        command.fill('rascunho resize');page.set_viewport_size({'width':max(1050,width-170),'height':height});expect(command).to_have_value('rascunho resize');expect(output).to_contain_text('Linha de teste 39')
        page.set_viewport_size({'width':width,'height':height});page.locator('.lab-topologia button').filter(has_text='Computador 2').click();command.fill('PC2 preservado')
        page.set_viewport_size({'width':max(1050,width-130),'height':height});expect(command).to_have_value('PC2 preservado');expect(page.locator('.lab-terminal-cabecalho')).to_contain_text('Computador 2')
        page.set_viewport_size({'width':width,'height':height});page.locator('.lab-topologia button').filter(has_text='Computador 1').click();expect(command).to_have_value('rascunho resize')
        page.get_by_role('button',name='Modo foco',exact=True).click();expect(page.locator('.sidebar')).not_to_be_visible();expect(page.locator('.topbar')).not_to_be_visible();expect(command).to_be_in_viewport(ratio=1)
        page.get_by_role('button',name='Sair do modo foco',exact=True).click();expect(page.locator('.topbar')).to_be_visible();expect(command).to_have_value('rascunho resize')
        command.fill('ping -c 2 10.0.0.21');execute.click();expect(band).to_contain_text('3 de 3 etapas');expect(band).to_contain_text('Missão concluída');expect(page.get_by_role('progressbar',name='Progresso da missão')).to_have_attribute('aria-valuenow','100')
        page.get_by_role('button',name='Validar missão',exact=True).click();expect(page.get_by_role('dialog',name='Primeiro Contato completo!')).to_contain_text('+100 XP')
        page.get_by_role('button',name='Voltar para a jornada',exact=True).click();expect(page).to_have_url(args.base_url+'/');assert not fixture.active
        expect(page.locator('.lab-responsivo')).to_have_count(0);expect(page.locator('.sidebar')).to_be_visible();expect(page.locator('.topbar')).to_be_visible()
        results.append({'viewport':[width,height],'ok':True,'requests_interceptadas':len(fixture.calls),'contratos_http':True,'sem_core_real':True})
        context.close()
    context=browser.new_context(viewport={'width':1366,'height':650},service_workers='block');fixture=Fixture();fixture.active=True;fixture.other='primeira-lan';context.route('**/api/**',fixture.route)
    page=context.new_page();page.goto(args.base_url+'/laboratorio');expect(page.get_by_role('heading',name='Outra missão está em execução')).to_be_visible();assert not [r for r in fixture.calls if r['method']!='GET'];context.close()
    context=browser.new_context(service_workers='block');context.route('**/api/**',lambda r:r.fulfill(status=401,json={'sucesso':False}));page=context.new_page();page.goto(args.base_url+'/laboratorio');expect(page).to_have_url(re.compile('/login'));context.close()
    assert not errors,errors
    assert not [r for r in unexpected if r['method']!='GET'],unexpected
    browser.close()
report.write_text(json.dumps({'results':results,'errors':errors,'unexpected':unexpected,'limite':'UI oficial e contratos HTTP com fixture; nenhum login real+CORE+XP de produção testado'},ensure_ascii=False,indent=2))
print(json.dumps({'ok':True,'viewports':len(results),'report':str(report)},ensure_ascii=False))
