from __future__ import annotations

import hashlib
import html
import ipaddress
import re
import shlex
import sqlite3
import threading
import time
from collections import defaultdict, deque

from autenticacao import BANCO


_lock = threading.RLock()
_eventos = defaultdict(deque)


def _agora():
    return time.monotonic()


def permitir(chave: str, limite: int, janela: int) -> bool:
    agora = _agora()
    with _lock:
        fila = _eventos[chave]
        while fila and agora - fila[0] >= janela:
            fila.popleft()
        if len(fila) >= limite:
            return False
        fila.append(agora)
        return True


def limpar_limite(chave: str):
    with _lock:
        _eventos.pop(chave, None)


def inicializar_auditoria():
    with sqlite3.connect(BANCO, timeout=10) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_seguranca (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                evento TEXT NOT NULL,
                origem TEXT NOT NULL,
                detalhes TEXT NOT NULL DEFAULT '',
                criado_em INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_auditoria_seguranca_criado
            ON auditoria_seguranca(criado_em DESC)
        """)


def auditar(evento: str, origem: str, usuario_id=None, detalhes=""):
    try:
        with sqlite3.connect(BANCO, timeout=5) as conexao:
            conexao.execute(
                """INSERT INTO auditoria_seguranca
                   (usuario_id, evento, origem, detalhes, criado_em)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario_id, evento[:60], origem[:80], str(detalhes)[:500], int(time.time())),
            )
    except Exception as erro:
        print(f"Auditoria de segurança indisponível: {erro}", flush=True)


OPERADORES_PROIBIDOS = (";", "&&", "||", "|", ">", "<", "`", "$(", "${", "\n", "\r")


def validar_comando(comando: str) -> tuple[bool, str, str]:
    comando = str(comando or "").strip()
    if not comando:
        return False, "", "Digite um comando."
    if len(comando) > 160:
        return False, "", "O comando ultrapassa o limite de 160 caracteres."
    if any(item in comando for item in OPERADORES_PROIBIDOS):
        return False, "", "Operadores de shell e encadeamento não são permitidos neste laboratório."
    try:
        partes = shlex.split(comando, posix=True)
    except ValueError:
        return False, "", "A sintaxe do comando não pôde ser interpretada."
    if not partes:
        return False, "", "Digite um comando."

    comandos_identificacao = {
        ("hostname",),
        ("hostname", "-s"),
        ("uname", "-n"),
        ("cat", "/etc/hostname"),
    }

    if tuple(partes) in comandos_identificacao:
        # As formas equivalentes são normalizadas para manter a
        # validação da missão independente do comando escolhido.
        return True, "hostname", ""

    comandos_endereco = {
        ("ip", "a"),
        ("ip", "addr"),
        ("ip", "address"),
        ("ip", "addr", "show"),
        ("ip", "address", "show"),
        ("ip", "addr", "show", "eth0"),
        ("ip", "address", "show", "eth0"),
        ("ifconfig",),
        ("ifconfig", "eth0"),
        ("hostname", "-I"),
    }

    if tuple(partes) in comandos_endereco:
        # Todas as formas aceitas são convertidas para o comando
        # didático, evitando a exposição da interface de controle.
        return True, "ip addr show eth0", ""

    if partes == ["if", "config"]:
        return (
            False,
            "",
            "O comando foi escrito separado. Você quis dizer "
            "'ifconfig'? Também é possível consultar o endereço "
            "com 'ip a'.",
        )

    if partes[0] == "ip" and partes[1:] in (
        ["route"],
        ["route", "show"],
        ["link"],
        ["link", "show"],
    ):
        return True, " ".join(partes), ""
    if partes[0] == "ping":
        aviso = ""

        if len(partes) == 2:
            quantidade = 5
            destino_texto = partes[1]
            aviso = (
                "O PingLevel limitou automaticamente o teste a 5 "
                "pacotes para evitar que o ping permaneça executando "
                "indefinidamente."
            )
        elif len(partes) == 4 and partes[1] == "-c":
            destino_texto = partes[3]
            try:
                quantidade_solicitada = int(partes[2])
            except ValueError:
                return False, "", "A quantidade de pacotes precisa ser um número inteiro."

            if quantidade_solicitada < 1:
                return False, "", "A quantidade deve ser de pelo menos 1 pacote."

            quantidade = min(quantidade_solicitada, 5)
            if quantidade_solicitada > 5:
                aviso = (
                    f"A quantidade solicitada ({quantidade_solicitada}) "
                    "foi reduzida para 5 pacotes, que é o limite de "
                    "segurança deste laboratório."
                )
        else:
            return (
                False,
                "",
                "Use 'ping ENDEREÇO' ou 'ping -c QUANTIDADE ENDEREÇO'.",
            )

        try:
            destino = ipaddress.ip_address(destino_texto)
        except ValueError:
            return False, "", "O endereço IPv4 informado não é válido."
        if destino not in ipaddress.ip_network("10.0.0.0/24"):
            return False, "", "O destino deve pertencer à rede didática 10.0.0.0/24."
        return True, f"ping -c {quantidade} {destino}", aviso
    return False, "", "Comando não autorizado nesta atividade. Use apenas as ferramentas indicadas pela aula."


PADROES_INJECAO = (
    r"ignore\s+(as|todas|qualquer|suas)?\s*(instruções|instrucoes|regras)",
    r"ignore\s+(all\s+|any\s+|your\s+)?(previous\s+)?(instructions|rules)",
    r"(revele|mostre|exiba|imprima).{0,35}(prompt|instruções do sistema|system prompt)",
    r"(reveal|show|display|print).{0,35}(system prompt|system message|instructions|rules)",
    r"(finja|aja|atue)\s+como",
    r"(pretend|act)\s+(to be|as)",
    r"modo\s+(desenvolvedor|developer|jailbreak)",
    r"(developer|jailbreak)\s+mode",
    r"(desconsidere|substitua).{0,30}(regras|instruções|instrucoes)",
    r"(repeat|repita).{0,30}(texto acima|text above|system message)",
    r"<\s*/?\s*(system|assistant|developer|tool|user)[^>]*>",
    r"<\s*/?\s*(pergunta_do_aluno|material_recuperado|terminal)[^>]*>",
)


def sanitizar_dado_llm(valor, limite: int) -> str:
    texto = str(valor or "").strip()

    texto = "".join(
        caractere
        if caractere in ("\n", "\t") or ord(caractere) >= 32
        else " "
        for caractere in texto
    )

    texto = texto[:limite]

    return html.escape(
        texto,
        quote=True,
    )


def resumir_pergunta_auditoria(pergunta) -> str:
    texto = str(pergunta or "")

    impressao = hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()[:16]

    return (
        f"tamanho={len(texto)};"
        f"sha256={impressao}"
    )


PADROES_VAZAMENTO_TUTOR = (
    r"anthropic_api_key",
    r"system prompt",
    r"instruções de sistema",
    r"instrucoes de sistema",
    r"hierarquia obrigatória",
    r"hierarquia obrigatoria",
    r"<pergunta_do_aluno_nao_confiavel>",
    r"<material_recuperado_nao_confiavel>",
    r"<terminal_nao_confiavel>",
)


def validar_resposta_tutor(resposta) -> tuple[bool, str]:
    texto = str(resposta or "").strip()

    texto = "".join(
        caractere
        if caractere in ("\n", "\t") or ord(caractere) >= 32
        else " "
        for caractere in texto
    ).strip()

    if not texto:
        return (
            False,
            "O tutor não produziu uma resposta válida.",
        )

    if len(texto) > 2_000:
        return (
            False,
            "A resposta do tutor ultrapassou o limite permitido.",
        )

    normalizada = texto.lower()

    if any(
        re.search(padrao, normalizada)
        for padrao in PADROES_VAZAMENTO_TUTOR
    ):
        return (
            False,
            "A resposta do tutor foi bloqueada pela política de segurança.",
        )

    return True, texto


def validar_pergunta(pergunta: str) -> tuple[bool, str]:
    pergunta = str(pergunta or "").strip()
    if not pergunta:
        return False, "Digite uma pergunta relacionada à atividade."
    if len(pergunta) > 500:
        return False, "A pergunta deve possuir no máximo 500 caracteres."
    normalizada = pergunta.lower()
    if any(re.search(padrao, normalizada) for padrao in PADROES_INJECAO):
        return False, "Não posso alterar minhas regras ou revelar instruções internas. Posso ajudar com a atividade de redes."
    return True, ""


inicializar_auditoria()
