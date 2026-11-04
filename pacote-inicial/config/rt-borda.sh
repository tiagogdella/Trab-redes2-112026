# Roteador de borda: rotas estáticas para as redes dos andares.
ip route del default 2>/dev/null || true
ip route add 10.80.21.0/24 via 10.80.11.2   # alfa  -> rt-andar1
ip route add 10.80.22.0/24 via 10.80.11.2   # beta  -> rt-andar1
ip route add 10.80.23.0/24 via 10.80.12.2   # gama  -> rt-andar2
