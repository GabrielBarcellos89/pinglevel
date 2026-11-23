// Conteúdo da aula Transporte: portas, TCP e UDP (abre o Módulo 3). Base: Redes para Iniciantes p. 82–84 (portas, a
// analogia do prédio e dos apartamentos, faixas de portas), p. 86–87 (Three-Way Handshake, ordem, retransmissão e FIN),
// p. 89–91 (comparativo TCP x UDP, melhor esforço, DNS na porta 53). Tudo o que as perguntas pedem é explicado antes na
// própria etapa: a aula não depende do livro, do Teste de carga (fora da trilha) nem de labs que vêm depois.

export const PERGUNTAS_PORTAS = [
  { id: 'papel', pergunta: 'O IP leva o pacote até o computador. O que a porta indica?',
    opcoes: [['rede', 'A rede do computador'], ['aplicacao', 'A aplicação (o serviço) que vai receber os dados'], ['placa', 'A placa de rede']],
    correta: 'aplicacao', certo: 'O IP é o prédio; a porta é o número do apartamento.' },
  { id: 'faixa', pergunta: 'Os números de porta vão de 0 a 65535. Em que faixa ficam as portas conhecidas, dos serviços padronizados?',
    opcoes: [['baixa', '0 a 1023'], ['media', '1024 a 49151'], ['alta', '49152 a 65535']],
    correta: 'baixa', certo: 'As portas de 49152 a 65535 são as dinâmicas, que o sistema empresta à aplicação cliente.' },
  { id: 'web', pergunta: 'Um navegador pede uma página a um servidor web. Para qual porta vai o pedido, se nada foi mudado?',
    opcoes: [['22', '22'], ['53', '53'], ['80', '80']],
    correta: '80', certo: 'Porta 80, a padrão do HTTP; um administrador pode configurar outra, como a 8080.' },
]

// A ordem do Three-Way Handshake: o aluno escolhe o pacote de cada passo.
export const PASSOS_TCP = [
  { id: 'p1', pergunta: '1º pacote: o cliente pede para abrir a conexão.', opcoes: [['syn', 'SYN'], ['synack', 'SYN-ACK'], ['ack', 'ACK']],
    correta: 'syn', certo: 'SYN (synchronize): leva o número de sequência inicial do cliente.' },
  { id: 'p2', pergunta: '2º pacote: o servidor, com a porta aberta, aceita.', opcoes: [['syn', 'SYN'], ['synack', 'SYN-ACK'], ['ack', 'ACK']],
    correta: 'synack', certo: 'SYN-ACK: a sequência do servidor e a confirmação do SYN do cliente.' },
  { id: 'p3', pergunta: '3º pacote: o cliente confirma, e a conexão está aberta.', opcoes: [['syn', 'SYN'], ['synack', 'SYN-ACK'], ['ack', 'ACK']],
    correta: 'ack', certo: 'ACK: a partir daqui os dados trafegam, em ordem e com retransmissão do que se perder.' },
  { id: 'fim', pergunta: 'Terminada a comunicação, como a conexão TCP é encerrada de forma ordenada?',
    opcoes: [['fin', 'Com FIN e ACK dos dois lados'], ['nada', 'Não precisa: ela some sozinha'], ['syn', 'Com outro SYN']],
    correta: 'fin', certo: 'FIN, ACK, FIN, ACK: os dois lados concordam em fechar e liberam os recursos.' },
]

export const PERGUNTAS_UDP = [
  { id: 'conexao', pergunta: 'Antes de mandar dados, o UDP faz um handshake como o TCP?',
    opcoes: [['sim', 'Sim, SYN, SYN-ACK e ACK'], ['nao', 'Não: envia os datagramas direto, sem conexão']],
    correta: 'nao', certo: 'UDP é melhor esforço: sem conexão, sem garantia de entrega e sem reenvio.' },
  { id: 'dns', pergunta: 'Uma consulta DNS (perguntar o endereço de um nome) normalmente usa:',
    opcoes: [['tcp', 'TCP, porta 80'], ['udp', 'UDP, porta 53'], ['tcp22', 'TCP, porta 22']],
    correta: 'udp', certo: 'DNS na porta 53 com UDP: muitas máquinas consultam o mesmo servidor nessa porta.' },
  { id: 'escolha', pergunta: 'Qual destes usos precisa do TCP, porque não pode perder nem embaralhar dados?',
    opcoes: [['voip', 'Voz por IP (VoIP)'], ['arquivo', 'Transferência de arquivos'], ['jogo', 'Jogos online']],
    correta: 'arquivo', certo: 'Web, e-mail e arquivos usam TCP; streaming, jogos, VoIP e DNS preferem a velocidade do UDP.' },
]

// Uma captura como as dos Bastidores da rede: um PC abre a página de um servidor web e depois pergunta um nome ao DNS.
export const CAPTURA = [
  ['1', 'TCP', '192.168.1.10:51514 → 192.168.1.80:80', '[SYN]'],
  ['2', 'TCP', '192.168.1.80:80 → 192.168.1.10:51514', '[SYN, ACK]'],
  ['3', 'TCP', '192.168.1.10:51514 → 192.168.1.80:80', '[ACK]'],
  ['4', 'HTTP', '192.168.1.10:51514 → 192.168.1.80:80', 'GET /'],
  ['5', 'UDP', '192.168.1.10:40112 → 192.168.1.53:53', 'DNS consulta intranet.empresa.local'],
  ['6', 'UDP', '192.168.1.53:53 → 192.168.1.10:40112', 'DNS resposta 192.168.1.80'],
]

export const PERGUNTAS_CAPTURA = [
  { id: 'handshake', pergunta: 'Quais linhas são o Three-Way Handshake?', opcoes: [['123', '1, 2 e 3'], ['456', '4, 5 e 6'], ['56', 'Só 5 e 6']],
    correta: '123', certo: 'SYN, SYN-ACK e ACK abrem a conexão; só depois vem o pedido HTTP (linha 4).' },
  { id: 'servico', pergunta: 'Na linha 1, qual número diz que o pedido é para o servidor web?',
    opcoes: [['51514', '51514'], ['80', '80'], ['50', 'O .50 do endereço']],
    correta: '80', certo: 'A porta de destino 80 é o serviço; a 51514 é a porta dinâmica do cliente, para onde volta a resposta.' },
  { id: 'dns', pergunta: 'Por que a consulta DNS (linhas 5 e 6) não tem handshake antes?',
    opcoes: [['erro', 'A captura perdeu os pacotes'], ['udp', 'É UDP: pergunta e resposta, sem conexão'], ['dns', 'O DNS não usa porta']],
    correta: 'udp', certo: 'UDP manda o datagrama direto; se a resposta não vier, a aplicação pergunta de novo.' },
]
