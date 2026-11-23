#!/usr/bin/env bash
# Leva uma branch aprovada à produção: avança o main de /opt/packetlab (fast-forward), roda todos os testes
# ali, publica o frontend se ele mudou e informa se o backend precisa ser reiniciado. Se os testes falharem,
# os arquivos de produção voltam ao commit anterior. Não reinicia serviços: isso exige confirmação.
# Uso: /opt/packetlab/tools/qa/publicar.sh <branch>
set -euo pipefail

# Tudo dentro de uma função: o merge reescreve este arquivo e o bash precisa tê-lo lido por inteiro antes.
main() {
    local raiz=/opt/packetlab branch=${1:?Informe a branch a publicar} antes alterados
    cd "$raiz"
    [ "$(git branch --show-current)" = main ] || { echo "$raiz precisa estar no main."; exit 1; }
    [ -z "$(git status --porcelain)" ] || { echo "$raiz tem alterações não commitadas; nada foi feito."; exit 1; }
    git merge-base --is-ancestor main "$branch" || { echo "$branch não parte do main atual: atualize-a antes."; exit 1; }
    alterados=$(git diff --name-only main "$branch")
    [ -n "$alterados" ] || { echo "$branch não traz mudanças em relação ao main."; exit 0; }

    antes=$(git rev-parse HEAD)
    git merge --ff-only -q "$branch"
    echo "main avançado de ${antes:0:7} para $(git rev-parse --short HEAD) ($(wc -l <<< "$alterados") arquivos)."
    if ! tools/qa/rodar.sh; then
        git reset -q --keep "$antes"
        echo "Testes falharam em produção; arquivos e main voltaram para ${antes:0:7}."
        exit 1
    fi

    if grep -qE '^frontend/(src/|public/|index\.html|package)' <<< "$alterados"; then
        tools/qa/publicar_frontend.sh
    else
        echo "Frontend sem mudanças; dist mantido."
    fi
    if grep -qE '^app/' <<< "$alterados"; then
        echo "BACKEND ALTERADO: falta reiniciar pinglevel-web.service (encerra treinos ativos) para valer."
    fi
    echo "Para o GitHub: git push origin main $branch"
}

main "$@"; exit
