import unittest

from laboratorios.tutoria import avaliar_interacao


class TestTutorLinkV2(unittest.TestCase):
    def resposta(self, etapa, pergunta, historico=None):
        return avaliar_interacao(etapa, pergunta, historico or [])

    def test_primeira_pista_nao_entrega_hostname(self):
        r = self.resposta("identificacao", "como identifico o computador?")
        self.assertNotIn("`hostname`", r["resposta_controlada"])

    def test_name_nao_e_chamado_de_incompleto(self):
        r = self.resposta("identificacao", "name?")
        self.assertNotIn("incomplet", r["resposta_controlada"].lower())

    def test_host_name_corrige_espaco(self):
        r = self.resposta("identificacao", "host name?")
        self.assertIn("sem espaço", r["resposta_controlada"])

    def test_name_host_corrige_ordem(self):
        r = self.resposta("identificacao", "name host?")
        self.assertIn("ordem inversa", r["resposta_controlada"])

    def test_pedido_persistente_entrega_hostname(self):
        h = [
            {"etapa_id": "identificacao"},
            {"etapa_id": "identificacao"},
        ]
        r = self.resposta("identificacao", "qual a resposta?", h)
        self.assertIn("`hostname`", r["resposta_controlada"])

    def test_ip_antes_da_hora_reconduz(self):
        r = self.resposta("identificacao", "como consulto o ip?")
        self.assertEqual(r["classificacao"], "fora_da_etapa")
        self.assertNotIn("`ip", r["resposta_controlada"])

    def test_primeira_duvida_ip_nao_entrega_comando(self):
        r = self.resposta("enderecamento", "como consulto o ip?")
        self.assertNotIn("`ip", r["resposta_controlada"])

    def test_ifconfig_nao_e_recomendado(self):
        r = self.resposta("enderecamento", "ifconfig")
        self.assertIn("não faz parte", r["resposta_controlada"])

    def test_ping_conceitual_nao_entrega_sintaxe(self):
        r = self.resposta("conectividade", "o que faz o ping?")
        self.assertNotIn("-c", r["resposta_controlada"])

    def test_ping_correto_confirma_limite(self):
        r = self.resposta("conectividade", "ping -c 2 10.0.0.21")
        self.assertEqual(r["classificacao"], "comando_correto")
        self.assertIn("limita", r["resposta_controlada"])

    def test_fontes_sao_fixadas_por_etapa(self):
        r = self.resposta("identificacao", "ajuda")
        self.assertEqual(r["fonte_controlada"].count("página"), 2)

    def test_respostas_nao_mencionam_implementacao(self):
        proibidos = ("docker", "container", "nó docker")
        for etapa in ("identificacao", "enderecamento", "conectividade"):
            texto = self.resposta(etapa, "ajuda")["resposta_controlada"].lower()
            self.assertFalse(any(item in texto for item in proibidos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
