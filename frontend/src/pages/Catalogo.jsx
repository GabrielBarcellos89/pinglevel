import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpen, FlaskConical } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { ATIVIDADES, MODULOS, situacaoAtividade } from '../data/catalogo'
import { PARADAS } from '../data/trilha'
import linkEnsinando from '../assets/mascote/link-kit-v2/link-v2-ensinando.webp'
import './Catalogo.css'

// Arte de cada parada, na ordem da trilha (as mesmas da Trilha e da Início).
const ARTES = Object.entries(import.meta.glob('../assets/trilha/*.webp', { eager: true, import: 'default' }))
  .sort(([a], [b]) => a.localeCompare(b)).map(([, url]) => url)

const TITULOS = {
  todas: { titulo: 'Aulas e laboratórios', texto: 'Continue seus estudos ou revise o que já concluiu. A ordem segue a trilha.' },
  aula: { titulo: 'Aulas', texto: 'A teoria antes de cada laboratório. Continue de onde parou ou revise o que já concluiu.' },
  laboratorio: { titulo: 'Laboratórios', texto: 'Escolha um laboratório para praticar em uma rede real.' },
}

function CatalogoAluno({ usuarioId, tipoInicial = 'todas' }) {
  const navigate = useNavigate()
  const [resumo, setResumo] = useState(null)
  const [erro, setErro] = useState('')
  const [tentativa, setTentativa] = useState(0)
  const [busca, setBusca] = useState('')
  // Cada aba mostra um tipo só (Aulas ou Laboratórios); a sequência completa, misturada, fica na Trilha.
  const tipo = tipoInicial
  const [moduloFiltro, setModuloFiltro] = useState('todos')
  const [situacaoFiltro, setSituacaoFiltro] = useState('todas')
  const total = ATIVIDADES.filter((item) => tipo === 'todas' || item.tipo === tipo).length
  const normalizar = (s) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  const lista = ATIVIDADES.filter((item) => (tipo === 'todas' || item.tipo === tipo)
    && (moduloFiltro === 'todos' || item.modulo === moduloFiltro)
    && normalizar(`${item.titulo} ${item.descricao}`).includes(normalizar(busca.trim()))
    && (situacaoFiltro === 'todas' || (resumo && situacaoAtividade(item, resumo).id === situacaoFiltro)))

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 15000)
    let ativo = true
    async function carregar() {
      try {
        const r = await fetch('/api/progresso/me', { credentials: 'same-origin', signal: controller.signal })
        const d = await r.json()
        if (!r.ok || !d.sucesso) throw new Error(d.mensagem || 'Não foi possível consultar seu progresso.')
        if (d.progresso?.usuario_id !== usuarioId || !Array.isArray(d.progresso.aulas) || !Array.isArray(d.progresso.laboratorios)) throw new Error('O resumo de progresso está inválido ou não pertence à sua sessão.')
        if (ativo) { setResumo(d.progresso); setErro('') }
      } catch (e) { if (ativo) setErro(e.name === 'AbortError' ? 'A consulta demorou demais. Tente novamente.' : e.message) }
      finally { clearTimeout(timer) }
    }
    void carregar()
    return () => { ativo = false; controller.abort(); clearTimeout(timer) }
  }, [usuarioId, tentativa])

  return <main className="principal catalogo-pagina">
    <header className="catalogo-hero"><div><span className="catalogo-etiqueta">CONTEÚDO DIDÁTICO</span><h1>{TITULOS[tipoInicial].titulo}</h1><p>{TITULOS[tipoInicial].texto}</p></div><img src={linkEnsinando} alt="Link apresentando as atividades" /></header>
    {!resumo && !erro && <p role="status">Consultando seu progresso…</p>}
    {erro && <section className="catalogo-erro" role="alert"><strong>Não foi possível confirmar seu progresso</strong><p>{erro}</p><button className="botao-secundario" onClick={() => { setResumo(null); setErro(''); setTentativa((n) => n + 1) }}>Tentar novamente</button></section>}
    <section className="catalogo-controles" aria-label="Filtros de atividades">
      <label><span>Buscar conteúdo</span><input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome da aula ou assunto" /></label>
      <label><span>Módulo</span><select aria-label="Módulo" value={moduloFiltro} onChange={(e) => setModuloFiltro(e.target.value)}><option value="todos">Todos os módulos</option>{MODULOS.map((m) => <option key={m.id} value={m.id}>{m.titulo}</option>)}</select></label>
      <label><span>Situação</span><select aria-label="Situação" value={situacaoFiltro} onChange={(e) => setSituacaoFiltro(e.target.value)}><option value="todas">Todas as situações</option><option value="pendente">Pendentes</option><option value="andamento">Em andamento</option><option value="concluida">Concluídas</option></select></label>
    </section>
    <p className="catalogo-contagem" role="status" aria-live="polite">{lista.length} de {total} {tipo === 'aula' ? 'aulas' : tipo === 'laboratorio' ? 'laboratórios' : 'atividades'} · a sequência completa, com aulas e laboratórios juntos, está na Trilha</p>
    {resumo && !lista.length && <section className="catalogo-vazio"><h2>Nenhuma atividade encontrada</h2><p>Experimente outro assunto ou ajuste os filtros.</p></section>}
    {MODULOS.filter((m) => lista.some((a) => a.modulo === m.id)).map((modulo) => <section className="catalogo-modulo" key={modulo.id} aria-labelledby={`modulo-${modulo.id}`}><h2 id={`modulo-${modulo.id}`}>{modulo.titulo}</h2><div className="catalogo-grade">{lista.filter((a) => a.modulo === modulo.id).map((item) => {
      const situacao = resumo ? situacaoAtividade(item, resumo) : null
      const Icone = item.tipo === 'aula' ? BookOpen : FlaskConical
      const parada = PARADAS.findIndex((p) => p.atividade === item.id) + 1
      return <article className="catalogo-card" data-atividade={item.id} key={item.id} title={item.retomada}>
        <div className="catalogo-card-topo"><span><Icone size={15} aria-hidden="true" />{item.tipo === 'aula' ? 'Aula' : 'Laboratório'}{parada > 0 && <em>· parada {parada}</em>}</span><strong className={`catalogo-situacao ${situacao?.id || ''}`}>{situacao?.texto || (erro ? 'Progresso indisponível' : 'Consultando…')}</strong></div>
        <div className="catalogo-card-corpo">{parada > 0 && <img src={ARTES[parada - 1]} alt="" loading="lazy" />}<div><h3>{item.titulo}</h3><p>{item.descricao}</p></div></div>
        {situacao?.percentual !== null && situacao && <div className="catalogo-progresso"><div role="progressbar" aria-label={`Progresso de ${item.titulo}`} aria-valuenow={situacao.percentual} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${situacao.percentual}%` }} /></div><span>{situacao.percentual}%</span></div>}
        <div className="catalogo-card-acoes">
          <button className="catalogo-acao" disabled={!situacao} onClick={() => navigate(item.caminho)}>{situacao?.acao || 'Aguarde'}<ArrowRight size={15} aria-hidden="true" /></button>
          {item.id === 'enderecamento-ipv4' && <button className="catalogo-acao-secundaria" onClick={() => navigate('/modulos/enderecamento/ipv4/previa')}>Explorar sem progresso</button>}
        </div>
      </article>
    })}</div></section>)}
  </main>
}

function Catalogo({ tipoInicial }) {
  const { usuario } = useAuth()
  return usuario ? <CatalogoAluno key={`${usuario.id}-${tipoInicial}`} usuarioId={usuario.id} tipoInicial={tipoInicial} /> : <main className="principal" role="status">Carregando sua sessão…</main>
}
export default Catalogo
