import { useLayoutEffect, useRef, useState } from 'react'

export default function ConversaLink({ mensagens, aoPerguntar, ocupado, disponivel, erro }) {
  const [pergunta, setPergunta] = useState('')
  const lista = useRef(null)
  useLayoutEffect(() => { if (lista.current) lista.current.scrollTop = lista.current.scrollHeight }, [mensagens.length])
  async function enviar(evento) {
    evento.preventDefault()
    if (!pergunta.trim() || ocupado || !disponivel) return
    if (await aoPerguntar(pergunta.trim())) setPergunta('')
  }
  return <section className="pl-conversa" aria-label="Conversa com o Link">
    {mensagens.length > 0 && <div ref={lista} className="pl-mensagens" aria-live="polite">
      {mensagens.map((item, index) => <article key={`${item.etapa}-${index}`}>
        <p className="pl-pergunta-aluno"><strong>Você:</strong> {item.pergunta}</p>
        <span className={`pl-modo-tutor ${item.modo === 'contingencia' ? 'pl-contingencia' : ''}`}>
          {item.modo === 'contingencia' ? 'Ajuda alternativa' : 'Link · materiais consultados'}
        </span>
        {item.aviso && <p className="pl-aviso-tutor">{item.aviso}</p>}
        <p className="pl-resposta-link">{item.resposta}</p>
        {item.fontes?.length > 0 && <details className="pl-fontes"><summary>Materiais consultados</summary><ul>
          {item.fontes.map((f, i) => <li key={i}>{f.guia || `${f.livro} · página ${f.pagina_pdf} do PDF`}</li>)}
        </ul></details>}
      </article>)}
    </div>}
    <form onSubmit={enviar}>
      <label htmlFor="pl-pergunta-link">Qual é sua dúvida?</label>
      <textarea id="pl-pergunta-link" aria-describedby="pl-dica-enter" value={pergunta} maxLength={400} rows={2}
        onChange={(e) => setPergunta(e.target.value)} disabled={!disponivel || ocupado}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form.requestSubmit() } }}
        placeholder="Conte o que você observou ou tentou…" />
      <small id="pl-dica-enter" className="pl-dica-enter">Enter envia · Shift+Enter quebra a linha</small>
      <button disabled={!disponivel || ocupado || !pergunta.trim()}>{ocupado ? 'Link está consultando…' : 'Perguntar ao Link'}</button>
      {!disponivel && <p className="pl-aviso-tutor">Inicie o ambiente para conversar sobre esta missão.</p>}
      {ocupado && <p role="status">Consultando a etapa e os materiais. Você pode continuar a prática.</p>}
      {erro && <p className="pl-erro-tutor" role="alert">{erro}</p>}
    </form>
  </section>
}
