#!/usr/bin/env bash
# Publica o build candidato (.qa/dist, gerado por tools/qa/rodar.sh) no frontend/dist servido pelo Nginx.
# Backup do dist antes; assets copiados primeiro e index.html trocado por último; assets antigos preservados
# para páginas já abertas. Não reinicia serviços nem toca no backend.
set -euo pipefail

RAIZ=/opt/packetlab
CANDIDATO=$RAIZ/.qa/dist
DESTINO=$RAIZ/frontend/dist
BACKUPS=/home/gabriel/backups-pinglevel

# Só se publica o que está no main de produção, sem alterações locais.
[ "$(cd "$(dirname "$0")/../.." && pwd)" = "$RAIZ" ] || { echo "Rode a partir de $RAIZ, não da cópia de trabalho."; exit 1; }
[ "$(git -C "$RAIZ" branch --show-current)" = main ] || { echo "$RAIZ precisa estar no main."; exit 1; }
[ -z "$(git -C "$RAIZ" status --porcelain)" ] || { echo "$RAIZ tem alterações não commitadas."; exit 1; }
[ -f "$CANDIDATO/index.html" ] || { echo "Sem build candidato: rode tools/qa/rodar.sh"; exit 1; }
MAIS_NOVOS=$(find "$RAIZ/frontend/src" "$RAIZ/frontend/public" "$RAIZ/frontend/index.html" -newer "$CANDIDATO/index.html" -type f)
if [ -n "$MAIS_NOVOS" ]; then
    echo "Fontes alteradas depois do build candidato; rode tools/qa/rodar.sh de novo:"; echo "$MAIS_NOVOS"; exit 1
fi

mkdir -p -m 700 "$BACKUPS"
BACKUP=$BACKUPS/antes-publicacao-frontend-$(date +%Y%m%d-%H%M%S).tar.gz
(umask 077; tar -czf "$BACKUP" -C "$RAIZ" frontend/dist)
tar -tzf "$BACKUP" > /dev/null
echo "Backup: $BACKUP"

cd "$CANDIDATO"
find . -type f ! -name index.html | while read -r arquivo; do
    mkdir -p "$DESTINO/$(dirname "$arquivo")"
    cp "$arquivo" "$DESTINO/$arquivo.publicando" && mv -f "$DESTINO/$arquivo.publicando" "$DESTINO/$arquivo"
done
cp index.html "$DESTINO/.index.html.publicando"
chmod 644 "$DESTINO/.index.html.publicando"
mv -f "$DESTINO/.index.html.publicando" "$DESTINO/index.html"

DIFERENTES=$(find . -type f | while read -r arquivo; do cmp -s "$arquivo" "$DESTINO/$arquivo" || echo "$arquivo"; done)
[ -z "$DIFERENTES" ] || { echo "Arquivos diferentes após a cópia:"; echo "$DIFERENTES"; exit 1; }
echo "Publicado: $(grep -oE 'assets/index-[^"]+\.js' "$DESTINO/index.html"). Nenhum serviço foi reiniciado."
