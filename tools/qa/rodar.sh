#!/usr/bin/env bash
# Roda todas as suítes de teste do PingLevel e gera um build candidato em .qa/dist.
# Uso: tools/qa/rodar.sh [--rapido]   (--rapido pula navegador e capturas)
# Não publica nada, não usa frontend/dist e não toca no CORE, no banco ou nos serviços.
set -uo pipefail

RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
QA=$RAIZ/.qa
NODE_BIN=/home/gabriel/.nvm/versions/node/v24.20.0/bin
RAPIDO=0; [ "${1:-}" = "--rapido" ] && RAPIDO=1

[ -x "$QA/venv/bin/python" ] || { echo "Ambiente ausente: rode tools/qa/preparar.sh"; exit 2; }
export TMPDIR=$QA/tmp PYTHONDONTWRITEBYTECODE=1 PATH=$NODE_BIN:$PATH PLAYWRIGHT_BROWSERS_PATH=$QA/browsers
PY=$QA/venv/bin/python
LOGS=$QA/logs/$(date +%Y%m%d-%H%M%S)
mkdir -p "$LOGS"
FALHAS=()

resumo() {
    local log=$1
    if grep -q 'oxlint\|eslint(\|react(' "$log"; then
        echo "$(grep -c ': warning ' "$log") avisos, $(grep -c ': error ' "$log") erros"; return
    fi
    local pass; pass=$(grep -oE '^ℹ pass [0-9]+' "$log" | tail -1)
    [ -n "$pass" ] && { echo "${pass#ℹ } testes"; return; }
    grep -E 'passed|^Ran [0-9]+|built in|"aprovado"|erros de página' "$log" | tail -1 | cut -c1-70
}

etapa() {
    local nome=$1 arquivo=$2; shift 2
    printf '%-34s ' "$nome"
    if "$@" > "$LOGS/$arquivo.log" 2>&1; then
        echo "ok    $(resumo "$LOGS/$arquivo.log")"
    else
        echo "FALHOU (log: $LOGS/$arquivo.log)"
        FALHAS+=("$nome")
    fi
}

interface_ipv4() {
    # O teste usa o Handler real em banco temporário servido por servidor_ipv4_isolado.py.
    rm -f "$TMPDIR/retomada-ipv4-frontend/api-teste.json"
    "$PY" -B frontend/tests/servidor_ipv4_isolado.py > "$LOGS/servidor-ipv4.log" 2>&1 &
    local pid=$! i
    for i in $(seq 100); do grep -q API_ISOLADA_PRONTA "$LOGS/servidor-ipv4.log" && break; sleep 0.1; done
    (cd frontend && node --test tests/interfaceIPv4.test.mjs)
    local codigo=$?
    kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
    return $codigo
}

cd "$RAIZ"
etapa 'Backend (pytest)' backend-pytest \
    env PYTHONPATH=app "$PY" -m pytest -p no:cacheprovider app/laboratorios/tests -q
etapa 'Backend HTTP (unittest)' backend-http \
    env PYTHONPATH=app:app/prototipo "$PY" -m unittest app/prototipo/testar_gateway_guiado_http.py \
    app/prototipo/testar_retomada_ipv4.py app/prototipo/testar_http_retomada_ipv4.py app/prototipo/testar_pedidos_acesso.py app/prototipo/testar_senhas_turma.py
etapa 'Backup do banco (pytest)' backup-banco \
    "$PY" -m pytest -p no:cacheprovider tools/backup -q
etapa 'Contas da apresentação (pytest)' contas-apresentacao \
    "$PY" -m pytest -p no:cacheprovider tools/admin -q
etapa 'Frontend unidade (node --test)' frontend-unidade \
    bash -c 'cd frontend && node --test tests/*.test.js tests/paletaIPv4.test.mjs'
etapa 'Frontend aula IPv4 (jsdom)' frontend-ipv4 interface_ipv4
etapa 'Lint (oxlint src)' lint bash -c 'cd frontend && node_modules/.bin/oxlint src'
etapa 'Build candidato (.qa/dist)' build \
    bash -c "cd frontend && node node_modules/vite/bin/vite.js build --outDir '$QA/dist' --emptyOutDir"

if [ $RAPIDO -eq 0 ]; then
    etapa 'Navegador Lab 3 (Playwright)' navegador-lab3 \
        env PINGLEVEL_QA_DIST="$QA/dist" PINGLEVEL_QA_OUT="$QA/capturas/gateway-ui" "$PY" -B frontend/tests/gateway-ui.playwright.py
    etapa 'Capturas topologia Lab 3' capturas-lab3 "$PY" -B tools/qa/capturar_lab3.py
    etapa 'Navegador aulas 1 e 2 (Playwright)' navegador-aulas-1-2 "$PY" -B tools/qa/capturar_aulas_1_2.py
    etapa 'Navegador aula 3 (Playwright)' navegador-aula3 "$PY" -B tools/qa/capturar_aula3.py
    etapa 'Navegador aula gateway (Playwright)' navegador-aula-gateway "$PY" -B tools/qa/capturar_aula_gateway.py
    etapa 'Navegador aula ferramentas (Playwright)' navegador-aula-ferramentas "$PY" -B tools/qa/capturar_aula_ferramentas.py
    etapa 'Navegador aula plano (Playwright)' navegador-aula-plano "$PY" -B tools/qa/capturar_aula_plano.py
    etapa 'Navegador aula VLSM (Playwright)' navegador-aula-vlsm "$PY" -B tools/qa/capturar_aula_vlsm.py
    etapa 'Navegador aula roteamento (Playwright)' navegador-aula-roteamento "$PY" -B tools/qa/capturar_aula_roteamento.py
    etapa 'Navegador aula DHCP e DNS (Playwright)' navegador-aula-dhcp-dns "$PY" -B tools/qa/capturar_aula_dhcp_dns.py
    etapa 'Navegador aulas LAN e transporte (Playwright)' navegador-aula-lan "$PY" -B tools/qa/capturar_aula_lan.py
    etapa 'Navegador trilha e módulos (Playwright)' navegador-navegacao "$PY" -B tools/qa/capturar_navegacao.py
    etapa 'Navegador Lab 4 (Playwright)' navegador-lab4 \
        env PINGLEVEL_QA_DIST="$QA/dist" PINGLEVEL_QA_OUT="$QA/capturas/lab4" "$PY" -B frontend/tests/terminal-ui.playwright.py
    etapa 'Navegador Labs 5, 6 e 7 (Playwright)' navegador-labs56 \
        env PINGLEVEL_QA_DIST="$QA/dist" PINGLEVEL_QA_OUT="$QA/capturas/labs56" "$PY" -B frontend/tests/labs-setores.playwright.py
    etapa 'Navegador teste de carga (Playwright)' navegador-carga \
        env PINGLEVEL_QA_DIST="$QA/dist" PINGLEVEL_QA_OUT="$QA/capturas/carga" "$PY" -B frontend/tests/suporte-remoto.playwright.py
fi

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
    echo "Tudo aprovado. Build candidato em $QA/dist; capturas em $QA/capturas; logs em $LOGS"
else
    echo "Falharam: ${FALHAS[*]}"; exit 1
fi
