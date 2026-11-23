"""Lab9 — Investigando e separando a LAN: tabela ARP dos PCs, tabela MAC do switch e VLANs por porta. Um switch real
(bridge Linux com filtro de VLAN) liga quatro PCs da mesma rede IP; o aluno investiga, atende um chamado de porta na
VLAN errada e separa o Financeiro, comprovando que VLANs diferentes não se falam (roteiro: doc 61)."""
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'investigando-a-lan'
TITULO = 'Investigando e separando a LAN'
DESCRICAO = 'Leia a tabela ARP e a tabela MAC do switch, corrija uma porta na VLAN errada e separe o Financeiro.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.30.0/24'

# MACs fixos (definidos na criação da topologia), para o servidor conferir a investigação.
MACS = {'v1': '02:16:3e:5a:01:0b', 'v2': '02:16:3e:5a:01:2c', 'f1': '02:16:3e:7d:02:4e', 'f2': '02:16:3e:7d:02:9f'}
PORTAS = {'v1': 'eth0', 'v2': 'eth1', 'f1': 'eth2', 'f2': 'eth3'}
IPS = {'v1': '192.168.30.11', 'v2': '192.168.30.12', 'f1': '192.168.30.21', 'f2': '192.168.30.22'}
VLAN_VENDAS, VLAN_FINANCEIRO = 10, 20

SETORES = {
    'vendas': {'nome': 'Vendas · VLAN 10', 'rede': '192.168.30.0', 'prefixo': 24, 'gateway': None, 'interface': 'eth0'},
    'financeiro': {'nome': 'Financeiro · VLAN 20', 'rede': '192.168.30.0', 'prefixo': 24, 'gateway': None, 'interface': 'eth0'},
}
SETORES_MODELO = ('vendas', 'financeiro')  # nada a planejar no endereçamento: a rede IP é uma só
NOS = {
    'v1': {'no': 1, 'nome': 'PC V1', 'host': 'pc-v1', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'v2': {'no': 2, 'nome': 'PC V2', 'host': 'pc-v2', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'switch': {'no': 5, 'nome': 'Switch', 'host': 'switch', 'tipo': 'switch', 'interfaces': ['eth0', 'eth1', 'eth2', 'eth3']},
    'f1': {'no': 6, 'nome': 'PC F1', 'host': 'pc-f1', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
    'f2': {'no': 7, 'nome': 'PC F2', 'host': 'pc-f2', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
}


def acesso(vlan):
    """Porta de acesso: membro de uma só VLAN, que é também a PVID e sai sem marcação."""
    return {'pvid': vlan, 'membro': [vlan], 'untagged': [vlan]}


def _pc(chave):
    return {'interfaces': {'eth0': [f'{IPS[chave]}/24']}, 'rota_padrao': None, 'rotas': []}


# Um técnico começou a separar os setores: o PC V1 já está na VLAN 10, mas a porta do PC V2 foi para a 20 por engano
# e o Financeiro continua na VLAN 1, a padrão.
INICIAL = {
    'v1': _pc('v1'), 'v2': _pc('v2'), 'f1': _pc('f1'), 'f2': _pc('f2'),
    'switch': {'interfaces': {p: [] for p in ('eth0', 'eth1', 'eth2', 'eth3')}, 'rota_padrao': None, 'rotas': [],
               'vlans': {'eth0': acesso(VLAN_VENDAS), 'eth1': acesso(VLAN_FINANCEIRO), 'eth2': acesso(1), 'eth3': acesso(1)}},
}
FINAL = {'eth0': acesso(VLAN_VENDAS), 'eth1': acesso(VLAN_VENDAS), 'eth2': acesso(VLAN_FINANCEIRO), 'eth3': acesso(VLAN_FINANCEIRO)}

PLANO = [
    {'id': 'mac-f2', 'rotulo': 'MAC do PC F2', 'grupo': 'investigacao', 'tipo': 'mac', 'esperado': MACS['f2']},
    {'id': 'porta-f2', 'rotulo': 'Porta do switch', 'grupo': 'investigacao', 'tipo': 'porta', 'esperado': PORTAS['f2']},
]
# A investigação só é conferida depois de o aluno ler as duas tabelas no terminal.
OBSERVAR_PLANO = (
    ('f1', 'ver-vizinhos', 'Antes de conferir: no PC F1, faça ping ao PC F2 e leia a tabela ARP com ip neigh show.'),
    ('switch', 'ver-fdb', 'Antes de conferir: no switch, leia a tabela MAC com bridge fdb show.'),
)
CHAMADO = {
    'no': 'v2', 'observar_no': 'switch', 'titulo': 'Chamado · Vendas', 'sintoma': 'O PC V2 não fala com o PC V1, que está na mesa ao lado.',
    'observar': 'ver-vlans', 'pedido_observar': 'Antes de responder, veja as VLANs das portas no switch com bridge vlan show.',
    'causas': {
        'vlan-errada': 'A porta do PC V2 no switch está numa VLAN diferente da do PC V1.',
        'ip': 'O PC V2 está com um endereço de outra rede IP.',
        'cabo': 'A porta do PC V2 no switch está desligada.'},
    'correta': 'vlan-errada',
    'acerto': 'Isso mesmo: a eth1 (PC V2) está na VLAN 20 e a eth0 (PC V1) na 10. VLANs diferentes não trocam quadros, '
              'mesmo com os dois na mesma rede IP.',
    'erro': 'Releia: os dois PCs estão em 192.168.30.0/24? A porta eth1 aparece em bridge vlan show? Em qual VLAN está cada porta?',
}
ETAPAS = (
    {'id': 'investigar', 'titulo': 'Investigação', 'orientacao': 'Tabela ARP do PC F1 e tabela MAC do switch: onde está o PC F2?'},
    {'id': 'chamado', 'titulo': 'Chamado', 'orientacao': CHAMADO['sintoma']},
    {'id': 'separar', 'titulo': 'Separar o Financeiro', 'orientacao': 'Portas do PC F1 e do PC F2 na VLAN 20, e o teste do isolamento.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê o switch e repete os testes: quem deve falar e quem não deve.'},
)
ALTERAVEIS = {'chamado': {'switch': ('eth1',)}, 'separar': {'switch': ('eth2', 'eth3')}}


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def _vlans(s):
    return s['estados']['switch'].get('vlans', {})


def etapa_ok(s, etapa):
    vlans, testes = _vlans(s), s['testes']
    if etapa == 'investigar':
        return s['plano']['correto']
    if etapa == 'chamado':
        return (s['diagnosticos']['chamado']['correta'] and vlans.get('eth1') == acesso(VLAN_VENDAS)
                and testes['v2'].get(IPS['v1']) is True)
    if etapa == 'separar':
        return (all(vlans.get(p) == acesso(VLAN_FINANCEIRO) for p in ('eth2', 'eth3'))
                and testes['f1'].get(IPS['f2']) is True and testes['f1'].get(IPS['v1']) is False)
    return False


def invalidar_testes(s, no, anterior, novo):
    """Mudar uma porta do switch só afeta os testes que envolvem o PC daquela porta (como origem ou destino)."""
    if NOS[no]['tipo'] != 'switch':
        s['testes'][no] = {}
        return
    portas = {p for p, v in novo['vlans'].items() if anterior.get('vlans', {}).get(p) != v}
    afetados = {pc for pc, porta in PORTAS.items() if porta in portas}
    for origem, testes in s['testes'].items():
        s['testes'][origem] = {} if origem in afetados else {
            ip: ok for ip, ok in testes.items() if ip not in {IPS[pc] for pc in afetados}}


def problemas(s):
    erros = [] if _vlans(s) == FINAL else ['Switch']
    return erros + [NOS[pc]['nome'] for pc in MACS if s['estados'][pc]['interfaces'] != INICIAL[pc]['interfaces']]


def testes_finais(s):
    return [('v2', IPS['v1']), ('f1', IPS['f2'])]


def testes_isolados(s):
    """Pares que precisam falhar: VLANs diferentes não se falam sem um roteador."""
    return [('f1', IPS['v1']), ('v1', IPS['f2'])]


def estado_publico(dados, ativo=False):
    publico = base.estado_publico(sys.modules[__name__], dados, ativo)
    # Qual PC está em cada porta é a resposta da investigação: só sai do servidor depois de conferida.
    conferida = publico['plano']['correto']
    publico['portas'] = {porta: NOS[pc]['nome'] for pc, porta in PORTAS.items()} if conferida else {}
    if not conferida:
        for no in publico['nos']:
            no.pop('mac', None)
    return publico


def montar_estado(evidencias=None):
    return estado_publico(None)
