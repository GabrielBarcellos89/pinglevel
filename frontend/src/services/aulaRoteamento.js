// Conteúdo da aula Roteamento estático (entre o Lab 6 e o Lab 7). Revisão de 15/11/2026: a aula parte do que o aluno fez
// no Lab 6 (um roteador que toca todas as redes) e chega ao cenário do Lab 7 (dois roteadores), explicando antes de
// perguntar. Cenário: PC A 192.168.10.10 — R1 (192.168.10.1 | 10.0.0.1) — R2 (10.0.0.2 | 192.168.20.1) — PC B 192.168.20.10.
import { conferirComando } from './aulaFerramentas.js'

// A topologia da aula: equipamentos e, entre eles, os três trechos de rede com os IPs de cada ponta.
export const EQUIPAMENTOS = [
  { id: 'pca', nome: 'PC A', tipo: 'pc' },
  { id: 'r1', nome: 'R1', tipo: 'roteador' },
  { id: 'r2', nome: 'R2', tipo: 'roteador' },
  { id: 'pcb', nome: 'PC B', tipo: 'pc' },
]
export const TRECHOS = [
  { nome: 'Filial A', rede: '192.168.10.0/24', esquerda: '.10', direita: '.1' },
  { nome: 'Enlace', rede: '10.0.0.0/30', esquerda: '.1', direita: '.2' },
  { nome: 'Filial B', rede: '192.168.20.0/24', esquerda: '.1', direita: '.10' },
]

// Tabelas como o ip route mostra, resumidas. `estatica` só existe depois da rota da etapa 3.
export const TABELAS = {
  pca: [{ linha: 'default via 192.168.10.1', tipo: 'padrao' }, { linha: '192.168.10.0/24 dev eth0', tipo: 'direta' }],
  r1: [{ linha: '192.168.10.0/24 dev eth0', tipo: 'direta' }, { linha: '10.0.0.0/30 dev eth1', tipo: 'direta' }],
  r2: [{ linha: '10.0.0.0/30 dev eth1', tipo: 'direta' }, { linha: '192.168.20.0/24 dev eth0', tipo: 'direta' }],
  pcb: [{ linha: 'default via 192.168.20.1', tipo: 'padrao' }, { linha: '192.168.20.0/24 dev eth0', tipo: 'direta' }],
}
export const ROTA_R1 = { linha: '192.168.20.0/24 via 10.0.0.2 dev eth1', tipo: 'estatica' }
export const ROTA_R2 = { linha: '192.168.10.0/24 via 10.0.0.1 dev eth1', tipo: 'estatica' }

export const PERGUNTAS_CONHECE = [
  { id: 'ate-onde', pergunta: 'Sem nenhuma rota estática, o PC A faz ping ao PC B (192.168.20.10). Até onde o pedido chega?',
    opcoes: [['pcb', 'Chega ao PC B'], ['r1', 'Chega ao R1, que descarta: ele não conhece 192.168.20.0/24'], ['pca', 'Nem sai do PC A']],
    correta: 'r1', erro: 'O PC A tem rota padrão para o R1. Olhe a tabela do R1: alguma linha contém 192.168.20.10?',
    certo: 'O PC A entrega ao R1 pela rota padrão; o R1 não tem linha para 192.168.20.0/24 e descarta.' },
  { id: 'falta', pergunta: 'Que linha falta na tabela do R1 para o pedido seguir?',
    opcoes: [['r1-20', 'Uma rota para 192.168.20.0/24'], ['r1-10', 'Uma rota para 192.168.10.0/24'], ['pca', 'Nenhuma: falta a rota padrão do PC A']],
    correta: 'r1-20', erro: 'O R1 já toca 192.168.10.0/24 e o PC A já tem rota padrão. Qual rede ele não conhece?',
    certo: 'O R1 precisa saber como chegar à rede do PC B. É isso que a rota estática faz.' },
]

export const PERGUNTAS_SALTO = [
  { id: 'r1', pergunta: 'No R1, a rota para 192.168.20.0/24 usa qual próximo salto?',
    opcoes: [['192.168.20.1', '192.168.20.1, o R2 na rede do PC B'], ['10.0.0.2', '10.0.0.2, o R2 no enlace'], ['10.0.0.1', '10.0.0.1, o próprio R1']],
    correta: '10.0.0.2', erro: 'O próximo salto é o vizinho que o R1 alcança direto: em qual rede o R1 e o R2 se encontram?',
    certo: 'O R1 alcança 10.0.0.2 pelo enlace, sem ajuda de ninguém.' },
  { id: 'r2', pergunta: 'E no R2, a rota para 192.168.10.0/24 usa qual próximo salto?',
    opcoes: [['192.168.10.1', '192.168.10.1, o R1 na rede do PC A'], ['10.0.0.1', '10.0.0.1, o R1 no enlace'], ['10.0.0.2', '10.0.0.2, o próprio R2']],
    correta: '10.0.0.1', erro: 'Do lado do R2, o vizinho no enlace é o R1. Qual é o IP dele nessa rede?',
    certo: 'Do lado do R2, o vizinho no enlace é 10.0.0.1.' },
  { id: 'internet', pergunta: 'Com a rota estática, o R1 recebe um pacote para 8.8.8.8. O que acontece?',
    opcoes: [['r2', 'Vai para o R2 pela rota estática'], ['descarta', 'É descartado: nenhuma linha contém 8.8.8.8 e não há rota padrão'], ['volta', 'Volta para o PC A']],
    correta: 'descarta', erro: 'A rota estática vale só para 192.168.20.0/24. 8.8.8.8 está nessa rede?',
    certo: 'Cada rota estática vale só para a rede que ela diz. O resto, sem rota padrão, é descartado.' },
]

// Seguir o pacote: em cada parada, a tabela consultada e a linha usada (o PC B só recebe).
export const PERCURSO = [
  { no: 'pca', linha: 0, texto: '192.168.20.10 não está em 192.168.10.0/24: o PC A usa a rota padrão e entrega ao R1.' },
  { no: 'r1', linha: 2, texto: 'O R1 encontra a rota estática: 192.168.20.0/24 via 10.0.0.2. Entrega ao R2, pelo enlace.' },
  { no: 'r2', linha: 1, texto: 'O R2 toca 192.168.20.0/24 (rota direta): entrega o pacote ao PC B.' },
  { no: 'pcb', linha: null, texto: 'O pedido chegou ao PC B. Agora ele precisa responder para 192.168.10.10.' },
]

export const PERGUNTAS_PERCURSO = [
  { id: 'r2-direta', pergunta: 'Por que o R2 não precisou de rota estática para entregar ao PC B?',
    opcoes: [['direta', 'A rede do PC B está ligada ao R2: é rota direta'], ['padrao', 'O R2 usou uma rota padrão'], ['r1', 'O R1 entregou direto ao PC B']],
    correta: 'direta', erro: 'Olhe a tabela do R2 no passo 3: a linha usada tem "via" ou "dev"?',
    certo: 'Rotas diretas aparecem sozinhas para as redes que o roteador toca.' },
]

// Ida e volta: só o R1 tem a rota estática.
export const VOLTA = [
  { no: 'pcb', texto: 'A resposta sai do PC B para 192.168.10.10 pela rota padrão: vai ao R2.', ok: true },
  { no: 'r2', texto: 'O R2 procura 192.168.10.10 na tabela: só conhece 10.0.0.0/30 e 192.168.20.0/24. Sem rota: descarta.', ok: false },
]

export const PERGUNTAS_VOLTA = [
  { id: 'onde', pergunta: 'Só com a rota no R1, onde a resposta do PC B para?',
    opcoes: [['pcb', 'No PC B, que nem responde'], ['r2', 'No R2, sem rota para 192.168.10.0/24'], ['r1', 'No R1']],
    correta: 'r2', erro: 'Siga a resposta: sai do PC B para 192.168.10.10. Quem não conhece essa rede?',
    certo: 'O pedido chegou, mas a resposta morre no R2: por isso o ping falha.' },
  { id: 'resolve', pergunta: 'Que rota resolve a volta?',
    opcoes: [['r2', 'No R2: 192.168.10.0/24 via 10.0.0.1'], ['r1', 'No R1: 192.168.10.0/24 via 10.0.0.2'], ['pcb', 'No PC B: 192.168.10.0/24 via 10.0.0.1']],
    correta: 'r2', erro: 'A resposta para no R2; o próximo salto precisa ser o vizinho dele no enlace.',
    certo: 'Com a rota no R2, a resposta volta pelo R1 até o PC A.' },
  { id: 'pcb', pergunta: 'O PC B precisa de uma rota para 192.168.10.0/24?',
    opcoes: [['sim', 'Sim, cada PC precisa de uma rota para cada rede'], ['nao', 'Não: a rota padrão dele já leva ao R2']],
    correta: 'nao', erro: 'O PC B já entrega tudo o que não é da rede dele ao R2. O problema estava depois disso.',
    certo: 'Os PCs saem pela rota padrão; quem precisa conhecer as redes distantes são os roteadores.' },
]

export const OBJETIVOS = [
  { id: 'r1', texto: 'No R1: rota para 192.168.20.0/24 pelo R2.', padrao: /^ip\s+r(oute)?\s+add\s+192\.168\.20\.0\/24\s+via\s+10\.0\.0\.2(\s+dev\s+eth1)?$/,
    modelo: 'ip route add <rede>/<prefixo> via <próximo salto>',
    ajuda: { partes: [['ip route add', 'adiciona uma rota'], ['<rede>/<prefixo>', 'a rede de destino, com o prefixo'], ['via <próximo salto>', 'o vizinho que leva até ela']],
      pagina: 13, exemplo: { rotulo: 'Exemplo 2.36', comando: 'ip route add 192.168.8.0/24 via 192.168.254.254' }, pista: 'ip route add 192.168.20.0/24 via ________' } },
  { id: 'r2', texto: 'No R2: rota para 192.168.10.0/24 pelo R1.', padrao: /^ip\s+r(oute)?\s+add\s+192\.168\.10\.0\/24\s+via\s+10\.0\.0\.1(\s+dev\s+eth1)?$/,
    modelo: 'ip route add <rede>/<prefixo> via <próximo salto>',
    ajuda: { partes: [['ip route add', 'adiciona uma rota'], ['<rede>/<prefixo>', 'a rede de destino, com o prefixo'], ['via <próximo salto>', 'o vizinho que leva até ela']],
      pagina: 13, exemplo: { rotulo: 'Exemplo 2.36', comando: 'ip route add 192.168.8.0/24 via 192.168.254.254' }, pista: 'ip route add _______________ via 10.0.0.1' } },
  { id: 'del', texto: 'No R1: remover a rota para 192.168.20.0/24.', padrao: /^ip\s+r(oute)?\s+del\s+192\.168\.20\.0\/24(\s+via\s+10\.0\.0\.2)?$/,
    modelo: 'ip route del <rede>/<prefixo>',
    ajuda: { partes: [['ip route del', 'remove (delete) uma rota'], ['<rede>/<prefixo>', 'a rede de destino da rota a remover']],
      pagina: 13, exemplo: { rotulo: 'Exemplo 2.38', comando: 'ip route del 192.168.8.0/24 via 192.168.254.254' }, pista: 'ip route del ______________' } },
]

export function conferirRota(objetivo, texto) {
  const r = conferirComando(objetivo, texto)
  const normal = String(texto || '').trim().replace(/^\$\s*/, '')
  if (r.ok || !r.retorno || !normal.startsWith('ip ')) return r
  if (/\bvia\s+192\.168\./.test(normal)) return { ok: false, retorno: 'O próximo salto é o vizinho no enlace (10.0.0.x), não uma interface distante.' }
  if (/\badd\s+\d+\.\d+\.\d+\.\d+(\s|$)/.test(normal)) return { ok: false, retorno: 'Informe a rede com o prefixo, por exemplo 192.168.20.0/24.' }
  return { ok: false, retorno: `Confira a forma: ${objetivo.modelo}` }
}
