import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Building2, Check, MapPin, MessageCircle, Package, Pencil, Radio, Server, Truck, Wifi } from 'lucide-react'
import './CenasPercursoOsi.css'

import { CONTEUDOS_ADICIONAIS, RECEBIMENTO, SIMPLES, TERMOS } from './conteudoPercursoOsi'

export function CenaCamada({ numero, concluida, onAcao }) {
  const conteudo = CONTEUDOS_ADICIONAIS[numero]
  return <section className="osi-atividade-camada" aria-label={`Explorar a camada ${numero}`}>
    {numero === 5 && <div className="osi-dialogo" data-testid="session-flow">
      <div className="osi-atividade-rotulo"><MessageCircle size={18} aria-hidden="true" /><span>Organização do diálogo</span></div>
      {concluida ? <ol className="osi-dialogo-passos"><li><strong>Início</strong><span>Estabelecer a troca</span></li><li><strong>Troca</strong><span>Coordenar o diálogo</span></li><li><strong>Encerramento</strong><span>Finalizar a interação</span></li></ol>
        : <p className="osi-atividade-espera">Vamos organizar os momentos dessa interação.</p>}
      <small>Representação de uma função do modelo, não de uma conexão TCP separada.</small>
    </div>}

    {numero === 4 && <div className="osi-portas" data-testid="transport-flow">
      <div className="osi-atividade-rotulo"><Server size={18} aria-hidden="true" /><span>Primeiro trecho · Ana → servidor</span></div>
      {concluida ? <div className="osi-extremos"><div><span>Processo do app de Ana</span><strong>Porta 55000</strong></div><ArrowRight size={22} aria-hidden="true" /><div><span>Serviço de mensagens no servidor</span><strong>Porta 80</strong></div></div>
        : <p className="osi-atividade-espera">O endereço do computador não basta para identificar um serviço.</p>}
      <small>Cenário ilustrativo com TCP e serviço de mensagens em HTTP. As portas são exemplos.</small>
    </div>}

    {numero === 3 && <div className="osi-enderecos" data-testid="network-destination">
      <div className="osi-atividade-rotulo"><Server size={18} aria-hidden="true" /><span>Destino deste trecho: servidor do aplicativo</span></div>
      {concluida ? <div className="osi-extremos"><div><span>IP ilustrativo de Ana</span><strong>192.0.2.34</strong></div><ArrowRight size={22} aria-hidden="true" /><div><span>IP ilustrativo do servidor</span><strong>198.51.100.20</strong></div></div>
        : <p className="osi-atividade-espera">Não confunda o nome do contato com o destino IP do primeiro trecho.</p>}
      <small>Endereços reservados para exemplos; nenhuma conexão é feita com eles.</small>
    </div>}

    {numero === 2 && <div className="osi-quadro-local">
      <div className="osi-atividade-rotulo"><Wifi size={18} aria-hidden="true" /><span>Primeiro enlace · celular de Ana → ponto de acesso</span></div>
      {concluida ? <div className="osi-quadro" data-testid="link-frame"><span className="osi-quadro-cabecalho">Cabeçalho Wi-Fi<small>Endereçamento MAC</small></span><div className="osi-pacote"><strong>Pacote IP</strong><div className="osi-segmento"><span>TCP</span><span>Dados do aplicativo</span></div></div><span className="osi-quadro-verificacao">Verificação<small>do quadro</small></span></div>
        : <p className="osi-atividade-espera">A entrega local usa um quadro adequado ao enlace.</p>}
      <small>Esquema simplificado de um quadro de dados Wi-Fi. Não é um quadro Ethernet.</small>
    </div>}

    {numero === 1 && <div className="osi-radio" data-testid="radio-signal" data-transmitted={concluida ? 'true' : 'false'}>
      <div className="osi-atividade-rotulo"><Radio size={18} aria-hidden="true" /><span>Wi-Fi · sinais de rádio no primeiro enlace</span></div>
      <div className="osi-radio-visual" aria-hidden="true"><span>Celular<br />de Ana</span><div className={`osi-ondas ${concluida ? 'osi-ondas-ativas' : ''}`}><i /><i /><i /></div><Wifi size={32} /><span>Ponto<br />de acesso</span></div>
      <p className="osi-radio-status" role="status">{concluida ? 'Transmissão representada no primeiro enlace.' : 'Aguardando sua ação para representar a transmissão.'}</p>
      <small>O restante da rede está resumido no cenário. Bruno ainda não recebeu a mensagem.</small>
    </div>}

    <button className="botao-secundario" onClick={onAcao} disabled={concluida}>{conteudo.acao}{concluida && <span aria-hidden="true"> · explorado</span>}</button>
  </section>
}

export function RecebimentoMensagem({ passo, onProximo, onAnterior, mensagem }) {
  const atual = RECEBIMENTO[passo]
  const ultima = passo === RECEBIMENTO.length - 1
  return <section className="osi-recebimento" aria-label="Percurso inverso no celular de Bruno">
    <div className="osi-ordens"><span><strong>Envio:</strong> 7 → 6 → 5 → 4 → 3 → 2 → 1</span><span><strong>Recebimento:</strong> 1 → 2 → 3 → 4 → 5 → 6 → 7</span></div>
    <ol className="osi-ordem-recebimento" data-testid="receive-order" aria-label="Camadas no recebimento, da Física à Aplicação">{RECEBIMENTO.map(({ numero, nome }) => <li key={numero} data-layer-number={numero} aria-current={numero === atual.numero ? 'step' : undefined} className={numero === atual.numero ? 'atual' : numero < atual.numero ? 'vista' : ''}><span>{numero}</span><strong>{nome}</strong></li>)}</ol>
    <div className="osi-recepcao-atual" aria-live="polite"><span className="osi-recepcao-numero" data-testid="receive-number">{atual.numero}</span><div><small>CAMADA NO RECEBIMENTO</small><h2>{atual.nome}</h2><p>{atual.texto}</p>{atual.numero === 6 && <p className="osi-texto-decodificado">Texto interpretado: <strong>{new TextDecoder('utf-8').decode(new TextEncoder().encode(mensagem))}</strong></p>}</div></div>
    <div className="osi-recepcao-controles"><button className="botao-secundario" onClick={onAnterior} disabled={passo === 0} aria-label="Camada anterior no recebimento"><ArrowLeft size={17} /> Anterior</button><button className="botao-secundario" onClick={onProximo} disabled={ultima} aria-label="Próxima camada no recebimento">{ultima ? 'Chegamos à Aplicação' : 'Próxima camada'}<ArrowRight size={17} /></button></div>
  </section>
}

const ENCOMENDA = [[Pencil, 'Escrever o bilhete'], [Package, 'Embalar'], [MapPin, 'Pôr o endereço'], [Building2, 'A agência separa'], [Truck, 'O caminhão leva']]
const NUMEROS = [7, 6, 5, 4, 3, 2, 1]

// Tela antes da tabela OSI: a ideia de dividir a comunicação em tarefas, com a analogia da encomenda.
export function IntroCamadas() {
  return <div className="osi-intro-camadas">
    <ol className="osi-encomenda" aria-label="Enviar uma encomenda pelo correio, em cinco tarefas">
      {ENCOMENDA.map(([Icone, texto], indice) => <li key={texto}><Icone size={26} aria-hidden="true" /><span>{indice + 1}</span><strong>{texto}</strong></li>)}
    </ol>
    <p className="osi-intro-moral">Cada um faz só a sua parte e confia no próximo. Ninguém precisa saber fazer tudo.</p>
    <div className="osi-intro-rede">
      <h2>Na rede é igual</h2>
      <p>Enviar uma mensagem envolve várias tarefas: preparar o texto, achar o destino, levar até o próximo equipamento,
        transformar tudo em sinais. O <strong>modelo OSI</strong> organiza essas tarefas em <strong>7 camadas</strong>.
        Ele serve para estudar e para achar defeitos: “o problema é no cabo ou no endereço?”.</p>
      <p>O <strong>TCP/IP</strong> é o modelo usado na Internet de verdade. Ele junta as mesmas tarefas em 4 grupos.
        Você vai vê-lo no fim desta aula.</p>
    </div>
    <div className="osi-intro-sentidos" aria-label="Quem envia desce da camada 7 até a 1; quem recebe sobe da 1 até a 7">
      <div><strong>Quem envia</strong><span>desce da 7 até a 1</span><ol>{NUMEROS.map((n) => <li key={n}>{n}</li>)}</ol><ArrowDown size={22} aria-hidden="true" /></div>
      <div><strong>Quem recebe</strong><span>sobe da 1 até a 7</span><ol>{NUMEROS.map((n) => <li key={n}>{n}</li>)}</ol><ArrowUp size={22} aria-hidden="true" /></div>
    </div>
  </div>
}

// Mapa sempre visível durante o envio: as 7 camadas, com a atual acesa e as já percorridas marcadas.
export function MapaCamadas({ atual, nomes }) {
  return <ol className="osi-mapa-fixo" aria-label={`Envio, da camada 7 até a 1. Agora: camada ${atual}`}>
    {NUMEROS.map((n) => <li key={n} className={n === atual ? 'atual' : n > atual ? 'feita' : ''} aria-current={n === atual ? 'step' : undefined}>
      <span>{n > atual ? <Check size={13} aria-hidden="true" /> : n}</span>{nomes[n]}
    </li>)}
  </ol>
}

// "Em palavras simples" e os termos novos da camada, sempre antes do texto técnico.
export function ExplicacaoSimples({ numero }) {
  return <div className="osi-simples">
    <p><strong>Em palavras simples:</strong> {SIMPLES[numero]}</p>
    {TERMOS[numero]?.length > 0 && <dl className="osi-termos" aria-label="Termos novos desta camada">
      {TERMOS[numero].map(([termo, definicao]) => <div key={termo}><dt>{termo}</dt><dd>{definicao}</dd></div>)}
    </dl>}
  </div>
}
