import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Check, FlaskConical, Lock, Trophy } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { NOMES_MODULOS, montarTrilha } from '../data/trilha'
import trilhaConcluida from '../assets/conquista/trilha-concluida.webp'
import './Trilha.css'

// Arte de cada parada, pelo nome do arquivo em PARADAS (`arte`); sem arte, a parada mostra o ícone.
const ARTES = Object.fromEntries(Object.entries(import.meta.glob('../assets/trilha/*.webp', { eager: true, import: 'default' }))
  .map(([caminho, url]) => [caminho.split('/').at(-1).replace('.webp', ''), url]))

const POR_LINHA = 4
const ALTURA_LINHA = 220
const COLUNAS = [125, 375, 625, 875]

// Posição de cada parada num caminho em serpentina: linhas alternam o sentido.
function posicao(indice) {
  const linha = Math.floor(indice / POR_LINHA)
  const coluna = indice % POR_LINHA
  return { x: COLUNAS[linha % 2 ? POR_LINHA - 1 - coluna : coluna], y: 90 + linha * ALTURA_LINHA }
}

function caminho(total) {
  const linhas = Math.ceil(total / POR_LINHA)
  let d = `M ${COLUNAS[0]} 90`
  for (let l = 0; l < linhas; l++) {
    const y = 90 + l * ALTURA_LINHA
    const indo = l % 2 === 0
    const ultimoDaLinha = Math.min(POR_LINHA, total - l * POR_LINHA) - 1
    const xFim = indo ? COLUNAS[ultimoDaLinha] : COLUNAS[POR_LINHA - 1 - ultimoDaLinha]
    d += ` L ${xFim} ${y}`
    if (l < linhas - 1) d += ` A ${ALTURA_LINHA / 2} ${ALTURA_LINHA / 2} 0 0 ${indo ? 1 : 0} ${xFim} ${y + ALTURA_LINHA}`
  }
  return d
}

const ICONES = { aula: BookOpen, laboratorio: FlaskConical, desafio: Trophy }
const RESUMO_ESTADO = { concluida: 'Concluída', andamento: 'Em andamento', disponivel: 'Disponível', bloqueada: 'Em breve' }

function TrilhaAluno({ usuarioId }) {
  const navigate = useNavigate()
  const [resumo, setResumo] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((d) => {
      if (!ativo) return
      if (!d.sucesso || d.progresso?.usuario_id !== usuarioId) throw new Error(d.mensagem || 'Não foi possível consultar seu progresso.')
      setResumo(d.progresso)
    }).catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [usuarioId])

  const paradas = montarTrilha(resumo)
  const concluidas = paradas.filter((p) => p.estado === 'concluida').length
  const altura = 90 + (Math.ceil(paradas.length / POR_LINHA) - 1) * ALTURA_LINHA + 150

  return <main className="principal trilha-pagina">
    <header className="trilha-cabecalho">
      <div><span className="trilha-etiqueta">JORNADA DE APRENDIZAGEM</span><h1>Trilha</h1>
        <p>Do primeiro contato com redes até o desafio final. Cada parada é uma aula ou um laboratório. Siga
          na ordem: cada aula prepara o laboratório seguinte.</p></div>
      <div className="trilha-placar" aria-label="Progresso na trilha">
        <strong>{concluidas}<small> de {paradas.length}</small></strong><span>paradas concluídas</span>
        <div className="trilha-barra"><i style={{ width: `${(concluidas / paradas.length) * 100}%` }} /></div>
      </div>
    </header>
    {resumo && paradas.length > 0 && concluidas === paradas.length && <section className="trilha-conclusao" aria-label="Trilha concluída">
      <img src={trilhaConcluida} alt="Parabéns! Você completou a trilha inicial do PingLevel." />
    </section>}
    {erro && <p className="trilha-erro" role="alert">{erro} As paradas aparecem sem o seu progresso.</p>}
    <ul className="trilha-legenda" aria-label="Legenda">
      <li><span className="ponto concluida" />Concluída</li><li><span className="ponto atual" />Você está aqui</li>
      <li><span className="ponto disponivel" />Disponível</li><li><span className="ponto bloqueada" />Em breve</li>
    </ul>
    <section className="trilha-mapa" style={{ height: altura }} aria-label="Paradas da trilha">
      <svg className="trilha-caminho" viewBox={`0 0 1000 ${altura}`} preserveAspectRatio="none" aria-hidden="true">
        <path d={caminho(paradas.length)} />
      </svg>
      <ol>
        {paradas.map((p) => {
          const { x, y } = posicao(p.indice)
          const Icone = p.estado === 'concluida' ? Check : p.estado === 'bloqueada' ? Lock : ICONES[p.tipo]
          const inicioModulo = p.indice === 0 || paradas[p.indice - 1].modulo !== p.modulo
          const classe = `trilha-parada ${p.estado} ${p.atual ? 'atual' : ''} ${p.tipo === 'desafio' ? 'final' : ''}`
          const conteudo = <>
            {inicioModulo && <span className="trilha-modulo">Módulo {p.modulo} · {NOMES_MODULOS[p.modulo]}</span>}
            <span className="trilha-marco">
              {ARTES[p.arte] ? <img src={ARTES[p.arte]} alt="" loading="lazy" /> : <Icone size={p.tipo === 'desafio' ? 30 : 22} aria-hidden="true" />}
              <i className="trilha-selo"><Icone size={14} aria-hidden="true" /></i><b>{p.indice + 1}</b></span>
            <span className="trilha-titulo">{p.titulo}</span>
            <span className="trilha-estado">{p.atual ? 'Você está aqui' : p.tipo === 'desafio' && p.estado === 'bloqueada' ? 'Objetivo final' : RESUMO_ESTADO[p.estado]}</span>
          </>
          return <li key={p.indice} className={classe} style={{ left: `${x / 10}%`, top: y }}>
            {p.estado === 'bloqueada'
              ? <div className="trilha-alvo" aria-label={`${p.titulo}: em breve`}>{conteudo}</div>
              : <button type="button" className="trilha-alvo" onClick={() => navigate(p.caminho)}
                aria-label={`${p.titulo}: ${p.atual ? 'você está aqui' : RESUMO_ESTADO[p.estado]}`}>{conteudo}</button>}
          </li>
        })}
      </ol>
    </section>
  </main>
}

export default function Trilha() {
  const { usuario } = useAuth()
  return usuario ? <TrilhaAluno key={usuario.id} usuarioId={usuario.id} /> : <main className="principal" role="status">Carregando sua sessão…</main>
}
