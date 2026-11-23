// Conteúdo da aula Gateway e entrega local; cenário igual ao do Lab 3. Base: Redes para Iniciantes, p. 154–157.
const REDE_LOCAL = '192.168.10.0'

// Decisão do livro: aplicar a máscara /24 ao destino e comparar com a própria rede.
export function decidir(destino) {
  const redeDestino = `${destino.split('.').slice(0, 3).join('.')}.0`
  const direto = redeDestino === REDE_LOCAL
  return {
    destino, redeDestino, caminho: direto ? 'direto' : 'gateway',
    explicacao: direto
      ? `Com /24, ${destino} pertence a ${redeDestino}, a mesma rede do PC Atendimento: entrega direta.`
      : `Com /24, ${destino} pertence a ${redeDestino}, diferente de ${REDE_LOCAL}: o pacote vai para o gateway.`,
  }
}

export const DESTINOS = [
  { id: 'colega', nome: 'PC Colega', ip: '192.168.10.20' },
  { id: 'servidor', nome: 'Servidor', ip: '192.168.20.10' },
  { id: 'impressora', nome: 'Impressora', ip: '192.168.10.50' },
  { id: 'site', nome: 'Um site na Internet', ip: '8.8.8.8' },
]

export const GATEWAYS = [
  { ip: '192.168.10.20', rotulo: 'PC Colega', correto: false, destaque: ['colega'],
    explicacao: 'O colega está na sua rede, mas é um computador: não encaminha pacotes para outras redes. O gateway precisa ser um roteador.' },
  { ip: '192.168.20.1', rotulo: 'Roteador · lado do Servidor', correto: false, destaque: ['roteador'],
    explicacao: 'Essa interface pertence à rede do Servidor (192.168.20.0/24). O PC Atendimento não a alcança diretamente: o gateway precisa estar na própria rede local.' },
  { ip: '192.168.10.1', rotulo: 'Roteador · lado do Atendimento', correto: true, destaque: ['roteador', 'switch', 'pc'],
    explicacao: 'Isso! É a interface do roteador na rede do Atendimento: alcançável diretamente e capaz de encaminhar para outras redes.' },
]

const ida = [
  { titulo: 'O destino está em outra rede', destaque: ['pc'],
    texto: 'O PC Atendimento aplica a máscara a 192.168.20.10, obtém 192.168.20.0 e compara com a própria rede, 192.168.10.0. São diferentes: o pacote precisa ir ao gateway 192.168.10.1.' },
  { titulo: 'ARP: quem tem 192.168.10.1?', destaque: ['pc', 'switch', 'roteador'],
    texto: 'Para entregar na rede local, o computador precisa do endereço MAC do gateway. Ele pergunta por ARP e o roteador responde com seu MAC.' },
  { titulo: 'Quadro até o roteador', destaque: ['pc', 'switch', 'roteador'],
    texto: 'O pacote IP, ainda destinado a 192.168.20.10, vai dentro de um quadro endereçado ao MAC do roteador.' },
  { titulo: 'O roteador encaminha', destaque: ['roteador', 'servidor'],
    texto: 'O roteador retira o quadro, examina o IP de destino, encontra a rede 192.168.20.0/24 ligada à sua interface 192.168.20.1 e entrega ao Servidor.' },
]

export const PASSOS = {
  normal: [...ida,
    { titulo: 'A resposta usa o gateway do Servidor', destaque: ['servidor', 'roteador'],
      texto: 'Para responder, o Servidor faz a mesma decisão: 192.168.10.10 está em outra rede, então ele envia ao seu gateway, 192.168.20.1.' },
    { titulo: 'Ida e volta completas', destaque: ['roteador', 'switch', 'pc'],
      texto: 'O roteador entrega a resposta ao PC Atendimento. O ping mostra respostas: houve caminho de ida e de volta.' }],
  semGateway: [...ida,
    { titulo: 'O Servidor não tem por onde responder', destaque: ['servidor'], falha: true,
      texto: 'Sem gateway, o Servidor não tem rota para 192.168.10.0/24. A resposta é descartada ali mesmo.' },
    { titulo: 'A ida chegou, a volta não', destaque: ['pc'], falha: true,
      texto: 'O PC Atendimento não recebe resposta e o ping mostra 100% de perda, embora o pedido tenha chegado ao Servidor. Toda comunicação precisa de caminho de volta.' }],
}

export const PERGUNTAS = [
  { id: 'colega', texto: 'Por que o PC Colega responde mesmo sem gateway configurado?', correta: 'mesma-rede',
    opcoes: [['switch-roteia', 'Porque o switch encaminha para qualquer rede.'], ['mesma-rede', 'Porque está na mesma rede: a entrega é direta.'],
      ['gateway-colega', 'Porque o colega usa o gateway do roteador por ele.']],
    acerto: 'Isso: destinos da mesma rede não passam pelo gateway.', dica: 'Pense na comparação de redes da primeira etapa.' },
  { id: 'gateway-outra-rede', texto: 'Se o PC Atendimento usar 192.168.20.1 como gateway, o que acontece?', correta: 'nao-alcanca',
    opcoes: [['funciona', 'Funciona igual, porque também é o roteador.'], ['so-colega', 'Só o colega deixa de responder.'],
      ['nao-alcanca', 'Não funciona: o gateway precisa estar na rede local do computador.']],
    acerto: 'Isso: o computador só entrega diretamente a quem está na própria rede.', dica: 'Reveja a etapa de escolha do gateway.' },
  { id: 'volta', texto: 'Na etapa anterior, por que o ping falhou quando o Servidor ficou sem gateway?', correta: 'sem-volta',
    opcoes: [['pc-sem-gateway', 'Porque o PC Atendimento ficou sem gateway.'], ['sem-volta', 'Porque o Servidor não tinha caminho de volta para a rede do Atendimento.'],
      ['switch-bloqueou', 'Porque o switch bloqueou a resposta.']],
    acerto: 'Isso: a resposta também é um pacote para outra rede.', dica: 'Volte à animação e veja até onde o pedido chegou.' },
]
