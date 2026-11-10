# Registro de decisões (ADR) — Espaço Ponto Comum

Formato: o que decidimos, por quê e o que mais consideramos.

## D1. Plano de endereçamento
- **Decisão:** um /24 por rede, dentro de 10.80.0.0/16 ("80" = organização 8).
  Terceiro octeto: 0 internet, 1 comum, 11/12 enlaces, 21/22/23 alfa/beta/gama,
  250 gerência. Gama nova (mudança): 10.80.33.0/24.
- **Por quê:** fácil de ler e de lembrar; o número da rede diz onde ela fica.
  Roteador sempre no .1; o .254 fica reservado ao gateway que o Docker exige.
- **Alternativas:** /30 nos enlaces (economiza endereços, mas o Docker precisa do .254
  e não há falta de endereços em 10.0.0.0/8).

## D2. Nomes das interfaces
- **Decisão:** eth0, eth1... nas redes normais; mgmt0 sempre na gerência.
- **Por quê:** as regras do nftables usam o nome da interface; com mgmt0 fica
  óbvio qual é a gerência.

## D3. Inventário em TOML
- **Decisão:** inventario.toml, uma ficha [[maquina]] por contêiner.
- **Por quê:** legível por pessoas e lido pelo Python sem biblioteca extra (tomllib).
- **Alternativas:** YAML (precisa instalar biblioteca), JSON (ruim de editar à mão).

## D4. Rotas estáticas
- **Decisão:** máquinas: rota padrão pelo roteador da sua rede. Roteadores de andar:
  rota padrão pelo rt-borda. rt-borda: uma rota por rede de inquilina.
  externo e sonda-internet: rota padrão pelo rt-borda (simulam a Internet).
- **Por quê:** topologia em árvore; só o rt-borda precisa conhecer as redes dos andares.

## D5. Condições dos enlaces (netem)
- **Decisão:** `delay 5ms rate 20mbit` nas duas pontas de cada enlace.
- **Por quê:** "em cada sentido" = uma qdisc em cada ponta.
- **Observação:** o 1º ping leva +10 ms porque a consulta ARP também passa pelo netem.

## D6. DNS
- **Decisão:** dnsmasq só com a nossa lista (/run/nomes), escutando só na rede comum.
  Um IP por nome: o da rede onde os usuários chegam. O gerente não usa DNS.
- **Por quê:** a lista fica em /run porque /config é só leitura e a mudança
  precisa editá-la. O gerente fica só na gerência, sem caminho até a comum.

## D7. Filtragem (nftables)
- **Decisão:** policy drop em forward e input. A política detalhada fica no rt-borda;
  os roteadores de andar deixam as inquilinas "subirem" (conferindo a origem,
  anti-falsificação) e isolam Alfa de Beta. A gerência é descartada antes de tudo.
  Cada descarte tem counter e um nome (comment). Prefixos em `define`.
- **Por quê:** o rt-borda é por onde passa todo tráfego entre redes diferentes.
  Os nomes aparecem no Prometheus; os `define` facilitam a mudança da Gama.
- **Ponto aberto:** ICMP entre inquilinas passa (regra geral: "ICMP passa entre as
  redes da organização"). TCP/UDP entre elas é bloqueado. **Confirmar em 19/11.**
- **Efeito colateral:** traceroute padrão (UDP) é bloqueado; usar `traceroute -I`.

## D8. SNMPv3
- **Decisão:** usuário "gerente", SHA-256 + AES, `rouser ... priv`, sem community.
  Um snmpd.conf para os 3 roteadores; o endereço de escuta vai na linha de comando.
- **Por quê:** authPriv = autenticação + cifragem (RFC 3414). Sem community,
  v1/v2c não respondem. "Só ao gerente" em 3 camadas: escuta só na mgmt0,
  firewall só aceita o IP do gerente, e precisa da senha.
- **Limitação:** as senhas ficam em texto no arquivo.

## D9. Monitoramento e alertas
- **Decisão:** coleta e avaliação a cada 5 s; `for: 10s`; um job por critério;
  todo alerta inclui `or up == 0`.
- **Por quê:** tempo até o alerta ≤ ~20 s (5 coleta + 5 avaliação + 10 for); o `for`
  evita alarme falso por um teste lento isolado; `up == 0` cumpre a regra
  "métrica que não chega = critério descumprido".
- **C2 (< 50 ms):** usamos probe_duration_seconds, que inclui o DNS (mais rigoroso).
- **Achado:** o DNS levava 21 ms (consultas A e AAAA); com `ip_protocol_fallback: false`
  caiu para 10 ms, e o C2 de ~43 ms para ~32 ms.

## D10. Pasta do projeto
- **Decisão:** trabalhar direto no pacote-inicial/.

## D11. Script de inventário
- **Decisão:** Python no computador (não num contêiner), usando docker exec para olhar
  dentro de cada máquina. Confere contêineres, redes, endereços, software em execução e
  versão, nos dois sentidos (inventário → rede e rede → inventário).
- **Por quê:** o tomllib já vem no Python 3.11+, sem instalar nada; o docker exec dá a
  mesma visão que o operador tem. Código de saída 1 quando há diferença (útil em automação).

## D12. Mudança da gama: make-before-break
- **Decisão:** 2 fases (acrescenta o novo, depois retira o antigo). Firewall com conjuntos
  nomeados (`@inquilinas`, `@gama`), editados com `nft add/delete element`.
  Um só comum.sh; aplicar = 23→33, reverter = 33→23 (a reversão é a mesma troca ao contrário).
  Cada máquina faz a sua parte conforme o próprio hostname.
- **Por quê:** trocar tudo de uma vez deixaria a Gama sem caminho por alguns segundos.
  Com as 2 fases, os testes de 0,1 em 0,1 s não falharam nenhuma vez.
  Os conjuntos nomeados mudam sem recarregar as regras e sem zerar os contadores.

## D13. Validação espera o monitoramento
- **Decisão:** o validar espera 15 s antes de conferir; o teste de isolamento separa
  "timeout" (descartado), "refused/succeeded" (alcançou) e "inconclusivo".
- **Por quê:** a 1ª versão deu falso positivo: validou no mesmo segundo da mudança e pegou
  um teste da sonda interrompido pela troca de endereço (o alerta não disparou, por causa do
  `for: 10s`). 15 s = pelo menos 2 testes novos de cada sonda (coleta a cada 5 s).
