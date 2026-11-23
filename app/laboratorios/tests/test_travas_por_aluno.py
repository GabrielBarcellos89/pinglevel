"""Alunos simultâneos: a criação lenta de um ambiente não bloqueia os outros alunos, e cada um recebe uma rede de
controle diferente. Usa o gerenciador real com a montagem no CORE substituída."""
import threading
import time

import pytest

from laboratorios import gerenciador as g


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setattr(g, 'ARQUIVO_ESTADO', tmp_path / 'laboratorios_ativos.json')
    e = g.GerenciadorLaboratorios()
    liberar, entrou = threading.Event(), threading.Event()

    def criar(uid, login, labid, indice):
        if uid == 1:  # o aluno 1 fica "montando" a topologia até o teste liberar
            entrou.set()
            assert liberar.wait(5)
        agora = time.time()
        lab = g.Laboratorio(usuario_id=uid, login=login, laboratorio_id=labid, session_id=uid, indice_rede=indice,
                            controlnet=f'172.30.{indice}.0/24', enderecos={}, iniciado_em=agora, prazo=agora + 900,
                            tempo_extensao=300, max_extensoes=1)
        with e._lock:
            e._laboratorios[uid] = lab
        return lab

    e._criar = criar
    e.liberar, e.entrou = liberar, entrou
    return e


def test_criacao_lenta_nao_bloqueia_outro_aluno(engine):
    lab2 = engine.criar(2, 'b', 'investigando-a-lan')
    criando = threading.Thread(target=engine.criar, args=(1, 'a', 'enderecos-e-nomes'))
    criando.start()
    try:
        assert engine.entrou.wait(5)
        _sem_esperar(engine, lab2)
    finally:
        engine.liberar.set()
    criando.join(5)
    assert engine.obter(1).indice_rede != lab2.indice_rede


def _sem_esperar(engine, lab2):
    inicio = time.time()
    # Enquanto o aluno 1 espera o CORE, o aluno 2 consulta, comanda (trava dele) e estende sem esperar.
    assert engine.obter(2) is lab2
    with engine.trava(2):
        engine.dados_temporais(lab2)
    assert engine.estender(2).extensoes_utilizadas == 1
    assert time.time() - inicio < 0.5
    # A trava do aluno 1 continua ocupada: um segundo pedido dele espera a criação terminar.
    assert not engine.trava(1).acquire(timeout=0.1)


def test_criacoes_simultaneas_recebem_redes_diferentes(engine):
    engine.liberar.set()
    resultados = {}
    threads = [threading.Thread(target=lambda u=u: resultados.update({u: engine.criar(u, f'a{u}', 'investigando-a-lan')}))
               for u in range(300, 310)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(5)
    indices = [lab.indice_rede for lab in resultados.values()]
    assert len(indices) == 10 and len(set(indices)) == 10
    assert not engine._reservados


def test_indice_reservado_nao_e_entregue_a_outro(engine):
    with engine._lock:
        engine._reservados.add(5)
    assert engine._indice_disponivel(5) != 5
