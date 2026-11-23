"""Lab10 — Desafio final: a rede da empresa. Dois setores em VLANs de um switch real, um roteador com uma interface em
cada VLAN (e servidor DHCP e DNS das duas) e o servidor da intranet numa terceira rede. Quatro chamados com pouca ajuda
reúnem o método do Lab 4, as rotas do Módulo 2, as VLANs do Lab 9 e o DHCP/DNS do Lab 8 (roteiro: doc 62)."""
import ipaddress
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'desafio-rede-da-empresa'
TITULO = 'Desafio final: a rede da empresa'
DESCRICAO = 'Quatro chamados numa empresa com VLANs, roteador, DHCP e DNS: investigue, corrija e comprove.'
XP = 150
TEMPO_LIMITE = 1500
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.0.0/16'
DOMINIO = 'empresa.local'
INTRANET = f'intranet.{DOMINIO}'
IP_INTRANET = '192.168.60.20'
GW = {'vendas': '192.168.10.1', 'financeiro': '192.168.20.1', 'servidores': '192.168.60.1'}
VLAN_VENDAS, VLAN_FINANCEIRO = 10, 20
ROTA_ERRADA = '192.168.60.254'
DNS_ERRADO = '192.168.20.9'
# PC V1 tem endereço reservado no DHCP (pelo MAC), para o estado inicial ser sempre o mesmo.
MACS = {'v1': '02:16:3e:10:00:11', 'v2': '02:16:3e:10:00:12', 'f1': '02:16:3e:20:00:21', 'f2': '02:16:3e:20:00:22'}
RESERVA_V1 = '192.168.10.11'
PORTAS = {'v1': 'eth0', 'v2': 'eth1', 'f1': 'eth2', 'f2': 'eth3'}
FAIXA = (100, 150)  # último byte das concessões em cada rede

SETORES = {
    'vendas': {'nome': 'Vendas · VLAN 10', 'rede': '192.168.10.0', 'prefixo': 24, 'gateway': GW['vendas'], 'interface': 'eth0'},
    'financeiro': {'nome': 'Financeiro · VLAN 20', 'rede': '192.168.20.0', 'prefixo': 24, 'gateway': GW['financeiro'], 'interface': 'eth1'},
}
SETORES_MODELO = ('vendas', 'financeiro')
NOS = {
    'v1': {'no': 1, 'nome': 'PC V1', 'host': 'pc-v1', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'v2': {'no': 2, 'nome': 'PC V2', 'host': 'pc-v2', 'tipo': 'pc', 'setor': 'vendas', 'interfaces': ['eth0']},
    'switch': {'no': 3, 'nome': 'Switch', 'host': 'switch', 'tipo': 'switch', 'interfaces': ['eth0', 'eth1', 'eth2', 'eth3', 'eth4', 'eth5']},
    'roteador': {'no': 4, 'nome': 'Roteador', 'host': 'roteador', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1', 'eth2']},
    'intranet': {'no': 8, 'nome': 'Servidor intranet', 'host': 'intranet', 'tipo': 'servidor', 'interfaces': ['eth0'], 'rotas': True},
    'f1': {'no': 6, 'nome': 'PC F1', 'host': 'pc-f1', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
    'f2': {'no': 7, 'nome': 'PC F2', 'host': 'pc-f2', 'tipo': 'pc', 'setor': 'financeiro', 'interfaces': ['eth0']},
}
PCS = ('v1', 'v2', 'f1', 'f2')
LER_DNS = PCS


def acesso(vlan):
    return {'pvid': vlan, 'membro': [vlan], 'untagged': [vlan]}


def _no(endereco, rota, dns=()):
    return {'interfaces': {'eth0': [endereco] if endereco else []}, 'rota_padrao': rota, 'rotas': [], 'dns': list(dns)}


# Quatro problemas ao mesmo tempo: a rota padrão do servidor da intranet aponta para um roteador que não existe; a
# porta do PC V2 foi para a VLAN do Financeiro; o PC F1 acabou de chegar; o PC F2 foi configurado à mão com o DNS errado.
VLANS_INICIAIS = {'eth0': acesso(VLAN_VENDAS), 'eth1': acesso(VLAN_FINANCEIRO), 'eth2': acesso(VLAN_FINANCEIRO),
                  'eth3': acesso(VLAN_FINANCEIRO), 'eth4': acesso(VLAN_VENDAS), 'eth5': acesso(VLAN_FINANCEIRO)}
VLANS_FINAIS = {**VLANS_INICIAIS, 'eth1': acesso(VLAN_VENDAS)}
INICIAL = {
    'v1': _no(f'{RESERVA_V1}/24', GW['vendas'], [GW['vendas']]),
    'v2': _no('192.168.10.12/24', GW['vendas'], [GW['vendas']]),
    'f1': _no(None, None),
    'f2': _no('192.168.20.22/24', GW['financeiro'], [DNS_ERRADO]),
    'switch': {'interfaces': {p: [] for p in NOS['switch']['interfaces']}, 'rota_padrao': None, 'rotas': [], 'vlans': VLANS_INICIAIS},
    'roteador': {'interfaces': {'eth0': [f"{GW['vendas']}/24"], 'eth1': [f"{GW['financeiro']}/24"], 'eth2': [f"{GW['servidores']}/24"]},
                 'rota_padrao': None, 'rotas': []},
    'intranet': _no(f'{IP_INTRANET}/24', ROTA_ERRADA),
}
PLANO = []

CHAMADOS = {
    'intranet': {
        # Quem abre o chamado é o PC V1; a causa está no servidor, e o aluno precisa ter lido as rotas dele.
        'no': 'v1', 'observar_no': 'intranet', 'titulo': 'Chamado 1 · Intranet', 'sintoma': 'Ninguém consegue abrir a intranet.',
        'objetivo': f'Os PCs voltam a alcançar o servidor intranet ({INTRANET}).',
        'observar': 'ver-rotas', 'pedido_observar': 'Antes de responder, investigue pelo terminal: teste a intranet por partes '
                                                    'e leia as tabelas de rotas dos equipamentos no caminho.',
        'causas': {
            'rota': 'A rota padrão do servidor intranet está errada: as respostas não têm caminho de volta.',
            'dns': 'O DNS não traduz o nome da intranet.',
            'vlan': 'A porta do roteador no switch está na VLAN errada.'},
        'correta': 'rota',
        'acerto': f'Isso: o pedido chega ao servidor, mas a resposta segue a rota padrão para {ROTA_ERRADA}, que não existe. '
                  'É a volta do Módulo 2.',
        'erro': 'Compare o que funciona e o que não: o nome é traduzido? O roteador responde? E o servidor, por onde ele '
                'devolve as respostas?',
        'resolucao': f'A rota padrão do servidor intranet passou a apontar para o roteador ({GW["servidores"]}).',
    },
    'vlan': {
        'no': 'v2', 'observar_no': 'switch', 'titulo': 'Chamado 2 · PC V2', 'sintoma': 'O PC V2 não fala com ninguém.',
        'objetivo': 'O PC V2 volta a falar com o gateway do Vendas e abre a intranet pelo nome.',
        'observar': 'ver-vlans', 'pedido_observar': 'Antes de responder, veja as VLANs das portas no switch.',
        'causas': {
            'vlan': 'A porta do PC V2 no switch está na VLAN de outro setor.',
            'endereco': 'O PC V2 está com um endereço de outra rede.',
            'gateway': 'O gateway do Vendas está desligado.'},
        'correta': 'vlan',
        'acerto': 'Isso: a porta do PC V2 está na VLAN do Financeiro, enquanto o endereço e o gateway dele são do Vendas.',
        'erro': 'Compare o endereço do PC V2 com o do PC V1 e a VLAN da porta de cada um no switch.',
        'resolucao': 'A porta do PC V2 voltou para a VLAN do Vendas.',
    },
    'dhcp': {
        'no': 'f1', 'titulo': 'Chamado 3 · PC F1', 'sintoma': 'O PC F1 acabou de chegar e não acessa nada.',
        'objetivo': 'O PC F1 recebe endereço, gateway e DNS do Financeiro e abre a intranet pelo nome.',
        'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, veja os endereços do PC F1.',
        'causas': {
            'sem-endereco': 'O PC F1 ainda não recebeu um endereço do servidor DHCP.',
            'vlan': 'A porta do PC F1 está na VLAN errada.',
            'cabo': 'O cabo do PC F1 está desconectado.'},
        'correta': 'sem-endereco',
        'acerto': 'Isso: a interface está ligada e sem endereço IPv4. O roteador também é o servidor DHCP de cada VLAN.',
        'erro': 'Releia os endereços do PC F1: a interface está UP? Tem alguma linha inet?',
        'resolucao': 'O PC F1 recebeu a concessão do DHCP do Financeiro.',
    },
    'dns': {
        'no': 'f2', 'titulo': 'Chamado 4 · PC F2', 'sintoma': 'O PC F2 abre a intranet pelo IP, mas não pelo nome.',
        'objetivo': 'O PC F2 usa o servidor DNS da empresa e abre a intranet pelo nome.',
        'observar': 'ver-dns', 'pedido_observar': 'Antes de responder, veja qual servidor DNS o PC F2 usa.',
        'causas': {
            'dns-errado': 'O PC F2 está configurado com um servidor DNS que não é o da empresa.',
            'nome': 'O nome da intranet não existe no DNS.',
            'rota': 'O PC F2 não tem rota para a intranet.'},
        'correta': 'dns-errado',
        'acerto': f'Isso: pelo IP funciona, e o nameserver {DNS_ERRADO} não é o servidor DNS da empresa. A configuração foi '
                  'feita à mão.',
        'erro': 'Pelo IP funciona: então rede e rotas estão certas. O que falta para o nome virar endereço?',
        'resolucao': 'O PC F2 passou para o DHCP e consulta o servidor DNS da empresa.',
    },
}
ETAPAS = (
    {'id': 'intranet', 'titulo': 'Chamado 1 · Intranet', 'orientacao': CHAMADOS['intranet']['sintoma']},
    {'id': 'vlan', 'titulo': 'Chamado 2 · PC V2', 'orientacao': CHAMADOS['vlan']['sintoma']},
    {'id': 'dhcp', 'titulo': 'Chamado 3 · PC F1', 'orientacao': CHAMADOS['dhcp']['sintoma']},
    {'id': 'dns', 'titulo': 'Chamado 4 · PC F2', 'orientacao': CHAMADOS['dns']['sintoma']},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê a rede inteira e repete os testes pelos nomes.'},
)
ALTERAVEIS = {'intranet': {'intranet': ('eth0',)}, 'vlan': {'switch': ('eth1',)}, 'dhcp': {'f1': ('eth0',)},
              'dns': {'f2': ('eth0',)}}


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def pc_ok(estado, setor):
    """Endereço do bloco do setor (fixo ou do DHCP), gateway do setor e o roteador como servidor DNS."""
    enderecos = estado['interfaces'].get('eth0', [])
    if len(enderecos) != 1:
        return False
    interface = ipaddress.IPv4Interface(enderecos[0])
    return (str(interface.network) == f"{SETORES[setor]['rede']}/24" and interface.ip.packed[-1] not in (0, 1, 255)
            and estado['rota_padrao'] == GW[setor] and estado.get('dns') == [GW[setor]])


def concessao_ok(estado, setor):
    enderecos = estado['interfaces'].get('eth0', [])
    return pc_ok(estado, setor) and FAIXA[0] <= ipaddress.IPv4Interface(enderecos[0]).ip.packed[-1] <= FAIXA[1]


def _vlans(s):
    return s['estados']['switch'].get('vlans', {})


def progresso_chamado(s, etapa):
    e, testes = s['estados'], s['testes']
    configuracao = {
        'intranet': e['intranet']['rota_padrao'] == GW['servidores'],
        'vlan': _vlans(s).get('eth1') == acesso(VLAN_VENDAS),
        'dhcp': concessao_ok(e['f1'], 'financeiro'),
        'dns': concessao_ok(e['f2'], 'financeiro'),
    }[etapa]
    pc = CHAMADOS[etapa]['no']
    return {'causa': s['diagnosticos'][etapa]['correta'], 'configuracao': configuracao, 'teste': testes[pc].get(INTRANET) is True}


def etapa_ok(s, etapa):
    return etapa in CHAMADOS and all(progresso_chamado(s, etapa).values())


def invalidar_testes(s, no, anterior, novo):
    """Mudar a porta de um PC afeta os testes dele; mudar o servidor intranet afeta todos os testes que passam por ele."""
    if NOS[no]['tipo'] == 'switch':
        portas = {p for p, v in novo['vlans'].items() if anterior.get('vlans', {}).get(p) != v}
        for pc, porta in PORTAS.items():
            if porta in portas:
                s['testes'][pc] = {}
        return
    if no == 'intranet':
        for origem in s['testes']:
            s['testes'][origem] = {}
        return
    s['testes'][no] = {}


def _endereco(s, pc):
    enderecos = s['estados'][pc]['interfaces'].get('eth0', [])
    return str(ipaddress.IPv4Interface(enderecos[0]).ip) if len(enderecos) == 1 else None


def problemas(s):
    e = s['estados']
    erros = [NOS[pc]['nome'] for pc in PCS if not pc_ok(e[pc], NOS[pc]['setor'])]
    if _vlans(s) != VLANS_FINAIS:
        erros.append('Switch')
    if e['intranet']['interfaces'] != INICIAL['intranet']['interfaces'] or e['intranet']['rota_padrao'] != GW['servidores']:
        erros.append(NOS['intranet']['nome'])
    if e['roteador']['interfaces'] != INICIAL['roteador']['interfaces']:
        erros.append(NOS['roteador']['nome'])
    return erros


def testes_finais(s):
    """Cada PC abre a intranet pelo nome; entre setores, o roteador encaminha (redes diferentes, VLANs diferentes)."""
    return [(pc, INTRANET) for pc in PCS] + [('v1', _endereco(s, 'f1'))]


def estado_publico(dados, ativo=False):
    publico = base.estado_publico(sys.modules[__name__], dados, ativo)
    publico['portas'] = {porta: NOS[pc]['nome'] for pc, porta in PORTAS.items()}
    publico['portas'].update({'eth4': 'Roteador eth0', 'eth5': 'Roteador eth1'})
    publico['servicos'] = {'dominio': DOMINIO, 'dns': 'o gateway de cada setor', 'nomes': {INTRANET: IP_INTRANET}}
    return publico


def montar_estado(evidencias=None):
    return estado_publico(None)
