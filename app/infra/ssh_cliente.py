import shlex
import socket
import time

import paramiko


CHAVE_PRIVADA = "/opt/packetlab/data/ssh-test/id_ed25519"

ENDERECOS_CONTROLE = {
    1: "172.30.250.1",
    2: "172.30.250.2",
}


def aguardar_porta(
    endereco: str,
    porta: int = 22,
    tentativas: int = 20,
    intervalo: float = 0.5,
) -> bool:
    for _ in range(tentativas):
        try:
            with socket.create_connection(
                (endereco, porta),
                timeout=1,
            ):
                return True
        except OSError:
            time.sleep(intervalo)

    return False


def iniciar_sshd_nos(
    core,
    session_id: int,
) -> None:
    comando = (
        "/usr/local/bin/iniciar-sshd "
        ">/tmp/sshd.log 2>&1 &"
    )

    for node_id, endereco in ENDERECOS_CONTROLE.items():
        codigo, saida = core.node_command(
            session_id,
            node_id,
            comando,
            wait=True,
            shell=True,
        )

        if codigo != 0:
            raise RuntimeError(
                f"Falha ao iniciar SSH no nó {node_id}: "
                f"{saida}"
            )

        if not aguardar_porta(endereco):
            _, log = core.node_command(
                session_id,
                node_id,
                "cat /tmp/sshd.log",
            )

            raise RuntimeError(
                f"SSH do nó {node_id} não respondeu "
                f"em {endereco}:22. Log: {log}"
            )

        print(
            f"SSH do nó {node_id} disponível "
            f"em {endereco}:22",
            flush=True,
        )



COMANDOS_AJUDA = {
    "ping": "ping -h",
    "ip": "ip help",
    "traceroute": "traceroute --help",
}


def obter_ajuda_local(
    node_id: int,
    comando: str,
    limite: int = 900,
) -> str:
    """
    Obtém somente linhas da ajuda relacionadas às opções
    que o aluno já utilizou.
    """

    try:
        partes = shlex.split(comando)
    except ValueError:
        return ""

    if not partes:
        return ""

    utilitario = partes[0].lower()
    comando_ajuda = COMANDOS_AJUDA.get(utilitario)

    if not comando_ajuda:
        return ""

    opcoes_usadas = {
        parte.split("=", 1)[0]
        for parte in partes[1:]
        if parte.startswith("-")
        and len(parte) <= 12
    }

    if not opcoes_usadas:
        return ""

    _, ajuda_completa = executar_comando_ssh(
        node_id,
        comando_ajuda,
        timeout=3,
    )

    if not ajuda_completa:
        return ""

    linhas_selecionadas = []

    for linha in ajuda_completa.splitlines():
        linha_limpa = linha.strip()

        if linha_limpa.lower().startswith("usage"):
            linhas_selecionadas.append(linha_limpa)
            continue

        if any(
            linha_limpa.startswith(f"{opcao} ")
            or linha_limpa == opcao
            for opcao in opcoes_usadas
        ):
            linhas_selecionadas.append(linha_limpa)

    if not linhas_selecionadas:
        return ""

    contexto = (
        f"Ajuda local do utilitário {utilitario}:\n"
        + "\n".join(linhas_selecionadas)
    )

    return contexto[:limite]

def executar_comando_ssh(
    node_id: int,
    comando: str,
    timeout: int = 10,
) -> tuple[int, str]:
    if node_id not in ENDERECOS_CONTROLE:
        raise ValueError(f"Nó SSH inválido: {node_id}")

    endereco = ENDERECOS_CONTROLE[node_id]
    cliente = paramiko.SSHClient()

    # Adequado para esta prova de conceito em rede isolada.
    # Na versão multiusuário usaremos chaves efêmeras por sessão.
    cliente.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    try:
        cliente.connect(
            hostname=endereco,
            port=22,
            username="root",
            key_filename=CHAVE_PRIVADA,
            look_for_keys=False,
            allow_agent=False,
            timeout=5,
            auth_timeout=5,
            banner_timeout=5,
        )

        _, stdout, stderr = cliente.exec_command(
            comando,
            timeout=timeout,
        )

        canal = stdout.channel
        canal.settimeout(timeout)

        try:
            codigo = canal.recv_exit_status()
        except socket.timeout:
            canal.close()

            return (
                124,
                (
                    "[PingLevel] O comando excedeu o tempo "
                    f"permitido de {timeout} segundos."
                ),
            )

        saida_normal = stdout.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        saida_erro = stderr.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        partes = []

        if saida_normal:
            partes.append(saida_normal)

        if saida_erro:
            partes.append(saida_erro)

        saida = "\n".join(partes)

        return codigo, saida

    finally:
        cliente.close()
