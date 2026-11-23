import test from 'node:test'
import assert from 'node:assert/strict'
import { orientarGateway } from '../src/services/orientacaoGateway.js'

const ativo = { ativo: true }
const local = { ...ativo, localPronto: true }
const rede = { ...local, redePronta: true }
const gateway = { ...rede, mesmoGateway: true }
const observado = { ...gateway, depoisValido: true }
const casos = [
  ['abertura', {}, 'iniciar'],
  ['previsão antes do terminal', ativo, 'previsao'],
  ['digitar comando', { ...ativo, previsao: 'sim' }, 'comando'],
  ['executar entrada preenchida', { ...ativo, previsao: 'nao', comando: 'ping 192.168.10.20' }, 'executar'],
  ['corrigir erro de digitação', { ...ativo, previsao: 'sim', comando: 'pingg', erroTerminal: 'Comando inválido' }, 'comando'],
  ['comparar após ping local', local, 'classificacao'],
  ['confirmar comparação', { ...local, classificacao: 'outra-rede' }, 'comparar'],
  ['rever resposta incorreta', { ...local, classificacao: 'mesma-rede', classificacaoIncorreta: true }, 'classificacao'],
  ['inspecionar antes de configurar', rede, 'roteador'],
  ['configurar após inspecionar', { ...rede, observado: true }, 'gateway'],
  ['aplicar rascunho válido', { ...rede, gateway: '192.168.10.1' }, 'aplicar'],
  ['corrigir gateway inválido', { ...rede, gateway: '192.168.20.1', gatewayInvalido: true }, 'gateway'],
  ['digitar ping remoto', gateway, 'comando'],
  ['executar ping remoto', { ...gateway, comando: 'ping 192.168.20.10' }, 'executar'],
  ['falha remota pede revisão', { ...gateway, remotoFalhou: true }, 'gateway'],
  ['interpretar somente após evidências', observado, 'interpretacao'],
  ['conferir interpretação', { ...observado, resposta: 'gateway-remoto' }, 'interpretar'],
  ['corrigir interpretação', { ...observado, resposta: 'gateway-sempre', interpretacaoIncorreta: true }, 'interpretacao'],
  ['concluir após interpretação confirmada', { ...observado, interpretacaoCorreta: true }, 'concluir'],
  ['recuperação', { ...observado, recuperacao: true }, 'atualizar'],
  ['prazo expirado', { ...ativo, expirado: true }, 'atualizar'],
  ['preparação incompleta', { ...ativo, preparacaoPendente: true }, 'encerrar'],
  ['outro laboratório', { ...ativo, conflito: {} }, 'catalogo'],
  ['limpeza pendente', { registrada: true, pendente: true }, 'limpar'],
  ['conclusão persistida', { registrada: true }, 'catalogo'],
]
for (const [nome, estado, alvo] of casos) {
  test(`orientação: ${nome}`, () => {
    const antes = structuredClone(estado)
    const resultado = orientarGateway(estado)
    assert.equal(resultado.alvo, alvo)
    assert.ok(resultado.titulo && resultado.texto)
    assert.deepEqual(estado, antes, 'A orientação não modifica o estado nem aprova evidências')
  })
}

test('instrução de teste pede observação da topologia sem fornecer comando resolvido', () => {
  for (const estado of [{ ativo: true, previsao: 'sim' }, { ativo: true, localPronto: true, redePronta: true, mesmoGateway: true }]) {
    const instrucao = orientarGateway(estado)
    assert.match(instrucao.texto, /topologia/)
    assert.doesNotMatch(instrucao.texto, /ping\s+\d/)
  }
})
