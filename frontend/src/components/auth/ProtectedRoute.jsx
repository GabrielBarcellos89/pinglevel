import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext'

function ProtectedRoute({ papel }) {
  const { usuario, carregando } = useAuth()
  const localizacao = useLocation()

  if (carregando) {
    return (
      <main className="auth-carregando" aria-live="polite">
        <div className="auth-pulso" />
        <span>Preparando sua jornada...</span>
      </main>
    )
  }

  if (!usuario) {
    return <Navigate to="/login" state={{ origem: localizacao }} replace />
  }

  if (
    usuario.troca_senha_obrigatoria
    && localizacao.pathname !== '/alterar-senha'
  ) {
    return <Navigate to="/alterar-senha" replace />
  }

  if (papel && usuario.papel !== papel) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
