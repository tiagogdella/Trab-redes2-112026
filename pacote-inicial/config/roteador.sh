# Inicialização do roteador. As duas redes estão ligadas a ele diretamente, então ele
# não precisa de rota estática; um roteador com rede remota usaria "ip route add PREFIXO via PRÓXIMO_SALTO".
ip route del default 2>/dev/null || true
# Condição do enlace: 20 ms de atraso na saída para rede-b.
tc qdisc replace dev eth1 root netem delay 20ms
