"""Demonstração "Suporte remoto" (teste de carga de 18/11/2026). Fica fora da trilha e não concede XP.

Topologia de cada aluno: um roteador liga dois prédios. Prédio A (192.168.10.0/24): Financeiro, Vendas e a
impressora. Prédio B (192.168.20.0/24): Financeiro, Vendas e a T.I. (O RH saiu depois do ensaio com 20 alunos
simultâneos, para cada ambiente ter 7 contêineres em vez de 9.)

O aluno trabalha só no PC da T.I.:
  1. entra por SSH de verdade no Financeiro B com usuário e senha (mesmo prédio, funciona sem gateway);
  2. descobre que o gateway do Financeiro B está errado e corrige pela própria sessão SSH;
  3. imprime uma folha pela página web da impressora do Prédio A (curl), atravessando o roteador.
Cada folha impressa aparece no mural do painel do professor.
"""
import ipaddress
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'suporte-remoto'
TITULO = 'Suporte remoto'
DESCRICAO = 'Da T.I., entre por SSH no Financeiro, corrija o gateway e imprima uma folha no outro prédio.'
XP = 0
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.10.0/24 · 192.168.20.0/24'

GW = {'a': '192.168.10.1', 'b': '192.168.20.1'}
GATEWAY_ERRADO = '192.168.20.254'  # o defeito do Financeiro B: aponta para um roteador que não existe
IMPRESSORA = '192.168.10.50'
PORTA_IMPRESSORA = 80   # página web da impressora (estado e /imprimir)
USUARIO_SSH = 'suporte'
SENHA_SSH = 'suporte123'  # senha da demonstração, dada no Agora faça; conferida pelo servidor
ORIGEM = 'ti'          # o único terminal do aluno
ALVO = 'fin_b'         # o computador atendido por SSH

SETORES = {
    'a': {'nome': 'Prédio A', 'rede': '192.168.10.0', 'prefixo': 24, 'gateway': GW['a'], 'interface': 'eth0'},
    'b': {'nome': 'Prédio B', 'rede': '192.168.20.0', 'prefixo': 24, 'gateway': GW['b'], 'interface': 'eth1'},
}
SETORES_MODELO = ('a', 'b')

# chave: no (id no CORE), nome, host, tipo, setor, endereço
_PCS = {
    'fin_a': (1, 'Financeiro A', 'financeiro-a', 'pc', 'a', '192.168.10.11'),
    'vendas_a': (3, 'Vendas A', 'vendas-a', 'pc', 'a', '192.168.10.13'),
    'impressora': (4, 'Impressora', 'impressora', 'impressora', 'a', IMPRESSORA),
    'fin_b': (6, 'Financeiro B', 'financeiro-b', 'pc', 'b', '192.168.20.21'),
    'vendas_b': (8, 'Vendas B', 'vendas-b', 'pc', 'b', '192.168.20.23'),
    'ti': (9, 'T.I.', 'ti', 'pc', 'b', '192.168.20.30'),
}
NOS = {chave: {'no': no, 'nome': nome, 'host': host, 'tipo': tipo, 'setor': setor, 'interfaces': ['eth0'], 'ip': ip}
       for chave, (no, nome, host, tipo, setor, ip) in _PCS.items()}
NOS['roteador'] = {'no': 5, 'nome': 'Roteador', 'host': 'roteador', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1']}
SWITCHES = {10: ('switch-a', 'a'), 11: ('switch-b', 'b')}
PCS = tuple(k for k, v in NOS.items() if v['tipo'] == 'pc')
TERMINAIS = (ORIGEM,)


def _no(endereco, rota):
    return {'interfaces': {'eth0': [f'{endereco}/24']}, 'rota_padrao': rota, 'rotas': []}


INICIAL = {chave: _no(n['ip'], GW[n['setor']]) for chave, n in NOS.items() if 'ip' in n}
INICIAL[ALVO] = _no(NOS[ALVO]['ip'], GATEWAY_ERRADO)
INICIAL['roteador'] = {'interfaces': {'eth0': [f"{GW['a']}/24"], 'eth1': [f"{GW['b']}/24"]}, 'rota_padrao': None, 'rotas': []}
PLANO = []

ETAPAS = (
    {'id': 'acesso', 'titulo': 'Acesso por SSH', 'orientacao': 'Da T.I., entre no Financeiro B por SSH.'},
    {'id': 'gateway', 'titulo': 'Corrigir o gateway', 'orientacao': 'No Financeiro B, leia as rotas e corrija o gateway.'},
    {'id': 'impressao', 'titulo': 'Imprimir', 'orientacao': 'Do Financeiro B, imprima uma folha na impressora do Prédio A.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê o Financeiro B e repete os testes.'},
)
ALTERAVEIS = {'gateway': {ALVO: ('eth0',)}}


def dados_iniciais(sortear=None):
    dados = base.dados_iniciais(sys.modules[__name__], sortear)
    dados.update(remoto=None, acessos=[], folhas=[], senha_pendente=None)
    return dados


def etapa_ok(s, etapa):
    if etapa == 'acesso':
        return ALVO in s.get('acessos', [])
    if etapa == 'gateway':
        return s['estados'][ALVO]['rota_padrao'] == GW['b']
    if etapa == 'impressao':
        return any(f['origem'] == ALVO for f in s.get('folhas', []))
    return False


def no_do_ip(ip):
    return next((chave for chave, n in NOS.items() if n.get('ip') == ip), None)


def problemas(s):
    e = s['estados'][ALVO]
    return [] if e['rota_padrao'] == GW['b'] and e['interfaces'] == INICIAL[ALVO]['interfaces'] else [NOS[ALVO]['nome']]


def testes_finais(s):
    """A T.I. alcança o Financeiro B e o Financeiro B alcança a impressora do outro prédio."""
    return [(ORIGEM, NOS[ALVO]['ip']), (ALVO, IMPRESSORA)]


def estado_publico(dados, ativo=False):
    publico = base.estado_publico(sys.modules[__name__], dados, ativo)
    s = dados or {}
    publico['remoto'] = s.get('remoto') if ativo else None
    publico['folhas'] = list(s.get('folhas', [])) if ativo else []
    pendente = s.get('senha_pendente') if ativo else None
    publico['senha_pendente'] = {'usuario': pendente['usuario'], 'ip': NOS[pendente['destino']]['ip']} if pendente else None
    publico['impressora'] = {'ip': IMPRESSORA, 'porta': PORTA_IMPRESSORA}
    return publico


def montar_estado(evidencias=None):
    return estado_publico(None)


def endereco(chave):
    return str(ipaddress.IPv4Address(NOS[chave]['ip']))
