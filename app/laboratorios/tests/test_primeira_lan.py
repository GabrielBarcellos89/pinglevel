"""Lab 2 (versão 2) com rede simulada: plano da rede do PC 1, PC 2 configurado pelo terminal e o chamado do PC 3
(prefixo /28). O alcance do ping depende de endereço e prefixo, como numa LAN real sem roteador."""
import ipaddress
import json
import threading
from copy import deepcopy
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import primeira_lan as lab2
from laboratorios.terminal_guiado import ErroTerminal
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import PERFIL_LAB2

PERDA = (1, '--- ping statistics ---\n2 packets transmitted, 0 received, 100% packet loss, time 1010ms')
OK = (0, '2 packets transmitted, 2 received, 0% packet loss')
SEM_ROTA = (2, 'ping: connect: Network is unreachable')


class Sala:
    def __init__(self):
        self.nos = {n: deepcopy(lab2.INICIAL[n]) for n in lab2.NOS}

    def _iface(self, no):
        e = self.nos[no]['interfaces']['eth0']
        return ipaddress.IPv4Interface(e[0]) if e else None

    def executar(self, no, cmd):
        e = self.nos[no]
        if cmd == 'ip -j addr show':
            info = [{'family': 'inet', 'local': a.split('/')[0], 'prefixlen': int(a.split('/')[1])} for a in e['interfaces']['eth0']]
            return 0, json.dumps([{'ifname': 'eth0@if9', 'flags': ['UP'], 'addr_info': info}])
        if cmd == 'ip -j -4 route show':
            return 0, json.dumps([])
        if cmd.startswith('ip addr show'):
            return 0, '2: eth0@if9: <BROADCAST,MULTICAST,UP,LOWER_UP>\n' + ''.join(f'    inet {a} scope global eth0\n' for a in e['interfaces']['eth0'])
        p = cmd.split()
        if p[:2] == ['ip', 'addr'] and p[2] in ('add', 'del'):
            lista = e['interfaces']['eth0']
            if p[2] == 'add':
                lista.append(p[3])
            elif p[3] in lista:
                lista.remove(p[3])
            else:
                return 2, 'RTNETLINK answers: Cannot assign requested address'
            return 0, ''
        if p[0] == 'ping':
            origem, alvo = self._iface(no), ipaddress.IPv4Address(p[-1])
            if origem is None or alvo not in origem.network:
                return SEM_ROTA
            destino = next((self._iface(n) for n in self.nos if self._iface(n) and self._iface(n).ip == alvo), None)
            return OK if destino and origem.ip in destino.network else PERDA
        raise AssertionError(f'comando inesperado: {cmd}')


class Engine:
    def __init__(self, rede):
        self._lock = threading.RLock()
        self.lab = None
        self.rede = rede
        self.por_id = {info['no']: chave for chave, info in lab2.NOS.items()}

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.lab = SimpleNamespace(usuario_id=uid, session_id=8, laboratorio_id=labid)
        return self.lab

    def obter(self, uid):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def dados_temporais(self, lab):
        return {'segundos_restantes': 900}

    def executar(self, uid, node, cmd, timeout=8):
        assert self._lock._is_owned()
        return self.rede.executar(self.por_id[node], cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True


def servico():
    salvos = []
    s = ServicoRede(Engine(Sala()), lambda uid, lab: (salvos.append(lab) or {'xp_concedido': 100}),
                    cenario=lab2, perfil_tutor=PERFIL_LAB2)
    return s, salvos


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(1, 'aluno', acao, extra)
    estado = s.executar_acao(1, 'aluno', 'status', {})
    return s.executar_acao(1, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
                                              'revisao': estado['missao']['revisao'], **extra})


def term(s, no, comando):
    return act(s, 'terminal', comando=comando, pc=no)['missao']


PLANO = {'rede': '192.168.10.0', 'prefixo': '/24', 'mascara': '255.255.255.0'}


def test_rede_so_aparece_depois_do_plano_e_plano_exige_olhar_o_pc1():
    s, _ = servico()
    missao = act(s, 'iniciar')['missao']
    assert missao['rede'] is None and missao['proxima_etapa'] == 'plano'
    assert 'rede' not in missao['setores']['sala']
    with pytest.raises(ErroTerminal, match='descubra o endereço do PC 1'):
        act(s, 'planejar', respostas=PLANO)
    term(s, 'pc1', 'ip addr show')
    with pytest.raises(ErroTerminal, match='complete o plano'):
        term(s, 'pc2', 'ip addr add 192.168.10.20/24 dev eth0')
    errado = act(s, 'planejar', respostas={**PLANO, 'rede': '192.168.10.1', 'mascara': '255.255.0.0'})
    # A dica explica o erro comum (um endereço de host no lugar do da rede) sem dizer o valor esperado.
    assert '192.168.10.1 é um endereço de host' in errado['mensagem'] and 'cada 8 bits' in errado['mensagem']
    assert '192.168.10.0' not in errado['mensagem']
    missao = act(s, 'planejar', respostas=PLANO)['missao']
    assert missao['plano']['correto'] and missao['rede'] == '192.168.10.0/24' and missao['proxima_etapa'] == 'pc2'


def test_percurso_completo_com_o_chamado_do_prefixo():
    s, salvos = servico()
    act(s, 'iniciar')
    term(s, 'pc1', 'ip addr show')
    act(s, 'planejar', respostas=PLANO)
    with pytest.raises(ErroTerminal, match='já está em uso|em uso'):
        term(s, 'pc2', 'ip addr add 192.168.10.10/24 dev eth0')
    term(s, 'pc2', 'ip addr add 192.168.10.20/24 dev eth0')
    missao = term(s, 'pc2', 'ping 192.168.10.10')
    assert missao['proxima_etapa'] == 'chamado'
    # O chamado: com /28, o PC 1 fica "fora da rede" do PC 3.
    missao = term(s, 'pc3', 'ping 192.168.10.10')
    assert missao['testes']['pc3']['192.168.10.10'] is False
    with pytest.raises(ErroTerminal, match='causa'):
        term(s, 'pc3', 'ip addr del 192.168.10.40/28 dev eth0')
    with pytest.raises(ErroTerminal, match='ip addr show'):
        act(s, 'diagnosticar', resposta='prefixo')
    term(s, 'pc3', 'ip addr show')
    assert act(s, 'diagnosticar', resposta='cabo')['missao']['chamado']['correta'] is False
    act(s, 'diagnosticar', resposta='prefixo')
    term(s, 'pc3', 'ip addr del 192.168.10.40/28 dev eth0')
    term(s, 'pc3', 'ip addr add 192.168.10.40/24 dev eth0')
    missao = term(s, 'pc3', 'ping 192.168.10.10')
    assert missao['chamado']['progresso'] == {'causa': True, 'configuracao': True, 'teste': True}
    assert missao['proxima_etapa'] == 'comprovar'
    resultado = act(s, 'validar')
    assert resultado['conclusao']['registrada'] and salvos


def test_pc2_fora_da_rede_nao_conclui_a_etapa():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'pc1', 'ip addr show')
    act(s, 'planejar', respostas=PLANO)
    term(s, 'pc2', 'ip addr add 192.168.11.20/24 dev eth0')
    assert term(s, 'pc2', 'ping 192.168.10.10')['proxima_etapa'] == 'pc2'
    term(s, 'pc2', 'ip addr del 192.168.11.20/24 dev eth0')
    with pytest.raises(ErroTerminal, match='broadcast'):
        term(s, 'pc2', 'ip addr add 192.168.10.255/24 dev eth0')


def test_tutor_nao_entrega_a_rede_nem_a_causa():
    aberto = {'chamado': {'correta': False}, 'plano': {'correto': False}}
    assert PERFIL_LAB2.bloquear('A rede é 192.168.10.0.', 'plano', 2, aberto, 'qual a rede?', {}) == 'filtro'
    assert PERFIL_LAB2.bloquear('A máscara é 255.255.255.0.', 'plano', 2, aberto, 'e a máscara?', {}) == 'filtro'
    conferido = {'chamado': {'correta': False}, 'plano': {'correto': True}}
    assert PERFIL_LAB2.bloquear('O PC 3 está com /28.', 'chamado', 2, conferido, 'o que houve?', {}) == 'filtro'
    assert PERFIL_LAB2.bloquear('O prefixo do PC 3 está errado.', 'chamado', 2, conferido, 'o que houve?', {}) == 'filtro'
    assert PERFIL_LAB2.bloquear('Compare o número depois da barra nos dois PCs.', 'chamado', 2, conferido, 'e agora?', {}) is None
    assert PERFIL_LAB2.bloquear('Use ip addr add 192.168.10.50/24 dev eth0.', 'pc2', 2, conferido, 'como?', {}) == 'filtro'
