import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, RotateCcw } from 'lucide-react'
import { paraNumero } from '../services/aulaPlano'
import { ALINHAMENTOS, BLOCOS_IGUAIS, DEMANDAS, ORDEM_CORRETA, PARES, PAR_SOBREPOSTO, PLANO, PLANO_COM_ERRO, PREFIXO_IGUAL,
  REDE, conferirRede, faixa, hostsUteis, tamanhoBloco } from '../services/aulaVlsm'
import './AulaFundamentosRede.css'
import './AulaGateway.css'
import './AulaFerramentas.css'
import './AulaPlanoEnderecamento.css'
import './AulaVlsm.css'
import { POSES_AULA } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'

const AULA_ID = 'planejamento-vlsm'
const etapas = ['Blocos iguais?', 'Do maior ao menor', 'Alinhamento', 'Montar o plano', 'Sobreposição', 'Conclusão']
const IMAGENS = POSES_AULA
const CORES = { atendimento: '#ff4f6d', vendas: '#2fbf71', financeiro: '#4c9dff', enlace: '#ffb020' }
const PREFIXOS = [24, 25, 26, 27, 28, 29, 30]
const NOME = Object.fromEntries(DEMANDAS.map((d) => [d.id, d.nome]))

function Escolhas({ grupo, opcoes, valor, aoEscolher }) {
  return <div className="ag-opcoes af-escolhas" role="group" aria-label={grupo}>
    {opcoes.map(([v, texto]) => <button key={v} type="button" aria-pressed={valor === v} className={valor === v ? 'ativo' : ''}
      onClick={() => aoEscolher(v)}>{texto}</button>)}
  </div>
}

// Faixa de 256 endereços com os blocos posicionados pelo endereço de rede.
function Faixa({ blocos, rotulo }) {
  const base = paraNumero(REDE.split('/')[0])
  return <div className="ap-faixa av-faixa" aria-label={rotulo}>
    {blocos.map((b) => {
      const [inicio] = faixa(b.rede, b.prefixo)
      return <span key={b.id} style={{ left: `${((inicio - base) / 256) * 100}%`, width: `${(tamanhoBloco(b.prefixo) / 256) * 100}%`,
        background: CORES[b.id] || '#6b7787' }} title={`${b.nome}: ${b.rede}/${b.prefixo}`}>{tamanhoBloco(b.prefixo) >= 32 ? `/${b.prefixo}` : ''}</span>
    })}
  </div>
}

// Referência de tamanhos: endereços do bloco e hosts úteis (tira a rede e o broadcast).
function TabelaPrefixos({ destaque = [] }) {
  return <div className="av-ref" role="table" aria-label="Tamanho de cada prefixo">
    <div role="row" className="av-ref-linha av-ref-cab"><span role="columnheader">Prefixo</span><span role="columnheader">Endereços no bloco</span>
      <span role="columnheader">Hosts úteis</span></div>
    {PREFIXOS.slice(1).map((p) => <div role="row" key={p} className={`av-ref-linha ${destaque.includes(p) ? 'destaque' : ''}`}>
      <span role="cell"><code>/{p}</code></span><span role="cell">{tamanhoBloco(p)}</span><span role="cell">{hostsUteis(p)}</span></div>)}
  </div>
}

export default function AulaVlsm() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(0)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)
  const [erro, setErro] = useState('')
  const [jaConcluida, setJaConcluida] = useState(false)
  const [iguais, setIguais] = useState({})
  const [ordem, setOrdem] = useState([])
  const [alinhamentos, setAlinhamentos] = useState({})
  const [plano, setPlano] = useState({})
  const [par, setPar] = useState('')
  const [conferido, setConferido] = useState({})

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' }).then((r) => r.json()).then((dados) => {
      if (ativo) setJaConcluida(Boolean(dados.progresso?.aulas?.find((a) => a.aula_id === AULA_ID)?.concluida))
    }).catch(() => {})
    return () => { ativo = false }
  }, [])

  const blocoCerto = (b) => Number(plano[`${b.id}-prefixo`]) === b.prefixo && conferirRede(plano[`${b.id}-rede`], b).ok
  const iguaisCerto = iguais.prefixo === PREFIXO_IGUAL && iguais.cabem === 'nao'

  function podeAvancar() {
    if (etapa === 0) return conferido[0] && iguaisCerto
    if (etapa === 1) return conferido[1] && ordem.join() === ORDEM_CORRETA.join()
    if (etapa === 2) return conferido[2] && ALINHAMENTOS.every((a) => alinhamentos[a.rede + a.prefixo] === a.correta)
    if (etapa === 3) return conferido[3] && PLANO.every(blocoCerto)
    if (etapa === 4) return conferido[4] && PAR_SOBREPOSTO.includes(par)
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

  const marcar = () => setConferido({ ...conferido, [etapa]: false })
  const responder = (setter, atual, chave, valor) => { setter({ ...atual, [chave]: valor }); marcar() }
  const retorno = (certo, textoCerto, textoErrado) => conferido[etapa] &&
    <p className={`ag-retorno ${certo ? 'ok' : 'erro'}`}>{certo ? `✓ ${textoCerto}` : `✗ ${textoErrado}`}</p>
  const botaoConferir = (pronto) => <button className="botao-interacao" type="button" disabled={!pronto}
    onClick={() => setConferido({ ...conferido, [etapa]: true })}><Check size={17} /> Conferir</button>
  const listaDemandas = <ul className="av-demandas">{DEMANDAS.map((d) => <li key={d.id}><i style={{ background: CORES[d.id] }} />
    <strong>{d.nome}</strong><span>{d.enderecos} endereços · {d.detalhe}</span></li>)}</ul>

  function conteudo() {
    if (etapa === 0) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MÓDULO 02 · VLSM</span>
        <h1>Blocos iguais servem?</h1>
        <p className="aula-destaque">Na aula anterior, a rede foi dividida em blocos do mesmo tamanho. Isso funciona quando os
          setores são parecidos. Quando um setor tem 100 computadores e outro só precisa de 2 endereços, blocos iguais
          desperdiçam espaço. <strong>VLSM</strong> (máscara de tamanho variável) resolve isso: cada sub-rede recebe o prefixo
          do seu tamanho.</p>
        <section className="ap-como"><strong>Como escolher o tamanho de um bloco</strong>
          <ol><li>Conte os endereços que o setor precisa, <b>incluindo o gateway</b>.</li>
            <li>Procure na tabela o <b>menor</b> prefixo cujos hosts úteis cobrem esse número.</li>
            <li>Hosts úteis = endereços do bloco − 2, porque o primeiro é a <b>rede</b> e o último é o <b>broadcast</b>.</li></ol>
          <p>Exemplo: 40 endereços não cabem num /27 (30 hosts), mas cabem num /26 (62 hosts).</p></section>
        <TabelaPrefixos />
        <h3>A empresa tem {REDE} para quatro necessidades</h3>
        {listaDemandas}
        <article className="af-caso">
          <strong>Com blocos iguais, todos têm o tamanho que o maior pedido exige. Qual prefixo?</strong>
          <Escolhas grupo="Prefixo dos blocos iguais" opcoes={PREFIXOS.map((p) => [p, `/${p} · ${hostsUteis(p)} hosts`])} valor={iguais.prefixo}
            aoEscolher={(v) => responder(setIguais, iguais, 'prefixo', v)} />
          {retorno(iguais.prefixo === PREFIXO_IGUAL, `O Atendimento precisa de 101 endereços: /${PREFIXO_IGUAL}.`, 'Olhe para o maior pedido: quantos hosts ele exige?')}
        </article>
        <article className="af-caso">
          <strong>Num /24 cabem {BLOCOS_IGUAIS} blocos desse tamanho. As quatro necessidades cabem?</strong>
          <Escolhas grupo="Cabem as quatro necessidades" opcoes={[['sim', 'Sim'], ['nao', 'Não']]} valor={iguais.cabem}
            aoEscolher={(v) => responder(setIguais, iguais, 'cabem', v)} />
          {retorno(iguais.cabem === 'nao', 'Dois blocos para quatro pedidos: faltam dois, e o enlace desperdiçaria 124 endereços.', 'Compare a quantidade de blocos com a de pedidos.')}
        </article>
        {conferido[0] && iguaisCerto && <div className="av-comparacao">
          <span>Blocos iguais (/{PREFIXO_IGUAL}): só dois pedidos atendidos</span>
          <Faixa blocos={[{ ...PLANO[0], prefixo: PREFIXO_IGUAL }, { ...PLANO[1], rede: '192.168.60.128', prefixo: PREFIXO_IGUAL }]} rotulo="Blocos iguais" />
          <span>VLSM: cada pedido com o seu tamanho, e ainda sobra espaço</span>
          <Faixa blocos={PLANO} rotulo="Blocos com VLSM" />
        </div>}
        {botaoConferir(iguais.prefixo && iguais.cabem)}
        <p className="ag-fonte">VLSM (máscaras de tamanho variável) no glossário de <i>Redes para Iniciantes</i>, p. 245.</p>
      </div>
    }
    if (etapa === 1) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">DO MAIOR AO MENOR</span>
        <h2>Em que ordem distribuir?</h2>
        <p>Cada bloco já tem o seu prefixo. Agora é preciso decidir a ordem em que eles entram na rede.</p>
        <section className="ap-como"><strong>Por que do maior para o menor?</strong>
          <p>Um bloco grande só pode começar em poucos lugares: um /25 começa em .0 ou em .128, nada no meio. Se um bloco
            pequeno entrar primeiro, por exemplo o Financeiro (/27) em .0, o Atendimento (/25) não pode mais começar em .32 e
            precisa pular para .128, deixando de .32 a .127 sem uso.</p>
          <p>Colocando os grandes primeiro, cada bloco começa logo onde o anterior terminou, sem buracos.</p></section>
        <h3>Clique nas necessidades do maior para o menor</h3>
        <div className="av-ordem">{DEMANDAS.map((d) => <button key={d.id} type="button" disabled={ordem.includes(d.id)}
          onClick={() => { setOrdem([...ordem, d.id]); marcar() }}><i style={{ background: CORES[d.id] }} />{d.nome}
          <small>{d.enderecos} endereços → /{d.prefixo}</small></button>)}</div>
        <ol className="av-escolhida" aria-label="Sua ordem">{ordem.map((id) => <li key={id}>{NOME[id]}</li>)}</ol>
        <button type="button" className="botao-voltar av-limpar" onClick={() => { setOrdem([]); marcar() }} disabled={!ordem.length}>
          <RotateCcw size={15} /> Recomeçar a ordem</button>
        {retorno(ordem.join() === ORDEM_CORRETA.join(), 'Do /25 ao /30: os maiores primeiro.', 'Comece pelo bloco com mais endereços.')}
        {botaoConferir(ordem.length === DEMANDAS.length)}
      </div>
    }
    if (etapa === 2) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">ALINHAMENTO</span>
        <h2>Onde um bloco pode começar?</h2>
        <p>O endereço de rede de um bloco tem todos os bits de host em zero. Na prática, isso quer dizer que um bloco só pode
          começar num <strong>múltiplo do seu tamanho</strong>.</p>
        <div className="ap-especiais">
          <div><code>/26 · 64 endereços</code><strong>Começa em .0, .64, .128 ou .192</strong><p>Todos múltiplos de 64.</p></div>
          <div><code>/27 · 32 endereços</code><strong>Começa em .0, .32, .64, .96…</strong><p>Todos múltiplos de 32.</p></div>
          <div><code>/28 · 16 endereços</code><strong>Começa em .0, .16, .32, .48…</strong><p>Todos múltiplos de 16.</p></div>
        </div>
        <section className="ap-como"><strong>Como conferir</strong>
          <ol><li>Veja o tamanho do bloco pelo prefixo (tabela da primeira etapa).</li>
            <li>Divida o último número do endereço por esse tamanho.</li>
            <li>Divisão exata: o bloco pode começar ali. Sobrou resto: não pode. Ex.: 96 ÷ 32 = 3 (pode); 40 ÷ 16 = 2,5 (não pode).</li></ol></section>
        <h3>Este bloco pode começar aqui?</h3>
        {ALINHAMENTOS.map((a) => <article key={a.rede + a.prefixo} className="af-caso af-caso-linha">
          <strong><code>{a.rede}/{a.prefixo}</code></strong>
          <Escolhas grupo={`${a.rede}/${a.prefixo} é um início válido`} opcoes={[['sim', 'Início válido'], ['nao', 'Não pode começar aí']]}
            valor={alinhamentos[a.rede + a.prefixo]} aoEscolher={(v) => responder(setAlinhamentos, alinhamentos, a.rede + a.prefixo, v)} />
          {retorno(alinhamentos[a.rede + a.prefixo] === a.correta,
            a.correta === 'sim' ? `${a.rede.split('.')[3]} é múltiplo de ${tamanhoBloco(a.prefixo)}.` : `${a.rede.split('.')[3]} não é múltiplo de ${tamanhoBloco(a.prefixo)}.`,
            `Divida o último número por ${tamanhoBloco(a.prefixo)}.`)}
        </article>)}
        {botaoConferir(ALINHAMENTOS.every((a) => alinhamentos[a.rede + a.prefixo]))}
      </div>
    }
    if (etapa === 3) {
      const corretos = PLANO.filter(blocoCerto)
      return <div className="aula-bloco">
        <span className="aula-etiqueta">MONTAR O PLANO</span>
        <h2>O plano de {REDE}</h2>
        <p>Agora junte as três regras e monte o plano completo.</p>
        <section className="ap-como"><strong>Passo a passo</strong>
          <ol><li><b>Prefixo:</b> o menor que cabe a necessidade (tabela abaixo). As linhas já estão do maior para o menor.</li>
            <li><b>Rede do primeiro bloco:</b> o início da rede da empresa, 192.168.60.0.</li>
            <li><b>Rede do próximo bloco:</b> rede do anterior + tamanho do anterior. Ex.: um /25 em .0 ocupa 128 endereços,
              então o próximo começa em .128.</li>
            <li>Confira se o início é múltiplo do tamanho do bloco novo.</li></ol></section>
        <TabelaPrefixos />
        <Faixa blocos={conferido[3] ? corretos : []} rotulo="Blocos já conferidos" />
        <div className="ap-tabela av-tabela" role="table" aria-label="Plano VLSM">
          <div role="row" className="ap-linha ap-cabecalho"><span role="columnheader">Necessidade</span><span role="columnheader">Prefixo</span>
            <span role="columnheader">Rede</span></div>
          {PLANO.map((b) => {
            const r = conferirRede(plano[`${b.id}-rede`], b)
            const prefixoOk = Number(plano[`${b.id}-prefixo`]) === b.prefixo
            return <div role="row" key={b.id} className="ap-linha">
              <span role="cell"><i style={{ background: CORES[b.id] }} />{b.nome}<small>{b.enderecos} end.</small></span>
              <span role="cell"><select aria-label={`Prefixo de ${b.nome}`} value={plano[`${b.id}-prefixo`] || ''}
                className={conferido[3] ? (prefixoOk ? 'ok' : 'erro') : ''}
                onChange={(e) => responder(setPlano, plano, `${b.id}-prefixo`, e.target.value)}>
                <option value="">—</option>{PREFIXOS.map((p) => <option key={p} value={p}>/{p} · {hostsUteis(p)} hosts</option>)}</select>
                {conferido[3] && !prefixoOk && <small>Escolha o menor bloco que comporta {b.enderecos} endereços.</small>}</span>
              <span role="cell"><input aria-label={`Rede de ${b.nome}`} value={plano[`${b.id}-rede`] || ''} spellCheck={false} autoComplete="off"
                className={conferido[3] ? (r.ok ? 'ok' : 'erro') : ''} onChange={(e) => responder(setPlano, plano, `${b.id}-rede`, e.target.value.trim())} />
                {conferido[3] && !r.ok && <small>{r.retorno}</small>}</span>
            </div>
          })}
        </div>
        {conferido[3] && corretos.length === PLANO.length && <p className="ag-retorno ok">✓ Quatro blocos sem sobreposição; de .228 a .255 fica livre para crescer.</p>}
        {botaoConferir(PLANO.every((b) => plano[`${b.id}-prefixo`] && plano[`${b.id}-rede`]))}
      </div>
    }
    if (etapa === 4) {
      return <div className="aula-bloco">
        <span className="aula-etiqueta">SOBREPOSIÇÃO</span>
        <h2>Encontre o erro do plano</h2>
        <p>Um colega montou este plano para 192.168.70.0/24. Dois blocos usam os mesmos endereços: um computador poderia
          receber um endereço que pertence a dois setores.</p>
        <section className="ap-como"><strong>Como achar a sobreposição</strong>
          <ol><li>Para cada bloco, calcule onde ele termina: <b>fim = rede + tamanho − 1</b>.</li>
            <li>Ex.: 192.168.70.0/25 tem 128 endereços e vai de .0 a .127.</li>
            <li>Se um bloco começa antes de o anterior terminar, os dois se sobrepõem.</li></ol></section>
        <h3>Qual par se sobrepõe?</h3>
        <div className="av-erro">{PLANO_COM_ERRO.map((b) => {
          const [inicio, fim] = faixa(b.rede, b.prefixo)
          return <p key={b.id}><strong>{b.nome}</strong> <code>{b.rede}/{b.prefixo}</code>
            {conferido[4] && <span> · de .{inicio % 256} a .{fim % 256}</span>}</p>
        })}</div>
        <Escolhas grupo="Par sobreposto" opcoes={PARES.map((p) => [p.id, `${p.a.nome} × ${p.b.nome}`])} valor={par} aoEscolher={(v) => { setPar(v); marcar() }} />
        {retorno(PAR_SOBREPOSTO.includes(par), 'Vendas vai de .128 a .191 e engole o Financeiro (.160 a .191). Pelo plano certo, o Financeiro começaria em .192.',
          'Calcule onde cada bloco termina: rede + tamanho − 1.')}
        {botaoConferir(Boolean(par))}
      </div>
    }
    return <div className="aula-bloco aula-conclusao">
      <span className="aula-etiqueta">CONCLUSÃO</span>
      <h2>VLSM em quatro regras</h2>
      <div className="resumo-aprendizado">
        <div><Check /> Cada sub-rede recebe o prefixo da sua demanda, contando o gateway.</div>
        <div><Check /> Distribua do maior bloco para o menor.</div>
        <div><Check /> Cada bloco começa num múltiplo do seu tamanho.</div>
        <div><Check /> Confira onde cada bloco termina: nenhum pode invadir outro.</div>
      </div>
      <div className="fala-link"><strong>Link diz:</strong>
        <p>No Laboratório 6 você vai planejar a rede de uma empresa inteira com VLSM e colocar o plano para funcionar.</p>
      </div>
      {jaConcluida && <p className="ag-dica">Você já concluiu esta aula; concluir de novo não concede XP outra vez.</p>}
    </div>
  }

  const progresso = Math.round(((etapa + 1) / etapas.length) * 100)
  return <main className="principal pagina-aula aula-gateway aula-ferramentas aula-plano aula-vlsm">
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
