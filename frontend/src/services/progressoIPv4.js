export const AULA_ID = 'enderecamento-ipv4'

export function verificarEstado(estado) {
  const indice = (valor) => Number.isInteger(valor) && valor >= 0 && valor <= 5
  const objeto = (valor) => valor && typeof valor === 'object' && !Array.isArray(valor)
  if (!objeto(estado) || estado.aula_id !== AULA_ID
    || !['andamento', 'revisao'].includes(estado.modo)
    || typeof estado.concluida !== 'boolean' || (estado.modo === 'revisao') !== estado.concluida
    || estado.versao_estado !== 1 || estado.versao_conteudo !== 1
    || !Number.isInteger(estado.revisao) || estado.revisao < 0
    || !indice(estado.etapa_retomada) || !indice(estado.etapa_visitada) || !indice(estado.etapa_liberada)
    || !objeto(estado.respostas) || !objeto(estado.respostas.pratica)
    || typeof estado.respostas.previsao !== 'string' || typeof estado.respostas.interpretacao !== 'string'
    || !['pendente', 'incorreta', 'aprovada'].includes(estado.validacoes?.pratica?.status)
    || !['pendente', 'incorreta', 'aprovada'].includes(estado.validacoes?.interpretacao?.status)) {
    throw new Error('Estado da aula inválido ou incompatível. Não foi carregada uma aula vazia.')
  }
  return estado
}

export function aplicarRascunho(estado, parcial) {
  const respostas = {
    ...estado.respostas, ...parcial,
    pratica: { ...estado.respostas.pratica, ...parcial.pratica },
  }
  const validacoes = { ...estado.validacoes }
  if (Object.keys(respostas.pratica).some((id) => respostas.pratica[id] !== estado.respostas.pratica[id])) {
    validacoes.pratica = { status: 'pendente' }
  }
  if (respostas.interpretacao !== estado.respostas.interpretacao) validacoes.interpretacao = { status: 'pendente' }
  return { ...estado, respostas, validacoes }
}

export function conferirRevisao(estado, atividade) {
  if (estado.modo !== 'revisao') throw new Error('Conferência local disponível somente em revisão.')
  const corretas = { rede: 'rede-10', local: 'sim', gateway: 'gateway' }
  let erros
  if (atividade === 'pratica') {
    if (Object.keys(corretas).some((id) => !estado.respostas.pratica[id])) {
      throw new Error('Responda todos os exercícios antes de conferir.')
    }
    erros = Object.keys(corretas).filter((id) => estado.respostas.pratica[id] !== corretas[id])
  } else if (atividade === 'interpretacao') {
    if (!estado.respostas.interpretacao) throw new Error('Responda à interpretação antes de conferir.')
    erros = estado.respostas.interpretacao === 'mac-gateway' ? [] : ['interpretacao']
  } else {
    throw new Error('Atividade inválida.')
  }
  return { ...estado, validacoes: {
    ...estado.validacoes, [atividade]: { status: erros.length ? 'incorreta' : 'aprovada', erros },
  } }
}

export function criarClienteIPv4(fetchImpl = globalThis.fetch) {
  async function solicitar(caminho, { signal, body } = {}) {
    const controller = new AbortController()
    const cancelar = () => controller.abort()
    signal?.addEventListener('abort', cancelar, { once: true })
    if (signal?.aborted) controller.abort()
    const timer = setTimeout(cancelar, 15_000)
    try {
      const resposta = await fetchImpl(caminho, {
        method: body ? 'POST' : 'GET', credentials: 'same-origin', signal: controller.signal,
        ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
      })
      let dados
      try {
        dados = await resposta.json()
      } catch {
        const erro = new Error('O serviço não retornou JSON válido. Tente novamente.')
        erro.status = resposta.status
        throw erro
      }
      if (!resposta.ok || !dados?.sucesso) {
        const erro = new Error(dados?.mensagem || 'Não foi possível recuperar ou salvar a aula.')
        erro.status = resposta.status
        throw erro
      }
      verificarEstado(dados.estado)
      return dados
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', cancelar)
    }
  }
  function escrever(rota, estado, campos, signal) {
    verificarEstado(estado)
    if (estado.modo === 'revisao') throw new Error('Revisão não altera o percurso concluído.')
    return solicitar(rota, { signal, body: { aula_id: AULA_ID, revisao: estado.revisao, ...campos } })
  }
  return {
    async carregar(signal) {
      const dados = await solicitar(`/api/progresso/aula/estado?aula_id=${AULA_ID}`, { signal })
      return dados.estado
    },
    async salvar(estado, respostas, etapaVisitada, signal) {
      const dados = await escrever('/api/progresso/aula/estado', estado, {
        respostas, ...(etapaVisitada === undefined ? {} : { etapa_visitada: etapaVisitada }),
      }, signal)
      return dados.estado
    },
    async validar(estado, atividade, signal) {
      const dados = await escrever('/api/progresso/aula/validar', estado, { atividade }, signal)
      return dados.estado
    },
    async avancar(estado, etapa, signal) {
      const dados = await escrever('/api/progresso/aula', estado, { etapa_atual: etapa }, signal)
      return dados.estado
    },
    async concluir(estado, signal) {
      return escrever('/api/progresso/aula/concluir', estado, {}, signal)
    },
  }
}
