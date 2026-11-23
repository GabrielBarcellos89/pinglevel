import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    let ativo = true

    async function consultarSessao() {
      try {
        const resposta = await fetch('/api/auth/me', {
          credentials: 'same-origin',
        })
        const dados = await resposta.json()
        if (ativo) setUsuario(resposta.ok ? dados.usuario : null)
      } catch {
        if (ativo) setUsuario(null)
      } finally {
        if (ativo) setCarregando(false)
      }
    }

    consultarSessao()
    return () => { ativo = false }
  }, [])

  async function entrar(login, senha) {
    const resposta = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, senha }),
    })
    const dados = await resposta.json()
    if (!resposta.ok) {
      throw new Error(dados.mensagem || 'Não foi possível entrar.')
    }
    setUsuario(dados.usuario)
    return dados.usuario
  }

  async function sair() {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
      })
    } finally {
      setUsuario(null)
    }
  }

  const valor = useMemo(
    () => ({ usuario, carregando, entrar, sair }),
    [usuario, carregando],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth deve ser usado dentro de AuthProvider.')
  return contexto
}
