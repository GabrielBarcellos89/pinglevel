import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { BLOCOS, CLASSIFICAR, DEMANDAS, ESPECIAIS, EXPLICA_ESPECIAIS, FAIXAS_PRIVADAS, explicarClassificacao, OPCOES_ESPECIAIS, PERGUNTAS_HOSTS, PREFIXOS_OPCOES,
  REDE_DIVIDIR, conferirEndereco, hostsUteis, tamanhoBloco } from '../services/aulaPlano'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaPlanoEnderecamento.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'planejamento-enderecamento'
const etapas = ['Público ou privado', 'Endereços especiais', 'Tamanho do bloco', 'Escolher o prefixo', 'Dividir a rede', 'Conclusão']
const IMAGENS = POSES_AULA
const CORES = ['#ff4f6d', '#2fbf71', '#4c9dff', '#ffb020']

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {opcoes.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

export default function AulaPlanoEnderecamento() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [classes, setClasses] = useState({})
  const [especiais, setEspeciais] = useState({})
  const [prefixo, setPrefixo] = useState(24)
  const [hosts, setHosts] = useState({})
  const [demandas, setDemandas] = useState({})
  const [blocos, setBlocos] = useState({})
  const [conferido, setConferido] = useState({})

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const blocoCerto = (i, tipo) => conferirEndereco(blocos[`${i}-${tipo}`], BLOCOS[i][tipo], tipo).ok

  function podeAvancar() {
    if (etapa === 0) return conferido[0] && CLASSIFICAR.every((c) => classes[c.ip] === c.correta)
    if (etapa === 1) return conferido[1] && ESPECIAIS.every((e) => especiais[e.ip] === e.correta)
    if (etapa === 2) return conferido[2] && PERGUNTAS_HOSTS.every((p) => Number(hosts[p.prefixo]) === p.correta)
    if (etapa === 3) return conferido[3] && DEMANDAS.every((d) => demandas[d.setor] === d.correta)
    if (etapa === 4) return conferido[4] && BLOCOS.every((_, i) => blocoCerto(i, 'rede') && blocoCerto(i, 'broadcast'))
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
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 02 · PLANO DE ENDEREÇAMENTO</span>
        <h1>Público ou privado?</h1>
        <p className="aula-destaque">Antes de dividir uma rede, é preciso escolher de onde vêm os endereços. Os
          <strong> privados</strong> são reservados para redes internas e podem se repetir em empresas diferentes; não
          são roteados na Internet, e o roteador de saída os traduz (NAT). Os <strong>públicos</strong> são únicos na Internet.</p>
        <h3>As três faixas privadas</h3>
        <div className="ap-faixas">{FAIXAS_PRIVADAS.map((f) => <div key={f.rede}><strong>{f.rede}</strong><span>{f.de} a {f.ate}</span>
          <p>{f.regra}</p><small>{f.exemplos}</small></div>)}</div>
        <section className="ap-como"><strong>Como conferir um endereço</strong>
          <ol><li>Olhe o <b>primeiro número</b>. Se não for 10, 172 ou 192, já é público.</li>
            <li>Se for <b>172</b>, olhe o segundo: só de 16 a 31 é privado.</li>
            <li>Se for <b>192</b>, o segundo precisa ser exatamente <b>168</b>.</li>
            <li>Todo o resto é <b>público</b>: único na Internet, como 8.8.8.8.</li></ol></section>
        <h3>Classifique cada endereço</h3>
        {CLASSIFICAR.map((c) => <article key={c.ip} className="af-caso af-caso-linha">
          <strong><code>{c.ip}</code></strong>
          <Escolhas grupo={`Tipo de ${c.ip}`} opcoes={[['privado', 'Privado'], ['publico', 'Público']]} valor={classes[c.ip]}
            aoEscolher={(v) => responder(setClasses, classes, c.ip, v)} />
          {retorno(classes[c.ip] === c.correta, explicarClassificacao(c.ip), `Reveja: ${explicarClassificacao(c.ip)}`)}
        </article>)}
        {botaoConferir(CLASSIFICAR.every((c) => classes[c.ip]))}
        <p className="ag-fonte">Faixas da RFC 1918 em <i>Redes para Iniciantes</i>, p. 78.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">ENDEREÇOS ESPECIAIS</span>
        <h2>Endereços que não vão para um computador comum</h2>
        <p>Alguns endereços têm uma função reservada e não podem ser dados a um computador da rede. Leia a regra de cada um
          e depois associe os exemplos.</p>
        <div className="ap-especiais">{EXPLICA_ESPECIAIS.map((e) => <div key={e.nome}><code>{e.faixa}</code><strong>{e.nome}</strong><p>{e.texto}</p></div>)}</div>
        <h3>Associe cada endereço ao seu papel</h3>
        {ESPECIAIS.map((e) => <article key={e.ip} className="af-caso">
          <strong><code>{e.ip}</code>{e.contexto && <small className="ap-contexto"> {e.contexto}</small>}</strong>
          <Escolhas grupo={`Papel de ${e.ip}`} opcoes={OPCOES_ESPECIAIS} valor={especiais[e.ip]}
            aoEscolher={(v) => responder(setEspeciais, especiais, e.ip, v)} />
          {retorno(especiais[e.ip] === e.correta, `Correto. ${e.porque}`, 'Ainda não. Volte à regra: comece pelo primeiro número, ou pelo último se for o fim da rede.')}
        </article>)}
        {botaoConferir(ESPECIAIS.every((e) => especiais[e.ip]))}
        <p className="ag-fonte">Endereços especiais em <i>Redes para Iniciantes</i>, p. 77–78.</p>
      </div>
    }
    if (etapa === 2) {
      const quantos = 256 / tamanhoBloco(prefixo)
      return <div className="aula-bloco">
        <span className="aula-etiqueta">TAMANHO DO BLOCO</span>
        <h2>Quantos endereços cabem?</h2>
        <p>O prefixo diz quantos dos 32 bits são de rede; o que sobra é de host. Com <code>h</code> bits de host, o bloco
          tem 2<sup>h</sup> endereços. Dois não vão para computadores: o primeiro é o endereço da rede e o último, o broadcast.</p>
        <div className="ap-controle">
          <label htmlFor="ap-prefixo">Prefixo <strong>/{prefixo}</strong></label>
          <input id="ap-prefixo" type="range" min="24" max="30" value={prefixo} onChange={(e) => setPrefixo(Number(e.target.value))} />
          <dl>
            <div><dt>bits de host</dt><dd>{32 - prefixo}</dd></div>
            <div><dt>endereços no bloco</dt><dd>{tamanhoBloco(prefixo)}</dd></div>
            <div><dt>hosts úteis</dt><dd>{hostsUteis(prefixo)}</dd></div>
            <div><dt>blocos num /24</dt><dd>{quantos}</dd></div>
          </dl>
          <div className="ap-faixa" aria-label={`Um /24 dividido em ${quantos} blocos /${prefixo}`}>
            {Array.from({ length: quantos }, (_, i) => <span key={i} style={{ background: CORES[i % 4] }} />)}
          </div>
        </div>
        <h3>Quantos hosts úteis tem cada prefixo?</h3>
        {PERGUNTAS_HOSTS.map((p) => <article key={p.prefixo} className="af-caso af-caso-linha">
          <label htmlFor={`ap-hosts-${p.prefixo}`}><code>/{p.prefixo}</code></label>
          <input id={`ap-hosts-${p.prefixo}`} className="ap-numero" inputMode="numeric" value={hosts[p.prefixo] || ''}
            onChange={(e) => responder(setHosts, hosts, p.prefixo, e.target.value.replace(/\D/g, ''))} />
          {retorno(Number(hosts[p.prefixo]) === p.correta, `2^${32 - p.prefixo} − 2 = ${p.correta}.`, 'Calcule 2 elevado aos bits de host e tire 2.')}
        </article>)}
        {botaoConferir(PERGUNTAS_HOSTS.every((p) => hosts[p.prefixo]))}
        <p className="ag-fonte">Prefixo e quantidade de endereços em <i>Redes para Iniciantes</i>, p. 75–76.</p>
      </div>
    }
    if (etapa === 3) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">ESCOLHER O PREFIXO</span>
        <h2>Cada setor, o bloco que atende</h2>
        <p>Para dimensionar uma sub-rede, conte os computadores <strong>e o gateway</strong>, que também usa um endereço. Escolha o
          menor bloco que atende: o maior prefixo cujos hosts úteis bastam.</p>
        {DEMANDAS.map((d) => <article key={d.setor} className="af-caso">
          <strong>{d.setor}: {d.computadores} computadores + o gateway</strong>
          <Escolhas grupo={`Prefixo para ${d.setor}`} opcoes={PREFIXOS_OPCOES.map((p) => [p, `/${p} · ${hostsUteis(p)} hosts`])}
            valor={demandas[d.setor]} aoEscolher={(v) => responder(setDemandas, demandas, d.setor, v)} />
          {retorno(demandas[d.setor] === d.correta, `Precisa de ${d.computadores + 1} endereços; /${d.correta} tem ${hostsUteis(d.correta)}.`,
            demandas[d.setor] > d.correta ? `Esse bloco não comporta ${d.computadores + 1} endereços.` : 'Atende, mas sobra demais: existe um bloco menor que basta.')}
        </article>)}
        {botaoConferir(DEMANDAS.every((d) => demandas[d.setor]))}
      </div>
    }
    if (etapa === 4) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">DIVIDIR A REDE</span>
        <h2>Quatro setores em {REDE_DIVIDIR}</h2>
        <p>A empresa recebeu {REDE_DIVIDIR} e quer quatro sub-redes iguais, uma por setor. Quatro blocos num /24 dão
          blocos /26 de 64 endereços. Escreva a rede e o broadcast de cada um.</p>
        <div className="ap-faixa ap-faixa-divisao" aria-hidden="true">{BLOCOS.map((b, i) => <span key={b.rede} style={{ background: CORES[i] }}>/26</span>)}</div>
        <div className="ap-tabela" role="table" aria-label="Sub-redes /26">
          <div role="row" className="ap-linha ap-cabecalho"><span role="columnheader">Bloco</span><span role="columnheader">Rede</span>
            <span role="columnheader">Broadcast</span></div>
          {BLOCOS.map((b, i) => <div role="row" key={b.rede} className="ap-linha">
            <span role="cell"><i style={{ background: CORES[i] }} />{i + 1}º /26</span>
            {['rede', 'broadcast'].map((tipo) => {
              const r = conferirEndereco(blocos[`${i}-${tipo}`], b[tipo], tipo)
              return <span role="cell" key={tipo}>
                <input aria-label={`${tipo === 'rede' ? 'Rede' : 'Broadcast'} do bloco ${i + 1}`} value={blocos[`${i}-${tipo}`] || ''}
                  spellCheck={false} autoComplete="off" className={conferido[4] ? (r.ok ? 'ok' : 'erro') : ''}
                  onChange={(e) => responder(setBlocos, blocos, `${i}-${tipo}`, e.target.value.trim())} />
                {conferido[4] && !r.ok && <small>{r.retorno}</small>}
              </span>
            })}
          </div>)}
        </div>
        {conferido[4] && podeAvancar() && <p className="ag-retorno ok">✓ Hosts úteis do 1º bloco: {BLOCOS[0].primeiroHost} a {BLOCOS[0].ultimoHost}. Sem sobreposição e sem sobra.</p>}
        {botaoConferir(BLOCOS.every((_, i) => blocos[`${i}-rede`] && blocos[`${i}-broadcast`]))}
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>Do plano à rede</h2>
      <div className="resumo-aprendizado">
        <div><Check /> Redes internas usam faixas privadas: 10/8, 172.16/12 e 192.168/16.</div>
        <div><Check /> Loopback, link-local, 0.0.0.0, rede e broadcast não vão para computadores.</div>
        <div><Check /> Com h bits de host, o bloco tem 2<sup>h</sup> endereços e 2<sup>h</sup> − 2 hosts úteis.</div>
        <div><Check /> Dimensione pela demanda, contando o gateway, e divida sem sobrepor blocos.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 5 você vai dividir uma rede entre setores de verdade: configurar o roteador e os computadores de
          cada sub-rede e comprovar onde termina cada bloco.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas aula-plano">
    <section className="aula-cabecalho">
      <button className="aula-sair" onClick={() => navigate('/modulos')}><ArrowLeft size={18} /> Sair da aula</button>
      <div className="aula-progresso-area"><div><span>{etapas[etapa]}</span><strong>{progresso}%</strong></div>
        <div className="aula-progresso"><div style={{ width: `${progresso}%` }} /></div></div>
      <span className="aula-tempo">15–18 min</span>
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
