import test from 'node:test'
import assert from 'node:assert/strict'
import { BLOCOS, CLASSIFICAR, DEMANDAS, conferirEndereco, ehPrivado, hostsUteis, prefixoParaHosts, subdividir } from '../src/services/aulaPlano.js'

test('faixas privadas, inclusive nas bordas', () => {
  for (const ip of ['10.0.0.0', '10.255.255.255', '172.16.0.1', '172.31.255.255', '192.168.0.0', '192.168.255.255']) assert.ok(ehPrivado(ip), ip)
  for (const ip of ['9.255.255.255', '172.15.255.255', '172.32.0.0', '192.167.255.255', '192.169.0.0', '8.8.8.8']) assert.ok(!ehPrivado(ip), ip)
  assert.deepEqual(CLASSIFICAR.filter((c) => c.correta === 'privado').map((c) => c.ip), ['10.20.5.4', '192.168.1.10', '172.31.200.1'])
})

test('hosts úteis e prefixo pela demanda, contando o gateway', () => {
  assert.deepEqual([24, 26, 27, 28, 30].map(hostsUteis), [254, 62, 30, 14, 2])
  assert.equal(prefixoParaHosts(14), 28)
  assert.equal(prefixoParaHosts(15), 27)
  assert.deepEqual(DEMANDAS.map((d) => d.correta), [26, 25, 27, 28])
})

test('divisão de um /24 em quatro /26 sem sobreposição', () => {
  assert.deepEqual(BLOCOS.map((b) => [b.rede, b.broadcast]), [['192.168.50.0', '192.168.50.63'], ['192.168.50.64', '192.168.50.127'],
    ['192.168.50.128', '192.168.50.191'], ['192.168.50.192', '192.168.50.255']])
  assert.equal(subdividir('10.0.0.0/24', 27).length, 8)
  assert.ok(conferirEndereco(' 192.168.50.64 ', '192.168.50.64').ok)
  assert.match(conferirEndereco('192.168.50.65', '192.168.50.64').retorno, /64/)
  assert.match(conferirEndereco('192.168.50.126', '192.168.50.127', 'broadcast').retorno, /último/)
  assert.match(conferirEndereco('192.168.50', '192.168.50.0').retorno, /completo/)
})
