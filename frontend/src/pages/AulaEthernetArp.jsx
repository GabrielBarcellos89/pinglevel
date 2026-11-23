import { useEffect, useMemo, useState } from 'react'
import { embaralhar } from '../services/embaralhar'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { OBJETIVOS as TODOS_OBJETIVOS, PASSOS_ARP, PCS, PERGUNTAS_MAC, conferirComandoLan } from '../services/aulaLan'
import AjudaComando from '../components/aula/AjudaComando'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaRoteamento.css'
import './AulaExplicacao.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

// Módulo 1 (trilha revisada em 15/11/2026): a base da rede local antes do Lab 2. Switch e VLANs ficam na aula do Módulo 3.
const AULA_ID = 'fundamentos-ethernet-arp'
const etapas = ['Quadro e MAC', 'ARP', 'Ver a tabela ARP', 'Conclusão']
const OBJETIVOS = TODOS_OBJETIVOS.filter((o) => o.id === 'arp')
const IMAGENS = POSES_AULA
// Etapas de perguntas: lista e a dica quando a resposta não confere.
const QUIZ = {
  0: [PERGUNTAS_MAC, 'Releia: o MAC tem 6 bytes; os três primeiros são do fabricante.'],
  1: [PASSOS_ARP, 'Quem ainda não conhece o MAC precisa perguntar a todos; o ARP só existe dentro da rede local.'],
}

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  const ordem = useMemo(() => embaralhar(opcoes), [opcoes])
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {ordem.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

function Lan() {
  return <div className="ar-topologia" aria-label="Quatro PCs na mesma rede local">
    {PCS.map((pc) => <div key={pc.nome} className="ar-no">
      <strong>{pc.nome}</strong><small>{pc.ip}</small><small>{pc.mac}</small></div>)}
  </div>
}

export default function AulaEthernetArp() {
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
    if (etapa === 2) return conferido[2] && OBJETIVOS.every((o) => conferirComandoLan(o, comandos[o.id]).ok)
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
        <span className="aula-etiqueta">MÓDULO 01 · ETHERNET, MAC E ARP</span>
        <h1>Quadro e endereço MAC</h1>
        <p className="aula-destaque">Dentro da rede local, os dados viajam em quadros Ethernet, endereçados pelo MAC: o
          endereço físico da interface. O IP diz a rede e o computador; o MAC diz a interface que recebe o quadro.</p>
        <section className="aula-explica" aria-label="Como é um endereço MAC">
          <h3>Como é um MAC</h3>
          <p>Tem <b>48 bits</b>, ou seja, <b>6 bytes</b>, escritos em hexadecimal e separados por dois-pontos. Ele vem gravado na
            interface de rede.</p>
          <div className="aula-mac" aria-label="02:a0:c9 é o fabricante; 3b:71:04 identifica a interface">
            <span className="fabricante">02:a0:c9<small>fabricante (OUI)</small></span>
            <span className="interface">3b:71:04<small>número da interface</small></span>
          </div>
          <p>Os <b>3 primeiros bytes</b> identificam o fabricante (o OUI); os 3 últimos, a interface daquele fabricante.</p>
          <p>Um MAC especial, <code>ff:ff:ff:ff:ff:ff</code>, é o <b>broadcast</b>: o quadro enviado para ele chega a todas as
            interfaces da mesma rede local.</p>
        </section>
        <Lan />
        {perguntas()}
        <p className="ag-fonte">MAC e OUI em <i>Redes para Iniciantes</i>, p. 72; broadcast, p. 36.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">ARP</span>
        <h2>Do IP ao MAC</h2>
        <p>O PC F1 vai mandar um ping ao PC F2 (10.1.1.22). Ele sabe o IP, mas o quadro precisa do MAC. Quem descobre
          é o ARP.</p>
        <section className="aula-explica" aria-label="Como o ARP funciona">
          <h3>Como o ARP funciona</h3>
          <ol>
            <li>O PC F1 pergunta para <b>todos</b> (em broadcast): “quem tem 10.1.1.22? Me diga o seu MAC.”</li>
            <li>Todos recebem, mas <b>só o dono do endereço</b> responde, direto ao PC F1, com o próprio MAC.</li>
            <li>O PC F1 guarda a resposta na <b>tabela ARP</b> (os vizinhos) e não precisa perguntar de novo por um tempo.</li>
            <li>O ARP só funciona <b>dentro da rede local</b>. Se o destino estiver em outra rede, o computador pergunta o MAC
              do <b>gateway</b>, que leva o pacote adiante.</li>
          </ol>
        </section>
        <pre className="af-terminal"><span className="af-prompt">pc-f1$ ip neigh show</span>{'\n'}10.1.1.22 lladdr 02:a0:c9:3b:71:04 REACHABLE</pre>
        {perguntas()}
        <p className="ag-fonte">ARP passo a passo em <i>Redes para Iniciantes</i>, p. 157; <code>ip neigh</code> em <i>Linux: Utilitários de Redes</i>, p. 12.</p>
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">VER A TABELA ARP</span>
        <h2>Os vizinhos que o computador já conhece</h2>
        <p>Escreva o comando. Nada é executado: aqui você confere a forma. Depois de um ping na rede local, é nessa tabela
          que aparece o MAC de quem respondeu.</p>
        {OBJETIVOS.map((o) => {
          const r = conferirComandoLan(o, comandos[o.id])
          return <article key={o.id} className="af-caso">
            <label htmlFor={`al-${o.id}`}>{o.texto}</label>
            <div className="af-comando"><span aria-hidden="true">$</span>
              <input id={`al-${o.id}`} value={comandos[o.id] || ''} spellCheck={false} autoComplete="off" autoCapitalize="none"
                onChange={(e) => { setComandos({ ...comandos, [o.id]: e.target.value }); setConferido({ ...conferido, 2: false }) }} /></div>
            {conferido[2] && <p className={`ag-retorno ${r.ok ? 'ok' : 'erro'}`}>{r.ok ? '✓ ' : '✗ '}{r.retorno || 'Escreva o comando.'}</p>}
            {!r.ok && <AjudaComando ajuda={o.ajuda} />}
          </article>
        })}
        {botaoConferir(OBJETIVOS.every((o) => (comandos[o.id] || '').trim()))}
        <p className="ag-fonte">Forma em <i>Linux: Utilitários de Redes</i>, p. 12.</p>
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>A rede local em três ideias</h2>
      <div className="resumo-aprendizado">
        <div><Check /> O IP diz a rede e o computador; o MAC (48 bits) diz a interface que recebe o quadro.</div>
        <div><Check /> O ARP descobre o MAC a partir do IP: pergunta em broadcast e só o dono do endereço responde.</div>
        <div><Check /> O ARP fica dentro da rede local: para outra rede, o computador pergunta o MAC do gateway.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 2 você monta uma rede local com um switch: cada ping entre os PCs começa com uma pergunta ARP.</p>
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
      <span className="aula-tempo">8–10 min</span>
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
