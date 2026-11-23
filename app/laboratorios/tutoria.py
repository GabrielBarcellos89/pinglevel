from __future__ import annotations

import re
import unicodedata


ORDEM_ETAPAS = {
    "identificacao": 1,
    "enderecamento": 2,
    "conectividade": 3,
}

COMANDOS_AUTORIZADOS = {
    "identificacao": ("hostname",),
    "enderecamento": ("ip a", "ip addr", "ip addr show", "ip addr show eth0"),
    "conectividade": (
        "ping 10.0.0.21",
        "ping -c 1 10.0.0.21",
        "ping -c 2 10.0.0.21",
        "ping -c 3 10.0.0.21",
        "ping -c 4 10.0.0.21",
        "ping -c 5 10.0.0.21",
    ),
}

FONTES_ETAPA = {
    "identificacao": (
        "Linux: Utilitários de Redes — página 63; "
        "Redes para Iniciantes — página 244"
    ),
    "enderecamento": (
        "Linux: Utilitários de Redes — página 13; "
        "Redes para Iniciantes — página 78"
    ),
    "conectividade": (
        "Linux: Utilitários de Redes — página 19; "
        "Redes para Iniciantes — página 224"
    ),
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^\w./:-]+", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def _assunto(texto: str) -> str | None:
    if re.search(r"\b(ping|alcance|conectividade|comunicacao|rota)\b", texto):
        return "conectividade"
    if re.search(r"\b(ip|ipv4|endereco|interface|ifconfig)\b", texto):
        return "enderecamento"
    if re.search(r"\b(host|hostname|nome|name|identifica)\w*\b", texto):
        return "identificacao"
    return None


def _pedido_resposta(texto: str) -> bool:
    return any(expressao in texto for expressao in (
        "qual a resposta", "me diga a resposta", "diga a resposta",
        "me mostra", "nao sei", "desisto",
    ))


def _duvida_conceitual(texto: str) -> bool:
    acoes_da_missao = (
        "como identifico", "como descobrir", "como descubro",
        "como consulto", "como vejo", "como testar", "como testo",
        "qual comando", "que comando", "o comando", "qual a resposta",
        "me ajuda", "ajuda", "nao sei", "desisto",
    )
    if any(acao in texto for acao in acoes_da_missao):
        return False
    return texto.startswith((
        "o que ", "por que ", "porque ", "qual a diferenca",
        "como funciona", "como o ", "como ele ", "como isso ",
        "ele ", "isso ", "essa ", "esse ",
    ))


def _resposta_identificacao(texto: str, nivel: int, classificacao: str) -> str:
    palavras = set(texto.split())
    if classificacao == "fora_da_etapa":
        return (
            "Essa consulta pertence a uma etapa posterior. Primeiro descubra o nome "
            "do Computador 1 no terminal; depois avançaremos para endereçamento e comunicação."
        )
    if classificacao in {"comando_correto", "dificuldade_persistente"}:
        return (
            "O comando é `hostname`. Ele consulta o nome atribuído ao sistema. "
            "Digite `hostname` no terminal do Computador 1 e pressione Enter."
        )
    if "host" in palavras and "name" in palavras:
        if texto.find("name") < texto.find("host"):
            return (
                "Você encontrou as duas partes. No comando, elas aparecem na ordem "
                "inversa e são escritas juntas, sem espaço. Ajuste e execute no terminal."
            )
        return (
            "Você encontrou o termo correto. No Linux, esse comando é escrito como "
            "uma única palavra, sem espaço. Ajuste e execute no terminal."
        )
    if texto in {"name", "nome"}:
        return (
            "Você encontrou a ideia de nome. Falta relacioná-la ao termo usado para "
            "um computador na rede. Complete essa palavra e tente o comando no terminal."
        )
    if nivel >= 3:
        return (
            "O nome do sistema é chamado hostname. O comando usa exatamente esse termo, "
            "escrito junto. Faça essa tentativa no terminal do Computador 1."
        )
    if nivel == 2:
        return (
            "Procure o termo em inglês formado pelas ideias de computador na rede e nome. "
            "Ele também é usado como comando no Linux. Faça uma tentativa no terminal."
        )
    return (
        "Todo computador Linux possui um nome usado pelo próprio sistema. Existe um "
        "comando curto que consulta essa identificação. Pense no termo em inglês usado "
        "para o nome de um computador na rede."
    )


def _resposta_enderecamento(texto: str, nivel: int, classificacao: str) -> str:
    if classificacao == "fora_da_etapa":
        return (
            "O teste de comunicação pertence à próxima etapa. Primeiro localize o endereço "
            "IPv4 do Computador 1 consultando suas interfaces de rede."
        )
    if classificacao in {"comando_correto", "dificuldade_persistente"}:
        return (
            "Use `ip addr show eth0`. Esse comando mostra os endereços configurados na "
            "interface eth0. Execute-o no Computador 1 e procure a linha iniciada por `inet`."
        )
    if texto == "ifconfig":
        return (
            "`ifconfig` é uma ferramenta conhecida, mas não faz parte desta atividade. "
            "Aqui usamos o utilitário `ip`. Pense em como pedir a ele os endereços da interface."
        )
    if texto in {"ip", "ip addr", "ip address"}:
        return (
            "Você escolheu a ferramenta correta. Agora indique que deseja consultar os "
            "endereços da interface. Complete o comando e execute-o no Computador 1."
        )
    if nivel >= 3:
        return (
            "A ferramenta usada nesta atividade é `ip`. Combine-a com a consulta de "
            "endereços e observe a interface eth0 no Computador 1."
        )
    if nivel == 2:
        return (
            "Procure uma ferramenta curta do Linux cujo nome também representa endereço "
            "de rede. Ela permite consultar as interfaces do Computador 1."
        )
    return (
        "O endereço IPv4 aparece nas informações das interfaces de rede. Procure uma "
        "ferramenta do Linux que consulte interfaces e endereços, e faça uma tentativa "
        "no terminal do Computador 1."
    )


def _resposta_conectividade(texto: str, nivel: int, classificacao: str) -> str:
    if classificacao in {"comando_correto", "dificuldade_persistente"}:
        return (
            "Use `ping -c 2 10.0.0.21`. O `-c 2` limita o teste a dois pacotes, evitando "
            "uma execução contínua. Execute no Computador 1 e observe se há respostas."
        )
    if texto == "ping":
        return (
            "Você escolheu a ferramenta correta. Agora falta informar quantos pacotes enviar "
            "e o endereço do Computador 2, visível na topologia."
        )
    if nivel >= 3:
        return (
            "Use o ping com uma quantidade limitada de pacotes e informe como destino o "
            "IPv4 do Computador 2 mostrado na topologia."
        )
    return (
        "Ping envia pequenos pacotes de teste e verifica se o outro computador responde. "
        "Nesta etapa, o teste deve partir do Computador 1 em direção ao Computador 2."
    )


def avaliar_interacao(etapa_id: str, pergunta: str, historico: list[dict]) -> dict:
    texto = _normalizar(pergunta)
    anteriores = [item for item in historico if item.get("etapa_id") == etapa_id]
    assunto = _assunto(texto)
    classificacao = "duvida_conceitual"

    if assunto and ORDEM_ETAPAS.get(assunto, 0) > ORDEM_ETAPAS.get(etapa_id, 0):
        classificacao = "fora_da_etapa"
    elif etapa_id == "identificacao":
        if texto == "hostname":
            classificacao = "comando_correto"
        elif set(texto.split()) >= {"host", "name"}:
            classificacao = "tentativa_aproximada"
        elif texto in {"name", "nome"}:
            classificacao = "conceito_parcial"
    elif etapa_id == "enderecamento":
        if texto in {"ip a", "ip addr", "ip addr show", "ip addr show eth0"}:
            classificacao = "comando_correto"
        elif texto in {"ip", "ip address", "ifconfig"}:
            classificacao = "tentativa_aproximada"
    elif etapa_id == "conectividade":
        if re.fullmatch(r"ping(?: -c [1-5])? 10\.0\.0\.21", texto):
            classificacao = "comando_correto"
        elif texto == "ping" or texto.startswith("ping "):
            classificacao = "tentativa_aproximada"

    nivel = min(4, len(anteriores) + 1)
    if classificacao == "tentativa_aproximada":
        nivel = max(3, nivel)
    if classificacao == "comando_correto":
        nivel = 4
    if _pedido_resposta(texto) and len(anteriores) >= 2:
        classificacao = "dificuldade_persistente"
        nivel = 4

    explicacao_livre = (
        classificacao != "fora_da_etapa"
        and _duvida_conceitual(texto)
    )

    if explicacao_livre:
        resposta = None
        classificacao = "explicacao_conceitual"
    elif etapa_id == "identificacao":
        resposta = _resposta_identificacao(texto, nivel, classificacao)
    elif etapa_id == "enderecamento":
        resposta = _resposta_enderecamento(texto, nivel, classificacao)
    elif etapa_id == "conectividade":
        resposta = _resposta_conectividade(texto, nivel, classificacao)
    else:
        resposta = "A missão já foi concluída. Revise o resultado apresentado na tela."

    return {
        "etapa_id": etapa_id,
        "pergunta": pergunta,
        "nivel": nivel,
        "classificacao": classificacao,
        "detalhe": (
            "Responda à dúvida conceitual usando os materiais e o histórico."
            if explicacao_livre
            else "Resposta pedagógica controlada pelo cenário."
        ),
        "historico": anteriores[-4:],
        "resposta_controlada": resposta,
        "fonte_controlada": FONTES_ETAPA.get(etapa_id, "Materiais da missão Primeiro Contato"),
        "comandos_autorizados": COMANDOS_AUTORIZADOS.get(etapa_id, ()),
    }
