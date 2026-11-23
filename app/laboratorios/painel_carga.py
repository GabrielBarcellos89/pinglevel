"""Métricas do servidor para o painel do teste de carga: leitura direta do /proc e do cgroup dos contêineres.

O servidor também roda outros serviços em contêineres; só entram na conta os dos laboratórios (nome pl-s<sessão>-...).
A lista deles vem do `docker ps`, guardada por alguns segundos; o resto é leitura de arquivo, de milissegundos.
"""
import os
import subprocess
import threading
import time
from pathlib import Path

CGROUP = Path('/sys/fs/cgroup/system.slice')
_lock = threading.Lock()
_anterior = {'cpu': None, 'contêineres': None}
_ids = {'momento': 0.0, 'lista': set()}


def _ids_laboratorio():
    agora = time.time()
    if agora - _ids['momento'] > 5:
        try:
            saida = subprocess.run(['docker', 'ps', '--no-trunc', '--filter', 'name=^pl-s', '--format', '{{.ID}}'],
                                   capture_output=True, text=True, timeout=3).stdout
            _ids['lista'] = set(saida.split())
        except (OSError, subprocess.SubprocessError):
            pass
        _ids['momento'] = agora
    return _ids['lista']


def _cpu_total():
    partes = Path('/proc/stat').read_text().splitlines()[0].split()[1:]
    valores = [int(v) for v in partes]
    ocioso = valores[3] + (valores[4] if len(valores) > 4 else 0)
    return sum(valores), ocioso


def _memoria():
    info = {}
    for linha in Path('/proc/meminfo').read_text().splitlines():
        chave, valor = linha.split(':', 1)
        info[chave] = int(valor.split()[0]) * 1024
    total, livre = info['MemTotal'], info['MemAvailable']
    return {'total': total, 'usada': total - livre, 'disponivel': livre}


def _conteineres():
    """Contêineres em execução, memória somada e tempo de CPU somado (µs), pelo cgroup de cada um."""
    total_mem, total_cpu, quantidade = 0, 0, 0
    ids = _ids_laboratorio()
    for pasta in CGROUP.glob('docker-*.scope'):
        if pasta.name[len('docker-'):-len('.scope')] not in ids:
            continue
        try:
            total_mem += int((pasta / 'memory.current').read_text())
            uso = (pasta / 'cpu.stat').read_text().split('\n', 1)[0].split()
            total_cpu += int(uso[1]) if uso and uso[0] == 'usage_usec' else 0
            quantidade += 1
        except (OSError, ValueError, IndexError):
            continue
    return quantidade, total_mem, total_cpu


def coletar(gerenciador):
    agora = time.time()
    total, ocioso = _cpu_total()
    quantidade, memoria_conteineres, cpu_conteineres = _conteineres()
    with _lock:
        anterior = _anterior['cpu']
        _anterior['cpu'] = (total, ocioso)
        cpu = None
        if anterior and total > anterior[0]:
            cpu = round(100 * (1 - (ocioso - anterior[1]) / (total - anterior[0])), 1)
        ant_cont = _anterior['contêineres']
        _anterior['contêineres'] = (agora, cpu_conteineres)
        cpu_cont = None
        if ant_cont and agora > ant_cont[0]:
            # Em núcleos: µs de CPU usados por segundo de relógio / 1e6.
            cpu_cont = round(max(0, cpu_conteineres - ant_cont[1]) / ((agora - ant_cont[0]) * 1e6), 2)
    carga = os.getloadavg()
    labs = gerenciador.listar()
    por_lab = {}
    for lab in labs:
        por_lab[lab.laboratorio_id] = por_lab.get(lab.laboratorio_id, 0) + 1
    criacoes = list(gerenciador.criacoes)[-40:]
    return {
        'momento': int(agora),
        'nucleos': os.cpu_count(),
        'cpu_percentual': cpu,
        'carga': [round(c, 2) for c in carga],
        'memoria': _memoria(),
        'conteineres': {'quantidade': quantidade, 'memoria': memoria_conteineres, 'cpu_nucleos': cpu_cont},
        'ambientes': {'total': len(labs), 'por_laboratorio': por_lab},
        'criacoes': [{'momento': m, 'laboratorio': l, 'segundos': s} for m, l, s in criacoes],
    }
