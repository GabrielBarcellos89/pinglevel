import { Fragment, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { CAUSAS_MENSAGEM, DESTINOS_TABELA, MENSAGENS, OBJETIVOS, OPCOES_INTERFACE, SAIDA_INTERFACE, SITUACOES_INTERFACE,
  TABELA, conferirComando } from '../services/aulaFerramentas'
import AjudaComando from '../components/aula/AjudaComando'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'fundamentos-ferramentas'
const etapas = ['Ler a interface', 'Diagnosticar', 'Tabela de rotas', 'Montar comandos', 'Mensagens', 'Conclusão']
const IMAGENS = POSES_AULA

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {opcoes.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

export default function AulaFerramentas() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [parteAberta, setParteAberta] = useState('')
  const [vistas, setVistas] = useState([])
  const [situacoes, setSituacoes] = useState({})
  const [rotas, setRotas] = useState({})
  const [comandos, setComandos] = useState({})
  const [mensagens, setMensagens] = useState({})
  const [conferido, setConferido] = useState({})

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const tudoCerto = (lista, respostas, chave) => lista.every((item) => respostas[item[chave]] === item.correta)
  const comandosCertos = OBJETIVOS.every((o) => conferirComando(o, comandos[o.id]).ok)

  function podeAvancar() {
    if (etapa === 0) return vistas.length === SAIDA_INTERFACE.length
    if (etapa === 1) return conferido[1] && tudoCerto(SITUACOES_INTERFACE, situacoes, 'id')
    if (etapa === 2) return conferido[2] && tudoCerto(DESTINOS_TABELA, rotas, 'ip')
    if (etapa === 3) return conferido[3] && comandosCertos
    if (etapa === 4) return conferido[4] && tudoCerto(MENSAGENS, mensagens, 'mensagem')
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

  const responder = (setter, atual, chave, valor) => { setter({ ...atual, [chave]: valor }); setConferido({ ...conferido, [etapa]: false }) }
  const retorno = (certo, textoCerto, textoErrado) => conferido[etapa] &&
    <p className={`ag-retorno ${certo ? 'ok' : 'erro'}`}>{certo ? `✓ ${textoCerto}` : `✗ ${textoErrado}`}</p>
  const botaoConferir = (pronto) => <button className="botao-interacao" type="button" disabled={!pronto}
    onClick={() => setConferido({ ...conferido, [etapa]: true })}><Check size={17} /> Conferir</button>

  function conteudo() {
    if (etapa === 0) {
      const aberta = SAIDA_INTERFACE.find((p) => p.id === parteAberta)
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 01 · FERRAMENTAS</span>
        <h1>Ler a interface</h1>
        <p className="aula-destaque">O comando <code>ip addr show eth0</code> mostra como está a interface de rede. Clique em
          cada parte da saída para entender o que ela diz.</p>
        <pre className="af-terminal" aria-label="Saída de ip addr show eth0"><span className="af-prompt">$ ip addr show eth0</span>{'\n'}
          {SAIDA_INTERFACE.map((p) => <Fragment key={p.id}><button type="button" className={`af-trecho ${parteAberta === p.id ? 'ativo' : ''} ${vistas.includes(p.id) ? 'visto' : ''}`}
            onClick={() => { setParteAberta(p.id); if (!vistas.includes(p.id)) setVistas([...vistas, p.id]) }}>{p.trecho}</button>{p.id === 'inet' ? '' : '\n'}</Fragment>)}
        </pre>
        {aberta && <section className="ag-decisao" aria-live="polite"><p>{aberta.explicacao}</p></section>}
        {vistas.length < SAIDA_INTERFACE.length && <p className="ag-dica">Explore as {SAIDA_INTERFACE.length} partes para continuar ({vistas.length} de {SAIDA_INTERFACE.length}).</p>}
        <p className="ag-fonte">Comandos em <i>Linux: Utilitários de Redes</i>, p. 13.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">DIAGNOSTICAR</span>
        <h2>O que cada saída revela?</h2>
        <p>Três computadores responderam a <code>ip addr show eth0</code>. Associe cada saída à situação.</p>
        {SITUACOES_INTERFACE.map((s, i) => <article key={s.id} className="af-caso">
          <strong>Computador {i + 1}</strong>
          <pre className="af-terminal">{s.saida}</pre>
          <Escolhas grupo={`Situação do computador ${i + 1}`} opcoes={OPCOES_INTERFACE} valor={situacoes[s.id]}
            aoEscolher={(v) => responder(setSituacoes, situacoes, s.id, v)} />
          {retorno(situacoes[s.id] === s.correta, 'Correto.', 'Procure UP na primeira linha e uma linha inet.')}
        </article>)}
        {botaoConferir(SITUACOES_INTERFACE.every((s) => situacoes[s.id]))}
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">TABELA DE ROTAS</span>
        <h2>Ler a tabela de rotas</h2>
        <p>O comando <code>ip route show</code> lista os caminhos que o computador conhece. Cada pacote usa a linha
          que corresponde ao destino; se nenhuma rede corresponder, vale a rota padrão.</p>
        <pre className="af-terminal"><span className="af-prompt">$ ip route show</span>{'\n'}{TABELA.map((t) => t.linha).join('\n')}</pre>
        <div className="af-explicacoes">{TABELA.map((t) => <p key={t.id}><code>{t.linha.split(' ')[0]}</code> {t.explicacao}</p>)}</div>
        <h3>Qual linha cada destino usa?</h3>
        {DESTINOS_TABELA.map((d) => <article key={d.ip} className="af-caso af-caso-linha">
          <strong><code>{d.ip}</code></strong>
          <Escolhas grupo={`Rota para ${d.ip}`} opcoes={[['local', '192.168.10.0/24 (direto)'], ['padrao', 'default (gateway)']]}
            valor={rotas[d.ip]} aoEscolher={(v) => responder(setRotas, rotas, d.ip, v)} />
          {retorno(rotas[d.ip] === d.correta, d.correta === 'local' ? 'Está na própria rede: entrega direta.' : 'Fora da própria rede: vai pela rota padrão.',
            'Compare os três primeiros números com 192.168.10.')}
        </article>)}
        {botaoConferir(DESTINOS_TABELA.every((d) => rotas[d.ip]))}
        <p className="ag-fonte">Tabela de roteamento em <i>Redes para Iniciantes</i>, p. 154–155.</p>
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MONTAR COMANDOS</span>
        <h2>Configurar pelo terminal</h2>
        <p>Escreva o comando para cada objetivo. Nada é executado: aqui você só confere a forma, que vai usar no Laboratório 4.
          Se travar, peça ajuda ao Link em cada objetivo: ele explica as partes, mostra o exemplo do livro e dá uma pista.</p>
        {OBJETIVOS.map((o) => {
          const r = conferirComando(o, comandos[o.id])
          return <article key={o.id} className="af-caso">
            <label htmlFor={`af-${o.id}`}>{o.texto}</label>
            <div className="af-comando"><span aria-hidden="true">$</span>
              <input id={`af-${o.id}`} value={comandos[o.id] || ''} spellCheck={false} autoComplete="off" autoCapitalize="none"
                onChange={(e) => responder(setComandos, comandos, o.id, e.target.value)} /></div>
            {conferido[3] && <p className={`ag-retorno ${r.ok ? 'ok' : 'erro'}`}>{r.ok ? '✓ ' : '✗ '}{r.retorno || 'Escreva o comando.'}</p>}
            {!r.ok && <AjudaComando ajuda={o.ajuda} />}
          </article>
        })}
        {botaoConferir(OBJETIVOS.every((o) => (comandos[o.id] || '').trim()))}
        <p className="ag-fonte">Formas em <i>Linux: Utilitários de Redes</i>, p. 12–13.</p>
      </div>
    }
    if (etapa === 4) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MENSAGENS DO SISTEMA</span>
        <h2>O que o terminal está dizendo?</h2>
        <p>Quando algo dá errado, o sistema responde com uma mensagem. Associe cada uma à causa provável.</p>
        {MENSAGENS.map((m) => <article key={m.mensagem} className="af-caso">
          <pre className="af-terminal">{m.mensagem}</pre>
          <Escolhas grupo={`Causa de ${m.mensagem}`} opcoes={CAUSAS_MENSAGEM} valor={mensagens[m.mensagem]}
            aoEscolher={(v) => responder(setMensagens, mensagens, m.mensagem, v)} />
          {retorno(mensagens[m.mensagem] === m.correta, 'Isso.', 'Releia a mensagem: ela fala do caminho, da resposta, do gateway ou do endereço?')}
        </article>)}
        {botaoConferir(MENSAGENS.every((m) => mensagens[m.mensagem]))}
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>Observar, corrigir e testar</h2>
      <div className="resumo-aprendizado">
        <div><Check /> <code>ip addr show</code>: a interface está ativa? tem endereço e prefixo?</div>
        <div><Check /> <code>ip route show</code>: existe a rota da própria rede e a rota padrão?</div>
        <div><Check /> <code>ip addr add/del</code> e <code>ip route add/del default</code> corrigem a configuração.</div>
        <div><Check /> <code>ping</code> comprova; as mensagens de erro apontam onde investigar.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 4 você atende chamados de suporte: computadores com problemas diferentes que você vai investigar
          e corrigir pelo terminal, usando exatamente esses comandos.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas">
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
