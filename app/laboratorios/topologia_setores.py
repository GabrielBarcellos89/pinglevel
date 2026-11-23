"""Topologias dos Labs 2 e 5 a 10: setores (um switch cada) ligados a um roteador. SDK injetado, sem CORE no import.

Os endereços dados aos enlaces só existem porque o CORE os exige; `preparar` remove os que o aluno deve configurar e
deixa o estado inicial descrito no cenário (INICIAL), que o serviço confere antes de liberar a missão.
"""
import base64
from pathlib import Path

ROTEADOR = 5

# laboratório → (switches {id: nome}, PCs {id: (nome, switch, endereço/prefixo)}, roteador [(interface, switch, endereço/prefixo)])
TOPOLOGIAS = {
    'dividindo-uma-rede': (
        {3: 'switch-vendas', 4: 'switch-financeiro'},
        {1: ('pc-v1', 3, '192.168.50.10/26'), 2: ('pc-v2', 3, '192.168.50.70/26'),
         6: ('pc-f1', 4, '192.168.50.66/26'), 7: ('pc-f2', 4, '192.168.50.67/26')},
        [('eth0', 3, '192.168.50.1/26'), ('eth1', 4, '192.168.50.65/26')]),
    'planejando-uma-empresa': (
        {3: 'switch-atendimento', 4: 'switch-vendas', 7: 'switch-financeiro'},
        {1: ('pc-atendimento', 3, '192.168.80.10/25'), 2: ('pc-vendas', 4, '192.168.80.130/26'),
         6: ('pc-financeiro', 7, '192.168.80.194/27')},
        [('eth0', 3, '192.168.80.1/25'), ('eth1', 4, '192.168.80.129/26'), ('eth2', 7, '192.168.80.193/27')]),
}
# Lab 7: dois roteadores ligados direto por um enlace /30, cada um com a sua filial.
DOIS_ROTEADORES = 'conectando-redes'
POSICOES_7 = {1: (90, 150), 3: (220, 150), 5: (370, 150), 6: (530, 150), 4: (680, 150), 2: (810, 150)}
POSICOES = {1: (90, 70), 2: (90, 230), 6: (690, 70), 7: (690, 230), 3: (230, 150), 4: (550, 150), 5: (390, 150)}
# Estado inicial de cada laboratório: (nó, comando) executados depois de criados os enlaces.
PREPARO = {
    'dividindo-uma-rede': [
        (1, 'ip -4 route replace default via 192.168.50.1 dev eth0'),  # PC V1 pronto, modelo do Vendas
        (5, 'ip -4 addr flush dev eth1'),
        (6, 'ip -4 addr flush dev eth0'), (7, 'ip -4 addr flush dev eth0'),
    ],
    'planejando-uma-empresa': [
        (5, 'ip -4 addr flush dev eth0'), (5, 'ip -4 addr flush dev eth1'), (5, 'ip -4 addr flush dev eth2'),
        (1, 'ip -4 addr flush dev eth0'), (2, 'ip -4 addr flush dev eth0'), (6, 'ip -4 addr flush dev eth0'),
    ],
}
REDE = {'dividindo-uma-rede': '192.168.50.0/24', 'planejando-uma-empresa': '192.168.80.0/24'}


# Lab 9: quatro PCs na mesma rede IP ligados a um switch real (nó Docker com bridge Linux e filtro de VLAN).
LAN = 'investigando-a-lan'
POSICOES_9 = {1: (120, 70), 2: (120, 230), 5: (400, 150), 6: (680, 70), 7: (680, 230)}
PCS_9 = {1: ('pc-v1', 0, '192.168.30.11', '02:16:3e:5a:01:0b'), 2: ('pc-v2', 1, '192.168.30.12', '02:16:3e:5a:01:2c'),
         6: ('pc-f1', 2, '192.168.30.21', '02:16:3e:7d:02:4e'), 7: ('pc-f2', 3, '192.168.30.22', '02:16:3e:7d:02:9f')}
VLANS_9 = {'eth0': 10, 'eth1': 20, 'eth2': 1, 'eth3': 1}  # a porta do PC V2 começa na VLAN errada (o chamado)


def _construir_lan(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    nos = {}
    for node_id, rotulo in [(5, 'switch'), *((n, p[0]) for n, p in PCS_9.items())]:
        x, y = POSICOES_9[node_id]
        nos[node_id] = sessao.add_node(node_id, name=f'pl-s{session_id}-{nome}-{rotulo}', _type=NodeType.DOCKER,
                                       position=Position(x=x, y=y), image=imagem)
    for node_id, (_, porta, ip, mac) in PCS_9.items():
        sessao.add_link(node1=nos[node_id], node2=nos[5],
                        iface1=Interface(id=0, name='eth0', mac=mac, ip4=ip, ip4_mask=24),
                        iface2=Interface(id=porta, name=f'eth{porta}'))
    return {5: 'switch', **{n: p[0] for n, p in PCS_9.items()}}


def _preparar_lan(core, session_id):
    comandos = [(n, c) for n in PCS_9 for c in ('ip -4 route flush default', 'sysctl -w net.ipv4.ip_forward=0',
                                                'ip neigh flush dev eth0')]
    comandos += [(5, 'sysctl -w net.ipv4.ip_forward=0'), (5, 'ip link add br0 type bridge vlan_filtering 1')]
    for porta, vlan in VLANS_9.items():
        comandos += [(5, f'ip -4 addr flush dev {porta}'), (5, f'ip link set {porta} master br0'), (5, f'ip link set {porta} up')]
        if vlan != 1:
            comandos += [(5, f'bridge vlan add dev {porta} vid {vlan} pvid untagged'), (5, f'bridge vlan del dev {porta} vid 1')]
    comandos.append((5, 'ip link set br0 up'))
    return comandos


# Lab 8: uma rede com DHCP e DNS (dnsmasq no servidor .2), três PCs de suporte e os destinos dos nomes.
SERVICOS = 'enderecos-e-nomes'
SWITCH_8 = 4
NOS_8 = {1: ('pc-novo', None, None), 2: ('pc-recepcao', '192.168.40.60', None), 3: ('pc-financeiro', None, '02:16:3e:40:00:33'),
         5: ('roteador', '192.168.40.1', None), 6: ('servidor', '192.168.40.2', None), 7: ('intranet', '192.168.40.20', None),
         8: ('impressora', '192.168.40.30', None)}
POSICOES_8 = {1: (90, 60), 2: (90, 150), 3: (90, 240), 4: (330, 150), 5: (330, 40), 6: (570, 60), 7: (570, 150), 8: (570, 240)}
DNSMASQ_8 = ('dnsmasq --interface=eth0 --bind-interfaces --no-resolv --no-hosts --domain=empresa.local --local=/empresa.local/ '
             '--dhcp-range=192.168.40.100,192.168.40.150,255.255.255.0,1h --dhcp-option=3,192.168.40.1 '
             '--dhcp-option=6,192.168.40.2 --dhcp-host=02:16:3e:40:00:33,192.168.40.120 '
             '--host-record=intranet.empresa.local,192.168.40.20 --host-record=impressora.empresa.local,192.168.40.30 '
             '--dhcp-leasefile=/tmp/dnsmasq.leases --pid-file=/tmp/dnsmasq.pid --no-ping')
# Concessão do udhcpc: -n desiste se ninguém responder, -q sai com a configuração aplicada.
UDHCPC = 'udhcpc -i eth0 -n -q -t 5 -T 1'


def _resolv(*servidores):
    """O /etc/resolv.conf é montado pelo Docker: reescreve-se o conteúdo, nunca o arquivo."""
    linhas = ''.join(f'nameserver {s}\\n' for s in servidores) or '# nenhum servidor DNS configurado\\n'
    return f"printf '{linhas}' > /etc/resolv.conf"


def _construir_servicos(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    x, y = POSICOES_8[SWITCH_8]
    switch = sessao.add_node(SWITCH_8, name=f'pl-s{session_id}-{nome}-switch', _type=NodeType.SWITCH, position=Position(x=x, y=y))
    for porta, (node_id, (rotulo, ip, mac)) in enumerate(NOS_8.items()):
        x, y = POSICOES_8[node_id]
        no = sessao.add_node(node_id, name=f'pl-s{session_id}-{nome}-{rotulo}', _type=NodeType.DOCKER,
                             position=Position(x=x, y=y), image=imagem)
        sessao.add_link(node1=no, node2=switch, iface1=Interface(id=0, name='eth0', mac=mac, ip4=ip, ip4_mask=24 if ip else None),
                        iface2=Interface(id=porta, name=f'eth{porta}'))
    return {n: r for n, (r, _, _) in NOS_8.items()}


def _preparar_servicos(core, session_id):
    comandos = [(n, 'ip -4 route flush default') for n in NOS_8]
    comandos += [(n, 'sysctl -w net.ipv4.ip_forward=0') for n in NOS_8]
    comandos += [(n, 'ip -4 route replace default via 192.168.40.1 dev eth0') for n in (2, 6, 7, 8)]
    comandos += [(1, 'ip -4 addr flush dev eth0'), (1, _resolv()), (2, _resolv('192.168.40.9')), (3, _resolv()),
                 (6, DNSMASQ_8), (3, UDHCPC)]
    return comandos


# Lab 10: VLANs do Lab 9, um roteador com uma interface por VLAN (e DHCP/DNS das duas) e o servidor intranet atrás dele.
DESAFIO = 'desafio-rede-da-empresa'
SWITCH_10, ROTEADOR_10, INTRANET_10 = 3, 4, 8
PCS_10 = {1: ('pc-v1', 0, '02:16:3e:10:00:11', None), 2: ('pc-v2', 1, '02:16:3e:10:00:12', '192.168.10.12'),
          6: ('pc-f1', 2, '02:16:3e:20:00:21', None), 7: ('pc-f2', 3, '02:16:3e:20:00:22', '192.168.20.22')}
VLANS_10 = {'eth0': 10, 'eth1': 20, 'eth2': 20, 'eth3': 20, 'eth4': 10, 'eth5': 20}  # eth1 (PC V2) na VLAN errada
POSICOES_10 = {1: (90, 70), 2: (90, 230), 3: (330, 150), 4: (520, 150), 8: (700, 150), 6: (330, 300), 7: (520, 300)}
DNSMASQ_10 = ('dnsmasq --interface=eth0 --interface=eth1 --bind-interfaces --no-resolv --no-hosts --domain=empresa.local '
              '--local=/empresa.local/ --dhcp-range=192.168.10.100,192.168.10.150,255.255.255.0,1h '
              '--dhcp-range=192.168.20.100,192.168.20.150,255.255.255.0,1h --dhcp-host=02:16:3e:10:00:11,192.168.10.11 '
              '--host-record=intranet.empresa.local,192.168.60.20 '
              '--dhcp-leasefile=/tmp/dnsmasq.leases --pid-file=/tmp/dnsmasq.pid --no-ping')


def _construir_desafio(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    rotulos = {SWITCH_10: 'switch', ROTEADOR_10: 'roteador', INTRANET_10: 'intranet', **{n: p[0] for n, p in PCS_10.items()}}
    nos = {}
    for node_id, rotulo in rotulos.items():
        x, y = POSICOES_10[node_id]
        nos[node_id] = sessao.add_node(node_id, name=f'pl-s{session_id}-{nome}-{rotulo}', _type=NodeType.DOCKER,
                                       position=Position(x=x, y=y), image=imagem)
    for node_id, (_, porta, mac, ip) in PCS_10.items():
        sessao.add_link(node1=nos[node_id], node2=nos[SWITCH_10],
                        iface1=Interface(id=0, name='eth0', mac=mac, ip4=ip, ip4_mask=24 if ip else None),
                        iface2=Interface(id=porta, name=f'eth{porta}'))
    for iface, porta, ip in ((0, 4, '192.168.10.1'), (1, 5, '192.168.20.1')):
        sessao.add_link(node1=nos[ROTEADOR_10], node2=nos[SWITCH_10], iface1=Interface(id=iface, name=f'eth{iface}', ip4=ip, ip4_mask=24),
                        iface2=Interface(id=porta, name=f'eth{porta}'))
    sessao.add_link(node1=nos[ROTEADOR_10], node2=nos[INTRANET_10], iface1=Interface(id=2, name='eth2', ip4='192.168.60.1', ip4_mask=24),
                    iface2=Interface(id=0, name='eth0', ip4='192.168.60.20', ip4_mask=24))
    return rotulos


def _preparar_desafio(core, session_id):
    todos = (*PCS_10, SWITCH_10, ROTEADOR_10, INTRANET_10)
    comandos = [(n, 'ip -4 route flush default') for n in todos]
    comandos += [(n, 'sysctl -w net.ipv4.ip_forward=0') for n in (*PCS_10, SWITCH_10, INTRANET_10)]
    comandos += [(SWITCH_10, 'ip link add br0 type bridge vlan_filtering 1')]
    for porta, vlan in VLANS_10.items():
        comandos += [(SWITCH_10, f'ip -4 addr flush dev {porta}'), (SWITCH_10, f'ip link set {porta} master br0'),
                     (SWITCH_10, f'ip link set {porta} up'), (SWITCH_10, f'bridge vlan add dev {porta} vid {vlan} pvid untagged'),
                     (SWITCH_10, f'bridge vlan del dev {porta} vid 1')]
    comandos.append((SWITCH_10, 'ip link set br0 up'))
    comandos += [(ROTEADOR_10, 'sysctl -w net.ipv4.ip_forward=1'), (ROTEADOR_10, 'sysctl -w net.ipv4.conf.all.rp_filter=0'),
                 # Responde ARP só pela interface do próprio endereço: um PC na VLAN errada não aprende o gateway do outro setor.
                 (ROTEADOR_10, 'sysctl -w net.ipv4.conf.all.arp_ignore=1'),
                 (ROTEADOR_10, 'iptables -P FORWARD DROP'),
                 # Só encaminha entre as redes do laboratório; a rede de controle nunca é atravessada.
                 (ROTEADOR_10, 'iptables -A FORWARD -s 192.168.0.0/16 -d 192.168.0.0/16 -j ACCEPT'),
                 (ROTEADOR_10, DNSMASQ_10)]
    comandos += [(INTRANET_10, 'ip -4 route replace default via 192.168.60.254 dev eth0'),
                 (2, 'ip -4 route replace default via 192.168.10.1 dev eth0'), (2, _resolv('192.168.10.1')),
                 (7, 'ip -4 route replace default via 192.168.20.1 dev eth0'), (7, _resolv('192.168.20.9')),
                 (6, 'ip -4 addr flush dev eth0'), (6, _resolv()), (1, _resolv()), (1, UDHCPC)]
    return comandos


def _construir_dois_roteadores(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    nomes = {1: 'pc-a', 2: 'pc-b', 3: 'switch-a', 4: 'switch-b', 5: 'r1', 6: 'r2'}
    nos = {}
    for node_id, rotulo in nomes.items():
        switch = node_id in (3, 4)
        x, y = POSICOES_7[node_id]
        kwargs = {'name': f'pl-s{session_id}-{nome}-{rotulo}', '_type': NodeType.SWITCH if switch else NodeType.DOCKER,
                  'position': Position(x=x, y=y)}
        if not switch:
            kwargs['image'] = imagem
        nos[node_id] = sessao.add_node(node_id, **kwargs)
    iface = lambda i, ip=None, mascara=None: Interface(id=i, name=f'eth{i}', ip4=ip, ip4_mask=mascara)  # noqa: E731
    sessao.add_link(node1=nos[1], node2=nos[3], iface1=iface(0, '192.168.10.10', 24), iface2=iface(0))
    sessao.add_link(node1=nos[5], node2=nos[3], iface1=iface(0, '192.168.10.1', 24), iface2=iface(1))
    sessao.add_link(node1=nos[5], node2=nos[6], iface1=iface(1, '10.0.0.1', 30), iface2=iface(1, '10.0.0.2', 30))
    sessao.add_link(node1=nos[6], node2=nos[4], iface1=iface(0, '192.168.20.1', 24), iface2=iface(0))
    sessao.add_link(node1=nos[2], node2=nos[4], iface1=iface(0, '192.168.20.10', 24), iface2=iface(1))
    return {n: r for n, r in nomes.items() if n not in (3, 4)}


def _preparar_dois_roteadores(core, session_id):
    comandos = [(n, 'ip -4 route flush default') for n in (1, 2, 5, 6)]
    comandos += [(n, 'sysctl -w net.ipv4.ip_forward=0') for n in (1, 2)]
    for r in (5, 6):
        comandos += [(r, 'sysctl -w net.ipv4.ip_forward=1'), (r, 'sysctl -w net.ipv4.conf.all.rp_filter=0'),
                     (r, 'iptables -P FORWARD DROP')]
        # Só encaminha entre as redes do laboratório; a rede de controle nunca é atravessada.
        for origem in ('192.168.0.0/16', '10.0.0.0/30'):
            for destino in ('192.168.0.0/16', '10.0.0.0/30'):
                comandos.append((r, f'iptables -A FORWARD -s {origem} -d {destino} -j ACCEPT'))
    comandos += [(1, 'ip -4 route replace default via 192.168.10.1 dev eth0'),
                 (2, 'ip -4 route replace default via 192.168.20.1 dev eth0')]
    return comandos


# Lab 2: uma sala com um switch do CORE e três PCs, sem roteador. O PC 2 chega sem endereço e o PC 3 com o prefixo
# errado (/28), o chamado do laboratório.
PRIMEIRA_LAN = 'primeira-lan'
SWITCH_2 = 4
PCS_2 = {1: ('pc-1', '192.168.10.10', 24), 2: ('pc-2', None, None), 3: ('pc-3', '192.168.10.40', 28)}
POSICOES_2 = {1: (120, 70), 2: (120, 230), 3: (560, 150), 4: (340, 150)}


def _construir_primeira_lan(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    x, y = POSICOES_2[SWITCH_2]
    switch = sessao.add_node(SWITCH_2, name=f'pl-s{session_id}-{nome}-switch', _type=NodeType.SWITCH, position=Position(x=x, y=y))
    for porta, (node_id, (rotulo, ip, prefixo)) in enumerate(PCS_2.items()):
        x, y = POSICOES_2[node_id]
        no = sessao.add_node(node_id, name=f'pl-s{session_id}-{nome}-{rotulo}', _type=NodeType.DOCKER,
                             position=Position(x=x, y=y), image=imagem)
        sessao.add_link(node1=no, node2=switch, iface1=Interface(id=0, name='eth0', ip4=ip, ip4_mask=prefixo),
                        iface2=Interface(id=porta, name=f'eth{porta}'))
    return {n: r for n, (r, _, _) in PCS_2.items()}


def _preparar_primeira_lan(core, session_id):
    comandos = [(n, 'ip -4 route flush default') for n in PCS_2]
    comandos += [(n, 'sysctl -w net.ipv4.ip_forward=0') for n in PCS_2]
    return comandos + [(2, 'ip -4 addr flush dev eth0')]


# Labs 8 e 10: a imagem do gateway mais o dnsmasq (servidor DHCP e DNS); fonte em images/pinglevel-servicos.
IMAGEM_SERVICOS = 'pinglevel/servicos:0.1'
# Demonstração "Suporte remoto": a dos serviços mais o cliente SSH e o recebedor da impressora (images/pinglevel-suporte).
IMAGEM_SUPORTE = 'pinglevel/suporte:0.1'


def imagem(laboratorio_id, padrao):
    if laboratorio_id == SUPORTE:
        return IMAGEM_SUPORTE
    return IMAGEM_SERVICOS if laboratorio_id in (SERVICOS, DESAFIO) else padrao


# Demonstração "Suporte remoto" (cenarios/suporte_remoto.py): dois prédios, cada um com um switch do CORE, e um roteador.
SUPORTE = 'suporte-remoto'
POSICOES_S = {10: (220, 260), 11: (620, 260), 5: (420, 80), 1: (80, 420), 2: (180, 420), 3: (280, 420), 4: (380, 420),
              6: (480, 420), 7: (580, 420), 8: (680, 420), 9: (780, 420)}
# A impressora atende uma página web na porta 80 (estado e POST /imprimir; cada folha vai para /tmp/folhas). O script
# fica em images/pinglevel-suporte e é instalado ao preparar o ambiente, sem mudar a imagem.
PAGINA_IMPRESSORA = base64.b64encode((Path(__file__).resolve().parents[2] / 'images/pinglevel-suporte/pagina-impressora.sh')
                                     .read_bytes()).decode()
ESCUTAR_IMPRESSORA = (f'echo {PAGINA_IMPRESSORA} | base64 -d > /usr/local/bin/pagina-impressora && chmod 755 /usr/local/bin/pagina-impressora'
                      ' && (setsid nc -lk -p 80 -e /usr/local/bin/pagina-impressora >/dev/null 2>&1 </dev/null &)')


def _construir_suporte(sessao, *, session_id, nome, imagem, Interface, NodeType, Position):
    from laboratorios.cenarios import suporte_remoto as c
    nos, portas = {}, {}
    for node_id, (rotulo, _) in c.SWITCHES.items():
        x, y = POSICOES_S[node_id]
        nos[node_id] = sessao.add_node(node_id, name=f'pl-s{session_id}-{nome}-{rotulo}', _type=NodeType.SWITCH,
                                       position=Position(x=x, y=y))
        portas[node_id] = 0
    switch_do = {setor: node_id for node_id, (_, setor) in c.SWITCHES.items()}
    rotulos = {}
    for chave, n in c.NOS.items():
        x, y = POSICOES_S[n['no']]
        nos[n['no']] = sessao.add_node(n['no'], name=f"pl-s{session_id}-{nome}-{n['host']}", _type=NodeType.DOCKER,
                                       position=Position(x=x, y=y), image=imagem)
        rotulos[n['no']] = n['host']

    def ligar(node_id, iface, setor, ip):
        switch = switch_do[setor]
        sessao.add_link(node1=nos[node_id], node2=nos[switch],
                        iface1=Interface(id=iface, name=f'eth{iface}', ip4=ip, ip4_mask=24),
                        iface2=Interface(id=portas[switch], name=f'eth{portas[switch]}'))
        portas[switch] += 1

    ligar(c.NOS['roteador']['no'], 0, 'a', c.GW['a'])
    ligar(c.NOS['roteador']['no'], 1, 'b', c.GW['b'])
    for chave, n in c.NOS.items():
        if 'ip' in n:
            ligar(n['no'], 0, n['setor'], n['ip'])
    return rotulos


def _preparar_suporte(core, session_id):
    from laboratorios.cenarios import suporte_remoto as c
    roteador = c.NOS['roteador']['no']
    comandos = [(n['no'], 'ip -4 route flush default') for n in c.NOS.values()]
    comandos += [(n['no'], 'sysctl -w net.ipv4.ip_forward=0') for n in c.NOS.values() if n['tipo'] != 'roteador']
    comandos += [(roteador, 'sysctl -w net.ipv4.ip_forward=1'), (roteador, 'sysctl -w net.ipv4.conf.all.rp_filter=0'),
                 (roteador, 'iptables -P FORWARD DROP'),
                 # Só encaminha entre os dois prédios; a rede de controle nunca é atravessada.
                 (roteador, 'iptables -A FORWARD -s 192.168.0.0/16 -d 192.168.0.0/16 -j ACCEPT')]
    for chave, n in c.NOS.items():
        if 'ip' in n:
            comandos.append((n['no'], f"ip -4 route replace default via {c.INICIAL[chave]['rota_padrao']} dev eth0"))
    comandos.append((c.NOS['impressora']['no'], ESCUTAR_IMPRESSORA))
    return comandos


def construir(sessao, laboratorio_id, *, session_id, nome, imagem, Interface, NodeType, Position):
    if laboratorio_id == PRIMEIRA_LAN:
        return _construir_primeira_lan(sessao, session_id=session_id, nome=nome, imagem=imagem,
                                       Interface=Interface, NodeType=NodeType, Position=Position)
    if laboratorio_id == LAN:
        return _construir_lan(sessao, session_id=session_id, nome=nome, imagem=imagem,
                              Interface=Interface, NodeType=NodeType, Position=Position)
    if laboratorio_id == SERVICOS:
        return _construir_servicos(sessao, session_id=session_id, nome=nome, imagem=imagem,
                                   Interface=Interface, NodeType=NodeType, Position=Position)
    if laboratorio_id == DESAFIO:
        return _construir_desafio(sessao, session_id=session_id, nome=nome, imagem=imagem,
                                  Interface=Interface, NodeType=NodeType, Position=Position)
    if laboratorio_id == SUPORTE:
        return _construir_suporte(sessao, session_id=session_id, nome=nome, imagem=imagem,
                                  Interface=Interface, NodeType=NodeType, Position=Position)
    if laboratorio_id == DOIS_ROTEADORES:
        return _construir_dois_roteadores(sessao, session_id=session_id, nome=nome, imagem=imagem,
                                          Interface=Interface, NodeType=NodeType, Position=Position)
    switches, pcs, interfaces = TOPOLOGIAS[laboratorio_id]
    nos, portas = {}, {s: 0 for s in switches}

    def adicionar(node_id, rotulo, switch=False):
        x, y = POSICOES[node_id]
        kwargs = {'name': f'pl-s{session_id}-{nome}-{rotulo}', '_type': NodeType.SWITCH if switch else NodeType.DOCKER,
                  'position': Position(x=x, y=y)}
        if not switch:
            kwargs['image'] = imagem
        nos[node_id] = sessao.add_node(node_id, **kwargs)

    for node_id, rotulo in switches.items():
        adicionar(node_id, rotulo, switch=True)
    adicionar(ROTEADOR, 'roteador')
    for node_id, (rotulo, _, _) in pcs.items():
        adicionar(node_id, rotulo)

    def ligar(node_id, iface_id, switch, endereco):
        ip, mascara = endereco.split('/')
        sessao.add_link(node1=nos[node_id], node2=nos[switch],
            iface1=Interface(id=iface_id, name=f'eth{iface_id}', ip4=ip, ip4_mask=int(mascara)),
            iface2=Interface(id=portas[switch], name=f'eth{portas[switch]}'))
        portas[switch] += 1

    for nome_iface, switch, endereco in interfaces:
        ligar(ROTEADOR, int(nome_iface[3:]), switch, endereco)
    for node_id, (_, switch, endereco) in pcs.items():
        ligar(node_id, 0, switch, endereco)
    return {ROTEADOR: 'roteador', **{node_id: rotulo for node_id, (rotulo, _, _) in pcs.items()}}


def preparar(core, session_id, laboratorio_id):
    """Executa exclusivamente pela API do nó da sessão, nunca no host. iptables é pré-requisito da imagem."""
    if laboratorio_id == PRIMEIRA_LAN:
        comandos = _preparar_primeira_lan(core, session_id)
    elif laboratorio_id == LAN:
        comandos = _preparar_lan(core, session_id)
    elif laboratorio_id == SERVICOS:
        comandos = _preparar_servicos(core, session_id)
    elif laboratorio_id == DESAFIO:
        comandos = _preparar_desafio(core, session_id)
    elif laboratorio_id == DOIS_ROTEADORES:
        comandos = _preparar_dois_roteadores(core, session_id)
    elif laboratorio_id == SUPORTE:
        comandos = _preparar_suporte(core, session_id)
    else:
        _, pcs, _ = TOPOLOGIAS[laboratorio_id]
        rede = REDE[laboratorio_id]
        comandos = [(node, 'ip -4 route flush default') for node in [ROTEADOR, *pcs]]
        comandos += [(node, 'sysctl -w net.ipv4.ip_forward=0') for node in pcs]
        comandos += [
            (ROTEADOR, 'sysctl -w net.ipv4.ip_forward=1'),
            (ROTEADOR, 'sysctl -w net.ipv4.conf.all.rp_filter=0'),
            # Só encaminha entre os setores do laboratório; a rede de controle nunca é atravessada.
            (ROTEADOR, 'iptables -P FORWARD DROP'),
            (ROTEADOR, f'iptables -A FORWARD -s {rede} -d {rede} -j ACCEPT'),
        ]
        comandos += PREPARO[laboratorio_id]
    for node, comando in comandos:
        codigo, _ = core.node_command(session_id, node, comando, wait=True, shell=True)
        if codigo != 0:
            raise RuntimeError(f'Preparação da topologia de setores não confirmada no nó {node}; sessão não liberada.')
