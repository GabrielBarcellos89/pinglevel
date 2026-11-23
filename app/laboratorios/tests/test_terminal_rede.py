"""Labs 5 e 6 com rede simulada: segmentos (switches), roteador que encaminha e as respostas do iproute2 e do ping."""
import ipaddress
import json
import threading
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import conectando_redes as lab7, dividindo_rede as lab5, planejando_empresa as lab6
from laboratorios.terminal_guiado import ErroTerminal
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import PERFIL_LAB5, PERFIL_LAB6, PERFIL_LAB7

PERDA = (1, 'PING x 56(84) bytes of data.\n\n--- ping statistics ---\n2 packets transmitted, 0 received, 100% packet loss, time 1010ms')
SEGMENTOS = {
    lab5.LABORATORIO_ID: {'v1': {'eth0': 'vendas'}, 'v2': {'eth0': 'vendas'}, 'f1': {'eth0': 'fin'}, 'f2': {'eth0': 'fin'},
                          'roteador': {'eth0': 'vendas', 'eth1': 'fin'}},
    lab6.LABORATORIO_ID: {'atendimento': {'eth0': 'a'}, 'vendas': {'eth0': 'v'}, 'financeiro': {'eth0': 'f'},
                          'roteador': {'eth0': 'a', 'eth1': 'v', 'eth2': 'f'}},
    lab7.LABORATORIO_ID: {'pca': {'eth0': 'a'}, 'r1': {'eth0': 'a', 'eth1': 'enlace'}, 'r2': {'eth1': 'enlace', 'eth0': 'b'},
                          'pcb': {'eth0': 'b'}},
}


class No:
    def __init__(self, rede, chave, info, inicial):
        self.rede, self.chave, self.roteador = rede, chave, info['tipo'] == 'roteador'
        self.ifs = {nome: list(inicial['interfaces'][nome]) for nome in info['interfaces']}
        self.rota = inicial['rota_padrao']
        self.estaticas = [(ipaddress.IPv4Network(r.split(' via ')[0]), r.split(' via ')[1]) for r in inicial.get('rotas', [])]

    def conectadas(self):
        return [(nome, ipaddress.IPv4Interface(e)) for nome, lista in self.ifs.items() for e in lista]

    def proximo(self, ip):
        """Interface e próximo salto para chegar a ip, como a tabela de rotas do kernel."""
        for nome, i in sorted(self.conectadas(), key=lambda x: -x[1].network.prefixlen):
            if ip in i.network:
                return nome, ip, i.ip
        for rede, via in sorted(self.estaticas, key=lambda x: -x[0].prefixlen):
            if ip in rede:
                saida = next(((n, i) for n, i in self.conectadas() if ipaddress.IPv4Address(via) in i.network), None)
                return (saida[0], ipaddress.IPv4Address(via), saida[1].ip) if saida else None
        if self.rota:
            for nome, i in self.conectadas():
                if ipaddress.IPv4Address(self.rota) in i.network:
                    return nome, ipaddress.IPv4Address(self.rota), i.ip
        return None

    def executar(self, cmd):
        p = cmd.split()
        if cmd == 'ip -j addr show':
            lista = [{'ifname': n, 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': e.split('/')[0], 'prefixlen': int(e.split('/')[1])} for e in l]}
                     for n, l in self.ifs.items()]
            lista.append({'ifname': 'ctrl0', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': '172.30.9.9', 'prefixlen': 24}]})
            return 0, json.dumps(lista)
        if cmd == 'ip -j -4 route show':
            tabela = [{'dst': 'default', 'gateway': self.rota, 'dev': 'eth0'}] if self.rota else []
            tabela += [{'dst': str(i.network), 'dev': n, 'prefsrc': str(i.ip)} for n, i in self.conectadas()]
            tabela += [{'dst': str(r), 'gateway': v, 'dev': next(n for n, i in self.conectadas() if ipaddress.IPv4Address(v) in i.network)}
                       for r, v in self.estaticas]
            tabela.append({'dst': '172.30.9.0/24', 'dev': 'ctrl0'})
            return 0, json.dumps(tabela)
        if cmd.startswith('ip addr show dev'):
            partes = [c.split()[-1] for c in cmd.split(';')]
            return 0, '\n'.join(f'{i + 2}: {n}: <BROADCAST,MULTICAST,UP,LOWER_UP>\n' + ''.join(f'    inet {e} scope global {n}\n' for e in self.ifs[n])
                                for i, n in enumerate(partes))
        if cmd == 'ip -4 route show':
            linhas = ['172.30.9.0/24 dev ctrl0 proto kernel scope link src 172.30.9.9']
            linhas += [f'{i.network} dev {n} proto kernel scope link src {i.ip}' for n, i in self.conectadas()]
            linhas += [f'{r} via {v} dev eth1' for r, v in self.estaticas]
            return 0, '\n'.join(([f'default via {self.rota} dev eth0'] if self.rota else []) + linhas)
        if p[:3] == ['ip', 'addr', 'add']:
            if p[3] in self.ifs[p[5]]:
                return 2, 'Error: ipv4: Address already assigned.'
            self.ifs[p[5]].append(p[3])
            return 0, ''
        if p[:3] == ['ip', 'addr', 'del']:
            if p[3] not in self.ifs[p[5]]:
                return 2, 'Error: ipv4: Address not found.'
            self.ifs[p[5]].remove(p[3])
            alcanca = lambda via: any(ipaddress.IPv4Address(via) in i.network for _, i in self.conectadas())  # noqa: E731
            if self.rota and not alcanca(self.rota):
                self.rota = None
            self.estaticas = [(r, v) for r, v in self.estaticas if alcanca(v)]
            return 0, ''
        if p[:3] == ['ip', 'route', 'add'] and p[3] != 'default':
            rede, via = ipaddress.IPv4Network(p[3]), p[5]
            if any(r == rede for r, _ in self.estaticas):
                return 2, 'RTNETLINK answers: File exists'
            if not any(ipaddress.IPv4Address(via) in i.network for _, i in self.conectadas()):
                return 2, 'Error: Nexthop has invalid gateway.'
            self.estaticas.append((rede, via))
            return 0, ''
        if p[:3] == ['ip', 'route', 'del'] and p[3] != 'default':
            antes = len(self.estaticas)
            self.estaticas = [(r, v) for r, v in self.estaticas if r != ipaddress.IPv4Network(p[3])]
            return (0, '') if len(self.estaticas) < antes else (2, 'RTNETLINK answers: No such process')
        if p[:4] == ['ip', 'route', 'add', 'default']:
            if self.rota:
                return 2, 'RTNETLINK answers: File exists'
            if not any(ipaddress.IPv4Address(p[5]) in i.network for _, i in self.conectadas()):
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
    def __init__(self, c):
        self.segmentos = SEGMENTOS[c.LABORATORIO_ID]
        self.nos = {chave: No(self, chave, info, c.INICIAL[chave]) for chave, info in c.NOS.items()}
        self.por_id = {c.NOS[chave]['no']: no for chave, no in self.nos.items()}

    def vizinho(self, no, interface, ip):
        segmento = self.segmentos[no.chave][interface]
        return next((o for o in self.nos.values() for n, i in o.conectadas()
                     if i.ip == ip and self.segmentos[o.chave][n] == segmento and o is not no), None)

    def alcanca(self, no, ip, saltos=3):
        rota = no.proximo(ip)
        if not rota:
            return None
        alvo = self.vizinho(no, rota[0], rota[1])
        if alvo is None:
            return None
        if any(i.ip == ip for _, i in alvo.conectadas()):
            return alvo
        return self.alcanca(alvo, ip, saltos - 1) if alvo.roteador and saltos else None

    def ping(self, no, destino):
        rota = no.proximo(destino)
        if not rota:
            return 2, 'ping: connect: Network unreachable'
        alvo = self.alcanca(no, destino)
        ok = alvo is not None and self.alcanca(alvo, rota[2]) is no
        return (0, '2 packets transmitted, 2 received, 0% packet loss') if ok else PERDA


class Engine:
    def __init__(self, c):
        self._lock = threading.RLock()
        self.lab = None
        self.rede = Rede(c)

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
        assert self._lock._is_owned() and timeout == 8
        return self.rede.por_id[node].executar(cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True

    def estender(self, uid):
        pass


def servico(c):
    salvos = []
    perfil = {lab5: PERFIL_LAB5, lab6: PERFIL_LAB6, lab7: PERFIL_LAB7}[c]
    s = ServicoRede(Engine(c), lambda uid, lab: (salvos.append(lab) or {'xp_concedido': 100}), cenario=c, perfil_tutor=perfil)
    return s, salvos


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(7, 'aluno', acao, extra)
    estado = act(s, 'status')
    return s.executar_acao(7, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
        'revisao': estado['missao']['revisao'], **extra})


def term(s, no, comando):
    return act(s, 'terminal', pc=no, comando=comando)['missao']


PLANO5 = {'rede': '192.168.50.64', 'gateway': '192.168.50.65', 'broadcast': '192.168.50.127'}
PLANO6 = {'atendimento-prefixo': '25', 'atendimento-rede': '192.168.80.0', 'vendas-prefixo': '/26',
          'vendas-rede': '192.168.80.128', 'financeiro-prefixo': '27', 'financeiro-rede': '192.168.80.192'}


def lab5_ate(s, etapa):
    act(s, 'iniciar')
    passos = [('plano', lambda: act(s, 'planejar', respostas=PLANO5)),
              ('roteador', lambda: term(s, 'roteador', 'ip addr add 192.168.50.65/26 dev eth1')),
              ('financeiro', lambda: [term(s, *p) for p in (
                  ('f1', 'ip addr add 192.168.50.66/26 dev eth0'), ('f1', 'ip route add default via 192.168.50.65'),
                  ('f2', 'ip addr add 192.168.50.67/26 dev eth0'), ('f2', 'ip route add default via 192.168.50.65'),
                  ('f1', 'ping 192.168.50.67'), ('f1', 'ping 192.168.50.10'))])]
    for nome, passo in passos:
        if nome == etapa:
            break
        passo()
    assert act(s, 'status')['missao']['proxima_etapa'] == etapa


def test_lab5_percurso_completo():
    s, salvos = servico(lab5)
    estado = act(s, 'iniciar')['missao']
    assert estado['proxima_etapa'] == 'plano' and estado['estados']['roteador']['interfaces'] == {'eth0': ['192.168.50.1/26'], 'eth1': []}
    m = term(s, 'v1', 'ping 192.168.50.1')
    assert m['testes']['v1']['192.168.50.1'] is True
    errado = act(s, 'planejar', respostas={**PLANO5, 'broadcast': '192.168.50.128'})
    assert errado['missao']['plano']['erros'] == ['broadcast'] and errado['missao']['proxima_etapa'] == 'plano'
    assert act(s, 'planejar', respostas=PLANO5)['missao']['proxima_etapa'] == 'roteador'
    m = term(s, 'roteador', 'ip addr add 192.168.50.65/26 dev eth1')
    assert m['proxima_etapa'] == 'financeiro' and m['terminal'][-1]['confirmacao'] == 'eth0: 192.168.50.1/26 · eth1: 192.168.50.65/26'
    m = term(s, 'roteador', 'ip route')
    assert '192.168.50.64/26 dev eth1' in m['terminal'][-1]['saida'] and 'ctrl0' not in m['terminal'][-1]['saida']
    with pytest.raises(ErroTerminal, match='já está em uso'):
        term(s, 'f1', 'ip addr add 192.168.50.70/26 dev eth0')  # ainda é o endereço do PC V2
    term(s, 'f1', 'ip addr add 192.168.50.66/26 dev eth0')
    term(s, 'f1', 'ip route add default via 192.168.50.65')
    term(s, 'f2', 'ip addr add 192.168.50.80/26 dev eth0')
    m = term(s, 'f1', 'ping 192.168.50.10')
    assert m['testes']['f1']['192.168.50.10'] is True and m['proxima_etapa'] == 'financeiro'
    m = term(s, 'f1', 'ping 192.168.50.80')
    # Mesmo segmento: o F2 responde sem rota padrão; a etapa ainda espera o F2 configurado por inteiro.
    assert m['testes']['f1']['192.168.50.80'] is True and m['proxima_etapa'] == 'financeiro'
    assert term(s, 'f2', 'ip route add default via 192.168.50.65')['proxima_etapa'] == 'chamado'
    m = term(s, 'v2', 'ping 192.168.50.10')
    assert 'Network unreachable' in m['terminal'][-1]['saida']
    term(s, 'v2', 'ip addr show')
    assert 'Isso mesmo' in act(s, 'diagnosticar', resposta='fora-do-bloco')['mensagem']
    term(s, 'v2', 'ip addr del 192.168.50.70/26 dev eth0')
    with pytest.raises(ErroTerminal, match='já está em uso'):
        term(s, 'v2', 'ip addr add 192.168.50.10/26 dev eth0')
    term(s, 'v2', 'ip addr add 192.168.50.20/26 dev eth0')
    term(s, 'v2', 'ip route add default via 192.168.50.1')
    assert term(s, 'v2', 'ping 192.168.50.66')['proxima_etapa'] == 'comprovar'
    final = act(s, 'validar')
    assert final['xp_concedido'] == 100 and final['conclusao']['registrada'] and salvos == [lab5.LABORATORIO_ID]


def test_lab5_cada_etapa_so_altera_o_que_e_dela():
    s, _ = servico(lab5)
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='plano'):
        term(s, 'roteador', 'ip addr add 192.168.50.65/26 dev eth1')
    act(s, 'planejar', respostas=PLANO5)
    with pytest.raises(ErroTerminal, match='só se altera: eth1'):
        term(s, 'roteador', 'ip addr del 192.168.50.1/26 dev eth0')
    with pytest.raises(ErroTerminal, match='só se altera: Roteador'):
        term(s, 'f1', 'ip addr add 192.168.50.66/26 dev eth0')
    with pytest.raises(ErroTerminal, match='rotas vêm das próprias interfaces'):
        term(s, 'roteador', 'ip route add default via 192.168.50.10')
    with pytest.raises(ErroTerminal, match='interfaces eth0, eth1'):
        term(s, 'roteador', 'ip addr add 192.168.50.65/26 dev eth2')
    with pytest.raises(ErroTerminal, match='rede ou de broadcast'):
        term(s, 'roteador', 'ip addr add 192.168.50.64/26 dev eth1')
    m = term(s, 'roteador', 'ip addr show')
    assert 'eth0' in m['terminal'][-1]['saida'] and 'eth1' in m['terminal'][-1]['saida']


def test_lab5_plano_recusa_campos_incompletos_e_nao_reconfere():
    s, _ = servico(lab5)
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='todos os campos'):
        act(s, 'planejar', respostas={'rede': '192.168.50.64'})
    act(s, 'planejar', respostas={k: f' {v} ' for k, v in PLANO5.items()})
    with pytest.raises(ErroTerminal, match='já foi conferido'):
        act(s, 'planejar', respostas=PLANO5)


def test_lab5_chamado_exige_observar_e_causa_antes_de_corrigir():
    s, _ = servico(lab5)
    lab5_ate(s, 'chamado')
    with pytest.raises(ErroTerminal, match='qual é a causa'):
        term(s, 'v2', 'ip addr del 192.168.50.70/26 dev eth0')
    with pytest.raises(ErroTerminal, match='ip addr show'):
        act(s, 'diagnosticar', resposta='fora-do-bloco')
    term(s, 'v2', 'ip a')
    assert 'Compare' in act(s, 'diagnosticar', resposta='cabo')['mensagem']
    assert act(s, 'status')['missao']['chamado']['correta'] is False


def test_lab5_conclusao_relê_tudo():
    s, _ = servico(lab5)
    lab5_ate(s, 'chamado')
    term(s, 'v2', 'ip a')
    act(s, 'diagnosticar', resposta='fora-do-bloco')
    for c in ('ip addr del 192.168.50.70/26 dev eth0', 'ip addr add 192.168.50.20/26 dev eth0',
              'ip route add default via 192.168.50.1', 'ping 192.168.50.66'):
        term(s, 'v2', c)
    s.engine.rede.nos['f2'].rota = None  # alteração fora do terminal do aluno
    with pytest.raises(ErroTerminal, match='PC F2'):
        act(s, 'validar')


@pytest.mark.parametrize('no, valor', [('v2', ['192.168.50.20/26']), ('roteador', ['192.168.50.65/26'])])
def test_lab5_iniciar_recusa_preparo_diferente(no, valor):
    s, _ = servico(lab5)
    s.engine.rede.nos[no].ifs['eth0' if no == 'v2' else 'eth1'] = valor
    with pytest.raises(ErroTerminal) as erro:
        act(s, 'iniciar')
    assert erro.value.status == 503


def test_lab6_percurso_completo_e_interface_trocada():
    s, salvos = servico(lab6)
    act(s, 'iniciar')
    m = act(s, 'planejar', respostas={**PLANO6, 'vendas-rede': '192.168.80.192', 'financeiro-rede': '192.168.80.128'})
    assert m['missao']['plano']['erros'] == ['vendas-rede', 'financeiro-rede']
    s2, _ = servico(lab6)
    act(s2, 'iniciar')
    assert act(s2, 'planejar', respostas=PLANO6)['missao']['proxima_etapa'] == 'roteador'
    term(s2, 'roteador', 'ip addr add 192.168.80.129/26 dev eth0')  # bloco do Vendas na interface do Atendimento
    term(s2, 'roteador', 'ip addr add 192.168.80.1/25 dev eth1')
    m = term(s2, 'roteador', 'ip addr add 192.168.80.193/27 dev eth2')
    assert m['proxima_etapa'] == 'roteador'
    for c in ('ip addr del 192.168.80.129/26 dev eth0', 'ip addr del 192.168.80.1/25 dev eth1',
              'ip addr add 192.168.80.1/25 dev eth0'):
        term(s2, 'roteador', c)
    assert term(s2, 'roteador', 'ip addr add 192.168.80.129/26 dev eth1')['proxima_etapa'] == 'pcs'
    for pc, ip, gw in (('atendimento', '192.168.80.10/25', '192.168.80.1'), ('vendas', '192.168.80.140/26', '192.168.80.129'),
                       ('financeiro', '192.168.80.200/27', '192.168.80.193')):
        term(s2, pc, f'ip addr add {ip} dev eth0')
        term(s2, pc, f'ip route add default via {gw}')
    term(s2, 'atendimento', 'ping 192.168.80.140')
    assert term(s2, 'atendimento', 'ping 192.168.80.200')['proxima_etapa'] == 'comprovar'
    final = act(s2, 'validar')
    assert final['xp_concedido'] == 100 and final['conclusao']['registrada']


def test_lab6_pc_fora_do_bloco_nao_conclui():
    s, _ = servico(lab6)
    act(s, 'iniciar')
    act(s, 'planejar', respostas=PLANO6)
    for c in ('ip addr add 192.168.80.1/25 dev eth0', 'ip addr add 192.168.80.129/26 dev eth1', 'ip addr add 192.168.80.193/27 dev eth2'):
        term(s, 'roteador', c)
    # /25 no PC Vendas: a rota pelo .129 é aceita (cabe em .128/25), mas o PC não está no bloco do setor.
    for pc, ip, gw in (('atendimento', '192.168.80.10/25', '192.168.80.1'), ('vendas', '192.168.80.140/25', '192.168.80.129'),
                       ('financeiro', '192.168.80.200/27', '192.168.80.193')):
        term(s, pc, f'ip addr add {ip} dev eth0')
        term(s, pc, f'ip route add default via {gw}')
    term(s, 'atendimento', 'ping 192.168.80.140')
    m = term(s, 'atendimento', 'ping 192.168.80.200')
    assert m['proxima_etapa'] == 'pcs'
    with pytest.raises(ErroTerminal, match='Conclua todas as etapas'):
        act(s, 'validar')


def test_blocos_so_saem_do_servidor_depois_do_plano():
    s, _ = servico(lab6)
    setores = act(s, 'iniciar')['missao']['setores']
    assert setores['vendas'] == {'nome': 'Vendas', 'interface': 'eth1', 'pedido': '50 computadores + gateway'}
    assert '192.168.80.128' not in str(act(s, 'status')['missao'])
    assert act(s, 'planejar', respostas=PLANO6)['missao']['setores']['vendas']['gateway'] == '192.168.80.129'
    s5, _ = servico(lab5)
    setores = act(s5, 'iniciar')['missao']['setores']
    assert setores['vendas']['rede'] == '192.168.50.0' and 'rede' not in setores['financeiro']


def test_campos_e_acoes_desconhecidas():
    s, _ = servico(lab5)
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal):
        act(s, 'terminal', pc='v1', comando='ip a', xp=100)
    with pytest.raises(ErroTerminal, match='equipamentos'):
        act(s, 'terminal', pc='switch', comando='ip a')
    with pytest.raises(ErroTerminal) as erro:
        s.executar_acao(7, 'aluno', 'aplicar', {})
    assert erro.value.status == 404


PLANO7 = {'r1-destino': '192.168.20.0/24', 'r1-via': '10.0.0.2', 'r2-destino': '192.168.10.0/24', 'r2-via': '10.0.0.1'}


def test_lab7_ida_sem_volta_falha_e_a_volta_fecha():
    s, salvos = servico(lab7)
    estado = act(s, 'iniciar')['missao']
    assert estado['proxima_etapa'] == 'chamado' and estado['estados']['r1']['rotas'] == []
    m = term(s, 'pca', 'ping 192.168.20.10')
    assert m['testes']['pca']['192.168.20.10'] is False
    assert term(s, 'pca', 'ping 10.0.0.1')['testes']['pca']['10.0.0.1'] is True
    with pytest.raises(ErroTerminal, match='qual é a causa'):
        term(s, 'r1', 'ip route add 192.168.20.0/24 via 10.0.0.2')
    with pytest.raises(ErroTerminal, match='ip route'):
        act(s, 'diagnosticar', resposta='sem-rota')
    with pytest.raises(ErroTerminal, match='depois do diagnóstico'):
        act(s, 'planejar', respostas=PLANO7)
    m = term(s, 'r1', 'ip route')
    assert '192.168.10.0/24 dev eth0' in m['terminal'][-1]['saida'] and '192.168.20' not in m['terminal'][-1]['saida']
    assert [x['testada'] for x in m['chamado']['suspeitas']] == [False, False, True]
    with pytest.raises(ErroTerminal, match='O PC A tem gateway.*O enlace'):
        act(s, 'diagnosticar', resposta='sem-rota')
    term(s, 'pca', 'ip route')
    assert term(s, 'r1', 'ping 10.0.0.2')['testes']['r1']['10.0.0.2'] is True
    assert 'o enlace funciona' in act(s, 'diagnosticar', resposta='enlace')['mensagem']
    assert 'Isso mesmo' in act(s, 'diagnosticar', resposta='sem-rota')['mensagem']
    with pytest.raises(ErroTerminal, match='plano'):
        term(s, 'r1', 'ip route add 192.168.20.0/24 via 10.0.0.2')
    erro = act(s, 'planejar', respostas={**PLANO7, 'r1-via': '192.168.20.1'})
    assert erro['missao']['plano']['erros'] == ['r1-via']
    assert act(s, 'planejar', respostas=PLANO7)['missao']['proxima_etapa'] == 'ida'
    with pytest.raises(ErroTerminal, match='só se altera: R1'):
        term(s, 'r2', 'ip route add 192.168.10.0/24 via 10.0.0.1')
    m = term(s, 'r1', 'ip route add 192.168.20.0/24 via 192.168.20.1')
    assert m['terminal'][-1]['saida'] == 'Error: Nexthop has invalid gateway.'
    m = term(s, 'r1', 'ip route add 192.168.20.0/24 via 10.0.0.2')
    assert m['terminal'][-1]['confirmacao'].endswith('rotas estáticas: 192.168.20.0/24 via 10.0.0.2')
    assert m['proxima_etapa'] == 'ida'  # ainda falta ver o ping falhar
    m = term(s, 'pca', 'ping 192.168.20.10')
    assert m['testes']['pca']['192.168.20.10'] is False and m['proxima_etapa'] == 'volta'
    m = term(s, 'r2', 'ip route add 192.168.10.0/24 via 10.0.0.1')
    assert m['proxima_etapa'] == 'volta' and m['testes']['pca'] == {}  # mudar um roteador apaga os testes de todos
    assert term(s, 'pca', 'ping 192.168.20.10')['proxima_etapa'] == 'comprovar'
    final = act(s, 'validar')
    assert final['xp_concedido'] == 100 and salvos == [lab7.LABORATORIO_ID]


def test_lab7_pcs_so_observam_e_rota_extra_impede_conclusao():
    s, _ = servico(lab7)
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal):
        term(s, 'r1', 'ip route add default via 10.0.0.2')
    term(s, 'r1', 'ip r')
    term(s, 'pca', 'ip r')
    term(s, 'r1', 'ping 10.0.0.2')
    act(s, 'diagnosticar', resposta='sem-rota')
    act(s, 'planejar', respostas=PLANO7)
    with pytest.raises(ErroTerminal, match='só se altera: R1'):
        term(s, 'pca', 'ip route del default')
    term(s, 'r1', 'ip route add 192.168.20.0/24 via 10.0.0.2')
    term(s, 'pca', 'ping 192.168.20.10')
    term(s, 'r2', 'ip route add 192.168.10.0/24 via 10.0.0.1')
    term(s, 'pca', 'ping 192.168.20.10')
    s.engine.rede.nos['r1'].estaticas.append((ipaddress.IPv4Network('192.168.30.0/24'), '10.0.0.2'))
    with pytest.raises(ErroTerminal, match='R1'):
        act(s, 'validar')
