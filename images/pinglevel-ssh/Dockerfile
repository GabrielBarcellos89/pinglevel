FROM pinglevel/base:0.1

RUN apk add --no-cache openssh-server \
    && mkdir -p /root/.ssh /run/sshd \
    && chmod 700 /root/.ssh \
    && sed -i 's/^#PermitRootLogin.*/PermitRootLogin prohibit-password/' \
        /etc/ssh/sshd_config \
    && sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' \
        /etc/ssh/sshd_config \
    && printf '\nPubkeyAuthentication yes\nAllowTcpForwarding no\nX11Forwarding no\n' \
        >> /etc/ssh/sshd_config

COPY authorized_keys /root/.ssh/authorized_keys
COPY iniciar-sshd.sh /usr/local/bin/iniciar-sshd

RUN chmod 600 /root/.ssh/authorized_keys \
    && chmod 755 /usr/local/bin/iniciar-sshd

EXPOSE 22

CMD ["/usr/local/bin/iniciar-sshd"]
