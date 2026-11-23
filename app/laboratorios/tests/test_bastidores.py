"""Bastidores (tshark) nos labs de rede: o servidor captura só os comandos que geram tráfego e guarda as últimas
capturas no estado do aluno; a leitura do tshark vira eventos em linguagem simples (ARP, ICMP, DNS e DHCP)."""
from contextlib import contextmanager

from laboratorios.captura import CAMPOS_REDE, interpretar_campos
from laboratorios.cenarios import primeira_lan as lab2
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import PERFIL_LAB2
from test_primeira_lan import Engine, Sala, act, term


def linha(**campos):
    return '\t'.join(campos.get(c.replace('.', '_'), '') for c in CAMPOS_REDE)


def test_interpreta_dns_dhcp_e_erro_icmp():
    saida = '\n'.join([
        linha(frame_number='1', frame_time_relative='0.0', ip_src='192.168.10.11', ip_dst='192.168.10.1', udp_dstport='53',
              dns_flags_response='0', dns_qry_name='intranet.empresa'),
        linha(frame_number='2', frame_time_relative='0.01', ip_src='192.168.10.1', ip_dst='192.168.10.11', udp_srcport='53',
              dns_flags_response='1', dns_qry_name='intranet.empresa', dns_a='192.168.60.20'),
        linha(frame_number='3', frame_time_relative='0.2', ip_src='0.0.0.0', ip_dst='255.255.255.255', dhcp_option_dhcp='1'),
        linha(frame_number='4', frame_time_relative='0.3', ip_src='192.168.10.1,192.168.10.10', ip_dst='192.168.10.10,192.168.20.10',
              icmp_type='3,8'),
    ])
    eventos = interpretar_campos(saida, CAMPOS_REDE)
    assert [e['tipo'] for e in eventos] == ['DNS Pergunta', 'DNS Resposta', 'DHCP Discover', 'ICMP Destino inalcançável']
    assert [e['protocolo'] for e in eventos] == ['DNS', 'DNS', 'DHCP', 'ICMP']
    assert eventos[3]['origem'] == '192.168.10.1' and eventos[3]['destino'] == '192.168.10.10'


class EngineObservada(Engine):
    def __init__(self, rede):
        super().__init__(rede)
        self.observados = []

    @contextmanager
    def observar(self, uid, node):
        resultado = {}
        self.observados.append(node)
        yield resultado
        resultado.update({'estado': 'concluida', 'node_id': node, 'eventos': [{'tipo': 'ARP Request'}], 'mensagem': ''})


def test_so_comandos_com_trafego_sao_capturados_e_ficam_os_ultimos():
    engine = EngineObservada(Sala())
    s = ServicoRede(engine, lambda uid, lab: {'xp_concedido': 0}, cenario=lab2, perfil_tutor=PERFIL_LAB2)
    act(s, 'iniciar')
    term(s, 'pc1', 'ip addr show')
    assert engine.observados == [] and act(s, 'status')['bastidores'] == []
    for _ in range(5):
        term(s, 'pc1', 'ping 192.168.10.10')
    estado = act(s, 'status')
    assert engine.observados == [lab2.NOS['pc1']['no']] * 5
    assert len(estado['bastidores']) == 4
    assert estado['bastidores'][-1]['pc'] == 'pc1' and estado['bastidores'][-1]['digitado'] == 'ping 192.168.10.10'
    assert estado['bastidores'][-1]['revisao'] == estado['missao']['terminal'][-1]['revisao']


def test_sem_captura_disponivel_o_lab_segue_igual():
    s = ServicoRede(Engine(Sala()), lambda uid, lab: {'xp_concedido': 0}, cenario=lab2, perfil_tutor=PERFIL_LAB2)
    act(s, 'iniciar')
    term(s, 'pc1', 'ping 192.168.10.10')
    assert act(s, 'status')['bastidores'] == []
