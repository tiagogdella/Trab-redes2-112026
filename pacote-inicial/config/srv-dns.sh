ip route del default 2>/dev/null || true
ip route add default via 10.80.1.1

# Catálogo de nomes. Fica em /run porque a mudança (degrau 10) vai editá-lo
# (a pasta /config é só leitura).
cat > /run/nomes <<'FIM'
10.80.1.1     rt-borda
10.80.11.2    rt-andar1
10.80.12.2    rt-andar2
10.80.1.10    srv-portal
10.80.1.20    srv-arquivos
10.80.1.30    srv-dns
10.80.21.10   cli-alfa
10.80.22.10   cli-beta
10.80.23.10   cli-gama
10.80.0.10    externo
10.80.0.20    sonda-internet
10.80.23.20   sonda-gama
10.80.250.100 gerente
FIM

# Servidor de nomes: responde só com o catálogo acima, na interface da rede comum.
dnsmasq --no-resolv --no-hosts --addn-hosts=/run/nomes \
        --listen-address=10.80.1.30 --bind-interfaces
