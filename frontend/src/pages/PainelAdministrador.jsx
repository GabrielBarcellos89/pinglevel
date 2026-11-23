import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarClock, Check, Copy, Gauge, KeyRound, Mail, Plus, ShieldCheck, UserPlus, UsersRound, GraduationCap, School } from 'lucide-react'
import './PainelAdministrador.css'

const validade = (segundos) => new Date(segundos * 1000).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
// Data e hora do campo datetime-local (hora do navegador) <-> segundos.
const paraCampo = (segundos) => {
  const d = new Date(segundos * 1000)
  const dois = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}T${dois(d.getHours())}:${dois(d.getMinutes())}`
}
const doCampo = (texto) => { const ms = new Date(texto).getTime(); return Number.isFinite(ms) ? Math.round(ms / 1000) : null }
const amanha = () => { const d = new Date(); d.setDate(d.getDate() + 1); d.setHours(23, 59, 0, 0); return Math.round(d.getTime() / 1000) }
const FORMULARIO_VAZIO = { nome: '', login: '', papel: 'aluno', turma_id: '', limitar: false, validade: '' }

function PainelAdministrador() {
  const [dados, setDados] = useState({ usuarios: [], turmas: [], auditoria: [], pedidos: [] })
  const [copiado, setCopiado] = useState(null)
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [modal, setModal] = useState(false)
  const [credencial, setCredencial] = useState(null)
  const [formulario, setFormulario] = useState(FORMULARIO_VAZIO)
  const [editando, setEditando] = useState(null) // { usuario, limitar, validade, turma_inteira }

  async function requisitar(url, opcoes) {
    const resposta = await fetch(url, opcoes)
    const corpo = await resposta.json()
    if (!resposta.ok) throw new Error(corpo.mensagem || 'Não foi possível concluir a operação.')
    return corpo
  }

  async function carregar() {
    try {
      const corpo = await requisitar('/api/admin/painel')
      setDados(corpo)
      setErro('')
    } catch (falha) {
      setErro(falha.message)
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => { carregar() }, [])

  const resumo = useMemo(() => ({
    alunos: dados.usuarios.filter((u) => u.papel === 'aluno').length,
    professores: dados.usuarios.filter((u) => u.papel === 'professor').length,
    ativos: dados.usuarios.filter((u) => u.ativo).length,
    turmas: dados.turmas.length,
  }), [dados])

  // Pedidos de acesso do formulário do login (23/11/2026): o administrador cria a conta e responde por e-mail.
  async function marcarPedido(pedido, atendido) {
    try {
      await requisitar('/api/admin/pedidos/atendido', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pedido_id: pedido.id, atendido }) })
      await carregar()
    } catch (falha) { setErro(falha.message) }
  }
  async function copiarEmail(pedido) {
    try { await navigator.clipboard.writeText(pedido.email); setCopiado(pedido.id) } catch { setCopiado(null) }
  }
  function criarConta(pedido) {
    setFormulario({ ...FORMULARIO_VAZIO, nome: pedido.nome })
    setCredencial(null)
    setModal(true)
  }
  const pendentes = (dados.pedidos || []).filter((p) => !p.atendido_em).length

  async function criar(evento) {
    evento.preventDefault()
    try {
      const corpo = await requisitar('/api/admin/usuarios/criar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome: formulario.nome, login: formulario.login, papel: formulario.papel, turma_id: formulario.turma_id,
          expira_em: formulario.limitar ? doCampo(formulario.validade) : null }),
      })
      setCredencial(corpo.usuario)
      setFormulario(FORMULARIO_VAZIO)
      await carregar()
    } catch (falha) { setErro(falha.message) }
  }

  async function atualizar(usuario, ativo) {
    try {
      await requisitar('/api/admin/usuarios/atualizar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario_id: usuario.id, nome: usuario.nome, ativo }),
      })
      await carregar()
    } catch (falha) { setErro(falha.message) }
  }

  function abrirValidade(usuario) {
    setEditando({ usuario, limitar: Boolean(usuario.expira_em), validade: paraCampo(usuario.expira_em || amanha()), turma_inteira: false })
  }

  function somarDias(dias) {
    const base = doCampo(editando.validade) || Math.round(Date.now() / 1000)
    setEditando({ ...editando, limitar: true, validade: paraCampo(base + dias * 86400) })
  }

  async function salvarValidade(evento) {
    evento.preventDefault()
    try {
      if (editando.limitar && !doCampo(editando.validade)) throw new Error('Informe a data e a hora da validade.')
      await requisitar('/api/admin/usuarios/validade', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario_id: editando.usuario.id, expira_em: editando.limitar ? doCampo(editando.validade) : null,
          turma_inteira: editando.turma_inteira }),
      })
      setEditando(null)
      await carregar()
    } catch (falha) { setErro(falha.message) }
  }

  async function redefinir(usuario) {
    try {
      const corpo = await requisitar('/api/admin/usuarios/redefinir-senha', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario_id: usuario.id }),
      })
      window.alert(`Nova senha temporária de ${usuario.nome}: ${corpo.senha_temporaria}`)
    } catch (falha) { setErro(falha.message) }
  }

  async function vincular(usuario, turmaId) {
    try {
      await requisitar('/api/admin/alunos/vincular', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario_id: usuario.id, turma_id: turmaId || null }),
      })
      await carregar()
    } catch (falha) { setErro(falha.message) }
  }

  return <main className="principal admin-pagina">
    <header className="admin-cabecalho">
      <div><span>CONTROLE DA PLATAFORMA</span><h1>Painel administrativo</h1><p>Gerencie contas, acessos e vínculos com as turmas.</p></div>
      <div className="admin-acoes">
        <Link className="admin-carga" to="/administrador/painel-carga"><Gauge size={18}/> Painel de carga</Link>
        <button className="botao-principal" onClick={() => { setModal(true); setCredencial(null) }}><Plus size={18}/> Novo usuário</button>
      </div>
    </header>
    {erro && <div className="admin-erro">{erro}</div>}
    <section className="admin-resumos">
      <article><UsersRound/><div><strong>{resumo.alunos}</strong><span>alunos</span></div></article>
      <article><GraduationCap/><div><strong>{resumo.professores}</strong><span>professores</span></div></article>
      <article><School/><div><strong>{resumo.turmas}</strong><span>turmas</span></div></article>
      <article><ShieldCheck/><div><strong>{resumo.ativos}</strong><span>contas ativas</span></div></article>
    </section>
    <section className="admin-card admin-pedidos">
      <div className="admin-card-topo"><div><span>PEDIDOS DE ACESSO</span><h2>Quem pediu para usar a plataforma</h2></div>
        <small>{carregando ? 'Carregando...' : `${pendentes} aguardando · ${(dados.pedidos || []).length} no total`}</small></div>
      {!carregando && !dados.aviso_email && <p className="admin-pedidos-aviso"><Mail size={16} aria-hidden="true" />O aviso por e-mail ainda não está configurado no servidor: por enquanto, os pedidos aparecem só aqui.</p>}
      {(dados.pedidos || []).length === 0 ? <p className="admin-pedidos-vazio">Nenhum pedido ainda. O formulário fica na tela de login, em “Pedir acesso”.</p>
        : <div className="admin-tabela-wrap"><table><thead><tr><th>Pessoa</th><th>Instituição</th><th>Mensagem</th><th>Recebido</th><th>Situação</th><th>Ações</th></tr></thead>
          <tbody>{dados.pedidos.map((pedido) => <tr key={pedido.id} className={pedido.atendido_em ? 'atendido' : ''}>
            <td><strong>{pedido.nome}</strong><span>{pedido.email}</span></td>
            <td>{pedido.instituicao}</td>
            <td className="admin-pedido-mensagem">{pedido.mensagem || '—'}</td>
            <td>{validade(pedido.criado_em)}</td>
            <td><button className={`admin-status ${pedido.atendido_em ? 'ativo' : ''}`} onClick={() => marcarPedido(pedido, !pedido.atendido_em)}
              title={pedido.atendido_em ? `Atendido por ${pedido.atendido_por_nome || 'administrador'}` : 'Marcar como atendido'}>{pedido.atendido_em ? 'Atendido' : 'Aguardando'}</button></td>
            <td><div className="admin-acoes-linha">
              <button className="admin-icone" title="Criar conta com este nome" aria-label={`Criar conta para ${pedido.nome}`} onClick={() => criarConta(pedido)}><UserPlus size={17}/></button>
              <button className="admin-icone" title="Copiar o e-mail" aria-label={`Copiar o e-mail de ${pedido.nome}`} onClick={() => copiarEmail(pedido)}>
                {copiado === pedido.id ? <Check size={17}/> : <Copy size={17}/>}</button>
            </div></td>
          </tr>)}</tbody></table></div>}
    </section>
    <section className="admin-card">
      <div className="admin-card-topo"><div><span>USUÁRIOS</span><h2>Contas da plataforma</h2></div><small>{carregando ? 'Carregando...' : `${dados.usuarios.length} contas`}</small></div>
      <div className="admin-tabela-wrap"><table><thead><tr><th>Usuário</th><th>Perfil</th><th>Turma</th><th>Conta</th><th>Ações</th></tr></thead>
        <tbody>{dados.usuarios.map((usuario) => <tr key={usuario.id}>
          <td><strong>{usuario.nome}</strong><span>@{usuario.login}</span></td>
          <td><b className={`admin-papel ${usuario.papel}`}>{usuario.papel}</b></td>
          <td>{usuario.papel === 'aluno' ? <select value={usuario.turma_id || ''} onChange={(e) => vincular(usuario, e.target.value)}><option value="">Sem turma</option>{dados.turmas.map((turma) => <option key={turma.id} value={turma.id}>{turma.nome}</option>)}</select> : <span>—</span>}</td>
          <td><button className={`admin-status ${usuario.ativo ? 'ativo' : ''}`} disabled={usuario.papel === 'administrador'} onClick={() => atualizar(usuario, !usuario.ativo)}>{usuario.ativo ? 'Ativa' : 'Desativada'}</button>{usuario.expira_em && <small className="admin-validade">{usuario.expira_em * 1000 > Date.now() ? 'até' : 'expirou em'} {validade(usuario.expira_em)}</small>}</td>
          <td><div className="admin-acoes-linha">
            <button className="admin-icone" title="Redefinir senha" onClick={() => redefinir(usuario)}><KeyRound size={17}/></button>
            {usuario.papel !== 'administrador' && <button className="admin-icone" title="Validade da conta" aria-label={`Validade da conta de ${usuario.nome}`}
              onClick={() => abrirValidade(usuario)}><CalendarClock size={17}/></button>}
          </div></td>
        </tr>)}</tbody></table></div>
    </section>
    {modal && <div className="admin-modal-fundo"><section className="admin-modal">
      <button className="admin-fechar" onClick={() => setModal(false)}>×</button>
      {credencial ? <div>
        <span>ACESSO CRIADO</span><h2>Credencial temporária</h2>
        <p>{credencial.papel === 'aluno' ? 'O aluno já foi matriculado na turma selecionada.' : 'O professor já pode entrar.'}
          {credencial.expira_em ? ` A conta vale até ${validade(credencial.expira_em)}.` : ' A conta não tem data de validade.'}</p>
        <div className="admin-credencial"><b>{credencial.nome}</b><code>{credencial.login}</code><code>{credencial.senha_temporaria}</code></div>
        <button className="botao-principal" onClick={() => setModal(false)}>Concluir</button>
      </div> : <form onSubmit={criar}>
        <span>NOVO USUÁRIO</span><h2>Criar acesso</h2>
        <label>Nome<input required minLength="2" value={formulario.nome} onChange={(e) => setFormulario({...formulario, nome: e.target.value})}/></label>
        <label>Login<input required minLength="3" value={formulario.login} onChange={(e) => setFormulario({...formulario, login: e.target.value.toLowerCase()})}/></label>
        <label>Perfil<select value={formulario.papel} onChange={(e) => setFormulario({...formulario, papel: e.target.value, turma_id: e.target.value === 'aluno' ? formulario.turma_id : ''})}><option value="aluno">Aluno</option><option value="professor">Professor</option></select></label>
        {formulario.papel === 'aluno' && <label>Turma<select required value={formulario.turma_id} onChange={(e) => setFormulario({...formulario, turma_id: e.target.value})}><option value="">Selecione uma turma</option>{dados.turmas.filter((turma) => turma.ativo).map((turma) => <option key={turma.id} value={turma.id}>{turma.nome}</option>)}</select></label>}
        <fieldset className="admin-validade-campo"><legend>Validade da conta</legend>
          <label className="admin-opcao"><input type="radio" name="limitar" checked={!formulario.limitar} onChange={() => setFormulario({...formulario, limitar: false})}/> Sem limite</label>
          <label className="admin-opcao"><input type="radio" name="limitar" checked={formulario.limitar}
            onChange={() => setFormulario({...formulario, limitar: true, validade: formulario.validade || paraCampo(amanha())})}/> Até uma data</label>
          {formulario.limitar && <input type="datetime-local" required aria-label="Data e hora em que a conta expira" value={formulario.validade}
            onChange={(e) => setFormulario({...formulario, validade: e.target.value})}/>}
        </fieldset>
        {formulario.papel === 'aluno' && !formulario.turma_id && (
          <p className="admin-aviso-formulario">
            Selecione uma turma para liberar a criação do aluno.
          </p>
        )}
        <button
          className="botao-principal"
          disabled={formulario.papel === 'aluno' && !formulario.turma_id}
        >
          Criar usuário
        </button>
      </form>}
    </section></div>}
    {editando && <div className="admin-modal-fundo"><section className="admin-modal">
      <button className="admin-fechar" onClick={() => setEditando(null)}>×</button>
      <form onSubmit={salvarValidade}>
        <span>VALIDADE DA CONTA</span><h2>{editando.usuario.nome}</h2>
        <p>@{editando.usuario.login} · {editando.usuario.expira_em ? `hoje vale até ${validade(editando.usuario.expira_em)}` : 'hoje sem limite'}.
          Depois da validade, o login é recusado e quem estiver dentro sai.</p>
        <label className="admin-opcao"><input type="radio" name="validade" checked={!editando.limitar} onChange={() => setEditando({...editando, limitar: false})}/> Sem limite</label>
        <label className="admin-opcao"><input type="radio" name="validade" checked={editando.limitar} onChange={() => setEditando({...editando, limitar: true})}/> Até uma data</label>
        {editando.limitar && <>
          <input type="datetime-local" required aria-label="Data e hora em que a conta expira" value={editando.validade}
            onChange={(e) => setEditando({...editando, validade: e.target.value})}/>
          <div className="admin-atalhos">
            <button type="button" onClick={() => somarDias(-1)}>− 1 dia</button>
            <button type="button" onClick={() => somarDias(1)}>+ 1 dia</button>
            <button type="button" onClick={() => somarDias(7)}>+ 7 dias</button>
            <button type="button" onClick={() => setEditando({...editando, validade: paraCampo(Math.round(Date.now() / 1000))})}>Expirar agora</button>
          </div>
        </>}
        {editando.usuario.papel === 'aluno' && editando.usuario.turma_id && <label className="admin-opcao">
          <input type="checkbox" checked={editando.turma_inteira} onChange={(e) => setEditando({...editando, turma_inteira: e.target.checked})}/>
          Aplicar a todos os alunos da {editando.usuario.turma_nome || 'turma'}</label>}
        <button className="botao-principal">Salvar validade</button>
      </form>
    </section></div>}
  </main>
}

export default PainelAdministrador
