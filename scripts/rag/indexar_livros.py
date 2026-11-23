import hashlib
import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader


DIRETORIO_FONTES = Path("/opt/packetlab/data/rag/fontes")
DIRETORIO_INDICE = Path("/opt/packetlab/data/rag/indice")
BANCO_FINAL = DIRETORIO_INDICE / "pinglevel_rag.db"
BANCO_TEMPORARIO = DIRETORIO_INDICE / "pinglevel_rag.tmp.db"

TAMANHO_ALVO = 1200
SOBREPOSICAO = 200

LIVROS = {
    "linux_utilitarios_de_redes.pdf": {
        "titulo": "Linux: Utilitários de Redes",
        "autor": "Eduardo Maroñas Monks",
    },
    "redes_para_Iniciantes.pdf": {
        "titulo": "Redes para Iniciantes",
        "autor": "Eduardo Maroñas Monks",
    },
}


def calcular_checksum(caminho: Path) -> str:
    resumo = hashlib.sha256()

    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)

    return resumo.hexdigest()


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""

    # Une palavras quebradas no final das linhas do PDF.
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)

    # Preserva separações de parágrafos.
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


def identificar_secao(texto: str, pagina: int) -> str:
    linhas = [
        linha.strip()
        for linha in texto.splitlines()
        if linha.strip()
    ]

    for linha in linhas[:8]:
        if len(linha) > 100:
            continue

        if re.match(r"^\d+(\.\d+)*\s+\S+", linha):
            return linha

        if (
            4 <= len(linha) <= 80
            and not linha.endswith((".", ",", ";", ":"))
            and len(linha.split()) <= 10
        ):
            return linha

    return f"Página {pagina}"


def criar_chunks(texto: str) -> list[str]:
    if not texto:
        return []

    paragrafos = [
        paragrafo.strip()
        for paragrafo in re.split(r"\n\s*\n", texto)
        if paragrafo.strip()
    ]

    chunks = []
    atual = ""

    for paragrafo in paragrafos:
        candidato = (
            f"{atual}\n\n{paragrafo}".strip()
            if atual
            else paragrafo
        )

        if len(candidato) <= TAMANHO_ALVO:
            atual = candidato
            continue

        if atual:
            chunks.append(atual)

        if len(paragrafo) <= TAMANHO_ALVO:
            atual = paragrafo
            continue

        inicio = 0

        while inicio < len(paragrafo):
            fim = inicio + TAMANHO_ALVO
            trecho = paragrafo[inicio:fim].strip()

            if trecho:
                chunks.append(trecho)

            inicio += TAMANHO_ALVO - SOBREPOSICAO

        atual = ""

    if atual:
        chunks.append(atual)

    return chunks


def preparar_banco(conexao: sqlite3.Connection) -> None:
    conexao.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE documentos (
            id INTEGER PRIMARY KEY,
            arquivo TEXT NOT NULL UNIQUE,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            paginas INTEGER NOT NULL,
            checksum TEXT NOT NULL
        );

        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            documento_id INTEGER NOT NULL,
            livro TEXT NOT NULL,
            arquivo TEXT NOT NULL,
            pagina_pdf INTEGER NOT NULL,
            secao TEXT NOT NULL,
            ordem_pagina INTEGER NOT NULL,
            conteudo TEXT NOT NULL,
            FOREIGN KEY(documento_id) REFERENCES documentos(id)
        );

        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            conteudo,
            content='chunks',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE INDEX idx_chunks_documento
        ON chunks(documento_id);

        CREATE INDEX idx_chunks_pagina
        ON chunks(arquivo, pagina_pdf);
        """
    )


def indexar_livro(
    conexao: sqlite3.Connection,
    caminho: Path,
) -> tuple[int, int]:
    metadados = LIVROS.get(
        caminho.name,
        {
            "titulo": caminho.stem.replace("_", " ").title(),
            "autor": "Autor não informado",
        },
    )

    leitor = PdfReader(str(caminho))
    checksum = calcular_checksum(caminho)

    cursor = conexao.execute(
        """
        INSERT INTO documentos (
            arquivo,
            titulo,
            autor,
            paginas,
            checksum
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            caminho.name,
            metadados["titulo"],
            metadados["autor"],
            len(leitor.pages),
            checksum,
        ),
    )

    documento_id = cursor.lastrowid
    total_chunks = 0
    paginas_com_texto = 0

    for numero, pagina in enumerate(leitor.pages, start=1):
        texto = normalizar_texto(pagina.extract_text() or "")

        if not texto:
            continue

        paginas_com_texto += 1
        secao = identificar_secao(texto, numero)
        chunks = criar_chunks(texto)

        for ordem, chunk in enumerate(chunks, start=1):
            conexao.execute(
                """
                INSERT INTO chunks (
                    documento_id,
                    livro,
                    arquivo,
                    pagina_pdf,
                    secao,
                    ordem_pagina,
                    conteudo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    documento_id,
                    metadados["titulo"],
                    caminho.name,
                    numero,
                    secao,
                    ordem,
                    chunk,
                ),
            )

            total_chunks += 1

    return paginas_com_texto, total_chunks


def main() -> None:
    DIRETORIO_INDICE.mkdir(parents=True, exist_ok=True)

    livros = sorted(DIRETORIO_FONTES.glob("*.pdf"))

    if not livros:
        raise SystemExit(
            f"Nenhum PDF encontrado em {DIRETORIO_FONTES}"
        )

    if BANCO_TEMPORARIO.exists():
        BANCO_TEMPORARIO.unlink()

    conexao = sqlite3.connect(BANCO_TEMPORARIO)

    try:
        preparar_banco(conexao)

        print("Iniciando indexação dos livros do PingLevel...\n")

        for caminho in livros:
            paginas, chunks = indexar_livro(conexao, caminho)

            print(f"Livro: {caminho.name}")
            print(f"  Páginas com texto: {paginas}")
            print(f"  Trechos criados: {chunks}")
            print()

        conexao.execute(
            "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')"
        )
        conexao.commit()

        total_documentos = conexao.execute(
            "SELECT COUNT(*) FROM documentos"
        ).fetchone()[0]

        total_chunks = conexao.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]

    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()

    BANCO_TEMPORARIO.replace(BANCO_FINAL)

    print("Indexação concluída com sucesso!")
    print(f"Documentos: {total_documentos}")
    print(f"Trechos: {total_chunks}")
    print(f"Banco: {BANCO_FINAL}")


if __name__ == "__main__":
    main()
