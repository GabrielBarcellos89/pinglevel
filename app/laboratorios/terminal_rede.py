"""Labs 5 a 10 — setores ligados a um roteador (ou a um switch com VLANs), configurados pelo terminal: somente I/O do
engine injetado.

O cenário (cenarios/dividindo_rede.py ou planejando_empresa.py) define equipamentos, plano, etapas e o que pode ser
alterado em cada etapa. Este serviço lê a configuração real de cada equipamento depois de cada comando, confere o
plano e as etapas no servidor e só registra a conclusão depois de reler tudo e repetir os testes.
"""
from contextlib import contextmanager, nullcontext
import ipaddress
import json
import threading
import time
from copy import deepcopy

from laboratorios.cenarios import rede_setores as base
from laboratorios.captura import registrar_bastidores
from laboratorios.terminal_comandos import (ErroComando, filtrar_bridge, filtrar_fdb, filtrar_rotas, interpretar,
    interpretar_remoto)
from laboratorios.terminal_guiado import ErroTerminal, alcance_ping
from laboratorios.tutor_referencias import TutorReferencias

LER_ENDERECOS = 'ip -j addr show'
LER_ROTAS = 'ip -j -4 route show'
LER_VLANS = 'bridge -j vlan show'
LER_DNS = 'cat /etc/resolv.conf'
CAMPOS = ('interfaces', 'rota_padrao', 'rotas', 'vlans', 'dns')
HISTORICO = 40
# Comandos que geram tráfego: o servidor captura com o tshark e o aluno vê nos Bastidores.
OBSERVADOS = ('ping', 'consultar-dns', 'pedir-dhcp')
TAMANHO_RESPOSTA = 20


def descrever_vlan(v):
    if v['membro'] == [v['pvid']] and v['untagged'] == [v['pvid']]:
        return f"VLAN {v['pvid']}"
    if not v['membro']:
        return 'sem VLAN'
    return f"VLANs {', '.join(map(str, v['membro']))} (PVID {v['pvid'] or 'nenhuma'})"


class ServicoRede:
    def __init__(self, gerenciador, concluir_laboratorio, consultar_progresso=None, *, cenario, perfil_tutor, tutor=None):
        self.engine = gerenciador
        self.concluir = concluir_laboratorio
        self.consultar_progresso = consultar_progresso
        self.cenario = cenario
        self.tutor = tutor or TutorReferencias(perfil=perfil_tutor)
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

    def _meu(self, lab):
        return bool(lab and lab.laboratorio_id == self.cenario.LABORATORIO_ID)

    def _dados(self, lab):
        registro = self._estados.get(lab.usuario_id)
        if registro is None or registro['lab'] is not lab:
            registro = {'lab': lab, 'dados': self.cenario.dados_iniciais()}
            self._estados[lab.usuario_id] = registro
        return registro['dados']

    def _status(self, uid, mensagem=''):
        lab = self.engine.obter(uid)
        ativo = self._meu(lab)
        conflito = None if not lab or ativo else {'laboratorio_id': lab.laboratorio_id,
            'titulo': 'Outro laboratório está ativo. Encerre-o na própria página.'}
        registro = self._finalizadas.get(uid)
        if ativo:
            registro = registro if registro and registro['lab'] is lab else None
        elif self.consultar_progresso:
            try:
                resumo = self.consultar_progresso(uid)
                registro = next((r for r in resumo['laboratorios']
                    if r.get('laboratorio_id') == self.cenario.LABORATORIO_ID and r.get('concluido') is True), None)
            except Exception as erro:
                raise ErroTerminal('Não foi possível confirmar o progresso salvo.', 503) from erro
        missao = self.cenario.estado_publico(self._dados(lab) if ativo else None, ativo)
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
        if atual is not lab or not self._meu(atual):
            raise ErroTerminal('A sessão expirou ou mudou. Consulte o estado atual.', 409)

    def _contexto(self, uid, dados):
        lab = self.engine.obter(uid)
        if not self._meu(lab):
            raise ErroTerminal('Inicie este laboratório; nenhuma outra sessão será alterada.', 409)
        s = self._dados(lab)
        if type(dados.get('session_id')) is not int or dados['session_id'] != lab.session_id:
            raise ErroTerminal('A sessão mudou. Consulte o estado atual.', 409)
        if type(dados.get('revisao')) is not int or dados['revisao'] != s['revisao']:
            raise ErroTerminal('A revisão mudou. Consulte o estado atual.', 409)
        return lab, s

    def _comando(self, lab, no, cmd):
        nome = self.cenario.NOS[no]['nome']
        with self.engine.trava(lab.usuario_id):
            self._mesma_sessao(lab)
            try:
                resultado = self.engine.executar(lab.usuario_id, self.cenario.NOS[no]['no'], cmd, timeout=8)
            except Exception as erro:
                raise ErroTerminal(f'Não foi possível executar o comando no {nome}.', 503) from erro
            self._mesma_sessao(lab)
            if (not isinstance(resultado, (tuple, list)) or len(resultado) != 2
                    or type(resultado[0]) is not int or not isinstance(resultado[1], str)):
                raise ErroTerminal(f'Resposta inválida do {nome}.', 503)
            return resultado[0], resultado[1]

    def _ler_estado(self, lab, no):
        """Endereços IPv4 das interfaces do laboratório e rota padrão, lidos do equipamento real."""
        permitidas = self.cenario.NOS[no]['interfaces']
        try:
            codigo, saida = self._comando(lab, no, LER_ENDERECOS)
            lista = json.loads(saida) if codigo == 0 else None
            if not isinstance(lista, list):
                raise ValueError()
            por_nome = {i.get('ifname', '').split('@')[0]: i for i in lista if isinstance(i, dict)}
            if any(nome not in por_nome for nome in permitidas):
                raise ValueError()
            interfaces = {nome: [str(ipaddress.IPv4Interface(f"{a['local']}/{a['prefixlen']}"))
                                 for a in por_nome[nome].get('addr_info', []) if a.get('family') == 'inet']
                          for nome in permitidas}
            ativa = all('UP' in por_nome[nome].get('flags', []) for nome in permitidas)
            codigo, saida = self._comando(lab, no, LER_ROTAS)
            tabela = json.loads(saida) if codigo == 0 else None
            if not isinstance(tabela, list):
                raise ValueError()
            tabela = [r for r in tabela if isinstance(r, dict) and r.get('dev') in permitidas]
            padrao = [r for r in tabela if r.get('dst') == 'default']
            rota = str(ipaddress.IPv4Address(padrao[0]['gateway'])) if len(padrao) == 1 and 'gateway' in padrao[0] else None
            # Rotas estáticas para redes (as conectadas, sem gateway, vêm das próprias interfaces).
            estaticas = sorted(f"{ipaddress.IPv4Network(r['dst'])} via {ipaddress.IPv4Address(r['gateway'])}"
                               for r in tabela if r.get('dst') != 'default' and 'gateway' in r)
            vlans = self._ler_vlans(lab, no, permitidas) if self.cenario.NOS[no]['tipo'] == 'switch' else {}
            dns = self._ler_dns(lab, no) if no in getattr(self.cenario, 'LER_DNS', ()) else []
        except (ValueError, TypeError, KeyError) as erro:
            raise ErroTerminal(f"Não foi possível ler a configuração real do {self.cenario.NOS[no]['nome']}.", 503) from erro
        return {'interfaces': interfaces, 'rota_padrao': rota, 'rotas': estaticas, 'vlans': vlans, 'dns': dns, 'lido': True,
                'ativa': ativa}

    def _ler_dns(self, lab, no):
        """Servidores DNS (linhas nameserver) do /etc/resolv.conf do equipamento (Labs 8 e 10)."""
        codigo, saida = self._comando(lab, no, LER_DNS)
        if codigo != 0:
            raise ValueError()
        return [str(ipaddress.IPv4Address(partes[1])) for partes in (linha.split() for linha in saida.splitlines())
                if len(partes) >= 2 and partes[0] == 'nameserver']

    def _ler_vlans(self, lab, no, portas):
        """VLANs de cada porta do switch: membro, PVID e as que saem sem marcação (untagged)."""
        codigo, saida = self._comando(lab, no, LER_VLANS)
        lista = json.loads(saida) if codigo == 0 else None
        if not isinstance(lista, list):
            raise ValueError()
        por_porta = {p.get('ifname'): p.get('vlans', []) for p in lista if isinstance(p, dict)}
        vlans = {}
        for porta in portas:
            itens = [v for v in por_porta.get(porta, []) if isinstance(v, dict) and type(v.get('vlan')) is int]
            pvid = [v['vlan'] for v in itens if 'PVID' in v.get('flags', [])]
            vlans[porta] = {'pvid': pvid[0] if len(pvid) == 1 else None, 'membro': sorted(v['vlan'] for v in itens),
                            'untagged': sorted(v['vlan'] for v in itens if 'Egress Untagged' in v.get('flags', []))}
        return vlans

    def _atualizar_estado(self, lab, s, no):
        novo = self._ler_estado(lab, no)
        anterior = s['estados'][no]
        if any(novo[k] != anterior.get(k, {} if k == 'vlans' else []) for k in CAMPOS):
            # Testes feitos com outra configuração deixam de valer; mudar um roteador muda o caminho de todos.
            invalidar = getattr(self.cenario, 'invalidar_testes', None)
            if invalidar:
                invalidar(s, no, anterior, novo)
            else:
                for afetado in (s['testes'] if self.cenario.NOS[no]['tipo'] == 'roteador' else [no]):
                    s['testes'][afetado] = {}
        s['estados'][no] = {k: novo[k] for k in (*CAMPOS, 'lido')}
        return novo

    def _via(self, lab, s, no, cmd):
        """Executa no nó. Numa sessão SSH aberta (demonstração "Suporte remoto"), o comando segue pelo SSH real a
        partir do terminal de origem; os comandos montados pelo servidor nunca têm aspas simples."""
        if s is not None and s.get('remoto') == no:
            return self._comando(lab, self.cenario.ORIGEM, f"ssh {self.cenario.NOS[no]['ip']} '{cmd}'")
        return self._comando(lab, no, cmd)

    def _ping(self, lab, no, destino, s=None):
        codigo, saida = self._via(lab, s, no, f'ping -n -c 2 -W 1 {destino}')
        if codigo not in (0, 1, 2):
            raise ErroTerminal('O teste de rede não foi executado com confirmação.', 503)
        return codigo, saida, alcance_ping(codigo, saida)

    def _confirmacao(self, no, estado):
        if self.cenario.NOS[no]['tipo'] == 'switch':
            return ' · '.join(f"{p}: {descrever_vlan(v)}" for p, v in estado['vlans'].items())
        partes = [f"{nome}: {', '.join(lista) or 'sem endereço IPv4'}" for nome, lista in estado['interfaces'].items()]
        if self.cenario.NOS[no]['tipo'] == 'pc' or self.cenario.NOS[no].get('rotas') is True:
            partes.append(f"rota padrão: {'via ' + estado['rota_padrao'] if estado['rota_padrao'] else 'nenhuma'}")
        elif self.cenario.NOS[no].get('rotas'):
            partes.append(f"rotas estáticas: {'; '.join(estado['rotas']) or 'nenhuma'}")
        return ' · '.join(partes)

    def _pode_alterar(self, s, no, interface):
        etapa = base.etapa_atual(self.cenario, s)
        permitidos = self.cenario.ALTERAVEIS.get(etapa, {})
        nome = self.cenario.NOS[no]['nome']
        if etapa == 'plano':
            raise ErroTerminal('Primeiro complete o plano: os endereços vêm dele.')
        if etapa in (None, 'comprovar'):
            raise ErroTerminal('Tudo configurado. Conclua a missão para o servidor conferir.')
        if etapa in base.chamados(self.cenario) and not s['diagnosticos'][etapa]['correta']:
            raise ErroTerminal(f'Antes de alterar o {nome}, responda no chamado: qual é a causa do problema?')
        if not permitidos:
            raise ErroTerminal('Nesta etapa não há nada para alterar: observe pelo terminal e responda no painel.')
        if no not in permitidos:
            alvos = ', '.join(self.cenario.NOS[n]['nome'] for n in permitidos)
            raise ErroTerminal(f'Nesta etapa só se altera: {alvos}. Você pode observar o {nome} à vontade.')
        if interface not in permitidos[no]:
            if permitidos[no] == ('rotas',):
                raise ErroTerminal(f'Nesta etapa, no {nome}, só se alteram as rotas estáticas.')
            raise ErroTerminal(f"Nesta etapa, no {nome}, só se altera: {', '.join(permitidos[no])}.")

    def _terminal_remoto(self, lab, s, aba, texto):
        """Demonstração "Suporte remoto": um só terminal (a T.I.), com ssh usuário@ip e senha, exit e a página web da
        impressora (curl). A senha é conferida pelo servidor; a conexão SSH em si é real, por chave, entre os nós."""
        c = self.cenario
        if aba not in c.TERMINAIS:
            raise ErroTerminal(f"Neste teste tudo é feito a partir do PC da {c.NOS[c.ORIGEM]['nome']}.")
        if s.get('senha_pendente'):
            return self._senha_ssh(s, aba, texto)
        try:
            especial = interpretar_remoto(texto)
        except ErroComando as erro:
            raise ErroTerminal(str(erro)) from erro
        atual = s.get('remoto') or aba
        if especial is None:
            return self._terminal(lab, s, atual, texto, aba=aba)
        s['revisao'] += 1
        tipo, codigo, saida = especial[0], 0, ''
        if tipo == 'exit':
            if not s.get('remoto'):
                raise ErroTerminal(f"Você já está na {c.NOS[aba]['nome']}: não há conexão SSH aberta.")
            saida = f"logout\nConnection to {c.NOS[s['remoto']]['ip']} closed. Você voltou ao terminal da {c.NOS[aba]['nome'].rstrip('.')}."
            s['remoto'] = None
        elif tipo == 'ssh':
            ip, usuario = especial[1], especial[2]
            if s.get('remoto'):
                raise ErroTerminal(f"Você já está no {c.NOS[s['remoto']]['nome']}. Digite exit antes de abrir outra conexão.")
            destino = c.no_do_ip(ip)
            if destino is None or c.NOS[destino]['tipo'] != 'pc':
                raise ErroTerminal('Esse endereço não é de um computador deste laboratório.')
            if destino == aba:
                raise ErroTerminal(f"{ip} é a própria {c.NOS[aba]['nome']}.")
            # Como no ssh de verdade: primeiro a conexão (real, pela rede do aluno); só depois a senha.
            codigo, saida = self._comando(lab, aba, f'ssh {ip} hostname 2>&1')
            if codigo == 0:
                s['senha_pendente'] = {'destino': destino, 'usuario': usuario, 'tentativas': 0}
                saida = f"{usuario}@{ip}'s password:"
        else:
            ip = especial[-1]
            if ip != c.IMPRESSORA:
                raise ErroTerminal('Esse endereço não é da impressora. Confira na topologia.')
            if tipo == 'pagina':
                codigo, saida = self._via(lab, s, atual, f'curl -sS -m 3 http://{ip}/ 2>&1')
                if codigo != 0:
                    saida = (saida.strip() + '\n' if saida.strip() else '') + \
                        f"A página da impressora não abriu: o {c.NOS[atual]['nome']} não alcançou {ip}."
            else:
                codigo, saida = self._imprimir(lab, s, atual, especial[1], ip)
        s['terminal'].append({'pc': aba, 'remoto': atual if atual != aba else None, 'digitado': ' '.join(texto.split()),
            'saida': saida[-4000:], 'codigo': codigo, 'alcance': None, 'tipo': tipo, 'revisao': s['revisao'], 'confirmacao': ''})
        del s['terminal'][:-HISTORICO]

    def _senha_ssh(self, s, aba, texto):
        """A linha digitada é a senha do ssh pedido antes; nunca entra no histórico."""
        c, pendente = self.cenario, s['senha_pendente']
        destino, usuario = pendente['destino'], pendente['usuario']
        s['revisao'] += 1
        if usuario == c.USUARIO_SSH and texto == c.SENHA_SSH:
            s['senha_pendente'] = None
            s['remoto'] = destino
            if destino not in s['acessos']:
                s['acessos'].append(destino)
            codigo, saida = 0, (f"Welcome to {c.NOS[destino]['host']}\nConectado ao {c.NOS[destino]['nome']} por SSH. "
                                f"Os próximos comandos rodam nele. Para voltar, digite exit.")
        else:
            pendente['tentativas'] += 1
            codigo = 255
            if pendente['tentativas'] >= 3:
                s['senha_pendente'] = None
                saida = f"{usuario}@{c.NOS[destino]['ip']}: Permission denied (publickey,password)."
            else:
                saida = f"Permission denied, please try again.\n{usuario}@{c.NOS[destino]['ip']}'s password:"
        s['terminal'].append({'pc': aba, 'remoto': None, 'digitado': '', 'senha': True, 'saida': saida, 'codigo': codigo,
            'alcance': None, 'tipo': 'senha', 'revisao': s['revisao'], 'confirmacao': ''})
        del s['terminal'][:-HISTORICO]

    def _imprimir(self, lab, s, atual, texto_folha, ip):
        c = self.cenario
        impressora = c.no_do_ip(c.IMPRESSORA)
        contar = 'ls /tmp/folhas 2>/dev/null | wc -l'
        antes = self._comando(lab, impressora, contar)[1].strip()
        codigo, saida = self._via(lab, s, atual, f'curl -sS -m 3 -d "texto={texto_folha}" http://{ip}/imprimir 2>&1')
        depois = self._comando(lab, impressora, contar)[1].strip()
        if depois.isdigit() and antes.isdigit() and int(depois) > int(antes):
            s['folhas'].append({'texto': texto_folha, 'origem': atual, 'hora': int(time.time()), 'aluno': lab.login})
            del s['folhas'][:-10]
            if atual != c.ALVO:
                saida = saida.rstrip() + f"\nEla saiu da {c.NOS[atual]['nome']}; o chamado pede imprimir a partir do {c.NOS[c.ALVO]['nome']}."
            return 0, saida
        return codigo or 1, (saida.strip() + '\n' if saida.strip() else '') + \
            f"A impressora não recebeu a folha: o {c.NOS[atual]['nome']} não alcançou {ip}."

    def painel(self):
        """Resumo de cada aluno com este laboratório ativo, para o painel do professor (sem dados pessoais além do login)."""
        with self._lock:
            registros = list(self._estados.values())
        alunos = []
        for r in registros:
            lab, s = r['lab'], r['dados']
            if self.engine.obter(lab.usuario_id) is not lab:
                continue
            alunos.append({'login': lab.login, 'etapa': base.etapa_atual(self.cenario, s), 'folhas': deepcopy(s.get('folhas', [])),
                           'iniciado_em': int(lab.iniciado_em), 'tempo_criacao': getattr(lab, 'tempo_criacao', None)})
        return alunos

    def _terminal(self, lab, s, no, texto, aba=None):
        if no not in self.cenario.NOS:
            raise ErroTerminal('Escolha um dos equipamentos do laboratório.')
        info = self.cenario.NOS[no]
        try:
            comando = interpretar(texto, base.em_uso(s['estados'], no), info['interfaces'],
                                  rotas=True if info['tipo'] == 'pc' else info.get('rotas', False), tipo=info['tipo'],
                                  servicos=getattr(self.cenario, 'DOMINIO', None) if info['tipo'] in ('pc', 'servidor') else None)
        except ErroComando as erro:
            raise ErroTerminal(str(erro)) from erro
        if comando.altera:
            self._pode_alterar(s, no, comando.interface)
        s['revisao'] += 1
        observar = getattr(self.engine, 'observar', None)
        with (observar(lab.usuario_id, info['no']) if observar and comando.tipo in OBSERVADOS else nullcontext()) as captura:
            if comando.tipo == 'ping':
                codigo, saida, alcance = self._ping(lab, no, comando.alvo, s)
            else:
                codigo, saida = self._via(lab, s, no, comando.executar)
                alcance = None
        if captura:
            registrar_bastidores(s, no, texto, captura)
        if comando.tipo == 'ver-rotas' and codigo == 0:
            saida = filtrar_rotas(saida, info['interfaces'])
        elif comando.tipo in ('ver-vlans', 'ver-portas') and codigo == 0:
            saida = filtrar_bridge(saida, info['interfaces'])
        elif comando.tipo == 'ver-fdb' and codigo == 0:
            macs = getattr(self.cenario, 'MACS', None)
            saida = filtrar_fdb(saida, info['interfaces'], set(macs.values()) if macs else None)
        estado = self._atualizar_estado(lab, s, no)
        if comando.tipo == 'ping':
            s['testes'][no][comando.alvo] = alcance
        if codigo in (0, 1):
            base.marcar_suspeitas(self.cenario, s, no, comando.tipo, getattr(comando, 'alvo', None))
        s['terminal'].append({'pc': aba or no, **({'remoto': no} if aba and aba != no else {}),
            'digitado': ' '.join(texto.split()), 'saida': saida[-4000:], 'codigo': codigo,
            'alcance': alcance, 'tipo': comando.tipo, 'revisao': s['revisao'],
            'confirmacao': self._confirmacao(no, estado) if comando.altera and codigo == 0 and not saida.strip() else ''})
        del s['terminal'][:-HISTORICO]

    def _planejar(self, s, respostas):
        campos = {c['id'] for c in self.cenario.PLANO}
        if (not isinstance(respostas, dict) or set(respostas) != campos
                or any(not isinstance(v, str) or len(v) > TAMANHO_RESPOSTA for v in respostas.values())):
            raise ErroTerminal('Preencha todos os campos do plano.')
        if s['plano']['correto']:
            raise ErroTerminal('O plano já foi conferido.')
        if getattr(self.cenario, 'PLANO_DEPOIS_DO_CHAMADO', False) and base.etapa_atual(self.cenario, s) in base.chamados(self.cenario):
            raise ErroTerminal('O plano abre depois do diagnóstico. Primeiro responda a causa no chamado.')
        for no, tipo, pedido in getattr(self.cenario, 'OBSERVAR_PLANO', ()):
            if not any(t['pc'] == no and t['tipo'] == tipo for t in s['terminal']):
                raise ErroTerminal(pedido)
        s['revisao'] += 1
        erros = base.conferir_plano(self.cenario.PLANO, respostas)
        s['plano'] = {'respostas': {k: v.strip() for k, v in respostas.items()}, 'erros': erros, 'correto': not erros}
        if not erros:
            return 'Plano conferido. Agora configure os equipamentos.'
        dica = getattr(self.cenario, 'dica_plano', None)
        return f"{len(erros)} campo(s) não conferem. Revise os destacados e confira de novo." + \
            (f" {dica(respostas, erros)}" if dica else '')

    def _diagnosticar(self, s, resposta):
        etapa = base.etapa_atual(self.cenario, s)
        chamado = base.chamados(self.cenario).get(etapa)
        if not chamado:
            raise ErroTerminal('Não há chamado aberto agora.')
        diagnostico = s['diagnosticos'][etapa]
        if diagnostico['correta']:
            raise ErroTerminal(chamado.get('ja_identificada', 'A causa já foi identificada. Corrija o equipamento e comprove com ping.'))
        observar_no = chamado.get('observar_no', chamado['no'])
        faltam = base.suspeitas_faltando(chamado, diagnostico)
        if faltam:
            raise ErroTerminal('Antes de responder, teste as suspeitas que faltam: '
                               + '; '.join(f"{x['texto']} ({x['onde']}: {x['comando']})" for x in faltam))
        if not chamado.get('suspeitas') and not any(t['tipo'] == chamado['observar'] and t['pc'] == observar_no for t in s['terminal']):
            raise ErroTerminal(chamado['pedido_observar'])
        if resposta not in chamado['causas']:
            raise ErroTerminal('Escolha uma das causas apresentadas.')
        s['revisao'] += 1
        correta = resposta == chamado['correta']
        diagnostico.update(resposta=resposta, correta=correta)
        return chamado['acerto'] if correta else chamado.get('erros', {}).get(resposta, chamado['erro'])

    def _encerrar(self, lab):
        self._mesma_sessao(lab)
        try:
            ok = self.engine.encerrar_confirmado(lab.usuario_id, lab.session_id, f'{self.cenario.TITULO}: encerramento solicitado')
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
        if base.etapa_atual(self.cenario, s) != 'comprovar':
            raise ErroTerminal('Conclua todas as etapas, com os testes de ping, antes de concluir.')
        s['revisao'] += 1
        estados = {no: self._atualizar_estado(lab, s, no) for no in self.cenario.NOS}
        mudou = self.cenario.problemas(s)
        if mudou:
            raise ErroTerminal(f"A configuração mudou em: {', '.join(mudou)}. Confira antes de concluir.")
        testes = self.cenario.testes_finais(s)
        isolados = getattr(self.cenario, 'testes_isolados', lambda _: [])(s)
        for origem, destino in (*testes, *isolados):
            s['testes'][origem][destino] = self._ping(lab, origem, destino)[2]
        relidos = {no: self._ler_estado(lab, no) for no in self.cenario.NOS}
        if (any(relidos[no][k] != estados[no][k] for no in self.cenario.NOS for k in CAMPOS)
                or not all(s['testes'][o].get(d) is True for o, d in testes)
                or not all(s['testes'][o].get(d) is False for o, d in isolados)):
            raise ErroTerminal('A comunicação não foi confirmada agora; teste novamente antes de concluir.')
        self._mesma_sessao(lab)
        try:
            progresso = self.concluir(uid, self.cenario.LABORATORIO_ID)
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

    def _iniciar(self, uid, login):
        lab = self.engine.obter(uid)
        if lab and not self._meu(lab):
            raise ErroTerminal('Outro laboratório permanece ativo.', 409)
        if lab and not getattr(lab, 'preparacao_confirmada', True):
            raise ErroTerminal('Preparação incompleta. Consulte e encerre o ambiente antes de tentar novamente.', 503)
        if not lab:
            lab = self.engine.criar(uid, login, self.cenario.LABORATORIO_ID)
            s = self._dados(lab)
            for no, esperado in self.cenario.INICIAL.items():
                estado = self._ler_estado(lab, no)
                if not estado['ativa'] or {k: estado[k] for k in esperado} != esperado:
                    raise ErroTerminal(f"O {self.cenario.NOS[no]['nome']} não foi preparado como previsto. Encerre e inicie novamente.", 503)
                s['estados'][no] = {k: estado[k] for k in (*CAMPOS, 'lido')}
        return self._status(uid, 'Ambiente preparado. Comece pelo plano.')

    def executar_acao(self, uid, login, acao, dados):
        if type(uid) is not int or uid <= 0:
            raise ErroTerminal('Sessão de usuário inválida.', 401)
        if not isinstance(dados, dict):
            raise ErroTerminal('Corpo JSON inválido.')
        base_campos = {'session_id', 'revisao'}
        permitidos = {'status': set(), 'iniciar': set(), 'terminal': base_campos | {'comando', 'pc'},
            'planejar': base_campos | {'respostas'}, 'diagnosticar': base_campos | {'resposta'},
            'tutor': base_campos | {'pergunta', 'rascunho'}, 'validar': base_campos, 'encerrar': base_campos,
            'estender': base_campos}
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
                return self._iniciar(uid, login)
            atual = self.engine.obter(uid)
            if self._meu(atual) and not getattr(atual, 'preparacao_confirmada', True) and acao != 'encerrar':
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
                senha = bool(s.get('senha_pendente'))
                try:
                    if getattr(self.cenario, 'TERMINAIS', None):
                        self._terminal_remoto(lab, s, dados.get('pc'), dados.get('comando'))
                    else:
                        self._terminal(lab, s, dados.get('pc'), dados.get('comando'))
                except ErroTerminal as erro:
                    # O Link vê os últimos comandos recusados e o motivo, para explicar o erro de formato.
                    # Uma senha digitada nunca é guardada.
                    if not senha and erro.status == 400 and isinstance(dados.get('comando'), str):
                        s.setdefault('recusas', []).append({'digitado': ' '.join(dados['comando'].split())[:100],
                                                            'motivo': str(erro)[:300], 'revisao': s['revisao']})
                        del s['recusas'][:-3]
                    raise
                return self._status(uid)
            if acao == 'planejar':
                return self._status(uid, self._planejar(s, dados.get('respostas')))
            if acao == 'diagnosticar':
                return self._status(uid, self._diagnosticar(s, dados.get('resposta')))
            return self._validar(uid, lab, s, dados)
