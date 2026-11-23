"""Regras comuns dos Labs 5 e 6: setores (sub-redes) ligados a um roteador, um plano conferido no servidor e a
configuração lida dos equipamentos reais. Os cenários definem nós, setores, plano e etapas; aqui ficam as conferências."""
import ipaddress
import random
from copy import deepcopy


def interface_de(endereco):
    return ipaddress.IPv4Interface(endereco)


def bloco(setor):
    return ipaddress.IPv4Network(f"{setor['rede']}/{setor['prefixo']}")


def todos_enderecos(estados, exceto=None):
    """Endereços (sem prefixo) configurados nos nós, exceto o nó indicado."""
    usados = set()
    for no, estado in estados.items():
        if no == exceto:
            continue
        for lista in estado['interfaces'].values():
            usados.update(str(interface_de(e).ip) for e in lista)
    return usados


def em_uso(estados, no):
    return tuple(sorted(todos_enderecos(estados, exceto=no)))


def pc_ok(estados, no, setor):
    """Um só endereço, host do bloco do setor (não a rede, o broadcast nem o gateway), único e rota pelo gateway."""
    estado = estados[no]
    enderecos = estado['interfaces'].get('eth0', [])
    if len(enderecos) != 1 or estado['rota_padrao'] != setor['gateway']:
        return False
    interface = interface_de(enderecos[0])
    rede = bloco(setor)
    return (interface.network == rede and interface.ip not in (rede.network_address, rede.broadcast_address)
            and str(interface.ip) != setor['gateway'] and str(interface.ip) not in todos_enderecos(estados, exceto=no))


def roteador_ok(estados, no, setores):
    """Cada interface do roteador com exatamente o gateway do seu setor."""
    interfaces = estados[no]['interfaces']
    return all(interfaces.get(s['interface']) == [f"{s['gateway']}/{s['prefixo']}"] for s in setores)


def endereco_pc(estados, no):
    enderecos = estados[no]['interfaces'].get('eth0', [])
    return str(interface_de(enderecos[0]).ip) if len(enderecos) == 1 else None


def conferir_plano(campos, respostas):
    """Campos errados do plano; aceita espaços e prefixo com ou sem barra."""
    erros = []
    for campo in campos:
        valor = str(respostas.get(campo['id'], '')).strip().lstrip('/').lower()
        if valor != campo['esperado']:
            erros.append(campo['id'])
    return erros


def plano_publico(campos, plano):
    return {'campos': [{k: c[k] for k in ('id', 'rotulo', 'grupo', 'tipo')} for c in campos],
            'respostas': deepcopy(plano['respostas']), 'erros': list(plano['erros']), 'correto': plano['correto']}


def chamados(c):
    """Chamados do cenário por etapa: CHAMADOS (Labs 8 e 10, um por etapa) ou o CHAMADO único da etapa 'chamado'."""
    if getattr(c, 'CHAMADOS', None):
        return c.CHAMADOS
    return {'chamado': c.CHAMADO} if getattr(c, 'CHAMADO', None) else {}


def marcar_suspeitas(c, s, no, tipo, alvo=None):
    """Registra as suspeitas do chamado que este comando testou (onde e o quê batem com a suspeita)."""
    for etapa, ch in chamados(c).items():
        testadas = s['diagnosticos'][etapa].setdefault('testadas', [])
        for x in ch.get('suspeitas', ()):
            if x['no'] == no and x['tipo'] == tipo and x.get('alvo') in (None, alvo) and x['id'] not in testadas:
                testadas.append(x['id'])


def suspeitas_faltando(ch, diagnostico):
    return [x for x in ch.get('suspeitas', ()) if x['id'] not in diagnostico.get('testadas', [])]


def dados_iniciais(c, sortear=None):
    sortear = sortear or random.sample
    return {'revisao': 0,
        'plano': {'respostas': {}, 'erros': [], 'correto': False},
        'diagnosticos': {etapa: {'ordem': sortear(list(ch['causas']), len(ch['causas'])), 'resposta': None, 'correta': False}
                         for etapa, ch in chamados(c).items()},
        'terminal': [],
        'estados': {no: {'interfaces': deepcopy(c.INICIAL[no]['interfaces']), 'rota_padrao': c.INICIAL[no]['rota_padrao'],
                         'rotas': list(c.INICIAL[no].get('rotas', [])), 'vlans': deepcopy(c.INICIAL[no].get('vlans', {})),
                         'dns': list(c.INICIAL[no].get('dns', [])), 'lido': False} for no in c.NOS},
        'testes': {no: {} for no in c.NOS},
        'conclusao_validada': False}


def etapas_concluidas(c, s, ativo):
    """Etapas em ordem: cada uma só conta se as anteriores também contam."""
    feitas = set()
    if not ativo:
        return feitas
    for etapa in c.ETAPAS:
        if etapa['id'] == 'comprovar':
            if s['conclusao_validada']:
                feitas.add('comprovar')
            break
        if not c.etapa_ok(s, etapa['id']):
            break
        feitas.add(etapa['id'])
    return feitas


def etapa_atual(c, s):
    feitas = etapas_concluidas(c, s, True)
    return next((e['id'] for e in c.ETAPAS if e['id'] not in feitas), None)


def estado_publico(c, dados, ativo=False):
    s = deepcopy(dados or c.dados_iniciais())
    feitas = etapas_concluidas(c, s, ativo)
    etapas = [{**e, 'concluida': e['id'] in feitas} for e in c.ETAPAS]
    atual = next((e['id'] for e in etapas if not e['concluida']), None)
    progresso = getattr(c, 'progresso_chamado', None)
    lista = []
    for etapa, ch in chamados(c).items():
        d = s['diagnosticos'][etapa]
        resolvido = etapa in feitas
        item = {'etapa': etapa, 'no': ch['no'], 'observar_no': ch.get('observar_no', ch['no']), 'observar': ch['observar'],
            'titulo': ch['titulo'], 'sintoma': ch['sintoma'], 'objetivo': ch.get('objetivo'),
            'opcoes': [{'id': i, 'texto': ch['causas'][i]} for i in d['ordem']], 'resposta': d['resposta'], 'correta': d['correta'],
            'situacao': 'resolvido' if resolvido else 'atual' if etapa == atual else 'fila'}
        if resolvido and ch.get('resolucao'):
            item['resolucao'] = ch['resolucao']
        if progresso and ativo:
            item['progresso'] = progresso(s, etapa)
        if ch.get('suspeitas'):
            item['suspeitas'] = [{**{k: x[k] for k in ('no', 'texto', 'onde', 'comando', 'olhar')},
                                  'testada': x['id'] in d.get('testadas', [])} for x in ch['suspeitas']]
        lista.append(item)
    # O chamado em atendimento; num cenário de chamado único, ele aparece mesmo fora da sua etapa.
    publico_chamado = next((i for i in lista if i['etapa'] == atual), lista[0] if len(lista) == 1 else None)
    # Blocos e gateways são as respostas do plano: só saem do servidor depois de o plano ser conferido.
    visiveis = set(c.SETORES) if s['plano']['correto'] else set(getattr(c, 'SETORES_MODELO', ()))
    setores = {k: (deepcopy(v) if k in visiveis else {'nome': v['nome'], 'interface': v['interface'], **({'pedido': v['pedido']} if 'pedido' in v else {})})
               for k, v in c.SETORES.items()}
    return {'id': c.LABORATORIO_ID, 'titulo': c.TITULO, 'descricao': c.DESCRICAO, 'xp': c.XP, 'rede': c.REDE,
        'nos': [{'chave': k, **deepcopy(v)} for k, v in c.NOS.items()], 'setores': setores, 'etapas': etapas,
        'proxima_etapa': atual,
        'concluido': all(e['concluida'] for e in etapas), 'retorno_preparado': True,
        'revisao': s['revisao'], 'terminal': s['terminal'], 'recusas': s.get('recusas', []), 'estados': s['estados'], 'testes': s['testes'],
        'plano': plano_publico(c.PLANO, s['plano']), 'chamado': publico_chamado,
        'chamados': lista if len(lista) > 1 else []}
