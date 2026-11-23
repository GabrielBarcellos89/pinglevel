import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import LogoPingLevel from '../components/layout/LogoPingLevel'
import { useAuth } from '../contexts/AuthContext'
import './AlterarSenha.css'

function AlterarSenha() {
  const { usuario, sair } = useAuth()
  const navegar = useNavigate()
  const obrigatoria = Boolean(
    usuario?.troca_senha_obrigatoria,
  )

  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [mostrarSenhas, setMostrarSenhas] = useState(false)
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setErro('')
    setSucesso('')
    setEnviando(true)

    try {
      const resposta = await fetch(
        '/api/auth/alterar-senha',
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            senha_atual: senhaAtual,
            nova_senha: novaSenha,
            confirmacao,
          }),
        },
      )

      const dados = await resposta.json()

      if (!resposta.ok) {
        throw new Error(
          dados.mensagem
          || 'Não foi possível alterar a senha.',
        )
      }

      setSucesso(dados.mensagem)

      window.setTimeout(async () => {
        await sair()
        navegar('/login', { replace: true })
      }, 1200)
    } catch (falha) {
      setErro(falha.message)
      setEnviando(false)
    }
  }

  return (
    <main className="senha-pagina">
      <section className="senha-card">
        <LogoPingLevel className="senha-logo" />

        <div className="senha-cabecalho">
          <span>SEGURANÇA DA CONTA</span>
          <h1>
            {obrigatoria
              ? 'Defina sua nova senha.'
              : 'Altere sua senha.'}
          </h1>
          <p>
            {obrigatoria
              ? 'Sua senha atual é temporária. Crie uma senha pessoal para continuar.'
              : 'Confirme sua senha atual e escolha uma nova senha pessoal.'}
          </p>
        </div>

        <form className="senha-formulario" onSubmit={enviar}>
          <label htmlFor="senha-atual">Senha atual</label>
          <div className="senha-campo">
            <LockKeyhole size={19} />
            <input
              id="senha-atual"
              type={mostrarSenhas ? 'text' : 'password'}
              value={senhaAtual}
              onChange={(evento) => setSenhaAtual(
                evento.target.value
              )}
              autoComplete="current-password"
              required
              autoFocus
            />
          </div>

          <label htmlFor="nova-senha">Nova senha</label>
          <div className="senha-campo">
            <LockKeyhole size={19} />
            <input
              id="nova-senha"
              type={mostrarSenhas ? 'text' : 'password'}
              value={novaSenha}
              onChange={(evento) => setNovaSenha(
                evento.target.value
              )}
              autoComplete="new-password"
              required
            />
          </div>

          <label htmlFor="confirmacao">
            Confirme a nova senha
          </label>
          <div className="senha-campo">
            <LockKeyhole size={19} />
            <input
              id="confirmacao"
              type={mostrarSenhas ? 'text' : 'password'}
              value={confirmacao}
              onChange={(evento) => setConfirmacao(
                evento.target.value
              )}
              autoComplete="new-password"
              required
            />
            <button
              type="button"
              className="senha-mostrar"
              onClick={() => setMostrarSenhas(
                !mostrarSenhas
              )}
              aria-label={
                mostrarSenhas
                  ? 'Ocultar senhas'
                  : 'Mostrar senhas'
              }
            >
              {mostrarSenhas
                ? <EyeOff size={19} />
                : <Eye size={19} />}
            </button>
          </div>

          <ul className="senha-requisitos">
            <li>Ao menos 10 caracteres</li>
            <li>Letras maiúsculas e minúsculas</li>
            <li>Número e caractere especial</li>
          </ul>

          {erro && (
            <div className="senha-mensagem erro" role="alert">
              {erro}
            </div>
          )}

          {sucesso && (
            <div className="senha-mensagem sucesso">
              <CheckCircle2 size={18} />
              {sucesso}
            </div>
          )}

          <button
            className="senha-confirmar"
            disabled={enviando || Boolean(sucesso)}
          >
            {enviando ? 'Alterando...' : 'Definir nova senha'}
            {!enviando && <ArrowRight size={19} />}
          </button>

          {!obrigatoria && (
            <button
              type="button"
              className="senha-cancelar"
              onClick={() => navegar(-1)}
              disabled={enviando}
            >
              Cancelar
            </button>
          )}
        </form>
      </section>
    </main>
  )
}

export default AlterarSenha
