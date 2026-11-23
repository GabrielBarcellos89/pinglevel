"""Labs 8 e 10 com rede simulada: DHCP e DNS (dnsmasq) imitados no I/O; regras dos chamados conferidas no servidor."""
import json
import threading
from copy import deepcopy
from types import SimpleNamespace

import pytest

from laboratorios.cenarios import desafio_empresa as lab10
from laboratorios.cenarios import enderecos_nomes as lab8
from laboratorios.cenarios import rede_setores as base
from laboratorios.terminal_comandos import ErroComando, interpretar
from laboratorios.terminal_guiado import ErroTerminal
from laboratorios.terminal_rede import ServicoRede
from laboratorios.tutor_setores import ANCORAS_8, ANCORAS_10, PERFIL_LAB8, PERFIL_LAB10

PERDA = (1, '--- ping statistics ---\n2 packets transmitted, 0 received, 100% packet loss, time 1010ms')
OK = (0, '2 packets transmitted, 2 received, 0% packet loss')


class Rede:
    """Lab 8: uma rede, servidor DHCP .2 com faixa .100–.150 e os nomes da empresa. Com o cenário do Lab 10, só imita
    as leituras do estado inicial (para a tela ser exercitada no navegador; o percurso é ensaiado no CORE)."""
    def __init__(self, cenario=lab8):
        self.cenario = cenario
        self.nos = {n: deepcopy(cenario.INICIAL[n]) for n in cenario.NOS}
        self.proximo = 100

    def ip(self, no):
        e = self.nos[no]['interfaces']['eth0']
        return e[0].split('/')[0] if e else None

    def executar(self, no, cmd):
        e = self.nos[no]
        if cmd == 'ip -j addr show':
            info = lambda i: [{'family': 'inet', 'local': a.split('/')[0], 'prefixlen': 24} for a in e['interfaces'][i]]  # noqa: E731
            return 0, json.dumps([{'ifname': f'{i}@if9', 'flags': ['UP'], 'addr_info': info(i)} for i in e['interfaces']]
                                 + [{'ifname': 'ctrl0', 'flags': ['UP'], 'addr_info': [{'family': 'inet', 'local': '172.30.9.1', 'prefixlen': 24}]}])
        if cmd == 'bridge -j vlan show':
            return 0, json.dumps([{'ifname': p, 'vlans': [{'vlan': v['pvid'], 'flags': ['PVID', 'Egress Untagged']}]} for p, v in e['vlans'].items()])
        if cmd == 'ip -j -4 route show':
            rotas = [{'dst': 'default', 'gateway': e['rota_padrao'], 'dev': 'eth0', 'metric': 1009}] if e['rota_padrao'] else []
            return 0, json.dumps(rotas + [{'dst': '172.30.9.0/24', 'dev': 'ctrl0'}])
        if cmd == 'cat /etc/resolv.conf':
            return 0, ''.join(f'nameserver {d}\n' for d in e['dns']) or '# nenhum servidor DNS configurado'
        if cmd.startswith('ip addr show'):
            return 0, '2: eth0@if9: <BROADCAST,MULTICAST,UP,LOWER_UP>\n' + ''.join(f'    inet {a} scope global eth0\n' for a in e['interfaces']['eth0'])
        if cmd.startswith('udhcpc -i eth0'):
            reserva = lab8.RESERVA_FINANCEIRO if no == 'financeiro' else f'192.168.40.{self.proximo}'
            self.proximo += no != 'financeiro'
            e.update(interfaces={'eth0': [f'{reserva}/24']}, rota_padrao=lab8.GATEWAY, dns=[lab8.SERVIDOR])
            return 0, f'udhcpc: lease of {reserva} obtained from 192.168.40.2, lease time 3600\nadding dns 192.168.40.2'
        p = cmd.split()
        if p[0] == 'nslookup':
            if e['dns'] != [lab8.SERVIDOR]:
                return 1, ';; connection timed out; no servers could be reached'
            if p[1] not in lab8.NOMES:
                return 1, f"** server can't find {p[1]}: NXDOMAIN"
            return 0, f'Name:\t{p[1]}\nAddress: {lab8.NOMES[p[1]]}'
        if p[0] == 'ping':
            alvo = p[-1]
            if not alvo[0].isdigit():
                if e['dns'] != [lab8.SERVIDOR] or alvo not in lab8.NOMES:
                    return 2, f'ping: {alvo}: Try again'
                alvo = lab8.NOMES[alvo]
            return OK if self.ip(no) and alvo in {self.ip(n) for n in self.nos} else PERDA
        raise AssertionError(f'comando inesperado: {cmd}')


class Engine:
    def __init__(self, rede, cenario):
        self._lock = threading.RLock()
        self.lab = None
        self.rede = rede
        self.por_id = {info['no']: chave for chave, info in cenario.NOS.items()}

    def trava(self, uid):
        return self._lock

    def criar(self, uid, login, labid):
        self.lab = SimpleNamespace(usuario_id=uid, session_id=8, laboratorio_id=labid)
        return self.lab

    def obter(self, uid):
        return self.lab if self.lab and self.lab.usuario_id == uid else None

    def dados_temporais(self, lab):
        return {'segundos_restantes': 900}

    def executar(self, uid, node, cmd, timeout=8):
        assert self._lock._is_owned()
        return self.rede.executar(self.por_id[node], cmd)

    def encerrar_confirmado(self, uid, sid, motivo):
        self.lab = None
        return True


def servico():
    salvos = []
    s = ServicoRede(Engine(Rede(), lab8), lambda uid, lab: (salvos.append(lab) or {'xp_concedido': 100}),
                    cenario=lab8, perfil_tutor=PERFIL_LAB8)
    return s, salvos


def act(s, acao, **extra):
    if acao in ('status', 'iniciar'):
        return s.executar_acao(1, 'aluno', acao, extra)
    estado = s.executar_acao(1, 'aluno', 'status', {})
    return s.executar_acao(1, 'aluno', acao, {'session_id': estado['laboratorio']['session_id'],
                                              'revisao': estado['missao']['revisao'], **extra})


def term(s, no, comando):
    return act(s, 'terminal', comando=comando, pc=no)['missao']


def chamado_novo(s):
    term(s, 'novo', 'ip addr show')
    act(s, 'diagnosticar', resposta='sem-endereco')
    term(s, 'novo', 'udhcpc -i eth0')
    return term(s, 'novo', 'ping intranet.empresa.local')


def chamado_recepcao(s):
    term(s, 'recepcao', 'ping 192.168.40.20')
    term(s, 'recepcao', 'cat /etc/resolv.conf')
    act(s, 'diagnosticar', resposta='dns-errado')
    term(s, 'recepcao', 'udhcpc -i eth0')
    return term(s, 'recepcao', 'ping intranet.empresa.local')


def test_lab8_percurso_completo():
    s, salvos = servico()
    missao = act(s, 'iniciar')['missao']
    assert missao['proxima_etapa'] == 'novo' and [c['situacao'] for c in missao['chamados']] == ['atual', 'fila', 'fila']
    assert missao['chamado']['objetivo'] and missao['chamado']['progresso'] == {'causa': False, 'configuracao': False, 'teste': False}
    missao = chamado_novo(s)
    assert missao['proxima_etapa'] == 'recepcao' and missao['estados']['novo']['dns'] == ['192.168.40.2']
    assert missao['chamados'][0]['situacao'] == 'resolvido' and 'resolucao' in missao['chamados'][0]
    assert chamado_recepcao(s)['proxima_etapa'] == 'financeiro'
    term(s, 'financeiro', 'nslookup impresora.empresa.local')
    act(s, 'diagnosticar', resposta='nome')
    assert term(s, 'financeiro', 'ping impressora.empresa.local')['proxima_etapa'] == 'comprovar'
    final = act(s, 'validar')
    assert final['conclusao']['registrada'] and final['xp_concedido'] == 100 and salvos == ['enderecos-e-nomes']


def test_lab8_causa_antes_de_corrigir_e_observacao_antes_da_causa():
    s, _ = servico()
    act(s, 'iniciar')
    with pytest.raises(ErroTerminal, match='ip addr show'):
        act(s, 'diagnosticar', resposta='sem-endereco')
    term(s, 'novo', 'ip addr show')
    with pytest.raises(ErroTerminal, match='responda no chamado'):
        term(s, 'novo', 'udhcpc -i eth0')
    assert 'Releia' in act(s, 'diagnosticar', resposta='cabo')['mensagem']
    act(s, 'diagnosticar', resposta='sem-endereco')
    with pytest.raises(ErroTerminal, match='só se altera: PC Novo'):
        term(s, 'recepcao', 'udhcpc -i eth0')


def test_lab8_financeiro_nao_tem_nada_a_corrigir_e_conclusao_relê_os_pcs():
    s, _ = servico()
    act(s, 'iniciar')
    chamado_novo(s)
    chamado_recepcao(s)
    term(s, 'financeiro', 'nslookup impresora.empresa.local')
    act(s, 'diagnosticar', resposta='nome')
    with pytest.raises(ErroTerminal, match='nada para alterar'):
        term(s, 'financeiro', 'udhcpc -i eth0')
    term(s, 'financeiro', 'ping impressora.empresa.local')
    s.engine.rede.nos['recepcao']['dns'] = ['192.168.40.9']
    with pytest.raises(ErroTerminal, match='PC Recepção'):
        act(s, 'validar')


def test_lab8_concessao_exige_faixa_gateway_e_dns():
    ok = {'interfaces': {'eth0': ['192.168.40.101/24']}, 'rota_padrao': '192.168.40.1', 'dns': ['192.168.40.2']}
    assert lab8.concessao_ok(ok)
    assert not lab8.concessao_ok({**ok, 'interfaces': {'eth0': ['192.168.40.60/24']}})
    assert not lab8.concessao_ok({**ok, 'dns': ['192.168.40.9']})
    assert not lab8.concessao_ok({**ok, 'rota_padrao': None})


@pytest.mark.parametrize('comando, mensagem', [
    ('udhcpc', 'depois de -i'), ('dhclient', 'dhclient eth0'), ('dhclient eth1', 'apenas'), ('cat /etc/shadow', 'resolv.conf'),
    ('nslookup intranet', 'intranet.empresa.local'), ('nslookup google.com', 'nomes da empresa'),
    ('ping www.google.com', 'nomes da empresa'), ('udhcpc -i eth0 -s /tmp/x', 'apenas'),
])
def test_interpretador_de_servicos_recusa(comando, mensagem):
    with pytest.raises(ErroComando, match=mensagem):
        interpretar(comando, servicos='empresa.local')


def test_dhclient_faz_o_mesmo_pedido_que_o_udhcpc():
    # O comando ensinado é o dhclient; nos nós Alpine o pedido é feito pelo udhcpc.
    for comando in ('dhclient eth0', 'dhclient -v eth0', 'udhcpc -i eth0'):
        c = interpretar(comando, servicos='empresa.local')
        assert c.tipo == 'pedir-dhcp' and c.executar.startswith('udhcpc -i eth0 ')


def test_interpretador_sem_servicos_nao_conhece_os_comandos_novos():
    with pytest.raises(ErroComando):
        interpretar('udhcpc -i eth0')
    with pytest.raises(ErroComando):
        interpretar('nslookup intranet.empresa.local')


def test_lab9_continua_com_chamado_unico():
    from laboratorios.cenarios import investigando_lan as lab9
    publico = lab9.estado_publico(lab9.dados_iniciais(), True)
    assert publico['chamado']['etapa'] == 'chamado' and publico['chamados'] == []
    assert set(base.chamados(lab9)) == {'chamado'}


def _estado10(**mudancas):
    s = lab10.dados_iniciais()
    for no, valores in mudancas.items():
        s['estados'][no].update(valores)
    return s


def test_lab10_chamados_em_ordem_e_cada_um_exige_causa_correcao_e_teste():
    s = _estado10()
    assert base.etapa_atual(lab10, s) == 'intranet'
    s['diagnosticos']['intranet']['correta'] = True
    s['estados']['intranet']['rota_padrao'] = '192.168.60.1'
    assert base.etapa_atual(lab10, s) == 'intranet'
    s['testes']['v1'][lab10.INTRANET] = True
    assert base.etapa_atual(lab10, s) == 'vlan'
    s['diagnosticos']['vlan']['correta'] = True
    s['estados']['switch']['vlans'] = dict(lab10.VLANS_FINAIS)
    s['testes']['v2'][lab10.INTRANET] = True
    assert base.etapa_atual(lab10, s) == 'dhcp'
    s['diagnosticos']['dhcp']['correta'] = True
    s['estados']['f1'].update(interfaces={'eth0': ['192.168.20.104/24']}, rota_padrao='192.168.20.1', dns=['192.168.20.1'])
    s['testes']['f1'][lab10.INTRANET] = True
    s['diagnosticos']['dns']['correta'] = True
    s['estados']['f2'].update(interfaces={'eth0': ['192.168.20.22/24']}, dns=['192.168.20.1'])
    s['testes']['f2'][lab10.INTRANET] = True
    assert base.etapa_atual(lab10, s) == 'dns', 'endereço manual não é concessão do DHCP'
    s['estados']['f2']['interfaces'] = {'eth0': ['192.168.20.105/24']}
    assert base.etapa_atual(lab10, s) == 'comprovar'
    assert lab10.problemas(s) == []
    assert ('v1', '192.168.20.104') in lab10.testes_finais(s)


def test_lab10_mudar_o_servidor_invalida_todos_os_testes_e_a_porta_so_os_do_pc():
    s = _estado10()
    s['testes'] = {pc: {lab10.INTRANET: True} for pc in lab10.NOS}
    lab10.invalidar_testes(s, 'switch', {'vlans': lab10.VLANS_INICIAIS}, {'vlans': lab10.VLANS_FINAIS})
    assert s['testes']['v2'] == {} and s['testes']['v1'] == {lab10.INTRANET: True}
    lab10.invalidar_testes(s, 'intranet', {}, {})
    assert all(t == {} for t in s['testes'].values())


def test_lab10_alteraveis_por_chamado():
    assert lab10.ALTERAVEIS == {'intranet': {'intranet': ('eth0',)}, 'vlan': {'switch': ('eth1',)},
                                'dhcp': {'f1': ('eth0',)}, 'dns': {'f2': ('eth0',)}}


def test_tutor_nao_entrega_as_causas():
    aberto = {'chamado': {'correta': False}}
    assert PERFIL_LAB8.bloquear('O nome está escrito errado.', 'financeiro', 2, aberto, 'por que não acha?', {}) == 'filtro'
    assert PERFIL_LAB8.bloquear('O servidor DNS está errado.', 'recepcao', 2, aberto, 'o que houve?', {}) == 'filtro'
    assert PERFIL_LAB8.bloquear('Leia a resposta do nslookup.', 'financeiro', 2, aberto, 'e agora?', {}) is None
    assert PERFIL_LAB8.bloquear('Rode udhcpc -i eth0.', 'novo', 2, {'chamado': {'correta': True}}, 'como?', {}) == 'filtro'
    assert PERFIL_LAB8.bloquear('Rode udhcpc -i eth0.', 'novo', 4, {'chamado': {'correta': True}}, 'como?', {}) is None
    assert PERFIL_LAB8.bloquear('Rode dhclient eth0.', 'novo', 2, {'chamado': {'correta': True}}, 'como?', {}) == 'filtro'
    assert PERFIL_LAB8.bloquear('O dhclient pede um endereço ao servidor DHCP.', 'novo', 2, aberto, 'o que é?', {}) is None
    assert PERFIL_LAB10.bloquear('A rota padrão do servidor está errada.', 'intranet', 2, aberto, 'o que é?', {}) == 'filtro'
    assert PERFIL_LAB10.bloquear('ip route add default via 192.168.60.1', 'intranet', 3, {'chamado': {'correta': True}}, 'e?', {}) == 'filtro'


def test_ancoras_existem_no_indice():
    import sqlite3
    from pathlib import Path
    banco = Path('/opt/packetlab/data/rag/indice/pinglevel_rag.db')
    if not banco.exists():
        pytest.skip('índice RAG ausente')
    ids = {i for a in (ANCORAS_8, ANCORAS_10) for v in a.values() for i in v}
    with sqlite3.connect(f'file:{banco}?mode=ro', uri=True) as c:
        achados = {r[0] for r in c.execute(f"select id from chunks where id in ({','.join('?' * len(ids))})", tuple(ids))}
    assert achados == ids


def test_link_dos_labs_9_e_10_pode_falar_da_tabela_arp():
    from laboratorios.tutor_setores import PERFIL_LAB9
    assert PERFIL_LAB9.bloquear('Leia a tabela ARP com ip neigh show.', 'investigar', 2, {'plano': {}}, 'e o mac?', {}) is None
    assert PERFIL_LAB10.bloquear('Veja ip neigh e cat /etc/resolv.conf.', 'dns', 2, {'chamado': {'correta': True}}, 'e?', {}) is None
    assert PERFIL_LAB8.bloquear('Edite /etc/network/interfaces.', 'novo', 2, {'chamado': {'correta': True}}, 'e?', {}) == 'fora_do_tema'
