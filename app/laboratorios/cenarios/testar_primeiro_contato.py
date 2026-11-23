from __future__ import annotations

import unittest

from laboratorios.cenarios.primeiro_contato import (
    detectar_evidencias,
    montar_estado,
)


class TestPrimeiroContato(unittest.TestCase):
    def test_estado_inicial(self):
        estado = montar_estado()

        self.assertFalse(estado["concluido"])
        self.assertEqual(
            estado["proxima_etapa"],
            "identificacao",
        )
        self.assertEqual(estado["evidencias"], [])

    def test_hostname_no_computador_1(self):
        evidencias = detectar_evidencias(
            node_id=1,
            comando="hostname",
            codigo=0,
            saida="pl-s12-user1-docker1",
        )

        self.assertEqual(
            evidencias,
            {"identificacao"},
        )

    def test_hostname_no_computador_2_nao_avanca(self):
        evidencias = detectar_evidencias(
            node_id=2,
            comando="hostname",
            codigo=0,
            saida="pl-s12-user1-docker2",
        )

        self.assertEqual(evidencias, set())

    def test_comando_com_erro_nao_avanca(self):
        evidencias = detectar_evidencias(
            node_id=1,
            comando="hostname",
            codigo=1,
            saida="erro",
        )

        self.assertEqual(evidencias, set())

    def test_endereco_correto(self):
        saida = """
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>
    inet 10.0.0.20/24 scope global eth0
"""

        evidencias = detectar_evidencias(
            node_id=1,
            comando="ip addr show eth0",
            codigo=0,
            saida=saida,
        )

        self.assertEqual(
            evidencias,
            {"enderecamento"},
        )

    def test_endereco_esperado_ausente(self):
        evidencias = detectar_evidencias(
            node_id=1,
            comando="ip addr show",
            codigo=0,
            saida="inet 127.0.0.1/8 scope host lo",
        )

        self.assertEqual(evidencias, set())

    def test_ping_com_sucesso(self):
        saida = """
2 packets transmitted, 2 received, 0% packet loss
"""

        evidencias = detectar_evidencias(
            node_id=1,
            comando="ping -c 2 10.0.0.21",
            codigo=0,
            saida=saida,
        )

        self.assertEqual(
            evidencias,
            {"conectividade"},
        )

    def test_ping_com_perda_total_nao_avanca(self):
        saida = """
2 packets transmitted, 0 received, 100% packet loss
"""

        evidencias = detectar_evidencias(
            node_id=1,
            comando="ping -c 2 10.0.0.21",
            codigo=1,
            saida=saida,
        )

        self.assertEqual(evidencias, set())

    def test_ping_para_outro_destino_nao_avanca(self):
        saida = """
2 packets transmitted, 2 received, 0% packet loss
"""

        evidencias = detectar_evidencias(
            node_id=1,
            comando="ping -c 2 10.0.0.30",
            codigo=0,
            saida=saida,
        )

        self.assertEqual(evidencias, set())

    def test_estado_parcial(self):
        estado = montar_estado({
            "identificacao",
            "enderecamento",
        })

        self.assertFalse(estado["concluido"])
        self.assertEqual(
            estado["proxima_etapa"],
            "conectividade",
        )

    def test_estado_concluido(self):
        estado = montar_estado({
            "identificacao",
            "enderecamento",
            "conectividade",
        })

        self.assertTrue(estado["concluido"])
        self.assertIsNone(estado["proxima_etapa"])

        self.assertTrue(
            all(
                etapa["concluida"]
                for etapa in estado["etapas"]
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)