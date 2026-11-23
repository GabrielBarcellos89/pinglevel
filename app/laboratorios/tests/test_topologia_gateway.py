"""Construtor CORE exercitado por protocolo fake: nunca cria sessão real."""
import unittest
from types import SimpleNamespace
try:
    from laboratorios import topologia_gateway as gateway
except ImportError:
    gateway = None

class Session:
    def __init__(self):self.nodes={};self.links=[]
    def add_node(self,id,**kwargs):
        node=SimpleNamespace(id=id,**kwargs);self.nodes[id]=node;return node
    def add_link(self,**kwargs):self.links.append(kwargs)

def record(**kwargs):return SimpleNamespace(**kwargs)

class TopologiaGateway(unittest.TestCase):
    def test_constroi_tres_pcs_roteador_e_duas_lans_sem_tocar_host(self):
        self.assertIsNotNone(gateway,'Falta o construtor do cenário gateway')
        session=Session();names=gateway.construir(session,session_id=77,nome='qa',imagem='pinglevel/ssh:0.1',Interface=record,NodeType=SimpleNamespace(DOCKER='docker',SWITCH='switch'),Position=record)
        self.assertEqual(set(session.nodes),{1,2,3,4,5});self.assertEqual(set(names),{1,2,4,5});self.assertEqual(len(session.links),4)
        self.assertEqual(session.nodes[5].name,'pl-s77-qa-roteador')
        data=[(l['node1'].id,l['node2'].id,l['iface1'].name,l['iface1'].ip4) for l in session.links]
        self.assertIn((5,3,'eth0','192.168.10.1'),data);self.assertIn((5,4,'eth1','192.168.20.1'),data)
        self.assertEqual(session.links[-1]['iface2'].ip4,'192.168.20.10')
        self.assertEqual(session.links[-1]['iface2'].name,'eth0')
        self.assertEqual(len({(l['node2'].id,l['iface2'].id) for l in session.links}),4)

    def test_preparacao_altera_somente_nos_e_preserva_rede_de_controle(self):
        self.assertTrue(hasattr(gateway,'preparar'),'Falta preparação segura dos nós')
        class Core:
            def __init__(self):self.calls=[]
            def node_command(self,session_id,node,cmd,**opts):self.calls.append((session_id,node,cmd));return 0,''
        core=Core();gateway.preparar(core,77)
        self.assertTrue(core.calls)
        self.assertTrue(all(s==77 and n in [1,2,4,5] for s,n,c in core.calls))
        self.assertIn((77,5,'sysctl -w net.ipv4.ip_forward=1'),core.calls)
        self.assertIn((77,1,'ip -4 route flush default'),core.calls)
        self.assertIn((77,4,'ip -4 route replace default via 192.168.20.1 dev eth0'),core.calls)
        self.assertIn((77,5,'iptables -P FORWARD DROP'),core.calls)
        self.assertFalse(any('172.30' in c or 'addr flush' in c for s,n,c in core.calls))
        self.assertTrue(all(n==5 for s,n,c in core.calls if 'ip_forward=1' in c))

    def test_preparacao_falha_fecha_caminho_sem_ignorar_comando(self):
        self.assertTrue(hasattr(gateway,'preparar'))
        class Core:
            calls=[]
            def node_command(self,*args,**kw):self.calls.append(args);return 1,'ferramenta indisponível'
        core=Core()
        with self.assertRaises(RuntimeError):gateway.preparar(core,77)
        self.assertEqual(len(core.calls),1)

if __name__=='__main__':unittest.main()
