import test from 'node:test'
import assert from 'node:assert/strict'

// Importação dinâmica torna o RED uma asserção da funcionalidade ausente.
test('cliente do gateway envia somente o contrato autorizado', async () => {
  const modulo = await import('../src/services/gatewayGuiado.js').catch(() => null)
  assert.ok(modulo, 'Falta o serviço guiado de gateway')
  const chamadas = []
  const api = modulo.criarClienteGateway({ fetchImpl: async (url, options) => {
    chamadas.push({ url, ...options }); return { ok: true, status: 200, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  await api.status()
  await api.iniciar({ uid: 55 })
  await api.aplicar({ session_id: 42, revisao: 0, gateway: '192.168.10.20', node_id: 4, concluido: true })
  assert.equal(chamadas[0].method, 'GET')
  assert.equal(chamadas[0].body, undefined)
  assert.equal(chamadas[0].url, '/api/gateway/status')
  assert.deepEqual(JSON.parse(chamadas[1].body), {})
  assert.deepEqual(JSON.parse(chamadas[2].body), { session_id: 42, revisao: 0, gateway: '192.168.10.20' })
  assert.equal(chamadas[2].credentials, 'same-origin')
  await assert.rejects(api.conferir({ session_id: '42', revisao: 0 }), /Sessão/)
})

test('validação contextual permite tentativa de host local sem entregar gabarito', async () => {
  const { validarGateway } = await import('../src/services/gatewayGuiado.js')
  assert.equal(typeof validarGateway, 'function', 'Falta validação contextual')
  const pc = { ip: '192.168.10.10', prefixo: 24 }
  for (const ip of ['', '01.2.3.4', '1.2.3.999', '1.2.3.4; id', '192.168.10.0', '192.168.10.255', '192.168.10.10', '192.168.20.1', '172.30.1.1']) assert.notEqual(validarGateway(ip, pc), '', ip)
  assert.equal(validarGateway('192.168.10.20', pc), '')
  assert.equal(validarGateway('192.168.10.1', pc), '')
  assert.notEqual(validarGateway('192.168.10.1', null), '')
})

for (const status of [400, 401, 404, 409, 503]) {
  test(`HTTP ${status} preserva estado contextual do servidor sem retry`, async () => {
    const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
    let chamadas = 0
    const dados = { sucesso: false, missao: { revisao: 9 }, mensagem: 'Recupere explicitamente.' }
    const api = criarClienteGateway({ fetchImpl: async () => {
      chamadas += 1
      return { ok: false, status, json: async () => dados }
    } })
    await assert.rejects(api.status(), (erro) => erro.status === status && erro.dados === dados)
    assert.equal(chamadas, 1)
  })
}

test('previsão e interpretação não enviam flags de evidência do cliente', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  const chamadas = []
  const api = criarClienteGateway({ fetchImpl: async (_, opcoes) => {
    chamadas.push(JSON.parse(opcoes.body)); return { ok: true, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  await api.prever({ session_id: 42, revisao: 1, local: 'nao', remota: 'sim', alcance: true })
  await api.interpretar({ session_id: 42, revisao: 2, resposta: 'gateway-sempre', correta: true, xp_concedido: 999 })
  assert.deepEqual(chamadas, [{ session_id: 42, revisao: 1, local: 'nao', remota: 'sim' }, { session_id: 42, revisao: 2, resposta: 'gateway-sempre' }])
})

test('timeout aborta a consulta, sem repetir escrita', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  let chamadas = 0
  const api = criarClienteGateway({ timeoutMs: 5, fetchImpl: (_, { signal }) => {
    chamadas += 1
    return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(signal.reason), { once: true }))
  } })
  await assert.rejects(api.iniciar(), { name: 'TimeoutError' })
  assert.equal(chamadas, 1)
})

test('cancelamento na desmontagem propaga AbortSignal', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  const controller = new AbortController()
  const api = criarClienteGateway({ fetchImpl: (_, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(signal.reason), { once: true })) })
  const pendente = api.status({}, { signal: controller.signal })
  controller.abort()
  await assert.rejects(pendente, { name: 'AbortError' })
})

test('JSON ilegível não é confirmação da operação', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  const api = criarClienteGateway({ fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw new Error('JSON inválido') } }) })
  await assert.rejects(api.status(), /Não foi possível confirmar/)
})


test('status de preparação pendente é legível sem habilitar operações', async()=>{
 const {criarClienteGateway}=await import('../src/services/gatewayGuiado.js')
 const dado={sucesso:true,disponivel:false,ativo:true,preparacao_pendente:true,conflito:null}
 const api=criarClienteGateway({fetchImpl:async()=>({ok:true,status:200,json:async()=>dado})})
 assert.equal(await api.status(),dado)
 dado.preparacao_pendente=false
 await assert.rejects(api.status())
})

test('fluxo local primeiro envia apenas previsão, classificação e tokens da sessão', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  const calls = []
  const api = criarClienteGateway({ fetchImpl: async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) })
    return { ok: true, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  const token = { session_id: 42, revisao: 3 }
  await api['testar-local']({ ...token, local: 'nao', node_id: 4, alcance: true })
  await api.classificar({ ...token, resposta: 'outra-rede', correta: true })
  await api.consultar({ ...token, comando: 'arbitrario' })
  await api['testar-remoto']({ ...token, destino: '8.8.8.8' })
  assert.deepEqual(calls, [
    { url: '/api/gateway/testar-local', payload: { ...token, local: 'nao' } },
    { url: '/api/gateway/classificar', payload: { ...token, resposta: 'outra-rede' } },
    { url: '/api/gateway/consultar', payload: token },
    { url: '/api/gateway/testar-remoto', payload: token },
  ])
})

test('ping digitado usa destinos conhecidos e não aceita opções, prompt ou comandos extras', async () => {
  const { validarComandoPing } = await import('../src/services/gatewayGuiado.js')
  const nos = [{ id: 2, ip: '192.168.10.20' }, { id: 4, ip: '192.168.20.10' }]
  assert.deepEqual(validarComandoPing('  ping\t192.168.10.20  ', nos), { comando: 'ping 192.168.10.20', destino: 2 })
  assert.deepEqual(validarComandoPing('ping 192.168.20.10', nos), { comando: 'ping 192.168.20.10', destino: 4 })
  for (const value of ['', null, 7, 'ls', 'ping', '$ ping 192.168.10.20', 'ping -c 2 192.168.10.20', 'ping 192.168.10.20; id', 'ping $(id)', 'ping 8.8.8.8', 'ping 192.168.10.20\n']) {
    assert.ok(validarComandoPing(value, nos).erro, String(value))
  }
})

test('endpoint do terminal envia entrada e previsão sem comando de shell, nós ou aprovação', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  const calls = []
  const api = criarClienteGateway({ fetchImpl: async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) })
    return { ok: true, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  await api.terminal({ session_id: 42, revisao: 1, comando: 'ping 192.168.10.20', local: 'nao', node_id: 5, concluido: true })
  await api.terminal({ session_id: 42, revisao: 2, comando: 'ping 192.168.20.10', shell: true })
  assert.deepEqual(calls, [
    { url: '/api/gateway/terminal', payload: { session_id: 42, revisao: 1, comando: 'ping 192.168.10.20', local: 'nao' } },
    { url: '/api/gateway/terminal', payload: { session_id: 42, revisao: 2, comando: 'ping 192.168.20.10' } },
  ])
})

test('pergunta ao Link não envia aprovação, nível de ajuda ou identidade do aluno', async () => {
  const { criarClienteGateway } = await import('../src/services/gatewayGuiado.js')
  let payload
  const api = criarClienteGateway({ fetchImpl: async (_, options) => {
    payload = JSON.parse(options.body)
    return { ok: true, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  await api.tutor({ session_id: 42, revisao: 2, pergunta: 'Como comparo as redes?', rascunho: { comando: 'ping', gateway: '', senha: 'ignorar' }, nivel: 4, uid: 7 })
  assert.deepEqual(payload, { session_id: 42, revisao: 2, pergunta: 'Como comparo as redes?', rascunho: { comando: 'ping', gateway: '' } })
})
