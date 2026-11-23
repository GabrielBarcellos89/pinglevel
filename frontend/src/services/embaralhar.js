// Sorteia a ordem das opções de uma pergunta (Fisher–Yates) para a resposta certa não cair sempre na mesma posição.
// A ordem é sorteada uma vez por pergunta exibida; as respostas continuam conferidas pelo valor, nunca pela posição.
export function embaralhar(lista, aleatorio = Math.random) {
  const copia = [...lista]
  for (let i = copia.length - 1; i > 0; i -= 1) {
    const j = Math.floor(aleatorio() * (i + 1))
    ;[copia[i], copia[j]] = [copia[j], copia[i]]
  }
  return copia
}
