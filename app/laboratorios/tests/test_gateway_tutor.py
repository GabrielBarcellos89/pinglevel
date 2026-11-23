import json
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_gateway_guiado import setup_service, act
from laboratorios.tutor_referencias import TutorReferencias
from laboratorios.api_gateway_guiado import despachar_gateway


def configurar(s):
    s.tutor=TutorReferencias(buscar=lambda q:[{'livro':'Referência de teste','pagina_pdf':4,'conteudo':'A máscara separa a rede da identificação do host em cada endereço da topologia.'}],
        gerar=lambda *args:json.dumps({'tipo':'resposta','trechos_usados':[1],'resposta':'Observe a topologia: qual endereço pertence ao colega e qual pertence ao servidor? A máscara separa a rede.'}),
        ancoras=lambda ids:[])


def test_conversa_nao_altera_evidencias_revisao_ou_xp_e_recupera_historico():
    s,e,saved,error=setup_service();configurar(s);before=act(s,'iniciar')
    after=act(s,'tutor',pergunta='Como escolho o destino?')
    assert after['tutor']['modo']=='referencias'
    assert after['missao']==before['missao'] and not e.commands and not saved
    assert act(s,'status')['tutoria']==after['tutoria']
    assert len(after['tutoria'])==1


@pytest.mark.parametrize('pergunta',['',None,7,'x'*501])
def test_pergunta_invalida_nao_mexe_na_rede(pergunta):
    s,e,saved,error=setup_service();configurar(s);act(s,'iniciar')
    with pytest.raises(error):act(s,'tutor',pergunta=pergunta)
    assert not e.commands and not saved


def test_tutor_nao_bloqueia_rede_e_descarta_resposta_se_revisao_mudar():
    s,e,saved,error=setup_service();act(s,'iniciar')
    iniciou=threading.Event();liberar=threading.Event()
    def gerar(*args):
        iniciou.set();assert liberar.wait(3)
        return json.dumps({'tipo':'resposta','trechos_usados':[1],'resposta':'Observe o endereço do colega na topologia local.'})
    s.tutor=TutorReferencias(buscar=lambda q:[{'livro':'Teste','pagina_pdf':1,'conteudo':'Rede local e endereço IPv4 do colega na topologia.'}],gerar=gerar,ancoras=lambda ids:[])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futuro=pool.submit(act,s,'tutor',pergunta='Qual endereço devo observar?')
        assert iniciou.wait(2)
        try:
            with pytest.raises(error) as exc:act(s,'tutor',pergunta='Outra pergunta')
            assert exc.value.status==429
            estado=pool.submit(act,s,'testar-local',local='sim').result(timeout=2)
            assert estado['missao']['antes']['local'] is True
        finally:liberar.set()
        with pytest.raises(error) as exc:futuro.result(timeout=2)
        assert exc.value.status==409
    assert not act(s,'status')['tutoria'] and not saved


def test_tutor_exige_sessao_e_revisao_atuais():
    s,e,saved,error=setup_service();configurar(s);act(s,'iniciar')
    with pytest.raises(error) as exc:
        s.executar_acao(7,'aluno','tutor',{'session_id':999,'revisao':0,'pergunta':'Dúvida'})
    assert exc.value.status==409 and not e.commands


@pytest.mark.parametrize('usuario,origem,codigo',[(None,True,401),({'id':7},False,403)])
def test_tutor_http_exige_login_e_origem(usuario,origem,codigo):
    s,e,saved,error=setup_service();configurar(s)
    _,status=despachar_gateway(s,usuario,'POST','/api/gateway/tutor',b'{}',origem_autorizada=origem,limitar=lambda *args:True)
    assert status==codigo and not e.created


def test_limite_tutor_separado_dos_testes():
    s,e,saved,error=setup_service();configurar(s);act(s,'iniciar')
    _,status=despachar_gateway(s,{'id':7},'POST','/api/gateway/tutor',json.dumps({'session_id':1,'revisao':0,'pergunta':'Dúvida'}).encode(),origem_autorizada=True,limitar=lambda chave,*args:not chave.startswith('gateway-tutor:'))
    assert status==429 and not e.commands
