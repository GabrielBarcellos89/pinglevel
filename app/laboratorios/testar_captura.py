"""Regressões de integração sem CORE, SSH ou captura real."""
import unittest
from unittest.mock import Mock, patch
from laboratorios.gerenciador import GerenciadorLaboratorios, Laboratorio
from laboratorios.captura import interpretar_campos, CAMPOS, resolver_interface


class TestCaptura(unittest.TestCase):
    def setUp(self):
        self.g = GerenciadorLaboratorios()
        self.lab = Laboratorio(1, 'teste', 'primeiro-contato', 99, 1, 'rede',
                               {1: 'endereco'}, 1000, 9999999999, 180, 1)
        self.lab.aprendizagem["previsao"] = "resposta"
        self.g._laboratorios[1] = self.lab
        self.g.executar = Mock(return_value=(0, 'resultado'))
        self.g._core = Mock(return_value=Mock())
        self.mock = patch('laboratorios.gerenciador.Captura')
        self.classe = self.mock.start()
        self.addCleanup(self.mock.stop)
        self.captura = self.classe.return_value
        self.captura.finalizar.return_value = {'estado': 'concluida', 'eventos': []}

    def test_ping_retoma_resultado_e_libera_reserva(self):
        codigo, saida, dados = self.g.executar_observado(1, 1, 'ping -c 2 10.0.0.21')
        self.assertEqual((codigo, saida), (0, 'resultado'))
        self.assertEqual(self.lab.bastidores, dados)
        self.captura.iniciar.assert_called_once()
        self.assertFalse(self.g._capturas)
        self.assertFalse(self.g._execucoes)

    def test_hostname_nao_inicia_captura(self):
        self.assertIsNone(self.g.executar_observado(1, 1, 'hostname')[2])
        self.classe.assert_not_called()

    def test_falha_core_nao_impede_comando(self):
        self.g._core.side_effect = RuntimeError('indisponível')
        codigo, _, _ = self.g.executar_observado(1, 1, 'ping -c 1 10.0.0.21')
        self.assertEqual(codigo, 0)
        self.captura.finalizar.assert_called_with('Captura indisponível; o comando continua disponível.')

    def test_falha_ssh_finaliza_captura(self):
        self.g.executar.side_effect = RuntimeError('SSH')
        with self.assertRaises(RuntimeError):
            self.g.executar_observado(1, 1, 'ping -c 1 10.0.0.21')
        self.captura.finalizar.assert_called()
        self.assertFalse(self.g._execucoes)

    def test_concorrencia_rejeitada(self):
        self.g._execucoes.add(1)
        with self.assertRaises(ValueError):
            self.g.executar_observado(1, 1, 'hostname')
        self.g.executar.assert_not_called()

    def test_encerramento_cancela_antes_de_excluir_sessao(self):
        self.g._capturas[1] = self.captura
        self.g._salvar_estado = Mock()
        self.g._core.return_value.delete_session.side_effect = lambda _: self.captura.cancelar.assert_called_once()
        self.assertTrue(self.g.encerrar(1))

    def test_interface_ambigua_nao_consulta_host(self):
        core = Mock()
        core.get_node.return_value = (Mock(), [], [])
        with patch('laboratorios.captura.subprocess.check_output') as host:
            with self.assertRaises(RuntimeError):
                resolver_interface(core, 99, 1)
            host.assert_not_called()

    def test_campos_preservam_tipo_e_sequencia(self):
        campos = dict.fromkeys(CAMPOS, '')
        campos.update({'frame.number': '1', 'frame.time_relative': '0.01',
                       'ip.src': '10.0.0.20', 'ip.dst': '10.0.0.21',
                       'icmp.type': '8', 'icmp.seq': '2'})
        eventos = interpretar_campos('\t'.join(campos.values()))
        self.assertEqual(eventos[0]['tipo'], 'ICMP Echo Request')
        self.assertEqual(eventos[0]['campos']['icmp.seq'], '2')


if __name__ == '__main__':
    unittest.main()
