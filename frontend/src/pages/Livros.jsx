import { useMemo, useState } from 'react'
import { BookOpen, Download, ExternalLink, Heart, Library, LockKeyhole, Search, ShieldCheck } from 'lucide-react'

import linkEnsinando from '../assets/mascote/link-kit-v2/link-v2-ensinando.webp'
import './Livros.css'

const materiais = [
  {
    id: 'redes-iniciantes', categoria: 'Fundamentos', titulo: 'Redes para Iniciantes',
    autor: 'Eduardo Maroñas Monks', selo: 'Base do Tutor Link', origem: 'GitHub do autor',
    descricao: 'Uma introdução direta aos conceitos que sustentam a comunicação em redes de computadores.',
    capa: '/capas/redes-para-iniciantes.png',
    download: 'https://github.com/emmonks/Livro_Redes_Iniciantes/releases/download/v1/Redes_para_Iniciantes_v1.pdf',
    fonte: 'https://github.com/emmonks/Livro_Redes_Iniciantes',
  },
  {
    id: 'linux-utilitarios', categoria: 'Linux e redes', titulo: 'Linux: Utilitários de Redes',
    autor: 'Eduardo Maroñas Monks', selo: 'Base do Tutor Link', origem: 'GitHub do autor',
    descricao: 'Comandos e ferramentas Linux para observar, diagnosticar e administrar redes.',
    capa: '/capas/linux-utilitarios-redes.png',
    download: 'https://github.com/emmonks/Livro_Linux_Utilitarios_de_Redes/blob/main/LivroUtilitariosRede_v1_7.pdf',
    fonte: 'https://github.com/emmonks/Livro_Linux_Utilitarios_de_Redes',
  },
  {
    id: '50-dicas', categoria: 'Administração', titulo: '++50 Dicas para Administradores de Redes',
    autor: 'Eduardo Maroñas Monks', origem: 'GitHub do autor',
    descricao: 'Dicas práticas reunidas a partir da experiência do autor em administração de redes.',
    capa: '/capas/50-dicas-administradores.png',
    download: 'https://github.com/emmonks/50Dicas/releases/download/v2/++50.Dicas.para.Administradores.de.Redes_v2.pdf',
    fonte: 'https://github.com/emmonks/50Dicas',
  },
  {
    id: 'switches-gerenciaveis', categoria: 'Switching', titulo: 'Administração de Switches Gerenciáveis',
    autor: 'Eduardo Maroñas Monks', origem: 'GitHub do autor',
    descricao: 'Um guia prático para conhecer switching e administrar switches gerenciáveis.',
    capa: '/capas/administracao-switches.png',
    download: 'https://github.com/emmonks/Livro_Adm_Switches/releases/download/V1/Livro_ADM_Switches_Gerenciaveis_v1.pdf',
    fonte: 'https://github.com/emmonks/Livro_Adm_Switches',
  },
  {
    id: 'fasciculos-cert', categoria: 'Segurança', titulo: 'Fascículos de Segurança para Internet',
    autor: 'CERT.br • NIC.br • CGI.br', selo: 'Coleção oficial', origem: 'Fonte institucional',
    descricao: 'Coleção atualizada sobre redes, autenticação, golpes, privacidade, backup e segurança digital.',
    capa: '/capas/fasciculo-redes-cert.png',
    download: 'https://cartilha.cert.br/fasciculos/', fonte: 'https://cartilha.cert.br/fasciculos/',
  },
  {
    id: 'em-breve', categoria: 'Em breve', titulo: 'Novos livros estão a caminho',
    autor: 'Curadoria PingLevel', origem: 'Em curadoria', disponivel: false,
    descricao: 'A biblioteca crescerá com materiais gratuitos, atuais e publicados por fontes confiáveis.',
  },
]

const categorias = ['Todos', 'Fundamentos', 'Linux e redes', 'Administração', 'Switching', 'Segurança']

function Livros() {
  const [busca, setBusca] = useState('')
  const [categoria, setCategoria] = useState('Todos')
  const materiaisFiltrados = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    return materiais.filter((material) => {
      const texto = `${material.titulo} ${material.autor} ${material.descricao} ${material.categoria}`.toLocaleLowerCase('pt-BR')
      return (categoria === 'Todos' || material.categoria === categoria) && (!termo || texto.includes(termo))
    })
  }, [busca, categoria])

  return (
    <main className="livros-pagina">
      <section className="livros-hero">
        <div className="livros-hero-conteudo">
          <span>BIBLIOTECA PINGLEVEL</span>
          <h1>Conhecimento aberto para você ir além.</h1>
          <p>Livros e materiais gratuitos selecionados para complementar sua jornada. Todo download leva à fonte oficial e preserva os créditos.</p>
          <a href="#acervo"><BookOpen size={18} /> Explorar acervo</a>
        </div>
        <div className="livros-link">
          <img src={linkEnsinando} alt="Link apresentando a Biblioteca PingLevel" />
          <div><strong>Curadoria responsável</strong><p>Materiais gratuitos, autores creditados e links oficiais.</p></div>
        </div>
      </section>

      <section className="livros-controles" aria-label="Filtros da biblioteca">
        <label className="livros-busca"><Search size={18} /><input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por título, autor ou assunto..." /></label>
        <div className="livros-filtros">
          {categorias.map((item) => <button type="button" key={item} className={categoria === item ? 'ativo' : ''} onClick={() => setCategoria(item)}>{item}</button>)}
        </div>
      </section>

      <section className="livros-secao" id="acervo">
        <header><div><span>ACERVO SELECIONADO</span><h2>Explore a biblioteca</h2></div><strong>{materiaisFiltrados.length} materiais</strong></header>
        {materiaisFiltrados.length ? (
          <div className="livros-grade">
            {materiaisFiltrados.map((material) => (
              <article className={`livro-card ${material.disponivel === false ? 'indisponivel' : ''}`} key={material.id}>
                <div className="livro-capa">
                  {material.capa ? <img src={material.capa} alt={`Capa de ${material.titulo}`} /> : <div className="livro-capa-breve"><Library size={42} /><span>EM BREVE</span></div>}
                </div>
                <div className="livro-conteudo">
                  <div className="livro-metadados"><span>{material.categoria}</span>{material.selo && <strong><ShieldCheck size={12} /> {material.selo}</strong>}</div>
                  <h3>{material.titulo}</h3><small className="livro-autor">Por {material.autor}</small><p>{material.descricao}</p>
                  <div className="livro-origem">{material.origem}</div>
                  <div className="livro-acoes">
                    {material.disponivel === false ? <button type="button" disabled><LockKeyhole size={14} /> Em breve</button> : <><a className="livro-download" href={material.download} target="_blank" rel="noreferrer"><Download size={15} /> Baixar na fonte oficial</a><a className="livro-fonte" href={material.fonte} target="_blank" rel="noreferrer" aria-label={`Conhecer a fonte de ${material.titulo}`}><ExternalLink size={16} /></a></>}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : <div className="livros-vazio"><Search size={25} /><strong>Nenhum material encontrado</strong><p>Tente buscar outro termo ou selecionar uma categoria diferente.</p></div>}
      </section>

      <section className="livros-agradecimento" aria-label="Agradecimento">
        <Heart size={20} aria-hidden="true" />
        <p>
          <strong>Agradecimento ao professor Eduardo Maroñas Monks.</strong> O Link responde com base nos livros dele,
          usados no PingLevel com a sua autorização. Muito obrigado pela generosidade e pelo apoio ao projeto.
        </p>
      </section>
    </main>
  )
}

export default Livros
