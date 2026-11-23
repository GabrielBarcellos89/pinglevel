"""Demonstração "Suporte remoto": um só terminal (T.I.), ssh real até o Financeiro B, correção do gateway pela sessão
SSH e impressão na porta 9100 do outro prédio. A rede é simulada aqui; o ensaio no CORE fica em
tools/qa/ensaio_core_suporte.py."""
import ipaddress
import json
import re
import threading
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import suporte_remoto as c
from laboratorios.terminal_comandos import ErroComando, interpretar_remoto
from laboratorios.terminal_guiado import ErroTerminal
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import PERFIL_SUPORTE


class Predios:
    """Dois prédios ligados por um roteador; cada nó tem um endereço /24 e uma rota padrão."""
    def __init__(self):
        self.ip = {k: n['ip'] for k, n in c.NOS.items() if 'ip' in n}
        self.rota = {k: c.INICIAL[k]['rota_padrao'] for k in self.ip}
        self.folhas = []

    @staticmethod
    def rede(ip):
        return ipaddress.IPv4Interface(f'{ip}/24').network

    def alcanca(self, origem, destino_ip):
        dono = next((k for k, ip in self.ip.items() if ip == destino_ip), None)
        if dono is None:
            return False
        if self.rede(self.ip[origem]) == self.rede(destino_ip):
            return True
        gw = lambda k: c.GW[c.NOS[k]['setor']]  # noqa: E731
        return self.rota[origem] == gw(origem) and self.rota[dono] == gw(dono)

    def executar(self, no, cmd):
        if no == 'roteador':
            return self._roteador(cmd)
        m = re.fullmatch(r"ssh (\S+) hostname 2>&1", cmd)
        if m:
            return (0, c.NOS[c.no_do_ip(m[1])]['host']) if self.alcanca(no, m[1]) else (255, f'ssh: connect to host {m[1]} port 22: Operation timed out')
        m = re.fullmatch(r"ssh (\S+) '(.*)'", cmd)
        if m:
            if not self.alcanca(no, m[1]):
                return 255, f'ssh: connect to host {m[1]} port 22: Operation timed out'
            return self.executar(c.no_do_ip(m[1]), m[2])
        if cmd == 'ip -j addr show':
            return 0, json.dumps([{'ifname': 'eth0', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': self.ip[no], 'prefixlen': 24}]}])
        if cmd == 'ip -j -4 route show':
            tabela = [{'dst': str(self.rede(self.ip[no])), 'dev': 'eth0'}]
            return 0, json.dumps(([{'dst': 'default', 'gateway': self.rota[no], 'dev': 'eth0'}] if self.rota[no] else []) + tabela)
        if cmd == 'ip -4 route show':
            return 0, (f'default via {self.rota[no]} dev eth0\n' if self.rota[no] else '') + f'{self.rede(self.ip[no])} dev eth0'
        if cmd == 'ip route del default dev eth0':
            self.rota[no] = None
            return 0, ''
        m = re.fullmatch(r'ip route add default via (\S+) dev eth0', cmd)
        if m:
            self.rota[no] = m[1]
            return 0, ''
        m = re.fullmatch(r'ping -n -c 2 -W 1 (\S+)', cmd)
        if m:
            return (0, '2 packets transmitted, 2 received, 0% packet loss') if self.alcanca(no, m[1]) else (1, '2 packets transmitted, 0 received, 100% packet loss')
        m = re.fullmatch(r'curl -sS -m 3 -d "texto=(.*)" http://(\S+)/imprimir 2>&1', cmd)
        if m:
            if self.alcanca(no, m[2]) and m[2] == c.IMPRESSORA:
                self.folhas.append(m[1])
                return 0, f'Impressora do Prédio A: trabalho recebido. Folha {len(self.folhas)} impressa.'
            return 28, f'curl: (28) Failed to connect to {m[2]} port 80 after 3001 ms: Timeout was reached'
        m = re.fullmatch(r'curl -sS -m 3 http://(\S+)/ 2>&1', cmd)
        if m:
            if self.alcanca(no, m[1]) and m[1] == c.IMPRESSORA:
                return 0, f'Impressora do Prédio A (192.168.10.50)\nFolhas impressas: {len(self.folhas)}'
            return 28, f'curl: (28) Failed to connect to {m[1]} port 80 after 3001 ms: Timeout was reached'
        if cmd == 'ls /tmp/folhas 2>/dev/null | wc -l':
            return 0, f'{len(self.folhas)}\n'
        if cmd.startswith('ip addr show dev eth0'):
            return 0, f'2: eth0: <UP>\n    inet {self.ip[no]}/24 scope global eth0'
        raise AssertionError(f'comando inesperado no {no}: {cmd}')

    def _roteador(self, cmd):
        if cmd == 'ip -j addr show':
            return 0, json.dumps([{'ifname': f'eth{i}', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': gw, 'prefixlen': 24}]}
                                  for i, gw in enumerate((c.GW['a'], c.GW['b']))])
        if cmd == 'ip -j -4 route show':
            return 0, '[]'
        raise AssertionError(cmd)


class Engine:
    def __init__(self, rede=None):
        self._lock = threading.RLock()
        self.lab = None
        self.rede = rede or Predios()
        self.por_id = {n['no']: k for k, n in c.NOS.items()}
        self.criacoes = []

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.lab = SimpleNamespace(usuario_id=uid, session_id=9, laboratorio_id=labid, login=login, iniciado_em=0, tempo_criacao=8.4)
        return self.lab

    def obter(self, uid, heartbeat=True):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def listar(self):
        return [self.lab] if self.lab else []

    def dados_temporais(self, lab):
        return {'segundos_restantes': 900}

    def executar(self, uid, node, cmd, timeout=8):
        assert self._lock._is_owned()
        return self.rede.executar(self.por_id[node], cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True


def servico():
    engine = Engine()
    return ServicoRede(engine, lambda uid, lab: {'xp_concedido': 0}, cenario=c, perfil_tutor=PERFIL_SUPORTE), engine


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(1, 'aluno', acao, extra)
    estado = s.executar_acao(1, 'aluno', 'status', {})
    return s.executar_acao(1, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
                                               'revisao': estado['missao']['revisao'], **extra})


def term(s, comando, pc='ti'):
    return act(s, 'terminal', comando=comando, pc=pc)['missao']


def test_reconhece_ssh_exit_e_impressao():
    assert interpretar_remoto('ssh 192.168.20.21') == ('ssh', '192.168.20.21', 'suporte')
    assert interpretar_remoto('ssh suporte@192.168.20.21') == ('ssh', '192.168.20.21', 'suporte')
    assert interpretar_remoto('ssh root@192.168.20.21') == ('ssh', '192.168.20.21', 'root')
    assert interpretar_remoto('exit') == ('exit',)
    assert interpretar_remoto('curl http://192.168.10.50') == ('pagina', '192.168.10.50')
    assert interpretar_remoto('curl 192.168.10.50/') == ('pagina', '192.168.10.50')
    assert interpretar_remoto('curl -d "texto=Folha da Ana 2" http://192.168.10.50/imprimir') == ('imprimir', 'Folha da Ana 2', '192.168.10.50')
    assert interpretar_remoto("curl -X POST -d 'texto=Oi' 192.168.10.50/imprimir") == ('imprimir', 'Oi', '192.168.10.50')
    assert interpretar_remoto('ip route') is None
    with pytest.raises(ErroComando, match='texto='):
        interpretar_remoto('curl -d "GabrielBarcellos" http://192.168.10.50/imprimir')
    for errado in ('ssh -p 22 192.168.20.21', 'curl -d "texto=a;rm" http://192.168.10.50/imprimir', 'curl http://192.168.10.50:8080',
                   'ssh 172.30.1.2', 'curl -d "texto=$(id)" 192.168.10.50/imprimir', 'echo oi | nc 192.168.10.50 9100',
                   'curl file:///etc/passwd'):
        with pytest.raises(ErroComando):
            interpretar_remoto(errado)


def entrar(s, senha=c.SENHA_SSH):
    m = term(s, 'ssh suporte@192.168.20.21')
    assert m['senha_pendente'] == {'usuario': 'suporte', 'ip': '192.168.20.21'} and m['remoto'] is None
    assert m['terminal'][-1]['saida'] == "suporte@192.168.20.21's password:"
    return term(s, senha)


def test_roteiro_completo_pela_ti():
    s, engine = servico()
    act(s, 'iniciar')
    m = entrar(s)
    assert m['remoto'] == 'fin_b' and m['proxima_etapa'] == 'gateway' and 'financeiro-b' in m['terminal'][-1]['saida']
    assert m['terminal'][-1]['digitado'] == '' and c.SENHA_SSH not in json.dumps(m)
    m = term(s, 'ip route')
    assert 'default via 192.168.20.254' in m['terminal'][-1]['saida'] and m['terminal'][-1]['remoto'] == 'fin_b'
    m = term(s, 'curl http://192.168.10.50')
    assert m['terminal'][-1]['codigo'] != 0 and 'não alcançou' in m['terminal'][-1]['saida']
    m = term(s, 'curl -d "texto=antes" http://192.168.10.50/imprimir')
    assert m['terminal'][-1]['codigo'] != 0 and not m['folhas'] and 'não recebeu' in m['terminal'][-1]['saida']
    term(s, 'ip route del default')
    m = term(s, 'ip route add default via 192.168.20.1')
    assert m['estados']['fin_b']['rota_padrao'] == '192.168.20.1' and m['proxima_etapa'] == 'impressao'
    m = term(s, 'curl http://192.168.10.50')
    assert 'Folhas impressas: 0' in m['terminal'][-1]['saida']
    m = term(s, 'curl -d "texto=Relatório do Financeiro" http://192.168.10.50/imprimir')
    assert m['folhas'][0]['texto'] == 'Relatório do Financeiro' and m['folhas'][0]['origem'] == 'fin_b'
    assert 'trabalho recebido' in m['terminal'][-1]['saida']
    assert m['proxima_etapa'] == 'comprovar'
    assert s.painel()[0]['folhas'][0]['texto'] == 'Relatório do Financeiro'
    m = term(s, 'exit')
    assert m['remoto'] is None
    final = act(s, 'validar')
    assert final['conclusao']['registrada'] and final['xp_concedido'] == 0 and not final['ativo']


def test_senha_errada_tres_vezes_cancela_e_usuario_errado_nao_entra():
    s, _ = servico()
    act(s, 'iniciar')
    m = entrar(s, 'errada')
    assert m['senha_pendente'] and 'please try again' in m['terminal'][-1]['saida'] and m['remoto'] is None
    term(s, 'errada')
    m = term(s, 'outra')
    assert m['senha_pendente'] is None and 'Permission denied (publickey,password)' in m['terminal'][-1]['saida']
    assert all(h['digitado'] in ('', 'ssh suporte@192.168.20.21') for h in m['terminal'])
    term(s, 'ssh root@192.168.20.21')
    m = term(s, c.SENHA_SSH)
    assert m['remoto'] is None and 'please try again' in m['terminal'][-1]['saida']
    assert m['proxima_etapa'] == 'acesso'


def test_so_o_terminal_da_ti_e_so_o_financeiro_b_muda():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='a partir do PC da T.I.'):
        term(s, 'ip route', pc='fin_b')
    with pytest.raises(ErroTerminal, match='não é de um computador'):
        term(s, 'ssh 192.168.10.1')
    with pytest.raises(ErroTerminal, match='própria'):
        term(s, 'ssh 192.168.20.30')
    with pytest.raises(ErroTerminal, match='não há conexão SSH'):
        term(s, 'exit')
    with pytest.raises(ErroTerminal, match='só se altera: Financeiro B|não há nada para alterar'):
        term(s, 'ip route del default')
    entrar(s)
    with pytest.raises(ErroTerminal, match='exit antes'):
        term(s, 'ssh 192.168.20.23')
    with pytest.raises(ErroTerminal, match='não é da impressora'):
        term(s, 'curl -d "texto=oi" http://192.168.10.11/imprimir')


def test_folha_impressa_da_ti_nao_conclui_a_etapa():
    s, _ = servico()
    act(s, 'iniciar')
    entrar(s)
    term(s, 'ip route del default')
    term(s, 'ip route add default via 192.168.20.1')
    term(s, 'exit')
    m = term(s, 'curl -d "texto=da ti" http://192.168.10.50/imprimir')
    assert m['folhas'][0]['origem'] == 'ti' and m['proxima_etapa'] == 'impressao'
    assert 'a partir do Financeiro B' in m['terminal'][-1]['saida']


def test_recusa_fica_para_o_link_mas_a_senha_nunca():
    s, _ = servico()
    act(s, 'iniciar')
    term(s, 'ssh suporte@192.168.20.21')
    term(s, 'senha errada')  # tratada como senha: não é recusa, não é guardada
    term(s, c.SENHA_SSH)
    with pytest.raises(ErroTerminal):
        term(s, 'curl -d "GabrielBarcellos" http://192.168.20.50/imprimir')
    missao = act(s, 'status')['missao']
    assert missao['recusas'][-1]['digitado'] == 'curl -d "GabrielBarcellos" http://192.168.20.50/imprimir'
    assert 'texto=' in missao['recusas'][-1]['motivo']
    assert 'senha errada' not in json.dumps(missao) and c.SENHA_SSH not in json.dumps(missao['terminal'])
    from laboratorios.tutor_setores import _contexto
    linha = _contexto(c)(missao)['ultimos_comandos']
    assert linha[-1]['aceito'] is False and linha[-1]['motivo_da_recusa']
    assert linha[-2]['equipamento'] == 'T.I.' or linha[-2]['equipamento'] == 'Financeiro B'


def test_link_recebe_o_guia_do_laboratorio_como_trecho():
    from laboratorios.tutor_referencias import TutorReferencias
    enviado = {}

    def gerar(sistema, contexto):
        enviado['sistema'], enviado['contexto'] = sistema, json.loads(contexto)
        return json.dumps({'tipo': 'resposta', 'trechos_usados': [1], 'resposta':
            'Faltou texto= antes da frase: o campo do formulário da impressora se chama texto. Use curl -d "texto=sua frase" '
            'http://192.168.10.50/imprimir, com o endereço da impressora do Prédio A.'})
    tutor = TutorReferencias(buscar=lambda q: [], ancoras=lambda ids: [], gerar=gerar, perfil=PERFIL_SUPORTE)
    r = tutor.responder(pergunta='onde estou errando?', missao={'proxima_etapa': 'impressao', 'nos': []}, historico=[], rascunho='')
    assert r['modo'] == 'referencias' and r['fontes'] == [{'guia': 'Guia deste laboratório'}]
    assert enviado['contexto']['trechos_dos_livros'][0]['texto'].startswith('Guia do Suporte remoto, etapa impressão')
