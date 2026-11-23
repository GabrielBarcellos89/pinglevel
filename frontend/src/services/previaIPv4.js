export const PREFIXOS_DIDATICOS = Array.from({ length: 11 }, (_, i) => i + 22)
// Leitura de máscara e capacidade também em /8 e /16; divisão em sub-redes continua de /22 a /32.
export const PREFIXOS_LEITURA = [8, 16, ...PREFIXOS_DIDATICOS]

function numeroIP(ip) {
  if (typeof ip !== 'string' || !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) throw new Error('IPv4 inválido.')
  const partes = ip.split('.').map(Number)
  if (partes.some((n) => n < 0 || n > 255)) throw new Error('IPv4 inválido.')
  return partes.reduce((valor, n) => valor * 256 + n, 0)
}

function textoIP(numero) {
  return [24, 16, 8, 0].map((bits) => (numero >>> bits) & 255).join('.')
}

export function calcularRede(ip, prefixo) {
  if (!PREFIXOS_LEITURA.includes(prefixo)) throw new Error('Esta prévia explora /8, /16 e de /22 a /32.')
  const endereco = numeroIP(ip)
  const total = 2 ** (32 - prefixo)
  const base = Math.floor(endereco / total) * total
  const fim = base + total - 1
  const convencional = prefixo <= 30
  return { ip, prefixo, rede: textoIP(base), cidr: `${textoIP(base)}/${prefixo}`, mascara: textoIP((2 ** 32 - total) >>> 0),
    primeiro: textoIP(convencional ? base + 1 : base), ultimo: textoIP(convencional ? fim - 1 : fim),
    broadcast: convencional ? textoIP(fim) : null, total, hosts: convencional ? total - 2 : total,
    bitsHost: 32 - prefixo, hostValido: convencional ? endereco > base && endereco < fim : true,
    tipo: prefixo === 31 ? 'ponto-a-ponto' : prefixo === 32 ? 'host' : 'lan' }
}

export function calcularDivisao(prefixo, prefixoBase = 24, ipBase = '192.168.10.0') {
  if (!PREFIXOS_DIDATICOS.includes(prefixo) || !PREFIXOS_DIDATICOS.includes(prefixoBase)) throw new Error('A divisão em sub-redes explora de /22 a /32.')
  const redeBase = calcularRede(ipBase, prefixoBase)
  if (prefixo < prefixoBase) throw new Error('O prefixo das partes não pode ser menor que o da origem.')
  return { redeBase, quantidade: 2 ** (prefixo - prefixoBase), tamanho: 2 ** (32 - prefixo) }
}

export function dividirRedeDidatica(prefixo, { prefixoBase = 24, ipBase = '192.168.10.0', offset = 0, limite = 8 } = {}) {
  const plano = calcularDivisao(prefixo, prefixoBase, ipBase)
  if (!Number.isInteger(offset) || offset < 0 || offset >= plano.quantidade || !Number.isInteger(limite) || limite < 1 || limite > 16) throw new Error('Página de sub-redes inválida.')
  const base = numeroIP(plano.redeBase.rede)
  return Array.from({ length: Math.min(limite, plano.quantidade - offset) }, (_, i) => calcularRede(textoIP(base + (offset + i) * plano.tamanho), prefixo))
}

export function avaliarLAN({ ipA, ipB, prefixo, conectada }) {
  if (prefixo === 31 || prefixo === 32) return { estado: 'uso-especial', titulo: prefixo === 31 ? '/31: cenário ponto a ponto' : '/32: um endereço individual', texto: prefixo === 31 ? 'Os dois endereços de /31 podem identificar as pontas de um enlace ponto a ponto. Não tratamos esse caso como a LAN com switch desta atividade.' : '/32 identifica um único IPv4, como uma rota de host. Não forma a LAN de dois computadores desta atividade.' }
  if (!conectada) return { estado: 'sem-enlace', titulo: 'Primeiro, conecte a rede', texto: 'Na simulação, os dois computadores precisam estar ligados ao switch.' }
  if (!ipB) return { estado: 'sem-configuracao', titulo: 'Falta configurar o Computador 2', texto: 'Escolha um endereço IPv4 para a interface do segundo computador.' }
  try {
    const a = calcularRede(ipA, prefixo)
    const b = calcularRede(ipB, prefixo)
    if (!a.hostValido || !b.hostValido) return { estado: 'endereco-reservado', titulo: 'Esse endereço não é um host utilizável', texto: 'Neste exemplo, os endereços de rede e broadcast não podem ser atribuídos aos computadores.' }
    if (ipA === ipB) return { estado: 'ip-duplicado', titulo: 'Os dois computadores estão com o mesmo IP', texto: 'Cada interface precisa de um endereço único dentro desta rede.' }
    if (a.rede !== b.rede) return { estado: 'redes-diferentes', titulo: 'Os computadores ficaram em sub-redes diferentes', texto: `O primeiro pertence a ${a.cidr}; o segundo, a ${b.cidr}. Sem roteador ou rotas neste cenário, não há comunicação IPv4 direta entre eles.` }
    return { estado: 'compativel', titulo: 'Configuração compatível nesta simulação', texto: `Os dois endereços são hosts válidos de ${a.cidr}. Nesta LAN simulada, a comunicação local é possível sem gateway.` }
  } catch {
    return { estado: 'configuracao-invalida', titulo: 'Confira os dados da configuração', texto: 'Use um IPv4 válido e um dos prefixos oferecidos nesta prévia.' }
  }
}
