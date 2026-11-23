"""Preserva, byte a byte, toda a lógica anterior ao render do laboratório real."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ContratoLaboratorio(unittest.TestCase):
    def test_logica_anterior_de_api_sessao_comandos_tutor_conclusao_preservada(self):
        source=(ROOT/'src/pages/Laboratorio.jsx').read_text()
        prefix=source.split('  if (carregando) return (',1)[0]
        prefix,count=re.subn(r'  // RESPONSIVO: INICIO[^\n]*\n.*?  // RESPONSIVO: FIM[^\n]*\n','',prefix,flags=re.S)
        self.assertEqual(count,2)
        prefix=prefix.replace("import './LaboratorioResponsivo.css'\n",'')
        self.assertEqual(prefix,(ROOT/'tests/fixtures/primeiroContatoAntesResponsivo.txt').read_text())

    def test_nenhuma_api_demonstrativa_importada_na_tela_oficial(self):
        source=(ROOT/'src/pages/Laboratorio.jsx').read_text()
        self.assertNotIn('criarAPIDemonstracao',source)
        self.assertNotIn('previaLayoutLaboratorio',source)
        self.assertNotIn('pinglevel:preview-layout:',source)
        self.assertNotIn('PRÉVIA DE LAYOUT',source)
        self.assertIn("fetch(caminho, { credentials: 'same-origin', ...opcoes })",source)
        self.assertIn("sessionStorage.setItem('pinglevel:lab:sessao'",source)

if __name__=='__main__':unittest.main(verbosity=2)
