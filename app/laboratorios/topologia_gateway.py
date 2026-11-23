"""Topologia de dados do Lab3. SDK injetado, sem comandos ou CORE no import."""

def construir(sessao, *, session_id, nome, imagem, Interface, NodeType, Position, chamados=False):
    """chamados (Lab4): três PCs com as configurações dos chamados; o PC Recepção entra como nó 6."""
    if chamados:
        nomes = {1: 'pc-novo', 2: 'pc-financeiro', 6: 'pc-recepcao', 4: 'servidor', 5: 'roteador'}
        posicoes = {1:(90,60),2:(90,170),6:(90,280),3:(250,170),5:(440,170),4:(660,170)}
        locais = [(1,0,'192.168.10.10',24), (2,1,'192.168.10.12',24), (5,2,'192.168.10.1',24), (6,3,'192.168.10.11',16)]
    else:
        nomes = {1: 'computador-1', 2: 'computador-2', 4: 'computador-3', 5: 'roteador'}
        posicoes = {1:(90,80),2:(90,260),3:(250,170),5:(440,170),4:(660,170)}
        locais = [(1,0,'192.168.10.10',24), (2,1,'192.168.10.20',24), (5,2,'192.168.10.1',24)]
    nos = {}
    for node_id in [n for n in [1,2,6,3,5,4] if n in posicoes]:
        switch = node_id == 3
        label = 'switch-a' if switch else nomes[node_id]
        kwargs = {'name':f'pl-s{session_id}-{nome}-{label}',
            '_type': NodeType.SWITCH if switch else NodeType.DOCKER,
            'position':Position(x=posicoes[node_id][0],y=posicoes[node_id][1])}
        if not switch: kwargs['image'] = imagem
        nos[node_id] = sessao.add_node(node_id, **kwargs)
    for node, porta, endereco, mascara in locais:
        sessao.add_link(node1=nos[node], node2=nos[3],
            iface1=Interface(id=0,name='eth0',ip4=endereco,ip4_mask=mascara),
            iface2=Interface(id=porta,name=f'eth{porta}'))
    sessao.add_link(node1=nos[5], node2=nos[4],
        iface1=Interface(id=1,name='eth1',ip4='192.168.20.1',ip4_mask=24),
        iface2=Interface(id=0,name='eth0',ip4='192.168.20.10',ip4_mask=24))
    return nomes


def preparar(core, session_id, chamados=False):
    """Executa exclusivamente pela API do nó da sessão, nunca no host.

    iptables é pré-requisito da imagem; ausência falha antes de liberar a missão.
    Rotas conectadas de controle permanecem, defaults do cenário são removidos.
    chamados (Lab4): PC Novo sem IPv4; PC Financeiro com rota padrão para um computador (192.168.10.11);
    PC Recepção com /16 e rota padrão correta.
    """
    comandos = []
    for node in [1,2,4,5,6] if chamados else [1,2,4,5]:
        comandos.append((node, 'ip -4 route flush default'))
        if node != 5:
            comandos.append((node, 'sysctl -w net.ipv4.ip_forward=0'))
    comandos.extend([
        (5, 'sysctl -w net.ipv4.ip_forward=1'),
        (5, 'sysctl -w net.ipv4.conf.all.rp_filter=0'),
        (5, 'sysctl -w net.ipv4.conf.eth0.rp_filter=0'),
        (5, 'sysctl -w net.ipv4.conf.eth1.rp_filter=0'),
        (5, 'iptables -P FORWARD DROP'),
        (5, 'iptables -A FORWARD -i eth0 -o eth1 -s 192.168.10.0/24 -d 192.168.20.0/24 -j ACCEPT'),
        (5, 'iptables -A FORWARD -i eth1 -o eth0 -s 192.168.20.0/24 -d 192.168.10.0/24 -j ACCEPT'),
        (4, 'ip -4 route replace default via 192.168.20.1 dev eth0'),
    ])
    if chamados:
        comandos.extend([
            (1, 'ip -4 addr flush dev eth0'),
            (2, 'ip -4 route replace default via 192.168.10.11 dev eth0'),
            (6, 'ip -4 route replace default via 192.168.10.1 dev eth0'),
        ])
    for node, comando in comandos:
        codigo, _ = core.node_command(session_id, node, comando, wait=True, shell=True)
        if codigo != 0:
            raise RuntimeError(f'Preparação da topologia com roteador não confirmada no nó {node}; sessão não liberada.')
