import { useEffect, useMemo, useState } from 'react'
import { Activity, BookOpenCheck, KeyRound, Plus, UsersRound, Zap } from 'lucide-react'
import './PainelProfessor.css'

function PainelProfessor() {
  const [turmas, setTurmas] = useState([])
  const [turmaAtual, setTurmaAtual] = useState(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [modal, setModal] = useState(false)
  const [nome, setNome] = useState('')
  const [quantidade, setQuantidade] = useState(10)
  const [credenciais, setCredenciais] = useState([])
  const [criando, setCriando] = useState(false)

  async function carregar() {
    try {
      const resposta = await fetch('/api/professor/turmas')
      const dados = await resposta.json()
      if (!resposta.ok) throw new Error(dados.mensagem || 'Não foi possível carregar as turmas.')
      setTurmas(dados.turmas)
      setTurmaAtual((atual) => atual && dados.turmas.some((t) => t.id === atual)
        ? atual : dados.turmas[0]?.id ?? null)
      setErro('')
    } catch (falha) {
      setErro(falha.message)
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
    const intervalo = setInterval(carregar, 15000)
    return () => clearInterval(intervalo)
  }, [])

  const turma = turmas.find((item) => item.id === turmaAtual)
  const resumo = useMemo(() => {
    const alunos = turma?.alunos ?? []
    return {
      alunos: alunos.length,
      concluidas: alunos.filter((a) => a.aulas_concluidas > 0).length,
      xp: alunos.reduce((total, a) => total + a.xp_total, 0),
      laboratorios: alunos.filter((a) => a.laboratorio).length,
    }
  }, [turma])

  async function criar(evento) {
    evento.preventDefault()
    setCriando(true)
    setErro('')
    try {
      const resposta = await fetch('/api/professor/turmas/criar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, quantidade: Number(quantidade) }),
      })
      const dados = await resposta.json()
      if (!resposta.ok) throw new Error(dados.mensagem || 'Não foi possível criar a turma.')
      setCredenciais(dados.turma.credenciais)
      setNome('')
      await carregar()
    } catch (falha) {
      setErro(falha.message)
    } finally {
      setCriando(false)
    }
  }

  async function redefinir(aluno) {
    const resposta = await fetch('/api/professor/alunos/redefinir-senha', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario_id: aluno.usuario_id }),
    })
    const dados = await resposta.json()
    if (resposta.ok) window.alert(`Senha temporária de ${aluno.nome}: ${dados.senha_temporaria}`)
    else setErro(dados.mensagem)
  }

  return (
    <main className="principal professor-pagina">
      <header className="professor-cabecalho">
        <div><span className="professor-etiqueta">ACOMPANHAMENTO DA TURMA</span><h1>Painel do professor</h1><p>Acompanhe o progresso dos alunos e prepare os acessos da próxima atividade.</p></div>
        <button className="botao-principal" onClick={() => { setModal(true); setCredenciais([]) }}><Plus size={18} /> Nova turma</button>
      </header>

      {erro && <div className="professor-erro">{erro}</div>}
      {carregando ? <div className="professor-vazio">Carregando turmas...</div> : turmas.length === 0 ? <div className="professor-vazio">Crie a primeira turma para começar.</div> : <>
        <div className="professor-seletor">
          <label>Turma acompanhada</label>
          <select value={turmaAtual ?? ''} onChange={(e) => setTurmaAtual(Number(e.target.value))}>{turmas.map((item) => <option key={item.id} value={item.id}>{item.nome} · {item.total_alunos} alunos</option>)}</select>
        </div>
        <section className="professor-resumos">
          <article><UsersRound /><div><strong>{resumo.alunos}</strong><span>alunos</span></div></article>
          <article><BookOpenCheck /><div><strong>{resumo.concluidas}</strong><span>iniciaram a jornada</span></div></article>
          <article><Zap /><div><strong>{resumo.xp}</strong><span>XP da turma</span></div></article>
          <article><Activity /><div><strong>{resumo.laboratorios}</strong><span>laboratórios ativos</span></div></article>
        </section>
        <section className="professor-tabela-card">
          <div className="professor-tabela-topo"><div><span className="professor-etiqueta">VISÃO INDIVIDUAL</span><h2>{turma?.nome}</h2></div><span>Atualização automática a cada 15 segundos</span></div>
          <div className="professor-tabela-wrap"><table><thead><tr><th>Aluno</th><th>Progresso da aula</th><th>XP</th><th>Laboratório</th><th>Conta</th><th></th></tr></thead><tbody>{turma?.alunos.map((aluno) => <tr key={aluno.usuario_id}><td><strong>{aluno.nome}</strong><span>@{aluno.login}</span></td><td><div className="professor-progresso"><div><span style={{ width: `${aluno.percentual}%` }} /></div><b>{aluno.percentual}%</b></div></td><td><b>{aluno.xp_total} XP</b></td><td><span className={`professor-status ${aluno.laboratorio ? 'online' : ''}`}>{aluno.laboratorio ? `Sessão ${aluno.laboratorio.session_id}` : 'Inativo'}</span></td><td><span className={`professor-status ${aluno.ativo ? 'ativo' : ''}`}>{aluno.ativo ? 'Ativa' : 'Desativada'}</span></td><td><button className="professor-icone" title="Redefinir senha" onClick={() => redefinir(aluno)}><KeyRound size={17} /></button></td></tr>)}</tbody></table></div>
        </section>
      </>}

      {modal && <div className="professor-modal-fundo"><section className="professor-modal"><button className="professor-fechar" onClick={() => setModal(false)}>×</button>{credenciais.length === 0 ? <form onSubmit={criar}><span className="professor-etiqueta">NOVA TURMA</span><h2>Preparar uma turma</h2><p>O PingLevel criará contas provisórias com senha temporária.</p><label>Nome da turma<input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Redes 2026 · Noite" required minLength={3} /></label><label>Quantidade de alunos<input type="number" min="1" max="40" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} required /></label><button className="botao-principal" disabled={criando}>{criando ? 'Criando...' : 'Criar turma e acessos'}</button></form> : <div><span className="professor-etiqueta">ACESSOS CRIADOS</span><h2>Credenciais provisórias</h2><p>Esta senha aparece agora para facilitar a distribuição aos alunos.</p><div className="professor-credenciais">{credenciais.map((item) => <div key={item.usuario_id}><span>{item.nome}</span><strong>{item.login}</strong><code>{item.senha_temporaria}</code></div>)}</div><button className="botao-principal" onClick={() => setModal(false)}>Concluir</button></div>}</section></div>}
    </main>
  )
}

export default PainelProfessor
