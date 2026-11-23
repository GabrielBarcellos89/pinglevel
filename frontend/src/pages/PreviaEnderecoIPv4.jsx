import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Computer, Network } from 'lucide-react'
import linkEnsinando from '../assets/mascote/link-kit-v2/link-v2-ensinando.webp'
import { POSES } from '../assets/mascote/poses'
import linkConectando from '../assets/mascote/link-expansao-v1/link-conectando.webp'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import linkComemorando from '../assets/mascote/link-kit-v2/link-v2-comemorando.webp'
import { calcularRede, dividirRedeDidatica, calcularDivisao, avaliarLAN, PREFIXOS_DIDATICOS, PREFIXOS_LEITURA } from '../services/previaIPv4'
import './AulaFundamentosRede.css'
import './AulaModelosRede.css'
import './PreviaEnderecoIPv4.css'
import ExploradorMascara from './ExploradorMascara'
import './ExploradorMascara.css'

const linkPensando = POSES.pensativo
const linkObservando = POSES.curioso

const IP_A = '192.168.10.10'
const ETAPAS = ['Nossa primeira rede', 'Endereço e host', 'A máscara', 'Rede, hosts e broadcast', 'Monte uma LAN simulada', 'Divida em sub-redes', 'O que descobrimos']
const TITULOS = ['Como dois computadores entram na mesma rede?', 'Um endereço para cada interface', 'A máscara desenha o limite', 'Quais endereços posso usar?', 'Agora monte sua primeira LAN', 'Uma rede pode virar redes menores', 'Da configuração ao planejamento']
const FALAS = [
  'Vamos conectar dois computadores e escolher seus endereços. Antes, precisamos descobrir o que identifica a rede e quais endereços podem ser usados pelos hosts.',
  'Aqui observamos uma interface de cada computador. Neste primeiro exemplo /24, os três primeiros números identificam a rede; o último diferencia os hosts.',
  'Vamos por partes: primeiro o que é um bit, depois o significado do prefixo e, por fim, como os grupos de bits formam a máscara. Escolha um prefixo e avance nos três passos abaixo.',
  'Nesta LAN, o primeiro endereço identifica a rede e o último é o broadcast. Os endereços entre eles podem ser atribuídos às interfaces. Mude a máscara e observe a faixa diminuir.',
  'O Computador 1 já tem um IPv4 de referência. Conecte os computadores ao switch, escolha o endereço do segundo e aplique uma máscara aos dois. Depois teste sua configuração nesta simulação.',
  'Escolha o prefixo de origem e o prefixo das partes. Nas LANs convencionais, cada parte tem sua rede, hosts e broadcast. Você também pode explorar os usos especiais de /31 e /32.',
  'Primeiro entendemos o endereço, depois a máscara e a capacidade. Já podemos montar uma LAN simples e começar a planejar como distribuir endereços em sub-redes.',
]

function Prefixos({ valor, onChange, subdivisao = false, minimo = 8 }) {
  const opcoes = (subdivisao ? PREFIXOS_DIDATICOS : PREFIXOS_LEITURA).filter((p) => p >= minimo)
  const atalhos = (subdivisao ? [25, 26] : [16, 24, 26, 30]).filter((p) => p >= minimo)
  return <div className="v4-prefixos"><label><span>{subdivisao ? 'Prefixo das partes' : 'Explore de /8 até /32'}</span><select aria-label={subdivisao ? 'Prefixo das partes' : 'Prefixo em estudo'} value={valor} onChange={(e) => onChange(Number(e.target.value))}>{opcoes.map((p) => <option key={p} value={p}>/{p} · {calcularRede(IP_A, p).mascara}</option>)}</select></label><div className="v4-atalhos" role="group" aria-label="Atalhos de prefixo">{atalhos.map((p) => <button type="button" className={valor === p ? 'selecionado' : ''} aria-pressed={valor === p} key={p} onClick={() => onChange(p)}>{subdivisao ? `Dividir em /${p}` : `/${p}`}</button>)}</div></div>
}

function Topologia({ ipB = '', prefixo = 24, conectada = false }) {
  return <div className={`v4-topologia ${conectada ? 'conectada' : ''}`} aria-label={`Rede ilustrativa: dois computadores e um switch; ${conectada ? 'cabos conectados' : 'cabos desconectados'}`}>
    <article className="v4-no v4-pc1"><Computer size={37} aria-hidden="true" /><strong>Computador 1</strong><code>{IP_A}/{prefixo}</code><small>Interface de rede</small></article>
    <span className="v4-cabo v4-cabo1" aria-hidden="true" />
    <article className="v4-no v4-switch"><Network size={35} aria-hidden="true" /><strong>Switch</strong><small>Conexão local</small></article>
    <span className="v4-cabo v4-cabo2" aria-hidden="true" />
    <article className="v4-no v4-pc2"><Computer size={37} aria-hidden="true" /><strong>Computador 2</strong><code>{ipB ? `${ipB}/${prefixo}` : 'Escolher IPv4'}</code><small>Interface de rede</small></article>
  </div>
}

function Faixa({ rede, prefixoLabel = false }) {
  if (rede.tipo === 'ponto-a-ponto') return <section className="v4-caso-especial" data-testid="prefix-special"><span className="v4-guia-kicker">USO ESPECIAL · NÃO É A LAN COM SWITCH</span><h2>/31 · Enlace ponto a ponto</h2><p>Os dois endereços podem identificar as duas pontas do enlace. Não reservamos um deles como rede e outro como broadcast neste caso.</p><div className="v4-extremos-especiais"><article><span>Ponta A</span><strong>{rede.primeiro}</strong></article><article><span>Ponta B</span><strong>{rede.ultimo}</strong></article></div></section>
  if (rede.tipo === 'host') return <section className="v4-caso-especial" data-testid="prefix-special"><span className="v4-guia-kicker">USO ESPECIAL · ENDEREÇO INDIVIDUAL</span><h2>/32 · Um único endereço</h2><strong className="v4-host-unico">{rede.cidr}</strong><p>Não há bits variáveis de host. Este prefixo identifica um IPv4 individual, como em uma rota de host; não forma uma LAN de vários computadores e não possui broadcast de sub-rede.</p></section>
  return <div className="v4-faixa"><div><span>Endereço da rede</span><strong>{prefixoLabel ? rede.cidr : rede.rede}</strong><small>Identifica a rede</small></div><div className="v4-faixa-hosts"><span>Faixa de hosts</span><strong>{rede.primeiro}</strong><small>até</small><strong>{rede.ultimo}</strong></div><div><span>Broadcast</span><strong data-testid="broadcast">{rede.broadcast}</strong><small>Alcança os hosts da sub-rede</small></div></div>
}

function PreviaEnderecoIPv4({ aula }) {
  const navigate = useNavigate()
  const [cena, setCena] = useState(aula?.initialState?.cena ?? 0)
  const [outroHost, setOutroHost] = useState(aula?.initialState?.outroHost ?? false)
  const [prefixo, setPrefixo] = useState(aula?.initialState?.prefixo ?? 24)
  const [ipB, setIpB] = useState(aula?.initialState?.ipB ?? '')
  const [lanPrefixo, setLanPrefixo] = useState(aula?.initialState?.lanPrefixo ?? 24)
  const [conectada, setConectada] = useState(aula?.initialState?.conectada ?? false)
  const [resultado, setResultado] = useState(null)
  const [divisao, setDivisao] = useState(aula?.initialState?.divisao ?? 25)
  const [prefixoBase, setPrefixoBase] = useState(aula?.initialState?.prefixoBase ?? 24)
  const [paginaSubredes, setPaginaSubredes] = useState(aula?.initialState?.paginaSubredes ?? 0)
  const [subredeAtiva, setSubredeAtiva] = useState(aula?.initialState?.subredeAtiva ?? 0)
  const [encerrada, setEncerrada] = useState(false)
  const tituloRef = useRef(null)
  const rede = calcularRede(IP_A, prefixo)
  const planoDiv = calcularDivisao(divisao, prefixoBase)
  const subredes = dividirRedeDidatica(divisao, { prefixoBase, offset: paginaSubredes * 8 })
  const subrede = subredes[subredeAtiva]
  const endereco = outroHost ? '192.168.10.80' : IP_A
  const imagens = [linkEnsinando, linkObservando, linkExplicando, linkPensando, resultado?.estado === 'compativel' ? linkConectando : linkPensando, linkEnsinando, linkComemorando]
  const contextos = ['Vamos aprender com uma rede', 'Identifique a interface', 'Rede de um lado, host do outro', 'Observe os limites', 'Experimente e confira', 'Cada parte tem seus limites', 'Conceitos que viraram prática']

  useEffect(() => { tituloRef.current?.focus() }, [cena])
  const onStateChange = aula?.onStateChange
  useEffect(() => {
    onStateChange?.({ versao: 1, cena, outroHost, prefixo, ipB, lanPrefixo, conectada,
      divisao, prefixoBase, paginaSubredes, subredeAtiva })
  }, [onStateChange, cena, outroHost, prefixo, ipB, lanPrefixo, conectada,
    divisao, prefixoBase, paginaSubredes, subredeAtiva])


  function avancar() { if (aula?.bloqueado) return; if (cena < ETAPAS.length - 1) setCena((atual) => atual + 1); else if (aula) void aula.onFim(); else setEncerrada(true) }
  function recomecar() {
    setCena(0); setOutroHost(false); setPrefixo(24); setIpB(''); setLanPrefixo(24)
    setConectada(false); setResultado(null); setDivisao(25); setPrefixoBase(24); setPaginaSubredes(0); setSubredeAtiva(0); setEncerrada(false)
  }

  return <main className={`principal pagina-aula aula-modelos-pagina pagina-previa-ipv4${aula ? ' aula-ipv4-pagina' : ''}`}>
    {aula?.status}
    <p className="v4-aviso">{aula ? <><strong>Endereçamento IPv4 · {aula.revisao ? 'Revisão' : 'Aula oficial'}</strong> · Explore no seu ritmo. Depois, continue para o gateway e as atividades de interpretação.</> : <><strong>Demonstração sem progresso.</strong> A versão aprovada já está na aula oficial. Aqui você pode experimentar sem alterar respostas, conclusão ou XP.</>}</p>
    <section className="aula-cabecalho"><button className="aula-sair" disabled={aula?.bloqueado} onClick={() => aula ? aula.onSair() : navigate('/modulos/enderecamento/ipv4')}><ArrowLeft size={18} /> {aula ? 'Módulos' : 'Voltar à aula atual'}</button><div className="aula-progresso-area"><div><span>{ETAPAS[cena]}</span><strong data-testid="scene-position">Etapa {cena + 1} de {ETAPAS.length}</strong></div><div className="aula-progresso" aria-label={aula ? "Posição na introdução interativa" : "Posição na prévia, não progresso da aula"}><div style={{ width: `${((cena + 1) / ETAPAS.length) * 100}%` }} /></div></div><span className="aula-tempo">No seu ritmo</span></section>
    <section className="aula-palco"><div className="aula-conteudo"><div className="aula-bloco v4-cena" data-scene={cena}>
      <span className="aula-etiqueta">{cena === 4 ? 'PRÁTICA VISUAL · NÃO É UMA SESSÃO CORE' : 'APRENDER OBSERVANDO · IPv4'}</span>
      <h1 ref={tituloRef} tabIndex={-1}>{TITULOS[cena]}</h1><p className="v4-narracao">{cena === 3 && prefixo >= 31 ? 'O intervalo /22 a /30 usa a regra comum deste exemplo de LAN. /31 e /32 são diferentes: veja o tipo de uso antes de contar os endereços.' : FALAS[cena]}</p>

      {cena === 0 && <><Topologia /><div className="v4-objetivos"><h2>{aula ? 'Nesta aula você vai descobrir' : 'Nesta prévia você vai descobrir'}</h2><ul><li>Qual parte do endereço pertence à rede.</li><li>Como a máscara muda a capacidade de hosts.</li><li>Como configurar uma LAN e reconhecer sub-redes.</li></ul></div></>}

      {cena === 1 && <><Topologia ipB="192.168.10.80" conectada /><div className="v4-anatomia" aria-label={`Endereço ${endereco}/24: rede nos primeiros três octetos e host no último`}><span className="v4-parte-rede">192.168.10.</span><strong className="v4-parte-host" data-testid="host-part">{outroHost ? '80' : '10'}</strong><span className="v4-prefixo-anatomia">/24</span></div><div className="v4-legenda"><span className="rede">Parte da rede · neste /24</span><span className="host">Parte do host</span></div><p className="v4-nota">Os dois endereços são diferentes, mas pertencem a 192.168.10.0/24. Apenas o IP, sem a máscara, não conta toda a história.</p><button className="botao-secundario" onClick={() => setOutroHost((atual) => !atual)}>{outroHost ? 'Voltar ao primeiro computador' : 'Ver o outro computador'}</button></>}

      {cena === 2 && <><Prefixos valor={prefixo} onChange={setPrefixo} /><ExploradorMascara prefixo={prefixo} />{prefixo >= 31 && <p className="v4-nota">Caso especial: {prefixo === 31 ? '/31 é usado para enlaces ponto a ponto, com duas pontas.' : '/32 identifica um único endereço.'} Na próxima etapa você verá por que não usamos a regra comum de rede e broadcast nesses casos.</p>}</>}

      {cena === 3 && <><Prefixos valor={prefixo} onChange={setPrefixo} /><div className="v4-endereco-referencia"><span>Interface de referência</span><strong>{IP_A}/{prefixo}</strong></div><Faixa rede={rede} /><div className="v4-capacidade"><article><strong>{rede.total.toLocaleString('pt-BR')}</strong><span>endereços no bloco</span></article><article><strong>{rede.total - rede.hosts}</strong><span>{rede.tipo === 'lan' ? 'rede e broadcast' : 'reservados por essa regra'}</span></article><article className="destaque"><strong data-testid="host-capacity">{rede.hosts.toLocaleString('pt-BR')}</strong><span>{rede.tipo === 'lan' ? 'endereços de host utilizáveis' : rede.tipo === 'ponto-a-ponto' ? 'endereços das duas pontas' : 'endereço individual'}</span></article></div>{prefixo <= 16 && <p className="v4-nota v4-nota-prefixo-largo" data-testid="prefixo-largo">{prefixo === 16
        ? 'Com /16, só os dois primeiros números identificam a rede. Por isso 192.168.10.10 e 192.168.20.10 ficam na mesma rede 192.168.0.0/16, e um computador com esse prefixo tenta entregar ao outro diretamente, sem gateway.'
        : 'Com /8, só o primeiro número identifica a rede: 192.168.10.10 e 192.200.5.1 ficam na mesma rede 192.0.0.0/8.'}</p>}<p className="v4-nota">Nas LANs /8 a /30 deste exemplo, rede e broadcast ficam fora da faixa de hosts. Em /31 e /32, siga o uso especial mostrado no painel, não a subtração de dois endereços.</p></>}

      {cena === 4 && <><p className="v4-simulacao-aviso">Simulação didática: sem máquinas virtuais, comandos ou envio de pacotes reais.</p><Topologia ipB={ipB} prefixo={lanPrefixo} conectada={conectada} /><div className="v4-configuracao"><button className="botao-secundario" aria-pressed={conectada} onClick={() => { setConectada((v) => !v); setResultado(null) }}>{conectada ? 'Desconectar computadores' : 'Conectar computadores'}</button><label><span>IPv4 do Computador 2</span><select aria-label="IPv4 do Computador 2" value={ipB} onChange={(e) => { setIpB(e.target.value); setResultado(null) }}><option value="">Escolha um endereço</option>{['192.168.10.0', '192.168.10.10', '192.168.10.20', '192.168.10.80'].map((ip) => <option key={ip} value={ip}>{ip}</option>)}</select></label><label><span>Máscara dos computadores</span><select aria-label="Máscara dos computadores" value={lanPrefixo} onChange={(e) => { setLanPrefixo(Number(e.target.value)); setResultado(null) }}>{PREFIXOS_DIDATICOS.map((p) => <option key={p} value={p}>/{p} · {calcularRede(IP_A, p).mascara}</option>)}</select></label></div><button className="botao-interacao" onClick={() => setResultado(avaliarLAN({ ipA: IP_A, ipB, prefixo: lanPrefixo, conectada }))}>Testar configuração simulada</button>{resultado && <div className={`v4-resultado ${resultado.estado === 'compativel' ? 'sucesso' : ''}`} data-testid="lan-result" data-result={resultado.estado} role="status"><strong>{resultado.titulo}</strong><p>{resultado.texto}</p></div>}<p className="v4-nota">A máscara escolhida é aplicada aos dois computadores. {aula ? 'O laboratório real de configuração por campos guiados será uma atividade separada.' : 'A versão prática com interfaces e comandos reais será construída depois da validação.'}</p></>}

      {cena === 5 && <><label className="v4-origem"><span>Prefixo da rede de origem</span><select aria-label="Prefixo da rede de origem" value={prefixoBase} onChange={(e) => { const p = Number(e.target.value); setPrefixoBase(p); setDivisao((atual) => Math.max(atual, p)); setPaginaSubredes(0); setSubredeAtiva(0) }}>{PREFIXOS_DIDATICOS.map((p) => <option key={p} value={p}>/{p}</option>)}</select></label><Prefixos valor={divisao} minimo={prefixoBase} subdivisao onChange={(p) => { setDivisao(p); setPaginaSubredes(0); setSubredeAtiva(0) }} /><p className="v4-nota">Origem: <strong>{planoDiv.redeBase.cidr}</strong>. Resultado: <strong data-testid="subnet-total">{planoDiv.quantidade}</strong> blocos /{divisao}. {divisao === prefixoBase ? 'Os prefixos são iguais: ainda temos um único bloco.' : 'O prefixo maior cria partes menores.'}</p><div className="v4-subredes">{subredes.map((n, i) => <button type="button" className={subredeAtiva === i ? 'selecionada' : ''} key={n.cidr} data-subnet={n.cidr} aria-label={`Explorar sub-rede ${n.cidr}`} aria-pressed={subredeAtiva === i} onClick={() => setSubredeAtiva(i)}><span>Bloco {paginaSubredes * 8 + i + 1}</span><strong>{n.cidr}</strong><small>{n.hosts} {n.tipo === 'lan' ? 'endereços de host utilizáveis' : n.tipo === 'ponto-a-ponto' ? 'endereços de ponta a ponta' : 'endereço individual'}</small></button>)}</div><div className="v4-paginacao"><button className="botao-secundario" disabled={paginaSubredes === 0} onClick={() => { setPaginaSubredes((p) => p - 1); setSubredeAtiva(0) }}>Sub-redes anteriores</button><span>Página {paginaSubredes + 1} de {Math.ceil(planoDiv.quantidade / 8)}</span><button className="botao-secundario" aria-label="Próximas sub-redes" disabled={(paginaSubredes + 1) * 8 >= planoDiv.quantidade} onClick={() => { setPaginaSubredes((p) => p + 1); setSubredeAtiva(0) }}>Próximas sub-redes</button></div><section className="v4-subnet-detalhe" data-testid="selected-subnet"><h2>Explore {subrede.cidr}</h2><Faixa rede={subrede} /></section><p className="v4-nota">Estas são divisões de endereçamento IP, não VLANs. /31 e /32 têm usos especiais, destacados acima; comunicação entre redes por um roteador será estudada depois.</p></>}

      {cena === 6 && <><div className="v4-resumo"><p><Check size={18} /> O endereço identifica a interface; a máscara ajuda a identificar sua rede.</p><p><Check size={18} /> Cada sub-rede tem limites e uma faixa própria de hosts.</p><p><Check size={18} /> Uma LAN simples vem antes do planejamento de redes maiores.</p></div><p className="v4-nota">{aula ? 'Você concluiu a exploração visual. Continue para relacionar os endereços ao gateway e conferir seu entendimento. O laboratório real de configuração será uma atividade separada.' : 'Na versão final, estes assuntos serão organizados em aulas independentes. Nesta prévia, você valida a explicação e a interação. O laboratório real ainda não foi criado.'}</p></>}
      {encerrada && <div className="feedback-desafio sucesso" role="status">Prévia finalizada. Nenhuma aula foi concluída e nenhum progresso ou XP foi registrado.</div>}
    </div></div><aside className="link-painel"><div className="link-fixo"><div className="link-luz" /><img src={imagens[cena]} alt={`Link acompanhando: ${ETAPAS[cena]}`} /><div className="link-identidade"><strong>Link</strong><span>{contextos[cena]}</span></div></div></aside></section>
    <footer className="aula-navegacao"><button className="botao-voltar" disabled={cena === 0 || aula?.bloqueado} onClick={() => { setCena((atual) => atual - 1); setEncerrada(false) }}><ArrowLeft size={18} /> Etapa anterior</button><div className="aula-passos" aria-label={aula ? "Etapas da introdução" : "Etapas da prévia"}>{ETAPAS.map((nome, i) => <span key={nome} className={i <= cena ? 'ativo' : ''} title={nome} />)}</div><button className="botao-avancar" disabled={aula?.bloqueado} onClick={encerrada ? recomecar : avancar}>{encerrada ? 'Rever prévia' : cena === ETAPAS.length - 1 ? aula ? aula.salvando ? 'Salvando…' : 'Continuar para gateway' : 'Finalizar prévia' : 'Continuar'}<ArrowRight size={18} /></button></footer>
  </main>
}
export default PreviaEnderecoIPv4
