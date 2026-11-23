import test from 'node:test'
import assert from 'node:assert/strict'
import { CASOS_DNS, DORA, LEITURA_CONCESSAO, OBJETIVOS, PROBLEMAS, conferirComandoServicos } from '../src/services/aulaDhcpDns.js'

test('comandos de DHCP e DNS aceitam variações e explicam os erros comuns', () => {
  const porId = Object.fromEntries(OBJETIVOS.map((o) => [o.id, o]))
  assert.ok(conferirComandoServicos(porId.pedir, 'udhcpc -i eth0').ok)
  assert.ok(conferirComandoServicos(porId.resolv, '$ cat /etc/resolv.conf').ok)
  assert.ok(conferirComandoServicos(porId.consultar, 'dig intranet.empresa.local +short').ok)
  assert.ok(conferirComandoServicos(porId.ping, 'ping -c 2 intranet.empresa.local').ok)
  assert.ok(conferirComandoServicos(porId.pedir, 'dhclient eth0').ok)
  assert.match(conferirComandoServicos(porId.pedir, 'dhclient').retorno, /dhclient eth0/)
  assert.match(conferirComandoServicos(porId.pedir, 'udhcpc eth0').retorno, /-i/)
  assert.match(conferirComandoServicos(porId.consultar, 'nslookup intranet.empresa').retorno, /nome completo/)
})

test('cada pergunta tem a resposta entre as opções e cada ajuda tem pista que não é a resposta', () => {
  for (const q of [...PROBLEMAS, ...DORA, ...LEITURA_CONCESSAO, ...CASOS_DNS]) assert.ok(q.opcoes.some(([v]) => v === q.correta), q.id)
  for (const o of OBJETIVOS) {
    assert.match(o.ajuda.pista, /_{2,}/, o.id)
    assert.ok(!conferirComandoServicos(o, o.ajuda.pista).ok, o.id)
  }
  assert.deepEqual(CASOS_DNS.map((c) => c.correta), ['nome', 'servidor', 'rede'])
})
