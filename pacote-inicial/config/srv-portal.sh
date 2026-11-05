ip route del default 2>/dev/null || true
ip route add default via 10.80.1.1

echo "nameserver 10.80.1.30" > /etc/resolv.conf

# Portal de reserva de salas: nginx na porta 80.
mkdir -p /srv/www
echo "Portal de reserva de salas - Espaco Ponto Comum" > /srv/www/index.html
cat > /run/nginx.conf <<'FIM'
events {}
http {
    access_log /var/log/nginx/acesso.log;
    server { listen 80; root /srv/www; }
}
FIM
nginx -c /run/nginx.conf
