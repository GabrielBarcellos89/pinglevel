import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { calcularRede, dividirRedeDidatica, calcularDivisao, avaliarLAN } from '../src/services/previaIPv4.js'

test('limites e capacidade conferem com Python ipaddress de /22 a /32, com exceções corretas de /31 e /32', () => {
  const casos = JSON.parse(readFileSync(new URL('./fixtures/previaIPv4_22_32.json', import.meta.url)))
  for (const caso of casos) {
    const real = calcularRede(caso.ip, caso.prefixo)
    for (const campo of ['rede', 'mascara', 'primeiro', 'ultimo', 'broadcast', 'total', 'hosts', 'hostValido']) {
      assert.equal(real[campo], caso[campo], `${caso.ip}/${caso.prefixo}: ${campo}`)
    }
  }
})

test('sub-redes cobrem a /24 sem sobreposição e mantêm seus próprios limites', () => {
  const r = dividirRedeDidatica(26)
  assert.deepEqual(r.map((n) => n.rede), ['192.168.10.0', '192.168.10.64', '192.168.10.128', '192.168.10.192'])
  assert.ok(r.every((n) => n.hosts === 62 && n.mascara === '255.255.255.192'))
  assert.equal(dividirRedeDidatica(25).length, 2)
})

test('simulação exige enlace, endereço configurado, hosts válidos e IPs únicos', () => {
  const base = { ipA: '192.168.10.10', ipB: '192.168.10.20', prefixo: 24, conectada: true }
  assert.equal(avaliarLAN({ ...base, conectada: false }).estado, 'sem-enlace')
  assert.equal(avaliarLAN({ ...base, ipB: '' }).estado, 'sem-configuracao')
  assert.equal(avaliarLAN({ ...base, ipB: '192.168.10.0' }).estado, 'endereco-reservado')
  assert.equal(avaliarLAN({ ...base, ipB: base.ipA }).estado, 'ip-duplicado')
  assert.equal(avaliarLAN({ ...base, ipB: '192.168.10.80', prefixo: 26 }).estado, 'redes-diferentes')
  assert.equal(avaliarLAN({ ...base, ipB: '192.168.10.80' }).estado, 'compativel')
  assert.equal(avaliarLAN(base).estado, 'compativel')
  assert.equal(avaliarLAN({ ...base, ipB: '999.168.10.20' }).estado, 'configuracao-invalida')
})

test('escopo do cálculo rejeita IPv4 inválido e prefixos não ensinados nesta amostra', () => {
  assert.throws(() => calcularRede('192.168.10.10', 21))
  assert.throws(() => calcularRede('999.168.10.10', 24))
  assert.throws(() => calcularRede('192.168.10.10', 33))
})

test('/31 é ponto a ponto e /32 é um único endereço, sem broadcast convencional', () => {
  const p2p = calcularRede('192.168.10.10', 31)
  assert.equal(p2p.hosts, 2)
  assert.equal(p2p.broadcast, null)
  assert.equal(p2p.primeiro, '192.168.10.10')
  assert.equal(p2p.ultimo, '192.168.10.11')
  const host = calcularRede('192.168.10.10', 32)
  assert.equal(host.hosts, 1)
  assert.equal(host.broadcast, null)
  assert.equal(host.bitsHost, 0)
  assert.equal(host.primeiro, host.ultimo)
  for (const prefixo of [31, 32]) assert.equal(avaliarLAN({ ipA: '192.168.10.10', ipB: '192.168.10.11', prefixo, conectada: true }).estado, 'uso-especial')
})

test('subdivisão cruza octetos e pagina /22 até /32 sem gerar mil cards', () => {
  const plano = calcularDivisao(32, 22)
  assert.equal(plano.redeBase.cidr, '192.168.8.0/22')
  assert.equal(plano.quantidade, 1024)
  const inicio = dividirRedeDidatica(32, { prefixoBase: 22 })
  assert.equal(inicio.length, 8)
  assert.equal(inicio[0].cidr, '192.168.8.0/32')
  const final = dividirRedeDidatica(32, { prefixoBase: 22, offset: 1016 })
  assert.equal(final.at(-1).cidr, '192.168.11.255/32')
  assert.throws(() => calcularDivisao(23, 24))
})

test('leitura de /8 e /16 para comparar com /24; divisão em sub-redes continua de /22 a /32', () => {
  const r16 = calcularRede('192.168.10.10', 16)
  assert.equal(r16.cidr, '192.168.0.0/16')
  assert.equal(r16.mascara, '255.255.0.0')
  assert.equal(r16.hosts, 65534)
  assert.equal(calcularRede('192.168.20.10', 16).rede, r16.rede)
  const r8 = calcularRede('192.168.10.10', 8)
  assert.equal(r8.cidr, '192.0.0.0/8')
  assert.equal(r8.broadcast, '192.255.255.255')
  assert.throws(() => calcularRede('192.168.10.10', 12))
  assert.throws(() => calcularDivisao(24, 16))
})
