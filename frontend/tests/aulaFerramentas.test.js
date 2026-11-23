import test from 'node:test'
import assert from 'node:assert/strict'
import { CAUSAS_MENSAGEM, DESTINOS_TABELA, MENSAGENS, OBJETIVOS, OPCOES_INTERFACE, SITUACOES_INTERFACE, conferirComando } from '../src/services/aulaFerramentas.js'

const obj = (id) => OBJETIVOS.find((o) => o.id === id)

test('conferência aceita as formas do terminal do Lab 4 e recusa variações erradas', () => {
  assert.ok(conferirComando(obj('add-endereco'), 'ip addr add 192.168.10.30/24 dev eth0').ok)
  assert.ok(conferirComando(obj('add-endereco'), '$  ip address add 192.168.10.30/24   dev eth0').ok)
  assert.ok(conferirComando(obj('add-rota'), 'ip route add default via 192.168.10.1').ok)
  assert.ok(conferirComando(obj('add-rota'), 'ip r add default via 192.168.10.1 dev eth0').ok)
  assert.ok(conferirComando(obj('del-rota'), 'ip route del default').ok)
  assert.ok(conferirComando(obj('del-endereco'), 'ip addr del 192.168.10.30/24 dev eth0').ok)
  assert.match(conferirComando(obj('add-endereco'), 'ip addr add 192.168.10.30/24 dev eth1').retorno, /eth0/)
  assert.match(conferirComando(obj('add-endereco'), 'ifconfig eth0 192.168.10.30').retorno, /começam com ip/)
  assert.match(conferirComando(obj('add-rota'), 'ip route add 192.168.10.1').retorno, /ip route add default via/)
  assert.equal(conferirComando(obj('add-rota'), '').ok, false)
})

test('cada exercício tem resposta entre as opções', () => {
  const opcoesInterface = OPCOES_INTERFACE.map(([v]) => v)
  assert.ok(SITUACOES_INTERFACE.every((s) => opcoesInterface.includes(s.correta)))
  assert.ok(DESTINOS_TABELA.every((d) => ['local', 'padrao'].includes(d.correta)))
  const causas = CAUSAS_MENSAGEM.map(([v]) => v)
  assert.ok(MENSAGENS.every((m) => causas.includes(m.correta)))
  assert.equal(new Set(MENSAGENS.map((m) => m.correta)).size, MENSAGENS.length)
})
