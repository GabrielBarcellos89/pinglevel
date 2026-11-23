"""Estado pedagógico da aula IPv4. Não inicia nem manipula sessões CORE."""
from __future__ import annotations

import json
import time

import progresso

AULA_ID = 'enderecamento-ipv4'
VERSAO_ESTADO = 1
VERSAO_CONTEUDO = 1
OPCOES_PRATICA = {
    'rede': {'rede-10', 'host-34', 'broadcast-10'},
    'local': {'sim', 'nao'},
    'gateway': {'mac-remoto', 'gateway', 'broadcast'},
}


class ConflitoEstado(ValueError):
    """Outra aba ou requisição já atualizou o estado."""


def _checar_revisao(estado, revisao):
    if type(revisao) is not int or revisao < 0:
        raise ValueError('Envie a revisão inteira retornada pela consulta da aula.')
    if revisao != estado['revisao']:
        raise ConflitoEstado('Revisão desatualizada; recarregue a aula.')


def _validar_aula(aula_id):
    if aula_id != AULA_ID:
        raise ValueError('Estado disponível apenas para a aula IPv4.')


def _pendente():
    return {'status': 'pendente'}


def _ler(conexao, usuario_id):
    registro = conexao.execute(
        'SELECT * FROM progresso_aulas WHERE usuario_id = ? AND aula_id = ?',
        (usuario_id, AULA_ID),
    ).fetchone()
    linha = conexao.execute(
        'SELECT * FROM estado_aulas WHERE usuario_id = ? AND aula_id = ?',
        (usuario_id, AULA_ID),
    ).fetchone()
    concluida = bool(registro and registro['concluida'])
    estado = {
        'aula_id': AULA_ID,
        'versao_estado': VERSAO_ESTADO,
        'versao_conteudo': VERSAO_CONTEUDO,
        'modo': 'revisao' if concluida else 'andamento',
        'concluida': concluida,
        'legado_sem_respostas': bool(registro and not linha),
        'etapa_visitada': 0,
        'etapa_liberada': 0,
        'etapa_retomada': 0,
        'revisao': 0,
        'respostas': {'previsao': '', 'pratica': {}, 'interpretacao': ''},
        'validacoes': {'pratica': _pendente(), 'interpretacao': _pendente()},
    }
    if linha:
        if (linha['versao_estado'] != VERSAO_ESTADO
                or linha['versao_conteudo'] != VERSAO_CONTEUDO):
            raise ValueError('Estado de outra versão da aula; recuperação precisa de migração.')
        for campo in ('etapa_visitada', 'etapa_liberada', 'revisao'):
            estado[campo] = linha[campo]
        estado['respostas'] = json.loads(linha['respostas_json'])
        estado['validacoes'] = json.loads(linha['validacoes_json'])
        estado['etapa_retomada'] = 0 if concluida else estado['etapa_visitada']
    return estado


def obter_estado(usuario_id, aula_id):
    _validar_aula(aula_id)
    with progresso._conectar() as conexao:
        return _ler(conexao, usuario_id)


def _gravar(conexao, usuario_id, estado):
    agora = int(time.time())
    conexao.execute('''
        INSERT OR IGNORE INTO progresso_aulas (
            usuario_id, aula_id, modulo_id, etapa_atual, percentual,
            concluida, iniciado_em, atualizado_em
        ) VALUES (?, ?, 'enderecamento', 0, 0, 0, ?, ?)
    ''', (usuario_id, AULA_ID, agora, agora))
    estado['revisao'] += 1
    conexao.execute('''
        INSERT INTO estado_aulas (
            usuario_id, aula_id, versao_estado, versao_conteudo,
            etapa_visitada, etapa_liberada, respostas_json,
            validacoes_json, revisao, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario_id, aula_id) DO UPDATE SET
            etapa_visitada = excluded.etapa_visitada,
            etapa_liberada = excluded.etapa_liberada,
            respostas_json = excluded.respostas_json,
            validacoes_json = excluded.validacoes_json,
            revisao = excluded.revisao,
            atualizado_em = excluded.atualizado_em
    ''', (usuario_id, AULA_ID, VERSAO_ESTADO, VERSAO_CONTEUDO,
          estado['etapa_visitada'], estado['etapa_liberada'],
          json.dumps(estado['respostas'], ensure_ascii=False),
          json.dumps(estado['validacoes'], ensure_ascii=False),
          estado['revisao'], agora))


def _atualizar_respostas(estado, respostas):
    if not isinstance(respostas, dict) or set(respostas) - {'previsao', 'pratica', 'interpretacao'}:
        raise ValueError('Campos de respostas inválidos.')
    atuais = estado['respostas']
    for campo, valor in respostas.items():
        if campo == 'pratica':
            if not isinstance(valor, dict) or set(valor) - set(OPCOES_PRATICA):
                raise ValueError('Exercícios inválidos.')
            for exercicio, opcao in valor.items():
                if not isinstance(opcao, str) or opcao not in OPCOES_PRATICA[exercicio] | {''}:
                    raise ValueError('Opção da prática inválida.')
            novo = {**atuais['pratica'], **valor}
        else:
            opcoes = ({'gateway', 'destino', 'switch', ''} if campo == 'previsao'
                      else {'mac-gateway', 'mac-remoto', 'ip-rede', ''})
            if not isinstance(valor, str) or valor not in opcoes:
                raise ValueError('Opção inválida.')
            novo = valor
        if novo != atuais[campo]:
            atuais[campo] = novo
            if campo in estado['validacoes']:
                estado['validacoes'][campo] = _pendente()


def _limite(estado):
    if not estado['respostas']['previsao']:
        return 1
    if estado['validacoes']['pratica']['status'] != 'aprovada':
        return 2
    if estado['validacoes']['interpretacao']['status'] != 'aprovada':
        return 4
    return 5


def _ajustar_etapas(estado):
    estado['etapa_liberada'] = min(estado['etapa_liberada'], _limite(estado))
    estado['etapa_visitada'] = min(estado['etapa_visitada'], estado['etapa_liberada'])


def salvar_estado(usuario_id, aula_id, revisao, respostas, etapa_visitada=None):
    _validar_aula(aula_id)
    with progresso._conectar() as conexao:
        conexao.execute('BEGIN IMMEDIATE')
        estado = _ler(conexao, usuario_id)
        if estado['concluida']:
            raise ValueError('Revisão não altera o percurso concluído.')
        _checar_revisao(estado, revisao)
        _atualizar_respostas(estado, respostas)
        _ajustar_etapas(estado)
        if etapa_visitada is not None:
            if type(etapa_visitada) is not int or not 0 <= etapa_visitada <= estado['etapa_liberada']:
                raise ValueError('Etapa ainda não liberada.')
            estado['etapa_visitada'] = etapa_visitada
        _gravar(conexao, usuario_id, estado)
        return _ler(conexao, usuario_id)


def validar_atividade(usuario_id, aula_id, revisao, atividade):
    _validar_aula(aula_id)
    if atividade not in ('pratica', 'interpretacao'):
        raise ValueError('Atividade inválida.')
    with progresso._conectar() as conexao:
        conexao.execute('BEGIN IMMEDIATE')
        estado = _ler(conexao, usuario_id)
        if estado['concluida']:
            raise ValueError('Revisão não altera o percurso concluído.')
        _checar_revisao(estado, revisao)
        etapa_exigida = 2 if atividade == 'pratica' else 4
        if estado['etapa_liberada'] < etapa_exigida:
            raise ValueError('Atividade ainda não liberada.')
        respostas = estado['respostas']
        if atividade == 'pratica':
            corretas = {'rede': 'rede-10', 'local': 'sim', 'gateway': 'gateway'}
            if any(not respostas['pratica'].get(item) for item in corretas):
                raise ValueError('Responda todos os exercícios antes de conferir.')
            erros = [item for item, certa in corretas.items() if respostas['pratica'][item] != certa]
        else:
            if not respostas['interpretacao']:
                raise ValueError('Responda à interpretação antes de conferir.')
            erros = [] if respostas['interpretacao'] == 'mac-gateway' else ['interpretacao']
        estado['validacoes'][atividade] = {
            'status': 'incorreta' if erros else 'aprovada',
            'erros': erros,
            'conferida_em': int(time.time()),
        }
        _ajustar_etapas(estado)
        _gravar(conexao, usuario_id, estado)
        return _ler(conexao, usuario_id)


def avancar(usuario_id, aula_id, revisao, etapa):
    _validar_aula(aula_id)
    with progresso._conectar() as conexao:
        conexao.execute('BEGIN IMMEDIATE')
        estado = _ler(conexao, usuario_id)
        if estado['concluida']:
            raise ValueError('Use o modo revisão para uma aula concluída.')
        _checar_revisao(estado, revisao)
        if (type(etapa) is not int or not 0 <= etapa <= 5
                or etapa > estado['etapa_liberada'] + 1 or etapa > _limite(estado)):
            raise ValueError('Conclua a atividade anterior antes de avançar.')
        estado['etapa_visitada'] = etapa
        estado['etapa_liberada'] = max(estado['etapa_liberada'], etapa)
        _gravar(conexao, usuario_id, estado)
        conexao.execute('''
            UPDATE progresso_aulas
            SET etapa_atual = MAX(etapa_atual, ?),
                percentual = MAX(percentual, ?), atualizado_em = ?
            WHERE usuario_id = ? AND aula_id = ?
        ''', (etapa, round(((etapa + 1) / 6) * 100), int(time.time()), usuario_id, AULA_ID))
        return _ler(conexao, usuario_id)


def verificar_conclusao(conexao, usuario_id, revisao):
    """Verifica evidências dentro da transação de conclusão e recompensa existente."""
    estado = _ler(conexao, usuario_id)
    _checar_revisao(estado, revisao)
    if estado['etapa_liberada'] != 5 or _limite(estado) != 5:
        raise ValueError('Conclua a previsão, a prática e a interpretação antes de finalizar.')
