import { ArrowRight } from 'lucide-react'

function PaginaEmConstrucao({
  etiqueta,
  titulo,
  descricao,
  icone: Icone,
}) {
  return (
    <main className="principal">
      <section className="secao-modulos">
        <div className="secao-cabecalho">
          <div>
            <span>{etiqueta}</span>
            <h2>{titulo}</h2>
          </div>
        </div>

        <div className="grade-modulos">
          <article className="cartao-modulo">
            <div className="cartao-topo">
              <span className="numero-modulo">
                ESTRUTURA INICIAL
              </span>

              <div className="icone-modulo">
                <Icone size={24} />
              </div>
            </div>

            <h3>{titulo}</h3>
            <p>{descricao}</p>

            <button className="acao-modulo">
              Conteúdo em desenvolvimento
              <ArrowRight size={17} />
            </button>
          </article>
        </div>
      </section>
    </main>
  )
}

export default PaginaEmConstrucao
