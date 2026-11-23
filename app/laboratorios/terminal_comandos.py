"""Interpretação estrita do terminal do Lab4.

O texto digitado nunca é enviado a um shell: só formas conhecidas de `ip` e `ping` são reconhecidas e o
comando executado é montado aqui, com endereços canônicos validados por `ipaddress`. Somente a interface
eth0 de cada computador pode ser lida ou alterada; a rede de controle do laboratório fica fora de alcance.
"""
import ipaddress
import re
from dataclasses import dataclass

CONTROLE = ipaddress.IPv4Network('172.30.0.0/16')
TAMANHO_MAXIMO = 100


class ErroComando(ValueError):
    pass


@dataclass(frozen=True)
class Comando:
    tipo: str          # ver-enderecos, ver-rotas, ver-vizinhos, ver-link, ver-fdb, ver-vlans, ver-dns, consultar-dns,
                       # pedir-dhcp, adicionar-*, remover-*, ping
    executar: str      # comando montado pelo servidor
    altera: bool       # muda a configuração do computador
    alvo: str = ''     # endereço, rede ou destino envolvido
    interface: str = 'eth0'


def _ipv4(texto, oque):
    if re.fullmatch(r'[0-9.]+', texto) and re.search(r'(^|\.)0[0-9]', texto):
        raise ErroComando(f'Escreva o {oque} sem zeros à esquerda em cada parte.')
    try:
        ip = ipaddress.IPv4Address(texto)
    except ValueError as erro:
        raise ErroComando(f'"{texto}" não é um {oque} IPv4 válido.') from erro
    if str(ip) != texto:
        raise ErroComando(f'Escreva o {oque} sem zeros à esquerda, como {ip}.')
    if ip in CONTROLE:
        raise ErroComando('Esse endereço pertence à rede de controle do laboratório e não pode ser usado.')
    if ip.is_loopback or ip.is_multicast or ip.is_unspecified or ip.is_link_local or ip.is_reserved:
        raise ErroComando(f'{ip} é um endereço especial e não serve para este laboratório.')
    return ip


def _interface(texto, em_uso):
    if '/' not in texto:
        raise ErroComando('Informe o endereço com o prefixo, por exemplo 192.168.10.50/24.')
    endereco, prefixo = texto.split('/', 1)
    ip = _ipv4(endereco, 'endereço')
    if not prefixo.isdigit() or not 8 <= int(prefixo) <= 30:
        raise ErroComando('Use um prefixo entre /8 e /30.')
    interface = ipaddress.IPv4Interface(f'{ip}/{int(prefixo)}')
    if interface.network.overlaps(CONTROLE):
        raise ErroComando('Essa rede se sobrepõe à rede de controle do laboratório. Escolha outra.')
    if str(ip) in em_uso:
        raise ErroComando(f'{ip} já está em uso por outro equipamento da topologia. Escolha um endereço livre.')
    if ip in (interface.network.network_address, interface.network.broadcast_address):
        raise ErroComando(f'{ip} é o endereço de rede ou de broadcast de {interface.network} e não identifica um host.')
    return interface


def _exigir_interface(resto, interfaces):
    if len(resto) == 2 and resto[0] == 'dev' and resto[1] in interfaces:
        return resto[1]
    if not resto:
        raise ErroComando(f'Indique a interface no final do comando: dev {interfaces[0]}.')
    if resto[:1] == ['dev'] and len(resto) == 2:
        if interfaces == ('eth0',):
            raise ErroComando(f'Este computador só tem a eth0. A {resto[1]} é de outro equipamento: confira no prompt em qual '
                              'aba você está e abra a do equipamento certo.')
        raise ErroComando(f"Este equipamento tem as interfaces {', '.join(interfaces)}.")
    raise ErroComando(f'Depois do endereço, informe apenas a interface: dev {interfaces[0]}.')


def _rede(texto):
    if '/' not in texto:
        raise ErroComando('Informe a rede de destino com o prefixo, por exemplo 192.168.20.0/24.')
    endereco, prefixo = texto.split('/', 1)
    ip = _ipv4(endereco, 'endereço de rede')
    if not prefixo.isdigit() or not 8 <= int(prefixo) <= 30:
        raise ErroComando('Use um prefixo entre /8 e /30.')
    rede = ipaddress.IPv4Network(f'{ip}/{int(prefixo)}', strict=False)
    if rede.network_address != ip:
        raise ErroComando(f'{texto} não é um endereço de rede: a rota usa {rede}.')
    if rede.overlaps(CONTROLE):
        raise ErroComando('Essa rede se sobrepõe à rede de controle do laboratório. Escolha outra.')
    return rede


def _rota_estatica(resto, interfaces):
    """ip route add <rede>/<prefixo> via <próximo salto> [dev <if>] e ip route del <rede>/<prefixo> [via <ip>]."""
    acao, alvo, extra = resto[0], resto[1], resto[2:]
    if alvo == 'default':
        raise ErroComando('Neste roteador use rotas para redes, como ip route add 192.168.20.0/24 via <próximo salto>.')
    rede = _rede(alvo)
    via = None
    if extra[:1] == ['via'] and len(extra) >= 2:
        via = _ipv4(extra[1], 'próximo salto')
        extra = extra[2:]
    if acao == 'add' and via is None:
        raise ErroComando('Informe o próximo salto: ip route add <rede>/<prefixo> via <endereço>.')
    dev = ''
    if extra:
        if len(extra) != 2 or extra[0] != 'dev' or extra[1] not in interfaces:
            raise ErroComando(f"Depois do próximo salto, só a interface: dev {' ou '.join(interfaces)}.")
        dev = f' dev {extra[1]}'
    executar = f"ip route {acao} {rede}" + (f' via {via}' if via else '') + dev
    return Comando('adicionar-rota-rede' if acao == 'add' else 'remover-rota-rede', executar, True, str(rede), 'rotas')


def _vid(texto):
    if not texto.isdigit() or not 1 <= int(texto) <= 4094 or str(int(texto)) != texto:
        raise ErroComando('O número da VLAN (vid) vai de 1 a 4094.')
    return int(texto)


def _bridge(t, portas):
    """Switch do Lab 9 (bridge Linux com VLANs): ver portas, tabela MAC e VLANs; mudar a VLAN de uma porta."""
    objeto, resto = (t[1], t[2:]) if len(t) > 1 else ('', [])
    if objeto == 'fdb' and resto in ([], ['show']):
        return Comando('ver-fdb', 'bridge fdb show br br0', False)
    if objeto == 'link' and resto in ([], ['show']):
        return Comando('ver-portas', 'bridge link show', False)
    if objeto != 'vlan':
        raise ErroComando('Com bridge, use: bridge link show, bridge fdb show ou bridge vlan show.')
    if resto in ([], ['show']):
        return Comando('ver-vlans', 'bridge vlan show', False)
    if resto[:1] not in (['add'], ['del']) or resto[1:2] != ['dev'] or len(resto) < 5 or resto[3] != 'vid':
        raise ErroComando('Use: bridge vlan add dev <porta> vid <número> pvid untagged, ou bridge vlan del dev <porta> vid <número>.')
    porta = resto[2]
    if porta not in portas:
        raise ErroComando(f"As portas deste switch são {', '.join(portas)}.")
    vid = _vid(resto[4])
    opcoes = resto[5:]
    if resto[0] == 'del':
        if opcoes:
            raise ErroComando('Para remover, basta: bridge vlan del dev <porta> vid <número>.')
        return Comando('remover-vlan', f'bridge vlan del dev {porta} vid {vid}', True, str(vid), porta)
    if len(set(opcoes)) != len(opcoes) or set(opcoes) - {'pvid', 'untagged'}:
        raise ErroComando('Depois do vid, só as opções pvid e untagged (porta de acesso).')
    extra = ''.join(f' {o}' for o in ('pvid', 'untagged') if o in opcoes)
    return Comando('adicionar-vlan', f'bridge vlan add dev {porta} vid {vid}{extra}', True, str(vid), porta)


def _nome(texto, dominio):
    """Nomes da empresa (Labs 8 e 10): só os do domínio do laboratório, para a consulta nunca sair da topologia."""
    if not re.fullmatch(r'[a-z0-9]+(\.[a-z0-9]+)*', texto):
        raise ErroComando(f'"{texto}" não é um nome válido.')
    if '.' not in texto:
        raise ErroComando(f'Use o nome completo: {texto}.{dominio}.')
    if texto == dominio or not texto.endswith('.' + dominio):
        raise ErroComando(f'Neste laboratório só existem os nomes da empresa, terminados em .{dominio}.')
    return texto


def _servicos(t, dominio, interfaces):
    """DHCP e DNS nos PCs (Labs 8 e 10): pedir endereço, ler o servidor DNS configurado e consultar um nome."""
    # O comando ensinado é o dhclient, como no livro e na faculdade. Os nós (Alpine) não têm o dhclient: o pedido é
    # feito pelo udhcpc, o cliente DHCP do BusyBox, e a saída real aparece com as linhas "udhcpc:".
    if t[0] == 'dhclient':
        if t[1:] in ([interfaces[0]], ['-v', interfaces[0]]):
            return Comando('pedir-dhcp', f'udhcpc -i {interfaces[0]} -n -q -t 3 -T 1 2>&1', True)
        if len(t) == 1:
            raise ErroComando(f'Indique a interface: dhclient {interfaces[0]}.')
        raise ErroComando(f'Use apenas: dhclient {interfaces[0]}.')
    if t[0] == 'udhcpc':
        if t[1:] == ['-i', interfaces[0]]:
            # -n: desiste se ninguém responder; -q: sai com a concessão (a configuração fica na interface).
            return Comando('pedir-dhcp', f'udhcpc -i {interfaces[0]} -n -q -t 3 -T 1 2>&1', True)
        if len(t) == 1 or t[1:] == [interfaces[0]]:
            raise ErroComando(f'Indique a interface depois de -i: udhcpc -i {interfaces[0]}.')
        raise ErroComando(f'Use apenas: udhcpc -i {interfaces[0]}.')
    if t[0] == 'cat':
        if t[1:] == ['/etc/resolv.conf']:
            return Comando('ver-dns', 'cat /etc/resolv.conf', False)
        raise ErroComando('Aqui o cat só lê o arquivo dos servidores DNS: cat /etc/resolv.conf.')
    if len(t) != 2:
        raise ErroComando(f'Use {t[0]} seguido apenas do nome, por exemplo: {t[0]} intranet.{dominio}.')
    nome = _nome(t[1], dominio)
    if t[0] == 'nslookup':
        return Comando('consultar-dns', f'nslookup {nome}', False, nome)
    return Comando('ping', f'ping -n -c 2 -W 1 {nome}', False, nome)


def interpretar(texto, em_uso=(), interfaces=('eth0',), rotas=True, tipo='pc', servicos=None):
    """interfaces: as que este equipamento mostra e aceita. rotas: True (PC: rota padrão), False (roteador sem
    rotas, Labs 5 e 6) ou 'estaticas' (roteador do Lab 7: rotas para redes com próximo salto). tipo 'switch' (Lab 9):
    só os comandos bridge, nas portas indicadas em interfaces. servicos: o domínio da empresa (Labs 8 e 10), que
    libera dhclient (ou udhcpc), cat /etc/resolv.conf, nslookup e ping por nome."""
    interfaces = tuple(interfaces)
    if not isinstance(texto, str) or not texto.strip():
        raise ErroComando('Digite um comando.')
    if len(texto) > TAMANHO_MAXIMO:
        raise ErroComando('Comando longo demais para este laboratório.')
    if not re.fullmatch(r'[a-z0-9 ./\t' + ('-' if servicos else '') + ']+', texto.strip()):
        raise ErroComando('Use apenas os comandos do laboratório, com letras minúsculas, números, pontos e barras.')
    t = texto.split()
    if servicos and (t[0] in ('udhcpc', 'dhclient', 'cat', 'nslookup')
                     or (t[0] == 'ping' and len(t) == 2 and re.search(r'[a-z]', t[1]))):
        return _servicos(t, servicos, interfaces)
    if tipo == 'switch':
        if t[0] == 'bridge':
            return _bridge(t, interfaces)
        if t[0] == 'ping':
            raise ErroComando('O switch não tem endereço IP: teste a comunicação a partir dos computadores.')
        if t[0] == 'arp' or (t[0] == 'ip' and t[1:2] and t[1] in ('n', 'neigh', 'neighbor', 'neighbour')):
            raise ErroComando('O switch não tem tabela ARP, porque não usa IP. A tabela dele é a tabela MAC: bridge fdb show.')
        raise ErroComando('No switch, use os comandos bridge: bridge link show, bridge fdb show e bridge vlan show.')
    if t[0] == 'bridge':
        raise ErroComando('Os comandos bridge são do switch. Abra a aba do switch.')
    if t[0] == 'ping':
        if len(t) != 2:
            raise ErroComando('Use ping seguido apenas do endereço de destino, sem opções.')
        ip = _ipv4(t[1], 'endereço de destino')
        return Comando('ping', f'ping -n -c 2 -W 1 {ip}', False, str(ip))
    if t[0] != 'ip' or len(t) < 2:
        if servicos:
            raise ErroComando('Comando não disponível neste laboratório. Use ip, ping, dhclient, nslookup ou cat /etc/resolv.conf.')
        raise ErroComando('Comando não disponível neste laboratório. Use ip ou ping.')
    objeto, resto = t[1], t[2:]
    if objeto in ('n', 'neigh', 'neighbor', 'neighbour'):
        if resto in ([], ['show']) or resto in (['show', 'dev', 'eth0'], ['show', 'eth0']):
            return Comando('ver-vizinhos', 'ip neigh show dev eth0', False)
        raise ErroComando('Para ver a tabela ARP (vizinhos), use: ip neigh show.')
    if objeto in ('l', 'link'):
        if resto in ([], ['show']) or resto in (['show', 'dev', 'eth0'], ['show', 'eth0']):
            return Comando('ver-link', 'ip link show dev eth0', False)
        raise ErroComando('Para ver a interface e o endereço MAC, use: ip link show.')
    if objeto in ('a', 'addr', 'address'):
        if resto in ([], ['show']):
            return Comando('ver-enderecos', '; '.join(f'ip addr show dev {i}' for i in interfaces), False)
        if resto[:1] == ['show'] and resto[-1] in interfaces and resto[1:-1] in ([], ['dev']):
            return Comando('ver-enderecos', f'ip addr show dev {resto[-1]}', False, interface=resto[-1])
        if resto[:1] in (['add'], ['del']) and len(resto) >= 2:
            endereco = _interface(resto[1], em_uso if resto[0] == 'add' else ())
            nome = _exigir_interface(resto[2:], interfaces)
            acao = 'adicionar-endereco' if resto[0] == 'add' else 'remover-endereco'
            return Comando(acao, f'ip addr {resto[0]} {endereco} dev {nome}', True, str(endereco), nome)
        raise ErroComando('Com ip addr, use show, add ou del. Exemplo: ip addr show.')
    if objeto in ('r', 'route'):
        if resto in ([], ['show']):
            return Comando('ver-rotas', 'ip -4 route show', False)
        if resto[:1] in (['add'], ['del']) and not rotas:
            raise ErroComando('Neste roteador as rotas vêm das próprias interfaces: configure só os endereços.')
        if resto[:1] in (['add'], ['del']) and rotas == 'estaticas':
            if len(resto) < 2:
                raise ErroComando('Use: ip route add <rede>/<prefixo> via <próximo salto>.')
            return _rota_estatica(resto, interfaces)
        if resto[:2] == ['add', 'default']:
            if len(resto) < 4 or resto[2] != 'via' or resto[4:] not in ([], ['dev', 'eth0']):
                raise ErroComando('Para a rota padrão, use: ip route add default via <gateway>.')
            gateway = _ipv4(resto[3], 'gateway')
            return Comando('adicionar-rota', f'ip route add default via {gateway} dev eth0', True, str(gateway))
        if resto[:2] == ['del', 'default']:
            if resto[2:] == []:
                return Comando('remover-rota', 'ip route del default dev eth0', True)
            if len(resto) == 4 and resto[2] == 'via':
                gateway = _ipv4(resto[3], 'gateway')
                return Comando('remover-rota', f'ip route del default via {gateway} dev eth0', True, str(gateway))
            raise ErroComando('Para remover a rota padrão, use: ip route del default.')
        if resto[:1] in (['add'], ['del']):
            raise ErroComando('Neste laboratório só a rota padrão (default) pode ser alterada.')
        raise ErroComando('Com ip route, use show, add default ou del default.')
    raise ErroComando('Neste laboratório use ip addr, ip route ou ping.')


def filtrar_rotas(saida, interfaces=('eth0',)):
    """Remove da saída de `ip route show` as rotas da rede de controle e de interfaces fora do laboratório."""
    linhas = []
    for linha in saida.splitlines():
        rede = linha.split(' ', 1)[0]
        try:
            if ipaddress.IPv4Network(rede).overlaps(CONTROLE):
                continue
        except ValueError:
            pass
        dev = re.search(r'\bdev (\S+)', linha)
        if dev and dev[1] not in interfaces:
            continue
        linhas.append(linha)
    return '\n'.join(linhas)


def filtrar_bridge(saida, portas):
    """Mantém na saída de bridge só as portas do switch (e a própria br0); a rede de controle fica de fora."""
    linhas, manter = [], False
    for linha in saida.splitlines():
        if not linha.strip():
            continue
        if linha[0].isspace():
            if manter:
                linhas.append(linha)
            continue
        primeiro = linha.split()[0].split('@')[0].rstrip(':')
        if linha.startswith('port'):
            manter = True
        elif re.fullmatch(r'\d+', primeiro):  # bridge link: "4: eth0@if5: ..."
            nome = linha.split()[1].split('@')[0].rstrip(':')
            manter = nome in portas
        else:
            manter = primeiro in (*portas, 'br0')
        if manter:
            linhas.append(linha)
    return '\n'.join(linhas)


def filtrar_fdb(saida, portas, macs=None):
    """Tabela MAC aprendida: só entradas dinâmicas das portas do switch, sem as fixas do próprio equipamento. Com
    macs, só os equipamentos da topologia: as pontas das ligações criadas pelo CORE no servidor também aparecem."""
    linhas = []
    for linha in saida.splitlines():
        dev = re.search(r'\bdev (\S+)', linha)
        if macs is not None and linha.split()[:1] and linha.split()[0].lower() not in macs:
            continue
        if dev and dev[1] in portas and 'permanent' not in linha and 'self' not in linha.split():
            linhas.append(linha)
    return '\n'.join(linhas) or '(tabela vazia: o switch ainda não viu quadros nas portas)'


# Demonstração "Suporte remoto": ssh usuário@ip, exit e a página web da impressora (curl). Formas fixas, conferidas antes de
# interpretar(); o texto da folha só tem letras, números e espaços, então segue sem risco dentro do comando montado.
USUARIO_SSH = 'suporte'
SSH = re.compile(r'ssh\s+(?:([a-z_][a-z0-9_-]{0,31})@)?(\S+)')
# Impressora do Prédio A pela página web (porta 80): curl <ip> mostra o estado; curl -d "texto=..." <ip>/imprimir imprime.
CURL_PAGINA = re.compile(r'curl\s+(?:http://)?([0-9.]+)/?')
CURL_IMPRIMIR = re.compile(r'curl\s+(?:-X\s+POST\s+)?-d\s+(["\'])texto=([A-Za-z0-9À-ÿ ]{1,60})\1\s+(?:http://)?([0-9.]+)/imprimir')


def interpretar_remoto(texto):
    """('ssh', ip, usuário), ('exit',), ('pagina', ip), ('imprimir', texto, ip) ou None quando não é um desses comandos."""
    if not isinstance(texto, str):
        return None
    t = ' '.join(texto.split())
    if t in ('exit', 'logout'):
        return ('exit',)
    primeiro = t.split(' ', 1)[0]
    if primeiro == 'ssh':
        m = SSH.fullmatch(t)
        if not m:
            raise ErroComando(f'Use: ssh {USUARIO_SSH}@<endereço do computador>, por exemplo ssh {USUARIO_SSH}@192.168.20.21.')
        return ('ssh', str(_ipv4(m[2], 'endereço')), m[1] or USUARIO_SSH)
    if primeiro == 'curl':
        m = CURL_IMPRIMIR.fullmatch(t)
        if m:
            texto_folha = ' '.join(m[2].split())
            if not texto_folha:
                raise ErroComando('Escreva o texto da folha depois de texto=, entre aspas.')
            return ('imprimir', texto_folha, str(_ipv4(m[3], 'endereço da impressora')))
        m = CURL_PAGINA.fullmatch(t)
        if m:
            return ('pagina', str(_ipv4(m[1], 'endereço')))
        if ' -d ' in f'{t} ' and 'texto=' not in t:
            raise ErroComando('Faltou o nome do campo: o que vai entre aspas começa com texto=, por exemplo '
                              'curl -d "texto=sua frase" http://192.168.10.50/imprimir.')
        raise ErroComando('Use curl <endereço> para ver a página da impressora, ou curl -d "texto=sua frase" '
                          '<endereço>/imprimir para imprimir.')
    if primeiro == 'echo' or ' nc ' in f' {t} ':
        raise ErroComando('Nesta impressora, use a página web: curl -d "texto=sua frase" <endereço da impressora>/imprimir.')
    return None
