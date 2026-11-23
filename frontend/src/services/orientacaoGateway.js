// Orientação visual derivada do estado confirmado; não concede etapas ou evidências.
export function orientarGateway(s) {
  const etapa = `ETAPA ${!s.localPronto ? 1 : !s.redePronta ? 2 : !s.mesmoGateway ? 3 : 4} DE 4`
  const instrucao = (titulo, texto, alvo, etiqueta = etapa) => ({ titulo, texto, alvo, etiqueta, ocupado: s.ocupado })
  if (s.recuperacao || s.expirado) return instrucao('Confira o estado do ambiente', 'Use Atualizar estado para continuar com segurança.', 'atualizar', 'AMBIENTE')
  if (s.preparacaoPendente) return instrucao('Encerre o ambiente incompleto', 'A preparação não foi confirmada. Encerre este ambiente antes de tentar novamente.', 'encerrar', 'AMBIENTE')
  if (s.conflito) return instrucao('Outra missão está em uso', 'Volte ao catálogo para abrir o laboratório que já está ativo.', 'catalogo', 'AMBIENTE')
  if (s.registrada) return s.pendente
    ? instrucao('Conclusão salva; falta encerrar o ambiente', 'Use Tentar limpeza novamente para confirmar a remoção.', 'limpar', 'CONCLUSÃO')
    : instrucao('Missão concluída', 'Seu progresso está salvo. Você pode voltar ao catálogo ou iniciar um novo treino.', 'catalogo', 'CONCLUSÃO')
  if (!s.ativo) return instrucao('Inicie sua rede', 'Clique em Iniciar ambiente para começar a prática.', 'iniciar', 'PREPARAÇÃO')
  if (!s.localPronto) return !s.previsao
    ? instrucao('Faça sua previsão', 'Sem gateway, o computador alcançará o colega? Escolha uma previsão.', 'previsao')
    : instrucao('Teste o colega no terminal', 'Observe o endereço do colega na topologia e verifique se ele responde a partir do PC Atendimento.', s.erroTerminal || !s.comando?.trim() ? 'comando' : 'executar')
  if (!s.redePronta) return instrucao('Compare as redes', 'O servidor está na mesma rede do PC Atendimento? Escolha uma resposta e confirme.', !s.classificacao || s.classificacaoIncorreta ? 'classificacao' : 'comparar')
  if (!s.mesmoGateway) {
    if (!s.observado && !s.gateway) return instrucao('Consulte o roteador', 'Clique no roteador e observe a interface ligada à rede do Atendimento.', 'roteador')
    return instrucao('Configure o gateway do computador', 'Informe a interface local do roteador como gateway. Depois aplique a configuração.', !s.gateway || s.gatewayInvalido ? 'gateway' : 'aplicar')
  }
  if (!s.depoisValido) {
    if (s.remotoFalhou) return instrucao('Revise o gateway escolhido', 'O servidor não respondeu. Compare o gateway com as interfaces do roteador e ajuste a configuração.', 'gateway')
    return instrucao('Teste o servidor no terminal', 'Localize o servidor na topologia e verifique se o PC Atendimento consegue se comunicar com ele.', s.erroTerminal || !s.comando?.trim() ? 'comando' : 'executar')
  }
  if (!s.interpretacaoCorreta) return instrucao('Explique os resultados', 'Por que o colega respondia sem gateway, mas o servidor precisava dele? Escolha e confirme sua explicação.', !s.resposta || s.interpretacaoIncorreta ? 'interpretacao' : 'interpretar')
  return instrucao('Conclua a missão', 'Comunicação e interpretação comprovadas. Clique em Validar missão para registrar seu progresso.', 'concluir')
}
