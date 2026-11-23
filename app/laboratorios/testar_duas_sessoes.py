import socket
import time
from dataclasses import dataclass

import paramiko

from core.api.grpc import client
from core.api.grpc.wrappers import (
    Interface,
    NodeType,
    Position,
)


IMAGEM = "pinglevel/ssh:0.1"
CHAVE = "/opt/packetlab/data/ssh-test/id_ed25519"


@dataclass
class Laboratorio:
    aluno: str
    session_id: int
    controlnet: str
    docker1_ip: str
    docker2_ip: str
    docker1_nome_real: str
    docker2_nome_real: str


def aguardar_porta(
    endereco: str,
    porta: int = 22,
    tentativas: int = 20,
) -> bool:
    for _ in range(tentativas):
        try:
            with socket.create_connection(
                (endereco, porta),
                timeout=1,
            ):
                return True
        except OSError:
            time.sleep(0.5)

    return False


def executar_ssh(
    endereco: str,
    comando: str,
    timeout: int = 10,
) -> tuple[int, str]:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    try:
        ssh.connect(
            hostname=endereco,
            username="root",
            key_filename=CHAVE,
            look_for_keys=False,
            allow_agent=False,
            timeout=5,
            auth_timeout=5,
        )

        _, stdout, stderr = ssh.exec_command(
            comando,
            timeout=timeout,
        )

        codigo = stdout.channel.recv_exit_status()

        saida_normal = stdout.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        saida_erro = stderr.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        saida = "\n".join(
            parte
            for parte in (saida_normal, saida_erro)
            if parte
        )

        return codigo, saida

    finally:
        ssh.close()


def iniciar_sshd(
    core: client.CoreGrpcClient,
    session_id: int,
    node_id: int,
    endereco: str,
) -> None:
    codigo, saida = core.node_command(
        session_id,
        node_id,
        (
            "/usr/local/bin/iniciar-sshd "
            ">/tmp/sshd.log 2>&1 &"
        ),
        wait=True,
        shell=True,
    )

    if codigo != 0:
        raise RuntimeError(
            f"Falha ao iniciar SSH: {saida}"
        )

    if not aguardar_porta(endereco):
        raise RuntimeError(
            f"SSH não respondeu em {endereco}:22"
        )


def criar_laboratorio(
    core: client.CoreGrpcClient,
    aluno: str,
    indice_rede: int,
) -> Laboratorio:
    sessao = core.create_session()
    session_id = sessao.id

    prefixo = f"172.30.{indice_rede}"
    controlnet = f"{prefixo}.0/24"
    docker1_ip = f"{prefixo}.1"
    docker2_ip = f"{prefixo}.2"

    nome_base = aluno.lower().replace(" ", "-")
    docker1_nome = (
        f"pl-s{session_id}-{nome_base}-docker1"
    )
    docker2_nome = (
        f"pl-s{session_id}-{nome_base}-docker2"
    )
    switch_nome = (
        f"pl-s{session_id}-{nome_base}-switch1"
    )

    try:
        sessao.set_options({
            "controlnet": controlnet,
        })

        docker1 = sessao.add_node(
            1,
            name=docker1_nome,
            _type=NodeType.DOCKER,
            image=IMAGEM,
            position=Position(x=150, y=100),
        )

        docker2 = sessao.add_node(
            2,
            name=docker2_nome,
            _type=NodeType.DOCKER,
            image=IMAGEM,
            position=Position(x=450, y=100),
        )

        switch1 = sessao.add_node(
            3,
            name=switch_nome,
            _type=NodeType.SWITCH,
            position=Position(x=300, y=250),
        )

        sessao.add_link(
            node1=docker1,
            node2=switch1,
            iface1=Interface(
                id=0,
                name="eth0",
                ip4="10.0.0.20",
                ip4_mask=24,
            ),
            iface2=Interface(
                id=0,
                name="eth0",
            ),
        )

        sessao.add_link(
            node1=docker2,
            node2=switch1,
            iface1=Interface(
                id=0,
                name="eth0",
                ip4="10.0.0.21",
                ip4_mask=24,
            ),
            iface2=Interface(
                id=1,
                name="eth1",
            ),
        )

        sucesso, erros = core.start_session(sessao)

        if not sucesso:
            raise RuntimeError(
                "; ".join(erros or [])
            )

        iniciar_sshd(
            core,
            session_id,
            1,
            docker1_ip,
        )

        iniciar_sshd(
            core,
            session_id,
            2,
            docker2_ip,
        )

        return Laboratorio(
            aluno=aluno,
            session_id=session_id,
            controlnet=controlnet,
            docker1_ip=docker1_ip,
            docker2_ip=docker2_ip,
            docker1_nome_real=docker1_nome,
            docker2_nome_real=docker2_nome,
        )

    except Exception:
        core.delete_session(session_id)
        raise


def mostrar_resultado(
    descricao: str,
    codigo: int,
    saida: str,
) -> None:
    print()
    print(f"===== {descricao} =====")
    print(f"Código: {codigo}")
    print(saida or "(saída vazia)")


def main() -> None:
    core = client.CoreGrpcClient()
    core.connect()

    if core.get_sessions():
        raise RuntimeError(
            "Existem sessões CORE abertas. "
            "O teste exige um ambiente limpo."
        )

    laboratorios = []

    try:
        print("Criando laboratório do Aluno A...")

        aluno_a = criar_laboratorio(
            core,
            aluno="aluno-a",
            indice_rede=1,
        )
        laboratorios.append(aluno_a)

        print("Criando laboratório do Aluno B...")

        aluno_b = criar_laboratorio(
            core,
            aluno="aluno-b",
            indice_rede=2,
        )
        laboratorios.append(aluno_b)

        print()
        print("Dois laboratórios iniciados.")
        print(
            f"Aluno A: sessão {aluno_a.session_id}, "
            f"controlnet {aluno_a.controlnet}"
        )
        print(
            f"Aluno B: sessão {aluno_b.session_id}, "
            f"controlnet {aluno_b.controlnet}"
        )

        codigo, saida = executar_ssh(
            aluno_a.docker1_ip,
            "ping -c 2 10.0.0.21",
        )
        mostrar_resultado(
            "ALUNO A — PING INTERNO",
            codigo,
            saida,
        )

        codigo, saida = executar_ssh(
            aluno_b.docker1_ip,
            "ping -c 2 10.0.0.21",
        )
        mostrar_resultado(
            "ALUNO B — PING INTERNO",
            codigo,
            saida,
        )

        codigo, saida = executar_ssh(
            aluno_a.docker1_ip,
            (
                "ip route add "
                "172.16.99.0/24 dev eth0"
            ),
        )
        mostrar_resultado(
            "ALUNO A — ADICIONAR ROTA",
            codigo,
            saida,
        )

        codigo, saida = executar_ssh(
            aluno_a.docker1_ip,
            "ip route show 172.16.99.0/24",
        )
        mostrar_resultado(
            "ALUNO A — CONSULTAR ROTA",
            codigo,
            saida,
        )

        codigo_b, saida_b = executar_ssh(
            aluno_b.docker1_ip,
            "ip route show 172.16.99.0/24",
        )
        mostrar_resultado(
            "ALUNO B — VERIFICAR ISOLAMENTO",
            codigo_b,
            saida_b,
        )

        if saida_b:
            raise RuntimeError(
                "Falha de isolamento: a rota do Aluno A "
                "apareceu no laboratório do Aluno B."
            )

        print()
        print("Isolamento confirmado: a rota existe somente no Aluno A.")

        print()
        print(
            f"Encerrando somente a sessão "
            f"{aluno_a.session_id} do Aluno A..."
        )
        core.delete_session(aluno_a.session_id)
        laboratorios.remove(aluno_a)

        codigo, saida = executar_ssh(
            aluno_b.docker1_ip,
            "ping -c 2 10.0.0.21",
        )
        mostrar_resultado(
            "ALUNO B APÓS ENCERRAR ALUNO A",
            codigo,
            saida,
        )

        if codigo != 0:
            raise RuntimeError(
                "O laboratório B foi afetado pela "
                "remoção do laboratório A."
            )

        print()
        print("TESTE MULTIUSUÁRIO APROVADO!")
        print(
            "O laboratório B permaneceu funcional após "
            "a remoção do laboratório A."
        )

    finally:
        print()
        print("Limpando sessões restantes...")

        for laboratorio in list(laboratorios):
            try:
                core.delete_session(
                    laboratorio.session_id
                )
                print(
                    f"Sessão {laboratorio.session_id} removida."
                )
            except Exception as erro:
                print(
                    f"Falha ao remover sessão "
                    f"{laboratorio.session_id}: {erro}"
                )


if __name__ == "__main__":
    main()
