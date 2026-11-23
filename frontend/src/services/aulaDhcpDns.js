// Conteúdo da aula DHCP e DNS. Base: Redes para Iniciantes p. 36, 63, 77–78 e 91; Linux: Utilitários de Redes p. 17–18
// (dig e nslookup) e p. 24 (dhclient). Cenário: rede 192.168.40.0/24, roteador .1, servidor de serviços .2 (DHCP e DNS
// da zona empresa.local), concessões de .100 a .150 (o mesmo do Lab 8).

export const PROBLEMAS = [
  { id: 'repetido', pergunta: 'Dois computadores com o mesmo endereço IP.', opcoes: [['evita', 'O DHCP evita'], ['nao', 'O DHCP não evita']],
    correta: 'evita', certo: 'O servidor controla quais endereços já foram emprestados.' },
  { id: 'gateway', pergunta: 'Gateway digitado errado num computador.', opcoes: [['evita', 'O DHCP evita'], ['nao', 'O DHCP não evita']],
    correta: 'evita', certo: 'O gateway vem na concessão, igual para todos.' },
  { id: 'cabo', pergunta: 'Cabo de rede desconectado.', opcoes: [['evita', 'O DHCP evita'], ['nao', 'O DHCP não evita']],
    correta: 'nao', certo: 'Sem enlace, o pedido nem chega ao servidor.' },
  { id: 'dns', pergunta: 'Computador sem servidor DNS configurado.', opcoes: [['evita', 'O DHCP evita'], ['nao', 'O DHCP não evita']],
    correta: 'evita', certo: 'Os servidores DNS também vêm na concessão.' },
]

export const DORA = [
  { id: 'ordem', pergunta: 'Qual é a ordem das mensagens?',
    opcoes: [['a', 'Pedido, oferta, descoberta, confirmação'], ['b', 'Descoberta, oferta, pedido, confirmação'], ['c', 'Oferta, descoberta, confirmação, pedido']],
    correta: 'b', certo: 'Descoberta (Discover), Oferta (Offer), Pedido (Request) e Confirmação (Ack): DORA.' },
  { id: 'destino', pergunta: 'A descoberta vai para quem?', opcoes: [['servidor', 'Para o IP do servidor DHCP'], ['broadcast', 'Para todos (broadcast)'], ['gateway', 'Para o gateway']],
    correta: 'broadcast', certo: 'O cliente ainda não sabe quem é o servidor: pergunta a todos.' },
  { id: 'origem', pergunta: 'Que endereço IP de origem o cliente usa antes de receber o seu?', opcoes: [['zero', '0.0.0.0'], ['apipa', '169.254.0.1'], ['gateway', 'O do gateway']],
    correta: 'zero', certo: '0.0.0.0 indica que ele ainda não tem endereço.' },
  { id: 'udp', pergunta: 'Por que o DHCP usa UDP, e não TCP?', opcoes: [['rapido', 'Só porque é mais rápido'], ['conexao', 'Sem endereço não há conexão TCP; e o pedido vai em broadcast'], ['seguro', 'Porque é mais seguro']],
    correta: 'conexao', certo: 'TCP precisa de conexão entre dois endereços; o DHCP trabalha em broadcast.' },
]

// Explicação das quatro mensagens, antes das perguntas (validação de 22/11/2026: explicar antes de perguntar).
export const MENSAGENS_DORA = [
  ['Descoberta (Discover)', 'do cliente para todos (broadcast)', '“Tem algum servidor DHCP aí? Preciso de um endereço.”'],
  ['Oferta (Offer)', 'do servidor para o cliente', '“Posso te emprestar o 192.168.40.117.”'],
  ['Pedido (Request)', 'do cliente para todos (broadcast)', '“Quero o 192.168.40.117, oferecido pelo servidor 192.168.40.2.” Em broadcast, para outros servidores saberem que a oferta deles não foi aceita.'],
  ['Confirmação (Ack)', 'do servidor para o cliente', '“Confirmado: o .117 é seu por uma hora, com esta máscara, este gateway e este DNS.”'],
]

export const LINHAS_CONCESSAO = [
  ['broadcasting discover', 'a descoberta, enviada para todos'],
  ['broadcasting select for 192.168.40.117, server 192.168.40.2', 'o pedido: o cliente escolheu a oferta do .117, feita pelo servidor .2'],
  ['lease of 192.168.40.117 obtained from 192.168.40.2, lease time 3600', 'a confirmação: o endereço .117 foi emprestado pelo servidor .2, por 3600 segundos'],
  ['deleting routers', 'o cliente apaga a rota padrão antiga e grava o gateway recebido (essa parte não imprime outra linha)'],
  ['adding dns 192.168.40.2', 'o servidor DNS recebido na concessão'],
]

// Saída real de um pedido nos nós do laboratório: o dhclient é atendido pelo udhcpc (cliente DHCP do BusyBox).
export const CONCESSAO = `udhcpc: started, v1.36.1
udhcpc: broadcasting discover
udhcpc: broadcasting select for 192.168.40.117, server 192.168.40.2
udhcpc: lease of 192.168.40.117 obtained from 192.168.40.2, lease time 3600
deleting routers
adding dns 192.168.40.2
`
export const LEITURA_CONCESSAO = [
  { id: 'endereco', pergunta: 'Que endereço este computador recebeu?', opcoes: [['117', '192.168.40.117'], ['2', '192.168.40.2'], ['1', '192.168.40.1']],
    correta: '117', certo: 'O .2 é o servidor que emprestou; o .117 é a concessão.' },
  { id: 'tempo', pergunta: 'O que significa "lease time 3600"?', opcoes: [['sempre', 'O endereço é dele para sempre'], ['hora', 'O empréstimo vale 3600 s (uma hora) e precisa ser renovado'], ['tentativas', 'Ele tentou 3600 vezes']],
    correta: 'hora', certo: 'É um empréstimo (concessão): o cliente renova antes de vencer.' },
  { id: 'dns', pergunta: 'Para onde vai o "adding dns 192.168.40.2"?', opcoes: [['rota', 'Para a tabela de rotas'], ['resolv', 'Para o /etc/resolv.conf (nameserver)'], ['arp', 'Para a tabela ARP']],
    correta: 'resolv', certo: 'É o servidor que o computador vai consultar para traduzir nomes.' },
  { id: 'apipa', pergunta: 'Um colega aparece com 169.254.20.7. O que isso indica?', opcoes: [['ok', 'Que o DHCP funcionou'], ['sem', 'Que não conseguiu endereço de um servidor DHCP'], ['dns', 'Que o DNS está errado']],
    correta: 'sem', certo: '169.254.0.0/16 é usado quando nenhum servidor DHCP responde.' },
]

export const CASOS_DNS = [
  { id: 'nx', saida: 'pc$ nslookup intrnet.empresa.local\n** server can\'t find intrnet.empresa.local: NXDOMAIN',
    pergunta: 'O que aconteceu?', opcoes: [['nome', 'O nome não existe no DNS (veja a grafia)'], ['servidor', 'O servidor DNS não responde'], ['rede', 'A rede está fora']],
    correta: 'nome', certo: 'NXDOMAIN: o servidor respondeu que esse nome não existe. Aqui, faltou um "a".' },
  { id: 'timeout', saida: 'pc$ nslookup intranet.empresa.local\n;; connection timed out; no servers could be reached\npc$ cat /etc/resolv.conf\nnameserver 192.168.40.9\npc$ ping 192.168.40.20\n2 packets transmitted, 2 received, 0% packet loss',
    pergunta: 'O que aconteceu?', opcoes: [['nome', 'O nome não existe'], ['servidor', 'O computador consulta um servidor DNS errado'], ['rede', 'A rede está fora']],
    correta: 'servidor', certo: 'A rede funciona (o ping pelo IP responde), mas o nameserver .9 não é o servidor DNS.' },
  { id: 'rede', saida: 'pc$ nslookup intranet.empresa.local\n;; connection timed out; no servers could be reached\npc$ ping 192.168.40.2\nping: connect: Network unreachable',
    pergunta: 'O que aconteceu?', opcoes: [['nome', 'O nome não existe'], ['servidor', 'Só o DNS está errado'], ['rede', 'O problema é antes: o computador nem alcança a rede']],
    correta: 'rede', certo: 'Se nem o IP responde, o DNS não tem como funcionar: comece pelo endereço e pela rota.' },
]

export const OBJETIVOS = [
  // O comando ensinado é o dhclient (livro e faculdade). O udhcpc, que faz o pedido nos nós do laboratório, também vale.
  { id: 'pedir', texto: 'Pedir um endereço por DHCP na eth0.', padrao: /^(dhclient\s+(-v\s+)?eth0|udhcpc\s+(-i\s+eth0|--interface=?\s*eth0))$/,
    modelo: 'dhclient <interface>',
    ajuda: { partes: [['dhclient', 'o cliente DHCP: pede endereço, gateway e DNS ao servidor'], ['<interface>', 'em qual placa de rede pedir']],
      exemplo: { comando: 'dhclient eth1' }, observacao: 'Esse pede pela eth1. Troque pela interface do objetivo.', pista: 'dhclient ____' } },
  { id: 'resolv', texto: 'Ver qual servidor DNS o computador está usando.', padrao: /^cat\s+\/etc\/resolv\.conf$/,
    modelo: 'cat /etc/resolv.conf',
    ajuda: { partes: [['cat', 'mostra o conteúdo de um arquivo'], ['/etc/resolv.conf', 'o arquivo com os servidores DNS (nameserver)']],
      exemplo: { comando: 'cat /etc/hosts' }, observacao: 'Esse mostra outro arquivo da pasta /etc. O dos servidores DNS é o resolv.conf.', pista: 'cat /etc/________' } },
  { id: 'consultar', texto: 'Perguntar ao DNS o endereço de intranet.empresa.local.', padrao: /^(nslookup\s+intranet\.empresa\.local|dig\s+intranet\.empresa\.local(\s+\+short)?)$/,
    modelo: 'nslookup <nome>',
    ajuda: { partes: [['nslookup', 'consulta o servidor DNS'], ['<nome>', 'o nome que você quer traduzir']],
      exemplo: { comando: 'nslookup www.exemplo.com' }, observacao: 'Troque o nome pelo do objetivo.', pista: 'nslookup ________.empresa.local' } },
  { id: 'ping', texto: 'Testar a comunicação com a intranet pelo nome.', padrao: /^ping(\s+-c\s+\d+)?\s+intranet\.empresa\.local$/,
    modelo: 'ping <nome>',
    ajuda: { partes: [['ping', 'testa a comunicação'], ['<nome>', 'o ping também aceita nomes: ele consulta o DNS antes']],
      exemplo: { comando: 'ping www.exemplo.com' }, observacao: 'Troque o nome pelo do objetivo.', pista: 'ping ________.empresa.local' } },
]

export function conferirComandoServicos(objetivo, texto) {
  const normal = String(texto || '').trim().replace(/^\$\s*/, '').replace(/\s+/g, ' ')
  if (!normal) return { ok: false, retorno: '' }
  if (objetivo.padrao.test(normal)) return { ok: true, retorno: 'Comando correto.' }
  if (objetivo.id === 'pedir' && /^dhclient$/.test(normal)) return { ok: false, retorno: 'Indique a interface: dhclient eth0.' }
  if (objetivo.id === 'pedir' && /^udhcpc\s+eth0$/.test(normal)) return { ok: false, retorno: 'A interface vem depois de -i.' }
  if (/\bintranet\.empresa\b(?!\.local)/.test(normal)) return { ok: false, retorno: 'Use o nome completo: intranet.empresa.local.' }
  return { ok: false, retorno: `Confira a forma: ${objetivo.modelo}` }
}
