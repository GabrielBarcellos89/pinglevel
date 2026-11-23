#!/usr/bin/env bash
# Prepara o ambiente de testes (fora do Git). Idempotente.
# As ferramentas ficam uma única vez em /opt/packetlab/.qa (venv de testes, Chromium, jsdom); uma cópia
# de trabalho (git worktree) recebe links para elas e para o node_modules de produção.
# Não altera o venv de produção, o package.json nem pacotes do sistema.
set -euo pipefail

RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
PRODUCAO=/opt/packetlab
QA=$PRODUCAO/.qa
NODE_BIN=/home/gabriel/.nvm/versions/node/v24.20.0/bin

mkdir -p "$QA/tmp" "$QA/browsers"

# Venv de testes com pytest e Playwright. Um .pth expõe os pacotes do venv de
# produção (CORE, paramiko, anthropic) somente para leitura.
if [ ! -x "$QA/venv/bin/python" ]; then
    python3 -m venv "$QA/venv"
fi
"$QA/venv/bin/pip" install -q --upgrade pip
"$QA/venv/bin/pip" install -q pytest playwright
SITE=$("$QA/venv/bin/python" -c 'import site; print(site.getsitepackages()[0])')
# addsitedir processa também os .pth do venv de produção (que apontam para o venv do CORE).
echo "import site; site.addsitedir('$PRODUCAO/venv/lib/python3.12/site-packages')" > "$SITE/pinglevel-producao.pth"

PLAYWRIGHT_BROWSERS_PATH="$QA/browsers" "$QA/venv/bin/playwright" install chromium

# jsdom para o teste de interface da aula de IPv4, no caminho que ele espera:
# $TMPDIR/retomada-ipv4-frontend/dom-test/node_modules/jsdom.
DOM="$QA/tmp/retomada-ipv4-frontend/dom-test"
mkdir -p "$DOM"
if [ ! -d "$DOM/node_modules/jsdom" ]; then
    [ -f "$DOM/package.json" ] || echo '{"private":true}' > "$DOM/package.json"
    (cd "$DOM" && PATH="$NODE_BIN:$PATH" npm install --silent --no-audit --no-fund jsdom)
fi

# Cópia de trabalho: build, capturas e logs ficam nela; ferramentas e dependências são as de produção.
if [ "$RAIZ" != "$PRODUCAO" ]; then
    mkdir -p "$RAIZ/.qa"
    for item in venv browsers tmp; do ln -sfn "$QA/$item" "$RAIZ/.qa/$item"; done
    [ -e "$RAIZ/frontend/node_modules" ] || ln -s "$PRODUCAO/frontend/node_modules" "$RAIZ/frontend/node_modules"
fi

echo "Ambiente de testes pronto em $RAIZ/.qa"
