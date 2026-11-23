// Orientação do Lab 4 (chamados) derivada do estado confirmado; não concede etapas. A ajuda diminui a cada chamado:
// o 1 sugere os comandos, o 2 sugere comparar com o PC Novo e o 3 traz só o sintoma.
export const NOMES_PC = { novo: 'PC Novo', financeiro: 'PC Financeiro', recepcao: 'PC Recepção' }

// "Onde" e "Pronto quando" de cada chamado: completam o "Agora faça" sem entregar valores.
const GUIA = {
  1: ['Aba PC Novo · interface eth0; a causa você escolhe no painel do chamado.', 'O PC Novo tem endereço e rota padrão, e o ping ao servidor (192.168.20.10) responde.'],
  2: ['Aba PC Financeiro; compare com a aba PC Novo. A causa você escolhe no painel do chamado.', 'Causa confirmada e o ping do PC Financeiro ao servidor responde.'],
  3: ['Aba PC Recepção; a causa você escolhe no painel do chamado.', 'Causa confirmada e o ping do PC Recepção ao servidor responde.'],
  4: ['Botão Validar missão, ao lado do tempo.', 'O servidor confirma a missão e mostra o XP.'],
}

export function orientarTerminal(s) {
  const orientacao = orientar(s)
  if (!/^(CHAMADO|COMPROVAR)/.test(orientacao.etiqueta)) return orientacao
  const [onde, pronto] = GUIA[{ 'chamado-1': 1, 'chamado-2': 2, 'chamado-3': 3 }[s.etapa] || 4]
  return { ...orientacao, onde, pronto }
}

function orientar(s) {
  const indice = { 'chamado-1': 1, 'chamado-2': 2, 'chamado-3': 3 }[s.etapa] || 4
  const instrucao = (titulo, texto, alvo, etiqueta = `CHAMADO ${indice} DE 3`) => ({ titulo, texto, alvo, etiqueta, ocupado: s.ocupado })
  if (s.recuperacao || s.expirado) return instrucao('Confira o estado do ambiente', 'Use Atualizar estado para continuar com segurança.', 'atualizar', 'AMBIENTE')
  if (s.preparacaoPendente) return instrucao('Encerre o ambiente incompleto', 'A preparação não foi confirmada. Encerre este ambiente antes de tentar novamente.', 'encerrar', 'AMBIENTE')
  if (s.conflito) return instrucao('Outra missão está em uso', 'Volte ao catálogo para abrir o laboratório que já está ativo.', 'catalogo', 'AMBIENTE')
  if (s.registrada) return s.pendente
    ? instrucao('Conclusão salva; falta encerrar o ambiente', 'Use Tentar limpeza novamente para confirmar a remoção.', 'limpar', 'CONCLUSÃO')
    : instrucao('Missão concluída', 'Seu progresso está salvo. Você pode voltar ao catálogo ou iniciar um novo treino.', 'catalogo', 'CONCLUSÃO')
  if (!s.ativo) return instrucao('Inicie o ambiente', 'Clique em Iniciar ambiente. Três chamados de suporte vão chegar da rede do Atendimento.', 'iniciar', 'PREPARAÇÃO')
  if (indice === 4) return instrucao('Conclua a missão', 'Os três chamados estão resolvidos. Clique em Validar missão: o servidor relê os PCs e repete os testes.', 'concluir', 'COMPROVAR')
  const nome = NOMES_PC[s.pc]
  if (!s.causaIdentificada) {
    if (s.observou) return instrucao('Qual é a causa?', `Com base no que o terminal mostrou, escolha no chamado a causa do problema do ${nome}.`, 'causa')
    if (indice === 1) return instrucao('Atenda o PC Novo', 'Na aba PC Novo, digite ip addr show para ver a interface e tente ping 192.168.10.12, o PC Financeiro.', 'comando')
    if (indice === 2) return instrucao('Investigue o PC Financeiro', 'Leia a tabela de rotas do PC Financeiro e compare com a do PC Novo, que já funciona.', 'comando')
    return instrucao('Investigue o PC Recepção', 'Fala com os colegas, mas não alcança o servidor. Investigue pelo terminal.', 'comando')
  }
  if (s.abaAtual !== s.pc) return instrucao(`Abra a aba ${nome}`, `As correções deste chamado são feitas no ${nome}.`, `aba-${s.pc}`)
  if (indice === 1) {
    if (s.enderecos > 1) return instrucao('Deixe um só endereço', 'A interface tem mais de um endereço. Remova o que não serve com ip addr del.', 'comando')
    if (!s.enderecos) return instrucao('Dê um endereço ao PC Novo', 'Escolha um endereço livre da rede 192.168.10.0/24 e aplique com: ip addr add <endereço>/<prefixo> dev eth0.', 'comando')
    if (!s.temRota) return instrucao('Falta o caminho para outras redes', 'Crie a rota padrão com ip route add default via <gateway>. O gateway é a interface do roteador na rede do PC.', 'comando')
    return instrucao('Comprove com o servidor', s.servidorFalhou ? 'O servidor não respondeu. Confira endereço, prefixo e rota padrão antes de testar de novo.' : 'Teste o servidor: ping 192.168.20.10.', 'comando')
  }
  if (indice === 2) return instrucao('Corrija o PC Financeiro', 'Corrija a rota padrão e comprove com um ping ao servidor.', 'comando')
  return instrucao('Corrija o PC Recepção', 'Corrija a configuração e comprove com o servidor.', 'comando')
}
