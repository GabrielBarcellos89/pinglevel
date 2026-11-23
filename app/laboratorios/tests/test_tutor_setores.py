import json

import pytest

from laboratorios.cenarios import dividindo_rede as lab5, planejando_empresa as lab6
from laboratorios.tutor_referencias import TutorReferencias, buscar_ancoras
from laboratorios.tutor_setores import ANCORAS_5, ANCORAS_6, ANCORAS_7, PERFIL_LAB5, PERFIL_LAB6, PERFIL_LAB7
from laboratorios.cenarios import conectando_redes as lab7

TRECHO = {'livro': 'Redes para Iniciantes', 'pagina_pdf': 75, 'conteudo': (
    'A máscara de rede (ou prefixo) indica quantos bits do endereço IP identificam a rede e quantos identificam o host. '
    'O roteador encaminha pacotes entre redes usando a tabela de roteamento; o gateway padrão é o roteador da rede local. '
    'Para configurar um endereço: ip addr add 1.2.3.4/24 dev eth0.')}


def responder(texto, c=lab5, etapa='plano', plano_ok=False, causa_ok=False, pergunta='Como faço?', nivel_alto=False):
    missao = c.estado_publico(None, True)
    missao['plano']['correto'] = plano_ok
    if missao['chamado']:
        missao['chamado']['correta'] = causa_ok
    missao['proxima_etapa'] = etapa
    historico = [{'etapa': etapa, 'modo': 'referencias', 'nivel': 3, 'pergunta': 'x'}] if nivel_alto else []
    perfil = {lab5: PERFIL_LAB5, lab6: PERFIL_LAB6, lab7: PERFIL_LAB7}[c]
    tutor = TutorReferencias(buscar=lambda q: [TRECHO], ancoras=lambda ids: [], perfil=perfil,
        gerar=lambda s, ctx: json.dumps({'tipo': 'resposta', 'trechos_usados': [1], 'resposta': texto}))
    return tutor.responder(pergunta=pergunta, missao=missao, historico=historico, rascunho={})


@pytest.mark.parametrize('ancoras', [ANCORAS_5, ANCORAS_6, ANCORAS_7])
def test_ancoras_existem_no_indice(ancoras):
    for etapa, ids in ancoras.items():
        assert len(buscar_ancoras(ids)) == len(ids), etapa


def test_plano_nao_e_entregue_antes_da_conferencia():
    texto = 'O bloco seguinte começa em 192.168.50.64: a máscara de rede indica quantos bits identificam a rede e o host.'
    assert responder(texto)['motivo'] == 'filtro'
    assert responder(texto, plano_ok=True, etapa='roteador')['modo'] == 'referencias'
    ok = 'Um /26 tem 64 endereços: o prefixo identifica a rede e o host; o bloco do Vendas vai de 192.168.50.0 a .63.'
    assert responder(ok)['modo'] == 'referencias'
    vlsm = 'A rede do Vendas é 192.168.80.128: a máscara de rede indica quantos bits identificam a rede e o host.'
    assert responder(vlsm, c=lab6)['motivo'] == 'filtro'
    assert responder('A rede 192.168.80.0/24 é dividida: a máscara de rede indica quantos bits identificam a rede e o host.', c=lab6)['modo'] == 'referencias'


def test_causa_do_chamado_e_comandos_prontos():
    causa = 'O endereço do PC V2 está fora do bloco do Vendas; o prefixo identifica a rede e o host.'
    assert responder(causa, etapa='chamado', plano_ok=True)['motivo'] == 'filtro'
    assert responder(causa, etapa='chamado', plano_ok=True, causa_ok=True)['modo'] == 'referencias'
    comando = 'No roteador use ip addr add 192.168.50.65/26 dev eth1; o roteador encaminha pacotes entre redes.'
    assert responder(comando, etapa='roteador', plano_ok=True)['motivo'] == 'filtro'
    assert responder(comando, etapa='roteador', plano_ok=True, nivel_alto=True, pergunta='Ainda não consegui')['modo'] == 'referencias'
    assert responder('Use ifconfig eth1 para configurar o endereço do roteador.', etapa='roteador', plano_ok=True)['motivo'] == 'fora_do_tema'


def test_lab7_nao_entrega_a_causa_nem_a_rota_pronta():
    causa = 'O R1 não tem rota para 192.168.20.0/24; o roteador encaminha pacotes entre redes pela tabela de roteamento.'
    assert responder(causa, c=lab7, etapa='chamado')['motivo'] == 'filtro'
    assert responder(causa, c=lab7, etapa='chamado', causa_ok=True)['modo'] == 'referencias'
    ok = 'Leia a tabela de roteamento do R1: o roteador encaminha pacotes entre redes que aparecem nela.'
    assert responder(ok, c=lab7, etapa='chamado')['modo'] == 'referencias'
    pronta = 'No R1: ip route add 192.168.20.0/24 via 10.0.0.2; o roteador encaminha pacotes entre redes.'
    assert responder(pronta, c=lab7, etapa='ida', plano_ok=True, causa_ok=True)['motivo'] == 'filtro'
