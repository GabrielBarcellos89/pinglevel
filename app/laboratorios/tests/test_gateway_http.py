import importlib
import json

import pytest
from test_gateway_guiado import setup_service, baseline


def adapter():
    assert importlib.util.find_spec('laboratorios.api_gateway_guiado') is not None
    return importlib.import_module('laboratorios.api_gateway_guiado').despachar_gateway


def request(s, route='status', method=None, body=b'', user=None, origin=True, limit=True):
    return adapter()(s, {'id': 7, 'login': 'aluno'} if user is None else user,
        method or ('GET' if route == 'status' else 'POST'), '/api/gateway/' + route, body,
        origem_autorizada=origin, limitar=lambda key, count, sec: limit)


def test_adaptador_status_e_fluxo_real_com_409_retorna_contexto_autenticado():
    s, e, saved, error = setup_service()
    data, code = request(s)
    assert code == 200 and not data['ativo'] and e.created == 0
    data, code = request(s, 'iniciar', body=b'{}')
    assert code == 200 and data['ativo']
    payload = {'session_id': data['laboratorio']['session_id'], 'revisao': 10, 'local': 'sim', 'remota': 'nao'}
    data, code = request(s, 'prever', body=json.dumps(payload).encode())
    assert code == 409 and data['laboratorio']['session_id'] == e.lab.session_id
    assert data['sucesso'] is False
    data, code = request(s, 'prever', body=json.dumps({**payload, 'revisao': 0}).encode())
    assert code == 200 and data['missao']['previsao']['registrada']


@pytest.mark.parametrize('kw,code', [
    ({'user': {}}, 401), ({'user': {'id': True}}, 401), ({'user': {'id': -1}}, 401),
    ({'user': {'id': 7, 'troca_senha_obrigatoria': True}}, 403),
    ({'method': 'POST'}, 405), ({'route': 'iniciar', 'method': 'GET'}, 405),
    ({'route': 'iniciar', 'origin': False}, 403), ({'route': 'nao-existe'}, 404),
    ({'route': 'iniciar', 'limit': False}, 429),
    ({'route': 'iniciar', 'body': b'x' * 2049}, 413),
    ({'route': 'iniciar', 'body': '{}'}, 413),
    ({'route': 'iniciar', 'body': b'[]'}, 400),
    ({'route': 'iniciar', 'body': b'null'}, 400),
    ({'route': 'iniciar', 'body': b'{no'}, 400),
    ({'route': 'iniciar', 'body': b'\xff'}, 400),
    ({'route': 'iniciar', 'body': b'{"uid":9}'}, 400),
    ({'route': 'iniciar', 'body': b'{"concluido":true,"xp":999}'}, 400),
])
def test_adaptador_fronteiras_sem_criar_recurso(kw, code):
    s, e, saved, error = setup_service()
    data, result = request(s, **kw)
    assert result == code and data['sucesso'] is False
    assert not e.created and not e.commands and not saved


def test_adaptador_fluxo_completo_registra_uma_vez_e_get_recupera_conclusao():
    s, e, saved, error = setup_service()
    def post(action, **extra):
        state, status = request(s)
        payload = {} if action == 'iniciar' else {
            'session_id': state['laboratorio']['session_id'], 'revisao': state['missao']['revisao'], **extra}
        return request(s, action, body=json.dumps(payload).encode())
    assert post('iniciar')[1] == 200
    assert post('prever', local='nao', remota='sim')[1] == 200
    assert post('testar-antes')[1] == 200
    assert post('classificar', resposta='outra-rede')[1] == 200
    assert post('conferir')[1] == 200
    assert post('aplicar', gateway='192.168.10.1')[1] == 200
    assert post('testar-depois')[1] == 200
    assert post('interpretar', resposta='gateway-remoto')[1] == 200
    before, _ = request(s)
    token = json.dumps({'session_id': before['laboratorio']['session_id'], 'revisao': before['missao']['revisao']}).encode()
    result, code = post('validar')
    assert code == 200 and result['conclusao']['registrada'] and result['xp_concedido'] == 100
    again, code = request(s, 'validar', body=token)
    assert code == 200 and again['xp_concedido'] == 0 and saved == [(7, 'saindo-da-rede-local')]
    loaded, code = request(s)
    assert code == 200 and loaded['conclusao']['registrada'] and not loaded['ativo']


def test_adaptador_rate_namespace_e_identidade_exclusiva_do_usuario():
    s, e, saved, error = setup_service()
    calls = []
    f = adapter()
    data, code = f(s, {'id': 7, 'login': 'aluno'}, 'POST', '/api/gateway/iniciar', b'{}',
        origem_autorizada=True, limitar=lambda *args: calls.append(args) or True)
    assert code == 200 and calls == [('gateway:7', 30, 60)] and e.lab.usuario_id == 7
    data, code = request(s, user={'id': 9, 'login': 'outro'})
    assert code == 200 and not data['ativo'] and data['laboratorio'] is None
