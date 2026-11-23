import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Network, Router } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { aplicarRascunho, conferirRevisao, criarClienteIPv4 } from '../services/progressoIPv4'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import './AulaFundamentosRede.css'
import './AulaEnderecoIPv4.css'
import PreviaEnderecoIPv4 from './PreviaEnderecoIPv4'
import { lerIntroducaoIPv4 } from '../services/retomadaIntroducaoIPv4'
import ConquistaAula from '../components/aula/ConquistaAula'

const etapas = ['Aprender', 'Prever', 'Praticar', 'Observar', 'Interpretar', 'Concluir']
const exercicios = [
  { id: 'rede', pergunta: 'Qual é o endereço da rede de 192.168.10.34/24?', opcoes: [['rede-10', '192.168.10.0'], ['host-34', '192.168.10.34'], ['broadcast-10', '192.168.10.255']], correta: '192.168.10.0' },
  { id: 'local', pergunta: '192.168.10.80/24 está na mesma rede que 192.168.10.34/24?', opcoes: [['sim', 'Sim'], ['nao', 'Não']], correta: 'Sim' },
  { id: 'gateway', pergunta: 'Para enviar dados a 8.8.8.8, qual destino local o computador usa primeiro?', opcoes: [['mac-remoto', 'O endereço MAC do servidor remoto'], ['gateway', 'O gateway da rede'], ['broadcast', 'O endereço de broadcast']], correta: 'O gateway da rede' },
]

function AulaEnderecoIPv4() {
  const { usuario } = useAuth()
  if (!usuario) return <main className="principal" role="status">Carregando sua sessão…</main>
  return <PercursoIPv4 key={usuario.id} usuarioId={usuario.id} />
}

function PercursoIPv4({ usuarioId }) {
  const navigate = useNavigate()
  const cliente = useMemo(() => criarClienteIPv4(), [])
  const [estado, setEstado] = useState(null)
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const [legado, setLegado] = useState(false)
  const [temPendente, setTemPendente] = useState(false)
  const [conquista, setConquista] = useState(null)
  const ativo = useRef(false)
  const geracao = useRef(0)
  const controller = useRef(null)
  const ocupado = useRef(false)
  const confirmado = useRef(null)
  const pendente = useRef(null)
  const revisando = estado?.modo === 'revisao'
  const chaveIntroducao = `pinglevel:ipv4:introducao:v1:usuario:${usuarioId}`
  const [introducao, setIntroducao] = useState(() => {
    try { return lerIntroducaoIPv4(window.localStorage.getItem(chaveIntroducao)) }
    catch { return null }
  })
  const [avisoIntroducao, setAvisoIntroducao] = useState('')
  const guardarIntroducao = useCallback((novo) => {
    if (revisando) return
    setIntroducao(novo)
    try { window.localStorage.setItem(chaveIntroducao, JSON.stringify(novo)) }
    catch { setAvisoIntroducao('Não foi possível salvar a introdução neste navegador. Respostas e conclusão no servidor continuam preservadas.') }
  }, [chaveIntroducao, revisando])

  const etapa = estado?.etapa_retomada ?? 0
  const previsao = estado?.respostas.previsao ?? ''
  const respostas = estado?.respostas.pratica ?? {}
  const interpretacao = estado?.respostas.interpretacao ?? ''
  const validada = estado?.validacoes.pratica.status !== 'pendente'
  const praticaCorreta = estado?.validacoes.pratica.status === 'aprovada'
  const interpretacaoValidada = estado?.validacoes.interpretacao.status === 'aprovada'
  const praticaCompleta = exercicios.every((item) => Boolean(respostas[item.id]))
  const bloqueado = carregando || salvando || Boolean(erro)
  const total = etapas.length
  const progresso = Math.round(((etapa + 1) / total) * 100)

  const carregar = useCallback(async () => {
    controller.current?.abort()
    const numero = ++geracao.current
    const controle = new AbortController()
    controller.current = controle
    ocupado.current = true
    setCarregando(true)
    setEstado(null)
    setErro(null)
    try {
      const salvo = await cliente.carregar(controle.signal)
      if (!ativo.current || numero !== geracao.current) return
      confirmado.current = salvo
      pendente.current = null
      setTemPendente(false)
      setEstado(salvo)
      setLegado(salvo.legado_sem_respostas)
    } catch (falha) {
      if (!ativo.current || numero !== geracao.current) return
      setErro({ status: falha.status, mensagem: falha.name === 'AbortError'
        ? 'A consulta demorou demais. Tente novamente.' : falha.message })
    } finally {
      if (ativo.current && numero === geracao.current) {
        ocupado.current = false
        setCarregando(false)
      }
    }
  }, [cliente])

  useEffect(() => {
    ativo.current = true
    const numero = geracao.current
    queueMicrotask(() => {
      if (ativo.current && numero === geracao.current) void carregar()
    })
    return () => {
      ativo.current = false
      geracao.current += 1
      controller.current?.abort()
      ocupado.current = false
    }
  }, [carregar])

  useEffect(() => {
    function avisarSaida(evento) {
      if (!pendente.current && !ocupado.current) return
      evento.preventDefault()
      evento.returnValue = ''
    }
    window.addEventListener('beforeunload', avisarSaida)
    return () => window.removeEventListener('beforeunload', avisarSaida)
  }, [])

  async function operar(operacao) {
    if (ocupado.current) return
    ocupado.current = true
    pendente.current = operacao
    setTemPendente(true)
    setSalvando(true)
    setErro(null)
    const numero = ++geracao.current
    const controle = new AbortController()
    controller.current = controle
    try {
      let novo
      let xp
      if (operacao.tipo === 'salvar') {
        novo = await cliente.salvar(operacao.base, operacao.respostas, operacao.etapa, controle.signal)
      } else if (operacao.tipo === 'validar') {
        novo = await cliente.validar(operacao.base, operacao.atividade, controle.signal)
      } else if (operacao.tipo === 'avancar') {
        novo = await cliente.avancar(operacao.base, operacao.etapa, controle.signal)
      } else {
        const dados = await cliente.concluir(operacao.base, controle.signal)
        novo = dados.estado
        xp = dados.progresso?.xp_concedido
      }
      if (!ativo.current || numero !== geracao.current) return
      confirmado.current = novo
      pendente.current = null
      setTemPendente(false)
      setEstado(novo)
      if (operacao.tipo === 'concluir') setConquista({ xp })
    } catch (falha) {
      if (!ativo.current || numero !== geracao.current) return
      setErro({ status: falha.status, mensagem: falha.name === 'AbortError'
        ? 'A operação demorou demais. O salvamento não foi confirmado.' : falha.message })
    } finally {
      if (ativo.current && numero === geracao.current) {
        ocupado.current = false
        setSalvando(false)
      }
    }
  }

  function atualizar(parcial) {
    if (ocupado.current || bloqueado) return
    setEstado(aplicarRascunho(estado, parcial))
    if (!revisando) void operar({ tipo: 'salvar', base: confirmado.current, respostas: parcial })
  }

  function conferir(atividade) {
    if (ocupado.current || bloqueado) return
    if (revisando) setEstado(conferirRevisao(estado, atividade))
    else void operar({ tipo: 'validar', base: confirmado.current, atividade })
  }

  function podeAvancar() {
    if (revisando) return true
    if (etapa === 1) return Boolean(previsao)
    if (etapa === 2) return praticaCorreta
    if (etapa === 4) return interpretacaoValidada
    return true
  }

  function avancar() {
    if (ocupado.current || bloqueado || !podeAvancar()) return
    if (revisando) {
      if (etapa === total - 1) navigate('/')
      else setEstado({ ...estado, etapa_retomada: etapa + 1 })
      return
    }
    void operar({ tipo: etapa === total - 1 ? 'concluir' : 'avancar',
      base: confirmado.current, etapa: etapa + 1 })
  }

  function voltar() {
    if (ocupado.current || bloqueado) return
    if (!etapa) { sair(); return }
    if (revisando) setEstado({ ...estado, etapa_retomada: etapa - 1 })
    else void operar({ tipo: 'salvar', base: confirmado.current, respostas: {}, etapa: etapa - 1 })
  }

  function sair(destino = '/') {
    if (ocupado.current) return
    if (pendente.current && !window.confirm('Há uma operação não confirmada. Sair pode perder alterações locais. Deseja sair?')) return
    navigate(destino)
  }

  function recarregar() {
    if (pendente.current && !window.confirm('Recarregar descarta alterações locais não confirmadas e recupera o estado salvo. Continuar?')) return
    void carregar()
  }

  function tentarNovamente() {
    if (pendente.current) void operar(pendente.current)
  }

  function renderErro() {
    if (!erro) return null
    return <section className="ipv4-estado ipv4-estado-erro" role="alert">
      <strong>{temPendente ? 'Operação não confirmada' : 'Não foi possível carregar a aula'}</strong>
      <p>{erro.mensagem}</p>
      {erro.status === 409 && <p>Outra aba atualizou a aula. Suas alterações locais não foram sobrescritas no servidor.</p>}
      <div className="ipv4-estado-acoes">
        {temPendente && (!erro.status || erro.status >= 500) && <button onClick={tentarNovamente}>Tentar novamente</button>}
        <button onClick={recarregar}>{temPendente ? 'Recarregar estado salvo' : 'Tentar carregar novamente'}</button>
        {[401, 403].includes(erro.status) && <button onClick={() => sair(erro.status === 403 ? '/alterar-senha' : '/login')}>{erro.status === 403 ? 'Verificar acesso' : 'Entrar novamente'}</button>}
      </div>
    </section>
  }

  // Depois da conclusão o estado volta como revisão (etapa 0); a conquista fica por cima de tudo até o aluno escolher.
  if (conquista) return <main className="principal pagina-aula aula-ipv4-pagina"><ConquistaAula aulaId="enderecamento-ipv4" xp={conquista.xp} /></main>

  if (carregando || !estado) return <main className="principal pagina-aula aula-ipv4-pagina">
    <section className="aula-bloco ipv4-estado">
      <h1>Endereçamento IPv4</h1>
      {carregando ? <p role="status">Recuperando seu progresso…</p> : renderErro()}
      <button className="botao-voltar" disabled={carregando} onClick={() => sair()}><ArrowLeft size={18} /> Início</button>
    </section>
  </main>

  if (etapa === 0) return <PreviaEnderecoIPv4 aula={{ initialState: revisando ? null : introducao, onStateChange: guardarIntroducao, onFim: avancar, onSair: () => sair('/modulos'), revisao: revisando, bloqueado, salvando, status: <>
    <div className="ipv4-estado" role="status" aria-live="polite">{salvando ? 'Salvando…' : erro ? 'Operação não confirmada' : revisando ? 'Revisão — aula já concluída. Alterações ficam somente nesta visita.' : 'Explore a introdução; as respostas e a conclusão são registradas na sua conta.'}</div>
    {legado && <p className="ipv4-estado">{revisando ? 'As respostas da conclusão antiga não foram armazenadas. Você pode refazer os exercícios sem alterar sua conclusão.' : 'Seu progresso anterior foi preservado, sem inventar respostas.'}</p>}
    {renderErro()}
    <p className="ipv4-estado">{avisoIntroducao || (revisando ? 'Revisão começa pela introdução e não altera sua conclusão.' : 'Posição e escolhas gerais desta introdução são retomadas no mesmo navegador. Respostas das atividades e conclusão ficam na sua conta.')}</p>
  </> }} />

  function renderConteudo() {
    if (etapa === 1) return <div className="aula-bloco">
      <span className="aula-etiqueta">PREVER · ANTES DA PRÁTICA</span>
      <h2>Seu computador quer acessar 8.8.8.8. Qual equipamento recebe o quadro primeiro?</h2>
      <p>O destino está fora de 192.168.10.0/24. Registre sua hipótese sobre a próxima entrega na rede local.</p>
      <div className="modelos-opcoes">{[['gateway', 'O gateway (roteador)'], ['destino', 'O servidor 8.8.8.8 diretamente'], ['switch', 'O switch, que escolhe a rota']].map(([id, texto]) => <label key={id} className={previsao === id ? 'selecionada' : ''}><input type="radio" name="previsao-ipv4" checked={previsao === id} onChange={() => atualizar({ previsao: id })} disabled={bloqueado} />{texto}</label>)}</div>
      {previsao && <div className="fala-link"><strong>Hipótese registrada</strong><p>Na próxima etapa vamos separar o endereço IP de destino do endereço MAC usado no enlace local.</p></div>}
    </div>

    if (etapa === 2) return <div className="aula-bloco">
      <span className="aula-etiqueta">PRATICAR · LER ENDEREÇOS</span>
      <h2>Use o prefixo /24 para analisar a rede</h2>
      <p>Neste exemplo, os três primeiros números formam a parte de rede. O último identifica o host, exceto nos endereços reservados de rede e broadcast.</p>
      <div className="ipv4-destaque-mascara"><code>192.168.10.34/24</code><ArrowRight /><code>255.255.255.0</code></div>
      <div className="ipv4-exercicios">{exercicios.map((item) => <label key={item.id}><strong>{item.pergunta}</strong><select value={respostas[item.id] || ''} disabled={bloqueado} onChange={(evento) => atualizar({ pratica: { [item.id]: evento.target.value } })}><option value="">Selecione uma resposta</option>{item.opcoes.map(([id, texto]) => <option key={id} value={id}>{texto}</option>)}</select></label>)}</div>
      <button className="botao-interacao modelos-validar" disabled={!praticaCompleta || bloqueado} onClick={() => conferir('pratica')}><Check size={17} /> Conferir respostas</button>
      {validada && <div className={`feedback-desafio ${praticaCorreta ? 'sucesso' : ''}`}>{praticaCorreta ? 'Correto! Os dois endereços pertencem a 192.168.10.0/24; destinos fora dela seguem pelo gateway.' : <>Revise os campos indicados. Para /24, 192.168.10.0 é a rede, .255 é o broadcast e .34 e .80 são endereços de host. Para alcançar 8.8.8.8, o computador envia o quadro ao gateway.<ul>{exercicios.filter((item) => estado.validacoes.pratica.erros?.includes(item.id)).map((item) => <li key={item.id}>{item.pergunta} Resposta: {item.correta}.</li>)}</ul></>}</div>}
    </div>

    if (etapa === 3) return <div className="aula-bloco">
      <span className="aula-etiqueta">OBSERVAR · IP, MAC E ARP</span>
      <h2>O pacote segue para fora; o quadro vai até o gateway</h2>
      <p>Veja a diferença entre destino IP e entrega local. Este diagrama explica o processo; não é uma captura do laboratório.</p>
      <div className="ipv4-caminho" aria-label="Computador envia dados ao roteador">
        <article><Network /><strong>Computador</strong><span>IP: 192.168.10.34</span><small>ARP pergunta: quem tem 192.168.10.1?</small></article>
        <div><ArrowRight /><small>Quadro para o MAC do gateway</small></div>
        <article><Router /><strong>Gateway</strong><span>IP local: 192.168.10.1</span><small>Roteia o pacote rumo a 8.8.8.8</small></article>
      </div>
      <div className="ipv4-pacote"><span>Destino IP do pacote</span><strong>8.8.8.8</strong><ArrowRight /><span>Destino MAC do quadro local</span><strong>MAC do gateway</strong></div>
      <p className="modelos-nota">O roteador retira o quadro recebido e cria outro para o próximo enlace. O destino IP continua sendo 8.8.8.8; os endereços MAC usados mudam a cada enlace.</p>
    </div>

    if (etapa === 4) return <div className="aula-bloco">
      <span className="aula-etiqueta">INTERPRETAR · ESCOLHER A ENTREGA</span>
      <h2>Qual endereço o ARP precisa descobrir para começar a rota?</h2>
      <p>Sua hipótese foi: <strong>{({ gateway: 'enviar primeiro ao gateway', destino: 'enviar diretamente ao servidor remoto', switch: 'deixar o switch escolher a rota' })[previsao] || 'não registrada'}</strong>. O IP informa o destino final, mas a primeira entrega ocorre no enlace local.</p>
      <div className="modelos-opcoes">{[['mac-gateway', 'O MAC do gateway 192.168.10.1'], ['mac-remoto', 'O MAC do servidor 8.8.8.8'], ['ip-rede', 'O endereço da rede 192.168.10.0']].map(([id, texto]) => <label key={id} className={interpretacao === id ? 'selecionada' : ''}><input type="radio" name="interpretacao-ipv4" checked={interpretacao === id} onChange={() => atualizar({ interpretacao: id })} disabled={bloqueado} />{texto}</label>)}</div>
      <button className="botao-interacao modelos-validar" disabled={!interpretacao || bloqueado} onClick={() => conferir('interpretacao')}><Check size={17} /> Conferir interpretação</button>
      {interpretacaoValidada && <div className="feedback-desafio sucesso">Isso! O computador usa ARP para localizar o MAC do gateway no enlace local. O pacote IP continua destinado a 8.8.8.8.</div>}
      {interpretacao && interpretacao !== 'mac-gateway' && <div className="feedback-desafio">Pista do Link: ARP resolve endereços IPv4 do enlace local. O servidor remoto está em outra rede.</div>}
    </div>

    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">{revisando ? 'AULA JÁ CONCLUÍDA · REVISÃO' : 'CONCLUIR · MÓDULO 1'}</span>
      <h2>Agora você consegue ler uma configuração IPv4</h2>
      <p className="aula-destaque">O prefixo separa rede e host. O gateway encaminha tráfego para outras redes. ARP encontra o MAC necessário para a entrega no enlace local.</p>
      <div className="resumo-aprendizado"><div><Check /> /24 corresponde à máscara 255.255.255.0.</div><div><Check /> Endereço de rede e broadcast não são hosts comuns.</div><div><Check /> IP aponta ao destino final; MAC serve à entrega local.</div></div>
      <section className="ipv4-terminal-ponte" aria-label="Como observar isso num computador">
        <h3>Como ver isso num computador</h3>
        <p>Nos laboratórios você vai usar o terminal. Estes dois comandos mostram o que estudamos nesta aula:</p>
        <pre className="ipv4-terminal-exemplo"><span>$ ip addr show eth0</span>{'\n'}    inet <b>192.168.10.34/24</b> brd <b>192.168.10.255</b> scope global eth0{'\n'}<span>$ ping 192.168.10.80</span>{'\n'}64 bytes from 192.168.10.80: icmp_seq=1 ttl=64 time=0.21 ms{'\n'}2 packets transmitted, 2 received, 0% packet loss</pre>
        <ul>
          <li><code>ip addr show</code> exibe a interface: na linha <code>inet</code> aparecem o endereço com o prefixo e o broadcast da rede.</li>
          <li><code>ping</code> envia pedidos de eco do protocolo ICMP ao destino e espera as respostas. Se elas voltam, o destino é alcançável; se não, algo no caminho precisa ser investigado.</li>
        </ul>
      </section>
      <div className="fala-link"><strong>Próxima etapa</strong><p>No Laboratório 1 você observa uma rede pronta pelo terminal com esses comandos; no Laboratório 2 monta sua primeira LAN.</p></div>
    </div>
  }

  return <main className="principal pagina-aula aula-modelos-pagina aula-ipv4-pagina">
    <div className="ipv4-estado" role="status" aria-live="polite">
      {salvando ? 'Salvando…' : erro ? 'Operação não confirmada' : revisando ? 'Revisão — aula já concluída. Alterações ficam somente nesta visita.' : 'Progresso salvo'}
    </div>
    {legado && <p className="ipv4-estado">{revisando ? 'As respostas da conclusão antiga não foram armazenadas. Você pode refazer os exercícios sem alterar sua conclusão.' : 'Encontramos progresso antigo, mas sem respostas armazenadas. Retome as atividades para registrar seu aprendizado; o histórico foi preservado.'}</p>}
    {renderErro()}
    <section className="aula-cabecalho"><button className="aula-sair" disabled={salvando} onClick={() => sair()}><ArrowLeft size={18} /> Início</button><div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div><div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div><span className="aula-tempo">12–15 min</span></section>
    <section className="aula-palco"><div className="aula-conteudo">{renderConteudo()}</div><aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={linkExplicando} alt="Link, guia de aprendizagem" /><div className="link-identidade"><strong>Link</strong><span>Aprender · Prever · Praticar · Observar · Interpretar</span></div></div></aside></section>
    <footer className="aula-navegacao"><button className="botao-voltar" onClick={voltar} disabled={bloqueado}><ArrowLeft size={18} /> Etapa anterior</button><div className="aula-passos" aria-label="Progresso da aula">{etapas.map((nome, indice) => <span key={nome} className={indice <= etapa ? 'ativo' : ''} title={nome} />)}</div><button className="botao-avancar" onClick={avancar} disabled={!podeAvancar() || bloqueado}>{salvando ? 'Salvando…' : etapa === total - 1 ? revisando ? 'Finalizar revisão' : 'Concluir aula' : 'Continuar'}<ArrowRight size={18} /></button></footer>
  </main>
}

export default AulaEnderecoIPv4
