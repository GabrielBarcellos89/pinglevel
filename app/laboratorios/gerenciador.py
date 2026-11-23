from __future__ import annotations

import json
import math
import re
import socket
import shlex
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import paramiko
from core.api.grpc import client
from core.api.grpc.wrappers import Interface, NodeType, Position

from laboratorios.cenarios.catalogo import (
    LABORATORIO_PADRAO,
    obter_cenario,
)
from laboratorios.tutoria import avaliar_interacao
from laboratorios.captura import Captura
from laboratorios.topologia_gateway import construir as construir_gateway, preparar as preparar_gateway
from laboratorios import topologia_setores


IMAGEM = "pinglevel/ssh:0.1"
IMAGEM_GATEWAY = "pinglevel/gateway:0.1"
# Laboratórios do fluxo novo (nome histórico COM_ROTEADOR): Lab 2 (sem roteador), Labs 3 e 4, setores (Labs 5 a 10). Todos têm limpeza confirmada.
COM_SETORES = ('primeira-lan', 'dividindo-uma-rede', 'planejando-uma-empresa', 'conectando-redes', 'investigando-a-lan',
               'enderecos-e-nomes', 'desafio-rede-da-empresa', 'suporte-remoto')
COM_ROTEADOR = ('primeira-lan', 'saindo-da-rede-local', 'configure-pelo-terminal', 'dividindo-uma-rede', 'planejando-uma-empresa',
                'conectando-redes', 'investigando-a-lan', 'enderecos-e-nomes', 'desafio-rede-da-empresa', 'suporte-remoto')
CHAVE_SSH = "/opt/packetlab/data/ssh-test/id_ed25519"
ARQUIVO_ESTADO = Path("/opt/packetlab/data/laboratorios_ativos.json")


@dataclass
class Laboratorio:
    usuario_id: int
    login: str
    laboratorio_id: str
    session_id: int
    indice_rede: int
    controlnet: str
    enderecos: dict[int, str]
    iniciado_em: float
    prazo: float
    tempo_extensao: int
    max_extensoes: int
    extensoes_utilizadas: int = 0
    heartbeat: float = field(default_factory=time.time)
    ultimos_comandos: dict[int, dict] = field(default_factory=dict)
    evidencias: set[str] = field(default_factory=set)
    total_comandos: int = 0
    preparacao_confirmada: bool = True
    historico_tutor: list[dict] = field(default_factory=list)
    bastidores: dict | None = None
    tempo_criacao: float | None = None
    aprendizagem: dict = field(default_factory=lambda: {
        "previsao": None, "interpretacao": None, "tentativas": 0,
        "interpretacao_correta": False, "feedback": "",
    })
    fingerprint_criacao: tuple[str, int, int, int] | None = None


class GerenciadorLaboratorios:
    """Travas: `_lock` protege só o registro (dicionários, índices e o arquivo de estado) e é sempre breve; `trava(uid)`
    serializa o que um aluno faz no próprio ambiente (criar, comandos, encerrar), sem bloquear os outros alunos.
    Ordem: a trava do aluno antes de `_lock`; nunca pedir a trava de um aluno segurando `_lock`."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._travas: dict[int, threading.RLock] = {}
        self._reservados: set[int] = set()
        # O CORE numera as sessões sem proteção contra pedidos simultâneos (/tmp/pycore.N já existe): só esse passo,
        # que é rápido, entra numa fila; montar e preparar a topologia correm em paralelo.
        self._criacao_core = threading.Lock()
        self._laboratorios: dict[int, Laboratorio] = {}
        self._capturas: dict[int, Captura] = {}
        self._execucoes: set[int] = set()
        # Tempo de montagem de cada ambiente (painel do teste de carga): (quando, laboratório, segundos).
        self.criacoes: deque = deque(maxlen=200)

    @staticmethod
    def _core():
        core = client.CoreGrpcClient()
        core.connect()
        return core

    @staticmethod
    def _nome_seguro(login: str) -> str:
        nome = re.sub(r"[^a-z0-9-]", "-", login.lower())
        return nome.strip("-") or "aluno"

    @staticmethod
    def _fingerprint_diretorio_sessao(sessao):
        """Prova local somente leitura; indisponibilidade nunca autoriza remoção."""
        diretorio = getattr(sessao, 'dir', None)
        if not diretorio:
            return None
        try:
            caminho = Path(diretorio).resolve(strict=True)
            if not caminho.is_dir():
                return None
            estado = caminho.stat()
            return (str(caminho), estado.st_dev, estado.st_ino, estado.st_ctime_ns)
        except (OSError, ValueError, TypeError, RuntimeError):
            return None

    @staticmethod
    def _aguardar_ssh(endereco: str, tentativas: int = 20) -> bool:
        for _ in range(tentativas):
            try:
                with socket.create_connection((endereco, 22), timeout=1):
                    return True
            except OSError:
                time.sleep(0.25)
        return False

    def _salvar_estado(self) -> None:
        ARQUIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
        temporario = ARQUIVO_ESTADO.with_suffix(".tmp")
        dados = [
            {
                "usuario_id": lab.usuario_id,
                "login": lab.login,
                "laboratorio_id": lab.laboratorio_id,
                "session_id": lab.session_id,
                "indice_rede": lab.indice_rede,
            }
            for lab in self._laboratorios.values()
        ]
        temporario.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporario.replace(ARQUIVO_ESTADO)

    def reconciliar_sessoes_anteriores(self) -> None:
        if not ARQUIVO_ESTADO.exists():
            return
        try:
            dados = json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
            core = self._core()
            for item in dados:
                try:
                    core.delete_session(int(item["session_id"]))
                    print(
                        f"Sessão anterior {item['session_id']} removida.",
                        flush=True,
                    )
                except Exception as erro:
                    print(f"Falha na reconciliação: {erro}", flush=True)
        finally:
            ARQUIVO_ESTADO.unlink(missing_ok=True)

    def trava(self, usuario_id: int) -> threading.RLock:
        with self._lock:
            return self._travas.setdefault(usuario_id, threading.RLock())

    def _indice_disponivel(self, usuario_id: int) -> int:
        preferido = usuario_id if 1 <= usuario_id <= 200 else None
        usados = {lab.indice_rede for lab in self._laboratorios.values()} | self._reservados
        if preferido and preferido not in usados:
            return preferido
        return next(indice for indice in range(1, 201) if indice not in usados)

    def criar(
        self,
        usuario_id: int,
        login: str,
        laboratorio_id: str = LABORATORIO_PADRAO,
    ) -> Laboratorio:
        with self.trava(usuario_id):
            existente = self.obter(usuario_id)
            if existente:
                existente.heartbeat = time.time()
                return existente

            laboratorio_id = obter_cenario(laboratorio_id).LABORATORIO_ID
            with self._lock:
                indice = self._indice_disponivel(usuario_id)
                self._reservados.add(indice)
            try:
                return self._criar(usuario_id, login, laboratorio_id, indice)
            finally:
                with self._lock:
                    self._reservados.discard(indice)

    def _criar(self, usuario_id, login, laboratorio_id, indice):
        """Monta a sessão no CORE fora de `_lock`: outros alunos seguem usando os ambientes deles enquanto isso."""
        inicio_criacao = time.time()
        prefixo = f"172.30.{indice}"
        enderecos = {1: f"{prefixo}.1", 2: f"{prefixo}.2"}
        core = self._core()
        with self._criacao_core:
            sessao = core.create_session()
        session_id = sessao.id
        nome = self._nome_seguro(login)

        fingerprint_criacao = None
        try:
            if laboratorio_id in COM_ROTEADOR and getattr(sessao, 'dir', None):
                fingerprint_criacao = self._fingerprint_diretorio_sessao(sessao)
            sessao.set_options({"controlnet": f"{prefixo}.0/24"})
            if laboratorio_id in COM_SETORES:
                nomes_didaticos = topologia_setores.construir(sessao, laboratorio_id, session_id=session_id, nome=nome,
                    imagem=topologia_setores.imagem(laboratorio_id, IMAGEM_GATEWAY),
                    Interface=Interface, NodeType=NodeType, Position=Position)
                enderecos = {node: f"{prefixo}.{node}" for node in nomes_didaticos}
            elif laboratorio_id in COM_ROTEADOR:
                nomes_didaticos = construir_gateway(sessao, session_id=session_id,
                    nome=nome, imagem=IMAGEM_GATEWAY, Interface=Interface, NodeType=NodeType, Position=Position,
                    chamados=laboratorio_id == 'configure-pelo-terminal')
                enderecos = {node: f"{prefixo}.{node}" for node in nomes_didaticos}
            else:
                docker1 = sessao.add_node(
                    1,
                    name=f"pl-s{session_id}-{nome}-docker1",
                    _type=NodeType.DOCKER,
                    image=IMAGEM,
                    position=Position(x=150, y=100),
                )
                docker2 = sessao.add_node(
                    2,
                    name=f"pl-s{session_id}-{nome}-docker2",
                    _type=NodeType.DOCKER,
                    image=IMAGEM,
                    position=Position(x=450, y=100),
                )
                switch = sessao.add_node(
                    3,
                    name=f"pl-s{session_id}-{nome}-switch1",
                    _type=NodeType.SWITCH,
                    position=Position(x=300, y=250),
                )
                sessao.add_link(
                    node1=docker1,
                    node2=switch,
                    iface1=Interface(
                        id=0, name="eth0", ip4="10.0.0.20", ip4_mask=24
                    ),
                    iface2=Interface(id=0, name="eth0"),
                )
                sessao.add_link(
                    node1=docker2,
                    node2=switch,
                    iface1=Interface(
                        id=0, name="eth0", ip4="10.0.0.21", ip4_mask=24
                    ),
                    iface2=Interface(id=1, name="eth1"),
                )

            sucesso, erros = core.start_session(sessao)
            if not sucesso:
                raise RuntimeError("; ".join(erros or []))

            if laboratorio_id not in COM_ROTEADOR:
                nomes_didaticos = {
                    1: "computador-1",
                    2: "computador-2",
                }

            comando_sshd = (
                "/usr/local/bin/iniciar-sshd "
                ">/tmp/sshd.log 2>&1 &"
            )

            for node_id, endereco in enderecos.items():
                codigo_nome, saida_nome = core.node_command(
                    session_id,
                    node_id,
                    f"hostname {nomes_didaticos[node_id]}",
                    wait=True,
                    shell=True,
                )
                if codigo_nome != 0:
                    raise RuntimeError(
                        "Não foi possível definir o nome "
                        f"didático do nó {node_id}: "
                        f"{saida_nome}"
                    )

                codigo, saida = core.node_command(
                    session_id,
                    node_id,
                    comando_sshd,
                    wait=True,
                    shell=True,
                )
                if codigo != 0 or not self._aguardar_ssh(endereco):
                    raise RuntimeError(
                        f"SSH indisponível no nó {node_id}: {saida}"
                    )

            if laboratorio_id in COM_SETORES:
                topologia_setores.preparar(core, session_id, laboratorio_id)
            elif laboratorio_id in COM_ROTEADOR:
                preparar_gateway(core, session_id,
                    chamados=laboratorio_id == 'configure-pelo-terminal')

            cenario = obter_cenario(laboratorio_id)
            iniciado_em = time.time()

            laboratorio = Laboratorio(
                usuario_id=usuario_id,
                login=login,
                laboratorio_id=laboratorio_id,
                session_id=session_id,
                indice_rede=indice,
                controlnet=f"{prefixo}.0/24",
                enderecos=enderecos,
                iniciado_em=iniciado_em,
                prazo=iniciado_em + cenario.TEMPO_LIMITE,
                tempo_extensao=cenario.TEMPO_EXTENSAO,
                max_extensoes=cenario.MAX_EXTENSOES,
            )
            laboratorio.tempo_criacao = round(time.time() - inicio_criacao, 1)
            with self._lock:
                self.criacoes.append((int(time.time()), laboratorio_id, laboratorio.tempo_criacao))
                self._laboratorios[usuario_id] = laboratorio
                self._salvar_estado()
            return laboratorio
        except Exception:
            if laboratorio_id not in COM_ROTEADOR:
                core.delete_session(session_id)
                raise
            removida = False
            try:
                if session_id in {s.id for s in core.get_sessions()}:
                    remota = core.get_session(session_id)
                    nos = remota.nodes.values() if isinstance(remota.nodes, dict) else remota.nodes
                    nomes = [no.name for no in nos]
                    prefixo_nome = f'pl-s{session_id}-{nome}-'
                    if nomes:
                        propria = all(n.startswith(prefixo_nome) for n in nomes)
                    else:
                        propria = bool(fingerprint_criacao) and (
                            self._fingerprint_diretorio_sessao(remota) == fingerprint_criacao)
                    if not propria:
                        raise RuntimeError('Propriedade da sessão não confirmada.')
                    core.delete_session(session_id)
                removida = session_id not in {s.id for s in core.get_sessions()}
            except Exception:
                pass
            if not removida:
                cenario = obter_cenario(laboratorio_id)
                agora = time.time()
                with self._lock:
                    self._laboratorios[usuario_id] = Laboratorio(
                        usuario_id=usuario_id, login=login, laboratorio_id=laboratorio_id,
                        session_id=session_id, indice_rede=indice, controlnet=f'{prefixo}.0/24',
                        enderecos=enderecos, iniciado_em=agora, prazo=agora+cenario.TEMPO_LIMITE,
                        tempo_extensao=cenario.TEMPO_EXTENSAO, max_extensoes=cenario.MAX_EXTENSOES,
                        preparacao_confirmada=False, fingerprint_criacao=fingerprint_criacao)
                    self._salvar_estado()
                raise RuntimeError('Preparação falhou e remoção está pendente; treino bloqueado. Consulte e encerre o ambiente.')
            raise
        finally:
            if laboratorio_id in COM_ROTEADOR:
                core.close()

    def obter(
        self, usuario_id: int, heartbeat: bool = True
    ) -> Laboratorio | None:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
            esgotado = bool(laboratorio and time.time() >= laboratorio.prazo)
            if laboratorio and heartbeat and not esgotado:
                laboratorio.heartbeat = time.time()
        if esgotado:
            self.encerrar(usuario_id, "prazo do laboratório esgotado")
            return None
        return laboratorio

    def dados_temporais(self, laboratorio: Laboratorio) -> dict:
        with self._lock:
            agora = time.time()
            return {
                "laboratorio_id": laboratorio.laboratorio_id,
                "iniciado_em": laboratorio.iniciado_em,
                "prazo": laboratorio.prazo,
                "agora": agora,
                "segundos_restantes": max(0, math.ceil(laboratorio.prazo - agora)),
                "tempo_extensao": laboratorio.tempo_extensao,
                "max_extensoes": laboratorio.max_extensoes,
                "extensoes_utilizadas": laboratorio.extensoes_utilizadas,
                "pode_estender": agora < laboratorio.prazo
                and laboratorio.extensoes_utilizadas < laboratorio.max_extensoes,
            }

    def estender(self, usuario_id: int) -> Laboratorio:
        with self.trava(usuario_id):
            laboratorio = self.obter(usuario_id, heartbeat=False)
            if not laboratorio:
                raise ValueError("Não existe laboratório ativo dentro do prazo.")
            if laboratorio.extensoes_utilizadas >= laboratorio.max_extensoes:
                raise ValueError("O limite de extensões deste laboratório foi atingido.")
            laboratorio.prazo += laboratorio.tempo_extensao
            laboratorio.extensoes_utilizadas += 1
            laboratorio.heartbeat = time.time()
            return laboratorio

    def executar(
        self,
        usuario_id: int,
        node_id: int,
        comando: str,
        timeout: int = 10,
    ) -> tuple[int, str]:
        laboratorio = self.obter(usuario_id)
        if not laboratorio:
            raise RuntimeError("O usuário não possui laboratório ativo.")
        if node_id not in laboratorio.enderecos:
            raise ValueError("Nó inválido.")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=laboratorio.enderecos[node_id],
                username="root",
                key_filename=CHAVE_SSH,
                look_for_keys=False,
                allow_agent=False,
                timeout=5,
                auth_timeout=5,
            )
            _, stdout, stderr = ssh.exec_command(comando, timeout=timeout)
            codigo = stdout.channel.recv_exit_status()
            saida = "\n".join(
                parte
                for parte in (
                    stdout.read().decode("utf-8", errors="replace").strip(),
                    stderr.read().decode("utf-8", errors="replace").strip(),
                )
                if parte
            )
            return codigo, saida
        finally:
            ssh.close()

    def executar_observado(self, usuario_id, node_id, comando, timeout=10):
        captura = None
        with self._lock:
            laboratorio = self.obter(usuario_id)
            if not laboratorio:
                raise ValueError("O usuário não possui laboratório ativo.")
            if usuario_id in self._execucoes:
                raise ValueError("Aguarde o término do comando anterior.")
            if node_id not in laboratorio.enderecos:
                raise ValueError("Nó inválido.")
            partes = shlex.split(comando)
            cenario = obter_cenario(laboratorio.laboratorio_id)
            if partes and partes[0] == "ping" and getattr(cenario, "PERGUNTAS", None):
                if not laboratorio.aprendizagem["previsao"]:
                    raise ValueError("Registre sua previsão antes de executar o ping.")
            perfil = getattr(cenario, "PERFIL_CAPTURA", None)
            if perfil == "arp_icmp" and partes and partes[0] == "ping":
                captura = Captura(laboratorio.session_id, node_id)
                self._capturas[usuario_id] = captura
            self._execucoes.add(usuario_id)
        erro_captura = None
        try:
            if captura:
                core = None
                try:
                    core = self._core()
                    captura.iniciar(core)
                except Exception:
                    erro_captura = "Captura indisponível; o comando continua disponível."
                finally:
                    if core:
                        core.close()
            with self._lock:
                if self._laboratorios.get(usuario_id) is not laboratorio:
                    raise ValueError("O laboratório foi encerrado.")
            codigo, saida = self.executar(usuario_id, node_id, comando, timeout)
            bastidores = captura.finalizar(erro_captura) if captura else None
            with self._lock:
                if self._laboratorios.get(usuario_id) is laboratorio and bastidores:
                    laboratorio.bastidores = bastidores
            return codigo, saida, bastidores
        finally:
            if captura:
                captura.finalizar(erro_captura)
            with self._lock:
                self._capturas.pop(usuario_id, None)
                self._execucoes.discard(usuario_id)

    @contextmanager
    def observar(self, usuario_id: int, node_id: int):
        """Captura tshark limitada na interface do nó enquanto o bloco roda (Labs 2 a 10).

        Entrega um dicionário que, ao sair do bloco, recebe o resultado. Falha na captura nunca impede o comando.
        """
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
            if not laboratorio or usuario_id in self._capturas:
                captura = None
            else:
                captura = Captura(laboratorio.session_id, node_id, "rede")
                self._capturas[usuario_id] = captura
        resultado = {}
        if not captura:
            yield resultado
            return
        erro = None
        try:
            core = None
            try:
                core = self._core()
                captura.iniciar(core)
            except Exception:
                erro = "Captura indisponível; o comando continua disponível."
            finally:
                if core:
                    core.close()
            yield resultado
        finally:
            resultado.update(captura.finalizar(erro))
            with self._lock:
                if self._capturas.get(usuario_id) is captura:
                    self._capturas.pop(usuario_id, None)

    def registrar_comando(
        self,
        usuario_id: int,
        node_id: int,
        resultado: dict,
    ) -> dict:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)

            if not laboratorio:
                raise RuntimeError(
                    "O usuário não possui laboratório ativo."
                )

            laboratorio.ultimos_comandos[node_id] = resultado
            laboratorio.total_comandos += 1
            laboratorio.heartbeat = time.time()

            cenario = obter_cenario(laboratorio.laboratorio_id)
            novas_evidencias = cenario.detectar_evidencias(
                node_id=node_id,
                comando=resultado.get("comando", ""),
                codigo=resultado.get("codigo", 1),
                saida=resultado.get("saida", ""),
            )

            etapas = getattr(cenario, "ETAPAS", ())
            proxima = next(
                (etapa["id"] for etapa in etapas
                 if etapa["id"] not in laboratorio.evidencias),
                None,
            )
            if proxima:
                laboratorio.evidencias.update(novas_evidencias & {proxima})

            return self._estado_laboratorio(laboratorio)

    def estado_missao(
        self,
        usuario_id: int,
        heartbeat: bool = True,
    ) -> dict | None:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)

            if not laboratorio:
                return None

            if heartbeat:
                laboratorio.heartbeat = time.time()
            cenario = obter_cenario(laboratorio.laboratorio_id)

            return self._estado_laboratorio(laboratorio)

    def _estado_laboratorio(self, laboratorio):
        cenario = obter_cenario(laboratorio.laboratorio_id)
        estado = cenario.montar_estado(laboratorio.evidencias)
        perguntas = getattr(cenario, "PERGUNTAS", None)
        if perguntas:
            estado["pratica_concluida"] = estado["concluido"]
            estado["aprendizagem"] = {
                **laboratorio.aprendizagem, "perguntas": perguntas,
                "pode_prever": {"identificacao", "enderecamento"}
                <= laboratorio.evidencias,
                "pode_interpretar": "conectividade" in laboratorio.evidencias,
            }
            estado["concluido"] = bool(
                estado["pratica_concluida"] and laboratorio.aprendizagem["previsao"]
                and laboratorio.aprendizagem["interpretacao_correta"]
            )
        return estado

    def responder_aprendizagem(self, usuario_id, fase, resposta):
        with self._lock:
            lab = self.obter(usuario_id)
            if not lab:
                raise ValueError("Não existe laboratório ativo dentro do prazo.")
            perguntas = getattr(obter_cenario(lab.laboratorio_id), "PERGUNTAS", {})
            if fase not in perguntas or resposta not in {o["id"] for o in perguntas[fase]["opcoes"]}:
                raise ValueError("Selecione uma resposta válida.")
            aprendizagem = lab.aprendizagem
            if fase == "previsao":
                if not {"identificacao", "enderecamento"} <= lab.evidencias:
                    raise ValueError("Conclua a identificação e a consulta IPv4 antes de registrar a previsão.")
                if aprendizagem["previsao"]:
                    raise ValueError("Sua previsão já foi registrada para esta sessão.")
                aprendizagem["previsao"] = resposta
                aprendizagem["feedback"] = "Hipótese registrada. Execute o ping e compare o resultado com sua previsão."
            else:
                if not aprendizagem["previsao"] or "conectividade" not in lab.evidencias:
                    raise ValueError("Registre a previsão e conclua o teste de conectividade antes de interpretar.")
                if aprendizagem["interpretacao_correta"]:
                    return self._estado_laboratorio(lab)
                aprendizagem["tentativas"] += 1
                aprendizagem["interpretacao"] = resposta
                aprendizagem["interpretacao_correta"] = resposta == "alcance"
                aprendizagem["feedback"] = (
                    "Isso! Houve comunicação de ida e volta. O ping não comprova todos os serviços nem acesso à internet."
                    if resposta == "alcance" else
                    "Compare os pedidos e as respostas. O que uma resposta recebida demonstra?"
                    if aprendizagem["tentativas"] == 1 else
                    "O Echo Reply volta do destino ao remetente. Pense no alcance entre esses dois computadores, sem generalizar para outros serviços."
                )
            return self._estado_laboratorio(lab)

    def ultimo_comando(self, usuario_id: int, node_id: int):
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
            if not laboratorio:
                return None
            laboratorio.heartbeat = time.time()
            return laboratorio.ultimos_comandos.get(node_id)

    def preparar_tutoria(
        self,
        usuario_id: int,
        etapa_id: str,
        pergunta: str,
    ) -> dict:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
            if not laboratorio:
                raise RuntimeError("O usuário não possui laboratório ativo.")
            laboratorio.heartbeat = time.time()
            return avaliar_interacao(
                etapa_id,
                pergunta,
                laboratorio.historico_tutor,
            )

    def registrar_tutoria(
        self,
        usuario_id: int,
        interacao: dict,
        resposta: str,
    ) -> None:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
            if not laboratorio:
                return
            laboratorio.historico_tutor.append({
                "etapa_id": interacao["etapa_id"],
                "pergunta": interacao["pergunta"],
                "resposta": resposta,
                "nivel": interacao["nivel"],
                "classificacao": interacao["classificacao"],
            })
            laboratorio.historico_tutor = laboratorio.historico_tutor[-30:]
            laboratorio.heartbeat = time.time()

    def encerrar_confirmado(self, usuario_id: int, session_id: int,
                            motivo: str = "missão concluída") -> bool:
        """Lab2: só descarta o registro após confirmar a ausência no CORE.

        O encerramento legado permanece inalterado para os demais cenários.
        """
        if self._lock._is_owned():
            # Chamado de dentro do registro (caminho legado do Lab 1): já está serializado e não pode pedir a trava do aluno.
            return self._encerrar_confirmado(usuario_id, session_id, motivo)
        with self.trava(usuario_id):
            return self._encerrar_confirmado(usuario_id, session_id, motivo)

    def _encerrar_confirmado(self, usuario_id, session_id, motivo):
        """Remove a sessão no CORE fora de `_lock`; a trava do aluno impede que o ambiente dele mude no meio."""
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
        if not laboratorio or laboratorio.session_id != session_id:
            return False
        if laboratorio.laboratorio_id not in ('primeira-lan', *COM_ROTEADOR):
            raise ValueError('Encerramento confirmado não habilitado para este cenário.')
        core = self._core()
        try:
            if session_id in {s.id for s in core.get_sessions()}:
                remota = core.get_session(session_id)
                nos = remota.nodes.values() if isinstance(remota.nodes, dict) else remota.nodes
                nomes = [no.name for no in nos]
                prefixo = f'pl-s{session_id}-{self._nome_seguro(laboratorio.login)}-'
                if nomes:
                    propria = all(n.startswith(prefixo) for n in nomes)
                else:
                    fingerprint = getattr(laboratorio, 'fingerprint_criacao', None)
                    propria = (
                        laboratorio.laboratorio_id in COM_ROTEADOR
                        and getattr(laboratorio, 'preparacao_confirmada', None) is False
                        and bool(fingerprint)
                        and self._fingerprint_diretorio_sessao(remota) == fingerprint)
                if not propria:
                    raise RuntimeError('Propriedade dos nós não confirmada; remoção cancelada.')
                if not core.delete_session(session_id):
                    raise RuntimeError('CORE não confirmou a solicitação de remoção.')
                if session_id in {s.id for s in core.get_sessions()}:
                    raise RuntimeError('A sessão ainda está presente no CORE.')
        finally:
            core.close()
        with self._lock:
            captura = self._capturas.get(usuario_id)
            if captura:
                captura.cancelar()
            self._laboratorios.pop(usuario_id)
            try:
                self._salvar_estado()
            except Exception:
                self._laboratorios[usuario_id] = laboratorio
                raise
        print(f'Sessão {session_id} removida e confirmada: {motivo}', flush=True)
        return True

    def encerrar(self, usuario_id: int, motivo: str = "solicitação") -> bool:
        with self._lock:
            laboratorio = self._laboratorios.get(usuario_id)
        if laboratorio and laboratorio.laboratorio_id in COM_ROTEADOR:
            return self.encerrar_confirmado(usuario_id, laboratorio.session_id, motivo)
        with self._lock:
            laboratorio = self._laboratorios.pop(usuario_id, None)
            if not laboratorio:
                return False
            captura = self._capturas.get(usuario_id)
            if captura:
                captura.cancelar()
            self._salvar_estado()
        try:
            self._core().delete_session(laboratorio.session_id)
            print(
                f"Sessão {laboratorio.session_id} de {laboratorio.login} "
                f"removida: {motivo}",
                flush=True,
            )
        except Exception as erro:
            print(
                f"Falha ao remover sessão {laboratorio.session_id}: {erro}",
                flush=True,
            )
        return True

    def encerrar_expirados(self, timeout: int) -> list[int]:
        with self._lock:
            agora = time.time()
            expirados = [
                (usuario_id, "prazo do laboratório esgotado"
                 if agora >= lab.prazo else f"inatividade por {timeout} segundos")
                for usuario_id, lab in self._laboratorios.items()
                if agora >= lab.prazo or agora - lab.heartbeat >= timeout
            ]
        removidos = []
        for usuario_id, motivo in expirados:
            # Cada remoção com a trava do aluno: confere de novo, porque ele pode ter agido enquanto isso.
            with self.trava(usuario_id):
                with self._lock:
                    lab = self._laboratorios.get(usuario_id)
                    agora = time.time()
                    if not lab or not (agora >= lab.prazo or agora - lab.heartbeat >= timeout):
                        continue
                try:
                    if self.encerrar(usuario_id, motivo):
                        removidos.append(usuario_id)
                except Exception:
                    if lab.laboratorio_id not in COM_ROTEADOR:
                        raise
                    print(f'Limpeza do Lab3 pendente para usuário {usuario_id}; registro preservado.', flush=True)
        return removidos

    def encerrar_todos(self, motivo: str = "parada do serviço") -> None:
        with self._lock:
            usuarios = list(self._laboratorios)
        for usuario_id in usuarios:
            lab = self._laboratorios.get(usuario_id)
            try:
                self.encerrar(usuario_id, motivo)
            except Exception:
                if not lab or lab.laboratorio_id not in COM_ROTEADOR:
                    raise
                print(f'Limpeza do Lab3 pendente na parada para usuário {usuario_id}; registro preservado.', flush=True)

    def listar(self) -> list[Laboratorio]:
        with self._lock:
            return list(self._laboratorios.values())
