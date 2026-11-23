import json
import sqlite3
import pytest
from laboratorios.tutor_referencias import ANCORAS, TutorReferencias, buscar_ancoras, fundamentada, nivel_ajuda
from laboratorios.cenarios.saindo_rede_local import estado_publico
from rag.recuperador import buscar_contexto

# Trecho com vocabulário amplo para que os testes de filtro não dependam da checagem de fundamentação.
TRECHO={'livro':'Material de teste','pagina_pdf':12,'secao':'IPv4','conteudo':(
    'A máscara identifica a parte de rede de cada endereço. Compare os endereços dos equipamentos na topologia. '
    'O gateway encaminha pacotes para outra rede pelo roteador; o ping testa a comunicação com o servidor e o colega.')}
TEXTO='Observe os endereços na topologia e compare a parte de rede indicada pela máscara. O que muda entre o computador e o destino?'


def gerado(texto, usados=(1,), tipo='resposta'):
    return json.dumps({'tipo':tipo,'trechos_usados':list(usados),'resposta':texto})


def tutor(gerar, buscar=lambda q:[TRECHO], ancoras=lambda ids:[]):
    return TutorReferencias(buscar=buscar,gerar=gerar,ancoras=ancoras)


def responder(t, pergunta='Como comparo as redes?', historico=None, etapa='rede'):
    missao=estado_publico(None,True);missao['proxima_etapa']=etapa
    return t.responder(pergunta=pergunta,missao=missao,historico=historico or [],rascunho={})


def test_trechos_numerados_e_contexto_sem_dados_pessoais():
    calls=[]
    r=responder(tutor(lambda s,c:(calls.append(json.loads(c)) or gerado(TEXTO))))
    assert r['modo']=='referencias' and r['fontes']==[{'livro':'Material de teste','pagina_pdf':12}]
    assert calls[0]['etapa']=='rede' and calls[0]['nivel']==1
    assert 'usuario_id' not in calls[0] and 'session_id' not in calls[0]
    assert calls[0]['trechos_dos_livros']==[{'numero':1,'texto':TRECHO['conteudo']}]
    assert 'Nunca afirme essa conclusão' in calls[0]['restricao_da_etapa']


def test_ancoras_da_etapa_vem_antes_da_busca_e_fontes_sao_so_as_usadas():
    ancora={'livro':'Redes para Iniciantes','pagina_pdf':155,'conteudo':TRECHO['conteudo']}
    pedidas=[]
    t=tutor(lambda s,c:gerado(TEXTO,usados=[2]),ancoras=lambda ids:(pedidas.append(ids) or [ancora]))
    r=responder(t)
    assert pedidas==[ANCORAS['rede']]
    assert r['fontes']==[{'livro':'Material de teste','pagina_pdf':12}]


def test_ancoras_reais_existem_no_indice():
    for etapa,ids in ANCORAS.items():
        trechos=buscar_ancoras(ids)
        assert len(trechos)==len(ids) and all(t['livro']=='Redes para Iniciantes' for t in trechos), etapa


def test_sem_busca_mas_com_ancora_ainda_responde():
    ancora={'livro':'Redes para Iniciantes','pagina_pdf':155,'conteudo':TRECHO['conteudo']}
    r=responder(tutor(lambda *a:gerado(TEXTO),buscar=lambda q:[],ancoras=lambda ids:[ancora]))
    assert r['modo']=='referencias' and r['fontes']==[{'livro':'Redes para Iniciantes','pagina_pdf':155}]


@pytest.mark.parametrize('buscar',[lambda q:[],lambda q: (_ for _ in ()).throw(FileNotFoundError('caminho privado')),lambda q:[{}]])
def test_sem_material_nao_inventa_fontes_e_nao_chama_provedor(buscar):
    r=responder(tutor(lambda *args:pytest.fail('Não deve chamar LLM sem referências'),buscar=buscar))
    assert r['modo']=='contingencia' and r['fontes']==[] and r['aviso']
    assert 'caminho privado' not in str(r)


@pytest.mark.parametrize('tipo',['sem_material','fora_do_tema'])
def test_modelo_declara_falta_de_material_ou_outro_tema(tipo):
    r=responder(tutor(lambda *a:gerado('',usados=[],tipo=tipo)))
    assert r['modo']=='contingencia' and r['fontes']==[]
    assert ('não tratam' if tipo=='sem_material' else 'outro laboratório') in r['aviso']


@pytest.mark.parametrize('saida',[
    'texto sem JSON', gerado(TEXTO,usados=[]), gerado(TEXTO,usados=[7]), gerado(''), gerado(TEXTO,tipo='outro'),
])
def test_json_invalido_ou_sem_trecho_valido_vira_alternativa(saida):
    r=responder(tutor(lambda *a:saida))
    assert r['modo']=='contingencia' and not r['fontes']


def test_resposta_sem_relacao_com_o_trecho_citado_nao_passa():
    r=responder(tutor(lambda *a:gerado('DNS traduz nomes de domínio legíveis em números usados pelas máquinas.')))
    assert r['modo']=='contingencia' and 'não tratam' in r['aviso']


def test_checagem_de_fundamentacao():
    assert fundamentada('A máscara identifica a parte de rede do endereço.',[TRECHO['conteudo']])
    assert not fundamentada('O protocolo traduz nomes legíveis.',[TRECHO['conteudo']])


@pytest.mark.parametrize('texto',[
    'x'*1601,'ANTHROPIC_API_KEY segredo',
    'Execute ping 192.168.10.20.', 'Configure 192.168.10.1 como gateway.',
    'Execute sudo ip route add default.', 'Execute ping 8.8.8.8.',
])
def test_saida_invalida_ou_solucao_antecipada_vira_alternativa_identificada(texto):
    r=responder(tutor(lambda *args:gerado(texto+' Compare a máscara e a parte de rede dos endereços.')))
    assert r['modo']=='contingencia' and not r['fontes']


def test_ip_do_pc_nao_e_confundido_com_gateway_por_substring():
    r=responder(tutor(lambda *args:gerado('Observe seu IP 192.168.10.10 e compare a parte de rede indicada pela máscara de cada endereço.')))
    assert r['modo']=='referencias'


def test_discute_tentativa_do_aluno_sem_esconder_ferramenta_que_ele_ja_propos():
    texto='Seu teste ping 192.168.10.20 aponta ao colega. Observe se a comunicação com esse endereço respondeu.'
    r=responder(tutor(lambda *args:gerado(texto)),pergunta='Usei ping 192.168.10.20, isso testa o colega?')
    assert r['modo']=='referencias'


def test_ajuda_so_progride_com_dificuldade_persistente_e_reseta_por_etapa():
    h=[{'etapa':'rede','modo':'referencias','nivel':1}]
    assert nivel_ajuda('O que é uma máscara?',h,'rede')==1
    assert nivel_ajuda('Não entendi, pode explicar de novo?',h,'rede')==2
    h.append({'etapa':'rede','modo':'referencias','nivel':4})
    assert nivel_ajuda('Ainda não consegui',h,'rede')==4
    assert nivel_ajuda('Não entendi',h,'gateway')==1


def test_provedor_indisponivel_nao_vaza_erro():
    r=responder(tutor(lambda *args:(_ for _ in ()).throw(RuntimeError('chave secreta'))))
    assert r['modo']=='contingencia' and 'chave secreta' not in str(r)


def test_busca_sqlite_real_com_indice_temporario(tmp_path):
    banco=tmp_path/'rag.db'
    with sqlite3.connect(banco) as conn:
        conn.executescript('''CREATE TABLE chunks(id INTEGER PRIMARY KEY,livro TEXT,arquivo TEXT,pagina_pdf INTEGER,secao TEXT,ordem_pagina INTEGER,conteudo TEXT);
        CREATE VIRTUAL TABLE chunks_fts USING fts5(conteudo,content='chunks',content_rowid='id');''')
        conn.execute('INSERT INTO chunks VALUES(1,?,?,?,?,?,?)',('Redes de teste','teste.pdf',7,'IPv4',1,TRECHO['conteudo']))
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    r=responder(tutor(lambda *args:gerado(TEXTO),buscar=lambda q:buscar_contexto(q,limite=3,banco=banco)))
    assert r['modo']=='referencias' and r['fontes']==[{'livro':'Redes de teste','pagina_pdf':7}]


def test_contingencia_tambem_progride_sem_esconder_resposta_indefinidamente():
    t=tutor(lambda *args:pytest.fail('Sem material'),buscar=lambda q:[])
    historico=[]
    for nivel in range(1,5):
        r=responder(t,pergunta='Não entendi, preciso de mais ajuda',historico=historico,etapa='local')
        assert r['nivel']==nivel and r['modo']=='contingencia'
        if nivel==1:assert 'ping 192.168.10.20' not in r['resposta']
        historico.append({**r,'pergunta':'Não entendi, preciso de mais ajuda','etapa':'local'})
    assert 'ping 192.168.10.20' in r['resposta']


def test_contingencia_reconhece_tentativa_aproximada():
    missao=estado_publico(None,True);missao['proxima_etapa']='local'
    r=tutor(None,buscar=lambda q:[]).responder(pergunta='O que falta na minha tentativa?',missao=missao,historico=[],rascunho={'comando':'ping'})
    assert 'já escolheu a ferramenta' in r['resposta']
    assert 'ping 192.168.10.20' not in r['resposta']


def test_markdown_vira_texto_simples():
    r=responder(tutor(lambda *a:gerado('# Máscara\n\nCompare a **parte de rede** de cada `endereço`.\n- Qual muda na topologia?')))
    assert r['modo']=='referencias' and r['resposta']=='Máscara\n\nCompare a parte de rede de cada endereço.\nQual muda na topologia?'


@pytest.mark.parametrize('saida',[
    'Os terceiros números são diferentes (10 vs 20), então o servidor está em outra rede pela máscara.',
    'Note que 192.168.10 é diferente de 192.168.20: as redes são distintas pela máscara dos endereços.',
    'O PC Atendimento e o servidor não estão na mesma rede, compare a máscara dos endereços.',
])
def test_etapa_rede_nao_entrega_a_conclusao(saida):
    assert responder(tutor(lambda *a:gerado(saida)))['modo']=='contingencia'


def test_etapa_rede_pode_ensinar_o_metodo_condicional():
    texto='Se a parte de rede indicada pela máscara for igual, os equipamentos estão na mesma rede. Compare os endereços da topologia.'
    assert responder(tutor(lambda *a:gerado(texto)))['modo']=='referencias'


def test_etapa_local_nao_antecipa_a_previsao():
    texto='O ping testa a comunicação. O colega está na mesma rede que você, compare os endereços.'
    assert responder(tutor(lambda *a:gerado(texto)),etapa='local')['modo']=='contingencia'


@pytest.mark.parametrize('saida',['Os endereços e a máscara se consultam com nslookup na topologia.','Você está no nível 2, compare a máscara dos endereços.'])
def test_fora_do_escopo_e_mencao_a_nivel_viram_alternativa(saida):
    assert responder(tutor(lambda *a:gerado(saida)),etapa='comprovar')['modo']=='contingencia'


def test_ip_do_gateway_liberado_depois_de_confirmado():
    texto='Depois que 192.168.10.1 virou o gateway, o servidor passou a responder pelo roteador. Compare os endereços.'
    missao=estado_publico(None,True);missao['proxima_etapa']='comprovar'
    t=tutor(lambda *a:gerado(texto))
    assert t.responder(pergunta='Por que funcionou?',missao=missao,historico=[],rascunho={})['modo']=='contingencia'
    missao['gateway']={'valor':'192.168.10.1','confirmado':True,'observado':'192.168.10.1'}
    assert t.responder(pergunta='Por que funcionou?',missao=missao,historico=[],rascunho={})['modo']=='referencias'


def test_etapa_comprovar_nao_entrega_a_interpretacao_pendente():
    texto='O colega está na mesma rede que você. Já o servidor está em outra rede e precisa do gateway pelo roteador.'
    missao=estado_publico(None,True);missao['proxima_etapa']='comprovar'
    t=tutor(lambda *a:gerado(texto))
    assert t.responder(pergunta='Por que funcionou?',missao=missao,historico=[],rascunho={})['modo']=='contingencia'
    missao['interpretacao']={'resposta':'gateway-remoto','correta':True,'feedback':''}
    assert t.responder(pergunta='Por que funcionou?',missao=missao,historico=[],rascunho={})['modo']=='referencias'


@pytest.mark.parametrize('texto,motivo',[
    ('Os endereços e a máscara se consultam com nslookup na topologia.','fora_do_tema'),
    ('O PC Atendimento e o servidor não estão na mesma rede, compare a máscara dos endereços.','filtro'),
])
def test_bloqueio_por_conteudo_nao_e_anunciado_como_falha(texto,motivo):
    r=responder(tutor(lambda *a:gerado(texto)))
    assert r['motivo']==motivo and 'Não consegui' not in r['aviso']


def test_falha_do_provedor_tem_motivo_proprio():
    r=responder(tutor(lambda *a:'sem JSON'))
    assert r['motivo']=='falha' and 'Não consegui' in r['aviso']
