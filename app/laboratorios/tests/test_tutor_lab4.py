import json
import pytest
from laboratorios.cenarios.configure_terminal import estado_publico
from laboratorios.tutor_lab4 import ANCORAS, PERFIL
from laboratorios.tutor_referencias import TutorReferencias, buscar_ancoras

TRECHO = {'livro': 'Linux: Utilitários de Redes', 'pagina_pdf': 13, 'conteudo': (
    'Para configurar um endereço IP na interface eth0: ip addr add 1.2.3.4/24 dev eth0. Para listar a tabela de '
    'roteamento: ip route show. Para adicionar uma rota padrão IPv4: ip route add default via 192.168.1.254. '
    'A máscara e o prefixo identificam a rede; o gateway padrão é o roteador da rede local.')}


def gerado(texto, usados=(1,), tipo='resposta'):
    return json.dumps({'tipo': tipo, 'trechos_usados': list(usados), 'resposta': texto})


def missao_em(etapa, identificada=False, **extra):
    missao = estado_publico(None, True)
    for c in missao['chamados']:
        if c['id'] == etapa:
            c['correta'] = identificada
    missao.update(proxima_etapa=etapa, **extra)
    return missao


def responder(texto, etapa='chamado-1', identificada=True, pergunta='Como configuro o endereço?', historico=None,
              rascunho=None, **extra):
    chamadas = []
    tutor = TutorReferencias(buscar=lambda q: [TRECHO], gerar=lambda s, c: (chamadas.append((s, json.loads(c))) or gerado(texto)),
                             ancoras=lambda ids: [], perfil=PERFIL)
    r = tutor.responder(pergunta=pergunta, missao=missao_em(etapa, identificada, **extra), historico=historico or [],
                        rascunho=rascunho or {})
    return r, chamadas


def test_ancoras_do_lab4_existem_no_indice():
    for etapa, ids in ANCORAS.items():
        assert len(buscar_ancoras(ids)) == len(ids), etapa


def test_contexto_traz_o_chamado_e_os_tres_pcs():
    texto = 'Use ip addr show para conferir o endereço da interface e o prefixo que identifica a rede.'
    r, chamadas = responder(texto, etapa='chamado-2', identificada=False)
    assert r['modo'] == 'referencias'
    sistema, contexto = chamadas[0]
    assert 'ip route add default via <gateway>' in sistema and 'aba por computador' in sistema
    assert contexto['chamado_atual'] == {'pc': 'PC Financeiro', 'sintoma': 'Fala com os colegas, mas não alcança o servidor.',
                                         'causa_identificada': False}
    assert contexto['estado_dos_pcs']['PC Financeiro'] == {'enderecos': ['192.168.10.12/24'], 'rota_padrao': '192.168.10.11'}
    assert 'compar' in contexto['restricao_da_etapa']
    assert 'session_id' not in json.dumps(contexto)


def test_comandos_ip_do_laboratorio_nao_sao_fora_do_tema():
    r, _ = responder('A forma é ip addr add <endereço>/<prefixo> dev eth0; depois ip route show mostra a tabela de roteamento.')
    assert r['modo'] == 'referencias'


@pytest.mark.parametrize('texto', [
    'Configure com ifconfig eth0 e confira o endereço da interface.', 'Use route add default gw para a rota padrão do roteador.',
    'Edite o arquivo /etc/network/interfaces para configurar o endereço IP da interface e a máscara.'])
def test_outras_ferramentas_sao_fora_do_tema(texto):
    assert responder(texto)[0]['motivo'] == 'fora_do_tema'


@pytest.mark.parametrize('etapa, texto', [
    ('chamado-1', 'A interface eth0 está ativa, mas não tem endereço IPv4 configurado na rede.'),
    ('chamado-1', 'A eth0 está UP, mas não há linha inet, ou seja, nenhum endereço IPv4 configurado na interface.'),
    ('chamado-2', 'Na tabela de roteamento, a rota padrão aponta para um computador e não para o roteador da rede local.'),
    ('chamado-2', 'O gateway está errado na tabela de roteamento deste computador.'),
    ('chamado-2', 'Repare: 192.168.10.11 não é o roteador da rede local, então a rota padrão não funciona.'),
    ('chamado-3', 'O prefixo está largo demais na interface e confunde a rede local.'),
    ('chamado-3', 'Com esse prefixo o servidor parece estar na mesma rede; o prefixo identifica a rede na tabela de roteamento.'),
    ('chamado-3', 'Basta trocar o /16 da interface pelo prefixo da rede local.'),
])
def test_causa_do_chamado_nao_e_entregue_antes_da_resposta(etapa, texto):
    assert responder(texto, etapa=etapa, identificada=False)[0]['motivo'] == 'filtro'
    assert responder(texto, etapa=etapa, identificada=True)[0]['modo'] == 'referencias'


def test_observar_sem_entregar_a_causa_e_permitido():
    for etapa, texto in (('chamado-1', 'Veja na saída se a interface eth0 está ativa e se aparece alguma linha inet; a máscara identifica a rede.'),
                         ('chamado-2', 'Compare as linhas default da tabela de roteamento dos dois computadores e veja para onde cada uma leva.'),
                         ('chamado-3', 'Veja qual rede o prefixo da interface identifica na tabela de roteamento e se o servidor fica dentro ou fora dela.')):
        assert responder(texto, etapa=etapa, identificada=False)[0]['modo'] == 'referencias', etapa


def test_endereco_concreto_so_no_nivel_4_ou_se_o_aluno_propos():
    texto = 'Para configurar o endereço na interface use ip addr add 192.168.10.50/24 dev eth0; o prefixo identifica a rede.'
    assert responder(texto)[0]['motivo'] == 'filtro'
    assert responder(texto, rascunho={'comando': 'ip addr add 192.168.10.50/24'})[0]['modo'] == 'referencias'
    historico = [{'etapa': 'chamado-1', 'modo': 'referencias', 'nivel': 3, 'pergunta': 'x'}]
    assert responder(texto, pergunta='Ainda não consegui', historico=historico)[0]['modo'] == 'referencias'


@pytest.mark.parametrize('texto', [
    'Adicione ip route add default via 192.168.10.1 e teste o servidor pela rota padrão.',
    'O gateway é 192.168.10.1, a interface do roteador na rede local da tabela de roteamento.'])
def test_gateway_nao_e_entregue_no_chamado_1_antes_do_nivel_4(texto):
    assert responder(texto)[0]['motivo'] == 'filtro'


def test_gateway_ja_conhecido_pode_ser_citado_nos_chamados_seguintes():
    texto = 'O PC Novo usa 192.168.10.1 como gateway na tabela de roteamento; compare com a rota padrão deste computador.'
    assert responder(texto, etapa='chamado-2', identificada=False)[0]['modo'] == 'referencias'
    comando = 'Remova a rota e use ip route add default via 192.168.10.1 na tabela de roteamento.'
    assert responder(comando, etapa='chamado-2')[0]['motivo'] == 'filtro'


def test_ajuda_revisada_progride_por_nivel_e_fase():
    m1 = missao_em('chamado-1', identificada=False)
    assert 'sem endereço' not in PERFIL.alternativa('chamado-1', 4, m1, {})
    m1 = missao_em('chamado-1', identificada=True)
    assert '<gateway>' in PERFIL.alternativa('chamado-1', 2, m1, {})
    assert '192.168.10.1' not in PERFIL.alternativa('chamado-1', 3, m1, {})
    assert '192.168.10.1' in PERFIL.alternativa('chamado-1', 4, m1, {})
    m2 = missao_em('chamado-2', identificada=False)
    assert 'aponta para um computador' not in PERFIL.alternativa('chamado-2', 4, m2, {})
    m3 = missao_em('chamado-3', identificada=False)
    texto = PERFIL.alternativa('chamado-3', 4, m3, {})
    assert 'largo' not in texto and '/24' not in texto
    assert '/24' in PERFIL.alternativa('chamado-3', 4, missao_em('chamado-3', identificada=True), {})


def test_na_terceira_pergunta_da_etapa_o_link_ensina_o_comando():
    texto = 'Remova a rota com ip route del default e crie a certa com ip route add default via 192.168.10.1 para o roteador.'
    uma = [{'etapa': 'chamado-2', 'modo': 'referencias', 'nivel': 1, 'pergunta': 'Como adiciono a rota?'}]
    r, chamadas = responder(texto, etapa='chamado-2', pergunta='Qual é o comando da rota?', historico=uma)
    assert r['motivo'] == 'filtro' and 'duas perguntas' not in chamadas[0][1]['restricao_da_etapa']
    duas = uma + [{'etapa': 'chamado-2', 'modo': 'contingencia', 'nivel': 1, 'pergunta': 'E o comando?'}]
    r, chamadas = responder(texto, etapa='chamado-2', pergunta='Qual é o comando da rota?', historico=duas)
    assert r['modo'] == 'referencias' and r['nivel'] == 4
    assert 'escreva o comando completo' in chamadas[0][1]['restricao_da_etapa']
    # Perguntas de outro chamado não contam.
    outras = [{**m, 'etapa': 'chamado-1'} for m in duas]
    assert responder(texto, etapa='chamado-2', pergunta='Qual é o comando?', historico=outras)[0]['motivo'] == 'filtro'
