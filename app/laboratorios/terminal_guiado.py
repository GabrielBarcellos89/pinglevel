"""Lab4 — chamados de suporte pelo terminal: somente I/O do engine injetado, sem CORE/DB no import."""
from contextlib import contextmanager, nullcontext
import ipaddress
import json
import re
import threading
import time
from copy import deepcopy

from laboratorios.cenarios import configure_terminal as cenario
from laboratorios.captura import registrar_bastidores
from laboratorios.terminal_comandos import ErroComando, filtrar_rotas, interpretar
from laboratorios.tutor_lab4 import PERFIL as PERFIL_TUTOR
from laboratorios.tutor_referencias import TutorReferencias

LER_ENDERECOS = 'ip -j addr show dev eth0'
LER_ROTA = 'ip -j -4 route show default'
HISTORICO = 30


class ErroTerminal(ValueError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


def alcance_ping(codigo, saida):
    stats = re.search(r'(\d+) packets transmitted,\s*(\d+)(?: packets)? received.*?(\d+(?:\.\d+)?)% packet loss', saida)
    return bool(codigo == 0 and stats and int(stats[1]) == 2 and int(stats[2]) == 2 and float(stats[3]) == 0)


class ServicoTerminal:
    def __init__(self, gerenciador, concluir_laboratorio, consultar_progresso=None, tutor=None):
        self.engine = gerenciador
        self.concluir = concluir_laboratorio
        self.consultar_progresso = consultar_progresso
        self.tutor = tutor or TutorReferencias(perfil=PERFIL_TUTOR)
        self._estados = {}
        self._finalizadas = {}
        self._locks = {}
        self._lock = threading.RLock()
        self._tutor_pendente = set()

    @contextmanager
    def _serializar(self, uid):
        with self._lock:
            lock = self._locks.setdefault(uid, threading.RLock())
        with lock, self.engine.trava(uid):
            yield

    def _dados(self, lab):
        registro = self._estados.get(lab.usuario_id)
        if registro is None or registro['lab'] is not lab:
            registro = {'lab': lab, 'dados': cenario.dados_iniciais()}
            self._estados[lab.usuario_id] = registro
        return registro['dados']

    def _status(self, uid, mensagem=''):
        lab = self.engine.obter(uid)
        ativo = bool(lab and lab.laboratorio_id == cenario.LABORATORIO_ID)
        conflito = None if not lab or ativo else {'laboratorio_id': lab.laboratorio_id,
            'titulo': 'Outro laboratório está ativo. Encerre-o na própria página.'}
        registro = self._finalizadas.get(uid)
        if ativo:
            registro = registro if registro and registro['lab'] is lab else None
        elif self.consultar_progresso:
            try:
                resumo = self.consultar_progresso(uid)
                registro = next((r for r in resumo['laboratorios']
                    if r.get('laboratorio_id') == cenario.LABORATORIO_ID and r.get('concluido') is True), None)
            except Exception as erro:
                raise ErroTerminal('Não foi possível confirmar o progresso salvo.', 503) from erro
        missao = cenario.estado_publico(self._dados(lab) if ativo else None, ativo)
        conclusao = None
        if registro and registro.get('concluido'):
            missao['concluido'] = True
            conclusao = {'registrada': True, 'encerramento_pendente': ativo, 'concluido_em': registro.get('concluido_em')}
        pendente = bool(ativo and not getattr(lab, 'preparacao_confirmada', True))
        return {'sucesso': True, 'disponivel': not pendente, 'preparacao_pendente': pendente, 'ativo': ativo,
            'conflito': conflito, 'laboratorio': {'session_id': lab.session_id, **self.engine.dados_temporais(lab)} if ativo else None,
            'missao': missao, 'conclusao': conclusao, 'mensagem': mensagem,
            'tutoria': deepcopy(self._estados.get(uid, {}).get('conversas', [])) if ativo else [],
            'bastidores': deepcopy(self._dados(lab).get('bastidores', [])) if ativo else []}

    def _mesma_sessao(self, lab):
        atual = self.engine.obter(lab.usuario_id)
        if atual is not lab or atual.laboratorio_id != cenario.LABORATORIO_ID:
            raise ErroTerminal('A sessão expirou ou mudou. Consulte o estado atual.', 409)

    def _contexto(self, uid, dados):
        lab = self.engine.obter(uid)
        if not lab or lab.laboratorio_id != cenario.LABORATORIO_ID:
            raise ErroTerminal('Inicie este laboratório; nenhuma outra sessão será alterada.', 409)
        s = self._dados(lab)
        if type(dados.get('session_id')) is not int or dados['session_id'] != lab.session_id:
            raise ErroTerminal('A sessão mudou. Consulte o estado atual.', 409)
        if type(dados.get('revisao')) is not int or dados['revisao'] != s['revisao']:
            raise ErroTerminal('A revisão mudou. Consulte o estado atual.', 409)
        return lab, s

    def _comando(self, lab, pc, cmd):
        nome = cenario.PCS[pc]['nome']
        with self.engine.trava(lab.usuario_id):
            self._mesma_sessao(lab)
            try:
                resultado = self.engine.executar(lab.usuario_id, cenario.PCS[pc]['no'], cmd, timeout=8)
            except Exception as erro:
                raise ErroTerminal(f'Não foi possível executar o comando no {nome}.', 503) from erro
            self._mesma_sessao(lab)
            if (not isinstance(resultado, (tuple, list)) or len(resultado) != 2
                    or type(resultado[0]) is not int or not isinstance(resultado[1], str)):
                raise ErroTerminal(f'Resposta inválida do {nome}.', 503)
            return resultado[0], resultado[1]

    def _ler_estado(self, lab, pc):
        """Endereços IPv4 de eth0 e rota padrão, lidos do nó real a cada consulta."""
        try:
            codigo, saida = self._comando(lab, pc, LER_ENDERECOS)
            interfaces = json.loads(saida) if codigo == 0 else None
            if not isinstance(interfaces, list) or len(interfaces) != 1 or interfaces[0].get('ifname') != 'eth0':
                raise ValueError()
            enderecos = [str(ipaddress.IPv4Interface(f"{a['local']}/{a['prefixlen']}"))
                for a in interfaces[0].get('addr_info', []) if a.get('family') == 'inet']
            codigo, saida = self._comando(lab, pc, LER_ROTA)
            rotas = json.loads(saida) if codigo == 0 else None
            if not isinstance(rotas, list):
                raise ValueError()
            padrao = [r for r in rotas if isinstance(r, dict) and r.get('dev') == 'eth0' and r.get('dst') == 'default']
            rota = str(ipaddress.IPv4Address(padrao[0]['gateway'])) if len(padrao) == 1 and 'gateway' in padrao[0] else None
            ativa = 'UP' in interfaces[0].get('flags', [])
        except (ValueError, TypeError, KeyError) as erro:
            raise ErroTerminal(f"Não foi possível ler a configuração real do {cenario.PCS[pc]['nome']}.", 503) from erro
        return {'enderecos': enderecos, 'rota_padrao': rota, 'lido': True, 'ativa': ativa}

    def _atualizar_estado(self, lab, s, pc):
        novo = self._ler_estado(lab, pc)
        anterior = s['estados'][pc]
        # Testes feitos com outra configuração deixam de valer.
        if (novo['enderecos'], novo['rota_padrao']) != (anterior['enderecos'], anterior['rota_padrao']):
            s['testes'][pc] = {}
        s['estados'][pc] = novo
        return novo

    def _ping(self, lab, pc, destino):
        codigo, saida = self._comando(lab, pc, f'ping -n -c 2 -W 1 {destino}')
        if codigo not in (0, 1, 2):
            raise ErroTerminal('O teste de rede não foi executado com confirmação.', 503)
        return codigo, saida, alcance_ping(codigo, saida)

    @staticmethod
    def _confirmacao(estado):
        """Resumo do estado novo, mostrado quando um comando que altera a configuração não imprime nada."""
        enderecos = ', '.join(estado['enderecos']) or 'sem endereço IPv4'
        rota = f"via {estado['rota_padrao']}" if estado['rota_padrao'] else 'nenhuma'
        return f'eth0: {enderecos} · rota padrão: {rota}'

    def _terminal(self, lab, s, pc, texto):
        if pc not in cenario.PCS:
            raise ErroTerminal('Escolha um dos computadores do laboratório.')
        try:
            comando = interpretar(texto, cenario.em_uso(s['estados'], pc))
        except ErroComando as erro:
            raise ErroTerminal(str(erro)) from erro
        if comando.altera:
            chamado = cenario.chamado_atual(s)
            if chamado is None:
                raise ErroTerminal('Os três chamados estão resolvidos. Conclua a missão para o servidor conferir.')
            if chamado['pc'] != pc:
                alvo = cenario.PCS[chamado['pc']]['nome']
                raise ErroTerminal(f'O chamado aberto é do {alvo}. Você pode observar este computador, mas só altere o {alvo}.')
            if not s['diagnosticos'][chamado['id']]['correta']:
                raise ErroTerminal(f'Antes de alterar o {cenario.PCS[pc]["nome"]}, responda no chamado: qual é a causa do problema?')
        s['revisao'] += 1
        observar = getattr(self.engine, 'observar', None)
        with (observar(lab.usuario_id, cenario.PCS[pc]['no']) if observar and comando.tipo == 'ping' else nullcontext()) as captura:
            if comando.tipo == 'ping':
                codigo, saida, alcance = self._ping(lab, pc, comando.alvo)
            else:
                codigo, saida = self._comando(lab, pc, comando.executar)
                alcance = None
        if captura:
            registrar_bastidores(s, pc, texto, captura)
        if comando.tipo == 'ver-rotas' and codigo == 0:
            saida = filtrar_rotas(saida)
        estado = self._atualizar_estado(lab, s, pc)
        if comando.tipo == 'ping':
            s['testes'][pc][comando.alvo] = alcance
        s['terminal'].append({'pc': pc, 'digitado': ' '.join(texto.split()), 'saida': saida[-4000:], 'codigo': codigo,
            'alcance': alcance, 'tipo': comando.tipo, 'revisao': s['revisao'],
            'confirmacao': self._confirmacao(estado) if comando.altera and codigo == 0 and not saida.strip() else ''})
        del s['terminal'][:-HISTORICO]

    def _encerrar(self, lab):
        self._mesma_sessao(lab)
        try:
            ok = self.engine.encerrar_confirmado(lab.usuario_id, lab.session_id, 'configure pelo terminal: encerramento solicitado')
            if not ok or self.engine.obter(lab.usuario_id) is lab:
                raise RuntimeError('Remoção não confirmada')
        except Exception as erro:
            raise ErroTerminal('A remoção do ambiente ainda não foi confirmada.', 503) from erro
        self._estados.pop(lab.usuario_id, None)

    def _finalizar(self, lab, xp=0):
        try:
            self._encerrar(lab)
            msg = 'Conclusão registrada e ambiente encerrado.'
        except ErroTerminal:
            msg = 'Conclusão registrada; remoção do ambiente pendente. Tente encerrar novamente.'
        return {**self._status(lab.usuario_id, msg), 'xp_concedido': xp}

    def _validar(self, uid, lab, s, dados):
        if cenario.estado_publico(s, True)['proxima_etapa'] != 'comprovar':
            raise ErroTerminal('Resolva os três chamados, com o servidor respondendo em cada PC, antes de concluir.')
        s['revisao'] += 1
        estados = {pc: self._atualizar_estado(lab, s, pc) for pc in cenario.PCS}
        mudou = [cenario.PCS[pc]['nome'] for pc in cenario.PCS if not cenario.configuracao_ok(s['estados'], pc)]
        if mudou:
            raise ErroTerminal(f"A configuração mudou em: {', '.join(mudou)}. Confira antes de concluir.")
        for pc in cenario.PCS:
            s['testes'][pc][cenario.SERVIDOR] = self._ping(lab, pc, cenario.SERVIDOR)[2]
        if (any(self._ler_estado(lab, pc) != estados[pc] for pc in cenario.PCS)
                or not all(s['testes'][pc].get(cenario.SERVIDOR) is True for pc in cenario.PCS)):
            raise ErroTerminal('A comunicação não foi confirmada agora; teste novamente antes de concluir.')
        self._mesma_sessao(lab)
        try:
            progresso = self.concluir(uid, cenario.LABORATORIO_ID)
            if not isinstance(progresso, dict) or type(progresso.get('xp_concedido')) is not int or progresso['xp_concedido'] < 0:
                raise ValueError('Confirmação de progresso inválida')
        except Exception as erro:
            raise ErroTerminal('A conclusão não foi confirmada; tente registrar novamente.', 503) from erro
        s['conclusao_validada'] = True
        self._finalizadas[uid] = {'lab': lab, 'concluido': True, 'concluido_em': int(time.time()),
            'revisao': s['revisao'], 'revisao_recebida': dados['revisao']}
        return self._finalizar(lab, progresso['xp_concedido'])

    def _perguntar_tutor(self, uid, dados):
        pergunta = dados.get('pergunta')
        if not isinstance(pergunta, str) or not 1 <= len(pergunta.strip()) <= 500:
            raise ErroTerminal('Escreva uma dúvida de até 500 caracteres.')
        pergunta = pergunta.strip()
        rascunho = dados.get('rascunho', {})
        if (not isinstance(rascunho, dict) or set(rascunho) - {'comando', 'pc'}
                or any(not isinstance(v, str) or len(v) > 100 for v in rascunho.values())):
            raise ErroTerminal('Rascunho de ajuda inválido.')
        with self._serializar(uid):
            lab, _ = self._contexto(uid, dados)
            if uid in self._tutor_pendente:
                raise ErroTerminal('O Link já está respondendo à sua pergunta. Aguarde.', 429)
            self._tutor_pendente.add(uid)
            contexto = self._status(uid)['missao']
            historico = deepcopy(self._estados[uid].get('conversas', []))
        try:
            resposta = self.tutor.responder(pergunta=pergunta, missao=contexto, historico=historico, rascunho=rascunho)
            with self._serializar(uid):
                atual, _ = self._contexto(uid, dados)
                if atual is not lab:
                    raise ErroTerminal('A sessão mudou durante a resposta. Faça uma nova pergunta.', 409)
                mensagem = {**resposta, 'pergunta': pergunta, 'etapa': contexto.get('proxima_etapa') or 'comprovar'}
                conversas = self._estados[uid].setdefault('conversas', [])
                conversas.append(mensagem)
                del conversas[:-8]
                return {**self._status(uid), 'tutor': mensagem}
        finally:
            with self._lock:
                self._tutor_pendente.discard(uid)

    def executar_acao(self, uid, login, acao, dados):
        if type(uid) is not int or uid <= 0:
            raise ErroTerminal('Sessão de usuário inválida.', 401)
        if not isinstance(dados, dict):
            raise ErroTerminal('Corpo JSON inválido.')
        base = {'session_id', 'revisao'}
        permitidos = {'status': set(), 'iniciar': set(), 'terminal': base | {'comando', 'pc'},
            'diagnosticar': base | {'resposta'}, 'tutor': base | {'pergunta', 'rascunho'},
            'validar': base, 'encerrar': base, 'estender': base}
        if acao not in permitidos:
            raise ErroTerminal('Operação inexistente.', 404)
        if set(dados) - permitidos[acao]:
            raise ErroTerminal('A requisição contém campos não permitidos.')
        if acao == 'tutor':
            return self._perguntar_tutor(uid, dados)
        with self._serializar(uid):
            if acao == 'status':
                return self._status(uid)
            if acao == 'iniciar':
                lab = self.engine.obter(uid)
                if lab and lab.laboratorio_id != cenario.LABORATORIO_ID:
                    raise ErroTerminal('Outro laboratório permanece ativo.', 409)
                if lab and not getattr(lab, 'preparacao_confirmada', True):
                    raise ErroTerminal('Preparação incompleta. Consulte e encerre o ambiente antes de tentar novamente.', 503)
                if not lab:
                    lab = self.engine.criar(uid, login, cenario.LABORATORIO_ID)
                    s = self._dados(lab)
                    for pc, esperado in cenario.INICIAL.items():
                        estado = self._ler_estado(lab, pc)
                        if not estado['ativa'] or {k: estado[k] for k in esperado} != esperado:
                            raise ErroTerminal(f"O {cenario.PCS[pc]['nome']} não foi preparado como previsto. Encerre e inicie novamente.", 503)
                        s['estados'][pc] = estado
                return self._status(uid, 'Ambiente preparado. Três chamados aguardam atendimento.')
            atual = self.engine.obter(uid)
            if atual and atual.laboratorio_id == cenario.LABORATORIO_ID and not getattr(atual, 'preparacao_confirmada', True) and acao != 'encerrar':
                raise ErroTerminal('Preparação incompleta; somente encerramento é permitido.', 503)
            if acao in ('validar', 'encerrar') and atual is None:
                status = self._status(uid)
                if status['conclusao'] and type(dados.get('session_id')) is int and type(dados.get('revisao')) is int:
                    return {**status, 'xp_concedido': 0}
            final = self._finalizadas.get(uid)
            if atual and final and final['lab'] is atual:
                if acao not in ('validar', 'encerrar'):
                    raise ErroTerminal('Conclusão já registrada; encerre antes de reiniciar o treino.', 409)
                if dados.get('session_id') != atual.session_id or dados.get('revisao') not in (final['revisao'], final['revisao_recebida']):
                    raise ErroTerminal('A sessão ou revisão mudou.', 409)
                return self._finalizar(atual)
            lab, s = self._contexto(uid, dados)
            if acao == 'encerrar':
                self._encerrar(lab)
                return self._status(uid, 'Remoção do ambiente confirmada.')
            if acao == 'estender':
                self._mesma_sessao(lab)
                try:
                    self.engine.estender(uid)
                except Exception as erro:
                    raise ErroTerminal('A extensão não foi confirmada.', 503) from erro
                self._mesma_sessao(lab)
                s['revisao'] += 1
                return self._status(uid, 'Tempo estendido.')
            if acao == 'terminal':
                self._terminal(lab, s, dados.get('pc', 'novo'), dados.get('comando'))
                return self._status(uid)
            if acao == 'diagnosticar':
                chamado = cenario.chamado_atual(s)
                if chamado is None:
                    raise ErroTerminal('Os três chamados já estão resolvidos.')
                diagnostico = s['diagnosticos'][chamado['id']]
                if diagnostico['correta']:
                    raise ErroTerminal('A causa deste chamado já foi identificada. Corrija o computador e teste o servidor.')
                if not any(t['tipo'] == chamado['observar'] and t['pc'] == chamado['pc'] for t in s['terminal']):
                    raise ErroTerminal(chamado['pedido_observar'])
                resposta = dados.get('resposta')
                if resposta not in chamado['causas']:
                    raise ErroTerminal('Escolha uma das causas apresentadas.')
                s['revisao'] += 1
                correta = resposta == chamado['correta']
                diagnostico.update(resposta=resposta, correta=correta)
                return self._status(uid, chamado['acerto'] if correta else chamado['erro'])
            return self._validar(uid, lab, s, dados)
