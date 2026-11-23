import {
  Activity,
  BookOpen,
  Gauge,
  FlaskConical,
  House,
  Library,
  Route,
  UsersRound,
  ShieldCheck,
} from 'lucide-react'

export const itensMenu = [
  {
    nome: 'Início',
    caminho: '/',
    icone: House,
  },
  {
    nome: 'Trilha',
    caminho: '/trilha',
    icone: Route,
  },
  {
    nome: 'Aulas',
    caminho: '/modulos',
    icone: BookOpen,
  },
  {
    nome: 'Laboratórios',
    caminho: '/laboratorios',
    icone: FlaskConical,
  },
  {
    nome: 'Livros',
    caminho: '/livros',
    icone: Library,
  },
  {
    nome: 'Teste de carga',
    caminho: '/teste-de-carga',
    icone: Activity,
  },
  {
    nome: 'Minha turma',
    caminho: '/professor',
    icone: UsersRound,
    papel: 'professor',
  },
  {
    nome: 'Administração',
    caminho: '/administrador',
    icone: ShieldCheck,
    papel: 'administrador',
  },
  {
    nome: 'Painel de carga',
    caminho: '/administrador/painel-carga',
    icone: Gauge,
    papel: 'administrador',
  },
]
