// Conteúdo e cálculos da aula Plano de endereçamento e sub-redes. Base: Redes para Iniciantes p. 75–78.

export const FAIXAS_PRIVADAS = [
  { rede: '10.0.0.0/8', de: '10.0.0.0', ate: '10.255.255.255',
    regra: 'Basta o primeiro número ser 10. O /8 fixa só esse número; os outros três podem ser qualquer coisa.',
    exemplos: 'Privado: 10.0.0.1, 10.200.3.4 · Público: 11.0.0.1' },
  { rede: '172.16.0.0/12', de: '172.16.0.0', ate: '172.31.255.255',
    regra: 'Primeiro número 172 e o segundo de 16 a 31. O /12 fixa o 172 e só parte do segundo número, por isso a faixa vai de 16 até 31.',
    exemplos: 'Privado: 172.16.0.1, 172.31.9.9 · Público: 172.15.0.1, 172.32.0.1' },
  { rede: '192.168.0.0/16', de: '192.168.0.0', ate: '192.168.255.255',
    regra: 'Os dois primeiros números precisam ser 192.168. O /16 fixa esses dois; os dois últimos variam.',
    exemplos: 'Privado: 192.168.0.1, 192.168.50.7 · Público: 192.169.0.1, 192.167.0.1' },
]

// Explica por que cada endereço do exercício é privado ou público, número a número.
export function explicarClassificacao(ip) {
  const [a, b] = ip.split('.').map(Number)
  if (a === 10) return 'Começa com 10: está na faixa 10.0.0.0/8, então é privado.'
  if (a === 172) return b >= 16 && b <= 31 ? `Começa com 172 e o segundo número (${b}) está entre 16 e 31: é privado.`
    : `Começa com 172, mas o segundo número (${b}) está fora de 16 a 31: é público.`
  if (a === 192) return b === 168 ? 'Começa com 192.168: está na faixa 192.168.0.0/16, então é privado.'
    : `Começa com 192, mas o segundo número é ${b}, não 168: é público.`
  return `O primeiro número (${a}) não é 10, 172 nem 192: está fora das três faixas, é público.`
}

export function paraNumero(ip) {
  const partes = String(ip).trim().split('.')
  if (partes.length !== 4 || partes.some((p) => !/^\d{1,3}$/.test(p) || Number(p) > 255)) return null
  return partes.reduce((total, p) => total * 256 + Number(p), 0)
}

export function paraTexto(numero) {
  return [24, 16, 8, 0].map((d) => Math.floor(numero / 2 ** d) % 256).join('.')
}

export function ehPrivado(ip) {
  const n = paraNumero(ip)
  return FAIXAS_PRIVADAS.some((f) => n >= paraNumero(f.de) && n <= paraNumero(f.ate))
}

export const CLASSIFICAR = ['10.20.5.4', '172.32.0.5', '192.168.1.10', '8.8.8.8', '172.31.200.1', '192.169.0.1']
  .map((ip) => ({ ip, correta: ehPrivado(ip) ? 'privado' : 'publico' }))

export const OPCOES_ESPECIAIS = [
  ['broadcast', 'Broadcast: chega a todos da rede'],
  ['loopback', 'Loopback: o próprio computador'],
  ['sem-endereco', 'Ainda sem endereço (ou "qualquer rede" na rota padrão)'],
  ['link-local', 'Link-local: escolhido sozinho quando o DHCP não respondeu'],
]
// Explicação mostrada antes do exercício: a regra de cada tipo, com faixas (o exercício usa outros exemplos).
export const EXPLICA_ESPECIAIS = [
  { faixa: '127.x.x.x', nome: 'Loopback', texto: 'O computador falando com ele mesmo. O pacote nem sai pela placa de rede: ping 127.0.0.1 testa só se o TCP/IP do próprio computador funciona.' },
  { faixa: '169.254.x.x', nome: 'Link-local', texto: 'O computador pediu endereço ao DHCP, ninguém respondeu, e ele escolheu um sozinho nessa faixa. Ver 169.254 é sinal de problema no DHCP.' },
  { faixa: '0.0.0.0', nome: 'Nenhum / qualquer', texto: 'Usado pelo computador que ainda não tem endereço (no pedido ao DHCP). Na tabela de rotas, 0.0.0.0/0 quer dizer "qualquer destino": é a rota padrão.' },
  { faixa: 'último da rede', nome: 'Broadcast', texto: 'Com todos os bits de host em 1, é o último endereço da rede: em 192.168.1.0/24 é 192.168.1.255. Um pacote para ele chega a todos da rede.' },
  { faixa: 'primeiro da rede', nome: 'Endereço da rede', texto: 'Com todos os bits de host em 0 (como 192.168.1.0 em /24), identifica a rede inteira. Também não vai para um computador.' },
]
export const ESPECIAIS = [
  { ip: '127.0.0.1', correta: 'loopback', porque: 'Tudo que começa com 127 é loopback: o próprio computador.' },
  { ip: '169.254.12.7', correta: 'link-local', porque: 'Começa com 169.254: o computador se deu esse endereço porque o DHCP não respondeu.' },
  { ip: '0.0.0.0', correta: 'sem-endereco', porque: 'Tudo zero: ainda sem endereço, ou "qualquer rede" na rota padrão.' },
  { ip: '192.168.10.255', contexto: 'na rede 192.168.10.0/24', correta: 'broadcast', porque: 'Em /24 o último número é o host; 255 é o último endereço da rede, o broadcast.' },
]

export const tamanhoBloco = (prefixo) => 2 ** (32 - prefixo)
export const hostsUteis = (prefixo) => tamanhoBloco(prefixo) - 2

// Menor bloco (maior prefixo) cujos hosts úteis atendem à demanda.
export function prefixoParaHosts(hosts) {
  for (let prefixo = 30; prefixo >= 8; prefixo -= 1) if (hostsUteis(prefixo) >= hosts) return prefixo
  return null
}

export const PERGUNTAS_HOSTS = [26, 27, 28].map((prefixo) => ({ prefixo, correta: hostsUteis(prefixo) }))

export const DEMANDAS = [
  { setor: 'Vendas', computadores: 50 },
  { setor: 'Atendimento', computadores: 100 },
  { setor: 'Diretoria', computadores: 14 },
  { setor: 'Suporte', computadores: 12 },
].map((d) => ({ ...d, correta: prefixoParaHosts(d.computadores + 1) }))
export const PREFIXOS_OPCOES = [24, 25, 26, 27, 28, 29]

// Divide uma rede em blocos iguais do prefixo pedido.
export function subdividir(rede, prefixo) {
  const [ip, base] = rede.split('/')
  const inicio = paraNumero(ip)
  const tamanho = tamanhoBloco(prefixo)
  return Array.from({ length: 2 ** (prefixo - Number(base)) }, (_, i) => {
    const primeiro = inicio + i * tamanho
    return { rede: paraTexto(primeiro), broadcast: paraTexto(primeiro + tamanho - 1),
      primeiroHost: paraTexto(primeiro + 1), ultimoHost: paraTexto(primeiro + tamanho - 2) }
  })
}

export const REDE_DIVIDIR = '192.168.50.0/24'
export const BLOCOS = subdividir(REDE_DIVIDIR, 26)

export function conferirEndereco(digitado, esperado, tipo = 'rede') {
  const n = paraNumero(digitado)
  if (n === null) return { ok: false, retorno: 'Escreva um endereço IPv4 completo, como 192.168.50.0.' }
  if (paraTexto(n) === esperado) return { ok: true, retorno: '' }
  return { ok: false, retorno: tipo === 'rede' ? 'Cada bloco /26 tem 64 endereços: some 64 ao início do bloco anterior.'
    : 'O broadcast é o último endereço do bloco, logo antes da rede seguinte.' }
}
