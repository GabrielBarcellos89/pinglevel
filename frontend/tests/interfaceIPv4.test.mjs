import assert from 'node:assert/strict'
import { after, afterEach, before, beforeEach, test } from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { createServer } from 'vite'

// jsdom fica no scratch, não adiciona dependências ao projeto ou ao sistema.
const scratch = path.join(process.env.TMPDIR, 'retomada-ipv4-frontend')
const { JSDOM } = await import(pathToFileURL(path.join(scratch, 'dom-test/node_modules/jsdom/lib/api.js')).href)
const { api } = JSON.parse(await readFile(path.join(scratch, 'api-teste.json'), 'utf8'))
assert.match(api, /^http:\/\/127\.0\.0\.1:\d+$/)
const fetchReal = globalThis.fetch
let servidor, dom, root, React, act, createRoot, MemoryRouter, Routes, Route, Aula, AuthProvider, useAuth
let chamadas, interceptar, usuarioAtual

function TrocarUsuarioTeste() {
  const { entrar } = useAuth()
  return React.createElement('button', { id: 'trocar-usuario', onClick: () => entrar('', '') }, 'Trocar usuário sintético')
}

async function requisicao(rota, body, usuario = 'usuario-1') {
  const r = await fetchReal(new URL(rota, api), {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Cookie: usuario, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  const dados = await r.json()
  assert.equal(r.status, 200, JSON.stringify(dados))
  return dados
}

async function esperar(condicao) {
  for (let tentativa = 0; tentativa < 150; tentativa += 1) {
    if (condicao()) return
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 20)) })
  }
  assert.fail('Condição não atendida. DOM: ' + document.body.textContent)
}

async function montar() {
  await act(async () => {
    root = createRoot(document.getElementById('root'))
    root.render(React.createElement(React.StrictMode, {},
      React.createElement(MemoryRouter, { initialEntries: ['/modulos/enderecamento/ipv4'] },
        React.createElement(AuthProvider, {}, React.createElement(TrocarUsuarioTeste), React.createElement(Routes, {},
          React.createElement(Route, { path: '/modulos/enderecamento/ipv4', element: React.createElement(Aula) }),
          React.createElement(Route, { path: '/', element: React.createElement('h1', {}, 'Início de teste') }),
          React.createElement(Route, { path: '/login', element: React.createElement('h1', {}, 'Login de teste') }),
          React.createElement(Route, { path: '/alterar-senha', element: React.createElement('h1', {}, 'Verificação de acesso de teste') }),
        )),
      ),
    ))
  })
}

async function clicar(seletor) {
  const elemento = document.querySelector(seletor)
  assert.ok(elemento, 'Elemento ausente: ' + seletor)
  assert.ok(!elemento.disabled, 'Elemento bloqueado: ' + seletor)
  await act(async () => elemento.click())
  await esperar(() => !document.body.textContent.includes('Salvando…'))
}

async function selecionar(indice, valor) {
  const elemento = document.querySelectorAll('select')[indice]
  assert.ok(elemento && !elemento.disabled)
  await act(async () => {
    elemento.value = valor
    elemento.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
  })
  await esperar(() => !document.body.textContent.includes('Salvando…'))
}

async function remontar() {
  await act(async () => root.unmount())
  root = null
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
}

async function concluirIntroducao() {
  for (let i = 0; i < 7 && document.querySelector('.v4-cena'); i += 1) await clicar('.botao-avancar')
}

async function iniciarPraticaPelaInterface() {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await concluirIntroducao()
  await clicar('input[name="previsao-ipv4"]')
  await clicar('.botao-avancar')
  for (const [i, valor] of ['rede-10', 'sim', 'gateway'].entries()) await selecionar(i, valor)
}

async function semInterfaceConcluir() {
  const aula_id = 'enderecamento-ipv4'
  let estado = (await requisicao('/api/progresso/aula/estado?aula_id=' + aula_id)).estado
  async function enviar(rota, campos = {}) {
    const dados = await requisicao(rota, { aula_id, revisao: estado.revisao, ...campos })
    estado = dados.estado
    return dados
  }
  await enviar('/api/progresso/aula', { etapa_atual: 1 })
  await enviar('/api/progresso/aula/estado', { respostas: { previsao: 'gateway' } })
  await enviar('/api/progresso/aula', { etapa_atual: 2 })
  await enviar('/api/progresso/aula/estado', { respostas: { pratica: { rede: 'rede-10', local: 'sim', gateway: 'gateway' } } })
  await enviar('/api/progresso/aula/validar', { atividade: 'pratica' })
  for (const etapa_atual of [3, 4]) await enviar('/api/progresso/aula', { etapa_atual })
  await enviar('/api/progresso/aula/estado', { respostas: { interpretacao: 'mac-gateway' } })
  await enviar('/api/progresso/aula/validar', { atividade: 'interpretacao' })
  await enviar('/api/progresso/aula', { etapa_atual: 5 })
  await enviar('/api/progresso/aula/concluir')
}

before(async () => {
  servidor = await createServer({
    root: process.cwd(), cacheDir: path.join(scratch, 'ssr-cache'),
    server: { middlewareMode: true }, appType: 'custom',
  })
  // SSR transforma os módulos; a renderização e os eventos usam ReactDOM real.
  React = await import('react'); act = React.act
  ;({ createRoot } = await import('react-dom/client'))
  ;({ MemoryRouter, Routes, Route } = await import('react-router-dom'))
  ;({ default: Aula } = await servidor.ssrLoadModule('/src/pages/AulaEnderecoIPv4.jsx'))
  ;({ AuthProvider, useAuth } = await servidor.ssrLoadModule('/src/contexts/AuthContext.jsx'))
})

beforeEach(async () => {
  await requisicao('/__teste__/reset', {})
  dom = new JSDOM('<!doctype html><div id="root"></div>', { url: api + '/modulos/enderecamento/ipv4' })
  Object.assign(globalThis, { window: dom.window, document: dom.window.document,
    HTMLElement: dom.window.HTMLElement, Event: dom.window.Event, IS_REACT_ACT_ENVIRONMENT: true })
  chamadas = []; interceptar = null; usuarioAtual = 'usuario-1'
  globalThis.fetch = async (url, opcoes = {}) => {
    chamadas.push({ url, method: opcoes.method || 'GET' })
    if (interceptar) {
      const resposta = await interceptar(url, opcoes)
      if (resposta) return resposta
    }
    return fetchReal(new URL(url, api), { ...opcoes, headers: { ...opcoes.headers, Cookie: usuarioAtual } })
  }
})

afterEach(async () => {
  if (root) await act(async () => root.unmount())
  root = null
  dom.window.close()
  globalThis.fetch = fetchReal
})
after(async () => { await servidor?.close() })

test('a interface retoma a prática e respostas parciais salvas no backend', async () => {
  const aula_id = 'enderecamento-ipv4'
  let dados = await requisicao('/api/progresso/aula', { aula_id, revisao: 0, etapa_atual: 1 })
  dados = await requisicao('/api/progresso/aula/estado', { aula_id, revisao: dados.estado.revisao,
    respostas: { previsao: 'destino', pratica: { rede: 'rede-10' } } })
  await requisicao('/api/progresso/aula', { aula_id, revisao: dados.estado.revisao, etapa_atual: 2 })
  await montar()
  await esperar(() => document.querySelector('.aula-progresso-area span')?.textContent === 'Praticar')
  assert.equal(document.querySelectorAll('select')[0].value, 'rede-10')
  assert.equal(document.querySelectorAll('select')[1].value, '')
  assert.ok(document.querySelector('.botao-avancar').disabled)
  assert.ok(chamadas.some((r) => r.url.includes('/api/progresso/aula/estado?')))
})

test('fluxo pela interface salva, confere e conclui no backend', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await concluirIntroducao()
  await clicar('input[name="previsao-ipv4"]')
  await clicar('.botao-avancar')
  for (const [i, valor] of ['rede-10', 'sim', 'gateway'].entries()) await selecionar(i, valor)
  assert.ok(document.querySelector('.botao-avancar').disabled)
  await clicar('.modelos-validar')
  assert.ok(document.querySelector('.feedback-desafio.sucesso'))
  await clicar('.botao-avancar')
  await clicar('.botao-avancar')
  await clicar('input[name="interpretacao-ipv4"]')
  assert.ok(document.querySelector('.botao-avancar').disabled)
  await clicar('.modelos-validar')
  await clicar('.botao-avancar')
  assert.equal(document.querySelector('.aula-etiqueta').textContent, 'CONCLUIR · MÓDULO 1')
  await clicar('.botao-avancar')
  // A conclusão abre o momento de conquista com o XP vindo do servidor real; dali o aluno volta ao início.
  await esperar(() => document.querySelector('.conquista-card')?.textContent.includes('+100 XP'))
  await esperar(() => document.querySelector('.conquista-acoes .botao-interacao'))
  assert.match(document.querySelector('.conquista-acoes .botao-interacao').textContent, /^Seguir: /)
  await clicar('.conquista-acoes .botao-secundario')
  await esperar(() => document.body.textContent.includes('Início de teste'))
  const resumo = (await requisicao('/api/progresso/me')).progresso
  assert.ok(resumo.aulas[0].concluida)
  assert.equal(resumo.xp_total, 100)
})

test('revisão refeita não escreve nem altera conclusão ou XP', async () => {
  await semInterfaceConcluir()
  const antes = (await requisicao('/api/progresso/me')).progresso
  await montar()
  await esperar(() => document.body.textContent.includes('Revisão — aula já concluída'))
  await concluirIntroducao()
  await clicar('input[name="previsao-ipv4"]:last-child')
  await clicar('.botao-avancar')
  await selecionar(1, 'nao')
  await clicar('.modelos-validar')
  assert.ok(!document.querySelector('.feedback-desafio.sucesso'))
  // A navegação de revisão é livre, sem inventar aprovação da atividade errada.
  for (let i = 0; i < 3; i += 1) await clicar('.botao-avancar')
  assert.equal(document.querySelector('.botao-avancar').textContent.trim(), 'Finalizar revisão')
  await clicar('.botao-avancar')
  assert.equal(chamadas.filter((r) => r.method === 'POST').length, 0)
  assert.deepEqual((await requisicao('/api/progresso/me')).progresso, antes)
})

test('falha de carregamento não inicia uma aula vazia', async () => {
  interceptar = async (url) => url.includes('/api/progresso/aula/estado?')
    ? new Response(JSON.stringify({ sucesso: false, mensagem: 'Falha de consulta sintética' }), { status: 500 }) : null
  await montar()
  await esperar(() => Boolean(document.querySelector('[role="alert"]')))
  assert.equal(document.querySelector('.botao-avancar'), null)
  assert.equal(document.querySelector('select'), null)
  interceptar = null
  await clicar('.ipv4-estado-acoes button')
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
})

test('falha de salvamento mantém rascunho e bloqueia avanço até confirmação', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await concluirIntroducao()
  interceptar = async (url, opcoes) => url === '/api/progresso/aula/estado' && opcoes.method === 'POST'
    ? new Response(JSON.stringify({ sucesso: false, mensagem: 'Falha de gravação sintética' }), { status: 500 }) : null
  await clicar('input[name="previsao-ipv4"]')
  assert.ok(document.querySelector('input[name="previsao-ipv4"]').checked)
  assert.ok(document.querySelector('[role="alert"]'))
  assert.ok(document.querySelector('.botao-avancar').disabled)
  assert.equal((await requisicao('/api/progresso/aula/estado?aula_id=enderecamento-ipv4')).estado.respostas.previsao, '')
  interceptar = null
  await clicar('.ipv4-estado-acoes button')
  assert.equal(document.querySelector('[role="alert"]'), null)
  assert.equal((await requisicao('/api/progresso/aula/estado?aula_id=enderecamento-ipv4')).estado.respostas.previsao, 'gateway')
})

test('conflito com outra aba mantém rascunho e exige recuperação explícita', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await concluirIntroducao()
  const outraAba = (await requisicao('/api/progresso/aula/estado?aula_id=enderecamento-ipv4')).estado
  await requisicao('/api/progresso/aula/estado', {
    aula_id: 'enderecamento-ipv4', revisao: outraAba.revisao, respostas: { previsao: 'switch' },
  })
  await clicar('input[name="previsao-ipv4"]')
  assert.match(document.querySelector('[role="alert"]').textContent, /outra aba/i)
  assert.ok(document.querySelector('.botao-avancar').disabled)
  assert.ok(document.querySelectorAll('input[name="previsao-ipv4"]')[0].checked)
  assert.equal((await requisicao('/api/progresso/aula/estado?aula_id=enderecamento-ipv4')).estado.respostas.previsao, 'switch')
  let confirmacoes = 0
  window.confirm = () => { confirmacoes += 1; return false }
  await clicar('.ipv4-estado-acoes button')
  assert.ok(document.querySelector('[role="alert"]'))
  window.confirm = () => { confirmacoes += 1; return true }
  await clicar('.ipv4-estado-acoes button')
  await esperar(() => document.querySelectorAll('input[name="previsao-ipv4"]')[2]?.checked)
  assert.equal(confirmacoes, 2)
  assert.equal(document.querySelector('[role="alert"]'), null)
  assert.ok(!document.querySelector('.botao-avancar').disabled)
})

test('sessão expirada no salvamento bloqueia avanço e oferece novo acesso', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await concluirIntroducao()
  const antes = (await requisicao('/api/progresso/me')).progresso
  // O próprio Handler real produz 401 para uma identidade sintética ausente.
  interceptar = async (url, opcoes) => url === '/api/progresso/aula/estado' && opcoes.method === 'POST'
    ? fetchReal(new URL(url, api), { ...opcoes, headers: { ...opcoes.headers, Cookie: 'sessao-ausente' } }) : null
  await clicar('input[name="previsao-ipv4"]')
  assert.match(document.querySelector('[role="alert"]').textContent, /sessão expirou/i)
  assert.ok(document.querySelector('.botao-avancar').disabled)
  assert.deepEqual((await requisicao('/api/progresso/me')).progresso, antes)
  window.confirm = () => true
  await clicar('.ipv4-estado-acoes button:last-child')
  await esperar(() => document.body.textContent.includes('Login de teste'))
})

test('conferência recuperada não permanece aprovada após editar uma resposta', async () => {
  await iniciarPraticaPelaInterface()
  await clicar('.modelos-validar')
  await clicar('.botao-avancar')
  await clicar('.botao-voltar')
  await remontar()
  assert.equal(document.querySelector('.aula-progresso-area span').textContent, 'Praticar')
  assert.ok(document.querySelector('.feedback-desafio.sucesso'))
  assert.ok(!document.querySelector('.botao-avancar').disabled)
  await selecionar(1, 'nao')
  assert.equal(document.querySelector('.feedback-desafio'), null)
  assert.ok(document.querySelector('.botao-avancar').disabled)
  await remontar()
  assert.equal(document.querySelectorAll('select')[1].value, 'nao')
  assert.equal(document.querySelector('.feedback-desafio'), null)
  await clicar('.modelos-validar')
  assert.ok(document.querySelector('.feedback-desafio:not(.sucesso)'))
  await remontar()
  assert.ok(document.querySelector('.feedback-desafio:not(.sucesso)'))
  await selecionar(1, 'sim')
  assert.ok(document.querySelector('.botao-avancar').disabled)
  await clicar('.modelos-validar')
  assert.ok(!document.querySelector('.botao-avancar').disabled)
})

test('troca de usuário descarta consulta tardia do usuário anterior', async () => {
  const aula_id = 'enderecamento-ipv4'
  let dados = await requisicao('/api/progresso/aula', { aula_id, revisao: 0, etapa_atual: 1 })
  dados = await requisicao('/api/progresso/aula/estado', { aula_id, revisao: dados.estado.revisao,
    respostas: { previsao: 'destino', pratica: { rede: 'rede-10' } } })
  await requisicao('/api/progresso/aula', { aula_id, revisao: dados.estado.revisao, etapa_atual: 2 })
  let liberarAntiga, sinalAntigo
  interceptar = async (url, opcoes) => {
    if (url === '/api/auth/login') {
      usuarioAtual = 'usuario-2'
      // A troca no AuthProvider usa o usuário retornado pela API sintética real.
      return fetchReal(new URL('/api/auth/me', api), { headers: { Cookie: usuarioAtual } })
    }
    if (url.includes('/api/progresso/aula/estado?') && usuarioAtual === 'usuario-1') {
      const resposta = await fetchReal(new URL(url, api), { headers: { Cookie: 'usuario-1' } })
      sinalAntigo = opcoes.signal
      return new Promise((resolve) => { liberarAntiga = () => resolve(resposta) })
    }
    return null
  }
  await montar()
  await esperar(() => Boolean(liberarAntiga))
  await clicar('#trocar-usuario')
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  assert.ok(sinalAntigo.aborted)
  assert.ok(document.querySelector('.v4-cena[data-scene="0"]'))
  await act(async () => { liberarAntiga(); await new Promise((resolve) => setTimeout(resolve, 30)) })
  assert.ok(document.querySelector('.v4-cena[data-scene="0"]'))
  assert.equal(document.querySelector('select'), null)
  assert.equal((await requisicao('/api/progresso/me', undefined, 'usuario-2')).progresso.aulas.length, 0)
})

test('revisão legada sem respostas não atribui previsão nem aprovação', async () => {
  const r = await fetchReal(new URL('/__teste__/legado', api), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ concluida: true }),
  })
  assert.equal(r.status, 200, 'Falta preparar o registro legado no banco isolado')
  const antes = (await requisicao('/api/progresso/me')).progresso
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  assert.match(document.body.textContent, /respostas.*não foram armazenadas/i)
  await concluirIntroducao()
  assert.ok([...document.querySelectorAll('input[name="previsao-ipv4"]')].every((input) => !input.checked))
  await clicar('.botao-avancar')
  assert.ok([...document.querySelectorAll('select')].every((select) => !select.value))
  assert.equal(document.querySelector('.feedback-desafio'), null)
  await clicar('.botao-avancar')
  await clicar('.botao-avancar')
  assert.match(document.querySelector('.aula-conteudo').textContent, /Sua hipótese foi: não registrada/)
  assert.equal(chamadas.filter((chamada) => chamada.method === 'POST').length, 0)
  assert.deepEqual((await requisicao('/api/progresso/me')).progresso, antes)
})

test('a aula oficial abre a sequência aprovada sem finalizar aula ou gerar XP ao explorar', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  assert.equal(document.querySelector('h1').textContent, 'Como dois computadores entram na mesma rede?')
  assert.ok(!document.body.textContent.includes('Prévia em validação'))
  for (let cena = 0; cena < 6; cena += 1) await clicar('.botao-avancar')
  assert.equal(document.querySelector('h1').textContent, 'Da configuração ao planejamento')
  const antes = (await requisicao('/api/progresso/me')).progresso
  assert.equal(antes.xp_total, 0)
  await clicar('.botao-avancar')
  assert.ok(document.querySelector('input[name="previsao-ipv4"]'))
  assert.equal((await requisicao('/api/progresso/me')).progresso.xp_total, 0)
})

test('introdução nova retoma cena e prefixo no mesmo navegador sem gravar XP', async () => {
  await montar()
  await esperar(() => Boolean(document.querySelector('.botao-avancar')))
  await clicar('.botao-avancar')
  await clicar('.botao-avancar')
  await selecionar(0, '26')
  await remontar()
  assert.equal(document.querySelector('.v4-cena')?.dataset.scene, '2')
  assert.equal(document.querySelector('select').value, '26')
  assert.equal(chamadas.filter((r) => r.method === 'POST').length, 0)
  assert.equal((await requisicao('/api/progresso/me')).progresso.xp_total, 0)
})
