import unittest

from laboratorios.tutoria import avaliar_interacao


class TestTutoriaProgressiva(unittest.TestCase):
    def test_primeira_pergunta_comeca_no_nivel_um(self):
        resultado = avaliar_interacao("identificacao", "Como identifico o computador?", [])
        self.assertEqual(resultado["nivel"], 1)

    def test_host_name_e_tentativa_aproximada(self):
        resultado = avaliar_interacao("identificacao", "host name", [])
        self.assertEqual(resultado["classificacao"], "tentativa_aproximada")
        self.assertEqual(resultado["nivel"], 3)
        self.assertIn("sem espaço", resultado["detalhe"])

    def test_hostname_e_comando_correto(self):
        resultado = avaliar_interacao("identificacao", "hostname", [])
        self.assertEqual(resultado["classificacao"], "comando_correto")
        self.assertEqual(resultado["nivel"], 4)

    def test_name_em_ingles_reconhece_o_conceito(self):
        resultado = avaliar_interacao("identificacao", "name?", [])
        self.assertEqual(resultado["classificacao"], "conceito_correto")
        self.assertEqual(resultado["nivel"], 1)

    def test_pergunta_sobre_ip_nao_e_tentativa_de_comando(self):
        resultado = avaliar_interacao("enderecamento", "como consulto ip?", [])
        self.assertEqual(resultado["classificacao"], "conceito_correto")
        self.assertEqual(resultado["nivel"], 1)

    def test_pergunta_sobre_ping_nao_e_tentativa_de_comando(self):
        resultado = avaliar_interacao("conectividade", "o que é o ping?", [])
        self.assertEqual(resultado["classificacao"], "conceito_correto")
        self.assertEqual(resultado["nivel"], 1)

    def test_pedido_de_resposta_apos_duas_ajudas_entrega_comando(self):
        historico = [
            {"etapa_id": "identificacao", "pergunta": "como identifico?", "resposta": "pista"},
            {"etapa_id": "identificacao", "pergunta": "name?", "resposta": "pista 2"},
        ]
        resultado = avaliar_interacao("identificacao", "qual a resposta?", historico)
        self.assertEqual(resultado["classificacao"], "dificuldade_persistente")
        self.assertEqual(resultado["nivel"], 4)
        self.assertIn("hostname", resultado["detalhe"])

    def test_ajuda_avanca_com_historico_da_mesma_etapa(self):
        historico = [
            {"etapa_id": "identificacao", "pergunta": "ajuda", "resposta": "pista"},
            {"etapa_id": "identificacao", "pergunta": "não sei", "resposta": "pista 2"},
            {"etapa_id": "identificacao", "pergunta": "ainda não", "resposta": "pista 3"},
        ]
        resultado = avaliar_interacao("identificacao", "não consegui", historico)
        self.assertEqual(resultado["nivel"], 4)

    def test_historico_de_outra_etapa_nao_aumenta_nivel(self):
        historico = [
            {"etapa_id": "identificacao", "pergunta": "ajuda", "resposta": "pista"},
        ]
        resultado = avaliar_interacao("enderecamento", "Preciso de ajuda", historico)
        self.assertEqual(resultado["nivel"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
