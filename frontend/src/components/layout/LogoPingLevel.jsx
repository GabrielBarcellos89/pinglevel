import logoHorizontal from '../../assets/brand/pinglevel-logo-horizontal-transparent.svg'
import logoSimbolo from '../../assets/brand/pinglevel-simbolo-color.svg'

export default function LogoPingLevel({ recolhido = false, className = '' }) {
  return (
    <img
      className={`logo-pinglevel ${recolhido ? 'logo-pinglevel--simbolo' : ''} ${className}`.trim()}
      src={recolhido ? logoSimbolo : logoHorizontal}
      alt="PingLevel — Aprenda. Pratique. Evolua."
    />
  )
}
