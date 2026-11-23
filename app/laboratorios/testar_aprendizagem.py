import unittest
from unittest.mock import Mock
from laboratorios.gerenciador import GerenciadorLaboratorios, Laboratorio


class TestAprendizagem(unittest.TestCase):
    def setUp(self):
        self.g = GerenciadorLaboratorios()
        self.lab = Laboratorio(1, 'teste', 'primeiro-contato', 99, 1, 'rede',
                               {1: 'endereco'}, 1000, 9999999999, 180, 1)
        self.g._laboratorios[1] = self.lab
        self.g.executar = Mock(return_value=(0, 'teste'))

    def prerequisitos(self):
        self.lab.evidencias.update({"identificacao", "enderecamento"})

    def test_previsao_bloqueada_ate_concluir_etapas_anteriores(self):
        with self.assertRaises(ValueError):
            self.g.responder_aprendizagem(1, 'previsao', 'resposta')
        self.prerequisitos()
        estado = self.g.responder_aprendizagem(1, 'previsao', 'resposta')
        self.assertTrue(estado['aprendizagem']['pode_prever'])

    def test_ping_bloqueado_antes_de_previsao(self):
        self.prerequisitos()
        with self.assertRaises(ValueError):
            self.g.executar_observado(1, 1, 'ping -c 2 10.0.0.21')
        self.g.executar.assert_not_called()
        self.assertFalse(self.g._execucoes)

    def test_hipotese_errada_e_aceita_e_nao_pode_ser_trocada(self):
        self.prerequisitos()
        estado = self.g.responder_aprendizagem(1, 'previsao', 'sem_resposta')
        self.assertEqual(estado['aprendizagem']['previsao'], 'sem_resposta')
        with self.assertRaises(ValueError):
            self.g.responder_aprendizagem(1, 'previsao', 'resposta')

    def test_interpretacao_antes_do_ping_e_bloqueada(self):
        self.prerequisitos()
        self.g.responder_aprendizagem(1, 'previsao', 'resposta')
        with self.assertRaises(ValueError):
            self.g.responder_aprendizagem(1, 'interpretacao', 'alcance')

    def test_pratica_sozinha_nao_conclui(self):
        self.lab.evidencias.update({'identificacao', 'enderecamento', 'conectividade'})
        estado = self.g.estado_missao(1)
        self.assertTrue(estado['pratica_concluida'])
        self.assertFalse(estado['concluido'])

    def test_pistas_e_conclusao_sem_captura(self):
        self.prerequisitos()
        self.g.responder_aprendizagem(1, 'previsao', 'sem_envio')
        self.lab.evidencias.update({'identificacao', 'enderecamento', 'conectividade'})
        um = self.g.responder_aprendizagem(1, 'interpretacao', 'internet')
        dois = self.g.responder_aprendizagem(1, 'interpretacao', 'internet')
        self.assertFalse(dois['concluido'])
        self.assertNotEqual(um['aprendizagem']['feedback'], dois['aprendizagem']['feedback'])
        estado = self.g.responder_aprendizagem(1, 'interpretacao', 'alcance')
        self.assertTrue(estado['concluido'])
        self.assertIsNone(self.lab.bastidores)
        self.assertEqual(self.g.estado_missao(1, heartbeat=False)['aprendizagem'], estado['aprendizagem'])

    def test_resposta_invalida_e_usuario_sem_sessao(self):
        with self.assertRaises(ValueError):
            self.g.responder_aprendizagem(1, 'previsao', 'inventada')
        with self.assertRaises(ValueError):
            self.g.responder_aprendizagem(2, 'previsao', 'resposta')
        self.assertIsNone(self.lab.aprendizagem['previsao'])


if __name__ == '__main__':
    unittest.main()
