import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Computer, Network, Clock3, Server, CheckCircle2, Ticket, Lightbulb, Search, Wrench, Activity } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { criarClienteTerminal, prepararComando } from '../services/terminalGuiado'
import { NOMES_PC, orientarTerminal } from '../services/orientacaoTerminal'
import { POSES } from '../assets/mascote/poses'
import ConversaLink from '../components/laboratorio/ConversaLink'
import TempoEValidar from '../components/laboratorio/TempoEValidar'
import BastidoresTshark from '../components/laboratorio/BastidoresTshark'
import EspacoLaboratorio from '../components/laboratorio/EspacoLaboratorio'
import IconeRoteador from '../components/laboratorio/IconeRoteador'
import './Laboratorio.css'
import './LaboratorioResponsivo.css'
import './LaboratorioGateway.css'
import './LaboratorioTerminal.css'
import './LaboratorioRede.css'
import arteLab4 from '../assets/trilha/09-lab4-configure-terminal.webp'

const api = criarClienteTerminal()
const PCS = ['novo', 'financeiro', 'recepcao']
const HOSTS = { novo: 'pc-novo', financeiro: 'pc-financeiro', recepcao: 'pc-recepcao' }
const SERVIDOR = '192.168.20.10'
const FLUXO = [[Search, 'Observar', 'ip addr e ip route'], [Lightbulb, 'Identificar a causa', 'entre três hipóteses'],
  [Wrench, 'Corrigir', 'só o PC do chamado'], [Activity, 'Comprovar', 'ping ao servidor']]

function SessaoTerminal() {
  const [dados, setDados] = useState(null)
  const [operacao, setOperacao] = useState('status')
  const [aviso, setAviso] = useState('')
  const [recuperacao, setRecuperacao] = useState(false)
  const [prazo, setPrazo] = useState(null)
  const [agora, setAgora] = useState(Date.now)
  const [xp, setXp] = useState(null)
  const [foco, setFoco] = useState(true)
  const [aba, setAba] = useState('novo')
  const [comando, setComando] = useState('')
  const [erroTerminal, setErroTerminal] = useState('')
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
  const etapas = (missao?.etapas || []).map((e) => registrada ? { ...e, concluida: true } : e)
  const historico = Array.isArray(missao?.terminal) ? missao.terminal : []
  const estados = missao?.estados || {}
  const donoIp = { [SERVIDOR]: 'Servidor', ...Object.fromEntries(PCS.flatMap((pc) => (estados[pc]?.enderecos || []).map((e) => [e.split('/')[0], NOMES_PC[pc]]))) }
  const nomeIp = (ip) => !ip ? '—' : donoIp[ip] ? `${donoIp[ip]} (${ip})` : ip
  const testes = missao?.testes || {}
  const chamados = missao?.chamados || []
  const etapaAtual = missao?.proxima_etapa
  const chamado = chamados.find((c) => c.id === etapaAtual)
  const linhas = historico.filter((h) => h.pc === aba)

  function receber(retorno) {
    if (retorno.missao?.id !== 'configure-pelo-terminal' || typeof retorno.ativo !== 'boolean' || !Number.isInteger(retorno.missao.revisao)
      || (retorno.ativo && (!Number.isInteger(retorno.laboratorio?.session_id) || retorno.laboratorio.session_id <= 0))) {
      throw new Error('O servidor não confirmou o estado deste laboratório.')
    }
    // Ao abrir um chamado novo, o terminal passa para o PC dele e a escolha de causa recomeça.
    const etapaAnterior = estadoAtual.current?.missao?.proxima_etapa
    const novo = retorno.missao.chamados?.find((c) => c.id === retorno.missao.proxima_etapa)
    if (retorno.missao.proxima_etapa !== etapaAnterior) {
      if (novo) setAba(novo.pc)
      setCausa('')
      setRetornoCausa('')
    }
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
  }, [])

  useEffect(() => {
    if (!dados?.ativo || registrada) return undefined
    const timer = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [dados?.ativo, registrada])

  useEffect(() => { saida.current?.scrollTo({ top: saida.current.scrollHeight }) }, [linhas.length, erroTerminal, aba])

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
      if (erro.status === 400 && ['terminal', 'diagnosticar', 'validar'].includes(acao)) {
        if (acao === 'terminal') setErroTerminal(erro.message)
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
    memoria.lista = [...memoria.lista.filter((c) => c !== entrada.comando), entrada.comando].slice(-20)
    memoria.posicao = -1
    executar('terminal', { comando: entrada.comando, pc: aba })
  }

  function navegarHistorico(evento) {
    const memoria = anteriores.current
    if (!['ArrowUp', 'ArrowDown'].includes(evento.key) || !memoria.lista.length) return
    evento.preventDefault()
    const total = memoria.lista.length
    const posicao = evento.key === 'ArrowUp' ? (memoria.posicao < 0 ? total - 1 : Math.max(0, memoria.posicao - 1))
      : (memoria.posicao < 0 ? -1 : memoria.posicao + 1)
    memoria.posicao = posicao >= total ? -1 : posicao
    setComando(memoria.posicao < 0 ? '' : memoria.lista[memoria.posicao])
  }

  function trocarAba(pc) {
    setAba(pc)
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
  const tipoObservar = etapaAtual === 'chamado-2' ? 'ver-rotas' : 'ver-enderecos'
  const estadoChamado = estados[chamado?.pc] || { enderecos: [], rota_padrao: null }
  const orientacao = orientarTerminal({
    ocupado, recuperacao, expirado, preparacaoPendente: dados?.preparacao_pendente, conflito: dados?.conflito,
    registrada, pendente, ativo: dados?.ativo, etapa: etapaAtual, pc: chamado?.pc, abaAtual: aba,
    causaIdentificada: Boolean(chamado?.correta),
    observou: Boolean(chamado) && historico.some((h) => h.pc === chamado.pc && h.tipo === tipoObservar),
    enderecos: estadoChamado.enderecos.length, temRota: Boolean(estadoChamado.rota_padrao),
    servidorFalhou: testes[chamado?.pc]?.[SERVIDOR] === false,
  })
  const resolvidos = chamados.filter((c) => c.resolvido)
  const naFila = chamados.filter((c) => !c.resolvido && c !== chamado)
  const andamento = chamado?.progresso || {}
  const nomePc = NOMES_PC[chamado?.pc]
  const feitos = [andamento.causa || (Boolean(chamado) && historico.some((h) => h.pc === chamado.pc && h.tipo === tipoObservar)),
    andamento.causa, andamento.configuracao, andamento.configuracao && andamento.servidor].map(Boolean)
  const primeiraPendente = feitos.indexOf(false)
  const passosChamado = [`Investigar o ${nomePc} pelo terminal`, 'Confirmar a causa no chamado', `Corrigir a configuração do ${nomePc}`,
    `Comprovar: ping do ${nomePc} ao servidor responde`].map((texto, i) => [texto, feitos[i] ? 'feito' : i === primeiraPendente ? 'atual' : 'falta'])
  const esperado = (alvo) => orientacao.alvo === alvo ? 'gw-proxima-acao' : ''
  const irParaAcao = () => requestAnimationFrame(() => {
    const elemento = document.querySelector(`.lt-lab [data-acao="${orientacao.alvo}"]`)
    if (!elemento) return
    elemento.scrollIntoView({ block: 'center', behavior: 'auto' })
    elemento.focus({ preventScroll: true })
  })

  const situacaoPc = (pc) => {
    const c = chamados.find((item) => item.pc === pc)
    if (registrada || c?.resolvido) return ['resolvido', 'Resolvido']
    return c?.id === etapaAtual ? ['aberto', 'Chamado aberto'] : ['fila', 'Na fila']
  }
  const resumoPc = (pc) => {
    const e = estados[pc]
    if (!e?.lido) return 'não lido'
    return e.enderecos.length ? e.enderecos.join(' · ') : 'sem endereço'
  }
  const painelTopologia = (<section className="gw-painel gw-topologia lt-topologia" aria-label="Topologia: Atendimento e Servidor">
    <h2 className="gw-etiqueta">TOPOLOGIA · CLIQUE NUM PC PARA ABRIR O TERMINAL DELE</h2>
    <div className="lt-mapa">
      <div className="lt-zona lt-zona-local"><span>Atendimento · 192.168.10.0/24</span>
        <div className="lt-pcs">{PCS.map((pc) => {
          const [classe, texto] = situacaoPc(pc)
          return <button key={pc} type="button" className={`lt-pc ${classe} ${aba === pc ? 'selecionado' : ''}`} disabled={!dados?.ativo}
            onClick={() => trocarAba(pc)} aria-label={`${NOMES_PC[pc]}: ${resumoPc(pc)}; ${texto}`}>
            <Computer size={16} aria-hidden="true" /><strong>{NOMES_PC[pc]}</strong><small>{resumoPc(pc)}</small><i aria-hidden="true">{texto}</i>
          </button>
        })}</div>
        <span className="lt-cabo" aria-hidden="true" />
        <div className="lt-equip" role="img" aria-label="Switch do Atendimento"><Network size={16} aria-hidden="true" /><strong>Switch</strong></div>
      </div>
      <span className="lt-cabo" aria-hidden="true" />
      <div className="lt-equip lt-roteador" role="img" aria-label="Roteador: eth0 192.168.10.1, eth1 192.168.20.1">
        <IconeRoteador aria-hidden="true" /><strong>Roteador</strong>
        <small><b>eth0</b> 192.168.10.1</small><small><b>eth1</b> 192.168.20.1</small>
      </div>
      <span className="lt-cabo" aria-hidden="true" />
      <div className="lt-zona lt-zona-remota"><span>Servidor · 192.168.20.0/24</span>
        <div className="lt-equip" role="img" aria-label="Servidor 192.168.20.10/24"><Server size={16} aria-hidden="true" /><strong>Servidor</strong><small>192.168.20.10/24</small></div>
      </div>
    </div>
  </section>)
  const painelEtapas = (<ol className="gw-etapas" aria-label="Chamados da missão">{etapas.map((e, i) => (
    <li key={e.id} className={e.concluida ? 'feita' : i === atual ? 'atual' : ''} aria-current={!e.concluida && i === atual ? 'step' : undefined}>
      <span>{e.concluida ? <CheckCircle2 size={20} /> : i + 1}</span>
      <div><strong>{e.titulo}</strong><small>{e.concluida ? 'Resolvido' : i === atual ? e.orientacao : 'Na fila'}</small></div>
    </li>))}</ol>)

  const avisos = <>
    {dados?.conflito && <section className="gw-alerta" role="alert"><strong>Outro laboratório está em uso</strong><p>Volte ao catálogo para abrir a missão correspondente. A sessão existente foi preservada.</p></section>}
    {dados?.preparacao_pendente && <section className="gw-alerta" role="alert"><strong>Preparação incompleta</strong><p>O servidor ainda não confirmou a preparação e a remoção do ambiente.</p></section>}
    {aviso && <p className="gw-alerta" role={recuperacao ? 'alert' : 'status'}>{aviso}</p>}
    {(recuperacao || expirado || dados?.preparacao_pendente) && <section className="gw-alerta">
      <p>{expirado ? 'O prazo terminou ou não foi confirmado. Consulte o estado do ambiente.' : 'Consulte o estado antes de continuar.'}</p>
      <button className={esperado('atualizar')} data-acao="atualizar" disabled={ocupado} onClick={() => executar('status')}>Atualizar estado</button>
    </section>}
    {registrada && <section className="gw-sucesso" data-testid="conclusao" aria-live="polite"><strong>Missão concluída: três chamados resolvidos</strong>
      <p>{pendente ? 'Conclusão salva; remoção do ambiente ainda pendente.' : 'Conclusão salva e ambiente encerrado pelo servidor.'} {xp !== null ? xp > 0 ? `+${xp} XP confirmados.` : 'Sem nova concessão de XP.' : 'Progresso recuperado do servidor.'}</p>
      {pendente && <button data-acao="limpar" className={esperado('limpar')} disabled={ocupado || recuperacao || !dados?.ativo} onClick={() => executar('encerrar')}>Tentar limpeza novamente</button>}
    </section>}
  </>

  // Tela de missão: apresenta os chamados; ao iniciar o ambiente, dá lugar à área de trabalho.
  if (!dados?.ativo) {
    return (
      <main className="laboratorio-pagina gateway-lab gw-v2 lt-lab lt-inicio" aria-busy={ocupado}>
        <nav className="gw-controles" aria-label="Navegação"><Link className={esperado('catalogo')} data-acao="catalogo" to="/laboratorios">Voltar aos laboratórios</Link></nav>
        {avisos}
        <section className="lt-missao lr-missao">
          <div className="lt-missao-texto">
            <span className="gw-etiqueta">LABORATÓRIO 4 · MESA DE SUPORTE</span>
            <h1>Três chamados aguardam você</h1>
            <p>Você é o técnico de suporte da rede do Atendimento. Cada chamado é um computador com um problema diferente:
              investigue pelo terminal, descubra a causa, corrija e comprove. A ajuda diminui a cada chamado.</p>
            <ol className="lt-fluxo">{FLUXO.map(([Icone, titulo, detalhe]) => <li key={titulo}><Icone size={18} aria-hidden="true" /><strong>{titulo}</strong><small>{detalhe}</small></li>)}</ol>
            <div className="lt-missao-acoes">
              <button className={`gw-primario ${esperado('iniciar')}`} data-acao="iniciar" disabled={ocupado || !dados?.disponivel || Boolean(dados?.conflito) || recuperacao || pendente}
                onClick={() => executar('iniciar')}>{operacao === 'iniciar' ? 'Preparando os três computadores…' : registrada ? 'Iniciar novo treino' : 'Iniciar ambiente'}</button>
              <span><Clock3 size={15} aria-hidden="true" /> 15 min (+5 se precisar) · {missao?.xp ?? 100} XP</span>
            </div>
          </div>
          <img className="lr-missao-arte" src={arteLab4} alt="" />
        </section>
        <div className="lr-briefing">
          <section className="lr-briefing-link" aria-label="O Link explica como funciona">
            <img src={POSES.explicando} alt="Link explicando" />
            <div className="lr-balao"><strong>Antes de começar</strong>
              <ul>
                <li>Os chamados chegam <b>um de cada vez</b>. O chamado aberto aparece ao lado do terminal, com o objetivo e o que falta.</li>
                <li><b>Clique num PC</b> da topologia (ou na aba) para abrir o terminal dele. Corrija só o PC do chamado.</li>
                <li><b>Agora faça</b> mostra o próximo passo. A ajuda diminui a cada chamado: no último, é com você.</li>
                <li><b>Validar missão</b> fica ao lado do tempo. Quem confere é o servidor, relendo os três PCs.</li>
                <li>Ficou em dúvida sobre um comando? <b>Pergunte para mim</b> no painel ao lado do terminal.</li>
              </ul></div>
          </section>
          <section className="lr-briefing-fila">
            <h2>Fila de chamados</h2>
            <ul className="lt-fila" aria-label="Fila de chamados">{chamados.map((c, i) => <li key={c.id}>
              <Ticket size={18} aria-hidden="true" /><div><b>#{i + 1} · {NOMES_PC[c.pc]}</b><span>“{c.sintoma}”</span></div>
            </li>)}</ul>
          </section>
        </div>
      </main>
    )
  }

  // Três colunas: o chamado e a decisão da causa à direita; o terminal na altura toda no centro.
  const tarefas = (<>
          {resolvidos.length > 0 && !registrada && <section className="lt-resolvidos" aria-label="Chamados resolvidos">
            {resolvidos.map((c) => <p key={c.id}><CheckCircle2 size={15} aria-hidden="true" /><span><strong>{c.titulo}: resolvido.</strong> {c.resolucao}</span></p>)}
            {naFila.length > 0 && <p className="lt-na-fila">Ainda na fila: {naFila.map((c) => c.titulo).join(' · ')}</p>}
          </section>}
          {chamado && !registrada && <section className="lt-chamado" aria-label="Chamado aberto">
            <header><Ticket size={18} aria-hidden="true" /><span>CHAMADO {chamados.indexOf(chamado) + 1} DE 3</span><strong>{NOMES_PC[chamado.pc]}</strong></header>
            <blockquote>“{chamado.sintoma}”</blockquote>
            <p className="lt-objetivo"><b>Objetivo</b>{chamado.objetivo}</p>
            <ol className="lt-checklist" aria-label="O que este chamado exige">{passosChamado.map(([texto, estado]) => (
              <li key={texto} className={estado}>{estado === 'feito' ? <CheckCircle2 size={15} aria-hidden="true" /> : <span aria-hidden="true" />}
                {texto}<small>{estado === 'feito' ? 'feito' : estado === 'atual' ? 'agora' : 'falta'}</small></li>))}</ol>
            {chamado.ajuda && <p className="lt-ajuda-chamado"><Lightbulb size={15} aria-hidden="true" />{chamado.ajuda}</p>}
            {!chamado.correta ? <>
              <fieldset data-acao="causa" className={`lt-opcoes ${esperado('causa')}`} tabIndex={-1} disabled={!livre}>
                <legend>Qual é a causa? Responda com base no que o terminal mostrou.</legend>
                {chamado.opcoes.map((o) => <label key={o.id}><input type="radio" name={`causa-${chamado.id}`} value={o.id}
                  checked={causa === o.id} onChange={() => { setCausa(o.id); setRetornoCausa('') }} />{o.texto}</label>)}
              </fieldset>
              <button className="gw-primario" disabled={!livre || !causa} onClick={() => executar('diagnosticar', { resposta: causa })}>Confirmar causa</button>
            </> : <p className="lt-causa-ok"><CheckCircle2 size={16} aria-hidden="true" /><span><strong>Causa identificada:</strong> {chamado.opcoes.find((o) => o.id === chamado.resposta)?.texto} Corrija o {NOMES_PC[chamado.pc]} e teste o servidor.</span></p>}
            {retornoCausa && <p className={`lt-retorno ${chamado.correta ? 'ok' : ''}`} role="status">{retornoCausa}</p>}
          </section>}

          {etapaAtual === 'comprovar' && !registrada && <section className="lt-chamado lt-comprovar">
            <header><CheckCircle2 size={18} aria-hidden="true" /><span>TRÊS CHAMADOS RESOLVIDOS</span></header>
            <p>O servidor vai reler a configuração dos três PCs e repetir o ping ao servidor em cada um.</p>
            <button data-acao="concluir" className={`gw-primario ${esperado('concluir')}`} disabled={!livre} onClick={() => executar('validar')}>Validar missão</button>
          </section>}
  </>)

  return (
    <main className={`laboratorio-pagina gateway-lab gw-v2 gw-v3 lt-lab ${foco ? 'gw-foco' : ''}`} aria-busy={ocupado}>
      <nav className="gw-controles" aria-label="Opções de visualização">
        <button aria-pressed={foco} onClick={() => setFoco(!foco)}>{foco ? 'Sair do modo foco' : 'Modo foco'}</button>
        <Link className={esperado('catalogo')} data-acao="catalogo" to="/laboratorios">Voltar aos laboratórios</Link>
      </nav>
      <header className="gw-cabecalho">
        <div><span className="gw-etiqueta">LABORATÓRIO 4 · MESA DE SUPORTE</span><h1>Configure pelo terminal</h1></div>
        <div className="gw-acoes">
          {!registrada && <TempoEValidar tempo={!dados.conflito ? tempo : '--:--'} restantes={dados.conflito ? null : restantes}
            pronta={etapaAtual === 'comprovar' && livre} feitas={etapas.filter((e) => e.concluida).length} total={etapas.length}
            ocupado={ocupado} aoValidar={dados.ativo ? () => executar('validar') : null} />}
        </div>
      </header>
      {avisos}

      <EspacoLaboratorio topologia={painelTopologia} etapas={painelEtapas} orientacao={orientacao}
        chaveEtapa={etapaAtual} aoIrParaAcao={irParaAcao} ajudaAberta={ajudaExpandida} apresentacao="lab4"
        lateral={<section className="gw-painel gw-pratica lt-pratica" aria-label="Atendimento dos chamados">{tarefas}</section>} aoAlternarAjuda={() => setAjudaExpandida(!ajudaExpandida)}
        tutor={{
          imagem: registrada ? POSES.comemorando : linkOcupado ? POSES.pensativo
            : etapaAtual === 'comprovar' ? POSES.incentivando : POSES.investigando,
          mensagem: registrada ? 'Os três chamados foram resolvidos. Você pode rever os resultados.' : 'Ficou em dúvida sobre um comando ou uma mensagem do terminal? Pergunte.',
          conteudo: <ConversaLink mensagens={mensagensLink} aoPerguntar={perguntarAoLink} ocupado={linkOcupado} disponivel={ativo} erro={erroLink} />,
        }}>
        <section className="gw-painel gw-pratica lt-pratica" aria-label="Prática">
          <section className="lt-terminal" aria-label={`Terminal do ${NOMES_PC[aba]}`}>
            <div className="lt-abas" role="tablist" aria-label="Computadores">
              {PCS.map((pc) => <button key={pc} type="button" role="tab" aria-selected={aba === pc} data-acao={`aba-${pc}`}
                className={`${aba === pc ? 'ativa' : ''} ${esperado(`aba-${pc}`)}`} onClick={() => trocarAba(pc)}>
                {NOMES_PC[pc]}{chamado?.pc === pc && !registrada && <i>chamado</i>}
              </button>)}
            </div>
            <div className="lt-tela" ref={saida} role="log" aria-live="polite" aria-label="Saída do terminal" onClick={() => campo.current?.focus()}>
              {linhas.length === 0 && <p className="lt-boasvindas">{HOSTS[aba]} · interface eth0 · comandos disponíveis: ip addr, ip route e ping</p>}
              {linhas.map((h) => <div key={h.revisao} className="lt-linha">
                <div className="lt-cmd"><span className="lt-ps1">suporte@{HOSTS[h.pc]}:~$</span> {h.digitado}</div>
                {h.saida && <pre className={h.codigo === 0 ? '' : 'lt-erro'}>{h.saida}</pre>}
                {h.confirmacao && <p className="lt-confirmacao">✓ comando aplicado · {h.confirmacao}</p>}
              </div>)}
              {erroTerminal && <p className="lt-recusado" role="alert">{erroTerminal}</p>}
              {!registrada && <form className={`lt-entrada ${esperado('comando')}`} onSubmit={enviarComando}>
                <label htmlFor="lt-comando" className="lt-ps1">suporte@{HOSTS[aba]}:~$</label>
                <input data-acao="comando" ref={campo} id="lt-comando" value={comando}
                  aria-label={`Comando no ${NOMES_PC[aba]}`}
                  onChange={(e) => { setComando(e.target.value); setErroTerminal('') }} onKeyDown={navegarHistorico}
                  disabled={!livre} autoComplete="off" spellCheck={false} autoCapitalize="none" maxLength={100} autoFocus />
              </form>}
            </div>
            <p className="lt-dica">Enter executa · ↑ e ↓ repetem comandos{ocupado && operacao === 'terminal' ? ` · aguardando o ${NOMES_PC[aba]}…` : ''}</p>
          </section>

          <section className="lt-estado" aria-label={`Estado lido do ${NOMES_PC[aba]}`}>
            <span><strong>{NOMES_PC[aba]}</strong> · lido do computador depois de cada comando</span>
            <span><b>eth0</b> {estados[aba]?.enderecos?.length ? estados[aba].enderecos.join(', ') : 'sem endereço IPv4'}</span>
            <span><b>rota padrão</b> {estados[aba]?.rota_padrao ? `via ${estados[aba].rota_padrao}` : 'nenhuma'}</span>
            <span><b>servidor</b> <em className={testes[aba]?.[SERVIDOR] === true ? 'ok' : testes[aba]?.[SERVIDOR] === false ? 'falhou' : ''}>
              {testes[aba]?.[SERVIDOR] === true ? 'respondeu' : testes[aba]?.[SERVIDOR] === false ? 'não respondeu' : 'não testado'}</em></span>
          </section>
          <BastidoresTshark capturas={dados?.bastidores} nomeNo={(pc) => NOMES_PC[pc] || pc} nomeIp={nomeIp} />
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

export default function LaboratorioTerminal() {
  const { usuario } = useAuth()
  return <SessaoTerminal key={usuario?.id || usuario?.login || 'sem-sessao'} />
}
