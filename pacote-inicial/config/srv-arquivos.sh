ip route del default 2>/dev/null || true
ip route add default via 10.80.1.1

echo "nameserver 10.80.1.30" > /etc/resolv.conf

# Arquivos compartilhados: simulados por um nginx na porta 8080.
mkdir -p /srv/www
echo "Arquivos compartilhados - Espaco Ponto Comum" > /srv/www/index.html
cat > /run/nginx.conf <<'FIM'
events {}
http {
    access_log /var/log/nginx/acesso.log;
    server { listen 8080; root /srv/www; }
}
FIM
nginx -c /run/nginx.conf
