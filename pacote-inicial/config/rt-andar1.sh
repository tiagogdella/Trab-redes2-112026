# Roteador do 1º andar: o que não conhece vai para o rt-borda.
ip route del default 2>/dev/null || true
ip route add default via 10.80.11.1

# Enlace com o rt-borda: 5 ms de atraso e 20 Mbit/s em cada sentido.
tc qdisc replace dev eth0 root netem delay 5ms rate 20mbit

echo "nameserver 10.80.1.30" > /etc/resolv.conf
