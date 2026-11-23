#!/bin/sh
# Cada conexão na porta 9100 (impressão direta, como nas impressoras de rede) vira uma folha em /tmp/folhas.
mkdir -p /tmp/folhas
cat > "/tmp/folhas/$(date +%s)-$$.txt"
