Trabalho prático: a rede de uma organização
1. Em resumo
Cada grupo recebe por sorteio uma de oito organizações fictícias, descritas na página "As organizações", publicada com este enunciado.
O grupo monta a rede dessa organização em contêineres Docker, com o Docker Compose, e a opera: rotas, nomes, filtragem de pacotes, gerência por SNMPv3, monitoramento com alertas, inventário e uma mudança planejada.
O grupo entrega um vídeo e um artigo até 27/11/2026, às 23h59.
2. Requisitos da rede
Topologia. As máquinas, as redes e as ligações descritas para a organização, com os mesmos nomes. Cada rede da organização é uma rede Docker, e cada máquina, um contêiner. Os roteadores encaminham os pacotes com rotas estáticas. Nenhuma máquina usa a rota padrão que o Docker cria, exceto o gerente, para que o Prometheus abra no navegador, como mostra o pacote inicial.
Endereços. IPv4, escolhidos pelo grupo dentro de 10.0.0.0/8, inclusive na rede internet.
Internet simulada. A rede internet faz o papel da Internet, mas é uma rede Docker comum, sem saída para a Internet real. Nela ficam externo e as sondas que representam usuários de fora da organização. É dessas máquinas que o grupo testa os acessos vindos de fora e varre as portas dos servidores.
Nomes. srv-dns resolve, com o dnsmasq, o nome de cada máquina da organização. Usuários e sondas acessam os serviços pelo nome, nunca pelo endereço.
Filtragem. Cada roteador filtra com o nftables e, por padrão, descarta tanto o tráfego que o atravessa (cadeia forward) quanto o tráfego destinado a ele (cadeia input). Passam só o tráfego que a política de acesso da organização permite, as respostas a esse tráfego, as consultas do gerente pela rede gerencia e, vindas da Internet, as consultas de nomes ao servidor de nomes em uso (53/udp e 53/tcp): srv-dns, ou srv-dns2 depois da mudança da organização 4. Cada regra de descarte conta os pacotes que descartou (counter).
Rede de gerência. Uma rede própria, gerencia, liga o gerente às máquinas marcadas na descrição da organização. Nenhum pacote passa entre ela e as demais redes.
SNMPv3. Cada roteador executa um agente SNMP, o programa que responde às consultas de gerência. Ele exige autenticação e cifragem (nível authPriv), responde só ao gerente e só a consultas SNMPv3.
Monitoramento. O Prometheus roda no gerente. Cada sonda, uma máquina que testa os serviços do lugar onde estão os usuários, roda o Blackbox Exporter. Cada critério de sucesso da organização tem uma regra de alerta, que dispara quando ele deixa de ser cumprido. Um critério de sucesso é uma condição que um serviço precisa cumprir, como responder em menos de 200 ms. Quando o Prometheus não consegue ler a métrica de um critério, porque a máquina ou o programa que a entrega parou, o critério conta como descumprido.
Inventário. Um arquivo lista cada máquina, com interfaces, endereços, software em execução e versão, e responsável: a equipe de redes nos roteadores, a equipe de sistemas nas demais máquinas. Um script compara o arquivo com a rede em funcionamento e lista cada diferença.
Mudança planejada. A mudança pedida na descrição da organização, com um plano em cinco partes (pré-condição, execução, validação, critério de reversão e reversão) e três scripts, aplicar, validar e reverter, executados dentro das máquinas com docker exec. As redes e as máquinas usadas pela mudança já estão no compose.yaml desde o início, ainda sem configuração: a mudança só configura, sem criar contêineres.
Um só comando. docker compose up -d --build inicia a rede com todos os requisitos acima funcionando, sem nenhum outro comando.
3. Pacote inicial
O pacote inicial, publicado no Moodle com este enunciado, traz:

uma imagem Debian, usada por todas as máquinas, com as ferramentas do trabalho: nftables, net-snmp, nginx, dnsmasq, Prometheus, Blackbox Exporter, OpenSSH, iperf3, nmap, nc, tcpdump e tc;
dois programas para as organizações que têm fluxos UDP: emissor-udp, que envia mensagens numeradas, e receptor-udp, que mede a perda e o atraso e entrega essas métricas ao Prometheus;
o programa exportar-nft, que entrega ao Prometheus os contadores das regras do nftables de um roteador;
um exemplo com três máquinas, cliente, roteador e servidor, que inicia com docker compose up -d --build.
Todos os comandos de rede, dentro dos contêineres, são de Linux. Cada linha docker funciona sem alteração no terminal do Linux e no cmd do Windows. Todo o trabalho acontece dentro dos contêineres: é proibido testar, varrer ou injetar tráfego em equipamentos da UFSC ou de terceiros.

4. Medições comuns a todos os grupos
Operação normal. Durante 10 minutos, a mediana e o maior valor medido em cada critério de sucesso.
Falha do serviço. O processo do serviço indicado na descrição da organização é encerrado, com a máquina ligada. Em 5 repetições, o tempo entre a falha e o disparo do alerta, e entre a correção e o fim do alerta.
Falha do enlace. Perda de 100% no enlace indicado na descrição da organização, aplicada com tc qdisc e netem nas duas pontas. As mesmas medições, em 5 repetições.
Mudança. O tempo em que as sondas ficam sem resposta durante a aplicação e durante a reversão.
Filtragem. Em externo, uma varredura das portas 1 a 1024 de cada servidor, com nmap -Pn -p 1-1024 seguido do nome do servidor. Para cada varredura, as portas que o nmap encontra abertas e o contador de cada regra de descarte antes e depois.
Condições. Computador, sistema operacional, versão do Docker e outros programas abertos durante as medições.
5. Calendário
Data	O que acontece
16/10	Lançamento: enunciado, descrição das organizações e pacote inicial no Moodle
até 17/10	Resultado do sorteio das organizações, no Moodle
19/11	Primeira metade da aula dedicada ao TP, com o professor na sala
27/11, 23h59	Entrega
6. O que o grupo entrega
6.1 Vídeo
Uma gravação contínua, sem cortes e sem limite de duração, com a tela legível, mostrando nesta ordem:

docker compose up -d --build iniciando a rede;
cada serviço funcionando, acessado de onde estão os seus usuários;
o script de inventário;
as duas falhas, com o alerta disparando e terminando depois da correção;
a mudança aplicada, validada e revertida.
Ao longo do vídeo, os integrantes explicam quatro partes: topologia, endereços e rotas; filtragem e SNMPv3; monitoramento e alertas; inventário e mudança. Os dois falam, e todas as partes são explicadas; o rosto não precisa aparecer. Um erro que surja durante a gravação é diagnosticado e corrigido ali mesmo. O grupo pode ensaiar e regravar o vídeo inteiro quantas vezes quiser; o que não pode é editar.

O vídeo é publicado no YouTube como não listado e fica disponível, sem alteração, até a divulgação da nota final da disciplina.

6.2 Artigo
Escrito em LaTeX, no modelo de artigos da Sociedade Brasileira de Computação (SBC), sem limite de páginas. O título traz o nome da organização; os autores são os integrantes, com nome e matrícula; o link do vídeo vem logo depois do resumo. As seções:

Introdução. A organização, o que a rede precisa garantir aos usuários e a teoria em que o projeto se apoia.
Projeto da rede. Diagrama com endereços, rotas, regras de filtragem, configuração do SNMPv3, critérios e regras de alerta, e o plano de mudança. Cada decisão vem com o motivo.
Método. Como cada medição da seção 4 foi feita, com as repetições e as condições registradas.
Resultados. Gráficos e tabelas de cada medição, com a variação entre as repetições.
Discussão. Por que cada resultado saiu como saiu, com o conteúdo da disciplina, como o que determina o tempo entre a falha e o alerta, e o que pode ter distorcido o resultado.
Fontes, ferramentas e divisão do trabalho. Inclui a declaração de uso de inteligência artificial pedida na seção 6.3.
6.3 Inteligência artificial
O artigo segue o Código de Conduta para Autores em Publicações da SBC, de 28/02/2024, que vale para todo artigo publicado pela SBC:

uma ferramenta de inteligência artificial, como ChatGPT, Copilot ou Claude, não é autora do artigo;
o artigo declara cada ferramenta usada e onde foi empregada: texto, tabelas, gráficos, citações, configurações ou scripts;
os integrantes respondem por todo o conteúdo, inclusive por plágio que a ferramenta tenha introduzido.
Nesta disciplina vale ainda uma regra a mais: o texto do artigo é escrito pelos integrantes. A ferramenta pode criticar o trabalho como faria um avaliador, traduzir o resumo para o inglês e revisar estrutura, repetição, ortografia, concordância e terminologia do texto deles, mas não o escreve. Na rede, o uso é livre, inclusive para escrever configurações e scripts, e no vídeo os integrantes explicam o próprio trabalho.

6.4 Envio no Moodle
Até 27/11/2026, às 23h59, um integrante envia, em nome do grupo:

o artigo em PDF;
a pasta do projeto em .zip, com tudo o que docker compose up -d --build precisa para iniciar a rede: compose.yaml, configurações e scripts. Só a pasta .git, com o histórico do Git, fica de fora;
os arquivos de todas as medições, sem edição, e o programa ou a planilha que gerou os gráficos.
Um link de vídeo que falte ou que peça acesso equivale a vídeo não entregue.

7. Organização
Item	Definição
Peso na média	25%
Composição da nota	Vídeo 40% e artigo 60%
Grupos	Duplas, com inscrição no Moodle até 17/10. Como a turma tem 15 estudantes, um estudante faz o trabalho sozinho, com o mesmo escopo, e explica todas as partes no vídeo
Ferramentas de inteligência artificial	Permitidas, nas condições da seção 6.3
8. Material de apoio
TANENBAUM, Andrew S.; FEAMSTER, Nick; WETHERALL, David J. Computer Networks. 6. ed. Pearson, 2021. Capítulo 5, seções 5.1 e 5.2 (encaminhamento e rotas), e Capítulo 8, seção 8.3 (firewalls).
RFC 3414 (modelo de segurança do SNMPv3) e RFC 3415 (controle de acesso do SNMP).
Documentação do Prometheus, do Blackbox Exporter, do nftables, do snmpd.conf(5) e do Docker Compose.
Manual do iproute2: ip-route(8) e tc-netem(8).