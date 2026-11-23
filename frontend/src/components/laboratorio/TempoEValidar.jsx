import { CheckCircle2, Clock3 } from 'lucide-react'
import './TempoEValidar.css'

// Padrão dos laboratórios (como no Lab 1): o tempo e o Validar missão sempre juntos no cabeçalho.
// O tempo fica amarelo nos 2 últimos minutos e vermelho no último; o botão fica visível desde o início e chama
// a atenção quando a missão pode ser validada. Quem confirma a conclusão continua sendo o servidor.
export default function TempoEValidar({ tempo, restantes, mostrarTempo = true, pronta, feitas, total, ocupado, aoValidar, semXp }) {
  const alerta = restantes !== null && restantes !== undefined && restantes <= 60 ? 'critico'
    : restantes !== null && restantes !== undefined && restantes <= 120 ? 'alerta' : ''
  return <>
    {mostrarTempo && <div className={`gw-tempo tv-tempo ${alerta}`} data-testid="tempo"><Clock3 size={22} aria-hidden="true" />
      <span><strong>{tempo}</strong><small>tempo restante</small></span></div>}
    {aoValidar && <button type="button" className={`tv-validar ${pronta ? 'pronta' : ''}`} disabled={!pronta || ocupado} onClick={aoValidar}>
      <CheckCircle2 size={20} aria-hidden="true" />
      <span>Validar missão<small>{pronta ? (semXp ? 'Clique para o servidor conferir' : 'Clique para registrar o XP') : `Conclua as etapas (${feitas} de ${total})`}</small></span>
    </button>}
  </>
}
