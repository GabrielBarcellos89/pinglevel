import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const nomes = ['PreviaEnderecoIPv4.css', 'ExploradorMascara.css']
test('conteúdo da prévia usa somente vermelho e neutros, sem azul ou âmbar', () => {
  for (const nome of nomes) {
    const css = readFileSync(new URL(`../src/pages/${nome}`, import.meta.url), 'utf8')
    for (const [hex] of css.matchAll(/#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\b/g)) {
      const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
      const neutro = Math.max(r, g, b) - Math.min(r, g, b) <= 5
      const vermelho = r === 240 && g === 32 && b === 53
      assert.ok(neutro || vermelho, `${nome}: cor fora da identidade preto/vermelho: ${hex}`)
    }
  }
})
test('rede vermelha e host neutro continuam distinguíveis por rótulos e bordas', () => {
  const a = readFileSync(new URL('../src/pages/PreviaEnderecoIPv4.css', import.meta.url), 'utf8')
  const b = readFileSync(new URL('../src/pages/ExploradorMascara.css', import.meta.url), 'utf8')
  assert.match(a, /--v4-rede:\s*var\(--vermelho\)/i)
  assert.match(a, /--v4-host:\s*#f1f1f1/i)
  assert.match(b, /\.bit-host\s*\{[^}]*dashed/s)
  assert.match(b, /\.bit-rede\s*\{[^}]*solid/s)
})
