"""Entrada simples digitada pelo aluno, I/O real encapsulado pelo serviço existente."""
import copy
import json
import pytest
from test_gateway_guiado import setup_service, act
from laboratorios.api_gateway_guiado import despachar_gateway

LOCAL='ping 192.168.10.20'
REMOTO='ping 192.168.20.10'


def test_ping_digitado_executa_teste_local_real_sem_ping_remoto():
    s,e,saved,error=setup_service();act(s,'iniciar')
    state=act(s,'terminal',comando=LOCAL,local='nao')
    assert state['missao']['antes']['local'] is True
    assert state['missao']['antes']['remoto'] is None
    item=state['missao']['terminal'][-1]
    assert item['digitado']==LOCAL and item['alcance'] is True
    assert item['executado']=='ping -n -I eth0 -c 2 -W 1 192.168.10.20'
    assert item['saida']=='2 packets transmitted, 2 received, 0% packet loss'
    assert [cmd for *_,cmd in e.commands if cmd.startswith('ping')]==[item['executado']]
    assert not saved


@pytest.mark.parametrize('comando',[
    '',None,7,[],{},'x'*81,'ls','ping','ping -c 2 192.168.10.20',
    '$ ping 192.168.10.20','ping 192.168.10.20; id',
    'ping 192.168.10.20 && id','ping $(id)','ping `id`',
    'ping 192.168.10.20\nid','ping 192.168.10.20\n',
    'ping 192.168.10.20\r','ping 192.168.10.20\x00',
    'ping 8.8.8.8','ping 172.30.1.1','ping exemplo.com',
    'ping 192.168.10.10','ping 192.168.10.1','ping 192.168.010.020',
])
def test_comando_nao_autorizado_nao_chega_ao_no(comando):
    s,e,saved,error=setup_service();act(s,'iniciar')
    with pytest.raises(error) as exc:act(s,'terminal',comando=comando,local='sim')
    assert exc.value.status==400
    assert not e.commands and not saved and not act(s,'status')['missao']['terminal']


def test_ping_remoto_exige_observacao_local_e_previsao_local_e_obrigatoria():
    s,e,saved,error=setup_service();act(s,'iniciar')
    with pytest.raises(error):act(s,'terminal',comando=LOCAL)
    with pytest.raises(error):act(s,'terminal',comando=REMOTO)
    assert not e.commands and not saved


def test_percurso_com_terminal_ate_conclusao_preserva_revalidacao_xp_e_consulta():
    s,e,saved,error=setup_service();act(s,'iniciar')
    act(s,'terminal',comando=LOCAL,local='sim')
    before=act(s,'terminal',comando=REMOTO)
    assert before['missao']['terminal'][-1]['alcance'] is False
    act(s,'classificar',resposta='outra-rede');act(s,'aplicar',gateway='192.168.10.1')
    after=act(s,'terminal',comando=REMOTO)
    assert after['missao']['terminal'][-1]['alcance'] is True
    assert after['missao']['depois']['local'] is True
    assert after['missao']['depois']['rota_confirmada'] is True
    act(s,'interpretar',resposta='gateway-remoto')
    history=copy.deepcopy(act(s,'status')['missao']['terminal'])
    assert act(s,'consultar')['missao']['terminal']==history
    state=act(s,'validar')
    assert state['xp_concedido']==100 and saved==[(7,'saindo-da-rede-local')]
    assert not state['ativo'] and state['conclusao']['registrada']


def test_historico_limitado_nao_altera_revisao_no_status_ou_consulta():
    s,e,saved,error=setup_service();act(s,'iniciar')
    for _ in range(10):state=act(s,'terminal',comando='  ping\t192.168.10.20  ',local='sim')
    assert len(state['missao']['terminal'])==8
    before=copy.deepcopy(state['missao']['terminal']);rev=state['missao']['revisao']
    state['missao']['terminal'].clear()
    assert act(s,'status')['missao']['terminal']==before
    assert act(s,'consultar')['missao']['revisao']==rev
    assert not saved


def test_terminal_nao_aceita_sessao_ou_revisao_antigas():
    s,e,saved,error=setup_service();act(s,'iniciar')
    with pytest.raises(error) as exc:
        s.executar_acao(7,'aluno','terminal',{'session_id':999,'revisao':0,'comando':LOCAL,'local':'sim'})
    assert exc.value.status==409 and not e.commands
    act(s,'terminal',comando=LOCAL,local='sim')
    e.commands.clear()
    with pytest.raises(error) as exc:
        s.executar_acao(7,'aluno','terminal',{'session_id':e.lab.session_id,'revisao':0,'comando':LOCAL,'local':'sim'})
    assert exc.value.status==409 and not e.commands


def test_falha_de_execucao_nao_cria_historico_ou_resultado_simulado():
    s,e,saved,error=setup_service();act(s,'iniciar')
    e.overrides[1,'ping -n -I eth0 -c 2 -W 1 192.168.10.20']=(255,'SSH disconnected')
    with pytest.raises(error) as exc:act(s,'terminal',comando=LOCAL,local='sim')
    assert exc.value.status==503
    state=act(s,'status')
    assert not state['missao']['terminal'] and not state['missao']['antes']['registrado'] and not saved


@pytest.mark.parametrize('user,origin,status',[(None,True,401),({'id':7},False,403)])
def test_endpoint_terminal_preserva_autenticacao_e_origem(user,origin,status):
    s,e,saved,error=setup_service();act(s,'iniciar')
    _,code=despachar_gateway(s,user,'POST','/api/gateway/terminal',json.dumps({'session_id':1,'revisao':0,'comando':LOCAL,'local':'sim'}).encode(),origem_autorizada=origin,limitar=lambda *args:True)
    assert code==status and not e.commands and not saved
