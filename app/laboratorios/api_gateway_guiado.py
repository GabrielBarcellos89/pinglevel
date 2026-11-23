"""Adaptador HTTP; identidade e validação de origem pertencem ao Handler autenticado."""
import json
from laboratorios.gateway_guiado import ErroGateway

ROTAS = {'/api/gateway/' + a: a for a in ('status', 'iniciar', 'tutor', 'terminal', 'consultar', 'testar-local', 'testar-remoto', 'classificar', 'prever', 'testar-antes',
    'aplicar', 'conferir', 'testar-depois', 'interpretar', 'validar', 'encerrar', 'estender')}


def despachar_gateway(servico, usuario, metodo, rota, corpo, *, origem_autorizada, limitar):
    if not isinstance(usuario, dict) or type(usuario.get('id')) is not int or usuario['id'] <= 0:
        return {'sucesso': False, 'mensagem': 'Entre novamente para acessar o laboratório.'}, 401
    if usuario.get('troca_senha_obrigatoria'):
        return {'sucesso': False, 'mensagem': 'Conclua a atualização de acesso antes de iniciar o laboratório.'}, 403
    acao = ROTAS.get(rota)
    if acao is None:
        return {'sucesso': False, 'mensagem': 'Operação de laboratório inexistente.'}, 404
    if metodo != ('GET' if acao == 'status' else 'POST'):
        return {'sucesso': False, 'mensagem': 'Método HTTP não permitido.'}, 405
    if metodo == 'POST' and not origem_autorizada:
        return {'sucesso': False, 'mensagem': 'Origem da requisição não autorizada.'}, 403
    if not isinstance(corpo, bytes) or len(corpo) > 2048:
        return {'sucesso': False, 'mensagem': 'Corpo da requisição inválido ou excessivo.'}, 413
    if metodo == 'POST' and not limitar(f"gateway:{usuario['id']}", 30, 60):
        return {'sucesso': False, 'mensagem': 'Limite de operações atingido. Aguarde antes de tentar novamente.'}, 429
    if acao == 'tutor' and not limitar(f"gateway-tutor:{usuario['id']}", 6, 60):
        return {'sucesso': False, 'mensagem': 'O Link recebeu muitas perguntas. Aguarde um minuto.'}, 429
    try:
        dados = {} if metodo == 'GET' else json.loads(corpo or b'{}')
        if not isinstance(dados, dict):
            raise ErroGateway('Envie um objeto JSON com os campos esperados.')
        return servico.executar_acao(usuario['id'], usuario.get('login', 'aluno'), acao, dados), 200
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {'sucesso': False, 'mensagem': 'JSON inválido.'}, 400
    except ErroGateway as erro:
        resultado = {'sucesso': False, 'mensagem': str(erro)}
        try:
            estado = servico.executar_acao(usuario['id'], usuario.get('login', 'aluno'), 'status', {})
            resultado = {**estado, **resultado}
        except Exception:
            resultado['recarregar'] = True
        return resultado, erro.status
    except Exception:
        return {'sucesso': False, 'mensagem': 'A operação não foi confirmada. Consulte o estado antes de continuar.',
            'recarregar': True}, 503
