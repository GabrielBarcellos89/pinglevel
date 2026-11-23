"""Lab8 — Endereços e nomes automáticos: mesa de suporte numa rede com DHCP e DNS (dnsmasq no servidor .2). Três
chamados, um por PC, com a ajuda diminuindo; a conclusão relê endereço, gateway e servidor DNS dos três e repete os
pings pelos nomes (roteiro: doc 59)."""
import ipaddress
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'enderecos-e-nomes'
TITULO = 'Endereços e nomes automáticos'
DESCRICAO = 'Atenda três chamados numa rede com DHCP e DNS: endereço automático, servidor DNS errado e nome digitado errado.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.40.0/24'
DOMINIO = 'empresa.local'
GATEWAY, SERVIDOR = '192.168.40.1', '192.168.40.2'
FAIXA = (ipaddress.IPv4Address('192.168.40.100'), ipaddress.IPv4Address('192.168.40.150'))
INTRANET, IMPRESSORA = f'intranet.{DOMINIO}', f'impressora.{DOMINIO}'
NOMES = {INTRANET: '192.168.40.20', IMPRESSORA: '192.168.40.30'}
# O PC Financeiro tem endereço reservado no DHCP (pelo MAC), para o estado inicial ser sempre o mesmo.
MAC_FINANCEIRO, RESERVA_FINANCEIRO = '02:16:3e:40:00:33', '192.168.40.120'
DNS_ERRADO = '192.168.40.9'

SETORES = {
    'atendimento': {'nome': 'Atendimento', 'rede': '192.168.40.0', 'prefixo': 24, 'gateway': GATEWAY, 'interface': 'eth0'},
    'servidores': {'nome': 'Servidores', 'rede': '192.168.40.0', 'prefixo': 24, 'gateway': GATEWAY, 'interface': 'eth0'},
}
SETORES_MODELO = ('atendimento', 'servidores')  # nada a planejar: a rede é dada
NOS = {
    'novo': {'no': 1, 'nome': 'PC Novo', 'host': 'pc-novo', 'tipo': 'pc', 'setor': 'atendimento', 'interfaces': ['eth0']},
    'recepcao': {'no': 2, 'nome': 'PC Recepção', 'host': 'pc-recepcao', 'tipo': 'pc', 'setor': 'atendimento', 'interfaces': ['eth0']},
    'financeiro': {'no': 3, 'nome': 'PC Financeiro', 'host': 'pc-financeiro', 'tipo': 'pc', 'setor': 'atendimento', 'interfaces': ['eth0']},
    'roteador': {'no': 5, 'nome': 'Roteador', 'host': 'roteador', 'tipo': 'roteador', 'interfaces': ['eth0']},
    'servidor': {'no': 6, 'nome': 'Servidor DHCP e DNS', 'host': 'servidor', 'tipo': 'servidor', 'setor': 'servidores', 'interfaces': ['eth0']},
    'intranet': {'no': 7, 'nome': 'Intranet', 'host': 'intranet', 'tipo': 'servidor', 'setor': 'servidores', 'interfaces': ['eth0']},
    'impressora': {'no': 8, 'nome': 'Impressora', 'host': 'impressora', 'tipo': 'servidor', 'setor': 'servidores', 'interfaces': ['eth0']},
}
PCS = ('novo', 'recepcao', 'financeiro')
LER_DNS = PCS


def _fixo(endereco, rota=GATEWAY, dns=()):
    return {'interfaces': {'eth0': [endereco] if endereco else []}, 'rota_padrao': rota, 'rotas': [], 'dns': list(dns)}


# PC Novo acabou de chegar (sem endereço nem DNS); no PC Recepção alguém configurou tudo à mão, com o servidor DNS
# errado; o PC Financeiro está certo (concessão do DHCP) e o problema é o nome que o usuário digita.
INICIAL = {
    'novo': _fixo(None, rota=None),
    'recepcao': _fixo('192.168.40.60/24', dns=[DNS_ERRADO]),
    'financeiro': _fixo(f'{RESERVA_FINANCEIRO}/24', dns=[SERVIDOR]),
    'roteador': _fixo(f'{GATEWAY}/24', rota=None),
    'servidor': _fixo(f'{SERVIDOR}/24'),
    'intranet': _fixo(f'{NOMES[INTRANET]}/24'),
    'impressora': _fixo(f'{NOMES[IMPRESSORA]}/24'),
}
PLANO = []

CHAMADOS = {
    'novo': {
        'no': 'novo', 'titulo': 'Chamado 1 · PC Novo', 'sintoma': 'Acabou de chegar e não acessa nada.',
        'objetivo': f'O PC Novo recebe endereço, gateway e servidor DNS automaticamente e abre a intranet pelo nome ({INTRANET}).',
        'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, veja os endereços do PC Novo com ip addr show.',
        'causas': {
            'sem-endereco': 'A interface está ligada, mas o PC ainda não recebeu um endereço do servidor DHCP.',
            'cabo': 'O cabo do PC Novo está desconectado: a interface está desligada.',
            'servidor': 'O servidor DHCP da rede está desligado.'},
        'correta': 'sem-endereco',
        'acerto': 'Isso: a eth0 está UP, mas não tem nenhuma linha inet. Peça um endereço ao servidor DHCP e confira o que '
                  'veio na concessão.',
        'erro': 'Releia o ip addr show: a eth0 aparece como UP? Há alguma linha inet com um endereço IPv4?',
        'resolucao': 'O PC Novo pediu um endereço por DHCP e recebeu endereço, gateway e servidor DNS.',
    },
    'recepcao': {
        'no': 'recepcao', 'titulo': 'Chamado 2 · PC Recepção', 'sintoma': 'A intranet não abre pelo nome; pelo endereço IP abre.',
        'objetivo': f'O PC Recepção usa o servidor DNS da empresa e abre a intranet pelo nome ({INTRANET}).',
        'observar': 'ver-dns', 'pedido_observar': 'Antes de responder, compare o ping pelo IP com a consulta do nome e veja '
                                                  'qual servidor DNS o PC usa com cat /etc/resolv.conf.',
        'causas': {
            'dns-errado': 'O PC Recepção está configurado com um servidor DNS que não é o da empresa.',
            'nome': f'O nome {INTRANET} não existe no DNS.',
            'rede': 'O PC Recepção não alcança a rede.'},
        'correta': 'dns-errado',
        'acerto': f'Isso: pelo IP a intranet responde, então a rede funciona; o nameserver {DNS_ERRADO} não é o servidor DNS '
                  'da empresa. A configuração foi feita à mão: passe o PC para o DHCP, que entrega o DNS certo.',
        'erro': 'Compare: o ping pelo IP responde? E o nslookup, que servidor ele tenta consultar? Esse servidor existe?',
        'resolucao': 'O PC Recepção passou para o DHCP e agora consulta o servidor DNS da empresa.',
    },
    'financeiro': {
        'no': 'financeiro', 'titulo': 'Chamado 3 · PC Financeiro',
        'sintoma': f'A impressora não é encontrada. O usuário digitou: impresora.{DOMINIO}',
        'objetivo': f'Descobrir por que o nome não é encontrado e mostrar que a impressora responde pelo nome certo ({IMPRESSORA}).',
        'observar': 'consultar-dns', 'pedido_observar': f'Antes de responder, faça a consulta do usuário: nslookup impresora.{DOMINIO}.',
        'causas': {
            'nome': 'O nome digitado não existe no DNS: está escrito errado.',
            'dns': 'O PC Financeiro está com o servidor DNS errado.',
            'impressora': 'A impressora está desligada.'},
        'correta': 'nome',
        'acerto': 'Isso: NXDOMAIN quer dizer que o servidor DNS respondeu, e que esse nome não existe. Falta um "s". Não há '
                  'nada a corrigir no PC: comprove com ping pelo nome certo.',
        'erro': 'Releia a resposta do nslookup: o servidor DNS respondeu? O que significa NXDOMAIN?',
        'ja_identificada': f'A causa já foi identificada. Comprove com ping {IMPRESSORA}.',
        'resolucao': f'O nome certo é {IMPRESSORA}: o DNS e o PC estavam certos.',
    },
}
ETAPAS = (
    {'id': 'novo', 'titulo': 'Chamado 1 · PC Novo', 'orientacao': CHAMADOS['novo']['sintoma']},
    {'id': 'recepcao', 'titulo': 'Chamado 2 · PC Recepção', 'orientacao': CHAMADOS['recepcao']['sintoma']},
    {'id': 'financeiro', 'titulo': 'Chamado 3 · PC Financeiro', 'orientacao': 'A impressora não é encontrada.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os três PCs e repete os pings pelos nomes.'},
)
ALTERAVEIS = {'novo': {'novo': ('eth0',)}, 'recepcao': {'recepcao': ('eth0',)}}


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def concessao_ok(estado):
    """Configuração do DHCP: um endereço da faixa, gateway .1 e o servidor DNS da empresa."""
    enderecos = estado['interfaces'].get('eth0', [])
    if len(enderecos) != 1:
        return False
    interface = ipaddress.IPv4Interface(enderecos[0])
    return (str(interface.network) == REDE and FAIXA[0] <= interface.ip <= FAIXA[1]
            and estado['rota_padrao'] == GATEWAY and estado.get('dns') == [SERVIDOR])


def progresso_chamado(s, etapa):
    pc = CHAMADOS[etapa]['no']
    alvo = IMPRESSORA if etapa == 'financeiro' else INTRANET
    return {'causa': s['diagnosticos'][etapa]['correta'],
            'configuracao': etapa == 'financeiro' or concessao_ok(s['estados'][pc]),
            'teste': s['testes'][pc].get(alvo) is True}


def etapa_ok(s, etapa):
    if etapa not in CHAMADOS:
        return False
    return all(progresso_chamado(s, etapa).values())


def problemas(s):
    erros = [NOS[pc]['nome'] for pc in PCS if not concessao_ok(s['estados'][pc])]
    return erros + [NOS[n]['nome'] for n in NOS if n not in PCS and s['estados'][n]['interfaces'] != INICIAL[n]['interfaces']]


def testes_finais(s):
    return [(pc, INTRANET) for pc in PCS] + [('financeiro', IMPRESSORA)]


def estado_publico(dados, ativo=False):
    publico = base.estado_publico(sys.modules[__name__], dados, ativo)
    publico['servicos'] = {'dhcp': f'{FAIXA[0]} a {FAIXA[1]}', 'gateway': GATEWAY, 'dns': SERVIDOR, 'dominio': DOMINIO,
                           'nomes': dict(NOMES)}
    return publico


def montar_estado(evidencias=None):
    return estado_publico(None)
