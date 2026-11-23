import { test } from 'node:test'
import assert from 'node:assert/strict'
import { lerIntroducaoIPv4 } from '../src/services/retomadaIntroducaoIPv4.js'

const valido = { versao: 1, cena: 2, outroHost: false, prefixo: 26, ipB: '',
  lanPrefixo: 24, conectada: false, divisao: 25, prefixoBase: 24,
  paginaSubredes: 0, subredeAtiva: 0 }

test('retomada da introdução guarda somente escolhas visuais, não conclusões ou aprovações', () => {
  assert.deepEqual(lerIntroducaoIPv4(JSON.stringify({ ...valido, concluida: true, xp: 100 })), valido)
})
test('dados inválidos não geram prefixos ou índices de sub-redes inexistentes', () => {
  for (const alteracao of [{ versao: 2 }, { cena: 7 }, { cena: -1 }, { prefixo: 21 },
    { prefixo: '26' }, { divisao: 23 }, { paginaSubredes: 1 }, { subredeAtiva: 2 },
    { ipB: '8.8.8.8' }, { conectada: 'sim' }]) {
    assert.equal(lerIntroducaoIPv4(JSON.stringify({ ...valido, ...alteracao })), null)
  }
  for (const texto of [null, 'null', '[]', '{}', '{']) assert.equal(lerIntroducaoIPv4(texto), null)
})
test('paginação grande retoma somente páginas e blocos válidos', () => {
  const ultimo = { ...valido, prefixoBase: 22, divisao: 32, paginaSubredes: 127, subredeAtiva: 7 }
  assert.deepEqual(lerIntroducaoIPv4(JSON.stringify(ultimo)), ultimo)
  assert.equal(lerIntroducaoIPv4(JSON.stringify({ ...ultimo, paginaSubredes: 128 })), null)
})
