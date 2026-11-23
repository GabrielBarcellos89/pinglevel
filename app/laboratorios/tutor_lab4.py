"""Perfil do Link no Lab4 (chamados de suporte): trechos, restrições, textos revisados e filtros.

Cada chamado tem duas fases: antes de o aluno identificar a causa (o Link ajuda a observar, sem dizer a causa) e
depois (o Link ajuda a corrigir, sem entregar o comando com valores antes do nível 4).
"""
import re

from laboratorios.cenarios import configure_terminal as cenario
from laboratorios.tutor_referencias import Perfil

CONCEITOS = {
    'chamado-1': 'interface endereço IP comando ip addr ping rede inacessível rota padrão gateway',
    'chamado-2': 'rota padrão gateway tabela de roteamento ip route roteador encaminha pacotes',
    'chamado-3': 'prefixo máscara rede local entrega direta tabela de roteamento',
    'comprovar': 'teste conectividade ping rota padrão gateway',
}
# Trechos dos livros (ids da tabela chunks do índice RAG): Linux: Utilitários de Redes p.13 (ip addr add/del,
# ip route show, ip route add/del default) e Redes para Iniciantes p.75 (/24), p.154 (tabela de roteamento)
# e p.155 (gateway padrão).
ANCORAS = {'chamado-1': (16, 395), 'chamado-2': (16, 614, 617), 'chamado-3': (395, 614), 'comprovar': (617,)}
RESTRICOES = {
    'chamado-1': 'PC Novo: "acabou de ser instalado e não acessa nada". Enquanto causa_identificada for falso, o aluno '
                 'escolhe a causa entre: interface sem endereço IPv4, cabo desconectado ou servidor desligado; não diga '
                 'qual é nem que falta um endereço, ajude-o a ler ip addr show e o ping. Depois, ele configura endereço '
                 'livre /24 e rota padrão: não sugira endereço específico e, até o nível 3, não escreva comandos com '
                 'valores nem diga o endereço do gateway; explique as formas e o critério.',
    'chamado-2': 'PC Financeiro: "fala com os colegas, mas não alcança o servidor". Enquanto causa_identificada for '
                 'falso, não diga que a rota padrão aponta para um computador nem que o gateway está errado; ajude-o a '
                 'ler ip route e a comparar com o PC Novo, que funciona. Depois, até o nível 3, explique a forma '
                 'ip route del default / ip route add default via <gateway> sem escrever o endereço.',
    'chamado-3': 'PC Recepção: mesmo sintoma do chamado 2, causa diferente. Enquanto causa_identificada for falso, não '
                 'diga que o prefixo está errado ou largo demais nem que o servidor parece local; ajude-o a ler a linha '
                 'inet e a tabela de rotas e a pensar no que o prefixo define como "minha rede". Depois, até o nível 3, '
                 'não escreva o comando com o endereço; lembre que remover o endereço também remove a rota padrão.',
    'comprovar': 'Os três chamados estão resolvidos; o aluno só precisa concluir. Explique os resultados reais sem inventar.',
}
REGRAS = ('O terminal deste laboratório tem uma aba por computador (PC Novo, PC Financeiro, PC Recepção) e aceita apenas: '
          'ip addr show, ip addr add e ip addr del <endereço>/<prefixo> dev eth0, ip route show, '
          'ip route add default via <gateway>, ip route del default e ping <endereço> sem opções. Não ensine outros '
          'comandos, opções ou arquivos de configuração. Você pode explicar as mensagens que aparecerem na saída real '
          'do terminal.\n')
GATEWAY = cenario.GATEWAY

FORA_DO_ESCOPO = re.compile(r'\b(?:nslookup|dig|traceroute|tracert|ifconfig|netstat|arp|hostname|netplan|nmcli|dhclient|'
                            r'(?<!ip\s)route\s+add|ip\s+(?:link|neigh|tunnel|-6))\b|/etc/', re.I)
CAUSA = re.compile(r'(?:\bsem|n[ãa]o tem|n[ãa]o possui|n[ãa]o h[áa]|\bfalta|faltando|aus[êe]ncia de|\bnenhum)\s+'
                   r'(?:nenhum\s+|um\s+)?(?:endere[çc]o|ip\b|ipv4)', re.I)
# Frases que entregam a causa de cada chamado antes de o aluno respondê-la.
CAUSAS = {
    'chamado-1': CAUSA,
    'chamado-2': re.compile(
        r'(?:rota padr[ãa]o|gateway|default)[^.]{0,60}?\b(?:aponta|aponte|apontando|leva|vai)\s+para\s+(?:um|o|outro)\s+'
        r'(?:computador|pc|host|192\.168\.10\.11)|(?:gateway|rota padr[ãa]o)\s+(?:est[áa]\s+|[ée]\s+)?(?:errad|incorret)|'
        r'192\.168\.10\.11\s+(?:n[ãa]o\s+[ée]|[ée])\s+(?:o\s+|um\s+)?(?:roteador|computador)', re.I),
    'chamado-3': re.compile(
        r'prefixo\s+(?:/16\s+)?(?:est[áa]\s+|[ée]\s+)?(?:errad|incorret|larg|grande|amplo)|'
        r'/16\s+(?:est[áa]|[ée])\s+(?:errad|incorret|larg|grande|amplo)|(?:troc|mud|corrij)\w*\s+(?:o\s+)?(?:prefixo|/16)|'
        r'servidor\s+parece\s+(?:estar\s+)?(?:na\s+mesma\s+rede|local)', re.I),
}


def _chamado(missao, etapa):
    return next((c for c in missao.get('chamados') or [] if c.get('id') == etapa), {})


def _estado(missao, pc):
    return ((missao.get('estados') or {}).get(pc)) or {}


def alternativa(etapa, nivel, missao, rascunho):
    identificada = bool(_chamado(missao, etapa).get('correta'))
    if etapa == 'chamado-1':
        if not identificada:
            return ('Observe a saída de ip addr show do PC Novo: a interface eth0 aparece como ativa (UP)? Há alguma '
                    'linha inet com endereço IPv4? Compare com o que o ping respondeu.')
        if nivel >= 4:
            return (f'Exemplo: ip addr add 192.168.10.50/24 dev eth0 e ip route add default via {GATEWAY}, o roteador '
                    'na rede do Atendimento. Depois teste o servidor.')
        if nivel >= 2:
            return ('As formas são ip addr add <endereço>/<prefixo> dev eth0 e ip route add default via <gateway>. O '
                    'endereço precisa ser livre e da rede 192.168.10.0/24; o gateway é a interface do roteador nessa rede.')
        return 'Falta configurar o PC Novo para participar da rede e sair dela. Confira cada passo com ip addr e ip route.'
    if etapa == 'chamado-2':
        if not identificada:
            return ('Leia ip route no PC Financeiro e no PC Novo, que já funciona. As linhas default são iguais? Para '
                    'qual equipamento cada uma aponta?')
        if nivel >= 4:
            return f'Remova a rota com ip route del default e crie outra com ip route add default via {GATEWAY}; teste o servidor.'
        return ('Uma rota padrão errada precisa sair antes de entrar a certa: ip route del default e depois '
                'ip route add default via <gateway>. O gateway é o roteador, não outro computador.')
    if etapa == 'chamado-3':
        if not identificada:
            return ('Compare a linha inet do PC Recepção com a dos outros PCs. Que rede esse prefixo define? O servidor '
                    '192.168.20.10 fica dentro ou fora dela?')
        if nivel >= 4:
            return ('Troque o endereço: ip addr del 192.168.10.11/16 dev eth0, ip addr add 192.168.10.11/24 dev eth0 e '
                    f'recoloque a rota com ip route add default via {GATEWAY}. Teste o servidor.')
        return ('Remova o endereço com o prefixo atual e adicione o mesmo endereço com o prefixo da rede do Atendimento. '
                'Remover o endereço também remove a rota padrão: confira com ip route.')
    return 'Tudo pronto: clique em Concluir missão. O servidor relê os três PCs e repete os testes.'


def contexto(missao):
    etapa = missao.get('proxima_etapa')
    chamado = _chamado(missao, etapa)
    pcs = missao.get('pcs') or cenario.PCS
    return {'chamado_atual': {'pc': pcs.get(chamado.get('pc'), {}).get('nome'), 'sintoma': chamado.get('sintoma'),
                              'causa_identificada': bool(chamado.get('correta'))} if chamado else None,
        'estado_dos_pcs': {pcs[pc]['nome']: {k: e.get(k) for k in ('enderecos', 'rota_padrao')}
                           for pc, e in (missao.get('estados') or {}).items() if pc in pcs},
        'testes_confirmados': {pcs[pc]['nome']: t for pc, t in (missao.get('testes') or {}).items() if pc in pcs},
        'ultimos_comandos_reais': [{'computador': pcs.get(t.get('pc'), {}).get('nome'), 'digitado': t.get('digitado'),
                                    'saida': (t.get('saida') or '')[-1200:], 'codigo': t.get('codigo')}
                                   for t in (missao.get('terminal') or [])[-3:]]}


def bloquear(texto, etapa, nivel, missao, pergunta, rascunho):
    if re.search(r'\b(?:sudo|curl|wget|ssh)\b', texto, re.I):
        return 'filtro'
    if FORA_DO_ESCOPO.search(texto):
        return 'fora_do_tema'
    chamado = _chamado(missao, etapa)
    if chamado and not chamado.get('correta') and etapa in CAUSAS and CAUSAS[etapa].search(texto):
        return 'filtro'
    if nivel < 4:
        referencia = f"{pergunta} {rascunho.get('comando', '')}"
        for ip in re.findall(r'\bip\s+addr(?:ess)?\s+add\s+(\d{1,3}(?:\.\d{1,3}){3})', texto, re.I):
            if ip not in referencia:
                return 'filtro'
        rota = _estado(missao, chamado.get('pc')).get('rota_padrao')
        for ip in re.findall(r'\bvia\s+(\d{1,3}(?:\.\d{1,3}){3})', texto, re.I):
            if ip not in referencia and ip != rota:
                return 'filtro'
        # O endereço do gateway é descoberto no chamado 1; depois ele já está no PC Novo, usado como comparação.
        if (etapa == 'chamado-1' and re.search(r'(?<![0-9.])192\.168\.10\.1(?![0-9.])', texto)
                and GATEWAY not in referencia and rota != GATEWAY):
            return 'filtro'
    return None


PERFIL = Perfil(conceitos=CONCEITOS, restricoes=RESTRICOES, ancoras=ANCORAS, regras=REGRAS,
    alternativa=alternativa, contexto=contexto, bloquear=bloquear)
