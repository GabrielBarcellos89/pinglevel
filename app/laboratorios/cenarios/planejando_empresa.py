"""Lab6 — Planejando uma empresa: plano VLSM de 192.168.80.0/24 para três setores e a rede funcionando no CORE:
uma interface do roteador por setor e um PC em cada um (roteiro: doc 55)."""
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'planejando-uma-empresa'
TITULO = 'Planejando uma empresa'
DESCRICAO = 'Monte o plano VLSM de três setores e coloque a rede para funcionar: roteador e computadores.'
XP = 100
TEMPO_LIMITE = 1200
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.80.0/24'

SETORES = {
    'atendimento': {'nome': 'Atendimento', 'pedido': '100 computadores + gateway', 'rede': '192.168.80.0', 'prefixo': 25,
                    'gateway': '192.168.80.1', 'interface': 'eth0'},
    'vendas': {'nome': 'Vendas', 'pedido': '50 computadores + gateway', 'rede': '192.168.80.128', 'prefixo': 26,
               'gateway': '192.168.80.129', 'interface': 'eth1'},
    'financeiro': {'nome': 'Financeiro', 'pedido': '20 computadores + gateway', 'rede': '192.168.80.192', 'prefixo': 27,
                   'gateway': '192.168.80.193', 'interface': 'eth2'},
}
NOS = {
    'atendimento': {'no': 1, 'nome': 'PC Atendimento', 'host': 'pc-atendimento', 'tipo': 'pc', 'setor': 'atendimento', 'interfaces': ['eth0']},
    'vendas': {'no': 2, 'nome': 'PC Vendas', 'host': 'pc-vendas', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'roteador': {'no': 5, 'nome': 'Roteador', 'host': 'roteador', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1', 'eth2']},
    'financeiro': {'no': 6, 'nome': 'PC Financeiro', 'host': 'pc-financeiro', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
}
INICIAL = {
    'atendimento': {'interfaces': {'eth0': []}, 'rota_padrao': None},
    'vendas': {'interfaces': {'eth0': []}, 'rota_padrao': None},
    'roteador': {'interfaces': {'eth0': [], 'eth1': [], 'eth2': []}, 'rota_padrao': None},
    'financeiro': {'interfaces': {'eth0': []}, 'rota_padrao': None},
}
PLANO = [campo for chave, s in SETORES.items() for campo in (
    {'id': f'{chave}-prefixo', 'rotulo': 'Prefixo', 'grupo': chave, 'tipo': 'prefixo', 'esperado': str(s['prefixo'])},
    {'id': f'{chave}-rede', 'rotulo': 'Rede', 'grupo': chave, 'tipo': 'ip', 'esperado': s['rede']})]
ETAPAS = (
    {'id': 'plano', 'titulo': 'Plano VLSM', 'orientacao': 'Prefixo e rede de cada setor, do maior bloco para o menor.'},
    {'id': 'roteador', 'titulo': 'Roteador', 'orientacao': 'Uma interface por setor, com o primeiro host de cada bloco.'},
    {'id': 'pcs', 'titulo': 'Computadores', 'orientacao': 'Endereço do bloco e rota padrão em cada PC; teste os setores.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os equipamentos e repete os testes.'},
)
ALTERAVEIS = {'roteador': {'roteador': ('eth0', 'eth1', 'eth2')},
              'pcs': {'atendimento': ('eth0',), 'vendas': ('eth0',), 'financeiro': ('eth0',)}}
PCS = ('atendimento', 'vendas', 'financeiro')


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def etapa_ok(s, etapa):
    e = s['estados']
    if etapa == 'plano':
        return s['plano']['correto']
    if etapa == 'roteador':
        return base.roteador_ok(e, 'roteador', SETORES.values())
    if etapa == 'pcs':
        if not all(base.pc_ok(e, pc, SETORES[pc]) for pc in PCS):
            return False
        return all(s['testes']['atendimento'].get(base.endereco_pc(e, pc)) is True for pc in ('vendas', 'financeiro'))
    return False


def problemas(s):
    e = s['estados']
    erros = [] if base.roteador_ok(e, 'roteador', SETORES.values()) else ['Roteador']
    return erros + [NOS[pc]['nome'] for pc in PCS if not base.pc_ok(e, pc, SETORES[pc])]


def testes_finais(s):
    ip = lambda pc: base.endereco_pc(s['estados'], pc)  # noqa: E731
    return [('atendimento', ip('vendas')), ('atendimento', ip('financeiro')), ('vendas', ip('financeiro'))]


def estado_publico(dados, ativo=False):
    return base.estado_publico(sys.modules[__name__], dados, ativo)


def montar_estado(evidencias=None):
    return estado_publico(None)
