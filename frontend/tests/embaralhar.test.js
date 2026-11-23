import test from 'node:test'
import assert from 'node:assert/strict'
import { embaralhar } from '../src/services/embaralhar.js'

test('embaralhar mantém as mesmas opções e não altera a lista original', () => {
  const opcoes = [['a', 'A'], ['b', 'B'], ['c', 'C']]
  const sorteadas = embaralhar(opcoes)
  assert.equal(sorteadas.length, 3)
  assert.deepEqual([...sorteadas].sort(), [...opcoes].sort())
  assert.deepEqual(opcoes.map(([v]) => v), ['a', 'b', 'c'])
})

test('embaralhar põe a opção do meio em outras posições', () => {
  const opcoes = [['a'], ['b'], ['c']]
  assert.deepEqual(embaralhar(opcoes, () => 0).map(([v]) => v), ['b', 'c', 'a'])
  assert.deepEqual(embaralhar(opcoes, () => 0.99).map(([v]) => v), ['a', 'b', 'c'])
})
