import { useEffect, useMemo, useState } from 'react'
import { embaralhar } from '../services/embaralhar'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { CAPTURA, PASSOS_TCP, PERGUNTAS_CAPTURA, PERGUNTAS_PORTAS, PERGUNTAS_UDP } from '../services/aulaTransporte'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaRoteamento.css'
import './AulaExplicacao.css'
import './AulaTransporte.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'
import cenaTcp from '../assets/aulas/transporte-tcp.webp'
import cenaUdp from '../assets/aulas/transporte-udp.webp'

// Abre o Módulo 3 (trilha revisada em 15/11/2026): a camada de transporte antes dos serviços que dependem dela.
const AULA_ID = 'servicos-transporte'
const etapas = ['Portas', 'TCP', 'UDP', 'Ler a captura', 'Conclusão']
const IMAGENS = POSES_AULA
// Etapas de perguntas: lista e a dica quando a resposta não confere.
const QUIZ = {
  0: [PERGUNTAS_PORTAS, 'O IP é o prédio; a porta é o apartamento. As portas conhecidas são as mais baixas.'],
  1: [PASSOS_TCP, 'O cliente pede (SYN), o servidor aceita e confirma (SYN-ACK), o cliente confirma (ACK).'],
  2: [PERGUNTAS_UDP, 'O UDP não abre conexão: troca velocidade por garantia.'],
  3: [PERGUNTAS_CAPTURA, 'Procure as flags SYN e ACK e a porta de destino de cada linha.'],
}

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  const ordem = useMemo(() => embaralhar(opcoes), [opcoes])
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {ordem.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

function Captura() {
  return <div className="at-captura" role="table" aria-label="Captura de pacotes">
    <div role="row" className="at-cabecalho"><span role="columnheader">#</span><span role="columnheader">Protocolo</span>
      <span role="columnheader">Origem → destino (IP:porta)</span><span role="columnheader">Informação</span></div>
    {CAPTURA.map(([n, protocolo, caminho, info]) => <div role="row" key={n} className={`at-linha ${protocolo === 'UDP' ? 'udp' : 'tcp'}`}>
      <span role="cell">{n}</span><span role="cell"><b>{protocolo}</b></span><span role="cell"><code>{caminho}</code></span><span role="cell">{info}</span></div>)}
  </div>
}

export default function AulaTransporte() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [respostas, setRespostas] = useState({})
  const [conferido, setConferido] = useState({})

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const chave = (q) => `${etapa}-${q.id}`
  function podeAvancar() {
    if (QUIZ[etapa]) return conferido[etapa] && QUIZ[etapa][0].every((q) => respostas[chave(q)] === q.correta)
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

  const botaoConferir = (pronto) => <button className="botao-interacao" type="button" disabled={!pronto}
    onClick={() => setConferido({ ...conferido, [etapa]: true })}><Check size={17} /> Conferir</button>
  const perguntas = () => {
    const [lista, dica] = QUIZ[etapa]
    return <>
      {lista.map((q) => <article key={q.id} className="af-caso">
        <strong>{q.pergunta || q.descricao}</strong>
        <Escolhas grupo={q.pergunta || q.descricao} opcoes={q.opcoes} valor={respostas[chave(q)]}
          aoEscolher={(v) => { setRespostas({ ...respostas, [chave(q)]: v }); setConferido({ ...conferido, [etapa]: false }) }} />
        {conferido[etapa] && <p className={`ag-retorno ${respostas[chave(q)] === q.correta ? 'ok' : 'erro'}`}>
          {respostas[chave(q)] === q.correta ? `✓ ${q.certo}` : `✗ ${dica}`}</p>}
      </article>)}
      {botaoConferir(lista.every((q) => respostas[chave(q)]))}
    </>
  }

  function conteudo() {
    if (etapa === 0) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 03 · TRANSPORTE: PORTAS, TCP E UDP</span>
        <h1>Portas de comunicação</h1>
        <p className="aula-destaque">O IP leva o pacote até o computador certo. Mas nele rodam várias aplicações ao mesmo
          tempo: a porta diz qual delas recebe os dados. Pense num prédio: o IP é o endereço do prédio e a porta é o número
          do apartamento.</p>
        <section className="aula-explica" aria-label="Faixas de portas">
          <h3>Os números de porta</h3>
          <p>Vão de <b>0 a 65535</b> e se dividem em três faixas:</p>
          <ul>
            <li><b>0 a 1023, portas conhecidas:</b> reservadas aos serviços mais comuns e padronizados.</li>
            <li><b>1024 a 49151, portas registradas:</b> usadas por aplicações específicas.</li>
            <li><b>49152 a 65535, portas dinâmicas:</b> o sistema empresta uma delas, por um tempo, à aplicação cliente.</li>
          </ul>
          <p>Algumas portas conhecidas que você vai encontrar:</p>
          <div className="aula-tabela">
            <b>22</b><span>SSH: acesso remoto ao terminal de outro computador</span>
            <b>53</b><span>DNS: descobrir o endereço de um nome</span>
            <b>80</b><span>HTTP: páginas web</span>
          </div>
        </section>
        {perguntas()}
        <p className="ag-fonte">Portas, a analogia do prédio e as faixas de portas em <i>Redes para Iniciantes</i>, p. 82–84.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">TCP</span>
        <h2>Conexão antes dos dados: o Three-Way Handshake</h2>
        <p>O TCP só troca dados depois de abrir uma conexão entre os dois computadores. Com a conexão aberta, ele garante
          que os dados cheguem na ordem certa e manda de novo o que se perder.</p>
        <section className="aula-explica" aria-label="Como o TCP abre e fecha a conexão">
          <h3>Abrir a conexão: três pacotes</h3>
          <ol>
            <li><b>SYN</b>: o cliente pede para abrir a conexão.</li>
            <li><b>SYN-ACK</b>: o servidor, se a porta estiver aberta, aceita e confirma o pedido.</li>
            <li><b>ACK</b>: o cliente confirma. A conexão está aberta e os dados começam a passar.</li>
          </ol>
          <h3>Fechar a conexão</h3>
          <p>No fim, os dois lados trocam <b>FIN</b> e <b>ACK</b>: cada um avisa que terminou e o outro confirma. Assim os
            dois concordam em fechar.</p>
        </section>
        <img className="at-cena" src={cenaTcp} alt="O Link entrega o pacote na mão: primeiro SYN, SYN-ACK e ACK abrem a conexão, depois o pacote vai e o servidor confirma com ACK." />
        <p>Agora monte a sequência:</p>
        {perguntas()}
        <p className="ag-fonte">Three-Way Handshake, ordem, retransmissão e encerramento em <i>Redes para Iniciantes</i>, p. 86–87.</p>
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">UDP</span>
        <h2>Sem conexão, mais rápido</h2>
        <p>O UDP é o protocolo de melhor esforço: manda o datagrama direto, sem abrir conexão (sem SYN, SYN-ACK e ACK), sem
          confirmar a entrega e sem mandar de novo o que se perder. Perde garantias, ganha velocidade, e a própria aplicação
          cuida do resto: numa consulta DNS, se a resposta não vier, ela simplesmente pergunta de novo.</p>
        <img className="at-cena" src={cenaUdp} alt="O Link joga os pacotes sem combinar antes: um chega ao servidor DNS, um cai no caminho e outro se perde, e ninguém reenvia." />
        <div className="at-comparativo">
          <article><b>TCP</b><span>orientado à conexão · garante entrega e ordem · mais lento</span><small>web, e-mail, arquivos, SSH</small></article>
          <article><b>UDP</b><span>sem conexão · melhor esforço · mais rápido</span><small>streaming, jogos, VoIP, DNS</small></article>
        </div>
        {perguntas()}
        <p className="ag-fonte">Comparativo TCP x UDP (Tabela 3) e o UDP em <i>Redes para Iniciantes</i>, p. 89–91.</p>
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">LER A CAPTURA</span>
        <h2>TCP e UDP nos bastidores</h2>
        <p>Uma captura mostra cada pacote com o protocolo, a origem e o destino com as portas (IP:porta). Nas linhas 1 a 4,
          o PC 192.168.1.10 abre a página de um servidor web; nas linhas 5 e 6, pergunta um nome ao servidor DNS.</p>
        <Captura />
        {perguntas()}
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>A camada de transporte em quatro ideias</h2>
      <div className="resumo-aprendizado">
        <div><Check /> O IP chega ao computador; a porta escolhe a aplicação. As portas conhecidas vão de 0 a 1023.</div>
        <div><Check /> O TCP abre a conexão com SYN, SYN-ACK e ACK e garante entrega e ordem.</div>
        <div><Check /> O UDP manda direto, sem conexão: mais rápido, sem garantia.</div>
        <div><Check /> SSH (22) e a web (80) usam TCP; o DNS (53) usa UDP nas consultas.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>Na próxima aula, o switch e as VLANs organizam a rede local. Mais adiante, na aula de DHCP e DNS, você vai
          reconhecer o UDP que acabou de ver.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas aula-roteamento aula-transporte">
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate('/modulos')}><ArrowLeft size={18} /> Sair da aula</button>
      <div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div>
        <div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div>
      <span className="aula-tempo">10–12 min</span>
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
