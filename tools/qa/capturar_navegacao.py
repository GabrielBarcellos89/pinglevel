"""Início, Trilha, Módulos e Laboratórios no build candidato, com progresso simulado (uma aula concluída, outra em andamento).
Uso: capturar_navegacao.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/navegacao)
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
CATALOGO = (ROOT / 'frontend/src/data/catalogo.js').read_text()  # contagens esperadas de cartões
args = sys.argv[1:] + [None, None]
DIST = Path(args[0] or ROOT / '.qa/dist')
OUT = Path(args[1] or ROOT / '.qa/capturas/navegacao')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
PROGRESSO = {'usuario_id': 17, 'xp_total': 100, 'aulas': [
    {'aula_id': 'fundamentos-aula-1', 'concluida': True, 'percentual': 100},
    {'aula_id': 'fundamentos-modelos-osi-tcpip', 'concluida': False, 'percentual': 50}], 'laboratorios': []}
erros = []


def api(route):
    u = route.request.url
    if u.endswith('/api/auth/me'):
        d = {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
    elif '/api/progresso/me' in u:
        d = {'sucesso': True, 'progresso': PROGRESSO}
    else:
        return route.abort()
    route.fulfill(status=200, content_type='application/json', body=json.dumps(d))


srv = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(DIST), '--host', '127.0.0.1', '--port', '5179',
                        '--strictPort'], cwd=ROOT / 'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(.1)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        c = b.new_context(viewport={'width': 1440, 'height': 1000})
        c.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim')")
        c.route('**/api/**', api)
        pg = c.new_page()
        pg.on('pageerror', lambda e: erros.append(str(e)))
        # Início: próximo passo e progresso vêm da trilha (1 de 22; a aula em andamento é o próximo passo).
        pg.goto(URL + '/', wait_until='networkidle')
        expect(pg.locator('.proximo-passo')).to_contain_text('Modelos OSI e TCP/IP')
        expect(pg.locator('.proximo-passo')).to_contain_text('parada 2 de 22')
        expect(pg.locator('.resumo')).to_contain_text('1 de 22 paradas')
        expect(pg.locator('.cartao-modulo')).to_have_count(3)
        expect(pg.locator('.cartao-modulo.atual')).to_contain_text('Fundamentos')
        pg.screenshot(path=str(OUT / 'inicio.png'), full_page=True)
        # Ajuda reabre a apresentação do Link; para quem já começou, a última tela mostra o próprio próximo passo.
        pg.get_by_role('button', name='Ajuda').click()
        for _ in range(2):
            pg.get_by_role('button', name='Continuar', exact=True).click()
        expect(pg.get_by_role('dialog')).to_contain_text('Siga o seu próximo passo')
        expect(pg.get_by_role('dialog')).to_contain_text('Modelos OSI e TCP/IP')
        pg.get_by_role('dialog').get_by_role('button', name='Continuar aula').click()
        expect(pg.get_by_role('dialog')).to_have_count(0)
        pg.wait_for_url('**/modulos/fundamentos/modelos-de-rede')
        pg.goto(URL + '/trilha', wait_until='networkidle')
        expect(pg.locator('.trilha-parada')).to_have_count(22)
        expect(pg.locator('.trilha-parada.concluida')).to_have_count(1)
        expect(pg.locator('.trilha-parada.atual')).to_contain_text('Modelos OSI')
        # Bloqueadas são as paradas ainda sem atividade publicada em data/trilha.js.
        paradas = [linha for linha in (ROOT / 'frontend/src/data/trilha.js').read_text().splitlines() if linha.strip().startswith('{ modulo:')]
        expect(pg.locator('.trilha-parada.bloqueada')).to_have_count(sum('atividade:' not in linha for linha in paradas))
        pg.screenshot(path=str(OUT / 'trilha.png'), full_page=True)
        pg.locator('.trilha-parada.atual button').click()
        pg.wait_for_url('**/modulos/fundamentos/modelos-de-rede')
        pg.goto(URL + '/modulos', wait_until='networkidle')
        expect(pg.locator('.catalogo-card')).to_have_count(CATALOGO.count("tipo: 'aula'"))
        expect(pg.get_by_role('heading', name='Aulas', exact=True)).to_be_visible()
        expect(pg.locator('.menu-item.ativo')).to_have_text('Aulas')
        # Cada aba mostra um tipo só, sem filtro de tipo; cada cartão tem a arte da sua parada.
        expect(pg.get_by_label('Tipo de atividade')).to_have_count(0)
        expect(pg.locator('.catalogo-card-corpo img')).to_have_count(CATALOGO.count("tipo: 'aula'"))
        pg.screenshot(path=str(OUT / 'modulos.png'), full_page=True)
        pg.get_by_role('link', name='Laboratórios').click()
        pg.wait_for_url('**/laboratorios')
        expect(pg.locator('.catalogo-card')).to_have_count(CATALOGO.count("tipo: 'laboratorio'"))
        expect(pg.get_by_role('heading', name='Laboratórios', exact=True)).to_be_visible()
        pg.screenshot(path=str(OUT / 'laboratorios.png'), full_page=True)
        # Trilha inteira concluída: a arte de parabéns aparece acima do mapa (e não aparece com a trilha pela metade).
        expect(pg.locator('.trilha-conclusao')).to_have_count(0)
        ids = re.findall(r"atividade: '([^']+)'", (ROOT / 'frontend/src/data/trilha.js').read_text())
        tudo = {'usuario_id': 17, 'xp_total': 999, 'aulas': [{'aula_id': i, 'concluida': True, 'percentual': 100} for i in ids],
                'laboratorios': [{'laboratorio_id': i, 'concluido': True} for i in ids]}
        completo = b.new_context(viewport={'width': 1440, 'height': 1000})
        completo.add_init_script("localStorage.setItem('pinglevel:link-apresentado:qa','sim')")
        completo.route('**/api/**', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'sucesso': True, 'progresso': tudo} if '/api/progresso/me' in r.request.url else
            {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}})))
        tc = completo.new_page()
        tc.on('pageerror', lambda e: erros.append(str(e)))
        tc.goto(URL + '/trilha', wait_until='networkidle')
        expect(tc.locator('.trilha-placar strong')).to_contain_text(f'{len(ids)} de {len(ids)}')
        expect(tc.get_by_alt_text('Parabéns! Você completou a trilha inicial do PingLevel.')).to_be_visible()
        tc.screenshot(path=str(OUT / 'trilha-concluida.png'))
        # Assinatura do autor no menu e agradecimento ao autor dos livros (23/11/2026).
        expect(tc.locator('.sidebar .criado-por')).to_contain_text('Gabriel Barcellos')
        tc.goto(URL + '/livros', wait_until='networkidle')
        expect(tc.locator('.livros-agradecimento')).to_contain_text('Eduardo Maroñas Monks')
        tc.locator('.livros-agradecimento').scroll_into_view_if_needed()
        tc.screenshot(path=str(OUT / 'livros-agradecimento.png'))
        # Login sem sessão: o pedido de acesso é um formulário no próprio site (23/11/2026), em tela de notebook.
        pedidos = []

        def api_anonima(r):
            if r.request.url.endswith('/api/acesso/pedido'):
                pedidos.append(json.loads(r.request.post_data))
                return r.fulfill(status=201, content_type='application/json', body='{"sucesso": true, "mensagem": "ok"}')
            r.fulfill(status=401, content_type='application/json', body='{"sucesso": false}')
        anonimo = b.new_context(viewport={'width': 1366, 'height': 768})
        anonimo.route('**/api/**', api_anonima)
        lg = anonimo.new_page()
        lg.on('pageerror', lambda e: erros.append(str(e)))
        lg.goto(URL + '/login', wait_until='networkidle')
        expect(lg.locator('.login-pedido')).to_contain_text('acesso@pinglevel.com.br')
        assert lg.evaluate('document.documentElement.scrollHeight') <= 768, 'o login não cabe na tela do notebook'
        lg.screenshot(path=str(OUT / 'login.png'))
        lg.get_by_role('button', name='Pedir acesso').click()
        lg.get_by_label('Nome completo').fill('Maria Souza')
        lg.get_by_label('E-mail').fill('maria@exemplo.com.br')
        lg.get_by_label('Instituição ou curso').fill('Senac')
        assert lg.evaluate('document.documentElement.scrollHeight') <= 768, 'o pedido não cabe na tela do notebook'
        lg.screenshot(path=str(OUT / 'login-pedido.png'))
        lg.get_by_role('button', name='Enviar pedido').click()
        expect(lg.get_by_role('status')).to_contain_text('maria@exemplo.com.br')
        assert pedidos == [{'nome': 'Maria Souza', 'email': 'maria@exemplo.com.br', 'instituicao': 'Senac', 'mensagem': '', 'site': ''}], pedidos
        lg.get_by_role('button', name='Voltar ao login').click()
        expect(lg.get_by_label('Usuário')).to_be_visible()
        b.close()
finally:
    srv.terminate()
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
