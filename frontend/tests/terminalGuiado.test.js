import test from 'node:test'
import assert from 'node:assert/strict'
import { criarClienteTerminal, prepararComando } from '../src/services/terminalGuiado.js'
import { orientarTerminal } from '../src/services/orientacaoTerminal.js'
import { ATIVIDADES, situacaoAtividade } from '../src/data/catalogo.js'

function fetchFalso(resposta = { sucesso: true, disponivel: true }, status = 200) {
  const chamadas = []
  const fetchImpl = async (url, opcoes) => {
    chamadas.push({ url, ...opcoes, corpo: opcoes.body && JSON.parse(opcoes.body) })
    return { ok: status < 400, status, json: async () => resposta }
  }
  return { chamadas, api: criarClienteTerminal({ fetchImpl }) }
}

test('prepararComando aceita uma linha, tira o $ inicial e limita o tamanho', () => {
  assert.deepEqual(prepararComando('  $ ip a  '), { comando: 'ip a' })
  assert.ok(prepararComando('').erro)
  assert.ok(prepararComando('ip a\nreboot').erro)
  assert.ok(prepararComando('x'.repeat(101)).erro)
})

test('cliente envia somente os campos de cada ação para /api/terminal', async () => {
  const { chamadas, api } = fetchFalso()
  await api.status()
  await api.terminal({ session_id: 3, revisao: 2, comando: 'ip a', pc: 'financeiro', xp: 100 })
  await api.diagnosticar({ session_id: 3, revisao: 3, resposta: 'sem-ipv4' })
  await api.tutor({ session_id: 3, revisao: 4, pergunta: 'O que é eth0?', rascunho: { comando: 'ip a', pc: 'novo', gateway: 'x' } })
  assert.equal(chamadas[0].url, '/api/terminal/status')
  assert.equal(chamadas[0].method, 'GET')
  assert.deepEqual(chamadas[1].corpo, { session_id: 3, revisao: 2, comando: 'ip a', pc: 'financeiro' })
  assert.deepEqual(chamadas[2].corpo, { session_id: 3, revisao: 3, resposta: 'sem-ipv4' })
  assert.deepEqual(chamadas[3].corpo, { session_id: 3, revisao: 4, pergunta: 'O que é eth0?', rascunho: { comando: 'ip a', pc: 'novo' } })
})

test('cliente recusa sessão inválida e propaga mensagem e estado do servidor', async () => {
  await assert.rejects(fetchFalso().api.terminal({ session_id: 0, revisao: 1, comando: 'ip a' }), /Sessão ou revisão/)
  const { api } = fetchFalso({ sucesso: false, mensagem: 'Comando não disponível neste laboratório.', missao: { revisao: 1 } }, 400)
  await assert.rejects(api.terminal({ session_id: 3, revisao: 1, comando: 'ls' }), (erro) =>
    erro.status === 400 && /não disponível/.test(erro.message) && erro.dados.missao.revisao === 1)
})

const base = { ativo: true, etapa: 'chamado-1', pc: 'novo', abaAtual: 'novo', causaIdentificada: false, observou: false, enderecos: 0 }

test('orientação diminui a cada chamado', () => {
  assert.match(orientarTerminal(base).texto, /ip addr show/)
  assert.equal(orientarTerminal({ ...base, observou: true }).alvo, 'causa')
  const c1 = orientarTerminal({ ...base, causaIdentificada: true })
  assert.match(c1.texto, /ip addr add <endereço>\/<prefixo> dev eth0/)
  assert.match(orientarTerminal({ ...base, causaIdentificada: true, enderecos: 1 }).texto, /ip route add default via <gateway>/)
  const c2 = orientarTerminal({ ...base, etapa: 'chamado-2', pc: 'financeiro' })
  assert.match(c2.texto, /compare/i)
  assert.doesNotMatch(c2.texto, /ip route (add|del)|192\.168\.10\.1\b/)
  assert.equal(c2.etiqueta, 'CHAMADO 2 DE 3')
  const c3 = orientarTerminal({ ...base, etapa: 'chamado-3', pc: 'recepcao' })
  assert.doesNotMatch(c3.texto, /prefixo|ip addr|ip route|\/16|\/24/)
  const c3fix = orientarTerminal({ ...base, etapa: 'chamado-3', pc: 'recepcao', abaAtual: 'recepcao', causaIdentificada: true })
  assert.doesNotMatch(c3fix.texto, /ip addr|\/24/)
  const final = orientarTerminal({ ...base, etapa: 'comprovar' })
  assert.equal(final.alvo, 'concluir')
  assert.doesNotMatch(final.texto, /ip |ping/)
})

test('orientação leva à aba do chamado e reage a erros comuns sem dar a resposta', () => {
  const aba = orientarTerminal({ ...base, etapa: 'chamado-2', pc: 'financeiro', abaAtual: 'novo', causaIdentificada: true })
  assert.equal(aba.alvo, 'aba-financeiro')
  // Observar outro PC antes de identificar a causa é permitido: a orientação não manda trocar de aba.
  assert.equal(orientarTerminal({ ...base, etapa: 'chamado-2', pc: 'financeiro', abaAtual: 'novo' }).alvo, 'comando')
  assert.match(orientarTerminal({ ...base, causaIdentificada: true, enderecos: 2 }).texto, /ip addr del/)
  const falhou = orientarTerminal({ ...base, causaIdentificada: true, enderecos: 1, temRota: true, servidorFalhou: true })
  assert.doesNotMatch(falhou.texto, /192\.168\.10\.1\b/)
  assert.equal(orientarTerminal({ ativo: false }).alvo, 'iniciar')
  assert.equal(orientarTerminal({ ...base, recuperacao: true }).alvo, 'atualizar')
})

test('Lab 4 aparece no catálogo com rota própria', () => {
  const item = ATIVIDADES.find((a) => a.id === 'configure-pelo-terminal')
  assert.equal(item.caminho, '/laboratorios/configure-pelo-terminal')
  assert.equal(situacaoAtividade(item, { aulas: [], laboratorios: [{ laboratorio_id: item.id, concluido: true }] }).acao, 'Revisar')
})
