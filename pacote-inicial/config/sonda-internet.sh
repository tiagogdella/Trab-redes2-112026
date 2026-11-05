ip route del default 2>/dev/null || true
ip route add default via 10.80.0.1

echo "nameserver 10.80.1.30" > /etc/resolv.conf

# Blackbox Exporter: testa os serviços daqui e entrega o resultado pela gerência.
prometheus-blackbox-exporter --config.file=/config/blackbox.yml \
    --web.listen-address=10.80.250.41:9115 > /tmp/blackbox.log 2>&1 &
