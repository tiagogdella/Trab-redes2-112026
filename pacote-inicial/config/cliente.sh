# Inicialização do cliente. Executado a cada início do contêiner; um erro interrompe o script.
# Troca a rota padrão do Docker pelo roteador do grupo.
ip route del default 2>/dev/null || true
ip route add default via 10.250.1.1
echo "nameserver 10.250.2.10" > /etc/resolv.conf
