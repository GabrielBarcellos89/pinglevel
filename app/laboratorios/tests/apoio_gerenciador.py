"""Valores de módulo do gerenciador para testes que compilam métodos isolados, sem importar o SDK do CORE."""
import ast
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[1] / 'gerenciador.py'


def constantes():
    arvore = ast.parse(ARQUIVO.read_text())
    return {n.targets[0].id: ast.literal_eval(n.value) for n in arvore.body
            if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') in ('COM_ROTEADOR', 'COM_SETORES')}
