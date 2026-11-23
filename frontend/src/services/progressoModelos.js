import { RESPOSTAS_VAZIAS, respostaValida } from '../data/testeModelos.js'

export const AULA_ID = 'fundamentos-modelos-osi-tcpip'

// Versão 2 (30/10/2026): tela "Por que camadas?" antes da tabela (11 cenas) e teste final por situações.
// Rascunhos da versão 1 são ignorados: o aluno recomeça a aula 2, e o progresso da conta fica preservado.
export const VERSAO_RASCUNHO = 2
const ULTIMA_CENA = 10

export function marcoLegado(cena) {
  if (!Number.isInteger(cena) || cena < 0 || cena > ULTIMA_CENA) throw new Error('Cena inválida.')
  // O cadastro existente continua com seis marcos. O último é salvo só na conclusão.
  return Math.min(4, Math.floor(cena / 2))
}

export function lerRascunho(texto) {
  try {
    const s = JSON.parse(texto)
    if (!s || s.versao !== VERSAO_RASCUNHO || !Number.isInteger(s.cena) || s.cena < 0 || s.cena > ULTIMA_CENA
      || !Number.isInteger(s.passoRecebimento) || s.passoRecebimento < 0 || s.passoRecebimento > 6
      || !s.atividades || typeof s.atividades !== 'object' || Array.isArray(s.atividades)
      || Object.entries(s.atividades).some(([n, v]) => !['1', '2', '3', '4', '5'].includes(n) || typeof v !== 'boolean')
      || ['pedidoPreparado', 'mostrarBytes', 'representacaoVista', 'resumoAberto', 'testeAberto'].some((n) => typeof s[n] !== 'boolean')
      || ![undefined, true, false].includes(s.transporteAberto)
      || !s.respostas || typeof s.respostas !== 'object'
      || Object.entries(s.respostas).some(([id, valor]) => !respostaValida(id, valor))) return null
    return { versao: VERSAO_RASCUNHO, cena: s.cena, passoRecebimento: s.passoRecebimento, atividades: s.atividades,
      pedidoPreparado: s.pedidoPreparado, mostrarBytes: s.mostrarBytes, representacaoVista: s.representacaoVista,
      resumoAberto: s.resumoAberto, transporteAberto: s.transporteAberto === true || s.testeAberto, testeAberto: s.testeAberto, respostas: { ...RESPOSTAS_VAZIAS, ...s.respostas } }
  } catch { return null }
}

export function criarClienteModelos(fetchImpl = globalThis.fetch) {
  async function solicitar(url, body, signal) {
    const controller = new AbortController()
    const cancelar = () => controller.abort()
    signal?.addEventListener('abort', cancelar, { once: true })
    if (signal?.aborted) controller.abort()
    const timer = setTimeout(cancelar, 15_000)
    try {
      const r = await fetchImpl(url, { method: body ? 'POST' : 'GET', credentials: 'same-origin', signal: controller.signal,
        ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) })
      let d
      try { d = await r.json() } catch { throw new Error('O serviço não retornou JSON válido. Tente novamente.') }
      if (!r.ok || d?.sucesso !== true) throw new Error(d?.mensagem || 'Não foi possível recuperar ou salvar o progresso.')
      return d
    } finally { clearTimeout(timer); signal?.removeEventListener('abort', cancelar) }
  }
  return {
    async carregar(signal) {
      const d = await solicitar('/api/progresso/me', undefined, signal)
      if (!Number.isInteger(d.progresso?.usuario_id) || d.progresso.usuario_id <= 0 || !Array.isArray(d.progresso.aulas)) throw new Error('Resumo de progresso ou identidade inválido.')
      return { usuarioId: d.progresso.usuario_id, registro: d.progresso.aulas.find((a) => a.aula_id === AULA_ID) || null }
    },
    async avancar(cena, revisao) {
      if (revisao) return
      return solicitar('/api/progresso/aula', { aula_id: AULA_ID, etapa_atual: marcoLegado(cena) })
    },
    async concluir(revisao) {
      if (revisao) throw new Error('A revisão não altera a aula concluída.')
      await solicitar('/api/progresso/aula', { aula_id: AULA_ID, etapa_atual: 5 })
      return solicitar('/api/progresso/aula/concluir', { aula_id: AULA_ID })
    },
  }
}
