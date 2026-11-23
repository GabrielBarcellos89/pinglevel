import { test } from 'node:test'
import assert from 'node:assert/strict'
import { AULA_ID, VERSAO_RASCUNHO, criarClienteModelos, marcoLegado, lerRascunho } from '../src/services/progressoModelos.js'
import { PERGUNTAS_TESTE, RESPOSTAS_VAZIAS, SITUACOES_TRANSPORTE, avaliarTeste, embaralharOpcoes, limparErradas } from '../src/data/testeModelos.js'

test('mantém o identificador e os marcos legados sem alterar o backend', () => {
  assert.equal(AULA_ID, 'fundamentos-modelos-osi-tcpip')
  for (let i = 0; i <= 10; i++) assert.ok(marcoLegado(i) >= 0 && marcoLegado(i) <= 4)
  assert.equal(marcoLegado(10), 4)
  assert.throws(() => marcoLegado(11))
})
test('carrega identidade e conclusão existentes sem escrever', async () => {
  const calls = []
  const c = criarClienteModelos(async (url, init) => { calls.push([url, init]); return { ok: true, json: async () => ({ sucesso: true, progresso: { usuario_id: 7, aulas: [{ aula_id: AULA_ID, concluida: true, etapa_atual: 5 }] } }) } })
  const r = await c.carregar()
  assert.equal(r.usuarioId, 7)
  assert.equal(r.registro.concluida, true)
  assert.equal(calls[0][1].method, 'GET')
})
test('identidade ausente é erro, não aula nova silenciosa', async () => {
  const c = criarClienteModelos(async () => ({ ok: true, json: async () => ({ sucesso: true, progresso: { aulas: [] } }) }))
  await assert.rejects(c.carregar(), /identidade|inválido/)
})
test('revisão não gera progresso nem XP', async () => {
  let calls = 0
  const c = criarClienteModelos(async () => { calls++; throw new Error('Não deveria chamar') })
  await c.avancar(3, true)
  await assert.rejects(c.concluir(true), /revisão/i)
  assert.equal(calls, 0)
})
test('conclusão usa os endpoints existentes, marco final cinco e mesmo ID', async () => {
  const calls = []
  const c = criarClienteModelos(async (url, init) => { calls.push([url, JSON.parse(init.body)]); return { ok: true, json: async () => ({ sucesso: true, progresso: {}, xp_concedido: 100 }) } })
  await c.concluir(false)
  assert.deepEqual(calls, [['/api/progresso/aula', { aula_id: AULA_ID, etapa_atual: 5 }], ['/api/progresso/aula/concluir', { aula_id: AULA_ID }]])
})
test('erro de gravação é propagado e não chama conclusão', async () => {
  let calls = 0
  const c = criarClienteModelos(async () => { calls++; return { ok: false, json: async () => ({ sucesso: false, mensagem: 'Falha sintética ao salvar' }) } })
  await assert.rejects(c.concluir(false), /Falha sintética/)
  assert.equal(calls, 1)
})
test('rascunho inválido ou da versão 1 não inventa retomada', () => {
  assert.equal(lerRascunho('{'), null)
  assert.equal(lerRascunho(JSON.stringify({ versao: 0 })), null)
  assert.equal(lerRascunho(JSON.stringify({ versao: 2, cena: 99 })), null)
  const v1 = { versao: 1, cena: 5, passoRecebimento: 0, atividades: {}, pedidoPreparado: true, mostrarBytes: false,
    representacaoVista: true, resumoAberto: false, respostas: { grupo: '', ordem: '' } }
  assert.equal(lerRascunho(JSON.stringify(v1)), null)
})
const BASE = { versao: VERSAO_RASCUNHO, cena: 10, passoRecebimento: 0, atividades: { 5: true }, pedidoPreparado: true,
  mostrarBytes: false, representacaoVista: true, resumoAberto: true, testeAberto: true }
test('rascunho da versão 2 retoma a cena e as respostas do teste, completando as que faltam', () => {
  const lido = lerRascunho(JSON.stringify({ ...BASE, respostas: { acentos: '6', ordem: '1-7' } }))
  assert.equal(lido.cena, 10)
  assert.deepEqual(lido.respostas, { ...RESPOSTAS_VAZIAS, acentos: '6', ordem: '1-7' })
})
test('rascunho com resposta ou pergunta desconhecida é descartado', () => {
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, respostas: { acentos: '9' } })), null)
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, respostas: { destino: 'mac' } })), null)
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, testeAberto: undefined, respostas: {} })), null)
})
test('teste final: aprova só com tudo certo e "tentar de novo" apaga só as erradas', () => {
  const certas = Object.fromEntries(PERGUNTAS_TESTE.map((p) => [p.id, p.correta]))
  assert.equal(PERGUNTAS_TESTE.length, 7)
  assert.deepEqual(avaliarTeste(certas), { completo: true, aprovado: true, erradas: [] })
  const comErro = { ...certas, acentos: '1', sinal: '2' }
  assert.deepEqual(avaliarTeste(comErro).erradas, ['acentos', 'sinal'])
  assert.deepEqual(limparErradas(comErro), { ...certas, acentos: '', sinal: '' })
  assert.equal(avaliarTeste(RESPOSTAS_VAZIAS).completo, false)
  for (const p of PERGUNTAS_TESTE) assert.ok(p.opcoes.some(([v]) => v === p.correta), p.id)
})
test('teste final: as opções são embaralhadas sem perder nenhuma e a certa muda de lugar', () => {
  let semente = 7
  const aleatorio = () => { semente = (semente * 16807) % 2147483647; return semente / 2147483647 }
  for (const p of PERGUNTAS_TESTE) {
    const posicoes = new Set()
    for (let vez = 0; vez < 40; vez += 1) {
      const ordem = embaralharOpcoes(p.opcoes, aleatorio)
      assert.deepEqual([...ordem].sort(), [...p.opcoes].sort())
      posicoes.add(ordem.findIndex(([valor]) => valor === p.correta))
    }
    assert.equal(posicoes.size, p.opcoes.length, p.id)
  }
})
test('rascunho guarda a tela "TCP ou UDP?" e rascunhos sem ela continuam válidos', () => {
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, testeAberto: false, respostas: {} })).transporteAberto, false)
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, testeAberto: false, transporteAberto: true, respostas: {} })).transporteAberto, true)
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, testeAberto: true, respostas: {} })).transporteAberto, true)
  assert.equal(lerRascunho(JSON.stringify({ ...BASE, transporteAberto: 'sim', respostas: {} })), null)
})
test('TCP ou UDP: as quatro situações têm resposta TCP ou UDP e explicação', () => {
  assert.deepEqual(SITUACOES_TRANSPORTE.map((s) => s.correta), ['tcp', 'tcp', 'udp', 'udp'])
  for (const s of SITUACOES_TRANSPORTE) assert.ok(s.explicacao.length > 20, s.id)
})
