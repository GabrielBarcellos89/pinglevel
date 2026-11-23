"""Aula Roteamento estático no build candidato: percurso completo, travas de cada etapa e capturas.

Login e progresso simulados; os avanços e a conclusão são respondidos localmente e registrados para conferência.
Uso: capturar_aula_roteamento.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aula-roteamento)
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
OUT = Path(args[1] or ROOT / '.qa/capturas/aula-roteamento')
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

        pg.goto(URL + '/modulos/planejamento/roteamento', wait_until='networkidle')
        expect(pg.locator('.rt-topologia .rt-no')).to_have_count(4)
        expect(pg.locator('.aula-explica')).to_contain_text('Lab 6')
        pg.screenshot(path=str(OUT / '1-do-lab6.png'), full_page=True)
        avancar.click()

        def responder(respostas, erradas=()):
            for pergunta, resposta in respostas:
                pg.get_by_role('group', name=pergunta).get_by_role('button', name=resposta, exact=True).click()
            conferir.click()
            expect(pg.locator('.ag-retorno.erro')).to_have_count(len(erradas))

        expect(avancar).to_be_disabled()
        responder((('Sem nenhuma rota estática, o PC A faz ping ao PC B (192.168.20.10). Até onde o pedido chega?', 'Chega ao PC B'),
                   ('Que linha falta na tabela do R1 para o pedido seguir?', 'Uma rota para 192.168.20.0/24')), erradas=[1])
        responder((('Sem nenhuma rota estática, o PC A faz ping ao PC B (192.168.20.10). Até onde o pedido chega?',
                    'Chega ao R1, que descarta: ele não conhece 192.168.20.0/24'),))
        pg.screenshot(path=str(OUT / '2-o-que-conhece.png'), full_page=True)
        avancar.click()

        responder((('No R1, a rota para 192.168.20.0/24 usa qual próximo salto?', '10.0.0.2, o R2 no enlace'),
                   ('E no R2, a rota para 192.168.10.0/24 usa qual próximo salto?', '10.0.0.1, o R1 no enlace'),
                   ('Com a rota estática, o R1 recebe um pacote para 8.8.8.8. O que acontece?',
                    'É descartado: nenhuma linha contém 8.8.8.8 e não há rota padrão')))
        pg.screenshot(path=str(OUT / '3-rota-estatica.png'), full_page=True)
        avancar.click()

        expect(pg.locator('.rt-bloco-perguntas')).to_have_count(0)
        pg.get_by_role('button', name='Enviar o pacote').click()
        expect(pg.locator('.rt-no.ativo')).to_contain_text('PC A')
        for _ in range(3):
            pg.get_by_role('button', name='Próximo salto').click()
        expect(pg.locator('.rt-no.ativo')).to_contain_text('PC B')
        pg.get_by_role('button', name='Ver de novo').click()
        pg.get_by_role('button', name='Enviar o pacote').click()
        pg.get_by_role('button', name='Próximo salto').click()
        expect(pg.locator('.rt-tabela code.usada')).to_contain_text('via 10.0.0.2')
        responder((('Por que o R2 não precisou de rota estática para entregar ao PC B?', 'A rede do PC B está ligada ao R2: é rota direta'),))
        pg.screenshot(path=str(OUT / '4-seguir-pacote.png'), full_page=True)
        avancar.click()

        pg.get_by_role('button', name='Enviar a resposta').click()
        pg.get_by_role('button', name='Próximo salto').click()
        expect(pg.locator('.rt-no.falha')).to_contain_text('R2')
        responder((('Só com a rota no R1, onde a resposta do PC B para?', 'No R2, sem rota para 192.168.10.0/24'),
                   ('Que rota resolve a volta?', 'No R2: 192.168.10.0/24 via 10.0.0.1'),
                   ('O PC B precisa de uma rota para 192.168.10.0/24?', 'Não: a rota padrão dele já leva ao R2')))
        pg.screenshot(path=str(OUT / '5-ida-e-volta.png'), full_page=True)
        avancar.click()

        pg.get_by_label('No R1: rota para 192.168.20.0/24 pelo R2.').fill('ip route add 192.168.20.0/24 via 192.168.20.1')
        pg.get_by_label('No R2: rota para 192.168.10.0/24 pelo R1.').fill('ip route add 192.168.10.0/24 via 10.0.0.1')
        pg.get_by_label('No R1: remover a rota para 192.168.20.0/24.').fill('ip route del 192.168.20.0/24')
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_contain_text('vizinho')
        ajuda = pg.locator('.af-caso', has_text='pelo R2').locator('.ajuda-comando')
        for botao in ('Pedir ajuda ao Link', 'Ver o exemplo do livro', 'Quero uma pista'):
            ajuda.get_by_role('button', name=botao).click()
        expect(ajuda).to_contain_text('Exemplo 2.36')
        pg.screenshot(path=str(OUT / '6-comandos-ajuda.png'), full_page=True)
        pg.get_by_label('No R1: rota para 192.168.20.0/24 pelo R2.').fill('ip route add 192.168.20.0/24 via 10.0.0.2')
        conferir.click()
        expect(pg.locator('.ag-retorno.erro')).to_have_count(0)
        avancar.click()
        expect(pg.locator('.aula-conclusao')).to_contain_text('Laboratório 7')
        avancar.click()
        expect(pg.get_by_role('dialog')).to_contain_text('AULA CONCLUÍDA')
        b.close()
finally:
    srv.terminate()
etapas = [c['etapa_atual'] for u, c in envios if u == 'progresso/aula']
assert etapas == [1, 2, 3, 4, 5, 6], envios
assert envios[-1] == ('progresso/aula/concluir', {'aula_id': 'planejamento-roteamento'}), envios[-1]
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
