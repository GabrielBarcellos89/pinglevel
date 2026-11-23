// Funções do modelo: não criamos cabeçalhos fictícios nas camadas superiores.
export const CONTEUDOS_ADICIONAIS = {
  5: {
    subtitulo: 'Organizar o diálogo entre os participantes.',
    antes: 'Uma comunicação precisa de organização: quando a troca começa, como continua e quando termina. No modelo OSI, essas funções estão relacionadas à Sessão.',
    depois: 'Início, troca e encerramento: você organizou o diálogo. Isso é diferente de escolher uma porta ou um endereço IP.',
    acao: 'Organizar a troca',
    proxima: 'Como encontrar o serviço certo?',
  },
  4: {
    subtitulo: 'Levar os dados ao processo certo.',
    antes: 'Um servidor pode executar vários serviços. Como os dados chegam ao serviço de mensagens, e não a outro processo?',
    depois: 'As portas identificam os processos da comunicação. Neste exemplo usamos TCP, que também organiza a entrega dos dados em ordem e trata perdas.',
    acao: 'Ver as portas',
    proxima: 'E o endereço do destino?',
  },
  3: {
    subtitulo: 'Endereçar e encaminhar o pacote pela rede.',
    antes: 'Bruno é o destinatário da conversa. Mas o primeiro trecho vai até o servidor do aplicativo: é esse destino que o pacote precisa identificar.',
    depois: 'O pacote tem um endereço IP de destino. Os roteadores usam informações da rede para encaminhá-lo. Primeiro ao servidor; a entrega a Bruno será outra comunicação.',
    acao: 'Identificar o destino IP',
    proxima: 'Como sair pela rede local?',
  },
  2: {
    subtitulo: 'Preparar a entrega no enlace local.',
    antes: 'Antes de atravessar outras redes, o celular precisa usar sua própria rede local. Neste exemplo, o primeiro enlace é Wi-Fi, até o ponto de acesso.',
    depois: 'O pacote IP vai dentro de um quadro Wi-Fi. O quadro tem informações de endereçamento MAC e de verificação de erros para esse enlace, não para a conversa inteira.',
    acao: 'Preparar o quadro Wi-Fi',
    proxima: 'Como isso vira uma transmissão?',
  },
  1: {
    subtitulo: 'Transmitir a informação por sinais no meio físico.',
    antes: 'O quadro não viaja como uma caixinha. No primeiro enlace, o celular transmite a informação usando sinais de rádio pelo Wi-Fi.',
    depois: 'Você representou a transmissão por sinais de rádio no primeiro enlace. Ao longo do caminho, outros enlaces podem usar outros meios, como cabo ou fibra.',
    acao: 'Transmitir pelo Wi-Fi',
    proxima: 'Ver o recebimento',
  },
}

export const RECEBIMENTO = [
  { numero: 1, nome: 'Física', texto: 'O celular recebe sinais e recupera a informação em bits.', estado: 'Recebendo sinais' },
  { numero: 2, nome: 'Enlace', texto: 'A rede local interpreta e verifica o quadro. Seu conteúdo segue para a camada de Rede.', estado: 'Interpretando o quadro' },
  { numero: 3, nome: 'Rede', texto: 'O celular trata o pacote IP destinado a ele e encaminha os dados para o protocolo de transporte.', estado: 'Interpretando o pacote IP' },
  { numero: 4, nome: 'Transporte', texto: 'O TCP organiza os dados recebidos e usa as portas para entregá-los ao processo correto.', estado: 'Organizando os dados' },
  { numero: 5, nome: 'Sessão', texto: 'No modelo OSI, as funções de Sessão ajudam a coordenar o diálogo da comunicação.', estado: 'Coordenando o diálogo' },
  { numero: 6, nome: 'Apresentação', texto: 'A representação do texto é interpretada. Com UTF-8, os caracteres podem ser reconhecidos corretamente.', estado: 'Interpretando o texto' },
  { numero: 7, nome: 'Aplicação', texto: 'O serviço de comunicação disponibiliza a mensagem ao aplicativo, que agora pode mostrá-la na conversa de Bruno.', estado: 'Mensagem exibida na simulação' },
]


// Revisão de 30/10/2026: uma frase "em palavras simples" e os termos novos de cada camada, para quem nunca estudou redes.
export const SIMPLES = {
  7: 'É o app de conversa pedindo à rede: “entregue este Oi! ao serviço de mensagens”.',
  6: 'É combinar o idioma: o texto vira números que o outro celular sabe transformar de volta em letras.',
  5: 'É organizar a conversa: quando começa, como as falas se alternam e quando termina.',
  4: 'O servidor é como um prédio com vários serviços, e a porta é o número do apartamento. Aqui também se confere se nada se perdeu no caminho.',
  3: 'É o endereço do destino (o IP), como o CEP e o número da casa numa encomenda. Os roteadores leem esse endereço para escolher o caminho.',
  2: 'É a entrega até o próximo equipamento da rede local, como levar a encomenda até a agência do bairro.',
  1: 'É o transporte de verdade: tudo vira sinais, como ondas de rádio no Wi-Fi, luz na fibra ou eletricidade no cabo.',
}

export const TERMOS = {
  7: [['Serviço', 'um programa num servidor que fica esperando pedidos, como o serviço de mensagens do app.']],
  6: [['UTF-8', 'uma regra que transforma cada letra em números (bytes). Os dois lados usam a mesma regra.'],
    ['Hexadecimal', 'um jeito curto de escrever esses números, com os algarismos de 0 a 9 e as letras de A a F.']],
  5: [['Sessão', 'o período de uma conversa entre dois programas, do começo ao fim.']],
  4: [['Porta', 'um número que identifica o programa certo dentro de um equipamento.'],
    ['TCP', 'um protocolo que entrega os dados em ordem e reenvia o que se perder.']],
  3: [['Endereço IP', 'o endereço de um equipamento, usado para achar o caminho entre redes. É o assunto da próxima aula.'],
    ['Pacote', 'os dados acompanhados dos endereços IP de origem e de destino.'],
    ['Roteador', 'o equipamento que liga redes diferentes e escolhe por onde o pacote segue.']],
  2: [['Quadro', 'o “envelope” usado dentro da rede local, com o endereço do próximo equipamento.'],
    ['MAC', 'o endereço da placa de rede, que só vale dentro da rede local.'],
    ['Ponto de acesso', 'o aparelho que cria a rede Wi-Fi.']],
  1: [['Bits', 'zeros e uns: a forma mais simples de representar qualquer informação.'],
    ['Sinal', 'a forma física dos bits: onda de rádio, luz ou eletricidade.']],
}
