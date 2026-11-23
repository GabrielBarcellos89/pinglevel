import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { PARADAS } from '../src/data/trilha.js'

test('cada arte da trilha existe e não se repete', () => {
  const artes = PARADAS.filter((p) => p.arte).map((p) => p.arte)
  for (const a of artes) assert.ok(existsSync(new URL(`../src/assets/trilha/${a}.webp`, import.meta.url)), a)
  assert.equal(new Set(artes).size, artes.length)
  assert.equal(PARADAS.find((p) => p.atividade === 'enderecos-e-nomes').arte, '17-lab8-enderecos-nomes')
  assert.equal(PARADAS.find((p) => p.atividade === 'desafio-rede-da-empresa').arte, '20-lab10-desafio-final')
})
