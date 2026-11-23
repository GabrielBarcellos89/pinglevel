"""Aula Ferramentas no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_ferramentas.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-ferramentas)
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT / '.qa/dist')
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-ferramentas')
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

        pg.goto(URL + '/modulos/fundamentos/ferramentas', wait_until='networkidle')
        expect(avancar).to_be_disabled()
        for trecho in pg.locator('.af-trecho').all():
            trecho.click()
        expect(pg.locator('.ag-decisao')).to_contain_text('broadcast')
        pg.screenshot(path=str(OUT / '1-interface.png'), full_page=True)
        avancar.click()

        for i, situacao in ((1, 'Ativa, mas sem endereço IPv4'), (2, 'Ativa e com endereço IPv4'), (3, 'Com endereço, mas desativada (sem UP)')):
            pg.get_by_role('group', name=f'Situação do computador {i}').get_by_role('button', name=situacao).click()
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()

        for ip, linha in (('192.168.10.20', '192.168.10.0/24 (direto)'), ('192.168.20.10', 'default (gateway)'),
                          ('8.8.8.8', 'default (gateway)'), ('192.168.10.1', 'default (gateway)')):
            pg.get_by_role('group', name=f'Rota para {ip}').get_by_role('button', name=linha).click()
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(1)
        expect(avancar).to_be_disabled()
        pg.get_by_role('group', name='Rota para 192.168.10.1').get_by_role('button', name='192.168.10.0/24 (direto)').click()
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '3-tabela.png'), full_page=True)
        avancar.click()

        for rotulo, comando in (('Configurar o endereço', 'ip addr add 192.168.10.30/24 dev eth0'),
                                ('Criar a rota padrão', 'ip route add default via 192.168.10.1'),
                                ('Remover a rota padrão', 'ip route del default'),
                                ('Remover o endereço', 'ip addr del 192.168.10.30/24 dev eth1')):
            pg.get_by_label(rotulo).fill(comando)
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('eth0')
        # Ajuda do Link no objetivo errado: partes, exemplo do livro e pista, um nível por clique.
        ajuda = pg.locator('.af-caso', has_text='Remover o endereço').locator('.ajuda-comando')
        for botao in ('Pedir ajuda ao Link', 'Ver o exemplo do livro', 'Quero uma pista'):
            ajuda.get_by_role('button', name=botao).click()
        expect(ajuda).to_contain_text('Exemplo 2.25')
        expect(ajuda).to_contain_text('dev ____')
        pg.screenshot(path=str(OUT / '4-ajuda-link.png'), full_page=True)
        pg.get_by_label('Remover o endereço').fill('ip addr del 192.168.10.30/24 dev eth0')
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '4-comandos.png'), full_page=True)
        avancar.click()

        for mensagem, causa in (('ping: connect: Network unreachable', 'O computador não tem rota'),
                                ('2 packets transmitted, 0 received, 100% packet loss', 'O pedido saiu'),
                                ('Error: Nexthop has invalid gateway.', 'O gateway informado'),
                                ('Error: ipv4: Address already assigned.', 'Esse endereço já está')):
            pg.get_by_role('group', name=f'Causa de {mensagem}').get_by_role('button', name=__import__('re').compile(causa)).click()
        pg.get_by_role('button', name='Conferir').click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        pg.screenshot(path=str(OUT / '5-mensagens.png'), full_page=True)
        avancar.click()
        expect(pg.locator('.aula-conclusao')).to_contain_text('Laboratório 4')
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'fundamentos-ferramentas'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
