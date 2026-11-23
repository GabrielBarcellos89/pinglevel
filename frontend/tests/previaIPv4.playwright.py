"""Prévia IPv4: identidade de UI simulada; nenhuma escrita ou sessão CORE real."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
BASE='http://10.20.0.4:5173'
PATH='/modulos/enderecamento/ipv4/previa'
checks,errors,writes=[],[],[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def next_stage(page):page.locator('.aula-navegacao .botao-avancar').click()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/opt/playwright/chromium-1243/chrome-linux64/chrome',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 try:
  guest=b.new_context();g=guest.new_page();g.goto(BASE+PATH,wait_until='networkidle');assert g.url.endswith('/login');guest.close();ok('previa_protegida_sem_sessao')
  c=b.new_context(viewport={'width':1440,'height':1000});c.add_init_script("localStorage.setItem('pinglevel:link-apresentado:ipv4-previa','sim')")
  def api(r):
   if r.request.method!='GET':writes.append(r.request.method+' '+r.request.url);r.abort();return
   if r.request.url.endswith('/api/auth/me'):d={'sucesso':True,'usuario':{'id':17,'login':'ipv4-previa','nome':'Aluno QA','papel':'aluno','troca_senha_obrigatoria':False}}
   elif r.request.url.endswith('/api/progresso/me'):d={'sucesso':True,'progresso':{'usuario_id':17,'aulas':[],'laboratorios':[],'xp_total':0,'aulas_concluidas':0,'laboratorios_concluidos':0}}
   else:r.abort();return
   r.fulfill(status=200,content_type='application/json',body=json.dumps(d))
  c.route('**/api/**',api)
  page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+PATH,wait_until='networkidle')
  page.get_by_role('heading',name='Como dois computadores entram na mesma rede?',exact=True).wait_for(timeout=6000)
  before=page.locator('[data-testid="scene-position"]').inner_text();page.wait_for_timeout(1200);assert page.locator('[data-testid="scene-position"]').inner_text()==before
  ok('introducao_e_ritmo_manual_sem_temporizador')
  next_stage(page)
  page.get_by_role('button',name='Ver o outro computador',exact=True).click()
  assert page.locator('[data-testid="host-part"]').inner_text()=='80'
  ok('endereco_distingue_a_interface_do_host_no_exemplo_24')
  theme=page.locator('.pagina-previa-ipv4').evaluate('(e)=>getComputedStyle(e).getPropertyValue("--vermelho").trim()')
  assert theme.lower()=='#f02035',theme
  for selector in ['.v4-no > svg','.v4-parte-rede']:
   assert page.locator(selector).evaluate_all('(els)=>els.length>0 && els.every(e=>getComputedStyle(e).color==="rgb(240, 32, 53)")'),selector
  page.screenshot(path=str(ROOT/'00-endereco-vermelho-real-desktop.png'),full_page=True)
  ok('icones_e_endereco_usam_vermelho_exato_do_tema_sem_rosa')

  next_stage(page)
  chooser=page.get_by_label('Prefixo em estudo',exact=True)
  assert chooser.locator('option').evaluate_all('(els)=>els.map(e=>Number(e.value))')==[8,16,*range(22,33)]
  page.get_by_role('button',name='/26',exact=True).click()
  page.get_by_role('button',name='Alterar bit de exemplo',exact=True).click()
  assert page.locator('[data-testid="bit-example"]').inner_text()=='1'
  page.get_by_role('button',name='2 · Ler o prefixo',exact=True).click()
  assert page.locator('[data-bit-type="rede"]').count()==26
  assert page.locator('[data-bit-type="host"]').count()==6
  assert page.locator('[data-bit-type]').evaluate_all('(els)=>els.every(e=>parseFloat(getComputedStyle(e).fontSize)>=16)')
  contrasts=page.locator('[data-bit-type]').evaluate_all(r"""(els)=>els.map(el=>{const st=getComputedStyle(el);const lum=(c)=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2]};const a=lum(st.color),b=lum(st.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)})""")
  assert min(contrasts)>=4.5,contrasts
  assert page.locator('[data-bit-type="rede"]').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).color==="rgb(240, 32, 53)")')

  ok('bits_maiores_com_contraste_minimo_4_5_e_rotulos_rede_host')
  page.screenshot(path=str(ROOT/'01b-bits-maiores-desktop.png'),full_page=True)
  page.get_by_role('button',name='3 · Formar a máscara',exact=True).click()
  assert 'cada posição vale o dobro da anterior' in page.locator('.v4-guia-bits').inner_text()
  page.get_by_role('button',name='Revelar valores das posições',exact=True).click()
  assert page.locator('[data-testid="binary-sum"]').inner_text()=='128 + 64 = 192'
  assert page.locator('[data-testid="netmask"]').inner_text()=='255.255.255.192'
  chooser.select_option('22')
  assert page.locator('[data-testid="netmask"]').inner_text()=='255.255.252.0'
  assert page.locator('[data-testid="binary-sum"]').inner_text()=='128 + 64 + 32 + 16 + 8 + 4 = 252'
  chooser.select_option('26')
  page.screenshot(path=str(ROOT/'01-mascara-desktop.png'),full_page=True)
  ok('bits_explicados_em_tres_passos_com_pesos_128_64_e_limite_em_outro_octeto')
  next_stage(page)
  assert page.locator('[data-testid="host-capacity"]').inner_text()=='62'
  assert page.locator('[data-testid="broadcast"]').inner_text()=='192.168.10.63'
  page.get_by_role('button',name='/24',exact=True).click();assert page.locator('[data-testid="host-capacity"]').inner_text()=='254'
  chooser=page.get_by_label('Prefixo em estudo',exact=True)
  chooser.select_option('22');assert page.locator('[data-testid="host-capacity"]').inner_text()=='1.022'
  chooser.select_option('31');assert page.locator('[data-testid="host-capacity"]').inner_text()=='2'
  assert page.locator('[data-testid="broadcast"]').count()==0
  assert 'ponto a ponto' in page.locator('[data-testid="prefix-special"]').inner_text().lower()
  chooser.select_option('32');assert page.locator('[data-testid="host-capacity"]').inner_text()=='1'
  assert page.locator('[data-testid="broadcast"]').count()==0
  page.screenshot(path=str(ROOT/'02b-prefixo32-desktop.png'),full_page=True)
  chooser.select_option('26')
  page.screenshot(path=str(ROOT/'02-hosts-desktop.png'),full_page=True)
  ok('capacidade_faixa_rede_e_broadcast_acompanham_a_mascara')
  next_stage(page)
  test=page.get_by_role('button',name='Testar configuração simulada',exact=True)
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='sem-enlace'
  page.get_by_role('button',name='Conectar computadores',exact=True).click()
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='sem-configuracao'
  page.get_by_label('IPv4 do Computador 2',exact=True).select_option('192.168.10.80')
  page.get_by_label('Máscara dos computadores',exact=True).select_option('26')
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='redes-diferentes'
  page.get_by_label('IPv4 do Computador 2',exact=True).select_option('192.168.10.10')
  assert page.locator('[data-testid="lan-result"]').count()==0
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='ip-duplicado'
  page.get_by_label('IPv4 do Computador 2',exact=True).select_option('192.168.10.0')
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='endereco-reservado'
  page.get_by_label('IPv4 do Computador 2',exact=True).select_option('192.168.10.20')
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='compativel'
  page.get_by_label('Máscara dos computadores',exact=True).select_option('31')
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='uso-especial'
  page.get_by_label('Máscara dos computadores',exact=True).select_option('32')
  test.click();assert page.locator('[data-testid="lan-result"]').get_attribute('data-result')=='uso-especial'
  page.get_by_label('Máscara dos computadores',exact=True).select_option('24');test.click()
  page.screenshot(path=str(ROOT/'03-lan-desktop.png'),full_page=True)
  ok('LAN_simulada_exige_enlace_e_IPs_unicos_validos_na_mesma_rede')
  next_stage(page)
  assert page.locator('[data-subnet]').count()==2
  page.get_by_role('button',name='Dividir em /26',exact=True).click()
  assert page.locator('[data-subnet]').count()==4
  assert page.locator('[data-subnet]').evaluate_all('(els)=>els.map(e=>e.dataset.subnet)')==['192.168.10.0/26','192.168.10.64/26','192.168.10.128/26','192.168.10.192/26']
  page.get_by_role('button',name='Explorar sub-rede 192.168.10.128/26',exact=True).click()
  assert '192.168.10.129' in page.locator('[data-testid="selected-subnet"]').inner_text()
  page.get_by_label('Prefixo da rede de origem',exact=True).select_option('22')
  page.get_by_label('Prefixo das partes',exact=True).select_option('32')
  assert page.locator('[data-testid="subnet-total"]').inner_text()=='1024'
  assert page.locator('[data-subnet]').count()==8
  page.get_by_role('button',name='Próximas sub-redes',exact=True).click()
  assert page.locator('[data-subnet]').first.get_attribute('data-subnet')=='192.168.8.8/32'
  page.get_by_label('Prefixo da rede de origem',exact=True).select_option('24')
  page.get_by_label('Prefixo das partes',exact=True).select_option('26')
  page.screenshot(path=str(ROOT/'04-subredes-desktop.png'),full_page=True)
  ok('subdivisao_24_em_25_e_26_com_limites_proprios')
  next_stage(page);page.get_by_role('button',name='Finalizar prévia',exact=True).click()
  assert page.get_by_text('Prévia finalizada.',exact=False).is_visible()
  ok('finalizacao_explicita_sem_concluir_aula_ou_gerar_XP')
  page.set_viewport_size({'width':390,'height':844})
  collapse=page.get_by_role('button',name='Recolher menu',exact=True)
  if collapse.is_visible():collapse.click()
  for _ in range(4):
   page.locator('.aula-navegacao .botao-voltar').click()
   for width in [320,390]:
    page.set_viewport_size({'width':width,'height':844})
    assert not page.locator('.pagina-previa-ipv4').evaluate('(el)=>el.scrollWidth>el.clientWidth')
   if page.get_by_role('heading',name='A máscara desenha o limite',exact=True).count():
    page.get_by_role('button',name='2 · Ler o prefixo',exact=True).click()
    for width in [320,390]:
     page.set_viewport_size({'width':width,'height':844})
     assert not page.locator('.pagina-previa-ipv4').evaluate('(el)=>el.scrollWidth>el.clientWidth')
    page.screenshot(path=str(ROOT/'05-mascara-mobile.png'),full_page=True)
    page.get_by_role('button',name='3 · Formar a máscara',exact=True).click()
    page.get_by_role('button',name='Revelar valores das posições',exact=True).click()
    for width in [320,390]:
     page.set_viewport_size({'width':width,'height':844})
     assert not page.locator('.pagina-previa-ipv4').evaluate('(el)=>el.scrollWidth>el.clientWidth')
    page.screenshot(path=str(ROOT/'06-valores-mobile.png'),full_page=True)
  ok('mascara_hosts_LAN_subredes_mobile_sem_overflow_interno')
  page.goto(BASE+'/modulos',wait_until='networkidle')
  collapse=page.get_by_role('button',name='Recolher menu',exact=True)
  if collapse.is_visible():collapse.click()
  card=page.locator('[data-atividade="enderecamento-ipv4"]')
  assert card.get_by_role('button',name='Iniciar',exact=True).is_visible()
  card.get_by_role('button',name='Explorar sem progresso',exact=True).click();page.wait_for_url(BASE+PATH)
  assert not errors,errors
  assert not writes,writes
  ok('catalogo_mantem_aula_atual_e_acesso_separado_a_previa_sem_escritas')
  c.close()
 finally:b.close()
result={'passed':len(checks),'checks':checks,'errors':errors,'writes':writes,'auth':'fixture somente no navegador; sem login real nem CORE'}
(ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
