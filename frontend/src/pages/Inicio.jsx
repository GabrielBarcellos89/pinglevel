import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Check, Globe2, Network, Play, Route, Server } from 'lucide-react'
import linkHome from '../assets/mascote/link-expansao-v1/link-home-rede-holografica.webp'
import { resumoInicio } from '../data/trilha'

// Arte de cada parada, na ordem da trilha (a mesma da página Trilha).
const ARTES = Object.entries(import.meta.glob('../assets/trilha/*.webp', { eager: true, import: 'default' }))
  .sort(([a], [b]) => a.localeCompare(b)).map(([, url]) => url)

const MODULOS = {
  1: { icone: Network, descricao: 'Redes, OSI e TCP/IP, IPv4, gateway e as primeiras configurações pelo terminal.' },
  2: { icone: Globe2, descricao: 'Sub-redes, VLSM e roteamento estático entre redes.' },
  3: { icone: Server, descricao: 'DHCP, DNS, ARP, switch, VLANs e o desafio final.' },
}

const ACAO_MODULO = { concluido: 'Revisar módulo', atual: 'Continuar módulo', andamento: 'Continuar módulo', 'a-fazer': 'Ver primeira parada' }
const TIPO = { aula: 'Aula', laboratorio: 'Laboratório', desafio: 'Desafio final' }

function Inicio() {
  const navigate = useNavigate()
  const [resumo, setResumo] = useState(null)

  useEffect(() => {
    let ativo = true

    fetch('/api/progresso/me', { credentials: 'same-origin' })
      .then((resposta) => resposta.json())
      .then((dados) => {
        if (ativo && dados.sucesso) setResumo(dados.progresso)
      })
      .catch(() => {})

    return () => {
      ativo = false
    }
  }, [])

  const { proximo, total, concluidas, laboratorios, modulos } = resumoInicio(resumo)
  const labsConcluidos = laboratorios.filter((p) => p.estado === 'concluida').length
  const percentual = Math.round((concluidas / total) * 100)

  return (
    <main className="principal">
      <section className="banner">
        <div className="banner-conteudo">
          <span className="etiqueta">
            {!proximo ? 'TRILHA CONCLUÍDA' : concluidas ? 'CONTINUE SUA JORNADA' : 'COMECE SUA JORNADA'}
          </span>

          <h1>
            Transforme conceitos
            <br />
            em <em>experiência prática.</em>
          </h1>

          <p>
            Aprenda redes passo a passo, teste seus conhecimentos e
            pratique em laboratórios reais acompanhado pelo Link.
          </p>

          {proximo ? (
            <div className="proximo-passo">
              <img src={ARTES[proximo.indice]} alt="" />
              <div className="proximo-texto">
                <span>Próximo passo · parada {proximo.numero} de {total} · {TIPO[proximo.tipo]}</span>
                <strong>{proximo.titulo}</strong>
              </div>
              <button className="botao-principal" onClick={() => navigate(proximo.caminho)}>
                <Play size={18} fill="currentColor" />
                {proximo.acao}
                <ArrowRight size={19} />
              </button>
            </div>
          ) : (
            <button className="botao-principal" onClick={() => navigate('/trilha')}>
              <Route size={18} />
              Ver a trilha completa
              <ArrowRight size={19} />
            </button>
          )}
        </div>

        <div className="banner-visual" aria-hidden="true">
          <img className="banner-link" src={linkHome} alt="" />
        </div>
      </section>

      <section className="resumo">
        <div className="resumo-texto">
          <span>SEU PROGRESSO</span>
          <strong>Trilha de redes</strong>
        </div>

        <div className="barra-progresso">
          <div className="barra-cabecalho">
            <span>{concluidas} de {total} paradas concluídas</span>
            <strong>{percentual}%</strong>
          </div>

          <div className="barra">
            <div style={{ width: `${percentual}%` }} />
          </div>
        </div>

        <div className="resumo-numeros">
          <div>
            <strong>{labsConcluidos} de {laboratorios.length}</strong>
            <span>laboratórios</span>
          </div>

          <div>
            <strong>{resumo?.xp_total ?? 0} XP</strong>
            <span>experiência</span>
          </div>
        </div>
      </section>

      <section className="secao-modulos">
        <div className="secao-cabecalho">
          <div>
            <span>TRILHA DE APRENDIZAGEM</span>
            <h2>Módulos do curso</h2>
          </div>

          <button className="ver-todos" onClick={() => navigate('/trilha')}>
            Ver a trilha
            <ArrowRight size={17} />
          </button>
        </div>

        <div className="grade-modulos">
          {modulos.map((modulo) => {
            const { icone: Icone, descricao } = MODULOS[modulo.numero]
            const progresso = Math.round((modulo.concluidas / modulo.total) * 100)

            return (
              <article className={`cartao-modulo ${modulo.estado === 'atual' ? 'atual' : ''}`} key={modulo.numero}>
                <div className="cartao-topo">
                  <span className="numero-modulo">
                    MÓDULO {modulo.numero}
                    {modulo.estado === 'atual' && <em> · você está aqui</em>}
                  </span>

                  <div className="icone-modulo">
                    {modulo.estado === 'concluido' ? <Check size={23} /> : <Icone size={23} />}
                  </div>
                </div>

                <h3>{modulo.nome}</h3>
                <p>
                  {modulo.aulas} aulas · {modulo.laboratorios} laboratórios
                  <br />
                  {descricao}
                </p>

                <div className="progresso-modulo">
                  <div className="barra pequena">
                    <div style={{ width: `${progresso}%` }} />
                  </div>
                  <span>{modulo.concluidas} de {modulo.total}</span>
                </div>

                <button className="acao-modulo" onClick={() => navigate(modulo.caminho)}>
                  {ACAO_MODULO[modulo.estado]}
                  <ArrowRight size={17} />
                </button>
              </article>
            )
          })}
        </div>
      </section>
    </main>
  )
}

export default Inicio
