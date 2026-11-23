"""Fluxo aprovado: normal local, classificação, gateway, evidência e interpretação."""
import copy
import pytest
from test_gateway_guiado import setup_service, act, GOOD, BAD
from laboratorios.api_gateway_guiado import despachar_gateway


def iniciar_local(s, previsao='nao'):
    act(s, 'iniciar')
    return act(s, 'testar-local', local=previsao)


def test_previsao_errada_nao_penaliza_e_teste_inicial_nao_executa_ping_remoto():
    s,e,saved,error=setup_service()
    state=iniciar_local(s)
    assert state['missao']['antes']['local'] is True
    assert state['missao']['antes']['remoto'] is None
    assert state['missao']['proxima_etapa']=='rede'
    assert state['missao']['previsao']['local']=='nao'
    assert [cmd for *_,cmd in e.commands if cmd.startswith('ping')]==['ping -n -I eth0 -c 2 -W 1 192.168.10.20']
    assert not saved


def test_percurso_completo_sem_teste_remoto_inicial_preserva_id_e_xp():
    s,e,saved,error=setup_service();iniciar_local(s)
    wrong=act(s,'classificar',resposta='mesma-rede')
    assert not wrong['missao']['classificacao']['correta']
    with pytest.raises(error):act(s,'aplicar',gateway='192.168.10.1')
    act(s,'classificar',resposta='outra-rede')
    state=act(s,'aplicar',gateway='192.168.10.1')
    assert state['missao']['conferencia']['ok']
    assert not state['missao']['depois']['registrado'] and not saved
    act(s,'testar-depois')
    act(s,'interpretar',resposta='gateway-remoto')
    state=act(s,'validar')
    assert state['xp_concedido']==100 and saved==[(7,'saindo-da-rede-local')]
    assert not state['ativo'] and state['conclusao']['registrada']


def test_consulta_roteador_nao_invalida_evidencias_nem_interpretacao():
    s,e,saved,error=setup_service();iniciar_local(s)
    act(s,'classificar',resposta='outra-rede');act(s,'aplicar',gateway='192.168.10.1')
    act(s,'testar-depois');before=act(s,'interpretar',resposta='gateway-remoto')
    after=act(s,'consultar')
    for key in ['revisao','depois','interpretacao','conferencia','gateway']:
        assert after['missao'][key]==before['missao'][key]
    interfaces=next(n for n in after['missao']['nos'] if n['id']==5)['interfaces']
    assert [i['ip'] for i in interfaces]==['192.168.10.1','192.168.20.1']
    assert after['missao']['concluido'] and not saved


def test_experimento_remoto_opcional_nao_substitui_comprovacao_final():
    s,e,saved,error=setup_service();iniciar_local(s)
    state=act(s,'testar-remoto')
    assert state['missao']['antes']['remoto'] is False
    assert state['missao']['proxima_etapa']=='rede' and not saved
    act(s,'classificar',resposta='outra-rede');act(s,'aplicar',gateway='192.168.10.1')
    with pytest.raises(error):act(s,'testar-remoto')
    assert not act(s,'status')['missao']['depois']['registrado']


@pytest.mark.parametrize('result',[(1,BAD),(255,'SSH disconnected'),(0,'sem estatísticas')])
def test_falha_local_nao_libera_etapa_ou_recompensa(result):
    s,e,saved,error=setup_service();act(s,'iniciar')
    e.overrides[1,'ping -n -I eth0 -c 2 -W 1 192.168.10.20']=result
    if result[0]==1:
        state=act(s,'testar-local',local='sim')
        assert state['missao']['teste_local']['alcance'] is False
    else:
        with pytest.raises(error):act(s,'testar-local',local='sim')
    assert not act(s,'status')['missao']['antes']['registrado'] and not saved
    with pytest.raises(error):act(s,'classificar',resposta='outra-rede')


@pytest.mark.parametrize('action,extra',[('testar-local',{'local':'sim'}),('testar-remoto',{}),('consultar',{}),('classificar',{'resposta':'outra-rede'})])
def test_novas_acoes_exigem_sessao_revisao_origem_e_identidade(action,extra):
    s,e,saved,error=setup_service();state=act(s,'iniciar')
    body=__import__('json').dumps({'session_id':state['laboratorio']['session_id'],'revisao':0,**extra}).encode()
    for user,origin,expected in [(None,True,401),({'id':7},False,403)]:
        data,code=despachar_gateway(s,user,'POST','/api/gateway/'+action,body,origem_autorizada=origin,limitar=lambda *args:True)
        assert code==expected and not e.commands
    with pytest.raises(error) as exc:
        s.executar_acao(7,'aluno',action,{'session_id':999,'revisao':0,**extra})
    assert exc.value.status==409 and not e.commands


def test_reteste_local_apos_gateway_preserva_evidencias_e_baseline():
    s,e,saved,error=setup_service();iniciar_local(s)
    act(s,'classificar',resposta='outra-rede');act(s,'aplicar',gateway='192.168.10.1');act(s,'testar-depois')
    before=copy.deepcopy(act(s,'status')['missao'])
    after=act(s,'testar-local',local='nao')['missao']
    assert after['antes']==before['antes'] and after['depois']==before['depois']
    assert e.gateway=='192.168.10.1' and not saved


def test_reteste_local_com_falha_invalida_aprovacao_antiga():
    s,e,saved,error=setup_service();iniciar_local(s)
    act(s,'classificar',resposta='outra-rede');act(s,'aplicar',gateway='192.168.10.1');act(s,'testar-depois')
    act(s,'interpretar',resposta='gateway-remoto')
    e.overrides[1,'ping -n -I eth0 -c 2 -W 1 192.168.10.20']=(1,BAD)
    state=act(s,'testar-local',local='sim')
    assert not state['missao']['depois']['registrado'] and not state['missao']['interpretacao']['correta']
    with pytest.raises(error):act(s,'validar')
    assert not saved
