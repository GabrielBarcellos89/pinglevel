import unittest

from laboratorios.tutoria import avaliar_interacao


class TestTutorLinkV21(unittest.TestCase):
    def avaliar(self, etapa, pergunta, historico=None):
        return avaliar_interacao(etapa, pergunta, historico or [])

    def test_ajuda_pratica_permanece_controlada(self):
        r = self.avaliar("identificacao", "como identifico o computador?")
        self.assertIsNotNone(r["resposta_controlada"])

    def test_tentativa_permanece_controlada(self):
        r = self.avaliar("identificacao", "name host?")
        self.assertIn("ordem inversa", r["resposta_controlada"])

    def test_ip_futuro_permanece_controlado(self):
        r = self.avaliar("identificacao", "como consulto o ip?")
        self.assertEqual(r["classificacao"], "fora_da_etapa")
        self.assertIsNotNone(r["resposta_controlada"])

    def test_conceito_ifconfig_segue_para_ia_na_etapa_correta(self):
        r = self.avaliar("enderecamento", "o que é o ifconfig?")
        self.assertEqual(r["classificacao"], "explicacao_conceitual")
        self.assertIsNone(r["resposta_controlada"])

    def test_como_ping_encontra_caminho_segue_para_ia(self):
        r = self.avaliar("conectividade", "como o ping encontra o caminho?")
        self.assertEqual(r["classificacao"], "explicacao_conceitual")
        self.assertIsNone(r["resposta_controlada"])

    def test_referencia_ele_segue_para_ia(self):
        r = self.avaliar("conectividade", "ele sabe a rota?")
        self.assertEqual(r["classificacao"], "explicacao_conceitual")
        self.assertIsNone(r["resposta_controlada"])

    def test_ping_comando_permanece_controlado(self):
        r = self.avaliar("conectividade", "ping -c 2 10.0.0.21")
        self.assertEqual(r["classificacao"], "comando_correto")
        self.assertIsNotNone(r["resposta_controlada"])

    def test_lista_de_comandos_e_limitada_a_etapa(self):
        r = self.avaliar("enderecamento", "o que é o ifconfig?")
        comandos = " ".join(r["comandos_autorizados"])
        self.assertIn("ip addr", comandos)
        self.assertNotIn("ifconfig", comandos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
