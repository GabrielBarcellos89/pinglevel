// Labs 5 e 6 (setores ligados a um roteador): textos, abas e a orientação "Agora faça" de cada etapa.
// A orientação deriva do estado confirmado pelo servidor e não concede etapas; a ajuda diminui ao longo do lab.

function instrucaoBase(s, total) {
  const indice = s.indice + 1
  const instrucao = (titulo, texto, alvo, etiqueta = `ETAPA ${indice} DE ${total}`, pistas) => ({ titulo, texto, alvo, etiqueta, pistas, ocupado: s.ocupado })
  if (s.recuperacao || s.expirado) return [instrucao('Confira o estado do ambiente', 'Use Atualizar estado para continuar com segurança.', 'atualizar', 'AMBIENTE')]
  if (s.preparacaoPendente) return [instrucao('Encerre o ambiente incompleto', 'A preparação não foi confirmada. Encerre este ambiente antes de tentar novamente.', 'encerrar', 'AMBIENTE')]
  if (s.conflito) return [instrucao('Outra missão está em uso', 'Volte aos laboratórios para abrir o que já está ativo.', 'catalogo', 'AMBIENTE')]
  if (s.registrada) return [s.pendente
    ? instrucao('Conclusão salva; falta encerrar o ambiente', 'Use Tentar limpeza novamente para confirmar a remoção.', 'limpar', 'CONCLUSÃO')
    : instrucao('Missão concluída', 'Seu progresso está salvo. Você pode voltar aos laboratórios ou iniciar um novo treino.', 'catalogo', 'CONCLUSÃO')]
  if (!s.ativo) return [instrucao('Inicie o ambiente', 'Clique em Iniciar ambiente.', 'iniciar', 'PREPARAÇÃO')]
  if (s.etapa === 'comprovar') return [instrucao('Conclua a missão', 'Tudo configurado. Clique em Validar missão, ao lado do tempo: o servidor relê os equipamentos e repete os testes.', 'concluir', 'COMPROVAR')]
  return [null, instrucao]
}

// "Onde" e "Pronto quando" de cada etapa: completam o "Agora faça" sem entregar valores. Só entram nas orientações
// de etapa (não nas de ambiente, preparação ou conclusão).
const COMPROVAR = ['Botão Validar missão, ao lado do tempo.', 'O servidor confirma a missão e mostra o XP.']
export function comGuia(config, orientacao, etapa) {
  if (!orientacao || !/^(ETAPA|CHAMADO|COMPROVAR)/.test(orientacao.etiqueta || '')) return orientacao
  const [onde, pronto] = (etapa === 'comprovar' ? config.guia?.comprovar || COMPROVAR : config.guia?.[etapa]) || []
  return { ...orientacao, onde, pronto }
}

const COMANDOS_SWITCH = 'bridge link show, bridge fdb show e bridge vlan show (ler); bridge vlan add e bridge vlan del (mudar)'

function naAba(s, instrucao, nos, nome, texto) {
  if (!nos.includes(s.abaAtual)) return instrucao(`Abra a aba ${nome}`, texto, `aba-${nos[0]}`)
  return null
}

// Lab 2 (versão 2, 30/10/2026): uma sala com switch e três PCs, sem roteador. Descobrir a rede, colocar o PC 2 nela
// e atender o chamado do PC 3 (prefixo errado). A ajuda é a mais detalhada da trilha: é o primeiro lab de terminal.
export const LAB2 = {
  id: 'primeira-lan', base: '/api/lab2', numero: 2, etiqueta: 'LABORATÓRIO 2 · MONTE SUA PRIMEIRA LAN',
  titulo: 'Monte sua primeira LAN', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'Uma sala, um switch e três computadores',
    texto: 'A sala de estudos tem um switch e três computadores. O PC 1 já funciona. O PC 2 acabou de chegar, sem endereço, e o PC 3 abriu um chamado. Descubra a rede do PC 1, coloque o PC 2 na mesma rede e resolva o chamado, tudo pelo terminal.',
    fila: [['Planejamento da sala', 'a rede do PC 1: endereço da rede, prefixo e máscara'], ['PC 2', 'um endereço livre da mesma rede'], ['Chamado', '“O PC 3 não fala com o PC 1.”']],
  },
  guia: {
    plano: ['Aba PC 1 para consultar; respostas no painel Planejamento da sala, à direita.', 'O planejamento fica verde: conferido pelo servidor.'],
    pc2: ['Aba PC 2 · interface eth0.', 'O PC 2 tem um endereço da rede da sala e o ping até o PC 1 responde.'],
    chamado: ['Aba PC 3; a causa você escolhe no painel do chamado.', 'Causa confirmada e o ping do PC 3 até o PC 1 responde.'],
  },
  abas: ['pc1', 'pc2', 'pc3'],
  roteadores: [],
  semGateway: true,
  descobrirEnderecos: true,
  titulosEtapas: { plano: 'Planejamento da sala' },
  rotuloPc: () => '',
  plano: { etiqueta: 'PLANEJAMENTO DA REDE DA SALA', coluna: 'Rede', botao: 'Conferir o planejamento',
    descricao: 'Antes de configurar qualquer PC, registre o planejamento da rede da sala, a partir do PC 1, que já funciona: o endereço da rede, o prefixo e a máscara. Todos os PCs da sala precisam estar nessa rede. É com ela que você vai escolher o endereço do PC 2 e conferir o PC 3.' },
  modeloPlano: null,
  comandos: () => 'ip addr (ver, adicionar e remover endereços) e ping · se travar, peça uma pista no Agora faça',
  textoComprovar: 'O servidor vai reler os três PCs (todos na rede da sala, sem endereço repetido) e repetir os pings até o PC 1.',
  passosChamado: () => ['Investigar o PC 3 pelo terminal', 'Confirmar a causa no chamado', 'Corrigir o endereço do PC 3', 'Comprovar: ping do PC 3 ao PC 1'],
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 4)
    if (pronta) return pronta
    if (s.etapa === 'plano') {
      if (!s.historico?.some((h) => h.pc === 'pc1' && h.tipo === 'ver-enderecos')) return naAba(s, instrucao, ['pc1'], 'PC 1', 'Comece pelo PC 1: ele já funciona.')
        || instrucao('Descubra o endereço do PC 1', 'Digite no terminal do PC 1 o comando que mostra os endereços das interfaces, o mesmo do Lab 1.', 'comando', undefined,
          ['É o comando ip, que mostra e altera as interfaces de rede, seguido do que você quer ver: os endereços (addr).', 'ip addr show'])
      return instrucao('Planeje a rede da sala', 'Na saída, a linha inet mostra o endereço do PC 1 e, depois da barra, o prefixo. Com eles, preencha o planejamento da sala: o endereço da rede (o primeiro da faixa, que nenhum PC usa), o prefixo e a máscara. Depois clique em Conferir o planejamento.', 'plano', undefined,
        ['O prefixo diz quantos bits são da rede. Com /24, os três primeiros números são a rede e o último é o host.', 'Endereço da rede: a parte do host vira zero. Máscara: cada grupo de 8 bits de rede vira 255, o resto vira 0.'])
    }
    if (s.etapa === 'pc2') return naAba(s, instrucao, ['pc2'], 'PC 2', 'O PC 2 acabou de chegar, sem endereço.')
      || instrucao('Coloque o PC 2 na rede', 'Dê ao PC 2 um endereço livre da rede da sala, com o mesmo prefixo, e comprove que ele fala com o PC 1.', 'comando', undefined,
        ['Livre quer dizer: nem o endereço da rede, nem o broadcast, nem o de outro PC. Para dar um endereço, use o mesmo comando ip addr, agora com add, dizendo a interface (eth0).',
          'ip addr add <endereço>/<prefixo> dev eth0. Para comprovar: ping <endereço do PC 1>.'])
    if (s.etapa === 'chamado') return naAba(s, instrucao, ['pc3'], 'PC 3', 'O chamado é do PC 3.') || orientarChamado(s, instrucao, {
      investigar: ['Investigue o PC 3', 'Teste se o PC 3 fala com o PC 1 e compare a configuração dos dois.',
        ['Compare o endereço e o número depois da barra do PC 3 com os do PC 1.', 'ping 192.168.10.10 e ip addr show, no PC 3.']],
      corrigir: ['Corrija o PC 3', 'Deixe o PC 3 com o mesmo endereço, mas com o prefixo da sala.',
        ['Primeiro remova o endereço errado, depois adicione o certo: ip addr com del e com add.', 'ip addr del <endereço>/<prefixo errado> dev eth0, depois ip addr add <endereço>/<prefixo da sala> dev eth0.']],
      comprovar: ['Comprove', 'Mostre que agora o PC 3 fala com o PC 1.', ['Use o mesmo teste do começo do chamado.', 'ping 192.168.10.10']],
    })
    return instrucao('Conclua a missão', 'Clique em Validar missão.', 'concluir')
  },
}

export const LAB5 = {
  id: 'dividindo-uma-rede', base: '/api/lab5', numero: 5, etiqueta: 'LABORATÓRIO 5 · DIVIDINDO UMA REDE',
  titulo: 'Dividindo uma rede', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'O Financeiro precisa do seu bloco',
    texto: 'A empresa recebeu 192.168.50.0/24 e o dividiu em quatro blocos /26. O Vendas já usa o 1º bloco e serve de modelo. Coloque o Financeiro no 2º: planeje, configure o roteador e os computadores e comprove. No fim, um chamado espera por você.',
    fila: [['Plano', 'rede, gateway e broadcast do 2º bloco'], ['Roteador', 'a interface eth1 com o gateway do Financeiro'],
      ['Financeiro', 'PC F1 e PC F2 no bloco, com rota padrão'], ['Chamado', '“O PC V2 não fala com ninguém.”']],
  },
  guia: {
    plano: ['Painel Plano, à direita.', 'O plano fica verde: conferido pelo servidor.'],
    roteador: ['Aba Roteador · interface eth1 (não nos PCs).', 'A eth1 aparece com o gateway do Financeiro no roteador da topologia.'],
    financeiro: ['Abas PC F1 e PC F2 · interface eth0.', 'Os dois PCs com endereço do bloco e rota padrão, e o ping até o PC V1 responde.'],
    chamado: ['Aba PC V2; a causa você escolhe no painel do chamado.', 'Causa confirmada e o PC V2 alcança um PC do Financeiro.'],
  },
  abas: ['v1', 'v2', 'roteador', 'f1', 'f2'],
  modeloPlano: { grupo: 'vendas', valores: { rede: '192.168.50.0', gateway: '192.168.50.1', broadcast: '192.168.50.63' } },
  // Explica a divisão sem entregar o bloco: a régua mostra o /24 em quatro partes de 64, só a do Vendas preenchida.
  plano: {
    descricao: 'A empresa tem uma só rede, 192.168.50.0/24 (256 endereços), dividida em quatro blocos /26 de 64 endereços. '
      + 'Os três primeiros números (192.168.50) são os mesmos em todos os blocos; só o último muda. Cada bloco começa logo '
      + 'depois do fim do anterior.',
    regua: { base: '192.168.50', tamanho: 64, blocos: [['Vendas', 'usa .0 a .63'], ['Financeiro', 'você planeja'], ['livre', ''], ['livre', '']] },
  },
  dicaPlano(campo, valor) {
    if (!String(valor).trim().startsWith('192.168.50.')) return 'O Financeiro fica dentro da rede da empresa: comece com 192.168.50. e mude só o último número.'
    return { rede: 'A rede do 2º bloco é o primeiro endereço depois do fim do Vendas (.63).',
      gateway: 'O gateway é o primeiro host: o endereço logo depois da rede do bloco.',
      broadcast: 'O broadcast é o último endereço do bloco: são 64 endereços, então some 63 à rede do bloco.' }[campo]
  },
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 5)
    if (pronta) return pronta
    if (s.etapa === 'plano') return instrucao('Planeje o bloco do Financeiro', 'A rede 192.168.50.0/24 foi dividida em quatro blocos /26 de 64 endereços. O Vendas usa o 1º (.0 a .63). Escreva a rede, o gateway (1º host) e o broadcast do 2º bloco, que é do Financeiro, e confira.', 'plano')
    if (s.etapa === 'roteador') return naAba(s, instrucao, ['roteador'], 'Roteador', 'A interface eth1 do roteador fica no switch do Financeiro.')
      || instrucao('Configure o roteador', 'Dê à eth1 o gateway do Financeiro, com o prefixo do plano: ip addr add <endereço>/<prefixo> dev eth1. Confira com ip route.', 'comando')
    if (s.etapa === 'financeiro') return naAba(s, instrucao, ['f1', 'f2'], 'PC F1', 'Os PCs F1 e F2 estão no switch do Financeiro.')
      || instrucao('Configure o Financeiro', 'Em cada PC: um endereço livre do bloco e a rota padrão pelo gateway. Comprove com ping entre F1 e F2 e até o PC V1 (192.168.50.10).', 'comando')
    if (!s.causaIdentificada) {
      if (s.observou) return instrucao('Qual é a causa?', 'Com base no que o terminal mostrou, escolha no chamado a causa do problema do PC V2.', 'causa')
      return naAba(s, instrucao, ['v2'], 'PC V2', 'O chamado é do PC V2.') || instrucao('Investigue o PC V2', 'Não fala com ninguém, nem com o PC V1 ao lado. Investigue pelo terminal.', 'comando')
    }
    return naAba(s, instrucao, ['v2'], 'PC V2', 'A correção é no PC V2.') || instrucao('Corrija o PC V2', 'Corrija a configuração e comprove com ping até um PC do Financeiro.', 'comando')
  },
}

export const LAB6 = {
  id: 'planejando-uma-empresa', base: '/api/lab6', numero: 6, etiqueta: 'LABORATÓRIO 6 · PLANEJANDO UMA EMPRESA',
  titulo: 'Planejando uma empresa', tempo: '20 min (+5 se precisar)',
  missao: {
    titulo: 'Uma empresa, três setores, um /24',
    texto: 'A empresa tem 192.168.80.0/24 para três setores de tamanhos bem diferentes. Monte o plano VLSM e coloque a rede para funcionar: uma interface do roteador por setor e um computador em cada um.',
    fila: [['Atendimento', '100 computadores + gateway'], ['Vendas', '50 computadores + gateway'], ['Financeiro', '20 computadores + gateway']],
  },
  guia: {
    plano: ['Painel Plano VLSM, à direita.', 'O plano fica verde: conferido pelo servidor.'],
    roteador: ['Aba Roteador · interfaces eth0, eth1 e eth2.', 'As três interfaces aparecem no roteador da topologia, cada uma no bloco do seu setor.'],
    pcs: ['Abas PC Atendimento, PC Vendas e PC Financeiro · interface eth0.', 'Cada PC com endereço e rota padrão, e do PC Atendimento o ping aos outros dois responde.'],
  },
  abas: ['atendimento', 'vendas', 'financeiro', 'roteador'],
  modeloPlano: null,
  // O que se espera do plano, sem entregar: as três regras da aula de VLSM e a tabela de tamanhos.
  plano: {
    descricao: 'Para cada setor, escreva o prefixo (o menor bloco cujos hosts úteis cobrem a demanda, já contando o gateway) '
      + 'e a rede (o endereço onde o bloco começa). Distribua do maior setor para o menor: cada bloco começa logo onde o '
      + 'anterior terminou e num múltiplo do seu tamanho. O primeiro começa em 192.168.80.0.',
    prefixos: [25, 26, 27, 28],
  },
  dicaPlano(campo, valor, respostas = {}) {
    const [setor, tipo] = campo.split('-')
    const demanda = { atendimento: 101, vendas: 51, financeiro: 21 }[setor]
    if (tipo === 'prefixo') return `O setor precisa de ${demanda} endereços: escolha o menor prefixo cujos hosts úteis cobrem ${demanda}.`
    if (!String(valor).trim().startsWith('192.168.80.')) return 'O bloco fica dentro da rede da empresa: comece com 192.168.80. e mude só o último número.'
    const tamanho = 2 ** (32 - Number(String(respostas[`${setor}-prefixo`] || '').replace('/', '')))
    const ultimo = Number(String(valor).trim().split('.')[3])
    if (tamanho >= 4 && tamanho <= 256 && ultimo % tamanho !== 0) return `Um bloco de ${tamanho} endereços só começa em múltiplos de ${tamanho}; ${ultimo} não é.`
    return 'Siga a ordem do maior para o menor: este bloco começa logo depois do fim do bloco anterior (rede anterior + tamanho anterior).'
  },
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 4)
    if (pronta) return pronta
    if (s.etapa === 'plano') return instrucao('Monte o plano VLSM', 'Prefixo e rede de cada setor: escolha o prefixo pela demanda, distribua do maior bloco para o menor e alinhe cada um.', 'plano')
    // Depois do plano conferido, um passo por vez: qual equipamento, qual interface e o que ainda falta nele.
    const blocos = SETORES_LAB6.map(([setor, nome, iface]) => ({ setor, nome, iface, ...blocoDoPlano(s.plano, setor) }))
    if (s.etapa === 'roteador') {
      const pendente = blocos.find((b) => (s.estados?.roteador?.interfaces?.[b.iface] || []).join() !== `${b.gateway}/${b.prefixo}`)
      if (!pendente) return instrucao('Confira o roteador', 'As três interfaces estão com o gateway de cada setor. Use Atualizar estado se a etapa não avançar.', 'atualizar')
      const feitas = blocos.filter((b) => b !== pendente && (s.estados?.roteador?.interfaces?.[b.iface] || []).join() === `${b.gateway}/${b.prefixo}`).length
      const { nome, iface, rede, prefixo, gateway } = pendente
      const atual = s.estados?.roteador?.interfaces?.[iface] || []
      const progresso = `Interfaces prontas: ${feitas} de 3.`
      return naAba(s, instrucao, ['roteador'], 'Roteador', 'Agora o roteador: cada interface dele fica no switch de um setor e é o gateway desse setor.')
        || (atual.length
          ? instrucao(`Corrija a ${iface} · ${nome}`, `A ${iface} está com ${atual.join(', ')}, mas o gateway do ${nome} é o 1º host do bloco ${rede}/${prefixo}. Remova o endereço errado e coloque o certo. ${progresso}`, 'comando', undefined,
            ['Para remover: ip addr del, com o endereço e a barra exatamente como aparecem, e a interface.', `ip addr del ${atual[0]} dev ${iface}`])
          : instrucao(`Configure a ${iface} · ${nome}`, `A ${iface} liga o roteador ao switch do ${nome}. Ela recebe o gateway do setor: o 1º host do bloco que você planejou (${rede}/${prefixo}), com o mesmo prefixo. ${progresso}`, 'comando', undefined,
            ['O 1º host é o endereço logo depois da rede do bloco. Use ip addr add com endereço/prefixo e diga a interface (dev).', `ip addr add ${gateway}/${prefixo} dev ${iface}`]))
    }
    for (const b of blocos) {
      const e = s.estados?.[b.setor] || {}
      const enderecos = e.interfaces?.eth0 || []
      const pc = `PC ${b.nome}`
      const aba = () => naAba(s, instrucao, [b.setor], pc, `O roteador está pronto. Agora o ${pc}: endereço e rota padrão.`)
      const regra = `um host livre do bloco ${b.rede}/${b.prefixo} (nem a rede, nem o gateway ${b.gateway}, nem o broadcast ${b.broadcast})`
      if (enderecos.length === 0) return aba() || instrucao(`${pc} · 1/2: endereço`, `Dê ao ${pc} ${regra}, com o prefixo /${b.prefixo}, na eth0.`, 'comando', undefined,
        ['Escolha um número entre o gateway e o broadcast. O comando é o mesmo do roteador, agora na eth0 do PC.', `ip addr add <host do bloco>/${b.prefixo} dev eth0 · por exemplo, ${b.exemplo}/${b.prefixo}`])
      if (enderecos.length > 1 || !hostDoBloco(enderecos[0], b)) return aba() || instrucao(`${pc} · corrija o endereço`, `O ${pc} está com ${enderecos.join(', ')}. Ele precisa de um só endereço: ${regra}, com /${b.prefixo}. Remova o que não serve.`, 'comando', undefined,
        ['Para remover: ip addr del, com o endereço e a barra exatamente como aparecem.', `ip addr del ${enderecos.find((x) => !hostDoBloco(x, b)) || enderecos[1]} dev eth0`])
      if (e.rota_padrao !== b.gateway) return aba() || instrucao(`${pc} · 2/2: rota padrão`, `${e.rota_padrao ? `A rota padrão aponta para ${e.rota_padrao}, que não é o gateway do ${b.nome}. Remova-a e` : 'O endereço está certo. Agora'} diga ao ${pc} que, para sair do setor, ele passa pelo gateway do ${b.nome} (${b.gateway}).`, 'comando', undefined,
        e.rota_padrao ? ['Remova a rota padrão errada e adicione a certa.', `ip route del default e depois ip route add default via ${b.gateway}`]
          : ['A rota padrão é a saída do PC para as outras redes: ip route add default via <gateway>.', `ip route add default via ${b.gateway}`])
    }
    const ip = (setor) => (s.estados?.[setor]?.interfaces?.eth0?.[0] || '').split('/')[0]
    const faltam = ['vendas', 'financeiro'].filter((setor) => s.testes?.atendimento?.[ip(setor)] !== true)
    const alvos = faltam.map((setor) => `PC ${setor === 'vendas' ? 'Vendas' : 'Financeiro'} (${ip(setor)})`).join(' e ')
    return naAba(s, instrucao, ['atendimento'], 'PC Atendimento', 'Os três PCs estão configurados. Falta testar a partir do Atendimento.')
      || instrucao('Teste entre os setores', `Do PC Atendimento, faça ping ao ${alvos}. Se não responder, confira o endereço e a rota padrão do PC de destino.`, 'comando', undefined,
        ['O ping vai do Atendimento, passa pelo roteador e chega ao outro setor.', `ping ${ip(faltam[0])}`])
  },
}

// Lab 6: os blocos vêm do plano já conferido pelo servidor (a resposta do próprio aluno).
const SETORES_LAB6 = [['atendimento', 'Atendimento', 'eth0'], ['vendas', 'Vendas', 'eth1'], ['financeiro', 'Financeiro', 'eth2']]
const paraNumero = (ip) => String(ip).split('.').reduce((n, o) => n * 256 + Number(o), 0)
const paraIp = (n) => [24, 16, 8, 0].map((d) => Math.floor(n / 2 ** d) % 256).join('.')
function blocoDoPlano(plano, setor) {
  const respostas = plano?.respostas || {}
  const rede = String(respostas[`${setor}-rede`] || '').trim()
  const prefixo = Number(String(respostas[`${setor}-prefixo`] || '').replace('/', '').trim())
  const inicio = paraNumero(rede)
  const tamanho = 2 ** (32 - prefixo)
  return { rede, prefixo, gateway: paraIp(inicio + 1), broadcast: paraIp(inicio + tamanho - 1), exemplo: paraIp(inicio + 10), inicio, tamanho }
}
function hostDoBloco(endereco, b) {
  const [ip, prefixo] = String(endereco).split('/')
  const n = paraNumero(ip)
  return Number(prefixo) === b.prefixo && n > b.inicio + 1 && n < b.inicio + b.tamanho - 1
}

export const LAB7 = {
  id: 'conectando-redes', base: '/api/lab7', numero: 7, etiqueta: 'LABORATÓRIO 7 · CONECTANDO REDES',
  titulo: 'Conectando redes', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'Duas filiais que não se enxergam',
    texto: 'Cada filial tem seu roteador, e os dois estão ligados por um enlace. Todo o endereçamento está pronto, mas o PC A não alcança o PC B. Descubra por quê, planeje as rotas estáticas e aplique uma de cada vez: primeiro a ida, depois a volta.',
    fila: [['Diagnóstico', '“O PC A não alcança o PC B.”'], ['Plano de rotas', 'destino e próximo salto de cada roteador'],
      ['Rota de ida', 'no R1, e um teste que mostra o que falta'], ['Rota de volta', 'no R2, e a comunicação nos dois sentidos']],
  },
  guia: {
    chamado: ['Abas PC A e R1 para testar; as suspeitas e a resposta ficam no painel do chamado.', 'As três suspeitas testadas e a causa confirmada no chamado.'],
    plano: ['Painel Plano de rotas, à direita.', 'O plano fica verde: conferido pelo servidor.'],
    ida: ['Aba R1 para a rota; aba PC A para o teste.', 'A rota aparece nas rotas do R1 e você testou do PC A.'],
    volta: ['Aba R2 para a rota; aba PC A para o teste.', 'A rota aparece nas rotas do R2 e o ping do PC A ao PC B responde.'],
  },
  abas: ['pca', 'r1', 'r2', 'pcb'],
  roteadores: ['r1', 'r2'],
  modeloPlano: null,
  planoDepoisDoChamado: true,
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 5)
    if (pronta) return pronta
    const rotas = (no) => s.estados?.[no]?.rotas?.length > 0
    if (s.etapa === 'chamado') {
      // Reproduzir o problema, testar uma suspeita de cada vez e só então responder: diz onde e o que observar,
      // a conclusão fica com o aluno (validação de 17/11/2026).
      const suspeitas = s.suspeitas || []
      if (s.testes?.pca?.['192.168.20.10'] === undefined && !suspeitas.some((x) => x.testada)) {
        return naAba(s, instrucao, ['pca'], 'PC A', 'Comece reproduzindo o problema no PC A.')
          || instrucao('Reproduza o problema', 'Do PC A, faça ping ao PC B (192.168.20.10). Repare no IP depois de "From": quem respondeu?', 'comando')
      }
      const i = suspeitas.findIndex((x) => !x.testada)
      if (i >= 0) {
        const x = suspeitas[i]
        const titulo = `Suspeita ${i + 1} de ${suspeitas.length}`
        return naAba(s, instrucao, [x.no], x.onde, `${titulo}: ${x.texto}`)
          || instrucao(titulo, `${x.texto} No ${x.onde}, rode ${x.comando}. ${x.olhar}`, 'comando')
      }
      return instrucao('Qual é a causa?', 'Compare cada suspeita com o que os seus testes mostraram e descarte as que funcionam. Pista: no ping ao PC B, quem respondeu "Destination Net Unreachable"? Procure esse IP na topologia.', 'causa')
    }
    if (s.etapa === 'plano') return instrucao('Planeje as rotas', 'Para cada roteador: a rede que ele ainda não conhece e o próximo salto, o vizinho no enlace 10.0.0.0/30.', 'plano')
    if (s.etapa === 'ida') {
      if (!rotas('r1')) return naAba(s, instrucao, ['r1'], 'R1', 'A rota de ida é no R1.')
        || instrucao('Aplique a rota de ida', 'No R1: ip route add <rede>/<prefixo> via <próximo salto>, com os valores do plano. Só a do R1, por enquanto.', 'comando')
      return naAba(s, instrucao, ['pca'], 'PC A', 'A rota de ida existe. Teste do PC A.')
        || instrucao('Teste a ida', 'Do PC A, faça ping ao PC B (192.168.20.10). A rota de ida existe: será que basta?', 'comando')
    }
    if (!rotas('r2')) return naAba(s, instrucao, ['r2'], 'R2', 'O pedido chega ao PC B, mas a resposta não tem caminho de volta.')
      || instrucao('Aplique a rota de volta', 'A resposta vai para 192.168.10.10 e o R2 não conhece essa rede. Aplique a rota do plano no R2.', 'comando')
    return naAba(s, instrucao, ['pca'], 'PC A', 'Agora há caminho nos dois sentidos.') || instrucao('Teste de novo', 'Do PC A, ping ao PC B.', 'comando')
  },
}

// Trilha revisada (15/11/2026): a LAN vem antes dos serviços, então este é o Lab 8 e o de DHCP e DNS passou a ser o 9.
// `arte` guarda o número do arquivo da arte, que não mudou.
export const LAB9 = {
  id: 'investigando-a-lan', base: '/api/lab9', numero: 8, arte: 9, etiqueta: 'LABORATÓRIO 8 · INVESTIGANDO E SEPARANDO A LAN',
  titulo: 'Investigando e separando a LAN', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'Uma LAN, dois setores, um switch',
    texto: 'Quatro computadores na mesma rede IP, ligados a um switch real. Um técnico começou a separar Vendas e Financeiro em VLANs e deixou o serviço pela metade. Investigue como o switch enxerga a rede, atenda o chamado e termine a separação.',
    fila: [['Investigação', 'tabela ARP do PC F1 e tabela MAC do switch'], ['Chamado', '“O PC V2 não fala com o PC V1.”'],
      ['Separar o Financeiro', 'portas do PC F1 e do PC F2 na VLAN 20'], ['Comprovar', 'quem deve se falar e quem não deve']],
  },
  guia: {
    investigar: ['Aba PC F1 (ping e ARP) e aba Switch (tabela MAC); respostas no painel Investigação.', 'A investigação fica verde: conferida pelo servidor.'],
    chamado: ['Aba Switch; a causa você escolhe no painel do chamado.', 'Causa confirmada e o ping do PC V2 ao PC V1 responde.'],
    separar: ['Aba Switch · portas eth2 e eth3; teste na aba PC F1.', 'Do PC F1, o PC F2 responde e o PC V1 não.'],
  },
  abas: ['v1', 'v2', 'switch', 'f1', 'f2'],
  roteadores: ['switch'],
  switchCentral: true,
  topologiaLan: true,
  agoraAoLado: true,
  semGateway: true,
  modeloPlano: null,
  observarChamado: ['ver-vlans'],
  plano: { etiqueta: 'INVESTIGAÇÃO · onde está o PC F2?', titulo: 'Investigação', coluna: 'Equipamento', rotulo: 'PC F2', botao: 'Conferir investigação' },
  textoComprovar: 'O servidor vai reler as VLANs do switch e repetir os pings: dentro de cada VLAN deve funcionar, entre VLANs não.',
  rotuloPc: (no, missao) => {
    const porta = Object.entries(missao?.portas || {}).find(([, nome]) => nome === missao?.nos?.find((n) => n.chave === no)?.nome)?.[0]
    return porta ? `porta ${porta}` : 'porta ?'
  },
  comandos: (no) => no?.tipo === 'switch' ? COMANDOS_SWITCH : 'ip addr show, ip link show, ip neigh show, ip route show e ping',
  // Um passo por vez, com a aba do equipamento marcada (validação de 22/11/2026). Os comandos seguem a forma da aula
  // Switch e VLANs: bridge <tabela> show para ler, bridge vlan add/del para mudar.
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 4)
    if (pronta) return pronta
    const passo = (titulo, texto, pistas, alvo = 'comando') => instrucao(titulo, texto, alvo, undefined, pistas)
    const indice = (no, tipo) => (s.historico || []).findIndex((h) => h.pc === no && h.tipo === tipo)
    const vlans = s.estados?.switch?.vlans || {}
    if (s.etapa === 'investigar') {
      const ping = indice('f1', 'ping')
      if (ping < 0) return naAba(s, instrucao, ['f1'], 'PC F1', 'Comece pelo PC F1: ele vai procurar o PC F2.')
        || passo('Fale com o PC F2', 'Do PC F1, faça ping ao PC F2 (192.168.30.22). Para mandar o ping, o PC F1 precisa descobrir o MAC do PC F2: é o ARP trabalhando.',
          ['O ping recebe só o endereço IP de destino.', 'ping 192.168.30.22'])
      if (!(s.historico || []).some((h, i) => i > ping && h.pc === 'f1' && h.tipo === 'ver-vizinhos')) return naAba(s, instrucao, ['f1'], 'PC F1', 'A tabela ARP que interessa é a do PC F1.')
        || passo('Leia a tabela ARP do PC F1', 'Agora o PC F1 guarda o MAC do PC F2. Na saída, procure a linha de 192.168.30.22: o MAC vem depois de lladdr.',
          ['É o comando ip com a tabela de vizinhos (neigh) e show, o mesmo da aula Ethernet, MAC e ARP.', 'ip neigh show'])
      if (indice('switch', 'ver-fdb') < 0) return naAba(s, instrucao, ['switch'], 'Switch', 'Você já tem o MAC do PC F2. Agora o switch: em que porta ele viu esse MAC?')
        || passo('Leia a tabela MAC do switch', 'O switch não tem tabela ARP, porque não usa IP. A tabela dele é a tabela MAC: em que porta cada MAC foi visto. Procure o MAC do PC F2; a porta vem depois de dev.',
          ['No switch, os comandos começam com bridge, seguidos da tabela e de show. A tabela MAC se chama fdb.', 'bridge fdb show'])
      return passo('Responda a investigação', 'No painel Investigação, à direita: o MAC do PC F2 (da tabela ARP do PC F1) e a porta do switch (da tabela MAC). Depois clique em Conferir investigação.', undefined, 'plano')
    }
    // Porta de acesso: primeiro entra na VLAN certa, depois sai da errada, e por fim o teste.
    // Cada porta em dois passos (validação de 22/11/2026: dizer o objetivo, onde a porta está agora e o que muda).
    // objetivo: a frase que abre o passo e diz por que esta porta muda.
    const ajustarPorta = (porta, vid, nome, objetivo, progresso = '') => {
      const v = vlans[porta] || { membro: [], untagged: [] }
      const membro = v.membro || []
      const agora = membro.length ? `Hoje a ${porta} está na VLAN ${membro.join(' e na VLAN ')}.` : `Hoje a ${porta} não está em nenhuma VLAN.`
      if (!membro.includes(vid) || v.pvid !== vid || !(v.untagged || []).includes(vid)) {
        return naAba(s, instrucao, ['switch'], 'Switch', `${objetivo} As portas se mudam no switch.`)
          || passo(`${porta} na VLAN ${vid} · 1 de 2`,
            `${objetivo} ${agora} Coloque a ${porta} na VLAN ${vid}; pvid e untagged a deixam como porta de acesso, e o ${nome} nem precisa saber de VLAN. ${progresso}`.trim(),
            ['O comando que põe uma porta numa VLAN é bridge vlan add, seguido da porta (dev), da VLAN (vid) e das duas opções da porta de acesso.', 'bridge vlan add dev <porta> vid <VLAN> pvid untagged'])
      }
      const sobra = membro.find((x) => x !== vid)
      if (sobra !== undefined) return naAba(s, instrucao, ['switch'], 'Switch', `A ${porta} ainda está em duas VLANs.`)
        || passo(`${porta} fora da VLAN ${sobra} · 2 de 2`,
          `A ${porta} (${nome}) entrou na VLAN ${vid}, mas continua na VLAN ${sobra}. Nas duas, ela não fica separada: tire a ${porta} da VLAN ${sobra}. ${progresso}`.trim(),
          ['O comando que tira uma porta de uma VLAN é bridge vlan del, seguido da porta (dev) e da VLAN que sai (vid).', 'bridge vlan del dev <porta> vid <VLAN que sai>'])
      return null
    }
    if (s.etapa === 'chamado') {
      if (!s.causaIdentificada) {
        if (s.observou) return passo('Qual é a causa?', 'Na saída de bridge vlan show, compare a VLAN da porta do PC V1 com a da porta do PC V2 (as portas estão na topologia). Depois escolha a causa no chamado.', undefined, 'causa')
        return naAba(s, instrucao, ['switch'], 'Switch', 'O PC V1 e o PC V2 estão na mesma rede IP e no mesmo switch.')
          || passo('Veja as VLANs das portas', 'Veja em que VLAN está cada porta do switch.',
            ['Mesmo padrão da tabela MAC: bridge, a tabela e show. As VLANs das portas são a tabela vlan.', 'bridge vlan show'])
      }
      return ajustarPorta('eth1', 10, 'PC V2', 'O PC V2 é do Vendas e precisa estar na mesma VLAN do PC V1, a 10.')
        || naAba(s, instrucao, ['v2'], 'PC V2', 'A porta do PC V2 está só na VLAN 10. Teste a partir dele.')
        || passo('Teste o PC V2', 'Do PC V2, faça ping ao PC V1 (192.168.30.11).', ['O mesmo teste do chamado.', 'ping 192.168.30.11'])
    }
    // Separar: o Financeiro sai da VLAN 1, que é a do switch inteiro, e vai para a VLAN 20, só dele.
    const prontas = ['eth2', 'eth3'].filter((p) => (vlans[p]?.membro || []).join() === '20' && vlans[p]?.pvid === 20).length
    const separar = 'Separe o Financeiro do Vendas: as portas do PC F1 (eth2) e do PC F2 (eth3) vão para a VLAN 20.'
    const porta = ajustarPorta('eth2', 20, 'PC F1', separar, `Portas prontas: ${prontas} de 2.`)
      || ajustarPorta('eth3', 20, 'PC F2', separar, `Portas prontas: ${prontas} de 2.`)
    if (porta) return porta
    const teste = (ip) => s.testes?.f1?.[ip]
    if (teste('192.168.30.22') !== true) return naAba(s, instrucao, ['f1'], 'PC F1', 'As duas portas estão na VLAN 20. Teste a partir do PC F1.')
      || passo('Teste dentro da VLAN 20', 'Do PC F1, faça ping ao PC F2 (192.168.30.22): os dois estão na VLAN 20 e devem se falar.', ['ping ao endereço do PC F2.', 'ping 192.168.30.22'])
    return naAba(s, instrucao, ['f1'], 'PC F1', 'Falta comprovar o isolamento, a partir do PC F1.')
      || passo('Comprove o isolamento', 'Do PC F1, faça ping ao PC V1 (192.168.30.11). Ele está na VLAN 10: desta vez o ping não deve responder.', ['ping ao endereço do PC V1.', 'ping 192.168.30.11'])
  },
}

// Labs 8 e 10: vários chamados, um por etapa. A orientação segue os passos do chamado aberto: investigar, causa,
// corrigir e comprovar; a ajuda diminui a cada chamado (no Lab 10, só o sintoma).
function orientarChamado(s, instrucao, { investigar, corrigir, comprovar }) {
  const p = s.progresso || {}
  // Cada passo pode trazer pistas no 3º item: [titulo, texto, pistas].
  const passo = ([titulo, texto, pistas]) => instrucao(titulo, texto, 'comando', undefined, pistas)
  if (!s.causaIdentificada) {
    if (s.observou) return instrucao('Qual é a causa?', 'Com base no que o terminal mostrou, escolha no chamado a causa do problema.', 'causa')
    return passo(investigar)
  }
  if (!p.configuracao) return passo(corrigir)
  return passo(comprovar)
}

const servidorDns = (no, missao) => {
  const e = missao?.estados?.[no]
  if (no && missao?.nos?.find((n) => n.chave === no)?.tipo !== 'pc') return e?.interfaces?.eth0?.length ? 'servidor' : ''
  return e?.dns?.length ? `DNS ${e.dns.join(', ')}` : 'sem DNS'
}

export const LAB8 = {
  id: 'enderecos-e-nomes', base: '/api/lab8', numero: 9, arte: 8, etiqueta: 'LABORATÓRIO 9 · ENDEREÇOS E NOMES AUTOMÁTICOS',
  titulo: 'Endereços e nomes automáticos', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'Mesa de suporte: endereços e nomes',
    texto: 'A rede do Atendimento (192.168.40.0/24) tem um servidor DHCP e DNS (192.168.40.2) que entrega endereços de .100 a .150 e traduz os nomes da empresa.local. Três chamados esperam por você; a ajuda diminui a cada um.',
    fila: [['PC Novo', '“Acabou de chegar e não acessa nada.”'], ['PC Recepção', '“A intranet não abre pelo nome; pelo IP abre.”'],
      ['PC Financeiro', '“A impressora não é encontrada.”'], ['Comprovar', 'endereço, gateway e DNS de cada PC, e os nomes']],
  },
  guia: {
    novo: ['Aba PC Novo; a causa você escolhe no painel do chamado.', 'O PC Novo tem endereço, gateway e DNS da concessão, e o ping pelo nome responde.'],
    recepcao: ['Aba PC Recepção; a causa você escolhe no painel do chamado.', 'O PC Recepção usa o DNS da empresa e a intranet responde pelo nome.'],
    financeiro: ['Aba PC Financeiro; a causa você escolhe no painel do chamado.', 'Causa confirmada e a impressora responde pelo nome certo.'],
  },
  abas: ['novo', 'recepcao', 'financeiro', 'servidor', 'intranet', 'impressora', 'roteador'],
  roteadores: ['roteador'],
  switchCentral: true,
  switchFixo: true,
  topologiaLan: true,
  agoraAoLado: true,
  mostrarDns: true,
  modeloPlano: null,
  rotuloPc: servidorDns,
  comandos: (no) => no?.tipo === 'pc' ? 'ip addr, ip route, ping, dhclient eth0, cat /etc/resolv.conf e nslookup'
    : 'ip addr, ip route (só leitura), ping e nslookup',
  textoComprovar: 'O servidor vai reler os três PCs (endereço da faixa do DHCP, gateway e servidor DNS) e repetir os pings pelos nomes.',
  passosChamado: (c, nos) => {
    const pc = nos[c?.no]?.nome
    if (c?.etapa === 'financeiro') return [`Repetir a consulta do usuário no ${pc}`, 'Confirmar a causa no chamado', 'Nada a corrigir no PC', 'Comprovar: ping pelo nome certo da impressora']
    return [`Investigar o ${pc} pelo terminal`, 'Confirmar a causa no chamado', `Corrigir a configuração do ${pc}`, `Comprovar: ping do ${pc} à intranet pelo nome`]
  },
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 4)
    if (pronta) return pronta
    const aba = (no, nome, texto) => naAba(s, instrucao, [no], nome, texto)
    if (s.etapa === 'novo') return aba('novo', 'PC Novo', 'O chamado 1 é do PC Novo.') || orientarChamado(s, instrucao, {
      investigar: ['Investigue o PC Novo', 'Veja os endereços com ip addr show: a eth0 está ligada (UP)? Tem alguma linha inet?'],
      corrigir: ['Peça um endereço ao DHCP', 'Use o cliente DHCP: dhclient eth0. Depois confira com ip addr show, ip route e cat /etc/resolv.conf.'],
      comprovar: ['Comprove pelo nome', 'Do PC Novo: ping intranet.empresa.local.'],
    })
    if (s.etapa === 'recepcao') return aba('recepcao', 'PC Recepção', 'O chamado 2 é do PC Recepção.') || orientarChamado(s, instrucao, {
      investigar: ['Compare IP e nome', 'Teste a intranet pelo IP (192.168.40.20) e pelo nome (nslookup), e veja qual servidor DNS o PC usa.'],
      corrigir: ['Passe o PC para o DHCP', 'A configuração foi feita à mão. Peça a concessão: ela traz o servidor DNS certo.'],
      comprovar: ['Comprove pelo nome', 'Teste a intranet pelo nome.'],
    })
    if (s.etapa === 'financeiro') return aba('financeiro', 'PC Financeiro', 'O chamado 3 é do PC Financeiro.') || orientarChamado(s, instrucao, {
      investigar: ['Repita o que o usuário fez', 'Consulte o nome que ele digitou e leia a resposta do servidor DNS.'],
      corrigir: ['Comprove', 'Teste a impressora pelo nome certo.'],
      comprovar: ['Comprove', 'Teste a impressora pelo nome certo.'],
    })
    return instrucao('Conclua a missão', 'Clique em Validar missão.', 'concluir')
  },
}

const PISTAS_LAB10 = {
  intranet: {
    investigar: ['Do PC V1, teste o caminho em ordem: o gateway do Vendas, o roteador do lado da intranet e a intranet pelo IP. Se o pedido chega e a resposta não volta, olhe as rotas de quem responde.',
      'ping 192.168.10.1, ping 192.168.60.1 e ping 192.168.60.20; depois, na aba do equipamento suspeito, ip route show'],
    corrigir: ['A rota padrão precisa apontar para o roteador, na mesma rede do equipamento. O Linux só aceita uma: remova a errada antes de adicionar a certa.',
      'ip route del default e depois ip route add default via <IP do roteador nessa rede>'],
  },
  vlan: {
    investigar: ['Compare o PC V2 com o PC V1: o endereço e o gateway são do mesmo setor? Se forem, olhe o caminho até o gateway: a porta de cada um no switch.',
      'No PC V2: ip addr show e ping 192.168.10.1. No switch: bridge vlan show, comparando a porta do PC V2 com a do PC V1.'],
    corrigir: ['A porta do PC V2 precisa ficar só na VLAN do Vendas, como porta de acesso: primeiro entra na VLAN certa, depois sai da errada.',
      'bridge vlan add dev <porta do PC V2> vid <VLAN do Vendas> pvid untagged e depois bridge vlan del dev <porta do PC V2> vid <VLAN errada>'],
  },
  dhcp: {
    investigar: ['Comece pelo próprio PC F1: a interface está ligada (UP)? Tem alguma linha inet com endereço?', 'No PC F1: ip addr show'],
    corrigir: ['O PC F1 precisa pedir endereço, gateway e DNS ao servidor DHCP do Financeiro.', 'dhclient eth0'],
  },
  dns: {
    investigar: ['Pelo IP a intranet abre? Então a rede está boa e o problema é o nome. Veja qual servidor DNS o PC F2 consulta e compare com o de um PC que funciona.',
      'No PC F2: ping 192.168.60.20, cat /etc/resolv.conf e nslookup intranet.empresa.local'],
    corrigir: ['Em vez de corrigir à mão, peça a configuração ao DHCP: ele entrega o servidor DNS certo do Financeiro.', 'dhclient eth0'],
  },
}

export const LAB10 = {
  id: 'desafio-rede-da-empresa', base: '/api/lab10', numero: 10, etiqueta: 'LABORATÓRIO 10 · DESAFIO FINAL',
  titulo: 'Desafio final: a rede da empresa', tempo: '25 min (+5 se precisar)',
  missao: {
    titulo: 'A rede da empresa está com quatro chamados',
    texto: 'Vendas (VLAN 10, 192.168.10.0/24) e Financeiro (VLAN 20, 192.168.20.0/24) ligados a um switch; o roteador liga os dois setores ao servidor da intranet (192.168.60.20) e é o servidor DHCP e DNS de cada setor. Use tudo o que aprendeu: investigue, encontre a causa, corrija e comprove. Aqui a ajuda é só o sintoma.',
    fila: [['Intranet', '“Ninguém consegue abrir a intranet.”'], ['PC V2', '“Não fala com ninguém.”'],
      ['PC F1', '“Acabou de chegar e não acessa nada.”'], ['PC F2', '“Abre a intranet pelo IP, mas não pelo nome.”']],
  },
  guia: {
    intranet: ['Comece pelo PC do chamado; a causa pode estar em outro equipamento.', 'Causa confirmada e um PC do Vendas abre a intranet pelo nome.'],
    vlan: ['Comece pelo PC V2; a causa pode estar em outro equipamento.', 'Causa confirmada e o PC V2 abre a intranet pelo nome.'],
    dhcp: ['Comece pelo PC F1; a causa pode estar em outro equipamento.', 'Causa confirmada e o PC F1 abre a intranet pelo nome.'],
    dns: ['Comece pelo PC F2; a causa pode estar em outro equipamento.', 'Causa confirmada e o PC F2 abre a intranet pelo nome.'],
  },
  abas: ['v1', 'v2', 'switch', 'roteador', 'intranet', 'f1', 'f2'],
  roteadores: ['switch', 'roteador', 'intranet'],
  switchCentral: true,
  enlace: '',
  topologiaLan: true,
  colunaLateral: true,
  agoraAoLado: true,
  mostrarDns: true,
  mostrarGateway: true,
  modeloPlano: null,
  rotuloPc: (no, missao) => {
    const porta = Object.entries(missao?.portas || {}).find(([, nome]) => nome === missao?.nos?.find((n) => n.chave === no)?.nome)?.[0]
    return [porta && `porta ${porta}`, servidorDns(no, missao)].filter(Boolean).join(' · ')
  },
  comandos: (no) => no?.tipo === 'switch' ? COMANDOS_SWITCH
    : no?.tipo === 'roteador' ? 'ip addr show, ip route show e ping (só leitura)'
      : 'ip addr show, ip link show, ip neigh show, ip route show, ping, dhclient eth0, cat /etc/resolv.conf e nslookup',
  textoComprovar: 'O servidor vai reler a rede inteira (VLANs, endereços, gateways, DNS e a rota do servidor) e repetir os testes: cada PC abre a intranet pelo nome, e o Vendas alcança o Financeiro pelo roteador.',
  passosChamado: (c, nos) => ['Investigar pelo terminal', 'Confirmar a causa no chamado', 'Corrigir o equipamento certo',
    `Comprovar: ping de ${c?.etapa === 'intranet' ? 'um PC do Vendas' : `o ${nos[c?.no]?.nome}`} à intranet pelo nome`],
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 5)
    if (pronta) return pronta
    if (s.etapa === 'comprovar') return instrucao('Conclua a missão', 'Clique em Validar missão.', 'concluir')
    // Validação de 22/11/2026: dizer quem abriu o chamado e como testar por partes, sem apontar a causa.
    const quem = s.nomeChamado || 'o PC do chamado'
    if (s.chamadoNo && !s.causaIdentificada && !s.observou && !(s.historico || []).some((h) => h.pc === s.chamadoNo)) {
      const aba = naAba(s, instrucao, [s.chamadoNo], quem, `Quem abriu este chamado foi o ${quem}. Comece por ele e reproduza o problema.`)
      if (aba) return aba
    }
    // Pistas sob pedido (validação de 22/11/2026): a 1ª diz o que observar e onde; a 2ª ajuda com o comando.
    const pistas = PISTAS_LAB10[s.etapa] || {}
    return orientarChamado(s, instrucao, {
      investigar: ['Investigue', `Quem abriu o chamado foi o ${quem}. Reproduza o problema nele e teste por partes: o nome vira endereço? O gateway responde? O destino responde pelo IP? Onde parar de funcionar, leia as tabelas daquele equipamento. A causa pode não estar no ${quem}.`, pistas.investigar],
      corrigir: ['Corrija', 'Você já sabe a causa: corrija só o equipamento responsável.', pistas.corrigir],
      comprovar: ['Comprove', `Teste a intranet pelo nome, a partir do ${quem}.`, ['O teste é o mesmo do sintoma: abrir a intranet pelo nome.', 'ping intranet.empresa.local']],
    })
  },
}

// Teste de carga (demonstração de 18/11/2026): fora da trilha e sem XP. Um só terminal, o da T.I.; o Financeiro B é
// atendido por SSH real, o gateway dele é corrigido pela própria sessão e uma folha vai à impressora do Prédio A.
export const LAB_SUPORTE = {
  id: 'suporte-remoto', base: '/api/carga', numero: 0, etiqueta: 'TESTE DE CARGA · SUPORTE REMOTO',
  titulo: 'Suporte remoto', tempo: '15 min (+5 se precisar)',
  missao: {
    titulo: 'O Financeiro do Prédio B não imprime',
    texto: 'Você está no PC da T.I., no Prédio B. Sem sair da sua mesa, entre por SSH no Financeiro B, descubra por que ele não alcança a impressora do Prédio A, corrija e imprima uma folha pela página da impressora. Cada aluno tem a própria rede, isolada, rodando no servidor ao mesmo tempo.',
    fila: [['SSH', 'da T.I. até o Financeiro B: usuário suporte, senha suporte123'], ['Gateway', 'a rota padrão do Financeiro B'],
      ['Impressão', 'pela página web da impressora do Prédio A (192.168.10.50)']],
  },
  guia: {
    acesso: ['Aba T.I. (a única): ssh suporte@192.168.20.21, senha suporte123.', 'O prompt muda para suporte@financeiro-b.'],
    gateway: ['Dentro do Financeiro B, pela sessão SSH.', 'A rota padrão do Financeiro B aponta para o roteador do Prédio B.'],
    impressao: ['Ainda no Financeiro B, pela sessão SSH.', 'A folha aparece em "Folhas impressas" e no mural do professor.'],
    comprovar: ['Botão Validar missão, ao lado do tempo.', 'O servidor confirma que a T.I. alcança o Financeiro B e ele alcança a impressora.'],
  },
  abas: ['fin_a', 'vendas_a', 'impressora', 'ti', 'fin_b', 'vendas_b'],
  terminais: ['ti'],
  topologiaPredios: true,
  agoraAoLado: true,
  semApresentacao: true,
  semXp: true,
  modeloPlano: null,
  comandos: () => 'ssh suporte@<endereço>, exit, ip addr, ip route, ping e curl (página da impressora)',
  textoComprovar: 'O servidor vai reler o Financeiro B e repetir os testes: a T.I. alcança o Financeiro B e o Financeiro B alcança a impressora do outro prédio.',
  orientar(s) {
    const [pronta, instrucao] = instrucaoBase(s, 4)
    if (pronta) return pronta
    const remoto = s.remoto === 'fin_b'
    if (s.senhaPendente) return instrucao('Digite a senha', 'O Financeiro B pediu a senha do usuário suporte: digite suporte123 e Enter. Ela não aparece na tela, como num terminal de verdade.', 'comando')
    if (s.etapa === 'acesso') return instrucao('Entre no Financeiro B por SSH', 'Na aba T.I., digite ssh suporte@192.168.20.21: o usuário suporte, no computador 192.168.20.21. A senha é suporte123.', 'comando', undefined,
      ['Antes, se quiser, teste com ping 192.168.20.21: os dois estão no mesmo prédio, sem passar pelo roteador.'])
    if (!remoto) return instrucao('Volte ao Financeiro B', 'A conexão SSH foi fechada. Digite ssh suporte@192.168.20.21 de novo (senha suporte123).', 'comando')
    if (s.etapa === 'gateway') return instrucao('Corrija o gateway do Financeiro B', 'A impressora fica em outra rede, então o caminho passa pelo gateway. Leia a rota padrão com ip route e troque pela do roteador do Prédio B.', 'comando', undefined,
      ['Tente abrir a página da impressora antes de corrigir: curl http://192.168.10.50. Veja o que acontece.',
        'O roteador do Prédio B é 192.168.20.1. Use ip route del default e depois ip route add default via 192.168.20.1.'])
    return instrucao('Imprima uma folha', 'Ainda no Financeiro B, abra a página da impressora com curl http://192.168.10.50. Depois imprima: curl -d "texto=seu nome" http://192.168.10.50/imprimir.', 'comando')
  },
}
