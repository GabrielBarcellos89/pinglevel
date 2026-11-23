"""Ensaio do Lab 4 numa sessão CORE real, com o código da cópia de trabalho, sem afetar a produção.

- Recusa começar se houver qualquer sessão no CORE (não disputa recursos com alunos).
- Registro de sessões em arquivo temporário (o de produção é apagado pelo backend ao reiniciar) e rede de
  controle 172.30.250.0/24, fora da faixa 1–200 usada pela produção.
- Atende os três chamados como um aluno, inclusive os erros previstos no roteiro (doc 46), guarda as saídas
  reais do iproute2 e do ping, conclui sem XP real e confirma a remoção da sessão.
Uso: .qa/venv/bin/python -B tools/qa/ensaio_core_lab4.py
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
from laboratorios.terminal_guiado import ErroTerminal, ServicoTerminal  # noqa: E402

UID, LOGIN = 900001, 'ensaio-lab4'


def sessoes_core():
    core = client.CoreGrpcClient()
    core.connect()
    try:
        return [s.id for s in core.get_sessions()]
    finally:
        core.close()


def main():
    existentes = sessoes_core()
    if existentes:
        sys.exit(f'Há sessões no CORE ({existentes}); ensaio não iniciado para não disputar recursos com alunos.')
    gerenciador.ARQUIVO_ESTADO = Path(tempfile.mkdtemp(prefix='ensaio-lab4-')) / 'laboratorios_ativos.json'
    engine = gerenciador.GerenciadorLaboratorios()
    engine._indice_disponivel = lambda uid: 250
    servico = ServicoTerminal(engine, lambda uid, lab: {'xp_concedido': 0})
    registro, falhas = [], []

    def act(acao, **extra):
        if acao in ('status', 'iniciar'):
            return servico.executar_acao(UID, LOGIN, acao, extra)
        estado = servico.executar_acao(UID, LOGIN, 'status', {})
        return servico.executar_acao(UID, LOGIN, acao, {'session_id': estado['laboratorio']['session_id'],
                                                        'revisao': estado['missao']['revisao'], **extra})

    def term(comando, espera, pc='novo'):
        resposta = act('terminal', comando=comando, pc=pc)
        missao = resposta['missao']
        captura = next((b for b in resposta.get('bastidores', []) if b['revisao'] == missao['terminal'][-1]['revisao']), None)
        if captura:
            # Bastidores: a captura tshark real do ping, na interface do PC desta sessão.
            print(f"     tshark: {captura['estado']} · {sorted({e['tipo'] for e in captura['eventos']})}", flush=True)
        ultimo = missao['terminal'][-1]
        ok = espera(ultimo, missao)
        registro.append({'pc': pc, 'comando': comando, 'codigo': ultimo['codigo'], 'saida': ultimo['saida'],
                         'confirmacao': ultimo['confirmacao'], 'estado': missao['estados'][pc],
                         'testes': missao['testes'][pc], 'esperado_ok': ok})
        print(f"{'ok ' if ok else 'ERRO'} {pc:10} $ {comando}\n     {(ultimo['saida'] or ultimo['confirmacao'])[:160]!r}", flush=True)
        if not ok:
            falhas.append(f'{pc}: {comando}')
        return missao

    def causa(resposta):
        print(f"     causa {resposta}: {act('diagnosticar', resposta=resposta)['mensagem']}", flush=True)

    servidor = '192.168.20.10'

    def responde(pc, etapa):
        return lambda u, m: m['testes'][pc].get(servidor) is True and m['proxima_etapa'] == etapa

    inicio = time.time()
    try:
        estado = act('iniciar')
        print(f"Sessão {estado['laboratorio']['session_id']} criada em {time.time() - inicio:.1f}s; "
              f"estados: {estado['missao']['estados']}", flush=True)

        # Chamado 1 — PC Novo sem IPv4.
        term('ping 192.168.10.12', lambda u, m: u['codigo'] == 2 and 'unreachable' in u['saida'].lower())
        term('ip addr show', lambda u, m: u['codigo'] == 0 and 'inet ' not in u['saida'] and 'UP' in u['saida'])
        causa('sem-ipv4')
        term('ip route add default via 192.168.10.1', lambda u, m: u['codigo'] != 0 and m['estados']['novo']['rota_padrao'] is None)
        term('ip addr add 192.168.10.30/24 dev eth0', lambda u, m: u['confirmacao'].startswith('eth0: 192.168.10.30/24'))
        term('ping 192.168.10.12', lambda u, m: m['testes']['novo'].get('192.168.10.12') is True)
        term('ip route add default via 192.168.10.1', lambda u, m: m['estados']['novo']['rota_padrao'] == '192.168.10.1')
        term('ip route', lambda u, m: 'default via 192.168.10.1' in u['saida'] and '172.30' not in u['saida'])
        term(f'ping {servidor}', responde('novo', 'chamado-2'))

        # Chamado 2 — PC Financeiro com rota padrão para um computador.
        term(f'ping {servidor}', lambda u, m: m['testes']['financeiro'].get(servidor) is False, 'financeiro')
        term('ping 192.168.10.30', lambda u, m: m['testes']['financeiro'].get('192.168.10.30') is True, 'financeiro')
        term('ip route', lambda u, m: 'default via 192.168.10.11' in u['saida'], 'financeiro')
        causa('gateway-errado')
        term('ip route del default', lambda u, m: m['estados']['financeiro']['rota_padrao'] is None, 'financeiro')
        term('ip route add default via 192.168.10.1', lambda u, m: u['codigo'] == 0, 'financeiro')
        term(f'ping {servidor}', responde('financeiro', 'chamado-3'), 'financeiro')

        # Chamado 3 — PC Recepção com /16: o servidor parece estar na mesma rede.
        term(f'ping {servidor}', lambda u, m: m['testes']['recepcao'].get(servidor) is False, 'recepcao')
        term('ip route', lambda u, m: 'default via 192.168.10.1' in u['saida'] and '192.168.0.0/16' in u['saida'], 'recepcao')
        term('ip addr show', lambda u, m: 'inet 192.168.10.11/16' in u['saida'], 'recepcao')
        causa('prefixo')
        term('ip addr del 192.168.10.11/16 dev eth0', lambda u, m: m['estados']['recepcao']['rota_padrao'] is None, 'recepcao')
        term('ip addr add 192.168.10.11/24 dev eth0', lambda u, m: m['estados']['recepcao']['enderecos'] == ['192.168.10.11/24'], 'recepcao')
        term(f'ping {servidor}', lambda u, m: u['codigo'] == 2 and 'unreachable' in u['saida'].lower(), 'recepcao')
        term('ip route add default via 192.168.10.1', lambda u, m: u['codigo'] == 0, 'recepcao')
        term(f'ping {servidor}', responde('recepcao', 'comprovar'), 'recepcao')

        final = act('validar')
        print(f"Conclusão: {final['conclusao']} · mensagem: {final['mensagem']}", flush=True)
        if not final['conclusao'] or final['ativo']:
            falhas.append('conclusão/limpeza')
    except ErroTerminal as erro:
        falhas.append(f'ErroTerminal {erro.status}: {erro}')
        print(f'Interrompido: {erro}', flush=True)
    finally:
        lab = engine.obter(UID, heartbeat=False)
        if lab:
            try:
                engine.encerrar_confirmado(UID, lab.session_id, 'ensaio do Lab 4')
            except Exception as erro:
                falhas.append(f'limpeza: {erro}')
        restantes = sessoes_core()
        if restantes:
            falhas.append(f'sessões restantes no CORE: {restantes}')
        relatorio = RAIZ / f".qa/ensaio-core-lab4-{time.strftime('%Y%m%d-%H%M%S')}.json"
        relatorio.write_text(json.dumps({'falhas': falhas, 'duracao': round(time.time() - inicio, 1), 'passos': registro},
                                        ensure_ascii=False, indent=1))
        print(f"\n{'APROVADO' if not falhas else 'FALHAS: ' + '; '.join(falhas)} · sessões no CORE agora: {restantes} · {relatorio}")


if __name__ == '__main__':
    main()
