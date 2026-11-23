import importlib


def test_cenario_publico_isolado_sem_gabarito_antecipado():
    assert importlib.util.find_spec('laboratorios.cenarios.saindo_rede_local') is not None
    c = importlib.import_module('laboratorios.cenarios.saindo_rede_local')
    s = c.estado_publico(None)
    assert c.LABORATORIO_ID == 'saindo-da-rede-local'
    assert (c.XP, c.TEMPO_LIMITE, c.TEMPO_EXTENSAO, c.MAX_EXTENSOES) == (100, 900, 300, 1)
    assert s['gateway'] == {'valor': '', 'confirmado': False, 'observado': None}
    assert s['previsao'] == {'local': None, 'remota': None, 'registrada': False}
    assert s['proxima_etapa'] == 'local' and not s['concluido']
    assert [n['id'] for n in s['nos']] == [1, 2, 3, 4, 5]
    assert 'interfaces' not in next(n for n in s['nos'] if n['id'] == 5)
    assert s['retorno_preparado'] is True
    s['antes']['detalhes'].append('alteracao')
    assert c.dados_iniciais()['antes']['detalhes'] == []
    assert c.detectar_evidencias(1, 'arbitrario', 0, 'ok') == set()
    assert not c.montar_estado({'concluido': True})['concluido']
