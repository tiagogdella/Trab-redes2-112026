# Roteador de borda: rotas estáticas para as redes dos andares.
ip route del default 2>/dev/null || true
ip route add 10.80.21.0/24 via 10.80.11.2   # alfa  -> rt-andar1
ip route add 10.80.22.0/24 via 10.80.11.2   # beta  -> rt-andar1
ip route add 10.80.23.0/24 via 10.80.12.2   # gama  -> rt-andar2

# Enlaces dos andares: 5 ms de atraso e 20 Mbit/s em cada sentido.
tc qdisc replace dev eth2 root netem delay 5ms rate 20mbit   # enlace-andar1
tc qdisc replace dev eth3 root netem delay 5ms rate 20mbit   # enlace-andar2
