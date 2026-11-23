import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ATIVIDADES, situacaoAtividade } from '../src/data/catalogo.js'

test('Lab3 aparece no catálogo e usa conclusão autenticada sem recriar IDs existentes', () => {
  const item=ATIVIDADES.find(a=>a.id==='saindo-da-rede-local')
  assert.ok(item,'Falta o Lab3 no catálogo')
  assert.equal(item.tipo,'laboratorio')
  assert.equal(item.caminho,'/laboratorios/saindo-da-rede-local')
  assert.equal(situacaoAtividade(item,{aulas:[],laboratorios:[]}).acao,'Iniciar')
  assert.equal(situacaoAtividade(item,{aulas:[],laboratorios:[{laboratorio_id:item.id,concluido:true}]}).acao,'Revisar')
  for(const id of ['primeiro-contato','primeira-lan','enderecamento-ipv4'])assert.ok(ATIVIDADES.some(a=>a.id===id))
})

test('rota do Lab3 integrada à aplicação com layout compacto próprio',()=>{
 const source=readFileSync(new URL('../src/App.jsx',import.meta.url),'utf8')
 assert.match(source,/import LaboratorioGateway from '.\/pages\/LaboratorioGateway'/)
 assert.match(source,/<AppLayout key="gateway-guiado" compactoInicial/)
 assert.match(source,/path="laboratorios\/saindo-da-rede-local" element=\{<LaboratorioGateway \/>\}/)
})

test('Primeiro Contato direciona conflito com Lab3 para sua própria rota',()=>{
 const source=readFileSync(new URL('../src/pages/Laboratorio.jsx',import.meta.url),'utf8')
 assert.match(source,/outroLaboratorio === 'saindo-da-rede-local' \? '\/laboratorios\/saindo-da-rede-local'/)
})
