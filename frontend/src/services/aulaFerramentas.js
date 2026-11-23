// Conteúdo da aula Ferramentas: interfaces, rotas e testes. Base: Linux: Utilitários de Redes p. 13 e 19;
// Redes para Iniciantes p. 154–155. As saídas seguem o formato real do iproute2 e do ping.

export const SAIDA_INTERFACE = [
  { trecho: '2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>', id: 'estado',
    explicacao: 'Nome da interface (eth0) e seus estados. UP indica que ela está ativa; LOWER_UP, que há enlace físico (o "cabo" está conectado).' },
  { trecho: '    link/ether 9e:06:b5:d7:36:0d', id: 'mac',
    explicacao: 'Endereço MAC da interface, usado na entrega dentro da rede local.' },
  { trecho: '    inet 192.168.10.30/24', id: 'inet',
    explicacao: 'Endereço IPv4 configurado e o prefixo. Sem uma linha inet, a interface não participa da rede IPv4.' },
  { trecho: ' brd 192.168.10.255 scope global eth0', id: 'brd',
    explicacao: 'Endereço de broadcast da rede, calculado a partir do endereço e do prefixo.' },
]

export const SITUACOES_INTERFACE = [
  { id: 'sem-ip', saida: '2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>\n    link/ether 9e:06:b5:d7:36:0d', correta: 'ativa-sem-ip' },
  { id: 'ok', saida: '2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>\n    link/ether 9e:06:b5:d7:36:0d\n    inet 192.168.10.30/24 brd 192.168.10.255 scope global eth0', correta: 'configurada' },
  { id: 'down', saida: '2: eth0: <BROADCAST,MULTICAST>\n    link/ether 9e:06:b5:d7:36:0d\n    inet 192.168.10.30/24 brd 192.168.10.255 scope global eth0', correta: 'desativada' },
]
export const OPCOES_INTERFACE = [
  ['configurada', 'Ativa e com endereço IPv4'],
  ['ativa-sem-ip', 'Ativa, mas sem endereço IPv4'],
  ['desativada', 'Com endereço, mas desativada (sem UP)'],
]

export const TABELA = [
  { linha: 'default via 192.168.10.1 dev eth0', id: 'padrao',
    explicacao: 'Rota padrão: o caminho de último recurso. Todo destino que não está em outra linha vai para o gateway 192.168.10.1.' },
  { linha: '192.168.10.0/24 dev eth0 proto kernel scope link src 192.168.10.30', id: 'local',
    explicacao: 'Rota da própria rede, criada sozinha quando o endereço foi configurado: destinos de 192.168.10.0/24 são entregues direto pela eth0.' },
]
export const DESTINOS_TABELA = [
  { ip: '192.168.10.20', correta: 'local' },
  { ip: '192.168.20.10', correta: 'padrao' },
  { ip: '8.8.8.8', correta: 'padrao' },
  { ip: '192.168.10.1', correta: 'local' },
]

// Objetivos para montar o comando; a conferência aceita as variações que o terminal do Lab 4 aceita.
export const OBJETIVOS = [
  { id: 'add-endereco', texto: 'Configurar o endereço 192.168.10.30 com prefixo /24 na interface eth0.',
    padrao: /^ip\s+addr(ess)?\s+add\s+192\.168\.10\.30\/24\s+dev\s+eth0$/, modelo: 'ip addr add <endereço>/<prefixo> dev <interface>',
    ajuda: { partes: [['ip addr add', 'adiciona um endereço IPv4'], ['<endereço>/<prefixo>', 'o endereço e o prefixo, juntos, com a barra'], ['dev <interface>', 'em qual interface (device)']],
      pagina: 12, exemplo: { rotulo: 'Exemplo 2.24', comando: 'ip addr add 192.168.1.2/24 dev eth0' }, pista: 'ip addr add 192.168.10.30/__ dev eth0' } },
  { id: 'add-rota', texto: 'Criar a rota padrão usando o gateway 192.168.10.1.',
    padrao: /^ip\s+r(oute)?\s+add\s+default\s+via\s+192\.168\.10\.1(\s+dev\s+eth0)?$/, modelo: 'ip route add default via <gateway>',
    ajuda: { partes: [['ip route add', 'adiciona uma rota'], ['default', 'a rota padrão: vale para qualquer destino sem outra rota'], ['via <gateway>', 'para quem entregar: o gateway']],
      pagina: 13, exemplo: { rotulo: 'Exemplo 2.33', comando: 'ip route add default via 192.168.1.254' }, pista: 'ip route add _______ via 192.168.10.1' } },
  { id: 'del-rota', texto: 'Remover a rota padrão atual.',
    padrao: /^ip\s+r(oute)?\s+del\s+default(\s+via\s+\S+)?$/, modelo: 'ip route del default',
    ajuda: { partes: [['ip route del', 'remove (delete) uma rota'], ['default', 'qual rota: a rota padrão']],
      pagina: 13, exemplo: { rotulo: 'Exemplo 2.34', comando: 'ip route del default via 192.168.1.254' }, pista: 'ip route ___ default' } },
  { id: 'del-endereco', texto: 'Remover o endereço 192.168.10.30/24 da eth0.',
    padrao: /^ip\s+addr(ess)?\s+del\s+192\.168\.10\.30\/24\s+dev\s+eth0$/, modelo: 'ip addr del <endereço>/<prefixo> dev <interface>',
    ajuda: { partes: [['ip addr del', 'remove um endereço IPv4'], ['<endereço>/<prefixo>', 'o mesmo endereço e prefixo que estão na interface'], ['dev <interface>', 'de qual interface']],
      pagina: 12, exemplo: { rotulo: 'Exemplo 2.25', comando: 'ip addr del 192.168.1.5/24 dev eth0' }, pista: 'ip addr del 192.168.10.30/24 dev ____' } },
]

export function conferirComando(objetivo, texto) {
  const normal = String(texto || '').trim().replace(/^\$\s*/, '').replace(/\s+/g, ' ')
  if (!normal) return { ok: false, retorno: '' }
  if (objetivo.padrao.test(normal)) return { ok: true, retorno: 'Comando correto.' }
  if (!normal.startsWith('ip ')) return { ok: false, retorno: 'Os comandos desta aula começam com ip.' }
  if (/\bdev\s+(?!eth0\b)\S+/.test(normal)) return { ok: false, retorno: 'A interface deste computador é eth0.' }
  return { ok: false, retorno: `Confira a forma: ${objetivo.modelo}` }
}

export const MENSAGENS = [
  { mensagem: 'ping: connect: Network unreachable', correta: 'sem-caminho' },
  { mensagem: '2 packets transmitted, 0 received, 100% packet loss', correta: 'sem-resposta' },
  { mensagem: 'Error: Nexthop has invalid gateway.', correta: 'gateway-fora' },
  { mensagem: 'Error: ipv4: Address already assigned.', correta: 'repetido' },
]
export const CAUSAS_MENSAGEM = [
  ['sem-resposta', 'O pedido saiu, mas nenhuma resposta voltou (destino ou caminho de volta com problema).'],
  ['repetido', 'Esse endereço já está configurado nesta interface.'],
  ['sem-caminho', 'O computador não tem rota para o destino (sem endereço ou sem rota padrão).'],
  ['gateway-fora', 'O gateway informado não está numa rede alcançável diretamente.'],
]
