import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Check, CheckCircle2, Circle, Clock3, Computer, LoaderCircle,
  MessageCircleQuestion, Minimize2, Network, Play, Send,
  SquareTerminal, StopCircle, Trophy,
} from 'lucide-react'
import linkObservando from '../assets/mascote/link-expansao-v1/link-observando-rede.webp'
import linkRecebendoXp from '../assets/mascote/link-expansao-v1/link-recebendo-xp.webp'
import BastidoresRede from '../components/laboratorio/BastidoresRede'
import linkAvatar from '../assets/mascote/link-kit-v2/link-v2-avatar-128.webp'
import './Laboratorio.css'
import './LaboratorioResponsivo.css'

const MISSAO_INICIAL = {
  titulo: 'Missão: Primeiro Contato', descricao: 'Carregando a missão...', xp: 100,
  nos: [], etapas: [], evidencias: [], proxima_etapa: null, concluido: false,
}

async function chamarApi(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, { credentials: 'same-origin', ...opcoes })
  const dados = await resposta.json().catch(() => ({}))
  if (!resposta.ok || dados.sucesso === false) {
    const erro = new Error(dados.mensagem || 'Não foi possível concluir a operação.')
    erro.dados = dados
    throw erro
  }
  return dados
}

function formatarTempo(segundos) {
  const total = Math.max(0, Number(segundos || 0))
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function Laboratorio() {
  // RESPONSIVO: INICIO estados de apresentação
  const [modoFoco, setModoFoco] = useState(false)
  const areaPraticaRef = useRef(null)
  const [alturaPratica, setAlturaPratica] = useState(null)
  const [mostrarBastidores, setMostrarBastidores] = useState(true)
  // RESPONSIVO: FIM estados de apresentação
  const navigate = useNavigate()
  const [ativo, setAtivo] = useState(false)
  const [outroLaboratorio, setOutroLaboratorio] = useState(null)
  const [missao, setMissao] = useState(MISSAO_INICIAL)
  const [segundosRestantes, setSegundosRestantes] = useState(0)
  const [nodeId, setNodeId] = useState(1)
  const [comandos, setComandos] = useState({ 1: '', 2: '' })
  const [historicos, setHistoricos] = useState({ 1: [], 2: [] })
  const [carregando, setCarregando] = useState(true)
  const [processando, setProcessando] = useState(false)
  const [aviso, setAviso] = useState({ texto: '', erro: false })
  const [tutorAberto, setTutorAberto] = useState(false)
  const [pergunta, setPergunta] = useState('')
  const [mensagensTutor, setMensagensTutor] = useState([])
  const [conclusao, setConclusao] = useState(null)
  const [bastidores, setBastidores] = useState(null)
  const [capturando, setCapturando] = useState(false)
  const capturandoRef = useRef(false)
  const terminalRef = useRef(null)
  const tutorRef = useRef(null)
  const prazoRef = useRef(null)
  const [tempoSessao, setTempoSessao] = useState(null)
  const [avisoExtensao, setAvisoExtensao] = useState(null)
  const sessionIdRef = useRef(null)
  const avisosTempoRef = useRef(new Set())
  const encerrandoPorTempoRef = useRef(false)

  // RESPONSIVO: INICIO dimensionamento de apresentação
  // Dimensiona pelo espaço realmente restante, inclusive com o menu expandido.
  useEffect(() => {
    const area = areaPraticaRef.current
    if (!area) return undefined
    let frame = null
    let montado = true
    const medir = () => {
      if (!montado) return
      const topo = area.getBoundingClientRect().top + window.scrollY
      setAlturaPratica(Math.max(180, Math.floor(window.innerHeight - topo - 12)))
    }
    const agendar = () => {
      if (frame !== null) cancelAnimationFrame(frame)
      frame = requestAnimationFrame(medir)
    }
    const observer = new ResizeObserver(agendar)
    const principal = area.closest('.lab-responsivo')
    for (const seletor of ['.responsivo-layout-controles', '.lab-cabecalho', '.lab-topologia-painel']) {
      const elemento = principal.querySelector(seletor)
      if (elemento) observer.observe(elemento)
    }
    const topo = document.querySelector('.topbar')
    if (topo) observer.observe(topo)
    window.addEventListener('resize', agendar)
    document.fonts.ready.then(() => { if (montado) agendar() })
    agendar()
    return () => { montado = false; observer.disconnect(); window.removeEventListener('resize', agendar); if (frame !== null) cancelAnimationFrame(frame) }
  }, [carregando, modoFoco, mostrarBastidores, aviso.texto, avisoExtensao])

  // RESPONSIVO: FIM dimensionamento de apresentação
  const etapasConcluidas = useMemo(
    () => missao.etapas.filter((etapa) => etapa.concluida).length,
    [missao.etapas],
  )
  const progresso = missao.etapas.length
    ? Math.round((etapasConcluidas / missao.etapas.length) * 100) : 0
  const etapaAtual = missao.etapas.find((etapa) => etapa.id === missao.proxima_etapa)
  const etapasFeitas = missao.etapas.filter((etapa) => etapa.concluida).length
  const historicoAtual = historicos[nodeId] || []
  const comandoAtual = comandos[nodeId] || ''
  const nosOrdenados = useMemo(() => {
    const ordem = [1, 3, 2]
    return ordem
      .map((id) => missao.nos.find((no) => no.id === id))
      .filter(Boolean)
  }, [missao.nos])

  function aplicarStatus(dados) {
    if (dados.ativo && dados.laboratorio?.laboratorio_id && dados.laboratorio.laboratorio_id !== 'primeiro-contato') {
      setOutroLaboratorio(dados.laboratorio.laboratorio_id)
      setAtivo(false); setTempoSessao(null); prazoRef.current = null
      return
    }
    setOutroLaboratorio(null)
    setAtivo(Boolean(dados.ativo))
    if (dados.ativo && dados.laboratorio) {
      const laboratorio = dados.laboratorio
      const sessaoAtual = String(laboratorio.session_id)
      if (sessionIdRef.current !== sessaoAtual) {
        sessionIdRef.current = sessaoAtual
        avisosTempoRef.current = new Set()
        setAvisoExtensao(null)
      }
      setTempoSessao(laboratorio)
      const agoraLocal = Date.now()
      const temPrazoServidor = Number.isFinite(laboratorio.prazo)
        && Number.isFinite(laboratorio.agora)
      if (temPrazoServidor) {
        prazoRef.current = agoraLocal
          + Math.max(0, laboratorio.prazo - laboratorio.agora) * 1000
      } else {
        // Compatibilidade enquanto o backend em execução usa a API anterior.
        const sessao = String(laboratorio.session_id)
        const sessaoSalva = sessionStorage.getItem('pinglevel:lab:sessao')
        const prazoSalvo = Number(sessionStorage.getItem('pinglevel:lab:prazo'))
        const segundos = Number.isFinite(laboratorio.segundos_restantes)
          ? laboratorio.segundos_restantes : 300
        prazoRef.current = sessaoSalva === sessao
          && Number.isFinite(prazoSalvo) && prazoSalvo > 0
          ? prazoSalvo : agoraLocal + Math.max(0, segundos) * 1000
      }
      sessionStorage.setItem('pinglevel:lab:sessao', String(laboratorio.session_id))
      sessionStorage.setItem('pinglevel:lab:prazo', String(prazoRef.current))
      setSegundosRestantes(Math.max(
        0,
        Math.ceil((prazoRef.current - Date.now()) / 1000),
      ))
    } else {
      setTempoSessao(null)
      sessionIdRef.current = null
      avisosTempoRef.current = new Set()
      setAvisoExtensao(null)
      sessionStorage.removeItem('pinglevel:lab:sessao')
      sessionStorage.removeItem('pinglevel:lab:prazo')
      prazoRef.current = null
      setSegundosRestantes(0)
    }
    if (!dados.ativo) setBastidores(null)
    else if (!capturandoRef.current && Object.hasOwn(dados, 'bastidores')) {
      setBastidores(dados.bastidores)
    }
    if (dados.missao) setMissao(dados.missao)
  }

  async function consultarStatus(silencioso = false) {
    try {
      aplicarStatus(await chamarApi('/api/status'))
      if (!silencioso) setAviso({ texto: '', erro: false })
    } catch (erro) {
      if (!silencioso) setAviso({ texto: erro.message, erro: true })
    } finally {
      if (!silencioso) setCarregando(false)
    }
  }

  useEffect(() => {
    consultarStatus()
    const intervalo = window.setInterval(() => consultarStatus(true), 10000)
    return () => window.clearInterval(intervalo)
  }, [])

  useEffect(() => {
    if (!ativo) return undefined
    const relogio = window.setInterval(() => {
      const restantes = prazoRef.current
        ? Math.max(0, Math.ceil((prazoRef.current - Date.now()) / 1000))
        : 0
      setSegundosRestantes(restantes)
    }, 1000)
    return () => window.clearInterval(relogio)
  }, [ativo])

  useEffect(() => {
    if (!ativo || !tempoSessao?.pode_estender || segundosRestantes <= 0) return
    if (segundosRestantes <= 15 && !avisosTempoRef.current.has('fechando')) {
      avisosTempoRef.current.add('fechando')
      setAvisoExtensao('fechando')
    } else if (segundosRestantes <= 60 && !avisosTempoRef.current.has('minuto')) {
      avisosTempoRef.current.add('minuto')
      setAvisoExtensao('minuto')
    }
  }, [ativo, segundosRestantes, tempoSessao?.pode_estender])

  useEffect(() => {
    if (!ativo || segundosRestantes > 0 || !prazoRef.current || encerrandoPorTempoRef.current) {
      return
    }
    encerrandoPorTempoRef.current = true
    chamarApi('/api/status')
      .then((dados) => {
        aplicarStatus(dados)
        if (!dados.ativo) {
          setAviso({ texto: 'O tempo terminou e o laboratório foi encerrado.', erro: false })
        }
      })
      .catch((erro) => setAviso({ texto: erro.message, erro: true }))
      .finally(() => { encerrandoPorTempoRef.current = false })
  }, [ativo, segundosRestantes])

  useEffect(() => {
    setNodeId(1)
  }, [missao.proxima_etapa])

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight
  }, [historicoAtual])

  useEffect(() => {
    if (tutorRef.current) tutorRef.current.scrollTop = tutorRef.current.scrollHeight
  }, [mensagensTutor])

  async function iniciar() {
    setProcessando(true)
    setAviso({ texto: 'Preparando sua sessão CORE...', erro: false })
    try {
      await chamarApi('/api/iniciar', { method: 'POST' })
      await consultarStatus(true)
      setBastidores(null)
      setHistoricos({ 1: [], 2: [] })
      setMensagensTutor([])
      setAviso({ texto: 'Ambiente pronto. Comece identificando o Computador 1.', erro: false })
    } catch (erro) {
      setAviso({ texto: erro.message, erro: true })
      if (erro.dados?.ativo) await consultarStatus(true)
    } finally { setProcessando(false) }
  }

  async function estender() {
    setProcessando(true)
    try {
      const dados = await chamarApi('/api/estender', { method: 'POST' })
      avisosTempoRef.current = new Set(['minuto', 'fechando'])
      setAvisoExtensao(null)
      aplicarStatus(dados)
      setAviso({ texto: dados.mensagem, erro: false })
    } catch (erro) {
      setAviso({ texto: erro.message, erro: true })
      await consultarStatus(true)
    } finally { setProcessando(false) }
  }

  async function executar(evento) {
    evento.preventDefault()
    const atual = comandoAtual.trim()
    if (!ativo || !atual || processando) return
    const observar = /^ping(?:\s|$)/.test(atual)
    if (observar && missao.aprendizagem && !missao.aprendizagem.previsao) {
      setAviso({ texto: 'Registre sua previsão nos Bastidores antes de executar o ping.', erro: false })
      return
    }
    capturandoRef.current = observar
    setCapturando(observar)
    setProcessando(true)
    setAviso({ texto: '', erro: false })
    setHistoricos((atuais) => ({
      ...atuais,
      [nodeId]: [...(atuais[nodeId] || []), { tipo: 'comando', texto: atual }],
    }))
    setComandos((valores) => ({ ...valores, [nodeId]: '' }))
    try {
      const dados = await chamarApi('/api/comando', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, comando: atual }),
      })
      setHistoricos((atuais) => ({
        ...atuais,
        [nodeId]: [...(atuais[nodeId] || []), {
          tipo: dados.codigo === 0 ? 'saida' : 'erro',
          texto: dados.saida || dados.mensagem,
        }],
      }))
      if (observar) setBastidores(dados.bastidores || null)
      if (dados.missao) setMissao(dados.missao)
    } catch (erro) {
      if (erro.dados?.bastidores) setBastidores(erro.dados.bastidores)
      setHistoricos((atuais) => ({
        ...atuais,
        [nodeId]: [...(atuais[nodeId] || []), { tipo: 'erro', texto: erro.message }],
      }))
    } finally {
      capturandoRef.current = false
      setCapturando(false)
      setProcessando(false)
    }
  }

  async function responderAprendizagem(fase, resposta) {
    setProcessando(true)
    try {
      const dados = await chamarApi('/api/aprendizagem', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fase, resposta }),
      })
      if (dados.missao) setMissao(dados.missao)
      setAviso({ texto: '', erro: false })
    } catch (erro) {
      setAviso({ texto: erro.message, erro: true })
    } finally { setProcessando(false) }
  }

  async function validar() {
    setProcessando(true)
    try {
      const dados = await chamarApi('/api/validar', { method: 'POST' })
      if (dados.missao) setMissao(dados.missao)
      setConclusao({ xp: dados.xp_concedido, mensagem: dados.mensagem })
    } catch (erro) {
      if (erro.dados?.missao) setMissao(erro.dados.missao)
      setAviso({ texto: erro.message, erro: true })
    } finally { setProcessando(false) }
  }

  async function encerrar() {
    setProcessando(true)
    try {
      const dados = await chamarApi('/api/encerrar', { method: 'POST' })
      aplicarStatus({ ativo: false })
      setAviso({ texto: dados.mensagem, erro: false })
    } catch (erro) { setAviso({ texto: erro.message, erro: true })
    } finally { setProcessando(false) }
  }

  async function concluirEVoltar() {
    if (processando) return
    setProcessando(true)
    try {
      if (ativo) {
        await chamarApi('/api/encerrar', { method: 'POST' })
      }
      aplicarStatus({ ativo: false })
      setConclusao(null)
      navigate('/')
    } catch (erro) {
      setConclusao(null)
      setAviso({
        texto: `A missão foi concluída, mas o ambiente não pôde ser encerrado: ${erro.message}`,
        erro: true,
      })
    } finally {
      setProcessando(false)
    }
  }

  async function perguntarTutor(evento) {
    evento.preventDefault()
    const texto = pergunta.trim()
    if (!texto || processando) return
    const horario = new Intl.DateTimeFormat('pt-BR', {
      hour: '2-digit', minute: '2-digit',
    }).format(new Date())
    setMensagensTutor((atuais) => [
      ...atuais,
      { tipo: 'aluno', texto, horario },
    ])
    setPergunta('')
    setProcessando(true)
    try {
      const dados = await chamarApi('/api/tutor', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, pergunta: texto }),
      })
      setMensagensTutor((atuais) => [
        ...atuais,
        {
          tipo: 'link',
          texto: dados.resposta,
          fonte: dados.fonte,
          horario,
        },
      ])
    } catch (erro) {
      setMensagensTutor((atuais) => [
        ...atuais,
        { tipo: 'erro', texto: erro.message, horario },
      ])
    } finally { setProcessando(false) }
  }

  if (carregando) return (
    <main className="lab-carregando"><LoaderCircle size={28} className="girando" /> Carregando laboratório...</main>
  )

  if (outroLaboratorio) return <main className="principal pagina-aula"><h1>Outra missão está em execução</h1><p>Seu ambiente foi preservado. Os controles do Primeiro Contato não vão operar a sessão de outro laboratório.</p><button className="botao-interacao" onClick={() => navigate(outroLaboratorio === 'saindo-da-rede-local' ? '/laboratorios/saindo-da-rede-local' : '/laboratorios/primeira-lan')}>{outroLaboratorio === 'saindo-da-rede-local' ? 'Abrir Saindo da rede local' : 'Abrir Monte sua primeira LAN'}</button></main>

  return (
    <main className={`laboratorio-pagina lab-responsivo ${modoFoco ? 'lab-responsivo-foco' : ''} ${mostrarBastidores ? '' : 'sem-bastidores'}`}>
      <nav className="responsivo-layout-controles" aria-label="Opções de visualização">
        <button type="button" onClick={() => setModoFoco((v) => !v)} aria-pressed={modoFoco}>{modoFoco ? 'Sair do modo foco' : 'Modo foco'}</button>
        <button type="button" onClick={() => setMostrarBastidores((v) => !v)} aria-expanded={mostrarBastidores}>{mostrarBastidores ? 'Ocultar Bastidores' : 'Mostrar Bastidores'}</button>
      </nav>
      <section className="lab-cabecalho">
        <div><span>LABORATÓRIO · PRIMEIRO CONTATO</span>
          <h1><span className="responsivo-titulo-completo">Descubra como os computadores se comunicam.</span><span className="responsivo-titulo-curto">Primeiro Contato</span></h1><p>{missao.descricao}</p></div>
        <div className="lab-cabecalho-acoes">
          <div className={`lab-tempo ${ativo ? 'ativo' : ''} ${ativo && segundosRestantes <= 60 ? 'critico' : ativo && segundosRestantes <= 120 ? 'alerta' : ''}`}><Clock3 size={24} />
            <div><strong>{ativo ? formatarTempo(segundosRestantes) : '--:--'}</strong>
              <span>{ativo ? 'tempo restante' : 'ambiente desligado'}</span></div>
          </div>
          <div className="lab-acoes-superiores">
            {!ativo ? <button className="lab-acao-principal" onClick={iniciar} disabled={processando}>
              {processando ? <LoaderCircle size={18} className="girando" /> : <Play size={18} />}
              Iniciar laboratório
            </button> : <>
              <button className={`lab-acao-principal lab-validar ${missao.concluido ? 'pronta' : ''}`} onClick={validar}
                disabled={!missao.concluido || processando}>
                <CheckCircle2 size={20} />
                <span>Validar missão<small>{missao.concluido ? 'Clique para registrar o XP'
                  : `Conclua as etapas (${etapasFeitas} de ${missao.etapas.length})`}</small></span>
              </button>
              {tempoSessao?.pode_estender && <button className="lab-acao-secundaria"
                onClick={estender} disabled={processando || segundosRestantes <= 0}>
                <Clock3 size={16} /> +{formatarTempo(tempoSessao.tempo_extensao)}
              </button>}
              <button className="lab-acao-secundaria" onClick={encerrar} disabled={processando}>
                <StopCircle size={16} /> Encerrar
              </button>
            </>}
          </div>
        </div>
      </section>

      {aviso.texto && <div className={`lab-aviso ${aviso.erro ? 'erro' : ''}`} role={aviso.erro ? 'alert' : 'status'}>{aviso.texto}</div>}

      {ativo && avisoExtensao && tempoSessao?.pode_estender && (
        <section className="lab-aviso-tempo" role="alertdialog" aria-labelledby="lab-aviso-tempo-titulo">
          <div><span>{avisoExtensao === 'minuto' ? 'FALTA 1 MINUTO' : 'O TEMPO ESTÁ ACABANDO'}</span>
            <h2 id="lab-aviso-tempo-titulo">Quer mais 3 minutos para concluir?</h2>
            <p>Você ainda tem uma extensão disponível. O laboratório continuará ativo se preferir seguir com o tempo atual.</p>
          </div>
          <div className="lab-aviso-tempo-acoes">
            <button type="button" className="lab-acao-principal" onClick={estender} disabled={processando}>
              <Clock3 size={16} /> {processando ? 'Estendendo…' : 'Adicionar 3 minutos'}
            </button>
            <button type="button" className="lab-acao-secundaria" onClick={() => setAvisoExtensao(null)}>
              Continuar sem estender
            </button>
          </div>
        </section>
      )}

      <div className="lab-grade">
        <div className="lab-area-pratica">
          <section className="lab-painel lab-topologia-painel responsivo-faixa-missao" aria-label="Progresso e topologia da missão">
            <div className="responsivo-progresso-integrado">
              <div className="responsivo-progresso-linha"><span>PROGRESSO DA MISSÃO</span><strong>{etapasConcluidas} de {missao.etapas.length} etapas</strong></div>
              <div className="lab-progresso" role="progressbar" aria-label="Progresso da missão" aria-valuenow={progresso} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progresso}%` }} /></div>
              <div className="responsivo-etapa-integrada" aria-live="polite"><span className="responsivo-etapa-numero">{missao.concluido ? <Check size={15} /> : missao.etapas.findIndex((e) => e.id === missao.proxima_etapa) + 1}</span><div><small>ETAPA ATUAL</small><strong>{missao.etapas.find((e) => e.id === missao.proxima_etapa)?.titulo || 'Missão concluída'}</strong></div></div>
              <div className="responsivo-progresso-inferior"><button type="button" popoverTarget="responsivo-etapas">Ver etapas <span aria-hidden="true">⌄</span></button><b><Trophy size={13} /> {missao.xp} XP</b></div>
            </div>
            <div className="responsivo-topologia-centro"><span className="responsivo-rede-legenda">TOPOLOGIA · REDE LOCAL</span>
            <div className={`lab-topologia ${ativo ? 'ativa' : ''}`}>
              {nosOrdenados.map((no, indice) => {
                const Icone = no.tipo === 'switch' ? Network : Computer
                return <div className="lab-no-grupo" key={no.id}>
                  {indice > 0 && <span className="lab-enlace" />}
                  <button type="button" className={`lab-no ${nodeId === no.id ? 'selecionado' : ''}`}
                    disabled={no.tipo === 'switch'} onClick={() => setNodeId(no.id)}>
                    <Icone size={25} /><strong>{no.nome}</strong>
                    <small className={no.ip ? 'lab-ip-no' : ''}>
                      {no.ip ? <><span>IPv4</span>{no.ip}/{no.prefixo}</> : 'Conexão da rede'}
                    </small>
                  </button></div>
              })}
            </div></div>
            <button className="responsivo-ajuda-integrada" type="button" onClick={() => setTutorAberto(true)} disabled={!ativo} aria-label="Conversar com o Link"><img src={linkAvatar} alt="" /><span><strong>Precisa de ajuda?</strong><small>Perguntar ao Link</small></span></button>
          </section>

          {/* "Agora faça": a orientação da etapa atual fica sempre à vista, logo acima do terminal. */}
          <section className={`lab1-agora ${ativo && missao.concluido ? 'pronta' : ''}`} aria-live="polite"><span>{ativo && missao.concluido ? 'MISSÃO CUMPRIDA' : 'AGORA FAÇA'}</span>
            <p>{!ativo ? 'Clique em Iniciar laboratório para ligar a rede.'
              : missao.concluido ? 'Missão cumprida! Clique em Validar missão para registrar seu XP.'
                : etapaAtual?.orientacao || 'Execute o comando da etapa atual.'}
              {ativo && !missao.concluido && etapaAtual && <small>Etapa {missao.etapas.indexOf(etapaAtual) + 1} de {missao.etapas.length} · {etapaAtual.titulo}</small>}</p>
            {ativo && missao.concluido && <button className="lab-acao-principal lab-validar pronta" onClick={validar} disabled={processando}>
              <CheckCircle2 size={20} /> Validar missão</button>}
          </section>

          <div className="lab-experimento" ref={areaPraticaRef} style={alturaPratica === null ? undefined : { height: `${alturaPratica}px` }}>
          <section className="lab-painel lab-terminal-painel">
            <header className="lab-terminal-cabecalho"><SquareTerminal size={17} />
              <strong>Terminal · {missao.nos.find((no) => no.id === nodeId)?.nome || 'Computador 1'}</strong>
              <span>{ativo ? 'SSH protegido' : 'Indisponível'}</span>
            </header>
            <div className="lab-terminal-saida" ref={terminalRef}>
              {!historicoAtual.length && <p className="lab-terminal-vazio">{ativo
                ? 'O terminal está pronto. Execute o comando da etapa atual.'
                : 'Inicie o laboratório para liberar o terminal.'}</p>}
              {historicoAtual.map((item, indice) => <pre key={`${item.tipo}-${indice}`} className={item.tipo}>
                {item.tipo === 'comando' && <span>aluno@computador-{nodeId}:~$ </span>}{item.texto}
              </pre>)}
            </div>
            <form className="lab-comando" onSubmit={executar}><input value={comandoAtual}
              onChange={(evento) => setComandos((valores) => ({
                ...valores, [nodeId]: evento.target.value,
              }))} disabled={!ativo || processando}
              placeholder={ativo ? 'Digite um comando...' : 'Terminal bloqueado'} aria-label="Comando do terminal" />
              <button disabled={!ativo || !comandoAtual.trim() || processando}><Play size={17} /> Executar</button></form>
          </section>

          <div className="responsivo-bastidores-host" hidden={!mostrarBastidores}><BastidoresRede captura={bastidores} capturando={capturando} ativo={ativo}
            aprendizagem={missao.aprendizagem} processando={processando}
            onResponder={responderAprendizagem} sessao={tempoSessao?.session_id} /></div>
          </div>


        </div>

        {tutorAberto && <aside className="lab-missao-painel aberto">
            <section className="lab-link-guia">
              <img src={linkObservando} alt="Link, tutor do PingLevel" />
              <div>
                <span>LINK · TUTOR DA MISSÃO</span>
                <h2>Vamos descobrir juntos?</h2>
                <p>Faça sua pergunta sobre a etapa atual. Eu ajudo com pistas sem entregar a resposta.</p>
              </div>
              <button className="lab-minimizar-tutor" type="button"
                onClick={() => setTutorAberto(false)}
                aria-label="Minimizar conversa com o Link"
                title="Minimizar conversa">
                <Minimize2 size={18} />
              </button>
            </section>

            <div className="lab-tutor">
            <div className="lab-tutor-conversa" ref={tutorRef} aria-live="polite">
              {!mensagensTutor.length && <div className="lab-tutor-vazio">
                <MessageCircleQuestion size={23} />
                <strong>Estou acompanhando esta etapa.</strong>
                <p>Conte o que você observou ou onde encontrou dificuldade.</p>
              </div>}
              {mensagensTutor.map((mensagem, indice) => (
                <article className={`lab-mensagem ${mensagem.tipo}`} key={`${mensagem.tipo}-${indice}`}>
                  <header>
                    <strong>{mensagem.tipo === 'aluno' ? 'Sua pergunta' : mensagem.tipo === 'link' ? 'Resposta do Link' : 'Não foi possível responder'}</strong>
                    <time>{mensagem.horario}</time>
                  </header>
                  <p>{mensagem.texto}</p>
                  {mensagem.fonte && <small>Fonte: {mensagem.fonte}</small>}
                </article>
              ))}
              {processando && mensagensTutor.at(-1)?.tipo === 'aluno' && (
                <div className="lab-tutor-digitando"><LoaderCircle size={15} className="girando" /> Link está pensando...</div>
              )}
            </div>
            <form onSubmit={perguntarTutor}><textarea value={pergunta} maxLength={500}
              disabled={!ativo || processando}
              onChange={(evento) => setPergunta(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === 'Enter' && !evento.shiftKey) {
                  evento.preventDefault()
                  evento.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder={ativo ? 'Digite sua pergunta...' : 'Inicie o laboratório para conversar'} />
              <button disabled={!ativo || !pergunta.trim() || processando} aria-label="Enviar pergunta"><Send size={16} /></button></form>
            </div>
        </aside>}
      </div>

      <div id="responsivo-etapas" popover="auto" className="responsivo-etapas-popover" role="dialog" aria-labelledby="responsivo-etapas-titulo">
        <header><h2 id="responsivo-etapas-titulo">Etapas da missão</h2><button type="button" popoverTarget="responsivo-etapas" popoverTargetAction="hide" aria-label="Fechar etapas">Fechar</button></header>
<ol className="lab-etapas">{missao.etapas.map((etapa, indice) => {
              const atual = etapa.id === missao.proxima_etapa
              const local = etapa.id === 'conectividade'
                ? 'Do Computador 1 para o Computador 2'
                : 'Execute no Computador 1'
              return <li key={etapa.id} className={`${etapa.concluida ? 'concluida' : ''} ${atual ? 'atual' : ''}`}>
                <div className="lab-etapa-icone">{etapa.concluida ? <Check size={16} /> : atual ? <Circle size={13} /> : indice + 1}</div>
                <div><span>{atual ? 'ETAPA ATUAL' : `ETAPA ${indice + 1}`}</span><h3>{etapa.titulo}</h3>
                  <strong className="lab-local-execucao">{local}</strong>
                  {(atual || etapa.concluida) && <p>{etapa.orientacao}</p>}
                  {atual && !etapa.concluida && <button type="button" className="lab-botao-dica"
                    disabled={!ativo} popoverTarget="responsivo-etapas" popoverTargetAction="hide" onClick={() => setTutorAberto(true)}>
                    Pedir orientação ao Link
                  </button>}
                  {!atual && !etapa.concluida && <p className="lab-etapa-bloqueada">
                    Conclua a etapa anterior para liberar.
                  </p>}
                </div>
              </li>
            })}</ol>
      </div>

      {conclusao && <div className="lab-modal-fundo" role="dialog" aria-modal="true" aria-labelledby="lab-conclusao-titulo">
        <section className="lab-modal"><img className="lab-link-xp" src={linkRecebendoXp}
          alt="Link comemorando a conquista" /><span>MISSÃO CONCLUÍDA</span>
          <h2 id="lab-conclusao-titulo">Primeiro Contato completo!</h2><p>{conclusao.mensagem}</p>
          <strong>{conclusao.xp > 0 ? `+${conclusao.xp} XP` : 'Conclusão já registrada'}</strong>
          <button onClick={concluirEVoltar} disabled={processando}>
            {processando ? 'Encerrando ambiente...' : 'Voltar para a jornada'}
          </button></section>
      </div>}
    </main>
  )
}

export default Laboratorio
