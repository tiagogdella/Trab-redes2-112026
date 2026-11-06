# Parte comum de aplicar.sh e reverter.sh: troca o prefixo da rede gama
# de 10.80.$1.0/24 para 10.80.$2.0/24, na fase $3, na máquina em que roda.
#   fase 1 (preparar): acrescenta o prefixo novo, sem tirar o antigo;
#   fase 2 (limpar):   tira o prefixo antigo.
# Entre as duas fases os dois prefixos funcionam juntos, então as sondas
# não ficam sem resposta (primeiro constrói o caminho novo, depois desfaz o velho).
trocar() {
    A=10.80.$1; N=10.80.$2; FASE=$3
    case "$(hostname)" in
        cli-gama)   H=10 ;;
        sonda-gama) H=20 ;;
    esac
    case "$(hostname)-$FASE" in
        rt-borda-1)
            ip route add $N.0/24 via 10.80.12.2
            nft add element inet filtro inquilinas "{ $N.0/24 }" ;;
        rt-borda-2)
            ip route del $A.0/24 via 10.80.12.2
            nft delete element inet filtro inquilinas "{ $A.0/24 }" ;;
        rt-andar2-1)
            ip addr add $N.1/24 dev eth1
            nft add element inet filtro gama "{ $N.0/24 }" ;;
        rt-andar2-2)
            ip addr del $A.1/24 dev eth1
            nft delete element inet filtro gama "{ $A.0/24 }" ;;
        cli-gama-1|sonda-gama-1)
            ip addr add $N.$H/24 dev eth0
            ip route replace default via $N.1 src $N.$H ;;
        cli-gama-2|sonda-gama-2)
            ip addr del $A.$H/24 dev eth0 ;;
        srv-dns-1)
            sed -i "s/^10\.80\.$1\./10.80.$2./" /run/nomes
            kill -HUP "$(pidof dnsmasq)" ;;
        *)
            echo "$(hostname): nada a fazer na fase $FASE"; return 0 ;;
    esac
    echo "$(hostname): fase $FASE concluída ($A.0/24 -> $N.0/24)"
}
