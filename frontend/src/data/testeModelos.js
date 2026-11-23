// Teste final da aula Modelos OSI e TCP/IP (revisão de 30/10/2026): situações em que o aluno diz qual camada está
// envolvida, no lugar de copiar a tabela. A pergunta de MAC saiu: volta na aula de Ethernet e ARP (módulo 3).
export const PERGUNTAS_TESTE = [
  { id: 'acentos', correta: '6',
    texto: 'A mensagem chegou, mas os acentos viraram símbolos estranhos (“Ã§” no lugar de “ç”). Qual tarefa falhou?',
    opcoes: [['6', '6 · Apresentação'], ['4', '4 · Transporte'], ['3', '3 · Rede'], ['1', '1 · Física']],
    acerto: 'A Apresentação cuida do formato do texto. Se os dois lados não usam a mesma regra (como o UTF-8), as letras viram símbolos.',
    dica: 'O texto chegou inteiro, só mudou a forma das letras. Qual camada cuida do formato dos dados?' },
  { id: 'programa', correta: 'porta',
    texto: 'A mensagem chegou ao servidor certo, mas foi entregue ao programa errado. O que indica o programa certo?',
    opcoes: [['porta', 'A porta · 4 · Transporte'], ['ip', 'O endereço IP · 3 · Rede'], ['sinal', 'O sinal de rádio · 1 · Física']],
    acerto: 'O IP leva até o equipamento; a porta escolhe o programa dentro dele, como o número do apartamento num prédio.',
    dica: 'O equipamento estava certo. Lembre do prédio: o que indica o apartamento?' },
  { id: 'roteador', correta: 'ip',
    texto: 'Um roteador precisa decidir para qual rede mandar o pacote. O que ele consulta?',
    opcoes: [['ip', 'O endereço IP de destino · 3 · Rede'], ['porta', 'A porta do serviço · 4 · Transporte'], ['texto', 'O texto da mensagem · 7 · Aplicação']],
    acerto: 'O roteador lê o endereço IP de destino para escolher o caminho entre redes, como o CEP numa encomenda.',
    dica: 'O roteador não abre a mensagem nem procura o programa: ele só precisa saber para onde o pacote vai.' },
  { id: 'sinal', correta: '1',
    texto: 'O sinal do Wi-Fi caiu e nada é transmitido. Qual camada é afetada primeiro?',
    opcoes: [['1', '1 · Física'], ['2', '2 · Enlace'], ['3', '3 · Rede'], ['7', '7 · Aplicação']],
    acerto: 'Sem sinal não há transmissão: é a camada Física, a da base. Ao investigar um defeito, comece por ela.',
    dica: 'Pense na camada que transforma tudo em sinais de rádio, luz ou eletricidade.' },
  { id: 'ordem', correta: '1-7',
    texto: 'O celular de Bruno começa a receber. Em que ordem as camadas trabalham?',
    opcoes: [['1-7', 'Da camada 1 (Física) até a 7 (Aplicação)'], ['7-1', 'Da camada 7 (Aplicação) até a 1 (Física)']],
    acerto: 'Quem recebe começa pelos sinais e sobe até a mensagem aparecer na conversa.',
    dica: 'O que chega primeiro ao celular de Bruno: os sinais ou a mensagem pronta?' },
  { id: 'grupo', correta: 'aplicacao',
    texto: 'As camadas 7, 6 e 5 do OSI ficam em qual grupo do TCP/IP?',
    opcoes: [['aplicacao', 'Aplicação'], ['transporte', 'Transporte'], ['internet', 'Internet'], ['acesso', 'Acesso à rede']],
    acerto: 'No TCP/IP, o grupo Aplicação junta as três camadas de cima do OSI.',
    dica: 'São as três camadas mais perto do app. Abra “Ver a tabela TCP/IP” se precisar.' },
  { id: 'transporte', correta: 'udp',
    texto: 'Numa chamada de vídeo, é melhor chegar rápido, mesmo perdendo um pedacinho. Qual protocolo de transporte combina?',
    opcoes: [['udp', 'UDP · manda e segue, sem conferir'], ['tcp', 'TCP · confere e reenvia o que se perdeu']],
    acerto: 'O UDP não espera reenvio: a conversa continua fluindo, mesmo que um pedacinho da imagem se perca.',
    dica: 'Esperar o reenvio de cada pedaço faria a imagem travar. Qual dos dois não confere a entrega?' },
]

export const RESPOSTAS_VAZIAS = Object.fromEntries(PERGUNTAS_TESTE.map((p) => [p.id, '']))

export function respostaValida(id, valor) {
  const pergunta = PERGUNTAS_TESTE.find((p) => p.id === id)
  return Boolean(pergunta) && (valor === '' || pergunta.opcoes.some(([opcao]) => opcao === valor))
}

export function avaliarTeste(respostas) {
  const erradas = PERGUNTAS_TESTE.filter((p) => respostas[p.id] !== p.correta).map((p) => p.id)
  return { completo: PERGUNTAS_TESTE.every((p) => respostas[p.id]), aprovado: erradas.length === 0, erradas }
}

// "Tentar de novo" apaga só as respostas erradas.
export function limparErradas(respostas) {
  const { erradas } = avaliarTeste(respostas)
  return { ...respostas, ...Object.fromEntries(erradas.map((id) => [id, ''])) }
}

// As opções aparecem em ordem aleatória (sorteada ao abrir o teste), para a resposta certa não ficar sempre no mesmo
// lugar. A ordem vale até o aluno sair do teste: "Tentar de novo" não troca as opções de lugar.
export function embaralharOpcoes(opcoes, aleatorio = Math.random) {
  const copia = [...opcoes]
  for (let i = copia.length - 1; i > 0; i -= 1) {
    const j = Math.floor(aleatorio() * (i + 1))
    ;[copia[i], copia[j]] = [copia[j], copia[i]]
  }
  return copia
}

// Tela "TCP ou UDP?" (30/10/2026): quatro situações para classificar antes do teste final.
export const SITUACOES_TRANSPORTE = [
  { id: 'mensagem', texto: 'Mandar uma mensagem no app de conversa.', correta: 'tcp',
    explicacao: 'Cada letra precisa chegar, e na ordem certa: o TCP confere e reenvia o que se perder.' },
  { id: 'arquivo', texto: 'Baixar um arquivo ou abrir uma página da web.', correta: 'tcp',
    explicacao: 'Um arquivo com um pedaço faltando fica estragado: vale esperar o TCP reenviar.' },
  { id: 'video', texto: 'Fazer uma chamada de vídeo.', correta: 'udp',
    explicacao: 'É melhor perder um pedacinho da imagem do que a conversa travar esperando um reenvio.' },
  { id: 'dns', texto: 'Perguntar ao DNS o endereço de um site.', correta: 'udp',
    explicacao: 'É uma pergunta curta: se a resposta não vier, o computador pergunta de novo. Você vai ver o DNS no Lab 9.' },
]
