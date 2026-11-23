import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Sem resposta do servidor, o navegador diz "Failed to fetch" (em inglês). As telas mostram a mensagem do erro,
// então a tradução fica aqui, num só lugar. Cancelamentos (AbortError) passam como estão.
const fetchOriginal = window.fetch.bind(window)
window.fetch = (...args) => fetchOriginal(...args).catch((erro) => {
  if (erro instanceof TypeError) throw new TypeError('Não foi possível falar com o servidor. Confira sua conexão e tente de novo.')
  throw erro
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
