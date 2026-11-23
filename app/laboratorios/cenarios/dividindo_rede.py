"""Lab5 — Dividindo uma rede: 192.168.50.0/24 em blocos /26; o Vendas é o modelo e o aluno põe o Financeiro no 2º
bloco. No fim, um chamado de limite: um PC do Vendas com endereço do bloco errado (roteiro: doc 53)."""
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'dividindo-uma-rede'
TITULO = 'Dividindo uma rede'
DESCRICAO = 'Coloque o Financeiro no seu bloco /26: plano, roteador, computadores e um chamado de limite.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.50.0/24'

SETORES = {
    'vendas': {'nome': 'Vendas', 'rede': '192.168.50.0', 'prefixo': 26, 'gateway': '192.168.50.1', 'interface': 'eth0'},
    'financeiro': {'nome': 'Financeiro', 'rede': '192.168.50.64', 'prefixo': 26, 'gateway': '192.168.50.65', 'interface': 'eth1'},
}
SETORES_MODELO = ('vendas',)  # o bloco do Vendas é dado como exemplo desde o início
# Chave usada na API → nó do CORE, nome, host (prompt do terminal), tipo, setor e interfaces visíveis ao aluno.
NOS = {
    'v1': {'no': 1, 'nome': 'PC V1', 'host': 'pc-v1', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'v2': {'no': 2, 'nome': 'PC V2', 'host': 'pc-v2', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'roteador': {'no': 5, 'nome': 'Roteador', 'host': 'roteador', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1']},
    'f1': {'no': 6, 'nome': 'PC F1', 'host': 'pc-f1', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
    'f2': {'no': 7, 'nome': 'PC F2', 'host': 'pc-f2', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
}
INICIAL = {
    'v1': {'interfaces': {'eth0': ['192.168.50.10/26']}, 'rota_padrao': '192.168.50.1'},
    'v2': {'interfaces': {'eth0': ['192.168.50.70/26']}, 'rota_padrao': None},
    'roteador': {'interfaces': {'eth0': ['192.168.50.1/26'], 'eth1': []}, 'rota_padrao': None},
    'f1': {'interfaces': {'eth0': []}, 'rota_padrao': None},
    'f2': {'interfaces': {'eth0': []}, 'rota_padrao': None},
}
PLANO = [
    {'id': 'rede', 'rotulo': 'Rede', 'grupo': 'financeiro', 'tipo': 'ip', 'esperado': '192.168.50.64'},
    {'id': 'gateway', 'rotulo': 'Gateway (1º host)', 'grupo': 'financeiro', 'tipo': 'ip', 'esperado': '192.168.50.65'},
    {'id': 'broadcast', 'rotulo': 'Broadcast', 'grupo': 'financeiro', 'tipo': 'ip', 'esperado': '192.168.50.127'},
]
CHAMADO = {
    'no': 'v2', 'titulo': 'Chamado · PC V2', 'sintoma': 'Não fala com ninguém, nem com o PC V1 ao lado.',
    'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, observe a interface do PC V2 com ip addr show.',
    'causas': {
        'fora-do-bloco': 'O endereço está fora do bloco do Vendas: pertence ao bloco do Financeiro.',
        'cabo': 'O cabo do PC V2 está desconectado.',
        'roteador': 'O roteador está desligado.'},
    'correta': 'fora-do-bloco',
    'acerto': 'Isso mesmo: 192.168.50.70/26 é do bloco .64–.127. No switch do Vendas, ninguém está nessa rede.',
    'erro': 'Compare o endereço do PC V2 com o bloco do Vendas (.0 a .63): ele está dentro?',
}
ETAPAS = (
    {'id': 'plano', 'titulo': 'Plano', 'orientacao': 'Escreva a rede, o gateway e o broadcast do bloco do Financeiro.'},
    {'id': 'roteador', 'titulo': 'Roteador', 'orientacao': 'Dê ao roteador o gateway do Financeiro na interface eth1.'},
    {'id': 'financeiro', 'titulo': 'Financeiro', 'orientacao': 'Configure os PCs F1 e F2 e comprove com ping.'},
    {'id': 'chamado', 'titulo': 'Chamado', 'orientacao': CHAMADO['sintoma']},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os cinco equipamentos e repete os testes.'},
)
# Quem pode ser alterado em cada etapa: nó → interfaces.
ALTERAVEIS = {'roteador': {'roteador': ('eth1',)}, 'financeiro': {'f1': ('eth0',), 'f2': ('eth0',)}, 'chamado': {'v2': ('eth0',)}}
V1 = '192.168.50.10'


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def _testou(s, origem, destino):
    return destino is not None and s['testes'][origem].get(destino) is True


def etapa_ok(s, etapa):
    e = s['estados']
    if etapa == 'plano':
        return s['plano']['correto']
    if etapa == 'roteador':
        return base.roteador_ok(e, 'roteador', SETORES.values())
    if etapa == 'financeiro':
        if not all(base.pc_ok(e, no, SETORES['financeiro']) for no in ('f1', 'f2')):
            return False
        return any(_testou(s, a, base.endereco_pc(e, b)) and _testou(s, a, V1) for a, b in (('f1', 'f2'), ('f2', 'f1')))
    if etapa == 'chamado':
        return (s['diagnosticos']['chamado']['correta'] and base.pc_ok(e, 'v2', SETORES['vendas'])
                and any(_testou(s, 'v2', base.endereco_pc(e, f)) for f in ('f1', 'f2')))
    return False


def problemas(s):
    """O que impede a conclusão, relendo a configuração (usado pela validação final)."""
    e = s['estados']
    erros = []
    if not base.roteador_ok(e, 'roteador', SETORES.values()):
        erros.append('Roteador')
    erros += [NOS[no]['nome'] for no in ('v1', 'v2', 'f1', 'f2') if not base.pc_ok(e, no, SETORES[NOS[no]['setor']])]
    return erros


def testes_finais(s):
    return [('v2', base.endereco_pc(s['estados'], 'f1')), ('f1', V1), ('f2', base.endereco_pc(s['estados'], 'v2'))]


def estado_publico(dados, ativo=False):
    return base.estado_publico(sys.modules[__name__], dados, ativo)


def montar_estado(evidencias=None):
    return estado_publico(None)
