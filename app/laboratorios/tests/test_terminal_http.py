import json
from laboratorios.api_terminal_guiado import despachar_terminal
from laboratorios.terminal_guiado import ErroTerminal

USUARIO = {'id': 7, 'login': 'aluno'}


class Servico:
    def __init__(self, erro=None):
        self.erro, self.chamadas = erro, []

    def executar_acao(self, uid, login, acao, dados):
        self.chamadas.append(acao)
        if self.erro and acao != 'status':
            raise self.erro
        return {'sucesso': True, 'acao': acao, 'missao': {'revisao': 1}}


def chamar(servico, metodo='POST', rota='/api/terminal/terminal', corpo=b'{}', origem=True, limitar=lambda *a: True, usuario=USUARIO):
    return despachar_terminal(servico, usuario, metodo, rota, corpo, origem_autorizada=origem, limitar=limitar)


def test_rotas_e_metodos():
    assert chamar(Servico(), 'GET', '/api/terminal/status', b'')[1] == 200
    assert chamar(Servico(), 'GET', '/api/terminal/terminal', b'')[1] == 405
    assert chamar(Servico(), rota='/api/terminal/aplicar')[1] == 404


def test_identidade_origem_tamanho_e_limite():
    assert chamar(Servico(), usuario=None)[1] == 401
    assert chamar(Servico(), usuario={**USUARIO, 'troca_senha_obrigatoria': True})[1] == 403
    assert chamar(Servico(), origem=False)[1] == 403
    assert chamar(Servico(), corpo=b'x' * 2049)[1] == 413
    assert chamar(Servico(), limitar=lambda *a: False)[1] == 429
    assert chamar(Servico(), corpo=b'{x')[1] == 400


def test_erro_do_servico_devolve_estado_e_status():
    payload, codigo = chamar(Servico(ErroTerminal('Comando não disponível neste laboratório.', 400)), corpo=json.dumps({'comando': 'ls'}).encode())
    assert codigo == 400 and payload['sucesso'] is False and payload['missao'] == {'revisao': 1}
    assert 'não disponível' in payload['mensagem']


def test_falha_inesperada_nao_vaza_detalhes():
    payload, codigo = chamar(Servico(RuntimeError('caminho /opt/segredo')))
    assert codigo == 503 and 'segredo' not in json.dumps(payload) and payload['recarregar']
