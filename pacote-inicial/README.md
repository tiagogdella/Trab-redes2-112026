# Pacote inicial do trabalho prático

Esta pasta é o ponto de partida do projeto do grupo. Ela traz a imagem usada por todas as máquinas e um exemplo com três máquinas: cliente, roteador e servidor.

## Requisitos

Docker Engine 28 ou mais recente, com Docker Compose 2.36 ou mais recente. No Windows e no macOS, a versão atual do Docker Desktop. Todas as linhas `docker` rodam nesta pasta, e cada uma funciona igual no terminal do Linux e no `cmd` do Windows.

## Iniciar o exemplo

Na primeira vez, a imagem é construída, o que leva alguns minutos:

```text
docker compose up -d --build --wait
docker exec cliente ip route show
docker exec cliente traceroute -n servidor
docker exec cliente curl http://servidor/
docker compose down
```

## Como o exemplo funciona

| Arquivo | O que faz |
|---|---|
| `compose.yaml` | Máquinas, redes e endereços. Todas as máquinas usam a mesma imagem e recebem, em `command`, o script que as configura |
| `config/*.sh` | Um script por máquina, executado sempre que o contêiner inicia: rotas, `netem` e serviços. O script roda no `sh` do Debian (o `dash`), e não no `bash`: `[[ ]]`, vetores e `source` não funcionam. Um comando com erro interrompe o script, e a mensagem aparece em `docker compose logs NOME` |
| `imagem/` | A imagem Debian com as ferramentas e os programas `iniciar`, `emissor-udp`, `receptor-udp` e `exportar-nft`. Não precisa ser alterada |

Pontos que valem para toda a rede do grupo:

- **O tráfego passa só pelos roteadores do grupo.** As redes do `compose.yaml` não têm endereço no computador, com a exceção da `gerencia` descrita abaixo, nem tradução de endereços, e o gateway que o Docker reserva fica no endereço `.254`, que nenhuma máquina usa. Cada script começa removendo a rota padrão criada pelo Docker.
- **Só os roteadores encaminham.** No `compose.yaml`, os roteadores usam `sysctls: *roteador`, com encaminhamento ligado, e as demais máquinas, `sysctls: *host`, com encaminhamento desligado. Assim um servidor ligado à `gerencia` e a outra rede não passa pacotes de uma para a outra.
- **Nomes de interface fixos**, com `interface_name`, para que os scripts e as regras do nftables não dependam da ordem das redes.
- **Máquina pronta.** A máquina fica marcada como pronta (`healthy`) quando o script termina sem erro; `docker compose up -d --build --wait` só termina quando todas estão prontas.
- **Arquivos dentro da máquina.** A pasta `config/` aparece em `/config` em todas as máquinas, só para leitura.
- **Prometheus no navegador.** Para abrir o Prometheus em `http://localhost:9090`, a rede `gerencia` é a única com endereço no computador, e o gerente publica a porta e mantém a rota padrão do Docker, sem a qual a resposta não volta ao navegador. É a única exceção à remoção da rota padrão:

  ```yaml
  gerente:
    ports: ["9090:9090"]
    networks:
      gerencia: {interface_name: mgmt0, ipv4_address: 10.250.9.100}
  ```

  e, em `networks`, a `gerencia` sem a opção `inhibit_ipv4`:

  ```yaml
  gerencia:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_ip_masquerade: "false"
    ipam: {config: [{subnet: 10.250.9.0/24, gateway: 10.250.9.254}]}
  ```

## Fluxos UDP

```text
emissor-udp DESTINO PORTA TAXA TAMANHO
receptor-udp PORTA_UDP ENDERECO:PORTA_DAS_METRICAS [ARQUIVO_CSV]
```

O emissor envia mensagens numeradas, cada uma com o instante de envio, e consulta o nome do destino no DNS a cada 5 s, sem interromper o envio enquanto espera a resposta. O receptor entrega ao Prometheus, em `http://ENDERECO:PORTA/metrics`, as métricas de cada emissor: mensagens recebidas, perdidas e fora de ordem, a distribuição do atraso (um histograma) e o instante da última chegada. Com o terceiro argumento, ele também grava uma linha por mensagem num arquivo CSV. O atraso medido é exato porque todos os contêineres usam o relógio do mesmo computador. Exemplo, nos scripts de inicialização:

```text
receptor-udp 5000 10.250.9.20:9101 /tmp/leituras.csv > /tmp/receptor.log 2>&1 &
emissor-udp coletor 5000 10 100 > /tmp/emissor.log 2>&1 &
```

Quando o emissor para, o receptor não conta perdas: só uma mensagem que chega revela as que faltaram antes dela. Para saber se as mensagens continuam chegando, use o instante da última chegada; para saber se o próprio receptor está no ar, a métrica `up` que o Prometheus cria para cada alvo.

## Contadores do nftables

```text
exportar-nft ENDERECO:PORTA
```

Entrega ao Prometheus, em `http://ENDERECO:PORTA/metrics`, os pacotes e os bytes contados por cada regra do nftables que tem `counter`, nas métricas `nft_pacotes_total` e `nft_bytes_total`. O rótulo `regra` é o comentário da regra, então dê um nome a cada regra de descarte:

```text
nft add rule inet filtro forward iifname "eth0" counter drop comment "descarte-internet"
exportar-nft 10.250.9.1:9102 > /tmp/exportar-nft.log 2>&1 &
```

## Problemas comuns

- **Uma máquina não fica pronta.** `docker compose logs NOME` mostra a mensagem do comando que falhou.
- **`\r` ou `not found` na primeira linha de um script.** O arquivo foi salvo com fim de linha do Windows. O `iniciar` remove o `\r` dos scripts de inicialização; nos demais arquivos, salve com fim de linha LF no editor. O `.gitattributes` desta pasta faz o Git usar LF.
- **`Pool overlaps with other one on this address space`.** Outra rede do computador já usa o mesmo prefixo. Escolha outro prefixo dentro de 10.0.0.0/8.
