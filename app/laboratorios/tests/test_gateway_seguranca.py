import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_gateway_guiado import setup_service, act, baseline, ready, ADDR, ROUTE, LAB, GOOD, BAD


def address(ip='192.168.10.11', prefix=24):
    return json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': [
        {'family': 'inet', 'scope': 'global', 'local': ip, 'prefixlen': prefix}]}])


def test_interfaces_roteador_somente_apos_consulta_explicita_sem_preencher_campo():
    s, e, saved, error = setup_service()
    baseline(s)
    assert not any(n == 5 for _, _, n, _ in e.commands)
    state = act(s, 'conferir')
    router = next(n for n in state['missao']['nos'] if n['id'] == 5)
    assert router['interfaces'] == [
        {'interface': 'eth0', 'ip': '192.168.10.1', 'prefixo': 24},
        {'interface': 'eth1', 'ip': '192.168.20.1', 'prefixo': 24}]
    assert state['missao']['gateway']['valor'] == '' and not state['missao']['concluido']


def test_dado_da_interface_alterado_invalida_baseline_e_impede_persistencia():
    s, e, saved, error = setup_service()
    ready(s)
    e.overrides[1, ADDR] = (0, address())
    with pytest.raises(error):
        act(s, 'validar')
    state = act(s, 'status')['missao']
    assert not state['concluido'] and not state['antes']['registrado']
    assert not state['depois']['registrado'] and not saved


def test_rota_criada_durante_baseline_nao_evidencia_ausencia_de_gateway():
    s, e, saved, error = setup_service()
    act(s, 'iniciar')
    act(s, 'prever', local='sim', remota='nao')
    def mutate(engine, cmd):
        if cmd.startswith('ping'):
            engine.gateway = '192.168.10.20'
    e.before_command = mutate
    with pytest.raises(error):
        act(s, 'testar-antes')
    assert not act(s, 'status')['missao']['antes']['registrado']


@pytest.mark.parametrize('result', [(0, 'ok'), (1, 'SSH not available'), (0, BAD)])
def test_ping_malformado_ou_inconsistente_nao_compõe_baseline(result):
    s, e, saved, error = setup_service()
    act(s, 'iniciar')
    act(s, 'prever', local='sim', remota='nao')
    e.overrides[1, 'ping -n -I eth0 -c 2 -W 1 192.168.20.10'] = result
    with pytest.raises(error):
        act(s, 'testar-antes')
    assert not act(s, 'status')['missao']['antes']['registrado']


@pytest.mark.parametrize('gateway', ['', None, 123, True, '192.168.010.1', ' 192.168.10.1',
    '192.168.10.1 ', '192.168.10.1;id', '$(id)', '192.168.10.0', '192.168.10.255',
    '192.168.10.10', '192.168.20.1', '172.30.7.5', '127.0.0.1', '::1', '8.8.8.8'])
def test_gateway_invalido_nao_gera_comando_de_escrita(gateway):
    s, e, saved, error = setup_service()
    baseline(s)
    old = act(s, 'status')['missao']['revisao']
    with pytest.raises(error) as caught:
        act(s, 'aplicar', gateway=gateway)
    assert caught.value.status == 400
    assert not any(cmd.startswith('ip -4 route replace') for _, _, _, cmd in e.commands)
    assert act(s, 'status')['missao']['revisao'] == old


@pytest.mark.parametrize('action', ['aplicar', 'testar-antes', 'testar-depois', 'conferir', 'validar', 'encerrar', 'estender'])
def test_aba_antiga_nao_altera_nova_sessao(action):
    s, e, saved, error = setup_service()
    state = baseline(s)
    payload = {'session_id': e.lab.session_id, 'revisao': state['missao']['revisao']}
    if action == 'aplicar':
        payload['gateway'] = '192.168.10.1'
    act(s, 'encerrar')
    act(s, 'iniciar')
    count = len(e.commands)
    with pytest.raises(error) as caught:
        s.executar_acao(7, 'aluno', action, payload)
    assert caught.value.status == 409 and len(e.commands) == count and e.lab.session_id == 2


def test_duas_abas_serializadas_uma_revisao_executa_apenas_uma_escrita():
    s, e, saved, error = setup_service()
    state = baseline(s)
    payload = {'session_id': e.lab.session_id, 'revisao': state['missao']['revisao'], 'gateway': '192.168.10.1'}
    barrier = threading.Barrier(2)
    def run():
        barrier.wait(timeout=3)
        try:
            s.executar_acao(7, 'aluno', 'aplicar', payload)
            return 200
        except error as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == [200, 409]
    assert len([cmd for _, _, _, cmd in e.commands if cmd.startswith('ip -4 route replace')]) == 1


@pytest.mark.parametrize('mode', ['expire', 'replace', 'other'])
def test_sessao_trocada_durante_comando_impede_proximos_comandos(mode):
    s, e, saved, error = setup_service()
    ready(s)
    def mutate(engine, cmd):
        if mode == 'expire':
            engine.lab = None
        else:
            engine.criar(7, 'aluno', LAB if mode == 'replace' else 'primeira-lan')
    e.before_command = mutate
    count = len(e.commands)
    with pytest.raises(error) as caught:
        act(s, 'validar')
    assert caught.value.status == 409 and len(e.commands) == count + 1
    assert saved == [] and e.events == []


@pytest.mark.parametrize('action', ['iniciar', 'aplicar', 'encerrar', 'estender', 'validar'])
def test_outro_lab_permanece_intocado(action):
    s, e, saved, error = setup_service()
    e.criar(7, 'aluno', 'primeira-lan')
    other = e.lab
    assert act(s, 'status')['conflito']['laboratorio_id'] == 'primeira-lan'
    with pytest.raises(error) as caught:
        s.executar_acao(7, 'aluno', action, {} if action == 'iniciar' else {'session_id': other.session_id, 'revisao': 0})
    assert caught.value.status == 409 and e.lab is other
    assert not e.commands and not e.events and e.extended == 0


@pytest.mark.parametrize('cmd,value', [(ADDR, (0, 'bad-json')), (ADDR, (0, '[]')),
    (ADDR, (0, address(prefix=True))), (ADDR, (0, address(ip='192.168.10.11;id'))),
    (ADDR, (0, '[null]')), (ADDR, (0, 'x' * 32001)), (ADDR, (2, 'down')),
    (ROUTE, (0, '{}')), (ROUTE, (0, '[null]')), (ROUTE, (1, 'not available')),
    (ROUTE, (0, '[{"dst":"default","dev":"eth0","gateway":"invalid"}]')),
    (ADDR, OSError('SSH unavailable'))])
def test_erro_no_no_ou_json_nao_aprova_evidencias(cmd, value):
    s, e, saved, error = setup_service()
    ready(s)
    e.overrides[1, cmd] = value
    with pytest.raises(error) as caught:
        act(s, 'validar')
    assert caught.value.status == 503
    assert not act(s, 'status')['missao']['depois']['registrado'] and not saved


@pytest.mark.parametrize('result', [(1, BAD), (0, GOOD)])
def test_baseline_nao_e_aprovado_quando_comparacao_nao_corresponde(result):
    s, e, saved, error = setup_service()
    act(s, 'iniciar')
    act(s, 'prever', local='sim', remota='nao')
    target = '192.168.10.20' if result[0] == 1 else '192.168.20.10'
    e.overrides[1, f'ping -n -I eth0 -c 2 -W 1 {target}'] = result
    state = act(s, 'testar-antes')
    assert next(et for et in state['missao']['etapas'] if et['id'] == 'local')['concluida'] is (result[0] == 0)
    assert not state['missao']['concluido']
    with pytest.raises(error):
        act(s, 'aplicar', gateway='192.168.10.1')
    assert not saved


def test_enderecos_dinamicos_sao_canonizados_sem_gabarito_de_gateway():
    s, e, saved, error = setup_service()
    e.overrides[1, ADDR] = (0, address('10.22.0.10'))
    e.overrides[2, ADDR] = (0, address('10.22.0.20'))
    e.overrides[4, ADDR] = (0, address('10.23.0.10'))
    e.overrides[1, 'ping -n -I eth0 -c 2 -W 1 10.22.0.20'] = (0, GOOD)
    e.overrides[1, 'ping -n -I eth0 -c 2 -W 1 10.23.0.10'] = (1, BAD)
    state = baseline(s)
    assert next(n for n in state['missao']['nos'] if n['id'] == 1)['ip'] == '10.22.0.10'
    act(s, 'aplicar', gateway='10.22.0.77')
    assert e.gateway == '10.22.0.77'
    assert not any(n == 5 for _, _, n, _ in e.commands)


def test_network_unreachable_do_ping_e_falha_observavel_nao_erro_ssh():
    s, e, saved, error = setup_service()
    e.overrides[1, 'ping -n -I eth0 -c 2 -W 1 192.168.20.10'] = (2, 'ping: connect: Network is unreachable')
    state = baseline(s)
    assert state['missao']['antes']['registrado'] and state['missao']['antes']['remoto'] is False


def test_treino_repetido_usa_callback_idempotente_sem_recompensa_nova():
    s, e, saved, error = setup_service()
    ready(s)
    assert act(s, 'validar')['xp_concedido'] == 100
    ready(s)
    assert act(s, 'validar')['xp_concedido'] == 0
    assert e.created == 2 and saved == [(7, LAB), (7, LAB)]


def test_encerramento_positivo_sem_remocao_permanece_pendente():
    s, e, saved, error = setup_service()
    ready(s)
    e.encerrar_confirmado = lambda *args: True
    result = act(s, 'validar')
    assert result['conclusao']['encerramento_pendente'] is True
    assert result['ativo'] and saved == [(7, LAB)]
    assert 'pendente' in result['mensagem']


def test_callback_sem_confirmacao_nao_anuncia_conclusao_nem_remove_ambiente():
    s, e, saved, error = setup_service()
    ready(s)
    s.concluir = lambda *args: None
    with pytest.raises(error) as caught:
        act(s, 'validar')
    assert caught.value.status == 503
    assert act(s, 'status')['conclusao'] is None and e.lab is not None


@pytest.mark.parametrize('route', [
    [{'dst': 'default', 'dev': 'eth0', 'gateway': '192.168.10.1', 'nexthops': [{'dev': 'ctrl0'}]}],
    [{'dst': 'default', 'dev': 'eth0', 'gateway': '192.168.10.1', 'type': 'blackhole'}],
    [{'dst': 'default', 'dev': 'eth0', 'gateway': '192.168.10.1'},
     {'dst': 'default', 'dev': 'eth0', 'gateway': '192.168.10.20'}],
])
def test_rota_ambigua_ou_sem_encaminhamento_nao_confirma_gateway(route):
    s, e, saved, error = setup_service()
    ready(s)
    e.overrides[1, ROUTE] = (0, json.dumps(route))
    with pytest.raises(error) as caught:
        act(s, 'validar')
    assert caught.value.status == 503 and not saved


def test_falha_persistencia_preserva_recurso_permite_repetir_sem_refazer_rede():
    s, e, saved, error = setup_service()
    ready(s)
    original = s.concluir
    def fail(*args):
        raise OSError('database unavailable')
    s.concluir = fail
    with pytest.raises(error) as caught:
        act(s, 'validar')
    assert caught.value.status == 503 and e.lab is not None and not e.events
    s.concluir = original
    assert act(s, 'validar')['conclusao']['registrada']
