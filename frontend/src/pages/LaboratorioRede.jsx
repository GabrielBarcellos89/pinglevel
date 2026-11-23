import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Computer, Network, Clock3, CheckCircle2, Ticket, ClipboardList, Server, Printer } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { criarClienteTerminal, prepararComando } from '../services/terminalGuiado'
import { LAB2, LAB5, LAB6, LAB7, LAB8, LAB9, LAB10, LAB_SUPORTE, comGuia } from '../services/labsSetores'
import { COMEMORACAO, POSES } from '../assets/mascote/poses'
import ConversaLink from '../components/laboratorio/ConversaLink'
import BastidoresTshark from '../components/laboratorio/BastidoresTshark'
import TempoEValidar from '../components/laboratorio/TempoEValidar'

const ARTES = Object.entries(import.meta.glob('../assets/trilha/*.webp', { eager: true, import: 'default' }))
const arteDoLab = (numero) => ARTES.find(([caminho]) => caminho.includes(`-lab${numero}-`))?.[1]
import EspacoLaboratorio from '../components/laboratorio/EspacoLaboratorio'
import IconeRoteador from '../components/laboratorio/IconeRoteador'
import './Laboratorio.css'
import './LaboratorioResponsivo.css'
import './LaboratorioGateway.css'
import './LaboratorioTerminal.css'
import './LaboratorioRede.css'

const CORES = ['#ff4f6d', '#2fbf71', '#4c9dff']

// Porta do switch (Lab 9): de acesso numa VLAN, ou o conjunto de VLANs quando a porta está no meio de uma mudança.
function descreverVlan(v) {
  if (!v) return '—'
  if (!v.membro.length) return 'sem VLAN'
  if (v.membro.length === 1 && v.pvid === v.membro[0] && v.untagged.includes(v.pvid)) return `VLAN ${v.pvid}`
  return `VLANs ${v.membro.join(', ')} (PVID ${v.pvid ?? 'nenhuma'})`
}

// Labs 5 a 10: setores ligados a um roteador (ou a um switch com VLANs, nos Labs 9 e 10). Mesma página; o que muda vem de `config` (services/labsSetores.js).
function SessaoRede({ config }) {
  const api = useMemo(() => criarClienteTerminal({ base: config.base }), [config.base])
  const [dados, setDados] = useState(null)
  const [operacao, setOperacao] = useState('status')
  const [aviso, setAviso] = useState('')
  const [recuperacao, setRecuperacao] = useState(false)
  const [prazo, setPrazo] = useState(null)
  const [agora, setAgora] = useState(Date.now)
  const [xp, setXp] = useState(null)
  const [foco, setFoco] = useState(true)
  // Abas de terminal: todas as do mapa, ou só as indicadas (teste de carga: só a T.I.; o resto se alcança por SSH).
  const terminais = config.terminais || config.abas
  const [aba, setAba] = useState(terminais[0])
  const [comando, setComando] = useState('')
  const [erroTerminal, setErroTerminal] = useState('')
  const [plano, setPlano] = useState({})
  const [retornoPlano, setRetornoPlano] = useState('')
  const [causa, setCausa] = useState('')
  const [retornoCausa, setRetornoCausa] = useState('')
  const [mensagensLink, setMensagensLink] = useState([])
  const [linkOcupado, setLinkOcupado] = useState(false)
  const [erroLink, setErroLink] = useState('')
  const [ajudaExpandida, setAjudaExpandida] = useState(false)
  const anteriores = useRef({ lista: [], posicao: -1 })
  const campo = useRef(null)
  const saida = useRef(null)
  const estadoAtual = useRef(null)
  const linkPendente = useRef(false)
  const vida = useRef(null)
  const sequencia = useRef(0)
  const trava = useRef(false)
  const missao = dados?.missao
  const registrada = dados?.conclusao?.registrada === true
  const pendente = registrada && dados.conclusao.encerramento_pendente !== false
  const sid = dados?.laboratorio?.session_id
  const revisao = missao?.revisao
  const ocupado = Boolean(operacao)
  const restantes = prazo === null ? null : Math.max(0, Math.ceil((prazo - agora) / 1000))
  const expirado = dados?.ativo && !registrada && (restantes === null || restantes <= 0)
  const ativo = dados?.ativo === true && dados?.disponivel === true && !dados.conflito && !registrada && !recuperacao && !expirado
  const livre = ativo && !ocupado
  const etapas = (missao?.etapas || []).map((e) => ({ ...e, titulo: config.titulosEtapas?.[e.id] || e.titulo, concluida: registrada || e.concluida }))
  const historico = Array.isArray(missao?.terminal) ? missao.terminal : []
  const estados = missao?.estados || {}
  const testes = missao?.testes || {}
  const nos = Object.fromEntries((missao?.nos || []).map((n) => [n.chave, n]))
  const setores = missao?.setores || {}
  const etapaAtual = missao?.proxima_etapa
  const chamado = missao?.chamado
  const chamados = missao?.chamados || []
  const linhas = historico.filter((h) => h.pc === aba)
  // Numa sessão SSH aberta, o terminal da aba fala com outro equipamento: o prompt e o estado mostram esse equipamento.
  const alvo = missao?.remoto || aba
  const pedindoSenha = Boolean(missao?.senha_pendente)
  const nomeAba = nos[alvo]?.nome || ''

  function receber(retorno) {
    if (retorno.missao?.id !== config.id || typeof retorno.ativo !== 'boolean' || !Number.isInteger(retorno.missao.revisao)
      || (retorno.ativo && (!Number.isInteger(retorno.laboratorio?.session_id) || retorno.laboratorio.session_id <= 0))) {
      throw new Error('O servidor não confirmou o estado deste laboratório.')
    }
    if (retorno.missao.proxima_etapa !== estadoAtual.current?.missao?.proxima_etapa) { setCausa(''); setRetornoCausa('') }
    estadoAtual.current = retorno
    setDados(retorno)
    setMensagensLink(Array.isArray(retorno.tutoria) ? retorno.tutoria : [])
    const lab = retorno.laboratorio
    const segundos = Number.isFinite(lab?.prazo) && Number.isFinite(lab?.agora) ? lab.prazo - lab.agora : lab?.segundos_restantes
    setPrazo(retorno.ativo && retorno.conclusao?.registrada !== true && Number.isFinite(segundos) ? Date.now() + Math.max(0, segundos) * 1000 : null)
    setAgora(Date.now())
  }

  useEffect(() => {
    const controller = new AbortController()
    vida.current = controller
    api.status({}, { signal: controller.signal }).then((retorno) => {
      if (!controller.signal.aborted) receber(retorno)
    }).catch((erro) => {
      if (!controller.signal.aborted) { setAviso(erro.message); setRecuperacao(true) }
    }).finally(() => { if (!controller.signal.aborted) setOperacao('') })
    return () => { controller.abort(); sequencia.current += 1 }
  }, [api])

  useEffect(() => {
    if (!dados?.ativo || registrada) return undefined
    const timer = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [dados?.ativo, registrada])

  useEffect(() => { saida.current?.scrollTo({ top: saida.current.scrollHeight }) }, [linhas.length, erroTerminal, aba])
  // Quando um chamado abre, a tela vai até ele e o destaca por um instante: o aluno não precisa procurá-lo.
  const chamadoAberto = missao?.chamado?.etapa === missao?.proxima_etapa ? missao?.proxima_etapa : null
  useEffect(() => {
    if (!chamadoAberto) return undefined
    const quadro = document.querySelector('.lr-lab .lt-chamado[data-chamado]')
    if (!quadro) return undefined
    quadro.scrollIntoView({ block: 'start', behavior: 'smooth' })
    quadro.classList.add('lr-chegou')
    const tempo = setTimeout(() => quadro.classList.remove('lr-chegou'), 2400)
    return () => clearTimeout(tempo)
  }, [chamadoAberto])

  async function executar(acao, extras = {}) {
    if (trava.current || vida.current?.signal.aborted) return
    if (acao === 'iniciar' && (!dados?.disponivel || dados.ativo || dados.conflito || recuperacao || pendente)) return
    if (!['status', 'iniciar', 'encerrar'].includes(acao) && !livre) return
    if (acao === 'encerrar' && (!dados?.ativo || dados.conflito || recuperacao)) return
    trava.current = true
    const versao = ++sequencia.current
    setOperacao(acao)
    setAviso('')
    const payload = ['status', 'iniciar'].includes(acao) ? {} : { session_id: sid, revisao, ...extras }
    try {
      const retorno = await api[acao](payload, { signal: vida.current?.signal })
      if (vida.current?.signal.aborted || versao !== sequencia.current) return
      receber(retorno)
      setRecuperacao(false)
      if (retorno.conflito) { setAviso('Outro laboratório está em uso. Nenhuma sessão foi substituída.'); return }
      if (acao === 'iniciar') { if (!retorno.ativo) throw new Error('O servidor não confirmou um ambiente ativo.'); setXp(null) }
      if (acao === 'terminal') { setComando(''); setErroTerminal('') }
      if (acao === 'planejar') setRetornoPlano(retorno.mensagem || '')
      if (acao === 'diagnosticar') setRetornoCausa(retorno.mensagem || '')
      if (acao === 'validar') {
        if (!retorno.conclusao?.registrada || !retorno.missao.concluido) throw new Error('A conclusão ainda não foi confirmada pelo servidor.')
        setXp(Number.isFinite(retorno.xp_concedido) ? retorno.xp_concedido : null)
      }
      if (acao === 'encerrar') {
        if (retorno.ativo || retorno.conclusao?.encerramento_pendente) throw new Error('A limpeza ainda não foi confirmada. Atualize o estado antes de tentar novamente.')
        setAviso('Encerramento confirmado pelo servidor.')
      }
      if (acao === 'status') setAviso('Estado atualizado.')
    } catch (erro) {
      if (vida.current?.signal.aborted || versao !== sequencia.current) return
      if (erro.dados?.missao) {
        try { receber(erro.dados) } catch { /* Incompleto: manter controles bloqueados. */ }
      }
      // Comando recusado ou pré-requisito faltando: resposta normal do laboratório, não falha do ambiente.
      if (erro.status === 400 && ['terminal', 'planejar', 'diagnosticar', 'validar'].includes(acao)) {
        if (acao === 'terminal') setErroTerminal(erro.message)
        else if (acao === 'planejar') setRetornoPlano(erro.message)
        else if (acao === 'diagnosticar') setRetornoCausa(erro.message)
        else setAviso(erro.message)
        return
      }
      setRecuperacao(true)
      setAviso(`${erro.message} Use “Atualizar estado” antes de repetir.`)
    } finally {
      trava.current = false
      if (!vida.current?.signal.aborted) setOperacao('')
      if (acao === 'terminal') requestAnimationFrame(() => campo.current?.focus())
    }
  }

  function enviarComando(evento) {
    evento.preventDefault()
    if (!livre) return
    const entrada = prepararComando(comando)
    if (entrada.erro) { setErroTerminal(entrada.erro); return }
    const memoria = anteriores.current
    // A senha do ssh nunca entra na memória das setas.
    if (!pedindoSenha) memoria.lista = [...memoria.lista.filter((c) => c !== entrada.comando), entrada.comando].slice(-20)
    memoria.posicao = -1
    executar('terminal', { comando: entrada.comando, pc: aba })
  }

  function navegarHistorico(evento) {
    const memoria = anteriores.current
    if (pedindoSenha || !['ArrowUp', 'ArrowDown'].includes(evento.key) || !memoria.lista.length) return
    evento.preventDefault()
    const total = memoria.lista.length
    const posicao = evento.key === 'ArrowUp' ? (memoria.posicao < 0 ? total - 1 : Math.max(0, memoria.posicao - 1))
      : (memoria.posicao < 0 ? -1 : memoria.posicao + 1)
    memoria.posicao = posicao >= total ? -1 : posicao
    setComando(memoria.posicao < 0 ? '' : memoria.lista[memoria.posicao])
  }

  function trocarAba(no) {
    if (!terminais.includes(no)) {
      setErroTerminal(`Neste teste, tudo é feito a partir do terminal da ${nos[terminais[0]]?.nome}. Para chegar ao ${nos[no]?.nome}, use ssh.`)
      return
    }
    setAba(no)
    setErroTerminal('')
    requestAnimationFrame(() => campo.current?.focus())
  }

  async function perguntarAoLink(pergunta) {
    if (!ativo || linkPendente.current) return false
    const contexto = { session_id: sid, revisao }
    linkPendente.current = true
    setLinkOcupado(true)
    setErroLink('')
    try {
      const retorno = await api.tutor({ ...contexto, pergunta, rascunho: { comando, pc: aba } }, { signal: vida.current?.signal })
      if (vida.current?.signal.aborted) return false
      const atual = estadoAtual.current
      if (atual?.laboratorio?.session_id !== contexto.session_id || atual?.missao?.revisao !== contexto.revisao) {
        setErroLink('O estado mudou durante a resposta. Faça sua pergunta novamente.')
        return false
      }
      if (!retorno.tutor?.resposta || !['referencias', 'contingencia'].includes(retorno.tutor.modo)) throw new Error('O Link não confirmou uma resposta válida.')
      setMensagensLink(retorno.tutoria)
      return true
    } catch (erro) {
      if (!vida.current?.signal.aborted) setErroLink(erro.status === 409 ? 'O estado mudou. Faça sua pergunta novamente.' : erro.message)
      return false
    } finally {
      linkPendente.current = false
      if (!vida.current?.signal.aborted) setLinkOcupado(false)
    }
  }

  const tempo = restantes === null ? '--:--' : `${String(Math.floor(restantes / 60)).padStart(2, '0')}:${String(restantes % 60).padStart(2, '0')}`
  const atual = Math.max(0, etapas.findIndex((e) => !e.concluida))
  const orientacao = comGuia(config, config.orientar({
    ocupado, recuperacao, expirado, preparacaoPendente: dados?.preparacao_pendente, conflito: dados?.conflito,
    registrada, pendente, ativo: dados?.ativo, etapa: etapaAtual, indice: atual, abaAtual: aba, estados, historico, remoto: missao?.remoto,
    plano: missao?.plano, testes: missao?.testes, senhaPendente: Boolean(missao?.senha_pendente),
    causaIdentificada: Boolean(chamado?.correta),
    observou: Boolean(chamado) && historico.some((h) => h.pc === (chamado.observar_no || chamado.no)
      && (chamados.length ? [chamado.observar] : config.observarChamado || ['ver-enderecos', 'ver-rotas']).includes(h.tipo)),
    progresso: chamado?.progresso || {}, suspeitas: chamado?.suspeitas || [],
    chamadoNo: chamado?.no, nomeChamado: nos[chamado?.no]?.nome,
  }), etapaAtual)
  // Labs 8 e 10 (vários chamados): o que cada chamado exige, do que o servidor confirmou.
  const andamento = chamado?.progresso || {}
  const observouChamado = Boolean(chamado) && historico.some((h) => h.pc === (chamado.observar_no || chamado.no) && h.tipo === chamado.observar)
  const feitos = [andamento.causa || observouChamado, andamento.causa, andamento.configuracao, andamento.configuracao && andamento.teste].map(Boolean)
  const primeiraPendente = feitos.indexOf(false)
  const passosChamado = (config.passosChamado ? config.passosChamado(chamado, nos) : [])
    .map((texto, i) => [texto, feitos[i] ? 'feito' : i === primeiraPendente ? 'atual' : 'falta'])
  const resolvidos = chamados.filter((c) => c.situacao === 'resolvido')
  const naFila = chamados.filter((c) => c.situacao === 'fila')
  const esperado = (alvo) => orientacao.alvo === alvo ? 'gw-proxima-acao' : ''
  const irParaAcao = () => requestAnimationFrame(() => {
    const elemento = document.querySelector(`.lr-lab [data-acao="${orientacao.alvo}"]`)
    if (!elemento) return
    elemento.scrollIntoView({ block: 'center', behavior: 'auto' })
    elemento.focus({ preventScroll: true })
  })

  const resumo = (no) => {
    const e = estados[no]
    if (!e?.lido) return 'não lido'
    if (config.descobrirEnderecos && !historico.some((h) => h.pc === no && h.tipo !== 'ping')) return 'endereço: descubra no terminal'
    const enderecos = Object.values(e.interfaces || {}).flat()
    return enderecos.length ? enderecos.join(' · ') : 'sem endereço'
  }
  const setoresLista = Object.entries(setores)
  const metade = Math.ceil(setoresLista.length / 2)
  const zona = ([chave, s], i) => <div key={chave} className="lt-zona lr-zona" style={{ '--cor-setor': CORES[i] }}>
    <span>{s.nome}{s.rede ? ` · ${s.rede}/${s.prefixo}` : ' · rede a planejar'}</span>
    <div className="lt-pcs">{config.abas.filter((no) => nos[no]?.setor === chave).map((no) =>
      <button key={no} type="button" className={`lt-pc ${aba === no ? 'selecionado' : ''}`} disabled={!dados?.ativo}
        onClick={() => trocarAba(no)} aria-label={`${nos[no].nome}: ${resumo(no)}`}>
        {nos[no].tipo === 'servidor' ? <Server size={16} aria-hidden="true" /> : nos[no].tipo === 'impressora' ? <Printer size={16} aria-hidden="true" /> : <Computer size={16} aria-hidden="true" />}<strong>{nos[no].nome}</strong><small>{resumo(no)}</small>
        <i aria-hidden="true">{config.rotuloPc ? config.rotuloPc(no, missao) : estados[no]?.rota_padrao ? `gw ${estados[no].rota_padrao}` : 'sem rota padrão'}</i>
      </button>)}</div>
    {!config.switchCentral && <><span className="lt-cabo" aria-hidden="true" />
      <div className="lt-equip" role="img" aria-label={`Switch ${s.nome}`}><Network size={16} aria-hidden="true" /><strong>Switch</strong></div></>}
  </div>
  const roteadores = config.roteadores || ['roteador']
  const botaoRoteador = (r) => <button key={r} type="button" className={`lt-equip lt-roteador lr-roteador ${aba === r ? 'selecionado' : ''}`} disabled={!dados?.ativo}
    onClick={() => trocarAba(r)} aria-label={`${nos[r]?.nome}: ${resumo(r)}`}>
    {nos[r]?.tipo === 'switch' ? <Network size={18} aria-hidden="true" /> : nos[r]?.tipo === 'servidor' ? <Server size={18} aria-hidden="true" />
      : <IconeRoteador aria-hidden="true" />}<strong>{nos[r]?.nome}</strong>
    {(nos[r]?.interfaces || []).map((i) => <small key={i}><b>{i}</b> {nos[r]?.tipo === 'switch'
      ? `${descreverVlan(estados[r]?.vlans?.[i])}${missao?.portas?.[i] ? ` · ${missao.portas[i]}` : ''}`
      : estados[r]?.interfaces?.[i]?.join(', ') || '—'}</small>)}
    {nos[r]?.rotas === true && <small className="lr-rotas"><b>rota padrão</b> {estados[r]?.rota_padrao ? `via ${estados[r].rota_padrao}` : 'nenhuma'}</small>}
    {nos[r]?.rotas && nos[r].rotas !== true && <small className="lr-rotas"><b>rotas</b> {estados[r]?.rotas?.join('; ') || 'só as redes conectadas'}</small>}
  </button>
  // Teste de carga: diagrama de rede. Prédio A em cima, o roteador no meio e o Prédio B embaixo; em cada prédio o
  // switch liga os três equipamentos, lado a lado.
  const icone = (no) => nos[no]?.tipo === 'impressora' ? Printer : Computer
  const predio = (entrada, posicao) => {
    if (!entrada) return null
    const [chave, setor] = entrada
    const equipamentos = config.abas.filter((no) => nos[no]?.setor === chave).map((no) => {
      const Icone = icone(no)
      const rota = estados[no]?.rota_padrao
      const gwErrado = nos[no]?.tipo === 'pc' && rota && rota !== setor.gateway
      const papel = no === terminais[0] ? 'voce' : no === missao?.remoto ? 'remoto' : ''
      return <li key={no} className={`tq-equip ${papel} ${gwErrado ? 'gw-errado' : ''}`}
        aria-label={`${nos[no]?.nome}: ${nos[no]?.ip}${nos[no]?.tipo === 'pc' ? `, gateway ${rota || 'nenhum'}` : ''}${gwErrado ? ' (errado)' : ''}`}>
        <span className="tq-icone" aria-hidden="true"><Icone size={22} />{gwErrado && <b>!</b>}</span>
        <strong>{nos[no]?.nome}</strong>
        <code>{nos[no]?.ip}</code>
        {nos[no]?.tipo === 'pc' && <small><span className="tq-gw-longo">gw {rota || '—'}</span><span className="tq-gw-curto">gw {rota ? `.${rota.split('.').pop()}` : '—'}</span></small>}
        {papel === 'voce' && <em>você está aqui</em>}{papel === 'remoto' && <em>SSH aberto</em>}
      </li>
    })
    return <div key={chave} className={`tq-predio tq-${posicao} tq-predio-${chave}`}>
      <p className="tq-predio-nome"><strong>{setor.nome}</strong> <code>{setor.rede}/{setor.prefixo}</code></p>
      <div className="tq-switch" role="img" aria-label={`Switch do ${setor.nome}`}><Network size={18} aria-hidden="true" /> Switch</div>
      <ul className="tq-fila">{equipamentos}</ul>
    </div>
  }
  const topologiaPredios = <section className="gw-painel gw-topologia lt-topologia tq-topologia" aria-label="Topologia dos dois prédios">
    <h2 className="gw-etiqueta">TOPOLOGIA · DOIS PRÉDIOS LIGADOS POR UM ROTEADOR</h2>
    <div className="tq-diagrama">
      {predio(setoresLista[0], 'cima')}
      <div className="tq-roteador" role="img" aria-label={`Roteador: eth0 ${estados.roteador?.interfaces?.eth0?.[0] || '192.168.10.1/24'}, eth1 ${estados.roteador?.interfaces?.eth1?.[0] || '192.168.20.1/24'}`}>
        <small className="tq-porta"><b>eth0</b> {estados.roteador?.interfaces?.eth0?.[0] || '192.168.10.1/24'}</small>
        <span className="tq-icone-roteador"><IconeRoteador aria-hidden="true" /></span>
        <strong>Roteador</strong>
        <small className="tq-porta"><b>eth1</b> {estados.roteador?.interfaces?.eth1?.[0] || '192.168.20.1/24'}</small>
      </div>
      {predio(setoresLista[1], 'baixo')}
    </div>
  </section>
  // Labs 8 e 9: diagrama como o do Teste de carga. Um setor em cima, o switch no meio, o outro setor embaixo.
  // No Lab 8 o switch mostra a VLAN de cada porta; no Lab 9 o roteador fica ao lado do switch. Clicar num equipamento
  // abre o terminal dele; o que o Agora faça espera fica marcado em vermelho, como a aba.
  const octetosDaRede = Math.floor(Number(String(missao?.rede || '').split('/')[1] || 24) / 8)
  const prefixoRede = String(missao?.rede || '').split('/')[0].split('.').slice(0, octetosDaRede).join('.') + '.'
  const curto = (ip) => String(ip || '').split('/')[0].startsWith(prefixoRede) ? `.${String(ip).split('/')[0].slice(prefixoRede.length)}` : String(ip || '').split('/')[0]
  const iconeLan = (no) => no === 'impressora' ? Printer : nos[no]?.tipo === 'servidor' ? Server : Computer
  const grupoLan = (entrada, posicao, cor) => {
    if (!entrada) return null
    const [chave, setor] = entrada
    const equipamentos = config.abas.filter((no) => nos[no]?.setor === chave)
    return <div key={chave} className={`tq-predio tq-${posicao}`} style={{ '--cor': cor, '--n': equipamentos.length }}>
      <p className="tq-predio-nome"><strong>{setor.nome}</strong></p>
      <ul className="tq-fila">{equipamentos.map((no) => {
        const aguardando = Boolean(esperado(`aba-${no}`))
        const Icone = iconeLan(no)
        // Labs 9 e 10: gateway (só no 10) e DNS de cada PC, sem a parte da rede que está no título, como no Teste de carga.
        const dns = estados[no]?.dns?.length ? `DNS ${estados[no].dns.map(curto).join(', ')}` : 'sem DNS'
        const gw = config.mostrarGateway && nos[no]?.tipo === 'pc' ? `gw ${estados[no]?.rota_padrao ? curto(estados[no].rota_padrao) : '—'}` : ''
        const rotulo = config.mostrarDns ? (nos[no]?.tipo === 'pc' ? dns : '')
          : config.rotuloPc ? config.rotuloPc(no, missao) : ''
        const ip = (estados[no]?.interfaces?.eth0?.[0] || '').split('/')[0]
        // Labs 9 e 10: quem abriu o chamado atual e quem tem chamado na fila (validação de 22/11/2026).
        const deste = chamados.find((c) => c.no === no && c.situacao !== 'resolvido')
        const etiqueta = registrada || !deste ? '' : deste.situacao === 'atual' ? 'abriu o chamado' : `chamado ${chamados.indexOf(deste) + 1} · fila`
        return <li key={no} className={`tq-equip ${aba === no ? 'voce' : ''} ${aguardando ? 'aguardando' : ''}`}>
          <button type="button" disabled={!dados?.ativo} onClick={() => trocarAba(no)}
            aria-label={`${nos[no]?.nome}: ${ip || 'sem endereço'}${gw ? `, ${gw}` : ''}${rotulo ? `, ${rotulo}` : ''}${aguardando ? ' (o próximo passo é aqui)' : ''}`}>
            <span className="tq-icone" aria-hidden="true"><Icone size={22} />{aguardando && <b>!</b>}</span>
            <strong>{nos[no]?.nome}</strong>
            <code>{ip || 'sem endereço'}</code>
            {gw && <small>{gw}</small>}
            {rotulo && <small>{rotulo}</small>}
            {etiqueta && <em className={deste.situacao === 'atual' ? 'tq-chamado-atual' : 'tq-chamado-fila'}>{etiqueta}</em>}
          </button>
        </li>
      })}</ul>
    </div>
  }
  const marcaLan = (no) => esperado(`aba-${no}`) ? 'aguardando' : ''
  const topologiaLan = <section className="gw-painel gw-topologia lt-topologia tq-topologia" aria-label="Topologia da rede">
    <h2 className="gw-etiqueta">TOPOLOGIA · {missao?.rede || 'REDE'} · CLIQUE NUM EQUIPAMENTO PARA ABRIR O TERMINAL DELE</h2>
    <div className={`tq-diagrama tq-lan ${config.colunaLateral ? 'tq-lan-com-coluna' : ''}`}>
      {grupoLan(setoresLista[0], 'cima', CORES[0])}
      <div className="tq-lan-centro">
        {nos.switch ? <button type="button" className={`tq-lan-switch ${aba === 'switch' ? 'selecionado' : ''} ${marcaLan('switch')}`}
          disabled={!dados?.ativo} onClick={() => trocarAba('switch')} aria-label={`Switch${marcaLan('switch') ? ' (o próximo passo é aqui)' : ''}`}>
          <span className="tq-lan-switch-nome"><Network size={18} aria-hidden="true" /><strong>Switch</strong>{marcaLan('switch') && <b aria-hidden="true">!</b>}</span>
          {(nos.switch?.interfaces || []).map((i) => <small key={i}><b>{i}</b> {descreverVlan(estados.switch?.vlans?.[i])}{missao?.portas?.[i] ? ` · ${missao.portas[i].replace(/ eth\d+$/, '')}` : ''}</small>)}
        </button>
          : <div className="tq-lan-switch tq-lan-fixo" role="img" aria-label="Switch"><span className="tq-lan-switch-nome"><Network size={18} aria-hidden="true" /><strong>Switch</strong></span></div>}
        {nos.roteador && config.colunaLateral && <div className="tq-lan-coluna">
          {['roteador', 'intranet'].filter((no) => nos[no]).map((no, i) => <span key={no} className="tq-lan-coluna-item">
            {i > 0 && <span className="tq-lan-cabo-vertical" aria-hidden="true" />}
            <button type="button" className={`tq-lan-switch ${aba === no ? 'selecionado' : ''} ${marcaLan(no)}`} disabled={!dados?.ativo}
              onClick={() => trocarAba(no)} aria-label={`${nos[no]?.nome}${marcaLan(no) ? ' (o próximo passo é aqui)' : ''}`}>
              <span className="tq-lan-switch-nome">{no === 'roteador' ? <IconeRoteador aria-hidden="true" /> : <Server size={18} aria-hidden="true" />}
                <strong>{no === 'roteador' ? 'Roteador' : 'Intranet'}</strong>{marcaLan(no) && <b aria-hidden="true">!</b>}</span>
              {(nos[no]?.interfaces || []).map((i) => <small key={i}><b>{i}</b> {curto(estados[no]?.interfaces?.[i]?.[0]) || '—'}</small>)}
              {nos[no]?.rotas === true && <small><b>gw</b> {estados[no]?.rota_padrao ? curto(estados[no].rota_padrao) : 'nenhum'}</small>}
            </button></span>)}
        </div>}
        {nos.roteador && !config.colunaLateral && <div className="tq-lan-lateral"><span className="tq-lan-cabo-lateral" aria-hidden="true" />
          <button type="button" className={`tq-lan-switch ${aba === 'roteador' ? 'selecionado' : ''} ${marcaLan('roteador')}`} disabled={!dados?.ativo}
            onClick={() => trocarAba('roteador')} aria-label={`Roteador: ${estados.roteador?.interfaces?.eth0?.[0] || 'sem endereço'}${marcaLan('roteador') ? ' (o próximo passo é aqui)' : ''}`}>
            <span className="tq-lan-switch-nome"><IconeRoteador aria-hidden="true" /><strong>Roteador</strong>{marcaLan('roteador') && <b aria-hidden="true">!</b>}</span>
            <small>{(estados.roteador?.interfaces?.eth0?.[0] || '—').split('/')[0]}</small>
          </button></div>}
      </div>
      {grupoLan(setoresLista[1], 'baixo', CORES[1])}
    </div>
  </section>
  const painelTopologia = (<section className="gw-painel gw-topologia lt-topologia" aria-label="Topologia dos setores">
    <h2 className="gw-etiqueta">TOPOLOGIA · {missao?.rede || 'REDE A DESCOBRIR'} · CLIQUE NUM EQUIPAMENTO PARA ABRIR O TERMINAL DELE</h2>
    {roteadores.length === 0 ? <div className="lr-lan">{setoresLista.map(([chave, s]) => <div key={chave} className="lr-lan-sala">
      <span className="lr-lan-nome">{s.nome}{s.rede ? ` · ${s.rede}/${s.prefixo}` : ''}</span>
      <div className="lr-lan-switch" role="img" aria-label="Switch da sala"><Network size={22} aria-hidden="true" /><strong>Switch</strong></div>
      <div className="lr-lan-pcs">{config.abas.filter((no) => nos[no]?.setor === chave).map((no) =>
        <button key={no} type="button" className={`lr-lan-pc ${aba === no ? 'selecionado' : ''}`} disabled={!dados?.ativo}
          onClick={() => trocarAba(no)} aria-label={`${nos[no].nome}: ${resumo(no)}`}>
          <Computer size={26} aria-hidden="true" /><strong>{nos[no].nome}</strong><small>{resumo(no)}</small>
        </button>)}</div>
    </div>)}</div> : <div className="lt-mapa lr-mapa">
      <div className="lr-lado">{setoresLista.slice(0, metade).map((s, i) => zona(s, i))}</div>
      <span className="lt-cabo" aria-hidden="true" />
      {config.switchFixo && <div className="lt-equip" role="img" aria-label="Switch da rede"><Network size={16} aria-hidden="true" /><strong>Switch</strong></div>}
      {roteadores.map((r, i) => <span key={r} className="lr-roteadores">{i > 0 && <span className="lt-cabo lr-enlace" aria-label={config.enlace ? 'Ligação' : 'Enlace entre os roteadores'}>
        {config.enlace !== '' && <i>{config.enlace || 'enlace'}</i>}</span>}{botaoRoteador(r)}</span>)}
      <span className="lt-cabo" aria-hidden="true" />
      <div className="lr-lado">{setoresLista.slice(metade).map((s, i) => zona(s, i + metade))}</div>
    </div>}
  </section>)
  const painelEtapas = (<ol className="gw-etapas" aria-label="Etapas da missão" style={{ gridTemplateColumns: `repeat(${etapas.length || 4}, minmax(0, 1fr))` }}>{etapas.map((e, i) => (
    <li key={e.id} className={e.concluida ? 'feita' : i === atual ? 'atual' : ''} aria-current={!e.concluida && i === atual ? 'step' : undefined}>
      <span>{e.concluida ? <CheckCircle2 size={20} /> : i + 1}</span>
      <div><strong>{e.titulo}</strong><small>{e.concluida ? 'Concluída' : i === atual ? e.orientacao : 'A seguir'}</small></div>
    </li>))}</ol>)

  const campos = missao?.plano?.campos || []
  const grupos = [...new Set(campos.map((c) => c.grupo))]
  const colunas = campos.filter((c) => c.grupo === grupos[0])
  const rotuloGrupo = (g) => config.plano?.rotulo || setores[g]?.nome || `Rota no ${nos[g]?.nome}`
  const valorPlano = (id) => missao?.plano?.correto ? missao.plano.respostas[id] : (plano[id] ?? '')
  const painelPlano = campos.length > 0 && <section className={`lr-plano ${missao.plano.correto ? 'conferido' : ''}`} aria-label={config.plano?.titulo || 'Plano de endereçamento'}>
    <header><ClipboardList size={18} aria-hidden="true" /><span>{config.plano?.etiqueta || `PLANO · ${missao.rede}`}</span>
      {missao.plano.correto && <b><CheckCircle2 size={15} aria-hidden="true" /> conferido pelo servidor</b>}</header>
    {config.plano?.descricao && <p className="lr-plano-descricao">{config.plano.descricao}</p>}
    {config.plano?.prefixos && <table className="lr-prefixos"><thead><tr><th>Prefixo</th><th>Endereços</th><th>Hosts úteis</th></tr></thead>
      <tbody>{config.plano.prefixos.map((p) => <tr key={p}><td><code>/{p}</code></td><td>{2 ** (32 - p)}</td><td>{2 ** (32 - p) - 2}</td></tr>)}</tbody></table>}
    {config.plano?.regua && <ol className="lr-regua" aria-label="Divisão da rede em blocos">{config.plano.regua.blocos.map(([nome, nota], i) =>
      <li key={i} className={nota ? '' : 'livre'}><b>{i + 1}º bloco</b><span>{nome}</span>{nota && <small>{nota}</small>}</li>)}</ol>}
    <div className="lr-tabela" role="table" style={{ '--colunas': colunas.length }}>
      <div role="row" className="lr-linha lr-cabecalho"><span role="columnheader">{config.plano?.coluna || 'Setor'}</span>
        {colunas.map((c) => <span role="columnheader" key={c.id}>{c.rotulo}</span>)}</div>
      {config.modeloPlano && <div role="row" className="lr-linha lr-modelo"><span role="cell">{setores[config.modeloPlano.grupo]?.nome} <small>(modelo)</small></span>
        {colunas.map((c) => <span role="cell" key={c.id}><code>{config.modeloPlano.valores[c.id]}</code></span>)}</div>}
      {grupos.map((g) => <div role="row" key={g} className="lr-linha">
        <span role="cell">{rotuloGrupo(g)}{setores[g]?.pedido && <small>{setores[g].pedido}</small>}</span>
        {campos.filter((c) => c.grupo === g).map((c) => <span role="cell" key={c.id}>
          <small className="lr-campo-rotulo" aria-hidden="true">{c.rotulo}</small>
          <input aria-label={`${c.rotulo} de ${rotuloGrupo(g)}`} value={valorPlano(c.id)} spellCheck={false} autoComplete="off"
            disabled={!livre || missao.plano.correto} className={missao.plano.erros.includes(c.id) && missao.plano.respostas[c.id] === String(plano[c.id] ?? '').trim() ? 'erro' : ''}
            placeholder={{ mascara: '255.…', prefixo: '/26', rede: '192.168.x.0/24', mac: '00:00:00:00:00:00', porta: 'eth…' }[c.tipo] || '192.168.…'}
            onChange={(e) => { setPlano({ ...plano, [c.id]: e.target.value }); setRetornoPlano('') }} />
        </span>)}
      </div>)}
    </div>
    {!missao.plano.correto && <button data-acao="plano" className={`gw-primario ${esperado('plano')}`} disabled={!livre || campos.some((c) => !String(plano[c.id] ?? '').trim())}
      onClick={() => executar('planejar', { respostas: Object.fromEntries(campos.map((c) => [c.id, String(plano[c.id] ?? '').trim()])) })}>{config.plano?.botao || 'Conferir plano'}</button>}
    {retornoPlano && <p className={`lt-retorno ${missao.plano.correto ? 'ok' : ''}`} role="status">{retornoPlano}</p>}
    {retornoPlano && !missao.plano.correto && config.dicaPlano && <ul className="lr-dicas-plano">
      {campos.filter((c) => missao.plano.erros.includes(c.id)).map((c) => <li key={c.id}><b>{rotuloGrupo(c.grupo)} · {c.rotulo}:</b> {config.dicaPlano(c.id, missao.plano.respostas[c.id] ?? '', missao.plano.respostas)}</li>)}</ul>}
  </section>

  // Conclusão de laboratório: o Link com confetes; o troféu fica só para o desafio final.
  const arte = arteDoLab(config.arte ?? config.numero)
  const imagemConclusao = config.id === 'desafio-rede-da-empresa' ? COMEMORACAO.trofeu : COMEMORACAO.confetes
  const avisos = <>
    {dados?.conflito && <section className="gw-alerta" role="alert"><strong>Outro laboratório está em uso</strong><p>Volte aos laboratórios para abrir a missão correspondente. A sessão existente foi preservada.</p></section>}
    {dados?.preparacao_pendente && <section className="gw-alerta" role="alert"><strong>Preparação incompleta</strong><p>O servidor ainda não confirmou a preparação e a remoção do ambiente.</p></section>}
    {aviso && <p className="gw-alerta" role={recuperacao ? 'alert' : 'status'}>{aviso}</p>}
    {(recuperacao || expirado || dados?.preparacao_pendente) && <section className="gw-alerta">
      <p>{expirado ? 'O prazo terminou ou não foi confirmado. Consulte o estado do ambiente.' : 'Consulte o estado antes de continuar.'}</p>
      <button className={esperado('atualizar')} data-acao="atualizar" disabled={ocupado} onClick={() => executar('status')}>Atualizar estado</button>
    </section>}
    {registrada && (xp !== null || pendente) && <section className="gw-sucesso lr-sucesso" data-testid="conclusao" aria-live="polite">
      <img src={imagemConclusao} alt="Link comemorando a missão concluída" />
      <div><strong>Missão concluída</strong>
      <p>{pendente ? 'Conclusão salva; remoção do ambiente ainda pendente.' : 'Conclusão salva e ambiente encerrado pelo servidor.'} {xp !== null ? xp > 0 ? `+${xp} XP confirmados.` : 'Sem nova concessão de XP.' : 'Progresso recuperado do servidor.'}</p>
      {pendente && <button data-acao="limpar" className={esperado('limpar')} disabled={ocupado || recuperacao || !dados?.ativo} onClick={() => executar('encerrar')}>Tentar limpeza novamente</button>}
      </div>
    </section>}
  </>

  if (!dados?.ativo) {
    return (
      <main className="laboratorio-pagina gateway-lab gw-v2 lt-lab lr-lab lt-inicio" aria-busy={ocupado}>
        <nav className="gw-controles" aria-label="Navegação"><Link className={esperado('catalogo')} data-acao="catalogo" to="/laboratorios">Voltar aos laboratórios</Link></nav>
        {avisos}
        <section className="lt-missao lr-missao">
          <div className="lt-missao-texto">
            <span className="gw-etiqueta">{config.etiqueta}</span>
            <h1>{config.missao.titulo}</h1>
            <p>{config.missao.texto}</p>
            <div className="lt-missao-acoes">
              <button className={`gw-primario ${esperado('iniciar')}`} data-acao="iniciar" disabled={ocupado || !dados?.disponivel || Boolean(dados?.conflito) || recuperacao || pendente}
                onClick={() => executar('iniciar')}>{operacao === 'iniciar' ? 'Preparando a rede…' : registrada ? 'Iniciar novo treino' : 'Iniciar ambiente'}</button>
              <span><Clock3 size={15} aria-hidden="true" /> {config.tempo}{config.semXp ? '' : ` · ${missao?.xp ?? 100} XP`}</span>
            </div>
          </div>
          {arte && <img className="lr-missao-arte" src={arte} alt="" />}
        </section>
        <div className="lr-briefing">
          <section className="lr-briefing-link" aria-label="O Link explica como funciona">
            <img src={POSES.explicando} alt="Link explicando" />
            <div className="lr-balao"><strong>Antes de começar</strong>
              <ul>
                <li><b>Agora faça</b> mostra o objetivo de cada etapa. Se travar, peça uma pista: elas abrem uma de cada vez.</li>
                {config.terminais ? <li><b>Tudo acontece no terminal da T.I.</b> Os outros computadores você alcança pela rede, com ssh.</li>
                  : <li><b>Clique num equipamento</b> da topologia para abrir o terminal dele.</li>}
                <li><b>Validar missão</b> fica ao lado do tempo e acende quando tudo estiver pronto. Quem confere é o servidor.</li>
                <li>Ficou em dúvida? <b>Pergunte para mim</b> no painel ao lado do terminal.</li>
              </ul></div>
          </section>
          <section className="lr-briefing-fila">
            <h2>O que você vai fazer</h2>
            <ul className="lt-fila" aria-label="O que você vai fazer">{config.missao.fila.map(([titulo, texto], i) => <li key={titulo}>
              <Ticket size={18} aria-hidden="true" /><div><b>{i + 1} · {titulo}</b><span>{texto}</span></div>
            </li>)}</ul>
          </section>
        </div>
      </main>
    )
  }

  const estadoAba = estados[alvo]
  const donoIp = Object.fromEntries(Object.entries(estados).flatMap(([no, e]) => Object.values(e?.interfaces || {}).flat()
    .map((end) => [end.split('/')[0], nos[no]?.nome])))
  const nomeIp = (ip) => !ip ? '—' : donoIp[ip] ? `${donoIp[ip]} (${ip})` : ip
  const planoTrancado = config.planoDepoisDoChamado && chamado && !chamado.correta && chamado.etapa === etapaAtual
  const tarefas = (<>
          {planoTrancado ? <section className="lr-plano lr-plano-trancado" aria-label="Plano de rotas">
            <header><ClipboardList size={18} aria-hidden="true" /><span>PLANO · {missao.rede}</span></header>
            <p>Abre depois do diagnóstico: primeiro descubra a causa no chamado.</p></section> : painelPlano}

          {config.terminais && !registrada && <section className="lt-chamado lr-suporte" aria-label="Missão">
            <header><Ticket size={18} aria-hidden="true" /><span>CHAMADO</span><strong>Financeiro B</strong></header>
            <blockquote>“{config.missao.titulo}.”</blockquote>
            <ol className="lt-checklist" aria-label="O que a missão exige">{etapas.filter((e) => e.id !== 'comprovar').map((e) => {
              const estado = e.concluida ? 'feito' : e.id === etapaAtual ? 'atual' : 'falta'
              return <li key={e.id} className={estado}>{estado === 'feito' ? <CheckCircle2 size={15} aria-hidden="true" /> : <span aria-hidden="true" />}
                {e.titulo}<small>{estado === 'feito' ? 'feito' : estado === 'atual' ? 'agora' : 'falta'}</small></li>
            })}</ol>
            <p className="lt-objetivo"><b>Conexão</b>{missao?.remoto ? `SSH aberto no ${nos[missao.remoto]?.nome}` : `terminal local da ${nos[aba]?.nome}`}</p>
            <div className="lr-folhas"><b><Printer size={15} aria-hidden="true" /> Folhas impressas</b>
              {missao?.folhas?.length ? <ul>{missao.folhas.map((f) => <li key={f.hora + f.texto}><q>{f.texto}</q><small>de {nos[f.origem]?.nome}</small></li>)}</ul>
                : <p>Nenhuma ainda. A impressora fica no Prédio A ({missao?.impressora?.ip}, porta {missao?.impressora?.porta}).</p>}</div>
          </section>}

          {resolvidos.length > 0 && !registrada && <section className="lt-resolvidos" aria-label="Chamados resolvidos">
            {resolvidos.map((c) => <p key={c.etapa}><CheckCircle2 size={15} aria-hidden="true" /><span><strong>{c.titulo}: resolvido.</strong> {c.resolucao}</span></p>)}
            {naFila.length > 0 && <p className="lt-na-fila">Ainda na fila: {naFila.map((c) => c.titulo).join(' · ')}</p>}
          </section>}

          {chamado && chamado.etapa === etapaAtual && !registrada && <section className="lt-chamado" data-chamado aria-label="Chamado aberto">
            <header><Ticket size={18} aria-hidden="true" /><span>{chamados.length ? `CHAMADO ${chamados.findIndex((c) => c.etapa === chamado.etapa) + 1} DE ${chamados.length}` : 'CHAMADO'}</span>
              <strong>{chamados.length ? chamado.titulo.split(' · ').at(-1) : nos[chamado.no]?.nome}</strong></header>
            <blockquote>“{chamado.sintoma}”</blockquote>
            {chamados.length > 0 && nos[chamado.no] && <p className="lt-aberto"><b>Aberto por</b>{nos[chamado.no].nome}</p>}
            {chamado.objetivo && <p className="lt-objetivo"><b>Objetivo</b>{chamado.objetivo}</p>}
            {passosChamado.length > 0 && <ol className="lt-checklist" aria-label="O que este chamado exige">{passosChamado.map(([texto, estado]) => (
              <li key={texto} className={estado}>{estado === 'feito' ? <CheckCircle2 size={15} aria-hidden="true" /> : <span aria-hidden="true" />}
                {texto}<small>{estado === 'feito' ? 'feito' : estado === 'atual' ? 'agora' : 'falta'}</small></li>))}</ol>}
            {chamado.suspeitas && !chamado.correta && <ol className="lt-suspeitas" aria-label="Suspeitas para testar">
              {chamado.suspeitas.map((x, i) => <li key={x.texto} className={x.testada ? 'feito' : ''}>
                {x.testada ? <CheckCircle2 size={15} aria-hidden="true" /> : <span aria-hidden="true">{i + 1}</span>}
                <div><b>{x.texto}</b><small>Aba {x.onde}: <code>{x.comando}</code> · {x.olhar}</small></div>
                <em>{x.testada ? 'testada' : 'falta testar'}</em></li>)}</ol>}
            {!chamado.correta ? <>
              <fieldset data-acao="causa" className={`lt-opcoes ${esperado('causa')}`} tabIndex={-1}
                disabled={!livre || Boolean(chamado.suspeitas?.some((x) => !x.testada))}>
                <legend>{chamado.suspeitas?.some((x) => !x.testada) ? 'Teste as suspeitas acima; a resposta abre depois dos testes.'
                  : 'Qual é a causa? Responda com base no que o terminal mostrou.'}</legend>
                {chamado.opcoes.map((o) => <label key={o.id}><input type="radio" name={`causa-${chamado.etapa}`} value={o.id}
                  checked={causa === o.id} onChange={() => { setCausa(o.id); setRetornoCausa('') }} />{o.texto}</label>)}
              </fieldset>
              <button className="gw-primario" disabled={!livre || !causa} onClick={() => executar('diagnosticar', { resposta: causa })}>Confirmar causa</button>
            </> : <p className="lt-causa-ok"><CheckCircle2 size={16} aria-hidden="true" /><span><strong>Causa identificada:</strong> {chamado.opcoes.find((o) => o.id === chamado.resposta)?.texto}</span></p>}
            {retornoCausa && <p className={`lt-retorno ${chamado.correta ? 'ok' : ''}`} role="status">{retornoCausa}</p>}
          </section>}

          {etapaAtual === 'comprovar' && !registrada && <section className="lt-chamado lt-comprovar">
            <header><CheckCircle2 size={18} aria-hidden="true" /><span>TUDO CONFIGURADO</span></header>
            <p>{config.textoComprovar || 'O servidor vai reler cada equipamento, conferir que cada endereço está no bloco do seu setor e repetir os pings.'}</p>
            <button data-acao="concluir" className={`gw-primario ${esperado('concluir')}`} disabled={!livre} onClick={() => executar('validar')}>Validar missão</button>
          </section>}
  </>)
  const terminal = (<>
          <section className="lt-terminal" aria-label={`Terminal do ${nomeAba}`}>
            <div className="lt-abas" role="tablist" aria-label="Equipamentos">
              {terminais.map((no) => <button key={no} type="button" role="tab" aria-selected={aba === no} data-acao={`aba-${no}`}
                className={`${aba === no ? 'ativa' : ''} ${esperado(`aba-${no}`)}`} onClick={() => trocarAba(no)}>{nos[no]?.nome}</button>)}
            </div>
            <div className="lt-tela" ref={saida} role="log" aria-live="polite" aria-label="Saída do terminal" onClick={() => campo.current?.focus()}>
              {linhas.length === 0 && <p className="lt-boasvindas">{nos[aba]?.host} · {nos[aba]?.tipo === 'switch' ? 'portas' : 'interfaces'} {nos[aba]?.interfaces?.join(', ')} · comandos: {config.comandos
                ? config.comandos(nos[aba]) : `ip addr, ip route${nos[aba]?.tipo === 'pc' || nos[aba]?.rotas ? '' : ' (só leitura)'} e ping`}</p>}
              {linhas.map((h) => <div key={h.revisao} className="lt-linha">
                {!h.senha && <div className="lt-cmd"><span className="lt-ps1">suporte@{nos[h.remoto || h.pc]?.host}:~$</span> {h.digitado}</div>}
                {h.saida && <pre className={h.codigo === 0 ? '' : 'lt-erro'}>{h.saida}</pre>}
                {h.confirmacao && <p className="lt-confirmacao">✓ comando aplicado · {h.confirmacao}</p>}
              </div>)}
              {erroTerminal && <p className="lt-recusado" role="alert">{erroTerminal}</p>}
              {!registrada && <form className={`lt-entrada ${esperado('comando')}`} onSubmit={enviarComando}>
                <label htmlFor="lt-comando" className="lt-ps1">{pedindoSenha ? 'senha:' : `suporte@${nos[alvo]?.host}:~$`}</label>
                <input data-acao="comando" ref={campo} id="lt-comando" value={comando} type={pedindoSenha ? 'password' : 'text'}
                  aria-label={pedindoSenha ? `Senha do ssh para ${missao.senha_pendente.usuario}@${missao.senha_pendente.ip}` : `Comando no ${nomeAba}`}
                  onChange={(e) => { setComando(e.target.value); setErroTerminal('') }} onKeyDown={navegarHistorico}
                  disabled={!livre} autoComplete="off" spellCheck={false} autoCapitalize="none" maxLength={100} />
              </form>}
            </div>
            <p className="lt-dica">Enter executa · ↑ e ↓ repetem comandos{ocupado && operacao === 'terminal' ? ` · aguardando o ${nomeAba}…` : ''}</p>
          </section>

          <section className="lt-estado" aria-label={`Estado lido do ${nomeAba}`}>
            <span><strong>{nomeAba}</strong> · lido do equipamento depois de cada comando</span>
            {nos[alvo]?.tipo === 'switch'
              ? Object.entries(estadoAba?.vlans || {}).map(([i, v]) => <span key={i}><b>{i}</b> {descreverVlan(v)}</span>)
              : Object.entries(estadoAba?.interfaces || {}).map(([i, l]) => <span key={i}><b>{i}</b> {l.length ? l.join(', ') : 'sem endereço IPv4'}</span>)}
            {(nos[alvo]?.tipo === 'pc' || nos[alvo]?.rotas === true) && !config.semGateway && <span><b>rota padrão</b> {estadoAba?.rota_padrao ? `via ${estadoAba.rota_padrao}` : 'nenhuma'}</span>}
            {config.mostrarDns && nos[aba]?.tipo === 'pc' && <span><b>servidor DNS</b> {estadoAba?.dns?.join(', ') || 'nenhum'}</span>}
            {nos[aba]?.rotas && nos[aba].rotas !== true && <span><b>rotas estáticas</b> {estadoAba?.rotas?.join('; ') || 'nenhuma'}</span>}
            {Object.entries(testes[alvo] || {}).map(([ip, ok]) => <span key={ip}><b>ping {ip}</b> <em className={ok ? 'ok' : 'falhou'}>{ok ? 'respondeu' : 'não respondeu'}</em></span>)}
          </section>
          <BastidoresTshark capturas={dados?.bastidores} nomeNo={(no) => nos[no]?.nome || no} nomeIp={nomeIp} />
  </>)
  return (
    <main className={`laboratorio-pagina gateway-lab gw-v2 gw-v3 lt-lab lr-lab ${foco ? 'gw-foco' : ''}`} aria-busy={ocupado}>
      <nav className="gw-controles" aria-label="Opções de visualização">
        <button aria-pressed={foco} onClick={() => setFoco(!foco)}>{foco ? 'Sair do modo foco' : 'Modo foco'}</button>
        <Link className={esperado('catalogo')} data-acao="catalogo" to="/laboratorios">Voltar aos laboratórios</Link>
      </nav>
      <header className="gw-cabecalho">
        <div><span className="gw-etiqueta">{config.etiqueta}</span><h1>{config.titulo}</h1></div>
        <div className="gw-acoes">
          {!registrada && <TempoEValidar tempo={!dados.conflito ? tempo : '--:--'} restantes={dados.conflito ? null : restantes}
            pronta={etapaAtual === 'comprovar' && livre} feitas={etapas.filter((e) => e.concluida).length} total={etapas.length}
            ocupado={ocupado} aoValidar={dados.ativo ? () => executar('validar') : null} semXp={config.semXp} />}
        </div>
      </header>
      {avisos}

      <EspacoLaboratorio agoraAoLado={config.agoraAoLado} apresentacao={config.semApresentacao ? undefined : config.id} topologia={config.topologiaPredios ? topologiaPredios : config.topologiaLan ? topologiaLan : painelTopologia} etapas={painelEtapas} orientacao={orientacao}
        chaveEtapa={etapaAtual} aoIrParaAcao={irParaAcao} ajudaAberta={ajudaExpandida} aoAlternarAjuda={() => setAjudaExpandida(!ajudaExpandida)}
        tutor={{
          imagem: registrada ? imagemConclusao : linkOcupado ? POSES.pensativo
            : etapaAtual === 'comprovar' ? POSES.incentivando : POSES.investigando,
          mensagem: registrada ? 'Missão concluída. Você pode rever os resultados.' : 'Dúvida sobre o plano, um comando ou uma mensagem do terminal? Pergunte.',
          conteudo: <ConversaLink mensagens={mensagensLink} aoPerguntar={perguntarAoLink} ocupado={linkOcupado} disponivel={ativo} erro={erroLink} />,
        }}
        lateral={<section className="gw-painel gw-pratica lt-pratica" aria-label="Tarefas">{tarefas}</section>}>
        <section className="gw-painel gw-pratica lt-pratica" aria-label="Prática">
          {terminal}
        </section>
      </EspacoLaboratorio>
      {!registrada && !dados?.conflito && <footer className="gw-gerencia">
        <details><summary>Gerenciar ambiente</summary><div className="gw-gerencia-itens">
          <p>O prazo continua ao sair da página.</p>
          <button disabled={!livre || !dados.laboratorio?.pode_estender || dados.laboratorio?.extensoes_utilizadas >= 1} onClick={() => executar('estender')}>Adicionar 5 minutos</button>
          <button data-acao="encerrar" className={esperado('encerrar')} disabled={ocupado || recuperacao} onClick={() => executar('encerrar')}>Encerrar ambiente</button>
          <button disabled={ocupado} onClick={() => executar('status')}>Atualizar estado</button>
        </div></details>
      </footer>}
    </main>
  )
}

function LaboratorioRede({ config }) {
  const { usuario } = useAuth()
  return <SessaoRede key={`${config.id}-${usuario?.id || usuario?.login || 'sem-sessao'}`} config={config} />
}

export function LaboratorioPrimeiraLAN() { return <LaboratorioRede config={LAB2} /> }
export function LaboratorioDividindoRede() { return <LaboratorioRede config={LAB5} /> }
export function LaboratorioPlanejandoEmpresa() { return <LaboratorioRede config={LAB6} /> }
export function LaboratorioInvestigandoLan() { return <LaboratorioRede config={LAB9} /> }
export function LaboratorioConectandoRedes() { return <LaboratorioRede config={LAB7} /> }
export function LaboratorioEnderecosNomes() { return <LaboratorioRede config={LAB8} /> }
export function LaboratorioDesafioEmpresa() { return <LaboratorioRede config={LAB10} /> }
export function LaboratorioSuporteRemoto() { return <LaboratorioRede config={LAB_SUPORTE} /> }
