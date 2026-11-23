import re
import sqlite3
import sys
import unicodedata
from pathlib import Path


BANCO_PADRAO = Path(
    "/opt/packetlab/data/rag/indice/pinglevel_rag.db"
)

PALAVRAS_IGNORADAS = {
    "a", "ao", "aos", "as", "como", "com", "da", "das", "de",
    "do", "dos", "e", "é", "em", "eu", "me", "meu", "minha",
    "na", "nas", "não", "no", "nos", "o", "os", "para", "por",
    "porque", "que", "qual", "se", "sem", "um", "uma",
}

SINONIMOS = {
    "ip": ["ipv4", "endereco", "interface"],
    "ipv4": ["ip", "endereco"],
    "rota": ["route", "roteamento", "gateway"],
    "rotas": ["route", "roteamento", "gateway"],
    "roteamento": ["rota", "route", "gateway"],
    "ping": ["icmp", "conectividade", "alcance"],
    "conectividade": ["ping", "icmp", "comunicacao"],
    "endereco": ["ip", "ipv4"],
    "interface": ["ip", "placa", "dispositivo"],
    "ssh": ["acesso", "remoto", "seguro"],
    "traceroute": ["rota", "saltos", "caminho"],
    "vlan": ["virtual", "lan", "segmentacao"],
    "dhcp": ["endereco", "automatico", "lease"],
    "dns": ["nome", "dominio", "resolucao"],
}


def sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)

    return "".join(
        caractere
        for caractere in normalizado
        if not unicodedata.combining(caractere)
    )


def extrair_termos(pergunta: str) -> list[str]:
    texto = sem_acentos(pergunta.lower())

    palavras = re.findall(r"[a-z0-9][a-z0-9._-]*", texto)

    termos = []
    vistos = set()

    for palavra in palavras:
        if len(palavra) < 2:
            continue

        if palavra in PALAVRAS_IGNORADAS:
            continue

        if palavra not in vistos:
            termos.append(palavra)
            vistos.add(palavra)

    return termos


def montar_consulta_fts(pergunta: str) -> str:
    termos_principais = extrair_termos(pergunta)

    if not termos_principais:
        raise ValueError(
            "A pergunta não possui termos suficientes para a busca."
        )

    grupos = []

    for termo in termos_principais:
        relacionados = [termo]

        for sinonimo in SINONIMOS.get(termo, []):
            sinonimo = sem_acentos(sinonimo.lower())

            if sinonimo not in relacionados:
                relacionados.append(sinonimo)

        grupo = " OR ".join(
            f'"{item}"'
            for item in relacionados
        )

        grupos.append(f"({grupo})")

    # OR entre os grupos permite recuperar material mesmo quando
    # nem todas as palavras da pergunta aparecem literalmente.
    return " OR ".join(grupos)


def recortar_contexto(
    pergunta: str,
    conteudo: str,
    tamanho: int = 620,
) -> str:
    pergunta_normalizada = sem_acentos(pergunta.lower())
    conteudo_minusculo = conteudo.lower()

    ancora = None

    regras = [
        (
            "ip" in pergunta_normalizada
            and any(
                termo in pergunta_normalizada
                for termo in (
                "descobrir",
                "descubro",
                "descobre",
                "identificar",
                "saber",
                "ver",
                "visualizar",
                "mostrar",
            )
            ),
            ["ip addr show", "ip -br addr", "ifconfig"],
        ),
        (
            "ping" in pergunta_normalizada,
            ["ping -c", "2.10 ping", "descricao 2.10"],
        ),
        (
            any(
                termo in pergunta_normalizada
                for termo in ("rota", "rotas", "roteamento")
            ),
            ["ip route show", "tabela de roteamento", "route"],
        ),
        (
            "ssh" in pergunta_normalizada,
            ["ssh (secure shell)", "2.15 ssh", "acesso remoto seguro"],
        ),
        (
            any(
                termo in pergunta_normalizada
                for termo in ("salto", "saltos", "caminho")
            ),
            ["traceroute", "tracepath", "salto (hop)"],
        ),
    ]

    for regra_ativa, possibilidades in regras:
        if not regra_ativa:
            continue

        for possibilidade in possibilidades:
            posicao = conteudo_minusculo.find(
                possibilidade.lower()
            )

            if posicao != -1:
                ancora = posicao
                break

        if ancora is not None:
            break

    if ancora is None:
        ancora = 0

    # Para perguntas sobre como visualizar o endereço, retorna somente
    # o bloco lógico do comando e evita avançar para os exemplos de ARP.
    consulta_endereco = (
        "ip" in pergunta_normalizada
        and any(
            termo in pergunta_normalizada
            for termo in (
                "descobrir",
                "descubro",
                "descobre",
                "identificar",
                "saber",
                "ver",
                "visualizar",
                "mostrar",
            )
        )
        and "ip addr show" in conteudo_minusculo
    )

    if consulta_endereco:
        linhas = conteudo.splitlines()
        indice_ancora = None

        for indice, linha in enumerate(linhas):
            if "ip addr show" in linha.lower():
                indice_ancora = indice
                break

        if indice_ancora is not None:
            inicio_linha = max(0, indice_ancora - 1)
            fim_linha = min(
                len(linhas),
                indice_ancora + 3,
            )

            trecho = "\n".join(
                linhas[inicio_linha:fim_linha]
            ).strip()

            if inicio_linha > 0:
                trecho = "[...]\n" + trecho

            if fim_linha < len(linhas):
                trecho = trecho + "\n[...]"

            return trecho

    inicio = max(0, ancora - 180)
    fim = min(len(conteudo), inicio + tamanho)

    # Tenta iniciar e terminar em uma quebra de linha.
    if inicio > 0:
        proxima_linha = conteudo.find("\n", inicio)

        if proxima_linha != -1 and proxima_linha < ancora:
            inicio = proxima_linha + 1

    if fim < len(conteudo):
        ultima_linha = conteudo.rfind("\n", inicio, fim)

        if ultima_linha > ancora:
            fim = ultima_linha

    trecho = conteudo[inicio:fim].strip()

    if inicio > 0:
        trecho = "[...]\n" + trecho

    if fim < len(conteudo):
        trecho = trecho + "\n[...]"

    return trecho


def calcular_bonus_intencao(
    pergunta: str,
    resultado: dict,
) -> float:
    pergunta_normalizada = sem_acentos(pergunta.lower())
    conteudo = sem_acentos(
        (
            resultado["secao"]
            + "\n"
            + resultado["conteudo"]
        ).lower()
    )

    bonus = 0.0

    # Intenção: visualizar endereços e interfaces.
    if (
        "ip" in pergunta_normalizada
        and any(
            termo in pergunta_normalizada
            for termo in (
                "descobrir",
                "descubro",
                "descobre",
                "identificar",
                "saber",
                "ver",
                "visualizar",
                "mostrar",
            )
        )
    ):
        if "ip addr show" in conteudo:
            bonus += 22.0
        elif "ip addr" in conteudo:
            bonus += 12.0

        if "ifconfig" in conteudo:
            bonus += 7.0

        if "configurar um endereco" in conteudo:
            bonus -= 4.0

    # Intenção: limitar ou interromper o ping.
    if (
        "ping" in pergunta_normalizada
        and any(
            termo in pergunta_normalizada
            for termo in ("termina", "parar", "continuo", "quantidade")
        )
    ):
        if "ping -c" in conteudo:
            bonus += 24.0

        if "quantidade" in conteudo:
            bonus += 8.0

        if "continu" in conteudo:
            bonus += 6.0

    # Intenção: consultar a tabela de roteamento.
    if (
        any(
            termo in pergunta_normalizada
            for termo in ("rota", "rotas", "roteamento")
        )
        and any(
            termo in pergunta_normalizada
            for termo in ("ver", "visualizar", "mostrar", "tabela")
        )
    ):
        if "ip route show" in conteudo:
            bonus += 24.0

        if "tabela de roteamento" in conteudo:
            bonus += 14.0

        if "route" in conteudo:
            bonus += 6.0

    # Intenção: compreender ou utilizar SSH.
    if "ssh" in pergunta_normalizada:
        if "secure shell" in conteudo:
            bonus += 16.0

        if "acesso remoto seguro" in conteudo:
            bonus += 14.0

        if "ssh " in conteudo:
            bonus += 8.0

    # Intenção: descobrir caminho e saltos.
    if any(
        termo in pergunta_normalizada
        for termo in ("salto", "saltos", "caminho")
    ):
        if "traceroute" in conteudo:
            bonus += 24.0

        if "tracepath" in conteudo:
            bonus += 20.0

        if "cada salto" in conteudo or "salto (hop)" in conteudo:
            bonus += 12.0

        if "dns" in conteudo and "traceroute" not in conteudo:
            bonus -= 8.0

    return bonus


def buscar_contexto(
    pergunta: str,
    limite: int = 5,
    banco: Path = BANCO_PADRAO,
) -> list[dict]:
    if not banco.exists():
        raise FileNotFoundError(
            f"Índice RAG não encontrado: {banco}"
        )

    consulta = montar_consulta_fts(pergunta)

    conexao = sqlite3.connect(banco)
    conexao.row_factory = sqlite3.Row

    try:
        linhas = conexao.execute(
            """
            SELECT
                c.id,
                c.livro,
                c.arquivo,
                c.pagina_pdf,
                c.secao,
                c.ordem_pagina,
                c.conteudo,
                bm25(chunks_fts) AS pontuacao
            FROM chunks_fts
            JOIN chunks AS c
              ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts)
            LIMIT 30
            """,
            (consulta,),
        ).fetchall()
    finally:
        conexao.close()

    candidatos = []

    for linha in linhas:
        resultado = {
            "id": linha["id"],
            "livro": linha["livro"],
            "arquivo": linha["arquivo"],
            "pagina_pdf": linha["pagina_pdf"],
            "secao": linha["secao"],
            "ordem_pagina": linha["ordem_pagina"],
            "conteudo": linha["conteudo"],
            "pontuacao": linha["pontuacao"],
        }

        resultado["conteudo_contextual"] = recortar_contexto(
            pergunta,
            resultado.get(
                "conteudo_contextual",
                resultado["conteudo"],
            ),
        )

        relevancia_bm25 = -float(linha["pontuacao"])
        bonus = calcular_bonus_intencao(pergunta, resultado)

        resultado["bonus_intencao"] = bonus
        resultado["relevancia"] = relevancia_bm25 + bonus
        candidatos.append(resultado)

    candidatos.sort(
        key=lambda item: item["relevancia"],
        reverse=True,
    )

    # Evita enviar vários chunks da mesma página ao modelo.
    resultados = []
    paginas_utilizadas = set()

    for candidato in candidatos:
        identificador_pagina = (
            candidato["arquivo"],
            candidato["pagina_pdf"],
        )

        if identificador_pagina in paginas_utilizadas:
            continue

        paginas_utilizadas.add(identificador_pagina)
        resultados.append(candidato)

        if len(resultados) >= limite:
            break

    return resultados


def ocultar_exemplos_nivel1(conteudo: str) -> str:
    linhas_filtradas = []

    for linha in conteudo.splitlines():
        linha_limpa = linha.strip()

        # Remove linhas que entregam sintaxe pronta dos livros.
        if re.search(
            r"\bExemplo\s+\d+(?:\.\d+)*",
            linha_limpa,
            flags=re.IGNORECASE,
        ):
            continue

        # Remove blocos explicitamente identificados como comandos.
        if linha_limpa.lower() in {
            "comando:",
            "comandos:",
            "exemplo:",
            "exemplos:",
        }:
            continue

        linhas_filtradas.append(linha)

    return "\n".join(linhas_filtradas).strip()


def formatar_contexto(
    resultados: list[dict],
    ocultar_exemplos: bool = False,
) -> str:
    blocos = []

    for numero, resultado in enumerate(resultados, start=1):
        conteudo = resultado.get(
            "conteudo_contextual",
            resultado["conteudo"],
        )

        if ocultar_exemplos:
            conteudo = ocultar_exemplos_nivel1(conteudo)

        blocos.append(
            "\n".join(
                [
                    f"[TRECHO {numero}]",
                    f"Livro: {resultado['livro']}",
                    f"Página do PDF: {resultado['pagina_pdf']}",
                    f"Seção: {resultado['secao']}",
                    "Conteúdo:",
                    conteudo,
                ]
            )
        )

    return "\n\n".join(blocos)


def mostrar_resultados(
    pergunta: str,
    resultados: list[dict],
) -> None:
    print(f"Pergunta: {pergunta}")
    print(f"Resultados encontrados: {len(resultados)}")

    if not resultados:
        print("\nNenhum trecho relevante foi localizado.")
        return

    for numero, resultado in enumerate(resultados, start=1):
        conteudo_resumido = re.sub(
            r"\s+",
            " ",
            resultado.get(
                "conteudo_contextual",
                resultado["conteudo"],
            ),
        ).strip()

        if len(conteudo_resumido) > 600:
            conteudo_resumido = conteudo_resumido[:600] + "..."

        print()
        print("=" * 72)
        print(f"RESULTADO {numero}")
        print(f"Livro: {resultado['livro']}")
        print(f"Página do PDF: {resultado['pagina_pdf']}")
        print(f"Seção detectada: {resultado['secao']}")
        print(f"Pontuação BM25: {resultado['pontuacao']:.4f}")
        print("-" * 72)
        print(conteudo_resumido)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Uso: recuperador.py "pergunta do aluno"'
        )

    pergunta = " ".join(sys.argv[1:])
    resultados = buscar_contexto(pergunta)
    mostrar_resultados(pergunta, resultados)


if __name__ == "__main__":
    main()
