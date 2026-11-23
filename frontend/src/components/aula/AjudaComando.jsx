import { useState } from 'react'
import { BookOpen, LifeBuoy } from 'lucide-react'
import linkExplicando from '../../assets/mascote/link-expansao-v1/link-explicando.webp'
import './AjudaComando.css'

// Ajuda do Link para montar um comando, em três níveis que se somam (a ajuda diminui, mas nunca some):
// 1) o que é cada parte; 2) o exemplo do livro do professor; 3) uma pista quase completa, com uma lacuna.
export default function AjudaComando({ ajuda }) {
  const [nivel, setNivel] = useState(0)
  if (!ajuda) return null
  return <div className="ajuda-comando">
    {nivel > 0 && <div className="ajuda-balao" aria-live="polite">
      <img src={linkExplicando} alt="" />
      <div>
        <strong>Link</strong>
        <ul className="ajuda-partes">{ajuda.partes.map(([trecho, explicacao]) => <li key={trecho}><code>{trecho}</code> {explicacao}</li>)}</ul>
        {nivel > 1 && <p className="ajuda-livro"><BookOpen size={15} aria-hidden="true" />{ajuda.pagina
          ? <span>No livro do professor (<i>{ajuda.livro || 'Linux: Utilitários de Redes'}</i>,
            p. {ajuda.pagina}), {ajuda.exemplo.rotulo}: <code>{ajuda.exemplo.comando}</code>. {ajuda.observacao || 'Troque os valores do exemplo pelos do objetivo.'}</span>
          : <span>Um exemplo com outros valores: <code>{ajuda.exemplo.comando}</code>. {ajuda.observacao || 'Troque os valores do exemplo pelos do objetivo.'}</span>}</p>}
        {nivel > 2 && <p className="ajuda-pista">Quase lá: <code>{ajuda.pista}</code> · complete a lacuna.</p>}
      </div>
    </div>}
    {nivel < 3 && <button type="button" className="ajuda-botao" onClick={() => setNivel(nivel + 1)}>
      <LifeBuoy size={15} aria-hidden="true" />{nivel === 0 ? 'Pedir ajuda ao Link' : nivel === 1 ? (ajuda.pagina ? 'Ver o exemplo do livro' : 'Ver um exemplo') : 'Quero uma pista'}
    </button>}
  </div>
}
