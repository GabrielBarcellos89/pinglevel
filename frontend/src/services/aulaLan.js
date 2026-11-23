// Conteúdo das aulas Ethernet, MAC e ARP (Módulo 1) e Switch e VLANs (Módulo 3). Base: Redes para Iniciantes p. 36 (broadcast), p. 72 (MAC),
// p. 131 (tabela MAC do switch), p. 157 (ARP), p. 96–99 (VLANs); Linux: Utilitários de Redes p. 12 (ip neigh) e
// p. 38 (bridge). Cenário: quatro PCs num switch, como no Lab 8, mas com outros MACs e portas (a investigação do lab
// não pode estar resolvida aqui).

export const PCS = [
  { nome: 'PC V1', ip: '10.1.1.11', mac: '02:a0:c9:14:6e:01', porta: 'eth2' },
  { nome: 'PC V2', ip: '10.1.1.12', mac: '02:a0:c9:14:6e:02', porta: 'eth0' },
  { nome: 'PC F1', ip: '10.1.1.21', mac: '02:a0:c9:3b:71:03', porta: 'eth3' },
  { nome: 'PC F2', ip: '10.1.1.22', mac: '02:a0:c9:3b:71:04', porta: 'eth1' },
]

export const PERGUNTAS_MAC = [
  { id: 'tamanho', pergunta: 'Quantos bits tem um endereço MAC?', opcoes: [['32', '32 bits, como o IPv4'], ['48', '48 bits (6 bytes)'], ['128', '128 bits']],
    correta: '48', certo: 'São 6 bytes, escritos em hexadecimal: 02:a0:c9:3b:71:04.' },
  { id: 'oui', pergunta: 'Em 02:a0:c9:3b:71:04, o que os três primeiros bytes (02:a0:c9) identificam?',
    opcoes: [['rede', 'A rede IP do computador'], ['fabricante', 'O fabricante da interface (OUI)'], ['porta', 'A porta do switch']],
    correta: 'fabricante', certo: 'É o OUI; os três últimos bytes são o número de série da interface.' },
  { id: 'broadcast', pergunta: 'Qual MAC de destino faz um quadro chegar a todas as interfaces da rede local?',
    opcoes: [['zeros', '00:00:00:00:00:00'], ['ff', 'ff:ff:ff:ff:ff:ff'], ['gateway', 'O MAC do gateway']],
    correta: 'ff', certo: 'É o broadcast: o quadro é entregue a todos da mesma rede local.' },
]

// ARP: o PC F1 quer mandar um ping ao PC F2 (mesma rede) e ainda não conhece o MAC dele.
export const PASSOS_ARP = [
  { id: 'pergunta', pergunta: 'Para quem vai a pergunta "quem tem 10.1.1.22?"', opcoes: [['f2', 'Só para o PC F2'], ['todos', 'Para todos (broadcast)'], ['roteador', 'Para o roteador']],
    correta: 'todos', certo: 'O PC F1 ainda não sabe o MAC do PC F2: pergunta em broadcast.' },
  { id: 'resposta', pergunta: 'Quem responde, e para quem?', opcoes: [['todos', 'Todos respondem para todos'], ['f2', 'Só o PC F2, direto ao PC F1'], ['switch', 'O switch responde por ele']],
    correta: 'f2', certo: 'Só quem tem o endereço responde, com o próprio MAC, direto a quem perguntou.' },
  { id: 'guarda', pergunta: 'Depois disso, onde fica o MAC do PC F2?', opcoes: [['arp', 'Na tabela ARP do PC F1 (ip neigh show)'], ['rota', 'Na tabela de rotas do PC F1'], ['dns', 'No servidor DNS']],
    correta: 'arp', certo: 'Na tabela ARP (vizinhos). Na próxima vez, o PC F1 não precisa perguntar de novo.' },
  { id: 'fora', pergunta: 'Se o destino estivesse em outra rede, o PC F1 perguntaria o MAC de quem?', opcoes: [['destino', 'Do computador de destino'], ['gateway', 'Do gateway (o roteador)'], ['ninguem', 'De ninguém']],
    correta: 'gateway', certo: 'O quadro vai até o roteador; o ARP é sempre dentro da rede local.' },
]

// O switch aprende: tabela começa vazia; em cada quadro, o que ele faz.
export const QUADROS = [
  { id: 'q1', descricao: 'PC V1 (porta eth2) envia um quadro para o MAC do PC F2. A tabela está vazia.',
    opcoes: [['eth1', 'Só para a eth1'], ['todas', 'Para todas as portas, menos a eth2'], ['descarta', 'Descarta']],
    correta: 'todas', certo: 'Destino desconhecido: inundação (flooding). E o switch aprende: o MAC do PC V1 está na eth2.' },
  { id: 'q2', descricao: 'PC F2 (porta eth1) responde para o MAC do PC V1.',
    opcoes: [['eth2', 'Só para a eth2'], ['todas', 'Para todas as portas, menos a eth1'], ['descarta', 'Descarta']],
    correta: 'eth2', certo: 'O MAC do PC V1 já está na tabela (eth2): o quadro vai só para lá. E agora ele aprende o PC F2 na eth1.' },
  { id: 'q3', descricao: 'PC V1 envia de novo para o MAC do PC F2.',
    opcoes: [['eth1', 'Só para a eth1'], ['todas', 'Para todas as portas, menos a eth2'], ['descarta', 'Descarta']],
    correta: 'eth1', certo: 'Agora a tabela tem os dois: encaminhamento só para a porta certa.' },
]

// VLANs: V1 e V2 na VLAN 10, F1 e F2 na VLAN 20, todos em 10.1.1.0/24.
export const PERGUNTAS_VLAN = [
  { id: 'broadcast', pergunta: 'O PC V1 envia um broadcast. Quem recebe?', opcoes: [['todos', 'Os outros três PCs'], ['v2', 'Só o PC V2'], ['ninguem', 'Ninguém']],
    correta: 'v2', certo: 'Cada VLAN é um domínio de broadcast separado: só a VLAN 10 recebe.' },
  { id: 'ip', pergunta: 'PC V1 e PC F1 estão na mesma rede IP. Eles se falam?', opcoes: [['sim', 'Sim, a rede IP é a mesma'], ['nao', 'Não: VLANs diferentes não trocam quadros']],
    correta: 'nao', certo: 'O isolamento é na camada 2. Entre VLANs, só passando por um roteador.' },
  { id: 'acesso', pergunta: 'Uma porta ligada a um PC, que pertence a uma só VLAN e entrega quadros sem marcação, é:',
    opcoes: [['acesso', 'Porta de acesso (PVID, untagged)'], ['tronco', 'Porta tronco (tagged)'], ['roteada', 'Porta roteada']],
    correta: 'acesso', certo: 'Porta de acesso: a PVID diz a VLAN do que entra e o quadro sai sem a marca 802.1Q.' },
  { id: 'tronco', pergunta: 'E a porta que liga dois switches e leva várias VLANs?', opcoes: [['acesso', 'Porta de acesso'], ['tronco', 'Porta tronco: quadros marcados com o número da VLAN']],
    correta: 'tronco', certo: 'No tronco, cada quadro leva a marca 802.1Q (4 bytes) com o número da VLAN.' },
]

const PARTES_VLAN = [['bridge vlan add', 'põe a porta numa VLAN'], ['dev <porta>', 'a porta do switch'], ['vid <número>', 'o número da VLAN'],
  ['pvid untagged', 'porta de acesso: VLAN do que entra e saída sem marca']]

export const OBJETIVOS = [
  { id: 'arp', texto: 'No PC F1: ver a tabela ARP (os vizinhos e seus MACs).', padrao: /^ip\s+n(eigh(bou?r)?)?(\s+show)?(\s+dev\s+eth0)?$/,
    modelo: 'ip neigh show',
    ajuda: { partes: [['ip neigh', 'a tabela de vizinhos (ARP)'], ['show', 'mostrar']], pagina: 12,
      exemplo: { rotulo: 'Exemplo 2.19', comando: 'ip neigh show' }, pista: 'ip ______ show' } },
  { id: 'fdb', texto: 'No switch: ver a tabela MAC (que MAC foi visto em cada porta).', padrao: /^bridge\s+fdb(\s+show)?(\s+br\s+br0)?$/,
    modelo: 'bridge fdb show',
    // Os comandos do switch (bridge) são explicados na própria etapa; os exemplos do livro usam outras ferramentas
    // (brctl, ip link ... type vlan) e confundiam (validação de 17/11/2026), então a ajuda traz exemplos da aula.
    ajuda: { partes: [['bridge', 'comandos do switch (bridge Linux)'], ['fdb', 'a tabela de encaminhamento: MAC → porta'], ['show', 'mostrar']],
      exemplo: { comando: 'bridge link show' }, observacao: 'Esse mostra as portas do switch. A tabela MAC usa a mesma forma.', pista: 'bridge ___ show' } },
  { id: 'vlans', texto: 'No switch: ver em que VLAN está cada porta.', padrao: /^bridge\s+vlan(\s+show)?$/,
    modelo: 'bridge vlan show',
    ajuda: { partes: [['bridge vlan', 'as VLANs de cada porta'], ['show', 'mostrar']],
      exemplo: { comando: 'bridge fdb show' }, observacao: 'Esse mostra a tabela MAC. As VLANs de cada porta usam a mesma forma.', pista: 'bridge ____ show' } },
  { id: 'add', texto: 'No switch: colocar a porta eth2 na VLAN 20 como porta de acesso.', padrao: /^bridge\s+vlan\s+add\s+dev\s+eth2\s+vid\s+20\s+(pvid\s+untagged|untagged\s+pvid)$/,
    modelo: 'bridge vlan add dev <porta> vid <número> pvid untagged',
    ajuda: { partes: PARTES_VLAN, exemplo: { comando: 'bridge vlan add dev eth3 vid 30 pvid untagged' },
      observacao: 'Troque a porta e a VLAN pelas do objetivo.', pista: 'bridge vlan add dev eth2 vid __ pvid untagged' } },
  { id: 'del', texto: 'No switch: tirar a porta eth2 da VLAN 1.', padrao: /^bridge\s+vlan\s+del\s+dev\s+eth2\s+vid\s+1$/,
    modelo: 'bridge vlan del dev <porta> vid <número>',
    ajuda: { partes: [['bridge vlan del', 'tira a porta de uma VLAN'], ['dev <porta>', 'a porta do switch'], ['vid <número>', 'a VLAN que sai']],
      exemplo: { comando: 'bridge vlan del dev eth3 vid 30' }, observacao: 'Troque a porta e a VLAN pelas do objetivo.', pista: 'bridge vlan ___ dev eth2 vid 1' } },
]

// Os comandos do switch, explicados antes de pedir (etapa Montar comandos).
export const COMANDOS_SWITCH = [
  ['bridge fdb show', 'a tabela MAC: que MAC foi visto em cada porta'],
  ['bridge vlan show', 'em que VLAN está cada porta'],
  ['bridge vlan add dev <porta> vid <número> pvid untagged', 'põe a porta numa VLAN como porta de acesso'],
  ['bridge vlan del dev <porta> vid <número>', 'tira a porta de uma VLAN'],
]

export function conferirComandoLan(objetivo, texto) {
  const normal = String(texto || '').trim().replace(/^\$\s*/, '').replace(/\s+/g, ' ')
  if (!normal) return { ok: false, retorno: '' }
  if (objetivo.padrao.test(normal)) return { ok: true, retorno: 'Comando correto.' }
  if (!/^(ip|bridge) /.test(normal)) return { ok: false, retorno: 'Os comandos desta aula começam com ip (nos PCs) ou bridge (no switch).' }
  if (objetivo.id === 'add' && /\bvid\s+20\b/.test(normal) && !/pvid/.test(normal)) {
    return { ok: false, retorno: 'Falta dizer que é porta de acesso: pvid untagged.' }
  }
  if (/\bdev\s+(?!eth2\b)\S+/.test(normal) && ['add', 'del'].includes(objetivo.id)) return { ok: false, retorno: 'O objetivo é a porta eth2.' }
  if (objetivo.id === 'add' && /^bridge vlan add dev eth2 vid \d+ (pvid untagged|untagged pvid)$/.test(normal)) {
    return { ok: false, retorno: 'A forma está certa. Confira o número: em qual VLAN a porta deve entrar?' }
  }
  if (objetivo.id === 'del' && /^bridge vlan del dev eth2 vid \d+$/.test(normal)) {
    return { ok: false, retorno: 'A forma está certa. Confira o número: de qual VLAN a porta sai?' }
  }
  return { ok: false, retorno: `Confira a forma: ${objetivo.modelo}` }
}
