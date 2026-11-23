# Demonstração "Suporte remoto" (teste de carga): a imagem dos serviços mais o cliente SSH, uma chave própria da
# demonstração aceita por todos os nós e o recebedor da impressora (porta 9100). As imagens dos Labs 1 a 10 não mudam.
FROM pinglevel/servicos:0.1

RUN apk add --no-cache openssh-client \
    && ssh-keygen -q -t ed25519 -N '' -C 'pinglevel-demonstracao' -f /root/.ssh/id_demo \
    && cat /root/.ssh/id_demo.pub >> /root/.ssh/authorized_keys \
    && chmod 600 /root/.ssh/authorized_keys /root/.ssh/id_demo

COPY ssh_config /root/.ssh/config
COPY receber-impressao.sh /usr/local/bin/receber-impressao
RUN chmod 600 /root/.ssh/config && chmod 755 /usr/local/bin/receber-impressao
