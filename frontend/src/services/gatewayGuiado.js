// O servidor seleciona nós, comandos, evidências e concessão de XP.
export function validarGateway(valor, pc) {
  const ipv4 = (ip) => typeof ip === 'string' && /^(0|[1-9]\d{0,2})(\.(0|[1-9]\d{0,2})){3}$/.test(ip) && ip.split('.').every((p) => Number(p) <= 255)
  if (!ipv4(valor)) return 'Digite um IPv4 com quatro números de 0 a 255, sem espaços ou comandos.'
  if (!ipv4(pc?.ip) || !Number.isInteger(pc?.prefixo) || pc.prefixo < 1 || pc.prefixo > 30) return 'Aguarde a confirmação do endereço do Computador 1 pelo servidor.'
  if (valor.startsWith('172.30.')) return 'A rede de controle é reservada; use somente a LAN de dados.'
  const numero = (ip) => ip.split('.').reduce((n, p) => n * 256 + Number(p), 0)
  const tamanho = 2 ** (32 - pc.prefixo)
  const rede = Math.floor(numero(pc.ip) / tamanho) * tamanho
  const n = numero(valor)
  if (n < rede || n >= rede + tamanho) return 'O próximo salto precisa ser diretamente alcançável na LAN do Computador 1, não na outra LAN.'
  if (n === rede || n === rede + tamanho - 1) return 'Rede e broadcast não são endereços de um próximo salto.'
  if (valor === pc.ip) return 'O Computador 1 não pode usar a si próprio como saída.'
  return '' // Host local pode ser tentativa; só o servidor e os testes comprovam encaminhamento.
}

// Sintaxe intencionalmente pequena: a execução e as evidências continuam no servidor.
export function validarComandoPing(valor, nos = []) {
  if (typeof valor !== 'string' || valor.length > 80) return { erro: 'Digite ping seguido do endereço de destino.' }
  if (/[\r\n]/.test(valor)) return { erro: 'Digite um único comando por vez.' }
  if (valor.trimStart().startsWith('$')) return { erro: 'O $ é o indicador do terminal. Digite apenas ping e o endereço.' }
  const entrada = /^[ \t]*ping[ \t]+([0-9.]+)[ \t]*$/.exec(valor)
  if (!entrada) return { erro: 'Este terminal aceita uma ferramenta de teste e um endereço de destino. Consulte a topologia ou peça ajuda ao Link.' }
  const no = nos.find((n) => [2, 4].includes(n.id) && n.ip === entrada[1])
  if (!no) return { erro: 'Use o IP do PC Colega ou do Servidor mostrado na topologia.' }
  return { comando: `ping ${no.ip}`, destino: no.id }
}

export function criarClienteGateway({ fetchImpl = globalThis.fetch, timeoutMs = 20000 } = {}) {
  async function chamar(acao, dados = {}, { signal } = {}) {
    let body
    if (acao !== 'status') {
      let payload = {}
      if (acao !== 'iniciar') {
        if (!Number.isInteger(dados.session_id) || dados.session_id <= 0 || !Number.isInteger(dados.revisao) || dados.revisao < 0) {
          throw new Error('Sessão ou revisão inválida. Atualize o estado do ambiente.')
        }
        payload = { session_id: dados.session_id, revisao: dados.revisao }
        if (acao === 'aplicar') payload.gateway = dados.gateway
        if (acao === 'prever') Object.assign(payload, { local: dados.local, remota: dados.remota })
        if (acao === 'interpretar' || acao === 'classificar') payload.resposta = dados.resposta
        if (acao === 'testar-local') payload.local = dados.local
        if (acao === 'tutor') {
          payload.pergunta = dados.pergunta
          if (dados.rascunho) payload.rascunho = { comando: dados.rascunho.comando || '', gateway: dados.rascunho.gateway || '' }
        }
        if (acao === 'terminal') {
          payload.comando = dados.comando
          if (dados.local !== undefined) payload.local = dados.local
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
      const resposta = await fetchImpl(`/api/gateway/${acao}`, {
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
  return Object.fromEntries(['status', 'iniciar', 'tutor', 'terminal', 'consultar', 'testar-local', 'testar-remoto', 'classificar', 'prever', 'testar-antes', 'aplicar', 'conferir', 'testar-depois', 'interpretar', 'validar', 'encerrar', 'estender'].map((acao) => [acao, (dados, opcoes) => chamar(acao, dados, opcoes)]))
}
