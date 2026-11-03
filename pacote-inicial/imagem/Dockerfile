# Imagem única de todas as máquinas do trabalho prático de DEC7128, 2026/2.
# Cada máquina recebe no compose.yaml o script de inicialização que a configura.
FROM alpine:3.23 AS mibs
RUN apk add --no-cache net-snmp-libs

FROM debian:trixie-slim
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    nftables snmpd snmp nginx-light dnsmasq-base prometheus prometheus-blackbox-exporter \
    openssh-server openssh-client iperf3 nmap tcpdump iproute2 iputils-ping traceroute \
    curl dnsutils netcat-openbsd procps psmisc python3 less nano vim-tiny ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
# O Debian não distribui as MIBs padrão; as do net-snmp vêm da imagem do Alpine.
COPY --from=mibs /usr/share/snmp/mibs /usr/share/snmp/mibs
RUN printf 'mibs SNMPv2-MIB:IF-MIB:IP-MIB:HOST-RESOURCES-MIB:SNMP-FRAMEWORK-MIB\n' > /etc/snmp/snmp.conf \
 && mkdir -p /var/lib/snmp /run/sshd \
 && ssh-keygen -A
COPY bin/ /usr/local/bin/
# Um arquivo salvo no Windows pode trazer CRLF; os programas usam LF.
RUN sed -i 's/\r$//' /usr/local/bin/* && chmod +x /usr/local/bin/*
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/iniciar"]
