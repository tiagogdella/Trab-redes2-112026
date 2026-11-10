# Plano de mudança: novo prefixo da rede gama

**Pedido:** a Gama quer outro prefixo, porque 10.80.23.0/24 coincide com outra rede que ela usa.
**De** 10.80.23.0/24 **para** 10.80.33.0/24 (fora de qualquer outra rede da organização).
**Afeta:** rt-borda (rota e filtro), rt-andar2 (endereço e filtro), cli-gama e sonda-gama
(endereço e rota padrão), srv-dns (nomes). A rede Docker gama não muda.
**Estratégia:** make-before-break, em 2 fases. Na fase 1 o prefixo novo é acrescentado
sem tirar o antigo; na fase 2 o antigo é retirado. Entre as fases os dois funcionam.

## 1. Pré-condição
- Todas as máquinas `healthy`: `docker compose ps`
- Inventário sem diferença: `python3 verificar-inventario.py`
- Estado inicial confirmado (gama em .23, nada em .33, C1–C3 cumpridos, nenhum alerta):
  `./mudanca.sh validar-reversao`

## 2. Execução
`./mudanca.sh aplicar`, que executa, nesta ordem:

    # Fase 1: constrói o caminho novo
    docker exec rt-borda   sh /config/mudanca/aplicar.sh 1   # rota + filtro para .33
    docker exec rt-andar2  sh /config/mudanca/aplicar.sh 1   # endereço .33.1 + filtro
    docker exec sonda-gama sh /config/mudanca/aplicar.sh 1   # endereço .33.20 + rota padrão
    docker exec cli-gama   sh /config/mudanca/aplicar.sh 1   # endereço .33.10 + rota padrão
    docker exec srv-dns    sh /config/mudanca/aplicar.sh 1   # nomes apontam para .33
    # Fase 2: desfaz o caminho antigo
    docker exec sonda-gama sh /config/mudanca/aplicar.sh 2
    docker exec cli-gama   sh /config/mudanca/aplicar.sh 2
    docker exec rt-andar2  sh /config/mudanca/aplicar.sh 2
    docker exec rt-borda   sh /config/mudanca/aplicar.sh 2

## 3. Validação
`./mudanca.sh validar` espera 15 s (as sondas testam de novo) e confere:
- o prefixo antigo não aparece em nenhuma rota, endereço, regra ou entrada de nome;
- cli-gama e sonda-gama resolvem para .33;
- a Gama continua sem alcançar a Alfa e a Beta (conexão TCP descartada: timeout);
- C1, C2 e C3 cumpridos e nenhum alerta disparado.

## 4. Critério de reversão
Reverter se acontecer qualquer um destes:
- um comando da execução termina com erro;
- a validação mostra qualquer FALHA;
- um alerta de C1, C2 ou C3 dispara durante ou depois da mudança.

## 5. Reversão
`./mudanca.sh reverter` (mesmas fases e ordem, de .33 para .23), depois
`./mudanca.sh validar-reversao`.
Último recurso, se a reversão falhar: `docker restart rt-borda rt-andar2 cli-gama sonda-gama srv-dns`.
Os scripts de inicialização recriam a configuração original.

## Para tornar a mudança permanente (depois de aprovada)
A mudança vale até as máquinas reiniciarem. Para ficar permanente: atualizar o
inventario.toml e os scripts de inicialização (rt-borda.sh, rt-borda.nft, rt-andar2.sh,
rt-andar2.nft, cli-gama.sh, sonda-gama.sh, srv-dns.sh).
