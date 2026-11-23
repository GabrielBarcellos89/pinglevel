from __future__ import annotations

import re
import shlex


LABORATORIO_ID = "primeiro-contato"
TITULO = "Missão: Primeiro Contato"
DESCRICAO = (
    "Identifique os computadores, consulte o endereçamento IPv4 "
    "e verifique a comunicação na rede local."
)
XP = 100
TEMPO_LIMITE = 300
TEMPO_EXTENSAO = 180
MAX_EXTENSOES = 1
PERFIL_CAPTURA = "arp_icmp"

NOS = {
    1: {
        "id": 1,
        "nome": "Computador 1",
        "tipo": "computador",
        "ip": "10.0.0.20",
        "prefixo": 24,
    },
    2: {
        "id": 2,
        "nome": "Computador 2",
        "tipo": "computador",
        "ip": "10.0.0.21",
        "prefixo": 24,
    },
    3: {
        "id": 3,
        "nome": "Switch",
        "tipo": "switch",
        "ip": None,
        "prefixo": None,
    },
}

ETAPAS = (
    {
        "id": "identificacao",
        "titulo": "Identifique o dispositivo",
        "orientacao": (
            "Selecione o Computador 1 e descubra o nome "
            "do dispositivo."
        ),
        "comando_sugerido": "hostname",
    },
    {
        "id": "enderecamento",
        "titulo": "Consulte o endereço IPv4",
        "orientacao": (
            "Consulte as interfaces do Computador 1 e "
            "localize seu endereço IPv4."
        ),
        "comando_sugerido": "ip addr show eth0",
    },
    {
        "id": "conectividade",
        "titulo": "Teste a comunicação",
        "orientacao": (
            "Verifique se o Computador 1 consegue alcançar "
            "o Computador 2."
        ),
        "comando_sugerido": "ping -c 2 10.0.0.21",
    },
)


def detectar_evidencias(
    node_id: int,
    comando: str,
    codigo: int,
    saida: str,
) -> set[str]:
    """Identifica quais objetivos foram comprovados pelo comando."""

    if int(node_id) != 1 or int(codigo) != 0:
        return set()

    comando = str(comando or "").strip()
    saida = str(saida or "")
    evidencias = set()

    if comando == "hostname" and saida.strip():
        evidencias.add("identificacao")

    if (
        comando in {
            "ip addr",
            "ip addr show",
            "ip addr show eth0",
        }
        and "10.0.0.20/24" in saida
    ):
        evidencias.add("enderecamento")

    try:
        partes = shlex.split(comando)
    except ValueError:
        partes = []

    if (
        len(partes) == 4
        and partes[0] == "ping"
        and partes[1] == "-c"
        and partes[3] == "10.0.0.21"
    ):
        resultado = re.search(r"(\d+)% packet loss", saida)
        perda = int(resultado.group(1)) if resultado else None

        if perda == 0:
            evidencias.add("conectividade")

    return evidencias


def montar_estado(evidencias: set[str] | None = None) -> dict:
    """Monta o estado público que poderá ser enviado ao frontend."""

    concluidas = set(evidencias or ())
    etapas = [
        {
            **etapa,
            "concluida": etapa["id"] in concluidas,
        }
        for etapa in ETAPAS
    ]

    proxima = next(
        (
            etapa["id"]
            for etapa in etapas
            if not etapa["concluida"]
        ),
        None,
    )

    return {
        "id": LABORATORIO_ID,
        "titulo": TITULO,
        "descricao": DESCRICAO,
        "xp": XP,
        "nos": list(NOS.values()),
        "etapas": etapas,
        "evidencias": sorted(concluidas),
        "proxima_etapa": proxima,
        "concluido": proxima is None,
    }

PERGUNTAS = {
    "previsao": {
        "enunciado": "Os dois computadores estão na mesma rede. O que você espera ao executar o ping?",
        "opcoes": [
            {"id": "resposta", "texto": "O Computador 2 deve responder ao Computador 1."},
            {"id": "sem_resposta", "texto": "O Computador 1 envia pedidos, mas não recebe respostas."},
            {"id": "sem_envio", "texto": "Nenhum pedido será enviado."},
        ],
    },
    "interpretacao": {
        "enunciado": "O ping terminou com 0% de perda. O que as respostas ICMP comprovam?",
        "opcoes": [
            {"id": "internet", "texto": "Todos os serviços e o acesso à internet estão funcionando."},
            {"id": "alcance", "texto": "Houve comunicação de ida e volta entre os computadores durante o teste."},
            {"id": "sem_rede", "texto": "Os computadores não precisam de uma rede para se comunicar."},
        ],
    },
}
