import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'prototipo'))
import progresso  # noqa: E402


def test_aula_gateway_registrada_com_seis_etapas_e_xp():
    aula = progresso.AULAS['fundamentos-gateway']
    assert aula == {'modulo_id': 'fundamentos', 'titulo': 'Gateway e entrega local', 'total_etapas': 6, 'xp': 100}


def test_aula_ferramentas_registrada_com_seis_etapas_e_xp():
    aula = progresso.AULAS['fundamentos-ferramentas']
    assert aula['total_etapas'] == 6 and aula['xp'] == 100 and aula['modulo_id'] == 'fundamentos'


def test_aula_plano_abre_o_modulo_2():
    aula = progresso.AULAS['planejamento-enderecamento']
    assert aula['total_etapas'] == 6 and aula['xp'] == 100 and aula['modulo_id'] == 'planejamento'


def test_aula_roteamento_registrada_no_modulo_2():
    aula = progresso.AULAS['planejamento-roteamento']
    assert aula['total_etapas'] == 7 and aula['xp'] == 100 and aula['modulo_id'] == 'planejamento'


def test_aula_vlsm_registrada_no_modulo_2():
    aula = progresso.AULAS['planejamento-vlsm']
    assert aula['total_etapas'] == 6 and aula['xp'] == 100 and aula['modulo_id'] == 'planejamento'
