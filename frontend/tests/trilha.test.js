import test from 'node:test'
import assert from 'node:assert/strict'
import { PARADAS, montarTrilha, resumoInicio } from '../src/data/trilha.js'
import { ATIVIDADES } from '../src/data/catalogo.js'

test('toda atividade do catálogo é uma parada da trilha, na mesma ordem', () => {
  const daTrilha = PARADAS.filter((p) => p.atividade).map((p) => p.atividade)
  assert.deepEqual([...daTrilha].sort(), ATIVIDADES.map((a) => a.id).sort())
  assert.deepEqual(daTrilha, ATIVIDADES.map((a) => a.id))
  assert.equal(PARADAS.length, 22)
  assert.equal(PARADAS.at(-1).tipo, 'desafio')
})

test('estados: concluída, você está aqui, disponível e bloqueada', () => {
  const resumo = { aulas: [{ aula_id: 'fundamentos-aula-1', concluida: true }, { aula_id: 'fundamentos-modelos-osi-tcpip', concluida: false, percentual: 40 }], laboratorios: [] }
  const t = montarTrilha(resumo)
  assert.equal(t[0].estado, 'concluida')
  assert.equal(t[1].estado, 'andamento')
  assert.ok(t[1].atual && t.filter((p) => p.atual).length === 1)
  assert.equal(t[2].estado, 'disponivel')
  assert.equal(t[7].estado, 'disponivel')
  assert.equal(t[9].estado, 'disponivel')
  assert.equal(t[12].estado, 'disponivel')
  assert.equal(t[13].estado, 'disponivel')
  assert.equal(t[14].estado, 'disponivel')
  assert.equal(t.find((p) => p.titulo.startsWith('Lab 8')).estado, 'disponivel')
  assert.equal(t.at(-1).estado, 'disponivel')
  assert.ok(t.every((p) => p.estado !== 'bloqueada'))
})

test('sem progresso carregado, nenhuma parada aparece como concluída', () => {
  assert.ok(montarTrilha(null).every((p) => p.estado !== 'concluida'))
})

test('Início: próximo passo, total e módulos vêm da trilha', () => {
  const resumo = { aulas: [{ aula_id: 'fundamentos-aula-1', concluida: true }, { aula_id: 'fundamentos-modelos-osi-tcpip', concluida: true },
    { aula_id: 'enderecamento-ipv4', concluida: true }], laboratorios: [{ laboratorio_id: 'primeiro-contato', concluido: true }] }
  const r = resumoInicio(resumo)
  assert.equal(r.total, 22)
  assert.equal(r.concluidas, 4)
  assert.equal(r.proximo.atividade, 'fundamentos-ethernet-arp')
  assert.equal(r.proximo.numero, 5)
  assert.equal(r.proximo.acao, 'Começar aula')
  assert.deepEqual(r.modulos.map((m) => [m.numero, m.concluidas, m.total, m.estado]),
    [[1, 4, 10, 'atual'], [2, 0, 6, 'a-fazer'], [3, 0, 6, 'a-fazer']])
  assert.equal(r.modulos[0].caminho, '/modulos/fundamentos/ethernet-arp')
  assert.equal(r.modulos[1].caminho, '/modulos/planejamento/enderecamento')
})

test('Início: aula em andamento continua; trilha completa não tem próximo passo', () => {
  const andamento = resumoInicio({ aulas: [{ aula_id: 'fundamentos-aula-1', concluida: false, percentual: 30 }], laboratorios: [] })
  assert.equal(andamento.proximo.acao, 'Continuar aula')
  assert.equal(andamento.concluidas, 0)
  const tudo = { aulas: ATIVIDADES.filter((a) => a.tipo === 'aula').map((a) => ({ aula_id: a.id, concluida: true })),
    laboratorios: ATIVIDADES.filter((a) => a.tipo === 'laboratorio').map((a) => ({ laboratorio_id: a.id, concluido: true })) }
  const fim = resumoInicio(tudo)
  assert.equal(fim.proximo, null)
  assert.equal(fim.concluidas, 22)
  assert.ok(fim.modulos.every((m) => m.estado === 'concluido'))
})
