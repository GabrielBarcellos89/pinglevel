// Dados demonstrativos para a prévia visual. Nenhum fetch, SSH, CORE ou gravação de XP.
const clone = (d) => structuredClone(d)
export function criarAPIDemonstracao() {
  const etapas = [
    { id: 'identificacao', titulo: 'Identifique o dispositivo', orientacao: 'Selecione o Computador 1 e descubra o nome do dispositivo.' },
    { id: 'enderecamento', titulo: 'Consulte o endereço IPv4', orientacao: 'Observe o endereço da interface eth0 e compare com a topologia.' },
    { id: 'conectividade', titulo: 'Teste a comunicação', orientacao: 'Faça sua previsão e observe um exemplo ilustrativo de ping.' },
  ]
  const feitos = new Set()
  let ativo = true
  let previsao = null
  let interpretacao = null
  let captura = null
  let prazo = Date.now() / 1000 + 900
  const missao = () => ({
    titulo: 'Primeiro Contato · prévia', descricao: 'Identifique os computadores, consulte o IPv4 e observe a comunicação local.', xp: 0,
    nos: [{ id: 1, nome: 'Computador 1', tipo: 'computador', ip: '10.0.0.20', prefixo: 24 },
      { id: 3, nome: 'Switch', tipo: 'switch' }, { id: 2, nome: 'Computador 2', tipo: 'computador', ip: '10.0.0.21', prefixo: 24 }],
    etapas: etapas.map((e) => ({ ...e, concluida: feitos.has(e.id) })),
    proxima_etapa: etapas.find((e) => !feitos.has(e.id))?.id || null,
    concluido: feitos.size === 3,
    aprendizagem: { previsao, interpretacao, interpretacao_correta: interpretacao === 'alcance',
      pode_prever: feitos.has('enderecamento'), pode_interpretar: feitos.has('conectividade'),
      perguntas: {
        previsao: { enunciado: 'Você espera comunicação entre estes dois PCs?', opcoes: [{ id: 'sim', texto: 'Sim, estão conectados à mesma rede.' }, { id: 'nao', texto: 'Não sei ainda; quero observar o teste.' }] },
        interpretacao: { enunciado: 'O que um ping entre os dois PCs pode demonstrar?', opcoes: [{ id: 'alcance', texto: 'Alcance entre esses computadores no teste.' }, { id: 'internet', texto: 'Acesso completo à internet.' }] },
      },
      feedback: interpretacao ? 'Exemplo demonstrativo: ping local não garante acesso à internet.' : '',
    },
  })
  const status = () => ({ sucesso: true, ativo, missao: missao(), bastidores: captura,
    laboratorio: ativo ? { session_id: 990001, laboratorio_id: 'primeiro-contato', prazo, agora: Date.now() / 1000, tempo_extensao: 180, pode_estender: true } : null })
  return async function apiLocal(caminho, opcoes = {}) {
    const d = opcoes.body ? JSON.parse(opcoes.body) : {}
    if (caminho === '/api/status') return clone(status())
    if (caminho === '/api/iniciar') { ativo = true; prazo = Date.now() / 1000 + 900; feitos.clear(); previsao = null; interpretacao = null; captura = null; return clone(status()) }
    if (caminho === '/api/encerrar') { ativo = false; return { ...clone(status()), mensagem: 'Demonstração encerrada. Nenhuma sessão CORE foi alterada.' } }
    if (caminho === '/api/estender') { prazo += 180; return clone(status()) }
    if (caminho === '/api/aprendizagem') {
      if (d.fase === 'previsao') previsao = d.resposta
      else interpretacao = d.resposta
      return clone(status())
    }
    if (caminho === '/api/tutor') return { sucesso: true, resposta: 'Esta é uma prévia de layout. Experimente hostname e ip addr show eth0, alterne o computador e teste o modo foco. Não há tutor ou comandos remotos nesta tela.', fonte: 'Demonstração local da interface' }
    if (caminho === '/api/validar') return { ...clone(status()), xp_concedido: 0, mensagem: 'Prévia visual concluída. Nenhum XP foi gravado.' }
    if (caminho === '/api/comando') {
      const cmd = String(d.comando || '').trim()
      const node = d.node_id === 2 ? 2 : 1
      let saida = 'Na prévia, use hostname, ip addr show eth0 ou ping -c 2 10.0.0.21.'
      if (cmd === 'hostname') { saida = `computador-${node}`; if (node === 1) feitos.add('identificacao') }
      else if (/^ip(?: -4)? addr show(?: dev)? eth0$/.test(cmd)) {
        saida = `eth0: interface de demonstração UP\n    inet 10.0.0.${node === 1 ? '20' : '21'}/24\n    Endereço ilustrativo; nenhum nó real foi consultado.`
        if (node === 1 && feitos.has('identificacao')) feitos.add('enderecamento')
      } else if (/^ping(?:\s|$)/.test(cmd)) {
        saida = 'Exemplo visual de comunicação local: 2 pedidos e 2 respostas.\nEste resultado é demonstrativo, não uma execução no CORE.'
        if (node === 1 && feitos.has('enderecamento')) feitos.add('conectividade')
        captura = { id: 'preview', estado: 'concluida', node_id: node, eventos: [
          { sequencia: 1, tipo: 'ARP Request', protocolo: 'ARP', origem: '10.0.0.20', destino: '10.0.0.21', tempo_relativo: 0, campos: {} },
          { sequencia: 2, tipo: 'ARP Reply', protocolo: 'ARP', origem: '10.0.0.21', destino: '10.0.0.20', tempo_relativo: .001, campos: {} },
          { sequencia: 3, tipo: 'ICMP Echo Request', protocolo: 'ICMP', origem: '10.0.0.20', destino: '10.0.0.21', tempo_relativo: .002, campos: {} },
          { sequencia: 4, tipo: 'ICMP Echo Reply', protocolo: 'ICMP', origem: '10.0.0.21', destino: '10.0.0.20', tempo_relativo: .003, campos: {} },
        ] }
      }
      return { ...clone(status()), codigo: 0, saida: `[DEMONSTRAÇÃO LOCAL — SEM CORE]\n${saida}` }
    }
    throw new Error('Operação não disponível na prévia visual.')
  }
}
