"""Aulas da rede local e do transporte no build candidato: Ethernet, MAC e ARP (Módulo 1), Switch e VLANs e
Transporte: portas, TCP e UDP (Módulo 3). Percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_lan.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-lan)
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT / '.qa/dist')
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-lan')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
envios, erros = [], []


def api(route):
    req = route.request
    if req.url.endswith('/api/auth/me'):
        dados = {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
    elif '/api/progresso/me' in req.url:
        dados = {'sucesso': True, 'progresso': {'usuario_id': 17, 'aulas': [], 'laboratorios': [], 'xp_total': 0}}
    elif req.method == 'POST' and '/api/progresso/aula' in req.url:
        envios.append((req.url.split('/api/')[-1], json.loads(req.post_data)))
        dados = {'sucesso': True}
    else:
        return route.abort()
    route.fulfill(status=200, content_type='application/json', body=json.dumps(dados))


log = open(OUT / 'preview.log', 'w')
srv = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(DIST), '--host', '127.0.0.1',
                        '--port', '5179', '--strictPort'], cwd=ROOT / 'frontend', stdout=log, stderr=log)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(.1)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 1440, 'height': 1000})
        ctx.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim')")
        ctx.route('**/api/**', api)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: erros.append(str(e)))
        avancar = pg.locator('.botao-avancar')
        conferir = pg.get_by_role('button', name='Conferir')

        def responder(pares, erros_esperados=0):
            for pergunta, resposta in pares:
                pg.get_by_role('group', name=pergunta).get_by_role('button', name=resposta, exact=True).click()
            conferir.click()
            expect(pg.locator('.ag-retorno.erro')).to_have_count(erros_esperados)

        def concluir(aula_id, etapas, aviso):
            expect(pg.locator('.aula-conclusao')).to_contain_text(aviso)
            avancar.click()
            expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
            enviados = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
            assert enviados == list(range(1, etapas)), envios
            assert envios[-1] == ('progresso/aula/concluir', {'aula_id': aula_id}), envios[-1]
            envios.clear()

        # ---- Módulo 1: Ethernet, MAC e ARP ----
        pg.goto(URL + '/modulos/fundamentos/ethernet-arp', wait_until='networkidle')
        expect(pg.get_by_label('Como é um endereço MAC')).to_contain_text('48 bits')
        expect(avancar).to_be_disabled()
        responder([('Quantos bits tem um endereço MAC?', '32 bits, como o IPv4'),
                   ('Em 02:a0:c9:3b:71:04, o que os três primeiros bytes (02:a0:c9) identificam?', 'O fabricante da interface (OUI)'),
                   ('Qual MAC de destino faz um quadro chegar a todas as interfaces da rede local?', 'ff:ff:ff:ff:ff:ff')], 1)
        expect(avancar).to_be_disabled()
        responder([('Quantos bits tem um endereço MAC?', '48 bits (6 bytes)')])
        pg.screenshot(path=str(OUT / 'm1-1-mac.png'), full_page=True)
        avancar.click()
        responder([('Para quem vai a pergunta "quem tem 10.1.1.22?"', 'Para todos (broadcast)'),
                   ('Quem responde, e para quem?', 'Só o PC F2, direto ao PC F1'),
                   ('Depois disso, onde fica o MAC do PC F2?', 'Na tabela ARP do PC F1 (ip neigh show)'),
                   ('Se o destino estivesse em outra rede, o PC F1 perguntaria o MAC de quem?', 'Do gateway (o roteador)')])
        avancar.click()
        expect(pg.locator('.af-caso')).to_have_count(1)
        pg.get_by_label(re.compile('^No PC F1: ver a tabela ARP')).fill('ip neigh show')
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()
        pg.screenshot(path=str(OUT / 'm1-4-conclusao.png'), full_page=True)
        concluir('fundamentos-ethernet-arp', 4, 'Laboratório 2')

        # ---- Módulo 3: Switch e VLANs (revisão de MAC e ARP) ----
        pg.goto(URL + '/modulos/servicos/lan', wait_until='networkidle')
        expect(avancar).to_be_disabled()
        responder([('Qual MAC de destino faz um quadro chegar a todas as interfaces da rede local?', 'ff:ff:ff:ff:ff:ff'),
                   ('Se o destino estivesse em outra rede, o PC F1 perguntaria o MAC de quem?', 'Do gateway (o roteador)')])
        pg.screenshot(path=str(OUT / '1-revisao.png'), full_page=True)
        avancar.click()
        responder([('PC V1 (porta eth2) envia um quadro para o MAC do PC F2. A tabela está vazia.', 'Para todas as portas, menos a eth2'),
                   ('PC F2 (porta eth1) responde para o MAC do PC V1.', 'Só para a eth2'),
                   ('PC V1 envia de novo para o MAC do PC F2.', 'Só para a eth1')])
        pg.screenshot(path=str(OUT / '2-switch.png'), full_page=True)
        avancar.click()
        responder([('O PC V1 envia um broadcast. Quem recebe?', 'Só o PC V2'),
                   ('PC V1 e PC F1 estão na mesma rede IP. Eles se falam?', 'Não: VLANs diferentes não trocam quadros'),
                   ('Uma porta ligada a um PC, que pertence a uma só VLAN e entrega quadros sem marcação, é:', 'Porta de acesso (PVID, untagged)'),
                   ('E a porta que liga dois switches e leva várias VLANs?', 'Porta tronco: quadros marcados com o número da VLAN')])
        pg.screenshot(path=str(OUT / '3-vlans.png'), full_page=True)
        avancar.click()
        for rotulo, comando in (('No PC F1: ver a tabela ARP', 'ip neigh show'), ('No switch: ver a tabela MAC', 'bridge fdb show'),
                                ('No switch: ver em que VLAN', 'bridge vlan show'), ('No switch: colocar a porta eth2', 'bridge vlan add dev eth2 vid 20'),
                                ('No switch: tirar a porta eth2', 'bridge vlan del dev eth2 vid 1')):
            pg.get_by_label(re.compile('^' + re.escape(rotulo))).fill(comando)
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('pvid untagged')
        ajuda = pg.locator('.af-caso', has_text='colocar a porta eth2').locator('.ajuda-comando')
        expect(pg.locator('.al-comandos li')).to_have_count(4)
        for botao in ('Pedir ajuda ao Link', 'Ver um exemplo', 'Quero uma pista'):
            ajuda.get_by_role('button', name=botao).click()
        expect(ajuda).to_contain_text('bridge vlan add dev eth3 vid 30 pvid untagged')
        expect(ajuda).not_to_contain_text('livro')
        pg.screenshot(path=str(OUT / '4-comandos-ajuda.png'), full_page=True)
        pg.get_by_label(re.compile('^No switch: colocar a porta eth2')).fill('bridge vlan add dev eth2 vid 20 pvid untagged')
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()
        concluir('servicos-lan', 5, 'Laboratório 8')

        # ---- Módulo 3: Transporte: portas, TCP e UDP ----
        pg.goto(URL + '/modulos/servicos/transporte', wait_until='networkidle')
        expect(pg.get_by_label('Faixas de portas')).to_contain_text('0 a 1023')
        expect(pg.locator('.aula-bloco')).not_to_contain_text('livro')
        expect(avancar).to_be_disabled()
        responder([('O IP leva o pacote até o computador. O que a porta indica?', 'A aplicação (o serviço) que vai receber os dados'),
                   ('Os números de porta vão de 0 a 65535. Em que faixa ficam as portas conhecidas, dos serviços padronizados?', '49152 a 65535'),
                   ('Um navegador pede uma página a um servidor web. Para qual porta vai o pedido, se nada foi mudado?', '80')], 1)
        responder([('Os números de porta vão de 0 a 65535. Em que faixa ficam as portas conhecidas, dos serviços padronizados?', '0 a 1023')])
        pg.screenshot(path=str(OUT / 't1-portas.png'), full_page=True)
        avancar.click()
        responder([('1º pacote: o cliente pede para abrir a conexão.', 'SYN'), ('2º pacote: o servidor, com a porta aberta, aceita.', 'SYN-ACK'),
                   ('3º pacote: o cliente confirma, e a conexão está aberta.', 'ACK'),
                   ('Terminada a comunicação, como a conexão TCP é encerrada de forma ordenada?', 'Com FIN e ACK dos dois lados')])
        pg.screenshot(path=str(OUT / 't2-tcp.png'), full_page=True)
        avancar.click()
        responder([('Antes de mandar dados, o UDP faz um handshake como o TCP?', 'Não: envia os datagramas direto, sem conexão'),
                   ('Uma consulta DNS (perguntar o endereço de um nome) normalmente usa:', 'UDP, porta 53'),
                   ('Qual destes usos precisa do TCP, porque não pode perder nem embaralhar dados?', 'Transferência de arquivos')])
        pg.screenshot(path=str(OUT / 't3-udp.png'), full_page=True)
        avancar.click()
        expect(pg.get_by_role('table', name='Captura de pacotes').get_by_role('row')).to_have_count(7)
        responder([('Quais linhas são o Three-Way Handshake?', '1, 2 e 3'),
                   ('Na linha 1, qual número diz que o pedido é para o servidor web?', '80'),
                   ('Por que a consulta DNS (linhas 5 e 6) não tem handshake antes?', 'É UDP: pergunta e resposta, sem conexão')])
        pg.screenshot(path=str(OUT / 't4-captura.png'), full_page=True)
        avancar.click()
        concluir('servicos-transporte', 5, 'aula de DHCP e DNS')
        b.close()
finally:
    srv.terminate()
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
