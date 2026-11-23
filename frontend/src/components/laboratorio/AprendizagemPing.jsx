import { useState } from 'react'

function Pergunta({ fase, pergunta, salva, bloqueada, processando, onResponder }) {
  const [escolha, setEscolha] = useState('')
  return (
    <form className="lab-aprendizagem-pergunta" onSubmit={(evento) => {
      evento.preventDefault()
      if (escolha) onResponder(fase, escolha)
    }}>
      <fieldset disabled={bloqueada || processando}>
        <legend>{pergunta.enunciado}</legend>
        {pergunta.opcoes.map((opcao) => (
          <label key={opcao.id}><input type="radio" name={`ping-${fase}`} value={opcao.id}
            checked={(bloqueada ? salva : escolha || salva) === opcao.id}
            onChange={() => setEscolha(opcao.id)} />{opcao.texto}</label>
        ))}
      </fieldset>
      {!bloqueada && <button type="submit" disabled={!escolha || processando}>
        {fase === 'previsao' ? 'Registrar minha previsão' : 'Conferir interpretação'}
      </button>}
    </form>
  )
}

export default function AprendizagemPing({ aprendizagem, ativo, processando, onResponder }) {
  if (!aprendizagem?.perguntas) return null
  const {
    perguntas, previsao, pode_prever: podePrever,
    pode_interpretar: podeInterpretar, interpretacao_correta: correta,
  } = aprendizagem
  return (
    <div className="lab-aprendizagem">
      <h3>{!podePrever ? 'Aguardando a etapa 3'
        : !previsao ? 'Etapa 3: faça sua previsão antes do ping'
          : !podeInterpretar ? 'Etapa 4: pratique e observe'
            : correta ? 'Etapa 5: interpretação concluída' : 'Etapa 5: interprete o resultado'}</h3>
      {!podePrever
        ? <p>Os Bastidores serão liberados quando você chegar à etapa de comunicação. Continue a missão pela etapa atual.</p>
        : !previsao && <>
          <p>Você concluiu a identificação e o endereçamento. Agora registre uma hipótese; errar faz parte da investigação.</p>
          <Pergunta fase="previsao" pergunta={perguntas.previsao} salva={previsao}
            bloqueada={!ativo} processando={processando} onResponder={onResponder} />
        </>}
      {previsao && !podeInterpretar && <p>Execute o ping do Computador 1 para o Computador 2 e observe a saída e os Bastidores.</p>}
      {podeInterpretar && <Pergunta fase="interpretacao" pergunta={perguntas.interpretacao}
        salva={aprendizagem.interpretacao} bloqueada={correta || !ativo}
        processando={processando} onResponder={onResponder} />}
      {aprendizagem.feedback && <p className="lab-aprendizagem-feedback" role="status"><strong>Link:</strong> {aprendizagem.feedback}</p>}
    </div>
  )
}
