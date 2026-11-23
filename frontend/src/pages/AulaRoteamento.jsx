import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Computer, Mail, RotateCcw } from 'lucide-react'
import {
  EQUIPAMENTOS, OBJETIVOS, PERCURSO, PERGUNTAS_CONHECE, PERGUNTAS_PERCURSO, PERGUNTAS_SALTO, PERGUNTAS_VOLTA, ROTA_R1,
  TABELAS, TRECHOS, VOLTA, conferirRota,
} from '../services/aulaRoteamento'
import { embaralhar } from '../services/embaralhar'
import AjudaComando from '../components/aula/AjudaComando'
import IconeRoteador from '../components/laboratorio/IconeRoteador'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaExplicacao.css'
import './AulaRoteamento.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'planejamento-roteamento'
const etapas = ['Do Lab 6 às filiais', 'O que cada roteador conhece', 'Rota estática', 'Seguir o pacote', 'Ida e volta',
  'Montar comandos', 'Conclusão']
const [descontraido, pensativo, explicando, curioso, incentivando, comemorando] = POSES_AULA
const IMAGENS = [descontraido, curioso, explicando, pensativo, curioso, incentivando, comemorando]
const NOMES = Object.fromEntries(EQUIPAMENTOS.map((e) => [e.id, e.nome]))

// Topologia da aula: equipamentos com ícones e, em cada cabo, a rede do trecho e os IPs das duas pontas.
// `ativo` destaca um equipamento (o pacote está nele) e `falha` marca onde o pacote foi descartado.
function Topologia({ ativo, falha }) {
  return <div className="rt-topologia" aria-label="PC A, R1, R2 e PC B ligados em linha">
    {EQUIPAMENTOS.map((e, i) => <div key={e.id} className="rt-par">
      <div className={`rt-no ${e.tipo} ${ativo === e.id ? 'ativo' : ''} ${falha === e.id ? 'falha' : ''}`}>
        {ativo === e.id && <Mail className="rt-pacote" size={18} aria-label="pacote" />}
        <span className="rt-icone">{e.tipo === 'pc' ? <Computer size={26} /> : <IconeRoteador aria-hidden="true" />}</span>
        <strong>{e.nome}</strong>
      </div>
      {i < TRECHOS.length && <div className="rt-trecho">
        <div className="rt-ips"><span>{TRECHOS[i].esquerda}</span><span>{TRECHOS[i].direita}</span></div>
        <div className="rt-cabo" />
        <div className="rt-rede"><b>{TRECHOS[i].nome}</b><code>{TRECHOS[i].rede}</code></div>
      </div>}
    </div>)}
  </div>
}

function Tabela({ no, linhas, destaque, titulo }) {
  return <div className="rt-tabela">
    <span>{titulo || `${NOMES[no]}$ ip route`}</span>
    {linhas.map((l, i) => <code key={l.linha} className={`${l.tipo} ${destaque === i ? 'usada' : ''}`}>{l.linha}
      <em>{l.tipo === 'direta' ? 'direta' : l.tipo === 'padrao' ? 'rota padrão' : 'estática'}</em></code>)}
  </div>
}

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  const ordem = useMemo(() => embaralhar(opcoes), [opcoes])
  return <div className="rt-opcoes" role="group" aria-label={grupo}>
    {ordem.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

function Perguntas({ lista, respostas, aoResponder, conferido }) {
  return <div className="rt-perguntas">
    {lista.map((q, i) => <article key={q.id} className="rt-pergunta">
      <strong><span>{i + 1}</span>{q.pergunta}</strong>
      <Escolhas grupo={q.pergunta} opcoes={q.opcoes} valor={respostas[q.id]} aoEscolher={(v) => aoResponder(q.id, v)} />
      {conferido && <p className={`ag-retorno ${respostas[q.id] === q.correta ? 'ok' : 'erro'}`}>
        {respostas[q.id] === q.correta ? `✓ ${q.certo}` : `✗ ${q.erro}`}</p>}
    </article>)}
  </div>
}

// Passo a passo do pacote: botão para avançar e, em cada parada, a explicação e a tabela consultada.
function Percurso({ passos, indice, setIndice, inicio, rotulo, tabelaDe }) {
  const atual = passos[indice]
  return <div className="rt-percurso">
    {atual ? <div className={`rt-passo ${atual.ok === false ? 'erro' : ''}`}>
      <span>{rotulo} · passo {indice + 1} de {passos.length} · {NOMES[atual.no]}</span>
      <p>{atual.texto}</p>
      {tabelaDe(atual)}
    </div> : <p className="rt-passo vazio">{inicio[0]}</p>}
    <div className="rt-botoes">
      {indice < passos.length - 1
        ? <button className="botao-interacao" type="button" onClick={() => setIndice(indice + 1)}><Mail size={17} />
          {indice < 0 ? inicio[1] : 'Próximo salto'}</button>
        : <button className="ag-secundario" type="button" onClick={() => setIndice(-1)}><RotateCcw size={16} /> Ver de novo</button>}
    </div>
  </div>
}

const QUIZ = { 1: PERGUNTAS_CONHECE, 2: PERGUNTAS_SALTO, 3: PERGUNTAS_PERCURSO, 4: PERGUNTAS_VOLTA }

export default function AulaRoteamento() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [respostas, setRespostas] = useState({})
  const [comandos, setComandos] = useState({})
  const [conferido, setConferido] = useState({})
  const [passo, setPasso] = useState(-1)
  const [volta, setVolta] = useState(-1)
  // O percurso só precisa ser visto até o fim uma vez; "Ver de novo" não trava as perguntas.
  const [viuIda, setViuIda] = useState(false)
  const [viuVolta, setViuVolta] = useState(false)

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])
  useEffect(() => { if (passo === PERCURSO.length - 1) setViuIda(true) }, [passo])
  useEffect(() => { if (volta === VOLTA.length - 1) setViuVolta(true) }, [volta])

  const quizCerto = (lista) => lista.every((q) => respostas[q.id] === q.correta)
  function podeAvancar() {
    if (QUIZ[etapa]) return conferido[etapa] && quizCerto(QUIZ[etapa])
    if (etapa === 5) return conferido[5] && OBJETIVOS.every((o) => conferirRota(o, comandos[o.id]).ok)
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

  const responder = (id, valor) => { setRespostas({ ...respostas, [id]: valor }); setConferido({ ...conferido, [etapa]: false }) }
  const botaoConferir = (pronto) => <button className="botao-interacao" type="button" disabled={!pronto}
    onClick={() => setConferido({ ...conferido, [etapa]: true })}><Check size={17} /> Conferir</button>
  const quiz = () => <section className="rt-bloco-perguntas" aria-label="Perguntas da etapa">
    <h3>Agora responda</h3>
    <Perguntas lista={QUIZ[etapa]} respostas={respostas} aoResponder={responder} conferido={conferido[etapa]} />
    {botaoConferir(QUIZ[etapa].every((q) => respostas[q.id]))}
  </section>

  function conteudo() {
    if (etapa === 0) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 02 · ROTEAMENTO ESTÁTICO</span>
        <h1>Do Lab 6 às duas filiais</h1>
        <p className="aula-destaque">No Lab 6, um único roteador ligava os três setores. Agora a empresa tem duas filiais, cada
          uma com o seu roteador. O que muda?</p>
        <div className="aula-explica">
          <h3>O que você já fez no Lab 6</h3>
          <ul>
            <li>Você deu um endereço a cada interface do roteador, uma em cada setor.</li>
            <li>Com isso, o roteador passou a <b>tocar</b> as três redes. Cada rede que ele toca aparece sozinha na tabela
              dele: é uma <b>rota direta</b> (no <code>ip route</code>, a linha com <code>dev</code> e sem <code>via</code>).</li>
            <li>Nos PCs, você configurou a <b>rota padrão</b>: tudo o que não é da rede do PC vai para o gateway.</li>
          </ul>
          <h3>O que é novo agora</h3>
          <p>Com <b>dois roteadores</b>, cada um toca só a rede da sua filial e o enlace entre eles. A rede da outra filial
            fica longe: ele não a conhece, e nada aparece sozinho na tabela dele sobre ela.</p>
        </div>
        <Topologia />
        <p className="rt-legenda">Cada cabo é uma rede. Os números nas pontas são o final do IP de cada equipamento nessa rede:
          o R1, por exemplo, é <code>192.168.10.1</code> na Filial A e <code>10.0.0.1</code> no enlace.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">O QUE CADA ROTEADOR CONHECE</span>
        <h2>Só as redes que toca</h2>
        <p>Antes de configurar qualquer rota, veja a tabela de cada equipamento. Para cada pacote, o equipamento procura uma
          linha que contenha o destino. Se nenhuma contiver e não houver rota padrão, ele <b>descarta</b> o pacote.</p>
        <Topologia />
        <div className="rt-tabelas">{['pca', 'r1', 'r2', 'pcb'].map((no) => <Tabela key={no} no={no} linhas={TABELAS[no]} />)}</div>
        {quiz()}
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">ROTA ESTÁTICA E PRÓXIMO SALTO</span>
        <h2>Ensinar o caminho ao R1</h2>
        <p>Uma <b>rota estática</b> é uma linha que você escreve na tabela do roteador: “para esta rede, entregue a este
          vizinho”. O vizinho é o <b>próximo salto</b>.</p>
        <div className="rt-anatomia" aria-label="Partes do comando">
          <span><code>ip route add</code><small>adiciona uma rota</small></span>
          <span className="destino"><code>192.168.20.0/24</code><small>rede de destino, com o prefixo</small></span>
          <span className="via"><code>via 10.0.0.2</code><small>próximo salto: o R2, no enlace</small></span>
        </div>
        <div className="aula-explica">
          <h3>Por que 10.0.0.2 e não 192.168.20.1?</h3>
          <p>O próximo salto precisa estar numa rede que o roteador <b>toca</b>. O R1 alcança o R2 pelo enlace
            (10.0.0.0/30); a interface 192.168.20.1 fica do outro lado, numa rede que o R1 não conhece. O R1 só entrega ao
            vizinho, e o R2 resolve o resto.</p>
          <h3>E o que não está na rota?</h3>
          <p>A rota vale só para a rede que ela diz. Um destino fora de todas as linhas, sem rota padrão, continua descartado.</p>
        </div>
        <Tabela no="r1" linhas={[...TABELAS.r1, ROTA_R1]} destaque={2} titulo="R1$ ip route   (depois da rota estática)" />
        <p className="rt-legenda">Confira na topologia o IP de cada roteador em cada rede antes de responder.</p>
        <Topologia />
        {quiz()}
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">SEGUIR O PACOTE</span>
        <h2>Do PC A ao PC B, salto a salto</h2>
        <p>O R1 já tem a rota estática. O PC A faz ping ao PC B (192.168.20.10). Avance o pacote e veja, em cada
          equipamento, a linha da tabela que ele usa.</p>
        <Topologia ativo={PERCURSO[passo]?.no} />
        <Percurso passos={PERCURSO} indice={passo} setIndice={setPasso} rotulo="Pedido"
          inicio={['O pacote está pronto para sair do PC A.', 'Enviar o pacote']}
          tabelaDe={(p) => p.linha !== null && <Tabela no={p.no} linhas={p.no === 'r1' ? [...TABELAS.r1, ROTA_R1] : TABELAS[p.no]} destaque={p.linha} />} />
        {viuIda && quiz()}
      </div>
    }
    if (etapa === 4) {
      const atual = VOLTA[volta]
      return <div className="aula-bloco">
        <span className="aula-etiqueta">IDA E VOLTA</span>
        <h2>Só a ida não basta</h2>
        <div className="aula-explica">
          <p>Um ping só funciona se o pedido <b>chega</b> e a resposta <b>volta</b>. Cada roteador decide sozinho, olhando só a
            própria tabela. A resposta do PC B é um pacote novo, com destino 192.168.10.10, e precisa de caminho até lá.</p>
          <p>Até agora, só o R1 tem rota estática. Veja o que acontece com a resposta.</p>
        </div>
        <Topologia ativo={atual?.no} falha={atual && !atual.ok ? atual.no : undefined} />
        <Percurso passos={VOLTA} indice={volta} setIndice={setVolta} rotulo="Resposta"
          inicio={['O PC B recebeu o pedido e vai responder.', 'Enviar a resposta']}
          tabelaDe={(p) => <Tabela no={p.no} linhas={TABELAS[p.no]} destaque={p.no === 'pcb' ? 0 : undefined} />} />
        {viuVolta && quiz()}
      </div>
    }
    if (etapa === 5) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MONTAR COMANDOS</span>
        <h2>Rotas estáticas pelo terminal</h2>
        <p>Escreva o comando de cada objetivo, na forma <code>ip route add &lt;rede&gt;/&lt;prefixo&gt; via &lt;próximo salto&gt;</code>.
          Nada é executado: aqui você confere a forma que vai usar no Laboratório 7.</p>
        <Topologia />
        {OBJETIVOS.map((o) => {
          const r = conferirRota(o, comandos[o.id])
          return <article key={o.id} className="af-caso">
            <label htmlFor={`ar-${o.id}`}>{o.texto}</label>
            <div className="af-comando"><span aria-hidden="true">$</span>
              <input id={`ar-${o.id}`} value={comandos[o.id] || ''} spellCheck={false} autoComplete="off" autoCapitalize="none"
                onChange={(e) => { setComandos({ ...comandos, [o.id]: e.target.value }); setConferido({ ...conferido, 5: false }) }} /></div>
            {conferido[5] && <p className={`ag-retorno ${r.ok ? 'ok' : 'erro'}`}>{r.ok ? '✓ ' : '✗ '}{r.retorno || 'Escreva o comando.'}</p>}
            {!r.ok && <AjudaComando ajuda={o.ajuda} />}
          </article>
        })}
        {botaoConferir(OBJETIVOS.every((o) => (comandos[o.id] || '').trim()))}
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>Rotas estáticas em quatro ideias</h2>
      <div className="resumo-aprendizado">
        <div><Check /> O roteador conhece sozinho só as redes que toca: as rotas diretas.</div>
        <div><Check /> Rota estática: rede de destino e próximo salto, o vizinho que ele alcança direto.</div>
        <div><Check /> Sem linha para o destino nem rota padrão, o pacote é descartado.</div>
        <div><Check /> Comunicação é ida e volta: cada roteador precisa de caminho até a rede do outro lado.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 7 você liga duas filiais de verdade: diagnostica, planeja as rotas e aplica uma de cada vez, para
          ver a ida funcionar antes da volta.</p>
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
      <span className="aula-tempo">15 min</span>
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
