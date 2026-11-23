import test from 'node:test'
import assert from 'node:assert/strict'
import { OBJETIVOS, PCS, PASSOS_ARP, PERGUNTAS_MAC, PERGUNTAS_VLAN, QUADROS, conferirComandoLan } from '../src/services/aulaLan.js'

test('comandos da aula LAN aceitam variações e explicam o erro comum', () => {
  const porId = Object.fromEntries(OBJETIVOS.map((o) => [o.id, o]))
  assert.ok(conferirComandoLan(porId.arp, 'ip neigh show').ok)
  assert.ok(conferirComandoLan(porId.arp, '$ ip n').ok)
  assert.ok(conferirComandoLan(porId.fdb, 'bridge fdb show br br0').ok)
  assert.ok(conferirComandoLan(porId.vlans, 'bridge vlan').ok)
  assert.ok(conferirComandoLan(porId.add, 'bridge vlan add dev eth2 vid 20 untagged pvid').ok)
  assert.ok(conferirComandoLan(porId.del, 'bridge vlan del dev eth2 vid 1').ok)
  assert.match(conferirComandoLan(porId.add, 'bridge vlan add dev eth2 vid 20').retorno, /pvid untagged/)
  assert.match(conferirComandoLan(porId.del, 'bridge vlan del dev eth3 vid 1').retorno, /eth2/)
  assert.match(conferirComandoLan(porId.fdb, 'brctl showmacs br0').retorno, /começam com ip/)
  assert.match(conferirComandoLan(porId.del, 'bridge vlan del dev eth2 vid 20').retorno, /forma está certa.*de qual VLAN/)
  assert.match(conferirComandoLan(porId.add, 'bridge vlan add dev eth2 vid 10 pvid untagged').retorno, /forma está certa/)
})

test('ajuda de cada comando tem exemplo e pista que não é a resposta', () => {
  for (const o of OBJETIVOS) {
    assert.ok(o.ajuda.partes.length >= 2, o.id)
    assert.ok(o.ajuda.exemplo.comando, o.id)
    assert.ok(!conferirComandoLan(o, o.ajuda.exemplo.comando).ok || o.id === 'arp', o.id)
    // No switch, o exemplo usa o mesmo comando bridge da aula, não as ferramentas do livro (brctl, ip link ... vlan).
    if (o.id !== 'arp') assert.match(o.ajuda.exemplo.comando, /^bridge /, o.id)
    assert.match(o.ajuda.pista, /_{2,}/, o.id)
    assert.ok(!conferirComandoLan(o, o.ajuda.pista).ok, o.id)
  }
})

test('o cenário da aula não entrega a investigação do Lab 9', () => {
  const textos = JSON.stringify({ PCS, PASSOS_ARP, PERGUNTAS_MAC, PERGUNTAS_VLAN, QUADROS })
  assert.doesNotMatch(textos, /02:16:3e|192\.168\.30\./)
  for (const lista of [PASSOS_ARP, PERGUNTAS_MAC, PERGUNTAS_VLAN, QUADROS]) {
    for (const q of lista) assert.ok(q.opcoes.some(([v]) => v === q.correta), q.id)
  }
})
