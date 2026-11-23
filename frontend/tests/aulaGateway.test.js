import test from 'node:test'
import assert from 'node:assert/strict'
import { DESTINOS, GATEWAYS, PASSOS, PERGUNTAS, decidir } from '../src/services/aulaGateway.js'
import { ATIVIDADES } from '../src/data/catalogo.js'

test('decisão aplica /24 e compara com a rede do Atendimento', () => {
  assert.equal(decidir('192.168.10.20').caminho, 'direto')
  assert.equal(decidir('192.168.10.50').caminho, 'direto')
  assert.equal(decidir('192.168.20.10').caminho, 'gateway')
  assert.equal(decidir('8.8.8.8').redeDestino, '8.8.8.0')
  assert.deepEqual(DESTINOS.map((d) => decidir(d.ip).caminho), ['direto', 'gateway', 'direto', 'gateway'])
})

test('um único gateway correto: a interface do roteador na rede local', () => {
  const certos = GATEWAYS.filter((g) => g.correto)
  assert.deepEqual(certos.map((g) => g.ip), ['192.168.10.1'])
  assert.notEqual(GATEWAYS[0].correto, true)
})

test('ida e volta: o percurso sem gateway do servidor termina em falha', () => {
  assert.equal(PASSOS.normal.length, PASSOS.semGateway.length)
  assert.ok(PASSOS.semGateway.at(-1).falha && !PASSOS.normal.at(-1).falha)
  assert.deepEqual(PASSOS.normal.slice(0, 4), PASSOS.semGateway.slice(0, 4))
})

test('perguntas com uma resposta correta e ela não fica sempre na primeira posição', () => {
  for (const p of PERGUNTAS) assert.equal(p.opcoes.filter(([v]) => v === p.correta).length, 1)
  assert.ok(PERGUNTAS.some((p) => p.opcoes[0][0] !== p.correta))
  assert.ok(new Set(PERGUNTAS.map((p) => p.opcoes.findIndex(([v]) => v === p.correta))).size > 1)
})

test('aula aparece no catálogo antes do Lab 3', () => {
  const ids = ATIVIDADES.map((a) => a.id)
  assert.ok(ids.indexOf('fundamentos-gateway') < ids.indexOf('saindo-da-rede-local'))
  assert.equal(ATIVIDADES.find((a) => a.id === 'fundamentos-gateway').caminho, '/modulos/fundamentos/gateway')
})
