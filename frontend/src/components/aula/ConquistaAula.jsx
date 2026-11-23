import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, House, Sparkles } from 'lucide-react'
import { COMEMORACAO } from '../../assets/mascote/poses'
import { PARADAS, resumoInicio } from '../../data/trilha'
import './ConquistaAula.css'

// Momento de conquista ao concluir qualquer aula: o Link com a estrela, o XP ganho e o próximo passo da trilha.
// `aulaId` dá o título (o mesmo da trilha). `xp` vem da resposta do servidor (xp_concedido); sem ele, mostra só a conclusão.
export default function ConquistaAula({ aulaId, xp }) {
  const titulo = PARADAS.find((p) => p.atividade === aulaId)?.titulo ?? 'Aula concluída'
  const navigate = useNavigate()
  const [proximo, setProximo] = useState(undefined)

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' })
      .then((resposta) => resposta.json())
      .then((dados) => { if (ativo) setProximo(dados.sucesso ? resumoInicio(dados.progresso).proximo : null) })
      .catch(() => { if (ativo) setProximo(null) })
    return () => { ativo = false }
  }, [])

  return <div className="conquista-overlay" role="dialog" aria-modal="true" aria-labelledby="conquista-titulo">
    <section className="conquista-card">
      <div className="conquista-texto">
        <span className="conquista-etiqueta">AULA CONCLUÍDA</span>
        <h2 id="conquista-titulo">{titulo}</h2>
        {xp > 0 && <p className="conquista-xp"><Sparkles size={24} /> +{xp} XP</p>}
        {xp === 0 && <p className="conquista-revisao">Aula revisada · o XP desta aula já estava na sua conta.</p>}
        <p>Muito bem! Seu progresso está salvo.</p>
        <div className="conquista-acoes">
          {proximo && <button className="botao-interacao" type="button" onClick={() => navigate(proximo.caminho)}>
            Seguir: {proximo.titulo} <ArrowRight size={18} />
          </button>}
          <button className="botao-secundario" type="button" onClick={() => navigate('/')}>
            <House size={17} /> Voltar ao início
          </button>
        </div>
      </div>
      <div className="conquista-mascote"><img src={COMEMORACAO.estrela} alt="Link comemorando com uma estrela dourada" /></div>
    </section>
  </div>
}
