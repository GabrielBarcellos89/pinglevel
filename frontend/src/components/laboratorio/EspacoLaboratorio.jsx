import { useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react'
import { ArrowRight, Network, ChevronDown } from 'lucide-react'
import './EspacoLaboratorio.css'

const consultaCompacta = '(max-width: 850px)'
function acompanharTela(avisar) {
  const consulta = window.matchMedia(consultaCompacta)
  consulta.addEventListener('change', avisar)
  return () => consulta.removeEventListener('change', avisar)
}
const telaCompacta = () => window.matchMedia(consultaCompacta).matches

// O "Agora faça" diz o objetivo; o comando fica nas pistas, abertas uma de cada vez só por quem pedir.
function Pistas({ pistas }) {
  const [abertas, setAbertas] = useState(0)
  return <div className="pl-pistas">
    {pistas.slice(0, abertas).map((p, i) => <p key={i} className="pl-pista"><b>Pista {i + 1}</b> {p}</p>)}
    {abertas < pistas.length && <button type="button" className="pl-pedir-pista" onClick={() => setAbertas(abertas + 1)}>
      {abertas === 0 ? 'Preciso de uma pista' : 'Outra pista'} ({abertas + 1} de {pistas.length})</button>}
  </div>
}

// Apresentação ao iniciar: escurece a tela e acende uma parte por vez. Vista uma vez por laboratório, neste navegador.
// Labs 3 e 4 e todos os de LaboratorioRede (menos o teste de carga, que tem o "Agora faça" ao lado do Link).
const PASSOS_APRESENTACAO = [
  { classe: 'pl-tour-acao', titulo: 'Comece por aqui', texto: 'O Agora faça diz o que fazer agora, e o painel da direita traz a tarefa do momento: o plano, a pergunta do chamado ou a investigação. Responda com base no que o terminal mostrar.' },
  { classe: 'pl-tour-mapa', titulo: 'Esta é a rede', texto: 'Clique num PC da topologia para abrir o terminal dele. Os endereços e o estado de cada um aparecem aqui.' },
]
const lerVista = (chave) => { try { return localStorage.getItem(chave) === 'sim' } catch { return true } }
const marcarVista = (chave) => { try { localStorage.setItem(chave, 'sim') } catch { /* sem armazenamento: só nesta visita */ } }

// Somente apresentação. Cada laboratório mantém sessões, evidências e conclusão.
export default function EspacoLaboratorio({ topologia, etapas, orientacao, aoIrParaAcao,
  tutor, ajudaAberta, aoAlternarAjuda, chaveEtapa, lateral, apresentacao, agoraAoLado, children }) {
  const compacto = useSyncExternalStore(acompanharTela, telaCompacta, () => false)
  const chaveApresentacao = apresentacao && `pinglevel:apresentacao:${apresentacao}`
  const [passoApresentacao, setPassoApresentacao] = useState(() => chaveApresentacao && !lerVista(chaveApresentacao) ? 0 : -1)
  const avancarApresentacao = (fim) => {
    if (fim || passoApresentacao + 1 >= PASSOS_APRESENTACAO.length) { marcarVista(chaveApresentacao); setPassoApresentacao(-1) }
    else setPassoApresentacao(passoApresentacao + 1)
  }
  const [topologiaAberta, setTopologiaAberta] = useState(false)
  // agoraAoLado (teste de carga): o "Agora faça" e o Link dividem a coluna da direita. Abrir o Link recolhe o "Agora
  // faça" (e o chamado) para o Link ter espaço; cada um tem Recolher/Expandir.
  const [agoraRecolhidaManual, setAgoraRecolhidaManual] = useState(false)
  const agoraRecolhida = Boolean(agoraAoLado) && (ajudaAberta || agoraRecolhidaManual)
  function alternarAgora() {
    if (!agoraRecolhida) { setAgoraRecolhidaManual(true); return }
    setAgoraRecolhidaManual(false)
    if (ajudaAberta) aoAlternarAjuda()
  }
  const raiz = useRef(null)
  const guia = useRef(null)
  const pratica = useRef(null)
  useLayoutEffect(() => {
    pratica.current?.scrollTo({ top: 0, behavior: 'instant' })
    guia.current?.scrollTo({ top: 0, behavior: 'instant' })
  }, [chaveEtapa])
  useLayoutEffect(() => {
    const medir = () => raiz.current?.style.setProperty('--pl-altura-guia', `${guia.current?.offsetHeight || 100}px`)
    const observer = new ResizeObserver(medir)
    if (guia.current) observer.observe(guia.current)
    medir()
    return () => observer.disconnect()
  }, [])

  const botaoAgora = agoraAoLado && <button type="button" className="pl-agora-alternar" aria-expanded={!agoraRecolhida} onClick={alternarAgora}>
    {agoraRecolhida ? 'Expandir' : 'Recolher'} <ChevronDown size={15} />
  </button>
  const agora = agoraRecolhida ? (
    <section className="pl-agora pl-agora-recolhida" ref={guia} aria-live="polite" aria-atomic="true" data-testid="agora-faca">
      <div><span className="pl-agora-etiqueta">AGORA FAÇA · {orientacao.etiqueta}</span><h2>{orientacao.titulo}</h2></div>
      {botaoAgora}
    </section>
  ) : (
    <section className="pl-agora" ref={guia} aria-live="polite" aria-atomic="true" data-testid="agora-faca">
      {botaoAgora}
      <div><span className="pl-agora-etiqueta">AGORA FAÇA · {orientacao.etiqueta}</span>
        <h2>{orientacao.titulo}</h2><p id="pl-instrucao-atual">{orientacao.ocupado ? 'Aguardando confirmação do servidor…' : orientacao.texto}</p>
        {(orientacao.onde || orientacao.pronto) && <dl className="pl-agora-guia">
          {orientacao.onde && <div><dt>Onde</dt><dd>{orientacao.onde}</dd></div>}
          {orientacao.pronto && <div><dt>Pronto quando</dt><dd>{orientacao.pronto}</dd></div>}
        </dl>}
        {orientacao.pistas?.length > 0 && <Pistas key={orientacao.titulo} pistas={orientacao.pistas} />}
      </div>
      {orientacao.alvo && <button onClick={() => { if (compacto) setTopologiaAberta(orientacao.alvo === 'roteador'); requestAnimationFrame(aoIrParaAcao) }} disabled={orientacao.ocupado}>
        Ir para ação <ArrowRight size={16} />
      </button>}
    </section>
  )
  const tres = lateral && !compacto
  const painelTutor = (
    <aside className={`pl-tutor ${ajudaAberta ? 'pl-tutor-expandido' : ''}`} aria-label="Tutor Link" data-testid="link-persistente">
      <header><img src={tutor.imagem} alt="Link, tutor da missão" /><strong>Tutor Link</strong>
        <button className="pl-tutor-alternar" aria-expanded={ajudaAberta} onClick={aoAlternarAjuda}>
          {ajudaAberta ? (tres ? 'Recolher' : 'Recolher ajuda') : (tres ? 'Perguntar ao Link' : 'Ver ajuda')} <ChevronDown size={15} />
        </button>
      </header>
      <div className="pl-tutor-conteudo">
        <img className="pl-mascote" src={tutor.imagem} alt="" />
        <p className="pl-fala-link">{tutor.mensagem}</p>
        {tutor.conteudo || <><button onClick={tutor.aoPedirPista} disabled={tutor.pistaDesabilitada}>{tutor.rotuloPista}</button>
          {tutor.pistaAberta && <button className="pl-recolher-pista" onClick={tutor.aoRecolherPista}>Recolher pista</button>}</>}
        <p className="pl-disponibilidade">Estou aqui durante toda a missão.</p>
      </div>
    </aside>
  )
  const topologiaFixa = (
    <div className="pl-topologia-fixa" data-testid="topologia-persistente">
      <button className="pl-topologia-alternar" aria-expanded={!compacto || topologiaAberta}
        onClick={() => setTopologiaAberta(!topologiaAberta)}>
        <Network size={17} /> {topologiaAberta ? 'Recolher topologia' : 'Ver topologia e equipamentos'} <ChevronDown size={15} />
      </button>
      {(!compacto || topologiaAberta) && topologia}
    </div>
  )

  // Três colunas: mapa e "Agora faça" | terminal | tarefas e Link (aberto quando o aluno pede). Em tela estreita, volta ao empilhado.
  const passo = tres ? PASSOS_APRESENTACAO[passoApresentacao] : null
  if (tres) return (
    <div className={`pl-espaco pl-tres ${passo ? `pl-tour ${passo.classe}` : ''}`} ref={raiz}>
      {passo && <>
        <div className="pl-tour-fundo" aria-hidden="true" />
        <section className="pl-tour-cartao" role="dialog" aria-modal="false" aria-label={passo.titulo}>
          <span>{passoApresentacao + 1} de {PASSOS_APRESENTACAO.length}</span>
          <h2>{passo.titulo}</h2><p>{passo.texto}</p>
          <div><button type="button" className="pl-tour-ok" onClick={() => avancarApresentacao(false)} autoFocus>
            {passoApresentacao + 1 < PASSOS_APRESENTACAO.length ? 'Entendi' : 'Começar'}</button>
            <button type="button" className="pl-tour-pular" onClick={() => avancarApresentacao(true)}>Pular</button></div>
        </section>
      </>}
      {/* agoraAoLado: o mapa ocupa a coluna inteira e o "Agora faça" sobe para o topo das tarefas (teste de carga). */}
      <div className={`pl-col pl-col-mapa ${agoraAoLado ? 'pl-mapa-inteiro' : ''}`}>{topologiaFixa}{etapas}{!agoraAoLado && agora}</div>
      <div className="pl-col pl-col-terminal" ref={pratica} role="region" aria-label="Área de prática" tabIndex={0}>{children}</div>
      <div className={`pl-col pl-col-tarefas ${agoraAoLado && ajudaAberta ? 'pl-link-aberto' : ''}`}>
        {agoraAoLado && agora}
        <div className="pl-tarefas" role="region" aria-label="Tarefas da missão">{lateral}</div>
        {painelTutor}
      </div>
    </div>
  )

  return (
    <div className="pl-espaco" ref={raiz}>
      {topologiaFixa}
      {etapas}
      <div className="pl-corpo">
        <div className="pl-pratica" ref={pratica} role="region" aria-label="Área de prática" tabIndex={0}>
          {agora}
          <div className="pl-conteudo-pratica">{lateral}{children}</div>
        </div>
        {painelTutor}
      </div>
    </div>
  )
}
