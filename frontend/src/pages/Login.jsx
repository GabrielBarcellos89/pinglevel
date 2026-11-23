import { ArrowLeft, ArrowRight, Building2, CheckCircle2, Eye, EyeOff, LockKeyhole, Mail, Send, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

// Link confiante, de polegar para cima (22/11/2026): a pose anterior parecia assustada.
import linkPrincipal from '../assets/mascote/link-login/link-confiante.webp'
import LogoPingLevel from '../components/layout/LogoPingLevel'
import { useAuth } from '../contexts/AuthContext'
import './Login.css'
import CriadoPor from '../components/layout/CriadoPor'

// Sem cadastro aberto por enquanto: quem quiser acesso preenche o pedido aqui mesmo (23/11/2026). O servidor guarda o
// pedido para o administrador e avisa por e-mail; a conta continua sendo criada por ele.
const EMAIL_ACESSO = 'acesso@pinglevel.com.br'
const PEDIDO_VAZIO = { nome: '', email: '', instituicao: '', mensagem: '', site: '' }

function PedidoAcesso({ aoVoltar }) {
  const [pedido, setPedido] = useState(PEDIDO_VAZIO)
  const [estado, setEstado] = useState({ enviando: false, erro: '', enviado: false })
  const campo = (nome) => ({ value: pedido[nome], onChange: (e) => setPedido({ ...pedido, [nome]: e.target.value }) })

  async function enviar(evento) {
    evento.preventDefault()
    setEstado({ enviando: true, erro: '', enviado: false })
    try {
      const resposta = await fetch('/api/acesso/pedido', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pedido) })
      const dados = await resposta.json().catch(() => ({}))
      if (!resposta.ok || !dados.sucesso) throw new Error(dados.mensagem || 'Não foi possível enviar o pedido. Tente novamente.')
      setEstado({ enviando: false, erro: '', enviado: true })
    } catch (falha) {
      setEstado({ enviando: false, erro: falha.message, enviado: false })
    }
  }

  if (estado.enviado) {
    return <div className="login-pedido-enviado" role="status">
      <CheckCircle2 size={38} aria-hidden="true" />
      <h2>Pedido enviado</h2>
      <p>Vamos responder no e-mail <b>{pedido.email.trim()}</b>, com o seu usuário e a senha de acesso.</p>
      <button type="button" className="login-voltar" onClick={aoVoltar}><ArrowLeft size={17} aria-hidden="true" />Voltar ao login</button>
    </div>
  }

  return <form onSubmit={enviar} className="login-formulario login-formulario-pedido">
    <label htmlFor="pedido-nome">Nome completo</label>
    <div className="login-campo"><UserRound size={19} /><input id="pedido-nome" {...campo('nome')} autoComplete="name" maxLength={80} required minLength={3} autoFocus /></div>
    <label htmlFor="pedido-email">E-mail</label>
    <div className="login-campo"><Mail size={19} /><input id="pedido-email" type="email" {...campo('email')} autoComplete="email" maxLength={120} required /></div>
    <label htmlFor="pedido-instituicao">Instituição ou curso</label>
    <div className="login-campo"><Building2 size={19} /><input id="pedido-instituicao" {...campo('instituicao')} autoComplete="organization" maxLength={120} required minLength={2} /></div>
    <label htmlFor="pedido-mensagem">Como pretende usar a plataforma? <small>(opcional)</small></label>
    <textarea id="pedido-mensagem" className="login-area" {...campo('mensagem')} maxLength={1000} rows={2} />
    {/* Campo-isca: invisível para pessoas; robôs que o preenchem não geram pedido. */}
    <input className="login-isca" tabIndex={-1} autoComplete="off" aria-hidden="true" {...campo('site')} />
    {estado.erro && <div className="login-erro" role="alert">{estado.erro}</div>}
    <button className="login-entrar" disabled={estado.enviando}>
      {estado.enviando ? 'Enviando...' : 'Enviar pedido'}{!estado.enviando && <Send size={18} aria-hidden="true" />}
    </button>
    <button type="button" className="login-voltar" onClick={aoVoltar}><ArrowLeft size={17} aria-hidden="true" />Voltar ao login</button>
  </form>
}

function Login() {
  const { usuario, carregando, entrar } = useAuth()
  const [login, setLogin] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [pedindo, setPedindo] = useState(false)
  const navegar = useNavigate()
  const localizacao = useLocation()

  if (!carregando && usuario) {
    return (
      <Navigate
        to={
          usuario.troca_senha_obrigatoria
            ? '/alterar-senha'
            : '/'
        }
        replace
      />
    )
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      const usuarioAutenticado = await entrar(login, senha)
      const origem = localizacao.state?.origem?.pathname
      navegar(
        usuarioAutenticado.troca_senha_obrigatoria
          ? '/alterar-senha'
          : usuarioAutenticado.papel === 'administrador'
            ? '/administrador'
            : usuarioAutenticado.papel === 'professor'
              ? '/professor'
              : origem && origem !== '/login'
                ? origem
                : '/',
        { replace: true },
      )
    } catch (falha) {
      setErro(falha.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="login-pagina">
      <section className="login-card">
        <div className="login-formulario-area">
          <div className="login-marca">
            <LogoPingLevel className="logo-pinglevel--login" />
          </div>

          {pedindo ? <>
            <div className="login-cabecalho login-cabecalho-pedido">
              <span>PEDIDO DE ACESSO</span>
              <h1>Quer usar o PingLevel?</h1>
              <p>Conte quem você é. A resposta chega no seu e-mail, com o usuário e a senha.</p>
            </div>
            <PedidoAcesso aoVoltar={() => setPedindo(false)} />
          </> : <>
          <div className="login-cabecalho">
            <span>ACESSO À PLATAFORMA</span>
            <h1>Bem-vindo ao PingLevel.</h1>
            <p>Acesse sua conta para aprender, praticar e evoluir em Redes de Computadores.</p>
          </div>

          <form onSubmit={enviar} className="login-formulario">
            <label htmlFor="login">Usuário</label>
            <div className="login-campo">
              <UserRound size={19} />
              <input id="login" value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" placeholder="Digite seu usuário" autoFocus required />
            </div>

            <label htmlFor="senha">Senha</label>
            <div className="login-campo">
              <LockKeyhole size={19} />
              <input id="senha" type={mostrarSenha ? 'text' : 'password'} value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" placeholder="Digite sua senha" required />
              <button type="button" className="login-ver-senha" onClick={() => setMostrarSenha(!mostrarSenha)} aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}>
                {mostrarSenha ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </div>

            {erro && <div className="login-erro" role="alert">{erro}</div>}

            <button className="login-entrar" disabled={enviando}>
              {enviando ? 'Entrando...' : 'Entrar'}
              {!enviando && <ArrowRight size={19} />}
            </button>
          </form>

          <div className="login-pedido">
            <p>Ainda não tem acesso?</p>
            <button type="button" onClick={() => { setErro(''); setPedindo(true) }}><Mail size={17} aria-hidden="true" />Pedir acesso</button>
            <small>Ou escreva para <b>{EMAIL_ACESSO}</b>.</small>
          </div>
          </>}

          <footer className={`login-rodape ${pedindo ? 'login-rodape-pedido' : ''}`}>
            <p>Ambiente de aprendizagem em Redes de Computadores</p>
            <CriadoPor />
          </footer>
        </div>

        <aside className="login-link-area">
          <div className="login-brilho" />
          <div className="login-link-fala">
            <span>LINK DIZ:</span>
            <p>Seu próximo desafio começa aqui. Vamos conectar conhecimento e prática?</p>
          </div>
          <img src={linkPrincipal} alt="Link, guia de aprendizagem do PingLevel" />
        </aside>
      </section>
    </main>
  )
}

export default Login
