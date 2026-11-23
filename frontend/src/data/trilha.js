// Paradas da trilha na ordem do mapa do curso (docs/projeto/47_MAPA_DO_CURSO.md; revisão de 15/11/2026: Ethernet, MAC e
// ARP no Módulo 1, Transporte abrindo o Módulo 3 e a LAN antes dos serviços). `atividade` liga a parada ao
// catálogo; paradas sem atividade publicada aparecem bloqueadas ("em breve"). `arte` é o arquivo em assets/trilha:
// ligado pelo nome, não pela posição, para que uma aula nova não desloque as artes (Ethernet e Transporte ainda sem arte).
import { ATIVIDADES, situacaoAtividade } from './catalogo.js'

export const PARADAS = [
  { modulo: 1, tipo: 'aula', titulo: 'O que é uma rede?', atividade: 'fundamentos-aula-1', arte: '01-o-que-e-uma-rede' },
  { modulo: 1, tipo: 'aula', titulo: 'Modelos OSI e TCP/IP', atividade: 'fundamentos-modelos-osi-tcpip', arte: '02-modelos-osi-tcp-ip' },
  { modulo: 1, tipo: 'aula', titulo: 'Endereçamento IPv4', atividade: 'enderecamento-ipv4', arte: '03-enderecamento-ipv4' },
  { modulo: 1, tipo: 'laboratorio', titulo: 'Lab 1 · Missão: Primeiro Contato', atividade: 'primeiro-contato', arte: '04-lab1-primeiro-contato' },
  { modulo: 1, tipo: 'aula', titulo: 'Ethernet, MAC e ARP', atividade: 'fundamentos-ethernet-arp' },
  { modulo: 1, tipo: 'laboratorio', titulo: 'Lab 2 · Monte sua primeira LAN', atividade: 'primeira-lan', arte: '05-lab2-primeira-lan' },
  { modulo: 1, tipo: 'aula', titulo: 'Gateway e entrega local', atividade: 'fundamentos-gateway', arte: '06-gateway-entrega-local' },
  { modulo: 1, tipo: 'laboratorio', titulo: 'Lab 3 · Dentro ou fora da minha rede?', atividade: 'saindo-da-rede-local', arte: '07-lab3-dentro-fora' },
  { modulo: 1, tipo: 'aula', titulo: 'Ferramentas: interfaces, rotas e testes', atividade: 'fundamentos-ferramentas', arte: '08-ferramentas-interfaces-rotas-testes' },
  { modulo: 1, tipo: 'laboratorio', titulo: 'Lab 4 · Configure pelo terminal', atividade: 'configure-pelo-terminal', arte: '09-lab4-configure-terminal' },
  { modulo: 2, tipo: 'aula', titulo: 'Plano de endereçamento e sub-redes', atividade: 'planejamento-enderecamento', arte: '10-plano-enderecamento-sub-redes' },
  { modulo: 2, tipo: 'laboratorio', titulo: 'Lab 5 · Dividindo uma rede', atividade: 'dividindo-uma-rede', arte: '11-lab5-dividindo-rede' },
  { modulo: 2, tipo: 'aula', titulo: 'VLSM', atividade: 'planejamento-vlsm', arte: '12-vlsm' },
  { modulo: 2, tipo: 'laboratorio', titulo: 'Lab 6 · Planejando uma empresa', atividade: 'planejando-uma-empresa', arte: '13-lab6-planejando-empresa' },
  { modulo: 2, tipo: 'aula', titulo: 'Roteamento estático', atividade: 'planejamento-roteamento', arte: '14-roteamento-estatico' },
  { modulo: 2, tipo: 'laboratorio', titulo: 'Lab 7 · Conectando redes', atividade: 'conectando-redes', arte: '15-lab7-conectando-redes' },
  { modulo: 3, tipo: 'aula', titulo: 'Transporte: portas, TCP e UDP', atividade: 'servicos-transporte' },
  { modulo: 3, tipo: 'aula', titulo: 'Switch e VLANs', atividade: 'servicos-lan', arte: '18-ethernet-arp-switch-vlans' },
  { modulo: 3, tipo: 'laboratorio', titulo: 'Lab 8 · Investigando e separando a LAN', atividade: 'investigando-a-lan', arte: '19-lab9-investigando-lan' },
  { modulo: 3, tipo: 'aula', titulo: 'DHCP e DNS', atividade: 'servicos-dhcp-dns', arte: '16-dhcp-dns' },
  { modulo: 3, tipo: 'laboratorio', titulo: 'Lab 9 · Endereços e nomes automáticos', atividade: 'enderecos-e-nomes', arte: '17-lab8-enderecos-nomes' },
  { modulo: 3, tipo: 'desafio', titulo: 'Lab 10 · Desafio final: a rede da empresa', atividade: 'desafio-rede-da-empresa', arte: '20-lab10-desafio-final' },
]

export const NOMES_MODULOS = { 1: 'Fundamentos', 2: 'Planejamento e roteamento', 3: 'Serviços, switching e desafio' }

// Estado de cada parada: concluída, em andamento, disponível ou bloqueada; a primeira não concluída é "atual".
export function montarTrilha(resumo) {
  const paradas = PARADAS.map((p, indice) => {
    const item = ATIVIDADES.find((a) => a.id === p.atividade)
    if (!item) return { ...p, indice, estado: 'bloqueada' }
    const situacao = resumo ? situacaoAtividade(item, resumo) : null
    const estado = situacao?.id === 'concluida' ? 'concluida' : situacao?.id === 'andamento' ? 'andamento' : 'disponivel'
    return { ...p, indice, estado, caminho: item.caminho, percentual: situacao?.percentual ?? null }
  })
  const atual = paradas.find((p) => p.estado === 'andamento' || p.estado === 'disponivel')
  return paradas.map((p) => ({ ...p, atual: p === atual }))
}

const ROTULO_ACAO = {
  aula: { iniciar: 'Começar aula', continuar: 'Continuar aula' },
  laboratorio: { iniciar: 'Abrir laboratório', continuar: 'Abrir laboratório' },
  desafio: { iniciar: 'Abrir o desafio final', continuar: 'Abrir o desafio final' },
}

// Resumo da Início, tirado da mesma trilha: próximo passo, total concluído e situação de cada módulo.
export function resumoInicio(resumo) {
  const paradas = montarTrilha(resumo)
  const atual = paradas.find((p) => p.atual) ?? null
  const proximo = atual && {
    ...atual,
    numero: atual.indice + 1,
    acao: ROTULO_ACAO[atual.tipo][atual.estado === 'andamento' ? 'continuar' : 'iniciar'],
  }
  const modulos = Object.entries(NOMES_MODULOS).map(([numero, nome]) => {
    const doModulo = paradas.filter((p) => p.modulo === Number(numero))
    const concluidas = doModulo.filter((p) => p.estado === 'concluida').length
    const aulas = doModulo.filter((p) => p.tipo === 'aula').length
    const estado = concluidas === doModulo.length ? 'concluido' : doModulo.some((p) => p.atual) ? 'atual'
      : concluidas > 0 ? 'andamento' : 'a-fazer'
    // "Continuar" leva ao próximo passo; os outros abrem a primeira parada não concluída (ou a primeira, para revisar).
    const destino = doModulo.find((p) => p.atual) ?? doModulo.find((p) => p.estado !== 'concluida') ?? doModulo[0]
    return { numero: Number(numero), nome, total: doModulo.length, concluidas, aulas, laboratorios: doModulo.length - aulas,
      estado, caminho: destino.caminho }
  })
  return {
    proximo,
    total: paradas.length,
    concluidas: paradas.filter((p) => p.estado === 'concluida').length,
    laboratorios: paradas.filter((p) => p.tipo !== 'aula'),
    modulos,
  }
}
