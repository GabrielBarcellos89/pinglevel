"""Lab2 — Monte sua primeira LAN (versão 2, 30/10/2026): uma sala com um switch e três PCs. O aluno descobre a rede do
PC 1 pelo terminal, coloca o PC 2 na mesma rede e atende um chamado: o PC 3 tem o prefixo errado (/28) e, para ele, o
PC 1 fica em outra rede. Usa o que a aula de IPv4 ensina: endereço de rede, máscara e prefixo, mesma rede."""
import ipaddress
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'primeira-lan'
TITULO = 'Monte sua primeira LAN'
DESCRICAO = 'Descubra a rede do PC 1, coloque o PC 2 na mesma rede pelo terminal e resolva o chamado do PC 3.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.10.0/24'
PC1 = '192.168.10.10'
# O PC 3 começa com o prefixo errado: com /28, a rede dele vai de .32 a .47 e o PC 1 (.10) fica "em outra rede".
PC3_ERRADO = '192.168.10.40/28'

# Uma rede local só, sem roteador: não há gateway (a rota padrão de cada PC deve continuar vazia).
SETORES = {'sala': {'nome': 'Sala de estudos', 'rede': '192.168.10.0', 'prefixo': 24, 'gateway': None, 'interface': 'eth0'}}
SETORES_MODELO = ()
NOS = {
    'pc1': {'no': 1, 'nome': 'PC 1', 'host': 'pc-1', 'tipo': 'pc', 'setor': 'sala', 'interfaces': ['eth0']},
    'pc2': {'no': 2, 'nome': 'PC 2', 'host': 'pc-2', 'tipo': 'pc', 'setor': 'sala', 'interfaces': ['eth0']},
    'pc3': {'no': 3, 'nome': 'PC 3', 'host': 'pc-3', 'tipo': 'pc', 'setor': 'sala', 'interfaces': ['eth0']},
}
INICIAL = {
    'pc1': {'interfaces': {'eth0': [f'{PC1}/24']}, 'rota_padrao': None},
    'pc2': {'interfaces': {'eth0': []}, 'rota_padrao': None},
    'pc3': {'interfaces': {'eth0': [PC3_ERRADO]}, 'rota_padrao': None},
}
PLANO = [
    {'id': 'rede', 'rotulo': 'Endereço da rede', 'grupo': 'sala', 'tipo': 'ip', 'esperado': '192.168.10.0'},
    {'id': 'prefixo', 'rotulo': 'Prefixo', 'grupo': 'sala', 'tipo': 'prefixo', 'esperado': '24'},
    {'id': 'mascara', 'rotulo': 'Máscara', 'grupo': 'sala', 'tipo': 'mascara', 'esperado': '255.255.255.0'},
]
# O plano só é conferido depois de o aluno olhar o PC 1 pelo terminal.
OBSERVAR_PLANO = (('pc1', 'ver-enderecos', 'Antes de conferir, descubra o endereço do PC 1 pelo terminal, na aba PC 1.'),)


def dica_plano(respostas, erros):
    """Uma frase por campo errado, sem dizer o valor esperado."""
    dicas = []
    if 'rede' in erros:
        try:
            ip = ipaddress.ip_address(respostas['rede'].strip().split('/')[0])
        except ValueError:
            ip = None
        if ip is not None and ip in ipaddress.ip_network(REDE) and str(ip) != REDE.split('/')[0]:
            dicas.append(f'{ip} é um endereço de host, que um PC pode usar. O endereço da rede é o primeiro da faixa: '
                         'a parte do host fica toda em zero, e nenhum PC o usa.')
        else:
            dicas.append('O endereço da rede é o primeiro da faixa do PC 1: a parte do host fica toda em zero.')
    if 'prefixo' in erros:
        dicas.append('O prefixo é o número depois da barra, na linha inet do PC 1.')
    if 'mascara' in erros:
        dicas.append('A máscara é o prefixo escrito em quatro números: cada 8 bits de rede viram um 255.')
    return ' '.join(dicas)
CHAMADO = {
    'no': 'pc3', 'titulo': 'Chamado · PC 3', 'sintoma': 'Não fala com o PC 1, que está na mesma sala e no mesmo switch.',
    'objetivo': 'O PC 3 fica na rede 192.168.10.0/24, como os outros, e responde ao ping até o PC 1.',
    'observar': 'ver-enderecos', 'pedido_observar': 'Antes de responder, veja o endereço do PC 3 com ip addr show e compare com o do PC 1.',
    'causas': {
        'prefixo': 'O prefixo do PC 3 é /28, diferente do /24 da sala: para ele, o PC 1 está em outra rede.',
        'cabo': 'O cabo do PC 3 está desconectado: a interface está desligada.',
        'repetido': 'O PC 3 está usando o mesmo endereço IPv4 de outro computador.'},
    'correta': 'prefixo',
    'acerto': 'Isso! Com /28, o PC 3 acha que a rede dele vai só de 192.168.10.32 a .47. O PC 1 (.10) fica de fora e, '
              'sem gateway, o PC 3 nem tenta enviar. Troque o prefixo do PC 3 para /24.',
    'erro': 'Compare os dois endereços: a eth0 do PC 3 está UP? O endereço é igual ao de outro PC? E o número depois da '
            'barra é o mesmo do PC 1?',
    'resolucao': 'O PC 3 voltou para o prefixo /24 da sala e fala com o PC 1.',
}
ETAPAS = (
    {'id': 'plano', 'titulo': 'A rede do PC 1', 'orientacao': 'Veja o endereço do PC 1 e escreva a rede, o prefixo e a máscara.'},
    {'id': 'pc2', 'titulo': 'PC 2 na rede', 'orientacao': 'Dê ao PC 2 um endereço livre da mesma rede e comprove com ping.'},
    {'id': 'chamado', 'titulo': 'Chamado · PC 3', 'orientacao': CHAMADO['sintoma']},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os três PCs e repete os pings.'},
)
ALTERAVEIS = {'pc2': {'pc2': ('eth0',)}, 'chamado': {'pc3': ('eth0',)}}
SALA = SETORES['sala']


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def _testou(s, origem, destino):
    return destino is not None and s['testes'][origem].get(destino) is True


def progresso_chamado(s, etapa):
    return {'causa': s['diagnosticos']['chamado']['correta'], 'configuracao': base.pc_ok(s['estados'], 'pc3', SALA),
            'teste': _testou(s, 'pc3', PC1)}


def etapa_ok(s, etapa):
    if etapa == 'plano':
        return s['plano']['correto']
    if etapa == 'pc2':
        return base.pc_ok(s['estados'], 'pc2', SALA) and _testou(s, 'pc2', PC1)
    if etapa == 'chamado':
        return all(progresso_chamado(s, etapa).values())
    return False


def problemas(s):
    """O que impede a conclusão, relendo a configuração (usado pela validação final)."""
    return [NOS[no]['nome'] for no in NOS if not base.pc_ok(s['estados'], no, SALA)]


def testes_finais(s):
    return [('pc2', PC1), ('pc3', PC1), ('pc1', base.endereco_pc(s['estados'], 'pc2'))]


def estado_publico(dados, ativo=False):
    publico = base.estado_publico(sys.modules[__name__], dados, ativo)
    # A rede é a resposta da primeira etapa: só sai do servidor depois de o plano ser conferido.
    if not publico['plano']['correto']:
        publico['rede'] = None
    return publico


def montar_estado(evidencias=None):
    return estado_publico(None)
