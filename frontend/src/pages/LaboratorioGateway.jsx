import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Computer, Network, Router, Server, LockKeyhole, CheckCircle2, ArrowRight, Terminal } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { criarClienteGateway, validarGateway, validarComandoPing } from '../services/gatewayGuiado'
import linkObservando from '../assets/mascote/link-expansao-v1/link-observando-rede.webp'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import linkConectando from '../assets/mascote/link-expansao-v1/link-conectando.webp'
import ConversaLink from '../components/laboratorio/ConversaLink'
import TempoEValidar from '../components/laboratorio/TempoEValidar'
import EspacoLaboratorio from '../components/laboratorio/EspacoLaboratorio'
import IconeRoteador from '../components/laboratorio/IconeRoteador'
import { orientarGateway } from '../services/orientacaoGateway'
import './Laboratorio.css'
import './LaboratorioResponsivo.css'
import './LaboratorioGateway.css'
import BastidoresTshark from '../components/laboratorio/BastidoresTshark'

const api = criarClienteGateway()

function SessaoGateway() {
  const [dados, setDados] = useState(null)
  const [gateway, setGateway] = useState('')
  const [sujo, setSujo] = useState(false)
  const [hipotese, setHipotese] = useState({ local: '', remota: '' })
  const [resposta, setResposta] = useState('')
  const [operacao, setOperacao] = useState('status')
  const [aviso, setAviso] = useState('')
  const [recuperacao, setRecuperacao] = useState(false)
  const [prazo, setPrazo] = useState(null)
  const [agora, setAgora] = useState(Date.now)
  const [xp, setXp] = useState(null)
  const [foco, setFoco] = useState(true)
  const [bastidores, setBastidores] = useState(false)
  const [mensagensLink, setMensagensLink] = useState([])
  const [linkOcupado, setLinkOcupado] = useState(false)
  const [erroLink, setErroLink] = useState('')
  const estadoAtual = useRef(null)
  const linkPendente = useRef(false)
  const [ajudaExpandida, setAjudaExpandida] = useState(false)
  const [consulta, setConsulta] = useState(null)
  const [comando, setComando] = useState('')
  const [erroTerminal, setErroTerminal] = useState('')
  const [terminalAberto, setTerminalAberto] = useState(false)
  const [alvoTerminal, setAlvoTerminal] = useState(2)
  const [inspecionarPc, setInspecionarPc] = useState(false)
  const campoTerminal = useRef(null)
  const [classificacao, setClassificacao] = useState('')
  const [pcSelecionado, setPcSelecionado] = useState(1)
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
  const mesmoGateway = !sujo && missao?.gateway?.confirmado === true && gateway === missao.gateway.valor
  const localPronto = missao?.antes?.registrado && missao.antes.local === true
  const redePronta = missao?.classificacao?.correta === true
  const depoisValido = mesmoGateway && missao?.conferencia?.ok && missao?.depois?.registrado && missao.depois.local === true && missao.depois.remoto === true && missao.depois.rota_confirmada === true
  const podeConcluir = livre && depoisValido && missao?.interpretacao?.correta === true && resposta === missao.interpretacao.resposta
  const pc1 = missao?.nos?.find((n) => n.id === 1)
  const etapa = missao?.etapas?.find((e) => e.id === missao.proxima_etapa)
  // Conclusão persistida é autoritativa mesmo sem histórico da sessão já removida.
  const etapas = (missao?.etapas || []).map((e) => registrada ? { ...e, concluida: true } : e)

  function receber(retorno, preencher = false) {
    if (retorno.missao?.id !== 'saindo-da-rede-local' || typeof retorno.ativo !== 'boolean' || !Number.isInteger(retorno.missao.revisao)
      || (retorno.ativo && (!Number.isInteger(retorno.laboratorio?.session_id) || retorno.laboratorio.session_id <= 0))) {
      throw new Error('O servidor não confirmou o estado deste laboratório.')
    }
    estadoAtual.current = retorno
    setDados(retorno)
    setMensagensLink(Array.isArray(retorno.tutoria) ? retorno.tutoria : [])
    const lab = retorno.laboratorio
    const segundos = Number.isFinite(lab?.prazo) && Number.isFinite(lab?.agora) ? lab.prazo - lab.agora : lab?.segundos_restantes
    setPrazo(retorno.ativo && retorno.conclusao?.registrada !== true && Number.isFinite(segundos) ? Date.now() + Math.max(0, segundos) * 1000 : null)
    setAgora(Date.now())
    if (preencher) {
      setGateway(retorno.missao.gateway?.valor || '')
      setSujo(false)
      setHipotese({ local: retorno.missao.previsao?.local || '', remota: retorno.missao.previsao?.remota || '' })
      setResposta(retorno.missao.interpretacao?.resposta || '')
      setClassificacao(retorno.missao.classificacao?.resposta || '')
      setComando('')
      setErroTerminal('')
      setTerminalAberto(false)
      setAlvoTerminal(2)
      setInspecionarPc(false)
      setConsulta(null)
      setErroLink('')
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    vida.current = controller
    api.status({}, { signal: controller.signal }).then((retorno) => {
      if (!controller.signal.aborted) receber(retorno, true)
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

  useEffect(() => {
    if (!dados?.ativo || registrada || ocupado || recuperacao) return undefined
    const controller = new AbortController()
    const versao = sequencia.current
    const timer = setInterval(async () => {
      try {
        const retorno = await api.status({}, { signal: controller.signal })
        if (controller.signal.aborted || versao !== sequencia.current) return
        receber(retorno) // Rascunhos e seleção não pertencem ao GET.
        if (retorno.laboratorio?.session_id !== sid || retorno.missao.revisao !== revisao || retorno.conflito || !retorno.ativo) {
          setRecuperacao(true)
          setConsulta(null)
          setAviso('O estado do ambiente mudou. Rascunhos preservados; atualize o estado explicitamente antes de continuar.')
        }
      } catch (erro) {
        if (!controller.signal.aborted && versao === sequencia.current) {
          setRecuperacao(true); setAviso(`${erro.message} Rascunhos preservados. Atualize o estado.`)
        }
      }
    }, 30000)
    return () => { clearInterval(timer); controller.abort() }
  }, [dados?.ativo, registrada, ocupado, recuperacao, sid, revisao])

  async function executar(acao, extras = {}) {
    if (trava.current || vida.current?.signal.aborted) return
    if (acao === 'iniciar' && (!dados?.disponivel || dados.ativo || dados.conflito || recuperacao || pendente)) return
    if (!['status', 'iniciar', 'encerrar'].includes(acao) && !livre) return
    if (acao === 'encerrar' && (!dados?.ativo || dados.conflito || recuperacao)) return
    if (acao === 'testar-local' && !hipotese.local) return
    if (acao === 'classificar' && (!localPronto || !classificacao)) return
    if (acao === 'testar-remoto' && (!localPronto || missao?.gateway?.confirmado)) return
    if (acao === 'aplicar') {
      if (!localPronto || !redePronta) return
      const problema = validarGateway(gateway, pc1)
      if (problema) { setAviso(problema); return }
    }
    if (acao === 'testar-depois' && !mesmoGateway) return
    if (acao === 'interpretar' && (!depoisValido || !resposta)) return
    if (acao === 'validar' && !podeConcluir) return
    trava.current = true
    const versao = ++sequencia.current
    setOperacao(acao)
    setAviso('')
    const payload = ['status', 'iniciar'].includes(acao) ? {} : { session_id: sid, revisao,
      ...(acao === 'aplicar' ? { gateway } : {}), ...(acao === 'testar-local' ? { local: hipotese.local } : {}),
      ...(acao === 'classificar' ? { resposta: classificacao } : {}), ...(acao === 'interpretar' ? { resposta } : {}),
      ...(acao === 'terminal' ? extras : {}) }
    try {
      const retorno = await api[acao](payload, { signal: vida.current?.signal })
      if (vida.current?.signal.aborted || versao !== sequencia.current) return
      receber(retorno, acao === 'iniciar')
      setRecuperacao(false)
      if (acao === 'consultar') setConsulta(retorno.laboratorio?.session_id ?? null)
      if (retorno.conflito) { setAviso('Outro laboratório está em uso. Nenhuma sessão foi substituída.'); return }
      if (acao === 'iniciar' && !retorno.ativo) throw new Error('O servidor não confirmou um ambiente ativo.')
      if (acao === 'aplicar') {
        if (!retorno.missao.gateway?.confirmado || retorno.missao.gateway.valor !== payload.gateway) throw new Error('O servidor não confirmou o gateway aplicado.')
        setSujo(false)
        setTerminalAberto(true)
        setAlvoTerminal(4)
      } else if (acao === 'validar') {
        if (!retorno.conclusao?.registrada || !retorno.missao.concluido) throw new Error('A conclusão ainda não foi confirmada pelo servidor.')
        setXp(Number.isFinite(retorno.xp_concedido) ? retorno.xp_concedido : null)
      } else if (acao === 'encerrar') {
        if (retorno.ativo || retorno.conclusao?.encerramento_pendente) throw new Error('A limpeza ainda não foi confirmada. Atualize o estado antes de tentar novamente.')
        setAviso('Encerramento confirmado pelo servidor.')
      } else if (acao === 'status') {
        setConsulta(null)
        setAviso('Estado atualizado. Seus rascunhos foram preservados; compare com o estado aplicado.')
      } else if (acao === 'terminal') {
        setComando('')
        setErroTerminal('')
        setTerminalAberto(true)
      } else if (acao === 'classificar' && retorno.missao.classificacao?.correta) {
        setTerminalAberto(false)
      }
      if (acao === 'iniciar') setXp(null)
    } catch (erro) {
      if (vida.current?.signal.aborted || versao !== sequencia.current) return
      if (erro.dados?.missao) {
        try { receber(erro.dados) } catch { /* Incompleto: manter controles bloqueados. */ }
      }
      setRecuperacao(true)
      setConsulta(null)
      setAviso(`${erro.message} Seus rascunhos foram preservados. Use “Atualizar estado” antes de repetir.`)
    } finally {
      trava.current = false
      if (!vida.current?.signal.aborted) setOperacao('')
    }
  }

  async function executarTerminal(evento) {
    evento.preventDefault()
    if (!livre || sujo) return
    const entrada = validarComandoPing(comando, missao?.nos)
    if (entrada.erro) { setErroTerminal(entrada.erro); return }
    if (entrada.destino === 2 && !hipotese.local) {
      setErroTerminal('Faça sua previsão sobre o colega antes de testar.')
      return
    }
    if (entrada.destino === 4 && !localPronto) {
      setErroTerminal('Primeiro teste o colega. Depois vamos experimentar o servidor.')
      return
    }
    setErroTerminal('')
    await executar('terminal', {
      comando: entrada.comando,
      ...(entrada.destino === 2 ? { local: hipotese.local } : {}),
    })
  }

  function abrirTerminal(destino = 2) {
    setAlvoTerminal(destino)
    setTerminalAberto(true)
    requestAnimationFrame(() => campoTerminal.current?.focus())
  }

  async function perguntarAoLink(pergunta) {
    if (!ativo || linkPendente.current) return false
    const contexto = { session_id: sid, revisao }
    linkPendente.current = true
    setLinkOcupado(true)
    setErroLink('')
    try {
      const retorno = await api.tutor({ ...contexto, pergunta, rascunho: { comando, gateway } }, { signal: vida.current?.signal })
      if (vida.current?.signal.aborted) return false
      const atual = estadoAtual.current
      if (atual?.laboratorio?.session_id !== contexto.session_id || atual?.missao?.revisao !== contexto.revisao) {
        setErroLink('A etapa ou a configuração mudou durante a resposta. Faça sua pergunta novamente.')
        return false
      }
      if (!retorno.tutor?.resposta || !['referencias', 'contingencia'].includes(retorno.tutor.modo)) throw new Error('O Link não confirmou uma resposta válida.')
      setMensagensLink(retorno.tutoria)
      return true
    } catch (erro) {
      if (!vida.current?.signal.aborted) setErroLink(erro.status === 409
        ? 'A etapa ou a configuração mudou. Faça sua pergunta novamente.' : erro.message)
      return false
    } finally {
      linkPendente.current = false
      if (!vida.current?.signal.aborted) setLinkOcupado(false)
    }
  }

  const observado = consulta === sid && sid !== undefined
  const computador = missao?.nos?.find((n) => n.id === pcSelecionado)
  const tempo = restantes === null ? '--:--' : `${String(Math.floor(restantes / 60)).padStart(2, '0')}:${String(restantes % 60).padStart(2, '0')}`
  const atual = Math.max(0, etapas.findIndex((e) => !e.concluida))
  const testes = !sujo && missao?.depois?.registrado ? missao.depois : missao?.antes
  const local = missao?.teste_local?.registrado ? missao.teste_local.alcance : testes?.local
  const remoto = testes?.remoto
  const historico = Array.isArray(missao?.terminal) ? missao.terminal : []
  const ultimo = historico.at(-1)
  const mostrarTerminal = !registrada && (terminalAberto || (!localPronto && Boolean(hipotese.local)) || (redePronta && mesmoGateway && !depoisValido))
  const orientacao = orientarGateway({
    ocupado, recuperacao, expirado, preparacaoPendente: dados?.preparacao_pendente,
    conflito: dados?.conflito, registrada, pendente, ativo: dados?.ativo,
    localPronto, redePronta, mesmoGateway, depoisValido,
    previsao: hipotese.local, comando, erroTerminal, classificacao,
    classificacaoIncorreta: missao?.classificacao?.resposta === classificacao && !redePronta,
    gateway, observado, gatewayInvalido: Boolean(gateway && validarGateway(gateway, pc1)),
    remotoFalhou: !sujo && missao?.depois?.registrado && missao.depois.remoto === false,
    resposta, interpretacaoCorreta: missao?.interpretacao?.correta && resposta === missao.interpretacao.resposta,
    interpretacaoIncorreta: missao?.interpretacao?.resposta === resposta && !missao?.interpretacao?.correta,
  })
  const esperado = (alvo) => orientacao.alvo === alvo ? 'gw-proxima-acao' : ''
  const irParaAcao = () => {
    if (['comando', 'executar'].includes(orientacao.alvo)) abrirTerminal(mesmoGateway ? 4 : 2)
    requestAnimationFrame(() => {
      const elemento = document.querySelector(`.gw-v3 [data-acao="${orientacao.alvo}"]`)
      if (!elemento) return
      const detalhes = elemento.closest('details')
      if (detalhes) detalhes.open = true
      elemento.scrollIntoView({ block: 'center', behavior: 'auto' })
      elemento.focus({ preventScroll: true })
    })
  }
  const statusTeste = (valor) => valor === true ? 'Respondeu' : valor === false ? 'Não respondeu' : 'Não testado'
  const selecionar = (id) => {
    setPcSelecionado(id)
    setInspecionarPc(id === 1 ? !inspecionarPc : false)
    if (id === 5 && livre) executar('consultar')
  }
  const ipInterfaceRoteador = (nome) => missao?.nos?.find((n) => n.id === 5)?.interfaces?.find((i) => i.interface === nome)?.ip
  const no = (id, titulo, Icone) => (
    <button className={`gw-equipamento gw-no-${id} ${id === 5 ? esperado('roteador') : ''}`} aria-pressed={pcSelecionado === id}
      data-acao={id === 5 ? 'roteador' : undefined} onClick={() => selecionar(id)} aria-label={`Consultar ${titulo}`}>
      <Icone aria-hidden="true" /><strong>{titulo}</strong>
      <small className={ [1, 2, 4].includes(id) ? 'gw-endereco-no' : '' }>{[1, 2, 4].includes(id) ? <><span>{missao?.nos?.find((n) => n.id === id)?.ip || '—'}</span><span className="gw-prefixo-no">/24</span></> : id === 3 ? 'Conexão local' : observado ? 'Duas interfaces' : 'Clique para consultar'}</small>
      {/* Interfaces presas ao nó do roteador, ao lado do cabo de cada rede; o IP só aparece depois da consulta real. */}
      {id === 5 && ['eth0', 'eth1'].map((nome) => (
        <span key={nome} className={`gw-porta gw-porta-${nome}`} data-testid={`porta-${nome}`} aria-hidden="true">
          <b>{nome}</b>{observado && <span>{ipInterfaceRoteador(nome)}</span>}
        </span>
      ))}
    </button>
  )
  const resultadoTerminal = (item) => (
    <div className="gw-saida-comando">
      <div className="gw-linha-comando"><code><span aria-hidden="true">$ </span>{item.digitado}</code>
        <span className={item.alcance ? 'ok' : 'falhou'}>{statusTeste(item.alcance)}</span>
      </div>
      <p className="gw-resumo-ping">{item.saida.split('\n').find((linha) => /packets transmitted|Network is unreachable/.test(linha)) || item.saida.split('\n').find(Boolean)}</p>
      <details className="gw-saida-completa"><summary>Ver saída completa</summary><pre>{item.saida}</pre></details>
    </div>
  )

  const painelEtapas = (<ol className="gw-etapas" aria-label="Etapas da missão">{etapas.map((e, i) => (
        <li key={e.id} className={e.concluida ? 'feita' : i === atual ? 'atual' : ''} aria-current={!e.concluida && i === atual ? 'step' : undefined}>
          <span>{e.concluida ? <CheckCircle2 size={20} /> : i + 1}</span>
          <div><strong>{e.titulo}</strong><small>{e.concluida ? 'Etapa comprovada' : i === atual ? e.orientacao : 'A seguir'}</small></div>
        </li>
      ))}</ol>)
  const painelTopologia = (<section className="gw-painel gw-topologia" aria-label="Topologia de duas redes">
        <h2 className="gw-etiqueta">TOPOLOGIA · DUAS REDES</h2>
        <div className="gw-mapa">
          <div className="gw-zona-local"><span>Atendimento · 192.168.10.0/24</span></div><div className="gw-zona-remota"><span>Servidor · 192.168.20.0/24</span></div>
          <svg className="gw-cabos" viewBox="0 0 1000 220" preserveAspectRatio="none" aria-hidden="true"><path d="M 180 67 H 230 V 115 H 340 M 180 165 H 230 V 115 M 440 115 H 580 M 700 115 H 840" /></svg>
          <svg className="gw-cabos-mobile" viewBox="0 0 1000 480" preserveAspectRatio="none" aria-hidden="true"><path d="M 230 144 V 170 H 490 V 200 M 750 144 V 170 H 490 M 490 304 V 315 H 230 V 330 M 430 382 H 550" /></svg>
          {no(1, 'PC Atendimento', Computer)}{no(2, 'PC Colega', Computer)}{no(3, 'Switch', Network)}{no(5, 'Roteador', IconeRoteador)}{no(4, 'Servidor', Server)}
        </div>
        {pcSelecionado === 1 && inspecionarPc && <div className="gw-inspecao gw-inspecao-pc">
          <strong>PC Atendimento · endereçamento preparado</strong>
          <div className="gw-enderecos"><label>Endereço IP <LockKeyhole size={13} /><input aria-label="Endereço IP" value={pc1?.ip || ''} readOnly /></label>
            <label>Máscara <LockKeyhole size={13} /><input aria-label="Máscara" value="255.255.255.0" readOnly /></label></div>
        </div>}
        {pcSelecionado === 5 && <div className="gw-inspecao" data-testid="interfaces-roteador"><strong>Interfaces do roteador</strong>
          {observado ? missao?.nos?.find((n) => n.id === 5)?.interfaces?.map((i) => <span key={i.interface}>{i.interface} · {i.ip}/{i.prefixo}</span>)
            : <span>{ocupado ? 'Consultando o nó…' : 'Inicie o ambiente e clique no roteador para consultar suas interfaces.'}</span>}
        </div>}
        {[2, 4].includes(pcSelecionado) && <div className="gw-inspecao"><strong>{computador?.nome}</strong><span>{computador?.ip}/24 · Configuração preparada, somente leitura.</span></div>}
        {pcSelecionado === 3 && <div className="gw-inspecao">O switch conecta os equipamentos da rede do Atendimento.</div>}
      </section>)

  // Três colunas: as tarefas da missão (e os conceitos, quando o aluno pede) ficam à direita; o terminal no centro.
  const tarefas = (<>
        <section className="gw-painel gw-pratica" aria-label="Prática guiada">
          <header><Computer size={19} /><h2>PC Atendimento</h2><span className="gw-etapa-atual">{etapa?.titulo || (registrada ? 'Concluído' : missao?.concluido ? 'Pronto para concluir' : 'Preparando')}</span></header>

          {!localPronto && !registrada && <section className="gw-atividade">
            <h3>O colega precisa de gateway?</h3>
            <p>Os dois computadores estão na rede 192.168.10.0/24. Faça uma previsão e teste no terminal.</p>
            <label htmlFor="gw-previsao">Sem gateway, o PC Atendimento alcançará o colega?</label>
            <select data-acao="previsao" className={esperado('previsao')} id="gw-previsao" value={hipotese.local} disabled={!livre} onChange={(e) => setHipotese({ ...hipotese, local: e.target.value })}>
              <option value="">Escolha sua previsão</option><option value="sim">Sim, alcançará</option><option value="nao">Não alcançará</option>
            </select>
            <p className="gw-nota">Errar a previsão não reduz seu XP.</p>
          </section>}

          {localPronto && !redePronta && !registrada && <section className="gw-atividade">
            <h3>E o servidor?</h3><p>Compare seu IP <strong>192.168.10.10/24</strong> com o do servidor <strong>192.168.20.10/24</strong>.</p>
            <label htmlFor="gw-classificacao">O servidor pertence à mesma rede do computador?</label>
            <select data-acao="classificacao" className={esperado('classificacao')} id="gw-classificacao" value={classificacao} disabled={!livre} onChange={(e) => setClassificacao(e.target.value)}>
              <option value="">Escolha uma opção</option><option value="mesma-rede">Sim, à mesma rede</option><option value="outra-rede">Não, a outra rede</option>
            </select>
            <button data-acao="comparar" className={`gw-primario ${esperado('comparar')}`} disabled={!livre || !classificacao} onClick={() => executar('classificar')}>Comparar redes</button>
            {missao?.classificacao?.resposta && !redePronta && <p role="status">Com a máscara /24, compare os três primeiros números: 192.168.10 e 192.168.20. Tente novamente.</p>}
            <details className="gw-opcional"><summary>Experimento opcional</summary><button disabled={!livre} onClick={() => abrirTerminal(4)}>Experimentar acesso ao servidor (opcional)</button></details>
          </section>}

          {(redePronta || registrada) && <form className="gw-form" onSubmit={(e) => { e.preventDefault(); executar('aplicar') }}>
            <p className="gw-contexto">Para alcançar outra rede, configure como gateway a interface local do roteador.</p>
            <label htmlFor="gateway-campo">Gateway padrão</label><div>
              <input data-acao="gateway" className={esperado('gateway')} id="gateway-campo" aria-label="Gateway padrão" placeholder="Endereço do gateway" value={gateway}
                onChange={(e) => { setGateway(e.target.value); setSujo(true); setAviso(''); setResposta('') }}
                disabled={!livre} inputMode="decimal" autoComplete="off" spellCheck={false} maxLength={15} />
              <button data-acao="aplicar" className={`gw-primario ${esperado('aplicar')}`} disabled={!livre || !gateway}>Aplicar gateway</button>
            </div>
            <p className="gw-nota">{sujo ? 'Alteração ainda não aplicada.' : missao?.gateway?.confirmado ? `Aplicado e conferido no nó: ${missao.gateway.valor}` : 'Clique no roteador para consultar suas interfaces.'}</p>
          </form>}

          {(local !== undefined && local !== null || remoto !== undefined && remoto !== null) && <section className="gw-testes">
            <h3>Resultados da comunicação</h3>
            <div className="gw-teste"><Computer size={20} /><span><strong>PC Colega</strong><small>192.168.10.20</small></span><b className={local === true ? 'ok' : local === false ? 'falhou' : ''}>{statusTeste(local)}</b></div>
            <div className="gw-teste"><Server size={20} /><span><strong>Servidor</strong><small>192.168.20.10</small></span><b className={remoto === true ? 'ok' : remoto === false ? 'falhou' : ''}>{statusTeste(remoto)}</b></div>
            {mesmoGateway && <p className="gw-nota">O ping para o servidor também reconfirma o colega e o gateway aplicado.</p>}
          </section>}

          {depoisValido && <section className="gw-atividade gw-interpretacao">
            <h3>Por que o colega respondia sem gateway?</h3><label htmlFor="gw-interpretacao">Escolha a explicação para os resultados</label>
            <select data-acao="interpretacao" className={esperado('interpretacao')} id="gw-interpretacao" value={resposta} disabled={!livre} onChange={(e) => setResposta(e.target.value)}>
              <option value="">Escolha sua interpretação</option><option value="gateway-remoto">O colega está na mesma rede; o servidor precisa do gateway.</option>
              <option value="gateway-sempre">Todos os destinos precisam do gateway.</option><option value="switch-roteia">O switch encaminha sozinho para qualquer rede.</option>
            </select><button data-acao="interpretar" className={esperado('interpretar')} disabled={!livre || !resposta} onClick={() => executar('interpretar')}>Conferir interpretação</button>
            {missao?.interpretacao?.resposta === resposta && <p role="status">{missao.interpretacao.feedback}</p>}
            <button data-acao="concluir" className={`gw-primario ${esperado('concluir')}`} disabled={!podeConcluir} onClick={() => executar('validar')}>Validar missão</button>
          </section>}
        </section>

        {bastidores && <aside className="gw-painel gw-bastidores"><span className="gw-etiqueta">BASTIDORES DA REDE</span>
          <h2>Quando usar o gateway?</h2>
          <span className="gw-ilustracao">Ilustração explicativa</span>
          <section className="gw-conceito"><Computer size={23} /><div><h3>Mesma rede <ArrowRight size={14} /> comunicação local</h3>
            <p>{localPronto || registrada ? 'O colega respondeu sem gateway. Para um destino na mesma rede, a comunicação é local.' : 'Faça uma previsão e teste o colega. Depois compare sua expectativa com o resultado.'}</p>
          </div></section>
          <section className="gw-conceito"><Router size={23} /><div><h3>Outra rede <ArrowRight size={14} /> envio ao gateway</h3>
            <p>{redePronta || registrada ? 'Para alcançar o servidor, o computador envia os pacotes ao gateway local. O roteador encaminha para a outra rede.' : 'Na próxima etapa, compare o endereço do servidor com o do seu computador.'}</p>
          </div></section>
          <p className="gw-nota">A explicação acima é ilustrativa; os pacotes de verdade estão nos Bastidores da rede, abaixo do terminal.</p>
        </aside>}
  </>)

  return (
    <main className={`laboratorio-pagina gateway-lab gw-v2 gw-v3 ${foco ? 'gw-foco' : ''}`} aria-busy={ocupado}>
      <nav className="gw-controles" aria-label="Opções de visualização">
        <button aria-pressed={foco} onClick={() => setFoco(!foco)}>{foco ? 'Sair do modo foco' : 'Modo foco'}</button>
        <button aria-expanded={bastidores} onClick={() => setBastidores(!bastidores)}>{bastidores ? 'Ocultar Bastidores' : 'Mostrar Bastidores'}</button>
        <Link className={esperado('catalogo')} data-acao="catalogo" to="/modulos">Voltar ao catálogo</Link>
      </nav>

      <header className="gw-cabecalho">
        <div><span className="gw-etiqueta">LABORATÓRIO 3 · GATEWAY</span>
          <h1>Dentro ou fora da minha rede?</h1><p>Configure a saída do computador para alcançar outra rede.</p>
        </div>
        <div className="gw-acoes">
          {dados?.ativo && !registrada && <TempoEValidar tempo={!dados.conflito ? tempo : '--:--'} restantes={dados.conflito ? null : restantes}
            pronta={podeConcluir} feitas={etapas.filter((e) => e.concluida).length} total={etapas.length}
            ocupado={ocupado} aoValidar={() => executar('validar')} />}
          {!dados?.ativo && <button className={`gw-primario ${esperado('iniciar')}`} data-acao="iniciar" disabled={ocupado || !dados?.disponivel || Boolean(dados?.conflito) || recuperacao || pendente}
            onClick={() => executar('iniciar')}>{registrada ? 'Iniciar novo treino' : 'Iniciar ambiente'}</button>}
        </div>
      </header>

      {dados?.conflito && <section className="gw-alerta" role="alert"><strong>Outro laboratório está em uso</strong><p>Volte ao catálogo para abrir a missão correspondente. A sessão existente foi preservada.</p></section>}
      {dados?.preparacao_pendente && <section className="gw-alerta" role="alert" data-testid="preparacao-pendente"><strong>Preparação incompleta</strong><p>O servidor ainda não confirmou a preparação e a remoção do ambiente.</p></section>}
      {aviso && <p className="gw-alerta" role={recuperacao ? 'alert' : 'status'}>{aviso}</p>}
      {(recuperacao || expirado || dados?.preparacao_pendente) && <section className="gw-alerta">
        <p>{expirado ? 'O prazo terminou ou não foi confirmado. Consulte o estado do ambiente.' : 'Consulte o estado antes de continuar. Seus rascunhos foram preservados.'}</p>
        <button className={esperado('atualizar')} data-acao="atualizar" disabled={ocupado} onClick={() => executar('status')}>Atualizar estado</button>
      </section>}
      {registrada && <section className="gw-sucesso" data-testid="conclusao" aria-live="polite"><strong>Missão concluída</strong>
        <p>{pendente ? 'Conclusão salva; remoção do ambiente ainda pendente.' : 'Conclusão salva e ambiente encerrado pelo servidor.'} {xp !== null ? xp > 0 ? `+${xp} XP confirmados.` : 'Sem nova concessão de XP.' : 'Progresso recuperado do servidor.'}</p>
        {pendente && <button data-acao="limpar" className={esperado('limpar')} disabled={ocupado || recuperacao || Boolean(dados?.conflito) || !dados?.ativo} onClick={() => executar('encerrar')}>Tentar limpeza novamente</button>}
      </section>}



      <EspacoLaboratorio topologia={painelTopologia} etapas={painelEtapas} orientacao={orientacao} lateral={tarefas} apresentacao="lab3"
        chaveEtapa={missao?.proxima_etapa} aoIrParaAcao={irParaAcao} ajudaAberta={ajudaExpandida} aoAlternarAjuda={() => setAjudaExpandida(!ajudaExpandida)}
        tutor={{
          imagem: registrada ? linkConectando : depoisValido ? linkExplicando : linkObservando,
          mensagem: registrada ? 'Sua missão foi concluída. Você pode rever os resultados.' : 'Qual é sua dúvida? Vamos pensar juntos sobre a topologia e o que você observou.',
          conteudo: <ConversaLink mensagens={mensagensLink} aoPerguntar={perguntarAoLink}
            ocupado={linkOcupado} disponivel={ativo} erro={erroLink} />,
        }}>
      <>
        {mostrarTerminal ? <section className="gw-terminal" aria-label="Terminal do PC Atendimento">
            <header><Terminal size={17} /><h3>Terminal · PC Atendimento</h3></header>
            <p>Observe o endereço {(!localPronto || alvoTerminal === 2) ? 'do colega' : 'do servidor'} na topologia e teste a comunicação a partir do PC Atendimento.</p>
            <p className="gw-nota">O teste envia duas tentativas e termina sozinho.</p>
            {ultimo && resultadoTerminal(ultimo)}
            <form className="gw-entrada-terminal" onSubmit={executarTerminal}>
              <label htmlFor="gw-comando">Digite seu comando</label>
              <div><span className="gw-prompt" aria-hidden="true">$</span>
                <input data-acao="comando" className={esperado('comando')} ref={campoTerminal} id="gw-comando" aria-label="Comando do terminal" value={comando}
                  onChange={(e) => { setComando(e.target.value); setErroTerminal('') }}
                  placeholder="Digite um comando…" disabled={!livre || sujo} autoComplete="off" spellCheck={false} maxLength={80}
                  aria-describedby="gw-terminal-nota gw-terminal-erro" />
                <button data-acao="executar" className={`gw-primario ${esperado('executar')}`} disabled={!livre || sujo || !comando.trim()}>Executar</button>
              </div>
              <p className="gw-nota">{localPronto && !redePronta ? 'Para avançar, responda à comparação de redes destacada ao lado.' : ''}</p>
              <p id="gw-terminal-nota" className="gw-nota">{sujo ? 'Aplique o gateway editado antes de novos testes.' : 'Digite somente o comando. O $ ao lado é o indicador do terminal.'}</p>
              <p id="gw-terminal-erro" role="alert">{erroTerminal}</p>
              {ocupado && <p role="status">Aguardando confirmação do servidor…</p>}
            </form>
            {historico.length > 1 && <details className="gw-historico"><summary>Testes anteriores ({historico.length - 1})</summary>
              {historico.slice(0, -1).map((item, index) => <div key={`${item.revisao}-${index}`}>{resultadoTerminal(item)}</div>)}
            </details>}
            {ultimo && <details className="gw-detalhes-execucao"><summary>Detalhes da execução</summary>
              <p>Você digitou <code>{ultimo.digitado}</code>. A plataforma acrescentou opções para usar a rede do laboratório e limitar a duração do teste.</p>
              <pre>{ultimo.executado}</pre>
              {!sujo && missao?.conferencia?.saida && <><p>Verificação adicional do gateway feita pela plataforma:</p><pre>ip -j -4 route show default{'\n'}{missao.conferencia.saida}</pre></>}
            </details>}
          </section> : <section className="gw-painel gw-terminal gw-terminal-espera" aria-label="Terminal do PC Atendimento">
          <header><Terminal size={17} /><h3>Terminal · PC Atendimento</h3></header>
          <p>{registrada ? 'Missão concluída. Os testes ficam registrados ao lado.' : localPronto ? 'Abra o terminal quando quiser testar a comunicação.' : 'Escolha sua previsão no painel ao lado e o terminal abre aqui.'}</p>
          {localPronto && !registrada && <button className="gw-abrir-terminal" disabled={!livre || sujo} onClick={() => abrirTerminal(mesmoGateway ? 4 : 2)}><Terminal size={16} /> Abrir terminal</button>}
        </section>}

        <BastidoresTshark capturas={dados?.bastidores} nomeNo={() => 'PC Atendimento'} nomeIp={(ip) => IPS_LAB3[ip] ? `${IPS_LAB3[ip]} (${ip})` : ip || '—'} />
      </>
      </EspacoLaboratorio>
      {dados?.ativo && !registrada && !dados?.conflito && <footer className="gw-gerencia">
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


// Nomes dos equipamentos do Lab 3, para os pacotes capturados pelo tshark.
const IPS_LAB3 = { '192.168.10.10': 'PC Atendimento', '192.168.10.20': 'PC Colega', '192.168.10.1': 'Roteador', '192.168.20.1': 'Roteador', '192.168.20.10': 'Servidor' }
export default function LaboratorioGateway() {
  const { usuario } = useAuth()
  return <SessaoGateway key={usuario?.id || usuario?.login || 'sem-sessao'} />
}
