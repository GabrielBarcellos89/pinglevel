"""Método criar real compilado por AST, sem importar/iniciar SDK CORE."""
import ast, threading, time, unittest
from apoio_gerenciador import constantes
from pathlib import Path
from types import SimpleNamespace as NS
from laboratorios.topologia_gateway import construir, preparar
from laboratorios import topologia_setores

class Session:
    id=77
    def __init__(self):self.nodes={};self.links=[];self.options={}
    def set_options(self,v):self.options=v
    def add_node(self,id,**kw):n=NS(id=id,**kw);self.nodes[id]=n;return n
    def add_link(self,**kw):self.links.append(kw)
class Core:
    def __init__(self):self.session=Session();self.deleted=[];self.commands=[];self.closed=False;self.fail_prepare=False;self.fail_delete=False
    def create_session(self):return self.session
    def start_session(self,s):return True,[]
    def node_command(self,sid,node,cmd,**kw):
        self.commands.append((sid,node,cmd))
        return (1,'iptables ausente') if self.fail_prepare and 'iptables -P' in cmd else (0,'')
    def delete_session(self,sid):
        if self.fail_delete:raise RuntimeError('CORE sem confirmação')
        self.deleted.append(sid);return True
    def get_sessions(self):return [] if 77 in self.deleted else [NS(id=77)]
    def get_session(self,sid):return self.session
    def close(self):self.closed=True

class CriacaoGateway(unittest.TestCase):
    def setUp(self):
        filename=Path(__file__).resolve().parents[1]/'gerenciador.py';tree=ast.parse(filename.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GerenciadorLaboratorios');metodos=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('criar','_criar')]
        self.core=Core();self.saved=[]
        self.engine=NS(_lock=threading.RLock(),obter=lambda uid:None,_indice_disponivel=lambda uid:9,_core=lambda:self.core,_nome_seguro=lambda v:v,_aguardar_ssh=lambda ip:True,_laboratorios={},_salvar_estado=lambda:self.saved.append(True),_reservados=set(),_criacao_core=threading.Lock(),criacoes=[])
        self.engine.trava=lambda uid:self.engine._lock
        scope={'LABORATORIO_PADRAO':'primeiro-contato','Laboratorio':lambda **kw:NS(**kw),'obter_cenario':lambda lab:NS(LABORATORIO_ID=lab,TEMPO_LIMITE=900,TEMPO_EXTENSAO=300,MAX_EXTENSOES=1),'NodeType':NS(DOCKER='docker',SWITCH='switch'),'Interface':lambda **kw:NS(**kw),'Position':lambda **kw:NS(**kw),'IMAGEM':'pinglevel/ssh:0.1','IMAGEM_GATEWAY':'pinglevel/gateway:0.1','time':time,'construir_gateway':construir,'preparar_gateway':preparar,'topologia_setores':topologia_setores,**constantes()}
        exec(compile(ast.Module(body=metodos,type_ignores=[]),str(filename),'exec'),scope);self.create=scope['criar']
        self.engine._criar=lambda *a:scope['_criar'](self.engine,*a)
    def test_lab3_constroi_cinco_nos_e_prepara_gateway(self):
        lab=self.create(self.engine,1,'qa','saindo-da-rede-local')
        self.assertEqual(set(self.core.session.nodes),{1,2,3,4,5})
        self.assertEqual(self.core.session.nodes[2].name,'pl-s77-qa-computador-2')
        self.assertFalse(any(c[1]==6 for c in self.core.commands))
        self.assertEqual(self.core.session.nodes[1].image,'pinglevel/gateway:0.1')
        self.assertEqual(self.core.session.nodes[5].image,'pinglevel/gateway:0.1')
        self.assertEqual(lab.enderecos,{1:'172.30.9.1',2:'172.30.9.2',4:'172.30.9.4',5:'172.30.9.5'})
        self.assertIn((77,5,'sysctl -w net.ipv4.ip_forward=1'),self.core.commands)
        self.assertEqual(self.saved,[True]);self.assertIs(self.engine._laboratorios[1],lab)
    def test_lab4_tem_tres_pcs_com_os_problemas_dos_chamados(self):
        lab=self.create(self.engine,1,'qa','configure-pelo-terminal')
        self.assertEqual(set(self.core.session.nodes),{1,2,3,4,5,6})
        self.assertEqual(lab.enderecos,{1:'172.30.9.1',2:'172.30.9.2',4:'172.30.9.4',5:'172.30.9.5',6:'172.30.9.6'})
        recepcao=next(l for l in self.core.session.links if l['node1'].id==6)
        self.assertEqual((recepcao['iface1'].ip4,recepcao['iface1'].ip4_mask,recepcao['iface2'].name),('192.168.10.11',16,'eth3'))
        self.assertIn((77,1,'ip -4 addr flush dev eth0'),self.core.commands)
        self.assertIn((77,2,'ip -4 route replace default via 192.168.10.11 dev eth0'),self.core.commands)
        self.assertIn((77,6,'ip -4 route replace default via 192.168.10.1 dev eth0'),self.core.commands)
        self.assertIn((77,6,'sysctl -w net.ipv4.ip_forward=0'),self.core.commands)
        self.assertIn((77,5,'sysctl -w net.ipv4.ip_forward=1'),self.core.commands)
        self.assertEqual(lab.laboratorio_id,'configure-pelo-terminal')
    def test_lab5_monta_dois_setores_e_deixa_o_estado_do_roteiro(self):
        lab=self.create(self.engine,1,'qa','dividindo-uma-rede')
        self.assertEqual(set(self.core.session.nodes),{1,2,3,4,5,6,7})
        self.assertEqual(lab.enderecos,{5:'172.30.9.5',1:'172.30.9.1',2:'172.30.9.2',6:'172.30.9.6',7:'172.30.9.7'})
        self.assertEqual(self.core.session.nodes[1].name,'pl-s77-qa-pc-v1')
        rot=[l for l in self.core.session.links if l['node1'].id==5]
        self.assertEqual([(l['iface1'].name,l['iface1'].ip4,l['iface1'].ip4_mask,l['node2'].id) for l in rot],
                         [('eth0','192.168.50.1',26,3),('eth1','192.168.50.65',26,4)])
        for cmd in [(77,5,'sysctl -w net.ipv4.ip_forward=1'),(77,5,'ip -4 addr flush dev eth1'),(77,6,'ip -4 addr flush dev eth0'),
                    (77,1,'ip -4 route replace default via 192.168.50.1 dev eth0'),(77,2,'sysctl -w net.ipv4.ip_forward=0'),
                    (77,5,'iptables -A FORWARD -s 192.168.50.0/24 -d 192.168.50.0/24 -j ACCEPT')]:
            self.assertIn(cmd,self.core.commands)
        self.assertFalse(any(n==2 and 'flush dev' in c for s,n,c in self.core.commands))
    def test_lab6_tres_setores_com_tudo_zerado(self):
        lab=self.create(self.engine,1,'qa','planejando-uma-empresa')
        self.assertEqual(set(self.core.session.nodes),{1,2,3,4,5,6,7})
        self.assertEqual(set(lab.enderecos),{1,2,5,6})
        rot=[(l['iface1'].name,l['iface1'].ip4_mask) for l in self.core.session.links if l['node1'].id==5]
        self.assertEqual(rot,[('eth0',25),('eth1',26),('eth2',27)])
        for n,i in [(5,'eth0'),(5,'eth1'),(5,'eth2'),(1,'eth0'),(2,'eth0'),(6,'eth0')]:
            self.assertIn((77,n,f'ip -4 addr flush dev {i}'),self.core.commands)
    def test_lab3_nao_zera_o_computador(self):
        self.create(self.engine,1,'qa','saindo-da-rede-local')
        self.assertFalse(any('addr flush' in c for s,n,c in self.core.commands))
    def test_labs_legados_preservam_topologia_original(self):
        self.setUp();lab=self.create(self.engine,1,'qa','primeiro-contato')
        self.assertEqual(set(self.core.session.nodes),{1,2,3});self.assertEqual(len(self.core.session.links),2)
        self.assertEqual(set(lab.enderecos),{1,2});self.assertFalse(any('ip_forward' in c for s,n,c in self.core.commands))

    def test_lab2_tem_tres_pcs_num_switch_sem_roteador(self):
        # Lab 2 versão 2 (30/10/2026): o PC 2 sem endereço e o PC 3 com o prefixo errado, o chamado.
        lab=self.create(self.engine,1,'qa','primeira-lan')
        self.assertEqual(set(self.core.session.nodes),{1,2,3,4});self.assertEqual(len(self.core.session.links),3)
        self.assertEqual(set(lab.enderecos),{1,2,3})

    def test_preparo_falha_remove_sessao_e_nao_libera_treino(self):
        self.core.fail_prepare=True
        with self.assertRaises(RuntimeError):self.create(self.engine,1,'qa','saindo-da-rede-local')
        self.assertEqual(self.core.deleted,[77]);self.assertEqual(self.engine._laboratorios,{})
        self.assertTrue(self.core.closed)
    def test_remocao_falha_preserva_registro_bloqueado_para_limpeza(self):
        self.core.fail_prepare=True;self.core.fail_delete=True
        with self.assertRaises(RuntimeError):self.create(self.engine,1,'qa','saindo-da-rede-local')
        self.assertIn(1,self.engine._laboratorios)
        self.assertFalse(self.engine._laboratorios[1].preparacao_confirmada)
        self.assertEqual(self.engine._laboratorios[1].session_id,77)
        self.assertTrue(self.core.closed)

if __name__=='__main__':unittest.main()
