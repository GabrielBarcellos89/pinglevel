"""Service tests exercise real parsing/validation; fake only replaces isolated-node I/O."""
import importlib
import json
import threading
from types import SimpleNamespace

import pytest

LAB = 'saindo-da-rede-local'
ADDR = 'ip -j addr show dev eth0'
ROUTE = 'ip -j -4 route show default'
GOOD = '2 packets transmitted, 2 received, 0% packet loss'
BAD = '2 packets transmitted, 0 received, 100% packet loss'


class Engine:
    def __init__(self):
        self._lock = threading.RLock()
        self.lab = None
        self.sequence = 0
        self.commands = []
        self.gateway = None
        self.events = []
        self.overrides = {}
        self.before_command = None
        self.cleanup = True
        self.created = 0
        self.extended = 0

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.sequence += 1
        self.created += 1
        self.lab = SimpleNamespace(usuario_id=uid, session_id=self.sequence, laboratorio_id=labid)
        self.gateway = None
        return self.lab

    def obter(self, uid):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def dados_temporais(self, lab):
        return {'tempo_restante': 900, 'extensoes_usadas': self.extended}

    def executar(self, uid, node, cmd, timeout=8):
        assert self._lock._is_owned(), 'engine lock required during I/O'
        assert timeout == 8
        self.commands.append((uid, self.lab.session_id, node, cmd))
        if self.before_command:
            self.before_command(self, cmd)
        if (node, cmd) in self.overrides:
            result = self.overrides[node, cmd]
            if isinstance(result, Exception):
                raise result
            return result
        if cmd == ADDR:
            ips = {1: '192.168.10.10', 2: '192.168.10.20', 4: '192.168.20.10', 5: '192.168.10.1'}
            return 0, json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': [
                {'family': 'inet6', 'local': 'fe80::1', 'prefixlen': 64, 'scope': 'link'},
                {'family': 'inet', 'local': ips[node], 'prefixlen': 24, 'scope': 'global'}]}])
        if cmd == 'ip -j addr show dev eth1' and node == 5:
            return 0, json.dumps([{'ifname': 'eth1', 'flags': ['UP'], 'addr_info': [
                {'family': 'inet', 'scope': 'global', 'local': '192.168.20.1', 'prefixlen': 24}]}])
        if cmd == ROUTE:
            return 0, json.dumps([{'dst': 'default', 'gateway': self.gateway, 'dev': 'eth0'}] if self.gateway else [])
        if cmd.startswith('ip -4 route replace default via '):
            self.gateway = cmd.split()[6]
            return 0, ''
        if cmd.startswith('ping -n -I eth0 -c 2 -W 1 '):
            success = cmd.endswith('192.168.10.20') or self.gateway == '192.168.10.1'
            return (0, GOOD) if success else (1, BAD)
        raise AssertionError(f'Unexpected command: {node} {cmd}')

    def encerrar_confirmado(self, uid, sid, motivo):
        assert self._lock._is_owned()
        assert self.lab.usuario_id == uid and self.lab.session_id == sid
        self.events.append('cleanup')
        if self.cleanup:
            self.lab = None
        return self.cleanup

    def estender(self, uid):
        assert self._lock._is_owned()
        self.extended += 1


def setup_service():
    assert importlib.util.find_spec('laboratorios.gateway_guiado') is not None
    m = importlib.import_module('laboratorios.gateway_guiado')
    e = Engine()
    saved = []

    def conclude(uid, labid):
        e.events.append('persist')
        saved.append((uid, labid))
        return {'xp_concedido': 100 if len(saved) == 1 else 0, 'primeira_conclusao': len(saved) == 1}

    def progress(uid):
        return {'laboratorios': [{'laboratorio_id': LAB, 'concluido': True, 'concluido_em': 123}] if saved else []}

    return m.ServicoGateway(e, conclude, progress), e, saved, m.ErroGateway


def act(s, action, **extra):
    if action in ('status', 'iniciar'):
        return s.executar_acao(7, 'aluno', action, extra)
    state = act(s, 'status')
    return s.executar_acao(7, 'aluno', action, {
        'session_id': state['laboratorio']['session_id'], 'revisao': state['missao']['revisao'], **extra})


def baseline(s):
    act(s, 'iniciar')
    act(s, 'prever', local='nao', remota='sim')
    act(s, 'testar-antes')
    return act(s, 'classificar', resposta='outra-rede')


def ready(s):
    baseline(s)
    act(s, 'aplicar', gateway='192.168.10.1')
    act(s, 'testar-depois')
    return act(s, 'interpretar', resposta='gateway-remoto')


@pytest.mark.parametrize('cleanup', [True, False])
def test_conclusao_persistida_antes_cleanup_idempotencia_e_recarga(cleanup):
    s, e, saved, error = setup_service()
    state = ready(s)
    assert state['missao']['concluido'] and not saved
    payload = {'session_id': state['laboratorio']['session_id'], 'revisao': state['missao']['revisao']}
    e.cleanup = cleanup
    result = s.executar_acao(7, 'aluno', 'validar', payload)
    assert result['conclusao']['registrada'] and result['xp_concedido'] == 100
    assert result['conclusao']['encerramento_pendente'] is (not cleanup)
    assert e.events[:2] == ['persist', 'cleanup'] and saved == [(7, LAB)]
    e.cleanup = True
    again = s.executar_acao(7, 'aluno', 'validar', payload)
    assert again['xp_concedido'] == 0 and len(saved) == 1 and not again['ativo']
    assert act(s, 'status')['conclusao']['registrada']
    new = type(s)(e, s.concluir, s.consultar_progresso)
    assert act(new, 'status')['missao']['concluido']
    state = act(new, 'iniciar')
    assert not state['missao']['concluido'] and state['conclusao'] is None
    assert state['missao']['antes']['registrado'] is False and e.created == 2


def test_interpretacao_exige_observacao_e_nao_aprova_alternativa_errada():
    s, e, saved, error = setup_service()
    baseline(s)
    with pytest.raises(error):
        act(s, 'interpretar', resposta='gateway-remoto')
    act(s, 'aplicar', gateway='192.168.10.1')
    act(s, 'testar-depois')
    state = act(s, 'interpretar', resposta='gateway-sempre')
    assert state['missao']['interpretacao']['correta'] is False
    with pytest.raises(error):
        act(s, 'validar')
    assert saved == []
    act(s, 'interpretar', resposta='gateway-remoto')
    e.gateway = '192.168.10.20'
    with pytest.raises(error):
        act(s, 'validar')
    assert saved == [] and e.lab is not None
    assert not act(s, 'status')['missao']['depois']['rota_confirmada']


def test_tentativa_host_local_e_saida_funcional_observadas_sem_conclusao_automatica():
    s, e, saved, error = setup_service()
    baseline(s)
    state = act(s, 'aplicar', gateway='192.168.10.20')
    assert state['missao']['gateway']['valor'] == '192.168.10.20'
    assert state['missao']['antes']['registrado']
    state = act(s, 'testar-depois')
    assert state['missao']['depois']['local'] is True
    assert state['missao']['depois']['remoto'] is False
    assert not state['missao']['concluido'] and not saved
    act(s, 'aplicar', gateway='192.168.10.1')
    state = act(s, 'conferir')
    assert state['missao']['conferencia']['ok']
    state = act(s, 'testar-depois')
    assert state['missao']['depois']['rota_confirmada'] is True
    assert state['missao']['depois']['remoto'] is True
    assert state['missao']['proxima_etapa'] == 'comprovar' and not saved
    old = state['missao']['revisao']
    state = act(s, 'aplicar', gateway='192.168.10.25')
    assert state['missao']['revisao'] > old
    assert not state['missao']['depois']['registrado']
    assert state['missao']['conferencia']['ok']  # Aplicação agora inclui releitura real da rota.
    assert not state['missao']['interpretacao']['correta']
    assert state['missao']['antes']['registrado']


@pytest.mark.parametrize('action', ['estender', 'encerrar'])
def test_operacoes_de_ciclo_de_vida_respeitam_sessao_e_lock(action):
    s, e, saved, error = setup_service()
    act(s, 'iniciar')
    old = {'session_id': e.lab.session_id, 'revisao': 0}
    state = act(s, action)
    if action == 'encerrar':
        assert not state['ativo'] and e.events == ['cleanup']
    else:
        assert e.extended == 1 and state['missao']['revisao'] == 1
    with pytest.raises(error) as caught:
        s.executar_acao(7, 'aluno', action, old)
    assert caught.value.status == 409
    assert saved == []


def test_baseline_com_erro_ssh_nao_pode_virar_falha_remota_pedagogica():
    s, e, saved, error = setup_service()
    act(s, 'iniciar')
    act(s, 'prever', local='sim', remota='nao')
    e.overrides[1, 'ping -n -I eth0 -c 2 -W 1 192.168.20.10'] = (255, 'SSH disconnected')
    with pytest.raises(error) as caught:
        act(s, 'testar-antes')
    assert caught.value.status == 503
    assert not act(s, 'status')['missao']['antes']['registrado']


@pytest.mark.parametrize('node,ip', [(1, '172.30.7.1'), (2, '172.30.7.2'), (4, '192.168.10.25')])
def test_enderecos_reais_isolados_e_redes_distintas_obrigatorios(node, ip):
    s, e, saved, error = setup_service()
    baseline(s)
    e.overrides[node, ADDR] = (0, json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': [
        {'family': 'inet', 'scope': 'global', 'local': ip, 'prefixlen': 24}]}]))
    with pytest.raises(error):
        act(s, 'testar-antes')
    assert not act(s, 'status')['missao']['antes']['registrado']
    assert not saved


def test_repetir_antes_com_gateway_nao_apaga_baseline_original():
    s, e, saved, error = setup_service()
    baseline(s)
    act(s, 'aplicar', gateway='192.168.10.1')
    previous = act(s, 'status')['missao']['antes']
    with pytest.raises(error):
        act(s, 'testar-antes')
    assert act(s, 'status')['missao']['antes'] == previous


def test_status_inicio_previsao_errada_e_baseline_observado():
    s, e, saved, error = setup_service()
    state = act(s, 'status')
    assert not state['ativo'] and e.created == 0 and e.commands == []
    state = act(s, 'iniciar')
    assert state['ativo'] and state['missao']['revisao'] == 0
    assert act(s, 'iniciar')['laboratorio'] == state['laboratorio'] and e.created == 1
    with pytest.raises(error, match='previs'):
        act(s, 'testar-antes')
    state = act(s, 'prever', local='nao', remota='sim')
    assert state['missao']['previsao'] == {'local': 'nao', 'remota': 'sim', 'registrada': True}
    assert state['missao']['antes']['local'] is None
    state = act(s, 'testar-antes')
    assert state['missao']['antes']['local'] is True
    assert state['missao']['antes']['remoto'] is False
    assert state['missao']['antes']['registrado'] is True
    assert state['missao']['proxima_etapa'] == 'rede'
    assert len(state['missao']['antes']['detalhes']) == 2 and not saved
    assert all(' -I eth0 ' in cmd for _, _, _, cmd in e.commands if cmd.startswith('ping'))
