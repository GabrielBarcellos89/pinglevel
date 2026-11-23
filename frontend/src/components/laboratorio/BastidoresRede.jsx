import { useState } from 'react'
import { Activity, LoaderCircle } from 'lucide-react'
import AprendizagemPing from './AprendizagemPing'

const rotulos = {
  'eth.src': 'MAC de origem', 'eth.dst': 'MAC de destino',
  'arp.opcode': 'Operação ARP', 'arp.src.proto_ipv4': 'IPv4 de origem ARP',
  'arp.dst.proto_ipv4': 'IPv4 procurado/respondido ARP',
  'ip.src': 'IPv4 de origem', 'ip.dst': 'IPv4 de destino', 'ip.ttl': 'TTL',
  'icmp.type': 'Tipo ICMP', 'icmp.code': 'Código ICMP',
  'icmp.ident': 'Identificador ICMP', 'icmp.seq': 'Sequência ICMP',
}

function explicar(evento) {
  switch (evento.tipo) {
    case 'ARP Request': return `${evento.origem} procura o endereço MAC associado a ${evento.destino}.`
    case 'ARP Reply': return `${evento.origem} informa seu endereço MAC a ${evento.destino}.`
    case 'ICMP Echo Request': return `${evento.origem} envia um pedido de resposta a ${evento.destino}.`
    case 'ICMP Echo Reply': return `${evento.origem} responde ao teste de ${evento.destino}.`
    default: return evento.resumo
  }
}

export default function BastidoresRede({ captura, capturando, ativo, aprendizagem, processando, onResponder, sessao }) {
  const [tecnico, setTecnico] = useState(false)
  const eventos = captura?.eventos || []
  const pedidos = eventos.filter((e) => e.tipo === 'ICMP Echo Request').length
  const respostas = eventos.filter((e) => e.tipo === 'ICMP Echo Reply').length
  const temArp = eventos.some((e) => e.protocolo === 'ARP')
  const estado = capturando ? 'Observando…' : {
    concluida: 'Captura concluída', vazia: 'Sem pacotes',
    cancelada: 'Captura cancelada', falha: 'Captura indisponível',
  }[captura?.estado] || (aprendizagem && !aprendizagem.pode_prever ? 'Em espera' : 'Aguardando ping')

  return (
    <section className="lab-painel lab-bastidores" aria-labelledby="lab-bastidores-titulo">
      <header className="lab-bastidores-cabecalho">
        <div><span>BASTIDORES DA REDE</span><h2 id="lab-bastidores-titulo"><Activity size={18} /> O caminho do ping</h2></div>
        <span className="lab-bastidores-estado" role="status">
          {capturando && <LoaderCircle size={14} className="girando" />}{estado}
        </span>
      </header>
      <div className="lab-bastidores-corpo" aria-busy={capturando}>
        <AprendizagemPing key={sessao} aprendizagem={aprendizagem} ativo={ativo}
          processando={processando} onResponder={onResponder} />
        {capturando ? <p className="lab-bastidores-vazio">Observando a comunicação enquanto o comando é executado…</p>
          : !captura ? <p className="lab-bastidores-vazio">{!ativo
            ? 'Inicie a missão para acompanhar a comunicação no momento adequado.'
            : aprendizagem && !aprendizagem.pode_prever
              ? 'Aguardando a etapa de comunicação.'
              : aprendizagem && !aprendizagem.previsao
                ? 'Registre sua previsão antes de acompanhar a comunicação.'
                : 'Execute um ping para observar os pedidos e as respostas entre os computadores.'}</p>
            : <>
              <div className="lab-bastidores-resumo">
                <strong>Último ping observado · Computador {captura.node_id}</strong>
                {eventos.length ? <>
                  <p>{pedidos} pedidos ICMP e {respostas} respostas ICMP observados nesta captura.</p>
                  <p>{temArp
                    ? 'Também houve mensagens ARP para descobrir ou confirmar endereços MAC.'
                    : 'Não houve ARP nesta captura. O endereço MAC pode já estar no cache do computador.'}</p>
                  <small>A captura mostra o tráfego observado; consulte a saída do ping para confirmar perda e latência.</small>
                </> : <p>{captura.estado === 'vazia'
                  ? 'Nenhum pacote ARP ou ICMP foi observado durante a coleta.'
                  : captura.mensagem || 'Não foi possível observar esta execução.'}</p>}
              </div>
              {eventos.length > 0 && <>
                <button className="lab-bastidores-modo" type="button" aria-pressed={tecnico}
                  onClick={() => setTecnico((atual) => !atual)}>
                  {tecnico ? 'Ocultar campos técnicos' : 'Mostrar campos técnicos'}
                </button>
                <ol className="lab-bastidores-eventos">
                  {eventos.map((evento) => (
                    <li key={`${captura.id}-${evento.sequencia}`} className={evento.protocolo === 'ARP' ? 'arp' : 'icmp'}>
                      <div className="lab-bastidores-evento-titulo"><strong>{evento.tipo}</strong>
                        <time>+{Number(evento.tempo_relativo).toFixed(3)} s</time></div>
                      <p>{explicar(evento)}</p>
                      {tecnico && <dl>{Object.entries(evento.campos || {})
                        .filter(([campo]) => rotulos[campo])
                        .map(([campo, valor]) => <div key={campo}><dt>{rotulos[campo]}</dt><dd>{valor}</dd></div>)}</dl>}
                    </li>
                  ))}
                </ol>
              </>}
            </>}
      </div>
    </section>
  )
}
