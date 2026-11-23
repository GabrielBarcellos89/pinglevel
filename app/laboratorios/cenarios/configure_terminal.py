"""Lab4 (versão 2): chamados de suporte resolvidos pelo terminal, com ajuda que diminui a cada chamado."""
import ipaddress
import random
from copy import deepcopy

LABORATORIO_ID = 'configure-pelo-terminal'
TITULO = 'Configure pelo terminal'
DESCRICAO = 'Resolva três chamados de suporte investigando e corrigindo computadores pelo terminal.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE_LOCAL = ipaddress.IPv4Network('192.168.10.0/24')
GATEWAY = '192.168.10.1'
SERVIDOR = '192.168.20.10'
# Computadores atendidos: chave usada na API, nó do CORE e nome do host (aparece no prompt do terminal).
PCS = {
    'novo': {'no': 1, 'nome': 'PC Novo', 'host': 'pc-novo'},
    'financeiro': {'no': 2, 'nome': 'PC Financeiro', 'host': 'pc-financeiro'},
    'recepcao': {'no': 6, 'nome': 'PC Recepção', 'host': 'pc-recepcao'},
}
# Configuração com que cada PC é entregue; o início do laboratório confere o estado real contra ela.
INICIAL = {
    'novo': {'enderecos': [], 'rota_padrao': None},
    'financeiro': {'enderecos': ['192.168.10.12/24'], 'rota_padrao': '192.168.10.11'},
    'recepcao': {'enderecos': ['192.168.10.11/16'], 'rota_padrao': GATEWAY},
}
NOS = {
    1: {'id': 1, 'nome': 'PC Novo', 'tipo': 'computador', 'pc': 'novo'},
    2: {'id': 2, 'nome': 'PC Financeiro', 'tipo': 'computador', 'pc': 'financeiro'},
    6: {'id': 6, 'nome': 'PC Recepção', 'tipo': 'computador', 'pc': 'recepcao'},
    3: {'id': 3, 'nome': 'Switch', 'tipo': 'switch'},
    4: {'id': 4, 'nome': 'Servidor', 'tipo': 'servidor', 'ip': SERVIDOR, 'prefixo': 24},
    5: {'id': 5, 'nome': 'Roteador', 'tipo': 'roteador', 'interfaces': [
        {'interface': 'eth0', 'ip': GATEWAY, 'prefixo': 24},
        {'interface': 'eth1', 'ip': '192.168.20.1', 'prefixo': 24}]},
}
# Endereços fixos de outros equipamentos; os dos PCs entram conforme o estado lido de cada um.
FIXOS = ('192.168.10.1', '192.168.20.1', '192.168.20.10')

CHAMADOS = (
    {'id': 'chamado-1', 'pc': 'novo', 'titulo': 'Chamado 1 · PC Novo',
     'sintoma': 'Acabou de ser instalado e não acessa nada.',
     'ajuda': 'Comece por ip addr show e tente um ping para um colega. Para corrigir, use ip addr add e '
              'ip route add default via; depois teste o servidor.',
     'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, observe a interface do PC Novo com ip addr show.',
     'causas': {
         'sem-ipv4': 'A interface está ativa, mas não tem endereço IPv4.',
         'cabo': 'O cabo de rede está desconectado.',
         'servidor-desligado': 'O servidor está desligado.'},
     'correta': 'sem-ipv4',
     'objetivo': 'O PC Novo alcança o servidor (192.168.20.10).',
     'resolucao': 'O PC Novo ganhou endereço na rede do Atendimento e rota padrão pelo roteador.',
     'acerto': 'Isso mesmo: sem endereço IPv4 a interface não participa da rede IP. Configure endereço e rota padrão.',
     'erro': 'Compare com o que o terminal mostrou: a interface está ativa (UP)? Aparece alguma linha inet?'},
    {'id': 'chamado-2', 'pc': 'financeiro', 'titulo': 'Chamado 2 · PC Financeiro',
     'sintoma': 'Fala com os colegas, mas não alcança o servidor.',
     'ajuda': 'Compare a tabela de rotas deste PC com a do PC Novo, que já funciona.',
     'observar': 'ver-rotas', 'pedido_observar': 'Antes de responder, leia a tabela de rotas do PC Financeiro com ip route.',
     'causas': {
         'gateway-errado': 'A rota padrão aponta para um computador, não para o roteador.',
         'sem-rota': 'Não existe rota padrão.',
         'prefixo': 'O prefixo da interface está errado.'},
     'correta': 'gateway-errado',
     'objetivo': 'O PC Financeiro volta a alcançar o servidor (192.168.20.10).',
     'resolucao': 'A rota padrão do PC Financeiro passou a apontar para o roteador (192.168.10.1).',
     'acerto': 'Isso mesmo: a rota padrão leva ao 192.168.10.11, que é um computador e não encaminha pacotes.',
     'erro': 'Releia ip route e ip addr deste PC: existe uma linha default? Para onde ela aponta? O prefixo é /24?'},
    {'id': 'chamado-3', 'pc': 'recepcao', 'titulo': 'Chamado 3 · PC Recepção',
     'sintoma': 'Fala com os colegas, mas não alcança o servidor.',
     'ajuda': '',
     'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, observe a interface do PC Recepção com ip addr show.',
     'causas': {
         'prefixo': 'O prefixo é largo demais: o servidor parece estar na mesma rede.',
         'gateway-errado': 'A rota padrão aponta para um computador, não para o roteador.',
         'sem-ipv4': 'A interface não tem endereço IPv4.'},
     'correta': 'prefixo',
     'objetivo': 'O PC Recepção volta a alcançar o servidor (192.168.20.10).',
     'resolucao': 'O PC Recepção ficou com o prefixo /24: o servidor voltou a ser outra rede, alcançada pelo roteador.',
     'acerto': 'Isso mesmo: com /16, 192.168.20.10 parece local e o PC tenta entregá-lo direto, sem passar pelo roteador.',
     'erro': 'Confira de novo: a rota padrão aponta para o roteador? Que prefixo aparece na linha inet?'},
)
CHAMADO = {c['id']: c for c in CHAMADOS}
ETAPAS = (
    *({'id': c['id'], 'titulo': c['titulo'], 'orientacao': c['sintoma']} for c in CHAMADOS),
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os três PCs e repete os testes.'},
)


def dados_iniciais(sortear=random.sample):
    # A ordem das causas é sorteada por sessão para a resposta certa não ficar sempre na mesma posição.
    return {'revisao': 0,
        'diagnosticos': {c['id']: {'ordem': sortear(list(c['causas']), len(c['causas'])), 'resposta': None, 'correta': False}
                         for c in CHAMADOS},
        'terminal': [],
        'estados': {pc: {**deepcopy(INICIAL[pc]), 'lido': False} for pc in PCS},
        'testes': {pc: {} for pc in PCS},
        'conclusao_validada': False}


def em_uso(estados, pc):
    """Endereços que o PC não pode usar: equipamentos fixos e o endereço atual dos outros PCs."""
    usados = set(FIXOS)
    for outro, estado in estados.items():
        if outro != pc:
            usados.update(str(ipaddress.IPv4Interface(e).ip) for e in estado['enderecos'])
    return tuple(sorted(usados))


def configuracao_ok(estados, pc):
    """Um só endereço, host livre /24 da rede do Atendimento, e rota padrão pelo roteador."""
    estado = estados[pc]
    if len(estado['enderecos']) != 1 or estado['rota_padrao'] != GATEWAY:
        return False
    try:
        interface = ipaddress.IPv4Interface(estado['enderecos'][0])
    except ValueError:
        return False
    return (interface.network == REDE_LOCAL and str(interface.ip) not in em_uso(estados, pc)
            and interface.ip not in (REDE_LOCAL.network_address, REDE_LOCAL.broadcast_address))


def chamado_resolvido(s, chamado):
    pc = chamado['pc']
    return (s['diagnosticos'][chamado['id']]['correta'] and configuracao_ok(s['estados'], pc)
            and s['testes'][pc].get(SERVIDOR) is True)


def chamado_atual(s):
    """Primeiro chamado ainda aberto; os chamados são atendidos em ordem."""
    return next((c for c in CHAMADOS if not chamado_resolvido(s, c)), None)


def estado_publico(dados, ativo=False):
    s = deepcopy(dados or dados_iniciais())
    feitos = set()
    if ativo:
        for c in CHAMADOS:
            if not chamado_resolvido(s, c):
                break
            feitos.add(c['id'])
        if len(feitos) == len(CHAMADOS) and s['conclusao_validada']:
            feitos.add('comprovar')
    etapas = [{**e, 'concluida': e['id'] in feitos} for e in ETAPAS]
    chamados = []
    for c in CHAMADOS:
        d = s['diagnosticos'][c['id']]
        chamados.append({'id': c['id'], 'pc': c['pc'], 'titulo': c['titulo'], 'sintoma': c['sintoma'], 'ajuda': c['ajuda'],
            'resolvido': c['id'] in feitos, 'objetivo': c['objetivo'],
            'resolucao': c['resolucao'] if c['id'] in feitos else '',
            # O que já foi cumprido no chamado, lido do estado real; só diz sim ou não, sem a configuração esperada.
            'progresso': {'causa': d['correta'], 'configuracao': ativo and configuracao_ok(s['estados'], c['pc']),
                          'servidor': ativo and s['testes'][c['pc']].get(SERVIDOR) is True},
            'opcoes': [{'id': i, 'texto': c['causas'][i]} for i in d['ordem']],
            'resposta': d['resposta'], 'correta': d['correta']})
    return {'id': LABORATORIO_ID, 'titulo': TITULO, 'descricao': DESCRICAO, 'xp': XP,
        'nos': deepcopy(list(NOS.values())), 'pcs': deepcopy(PCS), 'etapas': etapas,
        'proxima_etapa': next((e['id'] for e in etapas if not e['concluida']), None),
        'concluido': all(e['concluida'] for e in etapas), 'retorno_preparado': True,
        'revisao': s['revisao'], 'terminal': s['terminal'], 'estados': s['estados'], 'testes': s['testes'],
        'chamados': chamados}


def montar_estado(evidencias=None):
    return estado_publico(None)
