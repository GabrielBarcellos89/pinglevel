import test from 'node:test'
import assert from 'node:assert/strict'
import { LAB5, LAB6, LAB7, LAB8, LAB9, LAB10 } from '../src/services/labsSetores.js'
import { criarClienteTerminal } from '../src/services/terminalGuiado.js'
import { ATIVIDADES } from '../src/data/catalogo.js'

const base = { ativo: true, indice: 0, abaAtual: 'v1' }

test('Lab 5: orientação por etapa leva à aba certa e não entrega o plano', () => {
  const plano = LAB5.orientar({ ...base, etapa: 'plano' })
  assert.equal(plano.alvo, 'plano')
  assert.doesNotMatch(plano.texto, /\.64|\.65|\.127/)
  assert.equal(LAB5.orientar({ ...base, etapa: 'roteador', indice: 1 }).alvo, 'aba-roteador')
  assert.match(LAB5.orientar({ ...base, etapa: 'roteador', indice: 1, abaAtual: 'roteador' }).texto, /dev eth1/)
  assert.equal(LAB5.orientar({ ...base, etapa: 'financeiro', indice: 2, abaAtual: 'f2' }).alvo, 'comando')
  assert.equal(LAB5.orientar({ ...base, etapa: 'chamado', indice: 3, observou: true }).alvo, 'causa')
  assert.doesNotMatch(LAB5.orientar({ ...base, etapa: 'chamado', indice: 3, abaAtual: 'v2' }).texto, /bloco|\.70/)
  assert.equal(LAB5.orientar({ ...base, etapa: 'comprovar', indice: 4 }).alvo, 'concluir')
  assert.equal(LAB5.orientar({ ativo: false }).alvo, 'iniciar')
})

test('Lab 6: plano sem respostas e etiqueta com quatro etapas', () => {
  const plano = LAB6.orientar({ ...base, etapa: 'plano', abaAtual: 'atendimento' })
  assert.equal(plano.etiqueta, 'ETAPA 1 DE 4')
  assert.doesNotMatch(plano.texto, /\/2[5-7]|\.128|\.192/)
  assert.equal(LAB6.orientar({ ...base, etapa: 'roteador', indice: 1, abaAtual: 'vendas' }).alvo, 'aba-roteador')
  assert.equal(LAB6.orientar({ ...base, recuperacao: true, etapa: 'pcs' }).alvo, 'atualizar')
})

test('cliente com outro prefixo envia o plano como texto', async () => {
  const chamadas = []
  const api = criarClienteTerminal({ base: '/api/lab5', fetchImpl: async (url, o) => {
    chamadas.push({ url, corpo: JSON.parse(o.body) })
    return { ok: true, status: 200, json: async () => ({ sucesso: true, disponivel: true }) }
  } })
  await api.planejar({ session_id: 2, revisao: 1, respostas: { rede: '192.168.50.64', prefixo: 26 }, extra: 1 })
  assert.equal(chamadas[0].url, '/api/lab5/planejar')
  assert.deepEqual(chamadas[0].corpo, { session_id: 2, revisao: 1, respostas: { rede: '192.168.50.64', prefixo: '26' } })
})

test('Labs 5 e 6 no catálogo do Módulo 2', () => {
  for (const id of ['dividindo-uma-rede', 'planejando-uma-empresa', 'conectando-redes']) {
    const item = ATIVIDADES.find((a) => a.id === id)
    assert.equal(item.modulo, 'planejamento')
    assert.equal(item.caminho, `/laboratorios/${id}`)
  }
})

test('Lab 7: ida antes da volta, sem entregar a rota', () => {
  const b = { ativo: true, abaAtual: 'pca', estados: { r1: { rotas: [] }, r2: { rotas: [] } } }
  assert.equal(LAB7.orientar({ ...b, etapa: 'chamado', indice: 0 }).alvo, 'comando')
  const sus = [{ no: 'pca', onde: 'PC A', texto: 'O PC A tem gateway?', comando: 'ip route', olhar: 'Existe uma linha default via?', testada: false },
    { no: 'r1', onde: 'R1', texto: 'O enlace funciona?', comando: 'ping 10.0.0.2', olhar: 'O R2 responde?', testada: false }]
  assert.equal(LAB7.orientar({ ...b, etapa: 'chamado', indice: 0, abaAtual: 'pca', suspeitas: sus }).titulo, 'Reproduza o problema')
  const s1 = LAB7.orientar({ ...b, etapa: 'chamado', indice: 0, abaAtual: 'pca', suspeitas: sus, testes: { pca: { '192.168.20.10': false } } })
  assert.equal(s1.titulo, 'Suspeita 1 de 2')
  assert.match(s1.texto, /ip route/)
  const s2 = LAB7.orientar({ ...b, etapa: 'chamado', indice: 0, abaAtual: 'pca', suspeitas: [{ ...sus[0], testada: true }, sus[1]] })
  assert.equal(s2.alvo, 'aba-r1')
  const causa = LAB7.orientar({ ...b, etapa: 'chamado', indice: 0, suspeitas: sus.map((x) => ({ ...x, testada: true })) })
  assert.equal(causa.alvo, 'causa')
  assert.doesNotMatch(causa.texto, /não tem rota|sem rota/)
  assert.equal(LAB7.orientar({ ...b, etapa: 'ida', indice: 2 }).alvo, 'aba-r1')
  const ida = LAB7.orientar({ ...b, etapa: 'ida', indice: 2, abaAtual: 'r1' })
  assert.match(ida.texto, /<rede>\/<prefixo> via <próximo salto>/)
  assert.doesNotMatch(ida.texto, /192\.168\.20\.0|10\.0\.0\.2/)
  const teste = LAB7.orientar({ ...b, etapa: 'ida', indice: 2, estados: { r1: { rotas: ['x'] }, r2: { rotas: [] } } })
  assert.match(teste.texto, /será que basta/)
  assert.equal(LAB7.orientar({ ...b, etapa: 'volta', indice: 3 }).alvo, 'aba-r2')
})

test('Lab 9: investigação sem a resposta, chamado leva ao switch e porta só aparece depois de conferida', () => {
  // Investigação um passo por vez, com a aba marcada: ping, tabela ARP do PC F1, tabela MAC do switch, painel.
  assert.equal(LAB9.orientar({ ...base, etapa: 'investigar' }).alvo, 'aba-f1')
  assert.match(LAB9.orientar({ ...base, etapa: 'investigar', abaAtual: 'f1' }).pistas[1], /^ping 192\.168\.30\.22$/)
  const pingou = [{ pc: 'f1', tipo: 'ping' }]
  assert.match(LAB9.orientar({ ...base, etapa: 'investigar', abaAtual: 'f1', historico: pingou }).pistas[1], /^ip neigh show$/)
  const arp = [...pingou, { pc: 'f1', tipo: 'ver-vizinhos' }]
  assert.equal(LAB9.orientar({ ...base, etapa: 'investigar', abaAtual: 'f1', historico: arp }).alvo, 'aba-switch')
  const mac = LAB9.orientar({ ...base, etapa: 'investigar', abaAtual: 'switch', historico: arp })
  assert.match(mac.texto, /não tem tabela ARP/)
  assert.equal(mac.pistas[1], 'bridge fdb show')
  const investigar = LAB9.orientar({ ...base, etapa: 'investigar', historico: [...arp, { pc: 'switch', tipo: 'ver-fdb' }] })
  assert.equal(investigar.alvo, 'plano')
  assert.doesNotMatch(investigar.texto, /02:16|eth3/)
  // A ARP lida antes do ping não conta: a tabela ainda não tinha o PC F2.
  assert.match(LAB9.orientar({ ...base, etapa: 'investigar', abaAtual: 'f1', historico: [{ pc: 'f1', tipo: 'ver-vizinhos' }, ...pingou] }).titulo, /tabela ARP/)
  // Correções no switch: entrar na VLAN certa, sair da errada, testar.
  const vlans = (eth1) => ({ switch: { vlans: { eth1 } } })
  const corrigir = (eth1, abaAtual = 'switch') => LAB9.orientar({ ...base, etapa: 'chamado', indice: 1, causaIdentificada: true, abaAtual, estados: vlans(eth1) })
  assert.match(corrigir({ pvid: 20, membro: [20], untagged: [20] }).pistas[1], /bridge vlan add dev <porta> vid <VLAN> pvid untagged/)
  assert.match(corrigir({ pvid: 10, membro: [10, 20], untagged: [10, 20] }).titulo, /eth1 fora da VLAN 20 · 2 de 2/)
  assert.equal(corrigir({ pvid: 10, membro: [10], untagged: [10] }).alvo, 'aba-v2')
  assert.equal(LAB9.comandos({ tipo: 'switch' }).startsWith('bridge link show, bridge fdb show e bridge vlan show'), true)
  assert.equal(LAB9.orientar({ ...base, etapa: 'chamado', indice: 1 }).alvo, 'aba-switch')
  assert.equal(LAB9.orientar({ ...base, etapa: 'chamado', indice: 1, observou: true }).alvo, 'causa')
  assert.doesNotMatch(LAB9.orientar({ ...base, etapa: 'chamado', indice: 1, abaAtual: 'switch' }).texto, /VLAN 20|errad/)
  assert.equal(LAB9.orientar({ ...base, etapa: 'chamado', indice: 1, causaIdentificada: true, abaAtual: 'switch' }).alvo, 'comando')
  const nos = [{ chave: 'f2', nome: 'PC F2' }]
  assert.equal(LAB9.rotuloPc('f2', { nos, portas: {} }), 'porta ?')
  assert.equal(LAB9.rotuloPc('f2', { nos, portas: { eth3: 'PC F2' } }), 'porta eth3')
  assert.ok(ATIVIDADES.some((a) => a.id === LAB9.id && a.caminho === '/laboratorios/investigando-a-lan'))
})

test('Lab 8: cada chamado na aba do PC, investigar antes da causa, sem entregar a resposta do chamado 3', () => {
  assert.equal(LAB8.orientar({ ...base, etapa: 'novo', abaAtual: 'recepcao' }).alvo, 'aba-novo')
  assert.match(LAB8.orientar({ ...base, etapa: 'novo', abaAtual: 'novo' }).texto, /ip addr show/)
  assert.equal(LAB8.orientar({ ...base, etapa: 'novo', abaAtual: 'novo', observou: true }).alvo, 'causa')
  assert.match(LAB8.orientar({ ...base, etapa: 'novo', abaAtual: 'novo', causaIdentificada: true }).texto, /dhclient eth0/)
  assert.match(LAB8.orientar({ ...base, etapa: 'novo', abaAtual: 'novo', causaIdentificada: true, progresso: { configuracao: true } }).texto, /intranet\.empresa\.local/)
  const terceiro = LAB8.orientar({ ...base, etapa: 'financeiro', indice: 2, abaAtual: 'financeiro' })
  assert.doesNotMatch(terceiro.texto, /impressora\.empresa|escrit|errad/)
  assert.equal(LAB8.passosChamado({ etapa: 'financeiro', no: 'financeiro' }, { financeiro: { nome: 'PC Financeiro' } })[2], 'Nada a corrigir no PC')
  assert.equal(LAB8.rotuloPc('novo', { nos: [{ chave: 'novo', tipo: 'pc' }], estados: { novo: { dns: ['192.168.40.2'] } } }), 'DNS 192.168.40.2')
  assert.ok(ATIVIDADES.some((a) => a.id === LAB8.id && a.caminho === '/laboratorios/enderecos-e-nomes'))
})

test('Lab 10: só o sintoma, sem apontar o equipamento nem a causa', () => {
  for (const etapa of ['intranet', 'vlan', 'dhcp', 'dns']) {
    const o = LAB10.orientar({ ...base, etapa, abaAtual: 'v1' })
    assert.equal(o.alvo, 'comando')
    assert.doesNotMatch(o.texto, /rota padrão|VLAN|dhclient|udhcpc|resolv|servidor intranet/)
  }
  // Quem abriu o chamado aparece e a aba dele é marcada até o primeiro comando nele; depois, só o método.
  const pcV2 = { ...base, etapa: 'vlan', chamadoNo: 'v2', nomeChamado: 'PC V2' }
  assert.equal(LAB10.orientar({ ...pcV2, abaAtual: 'v1' }).alvo, 'aba-v2')
  assert.match(LAB10.orientar({ ...pcV2, abaAtual: 'v2' }).texto, /Quem abriu o chamado foi o PC V2/)
  assert.equal(LAB10.orientar({ ...pcV2, abaAtual: 'switch', historico: [{ pc: 'v2', tipo: 'ping' }] }).alvo, 'comando')
  // Pistas sob pedido: a 2ª ajuda com o comando, com a porta e a VLAN para o aluno completar.
  const investigar = LAB10.orientar({ ...pcV2, abaAtual: 'v2' })
  assert.equal(investigar.pistas.length, 2)
  assert.match(investigar.pistas[1], /bridge vlan show/)
  const corrigir = LAB10.orientar({ ...pcV2, abaAtual: 'switch', causaIdentificada: true, historico: [{ pc: 'v2', tipo: 'ping' }] })
  assert.match(corrigir.pistas[1], /bridge vlan add dev <porta do PC V2> vid <VLAN do Vendas> pvid untagged/)
  assert.equal(LAB10.orientar({ ...base, etapa: 'dhcp', abaAtual: 'f1', causaIdentificada: true }).pistas[1], 'dhclient eth0')
  assert.equal(LAB10.orientar({ ...base, etapa: 'dns', observou: true }).alvo, 'causa')
  assert.equal(LAB10.orientar({ ...base, etapa: 'comprovar', indice: 4 }).alvo, 'concluir')
  const nos = [{ chave: 'v2', nome: 'PC V2', tipo: 'pc' }]
  assert.equal(LAB10.rotuloPc('v2', { nos, portas: { eth1: 'PC V2' }, estados: { v2: { dns: [] } } }), 'porta eth1 · sem DNS')
  assert.ok(ATIVIDADES.some((a) => a.id === LAB10.id && a.caminho === '/laboratorios/desafio-rede-da-empresa'))
})
