import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, Boxes, Cpu, Gauge, MemoryStick, Printer, Timer, Users } from 'lucide-react'
import './PainelCarga.css'

// Painel do professor no teste de carga: o servidor ao vivo (a cada 2 s) e o mural das folhas impressas pelos alunos.
const INTERVALO = 2000
const PONTOS = 150 // ~5 minutos de histórico nos gráficos
const ETAPAS = { acesso: 'SSH', gateway: 'Gateway', impressao: 'Impressão', comprovar: 'Validar', null: 'Concluído' }

const gib = (b) => (b / 2 ** 30).toFixed(2)
const mib = (b) => Math.round(b / 2 ** 20)

function Grafico({ pontos, maximo, cor, rotulo, unidade }) {
  const largura = 600
  const altura = 120
  const passo = largura / Math.max(1, PONTOS - 1)
  const inicio = PONTOS - pontos.length
  const y = (v) => altura - (Math.min(v, maximo) / maximo) * (altura - 8) - 4
  const linha = pontos.map((v, i) => `${((inicio + i) * passo).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const ultimo = pontos.at(-1)
  return <figure className="pc-grafico">
    <figcaption><span>{rotulo}</span><strong>{ultimo == null ? '—' : `${ultimo}${unidade}`}</strong></figcaption>
    <svg viewBox={`0 0 ${largura} ${altura}`} preserveAspectRatio="none" role="img" aria-label={`${rotulo}: últimos 5 minutos`}>
      {[0.25, 0.5, 0.75].map((f) => <line key={f} x1="0" x2={largura} y1={altura * f} y2={altura * f} className="pc-grade" />)}
      {pontos.length > 1 && <polygon points={`${inicio * passo},${altura} ${linha} ${(PONTOS - 1) * passo},${altura}`} fill={cor} opacity=".15" />}
      {pontos.length > 1 && <polyline points={linha} fill="none" stroke={cor} strokeWidth="2.5" vectorEffect="non-scaling-stroke" />}
    </svg>
    <small>0 a {maximo}{unidade} · últimos 5 minutos</small>
  </figure>
}

export default function PainelCarga() {
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState('')
  const [historico, setHistorico] = useState({ cpu: [], livre: [], ambientes: [], memoriaLabs: [] })
  const vivo = useRef(true)

  useEffect(() => {
    vivo.current = true
    let temporizador
    async function atualizar() {
      try {
        const resposta = await fetch('/api/painel-carga', { credentials: 'same-origin' })
        const json = await resposta.json()
        if (!resposta.ok || !json.sucesso) throw new Error(json.mensagem || 'Painel indisponível.')
        if (!vivo.current) return
        setDados(json)
        setErro('')
        setHistorico((h) => {
          const mais = (lista, v) => [...lista, v].slice(-PONTOS)
          return {
            cpu: json.cpu_percentual == null ? h.cpu : mais(h.cpu, json.cpu_percentual),
            livre: mais(h.livre, Number(gib(json.memoria.disponivel))),
            ambientes: mais(h.ambientes, json.ambientes.total),
            memoriaLabs: mais(h.memoriaLabs, mib(json.conteineres.memoria)),
          }
        })
      } catch (e) {
        if (vivo.current) setErro(e.message)
      } finally {
        if (vivo.current) temporizador = setTimeout(atualizar, INTERVALO)
      }
    }
    atualizar()
    return () => { vivo.current = false; clearTimeout(temporizador) }
  }, [])

  const memoriaTotal = dados ? Number(gib(dados.memoria.total)) : 8
  const folhas = (dados?.alunos || []).flatMap((a) => a.folhas.map((f) => ({ ...f, login: a.login }))).sort((a, b) => b.hora - a.hora)
  const criacoes = (dados?.criacoes || []).filter((c) => c.laboratorio === 'suporte-remoto')
  const media = criacoes.length ? (criacoes.reduce((s, c) => s + c.segundos, 0) / criacoes.length).toFixed(1) : null
  const maiorCriacao = Math.max(10, ...criacoes.map((c) => c.segundos))

  return <main className="principal painel-carga">
    <header className="pc-cabecalho">
      <div><span className="pc-etiqueta">TESTE DE CARGA · AO VIVO</span><h1>Painel do servidor</h1>
        <p>Cada aluno roda a própria rede (7 contêineres) no mesmo servidor. Atualiza a cada 2 segundos.</p></div>
      <Link className="pc-link" to="/teste-de-carga">Abrir a atividade</Link>
    </header>
    {erro && <p className="pc-erro" role="alert">{erro}</p>}

    <section className="pc-numeros" aria-label="Agora">
      <article><Users size={20} aria-hidden="true" /><span>Alunos com ambiente</span><strong>{dados?.alunos?.length ?? '—'}</strong>
        <small>{dados ? `${dados.ambientes.total} ambientes no total` : ''}</small></article>
      <article><Boxes size={20} aria-hidden="true" /><span>Contêineres dos labs</span><strong>{dados?.conteineres.quantidade ?? '—'}</strong>
        <small>{dados ? `${mib(dados.conteineres.memoria)} MiB em uso` : ''}</small></article>
      <article><Cpu size={20} aria-hidden="true" /><span>CPU do servidor</span><strong>{dados?.cpu_percentual ?? '—'}%</strong>
        <small>{dados ? `${dados.nucleos} núcleos · labs usam ${dados.conteineres.cpu_nucleos ?? '—'}` : ''}</small></article>
      <article><MemoryStick size={20} aria-hidden="true" /><span>Memória livre</span><strong>{dados ? gib(dados.memoria.disponivel) : '—'} GiB</strong>
        <small>{dados ? `de ${gib(dados.memoria.total)} GiB` : ''}</small></article>
      <article><Gauge size={20} aria-hidden="true" /><span>Carga (1 min)</span><strong>{dados?.carga?.[0] ?? '—'}</strong>
        <small>{dados ? `5 min ${dados.carga[1]} · 15 min ${dados.carga[2]}` : ''}</small></article>
      <article><Timer size={20} aria-hidden="true" /><span>Subir um ambiente</span><strong>{media ? `${media} s` : '—'}</strong>
        <small>{criacoes.length ? `média de ${criacoes.length}` : 'nenhum ainda'}</small></article>
    </section>

    <section className="pc-graficos" aria-label="Últimos 5 minutos">
      <Grafico pontos={historico.cpu} maximo={100} cor="#ff4f6d" rotulo="CPU do servidor" unidade="%" />
      <Grafico pontos={historico.livre} maximo={memoriaTotal} cor="#4c9dff" rotulo="Memória livre" unidade=" GiB" />
      <Grafico pontos={historico.ambientes} maximo={Math.max(20, ...historico.ambientes)} cor="#2fbf71" rotulo="Ambientes ativos" unidade="" />
      <Grafico pontos={historico.memoriaLabs} maximo={Math.max(500, ...historico.memoriaLabs)} cor="#ffb020" rotulo="Memória dos labs" unidade=" MiB" />
    </section>

    <div className="pc-colunas">
      <section className="pc-bloco" aria-label="Alunos">
        <h2><Activity size={18} aria-hidden="true" /> Alunos</h2>
        {dados?.alunos?.length ? <table className="pc-tabela"><thead><tr><th>Aluno</th><th>Etapa</th><th>Subiu em</th><th>Folhas</th></tr></thead>
          <tbody>{dados.alunos.map((a) => <tr key={a.login}><td>{a.login}</td><td><span className={`pc-etapa pc-${a.etapa || 'fim'}`}>{ETAPAS[a.etapa] || a.etapa}</span></td>
            <td>{a.tempo_criacao ? `${a.tempo_criacao} s` : '—'}</td><td>{a.folhas.length}</td></tr>)}</tbody></table>
          : <p className="pc-vazio">Nenhum aluno com a atividade aberta.</p>}
        {criacoes.length > 0 && <>
          <h3>Tempo para subir cada ambiente</h3>
          <div className="pc-barras" role="img" aria-label="Segundos para subir cada ambiente, do mais antigo ao mais recente">
            {criacoes.map((c, i) => <span key={`${c.momento}-${i}`} style={{ height: `${(c.segundos / maiorCriacao) * 100}%` }} title={`${c.segundos} s`} />)}
          </div>
        </>}
      </section>

      <section className="pc-bloco pc-mural" aria-label="Mural das folhas impressas">
        <h2><Printer size={18} aria-hidden="true" /> Mural · folhas impressas</h2>
        {folhas.length ? <ul>{folhas.map((f) => <li key={`${f.login}-${f.hora}-${f.texto}`}>
          <q>{f.texto}</q><small>{f.login} · {new Date(f.hora * 1000).toLocaleTimeString('pt-BR')}</small></li>)}</ul>
          : <p className="pc-vazio">As folhas aparecem aqui assim que cada impressora recebe.</p>}
      </section>
    </div>
  </main>
}
