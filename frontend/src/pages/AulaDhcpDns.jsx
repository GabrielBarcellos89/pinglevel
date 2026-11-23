import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { CASOS_DNS, CONCESSAO, DORA, LINHAS_CONCESSAO, MENSAGENS_DORA, LEITURA_CONCESSAO, OBJETIVOS, PROBLEMAS, conferirComandoServicos } from '../services/aulaDhcpDns'
import AjudaComando from '../components/aula/AjudaComando'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaRoteamento.css'
import './AulaExplicacao.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'servicos-dhcp-dns'
const etapas = ['Por que automático', 'As quatro mensagens', 'A concessão', 'Nomes e endereços', 'Montar comandos', 'Conclusão']
const IMAGENS = POSES_AULA
// Etapas de perguntas: lista e a dica quando a resposta não confere.
const QUIZ = {
  0: [PROBLEMAS, 'O DHCP entrega a configuração; não resolve o que acontece antes dela, no cabo.'],
  1: [DORA, 'O cliente começa sem endereço e sem saber quem é o servidor.'],
  2: [LEITURA_CONCESSAO, 'Releia a saída: quem emprestou, o quê e por quanto tempo.'],
  3: [CASOS_DNS, 'Compare: o servidor respondeu? E o ping pelo IP funciona?'],
}

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {opcoes.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

export default function AulaLan() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [respostas, setRespostas] = useState({})
  const [comandos, setComandos] = useState({})
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
    if (etapa === 4) return conferido[4] && OBJETIVOS.every((o) => conferirComandoServicos(o, comandos[o.id]).ok)
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
        {q.saida && <pre className="af-terminal">{q.saida}</pre>}
        <strong>{q.pergunta || q.descricao}</strong>
        <Escolhas grupo={q.saida ? `${q.pergunta} (caso ${q.id})` : q.pergunta || q.descricao} opcoes={q.opcoes} valor={respostas[chave(q)]}
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
        <span className="aula-etiqueta">MÓDULO 03 · DHCP E DNS</span>
        <h1>Endereços e nomes automáticos</h1>
        <p className="aula-destaque">Configurar cinquenta computadores à mão é pedir para errar. O DHCP entrega a cada um
          endereço, máscara, gateway e servidores DNS; o DNS traduz nomes, como intranet.empresa.local, em endereços IP.</p>
        <div className="aula-explica">
          <h3>O que cada computador precisa</h3>
          <p>Para funcionar na rede, todo computador precisa de quatro informações: um <b>endereço IP</b> só dele, a <b>máscara</b>
            (o prefixo), o <b>gateway</b> (a saída para outras redes) e o <b>servidor DNS</b> (quem traduz nomes em endereços).</p>
          <h3>À mão, os erros aparecem</h3>
          <ul>
            <li>Alguém usa um endereço que já está em outro computador, e os dois passam a falhar.</li>
            <li>Um número do gateway é digitado errado, e aquele computador não sai da rede.</li>
            <li>O servidor DNS fica sem configurar, e os nomes param de funcionar.</li>
          </ul>
          <h3>Com DHCP</h3>
          <p>Um <b>servidor DHCP</b> guarda uma faixa de endereços livres (no exemplo, de .100 a .150) e anota cada um que empresta:
            assim, nunca entrega o mesmo endereço a dois computadores. Junto com o endereço, ele manda a máscara, o gateway e o
            servidor DNS, iguais para todos. O computador só precisa pedir.</p>
          <h3>O que o DHCP não resolve</h3>
          <p>O pedido viaja pela rede. Se o cabo está desconectado (sem enlace), o pedido nem sai do computador, e o servidor
            nunca fica sabendo dele. Problemas físicos continuam sendo resolvidos no cabo e na porta.</p>
        </div>
        <h3>Confira: o que o DHCP evita?</h3>
        {perguntas()}
        <p className="ag-fonte">DHCP e DNS em <i>Redes para Iniciantes</i>, p. 63.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">AS QUATRO MENSAGENS</span>
        <h2>Como um computador sem endereço pede um</h2>
        <p>Ao ligar, o computador não tem endereço e não sabe quem é o servidor DHCP. Ele procura, recebe uma oferta, pede
          aquele endereço e recebe a confirmação.</p>
        <div className="aula-explica">
          <h3>As quatro mensagens, em ordem</h3>
          <ol>{MENSAGENS_DORA.map(([nome, quem, texto]) => <li key={nome}><b>{nome}</b> · {quem}<br />{texto}</li>)}</ol>
          <p>As iniciais em inglês formam <b>DORA</b>: Discover, Offer, Request, Ack.</p>
          <h3>Por que broadcast</h3>
          <p>Na descoberta, o computador não sabe o endereço do servidor. Então manda para <b>todos</b> da rede local: o broadcast
            (destino 255.255.255.255). Só o servidor DHCP responde.</p>
          <h3>Por que a origem 0.0.0.0</h3>
          <p>Todo pacote IP leva um endereço de origem. Como o computador ainda não tem um, usa <code>0.0.0.0</code>, que quer
            dizer “ainda não tenho endereço”.</p>
          <h3>Por que UDP</h3>
          <p>Na aula Transporte você viu que o TCP abre uma conexão entre dois endereços conhecidos antes de enviar dados. Aqui o
            cliente não tem endereço e fala com todos em broadcast: não há com quem abrir conexão. Por isso o DHCP usa UDP
            (porta 67 no servidor e 68 no cliente).</p>
        </div>
        <h3>Confira</h3>
        {perguntas()}
        <p className="ag-fonte">Broadcast e 0.0.0.0 em <i>Redes para Iniciantes</i>, p. 36 e 78; DHCP sobre UDP, p. 91.</p>
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">A CONCESSÃO</span>
        <h2>Lendo o que o servidor entregou</h2>
        <p>O pedido é feito com o <code>dhclient</code>, o cliente DHCP. Esta é a saída de um pedido:</p>
        <pre className="af-terminal"><span className="af-prompt">pc$ dhclient eth0</span>{'\n'}{CONCESSAO}</pre>
        <p className="ag-dica">As linhas começam com “udhcpc:” porque, nos computadores do laboratório, quem faz o pedido por
          dentro é o <code>udhcpc</code>, outro cliente DHCP. O comando <code>udhcpc -i eth0</code> também funciona.</p>
        <div className="aula-explica">
          <h3>Linha a linha</h3>
          <ul className="al-comandos">{LINHAS_CONCESSAO.map(([linha, explicacao]) => <li key={linha}><code>{linha}</code><span>{explicacao}</span></li>)}</ul>
          <h3>Concessão: um empréstimo com prazo</h3>
          <p>O endereço não passa a ser do computador para sempre. O servidor o <b>empresta</b> por um tempo, o <i>lease time</i>,
            em segundos: 3600 s é uma hora. Antes de vencer, o computador pede para renovar. Se ele sai da rede e não renova, o
            endereço volta para a faixa livre e pode ir para outro.</p>
          <h3>Para onde vai o DNS</h3>
          <p>O servidor DNS recebido é gravado no arquivo <code>/etc/resolv.conf</code>, numa linha <code>nameserver</code>. É esse
            arquivo que o computador consulta sempre que precisa traduzir um nome.</p>
          <h3>E se ninguém responder?</h3>
          <p>Sem resposta de um servidor DHCP, muitos sistemas se dão sozinhos um endereço da faixa <code>169.254.0.0/16</code>.
            Ver um 169.254.x.x é sinal de que o DHCP falhou: o computador fala no máximo com vizinhos na mesma situação.</p>
        </div>
        <h3>Confira</h3>
        {perguntas()}
        <p className="ag-fonte">169.254.0.0/16 em <i>Redes para Iniciantes</i>, p. 77; <code>dhclient</code> em <i>Linux: Utilitários de Redes</i>, p. 24.</p>
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">NOMES E ENDEREÇOS</span>
        <h2>Quando o nome não funciona</h2>
        <p>O computador pergunta ao servidor DNS do <code>/etc/resolv.conf</code> e recebe o endereço. Se o nome falha,
          há três suspeitos: o nome, o servidor DNS configurado ou a rede até ele. Testar pelo IP separa os casos.</p>
        <div className="aula-explica">
          <h3>Perguntando ao DNS</h3>
          <p>O <code>nslookup</code> pergunta ao servidor DNS o endereço de um nome. Quando dá certo, a resposta traz o nome e o
            endereço (<code>Address: 192.168.40.20</code>).</p>
          <h3>As três falhas e como reconhecer</h3>
          <ul>
            <li><b>NXDOMAIN</b> (“non-existent domain”): o servidor <b>respondeu</b>, dizendo que esse nome não existe. A rede e o
              servidor estão bem; confira a grafia do nome.</li>
            <li><b>connection timed out; no servers could be reached</b>: <b>nenhum</b> servidor respondeu. Ou o computador consulta
              o servidor errado (veja o <code>nameserver</code> no <code>/etc/resolv.conf</code>), ou nem alcança a rede.</li>
            <li>Para separar esses dois, faça <b>ping pelo endereço IP</b>. Se o ping pelo IP responde, a rede está boa e o problema
              é o DNS. Se aparece <code>Network unreachable</code>, o computador nem tem caminho para a rede: comece pelo endereço
              e pela rota.</li>
          </ul>
        </div>
        <h3>Confira: o que aconteceu em cada caso?</h3>
        {perguntas()}
        <p className="ag-fonte"><code>nslookup</code> e <code>dig</code> em <i>Linux: Utilitários de Redes</i>, p. 17–18; DNS na porta 53/UDP em <i>Redes para Iniciantes</i>, p. 91.</p>
      </div>
    }
    if (etapa === 4) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MONTAR COMANDOS</span>
        <h2>Pedir endereço e testar nomes</h2>
        <p>Escreva o comando para cada objetivo. Nada é executado: aqui você confere a forma que vai usar no Laboratório 9.</p>
        {OBJETIVOS.map((o) => {
          const r = conferirComandoServicos(o, comandos[o.id])
          return <article key={o.id} className="af-caso">
            <label htmlFor={`ad-${o.id}`}>{o.texto}</label>
            <div className="af-comando"><span aria-hidden="true">$</span>
              <input id={`ad-${o.id}`} value={comandos[o.id] || ''} spellCheck={false} autoComplete="off" autoCapitalize="none"
                onChange={(e) => { setComandos({ ...comandos, [o.id]: e.target.value }); setConferido({ ...conferido, 4: false }) }} /></div>
            {conferido[4] && <p className={`ag-retorno ${r.ok ? 'ok' : 'erro'}`}>{r.ok ? '✓ ' : '✗ '}{r.retorno || 'Escreva o comando.'}</p>}
            {!r.ok && <AjudaComando ajuda={o.ajuda} />}
          </article>
        })}
        {botaoConferir(OBJETIVOS.every((o) => (comandos[o.id] || '').trim()))}
        <p className="ag-fonte">Formas em <i>Linux: Utilitários de Redes</i>, p. 17–19, 24 e 83.</p>
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>DHCP e DNS em quatro ideias</h2>
      <div className="resumo-aprendizado">
        <div><Check /> O DHCP empresta endereço, máscara, gateway e DNS por um tempo (a concessão).</div>
        <div><Check /> Sem endereço, o cliente procura o servidor em broadcast, com origem 0.0.0.0.</div>
        <div><Check /> 169.254.x.x indica que nenhum servidor DHCP respondeu.</div>
        <div><Check /> Se o IP responde e o nome não, o problema é DNS; se nem o IP responde, comece pela rede.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 9 você atende chamados de uma rede com DHCP e DNS: computador sem endereço, nome que não resolve
          e um servidor DNS errado.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas aula-roteamento">
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate('/modulos')}><ArrowLeft size={18} /> Sair da aula</button>
      <div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div>
        <div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div>
      <span className="aula-tempo">12–15 min</span>
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
