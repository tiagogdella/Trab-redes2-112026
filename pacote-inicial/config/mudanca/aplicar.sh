# Mudança: rede gama de 10.80.23.0/24 para 10.80.33.0/24.
# Uso: docker exec MAQUINA sh /config/mudanca/aplicar.sh FASE   (FASE = 1 ou 2)
set -e
. "$(dirname "$0")/comum.sh"
trocar 23 33 "$1"
