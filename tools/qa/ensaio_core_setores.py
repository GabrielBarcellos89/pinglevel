"""Ensaio dos Labs 2 e 5 a 10 numa sessão CORE real, com o código da cópia de trabalho, sem afetar a produção.

- Recusa começar se houver qualquer sessão no CORE (não disputa recursos com alunos).
- Registro de sessões em arquivo temporário (o de produção é apagado pelo backend ao reiniciar) e rede de
  controle 172.30.250.0/24, fora da faixa 1–200 usada pela produção.
- Percorre cada laboratório como um aluno, inclusive erros previstos nos roteiros (docs 53 e 55), guarda as saídas
  reais do iproute2 e do ping, conclui sem XP real e confirma a remoção de cada sessão.
Uso: .qa/venv/bin/python -B tools/qa/ensaio_core_setores.py [2 5 6 7 8 9 10]   (sem números: todos)
"""
import json
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'app'))
from core.api.grpc import client  # noqa: E402
import laboratorios.gerenciador as gerenciador  # noqa: E402
from laboratorios.cenarios import (conectando_redes, desafio_empresa, dividindo_rede, enderecos_nomes,  # noqa: E402
    investigando_lan, planejando_empresa, primeira_lan)
from laboratorios.terminal_guiado import ErroTerminal  # noqa: E402
from laboratorios.terminal_rede import ServicoRede  # noqa: E402
from laboratorios.tutor_setores import (PERFIL_LAB2, PERFIL_LAB5, PERFIL_LAB6, PERFIL_LAB7, PERFIL_LAB8, PERFIL_LAB9,  # noqa: E402
    PERFIL_LAB10)

UID, LOGIN = 900002, 'ensaio-setores'


def sessoes_core():
    core = client.CoreGrpcClient()
    core.connect()
    try:
        return [s.id for s in core.get_sessions()]
    finally:
        core.close()


def medir(session_id, lab, segundos):
    """Memória e CPU dos containers desta sessão (nomes pl-s<sessão>-...), para estimar alunos simultâneos."""
    import subprocess
    saida = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.Name}} {{.MemUsage}} {{.CPUPerc}}'],
                           capture_output=True, text=True, timeout=60).stdout
    linhas = [l.split() for l in saida.splitlines() if l.startswith(f'pl-s{session_id}-')]
    def mib(v):
        n = float(v.rstrip('KMGiB'))
        return n / 1024 if v.endswith('KiB') else n * 1024 if v.endswith('GiB') else n
    total = sum(mib(l[1]) for l in linhas)
    print(f"RECURSOS {lab}: {len(linhas)} containers, {total:.1f} MiB, criação em {segundos:.1f}s", flush=True)


def ensaiar(engine, cenario, perfil, roteiro, registro, falhas):
    servico = ServicoRede(engine, lambda uid, lab: {'xp_concedido': 0}, cenario=cenario, perfil_tutor=perfil)

    def act(acao, **extra):
        if acao in ('status', 'iniciar'):
            return servico.executar_acao(UID, LOGIN, acao, extra)
        estado = servico.executar_acao(UID, LOGIN, 'status', {})
        return servico.executar_acao(UID, LOGIN, acao, {'session_id': estado['laboratorio']['session_id'],
                                                        'revisao': estado['missao']['revisao'], **extra})

    def term(no, comando, espera):
        resposta = act('terminal', comando=comando, pc=no)
        missao = resposta['missao']
        ultimo = missao['terminal'][-1]
        captura = next((b for b in resposta.get('bastidores', []) if b['revisao'] == ultimo['revisao']), None)
        if captura:
            # Bastidores: a captura tshark real do comando, na interface do nó desta sessão.
            tipos = [e['tipo'] for e in captura['eventos']]
            print(f"     tshark: {captura['estado']} · {len(tipos)} pacotes · {sorted(set(tipos))}", flush=True)
            registro.append({'lab': cenario.LABORATORIO_ID, 'no': no, 'captura': captura['estado'], 'pacotes': tipos})
            if captura['estado'] not in ('concluida', 'vazia'):
                falhas.append(f"{cenario.LABORATORIO_ID} {no}: captura {captura['estado']} ({captura['mensagem']})")
        ok = espera(ultimo, missao)
        registro.append({'lab': cenario.LABORATORIO_ID, 'no': no, 'comando': comando, 'codigo': ultimo['codigo'],
                         'saida': ultimo['saida'], 'confirmacao': ultimo['confirmacao'], 'estado': missao['estados'][no], 'ok': ok})
        print(f"{'ok ' if ok else 'ERRO'} {no:11} $ {comando}\n     {(ultimo['saida'] or ultimo['confirmacao'])[:150]!r}", flush=True)
        if not ok:
            falhas.append(f'{cenario.LABORATORIO_ID} {no}: {comando}')
        return missao

    inicio = time.time()
    try:
        estado = act('iniciar')
        print(f"\n== {cenario.TITULO}: sessão {estado['laboratorio']['session_id']} em {time.time() - inicio:.1f}s; "
              f"estados: {estado['missao']['estados']}", flush=True)
        medir(estado['laboratorio']['session_id'], cenario.LABORATORIO_ID, time.time() - inicio)
        roteiro(act, term)
        final = act('validar')
        print(f"Conclusão: {final['conclusao']} · {final['mensagem']}", flush=True)
        if not final['conclusao'] or final['ativo']:
            falhas.append(f'{cenario.LABORATORIO_ID}: conclusão/limpeza')
    except ErroTerminal as erro:
        falhas.append(f'{cenario.LABORATORIO_ID}: ErroTerminal {erro.status}: {erro}')
        print(f'Interrompido: {erro}', flush=True)
    finally:
        lab = engine.obter(UID, heartbeat=False)
        if lab:
            try:
                engine.encerrar_confirmado(UID, lab.session_id, f'ensaio {cenario.LABORATORIO_ID}')
            except Exception as erro:
                falhas.append(f'limpeza: {erro}')


def roteiro_lab2(act, term):
    # Estado inicial real: PC 1 em /24, PC 2 sem endereço, PC 3 em /28 (o PC 1 fica fora da rede dele).
    term('pc1', 'ip addr show', lambda u, m: 'inet 192.168.10.10/24' in u['saida'])
    term('pc2', 'ip addr show', lambda u, m: 'inet ' not in u['saida'])
    act('planejar', respostas={'rede': '192.168.10.0', 'prefixo': '/24', 'mascara': '255.255.255.0'})
    term('pc2', 'ip addr add 192.168.10.20/24 dev eth0', lambda u, m: u['codigo'] == 0)
    term('pc2', 'ping 192.168.10.10', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'chamado')
    term('pc3', 'ping 192.168.10.10', lambda u, m: u['codigo'] == 2 and 'unreachable' in u['saida'].lower())
    term('pc3', 'ip addr show', lambda u, m: 'inet 192.168.10.40/28' in u['saida'])
    act('diagnosticar', resposta='prefixo')
    term('pc3', 'ip addr del 192.168.10.40/28 dev eth0', lambda u, m: u['codigo'] == 0)
    term('pc3', 'ip addr add 192.168.10.40/24 dev eth0', lambda u, m: u['codigo'] == 0)
    term('pc3', 'ping 192.168.10.10', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'comprovar')


def roteiro_lab5(act, term):
    ping_ok = lambda ip: lambda u, m, ip=ip: u['codigo'] == 0 and ' 0% packet loss' in u['saida']  # noqa: E731
    term('v1', 'ping 192.168.50.1', ping_ok('192.168.50.1'))
    term('v2', 'ping 192.168.50.10', lambda u, m: u['codigo'] == 2 and 'unreachable' in u['saida'].lower())
    term('roteador', 'ip addr show', lambda u, m: '192.168.50.1/26' in u['saida'] and 'eth1' in u['saida'])
    act('planejar', respostas={'rede': '192.168.50.64', 'gateway': '192.168.50.65', 'broadcast': '192.168.50.127'})
    term('roteador', 'ip addr add 192.168.50.65/26 dev eth1', lambda u, m: m['proxima_etapa'] == 'financeiro')
    term('roteador', 'ip route', lambda u, m: '192.168.50.64/26 dev eth1' in u['saida'] and '172.30' not in u['saida'])
    for no, ip in (('f1', '192.168.50.66'), ('f2', '192.168.50.67')):
        term(no, f'ip addr add {ip}/26 dev eth0', lambda u, m: u['codigo'] == 0)
        term(no, 'ip route add default via 192.168.50.65', lambda u, m: u['codigo'] == 0)
    term('f1', 'ping 192.168.50.67', ping_ok(''))
    term('f1', 'ping 192.168.50.10', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'chamado')
    term('v2', 'ip addr show', lambda u, m: 'inet 192.168.50.70/26' in u['saida'])
    act('diagnosticar', resposta='fora-do-bloco')
    term('v2', 'ip addr del 192.168.50.70/26 dev eth0', lambda u, m: u['codigo'] == 0)
    term('v2', 'ip addr add 192.168.50.20/26 dev eth0', lambda u, m: u['codigo'] == 0)
    term('v2', 'ip route add default via 192.168.50.1', lambda u, m: u['codigo'] == 0)
    term('v2', 'ping 192.168.50.66', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'comprovar')


def roteiro_lab6(act, term):
    plano = {'atendimento-prefixo': '25', 'atendimento-rede': '192.168.80.0', 'vendas-prefixo': '26',
             'vendas-rede': '192.168.80.128', 'financeiro-prefixo': '27', 'financeiro-rede': '192.168.80.192'}
    act('planejar', respostas=plano)
    for linha in ('ip addr add 192.168.80.1/25 dev eth0', 'ip addr add 192.168.80.129/26 dev eth1',
                  'ip addr add 192.168.80.193/27 dev eth2'):
        term('roteador', linha, lambda u, m: u['codigo'] == 0)
    term('roteador', 'ip route', lambda u, m: all(r in u['saida'] for r in ('192.168.80.0/25', '192.168.80.128/26', '192.168.80.192/27')))
    # Erro previsto: /25 no PC Vendas aceita a rota pelo .129, mas o ping ao Atendimento falha (o PC acha que .10 é local).
    term('vendas', 'ip addr add 192.168.80.140/25 dev eth0', lambda u, m: u['codigo'] == 0)
    term('vendas', 'ip route add default via 192.168.80.129', lambda u, m: u['codigo'] == 0)
    term('vendas', 'ping 192.168.80.10', lambda u, m: u['codigo'] != 0)
    term('vendas', 'ip addr del 192.168.80.140/25 dev eth0', lambda u, m: m['estados']['vendas']['rota_padrao'] is None)
    term('vendas', 'ip addr add 192.168.80.140/26 dev eth0', lambda u, m: u['codigo'] == 0)
    term('vendas', 'ip route add default via 192.168.80.129', lambda u, m: u['codigo'] == 0)
    for no, ip, gw in (('atendimento', '192.168.80.10/25', '192.168.80.1'), ('financeiro', '192.168.80.200/27', '192.168.80.193')):
        term(no, f'ip addr add {ip} dev eth0', lambda u, m: u['codigo'] == 0)
        term(no, f'ip route add default via {gw}', lambda u, m: u['codigo'] == 0)
    term('atendimento', 'ping 192.168.80.140', lambda u, m: ' 0% packet loss' in u['saida'])
    term('atendimento', 'ping 192.168.80.200', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'comprovar')


def roteiro_lab7(act, term):
    falha = lambda u, m: u['codigo'] != 0 and '100% packet loss' in u['saida']  # noqa: E731
    term('pca', 'ping 192.168.20.10', falha)
    term('pca', 'ping 10.0.0.1', lambda u, m: ' 0% packet loss' in u['saida'])
    term('pca', 'ping 10.0.0.2', falha)
    term('r1', 'ip route', lambda u, m: '10.0.0.0/30 dev eth1' in u['saida'] and '192.168.20' not in u['saida'] and '172.30' not in u['saida'])
    act('diagnosticar', resposta='sem-rota')
    act('planejar', respostas={'r1-destino': '192.168.20.0/24', 'r1-via': '10.0.0.2', 'r2-destino': '192.168.10.0/24', 'r2-via': '10.0.0.1'})
    term('r1', 'ip route add 192.168.20.0/24 via 192.168.20.1', lambda u, m: 'Nexthop' in u['saida'] and m['estados']['r1']['rotas'] == [])
    term('r1', 'ip route add 192.168.20.0/24 via 10.0.0.2', lambda u, m: m['estados']['r1']['rotas'] == ['192.168.20.0/24 via 10.0.0.2'])
    term('pca', 'ping 192.168.20.10', lambda u, m: falha(u, m) and m['proxima_etapa'] == 'volta')
    term('r2', 'ip route add 192.168.10.0/24 via 10.0.0.1', lambda u, m: m['estados']['r2']['rotas'] == ['192.168.10.0/24 via 10.0.0.1'])
    term('r2', 'ip route', lambda u, m: '192.168.10.0/24 via 10.0.0.1' in u['saida'])
    term('pca', 'ping 192.168.20.10', lambda u, m: ' 0% packet loss' in u['saida'] and m['proxima_etapa'] == 'comprovar')
    term('pcb', 'ping 192.168.10.10', lambda u, m: ' 0% packet loss' in u['saida'])


def roteiro_lab9(act, term):
    ok = lambda u, m: ' 0% packet loss' in u['saida']  # noqa: E731
    falha = lambda u, m: u['codigo'] != 0 and '100% packet loss' in u['saida']  # noqa: E731
    mac_f2 = investigando_lan.MACS['f2']
    term('f1', 'ip neigh', lambda u, m: mac_f2 not in u['saida'])
    term('f1', 'ping 192.168.30.22', ok)
    term('f1', 'ip neigh show', lambda u, m: mac_f2 in u['saida'] and 'lladdr' in u['saida'])
    term('f2', 'ip link show', lambda u, m: mac_f2 in u['saida'])
    term('switch', 'bridge link', lambda u, m: 'eth3' in u['saida'] and 'ctrl' not in u['saida'])
    term('switch', 'bridge fdb show', lambda u, m: f'{mac_f2} dev eth3' in u['saida'] and 'permanent' not in u['saida'])
    act('planejar', respostas={'mac-f2': mac_f2.upper(), 'porta-f2': 'eth3'})
    term('v2', 'ping 192.168.30.11', falha)
    term('switch', 'bridge vlan show', lambda u, m: 'eth1' in u['saida'] and '20' in u['saida'] and 'ctrl' not in u['saida'])
    act('diagnosticar', resposta='vlan-errada')
    term('switch', 'bridge vlan add dev eth1 vid 10 pvid untagged', lambda u, m: m['estados']['switch']['vlans']['eth1']['pvid'] == 10)
    term('switch', 'bridge vlan del dev eth1 vid 20', lambda u, m: m['estados']['switch']['vlans']['eth1'] == investigando_lan.acesso(10))
    term('v2', 'ping 192.168.30.11', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'separar')
    term('f1', 'ping 192.168.30.11', falha)
    for porta in ('eth2', 'eth3'):
        term('switch', f'bridge vlan add dev {porta} vid 20 pvid untagged', lambda u, m: u['codigo'] == 0)
        term('switch', f'bridge vlan del dev {porta} vid 1', lambda u, m, p=porta: m['estados']['switch']['vlans'][p] == investigando_lan.acesso(20))
    term('f1', 'ping 192.168.30.22', ok)
    term('f1', 'ping 192.168.30.11', lambda u, m: falha(u, m) and m['proxima_etapa'] == 'comprovar')


def recusado(act, no, comando, trecho):
    """Comando que o laboratório deve recusar, com a mensagem esperada."""
    try:
        act('terminal', comando=comando, pc=no)
    except ErroTerminal as erro:
        print(f"ok  {no:11} $ {comando}\n     recusado: {erro}", flush=True)
        if trecho not in str(erro):
            raise ErroTerminal(f'Recusa inesperada para {comando}: {erro}') from erro
        return
    raise ErroTerminal(f'Deveria ter sido recusado: {comando}')


def roteiro_lab8(act, term):
    ok = lambda u, m: ' 0% packet loss' in u['saida']  # noqa: E731
    falha = lambda u, m: ' 0% packet loss' not in u['saida']  # noqa: E731
    intranet, impressora = enderecos_nomes.INTRANET, enderecos_nomes.IMPRESSORA
    term('novo', 'ip addr show', lambda u, m: 'inet ' not in u['saida'] and 'UP' in u['saida'])
    recusado(act, 'novo', 'dhclient eth0', 'responda no chamado')
    act('diagnosticar', resposta='cabo')
    act('diagnosticar', resposta='sem-endereco')
    term('novo', 'dhclient eth0', lambda u, m: 'lease of 192.168.40.1' in u['saida'] and m['estados']['novo']['dns'] == ['192.168.40.2'])
    term('novo', 'cat /etc/resolv.conf', lambda u, m: 'nameserver 192.168.40.2' in u['saida'])
    term('novo', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'recepcao')
    term('recepcao', 'ping 192.168.40.20', ok)
    term('recepcao', f'nslookup {intranet}', lambda u, m: u['codigo'] != 0)
    term('recepcao', 'cat /etc/resolv.conf', lambda u, m: '192.168.40.9' in u['saida'])
    act('diagnosticar', resposta='dns-errado')
    term('recepcao', 'udhcpc -i eth0', lambda u, m: m['estados']['recepcao']['interfaces']['eth0'] != ['192.168.40.60/24']
         and m['estados']['recepcao']['dns'] == ['192.168.40.2'])
    term('recepcao', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'financeiro')
    term('financeiro', 'nslookup impresora.empresa.local', lambda u, m: 'NXDOMAIN' in u['saida'])
    recusado(act, 'financeiro', 'udhcpc -i eth0', 'responda no chamado')
    act('diagnosticar', resposta='nome')
    recusado(act, 'financeiro', 'udhcpc -i eth0', 'não há nada para alterar')
    term('financeiro', 'ping impresora.empresa.local', falha)
    term('financeiro', f'ping {impressora}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'comprovar')


def roteiro_lab10(act, term):
    ok = lambda u, m: ' 0% packet loss' in u['saida']  # noqa: E731
    falha = lambda u, m: ' 0% packet loss' not in u['saida']  # noqa: E731
    intranet = desafio_empresa.INTRANET
    term('v1', f'nslookup {intranet}', lambda u, m: '192.168.60.20' in u['saida'])
    term('v1', 'ping 192.168.10.1', ok)
    term('v1', f'ping {intranet}', falha)
    term('roteador', 'ping 192.168.60.20', ok)
    term('intranet', 'ip route', lambda u, m: '192.168.60.254' in u['saida'] and 'ctrl' not in u['saida'])
    act('diagnosticar', resposta='rota')
    term('intranet', 'ip route del default', lambda u, m: u['codigo'] == 0)
    term('intranet', 'ip route add default via 192.168.60.1', lambda u, m: m['estados']['intranet']['rota_padrao'] == '192.168.60.1')
    term('v1', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'vlan')
    term('v2', 'ping 192.168.10.1', falha)
    term('switch', 'bridge vlan show', lambda u, m: 'eth1' in u['saida'])
    act('diagnosticar', resposta='vlan')
    term('switch', 'bridge vlan add dev eth1 vid 10 pvid untagged', lambda u, m: u['codigo'] == 0)
    term('switch', 'bridge vlan del dev eth1 vid 20', lambda u, m: m['estados']['switch']['vlans']['eth1'] == desafio_empresa.acesso(10))
    term('v2', 'ping 192.168.10.1', lambda u, m: True)  # o primeiro pacote depois da troca de VLAN pode se perder
    term('v2', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'dhcp')
    term('f1', 'ip addr show', lambda u, m: 'inet ' not in u['saida'])
    act('diagnosticar', resposta='sem-endereco')
    term('f1', 'dhclient eth0', lambda u, m: 'lease of 192.168.20.1' in u['saida'])
    term('f1', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'dns')
    term('f2', 'ping 192.168.60.20', ok)
    term('f2', 'cat /etc/resolv.conf', lambda u, m: '192.168.20.9' in u['saida'])
    act('diagnosticar', resposta='dns-errado')
    term('f2', 'udhcpc -i eth0', lambda u, m: m['estados']['f2']['dns'] == ['192.168.20.1'])
    term('f2', f'ping {intranet}', lambda u, m: ok(u, m) and m['proxima_etapa'] == 'comprovar')


def main():
    existentes = sessoes_core()
    if existentes:
        sys.exit(f'Há sessões no CORE ({existentes}); ensaio não iniciado para não disputar recursos com alunos.')
    gerenciador.ARQUIVO_ESTADO = Path(tempfile.mkdtemp(prefix='ensaio-setores-')) / 'laboratorios_ativos.json'
    engine = gerenciador.GerenciadorLaboratorios()
    engine._indice_disponivel = lambda uid: 250
    registro, falhas = [], []
    inicio = time.time()
    labs = {'2': (primeira_lan, PERFIL_LAB2, roteiro_lab2), '5': (dividindo_rede, PERFIL_LAB5, roteiro_lab5), '6': (planejando_empresa, PERFIL_LAB6, roteiro_lab6),
            '7': (conectando_redes, PERFIL_LAB7, roteiro_lab7), '8': (enderecos_nomes, PERFIL_LAB8, roteiro_lab8),
            '9': (investigando_lan, PERFIL_LAB9, roteiro_lab9), '10': (desafio_empresa, PERFIL_LAB10, roteiro_lab10)}
    for numero in sys.argv[1:] or labs:
        ensaiar(engine, *labs[numero], registro, falhas)
    restantes = sessoes_core()
    if restantes:
        falhas.append(f'sessões restantes no CORE: {restantes}')
    relatorio = RAIZ / f".qa/ensaio-core-setores-{time.strftime('%Y%m%d-%H%M%S')}.json"
    relatorio.write_text(json.dumps({'falhas': falhas, 'duracao': round(time.time() - inicio, 1), 'passos': registro},
                                    ensure_ascii=False, indent=1))
    print(f"\n{'APROVADO' if not falhas else 'FALHAS: ' + '; '.join(falhas)} · sessões no CORE agora: {restantes} · {relatorio}")


if __name__ == '__main__':
    main()
