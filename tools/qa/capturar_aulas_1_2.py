"""Entrada de quem é novo e aulas 1 e 2 no build candidato (revisão de 30/10/2026).

Percorre como aluno novo: apresentação do Link (3 telas) → aula 1 inteira → conquista com +100 XP → aula 2 inteira
(por que camadas, tabela, camadas com mapa e explicação simples, TCP/IP e teste final por situações) → conquista.
Login e progresso simulados; nada chega ao servidor.
Uso: capturar_aulas_1_2.py [dist] [pasta_saida]  (padrão: .qa/dist e .qa/capturas/aulas-1-2)
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
OUT = Path(args[1] or ROOT / '.qa/capturas/aulas-1-2')
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:5179'
erros = []
aulas = {}
escritas = []


def api(route):
    req = route.request
    if req.url.endswith('/api/auth/me'):
        dados = {'sucesso': True, 'usuario': {'id': 17, 'login': 'qa', 'nome': 'Aluno QA', 'papel': 'aluno', 'troca_senha_obrigatoria': False}}
    elif '/api/progresso/me' in req.url:
        lista = [{'aula_id': k, 'concluida': v, 'etapa_atual': 5} for k, v in aulas.items()]
        dados = {'sucesso': True, 'progresso': {'usuario_id': 17, 'aulas': lista, 'laboratorios': [], 'xp_total': 100 * len(lista)}}
    elif req.method == 'POST' and req.url.endswith('/api/progresso/aula/concluir'):
        aula = req.post_data_json['aula_id']
        escritas.append(('concluir', aula))
        nova = not aulas.get(aula)
        aulas[aula] = True
        dados = {'sucesso': True, 'progresso': {'xp_concedido': 100 if nova else 0}}
    elif req.method == 'POST' and req.url.endswith('/api/progresso/aula'):
        dados = {'sucesso': True}
    else:
        return route.abort()
    route.fulfill(status=200, content_type='application/json', body=json.dumps(dados))


def seguir(pg):
    # Avança uma etapa e espera a gravação terminar (cliques durante "Salvando..." são ignorados pela aula).
    antes = pg.locator('.aula-progresso-area').text_content()
    pg.locator('.aula-navegacao .botao-avancar').click()
    expect(pg.locator('.aula-progresso-area')).not_to_have_text(antes)


def foto(pg, nome):
    pg.wait_for_timeout(250)
    pg.screenshot(path=str(OUT / f'{nome}.png'))


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
        ctx = b.new_context(viewport={'width': 1440, 'height': 900})
        ctx.route('**/api/**', api)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: erros.append(str(e)))
        avancar = pg.locator('.aula-navegacao .botao-avancar')

        # Entrada: três telas e o último botão leva direto à aula 1.
        pg.goto(URL + '/', wait_until='networkidle')
        dialogo = pg.get_by_role('dialog')
        expect(dialogo).to_contain_text('Olá, eu sou o Link!')
        foto(pg, '01-entrada-1')
        for _ in range(2):
            dialogo.get_by_role('button', name='Continuar', exact=True).click()
        expect(dialogo).to_contain_text('Comece pela aula 1')
        expect(dialogo.get_by_role('button', name='Explorar a plataforma primeiro')).to_be_visible()
        foto(pg, '02-entrada-3')
        dialogo.get_by_role('button', name='Começar a primeira aula').click()
        pg.wait_for_url('**/modulos/fundamentos/aula-1')
        expect(pg.get_by_role('dialog')).to_have_count(0)

        # Aula 1: switch × roteador, desafio rápido com o Link pensativo e, ao acertar, com os polegares.
        seguir(pg)
        pg.get_by_role('button', name='Conectar dispositivos').click()
        seguir(pg)
        pg.get_by_role('button', name='Equipamentos de conexão').click()
        regiao = pg.get_by_role('region', name='Switch e roteador')
        regiao.get_by_role('button', name='Roteador', exact=True).click()
        expect(regiao.get_by_role('status')).to_contain_text('Isso!')
        seguir(pg)
        seguir(pg)
        assert 'pensativo' in pg.locator('.link-painel img').get_attribute('src')
        for i, r in enumerate(['LAN', 'LAN', 'WAN', 'WAN']):
            pg.locator('.lista-situacoes article').nth(i).get_by_role('button', name=r, exact=True).click()
        pg.get_by_role('button', name='Conferir respostas').click()
        assert 'polegares' in pg.locator('.link-painel img').get_attribute('src')
        foto(pg, '10-aula1-desafio')
        seguir(pg)
        pg.get_by_role('button', name='Computador A').click()
        pg.get_by_role('button', name='Computador B').click()
        pg.get_by_role('button', name='Validar seleção').click()
        seguir(pg)
        # Conclusão: um só caminho (o rodapé); o botão que pulava a conclusão saiu.
        expect(pg.get_by_role('button', name='Continuar: modelos OSI e TCP/IP')).to_have_count(0)
        assert 'estrela' in pg.locator('.link-painel img').get_attribute('src')
        foto(pg, '11-aula1-conclusao')
        avancar.click()
        conquista = pg.get_by_role('dialog')
        expect(conquista).to_contain_text('+100 XP')
        expect(conquista).to_contain_text('O que é uma rede?')
        assert escritas == [('concluir', 'fundamentos-aula-1')]
        foto(pg, '12-aula1-conquista')
        conquista.get_by_role('button', name='Seguir: Modelos OSI e TCP/IP').click()
        pg.wait_for_url('**/modulos/fundamentos/modelos-de-rede')

        # Aula 2: por que camadas → tabela simples → camadas com mapa fixo e explicação simples.
        expect(pg.locator('[data-testid="scene-title"]')).to_have_text('Por que dividir em camadas?')
        expect(pg.locator('.osi-encomenda li')).to_have_count(5)
        foto(pg, '20-aula2-por-que-camadas')
        seguir(pg)
        expect(pg.locator('[data-testid="scene-title"]')).to_have_text('Vamos conhecer a tabela OSI')
        expect(pg.locator('.osi-tabela-intro')).to_contain_text('O app pede para enviar a mensagem.')
        foto(pg, '21-aula2-tabela')
        seguir(pg)
        seguir(pg)
        pg.get_by_role('button', name='Enviar', exact=True).click()
        expect(pg.locator('.osi-mapa-fixo li.atual')).to_contain_text('Aplicação')
        expect(pg.locator('.osi-simples')).to_contain_text('Em palavras simples')
        foto(pg, '22-aula2-camada7')
        seguir(pg)
        pg.get_by_role('button', name='Ver como o texto é representado', exact=True).click()
        seguir(pg)
        for nome in ['Organizar a troca', 'Ver as portas', 'Identificar o destino IP', 'Preparar o quadro Wi-Fi', 'Transmitir pelo Wi-Fi']:
            pg.get_by_role('button', name=nome, exact=True).click()
            if nome == 'Preparar o quadro Wi-Fi':
                expect(pg.locator('.osi-termos')).to_contain_text('MAC')
                expect(pg.locator('.osi-mapa-fixo li.feita')).to_have_count(5)
                foto(pg, '23-aula2-camada2')
            seguir(pg)
        for _ in range(6):
            pg.get_by_role('button', name='Próxima camada no recebimento', exact=True).click()
        avancar.click()

        # TCP/IP numa tela própria, depois o teste final por situações.
        expect(pg.get_by_role('heading', name='E o TCP/IP?')).to_be_visible()
        expect(pg.get_by_role('table', name='Correspondência entre TCP/IP e OSI').locator('tbody tr')).to_have_count(4)
        foto(pg, '24-aula2-tcpip')
        # TCP ou UDP: o teste final só abre com as quatro situações certas.
        pg.get_by_role('button', name='TCP ou UDP?').click()
        expect(pg.get_by_role('heading', name='TCP ou UDP? Dois jeitos de transportar')).to_be_visible()
        for i, r in enumerate(['TCP', 'UDP', 'UDP', 'UDP']):
            pg.locator('.lista-situacoes article').nth(i).get_by_role('button', name=r, exact=True).click()
        pg.get_by_role('button', name='Conferir respostas').click()
        expect(pg.locator('.lista-situacoes article.incorreta')).to_have_count(1)
        expect(pg.get_by_role('button', name='Ir para o teste final')).to_be_disabled()
        pg.locator('.lista-situacoes article').nth(1).get_by_role('button', name='TCP', exact=True).click()
        pg.get_by_role('button', name='Conferir respostas').click()
        expect(pg.locator('.feedback-desafio')).to_contain_text('Isso!')
        pg.screenshot(path=str(OUT / '24b-aula2-tcp-udp.png'), full_page=True)
        pg.get_by_role('button', name='Ir para o teste final').click()
        expect(pg.locator('.modelos-situacao')).to_have_count(7)
        expect(pg.locator('select')).to_have_count(0)
        expect(pg.locator('.modelos-ver-tabela')).not_to_have_attribute('open', '')
        respostas = ['6 · Apresentação', 'A porta · 4 · Transporte', 'O endereço IP de destino · 3 · Rede', '2 · Enlace',
                     'Da camada 1 (Física) até a 7 (Aplicação)', 'Transporte', 'UDP · manda e segue, sem conferir']
        for i, r in enumerate(respostas):
            pg.locator('.modelos-situacao').nth(i).get_by_role('button', name=r, exact=True).click()
        pg.get_by_role('button', name='Conferir respostas').click()
        expect(pg.locator('.modelos-situacao.errada')).to_have_count(2)
        expect(pg.get_by_role('button', name='Concluir aula')).to_be_disabled()
        foto(pg, '25-aula2-teste-com-erro')
        pg.screenshot(path=str(OUT / '25-aula2-teste-com-erro-inteira.png'), full_page=True)
        pg.get_by_role('button', name='Tentar de novo').click()
        expect(pg.locator('.modelos-situacao button.selecionada')).to_have_count(5)
        pg.locator('.modelos-situacao').nth(3).get_by_role('button', name='1 · Física', exact=True).click()
        pg.locator('.modelos-situacao').nth(5).get_by_role('button', name='Aplicação', exact=True).click()
        pg.get_by_role('button', name='Conferir respostas').click()
        expect(pg.locator('.feedback-desafio')).to_contain_text('Tudo certo')
        assert 'polegares' in pg.locator('.link-painel img').get_attribute('src')
        pg.get_by_role('button', name='Concluir aula').click()
        expect(pg.get_by_role('dialog')).to_contain_text('+100 XP')
        expect(pg.get_by_role('dialog')).to_contain_text('Seguir: Endereçamento IPv4')
        assert escritas[-1] == ('concluir', 'fundamentos-modelos-osi-tcpip')
        foto(pg, '26-aula2-conquista')
        b.close()
finally:
    srv.terminate()
if erros:
    raise SystemExit(f'erros de página: {erros}')
print(json.dumps({'aprovado': True, 'evidencias': str(OUT)}))
