# Validação da mudança, na máquina em que roda.
# Uso: docker exec MAQUINA sh /config/mudanca/validar.sh ANTIGO NOVO
#   depois de aplicar:  validar.sh 23 33     depois de reverter:  validar.sh 33 23
# Imprime OK ou FALHA por item; termina com erro se algum item falhar.
A="10\.80\.$1\."; N=10.80.$2
falhas=0
ok()    { echo "$(hostname): OK    $1"; }
falha() { echo "$(hostname): FALHA $1"; falhas=$((falhas + 1)); }

# 1. O prefixo antigo não aparece em nenhuma rota, endereço, regra ou entrada de nome.
sem_antigo() {   # $1 = descrição, $2 = comando
    if sh -c "$2" 2>/dev/null | grep -q "$A"; then falha "$1 ainda tem 10.80.$OLD"
    else ok "$1 sem o prefixo antigo"; fi
}
OLD=$1
sem_antigo "rotas"     "ip route show"
sem_antigo "endereços" "ip -4 addr show"
command -v nft >/dev/null && sem_antigo "regras" "nft list ruleset"
[ -f /run/nomes ] && sem_antigo "nomes" "cat /run/nomes"

case "$(hostname)" in
    srv-dns)
        # 2. Os nomes da Gama apontam para o prefixo novo.
        for nome in cli-gama sonda-gama; do
            ip=$(dig +short @10.80.1.30 $nome)
            case "$ip" in $N.*) ok "$nome = $ip" ;; *) falha "$nome = $ip" ;; esac
        done ;;
    cli-gama)
        # 3. Gama continua sem alcançar Alfa e Beta (o pacote é descartado: timeout).
        for nome in cli-alfa cli-beta; do
            r=$(nc -zv -w 3 $nome 80 2>&1)
            case "$r" in
                *"timed out"*)         ok "sem acesso a $nome" ;;
                *refused*|*succeeded*) falha "alcançou $nome" ;;
                *)                     falha "teste inconclusivo para $nome: $r" ;;
            esac
        done ;;    
    gerente)
        # 4. C1 a C3 cumpridos: sondas no ar, testes com sucesso e nenhum alerta disparado.
        for c in C1 C2 C3; do
            r=$(curl -s -G http://localhost:9090/api/v1/query \
                --data-urlencode "query=min(probe_success{job=\"$c\"}) * min(up{job=\"$c\"})")
            case "$r" in *'"1"]'*) ok "$c cumprido" ;; *) falha "$c descumprido" ;; esac
        done
        r=$(curl -s http://localhost:9090/api/v1/alerts)
        case "$r" in *'"firing"'*) falha "há alerta disparado" ;; *) ok "nenhum alerta disparado" ;; esac ;;
esac

[ $falhas -eq 0 ]
