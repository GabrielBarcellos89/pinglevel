"""Mesmos gates de propriedade/confirmação do Lab2 aplicados ao Lab3."""
from laboratorios.tests import test_encerramento_confirmado as base

class TestEncerramentoGateway(base.TestEncerramentoConfirmado):
    def setUp(self):
        super().setUp()
        self.lab.laboratorio_id='saindo-da-rede-local'
