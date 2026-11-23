"""Ensaio da demonstração "Suporte remoto" numa sessão CORE real, com o código da cópia de trabalho, sem afetar a produção.

- Recusa começar se houver qualquer sessão no CORE (não disputa recursos com alunos).
- Registro de sessões em arquivo temporário e redes de controle 172.30.201+ (fora da faixa 1–200 da produção).
- Cada "aluno" faz o roteiro inteiro: ssh real da T.I. ao Financeiro B (usuário e senha), correção do gateway, impressão pela página web da impressora do Prédio A e
  validação. Com --carga N, N alunos fazem isso ao mesmo tempo e o ensaio mede criação, memória e CPU.
Uso: /opt/packetlab/venv/bin/python -B tools/qa/ensaio_core_suporte.py [--carga N]
"""
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'app'))
from core.api.grpc import client  # noqa: E402
import laboratorios.gerenciador as gerenciador  # noqa: E402
from laboratorios import painel_carga  # noqa: E402
from laboratorios.cenarios import suporte_remoto  # noqa: E402
from laboratorios.terminal_guiado import ErroTerminal  # noqa: E402
from laboratorios.terminal_rede import ServicoRede  # noqa: E402
from laboratorios.tutor_setores import PERFIL_SUPORTE  # noqa: E402

UID_BASE = 900100


def sessoes_core():
    core = client.CoreGrpcClient()
    core.connect()
    try:
        return [s.id for s in core.get_sessions()]
    finally:
        core.close()


def aluno(servico, engine, numero, resultados, verbose):
    uid, login = UID_BASE + numero, f'ensaio-{numero}'
    falhas, tempos = [], {}

    def act(acao, **extra):
        if acao in ('status', 'iniciar'):
            return servico.executar_acao(uid, login, acao, extra)
        estado = servico.executar_acao(uid, login, 'status', {})
        return servico.executar_acao(uid, login, acao, {'session_id': estado['laboratorio']['session_id'],
                                                        'revisao': estado['missao']['revisao'], **extra})

    def term(comando, espera):
        missao = act('terminal', comando=comando, pc='ti')['missao']
        ultimo = missao['terminal'][-1]
        ok = espera(ultimo, missao)
        if verbose or not ok:
            onde = ultimo.get('remoto') or 'ti'
            print(f"{'ok ' if ok else 'ERRO'} [{numero}] {onde:7} $ {comando}\n     {ultimo['saida'][:200]!r}", flush=True)
        if not ok:
            falhas.append(comando)
        return missao

    inicio = time.time()
    try:
        act('iniciar')
        tempos['criacao'] = time.time() - inicio
        term('ping 192.168.20.21', lambda u, m: ' 0% packet loss' in u['saida'])
        term('ssh suporte@192.168.20.21', lambda u, m: m['senha_pendente'] and u['saida'].endswith("password:"))
        term('errada', lambda u, m: 'please try again' in u['saida'] and m['remoto'] is None)
        term('suporte123', lambda u, m: u['codigo'] == 0 and u['digitado'] == '' and m['remoto'] == 'fin_b'
             and m['proxima_etapa'] == 'gateway')
        term('ip route', lambda u, m: 'default via 192.168.20.254' in u['saida'] and u.get('remoto') == 'fin_b')
        term('curl http://192.168.10.50', lambda u, m: u['codigo'] != 0 and 'não abriu' in u['saida'])
        term('curl -d "texto=antes do conserto" http://192.168.10.50/imprimir', lambda u, m: u['codigo'] != 0 and not m['folhas'])
        term('ip route del default', lambda u, m: u['codigo'] == 0)
        term('ip route add default via 192.168.20.1', lambda u, m: u['codigo'] == 0 and m['proxima_etapa'] == 'impressao')
        term('ping 192.168.10.50', lambda u, m: ' 0% packet loss' in u['saida'])
        term('curl http://192.168.10.50', lambda u, m: u['codigo'] == 0 and 'Folhas impressas: 0' in u['saida'])
        term(f'curl -d "texto=Folha do aluno {numero}" http://192.168.10.50/imprimir',
             lambda u, m: u['codigo'] == 0 and 'trabalho recebido' in u['saida'] and m['folhas'] and m['proxima_etapa'] == 'comprovar')
        term('exit', lambda u, m: m['remoto'] is None)
        final = act('validar')
        tempos['total'] = time.time() - inicio
        if not final['conclusao'] or final['ativo']:
            falhas.append('conclusão/limpeza')
    except ErroTerminal as erro:
        falhas.append(f'ErroTerminal {erro.status}: {erro}')
        print(f'[{numero}] interrompido: {erro}', flush=True)
    except Exception as erro:  # noqa: BLE001 - o ensaio registra qualquer falha e segue limpando
        falhas.append(f'{type(erro).__name__}: {erro}')
        print(f'[{numero}] falhou: {erro!r}', flush=True)
    finally:
        lab = engine.obter(uid, heartbeat=False)
        if lab:
            try:
                engine.encerrar_confirmado(uid, lab.session_id, 'ensaio suporte remoto')
            except Exception as erro:  # noqa: BLE001
                falhas.append(f'limpeza: {erro}')
    resultados[numero] = {'falhas': falhas, **tempos}


def main():
    carga = int(sys.argv[sys.argv.index('--carga') + 1]) if '--carga' in sys.argv else 1
    if sessoes_core():
        print('Há sessões no CORE: o ensaio não começa para não disputar recursos com alunos.')
        return 2
    gerenciador.ARQUIVO_ESTADO = Path(tempfile.mkdtemp(prefix='ensaio-suporte-')) / 'laboratorios_ativos.json'
    engine = gerenciador.GerenciadorLaboratorios()
    engine._indice_disponivel = lambda uid: 201 + (uid - UID_BASE) % 50
    servico = ServicoRede(engine, lambda uid, lab: {'xp_concedido': 0}, cenario=suporte_remoto, perfil_tutor=PERFIL_SUPORTE)
    resultados, parar = {}, threading.Event()

    def monitorar():
        pico = {'memoria': 0, 'conteineres': 0, 'cpu': 0}
        while not parar.is_set():
            m = painel_carga.coletar(engine)
            pico['memoria'] = max(pico['memoria'], m['conteineres']['memoria'])
            pico['conteineres'] = max(pico['conteineres'], m['conteineres']['quantidade'])
            pico['cpu'] = max(pico['cpu'], m['cpu_percentual'] or 0)
            print(f"   painel: {m['ambientes']['total']} ambientes · {m['conteineres']['quantidade']} contêineres · "
                  f"{m['conteineres']['memoria'] / 2**20:.0f} MiB · CPU {m['cpu_percentual']}% · "
                  f"disponível {m['memoria']['disponivel'] / 2**30:.2f} GiB · carga {m['carga'][0]}", flush=True)
            parar.wait(5)
        resultados['pico'] = pico

    monitor = threading.Thread(target=monitorar, daemon=True)
    monitor.start()
    inicio = time.time()
    alunos = [threading.Thread(target=aluno, args=(servico, engine, n, resultados, carga == 1)) for n in range(carga)]
    for t in alunos:
        t.start()
    for t in alunos:
        t.join()
    parar.set()
    monitor.join(timeout=10)
    pico = resultados.pop('pico', {})
    criacoes = sorted(r['criacao'] for r in resultados.values() if 'criacao' in r)
    falhas = {n: r['falhas'] for n, r in resultados.items() if r['falhas']}
    print(f"\nRESUMO: {carga} aluno(s) em {time.time() - inicio:.0f}s · criação "
          f"{'mín %.1fs / máx %.1fs' % (criacoes[0], criacoes[-1]) if criacoes else '—'} · pico "
          f"{pico.get('conteineres', 0)} contêineres, {pico.get('memoria', 0) / 2**20:.0f} MiB, CPU {pico.get('cpu', 0)}%")
    restantes = sessoes_core()
    if restantes:
        print(f'ATENÇÃO: sessões ainda no CORE: {restantes}')
    print('FALHAS:', falhas if falhas else 'nenhuma')
    return 1 if falhas or restantes else 0


if __name__ == '__main__':
    sys.exit(main())
