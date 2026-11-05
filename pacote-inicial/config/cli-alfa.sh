ip route del default 2>/dev/null || true
ip route add default via 10.80.21.1

echo "nameserver 10.80.1.30" > /etc/resolv.conf
