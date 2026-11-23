// Detalhes da introdução ficam apenas neste navegador; o contrato do servidor não muda.
export function lerIntroducaoIPv4(texto) {
  try {
    const s = JSON.parse(texto)
    const prefixo = (p) => Number.isInteger(p) && p >= 22 && p <= 32
    const indice = (n) => Number.isInteger(n) && n >= 0
    if (!s || s.versao !== 1 || !indice(s.cena) || s.cena > 6
      || !prefixo(s.prefixo) || !prefixo(s.lanPrefixo) || !prefixo(s.prefixoBase)
      || !prefixo(s.divisao) || s.divisao < s.prefixoBase
      || !['outroHost', 'conectada'].every((k) => typeof s[k] === 'boolean')
      || !['', '192.168.10.0', '192.168.10.10', '192.168.10.20', '192.168.10.80'].includes(s.ipB)
      || !indice(s.paginaSubredes) || !indice(s.subredeAtiva)) return null
    const quantidade = 2 ** (s.divisao - s.prefixoBase)
    if (s.paginaSubredes >= Math.ceil(quantidade / 8)
      || s.subredeAtiva >= Math.min(8, quantidade - s.paginaSubredes * 8)) return null
    return { versao: 1, cena: s.cena, outroHost: s.outroHost, prefixo: s.prefixo,
      ipB: s.ipB, lanPrefixo: s.lanPrefixo, conectada: s.conectada,
      divisao: s.divisao, prefixoBase: s.prefixoBase,
      paginaSubredes: s.paginaSubredes, subredeAtiva: s.subredeAtiva }
  } catch { return null }
}
