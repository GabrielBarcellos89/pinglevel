"""Falha de preparação nunca habilita treino; remoção manual continua permitida."""
import pytest
from laboratorios.tests.test_gateway_guiado import setup_service,act

def test_quarentena_bloqueia_treino_mas_permite_encerrar():
    s,e,saved,error=setup_service();act(s,'iniciar');e.lab.preparacao_confirmada=False
    status=act(s,'status')
    assert status['ativo'] and status['disponivel'] is False and status['preparacao_pendente']
    for acao in ['iniciar','prever','testar-antes','aplicar','conferir','testar-depois','estender']:
        with pytest.raises(error) as exc:act(s,acao)
        assert exc.value.status==503
    assert not e.commands and not saved
    assert not act(s,'encerrar')['ativo']
