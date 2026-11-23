import { useState } from 'react'
import { Activity, ChevronDown } from 'lucide-react'
import './BastidoresTshark.css'

// Camada de cada protocolo, para o aluno ligar o pacote ao modelo visto nas aulas.
const CAMADA = { ARP: 'camada 2', ICMP: 'camada 3', DNS: 'camada 7', DHCP: 'camada 7' }

export function explicarPacote(e, nome) {
  const c = e.campos || {}
  const de = nome(e.origem)
  const para = nome(e.destino)
  switch (e.tipo) {
    case 'ARP Request': return `${de} pergunta a toda a rede: quem tem ${para}?`
    case 'ARP Reply': return `${de} responde: sou eu, meu MAC é ${c['eth.src'] || '—'}.`
    case 'ICMP Echo Request': return `${de} → ${para}: pedido de eco (o ping).`
    case 'ICMP Echo Reply': return `${de} → ${para}: resposta do eco. O ping chegou e voltou.`
    case 'ICMP Destino inalcançável': return `${de} avisa ${para}: não consegui entregar o pacote (destino inalcançável).`
    case 'DNS Pergunta': return `${de} pergunta ao DNS ${para}: qual é o IP de ${c['dns.qry.name'] || 'esse nome'}?`
    case 'DNS Resposta': return c['dns.a']
      ? `O DNS ${de} responde: ${c['dns.qry.name']} é ${c['dns.a'].split(',').join(', ')}.`
      : `O DNS ${de} responde: não encontrei ${c['dns.qry.name'] || 'esse nome'}.`
    case 'DHCP Discover': return 'O computador grita para a rede: tem algum servidor DHCP aí?'
    case 'DHCP Offer': return `O servidor DHCP ${de} oferece o endereço ${c['dhcp.ip.your'] || '—'}.`
    case 'DHCP Request': return 'O computador pede para ficar com o endereço oferecido.'
    case 'DHCP ACK': return `O servidor DHCP ${de} confirma: o endereço ${c['dhcp.ip.your'] || '—'} é seu.`
    default: return e.resumo
  }
}

function linhaTshark(e) {
  const c = e.campos || {}
  const extra = e.protocolo === 'ARP' ? `${e.tipo === 'ARP Request' ? 'Who has' : 'is at'} ${e.tipo === 'ARP Request' ? e.destino : c['eth.src']}`
    : e.protocolo === 'DNS' ? `${e.tipo === 'DNS Resposta' ? 'response' : 'query'} A ${c['dns.qry.name'] || ''} ${c['dns.a'] || ''}`
      : e.protocolo === 'ICMP' ? `type=${c['icmp.type']}${c['icmp.seq'] ? ` seq=${c['icmp.seq']}` : ''}${c['ip.ttl'] ? ` ttl=${c['ip.ttl'].split(',')[0]}` : ''}`
        : e.tipo
  return `${String(e.sequencia).padStart(3)}  ${Number(e.tempo_relativo).toFixed(6)}  ${e.origem || c['eth.src']} → ${e.destino || c['eth.dst']}  ${e.protocolo}  ${extra}`
}

const VAZIA = 'Nenhum pacote saiu pela placa de rede. Quando falta endereço ou rota, o comando falha dentro do próprio computador, antes de chegar à rede.'

// Painel recolhido: o aluno abre quando quiser ver o que o comando fez na rede, capturado pelo tshark no servidor.
export default function BastidoresTshark({ capturas = [], nomeNo, nomeIp = (ip) => ip }) {
  const [aberto, setAberto] = useState(false)
  const [escolhida, setEscolhida] = useState(null)
  const [tecnico, setTecnico] = useState(false)
  const lista = [...capturas].reverse()
  const atual = lista.find((c) => c.id === escolhida) || lista[0]
  return (
    <section className={`bt-painel ${aberto ? 'aberto' : ''}`} aria-label="Bastidores da rede">
      <button type="button" className="bt-alternar" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>
        <Activity size={16} aria-hidden="true" /><strong>Bastidores da rede</strong>
        <span>{lista.length ? `o que o último comando fez na rede, visto pelo tshark` : 'rode um ping para ver os pacotes'}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {aberto && <div className="bt-corpo">
        {!atual ? <p className="bt-vazio">Os Bastidores mostram os pacotes de verdade que passaram pela placa de rede, capturados pelo
          tshark no servidor. Rode um ping (ou nslookup e dhclient, onde o lab tiver) e eles aparecem aqui.</p> : <>
          {lista.length > 1 && <div className="bt-escolha" role="group" aria-label="Capturas recentes">
            {lista.map((c, i) => <button type="button" key={c.id} aria-pressed={c === atual} onClick={() => setEscolhida(c.id)}>
              {i === 0 ? 'Último: ' : ''}{nomeNo(c.pc)} $ {c.digitado}</button>)}
          </div>}
          <p className="bt-cabecalho"><b>{nomeNo(atual.pc)} $ {atual.digitado}</b> · capturado na placa de rede do {nomeNo(atual.pc)}
            {atual.eventos?.length ? ` · ${atual.eventos.length} pacote${atual.eventos.length > 1 ? 's' : ''}` : ''}</p>
          {atual.estado === 'vazia' && <p className="bt-vazio">{VAZIA}</p>}
          {['falha', 'cancelada'].includes(atual.estado) && <p className="bt-vazio">Desta vez a captura não ficou disponível. O comando
            funcionou normalmente; rode de novo para ver os pacotes.</p>}
          {atual.eventos?.length > 0 && <>
            <ol className="bt-pacotes">
              {atual.eventos.map((e) => <li key={e.sequencia} className={`bt-${e.protocolo.toLowerCase()}`}>
                <span className="bt-protocolo">{e.protocolo}<small>{CAMADA[e.protocolo]}</small></span>
                <p>{explicarPacote(e, nomeIp)}</p>
              </li>)}
            </ol>
            <button type="button" className="bt-tecnico" aria-pressed={tecnico} onClick={() => setTecnico(!tecnico)}>
              {tecnico ? 'Esconder a saída do tshark' : 'Ver como o tshark mostra'}</button>
            {tecnico && <pre className="bt-saida" aria-label="Saída do tshark">{atual.eventos.map(linhaTshark).join('\n')}</pre>}
          </>}
        </>}
      </div>}
    </section>
  )
}
