import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Computer, Network, Printer, Server, Globe, RotateCcw } from 'lucide-react'
import IconeRoteador from '../components/laboratorio/IconeRoteador'
import { DESTINOS, GATEWAYS, PASSOS, PERGUNTAS, decidir } from '../services/aulaGateway'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'fundamentos-gateway'
const etapas = ['Dois caminhos', 'Prever', 'Escolher o gateway', 'Ida e volta', 'Rota padrão', 'Conclusão']
const IMAGENS = POSES_AULA
const ICONES = { colega: Computer, impressora: Printer, servidor: Server, site: Globe }

// Topologia do Lab 3; `destaque` acende os elementos envolvidos no passo atual.
function Topologia({ destaque = [], falha = false }) {
  const marca = (id) => `ag-no ${destaque.includes(id) ? 'ag-destaque' : ''}`
  return <div className={`ag-topologia ${falha ? 'ag-falha' : ''}`} role="img"
    aria-label="PC Atendimento e PC Colega ligados a um switch; o switch liga ao roteador, que liga ao Servidor">
    <div className="ag-rede ag-rede-local"><span>Atendimento · 192.168.10.0/24</span>
      <div className="ag-pcs">
        <div className={marca('pc')}><Computer size={22} /><strong>PC Atendimento</strong><small>192.168.10.10</small></div>
        <div className={marca('colega')}><Computer size={22} /><strong>PC Colega</strong><small>192.168.10.20</small></div>
      </div>
      <div className="ag-cabo" aria-hidden="true" />
      <div className={marca('switch')}><Network size={22} /><strong>Switch</strong></div>
    </div>
    <div className="ag-cabo" aria-hidden="true" />
    <div className={marca('roteador')}><IconeRoteador /><strong>Roteador</strong><small>192.168.10.1</small><small>192.168.20.1</small></div>
    <div className="ag-cabo" aria-hidden="true" />
    <div className="ag-rede ag-rede-remota"><span>Servidor · 192.168.20.0/24</span>
      <div className={marca('servidor')}><Server size={22} /><strong>Servidor</strong><small>192.168.20.10</small></div>
    </div>
  </div>
}

export default function AulaGateway() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [destinoAberto, setDestinoAberto] = useState('')
  const [vistos, setVistos] = useState([])
  const [previsoes, setPrevisoes] = useState({})
  const [previsaoConferida, setPrevisaoConferida] = useState(false)
  const [gateway, setGateway] = useState('')
  const [passo, setPasso] = useState(0)
  const [semGateway, setSemGateway] = useState(false)
  const [viuFalha, setViuFalha] = useState(false)
  const [viuSucesso, setViuSucesso] = useState(false)
  const [respostas, setRespostas] = useState({})
  const [respostasConferidas, setRespostasConferidas] = useState(false)

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const previsaoCerta = previsaoConferida && DESTINOS.every((d) => previsoes[d.id] === decidir(d.ip).caminho)
  const gatewayCerto = GATEWAYS.find((g) => g.ip === gateway)?.correto === true
  const respostasCertas = respostasConferidas && PERGUNTAS.every((p) => respostas[p.id] === p.correta)
  const sequencia = semGateway ? PASSOS.semGateway : PASSOS.normal
  const passoAtual = sequencia[Math.min(passo, sequencia.length - 1)]

  function podeAvancar() {
    if (etapa === 0) return vistos.length === 2
    if (etapa === 1) return previsaoCerta
    if (etapa === 2) return gatewayCerto
    if (etapa === 3) return viuSucesso && viuFalha
    if (etapa === 4) return respostasCertas
    return true
  }

  async function enviar(url, corpo) {
    const resposta = await fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) })
    const dados = await resposta.json().catch(() => ({}))
    if (!resposta.ok || !dados.sucesso) throw new Error(dados.mensagem || 'Não foi possível salvar o progresso. Tente novamente.')
    return dados
  }

  async function avancar() {
    if (!podeAvancar() || salvando) return
    setSalvando(true)
    setErro('')
    try {
      if (etapa === etapas.length - 1) {
        const dados = await enviar('/api/progresso/aula/concluir', { aula_id: AULA_ID })
        setConquista({ xp: dados.progresso?.xp_concedido })
        return
      }
      await enviar('/api/progresso/aula', { aula_id: AULA_ID, etapa_atual: etapa + 1 })
      setEtapa(etapa + 1)
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  function abrirDestino(id) {
    setDestinoAberto(id)
    if (!vistos.includes(id)) setVistos([...vistos, id])
  }

  function avancarPasso() {
    const proximo = Math.min(passo + 1, sequencia.length - 1)
    setPasso(proximo)
    if (proximo === sequencia.length - 1) (semGateway ? setViuFalha : setViuSucesso)(true)
  }

  function alternarGatewayServidor() {
    setSemGateway(!semGateway)
    setPasso(0)
  }

  function conteudo() {
    if (etapa === 0) {
      const decisao = destinoAberto && decidir(DESTINOS.find((d) => d.id === destinoAberto).ip)
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 01 · GATEWAY E ENTREGA LOCAL</span>
        <h1>Dois destinos, dois caminhos</h1>
        <p className="aula-destaque">O PC Atendimento quer falar com o colega e com o servidor. Antes de enviar, ele decide:
          o destino está na minha rede ou em outra?</p>
        <Topologia destaque={destinoAberto === 'colega' ? ['pc', 'switch', 'colega'] : destinoAberto === 'servidor' ? ['pc', 'switch', 'roteador'] : []} />
        <div className="ag-escolha" role="group" aria-label="Escolha um destino">
          {['colega', 'servidor'].map((id) => <button key={id} type="button" aria-pressed={destinoAberto === id}
            className={destinoAberto === id ? 'ativo' : ''} onClick={() => abrirDestino(id)}>
            Enviar ao {id === 'colega' ? 'PC Colega' : 'Servidor'}</button>)}
        </div>
        {decisao && <section className="ag-decisao" aria-live="polite">
          <h3>Como o computador decide</h3>
          <ol>
            <li>Aplica a máscara /24 ao destino {decisao.destino}: rede <b>{decisao.redeDestino}</b>.</li>
            <li>Compara com a própria rede: <b>192.168.10.0</b>.</li>
            <li>{decisao.caminho === 'direto'
              ? 'São iguais: o destino está na mesma rede. A entrega é direta, pelo switch.'
              : 'São diferentes: o destino está em outra rede. O pacote vai para o gateway, o roteador da rede local.'}</li>
          </ol>
        </section>}
        {vistos.length < 2 && <p className="ag-dica">Experimente os dois destinos para continuar.</p>}
        <p className="ag-fonte">Baseado em <i>Redes para Iniciantes</i>, p. 155–156.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">PREVER</span>
        <h2>Direto ou pelo gateway?</h2>
        <p>O PC Atendimento (192.168.10.10/24) vai enviar dados a quatro destinos. Para cada um, decida o caminho.</p>
        <div className="ag-destinos">
          {DESTINOS.map((d) => {
            const Icone = ICONES[d.id]
            const certo = decidir(d.ip).caminho
            return <article key={d.id} className="ag-destino">
              <div><Icone size={22} /><strong>{d.nome}</strong><small>{d.ip}</small></div>
              <div className="ag-opcoes" role="group" aria-label={`Caminho até ${d.nome}`}>
                {[['direto', 'Entrega direta'], ['gateway', 'Pelo gateway']].map(([valor, rotulo]) =>
                  <button key={valor} type="button" aria-pressed={previsoes[d.id] === valor} className={previsoes[d.id] === valor ? 'ativo' : ''}
                    onClick={() => { setPrevisoes({ ...previsoes, [d.id]: valor }); setPrevisaoConferida(false) }}>{rotulo}</button>)}
              </div>
              {previsaoConferida && <p className={`ag-retorno ${previsoes[d.id] === certo ? 'ok' : 'erro'}`}>
                {previsoes[d.id] === certo ? 'Certo. ' : 'Reveja. '}{decidir(d.ip).explicacao}</p>}
            </article>
          })}
        </div>
        <button className="botao-interacao" type="button" disabled={DESTINOS.some((d) => !previsoes[d.id])}
          onClick={() => setPrevisaoConferida(true)}><Check size={17} /> Conferir previsões</button>
      </div>
    }
    if (etapa === 2) {
      const escolhido = GATEWAYS.find((g) => g.ip === gateway)
      return <div className="aula-bloco">
        <span className="aula-etiqueta">PRATICAR</span>
        <h2>Escolha o gateway do PC Atendimento</h2>
        <p>O gateway recebe os pacotes destinados a outras redes. Qual destes endereços pode cumprir esse papel?</p>
        <Topologia destaque={escolhido?.destaque || []} />
        <div className="ag-escolha ag-gateways" role="group" aria-label="Escolha o gateway">
          {GATEWAYS.map((g) => <button key={g.ip} type="button" aria-pressed={gateway === g.ip} className={gateway === g.ip ? 'ativo' : ''}
            onClick={() => setGateway(g.ip)}><strong>{g.ip}</strong><small>{g.rotulo}</small></button>)}
        </div>
        {escolhido && <p className={`feedback-desafio ${escolhido.correto ? 'sucesso' : ''}`} role="status">{escolhido.explicacao}</p>}
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">OBSERVAR</span>
        <h2>Ida e volta de um ping ao servidor</h2>
        <p>Primeiro acompanhe o ping com tudo configurado. Depois, tire o gateway do servidor e repita para ver o que muda.</p>
        <p className={`ag-parte ${semGateway ? 'ag-parte-falha' : ''}`}>{semGateway ? 'Parte 2 de 2 · Servidor sem gateway' : 'Parte 1 de 2 · Servidor com gateway'}</p>
        <Topologia destaque={passoAtual.destaque} falha={semGateway && passo === sequencia.length - 1} />
        <section className={`ag-passo ${passoAtual.falha ? 'ag-passo-falha' : ''}`} aria-live="polite">
          <span>Passo {passo + 1} de {sequencia.length}</span>
          <h3>{passoAtual.titulo}</h3>
          <p>{passoAtual.texto}</p>
        </section>
        <div className="ag-controles">
          <button className="botao-interacao" type="button" disabled={passo === sequencia.length - 1} onClick={avancarPasso}>
            Próximo passo <ArrowRight size={17} /></button>
          <button type="button" className="ag-secundario" onClick={() => setPasso(0)}><RotateCcw size={16} /> Recomeçar</button>
          {semGateway && <button type="button" className="ag-secundario" aria-pressed="true" onClick={alternarGatewayServidor}>
            Devolver o gateway ao servidor</button>}
        </div>
        {viuSucesso && !semGateway && !viuFalha && <section className="ag-chamada" aria-live="polite">
          <div><strong>Parte 1 concluída: o ping foi e voltou.</strong>
            <p>Agora tire o gateway do servidor e percorra de novo. Assim você vê por que a volta também precisa de caminho.</p></div>
          <button type="button" className="botao-interacao" onClick={alternarGatewayServidor}>Remover o gateway do servidor</button>
        </section>}
        <p className="ag-dica">{viuSucesso && viuFalha ? 'Pronto: você viu a ida e volta completa e o que acontece sem o caminho de volta. Clique em Continuar.'
          : !viuSucesso ? 'Clique em Próximo passo até o ping voltar ao PC Atendimento.'
            : semGateway ? 'Clique em Próximo passo até o fim para ver onde o ping se perde.' : 'Use o botão acima para remover o gateway do servidor.'}</p>
        <p className="ag-fonte">Passos baseados em <i>Redes para Iniciantes</i>, p. 156–157.</p>
      </div>
    }
    if (etapa === 4) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">INTERPRETAR</span>
        <h2>O gateway cria a rota padrão</h2>
        <p className="aula-destaque">Configurar o gateway cria a <b>rota padrão</b>: o caminho de último recurso para todo
          destino fora da própria rede. Sem ela, um pacote para outra rede não tem por onde sair e é descartado.</p>
        <div className="ag-perguntas">
          {PERGUNTAS.map((p) => <fieldset key={p.id} className="ag-pergunta">
            <legend>{p.texto}</legend>
            {p.opcoes.map(([valor, texto]) => <label key={valor}><input type="radio" name={p.id} value={valor} checked={respostas[p.id] === valor}
              onChange={() => { setRespostas({ ...respostas, [p.id]: valor }); setRespostasConferidas(false) }} />{texto}</label>)}
            {respostasConferidas && <p className={`ag-retorno ${respostas[p.id] === p.correta ? 'ok' : 'erro'}`}>
              {respostas[p.id] === p.correta ? p.acerto : p.dica}</p>}
          </fieldset>)}
        </div>
        <button className="botao-interacao" type="button" disabled={PERGUNTAS.some((p) => !respostas[p.id])}
          onClick={() => setRespostasConferidas(true)}><Check size={17} /> Conferir respostas</button>
        <p className="ag-fonte">Rota padrão em <i>Redes para Iniciantes</i>, p. 155.</p>
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>Agora você sabe quando usar o gateway</h2>
      <div className="resumo-aprendizado">
        <div><Check /> O computador aplica a máscara ao destino e compara com a própria rede.</div>
        <div><Check /> Mesma rede: entrega direta. Outra rede: envio ao gateway.</div>
        <div><Check /> O gateway é a interface do roteador na própria rede local.</div>
        <div><Check /> A comunicação precisa de caminho de ida e de volta.</div>
        <div><Check /> O gateway configurado é a rota padrão, o caminho de último recurso.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 3 você configura o gateway de um computador num ambiente real e compara a comunicação antes e
          depois. Mais adiante, na aula de ferramentas, vai ver a rota padrão no terminal com <code>ip route</code>.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway">
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate('/modulos')}><ArrowLeft size={18} /> Sair da aula</button>
      <div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div>
        <div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div>
      <span className="aula-tempo">10–15 min</span>
    </section>
    <section className="aula-palco">
      <div className="aula-conteudo">{conteudo()}</div>
      <aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={IMAGENS[etapa]} alt="Link, mascote do PingLevel" />
        <div className="link-identidade"><strong>Link</strong><span>Seu guia de aprendizagem</span></div></div></aside>
    </section>
    {erro && <p className="ag-erro" role="alert">{erro}</p>}
    <footer className="aula-navegacao">
      <button className="botao-voltar" onClick={() => (etapa === 0 ? navigate('/modulos') : setEtapa(etapa - 1))}>
        <ArrowLeft size={18} />{etapa === 0 ? 'Voltar aos módulos' : 'Etapa anterior'}</button>
      <div className="aula-passos" aria-label="Progresso das etapas">
        {etapas.map((nome, i) => <span key={nome} className={i <= etapa ? 'ativo' : ''} title={nome} />)}</div>
      <button className="botao-avancar" onClick={avancar} disabled={!podeAvancar() || salvando}>
        {salvando ? 'Salvando...' : etapa === etapas.length - 1 ? 'Concluir aula' : 'Continuar'}<ArrowRight size={18} /></button>
    </footer>
    {conquista && <ConquistaAula aulaId={AULA_ID} xp={conquista.xp} />}
  </main>
}
