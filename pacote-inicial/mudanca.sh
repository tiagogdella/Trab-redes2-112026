#!/bin/sh
# Executa a mudança da rede gama na ordem do plano (adr.md / plano-mudanca.md).
# Uso: ./mudanca.sh aplicar | validar | reverter | validar-reversao
# Cada linha "docker exec" também pode ser copiada e executada à mão (inclusive no cmd do Windows).
set -e
M=${M:-/config/mudanca}

passo() {   # $1 = script, $2 = fase, demais = máquinas, na ordem
    script=$1; fase=$2; shift 2
    for maquina in "$@"; do
        docker exec "$maquina" sh $M/$script.sh $fase
    done
}

case "$1" in
    aplicar|reverter)
        echo "== $1, fase 1: constrói o caminho novo"
        passo "$1" 1 rt-borda rt-andar2 sonda-gama cli-gama srv-dns
        echo "== $1, fase 2: desfaz o caminho antigo"
        passo "$1" 2 sonda-gama cli-gama rt-andar2 rt-borda ;;
    validar)
        for maquina in rt-borda rt-andar2 cli-gama sonda-gama srv-dns gerente; do
            docker exec "$maquina" sh $M/validar.sh 23 33 || falhou=1
        done
        [ -z "$falhou" ] && echo "== VALIDAÇÃO OK" || { echo "== VALIDAÇÃO FALHOU"; exit 1; } ;;
    validar-reversao)
        for maquina in rt-borda rt-andar2 cli-gama sonda-gama srv-dns gerente; do
            docker exec "$maquina" sh $M/validar.sh 33 23 || falhou=1
        done
        [ -z "$falhou" ] && echo "== VALIDAÇÃO OK" || { echo "== VALIDAÇÃO FALHOU"; exit 1; } ;;
    *)
        echo "uso: $0 aplicar | validar | reverter | validar-reversao"; exit 2 ;;
esac
