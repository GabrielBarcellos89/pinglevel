import test from 'node:test'
import assert from 'node:assert/strict'
import * as aula from '../src/services/aulaRoteamento.js'

const { OBJETIVOS, conferirRota } = aula

test('conferência das rotas estáticas aceita variações e explica erros comuns', () => {
  const [r1, r2, del] = OBJETIVOS
  assert.ok(conferirRota(r1, 'ip route add 192.168.20.0/24 via 10.0.0.2').ok)
  assert.ok(conferirRota(r1, '$ ip r add 192.168.20.0/24 via 10.0.0.2 dev eth1').ok)
  assert.ok(conferirRota(r2, 'ip route add 192.168.10.0/24 via 10.0.0.1').ok)
  assert.ok(conferirRota(del, 'ip route del 192.168.20.0/24').ok)
  assert.match(conferirRota(r1, 'ip route add 192.168.20.0/24 via 192.168.20.1').retorno, /vizinho/)
  assert.match(conferirRota(r1, 'ip route add 192.168.20.0 via 10.0.0.2').retorno, /prefixo/)
  assert.match(conferirRota(r1, 'route add -net 192.168.20.0').retorno, /começam com ip/)
})

test('toda pergunta da aula tem a resposta certa entre as opções, explicação e dica de erro', () => {
  const todas = [...aula.PERGUNTAS_CONHECE, ...aula.PERGUNTAS_SALTO, ...aula.PERGUNTAS_PERCURSO, ...aula.PERGUNTAS_VOLTA]
  assert.equal(new Set(todas.map((q) => q.id)).size, todas.length)
  for (const q of todas) {
    assert.ok(q.opcoes.some(([v]) => v === q.correta), q.id)
    assert.ok(q.certo && q.erro, q.id)
    assert.doesNotMatch(q.pergunta + q.certo + q.erro, /livro|Teste de carga/i, q.id)
  }
})

test('o percurso destaca linhas que existem e a volta para no R2', () => {
  for (const p of aula.PERCURSO) {
    if (p.linha === null) continue
    const linhas = p.no === 'r1' ? [...aula.TABELAS.r1, aula.ROTA_R1] : aula.TABELAS[p.no]
    assert.ok(linhas[p.linha], p.no)
  }
  assert.equal(aula.PERCURSO[1].linha, 2, 'no R1 o pacote usa a rota estática')
  assert.deepEqual(aula.VOLTA.map((v) => [v.no, v.ok]), [['pcb', true], ['r2', false]])
  assert.ok(!aula.TABELAS.r2.some((l) => l.linha.startsWith('192.168.10.')), 'o R2 começa sem rota para a Filial A')
})

test('todo comando das aulas tem ajuda do Link com o exemplo do livro e uma pista incompleta', async () => {
  const { OBJETIVOS: ferramentas, conferirComando } = await import('../src/services/aulaFerramentas.js')
  for (const o of [...ferramentas, ...OBJETIVOS]) {
    assert.ok(o.ajuda.partes.length >= 2, o.id)
    assert.match(o.ajuda.exemplo.rotulo, /^Exemplo 2\.\d+$/)
    assert.ok([12, 13].includes(o.ajuda.pagina))
    assert.match(o.ajuda.pista, /_{2,}/, o.id)
    assert.ok(!conferirComando(o, o.ajuda.pista).ok, `a pista de ${o.id} não pode ser a resposta`)
  }
})
