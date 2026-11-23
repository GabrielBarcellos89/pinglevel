"""Testes de tempo sem conexão com CORE, Docker ou arquivos de sessões reais."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from laboratorios.gerenciador import GerenciadorLaboratorios, Laboratorio


class TestTempoLaboratorio(unittest.TestCase):
    def setUp(self):
        self.relogio = patch("laboratorios.gerenciador.time.time", return_value=1000)
        self.agora = self.relogio.start()
        self.addCleanup(self.relogio.stop)
        self.gerenciador = GerenciadorLaboratorios()
        self.gerenciador._core = Mock(return_value=Mock())
        self.gerenciador._salvar_estado = Mock()
        self.lab = self.novo_lab(1)

    def novo_lab(self, usuario):
        lab = Laboratorio(
            usuario_id=usuario, login=f"aluno{usuario}",
            laboratorio_id="primeiro-contato", session_id=usuario,
            indice_rede=usuario, controlnet=f"172.30.{usuario}.0/24",
            enderecos={}, iniciado_em=1000, prazo=1300,
            tempo_extensao=180, max_extensoes=1, heartbeat=1000,
        )
        self.gerenciador._laboratorios[usuario] = lab
        return lab

    def test_extensao_adiciona_180_e_bloqueia_repeticao(self):
        self.gerenciador.estender(1)
        self.assertEqual(self.lab.prazo, 1480)
        self.assertEqual(self.lab.extensoes_utilizadas, 1)
        with self.assertRaises(ValueError):
            self.gerenciador.estender(1)
        self.assertFalse(self.gerenciador.dados_temporais(self.lab)["pode_estender"])

    def test_expira_no_prazo_mesmo_com_atividade(self):
        self.agora.return_value = 1300
        self.lab.heartbeat = 1299
        self.assertEqual(self.gerenciador.encerrar_expirados(300), [1])
        self.gerenciador._core().delete_session.assert_called_once_with(1)

    def test_nao_estende_sessao_expirada(self):
        self.agora.return_value = 1300
        with self.assertRaises(ValueError):
            self.gerenciador.estender(1)
        self.assertIsNone(self.gerenciador.obter(1))

    def test_status_nao_renova_heartbeat_nem_prazo(self):
        self.agora.return_value = 1100
        self.gerenciador.obter(1, heartbeat=False)
        self.gerenciador.estado_missao(1, heartbeat=False)
        dados = self.gerenciador.dados_temporais(self.lab)
        self.assertEqual(self.lab.heartbeat, 1000)
        self.assertEqual(dados["prazo"], 1300)
        self.assertEqual(dados["segundos_restantes"], 200)

    def test_inatividade_e_isolamento(self):
        outro = self.novo_lab(2)
        self.agora.return_value = 1200
        outro.heartbeat = 1199
        self.assertEqual(self.gerenciador.encerrar_expirados(120), [1])
        self.assertIs(self.gerenciador.obter(2, heartbeat=False), outro)

    def test_extensoes_concorrentes_consumem_apenas_uma(self):
        def tentar(_):
            try:
                self.gerenciador.estender(1)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(tentar, range(2)))
        self.assertEqual(sum(resultados), 1)
        self.assertEqual(self.lab.prazo, 1480)

    def test_extensao_preserva_sessao_ate_novo_prazo(self):
        self.gerenciador.estender(1)
        self.agora.return_value = 1300
        self.lab.heartbeat = 1299
        self.assertEqual(self.gerenciador.encerrar_expirados(300), [])
        self.agora.return_value = 1480
        self.lab.heartbeat = 1479
        self.assertEqual(self.gerenciador.encerrar_expirados(300), [1])


if __name__ == "__main__":
    unittest.main()
