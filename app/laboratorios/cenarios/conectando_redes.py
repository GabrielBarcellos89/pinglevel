"""Lab7 — Conectando redes: duas filiais ligadas por um enlace /30, tudo endereçado, mas sem rotas estáticas. O aluno
diagnostica, planeja e aplica a rota de ida e depois a de volta, vendo que só a ida não basta (roteiro: doc 57)."""
import sys

from laboratorios.cenarios import rede_setores as base

LABORATORIO_ID = 'conectando-redes'
TITULO = 'Conectando redes'
DESCRICAO = 'Ligue duas filiais com rotas estáticas: diagnóstico, plano, rota de ida, rota de volta e comprovação.'
XP = 100
TEMPO_LIMITE = 900
TEMPO_EXTENSAO = 300
MAX_EXTENSOES = 1
REDE = '192.168.10.0/24 · 192.168.20.0/24'

SETORES = {
    'a': {'nome': 'Filial A', 'rede': '192.168.10.0', 'prefixo': 24, 'gateway': '192.168.10.1', 'interface': 'eth0'},
    'b': {'nome': 'Filial B', 'rede': '192.168.20.0', 'prefixo': 24, 'gateway': '192.168.20.1', 'interface': 'eth0'},
}
SETORES_MODELO = ('a', 'b')  # todo o endereçamento já está pronto e visível; o que falta são as rotas
NOS = {
    'pca': {'no': 1, 'nome': 'PC A', 'host': 'pc-a', 'tipo': 'pc', 'setor': 'a', 'interfaces': ['eth0']},
    'r1': {'no': 5, 'nome': 'R1', 'host': 'r1', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1'], 'rotas': 'estaticas'},
    'r2': {'no': 6, 'nome': 'R2', 'host': 'r2', 'tipo': 'roteador', 'interfaces': ['eth0', 'eth1'], 'rotas': 'estaticas'},
    'pcb': {'no': 2, 'nome': 'PC B', 'host': 'pc-b', 'tipo': 'pc', 'setor': 'b', 'interfaces': ['eth0']},
}
INICIAL = {
    'pca': {'interfaces': {'eth0': ['192.168.10.10/24']}, 'rota_padrao': '192.168.10.1', 'rotas': []},
    'r1': {'interfaces': {'eth0': ['192.168.10.1/24'], 'eth1': ['10.0.0.1/30']}, 'rota_padrao': None, 'rotas': []},
    'r2': {'interfaces': {'eth0': ['192.168.20.1/24'], 'eth1': ['10.0.0.2/30']}, 'rota_padrao': None, 'rotas': []},
    'pcb': {'interfaces': {'eth0': ['192.168.20.10/24']}, 'rota_padrao': '192.168.20.1', 'rotas': []},
}
ROTA_R1 = '192.168.20.0/24 via 10.0.0.2'
ROTA_R2 = '192.168.10.0/24 via 10.0.0.1'
PCA, PCB = '192.168.10.10', '192.168.20.10'
PLANO = [
    {'id': 'r1-destino', 'rotulo': 'Rede de destino', 'grupo': 'r1', 'tipo': 'rede', 'esperado': '192.168.20.0/24'},
    {'id': 'r1-via', 'rotulo': 'Próximo salto', 'grupo': 'r1', 'tipo': 'ip', 'esperado': '10.0.0.2'},
    {'id': 'r2-destino', 'rotulo': 'Rede de destino', 'grupo': 'r2', 'tipo': 'rede', 'esperado': '192.168.10.0/24'},
    {'id': 'r2-via', 'rotulo': 'Próximo salto', 'grupo': 'r2', 'tipo': 'ip', 'esperado': '10.0.0.1'},
]
CHAMADO = {
    'no': 'r1', 'titulo': 'Chamado · Filial A', 'sintoma': 'O PC A não alcança o PC B, na outra filial.',
    'observar': 'ver-rotas', 'pedido_observar': 'Antes de responder, leia a tabela de rotas do R1 com ip route.',
    'causas': {
        'sem-rota': 'O R1 não tem rota para a rede do PC B.',
        'sem-gateway': 'O PC A está sem gateway.',
        'enlace': 'O enlace entre os roteadores está desligado.'},
    'correta': 'sem-rota',
    'acerto': 'Isso mesmo: o R1 só conhece as redes que toca (192.168.10.0/24 e 10.0.0.0/30). Falta dizer a ele como chegar a 192.168.20.0/24.',
    'erro': 'Releia: o PC A tem rota padrão? O ping ao 10.0.0.2 responde? E o que a tabela do R1 tem para 192.168.20.0/24?',
    # Uma suspeita por causa: onde testar e o que observar, sem a conclusão (validação de 17/11/2026: o aluno leu a
    # tabela do R1 sem saber o que procurar). A causa só é aceita depois das três testadas.
    'suspeitas': [
        {'id': 'sem-gateway', 'no': 'pca', 'tipo': 'ver-rotas', 'texto': 'O PC A tem gateway?', 'onde': 'PC A',
         'comando': 'ip route', 'olhar': 'Existe uma linha default via?'},
        {'id': 'enlace', 'no': 'r1', 'tipo': 'ping', 'alvo': '10.0.0.2', 'texto': 'O enlace entre os roteadores funciona?',
         'onde': 'R1', 'comando': 'ping 10.0.0.2', 'olhar': 'O R2 responde pelo enlace?'},
        {'id': 'sem-rota', 'no': 'r1', 'tipo': 'ver-rotas', 'texto': 'O R1 sabe chegar à rede do PC B?', 'onde': 'R1',
         'comando': 'ip route', 'olhar': 'Alguma linha leva a 192.168.20.0/24?'},
    ],
    # Errar aponta o teste do próprio aluno que descarta aquela causa, sem dizer qual é a certa.
    'erros': {
        'sem-gateway': 'Volte ao seu teste no PC A: o ip route mostrou uma linha default via? Se mostrou, o gateway existe. Reveja as outras suspeitas.',
        'enlace': 'Volte ao seu ping do R1 ao 10.0.0.2: o R2 respondeu? Se respondeu, o enlace funciona. Reveja as outras suspeitas.',
    },
}
PLANO_DEPOIS_DO_CHAMADO = True  # o plano só abre com a causa confirmada: uma tarefa de cada vez
ETAPAS = (
    {'id': 'chamado', 'titulo': 'Diagnóstico', 'orientacao': CHAMADO['sintoma']},
    {'id': 'plano', 'titulo': 'Plano de rotas', 'orientacao': 'Destino e próximo salto da rota de cada roteador.'},
    {'id': 'ida', 'titulo': 'Rota de ida', 'orientacao': 'Rota no R1 e ping do PC A ao PC B: o que acontece?'},
    {'id': 'volta', 'titulo': 'Rota de volta', 'orientacao': 'Rota no R2 e ping do PC A ao PC B de novo.'},
    {'id': 'comprovar', 'titulo': 'Comprovar', 'orientacao': 'O servidor relê os equipamentos e repete os pings nos dois sentidos.'},
)
ALTERAVEIS = {'ida': {'r1': ('rotas',)}, 'volta': {'r2': ('rotas',)}}


def dados_iniciais(sortear=None):
    return base.dados_iniciais(sys.modules[__name__], sortear)


def _roteadores_intactos(e):
    return all(e[r]['interfaces'] == INICIAL[r]['interfaces'] for r in ('r1', 'r2'))


def etapa_ok(s, etapa):
    e = s['estados']
    if etapa == 'chamado':
        return s['diagnosticos']['chamado']['correta']
    if etapa == 'plano':
        return s['plano']['correto']
    if etapa == 'ida':
        # A ida fecha com a rota no R1 e o ping ao PC B falhando; depois que a volta existe, a ida já foi vista.
        return e['r1']['rotas'] == [ROTA_R1] and (s['testes']['pca'].get(PCB) is False or e['r2']['rotas'] == [ROTA_R2])
    if etapa == 'volta':
        return e['r2']['rotas'] == [ROTA_R2] and s['testes']['pca'].get(PCB) is True
    return False


def problemas(s):
    e = s['estados']
    erros = []
    if e['r1']['rotas'] != [ROTA_R1] or not _roteadores_intactos(e):
        erros.append('R1')
    if e['r2']['rotas'] != [ROTA_R2] or not _roteadores_intactos(e):
        erros.append('R2')
    return erros + [NOS[pc]['nome'] for pc in ('pca', 'pcb') if not base.pc_ok(e, pc, SETORES[NOS[pc]['setor']])]


def testes_finais(s):
    return [('pca', PCB), ('pcb', PCA)]


def estado_publico(dados, ativo=False):
    return base.estado_publico(sys.modules[__name__], dados, ativo)


def montar_estado(evidencias=None):
    return estado_publico(None)
