# Imagem dos Labs 8 e 10 (DHCP e DNS): a do Lab 3 mais o dnsmasq, que faz os dois serviços.
# Não modifica pinglevel/ssh:0.1 nem pinglevel/gateway:0.1. Aprovada pelo Gabriel em 30/10/2026.
# Construir: docker build -t pinglevel/servicos:0.1 images/pinglevel-servicos
FROM pinglevel/gateway:0.1
RUN apk add --no-cache dnsmasq
# Cliente DHCP: grava os servidores DNS da concessão no /etc/resolv.conf montado pelo Docker.
COPY udhcpc/ /etc/udhcpc/
