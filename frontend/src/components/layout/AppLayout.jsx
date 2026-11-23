import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Menu,
  KeyRound,
  LogOut,
} from 'lucide-react'

import LogoPingLevel from './LogoPingLevel'
import CriadoPor from './CriadoPor'
import { itensMenu } from '../../data/navegacao'
import { useAuth } from '../../contexts/AuthContext'
import linkPrincipal from '../../assets/mascote/link-kit-v2/link-v2-principal.webp'
import linkEnsinando from '../../assets/mascote/link-kit-v2/link-v2-ensinando.webp'
import { POSES } from '../../assets/mascote/poses'
import { resumoInicio } from '../../data/trilha'

// Primeira entrada (revisão de 30/10/2026): três telas diretas que terminam na aula 1.
const etapasApresentacaoLink = [
  {
    etiqueta: 'BEM-VINDO AO PINGLEVEL',
    titulo: 'Olá, eu sou o Link!',
    texto: 'Sou seu guia neste curso de redes de computadores. Vou acompanhar você em cada aula e em cada laboratório.',
    complemento: 'Não precisa saber nada de redes para começar: vamos juntos, uma etapa de cada vez.',
    imagem: linkPrincipal,
  },
  {
    etiqueta: 'COMO O CURSO FUNCIONA',
    titulo: 'Aula explica, laboratório pratica',
    texto: 'Nas aulas você entende o conceito com exemplos e desafios curtos. Nos laboratórios, pratica numa rede de verdade.',
    complemento: 'Quando surgir uma dúvida, eu dou pistas sem entregar a resposta: cada conquista é sua.',
    imagem: linkEnsinando,
  },
  {
    etiqueta: 'POR ONDE COMEÇAR',
    titulo: 'Comece pela aula 1',
    texto: '“O que é uma rede?” leva cerca de 10 minutos. Depois, a Início sempre mostra o seu próximo passo, e a Trilha mostra o caminho inteiro.',
    complemento: 'Esta apresentação volta sempre pelo botão Ajuda.',
    imagem: POSES.incentivando,
  },
]

function AppLayout({ compactoInicial = false }) {
  const { usuario, sair } = useAuth()
  const navegar = useNavigate()
  const chaveApresentacao = `pinglevel:link-apresentado:${usuario.login}`
  // No celular o menu aberto cobre a página: começa recolhido e recolhe ao navegar.
  const telaEstreita = () => window.innerWidth <= 720
  const [menuAberto, setMenuAberto] = useState(() => !telaEstreita() && !(compactoInicial && (window.innerWidth < 1500 || window.innerHeight < 850)))
  const [apresentarLink, setApresentarLink] = useState(
    () => localStorage.getItem(chaveApresentacao) !== 'sim',
  )
  const [etapaApresentacaoLink, setEtapaApresentacaoLink] = useState(0)
  const localizacao = useLocation()
  const itensVisiveis = itensMenu.filter(
    (item) => !item.papel || item.papel === usuario.papel,
  )

  async function encerrarAcesso() {
    await sair()
    navegar('/login', { replace: true })
  }

  function concluirApresentacaoLink() {
    localStorage.setItem(chaveApresentacao, 'sim')
    setApresentarLink(false)
  }

  function avancarApresentacaoLink() {
    if (etapaApresentacaoLink === etapasApresentacaoLink.length - 1) {
      concluirApresentacaoLink()
      return
    }
    setEtapaApresentacaoLink((etapa) => etapa + 1)
  }

  // O último botão leva direto ao próximo passo da trilha (a aula 1, para quem é novo).
  const ultimaEtapa = etapaApresentacaoLink === etapasApresentacaoLink.length - 1
  const [proximoPasso, setProximoPasso] = useState(null)
  useEffect(() => {
    if (!apresentarLink) return undefined
    let ativo = true
    fetch('/api/progresso/me', { credentials: 'same-origin' })
      .then((resposta) => resposta.json())
      .then((dados) => { if (ativo && dados.sucesso) setProximoPasso(resumoInicio(dados.progresso).proximo) })
      .catch(() => {})
    return () => { ativo = false }
  }, [apresentarLink])

  // Quem já começou a trilha (Ajuda) vê o próprio próximo passo no lugar de "Comece pela aula 1".
  const apresentacaoAtual = ultimaEtapa && proximoPasso && proximoPasso.numero > 1
    ? { ...etapasApresentacaoLink[etapaApresentacaoLink], etiqueta: 'POR ONDE SEGUIR', titulo: 'Siga o seu próximo passo',
        texto: `Seu próximo passo é a parada ${proximoPasso.numero} da trilha: “${proximoPasso.titulo}”. A Início sempre mostra esse caminho, e a Trilha mostra o curso inteiro.` }
    : etapasApresentacaoLink[etapaApresentacaoLink]

  function irParaProximoPasso() {
    concluirApresentacaoLink()
    navegar(proximoPasso ? proximoPasso.caminho : '/trilha')
  }

  // "Ajuda" reabre a apresentação do Link, que termina explicando por onde seguir.
  function abrirAjuda() {
    setEtapaApresentacaoLink(0)
    setApresentarLink(true)
  }

  function voltarApresentacaoLink() {
    setEtapaApresentacaoLink((etapa) => Math.max(0, etapa - 1))
  }

  // O Lab 1 mora em /laboratorio (sem "s"): no topo ele aparece como Laboratórios, não como Início.
  const caminhoAtual = localizacao.pathname === '/laboratorio' ? '/laboratorios' : localizacao.pathname
  const itemAtual =
    itensVisiveis.find(
      (item) =>
        item.caminho !== '/' &&
        caminhoAtual.startsWith(item.caminho),
    ) ?? itensMenu[0]

  return (
    <div className={`aplicacao ${menuAberto ? '' : 'menu-recolhido'}`}>
      <aside className="sidebar">
        <div className="marca-area">
          <LogoPingLevel recolhido={!menuAberto} />

          <button
            className="botao-recolher"
            onClick={() => setMenuAberto(!menuAberto)}
            aria-label={menuAberto ? 'Recolher menu' : 'Abrir menu'}
          >
            {menuAberto ? (
              <ChevronLeft size={18} />
            ) : (
              <ChevronRight size={18} />
            )}
          </button>
        </div>

        <nav className="menu">
          {itensVisiveis.map((item) => {
            const Icone = item.icone

            return (
              <NavLink
                key={item.nome}
                to={item.caminho}
                end={item.caminho === '/'}
                className={({ isActive }) =>
                  `menu-item ${isActive ? 'ativo' : ''}`
                }
                title={!menuAberto ? item.nome : undefined}
                style={{ textDecoration: 'none' }}
                onClick={() => { if (telaEstreita()) setMenuAberto(false) }}
              >
                <Icone size={21} />
                {menuAberto && <span>{item.nome}</span>}
              </NavLink>
            )
          })}
        </nav>

        <div className="sidebar-rodape">
          <CriadoPor compacto={!menuAberto} />
        </div>
      </aside>

      <div className="conteudo">
        <header className="topbar">
          <button
            className="menu-mobile"
            onClick={() => setMenuAberto(!menuAberto)}
            aria-label="Abrir menu"
          >
            <Menu size={23} />
          </button>

          <div>
            <span className="saudacao">Olá, {usuario.nome.split(" ")[0]}</span>
            <strong>{itemAtual.nome}</strong>
          </div>

          <div className="topbar-acoes">
            <button className="ajuda" onClick={abrirAjuda}>
              <CircleHelp size={19} />
              <span>Ajuda</span>
            </button>

            <div className="usuario-menu">
              <div className="usuario-avatar" aria-hidden="true">
                {usuario.nome.charAt(0).toUpperCase()}
              </div>
              <div className="usuario-identidade">
                <strong>{usuario.nome}</strong>
                <span>{usuario.papel}</span>
              </div>
              <button
                className="sair"
                onClick={() => navegar('/alterar-senha')}
                aria-label="Alterar senha"
                title="Alterar senha"
              >
                <KeyRound size={18} />
              </button>

              <button
                className="sair"
                onClick={encerrarAcesso}
                aria-label="Sair da plataforma"
                title="Sair da plataforma"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </header>

        <Outlet />
      </div>

      {apresentarLink && (
        <div className="apresentacao-overlay" role="dialog" aria-modal="true">
          <section className="apresentacao-card">
            <button className="apresentacao-pular" onClick={concluirApresentacaoLink}>
              Pular apresentação
            </button>
            <div className="apresentacao-texto">
              <span className="apresentacao-etiqueta">{apresentacaoAtual.etiqueta}</span>
              <h2>{apresentacaoAtual.titulo}</h2>
              <p>{apresentacaoAtual.texto}</p>
              <p>{apresentacaoAtual.complemento}</p>
              <div className="apresentacao-passos">
                {etapasApresentacaoLink.map((etapa, indice) => (
                  <span key={etapa.titulo} className={indice <= etapaApresentacaoLink ? 'ativo' : ''} />
                ))}
              </div>
              <div className="apresentacao-acoes">
                {etapaApresentacaoLink > 0 && (
                  <button className="apresentacao-voltar" onClick={voltarApresentacaoLink}>
                    <ChevronLeft size={18} /> Voltar
                  </button>
                )}
                <button className="apresentacao-botao" onClick={ultimaEtapa ? irParaProximoPasso : avancarApresentacaoLink}>
                  {!ultimaEtapa ? 'Continuar' : !proximoPasso ? 'Ver a trilha' : proximoPasso.numero === 1 ? 'Começar a primeira aula' : proximoPasso.acao}
                  <ChevronRight size={19} />
                </button>
              </div>
              {ultimaEtapa && (
                <button className="apresentacao-explorar" onClick={concluirApresentacaoLink}>
                  Explorar a plataforma primeiro
                </button>
              )}
            </div>
            <div className="apresentacao-mascote">
              <div className="apresentacao-luz" />
              <img src={apresentacaoAtual.imagem} alt="Link, guia de aprendizagem do PingLevel" />
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default AppLayout
