// O servidor interpreta os comandos, executa no PC escolhido, lê o estado real e concede o XP.
export function prepararComando(valor) {
  if (typeof valor !== 'string' || !valor.trim()) return { erro: 'Digite um comando.' }
  if (/[\r\n]/.test(valor)) return { erro: 'Digite um único comando por vez.' }
  const texto = valor.trim().replace(/^\$\s*/, '')
  if (texto.length > 100) return { erro: 'Comando longo demais para este laboratório.' }
  return { comando: texto }
}

// base: '/api/terminal' (Lab 4) ou '/api/lab5' e '/api/lab6' (setores, que também planejam).
export function criarClienteTerminal({ fetchImpl = globalThis.fetch, timeoutMs = 20000, base = '/api/terminal' } = {}) {
  async function chamar(acao, dados = {}, { signal } = {}) {
    let body
    if (acao !== 'status') {
      let payload = {}
      if (acao !== 'iniciar') {
        if (!Number.isInteger(dados.session_id) || dados.session_id <= 0 || !Number.isInteger(dados.revisao) || dados.revisao < 0) {
          throw new Error('Sessão ou revisão inválida. Atualize o estado do ambiente.')
        }
        payload = { session_id: dados.session_id, revisao: dados.revisao }
        if (acao === 'terminal') { payload.comando = dados.comando; payload.pc = dados.pc }
        if (acao === 'diagnosticar') payload.resposta = dados.resposta
        if (acao === 'planejar') payload.respostas = Object.fromEntries(Object.entries(dados.respostas || {}).map(([k, v]) => [k, String(v)]))
        if (acao === 'tutor') {
          payload.pergunta = dados.pergunta
          if (dados.rascunho) payload.rascunho = { comando: dados.rascunho.comando || '', pc: dados.rascunho.pc || '' }
        }
      }
      body = JSON.stringify(payload)
    }
    const controller = new AbortController()
    const cancelar = () => controller.abort(signal.reason)
    if (signal?.aborted) cancelar()
    else signal?.addEventListener('abort', cancelar, { once: true })
    const timer = setTimeout(() => controller.abort(new DOMException('Tempo de resposta esgotado. Atualize o estado antes de repetir.', 'TimeoutError')), timeoutMs)
    try {
      const resposta = await fetchImpl(`${base}/${acao}`, {
        method: acao === 'status' ? 'GET' : 'POST', credentials: 'same-origin', signal: controller.signal,
        ...(body === undefined ? {} : { body, headers: { 'Content-Type': 'application/json' } }),
      })
      const retorno = await resposta.json().catch(() => ({}))
      const quarentena = acao === 'status' && retorno.disponivel === false && retorno.ativo === true && retorno.preparacao_pendente === true && !retorno.conflito
      if (!resposta.ok || retorno.sucesso !== true || (retorno.disponivel !== true && !quarentena)) {
        const erro = new Error(resposta.status === 404 ? 'Ativação pendente: este laboratório ainda não está disponível no servidor.'
          : retorno.mensagem || (resposta.status === 401 ? 'Sua sessão de acesso expirou. Entre novamente.' : 'Não foi possível confirmar a operação. Atualize o estado antes de repetir.'))
        erro.status = resposta.status
        erro.dados = retorno
        throw erro
      }
      return retorno
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', cancelar)
    }
  }
  return Object.fromEntries(['status', 'iniciar', 'terminal', 'planejar', 'diagnosticar', 'tutor', 'validar', 'encerrar', 'estender']
    .map((acao) => [acao, (dados, opcoes) => chamar(acao, dados, opcoes)]))
}
