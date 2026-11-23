"""Lab3: decisão local/remota e gateway; identidade e recompensas preservadas."""
from copy import deepcopy

LABORATORIO_ID = 'saindo-da-rede-local'
TITULO = 'Dentro ou fora da minha rede?'
DESCRICAO = 'Comprove a comunicação local e configure o gateway para alcançar outra rede.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
NOS = {
    1: {'id': 1, 'nome': 'PC Atendimento', 'tipo': 'computador', 'ip': '192.168.10.10', 'prefixo': 24},
    2: {'id': 2, 'nome': 'PC Colega', 'tipo': 'computador', 'ip': '192.168.10.20', 'prefixo': 24},
    3: {'id': 3, 'nome': 'Switch', 'tipo': 'switch'},
    4: {'id': 4, 'nome': 'Servidor', 'tipo': 'servidor', 'ip': '192.168.20.10', 'prefixo': 24},
    5: {'id': 5, 'nome': 'Roteador', 'tipo': 'roteador'},
}
ETAPAS = (
    {'id': 'local', 'titulo': 'Comunicação local', 'orientacao': 'Preveja e teste a comunicação com o colega.'},
    {'id': 'rede', 'titulo': 'Outra rede', 'orientacao': 'Compare os endereços e identifique a rede do servidor.'},
    {'id': 'gateway', 'titulo': 'Gateway', 'orientacao': 'Escolha a interface local do roteador como gateway.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'Teste a comunicação e explique a diferença entre os destinos.'},
)


def dados_iniciais():
    return {'revisao': 0,
        'classificacao': {'resposta': None, 'correta': False},
        'teste_local': {'registrado': False, 'alcance': None, 'detalhes': []},
        'terminal': [],
        'gateway': {'valor': '', 'confirmado': False, 'observado': None},
        'previsao': {'local': None, 'remota': None, 'registrada': False},
        'antes': {'registrado': False, 'local': None, 'remoto': None, 'detalhes': []},
        'conferencia': {'ok': False, 'gateway': None, 'interface': 'eth0', 'saida': ''},
        'depois': {'registrado': False, 'local': None, 'remoto': None, 'rota_confirmada': False, 'detalhes': []},
        'interpretacao': {'resposta': None, 'correta': False, 'feedback': ''}}


def estado_publico(dados, ativo=False):
    s = deepcopy(dados or dados_iniciais())
    feitos = set()
    if ativo and s['antes']['registrado'] and s['antes']['local'] is True:
        feitos.add('local')
    if ativo and s.get('classificacao', {}).get('correta') is True:
        feitos.add('rede')
    if ativo and s['gateway']['confirmado'] and s['conferencia']['ok']:
        feitos.add('gateway')
    d = s['depois']
    if (ativo and d['registrado'] and d['local'] is True and d['remoto'] is True
            and d['rota_confirmada'] and s['interpretacao']['correta']):
        feitos.add('comprovar')
    etapas = [{**e, 'concluida': e['id'] in feitos} for e in ETAPAS]
    return {'id': LABORATORIO_ID, 'titulo': TITULO, 'descricao': DESCRICAO, 'xp': XP,
        'nos': deepcopy(list(NOS.values())), 'etapas': etapas,
        'proxima_etapa': next((e['id'] for e in etapas if not e['concluida']), None),
        'concluido': all(e['concluida'] for e in etapas), 'retorno_preparado': True, **s}


def montar_estado(evidencias=None):
    return estado_publico(None)


def detectar_evidencias(node_id, comando, codigo, saida):
    return set()
