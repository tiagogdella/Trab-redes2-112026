# Inicialização do servidor: rota padrão pelo roteador, uma página no nginx e os nomes no dnsmasq.
ip route del default 2>/dev/null || true
ip route add default via 10.250.2.1

mkdir -p /srv/www
echo "servidor do exemplo" > /srv/www/index.html
cat > /run/nginx.conf <<'FIM'
events {}
http {
    access_log /var/log/nginx/acesso.log;
    server { listen 80; root /srv/www; }
}
FIM
nginx -c /run/nginx.conf

cat > /run/nomes <<'FIM'
10.250.1.10 cliente
10.250.1.1  roteador
10.250.2.10 servidor
FIM
dnsmasq --no-resolv --no-hosts --addn-hosts=/run/nomes --listen-address=10.250.2.10 --bind-interfaces
