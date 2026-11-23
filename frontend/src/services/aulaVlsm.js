// Conteúdo e cálculos da aula VLSM. Base: Redes para Iniciantes p. 75–76 (prefixo) e p. 245 (VLSM).
import { hostsUteis, paraNumero, paraTexto, prefixoParaHosts, tamanhoBloco } from './aulaPlano.js'

export const REDE = '192.168.60.0/24'

// Demandas de endereços (já contando o gateway; o enlace entre roteadores usa dois endereços).
export const DEMANDAS = [
  { id: 'vendas', nome: 'Vendas', enderecos: 51, detalhe: '50 computadores + gateway' },
  { id: 'enlace', nome: 'Enlace entre roteadores', enderecos: 2, detalhe: 'um endereço em cada ponta' },
  { id: 'atendimento', nome: 'Atendimento', enderecos: 101, detalhe: '100 computadores + gateway' },
  { id: 'financeiro', nome: 'Financeiro', enderecos: 21, detalhe: '20 computadores + gateway' },
].map((d) => ({ ...d, prefixo: prefixoParaHosts(d.enderecos) }))

export const alinhado = (ip, prefixo) => paraNumero(ip) % tamanhoBloco(prefixo) === 0

export function faixa(rede, prefixo) {
  const inicio = paraNumero(rede)
  return [inicio, inicio + tamanhoBloco(prefixo) - 1]
}

export function sobrepoe(a, b) {
  const [ia, fa] = faixa(a.rede, a.prefixo)
  const [ib, fb] = faixa(b.rede, b.prefixo)
  return ia <= fb && ib <= fa
}

// VLSM: do maior bloco para o menor, cada um no primeiro endereço livre e alinhado.
export function planejar(demandas, rede = REDE) {
  let proximo = paraNumero(rede.split('/')[0])
  return [...demandas].sort((a, b) => a.prefixo - b.prefixo).map((d) => {
    const tamanho = tamanhoBloco(d.prefixo)
    proximo = Math.ceil(proximo / tamanho) * tamanho
    const bloco = { ...d, rede: paraTexto(proximo) }
    proximo += tamanho
    return bloco
  })
}

export const PLANO = planejar(DEMANDAS)
export const ORDEM_CORRETA = PLANO.map((b) => b.id)

// Com blocos iguais, o maior setor define o tamanho de todos.
export const PREFIXO_IGUAL = Math.min(...DEMANDAS.map((d) => d.prefixo))
export const BLOCOS_IGUAIS = 256 / tamanhoBloco(PREFIXO_IGUAL)

export const ALINHAMENTOS = [
  { rede: '192.168.60.64', prefixo: 26 },
  { rede: '192.168.60.32', prefixo: 26 },
  { rede: '192.168.60.96', prefixo: 27 },
  { rede: '192.168.60.40', prefixo: 28 },
].map((a) => ({ ...a, correta: alinhado(a.rede, a.prefixo) ? 'sim' : 'nao' }))

// Plano com um erro de sobreposição para o aluno encontrar.
export const PLANO_COM_ERRO = [
  { id: 'a', nome: 'Atendimento', rede: '192.168.70.0', prefixo: 25 },
  { id: 'b', nome: 'Vendas', rede: '192.168.70.128', prefixo: 26 },
  { id: 'c', nome: 'Financeiro', rede: '192.168.70.160', prefixo: 27 },
  { id: 'd', nome: 'Enlace', rede: '192.168.70.224', prefixo: 30 },
]
export const PARES = PLANO_COM_ERRO.flatMap((a, i) => PLANO_COM_ERRO.slice(i + 1).map((b) => ({ id: `${a.id}-${b.id}`, a, b })))
export const PAR_SOBREPOSTO = PARES.filter((p) => sobrepoe(p.a, p.b)).map((p) => p.id)

export function conferirRede(digitado, bloco) {
  const n = paraNumero(digitado)
  if (n === null) return { ok: false, retorno: 'Escreva o endereço de rede completo, como 192.168.60.0.' }
  if (paraTexto(n) === bloco.rede) return { ok: true, retorno: '' }
  if (n % tamanhoBloco(bloco.prefixo) !== 0) return { ok: false, retorno: `Não está alinhado: um /${bloco.prefixo} começa em múltiplos de ${tamanhoBloco(bloco.prefixo)}.` }
  return { ok: false, retorno: 'Use o primeiro endereço livre depois do bloco anterior.' }
}

export { hostsUteis, tamanhoBloco }
