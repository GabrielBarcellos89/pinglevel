import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, RotateCcw } from 'lucide-react'
import PreviaMensagemOsi from './PreviaMensagemOsi'
import ConquistaAula from '../components/aula/ConquistaAula'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import { COMEMORACAO, POSES } from '../assets/mascote/poses'
import { AULA_ID, VERSAO_RASCUNHO, criarClienteModelos, lerRascunho, marcoLegado } from '../services/progressoModelos'
import { PERGUNTAS_TESTE, RESPOSTAS_VAZIAS, SITUACOES_TRANSPORTE, avaliarTeste, embaralharOpcoes, limparErradas } from '../data/testeModelos'

const VAZIO = { versao: VERSAO_RASCUNHO, cena: 0, pedidoPreparado: false, mostrarBytes: false, representacaoVista: false,
  atividades: {}, passoRecebimento: 0, resumoAberto: false, transporteAberto: false, testeAberto: false, respostas: RESPOSTAS_VAZIAS }
const MAPA = [
  ['Aplicação', '7 · Aplicação, 6 · Apresentação e 5 · Sessão', 'Preparar, formatar e organizar a conversa do app.', 'HTTP, DNS, SSH'],
  ['Transporte', '4 · Transporte', 'Entregar ao programa certo e conferir se nada se perdeu.', 'TCP, UDP'],
  ['Internet', '3 · Rede', 'Endereçar e achar o caminho entre redes.', 'IP'],
  ['Acesso à rede', '2 · Enlace e 1 · Física', 'Levar até o próximo equipamento e transformar em sinais.', 'Ethernet, Wi-Fi'],
]

function TabelaTcpIp() {
  return <table className="osi-tabela-intro" aria-label="Correspondência entre TCP/IP e OSI"><thead><tr><th>TCP/IP</th><th>Camadas OSI</th><th>O que fazem</th><th>Exemplos</th></tr></thead>
    <tbody>{MAPA.map(([tcp, osi, papel, exemplos]) => <tr key={tcp}><th scope="row">{tcp}</th><td>{osi}</td><td>{papel}</td><td>{exemplos}</td></tr>)}</tbody></table>
}

// "TCP ou UDP?": comparação e quatro situações para classificar; o teste final só abre com todas certas.
function TcpOuUdp({ respostas, onResponder, conferida, onConferir }) {
  const aprovado = SITUACOES_TRANSPORTE.every((s) => respostas[s.id] === s.correta)
  return <>
    <span className="aula-etiqueta">TRANSPORTE · CAMADA 4</span><h1>TCP ou UDP? Dois jeitos de transportar</h1>
    <p className="osi-narracao">Na camada de Transporte, o TCP/IP oferece dois protocolos. A escolha depende do que importa
      mais: chegar tudo certinho ou chegar rápido.</p>
    <div className="transporte-comparacao">
      <article><span>TCP</span><h2>Como uma carta registrada</h2><p>Confere a entrega, reenvia o que se perdeu e entrega na
        ordem. Mais seguro, um pouco mais lento.</p><small>Usado em mensagens, páginas da web, arquivos e acesso remoto (SSH).</small></article>
      <article><span>UDP</span><h2>Como falar ao vivo</h2><p>Manda e segue em frente, sem conferir. Mais rápido, mas um pedaço
        pode se perder no caminho.</p><small>Usado em chamadas de vídeo e voz, jogos online e consultas de DNS.</small></article>
    </div>
    <h2 className="transporte-subtitulo">Qual combina com cada situação?</h2>
    <div className="lista-situacoes">
      {SITUACOES_TRANSPORTE.map((s, indice) => {
        const resposta = respostas[s.id]
        return <article key={s.id} className={conferida && resposta ? (resposta === s.correta ? 'correta' : 'incorreta') : ''}>
          <div className="situacao-numero">{indice + 1}</div>
          <p>{s.texto}{conferida && resposta && <small className="transporte-explicacao">{resposta === s.correta ? `✓ ${s.explicacao}` : '✗ Pense no que importa mais aqui: tudo certinho ou rapidez?'}</small>}</p>
          <div className="situacao-opcoes">{['tcp', 'udp'].map((opcao) => <button key={opcao} type="button" className={resposta === opcao ? 'selecionada' : ''}
            aria-pressed={resposta === opcao} onClick={() => onResponder(s.id, opcao)}>{opcao.toUpperCase()}</button>)}</div>
        </article>
      })}
    </div>
    <div className="acoes-desafio"><button className="botao-interacao" disabled={SITUACOES_TRANSPORTE.some((s) => !respostas[s.id])} onClick={onConferir}><Check size={17} /> Conferir respostas</button></div>
    {conferida && <div className={`feedback-desafio ${aprovado ? 'sucesso' : ''}`} role="status">{aprovado
      ? 'Isso! Agora siga para o teste final.'
      : 'Algumas ainda não. Troque as marcadas com ✗ e confira de novo.'}</div>}
  </>
}

// Fechamento da aula em três telas: "E o TCP/IP?", "TCP ou UDP?" e o teste final por situações.
function ResumoModelos({ revisao, fase, onFase, respostas, onRespostas, onVoltar, onConcluir, salvando, erro, aviso }) {
  const [conferida, setConferida] = useState(false)
  const [transporte, setTransporte] = useState({})
  const [transporteConferido, setTransporteConferido] = useState(false)
  const transporteAprovado = SITUACOES_TRANSPORTE.every((s) => transporte[s.id] === s.correta)
  const testeAberto = fase === 'teste'
  const [ordem] = useState(() => Object.fromEntries(PERGUNTAS_TESTE.map((p) => [p.id, embaralharOpcoes(p.opcoes)])))
  const { completo, aprovado, erradas } = avaliarTeste(respostas)
  function responder(id, valor) { setConferida(false); onRespostas({ ...respostas, [id]: valor }) }
  function tentarDeNovo() { setConferida(false); onRespostas(limparErradas(respostas)) }

  const imagem = fase === 'tcpip' ? linkExplicando : (testeAberto ? conferida && aprovado : transporteConferido && transporteAprovado) ? COMEMORACAO.polegares : POSES.pensativo
  return <main className="principal pagina-aula aula-modelos-pagina pagina-previa-osi">
    <p className="osi-previa-aviso"><strong>Modelos OSI e TCP/IP · {revisao ? 'Revisão da aula concluída' : 'Fechamento da aula'}</strong></p>
    <section className="aula-palco"><div className="aula-conteudo"><div className="aula-bloco osi-previa-cena">
      {fase === 'transporte' ? <TcpOuUdp respostas={transporte} conferida={transporteConferido} onConferir={() => setTransporteConferido(true)}
        onResponder={(id, valor) => { setTransporteConferido(false); setTransporte((atual) => ({ ...atual, [id]: valor })) }} />
      : !testeAberto ? <>
        <span className="aula-etiqueta">O MODELO DA INTERNET</span><h1>E o TCP/IP?</h1>
        <p className="osi-narracao">O OSI, com 7 camadas, é o mapa para estudar e para achar defeitos. Na Internet de verdade, os
          equipamentos seguem o <strong>TCP/IP</strong>, que junta as mesmas tarefas em <strong>4 grupos</strong>. A mensagem não
          faz uma nova viagem: são as mesmas tarefas, só agrupadas de outro jeito.</p>
        <TabelaTcpIp />
        <div className="fala-link"><strong>Link diz:</strong><p>Nos laboratórios você vai ouvir falar de IP, TCP e Wi-Fi o tempo
          todo: são nomes do TCP/IP. Quando algo não funcionar, pergunte “em que camada está o problema?”.</p></div>
      </> : <>
        <span className="aula-etiqueta">TESTE FINAL · QUAL CAMADA?</span><h1>Olhe a situação e diga qual camada está envolvida</h1>
        <p className="osi-narracao">Responda às sete situações e confira. Cada resposta vem com uma explicação.</p>
        <details className="osi-saiba-mais modelos-ver-tabela"><summary>Ver a tabela TCP/IP</summary><TabelaTcpIp /></details>
        <div className="modelos-teste">
          {PERGUNTAS_TESTE.map((p, indice) => {
            const certo = respostas[p.id] === p.correta
            return <article key={p.id} className={`modelos-situacao ${conferida && respostas[p.id] ? (certo ? 'certa' : 'errada') : ''}`}>
              <p><span>{indice + 1}</span>{p.texto}</p>
              <div className="teste-opcoes" role="group" aria-label={`Situação ${indice + 1}`}>
                {ordem[p.id].map(([valor, texto]) => <button key={valor} type="button" aria-pressed={respostas[p.id] === valor}
                  className={respostas[p.id] === valor ? 'selecionada' : ''} onClick={() => responder(p.id, valor)}>{texto}</button>)}
              </div>
              {conferida && respostas[p.id] && <p className="modelos-retorno" role="status"><b>{certo ? '✓ Isso!' : '✗ Ainda não.'}</b> {certo ? p.acerto : p.dica}</p>}
            </article>
          })}
        </div>
        <div className="acoes-desafio">
          <button className="botao-interacao modelos-validar" disabled={!completo || salvando} onClick={() => setConferida(true)}><Check size={17} /> Conferir respostas</button>
          {conferida && !aprovado && <button className="botao-secundario" onClick={tentarDeNovo}><RotateCcw size={17} /> Tentar de novo</button>}
        </div>
        {conferida && <div className={`feedback-desafio ${aprovado ? 'sucesso' : ''}`} role="status">{aprovado
          ? 'Tudo certo! Você reconhece as camadas em situações reais. Clique em Concluir aula.'
          : `${erradas.length} de ${PERGUNTAS_TESTE.length} respostas ainda precisam de revisão. Leia a dica de cada uma e clique em Tentar de novo: só as erradas são apagadas.`}</div>}
      </>}
      {revisao && <p className="osi-narracao">Esta aula já foi concluída. Você pode revisar e experimentar sem alterar o progresso ou receber XP novamente.</p>}
      {erro && <div className="feedback-desafio" role="alert">{erro}</div>}{aviso && <p role="status">{aviso}</p>}
    </div></div><aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={imagem} alt="Link, guia de aprendizagem" /><div className="link-identidade"><strong>Link</strong><span>{testeAberto ? 'Qual camada?' : fase === 'transporte' ? 'TCP ou UDP?' : 'Do OSI ao TCP/IP'}</span></div></div></aside></section>
    <footer className="aula-navegacao">
      <button className="botao-voltar" disabled={salvando} onClick={testeAberto ? () => onFase('transporte') : fase === 'transporte' ? () => onFase('tcpip') : onVoltar}><ArrowLeft size={18} /> {testeAberto ? 'Voltar ao TCP ou UDP' : fase === 'transporte' ? 'Voltar ao TCP/IP' : 'Rever o percurso'}</button><span />
      {fase === 'tcpip'
        ? <button className="botao-avancar" onClick={() => onFase('transporte')}>TCP ou UDP? <ArrowRight size={18} /></button>
        : fase === 'transporte'
        ? <button className="botao-avancar" disabled={!revisao && !(transporteConferido && transporteAprovado)} onClick={() => onFase('teste')}>Ir para o teste final <ArrowRight size={18} /></button>
        : <button className="botao-avancar" onClick={onConcluir} disabled={salvando || (!revisao && !(conferida && aprovado))}>{salvando ? 'Salvando…' : revisao ? 'Voltar ao início' : 'Concluir aula'}<ArrowRight size={18} /></button>}
    </footer>
  </main>
}

function AulaModelosRede() {
  const navigate = useNavigate()
  const cliente = useMemo(() => criarClienteModelos(), [])
  const [sessao, setSessao] = useState(null)
  const [estadoInicial, setEstadoInicial] = useState(VAZIO)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [resumoAberto, setResumoAberto] = useState(false)
  const [fase, setFase] = useState('tcpip')
  const [respostas, setRespostas] = useState(VAZIO.respostas)
  const [conquista, setConquista] = useState(null)
  const estadoRef = useRef(VAZIO)
  const marcoRef = useRef(-1)
  const ocupadoRef = useRef(false)
  const usuarioId = sessao?.usuarioId
  const revisao = Boolean(sessao?.registro?.concluida)
  const chave = usuarioId ? `pinglevel:modelos-osi:v${VERSAO_RASCUNHO}:usuario:${usuarioId}` : null

  useEffect(() => {
    const controller = new AbortController()
    cliente.carregar(controller.signal).then((dados) => {
      if (controller.signal.aborted) return
      let rascunho = null
      if (!dados.registro?.concluida) {
        try { rascunho = lerRascunho(localStorage.getItem(`pinglevel:modelos-osi:v${VERSAO_RASCUNHO}:usuario:${dados.usuarioId}`)) }
        catch { setAviso('Não foi possível ler a retomada deste navegador. Seu progresso no servidor foi preservado.') }
      }
      estadoRef.current = rascunho || VAZIO
      setEstadoInicial(estadoRef.current)
      marcoRef.current = dados.registro?.etapa_atual ?? -1
      setRespostas(estadoRef.current.respostas)
      setResumoAberto(estadoRef.current.resumoAberto)
      setFase(estadoRef.current.testeAberto ? 'teste' : estadoRef.current.transporteAberto ? 'transporte' : 'tcpip')
      setSessao({ ...dados, retomada: Boolean(rascunho) })
    }).catch((e) => { if (!controller.signal.aborted) setErro(e.message) })
    return () => controller.abort()
  }, [cliente])

  const guardar = useCallback((parcial) => {
    estadoRef.current = { ...estadoRef.current, ...parcial, versao: VERSAO_RASCUNHO }
    if (!chave || revisao) return
    try { localStorage.setItem(chave, JSON.stringify(estadoRef.current)) }
    catch { setAviso('Não foi possível salvar a retomada neste navegador. O progresso geral continua sendo registrado no servidor.') }
  }, [chave, revisao])

  async function executar(acao) {
    if (ocupadoRef.current) return false
    ocupadoRef.current = true; setSalvando(true); setErro('')
    try { await acao(); return true }
    catch (e) { setErro(e.message); return false }
    finally { ocupadoRef.current = false; setSalvando(false) }
  }

  async function avancar(cena) {
    if (revisao || marcoLegado(cena) <= marcoRef.current) return true
    return executar(async () => { await cliente.avancar(cena, false); marcoRef.current = marcoLegado(cena) })
  }

  async function concluir() {
    if (revisao) { navigate('/'); return }
    await executar(async () => {
      const dados = await cliente.concluir(false)
      try { localStorage.removeItem(chave) } catch { /* A conclusão já está confirmada no servidor. */ }
      setConquista({ xp: dados.progresso?.xp_concedido })
    })
  }

  if (!sessao) return <main className="principal pagina-aula"><h1>Modelos OSI e TCP/IP</h1>{erro ? <><p role="alert">{erro}</p><button className="botao-secundario" onClick={() => window.location.reload()}>Tentar novamente</button></> : <p role="status">Carregando seu progresso…</p>}</main>
  if (resumoAberto) return <>
    <ResumoModelos revisao={revisao} fase={fase} onFase={(valor) => { setFase(valor); guardar({ transporteAberto: valor !== 'tcpip', testeAberto: valor === 'teste' }) }}
      respostas={respostas} onRespostas={(valor) => { setRespostas(valor); guardar({ respostas: valor }) }}
      onVoltar={() => { guardar({ resumoAberto: false }); setEstadoInicial(estadoRef.current); setResumoAberto(false) }}
      onConcluir={concluir} salvando={salvando} erro={erro} aviso={aviso} />
    {conquista && <ConquistaAula aulaId={AULA_ID} xp={conquista.xp} />}
  </>
  return <PreviaMensagemOsi aula={{ initialState: estadoInicial, onStateChange: guardar, onAvancar: avancar,
    onResumo: () => { guardar({ resumoAberto: true }); setResumoAberto(true) }, revisao, salvando, erro,
    aviso: aviso || (sessao.registro && !revisao && !sessao.retomada ? 'A aula foi atualizada. Seu progresso anterior foi preservado; esta nova sequência começa pela introdução.' : '') }} />
}

export default AulaModelosRede
