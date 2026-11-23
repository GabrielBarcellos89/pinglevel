import test from 'node:test'
import assert from 'node:assert/strict'
import { ALINHAMENTOS, BLOCOS_IGUAIS, ORDEM_CORRETA, PAR_SOBREPOSTO, PLANO, PREFIXO_IGUAL, conferirRede, planejar, sobrepoe } from '../src/services/aulaVlsm.js'

test('plano VLSM do maior para o menor, alinhado e sem sobreposição', () => {
  assert.deepEqual(PLANO.map((b) => `${b.rede}/${b.prefixo}`), ['192.168.60.0/25', '192.168.60.128/26', '192.168.60.192/27', '192.168.60.224/30'])
  assert.deepEqual(ORDEM_CORRETA, ['atendimento', 'vendas', 'financeiro', 'enlace'])
  for (let i = 0; i < PLANO.length; i += 1) for (let j = i + 1; j < PLANO.length; j += 1) assert.ok(!sobrepoe(PLANO[i], PLANO[j]))
  // Mesmo pedidos em ordem ruim saem alinhados: o planejador ordena antes de distribuir.
  const plano = planejar([{ id: 'p', prefixo: 30 }, { id: 'g', prefixo: 26 }], '10.0.0.0/24')
  assert.deepEqual(plano.map((b) => b.rede), ['10.0.0.0', '10.0.0.64'])
})

test('blocos iguais não atendem, alinhamento e o erro do plano do colega', () => {
  assert.equal(PREFIXO_IGUAL, 25)
  assert.equal(BLOCOS_IGUAIS, 2)
  assert.deepEqual(ALINHAMENTOS.map((a) => a.correta), ['sim', 'nao', 'sim', 'nao'])
  assert.deepEqual(PAR_SOBREPOSTO, ['b-c'])
})

test('conferência da rede explica alinhamento e ordem', () => {
  const vendas = PLANO[1]
  assert.ok(conferirRede('192.168.60.128', vendas).ok)
  assert.match(conferirRede('192.168.60.130', vendas).retorno, /múltiplos de 64/)
  assert.match(conferirRede('192.168.60.192', vendas).retorno, /primeiro endereço livre/)
  assert.match(conferirRede('abc', vendas).retorno, /completo/)
})
