import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Cable,
  Check,
  CircleCheck,
  Cloud,
  Gamepad2,
  House,
  Laptop,
  Network,
  Printer,
  Radio,
  RotateCcw,
  Router,
  Server,
  Smartphone,
  Sparkles,
  Wifi,
} from 'lucide-react'

import linkPrincipal from '../assets/mascote/link-kit-v2/link-v2-principal.webp'
import { COMEMORACAO, POSES } from '../assets/mascote/poses'
import ConquistaAula from '../components/aula/ConquistaAula'
import linkConectando from '../assets/mascote/link-expansao-v1/link-conectando.webp'
import linkExplicando from '../assets/mascote/link-expansao-v1/link-explicando.webp'
import './AulaFundamentosRede.css'

const AULA_ID = 'fundamentos-aula-1'
// A pose antiga "observando a rede" tem um holograma junto à cabeça: nas aulas usamos a pose curiosa.
const linkObservandoRede = POSES.curioso

const etapas = [
  'Boas-vindas',
  'Descoberta',
  'Elementos',
  'LAN e WAN',
  'Desafio',
  'Topologia',
  'Conclusão',
]

const elementosRede = [
  {
    titulo: 'Dispositivos finais',
    texto: 'São os equipamentos usados para enviar, receber ou utilizar informações.',
    exemplos: 'Computador, celular, servidor e impressora',
    icone: Laptop,
  },
  {
    titulo: 'Equipamentos de conexão',
    texto: 'Ajudam os dados a encontrar o caminho entre os dispositivos.',
    exemplos: 'Switch, roteador e ponto de acesso',
    icone: Router,
  },
  {
    titulo: 'Meios de comunicação',
    texto: 'São os caminhos por onde os sinais e os dados são transportados.',
    exemplos: 'Cabo, fibra óptica e Wi-Fi',
    icone: Cable,
  },
]

const situacoes = [
  {
    id: 1,
    texto: 'Computadores conectados dentro de um laboratório.',
    resposta: 'LAN',
  },
  {
    id: 2,
    texto: 'Celular conectado ao Wi-Fi de uma residência.',
    resposta: 'LAN',
  },
  {
    id: 3,
    texto: 'Filiais de uma empresa localizadas em cidades diferentes.',
    resposta: 'WAN',
  },
  {
    id: 4,
    texto: 'Redes distantes se comunicando por meio da Internet.',
    resposta: 'WAN',
  },
]

function AulaFundamentosRede() {
  const navigate = useNavigate()
  const [etapaAtual, setEtapaAtual] = useState(0)
  const [redeConectada, setRedeConectada] = useState(false)
  const [elementoAberto, setElementoAberto] = useState(0)
  const [conexaoEscolhida, setConexaoEscolhida] = useState('')
  const [respostas, setRespostas] = useState({})
  const [desafioValidado, setDesafioValidado] = useState(false)
  const [selecaoTopologia, setSelecaoTopologia] = useState([])
  const [topologiaValidada, setTopologiaValidada] = useState(false)
  const [aulaJaConcluida, setAulaJaConcluida] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [conquista, setConquista] = useState(null)

  useEffect(() => {
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' })
      .then((resposta) => resposta.json())
      .then((dados) => {
        const registro = dados.progresso?.aulas?.find(
          (item) => item.aula_id === AULA_ID,
        )
        if (ativo) setAulaJaConcluida(Boolean(registro?.concluida))
      })
      .catch(() => {})
    return () => { ativo = false }
  }, [])

  const progresso = Math.round(((etapaAtual + 1) / etapas.length) * 100)
  const respostasCorretas = useMemo(
    () =>
      situacoes.filter(
        (situacao) => respostas[situacao.id] === situacao.resposta,
      ).length,
    [respostas],
  )

  const desafioCompleto = Object.keys(respostas).length === situacoes.length
  const desafioAprovado = desafioValidado && respostasCorretas === situacoes.length
  const topologiaAprovada =
    topologiaValidada &&
    selecaoTopologia.includes('computador-1') &&
    selecaoTopologia.includes('computador-2') &&
    !selecaoTopologia.includes('switch')

  const imagemLink =
    etapaAtual === 0
      ? linkPrincipal
      : etapaAtual === 1
        ? linkConectando
        : etapaAtual <= 3
          ? linkExplicando
          : etapaAtual === 4
            ? desafioAprovado ? COMEMORACAO.polegares : POSES.pensativo
            : etapaAtual === 5
              ? topologiaAprovada ? COMEMORACAO.polegares : linkObservandoRede
              : COMEMORACAO.estrela

  function podeAvancar() {
    if (etapaAtual === 1) return redeConectada
    if (etapaAtual === 4) return desafioAprovado
    if (etapaAtual === 5) return topologiaAprovada
    return true
  }

  async function avancar() {
    if (!podeAvancar() || salvando) return
    setSalvando(true)

    try {
      if (etapaAtual === etapas.length - 1) {
        const resposta = await fetch('/api/progresso/aula/concluir', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ aula_id: AULA_ID }),
        })
        const dados = await resposta.json()
        if (!resposta.ok || !dados.sucesso) {
          throw new Error(dados.mensagem || 'Não foi possível concluir a aula.')
        }
        localStorage.removeItem('pinglevel:aula-fundamentos-1')
        setConquista({ xp: dados.progresso?.xp_concedido })
        return
      }

      const proximaEtapa = etapaAtual + 1
      const resposta = await fetch('/api/progresso/aula', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aula_id: AULA_ID, etapa_atual: proximaEtapa }),
      })
      const dados = await resposta.json()
      if (!resposta.ok || !dados.sucesso) {
        throw new Error(dados.mensagem || 'Não foi possível salvar o progresso.')
      }
      setEtapaAtual(proximaEtapa)
    } catch (erro) {
      window.alert(erro.message)
    } finally {
      setSalvando(false)
    }
  }

  function voltar() {
    if (etapaAtual === 0) {
      navigate('/')
      return
    }

    setEtapaAtual((etapa) => etapa - 1)
  }

  function responderSituacao(id, resposta) {
    setRespostas((atuais) => ({ ...atuais, [id]: resposta }))
    setDesafioValidado(false)
  }

  function validarDesafio() {
    if (desafioCompleto) setDesafioValidado(true)
  }

  function reiniciarDesafio() {
    setRespostas({})
    setDesafioValidado(false)
  }

  function alternarNo(no) {
    setSelecaoTopologia((atuais) =>
      atuais.includes(no)
        ? atuais.filter((item) => item !== no)
        : [...atuais, no],
    )
    setTopologiaValidada(false)
  }

  function renderizarConteudo() {
    if (etapaAtual === 0) {
      return (
        <div className="aula-bloco aula-introducao">
          <span className="aula-etiqueta">MÓDULO 01 · AULA 01</span>
          <h1>O que é uma rede?</h1>
          <p className="aula-destaque">
            Você usa redes todos os dias, mesmo quando não percebe. Vamos
            descobrir o que faz diferentes equipamentos conseguirem se comunicar.
          </p>

          <div className="aula-metas">
            <div><Network size={19} /> Entender o conceito de rede</div>
            <div><Radio size={19} /> Reconhecer seus elementos</div>
            <div><House size={19} /> Diferenciar LAN e WAN</div>
          </div>

          <div className="fala-link apresentacao-link">
            <strong>Olá! Eu sou o Link.</strong>
            <p>
              Serei seu guia nesta jornada. Não precisa decorar tudo agora:
              observe, experimente e construa os conceitos comigo, uma etapa
              por vez.
            </p>
          </div>
        </div>
      )
    }

    if (etapaAtual === 1) {
      return (
        <div className="aula-bloco">
          <span className="aula-etiqueta">DESCUBERTA VISUAL</span>
          <h2>Equipamentos isolados conseguem trocar informações?</h2>
          <p>
            Os dispositivos abaixo estão próximos, mas ainda não existe um caminho
            entre eles. Clique no botão para criar a conexão.
          </p>

          <div className={`rede-visual ${redeConectada ? 'conectada' : ''}`}>
            <div className="dispositivo"><Laptop /><span>Notebook</span></div>
            <div className="linha-rede linha-um" />
            <div className="dispositivo central"><Wifi /><span>Conexão</span></div>
            <div className="linha-rede linha-dois" />
            <div className="dispositivo"><Smartphone /><span>Celular</span></div>
          </div>

          <div className="acao-conectar">
            <button
              className={`botao-interacao botao-conectar ${
                redeConectada ? 'conectado' : ''
              }`}
              onClick={() => setRedeConectada(true)}
              disabled={redeConectada}
            >
              {redeConectada ? <Check size={18} /> : <Network size={18} />}
              {redeConectada ? 'Conexão realizada' : 'Conectar dispositivos'}
            </button>
          </div>

          {redeConectada && (
            <div className="conceito-revelado">
              <Sparkles size={21} />
              <p>
                Quando dispositivos conseguem trocar informações por um meio de
                comunicação, temos uma <strong>rede</strong>.
              </p>
            </div>
          )}
        </div>
      )
    }

    if (etapaAtual === 2) {
      const selecionado = elementosRede[elementoAberto]
      const IconeSelecionado = selecionado.icone

      return (
        <div className="aula-bloco">
          <span className="aula-etiqueta">ELEMENTOS BÁSICOS</span>
          <h2>Uma rede possui diferentes participantes</h2>
          <p>Selecione cada grupo para entender sua função.</p>

          <div className="elementos-abas">
            {elementosRede.map((elemento, indice) => {
              const Icone = elemento.icone
              return (
                <button
                  key={elemento.titulo}
                  className={indice === elementoAberto ? 'ativo' : ''}
                  onClick={() => setElementoAberto(indice)}
                >
                  <Icone size={22} />
                  <span>{elemento.titulo}</span>
                </button>
              )
            })}
          </div>

          <article className="elemento-detalhe">
            <div className="elemento-icone"><IconeSelecionado size={31} /></div>
            <div>
              <h3>{selecionado.titulo}</h3>
              <p>{selecionado.texto}</p>
              <span>Exemplos: {selecionado.exemplos}.</span>
            </div>
          </article>

          {elementoAberto === 1 && (
            <section className="switch-roteador" aria-label="Switch e roteador">
              <div className="switch-roteador-cartoes">
                <article><strong>Switch</strong><p>Liga os dispositivos de uma mesma rede local, como os computadores de uma sala.</p></article>
                <article><strong>Roteador</strong><p>Liga redes diferentes entre si e encaminha o que precisa sair da rede local.</p></article>
              </div>
              <p className="switch-roteador-pergunta">Uma escola quer que os computadores do laboratório acessem a Internet. Qual equipamento liga a rede da escola à rede externa?</p>
              <div className="switch-roteador-opcoes" role="group" aria-label="Escolha o equipamento">
                {[['switch', 'Switch'], ['roteador', 'Roteador']].map(([valor, rotulo]) => (
                  <button key={valor} type="button" aria-pressed={conexaoEscolhida === valor}
                    className={conexaoEscolhida === valor ? 'ativo' : ''} onClick={() => setConexaoEscolhida(valor)}>{rotulo}</button>
                ))}
              </div>
              {conexaoEscolhida && (
                <p className={`feedback-desafio ${conexaoEscolhida === 'roteador' ? 'sucesso' : ''}`} role="status">
                  {conexaoEscolhida === 'roteador'
                    ? 'Isso! O switch conecta os computadores do laboratório entre si; o roteador liga essa rede à rede externa.'
                    : 'O switch conecta os computadores dentro do laboratório. Para sair para outra rede, é preciso um equipamento que ligue redes diferentes.'}
                </p>
              )}
            </section>
          )}

          <div className="elementos-miniaturas" aria-label="Exemplos de elementos de rede">
            <Laptop /><Smartphone /><Server /><Printer /><Router /><Wifi /><Cable />
          </div>
        </div>
      )
    }

    if (etapaAtual === 3) {
      return (
        <div className="aula-bloco">
          <span className="aula-etiqueta">ALCANCE DA REDE</span>
          <h2>LAN e WAN representam alcances diferentes</h2>
          <p>
            A principal diferença está na área atendida e na distância entre as
            redes conectadas.
          </p>

          <div className="comparacao-redes">
            <article>
              <div className="comparacao-icone"><House size={31} /></div>
              <span>REDE LOCAL</span>
              <h3>LAN</h3>
              <p>
                Conecta dispositivos em uma área limitada, como uma casa,
                laboratório, escola ou empresa.
              </p>
              <div className="cenario-lan">
                <Laptop /><Wifi /><Gamepad2 />
              </div>
            </article>

            <article>
              <div className="comparacao-icone"><Cloud size={31} /></div>
              <span>LONGA DISTÂNCIA</span>
              <h3>WAN</h3>
              <p>
                Conecta redes que estão geograficamente distantes, como filiais em
                cidades diferentes.
              </p>
              <div className="cenario-wan">
                <House /><Cloud /><House />
              </div>
            </article>
          </div>

          <div className="nota-conceito">
            A Internet é um grande conjunto de redes interligadas.
          </div>
        </div>
      )
    }

    if (etapaAtual === 4) {
      return (
        <div className="aula-bloco">
          <span className="aula-etiqueta">DESAFIO RÁPIDO</span>
          <h2>Esta situação representa uma LAN ou uma WAN?</h2>
          <p>Classifique as quatro situações e depois confira seu raciocínio.</p>

          <div className="lista-situacoes">
            {situacoes.map((situacao, indice) => {
              const respostaAluno = respostas[situacao.id]
              const correta = respostaAluno === situacao.resposta
              const mostrarEstado = desafioValidado && respostaAluno

              return (
                <article
                  key={situacao.id}
                  className={
                    mostrarEstado ? (correta ? 'correta' : 'incorreta') : ''
                  }
                >
                  <div className="situacao-numero">{indice + 1}</div>
                  <p>{situacao.texto}</p>
                  <div className="situacao-opcoes">
                    {['LAN', 'WAN'].map((opcao) => (
                      <button
                        key={opcao}
                        className={respostaAluno === opcao ? 'selecionada' : ''}
                        onClick={() => responderSituacao(situacao.id, opcao)}
                      >
                        {opcao}
                      </button>
                    ))}
                  </div>
                </article>
              )
            })}
          </div>

          <div className="acoes-desafio">
            <button
              className="botao-interacao"
              onClick={validarDesafio}
              disabled={!desafioCompleto}
            >
              <CircleCheck size={18} /> Conferir respostas
            </button>
            {desafioValidado && !desafioAprovado && (
              <button className="botao-secundario" onClick={reiniciarDesafio}>
                <RotateCcw size={17} /> Tentar novamente
              </button>
            )}
          </div>

          {desafioValidado && (
            <div className={`feedback-desafio ${desafioAprovado ? 'sucesso' : ''}`}>
              {desafioAprovado
                ? 'Você identificou corretamente o alcance das quatro redes.'
                : `${respostasCorretas} de 4 respostas corretas. Observe se cada situação ocorre em uma área limitada ou conecta locais distantes.`}
            </div>
          )}
        </div>
      )
    }

    if (etapaAtual === 5) {
      const nos = [
        { id: 'computador-1', nome: 'Computador A', icone: Laptop },
        { id: 'switch', nome: 'Switch', icone: Network },
        { id: 'computador-2', nome: 'Computador B', icone: Laptop },
      ]

      return (
        <div className="aula-bloco">
          <span className="aula-etiqueta">MINIATIVIDADE</span>
          <h2>Identifique os dispositivos finais</h2>
          <p>
            Selecione os equipamentos que enviam ou recebem as informações. Não
            selecione o equipamento intermediário.
          </p>

          <div className="mini-topologia">
            {nos.map((no, indice) => {
              const Icone = no.icone
              const selecionado = selecaoTopologia.includes(no.id)
              return (
                <div className="mini-topologia-item" key={no.id}>
                  <button
                    className={selecionado ? 'selecionado' : ''}
                    onClick={() => alternarNo(no.id)}
                  >
                    <Icone size={31} />
                    <span>{no.nome}</span>
                    {selecionado && <Check className="no-check" size={17} />}
                  </button>
                  {indice < nos.length - 1 && <div className="mini-enlace" />}
                </div>
              )
            })}
          </div>

          <button
            className="botao-interacao"
            onClick={() => setTopologiaValidada(true)}
            disabled={selecaoTopologia.length === 0}
          >
            <CircleCheck size={18} /> Validar seleção
          </button>

          {topologiaValidada && (
            <div className={`feedback-desafio ${topologiaAprovada ? 'sucesso' : ''}`}>
              {topologiaAprovada
                ? 'Correto! Os computadores são os dispositivos finais. O switch cria a conexão entre eles.'
                : 'Ainda não. Pense em quais equipamentos são usados diretamente para enviar ou receber informações.'}
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="aula-bloco aula-conclusao">
        <span className="aula-etiqueta">AULA CONCLUÍDA</span>
        <h2>Primeira aula concluída!</h2>
        <p className="aula-destaque">
          Você deu o primeiro passo e já consegue reconhecer o que forma uma rede.
        </p>
        <div className="xp-conquistado">
          <Sparkles size={30} />
          <div>
            <strong>{aulaJaConcluida ? '100 XP conquistados' : '100 XP ao concluir'}</strong>
            <span>{aulaJaConcluida ? 'Revisão sem XP adicional' : 'Recompensa da aula'}</span>
          </div>
        </div>

        <div className="resumo-aprendizado">
          <div><Check /> Uma rede permite a troca de informações.</div>
          <div><Check /> Existem dispositivos, equipamentos intermediários e meios.</div>
          <div><Check /> LAN e WAN possuem alcances diferentes.</div>
          <div><Check /> O switch liga a rede local; o roteador liga redes diferentes.</div>
        </div>

        <div className="fala-link">
          <strong>Link diz:</strong>
          <p>
            Para conversar, cada participante precisa ser identificado por um
            endereço. Na próxima aula veremos como a informação encontra um
            caminho entre esses equipamentos; depois, como funcionam os endereços.
            Clique em <b>Concluir aula</b> para registrar seu XP e seguir.
          </p>
        </div>
      </div>
    )
  }

  return (
    <main className="principal pagina-aula">
      <section className="aula-cabecalho">
        <button className="aula-sair" onClick={() => navigate('/')}>
          <ArrowLeft size={18} /> Sair da aula
        </button>

        <div className="aula-progresso-area">
          <div>
            <span>{etapas[etapaAtual]}</span>
            <strong>{progresso}%</strong>
          </div>
          <div className="aula-progresso">
            <div style={{ width: `${progresso}%` }} />
          </div>
        </div>

        <span className="aula-tempo">8–12 min</span>
      </section>

      <section className="aula-palco">
        <div className="aula-conteudo">{renderizarConteudo()}</div>

        <aside className="link-painel"><div className="link-fixo">
          <div className="link-luz" />
          <img src={imagemLink} alt="Link, mascote do PingLevel" />
          <div className="link-identidade">
            <strong>Link</strong>
            <span>Seu guia de aprendizagem</span>
          </div>
        </div></aside>
      </section>

      <footer className="aula-navegacao">
        <button className="botao-voltar" onClick={voltar}>
          <ArrowLeft size={18} />
          {etapaAtual === 0 ? 'Voltar ao início' : 'Etapa anterior'}
        </button>

        <div className="aula-passos" aria-label="Progresso das etapas">
          {etapas.map((etapa, indice) => (
            <span
              key={etapa}
              className={indice <= etapaAtual ? 'ativo' : ''}
              title={etapa}
            />
          ))}
        </div>

        <button
          className="botao-avancar"
          onClick={avancar}
          disabled={!podeAvancar() || salvando}
        >
          {salvando
            ? 'Salvando...'
            : etapaAtual === etapas.length - 1
              ? 'Concluir aula'
              : 'Continuar'}
          <ArrowRight size={18} />
        </button>
      </footer>
      {conquista && <ConquistaAula aulaId={AULA_ID} xp={conquista.xp} />}
    </main>
  )
}

export default AulaFundamentosRede
