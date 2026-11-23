"""Lab 9 com rede simulada: um switch (bridge com filtro de VLAN) e quatro PCs; imita iproute2, bridge e ping."""
import json
import threading
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import investigando_lan as lab9
from laboratorios.terminal_comandos import ErroComando, filtrar_bridge, filtrar_fdb, interpretar
from laboratorios.terminal_guiado import ErroTerminal
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import ANCORAS_9, PERFIL_LAB9

PERDA = (1, 'PING x 56(84) bytes of data.\n\n--- ping statistics ---\n2 packets transmitted, 0 received, 100% packet loss, time 1010ms')
OK = (0, '2 packets transmitted, 2 received, 0% packet loss')


class Lan:
    def __init__(self):
        self.vlans = {p: {'pvid': v['pvid'], 'membro': list(v['membro']), 'untagged': list(v['untagged'])}
                      for p, v in lab9.INICIAL['switch']['vlans'].items()}
        self.fdb = {}
        self.neigh = {pc: {} for pc in lab9.MACS}
        self.por_ip = {ip: pc for pc, ip in lab9.IPS.items()}

    def vlan_de(self, pc):
        v = self.vlans[lab9.PORTAS[pc]]
        return v['pvid'] if v['pvid'] in v['membro'] and v['pvid'] in v['untagged'] else None

    def ping(self, origem, ip):
        destino = self.por_ip.get(ip)
        if destino is None or self.vlan_de(origem) is None or self.vlan_de(origem) != self.vlan_de(destino):
            return PERDA
        for pc in (origem, destino):
            self.fdb[lab9.MACS[pc]] = (lab9.PORTAS[pc], self.vlan_de(pc))
        self.neigh[origem][ip] = lab9.MACS[destino]
        self.neigh[destino][lab9.IPS[origem]] = lab9.MACS[origem]
        return OK

    def executar(self, no, cmd):
        p = cmd.split()
        if no == 'switch':
            portas = ['eth0', 'eth1', 'eth2', 'eth3']
            if cmd == 'ip -j addr show':
                return 0, json.dumps([{'ifname': f'{n}@if{i}', 'flags': ['UP'], 'addr_info': []} for i, n in enumerate(portas)]
                                     + [{'ifname': 'ctrl0', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': '172.30.9.5', 'prefixlen': 24}]}])
            if cmd == 'ip -j -4 route show':
                return 0, json.dumps([{'dst': '172.30.9.0/24', 'dev': 'ctrl0'}])
            if cmd == 'bridge -j vlan show':
                return 0, json.dumps([{'ifname': n, 'vlans': [{'vlan': v, 'flags': (['PVID'] if v == x['pvid'] else [])
                                       + (['Egress Untagged'] if v in x['untagged'] else [])} for v in x['membro']]}
                                      for n, x in self.vlans.items()] + [{'ifname': 'br0', 'vlans': [{'vlan': 1, 'flags': ['PVID']}]}])
            if cmd == 'bridge vlan show':
                return 0, 'port              vlan-id  \n' + ''.join(
                    f"{n:<18}{' '.join(str(v) for v in x['membro'])} PVID Egress Untagged\n" for n, x in self.vlans.items()) + 'br0               1 PVID Egress Untagged\nctrl0             1'
            if cmd == 'bridge fdb show br br0':
                return 0, '33:33:00:00:00:01 dev br0 self permanent\n' + ''.join(
                    f'{m} dev {porta} vlan {v} master br0\n' for m, (porta, v) in self.fdb.items()) + '02:aa:00:00:00:01 dev eth0 vlan 1 master br0 permanent'
            if cmd == 'bridge link show':
                return 0, '\n'.join(f'{i + 4}: {n}@if{i}: <BROADCAST,UP> mtu 1500 master br0 state forwarding' for i, n in enumerate(portas))
            if p[:3] == ['bridge', 'vlan', 'add']:
                x, vid = self.vlans[p[4]], int(p[6])
                x['membro'] = sorted({*x['membro'], vid})
                if 'pvid' in p:
                    x['pvid'] = vid
                if 'untagged' in p:
                    x['untagged'] = sorted({*x['untagged'], vid})
                return 0, ''
            if p[:3] == ['bridge', 'vlan', 'del']:
                x, vid = self.vlans[p[4]], int(p[6])
                if vid not in x['membro']:
                    return 255, 'RTNETLINK answers: No such file or directory'
                x['membro'].remove(vid)
                x['untagged'] = [v for v in x['untagged'] if v != vid]
                x['pvid'] = None if x['pvid'] == vid else x['pvid']
                return 0, ''
            raise AssertionError(f'comando inesperado no switch: {cmd}')
        ip = lab9.IPS[no]
        if cmd == 'ip -j addr show':
            return 0, json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': ip, 'prefixlen': 24}]}])
        if cmd == 'ip -j -4 route show':
            return 0, json.dumps([{'dst': '192.168.30.0/24', 'dev': 'eth0', 'prefsrc': ip}])
        if cmd == 'ip neigh show dev eth0':
            return 0, '\n'.join(f'{i} lladdr {m} REACHABLE' for i, m in self.neigh[no].items())
        if cmd == 'ip link show dev eth0':
            return 0, f'2: eth0@if7: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n    link/ether {lab9.MACS[no]} brd ff:ff:ff:ff:ff:ff'
        if cmd.startswith('ip addr show'):
            return 0, f'2: eth0: <UP>\n    inet {ip}/24 scope global eth0'
        if p[0] == 'ping':
            return self.ping(no, p[-1])
        raise AssertionError(f'comando inesperado: {cmd}')


class Engine:
    def __init__(self):
        self._lock = threading.RLock()
        self.lab = None
        self.lan = Lan()
        self.por_id = {info['no']: chave for chave, info in lab9.NOS.items()}

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.lab = SimpleNamespace(usuario_id=uid, session_id=5, laboratorio_id=labid)
        return self.lab

    def obter(self, uid):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def dados_temporais(self, lab):
        return {'segundos_restantes': 900}

    def executar(self, uid, node, cmd, timeout=8):
        assert self._lock._is_owned()
        return self.lan.executar(self.por_id[node], cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True


def servico():
    salvos = []
    s = ServicoRede(Engine(), lambda uid, lab: (salvos.append(lab) or {'xp_concedido': 100}), cenario=lab9, perfil_tutor=PERFIL_LAB9)
    return s, salvos


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(7, 'aluno', acao, extra)
    estado = act(s, 'status')
    return s.executar_acao(7, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
        'revisao': estado['missao']['revisao'], **extra})


def term(s, no, comando):
    return act(s, 'terminal', pc=no, comando=comando)['missao']


def investigar(s):
    term(s, 'f1', 'ping 192.168.30.22')
    term(s, 'f1', 'ip neigh')
    term(s, 'switch', 'bridge fdb show')
    return act(s, 'planejar', respostas={'mac-f2': '02:16:3E:7D:02:9F', 'porta-f2': 'eth3'})


def chamado(s):
    term(s, 'switch', 'bridge vlan show')
    act(s, 'diagnosticar', resposta='vlan-errada')
    term(s, 'switch', 'bridge vlan add dev eth1 vid 10 pvid untagged')
    term(s, 'switch', 'bridge vlan del dev eth1 vid 20')
    return term(s, 'v2', 'ping 192.168.30.11')


def separar(s):
    for porta in ('eth2', 'eth3'):
        term(s, 'switch', f'bridge vlan add dev {porta} vid 20 pvid untagged')
        term(s, 'switch', f'bridge vlan del dev {porta} vid 1')
    term(s, 'f1', 'ping 192.168.30.22')
    return term(s, 'f1', 'ping 192.168.30.11')


def test_percurso_completo_com_isolamento_comprovado():
    s, salvos = servico()
    inicio = act(s, 'iniciar')['missao']
    assert inicio['proxima_etapa'] == 'investigar' and inicio['portas'] == {}
    assert inicio['estados']['switch']['vlans']['eth1'] == lab9.acesso(20)
    assert investigar(s)['missao']['proxima_etapa'] == 'chamado'
    assert act(s, 'status')['missao']['portas']['eth3'] == 'PC F2'
    assert chamado(s)['proxima_etapa'] == 'separar'
    m = separar(s)
    assert m['testes']['f1'] == {'192.168.30.22': True, '192.168.30.11': False} and m['proxima_etapa'] == 'comprovar'
    final = act(s, 'validar')
    assert final['xp_concedido'] == 100 and salvos == [lab9.LABORATORIO_ID]


def test_investigacao_exige_ler_as_duas_tabelas_e_aceita_mac_em_maiusculas():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='ip neigh show'):
        act(s, 'planejar', respostas={'mac-f2': lab9.MACS['f2'], 'porta-f2': 'eth3'})
    term(s, 'f1', 'ping 192.168.30.22')
    term(s, 'f1', 'ip n')
    with pytest.raises(ErroTerminal, match='bridge fdb show'):
        act(s, 'planejar', respostas={'mac-f2': lab9.MACS['f2'], 'porta-f2': 'eth3'})
    term(s, 'switch', 'bridge fdb')
    errado = act(s, 'planejar', respostas={'mac-f2': lab9.MACS['f1'], 'porta-f2': 'eth3'})
    assert errado['missao']['plano']['erros'] == ['mac-f2'] and errado['missao']['portas'] == {}


def test_tabela_arp_so_tem_o_vizinho_depois_do_ping_e_fdb_esconde_entradas_fixas():
    s, _ = servico()
    act(s, 'iniciar')
    assert term(s, 'f1', 'ip neigh show')['terminal'][-1]['saida'] == ''
    term(s, 'f1', 'ping 192.168.30.22')
    assert lab9.MACS['f2'] in term(s, 'f1', 'ip neigh show')['terminal'][-1]['saida']
    saida = term(s, 'switch', 'bridge fdb show')['terminal'][-1]['saida']
    assert 'eth3' in saida and 'permanent' not in saida and 'br0 self' not in saida
    assert 'ctrl0' not in term(s, 'switch', 'bridge vlan')['terminal'][-1]['saida']


def test_switch_so_muda_a_porta_da_etapa_e_so_depois_da_causa():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='observe'):
        term(s, 'switch', 'bridge vlan add dev eth1 vid 10 pvid untagged')
    investigar(s)
    with pytest.raises(ErroTerminal, match='causa'):
        term(s, 'switch', 'bridge vlan add dev eth1 vid 10 pvid untagged')
    term(s, 'switch', 'bridge vlan show')
    act(s, 'diagnosticar', resposta='vlan-errada')
    with pytest.raises(ErroTerminal, match='eth1'):
        term(s, 'switch', 'bridge vlan add dev eth2 vid 20 pvid untagged')
    term(s, 'switch', 'bridge vlan add dev eth1 vid 10 pvid untagged')
    term(s, 'switch', 'bridge vlan del dev eth1 vid 20')
    term(s, 'v2', 'ping 192.168.30.11')
    with pytest.raises(ErroTerminal, match='eth2, eth3'):
        term(s, 'switch', 'bridge vlan del dev eth0 vid 10')


def test_mudar_uma_porta_invalida_so_os_testes_do_pc_dela():
    s, _ = servico()
    act(s, 'iniciar')
    investigar(s)
    chamado(s)
    term(s, 'f1', 'ping 192.168.30.22')
    term(s, 'v1', 'ping 192.168.30.21')
    m = term(s, 'switch', 'bridge vlan add dev eth2 vid 20 pvid untagged')
    assert m['testes']['f1'] == {} and m['testes']['v1'] == {}
    assert m['testes']['v2'] == {'192.168.30.11': True} and m['proxima_etapa'] == 'separar'
    assert 'eth2: VLANs 1, 20 (PVID 20)' in m['terminal'][-1]['confirmacao']


def test_conclusao_recusa_switch_alterado_depois_das_etapas():
    s, _ = servico()
    act(s, 'iniciar')
    investigar(s)
    chamado(s)
    separar(s)
    term(s, 'f1', 'ping 192.168.30.22')
    term(s, 'f1', 'ping 192.168.30.11')
    s.engine.lan.vlans['eth0'] = {'pvid': 20, 'membro': [20], 'untagged': [20]}
    with pytest.raises(ErroTerminal, match='Switch'):
        act(s, 'validar')


@pytest.mark.parametrize('comando, mensagem', [
    ('bridge vlan add dev eth9 vid 10 pvid untagged', 'portas'),
    ('bridge vlan add dev eth1 vid 5000', 'vid'),
    ('bridge vlan add dev eth1 vid 10 tagged', 'pvid e untagged'),
    ('bridge vlan del dev eth1 vid 20 pvid', 'basta'),
    ('ping 192.168.30.11', 'não tem endereço IP'),
    ('ip addr show', 'bridge'),
    ('bridge mdb show', 'bridge link show, bridge fdb show'),
    ('ip neigh show', 'não tem tabela ARP.*bridge fdb show'),
    ('arp', 'tabela MAC: bridge fdb show'),
])
def test_interpretador_do_switch_recusa_o_que_nao_e_permitido(comando, mensagem):
    with pytest.raises(ErroComando, match=mensagem):
        interpretar(comando, interfaces=('eth0', 'eth1', 'eth2', 'eth3'), tipo='switch')


def test_interpretador_monta_os_comandos_do_switch_e_dos_pcs():
    portas = ('eth0', 'eth1', 'eth2', 'eth3')
    assert interpretar('bridge vlan add dev eth2 vid 20 untagged pvid', interfaces=portas, tipo='switch').executar == \
        'bridge vlan add dev eth2 vid 20 pvid untagged'
    assert interpretar('bridge fdb', interfaces=portas, tipo='switch').executar == 'bridge fdb show br br0'
    assert interpretar('ip n').executar == 'ip neigh show dev eth0'
    assert interpretar('ip link show').tipo == 'ver-link'
    with pytest.raises(ErroComando, match='aba do switch'):
        interpretar('bridge vlan show')


def test_filtros_de_saida():
    vlan = 'port              vlan-id  \neth0              10 PVID Egress Untagged\nctrl0             1\n                  5\nbr0               1'
    assert filtrar_bridge(vlan, ('eth0',)) == 'port              vlan-id  \neth0              10 PVID Egress Untagged\nbr0               1'
    assert 'vazia' in filtrar_fdb('aa:bb dev br0 self permanent', ('eth0',))
    ruido = '7a:f6:33:6a:e3:9a dev eth2 vlan 1 master br0\n02:16:3e:7d:02:4e dev eth2 vlan 1 master br0'
    assert filtrar_fdb(ruido, ('eth2',), {lab9.MACS['f1']}) == '02:16:3e:7d:02:4e dev eth2 vlan 1 master br0'


def test_tutor_nao_entrega_mac_porta_nem_causa():
    bloquear = PERFIL_LAB9.bloquear
    missao = lab9.estado_publico(lab9.dados_iniciais(), True)
    assert bloquear(f"O MAC é {lab9.MACS['f2']}.", 'investigar', 1, missao, 'qual o mac?', {}) == 'filtro'
    assert bloquear('Ele está na porta eth3.', 'investigar', 1, missao, 'qual a porta?', {}) == 'filtro'
    assert bloquear('Leia a coluna dev em bridge fdb show.', 'investigar', 1, missao, 'como?', {}) is None
    missao['proxima_etapa'] = 'chamado'
    assert bloquear('A porta do V2 está na VLAN errada.', 'chamado', 1, missao, 'por quê?', {}) == 'filtro'
    assert bloquear('Use bridge vlan add dev eth1 vid 10 pvid untagged.', 'chamado', 2, missao, 'e agora?', {}) == 'filtro'
    # Validação de 22/11/2026: o Link indicou a eth0 para o PC V2. Porta fora da etapa é barrada, mesmo no nível 4.
    assert bloquear('Use bridge vlan add dev eth0 vid 10 pvid untagged.', 'chamado', 4, missao, 'qual comando?', {}) == 'filtro'
    assert bloquear('Para a eth1: bridge vlan del dev eth1 vid 20.', 'chamado', 4, missao, 'qual comando?', {}) is None
    assert bloquear('bridge vlan add dev eth1 vid 20 pvid untagged', 'separar', 4, missao, 'qual comando?', {}) == 'filtro'


def test_contexto_do_link_traz_a_porta_de_cada_pc_so_depois_da_investigacao():
    from laboratorios.tutor_setores import PERFIL_LAB9
    dados = lab9.dados_iniciais()
    missao = lab9.estado_publico(dados, True)
    assert 'portas_do_switch' not in PERFIL_LAB9.contexto(missao)
    missao['plano']['correto'] = True
    missao['proxima_etapa'] = 'chamado'
    contexto = PERFIL_LAB9.contexto(missao)
    assert contexto['portas_do_switch']['eth1'] == 'PC V2'
    assert contexto['portas_que_esta_etapa_permite_alterar'] == ['eth1']


def test_ancoras_do_lab9_existem_no_indice():
    from laboratorios.tutor_referencias import buscar_ancoras
    try:
        trechos = buscar_ancoras(sorted({i for ids in ANCORAS_9.values() for i in ids}))
    except Exception:
        pytest.skip('índice RAG indisponível neste ambiente')
    assert len(trechos) == len({i for ids in ANCORAS_9.values() for i in ids})
