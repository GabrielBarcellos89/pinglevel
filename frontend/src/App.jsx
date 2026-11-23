import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Info } from 'lucide-react'

import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'
import AlterarSenha from './pages/AlterarSenha'
import AulaFundamentosRede from './pages/AulaFundamentosRede'
import AulaGateway from './pages/AulaGateway'
import AulaFerramentas from './pages/AulaFerramentas'
import AulaPlanoEnderecamento from './pages/AulaPlanoEnderecamento'
import AulaVlsm from './pages/AulaVlsm'
import AulaRoteamento from './pages/AulaRoteamento'
import AulaLan from './pages/AulaLan'
import AulaDhcpDns from './pages/AulaDhcpDns'
import AulaEthernetArp from './pages/AulaEthernetArp'
import AulaTransporte from './pages/AulaTransporte'
import { LaboratorioConectandoRedes, LaboratorioDesafioEmpresa, LaboratorioDividindoRede, LaboratorioEnderecosNomes, LaboratorioInvestigandoLan,
  LaboratorioPlanejandoEmpresa, LaboratorioPrimeiraLAN, LaboratorioSuporteRemoto } from './pages/LaboratorioRede'
import PainelCarga from './pages/PainelCarga'
import AulaModelosRede from './pages/AulaModelosRede'
import PreviaMensagemOsi from './pages/PreviaMensagemOsi'
import AulaEnderecoIPv4 from './pages/AulaEnderecoIPv4'
import PreviaEnderecoIPv4 from './pages/PreviaEnderecoIPv4'
import Inicio from './pages/Inicio'
import Catalogo from './pages/Catalogo'
import Trilha from './pages/Trilha'
import Login from './pages/Login'
import Laboratorio from './pages/Laboratorio'
import LaboratorioGateway from './pages/LaboratorioGateway'
import LaboratorioTerminal from './pages/LaboratorioTerminal'
import PreviaLaboratorioResponsivo from './pages/PreviaLaboratorioResponsivo'
import Livros from './pages/Livros'
import PaginaEmConstrucao from './pages/PaginaEmConstrucao'
import PainelProfessor from './pages/PainelProfessor'
import PainelAdministrador from './pages/PainelAdministrador'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route path="alterar-senha" element={<AlterarSenha />} />

            <Route element={<AppLayout key="previa-responsiva" compactoInicial />}>
              <Route path="laboratorio/previa-responsiva" element={<PreviaLaboratorioResponsivo />} />
            </Route>
            <Route element={<AppLayout key="laboratorio-responsivo" compactoInicial />}>
              <Route path="laboratorio" element={<Laboratorio />} />
            </Route>
            <Route element={<AppLayout key="gateway-guiado" compactoInicial />}>
              <Route path="laboratorios/saindo-da-rede-local" element={<LaboratorioGateway />} />
            </Route>
            <Route element={<AppLayout key="terminal-guiado" compactoInicial />}>
              <Route path="laboratorios/configure-pelo-terminal" element={<LaboratorioTerminal />} />
              <Route path="laboratorios/dividindo-uma-rede" element={<LaboratorioDividindoRede />} />
              <Route path="laboratorios/planejando-uma-empresa" element={<LaboratorioPlanejandoEmpresa />} />
              <Route path="laboratorios/conectando-redes" element={<LaboratorioConectandoRedes />} />
              <Route path="laboratorios/enderecos-e-nomes" element={<LaboratorioEnderecosNomes />} />
              <Route path="laboratorios/investigando-a-lan" element={<LaboratorioInvestigandoLan />} />
              <Route path="laboratorios/desafio-rede-da-empresa" element={<LaboratorioDesafioEmpresa />} />
              <Route path="teste-de-carga" element={<LaboratorioSuporteRemoto />} />
            </Route>
            <Route element={<AppLayout />}>
              <Route index element={<Inicio />} />
              <Route path="trilha" element={<Trilha />} />
              <Route path="modulos" element={<Catalogo tipoInicial="aula" />} />
              <Route path="laboratorios" element={<Catalogo tipoInicial="laboratorio" />} />
              <Route path="modulos/fundamentos/aula-1" element={<AulaFundamentosRede />} />
              <Route path="modulos/fundamentos/gateway" element={<AulaGateway />} />
              <Route path="modulos/fundamentos/ferramentas" element={<AulaFerramentas />} />
              <Route path="modulos/planejamento/enderecamento" element={<AulaPlanoEnderecamento />} />
              <Route path="modulos/planejamento/vlsm" element={<AulaVlsm />} />
              <Route path="modulos/planejamento/roteamento" element={<AulaRoteamento />} />
              <Route path="modulos/servicos/dhcp-dns" element={<AulaDhcpDns />} />
              <Route path="modulos/servicos/lan" element={<AulaLan />} />
              <Route path="modulos/servicos/transporte" element={<AulaTransporte />} />
              <Route path="modulos/fundamentos/ethernet-arp" element={<AulaEthernetArp />} />
              <Route path="modulos/fundamentos/modelos-de-rede" element={<AulaModelosRede />} />
              <Route path="modulos/fundamentos/modelos-de-rede/previa" element={<PreviaMensagemOsi />} />
              <Route path="modulos/enderecamento/ipv4" element={<AulaEnderecoIPv4 />} />
              <Route path="modulos/enderecamento/ipv4/previa" element={<PreviaEnderecoIPv4 />} />
              <Route path="laboratorios/primeira-lan" element={<LaboratorioPrimeiraLAN />} />
              <Route path="livros" element={<Livros />} />
              <Route path="sobre" element={<PaginaEmConstrucao etiqueta="SOBRE O PROJETO" titulo="Sobre" descricao="Conheça a motivação, os objetivos acadêmicos e as tecnologias utilizadas pelo PingLevel." icone={Info} />} />
              <Route element={<ProtectedRoute papel="professor" />}>
                <Route path="professor" element={<PainelProfessor />} />
              </Route>
              <Route element={<ProtectedRoute papel="administrador" />}>
                <Route path="administrador" element={<PainelAdministrador />} />
                <Route path="administrador/painel-carga" element={<PainelCarga />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
