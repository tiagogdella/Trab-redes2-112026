# Roteador do 1º andar: o que não conhece vai para o rt-borda.
ip route del default 2>/dev/null || true
ip route add default via 10.80.11.1
