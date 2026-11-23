#!/bin/sh
# Página web da impressora do Prédio A (porta 80), atendida por "nc -lk -p 80 -e": cada conexão é um pedido HTTP.
#   GET  /          estado da impressora e quantas folhas já saíram
#   POST /imprimir  corpo "texto=..." vira uma folha em /tmp/folhas (o mural do professor lê de lá)
# Instalada pelo servidor ao preparar o ambiente (topologia_setores._preparar_suporte), sem mudar a imagem.
read -r metodo caminho _
tamanho=0
while read -r linha; do
  linha=$(printf '%s' "$linha" | tr -d '\r')
  [ -z "$linha" ] && break
  case "$linha" in
    [Cc]ontent-[Ll]ength:*) tamanho=$(printf '%s' "${linha#*:}" | tr -dc '0-9') ;;
  esac
done
mkdir -p /tmp/folhas
if [ "$metodo" = POST ] && [ "$caminho" = /imprimir ]; then
  corpo=$(head -c "${tamanho:-0}")
  texto=$(printf '%s' "${corpo#texto=}" | tr '+' ' ' | head -c 120)
  printf '%s\n' "$texto" > "/tmp/folhas/$(date +%s)-$$.txt"
  folhas=$(ls /tmp/folhas | wc -l)
  resposta="Impressora do Prédio A: trabalho recebido. Folha $folhas impressa."
else
  folhas=$(ls /tmp/folhas | wc -l)
  resposta="Impressora do Prédio A (192.168.10.50)
Estado: pronta | papel A4 | toner 72%
Folhas impressas: $folhas
Para imprimir: curl -d \"texto=...\" http://192.168.10.50/imprimir"
fi
printf 'HTTP/1.0 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\n\r\n%s\n' "$resposta"
