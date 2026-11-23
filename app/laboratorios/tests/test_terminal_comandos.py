import pytest
from laboratorios.terminal_comandos import ErroComando, filtrar_rotas, interpretar

EM_USO = ('192.168.10.1', '192.168.10.20', '192.168.20.1', '192.168.20.10')


@pytest.mark.parametrize('texto,executar,altera', [
    ('ip a', 'ip addr show dev eth0', False),
    ('ip addr', 'ip addr show dev eth0', False),
    ('ip address show', 'ip addr show dev eth0', False),
    ('ip addr show dev eth0', 'ip addr show dev eth0', False),
    ('  ip   r  ', 'ip -4 route show', False),
    ('ip route show', 'ip -4 route show', False),
    ('ip addr add 192.168.10.30/24 dev eth0', 'ip addr add 192.168.10.30/24 dev eth0', True),
    ('ip address add 192.168.10.30/16 dev eth0', 'ip addr add 192.168.10.30/16 dev eth0', True),
    ('ip addr del 192.168.10.30/24 dev eth0', 'ip addr del 192.168.10.30/24 dev eth0', True),
    ('ip route add default via 192.168.10.1', 'ip route add default via 192.168.10.1 dev eth0', True),
    ('ip r add default via 192.168.10.20 dev eth0', 'ip route add default via 192.168.10.20 dev eth0', True),
    ('ip route del default', 'ip route del default dev eth0', True),
    ('ip route del default via 192.168.10.1', 'ip route del default via 192.168.10.1 dev eth0', True),
    ('ping 192.168.20.10', 'ping -n -c 2 -W 1 192.168.20.10', False),
])
def test_formas_aceitas_montam_o_comando_no_servidor(texto, executar, altera):
    comando = interpretar(texto, EM_USO)
    assert comando.executar == executar and comando.altera is altera


@pytest.mark.parametrize('texto', [
    'ip a; rm -rf /', 'ping 192.168.10.20 && reboot', 'ip a | sh', 'ping $(id)', 'ip a `id`', 'ping 192.168.10.20\nid',
    "ip a 'x'", 'ip a > /tmp/x', 'ip addr add 192.168.10.30/24 dev eth0;id', 'IP A', 'ping -c 100 192.168.10.20',
    'ping -f 192.168.10.20', 'sudo ip a', 'bash', 'cat /etc/passwd', 'ip link set eth0 down', 'ip neigh flush all',
    'ip route flush table main', 'ip route add 10.0.0.0/8 via 192.168.10.1', 'ip addr flush dev eth0', 'x' * 101,
])
def test_entradas_perigosas_ou_fora_da_lista_sao_recusadas(texto):
    with pytest.raises(ErroComando):
        interpretar(texto, EM_USO)


@pytest.mark.parametrize('texto,trecho', [
    ('ip addr add 192.168.10.20/24 dev eth0', 'já está em uso'),
    ('ip addr add 192.168.10.1/24 dev eth0', 'já está em uso'),
    ('ip addr add 192.168.10.0/24 dev eth0', 'rede ou de broadcast'),
    ('ip addr add 192.168.10.255/24 dev eth0', 'rede ou de broadcast'),
    ('ip addr add 192.168.10.30/24 dev eth1', 'só tem a eth0. A eth1 é de outro equipamento'),
    ('ip addr add 192.168.10.30/24', 'dev eth0'),
    ('ip addr add 192.168.10.30 dev eth0', 'prefixo'),
    ('ip addr add 192.168.10.30/31 dev eth0', 'entre /8 e /30'),
    ('ip addr add 192.168.010.30/24 dev eth0', 'zeros à esquerda'),
    ('ip addr add 172.30.1.9/24 dev eth0', 'rede de controle'),
    ('ip addr add 172.16.0.5/12 dev eth0', 'sobrepõe à rede de controle'),
    ('ip route add default via 172.30.1.1', 'rede de controle'),
    ('ping 172.30.1.2', 'rede de controle'),
    ('ping 127.0.0.1', 'especial'),
    ('ip route add default 192.168.10.1', 'default via'),
    ('ping 999.1.1.1', 'não é um'),
])
def test_recusas_explicam_o_motivo(texto, trecho):
    with pytest.raises(ErroComando) as erro:
        interpretar(texto, EM_USO)
    assert trecho in str(erro.value)


def test_remover_endereco_nao_verifica_uso_na_topologia():
    assert interpretar('ip addr del 192.168.10.20/24 dev eth0', EM_USO).altera


def test_filtro_de_rotas_esconde_a_rede_de_controle():
    saida = ('default via 192.168.10.1 dev eth0\n172.30.4.0/24 dev eth1 proto kernel scope link src 172.30.4.1\n'
             '192.168.10.0/24 dev eth0 proto kernel scope link src 192.168.10.30')
    assert filtrar_rotas(saida) == ('default via 192.168.10.1 dev eth0\n'
                                    '192.168.10.0/24 dev eth0 proto kernel scope link src 192.168.10.30')
