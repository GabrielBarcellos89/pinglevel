import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, BatteryFull, ChevronLeft, Clock3, MessageCircle, MoreVertical, Send, Server, Wifi } from 'lucide-react'
import linkEnsinando from '../assets/mascote/link-kit-v2/link-v2-ensinando.webp'
import linkPrincipal from '../assets/mascote/link-kit-v2/link-v2-principal.webp'
import { POSES } from '../assets/mascote/poses'
import linkConectando from '../assets/mascote/link-expansao-v1/link-conectando.webp'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import linkComemorando from '../assets/mascote/link-kit-v2/link-v2-comemorando.webp'
import { CenaCamada, ExplicacaoSimples, IntroCamadas, MapaCamadas, RecebimentoMensagem } from './CenasPercursoOsi'
import { CONTEUDOS_ADICIONAIS, RECEBIMENTO } from './conteudoPercursoOsi'
import './AulaFundamentosRede.css'
import './AulaModelosRede.css'
import './PreviaMensagemOsi.css'

const linkPensando = POSES.pensativo
const linkObservando = POSES.curioso

const ETAPAS = ['Por que camadas?', 'Conhecer o modelo OSI', 'A história da mensagem', 'Camada 7 · Aplicação', 'Camada 6 · Apresentação', 'Camada 5 · Sessão', 'Camada 4 · Transporte', 'Camada 3 · Rede', 'Camada 2 · Enlace', 'Camada 1 · Física', 'Recebimento · da camada 1 à 7']
const CAMADAS = [
  [7, 'Aplicação', 'O app pede para enviar a mensagem.'],
  [6, 'Apresentação', 'Deixa o texto num formato que o outro lado entende.'],
  [5, 'Sessão', 'Organiza o começo, o meio e o fim da conversa.'],
  [4, 'Transporte', 'Entrega ao programa certo (porta) e confere se nada se perdeu.'],
  [3, 'Rede', 'Põe o endereço de destino (IP) e acha o caminho entre redes.'],
  [2, 'Enlace', 'Leva até o próximo equipamento da rede local (Wi-Fi ou cabo).'],
  [1, 'Física', 'Transforma tudo em sinais: rádio, luz ou eletricidade.'],
]
const NOMES_CAMADAS = Object.fromEntries(CAMADAS.map(([numero, nome]) => [numero, nome]))
const MENSAGEM = 'Oi!'
const BYTES_UTF8 = Array.from(new TextEncoder().encode(MENSAGEM), (byte) => byte.toString(16).padStart(2, '0')).join(' ')

function Celular({ pessoa, pedidoPreparado, interativo, onEnviar, recebida, status, saidaConcluida }) {
  const ana = pessoa === 'Ana'
  const contato = ana ? 'Bruno' : 'Ana'
  return <div className={`osi-aparelho osi-celular-${ana ? 'ana' : 'bruno'} ${ana && pedidoPreparado ? 'pedido-preparado' : ''}`}>
    <strong className="osi-dono-celular">Celular de {pessoa}</strong>
    <div className="osi-celular">
      <div className="osi-phone-screen">
        <div className="osi-phone-statusbar" aria-hidden="true"><span className="osi-phone-signal"><Wifi size={12} /></span><span className="osi-phone-camera" /><BatteryFull size={15} /></div>
        <div className="osi-chat-header"><ChevronLeft size={14} aria-hidden="true" /><span className="osi-contact-avatar" aria-hidden="true">{contato[0]}</span><div><strong>{contato}</strong><small>App da aula</small></div><MoreVertical size={14} aria-hidden="true" /></div>
        <div className="osi-chat-body">
          {ana ? pedidoPreparado
            ? <div className="osi-balao"><span>{MENSAGEM}</span><small>{!saidaConcluida && <Clock3 size={11} aria-hidden="true" />}{saidaConcluida ? 'Ao serviço' : 'Preparando'}</small></div>
            : <div className="osi-chat-empty"><MessageCircle size={24} aria-hidden="true" /><span>Sua mensagem<br />está no rascunho</span></div>
            : recebida ? <div className="osi-balao osi-balao-recebido"><span>{MENSAGEM}</span><small>Na conversa</small></div>
            : <div className="osi-chat-empty"><MessageCircle size={24} aria-hidden="true" /><span>A conversa<br />ainda está vazia</span></div>}
        </div>
        {ana ? <div className="osi-composer"><span className={`osi-composer-text ${pedidoPreparado ? 'placeholder' : ''}`}>{pedidoPreparado ? 'Mensagem' : MENSAGEM}</span>{interativo ? <button type="button" className="osi-enviar" aria-label={pedidoPreparado ? 'Preparando o envio' : 'Enviar'} title={pedidoPreparado ? 'Preparando o envio' : 'Enviar'} disabled={pedidoPreparado} onClick={onEnviar}>{pedidoPreparado ? <Clock3 size={18} /> : <Send size={18} />}</button> : <span className="osi-envio-ilustrativo" aria-hidden="true"><Send size={17} /></span>}</div> : <div className="osi-composer-vazio" aria-hidden="true"><span>Mensagem</span></div>}
        <div className="osi-home-indicator" aria-hidden="true" />
      </div>
    </div>
    <span className="osi-mensagem-status" data-testid={ana ? 'ana-status' : 'bruno-status'}>{status || (ana ? pedidoPreparado ? 'Preparando o envio' : 'Rascunho' : 'Ainda não recebeu')}</span>
  </div>
}

function PreviaMensagemOsi({ aula = null }) {
  const inicial = aula?.initialState
  const onStateChange = aula?.onStateChange
  const navigate = useNavigate()
  const [cena, setCena] = useState(inicial?.cena ?? 0)
  const [pedidoPreparado, setPedidoPreparado] = useState(inicial?.pedidoPreparado ?? false)
  const [mostrarBytes, setMostrarBytes] = useState(inicial?.mostrarBytes ?? false)
  const [representacaoVista, setRepresentacaoVista] = useState(inicial?.representacaoVista ?? false)
  const [encerrada, setEncerrada] = useState(false)
  const tituloRef = useRef(null)
  const [atividades, setAtividades] = useState(inicial?.atividades ?? {})
  const [passoRecebimento, setPassoRecebimento] = useState(inicial?.passoRecebimento ?? 0)
  // c: posição dentro do percurso original (-1 é a tela "Por que dividir em camadas?", que vem antes da tabela).
  const c = cena - 1
  const recebendo = cena === ETAPAS.length - 1
  const camada = c >= 2 && !recebendo ? CAMADAS[c - 2] : null
  const atividade = camada ? CONTEUDOS_ADICIONAIS[camada[0]] : null
  const atividadeConcluida = Boolean(camada && atividades[camada[0]])
  const recebida = recebendo && passoRecebimento === RECEBIMENTO.length - 1
  const podeAvancar = c <= 1 || (c === 2 ? pedidoPreparado : c === 3 ? representacaoVista : recebendo ? recebida : atividadeConcluida)
  const titulo = c === -1 ? 'Por que dividir em camadas?' : c === 0 ? 'Vamos conhecer a tabela OSI' : c === 1 ? 'Como o “Oi!” chega ao outro celular?' : recebendo ? 'Quem recebe faz o caminho inverso' : camada[1]
  const subtitulo = c === 2 ? 'O aplicativo prepara um pedido de comunicação.' : c === 3 ? 'Uma representação que os dois lados possam interpretar.' : atividade?.subtitulo
  const textoAvancar = c === -1 ? 'Conhecer as 7 camadas' : c === 0 ? 'Começar a história' : c === 1 ? 'Acompanhar a mensagem' : c === 2 ? 'Como preparar esse texto?' : c === 3 ? 'Como organizar a troca?' : recebendo ? aula ? 'Relacionar com TCP/IP' : 'Encerrar esta prévia' : atividade.proxima
  let fala
  let mentor
  if (c === -1) {
    fala = 'Antes de olhar a tabela, uma ideia simples: mandar uma mensagem pela rede é um trabalho dividido em tarefas, como enviar uma encomenda pelo correio.'
    mentor = { imagem: linkEnsinando, alt: 'Link explicando a ideia das camadas', contexto: 'Uma ideia antes da tabela' }
  } else if (c === 0) {
    fala = 'Vamos conhecer as sete camadas do modelo OSI e reconhecer suas funções em uma mensagem entre celulares. Use esta tabela como mapa, não como uma lista para decorar.'
    mentor = { imagem: linkEnsinando, alt: 'Link apresentando as camadas OSI', contexto: 'Conheça o mapa' }
  } else if (c === 1) {
    fala = 'Ana quer mandar um “Oi!” para Bruno. Vamos acompanhar o que precisa acontecer para essa mensagem chegar?'
    mentor = { imagem: linkPrincipal, alt: 'Link convidando a acompanhar a mensagem', contexto: 'Vamos acompanhar juntos' }
  } else if (c === 2) {
    fala = pedidoPreparado
      ? 'O aplicativo preparou o pedido ao serviço de mensagens. Você está observando uma função da camada de Aplicação; a mensagem ainda não foi entregue.'
      : 'Ana já escreveu para Bruno. Toque no botão de enviar do celular e observe o aplicativo preparar o pedido.'
    mentor = pedidoPreparado
      ? { imagem: linkConectando, alt: 'Link demonstrando a preparação da comunicação', contexto: 'O pedido foi preparado' }
      : { imagem: linkPensando, alt: 'Link pensando sobre o envio da mensagem', contexto: 'Observe antes de avançar' }
  } else if (c === 3) {
    fala = representacaoVista
      ? 'Os dois lados precisam interpretar o texto do mesmo jeito. Aqui usamos UTF-8: um exemplo de representação de dados, função relacionada à Apresentação.'
      : 'A mensagem continua sendo “Oi!”. Vamos observar uma forma de representar esses caracteres para a comunicação?'
    mentor = representacaoVista
      ? { imagem: linkExplicando, alt: 'Link explicando a representação dos dados', contexto: 'Texto e representação' }
      : { imagem: linkObservando, alt: 'Link observando a representação da mensagem', contexto: 'Vamos olhar mais de perto' }
  } else if (recebendo) {
    fala = 'No envio, percorremos da camada 7 até a 1. Quem recebe faz o contrário: começa na Física, camada 1, e sobe até a Aplicação, camada 7. Avance uma camada de cada vez.'
    mentor = recebida
      ? { imagem: linkComemorando, alt: 'Link comemorando a mensagem exibida na simulação', contexto: 'A mensagem apareceu para Bruno' }
      : { imagem: passoRecebimento >= 3 ? linkExplicando : linkObservando, alt: `Link acompanhando ${RECEBIMENTO[passoRecebimento].nome} no recebimento`, contexto: 'Agora o caminho é de baixo para cima' }
  } else {
    fala = atividadeConcluida ? atividade.depois : atividade.antes
    const expressoes = { 5: linkEnsinando, 4: linkExplicando, 3: linkConectando, 2: linkObservando, 1: linkConectando }
    mentor = { imagem: atividadeConcluida ? expressoes[camada[0]] : camada[0] === 5 ? linkPensando : linkObservando, alt: `Link ${atividadeConcluida ? 'explicando' : 'observando'} a camada de ${camada[1]}`, contexto: atividadeConcluida ? `Função de ${camada[1]} explorada` : 'Observe e experimente no seu ritmo' }
  }

  useEffect(() => { tituloRef.current?.focus() }, [cena])

  useEffect(() => {
    onStateChange?.({ cena, pedidoPreparado, mostrarBytes, representacaoVista, atividades, passoRecebimento })
  }, [cena, pedidoPreparado, mostrarBytes, representacaoVista, atividades, passoRecebimento, onStateChange])

  async function avancar() {
    if (!podeAvancar || aula?.salvando) return
    if (cena < ETAPAS.length - 1) {
      if (aula && !await aula.onAvancar(cena + 1)) return
      setCena((atual) => atual + 1)
    } else if (aula) aula.onResumo()
    else setEncerrada(true)
  }

  function recomecar() {
    setCena(0)
    setPedidoPreparado(false)
    setMostrarBytes(false)
    setRepresentacaoVista(false)
    setAtividades({})
    setPassoRecebimento(0)
    setEncerrada(false)
  }

  function alternarRepresentacao() {
    setMostrarBytes((atual) => !atual)
    setRepresentacaoVista(true)
  }

  return <main className="principal pagina-aula aula-modelos-pagina pagina-previa-osi">
    <p className="osi-previa-aviso">{aula ? <><strong>Modelos OSI e TCP/IP · {aula.revisao ? 'Revisão da aula concluída' : 'Módulo 1 · Aula 2'}</strong> {aula.revisao ? 'Revisar não altera o progresso nem concede XP novamente.' : 'Retomada detalhada neste navegador; progresso geral e conclusão na sua conta.'}</> : <><strong>Prévia para validar · percurso OSI completo e recebimento inverso.</strong> A aula atual, seu progresso e seu XP não são alterados.</>}</p>
    {aula?.erro && <div className="feedback-desafio" role="alert">{aula.erro}</div>}
    {aula?.aviso && <p className="osi-previa-aviso" role="status">{aula.aviso}</p>}
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate(aula ? '/' : '/modulos/fundamentos/modelos-de-rede')}><ArrowLeft size={18} /> {aula ? 'Voltar ao início' : 'Voltar à aula atual'}</button>
      <div className="aula-progresso-area"><div><span>{ETAPAS[cena]}</span><strong data-testid="scene-position">Etapa {cena + 1} de {ETAPAS.length}</strong></div><div className="aula-progresso" aria-label={aula ? 'Posição na sequência da aula' : 'Posição na prévia, não progresso da aula'}><div style={{ width: `${((cena + 1) / ETAPAS.length) * 100}%` }} /></div></div>
      <span className="aula-tempo">No seu ritmo</span>
    </section>

    <section className="aula-palco">
      <div className="aula-conteudo"><div className="aula-bloco osi-previa-cena" data-scene={cena + 1}>
        {camada ? <header className="osi-camada-atual" data-testid="layer-banner" aria-label={`Camada ${camada[0]}: ${camada[1]}`}><span className="osi-camada-numero">{camada[0]}</span><div><span className="osi-camada-kicker">CAMADA OSI EM FOCO</span><h1 data-testid="scene-title" ref={tituloRef} tabIndex={-1}>{titulo}</h1><p>{subtitulo}</p></div></header>
          : <><span className="aula-etiqueta">{c === -1 ? 'INTRODUÇÃO · A IDEIA DAS CAMADAS' : c === 0 ? 'INTRODUÇÃO · MODELO OSI' : recebendo ? 'RECEBIMENTO · CAMADA 1 → 7' : 'CENÁRIO · A MENSAGEM'}</span><h1 data-testid="scene-title" ref={tituloRef} tabIndex={-1}>{titulo}</h1></>}
        {camada && <MapaCamadas atual={camada[0]} nomes={NOMES_CAMADAS} />}
        {camada && <ExplicacaoSimples numero={camada[0]} />}
        <p className="osi-narracao" aria-live="polite">{fala}</p>

        {c === -1 ? <IntroCamadas /> : c === 0 ? <>
          <table className="osi-tabela-intro" aria-label="As sete camadas do modelo OSI"><thead><tr><th scope="col">Nº</th><th scope="col">Camada</th><th scope="col">Qual é o papel?</th></tr></thead><tbody>{CAMADAS.map(([numero, nome, funcao]) => <tr key={numero}><td><span>{numero}</span></td><th scope="row">{nome}</th><td>{funcao}</td></tr>)}</tbody></table>
          <p className="osi-intro-convite">Agora vamos dar vida a esse mapa: uma mensagem, uma função de cada vez.</p>
        </> : <>
          {recebendo && <><p className="osi-transicao-servidor" data-testid="server-transition">Na continuação desta simulação, o serviço já recebeu o pedido de Ana e prepara <strong>outra entrega</strong> para Bruno. É essa nova comunicação que vamos receber; não é o mesmo pacote passando intacto pelo servidor.</p><RecebimentoMensagem passo={passoRecebimento} mensagem={MENSAGEM} onProximo={() => setPassoRecebimento((atual) => Math.min(RECEBIMENTO.length - 1, atual + 1))} onAnterior={() => setPassoRecebimento((atual) => Math.max(0, atual - 1))} /></>}
          <div className={`osi-mensagem-cenario ${recebendo ? 'foco-bruno' : c >= 2 ? 'foco-ana' : ''}`} aria-label="Cenário ilustrativo: celular de Ana, rede, servidor do aplicativo, rede e celular de Bruno">
            <Celular pessoa="Ana" pedidoPreparado={pedidoPreparado} interativo={c === 2} onEnviar={() => setPedidoPreparado(true)} saidaConcluida={recebendo} status={recebendo ? 'Enviada ao serviço na simulação' : undefined} />
            <div className="osi-trecho-rede osi-trecho-ida" aria-label="Rede entre Ana e o servidor"><Wifi size={17} /><ArrowRight size={18} /><small>Rede</small></div>
            <div className="osi-servidor"><Server size={35} /><strong>Servidor</strong><span>do aplicativo</span><small>{recebendo ? 'Nova entrega' : 'Aguardando'}</small></div>
            <div className="osi-trecho-rede osi-trecho-volta" aria-label="Rede entre o servidor e Bruno"><Wifi size={17} /><ArrowRight size={18} /><small>Rede</small></div>
            <Celular pessoa="Bruno" recebida={recebida} status={recebendo ? RECEBIMENTO[passoRecebimento].estado : undefined} />
          </div>

          {c === 3 && <section className="osi-representacao" aria-label="Explorar a representação do texto"><div className="osi-representacao-conteudo"><span>{mostrarBytes ? 'Bytes UTF-8 · hexadecimal' : 'A mensagem que Ana escreveu'}</span><strong data-testid="representation">{mostrarBytes ? BYTES_UTF8 : MENSAGEM}</strong></div><button className="botao-secundario" onClick={alternarRepresentacao}>{!representacaoVista ? 'Ver como o texto é representado' : mostrarBytes ? 'Ver mensagem' : 'Ver representação'}</button></section>}

          {c === 1 && <details className="osi-saiba-mais"><summary>Por que aparece um servidor?</summary><p>Neste exemplo, o aplicativo usa um serviço intermediário. A primeira entrega é de Ana ao serviço; depois há outra entrega a Bruno. Não é um único pacote atravessando o servidor intacto.</p></details>}
          {c === 2 && <details className="osi-saiba-mais"><summary>O aplicativo inteiro é uma camada?</summary><p>Não. Estudamos funções de comunicação usadas por ele. Bruno é o destinatário da conversa; o pedido deste primeiro trecho vai ao servidor do aplicativo.</p></details>}
          {atividade && <CenaCamada numero={camada[0]} concluida={atividadeConcluida} onAcao={() => setAtividades((atual) => ({ ...atual, [camada[0]]: true }))} />}
        </>}
        {encerrada && <div className="feedback-desafio sucesso" role="status">Percurso explorado na simulação. No envio: 7 → 1. No recebimento: 1 → 7. Nenhuma aula real foi concluída e nenhum XP foi registrado.</div>}
      </div></div>
      <aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={mentor.imagem} alt={mentor.alt} data-testid="link-expression" /><div className="link-identidade"><strong>Link</strong><span>{mentor.contexto}</span></div></div></aside>
    </section>

    <footer className="aula-navegacao">
      <button className="botao-voltar" disabled={cena === 0 || aula?.salvando} onClick={() => { setCena((atual) => Math.max(0, atual - 1)); setEncerrada(false) }}><ArrowLeft size={18} /> Etapa anterior</button>
      <div className="aula-passos" aria-label="Etapas da prévia">{ETAPAS.map((nome, indice) => <span key={nome} className={indice <= cena ? 'ativo' : ''} title={nome} />)}</div>
      {encerrada ? <button className="botao-avancar" onClick={recomecar}>Rever desde a introdução <ArrowRight size={18} /></button>
        : <button className="botao-avancar" disabled={!podeAvancar || aula?.salvando} onClick={avancar}>{aula?.salvando ? 'Salvando…' : textoAvancar}<ArrowRight size={18} /></button>}
    </footer>
  </main>
}

export default PreviaMensagemOsi
