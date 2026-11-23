import { useEffect, useMemo, useState } from 'react'
import { embaralhar } from '../services/embaralhar'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { COMANDOS_SWITCH, OBJETIVOS, PASSOS_ARP, PCS, PERGUNTAS_MAC, PERGUNTAS_VLAN, QUADROS, conferirComandoLan } from '../services/aulaLan'
import AjudaComando from '../components/aula/AjudaComando'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaRoteamento.css'
import './AulaExplicacao.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

// Módulo 3 (trilha revisada em 15/11/2026): MAC e ARP passaram para a aula do Módulo 1; aqui ficam só como revisão.
const AULA_ID = 'servicos-lan'
const etapas = ['Revisão: MAC e ARP', 'O switch aprende', 'VLANs', 'Montar comandos', 'Conclusão']
const REVISAO = [PERGUNTAS_MAC.find((q) => q.id === 'broadcast'), PASSOS_ARP.find((q) => q.id === 'fora')]
const IMAGENS = POSES_AULA
// Etapas de perguntas: lista e a dica quando a resposta não confere.
const QUIZ = {
  0: [REVISAO, 'Revise a aula Ethernet, MAC e ARP: o broadcast chega a todos; o ARP só existe dentro da rede local.'],
  1: [QUADROS, 'O switch só manda para uma porta quando já viu aquele MAC; senão, inunda.'],
  2: [PERGUNTAS_VLAN, 'Cada VLAN é uma rede local separada, mesmo dentro do mesmo switch.'],
}

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  const ordem = useMemo(() => embaralhar(opcoes), [opcoes])
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {ordem.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

function Lan({ vlans = false }) {
  return <div className="ar-topologia" aria-label="Quatro PCs ligados a um switch">
    {PCS.map((pc) => <div key={pc.nome} className={`ar-no ${vlans && pc.nome.includes('F') ? 'roteador' : ''}`}>
      <strong>{pc.nome}{vlans ? ` · VLAN ${pc.nome.includes('V') ? 10 : 20}` : ''}</strong>
      <small>{pc.ip}</small><small>{pc.mac}</small><small>porta {pc.porta}</small></div>)}
  </div>
}

export default function AulaLan() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [respostas, setRespostas] = useState({})
  const [comandos, setComandos] = useState({})
  const [conferido, setConferido] = useState({})

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const chave = (q) => `${etapa}-${q.id}`
  function podeAvancar() {
    if (QUIZ[etapa]) return conferido[etapa] && QUIZ[etapa][0].every((q) => respostas[chave(q)] === q.correta)
    if (etapa === 3) return conferido[3] && OBJETIVOS.every((o) => conferirComandoLan(o, comandos[o.id]).ok)
    return true
  }

  async function enviar(url, corpo) {
    const resposta = await fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) })
    const dados = await resposta.json().catch(() => ({}))
    if (!resposta.ok || !dados.sucesso) throw new Error(dados.mensagem || 'Não foi possível salvar o progresso. Tente novamente.')
    return dados
  }

  async function avancar() {
    if (!podeAvancar() || salvando) return
    setSalvando(true)
    setErro('')
    try {
      if (etapa === etapas.length - 1) {
        const dados = await enviar('/api/progresso/aula/concluir', { aula_id: AULA_ID })
        setConquista({ xp: dados.progresso?.xp_concedido })
        return
      }
      await enviar('/api/progresso/aula', { aula_id: AULA_ID, etapa_atual: etapa + 1 })
      setEtapa(etapa + 1)
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  const botaoConferir = (pronto) => <button className="botao-interacao" type="button" disabled={!pronto}
    onClick={() => setConferido({ ...conferido, [etapa]: true })}><Check size={17} /> Conferir</button>
  const perguntas = () => {
    const [lista, dica] = QUIZ[etapa]
    return <>
      {lista.map((q) => <article key={q.id} className="af-caso">
        <strong>{q.pergunta || q.descricao}</strong>
        <Escolhas grupo={q.pergunta || q.descricao} opcoes={q.opcoes} valor={respostas[chave(q)]}
          aoEscolher={(v) => { setRespostas({ ...respostas, [chave(q)]: v }); setConferido({ ...conferido, [etapa]: false }) }} />
        {conferido[etapa] && <p className={`ag-retorno ${respostas[chave(q)] === q.correta ? 'ok' : 'erro'}`}>
          {respostas[chave(q)] === q.correta ? `✓ ${q.certo}` : `✗ ${dica}`}</p>}
      </article>)}
      {botaoConferir(lista.every((q) => respostas[chave(q)]))}
    </>
  }

  function conteudo() {
    if (etapa === 0) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 03 · SWITCH E VLANS</span>
        <h1>Revisão: MAC e ARP</h1>
        <p className="aula-destaque">Na aula Ethernet, MAC e ARP você viu que, dentro da rede local, o quadro é entregue pelo
          MAC e que o ARP descobre o MAC a partir do IP. Agora o foco é quem entrega esses quadros: o switch.</p>
        <Lan />
        {perguntas()}
        <p className="ag-fonte">MAC em <i>Redes para Iniciantes</i>, p. 72; ARP, p. 157; broadcast, p. 36.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">O SWITCH APRENDE</span>
        <h2>A tabela MAC do switch</h2>
        <p>O switch anota o MAC de origem de cada quadro e a porta em que ele chegou. Para decidir para onde mandar, consulta
          o MAC de destino: se conhece, manda só para aquela porta; se não, manda para todas as outras.</p>
        <Lan />
        {perguntas()}
        <pre className="af-terminal"><span className="af-prompt">switch$ bridge fdb show</span>{'\n'}02:a0:c9:14:6e:01 dev eth2 vlan 1 master br0{'\n'}02:a0:c9:3b:71:04 dev eth1 vlan 1 master br0</pre>
        <p className="ag-fonte">Tabela MAC e inundação em <i>Redes para Iniciantes</i>, p. 131.</p>
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">VLANS</span>
        <h2>Redes locais separadas no mesmo switch</h2>
        <p>Uma VLAN divide um switch em várias redes locais lógicas. Na analogia do livro, são andares de um prédio: quem
          está no mesmo andar se ouve; para falar com outro andar, é preciso passar pelo roteador.</p>
        <Lan vlans />
        {perguntas()}
        <p className="ag-fonte">VLANs, porta de acesso, PVID e tronco em <i>Redes para Iniciantes</i>, p. 96–99.</p>
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MONTAR COMANDOS</span>
        <h2>Investigar e separar pelo terminal</h2>
        <p>Nos PCs, a tabela ARP você já conhece: <code>ip neigh show</code>. O switch do laboratório é um Linux, e as portas
          dele formam uma <b>bridge</b>. Por isso, os comandos do switch começam com <code>bridge</code>.</p>
        <div className="aula-explica">
          <h3>Os comandos do switch</h3>
          <ul className="al-comandos">{COMANDOS_SWITCH.map(([comando, explicacao]) => <li key={comando}><code>{comando}</code><span>{explicacao}</span></li>)}</ul>
          <h3>Por que tirar a porta da VLAN 1?</h3>
          <p>Toda porta começa na VLAN 1. Ao entrar na VLAN 20, ela continua também na VLAN 1. Para a porta ficar só na VLAN 20,
            é preciso tirá-la da VLAN 1.</p>
        </div>
        <p>Escreva o comando para cada objetivo. Nada é executado: aqui você confere a forma que vai usar no Laboratório 8.</p>
        {OBJETIVOS.map((o) => {
          const r = conferirComandoLan(o, comandos[o.id])
          return <article key={o.id} className="af-caso">
            <label htmlFor={`al-${o.id}`}>{o.texto}</label>
            <div className="af-comando"><span aria-hidden="true">$</span>
              <input id={`al-${o.id}`} value={comandos[o.id] || ''} spellCheck={false} autoComplete="off" autoCapitalize="none"
                onChange={(e) => { setComandos({ ...comandos, [o.id]: e.target.value }); setConferido({ ...conferido, 3: false }) }} /></div>
            {conferido[3] && <p className={`ag-retorno ${r.ok ? 'ok' : 'erro'}`}>{r.ok ? '✓ ' : '✗ '}{r.retorno || 'Escreva o comando.'}</p>}
            {!r.ok && <AjudaComando ajuda={o.ajuda} />}
          </article>
        })}
        {botaoConferir(OBJETIVOS.every((o) => (comandos[o.id] || '').trim()))}
        <p className="ag-fonte">ip neigh em <i>Linux: Utilitários de Redes</i>, p. 12.</p>
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>Switch e VLANs em quatro ideias</h2>
      <div className="resumo-aprendizado">
        <div><Check /> Na rede local, o quadro é entregue pelo MAC; o ARP descobre o MAC a partir do IP.</div>
        <div><Check /> O switch aprende em que porta está cada MAC e inunda quando não sabe.</div>
        <div><Check /> Cada VLAN é uma rede local separada: VLANs diferentes não se falam sem roteador.</div>
        <div><Check /> Porta de acesso: uma VLAN, PVID e saída sem marca; tronco: várias VLANs marcadas.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 8 você investiga um switch real, atende um chamado de porta na VLAN errada e separa o Financeiro.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas aula-roteamento">
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate('/modulos')}><ArrowLeft size={18} /> Sair da aula</button>
      <div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div>
        <div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div>
      <span className="aula-tempo">12–15 min</span>
    </section>
    <section className="aula-palco">
      <div className="aula-conteudo">{conteudo()}</div>
      <aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={IMAGENS[etapa]} alt="Link, mascote do PingLevel" />
        <div className="link-identidade"><strong>Link</strong><span>Seu guia de aprendizagem</span></div></div></aside>
    </section>
    {erro && <p className="ag-erro" role="alert">{erro}</p>}
    <footer className="aula-navegacao">
      <button className="botao-voltar" onClick={() => (etapa === 0 ? navigate('/modulos') : setEtapa(etapa - 1))}>
        <ArrowLeft size={18} />{etapa === 0 ? 'Voltar aos módulos' : 'Etapa anterior'}</button>
      <div className="aula-passos" aria-label="Progresso das etapas">
        {etapas.map((nome, i) => <span key={nome} className={i <= etapa ? 'ativo' : ''} title={nome} />)}</div>
      <button className="botao-avancar" onClick={avancar} disabled={!podeAvancar() || salvando}>
        {salvando ? 'Salvando...' : etapa === etapas.length - 1 ? 'Concluir aula' : 'Continuar'}<ArrowRight size={18} /></button>
    </footer>
    {conquista && <ConquistaAula aulaId={AULA_ID} xp={conquista.xp} />}
  </main>
}
