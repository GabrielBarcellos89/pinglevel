"""Serviço do Lab4 (chamados) com rede simulada: o simulador imita as respostas reais do iproute2 e do ping."""
import ipaddress
import json
import threading
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import configure_terminal as cenario
from laboratorios.terminal_guiado import ErroTerminal, ServicoTerminal

LAB = 'configure-pelo-terminal'
ATENDIMENTO = ipaddress.IPv4Network('192.168.10.0/24')
ROTEADOR, SERVIDOR = '192.168.10.1', '192.168.20.10'


def ping(ok):
    return (0, '2 packets transmitted, 2 received, 0% packet loss') if ok else (1, '2 packets transmitted, 0 received, 100% packet loss')


class No:
    """Um PC simulado: endereços em eth0 e rota padrão; conhece a rede para responder ao ping."""
    def __init__(self, rede, enderecos=(), rota=None):
        self.rede, self.enderecos, self.rota = rede, list(enderecos), rota

    def interfaces(self):
        return [ipaddress.IPv4Interface(e) for e in self.enderecos]

    def origem(self, alvo):
        return next((i.ip for i in self.interfaces() if alvo in i.network), None)

    def responde_a(self, origem):
        """Um PC só responde se a origem é alcançável por ele: rede direta ou rota padrão pelo roteador."""
        if any(origem in i.network for i in self.interfaces()):
            return True
        return self.rota == ROTEADOR and origem in ATENDIMENTO

    def executar(self, cmd):
        p = cmd.split()
        if cmd == 'ip -j addr show dev eth0':
            info = [{'family': 'inet', 'local': e.split('/')[0], 'prefixlen': int(e.split('/')[1])} for e in self.enderecos]
            return 0, json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': info}])
        if cmd == 'ip -j -4 route show default':
            return 0, json.dumps([{'dst': 'default', 'gateway': self.rota, 'dev': 'eth0'}] if self.rota else [])
        if cmd == 'ip addr show dev eth0':
            return 0, '2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>\n' + ''.join(f'    inet {e} scope global eth0\n' for e in self.enderecos)
        if cmd == 'ip -4 route show':
            linhas = ['172.30.1.0/24 dev eth1 proto kernel scope link src 172.30.1.1']
            linhas += [f'{i.network} dev eth0 proto kernel scope link src {i.ip}' for i in self.interfaces()]
            return 0, '\n'.join(([f'default via {self.rota} dev eth0'] if self.rota else []) + linhas)
        if p[:3] == ['ip', 'addr', 'add']:
            if p[3] in self.enderecos:
                return 2, 'Error: ipv4: Address already assigned.'
            self.enderecos.append(p[3])
            return 0, ''
        if p[:3] == ['ip', 'addr', 'del']:
            if p[3] not in self.enderecos:
                return 2, 'Error: ipv4: Address not found.'
            self.enderecos.remove(p[3])
            if self.rota and self.origem(ipaddress.IPv4Address(self.rota)) is None:
                self.rota = None  # o kernel remove a rota cujo gateway deixou de ser alcançável
            return 0, ''
        if p[:4] == ['ip', 'route', 'add', 'default']:
            if self.rota:
                return 2, 'RTNETLINK answers: File exists'
            if self.origem(ipaddress.IPv4Address(p[5])) is None:
                return 2, 'Error: Nexthop has invalid gateway.'
            self.rota = p[5]
            return 0, ''
        if p[:4] == ['ip', 'route', 'del', 'default']:
            if not self.rota:
                return 2, 'RTNETLINK answers: No such process'
            self.rota = None
            return 0, ''
        if p[0] == 'ping':
            return self.rede.ping(self, ipaddress.IPv4Address(p[-1]))
        raise AssertionError(f'comando inesperado: {cmd}')


class Rede:
    """Atendimento 192.168.10.0/24 (PCs e roteador .1) e servidor 192.168.20.10 atrás do roteador."""
    def __init__(self):
        self.pcs = {1: No(self), 2: No(self, ['192.168.10.12/24'], '192.168.10.11'),
                    6: No(self, ['192.168.10.11/16'], ROTEADOR)}

    def dono(self, ip):
        return next((n for n in self.pcs.values() if any(i.ip == ip for i in n.interfaces())), None)

    def ping(self, no, destino):
        origem = no.origem(destino)
        if origem is not None:  # entrega direta
            if str(destino) == ROTEADOR:
                return ping(origem in ATENDIMENTO)
            alvo = self.dono(destino)
            # Ninguém responde ao ARP: com -c 2 -W 1 o ping real só mostra a perda (ensaio no CORE, 29/10/2026).
            return ping(alvo is not None and alvo is not no and alvo.responde_a(origem))
        if not no.rota:
            return 2, 'ping: connect: Network unreachable'
        origem = no.origem(ipaddress.IPv4Address(no.rota))
        # Só o roteador encaminha; o firewall dele aceita o Atendimento /24 até a rede do servidor.
        return ping(no.rota == ROTEADOR and str(destino) == SERVIDOR and origem in ATENDIMENTO)


class Engine:
    def __init__(self):
        self._lock = threading.RLock()
        self.lab = None
        self.rede = Rede()
        self.comandos = []

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.lab = SimpleNamespace(usuario_id=uid, session_id=5, laboratorio_id=labid)
        return self.lab

    def obter(self, uid):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def dados_temporais(self, lab):
        return {'tempo_restante': 900, 'extensoes_usadas': 0}

    def executar(self, uid, node, cmd, timeout=8):
        assert node in self.rede.pcs and timeout == 8 and self._lock._is_owned()
        self.comandos.append((node, cmd))
        return self.rede.pcs[node].executar(cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True

    def estender(self, uid):
        pass


def servico():
    salvos = []
    s = ServicoTerminal(Engine(), lambda uid, lab: (salvos.append(lab) or {'xp_concedido': 100 if len(salvos) == 1 else 0}))
    return s, salvos


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(7, 'aluno', acao, extra)
    estado = act(s, 'status')
    return s.executar_acao(7, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
        'revisao': estado['missao']['revisao'], **extra})


def term(s, comando, pc='novo'):
    return act(s, 'terminal', comando=comando, pc=pc)['missao']


RESOLVER = {
    'chamado-1': ('novo', 'sem-ipv4', ['ip addr show', 'ip addr add 192.168.10.30/24 dev eth0',
                                       'ip route add default via 192.168.10.1', 'ping 192.168.20.10']),
    'chamado-2': ('financeiro', 'gateway-errado', ['ip route', 'ip route del default',
                                                   'ip route add default via 192.168.10.1', 'ping 192.168.20.10']),
    'chamado-3': ('recepcao', 'prefixo', ['ip addr show', 'ip addr del 192.168.10.11/16 dev eth0',
                                          'ip addr add 192.168.10.11/24 dev eth0', 'ip route add default via 192.168.10.1',
                                          'ping 192.168.20.10']),
}


def resolver(s, chamado):
    pc, causa, comandos = RESOLVER[chamado]
    term(s, comandos[0], pc)
    act(s, 'diagnosticar', resposta=causa)
    for comando in comandos[1:]:
        m = term(s, comando, pc)
    return m


def levar_ate(s, etapa):
    """Inicia e resolve os chamados anteriores à etapa pedida (usado também pela validação do tutor)."""
    act(s, 'iniciar')
    for chamado in ('chamado-1', 'chamado-2', 'chamado-3'):
        if chamado == etapa:
            break
        resolver(s, chamado)
    assert act(s, 'status')['missao']['proxima_etapa'] == etapa, etapa


def test_percurso_completo_conclui_com_xp_e_estado_real():
    s, salvos = servico()
    estado = act(s, 'iniciar')
    assert estado['missao']['proxima_etapa'] == 'chamado-1'
    assert estado['missao']['estados']['financeiro']['rota_padrao'] == '192.168.10.11'
    m = term(s, 'ping 192.168.10.12')
    assert 'Network unreachable' in m['terminal'][-1]['saida'] and m['terminal'][-1]['pc'] == 'novo'
    assert resolver(s, 'chamado-1')['proxima_etapa'] == 'chamado-2'
    m = term(s, 'ping 192.168.20.10', 'financeiro')
    assert m['testes']['financeiro'][SERVIDOR] is False
    assert term(s, 'ping 192.168.10.30', 'financeiro')['testes']['financeiro']['192.168.10.30'] is True
    assert resolver(s, 'chamado-2')['proxima_etapa'] == 'chamado-3'
    m = term(s, 'ping 192.168.20.10', 'recepcao')
    assert '100% packet loss' in m['terminal'][-1]['saida'] and m['testes']['recepcao'][SERVIDOR] is False
    assert resolver(s, 'chamado-3')['proxima_etapa'] == 'comprovar'
    final = act(s, 'validar')
    assert final['xp_concedido'] == 100 and final['conclusao']['registrada'] and salvos == [LAB]


def test_alteracao_exige_a_causa_e_a_causa_exige_observar_o_pc_do_chamado():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='causa'):
        term(s, 'ip addr add 192.168.10.30/24 dev eth0')
    term(s, 'ip addr show', 'financeiro')
    with pytest.raises(ErroTerminal, match='ip addr show'):
        act(s, 'diagnosticar', resposta='sem-ipv4')
    term(s, 'ip a')
    errado = act(s, 'diagnosticar', resposta='cabo')
    assert errado['missao']['proxima_etapa'] == 'chamado-1' and 'UP' in errado['mensagem']
    certo = act(s, 'diagnosticar', resposta='sem-ipv4')
    assert certo['missao']['chamados'][0]['correta'] and 'Isso mesmo' in certo['mensagem']
    with pytest.raises(ErroTerminal, match='já foi identificada'):
        act(s, 'diagnosticar', resposta='cabo')


def test_so_o_pc_do_chamado_aberto_pode_ser_alterado_mas_todos_podem_ser_observados():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'ip a')
    act(s, 'diagnosticar', resposta='sem-ipv4')
    with pytest.raises(ErroTerminal, match='chamado aberto é do PC Novo'):
        term(s, 'ip route del default', 'financeiro')
    m = term(s, 'ip route', 'financeiro')
    assert 'default via 192.168.10.11' in m['terminal'][-1]['saida']
    with pytest.raises(ErroTerminal, match='Escolha um dos computadores'):
        term(s, 'ip a', 'roteador')


def test_chamado_2_pede_ler_a_tabela_de_rotas_e_chamado_3_pede_a_interface():
    s, _ = servico()
    levar_ate(s, 'chamado-2')
    term(s, 'ip a', 'financeiro')
    with pytest.raises(ErroTerminal, match='ip route'):
        act(s, 'diagnosticar', resposta='gateway-errado')
    term(s, 'ip r', 'financeiro')
    errado = act(s, 'diagnosticar', resposta='sem-rota')
    assert errado['missao']['chamados'][1]['correta'] is False and 'Para onde ela aponta' in errado['mensagem']
    resolver_restante = ['ip route del default', 'ip route add default via 192.168.10.1', 'ping 192.168.20.10']
    act(s, 'diagnosticar', resposta='gateway-errado')
    for comando in resolver_restante:
        term(s, comando, 'financeiro')
    term(s, 'ip r', 'recepcao')
    with pytest.raises(ErroTerminal, match='ip addr show'):
        act(s, 'diagnosticar', resposta='prefixo')


def test_ordem_das_opcoes_varia_entre_sessoes():
    posicoes = {cenario.dados_iniciais()['diagnosticos']['chamado-1']['ordem'].index('sem-ipv4') for _ in range(60)}
    assert len(posicoes) > 1
    fixa = cenario.dados_iniciais(sortear=lambda itens, n: list(reversed(itens)))
    opcoes = cenario.estado_publico(fixa, True)['chamados'][2]['opcoes']
    assert [o['id'] for o in opcoes] == list(reversed(list(cenario.CHAMADOS[2]['causas'])))


def test_recusa_do_interpretador_nao_executa_nada_nem_muda_revisao():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'ip a')
    act(s, 'diagnosticar', resposta='sem-ipv4')
    antes = act(s, 'status')['missao']['revisao']
    comandos = len(s.engine.comandos)
    for perigoso in ('ip a; reboot', 'ip addr add 192.168.10.12/24 dev eth0', 'ip addr add 192.168.10.11/24 dev eth0',
                     'ping -c 9 192.168.10.12', 'ip addr add 192.168.10.30/24 dev eth1'):
        with pytest.raises(ErroTerminal):
            term(s, perigoso)
    assert act(s, 'status')['missao']['revisao'] == antes and len(s.engine.comandos) == comandos


def test_erros_reais_aparecem_e_a_confirmacao_so_vem_quando_o_comando_nao_imprime_nada():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'ip a')
    act(s, 'diagnosticar', resposta='sem-ipv4')
    m = term(s, 'ip route add default via 192.168.10.1')
    ultimo = m['terminal'][-1]
    assert ultimo['saida'] == 'Error: Nexthop has invalid gateway.' and ultimo['confirmacao'] == ''
    m = term(s, 'ip addr add 192.168.10.30/24 dev eth0')
    assert m['terminal'][-1]['confirmacao'] == 'eth0: 192.168.10.30/24 · rota padrão: nenhuma'
    m = term(s, 'ip addr add 192.168.10.30/24 dev eth0')
    assert 'already assigned' in m['terminal'][-1]['saida']
    assert term(s, 'ip a')['terminal'][-1]['confirmacao'] == ''


def test_trocar_o_prefixo_derruba_a_rota_padrao_e_o_chamado_3_exige_recoloca_la():
    s, _ = servico()
    levar_ate(s, 'chamado-3')
    term(s, 'ip addr show', 'recepcao')
    act(s, 'diagnosticar', resposta='prefixo')
    term(s, 'ip addr del 192.168.10.11/16 dev eth0', 'recepcao')
    m = term(s, 'ip addr add 192.168.10.11/24 dev eth0', 'recepcao')
    assert m['terminal'][-1]['confirmacao'] == 'eth0: 192.168.10.11/24 · rota padrão: nenhuma'
    m = term(s, 'ping 192.168.20.10', 'recepcao')
    assert 'Network unreachable' in m['terminal'][-1]['saida'] and m['proxima_etapa'] == 'chamado-3'
    term(s, 'ip route add default via 192.168.10.1', 'recepcao')
    assert term(s, 'ping 192.168.20.10', 'recepcao')['proxima_etapa'] == 'comprovar'


def test_mudar_a_configuracao_invalida_os_testes_daquele_pc():
    s, _ = servico()
    levar_ate(s, 'chamado-2')
    term(s, 'ip r', 'financeiro')
    act(s, 'diagnosticar', resposta='gateway-errado')
    m = term(s, 'ping 192.168.10.30', 'financeiro')
    assert m['testes']['financeiro'] == {'192.168.10.30': True}
    m = term(s, 'ip route del default', 'financeiro')
    assert m['testes']['financeiro'] == {} and m['testes']['novo'][SERVIDOR] is True


def test_dois_enderecos_nao_resolvem_o_chamado():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'ip a')
    act(s, 'diagnosticar', resposta='sem-ipv4')
    for c in ('ip addr add 192.168.10.30/24 dev eth0', 'ip addr add 192.168.10.40/24 dev eth0',
              'ip route add default via 192.168.10.1'):
        term(s, c)
    m = term(s, 'ping 192.168.20.10')
    assert m['testes']['novo'][SERVIDOR] is True and m['proxima_etapa'] == 'chamado-1'
    term(s, 'ip addr del 192.168.10.40/24 dev eth0')
    assert term(s, 'ping 192.168.20.10')['proxima_etapa'] == 'chamado-2'


def test_conclusao_revalida_e_detecta_mudanca_em_qualquer_pc():
    s, _ = servico()
    levar_ate(s, 'chamado-3')
    resolver(s, 'chamado-3')
    s.engine.rede.pcs[2].rota = None  # alteração fora do terminal do aluno
    with pytest.raises(ErroTerminal, match='PC Financeiro'):
        act(s, 'validar')
    with pytest.raises(ErroTerminal, match='Resolva os três chamados'):
        act(s, 'validar')


def test_validar_antes_dos_chamados_e_recusado():
    s, _ = servico()
    levar_ate(s, 'chamado-2')
    with pytest.raises(ErroTerminal, match='três chamados'):
        act(s, 'validar')


def test_revisao_ou_sessao_antiga_sao_recusadas():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal) as erro:
        s.executar_acao(7, 'aluno', 'terminal', {'session_id': 5, 'revisao': 99, 'comando': 'ip a', 'pc': 'novo'})
    assert erro.value.status == 409
    with pytest.raises(ErroTerminal) as erro:
        s.executar_acao(7, 'aluno', 'terminal', {'session_id': 4, 'revisao': 0, 'comando': 'ip a', 'pc': 'novo'})
    assert erro.value.status == 409


@pytest.mark.parametrize('no, campo, valor', [(1, 'enderecos', ['192.168.10.10/24']), (2, 'rota', '192.168.10.1'),
                                              (6, 'enderecos', ['192.168.10.11/24'])])
def test_iniciar_recusa_pc_preparado_diferente_do_previsto(no, campo, valor):
    s, _ = servico()
    setattr(s.engine.rede.pcs[no], campo, valor)
    with pytest.raises(ErroTerminal) as erro:
        act(s, 'iniciar')
    assert erro.value.status == 503


def test_campos_extras_e_acoes_desconhecidas():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal):
        act(s, 'terminal', comando='ip a', xp=100)
    with pytest.raises(ErroTerminal) as erro:
        s.executar_acao(7, 'aluno', 'aplicar', {})
    assert erro.value.status == 404


def test_chamado_mostra_o_que_ja_foi_cumprido_e_o_resolvido_explica_a_correcao():
    s, _ = servico()
    m = act(s, 'iniciar')['missao']
    primeiro = m['chamados'][0]
    assert primeiro['objetivo'] and primeiro['resolucao'] == ''
    assert primeiro['progresso'] == {'causa': False, 'configuracao': False, 'servidor': False}
    term(s, 'ip addr show')
    act(s, 'diagnosticar', resposta='sem-ipv4')
    m = term(s, 'ip addr add 192.168.10.30/24 dev eth0')
    assert m['chamados'][0]['progresso'] == {'causa': True, 'configuracao': False, 'servidor': False}
    m = term(s, 'ip route add default via 192.168.10.1')
    assert m['chamados'][0]['progresso']['configuracao'] and not m['chamados'][0]['resolvido']
    m = term(s, 'ping 192.168.20.10')
    assert m['chamados'][0]['resolvido'] and 'rota padrão' in m['chamados'][0]['resolucao']
    assert m['chamados'][1]['resolucao'] == ''
