#!/usr/bin/env python3
"""Backup consistente do banco de usuários, progresso e XP, com o site no ar.

Usa a API de backup do SQLite (correta em modo WAL), confere a integridade da cópia,
grava compactado com permissão 600, relê o arquivo final e aplica a rotação:
os 14 backups mais recentes e o primeiro de cada mês dos últimos 12 meses.

Uso: /usr/bin/python3 tools/backup/backup_banco.py [--origem BANCO] [--destino PASTA]
Restauração: ver tools/backup/README.md.
"""
import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ORIGEM = Path('/opt/packetlab/data/auth/pinglevel_auth.db')
DESTINO = Path('/home/gabriel/backups-pinglevel/banco')
PREFIXO = 'pinglevel_auth-'
RECENTES = 14
MESES = 12


def verificar(caminho):
    """Integridade e contagem por tabela; levanta erro se o arquivo não for um banco íntegro."""
    conexao = sqlite3.connect(f'file:{caminho}?mode=ro', uri=True)
    try:
        resultado = conexao.execute('PRAGMA integrity_check').fetchone()[0]
        if resultado != 'ok':
            raise RuntimeError(f'integridade: {resultado}')
        tabelas = [t for (t,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t: conexao.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tabelas}
    finally:
        conexao.close()


def rotacionar(destino, agora):
    arquivos = sorted(destino.glob(f'{PREFIXO}*.db.gz'), reverse=True)
    manter = set(arquivos[:RECENTES])
    vistos = set()
    for arquivo in arquivos:
        mes = arquivo.name[len(PREFIXO):len(PREFIXO) + 6]
        idade = (agora.year * 12 + agora.month) - (int(mes[:4]) * 12 + int(mes[4:]))
        if idade < MESES and mes not in vistos:
            vistos.add(mes)
            manter.add(min(a for a in arquivos if a.name[len(PREFIXO):len(PREFIXO) + 6] == mes))
    removidos = [a for a in arquivos if a not in manter]
    for arquivo in removidos:
        arquivo.unlink()
    return removidos


def fazer_backup(origem, destino, agora=None):
    agora = agora or datetime.now()
    destino.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destino, 0o700)
    final = destino / f'{PREFIXO}{agora:%Y%m%d-%H%M%S}.db.gz'
    with tempfile.TemporaryDirectory(dir=destino) as temporaria:
        copia = Path(temporaria) / 'copia.db'
        fonte = sqlite3.connect(f'file:{origem}?mode=ro', uri=True)
        alvo = sqlite3.connect(copia)
        try:
            fonte.backup(alvo)
        finally:
            alvo.close()
            fonte.close()
        contagens = verificar(copia)
        parcial = Path(temporaria) / final.name
        with open(copia, 'rb') as entrada, gzip.open(parcial, 'wb') as saida:
            shutil.copyfileobj(entrada, saida)
        os.chmod(parcial, 0o600)
        # Relê o arquivo compactado: o backup só conta se puder ser restaurado.
        relida = Path(temporaria) / 'relida.db'
        with gzip.open(parcial, 'rb') as entrada, open(relida, 'wb') as saida:
            shutil.copyfileobj(entrada, saida)
        if verificar(relida) != contagens:
            raise RuntimeError('o arquivo compactado não corresponde à cópia verificada')
        os.replace(parcial, final)
    return final, contagens, rotacionar(destino, agora)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--origem', type=Path, default=ORIGEM)
    parser.add_argument('--destino', type=Path, default=DESTINO)
    args = parser.parse_args()
    momento = f'{datetime.now():%Y-%m-%d %H:%M:%S}'
    try:
        final, contagens, removidos = fazer_backup(args.origem, args.destino)
    except Exception as erro:
        print(f'{momento} FALHA no backup de {args.origem}: {erro}', file=sys.stderr)
        return 1
    resumo = ', '.join(f'{t} {n}' for t, n in contagens.items() if t in ('usuarios', 'progresso_laboratorios', 'eventos_xp'))
    print(f'{momento} ok {final.name} ({final.stat().st_size} bytes; {resumo}; {len(removidos)} antigos removidos)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
