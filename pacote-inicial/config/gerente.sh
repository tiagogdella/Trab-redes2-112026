# O gerente é o único que MANTÉM a rota padrão do Docker (pro Prometheus abrir no navegador).

# Prometheus: coleta pela gerência; abre no navegador em http://localhost:9090.
prometheus --config.file=/config/prometheus.yml --storage.tsdb.path=/tmp/prometheus \
    --web.listen-address=0.0.0.0:9090 > /tmp/prometheus.log 2>&1 &

