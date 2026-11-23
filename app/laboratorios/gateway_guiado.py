"""Gateway guiado: somente I/O do engine injetado, sem CORE/DB no import."""
from contextlib import contextmanager, nullcontext
import ipaddress
import json
import re
import threading
import time
from copy import deepcopy

from laboratorios.tutor_referencias import TutorReferencias
from laboratorios.captura import registrar_bastidores

from laboratorios.cenarios import saindo_rede_local as cenario

LEITURA = 'ip -j addr show dev eth0'
ROTAS = 'ip -j -4 route show default'
CONTROLE = ipaddress.IPv4Network('172.30.0.0/16')


class ErroGateway(ValueError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


class ServicoGateway:
    def __init__(self, gerenciador, concluir_laboratorio, consultar_progresso=None, tutor=None):
        self.engine = gerenciador
        self.concluir = concluir_laboratorio
        self.consultar_progresso = consultar_progresso
        self._estados = {}
        self._finalizadas = {}
        self._locks = {}
        self._lock = threading.RLock()
        self.tutor = tutor or TutorReferencias()
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
                raise ErroGateway('Não foi possível confirmar o progresso salvo.', 503) from erro
        missao = cenario.estado_publico(self._dados(lab) if ativo else None, ativo)
        if ativo:
            for no in missao['nos']:
                cidr = self._estados[uid].get('baseline', {}).get(no['id'])
                if cidr:
                    interface = ipaddress.IPv4Interface(cidr)
                    no.update(ip=str(interface.ip), prefixo=interface.network.prefixlen)
        if ativo and self._estados[uid].get('roteador'):
            next(n for n in missao['nos'] if n['id'] == 5)['interfaces'] = [
                dict(i) for i in self._estados[uid]['roteador']]
        conclusao = None
        if registro and registro.get('concluido'):
            missao['concluido'] = True
            conclusao = {'registrada': True, 'encerramento_pendente': ativo,
                'concluido_em': registro.get('concluido_em')}
        pendente = bool(ativo and not getattr(lab, 'preparacao_confirmada', True))
        return {'sucesso': True, 'disponivel': not pendente, 'preparacao_pendente': pendente, 'ativo': ativo, 'conflito': conflito,
            'laboratorio': {'session_id': lab.session_id, **self.engine.dados_temporais(lab)} if ativo else None,
            'missao': missao, 'conclusao': conclusao, 'mensagem': mensagem,
            'tutoria': deepcopy(self._estados.get(uid, {}).get('conversas', [])) if ativo else [],
            'bastidores': deepcopy(self._dados(lab).get('bastidores', [])) if ativo else []}

    def _mesma_sessao(self, lab):
        atual = self.engine.obter(lab.usuario_id)
        if atual is not lab or atual.laboratorio_id != cenario.LABORATORIO_ID:
            raise ErroGateway('A sessão expirou ou mudou. Consulte o estado atual.', 409)

    def _contexto(self, uid, dados):
        lab = self.engine.obter(uid)
        if not lab or lab.laboratorio_id != cenario.LABORATORIO_ID:
            raise ErroGateway('Inicie este laboratório; nenhuma outra sessão será alterada.', 409)
        s = self._dados(lab)
        if type(dados.get('session_id')) is not int or dados['session_id'] != lab.session_id:
            raise ErroGateway('A sessão mudou. Consulte o estado atual.', 409)
        if type(dados.get('revisao')) is not int or dados['revisao'] != s['revisao']:
            raise ErroGateway('A revisão mudou. Consulte o estado atual.', 409)
        return lab, s

    def _comando(self, lab, node, cmd):
        with self.engine.trava(lab.usuario_id):
            self._mesma_sessao(lab)
            try:
                resultado = self.engine.executar(lab.usuario_id, node, cmd, timeout=8)
            except Exception as erro:
                raise ErroGateway('Não foi possível executar a operação no nó isolado.', 503) from erro
            self._mesma_sessao(lab)
            if not isinstance(resultado, (tuple, list)) or len(resultado) != 2:
                raise ErroGateway('Resposta inválida do nó isolado.', 503)
            codigo, saida = resultado
            if type(codigo) is not int or not isinstance(saida, str):
                raise ErroGateway('Resposta inválida do nó isolado.', 503)
            return codigo, saida

    def _json(self, lab, node, cmd):
        codigo, saida = self._comando(lab, node, cmd)
        try:
            if codigo != 0 or len(saida) > 32000:
                raise ValueError()
            dados = json.loads(saida)
            if not isinstance(dados, list):
                raise ValueError()
            return dados, saida
        except (ValueError, TypeError) as erro:
            raise ErroGateway('Não foi possível interpretar a configuração real do nó.', 503) from erro

    def _interface(self, lab, node, dev='eth0'):
        dados, _ = self._json(lab, node, LEITURA if dev == 'eth0' else 'ip -j addr show dev eth1')
        try:
            if len(dados) != 1 or dados[0]['ifname'] != dev or 'UP' not in dados[0]['flags']:
                raise ValueError()
            addrs = [a for a in dados[0]['addr_info'] if a.get('family') == 'inet' and a.get('scope') == 'global']
            if len(addrs) != 1 or type(addrs[0]['prefixlen']) is not int:
                raise ValueError()
            interface = ipaddress.IPv4Interface(f"{addrs[0]['local']}/{addrs[0]['prefixlen']}")
            if (not 8 <= interface.network.prefixlen <= 30 or interface.network.overlaps(CONTROLE)
                    or not any(interface.network.subnet_of(ipaddress.IPv4Network(n))
                        for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
                    or interface.ip in (interface.network.network_address, interface.network.broadcast_address)):
                raise ValueError()
            return interface
        except (ValueError, TypeError, KeyError, AttributeError) as erro:
            raise ErroGateway('Não foi possível interpretar a interface real eth0.', 503) from erro

    def _rota(self, lab):
        dados, saida = self._json(lab, 1, ROTAS)
        try:
            if not all(isinstance(r, dict) and isinstance(r.get('dev'), str) for r in dados):
                raise ValueError()
            rotas = [r for r in dados if r['dev'] == 'eth0']
            if not rotas:
                return None, saida
            if (len(rotas) != 1 or rotas[0].get('dst') != 'default' or 'nexthops' in rotas[0]
                    or rotas[0].get('type', 'unicast') != 'unicast'):
                raise ValueError()
            return str(ipaddress.IPv4Address(rotas[0]['gateway'])), saida
        except (ValueError, TypeError, KeyError) as erro:
            raise ErroGateway('Não foi possível interpretar a rota real de dados.', 503) from erro

    def _plano(self, lab):
        interfaces = {n: self._interface(lab, n) for n in (1, 2, 4)}
        if (interfaces[1].network != interfaces[2].network or interfaces[1].ip == interfaces[2].ip
                or interfaces[1].network.overlaps(interfaces[4].network)):
            raise ErroGateway('O cenário exige dois hosts locais distintos e um destino em outra LAN.', 503)
        return interfaces

    def _pings(self, lab, destinos=(2, 4)):
        interfaces = self._plano(lab)
        detalhes = []
        for node in destinos:
            destino = interfaces[node].ip
            codigo, saida = self._comando(lab, 1, f'ping -n -I eth0 -c 2 -W 1 {destino}')
            if codigo not in (0, 1, 2) or (codigo == 2 and 'Network is unreachable' not in saida):
                raise ErroGateway('O teste de rede não foi executado com confirmação.', 503)
            stats = re.search(r'(\d+) packets transmitted,\s*(\d+)(?: packets)? received.*?(\d+(?:\.\d+)?)% packet loss', saida)
            ok = bool(codigo == 0 and stats and int(stats[1]) == 2 and int(stats[2]) == 2 and float(stats[3]) == 0)
            if (not stats and not (codigo == 2 and 'Network is unreachable' in saida)) or (codigo == 0 and not ok):
                raise ErroGateway('Saída de ping ausente ou inconsistente; nenhuma evidência foi confirmada.', 503)
            detalhes.append({'origem': 1, 'destino': node, 'alcance': ok, 'codigo': codigo, 'comando': f'ping -n -I eth0 -c 2 -W 1 {destino}', 'saida': saida[-4000:]})
        return detalhes

    def _fingerprint(self, lab):
        return {n: str(i) for n, i in self._plano(lab).items()}

    def _exigir_plano_inicial(self, lab, s):
        atual = self._fingerprint(lab)
        if atual != self._estados[lab.usuario_id].get('baseline'):
            s['antes'] = cenario.dados_iniciais()['antes']
            self._invalidar(s)
            raise ErroGateway('Os endereços mudaram. Reinicie a comparação sem gateway.', 409)

    @staticmethod
    def _invalidar(s):
        inicial = cenario.dados_iniciais()
        for chave in ('conferencia', 'depois', 'interpretacao'):
            s[chave] = inicial[chave]

    def _candidato(self, lab, valor):
        if not isinstance(valor, str) or len(valor) > 15:
            raise ErroGateway('Informe um IPv4 canônico da LAN local.')
        try:
            ip = ipaddress.IPv4Address(valor)
        except ValueError as erro:
            raise ErroGateway('Informe um IPv4 canônico da LAN local.') from erro
        interface = self._interface(lab, 1)
        if str(ip) != valor or ip in CONTROLE or interface.network.overlaps(CONTROLE):
            raise ErroGateway('O gateway não pode usar a rede de controle.')
        if ip not in interface.network:
            raise ErroGateway('Escolha um próximo salto na LAN local, não na rede remota.')
        if ip in (interface.ip, interface.network.network_address, interface.network.broadcast_address):
            raise ErroGateway('Use um host da LAN diferente do próprio IP, rede e broadcast.')
        return str(ip)

    def _observar_rota(self, lab, s):
        gateway, saida = self._rota(lab)
        # Também revalida a LAN real, não apenas o valor exibido no formulário.
        valido = False
        if s['gateway']['valor']:
            try:
                self._candidato(lab, s['gateway']['valor'])
                valido = True
            except ErroGateway as erro:
                if erro.status == 503:
                    raise
        ok = bool(valido and s['gateway']['confirmado'] and gateway == s['gateway']['valor'])
        s['gateway']['observado'] = gateway
        s['conferencia'] = {'ok': ok, 'gateway': gateway, 'interface': 'eth0', 'saida': saida[-4000:]}
        return ok

    def _depois(self, lab, s):
        self._invalidar(s)
        self._exigir_plano_inicial(lab, s)
        ok = self._observar_rota(lab, s)
        detalhes = self._pings(lab)
        self._exigir_plano_inicial(lab, s)
        # Ler novamente após I/O evita validar uma rota que mudou durante os testes.
        ok = bool(self._observar_rota(lab, s) and ok)
        s['depois'] = {'registrado': True, 'local': detalhes[0]['alcance'],
            'remoto': detalhes[1]['alcance'], 'rota_confirmada': ok, 'detalhes': detalhes}

    def _encerrar(self, lab):
        self._mesma_sessao(lab)
        try:
            ok = self.engine.encerrar_confirmado(lab.usuario_id, lab.session_id, 'saindo da rede local: encerramento solicitado')
            if not ok or self.engine.obter(lab.usuario_id) is lab:
                raise RuntimeError('Remoção não confirmada')
        except Exception as erro:
            raise ErroGateway('A remoção do ambiente ainda não foi confirmada.', 503) from erro
        self._estados.pop(lab.usuario_id, None)

    def _finalizar(self, lab, xp=0):
        try:
            self._encerrar(lab)
            msg = 'Conclusão registrada e ambiente encerrado.'
        except ErroGateway:
            msg = 'Conclusão registrada; remoção do ambiente pendente. Tente encerrar novamente.'
        return {**self._status(lab.usuario_id, msg), 'xp_concedido': xp}

    def _perguntar_tutor(self, uid, login, dados):
        pergunta = dados.get('pergunta')
        if not isinstance(pergunta, str) or not 1 <= len(pergunta.strip()) <= 500:
            raise ErroGateway('Escreva uma dúvida de até 500 caracteres.')
        pergunta = pergunta.strip()
        rascunho = dados.get('rascunho', {})
        if (not isinstance(rascunho, dict) or set(rascunho) - {'comando', 'gateway'}
                or any(not isinstance(v, str) or len(v) > 80 for v in rascunho.values())):
            raise ErroGateway('Rascunho de ajuda inválido.')
        with self._serializar(uid):
            lab, s = self._contexto(uid, dados)
            if not getattr(lab, 'preparacao_confirmada', True):
                raise ErroGateway('O ambiente ainda não foi preparado.', 409)
            if uid in self._tutor_pendente:
                raise ErroGateway('O Link já está respondendo à sua pergunta. Aguarde.', 429)
            self._tutor_pendente.add(uid)
            contexto = self._status(uid)['missao']
            historico = deepcopy(self._estados[uid].get('conversas', []))
        try:
            # Não manter o lock de rede durante a busca/LLM: outros testes continuam disponíveis.
            resposta = self.tutor.responder(pergunta=pergunta, missao=contexto,
                historico=historico, rascunho=rascunho)
            with self._serializar(uid):
                atual, _ = self._contexto(uid, dados)
                if atual is not lab:
                    raise ErroGateway('A sessão mudou durante a resposta. Faça uma nova pergunta.', 409)
                mensagem = {**resposta, 'pergunta': pergunta,
                    'etapa': contexto.get('proxima_etapa') or 'comprovar'}
                conversas = self._estados[uid].setdefault('conversas', [])
                conversas.append(mensagem)
                del conversas[:-8]
                return {**self._status(uid), 'tutor': mensagem}
        finally:
            with self._lock:
                self._tutor_pendente.discard(uid)

    def executar_acao(self, uid, login, acao, dados):
        if type(uid) is not int or uid <= 0:
            raise ErroGateway('Sessão de usuário inválida.', 401)
        if not isinstance(dados, dict):
            raise ErroGateway('Corpo JSON inválido.')
        permitidos = {'status': set(), 'iniciar': set(),
            'tutor': {'session_id', 'revisao', 'pergunta', 'rascunho'},
            'prever': {'session_id', 'revisao', 'local', 'remota'},
            'testar-local': {'session_id', 'revisao', 'local'},
            'classificar': {'session_id', 'revisao', 'resposta'},
            'consultar': {'session_id', 'revisao'},
            'terminal': {'session_id', 'revisao', 'comando', 'local'},
            'testar-remoto': {'session_id', 'revisao'},
            'testar-antes': {'session_id', 'revisao'},
            'aplicar': {'session_id', 'revisao', 'gateway'},
            'conferir': {'session_id', 'revisao'},
            'testar-depois': {'session_id', 'revisao'},
            'interpretar': {'session_id', 'revisao', 'resposta'},
            'validar': {'session_id', 'revisao'},
            'encerrar': {'session_id', 'revisao'},
            'estender': {'session_id', 'revisao'}}
        if acao not in permitidos:
            raise ErroGateway('Operação inexistente.', 404)
        if set(dados) - permitidos[acao]:
            raise ErroGateway('A requisição contém campos não permitidos.')
        if acao == 'tutor':
            return self._perguntar_tutor(uid, login, dados)
        with self._serializar(uid):
            if acao == 'status':
                return self._status(uid)
            if acao == 'iniciar':
                lab = self.engine.obter(uid)
                if lab and lab.laboratorio_id != cenario.LABORATORIO_ID:
                    raise ErroGateway('Outro laboratório permanece ativo.', 409)
                if lab and not getattr(lab, 'preparacao_confirmada', True):
                    raise ErroGateway('Preparação incompleta. Consulte e encerre o ambiente antes de tentar novamente.', 503)
                if not lab:
                    lab = self.engine.criar(uid, login, cenario.LABORATORIO_ID)
                    self._dados(lab)
                return self._status(uid, 'Ambiente preparado. Comece testando a comunicação com o colega.')
            atual = self.engine.obter(uid)
            if atual and atual.laboratorio_id == cenario.LABORATORIO_ID and not getattr(atual, 'preparacao_confirmada', True) and acao != 'encerrar':
                raise ErroGateway('Preparação incompleta; somente encerramento é permitido.', 503)
            if acao in ('validar', 'encerrar') and atual is None:
                status = self._status(uid)
                if status['conclusao'] and type(dados.get('session_id')) is int and dados['session_id'] > 0 and type(dados.get('revisao')) is int and dados['revisao'] >= 0:
                    return {**status, 'xp_concedido': 0}
            final = self._finalizadas.get(uid)
            if atual and final and final['lab'] is atual:
                if acao not in ('validar', 'encerrar'):
                    raise ErroGateway('Conclusão já registrada; encerre antes de reiniciar o treino.', 409)
                if type(dados.get('session_id')) is not int or dados['session_id'] != atual.session_id or type(dados.get('revisao')) is not int or dados['revisao'] not in (final['revisao'], final['revisao_recebida']):
                    raise ErroGateway('A sessão ou revisão mudou.', 409)
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
                    raise ErroGateway('A extensão não foi confirmada.', 503) from erro
                self._mesma_sessao(lab)
                s['revisao'] += 1
                return self._status(uid, 'Tempo estendido.')
            if acao == 'terminal':
                # A entrada do aluno é interpretada; nunca é enviada a um shell.
                comando = dados.get('comando')
                if not isinstance(comando, str) or len(comando) > 80:
                    raise ErroGateway('Digite ping seguido do endereço do colega ou do servidor.')
                entrada = re.fullmatch(r'[ \t]*ping[ \t]+([0-9.]+)[ \t]*', comando)
                if entrada is None:
                    raise ErroGateway('Neste laboratório, use apenas ping e o endereço de destino, sem opções.')
                destinos = {cenario.NOS[n]['ip']: n for n in (2, 4)}
                destino = entrada[1]
                if destino not in destinos:
                    raise ErroGateway('Use o endereço do PC Colega ou do Servidor mostrado na topologia.')
                campos = {'session_id': dados['session_id'], 'revisao': dados['revisao']}
                if destinos[destino] == 2:
                    campos['local'] = dados.get('local')
                    acao_teste = 'testar-local'
                else:
                    acao_teste = 'testar-depois' if s['gateway']['confirmado'] else 'testar-remoto'
                observar = getattr(self.engine, 'observar', None)
                with observar(lab.usuario_id, 1) if observar else nullcontext() as captura:
                    retorno = self.executar_acao(uid, login, acao_teste, campos)
                if captura:
                    registrar_bastidores(s, 1, f'ping {destino}', captura)
                missao = retorno['missao']
                origem = missao['teste_local'] if destinos[destino] == 2 else (
                    missao['depois'] if acao_teste == 'testar-depois' else missao['antes'])
                detalhe = next(d for d in origem['detalhes'] if d['destino'] == destinos[destino])
                historico = s.setdefault('terminal', [])
                historico.append({
                    'digitado': f'ping {destino}', 'destino': destinos[destino],
                    'codigo': detalhe['codigo'], 'alcance': detalhe['alcance'],
                    'saida': detalhe['saida'], 'executado': detalhe['comando'],
                    'revisao': s['revisao'],
                })
                del historico[:-8]
                return self._status(uid, 'Comando executado no PC Atendimento. Observe o resultado.')
            if acao == 'consultar':
                interfaces = []
                for dev in ('eth0', 'eth1'):
                    i = self._interface(lab, 5, dev)
                    interfaces.append({'interface': dev, 'ip': str(i.ip), 'prefixo': i.network.prefixlen})
                self._estados[uid]['roteador'] = interfaces
                return self._status(uid, 'Interfaces consultadas no roteador; configuração e testes preservados.')
            if acao == 'testar-local':
                if dados.get('local') not in ('sim', 'nao'):
                    raise ErroGateway('Registre sua previsão para o colega antes do teste.')
                # An initial observation requires no default route. Later local tests do not rewrite it.
                inicial = not s['antes']['registrado']
                if inicial and self._rota(lab)[0] is not None:
                    raise ErroGateway('A observação inicial exige um computador sem gateway de dados.')
                fingerprint = self._fingerprint(lab)
                if not inicial:
                    self._exigir_plano_inicial(lab, s)
                s['revisao'] += 1
                s['teste_local'] = cenario.dados_iniciais()['teste_local']
                detalhes = self._pings(lab, (2,))
                if self._fingerprint(lab) != fingerprint or (inicial and self._rota(lab)[0] is not None):
                    raise ErroGateway('A rede mudou durante o teste local. Consulte o estado e tente novamente.', 409)
                s['teste_local'] = {'registrado': True, 'alcance': detalhes[0]['alcance'], 'detalhes': detalhes}
                s['previsao']['local'] = dados['local']
                if detalhes[0]['alcance'] is not True:
                    self._invalidar(s)
                if inicial and detalhes[0]['alcance'] is True:
                    self._estados[uid]['baseline'] = fingerprint
                    s['antes'] = {'registrado': True, 'local': True, 'remoto': None, 'detalhes': detalhes}
                return self._status(uid, 'Teste local executado. Sua previsão não altera pontos ou XP.')
            if acao == 'testar-remoto':
                if not s['antes']['registrado'] or s['antes']['local'] is not True:
                    raise ErroGateway('Comprove primeiro a comunicação com o colega.')
                if s['gateway']['confirmado'] or self._rota(lab)[0] is not None:
                    raise ErroGateway('Depois de aplicar o gateway, use o teste de comunicação final.')
                self._exigir_plano_inicial(lab, s)
                s['revisao'] += 1
                s['antes']['remoto'] = None
                s['antes']['detalhes'] = [d for d in s['antes']['detalhes'] if d['destino'] != 4]
                detalhes = self._pings(lab, (4,))
                self._exigir_plano_inicial(lab, s)
                if self._rota(lab)[0] is not None:
                    raise ErroGateway('A configuração mudou durante o teste. Atualize o estado.', 409)
                s['antes']['remoto'] = detalhes[0]['alcance']
                s['antes']['detalhes'].extend(detalhes)
                return self._status(uid, 'Experimento opcional concluído: observe o resultado sem gateway.')
            if acao == 'classificar':
                if not s['antes']['registrado'] or s['antes']['local'] is not True:
                    raise ErroGateway('Comprove primeiro a comunicação com o colega.')
                if dados.get('resposta') not in ('mesma-rede', 'outra-rede'):
                    raise ErroGateway('Escolha se o servidor pertence à mesma rede ou a outra.')
                s['revisao'] += 1
                s['classificacao'] = {'resposta': dados['resposta'], 'correta': dados['resposta'] == 'outra-rede'}
                return self._status(uid, 'Com esta máscara /24, compare os três primeiros números dos endereços.')
            if acao == 'interpretar':
                d = s['depois']
                if not (d['registrado'] and d['rota_confirmada'] and d['local'] is True and d['remoto'] is True):
                    raise ErroGateway('Observe primeiro os testes e a rota depois da configuração.')
                resposta = dados.get('resposta')
                if resposta not in ('gateway-remoto', 'gateway-sempre', 'switch-roteia'):
                    raise ErroGateway('Selecione uma interpretação válida.')
                s['revisao'] += 1
                correta = resposta == 'gateway-remoto'
                s['interpretacao'] = {'resposta': resposta, 'correta': correta,
                    'feedback': 'O destino local usa a LAN; o remoto precisa de um roteador e caminho de retorno.' if correta else 'Compare o caminho para cada destino e tente novamente.'}
                return self._status(uid)
            if acao == 'validar':
                if not cenario.estado_publico(s, True)['concluido']:
                    raise ErroGateway('Complete as observações e a interpretação antes de concluir.')
                interpretacao = s['interpretacao'].copy()
                s['revisao'] += 1
                self._depois(lab, s)
                d = s['depois']
                if not (d['registrado'] and d['rota_confirmada'] and d['local'] is True and d['remoto'] is True):
                    raise ErroGateway('A rede mudou; confira novamente antes de concluir.')
                s['interpretacao'] = interpretacao
                self._mesma_sessao(lab)
                try:
                    progresso = self.concluir(uid, cenario.LABORATORIO_ID)
                    if (not isinstance(progresso, dict) or type(progresso.get('xp_concedido')) is not int
                            or progresso['xp_concedido'] < 0):
                        raise ValueError('Confirmação de progresso inválida')
                    self._finalizadas[uid] = {'lab': lab, 'concluido': True, 'concluido_em': int(time.time()),
                        'revisao': s['revisao'], 'revisao_recebida': dados['revisao']}
                except Exception as erro:
                    raise ErroGateway('A conclusão não foi confirmada; tente registrar novamente.', 503) from erro
                return self._finalizar(lab, progresso.get('xp_concedido', 0))
            if acao in ('aplicar', 'conferir', 'testar-depois'):
                a = s['antes']
                if not a['registrado'] or a['local'] is not True:
                    raise ErroGateway('Observe primeiro a comparação inicial sem gateway.')
                if acao == 'aplicar':
                    if not s.get('classificacao', {}).get('correta'):
                        raise ErroGateway('Identifique primeiro se o servidor está em outra rede.')
                    self._exigir_plano_inicial(lab, s)
                    gateway = self._candidato(lab, dados.get('gateway'))
                    s['revisao'] += 1
                    self._invalidar(s)
                    s['gateway'] = {'valor': gateway, 'confirmado': False, 'observado': None}
                    codigo, _ = self._comando(lab, 1, f'ip -4 route replace default via {gateway} dev eth0')
                    if codigo != 0:
                        raise ErroGateway('O nó não confirmou a aplicação do gateway.', 503)
                    s['gateway']['confirmado'] = True
                    if not self._observar_rota(lab, s):
                        raise ErroGateway('O gateway aplicado ainda não foi confirmado na configuração real.', 503)
                elif acao == 'conferir':
                    s['revisao'] += 1
                    self._invalidar(s)
                    self._estados[uid]['roteador'] = []
                    interfaces = []
                    for dev in ('eth0', 'eth1'):
                        i = self._interface(lab, 5, dev)
                        interfaces.append({'interface': dev, 'ip': str(i.ip), 'prefixo': i.network.prefixlen})
                    self._estados[uid]['roteador'] = interfaces
                    self._exigir_plano_inicial(lab, s)
                    self._observar_rota(lab, s)
                else:
                    s['revisao'] += 1
                    self._depois(lab, s)
                return self._status(uid, 'Observe a configuração e os testes; aplicar não conclui a missão.')
            if acao == 'prever':
                if dados.get('local') not in ('sim', 'nao') or dados.get('remota') not in ('sim', 'nao'):
                    raise ErroGateway('Registre uma previsão para cada destino.')
                s['revisao'] += 1
                s['previsao'] = {'local': dados['local'], 'remota': dados['remota'], 'registrada': True}
            if acao == 'testar-antes':
                if not s['previsao']['registrada']:
                    raise ErroGateway('Registre a previsão antes de observar a comunicação.')
                gateway, _ = self._rota(lab)
                if gateway is not None:
                    raise ErroGateway('A comparação inicial exige ausência de gateway de dados.')
                s['revisao'] += 1
                s['antes'] = cenario.dados_iniciais()['antes']
                self._invalidar(s)
                fingerprint = self._fingerprint(lab)
                detalhes = self._pings(lab)
                if self._rota(lab)[0] is not None or self._fingerprint(lab) != fingerprint:
                    raise ErroGateway('O cenário mudou durante a comparação inicial; teste novamente.', 409)
                self._estados[uid]['baseline'] = fingerprint
                s['antes'] = {'registrado': True, 'local': detalhes[0]['alcance'],
                    'remoto': detalhes[1]['alcance'], 'detalhes': detalhes}
            return self._status(uid)
