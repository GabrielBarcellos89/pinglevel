"""Captura limitada no par host da interface didática de uma sessão CORE."""
from __future__ import annotations

import json
import queue
import signal
import subprocess
import tempfile
import threading
import time
import uuid

CAMPOS = (
    'frame.number', 'frame.time_relative', 'eth.src', 'eth.dst',
    'arp.opcode', 'arp.src.proto_ipv4', 'arp.dst.proto_ipv4',
    'ip.src', 'ip.dst', 'ip.ttl', 'icmp.type', 'icmp.code', 'icmp.ident', 'icmp.seq',
)
# Labs 2 a 10: além de ARP e ICMP, as consultas DNS e a conversa DHCP (Labs 8 e 10).
CAMPOS_REDE = CAMPOS + (
    'udp.srcport', 'udp.dstport', 'dns.flags.response', 'dns.qry.name', 'dns.a', 'dhcp.option.dhcp', 'dhcp.ip.your',
)
PERFIS = {
    'arp_icmp': {'captura': 'arp or icmp', 'leitura': 'arp or icmp', 'campos': CAMPOS, 'segundos': 15, 'pacotes': 64},
    'rede': {'captura': 'arp or icmp or udp port 53 or udp port 67 or udp port 68', 'leitura': 'arp or icmp or dns or dhcp',
             'campos': CAMPOS_REDE, 'segundos': 12, 'pacotes': 50},
}
DHCP = {'1': 'DHCP Discover', '2': 'DHCP Offer', '3': 'DHCP Request', '5': 'DHCP ACK', '6': 'DHCP NAK'}


def resolver_interface(core, session_id: int, node_id: int) -> str:
    _, interfaces, links = core.get_node(session_id, node_id)
    candidatas = [i for i in interfaces if i.name == 'eth0' and i.id == 0]
    if len(candidatas) != 1 or not any(
        node_id in (l.node1_id, l.node2_id)
        and ((l.iface1 if l.node1_id == node_id else l.iface2) is not None)
        and (l.iface1 if l.node1_id == node_id else l.iface2).id == 0
        for l in links
    ):
        raise RuntimeError('Interface didática não identificada.')

    def ler_indice(campo):
        codigo, saida = core.node_command(
            session_id, node_id, f'cat /sys/class/net/eth0/{campo}',
            wait=True, shell=False,
        )
        if codigo:
            raise RuntimeError('Não foi possível identificar o par da interface.')
        return int(saida.strip())

    peer = ler_indice('iflink')
    indice_no = ler_indice('ifindex')
    host = json.loads(subprocess.check_output(
        ['ip', '-j', 'link', 'show'], text=True, timeout=5,
    ))
    pares = [i for i in host if i['ifindex'] == peer]
    if len(pares) != 1 or pares[0].get('link_index') != indice_no or not pares[0].get('master'):
        raise RuntimeError('Vínculo da interface didática não comprovado.')
    return pares[0]['ifname']


def interpretar_campos(saida: str, nomes_campos: tuple = CAMPOS) -> list[dict]:
    eventos = []
    nomes = {'1': 'ARP Request', '2': 'ARP Reply'}
    icmp = {'8': 'ICMP Echo Request', '0': 'ICMP Echo Reply', '3': 'ICMP Destino inalcançável'}
    for linha in saida.splitlines():
        valores = linha.split('\t')
        if len(valores) != len(nomes_campos):
            raise ValueError('Campos de captura inválidos.')
        campos = dict(zip(nomes_campos, valores))
        # Em erros ICMP o pacote original vem junto: o primeiro valor é o do pacote observado.
        primeiro = {k: v.split(',')[0] for k, v in campos.items()}
        arp = primeiro['arp.opcode']
        dhcp = primeiro.get('dhcp.option.dhcp', '')
        dns = primeiro.get('dns.qry.name', '')
        if arp:
            protocolo, tipo = 'ARP', nomes.get(arp, f'ARP operação {arp}')
        elif dhcp:
            protocolo, tipo = 'DHCP', DHCP.get(dhcp, f'DHCP mensagem {dhcp}')
        elif dns:
            protocolo, tipo = 'DNS', 'DNS Resposta' if primeiro.get('dns.flags.response') in ('1', 'True') else 'DNS Pergunta'
        else:
            protocolo, tipo = 'ICMP', icmp.get(primeiro['icmp.type'], f"ICMP tipo {primeiro['icmp.type']}")
        origem = primeiro['arp.src.proto_ipv4'] if arp else primeiro['ip.src']
        destino = primeiro['arp.dst.proto_ipv4'] if arp else primeiro['ip.dst']
        eventos.append({
            'sequencia': int(campos['frame.number']),
            'tempo_relativo': float(campos['frame.time_relative']),
            'protocolo': protocolo, 'tipo': tipo,
            'origem': origem, 'destino': destino,
            'resumo': f'{tipo}: {origem} → {destino}',
            'campos': {k: v for k, v in campos.items() if v},
        })
    return eventos


BASTIDORES = 4


def registrar_bastidores(s: dict, no, digitado: str, captura: dict):
    """Guarda as últimas capturas do aluno no estado do laboratório, para o painel Bastidores."""
    s.setdefault('bastidores', []).append({'pc': no, 'digitado': ' '.join(digitado.split()), 'revisao': s['revisao'], **captura})
    del s['bastidores'][:-BASTIDORES]


class Captura:
    def __init__(self, session_id: int, node_id: int, perfil: str = 'arp_icmp'):
        self.session_id = session_id
        self.node_id = node_id
        self._perfil = PERFIS[perfil]
        self._lock = threading.RLock()
        self._processo = None
        self._pasta = tempfile.TemporaryDirectory(prefix='pinglevel-captura-')
        self._arquivo = f'{self._pasta.name}/trafego.pcapng'
        self._cancelada = False
        self._resultado = None
        self._base = {
            'id': uuid.uuid4().hex, 'node_id': node_id, 'perfil': perfil,
            'iniciado_em': time.time(), 'limite_segundos': self._perfil['segundos'], 'limite_pacotes': self._perfil['pacotes'],
        }

    def iniciar(self, core):
        interface = resolver_interface(core, self.session_id, self.node_id)
        with self._lock:
            if self._cancelada:
                raise RuntimeError('Captura cancelada.')
            self._processo = subprocess.Popen(
                ['dumpcap', '-i', interface, '-p', '-f', self._perfil['captura'],
                 '-a', f"duration:{self._perfil['segundos']}", '-c', str(self._perfil['pacotes']), '-w', self._arquivo],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            processo = self._processo
        mensagens = queue.Queue()

        def ler():
            for linha in processo.stderr:
                mensagens.put(linha)
            mensagens.put(None)
        self._leitor = threading.Thread(target=ler, daemon=True)
        self._leitor.start()
        limite = time.monotonic() + 3
        while time.monotonic() < limite:
            try:
                linha = mensagens.get(timeout=0.1)
            except queue.Empty:
                continue
            if linha is None:
                break
            if 'File:' in linha:
                return
        raise RuntimeError('Captura indisponível ou sem indicação de prontidão.')

    def _parar(self):
        if self._processo:
            if self._processo.poll() is None:
                self._processo.send_signal(signal.SIGINT)
                try:
                    self._processo.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._processo.kill()
                    self._processo.wait(timeout=2)
            if hasattr(self, '_leitor'):
                self._leitor.join(timeout=1)
                self._processo.stderr.close()

    def cancelar(self):
        with self._lock:
            self._cancelada = True
            self._parar()

    def finalizar(self, erro: str | None = None) -> dict:
        with self._lock:
            if self._resultado is not None:
                return self._resultado
            eventos = []
            estado = 'cancelada' if self._cancelada else 'falha' if erro else 'concluida'
            try:
                # Aguardar a entrega do último lote do buffer de captura.
                if estado == 'concluida' and self._processo and self._processo.poll() is None:
                    time.sleep(1)
                terminou_com_erro = self._processo and self._processo.poll() not in (None, 0)
                self._parar()
                if estado == 'concluida':
                    if terminou_com_erro:
                        raise RuntimeError('Capturador terminou com erro.')
                    args = ['tshark', '-n', '-r', self._arquivo, '-Y', self._perfil['leitura'], '-T', 'fields']
                    for campo in self._perfil['campos']:
                        args.extend(['-e', campo])
                    saida = subprocess.check_output(args, text=True, timeout=5, stderr=subprocess.DEVNULL)
                    eventos = interpretar_campos(saida, self._perfil['campos'])
                    estado = 'concluida' if eventos else 'vazia'
            except Exception:
                estado = 'falha'
                erro = 'Não foi possível interpretar a captura.'
            finally:
                self._pasta.cleanup()
            self._resultado = {
                **self._base, 'estado': estado, 'finalizado_em': time.time(),
                'eventos': eventos,
                'mensagem': erro or ('Captura cancelada.' if self._cancelada else 'Captura finalizada.'),
            }
            return self._resultado
