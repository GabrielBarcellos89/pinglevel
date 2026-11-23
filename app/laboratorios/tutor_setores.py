"""Perfis do Link nos Labs 2 e 5 a 10 (setores, rotas, VLANs, DHCP e DNS): trechos, restrições e filtros.

O Link não entrega o plano antes de o servidor conferi-lo, não diz a causa do chamado do Lab 5 antes da resposta e
não escreve comandos com endereços antes do nível 4 (a menos que o aluno os tenha proposto).
"""
import re

from laboratorios.cenarios import (conectando_redes as lab7, desafio_empresa as lab10, dividindo_rede as lab5,
    enderecos_nomes as lab8, investigando_lan as lab9, planejando_empresa as lab6, primeira_lan as lab2,
    suporte_remoto as suporte)
from laboratorios.tutor_lab4 import FORA_DO_ESCOPO
from laboratorios.tutor_referencias import Perfil

# Trechos (ids da tabela chunks do índice RAG): Redes para Iniciantes p.75–76 (prefixo e 2^bits), p.78 (privados),
# p.154–155 (tabela de roteamento e gateway), glossário p.241 (sub-rede) e p.245 (VLSM);
# Linux: Utilitários de Redes p.13 (ip addr / ip route).
ANCORAS_5 = {'plano': (395, 396, 855), 'roteador': (16, 614), 'financeiro': (16, 617), 'chamado': (395, 396),
             'comprovar': (614, 617)}
ANCORAS_6 = {'plano': (396, 867, 855), 'roteador': (16, 614), 'pcs': (16, 617), 'comprovar': (614, 617)}
CONCEITOS_5 = {'plano': 'sub-rede bloco prefixo /26 endereço de rede broadcast hosts', 'roteador': 'roteador interface endereço ip addr add tabela de roteamento',
               'financeiro': 'gateway rota padrão ip route ping sub-rede', 'chamado': 'prefixo máscara rede local endereço fora da rede',
               'comprovar': 'roteador encaminha pacotes entre redes tabela de roteamento'}
CONCEITOS_6 = {'plano': 'VLSM máscara de tamanho variável prefixo bloco hosts', 'roteador': 'roteador interfaces endereço ip addr add',
               'pcs': 'gateway rota padrão ip route ping', 'comprovar': 'roteador encaminha pacotes entre redes tabela de roteamento'}
RESTRICOES_5 = {
    'plano': 'O aluno calcula a rede, o gateway (primeiro host) e o broadcast do 2º bloco /26 de 192.168.50.0/24. Não diga '
             'esses endereços; explique tamanho do bloco (2^bits de host), onde um bloco começa e termina e use o bloco do '
             'Vendas (.0 a .63) como exemplo.',
    'roteador': 'O aluno põe na eth1 do roteador o gateway do Financeiro, com o prefixo do plano. Até o nível 3, não escreva '
                'o comando com o endereço; explique a forma ip addr add <endereço>/<prefixo> dev <interface>.',
    'financeiro': 'O aluno configura PC F1 e PC F2: endereço livre do bloco do Financeiro e rota padrão pelo gateway do plano. '
                  'Até o nível 3, não escreva comandos com endereços.',
    'chamado': 'PC V2 "não fala com ninguém". Enquanto causa_identificada for falso, não diga que o endereço está fora do bloco '
               'nem que pertence ao Financeiro; ajude a comparar o endereço com o bloco do Vendas. Depois, não escreva o '
               'comando com endereço até o nível 3.',
    'comprovar': 'Tudo configurado; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
RESTRICOES_6 = {
    'plano': 'O aluno monta o plano VLSM de 192.168.80.0/24 (Atendimento 101, Vendas 51, Financeiro 21 endereços). Não diga '
             'prefixos nem redes do plano; explique as regras: prefixo pela demanda, do maior bloco ao menor, alinhamento e '
             'sem sobreposição.',
    'roteador': 'Cada interface do roteador recebe o primeiro host do bloco do seu setor (eth0 Atendimento, eth1 Vendas, eth2 '
                'Financeiro). Até o nível 3, não escreva comandos com endereços.',
    'pcs': 'Cada PC recebe um endereço livre do bloco do seu setor e a rota padrão pelo gateway do setor. Até o nível 3, não '
           'escreva comandos com endereços.',
    'comprovar': 'Tudo configurado; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS = ('O terminal deste laboratório tem uma aba por equipamento e aceita apenas: ip addr show, ip addr add e ip addr '
          'del <endereço>/<prefixo> dev <interface>, ip route show, ip route add default via <gateway> e ip route del '
          'default (só nos PCs) e ping <endereço> sem opções. Não ensine outros comandos, opções ou arquivos de '
          'configuração. Você pode explicar as mensagens que aparecerem na saída real do terminal.\n')
CAUSA_CHAMADO = re.compile(r'fora\s+do\s+bloco|bloco\s+(?:do|errado)|pertence\s+ao\s+(?:bloco|financeiro)|'
                           r'\.70\s+(?:n[ãa]o\s+)?(?:est[áa]|fica|pertence)', re.I)
IP = r'\d{1,3}(?:\.\d{1,3}){3}'


def _contexto(c):
    def contexto(missao):
        nos = c.NOS
        plano = missao.get('plano') or {}
        return {'plano_conferido': bool(plano.get('correto')),
            'causa_do_chamado_identificada': bool((missao.get('chamado') or {}).get('correta')),
            'estado_dos_equipamentos': {nos[n]['nome']: e for n, e in (missao.get('estados') or {}).items() if n in nos},
            'testes_confirmados': {nos[n]['nome']: t for n, t in (missao.get('testes') or {}).items() if n in nos},
            # Linha do tempo dos últimos comandos: os aceitos (com a saída real) e os que o terminal recusou (formato ou
            # equipamento errado), com o motivo mostrado ao aluno. Uma recusa vem depois do comando aceito de mesma revisão.
            'ultimos_comandos': [item for _, item in sorted(
                [((t.get('revisao') or 0, 0), {'equipamento': nos.get(t.get('remoto') or t.get('pc'), {}).get('nome'), 'digitado': t.get('digitado'),
                  'aceito': True, 'saida': (t.get('saida') or '')[-1200:], 'codigo': t.get('codigo')})
                 for t in (missao.get('terminal') or [])[-3:]]
                + [((r.get('revisao') or 0, 1), {'digitado': r.get('digitado'), 'aceito': False, 'motivo_da_recusa': r.get('motivo')})
                   for r in (missao.get('recusas') or [])[-3:]], key=lambda par: par[0])][-4:]}
    return contexto


def _segredos_do_plano(c):
    """Endereços que só o plano revela; prefixos ficam de fora (o Link precisa poder explicar um /26)."""
    valores = {campo['esperado'] for campo in c.PLANO if campo['tipo'] == 'ip'}
    valores.update(s['gateway'] for s in c.SETORES.values())
    # O início da rede está no enunciado; no Lab 5, o bloco do Vendas é o exemplo dado.
    return valores - {c.REDE.split('/')[0], '192.168.50.1'}


def _fora(*liberados):
    """Comandos de outros laboratórios, exceto os que este laboratório ensina (o filtro do Lab 4 barra ARP e nslookup)."""
    termos = [t for t in ('nslookup', 'dig', 'traceroute', 'tracert', 'ifconfig', 'netstat', 'arp', 'hostname', 'netplan',
                          'nmcli', 'dhclient', r'(?<!ip\s)route\s+add', r'ip\s+(?:link|neigh|tunnel|-6)') if t not in liberados]
    if r'ip\s+(?:link|neigh|tunnel|-6)' in liberados:
        termos.append(r'ip\s+(?:tunnel|-6)')
    arquivos = r'/etc/(?!resolv\.conf)' if '/etc/resolv.conf' in liberados else '/etc/'
    return re.compile(r'\b(?:' + '|'.join(termos) + r')\b|' + arquivos, re.I)


VIZINHOS = ('arp', r'ip\s+(?:link|neigh|tunnel|-6)')  # Labs 9 e 10: tabela ARP, ip neigh e ip link fazem parte do lab
SERVICOS = ('nslookup', 'dhclient', '/etc/resolv.conf')  # Labs 8 e 10


def _bloquear(c, segredos=None, causa=CAUSA_CHAMADO, fora=FORA_DO_ESCOPO):
    segredos = _segredos_do_plano(c) if segredos is None else segredos

    def bloquear(texto, etapa, nivel, missao, pergunta, rascunho):
        if re.search(r'\b(?:sudo|curl|wget|ssh)\b', texto, re.I):
            return 'filtro'
        if fora.search(texto):
            return 'fora_do_tema'
        referencia = f"{pergunta} {rascunho.get('comando', '')}"
        if not (missao.get('plano') or {}).get('correto'):
            for valor in segredos:
                if re.search(r'(?<![0-9.])' + re.escape(valor) + r'(?![0-9]|\.\d)', texto) and valor not in referencia:
                    return 'filtro'
        chamado = missao.get('chamado') or {}
        if etapa == 'chamado' and not chamado.get('correta') and causa.search(texto):
            return 'filtro'
        if nivel < 4:
            for ip in re.findall(r'\bip\s+addr(?:ess)?\s+add\s+(' + IP + ')', texto, re.I):
                if ip not in referencia:
                    return 'filtro'
            for ip in re.findall(r'\bvia\s+(' + IP + ')', texto, re.I):
                if ip not in referencia:
                    return 'filtro'
        return None
    return bloquear


def _alternativa(c):
    def alternativa(etapa, nivel, missao, rascunho):
        if etapa == 'plano':
            if c is lab5:
                return ('Um /26 tem 64 endereços. O bloco do Vendas vai de .0 a .63: o próximo começa logo depois. A rede é o '
                        'primeiro endereço do bloco, o gateway é o primeiro host e o broadcast é o último endereço.')
            return ('Escolha o prefixo pela demanda de cada setor (contando o gateway) e distribua do maior bloco para o menor, '
                    'cada um começando num múltiplo do seu tamanho.')
        if etapa == 'chamado' and not (missao.get('chamado') or {}).get('correta'):
            return 'Leia o endereço do PC V2 com ip addr show e compare com o intervalo do bloco do Vendas no plano.'
        if etapa in ('roteador', 'financeiro', 'pcs', 'chamado'):
            if nivel >= 4:
                return ('Use ip addr add <endereço>/<prefixo> dev <interface> com os valores do plano; nos PCs, depois, '
                        'ip route add default via <gateway do setor>. Confira com ip addr show e teste com ping.')
            return 'Confira no plano o bloco e o gateway do setor. A forma é ip addr add <endereço>/<prefixo> dev <interface>.'
        return 'Tudo pronto: clique em Concluir missão. O servidor relê os equipamentos e repete os testes.'
    return alternativa


ANCORAS_7 = {'chamado': (614, 616), 'plano': (615, 616), 'ida': (17, 616), 'volta': (17, 615), 'comprovar': (614, 616)}
CONCEITOS_7 = {'chamado': 'tabela de roteamento rota destino descartado', 'plano': 'próximo salto rota estática roteador',
               'ida': 'rota estática ip route add via próximo salto', 'volta': 'rota de volta resposta próximo salto tabela de roteamento',
               'comprovar': 'roteamento tabela de roteamento próximo salto'}
RESTRICOES_7 = {
    'chamado': 'O PC A não alcança o PC B. Enquanto causa_do_chamado_identificada for falso, não diga que falta rota no R1; '
               'ajude o aluno a ler a tabela do R1 e a testar o gateway e o enlace.',
    'plano': 'O aluno planeja a rede de destino e o próximo salto da rota de cada roteador. Não diga os valores; explique '
             'que o próximo salto é o vizinho numa rede diretamente conectada.',
    'ida': 'O aluno aplica só a rota do R1 e testa: o ping deve falhar, porque a resposta não tem volta. Até o nível 3, '
           'não escreva o comando com valores; explique a forma ip route add <rede>/<prefixo> via <próximo salto>.',
    'volta': 'Falta a rota de volta no R2. Até o nível 3, não escreva o comando com valores.',
    'comprovar': 'Tudo configurado; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
CAUSA_LAB7 = re.compile(r'(?:\br1\b|roteador)[^.]{0,40}?(?:n[ãa]o\s+(?:tem|conhece|possui|sabe)|sem)\s+(?:uma\s+|nenhuma\s+)?'
                        r'(?:rota|caminho)|falta(?:m)?\s+(?:uma\s+)?rota|n[ãa]o\s+h[áa]\s+rota\s+para', re.I)


def _alternativa_7(etapa, nivel, missao, rascunho):
    if etapa == 'chamado':
        return ('Leia a tabela do R1 com ip route: que redes aparecem? Teste também, do PC A, o gateway (192.168.10.1) e o '
                'R2 (10.0.0.2) para ver até onde o caminho funciona.')
    if etapa == 'plano':
        return 'Para cada roteador: a rede que ele ainda não conhece e o vizinho no enlace 10.0.0.0/30 que leva até ela.'
    if etapa in ('ida', 'volta'):
        if nivel >= 4:
            return ('No R1: ip route add 192.168.20.0/24 via 10.0.0.2. No R2: ip route add 192.168.10.0/24 via 10.0.0.1. '
                    'Depois teste do PC A ao PC B.')
        return 'Use ip route add <rede>/<prefixo> via <próximo salto>, com os valores do seu plano, e teste com ping.'
    return 'Tudo pronto: clique em Concluir missão. O servidor relê os equipamentos e repete os pings.'


PERFIL_LAB5 = Perfil(conceitos=CONCEITOS_5, restricoes=RESTRICOES_5, ancoras=ANCORAS_5, regras=REGRAS,
    alternativa=_alternativa(lab5), contexto=_contexto(lab5), bloquear=_bloquear(lab5))
PERFIL_LAB6 = Perfil(conceitos=CONCEITOS_6, restricoes=RESTRICOES_6, ancoras=ANCORAS_6, regras=REGRAS,
    alternativa=_alternativa(lab6), contexto=_contexto(lab6), bloquear=_bloquear(lab6))
PERFIL_LAB7 = Perfil(conceitos=CONCEITOS_7, restricoes=RESTRICOES_7, ancoras=ANCORAS_7, regras=REGRAS.replace(
    'ip route add default via <gateway> e ip route del default (só nos PCs)',
    'ip route add <rede>/<prefixo> via <próximo salto> e ip route del <rede>/<prefixo> (só nos roteadores)'),
    alternativa=_alternativa_7, contexto=_contexto(lab7), bloquear=_bloquear(lab7, segredos=set(), causa=CAUSA_LAB7))


# Lab 9: Linux: Utilitários de Redes p.12 (ip neigh) e p.38 (bridge); Redes para Iniciantes p.72 (MAC), p.131 (tabela
# MAC do switch), p.96–99 (VLANs, porta de acesso e PVID).
ANCORAS_9 = {'investigar': (15, 548, 386), 'chamado': (451, 452, 458), 'separar': (456, 458, 75), 'comprovar': (452, 454)}
CONCEITOS_9 = {'investigar': 'tabela ARP endereço MAC switch tabela MAC porta quadro',
               'chamado': 'VLAN domínio de broadcast porta isolamento switch',
               'separar': 'VLAN porta de acesso PVID untagged bridge vlan',
               'comprovar': 'VLAN isolamento roteador domínio de broadcast'}
RESTRICOES_9 = {
    'investigar': 'O aluno descobre o MAC do PC F2 (tabela ARP do PC F1, depois de um ping) e a porta do switch em que ele '
                  'está (tabela MAC do switch). Não diga o MAC nem a porta; explique como ler ip neigh show e bridge fdb show.',
    'chamado': 'O PC V2 não fala com o PC V1. Enquanto causa_do_chamado_identificada for falso, não diga que a porta está na '
               'VLAN errada nem em qual VLAN está; ajude a ler bridge vlan show e a comparar as portas. Depois, não escreva o '
               'comando com a porta e o número da VLAN até o nível 3. A porta de cada PC está em portas_do_switch: nunca '
               'indique outra, e só proponha mudar as de portas_que_esta_etapa_permite_alterar.',
    'separar': 'As portas do PC F1 e do PC F2 vão para a VLAN 20 como portas de acesso. Até o nível 3, não escreva o comando '
               'completo; explique a forma bridge vlan add dev <porta> vid <vlan> pvid untagged e a remoção da VLAN 1. A porta '
               'de cada PC está em portas_do_switch: nunca indique outra.',
    'comprovar': 'Tudo configurado; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS_9 = ('O terminal deste laboratório tem uma aba por equipamento. Nos PCs aceita apenas: ip addr show, ip link show, '
            'ip neigh show, ip route show e ping <endereço> sem opções. No switch, apenas: bridge link, bridge fdb show, '
            'bridge vlan show, bridge vlan add dev <porta> vid <número> pvid untagged e bridge vlan del dev <porta> vid '
            '<número>. Não ensine outros comandos, opções ou arquivos de configuração. Você pode explicar as mensagens '
            'que aparecerem na saída real do terminal.\n')
CAUSA_LAB9 = re.compile(r'vlan\s+(?:errada|diferente|20)|outra\s+vlan|vlans?\s+diferentes|n[ãa]o\s+est[ãa]o\s+na\s+mesma\s+vlan', re.I)
SEGREDOS_9 = {lab9.MACS['f2']}


def _contexto_9(missao):
    """Depois da investigação conferida, o Link recebe a porta de cada PC e as portas que a etapa deixa mudar (validação
    de 22/11/2026: sem isso, indicou a eth0 para o PC V2, que está na eth1)."""
    dados = _contexto(lab9)(missao)
    if dados['plano_conferido']:
        dados['portas_do_switch'] = {porta: lab9.NOS[pc]['nome'] for pc, porta in lab9.PORTAS.items()}
        dados['portas_que_esta_etapa_permite_alterar'] = list(
            lab9.ALTERAVEIS.get(missao.get('proxima_etapa'), {}).get('switch', ()))
    return dados


def _bloquear_9(texto, etapa, nivel, missao, pergunta, rascunho):
    referencia = f"{pergunta} {rascunho.get('comando', '')}".lower()
    # Nas correções, um comando com porta só pode citar as portas que a etapa deixa mudar.
    permitidas = lab9.ALTERAVEIS.get(etapa, {}).get('switch', ())
    if permitidas and any(p not in permitidas for p in re.findall(r'\bdev\s+(eth\d+)', texto, re.I)):
        return 'filtro'
    if not (missao.get('plano') or {}).get('correto'):
        if any(m in texto.lower() and m not in referencia for m in SEGREDOS_9):
            return 'filtro'
        if re.search(r'\beth3\b', texto) and 'eth3' not in referencia:
            return 'filtro'
    if nivel < 4 and re.search(r'bridge\s+vlan\s+add\s+dev\s+eth\d\s+vid\s+\d+', texto, re.I) \
            and not re.search(r'bridge\s+vlan\s+add\s+dev\s+eth\d', referencia):
        return 'filtro'
    return _bloquear(lab9, segredos=set(), causa=CAUSA_LAB9, fora=_fora(*VIZINHOS))(texto, etapa, nivel, missao, pergunta, rascunho)


def _alternativa_9(etapa, nivel, missao, rascunho):
    if etapa == 'investigar':
        return ('No PC F1, faça ping ao PC F2 (192.168.30.22) e rode ip neigh show: o MAC aparece depois de lladdr. No '
                'switch, bridge fdb show mostra cada MAC aprendido e a porta (dev) em que ele foi visto.')
    if etapa == 'chamado' and not (missao.get('chamado') or {}).get('correta'):
        return ('No switch, rode bridge vlan show e compare a porta do PC V1 (eth0) com a do PC V2: em qual VLAN está cada uma? '
                'O endereço IP dos dois também está em ip addr show.')
    if etapa in ('chamado', 'separar'):
        if nivel >= 4:
            return ('Porta de acesso: bridge vlan add dev <porta> vid <vlan> pvid untagged, e depois bridge vlan del dev '
                    '<porta> vid <vlan antiga>. Confira com bridge vlan show e teste com ping.')
        return 'Coloque a porta na VLAN certa como porta de acesso (pvid untagged) e tire a VLAN antiga. Depois, teste com ping.'
    return 'Tudo pronto: clique em Concluir missão. O servidor relê o switch e repete os testes.'


PERFIL_LAB9 = Perfil(conceitos=CONCEITOS_9, restricoes=RESTRICOES_9, ancoras=ANCORAS_9, regras=REGRAS_9,
    alternativa=_alternativa_9, contexto=_contexto_9, bloquear=_bloquear_9)


# Labs 8 e 10: chamados de DHCP e DNS (e, no 10, rota e VLAN). Trechos: Redes para Iniciantes p.63 (DHCP e DNS),
# p.78 (0.0.0.0, sem endereço), p.91 (DNS em UDP, porta 53), p.154–155 (roteamento); Linux: Utilitários de Redes p.24
# (dhclient), p.17–18 (nslookup) e p.83 (/etc/resolv.conf); VLANs como no Lab 9.
ANCORAS_8 = {'novo': (363, 402, 38), 'recepcao': (363, 437, 176), 'financeiro': (24, 27, 437), 'comprovar': (363, 437)}
CONCEITOS_8 = {'novo': 'DHCP concessão endereço automático gateway servidor DNS 0.0.0.0',
               'recepcao': 'DNS servidor DNS resolv.conf nameserver nome endereço IP',
               'financeiro': 'DNS consulta nslookup nome não existe NXDOMAIN',
               'comprovar': 'DHCP DNS nome endereço ping'}
RESTRICOES_8 = {
    'novo': 'PC Novo "acabou de chegar e não acessa nada". Enquanto causa_do_chamado_identificada for falso, não diga que '
            'falta o endereço nem que é preciso pedir ao DHCP; ajude a ler ip addr show (UP, linhas inet). Depois, até o '
            'nível 3, não escreva o comando completo do cliente DHCP; explique o que é a concessão.',
    'recepcao': 'PC Recepção abre a intranet pelo IP, mas não pelo nome. Enquanto causa_do_chamado_identificada for falso, '
                'não diga que o servidor DNS está errado nem qual é o certo; ajude a comparar ping pelo IP, nslookup e o '
                'conteúdo do /etc/resolv.conf. Depois, até o nível 3, não escreva o comando completo.',
    'financeiro': 'O usuário do PC Financeiro digitou impresora.empresa.local. Enquanto causa_do_chamado_identificada for '
                  'falso, não diga que o nome está escrito errado nem qual é o nome certo; ajude a ler a resposta do '
                  'nslookup (o que é NXDOMAIN).',
    'comprovar': 'Os três chamados estão resolvidos; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS_8 = ('O terminal deste laboratório tem uma aba por equipamento e aceita apenas: ip addr show, ip addr add e del '
            '<endereço>/<prefixo> dev eth0, ip route show, ip route add default via <gateway>, ip route del default, ping '
            '<endereço ou nome>, dhclient eth0 (o cliente DHCP; a saída aparece com linhas "udhcpc:" porque nestes '
            'computadores o pedido é feito pelo udhcpc, outro cliente DHCP), cat /etc/resolv.conf e nslookup <nome>. Os nomes '
            'terminam em .empresa.local. Não ensine outros comandos, opções ou arquivos de configuração. Você pode '
            'explicar as mensagens que aparecerem na saída real do terminal.\n')
CAUSAS_8 = {
    'novo': re.compile(r'sem\s+(?:endere[çc]o|ip)|n[ãa]o\s+(?:tem|recebeu|possui)\s+(?:um\s+|nenhum\s+)?(?:endere[çc]o|ip)|'
                       r'pe[çc]a\s+(?:um\s+)?endere[çc]o|pedir\s+(?:um\s+)?endere[çc]o', re.I),
    'recepcao': re.compile(r'(?:servidor\s+)?dns\s+(?:est[áa]\s+)?errado|nameserver\s+(?:est[áa]\s+)?errado|192\.168\.40\.9\s+'
                           r'(?:n[ãa]o|est[áa]\s+errado)|(?:servidor\s+dns|nameserver)\s+(?:certo|correto)\s+(?:é|seria)', re.I),
    'financeiro': re.compile(r'escrit[oa]\s+errad[oa]|digitad[oa]\s+errad[oa]|erro\s+de\s+digita[çc][ãa]o|falta\s+(?:um\s+)?'
                             r'["“]?s|impressora\.empresa\.local|grafia', re.I),
}


def _bloquear_chamados(c, causas, completos, fora):
    """Antes da causa identificada, nada que a revele; antes do nível 4, nenhum comando completo da correção."""
    def bloquear(texto, etapa, nivel, missao, pergunta, rascunho):
        referencia = f"{pergunta} {rascunho.get('comando', '')}".lower()
        chamado = missao.get('chamado') or {}
        if etapa in causas and not chamado.get('correta') and causas[etapa].search(texto):
            trecho = causas[etapa].search(texto).group(0).lower()
            if trecho not in referencia:
                return 'filtro'
        if nivel < 4:
            for padrao in completos:
                achado = re.search(padrao, texto, re.I)
                if achado and achado.group(0).lower() not in referencia:
                    return 'filtro'
        return _bloquear(c, segredos=set(), causa=re.compile(r'(?!x)x'), fora=fora)(texto, etapa, nivel, missao, pergunta, rascunho)
    return bloquear


def _alternativa_8(etapa, nivel, missao, rascunho):
    identificada = (missao.get('chamado') or {}).get('correta')
    if etapa == 'novo':
        if not identificada:
            return 'Leia ip addr show no PC Novo: a eth0 está UP? Tem alguma linha inet? Depois escolha a causa no chamado.'
        return ('O cliente DHCP pede a concessão ao servidor da rede. Depois, confira com ip addr show, ip route e cat '
                '/etc/resolv.conf, e teste com ping pelo nome da intranet.')
    if etapa == 'recepcao':
        if not identificada:
            return ('Compare: ping 192.168.40.20 (pelo IP) e nslookup intranet.empresa.local (pelo nome). Depois leia qual '
                    'servidor o PC consulta com cat /etc/resolv.conf.')
        return 'Passe o PC para o DHCP: a concessão traz o endereço, o gateway e o servidor DNS da empresa. Depois, teste pelo nome.'
    if etapa == 'financeiro':
        if not identificada:
            return 'Faça a mesma consulta do usuário com nslookup e leia a resposta: o servidor respondeu? O que ele disse?'
        return 'Não há nada a corrigir no PC: comprove com ping pelo nome certo da impressora.'
    return 'Tudo pronto: clique em Concluir missão. O servidor relê os PCs e repete os testes pelos nomes.'


PERFIL_LAB8 = Perfil(conceitos=CONCEITOS_8, restricoes=RESTRICOES_8, ancoras=ANCORAS_8, regras=REGRAS_8,
    alternativa=_alternativa_8, contexto=_contexto(lab8),
    bloquear=_bloquear_chamados(lab8, CAUSAS_8, (r'udhcpc\s+-i\s+eth0', r'dhclient\s+(?:-v\s+)?eth0'), _fora(*SERVICOS)))

ANCORAS_10 = {'intranet': (614, 615, 617), 'vlan': (451, 452, 458), 'dhcp': (363, 402, 38), 'dns': (437, 176, 24),
              'comprovar': (614, 452, 363)}
CONCEITOS_10 = {'intranet': 'rota padrão gateway resposta caminho de volta tabela de roteamento',
                'vlan': 'VLAN porta de acesso switch domínio de broadcast',
                'dhcp': 'DHCP concessão endereço automático gateway servidor DNS',
                'dns': 'DNS servidor DNS resolv.conf nameserver nome endereço IP',
                'comprovar': 'roteamento VLAN DHCP DNS'}
RESTRICOES_10 = {
    'intranet': 'Ninguém abre a intranet. É o desafio final: enquanto causa_do_chamado_identificada for falso, não diga '
                'qual equipamento tem o problema, nem que é a rota padrão do servidor; sugira testar por partes (o nome, o '
                'gateway, o roteador, o servidor) e ler as tabelas. Depois, até o nível 3, não escreva o comando completo.',
    'vlan': 'O PC V2 não fala com ninguém. Enquanto causa_do_chamado_identificada for falso, não diga que a porta está na '
            'VLAN errada; ajude a comparar o PC V2 com o PC V1. Depois, até o nível 3, não escreva o comando completo.',
    'dhcp': 'O PC F1 acabou de chegar. Enquanto causa_do_chamado_identificada for falso, não diga que falta o endereço; '
            'ajude a ler ip addr show. Depois, até o nível 3, não escreva o comando completo.',
    'dns': 'O PC F2 abre a intranet pelo IP, não pelo nome. Enquanto causa_do_chamado_identificada for falso, não diga que o '
           'servidor DNS está errado; ajude a comparar IP e nome. Depois, até o nível 3, não escreva o comando completo.',
    'comprovar': 'Os quatro chamados estão resolvidos; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS_10 = ('O terminal deste laboratório tem uma aba por equipamento. Nos PCs e no servidor intranet aceita apenas: ip '
             'addr show/add/del, ip link show, ip neigh show, ip route show, ip route add default via <gateway>, ip route '
             'del default, ping <endereço ou nome>, dhclient eth0, cat /etc/resolv.conf e nslookup <nome>. No roteador, '
             'só ip addr show, ip route show e ping. No switch, só bridge link, bridge fdb show, bridge vlan show, bridge '
             'vlan add dev <porta> vid <número> pvid untagged e bridge vlan del dev <porta> vid <número>. Não ensine outros '
             'comandos, opções ou arquivos de configuração. Você pode explicar as mensagens da saída real do terminal.\n')
CAUSAS_10 = {
    'intranet': re.compile(r'rota\s+padr[ãa]o\s+(?:do|no)\s+servidor|servidor[^.]{0,30}rota\s+(?:padr[ãa]o\s+)?errada|'
                           r'192\.168\.60\.254|caminho\s+de\s+volta\s+do\s+servidor', re.I),
    'vlan': CAUSA_LAB9,
    'dhcp': CAUSAS_8['novo'],
    'dns': re.compile(r'(?:servidor\s+)?dns\s+(?:est[áa]\s+)?errado|nameserver\s+(?:est[áa]\s+)?errado|192\.168\.20\.9', re.I),
}


def _alternativa_10(etapa, nivel, missao, rascunho):
    identificada = (missao.get('chamado') or {}).get('correta')
    if not identificada and etapa in CHAMADOS_10_DICAS:
        return CHAMADOS_10_DICAS[etapa]
    if etapa == 'comprovar':
        return 'Tudo pronto: clique em Concluir missão. O servidor relê a rede inteira e repete os testes.'
    return 'Você já sabe a causa: corrija só o equipamento do chamado e comprove com ping pelo nome da intranet.'


CHAMADOS_10_DICAS = {
    'intranet': 'Teste por partes, de um PC: o nome vira endereço? O gateway responde? E o servidor? Leia também as rotas '
                'de quem precisa responder.',
    'vlan': 'Compare o PC V2 com o PC V1: endereço, gateway e a porta de cada um no switch.',
    'dhcp': 'Leia os endereços do PC F1: a interface está UP? Tem alguma linha inet?',
    'dns': 'Compare o ping pelo IP da intranet com a consulta do nome, e veja qual servidor DNS o PC usa.',
}

PERFIL_LAB10 = Perfil(conceitos=CONCEITOS_10, restricoes=RESTRICOES_10, ancoras=ANCORAS_10, regras=REGRAS_10,
    alternativa=_alternativa_10, contexto=_contexto(lab10),
    bloquear=_bloquear_chamados(lab10, CAUSAS_10, (r'udhcpc\s+-i\s+eth0', r'dhclient\s+(?:-v\s+)?eth0', r'ip\s+route\s+add\s+default\s+via\s+192\.168\.60\.1\b',
                                                    r'bridge\s+vlan\s+add\s+dev\s+eth1\s+vid\s+10'), _fora(*VIZINHOS, *SERVICOS)))


# Lab 2 (versão 2): uma LAN sem roteador. Trechos: Redes para Iniciantes p.75–76 (prefixo, máscara e 2^bits);
# Linux: Utilitários de Redes p.13 (ip addr).
ANCORAS_2 = {'plano': (395, 396, 16), 'pc2': (16, 395), 'chamado': (395, 396), 'comprovar': (16, 395)}
CONCEITOS_2 = {'plano': 'endereço de rede prefixo máscara /24 255.255.255.0 hosts', 'pc2': 'endereço IPv4 mesma rede ip addr add host',
               'chamado': 'prefixo máscara rede local mesma rede endereço fora da rede', 'comprovar': 'rede local switch ping mesma rede'}
RESTRICOES_2 = {
    'plano': 'O aluno descobre, a partir do endereço do PC 1 (192.168.10.10/24), o endereço da rede, o prefixo e a máscara. '
             'Não diga esses três valores; explique como o prefixo separa a parte da rede e a parte do host e como o prefixo '
             'vira máscara. Se o aluno perguntar o que fazer ou o que é esperado, explique a tarefa em até três frases '
             'simples, sem falar de bits: primeiro ver o endereço do PC 1 pelo terminal (a linha inet mostra o endereço e, '
             'depois da barra, o prefixo); depois preencher o endereço da rede (o primeiro endereço da faixa, que nenhum '
             'PC usa), o prefixo e a máscara (o mesmo prefixo escrito em quatro números). Se ele ainda não viu o endereço '
             'do PC 1, comece por aí.',
    'pc2': 'O aluno escolhe um endereço livre da mesma rede para o PC 2 e o configura com ip addr add <endereço>/<prefixo> dev '
           'eth0. Explique que não pode usar o endereço da rede, o broadcast nem o de outro PC. Até o nível 3, não escreva o '
           'comando com um endereço escolhido por você. Esta rede não tem roteador: não fale em gateway nem rota padrão.',
    'chamado': 'O PC 3 não fala com o PC 1. Enquanto causa_do_chamado_identificada for falso, não diga que o problema é o '
               'prefixo, a máscara ou o /28; ajude o aluno a comparar o endereço e o número depois da barra dos dois PCs. '
               'Depois, explique a correção (remover o endereço com o prefixo errado e adicionar o mesmo endereço com o '
               'prefixo da sala), sem escrever os comandos completos até o nível 3.',
    'comprovar': 'Tudo configurado; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS_2 = ('O terminal deste laboratório tem uma aba por computador e aceita apenas: ip addr show, ip addr add e ip addr '
            'del <endereço>/<prefixo> dev eth0 e ping <endereço> sem opções. Esta rede local não tem roteador nem gateway. '
            'Não ensine outros comandos, opções ou arquivos de configuração. Você pode explicar as mensagens que aparecerem '
            'na saída real do terminal, como "Network unreachable".\n')
CAUSA_LAB2 = re.compile(r'/\s?28|(?:prefixo|m[áa]scara)[^.]{0,30}?(?:errad|diferent|incorret|trocad)|255\.255\.255\.240', re.I)


def _alternativa_2(etapa, nivel, missao, rascunho):
    if etapa == 'plano':
        return ('Veja o endereço do PC 1 com ip addr show: o número depois da barra é o prefixo. Com /24, os três primeiros '
                'números são a rede e o último é o host; o endereço da rede termina em 0.')
    if etapa == 'pc2':
        return ('Escolha um endereço da mesma rede do PC 1 que ninguém use (nem o da rede nem o broadcast) e use ip addr add '
                '<endereço>/<prefixo> dev eth0. Depois teste com ping até o PC 1.')
    if etapa == 'chamado' and not (missao.get('chamado') or {}).get('correta'):
        return 'Veja o endereço do PC 3 com ip addr show e compare com o do PC 1: o que é igual e o que é diferente?'
    if etapa == 'chamado':
        return ('Remova o endereço atual com ip addr del <endereço>/<prefixo> dev eth0 e adicione de novo com o prefixo da '
                'sala. Depois teste com ping até o PC 1.')
    return 'Tudo pronto: clique em Concluir missão. O servidor relê os três PCs e repete os pings.'


PERFIL_LAB2 = Perfil(conceitos=CONCEITOS_2, restricoes=RESTRICOES_2, ancoras=ANCORAS_2, regras=REGRAS_2,
    alternativa=_alternativa_2, contexto=_contexto(lab2),
    bloquear=_bloquear(lab2, segredos={'192.168.10.0', '255.255.255.0'}, causa=CAUSA_LAB2, fora=_fora()))


# Demonstração "Suporte remoto" (teste de carga): SSH, gateway e impressão a partir da T.I.
CONCEITOS_SUPORTE = {'acesso': 'acesso remoto ssh terminal outro computador mesma rede',
                     'gateway': 'gateway rota padrão ip route tabela de roteamento outra rede',
                     'impressao': 'impressora de rede porta conexão roteador outra rede',
                     'comprovar': 'roteador encaminha pacotes entre redes rota padrão'}
ANCORAS_SUPORTE = {'acesso': (16,), 'gateway': (16, 614, 617), 'impressao': (614, 617), 'comprovar': (614, 617)}
RESTRICOES_SUPORTE = {
    'acesso': 'O aluno está no PC da T.I. (192.168.20.30) e precisa entrar no Financeiro B (192.168.20.21) com '
              'ssh suporte@<endereço>; a senha do usuário suporte é suporte123 e não aparece enquanto é digitada. '
              'Pode explicar o que é SSH, usuário e senha e escrever o comando: é uma demonstração guiada.',
    'gateway': 'Dentro do Financeiro B, a rota padrão aponta para 192.168.20.254, que não existe; o roteador é 192.168.20.1. '
               'Ajude a ler ip route e a trocar a rota (ip route del default e ip route add default via <gateway>).',
    'impressao': 'Do Financeiro B, a impressora 192.168.10.50 do outro prédio tem uma página web: curl http://192.168.10.50 '
                 'mostra o estado e curl -d "texto=..." http://192.168.10.50/imprimir imprime uma folha. '
                 'Explique que o curl faz um pedido HTTP, como um navegador, e que ele atravessa o roteador.',
    'comprovar': 'Tudo pronto; o aluno só precisa clicar em Validar missão.',
}
REGRAS_SUPORTE = ('O terminal deste laboratório é o do PC da T.I. e aceita: ssh suporte@<endereço>, exit, ip addr show, ip route show, '
                  'ip route add default via <gateway>, ip route del default, ping <endereço>, curl http://<impressora> e '
                  'curl -d "texto=..." http://<impressora>/imprimir. '
                  'Não ensine outros comandos.\n')


def _alternativa_suporte(etapa, nivel, missao, rascunho):
    return {'acesso': 'Da T.I., digite ssh suporte@192.168.20.21 e, quando pedir, a senha suporte123. O prompt muda quando a conexão abre.',
            'gateway': 'No Financeiro B, leia ip route: o default aponta para quem? O gateway do Prédio B é a interface do roteador, 192.168.20.1.',
            'impressao': 'Do Financeiro B: curl http://192.168.10.50 abre a página da impressora; curl -d "texto=seu nome" http://192.168.10.50/imprimir imprime. O pedido atravessa o roteador até o Prédio A.',
            }.get(etapa, 'Tudo pronto: clique em Validar missão.')


def _bloquear_suporte(texto, etapa, nivel, missao, pergunta, rascunho):
    return 'filtro' if re.search(r'\b(?:sudo|wget)\b', texto, re.I) else None


GUIA_SUPORTE = {
    'acesso': 'Guia do Suporte remoto, etapa SSH. O aluno trabalha só no terminal da T.I. (192.168.20.30). Para entrar no '
              'Financeiro B: ssh suporte@192.168.20.21, isto é, o usuário suporte, a arroba e o endereço do computador. '
              'Depois do Enter o terminal pede a senha do usuário suporte, que é suporte123; ela não aparece enquanto é '
              'digitada, como num terminal de verdade. Senha errada mostra Permission denied e pede de novo; na terceira '
              'a conexão é recusada e é preciso digitar o ssh outra vez. Quando a conexão abre, o prompt muda para '
              'suporte@financeiro-b e os comandos seguintes rodam no Financeiro B.',
    'gateway': 'Guia do Suporte remoto, etapa gateway. Dentro do Financeiro B (prompt suporte@financeiro-b), ip route mostra '
               'a rota padrão na linha default via. Ela aponta para 192.168.20.254, que não existe; o roteador do Prédio B '
               'é 192.168.20.1. Para trocar: primeiro ip route del default, depois ip route add default via 192.168.20.1. '
               'Se o prompt voltou para suporte@ti, a conexão SSH foi fechada e é preciso entrar de novo.',
    'impressao': 'Guia do Suporte remoto, etapa impressão. A impressora fica no Prédio A, no endereço 192.168.10.50 '
                 '(192.168.20.50 não existe). Ela tem uma página web: curl http://192.168.10.50 mostra o estado e quantas '
                 'folhas saíram. Para imprimir: curl -d "texto=sua frase" http://192.168.10.50/imprimir. O -d envia os '
                 'dados de um formulário e o campo se chama texto, por isso o conteúdo entre aspas começa com texto= '
                 'seguido da frase; sem texto= o terminal recusa o comando. O caminho termina em /imprimir. A frase aceita '
                 'letras, números e espaços, até 60 caracteres. O comando precisa ser dado dentro do Financeiro B.',
    'comprovar': 'Guia do Suporte remoto, conclusão. Tudo pronto: o aluno clica em Validar missão, ao lado do tempo. O '
                 'servidor relê o Financeiro B e repete os testes: a T.I. alcança o Financeiro B e ele alcança a impressora.',
}
REGRAS_SUPORTE += ('O trecho Guia deste laboratório descreve os comandos aceitos e o que cada etapa pede: use-o para explicar '
                   'como fazer o laboratório. Se o aluno pergunta onde errou, compare o comando dele em ultimos_comandos '
                   '(digitado e motivo_da_recusa) com o formato do guia e aponte exatamente o que falta ou está diferente.\n')

PERFIL_SUPORTE = Perfil(conceitos=CONCEITOS_SUPORTE, restricoes=RESTRICOES_SUPORTE, ancoras=ANCORAS_SUPORTE,
    regras=REGRAS_SUPORTE, alternativa=_alternativa_suporte, contexto=_contexto(suporte), bloquear=_bloquear_suporte,
    guia=lambda etapa: GUIA_SUPORTE.get(etapa, GUIA_SUPORTE['comprovar']))
