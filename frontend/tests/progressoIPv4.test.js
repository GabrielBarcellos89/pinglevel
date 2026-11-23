import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { test } from 'node:test'

const caminho = new URL('../src/services/progressoIPv4.js', import.meta.url)

// Fixture sintética de contrato; não representa dados de alunos reais.
function estadoFixture() {
  return {
    aula_id: 'enderecamento-ipv4', modo: 'andamento', concluida: false,
    versao_estado: 1, versao_conteudo: 1, revisao: 4,
    etapa_visitada: 2, etapa_liberada: 2, etapa_retomada: 2,
    legado_sem_respostas: false,
    respostas: { previsao: 'destino', pratica: { rede: 'rede-10' }, interpretacao: '' },
    validacoes: { pratica: { status: 'pendente' }, interpretacao: { status: 'pendente' } },
  }
}

async function modulo() {
  assert.ok(existsSync(caminho), 'Falta o cliente de retomada IPv4')
  return import(caminho.href)
}

test('carrega etapa e respostas do contrato sem aprovar rascunho', async () => {
  const m = await modulo()
  const fixture = estadoFixture()
  const chamadas = []
  const cliente = m.criarClienteIPv4(async (url, opcoes) => {
    chamadas.push({ url, opcoes })
    return new Response(JSON.stringify({ sucesso: true, estado: fixture }))
  })
  const estado = await cliente.carregar()
  assert.deepEqual(estado, fixture)
  assert.equal(estado.validacoes.pratica.status, 'pendente')
  assert.equal(chamadas[0].url, '/api/progresso/aula/estado?aula_id=enderecamento-ipv4')
  assert.equal(chamadas[0].opcoes.credentials, 'same-origin')
})

test('salvamento usa revisão e envia somente respostas, sem aprovação ou usuário', async () => {
  const m = await modulo()
  assert.equal(typeof m.criarClienteIPv4().salvar, 'function', 'Falta salvar pelo contrato')
  const fixture = estadoFixture()
  const chamadas = []
  const cliente = m.criarClienteIPv4(async (url, opcoes) => {
    chamadas.push({ url, body: JSON.parse(opcoes.body) })
    return new Response(JSON.stringify({ sucesso: true, estado: { ...fixture, revisao: 5 } }))
  })
  assert.equal((await cliente.salvar(fixture, { pratica: { local: 'nao' } })).revisao, 5)
  assert.deepEqual(chamadas[0], {
    url: '/api/progresso/aula/estado',
    body: { aula_id: 'enderecamento-ipv4', revisao: 4, respostas: { pratica: { local: 'nao' } } },
  })
})

test('conflito e sessão expirada preservam o status para a interface', async () => {
  const m = await modulo()
  for (const status of [401, 403, 409, 500]) {
    const cliente = m.criarClienteIPv4(async () => new Response(
      JSON.stringify({ sucesso: false, mensagem: 'Falha sintética' }), { status },
    ))
    await assert.rejects(cliente.carregar(), (erro) => erro.status === status)
  }
})

test('estado ausente em resposta bem-sucedida não vira aula vazia', async () => {
  const m = await modulo()
  const cliente = m.criarClienteIPv4(async () => new Response(JSON.stringify({ sucesso: true })))
  await assert.rejects(cliente.carregar(), /estado.*inválido/i)
})


test('rascunho alterado invalida a conferência sem alterar o estado confirmado', async () => {
  const m = await modulo()
  assert.equal(typeof m.aplicarRascunho, 'function')
  const fixture = estadoFixture()
  fixture.validacoes.pratica = { status: 'aprovada' }
  const novo = m.aplicarRascunho(fixture, { pratica: { rede: 'host-34' } })
  assert.equal(novo.validacoes.pratica.status, 'pendente')
  assert.equal(fixture.validacoes.pratica.status, 'aprovada')
  assert.equal(fixture.respostas.pratica.rede, 'rede-10')
})

test('revisão só aprova após conferência explícita e nunca escreve no servidor', async () => {
  const m = await modulo()
  assert.equal(typeof m.conferirRevisao, 'function')
  const fixture = { ...estadoFixture(), modo: 'revisao', concluida: true }
  let escritas = 0
  const cliente = m.criarClienteIPv4(async () => { escritas += 1 })
  for (const acao of [() => cliente.salvar(fixture, {}), () => cliente.validar(fixture, 'pratica'),
    () => cliente.avancar(fixture, 1), () => cliente.concluir(fixture)]) {
    await assert.rejects(async () => acao(), /revisão/i)
  }
  assert.equal(escritas, 0)
  const respostas = { pratica: { rede: 'rede-10', local: 'sim', gateway: 'gateway' } }
  const rascunho = m.aplicarRascunho(fixture, respostas)
  assert.equal(rascunho.validacoes.pratica.status, 'pendente')
  assert.equal(m.conferirRevisao(rascunho, 'pratica').validacoes.pratica.status, 'aprovada')
  const incorreta = m.aplicarRascunho(rascunho, { pratica: { local: 'nao' } })
  assert.equal(m.conferirRevisao(incorreta, 'pratica').validacoes.pratica.status, 'incorreta')
  assert.throws(() => m.conferirRevisao(estadoFixture(), 'pratica'), /revisão/i)
})
