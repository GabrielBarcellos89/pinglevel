import gzip
import sqlite3
import stat
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backup_banco  # noqa: E402


def banco_wal(caminho):
    """Banco em modo WAL com escritas ainda não transferidas para o arquivo principal."""
    conexao = sqlite3.connect(caminho)
    conexao.execute('PRAGMA journal_mode=wal')
    conexao.execute('PRAGMA wal_autocheckpoint=0')
    conexao.execute('CREATE TABLE usuarios(id INTEGER PRIMARY KEY, nome TEXT)')
    conexao.executemany('INSERT INTO usuarios(nome) VALUES (?)', [('a',), ('b',), ('c',)])
    conexao.commit()
    return conexao


def test_backup_consistente_inclui_escritas_ainda_no_wal_e_protege_permissoes(tmp_path):
    aberta = banco_wal(tmp_path / 'origem.db')
    try:
        assert (tmp_path / 'origem.db-wal').stat().st_size > 0
        final, contagens, removidos = backup_banco.fazer_backup(tmp_path / 'origem.db', tmp_path / 'destino')
    finally:
        aberta.close()
    assert contagens == {'usuarios': 3} and removidos == []
    assert stat.S_IMODE(final.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / 'destino').stat().st_mode) == 0o700
    restaurado = tmp_path / 'restaurado.db'
    restaurado.write_bytes(gzip.decompress(final.read_bytes()))
    assert backup_banco.verificar(restaurado) == {'usuarios': 3}
    assert sorted(p.name for p in (tmp_path / 'destino').iterdir()) == [final.name]


def test_origem_invalida_falha_sem_deixar_arquivo(tmp_path, capsys, monkeypatch):
    (tmp_path / 'origem.db').write_bytes(b'nao e um banco sqlite' * 100)
    monkeypatch.setattr(sys, 'argv', ['backup_banco.py', '--origem', str(tmp_path / 'origem.db'), '--destino', str(tmp_path / 'destino')])
    assert backup_banco.main() == 1
    assert 'FALHA' in capsys.readouterr().err
    assert not list((tmp_path / 'destino').glob('*.gz'))


def test_rotacao_mantem_recentes_e_um_por_mes(tmp_path):
    datas = [datetime(2026, 10, d, 3) for d in range(1, 30)] + [
        datetime(2026, 9, 2, 3), datetime(2026, 9, 20, 3), datetime(2025, 9, 5, 3), datetime(2025, 11, 5, 3)]
    for data in datas:
        (tmp_path / f'{backup_banco.PREFIXO}{data:%Y%m%d-%H%M%S}.db.gz').write_bytes(b'x')
    backup_banco.rotacionar(tmp_path, datetime(2026, 10, 29, 3))
    restantes = sorted(p.name[len(backup_banco.PREFIXO):len(backup_banco.PREFIXO) + 8] for p in tmp_path.iterdir())
    outubro = [f'202610{d:02d}' for d in range(16, 30)]
    # 14 mais recentes, o primeiro de outubro e de setembro de 2026 e o de novembro de 2025 (11 meses atrás);
    # setembro de 2025 (13 meses) sai.
    assert restantes == sorted(['20251105', '20260902', '20261001', *outubro])
